"""
tests/test_budget_semaine.py — Semaine à budget fixe (planning).

Le planning répartit le budget en un plafond par portion
(/planning/mealplan?max_portion_cost=…) ; /planning/week_cost chiffre la
semaine (coût consommé, courses frais / produits qui se conservent).
"""
from __future__ import annotations

import random

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.data_io import load_nutrition_graph
from backend.engine.planning_engine.budget import portion_costs, week_cost
from backend.engine.planning_engine.planner import generate_plan

client = TestClient(app)


def _ids(plan):
    return [plan[d][m]["id"] for d in plan if d != "meta" for m in plan[d]]


def test_couts_par_portion_connus():
    costs = portion_costs()
    assert len(costs) > 1000
    per, complete = costs["dal_harira_822880"]
    assert complete and 0 < per < 5


def test_plafond_respecte_sans_repetition_et_vrais_repas():
    random.seed(4)
    plan = generate_plan(dish_type="main", max_portion_cost=1.0, month=11)
    assert "error" not in plan["meta"]
    ids = _ids(plan)
    costs, ng = portion_costs(), load_nutrition_graph()
    assert len(set(ids)) == 14
    for d in plan:
        if d == "meta":
            continue
        for m in plan[d]:
            rid = plan[d][m]["id"]
            assert plan[d][m]["cost_per_portion"] == costs[rid][0] <= 1.0
            assert ng[rid]["protein"] >= 10 and ng[rid]["calories"] >= 250


def test_budget_trop_serre_donne_le_minimum():
    res = client.get("/planning/mealplan?dish_type=main&max_portion_cost=0.2")
    assert res.status_code == 200
    meta = res.json()["meta"]
    assert meta["error"] == "budget_too_low" and meta["min_portion_cost"] > 0.2
    # au minimum indiqué, la semaine se compose
    ok = client.get(f"/planning/mealplan?dish_type=main&max_portion_cost={meta['min_portion_cost']}").json()
    assert "error" not in ok["meta"] and len(set(_ids(ok))) == 14


def test_cout_de_la_semaine():
    random.seed(2)
    p = generate_plan(dish_type="main", month=11)
    plan = {d: {"breakfast": {"skip": True, "recipes": [{"id": "dal_harira_822880"}]},
                "lunch": {"servings": 2, "recipes": [{"id": p[d]["lunch"]["id"]}]},
                "dinner": {"servings": 3, "recipes": [{"id": p[d]["dinner"]["id"]}]}}
            for d in p if d != "meta"}
    res = week_cost(plan)
    costs = portion_costs()
    expected = sum(costs[p[d]["lunch"]["id"]][0] * 2 + costs[p[d]["dinner"]["id"]][0] * 3
                   for d in p if d != "meta")
    assert res["portions"] == 35                       # le petit-déjeuner sauté ne compte pas
    assert abs(res["consumed_eur"] - expected) < 0.05
    assert abs(res["shopping_fresh_eur"] + res["shopping_keeps_eur"] - res["shopping_eur"]) < 0.05
    assert res["shopping_fresh_eur"] > 0 and res["shopping_keeps_eur"] > 0
    r = client.post("/planning/week_cost", json={"plan": plan})
    assert r.status_code == 200 and r.json()["portions"] == 35


def test_semaine_vide():
    assert week_cost({})["portions"] == 0
