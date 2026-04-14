"""
advanced_scoring.py — Shim de compatibilité ascendante.

Redirige vers reco_engine.orchestrator directement.
Plus de passage par recommendation_engine.py (lui-même un shim).

À migrer progressivement vers des imports directs de reco_engine.
"""
import logging

from backend.engine.reco_engine.orchestrator import recommend as _recommend

logger = logging.getLogger(__name__)


def recommend(
    query:         str        = "",
    email:         str | None = None,
    diet_override: str | None = None,
    limit:         int        = 20,
) -> list[dict]:
    """
    Délègue à reco_engine.orchestrator.recommend().
    Conserve l'interface list[dict] pour compat ascendante.
    """
    return _recommend(
        query=query,
        email=email,
        diet_override=diet_override,
        limit=limit,
    ).recipes
