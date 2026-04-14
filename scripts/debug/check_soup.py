import json
with open('backend/data/recipes/recipes.json', 'r', encoding='utf-8') as f:
    db = json.load(f)
for r in db['recipes']:
    if r['id'] == 'soup_onion_french_classic_v3_t9k2m4':
        print(f"Servings: {r.get('servings')}")
        for c in r.get('composition', []):
            print(f"  {c.get('ingredient')}: {c.get('quantity')} {c.get('unit')}")
