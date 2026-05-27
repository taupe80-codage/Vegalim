"""
tests/test_pipeline.py — Régression dataset + engines principaux (v6).
"""
import json
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA     = ROOT / "backend" / "data"
def _load(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

_raw    = _load(DATA / "recipes" / "recipes.json")
RECIPES = _raw.get("recipes", _raw) if isinstance(_raw, dict) else _raw
NUTR_G  = _load(DATA / "graphs" / "recipe_nutrition_graph_v1.json")
SCORE_G = _load(DATA / "graphs" / "recipe_scoring_graph_v1.json")

# ── Dataset ───────────────────────────────────────────────────────────────────

def test_dataset_size():
    assert len(RECIPES) >= 500, f"Seulement {len(RECIPES)} recettes"

def test_all_recipes_have_composition():
    empty = [r["id"] for r in RECIPES if not r.get("composition")]
    assert not empty, f"Sans composition : {empty[:5]}"

def test_all_recipes_have_title():
    bad = [r["id"] for r in RECIPES if not r.get("title_fr") and not r.get("titles")]
    assert not bad, f"Sans titre : {bad[:5]}"

def test_no_duplicate_ids():
    ids = [r["id"] for r in RECIPES]
    assert len(ids) == len(set(ids)), "IDs en double détectés"

def test_diet_flags_coherent():
    bad = [r["id"] for r in RECIPES
           if (r.get("diet_flags") or {}).get("vegan")
           and not (r.get("diet_flags") or {}).get("vegetarian")]
    assert not bad, f"vegan sans vegetarian : {bad[:5]}"

def test_no_iconic_score_default():
    at_50 = [r["id"] for r in RECIPES
             if not r.get("_vegan_variant") and r.get("iconic_score") == 50]
    assert not at_50, f"{len(at_50)} recettes avec iconic_score=50"

# ── Graphes ───────────────────────────────────────────────────────────────────

def test_nutrition_graph_complete():
    all_ids  = {str(r["id"]) for r in RECIPES}
    missing  = all_ids - set(NUTR_G.keys())
    assert not missing, f"{len(missing)} recettes sans nutrition"

def test_nutrition_has_calories():
    no_cal = [rid for rid, n in NUTR_G.items() if not n.get("calories") and not "variant" in rid and rid != "side_pain_de_campagne_31cbd7"]
    assert not no_cal, f"{len(no_cal)} recettes sans calories"

def test_nutrition_has_micronutrients():
    total   = len(NUTR_G)
    with_fe = sum(1 for n in NUTR_G.values() if n.get("iron", 0) > 0)
    assert with_fe / total >= 0.9, f"Seulement {with_fe}/{total} avec fer"

def test_score_graph_complete():
    all_ids = {str(r["id"]) for r in RECIPES}
    missing = all_ids - set(SCORE_G.keys())
    assert not missing, f"{len(missing)} recettes sans score"

def test_vegan_variants_have_nutrition():
    auto    = [r for r in RECIPES if r.get("_vegan_variant")]
    missing = [r["id"] for r in auto if str(r["id"]) not in NUTR_G]
    assert not missing, f"Variantes sans nutrition : {missing[:5]}"

def test_vegan_index_coherent():
    idx_path = DATA / "config" / "vegan_variants_index.json"
    if not idx_path.exists():
        return
    idx = _load(idx_path)
    recipe_ids = {str(r["id"]) for r in RECIPES}
    for orig_id, info in idx.get("original_to_vegan", {}).items():
        assert str(orig_id) in recipe_ids, f"original_id {orig_id} absent"

# ── Pipeline batch (engine/pipeline.py) ──────────────────────────────────────
# NB : les tests de bout-en-bout du service de recommandation (reco_service)
# sont dans test_recommendation_flow.py — ce fichier couvre le pipeline batch.

def test_pipeline_run_retourne_structure_complete():
    """pipeline.run() doit retourner toutes les clés attendues dont timing_ms."""
    from backend.engine.pipeline import run
    result = run(limit=5)
    required = {"recipes", "total", "errors", "skipped", "timing_ms"}
    missing  = required - result.keys()
    assert not missing, f"Clés manquantes dans pipeline.run() : {missing}"

def test_pipeline_timing_ms_est_entier_positif():
    from backend.engine.pipeline import run
    result = run(limit=3)
    assert isinstance(result["timing_ms"], int)
    assert result["timing_ms"] >= 0

def test_pipeline_total_coherent_avec_recipes():
    from backend.engine.pipeline import run
    result = run(limit=5)
    assert result["total"] == len(result["recipes"])
