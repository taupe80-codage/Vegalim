"""
carbon.py — Empreinte carbone recette.
Fusionne : sustainability_engine

API :
    carbon_score(recipe) → dict  {total_kg_co2, per_portion_kg, label, score}
"""
from __future__ import annotations
from functools import lru_cache

_LOW  = 0.5   # kg CO₂e / portion
_HIGH = 1.5

@lru_cache(maxsize=1)
def _carbon_db() -> dict:
    from backend.core.data_io import load_carbon_footprint
    return load_carbon_footprint()

def eco_label(kg_co2: float) -> str:
    if kg_co2 < _LOW:  return "🟢 Faible"
    if kg_co2 < _HIGH: return "🟡 Moyen"
    return "🔴 Élevé"

def carbon_score(recipe: dict) -> dict:
    """Calcule l'empreinte carbone et le score éco (0-10, 10=très faible)."""
    db       = _carbon_db()
    servings = max(1, recipe.get("servings", 4) or 4)
    total    = 0.0
    per_ing  = []

    for item in recipe.get("composition", []):
        if not isinstance(item, dict): continue
        iid  = item.get("ingredient", "")
        qty  = item.get("quantity") or 0
        unit = item.get("unit", "g")
        qty_g = qty * 1000 if unit == "kg" else qty * 100 if unit in ("piece", "") else qty
        raw  = db.get(iid, 0.0)
        co2_per_100g = float(raw) if isinstance(raw, (int, float)) else float(raw.get("co2_per_100g", 0.0)) if isinstance(raw, dict) else 0.0
        if co2_per_100g and qty_g:
            co2 = co2_per_100g * qty_g / 100
            total += co2
            per_ing.append({"ingredient": iid, "kg_co2": round(co2, 4)})

    per_portion = round(total / servings, 3)
    score       = round(max(1.0, min(10.0, 10.0 - per_portion * 4.0)), 2)

    return {
        "total_kg_co2":   round(total, 3),
        "per_portion_kg": per_portion,
        "label":          eco_label(per_portion),
        "score":          score,
        "ingredients_co2": sorted(per_ing, key=lambda x: -x["kg_co2"])[:8],
    }
