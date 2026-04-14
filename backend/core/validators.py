"""
validators.py — Validation des données du projet.

Fonctions de validation utilisables partout pour garantir
que les données sont bien formées avant traitement.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Champs requis par type de données ─────────────────────────────────────────

RECIPE_REQUIRED_FIELDS  = {"ingredients", "nutrition"}
RECIPE_OPTIONAL_FIELDS  = {"id", "title_fr", "title_original", "tags", "diet_flags",
                            "servings", "technique", "iconic_score", "composition",
                            "prep_time_min", "cook_time_min", "difficulty",
                            "recipe_origin", "instructions"}

INGREDIENT_REQUIRED_FIELDS = {"id"}
NUTRITION_REQUIRED_FIELDS  = {"calories"}


# ── Recettes ──────────────────────────────────────────────────────────────────

def is_valid_recipe(recipe: Any, strict: bool = False) -> bool:
    """
    Valide qu'une recette est utilisable.

    Args:
        recipe : objet à valider
        strict : si True, vérifie aussi que les ingrédients et la nutrition
                 ont du contenu réel (pas des listes/dicts vides)

    Returns:
        True si valide, False sinon (avec log warning).
    """
    if not isinstance(recipe, dict):
        logger.warning("Recette invalide : pas un dict (%s)", type(recipe).__name__)
        return False

    missing = RECIPE_REQUIRED_FIELDS - set(recipe.keys())
    if missing:
        title = recipe.get("titles", {}).get("fr") or recipe.get("title_original", "?")
        logger.warning("Recette '%s' — champs manquants : %s", title, missing)
        return False

    if strict:
        if not recipe.get("ingredients"):
            logger.warning("Recette '%s' — liste d'ingrédients vide", recipe.get("title_fr", "?"))
            return False
        if not isinstance(recipe.get("nutrition"), dict):
            logger.warning("Recette '%s' — nutrition invalide", recipe.get("title_fr", "?"))
            return False

    return True


def validate_recipes(recipes: list, strict: bool = False) -> list[dict]:
    """
    Filtre une liste de recettes — ne garde que les valides.
    Log un résumé en fin de traitement.
    """
    valid   = [r for r in recipes if is_valid_recipe(r, strict=strict)]
    invalid = len(recipes) - len(valid)
    if invalid:
        logger.warning("Validation recettes : %d/%d valides (%d écartées)",
                       len(valid), len(recipes), invalid)
    else:
        logger.debug("Validation recettes : %d/%d OK", len(valid), len(recipes))
    return valid


# ── Profils ───────────────────────────────────────────────────────────────────

ALLOWED_DIETS = frozenset(("vegetarien", "vegan", "diabete", "hyperproteine", "gluten_free", "raw", "kid_friendly", "sans_gluten", "enfants", "famille"))

def is_valid_diet(diet: Any) -> bool:
    """Vérifie qu'un régime est connu."""
    if diet is None:
        return True  # None = pas de filtre, toujours valide
    if not isinstance(diet, str):
        logger.warning("Régime invalide (pas une chaîne) : %s", diet)
        return False
    if diet.lower() not in ALLOWED_DIETS:
        logger.warning("Régime inconnu : '%s'. Valides : %s", diet, sorted(ALLOWED_DIETS))
        return False
    return True


# ── Nutrition ─────────────────────────────────────────────────────────────────

def is_valid_nutrition(nutrition: Any) -> bool:
    """Vérifie qu'un dict de nutrition est utilisable."""
    if not isinstance(nutrition, dict):
        return False
    # Au moins un macronutriment présent
    return any(nutrition.get(k) is not None
               for k in ("calories", "protein", "carbs", "fat"))


def safe_float(value: Any, default: float = 0.0) -> float:
    """Conversion sécurisée vers float — retourne default si invalide."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# ── Sanitisation texte — anti-injection (XSS, template, SQL) ─────────────────

_INJECTION_PATTERNS = [
    "<script", "</script", "javascript:", "vbscript:",   # XSS
    "{{", "}}", "${", "#{",                               # template injection
    "DROP TABLE", "SELECT *", "INSERT INTO", "DELETE FROM",  # SQL
    "UNION SELECT", "--", "/*", "*/",                    # SQL comments
    "eval(", "exec(", "__import__", "os.system",         # code injection
]


def sanitize_text(text: str, max_length: int = 500,
                  allow_empty: bool = True) -> str:
    """
    Nettoie un champ texte libre pour prévenir les injections.

    - Strip les espaces en début/fin
    - Rejette les patterns XSS / SQL / template injection
    - Tronque à max_length si dépassé
    - Rejette les caractères de contrôle dangereux

    Args:
        text       : texte à valider
        max_length : longueur maximale acceptée (défaut 500)
        allow_empty: si True, retourne "" pour texte vide

    Returns:
        Texte nettoyé

    Raises:
        ValueError : si le texte contient des patterns dangereux
    """
    if not text:
        return "" if allow_empty else text

    cleaned = text.strip()

    # Vérifier les patterns dangereux (insensible à la casse)
    upper = cleaned.upper()
    for pattern in _INJECTION_PATTERNS:
        if pattern.upper() in upper:
            raise ValueError(
                f"Contenu invalide détecté dans le texte (pattern: {pattern!r})"
            )

    # Rejeter caractères de contrôle (sauf newline/tab légitimes)
    if any(ord(c) < 32 and c not in ("\n", "\t", "\r") for c in cleaned):
        raise ValueError("Caractères de contrôle interdits dans le texte")

    # Tronquer si nécessaire
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned
