"""
scripts/add_recipe_aliases.py
Injecte les 24 aliases manquants dans nutrition_aliases_v6.json
section 'recipe_aliases'.

Chaque alias est verifie contre nutrition_v2 avant injection.
Principe : jamais d'approximation, toujours le variant exact.

Usage :
    python -m scripts.add_recipe_aliases
    python -m scripts.add_recipe_aliases --dry-run
"""
from __future__ import annotations
import argparse, json, pathlib

ALIASES_PATH = pathlib.Path("backend/data/nutrition/reference/nutrition_aliases_v6.json")
NUTR_PATH    = pathlib.Path("backend/data/nutrition/processed/nutrition_v2.json")

# ── Mappings exacts (audites par check_alias_targets.py + find_spice_keys.py)
# Format : "token_composition" -> "base_db/variant_exact"
# __null__ = ingredient sans contribution nutritionnelle (condiment ultra-mineur)
NEW_ALIASES: dict[str, str] = {
    # Huiles — base 'oil'
    "all_purpose_flour":   "flour/wheat",
    "olive_oil":           "oil/olive",
    "sesame_oil":          "oil/sesame",
    "sunflower_oil":       "oil/sunflower",
    "neutral_oil":         "oil/default",

    # Sucres — base 'sugar'
    "cane_sugar":          "sugar/cane",

    # Sauces — base 'sauce'
    "soy_sauce":           "sauce/soy",
    "tomato_ketchup":      "sauce/default",

    # Produits laitiers
    "heavy_cream":         "cream_animal/heavy",
    "dijon_mustard":       "mustard/default",

    # Legumes & condiments
    "lemon":               "citrus/lemon",
    "green_onion":         "onion/spring",
    "napa_cabbage":        "cabbage/default",
    "chili_pepper":        "chili/default",
    "korean_chili_pepper": "chili/korean",

    # Noix & graines
    "pine_nut":            "nut/pine",
    "dark_chocolate":      "chocolate/dark",

    # Farines — base 'flour'
    "rice_flour":          "flour/rice",

    # Vinaigres — base 'vinegar'
    "rice_vinegar":        "vinegar/rice",

    # Bouillons — base 'broth'
    "vegetable_broth":     "broth/vegetable",

    # Epices — base 'cloves' / 'spices' / 'pepper'
    "clove":               "cloves/default",
    "five_spice":          "spices/default",
    "sichuan_pepper":      "pepper/default",

    # Sans donnee nutritionnelle disponible
    "doubanjiang_paste":   "__null__",
}


def main(dry_run: bool = False) -> None:
    # Charger la DB nutrition pour verification
    nutr_db = {}
    if NUTR_PATH.exists():
        nd = json.loads(NUTR_PATH.read_text(encoding="utf-8"))
        nutr_db = nd.get("ingredients", nd) if isinstance(nd, dict) else {}

    # Verifier chaque mapping
    verified:   dict[str, str] = {}
    rejected:   list[tuple]    = []

    for token, target in NEW_ALIASES.items():
        if target == "__null__":
            verified[token] = target
            continue
        base, _, variant = target.partition("/")
        entry    = nutr_db.get(base, {})
        variants = entry.get("variants", {})
        if not entry:
            rejected.append((token, target, f"base '{base}' absente"))
        elif variant and variant not in variants:
            rejected.append((token, target,
                             f"variant '{variant}' absent — dispo: {list(variants.keys())}"))
        else:
            verified[token] = target

    print(f"=== Injection aliases ===")
    print(f"  Verifies OK : {len(verified)}")
    print(f"  Rejetes     : {len(rejected)}")

    if rejected:
        print("\n  [REJETE]")
        for tok, tgt, reason in rejected:
            print(f"    {tok:30s} -> {tgt} | {reason}")

    print(f"\n  [VERIFIES]")
    for tok, tgt in sorted(verified.items()):
        print(f"    {tok:30s} -> {tgt}")

    if dry_run:
        print("\nDRY RUN — aucune ecriture.")
        return

    # Charger les aliases existants
    data = json.loads(ALIASES_PATH.read_text(encoding="utf-8")) if ALIASES_PATH.exists() else {}
    recipe_aliases: dict = data.get("recipe_aliases", {})

    # Compter les nouveaux (ne pas ecraser ceux qui existent deja)
    added = skipped = 0
    for tok, tgt in verified.items():
        if tok in recipe_aliases:
            skipped += 1
        else:
            recipe_aliases[tok] = tgt
            added += 1

    data["recipe_aliases"] = recipe_aliases
    ALIASES_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Ajoutes : {added} | Ignores (existants) : {skipped}")
    print(f"  Ecrit  : {ALIASES_PATH.name} ({len(recipe_aliases)} aliases total)")

    # Invalider le cache LRU
    try:
        from backend.db.culinary_repositories import _aliases_raw, _base_recipe_aliases_raw
        _aliases_raw.cache_clear()
        _base_recipe_aliases_raw.cache_clear()
        print("  Caches LRU invalides.")
    except Exception as e:
        print(f"  Cache clear KO (non bloquant): {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    main(dry_run=parser.parse_args().dry_run)
