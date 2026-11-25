"""
tests/test_equipment_dish_types.py — Matériel déduit des étapes et reclassement
des « plats » qui n'en sont pas (2026-11-25).
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.data_io import load_catalogue_recipes, load_nutrition_graph, is_component_recipe
from backend.engine.equipment import recipe_equipment, needs_oven, needs_blender

client = TestClient(app)
RECIPES = load_catalogue_recipes()


def _r(steps, equipment=None, rid=""):
    return {"id": rid, "instructions": steps, "equipment": equipment or []}


def test_materiel_deduit_des_etapes():
    assert needs_oven(_r(["Préchauffer le four à 180 °C."]))
    assert needs_oven(_r(["Enfourner 25 minutes."]))
    assert not needs_oven(_r(["Servir avec une fourchette."]))
    assert needs_blender(_r(["Mixer finement la soupe."]))
    assert not needs_blender(_r(["Mélanger les légumes."]))
    assert recipe_equipment(_r(["Faire revenir dans une poêle, puis mijoter en cocotte."])) == ["poêle", "cocotte"]


def test_materiel_declare_complete_le_texte():
    assert needs_oven(_r(["Assembler."], equipment=["plat_gratin"]))


def test_filtre_sans_four_liste_et_recherche():
    all_ = client.get("/recettes?limit=600").json()
    no_oven = client.get("/recettes?limit=600&no_oven=true").json()
    assert 0 < no_oven["total"] < all_["total"]
    ids = {r["id"] for r in no_oven["results"]}
    assert not any(needs_oven(r) for r in RECIPES if r["id"] in ids)
    s = client.post("/recettes/recherche", json={"query": "gratin", "no_oven": True, "no_blender": True, "limit": 50}).json()
    for r in (s.get("results") or s.get("recipes") or []):
        full = next(x for x in RECIPES if x["id"] == r["id"])
        assert not needs_oven(full) and not needs_blender(full)


def test_fiche_affiche_le_materiel():
    d = client.get("/recettes/dal_harira_822880").json()
    assert "casserole" in d["equipment_needed"]


def test_planning_sans_four():
    plan = client.get("/planning/mealplan?dish_type=main&no_oven=true").json()
    ids = [plan[d][m]["id"] for d in plan if d != "meta" for m in plan[d]]
    assert ids and not any(needs_oven(r) for r in RECIPES if r["id"] in ids)


def test_plus_de_plat_principal_sans_repas():
    """Un plat principal apporte au moins 6 g de protéines ou 300 kcal, sauf
    les deux plats uniques gardés exprès (curry japonais, pancit)."""
    ng = load_nutrition_graph()
    keep = {"curry_japanese_4533d1", "rice_pancit_bfd33e"}
    thin = [r["id"] for r in RECIPES if r.get("dish_type") == "main" and not is_component_recipe(r)
            and (ng.get(r["id"], {}).get("protein") or 0) < 6 and (ng.get(r["id"], {}).get("calories") or 0) < 300
            and r["id"] not in keep]
    assert not thin, thin
    by_id = {r["id"]: r for r in RECIPES}
    assert by_id["stew_ratatouille_k8d2p4"]["dish_type"] == "side"
    assert by_id["main_pozole_82d096"]["dish_type"] == "soup"
