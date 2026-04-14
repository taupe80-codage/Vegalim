"""
tests/test_engines.py — Tests fonctionnels des engines.

Couvre : nutrition_engine, graph_engine, filter_service, substitution_service.
Aucune dépendance réseau ni base de données.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.engine.nutrition_engine   import compute_nutrition
from backend.engine.graph_engine       import _load_graph, get_cycle_ingredients
from backend.services.filter_service   import apply_diet_filter, filter_recipes
from backend.services.substitution_service import apply_substitutions


# ── Fixtures ──────────────────────────────────────────────────────────────────

RECIPE_VEGAN = {
    "id": 1, "title_fr": "Salade de lentilles",
    "ingredients": [{"ingredient_id": "lentils"}, {"ingredient_id": "carrot"}],
    "composition": [
        {"ingredient": "lentils", "quantity": 150, "unit": "g", "optional": False},
        {"ingredient": "carrot",  "quantity": 100, "unit": "g", "optional": False},
    ],
    "diet_flags": {"vegan": True, "vegetarian": True},
    "servings": 2,
}

RECIPE_DAIRY = {
    "id": 2, "title_fr": "Gratin dauphinois",
    "ingredients": [{"ingredient_id": "pommes_de_terre"}, {"ingredient_id": "creme"}],
    "composition": [
        {"ingredient": "pommes_de_terre", "quantity": 300, "unit": "g", "optional": False},
        {"ingredient": "creme",           "quantity": 100, "unit": "ml", "optional": False},
    ],
    "diet_flags": {"vegan": False, "vegetarian": True},
    "servings": 4,
}

SAMPLE = [RECIPE_VEGAN, RECIPE_DAIRY]


# ── nutrition_engine ──────────────────────────────────────────────────────────

def test_compute_nutrition_retourne_dict():
    r = compute_nutrition(RECIPE_VEGAN)
    assert isinstance(r, dict)

def test_compute_nutrition_a_calories():
    r = compute_nutrition(RECIPE_VEGAN)
    assert "calories" in r
    assert isinstance(r.get("calories", 0), (int, float))

def test_compute_nutrition_positif():
    r = compute_nutrition(RECIPE_VEGAN)
    assert r.get("calories", 0) >= 0

def test_compute_nutrition_recette_vide():
    r = compute_nutrition({"composition": [], "servings": 2})
    assert isinstance(r, dict)


# ── graph_engine ──────────────────────────────────────────────────────────────

def test_load_graph_retourne_dict():
    g = _load_graph()
    assert isinstance(g, dict)

def test_load_graph_non_vide():
    g = _load_graph()
    assert len(g) > 0

def test_get_cycle_ingredients_follicular():
    ings = get_cycle_ingredients("follicular")
    assert isinstance(ings, list)
    assert len(ings) > 0

def test_get_cycle_ingredients_toutes_phases():
    for phase in ("menstrual", "follicular", "ovulatory", "luteal"):
        ings = get_cycle_ingredients(phase)
        assert len(ings) > 0, f"Phase {phase} retourne liste vide"

def test_get_cycle_ingredients_phase_inconnue():
    ings = get_cycle_ingredients("unknown_phase")
    assert isinstance(ings, list)


# ── filter_service ────────────────────────────────────────────────────────────

def test_filter_vegan_retourne_seulement_vegan():
    result = apply_diet_filter(SAMPLE, "vegan")
    assert all(r["diet_flags"]["vegan"] for r in result)

def test_filter_vegetarian_inclut_vegan():
    result = apply_diet_filter(SAMPLE, "vegetarien")
    assert all(r["diet_flags"]["vegetarian"] for r in result)

def test_filter_none_retourne_tout():
    result = apply_diet_filter(SAMPLE, None)
    assert len(result) == len(SAMPLE)

def test_filter_recipes_alias():
    """filter_recipes est un alias de apply_diet_filter."""
    r1 = apply_diet_filter(SAMPLE, "vegan")
    r2 = filter_recipes(SAMPLE, "vegan")
    assert [r["id"] for r in r1] == [r["id"] for r in r2]


# ── substitution_service ──────────────────────────────────────────────────────

RECIPE_SUBS = {
    "id": 99, "title_fr": "Test substitutions",
    "ingredients": [{"ingredient_id": "tofu"}, {"ingredient_id": "garlic"}],
    "composition": [{"ingredient": "tofu", "quantity": 100, "unit": "g", "optional": False}],
    "diet_flags": {"vegan": True, "vegetarian": True},
    "servings": 2,
}

def test_substitution_retourne_liste():
    result = apply_substitutions([RECIPE_SUBS])
    assert isinstance(result, list)
    assert len(result) == 1

def test_substitution_ne_modifie_pas_recette_vegan():
    result = apply_substitutions([RECIPE_SUBS])
    assert isinstance(result, list)
    assert len(result) == 1


if __name__ == "__main__":
    tests = [(n, f) for n, f in globals().items() if n.startswith("test_") and callable(f)]
    ok = fail = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  ✅ {name}")
            ok += 1
        except Exception as e:
            print(f"  ❌ {name}: {e}")
            fail += 1
    print(f"\n{ok}/{ok+fail} tests passés")
