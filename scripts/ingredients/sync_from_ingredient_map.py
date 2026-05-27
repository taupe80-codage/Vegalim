#!/usr/bin/env python3
"""
scripts/ingredients/sync_from_ingredient_map.py
================================================
Synchronise ingredients_dictionary.json depuis ingredient_map + nutrition_v2.

Pour chaque recipe_key dans ingredient_map absent du dict :
  - Résout le nutri_id via la map
  - Dérive la catégorie depuis taxonomy.cat1/cat2 de nutrition_v2
  - Génère une entrée dict avec le diet_profile correct
    (ex : egg_yolk/egg_white → cat1=eggs → category=egg → sans_oeuf=False)

Cela corrige notamment le bug : recettes contenant egg_yolk ou egg_white
incorrectement flaggées "sans oeuf" (egg_free=True) dans enrichment_service
et filter_service, car ces clés n'avaient aucune entrée dans le dict.

Usage :
  python scripts/ingredients/sync_from_ingredient_map.py
  python scripts/ingredients/sync_from_ingredient_map.py --dry-run
  python scripts/ingredients/sync_from_ingredient_map.py --dry-run --verbose
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT       = Path(__file__).resolve().parents[2]
DICT_FILE  = ROOT / "backend/data/ingredients/ingredients_dictionary.json"
N2_FILE    = ROOT / "backend/data/nutrition/processed/nutrition_v2.json"
IMAP_GLOB  = "ingredient_map_*.json"
IMAP_DIR   = ROOT / "backend/data/recipes"

# ── Mapping taxonomy.cat1 / cat2 → catégorie dict ────────────────────────────
# Priorité : cat2 spécifique > cat1 générique
CAT2_TO_DICT: dict[str, str] = {
    "eggs_general":             "egg",
    "prepared_eggs":            "egg",
    "pasta":                    "grain",
    "bread_and_bakery":         "grain",
    "breakfast_cereals":        "grain",
    "rice":                     "grain",
    "whole_grains":             "grain",
    "flours_and_starches":      "grain",
    "brans_and_germs":          "grain",
    "milk_and_cream":           "dairy",
    "cheese":                   "dairy",
    "yogurt_and_kefir":         "dairy",
    "butter_and_ghee":          "dairy",
    "plant_milks":              "dairy_alternative",
    "plant_yogurts":            "dairy_alternative",
    "plant_creams":             "dairy_alternative",
    "nuts":                     "nut_seed",
    "seeds":                    "nut_seed",
    "nut_butters":              "nut_seed",
    "peanuts":                  "nut_seed",
    "oils":                     "fat",
    "solid_fats":               "fat",
    "honey_and_syrups":         "sweetener",
    "sugars":                   "sweetener",
    "confectionery":            "sweetener",
    "legumes":                  "legume",
    "soy_products":             "protein_plant",
    "meat_alternatives":        "protein_plant",
    "fermented_foods":          "fermented",
    "vinegars":                 "condiment",
    "sauces":                   "condiment",
    "spice_mixes":              "herb_spice",
    "seaweeds":                 "superfood",
    "superfoods":               "superfood",
    "leavening_agents":         "leavening",
    "food_additives":           "additive",
    "alcoholic_beverages":      "alcohol",
    "non_alcoholic_beverages":  "liquid",
    "waters":                   "liquid",
    "fruit_juices":             "liquid",
}

CAT1_TO_DICT: dict[str, str] = {
    "eggs":                             "egg",
    "vegetables":                       "vegetable",
    "fruits":                           "fruit",
    "legumes":                          "legume",
    "dairy_products":                   "dairy",
    "cereals_and_grains":               "grain",
    "nuts_and_seeds":                   "nut_seed",
    "fats_and_oils":                    "fat",
    "herbs_and_spices":                 "herb_spice",
    "condiments_and_sauces":            "condiment",
    "sugars_honeys_and_confectionery":  "sweetener",
    "beverages":                        "liquid",
    "seaweeds_and_sea_vegetables":      "superfood",
    "leavening_agents_and_additives":   "additive",
    "prepared_dishes_and_mixes":        "condiment",
    "fermented_foods":                  "fermented",
    "alcoholic_beverages":              "alcohol",
    "plant_based_proteins":             "protein_plant",
    "dairy_alternatives":               "dairy_alternative",
}

# cat2 contenant "egg" → toujours egg même si cat1 est prepared_dishes
EGG_CAT2 = {"eggs_general", "prepared_eggs", "egg_products"}

VALID_CATEGORIES = {
    "vegetable", "fruit", "fat", "herb_spice", "liquid", "grain",
    "protein_plant", "condiment", "nut_seed", "legume", "leavening",
    "dairy", "sweetener", "superfood", "dairy_alternative",
    "egg", "fermented", "additive", "alcohol",
}

# diet_profile par catégorie (hérité de sync_ingredients.py)
DIET_DEFAULTS: dict[str, dict] = {
    "vegetable":         dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "fruit":             dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "grain":             dict(vegan=True,  vegetarian=True,  sans_gluten=False, sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "legume":            dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=True,  diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=True),
    "fat":               dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "herb_spice":        dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "condiment":         dict(vegan=False, vegetarian=False, sans_gluten=False, sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=False, sans_oeuf=False, riche_en_fibres=False),
    "dairy":             dict(vegan=False, vegetarian=True,  sans_gluten=True,  sans_lactose=False, sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "dairy_alternative": dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=False, hyper_proteine=False, diabet_free=False, sans_soja=False, sans_oeuf=True,  riche_en_fibres=False),
    "sweetener":         dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "protein_plant":     dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=True,  diabet_free=True,  sans_soja=False, sans_oeuf=True,  riche_en_fibres=True),
    "nut_seed":          dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=False, hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=True),
    "superfood":         dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=True),
    "leavening":         dict(vegan=True,  vegetarian=True,  sans_gluten=False, sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "liquid":            dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "egg":               dict(vegan=False, vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=True,  diabet_free=True,  sans_soja=True,  sans_oeuf=False, riche_en_fibres=False),
    "fermented":         dict(vegan=False, vegetarian=False, sans_gluten=False, sans_lactose=False, sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=False, sans_oeuf=True,  riche_en_fibres=False),
    "additive":          dict(vegan=True,  vegetarian=True,  sans_gluten=True,  sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=True,  sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
    "alcohol":           dict(vegan=True,  vegetarian=True,  sans_gluten=False, sans_lactose=True,  sans_fruits_a_coque=True,  hyper_proteine=False, diabet_free=False, sans_soja=True,  sans_oeuf=True,  riche_en_fibres=False),
}

CULINARY_PROPS: dict[str, list] = {
    "vegetable": ["fresh", "fiber"],     "fruit": ["fresh", "sweet"],
    "grain": ["starchy"],                "legume": ["protein", "fiber", "starchy"],
    "fat": ["fat"],                      "herb_spice": ["aromatic"],
    "condiment": ["aromatic", "acid"],   "dairy": ["creamy", "protein"],
    "dairy_alternative": ["creamy"],     "sweetener": ["sweet"],
    "protein_plant": ["protein"],        "nut_seed": ["fat", "protein"],
    "superfood": ["fresh"],              "leavening": ["leavening"],
    "liquid": ["neutral"],               "egg": ["protein", "creamy"],
    "fermented": ["fermented", "umami"], "additive": ["neutral"],
    "alcohol": ["neutral"],
}

FLAVOR_PROPS: dict[str, list] = {
    "vegetable": ["neutral"],   "fruit": ["sweet"],     "grain": ["neutral"],
    "legume": ["earthy"],       "fat": ["neutral"],     "herb_spice": ["aromatic"],
    "condiment": ["savory"],    "dairy": ["creamy"],    "dairy_alternative": ["neutral"],
    "sweetener": ["sweet"],     "protein_plant": ["neutral"], "nut_seed": ["nutty"],
    "superfood": ["neutral"],   "leavening": ["neutral"], "liquid": ["neutral"],
    "egg": ["neutral"],         "fermented": ["umami"], "additive": ["neutral"],
    "alcohol": ["neutral"],
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _find_imap() -> Path | None:
    candidates = sorted(IMAP_DIR.glob(IMAP_GLOB), reverse=True)
    return candidates[0] if candidates else None


def _derive_category(taxonomy: dict) -> str:
    """Dérive la catégorie dict depuis taxonomy.cat1 / cat2 de nutrition_v2."""
    cat1 = (taxonomy.get("cat1") or "").lower().strip()
    cat2 = (taxonomy.get("cat2") or "").lower().strip()

    # cat2 spécifique d'abord (plus précis)
    if cat2 in EGG_CAT2:
        return "egg"
    if cat2 in CAT2_TO_DICT:
        return CAT2_TO_DICT[cat2]
    # cat1 générique ensuite
    if cat1 in CAT1_TO_DICT:
        return CAT1_TO_DICT[cat1]
    return "condiment"   # fallback sûr — conservateur pour les flags


def _name_fr_from_n2(n2_entry: dict, recipe_key: str) -> str:
    """Extrait le meilleur name_fr depuis l'entrée nutrition_v2."""
    tax = n2_entry.get("taxonomy", {})
    if tax.get("name_fr"):
        return tax["name_fr"]
    variants = n2_entry.get("variants", {})
    for vd in variants.values():
        if isinstance(vd, dict) and vd.get("name_fr"):
            return vd["name_fr"]
    # Fallback : recipe_key humanisé
    return recipe_key.replace("_", " ").replace("/", " — ")


def _axes_from_n2(n2_entry: dict) -> dict:
    """Retourne les axes du premier variant (pour référence)."""
    variants = n2_entry.get("variants", {})
    for vd in variants.values():
        if isinstance(vd, dict):
            return vd.get("axes", {})
    return {}


def _build_entry(recipe_key: str, nutri_id: str, n2_entry: dict,
                 imap_status: str) -> dict:
    """Construit une entrée ingredients_dictionary depuis les données nutrition."""
    taxonomy = n2_entry.get("taxonomy", {})
    category = _derive_category(taxonomy)
    name_fr  = _name_fr_from_n2(n2_entry, recipe_key)
    axes     = _axes_from_n2(n2_entry)

    import copy
    diet = copy.deepcopy(DIET_DEFAULTS.get(category, DIET_DEFAULTS["condiment"]))

    entry: dict = {
        "id":              recipe_key,
        "name_fr":         name_fr,
        "category":        category,
        "substitutions":   [],
        "diet_profile":    diet,
        "culinary_properties": CULINARY_PROPS.get(category, ["neutral"]),
        "flavor_profile":  FLAVOR_PROPS.get(category, ["neutral"]),
        "cooking_behavior": {"time_minutes": None, "__note": "À compléter"},
        "allergens_eu":    [],
        "nutrition_key":   nutri_id,
        "__auto_generated": True,
        "__source":        f"ingredient_map:{recipe_key}/{nutri_id}",
        "__imap_status":   imap_status,
    }

    if axes:
        entry["__axes"] = axes  # pour référence / debug

    return entry


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(
        description="Sync ingredients_dictionary depuis ingredient_map + nutrition_v2"
    )
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Affiche sans écrire")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Détail de chaque entrée générée")
    args = parser.parse_args()
    dry = args.dry_run

    # ── Chargement ────────────────────────────────────────────────
    print(f"Lecture : {DICT_FILE.name}")
    dict_raw = json.loads(DICT_FILE.read_text(encoding="utf-8"))
    dict_list: list = dict_raw.get("ingredients", [])
    dict_ids  = {e["id"] for e in dict_list if isinstance(e, dict)}
    print(f"  {len(dict_ids)} entrées existantes")

    print(f"Lecture : {N2_FILE.name}")
    n2_raw = json.loads(N2_FILE.read_text(encoding="utf-8"))
    n2_ings: dict = n2_raw.get("ingredients", {})
    print(f"  {len(n2_ings)} entrées nutrition")

    imap_path = _find_imap()
    if not imap_path:
        print(f"ERREUR : aucun fichier ingredient_map_*.json dans {IMAP_DIR}", file=sys.stderr)
        return 1
    print(f"Lecture : {imap_path.name}")
    imap: dict = json.loads(imap_path.read_text(encoding="utf-8"))
    print(f"  {len(imap)} entrées dans l'ingredient_map")

    # ── Analyse ────────────────────────────────────────────────────
    skipped_no_nutri  = []   # recipe_key sans nutri_id dans la map
    skipped_no_n2     = []   # nutri_id absent de nutrition_v2
    skipped_existing  = []   # recipe_key déjà dans le dict
    to_add: list[dict] = []

    # Compteurs par catégorie dérivée
    cat_counts: dict[str, int] = defaultdict(int)

    for recipe_key, map_entry in sorted(imap.items()):
        if recipe_key in dict_ids:
            skipped_existing.append(recipe_key)
            continue

        nutri_id = map_entry.get("nutri_id") if isinstance(map_entry, dict) else None
        status   = map_entry.get("status", "") if isinstance(map_entry, dict) else ""

        if not nutri_id:
            skipped_no_nutri.append(recipe_key)
            continue

        # Lookup dans nutrition_v2 : d'abord le nutri_id direct,
        # puis le "base" si nutri_id est au format base/variant
        n2_entry = n2_ings.get(nutri_id)
        if n2_entry is None and "/" in nutri_id:
            base = nutri_id.split("/")[0]
            n2_entry = n2_ings.get(base)
            if n2_entry:
                nutri_id = base   # normaliser vers la base

        if n2_entry is None:
            skipped_no_n2.append((recipe_key, nutri_id))
            continue

        entry = _build_entry(recipe_key, nutri_id, n2_entry, status)
        cat_counts[entry["category"]] += 1
        to_add.append(entry)

        if args.verbose:
            tax = n2_entry.get("taxonomy", {})
            print(f"  + {recipe_key!r:35} cat1={tax.get('cat1','?')!r:25} "
                  f"→ category={entry['category']!r:18} "
                  f"sans_oeuf={entry['diet_profile']['sans_oeuf']}")

    # ── Rapport ────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print(f"  RAPPORT SYNC ingredient_map → dict")
    print(f"{'='*60}")
    print(f"  Déjà présents dans le dict      : {len(skipped_existing)}")
    print(f"  Sans nutri_id dans la map       : {len(skipped_no_nutri)}")
    print(f"  nutri_id absent de nutrition_v2 : {len(skipped_no_n2)}")
    print(f"  A ajouter                       : {len(to_add)}")
    if to_add:
        print(f"\n  Distribution par catégorie :")
        for cat, cnt in sorted(cat_counts.items(), key=lambda x: -x[1]):
            print(f"    {cat:<20} : {cnt}")

    # Détail des entrées egg (le bug à corriger)
    egg_entries = [e for e in to_add if e["category"] == "egg"]
    if egg_entries:
        print(f"\n  Entrées 'egg' à ajouter ({len(egg_entries)}) :")
        for e in egg_entries:
            dp = e["diet_profile"]
            print(f"    id={e['id']!r:25} sans_oeuf={dp['sans_oeuf']}  "
                  f"vegan={dp['vegan']}  vegetarian={dp['vegetarian']}")

    if skipped_no_n2:
        print(f"\n  Clés sans entrée n2 (premières 10) :")
        for k, nid in skipped_no_n2[:10]:
            print(f"    {k!r} → nutri_id={nid!r}")

    if dry:
        print(f"\n  [DRY-RUN] aucun fichier modifié.")
        return 0

    # ── Écriture ───────────────────────────────────────────────────
    if not to_add:
        print(f"\n  Aucune entrée à ajouter — dictionnaire déjà complet.")
        return 0

    dict_list.extend(to_add)
    dict_raw["ingredients"]       = dict_list
    dict_raw["total_ingredients"] = len(dict_list)

    tmp = DICT_FILE.with_suffix(".tmp.json")
    tmp.write_text(json.dumps(dict_raw, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(DICT_FILE)

    print(f"\n  Ecrit : {DICT_FILE}  (+{len(to_add)} entrées, total={len(dict_list)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
