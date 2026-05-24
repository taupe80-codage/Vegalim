#!/usr/bin/env python3
"""
clean_fr_axes.py — Nettoyage des axes_fr après split_axes.py
=============================================================
Corrige les clés FR mal placées (héritage de migrate_axes.py) :
  - axes_fr.traitement=nature       → axes_fr.assaisonnement=nature
  - axes_fr.traitement=allégé*      → axes_fr.teneur_MG=allégé en gras
  - axes_fr.traitement=écrémé       → axes_fr.teneur_MG=écrémé
  - axes_fr.traitement=demi-écrémé  → axes_fr.teneur_MG=demi-écrémé
  - axes_fr.traitement=sans gluten  → supprimé (flag diète non géré par axes)
  - axes_fr.conditionnement=UHT     → axes_fr.etat_thermique=UHT
  - axes_fr.conditionnement=rayon frais → axes_fr.etat_thermique=réfrigéré
  - axes_fr.conditionnement=pasteurisé  → axes_fr.etat_thermique=pasteurisé
  - axes_fr.conditionnement=sous pression → axes_fr.etat_thermique=sous pression

Puis ajoute les clés FR manquantes en dérivant depuis axes_en.

Usage :
  python scripts/ingredients/clean_fr_axes.py --dry-run
  python scripts/ingredients/clean_fr_axes.py
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

# ── Remplacements de clés dans axes_fr ────────────────────────────────────────
# Format : (old_key, old_value_prefix) → (new_key, new_value)
# old_value_prefix=None → s'applique à toutes les valeurs de cet axe

TRAITEMENT_REMAPS: dict[str, tuple[str, str]] = {
    "nature":          ("assaisonnement", "nature"),
    "allégé en gras":  ("teneur_MG",      "allégé en gras"),
    "allégé":          ("teneur_MG",      "allégé"),
    "écrémé":          ("teneur_MG",      "écrémé"),
    "demi-écrémé":     ("teneur_MG",      "demi-écrémé"),
    "élevé en gras":   ("teneur_MG",      "élevé en gras"),
    "sans gluten":     None,   # supprimé
    "réduit en sodium": ("assaisonnement", "réduit en sodium"),  # → sodium ou seasoning
    "faible en sodium": ("assaisonnement", "faible en sodium"),
}

CONDITIONNEMENT_THERMIQUES = {
    "UHT":            ("etat_thermique", "UHT"),
    "rayon frais":    ("etat_thermique", "réfrigéré"),
    "pasteurisé":     ("etat_thermique", "pasteurisé"),
    "sous pression":  ("etat_thermique", "sous pression"),
}

# ── Dérivation EN → FR pour les clés manquantes ───────────────────────────────
EN_TO_FR_KEY: dict[str, str] = {
    "cooking_state": "etat_cuisson",
    "thermal_state": "etat_thermique",
    "form":          "forme",
    "part":          "partie",
    "treatment":     "traitement",
    "fat_content":   "teneur_MG",
    "seasoning":     "assaisonnement",
    "packaging":     "conditionnement",
    "draining":      "egouttage",
    "origin":        "origine",
    "ripeness":      "maturite",
}

EN_VAL_TO_FR: dict[str, str] = {
    # cooking_state
    "raw": "cru", "cooked": "cuit", "boiled": "bouilli", "steamed": "vapeur",
    "fried": "frit", "grilled": "grillé", "roasted": "rôti", "baked": "au four",
    "sauteed": "sauté", "braised": "braisé", "precooked": "précuit",
    "hard_boiled": "dur", "soft_boiled": "à la coque", "scrambled": "brouillé",
    # thermal_state
    "fresh": "frais", "frozen": "surgelé", "dried": "séché",
    "dehydrated": "déshydraté", "rehydrated": "réhydraté",
    "freeze_dried": "lyophilisé", "pasteurized": "pasteurisé",
    "refrigerated": "réfrigéré", "uht": "UHT",
    # form
    "juice": "jus", "oil": "huile", "milk": "lait", "butter": "beurre",
    "flour": "farine", "powder": "poudre", "paste": "pâte", "cream": "crème",
    "yogurt": "yaourt", "whole": "entier", "ground": "moulu", "extract": "extrait",
    "concentrate": "concentré", "sliced": "tranché", "grated": "râpé",
    "sauce": "sauce", "jam": "confiture", "jelly": "gelée", "compote": "compote",
    "pureed": "purée", "crushed": "broyé", "diced": "concassé", "crumbled": "émietté",
    "rolled": "flocons", "flakes": "paillettes", "granulated": "granulé",
    "block": "bloc", "tablet": "comprimé", "liquid": "liquide",
    "pieces": "petits morceaux", "crunchy": "croquant", "creamy": "crémeux",
    "whipped": "fouetté", "spice": "épice", "fresh_herb": "herbe fraîche",
    "dried_herb": "herbe séchée", "short_grain": "grain court",
    "medium_grain": "grain moyen", "long_grain": "grain long",
    "instant": "instantané", "steel_cut": "steel cut",
    "fruit_cream": "crème de fruit", "plant_water": "eau végétale",
    # part
    "leaf": "feuille", "seed": "graine", "flesh": "chair", "root": "racine",
    "stem": "tige", "peel": "pelure", "flower": "fleur", "sprout": "pousse",
    "peeled": "pelé", "pitted": "dénoyauté", "seedless": "sans graines",
    "with_seeds": "avec graines", "with_skin": "avec peau",
    "flesh_peeled": "chair sans peau", "flesh_skin": "chair+peau",
    "whole_seed": "graine entière", "tuber": "tubercule", "pod": "gousse",
    # seasoning
    "plain": "nature", "salted": "salé", "unsalted": "sans sel",
    "sweetened": "sucré", "unsweetened": "sans sucre", "flavored": "aromatisé",
    # treatment
    "smoked": "fumé", "fermented": "fermenté", "aged": "affiné",
    "refined": "raffiné", "unrefined": "brut", "sprouted": "germé",
    "dry_roasted": "grillé à sec", "oil_roasted": "grillé à l'huile",
    "blanched": "blanchi", "enriched": "enrichi", "iodized": "iodé",
    "hulled": "décortiqué", "parboiled": "étuvé", "distilled": "distillé",
    "virgin": "vierge", "extra_virgin": "extra vierge",
    "cold_pressed": "pression à froid", "textured": "texturé",
    "decaffeinated": "décaféiné", "marinated": "mariné", "pickled": "lacto-fermenté",
    "toasted": "grillé", "fat_added": "gras ajouté", "candied": "confit",
    # packaging
    "canned": "conserve", "vacuum": "sous vide", "prepackaged": "préemballé",
    "commercial": "commercial",
    # draining
    "drained": "égoutté", "in_oil": "à l'huile", "in_water": "dans l'eau",
    "in_brine": "en saumure", "in_syrup": "dans sirop", "in_vinegar": "au vinaigre",
    # fat_content
    "skimmed": "écrémé", "semi_skimmed": "demi-écrémé", "low_fat": "allégé en gras",
    "light": "allégé", "whole": "entier", "fat_free": "sans matières grasses",
    # origin
    "plant": "végétal", "cow": "vache", "goat": "chèvre", "sheep": "brebis",
    # ripeness
    "ripe": "mûr", "unripe": "pas mûr",
}


def walk_groups(tree: dict):
    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                yield ig


def fix_axes_fr(axes_fr: dict) -> tuple[dict, list[str]]:
    """Corrige les clés mal placées dans axes_fr. Retourne (new_axes_fr, changes)."""
    new_fr = dict(axes_fr)
    changes = []

    # Fix traitement mismatches
    if "traitement" in new_fr:
        v = new_fr["traitement"]
        v_str = str(v) if not isinstance(v, list) else None
        if v_str and v_str in TRAITEMENT_REMAPS:
            remap = TRAITEMENT_REMAPS[v_str]
            del new_fr["traitement"]
            if remap is not None:
                new_key, new_val = remap
                if new_key not in new_fr:
                    new_fr[new_key] = new_val
                    changes.append(f"traitement={v!r} → {new_key}={new_val!r}")
                else:
                    changes.append(f"traitement={v!r} supprimé (conflit {new_key} existe déjà)")
            else:
                changes.append(f"traitement={v!r} supprimé (flag diète)")

    # Fix conditionnement that belong in etat_thermique
    if "conditionnement" in new_fr:
        v = new_fr["conditionnement"]
        v_str = str(v)
        if v_str in CONDITIONNEMENT_THERMIQUES:
            new_key, new_val = CONDITIONNEMENT_THERMIQUES[v_str]
            del new_fr["conditionnement"]
            if new_key not in new_fr:
                new_fr[new_key] = new_val
                changes.append(f"conditionnement={v!r} → {new_key}={new_val!r}")
            else:
                changes.append(f"conditionnement={v!r} supprimé (conflit {new_key} existe déjà)")

    return new_fr, changes


def add_missing_fr(axes_en: dict, axes_fr: dict) -> tuple[dict, list[str]]:
    """Ajoute dans axes_fr les clés manquantes dérivées de axes_en."""
    new_fr = dict(axes_fr)
    changes = []

    for en_key, en_val in axes_en.items():
        fr_key = EN_TO_FR_KEY.get(en_key)
        if not fr_key:
            continue
        if fr_key in new_fr:
            continue  # déjà présent
        # Dériver la valeur FR
        fr_val = EN_VAL_TO_FR.get(str(en_val), str(en_val))
        new_fr[fr_key] = fr_val
        changes.append(f"+ axes_fr.{fr_key}={fr_val!r} (depuis axes_en.{en_key}={en_val!r})")

    return new_fr, changes


def process(tree: dict, dry_run: bool) -> dict:
    stats = {"igs": 0, "vars": 0, "fr_remaps": 0, "fr_adds": 0}
    all_changes = []

    def apply_to(obj: dict, label: str) -> list[str]:
        changes = []
        axes_en = obj.get("axes_en", {})
        axes_fr = obj.get("axes_fr", {})

        new_fr, fix_changes = fix_axes_fr(axes_fr)
        new_fr, add_changes = add_missing_fr(axes_en, new_fr)

        all_c = fix_changes + add_changes
        if all_c and not dry_run:
            obj["axes_fr"] = new_fr
        changes.extend(all_c)
        return fix_changes, add_changes

    for ig in walk_groups(tree):
        stats["igs"] += 1
        fixes, adds = apply_to(ig, ig["id"])
        if fixes or adds:
            all_changes.append({"id": ig["id"], "fixes": fixes, "adds": adds})
            stats["fr_remaps"] += len(fixes)
            stats["fr_adds"] += len(adds)

        for v in ig.get("variants", []):
            stats["vars"] += 1
            v_fixes, v_adds = apply_to(v, v.get("id", "?"))
            stats["fr_remaps"] += len(v_fixes)
            stats["fr_adds"] += len(v_adds)

    return stats, all_changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("Chargement du tree...")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))

    stats, changes = process(tree, dry_run=args.dry_run)

    print(f"\n=== RÉSULTATS ===")
    print(f"  IGs traités         : {stats['igs']}")
    print(f"  Variants traités    : {stats['vars']}")
    print(f"  Clés FR remplacées  : {stats['fr_remaps']}")
    print(f"  Clés FR ajoutées    : {stats['fr_adds']}")

    if args.verbose and changes:
        print("\n=== DÉTAIL (50 premiers IGs) ===")
        for c in changes[:50]:
            print(f"  [{c['id']}]")
            for f in c["fixes"]:
                print(f"    FIX: {f}")
            for a in c["adds"]:
                print(f"    ADD: {a}")

    if not args.dry_run:
        TREE_FILE.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nTree sauvegardé : {TREE_FILE}")

    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "stats": stats,
        "changes": changes,
    }
    (OUT_DIR / "clean_fr_axes_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Rapport sauvegardé : {OUT_DIR}/clean_fr_axes_report.json")


if __name__ == "__main__":
    main()
