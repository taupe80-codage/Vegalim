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
    # seasonality.json vit dans data/modules/, pas data/graphs/ : l'alias de
    # GraphRepository « seasonality » ne pointait vers aucun fichier.
    from backend.core.data_io import load_seasonality
    return load_seasonality() or {}

def in_season(ingredient: str, month: int) -> bool:
    """Retourne True si l'ingrédient est de saison au mois donné (1-12)."""
    data = _db()
    return month in data.get(ingredient, {}).get("months", [])

def seasonal_ingredients(month: int) -> list[str]:
    """Retourne tous les ingrédients de saison pour un mois donné."""
    db = _db()
    return [ing for ing, data in db.items() if month in data.get("months", [])]

def _ingredient_ids(recipe: dict) -> list[str]:
    """Identifiants d'ingrédients d'une recette : composition (CDC v4), sinon ingredients (legacy)."""
    ids = []
    for item in recipe.get("composition") or recipe.get("ingredients") or []:
        raw = (item.get("ingredient") or item.get("ingredient_id") or "") if isinstance(item, dict) else item
        raw = str(raw).lower().strip()
        if raw:
            ids.append(raw)
    return ids

def _season_key(ingredient: str, db: dict) -> str | None:
    """Clé de seasonality.json d'un ingrédient : exacte, sinon par préfixe (« baby_spinach » → « spinach »)."""
    if ingredient in db:
        return ingredient
    base = ingredient.split("_")[0]
    return base if base in db else None

def season_bonus(recipe: dict, month: int | None) -> float:
    """Bonus saisonnalité : +2 si >50% des ingrédients saisonniers sont de saison, +1 si >25%.

    Les ingrédients disponibles les 12 mois sont ignorés : ils ne distinguent
    pas une recette d'une autre.
    """
    if month is None:
        return 0.0
    db = _db()
    keys = (_season_key(i, db) for i in _ingredient_ids(recipe))
    seasonal = [k for k in keys if k and len(db[k].get("months", [])) < 12]
    if not seasonal:
        return 0.0
    ratio = sum(1 for i in seasonal if month in db[i].get("months", [])) / len(seasonal)
    return 2.0 if ratio > 0.5 else (1.0 if ratio > 0.25 else 0.0)
