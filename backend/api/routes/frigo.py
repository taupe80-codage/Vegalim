"""
routes/frigo.py â€” Mon frigo : suggestions basÃ©es sur les ingrÃ©dients disponibles.

Routes authentifiÃ©es :
  POST /frigo/suggestions  â€” recettes rÃ©alisables avec les ingrÃ©dients fournis
  POST /frigo/manquants    â€” ingrÃ©dients manquants pour une recette cible
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional

from backend.core.auth_deps import get_user, get_optional_user
from backend.core.data_io import load_recipes, load_ingredients_dict

router = APIRouter(prefix="/frigo", tags=["Mon frigo"])


class FridgeRequest(BaseModel):
    ingredients:  list[str]      = Field(..., min_length=1,
                                         description="Liste des ingredient_id disponibles dans le frigo")
    diet:         Optional[str]  = None
    dish_types:   list[str]      = Field(default=[],
                                         description="Filtre type de plat (main, dessert, soupâ€¦). Vide = tous.")
    max_missing:  int            = Field(default=2, ge=0, le=5,
                                         description="Nombre max d'ingrÃ©dients manquants tolÃ©rÃ©s")
    limit:        int            = Field(default=10, ge=1, le=50)


class MissingRequest(BaseModel):
    fridge:    list[str] = Field(..., description="IngrÃ©dients disponibles")
    recipe_id: str       = Field(..., description="ID de la recette cible (ex: dip_baba_ghanoush_dbd030)")


def _get_recipe_ingredients(recipe: dict) -> set[str]:
    """Extrait les identifiants d'ingrÃ©dients d'une recette.

    Supporte les deux schemas :
     - CDC v4 : composition[].ingredient  (snake_case EN)
     - legacy  : ingredients[].ingredient_id
    """
    ids = set()
    items = recipe.get("composition") or recipe.get("ingredients", [])
    for ing in items:
        if isinstance(ing, dict):
            iid = ing.get("ingredient") or ing.get("ingredient_id", "")
        else:
            iid = str(ing)
        if iid:
            ids.add(str(iid).lower())
    return ids


def _ingredient_matches(fridge_id: str, recipe_id: str) -> bool:
    """
    Matching hiÃ©rarchique entre un ingrÃ©dient du frigo et un ingrÃ©dient de recette.

    Les donnÃ©es utilisent un systÃ¨me famille/variÃ©tÃ© (ex: 'tomato/fresh',
    'butter/dairy', 'citrus/lemon', 'milk_animal/whole') mais l'UI envoie
    des IDs simplifiÃ©s ('tomato', 'butter', 'lemon', 'milk').

    RÃ¨gles (dans l'ordre) :
      1. Ã‰galitÃ© exacte                      : 'garlic'    == 'garlic'
      2. Prefix + '/'                        : 'tomato'    â†’ 'tomato/fresh'
      3. Prefix + '_'                        : 'tomato'    â†’ 'tomato_paste'
      4. Suffix  '_' + fridge_id             : 'lentils'   â†’ 'green_lentils'
      5. DerniÃ¨re partie aprÃ¨s '/' (famille) : 'lemon'     â†’ 'citrus/lemon'
         ou prefix de cette partie           : 'lemon'     â†’ 'citrus/lemon_juice'
    """
    if fridge_id == recipe_id:
        return True
    # RÃ¨gles 2-3 : frigo est un prÃ©fixe de la recette
    if recipe_id.startswith(fridge_id + "/") or recipe_id.startswith(fridge_id + "_"):
        return True
    # RÃ¨gle 4 : frigo est un suffixe (mot complet aprÃ¨s _)
    if recipe_id.endswith("_" + fridge_id):
        return True
    # RÃ¨gle 5 : famille/variÃ©tÃ© â†’ regarder la derniÃ¨re partie aprÃ¨s '/'
    parts = recipe_id.split("/")
    if len(parts) > 1:
        last = parts[-1]
        if last == fridge_id or last.startswith(fridge_id + "_"):
            return True
    return False


def _fridge_coverage(fridge: set[str], needed: set[str]) -> tuple[set[str], set[str]]:
    """
    Calcule (have, missing) en tenant compte du matching hiÃ©rarchique.

    Pour chaque ingrÃ©dient de la recette, cherche s'il est couvert par
    au moins un ingrÃ©dient du frigo via _ingredient_matches().
    """
    have    = set()
    missing = set()
    for recipe_ing in needed:
        matched = any(_ingredient_matches(fridge_ing, recipe_ing) for fridge_ing in fridge)
        if matched:
            have.add(recipe_ing)
        else:
            missing.add(recipe_ing)
    return have, missing


# â”€â”€ Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/suggestions")
def fridge_suggestions(payload: FridgeRequest, user: dict | None = Depends(get_optional_user)):
    """
    Retourne les recettes rÃ©alisables avec les ingrÃ©dients du frigo.
    **Public** â€” fonctionnel sans compte (CDC_11 plan gratuit).

    Tri par complÃ©tude dÃ©croissante (moins d'ingrÃ©dients manquants = prioritaire),
    puis par iconic_score.
    """
    fridge = {ing.lower() for ing in payload.ingredients}
    recipes    = load_recipes()
    ings_dict  = load_ingredients_dict()   # pour traduire les IDs manquants en noms FR

    if payload.diet:
        from backend.services.filter_service import apply_diet_filter
        recipes = apply_diet_filter(recipes, payload.diet)

    if payload.dish_types:
        allowed = {dt.lower() for dt in payload.dish_types}
        recipes = [r for r in recipes if r.get("dish_type", "").lower() in allowed]

    def _label(iid: str) -> str:
        """
        Retourne le nom FR d'un ingredient_id.
        Fallback : reconstruit un libellÃ© lisible depuis l'ID hiÃ©rarchique.
        Ex: 'butter/dairy' â†’ 'beurre' (via base 'butter'), 'sugar/white' â†’ 'sucre blanc'
        """
        # 1. Correspondance exacte dans le dictionnaire
        d = ings_dict.get(iid, {})
        if d.get("name_fr"):
            return d["name_fr"]
        # 2. Correspondance sur la partie avant '/' (ex: 'butter' pour 'butter/dairy')
        base = iid.split("/")[0]
        d_base = ings_dict.get(base, {})
        if d_base.get("name_fr"):
            variant = iid.split("/")[-1].replace("_", " ")
            return f"{d_base['name_fr']} ({variant})" if variant != base else d_base["name_fr"]
        # 3. Fallback : humanise l'ID complet
        return iid.replace("_", " ").replace("/", " ")

    scored = []
    for recipe in recipes:
        needed    = _get_recipe_ingredients(recipe)
        if not needed:
            continue
        have, missing = _fridge_coverage(fridge, needed)
        n_missing = len(missing)

        if n_missing > payload.max_missing:
            continue

        completeness = round(len(have) / len(needed), 2)

        # Exclure les recettes oÃ¹ aucun ingrÃ©dient du frigo ne correspond :
        # avoir 0 ingrÃ©dient sur 2 avec max_missing=2 ne constitue pas une
        # suggestion utile â€” l'utilisateur n'a RIEN de ce qu'il faut.
        if completeness == 0.0:
            continue
        iconic_score = recipe.get("scoring", {}).get("iconic", {}).get("score", 0)
        scored.append({
            # â”€â”€ Identification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            "id":             recipe["id"],
            "title_fr":       recipe.get("titles", {}).get("fr", ""),
            "titles":         recipe.get("titles", {}),

            # â”€â”€ Champs pour RecipeCard â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            "origin":         recipe.get("origin", {}),
            "difficulty":     recipe.get("difficulty_level"),   # clÃ© rÃ©elle dans les donnÃ©es
            "servings":       recipe.get("servings", 4),
            "nutrition":      recipe.get("nutrition", {}),
            "health_scores":  recipe.get("health_scores", {}),
            "tags":           recipe.get("tags", {}),
            "image_url":      recipe.get("image_url"),
            "diet_flags_enriched": recipe.get("diet_flags_enriched", {}),
            "nutrition_highlights": recipe.get("nutrition_highlights", {}),

            # â”€â”€ Filtres / tri â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            "dish_type":      recipe.get("dish_type", ""),
            "iconic_score":   iconic_score,
            "final_score":    iconic_score,   # alias attendu par RecipeCard
            "diet_flags":     recipe.get("diet_flags", {}),
            "technique":      recipe.get("technique", []),
            "total_time_min": recipe.get("timing", {}).get("total_min"),

            # â”€â”€ Frigo spÃ©cifique â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
            "completeness":   completeness,
            "have":           sorted(have),
            "missing": [
                {"id": iid, "name_fr": _label(iid)}
                for iid in sorted(missing)
            ],
            "n_missing":      n_missing,
        })

    # Tri : complÃ©tude dÃ©croissante (100% en tÃªte), puis iconic_score en Ã©galitÃ©
    scored.sort(key=lambda x: (-x["completeness"], -x["iconic_score"]))

    return {
        "fridge_ingredients": sorted(fridge),
        "total":  len(scored),
        "limit":  payload.limit,
        "results": scored[: payload.limit],
    }


@router.post("/manquants")
def missing_ingredients(payload: MissingRequest, user: dict = Depends(get_user)):
    """
    Retourne les ingrÃ©dients manquants pour rÃ©aliser une recette cible
    avec les ingrÃ©dients actuels du frigo.
    """
    recipes = load_recipes()
    recipe  = next((r for r in recipes if r["id"] == payload.recipe_id), None)
    if not recipe:
        raise HTTPException(status_code=404,
                            detail=f"Recette {payload.recipe_id} introuvable")

    fridge         = {ing.lower() for ing in payload.fridge}
    needed         = _get_recipe_ingredients(recipe)
    have, missing  = _fridge_coverage(fridge, needed)

    # Enrichir les ingrÃ©dients manquants avec leur nom FR
    ings_dict = load_ingredients_dict()
    missing_enriched = []
    for iid in sorted(missing):
        d = ings_dict.get(iid, {})
        missing_enriched.append({
            "id":      iid,
            "name_fr": d.get("name_fr", iid),
            "category": d.get("category", ""),
            "available_in_france": True,  # optimiste par dÃ©faut
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
