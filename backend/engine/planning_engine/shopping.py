"""
shopping.py — Liste de courses depuis un plan de repas.
Fusionne : shopping_engine

API :
    shopping_list(meal_plan, eco) → dict
"""
from __future__ import annotations
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


def shopping_list(meal_plan: dict, eco: bool = False) -> dict:
    """
    Génère la liste de courses pour un plan de repas hebdomadaire.

    Args:
        meal_plan : output de generate_plan()
        eco       : marque les ingrédients réutilisés (> 2 fois)

    Returns:
        {
          items:           [{ingredient, occurrences, price_eur, eco_reuse?}]
          estimated_cost:  float (€)
          n_recipes:       int
          by_category:     {category: [ingredient]}
        }
    """
    from backend.db.data_access import get_data
    from backend.engine.planning_engine.budget import estimate_price

    ing_count: dict[str, int] = defaultdict(int)
    n_recipes  = 0
    seen_ids   = set()

    for day, data in meal_plan.items():
        if day == "meta": continue
        for meal in ("lunch", "dinner"):
            meal_data = data.get(meal)
            if not meal_data: continue

            rid = meal_data.get("id") if isinstance(meal_data, dict) else None
            if not rid: continue

            recipe = get_data.recipes.get_by_id(rid)
            if not recipe: continue

            if rid in seen_ids:
                continue   # batch cooking : ne pas doubler
            seen_ids.add(rid)
            n_recipes += 1

            for ing in recipe.get("ingredients", []):
                key = (ing.get("ingredient_id", str(ing)) if isinstance(ing, dict) else str(ing)).lower()
                ing_count[key] += 1

    # Construire la liste
    items      = []
    total_eur  = 0.0

    from backend.core.data_io import load_prices
    prices = load_prices()

    for ing, count in sorted(ing_count.items(), key=lambda x: -x[1]):
        price_eur = float(prices.get(ing, 0.0)) * count

        item: dict = {"ingredient": ing, "occurrences": count, "price_eur": round(price_eur, 2)}
        if eco:
            item["eco_reuse"] = count > 2
        items.append(item)
        total_eur += price_eur

    # Regrouper par catégorie
    from backend.db.data_access import get_data
    by_cat: dict[str, list] = defaultdict(list)
    for item in items:
        ing_data = get_data.ingredients.get_by_name(item["ingredient"])
        cat      = (ing_data or {}).get("category", "autre")
        by_cat[cat].append({"ingredient": item["ingredient"], "occurrences": item["occurrences"]})

    return {
        "items":          items,
        "estimated_cost": round(total_eur, 2),
        "n_recipes":      n_recipes,
        "by_category":    dict(by_cat),
    }
