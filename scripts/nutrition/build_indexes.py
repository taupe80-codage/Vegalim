#!/usr/bin/env python3
"""
build_indexes.py — Reconstruction des indexes et graphs depuis nutrition_v2 + ingredients_tree
==============================================================================================
Clé de référence : SOURCE:source_id  (ex: CIQUAL:4028, CNF:501697, USDA:2644288)
Ces IDs sont les identifiants stables issus des sources officielles.

Produit :
  backend/data/indexes/nutrition_index.json
      source_id → {base, variant, valeurs nutritionnelles complètes}
  backend/data/indexes/ingredient_token_index.json
      source_id → {base, variant, ig_id, axes}
  backend/data/graphs/ingredient_availability_graph_v1.json  (synchronisé sur les clés du dico)
  backend/data/graphs/ingredient_relation_graph.json          (complète les manquants)

Usage :
  python build_indexes.py               # tous les fichiers
  python build_indexes.py --dry-run     # rapport sans écriture
  python build_indexes.py --target nutrition_index
"""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data"
N2   = DATA / "nutrition" / "processed" / "nutrition_v2.json"
TREE = DATA / "ingredients" / "ingredients_tree.json"
DICT = DATA / "ingredients" / "ingredients_dictionary.json"

OUT_NUTR_IDX  = DATA / "indexes" / "nutrition_index.json"
OUT_TOKEN_IDX = DATA / "indexes" / "ingredient_token_index.json"
OUT_AVAIL     = DATA / "graphs"  / "ingredient_availability_graph_v1.json"
OUT_RELATION  = DATA / "graphs"  / "ingredient_relation_graph.json"


# ── Helpers ───────────────────────────────────────────────────────────────────

def source_key(source: str, source_id) -> str:
    """Construit la clé canonique : 'CIQUAL:4028', 'CNF:501697', 'USDA:2644288'."""
    return f"{source}:{source_id}"


def _cat_short(tax: dict) -> str:
    cat = tax.get("cat1", "")
    mapping = {
        "fruits": "fruit", "vegetables": "vegetable",
        "legumes_and_pulses": "legume", "grains_and_cereals": "grain",
        "dairy_and_eggs": "dairy", "nuts_and_seeds": "nut",
        "oils_and_fats": "fat", "sweeteners": "sweetener",
        "beverages": "beverage", "condiments_and_sauces": "condiment",
        "herbs_and_spices": "spice", "leavening_agents_and_additives": "additive",
        "processed_foods": "processed", "prepared_dishes": "dish",
        "bread_and_bakery": "bread", "pasta_and_noodles": "pasta",
        "fungi_and_mushrooms": "mushroom", "algae_and_seaweed": "algae",
    }
    for key, short in mapping.items():
        if key in cat:
            return short
    return cat.replace("_", " ") if cat else "other"


NUTR_FIELDS = [
    "calories_kcal", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g",
    "fa_saturated_g", "fa_mufa_g", "fa_pufa_g",
    "fa_18_3_ala_g", "fa_20_5_epa_g", "fa_22_6_dha_g", "fa_18_2_linoleic_g",
    "omega3_g", "cholesterol_mg", "salt_g", "sodium_mg",
    "calcium_mg", "iron_mg", "magnesium_mg", "phosphorus_mg", "potassium_mg",
    "zinc_mg", "copper_mg", "manganese_mg", "selenium_ug",
    "retinol_ug", "beta_carotene_ug", "vitamin_d_ug", "alpha_tocopherol_mg",
    "vitamin_k1_ug", "vitamin_c_mg", "vitamin_b1_mg", "vitamin_b2_mg",
    "vitamin_b3_mg", "vitamin_b5_mg", "vitamin_b6_mg", "folate_ug",
    "vitamin_b12_ug", "alcohol_g", "water_g",
]


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_n2():
    with open(N2, encoding="utf-8") as f:
        raw = json.load(f)
    return raw["ingredients"], str(raw.get("schema_version", "?"))


def load_tree():
    with open(TREE, encoding="utf-8") as f:
        tree = json.load(f)
    igs = []
    for cat in tree.get("categories", []):
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                igs.append(ig)
    return igs


# ── Build nutrition_index ─────────────────────────────────────────────────────

def build_nutrition_index(ingrs: dict, n2_version: str) -> dict:
    """
    Clé primaire : SOURCE:source_id → valeurs nutritionnelles complètes + base/variant n2.
    """
    lookup: dict = {}

    for base, data in ingrs.items():
        tax      = data.get("taxonomy", {})
        category = _cat_short(tax)
        name_fr  = tax.get("name_fr", "")
        name_en  = tax.get("name_en", "")

        for vname, vdata in data.get("variants", {}).items():
            src    = vdata.get("_source")
            src_id = vdata.get("_source_id")
            if not src or src_id is None:
                continue

            key = source_key(src, src_id)
            entry = {
                "base":     base,
                "variant":  vname,
                "category": category,
                "name_fr":  vdata.get("name_fr") or name_fr,
                "name_en":  vdata.get("name_en") or name_en,
                "axes":     vdata.get("axes", {}),
            }
            for f in NUTR_FIELDS:
                v = vdata.get(f)
                if v is not None:
                    entry[f] = v

            lookup[key] = entry

    now = datetime.now(timezone.utc).isoformat()
    return {
        "_meta": {
            "description":       "Nutrition index — SOURCE:id → valeurs nutritionnelles",
            "version":           "3.0",
            "nutrition_version": n2_version,
            "generated_at":      now,
            "generated_by":      "build_indexes.py",
            "_generated":        True,
            "_do_not_edit":      "Fichier auto-généré — toute modification manuelle sera écrasée au prochain run du pipeline.",
            "key_format":        "SOURCE:source_id  ex: CIQUAL:4028, CNF:501697, USDA:2644288",
            "total_entries":     len(lookup),
            "by_source": {
                src: sum(1 for k in lookup if k.startswith(src + ":"))
                for src in ("CIQUAL", "CNF", "USDA")
            },
        },
        "lookup": lookup,
    }


# ── Build token_index ─────────────────────────────────────────────────────────

def build_token_index(ingrs: dict, igs: list, n2_version: str) -> dict:
    """
    Clé primaire : SOURCE:source_id → {base, variant, ig_id, ig_axes, var_axes}.
    Permet de retrouver le contexte complet (IG d'appartenance, axes) depuis un ID source.
    """
    # Index inverse : (source, source_id) → ig_id + ig_axes depuis l'arbre
    src_to_ig: dict[str, dict] = {}
    for ig in igs:
        ig_id   = ig.get("id", "")
        ig_axes = ig.get("axes_en") or ig.get("axes") or {}
        for var in ig.get("variants", []):
            src    = var.get("source")
            src_id = var.get("source_id")
            if src and src_id:
                k = source_key(src, src_id)
                src_to_ig[k] = {"ig_id": ig_id, "ig_axes": ig_axes, "var_axes": var.get("axes_en") or var.get("axes") or {}}

    index: dict = {}
    for base, data in ingrs.items():
        for vname, vdata in data.get("variants", {}).items():
            src    = vdata.get("_source")
            src_id = vdata.get("_source_id")
            if not src or src_id is None:
                continue

            key    = source_key(src, src_id)
            ig_ctx = src_to_ig.get(key, {})

            index[key] = {
                "base":     base,
                "variant":  vname,
                "ig_id":    ig_ctx.get("ig_id"),
                "ig_axes":  ig_ctx.get("ig_axes", {}),
                "var_axes": ig_ctx.get("var_axes", vdata.get("axes", {})),
            }

    now = datetime.now(timezone.utc).isoformat()
    return {
        "_meta": {
            "description":       "Token index — SOURCE:id → base/variant/IG context",
            "version":           "6.0",
            "nutrition_version": n2_version,
            "generated_at":      now,
            "generated_by":      "build_indexes.py",
            "_generated":        True,
            "_do_not_edit":      "Fichier auto-généré — toute modification manuelle sera écrasée au prochain run du pipeline.",
            "key_format":        "SOURCE:source_id  ex: CIQUAL:4028, CNF:501697, USDA:2644288",
            "total_entries":     len(index),
            "by_source": {
                src: sum(1 for k in index if k.startswith(src + ":"))
                for src in ("CIQUAL", "CNF", "USDA")
            },
            "with_ig_context": sum(1 for v in index.values() if v.get("ig_id")),
        },
        "index": index,
    }


# ── Extend availability graph ─────────────────────────────────────────────────

def build_availability() -> tuple[dict, int, list]:
    """Synchronise le graphe de disponibilité sur les clés du DICTIONNAIRE.

    Le graphe est indexé par clé d'entrée du dico (ex. 'acorn_squash_raw') —
    c'est le vocabulaire des recettes, et test_availability_couvre_tous_les_ingredients
    exige l'égalité exacte des deux jeux de clés. L'ancienne version ajoutait
    les clés de BASE nutrition_v2 ('acorn_squash') : +886 orphelines à chaque
    run (constaté en c3562f6, puis le 2026-09-14).

    Valeurs curées (available_in_france) conservées ; nouvelles clés du dico
    ajoutées à None (disponibilité à documenter) ; clés absentes du dico
    retirées.
    """
    existing: dict = {}
    if OUT_AVAIL.exists():
        with open(OUT_AVAIL, encoding="utf-8") as f:
            existing = json.load(f)
    with open(DICT, encoding="utf-8") as f:
        dico = json.load(f)

    entries: dict = {}
    for cat_label, cat in dico.get("categories", {}).items():
        for sub in cat.get("subcategories", {}).values():
            for key, entry in sub.get("ingredient_groups", {}).items():
                entries[key] = (cat_label, entry)

    out: dict = {k: v for k, v in existing.items() if k in entries}
    removed = sorted(k for k in existing if k not in entries)
    added = 0
    for key, (cat_label, entry) in entries.items():
        if key in out:
            continue
        out[key] = {
            "available_in_france": None,
            "category": _cat_short({"cat1": cat_label}),
            "name_fr":  entry.get("canonical_name_fr", ""),
        }
        added += 1
    return out, added, removed


# ── Extend relation graph ─────────────────────────────────────────────────────

def build_relation(ingrs: dict, igs: list) -> tuple[dict, int]:
    existing: dict = {}
    if OUT_RELATION.exists():
        with open(OUT_RELATION, encoding="utf-8") as f:
            existing = json.load(f)

    # Map source_key → base dans n2
    src_to_base: dict[str, str] = {}
    for base, data in ingrs.items():
        for vname, vdata in data.get("variants", {}).items():
            src    = vdata.get("_source")
            src_id = vdata.get("_source_id")
            if src and src_id is not None:
                src_to_base[source_key(src, src_id)] = base

    added = 0
    for ig in igs:
        ig_bases = []
        for var in ig.get("variants", []):
            src    = var.get("source")
            src_id = var.get("source_id")
            if src and src_id:
                b = src_to_base.get(source_key(src, src_id))
                if b and b not in ig_bases:
                    ig_bases.append(b)

        for base in ig_bases:
            if base in existing:
                continue
            relations = [
                {"type": "variant_of", "target": other}
                for other in ig_bases if other != base
            ]
            existing[base] = {"relations": relations}
            added += 1

    return existing, added


# ── Main ──────────────────────────────────────────────────────────────────────

ALL_TARGETS = ["nutrition_index", "token_index", "availability", "relation"]


def run(targets: list, dry_run: bool):
    print("Chargement des sources...")
    ingrs, n2_version = load_n2()
    igs               = load_tree()
    print(f"  nutrition_v2 v{n2_version} — {len(ingrs)} bases")
    print(f"  ingredients_tree — {len(igs)} IGs")

    def _write_atomic(path, data):
        """Écriture atomique via fichier temporaire + rename."""
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    if "nutrition_index" in targets:
        print("\nReconstruction nutrition_index (clé: SOURCE:id)...")
        ni = build_nutrition_index(ingrs, n2_version)
        m  = ni["_meta"]
        print(f"  {m['total_entries']} entrées  {m['by_source']}")
        if not dry_run:
            _write_atomic(OUT_NUTR_IDX, ni)
            print(f"  Ecrit → {OUT_NUTR_IDX}")

    if "token_index" in targets:
        print("\nReconstruction token_index (clé: SOURCE:id)...")
        ti = build_token_index(ingrs, igs, n2_version)
        m  = ti["_meta"]
        print(f"  {m['total_entries']} entrées  {m['by_source']}")
        print(f"  avec contexte IG : {m['with_ig_context']}/{m['total_entries']}")
        if not dry_run:
            _write_atomic(OUT_TOKEN_IDX, ti)
            print(f"  Ecrit → {OUT_TOKEN_IDX}")

    if "availability" in targets:
        print("\nExtension ingredient_availability_graph...")
        avail, added, removed = build_availability()
        print(f"  {len(avail)} entrées totales (+{added} nouvelles, -{len(removed)} absentes du dico)")
        if removed:
            print(f"  retirées : {removed[:10]}")
        if not dry_run:
            _write_atomic(OUT_AVAIL, avail)
            print(f"  Ecrit → {OUT_AVAIL}")

    if "relation" in targets:
        print("\nExtension ingredient_relation_graph...")
        rel, added = build_relation(ingrs, igs)
        print(f"  {len(rel)} entrées totales (+{added} nouvelles)")
        if not dry_run:
            _write_atomic(OUT_RELATION, rel)
            print(f"  Ecrit → {OUT_RELATION}")

    if dry_run:
        print("\n[DRY-RUN] Aucune écriture.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Rebuild indexes/graphs depuis nutrition_v2 + ingredients_tree"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--target", choices=ALL_TARGETS,
                        help="Cible unique (défaut: tous)")
    args    = parser.parse_args()
    targets = [args.target] if args.target else ALL_TARGETS
    run(targets, dry_run=args.dry_run)
