"""
recommendation_service.py — Service de recommandation simplifié.

Utilisé pour les cas où le pipeline complet (reco_engine) n'est pas nécessaire :
recherche textuelle basique + scoring santé rapide, sans profil ni learning.

Pour le pipeline complet avec profil utilisateur, utiliser reco_service.recommend().

CORRECTIONS vs version précédente :
    - health_score_engine supprimé (archivé) → score_engine.health.health_score
    - _final_score aligné sur la formule CDC_03c (W_QUALITY / W_RELEVANCE)
"""
import logging

from backend.db.data_access import get_data
from backend.core.validators import is_valid_recipe, safe_float
from backend.engine.score_engine.health import health_score   # corrigé
from backend.engine.config import W_QUALITY, W_RELEVANCE

logger = logging.getLogger(__name__)


def recommend_recipes(payload: dict) -> dict:
    """
    Pipeline de recommandation léger (sans profil ni learning).

    Args:
        payload : {
            "query" : str,
            "diet"  : str | None,
            "limit" : int (défaut 20),
        }

    Returns:
        {"recettes": list[dict], "meta": dict}
    """
    query = payload.get("query", "")
    diet  = payload.get("diet")
    limit = int(payload.get("limit", 20))

    # 1. Récupération recettes
    all_recipes = get_data.recipes.list_all()
    raw = get_data.recipes.search_by_text(query, all_recipes) if query else all_recipes[: limit * 3]

    # 2. Filtre régime
    if diet:
        raw = get_data.recipes.filter_by_diet(raw, diet)

    # 3. Enrichissement + scoring léger
    scored = []
    for recipe in raw:
        if not is_valid_recipe(recipe):
            continue
        try:
            nutr       = get_data.recipes.get_nutrition(recipe["id"])
            # health_score attend des totaux de plan, on l'appelle avec n_meals=1
            # pour obtenir un score proportionnel à une portion
            health_data = health_score(nutr, n_meals=1)
            health_sc   = health_data["health_score"]
            match_sc    = safe_float(recipe.get("_match_score", 1.0))

            enriched = dict(recipe)
            enriched["_health_score"] = health_sc
            enriched["_match_score"]  = match_sc
            # Formule alignée CDC_03c (W_QUALITY=0.65, W_RELEVANCE=0.35)
            enriched["_final_score"]  = round(
                match_sc * W_RELEVANCE + health_sc * W_QUALITY, 2
            )
            scored.append(enriched)
        except Exception as e:
            logger.debug("Enrichissement échoué pour %s : %s", recipe.get("id"), e)

    # 4. Tri
    scored.sort(key=lambda x: x.get("_final_score", 0), reverse=True)

    return {
        "recettes": scored[:limit],
        "meta": {
            "engine": "recommendation_service_light",
            "total":  len(scored),
            "query":  query,
            "diet":   diet,
        },
    }
