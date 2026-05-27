"""
patch_v32_remap_empty_groups.py
================================
Lit le rapport v32_empty_groups_remap.json et applique les corrections :
  - Groupes récupérables : ajouter un variant avec le vrai source_id
  - Groupes irrécupérables (4) : supprimer le groupe de v32
"""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT     = Path(__file__).parents[2]
DATA     = ROOT / 'backend/data'
V32_PATH = DATA / 'ingredients/ingredients_v32.json'
REPORT   = DATA / 'nutrition/logs/v32_empty_groups_remap.json'

report = json.loads(REPORT.read_text(encoding='utf-8'))
v32    = json.loads(V32_PATH.read_text(encoding='utf-8'))

# ── Construire les mappings ig_id → action ─────────────────────────────────────
# Pour chaque groupe récupérable, choisir CIQUAL en priorité, sinon CNF
remap: dict = {}   # ig_id → {'source': 'CIQUAL'|'CNF', 'source_id': int}
for r in report['recoverable']:
    ig_id = r['ig_id']
    if r.get('ciq_id'):
        remap[ig_id] = {'source': 'CIQUAL', 'source_id': r['ciq_id']}
    elif r.get('cnf_id'):
        remap[ig_id] = {'source': 'CNF',    'source_id': r['cnf_id']}

to_delete = {r['ig_id'] for r in report['unrecoverable']}

print(f'Remappages prévus  : {len(remap)}')
print(f'Suppressions prévues : {len(to_delete)}')
print()

stats = {'remapped': 0, 'deleted_groups': 0, 'skipped': 0}
log = []

# Générer des IDs de variant déterministes
def make_vr_id(ig_id: str, src: str) -> str:
    num = ig_id.replace('ing_', '')
    return f"var_{num}_remap_{src.lower()}"

cats = v32.get('categories', [])
new_cats = []
for cat in cats:
    new_subs = []
    for sub in cat.get('subcategories', []):
        new_groups = []
        for ig in sub.get('ingredient_groups', []):
            ig_id = ig.get('id', '')

            # ── Suppression ──────────────────────────────────────────────────
            if ig_id in to_delete:
                log.append(f'  DELETE  {ig_id}  ({ig.get("canonical_name_en","")})')
                stats['deleted_groups'] += 1
                continue  # ne pas garder ce groupe

            # ── Remap ─────────────────────────────────────────────────────────
            if ig_id in remap and not ig.get('variants'):
                mapping = remap[ig_id]
                src     = mapping['source']
                sid     = mapping['source_id']
                # Créer un variant minimal avec le vrai ID
                new_variant = {
                    'id':        make_vr_id(ig_id, src),
                    'source':    src,
                    'source_id': sid,
                    'name_fr':   ig.get('canonical_name_fr', ''),
                    'name_en':   ig.get('canonical_name_en', ''),
                    'axes':      {},
                }
                ig['variants'] = [new_variant]
                log.append(f'  REMAP   {ig_id}  → {src}#{sid}  ({ig.get("canonical_name_en","")})')
                stats['remapped'] += 1

            new_groups.append(ig)

        sub['ingredient_groups'] = new_groups
        new_subs.append(sub)
    cat['subcategories'] = new_subs
    new_cats.append(cat)

v32['categories'] = new_cats

# ── Rapport ────────────────────────────────────────────────────────────────────
print('=' * 60)
print('PATCH REMAP GROUPES VIDES')
print('=' * 60)
print(f'  Remappés  : {stats["remapped"]}')
print(f'  Supprimés : {stats["deleted_groups"]}')
print()
print('── Actions ──────────────────────────────────────────────────')
for line in log:
    print(line)

V32_PATH.write_text(json.dumps(v32, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n  ✅ ingredients_v32.json mis à jour')
