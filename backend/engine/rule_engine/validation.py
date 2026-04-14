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

_PLANT_PROTEINS = {
    "tofu", "tempeh", "seitan", "chickpea", "lentils", "lentilles_corail",
    "black_beans", "kidney_beans", "white_beans", "soybean", "edamame",
    "pea", "fava_bean", "quinoa", "paneer", "egg", "oeuf",
    "peanut", "peanut_butter", "walnuts", "almonds", "cashews",
    "tofu_soyeux", "tofu_ferme", "tofu_feta",
}
_FATS = {
    "oil", "olive_oil", "butter", "ghee", "coconut_oil", "sesame_oil",
    "sunflower_oil", "vegetable_oil", "creme", "beurre", "lait_coco",
    "coconut_milk", "fromage", "cheese", "feta", "parmesan", "tahini",
}
_AROMATICS_AND_SPICES = {
    "onion", "garlic", "ginger", "shallot", "oignon", "ail",
    "cumin", "turmeric", "paprika", "coriander_ground", "garam_masala",
    "cinnamon", "curry_powder", "chili_powder", "pepper", "black_pepper",
    "basil", "parsley", "thyme", "oregano", "mint", "rosemary",
}


@dataclass
class RuleViolation:
    rule:       str
    severity:   str   # "critical" | "warning" | "info"
    message:    str
    suggestion: str = ""

    def to_dict(self) -> dict:
        return {"rule": self.rule, "severity": self.severity,
                "message": self.message, "suggestion": self.suggestion}


def _ings(recipe: dict) -> set[str]:
    return {
        (i.get("ingredient_id", "") if isinstance(i, dict) else str(i)).lower()
        for i in recipe.get("ingredients", [])
    } - {""}


def validate_recipe(recipe: dict) -> dict:
    """
    Valide la cohérence culinaire d'une recette.

    Score = 10 - pénalités (critical: -2, warning: -1, info: 0)

    Returns:
        {score, is_valid, violations: list[dict]}
    """
    ids         = _ings(recipe)
    violations  = []
    penalties   = {"critical": 2, "warning": 1, "info": 0}

    # 1. Nombre d'ingrédients
    n = len(recipe.get("ingredients", []))
    if n < 3:
        violations.append(RuleViolation("TOO_FEW_INGREDIENTS", "warning",
            f"Seulement {n} ingrédient(s) — recette incomplète ?",
            "Vérifier la complétude"))
    elif n > 25:
        violations.append(RuleViolation("TOO_MANY_INGREDIENTS", "info",
            f"{n} ingrédients — très complexe",
            "Envisager de simplifier"))

    # 2. Source de protéines végétales
    if not (ids & _PLANT_PROTEINS):
        violations.append(RuleViolation("NO_PLANT_PROTEIN", "warning",
            "Aucune source de protéines végétales identifiée",
            "Ajouter légumineuses, tofu, œufs ou noix"))

    # 3. Matière grasse
    if not (ids & _FATS):
        violations.append(RuleViolation("NO_FAT", "info",
            "Aucune matière grasse",
            "Ajouter huile d'olive ou noix"))

    # 4. Aromate ou épice
    if not (ids & _AROMATICS_AND_SPICES):
        violations.append(RuleViolation("NO_AROMATIC", "warning",
            "Aucun aromate ni épice — recette potentiellement fade",
            "Ajouter ail, oignon, herbes ou épices"))

    # 5. Cohérence vegan/ingrédients
    from backend.engine.rule_engine.diet import NON_VEGAN
    flags = recipe.get("diet_flags") or {}
    if isinstance(flags, dict) and flags.get("vegan"):
        non_vegan_found = ids & NON_VEGAN
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
