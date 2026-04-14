import json

with open('backend/data/recipes/recipes.json', 'r', encoding='utf-8') as f:
    r_dict = json.load(f)

for rid in ['dip_baba_ghanoush_dbd030', 'dal_ajapsandali_8ebefc', 'couscous_couscous_tfaya_ee5f20', 'rice_bibimbap_classic_k91x2a']:
    if rid in r_dict:
        r = r_dict[rid]
        print(f'\n--- {rid} (Servings: {r.get("servings", "?")}) ---')
        for c in r.get('composition', []):
            if c.get('ingredient') in ['garlic', 'onion', 'carrot', 'egg', 'potato']:
                print(f"  {c['ingredient']}: {c.get('quantity')} {c.get('unit')}")
