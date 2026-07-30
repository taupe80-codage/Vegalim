#!/usr/bin/env python3
"""
derive_prices_from_base_recipes.py — Pour les entrees du catalogue de prix
qui n'ont jamais trouve de correspondance sur Open Food Facts mais qui
correspondent a une recette "base_*" du dataset (ex. la cle catalogue
"kashk" <-> la recette base_kashk_fd3ac6), calcule un prix derive de la
composition de cette recette plutot que de garder un prix invente a la
main.

Reutilise directement _compute_base_recipe_unit_cost() de shopping.py
(meme logique que pour le cout des ingredients base_* dans une liste de
courses : somme ponderee du prix de chaque ingredient de la composition).

Usage :
    python scripts/derive_prices_from_base_recipes.py
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.engine.planning_engine.shopping import _compute_base_recipe_unit_cost  # noqa: E402

CATALOG_PATH = ROOT / "backend/data/config/prices_catalog.json"
MAP_PATH = ROOT / "backend/data/config/ingredient_price_map.json"
RECIPES_PATH = ROOT / "backend/data/recipes/recipes.json"

# cle catalogue -> id de la recette base_* correspondante (identifiees a la
# main : meme plat, juste deux entrees distinctes dans le systeme)
CATALOG_TO_BASE_RECIPE = {
    "salted_ricotta": "base_salted_ricotta_1ecd1c",
    "kashk": "base_kashk_fd3ac6",
    "mozzarella_vegane": "base_mozzarella_vegane_fca8c8",
    "vegetarian_fish_sauce": "base_vegetarian_fish_sauce_536a33",
    "doubanjiang_paste": "base_doubanjiang_paste_340399",
    "mola_sauce": "base_mole_d0034f",
    "sauce_okonomiyaki": "base_okonomiyaki_1e5fba",
}


def main():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    price_map = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    recipes = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))["recipes"]
    recipe_index = {r["id"]: r for r in recipes}

    cache: dict = {}
    visiting: set = set()

    for catalog_key, base_id in CATALOG_TO_BASE_RECIPE.items():
        result = _compute_base_recipe_unit_cost(base_id, recipe_index, catalog, price_map, cache, visiting)
        if result is None:
            print(f"  ✗ {catalog_key} <- {base_id} : calcul impossible (composition vide/inconvertible)")
            continue
        total_cost, total_qty = result
        price_per_unit = total_cost / total_qty

        entry = catalog[catalog_key]
        old_price = entry["packages"][0]["price"]
        for pkg in entry["packages"]:
            pkg["price"] = round(price_per_unit * pkg["qty"], 2)
        entry["last_updated"] = "2026-07-30"
        entry["price_source"] = f"derive de la recette {base_id} (pas de correspondance OFF)"

        new_price = entry["packages"][0]["price"]
        print(f"  ✓ {catalog_key} <- {base_id} : {old_price}€ -> {new_price}€ "
              f"(recette complete : {round(total_cost, 2)}€ pour {round(total_qty)}g/ml)")

    CATALOG_PATH.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n{len(CATALOG_TO_BASE_RECIPE)} entrees traitees -> {CATALOG_PATH}")


if __name__ == "__main__":
    main()
