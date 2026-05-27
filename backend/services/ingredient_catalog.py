"""
ingredient_catalog.py — Catalogue unifié des ingrédients pour le frigo.

Fusionne ingredients_dictionary.json (510 entrées avec name_fr) et les IDs
réellement utilisés dans les recettes (510 IDs uniques, seulement 267 en commun).

Pour les 243 IDs manquants dans le dict (ex: tomato/fresh, butter/dairy),
génère automatiquement un name_fr et une catégorie par lookup hiérarchique.

API publique :
    search(q, limit)       → liste d'ingrédients triés par pertinence + popularité
    get_frigo_groups()     → catégories avec bases + variantes pour les chips
    get_catalog()          → catalogue complet (lazy, mis en cache)
"""
from __future__ import annotations

import logging
import threading
from functools import lru_cache
from collections import Counter, defaultdict
from typing import Optional

logger = logging.getLogger(__name__)

# ── Translations variants ─────────────────────────────────────────────────────
# Parties après '/' ou '_' dans les IDs hiérarchiques → libellé FR court
_VARIANT_FR: dict[str, str] = {
    # États / préparation
    "fresh":       "fraîche",
    "raw":         "crue",
    "canned":      "en conserve",
    "dried":       "séché",
    "ground":      "moulu",
    "whole":       "entier",
    "heavy":       "épaisse",
    "light":       "légère",
    "firm":        "ferme",
    "silken":      "soyeux",
    "smoked":      "fumé",
    "roasted":     "grillé",
    "fermented":   "fermenté",
    "toasted":     "grillé",
    # Qualificatifs génériques à ignorer
    "dairy":       "",   # beurre/dairy → juste "beurre"
    "default":     "",   # xxx/default → juste la base
    "animal":      "",   # cream/animal → juste "crème"
    "plant":       "végétal",
    # Couleurs
    "white":       "blanc",
    "brown":       "brun",
    "red":         "rouge",
    "green":       "verte",
    "purple":      "violet",
    "black":       "noir",
    "yellow":      "jaune",
    # Riz
    "long_grain":  "long grain",
    "short_grain": "grain rond",
    "round_grain": "grain rond",
    "basmati":     "basmati",
    # Champignons
    "button":      "de Paris",
    "oyster":      "pleurote",
    "shiitake":    "shiitake",
    # Agrumes (quand citrus est la base)
    "lemon":       "citron",
    "lime":        "citron vert",
    "lemon_juice": "jus de citron",
    "lime_juice":  "jus de citron vert",
    "orange":      "orange",
    "grapefruit":  "pamplemousse",
    # Huiles
    "olive":       "d'olive",
    "neutral":     "neutre",
    "coconut":     "de coco",
    # Laits végétaux
    "oat":         "d'avoine",
    "almond":      "d'amande",
    "soy":         "de soja",
    "cashew":      "de cajou",
    # Vinaigres
    "rice_wine":   "de riz",
    "rice":        "de riz",
    "white_wine":  "de vin blanc",
    "red_wine":    "de vin rouge",
    "apple_cider": "de cidre",
    "balsamic":    "balsamique",
    # Graines
    "seeds":       "graines",
    # Spring onion
    "spring":      "ciboule",
}

# IDs de base non présents dans le dict → name_fr + category manuels
# Utilisé aussi bien dans _auto_name_fr (pour les IDs avec slash)
# que dans DIRECT_FR_BASE (pour les IDs sans slash non couverts)
_BASE_OVERRIDES: dict[str, tuple[str, str]] = {
    "citrus":       ("agrume",        "fruit"),
    "milk_animal":  ("lait",          "dairy"),
    "cream_animal": ("crème",         "dairy"),
    "milk_plant":   ("lait végétal",  "dairy_alternative"),
    "cream_plant":  ("crème végétale","dairy_alternative"),
    "oil":          ("huile",         "fat"),
    "vinegar":      ("vinaigre",      "condiment"),
}

# IDs sans '/' non couverts → traduction directe (les plus fréquents)
_DIRECT_FR: dict[str, tuple[str, str]] = {
    "soy_sauce":          ("sauce soja",          "condiment"),
    "vegetable_broth":    ("bouillon de légumes",  "liquid"),
    "all_purpose_flour":  ("farine",               "grain"),
    "vegan_butter":       ("beurre végétal",       "fat"),
    "chili_pepper":       ("piment",               "herb_spice"),
    "coconut_milk":       ("lait de coco",         "liquid"),
    "sesame_seeds":       ("graines de sésame",    "nut_seed"),
    "green_lentils":      ("lentilles vertes",     "legume"),
    "dijon_mustard":      ("moutarde de Dijon",    "condiment"),
    "white_bean":         ("haricots blancs",      "legume"),
    "red_lentils":        ("lentilles corail",     "legume"),
    "black_bean":         ("haricots noirs",       "legume"),
    "vegan_cheese":       ("fromage végétal",      "dairy_alternative"),
    "tomato_sauce":       ("coulis de tomate",     "condiment"),
    "cane_sugar":         ("sucre de canne",       "sweetener"),
    "shallot":            ("échalote",             "vegetable"),
    "kidney_bean":        ("haricots rouges",      "legume"),
    "coconut_sugar":      ("sucre de coco",        "sweetener"),
    "vegan_parmesan":     ("parmesan végétal",     "dairy_alternative"),
    "bread_flour":        ("farine à pain",        "grain"),
    "silken_tofu":        ("tofu soyeux",          "protein_plant"),
    "vegan_feta":         ("feta végétale",        "dairy_alternative"),
    "cornstarch":         ("maïzena",              "grain"),
    "rice_noodles":       ("nouilles de riz",      "grain"),
    "cashew_cream":       ("crème de cajou",       "dairy_alternative"),
    "filo_pastry":        ("pâte filo",            "grain"),
    "mustard_seeds":      ("graines de moutarde",  "herb_spice"),
    "peanut_oil":         ("huile d'arachide",     "fat"),
    "egg_yolk":           ("jaune d'œuf",          "egg"),
    "cassava_flour":      ("farine de manioc",     "grain"),
    "rolled_oats":        ("flocons d'avoine",     "grain"),
    "chickpea_flour":     ("farine de pois chiches","grain"),
    "sushi_rice":         ("riz à sushi",          "grain"),
    "cream_cheese":       ("fromage frais",        "dairy"),
    "butternut_squash":   ("courge butternut",     "vegetable"),
    "tomato_paste":       ("concentré de tomate",  "vegetable"),
    "buckwheat_flour":    ("farine de sarrasin",   "grain"),
    "puff_pastry":        ("pâte feuilletée",      "grain"),
    "porcini":            ("cèpes",                "vegetable"),
    "cacao_powder":       ("cacao en poudre",      "sweetener"),
    "herbes_de_provence": ("herbes de Provence",   "herb_spice"),
    "split_peas":         ("pois cassés",          "legume"),
    "ground_ginger":      ("gingembre moulu",      "herb_spice"),
    "applesauce":         ("compote de pommes",    "fruit"),
    "napa_cabbage":       ("chou chinois",         "vegetable"),
    "rye_flour":          ("farine de seigle",     "grain"),
    "powdered_sugar":     ("sucre glace",          "sweetener"),
    "almond_butter":      ("beurre d'amande",      "nut_seed"),
    "agar_agar":          ("agar-agar",            "additive"),
    "black_olive":        ("olive noire",          "vegetable"),
    "coconut_cream":      ("crème de coco",        "liquid"),
    "goat_cheese":        ("fromage de chèvre",    "dairy"),
    "mascarpone":         ("mascarpone",           "dairy"),
    "almond_flour":       ("farine d'amande",      "nut_seed"),
    "ricotta_salata":     ("ricotta salata",       "dairy"),
    "sun_dried_tomato":   ("tomate séchée",        "vegetable"),
    "sunflower_seeds":    ("graines de tournesol", "nut_seed"),
    "egg_white":          ("blanc d'œuf",          "egg"),
    "canola_oil":         ("huile de colza",       "fat"),
    "gherkin":            ("cornichon",            "vegetable"),
    "oyster_mushroom":    ("pleurote",             "vegetable"),
    "curry_powder":       ("curry en poudre",      "herb_spice"),
    "white_pepper":       ("poivre blanc",         "herb_spice"),
    "clove":              ("clou de girofle",      "herb_spice"),
    "puy_lentil":         ("lentilles du Puy",     "legume"),
    "matcha":             ("matcha",               "herb_spice"),
    "peas":               ("petits pois",          "vegetable"),
    "espelette_pepper":   ("piment d'Espelette",   "herb_spice"),
    "chanterelle":        ("girolles",             "vegetable"),
    "seaweed":            ("algues",               "vegetable"),
    "mixed_salad":        ("salade mélangée",      "vegetable"),
    "lamb_lettuce":       ("mâche",                "vegetable"),
    "chinese_broccoli":   ("brocoli chinois",      "vegetable"),
    "napa_cabbage":       ("chou napa",            "vegetable"),
    "pita_bread":         ("pain pita",            "grain"),
    "sourdough_bread":    ("pain au levain",       "grain"),
    "whole_grain_bread":  ("pain complet",         "grain"),
    "granola":            ("granola",              "grain"),
    "beluga_lentil":      ("lentilles beluga",     "legume"),
    "brown_lentils":      ("lentilles brunes",     "legume"),
    "yellow_lentils":     ("lentilles jaunes",     "legume"),
    "black_eyed_pea":     ("doliques à œil noir",  "legume"),
    "flageolet_bean":     ("flageolets",           "legume"),
    "dried_chickpeas":    ("pois chiches secs",    "legume"),
    "hemp_seeds":         ("graines de chanvre",   "nut_seed"),
    "ground_flaxseed":    ("graines de lin moulues","nut_seed"),
    "black_sesame_seeds": ("graines de sésame noir","nut_seed"),
    "sliced_almond":      ("amandes effilées",     "nut_seed"),
    "orange_blossom_water":("eau de fleur d'oranger","condiment"),
    "pearl_onion":        ("oignon grelot",        "vegetable"),
    "vegan_mayonnaise":   ("mayonnaise végétale",  "condiment"),
    "basil_pesto":        ("pesto au basilic",     "condiment"),
    "miso_soup_base":     ("base miso",            "fermented"),
    "cashew_ricotta":     ("ricotta de cajou",     "dairy_alternative"),
    "vegetarian_dashi":   ("dashi végétarien",     "liquid"),
    "desiccated_coconut": ("noix de coco râpée",   "nut_seed"),
    "red_bean_paste":     ("pâte de haricot rouge","condiment"),
    "roasted_chickpea":   ("pois chiches grillés", "legume"),
    "cooked_rice":        ("riz cuit",             "grain"),
    "rice_cake":          ("galette de riz",       "grain"),
    "pearl_sugar":        ("sucre perlé",          "sweetener"),
    "vanilla_sugar":      ("sucre vanillé",        "sweetener"),
    "mixed_berries":      ("fruits rouges mélangés","fruit"),
    "frozen_banana":      ("banane congelée",      "fruit"),
    "dried_cranberry":    ("canneberge séchée",    "fruit"),
    "acai_puree":         ("purée d'açaï",         "fruit"),
    "strawberry_jam":     ("confiture de fraise",  "condiment"),
    "cherry_jam":         ("confiture de cerise",  "condiment"),
    "strawberry_coulis":  ("coulis de fraise",     "condiment"),
    "pomegranate_molasses":("mélasse de grenade",  "condiment"),
    "tomato_ketchup":     ("ketchup",              "condiment"),
    "black_bean_sauce":   ("sauce aux haricots noirs","condiment"),
    "berbere_sauce":      ("sauce berbéré",        "condiment"),
    "okonomiyaki_sauce":  ("sauce okonomiyaki",    "condiment"),
    "five_spice":         ("cinq-épices",          "herb_spice"),
    "bouquet_garni":      ("bouquet garni",        "herb_spice"),
    "anise_seeds":        ("graines d'anis",       "herb_spice"),
    "espresso":           ("expresso",             "liquid"),
    "orange_juice":       ("jus d'orange",         "liquid"),
    "apple_juice":        ("jus de pomme",         "liquid"),
    "white_wine":         ("vin blanc",            "liquid"),
    "red_wine":           ("vin rouge",            "liquid"),
    "cooking_water":      ("eau de cuisson",       "liquid"),
    "frying_oil":         ("huile de friture",     "fat"),
    "walnut_oil":         ("huile de noix",        "fat"),
    "hazelnut_oil":       ("huile de noisette",    "fat"),
    "truffle_oil":        ("huile de truffe",      "fat"),
    "salted_butter":      ("beurre salé",          "fat"),
    "vegan_cheddar":      ("cheddar végétal",      "dairy_alternative"),
    "salted_butter_caramel":("caramel au beurre salé","sweetener"),
    "dark_chocolate_chips":("pépites de chocolat noir","sweetener"),
    "chocolate_chips":    ("pépites de chocolat",  "sweetener"),
    "ladyfinger":         ("biscuit à la cuillère","grain"),
    "digestive_biscuit":  ("biscuit digestif",     "grain"),
    "crouton":            ("croûton",              "grain"),
    "short_pasta":        ("pâtes courtes",        "grain"),
    "lasagna_sheet":      ("feuille de lasagne",   "grain"),
    "vermicelli":         ("vermicelles",          "grain"),
    "bagel":              ("bagel",                "grain"),
    "wide_rice_noodles":  ("nouilles de riz larges","grain"),
    "glutinous_rice_flour":("farine de riz gluant","grain"),
    "teff_flour":         ("farine de teff",       "grain"),
    "rye_flour":          ("farine de seigle",     "grain"),
    "plum":               ("prune",                "fruit"),
    "rhubarb":            ("rhubarbe",             "fruit"),
    "kaffir_lime":        ("combava",              "fruit"),
    "sprouts":            ("graines germées",      "vegetable"),
    "zucchini_blossom":   ("fleur de courgette",   "vegetable"),
    "napa_cabbage":       ("chou napa",            "vegetable"),
    "curly_endive":       ("chicorée frisée",      "vegetable"),
    "candied_fruit":      ("fruits confits",       "fruit"),
    "roquefort":          ("roquefort",            "dairy"),
    "fresh_tome_cheese":  ("tomme fraîche",        "dairy"),
    "vegan_feta":         ("feta végétale",        "dairy_alternative"),
    "ricotta_salata":     ("ricotta salata",       "dairy"),
    "pecorino_romano":    ("pecorino romano",      "dairy"),
    "wakame_dried":       ("wakamé séché",         "vegetable"),
    "black_salt":         ("sel noir (kala namak)","condiment"),
    "rose_water":         ("eau de rose",          "condiment"),
    "kirsch":             ("kirsch",               "condiment"),
    "cognac":             ("cognac",               "condiment"),
    "marsala":            ("marsala",              "condiment"),
    "calvados":           ("calvados",             "condiment"),
    "amarillo_chili":     ("piment amarillo",      "herb_spice"),
    "thai_chili":         ("piment thaï",          "herb_spice"),
    "juniper_berry":      ("baie de genièvre",     "herb_spice"),
    "chervil":            ("cerfeuil",             "herb_spice"),
    "sourdough_starter":  ("levain",               "leavening"),
    "pie_dough":          ("pâte brisée",          "grain"),
    "dried_peas":         ("pois secs",            "legume"),
    "sauce":              ("sauce",                "condiment"),
    "legume":             ("légumineuse",          "legume"),
}

# ── Catégories frigo (pour les chips groupés) ─────────────────────────────────
# Ordre d'affichage + IDs de base (sans variante) qui y appartiennent
FRIGO_CATEGORIES: list[dict] = [
    {
        "id":    "grain",
        "label": "Féculents",
        "bases": [
            "pasta", "rice", "potato", "bread", "quinoa",
            "green_lentils", "red_lentils", "chickpea",
            "cornstarch", "rolled_oats", "bread_flour",
            "all_purpose_flour", "buckwheat_flour", "rye_flour",
            "chickpea_flour", "sushi_rice",
        ],
    },
    {
        "id":    "vegetable",
        "label": "Légumes",
        "bases": [
            "tomato", "onion", "garlic", "carrot", "zucchini",
            "spinach", "eggplant", "bell_pepper", "mushroom",
            "shallot", "leek", "celery", "cucumber", "cabbage",
            "broccoli", "cauliflower", "pumpkin", "sweet_potato",
            "chili_pepper", "butternut_squash", "porcini",
            "oyster_mushroom", "tomato_paste", "tomato_sauce",
            "sun_dried_tomato", "peas",
        ],
    },
    {
        "id":    "legume",
        "label": "Légumineuses",
        "bases": [
            "chickpea", "green_lentils", "red_lentils", "white_bean",
            "black_bean", "kidney_bean", "lentil", "split_peas",
            "puy_lentil", "beluga_lentil", "brown_lentils",
            "yellow_lentils", "flageolet_bean",
        ],
    },
    {
        "id":    "protein",
        "label": "Protéines",
        "bases": [
            "egg", "tofu", "tempeh", "feta", "mozzarella",
            "silken_tofu", "vegan_cheese", "vegan_feta",
            "goat_cheese", "cream_cheese", "ricotta",
        ],
    },
    {
        "id":    "dairy",
        "label": "Laitiers",
        "bases": [
            "milk", "milk_animal", "cream", "cream_animal",
            "yogurt", "parmesan", "butter",
            "goat_cheese", "mozzarella", "feta",
            "milk_plant", "vegan_butter", "coconut_milk", "coconut_cream",
        ],
    },
    {
        "id":    "fat",
        "label": "Huiles & graisses",
        "bases": [
            "olive_oil", "oil", "butter", "vegan_butter",
            "sesame_oil", "coconut_oil", "peanut_oil",
            "canola_oil", "frying_oil",
        ],
    },
    {
        "id":    "condiment",
        "label": "Condiments & sauces",
        "bases": [
            "soy_sauce", "vinegar", "lemon", "citrus",
            "dijon_mustard", "tomato_sauce", "tomato_paste",
            "olive_oil", "sesame_oil", "tahini",
            "vegan_mayonnaise", "basil_pesto", "tomato_ketchup",
        ],
    },
    {
        "id":    "herb_spice",
        "label": "Épices & herbes",
        "bases": [
            "cumin", "turmeric", "ginger", "coriander", "garlic",
            "onion", "pepper", "chili_pepper", "paprika",
            "cinnamon", "cardamom", "clove", "five_spice",
            "curry_powder", "herbes_de_provence", "thyme",
            "rosemary", "basil", "parsley", "mint",
            "oregano", "bay_leaf", "mustard_seeds",
            "ground_ginger", "espelette_pepper", "white_pepper",
        ],
    },
    {
        "id":    "sweetener",
        "label": "Sucrants",
        "bases": [
            "sugar", "honey", "maple_syrup", "agave_syrup",
            "cane_sugar", "coconut_sugar", "powdered_sugar",
            "vanilla_sugar", "cacao_powder",
        ],
    },
    {
        "id":    "nut_seed",
        "label": "Noix & graines",
        "bases": [
            "almond", "walnut", "cashew", "sesame_seeds",
            "sunflower_seeds", "hemp_seeds", "ground_flaxseed",
            "black_sesame_seeds", "sliced_almond", "desiccated_coconut",
            "peanut", "hazelnut", "pine_nut",
        ],
    },
]

# ── Cache ─────────────────────────────────────────────────────────────────────
_catalog_cache: list[dict] | None = None
_catalog_lock  = threading.Lock()


def _humanize(iid: str) -> str:
    """Fallback: humanise un ID en libellé lisible (si aucune traduction trouvée)."""
    return iid.replace("_", " ").replace("/", " - ")


def _resolve_base(base_id: str, d: dict) -> tuple[str, str]:
    """
    Résout le nom FR et la catégorie d'un ID de base (sans slash).
    Cherche dans _DIRECT_FR, puis _BASE_OVERRIDES, puis le dict, puis humanize.
    """
    if base_id in _DIRECT_FR:
        return _DIRECT_FR[base_id]
    if base_id in _BASE_OVERRIDES:
        return _BASE_OVERRIDES[base_id]
    if base_id in d:
        return d[base_id].get("name_fr", _humanize(base_id)), d[base_id].get("category", "")
    return _humanize(base_id), ""


def _auto_name_fr(iid: str, d: dict) -> tuple[str, str]:
    """
    Génère (name_fr, category) pour un ID absent du dict.
    Stratégie : lookup du base + traduction du variant.
    """
    # Cherche d'abord dans les surcharges directes
    if iid in _DIRECT_FR:
        return _DIRECT_FR[iid]

    if "/" in iid:
        base, *rest = iid.split("/")
        variant_key = "/".join(rest)  # ex: 'long_grain', 'lemon_juice'

        base_fr, cat = _resolve_base(base, d)

        # Translate variant
        variant_fr = _VARIANT_FR.get(variant_key, "")
        if not variant_fr:
            # essai avec la dernière partie si compound (ex: lemon_juice → déjà dans dict)
            last = variant_key.split("_")[-1]
            variant_fr = _VARIANT_FR.get(last, variant_key.replace("_", " "))

        if variant_fr:
            name_fr = f"{base_fr} {variant_fr}".strip()
        else:
            name_fr = base_fr

        return name_fr, cat

    # Pas de slash — utilise _resolve_base (couvre _BASE_OVERRIDES pour milk_animal etc.)
    return _resolve_base(iid, d)


def _build_catalog() -> list[dict]:
    """
    Construit le catalogue unifié.
    Retourne une liste de dicts triée par recipe_count décroissant.
    """
    from backend.core.data_io import load_ingredients_dict, load_recipes

    d       = load_ingredients_dict()    # 510 entrées avec name_fr
    recipes = load_recipes()             # 845 recettes

    # Compte d'utilisation dans les recettes
    counts: Counter[str] = Counter()
    for r in recipes:
        items = r.get("composition") or r.get("ingredients", [])
        for ing in items:
            if isinstance(ing, dict):
                iid = ing.get("ingredient") or ing.get("ingredient_id", "")
            else:
                iid = str(ing)
            if iid:
                counts[iid.lower()] += 1

    catalog: list[dict] = []

    all_ids = set(counts.keys()) | set(d.keys())

    for iid in all_ids:
        recipe_count = counts.get(iid, 0)

        if iid in d:
            entry = d[iid]
            name_fr  = entry.get("name_fr", _humanize(iid))
            name_en  = entry.get("name_en", iid)
            category = entry.get("category", "")
            tokens   = entry.get("search_tokens", [])
        else:
            name_fr, category = _auto_name_fr(iid, d)
            name_en  = iid.replace("_", " ").replace("/", " ")
            tokens   = []

        # Base ID (avant le premier '/')
        base = iid.split("/")[0] if "/" in iid else iid

        catalog.append({
            "id":           iid,
            "name_fr":      name_fr,
            "name_en":      name_en,
            "category":     category,
            "base":         base,
            "recipe_count": recipe_count,
            "search_tokens": tokens,
        })

    # Tri global par popularité
    catalog.sort(key=lambda x: (-x["recipe_count"], x["name_fr"].lower()))
    logger.info("ingredient_catalog: %d entrées construites", len(catalog))
    return catalog


def get_catalog() -> list[dict]:
    """Retourne le catalogue unifié (lazy-init, thread-safe)."""
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache
    with _catalog_lock:
        if _catalog_cache is None:
            _catalog_cache = _build_catalog()
    return _catalog_cache


def invalidate_cache() -> None:
    """Invalide le cache (appelé si les données changent)."""
    global _catalog_cache
    _catalog_cache = None


def search(q: str, limit: int = 20) -> list[dict]:
    """
    Recherche dans le catalogue unifié.

    Priorités :
      10 — correspondance exacte ID
       8 — ID commence par q
       7 — name_fr commence par q
       6 — q dans ID
       5 — q dans name_fr
       4 — q dans name_en
       3 — q dans search_tokens

    À égalité de score, trie par recipe_count décroissant.
    Retourne uniquement les ingrédients présents dans au moins 1 recette.
    """
    catalog = get_catalog()
    q_lower = q.lower().strip()

    scored: list[tuple[int, dict]] = []
    for entry in catalog:
        if entry["recipe_count"] == 0:
            continue  # ignorer les IDs hors recettes

        iid_lower    = entry["id"].lower()
        name_fr_l    = entry["name_fr"].lower()
        name_en_l    = entry["name_en"].lower()

        score = 0
        if iid_lower == q_lower or name_fr_l == q_lower:
            score = 10
        elif iid_lower.startswith(q_lower):
            score = 8
        elif name_fr_l.startswith(q_lower):
            score = 7
        elif q_lower in iid_lower:
            score = 6
        elif q_lower in name_fr_l:
            score = 5
        elif q_lower in name_en_l:
            score = 4
        elif any(q_lower in t.lower() for t in entry.get("search_tokens", [])):
            score = 3

        if score > 0:
            scored.append((score, entry))

    scored.sort(key=lambda x: (-x[0], -x[1]["recipe_count"], x[1]["name_fr"].lower()))
    return [e for _, e in scored[:limit]]


def get_frigo_groups() -> list[dict]:
    """
    Retourne les groupes d'ingrédients pour les chips expandables du frigo.

    Structure retournée :
    [
      {
        "id": "grain",
        "label": "Féculents",
        "items": [
          {
            "id": "rice",          # base ID (peut être utilisé directement)
            "name_fr": "Riz",
            "recipe_count": 62,    # somme base + variantes
            "variants": [          # variantes hiérarchiques (si >1 dans recettes)
              {"id": "rice/long_grain", "name_fr": "Riz long grain", "recipe_count": 45},
              {"id": "rice/short_grain","name_fr": "Riz grain rond",  "recipe_count": 17},
            ]
          },
          ...
        ]
      },
      ...
    ]
    """
    catalog = get_catalog()

    # Index par base ID
    by_base: dict[str, list[dict]] = defaultdict(list)
    by_id:   dict[str, dict]       = {}
    for entry in catalog:
        by_id[entry["id"]] = entry
        by_base[entry["base"]].append(entry)

    groups = []
    seen_ids: set[str] = set()

    for cat_def in FRIGO_CATEGORIES:
        items: list[dict] = []

        for base_id in cat_def["bases"]:
            if base_id in seen_ids:
                continue

            # Entrées pour ce base (base lui-même + ses variantes)
            entries_for_base = by_base.get(base_id, [])

            # Ajouter l'entrée directe du base si elle existe dans le catalogue
            base_entry = by_id.get(base_id)

            # Regrouper base + variantes (ex: rice, rice/long_grain, rice/short_grain)
            direct    = [e for e in entries_for_base if e["id"] == base_id]
            variants  = [e for e in entries_for_base if e["id"] != base_id
                         and e["recipe_count"] > 0]

            # Exiger au moins 1 recette (base ou variante)
            total_count = sum(e["recipe_count"] for e in entries_for_base
                              if e["recipe_count"] > 0)
            if total_count == 0:
                continue

            # Nom FR du groupe = celui du base
            # Priorité : dict entry > _resolve_base (couvre _BASE_OVERRIDES)
            if base_entry:
                group_name = base_entry["name_fr"]
                group_cat  = base_entry["category"]
            else:
                # On passe le dict pour que _resolve_base puisse le consulter
                from backend.core.data_io import load_ingredients_dict
                _d = load_ingredients_dict()
                group_name, group_cat = _resolve_base(base_id, _d)

            # Filtrer les variantes dont le nom FR est identique au groupe
            # (ex: butter/dairy → "beurre" == "beurre" du groupe → inutile)
            # Ajouter chip_label : étiquette courte pour l'affichage dans la puce
            # (si la variante commence par le nom du groupe → on retire ce préfixe)
            _group_prefix = group_name.lower() + " "
            filtered_variants = []
            for v in variants:
                if v["name_fr"].lower() == group_name.lower():
                    continue   # identique au groupe → skip
                # Calcul du chip_label
                vname = v["name_fr"]
                if vname.lower().startswith(_group_prefix):
                    chip_label = vname[len(_group_prefix):].strip().capitalize()
                else:
                    chip_label = vname
                filtered_variants.append({
                    "id":           v["id"],
                    "name_fr":      vname,
                    "chip_label":   chip_label,
                    "recipe_count": v["recipe_count"],
                })

            item: dict = {
                "id":           base_id,
                "name_fr":      group_name,
                "recipe_count": total_count,
                "variants":     sorted(filtered_variants, key=lambda x: -x["recipe_count"]),
            }
            items.append(item)
            seen_ids.add(base_id)
            for v in entries_for_base:
                seen_ids.add(v["id"])

        if items:
            # Trier les items par recipe_count décroissant
            items.sort(key=lambda x: -x["recipe_count"])
            groups.append({
                "id":    cat_def["id"],
                "label": cat_def["label"],
                "items": items,
            })

    return groups
