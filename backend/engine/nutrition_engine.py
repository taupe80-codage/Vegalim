"""
Nutrition Engine
=================
Calcule la nutrition d'une recette à la volée depuis la base CIQUAL.

Spec : sum nutrients | macro + micro | Use real DB

Utilise :
  - data/nutrition/nutrition_database.json (687 entrées CIQUAL)
  - data/ingredients/ingredients_dictionary.json (310 entrées avec nutrition_key)
  - data/ingredients/ingredient_physical.json (116 entrées — unités, densité, edible_pct)
  - composition de la recette (quantités réelles) si disponible

Retourne macros + micros par portion (÷ servings).
"""

from backend.db.data_access import get_data
from backend.engine.config import SERVINGS_DEFAULT, FRYING_CAP_G


# Facteurs de conversion unité → grammes (fallback si absent de ingredient_physical)
UNIT_TO_G = {
    "g":              1.0,   "kg":        1000.0,
    "ml":             1.0,   "l":         1000.0,
    "cuillere_soupe": 15.0,  "cuillere_cafe": 5.0,
    "tbsp":           15.0,  "tsp":       5.0,
    "gousse":         5.0,   "tranche":   30.0,
    "branche":        10.0,  "botte":     80.0,
    "piece":          100.0, "cup":       240.0,
    "oz":             28.0,  "lb":        454.0,
}

MACROS   = ["calories", "protein", "carbs", "fat", "fiber", "sugar", "sodium"]
MICROS   = ["calcium", "iron", "magnesium", "potassium",
            "vitamin_c", "vitamin_b12", "zinc", "phosphorus"]
ALL_KEYS = MACROS + MICROS

# Valeurs par défaut de portions par type de plat (mirroir de recipes.json)
DEFAULT_SERVINGS_BY_TYPE: dict[str, int] = {
    "main":      4,
    "soup":      4,
    "side":      4,
    "starter":   4,
    "dessert":   6,
    "snack":     2,
    "breakfast": 2,
    "sauce":     8,
}


def resolve_servings(recipe: dict, user_override: int | None = None) -> int:
    """
    Résout le nombre de portions effectif pour une recette.

    Priorité décroissante :
      1. user_override (paramètre API ?servings=N)
      2. recipe.servings_user_override (override stocké dans la recette)
      3. recipe.servings_default (valeur calibrée par dish_type)
      4. recipe.servings (valeur brute du JSON)
      5. DEFAULT_SERVINGS_BY_TYPE[dish_type]
      6. SERVINGS_DEFAULT (4 — fallback universel)
    """
    if user_override and isinstance(user_override, int) and user_override > 0:
        return user_override
    stored_override = recipe.get("servings_user_override")
    if stored_override and isinstance(stored_override, int) and stored_override > 0:
        return stored_override
    default = recipe.get("servings_default")
    if default and isinstance(default, int) and default > 0:
        return default
    raw = recipe.get("servings")
    if raw and isinstance(raw, (int, float)) and raw > 0:
        return int(raw)
    dish_type = recipe.get("dish_type", "")
    if isinstance(dish_type, str) and dish_type in DEFAULT_SERVINGS_BY_TYPE:
        return DEFAULT_SERVINGS_BY_TYPE[dish_type]
    return SERVINGS_DEFAULT


def _physical_unit_g(ingredient_id: str, unit: str) -> float | None:
    """
    Résout un facteur de conversion unité→g depuis ingredient_physical.json.
    Retourne None si non trouvé (fallback sur UNIT_TO_G).
    """
    from backend.core.data_io import load_ingredient_physical
    physical = load_ingredient_physical()
    entry = physical.get(ingredient_id)
    if not entry:
        return None
    units = entry.get("units", {})
    unit_entry = units.get(unit)
    if unit_entry and "g" in unit_entry:
        return float(unit_entry["g"])
    return None

def _physical_edible_pct(ingredient_id: str) -> float:
    from backend.core.data_io import load_ingredient_physical
    physical = load_ingredient_physical()
    entry = physical.get(ingredient_id, {})
    pct = entry.get("edible_pct", 100.0)
    return float(pct) / 100.0 if pct is not None else 1.0


def _qty_to_g(token: str, comp_entry: dict) -> float:
    """Convertit la quantité d'un ingrédient en grammes."""
    if token == "huile_friture":
        return FRYING_CAP_G

    qty = comp_entry.get("quantity") or 0
    unit = (comp_entry.get("unit") or "piece").lower()

    if not isinstance(qty, (int, float)) or qty <= 0:
        return 0.0

    if unit == "piece":
        ing = get_data.ingredients.get_by_name(token)
        avg_w = None

        if ing:
            nutr = get_data.ingredients.resolve_nutrition(token)
            if nutr:
                avg_w = nutr.get("average_unit_weight_g")

        # Fallback : ingredient_physical.default_unit → g
        if avg_w is None:
            phys_g = _physical_unit_g(token, "piece")
            if phys_g:
                avg_w = phys_g

        factor = float(avg_w) if avg_w else 100.0
    else:
        # Priorité : ingredient_physical → UNIT_TO_G statique
        factor = _physical_unit_g(token, unit) or UNIT_TO_G.get(unit, 50.0)

    return float(qty) * factor * _physical_edible_pct(token)

def compute_nutrition(recipe: dict,
                      servings: int | None = None) -> dict:
    """
    Calcule la nutrition d'une recette par portion.

    Args:
        recipe   : dict recette avec 'composition' (et optionnellement 'ingredients')
        servings : override utilisateur du nombre de portions.
                   Si None, utilise resolve_servings() qui lit dans l'ordre :
                   servings_user_override → servings_default → servings → dish_type → 4

    Returns:
        dict {calories, protein, carbs, fat, fiber, sugar, sodium,
              calcium, iron, …, glycemic_index, servings_used, source}
    """
    srv              = resolve_servings(recipe, user_override=servings)
    totals           = {k: 0.0 for k in ALL_KEYS}
    gi_sum, gi_n     = 0.0, 0

    ingredients = recipe.get("ingredients", [])
    comp        = {c["ingredient"]: c for c in recipe.get("composition", [])}
    
    if not ingredients and comp:
        ingredients = list(comp.keys())

    for raw_token in ingredients:
        # Accepte str (id direct) ou dict {ingredient_id: ...}
        token = raw_token.get("ingredient_id", "") if isinstance(raw_token, dict) else raw_token
        if not token:
            continue
        ing = get_data.ingredients.get_by_name(token)
        n_data = get_data.ingredients.resolve_nutrition(token)

        if not n_data:
            continue

        # Quantité en grammes
        comp_e = comp.get(token, {})
        cat = ing.get("category", "") if ing else ""
        if not comp_e:
            # Estimation par catégorie si pas de composition
            if cat in ("spice", "spice_mix", "herb", "seasoning"):
                qty_g = 5.0
            elif cat in ("fat_oil", "fat"):
                qty_g = 15.0
            elif cat == "condiment":
                qty_g = 20.0
            else:
                qty_g = 100.0
        else:
            qty_g = _qty_to_g(token, comp_e)

        # Facteur de forme (cru/cuit) via nutrition_form_engine (CDC_05)
        form = comp_e.get("form") if comp_e else None
        try:
            from backend.engine.nutrition_form_engine import get_form_factor
            form_factor = get_form_factor(token, form)
        except Exception:
            form_factor = 1.0

        f = qty_g / 100.0 * form_factor
        for k in ALL_KEYS:
            v = n_data.get(k)
            if v is not None:
                totals[k] += float(v) * f

        gi = n_data.get("glycemic_index")
        if gi:
            gi_sum += float(gi)
            gi_n   += 1

    result = {k: round(v / srv, 1) for k, v in totals.items()}
    result["calories"]       = round(totals["calories"] / srv)
    result["sodium"]         = round(totals["sodium"]   / srv)
    if gi_n:
        result["glycemic_index"] = round(gi_sum / gi_n)
    result["servings_used"] = srv   # renvoie le nb de portions utilisé pour le calcul
    result["source"] = "ciqual_computed"
    return result


def compute_nutrition_from_tokens(tokens: list[str],
                                  servings: int = 4) -> dict:
    """
    Calcule la nutrition depuis une simple liste de tokens (sans composition).
    Utile pour des recettes importées non structurées.
    """
    return compute_nutrition({"ingredients": tokens}, servings)


# Alias de compatibilité — utilisé par reco_service
compute_nutrition_score = compute_nutrition


def score_nutrition_values(nutr: dict, profile: dict | None = None) -> float:
    """
    Score nutritionnel depuis un dict de valeurs {protein, calories, fiber...}.
    Utilisé par reco_service quand la nutrition vient du graph séparé.

    Délègue le calcul de base à ajr_score() (source de vérité AJR ANSES/OMS),
    puis applique les ajustements profil (malus sucre, bonus hyperprotéiné).

    Retourne un score 0-10 cohérent avec les autres engines de scoring.
    """
    if not nutr or not isinstance(nutr, dict):
        return 0.0

    from backend.engine.score_engine.ajr import ajr_score
    base = ajr_score(nutr)["score"]  # 0-10, source de vérité AJR

    p    = profile or {}
    diet = p.get("diet", "")

    sugar   = float(nutr.get("sugar",   0) or 0)
    protein = float(nutr.get("protein", 0) or 0)

    # Ajustements profil (delta sur le score AJR de base)
    delta = 0.0
    if diet == "diabete" or p.get("low_sugar"):
        delta -= min(sugar * 0.1, 2.0)   # malus sucre renforcé
    else:
        delta -= min(sugar * 0.02, 0.5)  # malus sucre standard

    if diet == "hyperproteine":
        delta += min(protein * 0.1, 2.0)  # bonus protéine

    return round(max(0.0, min(10.0, base + delta)), 2)
