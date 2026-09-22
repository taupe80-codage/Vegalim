#!/usr/bin/env python3
"""
fix_recipe_diet_allergens.py — Propage le dictionnaire d'ingrédients
(allergens_eu / diet_profile) vers recipes.json, dans le sens restrictif
uniquement.

  - diet_flags (vegan, vegetarian, gluten_free, lactose_free, nut_free) :
    recalculés par compute_diet_flags ; seul True -> False est appliqué.
    Les False posés à la main (ex. gluten_free=False que le calcul ne voit
    pas) sont conservés.
  - tags.diet : retire les régimes contredits par un flag passé à False.
  - tags.allergens : ajoute les allergènes des ingrédients (vocabulaire des
    recettes : gluten, soy, milk + lactose…) et ceux des sous-recettes base_*.
  - tags.allergens : retire un tag UNIQUEMENT s'il contredit un flag de régime
    vrai (ex. 'eggs' sur une recette vegan) ET qu'aucun ingrédient ni
    sous-recette ne le justifie — restes des versions non vegan des plats
    (160 cas au 2026-09-14). Les autres tags sans ingrédient correspondant
    sont conservés (ex. céleri des bouillons du commerce).
  - vocabulaire : 'cereals_gluten' (dico) → 'gluten' (recettes).

Les lignes meta.role == 'serving_suggestion' (accompagnements optionnels,
ex. « toasts » avec une confiture) sont ignorées : elles ne font pas partie
de la recette.

Itère jusqu'au point fixe pour propager à travers les sous-recettes.

À relancer après toute correction du dictionnaire (fix_dict_allergens.py ou
build_dict_v2.py), puis rebuild_graphs.py.

Usage :
    python scripts/recipes/fix_recipe_diet_allergens.py --dry-run
    python scripts/recipes/fix_recipe_diet_allergens.py
"""
import argparse, json, logging, sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
logging.disable(logging.WARNING)

from backend.engine.config import RECIPES_PATH
from backend.db.culinary_repositories import IngredientRepository, _recipes_raw
from backend.engine.rule_engine.diet import compute_diet_flags

DIET_FLAGS = ('vegan', 'vegetarian', 'gluten_free', 'lactose_free', 'nut_free')
# allergens_eu (dico) -> vocabulaire tags.allergens (recettes)
ALLERGEN_TAG = {
    'cereals_gluten': ['gluten'], 'soybeans': ['soy'], 'milk': ['milk', 'lactose'],
    'eggs': ['eggs'], 'tree_nuts': ['tree_nuts'], 'peanuts': ['peanuts'],
    'sesame': ['sesame'], 'celery': ['celery'], 'mustard': ['mustard'],
    'sulphites': ['sulphites'], 'lupin': ['lupin'],
}


# flag de régime vrai → tags d'allergènes qu'il exclut
FLAG_EXCLUDES = {
    'vegan':        {'milk', 'lactose', 'eggs'},
    'lactose_free': {'milk', 'lactose'},
    'gluten_free':  {'gluten'},
    'nut_free':     {'tree_nuts', 'peanuts'},
}
TAG_ALIASES = {'cereals_gluten': 'gluten', 'soybeans': 'soy'}


def _core_composition(recipe: dict) -> list[dict]:
    return [c for c in recipe.get('composition', []) or []
            if isinstance(c, dict) and (c.get('ingredient') or c.get('ingredient_id'))
            and (c.get('meta') or {}).get('role') != 'serving_suggestion']


def one_pass(recipes: list[dict], repo: IngredientRepository, stats: Counter) -> int:
    by_id = {r['id']: r for r in recipes}
    changed = 0
    for r in recipes:
        flags = r.setdefault('diet_flags', {})
        computed = compute_diet_flags({**r, 'composition': _core_composition(r)})
        tags = r.setdefault('tags', {})
        diet_tags = tags.setdefault('diet', [])
        for f in DIET_FLAGS:
            if flags.get(f) is True and computed.get(f) is False:
                flags[f] = False
                stats[f'diet_flags.{f} True->False'] += 1
                changed += 1
            if flags.get(f) is False and f in diet_tags:
                diet_tags.remove(f)
                stats[f'tags.diet -{f}'] += 1
                changed += 1

        allergens = tags.setdefault('allergens', [])
        wanted: set[str] = set()
        for c in _core_composition(r):
            iid = str(c.get('ingredient') or c.get('ingredient_id'))
            item = repo.get_by_name(iid)
            if item and item.get('allergens_eu'):
                found = item['allergens_eu']
            elif iid in by_id:
                found = (by_id[iid].get('tags') or {}).get('allergens') or []
            else:
                found = []
            for a in found:
                wanted.update(ALLERGEN_TAG.get(a, [a]))
        for i, a in enumerate(list(allergens)):
            if a in TAG_ALIASES:
                canon = TAG_ALIASES[a]
                allergens[i] = canon
                stats[f'tags.allergens {a}->{canon}'] += 1
                changed += 1
        if len(set(allergens)) != len(allergens):
            allergens[:] = list(dict.fromkeys(allergens))
        for a in sorted(wanted - set(allergens)):
            allergens.append(a)
            stats[f'tags.allergens +{a}'] += 1
            changed += 1

        excluded = set().union(*(s for f, s in FLAG_EXCLUDES.items() if flags.get(f) is True))
        for a in [a for a in allergens if a in excluded and a not in wanted]:
            allergens.remove(a)
            stats[f'tags.allergens -{a} (contredit un flag, sans ingrédient)'] += 1
            changed += 1
    return changed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    raw = json.loads(Path(RECIPES_PATH).read_text(encoding='utf-8'))
    recipes = _recipes_raw()          # objets partagés avec compute_diet_flags (sous-recettes)
    repo = IngredientRepository()
    stats: Counter = Counter()
    touched_before = {r['id']: json.dumps([r.get('diet_flags'), r.get('tags')], sort_keys=True)
                      for r in recipes}
    for i in range(10):
        n = one_pass(recipes, repo, stats)
        print(f'  passe {i + 1} : {n} changements')
        if n == 0:
            break
    touched = [r['id'] for r in recipes
               if json.dumps([r.get('diet_flags'), r.get('tags')], sort_keys=True) != touched_before[r['id']]]
    for k, n in sorted(stats.items()):
        print(f'  {n:4d}  {k}')
    print(f'  recettes modifiées : {len(touched)}')

    if args.dry_run:
        print('\n[DRY-RUN] Aucune écriture.')
        return
    raw['recipes'] = recipes
    tmp = Path(RECIPES_PATH).with_suffix('.tmp')
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    tmp.replace(RECIPES_PATH)
    print(f'\nÉcrit → {RECIPES_PATH}')


if __name__ == '__main__':
    main()
