#!/usr/bin/env python3
"""
update_axes_schema.py
Met a jour axes_schema.json avec:
  - Nouvelles valeurs trouvees dans le tree
  - Nouveaux axes absents du schema
  - Suppression de egouttage (desormais supprime du tree)
  - Mise a jour milieu_conservation (tree_key_fr seul, plus de liste)
  - Ajout bufflonne dans origin
"""
import json, sys, io
from collections import defaultdict
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

tree   = json.load(open('ingredients_tree_enriched_v2.json', encoding='utf-8'))
schema = json.load(open('axes_schema.json', encoding='utf-8'))

# ── Collecter toutes les valeurs reelles du tree ──────────────────────────
tree_vals_fr = defaultdict(set)
tree_vals_en = defaultdict(set)
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        for ing in cat2.get('ingredient_groups', []):
            for obj in [ing] + ing.get('variants', []):
                axes_fr = obj.get('axes_fr', {})
                axes_en = obj.get('axes_en', {})
                if isinstance(axes_fr, dict):
                    for k, v in axes_fr.items():
                        for val in (v if isinstance(v, list) else [v]):
                            if val: tree_vals_fr[k].add(str(val))
                if isinstance(axes_en, dict):
                    for k, v in axes_en.items():
                        for val in (v if isinstance(v, list) else [v]):
                            if val: tree_vals_en[k].add(str(val))

# ── Mapper tree_key_fr -> schema_key ─────────────────────────────────────
tree_fr_to_schema = {}
for sk, sv in schema['axes'].items():
    tk = sv.get('tree_key_fr')
    if isinstance(tk, list):
        for t in tk:
            tree_fr_to_schema[t] = sk
    elif tk:
        tree_fr_to_schema[tk] = sk

# ── 1. Corriger milieu_conservation : plus lie a egouttage ───────────────
if 'draining' in schema['axes']:
    schema['axes']['draining']['tree_key_fr'] = 'milieu_conservation'
    schema['axes']['draining']['name_fr'] = 'milieu de conservation'
    schema['axes']['draining']['name_en'] = 'conservation medium'
    # Retirer les valeurs liees a egouttage (drained) du champ milieu_conservation
    # drained = egouttage, pas milieu_conservation -> le retirer
    draining_vals = schema['axes']['draining'].get('values', {})
    draining_vals.pop('drained', None)
    print('FIX  draining: tree_key_fr = milieu_conservation, supprime drained')

# ── 2. Ajouter bufflonne dans origin ─────────────────────────────────────
origin_vals = schema['axes']['origin']['values']
if 'buffalo' not in origin_vals:
    origin_vals['buffalo'] = {'en': 'buffalo', 'fr': 'bufflonne'}
    print('ADD  origin.buffalo')
# S'assurer que bufflonne est bien la valeur fr
origin_vals['buffalo']['fr'] = 'bufflonne'

# ── 3. Nouvelles valeurs dans axes existants ─────────────────────────────
# Construire index des valeurs fr connues par axe schema
schema_known_fr = defaultdict(set)
for sk, sv in schema['axes'].items():
    for vk, vv in sv.get('values', {}).items():
        fr = vv.get('fr','')
        schema_known_fr[sk].add(fr.lower())

# Mapping manuel des nouvelles valeurs trouvees
NEW_VALUES = {
    # maturite: bebe (pour epinard baby, avoine)
    'ripeness': {
        'baby': {'en': 'baby', 'fr': 'bébé'},
    },
    # cooking state: grillee a sec, a l'huile (procede) -> on les met dans treatment
    'treatment': {
        'oil_roasted_explicit': {'en': 'grilled in oil', 'fr': "grillé à l'huile"},
        'dry_roasted_explicit': {'en': 'grilled dry', 'fr': 'grillé à sec'},
    },
    # form: steel cut deja dans schema, mais verifions paillettes, broye
    'form': {
        'flakes_thin': {'en': 'flakes', 'fr': 'paillettes'},
        'ground_coarse': {'en': 'ground', 'fr': 'broyé'},
        'pieces_small': {'en': 'small pieces', 'fr': 'petits morceaux'},
    },
    # origin: vegetal deja la, ajouter plant_based explicite
    'origin': {},
    # thermal_state: UHT deja, mature deja
}

added_vals = []
for sk, new_vals in NEW_VALUES.items():
    if sk not in schema['axes']: continue
    existing = schema['axes'][sk].setdefault('values', {})
    known_frs = {v.get('fr','').lower() for v in existing.values()}
    for vk, vv in new_vals.items():
        if vk not in existing and vv['fr'].lower() not in known_frs:
            existing[vk] = vv
            added_vals.append(f'{sk}.{vk} = {vv}')
            print(f'ADD  {sk}.{vk} ({vv["fr"]})')

# ── 4. Axes presents dans tree mais absents du schema ────────────────────
NEW_AXES = {}

# procede_cuisson (tree fr) = cooking method
if 'procede_cuisson' not in tree_fr_to_schema:
    NEW_AXES['cooking_method'] = {
        'name_en': 'cooking method',
        'name_fr': 'procédé de cuisson',
        'tree_key_fr': 'procede_cuisson',
        'values': {
            'dry': {'en': 'dry', 'fr': 'à sec'},
            'in_oil': {'en': 'in oil', 'fr': "à l'huile"},
        }
    }
    print('ADD  axe cooking_method (procede_cuisson)')

# maturite -> schema a ripeness mais tree_key_fr pas set correctement ?
# Verifier
rip = schema['axes'].get('ripeness', {})
if rip.get('tree_key_fr') != 'maturite':
    schema['axes']['ripeness']['tree_key_fr'] = 'maturite'
    print('FIX  ripeness.tree_key_fr = maturite')

# Ajouter bebe dans ripeness
rip_vals = schema['axes']['ripeness'].setdefault('values', {})
if 'baby' not in rip_vals:
    rip_vals['baby'] = {'en': 'baby', 'fr': 'bébé'}
    print('ADD  ripeness.baby')

# sodium (deja dans schema mais tree_key_fr = None)
if schema['axes'].get('sodium', {}).get('tree_key_fr') is None:
    schema['axes']['sodium']['tree_key_fr'] = 'sodium'
    print('FIX  sodium.tree_key_fr = sodium')

# color, size, variety : tree_key_fr = None -> inchanges

for ak, av in NEW_AXES.items():
    schema['axes'][ak] = av

# ── 5. Verifier axes tree sans correspondance schema ─────────────────────
unmatched = []
for fr_key in sorted(tree_vals_fr.keys()):
    if fr_key not in tree_fr_to_schema:
        unmatched.append((fr_key, sorted(tree_vals_fr[fr_key])[:8]))

if unmatched:
    print()
    print('Axes tree sans mapping schema (info) :')
    for k, v in unmatched:
        print(f'  {k!r}: {v}')

# ── 6. Mettre a jour la date et sauvegarder ───────────────────────────────
schema['generated'] = str(date.today())
schema['version'] = '1.1'

json.dump(schema, open('axes_schema.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print()
print(f'axes_schema.json v{schema["version"]} sauvegarde.')
print('OK.')
