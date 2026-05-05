"""
ajr.py — AJR, score nutritionnel et détection de carences.

Fusionne : ajr_scoring_engine + deficiency_detection_engine

API :
    AJR                                   → dict références ANSES/OMS
    ajr_score(nutrition)                  → dict {score, coverage, details}
    compute_ajr_score(nutrition)          → float (alias compat)
    detect_deficiencies(nutrition, ajr?)  → list[dict]
    summarize_deficiencies(defics)        → dict {high: [...], medium: [...]}
"""
from __future__ import annotations

# Références ANSES/OMS pour un adulte (2000 kcal/jour)
AJR: dict[str, float] = {
    "calories":   2000.0,
    "protein":      50.0,
    "carbs":       275.0,
    "fat":          70.0,
    "fiber":        30.0,
    "sugar":        50.0,
    "sodium":     2300.0,
    "iron":         14.0,
    "calcium":    1000.0,
    "magnesium":   400.0,
    "potassium":  3500.0,
    "zinc":         10.0,
    "vitamin_c":    90.0,
    "vitamin_d":    15.0,
    "vitamin_b12":   2.5,
    "phosphorus":  700.0,
}

# Nutriments à limiter (score inversé : moins = mieux)
_LIMIT = {"sodium", "sugar"}


def ajr_score(nutrition: dict) -> dict:
    """
    Score AJR 0-10 avec taux de couverture.

    Returns:
        {score: float, coverage: float, details: dict}
    """
    if not nutrition:
        return {"score": 0.0, "coverage": 0.0, "details": {}}

    ratios, details, present = [], {}, 0
    for nutrient, ref in AJR.items():
        if ref <= 0:
            continue
        val = nutrition.get(nutrient)
        if val is None:
            continue
        present += 1
        val   = float(val or 0)
        ratio = (max(0.0, 1.0 - val / ref) if nutrient in _LIMIT
                 else min(1.0, val / ref))
        ratios.append(ratio)
        details[nutrient] = {
            "value": round(val, 2),
            "ref":   ref,
            "ratio": round(ratio, 3),
            "ok":    ratio >= 0.5,
        }

    score = round(sum(ratios) / len(ratios) * 10, 2) if ratios else 0.0
    return {
        "score":    score,
        "coverage": round(present / len(AJR), 3),
        "details":  details,
    }


def compute_ajr_score(nutrition: dict) -> float:
    """
    Alias de compat ajr_scoring_engine.compute_ajr_score → float.
    Retourne le score seul (0-10) sans le détail complet.
    """
    return ajr_score(nutrition)["score"]


def detect_deficiencies(
    nutrition: dict,
    ajr: dict | None = None,
) -> list[dict]:
    """
    Détecte les carences (< 50% AJR).

    Args:
        nutrition : dict de valeurs nutritionnelles
        ajr       : table de référence optionnelle — défaut = AJR global.
                    Accepte un AJR adapté (multi_profile_nutrition_engine).

    Returns:
        Liste triée par sévérité croissante (ratio le plus bas en premier) :
        [{"nutrient": str, "ratio": float, "severity": "high"|"medium"}, ...]
    """
    if not nutrition:
        return []
    ref_table = ajr if ajr is not None else AJR
    result = []
    for nutrient, ref in ref_table.items():
        if nutrient in _LIMIT or ref <= 0:
            continue
        val   = float(nutrition.get(nutrient) or 0)
        ratio = val / ref
        if ratio < 0.5:
            result.append({
                "nutrient": nutrient,
                "ratio":    round(ratio, 3),
                "severity": "high" if ratio < 0.25 else "medium",
            })
    return sorted(result, key=lambda d: d["ratio"])


def ajr_score_multi(nutrition: dict, profiles: list[str]) -> dict:
    """
    Score AJR adapté à un ou plusieurs profils combinés.

    Combine adapt_ajr_multi (besoins ajustés) et ajr_score (calcul du score).
    À utiliser dans les routes à la place de l'import inline de adapt_ajr_multi.

    Args:
        nutrition : valeurs nutritionnelles
        profiles  : liste de profils (ex: ["athlete", "diabetic"])

    Returns:
        {score, coverage, details, profiles, ajr_adapted}
        — même structure que ajr_score() + métadonnées profils
    """
    from backend.engine.multi_profile_nutrition_engine import get_adapted_ajr
    ajr_adapted = get_adapted_ajr(profiles)
    result = ajr_score(nutrition)

    # Recalculer avec l'AJR adapté
    ratios, details, present = [], {}, 0
    for nutrient, ref in ajr_adapted.items():
        if ref <= 0:
            continue
        val = nutrition.get(nutrient)
        if val is None:
            continue
        present += 1
        val   = float(val or 0)
        ratio = (max(0.0, 1.0 - val / ref) if nutrient in _LIMIT
                 else min(1.0, val / ref))
        ratios.append(ratio)
        details[nutrient] = {
            "value": round(val, 2),
            "ref":   ref,
            "ratio": round(ratio, 3),
            "ok":    ratio >= 0.5,
        }

    score = round(sum(ratios) / len(ratios) * 10, 2) if ratios else 0.0
    return {
        "score":       score,
        "coverage":    round(present / len(ajr_adapted), 3) if ajr_adapted else 0.0,
        "details":     details,
        "profiles":    profiles,
        "ajr_adapted": ajr_adapted,
    }

    """
    Résume une liste de carences par niveau de sévérité.

    Alias de compat deficiency_detection_engine.summarize_deficiencies.

    Args:
        deficiencies : sortie de detect_deficiencies()

    Returns:
        {"high": [nutrient, ...], "medium": [nutrient, ...]}
    """
    summary: dict[str, list] = {"high": [], "medium": []}
    for d in deficiencies:
        sev = d.get("severity", "medium")
        if sev in summary:
            summary[sev].append(d["nutrient"])
    return summary
