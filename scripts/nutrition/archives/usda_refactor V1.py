"""
usda_refactor.py  v1.0
======================
Transforme FoodData_Central_foundation_food_json_2025-12-18.json
en usda_flat.json structuré comme ciqual_flat_v2 (v3.1).

Structure de sortie :
  groups        — dict { group_key -> { name_en, variants: { state -> food } } }
  foods_flat    — liste plate rétrocompatible
  variant_conflicts — conflits d'état résolus
  _meta         — métadonnées schema + statistiques + rapport d'exclusion

Alignements CIQUAL :
  - Champs nutrients identiques (mêmes noms de champs)
  - Même structure group / variants / state
  - Même format _audit + _audit_score
  - Même diet_profile (38 flags)
  - salt_g calculé depuis sodium_mg (convention CIQUAL)
  - Valeur nutriment : median si dataPoints > 1, sinon amount

Spécificités USDA :
  - _quality par variant : source, confidence, data_points, derivation_pct
  - _usda_extra : choline, biotin, trans-FA, fibres solubles/insolubles,
                  caroténoïdes, acides aminés clés
  - Énergie : priorité 1008 (direct) > 2048 (Atwater Spécifique) > 2047 (Atwater Général)
  - Vitamine D : priorité 1114 (µg) > 1110 (IU × 0.025)

Exclusions (avec rapport audit) :
  - Catégories non-végétariennes (boeuf, volaille, porc, poissons/fruits de mer, gibier)
  - Charcuteries et saucisses
  - Plats restauration (fried rice, tamale, etc.)
  - Produits de boulangerie transformés (pain commercial, biscuits)
  - Soupes et sauces composites
  - Produits industriels composites (fromage fondu, commercial, additifs…)
  - Produits sucrés/aromatisés ajoutés (yogurt aromatisé, soy milk sucré)

Usage :
  python usda_refactor.py \\
      --input  FoodData_Central_foundation_food_json_2025-12-18.json \\
      --output usda_flat.json \\
      --audit-report usda_flat_audit.json \\
      --log-excl usda_flat_excluded.json
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


# ============================================================================
# 1. NUTRIENT DEFS — alignement CIQUAL
#    (usda_nutrient_id, field_name_ciqual, conversion_factor)
#    Ordre = priorité : pour un même field_name, le premier ID trouvé gagne.
# ============================================================================
NUTRIENT_DEFS: list[tuple[int, str, float]] = [
    # ── Énergie ─────────────────────────────────────────────────────────────
    (1062, "energy_kj",   1.0),          # Energy kJ
    (1008, "energy_kcal", 1.0),          # Energy kcal [direct]
    (2048, "energy_kcal", 1.0),          # Atwater Specific [fallback]
    (2047, "energy_kcal", 1.0),          # Atwater General  [fallback]
    # ── Eau + macros ─────────────────────────────────────────────────────────
    (1051, "water_g",     1.0),
    (1003, "protein_g",   1.0),
    (1005, "carbs_g",     1.0),
    (1004, "fat_g",       1.0),
    (1063, "sugar_g",     1.0),          # Sugars Total (269.3) [priorité]
    (2000, "sugar_g",     1.0),          # Total Sugars (269)   [fallback]
    (1009, "starch_g",    1.0),
    (1079, "fiber_g",     1.0),
    (1007, "ash_g",       1.0),
    (1018, "alcohol_g",   1.0),
    # ── Fractions sucres ─────────────────────────────────────────────────────
    (1012, "fructose_g",   1.0),
    (1075, "galactose_g",  1.0),
    (1011, "glucose_g",    1.0),
    (1013, "lactose_g",    1.0),
    (1014, "maltose_g",    1.0),
    (1010, "saccharose_g", 1.0),
    # ── AG totaux ────────────────────────────────────────────────────────────
    (1258, "fa_saturated_g", 1.0),
    (1292, "fa_mufa_g",      1.0),
    (1293, "fa_pufa_g",      1.0),
    # ── AG saturés détaillés ─────────────────────────────────────────────────
    (1259, "fa_4_0_g",  1.0),
    (1260, "fa_6_0_g",  1.0),
    (1261, "fa_8_0_g",  1.0),
    (1262, "fa_10_0_g", 1.0),
    (1263, "fa_12_0_g", 1.0),
    (1264, "fa_14_0_g", 1.0),
    (1265, "fa_16_0_g", 1.0),
    (1266, "fa_18_0_g", 1.0),
    # ── AG insaturés (alignés CIQUAL) ────────────────────────────────────────
    (1315, "fa_18_1_oleic_g",    1.0),   # MUFA 18:1 c (oléique)
    (1316, "fa_18_2_linoleic_g", 1.0),   # PUFA 18:2 n-6
    (1404, "fa_18_3_ala_g",      1.0),   # PUFA 18:3 n-3 ALA
    (1271, "fa_20_4_ara_g",      1.0),   # PUFA 20:4 ARA
    (1278, "fa_20_5_epa_g",      1.0),   # PUFA 20:5 EPA
    (1272, "fa_22_6_dha_g",      1.0),   # PUFA 22:6 DHA
    (1253, "cholesterol_mg",     1.0),
    # ── Minéraux ─────────────────────────────────────────────────────────────
    (1087, "calcium_mg",    1.0),
    (1098, "copper_mg",     1.0),
    (1089, "iron_mg",       1.0),
    (1100, "iodine_ug",     1.0),
    (1090, "magnesium_mg",  1.0),
    (1101, "manganese_mg",  1.0),
    (1091, "phosphorus_mg", 1.0),
    (1092, "potassium_mg",  1.0),
    (1103, "selenium_ug",   1.0),
    (1093, "sodium_mg",     1.0),
    (1095, "zinc_mg",       1.0),
    # ── Vitamines ────────────────────────────────────────────────────────────
    (1106, "vitamin_a_rae_ug",    1.0),
    (1105, "retinol_ug",          1.0),
    (1107, "beta_carotene_ug",    1.0),
    (1114, "vitamin_d_ug",        1.0),   # µg [priorité]
    (1110, "vitamin_d_ug",        0.025), # IU → µg [fallback, 1 IU = 0.025 µg]
    (1111, "vitamin_d2_ug",       1.0),
    (1112, "vitamin_d3_ug",       1.0),
    (1109, "alpha_tocopherol_mg", 1.0),
    (1109, "vitamin_e_mg",        1.0),   # alias : USDA n'a pas de total-tocopherols
    (1185, "vitamin_k1_ug",       1.0),
    (1183, "vitamin_k2_ug",       1.0),
    (1162, "vitamin_c_mg",        1.0),
    (1165, "vitamin_b1_mg",       1.0),
    (1166, "vitamin_b2_mg",       1.0),
    (1167, "vitamin_b3_mg",       1.0),
    (1170, "vitamin_b5_mg",       1.0),
    (1175, "vitamin_b6_mg",       1.0),
    (1177, "folate_ug",           1.0),
    (1178, "vitamin_b12_ug",      1.0),
]

# Champs CIQUAL non-disponibles en USDA Foundation → toujours None
CIQUAL_ABSENT = [
    "energy_kj_jones", "energy_kcal_jones",
    "protein_n625_g", "polyols_g", "organic_acids_g",
    "chloride_mg", "folate_dfe_ug", "folate_intrinsic_ug", "folic_acid_ug",
    "vitamin_d3_ug",  # rare
    "vitamin_k2_ug",  # rare
]

# ============================================================================
# 2. USDA EXTRA DEFS — champs sans équivalent CIQUAL → _usda_extra
# ============================================================================
USDA_EXTRA_DEFS: list[tuple[int, str, float]] = [
    (1180, "choline_mg",            1.0),  # utile pour végans
    (1176, "biotin_ug",             1.0),
    (1257, "fa_trans_g",            1.0),  # AG trans totaux
    (1082, "fiber_soluble_g",       1.0),
    (1084, "fiber_insoluble_g",     1.0),
    (1071, "starch_resistant_g",    1.0),
    (1002, "nitrogen_g",            1.0),
    (1122, "lycopene_ug",           1.0),
    (1123, "lutein_zeaxanthin_ug",  1.0),
    (1108, "alpha_carotene_ug",     1.0),
    # Acides aminés essentiels (clés nutrition ALIM)
    (1210, "aa_tryptophan_g",    1.0),
    (1211, "aa_threonine_g",     1.0),
    (1212, "aa_isoleucine_g",    1.0),
    (1213, "aa_leucine_g",       1.0),
    (1214, "aa_lysine_g",        1.0),
    (1215, "aa_methionine_g",    1.0),
    (1217, "aa_phenylalanine_g", 1.0),
    (1219, "aa_valine_g",        1.0),
    (1220, "aa_arginine_g",      1.0),
    (1221, "aa_histidine_g",     1.0),
    # Phytostérols
    (1288, "phytosterol_beta_sitosterol_mg", 1.0),
    (1285, "phytosterol_stigmasterol_mg",    1.0),
    (1286, "phytosterol_campesterol_mg",     1.0),
    # Isoflavones (légumineuses)
    (1340, "isoflavone_daidzein_mg",  1.0),
    (1341, "isoflavone_genistein_mg", 1.0),
]


# ============================================================================
# 3. RÈGLES D'EXCLUSION
# ============================================================================

# Catégories USDA entièrement exclues
EXCL_CATEGORIES_HARD: set[str] = {
    # Non-végétarien
    "Beef Products",
    "Poultry Products",
    "Pork Products",
    "Finfish and Shellfish Products",
    "Lamb, Veal, and Game Products",
    "Sausages and Luncheon Meats",
    # Plats composites / produits transformés complexes
    "Restaurant Foods",
    "Baked Products",           # pain commercial, biscuits
    "Soups, Sauces, and Gravies",
}

# Codes individuels exclus (hors catégories ci-dessus)
EXCL_CODES_HARD: set[int] = set()
# Note : les cas particuliers sont couverts par COMPOSITE_NAME_RE ci-dessous.

# Patterns sur la description → produit composite ou transformé industriel
COMPOSITE_NAME_RE: list[re.Pattern] = [re.compile(p, re.I) for p in [
    r"\bcommercially\s+prepared\b",  # pain commercial, etc.
    r"\bcommercial\b",               # hummus commercial, préparation industrielle
    r"\bpasteurized\s+process\b",    # fromages fondus industriels
    r"\brestaurant\b",               # plats/portions restauration
    r"\bwith\s+additives\b",         # chicken ground with additives
    r"\bsweet\s+and\s+sour\b",       # plat composite
    r"\bfried\s+rice\b",             # riz composite
    r"\btamale\b|\bpupusa\b",        # plats composites latino
    r"\bsweetened\b",                # produits avec sucre ajouté (soy milk sweetened…)
    r"\bstrawberry\b|\bchocolate\s+flavor",  # yogurts aromatisés
    r"\bbreaded\b",                  # produit pané (composite farine + aliment)
]]


# ============================================================================
# 4. DÉTECTION D'ÉTAT CULINAIRE (English)
#    Patterns ordonnés du plus spécifique au plus générique.
#    Matching sur description désaccentuée.
# ============================================================================
_STATE_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bsteamed\b",                            re.I), "steamed"),
    (re.compile(r"\boven[- ]cooked\b|\bbaked\b",           re.I), "oven_cooked"),
    (re.compile(r"\bboiled\b|\bsimmered\b",                re.I), "boiled"),
    (re.compile(r"\bpan[- ]broiled\b|\bpan[- ]fried\b|\bsauteed?\b", re.I), "pan_fried"),
    (re.compile(r"\bgrilled?\b|\bbroiled?\b",              re.I), "grilled"),
    (re.compile(r"\braasted\b|\broasted\b",                re.I), "roasted"),
    (re.compile(r"\bbraised\b",                            re.I), "braised"),
    (re.compile(r"\bfried\b(?!\s+rice)",                   re.I), "fried"),
    (re.compile(r"\bcanned\b",                             re.I), "canned"),
    (re.compile(r"\bin\s+(?:olive\s+)?oil\b",              re.I), "canned_in_oil"),
    (re.compile(r"\bdrainied?\b|\bdrained\b",              re.I), "canned"),
    (re.compile(r"\bpowdered?\b|\bdehydrated\b",           re.I), "dried"),
    (re.compile(r"\bdried?\b|\bdry\b(?!\s+matter)",        re.I), "dried"),
    (re.compile(r"\bfrozen\b",                             re.I), "frozen"),
    (re.compile(r"\bsmoked\b",                             re.I), "smoked"),
    (re.compile(r"\bfermented\b",                          re.I), "fermented"),
    (re.compile(r"\bpasteurized\b",                        re.I), "pasteurized"),
    (re.compile(r"\bcooked\b|\bprepared\b",                re.I), "cooked"),
    (re.compile(r"\braw\b",                                re.I), "raw"),
    (re.compile(r"\bfluid\b|\bliquid\b",                   re.I), "liquid"),
    (re.compile(r"\brefrigerated\b",                       re.I), "refrigerated"),
    (re.compile(r"\bshelf[- ]stable\b",                    re.I), "shelf_stable"),
    (re.compile(r"\bunsweetened\b",                        re.I), "unsweetened"),
    (re.compile(r"\bplain\b",                              re.I), "plain"),
    (re.compile(r"\bwhole\b(?!\s+milk|\s+grain)",          re.I), "whole"),
]


# ============================================================================
# 5. DIET PROFILE — règles (alignées CIQUAL)
# ============================================================================
NON_VEGAN_CATEGORIES = {"Dairy and Egg Products"}
NON_VEGAN_KW = [
    "milk", "cream", "cheese", "butter", "yogurt", "ghee",
    "whey", "casein", "lactose", "egg", "eggs", "honey",
    "beeswax", "gelatin",
]
VEGAN_OVERRIDE_KW = [
    "almond milk", "soy milk", "oat milk", "coconut milk",
    "plant-based", "vegan", "plant milk",
]

EGG_KW = ["egg", "eggs", "yolk", "egg white", "albumen", "meringue", "mayonnaise"]
EGG_CATEGORIES = {"Dairy and Egg Products"}

DAIRY_CATEGORIES = {"Dairy and Egg Products"}
DAIRY_KW = ["milk", "cream", "cheese", "butter", "yogurt", "ghee",
            "whey", "casein", "lactose", "kefir", "buttermilk"]
DAIRY_OVERRIDE_KW = ["almond milk", "soy milk", "oat milk", "coconut milk",
                     "cashew milk", "hemp milk", "plant milk"]

GLUTEN_KW = [
    "wheat", "rye", "barley", "triticale", "spelt", "kamut",
    "semolina", "bulgur", "farro", "flour", "bread", "pasta",
    "couscous", "seitan",
]
GLUTEN_FREE_CATEGORIES = {
    "Vegetables and Vegetable Products",
    "Fruits and Fruit Juices",
    "Nut and Seed Products",
    "Fats and Oils",
    "Legumes and Legume Products",  # par défaut (sauf produits à base de blé)
    "Sweets",
    "Beverages",
}

NUTS_KW = [
    "almond", "cashew", "walnut", "pecan", "pistachio", "hazelnut",
    "macadamia", "pine nut", "brazil nut", "chestnut", "nut ",
]
NUTS_FREE_CATEGORIES = {
    "Vegetables and Vegetable Products",
    "Fruits and Fruit Juices",
    "Cereal Grains and Pasta",
    "Legumes and Legume Products",
    "Dairy and Egg Products",
    "Fats and Oils",
}

SOY_KW = ["soy", "soya", "tofu", "tempeh", "edamame", "miso", "natto"]
SOY_FREE_CATEGORIES = {
    "Vegetables and Vegetable Products",
    "Fruits and Fruit Juices",
    "Cereal Grains and Pasta",
    "Nut and Seed Products",
    "Dairy and Egg Products",
    "Fats and Oils",
}

FERMENTED_KW = [
    "yogurt", "kefir", "buttermilk", "fermented", "miso",
    "tempeh", "natto", "kombucha", "vinegar",
]

WHOLE_FOOD_KW_POS = ["raw", "whole", "fresh", "dried", "sprouted"]
WHOLE_FOOD_KW_NEG = [
    "process", "fortified", "enriched", "instant", "commercial",
    "pasteurized process", "low-fat", "nonfat", "fat-free",
]
WHOLE_FOOD_CATEGORIES = {
    "Vegetables and Vegetable Products",
    "Fruits and Fruit Juices",
    "Nut and Seed Products",
    "Spices and Herbs",
}

# ── Seuils nutritionnels (alignés CIQUAL) ─────────────────────────────────
THRESHOLDS: dict[str, tuple[str, float, str]] = {
    "high_protein":    ("protein_g",    12.0, ">="),
    "high_fiber":      ("fiber_g",       6.0, ">="),
    "low_fat":         ("fat_g",          3.0, "<="),
    "low_sugar":       ("sugar_g",        5.0, "<="),
    "low_sodium":      ("sodium_mg",    120.0, "<="),
    "high_calcium":    ("calcium_mg",   120.0, ">="),
    "high_iron":       ("iron_mg",        2.1, ">="),
    "high_magnesium":  ("magnesium_mg",  56.0, ">="),
    "high_zinc":       ("zinc_mg",        1.5, ">="),
    "high_vit_c":      ("vitamin_c_mg",  12.0, ">="),
    "high_vit_d":      ("vitamin_d_ug",   1.5, ">="),
    "high_vit_b12":    ("vitamin_b12_ug", 0.375, ">="),
    "high_folate":     ("folate_ug",      30.0, ">="),
    "high_potassium":  ("potassium_mg",  350.0, ">="),
}

OMEGA3_ALA_THRESHOLD = 1.1   # g/100g
OMEGA3_EPA_DHA_MIN   = 0.3   # g/100g (EPA + DHA)


# ============================================================================
# 6. AUDIT — constantes (alignées CIQUAL)
# ============================================================================
ENERGY_FACTORS_KJ = {
    "protein_g":     17,
    "carbs_g":       17,
    "fat_g":         37,
    "fiber_g":        8,
    "alcohol_g":     29,
    "polyols_g":     10,  # absent USDA → 0
}
SALT_SODIUM_RATIO   = 2.542
MASS_BALANCE_WARN_G = 15.0
MASS_BALANCE_ERR_G  = 30.0
ENERGY_TOLERANCE    = 0.20
FA_BALANCE_TOL      = 0.10

SEVERITY_CLASS: dict[str, str] = {
    "negative_values":  "physical_error",
    "sugar_vs_carbs":   "physical_error",
    "energy_check":     "data_quality",   # acides organiques/facteurs Atwater → bruit normal
    "fa_balance":       "major_quality",
    "sugar_subfractions": "major_quality",
    "salt_sodium":      "data_quality",
    "mass_balance":     "physical_error",  # si error; major_quality si warning
    "omega_vs_pufa":    "data_quality",
    "vit_d_subforms":   "data_quality",
    "vit_e_tocopherol": "data_quality",
}

def get_severity_class(check: str, severity: str) -> str:
    if check == "mass_balance":
        if severity == "error":
            return "physical_error"
        elif severity == "warning":
            return "major_quality"
        else:           # "info" — base sèche, non applicable
            return "info"
    return SEVERITY_CLASS.get(check, "info")


# ── Nutriments clés pour le calcul de complétude ──────────────────────────
_COMPLETENESS_FIELDS: list[str] = [
    # Macros (6)
    "energy_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "water_g",
    # Minéraux clés (3)
    "sodium_mg", "calcium_mg", "iron_mg",
    # Vitamines clés (3)
    "vitamin_c_mg", "folate_ug", "vitamin_d_ug",
    # Lipides (2)
    "fa_saturated_g", "fa_18_3_ala_g",
]  # total = 14 champs


def compute_quality_score(
    quality_meta: dict,
    audit_score: dict,
    nutrients: dict,
) -> float:
    """Calcule un score qualité global [0, 1] par variant.

    Composantes :
      analytical_pct  (0–0.35) : fraction des nutriments mesurés analytiquement
      completeness    (0–0.35) : couverture des 14 nutriments clés
      audit           (0–0.30) : absence d'issues — physical_error = 0.0 direct

    Formule :
      score = anal_score + completeness_score + audit_score_component
    """
    # 1. Composante analytique
    anal_pct  = quality_meta.get("analytical_pct", 0.0)
    anal_comp = anal_pct * 0.35

    # 2. Composante complétude
    present      = sum(1 for f in _COMPLETENESS_FIELDS if nutrients.get(f) is not None)
    completeness = present / len(_COMPLETENESS_FIELDS)
    comp_score   = completeness * 0.35

    # 3. Composante audit
    n_physical = audit_score.get("physical_errors", 0)
    n_major    = audit_score.get("major_quality",   0)
    n_dq       = audit_score.get("data_quality",    0)

    if n_physical > 0:
        audit_comp = 0.0
    else:
        # Chaque major_quality coûte 0.05, chaque data_quality coûte 0.01
        penalty    = min(n_major * 0.05 + n_dq * 0.01, 0.30)
        audit_comp = round(0.30 - penalty, 4)

    return round(min(anal_comp + comp_score + audit_comp, 1.0), 3)


# ============================================================================
# 7. UTILITAIRES
# ============================================================================
_ACCENT_MAP: list[tuple[str, str]] = [
    ("\u00e0","a"),("\u00e2","a"),("\u00e4","a"),
    ("\u00e9","e"),("\u00e8","e"),("\u00ea","e"),("\u00eb","e"),
    ("\u00ee","i"),("\u00ef","i"),
    ("\u00f4","o"),("\u00f6","o"),
    ("\u00f9","u"),("\u00fb","u"),("\u00fc","u"),
    ("\u00e7","c"),("\u00f1","n"),
]

def _deaccent(text: str) -> str:
    for src, dst in _ACCENT_MAP:
        text = text.replace(src, dst)
    return text

def slugify(text: str) -> str:
    """Génère un group_key ASCII snake_case depuis un nom anglais."""
    t = _deaccent(text.lower())
    t = re.sub(r"[,;()\[\]'\".:/\\%]", " ", t)
    t = re.sub(r"[^a-z0-9\s_-]", "", t)
    t = re.sub(r"[\s_-]+", "_", t).strip("_")
    return t[:80]


# Termes USDA génériques (premier mot avant virgule) qui nécessitent un 2e niveau
# pour construire un group_key utile.
# Ex : "Oil, olive, extra virgin" → group_key "oil_olive" et non "oil"
GENERIC_USDA_PREFIXES: set[str] = {
    "oil", "beans", "bean", "flour", "cheese", "milk", "nuts", "butter",
    "cream", "yogurt", "mushroom", "mushrooms", "pepper", "peppers",
    "squash", "lettuce", "cabbage", "apple", "apples", "tomato", "tomatoes",
    "potato", "potatoes", "onion", "onions", "corn", "spinach", "broccoli",
    "carrot", "carrots", "egg", "eggs", "rice", "wheat", "berries", "berry",
    "beans dry",
}

# Qualificatifs d'état à ignorer lors de la recherche du différentiateur
_STATE_STOP_SLUGS: set[str] = {
    slugify(s) for s in [
        "dry", "dried", "raw", "cooked", "fresh", "frozen", "canned",
        "whole", "plain", "fluid", "unsweetened", "refrigerated",
        "low fat", "nonfat", "full fat", "fat free", "reduced fat",
        "boiled", "steamed", "grilled", "roasted", "fried",
        "uncooked", "unprepared", "pasteurized", "dehydrated",
    ]
}

_PAREN_RE = re.compile(r"\([^)]*\)")


def _split_usda_parts(description: str) -> list[str]:
    """Split sur virgules en respectant les parenthèses."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for ch in description:
        if ch == "(":
            depth += 1
            current.append(ch)
        elif ch == ")":
            depth -= 1
            current.append(ch)
        elif ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        parts.append("".join(current).strip())
    return [p for p in parts if p]


def build_usda_group_key(description: str) -> tuple[str, str]:
    """Construit (group_key, base_name) depuis une description USDA.

    Pour les termes génériques (oil, beans, flour…), inclut le 2e niveau
    significatif (en ignorant les qualificatifs d'état pur).

    Exemples :
      "Oil, olive, extra virgin"               -> ("oil_olive",        "Oil, olive")
      "Beans, Dry, Medium Red (0% moisture)"   -> ("beans_medium_red", "Beans, Medium Red")
      "Cheese, cheddar"                        -> ("cheese_cheddar",   "Cheese, cheddar")
      "Peanut butter, creamy"                  -> ("peanut_butter",    "Peanut butter")
      "Milk, whole, 3.25% milkfat"             -> ("milk_whole",       "Milk, whole")
    """
    parts = _split_usda_parts(description)
    if not parts:
        return slugify(description)[:80], description

    first = parts[0].strip()
    first_lower = first.lower()

    if first_lower in GENERIC_USDA_PREFIXES and len(parts) >= 2:
        for second in parts[1:]:
            second_clean = _PAREN_RE.sub("", second).strip()
            s_slug = slugify(second_clean)
            if s_slug and s_slug not in _STATE_STOP_SLUGS:
                # Prendre seulement le premier mot du qualificatif pour la clé
                # (évite les clés trop longues : "3.25% milkfat" → "3_25_milkfat")
                key_part = second_clean.split()[0] if second_clean.split() else second_clean
                base_name = f"{first}, {second_clean}"
                return slugify(f"{first} {key_part}"), base_name
        # Tous les qualificatifs sont des états → garder le 2e quand même
        second_clean = _PAREN_RE.sub("", parts[1]).strip()
        key_part = second_clean.split()[0] if second_clean.split() else second_clean
        base_name = f"{first}, {second_clean}"
        return slugify(f"{first} {key_part}"), base_name

    return slugify(first), first


def extract_base_name(description: str) -> tuple[str, str]:
    """Sépare 'Base, qualificatifs...' en (base_name, qualifier_str).

    Respecte les parenthèses. Exemples :
      "Chicken, breast, raw"                  -> ("Chicken", "breast, raw")
      "Beans, Dry, Medium Red (0% moisture)"  -> ("Beans", "Dry, Medium Red (0% moisture)")
      "Oil, olive, extra virgin"              -> ("Oil", "olive, extra virgin")
      "Peanut butter, creamy"                 -> ("Peanut butter", "creamy")
    """
    depth = 0
    for i, ch in enumerate(description):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            base = description[:i].strip()
            qual = description[i+1:].strip()
            return base, qual
    return description.strip(), ""


def parse_state(description: str) -> str:
    """Détecte l'état culinaire dans la description USDA."""
    for pat, state in _STATE_PATTERNS:
        if pat.search(description):
            return state
    return "default"


def parse_usda_name(description: str) -> tuple[str, str, str, str]:
    """Retourne (group_key, base_name, qualifier_str, state)."""
    group_key, base_name = build_usda_group_key(description)
    _, qual = extract_base_name(description)
    state = parse_state(description)
    return group_key, base_name, qual, state


# ============================================================================
# 8. EXTRACTION DES NUTRIMENTS
# ============================================================================
def extract_nutrients(
    food: dict,
) -> tuple[dict, dict, dict, dict]:
    """Retourne (nutrients, detection_limits, _usda_extra, _quality_meta).

    Stratégie de valeur :
      - si dataPoints > 1 ET median disponible → utiliser median
      - sinon → utiliser amount
    Priorité de champ : premier ID dans NUTRIENT_DEFS gagne.
    """
    nut_by_id: dict[int, dict] = {
        n["nutrient"]["id"]: n
        for n in food.get("foodNutrients", [])
    }

    nutrients: dict[str, float | None] = {}
    detection_limits: dict[str, float] = {}
    seen_fields: set[str] = set()

    # Compteurs qualité
    total_nuts = 0
    analytical_count = 0
    max_dp = 0
    median_used_count = 0

    for (usda_id, field, conv) in NUTRIENT_DEFS:
        if field in seen_fields:
            continue
        n = nut_by_id.get(usda_id)
        if n is None:
            continue

        dp     = n.get("dataPoints", 0) or 0
        median = n.get("median")
        amount = n.get("amount")

        if dp > 1 and median is not None:
            val = median * conv
            median_used_count += 1
        elif amount is not None:
            val = amount * conv
        else:
            continue

        nutrients[field] = round(val, 6) if val else val
        seen_fields.add(field)
        total_nuts += 1
        if dp > max_dp:
            max_dp = dp

        deriv = n.get("foodNutrientDerivation", {}).get("code", "?")
        if deriv in ("A", "AS"):
            analytical_count += 1

    # salt_g depuis sodium_mg (convention CIQUAL)
    if "sodium_mg" in nutrients and nutrients["sodium_mg"] is not None:
        nutrients["salt_g"] = round(nutrients["sodium_mg"] / 1000 * SALT_SODIUM_RATIO, 4)

    # Champs absents USDA → explicitement None pour compatibilité CIQUAL
    for field in CIQUAL_ABSENT:
        if field not in nutrients:
            nutrients[field] = None

    # _usda_extra
    extra: dict[str, float | None] = {}
    seen_extra: set[str] = set()
    for (usda_id, field, conv) in USDA_EXTRA_DEFS:
        if field in seen_extra:
            continue
        n = nut_by_id.get(usda_id)
        if n is None:
            continue
        dp     = n.get("dataPoints", 0) or 0
        median = n.get("median")
        amount = n.get("amount")
        val = (median * conv if (dp > 1 and median is not None) else
               (amount * conv if amount is not None else None))
        if val is not None:
            extra[field] = round(val, 6) if val else val
            seen_extra.add(field)

    # _quality
    anal_pct = round(analytical_count / total_nuts, 3) if total_nuts else 0.0
    confidence = 0.60
    if anal_pct >= 0.80:
        confidence += 0.15
    elif anal_pct >= 0.50:
        confidence += 0.08
    if max_dp >= 10:
        confidence += 0.15
    elif max_dp >= 5:
        confidence += 0.10
    elif max_dp >= 2:
        confidence += 0.05
    confidence = round(min(confidence, 1.0), 3)

    quality = {
        "source":         "usda_foundation_2025",
        "fdc_id":         food.get("fdcId"),
        "data_points_max": max_dp,
        "median_used":    median_used_count,
        "total_nutrients": total_nuts,
        "analytical_pct": anal_pct,
        "confidence":     confidence,
    }

    return nutrients, detection_limits, extra, quality


# ============================================================================
# 9. AUDIT
# ============================================================================
def run_audit(
    name_en: str,
    fdc_id: int,
    food_id: str,
    nutrients: dict,
    by_check: dict,
    all_issues: list,
) -> tuple[list[dict], dict]:
    """Exécute les checks de cohérence nutritionnelle.
    Retourne (_audit_issues, _audit_score).
    """
    issues: list[dict] = []

    def flag(check: str, sev: str, msg: str, **kw) -> None:
        sev_class = get_severity_class(check, sev)
        issues.append({
            "id": food_id, "fdc_id": fdc_id, "name_en": name_en,
            "severity": sev, "severity_class": sev_class,
            "check": check, "message": msg, **kw,
        })
        all_issues.append(issues[-1])
        by_check[check][sev + "s"] = by_check[check].get(sev + "s", 0) + 1

    def g(f: str) -> float | None:
        return nutrients.get(f)

    # 1. Valeurs négatives
    for field, val in nutrients.items():
        if val is not None and val < -0.001:
            flag("negative_values", "error",
                 f"Valeur négative : {field} = {val}")

    # 2. Sucres > glucides
    sug = g("sugar_g"); carbs = g("carbs_g")
    if sug is not None and carbs is not None and sug > carbs + 0.5:
        flag("sugar_vs_carbs", "error",
             f"sugar_g={sug} > carbs_g={carbs}")

    # 3. Mass balance — skip si base sèche explicite (0% moisture)
    dry_basis = "(0% moisture)" in name_en or "dry weight basis" in name_en.lower()
    if dry_basis:
        flag("mass_balance", "info",
             "Base sèche (0% moisture) — check mass_balance non applicable.")
    else:
        # USDA : carbs_g = "by difference" (100 - eau - protéines - lipides - cendres)
        # → fiber_g est inclus dans carbs_g → NE PAS l'additionner séparément
        if nutrients.get("carbs_g") is not None:
            components = ["water_g", "protein_g", "fat_g", "carbs_g", "ash_g", "alcohol_g"]
        else:
            components = ["water_g", "protein_g", "fat_g", "fiber_g", "ash_g", "alcohol_g"]
        vals = [g(f) for f in components if g(f) is not None]
        if len(vals) >= 4:
            total = sum(vals)
            delta = abs(100.0 - total)
            if delta > MASS_BALANCE_ERR_G:
                flag("mass_balance", "error",
                     f"Sigma macros={total:.1f} g/100g (écart={delta:.1f}g)")
            elif delta > MASS_BALANCE_WARN_G:
                flag("mass_balance", "warning",
                     f"Sigma macros={total:.1f} g/100g (écart={delta:.1f}g)")

    # 4. Énergie calculée vs déclarée (Atwater EU)
    # Priorité : kJ déclaré ; fallback : kcal déclaré converti en kJ (× 4.184)
    e_decl_kj = g("energy_kj")
    e_decl_kcal = g("energy_kcal")
    if not e_decl_kj and e_decl_kcal:
        e_decl_kj = e_decl_kcal * 4.184
    if e_decl_kj and e_decl_kj > 0:
        e_calc = sum(
            (g(f) or 0.0) * factor
            for f, factor in ENERGY_FACTORS_KJ.items()
            if g(f) is not None
        )
        if e_calc > 0:
            delta_pct = abs(e_decl_kj - e_calc) / e_decl_kj
            if delta_pct > ENERGY_TOLERANCE:
                src = "kJ" if g("energy_kj") else "kcal×4.184"
                flag("energy_check", "warning",
                     f"Energie déclarée={e_decl_kj:.0f} kJ ({src}) vs calculée={e_calc:.1f} kJ "
                     f"(delta={delta_pct*100:.1f}% > {ENERGY_TOLERANCE*100:.0f}%). "
                     "Cause probable : composants partiellement renseignés.",
                     delta_pct=round(delta_pct * 100, 1))

    # 5. Balance AG (SFA+MUFA+PUFA ≤ fat_g)
    fat = g("fat_g"); sfa = g("fa_saturated_g"); mufa = g("fa_mufa_g"); pufa = g("fa_pufa_g")
    if fat and sfa is not None and mufa is not None and pufa is not None:
        total_fa = sfa + mufa + pufa
        if total_fa > fat * (1 + FA_BALANCE_TOL) + 0.1:
            flag("fa_balance", "warning",
                 f"SFA+MUFA+PUFA={total_fa:.2f} > fat_g={fat:.2f} (+{FA_BALANCE_TOL*100:.0f}%)")

    # 6. Sel / Sodium
    salt = g("salt_g"); na = g("sodium_mg")
    if salt is not None and na is not None and na > 0:
        expected_salt = na / 1000 * SALT_SODIUM_RATIO
        if expected_salt > 0:
            delta = abs(salt - expected_salt) / expected_salt
            if delta > 0.15:
                flag("salt_sodium", "warning",
                     f"salt_g={salt:.3f} vs Na_mg/1000×2.542={expected_salt:.3f} "
                     f"(delta={delta*100:.1f}%)")

    # 7. Omega vs PUFA
    ala = g("fa_18_3_ala_g") or 0
    epa = g("fa_20_5_epa_g") or 0
    dha = g("fa_22_6_dha_g") or 0
    if pufa and pufa > 0:
        omega3 = ala + epa + dha
        linol  = g("fa_18_2_linoleic_g") or 0
        if (omega3 + linol) > pufa * (1 + 0.10) + 0.1:
            flag("omega_vs_pufa", "warning",
                 f"Σ oméga3+linol={omega3+linol:.3f} > fa_pufa={pufa:.3f}")

    # 8. Vitamine D sous-formes
    vd  = g("vitamin_d_ug")
    vd2 = g("vitamin_d2_ug")
    vd3 = g("vitamin_d3_ug")
    if vd and vd2 is not None and vd3 is not None:
        sub = vd2 + vd3
        if sub > vd * 1.05 + 0.01:
            flag("vit_d_subforms", "warning",
                 f"D2+D3={sub:.2f} > vitamin_d_ug={vd:.2f}")

    # Score
    n_physical = sum(1 for i in issues if i["severity_class"] == "physical_error")
    n_major    = sum(1 for i in issues if i["severity_class"] == "major_quality")
    n_dq       = sum(1 for i in issues if i["severity_class"] == "data_quality")
    score = {
        "physical_errors": n_physical,
        "major_quality":   n_major,
        "data_quality":    n_dq,
        "total":           len(issues),
        "usable":          n_physical == 0,
    }
    return issues, score


# ============================================================================
# 10. DIET PROFILE
# ============================================================================
def compute_diet_profile(
    category: str, name_en: str, nutrients: dict,
) -> dict:
    nl = name_en.lower()
    p: dict[str, bool | None] = {}

    # vegetarian : toujours True par construction (non-veg exclus en amont)
    p["vegetarian"] = True

    # vegan
    nv_cat  = category in NON_VEGAN_CATEGORIES
    nv_name = any(k in nl for k in NON_VEGAN_KW)
    vg_ov   = any(k in nl for k in VEGAN_OVERRIDE_KW)
    p["vegan"] = not ((nv_cat or nv_name) and not vg_ov)

    # egg_free
    eg_cat  = category in EGG_CATEGORIES
    eg_name = any(k in nl for k in EGG_KW)
    p["egg_free"] = not (eg_cat and eg_name) and not (not eg_cat and eg_name)

    # dairy_free
    d_cat = category in DAIRY_CATEGORIES
    d_nm  = any(k in nl for k in DAIRY_KW)
    d_ov  = any(k in nl for k in DAIRY_OVERRIDE_KW)
    p["dairy_free"] = not ((d_cat or d_nm) and not d_ov)

    # lactose_free (< 0.5 g/100g)
    lac = nutrients.get("lactose_g")
    if lac is not None:
        p["lactose_free"] = lac < 0.5
    else:
        p["lactose_free"] = p["dairy_free"]

    # gluten_free
    has_g = any(k in nl for k in GLUTEN_KW)
    if has_g:
        p["gluten_free"] = False
    elif category in GLUTEN_FREE_CATEGORIES:
        p["gluten_free"] = True
    else:
        p["gluten_free"] = None

    # nuts_free
    has_n = any(k in nl for k in NUTS_KW)
    if has_n:
        p["nuts_free"] = False
    elif category in NUTS_FREE_CATEGORIES:
        p["nuts_free"] = True
    else:
        p["nuts_free"] = None

    # soja_free
    has_s = any(k in nl for k in SOY_KW)
    if has_s:
        p["soja_free"] = False
    elif category in SOY_FREE_CATEGORIES:
        p["soja_free"] = True
    else:
        p["soja_free"] = None

    # gelatin_risk : absent des Foundation Foods retenus
    p["gelatin_risk"] = False

    # diabetic_friendly
    sugar = nutrients.get("sugar_g")
    carbs = nutrients.get("carbs_g")
    fiber = nutrients.get("fiber_g") or 0.0
    if sugar is not None and carbs is not None:
        p["diabetic_friendly"] = sugar <= 5.0 and (carbs - fiber) <= 15.0
    else:
        p["diabetic_friendly"] = None

    # Seuils nutritionnels
    for flag, (field, threshold, op) in THRESHOLDS.items():
        val = nutrients.get(field)
        if val is None:
            p[flag] = None
        else:
            p[flag] = (val >= threshold) if op == ">=" else (val <= threshold)

    # alcohol_free
    alc = nutrients.get("alcohol_g")
    p["alcohol_free"] = True if alc is None else (alc < 0.5)

    # whole_food
    has_neg = any(k in nl for k in WHOLE_FOOD_KW_NEG)
    has_pos = any(k in nl for k in WHOLE_FOOD_KW_POS)
    if has_neg:
        p["whole_food"] = False
    elif category in WHOLE_FOOD_CATEGORIES or has_pos:
        p["whole_food"] = True
    else:
        p["whole_food"] = None

    # fermented
    p["fermented"] = any(k in nl for k in FERMENTED_KW)

    # high_antioxidant (beta-carotène ou vitamine C)
    bc  = nutrients.get("beta_carotene_ug")
    vc  = nutrients.get("vitamin_c_mg")
    if (bc is not None and bc >= 600) or (vc is not None and vc >= 12):
        p["high_antioxidant"] = True
    elif bc is None and vc is None:
        p["high_antioxidant"] = None
    else:
        p["high_antioxidant"] = False

    # high_omega3
    ala = nutrients.get("fa_18_3_ala_g")
    epa = nutrients.get("fa_20_5_epa_g") or 0.0
    dha = nutrients.get("fa_22_6_dha_g") or 0.0
    if ala is not None:
        p["high_omega3"] = (ala >= OMEGA3_ALA_THRESHOLD) or \
                           ((epa + dha) >= OMEGA3_EPA_DHA_MIN)
    else:
        p["high_omega3"] = None

    return p


# ============================================================================
# 11. EXCLUSION
# ============================================================================
def should_exclude(fdc_id: int, category: str, description: str) -> tuple[bool, str]:
    if category in EXCL_CATEGORIES_HARD:
        return True, f"category:{category}"
    if fdc_id in EXCL_CODES_HARD:
        return True, "code:hard"
    for pat in COMPOSITE_NAME_RE:
        if pat.search(description):
            return True, f"composite_name:{pat.pattern[:40]}"
    return False, ""


# ============================================================================
# 12. GROUPEMENT PAR VARIANTS
# ============================================================================
def build_groups(
    foods: list[dict],
) -> tuple[dict, list[dict]]:
    """Construit la structure groups + retourne les conflits d'état."""
    groups: dict[str, dict] = {}
    conflicts: list[dict] = []

    for food in foods:
        gk   = food["group_key"]
        state = food["variant_key"]

        if gk not in groups:
            groups[gk] = {
                "name_en":  food["base_name"],
                "category": food["category"],
                "_meta": {
                    "variant_count": 0,
                    "variant_keys":  [],
                    "group_key":     gk,
                },
                "variants": {},
            }

        grp = groups[gk]

        # Conflit d'état
        if state in grp["variants"]:
            n = 2
            while f"{state}_{n}" in grp["variants"]:
                n += 1
            conflicts.append({
                "group_key":    gk,
                "original_state": state,
                "resolved_state": f"{state}_{n}",
                "fdc_id": food["fdcId"],
            })
            state = f"{state}_{n}"

        variant = {
            "usda_id":     food["id"],
            "fdc_id":      food["fdcId"],
            "name_en_full": food["description"],
            "nutrients":   food["nutrients"],
            "detection_limits": food.get("detection_limits", {}),
            "diet_profile": food.get("diet_profile", {}),
            "_quality":    food.get("_quality", {}),
            "_usda_extra": food.get("_usda_extra", {}),
            "portions":    food.get("portions", []),
        }
        if food.get("_audit"):
            variant["_audit"] = food["_audit"]
        if food.get("_audit_score"):
            variant["_audit_score"] = food["_audit_score"]

        grp["variants"][state] = variant
        grp["_meta"]["variant_count"] += 1
        grp["_meta"]["variant_keys"].append(state)

    return groups, conflicts


# ============================================================================
# 13. BUILD PRINCIPAL
# ============================================================================
def build(
    input_path: Path,
    output_path: Path,
    audit_path: Path | None = None,
    excl_path: Path | None = None,
    dry_run: bool = False,
) -> None:
    ts = datetime.now(timezone.utc).isoformat()
    print(f"\n[1/6] Lecture {input_path}...")

    with open(input_path, encoding="utf-8") as f:
        raw = json.load(f)
    source_foods: list[dict] = raw["FoundationFoods"]
    print(f"    {len(source_foods)} aliments dans la source USDA Foundation.")

    # ── Compteurs ─────────────────────────────────────────────────────────
    stats: dict = defaultdict(int)
    stats["total_usda"] = len(source_foods)
    excluded: list[dict] = []
    all_issues: list[dict] = []
    by_check: dict[str, dict] = defaultdict(lambda: defaultdict(int))

    print("\n[2/6] Filtrage + extraction...")
    foods: list[dict] = []

    for raw_food in source_foods:
        fdc_id   = raw_food.get("fdcId", 0)
        desc     = raw_food.get("description", "")
        category = raw_food.get("foodCategory", {}).get("description", "Unknown")

        excl, reason = should_exclude(fdc_id, category, desc)
        if excl:
            excluded.append({"fdcId": fdc_id, "description": desc,
                              "category": category, "reason": reason})
            top = reason.split(":")[0]
            stats[f"excl_{top}"] += 1
            stats["total_excl"] += 1
            continue

        stats["kept"] += 1

        # Extraction nutriments
        nutrients, dl, extra, quality = extract_nutrients(raw_food)

        # Parsing nom
        group_key, base_name, qualifier, state = parse_usda_name(desc)
        food_id    = f"usda_{fdc_id}"

        # Audit
        issues, audit_score = run_audit(
            desc, fdc_id, food_id, nutrients, by_check, all_issues
        )

        # Score qualité global
        quality["quality_score"] = compute_quality_score(quality, audit_score, nutrients)

        # Diet profile
        diet = compute_diet_profile(category, desc, nutrients)

        # Portions
        portions = []
        for p in raw_food.get("foodPortions", []):
            mu = p.get("measureUnit", {})
            gw = p.get("gramWeight") or p.get("value")
            if gw:
                portions.append({
                    "unit":  mu.get("name", "serving"),
                    "abbr":  mu.get("abbreviation", ""),
                    "grams_per_unit": round(gw, 3),
                })

        # Mise à jour stats audit
        if audit_score["total"] > 0:
            stats["foods_with_issues"] += 1
        for sev_class in ("physical_error", "major_quality", "data_quality", "info"):
            n = sum(1 for i in issues if i["severity_class"] == sev_class)
            stats[f"sevclass_{sev_class}"] += n
        for i in issues:
            stats[f"sev_{i['severity']}"] += 1

        if state == "default":
            stats["state_default"] += 1
        else:
            stats["state_detected"] += 1

        food_obj = {
            # Identifiants
            "id":          food_id,
            "fdcId":       fdc_id,
            "description": desc,
            "base_name":   base_name,
            "qualifier":   qualifier,
            "variant_key": state,
            "group_key":   group_key,
            "category":    category,
            # Nutritionnel
            "diet_profile": diet,
            "_quality":    quality,
            "portions":    portions,
            "detection_limits": dl,
            "_usda_extra": extra if extra else {},
            **nutrients,  # champs plats pour foods_flat
            # Audit
            **({ "_audit":       [i["check"] + ": " + i["message"] for i in issues],
                 "_audit_score": audit_score }
               if issues else {}),
        }
        # Stocker nutrients séparément pour la structure groups
        food_obj["nutrients"] = nutrients

        foods.append(food_obj)

    stats["total_groups"] = 0
    stats["multi_variant_groups"] = 0

    print(f"    Retenus : {stats['kept']} | Exclus : {stats['total_excl']}")
    print(f"\n[3/6] Construction groupes/variants...")

    groups, conflicts = build_groups(foods)
    stats["total_groups"]       = len(groups)
    stats["multi_variant_groups"] = sum(
        1 for g in groups.values() if g["_meta"]["variant_count"] > 1
    )
    stats["total_conflicts"] = len(conflicts)

    print(f"    {stats['total_groups']} groupes | "
          f"{stats['multi_variant_groups']} multi-variants | "
          f"{stats['total_conflicts']} conflits")

    total_excl = stats["total_excl"]

    print("\n[4/6] Rapport...")
    print(f"\n    --- Filtrage ---")
    print(f"    Total USDA Foundation             : {stats['total_usda']:>5}")
    print(f"    Exclusion catégorie non-veg       : {stats.get('excl_category',0):>5}")
    print(f"    Exclusion composite/industriel    : {stats.get('excl_composite_name',0):>5}")
    print(f"    Exclusion code individuel         : {stats.get('excl_code',0):>5}")
    print(f"    Total exclus                      : {total_excl:>5}")
    print(f"    Aliments conservés                : {stats['kept']:>5}")
    print(f"\n    --- Variants ---")
    print(f"    État détecté                      : {stats['state_detected']:>5}")
    print(f"    État 'default'                    : {stats['state_default']:>5}")
    print(f"\n    --- Audit ---")
    print(f"    Aliments avec issues              : {stats['foods_with_issues']:>5}")
    sev_physical = stats.get("sevclass_physical_error", 0)
    sev_major    = stats.get("sevclass_major_quality", 0)
    sev_dq       = stats.get("sevclass_data_quality", 0)
    if sev_physical > 0:
        print(f"    [CRIT] physical_error             : {sev_physical:>5}")
    print(f"    major_quality                     : {sev_major:>5}")
    print(f"    data_quality                      : {sev_dq:>5}")

    if dry_run:
        print("\n[DRY-RUN] Aucune écriture.")
        return

    print("\n[5/6] Sérialisation...")

    # foods_flat = liste plate (rétrocompat)
    foods_flat = []
    for f in foods:
        flat = {
            "id":          f["id"],
            "fdc_id":      f["fdcId"],
            "description": f["description"],
            "base_name":   f["base_name"],
            "variant_key": f["variant_key"],
            "group_key":   f["group_key"],
            "category":    f["category"],
            "diet_profile": f["diet_profile"],
            "_quality":    f["_quality"],
            "quality_score": f["_quality"].get("quality_score"),
            "portions":    f["portions"],
        }
        flat.update(f["nutrients"])
        if f.get("_audit_score"):
            flat["_audit_score"] = f["_audit_score"]
        foods_flat.append(flat)

    document = {
        "_meta": {
            "schema_version": "1.0",
            "schema_family":  "usda_flat",
            "generated_at":   ts,
            "source": {
                "title":     "USDA FoodData Central — Foundation Foods",
                "url":       "https://fdc.nal.usda.gov/",
                "file":      input_path.name,
                "total_foods_in_source": stats["total_usda"],
            },
            "stats": {
                "total_kept":          stats["kept"],
                "total_excluded":      stats["total_excl"],
                "total_groups":        stats["total_groups"],
                "multi_variant_groups": stats["multi_variant_groups"],
                "variant_conflicts":   stats["total_conflicts"],
                "foods_with_issues":   stats["foods_with_issues"],
                "by_severity_class": {
                    "physical_error": stats.get("sevclass_physical_error", 0),
                    "major_quality":  stats.get("sevclass_major_quality",  0),
                    "data_quality":   stats.get("sevclass_data_quality",   0),
                },
            },
            "filters_applied": [
                "non_vegetarian_categories",
                "restaurant_foods",
                "baked_products_commercial",
                "soups_sauces_composite",
                "composite_name_patterns",
                "sweetened_flavored_products",
            ],
            "schema_notes": {
                "structure_v1": (
                    "'groups' (clé principale) : dict { group_key -> { name_en, variants: { state -> food } } }. "
                    "États culinaires : raw, cooked, dried, frozen, steamed, boiled, canned, canned_in_oil, "
                    "smoked, grilled, roasted, fried, pan_fried, braised, pasteurized, plain, unsweetened, "
                    "liquid, refrigerated, shelf_stable, default."
                ),
                "nutrients_alignment": (
                    "Champs nutrients alignés CIQUAL v3.1. "
                    "Champs absents USDA Foundation (folate_dfe_ug, protein_n625_g, etc.) = null. "
                    "salt_g = sodium_mg/1000 × 2.542 (convention CIQUAL)."
                ),
                "vitamin_e_note": (
                    "vitamin_e_mg = alpha_tocopherol_mg (USDA Foundation n'a pas les équivalents "
                    "tocopherols totaux). Interprétation limitée vs CIQUAL."
                ),
                "energy_priority": (
                    "energy_kcal : ID 1008 (direct) > 2048 (Atwater Specific) > 2047 (Atwater General). "
                    "energy_kj   : ID 1062 uniquement."
                ),
                "value_strategy": (
                    "Valeur nutriment = median si dataPoints > 1, sinon amount. "
                    "Voir _quality.median_used et _quality.data_points_max par variant."
                ),
                "usda_extra_fields": (
                    "_usda_extra contient : choline, biotin, fa_trans, fibres solubles/insolubles, "
                    "caroténoïdes (lycopène, lutéine), acides aminés essentiels, phytostérols, isoflavones."
                ),
                "redundant_fields": {
                    "energy_kcal_vs_kj": "Priorité calculs : energy_kj. energy_kcal pour affichage.",
                    "alpha_tocopherol_vs_vitamin_e": (
                        "Identiques dans usda_flat (source unique ID 1109). "
                        "Préférer vitamin_e_mg pour cohérence cross-source avec CIQUAL."
                    ),
                },
            },
        },
        "groups":           groups,
        "foods_flat":       foods_flat,
        "variant_conflicts": conflicts,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(document, f, ensure_ascii=False, indent=2)
    print(f"    OK {output_path}  ({output_path.stat().st_size / 1_048_576:.1f} Mo)")

    if audit_path:
        by_sev = {
            "physical_error": stats.get("sevclass_physical_error", 0),
            "major_quality":  stats.get("sevclass_major_quality",  0),
            "data_quality":   stats.get("sevclass_data_quality",   0),
            "info":           stats.get("sevclass_info",           0),
        }
        audit_doc = {
            "_meta": {
                "schema_version":    "1.0",
                "generated_at":      ts,
                "total_checked":     stats["kept"],
                "foods_with_issues": stats["foods_with_issues"],
                "total_errors":      stats.get("sev_errors", 0),
                "total_warnings":    stats.get("sev_warnings", 0),
                "by_severity_class": by_sev,
                "interpretation": {
                    "physical_error": "Données inutilisables — corriger avant usage.",
                    "major_quality":  "Incohérences significatives — à vérifier.",
                    "data_quality":   "Bruit normal USDA — acceptable.",
                    "info":           "Informatif — aucune action requise.",
                },
                "by_check": {k: dict(v) for k, v in by_check.items()},
                "checks_documented": [
                    "negative_values   [physical_error] : aucun nutriment négatif",
                    "sugar_vs_carbs    [physical_error] : sucres inclus dans glucides",
                    "mass_balance      [physical_error/major_quality] : Σ macros ≈ 100g",
                    "energy_check      [data_quality]   : énergie kJ calculée vs déclarée (±20%) — acides organiques non couverts par Atwater",
                    "fa_balance        [major_quality]  : SFA+MUFA+PUFA ≤ fat_g (±10%)",
                    "salt_sodium       [data_quality]   : salt_g = Na/1000×2.542 (±15%)",
                    "omega_vs_pufa     [data_quality]   : Σ oméga ≤ fa_pufa (±10%)",
                    "vit_d_subforms    [data_quality]   : D_total ≥ D2+D3",
                ],
            },
            "excluded": excluded,
            "issues":   all_issues,
        }
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_doc, f, ensure_ascii=False, indent=2)
        print(f"    OK {audit_path}  "
              f"({len(all_issues)} issues | {len(excluded)} exclus)")

    if excl_path and excluded:
        excl_doc = {
            "_meta": {"generated_at": ts, "total_excluded": len(excluded)},
            "excluded": excluded,
        }
        with open(excl_path, "w", encoding="utf-8") as f:
            json.dump(excl_doc, f, ensure_ascii=False, indent=2)
        print(f"    OK {excl_path}  ({len(excluded)} aliments exclus)")

    print("\n[6/6] Terminé.")


# ============================================================================
# 14. POINT D'ENTRÉE
# ============================================================================
def main() -> None:
    ap = argparse.ArgumentParser(
        description="Transforme FoodData Central Foundation Foods → usda_flat.json v1.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--input",        "-i",
                    default="FoodData_Central_foundation_food_json_2025-12-18.json")
    ap.add_argument("--output",       "-o", default="usda_flat.json")
    ap.add_argument("--audit-report",       default=None, metavar="PATH")
    ap.add_argument("--log-excl",           default=None, metavar="PATH")
    ap.add_argument("--dry-run",            action="store_true")
    args = ap.parse_args()

    BASE_DIR = Path(__file__).resolve().parents[2]

    default_input = (
        BASE_DIR / "backend" / "data" / "nutrition" / "raw"
        / "FoodData_Central_foundation_food_json_2025-12-18.json"
    )

    xlsx = Path(args.input)
    if not xlsx.is_absolute():
        xlsx = Path.cwd() / xlsx
    if not xlsx.exists():
        xlsx = BASE_DIR / args.input
    if not xlsx.exists() and "FoodData_Central" in args.input:
        xlsx = default_input
    if not xlsx.exists():
        sys.exit(f"Fichier introuvable : {args.input}")

    build(
        input_path  = xlsx,
        output_path = Path(args.output),
        audit_path  = Path(args.audit_report) if args.audit_report else None,
        excl_path   = Path(args.log_excl)     if args.log_excl     else None,
        dry_run     = args.dry_run,
    )


if __name__ == "__main__":
    main()
