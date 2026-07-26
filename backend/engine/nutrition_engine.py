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

MACROS   = ["calories", "protein", "carbs", "fat", "fiber", "sugar", "sodium",
            "saturated_fat", "monounsaturated_fat", "polyunsaturated_fat"]
MICROS   = ["calcium", "iron", "magnesium", "potassium",
            "vitamin_c", "vitamin_b12", "zinc", "phosphorus",
            "vitamin_a", "vitamin_d", "vitamin_e", "vitamin_k", "folate", "omega3"]
# "salt" est dérivé de sodium après calcul (pas dans la DB) → ajouté en post-traitement
ALL_KEYS = MACROS + MICROS

# Correspondance champs nutrition_v2 (suffixe _kcal/_g/_mg/_ug) → clés internes
# Permet de gérer les deux formats de la DB sans modifier la logique de calcul.
_V2_FIELD_MAP: dict[str, str] = {
    # Macros
    "calories_kcal":    "calories",
    "protein_g":        "protein",
    "carbs_g":          "carbs",
    "fat_g":            "fat",
    "fiber_g":          "fiber",
    "sugar_g":          "sugar",
    # Sodium
    "sodium_mg":        "sodium",
    # Acides gras — notation N2/CIQUAL (fa_*), corrigé depuis saturated_fat_g
    "fa_saturated_g":   "saturated_fat",
    "fa_mufa_g":        "monounsaturated_fat",
    "fa_pufa_g":        "polyunsaturated_fat",
    # Minéraux
    "calcium_mg":       "calcium",
    "iron_mg":          "iron",
    "magnesium_mg":     "magnesium",
    "potassium_mg":     "potassium",
    "zinc_mg":          "zinc",
    "phosphorus_mg":    "phosphorus",
    # Vitamines
    "vitamin_c_mg":     "vitamin_c",
    "vitamin_b12_ug":   "vitamin_b12",
    "vitamin_a_rae_ug": "vitamin_a",   # corrigé depuis vitamin_a_ug (RAE = unité CIQUAL)
    "vitamin_d_ug":     "vitamin_d",
    "vitamin_e_mg":     "vitamin_e",
    "vitamin_k1_ug":    "vitamin_k",
    "vitamin_k2_ug":    "vitamin_k",   # s'additionne (K1 + K2)
    "folate_dfe_ug":    "folate",      # corrigé depuis folate_ug (DFE = unité CIQUAL)
    # Oméga-3 — s'additionnent (ALA + EPA + DHA)
    "omega3_g":         "omega3",
    "fa_18_3_ala_g":    "omega3",
    "fa_20_5_epa_g":    "omega3",
    "fa_22_6_dha_g":    "omega3",
}


def _normalize_n_data(n_data: dict) -> dict:
    """
    Normalise un dict nutritionnel v2 (champs suffixés _kcal/_g/_mg/_ug)
    vers les clés internes attendues par compute_nutrition().

    Les clés déjà au bon format (ex: 'calories') sont conservées.
    La valeur d'une clé suffixée est convertie en mg/100g si nécessaire
    (les valeurs de nutrition_v2 sont déjà en unités cohérentes pour 100g).
    """
    if not n_data:
        return n_data
    normalized: dict = {}
    for k, v in n_data.items():
        canonical = _V2_FIELD_MAP.get(k)
        if canonical:
            # Ne pas écraser si la clé canonique existe déjà avec une valeur
            if canonical not in normalized and v is not None:
                normalized[canonical] = v
        else:
            if k not in normalized:
                normalized[k] = v
    return normalized

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
    if unit_entry and unit_entry.get("g") is not None:
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

    # Plat chaud → utiliser les valeurs nutritionnelles cuites quand disponibles.
    # Un plat est considéré "chaud" si timing.cook_min > 0.
    is_hot_dish: bool = (recipe.get("timing", {}).get("cook_min") or 0) > 0

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

        # Décision cuisson par ingrédient :
        #   - plat chaud par défaut → use_cooked=True
        #   - sauf si meta.final_state == "raw" (garnish, herbe fraîche…)
        #   - sauf si meta.state == "cooked" (ingrédient déjà pré-cuit en entrée)
        #   - sauf si catégorie "poids sec" (grain/legume/pasta/flour) :
        #     les recettes spécifient la quantité en poids sec, mais les clés N2
        #     "cuit" sont par 100g réhydraté → substitution invalide.
        _DRY_WEIGHT_CATS = {"grain", "cereal", "legume", "pulse", "pasta", "noodle", "flour"}
        comp_e = comp.get(token, {})
        meta   = comp_e.get("meta", {}) if comp_e else {}
        final_state = meta.get("final_state")        # override explicite
        input_state = meta.get("state", "")          # état entrant
        ing_cat     = (ing.get("category") or "") if ing else ""
        cooked_subst_ok = bool(ing.get("cooked_subst_ok")) if ing else False
        stays_raw = (
            final_state == "raw"                     # override manuel
            or input_state in ("cooked", "sauteed", "grilled", "baked", "roasted")
            or (ing_cat in _DRY_WEIGHT_CATS and not cooked_subst_ok)
            # poids sec → pas de substitution, sauf exception explicite (légume frais)
        )
        use_cooked = is_hot_dish and not stays_raw

        # État de cuisson explicite déclaré dans la composition (override précis)
        # Exemples : meta.state = "roasted", "sauteed", "grilled"
        # Si présent et pas "raw", il remplace la logique use_cooked générique.
        explicit_cooking_state: str | None = None
        if input_state and input_state not in ("raw", ""):
            explicit_cooking_state = input_state
        elif final_state and final_state not in ("raw", ""):
            explicit_cooking_state = final_state

        n_data = get_data.ingredients.resolve_nutrition(
            token,
            use_cooked=use_cooked,
            cooking_state=explicit_cooking_state,
        )

        if not n_data:
            continue

        # Normaliser les champs v2 (calories_kcal → calories, protein_g → protein...)
        n_data = _normalize_n_data(n_data)

        # Quantité en grammes (comp_e déjà résolu plus haut)
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
    # Sel dérivé du sodium (1 mg sodium = 0.00254 g sel, norme UE Règl. 1169/2011)
    if totals.get("sodium", 0) > 0:
        result["salt"] = round(totals["sodium"] / srv * 0.00254, 2)
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


# Alias de compat — logique déplacée dans score_engine/ajr.py (responsabilité scoring)
from backend.engine.score_engine.ajr import ajr_score_with_profile as score_nutrition_values  # noqa: F401
