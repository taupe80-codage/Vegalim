import json
from pathlib import Path
from datetime import datetime, UTC

# =====================================================
# PATHS
# =====================================================

BASE_DIR = Path(__file__).resolve().parents[2]

RECIPES_FILE = BASE_DIR / "backend/data/recipes/recipes.json"
ONTOLOGY_FILE = BASE_DIR / "backend/data/reference/ontology_v4.json"
ALIAS_FILE = BASE_DIR / "backend/data/nutrition/alias_index.json"

OUTPUT_RECIPES = BASE_DIR / "backend/data/recipes/recipes_v2.json"

# =====================================================
# UTILS
# =====================================================

def normalize(text):
    return str(text).lower().strip().replace(",", "").replace("_", " ")


# =====================================================
# LOADERS
# =====================================================

def load_json(path):
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# =====================================================
# RESOLVE INGREDIENT (CRITIQUE)
# =====================================================

def resolve_ingredient(name, ontology, alias_index):

    key = normalize(name)

    # 1. direct match
    if key in ontology:
        return key, "direct"

    # 2. alias
    if key in alias_index:
        mapped = alias_index[key]
        if mapped in ontology:
            return mapped, "alias"

    # 3. fallback token matching
    parts = key.split()

    for p in parts:
        if p in ontology:
            return p, "token"

    return None, "unknown"


# =====================================================
# DIET PROFILE
# =====================================================

def get_diet_profile(ingredient, ontology, alias_index, stats):

    resolved, mode = resolve_ingredient(ingredient, ontology, alias_index)

    stats[mode] += 1

    if resolved:
        node = ontology.get(resolved, {})
        diet = node.get("diet", {})
        return {
            "vegan": diet.get("vegan", True),
            "vegetarian": diet.get("vegetarian", True),
            "source": mode
        }

    # fallback sécurisé
    return {
        "vegan": False,
        "vegetarian": False,
        "source": "fallback"
    }


# =====================================================
# COMPUTE FLAGS
# =====================================================

def compute_flags(recipe, ontology, alias_index, stats):

    vegan_strict = True
    vegan_possible = True
    vegetarian_strict = True

    unknown_count = 0

    for item in recipe.get("composition", []):

        ing = item.get("ingredient", "")
        optional = item.get("optional", False)

        profile = get_diet_profile(ing, ontology, alias_index, stats)

        if profile["source"] == "fallback":
            unknown_count += 1
            vegan_possible = False

        # VEGAN
        if not profile["vegan"]:
            if optional:
                vegan_strict = False
            else:
                vegan_strict = False
                vegan_possible = False

        # VEGETARIAN
        if not profile["vegetarian"]:
            if not optional:
                vegetarian_strict = False

    if vegan_strict:
        vegetarian_strict = True

    return {
        "vegan_strict": vegan_strict,
        "vegan_possible": vegan_possible,
        "vegetarian_strict": vegetarian_strict,
        "unknown_ingredients": unknown_count
    }


# =====================================================
# MAIN
# =====================================================

def main():

    ontology = load_json(ONTOLOGY_FILE)
    alias_index = load_json(ALIAS_FILE)

    with open(RECIPES_FILE, encoding="utf-8") as f:
        data = json.load(f)

    recipes = data.get("recipes", [])

    stats = {
        "direct": 0,
        "alias": 0,
        "token": 0,
        "fallback": 0,
        "unknown": 0
    }

    for recipe in recipes:

        flags = compute_flags(recipe, ontology, alias_index, stats)

        recipe["diet_flags_v3"] = flags
        recipe["diet_flags_meta"] = {
            "version": "v3_ontology_resolved",
            "updated_at": datetime.now(UTC).isoformat()
        }

    # SAVE
    data["recipes"] = recipes

    with open(OUTPUT_RECIPES, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    # REPORT
    print("\n════════════════════════════════════")
    print(" DIET FLAGS UPDATE V3")
    print("════════════════════════════════════")
    print(f" Recettes        : {len(recipes)}")
    print(f" Direct matches  : {stats['direct']}")
    print(f" Alias matches   : {stats['alias']}")
    print(f" Token matches   : {stats['token']}")
    print(f" Fallback        : {stats['fallback']}")
    print("════════════════════════════════════")


if __name__ == "__main__":
    main()