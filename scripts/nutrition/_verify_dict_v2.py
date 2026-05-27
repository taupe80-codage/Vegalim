"""Vérifie la structure du dictionnaire v2 et affiche des exemples."""
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
d = json.loads(Path('backend/data/ingredients/ingredients_dictionary_v2.json').read_text(encoding='utf-8'))
print('Schema:')
print(json.dumps(d['_schema'], ensure_ascii=False, indent=2))
print()

multi = []
for cat_label, cat in d['categories'].items():
    for sub_label, sub in cat['subcategories'].items():
        for ig_key, ig in sub['ingredient_groups'].items():
            n = len(ig.get('variants', {}))
            if n >= 2:
                multi.append((n, cat_label, sub_label, ig_key, ig))

multi.sort(reverse=True)
print(f'Groupes multi-variants (>=2) : {len(multi)}')
print()

if multi:
    n, cat_label, sub_label, ig_key, ig = multi[0]
    print(f'EXEMPLE le plus riche ({n} variants):')
    print(f'  CAT: {cat_label}')
    print(f'  SUB: {sub_label}')
    print(f'  IG : {ig_key}')
    print(json.dumps(ig, ensure_ascii=False, indent=2))
