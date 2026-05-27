"""
audit_cnf_v32.py
================
Compare les entrées CNF de ingredients_v32.json avec FOOD_NAME.csv :
  1. Noms : source_label v32 vs nom officiel CNF
  2. Axes : détecte les axes probablement manquants ou superflus
             en analysant le nom officiel CNF
"""
import json, re, sys, csv
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')

ROOT    = Path(__file__).parents[2]
DATA    = ROOT / 'backend/data'
V32_P   = DATA / 'ingredients/ingredients_v32.json'
CNF_P   = DATA / 'nutrition/raw/cnf/FOOD_NAME.csv'
OUT_P   = DATA / 'nutrition/logs/audit_cnf_v32.json'
OUT_P.parent.mkdir(parents=True, exist_ok=True)

# ── Charger CNF FOOD_NAME ────────────────────────────────────────────────────
print('Chargement CNF FOOD_NAME.csv...')
cnf_names: dict[str, dict] = {}   # FoodCode → {fr, en}
with open(CNF_P, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        code = str(row.get('FoodID', '') or row.get('FoodCode', '') or '').strip()
        lang = (row.get('FoodDescriptionF', '') or '').strip()  # peut être 'LanguageCode'
        # Détecter les colonnes disponibles
        if not code:
            code = str(row.get('food_code', '') or '').strip()
        # Selon le format CNF, les colonnes peuvent varier
        en_name = (row.get('FoodDescription', '')
                   or row.get('food_description', '')
                   or row.get('FoodDescriptionF', '')).strip()
        fr_name = (row.get('FoodDescriptionF', '')
                   or row.get('food_description_f', '')).strip()
        if code:
            if code not in cnf_names:
                cnf_names[code] = {'en': en_name, 'fr': fr_name}
            elif not cnf_names[code]['en'] and en_name:
                cnf_names[code]['en'] = en_name

print(f'  {len(cnf_names)} entrées CNF chargées')

# Afficher les premières colonnes disponibles pour debug
with open(CNF_P, newline='', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    cols = reader.fieldnames
    print(f'  Colonnes : {cols}')
    first = next(reader, None)
    if first:
        print(f'  Première ligne : {dict(first)}')

# ── Charger v32 ──────────────────────────────────────────────────────────────
print('\nChargement v32...')
v32 = json.loads(V32_P.read_text(encoding='utf-8'))

# ── Patterns détection d'axes depuis le nom officiel ─────────────────────────
# Ces patterns sont appliqués sur le nom CNF anglais pour détecter un état implicite

AXES_PATTERNS = [
    # (regex sur nom, axe_suggéré, valeur_suggérée)
    (r'\braw\b',                    'etat_cuisson', 'cru'),
    (r'\bcooked\b',                  'etat_cuisson', 'cuit'),
    (r'\bboiled\b',                  'etat_cuisson', 'cuit'),
    (r'\bsteamed\b',                 'etat_cuisson', 'cuit'),
    (r'\bfried\b',                   'etat_cuisson', 'frit'),
    (r'\broasted\b',                 'etat_cuisson', 'rôti'),
    (r'\bbaked\b',                   'etat_cuisson', 'cuit au four'),
    (r'\bdried\b',                   'etat_thermique', 'sec'),
    (r'\bdehydrated\b',              'etat_thermique', 'sec'),
    (r'\bfrozen\b',                  'etat_thermique', 'surgelé'),
    (r'\bcanned\b',                  'conditionnement', 'conserve'),
    (r'\bin (water|brine|oil|juice)\b', 'conditionnement', 'conserve'),
    (r'\bsalted\b',                  'assaisonnement', 'salé'),
    (r'\bsweetened\b',               'assaisonnement', 'sucré'),
    (r'\bwhole\b',                   'forme', 'entier'),
    (r'\bground\b',                  'forme', 'moulu'),
    (r'\bcrushed\b',                 'forme', 'concassé'),
    (r'\bpowder\b|\bpowdered\b',     'forme', 'poudre'),
    (r'\bsliced\b',                  'forme', 'tranché'),
    (r'\bpuree\b|\bmashed\b',        'forme', 'purée'),
    (r'\bpeeled\b',                  'partie', 'pelé'),
    (r'\bwith skin\b|\bwith peel\b', 'partie', 'avec peau'),
    (r'\bwithout skin\b',            'partie', 'sans peau'),
    (r'\bfresh\b',                   'etat_thermique', 'frais'),
    (r'\blow.fat\b|\breduced.fat\b', 'teneur_MG', 'allégé'),
    (r'\bskim\b|\bskimmed\b',        'teneur_MG', 'écrémé'),
    (r'\bwhole.milk\b|\bfull.fat\b', 'teneur_MG', 'entier'),
    (r'\bdrained\b',                 'egouttage_milieu', 'égoutté'),
    (r'\bunprepared\b',              'etat_cuisson', 'cru'),
    (r'\bprepared\b',                'etat_cuisson', 'préparé'),
]

def detect_axes_from_name(name: str) -> dict[str, str]:
    """Suggère des axes depuis le nom officiel CNF."""
    name_l = name.lower()
    suggested = {}
    for pattern, axe, valeur in AXES_PATTERNS:
        if re.search(pattern, name_l):
            suggested.setdefault(axe, valeur)
    return suggested

# ── Audit ────────────────────────────────────────────────────────────────────
issues: list[dict] = []
stats = defaultdict(int)

for cat in v32.get('categories', []):
    cat_label = cat.get('label', '')
    for sub in cat.get('subcategories', []):
        sub_label = sub.get('label', '')
        for ig in sub.get('ingredient_groups', []):
            ig_id    = ig.get('id', '')
            name_en  = ig.get('canonical_name_en', '')
            name_fr  = ig.get('canonical_name_fr', '')

            for vr in ig.get('variants', []):
                if vr.get('source', '').upper() != 'CNF':
                    continue

                stats['cnf_total'] += 1
                sid  = str(vr.get('source_id', '')).strip()
                axes = vr.get('axes', {}) or {}

                # Lookup CNF officiel
                cnf_entry = cnf_names.get(sid)
                if not cnf_entry:
                    stats['not_found'] += 1
                    issues.append({
                        'type': 'CNF_NOT_FOUND',
                        'severity': 'ERROR',
                        'ig_id': ig_id,
                        'canonical_name_en': name_en,
                        'source_id': sid,
                        'axes': axes,
                        'message': f'source_id CNF {sid} absent de FOOD_NAME.csv'
                    })
                    continue

                official_en = cnf_entry['en']
                official_fr = cnf_entry['fr']

                # 1. Vérifier axes depuis le nom officiel
                suggested = detect_axes_from_name(official_en)
                missing_axes = {k: v for k, v in suggested.items() if k not in axes}
                extra_axes   = {k: v for k, v in axes.items() if k not in suggested and k != 'etat_cuisson'}

                if missing_axes:
                    stats['missing_axes'] += 1
                    issues.append({
                        'type': 'MISSING_AXES',
                        'severity': 'WARNING',
                        'ig_id': ig_id,
                        'canonical_name_en': name_en,
                        'source_id': sid,
                        'official_name_en': official_en,
                        'axes_current': axes,
                        'axes_missing': missing_axes,
                        'message': f'Axes possiblement manquants selon nom CNF officiel'
                    })

                # 2. Vérifier le nom : différence significative ?
                # On normalise les deux et on compare
                def norm(s): return re.sub(r'[^a-z0-9]', ' ', s.lower()).strip()
                v32_words = set(norm(name_en).split())
                cnf_words = set(norm(official_en).split())
                # Mots importants dans CNF absents de v32
                import_words = cnf_words - v32_words - {'and','or','the','with','in','of','a','an','for'}
                if len(import_words) >= 2 and len(cnf_words) > 2:
                    stats['name_mismatch'] += 1
                    issues.append({
                        'type': 'NAME_MISMATCH',
                        'severity': 'INFO',
                        'ig_id': ig_id,
                        'canonical_name_en': name_en,
                        'source_id': sid,
                        'official_name_en': official_en,
                        'official_name_fr': official_fr,
                        'extra_cnf_words': sorted(import_words),
                        'message': f'Nom v32 potentiellement incomplet vs officiel CNF'
                    })

# ── Rapport ──────────────────────────────────────────────────────────────────
print()
print('=' * 65)
print('  AUDIT CNF v32')
print('=' * 65)
print(f'  CNF variants dans v32     : {stats["cnf_total"]}')
print(f'  IDs non trouvés dans CSV  : {stats["not_found"]}')
print(f'  Axes possiblement manqts  : {stats["missing_axes"]}')
print(f'  Noms potentiellement diff : {stats["name_mismatch"]}')
print()

# Grouper par type
by_type = defaultdict(list)
for iss in issues:
    by_type[iss['type']].append(iss)

# Afficher les erreurs critiques
print('── CNF IDs introuvables (ERRORS) ──────────────────────────────')
for iss in by_type['CNF_NOT_FOUND'][:20]:
    print(f'  {iss["ig_id"]}  source_id={iss["source_id"]}')
if len(by_type['CNF_NOT_FOUND']) > 20:
    print(f'  ... et {len(by_type["CNF_NOT_FOUND"]) - 20} autres')

print()
print('── Axes manquants (WARNINGS, top 30) ──────────────────────────')
for iss in by_type['MISSING_AXES'][:30]:
    print(f'  [{iss["ig_id"]}] {iss["canonical_name_en"][:40]:<40}')
    print(f'    CNF: {iss["official_name_en"][:70]}')
    print(f'    axes_actuel  : {iss["axes_current"]}')
    print(f'    axes_manqts  : {iss["axes_missing"]}')

print()
print('── Noms potentiellement différents (INFO, top 20) ─────────────')
for iss in by_type['NAME_MISMATCH'][:20]:
    print(f'  [{iss["ig_id"]}] v32: {iss["canonical_name_en"][:35]:<35}  →  CNF: {iss["official_name_en"][:50]}')

# Écrire JSON
OUT_P.write_text(json.dumps({
    'stats': dict(stats),
    'issues': issues,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n  Rapport complet → {OUT_P}')
