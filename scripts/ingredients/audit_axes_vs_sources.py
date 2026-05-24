#!/usr/bin/env python3
"""
audit_axes_vs_sources.py
Audits axes_en/axes_fr for every variant in ingredients_tree.json
by crossing them against their official source descriptions
(CIQUAL xlsx, CNF csv, USDA json).
"""

import json
import zipfile
import io
import csv
import re
import sys
from collections import defaultdict

# ── Paths ──────────────────────────────────────────────────────────────────
BASE = "C:/Users/Samijo/Downloads/project_final_v6_migrated/project_final_v6_migrated"
TREE_PATH   = f"{BASE}/backend/data/ingredients/ingredients_tree.json"
CIQUAL_ZIP  = f"{BASE}/backend/data/nutrition/raw/Table_Ciqual_2025_FR_2025_11_03.zip"
CNF_ZIP     = f"{BASE}/backend/data/nutrition/raw/cnf.zip"
USDA_ZIP    = f"{BASE}/backend/data/nutrition/raw/FoodData_Central_foundation_food_json_2025-12-18.zip"

MAX_CONFLICTS_REPORTED = 200

# ── Pattern rules ──────────────────────────────────────────────────────────
# Each entry: (pattern_regex, axis_name, expected_value, severity)
# severity: ERROR = definite conflict; WARN = mild warning (not reported)

RULES = [
    # cooking_state
    (r'\bcru\b|\braw\b|\buncooked\b',              'cooking_state', 'raw',       'ERROR'),
    (r'\bcuit[es]?\b|\bcooked\b',                  'cooking_state', 'cooked',    'ERROR'),
    (r'\bbouilli[es]?\b|\bboiled\b',               'cooking_state', 'boiled',    'ERROR'),
    (r'\bvapeur\b|\bsteamed\b',                    'cooking_state', 'steamed',   'ERROR'),
    (r'\bfrit[es]?\b|\bfried\b',                   'cooking_state', 'fried',     'ERROR'),
    (r'\bgrill[ée][es]?\b|\bgrilled\b|\brôti[es]?\b|\broasted\b|\broti[es]?\b',
                                                    'cooking_state', 'roasted',   'ERROR'),
    (r'\bau four\b|\bbaked\b',                     'cooking_state', 'baked',     'ERROR'),
    (r'\bpré[- ]?cuit[es]?\b|\bprecooked\b|\bpre-cooked\b',
                                                    'cooking_state', 'precooked', 'ERROR'),

    # thermal_state
    (r'\bséché[es]?\b|\bsec\b|\bsèche[s]?\b|\bdried\b|\bdehydrated\b|\bdés?hydraté[es]?\b',
                                                    'thermal_state', 'dried',       'ERROR'),
    (r'\bsurgelé[es]?\b|\bcongelé[es]?\b|\bfrozen\b',
                                                    'thermal_state', 'frozen',      'ERROR'),
    (r'\bfrais\b|\bfraîche[s]?\b|\bfresh\b',       'thermal_state', 'fresh',        'ERROR'),
    (r'\blyophilisé[es]?\b|\bfreeze[- ]?dried\b',  'thermal_state', 'freeze_dried', 'ERROR'),
    (r'\bpasteurisé[es]?\b|\bpasteurized\b',        'thermal_state', 'pasteurized',  'ERROR'),
    (r'\bUHT\b',                                    'thermal_state', 'uht',          'ERROR'),
    (r'\brayon frais\b|\bréfrigéré[es]?\b|\brefrigerated\b',
                                                    'thermal_state', 'refrigerated', 'ERROR'),

    # form
    (r'\bfarine[s]?\b|\bflour\b',                  'form', 'flour',      'ERROR'),
    (r'\bhuile[s]?\b|\boil\b',                     'form', 'oil',        'ERROR'),
    (r'\bjus\b|\bjuice\b',                         'form', 'juice',      'ERROR'),
    (r'\bpoudre\b|\bpowder\b',                     'form', 'powder',     'ERROR'),
    (r'\bpâte\b|\bpaste\b',                        'form', 'paste',      'ERROR'),
    (r'\bcrème\b|\bcream\b',                       'form', 'cream',      'ERROR'),
    (r'\bconcentré[es]?\b|\bconcentrate[ds]?\b',   'form', 'concentrate','ERROR'),
    (r'\bextrait[s]?\b|\bextract[s]?\b',           'form', 'extract',    'ERROR'),
    (r'\byaourt[s]?\b|\byogurt[s]?\b|\byoghurt[s]?\b',
                                                    'form', 'yogurt',     'ERROR'),
    (r'\bsauce[s]?\b',                             'form', 'sauce',      'ERROR'),
    (r'\bpurée[s]?\b|\bpuree[ds]?\b',             'form', 'pureed',     'ERROR'),
    # milk/butter need special treatment — handled separately below

    # seasoning
    (r'\bsalé[es]?\b|\bsalted\b|\bavec sel\b',    'seasoning', 'salted',      'ERROR'),
    (r'\bsans sel\b|\bunsalted\b|\bno salt\b',     'seasoning', 'unsalted',    'ERROR'),
    (r'\bsucré[es]?\b|\bsweetened\b',             'seasoning', 'sweetened',   'ERROR'),
    (r'\bsans sucre\b|\bunsweetened\b',            'seasoning', 'unsweetened', 'ERROR'),
    (r'\bnature\b|\bplain\b',                      'seasoning', 'plain',       'ERROR'),

    # packaging / draining
    (r'\bconserve\b|\bcanned\b|\ben boîte\b|\bappertisé[es]?\b',
                                                    'packaging', 'canned',   'ERROR'),
    (r'\bégoutté[es]?\b|\bdrained\b',              'draining',  'drained',   'ERROR'),
    (r"\bà l'huile\b|\bin oil\b",                  'draining',  'in_oil',    'ERROR'),
    (r'\bau naturel\b|\bin water\b',               'draining',  'in_water',  'ERROR'),
]

# Milk and butter are special: only flag form conflict if the axis exists
# and is set to something other than milk/butter
MILK_PATTERN   = re.compile(r'\blait\b|\bmilk\b', re.IGNORECASE)
BUTTER_PATTERN = re.compile(r'\bbeurre\b(?! de cacao)|\bbutter\b(?! bean)', re.IGNORECASE)

# Compile all patterns once
COMPILED_RULES = [
    (re.compile(pat, re.IGNORECASE), axis, expected, sev)
    for pat, axis, expected, sev in RULES
]


# ── Load lookup tables ─────────────────────────────────────────────────────

def load_ciqual():
    """Returns dict {alim_code_str: {'fr': name_fr, 'en': name_eng}}"""
    print("  Loading CIQUAL...", end=" ", flush=True)
    try:
        import openpyxl
    except ImportError:
        print("FAIL — openpyxl not installed")
        return {}
    z = zipfile.ZipFile(CIQUAL_ZIP)
    data = z.read('Table_Ciqual_2025_FR_2025_11_03.xlsx')
    wb = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h else '' for h in next(rows)]
    # Find column indices
    code_col = next((i for i, h in enumerate(headers) if 'alim_code' in h.lower()), None)
    nom_fr_col = next((i for i, h in enumerate(headers) if 'alim_nom_fr' in h.lower()), None)
    nom_eng_col = next((i for i, h in enumerate(headers) if 'alim_nom_eng' in h.lower() or 'alim_nom_en' in h.lower()), None)
    if code_col is None or nom_fr_col is None:
        print(f"FAIL — couldn't find columns. Headers: {headers[:10]}")
        return {}
    lookup = {}
    for row in rows:
        code = row[code_col]
        if code is None:
            continue
        code_str = str(int(float(str(code)))) if str(code).replace('.','').isdigit() else str(code).strip()
        name_fr = str(row[nom_fr_col]).strip() if row[nom_fr_col] else ''
        name_en = str(row[nom_eng_col]).strip() if nom_eng_col is not None and row[nom_eng_col] else ''
        lookup[code_str] = {'fr': name_fr, 'en': name_en}
    print(f"OK ({len(lookup)} entries)")
    return lookup


def load_cnf():
    """Returns dict {food_id_str: {'en': desc_en, 'fr': desc_fr}}"""
    print("  Loading CNF...", end=" ", flush=True)
    z = zipfile.ZipFile(CNF_ZIP)
    raw = z.read('cnf/FOOD_NAME.csv').decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(raw))
    lookup = {}
    for row in reader:
        fid = str(row.get('FoodID', '')).strip()
        if not fid:
            continue
        lookup[fid] = {
            'en': row.get('FoodDescription', '').strip(),
            'fr': row.get('FoodDescriptionF', '').strip(),
        }
    print(f"OK ({len(lookup)} entries)")
    return lookup


def load_usda():
    """Returns dict {fdc_id_str: {'en': description}}"""
    print("  Loading USDA...", end=" ", flush=True)
    z = zipfile.ZipFile(USDA_ZIP)
    data = z.read('FoodData_Central_foundation_food_json_2025-12-18.json')
    obj = json.loads(data)
    foods = obj.get('FoundationFoods', [])
    lookup = {}
    for food in foods:
        fdc_id = str(food.get('fdcId', '')).strip()
        if not fdc_id:
            continue
        lookup[fdc_id] = {'en': food.get('description', '').strip()}
    print(f"OK ({len(lookup)} entries)")
    return lookup


# ── Conflict detection ─────────────────────────────────────────────────────

def get_descriptions(source, source_id, ciqual_lkp, cnf_lkp, usda_lkp):
    """Returns list of strings to search in (all available descriptions)."""
    if source == 'CIQUAL':
        entry = ciqual_lkp.get(str(source_id))
        if entry:
            return [d for d in [entry['fr'], entry['en']] if d]
    elif source == 'CNF':
        entry = cnf_lkp.get(str(source_id))
        if entry:
            return [d for d in [entry['en'], entry['fr']] if d]
    elif source == 'USDA':
        entry = usda_lkp.get(str(source_id))
        if entry:
            return [d for d in [entry.get('en', '')] if d]
    return []


def check_variant(ig_id, var, ciqual_lkp, cnf_lkp, usda_lkp):
    """
    Returns list of conflict dicts:
      {ig_id, var_id, source, source_id, desc, axis, expected, actual, severity}
    """
    source    = var.get('source', '')
    source_id = str(var.get('source_id', ''))
    var_id    = var.get('id', '')
    axes_en   = var.get('axes_en', {}) or {}
    axes_fr   = var.get('axes_fr', {}) or {}

    descs = get_descriptions(source, source_id, ciqual_lkp, cnf_lkp, usda_lkp)
    if not descs:
        return []  # source not found → skip

    combined = ' | '.join(descs)
    conflicts = []

    for pattern, axis, expected, severity in COMPILED_RULES:
        if not pattern.search(combined):
            continue
        # Pattern matches → check if axis in tree matches expected
        actual = axes_en.get(axis)
        if actual is None:
            # Axis absent from tree — only flag packaging/draining as missing
            # (the task says "ne pas rapporter les axes absents du tree")
            continue
        # Axis is present but value differs → CONFLICT
        if actual != expected:
            # Special: cooking_state=cooked can be inferred by boiled/steamed/fried/baked/roasted/precooked
            # Allow those as sub-types of cooked only if actual IS one of the cooking sub-states
            COOKED_SUBTYPES = {'boiled', 'steamed', 'fried', 'roasted', 'baked', 'precooked'}
            if axis == 'cooking_state':
                if expected == 'cooked' and actual in COOKED_SUBTYPES:
                    continue  # more specific value, not a conflict
                if actual == 'cooked' and expected in COOKED_SUBTYPES:
                    # tree says "cooked" but source says "boiled" → report
                    pass
            conflicts.append({
                'ig_id':     ig_id,
                'var_id':    var_id,
                'source':    source,
                'source_id': source_id,
                'desc':      combined[:120],
                'axis':      axis,
                'expected':  expected,
                'actual':    actual,
                'severity':  severity,
            })

    # Special: milk
    if MILK_PATTERN.search(combined):
        actual = axes_en.get('form')
        if actual is not None and actual != 'milk':
            conflicts.append({
                'ig_id': ig_id, 'var_id': var_id,
                'source': source, 'source_id': source_id,
                'desc': combined[:120],
                'axis': 'form', 'expected': 'milk', 'actual': actual, 'severity': 'ERROR',
            })

    # Special: butter (excluding "beurre de cacao", "butter bean")
    if BUTTER_PATTERN.search(combined):
        actual = axes_en.get('form')
        if actual is not None and actual != 'butter':
            conflicts.append({
                'ig_id': ig_id, 'var_id': var_id,
                'source': source, 'source_id': source_id,
                'desc': combined[:120],
                'axis': 'form', 'expected': 'butter', 'actual': actual, 'severity': 'ERROR',
            })

    return conflicts


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=== AUDIT AXES VS SOURCES ===\n")

    # 1. Load tree
    print("Loading tree...", end=" ", flush=True)
    with open(TREE_PATH, encoding='utf-8') as f:
        tree = json.load(f)
    print("OK")

    # 2. Load lookups
    print("Loading source lookups:")
    ciqual_lkp = load_ciqual()
    cnf_lkp    = load_cnf()
    usda_lkp   = load_usda()
    print()

    # 3. Walk tree
    all_conflicts = []
    stats = {
        'total': 0,
        'by_source': defaultdict(int),
        'found_in_source': defaultdict(int),
        'not_found_in_source': defaultdict(int),
    }

    for cat in tree['categories']:
        for sc in cat.get('subcategories', []):
            for ig in sc.get('ingredient_groups', []):
                ig_id = ig.get('id', '')
                for var in ig.get('variants', []):
                    source = var.get('source', 'unknown')
                    stats['total'] += 1
                    stats['by_source'][source] += 1

                    # Check if source_id exists in lookup
                    source_id = str(var.get('source_id', ''))
                    if source == 'CIQUAL' and source_id in ciqual_lkp:
                        stats['found_in_source']['CIQUAL'] += 1
                    elif source == 'CNF' and source_id in cnf_lkp:
                        stats['found_in_source']['CNF'] += 1
                    elif source == 'USDA' and source_id in usda_lkp:
                        stats['found_in_source']['USDA'] += 1
                    else:
                        stats['not_found_in_source'][source] += 1

                    conflicts = check_variant(ig_id, var, ciqual_lkp, cnf_lkp, usda_lkp)
                    all_conflicts.extend(conflicts)

    # 4. Report
    print("=" * 70)
    print("RÉSUMÉ — VARIANTS VÉRIFIÉS")
    print("=" * 70)
    print(f"Total variants dans le tree : {stats['total']}")
    for src in ['CIQUAL', 'CNF', 'USDA']:
        n = stats['by_source'][src]
        found = stats['found_in_source'][src]
        nf = stats['not_found_in_source'][src]
        print(f"  {src:8s}: {n:4d} variants  |  {found:4d} trouvés dans la source  |  {nf:4d} non trouvés")
    print()

    # Conflicts by axis
    by_axis = defaultdict(list)
    for c in all_conflicts:
        by_axis[c['axis']].append(c)

    print("=" * 70)
    print("CONFLITS PAR TYPE D'AXE")
    print("=" * 70)
    total_conflicts = len(all_conflicts)
    print(f"Total conflits : {total_conflicts}")
    for axis in sorted(by_axis):
        print(f"  {axis:20s}: {len(by_axis[axis]):4d} conflits")
    print()

    # Conflicts by source
    by_source = defaultdict(list)
    for c in all_conflicts:
        by_source[c['source']].append(c)
    print("CONFLITS PAR SOURCE")
    for src in ['CIQUAL', 'CNF', 'USDA']:
        print(f"  {src:8s}: {len(by_source[src]):4d} conflits")
    print()

    # Detailed list (max MAX_CONFLICTS_REPORTED)
    print("=" * 70)
    print(f"LISTE DES CONFLITS (max {MAX_CONFLICTS_REPORTED})")
    print("=" * 70)
    reported = 0
    for c in all_conflicts:
        if reported >= MAX_CONFLICTS_REPORTED:
            print(f"\n  ... {total_conflicts - reported} conflits supplémentaires non affichés.")
            break
        print(
            f"\nCONFLIT AXLE : {c['ig_id']}  {c['var_id']}  {c['source']}:{c['source_id']}\n"
            f"  desc officielle : \"{c['desc']}\"\n"
            f"  attendu: {c['axis']}={c['expected']}  /  actuel: {c['axis']}={c['actual']}"
        )
        reported += 1

    print()
    print("=" * 70)
    print("CONCLUSIONS")
    print("=" * 70)
    total_checked = sum(stats['found_in_source'].values())
    conflict_rate = (total_conflicts / total_checked * 100) if total_checked else 0
    print(f"  Variants avec description trouvée : {total_checked} / {stats['total']}")
    print(f"  Taux de conflit global : {conflict_rate:.1f}% ({total_conflicts} conflits sur {total_checked} vérifiés)")
    print()
    if total_conflicts == 0:
        print("  Aucun conflit détecté — les axes semblent cohérents avec les sources officielles.")
    elif conflict_rate < 2:
        print("  Qualité globale EXCELLENTE — très peu de conflits.")
    elif conflict_rate < 5:
        print("  Qualité globale BONNE — quelques conflits à corriger.")
    elif conflict_rate < 10:
        print("  Qualité globale MOYENNE — nombre significatif de conflits.")
    else:
        print("  Qualité globale FAIBLE — de nombreux conflits nécessitent une révision.")

    # Per-axis conclusion
    if by_axis:
        worst = sorted(by_axis.items(), key=lambda x: -len(x[1]))
        print()
        print("  Axes les plus problématiques :")
        for axis, clist in worst[:5]:
            print(f"    {axis}: {len(clist)} conflits")


if __name__ == '__main__':
    main()
