"""
servings.py — Gestion des portions.

Fusionne : servings_engine

API :
    validate_servings(value)              → int   valeur sécurisée 1-20
    normalize_servings(recipe)            → dict  recette avec servings corrigé
    scale_recipe(recipe, target)          → dict  quantités adaptées
    nutrition_per_serving(recipe, totals) → dict  valeurs par portion
"""
from __future__ import annotations
import logging
logger = logging.getLogger(__name__)

_MIN, _MAX, _DEFAULT = 1, 20, 4


def validate_servings(value) -> int:
    """Retourne une valeur de portions valide (int, 1–20). Défaut = 4."""
    try:
        return max(_MIN, min(_MAX, int(float(str(value)))))
    except (TypeError, ValueError):
        return _DEFAULT


def normalize_servings(recipe: dict) -> dict:
    """
    Corrige le champ servings d'une recette (retourne une copie).

    - Si absent ou invalide → DEFAULT (4)
    - Si hors bornes [1, 20] → ramené aux bornes
    - Idempotent

    Alias de compat : servings_engine.normalize_servings
    """
    r = dict(recipe)
    r["servings"] = validate_servings(r.get("servings"))
    return r


def scale_recipe(recipe: dict, target_servings: int) -> dict:
    """
    Adapte les quantités de la composition pour target_servings portions.
    Retourne une copie — ne modifie pas la recette originale.
    """
    target = validate_servings(target_servings)
    base   = validate_servings(recipe.get("servings", _DEFAULT))
    r      = dict(recipe)
    r["servings"] = target
    if base == target:
        return r
    ratio  = target / base
    scaled = []
    for item in recipe.get("composition", []):
        item = dict(item)
        qty  = item.get("quantity")
        if isinstance(qty, (int, float)) and qty > 0:
            s = qty * ratio
            item["quantity"] = (round(s, 1) if s < 5
                                else round(s) if s < 50
                                else int(round(s / 5) * 5))
        scaled.append(item)
    r["composition"]  = scaled
    r["_scaled_from"] = base
    r["_scale_ratio"] = round(ratio, 3)
    return r


def nutrition_per_serving(recipe: dict, nutrition_total: dict) -> dict:
    """Divise les totaux nutritionnels par le nombre de portions."""
    servings = validate_servings(recipe.get("servings", _DEFAULT))
    result   = {
        k: round(v / servings, 2) if isinstance(v, (int, float)) else v
        for k, v in nutrition_total.items()
    }
    result["_per_serving"] = servings
    return result
