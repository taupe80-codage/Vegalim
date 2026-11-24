"""
tests/test_diabetes.py — Règle « adapté au diabète », ingrédients à surveiller,
objectifs santé du profil (2026-11-24).

Avant : le drapeau diabetic_friendly n'était lu par aucun code, le profil ne
proposait pas l'objectif diabète, et ses objectifs (proteines, poids…) étaient
ignorés par le score (seules les clés anglaises muscle/diabete… comptaient).
"""
from __future__ import annotations

import pytest

from backend.core.data_io import load_recipes
from backend.engine.diabetes import diabetes_watch, digestible_carbs, is_diabetic_friendly
from backend.services.scoring_service import _build_context, resolve_profile


@pytest.mark.parametrize("nutrients, expected", [
    ({"carbs_g": 0.0, "sugar_g": 0.0, "fiber_g": 0.0}, True),                     # œuf, huile
    ({"carbs_g": 99.8, "polyols_g": 99.8, "sugar_g": 0.0, "fiber_g": 0.0}, True),  # xylitol
    ({"carbs_g": 72.0, "sugar_g": 1.0, "fiber_g": 2.5}, False),                    # farine T55
    ({"carbs_g": 55.7, "sugar_g": 1.2, "fiber_g": 10.6}, True),                    # avoine (10:1)
    ({"carbs_g": 99.0, "sugar_g": 99.0, "fiber_g": 0.0}, False),                   # sucre
    ({"carbs_g": 13.5, "sugar_g": 12.2, "fiber_g": 4.1}, True),                    # figue fraîche (5:1)
    ({"carbs_g": 0.0, "sugar_g": 0.0, "fiber_g": 0.0, "alcohol_g": 32.9}, False),  # eau-de-vie
    # sucres non renseignés
    ({"_source": "MANUAL", "carbs_g": 92.0, "fiber_g": 0.0}, False),              # sucre de coco
    ({"_source": "USDA", "carbs_g": 76.3, "fiber_g": 2.7}, False),                # farine de blé
    ({"_source": "USDA", "carbs_g": 6.0, "fiber_g": 2.0}, True),                  # légume
    ({"_source": "USDA", "carbs_g": 73.0, "fiber_g": 14.5}, None),                # kaki séché : inconnu
    ({"carbs_g": 10.0, "sugar_g": 2.0}, None),                                    # fibres inconnues
])
def test_regle(nutrients, expected):
    assert is_diabetic_friendly(nutrients) is expected


def test_sous_categorie_alcool_exclue():
    assert is_diabetic_friendly({"carbs_g": 0.0, "sugar_g": 0.0, "fiber_g": 0.0}, "alcohols") is False


def test_glucides_assimilables_selon_la_source():
    assert digestible_carbs({"_source": "CNF", "carbs_g": 20.0, "fiber_g": 5.0}) == 15.0
    assert digestible_carbs({"_source": "CIQUAL", "carbs_g": 20.0, "fiber_g": 5.0}) == 20.0


def _recipe(rid: str) -> dict:
    return next(r for r in load_recipes() if r["id"] == rid)


def test_ingredients_a_surveiller():
    w = diabetes_watch(_recipe("brkf_compote_rhubarbe_fraise_1d9d38"))
    assert [x["ingredient"] for x in w] == ["white_sugar"]
    assert w[0]["sugar_g"] >= 30
    # Crumble : 10 g de sucre de coco par portion (sucres ajoutés le 2026-11-24
    # à la fiche MANUAL) ; myrtilles sans fibres renseignées : pas de conclusion
    ids = {x["ingredient"] for x in diabetes_watch(_recipe("dessert_crumble_aux_myrtilles_veg_15390f"))}
    assert "coconut_sugar" in ids
    assert "blueberry_raw" not in ids


def test_seuils_par_portion():
    for r in load_recipes()[:300]:
        for x in diabetes_watch(r):
            assert x["carbs_g"] >= 10 or x["sugar_g"] >= 5, (r["id"], x)


def test_fiche_recette_expose_la_liste():
    from fastapi.testclient import TestClient
    from backend.api.main import app
    r = TestClient(app).get("/recettes/brkf_compote_rhubarbe_fraise_1d9d38")
    assert r.status_code == 200
    assert r.json()["diabetes_watch"][0]["ingredient"] == "white_sugar"


@pytest.mark.parametrize("goal, profile", [
    ("diabete", "diabetic"), ("anemie", "anemia"), ("proteines", "athlete"),
    ("energie", "athlete"), ("poids", "health_focus"), ("sante", "health_focus"),
    ("antioxidants", "health_focus"), ("cycle", "default"), ("", "default"),
])
def test_objectifs_du_profil_reconnus(goal, profile):
    assert resolve_profile("default", {"health_goal": goal}) == profile


def test_objectif_proteines_active_le_contexte():
    assert _build_context({"health_goal": "proteines"})["high_protein"] is True
    assert _build_context({"health_goal": "sante"})["high_protein"] is False
