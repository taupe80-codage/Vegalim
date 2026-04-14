
import json
import os

with open('backend/data/recipes/recipes.json', 'r', encoding='utf-8') as f:
    db = json.load(f)

with open('backend/data/ingredients/ingredient_physical.json', 'r', encoding='utf-8') as f:
    phys = json.load(f)

changes = 0
for r in db['recipes']:
    for c in r.get('composition', []):
        u = c.get('unit')
        ing = c.get('ingredient')
        
        if u in ['piece', 'gousse']:
            # Find the equivalent weight in grams
            try:
                g_val = phys[ing]['units'][u]['g']
            except KeyError:
                continue # safeguard
                
            qty = c.get('quantity', 0)
            c['quantity'] = round(qty * g_val)
            c['unit'] = 'g'
            changes += 1

with open('backend/data/recipes/recipes.json', 'w', encoding='utf-8') as f:
    json.dump(db, f, indent=2, ensure_ascii=False)

print(f'Done! Converted {changes} non-SI units into grams.')

