"""Audit complétude des champs nutritionnels dans nutrition_v2.json."""
import json, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

ROOT = Path(__file__).parents[2]
N2   = ROOT / 'backend/data/nutrition/processed/nutrition_v2.json'

data = json.loads(N2.read_text(encoding='utf-8'))
ing  = data.get('ingredients', {})

# Champs nutritionnels obligatoires (EU 1169/2011 — étiquetage minimal)
MANDATORY = ['calories_kcal', 'protein_g', 'carbs_g', 'fat_g', 'fiber_g', 'sugar_g', 'fa_saturated_g', 'sodium_mg']
# Champs enrichis (souhaitables mais non obligatoires)
ENRICHED  = ['iron_mg', 'calcium_mg', 'vitamin_c_mg', 'vitamin_d_ug', 'potassium_mg',
             'magnesium_mg', 'zinc_mg', 'vitamin_b12_ug', 'folate_ug', 'omega3_g']

# Profils de complétude
LEVELS = {
    'complet':   lambda m, e: m == 8 and e >= 7,
    'standard':  lambda m, e: m == 8 and e >= 3,
    'minimal':   lambda m, e: m >= 5 and m < 8,
    'partiel':   lambda m, e: 2 <= m < 5,
    'vide':      lambda m, e: m < 2,
}

by_source    = defaultdict(lambda: defaultdict(int))  # source → niveau → count
field_missing = defaultdict(int)   # field → nb variants qui l'ont null
total_vr     = 0
level_counts = defaultdict(int)
examples     = defaultdict(list)   # niveau → exemples

for base_key, base in ing.items():
    for vr_key, vr in base.get('variants', {}).items():
        if not isinstance(vr, dict):
            continue
        total_vr += 1
        src = vr.get('_source', '?')

        m_present = sum(1 for f in MANDATORY if vr.get(f) is not None)
        e_present = sum(1 for f in ENRICHED  if vr.get(f) is not None)

        for f in MANDATORY + ENRICHED:
            if vr.get(f) is None:
                field_missing[f] += 1

        level = 'vide'
        for lvl, fn in LEVELS.items():
            if fn(m_present, e_present):
                level = lvl
                break

        level_counts[level] += 1
        by_source[src][level] += 1
        if level in ('vide', 'partiel') and len(examples[level]) < 5:
            examples[level].append(f'{base_key}/{vr_key}  ({src}#{vr.get("_source_id","?")})')

# ── Rapport ────────────────────────────────────────────────────────────────────
print('=' * 65)
print('AUDIT COMPLETUDE nutrition_v2.json')
print('=' * 65)
print(f'  Total variants analysés : {total_vr}')
print()

ORDER = ['complet', 'standard', 'minimal', 'partiel', 'vide']
EMOJI = {'complet':'✅', 'standard':'🟢', 'minimal':'🟡', 'partiel':'🟠', 'vide':'🔴'}
for lvl in ORDER:
    n = level_counts[lvl]
    pct = round(n / total_vr * 100, 1)
    bar = '█' * int(pct / 2) + '░' * (50 - int(pct / 2))
    print(f'  {EMOJI[lvl]} {lvl:<10} {n:>5} ({pct:>5}%)  {bar[:30]}')

print()
print('── Par source ───────────────────────────────────────────────')
print(f'  {"Source":<8} {"complet":>8} {"standard":>9} {"minimal":>8} {"partiel":>8} {"vide":>6}')
for src in ['CIQUAL', 'USDA', 'CNF']:
    s = by_source[src]
    tot = sum(s.values()) or 1
    print(f'  {src:<8} {s["complet"]:>8} {s["standard"]:>9} {s["minimal"]:>8} {s["partiel"]:>8} {s["vide"]:>6}  (total: {tot})')

print()
print('── Champs manquants (% variants sans la donnée) ─────────────')
for f in MANDATORY + ENRICHED:
    n = field_missing[f]
    pct = round(n / total_vr * 100, 1)
    tag = ' ← EU obligatoire' if f in MANDATORY else ''
    flag = '🔴' if pct > 80 else '🟠' if pct > 40 else '🟡' if pct > 10 else '✅'
    print(f'  {flag} {f:<28} : {n:>5} manquants ({pct:>5}%){tag}')

print()
for lvl in ['vide', 'partiel']:
    if examples[lvl]:
        print(f'── Exemples {lvl} ──────────────────────────────────────────')
        for ex in examples[lvl]:
            print(f'  {ex}')
        print()
