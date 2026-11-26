"""
tests/test_ingredient_sheet.py — Fiches ingrédients (2026-11-26).

Fiche de l'application (tableaux pour 100 g, source, saison, prix, CO₂,
recettes), pages publiques /ingredient/<slug> pour les moteurs de recherche,
et corrections proposées par les membres, source à l'appui : relecture,
application par-dessus la base (fiche et calcul des recettes), annulation.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.api.routes import ingredient_corrections as ic
from backend.core.auth_deps import get_optional_user, get_user
from backend.core.data_io import load_catalogue_recipes
from backend.db.models import Base, IngredientCorrection, User
from backend.db.session import get_db
from backend.engine.nutrition_engine import compute_nutrition
from backend.services import ingredient_sheet as S

MEMBER = "membre@exemple.com"
MOD = "moderation@exemple.com"
EGG = "eggplant_raw"


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        for e in (MEMBER, MOD):
            db.add(User(email=e, password_hash="x"))
        db.commit()

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(S, "CORRECTIONS_PATH", tmp_path / "ingredient_corrections.json")
    S._corr_cache.update(sig=None, data={})
    monkeypatch.setattr(ic, "check_rate_limit", lambda *a, **k: None)
    # le recalcul des graphes réécrirait les vrais fichiers de données : testé à part
    from backend.services import nutrition_refresh
    refreshed: list = []
    monkeypatch.setattr(nutrition_refresh, "refresh_for_ingredients", lambda ids, **k: refreshed.append(list(ids)))
    from backend.core.config import settings
    monkeypatch.setattr(settings, "admin_emails", {MOD})
    monkeypatch.delenv("SMTP_HOST", raising=False)
    who = {"email": MEMBER}
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_user] = lambda: dict(who)
    app.dependency_overrides[get_optional_user] = lambda: dict(who)
    try:
        yield TestClient(app), who, Session
    finally:
        for dep in (get_db, get_user, get_optional_user):
            app.dependency_overrides.pop(dep, None)
        S._corr_cache.update(sig=None, data={})


def _row(sheet, key):
    return next(r for g in sheet["nutrition"] for r in g["rows"] if r["key"] == key)


# ── Fiche ─────────────────────────────────────────────────────────────────────

def test_fiche_ingredient(env):
    c, _, _ = env
    s = c.get(f"/ingredients/{EGG}/fiche").json()
    assert s["name_fr"] == "Aubergine" and s["slug"] == "aubergine" and s["public_page"]
    assert s["source"]["code"] == "CIQUAL" and s["source"]["id"] == "20053"
    assert s["source"]["url"].endswith("/20053")
    assert [g["title"] for g in s["nutrition"]] == ["Énergie et macronutriments", "Minéraux", "Vitamines"]
    potassium = _row(s, "potassium_mg")
    assert potassium["value"] == pytest.approx(229) and potassium["pct"] == 11       # VNR 2000 mg
    assert s["season"]["months"] == [6, 7, 8, 9]
    assert s["price"]["per_kg_eur"] > 0 and s["carbon"]["kg_co2_per_kg"] > 0
    assert s["recipes_count"] >= 30 and s["recipes"][0]["title"]
    assert "Vegan" in s["diets"] and s["allergens"] == []
    assert c.get("/ingredients/inconnu_xyz/fiche").status_code == 404
    # GET /ingredients/{id} : la nutrition n'est plus vide
    assert c.get(f"/ingredients/{EGG}").json()["nutrition"]["calories_kcal"] == pytest.approx(22.9)


def test_pages_publiques(env):
    c, _, _ = env
    page = c.get("/ingredient/aubergine")
    assert page.status_code == 200
    html = page.text
    assert "<h1>Aubergine : valeurs nutritionnelles" in html
    assert "Vitamines" in html and "% VNR" in html and "ciqual.anses.fr" in html
    assert 'href="/recette/' in html and '"@type": "BreadcrumbList"' in html
    assert c.get("/ingredient/pas-un-ingredient").status_code == 404
    assert c.get("/ingredient/eau-eau-potable").status_code == 404        # pas de page pour l'eau
    index = c.get("/ingredient").text
    assert 'href="/ingredient/aubergine"' in index
    assert "/ingredient/aubergine" in c.get("/sitemap.xml").text
    recipe = c.get("/recette/curry_aubergine_sri_lanka_bf8bcd").text
    assert '<a href="/ingredient/aubergine">' in recipe


# ── Corrections ───────────────────────────────────────────────────────────────

def _propose(c, **kw):
    body = {"ingredient_id": EGG, "field": "protein_g", "proposed_value": 1.2,
            "source_ref": "Table Ciqual 2020, code 20053", "source_url": "https://ciqual.anses.fr/#/aliments/20053"}
    body.update(kw)
    return c.post("/ingredient-corrections", json=body)


def test_garde_fous(env):
    c, _, _ = env
    assert _propose(c, source_ref="").status_code == 422
    assert _propose(c, source_url="pas un lien").status_code == 422
    assert _propose(c, proposed_value=0.98).status_code == 422             # déjà la valeur affichée
    assert _propose(c, field="cholesterol").status_code == 422
    assert _propose(c, field="other", proposed_value=None, comment="court").status_code == 422
    assert _propose(c, ingredient_id="inconnu").status_code == 404
    assert _propose(c, proposed_value=None).status_code == 422
    assert _propose(c).status_code == 201
    assert _propose(c, proposed_value=1.3).status_code == 409             # déjà une en attente
    assert _propose(c, field="other", proposed_value=None,
                    comment="Le nom anglais devrait être « aubergine » au Royaume-Uni.").status_code == 201


def test_accepter_appliquer_annuler(env):
    from backend.services import mail_service
    c, who, Session = env
    curry = next(r for r in load_catalogue_recipes() if r["id"] == "curry_aubergine_sri_lanka_bf8bcd")
    before = compute_nutrition(curry)["protein"]
    mail_service.OUTBOX.clear()
    cid = _propose(c, proposed_value=5.0).json()["id"]
    assert any(MOD in m["to"] for m in mail_service.OUTBOX)
    assert c.post(f"/ingredient-corrections/moderation/{cid}/accept", json={}).status_code == 403

    who["email"] = MOD
    q = c.get("/ingredient-corrections/moderation/queue").json()
    assert q["counts"]["submitted"] == 1 and q["results"][0]["value_now"] == pytest.approx(0.98)
    res = c.post(f"/ingredient-corrections/moderation/{cid}/accept", json={"message": "Vérifié, merci."})
    assert res.status_code == 200 and res.json()["status"] == "accepted"
    assert res.json()["refresh"]["recipes"] >= 30
    assert S.CORRECTIONS_PATH.exists()

    # la fiche et le calcul des recettes utilisent la valeur corrigée
    s = c.get(f"/ingredients/{EGG}/fiche").json()
    assert _row(s, "protein_g")["value"] == 5.0 and _row(s, "protein_g")["corrected"]
    assert s["corrections"][0]["previous"] == pytest.approx(0.98) and "Ciqual" in s["corrections"][0]["source"]
    after = compute_nutrition(curry)["protein"]
    assert after == pytest.approx(before + (5.0 - 0.98) * 500 / 100 / 4, abs=0.2)   # 500 g pour 4
    assert "Corrections apportées" in c.get("/ingredient/aubergine").text
    assert any(MEMBER in m["to"] and "appliquée" in m["subject"] for m in mail_service.OUTBOX)

    # une nouvelle correction acceptée remplace la précédente
    who["email"] = MEMBER
    cid2 = _propose(c, proposed_value=1.1).json()["id"]
    who["email"] = MOD
    c.post(f"/ingredient-corrections/moderation/{cid2}/accept", json={})
    with Session() as db:
        assert db.get(IngredientCorrection, cid).status == "superseded"
    assert _row(c.get(f"/ingredients/{EGG}/fiche").json(), "protein_g")["value"] == 1.1

    # annulation : motif obligatoire, la valeur de la base revient
    assert c.post(f"/ingredient-corrections/moderation/{cid2}/revert", json={"message": "x"}).status_code == 422
    assert c.post(f"/ingredient-corrections/moderation/{cid2}/revert",
                  json={"message": "Valeur d'un produit cuit, pas cru."}).status_code == 200
    s = c.get(f"/ingredients/{EGG}/fiche").json()
    assert _row(s, "protein_g")["value"] == pytest.approx(0.98) and s["corrections"] == []
    assert compute_nutrition(curry)["protein"] == pytest.approx(before)


def test_refus_retrait_et_compte_supprime(env):
    c, who, Session = env
    rejected = _propose(c).json()["id"]
    pending = _propose(c, field="iron_mg", proposed_value=0.5).json()["id"]
    accepted = _propose(c, field="fiber_g", proposed_value=2.5).json()["id"]
    who["email"] = MOD
    assert c.post(f"/ingredient-corrections/moderation/{rejected}/reject", json={"message": ""}).status_code == 422
    c.post(f"/ingredient-corrections/moderation/{rejected}/reject", json={"message": "La source parle d'aubergine cuite."})
    c.post(f"/ingredient-corrections/moderation/{accepted}/accept", json={})
    who["email"] = MEMBER
    mine = {x["id"]: x for x in c.get("/ingredient-corrections/mine").json()["results"]}
    assert mine[rejected]["status"] == "rejected" and "cuite" in mine[rejected]["moderator_note"]
    assert c.delete(f"/ingredient-corrections/{rejected}").status_code == 409     # déjà relue
    with Session() as db:
        assert ic.delete_user_corrections(db, MEMBER) == 2                         # en attente + refusée
        db.commit()
        kept = db.get(IngredientCorrection, accepted)
        assert kept.user_email is None and kept.status == "accepted"
        assert db.get(IngredientCorrection, pending) is None
