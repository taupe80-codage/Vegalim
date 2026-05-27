"""
compare_n2_versions.py — Diff nutrition_v2.json (ancien) vs nutrition_v2_rebuilt.json (nouveau)
================================================================================================
Vérifie :
  1. Clés présentes dans l'ancien mais absentes du nouveau (RÉGRESSIONS)
  2. Clés présentes dans le nouveau mais pas dans l'ancien (NOUVEAUTÉS)
  3. Clés communes — différences de valeurs nutritives (calories, protéines)
  4. Couverture des recettes : toutes les nutrition_key utilisées sont-elles présentes ?
"""
import json, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

ROOT   = Path(__file__).parents[2]
DATA   = ROOT / 'backend/data'
OLD    = DATA / 'nutrition/processed/nutrition_v2.json'
NEW    = DATA / 'nutrition/processed/nutrition_v2_rebuilt.json'
DICT   = DATA / 'ingredients/ingredients_dictionary.json'
LOG    = DATA / 'nutrition/logs/compare_n2_versions.json'
LOG.parent.mkdir(parents=True, exist_ok=True)

print('Chargement...')
old_data = json.loads(OLD.read_text(encoding='utf-8'))
new_data = json.loads(NEW.read_text(encoding='utf-8'))

old_ing = old_data.get('ingredients', old_data)
new_ing = new_data.get('ingredients', new_data)

old_keys = set(old_ing.keys())
new_keys = set(new_ing.keys())

print(f'  Ancien : {len(old_keys)} bases')
print(f'  Nouveau: {len(new_keys)} bases')
print()

# ── 1. Régressions (dans l'ancien, pas dans le nouveau) ───────────────────────
regressions = sorted(old_keys - new_keys)

# ── 2. Nouveautés (dans le nouveau, pas dans l'ancien) ────────────────────────
nouveautes = sorted(new_keys - old_keys)

# ── 3. Diff valeurs nutritives sur clés communes ──────────────────────────────
common = old_keys & new_keys
nutr_diffs = []
FIELDS_CHECK = ['calories_kcal', 'protein_g', 'carbs_g', 'fat_g', 'fiber_g']

def get_main_variant_nutr(base: dict) -> dict:
    """Extrait les nutriments du premier variant principal d'une base."""
    variants = base.get('variants', {})
    if not variants:
        # Ancienne structure plate
        return base
    # Prendre le variant 'default' ou le premier
    vr = variants.get('default') or next(iter(variants.values()), {})
    return vr

for key in sorted(common):
    old_nutr = get_main_variant_nutr(old_ing[key])
    new_nutr = get_main_variant_nutr(new_ing[key])
    diffs = {}
    for f in FIELDS_CHECK:
        ov = old_nutr.get(f)
        nv = new_nutr.get(f)
        if ov is None and nv is None:
            continue
        if ov is None or nv is None:
            diffs[f] = {'old': ov, 'new': nv, 'delta': None}
        else:
            delta = abs(float(nv) - float(ov))
            pct   = delta / float(ov) * 100 if float(ov) != 0 else 0
            if pct > 10:   # divergence > 10%
                diffs[f] = {'old': round(float(ov),2), 'new': round(float(nv),2),
                             'delta_pct': round(pct,1)}
    if diffs:
        nutr_diffs.append({'key': key, 'diffs': diffs})

# ── 4. Couverture recettes ─────────────────────────────────────────────────────
dict_data  = json.loads(DICT.read_text(encoding='utf-8'))
all_nutr_keys = set()
for entry in dict_data.values() if isinstance(dict_data, dict) else []:
    nk = entry.get('nutrition_key') if isinstance(entry, dict) else None
    if nk and not nk.startswith('__'):
        # base_key est avant le premier '/' si il y a un variant
        base = nk.split('/')[0] if '/' in nk else nk
        all_nutr_keys.add(base)

missing_from_new  = sorted(all_nutr_keys - new_keys)
missing_from_old  = sorted(all_nutr_keys - old_keys)

# ── RAPPORT ────────────────────────────────────────────────────────────────────
print('=' * 65)
print('DIFF nutrition_v2  (ancien)  vs  nutrition_v2_rebuilt  (nouveau)')
print('=' * 65)
print()
print(f'  Régressions (ancien → absent du nouveau) : {len(regressions)}')
print(f'  Nouveautés  (nouveau → absent de l\'ancien): {len(nouveautes)}')
print(f'  Divergences nutritives (>10%)            : {len(nutr_diffs)}')
print(f'  Clés recettes manquantes dans NOUVEAU    : {len(missing_from_new)}')
print(f'  Clés recettes manquantes dans ANCIEN     : {len(missing_from_old)}')
print()

print('── RÉGRESSIONS (clés perdues) ────────────────────────────────')
if regressions:
    for k in regressions[:40]:
        # Chercher si une clé similaire existe dans le nouveau
        similar = [nk for nk in new_keys if k.split('_')[0] in nk][:2]
        hint = f'  → similaire: {similar}' if similar else ''
        print(f'  ✗ {k}{hint}')
    if len(regressions) > 40:
        print(f'  ... et {len(regressions)-40} autres')
else:
    print('  ✅ Aucune régression')

print()
print('── CLÉS RECETTES MANQUANTES DANS LE NOUVEAU ─────────────────')
if missing_from_new:
    for k in missing_from_new[:30]:
        similar = [nk for nk in new_keys if k.split('_')[0] in nk][:2]
        hint = f'  → {similar}' if similar else ''
        print(f'  ⚠️  {k}{hint}')
else:
    print('  ✅ Toutes les clés recettes présentes dans le nouveau')

print()
print('── DIVERGENCES NUTRITIVES (>10%) ─────────────────────────────')
if nutr_diffs:
    for item in nutr_diffs[:25]:
        print(f"  {item['key']}")
        for f, d in item['diffs'].items():
            if d.get('delta_pct') is not None:
                print(f"    {f}: {d['old']} → {d['new']}  ({d['delta_pct']}%)")
            else:
                print(f"    {f}: {d['old']} → {d['new']}  (l'un est null)")
else:
    print('  ✅ Aucune divergence nutritive majeure')

print()
print('── NOUVEAUTÉS (top 20) ───────────────────────────────────────')
for k in nouveautes[:20]:
    print(f'  + {k}')
if len(nouveautes) > 20:
    print(f'  ... et {len(nouveautes)-20} autres')

# Export
LOG.write_text(json.dumps({
    'summary': {
        'old_bases': len(old_keys), 'new_bases': len(new_keys),
        'regressions': len(regressions), 'nouveautes': len(nouveautes),
        'nutr_diffs': len(nutr_diffs),
        'recipe_keys_missing_new': len(missing_from_new),
        'recipe_keys_missing_old': len(missing_from_old),
    },
    'regressions': regressions,
    'nouveautes': nouveautes[:100],
    'nutr_diffs': nutr_diffs[:50],
    'recipe_keys_missing_new': missing_from_new,
    'recipe_keys_missing_old': missing_from_old,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n  Rapport complet → {LOG}')
