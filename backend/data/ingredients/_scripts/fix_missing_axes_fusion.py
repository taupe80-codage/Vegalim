#!/usr/bin/env python3
"""
fix_missing_axes_fusion.py
Ajoute les axes manquants identifies lors de l'analyse des 239 "fusions suspectes"
(audit_tree_coherence.py, section 8) pour 4 groupes ou une vraie distinction produit
etait masquee derriere des axes_fr identiques :

- ing_04859 beurre       : CIQUAL:16404 est un beurre "tendre" (a tartiner), distinct
                            du beurre standard (CIQUAL:16400 / CNF:92)
- ing_05087 emmental      : CIQUAL:12118 est rape, distinct du bloc (CIQUAL:12115 / USDA)
- ing_04255 pois chiches  : CNF:502262 est egoutte ET rince, distinct du simple egoutte
                            (CIQUAL:20532 / CNF:502261) -- impact reel sur le sodium
- ing_00188 capres        : CIQUAL:11040 est au vinaigre, CNF:4890 est en saumure
                            (conserve/brine) -- sodium tres different (1620 vs 2348mg)

Le 5e cas (ing_04555 sesame/tahini) est laisse de cote : la divergence de sodium
entre CNF:2598 (~1mg) et les 2 autres (~75mg) n'est appuyee par aucune mention
explicite "sale/non sale" dans les source_name -- necessite une verification manuelle
avant d'inventer un axe.
"""
import json
from pathlib import Path

BASE = Path(r'C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\backend\data\ingredients')
TREE_FILE = BASE / 'ingredients_tree.json'

tree = json.load(open(TREE_FILE, encoding='utf-8'))

FIXES = [
    ('var_04862', {'forme': 'tendre'}, {'form': 'spreadable'}),
    ('var_05114', {'forme': 'râpé'}, {'form': 'grated'}),
    ('var_05840', {'traitement': 'rincé'}, {'treatment': 'rinsed'}),
    ('var_00212', {'milieu_conservation': 'au vinaigre'}, {'draining': 'in_vinegar'}),
    ('var_00189', {'milieu_conservation': 'en saumure'}, {'draining': 'brined'}),
]
fix_map = {vid: (afr, aen) for vid, afr, aen in FIXES}

applied = []
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        for ing in cat2.get('ingredient_groups', []):
            for v in ing.get('variants', []):
                if v['id'] in fix_map:
                    afr, aen = fix_map[v['id']]
                    v['axes_fr'] = {**v.get('axes_fr', {}), **afr}
                    v['axes_en'] = {**v.get('axes_en', {}), **aen}
                    applied.append((ing['id'], v['id'], afr, aen))

assert len(applied) == len(FIXES), f"Attendu {len(FIXES)} fixes, {len(applied)} appliques"

print(f'{len(applied)} variantes corrigees :')
for ing_id, vid, afr, aen in applied:
    print(f'  {ing_id} / {vid} -> axes_fr+={afr} axes_en+={aen}')

TREE_FILE.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\nTree mis a jour : {TREE_FILE}')
