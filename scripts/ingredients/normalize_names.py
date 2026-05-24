#!/usr/bin/env python3
"""
scripts/ingredients/normalize_names.py
=======================================
Normalise les noms canoniques des ingredient_groups du tree :

  1. Form stripping   : retire les préfixes/suffixes de forme (farine de, flour…)
                        des noms végétaux et vérifie l'axe form correspondant.
  2. EN inversions    : "category, specific" -> "specific category"
                        (mushroom, rice, pepper, cabbage, lettuce, tomato,
                         potato, squash, apple, mango, pear, onion, radish,
                         peas, peanuts)
  3. FR comma removal : "catégorie, qualificatif" -> "catégorie qualificatif"
  4. Bean repair      : ajoute "bean" aux noms EN incomplets quand FR = haricot
  5. Audit fixes      : ing_00501 (axe diète mal placé), ing_00844 (thermal_state)

Usage :
  python scripts/ingredients/normalize_names.py --dry-run
  python scripts/ingredients/normalize_names.py
  python scripts/ingredients/normalize_names.py --verbose
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

# ─── 1. FORM STRIPPING ────────────────────────────────────────────────────────

# Suffixes EN → valeur d'axe form
FORM_SUFFIXES_EN: dict[str, str] = {
    " flour":   "flour",
    " oil":     "oil",
    " butter":  "butter",
    " milk":    "milk",
    " yogurt":  "yogurt",
    " juice":   "juice",
    " extract": "extract",
}

# Préfixes FR → valeur d’axe form (triés du plus long au plus court)
FORM_PREFIXES_FR: list[tuple[str, str]] = sorted([
    ("farine de ",    "flour"),
    ("farine d’", "flour"),
    ("farine d’",     "flour"),
    ("huile de ",     "oil"),
    ("huile d’", "oil"),
    ("huile d’",      "oil"),
    ("beurre de ",    "butter"),
    ("beurre d’","butter"),
    ("beurre d’",     "butter"),
    ("lait de ",      "milk"),
    ("lait d’",  "milk"),
    ("lait d’",       "milk"),
    ("yaourt de ",    "yogurt"),
    ("yaourt d’","yogurt"),
    ("yaourt d’",     "yogurt"),
    ("yogourt de ",   "yogurt"),
    ("jus de ",       "juice"),
    ("jus d’",   "juice"),
    ("jus d’",        "juice"),
    ("pâte de ",      "paste"),
    ("pâte d’",  "paste"),
    ("pâte d’",       "paste"),
    # NE PAS inclure "extrait de" : produits comme "extrait de levure" ont
    # l’extrait comme identité du produit, pas comme simple forme.
], key=lambda x: -len(x[0]))

# Valeurs form "texture" : ne pas écraser par un form "type" issu du strip
FORM_TEXTURE_VALUES = {
    "crunchy", "creamy", "long_grain", "medium_grain", "short_grain",
    "rolled", "sliced", "grated", "diced", "flakes", "granulated",
    "pieces", "block", "whipped", "fresh_herb", "dried_herb", "spice",
    "whole",
}

# Mots/expressions animaux/laitiers → exclure du form stripping
ANIMAL_INDICATORS = {
    "ewe", "ewe's", "goat", "goat's", "mare", "mare's", "cow", "cow's",
    "buffalo", "sheep", "bovine", "camel", "donkey",
    "chèvre", "brebis", "vache", "jument", "bufflonne", "chamelle",
}

# Noms de produits laitiers complexes (base = produit, "milk" décrit l'ingrédient de production)
DAIRY_BASE_PATTERNS = {
    "feta", "camembert", "ricotta", "brie", "gouda", "cheddar",
    "parmesan", "mozzarella", "gruyere", "greek yogurt", "greek",
    "edam", "emmental", "manchego",
}

# IGs à ignorer pour le form stripping (noms trop complexes/malformés)
FORM_STRIP_SKIP_IDS = {"ing_04553", "ing_04555"}

# Suffixes à ne PAS traiter quand précédés de "in " (ex: "pineapple in juice")
_DRAINING_PREPOSITION = re.compile(r'\bin\s+$')


def _is_animal_base(base: str) -> bool:
    base_l = base.lower()
    # Split sur espaces, apostrophes ET virgules
    words = re.split(r"[\s',]+", base_l)
    return bool(set(words) & ANIMAL_INDICATORS)


def _is_dairy_base(base: str) -> bool:
    base_l = base.lower()
    for pat in DAIRY_BASE_PATTERNS:
        if pat in base_l:
            return True
    return False


def _norm_apos(s: str) -> str:
    """Normalise les apostrophes typographiques en apostrophe ASCII."""
    return s.replace("’", "'").replace("‘", "'").replace("ʼ", "'")


def _nonsensical_base(base: str) -> bool:
    """Retourne True si le résidu du form stripping n'est pas un nom d'ingrédient valide."""
    stripped = base.strip()
    if not stripped:
        return True
    last_word = stripped.split()[-1].lower().rstrip(".,")
    if last_word in {"with", "in", "of", "from", "made", "and", "or", "de", "du", "des", "la", "le", "les", "à"}:
        return True
    # Base d'un seul mot trop générique
    if stripped.lower() in {"whole", "full", "raw", "plain"}:
        return True
    return False


def strip_form_en(en: str, ig_id: str, current_form: str | None) -> tuple[str, str] | None:
    """
    Tente de retirer un suffixe de forme du nom EN.
    Retourne (new_name, form_value) ou None si aucun match valide.
    Skippé si l'axe form existant est une valeur "texture" différente du form implicite.
    """
    if ig_id in FORM_STRIP_SKIP_IDS:
        return None
    en_l = en.lower()
    for suffix, form_val in FORM_SUFFIXES_EN.items():
        if en_l.endswith(suffix):
            before = en_l[: -len(suffix)]
            # Exclure patterns "in X" (draining)
            if _DRAINING_PREPOSITION.search(before):
                return None
            base = en[: -len(suffix)].strip()
            if _is_animal_base(base) or _is_dairy_base(base) or _nonsensical_base(base):
                return None
            # Si l'axe form existant est une texture (crunchy, sliced...) → ne pas écraser
            if current_form and current_form in FORM_TEXTURE_VALUES and current_form != form_val:
                return None
            return base, form_val
    return None


def strip_form_fr(fr: str, ig_id: str, current_form: str | None) -> tuple[str, str] | None:
    """
    Tente de retirer un préfixe de forme du nom FR.
    Retourne (new_name, form_value) ou None si aucun match valide.
    Skippé si l'axe form existant est une valeur "texture" différente du form implicite.
    """
    if ig_id in FORM_STRIP_SKIP_IDS:
        return None
    fr_norm = _norm_apos(fr)
    fr_l = fr_norm.lower()
    for prefix, form_val in FORM_PREFIXES_FR:
        prefix_n = _norm_apos(prefix)
        if fr_l.startswith(prefix_n):
            base = fr[len(prefix):].strip()
            if _is_animal_base(base) or _is_dairy_base(base) or _nonsensical_base(base):
                return None
            # Si l'axe form existant est une texture → ne pas écraser
            if current_form and current_form in FORM_TEXTURE_VALUES and current_form != form_val:
                return None
            # Retourne la base avec apostrophes originales (non normalisées)
            return fr[len(prefix_n):].strip(), form_val
    return None


# ─── 2. EN INVERSIONS ─────────────────────────────────────────────────────────

# Noms communs EN à inverser : forme normalisée → singulier de sortie
INVERT_NOUNS: dict[str, str] = {
    "mushroom":   "mushroom",
    "mushrooms":  "mushroom",
    "rice":       "rice",
    "cabbage":    "cabbage",
    "lettuce":    "lettuce",
    "tomato":     "tomato",
    "tomatoes":   "tomato",
    "apple":      "apple",
    "apples":     "apple",
    "mango":      "mango",
    "mangoes":    "mango",
    "pear":       "pear",
    "pears":      "pear",
    "onion":      "onion",
    "onions":     "onion",
    "radish":     "radish",
    "radishes":   "radish",
    "squash":     "squash",
    "potato":     "potato",
    "potatoes":   "potato",
}

# Mots qui indiquent une PARTIE du végétal → ne pas inverser (juste enlever la virgule)
PART_WORDS = {
    "skin", "peel", "flesh", "pulp", "tops", "seed",
    "seeds", "kernel", "kernels", "hull", "bran", "germ", "root", "stalk",
    "stem", "core", "rind", "pit", "stone",
}

# Qualificateurs de forme → pas d'inversion (le nom de produit reste noun+form)
NO_INVERT_QUALIFIERS = {
    "nectar", "concentrate", "extract", "sauce", "paste",
    "all types", "all type",
}

# Mots de classification à ignorer dans la jonction des qualificateurs
SKIP_QUALIFIERS = {"fungi"}

# Inversions explicites pour les cas ambigus ou très complexes
EXPLICIT_INVERSIONS: dict[str, str] = {
    "lettuce, leaf, green":                             "green leaf lettuce",
    "lettuce, leaf, red":                               "red leaf lettuce",
    "lettuce, leaf":                                    "leaf lettuce",
    "mushroom, fungi, Cloud ears":                      "Cloud ears mushroom",
    "peas, edible-podded (snow peas)":                  "snow peas",
    # Noms d'oignons complexes avec description de partie
    "onion, spring (green) or scallion (includes tops and bulb)": "spring onion (green scallion)",
    "onion, young green, tops only":                    "young green onion tops",
}

# Axes dont les valeurs sont des qualificateurs d'état → filtrés pendant l'inversion
STATE_AXIS_KEYS = {
    "cooking_state", "thermal_state",
    "etat_cuisson", "etat_thermique",
}


def _split_outside_parens(s: str) -> list[str]:
    """Découpe par virgule hors parenthèses."""
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for c in s:
        if c == "(":
            depth += 1
            current.append(c)
        elif c == ")":
            depth -= 1
            current.append(c)
        elif c == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(c)
    if current:
        parts.append("".join(current).strip())
    return parts


def _norm_qualifier(q: str) -> str:
    return q.lower().strip().rstrip(".,")


def invert_en_name(en: str, axes: dict | None = None) -> str:
    """
    Applique les règles d'inversion EN.
    "category, specific" -> "specific category"
    axes : si fourni, filtre les qualificateurs redondants avec les axes d'état.
    """
    # Inversions explicites (cas ambigus codés en dur)
    en_exact = EXPLICIT_INVERSIONS.get(en)
    if en_exact:
        return en_exact

    parts = _split_outside_parens(en)
    if len(parts) < 2:
        return en

    first = parts[0].strip()
    first_l = first.lower()

    # Valeurs d'état présentes dans les axes (cooking_state, thermal_state)
    state_values: set[str] = set()
    if axes:
        for k, v in axes.items():
            if k in STATE_AXIS_KEYS and isinstance(v, str):
                state_values.add(v.lower())

    def _filter_qualifiers(qs: list[str]) -> list[str]:
        """Retire les qualificateurs redondants avec les axes d'état et les mots à ignorer."""
        result = []
        for q in qs:
            qn = _norm_qualifier(q)
            if qn in SKIP_QUALIFIERS:
                continue
            if qn in NO_INVERT_QUALIFIERS:
                return []  # Présence de forme → pas d'inversion du tout
            if qn in state_values:
                continue  # Qualificateur d'état redondant avec axe
            result.append(q)
        return result

    # ── Pepper sweet → "color bell pepper" ───────────────────────────────────
    if first_l in ("pepper", "peppers") and len(parts) >= 3:
        if parts[1].strip().lower() == "sweet":
            color_parts = _filter_qualifiers(parts[2:])
            if not color_parts:
                return "bell pepper"
            color = " ".join(p.strip() for p in color_parts)
            return f"{color} bell pepper"

    # ── Pepper générique (non sweet) → "X pepper" ────────────────────────────
    if first_l in ("pepper", "peppers") and len(parts) >= 2:
        qs = _filter_qualifiers(parts[1:])
        if not qs:
            return "pepper"
        return " ".join(p.strip() for p in qs) + " pepper"

    # ── Peas → "X peas" ──────────────────────────────────────────────────────
    if first_l == "peas":
        qs = _filter_qualifiers(parts[1:])
        rest = ", ".join(p.strip() for p in qs) if qs else ""
        return f"{rest} peas" if rest else "peas"

    # ── Peanuts → normalisation ───────────────────────────────────────────────
    if first_l in ("peanut", "peanuts"):
        rest_parts = [p.strip() for p in parts[1:]]
        filtered = [p for p in rest_parts if _norm_qualifier(p) not in ("all types", "all type")]
        filtered = _filter_qualifiers(filtered)
        if not filtered:
            return "peanuts"
        rest = " ".join(filtered)
        return f"{rest} peanuts"

    # ── Inversions génériques via INVERT_NOUNS ────────────────────────────────
    if first_l in INVERT_NOUNS:
        noun = INVERT_NOUNS[first_l]
        qualifiers = parts[1:]

        # Vérifie si un qualificateur est un NO_INVERT → juste jonction sans inversion
        for q in qualifiers:
            if _norm_qualifier(q) in NO_INVERT_QUALIFIERS:
                return noun + " " + " ".join(q.strip() for q in qualifiers)

        # Si N'IMPORTE quel qualificateur commence par un mot de partie → pas d'inversion
        def _has_part(qs: list[str]) -> bool:
            return any(
                _norm_qualifier(q).split()[0] in PART_WORDS
                for q in qs if q
            )
        if _has_part(qualifiers):
            return noun + " " + " ".join(q.strip() for q in qualifiers)

        # Filtre les qualificateurs d'état redondants
        qs_filtered = _filter_qualifiers(qualifiers)
        if not qs_filtered:
            return noun
        qual_str = " ".join(q.strip() for q in qs_filtered)
        return f"{qual_str} {noun}"

    return en


# ─── 3. FR COMMA REMOVAL ─────────────────────────────────────────────────────

def remove_fr_commas(fr: str) -> str:
    """
    Supprime les virgules hors parenthèses dans un nom FR.
    "champignon, shiitake" -> "champignon shiitake"
    """
    parts = _split_outside_parens(fr)
    if len(parts) <= 1:
        return fr
    return " ".join(p.strip() for p in parts)


# ─── 4. BEAN REPAIR ──────────────────────────────────────────────────────────

# Noms EN incomplets → nom EN corrigé (avec "bean")
# Clé : nom EN normalisé (lowercase, strip) ; valeur : nom EN final
_BEAN_FIXES: dict[str, str] = {
    "yellow":            "yellow bean",
    "adzuki":            "adzuki bean",
    "black turtle":      "black turtle bean",
    "black":             "black bean",
    "cannellini":        "cannellini bean",
    "french":            "french bean",
    "great northern":    "great northern bean",
    "kidney, all types": "kidney bean",
    "kidney":            "kidney bean",
    "kidney, dark red":  "dark red kidney bean",
    "kidney, light red": "light red kidney bean",
    "lima, baby":        "baby lima bean",
    "lima, large":       "large lima bean",
    "lima":              "lima bean",
    "mung":              "mung bean",
    "mungo":             "mung bean",
    "navy":              "navy bean",
    "pinto":             "pinto bean",
    "pink":              "pink bean",
    "red":               "red bean",
    "small red":         "small red bean",
    "white":             "white bean",
    "borlotti":          "borlotti bean",
    "flageolet":         "flageolet bean",
}


def repair_bean_name(en: str, fr: str) -> str | None:
    """
    Si FR contient "haricot" et EN ne contient pas "bean" → retourne le nom EN corrigé.
    Sinon retourne None.
    """
    if "bean" in en.lower():
        return None
    if "haricot" not in fr.lower():
        return None
    en_key = en.lower().strip()
    return _BEAN_FIXES.get(en_key)


# ─── 5. AUDIT FIXES ──────────────────────────────────────────────────────────

def apply_audit_fixes(ig: dict, dry_run: bool) -> list[str]:
    """Corrections ciblées sur des IGs spécifiques. Retourne la liste des modifications."""
    changes = []
    ig_id = ig["id"]
    axes = ig.get("axes", {})

    # ing_00501 : axe diète (sans gluten) mal placé dans axes traitement
    if ig_id == "ing_00501":
        bad_keys = [k for k in list(axes.keys()) if "gluten" in k.lower() or k.lower() == "traitement"]
        for k in bad_keys:
            changes.append(f"remove axis '{k}: {axes[k]}'")
            if not dry_run:
                del axes[k]

    # ing_00844 : thermal_state rehydrated → dried (abricot séché moelleux)
    if ig_id == "ing_00844":
        if axes.get("thermal_state") == "rehydrated":
            changes.append("thermal_state: rehydrated -> dried")
            if not dry_run:
                axes["thermal_state"] = "dried"
        if axes.get("etat_thermique") == "réhydraté":
            changes.append("etat_thermique: réhydraté -> séché")
            if not dry_run:
                axes["etat_thermique"] = "séché"

    # ing_04589 : form paste → butter (peanut butter = beurre d'arachide)
    if ig_id == "ing_04589":
        if axes.get("form") == "paste":
            changes.append("form: paste -> butter")
            if not dry_run:
                axes["form"] = "butter"
        if axes.get("forme") == "pâte":
            changes.append("forme: pâte -> beurre")
            if not dry_run:
                axes["forme"] = "beurre"

    return changes


# ─── PIPELINE PRINCIPAL ───────────────────────────────────────────────────────

def walk_groups(tree: dict):
    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                yield ig


def process_tree(tree: dict, dry_run: bool, verbose: bool) -> dict:
    stats = {
        "form_en":    0,
        "form_fr":    0,
        "form_axis":  0,
        "inv_en":     0,
        "comma_fr":   0,
        "bean":       0,
        "audit":      0,
        "groups":     0,
    }
    changes = []

    for ig in walk_groups(tree):
        ig_id   = ig["id"]
        axes    = ig.get("axes", {})
        en_orig = ig.get("canonical_name_en", "")
        fr_orig = ig.get("canonical_name_fr", "")

        rec: dict = {"id": ig_id}
        changed = False

        # ── 1. Form stripping ────────────────────────────────────────────────
        en_cur = en_orig
        fr_cur = fr_orig
        current_form = axes.get("form") or axes.get("forme") or None

        form_en_result = strip_form_en(en_cur, ig_id, current_form)
        if form_en_result:
            new_en, form_val = form_en_result
            rec["en_before_form"] = en_cur
            rec["en_after_form"]  = new_en
            stats["form_en"] += 1
            changed = True
            if verbose:
                print(f"  FORM-EN [{ig_id}]: '{en_cur}' -> '{new_en}'  [form:{form_val}]")
            if not dry_run:
                ig["canonical_name_en"] = new_en
                en_cur = new_en
                # Met à jour l'axe form si absent ou différent (mais pas une texture)
                if current_form != form_val and current_form not in FORM_TEXTURE_VALUES:
                    rec["form_axis_before"] = current_form
                    rec["form_axis_after"]  = form_val
                    stats["form_axis"] += 1
                    axes["form"] = form_val
                    if "forme" in axes:
                        axes["forme"] = form_val
                    current_form = form_val

        form_fr_result = strip_form_fr(fr_cur, ig_id, current_form)
        if form_fr_result:
            new_fr, form_val_fr = form_fr_result
            rec["fr_before_form"] = fr_cur
            rec["fr_after_form"]  = new_fr
            stats["form_fr"] += 1
            changed = True
            if verbose:
                print(f"  FORM-FR [{ig_id}]: '{fr_cur}' -> '{new_fr}'  [form:{form_val_fr}]")
            if not dry_run:
                ig["canonical_name_fr"] = new_fr
                fr_cur = new_fr
                # Met à jour l'axe form seulement si EN strip n'a pas déjà défini un type
                if current_form != form_val_fr and current_form not in FORM_TEXTURE_VALUES:
                    if "en_after_form" not in rec:  # EN n'a pas déjà défini le form
                        axes["form"] = form_val_fr
                        if "forme" in axes:
                            axes["forme"] = form_val_fr

        # ── 2. EN inversions ────────────────────────────────────────────────
        new_en_inv = invert_en_name(en_cur, axes=axes)
        if new_en_inv != en_cur:
            rec["en_before_inv"] = en_cur
            rec["en_after_inv"]  = new_en_inv
            stats["inv_en"] += 1
            changed = True
            if verbose:
                print(f"  INV-EN  [{ig_id}]: '{en_cur}' -> '{new_en_inv}'")
            if not dry_run:
                ig["canonical_name_en"] = new_en_inv
                en_cur = new_en_inv

        # ── 3. FR comma removal ─────────────────────────────────────────────
        new_fr_nc = remove_fr_commas(fr_cur)
        if new_fr_nc != fr_cur:
            rec["fr_before_comma"] = fr_cur
            rec["fr_after_comma"]  = new_fr_nc
            stats["comma_fr"] += 1
            changed = True
            if verbose:
                print(f"  COMMA-FR [{ig_id}]: '{fr_cur}' -> '{new_fr_nc}'")
            if not dry_run:
                ig["canonical_name_fr"] = new_fr_nc
                fr_cur = new_fr_nc

        # ── 4. Bean repair ──────────────────────────────────────────────────
        bean_fix = repair_bean_name(en_cur, fr_cur)
        if bean_fix:
            rec["en_before_bean"] = en_cur
            rec["en_after_bean"]  = bean_fix
            stats["bean"] += 1
            changed = True
            if verbose:
                print(f"  BEAN    [{ig_id}]: '{en_cur}' -> '{bean_fix}'")
            if not dry_run:
                ig["canonical_name_en"] = bean_fix

        # ── 5. Audit fixes ───────────────────────────────────────────────────
        audit_changes = apply_audit_fixes(ig, dry_run)
        if audit_changes:
            rec["audit"] = audit_changes
            stats["audit"] += len(audit_changes)
            changed = True
            if verbose:
                for ac in audit_changes:
                    print(f"  AUDIT   [{ig_id}]: {ac}")

        if changed:
            stats["groups"] += 1
            changes.append(rec)

    return stats, changes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run",  action="store_true", help="Ne pas modifier le tree")
    parser.add_argument("--verbose",  action="store_true", help="Afficher chaque modification")
    args = parser.parse_args()

    print("Chargement du tree...")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))

    print("Normalisation des noms...")
    stats, changes = process_tree(tree, dry_run=args.dry_run, verbose=args.verbose)

    print(f"\nResultats :")
    print(f"  Groupes modifies        : {stats['groups']}")
    print(f"  Form stripping EN       : {stats['form_en']}")
    print(f"  Form stripping FR       : {stats['form_fr']}")
    print(f"  Axes form corriges      : {stats['form_axis']}")
    print(f"  EN inversions           : {stats['inv_en']}")
    print(f"  FR comma removal        : {stats['comma_fr']}")
    print(f"  Bean repairs            : {stats['bean']}")
    print(f"  Audit fixes             : {stats['audit']}")

    if not args.dry_run:
        TREE_FILE.write_text(
            json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"\nTree sauvegarde : {TREE_FILE}")

    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run":  args.dry_run,
        "stats":    stats,
        "changes":  changes,
    }
    report_path = OUT_DIR / "normalize_names_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Rapport sauve : {report_path}")

    if changes:
        print("\nEchantillon (15 premiers) :")
        for c in changes[:15]:
            for key in ("en_after_form", "en_after_inv", "en_after_bean", "fr_after_form", "fr_after_comma"):
                before_key = key.replace("after", "before")
                if key in c:
                    print(f"  [{c['id']}] {key}: '{c[before_key]}' -> '{c[key]}'")


if __name__ == "__main__":
    main()
