"""
patch_usda_axes_v32.py
======================
Audit + patch des axes manquants pour les variants USDA dans v32.
Noms USDA en anglais (memes regles que CNF).

Mode : DRY-RUN par defaut. --apply pour modifier v32.
"""
import json, re, sys, copy, shutil
from datetime import datetime
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
DRY_RUN = '--apply' not in sys.argv

ROOT   = Path(__file__).parents[2]
DATA   = ROOT / 'backend/data'
V32_P  = DATA / 'ingredients/ingredients_v32.json'
USDA_P = DATA / 'nutrition/raw/FoodData_Central_foundation_food_json_2025-12-18.json'

# ── Charger USDA FDC ──────────────────────────────────────────────────────────
print('Chargement USDA FDC json...')
usda_raw = json.loads(USDA_P.read_text(encoding='utf-8'))

# USDA Foundation Foods : liste sous la cle "FoundationFoods"
# Chaque entree : {"fdcId": 123456, "description": "Apples, raw, with skin", ...}
usda_names: dict[str, str] = {}
for entry in usda_raw.get('FoundationFoods', []):
    fdc_id = str(entry.get('fdcId', '')).strip()
    desc   = (entry.get('description', '') or '').strip()
    if fdc_id and desc:
        usda_names[fdc_id] = desc

print(f'  {len(usda_names)} entrees USDA chargees')
for k, v in list(usda_names.items())[:3]:
    print(f'  ex: {k} -> {v}')

# ── Charger v32 ──────────────────────────────────────────────────────────────
v32 = json.loads(V32_P.read_text(encoding='utf-8'))


# ══════════════════════════════════════════════════════════════════════════════
# FAUX POSITIFS (anglais — identiques CNF + quelques specifiques USDA)
# ══════════════════════════════════════════════════════════════════════════════
SKIP_RAW_CATS   = {'spices_and_herbs', 'leavening_agents_and_additives', 'fats_and_oils'}
SKIP_DRIED_CATS = {'spices_and_herbs', 'leavening_agents_and_additives'}

FALSE_POSITIVES = [
    # whole-grain / whole-wheat → type de grain, pas forme physique
    (r'whole.grain|whole.wheat|whole.groat',     'forme',        'whole = type de grain, pas forme'),
    # raw sugar → sucre non raffine
    (r'raw sugar|raw cane',                      'etat_cuisson', 'raw sugar = non raffine'),
    # epice en poudre → identite ingredient
    (r'(chili|chile|curry|garlic|onion|mustard|cayenne|paprika|cinnamon|cumin|pepper|turmeric|ginger|nutmeg|clove|allspice).+powder',
                                                 'forme',        'epice en poudre = identite'),
    # freshwater → habitat, pas etat thermique
    (r'fresh.?water',                            'etat_thermique','freshwater = eau douce'),
    # "ground" seul dans noms d'epices
    (r'\bground\b.*(cinnamon|pepper|spice|cumin|coriander|cardamom|allspice|nutmeg|clove|ginger|turmeric|anise)',
                                                 'forme',        'ground epice = etat par defaut'),
    # "salted" dans "salted butter" → axe valide en fait, on laisse passer
    # "in brine" → conserve OK
    # "dried" pour noix et amandes → etat normal
    (r'^(nuts|almonds|walnuts|pecans|cashews|pistachios|hazelnuts).+dried$',
                                                 'etat_thermique','noix sechees = etat standard'),
    # "canned" jus de tomate → conserve valide, pas FP
]

def is_fp(name: str, axe: str, cat_label: str):
    name_l = name.lower()
    if axe == 'etat_cuisson' and cat_label in SKIP_RAW_CATS:
        return f'cat={cat_label}: raw/cooked non pertinent'
    if axe == 'etat_thermique' and cat_label in SKIP_DRIED_CATS:
        return f'cat={cat_label}: dried = etat par defaut'
    for pattern, fp_axe, reason in FALSE_POSITIVES:
        if fp_axe == axe and re.search(pattern, name_l):
            return reason
    return None


# ══════════════════════════════════════════════════════════════════════════════
# REGLES DE DETECTION (noms USDA anglais)
# ══════════════════════════════════════════════════════════════════════════════
RULES_EN = [
    # ── Etat de cuisson ──────────────────────────────────────────────────────
    (r'\braw\b|\bunprepared\b',                 'etat_cuisson',    'cru',         'high'),
    (r'\bcooked\b|\bprepared\b',                'etat_cuisson',    'cuit',        'high'),
    (r'\bboiled\b',                             'etat_cuisson',    'cuit',        'high'),
    (r'\bsteamed\b',                            'etat_cuisson',    'cuit_vapeur', 'high'),
    (r'\bfried\b',                              'etat_cuisson',    'frit',        'high'),
    (r'\broasted\b',                            'etat_cuisson',    'roti',        'high'),
    (r'\bbaked\b',                              'etat_cuisson',    'cuit au four','high'),
    (r'\bgrilled\b|\bbroiled\b',                'etat_cuisson',    'grille',      'high'),
    (r'\bbraised\b',                            'etat_cuisson',    'braise',      'high'),
    (r'\bsauteed\b|\bstir.fried\b',             'etat_cuisson',    'saute',       'high'),
    (r'\bdeep.fried\b|\bpan.fried\b',           'etat_cuisson',    'frit',        'high'),
    (r'\bsmoked\b',                             'traitement',      'fume',        'high'),
    (r'\bfermented\b',                          'traitement',      'fermente',    'high'),

    # ── Etat thermique ───────────────────────────────────────────────────────
    (r'\bdried\b|\bdehydrated\b',               'etat_thermique',  'sec',         'high'),
    (r'\bfrozen\b',                             'etat_thermique',  'surgele',     'high'),
    (r'\bfresh\b',                              'etat_thermique',  'frais',       'high'),

    # ── Conditionnement ──────────────────────────────────────────────────────
    (r'\bcanned\b',                             'conditionnement', 'conserve',    'high'),
    (r'\bin water\b|\bin brine\b|\bin oil\b|\bin juice\b',
                                                'conditionnement', 'conserve',    'high'),
    (r'\bcanned or bottled\b|\bbottled\b',       'conditionnement', 'conserve',    'high'),

    # ── Egouttage ────────────────────────────────────────────────────────────
    (r'\bdrained\b',                            'egouttage_milieu','egoutte',     'high'),

    # ── Assaisonnement ───────────────────────────────────────────────────────
    (r'\bsalted\b|\bwith salt\b',               'assaisonnement',  'sale',        'high'),
    (r'\bsweetened\b|\bsugar added\b',           'assaisonnement',  'sucre',       'high'),
    (r'\bunsalted\b|\bwithout salt\b|\bno salt\b','assaisonnement', 'sans_sel',    'high'),
    (r'\bunsweetened\b|\bno sugar\b',            'assaisonnement',  'sans_sucre',  'high'),

    # ── Forme ────────────────────────────────────────────────────────────────
    (r'\bpowder\b|\bpowdered\b',                'forme',           'poudre',      'high'),
    (r'\bflakes\b',                             'forme',           'flocons',     'high'),
    (r'\bpuree\b|\bmashed\b',                   'forme',           'puree',       'high'),
    (r'\bground\b',                             'forme',           'moulu',       'high'),
    (r'\bsliced\b|\bin slices\b',               'forme',           'tranche',     'medium'),
    (r'\bchopped\b|\bminced\b',                 'forme',           'hache',       'medium'),
    (r'\bgrated\b|\bshredded\b',                'forme',           'rape',        'high'),
    (r'\bconcentrated\b|\bconcentrate\b',        'forme',           'concentre',   'high'),
    (r'\bpaste\b',                              'forme',           'pate',        'medium'),
    (r'\bflour\b',                              'forme',           'farine',      'high'),
    (r'\bgranulated\b',                         'forme',           'granule',     'high'),
    (r'\bcrumbled\b',                           'forme',           'emiette',     'medium'),
    (r'\bcrushed\b',                            'forme',           'concasse',    'medium'),
    (r'\bwhole\b(?!.*(grain|wheat|milk|egg))',   'forme',           'entier',      'medium'),

    # ── Partie ───────────────────────────────────────────────────────────────
    (r'\bwith skin\b|\bwith peel\b',            'partie',          'avec_peau',   'high'),
    (r'\bwithout skin\b|\bwithout peel\b|\bpeeled\b',
                                                'partie',          'sans_peau',   'high'),
    (r'\bwith seeds\b',                         'partie',          'avec_graines','high'),
    (r'\bwithout seeds\b|\bseeded\b',            'partie',          'sans_graines','high'),
    (r'\bfillets?\b',                           'partie',          'filet',       'medium'),
    (r'\bleaves\b',                             'partie',          'feuilles',    'medium'),
    (r'\bstalks?\b|\bstems?\b',                 'partie',          'tiges',       'medium'),
    (r'\bflesh\b|\bpulp\b',                     'partie',          'chair',       'medium'),
    (r'\bjuice\b',                              'partie',          'jus',         'medium'),

    # ── Teneur MG ────────────────────────────────────────────────────────────
    (r'\bskim\b|\bskimmed\b|\bnonfat\b|\bfat.?free\b',
                                                'teneur_MG',       'ecreme',      'high'),
    (r'\bpartly skim\b|\bpartially skim\b|\blow.fat\b|\breduced.fat\b',
                                                'teneur_MG',       'allege',      'high'),
    (r'\bwhole milk\b|\bfull.fat\b',             'teneur_MG',       'entier',      'high'),
    (r'\b2% fat\b|\b2% milk fat\b',              'teneur_MG',       'demi-ecreme', 'high'),
    (r'\b1% fat\b|\b1% milk fat\b',              'teneur_MG',       'allege',      'high'),
]


def detect_axes_en(name: str, existing: dict, cat_label: str) -> dict:
    suggestions = {}
    name_l = name.lower()
    for pattern, axe, valeur, conf in RULES_EN:
        if axe in existing or axe in suggestions:
            continue
        if not re.search(pattern, name_l):
            continue
        fp = is_fp(name, axe, cat_label)
        if fp:
            continue
        suggestions[axe] = (valeur, conf)
    return suggestions


# ── Audit + patch ─────────────────────────────────────────────────────────────
print('\nAnalyse variants USDA...')
stats   = defaultdict(int)
patches: list[dict] = []
errors:  list[dict] = []

v32_patched = copy.deepcopy(v32) if not DRY_RUN else v32

for cat in v32_patched.get('categories', []):
    cat_label = cat.get('label', '')
    for sub in cat.get('subcategories', []):
        for ig in sub.get('ingredient_groups', []):
            ig_id   = ig.get('id', '')
            name_en = ig.get('canonical_name_en', '')
            for vr in ig.get('variants', []):
                if vr.get('source', '').upper() != 'USDA':
                    continue
                stats['total'] += 1
                sid  = str(vr.get('source_id', '')).strip()
                name = usda_names.get(sid, '')
                if not name:
                    stats['not_found'] += 1
                    errors.append({'ig_id': ig_id, 'source_id': sid, 'name_en': name_en})
                    continue
                existing = vr.get('axes', {}) or {}
                sugg = detect_axes_en(name, existing, cat_label)
                if not sugg:
                    continue
                stats['patched'] += 1
                stats['axes'] += len(sugg)
                patches.append({
                    'ig_id': ig_id, 'name_en': name_en, 'source_id': sid,
                    'usda_name': name,
                    'added': {k: v[0] for k, v in sugg.items()},
                    'conf':  {k: v[1] for k, v in sugg.items()},
                    'axes_before': dict(existing),
                })
                if not DRY_RUN:
                    if not isinstance(vr.get('axes'), dict):
                        vr['axes'] = {}
                    for axe, (val, _) in sugg.items():
                        vr['axes'][axe] = val

# ── Ecriture ──────────────────────────────────────────────────────────────────
if not DRY_RUN:
    bk = V32_P.with_name(
        f'ingredients_v32_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    shutil.copy2(V32_P, bk)
    V32_P.write_text(
        json.dumps(v32_patched, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[OK] Backup -> {bk.name}')
    print(f'[OK] v32 mis a jour -> {V32_P}')

# ── Rapport ───────────────────────────────────────────────────────────────────
mode = 'DRY-RUN' if DRY_RUN else 'APPLIQUE'
print()
print('=' * 65)
print(f'  PATCH USDA AXES v32 -- {mode}')
print('=' * 65)
print(f'  Variants USDA total       : {stats["total"]}')
print(f'  IDs non trouves           : {stats["not_found"]}')
print(f'  Variants patches          : {stats["patched"]}')
print(f'  Axes ajoutes total        : {stats["axes"]}')
print()

by_axe = defaultdict(int)
for p in patches:
    for axe in p['added']:
        by_axe[axe] += 1
print('  Par axe :')
for axe, n in sorted(by_axe.items(), key=lambda x: -x[1]):
    print(f'    {axe:<25} : {n:>4}')

print()
print('  Apercu (30 premiers) :')
print('  ' + '-' * 62)
for p in patches[:30]:
    print(f'  [{p["ig_id"]}] {p["name_en"][:35]:<35}')
    print(f'    USDA: {p["usda_name"][:65]}')
    for axe, val in p['added'].items():
        cf = p['conf'].get(axe, '')
        print(f'    + {axe}: {val}  [{cf}]')
if len(patches) > 30:
    print(f'  ... et {len(patches) - 30} autres')

if errors:
    print(f'\n  IDs USDA introuvables ({len(errors)}) :')
    for e in errors[:10]:
        print(f'    [{e["ig_id"]}] fdcId={e["source_id"]}  {e["name_en"]}')

log = DATA / 'nutrition/logs/patch_usda_axes.json'
log.parent.mkdir(parents=True, exist_ok=True)
log.write_text(json.dumps({
    'mode': mode, 'stats': dict(stats), 'by_axe': dict(by_axe),
    'patches': patches, 'errors': errors,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n  Log -> {log}')
if DRY_RUN:
    print('\n  DRY-RUN -- relancer avec --apply pour appliquer.')
