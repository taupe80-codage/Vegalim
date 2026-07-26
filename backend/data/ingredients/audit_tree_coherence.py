#!/usr/bin/env python3
"""
audit_tree_coherence.py
Audit de coherence globale du fichier ingredients_tree.json :
1. Doublons d'ID (ing_, var_)
2. Variants sans source_name_fr ET sans source_name_en
3. canonical_name_fr / canonical_name_en manquants ou vides
4. axes_fr de l'ing incoherent avec les axes_fr de ses variants
5. Ingredients sans aucun variant
6. Variants avec axes_fr inconnus du vocabulary
7. Ingredients dupliques (meme canonical_name_fr + meme axes_fr)
8. name_fr / name_en vides sur variants
9. Verifier que les IDs sont uniques et bien formates
10. Ingredients avec variants de sources differentes mais axes_fr identiques (fusion suspecte)
"""
import json
from pathlib import Path
from collections import defaultdict

BASE = Path(r'C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\backend\data\ingredients')
TREE_FILE = BASE / 'ingredients_tree.json'

tree = json.load(open(TREE_FILE, encoding='utf-8'))

# Charger le vocabulary si disponible
vocab_keys = set()
try:
    vocab = tree.get('meta', {}).get('axes_vocabulary', {})
    for axe, axe_def in vocab.items():
        if not axe.startswith('_'):
            vocab_keys.add(axe)
    print(f'Vocabulary charge : {len(vocab_keys)} axes')
except Exception as e:
    print(f'Vocabulary non charge : {e}')

# --- Collecte de tous les ing_ et var_ ----------------------------------------
all_ings = []   # (cat1_id, cat2_id, ing)
all_var_ids = defaultdict(list)  # var_id -> [(ing_id, cat2_id)]
all_ing_ids = defaultdict(list)  # ing_id -> [cat2_id]

for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        for ing in cat2.get('ingredient_groups', []):
            all_ings.append((cat1['id'], cat1.get('label',''), cat2['id'], cat2.get('label',''), ing))
            all_ing_ids[ing['id']].append(cat2['id'])
            for var in ing.get('variants', []):
                all_var_ids[var['id']].append((ing['id'], cat2['id']))

total_ings = len(all_ings)
total_vars = sum(len(ing.get('variants',[])) for _,_,_,_,ing in all_ings)
print(f'Total ing_ : {total_ings}')
print(f'Total var_ : {total_vars}')
print()

issues = defaultdict(list)

# --- 1. IDs dupliques ---------------------------------------------------------
dup_ings = {k: v for k, v in all_ing_ids.items() if len(v) > 1}
dup_vars = {k: v for k, v in all_var_ids.items() if len(v) > 1}
if dup_ings:
    for ing_id, cats in dup_ings.items():
        issues['ing_id_duplique'].append(f'{ing_id} dans {cats}')
if dup_vars:
    for var_id, ings in dup_vars.items():
        issues['var_id_duplique'].append(f'{var_id} dans {ings}')

# --- 2. canonical_name manquant -----------------------------------------------
for cat1_id, cat1_lbl, cat2_id, cat2_lbl, ing in all_ings:
    cfr = ing.get('canonical_name_fr', '')
    cen = ing.get('canonical_name_en', '')
    if not cfr or cfr in ('None', 'null'):
        issues['canonical_name_fr_manquant'].append(f"{ing['id']} [{cat2_lbl}]")
    if not cen or cen in ('None', 'null'):
        issues['canonical_name_en_manquant'].append(f"{ing['id']} {cfr} [{cat2_lbl}]")

# --- 3. Ingredients sans variants ---------------------------------------------
for cat1_id, cat1_lbl, cat2_id, cat2_lbl, ing in all_ings:
    if not ing.get('variants'):
        issues['sans_variant'].append(f"{ing['id']} {ing.get('canonical_name_fr','')} [{cat2_lbl}]")

# --- 4. Variants sans nom source ----------------------------------------------
# Exception : source=MANUAL n'a jamais de source_name_fr/en (pas d'origine
# CIQUAL/CNF/USDA a citer -- c'est attendu, pas une anomalie).
for cat1_id, cat1_lbl, cat2_id, cat2_lbl, ing in all_ings:
    for var in ing.get('variants', []):
        sfr = var.get('source_name_fr')
        sen = var.get('source_name_en')
        nfr = var.get('name_fr')
        nen = var.get('name_en')
        if var.get('source') != 'MANUAL' and (not sfr or sfr == 'None') and (not sen or sen == 'None'):
            issues['variant_sans_source_name'].append(
                f"{var['id']} (ing={ing['id']} {ing.get('canonical_name_fr','')}) src={var.get('source','')}")
        if not nfr or nfr == 'None':
            issues['variant_name_fr_vide'].append(
                f"{var['id']} (ing={ing['id']} {ing.get('canonical_name_fr','')}) src={var.get('source','')}")

# --- 5. Axes inconnus du vocabulary ------------------------------------------
if vocab_keys:
    for cat1_id, cat1_lbl, cat2_id, cat2_lbl, ing in all_ings:
        for axe in ing.get('axes_fr', {}).keys():
            if axe not in vocab_keys:
                issues['axe_inconnu_vocabulary'].append(
                    f"{ing['id']} {ing.get('canonical_name_fr','')} axe={axe}")
        for var in ing.get('variants', []):
            for axe in var.get('axes_fr', {}).keys():
                if axe not in vocab_keys:
                    issues['axe_inconnu_vocabulary'].append(
                        f"  var={var['id']} axe={axe}")

# --- 6. Ingredients dupliques (meme canonical_fr + meme axes) -----------------
seen_keys = defaultdict(list)
for cat1_id, cat1_lbl, cat2_id, cat2_lbl, ing in all_ings:
    key = ing.get('canonical_name_fr','') + '|' + str(sorted(ing.get('axes_fr',{}).items()))
    seen_keys[key].append((ing['id'], cat2_lbl))
for key, entries in seen_keys.items():
    if len(entries) > 1:
        issues['ing_duplique_axes'].append(f'{key} -> {entries}')

# --- 7. Incoherence axes ing vs variants (1 seul variant) --------------------
for cat1_id, cat1_lbl, cat2_id, cat2_lbl, ing in all_ings:
    variants = ing.get('variants', [])
    ing_axes = ing.get('axes_fr', {})
    if len(variants) == 1:
        var_axes = variants[0].get('axes_fr', {})
        # Chaque cle de ing_axes doit exister et avoir la meme valeur dans var_axes
        conflicts = {k: (v, var_axes.get(k)) for k, v in ing_axes.items()
                     if k in var_axes and var_axes[k] != v}
        if conflicts:
            issues['incoherence_ing_var_axes'].append(
                f"{ing['id']} {ing.get('canonical_name_fr','')} ing={ing_axes} var={var_axes}")

# --- 8. Fusion suspecte : plusieurs variants avec axes_fr identiques ----------
for cat1_id, cat1_lbl, cat2_id, cat2_lbl, ing in all_ings:
    variants = ing.get('variants', [])
    if len(variants) > 1:
        seen_var_axes = defaultdict(list)
        for var in variants:
            k = str(sorted(var.get('axes_fr', {}).items()))
            seen_var_axes[k].append(var['id'])
        for k, var_ids in seen_var_axes.items():
            if len(var_ids) > 1:
                issues['variants_axes_identiques'].append(
                    f"{ing['id']} {ing.get('canonical_name_fr','')} [{cat2_lbl}] -> {var_ids} axes={k}")

# --- 9. ing sans axes_fr dans une cat qui en requiert -------------------------
# (heuristique : si les autres ing de la meme cat2 ont des axes, celui-ci devrait en avoir)
for cat1_id, cat1_lbl, cat2_id, cat2_lbl, ing in all_ings:
    if not ing.get('axes_fr') and ing.get('variants'):
        # Verifier si certains variants ont des axes
        var_has_axes = any(v.get('axes_fr') for v in ing.get('variants', []))
        if var_has_axes:
            issues['ing_sans_axes_mais_variants_en_ont'].append(
                f"{ing['id']} {ing.get('canonical_name_fr','')} [{cat2_lbl}]")

# --- Rapport ------------------------------------------------------------------
print('=' * 72)
print('RAPPORT DE COHERENCE')
print('=' * 72)

LABELS = {
    'ing_id_duplique':               'IDs ing_ dupliques',
    'var_id_duplique':               'IDs var_ dupliques',
    'canonical_name_fr_manquant':    'canonical_name_fr manquant',
    'canonical_name_en_manquant':    'canonical_name_en manquant',
    'sans_variant':                  'Ingredients sans variant',
    'variant_sans_source_name':      'Variants sans source_name_fr ni source_name_en',
    'variant_name_fr_vide':          'Variants avec name_fr vide',
    'axe_inconnu_vocabulary':        'Axes inconnus du vocabulary',
    'ing_duplique_axes':             'Ingredients dupliques (meme nom+axes)',
    'incoherence_ing_var_axes':      'Incoherence axes ing vs variant unique',
    'variants_axes_identiques':      'Variants avec axes identiques (fusion suspecte)',
    'ing_sans_axes_mais_variants_en_ont': 'ing sans axes alors que ses variants en ont',
}

total_issues = 0
for key, label in LABELS.items():
    lst = issues[key]
    total_issues += len(lst)
    status = 'OK' if not lst else 'KO'
    print(f'\n[{status}] {label} : {len(lst)}')
    for item in lst[:25]:
        print(f'     {item}')
    if len(lst) > 25:
        print(f'     ... et {len(lst)-25} autres')

print()
print('=' * 72)
print(f'TOTAL ANOMALIES : {total_issues}')
print('=' * 72)
