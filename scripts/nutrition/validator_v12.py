"""
╔══════════════════════════════════════════════════════════════════════════╗
║         NUTRITION VALIDATOR V12 — validator_v12.py                       ║
║                                                                          ║
║  But : valider et corriger nutrition_database_cleaned_final.json         ║
║        en croisant avec CIQUAL 2025 (ANSES) + USDA FoodData Central      ║
║                                                                          ║
║  Sources gratuites :                                                     ║
║    CIQUAL  → https://ciqual.anses.fr/#/cms/telechargement/node/20        ║
║              Télécharger "Table Ciqual 2025_FR_2025_11_03" (.xlsx)       ║
║    USDA    → https://fdc.nal.usda.gov/download-foods.html                ║
║              Foundation Foods JSON (recommandé) ou CSV                   ║
║           OU clé API gratuite : fdc.nal.usda.gov/api-key-signup.html     ║
║                                                                          ║
║  Sans ces fichiers : validation interne uniquement (déjà utile)          ║
╚══════════════════════════════════════════════════════════════════════════╝

WORKFLOW :
  Étape 1 → python validator_v12.py --audit
            Audit rapide interne, sans source externe.

  Étape 2 → Télécharger CIQUAL et/ou USDA (gratuit, voir URLs ci-dessus)
            Placer dans : sources/

  Étape 3 → python validator_v12.py
            Validation croisée → génère :
              outputs/validation_report.json
              outputs/correction_proposals.json

  Étape 4 → Ouvrir correction_proposals.json
            Changer "action": "replace" → "keep" pour refuser

  Étape 5 → python validator_v12.py --apply [--severity=critical] [--score=0.90]
            Sauvegarde automatique avant application.
            → outputs/nutrition_database_corrected.json

  Étape 6 → python validator_v12.py --diff
            Compare la DB originale et la version corrigée.

  Étape 7 → python validator_v12.py --clean
            Retire les champs _correction_* de la DB corrigée.

  Étape 8 → python validator_v12.py --enrich
            Enrichit ingredients_dictionary.json avec alim_nom_sci + name_en
            → outputs/ingredients_dictionary_enriched.json

NOUVEAUTÉS V10 (vs V9) :
  - validate_internal : saturated_fat > fat, somme macros > 105, limites absolues
  - validate_internal : micronutriments aberrants (sodium > 38 000 mg, calcium > 2 000 mg)
  - FORMULA_EXCEPTIONS complétées : matcha, cocoa, psyllium, chia_seed, chlorella, spirulina
  - USDA_NUTRIENT_IDS étendu : zinc, sélénium, vitamine C, vitamine B12
  - merge_proposals : pondération source_rank × match_score (CIQUAL à 0.76 < USDA à 1.0)
  - USDALoader.lookup : partial_ratio retiré (trop permissif), seuil WRatio resserré
  - run_validation : barre de progression + rapport de couverture
  - apply_corrections : sauvegarde automatique avant application
  - Nouveau mode --diff : visualise les changements effectués
  - Nouveau mode --clean : retire les champs _correction_* de la DB
  - enrich_dictionary : correction doublon label "Priorité 3" → "Priorité 4"

NOUVEAUTÉS V11 (vs V10) :
  - NUTRITION_DB_FILE : pointe vers nutrition_v2.json (schema hiérarchique base/variant)
      au lieu de nutrition_clean.json (schema plat v1 — obsolète)
  - validate_internal : lecture des champs avec fallback variants.default
      → support natif du schema v2 sans casser la rétro-compat flat
  - FIELDS étendu : ajout vitamin_c, vitamin_a, vitamin_d
  - USDA_NUTRIENT_IDS étendu : vitamin_a (ID 1106, RAE), vitamin_d (ID 1114, D2+D3)

NOUVEAUTÉS V12 (vs V11) :
  - BUGFIX : validate_internal/missing_field utilisait data.get() au lieu de _get()
      → ignorait variants.default → 1160 faux warnings sur tous les ingrédients
  - BUGFIX : USDA_CSV désormais défini dans la config (NameError latent en mode
      validation croisée quand usda_flat_v2.json absent)
  - NUTRITION_CORRECTED_FILE : chemin vers nutrition_corrected.json produit par
      auto_correct_v6.py — utilisé en priorité si le fichier existe
  - load_local_db / quick_audit : sélection automatique corrected > v2 > fallback
  - CLI --input=<path> : forcer un fichier source spécifique
      ex: python validator_v12.py --audit --input nutrition_corrected.json
  - run_validation / apply_corrections : version string "v10" → "v11" corrigé
  - FIBER_GT_CARBS_EXCEPTIONS : 35 ingrédients exemptés du check fiber_gt_carbs
      (glucides disponibles schéma CIQUAL — fiber > carbs est valide)
  - CATEGORY_INGREDIENTS : ~30 types ombrelle exemptés du check missing_field
      (flour, milk_animal, oil… résolus au rendu recette, pas de données directes)


NOUVEAUTÉS V12 (vs V11/V15/V16) :
  - BUGFIX 1 : NameError normalize — normalize() et normalize_col() déplacés
      en section 1b (avant toute classe). Corrige la version V16 refactorisée
      où les classes étaient déclarées avant les utils.
  - BUGFIX 2 : 108 propositions erronées (audit 2026-04)
    a) FUZZY_SCORE_OVERRIDES — seuils stricts par ingrédient (salt→1.0,
       almond/coconut→0.95, milk/rice/bean/seeds/sorghum/maca→0.92…)
    b) _detect_multi_field_contamination — détecte les faux matches de
       variante (≥3 minéraux avec ratio <0.2 ou >5 simultanément)
    c) INGREDIENT_PLAUSIBLE_RANGES / CATEGORY_PLAUSIBLE_RANGES — bornes
       physiologiques contextuelles (salt.sodium min=30000, almond.potassium
       min=500…) rejetant les valeurs hors plage avant merge_proposals
    d) _EXTENDED_SENTINELS — sentinelles étendues pour sel iodé, riz enrichi,
       haricots conserve, etc. (score < 0.85 → rejet)
    e) compare_to_source accepte ingredient_name pour appliquer les gardes c/d
    f) run_validation : stats dédiées (proposals_rejected_score,
       proposals_rejected_contamination) + seuil effectif par ingrédient

NOUVEAUTÉS V15 (vs V13) :
  - BUGFIX CRITIQUE — triple contamination "Farine de soja complète" (ciqual_code=20915) :
      Bug 1 : lookup_by_name — pénalité longueur utilisait > au lieu de >=.
              Pour q_words=2, m_words=4 : 4 > 4 = False → pas de pénalité.
              Score 85.7 passait FUZZY_THRESHOLD=75 → match accepté à tort.
              Fix : if m_words >= q_words * 2 (pénalité si cible ≥ double requête).
      Bug 2 : compare_to_source — _ACAI_SENTINELS actif uniquement pour dec=None.
              Pour corrections (dec≠None), protein=34.5/fat=20.7/etc. non filtrés.
              Fix : garde sentinelle universelle avant la branche enrichissement.
      Bug 3 : compare_to_source — MIN_SCORE_MACRO_ENRICHMENT(0.92) aussi
              réservé à dec=None. Score=0.857 suffisait à corriger les macros.
              Fix : garde MIN_SCORE appliquée aux enrichissements ET corrections.
  - Ces trois bugs combinés généraient 200 propositions erronées identiques
    (même match_score=0.857, mêmes valeurs) pour tous les ingrédients dont
    le nom_fr normalisé ≥ 2 tokens. Aucune ne devait être appliquée.


  - validate_internal : lipid_sub_incoherence — sat+mono+poly << fat_g
      → warning  si ratio 0.15–0.45 (fa_incomplete : vrais suspects, fusion incomplète)
      → critical si ratio < 0.15  (source_conflict : contamination probable)
      → ignoré si sub=0 ou fat≤0.3 g
  - validate_internal : omega_gt_poly — omega3+omega6 > poly_g (critical)
      → biologiquement impossible (omega ⊂ PUFA)
  - validate_internal : data_truth_score (0–1) distinct du validation_score structurel
      → pénalise source_conflict (−0.15), fa_incomplete (−0.05), omega_gt_poly (−0.10)
  - quick_audit : affichage des 3 nouveaux types avec ratio et delta
  - Règles vérifiées (print) mises à jour
"""

import json
import os
import re
import unicodedata
import time
from pathlib import Path
from datetime import datetime
from typing import Optional

import pandas as pd
from rapidfuzz import process, fuzz

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False


# ══════════════════════════════════════════════════════════════════════════
# 1. CONFIG
# ══════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parents[2]

SOURCES_DIR = BASE_DIR / "sources"
OUTPUT_DIR  = BASE_DIR / "outputs"

NUTRITION_DB_FILE        = BASE_DIR / "backend" / "data" / "nutrition" / "processed" / "nutrition_v2.json"
# Sortie de auto_correct_v6.py
NUTRITION_CORRECTED_FILE = BASE_DIR / "backend" / "data" / "nutrition" / "reference" / "nutrition_corrected.json"
# Sortie de patch_nutrition_v8.py — priorite maximale (v14+, schema carbs_schema)
NUTRITION_PATCHED_FILE   = BASE_DIR / "backend" / "outputs" / "nutrition_patched_v8.json"
PHYSICAL_FILE            = BASE_DIR / "backend" / "data" / "ingredients" / "ingredient_physical.json"
DICT_FILE                = BASE_DIR / "backend" / "data" / "ingredients" / "ingredients_dictionary.json"

# Sources flat pre-normalisees (generees par les scripts d'export)
CIQUAL_FILE = BASE_DIR / "backend" / "data" / "nutrition" / "raw" / "ciqual_flat_v3.json"
USDA_JSON   = BASE_DIR / "backend" / "data" / "nutrition" / "raw" / "usda_flat_v2.json"
USDA_CSV    = BASE_DIR / "backend" / "data" / "nutrition" / "raw" / "usda_flat.csv"

USDA_API_KEY = os.environ.get("USDA_API_KEY", "")
USDA_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

TODAY = datetime.now().strftime("%Y-%m-%d")


def resolve_db_file(cli_input=None):
    """
    Resout le fichier nutrition a utiliser, par ordre de priorite :
      1. --input=<path> passe en CLI (absolu ou relatif a BASE_DIR)
      2. nutrition_patched_v7.json (sortie patch_nutrition_v7) si present  <- v14
      3. nutrition_corrected.json  (sortie auto_correct_v6)   si present
      4. nutrition_v2.json         (source canonique)
    """
    if cli_input:
        p = Path(cli_input)
        if not p.is_absolute():
            p = BASE_DIR / p
        if p.exists():
            return p
        raise FileNotFoundError(f"--input : fichier introuvable : {p}")
    if NUTRITION_PATCHED_FILE.exists():
        return NUTRITION_PATCHED_FILE
    if NUTRITION_CORRECTED_FILE.exists():
        return NUTRITION_CORRECTED_FILE
    return NUTRITION_DB_FILE

# Seuil score ÉLEVÉ pour enrichissements CIQUAL sur macros (current=None)
# 0.85 est insuffisant : un mauvais match fuzzy injecte silencieusement des données
# Ex: baking_powder → acai (score=0.85) → fat=20.7g, protein=34.5g absurdes
MIN_SCORE_MACRO_ENRICHMENT = 0.92

# Valeurs sentinelles acaï — injectées par contamination fuzzy CIQUAL
# Si proposed == valeur sentinelle ET current=None → rejet garanti
_ACAI_SENTINELS: dict[str, float] = {
    "fat":          20.7,
    "protein":      34.5,
    "omega3":        1.45,
    "calories":    457.0,
    "calcium":     206.0,
    "potassium":  2520.0,
    "magnesium":   429.0,
    "selenium":     11.0,
    "saturated_fat": 2.99,
    "fiber":         9.6,
    "zinc":          3.92,
}
# Champs macros soumis au seuil enrichissement élevé
_MACRO_FIELDS_STRICT = {
    "calories", "protein", "fat", "carbs", "fiber", "sugar",
    "saturated_fat", "omega3", "omega3_ala",
}

DELTA_WARN     = 15.0   # % → warning
DELTA_CRITICAL = 40.0   # % → critical
FUZZY_THRESHOLD = 75    # score minimum pour accepter un match fuzzy (0–100)

# ── V12 — Seuils de score minimum par ingrédient ─────────────────────────────
# Ingrédients pour lesquels le fuzzy match retourne systématiquement une mauvaise
# variante (conserve, fortifié, graine sèche, eau vs chair…).
# Valeur 1.0 = match exact uniquement. 0.92 = seuil strict (quasi-exact).
FUZZY_SCORE_OVERRIDES: dict[str, float] = {
    "salt":         1.0,   # NaCl pur → sel iodé/marin à score 0.771 → sodium 875 au lieu de 38758
    "almond":       0.95,  # amandes grillées salées vs crues (potassium 17 vs 713)
    "milk_animal":  0.92,  # boisson soja fortifiée à score 0.771
    "milk_plant":   0.92,
    "rice":         0.92,  # riz enrichi fortifié (vitamin_a 243 µg absurde)
    "bean":         0.92,  # haricots EN CONSERVE (sodium 440, calcium 845)
    "seeds":        0.92,  # graines salées/conditionnées
    "sorghum":      0.92,  # boisson fermentée sorgho
    "coconut":      0.95,  # EAU de coco (iron 0.04, zinc 0.02 vs chair 2.4/0.8)
    "garam_masala": 0.92,  # mélange d'épices dilué
    "maca":         0.92,  # maca poudre enrichie
    "okra":         0.85,
    "parsley":      0.85,
    "grain":        0.92,
    "sauce":        0.92,
    "mushroom":     0.92,  # shiitake vs champignon de Paris
    "bran":         0.85,
}

# ── V13 — Correspondances CIQUAL directes (court-circuitent le fuzzy) ────────
# Format : ingredient_key → ciqual_code (str).
# Codes vérifiés sur ciqual_flat_v3.json — audit manuel 2026-05.
# Priorité absolue sur ciqual_id_map (physical.json) et sur toute recherche fuzzy.
CIQUAL_ID_OVERRIDES: dict[str, str] = {
    "coconut":           "15006",  # Noix de coco, chair, fraîche  (fat=34.7g, iron=2.27mg)
    "comte":             "12110",  # Comté                          (Ca=907mg, Na=403mg)
    "jalapeno":          "20151",  # Piment, cru                    (vit_c=144mg, K=322mg)
    "dill":              "11093",  # Aneth, frais                   (protein=3.93g)
    "bran":              "9621",   # Son de blé                     (fiber=38.6g, iron=10.6mg)
    "nutritional_yeast": "11009",  # Levure de bière en paillettes  (protein=40.4g)
    "dried_raisins":     "13046",  # Raisin sec                     (K=960mg, carbs=73.2g)
    "sugar_snap_pea":    "20173",  # Pois mange-tout, cru           (vit_c=60mg, fiber=2.6g)
    "sorghum":           "9360",   # Sorgho complet, cru            (protein=10.6g, K=363mg)
    "chlorella":         "20997",  # Chlorelle séchée/déshydratée   (protein=48.5g)
    "pastry":            "23410",  # Pâte brisée, MG végétale, crue (fat=21.7g, carbs=42.7g)
}

# ── V13 — Seuil CNF (légèrement plus permissif — 1833 aliments bien normalisés)
CNF_SCORE_THRESHOLD = 0.82

# ── V12 — Bornes physiologiques par ingrédient ────────────────────────────────
INGREDIENT_PLAUSIBLE_RANGES: dict[str, dict[str, tuple]] = {
    "salt": {
        "sodium":      (30_000, 42_000),
        "calcium":     (0,      200),
        "vitamin_a":   (0,      5.0),
        "vitamin_b12": (0,      0.1),
        "iodine":      (0,      6000),
        "iron":        (0,      2.0),
        "potassium":   (0,      500),
        "magnesium":   (0,      100),
        "zinc":        (0,      1.0),
        "selenium":    (0,      5.0),
        "folate":      (0,      50),
    },
    "almond": {
        "potassium":   (500,   1000),
        "magnesium":   (200,    400),
        "calcium":     (200,    400),
        "sodium":      (0,       10),
        "zinc":        (2.0,    5.0),
        "iron":        (2.0,    5.0),
    },
    "coconut": {
        "iron":        (1.5,    4.0),
        "zinc":        (0.5,    2.0),
    },
    "parmesan": {
        "sodium":      (1200,  2000),
    },
}

CATEGORY_PLAUSIBLE_RANGES: dict[str, dict[str, tuple]] = {
    "salt": {
        "sodium":    (30_000, 42_000),
        "calcium":   (0,      200),
    },
    "vegetable": {
        "sodium":    (0,      500),
        "calcium":   (0,      500),
        "potassium": (0,     2000),
        "magnesium": (0,      200),
        "zinc":      (0,      5.0),
    },
    "nut": {
        "sodium":    (0,       50),
        "potassium": (50,    2000),
        "magnesium": (50,     500),
        "zinc":      (0.5,   10.0),
    },
    "cheese": {
        "sodium":    (100,   3000),
        "calcium":   (100,   2000),
    },
    "herb_spice": {
        "sodium":    (0,      500),
    },
}

# ── V12 — Sentinelles étendues (valeurs caractéristiques de matchs faux) ──────
_EXTENDED_SENTINELS: dict[str, list[float]] = {
    "sodium":      [875.0, 760.0],
    "calcium":     [845.0, 680.0],
    "vitamin_a":   [243.0, 320.0],
    "vitamin_b12": [1.6, 1.86],
    "iron":        [0.06, 0.12],
    "potassium":   [2.0, 17.2],
    "magnesium":   [6.86, 4.26],
    "zinc":        [0.071, 0.07, 0.02, 0.08],
    "iodine":      [0.67, 10.0, 37.3],
}
_EXTENDED_SENTINEL_SCORE_THRESHOLD = 0.85



# ──────────────────────────────────────────────────────────────────────────
# Ingrédients dont les calories NE suivent PAS la formule p×4 + c×4 + f×9
#
# Raisons principales d'écart avec Atwater standard :
#   A) Fibres alimentaires : rendement ~2 kcal/g au lieu de 4
#      → surtout épices/herbes séchées (fibres 15–45 % du poids)
#   B) Polyphénols / tanins non digestibles : cacao, caroube, thé
#   C) Éthanol (alcools) : 7 kcal/g
#   D) Acide acétique (vinaigres) : ~3.5 kcal/g
#   E) Polyols : 2.4 kcal/g
#   F) Composition atypique : algues (pigments), aquafaba (eau à 94 %)
#   G) USDA/CIQUAL utilisent des facteurs de conversion spécifiques
#      validés expérimentalement → leurs valeurs font référence
# ──────────────────────────────────────────────────────────────────────────
FORMULA_EXCEPTIONS = {
    # ── Vinaigres — acide acétique (~3.5 kcal/g) ──────────────────────────
    "vinegar", "apple_cider_vinegar", "white_wine_vinegar", "red_wine_vinegar",
    "rice_vinegar", "rice_wine_vinegar", "balsamic_vinegar", "sherry_vinegar",
    "malt_vinegar", "champagne_vinegar", "wine_vinegar",

    # ── Alcools — éthanol (7 kcal/g) ──────────────────────────────────────
    "beer", "wine", "red_wine", "white_wine", "rum", "whiskey", "vodka",
    "sake", "mirin", "brandy", "champagne", "vermouth", "gin", "tequila",
    "vanilla", "vanilla_extract",

    # ── Jus acides (fibres + acides organiques) ───────────────────────────
    "lemon_juice", "lime_juice",

    # ── Polyols — 2.4 kcal/g (pas 4) ─────────────────────────────────────
    "xylitol", "erythritol", "sorbitol", "maltitol", "mannitol", "isomalt",

    # ── Fibres pures — rendement ~2 kcal/g ───────────────────────────────
    "psyllium", "psyllium_husk", "inulin",

    # ── Caroube — 40 g fibres/100 g → Atwater surestime de ~40 % ─────────
    # Les tanins (polyphénols) de la caroube réduisent aussi la digestibilité.
    # Valeur USDA (222 kcal) validée expérimentalement.
    "carob", "carob_powder", "farine_de_caroube", "poudre_de_caroube",

    # ── Cacao / chocolat — tanins non digestibles ─────────────────────────
    "cacao_powder", "cocoa_powder", "cacao", "cacao_nibs",
    "dark_chocolate",  # rapport fibres + polyphénols élevé

    # ── Matcha / thé — polyphénols, caféine ───────────────────────────────
    "matcha", "matcha_tea", "green_tea",

    # ── Graines de chia — gel hydrophile + oméga-3 ───────────────────────
    "chia_seed", "chia", "chia_seeds",

    # ── Algues / superfoods — composition atypique ────────────────────────
    "chlorella", "spirulina",
    "nori", "wakame_dried", "dried_seaweed", "dashi_kombu",

    # ── Herbes / épices SÉCHÉES — fibres 15–45 % → Atwater surestime ─────
    # Les fibres concentrées des épices séchées ont un rendement ~2 kcal/g,
    # d'où l'écart systématique >15 % par rapport à la formule standard.
    # Les valeurs CIQUAL/USDA intègrent des facteurs spécifiques et font référence.
    "pepper", "black_pepper", "white_pepper",
    "cinnamon",
    "cumin", "ground_cumin",
    "coriander", "ground_coriander", "fresh_coriander",
    "paprika", "smoked_paprika",
    "turmeric", "turmeric_fresh",
    "cloves",
    "cardamom",
    "caraway",
    "star_anise",
    "bay_leaf",
    "oregano",
    "thyme",
    "rosemary",
    "sage",
    "marjoram",
    "fenugreek",
    "ras_el_hanout",
    "curry", "curry_leaves",
    "garam_masala",
    "korean_chili",
    "za_atar", "sumac",
    "saffron",
    "nutmeg_whole",
    "mustard_seeds",
    "poppy_seeds",
    "caraway",
    "yeast", "nutritional_yeast",   # levures : parois cellulaires (glucanes)

    # ── Légumes à haute teneur en fibres / eau ────────────────────────────
    # Légumes feuilles : rapport fibres/glucides élevé → Atwater surestime
    "spinach", "kale", "watercress", "swiss_chard", "pak_choi",
    "bean_sprouts", "bamboo_shoots",
    "chrysanthemum_greens", "shiso", "thai_basil",
    "broccoli", "brussels_sprouts",
    "spring_onion", "chives",
    "bitter_gourd", "okra",
    "endive", "savoy_cabbage",
    "kohlrabi",

    # ── Fruits acides / exotiques ─────────────────────────────────────────
    "lemon", "lime", "yuzu",
    "moringa",  # feuilles de moringa : fibres ~19%

    # ── Fruits à fibres élevées (glucides CIQUAL disponibles ≠ total carbs) ──
    # énergie déclarée = correcte (base USDA/étiquette total carbs)
    # macros stockées = glucides disponibles → Atwater sous-estime
    "raspberry",    # fibres ~6.5g, carbs dispo ~5.4g vs total ~11.9g
    "artichoke",    # fibres ~8.6g, carbs dispo ~3.5g vs total ~10g
    "date",         # datte séchée : kcal USDA 277, carbs dispo CIQUAL ~29g vs total ~70g
    "fig",          # figue séchée : fibres ~9g, glucides dispo < total
    "kiwi",         # fibres ~3g, glucides dispo CIQUAL < total USDA

    # ── Légumes — mixage source kcal/macros (auto_correct_v6) ─────────────────
    # kcal d'une source, macros de l'autre → Atwater apparent hors cible
    # Les valeurs individuelles (kcal ET macros) sont toutes deux correctes
    # selon leur source respective ; l'écart est un artefact de fusion.
    "eggplant", "fennel", "parsnip", "parsley", "lettuce",
    "carrot", "chickpea", "quinoa", "lupine",

    # ── Condiments / préparations — même cause mixage source ─────────────────
    "wasabi", "caper", "harissa", "tortillas",

    # ── Légumes à matrice atypique (acides organiques, fructans, schéma mixte) ─
    # capers     : vinaigre + fibres → acide acétique non couvert par Atwater
    # sauerkraut : fermenté (acide lactique) + fibres concentrées → même logique que kimchi
    # green_bean : légume à fibres élevées, glucides CIQUAL dispo vs kcal source autre
    # garlic     : fructans (~17g/100g), acides organiques → Atwater surestime
    # hominy     : maïs nixtamalisé, amidon résistant → facteur < 4 kcal/g
    "capers", "sauerkraut", "green_bean", "garlic", "hominy",

    # ── Fruits — polyols naturels (sorbitol) + acides organiques ──────────────
    # cherry/mango/green_mango/watermelon : facteurs Atwater spécifiques fruits
    # Écarts structurels confirmés USDA/CIQUAL : 17–45%
    "cherry", "mango", "green_mango", "watermelon",

    # ── Noix — facteurs Atwater spécifiques USDA (protéines 5.18 kcal/g) ──────
    # cashew : p×5.18, c×3.87, f×9 (USDA NDB) vs formule générique p×4, c×4, f×9
    # almond : même logique + schema available → fib×2 surestime encore
    "cashew", "almond",

    # ── Légumes très peu caloriques — delta absolu négligeable ────────────────
    # zucchini : ~4 kcal/100g de différence absolue malgré 24% relatif
    "zucchini",

    # ── Herbes non encore couvertes ci-dessus ────────────────────────────────
    "tarragon", "dill",

    # ── Protéines concentrées / aliments atypiques ────────────────────────────
    "seitan",       # gluten de blé pur : facteur Atwater standard inadapté (fibres nulles, protéine ~75%)
    "maca",         # poudre de maca : fibres concentrées + acides organiques → Atwater surestime
    "jalapeno",     # piment frais : fibres + acides organiques → léger écart Atwater

    # ── Aquafaba — 94 % eau, protéines traces ─────────────────────────────
    "aquafaba",

    # ── Champignons (parois chitineuses non digestibles) ──────────────────
    "shiitake_mushroom",
    "kimchi",   # fermenté : acide lactique, fibres végétales concentrées

    # ── Légumineuses cuites (amidon résistant) ────────────────────────────
    "red_kidney_bean",   # teneurs en amidon résistant → rendement < 4 kcal/g

    # ── Divers produits à forte teneur en fibres ──────────────────────────
    "bran",          # son : fibres 40–45 % → même logique que psyllium
    "flax_egg",      # graines de lin : mucilage hydrophile
    "baobab",        # pulpe de baobab : fibres 44 %
    "nori",          # déjà dans algues, doublon inoffensif
    "red_lentil",    # amidon résistant post-cuisson
    "gundruk",       # légumes fermentés : acides organiques
    "dried_tomato",  # tomates séchées : fibres concentrées (~12 %)
    "peeled_tomato", # tomates en conserve : légère perte glucidique
    "lemon_verbena", # herbe aromatique : fibres et eau
    "aquafaba",
    "amarillo_chili", "green_bell_pepper",
    "butternut_squash",
    "laitue",        # acides organiques (malique, citrique) ≈ 2 kcal non capturés par Atwater
    "mint",          # menthe : 8g fibres/100g → Atwater corrigé donne delta 4.3% (OK)

    # ── Audit 2026-04-28 — 8 warnings résiduels structurels (CIQUAL dispo / ─────
    # biologie) confirmés non-actionnables ────────────────────────────────────────
    #
    # Groupe A — schéma glucides DISPONIBLES CIQUAL :
    #   cal déclarée = Atwater sur carbs_g dispo (fibres exclues)
    #   estimated   = Atwater sur glucides totaux → surestime systématiquement
    #   Delta 17–37% structurel, données correctes par convention CIQUAL.
    #
    "chicory",     # Δ36.6% — chicorée : fibres ~4g, glucides dispo ~3.5g vs total ~7.5g
    "citrus",      # Δ35.4% — agrumes : acides organiques + glucides dispo vs total
    "mushroom",    # Δ25.7% — champignons : parois chitineuses + glucides dispo CIQUAL
    "cabbage",     # Δ24.5% — chou : fibres ~2.3g, glucides dispo CIQUAL
    "corn",        # Δ19.1% — maïs : amidon + fibres → glucides dispo < total USDA
    "tomato",      # Δ17.5% — tomate : acides organiques (citrique, malique) non capturés
    #
    # Groupe B — exceptions biologiques (cal > macro_cal) :
    #   cal déclarée intègre des composés non couverts par Atwater standard
    #
    "onion",       # Δ22.2% inverse — fructanes ~5g/100g (non comptés dans carbs)
                   # + acides organiques → cal réelle > Atwater standard
    "dandelion",   # Δ16.9% inverse — pissenlit : acides organiques, inuline (~12g/100g)
                   # cal déclarée CIQUAL correcte, Atwater sous-estime

    # ── Herbes fraîches / séchées — fibres concentrées ────────────────────
    # basil séché : 33g fibres + tanins → cal déclarée CIQUAL 23 kcal correcte
    # Atwater estime 29 kcal (Δ20.6%) — même logique que carob/cacao.
    # rapport_incoherences_v2 §9 + §P2-3
    "basil",       # Δ20.6% — fibres concentrées, tanins, valeur CIQUAL fait référence
    # ── Cacao poudre — même logique que carob (rapport_incoherences_v2 §2) ──
    # chocolate/powder : cal=229 kcal (USDA FDC #19165 cacao non sucré), Atwater=433 (Δ89%)
    # 33g fibres + tanins polyphénoliques réduisent fortement la digestibilité.
    # carob était déjà exempté pour la même raison ; chocolate/powder était oublié.
    "chocolate",   # Δ89% — cacao poudre : fibres+tanins, valeur USDA FDC #19165 fait référence
}

NON_SCORING = {"water", "salt", "stevia", "corn_husk", "gelatin_sheet"}

# Ingrédients utilisant les glucides DISPONIBLES (schéma CIQUAL : carbs = total − fibres).
# Pour ces aliments, fiber > carbs est physiologiquement normal et ne doit pas
# déclencher une alarme fiber_gt_carbs.
FIBER_GT_CARBS_EXCEPTIONS = {
    # ── Légumes à fibres concentrées ──────────────────────────────────────────
    "artichoke", "brussels_sprouts", "leek", "fennel", "green_cabbage",
    "swiss_chard", "cabbage",
    # ── Épices / herbes séchées (fibres > glucides dispo très fréquent) ───────
    "caraway", "cinnamon", "coriander", "curry", "marjoram", "mint",
    "oregano", "paprika", "rosemary", "sage", "tarragon", "thyme",
    "bay_leaf", "cloves", "cumin", "ground_cumin", "ground_coriander",
    "smoked_paprika", "turmeric", "star_anise", "fenugreek", "cardamom",
    "nutmeg_whole", "za_atar", "sumac", "ras_el_hanout", "garam_masala",
    # ── Légumineuses — haricots secs/cuits : fibres > glucides dispo CIQUAL ────
    # Les haricots secs ont ~16g fibres/100g pour ~11g glucides disponibles CIQUAL
    # (glucides totaux ~60g mais schéma CIQUAL = total − fibres → dispo ~11-15g).
    # gigante_bean : même famille, données CIQUAL identiques.
    "bean", "gigante_bean",
    # ── Noix de coco : deux produits très différents, même clé racine ───────────
    # coconut râpé/chair : fibres ~9g, glucides dispo CIQUAL ~6g → fiber > carbs normal.
    # coconut_aminos : condiment dérivé de la sève — carbs_schema hérité de coconut
    # via fusion multi-source → schéma CIQUAL "available" appliqué ici aussi.
    "coconut", "coconut_aminos",
    # ── Noix / graines riches en fibres ──────────────────────────────────────
    "hazelnut", "flax_egg", "flaxseed", "coconut_flesh", "bran",
    "wheat_germ", "psyllium", "psyllium_husk",
    # ── Thés en poudre (matière sèche concentrée) ─────────────────────────────
    # matcha_tea en poudre : fiber ~37g/100g, carbs ~37.9g/100g → ratio fiber≈carbs
    # normal pour une poudre de feuilles séchées très concentrée (pas une infusion).
    "matcha_tea",
    # ── Herbes et épices fraîches (rapport_incoherences_v2 §9) ────────────────
    # basil séché : fiber~33g, carbs dispo~10g (CIQUAL) — fibres concentrées,
    # ratio normal. patch_v8 a recalibré les macros sans ajouter cette exception.
    "basil",
    # ── Graines (rapport_incoherences_v2 §6) ─────────────────────────────────
    # seeds/* (sesame, chia, black_sesame) : glucides disponibles CIQUAL < fibres.
    # Correct physiquement — carbs_schema=available déjà taggué dans patch_v8.
    "seeds",
    # ── Algues (rapport_incoherences_v2 §7) ──────────────────────────────────
    # seaweed/default et seaweed/irish_moss : fiber~30-37g > carbs~11-15g.
    # nori/wakame/kombu déjà exemptés path-level ; cette entrée couvre tous les variants.
    "seaweed",
    # ── Champignons — variant morel (rapport_incoherences_v2 §8) ─────────────
    # mushroom/morel : carbs=0.1g (glucides dispo très faibles), fiber=2.8g
    # Schéma available, faux positif validator — valeur biologiquement correcte.
    "mushroom",
}

# Ingrédients dont certains macros sont physiologiquement nuls/traces.
# Pour ces aliments, un champ manquant = 0 implicite ; pas besoin de l'alerter.
# Exemples : sucres purs (fat≈0, protein≈0), alcools (carbs≈0), eaux aromatisées.
PARTIAL_DATA_OK = {
    # ── Sucres / sirops / édulcorants ─────────────────────────────────────────
    "icing_sugar",      # pure sucrose, fat≈0, protein≈0
    "maple_syrup",      # ~67g sucres, fat<0.1g, protein≈0
    "molasses",         # ~55g sucres, protein traces
    "honey",            # ~82g sucres, fat≈0.17g (trace)
    "xylitol",          # polyol pur, protein≈0, fat≈0
    "date_syrup",       # sirop de dattes, fat≈0, protein traces
    # ── Alcools ───────────────────────────────────────────────────────────────
    "rum",              # éthanol pur, protein≈0, carbs≈0.1g, fat≈0
    "mirin",            # alcool+sucre, fat<0.1g
    # ── Condiments / aromatisants ─────────────────────────────────────────────
    "coconut_aminos",   # substitut soja, protein<1g, fat≈0
    "worcestershire_vegan",  # condiment, fat≈0
    "liquid_smoke",     # fumée liquide, protein≈0, fat≈0
    "tapioca_starch",   # amidon pur, fat≈0
    # ── Boissons / infusions ──────────────────────────────────────────────────
    "green_tea",        # infusion, protein<0.5g, fat<0.1g
    "kombucha",         # fermenté, protein≈0.3g, fat≈0
    # ── Agents levants ────────────────────────────────────────────────────────
    "baking_powder",    # sodium+acide, fat≈0, protein≈0
    "baking_soda",      # bicarbonate pur, fat≈0, carbs≈0
    # ── Herbes / zestes ───────────────────────────────────────────────────────
    "kaffir_lime_leaf", # utilisé en trace, données calories absentes
}

# Ingrédients pour lesquels saturated_fat > fat est un artefact de fusion
# multi-source (fat_g sous-estimé post-fusion CIQUAL/USDA) et non une erreur réelle.
# Ces valeurs sont cohérentes avec les sources primaires — la correction doit
# se faire dans auto_correct_v6.py via MANUAL_OVERRIDES, pas ici.
SAT_GT_FAT_EXCEPTIONS = {
    # turmeric_fresh : fat_g issu d'une source, saturated_fat_g d'une autre.
    # USDA #170926 (fresh turmeric root) : fat=0.97g, sat=0.338g → ratio cohérent.
    # Après fusion CIQUAL (fat=0.6g) + USDA sat=0.338g → sat > fat apparent.
    # Correction cible : fat_g ← 0.97 (USDA, mesurée) via KNOWN_LIPID_PROFILES.
    "turmeric_fresh",
    # kashk : produit laitier fermenté iranien (petit-lait séché/concentré).
    # Données sources partielles : mufa=0, pufa=0 non renseignés.
    # sat=fat=16g → sat_gt_fat apparent car total lipidique = sat seul déclaré.
    # Valeur correcte physiquement : laitier gras, gras saturé dominant, mais
    # mufa/pufa réels existent (non documentés). Exception justifiée.
    "kashk",
}

SUGAR_GT_CARBS_EXCEPTIONS = {
    # apple : carbs_g = glucides disponibles CIQUAL (sans fibres), sugar_g USDA
    # légèrement supérieur selon variété (Granny Smith vs Fuji). Écart < 1g, bénin.
    "apple",
    # bitter_gourd : alias → gourd. Données CIQUAL partielles, sucres et glucides
    # mesurés sur variétés différentes. Écart trace, pas d'impact nutritionnel.
    "bitter_gourd",
    # cherry : glucides disponibles CIQUAL (schema available) vs sucres USDA
    # mesurés sur cerises plus sucrées. Écart < 1g.
    "cherry",
    # ponzu : alias → lemon. Sauce condiment, teneur sucre/carbs trace (<2g).
    # Écart dû à la fusion alias : données lemon appliquées à un condiment acide.
    "ponzu",
    # tamari : alias → soy_sauce. Glucides très faibles (~1g), sucres mesurés
    # sur formulations différentes (tamari wheat-free vs soy sauce standard).
    "tamari",
    # dried_raisins : carbs_g=73.2g (CIQUAL 13046), sugar_g=62.5g (CIQUAL 13046).
    # Le patch patch_nutrition_v8.py fixe sugar_g=62.5 à chaque run mais la validation
    # croisée CNF injecte temporairement une valeur > carbs_g avant le patch.
    # CIQUAL 13046 confirme : sucres=62.5g < carbs=73.2g → exception légitime.
    "dried_raisins",
}

# Ingrédients génériques / catégories (types ombrelle résolus au rendu recette).
# Ils n'ont pas de données nutritionnelles directes → exclure du check missing_field.
CATEGORY_INGREDIENTS = {
    "flour", "bread", "rice", "pasta", "pastry",
    "milk_animal", "milk_plant", "cream_animal", "cream_plant",
    "yogurt_animal", "yogurt_plant", "butter", "oil",
    "sugar", "chocolate", "nut", "seeds",
    "tomato", "onion", "bell_pepper", "squash", "cabbage",
    "mushroom", "seaweed", "lentil", "bean",
    "broth", "sauce", "curry_paste",
    "citrus", "miso", "tofu",
    "vinegar",   # déjà dans FORMULA_EXCEPTIONS, redondance inoffensive
    # ── Types ombrelle avec variants nommés (pas de variant "default") ────────
    "sesame",         # variants: tahini_raw, black_sesame, white_sesame — pas de default
    "tropical_fruit", # variants: cherimoya, jackfruit, etc. — ombrelle géographique
}

# ── Règles biologiques ────────────────────────────────────────────────────────
# Ingrédients lait animal : fiber et starch sont physiologiquement nuls.
ANIMAL_MILK_KEYS = {"milk_animal", "cream_animal"}

# Catégories strictement végétales : cholestérol = 0 sans exception.
PLANT_CATEGORIES = {
    "vegetable", "fruit", "grain", "legume", "herb_spice",
    "dairy_alternative", "superfood", "protein_plant", "leavening",
}

# Noix/graines/huiles brutes : sodium naturel < 50 mg/100g.
# Au-delà c'est une erreur de source ou un produit salé mal catégorisé.
FAT_CATEGORY_SODIUM_THRESHOLD = 50   # mg/100g
FAT_SODIUM_EXCEPTIONS = {
    "peanut",    # cacahuètes parfois salées
    "tahini",    # pâte de sésame souvent salée
    "pesto",     # préparation avec sel
    "butter",    # beurre salé possible
}

SCHEMA_V6 = "6.0"

FIELDS = [
    "calories", "protein", "carbs", "fat", "fiber", "sugar",
    "saturated_fat", "omega3", "omega3_ala",
    "vitamin_c", "vitamin_a", "vitamin_d", "vitamin_b12",
    "calcium", "iron", "sodium", "potassium", "magnesium",
    "zinc", "selenium",
    "iodine",        # CIQUAL-exclusif
    "choline",       # USDA + CNF
    "folate",
    "trans_fat",     # USDA-exclusif
]

# Mapping short_key → (section, field) dans nutrients_v6 imbriqué
_V6_NESTED_PATHS: dict[str, tuple[str, str]] = {
    "calories":      ("energy",        "kcal"),
    "protein":       ("macros",        "protein_g"),
    "carbs":         ("macros",        "carbs_g"),
    "fat":           ("macros",        "fat_g"),
    "fiber":         ("macros",        "fiber_g"),
    "alcohol":       ("macros",        "alcohol_g"),
    "sugar":         ("carbohydrates", "sugars_g"),
    "starch":        ("carbohydrates", "starch_g"),
    "polyols":       ("carbohydrates", "polyols_g"),
    "saturated_fat": ("lipids",        "saturated_g"),
    "mufa":          ("lipids",        "monounsaturated_g"),
    "pufa":          ("lipids",        "polyunsaturated_g"),
    "trans_fat":     ("lipids",        "trans_g"),
    "omega3":        ("lipids",        "omega3_g"),
    "omega6":        ("lipids",        "omega6_g"),
    "omega3_ala":    ("lipids",        "fa_18_3_ala_g"),
    "omega3_epa":    ("lipids",        "fa_20_5_epa_g"),
    "omega3_dha":    ("lipids",        "fa_22_6_dha_g"),
    "cholesterol":   ("lipids",        "cholesterol_mg"),
    "vitamin_a":     ("vitamins",      "a_rae_mcg"),
    "beta_carotene": ("vitamins",      "beta_carotene_mcg"),
    "vitamin_d":     ("vitamins",      "d_mcg"),
    "vitamin_e":     ("vitamins",      "e_mg"),
    "vitamin_k1":    ("vitamins",      "k1_mcg"),
    "vitamin_k2":    ("vitamins",      "k2_mcg"),
    "vitamin_c":     ("vitamins",      "c_mg"),
    "vitamin_b1":    ("vitamins",      "b1_mg"),
    "vitamin_b2":    ("vitamins",      "b2_mg"),
    "vitamin_b3":    ("vitamins",      "b3_mg"),
    "vitamin_b5":    ("vitamins",      "b5_mg"),
    "vitamin_b6":    ("vitamins",      "b6_mg"),
    "folate":        ("vitamins",      "b9_mcg"),
    "vitamin_b12":   ("vitamins",      "b12_mcg"),
    "choline":       ("vitamins",      "choline_mg"),
    "calcium":       ("minerals",      "calcium_mg"),
    "phosphorus":    ("minerals",      "phosphorus_mg"),
    "potassium":     ("minerals",      "potassium_mg"),
    "sodium":        ("minerals",      "sodium_mg"),
    "magnesium":     ("minerals",      "magnesium_mg"),
    "iron":          ("minerals",      "iron_mg"),
    "zinc":          ("minerals",      "zinc_mg"),
    "copper":        ("minerals",      "copper_mg"),
    "manganese":     ("minerals",      "manganese_mg"),
    "selenium":      ("minerals",      "selenium_mcg"),
    "iodine":        ("minerals",      "iodine_mcg"),
    "lycopene":      ("bioactives",    "lycopene_mcg"),
    "organic_acids": ("bioactives",    "organic_acids_g"),
}

# Champs comparables uniquement contre une source précise
SOURCE_EXCLUSIVE_COMPARE: dict[str, str] = {
    "iodine":        "CIQUAL",
    "polyols":       "CIQUAL",
    "organic_acids": "CIQUAL",
    "vitamin_k2":    "CIQUAL",
    "trans_fat":     "USDA",
}

# IDs nutriments USDA FoodData Central
USDA_NUTRIENT_IDS = {
    1008: "calories",
    1003: "protein",
    1005: "carbs",
    1004: "fat",
    1079: "fiber",
    2000: "sugar",
    1087: "calcium",
    1089: "iron",
    1092: "potassium",
    1090: "magnesium",
    1093: "sodium",
    # V10 — ajoutés
    1095: "zinc",
    1103: "selenium",
    1162: "vitamin_c",
    1178: "vitamin_b12",
    # V11 — ajoutés (alignement nutrition_v2 + cnf_full_v10)
    1106: "vitamin_a",   # Retinol Activity Equivalents (RAE)
    1114: "vitamin_d",   # Vitamin D (D2 + D3)
}
# ──────────────────────────────────────────────────────────────────────────
# Limites absolues par champ (min, max) — valeurs physiquement impossibles.
# Déclenchent value_out_of_range (warning) ou impossible_value (critical).
#
# Unités :
#   macros       : g/100g     → max 100 (sauf cas extrêmes comme huile pure)
#   fiber        : g/100g     → max 90  (psyllium husk ~85%)
#   sodium       : mg/100g    → sel de table ~38 000 mg, légitimement élevé
#   calcium      : mg/100g    → épices séchées peuvent dépasser 1000 mg
#   iron         : mg/100g    → épices ~80 mg max
#   saturated_fat: g/100g     → ne peut pas dépasser fat
# ──────────────────────────────────────────────────────────────────────────
ABS_LIMITS: dict[str, tuple[float, float]] = {
    "calories":      (0,    900),   # huile ≈ 884 kcal
    "protein":       (0,    100),   # protéine isolée = 100%
    "carbs":         (0,    100),
    "fat":           (0,    100),
    "fiber":         (0,     90),   # psyllium husk ~85%
    "sugar":         (0,    100),
    "sodium":        (0,  40000),   # sel table iodé ~38 700 mg
    "calcium":       (0,   8000),   # baking_powder (CaCO3) ~7 728 mg
    "iron":          (0,    150),   # thym séché ~124 mg, chlorella ~130 mg
    "potassium":     (0,   4000),
    "magnesium":     (0,   1000),
    "saturated_fat": (0,    100),
    # v6 — nouveaux champs
    "iodine":        (0,   5000),   # µg — sel iodé ~3000 µg/100g
    "choline":       (0,   2000),   # mg
    "folate":        (0,   3000),   # µg
    "vitamin_k2":    (0,   1000),   # µg
    "trans_fat":     (0,     10),   # g — industriel max ~8g
    "omega3":        (0,     60),   # g — huile de lin ~53g
    "omega3_ala":    (0,     60),   # g
}


# ══════════════════════════════════════════════════════════════════════════
# 2. UTILS
# ══════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:
    """
    Normalise un texte pour la comparaison :
    minuscule, sans accents, sans ponctuation, _ pour espaces.

    Les virgules sont supprimées car CIQUAL 2025 utilise "Ail, cru"
    tandis que les notes de physical.json ont "Ail cru" — les deux
    doivent produire la même clé normalisée.
    """
    if not text:
        return ""
    text = str(text).lower().strip()
    text = "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )
    # Supprimer la ponctuation parasite avant de remplacer les séparateurs
    text = re.sub(r"[,;.()]", "", text)
    text = re.sub(r"[\s\-]+", "_", text)
    return text.strip("_")


def normalize_col(col: str) -> str:
    """Normalise un nom de colonne (supprime sauts de ligne et espaces multiples)."""
    return re.sub(r"\s+", " ", str(col).replace("\n", " ")).strip()


def safe_float(v) -> Optional[float]:
    """Convertit en float, retourne None pour les valeurs invalides ou NaN."""
    if v is None:
        return None
    try:
        s = str(v).replace(",", ".").strip()
        # CIQUAL utilise "-" pour les valeurs traces et "<X" pour les limites
        if s in ("-", "", "nd", "traces", "<0.5") or s.startswith("<"):
            return None
        r = float(s)
        return None if r != r else r   # NaN check
    except (TypeError, ValueError):
        return None


def pct_delta(declared: float, reference: float) -> Optional[float]:
    if None in (declared, reference) or reference == 0:
        return None
    return round(abs(declared - reference) / reference * 100, 1)


def classify(delta: Optional[float]) -> str:
    if delta is None:
        return "unknown"
    if delta >= DELTA_CRITICAL:
        return "critical"
    if delta >= DELTA_WARN:
        return "warning"
    return "ok"


def _find_col(cols_normalized: dict, candidates: list) -> Optional[str]:
    """
    Cherche la première colonne dont le nom normalisé contient un des candidats.
    cols_normalized = {col_originale: col_normalisée}
    """
    for orig, norm in cols_normalized.items():
        for cand in candidates:
            if cand.lower() in norm.lower():
                return orig
    return None


# ══════════════════════════════════════════════════════════════════════════
# 3. CHARGEMENT BASE LOCALE
# ══════════════════════════════════════════════════════════════════════════

def load_local_db(db_file=None):
    """
    Charge la base nutrition et extrait le ciqual_id_map depuis ingredient_physical.json.

    V12 : db_file optionnel — si None, utilise resolve_db_file() qui préfère
    nutrition_corrected.json à nutrition_v2.json quand disponible.
    """
    active_file = db_file or resolve_db_file()
    print(f"Chargement de la base locale...")
    print(f"  Source : {active_file.name}")

    if not active_file.exists():
        raise FileNotFoundError(f"❌ Fichier nutrition introuvable :\n  {active_file}")

    with open(active_file, encoding="utf-8") as f:
        db = json.load(f)

    ingredients = db.get("ingredients", {})

    # ── Extraction depuis ingredient_physical.json ─────────────────────
    # Structure : {nom_ingredient: {"ciqual_id": "XXXXX", "note": "Nom CIQUAL FR", ...}}
    #
    # ⚠ Version : les ciqual_id dans physical.json sont des codes CIQUAL 2024.
    #   CIQUAL 2025 a recodé la majorité (ex: oignon 10075 → 20034).
    #   → Le champ "note" (nom français CIQUAL) est utilisé en priorité pour
    #     le fuzzy matching ; le lookup par ID reste en complément.
    ciqual_id_map   = {}   # ingredient_id → code CIQUAL (fiabilité partielle avec 2025)
    ciqual_note_map = {}   # ingredient_id → nom_fr CIQUAL exact (pour fuzzy)

    if PHYSICAL_FILE.exists():
        try:
            with open(PHYSICAL_FILE, encoding="utf-8") as f:
                physical = json.load(f)

            for ing_name, ing_data in physical.items():
                if ing_name == "_meta":
                    continue
                if not isinstance(ing_data, dict):
                    continue
                cid = ing_data.get("ciqual_id")
                if cid:
                    ciqual_id_map[ing_name] = str(cid)
                note = ing_data.get("note", "")
                if note and len(note) > 2:
                    ciqual_note_map[ing_name] = str(note).strip()

        except Exception as e:
            print(f"  ⚠ Impossible de charger ingredient_physical.json : {e}")

    # ── V13 : overrides manuels — priorité sur physical.json ─────────────────
    for _ing, _cid in CIQUAL_ID_OVERRIDES.items():
        ciqual_id_map[_ing] = _cid

    print(f"  ✔ {len(ingredients)} ingrédients, "
          f"{len(ciqual_id_map)} avec ciqual_id, "
          f"{len(ciqual_note_map)} avec note CIQUAL")
    return ingredients, ciqual_id_map, ciqual_note_map


# ══════════════════════════════════════════════════════════════════════════
# 4. SOURCE CIQUAL 2025
# ══════════════════════════════════════════════════════════════════════════

class CIQUALLoader:
    """
    Charge Table_Ciqual_2025_FR_2025_11_03.xlsx (ANSES).
    Compatible avec les versions 2020 / 2021 / 2024 / 2025.

    Correctif V9 : les colonnes CIQUAL 2025 contiennent des sauts de ligne.
    → normalisation systématique avant matching des candidats.

    Nouvelles données extraites : alim_nom_sci (nom scientifique latin).
    """

    # Candidats pour chaque colonne — substrings cherchés dans le nom normalisé
    # (normalize_col remplace \n → espace, strip espaces multiples)
    COL_CODE     = ["alim_code", "code aliment"]
    COL_NAME_FR  = ["alim_nom_fr", "nom de l'aliment", "nom fr"]
    COL_NAME_SCI = ["alim_nom_sci", "nom sci"]
    # kcal : géré par _find_kcal_col (priorité Règlement UE)
    COL_KCAL     = ["kcal"]   # fallback uniquement
    # protéines : géré par _find_prot_col (priorité Jones)
    COL_PROTEIN  = ["jones (g", "facteur de jones", "protéines, n x 6.25", "protéines (g", "protein"]
    COL_CARBS    = ["glucides"]
    COL_FAT      = ["lipides"]
    COL_FIBER    = ["fibres alimentaires"]
    COL_SUGAR    = ["sucres (g"]
    COL_WATER    = ["eau (g"]

    def __init__(self):
        self.by_id:    dict = {}   # cid → {calories, protein, ...}
        self.by_name:  dict = {}   # nom_normalisé → cid
        self.sci_names: dict = {}  # cid → alim_nom_sci
        self.available = False

    def load(self):
        """Charge ciqual_flat_v3.json (pré-normalisé — plus besoin de xlsx)."""
        if CIQUAL_FILE.exists():
            self._parse(CIQUAL_FILE)
        else:
            print(f"  ⚠ CIQUAL non trouvé : {CIQUAL_FILE}")

    def _parse(self, path: Path):
        print(f"  → CIQUAL flat: {path.name}")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            for food in data.get("foods_flat", []):
                # Identifiant CIQUAL — la clé réelle dans ciqual_flat_v3.json est "ciqual_code"
                cid_raw = (food.get("ciqual_code")
                           or food.get("alim_code")   # compat anciens exports
                           or food.get("code"))
                if cid_raw is None:
                    continue
                cid = str(cid_raw).strip()

                entry = {
                    "calories":      safe_float(food.get("energy_kcal")),
                    "protein":       safe_float(food.get("protein_g")),
                    "carbs":         safe_float(food.get("carbs_g")),
                    "fat":           safe_float(food.get("fat_g")),
                    "fiber":         safe_float(food.get("fiber_g")),
                    "sugar":         safe_float(food.get("sugar_g")),
                    "water":         safe_float(food.get("water_g")),
                    # v6 — champs étendus
                    "saturated_fat": safe_float(food.get("fa_saturated_g")),
                    "omega3":        safe_float(
                        food.get("omega3_g") or (
                            (food.get("fa_18_3_ala_g") or 0)
                            + (food.get("fa_20_5_epa_g") or 0)
                            + (food.get("fa_22_6_dha_g") or 0)
                        ) or None
                    ),
                    "omega3_ala":    safe_float(food.get("fa_18_3_ala_g")),
                    "iodine":        safe_float(food.get("iodine_ug")),
                    "vitamin_k2":    safe_float(food.get("vitamin_k2_ug")),
                    "polyols":       safe_float(food.get("polyols_g")),
                    "organic_acids": safe_float(food.get("organic_acids_g")),
                    "vitamin_b12":   safe_float(food.get("vitamin_b12_ug")),
                    "folate":        safe_float(food.get("folate_ug")),
                    "calcium":       safe_float(food.get("calcium_mg")),
                    "iron":          safe_float(food.get("iron_mg")),
                    "sodium":        safe_float(food.get("sodium_mg")),
                    "potassium":     safe_float(food.get("potassium_mg")),
                    "magnesium":     safe_float(food.get("magnesium_mg")),
                    "zinc":          safe_float(food.get("zinc_mg")),
                    "selenium":      safe_float(food.get("selenium_ug")),
                    "vitamin_c":     safe_float(food.get("vitamin_c_mg")),
                    "vitamin_a":     safe_float(food.get("vitamin_a_rae_ug")),
                    "vitamin_d":     safe_float(food.get("vitamin_d_ug")),
                    # V13 traçabilité par champ
                    "_source_id":    cid,
                    "_source_name":  str(food.get("name_fr", "") or ""),
                }
                self.by_id[cid] = entry

                # Nom scientifique — clé "scientific_name" dans ciqual_flat_v3.json
                sci = food.get("scientific_name") or food.get("alim_nom_sci")
                if sci:
                    self.sci_names[cid] = str(sci).strip()

                # Index par nom normalisé
                # ciqual_flat_v3.json utilise "name_fr" comme clé canonique
                name_fr = food.get("name_fr") or food.get("description", "")
                if name_fr:
                    key = normalize(str(name_fr))
                    if key:
                        self.by_name[key] = cid

            print(f"  ✔ CIQUAL : {len(self.by_id)} aliments, {len(self.sci_names)} noms scientifiques")
            self.available = True

        except Exception as e:
            import traceback
            print(f"  ❌ Erreur CIQUAL : {e}")
            traceback.print_exc()

    def _find_kcal_col(self, cols_norm: dict) -> Optional[str]:
        """
        Priorité : colonne Règlement UE (officielle étiquetage)
        puis colonne Jones avec fibres.
        """
        # Priorité 1 : Règlement UE kcal
        for orig, norm in cols_norm.items():
            if ("reglement" in norm.lower() or "règlement" in norm.lower() or "1169" in norm) \
               and "kcal" in norm.lower():
                return orig
        # Priorité 2 : tout ce qui contient "kcal" (première occurrence)
        for orig, norm in cols_norm.items():
            if "kcal" in norm.lower():
                return orig
        return None

    def _find_prot_col(self, cols_norm: dict) -> Optional[str]:
        """
        Priorité : facteur de Jones (plus précis que N×6.25 pour les végétaux).
        """
        for orig, norm in cols_norm.items():
            if "jones" in norm.lower() and "prot" in norm.lower() and "energie" not in norm.lower():
                return orig
        # Fallback : tout ce qui contient "prot"
        for orig, norm in cols_norm.items():
            if "prot" in norm.lower() and "energie" not in norm.lower():
                return orig
        return None

    def lookup_by_id(self, cid: str) -> Optional[dict]:
        return self.by_id.get(str(cid))

    def lookup_by_name(self, name_fr: str) -> tuple[Optional[dict], str, float]:
        if not self.by_name:
            return None, "", 0.0
        key = normalize(name_fr)
        # Exact
        if key in self.by_name:
            cid = self.by_name[key]
            return self.by_id.get(cid), key, 1.0
        # Fuzzy WRatio avec pénalité longueur
        # Évite ex: "tomate_crue" → "laitue_romaine_crue" (partage "_crue")
        # BUG FIX v15 : pénalité si m_words >= q_words * 2 (≥ au lieu de >).
        # Avec >, un match 4-mots sur une requête 2-mots n'était PAS pénalisé
        # (4 > 4 = False) → "farine_de_soja_complete" passait pour tout ingrédient
        # en 2 mots dont le nom français normalisé a exactement 2 tokens.
        names = list(self.by_name.keys())
        match, score, _ = process.extractOne(key, names, scorer=fuzz.WRatio)
        if score >= FUZZY_THRESHOLD:
            q_words = len(key.split("_"))
            m_words = len(match.split("_"))
            if m_words >= q_words * 2:          # ← FIX: >= (était >)
                score = score * 0.8   # pénalité 20% si cible au moins le double
            if score >= FUZZY_THRESHOLD:
                cid = self.by_name[match]
                return self.by_id.get(cid), match, round(score / 100, 3)
        return None, "", 0.0

    def get_sci_name(self, cid: str) -> Optional[str]:
        return self.sci_names.get(str(cid))


# ══════════════════════════════════════════════════════════════════════════
# 5. SOURCE USDA FoodData Central
# ══════════════════════════════════════════════════════════════════════════

class USDALoader:
    """
    Charge USDA Foundation Foods JSON (prioritaire) ou CSV (fallback).

    Correctifs V9 :
    - Calcul kcal depuis nutrientConversionFactors quand nutrient 1008 absent
      (97/365 aliments seulement ont les kcal directement dans Foundation Foods)
    - Multi-scorer fuzzy : WRatio avec pénalité longueur pour éviter
      les matches aberrants sur termes courts (ex: "oil" → "anchovies in oil")
    - Expose scientificName depuis le JSON USDA

    Option A (offline JSON, recommandée) :
      → https://fdc.nal.usda.gov/download-foods.html
        "Foundation Foods" → JSON
      → placer dans sources/
    Option B (offline CSV) :
      → même page, télécharger le CSV
    Option C (API) :
      → export USDA_API_KEY='votre_cle'
      → https://fdc.nal.usda.gov/api-key-signup.html (gratuit, 3500 req/j)
    """

    def __init__(self):
        self.db:       dict = {}   # nom_normalisé → {calories, protein, ...}
        self.sci_map:  dict = {}   # nom_normalisé → scientificName
        self.available = False
        self.mode:     Optional[str] = None

    def load(self):
        # Cherche JSON dans le chemin configuré, puis dans sources/
        json_target = None
        if USDA_JSON.exists():
            json_target = USDA_JSON
        else:
            for f in SOURCES_DIR.glob("*.json"):
                if any(k in f.name.lower() for k in ["foundation", "fooddata", "usda"]):
                    json_target = f
                    break

        if json_target:
            self._load_json(json_target)
            return

        # Fallback CSV
        csv_target = None
        if USDA_CSV.exists():
            csv_target = USDA_CSV
        else:
            for f in SOURCES_DIR.glob("*.csv"):
                if any(k in f.name.lower() for k in ["foundation", "food"]):
                    csv_target = f
                    break

        if csv_target:
            self._load_csv(csv_target)
            return

        # API
        if USDA_API_KEY and REQUESTS_AVAILABLE:
            print("  → USDA : mode API (clé présente)")
            self.mode = "api"
            self.available = True
            return

        print("  ⚠ USDA non disponible.")
        print("    Option A : Foundation Foods JSON → https://fdc.nal.usda.gov/download-foods.html")
        print("    Option B : export USDA_API_KEY='votre_cle'")

    def _load_json(self, path: Path):
        """Charge usda_flat_v2.json (pré-normalisé)."""
        print(f"  → USDA flat JSON : {path.name}")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            foods = data.get("foods_flat", [])
            loaded = skipped_no_macros = 0

            for food in foods:
                desc = normalize(food.get("name_en", "") or food.get("description", ""))
                if not desc:
                    continue

                entry = {
                    "calories": safe_float(food.get("energy_kcal")),
                    "protein":       safe_float(food.get("protein_g")),
                    "carbs":         safe_float(food.get("carbs_g")),
                    "fat":           safe_float(food.get("fat_g")),
                    "fiber":         safe_float(food.get("fiber_g")),
                    "sugar":         safe_float(food.get("sugar_g")),
                    "calcium":       safe_float(food.get("calcium_mg")),
                    "iron":          safe_float(food.get("iron_mg")),
                    "potassium":     safe_float(food.get("potassium_mg")),
                    "magnesium":     safe_float(food.get("magnesium_mg")),
                    "sodium":        safe_float(food.get("sodium_mg")),
                    "zinc":          safe_float(food.get("zinc_mg")),
                    "selenium":      safe_float(food.get("selenium_ug")),
                    "vitamin_c":     safe_float(food.get("vitamin_c_mg")),
                    "vitamin_b12":   safe_float(food.get("vitamin_b12_ug")),
                    # v6 — champs étendus (top-level après fix usda_refactor_v2)
                    "saturated_fat": safe_float(food.get("fa_saturated_g")),
                    "omega3":        safe_float(food.get("omega3_g")),
                    "omega3_ala":    safe_float(food.get("fa_18_3_ala_g")),
                    "choline":       safe_float(food.get("choline_mg")),
                    "trans_fat":     safe_float(food.get("fa_trans_g")),
                    "iodine":        safe_float(food.get("iodine_ug")),
                    "folate":        safe_float(food.get("folate_ug")),
                    "vitamin_a":     safe_float(food.get("vitamin_a_rae_ug")),
                    "vitamin_d":     safe_float(food.get("vitamin_d_ug")),
                    "vitamin_k2":    safe_float(food.get("vitamin_k2_ug")),
                    # V13 traçabilité par champ
                    "_source_id":    str(food.get("source_id") or food.get("fdc_id") or ""),
                    "_source_name":  str(food.get("name_en") or food.get("description") or ""),
                }

                if entry["calories"] is None and entry["protein"] is None and entry["carbs"] is None:
                    skipped_no_macros += 1
                    continue

                self.db[desc] = entry
                loaded += 1
                # scientificName non présent dans le flat — ignoré

            print(f"  ✔ USDA flat JSON : {loaded} aliments ({skipped_no_macros} sans macro ignorés)")
            self.mode = "json"
            self.available = True

        except Exception as e:
            import traceback
            print(f"  ❌ USDA JSON : {e}")
            traceback.print_exc()


    @staticmethod
    def _get_calorie_factors(food: dict) -> Optional[tuple[float, float, float]]:
        """
        Extrait les facteurs de conversion p/c/f depuis nutrientConversionFactors.
        Retourne (protein_factor, carb_factor, fat_factor) ou None.
        """
        for cf in food.get("nutrientConversionFactors", []):
            if cf.get("type") == ".CalorieConversionFactor":
                return (
                    cf.get("proteinValue", 4.0),
                    cf.get("carbohydrateValue", 4.0),
                    cf.get("fatValue", 9.0),
                )
        return None

    def _load_csv(self, path: Path):
        print(f"  → USDA CSV : {path.name}")
        try:
            df = pd.read_csv(path, low_memory=False)
            for _, row in df.iterrows():
                desc = normalize(str(row.get("description", "")))
                if not desc:
                    continue
                self.db[desc] = {
                    "calories": safe_float(row.get("Energy")),
                    "protein":  safe_float(row.get("Protein")),
                    "carbs":    safe_float(row.get("Carbohydrate, by difference")),
                    "fat":      safe_float(row.get("Total lipid (fat)")),
                    "fiber":    safe_float(row.get("Fiber, total dietary")),
                    "sugar":    safe_float(row.get("Sugars, total including NLEA")),
                }
            self.mode = "csv"
            self.available = True
            print(f"  ✔ USDA CSV : {len(self.db)} aliments")
        except Exception as e:
            print(f"  ❌ USDA CSV : {e}")

    def lookup(self, name_en: str, name_fr: str = "") -> tuple[Optional[dict], str, float]:
        """
        Recherche multi-stratégie avec pénalité longueur.

        La pénalité longueur évite qu'un terme court comme "oil" matche
        "anchovy in olive oil" avec un score élevé.
        """
        name = name_en or name_fr
        if not self.available or not name:
            return None, "", 0.0
        if self.mode == "api":
            return self._api_query(name)

        key = normalize(name)

        # 1. Exact
        if key in self.db:
            return self.db[key], key, 1.0

        names = list(self.db.keys())
        if not names:
            return None, "", 0.0

        # 2. Fuzzy WRatio avec pénalité longueur
        match, score, _ = process.extractOne(key, names, scorer=fuzz.WRatio)
        if score >= FUZZY_THRESHOLD:
            # Pénalité si la cible est beaucoup plus longue que la requête
            # (évite "oil" → "anchovy in olive oil")
            q_words = len(key.split("_"))
            m_words = len(match.split("_"))
            if m_words > q_words * 3:
                score = score * 0.7   # pénalité 30%

            if score >= FUZZY_THRESHOLD:
                return self.db[match], match, round(score / 100, 3)

        # 3. WRatio global en dernier recours, seuil resserré à 85.
        #    partial_ratio retiré : trop permissif sur les termes courts
        #    ("oil" → "anchovy in olive oil" à 100, faux positif garanti).
        match2, score2, _ = process.extractOne(key, names, scorer=fuzz.WRatio)
        if score2 >= FUZZY_THRESHOLD + 10:   # seuil ≥ 85
            return self.db[match2], match2, round(score2 / 100, 3)

        return None, "", 0.0

    def _api_query(self, name: str, retries: int = 2) -> tuple[Optional[dict], str, float]:
        try:
            resp = requests.get(USDA_API_URL, params={
                "query": name, "api_key": USDA_API_KEY,
                "pageSize": 1, "dataType": "Foundation,SR Legacy"
            }, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            foods = data.get("foods", [])
            if not foods:
                return None, "", 0.0
            food = foods[0]
            result = {}
            for n in food.get("foodNutrients", []):
                nid = n.get("nutrientId") or n.get("nutrientNumber")
                try:
                    nid_int = int(nid) if nid is not None else None
                except (TypeError, ValueError):
                    nid_int = None
                if nid_int and nid_int in USDA_NUTRIENT_IDS:
                    result[USDA_NUTRIENT_IDS[nid_int]] = safe_float(n.get("value"))
            time.sleep(0.3)
            return result, food.get("description", name), 0.85
        except Exception:
            if retries > 0:
                time.sleep(1)
                return self._api_query(name, retries - 1)
            return None, "", 0.0




# ══════════════════════════════════════════════════════════════════════════
# 5b. SOURCE CNF (Canadian Nutrient File) v5
# ══════════════════════════════════════════════════════════════════════════

class CNFLoader:
    """
    Charge cnf_full_v10.json (pré-normalisé par build_cnf_full_v10.py).

    Usage : cohérence uniquement pour les plats composés / entrées mixtes.
    Les entrées avec meta.usage == "coherence_check_only" génèrent uniquement
    des avertissements de niveau "info" (non-bloquants).

    Structure attendue (cnf_full_v10) :
      {"_meta": {...}, "foods_flat": [{
        "name_en": "...", "name_fr": "...",
        "nutrients": {
          "energy":         {"kcal": ..., "kj": ...},
          "macros":         {"protein_g": ..., "fat_g": ..., "carbs_g": ..., "fiber_g": ...},
          "lipids":         {"saturated_g": ..., "omega3_g": ..., "fa_18_3_ala_g": ..., "cholesterol_mg": ...},
          "carbohydrates":  {"sugars_g": ...},
          "vitamins":       {"a_rae_mcg": ..., "c_mg": ..., "d_mcg": ..., "b12_mcg": ...,
                             "b9_mcg": ..., "choline_mg": ...},
          "minerals":       {"calcium_mg": ..., "iron_mg": ..., "potassium_mg": ...,
                             "magnesium_mg": ..., "sodium_mg": ..., "zinc_mg": ...,
                             "selenium_mcg": ...}
        }
      }]}

    Note : protein_g etc. sont aussi dupliqués à la racine, mais energy.kcal et
    vitamins.* ne sont accessibles que via le sous-dict.
    """

    # V13 — FIELD_MAP corrigé : clés réelles des sous-dicts nutrients.*
    # (les clés précédentes comme "energy_kcal", "fa_saturated_g", "vitamin_a_rae_ug"
    #  ne correspondent à aucun champ CNF réel → 0 valeur lue)
    FIELD_MAP = {
        # nutrients.energy
        "kcal":              "calories",
        # nutrients.macros
        "protein_g":         "protein",
        "fat_g":             "fat",
        "carbs_g":           "carbs",
        "fiber_g":           "fiber",
        # nutrients.carbohydrates
        "sugars_g":          "sugar",
        # nutrients.lipids
        "saturated_g":       "saturated_fat",
        "omega3_g":          "omega3",
        "fa_18_3_ala_g":     "omega3_ala",
        "cholesterol_mg":    "cholesterol",
        # nutrients.minerals (selenium_mcg = µg, même unité que selenium_ug)
        "calcium_mg":        "calcium",
        "iron_mg":           "iron",
        "potassium_mg":      "potassium",
        "magnesium_mg":      "magnesium",
        "sodium_mg":         "sodium",
        "zinc_mg":           "zinc",
        "selenium_mcg":      "selenium",
        # nutrients.vitamins
        "a_rae_mcg":         "vitamin_a",
        "c_mg":              "vitamin_c",
        "d_mcg":             "vitamin_d",
        "b12_mcg":           "vitamin_b12",
        "b9_mcg":            "folate",
        "choline_mg":        "choline",
    }

    # Chemin configurable — pointe sur cnf_full_v10.json dans raw/
    CNF_FILE = (BASE_DIR / "backend" / "data" / "nutrition" / "raw" / "cnf_full_v10.json")

    def __init__(self):
        self.db:        dict = {}   # nom_normalisé → entry nutritionnelle
        self.id_map:    dict = {}   # id_snake → nom_normalisé
        self.coherence_only: set = set()  # noms à traiter en "coherence_check_only"
        self.available  = False

    def load(self):
        if self.CNF_FILE.exists():
            self._parse(self.CNF_FILE)
        else:
            print(f"  ⚠ CNF non trouvé : {self.CNF_FILE}")

    def _parse(self, path: Path):
        print(f"  → CNF flat: {path.name}")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            loaded = 0
            for food in data.get("foods_flat", []):
                # V13 FIX : aplatir les sous-dicts nutrients.* en un seul dict
                # puis appliquer FIELD_MAP sur le dict aplati.
                nuts = food.get("nutrients", {})
                flat: dict = {}
                for section_val in nuts.values():
                    if isinstance(section_val, dict):
                        flat.update(section_val)
                # Les champs macros sont aussi dupliqués à la racine — fallback utile
                # si un variant CNF manque le sous-dict nutrients.
                for k in ("protein_g", "fat_g", "carbs_g", "fiber_g",
                          "calcium_mg", "iron_mg", "potassium_mg",
                          "magnesium_mg", "sodium_mg", "zinc_mg"):
                    if k not in flat and food.get(k) is not None:
                        flat[k] = food[k]
                # energy_kcal à la racine (fallback si nutrients.energy absent)
                if "kcal" not in flat and food.get("energy_kcal") is not None:
                    flat["kcal"] = food["energy_kcal"]

                entry: dict[str, Optional[float]] = {}
                for src_key, dst_key in self.FIELD_MAP.items():
                    entry[dst_key] = safe_float(flat.get(src_key))

                # V13 traçabilité par champ
                entry["_source_id"]   = str(food.get("id") or food.get("food_id") or "")
                entry["_source_name"] = str(food.get("name_en") or food.get("name_fr") or "")

                if entry.get("calories") is None and entry.get("protein") is None:
                    continue

                # Index par nom normalisé EN + FR
                name_en = normalize(food.get("name_en", "") or "")
                name_fr = normalize(food.get("name_fr", "") or "")

                if name_en:
                    self.db[name_en] = entry
                if name_fr and name_fr not in self.db:
                    self.db[name_fr] = entry

                if food.get("meta", {}).get("usage") == "coherence_check_only":
                    if name_en: self.coherence_only.add(name_en)
                    if name_fr: self.coherence_only.add(name_fr)

                food_id = food.get("id", "")
                if food_id:
                    self.id_map[food_id] = name_en or name_fr

                loaded += 1

            coherence_count = len(self.coherence_only)
            print(f"  ✔ CNF : {loaded} aliments ({coherence_count} coherence_check_only)")
            self.available = True

        except Exception as e:
            import traceback
            print(f"  ❌ Erreur CNF : {e}")
            traceback.print_exc()

    def lookup(self, name_en: str, name_fr: str = "") -> tuple[Optional[dict], str, float, bool]:
        """
        Recherche par nom avec fuzzy.
        Retourne (entry, matched_key, score, is_coherence_only).
        """
        if not self.available:
            return None, "", 0.0, False

        for query in filter(None, [normalize(name_en), normalize(name_fr)]):
            # Exact
            if query in self.db:
                is_coh = query in self.coherence_only
                return self.db[query], query, 1.0, is_coh

            # Fuzzy WRatio avec seuil élevé (CNF a moins d'aliments → moins de risque)
            if not self.db:
                continue
            names = list(self.db.keys())
            match, score, _ = process.extractOne(query, names, scorer=fuzz.WRatio)
            if score >= FUZZY_THRESHOLD + 5:   # seuil CNF légèrement plus strict
                is_coh = match in self.coherence_only
                return self.db[match], match, round(score / 100, 3), is_coh

        return None, "", 0.0, False

# ══════════════════════════════════════════════════════════════════════════
# 6. VALIDATION
# ══════════════════════════════════════════════════════════════════════════

def _read_all_nutrients(data: dict, variant_key: str = "default") -> dict:
    """
    Retourne un dict {short_key: float|None} depuis le schema v6 ou flat legacy.
    Priority : nutrients_v6 nested > flat variant > flat racine.
    """
    variants = data.get("variants", {})
    vdata = (variants.get(variant_key)
             or variants.get("default")
             or (next(iter(variants.values())) if variants else {}))

    n6 = vdata.get("nutrients_v6") or data.get("nutrients_v6") or {}
    result = {}

    for short_key, (section, field) in _V6_NESTED_PATHS.items():
        val = None
        if n6:
            sec = n6.get(section)
            if isinstance(sec, dict):
                val = safe_float(sec.get(field))
        if val is None:
            long_key = _SHORT_TO_LONG.get(short_key, short_key)
            val = (safe_float(vdata.get(long_key))
                   or safe_float(vdata.get(short_key))
                   or safe_float(data.get(long_key))
                   or safe_float(data.get(short_key)))
        result[short_key] = val

    # Métadonnées structurelles
    result["_carbs_schema"] = (
        vdata.get("carbs_schema") or data.get("carbs_schema") or "total"
    )
    result["_schema_version"] = data.get("schema_version", "")
    result["_has_nutrients_v6"] = bool(n6)
    result["_has_state"]        = bool(vdata.get("state") or data.get("state"))
    result["_has_diet_profile"] = bool(vdata.get("diet_profile") or data.get("diet_profile"))
    result["_has_source_meta"]  = bool(vdata.get("_source_meta") or data.get("_source_meta"))
    return result


def validate_v6_blocks(name: str, nutrients: dict) -> list:
    """
    Valide la présence et la cohérence des blocs v6.
    Warnings informatifs (non-bloquants) si blocs absents.
    """
    issues = []
    schema = nutrients.get("_schema_version", "")

    if schema < SCHEMA_V6:
        return issues   # fichier pré-v6 : on ne valide pas les blocs v6

    if not nutrients.get("_has_nutrients_v6"):
        issues.append({"type": "nutrients_v6_missing",
                       "severity": "warning",
                       "reason": "bloc nutrients_v6 absent (auto_correct_v6 --dry-run ?)"})

    if not nutrients.get("_has_state"):
        issues.append({"type": "state_missing",
                       "severity": "warning",
                       "reason": "bloc state absent (inférence parse_state_v2 non appliquée)"})

    if not nutrients.get("_has_diet_profile"):
        issues.append({"type": "diet_profile_missing",
                       "severity": "warning",
                       "reason": "diet_profile absent (schema v6 attendu 38 flags)"})

    if not nutrients.get("_has_source_meta"):
        issues.append({"type": "source_meta_missing",
                       "severity": "info",
                       "reason": "_source_meta absent"})

    return issues


def validate_internal(name: str, data: dict) -> list:
    """
    Validation de cohérence interne.

    Vérifie (V13) :
    - Cohérence calories vs macros (formule Atwater, sauf exceptions)
    - fiber > carbs (impossible)
    - sugar > carbs (impossible)
    - saturated_fat > fat (impossible physiquement)
    - protein + carbs + fat > 105 (impossible)
    - Valeurs hors limites absolues (ABS_LIMITS)
    - Valeurs négatives
    - Champs obligatoires manquants
    - lipid_sub_incoherence : ratio sub/fat hors seuil ← V13
        warning  si ratio 0.15–0.45 (fa_incomplete)
        critical si ratio < 0.15    (source_conflict)
    - omega_gt_poly : omega3+omega6 > poly (critical) ← V13
    """
    issues = []
    # ── Lecture unifiée v6/legacy ─────────────────────────────────────────
    _nutrients_meta = _read_all_nutrients(data)
    issues.extend(validate_v6_blocks(name, _nutrients_meta))

    # Vérifier state.process.level1 si disponible
    _d = data.get("variants", {}).get("default", {})
    _state = _d.get("state") or data.get("state") or {}
    if _state and _state.get("process", {}).get("level1") == "unknown":
        issues.append({
            "type":     "state_level1_unknown",
            "severity": "info",
            "reason":   "state.process.level1='unknown' — parse_state_v2 n'a pas convergé",
        })

    # ── Guard ombrelles sans default variant ────────────────────────────────
    # Les bases CATEGORY_INGREDIENTS sans variant "default" sont des types
    # ombrelles résolus au rendu recette (no-match = comportement correct).
    # Valider leurs champs plats hérités produirait des faux critiques
    # (macro_sum_impossible, energy_mismatch) sur des données non représentatives.
    if name in CATEGORY_INGREDIENTS and not _d:
        return []   # no-match légitime — aucune validation interne

    # Lire les champs — support schema v2 (variants.default) + flat legacy

    def _get(long_key, short_key):
        return safe_float(
            data.get(long_key) or data.get(short_key)
            or _d.get(long_key) or _d.get(short_key)
        )

    # ── Lecture carbs_schema (tag posé par patch_nutrition_v7.py) ─────────
    # "available" = glucides disponibles CIQUAL (total − fibres)
    # "total"     = glucides totaux USDA (fibres incluses) — défaut
    _carbs_schema = (
        _d.get("carbs_schema")
        or data.get("carbs_schema")
        or ("available" if name in FIBER_GT_CARBS_EXCEPTIONS else "total")
    )

    cal    = _get("calories_kcal", "calories")
    p      = _get("protein_g",     "protein")
    c      = _get("carbs_g",       "carbs")
    f      = _get("fat_g",         "fat")
    fib    = _get("fiber_g",       "fiber")
    sug    = _get("sugar_g",       "sugar")
    sat    = _get("saturated_fat_g",       "saturated_fat")
    mono   = _get("monounsaturated_fat_g", "mufa")
    poly   = _get("polyunsaturated_fat_g", "pufa")
    omega3 = _get("omega3_g", "omega3")
    omega6 = _get("omega6_g", "omega6")

    # ── Cohérence énergie / macros ─────────────────────────────────────────
    # Correction Atwater CIQUAL : si carbs_schema = "available", la formule
    # standard P×4 + C×4 + F×9 sous-estime car C ne contient pas les fibres.
    # On ajoute les fibres (rendement ~2 kcal/g) pour compenser.
    if name not in FORMULA_EXCEPTIONS and name not in NON_SCORING:
        if all(v is not None for v in [cal, p, c, f]) and cal > 0:
            if _carbs_schema == "available" and fib is not None:
                # Atwater corrigé CIQUAL : glucides disponibles + fibres×2
                estimated = p * 4.0 + c * 4.0 + fib * 2.0 + f * 9.0
            else:
                estimated = p * 4.0 + c * 4.0 + f * 9.0
            d = pct_delta(cal, estimated)
            cls = classify(d)
            if cls != "ok":
                issues.append({
                    "type": "energy_mismatch",
                    "declared_kcal": cal,
                    "estimated_from_macros": round(estimated, 1),
                    "delta_pct": d,
                    "severity": cls,
                    "carbs_schema": _carbs_schema,
                })

    # ── Cohérence fibres / glucides ────────────────────────────────────────
    # V14 : utilise carbs_schema dynamique en priorité sur la liste statique.
    # Si carbs_schema = "available" → fiber > carbs est NORMAL (CIQUAL dispo).
    # Si carbs_schema = "total"     → fiber > carbs est IMPOSSIBLE → critical.
    _fiber_schema_exempt = (
        _carbs_schema == "available"
        or name in FIBER_GT_CARBS_EXCEPTIONS
    )
    if (fib is not None and c is not None and fib > c + 0.5
            and not _fiber_schema_exempt):
        issues.append({
            "type": "fiber_gt_carbs",
            "fiber": fib, "carbs": c,
            "carbs_schema": _carbs_schema,
            "severity": "critical"
        })

    # ── Cohérence sucres / glucides ────────────────────────────────────────
    if sug is not None and c is not None and sug > c + 0.5 and name not in SUGAR_GT_CARBS_EXCEPTIONS:
        issues.append({
            "type": "sugar_gt_carbs",
            "sugar": sug, "carbs": c,
            "severity": "warning"
        })

    # ── saturated_fat > fat (impossible physiquement) ─────────────────────
    # SAT_GT_FAT_EXCEPTIONS : ingrédients dont fat_g est sous-estimé par fusion
    # multi-source (fat CIQUAL + sat USDA). Artefact corrigé dans auto_correct_v6
    # via KNOWN_LIPID_PROFILES — pas une erreur de données réelle.
    if sat is not None and f is not None and sat > f + 0.5 and name not in SAT_GT_FAT_EXCEPTIONS:
        issues.append({
            "type": "saturated_fat_gt_fat",
            "saturated_fat": sat, "fat": f,
            "severity": "critical"
        })

    # ── Cohérence lipidique : sat+mono+poly vs fat_g ── V13 ──────────────
    # Sévérité différenciée selon ratio :
    #   ratio < 0.15 → source_conflict (critical) : contamination probable
    #   ratio 0.15–0.45 → fa_incomplete (warning) : vrais suspects (fusion variants, données manquantes)
    #   ratio 0.45–1.0 ou sub=0 → OK (structurel CIQUAL : glycérol + phospholipides non comptés
    #       dans sat+mufa+pufa représentent ~5–35% de fat_g selon l'aliment → ratio naturel 0.60–0.95)
    # Seuil fat > 0.5g pour l'analyse de cohérence lipidique :
    # En dessous de 0.5g, mono/poly sont souvent absents (trace) → ratio non significatif.
    # Le seuil "critical" reste conditionné à fat >= 1g pour ne signaler que les vraies incohérences.
    if f is not None and f > 0.5:
        # Seuil relevé à 0.5g (était 0.3g) : en dessous, sat/mufa/pufa sont
        # souvent absents ou arrondis à zéro → ratio non significatif (date, pea_protein…).
        # BUGFIX : inclure trans_fat dans total_sub pour éviter les faux positifs
        # sur fruits/légumes/herbes où trans_fat est absent (présent sur ~7/292 ingrédients).
        # Sans trans_fat, le ratio est systématiquement sous-évalué → warnings spurieux.
        trans  = _get("trans_fat_g", "trans_fat")
        total_sub = (sat or 0.0) + (mono or 0.0) + (poly or 0.0) + (trans or 0.0)
        if total_sub > 0:
            ratio = total_sub / f
            if ratio < 0.45:
                # Faux positifs sur aliments à trace lipidique (fat < 1g) :
                # ne jamais classifier critical si fat < 1g
                if ratio < 0.15 and f >= 1.0:
                    sev = "critical"
                    subtype = "source_conflict"
                elif ratio < 0.15:
                    sev = "warning"        # downgrade : fat trop faible pour conclure
                    subtype = "fa_incomplete"
                else:
                    # fa_incomplete (ratio 0.15–0.45) : ne signaler qu'à partir de 1g de fat.
                    # En dessous, données FA partielles mais non significatives.
                    # Cas couverts : pea_protein (fat=0.83g), moringa (fat=0.80g).
                    # Exception structurelle : légumes feuilles à phospholipides membranaires
                    # (chloroplastes) non capturés dans sat+mufa+pufa → ratio ~0.40 normal.
                    # Cas couvert : kale (fat=1.11g, ratio=0.415).
                    _LIPID_FA_STRUCT_EXCEPTIONS = {"kale", "spinach", "watercress", "swiss_chard"}
                    if f < 1.0 or name in _LIPID_FA_STRUCT_EXCEPTIONS:
                        total_sub = -1  # force skip du issues.append ci-dessous
                    sev = "warning"
                    subtype = "fa_incomplete"
                if total_sub >= 0:   # total_sub=-1 = skip forcé (fat < 1g, fa_incomplete)
                    issues.append({
                        "type": "lipid_sub_incoherence",
                        "subtype": subtype,
                        "fat_g": f,
                        "sat_g": sat, "mono_g": mono, "poly_g": poly,
                        "total_sub_g": round(total_sub, 4),
                        "ratio": round(ratio, 4),
                        "severity": sev,
                    })

    # omega3 + omega6 > poly (omega subset PUFA, biologiquement impossible)
    # Tolerance absolue rehaussee : 0.1g pour eviter les faux positifs USDA
    # sur valeurs traces (rounding de 0.01-0.04g = bruit de mesure).
    # Si poly < 0.5g -> downgrade en warning (traces peu fiables).
    if poly is not None and poly >= 0:
        total_omega = (omega3 or 0.0) + (omega6 or 0.0)
        omega_delta = total_omega - (poly or 0.0)
        if omega_delta > 0.1:
            sev_omega = "warning" if (poly or 0.0) < 0.5 else "critical"
            issues.append({
                "type": "omega_gt_poly",
                "poly_g": poly,
                "omega3_g": omega3, "omega6_g": omega6,
                "total_omega_g": round(total_omega, 4),
                "delta_g": round(omega_delta, 4),
                "severity": sev_omega,
            })


    # ── Somme macros > 105 (impossible physiquement) ──────────────────────
    if all(v is not None for v in [p, c, f]):
        macro_sum = p + c + f
        if macro_sum > 105:
            issues.append({
                "type": "macro_sum_impossible",
                "sum": round(macro_sum, 1),
                "protein": p, "carbs": c, "fat": f,
                "severity": "critical"
            })

    # ── Limites absolues (ABS_LIMITS) ─────────────────────────────────────
    for fname, (lo, hi) in ABS_LIMITS.items():
        val = safe_float(data.get(fname))
        if val is None:
            continue
        if val < lo or val > hi:
            issues.append({
                "type": "value_out_of_range",
                "field": fname,
                "value": val,
                "allowed": [lo, hi],
                "severity": "critical" if (val < 0 or val > hi * 1.1) else "warning"
            })

    # ── Valeurs négatives (champs non couverts par ABS_LIMITS) ────────────
    for fname, val in [("calories", cal), ("protein", p), ("carbs", c), ("fat", f)]:
        if val is not None and val < 0:
            # Éviter le doublon avec value_out_of_range
            if not any(i["type"] == "value_out_of_range" and i["field"] == fname
                       for i in issues):
                issues.append({
                    "type": f"negative_{fname}",
                    "value": val,
                    "severity": "critical"
                })

    # ── Champs obligatoires manquants ──────────────────────────────────────
    # Supporte les deux conventions : clés courtes et clés suffixées (_kcal/_g)
    _FIELD_ALIASES = {
        "calories": ("calories_kcal", "calories"),
        "protein":  ("protein_g",     "protein"),
        "carbs":    ("carbs_g",        "carbs"),
        "fat":      ("fat_g",          "fat"),
    }
    if (name not in NON_SCORING
            and name not in CATEGORY_INGREDIENTS
            and name not in PARTIAL_DATA_OK):
        for fname, aliases in _FIELD_ALIASES.items():
            # V12 : utilise _get() pour supporter variants.default (schema v2)
            if _get(aliases[0], aliases[1]) is None:
                issues.append({
                    "type": "missing_field",
                    "field": fname,
                    "severity": "warning"
                })

    # ── Règles biologiques ─────────────────────────────────────────────────────
    category = data.get("_meta", {}).get("category")

    # 4a. Lait animal — fiber et starch biologiquement nuls
    if name in ANIMAL_MILK_KEYS:
        starch = _get("starch_g", "starch")
        if fib is not None and fib > 0:
            issues.append({
                "type": "bio_animal_milk_fiber",
                "field": "fiber_g", "value": fib,
                "reason": "lait animal = 0 fibre",
                "severity": "critical",
            })
        if starch is not None and starch > 0:
            issues.append({
                "type": "bio_animal_milk_starch",
                "field": "starch_g", "value": starch,
                "reason": "lait animal = 0 amidon (lactose ≠ starch)",
                "severity": "critical",
            })

    # 4b. Végétaux — cholestérol = 0
    if category in PLANT_CATEGORIES:
        chol = _get("cholesterol_mg", "cholesterol")
        if chol is not None and chol > 0:
            issues.append({
                "type": "bio_plant_cholesterol",
                "field": "cholesterol_mg", "value": chol,
                "reason": "aliment végétal = 0 cholestérol",
                "severity": "critical",
            })

    # 4c. Catégorie fat (noix/graines) — sodium aberrant
    if category == "fat" and name not in FAT_SODIUM_EXCEPTIONS:
        sod = _get("sodium_mg", "sodium")
        if sod is not None and sod > FAT_CATEGORY_SODIUM_THRESHOLD:
            issues.append({
                "type": "bio_nut_sodium_high",
                "field": "sodium_mg", "value": sod,
                "threshold": FAT_CATEGORY_SODIUM_THRESHOLD,
                "reason": f"sodium > {FAT_CATEGORY_SODIUM_THRESHOLD} mg pour une noix/graine brute",
                "severity": "warning",
            })

    # ── data_truth_score ── V13 ──────────────────────────────────────────
    # Score distinct de validation_score (cohérence structurelle).
    # Pénalise les problèmes de vérité scientifique des données lipidiques.
    # Retourné dans le dict d'issues pour usage par quick_audit et rapport.
    truth_penalty = 0.0
    for iss in issues:
        t = iss.get("type")
        sev = iss.get("severity")
        if t == "lipid_sub_incoherence":
            sub = iss.get("subtype")
            truth_penalty += 0.15 if sub == "source_conflict" else 0.05
        elif t == "omega_gt_poly":
            truth_penalty += 0.10
        elif sev == "critical":
            truth_penalty += 0.10
        elif sev == "warning":
            truth_penalty += 0.02
    data_truth_score = round(max(0.0, 1.0 - truth_penalty), 4)
    issues.append({
        "type": "_data_truth_score",
        "score": data_truth_score,
        "severity": "info",
    })

    return issues


# ── Corrections systémiques de mesure ──────────────────────────────────────
#
# 1. GLUCIDES USDA vs CIQUAL
#    USDA : carbs = glucides totaux (by difference, inclut les fibres)
#    CIQUAL / ALIM : carbs = glucides disponibles (totaux − fibres)
#    Correction : carbs_USDA_ajusté = carbs_USDA − fiber_USDA
#
# 2. TOLÉRANCE ABSOLUE PAR CHAMP
#    Un Δ% de 100% sur fat=0.4g est nutritionnellement négligeable.
#    On ignore les discordances dont la différence absolue est inférieure
#    au seuil du champ (unité native : g, mg, ug, kcal).
#
# 3. PROTÉINES : JONES vs N×6.25
#    USDA utilise N×6.25 (facteur générique).
#    CIQUAL et la majorité des bases européennes utilisent le facteur de Jones
#    (spécifique par aliment : blé ~5.7, soja ~5.71, lait ~6.38…).
#    Jones donne ~10–11% moins de protéines que N×6.25 pour les végétaux.
#    Correction appliquée à la référence USDA : ref_protein × 0.89

# Seuils de différence absolue négligeable (en unités natives du champ)
_ABS_NEGLIGIBLE = {
    "calories":      10.0,   # kcal
    "protein":        0.5,   # g
    "carbs":          1.5,   # g
    "fat":            0.5,   # g
    "fiber":          0.5,   # g
    "sugar":          1.0,   # g
    "calcium":       15.0,   # mg
    "iron":           0.5,   # mg
    "potassium":     50.0,   # mg
    "magnesium":      5.0,   # mg
    "sodium":        25.0,   # mg
    "zinc":           0.3,   # mg
    "selenium":       2.0,   # µg
    "vitamin_c":      3.0,   # mg
    "vitamin_a":     20.0,   # µg
    "vitamin_d":      0.5,   # µg
    # v6 — nouveaux champs
    "iodine":         5.0,   # µg
    "choline":       10.0,   # mg
    "folate":         5.0,   # µg
    "vitamin_k2":     2.0,   # µg
    "vitamin_b12":    0.1,   # µg
    "trans_fat":      0.2,   # g
    "omega3":         0.2,   # g
    "omega3_ala":     0.2,   # g
    "organic_acids":  0.5,   # g
    "polyols":        1.0,   # g
}

# Mapping clés courtes ↔ clés longues (nutrition_v2 variants.default)
_SHORT_TO_LONG = {
    "calories":      "calories_kcal",
    "protein":       "protein_g",
    "carbs":         "carbs_g",
    "fat":           "fat_g",
    "fiber":         "fiber_g",
    "sugar":         "sugar_g",
    "saturated_fat": "saturated_fat_g",
    "mufa":          "monounsaturated_fat_g",
    "pufa":          "polyunsaturated_fat_g",
    "trans_fat":     "trans_fat_g",
    "omega3":        "omega3_g",
    "omega3_ala":    "omega3_ala_g",
    "omega6":        "omega6_g",
    "cholesterol":   "cholesterol_mg",
    "calcium":       "calcium_mg",
    "iron":          "iron_mg",
    "potassium":     "potassium_mg",
    "magnesium":     "magnesium_mg",
    "sodium":        "sodium_mg",
    "zinc":          "zinc_mg",
    "selenium":      "selenium_ug",
    "iodine":        "iodine_ug",
    "vitamin_c":     "vitamin_c_mg",
    "vitamin_a":     "vitamin_a_ug",
    "vitamin_d":     "vitamin_d_ug",
    "vitamin_b12":   "vitamin_b12_ug",
    "vitamin_k2":    "vitamin_k2_ug",
    "choline":       "choline_mg",
    "folate":        "folate_ug",
    "polyols":       "polyols_g",
    "organic_acids": "organic_acids_g",
}



def _get_effective_score_threshold(ingredient_name: str) -> float:
    """Retourne le seuil de score effectif pour un ingrédient (V12)."""
    return FUZZY_SCORE_OVERRIDES.get(ingredient_name, FUZZY_THRESHOLD / 100.0)


def _check_plausible_range(ingredient_name: str, ing_data: dict,
                            field: str, proposed_value: float) -> bool:
    """Vérifie que proposed_value est dans les bornes plausibles (V12).
    Priorité : bornes individuelles > bornes catégorie. True = accepté."""
    ing_ranges = INGREDIENT_PLAUSIBLE_RANGES.get(ingredient_name, {})
    if field in ing_ranges:
        lo, hi = ing_ranges[field]
        return lo <= proposed_value <= hi
    category = ing_data.get("_meta", {}).get("category", "")
    cat_ranges = CATEGORY_PLAUSIBLE_RANGES.get(category, {})
    if field in cat_ranges:
        lo, hi = cat_ranges[field]
        return lo <= proposed_value <= hi
    return True


def _is_extended_sentinel(field: str, proposed_value: float, score: float) -> bool:
    """Retourne True si proposed_value est une sentinelle connue et score insuffisant (V12)."""
    for s in _EXTENDED_SENTINELS.get(field, []):
        if abs(proposed_value - s) < 0.01 and score < _EXTENDED_SENTINEL_SCORE_THRESHOLD:
            return True
    return False


def _detect_multi_field_contamination(ingredient_proposals: dict,
                                       current_data: dict) -> set:
    """Détecte une contamination multi-champ : ≥3 minéraux avec ratio <0.2 ou >5
    simultanément → mauvais match de variante. Retourne les champs à rejeter (V12)."""
    MINERAL_GROUP = ["calcium", "magnesium", "zinc", "potassium", "iron", "sodium"]
    ratios = {}
    for field in MINERAL_GROUP:
        prop = ingredient_proposals.get(field)
        if prop is None:
            continue
        current = prop.get("current")
        proposed = prop.get("proposed")
        if current is None or proposed is None:
            continue
        try:
            cur_f, pro_f = float(current), float(proposed)
            if cur_f > 0:
                ratios[field] = pro_f / cur_f
        except (TypeError, ValueError):
            pass
    if len(ratios) < 3:
        return set()
    low_contamination  = [f for f, r in ratios.items() if r < 0.2]
    high_contamination = [f for f, r in ratios.items() if r > 5.0]
    rejected = set()
    if len(low_contamination) >= 3:
        rejected.update(low_contamination)
    if len(high_contamination) >= 3:
        rejected.update(high_contamination)
    return rejected


def compare_to_source(declared: dict, reference: dict, source: str, score: float, ingredient_name: str = "") -> list:
    """Compare les champs FIELDS entre la DB locale et une source externe.

    Support schéma v2 (variants.default) + flat legacy.
    nutrition_v2.json stocke les valeurs sous variants.default avec des clés
    longues (ex: "calories_kcal") alors que FIELDS et les références utilisent
    des clés courtes (ex: "calories").
    Résolution : racine courte → variants.default courte → variants.default longue.
    """
    _flat = declared.get("variants", {}).get("default", {})

    # ── Lecture carbs_schema du variant déclaré ────────────────────────────
    # Priorité : variants.default > racine > fallback "total"
    _local_carbs_schema = (
        _flat.get("carbs_schema")
        or declared.get("carbs_schema")
        or "total"
    )

    def _get_declared(field: str):
        # 1. Clé courte à la racine (schéma flat legacy)
        v = declared.get(field)
        if v is not None:
            return v
        # 2. Clé courte dans variants.default
        v = _flat.get(field)
        if v is not None:
            return v
        # 3. Clé longue dans variants.default (schéma nutrition_v2)
        long_key = _SHORT_TO_LONG.get(field)
        if long_key:
            v = _flat.get(long_key)
            if v is not None:
                return v
            v = declared.get(long_key)
        return v

    discrepancies = []
    for field in FIELDS:
        # ── v6 : exclusivité source — ne comparer que contre la source autorisée ──
        exclusive_src = SOURCE_EXCLUSIVE_COMPARE.get(field)
        if exclusive_src and source.upper() != exclusive_src:
            continue
        # ── fin exclusivité ───────────────────────────────────────────────────────

        dec = safe_float(_get_declared(field))
        ref = safe_float(reference.get(field))

        # ── Garde universelle : sentinelles + seuil macro ────────────────────
        # BUG FIX v15 : ces deux gardes étaient limitées au cas dec=None
        # (enrichissement). Elles s'appliquent maintenant à TOUS les champs
        # non-nuls — enrichissement ET correction — pour bloquer les faux matches.
        #
        # Sentinelle : valeurs caractéristiques de "Farine de soja complète"
        # (ciqual_code=20915) qui contaminent toute DB via un fuzzy match faible.
        # Si la valeur proposée est une sentinelle connue ET score < 0.92 → rejet.
        if ref is not None:
            _sentinel = _ACAI_SENTINELS.get(field)
            if _sentinel is not None and abs(ref - _sentinel) < 0.01 and score < MIN_SCORE_MACRO_ENRICHMENT:
                continue   # rejet : contamination soja/acaï détectée
            # Seuil élevé pour macros (score insuffisant → ni enrichissement ni correction)
            if field in _MACRO_FIELDS_STRICT and score < MIN_SCORE_MACRO_ENRICHMENT:
                continue
            # ── V12 FIX d) : sentinelles étendues ─────────────────────────────
            if _is_extended_sentinel(field, ref, score):
                continue
            # ── V12 FIX c) : bornes plausibles contextuelles ──────────────────
            if ingredient_name and not _check_plausible_range(ingredient_name, declared, field, ref):
                continue

        # ── P1 FIX : enrichissement (dec=None, ref présent) ─────────────────
        # Les gardes ci-dessus ont déjà filtré les cas problématiques.
        # Ici : enrichissement accepté (dec manquant, ref validée).
        if dec is None and ref is not None:
            # Enrichissement accepté : delta_pct = 0 (pas de "correction"), severity=info
            discrepancies.append({
                "field":       field,
                "declared":    None,
                "reference":   ref,
                "delta_pct":   0.0,   # enrichissement pur : pas de delta mesurable
                "severity":    "info",
                "source":      source,
                "match_score": score,
                "source_id":   reference.get("_source_id", ""),
                "source_name": reference.get("_source_name", ""),
                "enrichment":  True,
            })
            continue

        if None in (dec, ref) or ref == 0:
            continue

        # ── Correction 1 : glucides disponibles CIQUAL vs totaux USDA ──────
        # USDA stocke carbs = glucides totaux (fiber incluse).
        # ALIM/CIQUAL stocke carbs = glucides disponibles (totaux − fibres).
        # Correction appliquée UNIQUEMENT si la DB locale est en schéma "available".
        # Si la DB est déjà en schéma "total" (ex: ingrédient sourcé USDA),
        # on compare directement sans ajustement pour éviter la double-soustraction.
        if field == "carbs" and source.upper().startswith("USDA"):
            if _local_carbs_schema == "available":
                # DB = glucides dispo → ajuster la référence USDA
                ref_fiber = safe_float(reference.get("fiber"))
                if ref_fiber is not None:
                    ref = ref - ref_fiber
                    if ref <= 0:
                        continue   # résidu nul ou négatif : rien à comparer
            # else: DB = total → comparer directement, pas d'ajustement

        # Note : la correction Jones (×0.89 sur protéines USDA) a été retirée —
        # nutrition_v2 mélange des sources CIQUAL (Jones) et USDA (N×6.25),
        # une correction uniforme aggrave les deltas pour les ingrédients
        # déjà sourcés depuis USDA. Les différences protéiques < 20% sont
        # absorbées par le seuil DELTA_WARN.

        d = pct_delta(dec, ref)
        cls = classify(d)
        if cls != "ok":
            # ── Correction 3 : tolérance absolue ────────────────────────────
            # Un Δ% élevé sur une valeur absolue négligeable (ex: fat=0.4g)
            # ne justifie pas une alerte. On ignore si |dec − ref| < seuil.
            abs_threshold = _ABS_NEGLIGIBLE.get(field, 0.5)
            if abs(dec - ref) < abs_threshold:
                continue

            # Plafonner à "warning" si le match est incertain (score < 0.85)
            if cls == "critical" and score < 0.85:
                cls = "warning"
            discrepancies.append({
                "field": field,
                "declared": dec,
                "reference": ref,
                "delta_pct": d,
                "severity": cls,
                "source": source,
                "match_score": score,
                "source_id":   reference.get("_source_id", ""),
                "source_name": reference.get("_source_name", ""),
            })
    return discrepancies


def merge_proposals(existing: dict, new_discs: list) -> dict:
    """
    Fusionne les propositions de correction.

    Pondération V10 : source_rank × match_score
      → Un match CIQUAL à 0.76 (score=76) donne un poids de 2 × 0.76 = 1.52
      → Un match USDA  à 1.00 (exact) donne un poids de  1 × 1.00 = 1.00
      → Dans ce cas USDA exact bat CIQUAL fuzzy faible.

    Priorité finale (poids décroissant) :
      CIQUAL exact  (2 × 1.0 = 2.0) > USDA exact (1 × 1.0 = 1.0)
      > CIQUAL 0.85 (2 × 0.85 = 1.7) > USDA 0.85 (1 × 0.85 = 0.85)
    """
    result = dict(existing)
    SOURCE_RANK = {"CIQUAL": 2, "USDA": 1}

    for disc in new_discs:
        field = disc["field"]
        existing_prop = result.get(field)

        new_weight = SOURCE_RANK.get(disc["source"], 0) * disc["match_score"]
        old_weight = (
            SOURCE_RANK.get(existing_prop.get("source", ""), 0)
            * existing_prop.get("match_score", 0)
            if existing_prop else -1
        )

        # À poids égal, garde le plus grand delta (discordance la plus marquée)
        is_better = (
            not existing_prop
            or new_weight > old_weight
            or (new_weight == old_weight
                and disc["delta_pct"] > existing_prop.get("delta_pct", 0))
        )
        if is_better:
            result[field] = {
                "current":     disc["declared"],
                "proposed":    disc["reference"],
                "delta_pct":   disc["delta_pct"],
                "severity":    disc["severity"],
                "source":      disc["source"],
                "match_score": disc["match_score"],
                "source_id":   disc.get("source_id", ""),
                "source_name": disc.get("source_name", ""),
                "weight":      round(new_weight, 3),
                "action":      "replace"   # changer en "keep" pour refuser
            }
    return result


# ══════════════════════════════════════════════════════════════════════════
# 7. PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════

def run_validation(db_file=None):
    OUTPUT_DIR.mkdir(exist_ok=True)
    SOURCES_DIR.mkdir(exist_ok=True)

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║    Nutrition Validator V13 — Validation Croisée      ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    ingredients, ciqual_id_map, ciqual_note_map = load_local_db(db_file=db_file)
    print()

    print("Chargement des sources de référence...")
    ciqual = CIQUALLoader()
    ciqual.load()
    usda = USDALoader()
    usda.load()
    cnf = CNFLoader()           # V13 — source de fallback (priorité 3)
    cnf.load()
    print()

    stats = {
        "total": 0, "ok": 0, "warning": 0, "critical": 0,
        "external_checked": 0, "proposals": 0,
        "ciqual_id_hits": 0, "ciqual_fuzzy_hits": 0, "usda_hits": 0,
        "cnf_hits": 0,          # V13

        "no_external_match": 0,
        "proposals_rejected_score": 0,
        "proposals_rejected_contamination": 0,
    }
    report = {}
    proposals_all = {}

    total = len(ingredients)
    print(f"Validation de {total} ingrédients...\n")

    for i, (name, data) in enumerate(ingredients.items(), 1):
        # ── Barre de progression ────────────────────────────────────────────
        pct = i / total
        bar_len = 40
        filled = int(bar_len * pct)
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"\r  [{bar}] {i}/{total}  ", end="", flush=True)

        stats["total"] += 1
        entry = {
            "name_fr": data.get("name_fr"),
            "name_en": data.get("name_en"),
            "internal_issues": [],
            "external_checks": [],
            "proposals": {},
            "status": "ok"
        }

        # ── Validation interne ──────────────────────────────────────────────
        entry["internal_issues"] = validate_internal(name, data)

        # ── V12 : seuil de score effectif par ingrédient ─────────────────────
        _effective_threshold = _get_effective_score_threshold(name)

        # ── V13 : extraction name_fr / name_en robuste ───────────────────────
        # Dans nutrition_v2 schema v6, name_fr est sous _meta ou variants.default
        # — pas à la racine. data.get("name_fr") retournait None systématiquement.
        _vdefault = data.get("variants", {}).get("default", {})
        _name_fr = (data.get("name_fr")
                    or data.get("_meta", {}).get("name_fr")
                    or _vdefault.get("name_fr")
                    or name.replace("_", " "))
        _name_en = (data.get("name_en")
                    or _vdefault.get("name_en")
                    or name.replace("_", " "))

        # ── Validation CIQUAL ───────────────────────────────────────────────
        had_external = False
        if ciqual.available:
            ref   = None
            label = ""
            score = 0.0

            cid = ciqual_id_map.get(name)
            if cid:
                ref = ciqual.lookup_by_id(cid)
                if ref:
                    label = f"CIQUAL id:{cid}"
                    score = 1.0
                    stats["ciqual_id_hits"] += 1

            if ref is None:
                ciqual_note = ciqual_note_map.get(name)
                if ciqual_note:
                    ref, matched, score = ciqual.lookup_by_name(ciqual_note)
                    if ref:
                        label = f"CIQUAL note:{matched}"
                        stats["ciqual_fuzzy_hits"] += 1

            if ref is None:
                ref, matched, score = ciqual.lookup_by_name(_name_fr)
                if ref:
                    label = f"CIQUAL fuzzy:{matched}"
                    stats["ciqual_fuzzy_hits"] += 1

            # ── V12 : rejeter si score < seuil effectif ──────────────────────
            if ref and score < _effective_threshold:
                stats["proposals_rejected_score"] += 1
                ref = None

            if ref:
                had_external = True
                stats["external_checked"] += 1
                discs = compare_to_source(data, ref, "CIQUAL", score, ingredient_name=name)
                entry["external_checks"].append({
                    "source": label,
                    "match_score": score,
                    "reference": {f: ref.get(f) for f in FIELDS},
                    "discrepancies": discs
                })
                entry["proposals"] = merge_proposals(entry["proposals"], discs)

        # ── Validation USDA ─────────────────────────────────────────────────
        if usda.available:
            ref, matched, score = usda.lookup(_name_en, _name_fr)
            # ── V12 : rejeter si score < seuil effectif ──────────────────────
            if ref and score < _effective_threshold:
                stats["proposals_rejected_score"] += 1
                ref = None

            if ref:
                had_external = True
                stats["usda_hits"] += 1
                discs = compare_to_source(data, ref, "USDA", score, ingredient_name=name)
                entry["external_checks"].append({
                    "source": f"USDA:{matched}",
                    "match_score": score,
                    "reference": {f: ref.get(f) for f in FIELDS},
                    "discrepancies": discs
                })
                entry["proposals"] = merge_proposals(entry["proposals"], discs)

        # ── Validation CNF (fallback — uniquement si CIQUAL+USDA ont raté) ──
        if cnf.available and not had_external:
            ref, matched, score, is_coh = cnf.lookup(_name_en, _name_fr)
            if ref and score < max(_effective_threshold, CNF_SCORE_THRESHOLD):
                stats["proposals_rejected_score"] += 1
                ref = None
            if ref:
                had_external = True
                stats["cnf_hits"] += 1
                discs = compare_to_source(data, ref, "CNF", score, ingredient_name=name)
                # Entrées "coherence_check_only" → dégrader en info (non-bloquant)
                if is_coh:
                    for d in discs:
                        d["severity"] = "info"
                entry["external_checks"].append({
                    "source": f"CNF:{matched}",
                    "match_score": score,
                    "reference": {f: ref.get(f) for f in FIELDS},
                    "discrepancies": discs
                })
                entry["proposals"] = merge_proposals(entry["proposals"], discs)

        if not had_external and (ciqual.available or usda.available or cnf.available):
            stats["no_external_match"] += 1

        # ── V12 : détection contamination multi-champs ────────────────────────
        if entry["proposals"]:
            _rejected_fields = _detect_multi_field_contamination(entry["proposals"], data)
            if _rejected_fields:
                stats["proposals_rejected_contamination"] += 1
                for _rf in _rejected_fields:
                    entry["proposals"].pop(_rf, None)

        # ── Statut final ─────────────────────────────────────────────────────
        all_issues = entry["internal_issues"] + [
            d for chk in entry["external_checks"] for d in chk["discrepancies"]
        ]
        if any(i.get("severity") == "critical" for i in all_issues):
            entry["status"] = "critical"
            stats["critical"] += 1
        elif all_issues:
            entry["status"] = "warning"
            stats["warning"] += 1
        else:
            stats["ok"] += 1

        if entry["proposals"]:
            stats["proposals"] += 1
            proposals_all[name] = entry["proposals"]

        report[name] = entry

    print()  # newline après la barre de progression

    # ── Sauvegarde ─────────────────────────────────────────────────────────
    with open(OUTPUT_DIR / "validation_report.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated": TODAY,
            "version": "v12",
            "stats": stats,
            "results": report
        }, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / "correction_proposals.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated": TODAY,
            "version": "v12",
            "_instructions": (
                "Réviser chaque proposition. "
                "Changer 'action' de 'replace' à 'keep' pour refuser. "
                "Puis lancer : python validator_v12.py --apply"
            ),
            "count": len(proposals_all),
            "proposals": proposals_all
        }, f, indent=2, ensure_ascii=False)

    # ── Résumé console ─────────────────────────────────────────────────────
    critical_list = [(n, e) for n, e in report.items() if e["status"] == "critical"]

    # Rapport de couverture externe
    any_ext = ciqual.available or usda.available
    coverage_pct = (
        round((stats["total"] - stats["no_external_match"]) / stats["total"] * 100, 1)
        if any_ext and stats["total"] else 0
    )

    print(f"\n{'═'*56}")
    print(f"  Total         : {stats['total']}")
    print(f"  ✔ OK          : {stats['ok']}")
    print(f"  ⚠ Warning     : {stats['warning']}")
    print(f"  ✗ Critical    : {stats['critical']}")
    print(f"  ──────────────────────────────────────────────")
    print(f"  CIQUAL par ID : {stats['ciqual_id_hits']}")
    print(f"  CIQUAL fuzzy  : {stats['ciqual_fuzzy_hits']}")
    print(f"  USDA hits     : {stats['usda_hits']}")
    print(f"  CNF hits      : {stats['cnf_hits']}")
    if any_ext:
        print(f"  Sans match ext: {stats['no_external_match']} "
              f"(couverture {coverage_pct}%)")
    print(f"  Corrections   : {stats['proposals']} proposées")
    print(f"  ── Gardes V13 ─────────────────────────────────")
    print(f"  Rejetés (score)        : {stats['proposals_rejected_score']}")
    print(f"  Rejetés (contamination): {stats['proposals_rejected_contamination']}")
    if critical_list:
        print(f"\n  Critiques :")
        for n, e in critical_list[:10]:
            # Chercher la première issue critique (interne ou externe)
            all_iss = e.get("internal_issues", []) + [
                d for chk in e.get("external_checks", [])
                for d in chk.get("discrepancies", [])
            ]
            crit_iss = [i for i in all_iss if i.get("severity") == "critical"]
            i0 = crit_iss[0] if crit_iss else (all_iss[0] if all_iss else {})
            t = i0.get("type", "?")
            if "delta_pct" in i0 and i0.get("source"):
                detail = f"{i0['source']} {i0.get('field','?')} Δ{i0['delta_pct']}%"
            elif "delta_pct" in i0:
                detail = f"Δ{i0['delta_pct']}%"
            elif t == "fiber_gt_carbs":
                detail = f"fiber({i0.get('fiber','?')})>carbs({i0.get('carbs','?')})"
            elif t == "energy_mismatch":
                detail = f"kcal({i0.get('declared_kcal','?')}) est({i0.get('estimated_from_macros','?')})"
            elif t == "missing_field":
                detail = f"champ manquant: {i0.get('field','?')}"
            elif t == "lipid_sub_incoherence":
                detail = f"lipid_sub fat={i0.get('fat_g','?')}g ratio={i0.get('ratio','?')}"
            else:
                detail = t
            print(f"    · {n} {detail}")
        if len(critical_list) > 10:
            print(f"    ... et {len(critical_list)-10} autres")
    print(f"{'═'*56}")
    print(f"\n  → outputs/validation_report.json")
    print(f"  → outputs/correction_proposals.json\n")


# ══════════════════════════════════════════════════════════════════════════
# 8. APPLICATION DES CORRECTIONS
# ══════════════════════════════════════════════════════════════════════════

def apply_corrections(min_severity: str = "warning", min_score: float = 0.90, db_file=None):
    proposals_file = OUTPUT_DIR / "correction_proposals.json"
    if not proposals_file.exists():
        print("❌ Lancer d'abord : python validator_v12.py")
        return

    severity_rank = {"ok": 0, "warning": 1, "critical": 2}
    min_rank = severity_rank.get(min_severity, 1)

    with open(proposals_file, encoding="utf-8") as f:
        pdata = json.load(f)
    active_file = db_file or resolve_db_file()
    with open(active_file, encoding="utf-8") as f:
        db = json.load(f)

    # ── Sauvegarde automatique avant toute modification ────────────────────
    backup_path = OUTPUT_DIR / f"nutrition_database_backup_{TODAY}.json"
    if not backup_path.exists():
        import shutil
        shutil.copy2(NUTRITION_DB_FILE, backup_path)
        print(f"  💾 Sauvegarde → {backup_path.name}")
    else:
        print(f"  💾 Sauvegarde déjà existante pour aujourd'hui : {backup_path.name}")

    applied, skipped = [], []

    for ingredient, fields in pdata["proposals"].items():
        if ingredient not in db["ingredients"]:
            continue
        for field, prop in fields.items():
            action   = prop.get("action", "replace")
            sev_rank = severity_rank.get(prop.get("severity", "ok"), 0)
            score    = prop.get("match_score", 1.0)

            if action == "keep":
                skipped.append(f"{ingredient}.{field} → keep (manuel)")
            elif sev_rank < min_rank:
                skipped.append(f"{ingredient}.{field} → sévérité insuffisante ({prop.get('severity')})")
            elif score < min_score:
                skipped.append(f"{ingredient}.{field} → score {score:.2f} < {min_score}")
            else:
                # ── Défense anti-contamination (ex: acai fuzzy) ──────────────
                _source   = prop.get("source", "")
                _current  = prop.get("current")
                _proposed = prop.get("proposed")
                _is_enrich = (_current is None)

                # Couche 1 : seuil enrichissement élevé sur macros CIQUAL
                if (_is_enrich and _source == "CIQUAL"
                        and field in _MACRO_FIELDS_STRICT
                        and score < MIN_SCORE_MACRO_ENRICHMENT):
                    skipped.append(
                        f"{ingredient}.{field} → CIQUAL enrichment score "
                        f"{score:.2f} < {MIN_SCORE_MACRO_ENRICHMENT} "
                        f"(macro enrichment threshold)"
                    )
                    continue

                # ── V12 : bornes plausibles au moment de --apply ──────────────
                if not _check_plausible_range(ingredient, db["ingredients"][ingredient], field, float(_proposed)):
                    skipped.append(
                        f"{ingredient}.{field} → out_of_plausible_range "
                        f"{_proposed} (gardes V12)"
                    )
                    continue
                # Couche 2 : détection valeurs sentinelles acaï
                # Étendu à TOUS les proposals (enrichissement ET remplacement)
                # fat=20.7 est une valeur acaï — impossible pour légumes/épices
                if _proposed is not None:
                    try:
                        _proposed_f = float(_proposed)
                        _sentinel = _ACAI_SENTINELS.get(field)
                        if _sentinel is not None and abs(_proposed_f - _sentinel) < 0.01:
                            skipped.append(
                                f"{ingredient}.{field} → sentinel_value "
                                f"{_proposed} matches acai contamination pattern"
                            )
                            continue

                        # Couche 3 : valeurs physiquement impossibles par catégorie
                        # fat=20.7 sur un légume/fruit/épice est impossible
                        _impossible = False
                        if field == "fat" and _proposed_f >= 20.0:
                            # Seuls les noix, graines, huiles, fromages peuvent avoir fat>20g
                            _fat_ok_categories = {
                                "nut", "seed", "oil", "cheese", "fat",
                                "meat", "fish", "egg", "dairy",
                            }
                            _ing_data = db.get("ingredients", {}).get(ingredient, {})
                            _cat = _ing_data.get("_meta", {}).get("category", "")
                            if _cat and _cat not in _fat_ok_categories:
                                _impossible = True
                        if field == "protein" and _proposed_f >= 30.0:
                            # Protéines >30g impossibles pour sirops/sucres/légumes
                            _ing_data = db.get("ingredients", {}).get(ingredient, {})
                            _cat = _ing_data.get("_meta", {}).get("category", "")
                            _protein_ok = {"protein_plant", "protein_animal", "legume", "grain", "dairy", "meat", "fish"}
                            if _cat and _cat not in _protein_ok:
                                _impossible = True
                        if _impossible:
                            skipped.append(
                                f"{ingredient}.{field} → impossible_value "
                                f"{_proposed} for category (acai contamination)"
                            )
                            continue
                    except (TypeError, ValueError):
                        pass
                # ── fin défense anti-contamination ───────────────────────────
                long_key  = _SHORT_TO_LONG.get(field, field)
                _ing      = db["ingredients"][ingredient]
                _vdefault = _ing.setdefault("variants", {}).setdefault("default", {})

                # Lire l'ancienne valeur depuis variants.default (schéma réel)
                old = _vdefault.get(long_key) or _vdefault.get(field)

                # ── V13 : anti-oscillation ────────────────────────────────────
                # Si ce champ a déjà une traçabilité (_source_meta), comparer
                # le rang de la source entrante avec celui de la source en place.
                # Refuser si la source entrante a un rang INFÉRIEUR OU ÉGAL
                # ET que la valeur proposée diffère — ce pattern génère exactement
                # l'oscillation CIQUAL↔USDA observée (carrot.K, cheddar.vit_A…).
                #
                # SOURCE_RANK : CIQUAL=2 > USDA=1 > CNF=0.5
                _APPLY_SOURCE_RANK = {"CIQUAL": 2, "USDA": 1, "CNF": 0.5}
                _sm_existing = _vdefault.get("_source_meta", {}).get(long_key, {})
                _existing_src_rank = _APPLY_SOURCE_RANK.get(
                    _sm_existing.get("source", ""), -1
                )
                _incoming_rank = _APPLY_SOURCE_RANK.get(prop["source"], 0)

                if (
                    _sm_existing                                     # traçabilité présente
                    and _existing_src_rank > _incoming_rank          # rang entrant < rang en place
                    and old is not None                              # valeur non nulle
                    and abs(float(old) - float(prop["proposed"])) > 0.01  # valeur différente
                ):
                    skipped.append(
                        f"{ingredient}.{long_key} → anti_oscillation: "
                        f"{prop['source']}(rank={_incoming_rank}) < "
                        f"{_sm_existing.get('source','')}(rank={_existing_src_rank}) "
                        f"déjà en place"
                    )
                    continue
                # ── fin anti-oscillation ─────────────────────────────────────

                # Écrire la valeur corrigée dans variants.default (long key)
                _vdefault[long_key] = prop["proposed"]

                # ── V13 traçabilité par champ ─────────────────────────────────
                _sm = _vdefault.setdefault("_source_meta", {})
                _sm[long_key] = {
                    "source":      prop["source"],
                    "source_id":   prop.get("source_id", ""),
                    "source_name": prop.get("source_name", ""),
                    "score":       prop["match_score"],
                    "rank":        _incoming_rank,
                    "date":        TODAY,
                    "original":    old,
                }
                # ── fin traçabilité ──────────────────────────────────────────

                # ── v6 : mettre à jour aussi nutrients_v6 nested si présent ──
                _n6 = _vdefault.get("nutrients_v6")
                if _n6:
                    for short_k, lk in _SHORT_TO_LONG.items():
                        if lk == long_key or short_k == field:
                            _path = _V6_NESTED_PATHS.get(short_k)
                            if _path:
                                section, nfield = _path
                                if section in _n6 and isinstance(_n6[section], dict):
                                    _n6[section][nfield] = prop["proposed"]
                            break
                # ── fin v6 ────────────────────────────────────────────────────

                applied.append(
                    f"{ingredient}.{long_key}: {old} → {prop['proposed']} "
                    f"({prop['source']} {prop.get('source_id','')}, Δ{prop['delta_pct']}%)"
                )

    out = OUTPUT_DIR / "nutrition_database_corrected.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print(f"\n✔ Appliquées : {len(applied)}")
    for line in applied[:25]:
        print(f"  · {line}")
    if len(applied) > 25:
        print(f"  ... et {len(applied)-25} autres")
    print(f"\n  Ignorées : {len(skipped)}")
    print(f"  → {out}\n")


# ══════════════════════════════════════════════════════════════════════════
# 9. ENRICHISSEMENT DU DICTIONNAIRE (--enrich)
# ══════════════════════════════════════════════════════════════════════════

def enrich_dictionary():
    """
    Enrichit ingredients_dictionary.json avec :
      - alim_nom_sci : nom scientifique latin depuis CIQUAL / USDA
      - name_en      : ajoute le champ si absent (depuis la clé id de l'entrée)

    Logique de résolution :
      1. Si ciqual_id présent dans ingredient_physical → CIQUAL lookup par ID (fiable)
      2. Sinon fuzzy match sur name_fr dans CIQUAL → alim_nom_sci si score ≥ 0.85
      3. Fallback : USDA scientificName si match exact sur name_en

    Output → outputs/ingredients_dictionary_enriched.json
    """
    OUTPUT_DIR.mkdir(exist_ok=True)

    if not DICT_FILE.exists():
        print(f"❌ Dictionnaire introuvable : {DICT_FILE}")
        return

    print("\n╔══════════════════════════════════════════════════════╗")
    print("║    Nutrition Validator V9 — Enrichissement Dict.     ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    with open(DICT_FILE, encoding="utf-8") as f:
        dct = json.load(f)

    # Charger CIQUAL et USDA pour les noms scientifiques
    _, ciqual_id_map, ciqual_note_map = load_local_db()
    print()

    ciqual = CIQUALLoader()
    ciqual.load()
    usda = USDALoader()
    usda.load()

    ings = dct.get("ingredients", [])

    stats = {"total": len(ings), "sci_added": 0, "sci_already": 0,
             "name_en_added": 0, "not_found": 0}

    for entry in ings:
        ing_id  = entry.get("id", "")
        name_fr = entry.get("name_fr", "")

        # ── name_en : on le prend de l'id si absent ─────────────────────────
        if not entry.get("name_en"):
            entry["name_en"] = ing_id.replace("_", " ")
            stats["name_en_added"] += 1

        # ── alim_nom_sci déjà présent ─────────────────────────────────────
        if entry.get("alim_nom_sci"):
            stats["sci_already"] += 1
            continue

        sci_name = None

        # Priorité 1 : ciqual_id connu → lookup direct (codes CIQUAL 2024)
        cid = ciqual_id_map.get(ing_id)
        if cid and ciqual.available:
            sci_name = ciqual.get_sci_name(cid)

        # Priorité 2 : note CIQUAL (nom exact)
        if not sci_name and ciqual.available:
            ciqual_note = ciqual_note_map.get(ing_id)
            if ciqual_note:
                _, matched, score = ciqual.lookup_by_name(ciqual_note)
                if score >= 0.85 and matched:
                    matched_cid = ciqual.by_name.get(matched)
                    if matched_cid:
                        sci_name = ciqual.get_sci_name(matched_cid)

        # Priorité 3 : fuzzy CIQUAL sur name_fr (seuil strict)
        if not sci_name and ciqual.available and name_fr:
            _, matched, score = ciqual.lookup_by_name(name_fr)
            if score >= 0.85 and matched:
                matched_cid = ciqual.by_name.get(matched)
                if matched_cid:
                    sci_name = ciqual.get_sci_name(matched_cid)

        # Priorité 4 : USDA scientificName
        if not sci_name and usda.available:
            name_en_key = normalize(entry.get("name_en", "") or ing_id)
            usda_sci = usda.sci_map.get(name_en_key)
            if usda_sci:
                sci_name = usda_sci
            else:
                # Essai fuzzy USDA (seuil strict)
                if usda.db:
                    names = list(usda.sci_map.keys())
                    if names:
                        match, score, _ = process.extractOne(
                            name_en_key, names, scorer=fuzz.WRatio
                        )
                        if score >= 90:
                            sci_name = usda.sci_map.get(match)

        if sci_name:
            entry["alim_nom_sci"] = sci_name
            stats["sci_added"] += 1
        else:
            stats["not_found"] += 1

    # Mettre à jour les métadonnées
    dct["_enrichment_date"] = TODAY
    dct["_enrichment_version"] = "v9"

    out = OUTPUT_DIR / "ingredients_dictionary_enriched.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(dct, f, indent=2, ensure_ascii=False)

    print(f"\n{'═'*52}")
    print(f"  Ingrédients traités : {stats['total']}")
    print(f"  alim_nom_sci ajoutés : {stats['sci_added']}")
    print(f"  alim_nom_sci déjà présents : {stats['sci_already']}")
    print(f"  name_en déduits : {stats['name_en_added']}")
    print(f"  Non trouvés : {stats['not_found']}")
    print(f"{'═'*52}")
    print(f"\n  → {out}\n")


# ══════════════════════════════════════════════════════════════════════════
# 10. AUDIT RAPIDE (--audit)
# ══════════════════════════════════════════════════════════════════════════

def quick_audit(db_file=None):
    active_file = db_file or resolve_db_file()
    print(f"  Source : {active_file.name}\n")
    with open(active_file, encoding="utf-8") as f:
        db = json.load(f)
    ing = db["ingredients"]

    rows = []
    for name, data in ing.items():
        issues = validate_internal(name, data)
        for iss in issues:
            t = iss.get("type")
            if t == "energy_mismatch":
                rows.append((
                    name,
                    iss["declared_kcal"],
                    iss["estimated_from_macros"],
                    iss["delta_pct"],
                    iss["severity"]
                ))
            elif t in ("fiber_gt_carbs", "sugar_gt_carbs",
                       "saturated_fat_gt_fat", "macro_sum_impossible"):
                rows.append((name, t, "-", 999, iss["severity"]))
            elif t == "lipid_sub_incoherence":
                rows.append((
                    name,
                    f"lipid_{iss['subtype']}",
                    f"fat={iss['fat_g']}g sub={iss['total_sub_g']}g",
                    round(iss["ratio"] * 100, 1),
                    iss["severity"]
                ))
            elif t == "omega_gt_poly":
                rows.append((
                    name,
                    "omega_gt_poly",
                    f"poly={iss['poly_g']}g ω={iss['total_omega_g']}g",
                    round(iss["delta_g"], 2),
                    iss["severity"]
                ))
            elif t == "_data_truth_score":
                pass  # collecté séparément ci-dessous
            elif t == "value_out_of_range":
                rows.append((
                    name,
                    f"{iss['field']}={iss['value']}",
                    f"max={iss['allowed'][1]}",
                    500,
                    iss["severity"]
                ))
            elif t == "missing_field":
                rows.append((name, f"missing:{iss['field']}", "-", 0, iss["severity"]))

    rows.sort(key=lambda x: (x[4] == "critical", x[3]), reverse=True)

    print(f"\n{'─'*72}")
    print(f"{'Ingrédient':<32} {'Info':<20} {'Estimé':>8} {'Delta':>7} {'Sév':>9}")
    print(f"{'─'*72}")
    for r in rows:
        if isinstance(r[1], (int, float)):
            print(f"{r[0]:<32} {r[1]:>8.1f}     {r[2]:>8.1f} {r[3]:>6.1f}% {r[4]:>9}")
        else:
            print(f"{r[0]:<32} {str(r[1]):<20} {str(r[2]):>8}          {r[4]:>9}")
    print(f"{'─'*72}")
    crit = sum(1 for r in rows if r[4] == "critical")
    warn = sum(1 for r in rows if r[4] == "warning")
    total = len(ing)
    print(f"Critical: {crit} | Warning: {warn} | Total issues: {len(rows)} / {total} ingrédients")

    # ── data_truth_score agrégé ── V13 ──────────────────────────────────
    truth_scores = []
    for name_t, data_t in ing.items():
        for iss in validate_internal(name_t, data_t):
            if iss.get("type") == "_data_truth_score":
                truth_scores.append(iss["score"])
    if truth_scores:
        avg_truth  = round(sum(truth_scores) / len(truth_scores), 4)
        low_truth  = sum(1 for s in truth_scores if s < 0.85)
        print(f"data_truth_score  : {avg_truth:.4f} avg | {low_truth} ingrédients < 0.85")

    # ── v6 : couverture des blocs structurels ── v14 ─────────────────────
    schema_ver = db.get("schema_version", "")
    if schema_ver >= SCHEMA_V6:
        n6_count    = sum(1 for d in ing.values()
                          if d.get("variants", {}).get("default", {}).get("nutrients_v6"))
        state_count = sum(1 for d in ing.values()
                          if d.get("variants", {}).get("default", {}).get("state"))
        dp_count    = sum(1 for d in ing.values()
                          if d.get("variants", {}).get("default", {}).get("diet_profile"))
        sm_count    = sum(1 for d in ing.values()
                          if d.get("variants", {}).get("default", {}).get("_source_meta"))
        print(f"\n  Blocs v6 (sur {len(ing)} ingrédients) :")
        print(f"    nutrients_v6   : {n6_count:>5}  ({n6_count/max(len(ing),1)*100:.1f}%)")
        print(f"    state          : {state_count:>5}  ({state_count/max(len(ing),1)*100:.1f}%)")
        print(f"    diet_profile   : {dp_count:>5}  ({dp_count/max(len(ing),1)*100:.1f}%)")
        print(f"    _source_meta   : {sm_count:>5}  ({sm_count/max(len(ing),1)*100:.1f}%)")
    # ── fin v6 ────────────────────────────────────────────────────────────

    print("\nRègles vérifiées : energy_mismatch · fiber/sugar>carbs · sat_fat>fat")
    print("                   macro_sum>105 · limites absolues · champs manquants")
    print("                   bio: lait/fiber+starch · végétaux/cholestérol · noix/sodium")
    print("                   lipid_sub_incoherence · omega_gt_poly · data_truth_score  ← V13")
    print("                   nutrients_v6/state/diet_profile/source_meta coverage     ← v14")
    print("Note : vinaigres/alcools/polyols/algues exclus de la vérification Atwater.")
    print(f"       FIBER_GT_CARBS_EXCEPTIONS : {len(FIBER_GT_CARBS_EXCEPTIONS)} ingrédients exemptés.")
    print(f"       SAT_GT_FAT_EXCEPTIONS     : {len(SAT_GT_FAT_EXCEPTIONS)} ingrédients exemptés (fusion multi-source).")
    print(f"       SUGAR_GT_CARBS_EXCEPTIONS : {len(SUGAR_GT_CARBS_EXCEPTIONS)} ingrédients exemptés (alias/schema available).")
    print(f"       CATEGORY_INGREDIENTS      : {len(CATEGORY_INGREDIENTS)} types ombrelle exclus du missing_field.")
    print(f"       PARTIAL_DATA_OK           : {len(PARTIAL_DATA_OK)} ingrédients à traces nulles exclus.")
    print("Pour validation croisée CIQUAL/USDA → python validator_v12.py\n")


def diff_corrections():
    """
    Compare la DB originale et la version corrigée.
    Affiche chaque champ modifié avec l'ancienne et la nouvelle valeur.
    """
    corrected_path = OUTPUT_DIR / "nutrition_database_corrected.json"
    if not corrected_path.exists():
        print("❌ Lancer d'abord : python validator_v12.py --apply")
        return

    with open(resolve_db_file(), encoding="utf-8") as f:
        original = json.load(f)["ingredients"]
    with open(corrected_path, encoding="utf-8") as f:
        corrected = json.load(f)["ingredients"]

    diffs = []
    for name in corrected:
        if name not in original:
            continue
        orig_data = original[name]
        corr_data = corrected[name]
        for field, new_val in corr_data.items():
            if field.startswith("_"):
                continue
            old_val = orig_data.get(field)
            if old_val != new_val and old_val is not None:
                meta = corr_data.get(f"_correction_{field}", {})
                diffs.append({
                    "ingredient": name,
                    "field":      field,
                    "old":        old_val,
                    "new":        new_val,
                    "source":     meta.get("source", "?"),
                    "delta_pct":  meta.get("delta_pct", "?"),
                })

    if not diffs:
        print("✔ Aucune différence détectée entre la DB originale et la version corrigée.")
        return

    print(f"\n{'─'*80}")
    print(f"{'Ingrédient':<28} {'Champ':<14} {'Avant':>10} {'Après':>10} {'Source':<10} {'Δ':>6}")
    print(f"{'─'*80}")
    for d in diffs:
        print(
            f"{d['ingredient']:<28} {d['field']:<14} "
            f"{str(d['old']):>10} {str(d['new']):>10} "
            f"{d['source']:<10} {str(d['delta_pct']):>6}"
        )
    print(f"{'─'*80}")
    print(f"  {len(diffs)} modification(s) au total.\n")


def clean_correction_fields():
    """
    Retire tous les champs _correction_* de la DB corrigée.
    Ces métadonnées de traçabilité ne doivent pas partir en production.
    Écrit outputs/nutrition_database_corrected_clean.json
    """
    corrected_path = OUTPUT_DIR / "nutrition_database_corrected.json"
    if not corrected_path.exists():
        print("❌ Lancer d'abord : python validator_v12.py --apply")
        return

    with open(corrected_path, encoding="utf-8") as f:
        db = json.load(f)

    cleaned = 0
    for name, data in db.get("ingredients", {}).items():
        keys_to_remove = [k for k in data if k.startswith("_correction_")]
        for k in keys_to_remove:
            del data[k]
            cleaned += 1

    out = OUTPUT_DIR / "nutrition_database_corrected_clean.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)

    print(f"✔ {cleaned} champ(s) _correction_* supprimés.")
    print(f"  → {out}\n")


# ══════════════════════════════════════════════════════════════════════════
# 11. ENTRYPOINT
# ══════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    import argparse as _ap

    # Migration V15 : argparse remplace le parsing manuel ad-hoc.
    # L'ancien --input=<path> (avec =) fonctionnait ; --input <path> (sans =)
    # retournait None silencieusement → patched chargé à la place.
    # argparse gère les deux formes nativement.
    _parser = _ap.ArgumentParser(
        description="Nutrition Validator V11 — ALIM",
        formatter_class=_ap.RawDescriptionHelpFormatter,
        epilog=(
            "Modes :\n"
            "  (défaut)      Validation croisée CIQUAL/USDA → correction_proposals.json\n"
            "  --audit       Audit interne rapide (sans sources externes)\n"
            "  --apply       Applique correction_proposals.json → nutrition_database_corrected.json\n"
            "  --diff        Compare original vs corrigé\n"
            "  --clean       Retire les champs _correction_* de la DB corrigée\n"
            "  --enrich      Enrichit ingredients_dictionary.json (alim_nom_sci, name_en)\n"
        )
    )

    # Mode exclusif (un seul à la fois)
    _mode = _parser.add_mutually_exclusive_group()
    _mode.add_argument("--audit",  action="store_true",
                       help="Audit interne sans sources externes")
    _mode.add_argument("--apply",  action="store_true",
                       help="Applique correction_proposals.json")
    _mode.add_argument("--diff",   action="store_true",
                       help="Compare original vs version corrigée")
    _mode.add_argument("--clean",  action="store_true",
                       help="Supprime les champs _correction_* de la DB corrigée")
    _mode.add_argument("--enrich", action="store_true",
                       help="Enrichit ingredients_dictionary.json")

    # Options communes
    _parser.add_argument(
        "--input", default=None, metavar="PATH",
        help=(
            "Fichier source nutrition (absolu ou relatif à la racine projet). "
            "Priorité : --input > nutrition_patched_v7.json > nutrition_corrected.json > nutrition_v2.json. "
            "Exemples : --input nutrition_corrected.json  |  --input outputs/nutrition_patched_v7.json"
        )
    )
    _parser.add_argument(
        "--severity", default="warning",
        choices=["ok", "warning", "critical"],
        help="Sévérité minimale pour --apply (défaut : warning)"
    )
    _parser.add_argument(
        "--score", type=float, default=0.90,
        help="Score minimal pour --apply (défaut : 0.90)"
    )

    _pargs = _parser.parse_args()

    # Résolution du fichier source
    _db_file = None
    if _pargs.input:
        try:
            _db_file = resolve_db_file(_pargs.input)
            print(f"  Source : {_db_file.name}")
        except FileNotFoundError as e:
            print(f"❌ {e}")
            sys.exit(1)

    # Dispatch
    if _pargs.audit:
        quick_audit(db_file=_db_file)
    elif _pargs.apply:
        apply_corrections(
            min_severity=_pargs.severity,
            min_score=_pargs.score,
            db_file=_db_file
        )
    elif _pargs.diff:
        diff_corrections()
    elif _pargs.clean:
        clean_correction_fields()
    elif _pargs.enrich:
        enrich_dictionary()
    else:
        run_validation(db_file=_db_file)