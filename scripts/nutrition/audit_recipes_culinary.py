import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / 'backend' / 'data'

def load_json(p):
    with open(p, 'r', encoding='utf-8') as f:
        return json.load(f)

db = load_json(DATA / 'recipes' / 'recipes.json')
recipes = db.get('recipes', [])
vegan_index = load_json(DATA / 'config' / 'vegan_variants_index.json')

anomalies = []

# 1. Verification du poids total par portion
for r in recipes:
    servings = r.get('servings', 1)
    if servings <= 0: servings = 1
    
    total_g = 0
    for c in r.get('composition', []):
        q = c.get('quantity', 0)
        u = c.get('unit', '')
        if u in ['g', 'ml']:
            total_g += q
    
    poids_par_portion = total_g / servings
    rt = r.get('recipe_type', 'main')
    
    # Plats principaux : si c'est < 150g ou > 1000g, c'est étrange
    if rt == 'main':
        if poids_par_portion < 150:
            anomalies.append(('POIDS TROP FAIBLE', r['id'], f'{poids_par_portion:.1f}g / pers'))
        elif poids_par_portion > 1200:
            anomalies.append(('POIDS TROP ELEVE', r['id'], f'{poids_par_portion:.1f}g / pers'))

# 2. Vérification d'assaisonnements ou ingrédients extrêmes
for r in recipes:
    servings = r.get('servings', 1)
    if servings <= 0: servings = 1
    
    for c in r.get('composition', []):
        ing = c.get('ingredient', '')
        q = c.get('quantity', 0)
        u = c.get('unit', '')
        
        if u == 'g':
            q_per_serving = q / servings
            if ing == 'garlic' and q_per_serving > 15: # 3 gousses/pers
                anomalies.append(('EXCES', r['id'], f'Ail: {q_per_serving:.1f}g / pers'))
            if ing == 'salt' and q_per_serving > 5: # 5g de sel = très salé
                anomalies.append(('EXCES', r['id'], f'Sel: {q_per_serving:.1f}g / pers'))
            if ing == 'egg' and q_per_serving > 200: # 4 oeufs / pers = massif
                anomalies.append(('EXCES', r['id'], f'Oeuf: {q_per_serving:.1f}g / pers'))

print(f"--- RAPPORT D'AUDIT CULINAIRE ---")
print(f"Recettes analysées : {len(recipes)}")
print(f"Anomalies de Poids : {sum(1 for a in anomalies if 'POIDS' in a[0])}")
print(f"Anomalies d'Assaisonnement : {sum(1 for a in anomalies if 'EXCES' in a[0])}")

print("\n--- ÉCHANTILLON D'ANOMALIES (Top 30) ---")
for a in anomalies[:30]:
    print(f"[{a[0]}] {a[1]} -> {a[2]}")

print("\n--- SUBSTITUTIONS VEGAN EFFECTUEES ---")
subs_freq = {}
for v_data in vegan_index.get('original_to_vegan', {}).values():
    for k, v in v_data.get('subs', {}).items():
        pair = f"{k} -> {v}"
        subs_freq[pair] = subs_freq.get(pair, 0) + 1

for pair, count in sorted(subs_freq.items(), key=lambda x: -x[1])[:10]:
    print(f"{count}x : {pair}")
