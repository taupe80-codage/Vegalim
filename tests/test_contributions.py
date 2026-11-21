"""
tests/test_contributions.py — Recettes proposées par les utilisateurs.

Parcours complet : brouillon → envoi → modération → publication dans le
catalogue (community_recipes.json fusionné par load_recipes), et garde-fous :
100 % végétarien, vegan tenu, droits de modération, photo ré-encodée,
suppression du compte.
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.core import data_io
from backend.core.auth_deps import get_user
from backend.db.models import Base, User
from backend.db.session import get_db
from backend.services import contribution_service as cs

AUTHOR = "auteur@exemple.com"
OTHER = "autre@exemple.com"
MOD = "moderation@exemple.com"


def _ing(name, iid, qty, unit="g", note=""):
    return {"name": name, "ingredient_id": iid, "quantity": qty, "unit": unit, "note": note}


GOOD = {
    "title": "Dahl de lentilles corail au potimarron rôti",
    "description": "Un dahl doux et réconfortant pour l'automne.",
    "diet": "vegan",
    "dish_type": "main",
    "cuisine": "indian",
    "difficulty": "easy",
    "servings": 4,
    "prep_min": 15,
    "cook_min": 30,
    "rest_min": 0,
    "ingredients": [
        _ing("lentilles corail", "red_lentil_dried", 250),
        _ing("lait de coco", "coconut_milk_plant", 400, "ml"),
        _ing("oignon", "onion_raw", 1, "piece", "émincé"),
        _ing("ail", "garlic_raw", 2, "gousse"),
        _ing("huile d'olive", "olive_oil_plant", 2, "tbsp"),
        _ing("sel", "table_salt_unenriched", None, "to_taste"),
    ],
    "steps": [
        "Faire revenir l'oignon et l'ail dans l'huile 5 minutes, sans coloration.",
        "Ajouter les lentilles rincées, le lait de coco et 50 cl d'eau, puis cuire 25 minutes à feu doux.",
    ],
    "tip": "Une pointe de citron vert au service réveille le plat.",
}


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        for e in (AUTHOR, OTHER, MOD):
            db.add(User(email=e, password_hash="x"))
        db.commit()

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(data_io, "COMMUNITY_RECIPES_PATH", tmp_path / "community_recipes.json")
    monkeypatch.setattr(cs, "PHOTO_DIR", tmp_path / "photos")
    from backend.core.config import settings
    monkeypatch.setattr(settings, "admin_emails", {MOD})
    from backend.core import rate_limiter
    monkeypatch.setattr(rate_limiter, "check_rate_limit", lambda *a, **k: None)
    import backend.api.routes.contributions as routes
    monkeypatch.setattr(routes, "check_rate_limit", lambda *a, **k: None)

    who = {"email": AUTHOR}
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_user] = lambda: dict(who)
    data_io.load_recipes.cache_clear()
    try:
        yield TestClient(app), who, Session
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_user, None)
        data_io.load_recipes.cache_clear()


def _create(c, data=GOOD):
    res = c.post("/contributions", json={"data": data, "author_name": "Léa"})
    assert res.status_code == 201, res.text
    return res.json()


def _submit(c, sid):
    return c.post(f"/contributions/{sid}/submit", json={"author_name": "Léa", "consent": True})


# ── Saisie ────────────────────────────────────────────────────────────────────

def test_lecture_des_lignes_d_ingredients():
    lines = cs.parse_ingredient_lines(
        "200 g de farine\n2 c. à soupe d'huile d'olive\n1 oignon, émincé\n"
        "3 gousses d'ail\npoivre selon le goût\n½ l de lait d'avoine\n10 cl de crème")
    got = [(l["quantity"], l["unit"], l["name"]) for l in lines]
    assert got == [
        (200.0, "g", "farine"), (2.0, "tbsp", "huile d'olive"), (1.0, "piece", "oignon"),
        (3.0, "gousse", "ail"), (None, "to_taste", "poivre"), (0.5, "l", "lait d'avoine"),
        (10.0, "cl", "crème"),
    ]
    assert lines[2]["note"] == "émincé"
    assert all(l["ingredient_id"] for l in lines)


def test_viande_et_poisson_bloques_des_la_saisie():
    lines = cs.parse_ingredient_lines("100 g de lardons\n1 filet de saumon")
    assert all(l["non_vegetarian"] and l["ingredient_id"] is None for l in lines)
    data = {**GOOD, "ingredients": GOOD["ingredients"] + [_ing("blanc de poulet", None, 200)]}
    a = cs.analyze(data)
    assert not a["ready"]
    assert any(i["level"] == "blocking" and "poulet" in i["message"] for i in a["issues"])


def test_vegan_annonce_mais_beurre_bloque_et_propose_un_remplacement():
    data = {**GOOD, "ingredients": GOOD["ingredients"] + [_ing("beurre", "butter_sup80pct", 30)]}
    a = cs.analyze(data)
    assert not a["ready"] and not a["diet"]["vegan"]
    culprit = a["diet"]["non_vegan_ingredients"][0]
    assert culprit["ingredient_id"] == "butter_sup80pct"
    assert culprit["substitute"]["id"] == "vegan_butter"
    # La même recette annoncée végétarienne passe
    assert cs.analyze({**data, "diet": "vegetarian"})["ready"]


def test_analyse_recette_complete():
    a = cs.analyze(GOOD)
    assert a["ready"], a["issues"]
    assert a["diet"]["vegan"]
    assert a["nutrition"]["calories"] > 100
    assert a["total_min"] == 45


def test_conversion_vers_le_format_du_catalogue():
    r = cs.build_recipe(GOOD, submission_id="x")
    comp = {c["ingredient"]: (c["quantity"], c["unit"]) for c in r["composition"]}
    assert comp["coconut_milk_plant"] == (400.0, "ml")
    assert comp["olive_oil_plant"][1] == "g" and 25 <= comp["olive_oil_plant"][0] <= 35
    assert comp["garlic_raw"][0] > 0 and comp["onion_raw"][0] >= 80
    assert r["instructions"][0].startswith("Étape 1: ")
    assert r["diet_flags"]["vegan"] is True and r["id"].startswith("comm_")


# ── Parcours complet ──────────────────────────────────────────────────────────

def test_parcours_brouillon_envoi_publication(env):
    c, who, _ = env
    sub = _create(c)
    assert sub["status"] == "draft" and sub["editable"]
    sid = sub["id"]

    # sans consentement : refus
    res = c.post(f"/contributions/{sid}/submit", json={"author_name": "Léa", "consent": False})
    assert res.status_code == 422
    res = _submit(c, sid)
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "submitted"
    # plus modifiable par l'auteur une fois envoyée
    assert c.put(f"/contributions/{sid}", json={"data": GOOD}).status_code == 409

    # un utilisateur ordinaire n'accède pas à la modération
    assert c.get("/contributions/moderation/queue").status_code == 403

    who["email"] = MOD
    q = c.get("/contributions/moderation/queue").json()
    assert [s["id"] for s in q["results"]] == [sid] and q["counts"]["submitted"] == 1
    detail = c.get(f"/contributions/moderation/{sid}").json()
    assert detail["analysis"]["ready"]
    res = c.post(f"/contributions/moderation/{sid}/publish", json={"message": "Merci !"})
    assert res.status_code == 200, res.text
    rid = res.json()["published_recipe_id"]

    # la recette est dans le catalogue, avec son auteur
    recipe = next(r for r in data_io.load_recipes() if r["id"] == rid)
    assert recipe["community"]["author_name"] == "Léa"
    fiche = c.get(f"/recettes/{rid}")
    assert fiche.status_code == 200, fiche.text
    assert fiche.json()["community"]["author_name"] == "Léa"
    assert fiche.json()["nutrition"]["calories"] > 100

    # l'auteur la voit publiée, la retire : elle quitte le catalogue
    who["email"] = AUTHOR
    mine = c.get("/contributions/mine").json()["results"]
    assert mine[0]["status"] == "published"
    assert c.delete(f"/contributions/{sid}").status_code == 204
    assert all(r["id"] != rid for r in data_io.load_recipes())


def test_recette_publiee_trouvee_par_la_recherche(env):
    c, who, _ = env
    sid = _create(c)["id"]
    _submit(c, sid)
    who["email"] = MOD
    rid = c.post(f"/contributions/moderation/{sid}/publish", json={}).json()["published_recipe_id"]
    res = c.post("/recettes/recherche", json={"query": "potimarron rôti", "limit": 50})
    assert res.status_code == 200, res.text
    body = res.json()
    ids = [r["id"] for r in (body.get("results") or body.get("recipes") or [])]
    assert rid in ids


def test_renvoi_a_l_auteur_puis_nouvel_envoi(env):
    c, who, _ = env
    sid = _create(c)["id"]
    _submit(c, sid)
    who["email"] = MOD
    assert c.post(f"/contributions/moderation/{sid}/request-changes", json={"message": "court"}).status_code == 422
    res = c.post(f"/contributions/moderation/{sid}/request-changes",
                 json={"message": "Précisez la quantité d'eau dans les ingrédients, s'il vous plaît."})
    assert res.json()["status"] == "changes_requested"
    who["email"] = AUTHOR
    s = c.get(f"/contributions/{sid}").json()
    assert s["editable"] and "quantité d'eau" in s["moderator_note"]
    assert c.put(f"/contributions/{sid}", json={"data": GOOD}).status_code == 200
    assert _submit(c, sid).json()["status"] == "submitted"


def test_ingredient_hors_catalogue_bloque_la_publication(env):
    c, who, _ = env
    data = {**GOOD, "ingredients": GOOD["ingredients"] + [_ing("épice secrète de mamie", None, 5)]}
    sid = _create(c, data)["id"]
    assert _submit(c, sid).status_code == 200          # l'auteur peut envoyer
    who["email"] = MOD
    res = c.post(f"/contributions/moderation/{sid}/publish", json={})
    assert res.status_code == 422 and "épice secrète" in res.json()["detail"]
    # la modération rattache l'ingrédient, puis publie
    fixed = {**data, "ingredients": GOOD["ingredients"] + [_ing("épice secrète de mamie", "cumin_spice_seed", 5)]}
    assert c.put(f"/contributions/moderation/{sid}", json={"data": fixed}).status_code == 200
    assert c.post(f"/contributions/moderation/{sid}/publish", json={}).status_code == 200


def test_on_ne_voit_pas_les_recettes_des_autres(env):
    c, who, _ = env
    sid = _create(c)["id"]
    who["email"] = OTHER
    assert c.get(f"/contributions/{sid}").status_code == 404
    assert c.put(f"/contributions/{sid}", json={"data": GOOD}).status_code == 404
    assert c.delete(f"/contributions/{sid}").status_code == 404
    assert c.get("/contributions/mine").json()["results"] == []


def test_envoi_refuse_si_incomplet(env):
    c, _, _ = env
    sid = _create(c, {**GOOD, "steps": ["Tout mélanger."]})["id"]
    res = _submit(c, sid)
    assert res.status_code == 422 and "étapes" in res.json()["detail"]


def test_photo_reencodee_sans_metadonnees(env):
    from PIL import Image
    c, _, _ = env
    sid = _create(c)["id"]
    img = Image.new("RGB", (900, 600), (200, 120, 40))
    exif = Image.Exif()
    exif[0x010F] = "Appareil"            # Make
    buf = io.BytesIO()
    img.save(buf, "PNG", exif=exif)
    res = c.put(f"/contributions/{sid}/photo", content=buf.getvalue(), headers={"Content-Type": "image/png"})
    assert res.status_code == 200, res.text
    url = res.json()["photo_url"]
    got = c.get(url)
    assert got.status_code == 200 and got.headers["content-type"] == "image/jpeg"
    out = Image.open(io.BytesIO(got.content))
    assert out.format == "JPEG" and not out.getexif()
    # un faux fichier image est refusé
    res = c.put(f"/contributions/{sid}/photo", content=b"pas une image", headers={"Content-Type": "image/jpeg"})
    assert res.status_code == 422


def test_suppression_du_compte_retire_les_recettes(env):
    from backend.api.routes.contributions import delete_user_contributions
    c, who, Session = env
    sid = _create(c)["id"]
    _submit(c, sid)
    who["email"] = MOD
    rid = c.post(f"/contributions/moderation/{sid}/publish", json={}).json()["published_recipe_id"]
    assert any(r["id"] == rid for r in data_io.load_recipes())
    with Session() as db:
        assert delete_user_contributions(db, AUTHOR) == 1
    assert all(r["id"] != rid for r in data_io.load_recipes())


def test_options_publiques():
    c = TestClient(app)
    res = c.get("/contributions/options")
    assert res.status_code == 200
    body = res.json()
    assert {d["value"] for d in body["diets"]} == {"vegan", "vegetarian"}
    assert body["is_moderator"] is False


def test_identifiant_d_ingredient_inconnu_traite_comme_hors_catalogue():
    data = {**GOOD, "ingredients": GOOD["ingredients"] + [_ing("truc", "id_invente_xyz", 10)]}
    clean = cs.normalize(data)
    assert clean["ingredients"][-1]["ingredient_id"] is None
    assert "truc" in cs.analyze(data)["unmatched"]


def test_herbes_a_la_feuille_et_au_brin_ne_pesent_pas_100_g():
    lines = {l["name"]: l for l in cs.parse_ingredient_lines("10 feuilles de sauge\n3 brins de thym")}
    assert lines["sauge"]["unit"] == "feuille" and lines["thym"]["unit"] == "brin"
    assert cs.to_catalogue_quantity(lines["sauge"]["ingredient_id"], 10, "feuille") == (5.0, "g")
    assert cs.to_catalogue_quantity(lines["thym"]["ingredient_id"], 3, "brin") == (3.0, "g")
