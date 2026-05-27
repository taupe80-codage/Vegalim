"""
deep_diff_n2.py — Analyse approfondie des divergences nutritives et des régressions
"""
import json, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

ROOT  = Path(__file__).parents[2]
DATA  = ROOT / 'backend/data'
OLD   = DATA / 'nutrition/processed/nutrition_v2.json'
NEW   = DATA / 'nutrition/processed/nutrition_v2_rebuilt.json'
DICT  = DATA / 'ingredients/ingredients_dictionary.json'

old_data = json.loads(OLD.read_text(encoding='utf-8'))
new_data = json.loads(NEW.read_text(encoding='utf-8'))
dict_data = json.loads(DICT.read_text(encoding='utf-8'))

old_ing = old_data.get('ingredients', old_data)
new_ing = new_data.get('ingredients', new_data)

# Toutes les base_keys référencées dans le dictionnaire
dict_nutrition_keys = set()
for entry in (dict_data.values() if isinstance(dict_data, dict) else []):
    if not isinstance(entry, dict): continue
    nk = entry.get('nutrition_key','')
    if nk and not nk.startswith('__'):
        base = nk.split('/')[0]
        dict_nutrition_keys.add(base)

# ── Régressions → catégoriser ─────────────────────────────────────────────────
old_keys = set(old_ing.keys())
new_keys = set(new_ing.keys())
regressions = sorted(old_keys - new_keys)

in_dict    = [k for k in regressions if k in dict_nutrition_keys]
not_in_dict = [k for k in regressions if k not in dict_nutrition_keys]

# Pour chaque régression dans le dict, trouver son remplaçant potentiel
replacements = {}
for k in in_dict:
    stem = k.split('_')[0]
    candidates = [nk for nk in new_keys if nk.startswith(stem)][:3]
    replacements[k] = candidates

# ── Divergences → analyser la cause ───────────────────────────────────────────
FIELDS = ['calories_kcal','protein_g','carbs_g','fat_g','fiber_g']

def get_best_variant(base: dict) -> tuple[str, dict]:
    """Retourne (vr_key, nutriments) du variant le plus probable (default ou raw ou premier)."""
    variants = base.get('variants', {})
    if not variants:
        return 'flat', base
    for pref in ('default', 'raw', 'fresh', 'whole'):
        if pref in variants:
            return pref, variants[pref]
    return next(iter(variants.items()))

serious_diffs = []
for key in sorted(old_keys & new_keys):
    old_vr_key, old_nutr = get_best_variant(old_ing[key])
    new_vr_key, new_nutr = get_best_variant(new_ing[key])
    issues = []
    for f in FIELDS:
        ov = old_nutr.get(f)
        nv = new_nutr.get(f)
        if ov is None or nv is None: continue
        pct = abs(float(nv)-float(ov)) / max(abs(float(ov)),0.001) * 100
        if pct > 20:
            issues.append((f, round(float(ov),2), round(float(nv),2), round(pct,1)))
    if issues:
        new_src   = new_nutr.get('_source','?')
        new_sid   = new_nutr.get('_source_id','?')
        new_name  = new_nutr.get('name_fr','') or new_nutr.get('name_en','')
        serious_diffs.append({
            'key': key, 'old_vr': old_vr_key, 'new_vr': new_vr_key,
            'src': new_src, 'sid': new_sid, 'name': new_name[:55],
            'issues': issues,
        })

# Trier par sévérité (nb champs divergents × amplitude max)
serious_diffs.sort(key=lambda x: -len(x['issues']))

# ── RAPPORT CONSOLE ────────────────────────────────────────────────────────────
print('=' * 68)
print('DIFF APPROFONDI — nutrition_v2 (ancien) vs nutrition_v2_rebuilt')
print('=' * 68)
print()
print(f'  Régressions totales           : {len(regressions)}')
print(f'    dont référencées en recette : {len(in_dict)}  ← CRITIQUES')
print(f'    dont non référencées        : {len(not_in_dict)}  (inactives)')
print(f'  Divergences nutritives (>20%) : {len(serious_diffs)}')
print()

print('── RÉGRESSIONS CRITIQUES (dans le dictionnaire) ────────────────')
if in_dict:
    for k in in_dict:
        cands = replacements.get(k, [])
        print(f'  ✗ {k:<35} → candidats: {cands}')
else:
    print('  ✅ Aucune — toutes les clés recettes sont couvertes')

print()
print('── RÉGRESSIONS INACTIVES (hors dictionnaire — top 30) ──────────')
for k in not_in_dict[:30]:
    print(f'  – {k}')
if len(not_in_dict) > 30:
    print(f'  ... et {len(not_in_dict)-30} autres (toutes inactives)')

print()
print('── DIVERGENCES NUTRITIVES SÉRIEUSES (>20%) ─────────────────────')
print(f'  {"Clé":<30} {"Src":<8} {"ID":>8}  {"Nom source":<40}')
print(f'  {"-"*30} {"-"*8} {"-"*8}  {"-"*40}')
for d in serious_diffs:
    print(f"  {d['key']:<30} {d['src']:<8} {str(d['sid']):>8}  {d['name']}")
    for f, ov, nv, pct in d['issues']:
        flag = '🔴' if pct > 100 else '🟠' if pct > 50 else '🟡'
        print(f"    {flag} {f:<22}: {ov:>8} → {nv:>8}  ({pct}%)")

# Export JSON complet
LOG = DATA / 'nutrition/logs/deep_diff_n2.json'
LOG.write_text(json.dumps({
    'regressions_in_dict':    in_dict,
    'regressions_not_in_dict': not_in_dict,
    'regression_replacements': replacements,
    'serious_diffs':          serious_diffs,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n  Rapport JSON → {LOG}')
