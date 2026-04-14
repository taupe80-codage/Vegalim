"""
reliability.py — Fiabilité du score nutritionnel (CDC_03c).

Fusionne : score_reliability_engine

API :
    reliability(recipe) → dict  {status, coverage, label, message}
    attach(recipe)      → dict  recette enrichie (compat score_reliability_engine.attach)
"""
from __future__ import annotations

from backend.engine.config import RELIABILITY_HIGH, RELIABILITY_MEDIUM

_LABELS = {
    "high":   "🟢 Élevée",
    "medium": "🟡 Moyenne",
    "low":    "🔴 Faible",
}
_MESSAGES = {
    "high":   "Score fiable — données CIQUAL disponibles pour la majorité des ingrédients.",
    "medium": "Score partiellement fiable — certains ingrédients manquent de données CIQUAL.",
    "low":    "Score indicatif — peu d'ingrédients ont des données CIQUAL disponibles.",
}


def reliability(recipe: dict) -> dict:
    """
    Calcule la fiabilité du score nutritionnel d'une recette.

    Returns:
        {status: str, coverage: float, label: str, message: str}
    """
    ings = recipe.get("ingredients", []) or []
    if not ings:
        return {
            "status":   "low",
            "coverage": 0.0,
            "label":    _LABELS["low"],
            "message":  _MESSAGES["low"],
        }
    from backend.db.data_access import get_data
    names    = [i if isinstance(i, str) else str(i) for i in ings]
    coverage = get_data.nutrition.coverage_for_recipe(names)
    status   = ("high"   if coverage >= RELIABILITY_HIGH
                else "medium" if coverage >= RELIABILITY_MEDIUM
                else "low")
    return {
        "status":   status,
        "coverage": coverage,
        "label":    _LABELS[status],
        "message":  _MESSAGES[status],
    }


def attach(recipe: dict) -> dict:
    """
    Enrichit une recette avec les champs score_reliability et score_coverage.

    Idempotent — ne recalcule que si score_reliability est absent.
    Alias de compat : score_reliability_engine.attach → reliability.attach

    Returns:
        Copie enrichie de la recette, ou la recette originale si déjà enrichie.
    """
    if "score_reliability" in recipe:
        return recipe
    r    = dict(recipe)
    data = reliability(r)
    r["score_reliability"] = data["status"]
    r["score_coverage"]    = data["coverage"]
    return r
