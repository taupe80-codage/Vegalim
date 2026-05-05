"""
validators.py — Validation des données du projet.

Fonctions de validation utilisables partout pour garantir
que les données sont bien formées avant traitement.

Régimes alimentaires :
    DIET_ALIASES   — source de vérité unique : clé canonique → aliases acceptés
    DIET_CANONICAL — map inverse : alias → clé canonique (pour normalisation)
    ALLOWED_DIETS  — ensemble plat de toutes les valeurs acceptées (validation API)

    Le projet est 100 % végétarien. Tout régime implique a minima l'absence
    d'ingrédients carnés. Les régimes religieux (halal, kosher) ne font pas
    partie de la taxonomie du projet.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


# ── Taxonomie des régimes ──────────────────────────────────────────────────────
#
# Structure : clé canonique → frozenset d'alias acceptés en entrée (API, profil).
# Règles :
#   • Chaque alias n'appartient qu'à un seul groupe (pas de doublon).
#   • La clé canonique est toujours incluse dans ses propres aliases.
#   • filter_service.py consomme DIET_CANONICAL pour normaliser avant filtrage.
#   • Ajouter un régime = une seule entrée ici, nulle part ailleurs.
#
# Résolution des flags :
#   vegan          → diet_flags["vegan"]
#   vegetarien     → diet_flags["vegetarian"]
#   gluten_free    → diet_flags["gluten_free"]
#   lactose_free   → diet_flags["lactose_free"]
#   nut_free       → diet_flags["nut_free"]
#   raw            → diet_flags["raw"]
#   kid_friendly   → diet_flags["kid_friendly"]
#   diabete        → health_scores["glycemic_category"] == "low"
#   hyperproteine  → health_scores["high_protein"] == True

DIET_ALIASES: dict[str, frozenset[str]] = {

    # ── Vegan ──────────────────────────────────────────────────────────────────
    "vegan": frozenset({
        "vegan",
    }),

    # ── Végétarien ─────────────────────────────────────────────────────────────
    # Baseline minimum du projet — tous les autres régimes l'impliquent.
    "vegetarien": frozenset({
        "vegetarien",       # FR canonique
        "vegetarian",       # EN (API externe, import)
        "vegetarienne",     # FR féminin (formulaires utilisateurs)
    }),

    # ── Sans gluten ────────────────────────────────────────────────────────────
    "gluten_free": frozenset({
        "gluten_free",      # EN canonique (clé diet_flags)
        "sans_gluten",      # FR courant
    }),

    # ── Sans lactose ───────────────────────────────────────────────────────────
    "lactose_free": frozenset({
        "lactose_free",     # EN canonique (clé diet_flags)
        "sans_lactose",     # FR courant
        "dairy_free",       # EN alternatif (formulaires EN)
        "sans_lait",        # FR simplifié
    }),

    # ── Sans fruits à coque ────────────────────────────────────────────────────
    "nut_free": frozenset({
        "nut_free",             # EN canonique (clé diet_flags)
        "sans_fruits_a_coque",  # FR officiel (étiquetage allergènes)
        "sans_noix",            # FR simplifié
    }),

    # ── Cru ────────────────────────────────────────────────────────────────────
    "raw": frozenset({
        "raw",              # EN canonique (clé diet_flags)
        "cru",              # FR courant
    }),

    # ── Adapté aux enfants ─────────────────────────────────────────────────────
    "kid_friendly": frozenset({
        "kid_friendly",     # EN canonique (clé diet_flags)
    }),

    # ── Diabète ────────────────────────────────────────────────────────────────
    # Résolu via health_scores["glycemic_category"] == "low".
    "diabete": frozenset({
        "diabete",
    }),

    # ── Hyperprotéiné ──────────────────────────────────────────────────────────
    # Résolu via health_scores["high_protein"] == True.
    "hyperproteine": frozenset({
        "hyperproteine",
    }),
}

# Map inverse : alias (tel que reçu) → clé canonique.
# Généré automatiquement — ne pas éditer manuellement.
DIET_CANONICAL: dict[str, str] = {
    alias: canonical
    for canonical, aliases in DIET_ALIASES.items()
    for alias in aliases
}

# Ensemble plat de toutes les valeurs acceptées en entrée (validation API / profil).
ALLOWED_DIETS: frozenset[str] = frozenset(DIET_CANONICAL.keys())


# ── Champs requis par type de données ─────────────────────────────────────────

RECIPE_REQUIRED_FIELDS = {"ingredients", "nutrition"}
RECIPE_OPTIONAL_FIELDS = {"id", "title_fr", "title_original", "tags", "diet_flags",
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

def is_valid_diet(diet: Any) -> bool:
    """
    Vérifie qu'un régime est connu (alias inclus).
    None est valide — signifie "pas de filtre".
    """
    if diet is None:
        return True
    if not isinstance(diet, str):
        logger.warning("Régime invalide (pas une chaîne) : %s", diet)
        return False
    if diet.lower() not in ALLOWED_DIETS:
        logger.warning(
            "Régime inconnu : '%s'. Valides : %s",
            diet, sorted(ALLOWED_DIETS),
        )
        return False
    return True


def normalize_diet(diet: str | None) -> str | None:
    """
    Normalise un alias de régime vers sa clé canonique.

    Exemple : "sans_gluten" → "gluten_free", "vegetarienne" → "vegetarien"

    Returns:
        Clé canonique, ou None si diet est None / vide.
        Retourne la valeur lowercased originale si l'alias est inconnu,
        pour ne pas bloquer silencieusement.
    """
    if not diet:
        return None
    normalized = diet.strip().lower().replace("-", "_").replace(" ", "_")
    return DIET_CANONICAL.get(normalized, normalized)


# ── Nutrition ─────────────────────────────────────────────────────────────────

def is_valid_nutrition(nutrition: Any) -> bool:
    """Vérifie qu'un dict de nutrition est utilisable."""
    if not isinstance(nutrition, dict):
        return False
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
    "<script", "</script", "javascript:", "vbscript:",
    "{{", "}}", "${", "#{",
    "DROP TABLE", "SELECT *", "INSERT INTO", "DELETE FROM",
    "UNION SELECT", "--", "/*", "*/",
    "eval(", "exec(", "__import__", "os.system",
]


def sanitize_text(text: str, max_length: int = 500,
                  allow_empty: bool = True) -> str:
    """
    Nettoie un champ texte libre pour prévenir les injections.

    - Strip les espaces en début/fin
    - Rejette les patterns XSS / SQL / template injection
    - Tronque à max_length si dépassé
    - Rejette les caractères de contrôle dangereux

    Raises:
        ValueError : si le texte contient des patterns dangereux
    """
    if not text:
        return "" if allow_empty else text

    cleaned = text.strip()

    upper = cleaned.upper()
    for pattern in _INJECTION_PATTERNS:
        if pattern.upper() in upper:
            raise ValueError(
                f"Contenu invalide détecté dans le texte (pattern: {pattern!r})"
            )

    if any(ord(c) < 32 and c not in ("\n", "\t", "\r") for c in cleaned):
        raise ValueError("Caractères de contrôle interdits dans le texte")

    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length]

    return cleaned