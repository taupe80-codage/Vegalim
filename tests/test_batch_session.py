"""
tests/test_batch_session.py — Session de batch cooking (planning).

backend/engine/planning_engine/batch.py : la semaine planifiée devient une
session du dimanche (trempage, cuissons, préparations maison, légumes),
avec conservation prudente et part à congeler ou à préparer plus tard.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.data_io import load_catalogue_recipes
from backend.engine.planning_engine.batch import DAYS, batch_session

client = TestClient(app)
RECIPES = load_catalogue_recipes()


def _with(token: str, dish: str = "main"):
    return next(r for r in RECIPES if r.get("dish_type") == dish
                and any(c.get("ingredient") == token and isinstance(c.get("quantity"), (int, float))
                        and (c.get("meta") or {}).get("role") != "serving_suggestion"
                        for c in r.get("composition") or []))


def _plan(entries: dict[str, str], servings: int = 2) -> dict:
    """{jour: id} → planning, déjeuner seulement."""
    return {d: {"lunch": {"servings": servings, "recipes": [{"id": rid}]}} for d, rid in entries.items()}


def _items(res, step_id):
    return next(s for s in res["steps"] if s["id"] == step_id)["items"]


def test_pois_chiches_secs_trempes_la_veille_et_cuits():
    r = _with("chickpea_raw_dried")
    res = batch_session(_plan({"lundi": r["id"]}))
    assert [e["key"] for e in res["eve"]] == ["chickpea_raw_dried"]
    leg = _items(res, "legumes")[0]
    assert leg["soak"] and leg["cook_min"] >= 60 and leg["cooked_grams"] > leg["grams"]


def test_riz_cuit_24_h_puis_congele():
    r = _with("basmati_rice_raw_seed")
    res = batch_session(_plan({"lundi": r["id"], "jeudi": r["id"]}))
    rice = next(i for i in _items(res, "grains") if i["key"] == "basmati_rice_raw_seed")
    assert rice["storage"]["fridge_days"] == 1
    assert rice["storage"]["late_days"] == ["jeudi"] and rice["freeze_grams"] > 0


def test_legumes_tailles_3_jours_le_reste_plus_tard():
    r = _with("carrot_raw")
    res = batch_session(_plan({"lundi": r["id"], "vendredi": r["id"]}))
    carrot = next(i for i in _items(res, "veg") if i["key"] == "carrot_raw")
    later = next(x for x in res["later"] if x["key"] == "carrot_raw")
    assert carrot["grams"] > 0 and carrot["later_grams"] == later["grams"] > 0
    assert later["days"] == ["vendredi"]


def test_quantites_a_l_echelle_des_portions():
    r = _with("carrot_raw")
    base = int(r.get("servings") or 4)
    one = batch_session(_plan({"lundi": r["id"]}, servings=base))
    two = batch_session(_plan({"lundi": r["id"]}, servings=base * 2))
    g1 = next(i for i in _items(one, "veg") if i["key"] == "carrot_raw")["grams"]
    g2 = next(i for i in _items(two, "veg") if i["key"] == "carrot_raw")["grams"]
    assert abs(g2 - 2 * g1) <= 1


def test_preparations_maison_et_epices_exclues():
    r = next(x for x in RECIPES if x.get("dish_type") == "main"
             and any(str(c.get("ingredient", "")).startswith("base_") for c in x.get("composition") or []))
    res = batch_session(_plan({"mardi": r["id"]}))
    assert _items(res, "bases")
    keys = {i["key"] for s in res["steps"] for i in s["items"]}
    assert not any("powder" in k or "juice" in k for k in keys)


def test_route_et_planning_vide():
    assert batch_session({})["meals"] == 0
    r = client.post("/planning/batch_session", json={"plan": _plan({d: _with("carrot_raw")["id"] for d in DAYS[:3]})})
    assert r.status_code == 200 and r.json()["meals"] == 3
