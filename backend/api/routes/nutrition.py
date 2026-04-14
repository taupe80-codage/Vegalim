"""
Routes nutrition, AJR, carences, cycle féminin.

MIGRATION — imports archivés remplacés :
  ajr_scoring_engine.*          → score_engine.ajr.*
  deficiency_detection_engine.* → score_engine.ajr.*

Conservés (engines actifs non encore migrés) :
  multi_profile_nutrition_engine.adapt_ajr_multi
  cycle_engine.cycle_score
  correction_engine.recommend_corrections
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from typing import Optional

from backend.core.auth_deps    import get_user, get_optional_user
from backend.core.rate_limiter import check_rate_limit

# Imports migrés en tête — remplacent les 6 imports inline répétés   ✅
from backend.engine.score_engine.ajr import (
    AJR,
    compute_ajr_score,
    detect_deficiencies,
    summarize_deficiencies,
)

router = APIRouter(prefix="/nutrition", tags=["Nutrition"])


# ── Modèles Pydantic ──────────────────────────────────────────────────────────

class AJRRequest(BaseModel):
    recipe_id: Optional[int]        = Field(default=None,
                                            description="ID recette (source CIQUAL)")
    nutrition:  Optional[dict]      = Field(default=None,
                                            description="Dict nutrition {calories, protein…}")


class DeficiencyRequest(BaseModel):
    nutrition: dict                 = Field(...,
                                            description="Valeurs nutritionnelles {calories, iron…}")
    profiles:  list[str]            = Field(default=[],
                                            description="Profils santé [diabete, anemia…]")


class CycleScoreRequest(BaseModel):
    recipe:    dict                 = Field(..., description="Recette à scorer")
    phase:     Optional[str]        = Field(default=None,
                                            description="menstrual|follicular|ovulatory|luteal")
    cycle_day: Optional[int]        = Field(default=None, ge=1, le=35)


class NutritionAlertsRequest(BaseModel):
    plan:       Optional[dict]      = Field(default=None,
                                            description="Plan hebdo {lundi:{lunch:{id,title}}}")
    recipe_ids: Optional[list[int]] = Field(default=None,
                                            description="IDs recettes du plan")


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/ajr_score")
def ajr_score_route(
    payload: AJRRequest,
    request: Request,
    user: dict | None = Depends(get_optional_user),
):
    """
    Score AJR d'une recette ou d'un profil nutritionnel.
    Accepte un `recipe_id` (source graphe CIQUAL) ou un dict `nutrition` direct.
    **Public** — outil de calcul gratuit (CDC_11).
    """
    check_rate_limit(request, limit=30, window_seconds=60)
    from backend.core.data_io import load_nutrition_graph

    nutr = (load_nutrition_graph().get(str(payload.recipe_id), {})
            if payload.recipe_id is not None
            else payload.nutrition or {})

    defics = detect_deficiencies(nutr)
    return {
        "ajr_score":    round(compute_ajr_score(nutr), 2),
        "deficiencies": defics,
        "summary":      summarize_deficiencies(defics),
    }


@router.post("/detect_deficiencies")
def route_detect_deficiencies(
    payload: DeficiencyRequest,
    request: Request,
    user: dict = Depends(get_user),
):
    """Détecte les déficiences nutritionnelles avec adaptation multi-profils."""
    check_rate_limit(request, limit=20, window_seconds=60)

    if payload.profiles:
        from backend.engine.multi_profile_nutrition_engine import adapt_ajr_multi
        ajr_ref = adapt_ajr_multi(AJR, payload.profiles)
    else:
        ajr_ref = AJR

    defics = detect_deficiencies(payload.nutrition, ajr_ref)
    return {
        "deficiencies": defics,
        "summary":      summarize_deficiencies(defics),
    }


@router.post("/cycle_score")
def route_cycle_score(
    payload: CycleScoreRequest,
    user: dict = Depends(get_user),
):
    """Score d'adéquation d'une recette à une phase du cycle féminin."""
    from backend.engine.cycle_engine import cycle_score
    return cycle_score(
        recipe    = payload.recipe,
        phase     = payload.phase,
        cycle_day = payload.cycle_day,
    )


@router.post("/alerts")
def nutrition_alerts(
    payload: NutritionAlertsRequest,
    user: dict = Depends(get_user),
):
    """Alertes carences moyennes sur un plan de repas hebdomadaire."""
    from backend.engine.correction_engine import recommend_corrections
    from backend.core.data_io             import load_nutrition_graph

    nutr_g = load_nutrition_graph()
    rids   = payload.recipe_ids or []

    if payload.plan and not rids:
        rids = [
            info.get("id")
            for day in payload.plan.values() if isinstance(day, dict)
            for info in day.values()
            if isinstance(info, dict) and info.get("id")
        ]

    totals: dict = {}
    for rid in filter(None, rids):
        for k, v in nutr_g.get(str(rid), {}).items():
            if isinstance(v, (int, float)):
                totals[k] = totals.get(k, 0) + v

    n_meals = max(len(rids), 1)
    avg     = {k: round(v / n_meals, 1) for k, v in totals.items()}
    defics  = detect_deficiencies(avg)

    return {
        "deficiencies": defics,
        "summary":      summarize_deficiencies(defics),
        "corrections":  recommend_corrections(defics[:5]),
        "avg_per_meal": avg,
    }
