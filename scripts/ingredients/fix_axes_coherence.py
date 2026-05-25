#!/usr/bin/env python3
"""
scripts/ingredients/fix_axes_coherence.py
==========================================
Corrections ciblées issues audit_axes_coherence.py.
13 corrections réelles identifiées (faux-positifs écartés).

Usage :
  python scripts/ingredients/fix_axes_coherence.py --dry-run
  python scripts/ingredients/fix_axes_coherence.py
"""

import argparse
import copy
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT      = Path(__file__).resolve().parents[2]
TREE_FILE = ROOT / "backend/data/ingredients/ingredients_tree.json"
OUT_DIR   = ROOT / "scripts/ingredients"

# ── Corrections IG : axes_en + axes_fr + éventuellement canonical_name_en ──────

FIXES: dict[str, dict] = {
    # A. EN↔FR encodage/type erroné
    # -----------------------------------------------------------------------
    # ing_02129 "nutritional yeast flakes" : forme='paillettes' → 'flocons'
    "ing_02129": {
        "axes_en": {},
        "axes_fr": {"forme": "flocons"},   # correction sans toucher axes_en
    },
    # ing_01228 "table salt, iodised" : traitement=['iodé'] → 'iodé' (string)
    "ing_01228": {
        "axes_en": {},
        "axes_fr": {"traitement": "iodé"},
    },
    # ing_04589 "peanut butter" : forme='butter' → 'beurre'
    "ing_04589": {
        "axes_en": {},
        "axes_fr": {"forme": "beurre"},
    },

    # B1. Jus sans form=juice (+ cooking_state=raw incohérent pour un jus)
    # -----------------------------------------------------------------------
    # ing_01039 "lemon juice or bottled"
    "ing_01039": {
        "axes_en": {"form": "juice"},
        "axes_fr": {"forme": "jus"},
        "remove_axes_en": ["cooking_state"],    # pas de cooking_state sur un jus
        "remove_axes_fr": ["etat_cuisson"],
    },
    # ing_01115 "passion fruit juice, purple"
    "ing_01115": {
        "axes_en": {"form": "juice"},
        "axes_fr": {"forme": "jus"},
        "remove_axes_en": ["cooking_state"],
        "remove_axes_fr": ["etat_cuisson"],
    },
    # ing_01117 "passion fruit juice, yellow"
    "ing_01117": {
        "axes_en": {"form": "juice"},
        "axes_fr": {"forme": "jus"},
        "remove_axes_en": ["cooking_state"],
        "remove_axes_fr": ["etat_cuisson"],
    },
    # ing_01240 "lime juice in bottled"
    "ing_01240": {
        "axes_en": {"form": "juice"},
        "axes_fr": {"forme": "jus"},
    },
    # ing_01914 "grapefruit juice, pink"
    "ing_01914": {
        "axes_en": {"form": "juice"},
        "axes_fr": {"forme": "jus"},
        "remove_axes_en": ["cooking_state"],
        "remove_axes_fr": ["etat_cuisson"],
    },
    # ing_01916 "grapefruit juice, white"
    "ing_01916": {
        "axes_en": {"form": "juice"},
        "axes_fr": {"forme": "jus"},
        "remove_axes_en": ["cooking_state"],
        "remove_axes_fr": ["etat_cuisson"],
    },

    # B2. Olives drained : draining absent alors que le nom le dit
    # -----------------------------------------------------------------------
    # ing_03234 "black olive, drained"
    "ing_03234": {
        "axes_en": {"draining": "drained"},
        "axes_fr": {"egouttage": "égoutté"},
    },
    # ing_03238 "green olive, drained"
    "ing_03238": {
        "axes_en": {"draining": "drained"},
        "axes_fr": {"egouttage": "égoutté"},
    },

    # B3. Pomme de terre vapeur sous vide : cooking_state absent
    # -----------------------------------------------------------------------
    # ing_01698 "steamed potato, vacuum-packed"
    "ing_01698": {
        "axes_en": {"cooking_state": "steamed"},
        "axes_fr": {"etat_cuisson": "vapeur"},
    },

    # B4. Farine de blé T55 : aucun axe — form=flour manquant
    # -----------------------------------------------------------------------
    # ing_00621 "wheat flour T55 for bread"
    "ing_00621": {
        "axes_en": {"form": "flour"},
        "axes_fr": {"forme": "farine"},
    },

    # B5. Sesame butter : nom contient encore ", paste" alors que form=butter
    # -----------------------------------------------------------------------
    # ing_04553 : simplifier le nom en retirant ", paste"
    "ing_04553": {
        "axes_en": {},
        "axes_fr": {},
        "canonical_name_en": "sesame butter, from whole seed",
    },
}


def apply_fix(ig: dict, fix: dict, label: str) -> list[str]:
    log = []
    axes_en = ig.setdefault("axes_en", {})
    axes_fr = ig.setdefault("axes_fr", {})

    # Mises à jour axes_en
    for key, val in fix.get("axes_en", {}).items():
        old = axes_en.get(key)
        if old != val:
            axes_en[key] = val
            log.append(f"  [{label}] axes_en.{key}: {old!r} → {val!r}")

    # Mises à jour axes_fr
    for key, val in fix.get("axes_fr", {}).items():
        old = axes_fr.get(key)
        if old != val:
            axes_fr[key] = val
            log.append(f"  [{label}] axes_fr.{key}: {old!r} → {val!r}")

    # Suppressions axes_en
    for key in fix.get("remove_axes_en", []):
        if key in axes_en:
            old = axes_en.pop(key)
            log.append(f"  [{label}] axes_en.{key} supprimé (était {old!r})")

    # Suppressions axes_fr
    for key in fix.get("remove_axes_fr", []):
        if key in axes_fr:
            old = axes_fr.pop(key)
            log.append(f"  [{label}] axes_fr.{key} supprimé (était {old!r})")

    # Mise à jour canonical_name_en
    if "canonical_name_en" in fix:
        old = ig.get("canonical_name_en", "")
        new = fix["canonical_name_en"]
        if old != new:
            ig["canonical_name_en"] = new
            log.append(f"  [{label}] canonical_name_en: {old!r} → {new!r}")

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

    if args.dry_run:
        tree_work = copy.deepcopy(tree)
    else:
        tree_work = tree

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
        print(f"\nATTENTION : IDs non trouvés dans le tree : {missed}")

    print(f"\n=== RÉSUMÉ ===")
    print(f"  IGs modifiés : {len(applied_ids)}")

    if not args.dry_run:
        TREE_FILE.write_text(
            json.dumps(tree_work, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nTree sauvegardé : {TREE_FILE}")

    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "fixes_applied": list(applied_ids),
        "log": all_log,
    }
    (OUT_DIR / "fix_axes_coherence_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Rapport : {OUT_DIR}/fix_axes_coherence_report.json")


if __name__ == "__main__":
    main()
