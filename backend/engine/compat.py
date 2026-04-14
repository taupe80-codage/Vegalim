"""
compat.py — Couche de compatibilité ascendante.

Permet de migrer progressivement les imports sans tout casser d'un coup.
Chaque ancien chemin d'import fonctionne encore — il délègue au nouveau package.

ÉTAT DE LA MIGRATION :
    ✅ global_score_engine       → score_engine.quality
    ✅ adaptive_score_engine_v4  → score_engine.quality
    ✅ health_score_engine        → score_engine.health
    ✅ ajr_scoring_engine         → score_engine.ajr
    ✅ deficiency_detection_engine→ score_engine.ajr
    ✅ score_reliability_engine   → score_engine.reliability
    ✅ score_explainer            → score_engine.explainer
    ✅ search_engine_v3           → search_engine.core
    ✅ similarity_engine          → search_engine.similar
    ✅ ingredient_synonym_resolver→ search_engine.resolver
    ✅ dictionary_engine          → search_engine.resolver
    ✅ culinary_rule_engine       → rule_engine.validation
    ✅ diet_flag_engine           → rule_engine.diet
    ✅ diet_flag_auto_engine      → rule_engine.diet
    ✅ seasonality_engine         → rule_engine.seasonality
    ✅ sustainability_engine      → rule_engine.carbon
    ✅ vegan_variant_engine       → rule_engine.variants
    ✅ meal_planner               → planning_engine.planner
    ✅ shopping_engine            → planning_engine.shopping
    ✅ servings_engine            → planning_engine.servings
    ✅ ingredient_price_engine    → planning_engine.budget
    ✅ meal_structure_engine      → planning_engine.structure
    ✅ recommendation_engine      → reco_engine.orchestrator
"""

# ── score_engine ──────────────────────────────────────────────────────────────
from backend.engine.score_engine.quality import (
    score_recipe as _score_recipe,
    score_batch  as _score_batch,
    PROFILES,
)
from backend.engine.score_engine.health      import health_score as compute_health_score
from backend.engine.score_engine.ajr         import (
    AJR,
    ajr_score,
    compute_ajr_score,
    detect_deficiencies,
    summarize_deficiencies,
)
from backend.engine.score_engine.reliability import reliability as compute_reliability, attach
from backend.engine.score_engine.explainer   import explain


def compute_global_score(recipe: dict, **kwargs) -> dict:
    """Compat : global_score_engine.compute_global_score → score_engine.score_recipe"""
    res = _score_recipe(recipe)
    return {**res.get("dims", {}), "global_score": res["global_score"], **res}


def score(recipe: dict, profile: str = "default", context: dict = None) -> dict:
    """Compat : adaptive_score_engine_v4.score → score_engine.score_recipe"""
    return _score_recipe(recipe, profile=profile, context=context or {})


# ── search_engine ─────────────────────────────────────────────────────────────
from backend.engine.search_engine.core     import search
from backend.engine.search_engine.similar  import find_similar, find_similar_by_id
from backend.engine.search_engine.resolver import resolve, resolve_list, normalize_list


# ── rule_engine ───────────────────────────────────────────────────────────────
from backend.engine.rule_engine.diet        import (
    compute_diet_flags,
    apply_flags,
    batch_update,
    audit,
    NON_VEGAN,
    NON_VEGETARIAN,
)
from backend.engine.rule_engine.validation  import validate_recipe
from backend.engine.rule_engine.seasonality import (
    in_season,
    seasonal_ingredients,
    season_bonus,
)
from backend.engine.rule_engine.carbon      import carbon_score, eco_label
from backend.engine.rule_engine.variants    import vegan_variant


# ── planning_engine ───────────────────────────────────────────────────────────
from backend.engine.planning_engine.planner   import generate_plan
from backend.engine.planning_engine.shopping  import shopping_list
from backend.engine.planning_engine.servings  import (
    scale_recipe,
    validate_servings,
    normalize_servings,
    nutrition_per_serving,
)
from backend.engine.planning_engine.budget    import estimate_price, budget_label
from backend.engine.planning_engine.structure import meal_type


__all__ = [
    # score
    "compute_global_score", "score", "PROFILES",
    "compute_health_score",
    "AJR", "ajr_score", "compute_ajr_score",
    "detect_deficiencies", "summarize_deficiencies",
    "compute_reliability", "attach",
    "explain",
    # search
    "search", "find_similar", "find_similar_by_id",
    "resolve", "resolve_list", "normalize_list",
    # rules
    "compute_diet_flags", "apply_flags", "batch_update", "audit",
    "NON_VEGAN", "NON_VEGETARIAN",
    "validate_recipe",
    "in_season", "seasonal_ingredients", "season_bonus",
    "carbon_score", "eco_label",
    "vegan_variant",
    # planning
    "generate_plan", "shopping_list",
    "scale_recipe", "validate_servings", "normalize_servings", "nutrition_per_serving",
    "estimate_price", "budget_label",
    "meal_type",
]
