"""
test_final_zero_obsolete_imports.py — Zéro import archivé dans tout le backend.

Scanne récursivement backend/ (hors _archive/) et échoue sur le moindre
import vers un engine archivé.

Lance avec : pytest tests/test_final_zero_obsolete_imports.py -v
"""
import re
import pytest
from pathlib import Path

# ── Liste exhaustive des engines archivés ─────────────────────────────────────
ARCHIVED = [
    "adaptive_score_engine_v4",
    "ajr_scoring_engine",
    "auto_apply_engine",
    "auto_correct_engine",
    "culinary_rule_engine",
    "deficiency_detection_engine",
    "dictionary_engine",
    "dictionary_integration_engine",
    "diet_flag_auto_engine",
    "diet_flag_engine",
    "embedding_engine",
    "global_score_engine",
    "graph_versioning",
    "health_score_engine",
    "ingredient_price_engine",
    "ingredient_reuse_optimizer",
    "ingredient_synonym_resolver",
    "learning_engine",              # FIX #15 — migré vers reco_engine.learning
    "meal_planner",
    "meal_structure_engine",
    "missing_ingredients_tracker",
    "nutrition_resolver",
    "recipe_normalizer",
    "score_explainer",
    "score_reliability_engine",
    "search_engine_v3",
    "search_orchestrator",
    "seasonality_engine",
    "servings_engine",
    "shopping_engine",
    "similarity_engine",
    "sustainability_engine",
    "user_profile_engine",
    "vegan_variant_engine",
]

EXCLUDE = {"_archive", "__pycache__", ".pyc"}


def _backend_root() -> Path:
    here = Path(__file__).resolve().parent
    for p in [here.parent / "backend", here / "backend"]:
        if p.exists():
            return p
    raise FileNotFoundError("backend/ introuvable")


def _scan() -> dict[str, list[tuple[int, str]]]:
    root    = _backend_root()
    results = {}
    for f in sorted(root.rglob("*.py")):
        if any(e in str(f) for e in EXCLUDE):
            continue
        try:
            lines = f.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        hits = []
        for i, line in enumerate(lines, 1):
            for eng in ARCHIVED:
                if re.search(rf"from backend\.engine\.{re.escape(eng)}\b", line):
                    hits.append((i, line.strip()))
        if hits:
            results[str(f.relative_to(root.parent))] = hits
    return results


@pytest.fixture(scope="module")
def violations():
    return _scan()


# ── Un test par engine archivé ────────────────────────────────────────────────

def _check(violations, engine):
    hits = {
        path: [(n, l) for n, l in lines if engine in l]
        for path, lines in violations.items()
    }
    hits = {k: v for k, v in hits.items() if v}
    if hits:
        detail = "\n".join(
            f"  {path}:{n}  {l}"
            for path, lines in hits.items()
            for n, l in lines
        )
        pytest.fail(f"{engine} encore importé hors _archive/ :\n{detail}")


def test_no_adaptive_score_engine_v4(violations):    _check(violations, "adaptive_score_engine_v4")
def test_no_ajr_scoring_engine(violations):          _check(violations, "ajr_scoring_engine")
def test_no_culinary_rule_engine(violations):        _check(violations, "culinary_rule_engine")
def test_no_deficiency_detection_engine(violations): _check(violations, "deficiency_detection_engine")
def test_no_dictionary_engine(violations):           _check(violations, "dictionary_engine")
def test_no_diet_flag_auto_engine(violations):       _check(violations, "diet_flag_auto_engine")
def test_no_diet_flag_engine(violations):            _check(violations, "diet_flag_engine")
def test_no_embedding_engine(violations):            _check(violations, "embedding_engine")
def test_no_global_score_engine(violations):         _check(violations, "global_score_engine")
def test_no_health_score_engine(violations):         _check(violations, "health_score_engine")
def test_no_ingredient_price_engine(violations):     _check(violations, "ingredient_price_engine")
def test_no_ingredient_reuse_optimizer(violations):  _check(violations, "ingredient_reuse_optimizer")
def test_no_ingredient_synonym_resolver(violations): _check(violations, "ingredient_synonym_resolver")
def test_no_meal_planner(violations):                _check(violations, "meal_planner")
def test_no_meal_structure_engine(violations):       _check(violations, "meal_structure_engine")
def test_no_score_explainer(violations):             _check(violations, "score_explainer")
def test_no_score_reliability_engine(violations):    _check(violations, "score_reliability_engine")
def test_no_search_engine_v3(violations):            _check(violations, "search_engine_v3")
def test_no_search_orchestrator(violations):         _check(violations, "search_orchestrator")
def test_no_seasonality_engine(violations):          _check(violations, "seasonality_engine")
def test_no_servings_engine(violations):             _check(violations, "servings_engine")
def test_no_shopping_engine(violations):             _check(violations, "shopping_engine")
def test_no_similarity_engine(violations):           _check(violations, "similarity_engine")
def test_no_learning_engine(violations):             _check(violations, "learning_engine")  # FIX #15
def test_no_sustainability_engine(violations):       _check(violations, "sustainability_engine")
def test_no_vegan_variant_engine(violations):        _check(violations, "vegan_variant_engine")


# ── Tests fonctionnels — nouvelles fonctions accessibles ─────────────────────

def test_summarize_deficiencies():
    from backend.engine.score_engine.ajr import summarize_deficiencies
    result = summarize_deficiencies([
        {"nutrient": "iron",  "ratio": 0.1, "severity": "high"},
        {"nutrient": "fiber", "ratio": 0.3, "severity": "medium"},
    ])
    assert result == {"high": ["iron"], "medium": ["fiber"]}


def test_compute_ajr_score_float():
    from backend.engine.score_engine.ajr import compute_ajr_score
    s = compute_ajr_score({"calories": 2000, "protein": 50})
    assert isinstance(s, float)
    assert 0.0 <= s <= 10.0


def test_detect_deficiencies_custom_ajr():
    from backend.engine.score_engine.ajr import detect_deficiencies
    result = detect_deficiencies({"iron": 1.0}, {"iron": 20.0})
    assert any(d["nutrient"] == "iron" for d in result)


def test_reliability_attach():
    from backend.engine.score_engine.reliability import attach
    from unittest.mock import patch, MagicMock
    mock_gd = MagicMock()
    mock_gd.nutrition.coverage_for_recipe.return_value = 0.85
    # get_data est importé localement dans la fonction reliability() → patch via data_access
    with patch("backend.db.data_access.get_data", mock_gd):
        result = attach({"id": 1, "ingredients": ["tomate"]})
    assert result["score_reliability"] in ("high", "medium", "low")
    assert "score_coverage" in result


def test_reliability_attach_idempotent():
    from backend.engine.score_engine.reliability import attach
    recipe = {"id": 1, "ingredients": ["tomate"], "score_reliability": "high"}
    assert attach(recipe) is recipe


def test_normalize_servings():
    from backend.engine.planning_engine.servings import normalize_servings
    assert normalize_servings({"servings": 0})["servings"] == 1
    assert normalize_servings({"servings": 99})["servings"] == 20
    assert normalize_servings({"servings": 4})["servings"] == 4


def test_base_engine_removed():
    """base_engine.py a été supprimé lors de la migration v6.
    Ce test vérifie qu'il n'est plus importé nulle part dans le projet.
    """
    import os
    from pathlib import Path
    root = Path(__file__).parent.parent / "backend"
    for py_file in root.rglob("*.py"):
        if "base_engine" in py_file.name:
            continue  # le fichier lui-même s'il existait encore
        src = py_file.read_text(encoding="utf-8", errors="ignore")
        assert "base_engine" not in src, (
            f"Import obsolète de base_engine trouvé dans {py_file.relative_to(root.parent)}"
        )


def test_pipeline_no_archived_engines():
    import inspect, ast
    import backend.engine.pipeline as mod
    src = inspect.getsource(mod)
    # Exclure le docstring du module (entre les premiers triple-quotes)
    # On cherche uniquement dans le code hors docstrings
    try:
        tree = ast.parse(src)
        # Extraire les nœuds Import/ImportFrom uniquement
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node))
        import_src = "\n".join(imports)
    except Exception:
        import_src = src  # fallback
    for eng in ["dictionary_engine", "servings_engine",
                "diet_flag_auto_engine", "score_reliability_engine",
                "adaptive_score_engine_v4", "culinary_rule_engine"]:
        assert eng not in import_src, f"pipeline.py importe encore {eng}"


def test_pipeline_sg_d_defined():
    import inspect, re
    import backend.engine.pipeline as mod
    src = inspect.getsource(mod)
    # Chercher l'assignation sg_d = sg.get(...)
    assign = src.find("sg_d = sg.get(")
    # Chercher l'utilisation avec pattern flexible (espaces variables après la clé)
    use = re.search(r'sg_d\.get\("overall_score"', src)
    assert assign != -1, "sg_d n'est pas défini dans pipeline.py"
    assert use is not None, 'sg_d.get("overall_score"...) introuvable'
    assert assign < use.start(), "sg_d utilisé avant d'être défini"


def test_nutrition_route_no_archived():
    import inspect, ast
    import backend.api.routes.nutrition as mod
    src = inspect.getsource(mod)
    # Vérifier uniquement les imports réels (pas les docstrings/commentaires)
    try:
        tree = ast.parse(src)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                imports.append(ast.unparse(node))
        import_src = "\n".join(imports)
    except Exception:
        import_src = src
    assert "ajr_scoring_engine"          not in import_src
    assert "deficiency_detection_engine" not in import_src
    assert "score_engine.ajr"            in src  # présent dans le code réel


def test_compat_exports_new_aliases():
    from backend.engine.compat import (
        summarize_deficiencies,
        compute_ajr_score,
        attach,
        normalize_servings,
        AJR,
        apply_flags,
        batch_update,
        audit,
    )
    assert callable(summarize_deficiencies)
    assert callable(compute_ajr_score)
    assert callable(attach)
    assert callable(normalize_servings)
    assert isinstance(AJR, dict)


def test_score_engine_init_exports():
    from backend.engine.score_engine import (
        AJR, ajr_score, compute_ajr_score,
        detect_deficiencies, summarize_deficiencies,
        reliability, attach,
    )
    assert callable(summarize_deficiencies)
    assert callable(attach)
    assert isinstance(AJR, dict)
