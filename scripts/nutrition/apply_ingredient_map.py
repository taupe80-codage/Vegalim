"""
apply_ingredient_map.py
=======================
Applique ingredient_map_2026-05-23.json → recipe_aliases de nutrition_aliases_v6.json.

Pour chaque entrée matchée (status != unmatched, nutri_id != null) :
  1. Vérifie que le nutri_id existe dans nutrition_v2
  2. Détermine le meilleur variant (default > premier dispo)
  3. Construit la clé "nutri_id/variant"
  4. Ajoute/met à jour recipe_aliases (ne touche pas base_recipe_aliases)

Usage :
  python scripts/nutrition/apply_ingredient_map.py [--dry-run]
"""
import io
import json
import sys
from pathlib import Path

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data"

INGREDIENT_MAP = DATA / "recipes" / "ingredient_map_2026-05-23.json"
NUTRITION_V2   = DATA / "nutrition" / "processed" / "nutrition_v2.json"
ALIASES_FILE   = DATA / "nutrition" / "reference" / "nutrition_aliases_v6.json"

DRY_RUN = "--dry-run" in sys.argv


def best_variant(variants: dict) -> str:
    """Retourne le meilleur variant : default > raw > premier dispo."""
    for preferred in ("default", "raw", "dried", "cooked"):
        if preferred in variants:
            return preferred
    return next(iter(variants))


def main():
    # Charger les fichiers
    ing_map   = json.loads(INGREDIENT_MAP.read_text(encoding="utf-8"))
    n2_raw    = json.loads(NUTRITION_V2.read_text(encoding="utf-8"))
    aliases   = json.loads(ALIASES_FILE.read_text(encoding="utf-8"))

    n2_ingredients = n2_raw.get("ingredients", {})
    recipe_aliases = aliases.get("recipe_aliases", {})

    stats = {"added": 0, "updated": 0, "already_ok": 0, "skipped_unmatched": 0,
             "nutri_id_not_in_n2": 0, "no_variants": 0}
    changes = []

    for recipe_key, entry in ing_map.items():
        status   = entry.get("status")
        nutri_id = entry.get("nutri_id")

        if status == "unmatched" or nutri_id is None:
            stats["skipped_unmatched"] += 1
            continue

        # Vérifier que nutri_id existe dans nutrition_v2
        n2_entry = n2_ingredients.get(nutri_id)
        if n2_entry is None:
            print(f"  [WARN] nutri_id '{nutri_id}' absent de nutrition_v2  ←  {recipe_key}")
            stats["nutri_id_not_in_n2"] += 1
            continue

        # Trouver le meilleur variant
        variants = n2_entry.get("variants", {})
        if not variants:
            print(f"  [WARN] '{nutri_id}' n'a pas de variants  ←  {recipe_key}")
            stats["no_variants"] += 1
            continue

        variant   = best_variant(variants)
        alias_val = f"{nutri_id}/{variant}"

        current = recipe_aliases.get(recipe_key)
        if current == alias_val:
            stats["already_ok"] += 1
        elif current is None:
            recipe_aliases[recipe_key] = alias_val
            changes.append(f"  ADD     {recipe_key!r:45} → {alias_val}")
            stats["added"] += 1
        else:
            recipe_aliases[recipe_key] = alias_val
            changes.append(f"  UPDATE  {recipe_key!r:45} {current!r} → {alias_val!r}")
            stats["updated"] += 1

    print(f"\n{'=== DRY RUN ===' if DRY_RUN else '=== APPLY ==='}")
    if changes:
        for c in changes:
            print(c)
    else:
        print("  Aucun changement.")

    print(f"\nStats :")
    print(f"  Ajoutés       : {stats['added']}")
    print(f"  Mis à jour    : {stats['updated']}")
    print(f"  Déjà corrects : {stats['already_ok']}")
    print(f"  Non matchés   : {stats['skipped_unmatched']}")
    print(f"  nutri_id absent de n2  : {stats['nutri_id_not_in_n2']}")
    print(f"  Sans variants          : {stats['no_variants']}")

    if not DRY_RUN:
        aliases["recipe_aliases"] = recipe_aliases
        total = len(recipe_aliases)
        aliases.setdefault("recipe_aliases_meta", {})
        aliases["recipe_aliases_meta"]["total"]            = total
        aliases["recipe_aliases_meta"]["last_patch"]       = "2026-05-24T00:00:00Z"
        aliases["recipe_aliases_meta"]["patch_description"] = (
            f"apply_ingredient_map 2026-05-23 : {stats['added']} added, "
            f"{stats['updated']} updated"
        )
        ALIASES_FILE.write_text(
            json.dumps(aliases, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"\n  ✓ nutrition_aliases_v6.json mis à jour ({total} recipe_aliases).")
    else:
        print("\n  → Pas d'écriture (dry-run).")


if __name__ == "__main__":
    main()
