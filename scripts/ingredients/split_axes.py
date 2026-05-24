#!/usr/bin/env python3
"""
split_axes.py — Séparation axes FR/EN + corrections ciblées
============================================================
Transforme la structure plate `axes: {etat_cuisson: cru, cooking_state: raw}`
en deux dicts distincts :
  axes_en: {cooking_state: raw}
  axes_fr: {etat_cuisson: cru}

Opérations :
  1. Split axes → axes_en + axes_fr pour tous IGs et variants
  2. Normalise cooking_state boiled/cooked dans les variants quand IG=boiled
  3. Corrections ciblées :
     - ing_01872 : grape (vine) → vine leaf (part:leaf, raw)
     - ing_01906 : supprime part:seeds (raisin golden seedless)
     - ing_01910 : raisin (sultana) → sultana raisin
     - ing_01920 : grapes, green + form:juice (erroné) → grape + color:green
     - ing_01922 : grape juice concentrate → grape juice + form:concentrate
     - ing_01928 : grape → vine leaf (canned)
     - ing_00005 : gelatin → flag ingrédient animal
  4. Ajoute axes form manquants : tomato paste, tomato sauce, etc.

Usage :
  python scripts/ingredients/split_axes.py --dry-run
  python scripts/ingredients/split_axes.py
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT      = Path(__file__).resolve().parents[2]
TREE_FILE = ROOT / "backend/data/ingredients/ingredients_tree.json"
OUT_DIR   = ROOT / "scripts/ingredients"

# ── Clés EN connues ────────────────────────────────────────────────────────────
EN_AXIS_KEYS = {
    "cooking_state", "thermal_state", "form", "part", "treatment",
    "fat_content", "fat_content_pct", "seasoning", "packaging", "draining",
    "origin", "ripeness", "ripening", "color", "size", "variety", "sodium",
}

# ── Clés FR connues ────────────────────────────────────────────────────────────
FR_AXIS_KEYS = {
    "etat_cuisson", "etat_thermique", "forme", "partie", "traitement",
    "teneur_MG", "assaisonnement", "conditionnement", "egouttage",
    "milieu_conservation", "origine", "maturite", "procede_cuisson",
}

# ── Traduction EN cooking_state : cooked → boiled (correction de précision) ───
COOKED_TO_BOILED_EN = {"cooked": "boiled"}
COOKED_TO_BOILED_FR = {"cuit": "bouilli", "cuite": "bouilli"}

# ── Corrections ciblées ────────────────────────────────────────────────────────
TARGETED_FIXES: dict[str, dict] = {
    # vine leaf (raw)
    "ing_01872": {
        "canonical_name_en": "vine leaf",
        "canonical_name_fr": "feuille de vigne",
    },
    # golden seedless — retire l'axe part:seeds (incohérent avec "seedless")
    "ing_01906": {
        "_remove_axes_en": {"part"},
        "_remove_axes_fr": {"partie"},
        "_remove_variant_axes_en": {"part"},
        "_remove_variant_axes_fr": {"partie"},
    },
    # sultana raisin
    "ing_01910": {
        "canonical_name_en": "sultana raisin",
        "canonical_name_fr": "raisin sultana",
    },
    # fresh green grape — le form:juice était erroné; ajoute color:green
    "ing_01920": {
        "canonical_name_en": "grape",
        "canonical_name_fr": "raisin blanc",
        "_remove_axes_en": {"form"},
        "_remove_axes_fr": {"forme"},
        "_add_axes_en": {"color": "green"},
    },
    # grape juice concentrate — simplifie le nom
    "ing_01922": {
        "canonical_name_en": "grape juice",
        "canonical_name_fr": "jus de raisin",
    },
    # vine leaf (canned)
    "ing_01928": {
        "canonical_name_en": "vine leaf",
        "canonical_name_fr": "feuille de vigne",
    },
    # gelatin — flag animal
    "ing_00005": {
        "_dietary_flag": (
            "ANIMAL_BASED: gélatine animale (CIQUAL:11007). "
            "Projet 100% végétarien — remplacer par agar-agar si nécessaire."
        ),
    },
}

# ── Axes form manquants à ajouter ─────────────────────────────────────────────
FORM_AXIS_ADDS: dict[str, tuple[str, str]] = {
    # ig_id → (form_en_value, forme_fr_value)
    "ing_03638": ("paste",  "pâte"),       # tomato paste
    "ing_03644": ("sauce",  "sauce"),      # tomato sauce
    "ing_03572": ("sauce",  "sauce"),      # pizza tomato sauce
    "ing_05613": ("sauce",  "sauce"),      # caramel sauce
}


# ══════════════════════════════════════════════════════════════════════════════
# FONCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def split_axes(axes: dict) -> tuple[dict, dict]:
    """Sépare un dict axes mixte en (axes_en, axes_fr)."""
    axes_en: dict = {}
    axes_fr: dict = {}
    for k, v in (axes or {}).items():
        if k in EN_AXIS_KEYS:
            axes_en[k] = v
        elif k in FR_AXIS_KEYS:
            axes_fr[k] = v
        else:
            # Clé inconnue → axes_en par défaut (post-migration, toutes nouvelles clés sont EN)
            axes_en[k] = v
    return axes_en, axes_fr


def walk_groups(tree: dict):
    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                yield ig


def apply_tree(tree: dict, dry_run: bool) -> dict:
    stats = {
        "igs_processed": 0,
        "vars_processed": 0,
        "cooking_conflicts_fixed": 0,
        "targeted_fixes": 0,
        "form_axes_added": 0,
        "unknown_keys": [],
    }
    changes: list = []

    for ig in walk_groups(tree):
        ig_id = ig.get("id", "")
        stats["igs_processed"] += 1

        # ── 1. Split IG axes ──────────────────────────────────────────────────
        old_axes = ig.get("axes", {})
        ig_axes_en, ig_axes_fr = split_axes(old_axes)

        # Track unknown keys
        for k in old_axes:
            if k not in EN_AXIS_KEYS and k not in FR_AXIS_KEYS and k not in stats["unknown_keys"]:
                stats["unknown_keys"].append(k)

        # ── 2. Targeted fixes on axes_en / axes_fr ────────────────────────────
        fix = TARGETED_FIXES.get(ig_id)
        if fix:
            stats["targeted_fixes"] += 1
            rec: dict = {"id": ig_id}

            for field in ("canonical_name_en", "canonical_name_fr"):
                if field in fix:
                    rec[f"{field}_before"] = ig.get(field, "")
                    rec[f"{field}_after"]  = fix[field]
                    if not dry_run:
                        ig[field] = fix[field]

            if "_remove_axes_en" in fix:
                for k in fix["_remove_axes_en"]:
                    ig_axes_en.pop(k, None)
            if "_remove_axes_fr" in fix:
                for k in fix["_remove_axes_fr"]:
                    ig_axes_fr.pop(k, None)
            if "_add_axes_en" in fix:
                ig_axes_en.update(fix["_add_axes_en"])
            if "_add_axes_fr" in fix:
                ig_axes_fr.update(fix["_add_axes_fr"])
            if "_dietary_flag" in fix and not dry_run:
                ig["_dietary_flag"] = fix["_dietary_flag"]
                rec["_dietary_flag"] = fix["_dietary_flag"]

            changes.append(rec)

        # ── 3. Form axes manquants ────────────────────────────────────────────
        if ig_id in FORM_AXIS_ADDS:
            form_en, forme_fr = FORM_AXIS_ADDS[ig_id]
            if "form" not in ig_axes_en:
                ig_axes_en["form"] = form_en
                ig_axes_fr["forme"] = forme_fr
                stats["form_axes_added"] += 1

        # ── 4. Appliquer les axes splittés à l'IG ────────────────────────────
        if not dry_run:
            ig.pop("axes", None)
            ig["axes_en"] = ig_axes_en
            ig["axes_fr"] = ig_axes_fr

        # ── 5. Traitement des variants ────────────────────────────────────────
        ig_boiled = ig_axes_en.get("cooking_state") == "boiled"

        for v in ig.get("variants", []):
            stats["vars_processed"] += 1
            v_old = v.get("axes", {})
            v_axes_en, v_axes_fr = split_axes(v_old)

            # Targeted fix: retire axes indésirables des variants
            if fix:
                if "_remove_variant_axes_en" in fix:
                    for k in fix["_remove_variant_axes_en"]:
                        v_axes_en.pop(k, None)
                if "_remove_variant_axes_fr" in fix:
                    for k in fix["_remove_variant_axes_fr"]:
                        v_axes_fr.pop(k, None)

            # Fix cooking_state conflict (variant cooked → boiled quand IG=boiled)
            if ig_boiled:
                if v_axes_en.get("cooking_state") in COOKED_TO_BOILED_EN:
                    v_axes_en["cooking_state"] = "boiled"
                    stats["cooking_conflicts_fixed"] += 1
                if v_axes_fr.get("etat_cuisson") in COOKED_TO_BOILED_FR:
                    v_axes_fr["etat_cuisson"] = "bouilli"

            if not dry_run:
                v.pop("axes", None)
                v["axes_en"] = v_axes_en
                v["axes_fr"] = v_axes_fr

    return stats, changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Ne pas modifier le tree")
    parser.add_argument("--verbose", action="store_true", help="Afficher chaque changement")
    args = parser.parse_args()

    print("Chargement du tree...")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))

    print("Application des transformations...")
    stats, changes = apply_tree(tree, dry_run=args.dry_run)

    print(f"\n=== RÉSULTATS ===")
    print(f"  IGs traités              : {stats['igs_processed']}")
    print(f"  Variants traités         : {stats['vars_processed']}")
    print(f"  Conflits cuisson corrigés: {stats['cooking_conflicts_fixed']}")
    print(f"  Corrections ciblées      : {stats['targeted_fixes']}")
    print(f"  Axes form ajoutés        : {stats['form_axes_added']}")
    if stats["unknown_keys"]:
        print(f"  Clés axes inconnues      : {stats['unknown_keys']}")

    if args.verbose and changes:
        print("\n=== CORRECTIONS CIBLÉES ===")
        for c in changes:
            print(f"  [{c['id']}]")
            for k, v in c.items():
                if k != "id":
                    print(f"    {k}: {v}")

    if not args.dry_run:
        TREE_FILE.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nTree sauvegardé : {TREE_FILE}")

    # Rapport
    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "stats": {k: v for k, v in stats.items() if k != "unknown_keys"},
        "unknown_axis_keys": stats["unknown_keys"],
        "targeted_changes": changes,
    }
    report_path = OUT_DIR / "split_axes_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapport sauvegardé : {report_path}")


if __name__ == "__main__":
    main()
