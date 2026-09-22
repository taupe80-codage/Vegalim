#!/usr/bin/env python3
"""
build_derived_base_registry.py — Régénère
backend/data/ingredients/derived_from_base_recipes.json.

Pour chaque recette base_* déjà présente dans le registre (sous-recettes
référencées comme ingrédient par d'autres recettes : paneer, ghee, bouillons,
sauces maison…) :
  - total_weight_g     = Σ quantity × UNIT_TO_G (unité inconnue → ×1)
  - nutrition_per_100g = compute_nutrition(recette, servings=1) × 100 / total_weight_g
                         (total_weight_g × yield_factor ; fiche `nutrition_reference`
                          de nutrition_v2 si la recette en déclare une)
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


def recipe_yield(recipe: dict) -> float:
    """
    Rendement de la préparation (poids obtenu / poids des ingrédients), champ
    `yield_factor` de la recette. Sans lui, un paneer fait avec 1 L de lait
    était compté à la densité du lait (62 kcal/100 g au lieu d'environ 300) et
    un concentré de tomate à celle des tomates crues (constaté le 2026-09-14).
    Approximation : les nutriments du liquide éliminé (petit-lait, vapeur,
    pulpe filtrée) restent comptés — pour les fromages caillés maison, la
    recette déclare plutôt une `nutrition_reference` (voir reference_per_100g).
    """
    y = recipe.get('yield_factor')
    return float(y) if isinstance(y, (int, float)) and 0 < y <= 1 else 1.0


def reference_per_100g(ref: str, keys) -> dict:
    """
    Nutriments /100 g d'une fiche nutrition_v2 ('base/variant') servant de
    référence à une préparation maison. Utilisé quand le calcul depuis les
    ingrédients est faux par construction : un fromage caillé au citron garde
    dans le calcul le lactose du petit-lait égoutté (paneer à 24 g de glucides
    au lieu de ~3 — vérifié le 2026-09-15 contre USDA SR queso blanco, fiches
    de marques paneer/halloumi et IFCT 2017).
    """
    from backend.core.data_io import load_nutrition_db
    from backend.engine.nutrition_engine import _normalize_n_data
    base, _, variant = ref.partition('/')
    entry = load_nutrition_db().get(base) or {}
    vdata = (entry.get('variants') or {}).get(variant)
    if not vdata:
        raise KeyError(f"nutrition_reference introuvable dans nutrition_v2 : {ref}")
    n = _normalize_n_data(vdata)
    out = {k: (round(float(n[k]), 2) if isinstance(n.get(k), (int, float)) else 0.0) for k in keys}
    if out.get('sodium'):
        out['salt'] = round(out['sodium'] * 0.00254, 2)
    return out


def build_entry(recipe: dict) -> dict:
    weight = total_weight_g(recipe) * recipe_yield(recipe)
    nutr = compute_nutrition(recipe, servings=1)
    per100 = {k: (round(v * 100 / weight, 2) if isinstance(v, (int, float)) and weight else v)
              for k, v in nutr.items() if k not in DROP_KEYS}
    ref = recipe.get('nutrition_reference')
    if ref:
        per100.update(reference_per_100g(ref, [k for k in per100 if k not in ('salt', 'glycemic_index')]))
    per100.setdefault('glycemic_index', None)
    flags = recipe.get('diet_flags') or {}
    entry = {
        'name_fr': (recipe.get('titles') or {}).get('fr', ''),
        'name_en': (recipe.get('titles') or {}).get('en', ''),
        'total_weight_g': round(weight, 1),
        'nutrition_per_100g': per100,
        'diet_profile': {f: bool(flags.get(f)) for f in DIET_FLAGS},
        'source': 'derived_from_base_recipe',
    }
    if ref:
        entry['nutrition_reference'] = ref
    return entry


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
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    tmp.replace(REGISTRY)
    print(f'\nÉcrit → {REGISTRY}')


if __name__ == '__main__':
    main()
