#!/usr/bin/env python3
"""
merge_fusion_suspecte.py
Fusionne les variantes d'un meme ing_ qui partagent des axes_fr identiques
(candidates "fusion suspecte" -- audit_tree_coherence.py section 8).

A executer APRES fix_missing_axes_fusion.py (qui a differencie les 4 groupes
ou une vraie distinction produit existait). Reprend le pattern deja utilise par
scripts/ingredients/migrate_axes.py (67 fusions en 2026-05-24) : priorite source
CIQUAL > USDA > CNF pour la variante primaire conservee, les autres sources sont
gardees dans un tableau `sources` de tracabilite (rien n'est perdu).

ing_04555 (sesame/tahini) est exclu : divergence de sodium non expliquee par les
source_name, necessite une verification manuelle avant fusion.
"""
import json
from pathlib import Path
from collections import defaultdict

BASE = Path(r'C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\backend\data\ingredients')
TREE_FILE = BASE / 'ingredients_tree.json'

tree = json.load(open(TREE_FILE, encoding='utf-8'))

SOURCE_PRIORITY = {'CIQUAL': 0, 'USDA': 1, 'CNF': 2}
SKIP_ING_IDS = set()   # ing_04555 (tahini) differencie via assaisonnement=sans sel, plus besoin d'exclusion

groups_merged = []
variants_removed = 0

for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        for ing in cat2.get('ingredient_groups', []):
            if ing['id'] in SKIP_ING_IDS:
                continue
            variants = ing.get('variants', [])
            if len(variants) <= 1:
                continue

            fp_groups = defaultdict(list)
            for v in variants:
                fp = str(sorted(v.get('axes_fr', {}).items()))
                fp_groups[fp].append(v)

            new_variants = []
            group_had_merge = False
            for fp, vs in fp_groups.items():
                if len(vs) == 1:
                    new_variants.append(vs[0])
                    continue

                vs_sorted = sorted(vs, key=lambda v: SOURCE_PRIORITY.get(v.get('source', ''), 99))
                primary = dict(vs_sorted[0])
                primary['sources'] = [
                    {'source': v.get('source', ''), 'source_id': v.get('source_id', '')}
                    for v in vs_sorted
                ]
                primary['is_primary'] = True
                new_variants.append(primary)

                group_had_merge = True
                variants_removed += len(vs) - 1
                groups_merged.append({
                    'ing_id': ing['id'],
                    'name': ing.get('canonical_name_fr'),
                    'kept': primary['id'],
                    'kept_source': f"{primary.get('source')}:{primary.get('source_id')}",
                    'removed': [f"{v['id']} ({v.get('source')}:{v.get('source_id')})" for v in vs_sorted[1:]],
                })

            if group_had_merge:
                ing['variants'] = new_variants

print(f'Groupes fusionnes    : {len(groups_merged)}')
print(f'Variantes supprimees : {variants_removed}')
print()
for g in groups_merged:
    print(f"  {g['ing_id']:12} {g['name']:35} garde={g['kept']} ({g['kept_source']})  <- {', '.join(g['removed'])}")

TREE_FILE.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\nTree mis a jour : {TREE_FILE}')
