"""
score_engine/ — Moteur de scoring nutritionnel et qualitatif (CDC_03c).

Fusionne 7 engines :
    global_score_engine + adaptive_score_engine_v4
    health_score_engine + ajr_scoring_engine
    score_reliability_engine + deficiency_detection_engine
    score_explainer

API PUBLIQUE :
    from backend.engine.score_engine import (
        score_recipe, score_batch, PROFILES,
        health_score,
        AJR, ajr_score, compute_ajr_score,
        detect_deficiencies, summarize_deficiencies,
        reliability, attach,
        explain,
    )
"""
from backend.engine.score_engine.quality import (
    score_recipe,
    score_batch,
    PROFILES,
)
from backend.engine.score_engine.health import health_score
from backend.engine.score_engine.ajr import (
    AJR,
    ajr_score,
    compute_ajr_score,
    detect_deficiencies,
    summarize_deficiencies,
)
from backend.engine.score_engine.reliability import reliability, attach
from backend.engine.score_engine.explainer import explain

__all__ = [
    # Scoring qualité
    "score_recipe", "score_batch", "PROFILES",
    # Santé plan repas
    "health_score",
    # AJR + carences
    "AJR", "ajr_score", "compute_ajr_score",
    "detect_deficiencies", "summarize_deficiencies",
    # Fiabilité
    "reliability", "attach",
    # Explicabilité
    "explain",
]
