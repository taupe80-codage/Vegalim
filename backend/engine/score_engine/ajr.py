"""
ajr.py — AJR, score nutritionnel et détection de carences.

Fusionne : ajr_scoring_engine + deficiency_detection_engine

API :
    AJR                                        → dict références ANSES/OMS
    NUTRIENT_WEIGHTS                           → poids par nutriment (score pondéré)
    ajr_score(nutrition, weights?)             → dict {score, coverage, details}
    compute_ajr_score(nutrition)               → float (alias compat)
    ajr_score_with_profile(nutrition, profile) → float (ex score_nutrition_values)
    ajr_score_multi(nutrition, profiles)       → dict {score, coverage, ...}
    detect_deficiencies(nutrition, ajr?)       → list[dict]
    summarize_deficiencies(deficiencies)       → dict {high: [...], medium: [...]}

Scoring pondéré (NUTRIENT_WEIGHTS)
-----------------------------------
Pour une plateforme végétarienne/vegan, les micronutriments à risque de carence
(fer, B12, calcium, zinc, vitamine D) sont pondérés 2x afin que le score reflète
mieux la qualité nutritionnelle réelle d'une recette plant-based.
Les macros (calories, carbs, fat) reçoivent un poids réduit : ils sont faciles à
couvrir et ne discriminent pas les recettes végétales de qualité.

Corrections appliquées :
    - summarize_deficiencies était piégée à l'intérieur de ajr_score_multi
      après son return — fonction morte, désormais correctement définie.
    - ajr_score_multi dupliquait intégralement le calcul d'ajr_score —
      refactorisé pour réutiliser la logique commune.
    - score_nutrition_values (nutrition_engine) migré ici en tant que
      ajr_score_with_profile — responsabilité dans le bon module.
"""
from __future__ import annotations

# ── Références ANSES/OMS pour un adulte (2000 kcal/jour) ─────────────────────

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

# ── Poids par nutriment ───────────────────────────────────────────────────────
# Micronutriments à risque de carence en alimentation végétarienne/vegan : x2.
# Macros peu discriminants pour la qualité d'une recette plant-based : x0.5.
# Valeur par défaut (nutriments non listés) : 1.0.
NUTRIENT_WEIGHTS: dict[str, float] = {
    # Micronutriments prioritaires (végétarien/vegan)
    "iron":        2.0,   # carence fréquente en plant-based
    "vitamin_b12": 2.0,   # critique pour les véganes
    "calcium":     2.0,   # os + véganes sans produits laitiers
    "zinc":        2.0,   # biodisponibilité réduite dans les végétaux
    "vitamin_d":   2.0,   # déficience très répandue
    # Micronutriments importants
    "magnesium":   1.5,
    "vitamin_c":   1.5,
    "fiber":       1.5,   # marqueur fort de qualité végétale
    "potassium":   1.0,
    "phosphorus":  1.0,
    # Macros moins discriminants
    "protein":     1.0,
    "sodium":      1.0,
    "sugar":       1.0,
    "calories":    0.5,
    "carbs":       0.5,
    "fat":         0.5,
}


# ── Score AJR ─────────────────────────────────────────────────────────────────

def ajr_score(
    nutrition: dict,
    weights: dict[str, float] | None = None,
) -> dict:
    """
    Score AJR pondéré 0-10 avec taux de couverture.

    Args:
        nutrition : valeurs nutritionnelles de la recette
        weights   : poids par nutriment. Défaut = NUTRIENT_WEIGHTS.
                    Passer {} pour un score non pondéré (moyenne simple).

    Returns:
        {score: float, coverage: float, details: dict}
    """
    if not nutrition:
        return {"score": 0.0, "coverage": 0.0, "details": {}}

    w = NUTRIENT_WEIGHTS if weights is None else weights
    weighted_ratios, total_weight, details, present = [], 0.0, {}, 0

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
        nw    = w.get(nutrient, 1.0)
        weighted_ratios.append(ratio * nw)
        total_weight += nw
        details[nutrient] = {
            "value":  round(val, 2),
            "ref":    ref,
            "ratio":  round(ratio, 3),
            "weight": nw,
            "ok":     ratio >= 0.5,
        }

    score = (
        round(sum(weighted_ratios) / total_weight * 10, 2)
        if total_weight > 0 else 0.0
    )
    return {
        "score":    score,
        "coverage": round(present / len(AJR), 3),
        "details":  details,
    }


def compute_ajr_score(nutrition: dict) -> float:
    """Alias compat ajr_scoring_engine.compute_ajr_score -> float."""
    return ajr_score(nutrition)["score"]


# ── Score avec ajustements profil ─────────────────────────────────────────────

def ajr_score_with_profile(
    nutrition: dict,
    profile: dict | None = None,
) -> float:
    """
    Score AJR 0-10 avec ajustements profil utilisateur.

    Anciennement nutrition_engine.score_nutrition_values().
    Déplacé ici : c'est une fonction de scoring, pas de calcul nutritionnel.

    Ajustements après score AJR de base :
        - Malus sucre renforcé pour profil diabète / low_sugar
        - Bonus protéine pour profil hyperprotéiné

    Args:
        nutrition : valeurs nutritionnelles
        profile   : dict profil utilisateur (diet, low_sugar, ...) ou None

    Returns:
        Score 0-10
    """
    if not nutrition or not isinstance(nutrition, dict):
        return 0.0

    base = ajr_score(nutrition)["score"]
    p    = profile or {}
    diet = p.get("diet", "")

    sugar   = float(nutrition.get("sugar",   0) or 0)
    protein = float(nutrition.get("protein", 0) or 0)

    delta = 0.0
    if diet == "diabete" or p.get("low_sugar"):
        delta -= min(sugar * 0.1, 2.0)   # malus sucre renforcé
    else:
        delta -= min(sugar * 0.02, 0.5)  # malus sucre standard

    if diet == "hyperproteine":
        delta += min(protein * 0.1, 2.0)  # bonus protéine

    return round(max(0.0, min(10.0, base + delta)), 2)


# ── Score multi-profils ────────────────────────────────────────────────────────

def ajr_score_multi(nutrition: dict, profiles: list[str]) -> dict:
    """
    Score AJR adapté à un ou plusieurs profils combinés.

    Args:
        nutrition : valeurs nutritionnelles
        profiles  : liste de profils (ex: ["athlete", "diabetic"])

    Returns:
        {score, coverage, details, profiles, ajr_adapted}
    """
    from backend.engine.multi_profile_nutrition_engine import get_adapted_ajr
    ajr_adapted = get_adapted_ajr(profiles)

    if not nutrition or not ajr_adapted:
        return {"score": 0.0, "coverage": 0.0, "details": {},
                "profiles": profiles, "ajr_adapted": ajr_adapted}

    # Réutilise ajr_score en substituant la table de référence via un AJR
    # temporaire — évite de dupliquer la logique de calcul.
    tmp_nutrition = dict(nutrition)
    w = NUTRIENT_WEIGHTS
    weighted_ratios, total_weight, details, present = [], 0.0, {}, 0

    for nutrient, ref in ajr_adapted.items():
        if ref <= 0:
            continue
        val = tmp_nutrition.get(nutrient)
        if val is None:
            continue
        present += 1
        val   = float(val or 0)
        ratio = (max(0.0, 1.0 - val / ref) if nutrient in _LIMIT
                 else min(1.0, val / ref))
        nw    = w.get(nutrient, 1.0)
        weighted_ratios.append(ratio * nw)
        total_weight += nw
        details[nutrient] = {
            "value":  round(val, 2),
            "ref":    ref,
            "ratio":  round(ratio, 3),
            "weight": nw,
            "ok":     ratio >= 0.5,
        }

    score = (
        round(sum(weighted_ratios) / total_weight * 10, 2)
        if total_weight > 0 else 0.0
    )
    return {
        "score":       score,
        "coverage":    round(present / len(ajr_adapted), 3),
        "details":     details,
        "profiles":    profiles,
        "ajr_adapted": ajr_adapted,
    }


# ── Détection de carences ─────────────────────────────────────────────────────

def detect_deficiencies(
    nutrition: dict,
    ajr: dict | None = None,
) -> list[dict]:
    """
    Détecte les carences (< 50% AJR).

    Args:
        nutrition : dict de valeurs nutritionnelles
        ajr       : table de référence optionnelle — défaut = AJR global.

    Returns:
        Liste triée par sévérité croissante :
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


def summarize_deficiencies(deficiencies: list[dict]) -> dict:
    """
    Résume une liste de carences par niveau de sévérité.

    Alias compat deficiency_detection_engine.summarize_deficiencies.

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
