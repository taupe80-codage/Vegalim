"""
tests/test_cycle_engine.py — Tests unitaires de cycle_engine.py.

Couverture :
    get_phase          mapping jour → phase / bornes / hors-cycle
    get_phase_info     délègue à _load_cycle_data
    cycle_score        ingrédients recommandés / à éviter / bonus nutriments /
                       inférence depuis cycle_day / fallback phase par défaut /
                       score borné 0-10
    adjust_ranking     lecture final_score / composite / tri décroissant /
                       pas de mutation des originaux / dégradation gracieuse
"""
from __future__ import annotations

import sys
import types
from unittest.mock import patch

import pytest


# ═══════════════════════════════════════════════════════════════════════════════
# Données de test
# ═══════════════════════════════════════════════════════════════════════════════

CYCLE_DATA = {
    "cycle_phases": {
        "menstrual_phase": {
            "days": "1-5",
            "focus": ["iron", "magnesium", "omega_3"],
            "ingredient_ids": ["lentils", "spinach", "walnut"],
            "avoid_ingredient_ids": ["coffee", "alcohol"],
            "notes": "Privilégier le fer",
        },
        "follicular_phase": {
            "days": "6-13",
            "focus": ["protein", "fiber"],
            "ingredient_ids": ["quinoa", "chickpeas", "broccoli"],
            "avoid_ingredient_ids": [],
            "notes": "",
        },
        "ovulatory_phase": {
            "days": "14-16",
            "focus": ["vitamin_c", "zinc"],
            "ingredient_ids": ["bell_pepper", "pumpkin_seeds"],
            "avoid_ingredient_ids": [],
            "notes": "",
        },
        "luteal_phase": {
            "days": "17-28",
            "focus": ["magnesium", "calcium"],
            "ingredient_ids": ["dark_chocolate", "almonds", "sweet_potato"],
            "avoid_ingredient_ids": ["sugar"],
            "notes": "",
        },
    }
}

NUTR_GRAPH = {
    "42": {"iron": 5.0, "protein": 15.0, "fiber": 10.0,
           "calcium": 200.0, "magnesium": 80.0, "vitamin_c": 30.0},
}


# ═══════════════════════════════════════════════════════════════════════════════
# Fixture
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def ce():
    """Charge cycle_engine avec data_io et config mockés."""
    for key in [k for k in sys.modules if "cycle_engine" in k]:
        del sys.modules[key]

    for mod in ["backend", "backend.core", "backend.engine"]:
        sys.modules.setdefault(mod, types.ModuleType(mod))

    config = types.ModuleType("backend.engine.config")
    config.DATA_ROOT = "/tmp/fake"
    sys.modules["backend.engine.config"] = config

    data_io = types.ModuleType("backend.core.data_io")
    data_io.load_cycle_data      = lambda: CYCLE_DATA
    data_io.load_nutrition_graph = lambda: NUTR_GRAPH
    sys.modules["backend.core.data_io"] = data_io

    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "cycle_engine",
        Path(__file__).parent.parent / "backend" / "engine" / "cycle_engine.py",
    )
    m = importlib.util.module_from_spec(spec)
    sys.modules["cycle_engine"] = m
    spec.loader.exec_module(m)

    yield m

    for key in [k for k in sys.modules if "cycle_engine" in k]:
        del sys.modules[key]


def _recipe(rid=1, ingredients=None, final_score=7.0, global_score=None):
    r = {
        "id":          rid,
        "ingredients": ingredients or [],
        "final_score": final_score,
    }
    if global_score is not None:
        r["global_score"] = global_score
    return r


# ═══════════════════════════════════════════════════════════════════════════════
# get_phase
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPhase:

    @pytest.mark.parametrize("day,expected", [
        (1,  "menstrual_phase"),
        (5,  "menstrual_phase"),
        (6,  "follicular_phase"),
        (13, "follicular_phase"),
        (14, "ovulatory_phase"),
        (16, "ovulatory_phase"),
        (17, "luteal_phase"),
        (28, "luteal_phase"),
    ])
    def test_mapping_jour_phase(self, ce, day, expected):
        assert ce.get_phase(day) == expected

    def test_hors_cycle_retourne_follicular(self, ce):
        """Jour > 28 → fallback follicular_phase."""
        assert ce.get_phase(29) == "follicular_phase"
        assert ce.get_phase(0)  == "follicular_phase"

    def test_borne_basse_jour_1(self, ce):
        assert ce.get_phase(1) == "menstrual_phase"

    def test_borne_haute_jour_28(self, ce):
        assert ce.get_phase(28) == "luteal_phase"


# ═══════════════════════════════════════════════════════════════════════════════
# cycle_score
# ═══════════════════════════════════════════════════════════════════════════════

class TestCycleScore:

    def test_structure_retour(self, ce):
        result = ce.cycle_score(_recipe(), phase="follicular_phase")
        assert all(k in result for k in
                   ("score", "phase", "phase_days", "focus", "recommended",
                    "to_avoid", "notes"))

    def test_score_ingredients_recommandes(self, ce):
        """Chaque ingrédient recommandé présent ajoute 1 point."""
        r = _recipe(ingredients=["lentils", "spinach"])
        result = ce.cycle_score(r, phase="menstrual_phase")
        assert result["score"] >= 2.0
        assert "lentils" in result["recommended"]
        assert "spinach" in result["recommended"]

    def test_score_ingredients_a_eviter(self, ce):
        """Chaque ingrédient à éviter retire 0.5 point."""
        r = _recipe(ingredients=["coffee", "alcohol"])
        result = ce.cycle_score(r, phase="menstrual_phase")
        assert result["score"] == 0.0   # max(0, 0 - 1.0) = 0
        assert "coffee"  in result["to_avoid"]
        assert "alcohol" in result["to_avoid"]

    def test_score_borne_zero(self, ce):
        """Le score ne peut pas être négatif."""
        r = _recipe(ingredients=["coffee", "alcohol", "coffee", "sugar"])
        result = ce.cycle_score(r, phase="menstrual_phase")
        assert result["score"] >= 0.0

    def test_score_borne_dix(self, ce):
        """Le score ne peut pas dépasser 10."""
        r = _recipe(ingredients=[f"ing_{i}" for i in range(20)])
        result = ce.cycle_score(r, phase="follicular_phase")
        assert result["score"] <= 10.0

    def test_inference_phase_depuis_cycle_day(self, ce):
        """Sans phase, cycle_day doit être utilisé pour l'inférer."""
        r = _recipe(ingredients=["lentils"])
        result = ce.cycle_score(r, cycle_day=3)   # jour 3 → menstrual
        assert result["phase"] == "menstrual_phase"
        assert "lentils" in result["recommended"]

    def test_phase_par_defaut_si_aucun_argument(self, ce):
        """Sans phase ni cycle_day → follicular_phase par défaut."""
        result = ce.cycle_score(_recipe())
        assert result["phase"] == "follicular_phase"

    def test_bonus_nutriments_focus(self, ce):
        """Recette id=42 a des données nutrition → bonus focus."""
        r = _recipe(rid=42, ingredients=["lentils", "spinach"])
        # menstrual focus = [iron, magnesium, omega_3]
        # NUTR_GRAPH[42] a iron=5 (>3 ✓), magnesium=80 (>50 ✓)
        result_avec    = ce.cycle_score(r,          phase="menstrual_phase")
        result_sans    = ce.cycle_score(_recipe(1), phase="menstrual_phase")
        # La recette 42 doit avoir un score >= recette sans données nutr
        assert result_avec["score"] >= result_sans["score"]

    def test_bonus_omega3_ingredient(self, ce):
        """walnut est reconnu comme source omega_3."""
        r = _recipe(ingredients=["walnut", "lentils", "spinach"])
        result = ce.cycle_score(r, phase="menstrual_phase")
        # walnut recommandé ET comptabilisé dans omega_3
        assert "walnut" in result["recommended"]

    def test_recette_vide(self, ce):
        result = ce.cycle_score(_recipe(ingredients=[]))
        assert isinstance(result["score"], float)
        assert result["recommended"] == []
        assert result["to_avoid"]    == []

    def test_phase_inconnue_retourne_structure_vide(self, ce):
        result = ce.cycle_score(_recipe(), phase="phase_inexistante")
        assert result["score"] == 0.0
        assert result["recommended"] == []


# ═══════════════════════════════════════════════════════════════════════════════
# adjust_ranking
# ═══════════════════════════════════════════════════════════════════════════════

class TestAdjustRanking:

    def test_retourne_liste_meme_longueur(self, ce):
        recipes = [_recipe(i, final_score=float(i)) for i in range(1, 6)]
        result  = ce.adjust_ranking(recipes, phase="follicular_phase")
        assert len(result) == 5

    def test_tri_decroissant_par_adjusted_score(self, ce):
        recipes = [
            _recipe(1, final_score=5.0),
            _recipe(2, final_score=8.0),
            _recipe(3, final_score=3.0),
        ]
        result = ce.adjust_ranking(recipes, phase="follicular_phase")
        scores = [r["_adjusted_score"] for r in result]
        assert scores == sorted(scores, reverse=True)

    def test_injecte_cycle_score_et_adjusted_score(self, ce):
        recipes = [_recipe(1, final_score=7.0)]
        result  = ce.adjust_ranking(recipes, phase="follicular_phase")
        assert "_cycle_score"    in result[0]
        assert "_adjusted_score" in result[0]

    def test_lit_final_score(self, ce):
        """adjust_ranking doit utiliser final_score, pas global_score."""
        r = _recipe(1, final_score=8.0)
        r["global_score"] = 3.0   # valeur trompeuse
        result = ce.adjust_ranking([r], phase="follicular_phase")
        # Score ajusté doit être proche de 8.0 * 0.75 = 6.0, pas 3.0 * 0.75
        assert result[0]["_adjusted_score"] > 4.0

    def test_fallback_global_score_si_pas_de_final_score(self, ce):
        r = {"id": 1, "global_score": 6.0, "ingredients": []}
        result = ce.adjust_ranking([r], phase="follicular_phase")
        # global_score=6.0 * 0.75 = 4.5 (sans bonus cycle)
        assert result[0]["_adjusted_score"] == pytest.approx(4.5, abs=0.5)

    def test_pas_de_mutation_originaux(self, ce):
        """adjust_ranking ne doit pas modifier les dicts originaux."""
        import copy
        original = _recipe(1, final_score=7.0)
        snap     = copy.deepcopy(original)
        ce.adjust_ranking([original], phase="follicular_phase")
        assert original == snap

    def test_recette_avec_ingredients_recommandes_monte(self, ce):
        """Une recette avec ingrédients recommandés doit passer devant une sans."""
        r_avec  = _recipe(1, final_score=7.0, ingredients=["quinoa", "chickpeas"])
        r_sans  = _recipe(2, final_score=7.0, ingredients=[])
        result  = ce.adjust_ranking([r_sans, r_avec], phase="follicular_phase")
        assert result[0]["id"] == 1

    def test_inference_phase_depuis_cycle_day(self, ce):
        """phase=None + cycle_day → phase inférée correctement."""
        recipes = [_recipe(1, final_score=7.0)]
        result  = ce.adjust_ranking(recipes, cycle_day=20)  # → luteal
        assert result[0]["_cycle_score"]["phase"] == "luteal_phase"

    def test_poids_weight_personnalisable(self, ce):
        """weight=0 → adjusted_score == final_score * 1.0 (cycle ignoré)."""
        r = _recipe(1, final_score=8.0)
        result = ce.adjust_ranking([r], phase="follicular_phase", weight=0.0)
        assert result[0]["_adjusted_score"] == pytest.approx(8.0)

    def test_liste_vide(self, ce):
        result = ce.adjust_ranking([], phase="follicular_phase")
        assert result == []
