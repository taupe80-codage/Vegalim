"""
_diagnose_v2.py
═══════════════════════════════════════════════════════════════════════════
FUSION de _diagnose_ontology.py + _diagnose_ontology_full.py

Changements v2 :
  ✦ Lit nutrition_v2.json (schema hiérarchique base/variant) au lieu de
      nutrition_clean.json (v1 plat — obsolète)
  ✦ Lit ontology_v5.json en priorité, fallback ontology_v4_0.json
  ✦ Sections fusionnées :
      1. Rapport ontologie + outliers
      2. Couverture champs par ingrédient (nutrition_v2)
      3. No-match détaillés avec candidats proches
      4. Stats auto-correct (corrections_log.json)
  ✦ Flag --full pour le détail complet (ex-_diagnose_ontology_full)
  ✦ Flag --section [onto|coverage|nomatch|log] pour cibler

Obsolètes remplacés :
  ✗ _diagnose_ontology.py
  ✗ _diagnose_ontology_full.py

Usage :
  python _diagnose_v2.py              # rapport complet condensé
  python _diagnose_v2.py --full       # détail no-match avec candidats
  python _diagnose_v2.py --section onto
  python _diagnose_v2.py --section nomatch
═══════════════════════════════════════════════════════════════════════════
"""

import json
import unicodedata
import argparse
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CHEMINS
# ══════════════════════════════════════════════════════════════════════════════

BASE = Path(__file__).resolve().parents[2] / "backend" / "data"

ONTO_FILE    = (
    BASE / "nutrition/reference/ontology_v5.json"
    if (BASE / "nutrition/reference/ontology_v5.json").exists()
    else BASE / "nutrition/reference/ontology_v4_0.json"
)
REPORT_FILE  = (
    BASE / "nutrition/reference/ontology_v5_report.json"
    if (BASE / "nutrition/reference/ontology_v5_report.json").exists()
    else BASE / "nutrition/reference/ontology_v4_0_report.json"
)
MAPPING_FILE = BASE / "ingredients/fr_to_en_mapping.json"
NC_FILE      = BASE / "nutrition/processed/nutrition_v2.json"
LOG_FILE     = BASE / "logs/corrections_log.json"

# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:
    if not text:
        return ""
    text = text.lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )

def load_mapping() -> dict:
    if not MAPPING_FILE.exists():
        return {}
    raw = json.loads(MAPPING_FILE.read_text(encoding="utf-8"))
    return {normalize(k): v for k, v in raw.get("mapping", {}).items()}

VARIANT_MAP = {
    "cru":"raw","crue":"raw","cuit":"cooked","cuite":"cooked",
    "raw":"raw","cooked":"cooked","dried":"dried","fresh":"fresh",
    "frozen":"frozen","roasted":"roasted","ground":"ground",
}
STOPWORDS = {"et","or","with","without","de","du","des","le","la","les",
             "un","une","and","au","aux","en","a","the","of"}

def extract_base(name: str, mapping: dict) -> str:
    name = name.split(",")[0].split(" ou ")[0].strip()
    snake = normalize(name).replace(" ", "_").replace("-", "_")
    if snake in mapping:
        return mapping[snake]
    tokens = snake.split("_")
    out, skip = [], False
    for i, tok in enumerate(tokens):
        if skip:
            skip = False
            continue
        if i + 1 < len(tokens):
            bigram = f"{tok}_{tokens[i+1]}"
            if bigram in mapping:
                out.append(mapping[bigram])
                skip = True
                continue
        if tok in mapping:
            out.append(mapping[tok])
        elif tok not in VARIANT_MAP and tok not in STOPWORDS:
            out.append(tok)
    return "_".join(t.strip("_") for t in out if t) or snake

# ══════════════════════════════════════════════════════════════════════════════
# SECTIONS
# ══════════════════════════════════════════════════════════════════════════════

def section_ontology(onto: dict, full: bool = False):
    print("═" * 60)
    print("1. RAPPORT ONTOLOGIE")
    print("═" * 60)

    if REPORT_FILE.exists():
        r = json.loads(REPORT_FILE.read_text(encoding="utf-8"))
        for k, v in r.items():
            print(f"  {k}: {v}")
    else:
        total_bases    = len(onto)
        total_variants = sum(len(v.get("variants", {})) for v in onto.values())
        print(f"  Bases    : {total_bases}")
        print(f"  Variants : {total_variants}")

    if full:
        TOP_KEYS = ["flour", "tomato", "mushroom", "beans", "kale", "rice", "lemon"]
        print(f"\n  Outliers top ingrédients :")
        for key in TOP_KEYS:
            if key not in onto:
                continue
            for var, vdata in onto[key].get("variants", {}).items():
                outliers = vdata.get("outliers", {})
                if outliers:
                    print(f"    {key}/{var}  conf={vdata.get('confidence', 0):.2f}")
                    for field, vals in outliers.items():
                        print(f"      {field}: outliers={vals}  fused={vdata.get(field)}")


def section_coverage(ings: dict):
    """Couverture des champs nutritionnels dans nutrition_v2."""
    print("\n═" * 60)
    print("2. COUVERTURE CHAMPS — nutrition_v2")
    print("═" * 60)

    # Les champs peuvent être à la racine ou dans variants.default
    ALL_FIELDS = [
        "calories_kcal","protein_g","fat_g","carbs_g","fiber_g","sugar_g",
        "vitamin_c_mg","vitamin_a_ug","vitamin_d_ug","calcium_mg","iron_mg",
        "potassium_mg","magnesium_mg","sodium_mg","zinc_mg",
    ]
    total = len(ings)

    def get_val(data, field):
        if field in data:
            return data[field]
        default = data.get("variants", {}).get("default", {})
        return default.get(field)

    for field in ALL_FIELDS:
        count = sum(1 for d in ings.values() if get_val(d, field) is not None)
        pct   = count / total * 100 if total else 0
        bar   = "█" * int(pct / 5)
        flag  = " ⚠" if pct < 50 else ""
        print(f"  {field:<22} {count:4d}/{total} ({pct:5.1f}%)  {bar}{flag}")


def section_nomatch(ings: dict, onto: dict, mapping: dict, full: bool = False):
    print("\n═" * 60)
    print("3. NO-MATCH ONTOLOGIE")
    print("═" * 60)

    onto_keys = set(onto.keys())
    no_match  = []

    for name in ings:
        base = extract_base(name, mapping)
        if base not in onto_keys:
            if full:
                candidates = [
                    k for k in onto_keys
                    if base[:4] in k or k[:4] in base or
                       (len(base.split("_")) > 0 and base.split("_")[0] in k)
                ][:3]
            else:
                candidates = []
            no_match.append((name, base, candidates))

    print(f"  No-match : {len(no_match)} / {len(ings)}")
    limit = len(no_match) if full else min(40, len(no_match))
    if full:
        print(f"\n  {'Ingrédient':<30} {'Base calculée':<35} {'Clés proches ontologie'}")
        print("  " + "-" * 90)
    for name, base, cands in sorted(no_match)[:limit]:
        if full:
            print(f"  {name:<30} {base:<35} {cands}")
        else:
            print(f"  '{name}'  =>  '{base}'")


def section_log():
    print("\n═" * 60)
    print("4. STATS AUTO-CORRECT")
    print("═" * 60)
    if not LOG_FILE.exists():
        print("  Log absent — lancer auto_correct_v5.py d'abord")
        return
    log   = json.loads(LOG_FILE.read_text(encoding="utf-8"))
    stats = log.get("stats", {})
    for k, v in stats.items():
        if k != "by_field":
            print(f"  {k}: {v}")
    bf = stats.get("by_field", {})
    if bf:
        print(f"\n  Corrections par champ :")
        for field, count in bf.items():
            if count:
                print(f"    {field:<22} {count}")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="_diagnose_v2")
    parser.add_argument("--full",    action="store_true",  help="Détail complet no-match + outliers")
    parser.add_argument("--section", choices=["onto","coverage","nomatch","log"], default=None)
    args = parser.parse_args()

    onto    = json.loads(ONTO_FILE.read_text(encoding="utf-8")) if ONTO_FILE.exists() else {}
    nc      = json.loads(NC_FILE.read_text(encoding="utf-8"))   if NC_FILE.exists()   else {}
    ings    = nc.get("ingredients", nc)
    mapping = load_mapping()

    print(f"\n  Ontologie : {ONTO_FILE.name}  ({len(onto)} bases)")
    print(f"  Nutrition : {NC_FILE.name}  ({len(ings)} ingrédients)\n")

    run_onto     = args.section in (None, "onto")
    run_coverage = args.section in (None, "coverage")
    run_nomatch  = args.section in (None, "nomatch")
    run_log      = args.section in (None, "log")

    if run_onto:
        section_ontology(onto, full=args.full)
    if run_coverage:
        section_coverage(ings)
    if run_nomatch:
        section_nomatch(ings, onto, mapping, full=args.full)
    if run_log:
        section_log()


if __name__ == "__main__":
    main()
