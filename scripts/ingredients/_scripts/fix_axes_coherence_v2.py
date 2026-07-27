#!/usr/bin/env python3
"""
scripts/ingredients/_scripts/fix_axes_coherence_v2.py
=======================================================
Corrections issues du 2e passage audit_axes_coherence.py (post-fusion 393d8bc).

La majorité des 250 signalements de la section A (67 FR_WITHOUT_EN +
quelques EN_FR_MISMATCH) étaient un FAUX POSITIF de l'outil d'audit lui-même :
la clé EN réelle du tree est `cooking_process` (voir meta.structure du tree),
pas `cooking_method` que l'audit cherchait — corrigé séparément dans
audit_axes_coherence.py. Ce script ne couvre que les VRAIES corrections de
données restantes après ce correctif outil.

Usage :
  python scripts/ingredients/_scripts/fix_axes_coherence_v2.py --dry-run
  python scripts/ingredients/_scripts/fix_axes_coherence_v2.py
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
    # A1. celery flakes : "flocons" est le terme des flocons roulés (avoine,
    # pomme de terre) ; pour des paillettes séchées de céleri (assaisonnement),
    # le terme réel est "paillettes" — cf. nutritional yeast (ing_02129) qui
    # utilise déjà "paillettes" pour le même type de produit.
    "ing_02854": {
        "axes_fr": {"forme": "paillettes"},
    },
    # A2. tomato crushed : "tomates concassées" est le terme consacré (cf.
    # ing_03596 "tomate concassée" qui utilise déjà ce terme, au féminin
    # pour accorder avec "tomate").
    "ing_03628": {
        "axes_fr": {"forme": "concassée"},
    },
    # A3. almond / sunflower roasted+dry : incohérent avec les 3 IGs soeurs
    # (ing_00251, ing_05768, ing_00617) qui utilisent déjà "rôti" pour la
    # même combinaison treatment=roasted + cooking_process=dry.
    "ing_00530": {
        "axes_fr": {"traitement": "rôti"},
    },
    "ing_00625": {
        "axes_fr": {"traitement": "rôti"},
    },
    # A4. egg soft_boiled : "coque" seul n'est pas un état, le terme
    # culinaire complet est "à la coque" (œuf à la coque).
    "ing_05746": {
        "axes_fr": {"etat_cuisson": "à la coque"},
    },
    # A5. EN_WITHOUT_FR : axes_en.cooking_state=raw sans équivalent axes_fr.
    "ing_01427": {
        "axes_fr": {"etat_cuisson": "cru"},
    },
    "ing_01888": {
        "axes_fr": {"etat_cuisson": "cru"},
    },
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
        print(f"\nATTENTION : IDs non trouvés/non modifiés dans le tree : {missed}")

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
    (OUT_DIR / "fix_axes_coherence_v2_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Rapport : {OUT_DIR}/fix_axes_coherence_v2_report.json")


if __name__ == "__main__":
    main()
