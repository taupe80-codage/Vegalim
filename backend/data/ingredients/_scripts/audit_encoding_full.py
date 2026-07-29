#!/usr/bin/env python3
"""
audit_encoding_full.py
Audit complet de tous les caracteres non-ASCII dans le tree.
Classe chaque chaine par type de probleme potentiel.
"""
import json, unicodedata
from pathlib import Path
from collections import defaultdict

BASE = Path(__file__).resolve().parent.parent
tree = json.load(open(BASE / 'ingredients_tree.json', encoding='utf-8'))

# Collecter toutes les chaines uniques avec leur contexte
all_strings = []

def collect(v, ctx=''):
    if isinstance(v, str):
        all_strings.append((ctx, v))
    elif isinstance(v, dict):
        for k, val in v.items():
            collect(val, ctx + '.' + k)
    elif isinstance(v, list):
        for item in v:
            collect(item, ctx)

collect(tree)
print(f'Total chaines : {len(all_strings)}')

# Categoriser les anomalies
latin1_private   = []   # chars U+0080-U+009F (latin-1 "C1 controls" - jamais voulus)
latin1_chars_ok  = []   # chars U+00A0-U+00FF normaux (accents, etc.) - OK
high_unicode     = []   # chars > U+00FF (OK si voulus)
replacement_char = []   # U+FFFD (char de remplacement - toujours une erreur)
label_fr_issues  = []   # label_fr specifiquement

for ctx, s in all_strings:
    for c in s:
        o = ord(c)
        if o == 0xFFFD:
            replacement_char.append((ctx, s[:100]))
            break
        if 0x0080 <= o <= 0x009F:
            latin1_private.append((ctx, s[:100], hex(o), c))
            break

# Chercher les label_fr
for ctx, s in all_strings:
    if 'label_fr' in ctx or 'label' in ctx:
        has_issue = any(ord(c) > 0x7F for c in s)
        if has_issue:
            label_fr_issues.append((ctx, s))

# Trouver les 2 chaines suspectes detectees precedemment
suspects_pates = [(ctx, s) for ctx, s in all_strings if 'TES' in s and any(ord(c) > 0x7F for c in s)]

print(f'\nChars U+FFFD (remplacement) : {len(replacement_char)}')
for ctx, s in replacement_char[:5]:
    print(f'  [{ctx}] {s[:60]}')

print(f'\nChars U+0080-U+009F (C1 controls, anomalie) : {len(latin1_private)}')
for ctx, s, h, c in latin1_private[:10]:
    print(f'  [{ctx}] char={h} dans : {s[:60]}')

print(f'\nLabel_fr avec accents (pour inspection visuelle) :')
for ctx, s in label_fr_issues[:30]:
    print(f'  {s}')

print(f'\nChaines contenant PATES/TES :')
for ctx, s in suspects_pates[:10]:
    codes = [hex(ord(c)) for c in s]
    print(f'  [{ctx}] {s}')
    print(f'  codes : {codes}')
