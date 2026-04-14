"""
routes/frigo.py — Mon frigo : suggestions basées sur les ingrédients disponibles.

Routes authentifiées :
  POST /frigo/suggestions  — recettes réalisables avec les ingrédients fournis
  POST /frigo/manquants    — ingrédients manquants pour une recette cible
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional

from backend.core.auth_deps import get_user, get_optional_user
from backend.core.rate_limiter import check_rate_limit
from backend.core.data_io import load_recipes, load_ingredients_dict

router = APIRouter(prefix="/frigo", tags=["Mon frigo"])


class FridgeRequest(BaseModel):
    ingredients: list[str] = Field(..., min_length=1,
                                   description="Liste des ingredient_id disponibles dans le frigo")
    diet:        Optional[str]  = None
    max_missing: int            = Field(default=2, ge=0, le=5,
                                        description="Nombre max d'ingrédients manquants tolérés")
    limit:       int            = Field(default=10, ge=1, le=50)


class MissingRequest(BaseModel):
    fridge:    list[str] = Field(..., description="Ingrédients disponibles")
    recipe_id: int       = Field(..., description="Recette cible")


def _get_recipe_ingredients(recipe: dict) -> set[str]:
    """Extrait les identifiants d'ingrédients d'une recette.
    
    Supporte les deux schemas :
     - CDC v4 : composition[].ingredient  (snake_case EN)
     - legacy  : ingredients[].ingredient_id
    """
    ids = set()
    # CDC v4 utilise 'composition', legacy utilise 'ingredients'
    items = recipe.get("composition") or recipe.get("ingredients", [])
    for ing in items:
        if isinstance(ing, dict):
            # CDC v4 : champ 'ingredient' (ex: 'eggplant')
            # legacy  : champ 'ingredient_id'
            iid = ing.get("ingredient") or ing.get("ingredient_id", "")
        else:
            iid = str(ing)
        if iid:
            ids.add(str(iid).lower())
    return ids


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/suggestions")
def fridge_suggestions(payload: FridgeRequest, request: Request = None, user: dict | None = Depends(get_optional_user)):
    """
    Retourne les recettes réalisables avec les ingrédients du frigo.
    **Public** — fonctionnel sans compte (CDC_11 plan gratuit).

    Tri par complétude décroissante (moins d'ingrédients manquants = prioritaire),
    puis par iconic_score.
    """
    fridge = {ing.lower() for ing in payload.ingredients}
    recipes = load_recipes()

    if payload.diet:
        from backend.services.filter_service import apply_diet_filter
        recipes = apply_diet_filter(recipes, payload.diet)

    scored = []
    for recipe in recipes:
        needed    = _get_recipe_ingredients(recipe)
        if not needed:
            continue
        have      = fridge & needed
        missing   = needed - fridge
        n_missing = len(missing)

        if n_missing > payload.max_missing:
            continue

        completeness = round(len(have) / len(needed), 2)
        scored.append({
            "id":           recipe["id"],
            "title_fr":     recipe.get("titles", {}).get("fr", ""),
            "iconic_score": recipe.get("scoring", {}).get("iconic", {}).get("score", 0),
            "diet_flags":   recipe.get("diet_flags", {}),
            "technique":    recipe.get("technique", []),
            "total_time_min": recipe.get("timing", {}).get("total_min"),
            "completeness":   completeness,
            "have":         sorted(have),
            "missing":      sorted(missing),
            "n_missing":    n_missing,
        })

    # Tri : d'abord moins de manquants, ensuite iconic_score
    scored.sort(key=lambda x: (x["n_missing"], -x["iconic_score"]))

    return {
        "fridge_ingredients": sorted(fridge),
        "total":  len(scored),
        "limit":  payload.limit,
        "results": scored[: payload.limit],
    }


@router.post("/manquants")
def missing_ingredients(payload: MissingRequest, user: dict = Depends(get_user)):
    """
    Retourne les ingrédients manquants pour réaliser une recette cible
    avec les ingrédients actuels du frigo.
    """
    recipes = load_recipes()
    recipe  = next((r for r in recipes if r["id"] == payload.recipe_id), None)
    if not recipe:
        raise HTTPException(status_code=404,
                            detail=f"Recette {payload.recipe_id} introuvable")

    fridge  = {ing.lower() for ing in payload.fridge}
    needed  = _get_recipe_ingredients(recipe)
    missing = needed - fridge
    have    = fridge & needed

    # Enrichir les ingrédients manquants avec leur nom FR
    ings_dict = load_ingredients_dict()
    missing_enriched = []
    for iid in sorted(missing):
        d = ings_dict.get(iid, {})
        missing_enriched.append({
            "id":      iid,
            "name_fr": d.get("name_fr", iid),
            "category": d.get("category", ""),
            "available_in_france": True,  # optimiste par défaut
        })

    return {
        "recipe_id":    payload.recipe_id,
        "recipe_title": recipe.get("titles", {}).get("fr", ""),
        "fridge_count": len(fridge),
        "needed_count": len(needed),
        "have_count":   len(have),
        "missing_count": len(missing),
        "completeness": round(len(have) / len(needed), 2) if needed else 1.0,
        "have":    sorted(have),
        "missing": missing_enriched,
    }
