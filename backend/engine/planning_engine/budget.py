"""budget.py — Budget estimé par recette. Fusionne : ingredient_price_engine"""
from __future__ import annotations
import logging
from functools import lru_cache
logger = logging.getLogger(__name__)

_ECO  = 1.0
_PREM = 2.5

@lru_cache(maxsize=1)
def _prices() -> dict:
    from backend.core.data_io import load_prices
    return load_prices()

def budget_label(price_per_portion: float) -> str:
    if price_per_portion < _ECO:  return "€ Économique"
    if price_per_portion < _PREM: return "€€ Standard"
    return "€€€ Premium"

@lru_cache(maxsize=1)
def _unit_conversions() -> dict:
    from backend.core.data_io import load_unit_conversion_graph
    g = load_unit_conversion_graph()
    mapping = {"g": 1.0, "kg": 1000.0, "ml": 1.0, "l": 1000.0, "piece": 100.0, "": 100.0, "cc": 5.0, "cs": 15.0, "pincee": 1.0, "pinch": 1.0, "branche": 3.0, "feuille": 3.0}
    if "weight" in g:
        mapping["kg"] = g["weight"].get("kg_to_g", 1000.0)
    if "volume" in g:
        vol = g["volume"]
        mapping["l"] = vol.get("l_to_ml", 1000.0)
        mapping["tbsp"] = vol.get("tbsp_to_ml", 15.0)
        mapping["tsp"] = vol.get("tsp_to_ml", 5.0)
        mapping["cup"] = vol.get("cup_to_ml", 240.0)
    return mapping

def estimate_price(recipe: dict, servings: int | None = None) -> dict:
    """Calcule le coût estimé par recette et par portion."""
    prices  = _prices()
    n_serv  = max(1, servings or recipe.get("servings", 4) or 4)
    total   = 0.0
    details = []

    for item in recipe.get("composition", []):
        if not isinstance(item, dict): continue
        iid  = item.get("ingredient", "")
        qty  = item.get("quantity") or 0
        unit = item.get("unit", "g").lower()
        p100 = prices.get(iid, 0.0)
        if not p100: continue
        qty_g = qty * _unit_conversions().get(unit, 50.0)
        cost  = p100 * qty_g / 100
        total += cost
        if cost > 0:
            details.append({"ingredient": iid, "cost_eur": round(cost, 3)})

    per_p = round(total / n_serv, 2)
    details.sort(key=lambda x: -x["cost_eur"])
    return {
        "total_eur":       round(total, 2),
        "per_portion_eur": per_p,
        "label":           budget_label(per_p),
        "currency":        "EUR",
        "ingredients_cost": details[:8],
    }
