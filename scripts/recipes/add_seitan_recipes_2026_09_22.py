#!/usr/bin/env python3
"""Ajoute deux plats au seitan (idempotent).

`base_seitan_249032` est une préparation de base (v18) qu'aucune recette n'utilisait :
ces deux plats l'emploient comme ingrédient, l'un sauté au wok, l'autre mijoté.

Usage :
    python scripts/recipes/add_seitan_recipes_2026_09_22.py [--dry-run]

Relancer ensuite le pipeline habituel (fix_recipe_diet_allergens, build_derived_base_registry,
rebuild_graphs, build_index) : nutrition, scoring, search_tokens et index sont recalculés.
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.engine.config import RECIPES_PATH


def compo(items):
    return [{"ingredient": i, "quantity": q, "unit": u,
             "meta": {"role": r, "form": "", "state": st, "preparation": ""}}
            for i, q, u, r, st in items]


def steps(lines):
    return [f"Étape {n} : {t}" for n, t in enumerate(lines, 1)]


NEW = [
    {
        "id": "wok_seitan_poivrons_3f81c4",
        "titles": {"fr": "Seitan sauté aux poivrons et à la sauce soja",
                   "en": "Stir-Fried Seitan with Peppers and Soy Sauce",
                   "original": "Stir-Fried Seitan with Peppers and Soy Sauce"},
        "origin": {"cuisine": "chinese", "country": "china", "region": "guangdong", "city": ""},
        "servings": 4, "servings_default": 4,
        "timing": {"prep_active_min": 15, "prep_passive_min": 0, "cook_min": 15, "total_min": 30},
        "composition": compo([
            ("base_seitan_249032", 400, "g", "protein", "raw"),
            ("red_bell_pepper_raw", 200, "g", "vegetable", "raw"),
            ("green_bell_pepper_raw", 150, "g", "vegetable", "raw"),
            ("onion_raw", 120, "g", "aromatic_base", "raw"),
            ("garlic_raw", 9, "g", "aromatic", "raw"),
            ("ginger_raw_root_fresh", 10, "g", "aromatic", "raw"),
            ("green_onion_raw", 30, "g", "garnish", "raw"),
            ("soy_sauce_shoyu_reduced_sodium", 30, "ml", "condiment", "raw"),
            ("white_vinegar_liquid_distilled", 10, "ml", "condiment", "raw"),
            ("white_sugar", 8, "g", "seasoning", "raw"),
            ("cornstarch_flour", 8, "g", "thickener", "raw"),
            ("peanut_oil_plant", 25, "ml", "fat", "raw"),
            ("sesame_oil_plant", 10, "ml", "fat", "raw"),
            ("white_rice_raw_seed_unenriched", 250, "g", "carbohydrate", "raw"),
            ("water", 450, "ml", "liquid", "raw"),
        ]),
        "tags": {"diet": ["vegan", "vegetarian", "high_protein"], "meal": ["main"], "season": [],
                 "allergens": ["gluten", "soy", "peanuts", "sesame"],
                 "technique": ["wok"], "process": []},
        "result": {"texture": ["ferme", "croquant"], "taste": ["umami", "soja"], "visual": ["colore", "brillant"]},
        "scoring": {"confidence": 0.9, "spice_level": 0},
        "dish_type": "main",
        "difficulty_level": "easy",
        "description": ("Lamelles de seitan saisies au wok avec poivrons, oignon, ail et gingembre, enrobées d'une "
                        "sauce soja légèrement sucrée et liée à la fécule, servies sur du riz."),
        "instructions": steps([
            "Rincer 250 g de riz et le cuire dans 370 ml d'eau, 12 minutes à couvert, puis le laisser reposer.",
            "Couper 400 g de seitan en lamelles de 5 mm et les saisir dans 15 ml d'huile d'arachide à feu vif, 4 minutes, jusqu'à ce qu'elles soient dorées. Réserver.",
            "Sauce : mélanger 30 ml de sauce soja, 10 ml de vinaigre, 8 g de sucre, 8 g de fécule et 80 ml d'eau.",
            "Dans 10 ml d'huile, sauter 120 g d'oignon, 200 g de poivron rouge et 150 g de poivron vert en lanières, 4 minutes à feu vif, puis ajouter 9 g d'ail et 10 g de gingembre hachés.",
            "Remettre le seitan, verser la sauce et remuer 1 minute, jusqu'à ce qu'elle nappe et devienne brillante.",
            "Hors du feu, arroser de 10 ml d'huile de sésame et parsemer de 30 g d'oignons verts. Servir sur le riz.",
        ]),
        "diet_flags": {"vegan": True, "vegetarian": True, "gluten_free": False, "lactose_free": True,
                       "nut_free": False, "raw": False, "kid_friendly": True},
    },
    {
        "id": "stew_seitan_champignons_moutarde_7ac502",
        "titles": {"fr": "Seitan mijoté aux champignons et à la moutarde",
                   "en": "Braised Seitan with Mushrooms and Mustard",
                   "original": "Braised Seitan with Mushrooms and Mustard"},
        "origin": {"cuisine": "french", "country": "france", "region": "bourgogne", "city": ""},
        "servings": 4, "servings_default": 4,
        "timing": {"prep_active_min": 20, "prep_passive_min": 0, "cook_min": 30, "total_min": 50},
        "composition": compo([
            ("base_seitan_249032", 400, "g", "protein", "raw"),
            ("button_mushroom_raw", 300, "g", "vegetable", "raw"),
            ("carrot_raw", 200, "g", "vegetable", "raw"),
            ("onion_raw", 150, "g", "aromatic_base", "raw"),
            ("garlic_raw", 9, "g", "aromatic", "raw"),
            ("mustard", 20, "g", "condiment", "raw"),
            ("base_oat_cream_954865", 200, "ml", "sauce", "raw"),
            ("white_wine_liquid", 100, "ml", "liquid", "raw"),
            ("vegetable_stock_dried", 8, "g", "ingredient", "raw"),
            ("water", 300, "ml", "liquid", "raw"),
            ("thyme_dried_herb", 1, "g", "herb", "raw"),
            ("bay_leaf", 1, "g", "aromatic", "raw"),
            ("olive_oil_plant", 30, "ml", "fat", "raw"),
            ("parsley_fresh_herb", 10, "g", "herb", "raw"),
            ("black_pepper_spice", 1, "g", "spice", "raw"),
            ("pasta_raw_dried", None, "1 portion", "serving_suggestion", None),
        ]),
        "tags": {"diet": ["vegan", "vegetarian", "high_protein"], "meal": ["main"], "season": [],
                 "allergens": ["gluten", "soy", "mustard", "sulphites"],
                 "technique": ["braise"], "process": []},
        "result": {"texture": ["fondant", "nappant"], "taste": ["umami", "moutarde"], "visual": ["dore"]},
        "scoring": {"confidence": 0.9, "spice_level": 0},
        "dish_type": "main",
        "difficulty_level": "easy",
        "description": ("Cubes de seitan dorés puis mijotés avec champignons, carottes et vin blanc, dans une sauce "
                        "crémeuse à la moutarde et à la crème d'avoine, parsemée de persil."),
        "instructions": steps([
            "Couper 400 g de seitan en cubes de 3 cm et les dorer dans 20 ml d'huile d'olive à feu vif, 5 minutes. Réserver.",
            "Faire revenir 150 g d'oignon émincé et 200 g de carotte en rondelles dans 10 ml d'huile, 6 minutes, puis ajouter 300 g de champignons en quartiers et les saisir 5 minutes.",
            "Ajouter 9 g d'ail haché, déglacer avec 100 ml de vin blanc et laisser réduire 2 minutes.",
            "Verser 300 ml d'eau avec 8 g de bouillon déshydraté, 1 g de thym et 1 g de laurier, remettre le seitan et mijoter 20 minutes à couvert.",
            "Hors du feu, incorporer 200 ml de crème d'avoine et 20 g de moutarde, puis réchauffer 2 minutes sans bouillir.",
            "Poivrer avec 1 g de poivre, parsemer de 10 g de persil et servir avec des pâtes fraîches.",
        ]),
        "diet_flags": {"vegan": True, "vegetarian": True, "gluten_free": False, "lactose_free": True,
                       "nut_free": True, "raw": False, "kid_friendly": True},
    },
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))
    recipes = raw["recipes"]
    have = {r["id"] for r in recipes}
    added = [r for r in NEW if r["id"] not in have]
    for r in added:
        recipes.append(r)
    print(f"{len(added)} recette(s) ajoutée(s)" + (" (dry-run)" if args.dry_run else ""))
    if added and not args.dry_run:
        if isinstance(raw.get("total_recipes"), int):
            raw["total_recipes"] = len(recipes)
        RECIPES_PATH.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")
        print("écrit :", RECIPES_PATH)


if __name__ == "__main__":
    main()
