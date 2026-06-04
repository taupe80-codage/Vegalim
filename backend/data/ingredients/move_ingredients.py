#!/usr/bin/env python3
"""
move_ingredients.py
Deplace des ing_ vers les bonnes cat2.
"""
import json, copy
from pathlib import Path

BASE = Path(r'C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\backend\data\ingredients')
TREE_FILE = BASE / 'ingredients_tree_enriched_v2.json'
tree = json.load(open(TREE_FILE, encoding='utf-8'))

# ing_id -> cat2_id cible
MOVES = {
    'ing_00962': 'cat2_03764',   # haricot canneberge -> legumineuses > haricots
    'ing_00111': 'cat2_00043',   # meloukhia -> legumes > salades/feuilles
    'ing_02400': 'cat2_03414',   # crosses de fougeres -> legumes > pousses de bambou
    'ing_00615': 'cat2_04592',   # caroube farine -> noix & graines > graines
    'ing_03038': 'cat2_02995',   # pates de mais cuites -> legumes > mais
    'ing_03040': 'cat2_02995',   # pates de mais seches -> legumes > mais
}

# Indexer cat2 par id
cat2_map = {}
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        cat2_map[cat2['id']] = cat2

# Extraire les ing a deplacer
to_move = {}  # ing_id -> ing_obj
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        remaining = []
        for ing in cat2.get('ingredient_groups', []):
            if ing['id'] in MOVES:
                to_move[ing['id']] = (ing, cat2['id'], cat2.get('label',''), cat1.get('label',''))
            else:
                remaining.append(ing)
        cat2['ingredient_groups'] = remaining

# Inserer dans les cat2 cibles
moved = []
for ing_id, (ing, from_cat2, from_label, from_cat1) in to_move.items():
    target_cat2_id = MOVES[ing_id]
    target_cat2 = cat2_map.get(target_cat2_id)
    if not target_cat2:
        print('ERREUR : cat2 cible introuvable ' + target_cat2_id)
        continue
    target_cat2['ingredient_groups'].append(ing)
    moved.append(
        ing_id + '  ' + ing.get('canonical_name_fr','') +
        '\n    de : ' + from_cat1 + ' > ' + from_label +
        '\n    vers: ' + target_cat2_id + ' [' + target_cat2.get('label','') + ']'
    )

print('Ingredients deplaces : ' + str(len(moved)))
for m in moved:
    print('  ' + m)
    print()

json.dump(tree, open(TREE_FILE, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
print('OK.')
