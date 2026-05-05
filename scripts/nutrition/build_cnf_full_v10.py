#!/usr/bin/env python3
"""
build_cnf_full_v10.py  v10.1
=============================
Transforme les CSV bruts de Santé Canada (CNF 2015) en cnf_full_v10.json.

CHANGEMENTS v10.0 → v10.1 (audit scope recettes maison) :
  EXCL_GROUP_KEYS_BLOAT étendu — 62 group_keys ajoutés :
    Boissons industrielles (31) : alcools, sodas, jus concentrés, nectars,
    shakes, boissons sucrées, eau minérale, thé préparé, etc.
    Pâtisseries/gâteaux/biscuits industriels (25) : cakes, cookies, muffins,
    danish, donuts, croissants, toaster pastries, pies, strudel, etc.
    Confiseries industrielles (6) : icing, chocolate syrup, sweetener,
    dulce de leche, candied foods, frozen desserts.
  EXCL_NAME_RE_EXTENDED — 3 patterns ajoutés (cas mixtes) :
    "coffee, brewed" → exclut café prêt à boire (garde café poudre/instant).
    "sweets, pie fillings" → exclut garnitures industrielles.
    "sweets, sugars, icing" → exclut sucre glace (garde baking chocolate).

CHANGEMENTS v9.0 → v10.0 (délégation food_schema_v2) :
  - parse_state_v2, build_nutrients_object, build_diet_profile,
    compute_variant_id, state_variant_key, slugify, validate_food_item :
    SUPPRIMÉS localement → délégués à food_schema_v2 (source unique de vérité).
  - Appel build_nutrients_object : keyword-only (level1=, completeness_fields=).
    Le post-hoc nutrients_obj["_nutrient_meta"]["basis"] = ... est supprimé.
  - Appel parse_state_v2 : category=grp_en (aligné USDA).
  - DAIRY_CATEGORIES, _deaccent, _ACCENT_MAP : supprimés (dans food_schema_v2).
  - ~700 lignes retirées (patterns, constantes, implémentations dupliquées).

Usage :
  python build_cnf_full_v10.py
  python build_cnf_full_v10.py --dry-run
  python build_cnf_full_v10.py --output path/to/cnf_full_v10.json
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
SCRIPT_DIR = Path(__file__).resolve().parent
NUTRITION_DIR = (
    SCRIPT_DIR.parent if SCRIPT_DIR.name in ("raw", "scripts") else SCRIPT_DIR
)

if str(NUTRITION_DIR) not in sys.path:
    sys.path.insert(0, str(NUTRITION_DIR))
from food_schema_v2 import (
    compute_variant_id,
    parse_state_v2,
    build_nutrients_object,
    build_diet_profile,
    state_variant_key,
    slugify,
    validate_food_item,
    build_variant_tree,
    detect_extra_dimensions,
    round_nutrients,
    BASE_INGREDIENT_MAP,
)

# ── Taxonomie dynamique ───────────────────────────────────────────────────────
# Chargée une fois dans build() depuis taxonomy_session_*.json.
try:
    from taxonomy_loader import load_bk_taxonomy, build_taxonomy_object
    _TAXONOMY_AVAILABLE = True
except ImportError:
    _TAXONOMY_AVAILABLE = False
    def load_bk_taxonomy(path):   # type: ignore[override]
        return {}
    def build_taxonomy_object(bk, bk_taxonomy, *, fallback_unclassified=True):  # type: ignore[override]
        return None

_BK_TAXONOMY: dict[str, dict] = {}   # peuplé dans build()

# =============================================================================
# 1. PATHS
# =============================================================================
BASE_DIR       = Path(__file__).resolve().parents[2]
CNF_DIR        = BASE_DIR / "backend/data/nutrition/raw/cnf"
DEFAULT_OUTPUT = BASE_DIR / "backend/data/nutrition/outputs/cnf_full_v10.json"

# =============================================================================
# 2. NUTRIENT DEFS — IDs CNF réels
#    (cnf_id, champ_sortie, facteur_conversion)
#    Priorité : premier ID gagne pour un même champ.
# =============================================================================
NUTRIENT_DEFS: list[tuple[int, str, float]] = [
    # Énergie
    (208, "energy_kcal",         1.0),
    # Macros
    (203, "protein_g",           1.0),
    (205, "carbs_g",             1.0),
    (204, "fat_g",               1.0),
    (291, "fiber_g",             1.0),
    (269, "sugar_g",             1.0),
    (810, "starch_g",            1.0),
    # Bilan masse
    (255, "water_g",             1.0),
    (207, "ash_g",               1.0),
    # Acides gras totaux
    (606, "fa_saturated_g",      1.0),
    (645, "fa_mufa_g",           1.0),
    (646, "fa_pufa_g",           1.0),
    # FA spécifiques
    (607, "fa_4_0_g",            1.0),
    (608, "fa_6_0_g",            1.0),
    (609, "fa_8_0_g",            1.0),
    (610, "fa_10_0_g",           1.0),
    (611, "fa_12_0_g",           1.0),
    (612, "fa_14_0_g",           1.0),
    (613, "fa_16_0_g",           1.0),
    (614, "fa_18_0_g",           1.0),
    (617, "fa_18_1_oleic_g",     1.0),
    (620, "fa_20_4_ara_g",       1.0),
    # Oméga-3/6
    (831, "fa_18_3_ala_g",       1.0),
    (629, "fa_20_5_epa_g",       1.0),
    (621, "fa_22_6_dha_g",       1.0),
    (618, "fa_18_2_linoleic_g",  1.0),
    # Cholestérol
    (601, "cholesterol_mg",      1.0),
    # Minéraux
    (301, "calcium_mg",          1.0),
    (312, "copper_mg",           1.0),
    (303, "iron_mg",             1.0),
    (304, "magnesium_mg",        1.0),
    (315, "manganese_mg",        1.0),
    (305, "phosphorus_mg",       1.0),
    (306, "potassium_mg",        1.0),
    (317, "selenium_ug",         1.0),
    (307, "sodium_mg",           1.0),
    (309, "zinc_mg",             1.0),
    # Vitamines
    (814, "vitamin_a_rae_ug",    1.0),
    (319, "retinol_ug",          1.0),
    (321, "beta_carotene_ug",    1.0),
    (339, "vitamin_d_ug",        1.0),
    # vitamin_e_mg et alpha_tocopherol_mg → même ID 323 ; alias géré post-extraction
    (323, "vitamin_e_mg",        1.0),
    (430, "vitamin_k1_ug",       1.0),
    (401, "vitamin_c_mg",        1.0),
    (404, "vitamin_b1_mg",       1.0),
    (405, "vitamin_b2_mg",       1.0),
    (406, "vitamin_b3_mg",       1.0),
    (410, "vitamin_b5_mg",       1.0),
    (415, "vitamin_b6_mg",       1.0),
    (417, "folate_ug",           1.0),
    (431, "folic_acid_ug",       1.0),
    (815, "folate_dfe_ug",       1.0),
    (806, "folate_intrinsic_ug", 1.0),
    (418, "vitamin_b12_ug",      1.0),
    (862, "choline_mg",          1.0),   # CNF-spécifique (ID 862)
]

NUTRIENT_FIELDS = [f for _, f, _ in NUTRIENT_DEFS]

COMPUTED_FIELDS = ["energy_kj", "salt_g"]

# Champs absents CNF — toujours None pour compatibilité CIQUAL/USDA
CNF_ABSENT = [
    "energy_kj_jones", "energy_kcal_jones",
    "protein_n625_g",
    "polyols_g",
    "organic_acids_g",
    "fructose_g", "galactose_g", "glucose_g",
    "lactose_g",  "maltose_g",   "saccharose_g",
    "alcohol_g",
    "chloride_mg", "iodine_ug",
    "vitamin_d2_ug", "vitamin_d3_ug", "vitamin_k2_ug",
]

SALT_SODIUM_RATIO = 2.542
KCAL_TO_KJ        = 4.184

# =============================================================================
# 2b. MAPPING CATÉGORIE CNF → CATÉGORIE UNIFIÉE + TAXONOMY
# =============================================================================
_CNF_CATEGORY_MAP: dict[str, tuple] = {
    "Dairy and Egg Products":            ("produits laitiers et œufs",        "cnf_1.0",  None, "cnf_1.1"),
    "Spices and Herbs":                  ("épices et herbes aromatiques",     "cnf_2.0",  None, "cnf_2.1"),
    "Baby Foods":                        ("aliments pour bébés",              "cnf_3.0",  None, "cnf_3.1"),
    "Fats and Oils":                     ("matières grasses et huiles",       "cnf_4.0",  None, "cnf_4.1"),
    "Poultry Products":                  ("volaille et produits dérivés",     "cnf_5.0",  None, "cnf_5.1"),
    "Soups, Sauces, and Gravies":        ("soupes, sauces et jus de cuisson", "cnf_6.0",  None, "cnf_6.1"),
    "Sausages and Luncheon Meats":       ("charcuteries et saucisses",        "cnf_7.0",  None, "cnf_7.1"),
    "Breakfast Cereals":                 ("céréales pour petit-déjeuner",     "cnf_8.0",  None, "cnf_8.1"),
    "Fruits and Fruit Juices":           ("fruits et jus de fruits",          "cnf_9.0",  None, "cnf_9.1"),
    "Pork Products":                     ("porc et produits dérivés",         "cnf_10.0", None, "cnf_10.1"),
    "Vegetables and Vegetable Products": ("légumes et produits végétaux",     "cnf_11.0", None, "cnf_11.1"),
    "Nut and Seed Products":             ("noix, graines et oléagineux",      "cnf_12.0", None, "cnf_12.1"),
    "Beef Products":                     ("bœuf et produits dérivés",         "cnf_13.0", None, "cnf_13.1"),
    "Beverages":                         ("boissons",                         "cnf_14.0", None, "cnf_14.1"),
    "Finfish and Shellfish Products":    ("poissons et fruits de mer",        "cnf_15.0", None, "cnf_15.1"),
    "Legumes and Legume Products":       ("légumineuses et dérivés",          "cnf_16.0", None, "cnf_16.1"),
    "Lamb, Veal, and Game Products":     ("agneau, veau et gibier",           "cnf_17.0", None, "cnf_17.1"),
    "Baked Products":                    ("produits de boulangerie",          "cnf_18.0", None, "cnf_18.1"),
    "Sweets":                            ("sucreries et confiseries",         "cnf_19.0", None, "cnf_19.1"),
    "Cereal Grains and Pasta":           ("céréales, grains et pâtes",        "cnf_20.0", None, "cnf_20.1"),
    "Fast Foods":                        ("restauration rapide",              "cnf_21.0", None, "cnf_21.1"),
    "Meals, Entrees, and Side Dishes":   ("plats préparés et accompagnements","cnf_22.0", None, "cnf_22.1"),
    "Snacks":                            ("snacks et apéritifs",              "cnf_23.0", None, "cnf_23.1"),
    "Restaurant Foods":                  ("restauration",                     "cnf_24.0", None, "cnf_24.1"),
}
_CNF_CATEGORY_DEFAULT: tuple = (None, "cnf_0.0", None, "cnf_0.1")

_CNF_TAXONOMY_L1: dict[str, str] = {
    "Dairy and Egg Products":            "dairy_eggs",
    "Spices and Herbs":                  "spices_herbs",
    "Baby Foods":                        "baby_foods",
    "Fats and Oils":                     "fats_oils",
    "Fruits and Fruit Juices":           "fruits",
    "Vegetables and Vegetable Products": "vegetables",
    "Nut and Seed Products":             "nuts_seeds",
    "Legumes and Legume Products":       "legumes",
    "Cereal Grains and Pasta":           "cereals_pasta",
    "Breakfast Cereals":                 "cereals_breakfast",
    "Beverages":                         "beverages",
    "Sweets":                            "sweets",
    "Snacks":                            "snacks",
    "Baked Products":                    "baked",
    "Meals, Entrees, and Side Dishes":   "prepared_meals",
    "Fast Foods":                        "fast_food",
    "Restaurant Foods":                  "restaurant",
    "Soups, Sauces, and Gravies":        "sauces_soups",
}


def build_unified_category(grp_en: str, grp_fr: str) -> dict:
    l1_fr_map, l1_code, l2_fr, l2_code = _CNF_CATEGORY_MAP.get(grp_en, _CNF_CATEGORY_DEFAULT)
    return {
        "level1_fr":   l1_fr_map or (grp_fr if grp_fr else None),
        "level1_en":   grp_en if grp_en else None,
        "level1_code": l1_code,
        "level2_fr":   l2_fr,
        "level2_code": l2_code,
        "level3_fr":   None,
        "level3_code": None,
    }


def build_taxonomy(grp_en: str, bk: str | None = None) -> dict:
    """
    Résout la taxonomie pour un item CNF.

    Stratégie (priorité décroissante) :
      1. bk dans _BK_TAXONOMY          → taxonomie dynamique (taxonomy_session_*.json)
      2. grp_en slugifié dans _BK_TAXONOMY → approximation par label de groupe
      3. _CNF_TAXONOMY_L1              → mapping statique hérité (rétrocompat)
      4. Fallback unclassified

    Le format de retour est désormais aligné sur le schéma unifié :
      { group_id, group_label, subgroup_id, subgroup_label }
    Un champ supplémentaire _legacy_l1 conserve l'ancien libellé pour
    la rétrocompat des scripts qui lisaient taxonomy.l1.
    """
    # Priorité 1 : lookup dynamique par bk canonique
    if bk and _BK_TAXONOMY:
        dyn = build_taxonomy_object(bk, _BK_TAXONOMY, fallback_unclassified=False)
        if dyn is not None:
            return {**dyn, "_legacy_l1": _CNF_TAXONOMY_L1.get(grp_en, "other")}

    # Priorité 2 : tentative par grp_en slugifié (ex: "Beverages" → "beverages")
    if grp_en and _BK_TAXONOMY:
        _slug = grp_en.lower().replace(" ", "_").replace(",", "").replace("&", "and")
        dyn2 = build_taxonomy_object(_slug, _BK_TAXONOMY, fallback_unclassified=False)
        if dyn2 is not None:
            return {**dyn2, "_legacy_l1": _CNF_TAXONOMY_L1.get(grp_en, "other")}

    # Priorité 3 : mapping statique hérité (_CNF_TAXONOMY_L1)
    legacy_l1 = _CNF_TAXONOMY_L1.get(grp_en, "other")
    return {
        "group_id":       None,
        "group_label":    grp_en if grp_en else None,
        "subgroup_id":    None,
        "subgroup_label": None,
        "_legacy_l1":     legacy_l1,
    }


# =============================================================================
# 3. EXCLUSIONS
# =============================================================================
EXCL_GROUPS_HARD: set[int] = {3, 5, 6, 7, 10, 13, 15, 17, 21, 22, 25}

EXCL_GROUP_KEYS_BLOAT: set[str] = {
    # Catégories originales
    "cereal_ready", "candies", "dessert", "salad_dressing",
    # ── v10.1 : boissons industrielles ───────────────────────────────────────
    "alcohol",                          # cocktails, vins de dessert
    "non_alcoholic",                    # vin sans alcool
    "carbonated_drinks",                # club soda, sodas
    "water",                            # eau minérale embouteillée
    "tea",                              # thé infusé prêt à boire (pas feuilles)
    "apple_juice",                      # jus de pomme concentré
    "apricot_nectar",                   # nectar d'abricot
    "blackberry_juice",                 # jus de mûre
    "cranberry_juice",                  # jus de canneberge
    "juice_apple",                      # blend jus pomme+raisin
    "juice_drink",                      # boissons aux fruits sucrées
    "juice_cocktail",                   # cocktail de jus concentré
    "peach_nectar",                     # nectar de pêche
    "pear_nectar",                      # nectar de poire
    "pomegranate_juice",                # jus de grenade
    "prune_juice",                      # jus de pruneau
    "lemonade",                         # limonade concentrée
    "lemonade_with_artificial_sweetener",
    "limeade",                          # citron vert concentré
    "beverage_mix",                     # poudre aromatisée chocolat
    "beverage",                         # "Beverage, bean" — composite
    "beverages",                        # "Beverages, high protein powder"
    "coffee_substitute",                # succédané de café céréales
    "coffee_and_cocoa_mocha_powder",    # mélange café-cacao industriel
    "chocolate_flavour_drink",          # boisson chocolatée lacto-industrielle
    "hot_chocolate",                    # chocolat chaud avec aspartame
    "drink",                            # boissons aux fruits sucrées en poudre
    "milk_shake",                       # milkshake épais
    "milk_shake_fast_food",             # milkshake fast-food
    "malted_milk",                      # poudre de lait malté enrichi
    "strawberry_flavour_mix",           # poudre aromatisée fraise
    "plant_based_beverage",             # lait de riz enrichi (boisson, pas ingrédient)
    # ── v10.1 : pâtisseries et biscuits industriels ────────────────────────
    "cake_pound",                       # cake allégé commercial
    "cake_snack",                       # cake snack crème
    "cake_yellow",                      # gâteau avec glaçage industriel
    "cinnamon_bun",                     # pain à la cannelle glacé
    "coffee_cake",                      # gâteau streusel
    "cookie_brownie",                   # brownie commercial allégé
    "cookie_butter",                    # biscuit beurre avec glaçage
    "cookie_chocolate",                 # cookies pépites chocolat commercial
    "cookie_graham",                    # crackers graham low-fat
    "cookie_ladyfinger",                # boudoirs
    "cookie_oatmeal",                   # biscuits avoine commercial
    "cookie_peanut",                    # sandwich beurre de cacahuète
    "cookie_shortbread",                # sablés sans sucre ajouté
    "cookie_sugar",                     # gaufrettes fourrées
    "cookie_vanilla",                   # gaufrettes vanille
    "croissant",                        # croissant pomme commercial
    "danish_pastry",                    # viennoiserie cannelle
    "doughnut_donut",                   # donut glacé chocolat
    "muffin_bar",                       # barre muffin toutes saveurs
    "muffin",                           # muffin bleuet toaster-type
    "pie",                              # tartes industrielles (chocolat, cerises)
    "pie_crust",                        # fond de tarte cookie chocolat
    "strudel",                          # strudel pomme
    "sweet_roll",                       # rouleau sucré raisins commercial
    "toaster_pastry",                   # tartelette toaster fruits
    # ── v10.1 : confiseries et sucres industriels ─────────────────────────
    "candied_foods",                    # écorces confites
    "dulce_de_leche_caramelized_milk",  # confiture de lait
    "frozen",                           # glace bâtonnet low-fat
    "icing_frosting",                   # glaçage chocolat prêt-à-l'emploi
    "chocolate_syrup",                  # sirop chocolat liquide
    "sweetener",                        # sucralose SPLENDA
    # ── v10.2 : résidus post-audit ────────────────────────────────────────
    "dessert_topping_non_dairy",        # crème fouettée synthétique industrielle
    "bread_crumbs",                     # chapelure assaisonnée industrielle
}

NON_VEG_RE: list[re.Pattern] = [re.compile(p, re.I) for p in [
    r"\bbeef\b", r"\bpork\b",
    r"\bchicken\b", r"\bturkey\b", r"\bduck\b", r"\bgoose\b",
    r"\blamb\b", r"\bveal\b", r"\bgoat\b",
    r"\bmeat\b", r"\bsteak\b", r"\bribs?\b",
    r"\bbacon\b", r"\bham\b(?!burg)",
    r"\bsausages?\b",
    r"\blard\b",
    r"\bgelatin[e]?\b",
    r"\banchovies?\b", r"\bsardines?\b",
    r"\btuna\b", r"\btrout\b",
    r"\bsalmon\b",
    r"\bshrimp\b", r"\blobster\b",
    r"\bcrab\b(?!\s*apple)",
    r"\boyster\b", r"\bclams?\b",
    r"\bmussels?\b", r"\bsquid\b",
    r"\bfish\b",
    r"\bseafood\b", r"\bshellfish\b",
    r"\bluncheon\b", r"\bfrankfurter\b",
    r"\bwieners?\b",
    r"\bpepperoni\b", r"\bchorizo\b", r"\bsalami\b",
    r"\bjerk(y)?\b", r"\bpat[e\xe9]\b",
    r"\bpig\b", r"\bvenison\b",
    r"\bprosciutto\b",
    r"\banimal\s+fat\b",
]]

COMPOSITE_NAME_RE: list[re.Pattern] = [re.compile(p, re.I) for p in [
    r"\blasagnas?\b", r"\braviolis?\b", r"\bpizzas?\b",
    r"\bburritos?\b", r"\btamales?\b", r"\bquesadillas?\b",
    r"\begg\s+rolls?\b", r"\bpot\s+pie\b",
    r"\bshepherd['']?s?\s+pie\b",
    r"\bpoutine\b", r"\bstew\b", r"\bcasserole\b",
    r"\bpasteurized\s+process\b",
    r"\bcommercially\s+prepared\b", r"\brestaurant\s+prepared\b",
    r"\bwith\s+(?:meat|beef|pork|chicken|turkey|bacon|ham|sausage|seafood|fish)\b",
    r"\bwith\s+(?:gravy|meat\s+sauce)\b",
    r"\band\s+(?:meat|beef|pork|chicken|turkey)\b",
    r"\bbarbecue\s+flavou?r\b", r"\bsour\s+cream\s+and\s+onion\b",
    r"\bhomemade\b", r"\bdry\s+mix\b",
    r",\s*unprepared\b",
    r"\bprepared\s+with\s+\d",
    r"\brefrigerated\s+dough\b",
    r"\bmade\s+with\s+(?:margarine|shortening|lard)\b",
]]

EXCL_NAME_RE_EXTENDED: list[re.Pattern] = [re.compile(p, re.I) for p in [
    # ── v10.1 : cas mixtes (group_key partagé avec items légitimes) ──────────
    # "coffee" = [brewed → EXCLU] + [instant powder → GARDÉ]
    r"\bcoffee,\s+brewed\b",
    # "sweets" = [baking chocolate → GARDÉ] + [pie fillings / icing → EXCLUS]
    r"\bsweets,\s+pie\s+filling",
    r"\bsweets,\s+sugars,\s+icing\b",
    # Ingrédients autochtones canadiens
    r"\bcattail\b", r"\bcloudberry\b", r"\bbakeapple\b",
    r"\bblack\s+crowberry\b", r"\bcurlewberry\b",
    r"\bchokecherry\b", r"\bfireweed\b", r"\brose\s+hips?\b",
    r"\bsalmonberry\b", r"\bmashu\b", r"\bsweetvetch\b",
    r"\bmountain\s+sorrel,\s+native\b", r"\bsourdock\b",
    r"\bnetted\s+willow\b", r"\bwillow,\s+native\b",
    r"\boheloberry\b", r"\beppaw\b",
    # Fruits tropicaux exotiques
    r"\babiyuch\b", r"\bacerola\b", r"\bbreadfruit\b",
    r"\bcarissa\b", r"\bnatalplum\b", r"\bcherimoya\b",
    r"\bcustard[- ]apple\b", r"\bdurian\b", r"\bfeijoa\b",
    r"\bgroundcherry\b", r"\bjackfruit\b", r"\bjava[- ]plum\b",
    r"\blongan\b", r"\bloquat\b", r"\bmammy[- ]apple\b",
    r"\bmangosteen\b", r"\bpitanga\b", r"\bpummelo\b",
    r"\brambutan\b", r"\brose[- ]apple\b", r"\browal\b",
    r"\bsapodilla\b", r"\bsapote\b", r"\bsoursop\b",
    r"\bsugar[- ]apple\b",
    # Légumes exotiques
    r"\bagave\b", r"\barrowhead\b",
    r"\bbalsam[- ]pear\b", r"\bbitter\s+gourd\b", r"\bbitter\s+melon\b",
    r"\bborage\b", r"\bbutterbur\b", r"\bfuki\b", r"\bcardoon\b",
    r"\bceltuce\b", r"\bchrysanthemum\b",
    r"\bdrumstick\s*\(horseradish[- ]tree\)\b",
    r"\bepazote\b", r"\bjute,\s+potherb\b", r"\bkanpyo\b",
    r"\blambsquarters\b", r"\bmalabar\s+spinach\b",
    r"\bnopales\b", r"\bpoi\b", r"\bpokeberry\b",
    r"\bsesbania\b", r"\bstinging\s+nettles?\b",
    r"\bswamp\s+cabbage\b", r"\bskunk\s+cabbage\b",
    r"\btaro\b", r"\bvine\s+spinach\b", r"\bwaxgourd\b",
    r"\bwinged\s+beans?\b", r"\bgoa\s+beans?\b",
    r"\byambean\b", r"\bjimaca\b", r"\byautia\b", r"\btannier\b",
    # Produits industriels
    r"\bshake\s+and\s+bake\b", r"\bquaker\b", r"\bkellogg'?s\b",
    r"\bsweetener,\s+aspartame\b", r"\breddi\s+wip\b",
    r"\benergy\s+drink\b", r"\bvitamin\s+water\b",
    r"\bvodka\s+cooler\b", r"\bwhisky\s+sour\s+mix\b",
    r"\bsports\s+drink\b", r"\bsangria\b",
    r"\bmalt\s+beverage\b", r"\binstant\s+breakfast\b",
    r"\bbreakfast\s+tart\b", r"\bmeal\s+replacement\b",
    # Noix exotiques
    r"\bnuts,\s+acorn\b", r"\bacorn\s+flour\b",
    r"\bbeechnuts?\b", r"\bginkgo\s+nuts?\b",
    r"\bpilinuts?\b", r"\bcanarytree\b",
    r"\bbutternuts?\b", r"\bhickory\s+nuts?\b",
    r"\bbreadnuttree\b", r"\bcottonseed\b",
    # Produits laitiers de niche
    r"\bbutter\s+oil,\s+anhydrous\b", r"\bwhey,\s+acid\b",
    r"\bmilk,\s+fluid,\s+human\b", r"\bmilk,\s+fluid,\s+sheep\b",
    r"\bmilk,\s+fluid,\s+whole,\s+producer\b",
    r"\bcoffee\s+whitener.*powdered,\s+light\b",
    r"\bcream,\s+substitute,\s+flavoured\b",
    r"\bwhipped\s+cream\s+substitute,\s+dietetic\b",
    r"\begg\s+substitute,\s+frozen\b", r"\begg\s+benedict\b",
    # États redondants
    r"\bchinese\s+restaurant\b",
    r",\s*stir[- ]fried\b", r",\s*microwaved\b",
    r"\bfrozen,\s+ready[- ]to[- ]heat\b",
    r"\bpar\s+fried,\s+frozen\b", r"\bhashed\s+brown,\s+frozen\b",
    r"\bpotato\s+puff\b", r"\bpotato,\s+o'brien\b",
    r"\bbeans,\s+liquid\s+from\b",
    r",\s*freeze[- ]dried\b", r"\bonion,\s+dehydrated\s+flakes\b",
    # Algues / graines exotiques
    r"\bemi[- ]tsunomata\b", r"\bseaweed,\s+agar\b",
    r"\bseeds,\s+breadfruit\b", r"\bseeds,\s+breadnuttree\b",
    r"\bseeds,\s+cottonseed\b",
]]

# =============================================================================
# 4. AUDIT — spécifique CNF (tolérance énergie 25% vs 20% USDA)
# =============================================================================
ENERGY_FACTORS_KJ = {
    "protein_g": 17, "carbs_g": 17, "fat_g": 37, "fiber_g": 8, "alcohol_g": 29,
}
MASS_BALANCE_WARN_G = 15.0
MASS_BALANCE_ERR_G  = 30.0
ENERGY_TOLERANCE    = 0.25   # CNF : tolérance plus large qu'USDA (0.20)
FA_BALANCE_TOL      = 0.10

SEVERITY_CLASS: dict[str, str] = {
    "negative_values": "physical_error",
    "sugar_vs_carbs":  "physical_error",
    "mass_balance":    "major_quality",
    "energy_check":    "data_quality",
    "fa_balance":      "major_quality",
}

_COMPLETENESS_FIELDS: list[str] = [
    "energy_kcal", "protein_g", "carbs_g",  "fat_g",
    "fiber_g",     "water_g",   "sodium_mg", "calcium_mg",
    "iron_mg",     "vitamin_c_mg", "folate_ug", "vitamin_d_ug",
    "fa_saturated_g", "fa_18_3_ala_g",
]


def get_severity_class(check: str, severity: str) -> str:
    if check == "mass_balance" and severity == "error":
        return "physical_error"
    return SEVERITY_CLASS.get(check, "info")


def run_audit(description, cnf_id, food_id, nutrients, by_check, all_issues):
    issues: list[dict] = []

    def flag(check, sev, msg, **kw):
        sev_class = get_severity_class(check, sev)
        issue = {"severity_class": sev_class, "severity": sev, "check": check, "message": msg}
        if kw:
            issue.update(kw)
        issues.append(issue)
        all_issues.append({"id": food_id, "source_id": cnf_id, "name_en": description, **issue})
        by_check[check][sev + "s"] = by_check[check].get(sev + "s", 0) + 1

    def g(f):
        return nutrients.get(f)

    for field, val in nutrients.items():
        if val is not None and val < -0.001:
            flag("negative_values", "error", f"Valeur negative : {field} = {val}")

    sug, carbs = g("sugar_g"), g("carbs_g")
    if sug is not None and carbs is not None and sug > carbs + 0.5:
        flag("sugar_vs_carbs", "error", f"sugar_g={sug} > carbs_g={carbs}")

    components = ["water_g", "protein_g", "fat_g", "carbs_g", "ash_g"]
    vals = [g(f) for f in components if g(f) is not None]
    if len(vals) >= 4:
        total = sum(vals)
        delta = abs(100.0 - total)
        if delta > MASS_BALANCE_ERR_G:
            flag("mass_balance", "error",
                 f"Sigma macros={total:.1f} g/100g (ecart={delta:.1f}g)")
        elif delta > MASS_BALANCE_WARN_G:
            flag("mass_balance", "warning",
                 f"Sigma macros={total:.1f} g/100g (ecart={delta:.1f}g)")

    e_decl = g("energy_kcal")
    if e_decl and e_decl > 0:
        e_calc = sum((g(f) or 0.0) * fac / KCAL_TO_KJ
                     for f, fac in ENERGY_FACTORS_KJ.items() if g(f) is not None)
        if e_calc > 0:
            delta_pct = abs(e_decl - e_calc) / e_decl
            if delta_pct > ENERGY_TOLERANCE:
                flag("energy_check", "warning",
                     f"Energie declaree={e_decl:.0f} kcal vs calculee={e_calc:.1f} kcal "
                     f"(delta={delta_pct*100:.1f}%)",
                     delta_pct=round(delta_pct * 100, 1))

    fat = g("fat_g"); sfa = g("fa_saturated_g"); mufa = g("fa_mufa_g"); pufa = g("fa_pufa_g")
    if fat and sfa is not None and mufa is not None and pufa is not None:
        total_fa = sfa + mufa + pufa
        if total_fa > fat * (1 + FA_BALANCE_TOL) + 0.1:
            flag("fa_balance", "warning", f"SFA+MUFA+PUFA={total_fa:.2f} > fat_g={fat:.2f}")

    n_phys  = sum(1 for i in issues if i["severity_class"] == "physical_error")
    n_major = sum(1 for i in issues if i["severity_class"] == "major_quality")
    n_dq    = sum(1 for i in issues if i["severity_class"] == "data_quality")
    score = {
        "physical_errors": n_phys, "major_quality": n_major, "data_quality": n_dq,
        "total": len(issues), "usable": n_phys == 0,
    }
    return issues, score


def compute_quality_score(audit_score: dict, nutrients: dict) -> float:
    present      = sum(1 for f in _COMPLETENESS_FIELDS if nutrients.get(f) is not None)
    completeness = present / len(_COMPLETENESS_FIELDS) * 0.50
    n_phys  = audit_score.get("physical_errors", 0)
    n_major = audit_score.get("major_quality", 0)
    n_dq    = audit_score.get("data_quality", 0)
    if n_phys > 0:
        audit_comp = 0.0
    else:
        penalty    = min(n_major * 0.05 + n_dq * 0.01, 0.50)
        audit_comp = round(0.50 - penalty, 4)
    return round(min(completeness + audit_comp, 1.0), 3)


# =============================================================================
# 5. UTILITAIRES — group_key spécifique CNF
#    slugify importé depuis food_schema_v2.
# =============================================================================
_GENERIC_CNF_PREFIXES: set[str] = {
    "oil", "oils", "beans", "bean", "flour", "cheese", "milk", "nuts", "butter",
    "cream", "yogurt", "yoghurt", "mushroom", "mushrooms", "pepper", "peppers",
    "squash", "lettuce", "cabbage", "apple", "apples", "tomato", "tomatoes",
    "potato", "potatoes", "onion", "onions", "corn", "spinach", "broccoli",
    "carrot", "carrots", "egg", "eggs", "rice", "wheat", "berries", "berry",
    "juice", "bread", "crackers", "cereal", "cereals", "cookies", "cookie",
    "cake", "cakes", "soup", "sauce", "salad",
}

# slugify importé → les stop-slugs sont calculés via le même hash que USDA/CIQUAL
_STATE_STOP_SLUGS: set[str] = {
    slugify(s) for s in [
        "dry", "dried", "raw", "cooked", "fresh", "frozen", "canned",
        "whole", "plain", "fluid", "unsweetened", "refrigerated",
        "low fat", "nonfat", "full fat", "fat free", "reduced fat",
        "boiled", "steamed", "grilled", "roasted", "fried",
        "uncooked", "unprepared", "pasteurized", "dehydrated",
        "ready to serve", "condensed",
    ]
}

_PAREN_RE = re.compile(r"\([^)]*\)")


def _split_parts(description: str) -> list[str]:
    parts, current, depth = [], [], 0
    for ch in description:
        if ch == "(":
            depth += 1; current.append(ch)
        elif ch == ")":
            depth -= 1; current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip()); current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def build_group_key(description: str) -> tuple[str, str]:
    """Clé de regroupement canonique + base_name depuis la description CNF."""
    parts = _split_parts(description)
    if not parts:
        return slugify(description)[:80], description
    first       = parts[0].strip()
    first_lower = first.lower()
    if first_lower in _GENERIC_CNF_PREFIXES and len(parts) >= 2:
        for second in parts[1:]:
            second_clean = _PAREN_RE.sub("", second).strip()
            s_slug = slugify(second_clean)
            if s_slug and s_slug not in _STATE_STOP_SLUGS:
                key_part  = second_clean.split()[0] if second_clean.split() else second_clean
                base_name = f"{first}, {second_clean}"
                return slugify(f"{first} {key_part}"), base_name
        second_clean = _PAREN_RE.sub("", parts[1]).strip()
        key_part  = second_clean.split()[0] if second_clean.split() else second_clean
        base_name = f"{first}, {second_clean}"
        return slugify(f"{first} {key_part}"), base_name
    return slugify(first), first


def extract_base_name(description: str) -> tuple[str, str]:
    """Retourne (partie avant 1ère virgule, reste)."""
    depth = 0
    for i, ch in enumerate(description):
        if ch == "(":   depth += 1
        elif ch == ")": depth -= 1
        elif ch == "," and depth == 0:
            return description[:i].strip(), description[i+1:].strip()
    return description.strip(), ""


# =============================================================================
# 6. CSV LOADER
# =============================================================================
def load_csv(name: str, cnf_dir: Path) -> pd.DataFrame:
    path = cnf_dir / name
    if not path.exists():
        raise FileNotFoundError(
            f"CSV absent : {path}\n  Dispo : {[f.name for f in cnf_dir.glob('*.csv')]}"
        )
    for enc in ["utf-8-sig", "utf-8", "latin1", "cp1252"]:
        for sep in [",", ";", "\t"]:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep)
                if len(df.columns) > 2:
                    return df
            except Exception:
                continue
    raise Exception(f"Impossible de lire : {name}")


# =============================================================================
# 7. BUILD PRINCIPAL
# =============================================================================
def build(dry_run: bool = False, output_path: Path = DEFAULT_OUTPUT,
          cnf_dir: Path = CNF_DIR,
          taxonomy_path: Path | None = None) -> dict:

    print("=" * 70)
    print("BUILD CNF v10.0  (food_schema_v2 — source unique de vérité)")
    print("=" * 70)

    # ── Chargement de la taxonomie dynamique ─────────────────────────────────
    global _BK_TAXONOMY
    if taxonomy_path is not None and taxonomy_path.exists():
        _BK_TAXONOMY = load_bk_taxonomy(taxonomy_path)
        print(f"[0/6] Taxonomie chargée : {len(_BK_TAXONOMY)} bk depuis {taxonomy_path.name}")
    elif taxonomy_path is not None:
        print(f"[0/6] ⚠️  taxonomy_path introuvable : {taxonomy_path} — champ 'taxonomy' en mode legacy.")
    else:
        # Auto-détection dans reference/
        ref_dir    = BASE_DIR / "backend" / "data" / "nutrition" / "reference"
        candidates = sorted(ref_dir.glob("taxonomy_session_*.json"), reverse=True)
        if candidates:
            _BK_TAXONOMY = load_bk_taxonomy(candidates[0])
            print(f"[0/6] Taxonomie auto-détectée : {len(_BK_TAXONOMY)} bk — {candidates[0].name}")

    # ── Chargement CSV ──────────────────────────────────────────────────────
    print("\n[1/6] Chargement des CSV sources...")
    food         = load_csv("FOOD_NAME.csv",        cnf_dir)
    group        = load_csv("FOOD_GROUP.csv",        cnf_dir)
    nutrient_amt = load_csv("NUTRIENT_AMOUNT.csv",   cnf_dir)
    refuse_df    = load_csv("REFUSE_AMOUNT.csv",     cnf_dir)
    yield_df     = load_csv("YIELD_AMOUNT.csv",      cnf_dir)
    conv_df      = load_csv("CONVERSION_FACTOR.csv", cnf_dir)
    measure_df   = load_csv("MEASURE_NAME.csv",      cnf_dir)

    total_input = len(food)
    print(f"    FOOD_NAME         : {total_input} items")
    print(f"    NUTRIENT_AMOUNT   : {len(nutrient_amt)} mesures")

    group_map    = dict(zip(group["FoodGroupID"], group["FoodGroupName"]))
    group_map_fr = dict(zip(group["FoodGroupID"], group["FoodGroupNameF"]))

    # ── Index mesures (portions) ─────────────────────────────────────────
    print("\n[2/6] Indexation nutriments + portions...")
    measure_map: dict[str, dict] = {}
    for _, r in measure_df.iterrows():
        mid = str(r.get("MeasureID", "")).strip()
        en  = str(r.get("MeasureDescription",  "") or "").strip()
        fr  = str(r.get("MeasureDescriptionF", "") or "").strip()
        if mid:
            measure_map[mid] = {"en": en, "fr": fr}

    portions_map: dict = defaultdict(list)
    for _, r in conv_df.iterrows():
        fid = r.get("FoodID")
        mid = str(r.get("MeasureID", "")).strip()
        cf  = r.get("ConversionFactorValue")
        if fid is None or cf is None:
            continue
        try:
            gpv = round(float(cf) * 100, 1)
        except (TypeError, ValueError):
            continue
        if gpv <= 0:
            continue
        m = measure_map.get(mid, {})
        portions_map[fid].append({
            "unit":           m.get("en", mid),
            "unit_fr":        m.get("fr", ""),
            "grams_per_unit": gpv,
        })

    # ── Index nutriments ─────────────────────────────────────────────────
    _seen_fields: dict[str, None] = {}
    _id_to_field: dict[int, tuple[str, float]] = {}
    for cnf_id, field, conv in NUTRIENT_DEFS:
        if field not in _seen_fields:
            _seen_fields[field] = None
            _id_to_field[cnf_id] = (field, conv)

    nut_index: dict = defaultdict(dict)
    for _, r in nutrient_amt.iterrows():
        fid = r.get("FoodID")
        nid = r.get("NutrientID")
        val = r.get("NutrientValue")
        if fid is None or nid is None or val is None:
            continue
        info = _id_to_field.get(nid)
        if info and info[0] not in nut_index[fid]:
            try:
                nut_index[fid][info[0]] = float(val) * info[1]
            except (TypeError, ValueError):
                pass

    # ── Index refuse / yield ─────────────────────────────────────────────
    refuse_map: dict = {}
    for _, r in refuse_df.iterrows():
        fid, val = r.get("FoodID"), r.get("RefuseAmount")
        if fid is not None and val is not None:
            try: refuse_map[fid] = float(val)
            except (TypeError, ValueError): pass

    yield_map: dict = defaultdict(dict)
    for _, r in yield_df.iterrows():
        fid, yid, val = r.get("FoodID"), r.get("YieldID"), r.get("YieldAmount")
        if fid and yid and val is not None:
            try: yield_map[fid][str(yid)] = float(val)
            except (TypeError, ValueError): pass

    # ── Build items ─────────────────────────────────────────────────────
    print("\n[3/6] Construction des items...")
    foods_flat      : list[dict] = []
    exclusions       = defaultdict(int)
    excl_log         : list[dict] = []
    all_issues       : list[dict] = []
    by_check         : dict       = defaultdict(dict)
    seen_group_keys  : dict       = defaultdict(int)
    stats_state      : dict       = defaultdict(int)

    ts = datetime.now(timezone.utc).isoformat()

    def excl(fid, name, reason):
        exclusions[reason] += 1
        excl_log.append({"source_id": fid, "name_en": name, "reason": reason})

    for _, row in food.iterrows():
        fid    = row.get("FoodID")
        name   = str(row.get("FoodDescription",  "") or "")
        namef  = str(row.get("FoodDescriptionF", "") or "")
        grp_id = row.get("FoodGroupID")
        grp_en = group_map.get(grp_id, "")
        grp_fr = group_map_fr.get(grp_id, "")

        if grp_id in EXCL_GROUPS_HARD:
            excl(fid, name, f"group_hard_{grp_id}"); continue

        _gk_preview, _ = build_group_key(name)
        if _gk_preview in EXCL_GROUP_KEYS_BLOAT:
            excl(fid, name, f"bloat_group_{_gk_preview}"); continue

        if any(p.search(name) for p in NON_VEG_RE):
            excl(fid, name, "non_veg_name"); continue

        if any(p.search(name) for p in COMPOSITE_NAME_RE):
            excl(fid, name, "composite_name"); continue

        if any(p.search(name) for p in EXCL_NAME_RE_EXTENDED):
            excl(fid, name, "irrelevant_ingredient"); continue

        # ── Nutriments plats ─────────────────────────────────────────────
        raw_nut = nut_index.get(fid, {})
        nutrients: dict = {f: raw_nut.get(f) for f in NUTRIENT_FIELDS}

        # alias alpha_tocopherol_mg = vitamin_e_mg (même ID 323)
        nutrients["alpha_tocopherol_mg"] = nutrients.get("vitamin_e_mg")

        # Champs calculés
        kcal = nutrients.get("energy_kcal")
        nutrients["energy_kj"] = round(kcal * KCAL_TO_KJ, 2) if kcal is not None else None
        sod  = nutrients.get("sodium_mg")
        nutrients["salt_g"] = round(sod / 1000 * SALT_SODIUM_RATIO, 4) if sod is not None else None

        # Champs absents CNF → None explicite pour rétrocompat
        for f in CNF_ABSENT:
            if f not in nutrients:
                nutrients[f] = None

        # ── State v2 (food_schema_v2) ─────────────────────────────────────
        state = parse_state_v2(name, category=grp_en, lang="en")
        rules_fired = state.pop("_rules_fired", [])

        l1 = state["process"]["level1"]
        l2 = state["process"]["level2"]
        # stats_state recalculé post-dedup (voir [3b/6]) pour éviter le biais
        # dénominateur qui produisait unknown_rate > 100%.

        # ── Clé de groupement ─────────────────────────────────────────────
        group_key, base_name = build_group_key(name)
        variant_key_str = state_variant_key(state)

        gk_vk = f"{group_key}/{variant_key_str}"
        seen_group_keys[gk_vk] += 1
        if seen_group_keys[gk_vk] > 1:
            variant_key_str = f"{variant_key_str}_{seen_group_keys[gk_vk]}"

        # ── food_id + variant_id ──────────────────────────────────────────
        food_id    = f"cnf_{fid}"
        variant_id = compute_variant_id(food_id, state)

        # ── Nutrients imbriqués (food_schema_v2) ──────────────────────────
        nutrients_obj = build_nutrients_object(
            nutrients,
            level1=l1,
            completeness_fields=_COMPLETENESS_FIELDS,
        )
        # Pas de extra= (CNF n'a pas d'amino acids ni lycopene)
        # Pas de detection_limits= (pas de valeurs sous seuil dans CNF)

        # ── Audit ─────────────────────────────────────────────────────────
        _audit_issues, _audit_score = run_audit(
            name, fid, food_id, nutrients, by_check, all_issues
        )
        quality_score = compute_quality_score(_audit_score, nutrients)

        # ── Diet profile (food_schema_v2) ─────────────────────────────────
        diet_profile = build_diet_profile(name, nutrients, category=grp_en)

        # ── Portions ──────────────────────────────────────────────────────
        portions = list(portions_map.get(fid, []))

        # ── Catégorie + Taxonomy ──────────────────────────────────────────
        category_obj = build_unified_category(grp_en, grp_fr)
        # ingredient_key : base_key canonique (via BASE_INGREDIENT_MAP si connu, sinon group_key)
        _bim_entry     = BASE_INGREDIENT_MAP.get(group_key, {})
        ingredient_key = _bim_entry.get("base_key") or group_key
        taxonomy_obj   = build_taxonomy(grp_en, bk=ingredient_key)

        # ── _quality (inclut state_inference) ────────────────────────────
        quality_meta = {
            "source":           "cnf_2015",
            "source_id":        int(fid) if fid is not None else None,
            "nut_count":        len([v for v in raw_nut.values() if v is not None]),
            "completeness_ix":  sum(1 for f in _COMPLETENESS_FIELDS
                                    if nutrients.get(f) is not None),
            "portions_count":   len(portions),
            "pipeline_version": "5.0",
            "created_at":       ts,
            "state_inference": {
                "confidence":  state["process"]["confidence"],
                "rules_fired": rules_fired,
                "raw_label":   name,
            },
            "unknown_fields": ["process.level1"] if l1 == "unknown" else [],
        }

        # ── Objet final ───────────────────────────────────────────────────
        item: dict = {
            # Identité schema v2
            "variant_id":   variant_id,
            "food_id":      food_id,
            "name": {
                "fr":        namef if namef else None,
                "en":        name  if name  else None,
                "canonical": name  if name  else namef,
            },
            "taxonomy":  taxonomy_obj,
            "state":     state,
            "nutrients": nutrients_obj,
            "sources": [{
                "db":        "CNF",
                "source_id": str(fid) if fid is not None else None,
                "raw_label": name,
                "version":   "2015",
            }],
            "origin": None,
            "grade":  None,
            "_quality":    quality_meta,
            # Champs rétrocompat pipeline ALIM
            "id":              food_id,
            "source":          "cnf",
            "source_id":       int(fid) if fid is not None else None,
            "name_fr":         namef if namef else None,
            "name_en":         name  if name  else None,
            "base_name":       base_name,
            "scientific_name": None,
            "group_key":       group_key,
            "variant_key":     variant_key_str,
            "is_generic":      False,
            "category":        category_obj,
            "diet_profile":    diet_profile,
            "refuse_percent":  refuse_map.get(fid),
            "jones_factor":    None,
            "detection_limits":{},
            "portions":        portions,
            "yield_data":      dict(yield_map.get(fid, {})),
            "_usda_extra":     None,
            "quality_score":   quality_score,
            "_audit_issues":   _audit_issues if _audit_issues else None,
            "_audit_score":    _audit_score,
            # Nutriments plats rétrocompat
            **{k: v for k, v in nutrients.items()},
        }

        # Validation schéma (warnings seulement, pas bloquant)
        schema_errs = validate_food_item(item)
        if schema_errs:
            print(f"  [SCHEMA] {food_id} : {schema_errs}")

        foods_flat.append(item)

    # ── Déduplication _N overflow ─────────────────────────────────────────
    print("\n[3b/6] Deduplication _N overflow...")
    _seen_gk_state: dict[str, str] = {}
    foods_deduped:  list[dict]     = []
    dedup_removed = 0

    for item in foods_flat:
        gk         = item["group_key"]
        vk         = item["variant_key"]
        slot       = f"{gk}/{vk}"
        if slot not in _seen_gk_state:
            _seen_gk_state[slot] = item["food_id"]
            foods_deduped.append(item)
        else:
            current_best_id = _seen_gk_state[slot]
            current_best = next(
                (f for f in foods_deduped if f["food_id"] == current_best_id), None
            )
            if current_best and item.get("quality_score", 0) > current_best.get("quality_score", 0):
                foods_deduped.remove(current_best)
                foods_deduped.append(item)
                _seen_gk_state[slot] = item["food_id"]
            else:
                dedup_removed += 1

    foods_flat = foods_deduped
    print(f"    Supprimes par deduplication _N : {dedup_removed}")
    print(f"    Items restants apres dedup     : {len(foods_flat)}")

    # ── Recalcul stats_state POST-DEDUP (fix unknown_rate > 100%) ─────────
    # Avant ce fix, stats_state etait calcule sur les ~2086 items pre-dedup
    # avec foods_flat=776 comme denominateur => taux aberrants (153.4%).
    stats_state.clear()
    for _item in foods_flat:
        _l1 = _item["state"]["process"]["level1"]
        _l2 = _item["state"]["process"].get("level2")
        stats_state[f"level1_{_l1}"] += 1
        if _l2:
            stats_state[f"level2_{_l2}"] += 1

    # ── Groupement + arbre multi-level ───────────────────────────────────
    print("\n[4/6] Groupement + arbre multi-level...")

    all_nut_fields = (
        NUTRIENT_FIELDS + COMPUTED_FIELDS + ["alpha_tocopherol_mg"] + CNF_ABSENT
    )

    base_groups: dict[str, list] = defaultdict(list)
    for item in foods_flat:
        entry = BASE_INGREDIENT_MAP.get(item["group_key"], {})
        base_key = entry.get("base_key", item["group_key"])
        extra_dims = entry.get("extra_dims", {})
        for dim, val in extra_dims.items():
            if dim in ("process.level1", "process.level2"):
                continue
            if item["state"].get(dim) is None:
                item["state"][dim] = val
        base_groups[base_key].append(item)

    groups_dict: dict = {}
    for base_key, base_foods in base_groups.items():
        entry = BASE_INGREDIENT_MAP.get(base_foods[0]["group_key"], {})
        name_fr = entry.get("name_fr") or (
            (base_foods[0].get("name_fr", "") or "").split(",")[0].strip() or None
        )
        name_en = entry.get("name_en") or base_foods[0].get("base_name") or base_key
        category = base_foods[0].get("category", {})
        extra_fields = {"taxonomy": base_foods[0].get("taxonomy")}

        groups_dict[base_key] = build_variant_tree(
            foods=base_foods,
            base_key=base_key,
            name_fr=name_fr,
            name_en=name_en,
            category=category,
            source_name="cnf",
            extra_fields=extra_fields,
        )

    variant_conflicts: list[dict] = []

    # ── Stats + meta ──────────────────────────────────────────────────────
    usable_count        = sum(1 for f in foods_flat if f["_audit_score"].get("usable", True))
    foods_with_portions = sum(1 for f in foods_flat if f["portions"])

    field_coverage = {}
    for field in all_nut_fields:
        cnt = sum(1 for f in foods_flat if f.get(field) is not None)
        field_coverage[field] = {
            "count": cnt,
            "pct":   round(cnt / len(foods_flat) * 100, 1) if foods_flat else 0,
        }

    _key_fields = ["energy_kcal", "energy_kj", "protein_g", "carbs_g", "fat_g",
                   "fiber_g", "sugar_g", "salt_g", "sodium_mg", "calcium_mg",
                   "iron_mg", "vitamin_c_mg", "folate_dfe_ug", "choline_mg"]
    field_source_coverage = {
        f: (["cnf"] if any(item.get(f) is not None for item in foods_flat) else [])
        for f in _key_fields
    }
    for f in ["energy_kcal_jones", "energy_kj_jones", "protein_n625_g", "iodine_ug"]:
        field_source_coverage[f] = []

    unknown_rate  = stats_state.get("level1_unknown", 0) / max(len(foods_flat), 1) * 100
    cooked_count  = stats_state.get("level1_cooked", 0)
    cooked_generic = stats_state.get("level2_cooked_generic", 0)
    cg_rate       = cooked_generic / max(cooked_count, 1) * 100

    l2_counts = sorted(
        ((k.replace("level2_", ""), v) for k, v in stats_state.items() if k.startswith("level2_")),
        key=lambda x: -x[1],
    )

    meta: dict = {
        "schema_version": "6.0",
        "schema_family":  "unified_food",
        "generated_at":   ts,
        "sources": {
            "cnf": {
                "title":       "Sante Canada CNF 2015",
                "url":         "https://www.canada.ca/en/health-canada/services/food-nutrition/healthy-eating/nutrient-data.html",
                "total_input": total_input,
            }
        },
        "total_foods":           len(foods_flat),
        "nutrient_fields":       all_nut_fields,
        "field_source_coverage": field_source_coverage,
        "stats": {
            "total_kept":           len(foods_flat),
            "total_excluded":       sum(exclusions.values()),
            "usable_count":         usable_count,
            "physical_errors":      sum(
                1 for f in foods_flat if f["_audit_score"].get("physical_errors", 0) > 0
            ),
            "groups_count":         len(groups_dict),
            "multi_variant_groups": len(variant_conflicts),
            "foods_with_portions":  foods_with_portions,
            "dedup_removed":        dedup_removed,
            "exclusions_by_reason": dict(exclusions),
            "state_stats": {
                "level1_raw":              stats_state.get("level1_raw", 0),
                "level1_cooked":           cooked_count,
                "level1_unknown":          stats_state.get("level1_unknown", 0),
                "unknown_rate_pct":        round(unknown_rate, 1),
                "cooked_generic_rate_pct": round(cg_rate, 1),
                "top_level2":              dict(l2_counts[:15]),
            },
        },
        "schema_notes": {
            "state_v2": (
                "parse_state_v2 délégué à food_schema_v2 v2.1. "
                "process.level1 ∈ {raw, cooked, unknown}. "
                "Règles R2-R8 appliquées."
            ),
            "nutrients_v2": (
                "build_nutrients_object délégué à food_schema_v2. "
                "proteins_detail tout null (CNF 2015 sans amino acids). "
                "Champs plats conservés à la racine pour rétrocompat pipeline ALIM."
            ),
            "variant_id": (
                "SHA-1(food_id + state canonique), tronqué 12 chars. "
                "Déterministe et identique USDA/CIQUAL."
            ),
            "cnf_absent": (
                "Champs CIQUAL/USDA absents CNF, toujours null : " + ", ".join(CNF_ABSENT)
            ),
            "taxonomy_v1": (
                "taxonomy = objet { group_id, group_label, subgroup_id, subgroup_label, _legacy_l1 }. "
                "Priorité : taxonomie dynamique (taxonomy_session_*.json v3) > slugify(grp_en) > "
                "_CNF_TAXONOMY_L1 statique. _legacy_l1 conservé pour rétrocompat pipeline existant."
            ),
        },
    }

    payload: dict = {
        "_meta":             meta,
        "groups":            groups_dict,
        "foods_flat":        foods_flat,
        "variant_conflicts": variant_conflicts,
    }

    # ── Rapport ──────────────────────────────────────────────────────────
    print(f"\n[5/6] Rapport")
    print(f"    Input FOOD_NAME           : {total_input:>5}")
    for reason, cnt in sorted(exclusions.items(), key=lambda x: -x[1]):
        print(f"    Exclus {reason:<28}: {cnt:>5}")
    print(f"    {'-'*40}")
    print(f"    Conserves avant dedup     : {len(foods_flat) + dedup_removed:>5}")
    print(f"    Supprimes dedup _N        : {dedup_removed:>5}")
    print(f"    Conserves final           : {len(foods_flat):>5}")
    print(f"    dont usable               : {usable_count:>5}")
    print(f"    Avec portions             : {foods_with_portions:>5}")
    print(f"    Groupes                   : {len(groups_dict):>5}")
    print(f"    Multi-variants            : {len(variant_conflicts):>5}")
    print(f"    Issues audit total        : {len(all_issues):>5}")
    print(f"\n    --- État process (level1) ---")
    for key in ("level1_raw", "level1_cooked", "level1_unknown"):
        print(f"    {key:<35}: {stats_state.get(key, 0):>5}")
    print(f"    unknown_rate              : {unknown_rate:.1f}%  (cible < 5%)")
    print(f"    cooked_generic_rate       : {cg_rate:.1f}%  (cible < 10%)")
    print(f"\n    --- Top level2 ---")
    for l2, cnt in l2_counts[:12]:
        print(f"      {l2:<30} : {cnt:>5}")
    print(f"\n    Couverture nutriments (top 12) :")
    top_fields = sorted(field_coverage.items(), key=lambda x: -x[1]["count"])
    for field, cov in top_fields[:12]:
        bar = "#" * int(cov["pct"] / 5)
        print(f"      {field:<32} {cov['count']:>5}/{len(foods_flat)} "
              f"({cov['pct']:>5.1f}%)  {bar}")

    # ── Écriture ─────────────────────────────────────────────────────────
    if dry_run:
        print("\n[6/6] DRY-RUN — pas d'écriture.")
    else:
        print("\n[6/6] Ecriture...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        size_kb = output_path.stat().st_size // 1024
        print(f"    OK {output_path}  ({size_kb} Ko)")

    print("=" * 70)
    return payload


# =============================================================================
# 8. CLI
# =============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="Build cnf_full_v10.json v10.0 depuis CSV CNF (food_schema_v2)"
    )
    parser.add_argument("--output",   default=str(DEFAULT_OUTPUT))
    parser.add_argument("--dry-run",  action="store_true")
    parser.add_argument("--cnf-dir",  default=str(CNF_DIR))
    parser.add_argument(
        "--taxonomy",
        default=None,
        metavar="PATH",
        help=(
            "Chemin vers taxonomy_session_*.json. "
            "Si absent, auto-détection dans reference/. "
            "Injecte { group_id, group_label, subgroup_id, subgroup_label } "
            "dans chaque food object."
        ),
    )
    args = parser.parse_args()

    tax_path: Path | None = None
    if args.taxonomy:
        tax_path = Path(args.taxonomy)

    build(
        dry_run       = args.dry_run,
        output_path   = Path(args.output),
        cnf_dir       = Path(args.cnf_dir),
        taxonomy_path = tax_path,
    )


if __name__ == "__main__":
    main()
