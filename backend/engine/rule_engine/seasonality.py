"""
seasonality.py — Saisonnalité des ingrédients.
Fusionne : seasonality_engine

API :
    in_season(ingredient, month) → bool
    seasonal_ingredients(month)  → list[str]
    season_bonus(recipe, month)  → float
"""
from __future__ import annotations
from backend.core.data_cache import data_cached

@data_cached
def _db() -> dict:
    from backend.db.data_access import get_data
    return get_data.graphs.get_raw("seasonality") or {}

def in_season(ingredient: str, month: int) -> bool:
    """Retourne True si l'ingrédient est de saison au mois donné (1-12)."""
    data = _db()
    return month in data.get(ingredient, {}).get("months", [])

def seasonal_ingredients(month: int) -> list[str]:
    """Retourne tous les ingrédients de saison pour un mois donné."""
    db = _db()
    return [ing for ing, data in db.items() if month in data.get("months", [])]

def season_bonus(recipe: dict, month: int | None) -> float:
    """Bonus saisonnalité pour une recette : +2 si >50% des ingrédients sont de saison."""
    if month is None:
        return 0.0
    ingredients = recipe.get("ingredients", [])
    if not ingredients:
        return 0.0
    in_s = sum(1 for i in ingredients if in_season(str(i), month))
    ratio = in_s / len(ingredients)
    return 2.0 if ratio > 0.5 else (1.0 if ratio > 0.25 else 0.0)
