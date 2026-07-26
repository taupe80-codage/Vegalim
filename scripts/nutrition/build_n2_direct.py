#!/usr/bin/env python3
"""
build_n2_direct.py  —  Reconstruction déterministe de nutrition_v2
===================================================================
Version SANS flat files : charge directement les sources officielles brutes.

Sources :
  CIQUAL  : Table_Ciqual_2025_FR_2025_11_03.xlsx  (alim_code → nutriments)
  USDA    : FoodData_Central_foundation_food_json_2025-12-18.json (fdcId → nutriments)
  CNF     : cnf/FOOD_NAME.csv + NUTRIENT_AMOUNT.csv (FoodCode → nutriments)

Usage :
  python build_n2_direct.py               # écrit nutrition_v2_rebuilt.json
  python build_n2_direct.py --promote     # écrase nutrition_v2.json
  python build_n2_direct.py --dry-run     # rapport sans écriture
"""
import argparse, csv, hashlib, json, re, sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# ── Chemins ────────────────────────────────────────────────────────────────────
ROOT     = Path(__file__).parents[2]
DATA     = ROOT / 'backend/data'
V32_FILE = DATA / 'ingredients/ingredients_tree.json'
RAW_DIR  = DATA / 'nutrition/raw'
PROC_DIR = DATA / 'nutrition/processed'
OUTPUT_REBUILT  = PROC_DIR / 'nutrition_v2_rebuilt.json'
OUTPUT_N2       = PROC_DIR / 'nutrition_v2.json'
MANIFEST_FILE   = DATA / 'nutrition/logs/raw_sources_manifest.json'
SUPPLEMENTS_FILE = DATA / 'nutrition/reference/nutrition_manual_supplements.json'

SOURCE_PRIORITY = {'CIQUAL': 0, 'USDA': 1, 'CNF': 2}

# ══════════════════════════════════════════════════════════════════════════════
# MAPPING CIQUAL : colonne xlsx (normalisée) → champ n2
# Les colonnes CIQUAL ont des noms longs avec \n — on les normalise en slug.
# ══════════════════════════════════════════════════════════════════════════════
def _ciq_slug(s: str) -> str:
    """Normalise un nom de colonne CIQUAL en clé courte."""
    s = s.lower().replace('\n', ' ').strip()
    # Remplacements ciblés avant slug général
    s = s.replace('alpha-tocophérol', 'vit_e')
    s = s.replace('tocophérol', 'vit_e')
    replacements = {
        'é':'e','è':'e','ê':'e','à':'a','â':'a','ù':'u',
        'û':'u','î':'i','ï':'i','ô':'o','ç':'c','œ':'oe',
    }
    for fr, en in replacements.items():
        s = s.replace(fr, en)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_')

# Mapping slug_colonne_ciqual → champ n2
CIQUAL_COL_MAP: dict[str, str] = {
    # Énergie
    'energie_reglement_ue_n_1169_2011_kcal_100_g':     'calories_kcal',
    'energie_reglement_ue_n_1169_2011_kj_100_g':       'energy_kj',
    'energie_n_x_facteur_jones_avec_fibres_kj_100_g':  'energy_kj_jones',
    'energie_n_x_facteur_jones_avec_fibres_kcal_100_g':'energy_kcal_jones',
    # Macros
    'eau_g_100_g':                                     'water_g',
    'proteines_n_x_facteur_de_jones_g_100_g':          'protein_g',
    'proteines_n_x_6_25_g_100_g':                      'protein_n625_g',
    'glucides_g_100_g':                                'carbs_g',
    'lipides_g_100_g':                                 'fat_g',
    'sucres_g_100_g':                                  'sugar_g',
    'fructose_g_100_g':                                'fructose_g',
    'galactose_g_100_g':                               'galactose_g',
    'glucose_g_100_g':                                 'glucose_g',
    'lactose_g_100_g':                                 'lactose_g',
    'maltose_g_100_g':                                 'maltose_g',
    'saccharose_g_100_g':                              'saccharose_g',
    'amidon_g_100_g':                                  'starch_g',
    'fibres_alimentaires_g_100_g':                     'fiber_g',
    'polyols_totaux_g_100_g':                          'polyols_g',
    'cendres_g_100_g':                                 'ash_g',
    'alcool_ethanol_g_100_g':                          'alcohol_g',
    'acides_organiques_g_100_g':                       'organic_acids_g',
    # Lipides détaillés
    'ag_satures_g_100_g':                              'fa_saturated_g',
    'ag_monoinsatures_g_100_g':                        'fa_mufa_g',
    'ag_polyinsatures_g_100_g':                        'fa_pufa_g',
    'ag_4_0_butyrique_g_100_g':                        'fa_4_0_g',
    'ag_6_0_caproique_g_100_g':                        'fa_6_0_g',
    'ag_8_0_caprylique_g_100_g':                       'fa_8_0_g',
    'ag_10_0_caprique_g_100_g':                        'fa_10_0_g',
    'ag_12_0_laurique_g_100_g':                        'fa_12_0_g',
    'ag_14_0_myristique_g_100_g':                      'fa_14_0_g',
    'ag_16_0_palmitique_g_100_g':                      'fa_16_0_g',
    'ag_18_0_stearique_g_100_g':                       'fa_18_0_g',
    'ag_18_1_9c_n_9_oleique_g_100_g':                  'fa_18_1_oleic_g',
    'ag_18_2_9c_12c_n_6_linoleique_g_100_g':           'fa_18_2_linoleic_g',
    'ag_18_3_c9_c12_c15_n_3_alpha_linolenique_g_100_g':'fa_18_3_ala_g',
    'ag_20_4_5c_8c_11c_14c_n_6_arachidonique_g_100_g': 'fa_20_4_ara_g',
    'ag_20_5_5c_8c_11c_14c_17c_n_3_epa_g_100_g':       'fa_20_5_epa_g',
    'ag_22_6_4c_7c_10c_13c_16c_19c_n_3_dha_g_100_g':   'fa_22_6_dha_g',
    'cholesterol_mg_100_g':                            'cholesterol_mg',
    'sel_chlorure_de_sodium_g_100_g':                  'salt_g',
    # Minéraux
    'calcium_mg_100_g':    'calcium_mg',
    'chlorure_mg_100_g':   'chloride_mg',
    'cuivre_mg_100_g':     'copper_mg',
    'fer_mg_100_g':        'iron_mg',
    'iode_g_100_g':        'iodine_ug',   # µg noté µg dans xlsx → mapper
    'magnesium_mg_100_g':  'magnesium_mg',
    'manganese_mg_100_g':  'manganese_mg',
    'phosphore_mg_100_g':  'phosphorus_mg',
    'potassium_mg_100_g':  'potassium_mg',
    'selenium_g_100_g':    'selenium_ug',  # idem µg
    'sodium_mg_100_g':     'sodium_mg',
    'zinc_mg_100_g':       'zinc_mg',
    # Vitamines
    'activite_vitaminique_a_equivalents_retinol_g_100_g': 'vitamin_a_rae_ug',
    'retinol_g_100_g':                                    'retinol_ug',
    'beta_carotene_g_100_g':                              'beta_carotene_ug',
    'vitamine_d_g_100_g':                                 'vitamin_d_ug',
    'vitamine_d2_ergocalciferol_g_100_g':                 'vitamin_d2_ug',
    'vitamine_d3_cholecalciferol_g_100_g':                'vitamin_d3_ug',
    'alpha_tocopherol_vitamine_e_mg_100_g':               'alpha_tocopherol_mg',
    'vit_e_mg_100_g':                                     'vitamin_e_mg',
    'vitamine_k1_g_100_g':                                'vitamin_k1_ug',
    'vitamine_k2_g_100_g':                                'vitamin_k2_ug',
    'vitamine_c_mg_100_g':                                'vitamin_c_mg',
    'vitamine_b1_ou_thiamine_mg_100_g':                   'vitamin_b1_mg',
    'vitamine_b2_ou_riboflavine_mg_100_g':                'vitamin_b2_mg',
    'vitamine_b3_ou_pp_ou_niacine_mg_100_g':              'vitamin_b3_mg',
    'vitamine_b5_ou_acide_pantothenique_mg_100_g':        'vitamin_b5_mg',
    'vitamine_b6_mg_100_g':                               'vitamin_b6_mg',
    'vitamine_b9_ou_folates_totaux_equivalents_folates_alimentaires_dfe_g_100_g': 'folate_dfe_ug',
    'vitamine_b9_ou_folates_totaux_g_100_g':              'folate_ug',
    'folates_intrinseques_g_100_g':                       'folate_intrinsic_ug',
    'acide_folique_enrichissement_g_100_g':               'folic_acid_ug',
    'vitamine_b12_g_100_g':                               'vitamin_b12_ug',
}

# Mapping n2_field → calories_kcal / protein_g / ...  (schéma final n2)
FIELD_MAP_N2 = {
    'calories_kcal': 'calories_kcal', 'energy_kj': None,
    'water_g': None, 'protein_g': 'protein_g', 'carbs_g': 'carbs_g',
    'fat_g': 'fat_g', 'fiber_g': 'fiber_g', 'sugar_g': 'sugar_g',
    'starch_g': 'starch_g', 'alcohol_g': 'alcohol_g',
    'polyols_g': 'polyols_g', 'organic_acids_g': 'organic_acids_g',
    'fa_saturated_g': 'saturated_fat_g', 'fa_mufa_g': 'monounsaturated_fat_g',
    'fa_pufa_g': 'polyunsaturated_fat_g', 'fa_18_3_ala_g': 'omega3_ala_g',
    'fa_20_5_epa_g': 'omega3_epa_g', 'fa_22_6_dha_g': 'omega3_dha_g',
    'fa_18_2_linoleic_g': 'omega6_g', 'cholesterol_mg': 'cholesterol_mg',
    'calcium_mg': 'calcium_mg', 'iron_mg': 'iron_mg',
    'magnesium_mg': 'magnesium_mg', 'phosphorus_mg': 'phosphorus_mg',
    'potassium_mg': 'potassium_mg', 'sodium_mg': 'sodium_mg',
    'zinc_mg': 'zinc_mg', 'copper_mg': 'copper_mg',
    'manganese_mg': 'manganese_mg', 'selenium_ug': 'selenium_ug',
    'iodine_ug': 'iodine_ug', 'vitamin_a_rae_ug': 'vitamin_a_ug',
    'beta_carotene_ug': 'beta_carotene_ug', 'vitamin_d_ug': 'vitamin_d_ug',
    'alpha_tocopherol_mg': 'vitamin_e_mg', 'vitamin_k1_ug': 'vitamin_k1_ug',
    'vitamin_k2_ug': 'vitamin_k2_ug', 'vitamin_c_mg': 'vitamin_c_mg',
    'vitamin_b1_mg': 'vitamin_b1_mg', 'vitamin_b2_mg': 'vitamin_b2_mg',
    'vitamin_b3_mg': 'vitamin_b3_mg', 'vitamin_b5_mg': 'vitamin_b5_mg',
    'vitamin_b6_mg': 'vitamin_b6_mg', 'folate_ug': 'folate_ug',
    'vitamin_b12_ug': 'vitamin_b12_ug',
}

# ══════════════════════════════════════════════════════════════════════════════
# AXES → variant_key  +  traduction FR → EN (clés et valeurs)
# ══════════════════════════════════════════════════════════════════════════════

# Clés d'axes FR → EN
AXES_EN: dict[str, str] = {
    'etat_cuisson':        'cooking_state',
    'forme':               'form',
    'partie':              'part',
    'traitement':          'treatment',
    'etat_thermique':      'thermal_state',
    'assaisonnement':      'seasoning',
    'conditionnement':     'packaging',
    'egouttage':           'draining',
    'teneur_MG':           'fat_content',
    'maturite':            'ripeness',
    'origine':             'origin',
    'milieu_conservation': 'storage_medium',
    'procede_cuisson':     'cooking_process',
}

# Ordre de priorité pour construire la variant_key (clés FR du tree)
AXES_PRIORITY = [
    'etat_cuisson', 'forme', 'partie', 'traitement',
    'etat_thermique', 'assaisonnement', 'conditionnement',
    'egouttage', 'teneur_MG', 'maturite', 'origine',
    'milieu_conservation', 'procede_cuisson',
]

# Valeurs FR → EN par axe (clés FR du tree)
AXES_VALUE_MAP: dict[str, dict[str, str]] = {
    'etat_cuisson': {
        'cru': 'raw', 'cuit': 'cooked', 'bouilli': 'boiled', 'frit': 'fried',
        'grillé': 'grilled', 'grillé à sec': 'dry_roasted', 'vapeur': 'steamed',
        'rôti': 'roasted', 'sauté': 'sauteed', 'précuit': 'precooked',
        'au four': 'baked', 'à cuire': 'to_cook', 'étouffée': 'braised',
    },
    'forme': {
        'entière': 'whole', 'entier': 'whole', 'moulue': 'ground', 'moulu': 'ground',
        'poudre': 'powder', 'beurre': 'butter', 'compote': 'puree', 'purée': 'puree',
        'concentré': 'concentrated', 'flocon': 'flaked', 'flocons': 'flakes',
        'concassé': 'cracked', 'tranche': 'sliced', 'tranché': 'sliced',
        'bloc': 'block', 'crème': 'cream', 'extrait': 'extract', 'jus': 'juice',
        'zeste': 'zest', 'confiture': 'jam', 'broyé': 'crushed', 'farine': 'flour',
        'huile': 'oil', 'lait': 'milk', 'pâte': 'paste', 'râpé': 'grated',
        'liquide': 'liquid', 'gelée': 'jelly', 'granulé': 'granulated',
        'comprimé': 'tablet', 'pastilles': 'lozenges', 'confit': 'candied',
        'croquant': 'crunchy', 'crème de fruit': 'fruit_cream', 'crémeux': 'creamy',
        'eau végétale': 'plant_water', 'fouetté': 'whipped',
        'grain court': 'short_grain', 'grain long': 'long_grain',
        'grain moyen': 'medium_grain', 'herbe fraîche': 'fresh_herb',
        'herbe séchée': 'dried_herb', 'paillettes': 'flakes',
        'petits morceaux': 'small_pieces', 'yaourt': 'yogurt',
        'émietté': 'crumbled', 'épice': 'spice',
    },
    'partie': {
        'graine': 'seed', 'graine entière': 'whole_seed', 'feuille': 'leaf',
        'racine': 'root', 'chair': 'flesh', 'chair sans peau': 'flesh_no_skin',
        'chair+peau': 'flesh_with_skin', 'peau': 'skin', 'fleur': 'flower',
        'gousse': 'pod', 'dénoyauté': 'pitted', 'pelure': 'peel',
        'avec graines': 'with_seeds', 'avec peau': 'with_skin', 'pelé': 'peeled',
        'pousse': 'sprout', 'pépins': 'seeds', 'sans graines': 'seedless',
        'sans peau': 'skinless', 'tige': 'stem', 'tubercule': 'tuber',
    },
    'traitement': {
        'fumé': 'smoked', 'fermenté': 'fermented', 'affiné': 'aged',
        'blanchi': 'blanched', 'allégé en gras': 'low_fat', 'salé': 'salted',
        'mariné': 'marinated', 'brut': 'raw', 'confit': 'candied',
        'demi-écrémé': 'semi_skimmed', 'distillé': 'distilled',
        'décaféiné': 'decaffeinated', 'décortiqué': 'hulled', 'enrichi': 'enriched',
        'faible en sodium': 'low_sodium', 'germé': 'sprouted',
        'gras ajouté': 'added_fat', 'instantané': 'instant', 'iodé': 'iodized',
        'nature': 'plain', 'non enrichi': 'unenriched', 'raffiné': 'refined',
        'réduit en lactose': 'lactose_reduced', 'réduit en sodium': 'sodium_reduced',
        'sans gluten': 'gluten_free', 'texturé': 'textured', 'vierge': 'virgin',
        'écrémé': 'skimmed', 'élevé en gras': 'high_fat', 'étuvé': 'parboiled',
    },
    'etat_thermique': {
        'séché': 'dried', 'frais': 'fresh', 'déshydraté': 'dehydrated',
        'réhydraté': 'rehydrated', 'UHT': 'uht', 'pasteurisé': 'pasteurized',
    },
    'assaisonnement': {
        'salé': 'salted', 'sucré': 'sweetened', 'sans sel': 'unsalted',
        'sans sucre': 'unsweetened', 'épicé': 'spiced', 'aromatisé': 'flavored',
        'nature': 'plain',
    },
    'conditionnement': {
        'conserve': 'canned', 'appertisé': 'canned', 'sous vide': 'vacuum',
        'lyophilisé': 'freeze_dried', 'surgelé': 'frozen', 'UHT': 'uht',
        'commercial': 'commercial', 'pasteurisé': 'pasteurized',
        'préemballé': 'pre_packaged', 'rayon frais': 'fresh_aisle',
        'sous pression': 'pressurized', 'tablette': 'tablet',
    },
    'egouttage': {
        "à l'huile": 'in_oil', 'au vinaigre': 'in_vinegar',
        'dans sirop': 'in_syrup', "dans l'eau": 'in_water', 'égoutté': 'drained',
    },
    'maturite':           {'mûr': 'ripe', 'vert': 'unripe', 'trop mûr': 'overripe'},
    'teneur_MG':          {},
    'origine':            {
        'végétal': 'plant', 'animal': 'animal',
        'vache': 'cow', 'chèvre': 'goat', 'brebis': 'sheep', 'bufflonne': 'buffalo',
    },
    'milieu_conservation': {
        "à l'huile": 'in_oil', 'au vinaigre': 'in_vinegar',
        'dans sirop': 'in_syrup', "dans l'eau": 'in_water',
    },
    'procede_cuisson':    {"à l'huile": 'in_oil', 'à sec': 'dry'},
}


def slug(s: str) -> str:
    s = (s or '').lower().strip()
    s = re.sub(r"['\u2019\u2018]", '', s)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_')


def translate_axes(axes_fr: dict) -> dict:
    """Traduit clés et valeurs d'un dict d'axes FR → EN.

    - Clé FR inconnue : conservée telle quelle.
    - Valeur list (bug tree sur traitement) : jointe puis slugifiée.
    - Valeur FR inconnue dans le mapping : slugifiée en fallback.
    - teneur_MG : valeurs textuelles (écrémé/allégé/entier) traduites en EN;
      valeurs numériques conservées brutes.
    """
    out: dict = {}
    for k_fr, v_raw in (axes_fr or {}).items():
        k_en = AXES_EN.get(k_fr, k_fr)
        if isinstance(v_raw, list):
            v_str = slug('_'.join(str(x) for x in v_raw))
            out[k_en] = v_str
        elif k_fr == 'teneur_MG':
            _TEXT_MG = {'écrémé': 'skimmed', 'allégé': 'light', 'entier': 'whole'}
            v_str = str(v_raw).strip()
            out[k_en] = _TEXT_MG.get(v_str, v_str)
        else:
            v_str = str(v_raw).strip()
            out[k_en] = AXES_VALUE_MAP.get(k_fr, {}).get(v_str) or slug(v_str)
    return out


def build_variant_key(
    group_axes: dict,
    variant_axes: dict | None = None,
    exclude_words: set[str] | None = None,
) -> str:
    """Construit la clé de variant en anglais depuis les axes FR du tree.

    exclude_words : mots déjà présents dans le nom de base (ex.
    canonical_name_en slugifié). Un segment d'axe qui ne ferait que répéter
    des mots déjà présents — dans le nom de base OU dans un axe de priorité
    supérieure déjà traité — est allégé ou ignoré, pour éviter les suffixes
    redondants : base_key 'goat_cheese' + axe origine=chèvre ne doit pas
    devenir 'goat_cheese_goat' ; deux axes qui traduisent tous les deux
    "frais" (forme=herbe fraîche → fresh_herb, etat_thermique=frais →
    fresh) ne doivent produire "fresh" qu'une fois ('basil_fresh_herb', pas
    'basil_fresh_herb_fresh').
    Le filtrage se fait mot par mot en gardant l'ordre du segment, pas en
    l'ignorant en bloc, pour ne perdre que le mot redondant (ex.
    forme=entier → 'whole' puis partie=graine entière → 'whole_seed'
    devient 'whole' + 'seed', pas 'whole_whole_seed').
    Un doublon *interne* à un seul axe (ex. traitement=['non enrichi',
    'non blanchi'] → 'non_enrichi_non_blanchi') n'est PAS touché : "non"
    y est une particule grammaticale portant une négation différente à
    chaque fois, pas une répétition d'information.
    """
    all_axes = {**(group_axes or {}), **(variant_axes or {})}
    if not all_axes:
        return 'default'
    used_words = set(exclude_words or set())
    parts = []
    for axe in AXES_PRIORITY:
        val = all_axes.get(axe)
        if val is None:
            continue
        if isinstance(val, list):
            seg = slug('_'.join(str(x) for x in val))
        else:
            val_str = str(val).strip()
            if axe == 'teneur_MG':
                _TEXT_MG = {'écrémé': 'skimmed', 'allégé': 'light', 'entier': 'whole'}
                if val_str in _TEXT_MG:
                    seg = _TEXT_MG[val_str]
                else:
                    try:
                        mg = float(val_str.replace(',', '.').split('-')[-1].rstrip('%'))
                        seg = (
                            'skimmed' if mg == 0 else
                            'semi_skimmed' if mg <= 1.5 else
                            'low_fat' if mg <= 5 else 'whole'
                        )
                    except ValueError:
                        seg = slug(val_str)
            else:
                seg = AXES_VALUE_MAP.get(axe, {}).get(val_str) or slug(val_str)
        if not seg:
            continue
        seg_words = seg.split('_')
        kept = [w for w in seg_words if w not in used_words]
        if not kept:
            continue  # segment entierement redondant avec un axe deja traite : ignore
        parts.append('_'.join(kept))
        used_words.update(seg_words)
    return '_'.join(parts) if parts else 'default'


# ══════════════════════════════════════════════════════════════════════════════
# USDA nutrient number → champ n2
# ══════════════════════════════════════════════════════════════════════════════
USDA_NUTR_MAP: dict[str, str] = {
    '203': 'protein_g',        '204': 'fat_g',
    '205': 'carbs_g',          '207': 'ash_g',
    '208': 'calories_kcal',    '209': 'starch_g',
    '210': 'saccharose_g',     '211': 'glucose_g',
    '212': 'fructose_g',       '213': 'lactose_g',
    '214': 'maltose_g',        '221': 'alcohol_g',
    '255': 'water_g',          '268': 'energy_kj',
    '287': 'galactose_g',      '291': 'fiber_g',
    '301': 'calcium_mg',       '303': 'iron_mg',
    '304': 'magnesium_mg',     '305': 'phosphorus_mg',
    '306': 'potassium_mg',     '307': 'sodium_mg',
    '309': 'zinc_mg',          '312': 'copper_mg',
    '314': 'iodine_ug',        '315': 'manganese_mg',
    '317': 'selenium_ug',      '319': 'retinol_ug',
    '320': 'vitamin_a_rae_ug', '321': 'beta_carotene_ug',
    '323': 'alpha_tocopherol_mg', '325': 'vitamin_d2_ug',
    '326': 'vitamin_d3_ug',    '328': 'vitamin_d_ug',
    '401': 'vitamin_c_mg',     '404': 'vitamin_b1_mg',
    '405': 'vitamin_b2_mg',    '406': 'vitamin_b3_mg',
    '410': 'vitamin_b5_mg',    '415': 'vitamin_b6_mg',
    '417': 'folate_ug',        '418': 'vitamin_b12_ug',
    '421': 'choline_mg',       '430': 'vitamin_k1_ug',
    '432': 'folate_dfe_ug',    '435': 'folic_acid_ug',
    '601': 'cholesterol_mg',   '606': 'fa_saturated_g',
    '645': 'fa_mufa_g',        '646': 'fa_pufa_g',
    '629': 'fa_20_5_epa_g',    '621': 'fa_22_6_dha_g',
    '619': 'fa_18_3_ala_g',    '618': 'fa_18_2_linoleic_g',
    '269': 'sugar_g',
}

# CNF nutrient IDs (même numéros qu'USDA pour la majorité)
CNF_NUTR_MAP: dict[str, str] = {
    **USDA_NUTR_MAP,          # réutilise le mapping USDA
    '221': 'alcohol_g',       # CNF spécifique
    '269': 'sugar_g',
    '605': 'fa_trans_g',
    '339': 'vitamin_d_ug',    # CNF D2+D3 combiné
}


# ══════════════════════════════════════════════════════════════════════════════
# INTÉGRITÉ — hachage SHA-256 des sources brutes
# ══════════════════════════════════════════════════════════════════════════════

def sha256_file(path: Path) -> str:
    """Retourne le SHA-256 hex d'un fichier, en lecture par blocs (fichiers larges)."""
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):  # blocs de 1 Mo
            h.update(block)
    return h.hexdigest()


def hash_raw_sources(raw_dir: Path) -> dict:
    """Calcule les SHA-256 des trois sources brutes et retourne un dict signé."""
    files = {
        'CIQUAL': raw_dir / 'Table_Ciqual_2025_FR_2025_11_03.xlsx',
        'USDA':   raw_dir / 'FoodData_Central_foundation_food_json_2025-12-18.json',
        'CNF_FOOD_NAME':      raw_dir / 'cnf/FOOD_NAME.csv',
        'CNF_NUTRIENT_AMOUNT': raw_dir / 'cnf/NUTRIENT_AMOUNT.csv',
    }
    hashes = {}
    print('  Vérification intégrité sources brutes...')
    for label, path in files.items():
        if not path.exists():
            print(f'    ⚠ FICHIER ABSENT : {path}')
            hashes[label] = {'sha256': None, 'path': str(path), 'size_bytes': None}
            continue
        digest = sha256_file(path)
        size   = path.stat().st_size
        hashes[label] = {
            'sha256':     digest,
            'path':       str(path.relative_to(RAW_DIR.parent)),
            'size_bytes': size,
        }
        print(f'    {label:<24} {digest[:16]}…  ({size:,} bytes)')
    return hashes


def check_against_manifest(hashes: dict) -> list[str]:
    """Compare les hashes courants avec le manifest existant. Retourne les écarts."""
    if not MANIFEST_FILE.exists():
        return []
    manifest = json.loads(MANIFEST_FILE.read_text(encoding='utf-8'))
    prev = manifest.get('sources', {})
    warnings = []
    for label, info in hashes.items():
        if label not in prev:
            continue
        if info['sha256'] != prev[label]['sha256']:
            warnings.append(
                f"  ⚠ SOURCE MODIFIÉE : {label}\n"
                f"      précédent : {prev[label]['sha256'][:16]}…\n"
                f"      courant   : {(info['sha256'] or 'ABSENT')[:16]}…"
            )
    return warnings


def write_manifest(hashes: dict) -> None:
    """Écrit / met à jour raw_sources_manifest.json."""
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        '_description': 'Hashes SHA-256 des sources brutes au dernier build réussi.',
        'updated_at':   datetime.now(timezone.utc).isoformat(),
        'sources':      hashes,
    }
    MANIFEST_FILE.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')


# ══════════════════════════════════════════════════════════════════════════════
# NON-RÉGRESSION — comparaison ancien vs nouveau nutrition_v2
# ══════════════════════════════════════════════════════════════════════════════

COMPARE_LOG    = DATA / 'nutrition/logs/compare_n2_versions.json'
RECIPES_FILE   = DATA / 'recipes/recipes.json'
NUTR_DIFF_PCT  = 20.0   # seuil delta_pct pour signaler une divergence nutritive


def _default_variant_nutrients(base: dict) -> dict:
    """Retourne les nutriments du variant 'default', ou du premier variant disponible."""
    variants = base.get('variants', {})
    return variants.get('default') or next(iter(variants.values()), {})


def compare_with_previous(new_ingredients: dict) -> dict:
    """
    Compare new_ingredients avec l'actuel nutrition_v2.json.
    Retourne un dict au format compare_n2_versions.json.
    Écrit le résultat dans logs/compare_n2_versions.json.
    """
    if not OUTPUT_N2.exists():
        return {}

    old_data = json.loads(OUTPUT_N2.read_text(encoding='utf-8'))
    old_ingredients = old_data.get('ingredients', {})

    old_keys = set(old_ingredients.keys())
    new_keys = set(new_ingredients.keys())

    regressions = sorted(old_keys - new_keys)
    nouveautes  = sorted(new_keys - old_keys)

    # Divergences nutritives sur les bases présentes dans les deux versions
    nutr_fields = ['calories_kcal', 'protein_g', 'carbs_g', 'fat_g',
                   'fiber_g', 'sugar_g', 'fa_saturated_g', 'sodium_mg']
    nutr_diffs = []
    for key in sorted(old_keys & new_keys):
        old_nutr = _default_variant_nutrients(old_ingredients[key])
        new_nutr = _default_variant_nutrients(new_ingredients[key])
        diffs = {}
        for f in nutr_fields:
            ov = old_nutr.get(f)
            nv = new_nutr.get(f)
            if ov is None or nv is None:
                continue
            if ov == 0 and nv == 0:
                continue
            ref = ov if ov != 0 else nv
            delta_pct = round(abs(nv - ov) / abs(ref) * 100, 1)
            if delta_pct >= NUTR_DIFF_PCT:
                diffs[f] = {'old': ov, 'new': nv, 'delta_pct': delta_pct}
        if diffs:
            nutr_diffs.append({'key': key, 'diffs': diffs})

    # Clés recettes absentes du nouveau build
    recipe_keys_missing_new = []
    recipe_keys_missing_old = []
    if RECIPES_FILE.exists():
        try:
            recipes = json.loads(RECIPES_FILE.read_text(encoding='utf-8'))
        except Exception as _rje:
            print(f'  ⚠ recipes.json illisible (ignoré) : {_rje}')
            recipes = []
        recipe_keys = set()
        for r in (recipes if isinstance(recipes, list) else recipes.get('recipes', [])):
            for comp in r.get('composition', r.get('ingredients', [])):
                if isinstance(comp, dict):
                    # format composition: {"ingredient": "almond/default", ...}
                    ref = comp.get('ingredient') or comp.get('nutrition_key') or comp.get('ingredient_key', '')
                    base = ref.split('/')[0].strip() if ref else ''
                    if base:
                        recipe_keys.add(base)
        recipe_keys_missing_new = sorted(recipe_keys - new_keys)
        recipe_keys_missing_old = sorted(recipe_keys - old_keys)

    result = {
        'summary': {
            'old_bases':               len(old_keys),
            'new_bases':               len(new_keys),
            'regressions':             len(regressions),
            'nouveautes':              len(nouveautes),
            'nutr_diffs':              len(nutr_diffs),
            'recipe_keys_missing_new': len(recipe_keys_missing_new),
            'recipe_keys_missing_old': len(recipe_keys_missing_old),
        },
        'regressions':             regressions,
        'nouveautes':              nouveautes,
        'nutr_diffs':              nutr_diffs,
        'recipe_keys_missing_new': recipe_keys_missing_new,
        'recipe_keys_missing_old': recipe_keys_missing_old,
    }

    COMPARE_LOG.parent.mkdir(parents=True, exist_ok=True)
    COMPARE_LOG.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return result


def print_compare_report(cmp: dict) -> None:
    """Affiche un résumé console du rapport de comparaison."""
    if not cmp:
        return
    s = cmp['summary']
    print()
    print('─' * 55)
    print('  COMPARAISON vs nutrition_v2.json (production)')
    print('─' * 55)
    print(f"  Bases ancien / nouveau       : {s['old_bases']} / {s['new_bases']}")

    reg = s['regressions']
    reg_label = f'⚠ {reg}' if reg > 0 else f'✅ {reg}'
    print(f"  Régressions (bases perdues)  : {reg_label}")

    rkeys = s['recipe_keys_missing_new']
    rkeys_label = f'🔴 {rkeys}  ← BLOQUANT' if rkeys > 0 else f'✅ {rkeys}'
    print(f"  Clés recettes manquantes     : {rkeys_label}")

    print(f"  Nouveautés                   : +{s['nouveautes']}")
    print(f"  Divergences nutritives >20%  : {s['nutr_diffs']}")

    if rkeys > 0:
        print()
        print('  🔴 Clés recettes absentes du nouveau build :')
        for k in cmp['recipe_keys_missing_new'][:10]:
            print(f'      {k}')
        if rkeys > 10:
            print(f'      … et {rkeys - 10} autres (voir compare_n2_versions.json)')

    if reg > 0:
        print()
        print(f'  ⚠ {reg} bases présentes en production mais absentes du nouveau build.')
        print('  Vérifiez avant de promouvoir (voir compare_n2_versions.json).')

    print(f'  📄 Rapport complet → {COMPARE_LOG.name}')
    print('─' * 55)
# ══════════════════════════════════════════════════════════════════════════════

def load_ciqual(path: Path) -> dict:
    """CIQUAL xlsx → {alim_code_int: {n2_field: value}}"""
    import openpyxl
    print('  Chargement CIQUAL xlsx...')
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    headers_raw = [str(h or '').replace('\n', ' ').strip() for h in
                   next(ws.iter_rows(max_row=1, values_only=True))]
    # Construire la liste (col_index, n2_field) pour chaque colonne connue
    col_fields: list[tuple[int, str]] = []
    for i, h in enumerate(headers_raw):
        slug_h = _ciq_slug(h)
        n2_f = CIQUAL_COL_MAP.get(slug_h)
        if n2_f:
            col_fields.append((i, n2_f))

    idx = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        code = row[6]   # alim_code toujours en col 6
        if code is None:
            continue
        try:
            code = int(code)
        except (ValueError, TypeError):
            continue
        name_fr = str(row[7] or '')
        nutr: dict = {'name_fr': name_fr}
        for i, n2_f in col_fields:
            v = row[i]
            if v is not None and v != '':
                s = str(v).replace(',', '.').replace('<', '').strip()
                if s in ('-', 'nd', 'nr', 'NR', 'ND'):
                    # Non mesuré / non renseigné → ne pas écrire la clé (None implicite).
                    # Le fallback Atwater ou la source secondaire prendra le relais.
                    pass
                elif s.lower() in ('traces', 'trace', 'tr'):
                    # Traces = < seuil de détection.
                    # Pour les macros structurants (calories, protéines, glucides, lipides,
                    # fibres) on laisse None afin de ne pas masquer un vrai zéro ou déclencher
                    # un faux calcul Atwater. Pour les micros (sodium, sucres…) 0.0 est OK.
                    _MACRO_FIELDS = {
                        'calories_kcal', 'protein_g', 'carbs_g', 'fat_g', 'fiber_g'
                    }
                    if n2_f not in _MACRO_FIELDS:
                        nutr[n2_f] = 0.0
                    # else: ne pas écrire → None implicite
                else:
                    try:
                        nutr[n2_f] = float(s)
                    except ValueError:
                        pass
        # CIQUAL encode 0 comme sentinel "non mesuré" sur la colonne énergie.
        # Supprimer la clé permet au fallback Atwater de prendre le relais.
        # Exception : sel et additifs (protein=carbs=fat=0) → 0 kcal est légitime.
        if nutr.get('calories_kcal') == 0.0:
            prot = nutr.get('protein_g') or 0
            carb = nutr.get('carbs_g') or 0
            fat  = nutr.get('fat_g') or 0
            if 4*prot + 4*carb + 9*fat > 5:
                del nutr['calories_kcal']
        idx[code] = nutr
    wb.close()
    print(f'    → {len(idx)} aliments CIQUAL indexés')
    return idx


def load_usda(path: Path) -> dict:
    """USDA Foundation Foods JSON → {fdcId_int: {n2_field: value}}"""
    print('  Chargement USDA json...')
    data = json.loads(path.read_text(encoding='utf-8'))
    idx = {}
    for food in data.get('FoundationFoods', []):
        fid = food.get('fdcId')
        if fid is None:
            continue
        nutr: dict = {
            'name_en': food.get('description', ''),
            'name_fr': '',
        }
        for fn in food.get('foodNutrients', []):
            n = fn.get('nutrient', {})
            num = str(n.get('number', ''))
            n2_f = USDA_NUTR_MAP.get(num)
            if n2_f:
                amt = fn.get('amount')
                if amt is not None:
                    nutr[n2_f] = float(amt)
        idx[int(fid)] = nutr
    print(f'    → {len(idx)} aliments USDA indexés')
    return idx


def load_cnf(cnf_dir: Path) -> dict:
    """CNF CSV (FOOD_NAME + NUTRIENT_AMOUNT) → {FoodCode_int: {n2_field: value}}"""
    print('  Chargement CNF csv...')
    # 1. Noms
    names: dict[int, dict] = {}
    _PROBES = {502223, 501766}   # food codes à tracer pour diagnostic
    with open(cnf_dir / 'FOOD_NAME.csv', encoding='utf-8-sig', errors='replace') as f:
        reader = csv.DictReader(f)
        # ── Diagnostic : afficher les headers réels du CSV ──────────────────
        headers = reader.fieldnames or []
        fc_col = next((h for h in headers if h.strip() in ('FoodCode', 'FoodID')), None)
        if fc_col is None:
            print(f'    ⚠ FOOD_NAME.csv : colonne FoodCode/FoodID introuvable !')
            print(f'    Headers détectés : {headers[:8]}')
        else:
            print(f'    FOOD_NAME.csv : colonne clé = "{fc_col}"')
        # ────────────────────────────────────────────────────────────────────
        for row in reader:
            # Priorité FoodID : c'est la clé utilisée comme source_id dans ingredients_tree.json.
            # FoodCode est un numéro séquentiel court (max ~7578) qui diverge de FoodID
            # pour les entrées récentes (FoodID = 5xxxxx ≠ FoodCode).
            fc = row.get('FoodID') or row.get('FoodCode') or ''
            try:
                fc = int(fc)
                names[fc] = {
                    'name_en': row.get('FoodDescription', ''),
                    'name_fr': row.get('FoodDescriptionF', ''),
                }
                if fc in _PROBES:
                    print(f'    ✅ FOOD_NAME probe {fc} → {names[fc]}')
            except ValueError:
                pass
    # ── Rapport post-lecture ─────────────────────────────────────────────────
    for p in _PROBES:
        if p not in names:
            last5 = sorted(names.keys())[-5:]
            print(f'    ❌ FOOD_NAME probe {p} ABSENT (max codes lus : {last5})')

    # 2. Nutriments
    idx: dict[int, dict] = {fc: {**info} for fc, info in names.items()}
    with open(cnf_dir / 'NUTRIENT_AMOUNT.csv', encoding='utf-8-sig', errors='replace') as f:
        for row in csv.DictReader(f):
            fc_raw  = row.get('FoodID') or row.get('FoodCode') or ''
            nid_raw = row.get('NutrientID', '')
            val_raw = row.get('NutrientValue', '')
            try:
                fc  = int(fc_raw)
                n2_f = CNF_NUTR_MAP.get(nid_raw)
                if n2_f and fc in idx:
                    idx[fc][n2_f] = float(val_raw)
            except (ValueError, TypeError):
                pass

    # Sel (sodium → g) si absent
    for nutr in idx.values():
        na = nutr.get('sodium_mg')
        if na is not None and 'salt_g' not in nutr:
            nutr['salt_g'] = round(na * 2.54 / 1000, 4)

    print(f'    → {len(idx)} aliments CNF indexés')
    return idx


def build_raw_index(raw_dir: Path) -> dict:
    """Charge les 3 sources et retourne un index unifié (SOURCE, sid_int) → nutrients."""
    ciq = load_ciqual(raw_dir / 'Table_Ciqual_2025_FR_2025_11_03.xlsx')
    usd = load_usda(raw_dir / 'FoodData_Central_foundation_food_json_2025-12-18.json')
    cnf = load_cnf(raw_dir / 'cnf')

    idx: dict[tuple, dict] = {}
    for code, v in ciq.items():
        idx[('CIQUAL', code)] = v
    for fid, v in usd.items():
        idx[('USDA', fid)] = v
    for fc, v in cnf.items():
        idx[('CNF', fc)] = v
    print(f'  Index total : {len(idx)} entrées\n')
    return idx


def extract_nutrients(raw: dict) -> dict:
    """Mappe un item raw index → schéma n2 (calories_kcal, protein_g, ...)."""
    out: dict = {}
    N2_FIELDS = [
        'calories_kcal','protein_g','carbs_g','fat_g','fiber_g','sugar_g',
        'starch_g','alcohol_g','polyols_g','organic_acids_g','water_g',
        'fa_saturated_g','fa_mufa_g','fa_pufa_g',
        'fa_18_3_ala_g','fa_20_5_epa_g','fa_22_6_dha_g','fa_18_2_linoleic_g',
        'cholesterol_mg','salt_g',
        'calcium_mg','iron_mg','magnesium_mg','phosphorus_mg','potassium_mg',
        'sodium_mg','zinc_mg','copper_mg','manganese_mg','selenium_ug','iodine_ug',
        'vitamin_a_rae_ug','retinol_ug','beta_carotene_ug',
        'vitamin_d_ug','vitamin_d2_ug','vitamin_d3_ug',
        'alpha_tocopherol_mg','vitamin_k1_ug','vitamin_k2_ug','vitamin_c_mg',
        'vitamin_b1_mg','vitamin_b2_mg','vitamin_b3_mg','vitamin_b5_mg','vitamin_b6_mg',
        'folate_ug','folate_dfe_ug','folic_acid_ug','folate_intrinsic_ug','vitamin_b12_ug',
        'choline_mg',
    ]
    for f in N2_FIELDS:
        v = raw.get(f)
        if v is not None:
            out[f] = v
    # omega3_g
    parts = [raw.get(k) for k in ('fa_18_3_ala_g','fa_20_5_epa_g','fa_22_6_dha_g') if raw.get(k) is not None]
    if parts:
        out['omega3_g'] = round(sum(parts), 4)

    # ── Dérivation 1 : calories_kcal depuis energy_kj si absent ──────────────
    # EU 1169/2011 : 1 kcal = 4.184 kJ
    if 'calories_kcal' not in out:
        kj = out.get('energy_kj') or raw.get('energy_kj') or raw.get('energy_kj_jones')
        if kj:  # kj=0.0 est aussi un sentinel → on skip pour laisser Atwater
            out['calories_kcal'] = round(float(kj) / 4.184, 1)
            out['_calories_derived'] = 'kj'

    # ── Dérivation 2 : calories_kcal via Atwater si kJ aussi absent ──────────
    # Atwater général : 4 kcal/g prot+glucides, 9 kcal/g lipides, 7 kcal/g alcool
    # Utilisé quand ni la valeur source ni kJ ne sont disponibles (ou kJ=0 sentinel).
    if not out.get('calories_kcal'):  # None ou 0.0 → Atwater
        prot  = out.get('protein_g')  or 0.0
        carbs = out.get('carbs_g')    or 0.0
        fat   = out.get('fat_g')      or 0.0
        alc   = out.get('alcohol_g')  or 0.0
        if prot + carbs + fat > 0:
            out['calories_kcal'] = round(4*prot + 4*carbs + 9*fat + 7*alc, 1)
            out['_calories_derived'] = 'atwater'

    # ── Dérivation 3 : carbs_g depuis fractions si absent ────────────────────
    # glucides totaux ≈ amidon + sucres + fibres + polyols + acides organiques
    # (méthode par différence des fractions disponibles)
    if 'carbs_g' not in out:
        fractions = [
            out.get('starch_g'), out.get('sugar_g'),
            out.get('fiber_g'), out.get('polyols_g'), out.get('organic_acids_g'),
        ]
        parts = [f for f in fractions if f is not None]
        if len(parts) >= 2:  # au moins 2 fractions connues pour être fiable
            out['carbs_g'] = round(sum(parts), 3)
            out['_carbs_derived'] = True

    # ── Dérivation 4 : sugar_g depuis sucres détaillés si absent ─────────────
    # fructose + glucose + galactose + saccharose + lactose + maltose
    if 'sugar_g' not in out:
        sugar_parts = [out.get(f) or raw.get(f) for f in
                       ('fructose_g','glucose_g','galactose_g','saccharose_g','lactose_g','maltose_g')
                       if (out.get(f) is not None or raw.get(f) is not None)]
        if sugar_parts:
            out['sugar_g'] = round(sum(sugar_parts), 3)
            out['_sugar_derived'] = True

    return out



# ══════════════════════════════════════════════════════════════════════════════
# BUILDER PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def classify_cat2(groups: list) -> str:
    base = [g for g in groups if not (g.get('axes_fr') or g.get('axes') or {})]
    if len(base) > 1: return 'ombrelle'
    if not base and groups: return 'axe_nodes'
    return 'leaf'


def build_n2(v32: dict, raw_idx: dict) -> tuple:
    n2: dict = {}
    stats = {k: 0 for k in ('bases','ombrelle','variants','conflicts','hits','misses','collisions')}
    collision_log: list = []

    for cat in v32.get('categories', []):
        cat1 = cat.get('label', '')
        for sub in cat.get('subcategories', []):
            cat2   = sub.get('label', '')
            groups = sub.get('ingredient_groups', [])
            c2type = classify_cat2(groups)

            for ig in groups:
                en_name  = ig.get('canonical_name_en') or ''
                fr_name  = ig.get('canonical_name_fr') or ''
                ig_axes  = ig.get('axes_fr') or ig.get('axes') or {}
                ig_id    = ig.get('id', '')
                base_key = slug(en_name) if en_name else slug(fr_name)
                if not base_key:
                    continue

                # Collision base_key → suffixe axes EN
                if base_key in n2 and n2[base_key].get('_v32_id') != ig_id:
                    # Un axe qui ne fait que repeter un mot deja dans base_key
                    # (ex. origine=chevre quand le nom dit deja "goat cheese")
                    # est ignore pour ne pas produire un suffixe redondant.
                    axes_suffix = build_variant_key(
                        ig_axes, exclude_words=set(base_key.split('_'))
                    )
                    if axes_suffix and axes_suffix != 'default':
                        alt = f'{base_key}_{axes_suffix}'
                    elif fr_name and slug(fr_name) != base_key:
                        alt = slug(fr_name)
                    else:
                        alt = f"{base_key}_{ig_id.replace('ing_','')}"
                    # Garde-fou : si alt_key est déjà prise par un autre ig,
                    # fallback garanti sur ig_id (unique par construction).
                    if alt in n2 and n2[alt].get('_v32_id') != ig_id:
                        collision_log.append(
                            f"  COLLISION '{base_key}' → '{alt}' DÉJÀ PRIS"
                            f" → fallback '{base_key}_{ig_id.replace('ing_','')}'"
                            f"  (v32_id={ig_id})"
                        )
                        alt = f"{base_key}_{ig_id.replace('ing_','')}"
                        stats.setdefault('collisions_fallback', 0)
                        stats['collisions_fallback'] += 1
                    collision_log.append(f"  COLLISION '{base_key}' → '{alt}'  (v32_id={ig_id})")
                    base_key = alt
                    stats['collisions'] += 1

                variants: dict = {}
                for vr in ig.get('variants', []):
                    src = (vr.get('source') or '').upper()
                    sid = vr.get('source_id')
                    if not src or sid is None:
                        continue
                    raw = raw_idx.get((src, int(sid)))
                    if raw is None:
                        stats['misses'] += 1
                        continue
                    stats['hits'] += 1

                    # Axes fusionnés FR (pour construire la clé)
                    merged_axes_fr = {**ig_axes, **(vr.get('axes_fr') or vr.get('axes') or {})}
                    vr_key = build_variant_key(ig_axes, vr.get('axes_fr') or vr.get('axes') or {})
                    # Axes traduits EN (stockés dans le variant)
                    axes_en = translate_axes(merged_axes_fr)

                    alt_entry = {
                        '_source': src, '_source_id': int(sid),
                        '_v32_ing_id': ig_id,
                        '_v32_var_id': vr.get('id',''),
                        'axes': axes_en,
                        'name_fr': vr.get('name_fr') or fr_name,
                        'name_en': vr.get('name_en') or en_name,
                        **extract_nutrients(raw),
                    }

                    if vr_key in variants:
                        existing_prio = SOURCE_PRIORITY.get(variants[vr_key].get('_source',''), 99)
                        new_prio      = SOURCE_PRIORITY.get(src, 99)
                        if new_prio < existing_prio:
                            old_alt = {k: v for k, v in variants[vr_key].items()
                                       if k in ('_source','_source_id','_v32_var_id','name_fr')
                                       or isinstance(v, float)}
                            existing_alts = variants[vr_key].get('_alt_sources', [])
                            variants[vr_key] = {
                                '_source': src, '_source_id': int(sid),
                                '_v32_ing_id': ig_id, '_v32_var_id': vr.get('id',''),
                                'axes': axes_en,
                                **extract_nutrients(raw),
                                'name_fr': vr.get('name_fr') or fr_name,
                                'name_en': vr.get('name_en') or en_name,
                                'indus_conditionne':  vr.get('indus_conditionne',
                                                             ig.get('indus_conditionne', False)),
                                'conditioning_types': vr.get('conditioning_types') or
                                                      ig.get('conditioning_types') or [],
                                '_alt_sources': [old_alt] + existing_alts,
                            }
                        else:
                            variants[vr_key].setdefault('_alt_sources', []).append(alt_entry)
                        stats['conflicts'] += 1
                        continue

                    variants[vr_key] = {
                        '_source': src, '_source_id': int(sid),
                        '_v32_ing_id': ig_id, '_v32_var_id': vr.get('id',''),
                        'axes': axes_en,
                        **extract_nutrients(raw),
                        'name_fr': vr.get('name_fr') or fr_name,
                        'name_en': vr.get('name_en') or en_name,
                        'indus_conditionne':     vr.get('indus_conditionne',
                                                        ig.get('indus_conditionne', False)),
                        'conditioning_types':    vr.get('conditioning_types') or
                                                 ig.get('conditioning_types') or [],
                    }
                    stats['variants'] += 1

                ing_type = (
                    'ombrelle' if c2type == 'ombrelle' and len(groups) > 1
                    else 'node' if c2type == 'axe_nodes' else 'leaf'
                )
                # variant_dimensions : clés EN, ordonnées selon AXES_PRIORITY
                all_vr_axes_fr: set = set(ig_axes.keys())
                for vr in ig.get('variants', []):
                    all_vr_axes_fr.update((vr.get('axes_fr') or vr.get('axes') or {}).keys())
                vd_en = [AXES_EN.get(k, k) for k in AXES_PRIORITY if k in all_vr_axes_fr]
                for k in all_vr_axes_fr:  # axes hors AXES_PRIORITY en fin
                    en_k = AXES_EN.get(k, k)
                    if en_k not in vd_en:
                        vd_en.append(en_k)

                n2[base_key] = {
                    'taxonomy': {
                        'cat1': cat1,       'cat1_fr': cat.get('label_fr', ''),
                        'cat2': cat2,       'cat2_fr': sub.get('label_fr', ''),
                        'cat2_type': c2type,
                        'v32_id': ig_id, 'name_fr': fr_name, 'name_en': en_name,
                    },
                    'ingredient_type':    ing_type,
                    'variant_dimensions': vd_en,
                    'indus_conditionne':       ig.get('indus_conditionne', False),
                    'indus_conditionne_only':  ig.get('indus_conditionne_only', False),
                    'conditioning_types':      ig.get('conditioning_types') or [],
                    'aliases_fr':              ig.get('aliases_fr') or [],
                    '_v32_id':                 ig_id,
                    'variants':                variants,
                }
                if not variants:
                    stats.setdefault('empty_variants', 0)
                    stats['empty_variants'] += 1
                    if ing_type == 'leaf':
                        stats.setdefault('leaf_no_variants', [])
                        stats['leaf_no_variants'].append(base_key)
                stats['bases'] += 1
                if ing_type == 'ombrelle':
                    stats['ombrelle'] += 1

    return n2, stats, collision_log


def run(dry_run: bool = False, promote: bool = False) -> None:
    print('=' * 65)
    print('  BUILD N2 DIRECT  —  Sources brutes → nutrition_v2')
    print('=' * 65)

    print('\nChargement sources brutes...')
    raw_hashes = hash_raw_sources(RAW_DIR)

    # Vérification contre le manifest précédent
    manifest_warnings = check_against_manifest(raw_hashes)
    if manifest_warnings:
        print('\n' + '─' * 55)
        for w in manifest_warnings:
            print(w)
        print('─' * 55)
        print('  Sources modifiées depuis le dernier build.')
        print('  Vérifiez que le remplacement est intentionnel.')
        print('─' * 55 + '\n')

    v32     = json.loads(V32_FILE.read_text(encoding='utf-8'))
    raw_idx = build_raw_index(RAW_DIR)

    print('Construction...')
    n2_ingredients, stats, collision_log = build_n2(v32, raw_idx)

    # ── Injection suppléments MANUAL (ingrédients sans source officielle) ─────
    # Lus depuis nutrition_manual_supplements.json (source de vérité déclarative).
    # Correspondance par ig_id (reverse map) car canonical_name_en du tree peut
    # diverger du ing_key du fichier supplements.
    if SUPPLEMENTS_FILE.exists():
        try:
            supp_doc = json.loads(SUPPLEMENTS_FILE.read_text(encoding='utf-8'))
            supplements = supp_doc.get('supplements', {})
            # Reverse map : ig_id → n2_key (clé générée par slug(canonical_name_en))
            igid_to_n2key = {
                b.get('_v32_id'): k
                for k, b in n2_ingredients.items()
                if b.get('_v32_id')
            }
            injected = 0
            skipped = 0
            for ing_key, supp in supplements.items():
                nutrients = supp.get('nutrients', {})
                if not nutrients:
                    continue
                ig_id = supp.get('ig_id')
                # Cherche la clé n2 réelle via ig_id, sinon fallback sur ing_key
                n2_key = igid_to_n2key.get(ig_id, ing_key)
                variant_data = {
                    '_source':    'MANUAL',
                    '_source_id': None,
                    '_v32_ing_id': ig_id,
                    '_v32_var_id': supp.get('var_id'),
                    'axes':       {},
                    'name_fr':    supp.get('name_fr', ing_key),
                    'name_en':    supp.get('name_en', ing_key),
                    'indus_conditionne': False,
                    'conditioning_types': [],
                    **nutrients,
                }
                if n2_key not in n2_ingredients:
                    n2_ingredients[n2_key] = {
                        'taxonomy':               {},
                        'ingredient_type':         'ingredient',
                        'variant_dimensions':      [],
                        'indus_conditionne':        False,
                        'indus_conditionne_only':   False,
                        'conditioning_types':       [],
                        'aliases_fr':              [],
                        '_v32_id':                 ig_id,
                        'variants':                {'default': variant_data},
                    }
                    injected += 1
                else:
                    if 'default' not in n2_ingredients[n2_key].get('variants', {}):
                        n2_ingredients[n2_key].setdefault('variants', {})['default'] = variant_data
                        injected += 1
                    else:
                        skipped += 1
            print(f'  💉 Suppléments MANUAL injectés : {injected} / {len(supplements)} (déjà couverts: {skipped})')
        except Exception as exc:
            print(f'  ⚠ Impossible de charger supplements MANUAL : {exc}')
    else:
        print(f'  ℹ️  Pas de fichier supplements ({SUPPLEMENTS_FILE.name})')

    total_variants = sum(len(b.get('variants', {})) for b in n2_ingredients.values())

    n2_out = {
        'schema_version': '7.1',
        'schema_family':  'nutrition_v2',
        'built_from':     'raw_sources_direct',
        'built_at':       datetime.now(timezone.utc).isoformat(),
        'pipeline':       'build_n2_direct.py',
        'raw_sources':    raw_hashes,
        'total_bases':    len(n2_ingredients),
        'total_variants': total_variants,
        'ingredients':    n2_ingredients,
    }

    print()
    print('─' * 55)
    print(f"  Bases créées          : {stats['bases']}")
    print(f"  Bases ombrelle        : {stats['ombrelle']}")
    print(f"  Variants créés        : {stats['variants']}")
    print(f"  Collisions base_key   : {stats['collisions']}")
    print(f"  Conflits → _alt_sources : {stats['conflicts']}")
    print(f"  Lookup hits / misses  : {stats['hits']} / {stats['misses']}")
    print(f"  Total variants final  : {total_variants}")
    empty_v = stats.get('empty_variants', 0)
    leaf_empty = stats.get('leaf_no_variants', [])
    empty_label = f'⚠ {empty_v}' if empty_v > 0 else '✅ 0'
    print(f"  Ingrédients sans variants : {empty_label}")
    if leaf_empty:
        print(f'  🔴 leaf sans variants (données manquantes) :')
        for k in leaf_empty:
            print(f'      {k}')
    if collision_log:
        print('\n  Collisions (15 premières) :')
        for line in collision_log[:15]:
            print(line)

    # Comparaison avec la version en production
    cmp = compare_with_previous(n2_ingredients)
    print_compare_report(cmp)

    if dry_run:
        print('\n  [DRY-RUN] Aucune écriture.')
        return

    dest = OUTPUT_N2 if promote else OUTPUT_REBUILT
    dest.parent.mkdir(parents=True, exist_ok=True)

    # Backup automatique avant promote
    if promote and OUTPUT_N2.exists():
        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup = PROC_DIR / f'nutrition_v2_backup_{ts}.json'
        backup.write_bytes(OUTPUT_N2.read_bytes())
        print(f'\n  💾 Backup → {backup.name}')

    dest.write_text(json.dumps(n2_out, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  ✅ Écrit → {dest}')
    if promote:
        write_manifest(raw_hashes)
        print(f'  ✅ Manifest mis à jour → {MANIFEST_FILE}')
    else:
        print('  ℹ  Validez puis relancez avec --promote')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='Reconstruit nutrition_v2 depuis les sources brutes')
    ap.add_argument('--dry-run', action='store_true', help='Rapport sans écriture')
    ap.add_argument('--promote', action='store_true', help='Écrase nutrition_v2.json')
    args = ap.parse_args()
    run(dry_run=args.dry_run, promote=args.promote)
