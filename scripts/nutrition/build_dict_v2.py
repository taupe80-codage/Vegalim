"""
build_dict_v2.py  —  Pipeline dictionnaire v2 unifié
=====================================================
1 entrée dictionnaire = 1 variant n2 = 1 état d'un produit

Chaque entrée porte :
  - source / source_id  (ancre de fiabilité, niveau racine)
  - v32_ing_id / v32_var_id
  - axes  (état du produit : raw, cooked, dried...)
  - alt_sources[]  (autres IDs officiels pour ce même état)
  - diet_profile / allergens_eu / nova_group / culinary (enrichis)

Total entrées ≈ nb variants n2 (~1 921)

Sources :
  ingredients_tree.json         → hiérarchie, v32_ids
  nutrition_v2.json             → variants avec source_id + axes
  ingredients_dictionary.json   → migration méta (culinary, diet_profile...)
"""

import json, re, sys
from datetime import datetime, timezone; UTC = timezone.utc
from pathlib import Path
from collections import defaultdict, OrderedDict

# ══════════════════════════════════════════════════════════════════
# TRADUCTION AXES FR → EN (clés et valeurs)
# ══════════════════════════════════════════════════════════════════
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

DICT_AXES_VALUE_MAP: dict[str, dict[str, str]] = {
    'etat_cuisson': {
        'cru': 'raw', 'cuit': 'cooked', 'bouilli': 'boiled', 'frit': 'fried',
        'grillé': 'grilled', 'grillé à sec': 'dry_roasted', 'vapeur': 'steamed',
        'rôti': 'roasted', 'sauté': 'sauteed', 'précuit': 'precooked',
        'au four': 'baked', 'à cuire': 'to_cook', 'étouffée': 'braised',
        'au plat': 'fried_flat', 'brouillé': 'scrambled', 'coque': 'soft_boiled',
        'dur': 'hard_boiled', 'poché': 'poached', 'étuvée': 'steamed',
    },
    'forme': {
        'entière': 'whole', 'entier': 'whole', 'moulue': 'ground', 'moulu': 'ground',
        'poudre': 'powder', 'beurre': 'butter', 'compote': 'puree', 'purée': 'puree',
        'concentré': 'concentrated', 'flocon': 'flaked', 'flocons': 'flakes',
        'concassé': 'cracked', 'concassée': 'cracked', 'tranche': 'sliced',
        'tranché': 'sliced', 'bloc': 'block', 'crème': 'cream', 'extrait': 'extract',
        'jus': 'juice', 'zeste': 'zest', 'confiture': 'jam', 'broyé': 'crushed',
        'farine': 'flour', 'huile': 'oil', 'lait': 'milk', 'pâte': 'paste',
        'râpé': 'grated', 'liquide': 'liquid', 'gelée': 'jelly',
        'granulé': 'granulated', 'comprimé': 'tablet', 'pastilles': 'lozenges',
        'confit': 'candied', 'croquant': 'crunchy', 'crème de fruit': 'fruit_cream',
        'crémeux': 'creamy', 'eau végétale': 'plant_water', 'fouetté': 'whipped',
        'grain court': 'short_grain', 'grain long': 'long_grain',
        'grain moyen': 'medium_grain', 'herbe fraîche': 'fresh_herb',
        'herbe séchée': 'dried_herb', 'paillettes': 'flakes',
        'petits morceaux': 'small_pieces', 'yaourt': 'yogurt',
        'émietté': 'crumbled', 'épice': 'spice',
        'semoule': 'semolina', 'sauce': 'sauce', 'steel cut': 'steel_cut',
        'en dés': 'diced', 'double concentré': 'double_concentrated',
        'fondant': 'fondant', 'pâte dure': 'hard_paste',
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
        'iodé, fluoré': 'iodized_fluoridated', 'torréfié': 'roasted',
        'grillé': 'roasted', 'rôti': 'roasted', 'extra vierge': 'extra_virgin',
        'sans pulpe': 'pulp_free', 'alcoolique': 'alcoholic',
        'pression à froid': 'cold_pressed', 'à base de concentré': 'from_concentrate',
        'lait_cru': 'raw_milk', 'non blanchi': 'unbleached',
        'non blanchi (peau conservée)': 'unbleached_skin_on',
        'décaféiné_instantané': 'decaf_instant',
        'enrichi_blanchi': 'enriched_bleached',
        'enrichi_non_blanchi': 'enriched_unbleached',
        'non_enrichi_non_blanchi': 'unenriched_unbleached',
        'avec additifs': 'with_additives', 'frais': 'fresh',
        'grillé à sec': 'dry_roasted', "grillé à l'huile": 'roasted_in_oil',
    },
    'etat_thermique': {
        'séché': 'dried', 'frais': 'fresh', 'déshydraté': 'dehydrated',
        'réhydraté': 'rehydrated', 'UHT': 'uht', 'pasteurisé': 'pasteurized',
        'réfrigéré': 'refrigerated', 'sous pression': 'pressurized',
        'surgelé': 'frozen',
    },
    'assaisonnement': {
        'salé': 'salted', 'sucré': 'sweetened', 'sans sel': 'unsalted',
        'sans sucre': 'unsweetened', 'épicé': 'spiced', 'aromatisé': 'flavored',
        'nature': 'plain', 'naturel': 'natural', 'demi-sel': 'lightly_salted',
    },
    'conditionnement': {
        'conserve': 'canned', 'appertisé': 'canned', 'sous vide': 'vacuum',
        'lyophilisé': 'freeze_dried', 'surgelé': 'frozen', 'UHT': 'uht',
        'commercial': 'commercial', 'pasteurisé': 'pasteurized',
        'préemballé': 'pre_packaged', 'rayon frais': 'fresh_aisle',
        'sous pression': 'pressurized', 'tablette': 'tablet', 'frais': 'fresh',
    },
    'egouttage': {
        "à l'huile": 'in_oil', 'au vinaigre': 'in_vinegar',
        'dans sirop': 'in_syrup', "dans l'eau": 'in_water', 'égoutté': 'drained',
    },
    'maturite': {
        'mûr': 'ripe', 'mûre': 'ripe', 'vert': 'unripe', 'trop mûr': 'overripe',
        'mature': 'mature', 'bébé': 'baby', 'pas mûr': 'unripe',
    },
    'teneur_MG':          {'écrémé': 'skimmed', 'allégé': 'light', 'entier': 'whole',
                           'demi-écrémé': 'semi_skimmed', 'élevé en gras': 'high_fat'},
    'origine':            {
        'végétal': 'plant', 'animal': 'animal',
        'vache': 'cow', 'brebis': 'sheep', 'chèvre': 'goat', 'bufflonne': 'buffalo',
    },
    'milieu_conservation': {
        "à l'huile": 'in_oil', 'au vinaigre': 'in_vinegar',
        'dans sirop': 'in_syrup', "dans l'eau": 'in_water',
        'dans du jus': 'in_juice', 'en saumure': 'in_brine',
        'sirop léger': 'in_light_syrup', 'sirop épais': 'in_heavy_syrup',
    },
    'procede_cuisson':    {"à l'huile": 'in_oil', 'à sec': 'dry', 'au four': 'baked'},
}


def translate_axes(axes_fr: dict) -> dict:
    """Traduit clés et valeurs d'axes FR → EN pour le dict."""
    out: dict = {}
    for k_fr, v_raw in (axes_fr or {}).items():
        k_en = AXES_EN.get(k_fr, k_fr)
        if isinstance(v_raw, list):
            v_str = re.sub(r'[^a-z0-9]+', '_',
                           '_'.join(str(x) for x in v_raw).lower()).strip('_')
            out[k_en] = v_str
        elif k_fr == 'teneur_MG':
            _TEXT_MG = {'écrémé': 'skimmed', 'allégé': 'light', 'entier': 'whole', 'demi-écrémé': 'semi_skimmed', 'élevé en gras': 'high_fat'}
            v_str = str(v_raw).strip()
            out[k_en] = _TEXT_MG.get(v_str, v_str)
        else:
            v_str = str(v_raw).strip()
            out[k_en] = DICT_AXES_VALUE_MAP.get(k_fr, {}).get(v_str) or re.sub(
                r'[^a-z0-9]+', '_',
                re.sub(r"['\u2019\u2018]", '', v_str.lower())).strip('_')
    return out



sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parents[2]
DATA = ROOT / 'backend/data'
V32  = DATA / 'ingredients/ingredients_tree.json'
N2   = DATA / 'nutrition/processed/nutrition_v2.json'
# DOLD : ancien dict lu en mémoire AVANT l'écriture — l'écrasement est safe.
# Si le fichier n'existe pas encore (première run), la migration méta est ignorée gracieusement.
DOLD = DATA / 'ingredients/ingredients_dictionary.json'
OUT  = DATA / 'ingredients/ingredients_dictionary.json'

# ══════════════════════════════════════════════════════════════════
# CHARGEMENT
# ══════════════════════════════════════════════════════════════════
print('Chargement sources...')
v32  = json.loads(V32.read_text(encoding='utf-8'))
n2   = json.loads(N2.read_text(encoding='utf-8'))
# Chargement de l'ancien dict pour migration méta (culinary, diet_profile…)
# Le fichier est chargé en mémoire maintenant ; OUT sera écrasé seulement à la fin.
if DOLD.exists():
    dold = json.loads(DOLD.read_text(encoding='utf-8'))
    # Support des deux structures : liste 'ingredients' (ancienne) ou dict 'categories' (nouvelle)
    if 'ingredients' in dold and isinstance(dold['ingredients'], list):
        old_ing = {e['id']: e for e in dold['ingredients']}
    elif 'categories' in dold:
        # Nouvelle structure : aplatir ingredient_groups
        old_ing = {}
        for _cat in dold['categories'].values():
            for _sub in _cat.get('subcategories', {}).values():
                for _k, _e in _sub.get('ingredient_groups', {}).items():
                    old_ing[_k] = _e
    else:
        old_ing = {}
else:
    dold = {}
    old_ing = {}
    print('  [INFO] ingredients_dictionary.json absent — migration méta désactivée (première run)')

# Index n2 par v32_var_id → variant complet
n2_by_var_id: dict[str, dict] = {}
# Index n2 par v32_ing_id → liste de variants (pour ingr. sans var_id dans v32)
n2_by_ing_id: dict[str, list] = defaultdict(list)
# Index par (source, source_id) → variant
n2_by_source: dict[tuple, dict] = {}
# Index n2 : ing_id → base_key nutrition_v2 (clé source de vérité pour le nommage)
n2_base_by_ing_id: dict[str, str] = {}

for base_key, base in n2.get('ingredients', {}).items():
    # Récupérer le v32_id depuis la taxonomy ou le champ _v32_id
    ing_id_n2 = base.get('_v32_id') or base.get('taxonomy', {}).get('v32_id')
    if ing_id_n2:
        n2_base_by_ing_id[ing_id_n2] = base_key
    for vk, vr in base.get('variants', {}).items():
        if not isinstance(vr, dict): continue
        var_id = vr.get('_v32_var_id')
        ing_id = vr.get('_v32_ing_id')
        src_key = (vr.get('_source', ''), str(vr.get('_source_id', '')))
        if var_id:
            n2_by_var_id[var_id] = vr
        if ing_id:
            n2_by_ing_id[ing_id].append(vr)
            n2_base_by_ing_id.setdefault(ing_id, base_key)  # premier match gagne
        if src_key[1]:
            n2_by_source[src_key] = vr

print(f'  n2 : {len(n2_by_var_id)} variants indexés par var_id')
print(f'  n2 : {len(n2_by_ing_id)} ing_ids référencés')
print(f'  n2 : {len(n2_base_by_ing_id)} ing_ids avec base_key n2')

# ══════════════════════════════════════════════════════════════════
# HELPERS COMMUNS
# ══════════════════════════════════════════════════════════════════
SOURCE_PRIORITY = {'CIQUAL': 0, 'USDA': 1, 'CNF': 2, 'MANUAL': 3}

def src_rank(src: str) -> int:
    return SOURCE_PRIORITY.get((src or '').upper(), 99)

def clean_key(s: str, fallback: str = '') -> str:
    k = re.sub(r'[^a-z0-9_]', '_',
               s.lower().replace(' ', '_').replace('-', '_').replace('/', '_'))
    return re.sub(r'_+', '_', k).strip('_') or fallback

AXES_LABEL_PRIORITY = [
    'etat_cuisson', 'forme', 'partie', 'traitement', 'etat_thermique',
    'assaisonnement', 'conditionnement', 'egouttage', 'teneur_MG',
    'maturite', 'origine', 'milieu_conservation', 'procede_cuisson',
]

def axes_label(axes_fr: dict) -> str:
    """Produit un suffixe lisible EN depuis les axes FR d'un variant."""
    if not axes_fr:
        return ''
    translated = translate_axes(axes_fr)
    parts = []
    # D'abord les axes dans l'ordre de priorité (valeurs déjà EN)
    seen = set()
    for k_fr in AXES_LABEL_PRIORITY:
        k_en = AXES_EN.get(k_fr, k_fr)
        v = translated.get(k_en)
        if v:
            parts.append(str(v).lower().replace(' ', '_'))
            seen.add(k_en)
    # Puis les axes restants (hors priorité)
    for k_en, v in translated.items():
        if k_en not in seen and v:
            parts.append(str(v).lower().replace(' ', '_'))
    return '_'.join(parts)

# ══════════════════════════════════════════════════════════════════
# INDEX ANCIEN DICT → migration méta
# ══════════════════════════════════════════════════════════════════
old_by_v32id = {e.get('v32_ing_id'): e for e in old_ing.values() if e.get('v32_ing_id')}
old_by_id    = {e.get('id', ''): e for e in old_ing.values()}

def _nk(s: str) -> str:
    return re.sub(r'[^a-z0-9]', '_', s.lower())

old_by_norm = {_nk(e.get('id', '')): e for e in old_ing.values()}

CULINARY_F = ('culinary_properties', 'flavor_profile', 'cooking_behavior', 'substitutions')
DIET_F     = ('diet_profile',)
META_F     = ('allergens_eu', 'nova_group', 'bioavailability_protein')

# Clés legacy FR présentes dans l'ancien dict — supprimées à l'import,
# leurs équivalents EN sont recalculés de façon déterministe par enrich().
LEGACY_DIET_KEYS: frozenset = frozenset({
    'sans_gluten', 'sans_lactose', 'sans_fruits_a_coque',
    'hyper_proteine', 'diabet_free', 'sans_soja', 'sans_oeuf', 'riche_en_fibres',
})

def _pack_old(old: dict) -> dict:
    if not old: return {}
    result, culinary = {}, {}
    for f in CULINARY_F:
        if f in old:
            if f == 'substitutions':         culinary['substitutions'] = old[f]
            elif f == 'culinary_properties': culinary['properties']    = old[f]
            else:                            culinary[f]               = old[f]
    if culinary: result['culinary'] = culinary
    for f in DIET_F + META_F:
        if f in old:
            if f == 'diet_profile':
                # Filtrer les clés legacy FR — elles seraient sinon copiées dans
                # le diet_profile final et créeraient du bruit (521 entrées concernées).
                cleaned = {k: v for k, v in old[f].items() if k not in LEGACY_DIET_KEYS}
                if cleaned:
                    result[f] = cleaned
            else:
                result[f] = old[f]
    return result

def get_meta(ig_id: str, name_en: str, entry_key: str) -> dict:
    for src in (old_by_v32id.get(ig_id),
                old_by_id.get(entry_key),
                old_by_id.get(name_en),
                old_by_norm.get(_nk(entry_key))):
        if src: return _pack_old(src)
    return {}

# ══════════════════════════════════════════════════════════════════
# RULES ENRICHISSEMENT
# ══════════════════════════════════════════════════════════════════
# Sous-catégories naturellement sans gluten (même si leur nom contient "wheat" comme buckwheat)
GLUTEN_FREE_SUBS = {'rice','corn','millet','sorghum','buckwheat','quinoa','amaranth','teff'}

# Mots-clés dans la clé d'entrée qui indiquent la présence de gluten
# (couvre les cas où sub_label seul ne suffit pas : ex pasta, breads, brans_and_germs, fats_and_oils)
GLUTEN_KEY_TRIGGERS = (
    'wheat', 'barley', 'rye', 'spelt', 'kamut', 'bulgur', 'farro', 'einkorn', 'triticale',
)
# Exceptions : mots composés où le trigger est un faux positif
GLUTEN_KEY_EXCEPTIONS = ('buckwheat',)

# Sous-catégories qui déclenchent gluten_free=False par leur nom seul
GLUTEN_SUB_TRIGGERS = ('wheat', 'barley', 'rye', 'spelt', 'kamut', 'bulgur', 'farro', 'einkorn')

ALLERGEN_RULES = [
    (None,'wheat',['cereals_gluten']),(None,'barley',['cereals_gluten']),
    (None,'rye',['cereals_gluten']),(None,'oat',['cereals_gluten']),
    (None,'spelt',['cereals_gluten']),(None,'kamut',['cereals_gluten']),
    ('cereals','pasta',['cereals_gluten']),('cereals','semolina',['cereals_gluten']),
    ('dairy',None,['milk']),('eggs',None,['eggs']),(None,'prepared_eggs',['eggs']),
    (None,'peanut',['peanuts']),
    ('nuts_and_seeds','almond',['tree_nuts']),('nuts_and_seeds','walnut',['tree_nuts']),
    ('nuts_and_seeds','hazelnut',['tree_nuts']),('nuts_and_seeds','cashew',['tree_nuts']),
    ('nuts_and_seeds','pistachio',['tree_nuts']),('nuts_and_seeds','brazil',['tree_nuts']),
    ('nuts_and_seeds','macadamia',['tree_nuts']),('nuts_and_seeds','pecan',['tree_nuts']),
    ('nuts_and_seeds','pine',['tree_nuts']),
    (None,'soy',['soybeans']),(None,'sesame',['sesame']),(None,'mustard',['mustard']),
    (None,'celery',['celery']),('fish',None,['fish']),
    (None,'crustacean',['crustaceans']),(None,'shrimp',['crustaceans']),
    (None,'mussel',['molluscs']),(None,'oyster',['molluscs']),(None,'squid',['molluscs']),
    (None,'lupin',['lupin']),(None,'wine',['sulphites']),(None,'vinegar',['sulphites']),
]

def get_allergens(cat: str, sub: str) -> list:
    cat_l, sub_l = cat.lower(), sub.lower()
    if any(sub_l.startswith(g) for g in GLUTEN_FREE_SUBS): return []
    als: set = set()
    for rc, rs, a in ALLERGEN_RULES:
        if (rc is None or cat_l.startswith(rc)) and (rs is None or sub_l.startswith(rs)):
            als.update(a)
    return sorted(als)

NOVA_RULES = [
    ('prepared',None,4),('dairy','cheese',3),('dairy','butter',2),
    ('dairy','cream',3),('dairy','kefir',3),('dairy','yogurt',3),
    ('dairy','condensed',3),('dairy','powdered',3),('dairy','whey',2),('dairy','milk',1),
    ('fats_and_oils',None,2),('sugars_honeys','sugar',2),('sugars_honeys','honey',1),
    ('sugars_honeys','syrup',2),('sugars_honeys','chocolate',4),('leavening',None,2),
    ('cereals','pasta',3),('cereals','bread',3),('cereals','flour',2),
    ('cereals','rice',1),('cereals','corn',1),('cereals','buckwheat',1),
    ('cereals','quinoa',1),('cereals','oat',1),
    ('fruits',None,1),('vegetables',None,1),('legumes',None,1),
    ('nuts_and_seeds',None,1),('eggs',None,1),('seaweed',None,1),
    ('fish',None,1),('spices',None,1),('herbs',None,1),
    ('beverages','water',1),('beverages','tea',1),('beverages','juice',1),
    ('beverages','alcohol',4),
]

def get_nova(cat: str, sub: str):
    for rc, rs, n in NOVA_RULES:
        if (rc is None or cat.lower().startswith(rc)) and \
           (rs is None or sub.lower().startswith(rs)):
            return n
    return None

NOT_VEGAN_CATS = {'dairy_products','eggs','fish_and_seafood','meat_and_poultry','fish','seafood'}
NOT_VEGAN_SUBS = {'butter','cream','creme_fraiche','cheeses','kefir','whey','milk',
                  'condensed_milk','powdered_milk','yogurts','eggs_general','prepared_eggs'}
NOT_VEG_CATS   = {'fish_and_seafood','meat_and_poultry','fish','seafood'}

# Sous-catégories toujours considérées comme produits laitiers (dairy_free=False)
DAIRY_SUBS = {'milk','condensed_milk','powdered_milk','butter','cream',
               'creme_fraiche','cheeses','kefir','whey','yogurts'}

# Mots-clés dans la clé d'entrée qui indiquent un produit contenant du lait,
# même si la taxonomie cat1/cat2 ne pointe pas vers dairy_products.
# NB : on n'attrape pas les plats composés (lasagne, quiche...) — hors périmètre.
DAIRY_KEY_TRIGGERS = {
    'milk_chocolate',       # chocolat au lait
    'white_chocolate',      # chocolat blanc (beurre de cacao + lait)
    'au_lait',              # ex: café_au_lait, riz_au_lait
    'dulce_de_leche',       # confiture de lait
    'bechamel',             # sauce béchamel (base lait)
    'custard',              # crème anglaise / crème pâtissière
    'caramel_au_beurre',    # contient du beurre
}
BIO_TABLE = [
    ('dairy','',0.92),('eggs','',0.97),('fish','',0.90),('meat','',0.91),
    ('legumes','soy',0.91),('legumes','',0.72),
    ('nuts_and_seed','peanut',0.78),('nuts_and_seed','',0.75),
    ('cereals','',0.67),('vegetables','',0.55),('fruits','',0.50),
]

def get_bio(cat: str, sub: str) -> float:
    for rc, rs, b in BIO_TABLE:
        if cat.lower().startswith(rc) and (rs == '' or sub.lower().startswith(rs)):
            return b
    return 0.65

CULINARY_MAP = {
    'vegetables':['fresh','fiber'],'fruits':['fresh','sweet'],
    'legumes':['protein','fiber'],'cereals':['starch'],
    'dairy':['protein','fat'],'eggs':['protein','fat'],
    'fish':['protein','omega3'],'nuts_and_seeds':['fat','protein'],
    'fats_and_oils':['fat'],'sugars_honeys':['sweet'],
    'spices':['aromatic'],'herbs':['aromatic'],'seaweed':['mineral'],
}

def _has_gluten_keyword(key: str) -> bool:
    """Retourne True si la clé d'entrée contient un mot-clé gluten qui n'est pas un faux positif."""
    key_l = key.lower()
    # Vérifier d'abord les exceptions (ex: buckwheat contient "wheat" mais est GF)
    for exc in GLUTEN_KEY_EXCEPTIONS:
        if key_l.startswith(exc) or ('_' + exc) in key_l:
            return False
    # Puis chercher les triggers
    for trigger in GLUTEN_KEY_TRIGGERS:
        # Chercher le trigger comme mot entier (délimité par _ ou début/fin)
        # Ex: "wheat" dans "wheat_germ", "whole_wheat_pasta", "bulgur_raw"
        if key_l == trigger or key_l.startswith(trigger + '_') or \
           ('_' + trigger + '_') in key_l or key_l.endswith('_' + trigger):
            return True
    return False


def enrich(ig: dict, cat_label: str, sub_label: str, n2_vr: dict, entry_key: str = ''):
    """Enrichit une entrée dict depuis taxonomie + macros n2. Ne pas écraser valeurs existantes."""
    prot  = n2_vr.get('protein_g')
    fiber = n2_vr.get('fiber_g')
    fat   = n2_vr.get('fat_g')
    sugar = n2_vr.get('sugar_g')
    cat_l, sub_l = cat_label.lower(), sub_label.lower()
    key_l = (entry_key or '').lower()

    # ── vegan ──────────────────────────────────────────────────────
    vegan  = not (any(cat_l.startswith(c) for c in NOT_VEGAN_CATS) or sub_l in NOT_VEGAN_SUBS)
    # Gélatine : origine animale (gelling_agents), non couverte par taxonomie seule
    if sub_l == 'gelling_agents' and 'gelatin' in key_l:
        vegan = False
    # Pâtes aux œufs : contiennent des œufs malgré la sous-cat "pasta"
    if key_l.startswith('egg_pasta'):
        vegan = False

    # ── vegetarian ─────────────────────────────────────────────────
    vegeta = not any(cat_l.startswith(c) for c in NOT_VEG_CATS)
    if sub_l == 'gelling_agents' and 'gelatin' in key_l:
        vegeta = False  # gélatine d'origine animale (os/peau)

    # ── gluten_free ────────────────────────────────────────────────
    # Règle 1 : sous-catégorie naturellement GF (buckwheat, rice, quinoa…)
    if any(sub_l.startswith(s) for s in GLUTEN_FREE_SUBS):
        gluten = True
    # Règle 2 : sous-catégorie dont le nom est un trigger gluten
    elif any(sub_l.startswith(s) for s in GLUTEN_SUB_TRIGGERS):
        gluten = False
    # Règle 3 : clé d'entrée contient un mot-clé gluten (couvre whole_wheat_pasta, bulgur_*, etc.)
    elif _has_gluten_keyword(key_l):
        gluten = False
    else:
        gluten = True

    # ── lactose_free ───────────────────────────────────────────────
    lactose= not (cat_l.startswith('dairy') or sub_l in
                  {'milk','condensed_milk','powdered_milk','butter','cream',
                   'creme_fraiche','cheeses','kefir','whey','yogurts'})

    # ── dairy_free ────────────────────────────────────────────────
    # Condition taxonomique : même périmètre que lactose_free (toute la cat dairy
    # + sous-catégories laitières dans d'autres cat, ex: butter dans fats_and_oils).
    dairy  = not (cat_l.startswith('dairy') or sub_l in DAIRY_SUBS)
    # Rattrapage par clé d'entrée : ingrédients composés contenant du lait
    # mais classés hors dairy_products (chocolat au lait, béchamel, etc.).
    if dairy and any(kw in key_l for kw in DAIRY_KEY_TRIGGERS):
        dairy = False

    # ── nut_free ───────────────────────────────────────────────────
    nuts   = not (cat_l.startswith('nuts') and sub_l not in {'seeds','nut_butters','coconut'})

    # ── soy_free ───────────────────────────────────────────────────
    soy    = sub_l != 'soy'
    # Sauce soja au blé : contient aussi du gluten (déjà couvert par gluten ci-dessus)
    # soy_free reste False pour toute la sous-cat soy (correct)

    # ── egg_free ───────────────────────────────────────────────────
    egg    = not (cat_l.startswith('egg') or sub_l in {'eggs_general','prepared_eggs'})
    # Pâtes aux œufs : contiennent des œufs
    if key_l.startswith('egg_pasta'):
        egg = False

    # Champs d'exclusion calculés de façon déterministe depuis la taxonomie.
    # Ces 7 champs ne doivent JAMAIS être écrasés par l'ancien dict (migration partielle)
    # car les erreurs de l'ancien dict (ex: dairy vegan=True) survivraient au calcul correct.
    EXCLUSION_FLAGS = {'vegan', 'vegetarian', 'gluten_free', 'lactose_free',
                       'nut_free', 'soy_free', 'egg_free', 'dairy_free'}

    base_dp = {'vegan':vegan,'vegetarian':vegeta,'gluten_free':gluten,
               'lactose_free':lactose,'dairy_free':dairy,
               'nut_free':nuts,'soy_free':soy,'egg_free':egg}
    if prot  is not None: base_dp['high_protein']      = float(prot)  >= 15.0
    if fiber is not None: base_dp['high_fiber']         = float(fiber) >= 3.0
    if fat   is not None: base_dp['high_fat']           = float(fat)   >= 20.0
    if sugar is not None and fiber is not None:
        base_dp['diabetic_friendly'] = float(sugar) < 10.0 and float(fiber) >= 2.0

    # Merge : l'ancien dict prime pour les champs nutritionnels (high_protein, nova…)
    # mais les flags d'exclusion sont toujours ceux calculés ci-dessus (priorité inversée).
    old_dp = {k: v for k, v in (ig.get('diet_profile') or {}).items()
              if k not in EXCLUSION_FLAGS}
    ig['diet_profile'] = {**base_dp, **old_dp}

    if ig.get('allergens_eu') is None:
        ig['allergens_eu'] = get_allergens(cat_label, sub_label)
    if not ig.get('nova_group'):
        n = get_nova(cat_label, sub_label)
        if n: ig['nova_group'] = n
    if ig.get('bioavailability_protein') is None:
        ig['bioavailability_protein'] = get_bio(cat_label, sub_label)
    culinary = ig.get('culinary') or {}
    if not culinary.get('properties'):
        props = list(next((v for k, v in CULINARY_MAP.items()
                           if cat_label.lower().startswith(k.lower())), []))
        if prot  and float(prot)  >= 15 and 'protein' not in props: props.append('protein')
        if fiber and float(fiber) >= 5  and 'fiber'   not in props: props.append('fiber')
        if props: culinary['properties'] = props; ig['culinary'] = culinary


# ══════════════════════════════════════════════════════════════════
# CONSTRUCTION PRINCIPALE
# 1 entrée = 1 variant n2 (identifié par v32_var_id)
# Organisé dans la hiérarchie v32 (cat > sub > ingredient_groups)
# ══════════════════════════════════════════════════════════════════
print('\nConstruction dictionnaire (1 entrée = 1 variant n2)...')
stats    = defaultdict(int)
cats_out: dict = {}
orphans:  list = []

# Tracker les var_ids déjà placés (éviter doublons si un var_id apparaît plusieurs fois)
placed_var_ids: set[str] = set()
placed_keys:    set[str] = set()   # pour clés uniques dans chaque sub

for cat in v32.get('categories', []):
    cat_label = cat.get('label', cat.get('id', ''))
    cat_entry = cats_out.setdefault(cat_label, {
        'id': cat.get('id', ''), 'subcategories': {}
    })

    for sub in cat.get('subcategories', []):
        sub_label = sub.get('label', sub.get('id', ''))
        sub_entry = cat_entry['subcategories'].setdefault(sub_label, {
            'id': sub.get('id', ''), 'ingredient_groups': {}
        })
        sub_keys_used: set[str] = set()

        for ig in sub.get('ingredient_groups', []):
            ig_id   = ig.get('id', '')
            name_en = ig.get('canonical_name_en', '') or ig_id
            name_fr = ig.get('canonical_name_fr', '')
            # Priorité : clé nutrition_v2 (source de vérité) > canonical_name_en du tree
            base_key = n2_base_by_ing_id.get(ig_id) or clean_key(name_en, ig_id)

            # Migration méta depuis ancien dict (commune à tous les variants de cet ig)
            meta = get_meta(ig_id, name_en, base_key)

            v32_variants = ig.get('variants', [])
            if not v32_variants:
                stats['ig_no_variant'] += 1
                continue

            # Axes définis au niveau du groupe (partagés par tous les variants)
            ig_axes_fr: dict = ig.get('axes_fr') or ig.get('axes') or {}

            # Regrouper les variants v32 par axes pour détecter les doublons (sources multiples)
            vr_by_axes: dict = defaultdict(list)
            for vr in v32_variants:
                if not isinstance(vr, dict): continue
                var_id = vr.get('id', '')
                source = vr.get('source', '')
                sid    = vr.get('source_id')
                if not sid and source != 'MANUAL': continue
                # Merger axes groupe + axes variant (variant a priorité)
                merged_axes = {**ig_axes_fr, **(vr.get('axes_fr') or vr.get('axes') or {})}
                ax     = axes_label(merged_axes)
                vr_by_axes[ax].append({
                    'var_id': var_id,
                    'source': source,
                    'source_id': sid,
                    'axes': merged_axes,
                })
                stats['total_v32_variants'] += 1

            if not vr_by_axes:
                stats['ig_no_valid_variant'] += 1
                continue

            # Pour chaque axe (état), créer UNE entrée dict
            for ax, candidates in vr_by_axes.items():
                # Trier par priorité source
                candidates.sort(key=lambda c: src_rank(c['source']))
                primary   = candidates[0]
                alt_list  = candidates[1:]

                var_id    = primary['var_id']
                source    = primary['source']
                source_id = primary['source_id']

                # Lookup n2 pour ce variant
                n2_vr = (n2_by_var_id.get(var_id)
                         or n2_by_source.get((source, str(source_id)))
                         or {})

                # Clé d'entrée : base_key[_axe_label]
                if ax:
                    entry_key = clean_key(f'{base_key}_{ax}', f'{base_key}_{ax}')
                else:
                    entry_key = base_key

                # Garantir unicité dans la sous-catégorie
                if entry_key in sub_keys_used:
                    entry_key = f'{entry_key}_{ig_id[-4:]}'
                sub_keys_used.add(entry_key)

                # Construire l'entrée
                ig_entry: dict = {
                    # ── Ancres d'identité ──────────────────────────────────
                    'v32_ing_id':  ig_id,
                    'v32_var_id':  var_id,
                    # ── Source officielle (niveau racine) ─────────────────
                    'source':        source,
                    'source_id':     source_id,
                    'source_label':  n2_vr.get('name_fr') or n2_vr.get('name_en') or '',
                    # ── Noms ──────────────────────────────────────────────
                    'canonical_name_fr': name_fr,
                    'canonical_name_en': name_en,
                    # ── État du produit (traduit FR → EN) ─────────────────
                    'axes': translate_axes(primary['axes']),  # primary['axes'] already FR-keyed
                    'aliases': [],
                }

                # Alt sources (autres IDs officiels pour ce même état)
                if alt_list:
                    ig_entry['alt_sources'] = [
                        {'source': a['source'], 'source_id': a['source_id'],
                         'v32_var_id': a['var_id']}
                        for a in alt_list
                    ]
                    stats['alts'] += len(alt_list)

                # Métadonnées migrées depuis ancien dict
                ig_entry.update(meta)

                # Enrichissement déterministe
                enrich(ig_entry, cat_label, sub_label, n2_vr, entry_key)

                sub_entry['ingredient_groups'][entry_key] = ig_entry
                placed_var_ids.add(var_id)
                # Marquer aussi les alt_sources comme placés (évite faux "non placés")
                for a in alt_list:
                    placed_var_ids.add(a['var_id'])
                stats['written'] += 1

print(f'  Entrées écrites         : {stats["written"]}')
print(f'  Variants v32 traités    : {stats["total_v32_variants"]}')
print(f'  Alt sources             : {stats["alts"]}')
print(f'  Méta migrées            : {sum(1 for cat in cats_out.values() for sub in cat["subcategories"].values() for ig in sub["ingredient_groups"].values() if ig.get("culinary") or ig.get("nova_group"))}')

# ── Audit croisé tree ↔ n2 ────────────────────────────────────────────────────
# Sens 1 : variants n2 non placés (dans n2 mais var_id absent du tree)
n2_unplaced = [vr for vr in
               (vr for b in n2['ingredients'].values() for vr in b.get('variants', {}).values()
                if isinstance(vr, dict))
               if vr.get('_v32_var_id') not in placed_var_ids and vr.get('_source_id')]
print(f'  Variants n2 non placés  : {len(n2_unplaced)}')
if n2_unplaced:
    print('  ⚠  Détail (20 premiers) :')
    for vr in n2_unplaced[:20]:
        print(f'     [{vr.get("_source","?")}:{vr.get("_source_id","?")}]'
              f'  var_id={vr.get("_v32_var_id","∅")}'
              f'  {vr.get("name_fr") or vr.get("name_en","?")}')
    if len(n2_unplaced) > 20:
        print(f'     ... +{len(n2_unplaced) - 20} autres')

# Sens 2 : variants déclarés dans l'arbre mais absents de n2 en source primaire.
# Distingue : vraiment absents (raw introuvable) vs présents en _alt_sources (priorité inférieure).
n2_var_ids_primary: set[str] = set()
n2_var_ids_alt:     set[str] = set()
for b in n2['ingredients'].values():
    for vr in b.get('variants', {}).values():
        if not isinstance(vr, dict):
            continue
        if vr.get('_v32_var_id'):
            n2_var_ids_primary.add(vr['_v32_var_id'])
        for alt in vr.get('_alt_sources', []):
            if alt.get('_v32_var_id'):
                n2_var_ids_alt.add(alt['_v32_var_id'])

tree_missing: list[dict] = []   # vraiment absents de n2 (raw introuvable)
tree_in_alt:  list[dict] = []   # présents en _alt_sources (source secondaire, données OK)
for _cat in v32.get('categories', []):
    for _sub in _cat.get('subcategories', []):
        for _ig in _sub.get('ingredient_groups', []):
            for _vr in _ig.get('variants', []):
                if not isinstance(_vr, dict): continue
                _vid = _vr.get('id', '')
                _sid = _vr.get('source_id')
                if not (_vid and _sid):
                    continue
                _entry = {
                    'ing_id':    _ig.get('id', ''),
                    'var_id':    _vid,
                    'cat':       _cat.get('label', _cat.get('id', '')),
                    'sub':       _sub.get('label', _sub.get('id', '')),
                    'name_fr':   _ig.get('canonical_name_fr', _ig.get('name_fr', '')),
                    'name_en':   _ig.get('canonical_name_en', _ig.get('name_en', '')),
                    'axes':      _vr.get('axes_fr') or _vr.get('axes') or {},
                    'source':    _vr.get('source', '?'),
                    'source_id': _sid,
                }
                if _vid in n2_var_ids_alt:
                    tree_in_alt.append(_entry)
                elif _vid not in n2_var_ids_primary:
                    tree_missing.append(_entry)

from collections import Counter as _Counter
if tree_in_alt:
    _alt_src = dict(_Counter(m['source'] for m in tree_in_alt).most_common())
    print(f'  Variants en alt_sources  : {len(tree_in_alt)}'
          f'  (source secondaire, données présentes — {_alt_src})')

_by_src = dict(_Counter(m['source'] for m in tree_missing).most_common())
_by_cat = dict(_Counter(m['cat']    for m in tree_missing).most_common(8))
print(f'  Variants tree sans nutri : {len(tree_missing)}'
      + (f'  (vraiment absents — {_by_src})' if tree_missing else ' ✅'))
if tree_missing:
    print(f'  Top catégories          : {_by_cat}')
    _audit = {
        'summary': {
            'total_missing':  len(tree_missing),
            'total_in_alt':   len(tree_in_alt),
            'by_source':      _by_src,
            'top_categories': _by_cat,
        },
        'missing_variants':    tree_missing,
        'alt_source_variants': tree_in_alt,
    }
    _audit_path = Path(__file__).parent / 'n2_missing_audit.json'
    _audit_path.write_text(json.dumps(_audit, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'  📄 Audit → {_audit_path.name}  (source_ids vraiment absents des raws)')
# ──────────────────────────────────────────────────────────────────────────────

# ══════════════════════════════════════════════════════════════════
# PHASE 2 — ALIAS INDEX
# ══════════════════════════════════════════════════════════════════
print('\nPhase 2 — Alias index...')

v2_keys:         set[str]       = set()
v2_v32id_to_key: dict[str, str] = {}
v2_norm_to_key:  dict[str, str] = {}

def _norm(s: str) -> str:
    s = re.sub(r'[-\s]+', '_', s.lower().strip())
    return re.sub(r'_+', '_', re.sub(r'[^a-z0-9_]', '', s)).strip('_')

def _singular(s: str) -> str:
    if s.endswith('ies'): return s[:-3] + 'y'
    if s.endswith('es') and len(s) > 4: return s[:-2]
    if s.endswith('s')  and len(s) > 3: return s[:-1]
    return s

for cat in cats_out.values():
    for sub in cat['subcategories'].values():
        for ek, ig in sub['ingredient_groups'].items():
            v2_keys.add(ek)
            iid = ig.get('v32_ing_id')
            if iid: v2_v32id_to_key.setdefault(iid, ek)
            for k in (_norm(ek), _singular(_norm(ek)), _norm(ek) + 's'):
                v2_norm_to_key.setdefault(k, ek)

BLOCKED: set[tuple] = {
    ('olive_oil','*'),('coconut_oil','*'),('palm_oil','*'),('sesame_oil','*'),
    ('sunflower_oil','*'),('flaxseed_oil','*'),
    ('zucchini','squash_green_zucchini'),('beet','beet_greens'),
    ('curry_paste','curry_powder'),('curry_leaf','curry_powder'),
    ('milk_plant_almond','milk'),('milk_plant_oat','milk'),('milk_plant_soy','milk'),
    ('lait_coco','milk'),('mushroom','mushroom_beech'),
    ('tofu','tofu_smoked'),('salt','salt_table'),('bread','bread_gluten_free'),
    ('xylitol','sugars'),('peanut_butter','butter'),('rice_vinegar','vinegar'),
    ('semolina','couscous_semolina_cooked'),
}

aliases: dict[str, str] = {}

def add_alias(alias: str, canon: str):
    if alias == canon or canon not in v2_keys or alias in aliases: return
    if (alias, '*') in BLOCKED or (alias, canon) in BLOCKED: return
    aliases[alias] = canon

# A : même v32_ing_id → pointer vers le variant "default" ou premier disponible
v32id_to_old: dict = defaultdict(list)
for nm, e in old_ing.items():
    vid = e.get('v32_ing_id')
    if vid: v32id_to_old[vid].append(nm)
for vid, names in v32id_to_old.items():
    canon = v2_v32id_to_key.get(vid)
    if canon:
        for nm in names: add_alias(nm, canon)

# D : normalisation
for nm in old_ing:
    if nm in aliases: continue
    t = v2_norm_to_key.get(_norm(nm)) or v2_norm_to_key.get(_singular(_norm(nm)))
    if t and t != nm: add_alias(nm, t)

MANUAL = {'rice_noodle':'rice_vermicelli','vine_leaf':'vine_leaves','zaatar':'za_atar',
          'spatzle':'spaetzle','aubergine':'eggplant','small_eggplant':'eggplant',
          'lemongrass_stalk':'lemongrass','pine_nut':'pine_nuts','poppy':'poppy_seeds'}
alias_index: dict[str, str] = {a: c for a, c in MANUAL.items() if c in v2_keys}
for a, c in aliases.items(): alias_index.setdefault(a, c)
alias_index = dict(sorted(alias_index.items()))
print(f'  Alias index : {len(alias_index)} entrées')

# ══════════════════════════════════════════════════════════════════
# ÉCRITURE FINALE
# ══════════════════════════════════════════════════════════════════
print('\nÉcriture...')
total = stats['written']
output = {
    '_schema': {
        'version':           '2.0',
        'family':            'ingredients_dictionary',
        'built_from':        ['ingredients_tree.json', 'nutrition_v2.json'],
        'built_at':          datetime.now(UTC).strftime('%Y-%m-%d'),
        'note':              '1 entrée = 1 variant n2 (1 état produit)',
        'total_entries':     total,
        'total_aliases':     len(alias_index),
        'orphans_count':     len(orphans),
        'n2_unplaced':       len(n2_unplaced),
        'key_convention':    'nutrition_v2',
        'enrichment_fields': ['culinary'],
        'enrichment_note':   (
            'Les champs listés dans enrichment_fields sont saisis manuellement '
            'et préservés entre deux rebuilds. Tous les autres champs '
            '(diet_profile, allergens_eu, nova_group, bioavailability_protein) '
            'sont calculés algorithmiquement par build_dict_v2.py.'
        ),
    },
    'categories': cats_out,
    'alias_index': alias_index,
    'orphans':     orphans,
}
# Écriture atomique : on écrit dans un .tmp puis on renomme
# → si le process est tué à mi-écriture, le fichier final reste intact
_tmp = OUT.with_suffix('.tmp')
_tmp.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
_tmp.replace(OUT)

print()
print('=' * 60)
print('  BUILD DICT v2 — TERMINÉ')
print('=' * 60)
print(f'  Entrées dict       : {total}')
print(f'  (n2 a {len(n2_by_var_id)} variants — {len(n2_by_var_id) - total} non couverts)')
print(f'  Alias index        : {len(alias_index)}')
print(f'  Orphelins          : {len(orphans)}')
print(f'\n  Ecrit → {OUT}')
