"""
tests/test_recipe_versions.py — Recettes modifiées par un membre (2026-11-26).

Remplacer, retirer, ajouter un ingrédient et changer les quantités : la fiche
(nutrition, prix, allergènes, étapes) suit, la version s'enregistre ou non, et
le planning (courses, coût, bilan, batch cooking) cuisine la version choisie.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.api.routes import recipe_versions as rv
from backend.core.auth_deps import get_optional_user, get_user
from backend.core.data_io import load_catalogue_recipes
from backend.db.models import Base, RecipeVersion, User
from backend.db.session import get_db
from backend.services import recipe_edits as E

MEMBER = "membre@exemple.com"
OTHER = "autre@exemple.com"

CURRY = next(r for r in load_catalogue_recipes() if r["id"] == "curry_aubergine_sri_lanka_bf8bcd")
RID = CURRY["id"]


def _rows(recipe=CURRY):
    return [{"src": i, "orig": c["ingredient"], "ingredient": c["ingredient"],
             "quantity": c.get("quantity"), "unit": c.get("unit") if c.get("unit") in ("g", "ml") else None}
            for i, c in enumerate(recipe["composition"])]


def _row(rows, iid):
    return next(r for r in rows if r["orig"] == iid)


def _edited():
    """Courgette au lieu de l'aubergine (400 g), moins d'oignon, beurre de cacahuète au
    lieu du lait de coco, sans piment, avec 200 g de tofu."""
    rows = _rows()
    _row(rows, "eggplant_raw").update(ingredient="green_zucchini_squash_raw", quantity=400)
    _row(rows, "onion_raw")["quantity"] = 100
    _row(rows, "coconut_milk_plant").update(ingredient="peanut_butter_natural_plant", quantity=120, unit="g")
    rows = [r for r in rows if r["orig"] != "chilli_pepper_raw"]
    rows.append({"src": None, "ingredient": "tofu_plain_pre_packaged", "quantity": 200, "unit": "g"})
    return {"base": "original", "rows": rows}


@pytest.fixture
def env(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        for e in (MEMBER, OTHER):
            db.add(User(email=e, password_hash="x"))
        db.commit()

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(rv, "check_rate_limit", lambda *a, **k: None)
    who = {"email": MEMBER}
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_user] = lambda: dict(who)
    app.dependency_overrides[get_optional_user] = lambda: dict(who)
    try:
        yield TestClient(app), who, Session
    finally:
        for dep in (get_db, get_user, get_optional_user):
            app.dependency_overrides.pop(dep, None)


# ── Fiche de la version ───────────────────────────────────────────────────────

def test_sans_modification_les_valeurs_sont_celles_de_l_originale(env):
    c, _, _ = env
    original = c.get(f"/recettes/{RID}").json()
    v = c.post(f"/recettes/{RID}/personnaliser", json={"rows": _rows()}).json()
    assert v["_custom"]["changes"] == []
    for k, val in original["nutrition"].items():
        if isinstance(val, (int, float)):
            assert v["nutrition"][k] == pytest.approx(val, abs=0.02), k
    assert v["health_scores"] == original["health_scores"]
    assert v["_nutrition"] == original["_nutrition"]
    assert v["price_data"]["per_portion_eur"] == original["price_data"]["per_portion_eur"]


def test_remplacer_retirer_ajouter_et_changer_les_quantites(env):
    c, _, _ = env
    original = c.get(f"/recettes/{RID}").json()
    res = c.post(f"/recettes/{RID}/personnaliser", json=_edited())
    assert res.status_code == 200, res.text
    v = res.json()
    kinds = {(ch["kind"], ch.get("ingredient")) for ch in v["_custom"]["changes"]}
    assert ("replaced", "green_zucchini_squash_raw") in kinds
    assert ("quantity", "onion_raw") in kinds
    assert ("removed", "chilli_pepper_raw") in kinds
    assert ("added", "tofu_plain_pre_packaged") in kinds
    zuc = next(ch for ch in v["_custom"]["changes"] if ch.get("ingredient") == "green_zucchini_squash_raw")
    assert (zuc["before"], zuc["after"]) == ("500 g", "400 g")

    # composition, étapes, description
    ids = [x["ingredient"] for x in v["composition"]]
    assert "eggplant_raw" not in ids and "chilli_pepper_raw" not in ids and "tofu_plain_pre_packaged" in ids
    steps = " ".join(v["instructions"])
    assert "les courgettes" in steps and "aubergine" not in steps.lower()
    assert "100 g d'oignon" in steps and "150 g d'oignon" not in steps
    assert "120 g de beurre de cacahuète" in steps and "300 ml de lait de coco" not in steps
    assert "base de courgettes" in v["description"]
    notes = " ".join(v["_custom"]["step_notes"])
    assert "piment" in notes and "tofu" in notes.lower()

    # allergènes : arachide (beurre de cacahuète) et soja (tofu)
    assert {"peanuts", "soy"} <= set(v["tags"]["allergens"])
    assert v["diet_flags"]["nut_free"] is False
    assert v["diet_flags_enriched"]["soy_free"] is False

    # nutrition et prix recalculés
    assert v["nutrition"]["protein"] > original["nutrition"]["protein"] + 5
    assert v["nutrition"]["calories"] > original["nutrition"]["calories"]
    assert v["health_scores"]["protein_g"] > original["health_scores"]["protein_g"]
    assert v["price_data"]["per_portion_eur"] != original["price_data"]["per_portion_eur"]
    names = {x["name_fr"].lower() for x in v["ingredients_meta"].values()}
    assert "courgette" in names and "tofu" in names


def test_modifications_invalides(env):
    c, _, _ = env
    url = f"/recettes/{RID}/personnaliser"
    rows = _rows()
    bad = [dict(r) for r in rows]
    bad[0]["ingredient"] = "poulet_roti"
    assert c.post(url, json={"rows": bad}).status_code == 422          # ingrédient inconnu
    assert c.post(url, json={"rows": []}).status_code == 422
    bad = [dict(r) for r in rows]
    bad[0]["unit"] = "kg"
    assert c.post(url, json={"rows": bad}).status_code == 422
    added = rows + [{"src": None, "ingredient": "tofu_plain_pre_packaged"}]
    assert c.post(url, json={"rows": added}).status_code == 422        # ajout sans quantité
    dup = rows + [dict(rows[0])]
    dup[-1]["orig"] = None
    assert c.post(url, json={"rows": dup}).status_code == 422          # même ligne deux fois
    only_garnish = [r for r in rows if r["orig"] == "coriander_raw_fresh_herb"]
    assert c.post(url, json={"rows": only_garnish}).status_code == 422
    assert c.post("/recettes/inconnue/personnaliser", json={"rows": rows}).status_code == 404


def test_ligne_retrouvee_par_son_ingredient_si_la_recette_a_change():
    rows = _rows()
    for r in rows:
        r["src"] = (r["src"] + 1) % len(rows)       # lignes décalées (recette retouchée)
    res = E.apply_edits(CURRY, {"rows": rows})
    assert res["changes"] == []


def test_version_vegan_comme_depart():
    paneer = next(r for r in load_catalogue_recipes()
                  if not (r.get("diet_flags") or {}).get("vegan") and _vegan_ok(r))
    from backend.engine.rule_engine.variants import vegan_variant
    v = vegan_variant(paneer)["recipe"]
    res = E.apply_edits(paneer, {"base": "vegan", "rows": _rows(v)})
    assert res["changes"] == []
    assert res["recipe"]["diet_flags"]["vegan"] is True


def _vegan_ok(r):
    from backend.engine.rule_engine.variants import vegan_variant
    try:
        return vegan_variant(r)["source"] == "generated"
    except Exception:
        return False


def test_remplacements_proposes(env):
    c, _, _ = env
    res = c.get(f"/recettes/{RID}/remplacements", params={"ingredient": "eggplant_raw"}).json()
    ids = [x["id"] for x in res["results"]]
    assert ids and "eggplant_raw" not in ids
    milk = c.get(f"/recettes/{RID}/remplacements", params={"ingredient": "milk_liquid_uht_3_5pct"}).json()
    assert milk["results"][0]["reason"] == "version vegan"
    assert c.get(f"/recettes/{RID}/remplacements", params={"ingredient": "poulet"}).status_code == 404


# ── Enregistrement ────────────────────────────────────────────────────────────

def test_enregistrer_relire_lister_supprimer(env):
    c, who, _ = env
    assert c.get(f"/mes-versions/{RID}").status_code == 404
    assert c.put(f"/mes-versions/{RID}", json={"rows": _rows()}).status_code == 422   # rien de changé
    res = c.put(f"/mes-versions/{RID}", json={**_edited(), "servings": 2})
    assert res.status_code == 200, res.text
    assert res.json()["servings"] == 2 and res.json()["changes"]
    saved = c.get(f"/mes-versions/{RID}").json()
    assert saved["base"] == "original" and len(saved["rows"]) == len(_edited()["rows"])
    # la version enregistrée redonne la même fiche
    again = c.post(f"/recettes/{RID}/personnaliser", json={"base": saved["base"], "rows": saved["rows"]}).json()
    assert "tofu_plain_pre_packaged" in [x["ingredient"] for x in again["composition"]]
    # remplacer : toujours une seule version par recette
    edits = _edited()
    _row(edits["rows"], "onion_raw")["quantity"] = 80
    assert c.put(f"/mes-versions/{RID}", json=edits).status_code == 200
    mine = c.get("/mes-versions").json()["results"]
    assert len(mine) == 1 and mine[0]["title"] and any(ch.get("after") == "80 g" for ch in mine[0]["changes"])

    who["email"] = OTHER
    assert c.get(f"/mes-versions/{RID}").status_code == 404
    assert c.get("/mes-versions").json()["results"] == []
    assert c.delete(f"/mes-versions/{RID}").status_code == 404

    who["email"] = MEMBER
    assert c.delete(f"/mes-versions/{RID}").status_code == 204
    assert c.get(f"/mes-versions/{RID}").status_code == 404


def test_suppression_du_compte(env):
    c, _, Session = env
    c.put(f"/mes-versions/{RID}", json=_edited())
    with Session() as db:
        assert rv.delete_user_versions(db, MEMBER) == 1
        db.commit()
        assert db.query(RecipeVersion).count() == 0


# ── Planning ──────────────────────────────────────────────────────────────────

def _plan(entry: dict) -> dict:
    return {"lundi": {"dinner": {"servings": 4, "recipes": [entry]}}}


def test_planning_cuisine_la_version_modifiee(env):
    c, _, _ = env
    plain = {"id": RID, "title_fr": "Curry"}
    perso = {**plain, "variant": "perso", "edits": _edited()}

    # liste de courses : la courgette et le tofu, plus l'aubergine ni le piment
    shop = c.post("/planning/shopping_list", json={"plan": {"lundi": {"dinner_0": {**perso, "servings": 4}}}}).json()
    bought = {i["ingredient"] for i in shop["items"]}
    assert {"green_zucchini_squash_raw", "tofu_plain_pre_packaged"} <= bought
    assert "eggplant_raw" not in bought and "chilli_pepper_raw" not in bought
    onion = next(i for i in shop["items"] if i["ingredient"] == "onion_raw")
    assert "100" in str(onion.get("qty_str") or onion.get("quantity"))

    # coût de la semaine
    cost0 = c.post("/planning/week_cost", json={"plan": _plan(plain)}).json()
    cost1 = c.post("/planning/week_cost", json={"plan": _plan(perso)}).json()
    assert cost1["consumed_eur"] != cost0["consumed_eur"]

    # bilan de la semaine et nutrition du jour : les protéines du tofu comptent
    def protein(balance):
        return next(n["total"] for n in balance["nutrients"] if n["key"] == "protein")
    b0 = c.post("/planning/week_balance", json={"plan": _plan(plain)}).json()
    b1 = c.post("/planning/week_balance", json={"plan": _plan(perso)}).json()
    assert protein(b1) > protein(b0) + 5
    d0 = c.post("/planning/daily_nutrition", json={"plan": _plan(plain)}).json()["lundi"]
    d1 = c.post("/planning/daily_nutrition", json={"plan": _plan(perso)}).json()["lundi"]
    assert d1["protein"] > d0["protein"] + 5

    # modifications illisibles : la recette d'origine, sans erreur
    broken = {**plain, "variant": "perso", "edits": {"rows": [{"ingredient": "poulet"}]}}
    b2 = c.post("/planning/week_balance", json={"plan": _plan(broken)}).json()
    assert protein(b2) == protein(b0)
