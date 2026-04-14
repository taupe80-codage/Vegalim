"""
reco_engine/ — Moteur de recommandation ALIM.

STRUCTURE INTERNE :
    orchestrator.py     → pipeline principal, point d'entrée public
    personalization.py  → profil utilisateur, learning, exclusions
    scoring.py          → score final CDC_03c, enrichissement recettes

API PUBLIQUE — identique à l'ancien recommendation_engine.py :
    from backend.engine.reco_engine import recommend, RecommendationResult
"""
from backend.engine.reco_engine.orchestrator import recommend, RecommendationResult

__all__ = ["recommend", "RecommendationResult"]
