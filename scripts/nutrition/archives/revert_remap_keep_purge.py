"""
revert_remap_keep_purge.py
===========================
Revient en arrière sur patch_v32_remap_empty_groups.py :
  - Restore le v32 APRÈS la purge des IDs synthétiques (bon)
  - Annule les remaps par similarité de nom (mauvais → erreurs)
  - Les groupes sans variant restent vides (honnêtes)

Utilise le backup créé avant les patchs (ingredients_v32.bak.json)
OU repart du v32 actuel en retirant les variants "_remap_" injectés.
"""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT     = Path(__file__).parents[2]
DATA     = ROOT / 'backend/data'
V32_PATH = DATA / 'ingredients/ingredients_v32.json'
BAK_PATH = DATA / 'ingredients/ingredients_v32.bak.json'

# Le backup contient le v32 d'avant tous les patchs de cette session.
# On va retirer uniquement les variants injectés par le remap (id contient "_remap_")
# et les IDs synthétiques (CNF >= 500000)

v32 = json.loads(V32_PATH.read_text(encoding='utf-8'))

stats = {'removed_remap': 0, 'removed_synthetic': 0, 'kept': 0, 'empty_groups': 0}

for cat in v32.get('categories', []):
    for sub in cat.get('subcategories', []):
        for ig in sub.get('ingredient_groups', []):
            new_variants = []
            for vr in ig.get('variants', []):
                vr_id  = vr.get('id', '')
                src    = (vr.get('source') or '').upper()
                sid    = vr.get('source_id')

                # Retirer les variants injectés par le remap
                if '_remap_' in vr_id:
                    stats['removed_remap'] += 1
                    continue

                # Retirer les IDs synthétiques CNF restants (>= 500000)
                if src == 'CNF' and sid is not None:
                    try:
                        if int(sid) >= 500000:
                            stats['removed_synthetic'] += 1
                            continue
                    except (ValueError, TypeError):
                        pass

                new_variants.append(vr)
                stats['kept'] += 1

            ig['variants'] = new_variants
            if not new_variants:
                stats['empty_groups'] += 1

print('=' * 60)
print('REVERT REMAP — état propre post-purge')
print('=' * 60)
print(f'  Variants remap retirés    : {stats["removed_remap"]}')
print(f'  Variants synthétiques CNF : {stats["removed_synthetic"]}')
print(f'  Variants conservés        : {stats["kept"]}')
print(f'  Groupes sans variant      : {stats["empty_groups"]}')

V32_PATH.write_text(json.dumps(v32, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n  ✅ ingredients_v32.json — état post-purge sans remap')
