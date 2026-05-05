"""
correction_engine.py — Recommandations alimentaires correctives.

Rôle : à partir d'une liste de carences (sortie de score_engine.ajr.detect_deficiencies),
propose des aliments sources pour combler chaque déficit nutritionnel.

Périmètre :
    - Mapping nutriment → ingrédients correcteurs (NUTRIENT_TO_INGREDIENTS)
    - recommend_corrections() : API principale, consommée par routes/nutrition.py /alerts

Utilisé en production via :
    POST /nutrition/alerts  →  correction_engine.recommend_corrections(defics[:5])

Migration : aucune migration en cours. Ce module est stable.
"""
from __future__ import annotations
import warnings


# Mapping nutriment → ingrédients correcteurs.
# Couvre tous les nutriments de score_engine.ajr.AJR hors nutriments à limiter
# (sodium, sugar — pas de correction "manger plus" pertinente).
NUTRIENT_TO_INGREDIENTS: dict[str, list[str]] = {
    "calories":    ["olive_oil", "nuts", "avocado"],
    "protein":     ["lentils", "beans", "tofu"],
    "carbs":       ["whole_grains", "oats", "sweet_potato"],
    "fat":         ["olive_oil", "nuts", "avocado"],
    "fiber":       ["vegetables", "whole_grains", "legumes"],
    "iron":        ["lentils", "spinach", "chickpeas"],
    "calcium":     ["milk", "yogurt", "tofu"],
    "magnesium":   ["nuts", "seeds", "dark_chocolate"],
    "potassium":   ["banana", "potato", "legumes"],
    "zinc":        ["beef", "pumpkin_seeds", "chickpeas"],
    "vitamin_c":   ["bell_pepper", "kiwi", "broccoli"],
    "vitamin_d":   ["salmon", "egg", "fortified_milk"],
    "vitamin_b12": ["fortified_cereal", "milk", "egg"],
    "phosphorus":  ["fish", "dairy", "whole_grains"],
}


def recommend_corrections(deficiencies: list[dict]) -> list[dict]:
    """
    Génère des recommandations alimentaires pour une liste de carences.

    Args:
        deficiencies : sortie de detect_deficiencies() —
                       [{"nutrient": str, "severity": str, "ratio": float}, ...]

    Returns:
        Liste de recommandations triées par sévérité décroissante :
        [{"nutrient": str, "severity": str, "recommendations": list[str]}, ...]
    """
    _PRIORITY = {"high": 2, "medium": 1}
    recommendations = []

    for d in deficiencies:
        nutrient = d["nutrient"]
        foods    = NUTRIENT_TO_INGREDIENTS.get(nutrient, [])
        recommendations.append({
            "nutrient":        nutrient,
            "severity":        d["severity"],
            "recommendations": foods[:3],
        })

    return sorted(recommendations, key=lambda x: _PRIORITY.get(x["severity"], 0), reverse=True)


def rank_corrections(recommendations: list[dict]) -> list[dict]:
    """
    .. deprecated::
        Utilisez recommend_corrections() directement — le tri par sévérité
        est désormais intégré. rank_corrections() sera supprimée dans la
        prochaine version majeure.
    """
    warnings.warn(
        "rank_corrections() est dépréciée. recommend_corrections() trie déjà par sévérité.",
        DeprecationWarning,
        stacklevel=2,
    )
    _PRIORITY = {"high": 2, "medium": 1}
    return sorted(
        recommendations,
        key=lambda x: _PRIORITY.get(x["severity"], 0),
        reverse=True,
    )
