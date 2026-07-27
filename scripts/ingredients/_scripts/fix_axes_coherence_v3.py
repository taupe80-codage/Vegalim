#!/usr/bin/env python3
"""
scripts/ingredients/_scripts/fix_axes_coherence_v3.py
=======================================================
Suite de fix_axes_coherence_v2.py, sur 2 axes demandés par l'utilisateur :

A. cooking_state manquant/erroné, détecté par cross-check contre
   source_name_en/fr des variants (le même type d'erreur que
   "stewed" mal saisi "steamed" sur ing_05852 : vérifié sur tout le tree).
B. Séparation des 5 IGs qui portaient des axes au niveau variant (donc 2
   états différents partageaient un seul ing_) en IGs distincts par
   combinaison d'axes — cohérent avec le principe du tree (1 ing_ = 1 nom +
   1 combinaison figée d'axes). Les axes_fr/axes_en du variant déplacé sont
   fusionnés dans le nouvel IG puis vidés côté variant.

Usage :
  python scripts/ingredients/_scripts/fix_axes_coherence_v3.py --dry-run
  python scripts/ingredients/_scripts/fix_axes_coherence_v3.py
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

# ── A. cooking_state fixes (IG-level axes_en + axes_fr) ────────────────────

COOKING_STATE_FIXES: dict[str, dict] = {
    # Manquant alors que le nom + la source disent "raw"/"crue" explicitement,
    # incohérent avec toutes les autres IGs de la même sous-catégorie.
    "ing_05891": {"axes_en": {"cooking_state": "raw"}, "axes_fr": {"etat_cuisson": "cru"}},   # white grapefruit (floride)
    "ing_05779": {"axes_en": {"cooking_state": "raw"}, "axes_fr": {"etat_cuisson": "cru"}},   # squash (pumpkin)
    "ing_05780": {"axes_en": {"cooking_state": "raw"}, "axes_fr": {"etat_cuisson": "cru"}},   # pie pumpkin
    "ing_05789": {"axes_en": {"cooking_state": "raw"}, "axes_fr": {"etat_cuisson": "cru"}},   # kabocha squash (MANUAL, générique = cru comme ses pairs)
    "ing_05781": {"axes_en": {"cooking_state": "raw"}, "axes_fr": {"etat_cuisson": "cru"}},   # banana pepper, seeded
    # ing_05852 "stewed tomatoes" : source CNF dit explicitement "stewed"
    # (pas "steamed") — etat_cuisson=étuvée déjà correct côté FR.
    "ing_05852": {"axes_en": {"cooking_state": "stewed"}},
    # ing_04731 hazelnut : cooking_state=grilled est redondant/incohérent
    # avec le traitement=dry_roasted déjà présent — les 8 autres noix/graines
    # "dry_roasted" du tree ne portent PAS de cooking_state (convention :
    # le rôtissage des fruits à coque passe par `treatment`, pas
    # `cooking_state`). Suppression pour aligner sur cette convention.
    "ing_04731": {"remove_axes_en": ["cooking_state"], "remove_axes_fr": ["etat_cuisson"]},
}


def apply_axis_fix(ig: dict, fix: dict, label: str) -> list[str]:
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
    for key in fix.get("remove_axes_en", []):
        if key in axes_en:
            old = axes_en.pop(key)
            log.append(f"  [{label}] axes_en.{key} supprimé (était {old!r})")
    for key in fix.get("remove_axes_fr", []):
        if key in axes_fr:
            old = axes_fr.pop(key)
            log.append(f"  [{label}] axes_fr.{key} supprimé (était {old!r})")
    return log


# ── B. Séparation des IGs à axes variant ────────────────────────────────────
# Pour chaque IG : id du variant à extraire dans un nouvel IG + id du nouvel IG.
SPLIT_FIXES: list[dict] = [
    # capers, en saumure : le variant CNF porte axes_en={'draining':'brined'},
    # une clé EN erronée (devrait être storage_medium, comme ses pairs
    # black/green olive "en saumure" -> storage_medium=in_brine) pour la
    # même clé FR milieu_conservation que l'IG de base (in_vinegar) — sans
    # correction, le merge garderait à tort in_vinegar. Override explicite.
    {"ig_id": "ing_00188", "variant_id": "var_00189", "new_id": "ing_05893",
     "axes_en_override": {"storage_medium": "in_brine"}, "drop_axes_en": ["draining"]},
    {"ig_id": "ing_04255", "variant_id": "var_05840", "new_id": "ing_05894"},  # chickpea, rincé
    {"ig_id": "ing_04555", "variant_id": "var_04558", "new_id": "ing_05895"},  # tahini, sans sel
    {"ig_id": "ing_04859", "variant_id": "var_04862", "new_id": "ing_05896"},  # butter, tendre
    {"ig_id": "ing_05087", "variant_id": "var_05114", "new_id": "ing_05897"},  # swiss, râpé
]


def split_ig(sub: dict, spec: dict, log: list[str]) -> None:
    igs = sub["ingredient_groups"]
    ig = next((g for g in igs if g["id"] == spec["ig_id"]), None)
    if ig is None:
        return
    variants = ig.get("variants", [])
    vr = next((v for v in variants if v["id"] == spec["variant_id"]), None)
    if vr is None:
        return

    moved_axes_en = vr.get("axes_en") or {}
    moved_axes_fr = vr.get("axes_fr") or {}
    if not moved_axes_en and not moved_axes_fr:
        return  # rien à extraire, déjà traité

    merged_axes_en = {**(ig.get("axes_en") or {}), **moved_axes_en}
    for key in spec.get("drop_axes_en", []):
        merged_axes_en.pop(key, None)
    merged_axes_en.update(spec.get("axes_en_override", {}))

    new_ig = {
        "id": spec["new_id"],
        "canonical_name_fr": ig.get("canonical_name_fr", ""),
        "canonical_name_en": ig.get("canonical_name_en", ""),
        "indus_conditionne": vr.get("indus_conditionne", ig.get("indus_conditionne", False)),
        "indus_conditionne_only": ig.get("indus_conditionne_only", False),
        "conditioning_types": vr.get("conditioning_types") or ig.get("conditioning_types") or [],
        "axes_fr": {**(ig.get("axes_fr") or {}), **moved_axes_fr},
        "axes_en": merged_axes_en,
        "preferred_source": vr.get("source", ig.get("preferred_source", "")),
        "variants": [
            {**vr, "axes_en": {}, "axes_fr": {}, "is_primary": True},
        ],
    }
    if ig.get("aliases_fr"):
        new_ig["aliases_fr"] = ig["aliases_fr"]

    ig["variants"] = [v for v in variants if v["id"] != spec["variant_id"]]
    # Le variant restant (souvent déjà primary) devient l'unique variant de l'IG d'origine.
    if len(ig["variants"]) == 1:
        ig["variants"][0]["is_primary"] = True

    idx = igs.index(ig)
    igs.insert(idx + 1, new_ig)

    log.append(
        f"\n[SPLIT] {spec['ig_id']} -> {spec['new_id']} "
        f"({new_ig['canonical_name_en']}, variant {spec['variant_id']})"
    )
    log.append(f"  axes_fr nouveau IG : {new_ig['axes_fr']}")
    log.append(f"  axes_en nouveau IG : {new_ig['axes_en']}")
    log.append(f"  variant {spec['variant_id']} : axes_fr/axes_en vidés, is_primary=True")
    if len(ig["variants"]) == 1:
        log.append(f"  IG d'origine {spec['ig_id']} : variant restant promu is_primary=True")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    print("Chargement du tree...")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))
    tree_work = copy.deepcopy(tree) if args.dry_run else tree

    print(f"Application {'(DRY-RUN) ' if args.dry_run else ''}...\n")

    all_log: list[str] = []
    applied_axis_ids = set()

    for cat in tree_work.get("categories", []):
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                if ig["id"] in COOKING_STATE_FIXES:
                    log = apply_axis_fix(ig, COOKING_STATE_FIXES[ig["id"]], ig["id"])
                    if log:
                        en = ig.get("canonical_name_en", "")
                        all_log.append(f"\n[{ig['id']}] {en}")
                        all_log.extend(log)
                        applied_axis_ids.add(ig["id"])

    for cat in tree_work.get("categories", []):
        for sub in cat.get("subcategories", []):
            for spec in SPLIT_FIXES:
                split_ig(sub, spec, all_log)

    for line in all_log:
        print(line)

    missed = set(COOKING_STATE_FIXES.keys()) - applied_axis_ids
    if missed:
        print(f"\nATTENTION : IDs cooking_state non trouvés/non modifiés : {missed}")

    n_igs_after = sum(
        len(sub["ingredient_groups"])
        for cat in tree_work["categories"]
        for sub in cat["subcategories"]
    )
    tree_work.setdefault("meta", {}).setdefault("stats", {})["total_ingredient_groups"] = n_igs_after

    print("\n=== RESUME ===")
    print(f"  IGs modifiés (cooking_state) : {len(applied_axis_ids)}")
    print(f"  IGs séparés (split)          : {len(SPLIT_FIXES)}")
    print(f"  Total ingredient_groups      : {n_igs_after}")

    if not args.dry_run:
        TREE_FILE.write_text(
            json.dumps(tree_work, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nTree sauvegardé : {TREE_FILE}")

    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "cooking_state_fixes_applied": sorted(applied_axis_ids),
        "splits_applied": [s["ig_id"] + "->" + s["new_id"] for s in SPLIT_FIXES],
        "log": all_log,
    }
    (OUT_DIR / "fix_axes_coherence_v3_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Rapport : {OUT_DIR}/fix_axes_coherence_v3_report.json")


if __name__ == "__main__":
    main()
