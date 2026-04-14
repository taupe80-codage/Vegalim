"""
reco_service.py — Service de recommandation (point d'entrée unique).

Délègue à reco_engine/orchestrator.
Expose deux interfaces :
    recommend()      → list[dict]          (compat ascendante, utilisée par les routes)
    recommend_full() → RecommendationResult (interface riche, avec meta et timing)

AVANT : pointait vers recommendation_engine.py (fichier monolithique)
APRÈS : pointe directement vers reco_engine.orchestrator (pipeline découpé)

Consommateurs actuels :
    backend/api/routes/recipes.py      → recommend()
    backend/api/main.py                → recommend()
"""
import logging

from backend.engine.reco_engine.orchestrator import (
    recommend as _recommend,
    RecommendationResult,
)

logger = logging.getLogger(__name__)


def recommend(
    query:         str        = "",
    email:         str | None = None,
    diet_override: str | None = None,
    limit:         int        = 20,
) -> list[dict]:
    """
    Recommande des recettes. Interface list[dict] pour compat ascendante.

    Args:
        query         : texte libre
        email         : email utilisateur (active profil + learning)
        diet_override : filtre régime forcé
        limit         : nombre max de recettes retournées

    Returns:
        list[dict] — recettes scorées et triées
    """
    return _recommend(
        query=query,
        email=email,
        diet_override=diet_override,
        limit=limit,
    ).recipes


def recommend_full(
    query:         str        = "",
    email:         str | None = None,
    diet_override: str | None = None,
    limit:         int        = 20,
) -> RecommendationResult:
    """
    Recommande des recettes. Interface riche avec meta, timing et profile_used.

    Returns:
        RecommendationResult avec .recipes, .meta, .timing_ms, .profile_used
    """
    return _recommend(
        query=query,
        email=email,
        diet_override=diet_override,
        limit=limit,
    )


__all__ = ["recommend", "recommend_full", "RecommendationResult"]
