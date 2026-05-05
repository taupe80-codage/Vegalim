"""
Routes plan repas, liste de courses, saisonnalité.

MIGRATION étape 3 — imports obsolètes remplacés :
  meal_planner.generate_weekly_plan   → planning_engine.planner.generate_plan
  meal_planner.rank_recipes           → conservé via compat (non migré)
  meal_planner._filter_diet           → planning_engine : filtrage via filter_service
  shopping_engine.generate_shopping_list → planning_engine.shopping.shopping_list
  seasonality_engine.ingredients_in_season → rule_engine.seasonality.seasonal_ingredients
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional

from backend.core.auth_deps import get_user, require_feature

router = APIRouter(prefix="/planning", tags=["Planification"])


# ── Modèles Pydantic ──────────────────────────────────────────────────────────

class MealPlanExportRequest(BaseModel):
    plan:       dict          = Field(..., description="Plan hebdo {lundi:{lunch:{id,title}}}")
    start_date: Optional[str] = Field(default=None, description="Date ISO YYYY-MM-DD")


class ShoppingListRequest(BaseModel):
    plan: dict = Field(..., description="Plan hebdo {lundi:{lunch:{id,title}}}")


class DiversityScoreRequest(BaseModel):
    plan: dict = Field(..., description="Plan hebdo {lundi:{lunch:{id,title}}}")


class MealPlanReplaceRequest(BaseModel):
    plan:        dict              = Field(..., description="Plan hebdo existant")
    day:         str               = Field(..., description="Jour : monday|tuesday|…")
    slot:        str               = Field(..., description="Repas : lunch|dinner|breakfast")
    exclude_ids: Optional[list[int]] = Field(default=None)
    diet:        Optional[str]     = Field(default=None)


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/mealplan")
def mealplan(
    diet:          Optional[str] = None,
    servings:      int           = 4,
    month:         Optional[int] = None,
    cycle:         Optional[str] = None,
    batch:         bool          = False,
    meals_per_day: int           = Query(default=2, ge=2, le=3),
    _user = require_feature("mealplan"),
):
    """
    Génère un plan de repas hebdomadaire personnalisé. [Plan premium]
    """
    from backend.core.validators import is_valid_diet
    from backend.engine.planning_engine.planner import generate_plan        # ✅ migré
    if not is_valid_diet(diet):
        from fastapi import HTTPException
        from backend.core.validators import ALLOWED_DIETS
        raise HTTPException(status_code=422,
            detail=f"Régime invalide : '{diet}'. Valeurs acceptées : {sorted(ALLOWED_DIETS)}")
    return generate_plan(
        diet=diet,
        month=month,
        batch_cooking=batch,
    )


@router.post("/mealplan/export_ics")
def export_ics(payload: MealPlanExportRequest, user: dict = Depends(get_user)):
    """Exporte un plan de repas au format .ics (calendrier)."""
    from datetime import date, timedelta
    plan = payload.plan
    try:
        start = date.fromisoformat(payload.start_date) if payload.start_date else date.today()
    except ValueError:
        start = date.today()

    DAYS  = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//AlimUnified//FR",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]

    for i, day in enumerate(DAYS):
        for slot, info in (plan.get(day) or {}).items():
            if not isinstance(info, dict):
                continue
            d = (start + timedelta(days=i)).strftime("%Y%m%d")
            h = "120000" if slot == "lunch" else "190000"
            lines += [
                "BEGIN:VEVENT",
                f"UID:{d}-{slot}@alimunified",
                f"DTSTART;VALUE=DATE-TIME:{d}T{h}",
                "DURATION:PT30M",
                f"SUMMARY:{slot} — {info.get('title', slot)}",
                "END:VEVENT",
            ]
    lines.append("END:VCALENDAR")
    return {
        "ics_content": "\r\n".join(lines),
        "filename":    f"plan_{start.isoformat()}.ics",
    }


@router.post("/shopping_list")
def shopping_list_route(payload: ShoppingListRequest, user: dict = Depends(get_user)):
    """Génère la liste de courses depuis un plan hebdomadaire."""
    from backend.engine.planning_engine.shopping import shopping_list       # ✅ migré
    return shopping_list(payload.plan)


@router.get("/seasonal")
def seasonal(month: int):
    """Ingrédients de saison pour un mois donné (1-12). **Public.**"""
    from backend.engine.rule_engine.seasonality import seasonal_ingredients # ✅ migré
    from backend.core.data_io import load_ingredients_dict
    try:
        d        = load_ingredients_dict()
        id_to_fr = {k: v.get("name_fr", k.replace("_", " ").title()) for k, v in d.items()}
    except Exception:
        id_to_fr = {}
    ids = seasonal_ingredients(month)
    return {
        "month":          month,
        "ingredients":    ids,
        "ingredients_fr": [{"id": i, "nom": id_to_fr.get(i, i)} for i in ids],
    }


@router.post("/diversity_score")
def diversity_score(payload: DiversityScoreRequest, user: dict = Depends(get_user)):
    """Calcule le score de diversité nutritionnelle d'un plan hebdomadaire."""
    from backend.core.data_io import load_recipes
    plan = payload.plan
    rmap = {r["id"]: r for r in load_recipes()}
    cuisines, techs, colors, ings = set(), set(), set(), set()
    n = 0
    for day_data in plan.values():
        if not isinstance(day_data, dict):
            continue
        for info in day_data.values():
            if not isinstance(info, dict):
                continue
            r = rmap.get(info.get("id"), {})
            n += 1
            c = (r.get("iconic_status") or {}).get("cuisine_origin", "")
            t = r.get("technique", "")
            p = r.get("color_palette", "")
            if c: cuisines.add(c)
            if t: techs.add(t[0] if isinstance(t, list) and t else str(t))
            if p: colors.add(p)
            ings.update(str(i) for i in r.get("ingredients", []))
    return {
        "diversity_score": (
            min(len(cuisines) * 10, 40) +
            min(len(techs)    * 8,  30) +
            min(len(colors)   * 6,  20) +
            min(len(ings) // 3,     10)
        ),
        "cuisines":   len(cuisines),
        "techniques": len(techs),
        "n_recipes":  n,
    }


@router.post("/mealplan/replace")
def replace_meal(payload: MealPlanReplaceRequest, user: dict = Depends(get_user)):
    """
    Remplace un seul repas dans un plan existant sans recalculer tout le plan.
    """
    from backend.core.data_io import load_recipes, load_nutrition_graph
    from backend.services.filter_service import apply_diet_filter

    VALID_DAYS  = {"monday", "tuesday", "wednesday", "thursday",
                   "friday", "saturday", "sunday"}
    VALID_SLOTS = {"lunch", "dinner", "breakfast"}
    if payload.day not in VALID_DAYS:
        raise HTTPException(status_code=422, detail=f"Jour invalide : {payload.day}")
    if payload.slot not in VALID_SLOTS:
        raise HTTPException(status_code=422, detail=f"Repas invalide : {payload.slot}")

    existing_ids = set(payload.exclude_ids or [])
    for day_data in payload.plan.values():
        if isinstance(day_data, dict):
            for slot_data in day_data.values():
                if isinstance(slot_data, dict) and slot_data.get("id"):
                    existing_ids.add(slot_data["id"])

    if payload.diet:
        from backend.core.validators import is_valid_diet, ALLOWED_DIETS
        if not is_valid_diet(payload.diet):
            raise HTTPException(status_code=422,
                detail=f"Régime invalide : '{payload.diet}'. Valeurs acceptées : {sorted(ALLOWED_DIETS)}")

    load_recipes.cache_clear()
    recipes    = list(load_recipes())
    candidates = apply_diet_filter(recipes, payload.diet) if payload.diet else recipes
    candidates = [r for r in candidates if r["id"] not in existing_ids]

    if not candidates:
        raise HTTPException(status_code=404,
            detail="Aucune recette disponible pour ce remplacement")

    # Tri simple par iconic_score (rank_recipes n'est plus importé directement)
    candidates.sort(key=lambda r: r.get("scoring", {}).get("iconic", {}).get("score", 0), reverse=True)
    new_rec = candidates[0]
    ng      = load_nutrition_graph()
    nutr    = ng.get(str(new_rec["id"]), {})

    new_slot = {
        "title":    new_rec.get("titles", {}).get("original") or new_rec.get("titles", {}).get("fr"),
        "id":       new_rec["id"],
        "calories": nutr.get("calories"),
        "protein":  nutr.get("protein"),
        "vegan":    (new_rec.get("diet_flags") or {}).get("vegan", False),
    }
    updated_plan = dict(payload.plan)
    if payload.day not in updated_plan:
        updated_plan[payload.day] = {}
    updated_plan[payload.day][payload.slot] = new_slot

    return {"plan": updated_plan, "replaced": new_slot,
            "day": payload.day, "slot": payload.slot}
