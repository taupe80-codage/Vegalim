import json
with open('backend/data/recipes/recipes.json', 'r', encoding='utf-8') as f:
    db = json.load(f)
for r in db['recipes'][:20]:
    print(f"{r['id']} => {r.get('diet_flags')}")
