"""
resolve_remaining_ingredients.py
=================================
Résout les 25 ingrédients encore manquants après apply_ingredient_map :

  Étape 1 — base_recipe_aliases : branche les 4 base_recipes existantes
  Étape 2 — recipe_aliases     : mappe les 15 ingrédients simples
  Étape 3 — nouvelles base_recipes : crée 6 recettes dans recipes.json
             + branche leurs IDs dans base_recipe_aliases

Usage :
  python scripts/nutrition/resolve_remaining_ingredients.py [--dry-run]
"""
import hashlib
import io
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT     = Path(__file__).resolve().parents[2]
DATA     = ROOT / "backend" / "data"
ALIASES  = DATA / "nutrition" / "reference" / "nutrition_aliases_v6.json"
RECIPES  = DATA / "recipes" / "recipes.json"

DRY_RUN  = "--dry-run" in sys.argv


def recipe_id(name: str) -> str:
    h = hashlib.md5(name.encode()).hexdigest()[:6]
    return f"base_{name}_{h}"


# ── Étape 1 : base_recipe_aliases existantes à brancher ─────────────────────
EXISTING_BASE = {
    "gundruk":             "base_gundruk_94c079",
    "ras_el_hanout":       "base_ras_el_hanout_7cd544",
    "worcestershire_vegan":"base_worcestershire_vegan_5f26ec",
    "za_atar":             "base_za_atar_2badf3",
}

# ── Étape 2 : aliases directs vers nutrition_v2 ──────────────────────────────
SIMPLE_ALIASES = {
    # Légumes manquants
    "fennel":              "fennel_bulb/raw",
    "green_peas":          "green_peas_raw/raw",
    "okra":                "okra_raw/raw",
    "glass_noodles":       "glass_noodles_soy_vermicelli_dried/raw_dried",
    "gigante_bean":        "great_northern_dried/dried",
    # Amidons / farines
    "tapioca_starch":      "tapioca/raw",
    "rice_paper":          "rice_white/flour_unenriched",
    "gyoza_wrapper":       "wheat_flour_t110/flour",
    "attieke":             "gari_fermented_cassava/fermented_dried",
    # Levure / condiments
    "yeast/instant":       "active_dry_yeast/dehydrated",
    "kashk":               "cottage_2_milkfat/low_fat",
    "mirin":               "rice_white_glutinous_flour/flour",
    # Nulls (aucune valeur nutritive utile)
    "aquafaba":            "__null__",
    "corn_husk":           "__null__",
    "sauce":               "__null__",
}

# ── Étape 3 : nouvelles base_recipes ────────────────────────────────────────
NOW = datetime.now(timezone.utc).isoformat()

NEW_RECIPES = [
    {
        "id": recipe_id("buckwheat_crepe"),
        "titles": {"fr": "Crêpe de Sarrasin", "en": "Buckwheat Crepe"},
        "origin": {"cuisine": "french", "country": "france", "region": "bretagne", "city": ""},
        "servings": 4,
        "servings_default": 4,
        "timing": {"prep_active_min": 10, "prep_passive_min": 30, "cook_min": 20, "total_min": 60},
        "composition": [
            {"ingredient": "buckwheat_flour", "quantity": 250, "unit": "g",  "meta": {"role": "base"}},
            {"ingredient": "egg",             "quantity": 2,   "unit": "piece","meta": {"role": "binding"}},
            {"ingredient": "milk_animal/whole","quantity": 500, "unit": "ml", "meta": {"role": "liquid"}},
            {"ingredient": "butter/dairy",    "quantity": 20,  "unit": "g",  "meta": {"role": "fat"}},
            {"ingredient": "salt",            "quantity": 5,   "unit": "g",  "meta": {"role": "seasoning"}},
        ],
        "tags": {"diet": ["vegetarian"], "meal": ["crepe", "base"], "season": []},
        "dish_type": "base",
        "diet_flags": {"vegan": False, "vegetarian": True, "gluten_free": False,
                       "lactose_free": False, "nut_free": True, "raw": False, "kid_friendly": True},
        "description": "Pâte à crêpes de sarrasin traditionnelle bretonne, légèrement épaisse "
                       "et rustique, avec la saveur noisette caractéristique du blé noir. "
                       "Préparation simple qui demande un temps de repos pour une texture optimale.",
        "instructions": [
            "Mélanger 250g de farine de sarrasin avec une pincée de sel dans un grand bol.",
            "Creuser un puits au centre, y ajouter 2 œufs battus et verser progressivement "
            "500ml de lait tout en fouettant pour éviter les grumeaux.",
            "Incorporer 20g de beurre fondu, puis laisser reposer la pâte 30 minutes au réfrigérateur.",
            "Cuire chaque crêpe 2 minutes par face dans une crêpière légèrement beurrée.",
        ],
        "scoring": {"confidence": 0.95},
        "_flags": [],
        "_created_by": "resolve_remaining_ingredients.py",
        "_created_at": NOW,
    },
    {
        "id": recipe_id("cashew_ricotta"),
        "titles": {"fr": "Ricotta de Cajou", "en": "Cashew Ricotta"},
        "origin": {"cuisine": "international", "country": "", "region": "", "city": ""},
        "servings": 4,
        "servings_default": 4,
        "timing": {"prep_active_min": 10, "prep_passive_min": 120, "cook_min": 0, "total_min": 130},
        "composition": [
            {"ingredient": "cashew/raw",          "quantity": 200, "unit": "g",  "meta": {"role": "base"}},
            {"ingredient": "citrus/lemon_juice",  "quantity": 30,  "unit": "ml", "meta": {"role": "acidifier"}},
            {"ingredient": "nutritional_yeast",   "quantity": 15,  "unit": "g",  "meta": {"role": "flavoring"}},
            {"ingredient": "salt",                "quantity": 4,   "unit": "g",  "meta": {"role": "seasoning"}},
        ],
        "tags": {"diet": ["vegan", "vegetarian", "gluten_free"], "meal": ["cheese", "base"], "season": []},
        "dish_type": "base",
        "diet_flags": {"vegan": True, "vegetarian": True, "gluten_free": True,
                       "lactose_free": True, "nut_free": False, "raw": True, "kid_friendly": True},
        "description": "Alternative végane à la ricotta à base de noix de cajou trempées, "
                       "crémeuse et légèrement acidulée grâce au jus de citron. "
                       "La levure nutritionnelle apporte des notes fromagères subtiles.",
        "instructions": [
            "Faire tremper 200g de noix de cajou dans de l'eau froide pendant 2 heures minimum, "
            "ou 30 minutes dans de l'eau bouillante.",
            "Égoutter et rincer les noix de cajou, puis les mixer avec 30ml de jus de citron, "
            "15g de levure nutritionnelle, 4g de sel et 30–60ml d'eau selon la texture souhaitée.",
            "Mixer jusqu'à obtenir une texture lisse et crémeuse, similaire à la ricotta. "
            "Ajuster l'assaisonnement et conserver au réfrigérateur jusqu'à 5 jours.",
        ],
        "scoring": {"confidence": 0.93},
        "_flags": [],
        "_created_by": "resolve_remaining_ingredients.py",
        "_created_at": NOW,
    },
    {
        "id": recipe_id("paneer"),
        "titles": {"fr": "Paneer", "en": "Paneer"},
        "origin": {"cuisine": "indian", "country": "india", "region": "", "city": ""},
        "servings": 4,
        "servings_default": 4,
        "timing": {"prep_active_min": 10, "prep_passive_min": 60, "cook_min": 15, "total_min": 85},
        "composition": [
            {"ingredient": "milk_animal/whole",  "quantity": 1000, "unit": "ml", "meta": {"role": "base"}},
            {"ingredient": "citrus/lemon_juice", "quantity": 45,   "unit": "ml", "meta": {"role": "acidifier"}},
            {"ingredient": "salt",               "quantity": 5,    "unit": "g",  "meta": {"role": "seasoning"}},
        ],
        "tags": {"diet": ["vegetarian", "gluten_free"], "meal": ["cheese", "base"], "season": []},
        "dish_type": "base",
        "diet_flags": {"vegan": False, "vegetarian": True, "gluten_free": True,
                       "lactose_free": False, "nut_free": True, "raw": False, "kid_friendly": True},
        "description": "Fromage frais indien non affiné, obtenu par coagulation du lait entier "
                       "avec du jus de citron. Ferme et doux, il absorbe parfaitement les épices "
                       "et résiste bien à la cuisson sans fondre.",
        "instructions": [
            "Porter 1 litre de lait entier à ébullition douce dans une grande casserole, "
            "en remuant régulièrement pour éviter qu'il n'attache.",
            "Hors du feu, ajouter progressivement 45ml de jus de citron en remuant doucement "
            "jusqu'à ce que le lait caille complètement et que le lactosérum devienne translucide.",
            "Verser dans une étamine, égoutter le lactosérum, ajouter le sel, "
            "puis presser le fromage en boule et laisser reposer sous un poids 1 heure minimum.",
        ],
        "scoring": {"confidence": 0.97},
        "_flags": [],
        "_created_by": "resolve_remaining_ingredients.py",
        "_created_at": NOW,
    },
    {
        "id": recipe_id("vegan_cheddar"),
        "titles": {"fr": "Cheddar Végétal", "en": "Vegan Cheddar"},
        "origin": {"cuisine": "international", "country": "", "region": "", "city": ""},
        "servings": 8,
        "servings_default": 8,
        "timing": {"prep_active_min": 15, "prep_passive_min": 120, "cook_min": 10, "total_min": 145},
        "composition": [
            {"ingredient": "cashew/raw",          "quantity": 150, "unit": "g",  "meta": {"role": "base"}},
            {"ingredient": "nutritional_yeast",   "quantity": 30,  "unit": "g",  "meta": {"role": "flavoring"}},
            {"ingredient": "red_bell_pepper",     "quantity": 60,  "unit": "g",  "meta": {"role": "coloring"}},
            {"ingredient": "citrus/lemon_juice",  "quantity": 30,  "unit": "ml", "meta": {"role": "acidifier"}},
            {"ingredient": "garlic",              "quantity": 5,   "unit": "g",  "meta": {"role": "aromatic"}},
            {"ingredient": "salt",                "quantity": 5,   "unit": "g",  "meta": {"role": "seasoning"}},
        ],
        "tags": {"diet": ["vegan", "vegetarian", "gluten_free"], "meal": ["cheese", "base"], "season": []},
        "dish_type": "base",
        "diet_flags": {"vegan": True, "vegetarian": True, "gluten_free": True,
                       "lactose_free": True, "nut_free": False, "raw": False, "kid_friendly": False},
        "description": "Fromage végétal à base de noix de cajou et de poivron rouge rôti, "
                       "qui imite la saveur et la couleur du cheddar. La levure nutritionnelle "
                       "apporte les notes umami fromagères caractéristiques.",
        "instructions": [
            "Faire tremper 150g de noix de cajou 2 heures dans l'eau froide, puis égoutter.",
            "Rôtir 60g de poivron rouge à 200°C pendant 20 minutes, laisser refroidir et peler.",
            "Mixer tous les ingrédients (cajou, poivron, levure nutritionnelle, jus de citron, "
            "ail, sel) avec 60ml d'eau jusqu'à texture parfaitement lisse.",
            "Verser dans un moule et réfrigérer 2 heures minimum pour que le fromage prenne "
            "une texture plus ferme et découpable.",
        ],
        "scoring": {"confidence": 0.88},
        "_flags": [],
        "_created_by": "resolve_remaining_ingredients.py",
        "_created_at": NOW,
    },
    {
        "id": recipe_id("vegan_mayonnaise"),
        "titles": {"fr": "Mayonnaise Végane", "en": "Vegan Mayonnaise"},
        "origin": {"cuisine": "international", "country": "", "region": "", "city": ""},
        "servings": 8,
        "servings_default": 8,
        "timing": {"prep_active_min": 10, "prep_passive_min": 0, "cook_min": 0, "total_min": 10},
        "composition": [
            {"ingredient": "aquafaba",          "quantity": 60,  "unit": "ml", "meta": {"role": "emulsifier"}},
            {"ingredient": "oil/neutral",       "quantity": 180, "unit": "ml", "meta": {"role": "fat"}},
            {"ingredient": "dijon_mustard",     "quantity": 15,  "unit": "g",  "meta": {"role": "emulsifier"}},
            {"ingredient": "citrus/lemon_juice","quantity": 15,  "unit": "ml", "meta": {"role": "acidifier"}},
            {"ingredient": "salt",              "quantity": 4,   "unit": "g",  "meta": {"role": "seasoning"}},
        ],
        "tags": {"diet": ["vegan", "vegetarian", "gluten_free"], "meal": ["sauce", "condiment"], "season": []},
        "dish_type": "sauce",
        "diet_flags": {"vegan": True, "vegetarian": True, "gluten_free": True,
                       "lactose_free": True, "nut_free": True, "raw": True, "kid_friendly": True},
        "description": "Mayonnaise végane légère et crémeuse préparée à partir d'aquafaba "
                       "(eau de cuisson des pois chiches), qui joue le rôle d'émulsifiant "
                       "naturel. Texture identique à la mayo traditionnelle, sans œuf.",
        "instructions": [
            "Verser 60ml d'aquafaba dans un verre doseur haut et étroit avec 15g de moutarde "
            "de Dijon, 15ml de jus de citron et 4g de sel.",
            "À l'aide d'un mixeur plongeant posé au fond du verre, mixer à pleine vitesse "
            "tout en versant les 180ml d'huile neutre en filet très lentement.",
            "Remonter progressivement le mixeur une fois l'émulsion formée. "
            "Ajuster l'assaisonnement et réfrigérer jusqu'à utilisation (5 jours max).",
        ],
        "scoring": {"confidence": 0.92},
        "_flags": [],
        "_created_by": "resolve_remaining_ingredients.py",
        "_created_at": NOW,
    },
    {
        "id": recipe_id("fried_onion"),
        "titles": {"fr": "Oignon Frit", "en": "Fried Onion"},
        "origin": {"cuisine": "international", "country": "", "region": "", "city": ""},
        "servings": 4,
        "servings_default": 4,
        "timing": {"prep_active_min": 10, "prep_passive_min": 0, "cook_min": 25, "total_min": 35},
        "composition": [
            {"ingredient": "onion",       "quantity": 500, "unit": "g",  "meta": {"role": "base"}},
            {"ingredient": "oil/neutral", "quantity": 60,  "unit": "ml", "meta": {"role": "fat"}},
            {"ingredient": "salt",        "quantity": 5,   "unit": "g",  "meta": {"role": "seasoning"}},
        ],
        "tags": {"diet": ["vegan", "vegetarian", "gluten_free"], "meal": ["condiment", "topping"], "season": []},
        "dish_type": "condiment",
        "diet_flags": {"vegan": True, "vegetarian": True, "gluten_free": True,
                       "lactose_free": True, "nut_free": True, "raw": False, "kid_friendly": True},
        "description": "Oignons émincés lentement frits dans l'huile jusqu'à caramélisation "
                       "complète, sucrés et fondants. Utilisés comme topping ou condiment "
                       "dans de nombreuses cuisines du monde.",
        "instructions": [
            "Émincer finement 500g d'oignons en demi-lunes régulières.",
            "Chauffer 60ml d'huile neutre dans une grande poêle à feu moyen-vif. "
            "Ajouter les oignons et saler.",
            "Cuire 20–25 minutes en remuant régulièrement, d'abord à feu vif puis en "
            "baissant progressivement, jusqu'à obtenir une couleur dorée uniforme et "
            "une texture fondante. Égoutter sur papier absorbant.",
        ],
        "scoring": {"confidence": 0.97},
        "_flags": [],
        "_created_by": "resolve_remaining_ingredients.py",
        "_created_at": NOW,
    },
]

# Les clés d'ingrédient → ID de la nouvelle base_recipe
NEW_BASE_ALIASES = {
    "buckwheat_crepe": recipe_id("buckwheat_crepe"),
    "cashew_ricotta":  recipe_id("cashew_ricotta"),
    "paneer":          recipe_id("paneer"),
    "vegan_cheddar":   recipe_id("vegan_cheddar"),
    "vegan_mayonnaise":recipe_id("vegan_mayonnaise"),
    "fried_onion":     recipe_id("fried_onion"),
}


def main():
    aliases = json.loads(ALIASES.read_text(encoding="utf-8"))
    recipes = json.loads(RECIPES.read_text(encoding="utf-8"))

    bra = aliases.setdefault("base_recipe_aliases", {})
    ra  = aliases.setdefault("recipe_aliases", {})
    recipe_list = recipes.get("recipes", [])
    existing_ids = {r["id"] for r in recipe_list}

    stats = {"bra_added": 0, "ra_added": 0, "ra_updated": 0,
             "recipes_added": 0, "recipes_skipped": 0}

    # ── Étape 1 : brancher les 4 base_recipes existantes ────────────────────
    print("\n=== Étape 1 — Branchement base_recipe_aliases existantes ===")
    for key, bid in EXISTING_BASE.items():
        if key not in bra:
            bra[key] = bid
            print(f"  ADD BRA  {key!r:30} -> {bid}")
            stats["bra_added"] += 1
        else:
            print(f"  SKIP     {key!r:30} (déjà présent: {bra[key]})")

    # ── Étape 2 : aliases directs ────────────────────────────────────────────
    print("\n=== Étape 2 — Aliases directs recipe_aliases ===")
    for key, val in SIMPLE_ALIASES.items():
        current = ra.get(key)
        if current is None:
            ra[key] = val
            print(f"  ADD RA   {key!r:30} -> {val}")
            stats["ra_added"] += 1
        elif current != val:
            ra[key] = val
            print(f"  UPD RA   {key!r:30} {current!r} -> {val!r}")
            stats["ra_updated"] += 1
        else:
            print(f"  OK       {key!r:30} (inchangé)")

    # ── Étape 3 : nouvelles base_recipes ────────────────────────────────────
    print("\n=== Étape 3 — Création nouvelles base_recipes ===")
    for r in NEW_RECIPES:
        if r["id"] in existing_ids:
            print(f"  SKIP     {r['id']}  (déjà dans recipes.json)")
            stats["recipes_skipped"] += 1
        else:
            recipe_list.append(r)
            print(f"  CREATE   {r['id']}  ({r['titles']['fr']})")
            stats["recipes_added"] += 1

    # Brancher les nouveaux IDs dans base_recipe_aliases
    print("\n=== Étape 3b — Branchement nouvelles base_recipe_aliases ===")
    for key, bid in NEW_BASE_ALIASES.items():
        if key not in bra:
            bra[key] = bid
            print(f"  ADD BRA  {key!r:30} -> {bid}")
            stats["bra_added"] += 1
        else:
            print(f"  SKIP     {key!r:30} (déjà: {bra[key]})")

    # ── Stats ────────────────────────────────────────────────────────────────
    print(f"\nStats :")
    print(f"  base_recipe_aliases ajoutés : {stats['bra_added']}")
    print(f"  recipe_aliases ajoutés      : {stats['ra_added']}")
    print(f"  recipe_aliases mis à jour   : {stats['ra_updated']}")
    print(f"  base_recipes créées         : {stats['recipes_added']}")
    print(f"  base_recipes skippées       : {stats['recipes_skipped']}")

    if not DRY_RUN:
        # Mettre à jour les métadonnées
        aliases["base_recipe_aliases_meta"]["total"] = len(bra)
        aliases["base_recipe_aliases_meta"]["last_patched"] = NOW[:10]
        aliases["recipe_aliases_meta"]["total"] = len(ra)
        aliases["recipe_aliases_meta"]["last_patch"] = NOW[:10]

        # Mettre à jour recipes.json
        recipes["recipes"] = recipe_list
        recipes["metadata"]["total_count"] = len(recipe_list)
        recipes["metadata"]["total_recipes"] = len(recipe_list)
        recipes["metadata"]["base_recipes_count"] = sum(
            1 for r in recipe_list if r.get("id", "").startswith("base_")
        )
        recipes["metadata"]["patch_history"].append({
            "date": NOW[:10],
            "action": "add_6_base_recipes_resolve_remaining",
            "fixes": stats["recipes_added"],
            "description": (
                "Ajout 6 base_recipes : buckwheat_crepe, cashew_ricotta, paneer, "
                "vegan_cheddar, vegan_mayonnaise, fried_onion"
            ),
        })

        ALIASES.write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")
        RECIPES.write_text(json.dumps(recipes, ensure_ascii=False, indent=2), encoding="utf-8")
        print("\n  ✓ nutrition_aliases_v6.json mis à jour")
        print(f"  ✓ recipes.json mis à jour ({len(recipe_list)} recettes total)")
    else:
        print("\n  → Pas d'écriture (dry-run).")


if __name__ == "__main__":
    main()
