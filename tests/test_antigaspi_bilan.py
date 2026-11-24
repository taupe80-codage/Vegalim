"""
tests/test_antigaspi_bilan.py — Anti-gaspillage du planning et bilan de la semaine.

- L'anti-gaspillage lisait recipe["ingredients"] (champ absent) : il n'avait
  jamais agi. Il porte désormais sur les ingrédients qui se gâchent.
- Le bilan de la semaine compare les apports aux repas réellement planifiés
  (et non à AJR × 7), signale manques et excès et propose des recettes.
"""
from __future__ import annotations

import random
import statistics
from collections import Counter

from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.data_io import load_recipes
from backend.engine.planning_engine import planner
from backend.services import week_balance as wb

client = TestClient(app)
RECIPES = {r["id"]: r for r in load_recipes()}
DAYS = wb.DAYS


# ── Anti-gaspillage ──────────────────────────────────────────────────────────

def test_ingredients_qui_se_gachent_seulement():
    r = {"composition": [
        {"ingredient": "coconut_milk_plant", "quantity": 200, "unit": "ml", "meta": {"role": "liquid"}},
        {"ingredient": "table_salt_unenriched", "quantity": 3, "unit": "g", "meta": {"role": "seasoning"}},
        {"ingredient": "olive_oil_plant", "quantity": 15, "unit": "ml", "meta": {"role": "fat"}},
        {"ingredient": "coriander_raw_fresh_herb", "quantity": 10, "unit": "g", "meta": {"role": "herb"}},
    ]}
    p = planner._perishables(r)
    assert "coconut_milk_plant" in p and p["coriander_raw_fresh_herb"] == "fresh_herb"
    assert "table_salt_unenriched" not in p and "olive_oil_plant" not in p


def test_bonus_de_reutilisation_non_nul():
    """Régression : le bonus valait 0 pour toutes les recettes."""
    r = next(x for x in RECIPES.values()
             if any(c.get("ingredient") == "coconut_milk_plant" for c in x.get("composition") or []))
    assert planner._reuse_score(r, Counter()) == 0
    assert planner._reuse_score(r, Counter({"coconut_milk_plant": 1})) > 0


def _week_stats(anti: bool, seeds=range(10)) -> tuple[float, float]:
    """(produits frais différents, produits frais servant plusieurs fois)."""
    distinct, reused = [], []
    for sd in seeds:
        random.seed(sd)
        p = planner.generate_plan(dish_type="main", diversity=0.5, month=11, anti_waste=anti)
        ids = [p[d][m]["id"] for d in p if d != "meta" for m in p[d]]
        c = Counter(k for i in ids for k in planner._perishables(RECIPES[i]))
        distinct.append(len(c))
        reused.append(sum(1 for v in c.values() if v > 1))
    return statistics.mean(distinct), statistics.mean(reused)


def test_anti_gaspillage_reutilise_les_produits_entames():
    d_off, r_off = _week_stats(False)
    d_on, r_on = _week_stats(True)
    assert r_on > r_off + 3          # +49 % mesuré sur 20 semaines
    assert d_on < d_off              # moins de produits frais différents à acheter


def test_produits_secs_hors_anti_gaspillage():
    r = {"composition": [{"ingredient": "red_lentil_dried", "quantity": 200, "unit": "g", "meta": {}},
                         {"ingredient": "cumin_spice_seed", "quantity": 3, "unit": "g", "meta": {}},
                         {"ingredient": "coconut_milk_plant", "quantity": 100, "unit": "ml", "meta": {"role": "fat"}}]}
    assert list(planner._perishables(r)) == ["coconut_milk_plant"]


def test_route_mealplan_accepte_anti_waste():
    for v in ("true", "false"):
        r = client.get(f"/planning/mealplan?dish_type=main&anti_waste={v}")
        assert r.status_code == 200 and "lundi" in r.json()


# ── Bilan de la semaine ──────────────────────────────────────────────────────

def _plan(meals=("lunch", "dinner"), dish="main", n=14, skip_breakfast=True):
    ids = [i for i, r in RECIPES.items() if r.get("dish_type") == dish][:n]
    plan, k = {}, 0
    for d in DAYS:
        plan[d] = {"breakfast": {"skip": skip_breakfast, "recipes": []}}
        for m in meals:
            plan[d][m] = {"skip": False, "recipes": [{"id": ids[k % len(ids)]}]}
            k += 1
    return plan, ids


def test_objectifs_rapportes_aux_repas_planifies():
    plan, _ = _plan()
    res = wb.balance(plan)
    assert res["meals"] == {"breakfast": 0, "lunch": 7, "dinner": 7}
    assert res["days_equivalent"] == 5.25               # 14 × 37,5 %
    prot = next(n for n in res["nutrients"] if n["key"] == "protein")
    assert prot["target"] == round(50 * 5.25, 1)        # et non 50 × 7


def test_planning_vide():
    assert wb.balance({})["n_meals"] == 0
    r = client.post("/planning/week_balance", json={"plan": {}})
    assert r.status_code == 200 and r.json()["n_meals"] == 0


def test_manques_avec_recettes_hors_planning():
    plan, ids = _plan()
    res = client.post("/planning/week_balance", json={"plan": plan}).json()
    assert res["gaps"], "un planning de plats seuls manque au moins de vitamine D"
    assert [g["pct"] for g in res["gaps"]] == sorted(g["pct"] for g in res["gaps"])
    proposed = [r["id"] for g in res["gaps"] for r in g["recipes"]]
    assert proposed and not set(proposed) & set(ids)
    assert len(proposed) == len(set(proposed))          # pas de doublon d'un manque à l'autre
    vit_d = next((g for g in res["gaps"] if g["key"] == "vitamin_d"), None)
    assert vit_d is None or vit_d["recipes"] == []      # le soleil, pas une recette
    for g in res["gaps"]:
        for r in g["recipes"]:
            assert r["amount"] > 0


def test_vegan_recettes_vegan_et_pas_de_b12():
    plan, _ = _plan()
    res = wb.balance(plan, diet="vegan")
    for g in res["gaps"]:
        for r in g["recipes"]:
            assert (RECIPES[r["id"]].get("diet_flags") or {}).get("vegan")
        if g["key"] == "vitamin_b12":
            assert g["recipes"] == [] and "complément" in g["tip"]


def test_creneaux_sautes_ignores():
    plan, _ = _plan()
    for d in DAYS:
        plan[d]["dinner"]["skip"] = True
    res = wb.balance(plan)
    assert res["meals"]["dinner"] == 0 and res["meals"]["lunch"] == 7
    assert abs(res["days_equivalent"] - 7 * 0.375) < 0.01
