#!/usr/bin/env python3
"""
fix_stock_reconstitution.py — Corrige les recettes qui dosent le bouillon
déshydraté (vegetable_stock_dried, CIQUAL 11041 : 287 kcal, 19 100 mg Na /100 g)
comme du bouillon liquide (« 1200 ml »).

Chaque ligne liquide devient deux lignes :
    vegetable_stock_dried  : poudre, dosée à STOCK_G_PER_100ML
    water                  : le volume d'origine

STOCK_G_PER_100ML est calibré sur CIQUAL 25948 « Bouillon de légumes,
déshydraté reconstitué » (240 mg Na /100 g) : 240 / 19 100 × 100 ≈ 1,26 g de
poudre pour 100 ml — soit à peu près un cube de 10-12 g par litre.

Une ligne est considérée « liquide » si unit == 'ml', ou si la quantité en g
dépasse LIQUID_THRESHOLD_G (aucun usage réel de poudre n'approche 30 g).

Usage :
    python scripts/recipes/fix_stock_reconstitution.py --dry-run
    python scripts/recipes/fix_stock_reconstitution.py
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECIPES = ROOT / 'backend/data/recipes/recipes.json'
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

STOCK_KEY = 'vegetable_stock_dried'
WATER_KEY = 'water'
STOCK_G_PER_100ML = 240 / 19100 * 100     # ≈ 1.257
LIQUID_THRESHOLD_G = 30


def is_liquid_dose(item: dict) -> bool:
    unit = (item.get('unit') or '').lower()
    qty = item.get('quantity')
    if not isinstance(qty, (int, float)) or qty <= 0:
        return False
    return unit == 'ml' or (unit == 'g' and qty > LIQUID_THRESHOLD_G)


def fix_recipe(recipe: dict) -> list[tuple]:
    changes = []
    new_comp = []
    for item in recipe.get('composition', []):
        if item.get('ingredient') == STOCK_KEY and is_liquid_dose(item):
            volume_ml = float(item['quantity'])
            powder_g = round(volume_ml * STOCK_G_PER_100ML / 100, 1)
            meta = dict(item.get('meta') or {})
            meta['note'] = f'bouillon déshydraté pour {volume_ml:g} ml d\'eau'
            new_comp.append({**item, 'quantity': powder_g, 'unit': 'g', 'meta': meta})
            new_comp.append({
                'ingredient': WATER_KEY, 'quantity': volume_ml, 'unit': 'ml',
                'meta': {'role': meta.get('role', 'liquid'), 'note': 'pour reconstituer le bouillon'},
            })
            changes.append((recipe['id'], item['quantity'], item.get('unit'), powder_g))
        else:
            new_comp.append(item)
    recipe['composition'] = new_comp
    return changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    raw = json.loads(RECIPES.read_text(encoding='utf-8'))
    changes = []
    for r in raw['recipes']:
        changes += fix_recipe(r)
    for c in changes[:10]:
        print(f'  {c[0]:45s} {c[1]:>7} {c[2]:<3} -> {c[3]} g poudre + eau')
    print(f'  … {len(changes)} lignes corrigées dans {len({c[0] for c in changes})} recettes')
    if args.dry_run:
        print('\n[DRY-RUN] Aucune écriture.')
        return
    tmp = RECIPES.with_suffix('.tmp')
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(RECIPES)
    print(f'\nÉcrit → {RECIPES}')


if __name__ == '__main__':
    main()
