"""
nutrition_form_engine.py — Impact nutritionnel selon la forme de l'ingrédient (CDC_05).

Certains ingrédients ont des valeurs nutritionnelles très différentes selon leur forme :
  - Épinards crus : 23 kcal/100g  vs  épinards cuits : 23 kcal (mais volume réduit 7x)
  - Légumineuses crues : ~350 kcal vs  cuites : ~120 kcal
  - Riz cru : 350 kcal  vs  riz cuit : 130 kcal (absorption eau)

Cet engine ajuste les valeurs nutritionnelles selon la forme déclarée
dans le champ `form` de la composition.

API publique :
    adjust_for_form(ingredient_id, quantity_g, form, nutr_per_100g) → dict
    get_form_factor(ingredient_id, form)                             → float
    apply_to_recipe(recipe, nutrition_db)                            → dict
"""
import logging

logger = logging.getLogger(__name__)

# ── Facteurs de conversion par forme ─────────────────────────────────────────
# format : {ingredient_id: {form: facteur}}
# facteur > 1 : valeurs nutritionnelles augmentent (ex: concentration)
# facteur < 1 : valeurs nutritionnelles diminuent (ex: cuisson / absorption eau)

_FORM_FACTORS: dict[str, dict[str, float]] = {
    # Légumineuses : crues vs cuites
    "lentils":      {"raw": 3.0, "cru": 3.0, "cooked": 1.0, "cuit": 1.0},
    "chickpea":     {"raw": 3.2, "cru": 3.2, "cooked": 1.0, "cuit": 1.0},
    "soybean":      {"raw": 2.5, "cru": 2.5, "cooked": 1.0, "cuit": 1.0},
    "black_beans":  {"raw": 3.0, "cru": 3.0, "cooked": 1.0, "cuit": 1.0},
    # Céréales : crues vs cuites (absorption eau)
    "rice":         {"raw": 2.7, "cru": 2.7, "cooked": 1.0, "cuit": 1.0},
    "oats":         {"raw": 1.7, "cru": 1.7, "cooked": 1.0, "porridge": 1.0},
    "quinoa":       {"raw": 2.5, "cru": 2.5, "cooked": 1.0, "cuit": 1.0},
    # Légumes feuilles : crus vs cuits (réduction volume)
    "spinach":      {"raw": 0.14, "cru": 0.14, "cooked": 1.0, "sauté": 1.0},
    "kale":         {"raw": 0.17, "cru": 0.17, "cooked": 1.0},
    # Champignons : crus vs cuits (libèrent eau)
    "mushroom":     {"raw": 0.8, "cru": 0.8, "cooked": 1.0, "sauté": 1.0},
    # Tomates : fraîches vs concentrées
    "tomato":       {"fresh": 1.0, "paste": 5.0, "concentré": 5.0, "sun_dried": 8.0},
    # Noix de coco
    "coconut":      {"fresh": 1.0, "desiccated": 2.5, "râpé": 2.5},
}

_DEFAULT_FACTOR = 1.0


def get_form_factor(ingredient_id: str, form: str | None) -> float:
    """
    Retourne le facteur de conversion nutritionnelle selon la forme.

    Ex: get_form_factor("lentils", "raw") → 3.0
        (les lentilles crues ont 3x plus de calories que cuites à poids égal)
    """
    if not form:
        return _DEFAULT_FACTOR
    form_lower = form.lower().strip()
    factors    = _FORM_FACTORS.get(ingredient_id, {})
    # Correspondance exacte
    if form_lower in factors:
        return factors[form_lower]
    # Correspondance partielle
    for key, val in factors.items():
        if key in form_lower or form_lower in key:
            return val
    return _DEFAULT_FACTOR


def adjust_for_form(ingredient_id: str,
                    quantity_g:    float,
                    form:          str | None,
                    nutr_per_100g: dict) -> dict:
    """
    Ajuste les valeurs nutritionnelles d'un ingrédient selon sa forme.

    Args:
        ingredient_id : ID ingrédient
        quantity_g    : quantité en grammes
        form          : forme de l'ingrédient (raw, cuit, concentré…)
        nutr_per_100g : valeurs nutritionnelles de référence pour 100g

    Returns:
        Dict des valeurs nutritionnelles pour la quantité donnée,
        ajustées selon la forme.
    """
    factor = get_form_factor(ingredient_id, form)
    result = {}
    for key, val in nutr_per_100g.items():
        if isinstance(val, (int, float)) and val is not None:
            result[key] = round(val * quantity_g / 100 * factor, 3)
    result["_form_factor"]    = factor
    result["_form_applied"]   = form
    result["_quantity_g"]     = quantity_g
    return result


def apply_to_recipe(recipe: dict, nutrition_db: dict) -> dict:
    """
    Calcule la nutrition d'une recette en tenant compte des formes des ingrédients.

    Retourne un dict de valeurs nutritionnelles totales (toute la recette).
    Plus précis que nutrition_engine.compute_nutrition() pour les ingrédients
    avec transformation (légumineuses, céréales, légumes feuilles).
    """
    totals: dict[str, float] = {}
    for item in recipe.get("composition", []):
        if not isinstance(item, dict):
            continue
        iid    = item.get("ingredient", "")
        qty    = item.get("quantity") or 0
        unit   = item.get("unit", "g")
        form   = item.get("form")

        # Conversion quantité → grammes
        qty_g = float(qty)
        if unit == "kg":
            qty_g *= 1000
        elif unit in ("piece", ""):
            qty_g *= 100

        # Récupérer les données nutritionnelles
        nutr = nutrition_db.get(iid, {})
        if not nutr or qty_g <= 0:
            continue

        # Ajustement selon la forme
        adjusted = adjust_for_form(iid, qty_g, form, nutr)
        for k, v in adjusted.items():
            if k.startswith("_"):
                continue
            if isinstance(v, (int, float)):
                totals[k] = totals.get(k, 0.0) + v

    totals["_form_adjusted"] = True
    return totals
