"""
planning_engine/ — Moteur de planification repas et courses.

Fusionne 6 engines :
    meal_planner + shopping_engine + servings_engine
    ingredient_reuse_optimizer + ingredient_price_engine + meal_structure_engine

API PUBLIQUE :
    from backend.engine.planning_engine import (
        generate_plan, shopping_list,
        scale_recipe, validate_servings,
        estimate_price, budget_label,
        meal_type,
    )
"""
from backend.engine.planning_engine.planner   import generate_plan
from backend.engine.planning_engine.shopping  import shopping_list
from backend.engine.planning_engine.servings  import scale_recipe, validate_servings
from backend.engine.planning_engine.budget    import estimate_price, budget_label
from backend.engine.planning_engine.structure import meal_type

__all__ = [
    "generate_plan", "shopping_list",
    "scale_recipe", "validate_servings",
    "estimate_price", "budget_label",
    "meal_type",
]
