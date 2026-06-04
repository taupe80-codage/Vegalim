#!/usr/bin/env python3
"""
merge_duplicates.py
Fusionne les ing_groups ayant le meme canonical_name_fr + memes axes_fr.

Phase 1 : 171 groupes intra-cat2 (fusion automatique, meme cat2)
Phase 2 :  9 cas cross-cat2 (deplacements + fusion)
           2 faux doublons ignores (citron vert lemons/limes, endive chicory/endives)
"""
import json, copy
from collections import defaultdict
from pathlib import Path

BASE = Path(r'C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\backend\data\ingredients')
TREE_FILE = BASE / 'ingredients_tree_enriched_v2.json'
tree = json.load(open(TREE_FILE, encoding='utf-8'))

log_merged = []
log_moved  = []

# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────
def build_index():
    """Retourne (all_ings, cat2_index)."""
    all_ings = []
    cat2_idx = {}
    for cat1 in tree['categories']:
        for cat2 in cat1['subcategories']:
            cat2_idx[cat2['id']] = cat2
            for ing in cat2.get('ingredient_groups', []):
                all_ings.append({
                    'id': ing['id'],
                    'name_fr': ing.get('canonical_name_fr', '').strip().lower(),
                    'axes_key': json.dumps(ing.get('axes_fr', {}), sort_keys=True, ensure_ascii=False),
                    'cat2_id': cat2['id'],
                    'cat2_label': cat2.get('label', ''),
                    'obj': ing,
                    'lst': cat2['ingredient_groups'],
                })
    return all_ings, cat2_idx

def merge_into(survivor, others):
    """Ajoute tous les variants de 'others' dans 'survivor', puis retire les 'others' de leurs listes."""
    for oth in others:
        for v in oth['obj'].get('variants', []):
            # Eviter doublons de variant_id
            existing_ids = {x['id'] for x in survivor['obj'].get('variants', [])}
            if v['id'] not in existing_ids:
                survivor['obj'].setdefault('variants', []).append(v)
        # Retirer l'ing de sa cat2
        oth['lst'][:] = [x for x in oth['lst'] if x['id'] != oth['id']]

def find_ing_by_id(ing_id):
    for cat1 in tree['categories']:
        for cat2 in cat1['subcategories']:
            for ing in cat2.get('ingredient_groups', []):
                if ing['id'] == ing_id:
                    return ing, cat2['ingredient_groups'], cat2
    return None, None, None

# ─────────────────────────────────────────────────────────────
# PHASE 1 : fusions intra-cat2
# ─────────────────────────────────────────────────────────────
all_ings, cat2_index = build_index()

groups = defaultdict(list)
for ing in all_ings:
    if not ing['name_fr']:
        continue
    key = (ing['name_fr'], ing['axes_key'], ing['cat2_id'])
    groups[key].append(ing)

intra = {k: v for k, v in groups.items() if len(v) > 1}

for (name_fr, axes_key, cat2_id), ings in sorted(intra.items(), key=lambda x: x[0][0]):
    # Survivant = celui avec le plus de variants, sinon le plus petit ID
    survivor = max(ings, key=lambda x: (x['obj'].get('nb_variants', len(x['obj'].get('variants', []))), -int(x['id'].split('_')[1])))
    others   = [i for i in ings if i['id'] != survivor['id']]
    other_ids = [o['id'] for o in others]
    merge_into(survivor, others)
    log_merged.append(f"MERGE  {survivor['id']} ({name_fr}) [{survivor['cat2_label']}]  <-- {', '.join(other_ids)}  ({len(survivor['obj'].get('variants',[]))} variants)")

# ─────────────────────────────────────────────────────────────
# PHASE 2 : cas cross-cat2
# Regle : on choisit la cat2 cible, on y deplace/fusionne
# ─────────────────────────────────────────────────────────────
# Rebuild index apres phase 1
all_ings2, cat2_index2 = build_index()
ing_by_id = {i['id']: i for i in all_ings2}

def move_and_merge(from_id, to_id):
    """Deplace les variants de from_id dans to_id, supprime from_id."""
    src = ing_by_id.get(from_id)
    dst = ing_by_id.get(to_id)
    if not src or not dst:
        print(f'  WARN: introuvable {from_id} ou {to_id}')
        return
    existing_ids = {v['id'] for v in dst['obj'].get('variants', [])}
    for v in src['obj'].get('variants', []):
        if v['id'] not in existing_ids:
            dst['obj'].setdefault('variants', []).append(v)
    src['lst'][:] = [x for x in src['lst'] if x['id'] != from_id]
    log_moved.append(f"MOVE+MERGE  {from_id} -> {to_id} ({dst['obj'].get('canonical_name_fr','')})")

def move_to_cat2(ing_id, target_cat2_id):
    """Deplace un ing_group entier vers une autre cat2."""
    src = ing_by_id.get(ing_id)
    if not src:
        print(f'  WARN: introuvable {ing_id}')
        return
    target_cat2 = cat2_index2.get(target_cat2_id)
    if not target_cat2:
        print(f'  WARN: cat2 introuvable {target_cat2_id}')
        return
    src['lst'][:] = [x for x in src['lst'] if x['id'] != ing_id]
    target_cat2['ingredient_groups'].append(src['obj'])
    log_moved.append(f"RELOCATE  {ing_id} ({src['obj'].get('canonical_name_fr','')}) -> cat2 {target_cat2_id} [{target_cat2.get('label','')}]")

# Rebuild ing_by_id apres reloc/merges pour chaque op
def refresh():
    global all_ings2, cat2_index2, ing_by_id
    all_ings2, cat2_index2 = build_index()
    ing_by_id = {i['id']: i for i in all_ings2}

# 1. banane plantain cuite : ing_00942 (bananas) -> ing_00930 (plantains)
move_and_merge('ing_00942', 'ing_00930')
refresh()

# 2. ble farine enrichie non blanchie : ing_00509 (breads) -> ing_00383 (wheat)
move_and_merge('ing_00509', 'ing_00383')
refresh()

# 3. cacahuete beurre : ing_04589 (peanuts) -> ing_04547 (nut_butters)
move_and_merge('ing_04589', 'ing_04547')
refresh()

# 4. carvi graine : ing_04595 (seeds) -> ing_04644 (caraway)
move_and_merge('ing_04595', 'ing_04644')
refresh()

# 5. cumin graine : ing_04604 (seeds) -> ing_04648 (cumin)
move_and_merge('ing_04604', 'ing_04648')
refresh()

# 6. fenugrec graine : ing_04606 (seeds) -> ing_04652 (fenugreek)
move_and_merge('ing_04606', 'ing_04652')
refresh()

# 7. pavot graine : ing_04618 (seeds) -> ing_04656 (poppy)
move_and_merge('ing_04618', 'ing_04656')
refresh()

# 8. fenouil graine : ing_02893 (herbs/fennel) -> ing_02891 (vegetables/fennel)
#    user veut -> seeds
#    Trouver la cat2 seeds
seeds_cat2_id = None
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        if cat2.get('label') == 'seeds':
            seeds_cat2_id = cat2['id']
            break

# ing_02893 est dans herbs, ing_02891 dans vegetables/fennel
# On fusionne les 2 dans l'un, puis on deplace vers seeds
move_and_merge('ing_02891', 'ing_02893')  # consolidation dans ing_02893
refresh()
move_to_cat2('ing_02893', seeds_cat2_id)  # relocalisation vers seeds
refresh()

# 9. pasteque crue : ing_01300 (melons) -> ing_01443 (watermelons)
move_and_merge('ing_01300', 'ing_01443')
refresh()

# ─────────────────────────────────────────────────────────────
# SAUVEGARDE
# ─────────────────────────────────────────────────────────────
json.dump(tree, open(TREE_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f'Phase 1 - Fusions intra-cat2 : {len(log_merged)} groupes fusionnes')
print(f'Phase 2 - Cas cross-cat2     : {len(log_moved)} operations')
print()
print('=== PHASE 1 (extrait) ===')
for l in log_merged[:10]:
    print(' ', l)
if len(log_merged) > 10:
    print(f'  ... +{len(log_merged)-10} autres')
print()
print('=== PHASE 2 ===')
for l in log_moved:
    print(' ', l)
print()
print('OK.')
