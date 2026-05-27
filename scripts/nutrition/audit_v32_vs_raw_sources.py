"""
audit_v32_vs_raw_sources.py — Audit v32 contre les sources officielles brutes
==============================================================================
Sources utilisées :
  CIQUAL : Table_Ciqual_2025_FR_2025_11_03.xlsx  (alim_code → ID)
  USDA   : FoodData_Central_foundation_food_json_2025-12-18.json (fdcId → ID)
  CNF    : cnf/FOOD_NAME.csv + NUTRIENT_AMOUNT.csv (FoodCode → ID)

Vérifie pour chaque variant de ingredients_v32.json :
  1. NAME       : name_fr v32 vs nom officiel source brute
  2. AXIS/STATE : etat_cuisson/etat_thermique v32 vs nom officiel (détection textuelle)
  3. CROSS-ID   : même source_id partagé par deux ingredient_groups différents

Rapport : backend/data/nutrition/logs/audit_v32_raw.json
"""
import csv, json, re, sys
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

ROOT    = Path(__file__).parents[2]
RAW     = ROOT / 'backend/data/nutrition/raw'
V32     = ROOT / 'backend/data/ingredients/ingredients_v32.json'
LOG_DIR = ROOT / 'backend/data/nutrition/logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ══════════════════════════════════════════════════════════════════════════════
# 1. CHARGEMENT DES SOURCES BRUTES
# ══════════════════════════════════════════════════════════════════════════════

def slug(s):
    s = (s or '').lower().strip()
    s = re.sub(r"['\u2019\u2018\u00e9\u00e8\u00ea\u00e0\u00e2\u00f9\u00fb\u00ee\u00ef\u00f4\u00e7]",
               lambda m: {'é':'e','è':'e','ê':'e','à':'a','â':'a','ù':'u',
                           'û':'u','î':'i','ï':'i','ô':'o','ç':'c'}.get(m.group(),''), s)
    s = re.sub(r'[^a-z0-9]+', '_', s)
    return s.strip('_')

def token_sim(a, b):
    ta = set(slug(a).split('_')) - {'de','du','des','le','la','les','et','au','aux','l'}
    tb = set(slug(b).split('_')) - {'de','du','des','le','la','les','et','au','aux','l'}
    if not ta or not tb: return 0.0
    return len(ta & tb) / max(len(ta), len(tb))

# ── CIQUAL XLSX ───────────────────────────────────────────────────────────────
print('Chargement CIQUAL xlsx...')
import openpyxl
wb = openpyxl.load_workbook(RAW / 'Table_Ciqual_2025_FR_2025_11_03.xlsx', read_only=True)
ws = wb.active
headers_ciq = None
ciq_raw = {}   # alim_code (int) -> {alim_nom_fr, alim_grp_nom_fr, ...}
for row in ws.iter_rows(values_only=True):
    if headers_ciq is None:
        headers_ciq = [str(h or '').strip() for h in row]
        continue
    if not row[0]:
        continue
    rec = dict(zip(headers_ciq, row))
    code = rec.get('alim_code')
    if code is not None:
        try:
            ciq_raw[int(code)] = rec
        except (ValueError, TypeError):
            pass
wb.close()
print(f'  CIQUAL : {len(ciq_raw)} aliments  (colonnes: {headers_ciq[:8]})')

# ── USDA Foundation Foods JSON ────────────────────────────────────────────────
print('Chargement USDA json...')
usda_data = json.loads((RAW / 'FoodData_Central_foundation_food_json_2025-12-18.json').read_text(encoding='utf-8'))
usda_raw = {}   # fdcId (int) -> {description, foodCategory, ...}
for food in usda_data.get('FoundationFoods', []):
    fid = food.get('fdcId')
    if fid:
        usda_raw[int(fid)] = {
            'description': food.get('description', ''),
            'foodCategory': (food.get('foodCategory') or {}).get('description', ''),
            'fdcId': fid,
        }
print(f'  USDA   : {len(usda_raw)} aliments')

# ── CNF CSV ───────────────────────────────────────────────────────────────────
print('Chargement CNF csv...')
cnf_dir = RAW / 'cnf'
cnf_raw = {}   # FoodCode (int) -> {FoodDescription, FoodDescriptionF, FoodGroupID}
with open(cnf_dir / 'FOOD_NAME.csv', encoding='utf-8-sig', errors='replace') as f:
    for row in csv.DictReader(f):
        fc = row.get('FoodCode') or row.get('FoodID')
        if fc:
            try:
                cnf_raw[int(fc)] = {
                    'FoodDescription':  row.get('FoodDescription', ''),
                    'FoodDescriptionF': row.get('FoodDescriptionF', ''),
                    'FoodGroupID':      row.get('FoodGroupID', ''),
                }
            except ValueError:
                pass
print(f'  CNF    : {len(cnf_raw)} aliments')

# Index unifié: (SOURCE_UPPER, source_id_int) -> {name_fr, name_en, category}
raw_idx = {}
for code, rec in ciq_raw.items():
    nom = str(rec.get('alim_nom_fr') or '')
    grp = str(rec.get('alim_grp_nom_fr') or '')
    raw_idx[('CIQUAL', code)] = {'name_fr': nom, 'name_en': '', 'category': grp}
for fid, rec in usda_raw.items():
    raw_idx[('USDA', fid)] = {'name_fr': '', 'name_en': rec['description'], 'category': rec['foodCategory']}
for fc, rec in cnf_raw.items():
    raw_idx[('CNF', fc)] = {
        'name_fr': rec['FoodDescriptionF'],
        'name_en': rec['FoodDescription'],
        'category': rec['FoodGroupID'],
    }
print(f'  Index  : {len(raw_idx)} entrées\n')

# Mots-clés de cuisson détectables dans le nom officiel
COOKED_KW   = {'cuit', 'cuites', 'bouillie', 'bouilli', 'frit', 'frite', 'grillé', 'grillée',
                'rôti', 'rôtie', 'cooked', 'boiled', 'fried', 'roasted', 'grilled', 'baked',
                'toasted', 'toastée', 'toasté', 'sauté', 'steamed', 'vapeur'}
RAW_KW      = {'cru', 'crue', 'crues', 'crus', 'frais', 'fraîche', 'fresh', 'raw', 'uncooked'}
DRIED_KW    = {'séché', 'séchée', 'dried', 'deshydraté', 'déshydraté', 'dehydrated',
                'lyophilisé', 'freeze-dried', 'sec', 'sèche'}

def detect_state_from_name(name_fr, name_en):
    """Détecte l'état de cuisson depuis le nom officiel."""
    combined = (name_fr + ' ' + name_en).lower()
    words = set(re.findall(r'\w+', combined))
    if words & COOKED_KW:
        return 'cooked'
    if words & DRIED_KW:
        return 'dried'
    if words & RAW_KW:
        return 'raw'
    return 'unknown'

# Mapping axes v32 → état attendu
COOKING_EXPECTED = {
    'cru': 'raw', 'cuit': 'cooked', 'bouilli': 'cooked', 'frit': 'cooked',
    'grillé': 'cooked', 'grillé à sec': 'cooked', 'vapeur': 'cooked',
    'rôti': 'cooked', 'sauté': 'cooked', 'précuit': 'cooked',
}
THERMAL_EXPECTED = {
    'séché': 'dried', 'déshydraté': 'dried', 'frais': 'raw', 'réhydraté': 'raw',
}

# ══════════════════════════════════════════════════════════════════════════════
# 2. AUDIT
# ══════════════════════════════════════════════════════════════════════════════
print('Audit en cours...')
v32_data = json.loads(V32.read_text(encoding='utf-8'))

issues = {'name_mismatch': [], 'axis_name_mismatch': [], 'cross_id_duplicate': []}
source_usage = defaultdict(list)   # (src, sid) -> usages
stats = {'total': 0, 'checked': 0, 'not_found': 0}

for cat in v32_data.get('categories', []):
    cat1 = cat.get('label', '')
    for sub in cat.get('subcategories', []):
        cat2 = sub.get('label', '')
        for ig in sub.get('ingredient_groups', []):
            ig_id    = ig.get('id', '')
            ig_axes  = ig.get('axes') or {}
            en_name  = ig.get('canonical_name_en', '')
            fr_name  = ig.get('canonical_name_fr', '')

            for vr in ig.get('variants', []):
                stats['total'] += 1
                src = (vr.get('source') or '').upper()
                sid = vr.get('source_id')
                if not src or sid is None:
                    continue
                key = (src, int(sid))
                source_usage[key].append({
                    'ig_id': ig_id, 'vr_id': vr.get('id',''),
                    'cat1': cat1, 'cat2': cat2,
                    'en': en_name[:45], 'fr': fr_name[:45],
                })

                raw = raw_idx.get(key)
                if raw is None:
                    stats['not_found'] += 1
                    continue
                stats['checked'] += 1

                all_axes = {**ig_axes, **(vr.get('axes') or {})}
                vr_name_fr = vr.get('name_fr') or fr_name
                vr_name_en = vr.get('name_en') or en_name

                # ── 1. NOM ────────────────────────────────────────────────────
                official_fr = raw['name_fr']
                official_en = raw['name_en']
                sim_fr = token_sim(vr_name_fr, official_fr) if official_fr else 1.0
                sim_en = token_sim(vr_name_en, official_en) if official_en else 1.0
                best_sim = max(sim_fr, sim_en)

                if best_sim < 0.2 and (official_fr or official_en):
                    issues['name_mismatch'].append({
                        'severity': 'WARNING',
                        'ig_id': ig_id, 'vr_id': vr.get('id',''),
                        'src': src, 'source_id': int(sid),
                        'v32_fr':   vr_name_fr[:50],
                        'v32_en':   vr_name_en[:50],
                        'official_fr': official_fr[:60],
                        'official_en': official_en[:60],
                        'sim': round(best_sim, 2),
                        'cat1': cat1, 'cat2': cat2,
                    })

                # ── 2. AXE vs NOM OFFICIEL ────────────────────────────────────
                official_state = detect_state_from_name(official_fr, official_en)
                if official_state == 'unknown':
                    continue

                v32_cooking = all_axes.get('etat_cuisson')
                v32_thermal = all_axes.get('etat_thermique')

                expected = None
                axe_used = None
                if v32_cooking:
                    expected = COOKING_EXPECTED.get(v32_cooking)
                    axe_used = f'etat_cuisson={v32_cooking}'
                elif v32_thermal:
                    expected = THERMAL_EXPECTED.get(v32_thermal)
                    axe_used = f'etat_thermique={v32_thermal}'

                if expected and official_state != 'unknown' and expected != official_state:
                    # Cas particulier: grillé→cooked est parfois 'cooked' dans source aussi
                    # On veut surtout les vrais conflits raw↔cooked et raw↔dried
                    conflict_pairs = {('raw','cooked'),('cooked','raw'),('raw','dried'),('dried','raw')}
                    if (expected, official_state) in conflict_pairs:
                        severity = 'ERROR'
                    else:
                        severity = 'WARNING'
                    issues['axis_name_mismatch'].append({
                        'severity': severity,
                        'ig_id': ig_id, 'vr_id': vr.get('id',''),
                        'src': src, 'source_id': int(sid),
                        'v32_axis':       axe_used,
                        'expected_state': expected,
                        'official_state': official_state,
                        'official_name':  (official_fr or official_en)[:60],
                        'cat1': cat1, 'cat2': cat2,
                        'v32_en': en_name[:40],
                    })

# ── 3. DOUBLONS CROSS-GROUP ────────────────────────────────────────────────────
for key, usages in source_usage.items():
    if len(usages) <= 1:
        continue
    ig_ids = set(u['ig_id'] for u in usages)
    if len(ig_ids) <= 1:
        continue  # doublon intra-groupe (synonymes) → inoffensif
    src, sid = key
    official = raw_idx.get(key, {})
    issues['cross_id_duplicate'].append({
        'severity': 'ERROR',
        'src': src, 'source_id': sid,
        'official_name': (official.get('name_fr') or official.get('name_en',''))[:60],
        'n_groups': len(ig_ids),
        'usages': usages[:6],
    })

# ══════════════════════════════════════════════════════════════════════════════
# 3. RAPPORT
# ══════════════════════════════════════════════════════════════════════════════
errors_name = [i for i in issues['name_mismatch']     if i['severity']=='ERROR']
errors_axis = [i for i in issues['axis_name_mismatch'] if i['severity']=='ERROR']
warn_name   = [i for i in issues['name_mismatch']     if i['severity']=='WARNING']
warn_axis   = [i for i in issues['axis_name_mismatch'] if i['severity']=='WARNING']

print()
print('=' * 65)
print('AUDIT v32 vs SOURCES OFFICIELLES BRUTES')
print('=' * 65)
print(f'  Variants analysés    : {stats["total"]}')
print(f'  Vérifiés vs source   : {stats["checked"]}')
print(f'  Non trouvés          : {stats["not_found"]}')
print()
print(f'  name_mismatch        : {len(issues["name_mismatch"]):4d}'
      f'  (ERROR={len(errors_name)}, WARNING={len(warn_name)})')
print(f'  axis_name_mismatch   : {len(issues["axis_name_mismatch"]):4d}'
      f'  (ERROR={len(errors_axis)}, WARNING={len(warn_axis)})')
print(f'  cross_id_duplicate   : {len(issues["cross_id_duplicate"]):4d}  (tous ERROR)')
print()

print('── ERRORS axis_name_mismatch (conflits raw↔cooked, raw↔dried) ──')
for item in issues['axis_name_mismatch']:
    if item['severity'] == 'ERROR':
        print(f"  [{item['src']}#{item['source_id']:8d}] "
              f"axe={item['v32_axis']} → attendu:{item['expected_state']} "
              f"| source dit:'{item['official_state']}' "
              f"| \"{item['official_name']}\"")

print()
print('── ERRORS cross_id_duplicate (même source_id pour groupes différents) ──')
for item in issues['cross_id_duplicate']:
    print(f"  {item['src']}#{item['source_id']} "
          f"[{item['official_name']}] "
          f"x{item['n_groups']} groupes :")
    for u in item['usages']:
        print(f"    {u['ig_id']} | {u['cat2']} | {u['en'][:40]}")

print()
print('── WARNINGS name_mismatch (échantillon 15) ──')
for item in issues['name_mismatch'][:15]:
    print(f"  [{item['src']}#{item['source_id']:8d}] sim={item['sim']}"
          f" | v32:'{item['v32_fr'][:30]}'"
          f" | officiel:'{item['official_fr'][:40] or item['official_en'][:40]}'")

# Export
report = {
    'stats': stats,
    'summary': {k: len(v) for k, v in issues.items()},
    'errors': {
        'axis_name_mismatch': [i for i in issues['axis_name_mismatch'] if i['severity']=='ERROR'],
        'cross_id_duplicate': issues['cross_id_duplicate'],
    },
    'warnings': {
        'name_mismatch':    issues['name_mismatch'],
        'axis_name_mismatch': [i for i in issues['axis_name_mismatch'] if i['severity']=='WARNING'],
    },
}
out = LOG_DIR / 'audit_v32_raw.json'
out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n  Rapport complet → {out}')
