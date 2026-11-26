"""
derived_registry.py — Entrées du registre des sous-recettes
(backend/data/ingredients/derived_from_base_recipes.json).

Partagé par scripts/recipes/build_derived_base_registry.py (rebuild complet)
et services/nutrition_refresh.py (recalcul ciblé après la correction d'un
ingrédient, 2026-11-26).
"""
from __future__ import annotations

from backend.engine.config import DATA_ROOT
from backend.engine.nutrition_engine import UNIT_TO_G, compute_nutrition

REGISTRY = DATA_ROOT / 'ingredients' / 'derived_from_base_recipes.json'
DIET_FLAGS = ('vegan', 'vegetarian', 'gluten_free', 'lactose_free', 'nut_free')
DROP_KEYS = {'servings_used', 'source', 'portion_g'}   # portion_g : poids, pas un nutriment


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
