"""
recommendation_engine.py — Shim de compatibilité ascendante.

MIGRATION TERMINÉE : toute la logique est dans reco_engine/.

Ce fichier existe uniquement pour ne pas casser les imports existants
qui n'ont pas encore été migrés (routes, tests, scripts).

À SUPPRIMER une fois que tous les imports pointent vers reco_engine.

Checklist avant suppression :
    grep -r "from backend.engine.recommendation_engine" backend/ tests/
    → doit retourner 0 résultats (hors ce fichier et _archive/)
"""
from backend.engine.reco_engine.orchestrator import (
    recommend,
    RecommendationResult,
)

__all__ = ["recommend", "RecommendationResult"]
