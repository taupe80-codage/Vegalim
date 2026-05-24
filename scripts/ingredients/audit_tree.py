#!/usr/bin/env python3
"""
scripts/ingredients/audit_tree.py
==================================
Audit complet du ingredients_tree.json — vérifie chaque IG pour des erreurs
de noms, axes, variants, doublons et incohérences.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT      = Path(__file__).resolve().parents[2]
TREE_FILE = ROOT / "backend/data/ingredients/ingredients_tree.json"
OUT_FILE  = ROOT / "scripts/ingredients/audit_tree_report.json"

FORM_SUFFIXES_EN = [" flour", " oil", " butter", " milk", " yogurt",
                    " juice", " extract", " paste", " sauce", " cream", " powder"]
FORM_PREFIXES_FR = [
    "farine de ", "farine d'", "farine d’",
    "huile de ", "huile d'", "huile d’",
    "beurre de ", "beurre d'", "beurre d’",
    "lait de ", "lait d'", "lait d’",
    "yaourt de ", "yaourt d'", "yaourt d’",
    "jus de ", "jus d'", "jus d’",
    "extrait de ", "extrait d'",
    "pâte de ", "pâte d'",
]

INVERSION_NOUNS = [
    "mushroom", "mushrooms", "rice", "cabbage", "lettuce",
    "tomato", "tomatoes", "apple", "apples", "mango", "mangoes",
    "pear", "pears", "onion", "onions", "radish", "radishes",
    "squash", "potato", "potatoes", "peas", "pepper", "peppers",
    "peanut", "peanuts",
]

ANIMAL_KEYWORDS = {
    "beef", "pork", "chicken", "lamb", "veal", "duck", "turkey",
    "salmon", "tuna", "cod", "fish", "shrimp", "prawn", "lobster",
    "crab", "oyster", "scallop", "mussel", "lard", "suet",
    "gelatin", "gelatine", "anchovy", "sardine", "mackerel",
    "herring", "trout", "bacon", "ham", "sausage",
}


def has_comma_outside_parens(s: str) -> bool:
    depth = 0
    for c in s:
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif c == "," and depth == 0:
            return True
    return False


def audit_tree(tree: dict) -> list[dict]:
    issues = []
    seen_en: dict[str, str] = {}
    seen_source_ids: dict[str, bool] = {}

    ig_count = 0
    for cat in tree.get("categories", []):
        cat_label = cat.get("label", "")
        for sub in cat.get("subcategories", []):
            sub_label = sub.get("label", "")
            for ig in sub.get("ingredient_groups", []):
                ig_count += 1
                ig_id   = ig["id"]
                en      = ig.get("canonical_name_en", "")
                fr      = ig.get("canonical_name_fr", "")
                axes_en = ig.get("axes_en") or ig.get("axes") or {}
                axes_fr = ig.get("axes_fr") or {}
                axes    = {**axes_fr, **axes_en}  # merged view for legacy checks
                variants = ig.get("variants", [])
                form_axis = axes_en.get("form")

                def add(cat_name: str, msg: str):
                    issues.append({
                        "category": cat_name,
                        "id": ig_id,
                        "en": en,
                        "fr": fr,
                        "msg": msg,
                    })

                # ── 1. Noms manquants ──────────────────────────────────────
                if not en:
                    add("MISSING_NAME", "canonical_name_en absent")
                if not fr:
                    add("MISSING_NAME", "canonical_name_fr absent")

                # ── 2. EN avec virgule → inversion ratée ──────────────────
                en_l = en.lower()
                for noun in INVERSION_NOUNS:
                    if en_l.startswith(noun + ", ") or en_l.startswith(noun + "s, "):
                        add("EN_INVERSION_MISSED", f'"{en}"')
                        break

                # ── 3. FR avec virgule hors parenthèses ───────────────────
                if fr and has_comma_outside_parens(fr):
                    add("FR_COMMA_REMAINING", f'"{fr[:70]}"')

                # ── 4. EN suffixe form non retiré + axe form présent ──────
                for suf in FORM_SUFFIXES_EN:
                    if en_l.endswith(suf):
                        if form_axis:
                            add("EN_FORM_NOT_STRIPPED",
                                f'"{en}" (form:{form_axis})')
                        else:
                            add("FORM_AXIS_MISSING",
                                f'"{en}" n\'a pas d\'axe form')
                        break

                # ── 5. FR préfixe form non retiré + axe form présent ──────
                fr_l = fr.lower()
                for pref in FORM_PREFIXES_FR:
                    if fr_l.startswith(pref):
                        if form_axis:
                            add("FR_FORM_NOT_STRIPPED",
                                f'"{fr[:60]}" (form:{form_axis})')
                        else:
                            add("FORM_AXIS_MISSING_FR",
                                f'"{fr[:60]}" n\'a pas d\'axe form')
                        break

                # ── 6. Ingrédients animaux (projet 100% végétarien) ───────
                en_words = set(re.split(r"[ ,_\-/()+]+", en_l))
                if en_words & ANIMAL_KEYWORDS:
                    add("ANIMAL_INGREDIENT", f'"{en}"')

                # ── 7. Doublons canonical_name_en ─────────────────────────
                key_en = en.lower().strip()
                if key_en and key_en in seen_en:
                    add("DUPLICATE_EN",
                        f'même nom EN que {seen_en[key_en]}: "{en}"')
                else:
                    if key_en:
                        seen_en[key_en] = ig_id

                # ── 8. IG sans variants ───────────────────────────────────
                if not variants:
                    add("NO_VARIANTS", "IG sans aucun variant")

                # ── 9. Variants sans source_id ────────────────────────────
                for v in variants:
                    if not v.get("source_id"):
                        add("VARIANT_NO_SOURCE_ID",
                            f'variant {v.get("id","?")} sans source_id')


                # ── 10. Doublons source_id dans variants ──────────────────
                vids = [
                    f"{v.get('source','?')}:{v.get('source_id','')}"
                    for v in variants
                    if v.get("source_id")
                ]
                duplicated = {vid for vid in vids if vids.count(vid) > 1}
                if duplicated and ig_id not in seen_source_ids:
                    add("DUPLICATE_SOURCE_ID_VARIANT",
                        f"source_ids dupliqués: {duplicated}")
                    seen_source_ids[ig_id] = True

                # ── 11. cooking_state boiled vs cooked conflict ───────────
                ig_cooking = axes_en.get("cooking_state") or axes_fr.get("etat_cuisson")
                if ig_cooking in ("boiled", "cooked"):
                    for v in variants:
                        v_ax_en = v.get("axes_en") or v.get("axes") or {}
                        v_cooking = v_ax_en.get("cooking_state")
                        if v_cooking and v_cooking != ig_cooking and \
                                {v_cooking, ig_cooking} <= {"boiled", "cooked"}:
                            add("COOKING_STATE_CONFLICT",
                                f"IG={ig_cooking} vs variant {v.get('id','?')}={v_cooking}")

                # ── 12. Axe form incohérent avec nom ─────────────────────
                if form_axis:
                    form_map = {
                        "flour": "flour", "oil": "oil", "butter": "butter",
                        "milk": "milk", "yogurt": "yogurt", "juice": "juice",
                        "extract": "extract", "paste": "paste",
                    }
                    expected_suffix = form_map.get(form_axis)
                    if expected_suffix and en_l.endswith(f" {expected_suffix}"):
                        add("FORM_AXIS_IN_NAME",
                            f'"{en}" contient "{expected_suffix}" mais axe form={form_axis}')

                # ── 13. Axes EN sans contrepartie FR (info seulement) ─────
                AXIS_FR_MAP = {
                    "cooking_state": "etat_cuisson",
                    "thermal_state": "etat_thermique",
                    "form":          "forme",
                    "seasoning":     "assaisonnement",
                    "treatment":     "traitement",
                    "packaging":     "conditionnement",
                    "draining":      "egouttage",
                    "part":          "partie",
                }
                for en_key, fr_key in AXIS_FR_MAP.items():
                    en_val = axes_en.get(en_key)
                    fr_val = axes_fr.get(fr_key)
                    if en_val and not fr_val:
                        add("AXIS_MISSING_FR_KEY",
                            f"axe_en {en_key}={en_val} sans axes_fr.{fr_key}")
                    elif fr_val and not en_val:
                        add("AXIS_MISSING_EN_KEY",
                            f"axes_fr {fr_key}={fr_val} sans axes_en.{en_key}")

    return issues, ig_count


def main():
    print("Chargement du tree...")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))

    print("Audit en cours...")
    issues, ig_count = audit_tree(tree)

    cats = Counter(i["category"] for i in issues)

    print(f"\n=== AUDIT RÉSUMÉ ({ig_count} IGs) ===")
    for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"  {cat:40s}: {n:4d}")
    print(f"  {'TOTAL':40s}: {len(issues):4d}")

    # Détail par catégorie (limité à 15 exemples par cat)
    print("\n=== DÉTAIL ===")
    by_cat: dict[str, list] = {}
    for issue in issues:
        by_cat.setdefault(issue["category"], []).append(issue)

    for cat_name, cat_issues in sorted(by_cat.items(), key=lambda x: -len(x[1])):
        if len(cat_issues) == 0:
            continue
        print(f"\n{cat_name} ({len(cat_issues)}) :")
        for issue in cat_issues[:12]:
            print(f"  [{issue['id']}] {issue['msg']}")
        if len(cat_issues) > 12:
            print(f"  ... et {len(cat_issues) - 12} autres")

    report = {
        "summary": dict(cats),
        "total_issues": len(issues),
        "ig_count": ig_count,
        "issues": issues,
    }
    OUT_FILE.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nRapport sauvé : {OUT_FILE}")


if __name__ == "__main__":
    main()
