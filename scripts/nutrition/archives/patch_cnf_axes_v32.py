"""
patch_cnf_axes_v32.py
=====================
Applique les axes manquants dans ingredients_v32.json pour les variants CNF,
en s'appuyant sur les noms officiels FOOD_NAME.csv.

Stratégie : uniquement les cas HAUTE CONFIANCE.
Faux positifs courants exclus explicitement.

Mode : par défaut DRY-RUN (affiche sans modifier).
       --apply pour modifier v32.
"""
import json, re, sys, csv, copy
from pathlib import Path
from collections import defaultdict

sys.stdout.reconfigure(encoding='utf-8')
DRY_RUN = '--apply' not in sys.argv

ROOT  = Path(__file__).parents[2]
DATA  = ROOT / 'backend/data'
V32_P = DATA / 'ingredients/ingredients_v32.json'
CNF_P = DATA / 'nutrition/raw/cnf/FOOD_NAME.csv'

# ── Charger CNF ──────────────────────────────────────────────────────────────
cnf_names: dict[str, str] = {}
with open(CNF_P, newline='', encoding='utf-8-sig') as f:
    for row in csv.DictReader(f):
        code = str(row.get('FoodCode', '') or row.get('FoodID', '')).strip()
        en   = (row.get('FoodDescription', '')).strip()
        if code and en:
            cnf_names[code] = en

# ── Charger v32 ──────────────────────────────────────────────────────────────
v32 = json.loads(V32_P.read_text(encoding='utf-8'))


# ══════════════════════════════════════════════════════════════════════════════
# RÈGLES DE DÉTECTION — HAUTE CONFIANCE UNIQUEMENT
# ══════════════════════════════════════════════════════════════════════════════

# Catégories où "raw" / "dried" / "fresh" ne sont PAS des axes pertinents
# car l'ingrédient est toujours dans cet état par nature.
SKIP_RAW_CATS  = {'spices_and_herbs', 'leavening_agents_and_additives',
                  'condiments_and_sauces', 'fats_and_oils'}
SKIP_DRIED_CATS = {'spices_and_herbs', 'leavening_agents_and_additives'}

# Faux positifs lexicaux : patterns à IGNORER dans certains contextes
FALSE_POSITIVE_PATTERNS: list[tuple] = [
    # (regex_sur_nom_cnf, axe, explication)
    # "whole-grain" / "whole-wheat" ne signifie pas forme=entier mais traitement
    (r'whole.grain|whole.wheat|whole.groat', 'forme',          'whole ici = type de grain, pas forme physique'),
    # "raw sugar" = sucre non raffiné, pas état de cuisson
    (r'raw sugar',                           'etat_cuisson',   'raw sugar = non raffiné, pas cru'),
    # "ground" dans noms d'épices = état normal, pas un axe forme
    (r'\bground\b.*(cinnamon|pepper|spice|cumin|coriander|cardamom|allspice|nutmeg|clove|ginger|turmeric)',
                                             'forme',          'épice moulue = état par défaut'),
    # "fresh" dans "fresh water" (poissons eau douce) = pas état thermique
    (r'fresh.?water',                        'etat_thermique', 'freshwater = eau douce, pas frais'),
    # "salted" dans "salted butter" est déjà capturé par assaisonnement mais
    # "beurre salé" est un ingrédient distinct → conserver l'axe en fait
    # "powder" dans "chili powder" / "curry powder" = ingrédient spécifique, pas forme
    (r'(chili|chile|curry|garlic|onion|mustard|cayenne|paprika).+powder',
                                             'forme',          'poudre épice = identité de l\'ingrédient'),
    # "canned" dans "canned goods" génériques — pas de cas CNF direct
    # "boiled" dans "hard-boiled egg" = cuisson spécifique OK, pas exclu
    # "dried" pour les légumineuses (haricots secs) = état normal, pas un axe utile
    # on laisse passer car c'est bien un état_thermique discriminant
]

def is_false_positive(cnf_name: str, axe: str, cat_label: str) -> str | None:
    """Retourne l'explication si c'est un faux positif, sinon None."""
    name_l = cnf_name.lower()
    # Règles par catégorie
    if axe == 'etat_cuisson' and cat_label in SKIP_RAW_CATS:
        return f'cat={cat_label} → raw/cooked non pertinent'
    if axe == 'etat_thermique' and cat_label in SKIP_DRIED_CATS:
        return f'cat={cat_label} → dried non pertinent (état par défaut)'
    # Règles lexicales
    for pattern, fp_axe, reason in FALSE_POSITIVE_PATTERNS:
        if fp_axe == axe and re.search(pattern, name_l):
            return reason
    return None


# ── RÈGLES DE DÉDUCTION — uniquement si non-faux positif ────────────────────
# Format : (regex_cnf, axe, valeur, confiance)
# confiance = 'high' | 'medium'
RULES: list[tuple] = [
    # État de cuisson
    (r'\braw\b',                          'etat_cuisson',   'cru',             'high'),
    (r'\bcooked\b',                       'etat_cuisson',   'cuit',            'high'),
    (r'\bboiled\b',                       'etat_cuisson',   'cuit',            'high'),
    (r'\bsteamed\b',                      'etat_cuisson',   'cuit_vapeur',     'high'),
    (r'\bfried\b',                        'etat_cuisson',   'frit',            'high'),
    (r'\broasted\b',                      'etat_cuisson',   'rôti',            'high'),
    (r'\bbaked\b',                        'etat_cuisson',   'cuit au four',    'high'),
    (r'\bunprepared\b',                   'etat_cuisson',   'cru',             'high'),
    # État thermique
    (r'\bdried\b|\bdehydrated\b',         'etat_thermique', 'sec',             'high'),
    (r'\bfrozen\b',                       'etat_thermique', 'surgelé',         'high'),
    (r'\bfresh\b',                        'etat_thermique', 'frais',           'high'),
    # Conditionnement
    (r'\bcanned\b',                       'conditionnement','conserve',        'high'),
    (r'\bin (water|brine|oil|juice)\b',   'conditionnement','conserve',        'high'),
    (r'\bcanned or bottled\b',            'conditionnement','conserve',        'high'),
    # Égouttage
    (r'\bdrained\b',                      'egouttage_milieu','égoutté',        'high'),
    # Assaisonnement
    (r'\bsalted\b',                       'assaisonnement', 'salé',            'high'),
    (r'\bwith salt\b',                    'assaisonnement', 'salé',            'high'),
    (r'\bsweetened\b',                    'assaisonnement', 'sucré',           'high'),
    (r'\bsugar added\b',                  'assaisonnement', 'sucré',           'high'),
    # Forme
    (r'\bpowder\b|\bpowdered\b',          'forme',          'poudre',          'high'),
    (r'\bflakes\b',                       'forme',          'flocons',         'high'),
    (r'\bpaste\b',                        'forme',          'pâte',            'medium'),
    # Partie
    (r'\bwith skin\b|\bwith peel\b',      'partie',         'avec peau',       'high'),
    (r'\bwithout skin\b|\bwithout peel\b','partie',         'sans peau',       'high'),
    (r'\bpeeled\b',                       'partie',         'pelé',            'high'),
    (r'\bwith seeds\b',                   'partie',         'avec graines',    'high'),
    # Teneur MG
    (r'\bskim\b|\bskimmed\b',             'teneur_MG',      'écrémé',          'high'),
    (r'\bpartly skim\b|\bpartially skim\b','teneur_MG',     'demi-écrémé',     'high'),
    (r'\bfull.fat\b|\bwhole.milk\b',      'teneur_MG',      'entier',          'high'),
    (r'\blow.fat\b|\breduced.fat\b',      'teneur_MG',      'allégé',          'high'),
]

def detect_axes(cnf_name: str, existing_axes: dict, cat_label: str) -> dict[str, tuple]:
    """
    Retourne {axe: (valeur, confiance)} pour les axes à ajouter.
    Ne propose que ceux absents des axes existants.
    Filtre les faux positifs.
    """
    suggestions: dict[str, tuple] = {}
    name_l = cnf_name.lower()

    for pattern, axe, valeur, conf in RULES:
        if axe in existing_axes:
            continue  # déjà renseigné
        if axe in suggestions:
            continue  # déjà suggéré par une règle précédente
        if not re.search(pattern, name_l):
            continue
        fp_reason = is_false_positive(cnf_name, axe, cat_label)
        if fp_reason:
            continue
        suggestions[axe] = (valeur, conf)

    return suggestions


# ── Appliquer le patch ────────────────────────────────────────────────────────
stats    = defaultdict(int)
changes: list[dict] = []

v32_patched = copy.deepcopy(v32) if not DRY_RUN else v32

for cat_i, cat in enumerate(v32_patched.get('categories', [])):
    cat_label = cat.get('label', '')
    for sub in cat.get('subcategories', []):
        sub_label = sub.get('label', '')
        for ig in sub.get('ingredient_groups', []):
            ig_id   = ig.get('id', '')
            name_en = ig.get('canonical_name_en', '')
            for vr in ig.get('variants', []):
                if vr.get('source', '').upper() != 'CNF':
                    continue
                sid = str(vr.get('source_id', '')).strip()
                cnf_name = cnf_names.get(sid, '')
                if not cnf_name:
                    continue
                existing_axes = vr.get('axes', {}) or {}
                suggestions   = detect_axes(cnf_name, existing_axes, cat_label)
                if not suggestions:
                    continue

                stats['variants_patched'] += 1
                stats['axes_added'] += len(suggestions)
                rec = {
                    'ig_id':     ig_id,
                    'name_en':   name_en,
                    'source_id': sid,
                    'cnf_name':  cnf_name,
                    'added':     {k: v[0] for k, v in suggestions.items()},
                    'conf':      {k: v[1] for k, v in suggestions.items()},
                    'axes_before': dict(existing_axes),
                }
                changes.append(rec)

                if not DRY_RUN:
                    # Appliquer dans la copie profonde
                    if 'axes' not in vr or vr['axes'] is None:
                        vr['axes'] = {}
                    for axe, (val, _) in suggestions.items():
                        vr['axes'][axe] = val

# ── Écrire si --apply ─────────────────────────────────────────────────────────
if not DRY_RUN:
    # Backup
    import shutil
    from datetime import datetime
    bk = V32_P.with_name(f'ingredients_v32_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
    shutil.copy2(V32_P, bk)
    V32_P.write_text(json.dumps(v32_patched, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'[OK] Backup → {bk.name}')
    print(f'[OK] v32 mis à jour → {V32_P}')

# ── Rapport ───────────────────────────────────────────────────────────────────
mode = 'DRY-RUN' if DRY_RUN else 'APPLIQUÉ'
print()
print('=' * 65)
print(f'  PATCH CNF AXES v32 — {mode}')
print('=' * 65)
print(f'  Variants CNF patchés : {stats["variants_patched"]}')
print(f'  Axes ajoutés total   : {stats["axes_added"]}')
print()

# Résumé par axe ajouté
by_axe = defaultdict(int)
for c in changes:
    for axe in c['added']:
        by_axe[axe] += 1
print('  Par axe :')
for axe, n in sorted(by_axe.items(), key=lambda x: -x[1]):
    print(f'    {axe:<25} : {n:>3}')

print()
print(f'  Aperçu (30 premiers) :')
print('  ' + '─' * 62)
for c in changes[:30]:
    print(f'  [{c["ig_id"]}] {c["name_en"][:33]:<33}')
    print(f'    CNF: {c["cnf_name"][:60]}')
    for axe, val in c['added'].items():
        print(f'    + {axe}: {val}')

if len(changes) > 30:
    print(f'  ... et {len(changes)-30} autres variants')

# Écrire le log
log_path = DATA / 'nutrition/logs/patch_cnf_axes.json'
log_path.parent.mkdir(parents=True, exist_ok=True)
log_path.write_text(json.dumps({
    'mode': mode,
    'stats': dict(stats),
    'by_axe': dict(by_axe),
    'changes': changes,
}, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'\n  Log complet → {log_path}')

if DRY_RUN:
    print()
    print('  ⚠ DRY-RUN — aucune modification. Relancer avec --apply pour appliquer.')
