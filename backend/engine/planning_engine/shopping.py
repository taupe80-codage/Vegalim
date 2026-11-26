"""
shopping.py — Liste de courses depuis un plan ou une sélection de recettes.

API publique :
    shopping_list(meal_plan, eco)           → dict
    shopping_list_from_recipes(ids, eco)    → dict
"""
from __future__ import annotations
import logging
import math
import re
import unicodedata
from collections import defaultdict
from backend.core.data_cache import data_cached

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

def _compute_base_recipe_unit_cost(
    base_id: str,
    recipe_index: dict,
    catalog: dict,
    price_map: dict | None,
    cache: dict,
    visiting: set,
) -> tuple[float, float] | None:
    """
    Calcule le cout de production d'une recette base_* a partir de sa propre
    composition, pondere par les quantites de chaque ingredient.

    Retourne (cout_total, quantite_totale_produite) en unite "poids-
    equivalent" (grammes, avec l'approximation courante en cuisine
    1g ~= 1ml pour les liquides — suffisant pour une ESTIMATION de cout,
    pas une precision scientifique). None si le calcul est impossible
    (recette introuvable, composition vide, cycle detecte).

    Mise en cache par base_id (une meme base peut apparaitre dans plusieurs
    recettes) et protection anti-cycle (une base ne devrait jamais se
    referencer elle-meme, meme indirectement, mais on se protege quand
    meme d'une boucle infinie).
    """
    if base_id in cache:
        return cache[base_id]
    if base_id in visiting:
        return None  # cycle detecte
    recipe = recipe_index.get(base_id)
    if not recipe:
        return None

    # Même calcul que le coût de la fiche (recipe_cost) : prix au gramme de
    # chaque ingrédient, sans arrondi aux emballages (il donnait 5,15 € pour
    # 250 g de halloumi contre 2,94 € sur la fiche).
    rc = recipe_cost(recipe, catalog, recipe_index, frozenset(visiting | {base_id}))
    total_cost, total_qty = rc["total_eur"], rc["total_weight_g"]
    if total_qty <= 0 or rc["n_priced"] == 0:
        cache[base_id] = None
        return None

    # Quantité obtenue, pas la somme des ingrédients : 2 L de lait donnent
    # 250 g de halloumi (même règle que ingredient_cost_eur).
    y = recipe.get("yield_factor")
    if isinstance(y, (int, float)) and 0 < y <= 1:
        total_qty *= float(y)
    result = (total_cost, total_qty)
    cache[base_id] = result
    return result


def _compute_price(ing_key: str, qty_value: float | None, qty_unit: str | None,
                   catalog: dict, price_map: dict | None = None,
                   recipe_index: dict | None = None, base_cache: dict | None = None,
                   _visiting: set | None = None) -> dict:
    """
    Retourne le prix réel d'achat en tenant compte du conditionnement.
    {price, package_label, n_packages, price_unknown, pantry}

    price_map (backend/data/config/ingredient_price_map.json, genere par
    scripts/build_ingredient_price_map.py) resout les ids d'ingredients de
    recette (ex. "garlic_raw") vers les cles du catalogue de prix (ex.
    "garlic") quand elles ne correspondent pas directement — les deux
    vocabulaires ont evolue separement.

    recipe_index + base_cache : si ing_key n'est ni dans le catalogue ni
    dans price_map mais correspond a une recette "base_*" (sous-recette
    utilisee comme ingredient composite, ex. base_teriyaki_...), le prix
    est estime en sommant le cout de TOUS ses propres ingredients au
    prorata des quantites de sa composition (voir
    _compute_base_recipe_unit_cost). Sans recipe_index, ce repli est
    simplement ignore (comportement inchange : prix inconnu).
    """
    entry = catalog.get(ing_key)
    if not entry:
        base = ing_key.split("/")[0]
        entry = catalog.get(base)
    if not entry and price_map:
        mapped_key = price_map.get(ing_key) or price_map.get(ing_key.split("/")[0])
        if mapped_key:
            entry = catalog.get(mapped_key)

    pantry = bool(entry.get("pantry")) if entry else False

    if not entry and recipe_index and ing_key.startswith("base_") and ing_key in recipe_index:
        cache = base_cache if base_cache is not None else {}
        visiting = _visiting if _visiting is not None else set()
        unit_cost = _compute_base_recipe_unit_cost(ing_key, recipe_index, catalog, price_map, cache, visiting)
        if unit_cost is not None:
            total_cost, total_qty = unit_cost
            price_per_unit = total_cost / total_qty
            if qty_value is not None and qty_unit is not None:
                converted = _item_to_base(qty_value, qty_unit)
                needed_qty = converted[0] if converted and converted[1] in ("g", "ml") else qty_value
            else:
                needed_qty = total_qty  # pas de quantite demandee -> cout de la recette entiere
            return {
                "price": round(price_per_unit * needed_qty, 2),
                "unit_price": round(price_per_unit, 4),
                "package_label": "recette (estimation)",
                "n_packages": 0,
                "price_unknown": False,
                "pantry": False,
            }

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
    # unit_weight_g : poids d'une pièce vendue — « 100 g de persil » se compte
    # en bouquets, « 2 citrons » en grammes (même règle qu'ingredient_cost_eur).
    piece_g = entry.get("unit_weight_g")
    if needed_unit == "piece" and piece_g:
        needed_qty, needed_unit = needed_qty * piece_g, "g"

    # Trouver la combinaison optimale (coût minimal couvrant le besoin)
    best: dict | None = None
    for pkg in packages:
        conv = _pkg_to_base(pkg["qty"], pkg["unit"])
        if conv is not None and conv[1] == "piece" and needed_unit != "piece" and piece_g:
            conv = (conv[0] * piece_g, "g")
        # g ↔ ml interchangeables (approximation cuisine, comme ingredient_cost_eur)
        if conv is None or (conv[1] == "piece") != (needed_unit == "piece"):
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



# ── Rayons du magasin ─────────────────────────────────────────────────────────
# Le dictionnaire d'ingrédients n'a pas de catégorie : 56 articles sur 60 d'une
# semaine tombaient dans « Autre ». Rayon déduit de l'identifiant (motifs, dans
# l'ordre), puis de la catégorie du graphe de disponibilité ; ordre de passage
# dans un magasin.
AISLES: tuple[str, ...] = (
    "Fruits & légumes", "Herbes fraîches", "Frais : crèmerie, œufs, tofu",
    "Féculents & boulangerie", "Légumineuses", "Fruits secs, noix & graines",
    "Conserves & bocaux", "Condiments & sauces", "Épices & aromates séchés",
    "Huiles & matières grasses", "Épicerie salée", "Sucre, pâtisserie & levures",
    "Boissons & laits végétaux", "Préparations maison", "Autre",
)

_AISLE_RULES: tuple[tuple[str, str], ...] = (
    # (?:^|_)…(?:_|$) : mots entiers, sinon « eggplant » est un œuf, « butternut » une noix,
    # « garam masala » une masa, « breadcrumbs » du rhum
    (r"green_peas|snow_pea|french_bean|green_bean|broadbeans_fava_beans_(raw|boiled)_fresh|bean_sprout|edamame|broccoli|mustard_raw_leaf",
     "Fruits & légumes"),
    (r"fresh_herb|herb_leaf|^chives|parsley|coriander_raw|basil_fresh|mint_fresh|dill_weed|^tarragon|^chervil"
     r"|curry_leaf|kaffir_lime_leaf|lemon_grass|thai_basil|^sage_fresh|rosemary_fresh|thyme_fresh", "Herbes fraîches"),
    (r"coconut_milk|coconut_cream|_canned|canned_|sun_dried_tomato|tomato_dried|tomato_(paste|sauce|crushed)"
     r"|olive_(black|green)|^black_olive|^green_olive", "Conserves & bocaux"),
    (r"pastry|phyllo|(?:^|_)filo(?:_|$)", "Frais : crèmerie, œufs, tofu"),          # pâtes à tarte : rayon frais
    (r"(peanut|almond|cashew|hazelnut)_butter|tahini", "Fruits secs, noix & graines"),
    (r"vinegar", "Condiments & sauces"),
    (r"_oil|^oil|vegetable_fat|margarine", "Huiles & matières grasses"),
    (r"provolone|parmesan|pecorino|cheese|queso", "Frais : crèmerie, œufs, tofu"),
    (r"vinegar|sauce|tamari|mustard(?!.*spice)|ketchup|miso|(?:^|_)paste(?:_|$)|mirin|chutney|harissa|gochujang"
     r"|pickle|gherkin|caper|preserved_lemon|umeboshi|sriracha|mayonnaise|kimchi|sauerkraut", "Condiments & sauces"),
    (r"_milk_plant|oat_milk|almond_milk|soy(bean)?_milk|rice_milk|(?:^|_)wine(?:_|$)|beer|(?:^|_)cider(?:_|$)"
     r"|(?:^|_)rum(?:_|$)|cognac|kirsch|calvados|marsala|(?:^|_)tea(?:_|$)|coffee|matcha|kombucha|sparkling_water|roselle|hibiscus"
     r"|orange_juice", "Boissons & laits végétaux"),
    (r"tofu|tempeh|seitan|paneer|halloumi|milk|cream|butter(?!nut)|cheese|yog(h)?urt|ricotta|feta|parmesan|pecorino"
     r"|mozzarella|comte|gruyere|cheddar|mascarpone|reblochon|camembert|roquefort|tomme|fromage|queso|emmental|gouda"
     r"|cotija|provolone|gorgonzola|(?:^|_)eggs?(?:_|$)|ghee|kefir|quark", "Frais : crèmerie, œufs, tofu"),
    (r"sugar|honey|syrup|molasses|chocolate|cocoa|vanilla|baking|yeast(?!_flakes)|(?:^|_)agar(?:_|$)|gelatin"
     r"|(?:^|_)jam(?:_|$)|condensed|ladyfinger|ice_cream|meringue|marzipan", "Sucre, pâtisserie & levures"),
    (r"_spice|powder|garam|berbere|curry(?!_leaf)|paprika|cinnamon|nutmeg|cumin|turmeric|cardamom|clove|star_anise"
     r"|saffron|sumac|bay_leaf|dried_herb|herb_dried|oregano|dried_mint|chili.*dried|black_pepper|white_pepper"
     r"|allspice|fenugreek|caraway|anise|juniper|five_spice|za.?atar|ras_el_hanout|sichuan|gochugaru|amchoor",
     "Épices & aromates séchés"),
    (r"lentil|chickpea(?!_flour)|(?:^|_)beans?(?:_|$)|split_pea|fava|(?:^|_)dal(?:_|$)|urad|mung|cowpea|black_eyed"
     r"|lupin|pigeon_pea", "Légumineuses"),
    (r"(?:^|_)rice(?:_|$)|pasta|noodle|flour|bread|baguette|pita|naan|tortilla|couscous|semolina|bulgur|quinoa"
     r"|(?:^|_)oats?(?:_|$)|buckwheat|polenta|cornmeal|gnocchi|udon|soba|vermicelli|tapioca|starch|masa_harina|panko"
     r"|crouton|millet|barley|teff|wrapper|tteok|bagel|(?:^|_)bun(?:_|$)|spaetzle|cracker|rice_paper", "Féculents & boulangerie"),
    (r"(?:^|_)nuts?(?:_|$)|almond|cashew|pistachio|hazelnut|walnut|pecan|macadamia|peanut|sesame|sunflower_(raw_)?seed"
     r"|pumpkin_squash_raw_seed|pumpkin_seed|chia|flax|linseed|hemp|poppy|coconut_flesh|raisin|^dates?(?:_|$)"
     r"|dried_apricot|prune(?!_umeboshi)|cranberr|dried_fig", "Fruits secs, noix & graines"),
    (r"salt|fleur_de_sel|stock|bouillon|nutritional_yeast|seaweed|nori|kombu|wakame|dashi|spirulina", "Épicerie salée"),
    (r"_raw|lemon_juice|lime_juice|^garlic|^ginger|^onion|^shallot|^leek|_fresh$|fresh_|mushroom|plantain|avocado"
     r"|banana|apple|pear|berry|cherry|grape|melon|mango|pineapple|citrus|orange|lemon|lime|_cooked$", "Fruits & légumes"),
)

_AVAIL_AISLE = {
    "vegetable": "Fruits & légumes", "fruit": "Fruits & légumes", "herb": "Herbes fraîches",
    "dairy products": "Frais : crèmerie, œufs, tofu", "eggs": "Frais : crèmerie, œufs, tofu",
    "cereals and grains": "Féculents & boulangerie", "grain": "Féculents & boulangerie",
    "grain_cereal": "Féculents & boulangerie", "grain/flour": "Féculents & boulangerie",
    "legumes": "Légumineuses", "legume": "Légumineuses", "nut": "Fruits secs, noix & graines",
    "spice": "Épices & aromates séchés", "spice_mix": "Épices & aromates séchés", "herb_spice": "Épices & aromates séchés",
    "fats and oils": "Huiles & matières grasses", "fat": "Huiles & matières grasses",
    "condiment": "Condiments & sauces", "condiments": "Condiments & sauces",
    "sugars honeys and confectionery": "Sucre, pâtisserie & levures", "sweetener": "Sucre, pâtisserie & levures",
    "sweet": "Sucre, pâtisserie & levures", "leavening": "Sucre, pâtisserie & levures",
    "dessert": "Sucre, pâtisserie & levures", "beverage": "Boissons & laits végétaux",
    "protein": "Frais : crèmerie, œufs, tofu", "plant_protein": "Frais : crèmerie, œufs, tofu",
}


@data_cached
def _aisle_patterns():
    import re
    return [(re.compile(pat), aisle) for pat, aisle in _AISLE_RULES]


def aisle_of(iid: str) -> str:
    """Rayon d'un ingrédient de la liste de courses (AISLES)."""
    from backend.core.data_io import load_availability_graph, sub_recipe_label
    key = str(iid or "").lower()
    if sub_recipe_label(key):
        return "Préparations maison"
    for pattern, aisle in _aisle_patterns():
        if pattern.search(key):
            return aisle
    cat = ((load_availability_graph() or {}).get(key) or {}).get("category") or ""
    return _AVAIL_AISLE.get(str(cat).lower(), "Autre")


# ── Helpers partagés ──────────────────────────────────────────────────────────

def _make_resolvers(ings_dict: dict):
    """Retourne (get_name_fr, get_category_fr) pour un dict d'ingrédients."""

    from backend.core.data_io import sub_recipe_label
    from backend.services.ingredient_catalog import full_name_fr

    # Nom complet (nom de base + axe « forme ») : canonical_name_fr seul
    # affichait « Olive » pour l'huile d'olive, « Citron » pour le jus.
    def _get_name_fr(iid: str) -> str:
        for key in (iid, iid.split("/")[0]):
            d = ings_dict.get(key)
            if d and d.get("canonical_name_fr"):
                name = full_name_fr(d, key)
                return name[0].upper() + name[1:]
        label = sub_recipe_label(iid)      # « Halloumi », pas « Base halloumi 293d5e »
        if label:
            return label
        return iid.replace("_", " ").replace("/", " ").capitalize()

    def _get_category_fr(iid: str) -> str:
        return aisle_of(iid)

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


# Agrumes : le jus et le zeste viennent des mêmes fruits. Unité d'achat du fruit,
# jus (ml) et zeste (g) qu'en tire une unité ; clés du catalogue « pour le jus ».
CITRUS = {
    "lemon":  {"unit": "piece", "juice_ml": 40,  "zest_g": 6,    "juice_keys": {"lemon_juice_fresh"}},
    "lime":   {"unit": "piece", "juice_ml": 30,  "zest_g": 3,    "juice_keys": {"lime_juice_fresh_fruit"}},
    "orange": {"unit": "g",     "juice_ml": 0.4, "zest_g": 0.05, "juice_keys": {"orange_juice_fresh"}},
}
_CITRUS_OF = {k: fruit for fruit, d in CITRUS.items() for k in ({fruit} | d["juice_keys"])}


def _citrus_role(ing: str, key: str) -> str:
    if "peel" in ing or "zest" in ing:
        return "zest"
    if "juice" in ing or key in CITRUS[_CITRUS_OF[key]]["juice_keys"]:
        return "juice"
    return "whole"


def _merge_citrus(fruit: str, members: list[str], keys: dict, ing_data: dict, catalog: dict,
                  get_name_fr) -> tuple[str, dict] | None:
    """Une ligne « Citron : 5 pièces » au lieu de « Jus de citron 180 ml » + « Zeste de
    citron 16 g » (qui faisait acheter un citron de plus pour le zeste) : on zeste les
    fruits qu'on presse, donc fruits = entiers + max(jus, zestes). Le jus seul garde sa
    ligne (le catalogue le chiffre déjà en citrons) : renvoie None."""
    d = CITRUS[fruit]
    roles = {m: _citrus_role(m, keys[m]) for m in members}
    if set(roles.values()) == {"juice"} or set(roles.values()) == {"whole"}:
        return None
    unit_w = (catalog.get(fruit) or {}).get("unit_weight_g")
    whole = juice = zest = 0.0
    for m, role in roles.items():
        units = ing_data[m].get("units") or {}
        if role == "juice":
            juice += units.get("ml", 0) / d["juice_ml"]
        elif role == "zest":
            zest += units.get("g", 0) / d["zest_g"]
        elif d["unit"] == "g":
            whole += units.get("g", 0)
        else:
            pieces = sum(v for u, v in units.items() if u in ("piece", "pièce", "pièces"))
            if unit_w and units.get("g"):
                pieces += units["g"] / unit_w
            # « 1/2 citron », « 2 tranches » : sans quantité exploitable, un fruit par recette
            whole += pieces or ing_data[m]["occurrences"]
    total = whole + max(juice, zest)
    if total <= 0:   # zeste ou jus sans quantité : au moins un fruit
        total = 1 if d["unit"] == "piece" else 200
    qty = math.ceil(total - 1e-6) if d["unit"] == "piece" else round(total)
    main = next(m for m in members if roles[m] != "juice")
    # détail : jus et zeste, un seul « jus d'orange » même s'il vient de deux ids
    detail: dict[str, dict] = {}
    for m in members:
        if roles[m] == "whole":
            continue
        name = get_name_fr(m)
        row = detail.setdefault(name.lower(), {"ingredient": m, "name_fr": name, "units": defaultdict(float)})
        for u, v in (ing_data[m].get("units") or {}).items():
            row["units"][u] += v
    return main, {
        "occurrences": sum(ing_data[m]["occurrences"] for m in members),
        "units": {d["unit"]: qty},
        "name_fr": (catalog.get(fruit) or {}).get("name_fr") or get_name_fr(main),
        "merged": [{"ingredient": r["ingredient"], "name_fr": r["name_fr"],
                    "qty_str": _build_qty_str(r["units"])} for r in detail.values()],
    }


# Parties d'un produit (on achète l'œuf, pas le blanc) : jamais le nom de la ligne
_PART_NAME = re.compile(r"^(blancs?|jaunes?|zestes?|jus|écorces?) d", re.I)


def _norm_name(name: str) -> str:
    """« Œufs » ≈ « Œuf », « Oignons » ≈ « oignon » : minuscules, sans accents, sans
    parenthèse ni pluriel."""
    s = re.sub(r"\s*\(.*?\)", "", name).lower().replace("œ", "oe")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if not unicodedata.combining(c))
    return " ".join(re.sub(r"[sx]$", "", w) for w in re.findall(r"[a-z]+", s))


def _main_member(key: str, members: list[str], ing_data: dict, catalog: dict,
                 get_name_fr) -> tuple[str, str | None]:
    """Ligne principale d'un produit fusionné et, si besoin, son nom.
    1. l'ingrédient qui porte le nom du produit (« Œuf » pour « Œufs ») ;
    2. sinon la plus grosse quantité, hors parties (blanc, jaune, zeste, jus) ;
    3. que des parties : la plus grosse, nommée d'après le produit (« Œufs »)."""
    def weight(i):
        return (-sum((ing_data[i].get("units") or {}).get(u, 0) for u in ("g", "ml")),
                -ing_data[i]["occurrences"], len(i))
    product = (catalog.get(key) or {}).get("name_fr") or ""
    target = _norm_name(product)
    named = sorted((m for m in members if _norm_name(get_name_fr(m)) == target), key=weight)
    if named:
        return named[0], None
    whole = sorted((m for m in members if not _PART_NAME.match(get_name_fr(m))), key=weight)
    if whole:
        return whole[0], None
    return sorted(members, key=weight)[0], re.sub(r"\s*\(.*?\)", "", product).strip() or None


def _merge_same_product(ing_data: dict, catalog: dict, get_name_fr) -> dict:
    """Une ligne par produit acheté : les ingrédients qui renvoient à la même entrée
    du catalogue (œuf et jaune d'œuf, oignon et oignon jaune…) comptaient chacun
    leurs emballages. L'eau du robinet n'est pas un achat : retirée.

    La ligne fusionnée garde l'id de la plus grosse quantité ; « merged » détaille les autres.
    Agrumes : jus, zeste et fruit entier sur une ligne de fruits entiers (_merge_citrus)."""
    from backend.core.data_io import resolve_catalog_key
    groups: dict[str, list[str]] = defaultdict(list)
    keys: dict[str, str] = {}
    out: dict = {}
    for ing in ing_data:
        if ing.startswith("base_"):
            out[ing] = ing_data[ing]
            continue
        key = resolve_catalog_key(ing, catalog)
        if key == "water":
            continue
        if key:
            keys[ing] = key
            groups[_CITRUS_OF.get(key, key)].append(ing)
        else:
            out[ing] = ing_data[ing]
    for key, members in groups.items():
        if key in CITRUS:
            merged = _merge_citrus(key, members, keys, ing_data, catalog, get_name_fr)
            if merged:
                out[merged[0]] = merged[1]
                continue
        if len(members) == 1:
            out[members[0]] = ing_data[members[0]]
            continue
        # ligne principale : « Œuf », pas « Blanc d'œuf » même quand le blanc pèse plus
        members.sort(key=lambda i: (-sum((ing_data[i].get("units") or {}).get(u, 0) for u in ("g", "ml")),
                                    -ing_data[i]["occurrences"], len(i)))
        main, name = _main_member(key, members, ing_data, catalog, get_name_fr)
        units: dict = defaultdict(float)
        for m in members:
            for u, v in (ing_data[m].get("units") or {}).items():
                units[u] += v
        out[main] = {
            "occurrences": sum(ing_data[m]["occurrences"] for m in members),
            "units": units,
            # nommée d'après le produit : toutes les parties en détail
            "merged": [{"ingredient": m, "name_fr": get_name_fr(m),
                        "qty_str": _build_qty_str(ing_data[m].get("units", {}))}
                       for m in members if name or m != main],
        }
        if name:
            out[main]["name_fr"] = name
    return out


def _build_result(
    ing_data: dict,
    n_recipes: int,
    eco: bool,
    prices: dict,
    ings_dict: dict,
    catalog: dict | None = None,
    price_map: dict | None = None,
    recipe_index: dict | None = None,
) -> dict:
    """
    Construit le dict de sortie standard.

    ing_data : {ingredient_key: {"occurrences": int, "units": {unit: total_amount}}}

    recipe_index permet d'estimer le prix des ingredients "base_*" (sous-
    recettes utilisees comme ingredient composite) a partir de leur propre
    composition — voir _compute_base_recipe_unit_cost. base_cost_cache est
    partage entre tous les items de cet appel pour ne calculer chaque base
    qu'une seule fois meme si elle est utilisee dans plusieurs recettes.
    """
    get_name_fr, get_category_fr = _make_resolvers(ings_dict)
    if catalog is None:
        catalog = {}
    ing_data = _merge_same_product(ing_data, catalog, get_name_fr)

    items: list[dict] = []
    total_eur = 0.0
    n_unknown = 0
    base_cost_cache: dict = {}

    for ing, data in sorted(ing_data.items(), key=lambda x: -x[1]["occurrences"]):
        count   = data["occurrences"]
        qty_str = _build_qty_str(data.get("units", {}))

        units_map = data.get("units", {})
        _order = ["g", "ml"] + [u for u in units_map if u not in ("g", "ml")]
        _punit = next((u for u in _order if u in units_map), None)
        qty_value = round(units_map[_punit], 2) if _punit else None

        price_info = _compute_price(
            ing, qty_value, _punit, catalog, price_map,
            recipe_index=recipe_index, base_cache=base_cost_cache,
        )
        if price_info["price_unknown"]:
            n_unknown += 1

        item: dict = {
            "ingredient":    ing,
            "name_fr":       data.get("name_fr") or get_name_fr(ing),
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
        if data.get("merged"):
            item["merged"] = data["merged"]
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
            **({"merged": item["merged"]} if item.get("merged") else {}),
        })

    def _cat_sort(kv):
        k = kv[0]
        return (AISLES.index(k) if k in AISLES else len(AISLES), k)

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
    from backend.core.data_io import (
        load_prices, load_ingredients_dict, load_recipes,
        load_prices_catalog, load_ingredient_price_map,
    )

    prices    = load_prices()
    catalog   = load_prices_catalog()
    price_map = load_ingredient_price_map()
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

    # Chaque repas planifié compte : une recette prévue lundi et jeudi
    # demande deux fois ses ingrédients (elle n'était comptée qu'une fois).
    ing_data: dict = {}
    n_recipes = 0

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
            if not rid:
                continue

            recipe = recipe_index.get(rid)
            if not recipe:
                continue
            # Recette ajoutée au planning dans sa version vegan ou dans la version
            # modifiée par le membre : on achète les substituts (beurre végétal,
            # tofu soyeux, courgette…) et les quantités changées, pas l'original
            from backend.services.recipe_edits import plan_entry_recipe
            recipe = plan_entry_recipe(recipe, slot_data)

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

    return _build_result(ing_data, n_recipes, eco, prices, ings_dict, catalog, price_map, recipe_index)


def shopping_list_from_recipes(recipe_ids: list[str], eco: bool = False) -> dict:
    """
    Génère la liste de courses pour une sélection libre de recettes.

    Args:
        recipe_ids : liste d'IDs (strings)
        eco        : marque les ingrédients réutilisés (> 2 fois)

    Returns:
        {items, estimated_cost, n_recipes, by_category}
    """
    from backend.core.data_io import (
        load_prices, load_ingredients_dict, load_recipes,
        load_prices_catalog, load_ingredient_price_map,
    )

    if not recipe_ids:
        return {"items": [], "estimated_cost": 0.0, "n_recipes": 0, "by_category": {}}

    prices    = load_prices()
    catalog   = load_prices_catalog()
    price_map = load_ingredient_price_map()
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

    return _build_result(ing_data, n_recipes, eco, prices, ings_dict, catalog, price_map, recipe_index)


# ── Coût consommé d'une recette (scoring, budget) ────────────────────────────
#
# Différent de la liste de courses : on facture la quantité UTILISÉE au prix
# unitaire du conditionnement le plus avantageux, pas des paquets entiers
# (5 g de sel ≠ un paquet de 1 kg). Sert au score coût et à estimate_price().

def ingredient_cost_eur(ing_key: str, qty: float, unit: str, catalog: dict,
                        recipe_index: dict | None = None,
                        _visiting: frozenset = frozenset()) -> float | None:
    """Coût en € de `qty` `unit` d'un ingrédient, ou None si non chiffrable."""
    from backend.core.data_io import resolve_catalog_key

    try:
        n_qty, n_unit = _normalise_unit(float(qty), (unit or "").lower().strip())
    except (TypeError, ValueError):
        return None
    base = _item_to_base(n_qty, n_unit)
    if base is None or base[0] <= 0:
        return None
    needed, needed_unit = base

    key = str(ing_key).lower().strip()
    if key.startswith("base_") and recipe_index and key in recipe_index and key not in _visiting:
        if needed_unit == "piece":
            return None
        sub = recipe_cost(recipe_index[key], catalog, recipe_index, _visiting | {key})
        if not sub["total_weight_g"] or sub["n_priced"] == 0:
            return None
        # Coût au poids OBTENU, pas au poids des ingrédients : 2 L de lait donnent
        # 250 g de halloumi (yield_factor 0,12, comme le registre nutritionnel de
        # build_derived_base_registry). Sans cela, 250 g coûtaient 0,35 € au lieu de 2,94 €.
        y = recipe_index[key].get("yield_factor")
        yield_factor = float(y) if isinstance(y, (int, float)) and 0 < y <= 1 else 1.0
        return sub["total_eur"] / (sub["total_weight_g"] * yield_factor) * needed   # 1 g ≈ 1 ml

    entry_key = resolve_catalog_key(key, catalog)
    if not entry_key:
        return None
    entry = catalog[entry_key]
    # unit_weight_g : poids moyen d'une pièce vendue (ail, œuf, cube de bouillon…)
    # — permet de chiffrer « 15 g d'ail » quand le catalogue vend des têtes.
    piece_g = entry.get("unit_weight_g")
    if needed_unit == "piece" and piece_g:
        needed, needed_unit = needed * piece_g, "g"
    best = None
    for pkg in entry.get("packages", []):
        conv = _pkg_to_base(pkg.get("qty") or 0, pkg.get("unit") or "")
        if not conv or conv[0] <= 0:
            continue
        if conv[1] == "piece" and needed_unit != "piece" and piece_g:
            conv = (conv[0] * piece_g, "g")
        # g ↔ ml interchangeables (approximation cuisine), pièce ≠ poids
        if (conv[1] == "piece") != (needed_unit == "piece"):
            continue
        per_unit = pkg["price"] / conv[0]
        best = per_unit if best is None else min(best, per_unit)
    return None if best is None else best * needed


def recipe_cost(recipe: dict, catalog: dict | None = None,
                recipe_index: dict | None = None,
                _visiting: frozenset = frozenset()) -> dict:
    """
    Coût consommé d'une recette.

    Returns:
        {total_eur, per_portion_eur, n_priced, n_unknown, unknown, total_weight_g, details}
        Les lignes sans quantité numérique ou en suggestion de service sont ignorées.
        `unknown` : ids des ingrédients sans prix, y compris ceux des sous-recettes
        (une sous-recette en partie chiffrée compte ses ingrédients connus seulement).
    """
    from backend.core.data_io import load_prices_catalog, load_recipes

    if catalog is None:
        catalog = load_prices_catalog()
    if recipe_index is None:
        recipe_index = {str(r.get("id")): r for r in load_recipes()}

    total = weight = 0.0
    n_priced = n_unknown = 0
    details = []
    unknown: list[str] = []
    for item in recipe.get("composition", []) or []:
        if not isinstance(item, dict) or (item.get("meta") or {}).get("role") == "serving_suggestion":
            continue
        qty = item.get("quantity")
        if not isinstance(qty, (int, float)) or qty <= 0:
            continue
        key = item.get("ingredient") or item.get("ingredient_id") or ""
        unit = item.get("unit") or "g"
        norm = _item_to_base(*_normalise_unit(float(qty), unit.lower().strip()))
        if norm and norm[1] in ("g", "ml"):
            weight += norm[0]
        cost = ingredient_cost_eur(key, qty, unit, catalog, recipe_index, _visiting)
        if key.startswith("base_") and key in recipe_index and key not in _visiting:
            sub_unknown = recipe_cost(recipe_index[key], catalog, recipe_index,
                                      _visiting | {key})["unknown"]
            unknown.extend(i for i in sub_unknown if i not in unknown)
        if cost is None:
            n_unknown += 1
            if key not in unknown and not (key.startswith("base_") and key in recipe_index):
                unknown.append(key)
            continue
        n_priced += 1
        total += cost
        details.append({"ingredient": key, "cost_eur": round(cost, 3)})

    servings = max(1, int(recipe.get("servings") or 4))
    details.sort(key=lambda x: -x["cost_eur"])
    return {
        "total_eur":       round(total, 2),
        "per_portion_eur": round(total / servings, 2),
        "n_priced":        n_priced,
        "n_unknown":       n_unknown,
        "unknown":         unknown,
        "total_weight_g":  round(weight, 1),
        "details":         details,
    }
