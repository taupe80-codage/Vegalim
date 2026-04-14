"""
scoring.py — Calcul du score final et enrichissement des recettes.

Responsabilité UNIQUE : "Quel score mérite cette recette pour cet utilisateur ?"

Ce module ne touche PAS à la recherche, au filtrage, ni au learning.

API :
    score_and_enrich(recipe, context) → dict | None
    batch_score(recipes, context)     → list[dict]  triée par final_score

Formule CDC_03c :
    final_score = W_QUALITY * quality_score + W_RELEVANCE * relevance_score
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

from backend.engine.config import W_QUALITY, W_RELEVANCE


# ── Enrichissement nutrition ──────────────────────────────────────────────────

def _enrich_nutrition(recipe: dict) -> dict:
    """Attache les données nutrition via repository si absentes. Ne mute pas l'original."""
    if recipe.get("nutrition"):
        return recipe
    try:
        from backend.db.data_access import get_data
        rid  = recipe.get("id")
        # Robustesse : get_nutrition attend un int mais les IDs CDC v4 sont des strings.
        # On essaie d'abord avec l'ID tel quel, puis en version entière si applicable.
        nutr = {}
        if rid is not None:
            nutr = get_data.recipes.get_nutrition(rid) or {}
            if not nutr:
                try:
                    nutr = get_data.recipes.get_nutrition(int(rid)) or {}
                except (ValueError, TypeError):
                    pass
        if nutr:
            recipe = dict(recipe)
            recipe["nutrition"] = nutr
    except Exception as e:
        logger.debug("scoring: enrichissement nutrition échoué id=%s — %s",
                     recipe.get("id"), e)
    return recipe


# ── Score de pertinence ───────────────────────────────────────────────────────

def _extract_relevance(recipe: dict) -> float:
    """Extrait le score de pertinence produit par search_engine et le normalise sur [0, 10]."""
    from backend.core.validators import safe_float
    raw = safe_float(
        recipe.get("_search_v3", {}).get("final_score")
        or recipe.get("_search",  {}).get("final_score")
        or recipe.get("match_score", 1.0)
    )
    return round(max(0.0, min(10.0, raw)), 2)


# ── Score qualité CDC_03c ─────────────────────────────────────────────────────

def _compute_quality(recipe: dict, context) -> tuple[float, dict]:
    """
    Calcule le score qualité via scoring_service (qui délègue à score_engine).

    Returns:
        (quality_score: float, score_details: dict)
    """
    try:
        from backend.services.scoring_service import score_recipe
        result = score_recipe(
            recipe,
            profile="default",
            profile_data=context.effective_profile,
        )
        return result.get("adaptive_score", 0.0), result
    except Exception as e:
        logger.warning("scoring: score_recipe échoué id=%s — %s",
                       recipe.get("id"), e)
        return 5.0, {}


# ── Enrichissement graphe ─────────────────────────────────────────────────────

def _enrich_from_graph(recipe: dict, context) -> dict:
    """
    Enrichit la recette avec les données du graphe d'ingrédients.
    Champs ajoutés : risks, cycle_match, graph_tags.
    Ne lève jamais d'exception — graph_engine est optionnel.
    """
    try:
        from backend.engine.graph_engine import analyze_recipe
        graph = analyze_recipe(recipe, context.effective_profile)
        recipe["risks"]       = graph.get("risks")
        recipe["cycle_match"] = graph.get("cycle_match")
        recipe["graph_tags"]  = graph.get("tags")
    except Exception as e:
        logger.debug("scoring: graph_engine indisponible — %s", e)
    return recipe


# ── Explicabilité ─────────────────────────────────────────────────────────────

def _attach_reasons(recipe: dict, score_details: dict) -> dict:
    """
    Attache les raisons lisibles du score (CDC — transparence utilisateur).
    Utilise score_engine.explainer (nouveau package). Ne lève jamais d'exception.
    """
    try:
        from backend.engine.score_engine.explainer import explain
        recipe["score_reasons"] = explain(
            score_details.get("_adaptive", score_details)
        )
    except Exception as e:
        logger.debug("scoring: explainer indisponible — %s", e)
        recipe["score_reasons"] = []
    return recipe


# ── API publique ──────────────────────────────────────────────────────────────

def score_and_enrich(recipe: dict, context) -> dict | None:
    """
    Score une recette et l'enrichit avec tous les champs dérivés.

    Étapes :
        1. Enrichissement nutrition (repository)
        2. Score pertinence search  → relevance_score
        3. Score qualité CDC_03c    → quality_score
        4. Score final = W_QUALITY * quality + W_RELEVANCE * relevance
        5. Enrichissement graphe    → risks, cycle_match, graph_tags
        6. Raisons lisibles         → score_reasons

    Returns:
        Recette enrichie (dict), ou None si erreur critique.
    """
    try:
        recipe           = _enrich_nutrition(recipe)
        relevance        = _extract_relevance(recipe)
        quality, details = _compute_quality(recipe, context)
        final            = round(W_QUALITY * quality + W_RELEVANCE * relevance, 2)

        recipe.update({
            "final_score":     final,
            "quality_score":   round(quality, 2),
            "relevance_score": relevance,
            "_adaptive":       details,
        })

        recipe = _enrich_from_graph(recipe, context)
        recipe = _attach_reasons(recipe, details)
        return recipe

    except Exception as e:
        logger.warning("scoring: erreur recette id=%s — %s", recipe.get("id"), e)
        return None


def batch_score(recipes: list[dict], context) -> list[dict]:
    """
    Score une liste de recettes et retourne la liste triée par final_score décroissant.
    Les recettes qui échouent au scoring sont exclues avec un log WARNING (pas silencieux).
    """
    scored  = []
    dropped = 0
    for recipe in recipes:
        result = score_and_enrich(recipe, context)
        if result is not None:
            scored.append(result)
        else:
            dropped += 1
            logger.warning(
                "batch_score: recette exclue id=%s titre='%s'",
                recipe.get("id"), recipe.get("titles", {}).get("fr", "?")
            )

    if dropped:
        logger.warning("batch_score: %d/%d recettes exclues — vérifier les warnings ci-dessus",
                       dropped, len(recipes))

    scored.sort(key=lambda r: r.get("final_score", 0), reverse=True)
    return scored
