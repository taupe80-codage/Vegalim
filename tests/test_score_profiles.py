"""
tests/test_score_profiles.py — Chaque objectif du profil oriente le classement
dans le bon sens (revue du 2026-11-24).

Constaté avant correction, sur les 40 premières recettes :
- diabète : bonus « IG bas » pour 100 % des plats (indice glycémique absent des
  données), plus de glucides que la moyenne du catalogue ;
- poids : 470 kcal en tête contre 355 en moyenne (profil santé générique) ;
- antioxydants : aucun critère propre, vitamine E à 0 partout ;
- anémie : 5,4 mg de fer contre 4,9 sans objectif.
"""
from __future__ import annotations

import logging
import statistics

import pytest

from backend.core.data_io import load_nutrition_graph, load_recipes
from backend.engine.score_engine.quality import _check_rule
from backend.services.scoring_service import score_recipe

TOP = 30


@pytest.fixture(scope="module")
def ranking():
    logging.disable(logging.WARNING)
    recipes = [r for r in load_recipes() if not str(r["id"]).startswith("base_")][:500]
    ng = load_nutrition_graph()

    def top(goal: str) -> list[dict]:
        scored = sorted(((score_recipe(r, profile_data={"health_goal": goal})["adaptive_score"], str(r["id"]))
                         for r in recipes), reverse=True)
        return [ng[rid] for _, rid in scored[:TOP]]

    cache: dict[str, list[dict]] = {}
    yield lambda goal: cache.setdefault(goal, top(goal))
    logging.disable(logging.NOTSET)


def _mean(rows: list[dict], field: str) -> float:
    return statistics.mean(float(r.get(field) or 0) for r in rows)


def test_diabete_moins_de_glucides_rapides(ranking):
    assert _mean(ranking("diabete"), "fast_carbs") < 0.5 * _mean(ranking(""), "fast_carbs")


def test_poids_moins_calorique(ranking):
    assert _mean(ranking("poids"), "calories") < _mean(ranking("sante"), "calories")
    assert _mean(ranking("poids"), "calories") <= _mean(ranking(""), "calories")


def test_antioxydants_plus_de_vitamines(ranking):
    # vitamine E : effet plus faible (+16 % mesuré), les plats riches en huile
    # ou en oléagineux sont déjà bien classés par défaut
    for field, factor in (("vitamin_c", 1.2), ("vitamin_a", 1.2), ("vitamin_e", 1.1)):
        assert _mean(ranking("antioxidants"), field) > factor * _mean(ranking(""), field), field


def test_anemie_plus_de_fer(ranking):
    assert _mean(ranking("anemie"), "iron") > 1.15 * _mean(ranking(""), "iron")


def test_proteines_plus_de_proteines(ranking):
    assert _mean(ranking("proteines"), "protein") > 1.2 * _mean(ranking(""), "protein")


def test_regle_sans_valeur_non_appliquee():
    """Avant : valeur absente lue comme 0 → « IG ≤ 55 » vrai pour tout le monde."""
    rule = {"field": "glycemic_index", "op": "<=", "value": 55}
    assert _check_rule(rule, {}) is False
    assert _check_rule(rule, {"glycemic_index": None}) is False
    assert _check_rule(rule, {"glycemic_index": 40}) is True


def test_graphe_nutrition_glucides_rapides_et_vitamines():
    ng = load_nutrition_graph()
    assert all(isinstance(v.get("fast_carbs"), (int, float)) for v in ng.values())
    vit_e = [float(v.get("vitamin_e") or 0) for v in ng.values()]
    assert statistics.median(vit_e) > 1.0            # 0 partout avant
    assert sum(1 for x in vit_e if x == 0) < 100


def test_filtre_glycemie_ne_garde_pas_tout():
    from backend.services.filter_service import apply_filters
    recipes = load_recipes()
    _, low = apply_filters(recipes, low_ig=True, limit=len(recipes))
    _, moderate = apply_filters(recipes, moderate_ig=True, limit=len(recipes))
    assert 0 < low < moderate < len(recipes)


def test_vitamine_a_et_folates_par_repli():
    """CNF : bêta-carotène sans équivalent rétinol ; folates totaux sans DFE."""
    from backend.engine.nutrition_engine import _normalize_n_data
    n = _normalize_n_data({"beta_carotene_ug": 1200.0, "retinol_ug": 0.0, "folate_ug": 50.0,
                           "alpha_tocopherol_mg": 2.0})
    assert n["vitamin_a"] == 100.0 and n["folate"] == 50.0 and n["vitamin_e"] == 2.0
    n = _normalize_n_data({"vitamin_a_rae_ug": 300.0, "beta_carotene_ug": 1200.0,
                           "folate_dfe_ug": 80.0, "folate_ug": 50.0})
    assert n["vitamin_a"] == 300.0 and n["folate"] == 80.0
