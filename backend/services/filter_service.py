"""
filter_service.py — Filtrage des recettes par régime.
Logging sur les régimes inconnus, validation des tags.
"""
import logging
from backend.core.validators import ALLOWED_DIETS
from backend.db.data_access import get_data

logger = logging.getLogger(__name__)


def match_diet(recipe: dict, diet: str) -> bool:
    """Vérifie si une recette correspond à un régime donné."""
    flags = recipe.get("diet_flags", {})

    if not diet:
        return True

    diet = diet.lower()

    if diet == "vegan":
        return flags.get("vegan", False)

    if diet == "vegan_flexible":
        return flags.get("vegan", False) or flags.get("vegetarian", False)

    if diet in ("vegetarien", "vegetarian"):
        return flags.get("vegetarian", False)

    if diet in ("gluten_free", "sans_gluten", "sans gluten"):
        return flags.get("gluten_free", False)

    if diet in ("raw", "cru", "crudivorisme"):
        return flags.get("raw", False)

    if diet in ("kid_friendly", "enfants", "famille"):
        return flags.get("kid_friendly", False)

    if diet not in ALLOWED_DIETS:
        logger.warning("Régime inconnu : '%s'. Valides : %s", diet, sorted(ALLOWED_DIETS))

    return True


def apply_diet_filter(recipes: list, diet: str) -> list:
    """
    Filtre une liste de recettes par régime alimentaire.
    Délègue au RecipeRepository (repository layer).
    """
    if not diet:
        return recipes
    filtered = get_data.recipes.filter_by_diet(recipes, diet)
    logger.debug("Filtrage %s : %d → %d recettes", diet, len(recipes), len(filtered))
    return filtered


# Alias de compatibilité
filter_recipes = apply_diet_filter
