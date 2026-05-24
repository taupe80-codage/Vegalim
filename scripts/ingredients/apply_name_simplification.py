#!/usr/bin/env python3
"""
scripts/ingredients/apply_name_simplification.py
=================================================
Simplifie les canonical_name_en et canonical_name_fr des ingredient_groups
du tree en retirant les qualificateurs redondants avec les axes déjà présents.

Règle : un qualificateur post-virgule est retiré du nom si et seulement si
l'axe correspondant EST déjà présent dans le groupe (après migrate_axes.py).

Exemples :
  "egg yolk, raw"         + axes:{cooking_state:raw}    → "egg yolk"
  "bulgur wheat, cooked"  + axes:{cooking_state:cooked} → "bulgur wheat"
  "cocoa powder, unsweetened" + axes:{seasoning:unsweetened} → "cocoa powder"
  "olive oil, extra virgin"   + axes:{treatment:extra_virgin} → "olive oil"

Usage :
  python scripts/ingredients/apply_name_simplification.py --dry-run
  python scripts/ingredients/apply_name_simplification.py
"""

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT      = Path(__file__).resolve().parents[2]
TREE_FILE = ROOT / "backend/data/ingredients/ingredients_tree.json"
OUT_DIR   = ROOT / "scripts/ingredients"

# ── Axes EN pour lesquels on auto-supprime les qualificateurs redondants ──────

EN_AXIS_TYPES = {
    "cooking_state", "thermal_state", "form", "fat_content",
    "seasoning", "treatment", "packaging", "draining",
    "ripeness", "color", "size", "variety", "ripening", "sodium",
}

# ── Mapping qualificateur normalisé → axis_type ───────────────────────────────
# Les clés multi-mots sont testées EN PREMIER (ordre décroissant de longueur).

QUALIFIER_MAP: dict[str, str] = {
    # cooking_state
    "raw":           "cooking_state",
    "cooked":        "cooking_state",
    "boiled":        "cooking_state",
    "hard boiled":   "cooking_state",
    "soft boiled":   "cooking_state",
    "steamed":       "cooking_state",
    "fried":         "cooking_state",
    "deep fried":    "cooking_state",
    "pan fried":     "cooking_state",
    "stir fried":    "cooking_state",
    "roasted":       "cooking_state",
    "baked":         "cooking_state",
    "grilled":       "cooking_state",
    "braised":       "cooking_state",
    "poached":       "cooking_state",
    "scrambled":     "cooking_state",
    "microwaved":    "cooking_state",
    "precooked":     "cooking_state",
    "uncooked":      "cooking_state",
    # thermal_state
    "fresh":         "thermal_state",
    "dried":         "thermal_state",
    "dry":           "thermal_state",
    "dehydrated":    "thermal_state",
    "freeze dried":  "thermal_state",
    "frozen":        "thermal_state",
    "pasteurized":   "thermal_state",
    "sterilized":    "thermal_state",
    "refrigerated":  "thermal_state",
    "rehydrated":    "thermal_state",
    # form
    "powder":        "form",
    "powdered":      "form",
    "flour":         "form",
    "flakes":        "form",
    "sliced":        "form",
    "diced":         "form",
    "chopped":       "form",
    "pureed":        "form",
    "ground":        "form",
    "grated":        "form",
    "crushed":       "form",
    "minced":        "form",
    "rolled":        "form",
    "spray dried":   "form",
    "instant":       "form",
    # fat_content
    "fat free":      "fat_content",
    "full fat":      "fat_content",
    "low fat":       "fat_content",
    "reduced fat":   "fat_content",
    "semi skimmed":  "fat_content",
    "skimmed":       "fat_content",
    "skim":          "fat_content",
    # packaging
    "canned":        "packaging",
    "jarred":        "packaging",
    "vacuum":        "packaging",
    "prepackaged":   "packaging",
    # draining
    "drained and rinsed": "draining",
    "drained":       "draining",
    "in oil":        "draining",
    "in water":      "draining",
    "in brine":      "draining",
    "in syrup":      "draining",
    "in vinegar":    "draining",
    # seasoning
    "unsalted":      "seasoning",
    "salted":        "seasoning",
    "sweetened":     "seasoning",
    "unsweetened":   "seasoning",
    "plain":         "seasoning",
    "flavored":      "seasoning",
    # treatment
    "extra virgin":  "treatment",
    "cold pressed":  "treatment",
    "dry roasted":   "treatment",
    "oil roasted":   "treatment",
    "smoked":        "treatment",
    "fermented":     "treatment",
    "blanched":      "treatment",
    "enriched":      "treatment",
    "fortified":     "treatment",
    "iodized":       "treatment",
    "refined":       "treatment",
    "unrefined":     "treatment",
    "marinated":     "treatment",
    "pickled":       "treatment",
    "toasted":       "treatment",
    "virgin":        "treatment",
    "distilled":     "treatment",
    "aged":          "treatment",
    "parboiled":     "treatment",
    "sprouted":      "treatment",
    "hulled":        "treatment",
    "textured":      "treatment",
    # sodium
    "low sodium":    "sodium",
    "reduced sodium": "sodium",
    "no salt added": "sodium",
    "sodium free":   "sodium",
    # ripeness
    "ripe":          "ripeness",
    "unripe":        "ripeness",
    "sun dried":     "ripeness",
    # FR equivalents (mêmes clés utilisées pour canonical_name_fr)
    "cru":           "cooking_state",
    "crue":          "cooking_state",
    "cuit":          "cooking_state",
    "cuite":         "cooking_state",
    "bouilli":       "cooking_state",
    "bouillie":      "cooking_state",
    "vapeur":        "cooking_state",
    "frit":          "cooking_state",
    "frite":         "cooking_state",
    "grille":        "cooking_state",
    "au four":       "cooking_state",
    "saute":         "cooking_state",
    "braise":        "cooking_state",
    "precuit":       "cooking_state",
    "precuite":      "cooking_state",
    "frais":         "thermal_state",
    "fraiche":       "thermal_state",
    "seche":         "thermal_state",
    "sechee":        "thermal_state",
    "deshydrate":    "thermal_state",
    "dehydrate":     "thermal_state",
    "surgele":       "thermal_state",
    "congele":       "thermal_state",
    "pasteurise":    "thermal_state",
    "rehydrate":     "thermal_state",
    "poudre":        "form",
    "farine":        "form",
    "flocons":       "form",
    "tranche":       "form",
    "tranchee":      "form",
    "hache":         "form",
    "rape":          "form",
    "ecreme":        "fat_content",
    "demi ecreme":   "fat_content",
    "sale":          "seasoning",
    "non sale":      "seasoning",
    "sucre":         "seasoning",
    "nature":        "seasoning",
    "fume":          "treatment",
    "fermente":      "treatment",
    "blanchie":      "treatment",
    "enrichi":       "treatment",
    "raffine":       "treatment",
    "marine":        "treatment",
    "grille a sec":  "treatment",
    "extra vierge":  "treatment",
    "pression a froid": "treatment",
    "etuve":         "treatment",
    "iode":          "treatment",
    "egoutte":       "draining",
    "en conserve":   "packaging",
    "sous vide":     "packaging",
    "mur":           "ripeness",
    "mure":          "ripeness",
}

# Clés multi-mots triées par longueur décroissante pour priorité de matching
MULTI_WORD_KEYS = sorted(
    [k for k in QUALIFIER_MAP if " " in k],
    key=lambda k: len(k.split()),
    reverse=True,
)


def _norm(s: str) -> str:
    """Normalise : minuscules, sans accents, remplace non-alphanum par espace."""
    s = unicodedata.normalize("NFD", s.lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def _match_qualifier(segment: str) -> str | None:
    """Retourne l'axis_type si le segment normalisé est dans QUALIFIER_MAP."""
    sn = _norm(segment)
    # D'abord les multi-mots (plus précis)
    for mk in MULTI_WORD_KEYS:
        if sn == mk or sn.startswith(mk + " ") or sn.endswith(" " + mk):
            if mk in QUALIFIER_MAP:
                return QUALIFIER_MAP[mk]
    # Puis les mots simples
    return QUALIFIER_MAP.get(sn)


def simplify_name(name: str, axes: dict) -> str:
    """
    Retire de 'name' les segments post-virgule dont l'axis_type est dans 'axes'.
    Le premier segment (base) n'est jamais modifié.
    Les parenthèses de synonymes sont conservées sur le premier segment uniquement.
    """
    if "," not in name:
        return name

    # Identifie les EN axis types présents sur ce groupe
    present_en_axes = {k for k in axes if k in EN_AXIS_TYPES}
    if not present_en_axes:
        return name

    parts = [p.strip() for p in name.split(",")]
    base = parts[0]
    qualifiers = parts[1:]

    kept = []
    for q in qualifiers:
        at = _match_qualifier(q)
        if at and at in present_en_axes:
            continue  # qualificateur redondant : on le retire
        kept.append(q)

    if len(kept) == len(qualifiers):
        return name  # rien supprimé

    if kept:
        return base + ", " + ", ".join(kept)
    return base


def walk_groups(tree: dict):
    """Générateur sur tous les ingredient_groups du tree."""
    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                yield ig


def apply_simplification(tree: dict, dry_run: bool, verbose: bool) -> dict:
    stats = {"groups_changed": 0, "en_changed": 0, "fr_changed": 0}
    changes = []

    for ig in walk_groups(tree):
        axes = ig.get("axes_en") or ig.get("axes") or {}
        orig_en = ig.get("canonical_name_en", "")
        orig_fr = ig.get("canonical_name_fr", "")

        new_en = simplify_name(orig_en, axes)
        new_fr = simplify_name(orig_fr, axes)

        changed = False
        rec = {"id": ig["id"], "en_before": orig_en, "fr_before": orig_fr}

        if new_en != orig_en:
            if not dry_run:
                ig["canonical_name_en"] = new_en
            rec["en_after"] = new_en
            stats["en_changed"] += 1
            changed = True
            if verbose:
                print(f"  EN [{ig['id']}]: '{orig_en}' -> '{new_en}'")

        if new_fr != orig_fr:
            if not dry_run:
                ig["canonical_name_fr"] = new_fr
            rec["fr_after"] = new_fr
            stats["fr_changed"] += 1
            changed = True
            if verbose:
                print(f"  FR [{ig['id']}]: '{orig_fr}' -> '{new_fr}'")

        if changed:
            stats["groups_changed"] += 1
            changes.append(rec)

    return stats, changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Ne pas modifier le tree")
    parser.add_argument("--verbose", action="store_true", help="Afficher chaque modification")
    args = parser.parse_args()

    print("Chargement du tree...")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))

    print("Simplification des noms...")
    stats, changes = apply_simplification(tree, dry_run=args.dry_run, verbose=args.verbose)

    print(f"\nResultats :")
    print(f"  Groupes modifies     : {stats['groups_changed']}")
    print(f"  Noms EN simplifies   : {stats['en_changed']}")
    print(f"  Noms FR simplifies   : {stats['fr_changed']}")

    if not args.dry_run:
        TREE_FILE.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nTree sauvegarde : {TREE_FILE}")

    # Rapport
    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "stats": stats,
        "changes": changes,
    }
    report_path = OUT_DIR / "apply_name_simplification_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapport sauve : {report_path}")

    # Afficher un echantillon
    if changes:
        print("\nEchantillon de modifications (10 premiers) :")
        for c in changes[:10]:
            if "en_after" in c:
                print(f"  EN {c['id']}: '{c['en_before']}' -> '{c['en_after']}'")
            if "fr_after" in c:
                print(f"  FR {c['id']}: '{c['fr_before']}' -> '{c['fr_after']}'")


if __name__ == "__main__":
    main()
