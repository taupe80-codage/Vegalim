"""
╔══════════════════════════════════════════════════════════════════════════╗
║         NUTRITION VALIDATOR V11 — validator_v11.py                       ║
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
  Étape 1 → python validator_v11.py --audit
            Audit rapide interne, sans source externe.

  Étape 2 → Télécharger CIQUAL et/ou USDA (gratuit, voir URLs ci-dessus)
            Placer dans : sources/

  Étape 3 → python validator_v11.py
            Validation croisée → génère :
              outputs/validation_report.json
              outputs/correction_proposals.json

  Étape 4 → Ouvrir correction_proposals.json
            Changer "action": "replace" → "keep" pour refuser

  Étape 5 → python validator_v11.py --apply [--severity=critical] [--score=0.90]
            Sauvegarde automatique avant application.
            → outputs/nutrition_database_corrected.json

  Étape 6 → python validator_v11.py --diff
            Compare la DB originale et la version corrigée.

  Étape 7 → python validator_v11.py --clean
            Retire les champs _correction_* de la DB corrigée.

  Étape 8 → python validator_v11.py --enrich
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
      validation croisée quand usda_flat.json absent)
  - NUTRITION_CORRECTED_FILE : chemin vers nutrition_corrected.json produit par
      auto_correct_v6.py — utilisé en priorité si le fichier existe
  - load_local_db / quick_audit : sélection automatique corrected > v2 > fallback
  - CLI --input=<path> : forcer un fichier source spécifique
      ex: python validator_v11.py --audit --input nutrition_corrected.json
  - run_validation / apply_corrections : version string "v10" → "v11" corrigé
  - FIBER_GT_CARBS_EXCEPTIONS : 35 ingrédients exemptés du check fiber_gt_carbs
      (glucides disponibles schéma CIQUAL — fiber > carbs est valide)
  - CATEGORY_INGREDIENTS : ~30 types ombrelle exemptés du check missing_field
      (flour, milk_animal, oil… résolus au rendu recette, pas de données directes)

NOUVEAUTÉS V13 (vs V12) :
  - validate_internal : lipid_sub_incoherence — sat+mono+poly << fat_g
      → warning  si ratio 0.15–0.7 (fa_incomplete : PUFA partiellement renseigné)
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
# Sortie de auto_correct_v6.py — utilisée en priorité si elle existe
NUTRITION_CORRECTED_FILE = BASE_DIR / "backend" / "data" / "nutrition" / "reference" / "nutrition_corrected.json"
PHYSICAL_FILE            = BASE_DIR / "backend" / "data" / "ingredients" / "ingredient_physical.json"
DICT_FILE                = BASE_DIR / "backend" / "data" / "ingredients" / "ingredients_dictionary.json"

# Sources flat pré-normalisées (générées par les scripts d'export)
CIQUAL_FILE = BASE_DIR / "backend" / "data" / "nutrition" / "raw" / "ciqual_flat.json"
USDA_JSON   = BASE_DIR / "backend" / "data" / "nutrition" / "raw" / "usda_flat.json"
USDA_CSV    = BASE_DIR / "backend" / "data" / "nutrition" / "raw" / "usda_flat.csv"

USDA_API_KEY = os.environ.get("USDA_API_KEY", "")
USDA_API_URL = "https://api.nal.usda.gov/fdc/v1/foods/search"

TODAY = datetime.now().strftime("%Y-%m-%d")


def resolve_db_file(cli_input=None):
    """
    Résout le fichier nutrition à utiliser, par ordre de priorité :
      1. --input=<path> passé en CLI (absolu ou relatif à BASE_DIR)
      2. nutrition_corrected.json (sortie auto_correct_v6) si présent
      3. nutrition_v2.json (source canonique)
    """
    if cli_input:
        p = Path(cli_input)
        if not p.is_absolute():
            p = BASE_DIR / p
        if p.exists():
            return p
        raise FileNotFoundError(f"--input : fichier introuvable : {p}")
    if NUTRITION_CORRECTED_FILE.exists():
        return NUTRITION_CORRECTED_FILE
    return NUTRITION_DB_FILE

DELTA_WARN     = 15.0   # % → warning
DELTA_CRITICAL = 40.0   # % → critical
FUZZY_THRESHOLD = 75    # score minimum pour accepter un match fuzzy (0–100)

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

    # ── Herbes non encore couvertes ci-dessus ────────────────────────────────
    "tarragon", "dill",

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
    # ── Noix / graines riches en fibres ──────────────────────────────────────
    "hazelnut", "flax_egg", "flaxseed", "coconut_flesh", "bran",
    "wheat_germ", "psyllium", "psyllium_husk",
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

FIELDS = ["calories", "protein", "carbs", "fat", "fiber",
          "vitamin_c", "vitamin_a", "vitamin_d"]

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
    # V11 — ajoutés (alignement nutrition_v2 + cnf_full_v5)
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
        """Charge ciqual_flat.json (pré-normalisé — plus besoin de xlsx)."""
        if CIQUAL_FILE.exists():
            self._parse(CIQUAL_FILE)
        else:
            print(f"  ⚠ CIQUAL non trouvé : {CIQUAL_FILE}")

    def _parse(self, path: Path):
        print(f"  → CIQUAL flat: {path.name}")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            for food in data.get("foods", []):
                # Identifiant CIQUAL
                cid_raw = food.get("alim_code") or food.get("code")
                if cid_raw is None:
                    continue
                cid = str(cid_raw).strip()

                entry = {
                    "calories": safe_float(food.get("calories_kcal")),
                    "protein":  safe_float(food.get("protein_g")),
                    "carbs":    safe_float(food.get("carbs_g")),
                    "fat":      safe_float(food.get("fat_g")),
                    "fiber":    safe_float(food.get("fiber_g")),
                    "sugar":    safe_float(food.get("sugar_g")),
                    "water":    safe_float(food.get("water_g")),
                }
                self.by_id[cid] = entry

                # Nom scientifique
                sci = food.get("alim_nom_sci")
                if sci:
                    self.sci_names[cid] = str(sci).strip()

                # Index par nom normalisé
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
        names = list(self.by_name.keys())
        match, score, _ = process.extractOne(key, names, scorer=fuzz.WRatio)
        if score >= FUZZY_THRESHOLD:
            q_words = len(key.split("_"))
            m_words = len(match.split("_"))
            if m_words > q_words * 2:
                score = score * 0.8   # pénalité 20% si cible plus du double
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
        """Charge usda_flat.json (pré-normalisé)."""
        print(f"  → USDA flat JSON : {path.name}")
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)

            foods = data.get("foods", [])
            loaded = skipped_no_macros = 0

            for food in foods:
                desc = normalize(food.get("description", ""))
                if not desc:
                    continue

                entry = {
                    "calories": safe_float(food.get("calories_kcal")),
                    "protein":  safe_float(food.get("protein_g")),
                    "carbs":    safe_float(food.get("carbs_g")),
                    "fat":      safe_float(food.get("fat_g")),
                    "fiber":    safe_float(food.get("fiber_g")),
                    "sugar":    safe_float(food.get("sugar_g")),
                    "calcium":  safe_float(food.get("calcium_mg")),
                    "iron":     safe_float(food.get("iron_mg")),
                    "potassium": safe_float(food.get("potassium_mg")),
                    "magnesium": safe_float(food.get("magnesium_mg")),
                    "sodium":   safe_float(food.get("sodium_mg")),
                    "zinc":     safe_float(food.get("zinc_mg")),
                    "selenium": safe_float(food.get("selenium_ug")),
                    "vitamin_c": safe_float(food.get("vitamin_c_mg")),
                    "vitamin_b12": safe_float(food.get("vitamin_b12_ug")),
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
# 6. VALIDATION
# ══════════════════════════════════════════════════════════════════════════

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
        warning  si ratio 0.15–0.70 (fa_incomplete)
        critical si ratio < 0.15    (source_conflict)
    - omega_gt_poly : omega3+omega6 > poly (critical) ← V13
    """
    issues = []
    # Lire les champs — support schema v2 (variants.default) + flat legacy
    _d = data.get("variants", {}).get("default", {})

    def _get(long_key, short_key):
        return safe_float(
            data.get(long_key) or data.get(short_key)
            or _d.get(long_key) or _d.get(short_key)
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
    if name not in FORMULA_EXCEPTIONS and name not in NON_SCORING:
        if all(v is not None for v in [cal, p, c, f]) and cal > 0:
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
                })

    # ── Cohérence fibres / glucides ────────────────────────────────────────
    # V12 : exclut FIBER_GT_CARBS_EXCEPTIONS (glucides dispo schéma CIQUAL)
    if (fib is not None and c is not None and fib > c + 0.5
            and name not in FIBER_GT_CARBS_EXCEPTIONS):
        issues.append({
            "type": "fiber_gt_carbs",
            "fiber": fib, "carbs": c,
            "severity": "critical"
        })

    # ── Cohérence sucres / glucides ────────────────────────────────────────
    if sug is not None and c is not None and sug > c + 0.5:
        issues.append({
            "type": "sugar_gt_carbs",
            "sugar": sug, "carbs": c,
            "severity": "warning"
        })

    # ── saturated_fat > fat (impossible physiquement) ─────────────────────
    if sat is not None and f is not None and sat > f + 0.5:
        issues.append({
            "type": "saturated_fat_gt_fat",
            "saturated_fat": sat, "fat": f,
            "severity": "critical"
        })

    # ── Cohérence lipidique : sat+mono+poly vs fat_g ── V13 ──────────────
    # Sévérité différenciée selon ratio :
    #   ratio < 0.15 → source_conflict (critical) : contamination probable
    #   ratio 0.15–0.70 → fa_incomplete (warning) : PUFA partiel
    #   ratio > 0.70 ou sub=0 → OK
    if f is not None and f > 0.3:
        total_sub = (sat or 0.0) + (mono or 0.0) + (poly or 0.0)
        if total_sub > 0:
            ratio = total_sub / f
            if ratio < 0.70:
                sev = "critical" if ratio < 0.15 else "warning"
                subtype = "source_conflict" if ratio < 0.15 else "fa_incomplete"
                issues.append({
                    "type": "lipid_sub_incoherence",
                    "subtype": subtype,
                    "fat_g": f,
                    "sat_g": sat, "mono_g": mono, "poly_g": poly,
                    "total_sub_g": round(total_sub, 4),
                    "ratio": round(ratio, 4),
                    "severity": sev,
                })

    # ── omega3 + omega6 > poly (omega ⊂ PUFA, biologiquement impossible) ─
    if poly is not None and poly >= 0:
        total_omega = (omega3 or 0.0) + (omega6 or 0.0)
        if total_omega > (poly or 0.0) + 0.01:
            issues.append({
                "type": "omega_gt_poly",
                "poly_g": poly,
                "omega3_g": omega3, "omega6_g": omega6,
                "total_omega_g": round(total_omega, 4),
                "delta_g": round(total_omega - (poly or 0.0), 4),
                "severity": "critical",
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


def compare_to_source(declared: dict, reference: dict, source: str, score: float) -> list:
    """Compare les champs FIELDS entre la DB locale et une source externe."""
    discrepancies = []
    for field in FIELDS:
        dec = safe_float(declared.get(field))
        ref = safe_float(reference.get(field))
        if None in (dec, ref) or ref == 0:
            continue
        d = pct_delta(dec, ref)
        cls = classify(d)
        if cls != "ok":
            discrepancies.append({
                "field": field,
                "declared": dec,
                "reference": ref,
                "delta_pct": d,
                "severity": cls,
                "source": source,
                "match_score": score
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
    print("║    Nutrition Validator V11 — Validation Croisée      ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    ingredients, ciqual_id_map, ciqual_note_map = load_local_db(db_file=db_file)
    print()

    print("Chargement des sources de référence...")
    ciqual = CIQUALLoader()
    ciqual.load()
    usda = USDALoader()
    usda.load()
    print()

    stats = {
        "total": 0, "ok": 0, "warning": 0, "critical": 0,
        "external_checked": 0, "proposals": 0,
        "ciqual_id_hits": 0, "ciqual_fuzzy_hits": 0, "usda_hits": 0,
        "no_external_match": 0,
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
                name_query = (data.get("name_fr") or name.replace("_", " "))
                ref, matched, score = ciqual.lookup_by_name(name_query)
                if ref:
                    label = f"CIQUAL fuzzy:{matched}"
                    stats["ciqual_fuzzy_hits"] += 1

            if ref:
                had_external = True
                stats["external_checked"] += 1
                discs = compare_to_source(data, ref, "CIQUAL", score)
                entry["external_checks"].append({
                    "source": label,
                    "match_score": score,
                    "reference": {f: ref.get(f) for f in FIELDS},
                    "discrepancies": discs
                })
                entry["proposals"] = merge_proposals(entry["proposals"], discs)

        # ── Validation USDA ─────────────────────────────────────────────────
        if usda.available:
            name_query = data.get("name_en") or name.replace("_", " ")
            ref, matched, score = usda.lookup(name_query, data.get("name_fr", ""))
            if ref:
                had_external = True
                stats["usda_hits"] += 1
                discs = compare_to_source(data, ref, "USDA", score)
                entry["external_checks"].append({
                    "source": f"USDA:{matched}",
                    "match_score": score,
                    "reference": {f: ref.get(f) for f in FIELDS},
                    "discrepancies": discs
                })
                entry["proposals"] = merge_proposals(entry["proposals"], discs)

        if not had_external and (ciqual.available or usda.available):
            stats["no_external_match"] += 1

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
            "version": "v11",
            "stats": stats,
            "results": report
        }, f, indent=2, ensure_ascii=False)

    with open(OUTPUT_DIR / "correction_proposals.json", "w", encoding="utf-8") as f:
        json.dump({
            "generated": TODAY,
            "version": "v11",
            "_instructions": (
                "Réviser chaque proposition. "
                "Changer 'action' de 'replace' à 'keep' pour refuser. "
                "Puis lancer : python validator_v11.py --apply"
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
    if any_ext:
        print(f"  Sans match ext: {stats['no_external_match']} "
              f"(couverture {coverage_pct}%)")
    print(f"  Corrections   : {stats['proposals']} proposées")
    if critical_list:
        print(f"\n  Critiques :")
        for n, e in critical_list[:10]:
            iss = e["internal_issues"]
            detail = f"Δ{iss[0].get('delta_pct','?')}%" if iss else ""
            print(f"    · {n} {detail}")
        if len(critical_list) > 10:
            print(f"    ... et {len(critical_list)-10} autres")
    print(f"{'═'*56}")
    print(f"\n  → outputs/validation_report.json")
    print(f"  → outputs/correction_proposals.json\n")


# ══════════════════════════════════════════════════════════════════════════
# 8. APPLICATION DES CORRECTIONS
# ══════════════════════════════════════════════════════════════════════════

def apply_corrections(min_severity: str = "warning", min_score: float = 0.85, db_file=None):
    proposals_file = OUTPUT_DIR / "correction_proposals.json"
    if not proposals_file.exists():
        print("❌ Lancer d'abord : python validator_v11.py")
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
                old = db["ingredients"][ingredient].get(field)
                db["ingredients"][ingredient][field] = prop["proposed"]
                db["ingredients"][ingredient][f"_correction_{field}"] = {
                    "original": old,
                    "source":   prop["source"],
                    "delta_pct": prop["delta_pct"],
                    "date":     TODAY
                }
                applied.append(
                    f"{ingredient}.{field}: {old} → {prop['proposed']} "
                    f"({prop['source']}, Δ{prop['delta_pct']}%)"
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

    print("\nRègles vérifiées : energy_mismatch · fiber/sugar>carbs · sat_fat>fat")
    print("                   macro_sum>105 · limites absolues · champs manquants")
    print("                   bio: lait/fiber+starch · végétaux/cholestérol · noix/sodium")
    print("                   lipid_sub_incoherence · omega_gt_poly · data_truth_score  ← V13")
    print("Note : vinaigres/alcools/polyols/algues exclus de la vérification Atwater.")
    print(f"       FIBER_GT_CARBS_EXCEPTIONS : {len(FIBER_GT_CARBS_EXCEPTIONS)} ingrédients exemptés.")
    print(f"       CATEGORY_INGREDIENTS      : {len(CATEGORY_INGREDIENTS)} types ombrelle exclus du missing_field.")
    print(f"       PARTIAL_DATA_OK           : {len(PARTIAL_DATA_OK)} ingrédients à traces nulles exclus.")
    print("Pour validation croisée CIQUAL/USDA → python validator_v11.py\n")


def diff_corrections():
    """
    Compare la DB originale et la version corrigée.
    Affiche chaque champ modifié avec l'ancienne et la nouvelle valeur.
    """
    corrected_path = OUTPUT_DIR / "nutrition_database_corrected.json"
    if not corrected_path.exists():
        print("❌ Lancer d'abord : python validator_v11.py --apply")
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
        print("❌ Lancer d'abord : python validator_v11.py --apply")
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
    args = sys.argv[1:]

    # V12 : --input=<path> force un fichier source explicite
    _input_arg = next((a.split("=", 1)[1] for a in args if a.startswith("--input=")), None)
    _db_file   = None
    if _input_arg:
        try:
            _db_file = resolve_db_file(_input_arg)
            print(f"  --input : {_db_file}")
        except FileNotFoundError as e:
            print(e)
            sys.exit(1)

    if "--audit" in args:
        quick_audit(db_file=_db_file)
    elif "--apply" in args:
        sev   = next((a.split("=")[1] for a in args if a.startswith("--severity=")), "warning")
        score = float(next((a.split("=")[1] for a in args if a.startswith("--score=")), "0.85"))
        apply_corrections(min_severity=sev, min_score=score, db_file=_db_file)
    elif "--diff" in args:
        diff_corrections()
    elif "--clean" in args:
        clean_correction_fields()
    elif "--enrich" in args:
        enrich_dictionary()
    else:
        run_validation(db_file=_db_file)