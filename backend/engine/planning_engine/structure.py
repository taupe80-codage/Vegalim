"""structure.py — Classification du type de repas. Fusionne : meal_structure_engine"""
from __future__ import annotations

_TAG_MAP = {
    "dessert": "dessert", "sweet": "dessert", "sucre": "dessert",
    "soup": "soup", "soupe": "soup", "veloute": "soup", "potage": "soup",
    "salad": "salad", "salade": "salad",
    "breakfast": "breakfast", "petit_dej": "breakfast", "smoothie": "breakfast",
    "snack": "snack", "encas": "snack",
    "appetizer": "starter", "entree": "starter",
}

def meal_type(recipe: dict) -> str:
    """Classifie le type de repas : main|soup|dessert|salad|breakfast|snack|starter."""
    tags  = [t.lower() for t in (recipe.get("tags") or [])]
    title = (recipe.get("titles", {}).get("fr") or recipe.get("titles", {}).get("original") or "").lower()
    for tag in tags:
        if tag in _TAG_MAP: return _TAG_MAP[tag]
    for kw, t in _TAG_MAP.items():
        if kw in title: return t
    return "main"
