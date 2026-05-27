"""Analyse le taux de couverture des métadonnées entre l'ancien dict et le dict v2."""
import json, sys
from pathlib import Path
from collections import defaultdict
sys.stdout.reconfigure(encoding='utf-8')

ROOT  = Path(__file__).parents[2]
DATA  = ROOT / 'backend/data'

dold = json.loads((DATA / 'ingredients/ingredients_dictionary.json').read_text(encoding='utf-8'))
dv2  = json.loads((DATA / 'ingredients/ingredients_dictionary_v2.json').read_text(encoding='utf-8'))

old_ing = {e['id']: e for e in dold.get('ingredients', [])}

# Index des groupes v2 → quels champs méta sont présents
fields = ('diet_profile', 'allergens_eu', 'nova_group', 'culinary', 'bioavailability_protein')
coverage = defaultdict(int)
total_groups = 0

examples_missing = []

for cat in dv2['categories'].values():
    for sub in cat['subcategories'].values():
        for ig_key, ig in sub['ingredient_groups'].items():
            total_groups += 1
            has_any = any(ig.get(f) for f in fields)
            if has_any:
                for f in fields:
                    if ig.get(f) is not None:
                        coverage[f] += 1
            else:
                examples_missing.append(ig_key)

print(f'Total groupes v2       : {total_groups}')
print(f'Groupes avec >=1 méta  : {sum(1 for cat in dv2["categories"].values() for sub in cat["subcategories"].values() for ig in sub["ingredient_groups"].values() if any(ig.get(f) for f in fields))}')
print()
print('Couverture par champ :')
for f in fields:
    pct = coverage[f] / total_groups * 100
    print(f'  {f:<35} : {coverage[f]:>4} / {total_groups}  ({pct:.1f}%)')
print()

# Taux de correspondance possible : ancien dict → v2
# via nutrition_key base → entry_key
v2_all_keys = {ig_key for cat in dv2['categories'].values()
               for sub in cat['subcategories'].values()
               for ig_key in sub['ingredient_groups']}

# combien d'entrées old_ing ont un id ou nk_base dans v2_all_keys
matchable = 0
total_old = len(old_ing)
for name, e in old_ing.items():
    nk = e.get('nutrition_key', '')
    nk_base = nk.split('/')[0] if nk else ''
    if name in v2_all_keys or nk_base in v2_all_keys:
        matchable += 1

print(f'Entrées ancien dict matchables dans v2 : {matchable} / {total_old}')
print()
print(f'Exemples groupes v2 sans méta (top 20) :')
for k in examples_missing[:20]:
    print(f'  {k}')
