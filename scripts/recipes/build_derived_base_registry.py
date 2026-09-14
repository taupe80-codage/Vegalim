#!/usr/bin/env python3
"""
build_derived_base_registry.py — Régénère
backend/data/ingredients/derived_from_base_recipes.json.

Pour chaque recette base_* déjà présente dans le registre (sous-recettes
référencées comme ingrédient par d'autres recettes : paneer, ghee, bouillons,
sauces maison…) :
  - total_weight_g     = Σ quantity × UNIT_TO_G (unité inconnue → ×1)
  - nutrition_per_100g = compute_nutrition(recette, servings=1) × 100 / total_weight_g
  - diet_profile       = les 5 flags de régime de recipe.diet_flags

Le registre n'avait pas de script générateur : ses valeurs figées au
2026-07-28 ne suivaient ni les réécritures de recettes ni les corrections de
données (ex. bouillon déshydraté). IngredientRepository le consulte AVANT les
diet_flags de la sous-recette, d'où l'importance de le garder synchrone.

Les sous-recettes pouvant en référencer d'autres, le calcul itère jusqu'à
stabilisation, en injectant chaque passe dans le cache du registre.

À lancer après toute modification de recipes.json ou des données
nutritionnelles, AVANT rebuild_graphs.py.

Usage :
    python scripts/recipes/build_derived_base_registry.py --dry-run
    python scripts/recipes/build_derived_base_registry.py --check   # exit 1 si périmé
    python scripts/recipes/build_derived_base_registry.py
"""
import argparse, json, logging, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
logging.disable(logging.WARNING)

from backend.engine.config import DATA_ROOT
from backend.core.data_io import load_recipes
from backend.db.culinary_repositories import _derived_registry
from backend.engine.nutrition_engine import compute_nutrition, UNIT_TO_G

REGISTRY = DATA_ROOT / 'ingredients' / 'derived_from_base_recipes.json'
DIET_FLAGS = ('vegan', 'vegetarian', 'gluten_free', 'lactose_free', 'nut_free')
DROP_KEYS = {'servings_used', 'source'}


def total_weight_g(recipe: dict) -> float:
    return sum(float(c['quantity']) * UNIT_TO_G.get((c.get('unit') or 'g').lower(), 1.0)
               for c in recipe.get('composition', [])
               if isinstance(c.get('quantity'), (int, float)))


def build_entry(recipe: dict) -> dict:
    weight = total_weight_g(recipe)
    nutr = compute_nutrition(recipe, servings=1)
    per100 = {k: (round(v * 100 / weight, 2) if isinstance(v, (int, float)) and weight else v)
              for k, v in nutr.items() if k not in DROP_KEYS}
    per100.setdefault('glycemic_index', None)
    flags = recipe.get('diet_flags') or {}
    return {
        'name_fr': (recipe.get('titles') or {}).get('fr', ''),
        'name_en': (recipe.get('titles') or {}).get('en', ''),
        'total_weight_g': round(weight, 1),
        'nutrition_per_100g': per100,
        'diet_profile': {f: bool(flags.get(f)) for f in DIET_FLAGS},
        'source': 'derived_from_base_recipe',
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--check', action='store_true',
                    help="n'écrit rien ; code retour 1 si le registre est périmé")
    args = ap.parse_args()

    raw = json.loads(REGISTRY.read_text(encoding='utf-8'))
    old = raw['recipes']
    recipes = {r['id']: r for r in load_recipes()}
    missing = [k for k in old if k not in recipes]
    if missing:
        print(f'  ⚠ recettes du registre absentes de recipes.json : {missing}')

    live = _derived_registry()                     # dict mis en cache, patché à chaque passe
    for i in range(6):
        new = {k: build_entry(recipes[k]) for k in old if k in recipes}
        delta = sum(1 for k in new if new[k] != live.get(k))
        live.update(new)
        print(f'  passe {i + 1} : {delta} entrées modifiées')
        if delta == 0:
            break

    changed = [k for k in new if new[k] != old.get(k)]
    print(f'  entrées différentes du registre actuel : {len(changed)} / {len(new)}')
    for k in sorted(changed, key=lambda k: -abs(new[k]['nutrition_per_100g'].get('sodium', 0)
                                                - old[k]['nutrition_per_100g'].get('sodium', 0)))[:8]:
        o, n = old[k]['nutrition_per_100g'], new[k]['nutrition_per_100g']
        print(f'    {k:40s} kcal {o.get("calories")} -> {n.get("calories")}   '
              f'Na {o.get("sodium")} -> {n.get("sodium")}')

    if args.check:
        sys.exit(1 if changed else 0)
    if args.dry_run:
        print('\n[DRY-RUN] Aucune écriture.')
        return
    raw['recipes'] = new
    tmp = REGISTRY.with_suffix('.tmp')
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8')
    tmp.replace(REGISTRY)
    print(f'\nÉcrit → {REGISTRY}')


if __name__ == '__main__':
    main()
