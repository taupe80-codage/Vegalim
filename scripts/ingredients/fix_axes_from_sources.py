#!/usr/bin/env python3
"""
scripts/ingredients/fix_axes_from_sources.py
============================================
Corrections ciblées suite à l'audit audit_axes_vs_sources.py.
23 vraies corrections sur 52 conflits identifiés (29 faux positifs écartés).

Faux positifs écartés :
  - Lait en poudre/concentré : form=powder/concentrate intentionnel
  - Plant milks unsweetened/plain : les deux coexistent, on garde unsweetened
  - Beurres de noix plain+salted : salted est la valeur principale
  - Fromage blanc "nature, sucré" / yaourt "nature, sucré" : sweetened = principal
  - Feta crumbled : form=crumbled correct, "milk" détecté par faux-positif keyword
  - Huile de beurre concentrée : form=concentrate défendable pour beurre clarifié/ghee

Usage :
  python scripts/ingredients/fix_axes_from_sources.py --dry-run
  python scripts/ingredients/fix_axes_from_sources.py
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

EN_TO_FR_KEY = {
    "cooking_state": "etat_cuisson",
    "thermal_state": "etat_thermique",
    "form":          "forme",
    "treatment":     "traitement",
    "seasoning":     "assaisonnement",
    "draining":      "egouttage",
    "fat_content":   "teneur_MG",
    "part":          "partie",
}

EN_TO_FR_VAL = {
    "raw": "cru", "cooked": "cuit", "boiled": "bouilli", "steamed": "vapeur",
    "fried": "frit", "grilled": "grillé", "roasted": "rôti", "baked": "au four",
    "precooked": "précuit",
    "fresh": "frais", "frozen": "surgelé", "dried": "séché",
    "dehydrated": "déshydraté", "refrigerated": "réfrigéré",
    "juice": "jus", "oil": "huile", "butter": "beurre", "milk": "lait",
    "flour": "farine", "powder": "poudre", "paste": "pâte", "cream": "crème",
    "concentrate": "concentré", "pureed": "purée", "flakes": "flocons",
    "from_concentrate": "à base de concentré",
    "plain": "nature", "salted": "salé", "unsalted": "sans sel",
    "sweetened": "sucré", "unsweetened": "sans sucre",
    "drained": "égoutté", "in_oil": "à l'huile", "in_water": "dans l'eau",
    "in_brine": "en saumure",
    "skimmed": "écrémé", "semi_skimmed": "demi-écrémé", "low_fat": "allégé en gras",
}

# ──────────────────────────────────────────────────────────────────────────────
# Corrections : { id: {axes_en_key: new_val OR None (=supprime)} }
# S'applique à IGs ET variants selon quelle table contient l'id.
# ──────────────────────────────────────────────────────────────────────────────

IG_FIXES: dict[str, dict] = {
    # ── cooking_state ─────────────────────────────────────────────────────────
    # CNF:4413 "buckwheat groats, roasted, cooked"
    "ing_00251": {"cooking_state": "roasted"},
    # CIQUAL:2015 "Jus de pamplemousse, à base de concentré"  (IG level)
    "ing_01423": {"form": "juice", "treatment": "from_concentrate"},
    # CIQUAL:2014 "Jus de pomme, à base de concentré"  (IG level)
    "ing_01635": {"form": "juice", "treatment": "from_concentrate"},
    # CIQUAL:2019 "Jus de raisin, à base de concentré"  (IG level; était form=concentrate)
    "ing_01922": {"form": "juice", "treatment": "from_concentrate"},
    # CIQUAL:2000 "Jus d'ananas, à base de concentré"  (IG level; déjà form=juice, ajoute treatment)
    "ing_00901": {"form": "juice", "treatment": "from_concentrate"},
    # CNF:2459 "Squash, spaghetti, baked or boiled" → baked
    "ing_02808": {"cooking_state": "baked"},
    # CNF:2426 "Potato, mashed, flakes" → flakes (pas rolled)
    "ing_01649": {"form": "flakes"},
    # CIQUAL:13131 "Olive noire, à l'huile" → retirer draining de l'IG (milieu_conservation suffit)
    # Évite la double apparition in_oil dans la clé (milieu_conservation + egouttage)
    "ing_03236": {"draining": None},
    # CIQUAL:20256 "Tomate, séchée, à l'huile" → même raison
    "ing_03576": {"draining": None},
    # CNF:2596 "sesame butter… paste" → form=butter (tahini = beurre de sésame)
    "ing_04553": {"form": "butter"},
}

VARIANT_FIXES: dict[str, dict] = {
    # ── cooking_state variants non mis à jour lors des sessions précédentes ───
    # ing_00251 CNF:4413 buckwheat roasted
    "var_00252": {"cooking_state": "roasted"},
    # ing_00770 CIQUAL:9107 riz précuit (IG=precooked, variant=cooked)
    "var_00771": {"cooking_state": "precooked"},
    # ing_01657 CNF:1698 apple cooked/boiled (CNF quirk: starts "raw, …, cooked, boiled")
    "var_01658": {"cooking_state": "boiled"},
    # ing_02139 CIQUAL:11306 garlic roasted
    "var_02140": {"cooking_state": "roasted"},
    # ing_02164 CIQUAL:20074 artichoke steamed
    "var_02165": {"cooking_state": "steamed"},
    # ing_02325 CIQUAL:20304 broccoli steamed
    "var_02326": {"cooking_state": "steamed"},
    # ing_02652 CIQUAL:20312 cauliflower steamed
    "var_02653": {"cooking_state": "steamed"},
    # ing_02780 CIQUAL:20332 pumpkin roasted
    "var_02781": {"cooking_state": "roasted"},
    # ing_02808 CNF:2459 squash baked
    "var_02809": {"cooking_state": "baked"},

    # ── form corrections (jus "à base de concentré") ──────────────────────────
    # ing_00901 pineapple juice
    "var_00902": {"form": "juice", "treatment": "from_concentrate"},
    # ing_01402 CIQUAL:2012 "Jus d'orange, à base de concentré"
    "var_01403": {"form": "juice", "treatment": "from_concentrate"},
    # ing_01408 USDA "from concentrate"
    "var_01409": {"form": "juice", "treatment": "from_concentrate"},
    # ing_01408 USDA "not from concentrate" → juice seulement (treatment=no_pulp conservé)
    "var_01411": {"form": "juice"},
    # ing_01423 grapefruit
    "var_01424": {"form": "juice", "treatment": "from_concentrate"},
    # ing_01635 apple
    "var_01636": {"form": "juice", "treatment": "from_concentrate"},
    # ing_01922 grape juice
    "var_01923": {"form": "juice", "treatment": "from_concentrate"},

    # ── draining ──────────────────────────────────────────────────────────────
    # ing_03236 CIQUAL:13131 olive noire à l'huile
    "var_03237": {"draining": "in_oil"},
    # ing_03576 CIQUAL:20256 tomate séchée à l'huile
    "var_03577": {"draining": "in_oil"},

    # ── form autres ───────────────────────────────────────────────────────────
    # ing_01649 potato flakes
    "var_01650": {"form": "flakes"},
    # ing_04553 sesame butter
    "var_04554": {"form": "butter"},

    # ── thermal_state liste → string ──────────────────────────────────────────
    # ing_04921 var_04922 CIQUAL:19436 crème légère rayon frais
    "var_04922": {"thermal_state": "refrigerated"},
    # ing_04925 var_04926 CIQUAL:19431
    "var_04926": {"thermal_state": "refrigerated"},
    # ing_04931 var_04932 CIQUAL:19410
    "var_04932": {"thermal_state": "refrigerated"},
}


def apply_fix(obj: dict, fix: dict, label: str) -> list[str]:
    """Applique un dict de fix à un objet IG ou variant. Retourne les changements."""
    changes = []
    axes_en = obj.setdefault("axes_en", {})
    axes_fr = obj.setdefault("axes_fr", {})

    for key, val in fix.items():
        fr_key = EN_TO_FR_KEY.get(key)
        old_en = axes_en.get(key)

        if val is None:
            # Suppression
            if key in axes_en:
                del axes_en[key]
                changes.append(f"  [{label}] axes_en.{key} supprimé (était {old_en!r})")
            if fr_key and fr_key in axes_fr:
                del axes_fr[fr_key]
                changes.append(f"  [{label}] axes_fr.{fr_key} supprimé")
        else:
            # Correction — même valeur = no-op silencieux
            if old_en == val:
                continue
            axes_en[key] = val
            changes.append(f"  [{label}] axes_en.{key}: {old_en!r} → {val!r}")
            if fr_key:
                fr_val = EN_TO_FR_VAL.get(str(val), str(val))
                old_fr = axes_fr.get(fr_key)
                axes_fr[fr_key] = fr_val
                changes.append(f"  [{label}] axes_fr.{fr_key}: {old_fr!r} → {fr_val!r}")

    return changes


def walk_groups(tree: dict):
    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                yield ig


def process(tree: dict) -> list[str]:
    log = []
    ig_changed = set()
    var_changed = set()

    for ig in walk_groups(tree):
        ig_id = ig["id"]

        if ig_id in IG_FIXES:
            changes = apply_fix(ig, IG_FIXES[ig_id], ig_id)
            if changes:
                en = ig.get("canonical_name_en", "")
                log.append(f"\n[IG {ig_id}] {en}")
                log.extend(changes)
                ig_changed.add(ig_id)

        for var in ig.get("variants", []):
            var_id = var.get("id", "?")
            if var_id in VARIANT_FIXES:
                changes = apply_fix(var, VARIANT_FIXES[var_id], var_id)
                if changes:
                    src = f"{var.get('source','?')}:{var.get('source_id','?')}"
                    log.append(f"\n[VAR {var_id}] ({src})")
                    log.extend(changes)
                    var_changed.add(var_id)

    log.append(f"\n=== RÉSUMÉ ===")
    log.append(f"  IGs modifiés      : {len(ig_changed)}")
    log.append(f"  Variants modifiés : {len(var_changed)}")
    return log


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

    print(f"Application des corrections {'(DRY-RUN)' if args.dry_run else ''}...\n")
    log = process(tree_work)
    for line in log:
        print(line)

    if not args.dry_run:
        TREE_FILE.write_text(
            json.dumps(tree_work, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nTree sauvegardé : {TREE_FILE}")

    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "ig_fixes": list(IG_FIXES.keys()),
        "variant_fixes": list(VARIANT_FIXES.keys()),
        "log": log,
    }
    (OUT_DIR / "fix_axes_from_sources_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Rapport : {OUT_DIR}/fix_axes_from_sources_report.json")


if __name__ == "__main__":
    main()
