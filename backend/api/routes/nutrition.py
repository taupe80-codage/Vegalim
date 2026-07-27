"""
Routes nutrition, AJR, carences, cycle féminin.

MIGRATION — imports archivés remplacés :
  ajr_scoring_engine.*          → score_engine.ajr.*
  deficiency_detection_engine.* → score_engine.ajr.*

Conservés (engines actifs non encore migrés) :
  multi_profile_nutrition_engine.adapt_ajr_multi
  cycle_engine.cycle_score
  correction_engine.recommend_corrections

Ajout v6.17 — feature dual nutrition source :
  GET  /nutrition/ingredient/{ingredient_id}         → nutrition pour 100g
  GET  /nutrition/ingredient/{ingredient_id}/sources → sources disponibles
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, Literal

from backend.core.auth_deps    import get_user, get_optional_user
from backend.core.rate_limiter import check_rate_limit

# Imports migrés en tête — remplacent les 6 imports inline répétés   ✅
from backend.engine.score_engine.ajr import (
    AJR,
    ajr_score,
    compute_ajr_score,
    detect_deficiencies,
    summarize_deficiencies,
    ajr_score_multi,
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


# ── Routes existantes ─────────────────────────────────────────────────────────

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

    scored = ajr_score(nutr)
    defics = detect_deficiencies(nutr)
    return {
        "ajr_score":    round(scored["score"], 2),
        "coverage":     scored["coverage"],
        "details":      scored["details"],
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
        from backend.engine.multi_profile_nutrition_engine import get_adapted_ajr
        ajr_ref = get_adapted_ajr(payload.profiles)
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


# ── Routes dual nutrition source (v6.17) ──────────────────────────────────────
#
# Ces endpoints exposent la feature dual pour les laits/crèmes végétaux et
# tout futur ingrédient avec nutrition_source_mode='dual'.
#
# L'UI peut :
#   1. Vérifier si un ingrédient a deux sources → GET /ingredient/{id}/sources
#   2. Obtenir la nutrition avec la source choisie → GET /ingredient/{id}?source=recipe
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/ingredient/{ingredient_id}/sources")
def get_ingredient_sources(
    ingredient_id: str,
    user: dict | None = Depends(get_optional_user),
):
    """
    Retourne les sources nutritionnelles disponibles pour un ingrédient.

    Permet à l'UI de savoir si un choix industriel/recette est proposable.
    Pour les ingrédients standard, retourne uniquement `['industrial']`.
    Pour les ingrédients dual (laits/crèmes végétaux), retourne `['industrial', 'recipe']`.

    **Public** — utilisé par l'UI pour afficher ou masquer le sélecteur de source.

    Réponse :
    ```json
    {
      "ingredient_id": "milk_plant_oat",
      "name_fr": "lait d'avoine",
      "dual": true,
      "available_sources": ["industrial", "recipe"],
      "base_recipe_id": "base_oat_milk_3519f4",
      "base_recipe_title_fr": "Lait d'Avoine Maison"
    }
    ```
    """
    from backend.core.data_io import load_ingredients_dict, load_recipes

    ings = load_ingredients_dict()
    if ingredient_id not in ings:
        raise HTTPException(status_code=404, detail=f"Ingrédient inconnu : {ingredient_id}")

    ing             = ings[ingredient_id]
    mode            = ing.get("nutrition_source_mode", "industrial")
    base_recipe_key = ing.get("base_recipe_key")
    is_dual         = mode == "dual" and bool(base_recipe_key)

    sources = ["industrial"]
    recipe_title = None

    if is_dual:
        sources.append("recipe")
        # Résoudre le titre de la recette maison
        try:
            recipes = load_recipes()
            rec = next((r for r in recipes if r.get("id") == base_recipe_key), None)
            if rec:
                recipe_title = (
                    rec.get("titles", {}).get("fr")
                    or rec.get("titles", {}).get("en")
                )
        except Exception:
            pass

    return {
        "ingredient_id":       ingredient_id,
        "name_fr":             ing.get("canonical_name_fr", ingredient_id),
        "dual":                is_dual,
        "available_sources":   sources,
        "base_recipe_id":      base_recipe_key if is_dual else None,
        "base_recipe_title_fr": recipe_title,
    }


@router.get("/ingredient/{ingredient_id}")
def get_ingredient_nutrition(
    ingredient_id: str,
    source:  str = Query(default="industrial",
                         description="Source : 'industrial' (CIQUAL/USDA) ou 'recipe' (maison)"),
    variant: str = Query(default="default",
                         description="Variante nutritionnelle (ex: 'oat', 'soy', 'default')"),
    request: Request = None,
    user: dict | None = Depends(get_optional_user),
):
    """
    Nutrition pour 100g d'un ingrédient, avec sélection de source pour les duaux.

    Pour les ingrédients standard : `source` est ignoré, retourne toujours
    les données CIQUAL/USDA de nutrition_v2.json.

    Pour les ingrédients dual (laits/crèmes végétaux) :
    - `source=industrial` (défaut) : données CIQUAL/USDA industrielles
    - `source=recipe`              : calculé depuis la composition de la recette maison
      (ratios pondérés de chaque ingrédient, ramenés à 100g de produit fini)

    **Public** — aucune authentification requise.

    Exemples :
    - `GET /nutrition/ingredient/milk_plant_oat` → industriel (défaut)
    - `GET /nutrition/ingredient/milk_plant_oat?source=recipe` → recette maison
    - `GET /nutrition/ingredient/milk_plant_oat?source=recipe&variant=oat` → variante oat

    Réponse :
    ```json
    {
      "ingredient_id": "milk_plant_oat",
      "name_fr": "lait d'avoine",
      "source_mode": "dual",
      "source_used": "recipe",
      "base_recipe_id": "base_oat_milk_3519f4",
      "variant": "default",
      "nutrition_per_100g": {
        "calories_kcal": 48.7,
        "protein_g": 1.2,
        ...
      }
    }
    ```
    """
    if source not in ("industrial", "recipe"):
        raise HTTPException(
            status_code=422,
            detail=f"Source invalide : '{source}'. Valeurs acceptées : 'industrial', 'recipe'."
        )

    from backend.core.data_io import load_ingredients_dict, resolve_ingredient_nutrition

    ings = load_ingredients_dict()
    if ingredient_id not in ings:
        raise HTTPException(status_code=404, detail=f"Ingrédient inconnu : {ingredient_id}")

    ing  = ings[ingredient_id]
    mode = ing.get("nutrition_source_mode", "industrial")

    # Résoudre la nutrition (gestion dual + fallback automatique)
    nutr = resolve_ingredient_nutrition(
        ingredient_id=ingredient_id,
        variant=variant,
        source_pref=source,
    )

    # Extraire les métadonnées internes avant de retourner
    source_used = nutr.pop("_source", source)
    recipe_id   = nutr.pop("_recipe_id", None)
    nutr.pop("_yield_g", None)
    missing     = nutr.pop("_missing", False)

    if missing:
        raise HTTPException(
            status_code=404,
            detail=f"Données nutritionnelles introuvables pour '{ingredient_id}' (variant={variant})."
        )

    # Score AJR optionnel sur les données résolues
    try:
        ajr_score = round(compute_ajr_score(nutr), 2)
    except Exception:
        ajr_score = None

    return {
        "ingredient_id":     ingredient_id,
        "name_fr":           ing.get("canonical_name_fr", ingredient_id),
        "category":          ing.get("category"),
        "source_mode":       mode,
        "source_used":       source_used,
        "base_recipe_id":    recipe_id,
        "variant":           variant,
        "nutrition_per_100g": nutr,
        "ajr_score":         ajr_score,
    }


@router.post("/ingredient/batch")
def get_ingredients_nutrition_batch(
    ingredient_ids: list[str],
    source: str = Query(default="industrial",
                        description="Source appliquée à tous les ingrédients dual"),
    user: dict | None = Depends(get_optional_user),
):
    """
    Nutrition pour une liste d'ingrédients en un seul appel.

    Utile pour calculer la nutrition d'une recette côté client, ou afficher
    un tableau comparatif. Max 50 ingrédients par requête.

    Chaque ingrédient dual utilise la `source` demandée si disponible.
    """
    if len(ingredient_ids) > 50:
        raise HTTPException(
            status_code=422,
            detail="Maximum 50 ingrédients par requête batch."
        )
    if source not in ("industrial", "recipe"):
        raise HTTPException(
            status_code=422,
            detail=f"Source invalide : '{source}'."
        )

    from backend.core.data_io import load_ingredients_dict, resolve_ingredient_nutrition

    ings = load_ingredients_dict()
    results = {}

    for iid in ingredient_ids:
        if iid not in ings:
            results[iid] = {"error": "introuvable"}
            continue

        nutr = resolve_ingredient_nutrition(iid, source_pref=source)
        source_used = nutr.pop("_source", source)
        nutr.pop("_recipe_id", None)
        nutr.pop("_yield_g", None)
        nutr.pop("_missing", None)

        results[iid] = {
            "name_fr":    ings[iid].get("canonical_name_fr", iid),
            "source_used": source_used,
            "nutrition_per_100g": nutr,
        }

    return {
        "source_requested": source,
        "count": len(ingredient_ids),
        "results": results,
    }