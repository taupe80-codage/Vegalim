"""
shopping.py — Liste de courses depuis un plan ou une sélection de recettes.

API publique :
    shopping_list(meal_plan, eco)           → dict
    shopping_list_from_recipes(ids, eco)    → dict
"""
from __future__ import annotations
import logging
import math
from collections import defaultdict

logger = logging.getLogger(__name__)

# ── Moteur de prix par conditionnement ───────────────────────────────────────

_PKG_TO_G  = {"g": 1.0, "kg": 1000.0, "mg": 0.001}
_PKG_TO_ML = {"ml": 1.0, "cl": 10.0, "dl": 100.0, "l": 1000.0, "L": 1000.0}

def _pkg_to_base(qty: float, unit: str) -> tuple[float, str] | None:
    u = unit.lower()
    if u in _PKG_TO_G:  return qty * _PKG_TO_G[u],  "g"
    if u in _PKG_TO_ML: return qty * _PKG_TO_ML[u], "ml"
    if u in ("piece", "pieces", "pièce", "pièces"): return qty, "piece"
    return None

def _item_to_base(qty: float, unit: str) -> tuple[float, str] | None:
    """Same conversion for shopping item units (already normalised by _normalise_unit)."""
    return _pkg_to_base(qty, unit)

def _compute_price(ing_key: str, qty_value: float | None, qty_unit: str | None,
                   catalog: dict) -> dict:
    """
    Retourne le prix réel d'achat en tenant compte du conditionnement.
    {price, package_label, n_packages, price_unknown, pantry}
    """
    entry = catalog.get(ing_key)
    if not entry:
        base = ing_key.split("/")[0]
        entry = catalog.get(base)

    pantry = bool(entry.get("pantry")) if entry else False

    if not entry:
        return {"price": 0.0, "package_label": None, "n_packages": 0,
                "price_unknown": True, "pantry": pantry}

    packages = entry.get("packages", [])
    if not packages:
        return {"price": 0.0, "package_label": None, "n_packages": 0,
                "price_unknown": False, "pantry": pantry}

    # Cas sans quantité connue → plus petit paquet
    if qty_value is None or qty_unit is None:
        pkg = min(packages, key=lambda p: p["price"])
        return {"price": round(pkg["price"], 2), "unit_price": round(pkg["price"], 2),
                "package_label": pkg["label"], "n_packages": 1,
                "price_unknown": False, "pantry": pantry}

    # Normaliser la quantité nécessaire
    needed = _item_to_base(qty_value, qty_unit)
    if needed is None:
        pkg = min(packages, key=lambda p: p["price"])
        return {"price": round(pkg["price"], 2), "package_label": pkg["label"],
                "n_packages": 1, "price_unknown": False, "pantry": pantry}
    needed_qty, needed_unit = needed

    # Trouver la combinaison optimale (coût minimal couvrant le besoin)
    best: dict | None = None
    for pkg in packages:
        conv = _pkg_to_base(pkg["qty"], pkg["unit"])
        if conv is None or conv[1] != needed_unit:
            continue
        pkg_qty_base = conv[0]
        if pkg_qty_base <= 0:
            continue
        n    = max(1, math.ceil(needed_qty / pkg_qty_base))
        cost = round(n * pkg["price"], 2)
        if best is None or cost < best["cost"] or (cost == best["cost"] and n < best["n"]):
            best = {"pkg": pkg, "n": n, "cost": cost}

    if best is None:
        # Aucun paquet compatible (unités différentes) → plus petit
        pkg = min(packages, key=lambda p: p["price"])
        return {"price": round(pkg["price"], 2), "unit_price": round(pkg["price"], 2),
                "package_label": pkg["label"], "n_packages": 1,
                "price_unknown": False, "pantry": pantry}

    label = f"{best['n']}× {best['pkg']['label']}" if best["n"] > 1 else best["pkg"]["label"]
    return {"price": best["cost"], "unit_price": round(best["pkg"]["price"], 2),
            "package_label": label, "n_packages": best["n"],
            "price_unknown": False, "pantry": pantry}

# Catégories anglaises → libellés FR  (couvre les valeurs réelles du dict ingrédients)
_CAT_FR = {
    # Légumes
    "vegetable":          "Légumes",
    "vegetables":         "Légumes",
    "legumes":            "Légumes",
    # Fruits
    "fruit":              "Fruits",
    "fruits":             "Fruits",
    # Protéines animales
    "proteins":           "Protéines",
    "meat":               "Viandes",
    "poultry":            "Volaille",
    "fish":               "Poissons",
    "seafood":            "Poissons & fruits de mer",
    # Protéines végétales
    "protein_plant":      "Protéines végétales",
    "leguminous":         "Légumineuses",
    "legumes_sec":        "Légumineuses",
    "legume":             "Légumineuses",
    # Produits laitiers
    "dairy":              "Produits laitiers",
    "dairy_alternative":  "Alternatives laitières",
    "eggs":               "Oeufs",
    "egg":                "Oeufs",
    # Féculents
    "grain":              "Céréales & féculents",
    "grains":             "Céréales & féculents",
    "cereals":            "Céréales & féculents",
    # Noix & graines
    "nut_seed":           "Noix & graines",
    "nuts":               "Noix & graines",
    "seeds":              "Noix & graines",
    # Condiments & épices
    "herb_spice":         "Épices & aromates",
    "condiment":          "Condiments & sauces",
    "condiments":         "Condiments & sauces",
    "spices":             "Épices & aromates",
    "herbs":              "Herbes fraîches",
    # Matières grasses
    "fat":                "Huiles & matières grasses",
    "fats":               "Huiles & matières grasses",
    "oils":               "Huiles & matières grasses",
    # Sucres
    "sweetener":          "Sucres & édulcorants",
    "sweeteners":         "Sucres & édulcorants",
    # Liquides & boissons
    "liquid":             "Liquides & bouillons",
    "beverages":          "Boissons",
    # Autres
    "superfood":          "Superaliments",
    "fermented":          "Fermentés",
    "leavening":          "Levures & poudres",
    "additive":           "Additifs",
    "alcohol":            "Alcools",
    "baking":             "Pâtisserie",
    "canned":             "Conserves",
    "frozen":             "Surgelés",
    "autre":              "Autre",
    "other":              "Autre",
}


# ── Helpers partagés ──────────────────────────────────────────────────────────

def _make_resolvers(ings_dict: dict):
    """Retourne (get_name_fr, get_category_fr) pour un dict d'ingrédients."""

    def _get_name_fr(iid: str) -> str:
        d = ings_dict.get(iid)
        if d and d.get("canonical_name_fr"):
            name = d["canonical_name_fr"]
            return name[0].upper() + name[1:] if name else iid
        base = iid.split("/")[0]
        d = ings_dict.get(base)
        if d and d.get("canonical_name_fr"):
            name = d["canonical_name_fr"]
            return (name[0].upper() + name[1:]) if name else base
        return iid.replace("_", " ").replace("/", " ").capitalize()

    def _get_category_fr(iid: str) -> str:
        d = ings_dict.get(iid) or ings_dict.get(iid.split("/")[0]) or {}
        cat_en = d.get("category", "autre").lower()
        return _CAT_FR.get(cat_en, cat_en.capitalize())

    return _get_name_fr, _get_category_fr


# ── Formatage des quantités ───────────────────────────────────────────────────

_UNIT_FR: dict[str, str] = {
    "g": "g", "kg": "kg", "mg": "mg",
    "ml": "ml", "cl": "cl", "dl": "dl", "l": "L",
    "piece": "pièce", "pieces": "pièces",
    "pinch": "pincée", "pinches": "pincées",
    "leaf": "feuille", "leaves": "feuilles",
    "tbsp": "c. à s.", "tsp": "c. à c.",
    "cup": "tasse", "oz": "oz", "lb": "lb",
    "bunch": "botte", "clove": "gousse", "cloves": "gousses",
    "slice": "tranche", "slices": "tranches",
}

# Unités convertibles en grammes (pour la somme inter-unités)
_TO_GRAMS: dict[str, float] = {
    "kg": 1000.0,
    "mg": 0.001,
}
# Unités convertibles en ml
_TO_ML: dict[str, float] = {
    "cl":  10.0,
    "dl": 100.0,
    "l": 1000.0,
}


def _normalise_unit(qty: float, unit: str) -> tuple[float, str]:
    """Normalise vers g ou ml si possible, sinon retourne tel quel."""
    u = unit.lower()
    if u in _TO_GRAMS:
        return qty * _TO_GRAMS[u], "g"
    if u in _TO_ML:
        return qty * _TO_ML[u], "ml"
    return qty, u


def _fmt_amount(amount: float) -> str:
    """Formate un nombre sans decimale inutile. Ex: 1500 -> '1 500', 1.5 -> '1,5'."""
    if amount == int(amount):
        v = int(amount)
        if v >= 1000:
            s = str(v)
            parts = []
            while len(s) > 3:
                parts.append(s[-3:])
                s = s[:-3]
            parts.append(s)
            return " ".join(reversed(parts))
        return str(v)
    rounded = round(amount, 1)
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.1f}".replace(".", ",")


def _build_qty_str(units_map: dict) -> str | None:
    """
    Construit la chaîne lisible à partir de {unit: total_amount}.
    Exemples : '350 g', '250 ml', '2 pièces', '100 g · 50 ml'
    """
    if not units_map:
        return None
    parts = []
    # Ordre d'affichage : g d'abord, ml ensuite, puis le reste
    order = ["g", "ml"] + [u for u in units_map if u not in ("g", "ml")]
    for unit in order:
        if unit not in units_map:
            continue
        total = units_map[unit]
        u_label = _UNIT_FR.get(unit, unit)
        # Pluriel simple pour pièce/feuille/pincée/etc.
        if u_label in ("pièce", "feuille", "pincée", "gousse", "botte",
                        "tranche", "tasse") and total > 1:
            u_label += "s"
        parts.append(f"{_fmt_amount(total)} {u_label}".strip())
    return " · ".join(parts) if parts else None


def _build_result(
    ing_data: dict,
    n_recipes: int,
    eco: bool,
    prices: dict,
    ings_dict: dict,
    catalog: dict | None = None,
) -> dict:
    """
    Construit le dict de sortie standard.

    ing_data : {ingredient_key: {"occurrences": int, "units": {unit: total_amount}}}
    """
    get_name_fr, get_category_fr = _make_resolvers(ings_dict)
    if catalog is None:
        catalog = {}

    items: list[dict] = []
    total_eur = 0.0
    n_unknown = 0

    for ing, data in sorted(ing_data.items(), key=lambda x: -x[1]["occurrences"]):
        count   = data["occurrences"]
        qty_str = _build_qty_str(data.get("units", {}))

        units_map = data.get("units", {})
        _order = ["g", "ml"] + [u for u in units_map if u not in ("g", "ml")]
        _punit = next((u for u in _order if u in units_map), None)
        qty_value = round(units_map[_punit], 2) if _punit else None

        price_info = _compute_price(ing, qty_value, _punit, catalog)
        if price_info["price_unknown"]:
            n_unknown += 1

        item: dict = {
            "ingredient":    ing,
            "name_fr":       get_name_fr(ing),
            "occurrences":   count,
            "qty_str":       qty_str,
            "qty_value":     qty_value,
            "qty_unit":      _punit,
            "price_eur":     price_info["price"],
            "unit_price":    price_info.get("unit_price"),
            "n_packages":    price_info.get("n_packages", 0),
            "package_label": price_info["package_label"],
            "price_unknown": price_info["price_unknown"],
            "pantry":        price_info["pantry"],
        }
        if eco:
            item["eco_reuse"] = count > 2
        items.append(item)
        total_eur += price_info["price"]

    # Regrouper par catégorie FR
    by_cat: dict[str, list] = defaultdict(list)
    for item in items:
        cat_fr = get_category_fr(item["ingredient"])
        by_cat[cat_fr].append({
            "ingredient":    item["ingredient"],
            "name_fr":       item["name_fr"],
            "occurrences":   item["occurrences"],
            "qty_str":       item["qty_str"],
            "qty_value":     item["qty_value"],
            "qty_unit":      item["qty_unit"],
            "price_eur":     item["price_eur"],
            "unit_price":    item["unit_price"],
            "n_packages":    item["n_packages"],
            "package_label": item["package_label"],
            "price_unknown": item["price_unknown"],
            "pantry":        item["pantry"],
        })

    def _cat_sort(kv):
        k = kv[0]
        return (1 if k == "Autre" else 0, k)

    return {
        "items":          items,
        "estimated_cost": round(total_eur, 2),
        "n_unknown_price": n_unknown,
        "n_recipes":      n_recipes,
        "by_category":    dict(sorted(by_cat.items(), key=_cat_sort)),
    }


def _extract_ingredients(recipe: dict, scale: float = 1.0) -> list[tuple[str, float | None, str]]:
    """
    Extrait (clé_ingrédient, quantité_normalisée, unité) pour chaque ingrédient.
    `scale` permet de multiplier les quantités (ex : mise à l'échelle des portions).
    """
    result = []
    items_list = recipe.get("composition") or recipe.get("ingredients", [])
    for ing in items_list:
        if isinstance(ing, dict):
            key = (
                ing.get("ingredient") or
                ing.get("ingredient_id") or
                str(ing)
            ).lower().strip()
            raw_qty  = ing.get("quantity")
            raw_unit = (ing.get("unit") or "").lower().strip()
        else:
            key      = str(ing).lower().strip()
            raw_qty  = None
            raw_unit = ""

        if not key:
            continue

        if raw_qty is not None:
            try:
                qty, unit = _normalise_unit(float(raw_qty) * scale, raw_unit)
            except (TypeError, ValueError):
                qty, unit = None, raw_unit
        else:
            qty, unit = None, raw_unit

        result.append((key, qty, unit))
    return result


def _accumulate(ing_data: dict, key: str, qty: float | None, unit: str) -> None:
    """Ajoute une entrée dans le dictionnaire d'agrégation."""
    if key not in ing_data:
        ing_data[key] = {"occurrences": 0, "units": defaultdict(float)}
    ing_data[key]["occurrences"] += 1
    if qty is not None and qty > 0:
        ing_data[key]["units"][unit] += qty


# ── API publique ──────────────────────────────────────────────────────────────

def shopping_list(meal_plan: dict, eco: bool = False) -> dict:
    """
    Génère la liste de courses pour un plan de repas hebdomadaire.

    Args:
        meal_plan : output de generate_plan() OU format frontend planToShoppingFormat()
                    Accepte les deux formats :
                      • Ancien  → {lundi: {lunch: {id, title_fr}, dinner: {...}}}
                      • Nouveau → {lundi: {lunch_0: {id, title}, lunch_1: {...}, ...}}
        eco       : marque les ingrédients réutilisés (> 2 fois)

    Returns:
        {items, estimated_cost, n_recipes, by_category}
    """
    from backend.core.data_io import load_prices, load_ingredients_dict, load_recipes, load_prices_catalog

    prices    = load_prices()
    catalog   = load_prices_catalog()
    ings_dict = load_ingredients_dict()

    # Index recettes par ID pour accès rapide
    recipe_index: dict[str, dict] = {}
    try:
        for r in load_recipes():
            rid = str(r.get("id", ""))
            if rid:
                recipe_index[rid] = r
    except Exception as e:
        logger.warning("shopping_list: impossible de charger les recettes : %s", e)

    ing_data: dict = {}
    n_recipes = 0
    seen_ids: set[str] = set()

    for day, data in meal_plan.items():
        if day == "meta":
            continue
        if not isinstance(data, dict):
            continue

        # Itère sur TOUTES les valeurs du jour (compatible ancien ET nouveau format)
        for slot_data in data.values():
            if not isinstance(slot_data, dict):
                continue
            rid = str(slot_data.get("id", "")).strip()
            if not rid or rid in seen_ids:
                continue

            recipe = recipe_index.get(rid)
            if not recipe:
                continue

            seen_ids.add(rid)
            n_recipes += 1

            # Facteur d'échelle : portions demandées vs portions de la recette
            slot_srv   = slot_data.get("servings")
            recipe_srv = recipe.get("servings")
            if slot_srv and recipe_srv and recipe_srv > 0:
                scale = float(slot_srv) / float(recipe_srv)
            else:
                scale = 1.0

            for key, qty, unit in _extract_ingredients(recipe, scale=scale):
                _accumulate(ing_data, key, qty, unit)

    return _build_result(ing_data, n_recipes, eco, prices, ings_dict, catalog)


def shopping_list_from_recipes(recipe_ids: list[str], eco: bool = False) -> dict:
    """
    Génère la liste de courses pour une sélection libre de recettes.

    Args:
        recipe_ids : liste d'IDs (strings)
        eco        : marque les ingrédients réutilisés (> 2 fois)

    Returns:
        {items, estimated_cost, n_recipes, by_category}
    """
    from backend.core.data_io import load_prices, load_ingredients_dict, load_recipes, load_prices_catalog

    if not recipe_ids:
        return {"items": [], "estimated_cost": 0.0, "n_recipes": 0, "by_category": {}}

    prices    = load_prices()
    catalog   = load_prices_catalog()
    ings_dict = load_ingredients_dict()

    recipe_index: dict[str, dict] = {}
    try:
        for r in load_recipes():
            rid = str(r.get("id", ""))
            if rid:
                recipe_index[rid] = r
    except Exception as e:
        logger.warning("shopping_list_from_recipes: impossible de charger les recettes : %s", e)

    ing_data: dict = {}
    n_recipes = 0
    seen_ids: set[str] = set()

    for rid in recipe_ids:
        rid = str(rid).strip()
        if not rid or rid in seen_ids:
            continue
        recipe = recipe_index.get(rid)
        if not recipe:
            continue
        seen_ids.add(rid)
        n_recipes += 1
        for key, qty, unit in _extract_ingredients(recipe):
            _accumulate(ing_data, key, qty, unit)

    return _build_result(ing_data, n_recipes, eco, prices, ings_dict, catalog)
