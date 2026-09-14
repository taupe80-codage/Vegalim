#!/usr/bin/env python3
"""
fix_dict_allergens.py — Applique les règles de allergen_rules.py au
ingredients_dictionary.json EN PLACE, sans rebuild complet.

Ne modifie que `allergens_eu` et les flags d'exclusion de `diet_profile`
(uniquement vers False). Équivalent ciblé de ce que build_dict_v2.py
applique au rebuild complet — pratique pour corriger les règles sans
reconstruire tout le dico.

Usage :
    python scripts/nutrition/fix_dict_allergens.py --dry-run
    python scripts/nutrition/fix_dict_allergens.py
"""
import argparse, json, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from allergen_rules import (get_allergens, key_allergens, restrict_diet_profile,
                            is_explicitly_gluten_free)

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = Path(__file__).parents[2]
DICT = ROOT / 'backend/data/ingredients/ingredients_dictionary.json'


def fix(dico: dict) -> Counter:
    stats: Counter = Counter()
    for cat_label, cat in dico['categories'].items():
        for sub_label, sub in cat.get('subcategories', {}).items():
            for key, entry in sub.get('ingredient_groups', {}).items():
                before_al = set(entry.get('allergens_eu') or [])
                al = before_al | set(get_allergens(cat_label, sub_label)) | key_allergens(key, sub_label)
                if is_explicitly_gluten_free(key):
                    al.discard('cereals_gluten')
                for a in al - before_al:
                    stats[f'+{a}'] += 1
                for a in before_al - al:
                    stats[f'-{a}'] += 1
                entry['allergens_eu'] = sorted(al)

                dp = entry.setdefault('diet_profile', {})
                before_dp = dict(dp)
                restrict_diet_profile(dp, al, key, sub_label)
                for f, v in dp.items():
                    if before_dp.get(f) != v:
                        stats[f'{f} {before_dp.get(f)}->{v}'] += 1
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    dico = json.loads(DICT.read_text(encoding='utf-8'))
    stats = fix(dico)
    for k, n in sorted(stats.items()):
        print(f'  {n:4d}  {k}')
    if args.dry_run:
        print('\n[DRY-RUN] Aucune écriture.')
        return
    tmp = DICT.with_suffix('.tmp')
    tmp.write_text(json.dumps(dico, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(DICT)
    print(f'\nÉcrit → {DICT}')


if __name__ == '__main__':
    main()
