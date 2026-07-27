#!/usr/bin/env python3
"""
scripts/ingredients/audit_axes_coherence.py
============================================
Audit de cohérence INTERNE du tree — différent de audit_axes_vs_sources.py
(qui compare contre les descriptions officielles) et de audit_tree.py
(qui vérifie la structure formelle).

3 types de vérifications :

A. COHÉRENCE EN ↔ FR
   Pour chaque IG/variant : axes_en.key=val doit correspondre à
   axes_fr.fr_key=fr_val via les tables de traduction connues.
   Détecte les désynchronisations introduites par des scripts partiels.

B. COHÉRENCE NOM ↔ AXES (reverse check)
   Le canonical_name_en contient des tokens qui impliquent un axe.
   Ex : "boiled" dans le nom → axes_en.cooking_state devrait = "boiled".
   Ex : "canned" dans le nom → axes_en.packaging devrait = "canned".
   Si l'axe est absent ou différent → signal.

C. OUTLIERS INTRA-SOUS-CATÉGORIE
   Dans chaque sous-catégorie, calculer la distribution des valeurs
   d'axes. Un IG avec une valeur qui n'apparaît qu'une seule fois
   dans sa sous-catégorie est suspect (potentielle erreur de classement).

Usage :
  python scripts/ingredients/audit_axes_coherence.py [--verbose]
"""

import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT      = Path(__file__).resolve().parents[2]
TREE_FILE = ROOT / "backend/data/ingredients/ingredients_tree.json"
OUT_FILE  = ROOT / "scripts/ingredients/audit_axes_coherence_report.json"

# ── Tables de traduction attendues ─────────────────────────────────────────────

# axes_en_key → axes_fr_key
EN_KEY_TO_FR_KEY = {
    "cooking_state": "etat_cuisson",
    "thermal_state": "etat_thermique",
    "form":          "forme",
    "treatment":     "traitement",
    "cooking_process":"procede_cuisson",
    "fat_content":   "teneur_MG",
    "seasoning":     "assaisonnement",
    "packaging":     "conditionnement",
    "draining":      "egouttage",
    "part":          "partie",
    "origin":        "origine",
    "ripeness":      "maturite",
}

# Valeurs FR alternatives tolérées en plus de la valeur "attendue" par défaut
# (synonymes légitimes déjà utilisés de façon cohérente ailleurs dans le tree,
# ou variations d'accord grammatical FR selon le genre du nom canonique).
EN_VAL_TO_FR_VAL_ALTERNATES: dict[str, dict[str, set[str]]] = {
    "packaging": {"canned": {"appertisé"}},   # synonyme de "conserve"
    "ripeness":  {"ripe": {"mûre"}},           # accord féminin (ex. tomate mûre)
    "form": {
        # "flocons" (flocons roulés type avoine/pomme de terre) et "paillettes"
        # (paillettes séchées type céleri/levure) sont deux traductions
        # valides de "flakes" selon le produit — pas de règle universelle.
        "flakes": {"flocons"},
        "crushed": {"concassée"},   # accord féminin (ex. tomate concassée)
    },
    "treatment": {
        # "torréfié" reste valide pour un fruit à coque/graine même quand
        # cooking_process est renseigné, si cooking_state=roasted porte déjà
        # l'information "rôti" séparément (double encodage volontaire).
        "roasted": {"torréfié"},
    },
}

# axes_en.value → axes_fr.value attendue — mapping PAR AXE (évite les clés dupliquées)
# Règle clé : cooking_state.roasted="rôti" (légumes/viandes)
#             treatment.roasted="torréfié" (noix/graines/café)
#             treatment.toasted="grillé"   (torréfaction légère, amandes/graines)
EN_VAL_TO_FR_VAL_BY_AXIS: dict[str, dict[str, str]] = {
    "cooking_state": {
        "raw": "cru", "cooked": "cuit", "boiled": "bouilli", "steamed": "vapeur",
        "fried": "frit", "grilled": "grillé", "roasted": "rôti", "baked": "au four",
        "sauteed": "sauté", "braised": "étouffée", "precooked": "précuit",
        "hard_boiled": "dur", "soft_boiled": "à la coque", "scrambled": "brouillé",
        "stewed": "étuvée",
    },
    "thermal_state": {
        "fresh": "frais", "frozen": "surgelé", "dried": "séché",
        "dehydrated": "déshydraté", "rehydrated": "réhydraté",
        "freeze_dried": "lyophilisé", "pasteurized": "pasteurisé",
        "refrigerated": "réfrigéré", "uht": "UHT",
    },
    "form": {
        "juice": "jus", "oil": "huile", "butter": "beurre", "milk": "lait",
        "flour": "farine", "powder": "poudre", "paste": "pâte", "cream": "crème",
        "yogurt": "yaourt", "whole": "entier", "ground": "moulu", "extract": "extrait",
        "concentrate": "concentré", "sliced": "tranché", "grated": "râpé",
        "sauce": "sauce", "jam": "confiture", "jelly": "gelée", "compote": "compote",
        "pureed": "purée", "crushed": "concassé", "cracked": "concassé",
        "diced": "en dés", "crumbled": "émietté",
        "rolled": "flocons", "flakes": "paillettes", "granulated": "granulé",
        "block": "bloc", "liquid": "liquide", "pieces": "petits morceaux",
        "crunchy": "croquant", "creamy": "crémeux", "whipped": "fouetté",
    },
    "part": {
        "leaf": "feuille", "seed": "graine", "flesh": "chair", "root": "racine",
        "stem": "tige", "peel": "pelure", "flower": "fleur", "sprout": "pousse",
        "peeled": "pelé", "pitted": "dénoyauté", "seedless": "sans graines",
        "with_seeds": "avec graines", "with_skin": "avec peau",
        "tuber": "tubercule", "pod": "gousse",
    },
    "seasoning": {
        "plain": "nature", "salted": "salé", "unsalted": "sans sel",
        "sweetened": "sucré", "unsweetened": "sans sucre", "flavored": "aromatisé",
    },
    "treatment": {
        "smoked": "fumé", "fermented": "fermenté", "aged": "affiné",
        "refined": "raffiné", "unrefined": "brut", "sprouted": "germé",
        # "roasted" est géré par la logique context-aware dans check_en_fr_coherence :
        #   avec cooking_method → rôti  |  sans cooking_method → torréfié
        "blanched": "blanchi", "enriched": "enrichi", "iodized": "iodé",
        "hulled": "décortiqué", "parboiled": "étuvé", "virgin": "vierge",
        "extra_virgin": "extra vierge", "cold_pressed": "pression à froid",
        "textured": "texturé", "decaffeinated": "décaféiné", "marinated": "mariné",
        "pickled": "lacto-fermenté", "toasted": "grillé", "candied": "confit",
        "unblanched": "non blanchi", "unbleached": "non blanchi",
        "from_concentrate": "à base de concentré",
    },
    "packaging": {
        "canned": "conserve", "vacuum": "sous vide", "prepackaged": "préemballé",
        "commercial": "commercial",
    },
    "fat_content": {
        "skimmed": "écrémé", "semi_skimmed": "demi-écrémé", "low_fat": "allégé",
        "light": "allégé", "fat_free": "sans MG", "high_fat": "élevé en gras",
        "medium_fat": "teneur moyenne en MG", "full_fat": "entier",
    },
    "origin": {
        "plant": "végétal", "cow": "vache", "goat": "chèvre", "sheep": "brebis",
    },
    "ripeness": {
        "ripe": "mûr", "unripe": "pas mûr",
    },
    "cooking_process": {
        "dry":    "à sec",
        "in_oil": "à l'huile",
    },
}

# Tokens dans le nom EN → axe attendu (pour B)
NAME_TOKEN_TO_AXIS: list[tuple[str, str, str]] = [
    # (token_regex, axes_en_key, axes_en_value_expected)
    # cooking_state
    (r"\braw\b",       "cooking_state", "raw"),
    (r"\bboiled\b",    "cooking_state", "boiled"),
    (r"\bsteamed\b",   "cooking_state", "steamed"),
    (r"\broasted\b",   "cooking_state", "roasted"),
    (r"\bbaked\b",     "cooking_state", "baked"),
    (r"\bfried\b",     "cooking_state", "fried"),
    (r"\bgrilled\b",   "cooking_state", "grilled"),
    (r"\bprecooked\b", "cooking_state", "precooked"),
    (r"\bcooked\b",    "cooking_state", "cooked"),
    # thermal_state
    (r"\bfrozen\b",    "thermal_state", "frozen"),
    (r"\bdried\b",     "thermal_state", "dried"),
    (r"\bdehydrated\b","thermal_state", "dehydrated"),
    # form
    (r"\bjuice\b",     "form", "juice"),
    (r"\bflour\b",     "form", "flour"),
    (r"\boil\b(?! roasted| pressed)", "form", "oil"),
    (r"\bmilk\b",      "form", "milk"),
    (r"\bpowder\b",    "form", "powder"),
    (r"\bpaste\b",     "form", "paste"),
    (r"\bbutler\b",    "form", "butter"),   # intentional typo guard
    # packaging
    (r"\bcanned\b",    "packaging", "canned"),
    # draining
    (r"\bdrained\b",   "draining", "drained"),
    (r"\bin.oil\b",    "draining", "in_oil"),
    (r"\bin.brine\b",  "draining", "in_brine"),
    # seasoning
    (r"\bsalted\b",    "seasoning", "salted"),
    (r"\bunsalted\b",  "seasoning", "unsalted"),
    (r"\bsweetened\b", "seasoning", "sweetened"),
    (r"\bunsweetened\b","seasoning","unsweetened"),
    # fat_content
    (r"\bskim(?:med)?\b", "fat_content", "skimmed"),
    (r"\bwhole[ -]milk\b","fat_content", "whole"),
]

# Axes à vérifier pour outliers intra-sous-catégorie
AXES_FOR_OUTLIER = ["cooking_state", "thermal_state", "form", "seasoning", "packaging"]


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# ═══════════════════════════════════════════════════════════════════════════════
# A. COHÉRENCE EN ↔ FR
# ═══════════════════════════════════════════════════════════════════════════════

def check_en_fr_coherence(ig_id: str, en_name: str, axes_en: dict, axes_fr: dict) -> list[dict]:
    issues = []
    for en_key, fr_key in EN_KEY_TO_FR_KEY.items():
        en_val = axes_en.get(en_key)
        fr_val = axes_fr.get(fr_key)
        if en_val is None and fr_val is None:
            continue
        if en_val is not None and fr_val is None:
            issues.append({
                "type": "EN_WITHOUT_FR",
                "id": ig_id, "en": en_name,
                "msg": f"axes_en.{en_key}={en_val!r} mais axes_fr.{fr_key} absent"
            })
        elif fr_val is not None and en_val is None:
            issues.append({
                "type": "FR_WITHOUT_EN",
                "id": ig_id, "en": en_name,
                "msg": f"axes_fr.{fr_key}={fr_val!r} mais axes_en.{en_key} absent"
            })
        else:
            # Les deux présents : vérifier que fr_val correspond à la traduction attendue
            if isinstance(en_val, list):
                continue  # skip lists (edge case)

            # Cas spécial : treatment=roasted est context-dépendant
            #   avec cooking_process (dry/in_oil) → traitement=rôti
            #   sans cooking_process              → traitement=torréfié
            if en_key == "treatment" and str(en_val) == "roasted":
                cm = axes_en.get("cooking_process")
                expected_fr = "rôti" if cm else "torréfié"
            else:
                expected_fr = EN_VAL_TO_FR_VAL_BY_AXIS.get(en_key, {}).get(str(en_val))

            alternates = EN_VAL_TO_FR_VAL_ALTERNATES.get(en_key, {}).get(str(en_val), set())
            if (expected_fr and norm(str(fr_val)) != norm(expected_fr)
                    and norm(str(fr_val)) not in {norm(a) for a in alternates}):
                issues.append({
                    "type": "EN_FR_MISMATCH",
                    "id": ig_id, "en": en_name,
                    "msg": (f"axes_en.{en_key}={en_val!r} → "
                            f"axes_fr.{fr_key}={fr_val!r} "
                            f"(attendu: {expected_fr!r})")
                })
    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# B. COHÉRENCE NOM ↔ AXES
# ═══════════════════════════════════════════════════════════════════════════════

# Noms intentionnellement porteurs de qualificateurs qu'on a gardés
KNOWN_NAME_EXCEPTIONS = {
    # noms qui contiennent un mot mais l'axe ne correspond pas (intentionnel)
    ("ing_01657", "cooking_state"),   # apple (CNF commence par "raw")
    ("ing_00770", "cooking_state"),   # pre-cooked white rice (contient "cooked" dans fr)

    # "X milk" / "X's milk" en préfixe de fromage/yaourt = modificateur
    # d'origine (quel animal), pas la forme du produit — le fromage n'est
    # jamais "sous forme de lait". form=paste/crumbled/yogurt déjà correct.
    ("ing_00489", "form"),   # bread, made with milk (milk = ingrédient de la recette)
    ("ing_04985", "form"),   # Camembert, raw milk
    ("ing_05025", "form"),   # feta (sheep milk)
    ("ing_05230", "form"),   # cow's milk mozzarella
    ("ing_05286", "form"),   # cow's milk tomme
    ("ing_05369", "form"),   # ewe's milk fromage blanc
    ("ing_05371", "form"),   # goat's milk fromage blanc
    ("ing_05408", "form"),   # goat crottin, raw milk
    ("ing_05850", "form"),   # feta (whole cow milk)
    ("ing_05136", "form"),   # corsican ewe's milk soft cheese
    ("ing_05138", "form"),   # ewe's milk soft-ripened cheese
    ("ing_05140", "form"),   # ewe's milk pressed cheese (Pyrenees type)

    # "raw milk" = lait cru/non pasteurisé (un traitement), pas un
    # cooking_state — déjà porté par axes_en.treatment=raw_milk.
    ("ing_04985", "cooking_state"),  # Camembert, raw milk
    ("ing_05408", "cooking_state"),  # goat crottin, raw milk
    # "cooked pressed cheese" (pâte pressée demi-cuite) : le "cooked"
    # désigne la cuisson du caillé en fromagerie, pas un cooking_state.
    ("ing_05196", "cooking_state"),

    # fat_content numérique (ex. '16pct', '0pct') vs catégoriel
    # (skimmed/low_fat...) — asymétrie intentionnelle, déjà documentée.
    ("ing_05888", "fat_content"),  # part-skim mozzarella
    ("ing_05751", "fat_content"),  # skimmed pasteurized milk

    # "roasted chickpea" : convention légumineuse-snack = treatment=roasted
    # (comme les cacahuètes), pas cooking_state — cf. catégorie A.
    ("ing_05814", "cooking_state"),
}

# Formes dérivées du lait acceptables comme alternative à form="milk" quand
# le nom contient "milk" mais désigne un produit laitier transformé (pas du
# lait liquide brut) : liquide standard, concentré, en poudre, ou yaourt.
MILK_FORM_FAMILY = {"liquid", "concentrated", "powder", "yogurt"}

def check_name_axes(ig_id: str, en_name: str, axes_en: dict) -> list[dict]:
    issues = []
    en_lower = en_name.lower()
    for pattern, key, expected_val in NAME_TOKEN_TO_AXIS:
        if re.search(pattern, en_lower):
            actual = axes_en.get(key)
            if actual is None:
                # Axe absent mais le nom l'implique
                if (ig_id, key) not in KNOWN_NAME_EXCEPTIONS:
                    issues.append({
                        "type": "NAME_IMPLIES_AXIS_MISSING",
                        "id": ig_id, "en": en_name,
                        "msg": f'"{en_name}" implique {key}={expected_val} mais axe absent'
                    })
            elif str(actual) != expected_val:
                # Axe présent mais valeur différente du nom
                # On tolère cooking_state génériques (cooked/boiled/steamed tous acceptables)
                COOKING_FAMILY = {"cooked", "boiled", "steamed", "roasted", "baked",
                                  "fried", "grilled", "braised", "precooked"}
                if key == "cooking_state" and str(actual) in COOKING_FAMILY:
                    pass  # variante de cuisson acceptable
                elif key == "form" and expected_val == "milk" and str(actual) in MILK_FORM_FAMILY:
                    pass  # forme laitière dérivée acceptable
                elif (ig_id, key) not in KNOWN_NAME_EXCEPTIONS:
                    issues.append({
                        "type": "NAME_AXIS_MISMATCH",
                        "id": ig_id, "en": en_name,
                        "msg": (f'"{en_name}" implique {key}={expected_val} '
                                f'mais axe={actual!r}')
                    })
    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# C. OUTLIERS INTRA-SOUS-CATÉGORIE
# ═══════════════════════════════════════════════════════════════════════════════

def detect_outliers(
    sub_label: str, igs: list[dict]
) -> list[dict]:
    """Détecte les IGs dont les valeurs d'axes sont aberrantes pour leur sous-cat."""
    issues = []
    if len(igs) < 4:
        return []  # pas assez de voisins pour statistique

    # Distribution des valeurs par axe dans cette sous-cat
    axis_counts: dict[str, Counter] = {ax: Counter() for ax in AXES_FOR_OUTLIER}
    for ig in igs:
        axes_en = ig.get("axes_en") or {}
        for ax in AXES_FOR_OUTLIER:
            val = axes_en.get(ax)
            if val and not isinstance(val, list):
                axis_counts[ax][str(val)] += 1

    for ig in igs:
        axes_en = ig.get("axes_en") or {}
        ig_id = ig["id"]
        en_name = ig.get("canonical_name_en", "")
        for ax in AXES_FOR_OUTLIER:
            val = axes_en.get(ax)
            if val is None or isinstance(val, list):
                continue
            val_str = str(val)
            total = sum(axis_counts[ax].values())
            count = axis_counts[ax][val_str]
            # Signaler si la valeur est unique ET représente moins de 5% des IGs
            if count == 1 and total >= 5:
                issues.append({
                    "type": "OUTLIER_AXIS_VALUE",
                    "id": ig_id, "en": en_name,
                    "subcategory": sub_label,
                    "msg": (f'axes_en.{ax}={val_str!r} est unique dans "{sub_label}" '
                            f'({total} IGs, toutes autres valeurs: '
                            f'{dict(axis_counts[ax].most_common(3))})')
                })
    return issues


# ═══════════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    print("Chargement du tree...")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))

    issues_a: list[dict] = []  # EN↔FR coherence
    issues_b: list[dict] = []  # Name↔Axes coherence
    issues_c: list[dict] = []  # Outliers
    ig_count = 0

    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            sub_label = sub.get("label", "?")
            igs = sub.get("ingredient_groups", [])

            # C - outliers à la sous-catégorie
            issues_c.extend(detect_outliers(sub_label, igs))

            for ig in igs:
                ig_count += 1
                ig_id   = ig["id"]
                en_name = ig.get("canonical_name_en", "")
                axes_en = ig.get("axes_en") or {}
                axes_fr = ig.get("axes_fr") or {}

                # A
                issues_a.extend(check_en_fr_coherence(ig_id, en_name, axes_en, axes_fr))
                # B
                issues_b.extend(check_name_axes(ig_id, en_name, axes_en))

    # Dédupliquer les outliers identiques (même id+axe signalé plusieurs fois)
    seen_c = set()
    issues_c_dedup = []
    for i in issues_c:
        k = (i["id"], i["msg"][:60])
        if k not in seen_c:
            seen_c.add(k)
            issues_c_dedup.append(i)
    issues_c = issues_c_dedup

    all_issues = issues_a + issues_b + issues_c
    from collections import Counter as C2
    by_type = C2(i["type"] for i in all_issues)

    print(f"\n=== AUDIT COHÉRENCE INTERNE ({ig_count} IGs) ===\n")

    print("A. COHÉRENCE EN ↔ FR :")
    for t in ["EN_WITHOUT_FR", "FR_WITHOUT_EN", "EN_FR_MISMATCH"]:
        n = by_type.get(t, 0)
        print(f"  {t:35s}: {n:4d}")

    print("\nB. COHÉRENCE NOM ↔ AXES :")
    for t in ["NAME_IMPLIES_AXIS_MISSING", "NAME_AXIS_MISMATCH"]:
        n = by_type.get(t, 0)
        print(f"  {t:35s}: {n:4d}")

    print("\nC. OUTLIERS INTRA-SOUS-CATÉGORIE :")
    n = by_type.get("OUTLIER_AXIS_VALUE", 0)
    print(f"  {'OUTLIER_AXIS_VALUE':35s}: {n:4d}")

    print(f"\n  {'TOTAL':35s}: {len(all_issues):4d}")

    # Détail
    for section, label, issues in [
        ("A", "EN ↔ FR", issues_a),
        ("B", "Nom ↔ Axes", issues_b),
        ("C", "Outliers", issues_c),
    ]:
        if not issues:
            continue
        print(f"\n{'═'*60}")
        print(f"{section}. {label} ({len(issues)} issues) :")
        # Grouper par type
        by_t: dict[str, list] = defaultdict(list)
        for i in issues:
            by_t[i["type"]].append(i)
        for t, lst in sorted(by_t.items(), key=lambda x: -len(x[1])):
            print(f"\n  {t} ({len(lst)}) :")
            limit = 200 if args.verbose else 15
            for item in lst[:limit]:
                print(f"    [{item['id']}] {item['msg']}")
            if len(lst) > limit:
                print(f"    ... et {len(lst) - limit} autres")

    report = {
        "generated_at": datetime.now().isoformat(),
        "ig_count": ig_count,
        "summary": dict(by_type),
        "total": len(all_issues),
        "issues_A_en_fr": issues_a,
        "issues_B_name_axes": issues_b,
        "issues_C_outliers": issues_c,
    }
    OUT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRapport : {OUT_FILE}")


if __name__ == "__main__":
    main()
