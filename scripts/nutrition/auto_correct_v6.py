"""
auto_correct_v6.py
═══════════════════════════════════════════════════════════════════════════
Mise à jour de auto_correct_v5.py → v6.0

Changements v6 vs v5 :
  ✦ FIELD_MAP étendu : 15 → 30 champs (aligné ontology_v6)
      Ajouts : starch_g, alcohol_g, iodine_ug, choline_mg, trans_fat_g,
               beta_carotene_ug, vitamin_k2_ug, polyols_g, organic_acids_g,
               omega3_ala_g, omega3_epa_g, omega3_dha_g
  ✦ Enrichissement des champs CALCULÉS (jamais couverts par les sources) :
      → nova_group          : règles NOVA 1-4 par category + ingredient_type
      → health_score        : score 0-100 depuis profil nutritionnel
      → bioavailability_protein : table statique par catégorie d'aliment
      → glycemic_load       : GI × carbs_g / 100
      → glycemic_index_source : "measured" | "estimated" selon origine GI
  ✦ scientific_name rempli depuis ontology_v6 (extrait de CIQUAL)
  ✦ Lit ontology_v6.json en priorité, fallback ontology_v5.json
  ✦ Seuils ajustés pour nouveaux champs (starch plus tolérant = 0.30)

Conservé intact de v5 :
  - Logique DRY_RUN
  - compute_delta(), pick_variant()
  - Backup automatique avant write
  - resolve_key() (~93% match rate)

Inputs  :  processed/nutrition_v2.json
           reference/ontology_v6.json (fallback: ontology_v5.json)
           ingredients/fr_to_en_mapping.json

Outputs :  reference/nutrition_corrected.json
           logs/corrections_log.json
═══════════════════════════════════════════════════════════════════════════
"""

import json
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parents[2]

MAPPING_FILE  = BASE_DIR / "backend/data/ingredients/fr_to_en_mapping.json"
ONTOLOGY_FILE = next(
    (p for p in [
        BASE_DIR / "backend/data/nutrition/reference/ontology_v6.json",
        BASE_DIR / "backend/data/nutrition/reference/ontology_v5.json",
    ] if p.exists()),
    BASE_DIR / "backend/data/nutrition/reference/ontology_v6.json"
)
INPUT_FILE    = BASE_DIR / "backend/data/nutrition/processed/nutrition_v2.json"
OUTPUT_FILE   = BASE_DIR / "backend/data/nutrition/reference/nutrition_corrected.json"
LOG_FILE      = BASE_DIR / "backend/data/logs/corrections_log.json"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

DRY_RUN = False

# ── Seuils de déviation acceptée avant correction ────────────────────────────
DEFAULT_THRESHOLDS: dict[str, float] = {
    # Macros
    "calories":      0.15,
    "protein":       0.20,
    "carbs":         0.20,
    "fat":           0.20,
    "fiber":         0.25,
    "sugar":         0.25,
    "starch":        0.30,   # ← nouveau v6 (sources hétérogènes)
    "alcohol":       0.20,   # ← nouveau v6
    # Lipides
    "saturated_fat": 0.25,
    "mufa":          0.25,
    "pufa":          0.25,
    "trans_fat":     0.30,   # ← nouveau v6
    "omega3":        0.30,
    "omega3_ala":    0.30,   # ← nouveau v6
    "omega3_epa":    0.35,   # ← nouveau v6
    "omega3_dha":    0.35,   # ← nouveau v6
    "omega6":        0.30,
    "cholesterol":   0.25,
    # Minéraux
    "sodium":        0.20,
    "calcium":       0.25,
    "iron":          0.30,
    "magnesium":     0.25,
    "phosphorus":    0.25,
    "potassium":     0.25,
    "zinc":          0.30,
    "copper":        0.30,
    "manganese":     0.30,
    "selenium":      0.35,
    "iodine":        0.35,   # ← nouveau v6 (très variable selon sol)
    # Vitamines
    "vitamin_a":     0.35,
    "beta_carotene": 0.40,   # ← nouveau v6
    "vitamin_d":     0.35,
    "vitamin_e":     0.30,
    "vitamin_k1":    0.30,
    "vitamin_k2":    0.35,   # ← nouveau v6
    "vitamin_c":     0.30,
    "vitamin_b1":    0.30,
    "vitamin_b2":    0.30,
    "vitamin_b3":    0.30,
    "vitamin_b5":    0.30,
    "vitamin_b6":    0.30,
    "folate":        0.30,
    "vitamin_b12":   0.35,
    "choline":       0.30,   # ← nouveau v6
    # Autres
    "polyols":       0.35,   # ← nouveau v6
    "organic_acids": 0.35,   # ← nouveau v6
}

# Correspondance clé nutrition_v2 → clé ontologie (courte)
FIELD_MAP: dict[str, str] = {
    # Macros
    "calories_kcal":          "calories",
    "protein_g":              "protein",
    "carbs_g":                "carbs",
    "fat_g":                  "fat",
    "fiber_g":                "fiber",
    "sugar_g":                "sugar",
    "starch_g":               "starch",          # ← nouveau v6
    "alcohol_g":              "alcohol",          # ← nouveau v6
    # Lipides
    "saturated_fat_g":        "saturated_fat",
    "monounsaturated_fat_g":  "mufa",
    "polyunsaturated_fat_g":  "pufa",
    "trans_fat_g":            "trans_fat",        # ← nouveau v6
    "omega3_g":               "omega3",
    "omega3_ala_g":           "omega3_ala",       # ← nouveau v6
    "omega3_epa_g":           "omega3_epa",       # ← nouveau v6
    "omega3_dha_g":           "omega3_dha",       # ← nouveau v6
    "omega6_g":               "omega6",
    "cholesterol_mg":         "cholesterol",
    # Minéraux
    "sodium_mg":              "sodium",
    "calcium_mg":             "calcium",
    "iron_mg":                "iron",
    "magnesium_mg":           "magnesium",
    "phosphorus_mg":          "phosphorus",
    "potassium_mg":           "potassium",
    "zinc_mg":                "zinc",
    "copper_mg":              "copper",
    "manganese_mg":           "manganese",
    "selenium_ug":            "selenium",
    "iodine_ug":              "iodine",           # ← nouveau v6
    # Vitamines
    "vitamin_a_ug":           "vitamin_a",
    "beta_carotene_ug":       "beta_carotene",    # ← nouveau v6
    "vitamin_d_ug":           "vitamin_d",
    "vitamin_e_mg":           "vitamin_e",
    "vitamin_k1_ug":          "vitamin_k1",
    "vitamin_k2_ug":          "vitamin_k2",       # ← nouveau v6
    "vitamin_c_mg":           "vitamin_c",
    "vitamin_b1_mg":          "vitamin_b1",
    "vitamin_b2_mg":          "vitamin_b2",
    "vitamin_b3_mg":          "vitamin_b3",
    "vitamin_b5_mg":          "vitamin_b5",
    "vitamin_b6_mg":          "vitamin_b6",
    "folate_ug":              "folate",
    "vitamin_b12_ug":         "vitamin_b12",
    "choline_mg":             "choline",          # ← nouveau v6
    # Autres
    "polyols_g":              "polyols",          # ← nouveau v6
    "organic_acids_g":        "organic_acids",    # ← nouveau v6
}
_INV_FIELD_MAP = {v: k for k, v in FIELD_MAP.items()}


# ══════════════════════════════════════════════════════════════════════════════
# ENRICHISSEMENT CHAMPS CALCULÉS (nova, health_score, bioavailability, etc.)
# ══════════════════════════════════════════════════════════════════════════════

# NOVA Classification rules
# Source: Monteiro et al. (2019) NOVA groups
NOVA_BY_INGREDIENT_TYPE: dict[str, int] = {
    "raw":        1,
    "fresh":      1,
    "dried":      1,
    "frozen":     1,
    "roasted":    1,
    "ground":     1,
    "smoked":     2,
    "fermented":  2,
    "cooked":     2,
    "default":    1,
}

NOVA_BY_CATEGORY: dict[str, int] = {
    # Group 1 — unprocessed / minimally processed
    "fruit":       1, "vegetable": 1, "legume": 1, "grain": 1,
    "nut": 1, "seed": 1, "herb": 1, "spice": 1, "mushroom": 1,
    "egg": 1, "dairy_plain": 1, "fish_fresh": 1,
    # Group 2 — culinary ingredients
    "oil": 2, "fat": 2, "sugar_raw": 2, "salt": 2, "vinegar": 2,
    "flour": 2, "starch": 2, "butter": 2,
    # Group 3 — processed foods
    "cheese": 3, "cured_meat": 3, "canned": 3, "salted_nut": 3,
    "preserved": 3, "fermented_dairy": 3,
    # Group 4 — ultra-processed
    "soft_drink": 4, "snack": 4, "ready_meal": 4, "breakfast_cereal": 4,
    "processed_meat": 4, "instant": 4, "confectionery": 4,
    "sweetened_beverage": 4, "flavored_yogurt": 4,
}


def compute_nova_group(variant: dict) -> int | None:
    """
    Estime le groupe NOVA depuis category + ingredient_type.
    Retourne 1-4 ou None si indéterminable.
    """
    ingredient_type = variant.get("ingredient_type", "default")
    category = variant.get("category")  # depuis _meta parent

    nova = NOVA_BY_CATEGORY.get(category) if category else None
    if nova is None:
        nova = NOVA_BY_INGREDIENT_TYPE.get(ingredient_type, 1)
    return nova


def compute_health_score(variant: dict) -> float | None:
    """
    Score santé 0-100 basé sur le profil nutritionnel.
    
    Approche : score positif pour fibres, protéines, micronutriments ;
               score négatif pour sucre ajouté, graisses saturées, sodium.
    
    Inspiré de NutriScore FR + FSA UK score (adapté).
    Retourne None si trop de valeurs manquantes.
    """
    # Composantes requises pour calculer
    required = ["calories_kcal", "fiber_g", "protein_g", "sugar_g", "fat_g"]
    if any(variant.get(f) is None for f in required):
        return None

    cal    = variant.get("calories_kcal", 0) or 1  # avoid div/0
    fiber  = variant.get("fiber_g", 0) or 0
    prot   = variant.get("protein_g", 0) or 0
    sugar  = variant.get("sugar_g", 0) or 0
    satfat = variant.get("saturated_fat_g", 0) or 0
    sodium = variant.get("sodium_mg", 0) or 0

    # Points positifs (max 40)
    fiber_score  = min(fiber / 0.25, 15)           # 15 pts max (≥3.75g/100g)
    prot_score   = min(prot / 0.5, 15)             # 15 pts max (≥7.5g/100g)
    # Bonus micronutriments si présents
    micro_bonus  = 0
    for field in ["vitamin_c_mg", "iron_mg", "calcium_mg", "potassium_mg"]:
        if variant.get(field) and variant[field] > 0:
            micro_bonus += 2.5
    # choline : nutriment de référence depuis FIELD_MAP v6 — AJR ~400 mg/j
    # contribue positivement comme les autres vitamines B (même poids 2.5 pts)
    if variant.get("choline_mg") and variant["choline_mg"] > 0:
        micro_bonus += 2.5
    micro_bonus = min(micro_bonus, 10)

    positive = fiber_score + prot_score + micro_bonus

    # Points négatifs (max 40)
    # Calories density (> 400 kcal/100g = pénalité max)
    cal_penalty   = min(cal / 40, 10)
    sugar_penalty = min(sugar / 1, 15)             # 15 pts max (>15g/100g)
    satfat_penalty = min(satfat / 0.5, 10)         # 10 pts max (>5g/100g)
    sodium_penalty = min(sodium / 80, 5)           # 5 pts max (>400mg/100g)

    negative = cal_penalty + sugar_penalty + satfat_penalty + sodium_penalty

    raw_score = 100 - (negative - positive + 40) * (100 / 80)
    return round(max(0.0, min(100.0, raw_score)), 1)


# Bioavailabilité protéines par catégorie (PDCAAS/DIAAS approchés)
# Sources: FAO/WHO 2013, van Vliet et al. 2015
BIOAVAILABILITY_TABLE: dict[str, float] = {
    # Animaux (haute biodisponibilité)
    "egg":            0.97,
    "dairy":          0.95,
    "dairy_plain":    0.95,
    "fermented_dairy":0.93,
    "fish_fresh":     0.92,
    "meat":           0.92,
    "poultry":        0.91,
    "seafood":        0.90,
    # Légumineuses
    "legume":         0.75,
    "soy":            0.91,  # soja = exception
    # Céréales / grains
    "grain":          0.70,
    "flour":          0.68,
    # Noix / graines
    "nut":            0.65,
    "seed":           0.65,
    # Végétaux
    "vegetable":      0.60,
    "fruit":          0.55,
    "mushroom":       0.62,
    # Autres
    "default":        0.70,
}


def compute_bioavailability(category: str | None, ingredient_type: str | None) -> float | None:
    """Retourne la biodisponibilité protéique estimée (0-1) selon catégorie."""
    if not category:
        return None
    return BIOAVAILABILITY_TABLE.get(category, BIOAVAILABILITY_TABLE.get("default"))


# ── Règles biologiques ────────────────────────────────────────────────────────
# Lait animal : fiber et starch sont physiologiquement nuls
ANIMAL_MILK_KEYS = {"milk_animal", "cream_animal"}

# Catégories strictement végétales : cholestérol = 0 sans exception
BIO_PLANT_CATEGORIES = {
    "vegetable", "fruit", "grain", "legume", "herb_spice",
    "dairy_alternative", "superfood", "protein_plant", "leavening",
}

# Noix/graines brutes : sodium naturel < 50 mg/100g
BIO_FAT_SODIUM_THRESHOLD = 50   # mg/100g
BIO_FAT_SODIUM_EXCEPTIONS = {"peanut", "tahini", "pesto", "butter"}

# ── Hiérarchie de confiance des sources ──────────────────────────────────────
# Utilisée pour protéger les données haute-confiance contre l'écrasement.
# Règle : ne jamais écraser un champ dont source_priority >= THRESHOLD_PROTECT.
SOURCE_PRIORITY = {
    "measured":       4,   # valeur mesurée directement (CIQUAL officiel, USDA FDC raw)
    "trusted_source": 3,   # source croisée fiable
    "estimated":      2,   # calculé / estimé avec règles
    "derived":        1,   # reconstruit mathématiquement
    "unknown":        0,
}
THRESHOLD_PROTECT = SOURCE_PRIORITY["measured"]  # ne pas écraser les valeurs mesurées

# ── Profils lipidiques mesurés — sources USDA/CIQUAL citées ──────────────────
# Format : (base, variant) → (sat_g, mono_g, poly_g, omega3_g, omega6_g, source_ref)
# À compléter progressivement avec les ingrédients haute-priorité.
# Ces valeurs ont priorité absolue sur tout match automatique.
KNOWN_LIPID_PROFILES: dict[tuple, tuple] = {
    # USDA FDC #2261756 — Almond flour (blanched, full-fat)
    ("flour", "almond"): (3.73, 31.57, 12.26, 0.003, 12.14, "USDA FDC #2261756"),
    # USDA FDC #1100612 — Almonds, raw
    ("almond", "default"): (3.73, 33.61, 12.50, 0.006, 12.32, "USDA FDC #1100612"),
    # USDA FDC #1100612 — Almonds slivered ≈ default
    ("almond", "slivered"): (3.73, 33.61, 12.50, 0.006, 12.32, "USDA FDC #1100612"),
    ("almond", "toasted"): (3.79, 34.17, 12.72, 0.006, 12.53, "USDA FDC #1100613"),
    # USDA FDC #173944 — Avocado, raw
    ("avocado", "default"): (2.13, 9.80, 1.82, 0.11, 1.69, "USDA FDC #173944"),
    # USDA FDC #170926 — Turmeric, raw (fresh root)
    # fat_g=0.97 est la valeur mesurée USDA. Le check saturated_fat_gt_fat se
    # déclenchait car fat_g post-fusion CIQUAL (0.6g) < sat_g USDA (0.338g).
    # Injection du profil complet pour aligner fat_g sur la source la plus fiable.
    ("turmeric_fresh", "default"): (0.338, 0.052, 0.097, 0.049, 0.040, "USDA FDC #170926"),
    ("turmeric_fresh", "raw"):     (0.338, 0.052, 0.097, 0.049, 0.040, "USDA FDC #170926"),
}

# ── Overrides manuels — valeurs figées, priorité absolue sur ontologie ───────
# Format : ingredient_key → variant_key → {v2_field: value}
# Usage : corriger les artefacts de fusion multi-source non couverts par
# KNOWN_LIPID_PROFILES (qui ne gère que sat/mono/poly/omega3/omega6).
# Ces valeurs écrasent TOUJOURS la valeur courante, même si elle est non-None.
# Source obligatoire dans le commentaire.
MANUAL_OVERRIDES: dict[str, dict[str, dict[str, float]]] = {
    # ── turmeric_fresh : fat_g sous-estimé après fusion CIQUAL(0.6g)/USDA(0.97g) ─
    # CIQUAL 2025 #11000 "Curcuma, frais" fat=0.6g — moins fiable (n=1 source).
    # USDA FDC #170926 "Spices, turmeric, raw" fat=0.97g — mesure directe.
    # Sans ce fix : sat=0.338g (USDA) > fat=0.6g (CIQUAL) → saturated_fat_gt_fat critical.
    # Correction : fat_g aligné sur USDA, cohérent avec le profil lipidique injecté
    # par KNOWN_LIPID_PROFILES (sat+mono+poly = 0.338+0.052+0.097 = 0.487g < 0.97g ✓).
    "turmeric_fresh": {
        "default": {"fat_g": 0.97},
        "raw":     {"fat_g": 0.97},
    },
    # ══════════════════════════════════════════════════════════════════════════
    # URGENT_FIXES portés depuis patch_nutrition_v7.py
    # Corrections vérifiées manuellement contre USDA FoodData Central.
    # Ces ingrédients ont data_quality='exact'/conf=1.0 dans nutrition_v2
    # mais leurs valeurs sources sont erronées (mauvais match, confusion variante,
    # source per-cup vs per-100g, doublon raw/dried…).
    # MANUAL_OVERRIDES (étape 1c) écrase toujours, même les valeurs 'exact'.
    # ══════════════════════════════════════════════════════════════════════════

    # ── fennel : mélange graines (345kcal) + bulbe (31kcal) dans la source ──
    # USDA FDC #169944 Fennel, bulb, raw : 31kcal, fat=0.20, carbs=7.29
    "fennel": {
        "default": {
            "calories_kcal": 31.0,
            "protein_g":      1.24,
            "carbs_g":        7.29,
            "fat_g":          0.20,
            "fiber_g":        3.10,
            "sugar_g":        3.93,
        },
    },

    # ── chestnut : energy_mismatch + sat>fat (confusion dried vs raw) ────────
    # USDA FDC #170578 Chestnuts, raw : 245kcal, carbs=52.96, protein=3.17
    "chestnut": {
        "default": {
            "calories_kcal":          245.0,
            "protein_g":                3.17,
            "carbs_g":                 52.96,
            "fat_g":                    2.26,
            "fiber_g":                  8.1,
            "saturated_fat_g":          0.43,
            "monounsaturated_fat_g":    0.79,
            "polyunsaturated_fat_g":    0.90,
        },
    },

    # ── strawberry : calories=92 erronées (source per-cup × 2.8 cups/100g) ──
    # USDA FDC #167762 Strawberries raw : 32kcal. Atwater macros ≈ 37kcal.
    "strawberry": {
        "default": {"calories_kcal": 36.0},
    },

    # ── asparagus : calories=15 (CIQUAL) sous-estimé vs USDA 20kcal ─────────
    # USDA FDC #168409 Asparagus raw : 20kcal. Proposals carbs/sodium bloqués.
    "asparagus": {
        "default": {"calories_kcal": 20.0},
    },

    # ── jalapeno : calories=24.1 trop bas (source CIQUAL poids net vs brut) ──
    # USDA FDC #168576 Peppers jalapeño raw : 27kcal
    "jalapeno": {
        "default": {
            "calories_kcal": 27.0,
            "protein_g":      0.91,
            "carbs_g":        5.9,
            "fat_g":          0.37,
            "fiber_g":        2.5,
            "sugar_g":        3.22,
        },
    },

    # ── maca : calories=669 doublon (maca×2 ou confusion raw/dried) ──────────
    # USDA FDC #170400 Maca powder : 325kcal, protein=10.2, carbs=70.7, fat=2.2
    "maca": {
        "default": {
            "calories_kcal": 325.0,
            "protein_g":      10.2,
            "carbs_g":        70.7,
            "fat_g":           2.2,
            "fiber_g":         8.5,
            "sugar_g":        20.5,
        },
    },

    # ── zucchini : sat(1.3g) > fat(0.19g) — contamination source ────────────
    # USDA FDC #169282 Squash zucchini raw : sat=0.083, mono=0.011, poly=0.099
    "zucchini": {
        "default": {
            "saturated_fat_g":         0.083,
            "monounsaturated_fat_g":   0.011,
            "polyunsaturated_fat_g":   0.099,
        },
    },

    # ── bean : omega_gt_poly (omega6=0.29 > poly=0.26) ───────────────────────
    # USDA kidney/pinto beans cooked : omega6≈0.16g, omega3≈0.05g
    "bean": {
        "default": {
            "omega6_g": 0.16,
            "omega3_g": 0.05,
        },
    },

    # ── kashk : sat=fat=16g car mufa/pufa non renseignés dans données sources ──
    # Kashk = petit-lait iranien séché/concentré. Profil laitier : sat dominant
    # mais mufa/pufa réels existent. USDA n'indexe pas kashk directement.
    # Estimation conservative basée sur profil fromage affiné similaire (USDA feta) :
    #   fat_g=16, sat=11.5 (72%), mufa=3.5 (22%), pufa=0.6 (4%) → ratio cohérent.
    # Injecte les sous-composants manquants ; fat_g reste à 16 (inchangé).
    # NOTE : les macros principales (protein/fat/carbs/kcal) sont aussi figées ici
    # car nutrition_patched_v7.json (prioritaire sur nutrition_corrected) contient
    # les valeurs du proxy ricotta écrasées avant l'introduction du guard.
    # Cette entrée MANUAL_OVERRIDES garantit la cohérence quelle que soit la source lue.
    "kashk": {
        "default": {
            "calories_kcal":          267,
            "protein_g":               24.0,
            "fat_g":                   16.0,
            "carbs_g":                  8.0,
            "saturated_fat_g":         11.5,   # ~72% du fat total
            "monounsaturated_fat_g":    3.5,   # ~22%
            "polyunsaturated_fat_g":    0.6,   # ~4%
        },
    },

    # ══════════════════════════════════════════════════════════════════════════
    # CORRECTIONS AUDIT 2026-04-28 — INCOHÉRENCES MACRO/SUCRE BIOLOGIQUES
    # Sources : USDA FoodData Central sauf mention contraire
    # Note : water/default sugar déjà couvert par patch_nutrition_critical.py (C1)
    # ══════════════════════════════════════════════════════════════════════════

    # ── hard_boiled_egg/default : sugar_g(1.1) > carbs_g(0.747) ─────────────
    # USDA FDC #173424 Egg hard-boiled : sugar=0.56g, carbs=1.12g
    "hard_boiled_egg": {
        "default": {"sugar_g": 0.56, "carbs_g": 1.12},
    },

    # ── milk_plant/coconut : sugar(0.959) > carbs(0.766) ─────────────────────
    # USDA FDC #2340793 Coconut milk beverage unsw. : carbs=3.39, sugar=2.08
    # ── milk_plant/soy : sugar(0.959) > carbs(0.766) ─────────────────────────
    # USDA FDC #2263715 Soy beverage unsweetened : carbs=1.5, sugar=1.0
    "milk_plant": {
        "coconut": {"carbs_g": 3.39, "sugar_g": 2.08},
        "soy":     {"carbs_g": 1.5,  "sugar_g": 1.0},
    },

    # ── cabbage/red : macro_cal=20 ≪ cal=29 (ratio 0.68) ─────────────────────
    # USDA FDC #169975 Cabbage red raw : cal=31. Atwater ≈ 31 ✓
    "cabbage": {
        "red": {
            "calories_kcal": 31.0,
            "protein_g":      1.43,
            "carbs_g":        7.37,
            "fat_g":          0.16,
        },
    },

    # ── cherry/default : cal=36 mais macro_cal=52 (ratio 1.46) ───────────────
    # USDA FDC #171719 Cherries sweet raw : cal=63. Atwater ≈ 68 — cohérent ✓
    "cherry": {
        "default": {
            "calories_kcal": 63.0,
            "protein_g":      1.06,
            "carbs_g":       16.01,
            "fat_g":          0.20,
            "sugar_g":       12.82,
            "fiber_g":        2.1,
        },
    },

    # ── onion/white+yellow : cal=23 mais macro_cal≈32 (ratio ~1.40) ──────────
    # USDA FDC #170000 Onions raw : cal=40. Atwater ≈ 43 — cohérent ✓
    "onion": {
        "white": {
            "calories_kcal": 40.0, "protein_g": 1.10,
            "carbs_g": 9.34, "fat_g": 0.10,
            "sugar_g": 4.24, "fiber_g": 1.7,
        },
        "yellow": {
            "calories_kcal": 40.0, "protein_g": 1.10,
            "carbs_g": 9.34, "fat_g": 0.10,
            "sugar_g": 4.24, "fiber_g": 1.7,
        },
    },

    # ── lettuce/default : cal=14.7 mais macro_cal=20 (ratio 1.37) ─────────────
    # USDA FDC #169247 Lettuce green-leaf raw : cal=15.
    "lettuce": {
        "default": {
            "calories_kcal": 15.0, "protein_g": 1.36,
            "carbs_g": 2.87, "fat_g": 0.22,
            "fiber_g": 1.3, "sugar_g": 1.19,
        },
    },

    # ── pak_choi/default : cal=13 mais macro_cal=17 (ratio 1.27) ──────────────
    # USDA FDC #169088 Cabbage chinese pak-choi raw : cal=13.
    "pak_choi": {
        "default": {
            "calories_kcal": 13.0, "protein_g": 1.5,
            "carbs_g": 2.18, "fat_g": 0.20,
            "fiber_g": 1.0, "sugar_g": 1.18,
        },
    },

    # ── green_apple/red_apple : sugar(13.992) > carbs(13.80) ─────────────────
    # Delta arrondi — contrainte biologique : sugar ≤ carbs.
    "green_apple": {
        "default": {"sugar_g": 13.80},
    },
    "red_apple": {
        "default": {"sugar_g": 13.80},
    },
}

# Empêche les mauvais matches USDA de contaminer fat_g.
FAT_SANITY_MAX_RATIO = 5.0  # fat_g_new / sub_total_existing

# ── Garde-fou enrichissement : sentinelles acaï ──────────────────────────────
# Valeurs injectées par contamination fuzzy CIQUAL (agave → sirop_d'agave qui
# a reçu les données acaï via mauvais alias). Si une valeur de référence
# correspond exactement à une sentinelle ET que le champ cible est None,
# l'enrichissement est rejeté.
_ACAI_SENTINELS: dict[str, float] = {
    "calories_kcal":      457.0,
    "protein_g":           34.5,
    "fat_g":               20.7,
    "carbs_g":             25.7,
    "fiber_g":              9.6,
    "sugar_g":              7.5,
    "saturated_fat_g":      2.99,
    "omega3_g":             1.45,
    "calcium_mg":         206.0,
    "potassium_mg":      2520.0,
    "magnesium_mg":       429.0,
    "selenium_ug":         11.0,
    "zinc_mg":              3.92,
    "iron_mg":              6.37,
}

# Champs macros critiques : seuil de sanity-check sur la valeur absolue.
# Si ref_val > MAX_MACRO_VAL[field] ET current=None → enrichissement bloqué.
# Évite d'injecter des valeurs absurdes (ex: protein=34.5g dans un sirop).
_MAX_MACRO_VAL: dict[str, float] = {
    "protein_g":   30.0,   # aucun sirop/sucre ne dépasse 5g — 30g = seuil libéral
    "fat_g":       15.0,   # sirops/sucres ont fat < 1g
    "calories_kcal": 420.0,  # sirop d'agave ~310 kcal — 420 est le seuil acaï
}

# Bases ontologie dont l'enrichissement auto est désactivé (alias résolu mais
# données suspectes — à corriger manuellement via KNOWN_LIPID_PROFILES).
_ENRICHMENT_BLOCKED_BASES: set[str] = {
    # "agave" est un alias → sa cible sirop_d'agave peut avoir des données acaï
    # si l'ontologie a été construite avant le fix des aliases.
    # On bloque jusqu'à ce que l'ontologie soit reconstruite proprement.
}


def _is_acai_contamination(field: str, ref_val: float) -> bool:
    """Retourne True si ref_val ressemble à une valeur sentinelle acaï."""
    sentinel = _ACAI_SENTINELS.get(field)
    if sentinel is not None and abs(ref_val - sentinel) < 0.01:
        return True
    max_val = _MAX_MACRO_VAL.get(field)
    if max_val is not None and ref_val > max_val:
        return True
    return False


def compute_glycemic_load(gi: float | None, carbs: float | None) -> float | None:
    """GL = GI × carbs_g / 100"""
    if gi is None or carbs is None:
        return None
    return round(gi * carbs / 100, 2)


def infer_glycemic_index_source(variant: dict) -> str | None:
    """
    Détermine la source du GI :
    - 'measured' si la source est CIQUAL ou une base GI connue
    - 'estimated' si calculé / estimé
    - None si GI absent
    """
    if variant.get("glycemic_index") is None:
        return None
    sources = [s.get("name", "") for s in variant.get("sources", [])]
    measured_sources = {"CIQUAL", "Atkinson GI Tables", "Sydney Uni GI", "Foster-Powell"}
    if any(s in measured_sources for s in sources):
        return "measured"
    return "estimated"


# ==============================================================================
# SCHEMA v4.0 — NOUVEAUX BLOCS CALCULES
# diet_profile | allergen_flags | nutrition_flags | cooking_profile
# reco_context | substitution
# Principe : uniquement ce qui est derivable des donnees sources ou des
# valeurs nutriments deja presentes. Aucune valeur inventee.
# Seuils nutrition_flags : EU Reglement 1924/2006.
# ==============================================================================

import re as _re

# ── 5.1 DIET PROFILE ──────────────────────────────────────────────────────────
_DAIRY_RE       = _re.compile(r'\b(milk|cream|cheese|butter|yogurt|yoghurt|ghee|whey|casein|kefir|lactose|fromage|lait|creme|beurre|yaourt)\b', _re.I)
_DAIRY_PLANT_RE = _re.compile(r'\b(almond\s*milk|soy\s*milk|oat\s*milk|coconut\s*milk|plant[- ]?based|lait\s*(veg|d\'amande|d\'avoine|de\s*soja))\b', _re.I)
_EGG_RE         = _re.compile(r'\b(egg|eggs|yolk|albumen|meringue|mayonnaise|oeuf|oeufs|jaune)\b', _re.I)
_GLUTEN_RE      = _re.compile(r'\b(wheat|rye|barley|spelt|kamut|semolina|bulgur|farro|flour|bread|couscous|seitan|gluten|ble|seigle|orge|epeautre|farine|baguette)\b', _re.I)
_NUT_RE         = _re.compile(r'\b(almond|cashew|walnut|pecan|pistachio|hazelnut|macadamia|brazil\s*nut|chestnut|pine\s*nut|amande|noix|noisette|pistache)\b', _re.I)
_SOY_RE         = _re.compile(r'\b(soy|soya|tofu|tempeh|edamame|miso|natto|soja)\b', _re.I)
_FERMENT_RE     = _re.compile(r'\b(yogurt|yoghurt|kefir|miso|tempeh|natto|kimchi|kombucha|sourdough|fermented|vinegar|vinaigre|yaourt|ferment|levain)\b', _re.I)

_FORCED_DAIRY       = {"dairy", "dairy_plain", "fermented_dairy"}
_FORCED_EGG         = {"egg"}
_FORCED_GLUTEN      = {"grain", "flour"}
_FORCED_NUT         = {"nut", "seed"}
_FORCED_SOY         = {"soy"}


def compute_diet_profile(
    name_en: str, name_fr: str,
    category: str | None,
    ingredient_type: str | None
) -> dict:
    """Flags dietetiques derives du category + keywords (word-boundary)."""
    text = f"{name_en} {name_fr}"
    is_plant_dairy = bool(_DAIRY_PLANT_RE.search(text))
    has_dairy  = not is_plant_dairy and bool(_DAIRY_RE.search(text))
    has_egg    = bool(_EGG_RE.search(text))
    has_gluten = bool(_GLUTEN_RE.search(text))
    has_nut    = bool(_NUT_RE.search(text))
    has_soy    = bool(_SOY_RE.search(text))
    is_ferment = bool(_FERMENT_RE.search(text))

    if category in _FORCED_DAIRY:  has_dairy  = True
    if category in _FORCED_EGG:    has_egg    = True
    if category in _FORCED_GLUTEN: has_gluten = True
    if category in _FORCED_NUT:    has_nut    = True
    if category in _FORCED_SOY:    has_soy    = True

    return {
        "vegetarian":  True,
        "vegan":       not has_dairy and not has_egg,
        "egg_free":    not has_egg,
        "dairy_free":  not has_dairy,
        "gluten_free": not has_gluten,
        "nut_free":    not has_nut,
        "soy_free":    not has_soy,
        "fermented":   is_ferment,
        "confidence":  0.95 if category else 0.80,
        "_source":     "auto_detected",
    }


# ── 5.2 ALLERGEN FLAGS (EU 14, Reglement 1169/2011) ──────────────────────────
#
# Améliorations v6.4 (audit 2026-04-28) :
#   - gluten : n'attrape plus les farines naturellement GF (almond, buckwheat,
#              cassava, chickpea, corn, rice, teff, oat, tapioca, arrowroot…)
#   - eggs   : n'attrape plus "eggplant" (aubergine)
#   - _FORCED_ALLERGEN : faux négatifs impossibles à détecter textuellement
#              (milk_plant/almond+cashew → nuts, broth/miso → soy,
#               sauce/peanut → peanuts, buckwheat_crepe → gluten)
#   - _ALLERGEN_FP_OVERRIDE : neutralise les faux positifs connus par clé
#              (butter/almond ≠ lait, eggplant ≠ œuf, flax_egg ≠ œuf)
#
_EU_ALLERGEN_RE: dict[str, _re.Pattern] = {
    "gluten":      _re.compile(
        r'\b(wheat|rye|barley|spelt|kamut|semolina|bulgur|farro|couscous|seitan'
        r'|ble|seigle|orge|epeautre|baguette|pita|udon|soba)\b'
        r'|\b(bread|noodle|pasta|breadcrumb)\b'
        r'|\bflour\b(?!\s*(?:almond|buckwheat|cassava|chickpea|corn|rice|teff|oat'
        r'|tapioca|arrowroot|potato|sorghum|millet|quinoa|amaranth|coconut|hemp))'
        r'|\bfarine\b(?!\s*(?:amande|sarrasin|manioc|pois|mais|riz|teff|avoine|coco|chanvre))',
        _re.I),
    "crustaceans": _re.compile(r'\b(shrimp|prawn|lobster|crab|crayfish|crevette|homard|ecrevisse)\b', _re.I),
    "eggs":        _re.compile(r'\b(eggs?|yolk|albumen|meringue|oeuf|jaune)\b', _re.I),
    "fish":        _re.compile(r'\b(fish|salmon|tuna|cod|anchov|sardine|trout|poisson|saumon|thon|morue)\b', _re.I),
    "peanuts":     _re.compile(r'\b(peanut|groundnut|cacahuete|arachide)\b', _re.I),
    "soy":         _re.compile(r'\b(soy|soya|tofu|tempeh|edamame|miso|soja)\b', _re.I),
    "milk":        _re.compile(r'\b(milk|cream|cheese|butter|yogurt|yoghurt|ghee|whey|casein|kefir|lactose|lait|fromage|creme|beurre|yaourt)\b', _re.I),
    "nuts":        _re.compile(r'\b(almond|cashew|walnut|pecan|pistachio|hazelnut|macadamia|brazil\s*nut|chestnut|pine\s*nut|amande|noix|noisette|pistache)\b', _re.I),
    "celery":      _re.compile(r'\b(celery|celeriac|celeri|rave)\b', _re.I),
    "mustard":     _re.compile(r'\b(mustard|moutarde|senf)\b', _re.I),
    "sesame":      _re.compile(r'\b(sesame|tahini|sesam|sesame\s*oil|huile\s*de\s*sesame)\b', _re.I),
    "sulfites":    _re.compile(r'\b(sulfite|sulphite|wine|vin|dried\s*apricot|abricot\s*sec)\b', _re.I),
    "lupin":       _re.compile(r'\b(lupin|lupine|lupin\s*flour|farine\s*de\s*lupin)\b', _re.I),
    "molluscs":    _re.compile(r'\b(oyster|mussel|clam|squid|octopus|scallop|huitre|moule|palourde)\b', _re.I),
}

# Allergènes forcés par ingredient_key (faux négatifs non détectables textuellement).
# Format : {"base/variant": {allergen, ...}} — ajoutés après regex, non supprimables.
_FORCED_ALLERGEN: dict[str, set[str]] = {
    "milk_plant/almond":  {"nuts"},    # lait d'amande → fruit à coque
    "milk_plant/cashew":  {"nuts"},    # lait de cajou → fruit à coque
    "broth/miso":         {"soy"},     # bouillon miso → soja
    "sauce/peanut":       {"peanuts"}, # sauce cacahuète → arachide EU
    "buckwheat_crepe":    {"gluten"},  # crêpe sarrasin = mélange blé+sarrasin probable
}

# Faux positifs à neutraliser après regex.
# Format : {"base/variant_or_base": {allergen, ...}} — forcés à False.
_ALLERGEN_FP_OVERRIDE: dict[str, set[str]] = {
    "eggplant":         {"eggs"},  # aubergine ≠ œuf (trigger sur "egg")
    "flax_egg":         {"eggs"},  # substitut vegan : lin + eau, pas d'œuf
    "butter/almond":    {"milk"},  # beurre d'amande ≠ produit laitier
    "squash/butternut": {"milk"},  # courge butternut ≠ beurre
    "butternut":        {"milk"},  # idem (clé sans variant)
}


def compute_allergen_flags(
    name_en: str,
    name_fr: str,
    category: str | None,
    ingredient_key: str = "",
) -> dict:
    """Detecte les 14 allergenes EU depuis les noms (word-boundary).

    v6.4 : corrige faux positifs (eggplant/eggs, butter almond/milk, flax_egg/eggs)
           et faux négatifs (lait amande/cajou→nuts, miso→soy, peanut sauce→peanuts).
    """
    text = f"{name_en} {name_fr}"
    flags: dict = {k: bool(pat.search(text)) for k, pat in _EU_ALLERGEN_RE.items()}

    # Catégories forcées
    if category in _FORCED_DAIRY: flags["milk"] = True
    if category in _FORCED_EGG:   flags["eggs"] = True
    if category in _FORCED_NUT:   flags["nuts"] = True
    if category in _FORCED_SOY:   flags["soy"]  = True

    # Faux positifs par clé exacte ou préfixe base
    for fp_key, fp_allergens in _ALLERGEN_FP_OVERRIDE.items():
        if ingredient_key == fp_key or ingredient_key.startswith(fp_key + "/"):
            for allergen in fp_allergens:
                flags[allergen] = False

    # Allergènes forcés par clé
    for forced_key, forced_allergens in _FORCED_ALLERGEN.items():
        if ingredient_key == forced_key or ingredient_key.startswith(forced_key + "/"):
            for allergen in forced_allergens:
                flags[allergen] = True

    flags["_source"]     = "auto_detected"
    flags["_confidence"] = 0.92
    return flags


# ── 5.3 NUTRITION FLAGS (EU Reglement 1924/2006) ──────────────────────────────
# (field, seuil_source, seuil_riche, nom_flag_source, nom_flag_riche)
_NF_PAIRS: list[tuple] = [
    ("fiber_g",      3.0,   6.0,   "good_source_fiber",      "high_fiber"),
    ("protein_g",   10.0,  20.0,   "good_source_protein",    "high_protein"),
    ("vitamin_c_mg",12.0,  24.0,   "source_vitamin_c",       "high_vitamin_c"),
    ("iron_mg",      2.1,   4.2,   "good_source_iron",       "high_iron"),
    ("calcium_mg",  120.0, 240.0,  "good_source_calcium",    "high_calcium"),
    ("potassium_mg",300.0, 600.0,  "good_source_potassium",  "high_potassium"),
    ("folate_ug",    30.0,  60.0,  "source_folate",          "high_folate"),
    ("vitamin_d_ug",  0.75,  1.5,  "source_vitamin_d",       "high_vitamin_d"),
    ("magnesium_mg", 56.0, 112.0,  "source_magnesium",       "high_magnesium"),
    ("zinc_mg",       1.5,   3.0,  "source_zinc",            "high_zinc"),
    ("omega3_g",      0.3,   0.6,  "source_omega3",          "high_omega3"),
]


def compute_nutrition_flags(variant: dict) -> dict:
    """Labels nutritionnels EU 1924/2006 calcules depuis les valeurs nutriments."""
    flags: dict = {}
    for field, src_thr, high_thr, src_name, high_name in _NF_PAIRS:
        val = variant.get(field) or 0
        flags[high_name] = val >= high_thr
        flags[src_name]  = val >= src_thr

    kcal = variant.get("calories_kcal") or 0
    flags["low_calorie"]      = 0 < kcal <= 40
    flags["low_sodium"]       = (variant.get("sodium_mg") or 999) <= 120
    flags["low_sugar"]        = (variant.get("sugar_g") or 999) <= 5
    flags["antioxidant_rich"] = (
        (variant.get("beta_carotene_ug") or 0) > 500
        or (variant.get("vitamin_c_mg") or 0) > 30
    )
    return flags


# ── 5.4 COOKING PROFILE ───────────────────────────────────────────────────────
_CULINARY_ROLE_MAP: dict[str, str] = {
    "fruit": "fruit",   "vegetable": "vegetable", "grain": "grain",
    "legume": "legume", "nut": "nut_seed",        "seed": "nut_seed",
    "oil": "fat",       "fat": "fat",              "butter": "fat",
    "dairy": "dairy",  "dairy_plain": "dairy",    "fermented_dairy": "dairy",
    "egg": "protein_binding",
    "herb_spice": "aromatic", "spice": "aromatic", "mushroom": "umami",
    "protein_plant": "protein", "soy": "protein",
    "sugar_raw": "sweetener", "sweetener": "sweetener",
    "leavening": "leavening",  "starch": "thickener",
    "condiment": "condiment",  "vinegar": "acid",
    "flour": "binder",         "beverage": "liquid",
    "dairy_alternative": "dairy", "algae": "umami",
}
# Defaults par categorie (Larousse Gastronomique + USDA Refuse Factors)
_DEFAULT_REFUSE:  dict[str, float] = {
    "vegetable": 15, "fruit": 15, "legume": 5, "grain": 2, "nut": 10,
    "seed": 5, "mushroom": 20, "egg": 12, "dairy": 0, "oil": 0,
    "herb_spice": 25, "flour": 0, "protein_plant": 0, "default": 10,
}
_DEFAULT_YIELD: dict[str, float] = {
    "grain": 240, "legume": 225, "vegetable": 85, "fruit": 90,
    "egg": 88, "dairy": 100, "nut": 100, "seed": 100, "mushroom": 60,
    "flour": 100, "protein_plant": 85, "oil": 100, "default": 90,
}
_RAW_UNFRIENDLY = {"grain", "legume", "leavening", "starch"}


def compute_cooking_profile(
    variant: dict,
    category: str | None,
    ingredient_type: str | None,
    onto_variant_keys: list[str],
    onto_stats: dict | None = None,
) -> dict:
    """Profil culinaire : etats courants + yield/refus + roles."""
    cat        = category or "default"
    non_culinary = {"default", "unknown"}
    typical    = [k for k in onto_variant_keys if k not in non_culinary] or [ingredient_type or "raw"]

    refuse_pct   = _DEFAULT_REFUSE.get(cat, _DEFAULT_REFUSE["default"])
    yield_pct    = _DEFAULT_YIELD.get(cat, _DEFAULT_YIELD["default"])
    yield_source = "category_default"

    # Donnees CNF reelles si disponibles via _quality
    q = variant.get("_quality") or {}
    if q.get("refuse_percent") is not None:
        refuse_pct   = q["refuse_percent"]
        yield_source = "cnf_measured"

    # onto_stats peut affiner le yield si disponible
    if onto_stats and isinstance(onto_stats, dict):
        _onto_refuse = onto_stats.get("refuse_pct") or onto_stats.get("refuse_percent")
        if _onto_refuse is not None and yield_source == "category_default":
            refuse_pct   = float(_onto_refuse)
            yield_source = "onto_stats"

    fat_sol = any(
        (variant.get(f) or 0) > 0
        for f in ["vitamin_a_ug", "vitamin_d_ug", "vitamin_e_mg", "vitamin_k1_ug"]
    )
    heat_sensitive = (
        (variant.get("vitamin_c_mg") or 0) > 5
        or (variant.get("folate_ug") or 0) > 20
    )
    return {
        "typical_states":       typical[:6],
        "refuse_pct":           round(refuse_pct, 1),
        "yield_cooked_pct":     yield_pct,
        "culinary_role":        _CULINARY_ROLE_MAP.get(cat, "ingredient"),
        "fat_soluble_vitamins": fat_sol,
        "heat_sensitive":       heat_sensitive,
        "raw_friendly":         cat not in _RAW_UNFRIENDLY and ingredient_type != "dried",
        "_yield_source":        yield_source,
    }



# ── 5.7 NUTRIENTS_V6 ──────────────────────────────────────────────────────────

# Mapping : champ plat nutrition_v2 → (section_v6, clé_v6)
# Aligné sur _V6_NESTED_PATHS de validator_v12.py
_FLAT_TO_V6: list[tuple[str, str, str]] = [
    # (flat_key, section, v6_key)
    ("calories_kcal",           "energy",          "kcal"),
    ("protein_g",               "macros",           "protein_g"),
    ("carbs_g",                 "macros",           "carbs_g"),
    ("fat_g",                   "macros",           "fat_g"),
    ("fiber_g",                 "macros",           "fiber_g"),
    ("alcohol_g",               "macros",           "alcohol_g"),
    ("sugar_g",                 "carbohydrates",    "sugars_g"),
    ("starch_g",                "carbohydrates",    "starch_g"),
    ("polyols_g",               "carbohydrates",    "polyols_g"),
    ("saturated_fat_g",         "lipids",           "saturated_g"),
    ("monounsaturated_fat_g",   "lipids",           "monounsaturated_g"),
    ("polyunsaturated_fat_g",   "lipids",           "polyunsaturated_g"),
    ("trans_fat_g",             "lipids",           "trans_g"),
    ("omega3_g",                "lipids",           "omega3_g"),
    ("omega6_g",                "lipids",           "omega6_g"),
    ("omega3_ala_g",            "lipids",           "fa_18_3_ala_g"),
    ("omega3_epa_g",            "lipids",           "fa_20_5_epa_g"),
    ("omega3_dha_g",            "lipids",           "fa_22_6_dha_g"),
    ("cholesterol_mg",          "lipids",           "cholesterol_mg"),
    ("vitamin_a_ug",            "vitamins",         "a_rae_mcg"),
    ("beta_carotene_ug",        "vitamins",         "beta_carotene_mcg"),
    ("vitamin_d_ug",            "vitamins",         "d_mcg"),
    ("vitamin_e_mg",            "vitamins",         "e_mg"),
    ("vitamin_k1_ug",           "vitamins",         "k1_mcg"),
    ("vitamin_k2_ug",           "vitamins",         "k2_mcg"),
    ("vitamin_c_mg",            "vitamins",         "c_mg"),
    ("vitamin_b1_mg",           "vitamins",         "b1_mg"),
    ("vitamin_b2_mg",           "vitamins",         "b2_mg"),
    ("vitamin_b3_mg",           "vitamins",         "b3_mg"),
    ("vitamin_b5_mg",           "vitamins",         "b5_mg"),
    ("vitamin_b6_mg",           "vitamins",         "b6_mg"),
    ("folate_ug",               "vitamins",         "b9_mcg"),
    ("vitamin_b12_ug",          "vitamins",         "b12_mcg"),
    ("choline_mg",              "vitamins",         "choline_mg"),
    ("calcium_mg",              "minerals",         "calcium_mg"),
    ("phosphorus_mg",           "minerals",         "phosphorus_mg"),
    ("potassium_mg",            "minerals",         "potassium_mg"),
    ("sodium_mg",               "minerals",         "sodium_mg"),
    ("magnesium_mg",            "minerals",         "magnesium_mg"),
    ("iron_mg",                 "minerals",         "iron_mg"),
    ("zinc_mg",                 "minerals",         "zinc_mg"),
    ("copper_mg",               "minerals",         "copper_mg"),
    ("manganese_mg",            "minerals",         "manganese_mg"),
    ("selenium_ug",             "minerals",         "selenium_mcg"),
    ("iodine_ug",               "minerals",         "iodine_mcg"),
    ("organic_acids_g",         "bioactives",       "organic_acids_g"),
]

# Sections ordonnées pour une sérialisation cohérente
_V6_SECTIONS = ["energy", "macros", "carbohydrates", "lipids",
                 "vitamins", "minerals", "bioactives"]


def compute_nutrients_v6(variant: dict) -> dict:
    """
    Construit le bloc nutrients_v6 structuré depuis les champs plats du variant.

    Regroupe les nutriments en sections : energy / macros / carbohydrates /
    lipids / vitamins / minerals / bioactives.
    Seuls les champs non-None sont inclus dans chaque section.
    Une section absente de toutes valeurs n'est pas créée (sauf energy).

    Aligné sur _V6_NESTED_PATHS de validator_v12.py — lecture transparente
    par _read_all_nutrients() sans modification du validator.
    """
    # Initialiser les sections
    sections: dict[str, dict] = {s: {} for s in _V6_SECTIONS}

    for flat_key, section, v6_key in _FLAT_TO_V6:
        val = variant.get(flat_key)
        if val is not None:
            sections[section][v6_key] = val

    # Ne retourner que les sections non vides (energy toujours incluse)
    result = {}
    for s in _V6_SECTIONS:
        if sections[s] or s == "energy":
            result[s] = sections[s]

    # Métadonnées structurelles
    result["_generated_by"] = "auto_correct_v6"
    result["_schema"]       = "nutrients_v6.1"
    return result


# ── 5.8 STATE ─────────────────────────────────────────────────────────────────

# Mapping : variant_key → level1 state canonique
_VARKEY_TO_STATE: dict[str, str] = {
    "raw":       "raw",       "fresh":    "raw",      "default": "raw",
    "cooked":    "cooked",    "steamed":  "cooked",   "boiled":  "cooked",
    "roasted":   "cooked",    "fried":    "cooked",   "baked":   "cooked",
    "grilled":   "cooked",    "sauteed":  "cooked",
    "dried":     "dried",     "dry":      "dried",    "dehydrated": "dried",
    "smoked":    "processed", "cured":    "processed","pickled":  "fermented",
    "fermented": "fermented", "cultured": "fermented","aged":    "fermented",
    "frozen":    "frozen",    "canned":   "canned",   "preserved":"canned",
    "powder":    "dried",     "flour":    "processed","paste":   "processed",
    "juice":     "processed", "extract":  "processed","oil":     "processed",
    "peel":      "raw",       "zest":     "raw",
}

# Mapping : category → level1 state par défaut
_CATEGORY_DEFAULT_STATE: dict[str, str] = {
    "fruit":      "raw",      "vegetable":  "raw",    "grain":      "cooked",
    "legume":     "cooked",   "nut":        "raw",    "seed":       "raw",
    "dairy":      "raw",      "egg":        "raw",    "oil":        "processed",
    "herb_spice": "dried",    "spice":      "dried",  "mushroom":   "raw",
    "flour":      "processed","starch":     "processed","sugar_raw": "processed",
    "fermented":  "fermented","algae":      "dried",  "beverage":   "processed",
    "condiment":  "processed","vinegar":    "processed",
}


def compute_state(variant_key: str, category: str | None,
                  cooking_profile: dict | None = None) -> dict:
    """
    Infère le bloc state depuis la clé de variant et la catégorie.

    Structure : {"process": {"level1": str, "confidence": str}}
      level1 : raw | cooked | dried | fermented | frozen | canned | processed
      confidence : exact (varkey match) | inferred (catégorie) | unknown

    Utilisé par validate_v6_blocks() du validator_v12.py :
    vdata.get("state") → {"process": {"level1": "raw", ...}}
    """
    vkey = (variant_key or "default").lower()

    # Passe 1 : match direct sur la clé de variant
    if vkey in _VARKEY_TO_STATE:
        return {
            "process": {
                "level1":     _VARKEY_TO_STATE[vkey],
                "confidence": "exact",
            }
        }

    # Passe 2 : chercher dans cooking_profile.typical_states
    if cooking_profile:
        states = cooking_profile.get("typical_states") or []
        for s in states:
            if isinstance(s, str) and s in _VARKEY_TO_STATE:
                return {
                    "process": {
                        "level1":     _VARKEY_TO_STATE[s],
                        "confidence": "inferred",
                    }
                }

    # Passe 3 : fallback par catégorie
    cat = (category or "").lower()
    if cat in _CATEGORY_DEFAULT_STATE:
        return {
            "process": {
                "level1":     _CATEGORY_DEFAULT_STATE[cat],
                "confidence": "inferred",
            }
        }

    # Passe 4 : unknown
    return {
        "process": {
            "level1":     "unknown",
            "confidence": "unknown",
        }
    }

# ── 5.5 RECO CONTEXT ──────────────────────────────────────────────────────────
_MICRO_AJR: dict[str, float] = {
    "vitamin_c_mg": 8, "iron_mg": 2.1, "calcium_mg": 120, "potassium_mg": 300,
    "folate_ug": 30, "vitamin_d_ug": 0.75, "magnesium_mg": 56, "zinc_mg": 1.5,
    "vitamin_a_ug": 120, "vitamin_b1_mg": 0.165, "vitamin_b2_mg": 0.21,
    "vitamin_b6_mg": 0.21, "vitamin_b12_ug": 0.375, "selenium_ug": 8.25,
}


def compute_reco_context(variant: dict) -> dict:
    """Indicateurs de contexte pour la recommandation (depuis nutriments)."""
    kcal  = variant.get("calories_kcal") or 0
    prot  = variant.get("protein_g") or 0
    fiber = variant.get("fiber_g") or 0
    omega3= variant.get("omega3_g") or 0
    omega6= variant.get("omega6_g") or 0
    gl    = variant.get("glycemic_load")

    if   kcal <= 0:   e_density = "unknown"
    elif kcal <= 40:  e_density = "very_low"
    elif kcal <= 100: e_density = "low"
    elif kcal <= 300: e_density = "medium"
    elif kcal <= 500: e_density = "high"
    else:             e_density = "very_high"

    n_above = sum(1 for f, t in _MICRO_AJR.items() if (variant.get(f) or 0) >= t)

    if   gl is None: gl_profile = "unknown"
    elif gl <= 2:    gl_profile = "very_low"
    elif gl <= 5:    gl_profile = "low"
    elif gl <= 10:   gl_profile = "medium"
    else:            gl_profile = "high"

    return {
        "energy_density":         e_density,
        "satiety_score":          round(min((prot * 2 + fiber * 3) / 100, 1.0), 3),
        "micronutrient_richness": round(n_above / len(_MICRO_AJR), 3),
        "omega3_omega6_ratio":    round(omega3 / omega6, 3) if omega6 > 0 else None,
        "glycemic_profile":       gl_profile,
    }


# ── 5.6 SUBSTITUTION ──────────────────────────────────────────────────────────
# Table curated haute valeur pour cuisine veg/vegan
SUBSTITUTION_TABLE: dict[str, list[dict]] = {
    "butter": [
        {"ingredient": "huile_coco",     "ratio": 0.80, "diet_ok": ["vegan", "dairy_free"], "note": "Patisserie"},
        {"ingredient": "margarine_vegan","ratio": 1.00, "diet_ok": ["vegan", "dairy_free"], "note": ""},
        {"ingredient": "compote",        "ratio": 0.75, "diet_ok": ["vegan", "dairy_free"], "note": "Reduire sucre"},
    ],
    "cream": [
        {"ingredient": "creme_coco",     "ratio": 1.00, "diet_ok": ["vegan", "dairy_free"], "note": ""},
        {"ingredient": "creme_avoine",   "ratio": 1.00, "diet_ok": ["vegan", "dairy_free"], "note": ""},
        {"ingredient": "noix_cajou",     "ratio": 0.85, "diet_ok": ["vegan", "dairy_free"], "note": "Mixer avec eau"},
    ],
    "milk": [
        {"ingredient": "lait_avoine",    "ratio": 1.00, "diet_ok": ["vegan", "dairy_free"], "note": ""},
        {"ingredient": "lait_amande",    "ratio": 1.00, "diet_ok": ["vegan", "dairy_free", "nut_based"], "note": ""},
        {"ingredient": "lait_soja",      "ratio": 1.00, "diet_ok": ["vegan", "dairy_free"], "note": ""},
    ],
    "egg": [
        {"ingredient": "graine_chia",    "ratio": None, "diet_ok": ["vegan", "egg_free"], "note": "1 oeuf = 1 cs + 3 cs eau"},
        {"ingredient": "tofu_soyeux",    "ratio": None, "diet_ok": ["vegan", "egg_free"], "note": "60g par oeuf"},
        {"ingredient": "compote",        "ratio": None, "diet_ok": ["vegan", "egg_free"], "note": "3 cs par oeuf, patisserie"},
    ],
    "honey": [
        {"ingredient": "sirop_agave",    "ratio": 0.75, "diet_ok": ["vegan"], "note": "Sucrant plus fort"},
        {"ingredient": "sirop_erable",   "ratio": 0.75, "diet_ok": ["vegan"], "note": ""},
    ],
    "fromage": [
        {"ingredient": "levure_nutritionnelle", "ratio": None, "diet_ok": ["vegan", "dairy_free"], "note": "Saveur fromagere"},
        {"ingredient": "tofu",           "ratio": None, "diet_ok": ["vegan", "dairy_free"], "note": "Texture"},
    ],
    "creme_fraiche": [
        {"ingredient": "creme_coco",     "ratio": 1.00, "diet_ok": ["vegan", "dairy_free"], "note": ""},
        {"ingredient": "yaourt_soja",    "ratio": 1.00, "diet_ok": ["vegan", "dairy_free"], "note": ""},
    ],
    "parmesan": [
        {"ingredient": "levure_nutritionnelle", "ratio": 0.50, "diet_ok": ["vegan", "dairy_free"], "note": "Saupoudrer"},
    ],
    "creme_sure": [
        {"ingredient": "yaourt_coco",    "ratio": 1.00, "diet_ok": ["vegan", "dairy_free"], "note": ""},
    ],
    "lait_concentre_sucre": [
        {"ingredient": "lait_coco",      "ratio": 1.00, "diet_ok": ["vegan", "dairy_free"], "note": "Sucrer a part"},
    ],
    "gelatine": [
        {"ingredient": "agar_agar",      "ratio": 0.40, "diet_ok": ["vegan", "egg_free"], "note": "4g agar = 10g gelatine"},
        {"ingredient": "carraghenanes",  "ratio": 0.30, "diet_ok": ["vegan"], "note": "Texture plus ferme"},
    ],
}


def compute_substitution_same_category(
    ing_key: str,
    category: str | None,
    cat_index: dict[str, list[str]],
) -> dict:
    """Bloc substitution : same_category auto + alternatives curatees."""
    same = [k for k in cat_index.get(category or "", []) if k != ing_key][:8]
    alternatives = SUBSTITUTION_TABLE.get(ing_key, [])
    return {
        "same_category": same,
        "alternatives":  alternatives,
        "_source":       "auto" if same or alternatives else "none",
    }


# ==============================================================================
# CHARGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def load_mapping(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {_normalize(k): v for k, v in raw.get("mapping", {}).items()}


VARIANT_MAP = {
    "cru": "raw", "crue": "raw", "raw": "raw",
    "cuit": "cooked", "cuite": "cooked", "cooked": "cooked",
    "séché": "dried", "dried": "dried",
    "grillé": "roasted", "roasted": "roasted",
    "congelé": "frozen", "frozen": "frozen",
    "fermenté": "fermented",
}
STOPWORDS = {"et","or","de","du","des","le","la","les","un","une","and","au","aux","en","a","the"}


def resolve_key(name: str, mapping: dict) -> tuple[str, str]:
    """
    Résout (base, variant) depuis un nom d'ingrédient.
    Conservé de v5 — taux de match ~93%.
    """
    original = name
    name = _normalize(name)
    tokens = name.replace(",", " ").split()

    variant = "default"
    for tok in tokens:
        if tok in VARIANT_MAP:
            variant = VARIANT_MAP[tok]
            break

    # Essai direct mapping
    snake = name.replace(" ", "_")
    if snake in mapping:
        return mapping[snake], variant

    # Bigrams
    parts = [t for t in tokens if t not in STOPWORDS and t not in VARIANT_MAP]
    for i in range(len(parts) - 1):
        bigram = f"{parts[i]}_{parts[i+1]}"
        if bigram in mapping:
            return mapping[bigram], variant

    # Tokens seuls
    for tok in parts:
        if tok in mapping:
            return mapping[tok], variant

    # Fallback : premier token non-stopword
    candidates = [t for t in tokens if t not in STOPWORDS and t not in VARIANT_MAP]
    if candidates:
        return candidates[0], variant

    return _normalize(original).replace(" ", "_"), variant


def load_ontology(path: Path) -> dict:
    if not path.exists():
        print(f"  ⚠ Ontologie absente : {path}")
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    # ontology_v6 : key = "ingredients"
    # ontology_v5 : key = "ontology" ou "reference"
    return raw.get("ingredients") or raw.get("ontology") or raw.get("reference", {})


def pick_variant(onto_entry: dict, preferred: str) -> dict | None:
    """Retourne le variant préféré ou default ou le premier disponible."""
    if preferred in onto_entry:
        return onto_entry[preferred]
    if "default" in onto_entry:
        return onto_entry["default"]
    if onto_entry:
        return next(iter(onto_entry.values()))
    return None


def compute_delta(current: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return abs(current - reference) / reference


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def auto_correct(dry_run: bool = False) -> dict:
    print("═" * 70)
    print("AUTO CORRECT v6")
    print("═" * 70)

    mapping  = load_mapping(MAPPING_FILE)
    ontology = load_ontology(ONTOLOGY_FILE)
    print(f"  Ontologie : {ONTOLOGY_FILE.name} ({len(ontology)} bases)")

    with open(INPUT_FILE, encoding="utf-8") as f:
        db = json.load(f)

    corrections_log = []
    enriched_log    = []
    skip_log        = []

    ingredients = db.get("ingredients", {})
    corrected   = 0
    enriched    = 0

    # ── GÉNÉRATION DE VARIANTS "default" — DÉSACTIVÉE (règle exactitude) ───────
    # Règle métier : toute valeur nutritionnelle doit être exacte ou absente.
    # Copier un variant existant comme "default" d'une base (ex: brazil_nut →
    # nut/default) introduit des valeurs factuellement incorrectes pour tous
    # les autres membres de la catégorie. Ce comportement est interdit.
    #
    # Conséquences :
    #   - Les bases sans variant "default" retournent no-match au resolver.
    #   - Les variants "default" doivent être créés EXPLICITEMENT dans
    #     patch_nutrition_v8.py avec des valeurs sourcées (CIQUAL/USDA).
    #   - La liste des bases concernées est visible via _diagnose_v2.py
    #     (section "missing_default").
    #
    # Historique : génération automatique supprimée le 2026-04-28 après
    # audit — causait macro_sum_impossible (nut) et energy_mismatch (sauce)
    # par contamination de variants non représentatifs.
    # ─────────────────────────────────────────────────────────────────────────

        # ── SEED_INGREDIENTS ──────────────────────────────────────────────────────
    # Ingrédients présents dans l'ontologie mais absents de nutrition_v2 à cause
    # de bugs de mapping dans build_ontology (mauvaise clé slug, clé manquante
    # dans ALIM_ALIASES, ou contamination par homonymes).
    # Pour chaque entrée : onto_key = clé dans l'ontologie,
    #                      variant  = variante à utiliser comme base,
    #                      meta     = bloc _meta à injecter dans n2.
    # La boucle crée un squelette minimal si la clé est absente de n2 ;
    # auto_correct l'enrichit ensuite normalement dans la boucle principale.
    SEED_INGREDIENTS: dict[str, dict] = {
        "ancho_chili": {
            "onto_key": "ancho_chili",
            "variant":  "dried",
            "meta": {
                "category": "vegetable",
                "name_fr": "piment ancho",
                "scientific_name": "Capsicum annum",
                "is_standalone": True,
            },
        },
        "chinese_cabbage": {
            "onto_key": "napa_cabbage_pe_tsai",
            "variant":  "raw",
            "meta": {
                "category": "vegetable",
                "name_fr": "chou chinois pé-tsaï",
                "scientific_name": "Brassica rapa subsp. pekinensis",
                "is_standalone": True,
            },
        },
        "dandelion": {
            "onto_key": "dandelion",
            "variant":  "raw",
            "meta": {
                "category": "vegetable",
                "name_fr": "pissenlit",
                "scientific_name": "Taraxacum spp.",
                "is_standalone": True,
            },
        },
        "chicory": {
            "onto_key": "chicory",
            "variant":  "raw",          # raw = feuilles fraîches (23 kcal) — après fix CIQUAL_EXCLUDE
            "meta": {
                "category": "vegetable",
                "name_fr": "chicorée (feuilles)",
                "scientific_name": "Cichorium intybus",
                "is_standalone": True,
            },
        },
        "dried_pea": {
            "onto_key": "split_peas",
            "variant":  "default",
            "meta": {
                "category": "legume",
                "name_fr": "pois sec",
                "scientific_name": "Pisum sativum",
                "is_standalone": True,
            },
        },
    }

    _seeded = 0
    for seed_key, seed_conf in SEED_INGREDIENTS.items():
        if seed_key in ingredients:
            # Déjà présent — vérifier que variants["default"] a bien des données.
            # Un run précédent peut avoir créé l'entrée sous une clé "raw"/"dried"
            # (invisible au validator qui lit toujours variants["default"]).
            existing_default = ingredients[seed_key].get("variants", {}).get("default", {})
            if existing_default.get("calories_kcal") is not None:
                continue   # default présent et renseigné → pas d'écrasement
            # Sinon : default absent ou vide → reseed sous "default"

        onto_key = seed_conf["onto_key"]
        var_key  = seed_conf["variant"]
        onto_entry = ontology.get(onto_key, {})
        onto_var   = onto_entry.get(var_key) or onto_entry.get("default") or {}
        if not onto_var:
            # Aucune variante disponible dans l'ontologie → seed vide (sera enrichi après)
            onto_var = {}

        nutrients = onto_var.get("nutrients", onto_var)  # ontology_v6 aplatit sous "nutrients"
        # Construire un squelette n2 minimal — auto_correct remplira le reste
        skeleton_variant = {
            "name_fr":         seed_conf["meta"].get("name_fr", seed_key),
            "name_en":         seed_key,
            "scientific_name": seed_conf["meta"].get("scientific_name"),
            "aliases":         [],
            "source_key":      seed_key,
            "ingredient_type": var_key,
            "calories_kcal":   nutrients.get("calories_kcal"),
            "protein_g":       nutrients.get("protein_g"),
            "carbs_g":         nutrients.get("carbs_g"),
            "fat_g":           nutrients.get("fat_g"),
            "fiber_g":         nutrients.get("fiber_g"),
            "sugar_g":         nutrients.get("sugar_g"),
            "sodium_mg":       nutrients.get("sodium_mg"),
            "confidence":      0.80,
            "_seeded_from":    f"ontology:{onto_key}/{var_key}",
        }
        # Toujours injecter sous "default" — convention n2 lue par le validator
        # et le resolver. ingredient_type conserve la trace de l'état réel.
        ingredients[seed_key] = {
            "_meta":    seed_conf["meta"],
            "variants": {"default": skeleton_variant},
        }
        _seeded += 1
        if not dry_run:
            print(f"  [SEED] {seed_key} ← ontology:{onto_key}/{var_key}")

    if _seeded:
        print(f"  Seeded {_seeded} ingrédients absents de n2 depuis l'ontologie")
    # ─────────────────────────────────────────────────────────────────────────

    # ── PURGE DES CHAMPS NUTRITIONNELS FLAT-LEVEL (audit 2026-04-28) ────────
    # L'ontologie écrit des champs nutritionnels directement sur la base (hors
    # variants) pour les bases non-standalone. validate_internal les lit en
    # fallback quand default est absent → faux macro_sum_impossible (ex: nut).
    # On les supprime ici : la donnée exacte est dans variants, pas au flat level.
    _NUTRITIONAL_FLAT_FIELDS = {
        'calories_kcal', 'calories', 'protein_g', 'carbs_g', 'fat_g', 'fiber_g',
        'sugar_g', 'starch_g', 'saturated_fat_g', 'monounsaturated_fat_g',
        'polyunsaturated_fat_g', 'omega3_g', 'omega6_g', 'cholesterol_mg',
        'sodium_mg', 'calcium_mg', 'iron_mg', 'magnesium_mg', 'phosphorus_mg',
        'potassium_mg', 'zinc_mg', 'copper_mg', 'manganese_mg', 'selenium_ug',
        'vitamin_a_ug', 'vitamin_b1_mg', 'vitamin_b2_mg', 'vitamin_b3_mg',
        'vitamin_b5_mg', 'vitamin_b6_mg', 'folate_ug', 'vitamin_b12_ug',
        'vitamin_c_mg', 'vitamin_d_ug', 'vitamin_e_mg', 'vitamin_k1_ug',
        'glycemic_index', 'glycemic_load', 'nova_group', 'health_score',
        'added_sugar', 'alcohol_g',
    }
    _flat_purged = 0
    for _base_key, _base_data in ingredients.items():
        _has_variants = bool(_base_data.get('variants'))
        _flat_nutrition = [k for k in _base_data if k in _NUTRITIONAL_FLAT_FIELDS]
        if _flat_nutrition and _has_variants:
            if not dry_run:
                for _fk in _flat_nutrition:
                    del _base_data[_fk]
            _flat_purged += len(_flat_nutrition)
    if _flat_purged:
        print(f"  Champs flat-level purgés : {_flat_purged} (données dans variants uniquement)")

        # ── SCAN DE DÉCONTAMINATION SENTINELLES ACAÏ ─────────────────────────────
    # Les valeurs sentinelles (fat_g=20.7, sat=2.99, calcium=206, etc.) peuvent
    # être figées dans la DB depuis un run précédent sans guards.
    # On les nullifie ici pour que la boucle de correction/enrichissement
    # puisse ré-injecter les vraies valeurs depuis l'ontologie.
    _FAT_SENTINEL_OK_CATS = {"nut", "seed", "oil", "fat", "dairy", "chocolate"}
    _decontam_count = 0
    for _ing_key, _ing_data in ingredients.items():
        if _ing_key == "acai":
            continue
        _cat = _ing_data.get("_meta", {}).get("category", "") or ""
        _fat_ok = _cat in _FAT_SENTINEL_OK_CATS
        for _var_key, _variant in _ing_data.get("variants", {}).items():
            # fat_g sentinel
            _fat = _variant.get("fat_g")
            if _fat is not None and not _fat_ok:
                try:
                    if abs(float(_fat) - 20.7) < 0.01:
                        if not dry_run:
                            _variant["fat_g"] = None
                        # sat_g sentinel si présent
                        _sat = _variant.get("saturated_fat_g")
                        if _sat is not None and abs(float(_sat) - 2.99) < 0.005:
                            if not dry_run:
                                _variant["saturated_fat_g"] = None
                        _decontam_count += 1
                except (TypeError, ValueError):
                    pass
            # Autres sentinelles ultra-spécifiques acaï
            for _fld, (_sv, _tol) in {
                "calcium_mg":   (206.0,  0.1),
                "potassium_mg": (2520.0, 1.0),
                "magnesium_mg": (429.0,  0.5),
                "omega3_g":     (1.45,   0.005),
                "selenium_ug":  (11.0,   0.05),
            }.items():
                _v = _variant.get(_fld)
                if _v is not None:
                    try:
                        if abs(float(_v) - _sv) < _tol and not dry_run:
                            _variant[_fld] = None
                    except (TypeError, ValueError):
                        pass
    print(f"  Décontamination acaï : {_decontam_count} variants nettoyés")
    # ─────────────────────────────────────────────────────────────────────────

    # Pre-calcul index categorie (substitution same_category)
    _cat_index: dict[str, list[str]] = {}
    for _k, _v in ingredients.items():
        _cat = _v.get("_meta", {}).get("category") or ""
        _cat_index.setdefault(_cat, []).append(_k)

    for ing_key, ing_data in ingredients.items():
        category = ing_data.get("_meta", {}).get("category")

        for var_key, variant in ing_data.get("variants", {}).items():
            name      = variant.get("name_fr") or variant.get("name_en") or ing_key
            base, det = resolve_key(name, mapping)
            onto_entry = ontology.get(base, {})

            # Résolution variant dans ontologie
            onto_var = pick_variant(onto_entry, var_key if var_key != "default" else det)

            # Extraire onto_stats (dict {field: {n_sources, std, min, max}})
            # disponible dans les ontologies v6 sous la clé "stats"
            onto_stats: dict = onto_var.get("stats", {}) if onto_var else {}

            # ── _source_meta : métadonnées de provenance des données onto ────
            if onto_var and not dry_run:
                n_src_set = {
                    v.get("n_sources", 1)
                    for v in onto_stats.values()
                    if isinstance(v, dict)
                }
                n_sources_onto = max(n_src_set) if n_src_set else (1 if onto_var else 0)
                variant["_source_meta"] = {
                    "onto_base":       base,
                    "onto_variant":    var_key if var_key != "default" else det,
                    "n_sources_onto":  n_sources_onto,
                    "has_stats":       bool(onto_stats),
                }

            # ── 1. CORRECTIONS SOURCES (champs existants déviants) ────────────
            if onto_var:
                nutrients = onto_var.get("nutrients", onto_var)  # v6 vs v5

                # ── Guard THRESHOLD_PROTECT ────────────────────────────────────
                # Ne pas écraser les données mesurées/exactes avec un proxy.
                # Un ingrédient est protégé si :
                #   - data_quality ∈ {"exact", "measured"} : données saisies à la main
                #     ou issues d'une source primaire fiable ;
                #   - source_priority >= THRESHOLD_PROTECT : valeur mesurée certifiée.
                #   - confidence >= 0.85 ET data_quality = "estimated" : estimation
                #     haute-confiance (ex: kashk, paneer) — proxy ontologie moins fiable.
                # Dans ce cas, la correction de sources (étape 1) est entièrement
                # sautée. L'enrichissement des champs null (étape 2) reste actif.
                _dq = variant.get("data_quality", "")
                _sp = SOURCE_PRIORITY.get(variant.get("_source_priority", "unknown"), 0)
                _conf = float(variant.get("confidence", 0) or 0)
                _is_protected = (
                    _dq in ("exact", "measured")
                    or _sp >= THRESHOLD_PROTECT
                    or (_dq == "estimated" and _conf >= 0.85)
                )

                for v2_field, onto_key in FIELD_MAP.items():
                    current = variant.get(v2_field)
                    reference = nutrients.get(v2_field) or nutrients.get(onto_key)
                    if current is None or reference is None:
                        continue

                    # Champ existant + ingrédient protégé → skip correction source.
                    # L'enrichissement (étape 2) prendra le relais pour les champs null.
                    if _is_protected and current is not None:
                        continue

                    threshold = DEFAULT_THRESHOLDS.get(onto_key, 0.25)
                    delta = compute_delta(current, reference)
                    if delta > threshold:
                        # ── Garde-fou fat_g : rejeter si conflit avec sub-composants ──
                        # Si on propose de changer fat_g et que la nouvelle valeur est
                        # > FAT_SANITY_MAX_RATIO × sub_total existants → source_conflict.
                        if v2_field == "fat_g":
                            sat_ex  = variant.get("saturated_fat_g") or 0.0
                            mono_ex = variant.get("monounsaturated_fat_g") or 0.0
                            poly_ex = variant.get("polyunsaturated_fat_g") or 0.0
                            sub_total = sat_ex + mono_ex + poly_ex
                            if sub_total > 0 and reference > sub_total * FAT_SANITY_MAX_RATIO:
                                corrections_log.append({
                                    "ingredient": ing_key,
                                    "variant": var_key,
                                    "field": v2_field,
                                    "current": current,
                                    "reference": reference,
                                    "delta_pct": round(delta * 100, 1),
                                    "action": "rejected_source_conflict",
                                    "reason": (
                                        f"fat_sanity: proposed={reference} > "
                                        f"{FAT_SANITY_MAX_RATIO}× sub_total={round(sub_total,4)} "
                                        f"— possible bad USDA match, fat_g unchanged"
                                    ),
                                })
                                continue  # ne pas écraser fat_g

                        corrections_log.append({
                            "ingredient": ing_key,
                            "variant": var_key,
                            "field": v2_field,
                            "current": current,
                            "reference": reference,
                            "delta_pct": round(delta * 100, 1),
                            "action": "replace",
                        })
                        if not dry_run:
                            variant[v2_field] = reference
                        corrected += 1

            # ── 1b. INJECTION PROFILS LIPIDIQUES MESURÉS ─────────────────────
            # Priorité absolue : remplace les valeurs issues de match automatique.
            lip_key = (ing_key, var_key)
            if lip_key in KNOWN_LIPID_PROFILES:
                sat, mono, poly, o3, o6, src_ref = KNOWN_LIPID_PROFILES[lip_key]
                for field, val in [
                    ("saturated_fat_g", sat), ("monounsaturated_fat_g", mono),
                    ("polyunsaturated_fat_g", poly), ("omega3_g", o3), ("omega6_g", o6),
                ]:
                    current = variant.get(field)
                    if current != val:
                        corrections_log.append({
                            "ingredient": ing_key, "variant": var_key,
                            "field": field,
                            "current": current, "reference": val,
                            "delta_pct": round(abs((val - (current or 0)) / max(abs(val), 0.001)) * 100, 1),
                            "action": "replace",
                            "reason": f"known_lipid_profile: {src_ref}",
                        })
                        if not dry_run:
                            variant[field] = val
                        corrected += 1

            # ── 1c. MANUAL OVERRIDES ──────────────────────────────────────────
            # Valeurs figées manuellement — priorité absolue sur ontologie ET
            # profils lipidiques automatiques. Utilisé pour corriger les artefacts
            # de fusion multi-source non traitables algorithmiquement.
            _mo_variants = MANUAL_OVERRIDES.get(ing_key, {})
            _mo_fields   = _mo_variants.get(var_key) or _mo_variants.get("default") or {}
            for mo_field, mo_val in _mo_fields.items():
                current_mo = variant.get(mo_field)
                if current_mo != mo_val:
                    corrections_log.append({
                        "ingredient": ing_key,
                        "variant":    var_key,
                        "field":      mo_field,
                        "current":    current_mo,
                        "reference":  mo_val,
                        "delta_pct":  round(
                            abs((mo_val - (current_mo or 0)) / max(abs(mo_val), 0.001)) * 100, 1
                        ),
                        "action":  "replace",
                        "reason":  "manual_override",
                    })
                    if not dry_run:
                        variant[mo_field] = mo_val
                    corrected += 1

            # ── 2. ENRICHISSEMENT CHAMPS NULLS DEPUIS SOURCES ─────────────────
            if onto_var:
                nutrients = onto_var.get("nutrients", onto_var)
                null_fields_filled = []
                # Bloquer l'enrichissement depuis des bases suspectes
                _onto_base_blocked = base in _ENRICHMENT_BLOCKED_BASES
                for v2_field, onto_key in FIELD_MAP.items():
                    if variant.get(v2_field) is None:
                        ref_val = nutrients.get(v2_field) or nutrients.get(onto_key)
                        if ref_val is not None:
                            # ── Garde-fou acaï : rejeter enrichissement suspect ──
                            if _onto_base_blocked or _is_acai_contamination(v2_field, ref_val):
                                enriched_log.append({
                                    "ingredient": ing_key, "variant": var_key,
                                    "field": v2_field,
                                    "ref_val": ref_val,
                                    "action": "rejected_acai_sentinel",
                                })
                                continue
                            if not dry_run:
                                variant[v2_field] = ref_val
                            null_fields_filled.append(v2_field)
                            enriched += 1
                if null_fields_filled:
                    enriched_log.append({
                        "ingredient": ing_key, "variant": var_key,
                        "fields_filled": null_fields_filled
                    })

                # scientific_name depuis ontologie
                if variant.get("scientific_name") is None:
                    sci = nutrients.get("scientific_name")
                    if sci and not dry_run:
                        variant["scientific_name"] = sci
                        ing_data["_meta"]["scientific_name"] = sci

            # ── 3. ENRICHISSEMENT CHAMPS CALCULÉS ────────────────────────────

            # energy_kj — conversion depuis calories_kcal si absent
            if variant.get("energy_kj") is None and variant.get("calories_kcal") is not None:
                if not dry_run:
                    variant["energy_kj"] = round(variant["calories_kcal"] * 4.184, 1)
                enriched += 1

            # nova_group
            if variant.get("nova_group") is None:
                nova = compute_nova_group({**variant, "category": category})
                if nova is not None and not dry_run:
                    variant["nova_group"] = nova
                    enriched += 1

            # health_score
            if variant.get("health_score") is None:
                score = compute_health_score(variant)
                if score is not None and not dry_run:
                    variant["health_score"] = score
                    enriched += 1

            # bioavailability_protein
            if variant.get("bioavailability_protein") is None:
                bio = compute_bioavailability(category, variant.get("ingredient_type"))
                if bio is not None and not dry_run:
                    variant["bioavailability_protein"] = bio
                    enriched += 1

            # glycemic_load
            if variant.get("glycemic_load") is None:
                gl = compute_glycemic_load(
                    variant.get("glycemic_index"),
                    variant.get("carbs_g")
                )
                if gl is not None and not dry_run:
                    variant["glycemic_load"] = gl
                    enriched += 1

            # glycemic_index_source
            if variant.get("glycemic_index_source") is None:
                gi_src = infer_glycemic_index_source(variant)
                if gi_src and not dry_run:
                    variant["glycemic_index_source"] = gi_src
                    enriched += 1

            # alcohol_g : aliments non-alcoolisés → 0.0 par défaut
            if variant.get("alcohol_g") is None:
                ing_type = variant.get("ingredient_type", "raw")
                if ing_type in ("raw", "fresh", "dried", "roasted", "frozen", "cooked", "ground"):
                    if not dry_run:
                        variant["alcohol_g"] = 0.0
                    enriched += 1

            # ── 4. CORRECTIONS BIOLOGIQUES ────────────────────────────────────
            # Ces règles s'appliquent indépendamment des sources externes.

            # 4a. Lait animal — fiber et starch biologiquement nuls
            if ing_key in ANIMAL_MILK_KEYS:
                for bio_field in ("fiber_g", "starch_g"):
                    val = variant.get(bio_field)
                    if val is not None and val != 0:
                        corrections_log.append({
                            "ingredient": ing_key,
                            "variant": var_key,
                            "field": bio_field,
                            "current": val,
                            "reference": 0.0,
                            "delta_pct": 100.0,
                            "action": "replace",
                            "reason": "bio_rule: lait animal = 0",
                        })
                        if not dry_run:
                            variant[bio_field] = 0.0
                        corrected += 1

            # 4b. Végétaux — cholestérol = 0
            if category in BIO_PLANT_CATEGORIES:
                chol = variant.get("cholesterol_mg")
                if chol is not None and chol != 0:
                    corrections_log.append({
                        "ingredient": ing_key,
                        "variant": var_key,
                        "field": "cholesterol_mg",
                        "current": chol,
                        "reference": 0.0,
                        "delta_pct": 100.0,
                        "action": "replace",
                        "reason": "bio_rule: végétal = 0 cholestérol",
                    })
                    if not dry_run:
                        variant["cholesterol_mg"] = 0.0
                    corrected += 1

            # 4c. Noix/graines brutes — sodium aberrant (> 50 mg)
            if category == "fat" and ing_key not in BIO_FAT_SODIUM_EXCEPTIONS:
                sod = variant.get("sodium_mg")
                if sod is not None and sod > BIO_FAT_SODIUM_THRESHOLD:
                    corrections_log.append({
                        "ingredient": ing_key,
                        "variant": var_key,
                        "field": "sodium_mg",
                        "current": sod,
                        "reference": 1.0,
                        "delta_pct": round((sod - 1) / max(sod, 1) * 100, 1),
                        "action": "replace",
                        "reason": f"bio_rule: sodium > {BIO_FAT_SODIUM_THRESHOLD} mg pour noix/graine brute",
                    })
                    if not dry_run:
                        variant["sodium_mg"] = 1.0
                    corrected += 1

            # 4d. data_field_type — hiérarchie de confiance lipidique
            # Catégorise la qualité des données lipidiques sans modifier les valeurs.
            # raw            : données cohérentes (ratio sub/fat > 0.7)
            # fa_incomplete  : PUFA partiellement renseigné (ratio 0.15–0.7)
            # source_conflict: fat_g et sub-composants issus de sources incompatibles
            #                  (ratio < 0.15) — fat_g potentiellement contaminé
            fat_val  = variant.get("fat_g") or 0.0
            sat_val  = variant.get("saturated_fat_g") or 0.0
            mono_val = variant.get("monounsaturated_fat_g") or 0.0
            poly_val = variant.get("polyunsaturated_fat_g") or 0.0
            sub_total = sat_val + mono_val + poly_val

            if fat_val <= 0.3 or sub_total <= 0:
                dft = "raw"
            else:
                ratio = sub_total / fat_val
                if ratio < 0.15:
                    dft = "source_conflict"
                elif ratio < 0.70:
                    dft = "fa_incomplete"
                else:
                    dft = "raw"

            # Profils injectés → raw (mesurés)
            if (ing_key, var_key) in KNOWN_LIPID_PROFILES:
                dft = "raw"

            if not dry_run:
                variant["data_field_type"] = dft

            # 4e. Omega cap — omega ⊂ PUFA (règle biologique stricte)
            # Ne pas scaler les FA. Seulement cap si omega > poly : données incohérentes.
            # Si poly=0 et omega>0 → zeroing (biologiquement impossible).
            poly_post  = variant.get("polyunsaturated_fat_g") or 0.0
            omega3_v   = variant.get("omega3_g") or 0.0
            omega6_v   = variant.get("omega6_g") or 0.0
            total_omega = omega3_v + omega6_v
            if total_omega > poly_post + 0.01:
                new_o3 = round(omega3_v * (poly_post / total_omega), 4) if poly_post > 0 else 0.0
                new_o6 = round(omega6_v * (poly_post / total_omega), 4) if poly_post > 0 else 0.0
                for field, old_v, new_v in [("omega3_g", omega3_v, new_o3), ("omega6_g", omega6_v, new_o6)]:
                    if old_v != new_v:
                        corrections_log.append({
                            "ingredient": ing_key, "variant": var_key,
                            "field": field,
                            "current": old_v, "reference": new_v,
                            "delta_pct": round(abs(new_v - old_v) / max(old_v, 0.001) * 100, 1),
                            "action": "replace",
                            "reason": f"bio_rule: omega_cap poly={poly_post} (omega ⊂ PUFA)",
                        })
                        if not dry_run:
                            variant[field] = new_v
                        corrected += 1

            # ── 5. diet_profile ─────────────────────────────────────────────────
            if not dry_run:
                variant["diet_profile"] = compute_diet_profile(
                    variant.get("name_en") or "",
                    variant.get("name_fr") or "",
                    category,
                    variant.get("ingredient_type"),
                )

            # ── 6. allergen_flags (EU 14) ────────────────────────────────────────
            if not dry_run:
                _ing_key = f"{ing_key}/{var_key}" if var_key != "default" else ing_key
                variant["allergen_flags"] = compute_allergen_flags(
                    variant.get("name_en") or "",
                    variant.get("name_fr") or "",
                    category,
                    ingredient_key=_ing_key,
                )

            # ── 7. nutrition_flags (EU 1924/2006) ────────────────────────────────
            if not dry_run:
                variant["nutrition_flags"] = compute_nutrition_flags(variant)

            # ── 8. cooking_profile ───────────────────────────────────────────────
            if not dry_run:
                onto_vkeys = list(onto_entry.keys()) if onto_entry else []
                variant["cooking_profile"] = compute_cooking_profile(
                    variant, category,
                    variant.get("ingredient_type"),
                    onto_vkeys,
                    onto_stats=onto_stats,
                )

            # ── 9. reco_context ──────────────────────────────────────────────────
            if not dry_run:
                variant["reco_context"] = compute_reco_context(variant)

            # ── 10. nutrients_v6 — restructuration v6 depuis champs plats ────────
            # Construit le bloc structuré attendu par validator_v12 _read_all_nutrients().
            # Idempotent : recompute à chaque run depuis les champs plats.
            if not dry_run:
                variant["nutrients_v6"] = compute_nutrients_v6(variant)

            # ── 11. state — inférence depuis variant_key + catégorie ─────────────
            # Génère {"process": {"level1": "raw|cooked|...", "confidence": "..."}}
            # Utilisé par validate_v6_blocks() du validator_v12.
            if not dry_run:
                cp = variant.get("cooking_profile")
                variant["state"] = compute_state(var_key, category, cp)

    # ── 10. substitution (niveau ingredient, apres toutes les variantes) ────────
    if not dry_run:
        for ing_key2, ing_data2 in ingredients.items():
            cat2 = ing_data2.get("_meta", {}).get("category")
            ing_data2["substitution"] = compute_substitution_same_category(
                ing_key2, cat2, _cat_index
            )

    # ── Mise a jour version ───────────────────────────────────────────────────
    if not dry_run:
        db["schema_version"] = "6.0"  # aligné CIQUAL v3 (7.0) / USDA v2 (6.0) / CNF v10 (6.0)
        db["generated_at"] = datetime.now().strftime("%Y-%m-%d")
        db["changelog"] = db.get("changelog", {})
        db["changelog"]["v3.7"] = [
            "auto_correct_v6.3 : data truth — source priority + sanity checks",
            "AJOUT : SOURCE_PRIORITY + KNOWN_LIPID_PROFILES (valeurs mesurees, priorite absolue)",
            "AJOUT : FAT_SANITY guard — fat_g rejete si >5x sub_total existants",
            "AJOUT : data_field_type (raw|fa_incomplete|source_conflict)",
            "AJOUT : 4e omega_cap biologique — cap sans scaling (omega dans PUFA)",
        ]
        db["changelog"]["v4.0"] = [
            "Schema v4.0 : 6 nouveaux blocs derives des donnees sources",
            "AJOUT : diet_profile (vegetarian/vegan/egg_free/dairy_free/gluten_free/nut_free/soy_free/fermented)",
            "AJOUT : allergen_flags (EU 14 allergenes, Reglement 1169/2011)",
            "AJOUT : nutrition_flags (labels EU 1924/2006 : high_fiber, good_source_iron, low_sodium...)",
            "AJOUT : cooking_profile (typical_states, refuse_pct, yield_cooked_pct, culinary_role...)",
            "AJOUT : reco_context (energy_density, satiety_score, micronutrient_richness, omega ratios)",
            "AJOUT : substitution (same_category auto + alternatives curatedees veg/vegan)",
            "AJOUT : data_field_type sur toutes les variantes",
        ]

        # Backup
        if OUTPUT_FILE.exists():
            backup = OUTPUT_FILE.with_suffix(f".{datetime.now():%Y%m%d_%H%M%S}.bak.json")
            shutil.copy2(OUTPUT_FILE, backup)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"\n✓ nutrition_corrected.json → {OUTPUT_FILE}")

    # Log
    log = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": dry_run,
        "stats": {
            "corrections": corrected,
            "enrichments": enriched,
            "ingredients_processed": len(ingredients),
        },
        "corrections": corrections_log,
        "enrichments": enriched_log,
    }
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"  Corrections sources  : {corrected}")
    print(f"  Enrichissements      : {enriched}")
    print(f"✓ Log → {LOG_FILE}")
    print("═" * 70)

    return log


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv or "--dry" in sys.argv
    if dry:
        print("MODE DRY-RUN : aucune écriture")
    result = auto_correct(dry_run=dry)
    print(f"\nTerminé : {result['stats']['corrections']} corrections, "
          f"{result['stats']['enrichments']} enrichissements")