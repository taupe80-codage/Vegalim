#!/usr/bin/env python3
"""
audit_axes_usage.py
Pour chaque axe et chaque valeur dans axes_vocabulary :
- Compte combien d'ingredient_groups l'utilisent
- Signale les axes/valeurs jamais utilises
"""
import json
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
tree = json.load(open(BASE / 'ingredients_tree.json', encoding='utf-8'))

vocab = tree['meta']['axes_vocabulary']

# --- Compter les usages dans les ingredient_groups ----------------------------
axis_key_count   = defaultdict(int)   # {axe: nb ing qui l'utilisent}
axis_value_count = defaultdict(lambda: defaultdict(int))  # {axe: {valeur: nb}}

for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        for ing in cat2.get('ingredient_groups', []):
            axes = ing.get('axes_fr', {})
            for k, v in axes.items():
                axis_key_count[k] += 1
                if isinstance(v, list):
                    for item in v:
                        axis_value_count[k][item] += 1
                else:
                    axis_value_count[k][v] += 1

# --- Affichage ----------------------------------------------------------------
print("=" * 72)
print("USAGE DES AXES (axes_vocabulary vs ingredients_tree)")
print("=" * 72)

for axe_name, axe_def in vocab.items():
    if axe_name.startswith('_'):
        continue

    valeurs = axe_def.get('valeurs', {})
    total_ing_with_axe = axis_key_count.get(axe_name, 0)
    never_used_axe = total_ing_with_axe == 0

    marker = " [JAMAIS UTILISE]" if never_used_axe else ""
    print(f"\n{'=' * 72}")
    print(f"  AXE : {axe_name}  ({total_ing_with_axe} ing. l'utilisent){marker}")
    print(f"{'=' * 72}")

    if valeurs:
        for val_key, val_desc in valeurs.items():
            count = axis_value_count[axe_name].get(val_key, 0)
            flag = "  <-- JAMAIS UTILISE" if count == 0 else ""
            print(f"    {val_key:<35} : {count:>5} ing.{flag}")

    # Valeurs utilisees dans le tree mais ABSENTES du vocabulary
    extra_vals = {
        k: v for k, v in axis_value_count[axe_name].items()
        if k not in valeurs
    }
    if extra_vals:
        print(f"  -- Valeurs utilisees HORS vocabulary --")
        for k, v in sorted(extra_vals.items(), key=lambda x: -x[1]):
            print(f"    {k:<35} : {v:>5} ing.  <-- NON DOCUMENTE")

# --- Axes utilises dans le tree mais ABSENTS du vocabulary -------------------
print(f"\n{'=' * 72}")
print("AXES UTILISES DANS LE TREE MAIS ABSENTS DU VOCABULARY")
print(f"{'=' * 72}")
extra_axes = {k: v for k, v in axis_key_count.items() if k not in vocab}
if extra_axes:
    for k, v in sorted(extra_axes.items(), key=lambda x: -x[1]):
        print(f"  {k:<35} : {v:>5} ing. utilises")
        for val, cnt in sorted(axis_value_count[k].items(), key=lambda x: -x[1]):
            print(f"    {val:<33} : {cnt:>5}")
else:
    print("  Aucun.")

# --- Recap final -----------------------------------------------------------
print(f"\n{'=' * 72}")
print("RECAP")
print(f"{'=' * 72}")
never_axes = [a for a in vocab if not a.startswith('_') and axis_key_count.get(a, 0) == 0]
print(f"  Axes vocabulary jamais utilises : {len(never_axes)}")
for a in never_axes:
    print(f"    - {a}")

never_vals = []
for axe_name, axe_def in vocab.items():
    if axe_name.startswith('_'):
        continue
    for val_key in axe_def.get('valeurs', {}):
        if axis_value_count[axe_name].get(val_key, 0) == 0:
            never_vals.append((axe_name, val_key))
print(f"\n  Valeurs vocabulary jamais utilisees : {len(never_vals)}")
for a, v in never_vals:
    print(f"    - {a}.{v}")
