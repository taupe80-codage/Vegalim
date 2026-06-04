#!/usr/bin/env python3
"""
split_ingredients_v2.py
Sépare 3 ing mal fusionnés + corrige 3 axes manquants.

SPLITS (ing_group dédoublés) :
  ing_05426 lait         → ing_05426 (demi-écrémé) + ing_05751 (écrémé)
  ing_00263 avoine       → ing_00263 (flocons)     + ing_05752 (steel cut)
  ing_03683 épinard      → ing_03683 (baby)        + ing_05753 (mature)

CORRECTIONS D'AXES (variants avec axes incomplets) :
  ing_00964 var_00965    → ajouter etat_thermique: séché  (source dit bien "séchée sucrée")
  ing_02343 var_02345    → ajouter etat_thermique: déshydraté  (source dit "déshydratée")
  ing_02024 var_02025    → ajouter forme: poudre  (source dit "cardamom, ground")
"""
import json, copy
from pathlib import Path

BASE = Path(r'C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\backend\data\ingredients')
TREE_FILE = BASE / 'ingredients_tree_enriched_v2.json'
tree = json.load(open(TREE_FILE, encoding='utf-8'))

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def find_ing(ing_id):
    """Retourne (ing_obj, cat2_list, index)."""
    for cat1 in tree['categories']:
        for cat2 in cat1['subcategories']:
            lst = cat2.get('ingredient_groups', [])
            for i, ing in enumerate(lst):
                if ing['id'] == ing_id:
                    return ing, lst, i
    raise KeyError(f'ing introuvable : {ing_id}')

def find_var(ing, var_id):
    for v in ing.get('variants', []):
        if v['id'] == var_id:
            return v
    raise KeyError(f'var introuvable : {var_id}')

def make_ing(ing_id, name_fr, name_en, axes_fr, axes_en, variants,
             indus=False, indus_only=False, cond_types=None, aliases_fr=None):
    obj = {
        'id': ing_id,
        'canonical_name_fr': name_fr,
        'canonical_name_en': name_en,
        'indus_conditionne': indus,
        'indus_conditionne_only': indus_only,
        'conditioning_types': cond_types or [],
        'variants': variants,
        'axes_en': axes_en,
        'axes_fr': axes_fr,
    }
    if aliases_fr:
        obj['aliases_fr'] = aliases_fr
    return obj

log = []

# ─────────────────────────────────────────────────────────────
# 1. SPLIT — ing_05426 lait pasteurisé
#    var_05427 demi-écrémé → reste ing_05426
#    var_05451 écrémé      → nouveau ing_05751
# ─────────────────────────────────────────────────────────────
ing_lait, lst_lait, idx_lait = find_ing('ing_05426')
var_demi  = find_var(ing_lait, 'var_05427')   # demi-écrémé
var_ecreme = find_var(ing_lait, 'var_05451')  # écrémé

# Mettre à jour ing_05426 → demi-écrémé seulement
ing_lait['variants'] = [var_demi]
ing_lait['axes_fr'] = {'teneur_MG': 'demi-écrémé', 'etat_thermique': 'pasteurisé'}
ing_lait['axes_en'] = {'fat_content': 'semi_skimmed', 'thermal_state': 'pasteurized'}

# Nouveau ing_05751 → écrémé
ing_05751 = make_ing(
    'ing_05751', 'lait écrémé pasteurisé', 'skimmed pasteurized milk',
    {'teneur_MG': 'écrémé', 'etat_thermique': 'pasteurisé'},
    {'fat_content': 'skimmed', 'thermal_state': 'pasteurized'},
    [var_ecreme],
    indus=True
)
lst_lait.insert(idx_lait + 1, ing_05751)
log.append('SPLIT  ing_05426 lait → ing_05426 (demi-écrémé) + ing_05751 (écrémé)')

# ─────────────────────────────────────────────────────────────
# 2. SPLIT — ing_00263 avoine
#    var_00264 rolled/flocons → reste ing_00263
#    var_00266 steel cut      → nouveau ing_05752
# ─────────────────────────────────────────────────────────────
ing_avoine, lst_avoine, idx_avoine = find_ing('ing_00263')
var_flocons   = find_var(ing_avoine, 'var_00264')   # rolled old fashioned
var_steelcut  = find_var(ing_avoine, 'var_00266')   # steel cut

# Corriger les axes du variant flocons (manquait la forme)
var_flocons['axes_fr']['forme'] = 'flocons'
var_flocons['axes_en']['form']  = 'rolled'

# Mettre à jour ing_00263 → flocons seulement
ing_avoine['variants'] = [var_flocons]
ing_avoine['axes_fr'] = {'forme': 'flocons', 'partie': 'graine entière'}
ing_avoine['axes_en'] = {'form': 'rolled', 'part': 'whole_grain'}

# Nouveau ing_05752 → steel cut
ing_05752 = make_ing(
    'ing_05752', 'avoine steel cut', 'steel cut oats',
    {'forme': 'steel cut', 'partie': 'graine entière'},
    {'form': 'steel_cut', 'part': 'whole_grain'},
    [var_steelcut]
)
lst_avoine.insert(idx_avoine + 1, ing_05752)
log.append('SPLIT  ing_00263 avoine → ing_00263 (flocons) + ing_05752 (steel cut)')

# ─────────────────────────────────────────────────────────────
# 3. SPLIT — ing_03683 épinard
#    var_03684 baby spinach   → reste ing_03683
#    var_03686 mature spinach → nouveau ing_05753
# ─────────────────────────────────────────────────────────────
ing_epinard, lst_epinard, idx_epinard = find_ing('ing_03683')
var_baby   = find_var(ing_epinard, 'var_03684')   # baby
var_mature = find_var(ing_epinard, 'var_03686')   # mature

# Corriger les axes du variant baby (source = "Spinach, baby")
var_baby['axes_fr']['maturite'] = 'bébé'
var_baby['axes_en']['maturity'] = 'baby'

# Mettre à jour ing_03683 → baby seulement
ing_epinard['variants'] = [var_baby]
ing_epinard['canonical_name_fr'] = 'épinard (baby)'
ing_epinard['canonical_name_en'] = 'baby spinach'
ing_epinard['axes_fr'] = {'etat_cuisson': 'cru', 'maturite': 'bébé'}
ing_epinard['axes_en'] = {'cooking_state': 'raw', 'maturity': 'baby'}

# Corriger l'axe du variant mature (etat_thermique: mature est une erreur de champ)
var_mature['axes_fr'] = {'maturite': 'mature'}
var_mature['axes_en'] = {'maturity': 'mature'}

# Nouveau ing_05753 → épinard mature
ing_05753 = make_ing(
    'ing_05753', 'épinard mature', 'mature spinach',
    {'etat_cuisson': 'cru', 'maturite': 'mature'},
    {'cooking_state': 'raw', 'maturity': 'mature'},
    [var_mature]
)
lst_epinard.insert(idx_epinard + 1, ing_05753)
log.append('SPLIT  ing_03683 épinard → ing_03683 (baby) + ing_05753 (mature)')

# ─────────────────────────────────────────────────────────────
# 4. CORRECTION AXES — ing_00964 var_00965 canneberge sucrée
#    Source dit "séchée sucrée" mais axe etat_thermique manquait
# ─────────────────────────────────────────────────────────────
ing_cann, _, _ = find_ing('ing_00964')
var_cann = find_var(ing_cann, 'var_00965')
var_cann['axes_fr']['etat_thermique'] = 'séché'
var_cann['axes_en']['thermal_state']  = 'dried'
log.append('FIX AXE  ing_00964 var_00965 → +etat_thermique: séché')

# ─────────────────────────────────────────────────────────────
# 5. CORRECTION AXES — ing_02343 var_02345 carotte
#    Source CIQUAL dit "déshydratée" mais axes étaient vides
# ─────────────────────────────────────────────────────────────
ing_car, _, _ = find_ing('ing_02343')
var_car = find_var(ing_car, 'var_02345')
var_car['axes_fr']['etat_thermique'] = 'déshydraté'
var_car['axes_en']['thermal_state']  = 'dehydrated'
log.append('FIX AXE  ing_02343 var_02345 → +etat_thermique: déshydraté')

# ─────────────────────────────────────────────────────────────
# 6. CORRECTION AXES — ing_02024 var_02025 cardamome
#    Source CNF dit "ground" mais axe forme manquait
# ─────────────────────────────────────────────────────────────
ing_card, _, _ = find_ing('ing_02024')
var_card = find_var(ing_card, 'var_02025')
var_card['axes_fr']['forme'] = 'poudre'
var_card['axes_en']['form']  = 'powder'
log.append('FIX AXE  ing_02024 var_02025 → +forme: poudre')

# ─────────────────────────────────────────────────────────────
# SAUVEGARDE
# ─────────────────────────────────────────────────────────────
json.dump(tree, open(TREE_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print('Operations effectuees :')
for l in log:
    print('  ' + l)
print()
print('OK.')
