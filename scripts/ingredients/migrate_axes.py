#!/usr/bin/env python3
"""
scripts/ingredients/migrate_axes.py
=====================================
Migre le ingredient_tree.json en deux opérations atomiques :

  1. TRADUCTION FR → EN
     Ajoute les clés EN canoniques en parallèle des clés FR existantes
     (les FR ne sont PAS supprimées — on garde les deux).
     Cas spéciaux :
       - conditionnement  → packaging OU thermal_state selon la valeur
       - traitement       → treatment + migration fat_content / sodium / seasoning
       - procede_cuisson  → treatment (merge avec traitement si présent)
       - egouttage + milieu_conservation → draining (merge des deux)
       - teneur_MG numérique → fat_content_pct (conservé brut) + fat_content (catégoriel)
       - traitement array-sérialisé → liste de traitements EN

  2. CONSOLIDATION DES VARIANTS
     Si plusieurs variants d'un même groupe ont la même empreinte EN résolue,
     ils sont fusionnés en un seul variant avec un tableau `sources` (priorité :
     CIQUAL > USDA > CNF). Les champs `source` et `source_id` sont conservés
     (source primaire) pour la rétrocompatibilité.

Usage :
  python scripts/ingredients/migrate_axes.py [--dry-run] [--verbose]

Sortie :
  backend/data/ingredients/ingredients_tree.json  (mis à jour in-place)
  scripts/ingredients/migrate_axes_report.json    (rapport détaillé)
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT       = Path(__file__).resolve().parents[2]
DATA       = ROOT / "backend/data"
TREE_FILE  = DATA / "ingredients/ingredients_tree.json"
SCHEMA_FILE= DATA / "ingredients/axes_schema.json"
OUT_DIR    = ROOT / "scripts/ingredients"
REPORT_FILE= OUT_DIR / "migrate_axes_report.json"

SOURCE_PRIORITY = {"CIQUAL": 0, "USDA": 1, "CNF": 2}


# ══════════════════════════════════════════════════════════════════════════════
# NORMALISATION
# ══════════════════════════════════════════════════════════════════════════════

def _norm(s: str) -> str:
    """Minuscules, sans accent ; séparateurs (-, +, ', /) → espace → clé de lookup."""
    s = unicodedata.normalize("NFD", str(s).lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    # Remplace les séparateurs par un espace (pas suppression) pour chair+peau, demi-écrémé, etc.
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


# ══════════════════════════════════════════════════════════════════════════════
# TABLES DE TRADUCTION FR → EN
# ══════════════════════════════════════════════════════════════════════════════

# Axe FR → axe EN canonique (cas simple, hors split)
FR_AXIS_TO_EN: dict[str, str] = {
    "etat_cuisson":       "cooking_state",
    "etat_thermique":     "thermal_state",
    "forme":              "form",
    "partie":             "part",
    "traitement":         "treatment",
    "procede_cuisson":    "treatment",
    "assaisonnement":     "seasoning",
    "egouttage":          "draining",
    "milieu_conservation":"draining",
    "origine":            "origin",
    "maturite":           "ripeness",
    "teneur_MG":          "fat_content",
    # conditionnement : split selon valeur, traité séparément
}

# Valeur FR normalisée → valeur EN (partagée entre axes)
FR_VAL_TO_EN: dict[str, str] = {
    # cooking_state
    "cru": "raw", "crue": "raw",
    "cuit": "cooked", "cuite": "cooked", "cuits": "cooked", "cuites": "cooked",
    "bouilli": "boiled", "bouillie": "boiled",
    "vapeur": "steamed", "a la vapeur": "steamed",
    "frit": "fried", "frite": "fried",
    "grille": "grilled", "grilee": "grilled",
    "roti": "roasted", "rotie": "roasted",
    "au four": "baked",
    "saute": "sauteed", "sautee": "sauteed",
    "poche": "poached", "pochee": "poached",
    "braise": "braised", "braisee": "braised", "etouffee": "braised",
    "brouille": "scrambled", "brouilee": "scrambled",
    "dur": "hard_boiled",
    "coque": "soft_boiled", "a la coque": "soft_boiled",
    "plat": "fried_flat",
    "precuit": "precooked", "precuite": "precooked",
    "a cuire": "to_cook",
    "omelette": "omelette",
    "poele": "pan_fried",
    # thermal_state
    "frais": "fresh", "fraiche": "fresh",
    "surgele": "frozen", "surgelee": "frozen",
    "congele": "frozen", "congelee": "frozen",
    "seche": "dried", "sechee": "dried", "sec": "dried",
    "deshydrate": "dehydrated", "deshydratee": "dehydrated",
    "rehydrate": "rehydrated", "rehydratee": "rehydrated",
    "lyophilise": "freeze_dried", "lyophilisee": "freeze_dried",
    "pasteurise": "pasteurized", "pasteurisee": "pasteurized",
    "uht": "uht",
    "rayon frais": "refrigerated",
    "refrigere": "refrigerated", "refrigeree": "refrigerated",
    "sous pression": "pressurized",
    "mature": "mature",
    # forme / form
    "entier": "whole", "entiere": "whole",
    "poudre": "powder",
    "farine": "flour",
    "huile": "oil",
    "jus": "juice",
    "beurre": "butter",
    "creme": "cream",
    "concentre": "concentrate", "concentree": "concentrate",
    "extrait": "extract", "extraite": "extract",
    "moulu": "ground", "moulue": "ground",
    "broye": "crushed", "broyee": "crushed",
    "concasse": "diced", "concassee": "diced",
    "tranche": "sliced", "tranchee": "sliced",
    "rape": "grated", "rapee": "grated",
    "emiette": "crumbled", "emiettee": "crumbled",
    "flocons": "rolled",
    "paillettes": "flakes",
    "granule": "granulated", "granulee": "granulated",
    "petits morceaux": "pieces",
    "liquide": "liquid",
    "bloc": "block",
    "comprime": "tablet", "pastilles": "tablet",
    "confiture": "jam",
    "compote": "compote",
    "gelee": "jelly",
    "confit": "candied", "confite": "candied",
    "croquant": "crunchy", "croquante": "crunchy",
    "cremeux": "creamy", "cremeuse": "creamy",
    "fouette": "whipped", "fouettee": "whipped",
    "epice": "spice",
    "herbe fraiche": "fresh_herb",
    "herbe sechee": "dried_herb",
    "creme de fruit": "fruit_cream",
    "eau vegetale": "plant_water",
    "grain court": "short_grain",
    "grain moyen": "medium_grain",
    "grain long": "long_grain",
    "steel cut": "steel_cut",
    "instantane": "instant", "instantanee": "instant",
    "yaourt": "yogurt",
    "lait": "milk",
    "pate": "paste",
    "puree": "pureed",
    # chair+peau — le + devient espace après _norm → "chair peau"
    "chair peau": "flesh_skin",
    # partie / part
    "graine": "seed", "graines": "seed",
    "graine entiere": "whole_seed",
    "avec graines": "with_seeds",
    "sans graines": "seedless",
    "feuille": "leaf", "feuilles": "leaf",
    "tige": "stem",
    "racine": "root",
    "gousse": "pod",
    "fleur": "flower",
    "chair": "flesh",
    "chair sans peau": "flesh_peeled",
    "chair peau": "flesh_skin",
    "chair peau": "flesh_skin",
    "avec peau": "with_skin",
    "sans peau": "peeled",
    "pele": "peeled", "pelee": "peeled",
    "pelure": "peel",
    "pepins": "seeds",
    "denoyaute": "pitted", "denoyautee": "pitted",
    "pousse": "sprout", "pousses": "sprout",
    "tubercule": "tuber",
    # assaisonnement / seasoning
    "sale": "salted", "salee": "salted",
    "sans sel": "unsalted",
    "sucre": "sweetened", "sucree": "sweetened",
    "sans sucre": "unsweetened",
    "aromatise": "flavored", "aromatisee": "flavored",
    "epice_as": "spiced",
    "nature": "plain",
    # traitement / treatment
    "fume": "smoked", "fumee": "smoked",
    "fermente": "fermented", "fermentee": "fermented",
    "affine": "aged", "affinee": "aged",
    "blanchi": "blanched", "blanchie": "blanched",
    "enrichi": "enriched", "enrichie": "enriched",
    "non enrichi": "unenriched", "non enrichie": "unenriched",
    "iode": "iodized", "iodee": "iodized",
    "iode et fluore": "iodized_fluoride", "iode fluore": "iodized_fluoride",
    "raffine": "refined", "raffinee": "refined",
    "brut": "unrefined", "brute": "unrefined",
    "distille": "distilled", "distillee": "distilled",
    "germe": "sprouted", "germee": "sprouted",
    "decortique": "hulled", "decortiquee": "hulled",
    "vierge": "virgin",
    "extra vierge": "extra_virgin",
    "texture": "textured", "texturee": "textured",
    "decafeine": "decaffeinated", "decafeinee": "decaffeinated",
    "etuve": "parboiled", "etuvee": "parboiled",
    "sans pulpe": "no_pulp",
    "non blanchi": "unblanched", "non blanchie": "unblanched",
    "fluore": "fluoride_added", "fluoree": "fluoride_added",
    "gras ajoute": "fat_added",
    # egouttage
    "egoutte": "drained", "egouttee": "drained",
    # milieu_conservation (clés dédiées — ne pas utiliser pour procede_cuisson)
    "dans l eau": "in_water",
    "dans sirop": "in_syrup",
    "au vinaigre": "in_vinegar",
    # origine
    "vegetal": "plant", "vegetale": "plant",
    # maturite
    "trop mur": "overripe", "trop mure": "overripe",
    # teneur_MG (catégoriels)
    "ecreme": "skimmed", "ecremee": "skimmed",
    "demi ecreme": "semi_skimmed", "demi ecremee": "semi_skimmed",
    "entier_mg": "whole",        # alias pour éviter conflit avec forme:entier
    "allege": "light", "allegee": "light",
    # traitement → fat_content (valeurs déplacées)
    "ecreme_tr": "skimmed",
    "demi ecreme_tr": "semi_skimmed",
    "allege en gras": "low_fat",
    "eleve en gras": "high_fat",
    # traitement → sodium
    "faible en sodium": "low",
    "reduit en sodium": "reduced",
}

# Valeurs de traitement qui migrent vers fat_content
TRAITEMENT_TO_FAT: set[str] = {
    "ecreme", "ecremee", "demi ecreme", "demi ecremee",
    "allege en gras", "allegee en gras", "eleve en gras", "elevee en gras",
}
# Valeurs de traitement qui migrent vers sodium
TRAITEMENT_TO_SODIUM: set[str] = {
    "faible en sodium", "reduit en sodium",
}
# Valeurs de traitement qui migrent vers seasoning
TRAITEMENT_TO_SEASONING: set[str] = {"nature"}
# Valeurs à ignorer (drapeaux diét, non-traitements)
TRAITEMENT_SKIP: set[str] = {
    "sans gluten", "reduit en lactose", "reduit en proteines",
}

# conditionnement → thermal_state (set de normes)
# Table dédiée procede_cuisson → traitement EN (évite la collision avec milieu_conservation "à l'huile")
PROCEDE_CUISSON_MAP: dict[str, str] = {
    "a l huile": "oil_roasted",
    "a sec":     "dry_roasted",
}

# milieu_conservation → draining
MILIEU_CONSERVATION_MAP: dict[str, str] = {
    "a l huile":  "in_oil",
    "dans l eau": "in_water",
    "dans sirop": "in_syrup",
    "au vinaigre":"in_vinegar",
}

COND_TO_THERMAL: dict[str, str] = {
    "uht": "uht",
    "pasteurise": "pasteurized",
    "pasteurisee": "pasteurized",
    "rayon frais": "refrigerated",
    "sous pression": "pressurized",
}
# conditionnement → packaging
COND_TO_PACKAGING: dict[str, str] = {
    "commercial": "commercial",
    "conserve": "canned",
    "preemballe": "prepackaged",
    "preemballee": "prepackaged",
    "sous vide": "vacuum",
    "tablette": "tablet",
}

# teneur_MG numérique → catégorie fat_content (bornes supérieures en %)
TENEUR_MG_RANGES = [
    (0.5,  "fat_free"),
    (1.5,  "skimmed"),
    (2.5,  "semi_skimmed"),
    (5.0,  "low_fat"),
    (20.0, "medium_fat"),
    (40.0, "full_fat"),
    (999,  "high_fat"),
]


def _teneur_to_cat(val: str) -> str | None:
    """Convertit une valeur numérique teneur_MG en catégorie fat_content."""
    val = val.strip().replace(",", ".")
    # plage "2-3" → prendre la moyenne
    if "-" in val:
        parts = val.split("-")
        try:
            nums = [float(p) for p in parts]
            num = sum(nums) / len(nums)
        except ValueError:
            return None
    else:
        try:
            num = float(val)
        except ValueError:
            return None
    for upper, cat in TENEUR_MG_RANGES:
        if num <= upper:
            return cat
    return "high_fat"


def _parse_traitement_array(raw: str) -> list[str]:
    """Tente de parser une valeur array-sérialisée comme '['blanchi', 'non blanchi']'."""
    m = re.findall(r"'([^']+)'", raw)
    return m if m else [raw]


# ══════════════════════════════════════════════════════════════════════════════
# TRADUCTION D'UN DICT D'AXES
# ══════════════════════════════════════════════════════════════════════════════

def translate_axes(axes_fr: dict, verbose: bool = False) -> tuple[dict, list[str]]:
    """
    Traduit les axes FR en EN et les ajoute dans le dict.
    Retourne (axes_bilingues, [warnings]).
    Les clés FR sont conservées.
    """
    out = dict(axes_fr)   # copie avec FR
    notes: list[str] = []

    # Accumulation si plusieurs axes FR → même axe EN (traitement+procede_cuisson, egouttage+milieu)
    en_accumulator: dict[str, list[str]] = defaultdict(list)

    for fr_key, fr_val in axes_fr.items():
        val_n = _norm(str(fr_val))

        # ── conditionnement (split) ──────────────────────────────────
        if fr_key == "conditionnement":
            if val_n in COND_TO_THERMAL:
                en_accumulator["thermal_state"].append(COND_TO_THERMAL[val_n])
            elif val_n in COND_TO_PACKAGING:
                en_accumulator["packaging"].append(COND_TO_PACKAGING[val_n])
            else:
                notes.append(f"conditionnement valeur inconnue: {fr_val!r}")
            continue

        # ── teneur_MG ─────────────────────────────────────────────────
        if fr_key == "teneur_MG":
            # val_n est déjà normalisé — cat_map utilise les formes normalisées
            cat_map = {
                "ecreme": "skimmed", "ecremee": "skimmed",
                "demi ecreme": "semi_skimmed", "demi ecremee": "semi_skimmed",
                "entier": "whole", "entiere": "whole",
                "allege": "light", "allegee": "light",
            }
            if val_n in cat_map:
                en_accumulator["fat_content"].append(cat_map[val_n])
            else:
                cat = _teneur_to_cat(str(fr_val))
                if cat:
                    en_accumulator["fat_content"].append(cat)
                    out["fat_content_pct"] = str(fr_val)   # valeur brute conservée
                else:
                    notes.append(f"teneur_MG non parsable: {fr_val!r}")
            continue

        # ── traitement (valeurs qui migrent vers d'autres axes) ───────
        if fr_key == "traitement":
            raw_str = str(fr_val)
            # Array sérialisé ?
            if raw_str.startswith("["):
                items = _parse_traitement_array(raw_str)
            else:
                items = [raw_str]

            treatment_vals: list[str] = []
            for item in items:
                item_n = _norm(item)
                if item_n in TRAITEMENT_SKIP:
                    notes.append(f"traitement ignoré (drapeau diét): {item!r}")
                elif item_n in TRAITEMENT_TO_FAT:
                    fat_map = {
                        "ecreme": "skimmed", "ecremee": "skimmed",
                        "demi ecreme": "semi_skimmed", "demi ecremee": "semi_skimmed",
                        "allege en gras": "low_fat", "allegee en gras": "low_fat",
                        "eleve en gras": "high_fat", "elevee en gras": "high_fat",
                    }
                    en_accumulator["fat_content"].append(fat_map.get(item_n, item_n))
                elif item_n in TRAITEMENT_TO_SODIUM:
                    sod_map = {"faible en sodium": "low", "reduit en sodium": "reduced"}
                    en_accumulator["sodium"].append(sod_map.get(item_n, item_n))
                elif item_n in TRAITEMENT_TO_SEASONING:
                    en_accumulator["seasoning"].append("plain")
                else:
                    en_val = FR_VAL_TO_EN.get(item_n, item_n)
                    if en_val != item_n:
                        treatment_vals.append(en_val)
                    else:
                        notes.append(f"traitement non traduit: {item!r}")
                        treatment_vals.append(item_n)

            if treatment_vals:
                en_accumulator["treatment"].extend(treatment_vals)
            continue

        # ── procede_cuisson → treatment (table dédiée) ────────────────
        if fr_key == "procede_cuisson":
            en_val = PROCEDE_CUISSON_MAP.get(val_n)
            if en_val:
                en_accumulator["treatment"].append(en_val)
            else:
                notes.append(f"procede_cuisson non traduit: {fr_val!r}")
            continue

        # ── assaisonnement avec "épicé" qui a un alias ────────────────
        if fr_key == "assaisonnement" and val_n in ("epice", "epicee"):
            en_accumulator["seasoning"].append("spiced")
            continue

        # ── milieu_conservation → draining (table dédiée) ─────────────
        if fr_key == "milieu_conservation":
            en_val = MILIEU_CONSERVATION_MAP.get(val_n)
            if en_val:
                en_accumulator["draining"].append(en_val)
            else:
                notes.append(f"milieu_conservation non traduit: {fr_val!r}")
            continue

        # ── cas général ───────────────────────────────────────────────
        en_key = FR_AXIS_TO_EN.get(fr_key)
        if not en_key:
            # Déjà des clés EN dans le tree (migration partielle) → ignorer
            if fr_key not in ("color", "couleur", "taille", "size", "variete", "variety",
                               "affinage", "ripening", "sodium", "packaging", "draining",
                               "cooking_state", "thermal_state", "form", "part",
                               "treatment", "seasoning", "fat_content", "origin",
                               "ripeness", "fat_content_pct"):
                notes.append(f"axe FR non mappé: {fr_key!r}")
            continue

        en_val = FR_VAL_TO_EN.get(val_n)
        if en_val:
            en_accumulator[en_key].append(en_val)
        else:
            notes.append(f"valeur non traduite: {fr_key}={fr_val!r}")
            en_accumulator[en_key].append(val_n)

    # Injecter les accumulations dans out
    for en_key, vals in en_accumulator.items():
        unique = list(dict.fromkeys(vals))
        out[en_key] = unique[0] if len(unique) == 1 else unique

    return out, notes


# ══════════════════════════════════════════════════════════════════════════════
# FINGERPRINT EN (pour détection de doublons)
# ══════════════════════════════════════════════════════════════════════════════

EN_AXES = {
    "cooking_state", "thermal_state", "form", "part", "treatment",
    "seasoning", "packaging", "draining", "origin", "ripeness",
    "fat_content", "color", "size", "variety", "ripening", "sodium",
}


def axes_fingerprint(axes_dict: dict) -> tuple:
    """Empreinte normalisée des axes EN d'un variant — utilisée pour la consolidation."""
    items = []
    for k, v in axes_dict.items():
        if k not in EN_AXES:
            continue
        val = tuple(sorted(v)) if isinstance(v, list) else str(v)
        items.append((k, val))
    return tuple(sorted(items))


# ══════════════════════════════════════════════════════════════════════════════
# CONSOLIDATION DES VARIANTS
# ══════════════════════════════════════════════════════════════════════════════

def merge_variants(variants: list[dict]) -> list[dict]:
    """
    Fusionne les variants ayant la même empreinte EN.
    Priorité sources : CIQUAL > USDA > CNF.
    Retourne la liste consolidée.
    """
    # Grouper par fingerprint
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for vr in variants:
        fp = axes_fingerprint(vr.get("axes", {}))
        groups[fp].append(vr)

    result: list[dict] = []
    for fp, group in groups.items():
        if len(group) == 1:
            result.append(group[0])
            continue

        # Trier par priorité source
        group_sorted = sorted(
            group,
            key=lambda v: SOURCE_PRIORITY.get(v.get("source", ""), 99)
        )
        primary = group_sorted[0]

        # Construire la liste sources
        sources = [
            {"source": v.get("source", ""), "source_id": str(v.get("source_id", ""))}
            for v in group_sorted
        ]

        merged = dict(primary)
        merged["source"]    = primary.get("source", "")
        merged["source_id"] = primary.get("source_id", "")
        merged["sources"]   = sources   # toutes les origines
        result.append(merged)

    return result


# ══════════════════════════════════════════════════════════════════════════════
# TRAITEMENT D'UN GROUPE
# ══════════════════════════════════════════════════════════════════════════════

def process_group(ig: dict, verbose: bool) -> tuple[dict, dict]:
    """Traduit + consolide un ingredient_group. Retourne (ig_modifié, stats)."""
    stats = {"axes_translated": 0, "variants_merged": 0, "warnings": []}

    # Axes au niveau du groupe
    if ig.get("axes"):
        new_axes, notes = translate_axes(ig["axes"], verbose)
        if new_axes != ig["axes"]:
            stats["axes_translated"] += 1
        ig = dict(ig)
        ig["axes"] = new_axes
        stats["warnings"].extend(notes)

    # Variants
    variants = ig.get("variants", [])
    before = len(variants)
    new_variants = []
    for vr in variants:
        if vr.get("axes"):
            new_ax, notes = translate_axes(vr["axes"], verbose)
            if new_ax != vr["axes"]:
                stats["axes_translated"] += 1
            vr = dict(vr)
            vr["axes"] = new_ax
            stats["warnings"].extend(notes)
        new_variants.append(vr)

    # Consolidation
    consolidated = merge_variants(new_variants)
    after = len(consolidated)
    stats["variants_merged"] = before - after

    ig = dict(ig)
    ig["variants"] = consolidated
    return ig, stats


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Migre les axes du ingredient_tree FR→EN + consolide les variants")
    parser.add_argument("--dry-run", action="store_true", help="Simulation sans écriture")
    parser.add_argument("--verbose", action="store_true", help="Afficher les warnings par groupe")
    args = parser.parse_args()

    print("\n" + "=" * 65)
    print("  MIGRATION AXES ingredient_tree.json")
    print("=" * 65)

    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))
    cats = tree.get("categories", [])
    print(f"  {sum(len(s.get('ingredient_groups',[])) for c in cats for s in c.get('subcategories',[]))} groupes chargés")

    total_axes       = 0
    total_merged     = 0
    total_warnings   = 0
    groups_changed   = 0
    all_warnings: list[dict] = []

    new_cats = []
    for cat in cats:
        new_subs = []
        for sub in cat.get("subcategories", []):
            new_igs = []
            for ig in sub.get("ingredient_groups", []):
                new_ig, stats = process_group(ig, args.verbose)
                if stats["axes_translated"] or stats["variants_merged"]:
                    groups_changed += 1
                total_axes   += stats["axes_translated"]
                total_merged += stats["variants_merged"]
                if stats["warnings"]:
                    total_warnings += len(stats["warnings"])
                    all_warnings.append({
                        "ig_id": ig.get("id", "?"),
                        "name_en": ig.get("canonical_name_en", ""),
                        "warnings": stats["warnings"],
                    })
                    if args.verbose:
                        print(f"  [{ig.get('id')}] {ig.get('canonical_name_en')} — {len(stats['warnings'])} warnings")
                new_igs.append(new_ig)
            new_subs.append(dict(sub, ingredient_groups=new_igs))
        new_cats.append(dict(cat, subcategories=new_subs))

    tree["categories"] = new_cats

    # ── Rapport ───────────────────────────────────────────────────
    report = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": args.dry_run,
        "stats": {
            "groups_changed":    groups_changed,
            "axes_translated":   total_axes,
            "variants_merged":   total_merged,
            "total_warnings":    total_warnings,
        },
        "warnings_by_group": all_warnings,
    }

    print(f"\n{'─'*65}")
    print(f"  Groupes modifiés        : {groups_changed}")
    print(f"  Axes traduits EN        : {total_axes}")
    print(f"  Variants consolidés     : {total_merged}")
    print(f"  Warnings                : {total_warnings}")

    if args.dry_run:
        print(f"\n  [DRY-RUN] Aucune écriture.")
    else:
        TREE_FILE.write_text(json.dumps(tree, ensure_ascii=False, indent=2), encoding="utf-8")
        REPORT_FILE.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n  Tree mis à jour : {TREE_FILE.name}")
        print(f"  Rapport         : {REPORT_FILE.name}")

    print(f"\n{'='*65}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
