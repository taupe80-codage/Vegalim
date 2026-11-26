"""
tests/test_week_carbon.py — Empreinte carbone de la semaine planifiée (2026-11-26).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.data_io import load_catalogue_recipes
from backend.services.week_carbon import portion_carbon, week_carbon

client = TestClient(app)
MOUSSAKA = "tarte_moussaka_veg_d55fa8"
CURRY = "curry_aubergine_sri_lanka_bf8bcd"


def _plan(*entries, servings=2):
    days = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    return {days[i]: {"dinner": {"servings": servings, "recipes": [e]}} for i, e in enumerate(entries)}


def test_total_et_portions():
    w = week_carbon(_plan({"id": CURRY}, {"id": MOUSSAKA}), month=11)
    pc = portion_carbon(11)
    assert w["portions"] == 4 and w["n_meals"] == 2
    assert w["total_kg"] == pytest.approx(2 * pc[CURRY] + 2 * pc[MOUSSAKA], abs=0.02)
    assert w["catalogue_avg_kg"] and 0.1 < w["catalogue_avg_kg"] < 2
    assert w["top_meals"][0]["id"] == MOUSSAKA                 # la plus émettrice d'abord


def test_alternatives_moins_emettrices_du_meme_type():
    w = week_carbon(_plan({"id": MOUSSAKA}), month=11)
    top = w["top_meals"][0]
    types = {r["id"]: r.get("dish_type") for r in load_catalogue_recipes()}
    for alt in top["alternatives"]:
        assert alt["per_portion_kg"] <= top["per_portion_kg"] * 0.6
        assert types[alt["id"]] == types[MOUSSAKA]
    milk = next((i for i in w["top_ingredients"] if i["id"] == "milk_liquid_uht_3_5pct"), None)
    if milk:
        assert milk["lower"] and all("lait" in x["name_fr"] for x in milk["lower"])


def test_hors_saison_et_versions():
    tomato_recipe = next(r["id"] for r in load_catalogue_recipes()
                         if any(c.get("ingredient") == "tomato_raw_ripe" and (c.get("quantity") or 0) >= 200
                                for c in r.get("composition") or []))
    nov = week_carbon(_plan({"id": tomato_recipe}), month=11)
    jul = week_carbon(_plan({"id": tomato_recipe}), month=7)
    assert any(x["id"] == "tomato_raw_ripe" for x in nov["off_season"]) and not jul["off_season"]
    assert nov["total_kg"] > jul["total_kg"]
    # version modifiée : sans la tomate, l'empreinte baisse
    r = next(x for x in load_catalogue_recipes() if x["id"] == tomato_recipe)
    rows = [{"src": i, "orig": c["ingredient"], "ingredient": c["ingredient"], "quantity": c.get("quantity"),
             "unit": c.get("unit") if c.get("unit") in ("g", "ml") else None}
            for i, c in enumerate(r["composition"]) if c["ingredient"] != "tomato_raw_ripe"]
    perso = week_carbon(_plan({"id": tomato_recipe, "variant": "perso", "edits": {"rows": rows}}), month=11)
    assert perso["total_kg"] < nov["total_kg"]


def test_route():
    res = client.post("/planning/week_carbon", json={"plan": _plan({"id": CURRY})})
    assert res.status_code == 200 and res.json()["n_meals"] == 1
    assert client.post("/planning/week_carbon", json={"plan": {}}).json()["n_meals"] == 0
