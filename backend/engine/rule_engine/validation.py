"""
validation.py — Validation culinaire d'une recette.
Fusionne : culinary_rule_engine

API :
    validate_recipe(recipe) → dict  {score, violations, is_valid}
"""
from __future__ import annotations
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Mots reconnus dans les ids d'ingrédients (« red_lentil_dried » → lentil,
# « olive_oil_extra_virgin_plant » → oil) ou dans leur clé de prix.
_PLANT_PROTEINS = {
    "tofu", "tempeh", "seitan", "chickpea", "chickpeas", "lentil", "lentils",
    "bean", "beans", "soybean", "soy", "edamame", "pea", "peas", "fava",
    "broadbeans", "quinoa", "paneer", "egg", "eggs", "oeuf", "peanut",
    "walnut", "walnuts", "almond", "almonds", "cashew", "cashews", "dal",
    "halloumi", "cheese", "feta", "ricotta", "mozzarella", "parmesan", "yogurt",
    "hazelnut", "pistachio", "hemp", "chana", "urad", "mung",
}
_FATS = {
    "oil", "butter", "ghee", "cream", "creme", "beurre", "lait_coco", "coconut",
    "cheese", "feta", "parmesan", "tahini", "avocado", "margarine",
}
_AROMATICS_AND_SPICES = {
    "onion", "garlic", "ginger", "shallot", "oignon", "ail", "leeks", "leek",
    "cumin", "turmeric", "paprika", "coriander", "garam", "masala", "cinnamon",
    "curry", "chili", "chilli", "pepper", "basil", "parsley", "thyme",
    "oregano", "mint", "rosemary", "dill", "chives", "sage", "tarragon",
    "cardamom", "clove", "cloves", "nutmeg", "fennel", "lemon", "lime",
    "vanilla", "miso", "soy_sauce", "harissa", "sumac", "zaatar", "bay",
}
# Rôles de composition (meta.role) qui suffisent à cocher une catégorie
_ROLE_PROTEIN = {"plant_protein", "protein"}
_ROLE_FAT = {"fat", "fat_cooking"}
_ROLE_AROMATIC = {"aromatic", "aromatic_base", "spice", "herb", "seasoning", "aroma", "umami"}
# Types de plat salés où l'on attend une protéine (plats) ou un aromate
_NEEDS_PROTEIN = {"main"}
_NEEDS_AROMATIC = {"main", "side", "soup", "starter", "snack"}


@dataclass
class RuleViolation:
    rule:       str
    severity:   str   # "critical" | "warning" | "info"
    message:    str
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {"rule": self.rule, "severity": self.severity,
                "message": self.message, "suggestion": self.suggestion}


def _items(recipe: dict) -> list:
    """Lignes de composition (schéma actuel), sinon l'ancien champ ingredients.
    Lire seulement « ingredients » faisait voir 0 ingrédient partout."""
    return recipe.get("composition") or recipe.get("ingredients") or []


def _item_id(i) -> str:
    if isinstance(i, dict):
        return str(i.get("ingredient") or i.get("ingredient_id") or "").lower()
    return str(i).lower()


def _ings(recipe: dict) -> set[str]:
    """Ids des ingrédients et leur clé de prix (« egg_raw » → egg)."""
    from backend.core.data_io import load_prices_catalog, resolve_catalog_key
    catalog = load_prices_catalog()
    out: set[str] = set()
    for i in _items(recipe):
        iid = _item_id(i)
        if iid:
            out.add(iid)
            key = resolve_catalog_key(iid, catalog)
            if key:
                out.add(key)
    return out


def _words(recipe: dict) -> tuple[set[str], set[str]]:
    """(mots des ids et clés de prix, rôles de composition)."""
    words: set[str] = set()
    for iid in _ings(recipe):
        words.add(iid)
        words.update(iid.replace("/", "_").split("_"))
    roles = {str((i.get("meta") or {}).get("role") or "").lower()
             for i in _items(recipe) if isinstance(i, dict)}
    return words, roles


def validate_recipe(recipe: dict) -> dict:
    """
    Valide la cohérence culinaire d'une recette.

    Score = 10 - pénalités (critical: -2, warning: -1, info: 0)

    Returns:
        {score, is_valid, violations: list[dict]}
    """
    words, roles = _words(recipe)
    dish        = str(recipe.get("dish_type") or "").lower()
    violations  = []
    penalties   = {"critical": 2, "warning": 1, "info": 0}

    # 1. Nombre d'ingrédients
    n = len(_items(recipe))
    if n < 3:
        violations.append(RuleViolation("TOO_FEW_INGREDIENTS", "warning",
            f"Seulement {n} ingrédient(s) — recette incomplète ?",
            "Vérifier la complétude"))
    elif n > 25:
        violations.append(RuleViolation("TOO_MANY_INGREDIENTS", "info",
            f"{n} ingrédients — très complexe",
            "Envisager de simplifier"))

    # 2. Source de protéines végétales (plats principaux seulement : un
    #    accompagnement ou un dessert n'en a pas besoin)
    if dish in _NEEDS_PROTEIN and not (words & _PLANT_PROTEINS or roles & _ROLE_PROTEIN):
        violations.append(RuleViolation("NO_PLANT_PROTEIN", "warning",
            "Aucune source de protéines végétales identifiée",
            "Ajouter légumineuses, tofu, œufs ou noix"))

    # 3. Matière grasse
    if not (words & _FATS or roles & _ROLE_FAT):
        violations.append(RuleViolation("NO_FAT", "info",
            "Aucune matière grasse",
            "Ajouter huile d'olive ou noix"))

    # 4. Aromate ou épice (préparations salées)
    if dish in _NEEDS_AROMATIC and not (words & _AROMATICS_AND_SPICES or roles & _ROLE_AROMATIC):
        violations.append(RuleViolation("NO_AROMATIC", "warning",
            "Aucun aromate ni épice — recette potentiellement fade",
            "Ajouter ail, oignon, herbes ou épices"))

    # 5. Cohérence vegan/ingrédients : profil de régime de chaque ingrédient
    #    (comme tests/test_data_integrity), suggestions de service exclues.
    #    Pas la clé de prix : le beurre végétal y est rangé avec le beurre.
    flags = recipe.get("diet_flags") or {}
    if isinstance(flags, dict) and flags.get("vegan"):
        from backend.db.culinary_repositories import IngredientRepository
        repo = IngredientRepository()
        non_vegan_found = {
            _item_id(i) for i in _items(recipe)
            if isinstance(i, dict) and (i.get("meta") or {}).get("role") != "serving_suggestion"
            and ((repo.get_by_name(_item_id(i)) or {}).get("diet_profile") or {}).get("vegan") is False
        }
        if non_vegan_found:
            violations.append(RuleViolation("VEGAN_FLAG_INCONSISTENT", "critical",
                f"Flag vegan mais ingrédients non-vegan : {non_vegan_found}",
                "Corriger le flag ou substituer les ingrédients"))

    # Calcul du score
    penalty = sum(penalties.get(v.severity, 0) for v in violations)
    score   = max(0, 10 - penalty)

    return {
        "score":      score,
        "is_valid":   score >= 6,
        "violations": [v.to_dict() for v in violations],
    }
