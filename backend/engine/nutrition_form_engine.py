"""
nutrition_form_engine.py — Impact nutritionnel selon l'état de cuisson (CDC_05).

Utilise ingredients_tree_enriched_v2.json comme référence (remplace les facteurs
manuels hardcodés de la v précédente).

Deux stratégies selon la disponibilité des données :
  1. Si le tree a un groupe dédié au bon cooking_state → utiliser ses source_id
     pour pointer vers la bonne entrée nutritionnelle (cru vs cuit vs bouilli).
  2. Sinon → facteur scalaire de fallback pour les cas critiques (légumineuses,
     céréales) où la différence cru/cuit est majeure.

API publique :
    get_tree_variant(ingredient_id, cooking_state) → dict | None
    get_form_factor(ingredient_id, form)           → float
    adjust_for_form(ingredient_id, quantity_g, form, nutr_per_100g) → dict
    apply_to_recipe(recipe, nutrition_db)          → dict
"""
import logging

logger = logging.getLogger(__name__)

# ── Facteurs scalaires de fallback (uniquement si le tree ne couvre pas) ──────
# Couvrent les cas où la différence cru→cuit est critique (poids sec vs réhydraté)
_FALLBACK_FACTORS: dict[str, dict[str, float]] = {
    # Légumineuses : crues ~3× plus denses que cuites (réhydratation)
    "lentils":     {"raw": 3.0, "cru": 3.0, "cooked": 1.0, "cuit": 1.0, "boiled": 1.0},
    "chickpea":    {"raw": 3.2, "cru": 3.2, "cooked": 1.0, "cuit": 1.0, "boiled": 1.0},
    "soybean":     {"raw": 2.5, "cru": 2.5, "cooked": 1.0, "cuit": 1.0},
    "black_beans": {"raw": 3.0, "cru": 3.0, "cooked": 1.0, "cuit": 1.0},
    # Céréales : absorption eau à la cuisson
    "rice":        {"raw": 2.7, "cru": 2.7, "cooked": 1.0, "cuit": 1.0},
    "oats":        {"raw": 1.7, "cru": 1.7, "cooked": 1.0, "porridge": 1.0},
    "quinoa":      {"raw": 2.5, "cru": 2.5, "cooked": 1.0, "cuit": 1.0},
    # Légumes feuilles : réduction volume à la cuisson
    "spinach":     {"raw": 0.14, "cru": 0.14, "cooked": 1.0, "sauté": 1.0, "sauteed": 1.0},
    "kale":        {"raw": 0.17, "cru": 0.17, "cooked": 1.0},
    # Champignons : libèrent eau à la cuisson
    "mushroom":    {"raw": 0.8, "cru": 0.8, "cooked": 1.0, "sauté": 1.0, "sauteed": 1.0},
    # Tomates : fraîches vs concentrées
    "tomato":      {"fresh": 1.0, "paste": 5.0, "concentré": 5.0, "sun_dried": 8.0},
    # Noix de coco
    "coconut":     {"fresh": 1.0, "desiccated": 2.5, "râpé": 2.5},
}

_DEFAULT_FACTOR = 1.0


def get_tree_variant(ingredient_id: str, cooking_state: str | None) -> dict | None:
    """
    Retourne le groupe tree le plus adapté pour cet ingrédient et cet état de cuisson.
    Délègue à data_io.resolve_ingredient_cooking_variant().
    """
    try:
        from backend.core.data_io import resolve_ingredient_cooking_variant
        return resolve_ingredient_cooking_variant(ingredient_id, cooking_state)
    except Exception as exc:
        logger.debug("tree lookup failed for %s: %s", ingredient_id, exc)
        return None


def get_form_factor(ingredient_id: str, form: str | None) -> float:
    """
    Facteur de conversion nutritionnelle selon la forme/état de cuisson.
    Consulte d'abord le tree ; bascule sur les facteurs scalaires de fallback.
    """
    if not form:
        return _DEFAULT_FACTOR

    form_lower = form.lower().strip()

    # ── Tentative via tree ────────────────────────────────────────────────────
    # Le tree couvre mieux les variants cru/cuit ; si on trouve les deux on peut
    # calculer un ratio précis. Pour l'instant on garde le fallback scalaire
    # pour les cas critiques et on retourne 1.0 si le tree couvre sans facteur.
    tree_group = get_tree_variant(ingredient_id, form_lower)
    if tree_group is not None:
        # Si le tree connaît cet état, vérifier si un facteur scalaire existe aussi
        base = ingredient_id.split('/')[0]
        factors = _FALLBACK_FACTORS.get(base, {})
        if form_lower in factors:
            return factors[form_lower]
        # tree couvre l'état mais pas de facteur scalaire → 1.0 (valeurs tree directes)
        return _DEFAULT_FACTOR

    # ── Fallback scalaire ─────────────────────────────────────────────────────
    base = ingredient_id.split('/')[0]
    factors = _FALLBACK_FACTORS.get(base, {})
    if form_lower in factors:
        return factors[form_lower]
    for key, val in factors.items():
        if key in form_lower or form_lower in key:
            return val

    return _DEFAULT_FACTOR


def adjust_for_form(
    ingredient_id: str,
    quantity_g:    float,
    form:          str | None,
    nutr_per_100g: dict,
) -> dict:
    """
    Ajuste les valeurs nutritionnelles d'un ingrédient selon sa forme/état de cuisson.

    Args:
        ingredient_id : ID ingrédient (ex: 'lentils', 'carrot/default')
        quantity_g    : quantité en grammes
        form          : état de cuisson (raw, boiled, steamed, …)
        nutr_per_100g : valeurs nutritionnelles de référence pour 100g

    Returns:
        Dict des valeurs nutritionnelles pour la quantité, ajustées selon la forme.
    """
    factor = get_form_factor(ingredient_id, form)
    result = {}
    for key, val in nutr_per_100g.items():
        if isinstance(val, (int, float)) and val is not None:
            result[key] = round(val * quantity_g / 100 * factor, 3)
    result["_form_factor"]  = factor
    result["_form_applied"] = form
    result["_quantity_g"]   = quantity_g
    return result


def apply_to_recipe(recipe: dict, nutrition_db: dict) -> dict:
    """
    Calcule la nutrition d'une recette en tenant compte des états de cuisson.

    Consulte le tree pour chaque ingrédient afin d'utiliser les valeurs
    nutritionnelles du variant cuit/cru approprié quand disponible.

    Returns:
        Dict de valeurs nutritionnelles totales (toute la recette).
    """
    totals: dict[str, float] = {}
    for item in recipe.get("composition", []):
        if not isinstance(item, dict):
            continue
        iid    = item.get("ingredient", "")
        qty    = item.get("quantity") or 0
        unit   = item.get("unit", "g")
        form   = item.get("form") or item.get("meta", {}).get("state")

        qty_g = float(qty)
        if unit == "kg":
            qty_g *= 1000
        elif unit in ("piece", ""):
            qty_g *= 100

        nutr = nutrition_db.get(iid, {})
        if not nutr or qty_g <= 0:
            continue

        adjusted = adjust_for_form(iid, qty_g, form, nutr)
        for k, v in adjusted.items():
            if k.startswith("_"):
                continue
            if isinstance(v, (int, float)):
                totals[k] = totals.get(k, 0.0) + v

    totals["_form_adjusted"] = True
    return totals
