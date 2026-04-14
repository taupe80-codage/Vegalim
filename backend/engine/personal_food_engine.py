"""
personal_food_engine.py — Ajustement des scores selon les préférences explicites.

Façade légère sur learning_engine pour les préférences déclarées
(liked_ingredients / disliked_ingredients) vs les préférences implicites
calculées par learning_engine depuis l'historique.

API publique :
    adjust_recipe_scores(recipes, user_profile) → list[dict]
"""
import logging
logger = logging.getLogger(__name__)

_LIKED_BONUS   =  0.5   # boost si ingrédient aimé présent
_DISLIKED_MALUS = -0.8  # malus si ingrédient non-aimé présent
_MAX_ADJUST    =  2.0   # ajustement max absolu


def adjust_recipe_scores(recipes: list[dict], user_profile: dict) -> list[dict]:
    """
    Ajuste le score de chaque recette selon les préférences explicites.

    Args:
        recipes      : liste de recettes (avec ou sans final_score)
        user_profile : {"liked_ingredients": [...], "disliked_ingredients": [...]}

    Returns:
        Liste de recettes avec _personal_adjustment et final_score mis à jour.
    """
    if not recipes:
        return []

    liked    = set(user_profile.get("liked_ingredients",    []))
    disliked = set(user_profile.get("disliked_ingredients", []))

    if not liked and not disliked:
        return recipes

    result = []
    for recipe in recipes:
        r = dict(recipe)
        ings = {
            (i.get("ingredient_id","") if isinstance(i,dict) else str(i)).lower()
            for i in r.get("ingredients", [])
        } - {""}

        bonus  = len(ings & liked)    * _LIKED_BONUS
        malus  = len(ings & disliked) * _DISLIKED_MALUS
        adjust = max(-_MAX_ADJUST, min(_MAX_ADJUST, bonus + malus))

        base = float(r.get("final_score", r.get("score", 5.0)))
        r["final_score"]          = round(max(0.0, min(10.0, base + adjust)), 2)
        r["_personal_adjustment"] = round(adjust, 3)
        result.append(r)

    result.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return result
