import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
tree = json.load(open(BASE / 'ingredients_tree.json', encoding='utf-8'))

# Afficher toutes les cat2 avec leurs labels pour identifier les cibles
print('=== CATALOGUE cat1 / cat2 ===\n')
for cat1 in tree['categories']:
    print('CAT1 ' + cat1['id'] + '  [' + cat1.get('label','') + ']  label_fr=' + str(cat1.get('label_fr','')))
    for cat2 in cat1['subcategories']:
        nb = len(cat2.get('ingredient_groups', []))
        print('  cat2 ' + cat2['id'] + '  [' + cat2.get('label','') + ']  label_fr=' + str(cat2.get('label_fr','')) + '  (' + str(nb) + ' ing.)')
    print()
