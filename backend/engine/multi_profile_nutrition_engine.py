"""
multi_profile_nutrition_engine.py — Adaptation AJR multi-profils.

Rôle : ajuster les références AJR (ANSES/OMS) selon les besoins nutritionnels
spécifiques de un ou plusieurs profils combinés.

Distinct de quality.py (poids de scoring 7 dims) : ici on adapte les *besoins*,
pas les *pondérations de classement*.

Profils communs avec quality.py (athlete, diabetic) : les multiplicateurs AJR
sont définis ici, les poids de scoring restent dans quality.PROFILES.
Source de vérité : quality.PROFILES pour le scoring, BASE_PROFILES ici pour l'AJR.

API :
    BASE_PROFILES                           → dict multiplicateurs AJR par profil
    get_adapted_ajr(profiles, ajr_base?)    → dict AJR adapté
    merge_profiles(profiles)                → dict multiplicateurs fusionnés
    adapt_ajr_multi(ajr_base, profiles)     → dict AJR adapté (alias compat)
    compute_multi_profile_score(...)        → float score 0-10
"""
from __future__ import annotations

# Multiplicateurs AJR par profil.
# Valeur > 1.0 = besoin accru, < 1.0 = besoin réduit.
# NB : athlete et diabetic sont aussi dans quality.PROFILES (poids scoring) —
#      ces deux dicts ont des rôles différents et ne se dupliquent pas.
BASE_PROFILES: dict[str, dict[str, float]] = {
    "vegan":     {"vitamin_b12": 2.0, "iron": 1.2},
    "athlete":   {"protein": 1.5, "magnesium": 1.2},
    "pregnancy": {"iron": 1.5, "folate": 1.5, "calcium": 1.3},
    "diabetic":  {"sugar": 0.5, "fiber": 1.5},
    "anemia":    {"iron": 2.0, "vitamin_c": 1.5, "vitamin_b12": 1.5},
}

def merge_profiles(profiles: list[str]) -> dict[str, float]:
    """Fusionne les multiplicateurs AJR de plusieurs profils (produit des facteurs)."""
    merged = {}
    for profile in profiles:
        rules = BASE_PROFILES.get(profile, {})
        for k, v in rules.items():
            if k in merged:
                merged[k] *= v
            else:
                merged[k] = v
    return merged

def adapt_ajr_multi(ajr_base: dict, profiles: list[str]) -> dict:
    """
    Retourne un AJR adapté en appliquant les multiplicateurs des profils demandés.

    Args:
        ajr_base : table AJR de référence (ex: score_engine.ajr.AJR)
        profiles : liste de profils (ex: ["athlete", "vegan"])

    Returns:
        dict AJR avec valeurs ajustées — prêt pour detect_deficiencies(ajr=...)
    """
    multipliers = merge_profiles(profiles)
    adapted = {}

    for k, v in ajr_base.items():
        factor = multipliers.get(k, 1.0)
        adapted[k] = v * factor

    return adapted

def get_adapted_ajr(profiles: list[str], ajr_base: dict | None = None) -> dict:
    """
    API publique — retourne un AJR adapté pour une liste de profils.

    Wrapper sur adapt_ajr_multi avec import automatique de l'AJR de référence.
    Utiliser cette fonction dans les routes plutôt que l'import inline.

    Args:
        profiles : ex. ["athlete", "diabetic"]
        ajr_base : AJR de référence optionnel — défaut = score_engine.ajr.AJR

    Returns:
        dict AJR adapté, prêt pour detect_deficiencies(ajr=...)
    """
    if ajr_base is None:
        from backend.engine.score_engine.ajr import AJR
        ajr_base = AJR
    return adapt_ajr_multi(ajr_base, profiles)


def compute_multi_profile_score(nutrition: dict, ajr_base: dict, profiles: list[str]) -> float:
    """
    Score nutritionnel 0-10 adapté à plusieurs profils combinés.

    Args:
        nutrition : valeurs nutritionnelles de la recette
        ajr_base  : AJR de référence (score_engine.ajr.AJR)
        profiles  : liste de profils actifs

    Returns:
        float score 0-10 (moyenne des ratios valeur/AJR adapté, plafonnée à 1)
    """
    ajr = adapt_ajr_multi(ajr_base, profiles)

    score = 0
    count = 0

    for k, ref in ajr.items():
        val = nutrition.get(k, 0)
        ratio = min(val / ref, 1.0)
        score += ratio
        count += 1

    return (score / count) * 10 if count else 0
