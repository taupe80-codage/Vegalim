"""budget.py — Budget estimé par recette. Fusionne : ingredient_price_engine"""
from __future__ import annotations
import logging
logger = logging.getLogger(__name__)

_ECO  = 1.0
_PREM = 2.5

def budget_label(price_per_portion: float) -> str:
    if price_per_portion < _ECO:  return "€ Économique"
    if price_per_portion < _PREM: return "€€ Standard"
    return "€€€ Premium"

def estimate_price(recipe: dict, servings: int | None = None) -> dict:
    """Coût estimé par recette et par portion, au prix du catalogue
    (prices_catalog.json) pour la quantité réellement utilisée.

    Remplace l'ancien calcul sur prices.json (clés couvrant ~5 % des ids de
    composition, 50 g supposés pour toute unité inconnue)."""
    from backend.engine.planning_engine.shopping import recipe_cost

    cost   = recipe_cost(recipe)
    n_serv = max(1, servings or recipe.get("servings", 4) or 4)
    per_p  = round(cost["total_eur"] / n_serv, 2)
    return {
        "total_eur":        cost["total_eur"],
        "per_portion_eur":  per_p,
        "label":            budget_label(per_p),
        "currency":         "EUR",
        "ingredients_cost": cost["details"][:8],
        "n_unknown_price":  cost["n_unknown"],
    }
