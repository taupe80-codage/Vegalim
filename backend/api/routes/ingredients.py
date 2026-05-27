"""
routes/ingredients.py — Dictionnaire des ingrédients.

Routes publiques :
  GET /ingredients            — liste paginée avec filtres
  GET /ingredients/{id}       — fiche ingrédient complète

Routes authentifiées :
  GET /ingredients/search     — recherche par token
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import Optional

from backend.core.auth_deps   import get_user, get_optional_user
from backend.core.rate_limiter import check_rate_limit
from backend.core.data_io     import (
    load_ingredients_dict, load_availability_graph,
    load_nutrition_db, load_recipes,
)

router = APIRouter(prefix="/ingredients", tags=["Ingrédients"])


def _enrich_ingredient(iid: str, ing: dict) -> dict:
    """Enrichit un ingrédient avec disponibilité, nutrition et recettes associées."""
    av   = load_availability_graph()
    nutr = load_nutrition_db()

    entry = dict(ing)
    entry["id"] = iid

    # Disponibilité France
    av_data = av.get(iid, {})
    entry["available_in_france"] = av_data.get("available_in_france", True)

    # Données nutritionnelles (via nutrition_key)
    nkey = ing.get("nutrition_key", "")
    entry["nutrition"] = nutr.get(nkey, {}) if nkey else nutr.get(iid, {})

    return entry


# ── Routes publiques ──────────────────────────────────────────────────────────

@router.get("")
@router.get("/")
def list_ingredients(
    request:   Request,
    skip:      int           = Query(default=0,  ge=0),
    limit:     int           = Query(default=50, ge=1, le=302),
    category:  Optional[str] = Query(default=None,
                                     description="vegetable | grain_cereal | spice | dairy | …"),
    family:    Optional[str] = Query(default=None),
    vegan:     Optional[bool]= Query(default=None),
    available: Optional[bool]= Query(default=None,
                                     description="Filtrer par disponibilité en France"),
):
    """
    Liste paginée des 302 ingrédients du dictionnaire avec filtres.
    **Public — aucune authentification requise.**
    """
    check_rate_limit(request, limit=120, window_seconds=60)
    d    = load_ingredients_dict()
    av   = load_availability_graph()
    ings = list(d.items())  # [(id, dict), …]

    # Filtres
    if category:
        ings = [(k, v) for k, v in ings if v.get("category") == category]
    if family:
        ings = [(k, v) for k, v in ings if v.get("family") == family]
    if vegan is not None:
        ings = [(k, v) for k, v in ings
                if v.get("diet_profile", {}).get("vegan") == vegan]
    if available is not None:
        ings = [(k, v) for k, v in ings
                if (av.get(k, {}).get("available_in_france") is True) == available]

    total = len(ings)
    page  = ings[skip: skip + limit]

    results = []
    for iid, ing in page:
        entry = {"id": iid,
                 "name_fr":   ing.get("name_fr", iid),
                 "name_en":   ing.get("name_en", iid),
                 "category":  ing.get("category", ""),
                 "family":    ing.get("family", ""),
                 "diet_profile":        ing.get("diet_profile", {}),
                 "available_in_france": av.get(iid, {}).get("available_in_france", True),
                 "substitutions":       ing.get("substitutions", []),
                 "flavor_profile":      ing.get("flavor_profile", ""),
                 }
        results.append(entry)

    return {
        "total":   total,
        "skip":    skip,
        "limit":   limit,
        "filters": {"category": category, "family": family,
                    "vegan": vegan, "available": available},
        "results": results,
    }


@router.get("/frigo-groups")
def get_frigo_groups(request: Request):
    """
    Retourne les groupes d'ingrédients pour les chips expandables du frigo.
    Chaque groupe = catégorie (Féculents, Légumes…) avec items triés par popularité.
    Chaque item = base ingredient avec ses variantes hiérarchiques.
    **Public — aucune authentification requise.**
    """
    check_rate_limit(request, limit=120, window_seconds=60)
    from backend.services.ingredient_catalog import get_frigo_groups
    return {"groups": get_frigo_groups()}


@router.get("/search")
def search_ingredients(
    request: Request,
    q:       str           = Query(..., min_length=1, description="Début de nom (FR ou ID)"),
    limit:   int           = Query(default=20, ge=1, le=50),
    user:    dict | None   = Depends(get_optional_user),
):
    """
    Recherche d'ingrédients par préfixe ou token.
    Catalogue étendu : 510 IDs recettes + dict (avec name_fr auto-générés).
    Résultats triés par pertinence puis popularité (recipe_count).
    **Public** — CDC_11 plan gratuit.
    """
    check_rate_limit(request, limit=60, window_seconds=60)
    from backend.services.ingredient_catalog import search as catalog_search
    results = catalog_search(q, limit=limit)
    return {
        "query":   q,
        "total":   len(results),
        "results": [
            {
                "id":           r["id"],
                "name_fr":      r["name_fr"],
                "name_en":      r["name_en"],
                "category":     r["category"],
                "recipe_count": r["recipe_count"],
            }
            for r in results
        ],
    }


@router.get("/{ingredient_id}")
def get_ingredient(ingredient_id: str, request: Request):
    """
    Fiche complète d'un ingrédient : nutrition, disponibilité France,
    profil gustatif, substitutions, recettes associées.
    **Public — aucune authentification requise.**
    """
    check_rate_limit(request, limit=120, window_seconds=60)
    d   = load_ingredients_dict()
    ing = d.get(ingredient_id)
    if not ing:
        raise HTTPException(status_code=404,
                            detail=f"Ingrédient '{ingredient_id}' introuvable")

    entry = _enrich_ingredient(ingredient_id, ing)

    # Recettes associées (celles qui contiennent cet ingrédient)
    recipes = load_recipes()
    associated = []
    for r in recipes:
        for i in r.get("ingredients", []):
            iid = i.get("ingredient_id", "") if isinstance(i, dict) else str(i)
            if iid == ingredient_id:
                associated.append({
                    "id":       r["id"],
                    "title_fr": r.get("titles", {}).get("fr", ""),
                    "vegan":    r.get("diet_flags", {}).get("vegan"),
                    "iconic_score": r.get("scoring", {}).get("iconic", {}).get("score"),
                })
                break
    associated.sort(key=lambda x: x.get("iconic_score") or 0, reverse=True)
    entry["recipes_count"] = len(associated)
    entry["recipes"]       = associated[:10]  # Top 10

    return entry
