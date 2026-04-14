"""
build_ontology_v6.py
═══════════════════════════════════════════════════════════════════════════
FUSION build_ontology_v5.py → v6.0

Changements v6 vs v5 :
  ✦ Import collector_v2 (sources complètes + champs étendus)
  ✦ FIELD_MAP étendu : 15 → 30 champs
      Ajouts : starch_g, alcohol_g, iodine_ug, choline_mg, trans_fat_g,
               beta_carotene_ug, vitamin_k2_ug, polyols_g, organic_acids_g,
               omega3_ala_g, omega3_epa_g, omega3_dha_g
  ✦ scientific_name extrait depuis CIQUAL
  ✦ Double export conservé : ontology_v6.json + reference_db.json
  ✦ Poids source : CIQUAL=1.0 / USDA=0.85 / CNF=0.75 (inchangé)

Inputs  :  raw/usda_flat.json       (ou usda_flat_light.json si absent)
           raw/ciqual_flat.json     (ou ciqual_flat_light.json si absent)
           raw/cnf_full_v5.json     (ou cnf_v5_light.json si absent)
           ingredients/fr_to_en_mapping.json

Outputs :  reference/ontology_v6.json
           reference/ontology_v6_report.json
           reference/reference_db.json    (backward compat avec auto_correct)
═══════════════════════════════════════════════════════════════════════════
"""

import json
import math
import statistics
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CHEMINS
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR  = Path(__file__).resolve().parents[2]
DATA_DIR  = BASE_DIR / "backend/data"
RAW_DIR   = DATA_DIR / "nutrition/raw"
REF_DIR   = DATA_DIR / "nutrition/reference"

MAPPING_FILE  = DATA_DIR / "ingredients/fr_to_en_mapping.json"
OUTPUT_ONTO   = REF_DIR  / "ontology_v6.json"
OUTPUT_RPT    = REF_DIR  / "ontology_v6_report.json"
OUTPUT_REFDB  = REF_DIR  / "reference_db.json"

# ══════════════════════════════════════════════════════════════════════════════
# NUTRIMENTS — alignés sur nutrition_v2 schema v3.0 (30 champs)
# ══════════════════════════════════════════════════════════════════════════════

# Clés longues nutrition_v2 → clés courtes internes ontologie
FIELD_MAP: dict[str, str] = {
    # ── Macros ────────────────────────────────────────────────────────────────
    "calories_kcal":          "calories",
    "protein_g":              "protein",
    "fat_g":                  "fat",
    "carbs_g":                "carbs",
    "fiber_g":                "fiber",
    "sugar_g":                "sugar",
    "starch_g":               "starch",           # ← NOUVEAU (v6)
    "alcohol_g":              "alcohol",           # ← NOUVEAU (v6)
    # ── Lipides détaillés ─────────────────────────────────────────────────────
    "saturated_fat_g":        "saturated_fat",
    "monounsaturated_fat_g":  "mufa",
    "polyunsaturated_fat_g":  "pufa",
    "trans_fat_g":            "trans_fat",         # ← NOUVEAU (v6)
    "omega3_g":               "omega3",
    "omega3_ala_g":           "omega3_ala",        # ← NOUVEAU (v6)
    "omega3_epa_g":           "omega3_epa",        # ← NOUVEAU (v6)
    "omega3_dha_g":           "omega3_dha",        # ← NOUVEAU (v6)
    "omega6_g":               "omega6",
    "cholesterol_mg":         "cholesterol",
    # ── Minéraux ──────────────────────────────────────────────────────────────
    "sodium_mg":              "sodium",
    "calcium_mg":             "calcium",
    "iron_mg":                "iron",
    "magnesium_mg":           "magnesium",
    "phosphorus_mg":          "phosphorus",
    "potassium_mg":           "potassium",
    "zinc_mg":                "zinc",
    "copper_mg":              "copper",
    "manganese_mg":           "manganese",
    "selenium_ug":            "selenium",
    "iodine_ug":              "iodine",            # ← NOUVEAU (v6, source CIQUAL)
    # ── Vitamines ─────────────────────────────────────────────────────────────
    "vitamin_a_ug":           "vitamin_a",
    "beta_carotene_ug":       "beta_carotene",     # ← NOUVEAU (v6)
    "vitamin_d_ug":           "vitamin_d",
    "vitamin_e_mg":           "vitamin_e",
    "vitamin_k1_ug":          "vitamin_k1",
    "vitamin_k2_ug":          "vitamin_k2",        # ← NOUVEAU (v6, source CIQUAL)
    "vitamin_c_mg":           "vitamin_c",
    "vitamin_b1_mg":          "vitamin_b1",
    "vitamin_b2_mg":          "vitamin_b2",
    "vitamin_b3_mg":          "vitamin_b3",
    "vitamin_b5_mg":          "vitamin_b5",
    "vitamin_b6_mg":          "vitamin_b6",
    "folate_ug":              "folate",
    "vitamin_b12_ug":         "vitamin_b12",
    "choline_mg":             "choline",           # ← NOUVEAU (v6, source USDA)
    # ── Autres ────────────────────────────────────────────────────────────────
    "polyols_g":              "polyols",           # ← NOUVEAU (v6, source CIQUAL)
    "organic_acids_g":        "organic_acids",     # ← NOUVEAU (v6, source CIQUAL)
}

FIELDS = list(FIELD_MAP.values())

# Mapping inverse : clé courte → clé longue nutrition_v2
INV_FIELD_MAP = {v: k for k, v in FIELD_MAP.items()}

# Poids de confiance par source
SOURCE_WEIGHTS = {"CIQUAL": 1.0, "USDA": 0.85, "CNF": 0.75}

# ══════════════════════════════════════════════════════════════════════════════
# MAPPING VARIANTS
# ══════════════════════════════════════════════════════════════════════════════

VARIANT_MAP: dict[str, str] = {
    "cru": "raw", "crue": "raw", "crues": "raw", "crus": "raw",
    "cuit": "cooked", "cuite": "cooked", "cuites": "cooked", "cuits": "cooked",
    "séché": "dried", "séchée": "dried", "sec": "dried", "sèche": "dried",
    "grillé": "roasted", "grillée": "roasted", "torréfié": "roasted",
    "congelé": "frozen", "surgelé": "frozen",
    "fermenté": "fermented", "fumé": "smoked",
    "raw": "raw", "cooked": "cooked", "dried": "dried", "fresh": "fresh",
    "frozen": "frozen", "roasted": "roasted", "ground": "ground",
    "boiled": "cooked", "steamed": "cooked", "baked": "cooked",
}

STOPWORDS = {
    "et", "or", "with", "without", "de", "du", "des", "le", "la", "les",
    "un", "une", "and", "au", "aux", "en", "a", "the", "of", "in",
}

# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES TEXTE
# ══════════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def load_mapping(path: Path) -> dict:
    if not path.exists():
        print(f"  ⚠ Mapping absent : {path}")
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {normalize(k): v for k, v in raw.get("mapping", {}).items()}


def extract_base(name: str, mapping: dict) -> str:
    name = name.split(",")[0].strip()
    name = name.split(" ou ")[0].strip()
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


def detect_variant(name: str) -> str:
    tokens = normalize(name).replace(",", " ").split()
    for tok in tokens:
        if tok in VARIANT_MAP:
            return VARIANT_MAP[tok]
    return "default"


# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT SOURCES (via collector_v2)
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_path(full: Path, light: Path) -> Path:
    if full.exists():
        return full
    if light.exists():
        print(f"  ⚠ Version light : {light.name}")
        return light
    raise FileNotFoundError(f"Source introuvable : {full}")


def load_ciqual() -> list[dict]:
    path = _resolve_path(
        RAW_DIR / "ciqual_flat.json",
        RAW_DIR / "ciqual_flat_light.json"
    )
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("foods", [])


def load_usda() -> list[dict]:
    path = _resolve_path(
        RAW_DIR / "usda_flat.json",
        RAW_DIR / "usda_flat_light.json"
    )
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("foods", [])


def load_cnf() -> list[dict]:
    path = _resolve_path(
        RAW_DIR / "cnf_full_v5.json",
        RAW_DIR / "cnf_v5_light.json"
    )
    with open(path, encoding="utf-8") as f:
        return json.load(f).get("foods", [])


# ══════════════════════════════════════════════════════════════════════════════
# EXTRACTION CHAMPS PAR SOURCE
# ══════════════════════════════════════════════════════════════════════════════

def extract_ciqual(food: dict) -> dict[str, float | None]:
    """Extrait et normalise les champs CIQUAL → clés courtes ontologie."""
    bdl = food.get("below_detection_limit", {})
    result = {}

    # Champs nutritionnels standard
    ciqual_to_short = {
        "calories_kcal": "calories", "protein_g": "protein", "fat_g": "fat",
        "carbs_g": "carbs", "fiber_g": "fiber", "sugar_g": "sugar",
        "starch_g": "starch", "alcohol_g": "alcohol",
        "saturated_fat_g": "saturated_fat", "monounsaturated_fat_g": "mufa",
        "polyunsaturated_fat_g": "pufa", "omega3_ala_g": "omega3_ala",
        "omega3_epa_g": "omega3_epa", "omega3_dha_g": "omega3_dha",
        "omega6_linoleic_g": "omega6", "cholesterol_mg": "cholesterol",
        "sodium_mg": "sodium", "calcium_mg": "calcium", "iron_mg": "iron",
        "magnesium_mg": "magnesium", "phosphorus_mg": "phosphorus",
        "potassium_mg": "potassium", "zinc_mg": "zinc", "copper_mg": "copper",
        "manganese_mg": "manganese", "selenium_ug": "selenium",
        "iodine_ug": "iodine",
        "vitamin_a_retinol_ug": "vitamin_a", "beta_carotene_ug": "beta_carotene",
        "vitamin_d_ug": "vitamin_d", "vitamin_e_mg": "vitamin_e",
        "vitamin_k1_ug": "vitamin_k1", "vitamin_k2_ug": "vitamin_k2",
        "vitamin_c_mg": "vitamin_c", "vitamin_b1_mg": "vitamin_b1",
        "vitamin_b2_mg": "vitamin_b2", "vitamin_b3_mg": "vitamin_b3",
        "vitamin_b5_mg": "vitamin_b5", "vitamin_b6_mg": "vitamin_b6",
        "folate_ug": "folate", "vitamin_b12_ug": "vitamin_b12",
        "polyols_g": "polyols", "organic_acids_g": "organic_acids",
    }
    for src, dst in ciqual_to_short.items():
        val = food.get(src)
        if val is None and src in bdl:
            val = 0.0  # below detection = confirmed 0
        result[dst] = val

    # omega3 total
    fractions = [result.get("omega3_ala"), result.get("omega3_epa"), result.get("omega3_dha")]
    if any(v is not None for v in fractions):
        result["omega3"] = sum(v for v in fractions if v is not None)

    # scientific_name (métadonnée précieuse)
    result["_scientific_name"] = food.get("scientific_name")
    result["_source"] = "CIQUAL"
    return result


def extract_usda(food: dict) -> dict[str, float | None]:
    """Extrait et normalise les champs USDA → clés courtes ontologie."""
    usda_to_short = {
        "calories_kcal": "calories", "protein_g": "protein", "fat_g": "fat",
        "carbs_g": "carbs", "fiber_g": "fiber", "sugar_g": "sugar",
        "starch_g": "starch", "saturated_fat_g": "saturated_fat",
        "monounsaturated_fat_g": "mufa", "polyunsaturated_fat_g": "pufa",
        "trans_fat_g": "trans_fat",
        "omega3_ala_g": "omega3_ala", "omega3_epa_g": "omega3_epa",
        "omega3_dha_g": "omega3_dha", "omega6_g": "omega6",
        "cholesterol_mg": "cholesterol",
        "sodium_mg": "sodium", "calcium_mg": "calcium", "iron_mg": "iron",
        "magnesium_mg": "magnesium", "phosphorus_mg": "phosphorus",
        "potassium_mg": "potassium", "zinc_mg": "zinc", "copper_mg": "copper",
        "manganese_mg": "manganese", "selenium_ug": "selenium",
        "vitamin_a_ug": "vitamin_a", "vitamin_d_ug": "vitamin_d",
        "vitamin_e_mg": "vitamin_e", "vitamin_k_ug": "vitamin_k1",  # K total ≈ K1
        "vitamin_c_mg": "vitamin_c", "vitamin_b1_mg": "vitamin_b1",
        "vitamin_b2_mg": "vitamin_b2", "vitamin_b3_mg": "vitamin_b3",
        "vitamin_b5_mg": "vitamin_b5", "vitamin_b6_mg": "vitamin_b6",
        "folate_ug": "folate", "vitamin_b12_ug": "vitamin_b12",
        "choline_mg": "choline",
    }
    result = {}
    for src, dst in usda_to_short.items():
        result[dst] = food.get(src)

    fractions = [result.get("omega3_ala"), result.get("omega3_epa"), result.get("omega3_dha")]
    if any(v is not None for v in fractions):
        result["omega3"] = sum(v for v in fractions if v is not None)

    result["_source"] = "USDA"
    return result


def extract_cnf(food: dict) -> dict[str, float | None]:
    """Extrait les champs CNF → clés courtes ontologie."""
    nutrition = food.get("nutrition", {})
    cnf_to_short = {
        "calories_kcal": "calories", "protein_g": "protein", "fat_g": "fat",
        "carbs_g": "carbs", "fiber_g": "fiber", "sugar_g": "sugar",
        "calcium_mg": "calcium", "iron_mg": "iron", "magnesium_mg": "magnesium",
        "potassium_mg": "potassium", "sodium_mg": "sodium", "zinc_mg": "zinc",
        "vitamin_d_ug": "vitamin_d", "vitamin_c_mg": "vitamin_c",
        "vitamin_a_ug": "vitamin_a",
    }
    result = {dst: nutrition.get(src) for src, dst in cnf_to_short.items()}
    result["_source"] = "CNF"
    return result


# ══════════════════════════════════════════════════════════════════════════════
# FUSION MULTI-SOURCE (weighted average avec MAD outlier detection)
# ══════════════════════════════════════════════════════════════════════════════

def weighted_merge(entries: list[tuple[float, float]]) -> float | None:
    """
    Fusionne des valeurs (val, weight) avec détection outliers MAD.
    Conservé de v5 (éprouvé).
    """
    valid = [(v, w) for v, w in entries if v is not None and not math.isnan(v)]
    if not valid:
        return None
    if len(valid) == 1:
        return valid[0][0]

    values = [v for v, _ in valid]
    if len(values) >= 3:
        med = statistics.median(values)
        deviations = [abs(v - med) for v in values]
        mad = statistics.median(deviations) or 1e-9
        valid = [(v, w) for (v, w), dev in zip(valid, deviations) if dev / mad < 3.5]

    total_w = sum(w for _, w in valid)
    if total_w == 0:
        return None
    return sum(v * w for v, w in valid) / total_w


# ══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION ONTOLOGIE
# ══════════════════════════════════════════════════════════════════════════════

def build_ontology(mapping: dict) -> dict:
    print("Chargement des sources...")
    ciqual_foods = load_ciqual()
    usda_foods   = load_usda()
    cnf_foods    = load_cnf()

    # Index par clé normalisée
    ciqual_index = {}
    for f in ciqual_foods:
        key = normalize(f.get("description", ""))
        ciqual_index[key] = f

    usda_index = {}
    for f in usda_foods:
        key = normalize(f.get("description", ""))
        usda_index[key] = f
        base = key.split(",")[0].strip()
        if base not in usda_index:
            usda_index[base] = f

    cnf_index = {}
    for f in cnf_foods:
        for k in [f.get("id", ""), normalize(f.get("clean_name", ""))]:
            if k:
                cnf_index[k] = f
        for alias in f.get("matching", {}).get("aliases", []):
            cnf_index[normalize(alias)] = f

    # Aggrégation par base_key
    ontology: dict[str, dict[str, list]] = defaultdict(
        lambda: defaultdict(list)
    )
    scientific_names: dict[str, str] = {}

    def _add(base, variant, data, weight):
        for field in FIELDS:
            val = data.get(field)
            if val is not None:
                ontology[base][variant].append((field, val, weight))

    # CIQUAL
    print(f"Indexation CIQUAL ({len(ciqual_foods)} aliments)...")
    for food in ciqual_foods:
        base    = extract_base(food.get("description", ""), mapping)
        variant = detect_variant(food.get("description", ""))
        data    = extract_ciqual(food)
        _add(base, variant, data, SOURCE_WEIGHTS["CIQUAL"])
        # scientific_name depuis CIQUAL
        sci = data.get("_scientific_name")
        if sci and base not in scientific_names:
            scientific_names[base] = sci

    # USDA
    print(f"Indexation USDA ({len(usda_foods)} aliments)...")
    for food in usda_foods:
        base    = extract_base(food.get("description", ""), mapping)
        variant = detect_variant(food.get("description", ""))
        data    = extract_usda(food)
        _add(base, variant, data, SOURCE_WEIGHTS["USDA"])

    # CNF
    print(f"Indexation CNF ({len(cnf_foods)} aliments)...")
    for food in cnf_foods:
        base    = extract_base(food.get("clean_name", ""), mapping)
        variant = detect_variant(food.get("clean_name", ""))
        data    = extract_cnf(food)
        _add(base, variant, data, SOURCE_WEIGHTS["CNF"])

    # Fusion
    print("Fusion des sources (weighted average + MAD outlier detection)...")
    result_onto = {}
    result_refdb = {}

    for base, variants in ontology.items():
        result_onto[base] = {}
        result_refdb[base] = {}

        for variant, entries in variants.items():
            # Group by field
            by_field: dict[str, list] = defaultdict(list)
            for field, val, w in entries:
                by_field[field].append((val, w))

            merged = {}
            stats  = {}
            for field, pairs in by_field.items():
                merged_val = weighted_merge(pairs)
                merged[field] = merged_val
                if len(pairs) > 1 and merged_val is not None:
                    vals = [v for v, _ in pairs if v is not None]
                    stats[field] = {
                        "n_sources": len(pairs),
                        "min": min(vals),
                        "max": max(vals),
                        "std": statistics.stdev(vals) if len(vals) > 1 else 0,
                    }

            # Clés longues pour ontologie riche
            merged_long = {INV_FIELD_MAP.get(k, k): v for k, v in merged.items()}
            merged_long["scientific_name"] = scientific_names.get(base)

            result_onto[base][variant] = {
                "nutrients": merged_long,
                "stats": stats,
                "n_sources": len(set(e[2] for e in entries)),
            }
            result_refdb[base][variant] = merged  # clés courtes pour backward compat

    return result_onto, result_refdb, scientific_names


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    print("═" * 70)
    print("BUILD ONTOLOGY v6")
    print("═" * 70)

    REF_DIR.mkdir(parents=True, exist_ok=True)
    mapping = load_mapping(MAPPING_FILE)
    print(f"  Mapping chargé : {len(mapping)} entrées")

    onto, refdb, sci_names = build_ontology(mapping)

    # Export ontologie riche
    onto_output = {
        "schema_version": "6.0",
        "generated_at": datetime.now().isoformat(),
        "source_weights": SOURCE_WEIGHTS,
        "fields": list(FIELD_MAP.keys()),
        "total_bases": len(onto),
        "ontology": onto,
        "scientific_names": sci_names,
    }
    with open(OUTPUT_ONTO, "w", encoding="utf-8") as f:
        json.dump(onto_output, f, ensure_ascii=False, indent=2)
    print(f"\n✓ Ontologie v6 → {OUTPUT_ONTO}")

    # Rapport
    field_coverage = defaultdict(int)
    total_variants = 0
    for base, variants in onto.items():
        for variant, data in variants.items():
            total_variants += 1
            for field, val in data["nutrients"].items():
                if val is not None:
                    field_coverage[field] += 1

    report = {
        "generated_at": datetime.now().isoformat(),
        "total_bases": len(onto),
        "total_variants": total_variants,
        "field_coverage": {
            f: f"{100 * c // total_variants}%" if total_variants else "0%"
            for f, c in sorted(field_coverage.items())
        },
        "new_fields_v6": [
            "starch_g", "alcohol_g", "iodine_ug", "choline_mg", "trans_fat_g",
            "beta_carotene_ug", "vitamin_k2_ug", "polyols_g", "organic_acids_g",
            "omega3_ala_g", "omega3_epa_g", "omega3_dha_g", "scientific_name"
        ]
    }
    with open(OUTPUT_RPT, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✓ Rapport       → {OUTPUT_RPT}")

    # Export reference_db (backward compat auto_correct_v5/v6)
    refdb_output = {
        "schema_version": "6.0",
        "generated_at": datetime.now().isoformat(),
        "source_weights": SOURCE_WEIGHTS,
        "reference": refdb,
    }
    with open(OUTPUT_REFDB, "w", encoding="utf-8") as f:
        json.dump(refdb_output, f, ensure_ascii=False, indent=2)
    print(f"✓ Reference DB  → {OUTPUT_REFDB}")
    print(f"\nTotal bases : {len(onto)} | Variants : {total_variants}")
    print("═" * 70)


if __name__ == "__main__":
    main()
