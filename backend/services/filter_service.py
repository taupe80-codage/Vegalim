"""
filter_service.py — Filtrage des recettes par régime alimentaire.

Correction v6.17 :
    apply_diet_filter() délégait à RecipeRepository.filter_by_diet() qui
    ignorait les alias français et ne connaissait pas la majorité des régimes.
    Fix : utilisation directe de match_diet() avec logique canonique complète.

Correction v6.18 :
    Import ALLOWED_DIETS rendu résilient (try/except). Halal/kosher retirés
    (hors taxonomie projet). Fallback local aligné sur validators.

Correction v6.19 :
    Refonte complète. Ce module ne contient plus aucune liste d'alias —
    validators.DIET_CANONICAL est la source unique de vérité.
    lactose_free et nut_free intégrés à la taxonomie.
    Baseline végétarien appliquée sur tous les appels à match_diet().

Architecture :
    validators.DIET_ALIASES   → groupes canoniques + aliases (éditer là-bas)
    validators.DIET_CANONICAL → map alias → canonique (généré automatiquement)
    _DIET_FLAG_MAP             → canonique → clé diet_flags  (ici)
    _DIET_HEALTH_MAP           → canonique → prédicat health_scores (ici)
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


# ── Import validators — source de vérité des alias ────────────────────────────

try:
    from backend.core.validators import DIET_CANONICAL, ALLOWED_DIETS
except ImportError:
    logger.critical(
        "filter_service: impossible d'importer validators. "
        "DIET_CANONICAL et ALLOWED_DIETS indisponibles — aucun filtrage ne fonctionnera."
    )
    DIET_CANONICAL: dict[str, str] = {}
    ALLOWED_DIETS:  frozenset[str] = frozenset()


# ── Tables de résolution ───────────────────────────────────────────────────────
#
# _DIET_FLAG_MAP   : clé canonique → champ dans recipe["diet_flags"]
# _DIET_HEALTH_MAP : clé canonique → prédicat sur recipe["health_scores"]
#
# Chaque clé canonique de DIET_ALIASES doit apparaître dans l'une des deux.
# Si un nouveau régime est ajouté dans validators, compléter ici.

_DIET_FLAG_MAP: dict[str, str] = {
    "vegan":        "vegan",
    "vegetarien":   "vegetarian",   # flag EN produit par compute_diet_flags()
    "gluten_free":  "gluten_free",
    "lactose_free": "lactose_free",
    "nut_free":     "nut_free",
    "raw":          "raw",
    "kid_friendly": "kid_friendly",
}

_DIET_HEALTH_MAP: dict[str, object] = {
    "diabete":       lambda hs: hs.get("glycemic_category") == "low",
    "hyperproteine": lambda hs: bool(hs.get("high_protein")),
}


# ── Logique de matching ────────────────────────────────────────────────────────

def match_diet(recipe: dict, diet: str) -> bool:
    """
    Vérifie si une recette correspond à un régime donné.

    Étapes :
      1. Normalise l'alias via DIET_CANONICAL → clé canonique
      2. Vérifie la baseline végétarienne du projet
      3. Résout via _DIET_FLAG_MAP (diet_flags) ou _DIET_HEALTH_MAP (health_scores)

    Args:
        recipe : dict recette (doit avoir diet_flags et health_scores)
        diet   : identifiant de régime — alias FR/EN acceptés

    Returns:
        True si la recette correspond au régime (ou si diet est vide).
        False si le flag est absent ou à False.
        True (pass-through + warning) si le régime est inconnu.
    """
    if not diet:
        return True

    # ── 1. Normalisation alias → canonique ────────────────────────────────────
    raw      = diet.strip().lower().replace("-", "_").replace(" ", "_")
    canonical = DIET_CANONICAL.get(raw, raw)

    flags  = recipe.get("diet_flags")  or {}
    health = recipe.get("health_scores") or {}

    # ── 2. Baseline végétarienne (contrainte projet) ───────────────────────────
    # Appliquée sur tous les régimes sauf "vegetarien" lui-même (évite le double check).
    # Si le flag est absent (recette non encore scorée), on laisse passer
    # pour ne pas bloquer les données partielles en cours d'indexation.
    if canonical != "vegetarien":
        vegetarian_flag = flags.get("vegetarian")
        if vegetarian_flag is not None and not vegetarian_flag:
            logger.warning(
                "match_diet: recette id=%s écartée — non-végétarienne (baseline projet)",
                recipe.get("id", "?"),
            )
            return False

    # ── 3a. Résolution via diet_flags ─────────────────────────────────────────
    if canonical in _DIET_FLAG_MAP:
        return bool(flags.get(_DIET_FLAG_MAP[canonical]))

    # ── 3b. Résolution via health_scores ──────────────────────────────────────
    if canonical in _DIET_HEALTH_MAP:
        return bool(_DIET_HEALTH_MAP[canonical](health))

    # ── 4. Régime inconnu ─────────────────────────────────────────────────────
    logger.warning(
        "match_diet: régime inconnu '%s' (canonique: '%s') — pass-through. "
        "Ajouter l'alias dans validators.DIET_ALIASES.",
        diet, canonical,
    )
    return True


def apply_diet_filter(recipes: list, diet: str) -> list:
    """
    Filtre une liste de recettes par régime alimentaire.

    Délègue entièrement à match_diet(). L'ordre de la liste est préservé.

    Args:
        recipes : liste de dicts recettes
        diet    : identifiant de régime (vide = pas de filtre)

    Returns:
        Sous-liste des recettes correspondant au régime.
    """
    if not diet:
        return recipes

    filtered = [r for r in recipes if match_diet(r, diet)]
    logger.debug(
        "apply_diet_filter '%s' : %d → %d recettes",
        diet, len(recipes), len(filtered),
    )
    return filtered


# Alias de compatibilité (anciens imports)
filter_recipes = apply_diet_filter
