"""
test_stability.py — Tests de stabilisation (Pass 5).
Vérifie : gestion d'erreur, validation, logging, robustesse.
"""
import logging
from pathlib import Path

from backend.core.validators import (
    is_valid_recipe, validate_recipes, is_valid_diet, safe_float
)
from backend.core.data_io import load_json


# ── Tests validators ──────────────────────────────────────────────────────────

def test_is_valid_recipe_ok():
    r = {"ingredients": ["lentils"], "nutrition": {"protein": 20}}
    assert is_valid_recipe(r)

def test_is_valid_recipe_missing_nutrition():
    r = {"ingredients": ["lentils"]}
    assert not is_valid_recipe(r)

def test_is_valid_recipe_missing_ingredients():
    r = {"nutrition": {"protein": 20}}
    assert not is_valid_recipe(r)

def test_is_valid_recipe_not_dict():
    assert not is_valid_recipe(None)
    assert not is_valid_recipe("lentil salad")
    assert not is_valid_recipe([1, 2, 3])

def test_is_valid_recipe_strict_empty_ingredients():
    r = {"ingredients": [], "nutrition": {"protein": 20}}
    assert not is_valid_recipe(r, strict=True)

def test_is_valid_recipe_strict_ok():
    r = {"ingredients": ["lentils"], "nutrition": {"protein": 20, "calories": 300}}
    assert is_valid_recipe(r, strict=True)

def test_validate_recipes_filters_invalid():
    recipes = [
        {"ingredients": ["lentils"], "nutrition": {"protein": 20}},  # valide
        {"title": "sans nutrition"},                                   # invalide (pas nutrition)
        None,                                                          # invalide (pas un dict)
        {"ingredients": ["x"], "nutrition": {}},                       # valide (strict=False)
    ]
    valid = validate_recipes(recipes)
    # En mode non-strict : valide si ingredients ET nutrition présents (même vides)
    assert len(valid) == 2
    # La recette avec None est exclue, celle sans nutrition aussi
    titles = [r.get("title") for r in valid]
    assert None not in [r.get("ingredients") for r in valid]

def test_validate_recipes_all_valid():
    recipes = [
        {"ingredients": ["a"], "nutrition": {"protein": 10}},
        {"ingredients": ["b"], "nutrition": {"calories": 300}},
    ]
    assert len(validate_recipes(recipes)) == 2

def test_is_valid_diet_known():
    for diet in ("vegan", "vegetarien", "diabete", "hyperproteine", "gluten_free"):
        assert is_valid_diet(diet)

def test_is_valid_diet_unknown():
    import warnings
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        result = is_valid_diet("carnivore")
        assert not result

def test_is_valid_diet_none():
    assert is_valid_diet(None)

def test_safe_float_valid():
    assert safe_float(3.14) == 3.14
    assert safe_float("7.5") == 7.5
    assert safe_float(0) == 0.0

def test_safe_float_invalid():
    assert safe_float(None)    == 0.0
    assert safe_float("abc")   == 0.0
    assert safe_float([])      == 0.0

def test_safe_float_custom_default():
    assert safe_float("bad", default=5.0) == 5.0


# ── Tests data_io ─────────────────────────────────────────────────────────────

def test_load_json_missing_file():
    """Fichier absent → retourne default sans crash."""
    result = load_json("/tmp/fichier_inexistant_abc123.json", default={"empty": True})
    assert result == {"empty": True}

def test_load_json_missing_file_empty_default():
    """Fichier absent sans default → retourne {}."""
    result = load_json("/tmp/fichier_inexistant_abc123.json")
    assert result == {}

def test_load_json_corrupted(tmp_path):
    """JSON corrompu → retourne default sans crash."""
    bad = tmp_path / "bad.json"
    bad.write_text("{invalid json !")
    result = load_json(bad, default={"fallback": True})
    assert result == {"fallback": True}

def test_load_json_valid(tmp_path):
    """JSON valide → retourne le contenu."""
    import json
    good = tmp_path / "good.json"
    good.write_text(json.dumps({"key": "value", "number": 42}))
    result = load_json(good)
    assert result == {"key": "value", "number": 42}


# ── Tests logging configuré ───────────────────────────────────────────────────

def test_logger_module_exists():
    from backend.core.logger import get_logger
    logger = get_logger("test")
    assert logger is not None
    assert logger.name == "test"

def test_logger_levels():
    from backend.core.logger import get_logger
    logger = get_logger("test_levels")
    # Ces appels ne doivent pas crasher
    logger.debug("debug message")
    logger.info("info message")
    logger.warning("warning message")
    logger.error("error message")


if __name__ == "__main__":
    tests = [f for name, f in globals().items()
             if name.startswith("test_") and callable(f)]
    ok = fail = 0
    for t in tests:
        try:
            import inspect
            sig = inspect.signature(t)
            if "tmp_path" in sig.parameters:
                import tempfile
                with tempfile.TemporaryDirectory() as d:
                    t(Path(d))
            else:
                t()
            print(f"  ✅ {t.__name__}")
            ok += 1
        except Exception as e:
            print(f"  ❌ {t.__name__}: {e}")
            fail += 1
    print(f"\n{ok}/{ok+fail} tests passés")
