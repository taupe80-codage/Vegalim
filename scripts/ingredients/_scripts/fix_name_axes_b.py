#!/usr/bin/env python3
"""
scripts/ingredients/_scripts/fix_name_axes_b.py
==================================================
Corrections catégorie B (nom -> axes) de audit_axes_coherence.py, 53 issues
passées en revue une par une :

- 22 vraies corrections (ce fichier).
- 31 faux positifs documentés (non touchés) : "X milk Y" sur des fromages
  (milk = modificateur d'origine, pas la forme du produit — fromage n'est
  jamais "sous forme de lait"), buttermilk/condensed/powdered milk (déjà
  correctement affinés en liquid/concentrated/powder), "bread, made with
  milk" (milk = ingrédient de la recette, pas la forme du pain), "cooked
  pressed cheese" (le "cooked" désigne l'étape de cuisson du caillé en
  fromagerie, pas un cooking_state), fat_content numérique vs catégoriel
  (asymétrie déjà documentée en session précédente).

Usage :
  python scripts/ingredients/_scripts/fix_name_axes_b.py --dry-run
  python scripts/ingredients/_scripts/fix_name_axes_b.py
"""

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT      = Path(__file__).resolve().parents[3]
TREE_FILE = ROOT / "backend/data/ingredients/ingredients_tree.json"
OUT_DIR   = ROOT / "scripts/ingredients/_scripts"

FIXES: dict[str, dict] = {
    # Forme absente alors que le nom la porte explicitement (powder/oil/flour)
    "ing_05877": {"axes_en": {"form": "oil"},    "axes_fr": {"forme": "huile"}},     # soy lecithin oil
    "ing_05835": {"axes_en": {"form": "powder"}, "axes_fr": {"forme": "poudre"}},    # matcha green tea powder
    "ing_05820": {"axes_en": {"form": "powder"}, "axes_fr": {"forme": "poudre"}},    # wheatgrass powder
    "ing_05823": {"axes_en": {"form": "flour"},  "axes_fr": {"forme": "farine"}},    # tempura flour
    "ing_05786": {"axes_en": {"form": "powder"}, "axes_fr": {"forme": "poudre"}},    # baobab powder
    "ing_05794": {"axes_en": {"form": "powder"}, "axes_fr": {"forme": "poudre"}},    # amchoor powder
    "ing_05797": {"axes_en": {"form": "powder"}, "axes_fr": {"forme": "poudre"}},    # sambar powder
    "ing_05825": {"axes_en": {"form": "powder"}, "axes_fr": {"forme": "poudre"}},    # maca powder

    # Assaisonnement absent alors que le nom le porte
    "ing_05840": {"axes_en": {"seasoning": "salted"}, "axes_fr": {"assaisonnement": "salé"}},  # salted crackers

    # "roasted chickpea" : convention légumineuse-snack = treatment (comme
    # les cacahuètes, autre légumineuse), pas cooking_state. Sans
    # cooking_process -> torréfié (règle déjà établie en catégorie A).
    "ing_05814": {"axes_en": {"treatment": "roasted"}, "axes_fr": {"traitement": "torréfié"}},

    # "milk" nu (sans qualificatif fromage/yaourt/etc.) sans axe form=liquid,
    # incohérent avec ing_05466 "milk" et ing_05763 "milk, 2%, liquid" qui
    # l'ont déjà -- lait liquide standard, sans ambiguïté de forme.
    "ing_05410": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # sheep's milk
    "ing_05412": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # buffalo milk
    "ing_05414": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # goat's milk
    "ing_05416": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # goat's milk
    "ing_05418": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # goat's milk
    "ing_05422": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # mare's milk
    "ing_05426": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # milk
    "ing_05428": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # milk
    "ing_05432": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # milk
    "ing_05434": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # milk
    "ing_05436": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # milk
    "ing_05749": {"axes_en": {"form": "liquid"}, "axes_fr": {"forme": "liquide"}},  # milk
}


def apply_fix(ig: dict, fix: dict, label: str) -> list[str]:
    log = []
    axes_en = ig.setdefault("axes_en", {})
    axes_fr = ig.setdefault("axes_fr", {})
    for key, val in fix.get("axes_en", {}).items():
        old = axes_en.get(key)
        if old != val:
            axes_en[key] = val
            log.append(f"  [{label}] axes_en.{key}: {old!r} -> {val!r}")
    for key, val in fix.get("axes_fr", {}).items():
        old = axes_fr.get(key)
        if old != val:
            axes_fr[key] = val
            log.append(f"  [{label}] axes_fr.{key}: {old!r} -> {val!r}")
    return log


def walk_groups(tree: dict):
    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                yield ig


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Chargement du tree...")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))
    tree_work = copy.deepcopy(tree) if args.dry_run else tree

    print(f"Application {'(DRY-RUN) ' if args.dry_run else ''}...\n")

    all_log = []
    applied_ids = set()
    for ig in walk_groups(tree_work):
        if ig["id"] in FIXES:
            log = apply_fix(ig, FIXES[ig["id"]], ig["id"])
            if log:
                en = ig.get("canonical_name_en", "")
                all_log.append(f"\n[{ig['id']}] {en}")
                all_log.extend(log)
                applied_ids.add(ig["id"])

    for line in all_log:
        print(line)

    missed = set(FIXES.keys()) - applied_ids
    if missed:
        print(f"\nATTENTION : IDs non trouvés/non modifiés : {missed}")

    print("\n=== RESUME ===")
    print(f"  IGs modifiés : {len(applied_ids)}")

    if not args.dry_run:
        TREE_FILE.write_text(
            json.dumps(tree_work, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nTree sauvegardé : {TREE_FILE}")

    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "fixes_applied": sorted(applied_ids),
        "log": all_log,
    }
    (OUT_DIR / "fix_name_axes_b_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Rapport : {OUT_DIR}/fix_name_axes_b_report.json")


if __name__ == "__main__":
    main()
