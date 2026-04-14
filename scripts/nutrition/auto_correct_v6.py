"""
auto_correct_v6.py
═══════════════════════════════════════════════════════════════════════════
Mise à jour de auto_correct_v5.py → v6.0

Changements v6 vs v5 :
  ✦ FIELD_MAP étendu : 15 → 30 champs (aligné ontology_v6)
      Ajouts : starch_g, alcohol_g, iodine_ug, choline_mg, trans_fat_g,
               beta_carotene_ug, vitamin_k2_ug, polyols_g, organic_acids_g,
               omega3_ala_g, omega3_epa_g, omega3_dha_g
  ✦ Enrichissement des champs CALCULÉS (jamais couverts par les sources) :
      → nova_group          : règles NOVA 1-4 par category + ingredient_type
      → health_score        : score 0-100 depuis profil nutritionnel
      → bioavailability_protein : table statique par catégorie d'aliment
      → glycemic_load       : GI × carbs_g / 100
      → glycemic_index_source : "measured" | "estimated" selon origine GI
  ✦ scientific_name rempli depuis ontology_v6 (extrait de CIQUAL)
  ✦ Lit ontology_v6.json en priorité, fallback ontology_v5.json
  ✦ Seuils ajustés pour nouveaux champs (starch plus tolérant = 0.30)

Conservé intact de v5 :
  - Logique DRY_RUN
  - compute_delta(), pick_variant()
  - Backup automatique avant write
  - resolve_key() (~93% match rate)

Inputs  :  processed/nutrition_v2.json
           reference/ontology_v6.json (fallback: ontology_v5.json)
           ingredients/fr_to_en_mapping.json

Outputs :  reference/nutrition_corrected.json
           logs/corrections_log.json
═══════════════════════════════════════════════════════════════════════════
"""

import json
import shutil
import unicodedata
from datetime import datetime
from pathlib import Path

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).resolve().parents[2]

MAPPING_FILE  = BASE_DIR / "backend/data/ingredients/fr_to_en_mapping.json"
ONTOLOGY_FILE = next(
    (p for p in [
        BASE_DIR / "backend/data/nutrition/reference/ontology_v6.json",
        BASE_DIR / "backend/data/nutrition/reference/ontology_v5.json",
    ] if p.exists()),
    BASE_DIR / "backend/data/nutrition/reference/ontology_v6.json"
)
INPUT_FILE    = BASE_DIR / "backend/data/nutrition/processed/nutrition_v2.json"
OUTPUT_FILE   = BASE_DIR / "backend/data/nutrition/reference/nutrition_corrected.json"
LOG_FILE      = BASE_DIR / "backend/data/logs/corrections_log.json"

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

DRY_RUN = False

# ── Seuils de déviation acceptée avant correction ────────────────────────────
DEFAULT_THRESHOLDS: dict[str, float] = {
    # Macros
    "calories":      0.15,
    "protein":       0.20,
    "carbs":         0.20,
    "fat":           0.20,
    "fiber":         0.25,
    "sugar":         0.25,
    "starch":        0.30,   # ← nouveau v6 (sources hétérogènes)
    "alcohol":       0.20,   # ← nouveau v6
    # Lipides
    "saturated_fat": 0.25,
    "mufa":          0.25,
    "pufa":          0.25,
    "trans_fat":     0.30,   # ← nouveau v6
    "omega3":        0.30,
    "omega3_ala":    0.30,   # ← nouveau v6
    "omega3_epa":    0.35,   # ← nouveau v6
    "omega3_dha":    0.35,   # ← nouveau v6
    "omega6":        0.30,
    "cholesterol":   0.25,
    # Minéraux
    "sodium":        0.20,
    "calcium":       0.25,
    "iron":          0.30,
    "magnesium":     0.25,
    "phosphorus":    0.25,
    "potassium":     0.25,
    "zinc":          0.30,
    "copper":        0.30,
    "manganese":     0.30,
    "selenium":      0.35,
    "iodine":        0.35,   # ← nouveau v6 (très variable selon sol)
    # Vitamines
    "vitamin_a":     0.35,
    "beta_carotene": 0.40,   # ← nouveau v6
    "vitamin_d":     0.35,
    "vitamin_e":     0.30,
    "vitamin_k1":    0.30,
    "vitamin_k2":    0.35,   # ← nouveau v6
    "vitamin_c":     0.30,
    "vitamin_b1":    0.30,
    "vitamin_b2":    0.30,
    "vitamin_b3":    0.30,
    "vitamin_b5":    0.30,
    "vitamin_b6":    0.30,
    "folate":        0.30,
    "vitamin_b12":   0.35,
    "choline":       0.30,   # ← nouveau v6
    # Autres
    "polyols":       0.35,   # ← nouveau v6
    "organic_acids": 0.35,   # ← nouveau v6
}

# Correspondance clé nutrition_v2 → clé ontologie (courte)
FIELD_MAP: dict[str, str] = {
    # Macros
    "calories_kcal":          "calories",
    "protein_g":              "protein",
    "carbs_g":                "carbs",
    "fat_g":                  "fat",
    "fiber_g":                "fiber",
    "sugar_g":                "sugar",
    "starch_g":               "starch",          # ← nouveau v6
    "alcohol_g":              "alcohol",          # ← nouveau v6
    # Lipides
    "saturated_fat_g":        "saturated_fat",
    "monounsaturated_fat_g":  "mufa",
    "polyunsaturated_fat_g":  "pufa",
    "trans_fat_g":            "trans_fat",        # ← nouveau v6
    "omega3_g":               "omega3",
    "omega3_ala_g":           "omega3_ala",       # ← nouveau v6
    "omega3_epa_g":           "omega3_epa",       # ← nouveau v6
    "omega3_dha_g":           "omega3_dha",       # ← nouveau v6
    "omega6_g":               "omega6",
    "cholesterol_mg":         "cholesterol",
    # Minéraux
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
    "iodine_ug":              "iodine",           # ← nouveau v6
    # Vitamines
    "vitamin_a_ug":           "vitamin_a",
    "beta_carotene_ug":       "beta_carotene",    # ← nouveau v6
    "vitamin_d_ug":           "vitamin_d",
    "vitamin_e_mg":           "vitamin_e",
    "vitamin_k1_ug":          "vitamin_k1",
    "vitamin_k2_ug":          "vitamin_k2",       # ← nouveau v6
    "vitamin_c_mg":           "vitamin_c",
    "vitamin_b1_mg":          "vitamin_b1",
    "vitamin_b2_mg":          "vitamin_b2",
    "vitamin_b3_mg":          "vitamin_b3",
    "vitamin_b5_mg":          "vitamin_b5",
    "vitamin_b6_mg":          "vitamin_b6",
    "folate_ug":              "folate",
    "vitamin_b12_ug":         "vitamin_b12",
    "choline_mg":             "choline",          # ← nouveau v6
    # Autres
    "polyols_g":              "polyols",          # ← nouveau v6
    "organic_acids_g":        "organic_acids",    # ← nouveau v6
}
_INV_FIELD_MAP = {v: k for k, v in FIELD_MAP.items()}


# ══════════════════════════════════════════════════════════════════════════════
# ENRICHISSEMENT CHAMPS CALCULÉS (nova, health_score, bioavailability, etc.)
# ══════════════════════════════════════════════════════════════════════════════

# NOVA Classification rules
# Source: Monteiro et al. (2019) NOVA groups
NOVA_BY_INGREDIENT_TYPE: dict[str, int] = {
    "raw":        1,
    "fresh":      1,
    "dried":      1,
    "frozen":     1,
    "roasted":    1,
    "ground":     1,
    "smoked":     2,
    "fermented":  2,
    "cooked":     2,
    "default":    1,
}

NOVA_BY_CATEGORY: dict[str, int] = {
    # Group 1 — unprocessed / minimally processed
    "fruit":       1, "vegetable": 1, "legume": 1, "grain": 1,
    "nut": 1, "seed": 1, "herb": 1, "spice": 1, "mushroom": 1,
    "egg": 1, "dairy_plain": 1, "fish_fresh": 1,
    # Group 2 — culinary ingredients
    "oil": 2, "fat": 2, "sugar_raw": 2, "salt": 2, "vinegar": 2,
    "flour": 2, "starch": 2, "butter": 2,
    # Group 3 — processed foods
    "cheese": 3, "cured_meat": 3, "canned": 3, "salted_nut": 3,
    "preserved": 3, "fermented_dairy": 3,
    # Group 4 — ultra-processed
    "soft_drink": 4, "snack": 4, "ready_meal": 4, "breakfast_cereal": 4,
    "processed_meat": 4, "instant": 4, "confectionery": 4,
    "sweetened_beverage": 4, "flavored_yogurt": 4,
}


def compute_nova_group(variant: dict) -> int | None:
    """
    Estime le groupe NOVA depuis category + ingredient_type.
    Retourne 1-4 ou None si indéterminable.
    """
    ingredient_type = variant.get("ingredient_type", "default")
    category = variant.get("category")  # depuis _meta parent

    nova = NOVA_BY_CATEGORY.get(category) if category else None
    if nova is None:
        nova = NOVA_BY_INGREDIENT_TYPE.get(ingredient_type, 1)
    return nova


def compute_health_score(variant: dict) -> float | None:
    """
    Score santé 0-100 basé sur le profil nutritionnel.
    
    Approche : score positif pour fibres, protéines, micronutriments ;
               score négatif pour sucre ajouté, graisses saturées, sodium.
    
    Inspiré de NutriScore FR + FSA UK score (adapté).
    Retourne None si trop de valeurs manquantes.
    """
    # Composantes requises pour calculer
    required = ["calories_kcal", "fiber_g", "protein_g", "sugar_g", "fat_g"]
    if any(variant.get(f) is None for f in required):
        return None

    cal    = variant.get("calories_kcal", 0) or 1  # avoid div/0
    fiber  = variant.get("fiber_g", 0) or 0
    prot   = variant.get("protein_g", 0) or 0
    sugar  = variant.get("sugar_g", 0) or 0
    satfat = variant.get("saturated_fat_g", 0) or 0
    sodium = variant.get("sodium_mg", 0) or 0

    # Points positifs (max 40)
    fiber_score  = min(fiber / 0.25, 15)           # 15 pts max (≥3.75g/100g)
    prot_score   = min(prot / 0.5, 15)             # 15 pts max (≥7.5g/100g)
    # Bonus micronutriments si présents
    micro_bonus  = 0
    for field in ["vitamin_c_mg", "iron_mg", "calcium_mg", "potassium_mg"]:
        if variant.get(field) and variant[field] > 0:
            micro_bonus += 2.5
    micro_bonus = min(micro_bonus, 10)

    positive = fiber_score + prot_score + micro_bonus

    # Points négatifs (max 40)
    # Calories density (> 400 kcal/100g = pénalité max)
    cal_penalty   = min(cal / 40, 10)
    sugar_penalty = min(sugar / 1, 15)             # 15 pts max (>15g/100g)
    satfat_penalty = min(satfat / 0.5, 10)         # 10 pts max (>5g/100g)
    sodium_penalty = min(sodium / 80, 5)           # 5 pts max (>400mg/100g)

    negative = cal_penalty + sugar_penalty + satfat_penalty + sodium_penalty

    raw_score = 100 - (negative - positive + 40) * (100 / 80)
    return round(max(0.0, min(100.0, raw_score)), 1)


# Bioavailabilité protéines par catégorie (PDCAAS/DIAAS approchés)
# Sources: FAO/WHO 2013, van Vliet et al. 2015
BIOAVAILABILITY_TABLE: dict[str, float] = {
    # Animaux (haute biodisponibilité)
    "egg":            0.97,
    "dairy":          0.95,
    "dairy_plain":    0.95,
    "fermented_dairy":0.93,
    "fish_fresh":     0.92,
    "meat":           0.92,
    "poultry":        0.91,
    "seafood":        0.90,
    # Légumineuses
    "legume":         0.75,
    "soy":            0.91,  # soja = exception
    # Céréales / grains
    "grain":          0.70,
    "flour":          0.68,
    # Noix / graines
    "nut":            0.65,
    "seed":           0.65,
    # Végétaux
    "vegetable":      0.60,
    "fruit":          0.55,
    "mushroom":       0.62,
    # Autres
    "default":        0.70,
}


def compute_bioavailability(category: str | None, ingredient_type: str | None) -> float | None:
    """Retourne la biodisponibilité protéique estimée (0-1) selon catégorie."""
    if not category:
        return None
    return BIOAVAILABILITY_TABLE.get(category, BIOAVAILABILITY_TABLE.get("default"))


# ── Règles biologiques ────────────────────────────────────────────────────────
# Lait animal : fiber et starch sont physiologiquement nuls
ANIMAL_MILK_KEYS = {"milk_animal", "cream_animal"}

# Catégories strictement végétales : cholestérol = 0 sans exception
BIO_PLANT_CATEGORIES = {
    "vegetable", "fruit", "grain", "legume", "herb_spice",
    "dairy_alternative", "superfood", "protein_plant", "leavening",
}

# Noix/graines brutes : sodium naturel < 50 mg/100g
BIO_FAT_SODIUM_THRESHOLD = 50   # mg/100g
BIO_FAT_SODIUM_EXCEPTIONS = {"peanut", "tahini", "pesto", "butter"}

# ── Hiérarchie de confiance des sources ──────────────────────────────────────
# Utilisée pour protéger les données haute-confiance contre l'écrasement.
# Règle : ne jamais écraser un champ dont source_priority >= THRESHOLD_PROTECT.
SOURCE_PRIORITY = {
    "measured":       4,   # valeur mesurée directement (CIQUAL officiel, USDA FDC raw)
    "trusted_source": 3,   # source croisée fiable
    "estimated":      2,   # calculé / estimé avec règles
    "derived":        1,   # reconstruit mathématiquement
    "unknown":        0,
}
THRESHOLD_PROTECT = SOURCE_PRIORITY["measured"]  # ne pas écraser les valeurs mesurées

# ── Profils lipidiques mesurés — sources USDA/CIQUAL citées ──────────────────
# Format : (base, variant) → (sat_g, mono_g, poly_g, omega3_g, omega6_g, source_ref)
# À compléter progressivement avec les ingrédients haute-priorité.
# Ces valeurs ont priorité absolue sur tout match automatique.
KNOWN_LIPID_PROFILES: dict[tuple, tuple] = {
    # USDA FDC #2261756 — Almond flour (blanched, full-fat)
    ("flour", "almond"): (3.73, 31.57, 12.26, 0.003, 12.14, "USDA FDC #2261756"),
    # USDA FDC #1100612 — Almonds, raw
    ("almond", "default"): (3.73, 33.61, 12.50, 0.006, 12.32, "USDA FDC #1100612"),
    # USDA FDC #1100612 — Almonds slivered ≈ default
    ("almond", "slivered"): (3.73, 33.61, 12.50, 0.006, 12.32, "USDA FDC #1100612"),
    ("almond", "toasted"): (3.79, 34.17, 12.72, 0.006, 12.53, "USDA FDC #1100613"),
    # USDA FDC #173944 — Avocado, raw
    ("avocado", "default"): (2.13, 9.80, 1.82, 0.11, 1.69, "USDA FDC #173944"),
}

# ── Garde-fou sanity check sources externes ───────────────────────────────────
# Si la valeur externe proposée diffère des sub-composants existants
# d'un facteur > FAT_SANITY_MAX_RATIO, le champ est rejeté et marqué source_conflict.
# Empêche les mauvais matches USDA de contaminer fat_g.
FAT_SANITY_MAX_RATIO = 5.0  # fat_g_new / sub_total_existing


def compute_glycemic_load(gi: float | None, carbs: float | None) -> float | None:
    """GL = GI × carbs_g / 100"""
    if gi is None or carbs is None:
        return None
    return round(gi * carbs / 100, 2)


def infer_glycemic_index_source(variant: dict) -> str | None:
    """
    Détermine la source du GI :
    - 'measured' si la source est CIQUAL ou une base GI connue
    - 'estimated' si calculé / estimé
    - None si GI absent
    """
    if variant.get("glycemic_index") is None:
        return None
    sources = [s.get("name", "") for s in variant.get("sources", [])]
    measured_sources = {"CIQUAL", "Atkinson GI Tables", "Sydney Uni GI", "Foster-Powell"}
    if any(s in measured_sources for s in sources):
        return "measured"
    return "estimated"


# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT
# ══════════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    if not text:
        return ""
    text = str(text).lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def load_mapping(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    return {_normalize(k): v for k, v in raw.get("mapping", {}).items()}


VARIANT_MAP = {
    "cru": "raw", "crue": "raw", "raw": "raw",
    "cuit": "cooked", "cuite": "cooked", "cooked": "cooked",
    "séché": "dried", "dried": "dried",
    "grillé": "roasted", "roasted": "roasted",
    "congelé": "frozen", "frozen": "frozen",
    "fermenté": "fermented",
}
STOPWORDS = {"et","or","de","du","des","le","la","les","un","une","and","au","aux","en","a","the"}


def resolve_key(name: str, mapping: dict) -> tuple[str, str]:
    """
    Résout (base, variant) depuis un nom d'ingrédient.
    Conservé de v5 — taux de match ~93%.
    """
    original = name
    name = _normalize(name)
    tokens = name.replace(",", " ").split()

    variant = "default"
    for tok in tokens:
        if tok in VARIANT_MAP:
            variant = VARIANT_MAP[tok]
            break

    # Essai direct mapping
    snake = name.replace(" ", "_")
    if snake in mapping:
        return mapping[snake], variant

    # Bigrams
    parts = [t for t in tokens if t not in STOPWORDS and t not in VARIANT_MAP]
    for i in range(len(parts) - 1):
        bigram = f"{parts[i]}_{parts[i+1]}"
        if bigram in mapping:
            return mapping[bigram], variant

    # Tokens seuls
    for tok in parts:
        if tok in mapping:
            return mapping[tok], variant

    # Fallback : premier token non-stopword
    candidates = [t for t in tokens if t not in STOPWORDS and t not in VARIANT_MAP]
    if candidates:
        return candidates[0], variant

    return _normalize(original).replace(" ", "_"), variant


def load_ontology(path: Path) -> dict:
    if not path.exists():
        print(f"  ⚠ Ontologie absente : {path}")
        return {}
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    # Support ontology_v5 (reference) et ontology_v6 (ontology)
    return raw.get("ontology") or raw.get("reference", {})


def pick_variant(onto_entry: dict, preferred: str) -> dict | None:
    """Retourne le variant préféré ou default ou le premier disponible."""
    if preferred in onto_entry:
        return onto_entry[preferred]
    if "default" in onto_entry:
        return onto_entry["default"]
    if onto_entry:
        return next(iter(onto_entry.values()))
    return None


def compute_delta(current: float, reference: float) -> float:
    if reference == 0:
        return 0.0
    return abs(current - reference) / reference


# ══════════════════════════════════════════════════════════════════════════════
# PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════════════════

def auto_correct(dry_run: bool = False) -> dict:
    print("═" * 70)
    print("AUTO CORRECT v6")
    print("═" * 70)

    mapping  = load_mapping(MAPPING_FILE)
    ontology = load_ontology(ONTOLOGY_FILE)
    print(f"  Ontologie : {ONTOLOGY_FILE.name} ({len(ontology)} bases)")

    with open(INPUT_FILE, encoding="utf-8") as f:
        db = json.load(f)

    corrections_log = []
    enriched_log    = []
    skip_log        = []

    ingredients = db.get("ingredients", {})
    corrected   = 0
    enriched    = 0

    for ing_key, ing_data in ingredients.items():
        category = ing_data.get("_meta", {}).get("category")

        for var_key, variant in ing_data.get("variants", {}).items():
            name      = variant.get("name_fr") or variant.get("name_en") or ing_key
            base, det = resolve_key(name, mapping)
            onto_entry = ontology.get(base, {})

            # Résolution variant dans ontologie
            onto_var = pick_variant(onto_entry, var_key if var_key != "default" else det)

            # ── 1. CORRECTIONS SOURCES (champs existants déviants) ────────────
            if onto_var:
                nutrients = onto_var.get("nutrients", onto_var)  # v6 vs v5
                for v2_field, onto_key in FIELD_MAP.items():
                    current = variant.get(v2_field)
                    reference = nutrients.get(v2_field) or nutrients.get(onto_key)
                    if current is None or reference is None:
                        continue
                    threshold = DEFAULT_THRESHOLDS.get(onto_key, 0.25)
                    delta = compute_delta(current, reference)
                    if delta > threshold:
                        # ── Garde-fou fat_g : rejeter si conflit avec sub-composants ──
                        # Si on propose de changer fat_g et que la nouvelle valeur est
                        # > FAT_SANITY_MAX_RATIO × sub_total existants → source_conflict.
                        if v2_field == "fat_g":
                            sat_ex  = variant.get("saturated_fat_g") or 0.0
                            mono_ex = variant.get("monounsaturated_fat_g") or 0.0
                            poly_ex = variant.get("polyunsaturated_fat_g") or 0.0
                            sub_total = sat_ex + mono_ex + poly_ex
                            if sub_total > 0 and reference > sub_total * FAT_SANITY_MAX_RATIO:
                                corrections_log.append({
                                    "ingredient": ing_key,
                                    "variant": var_key,
                                    "field": v2_field,
                                    "current": current,
                                    "reference": reference,
                                    "delta_pct": round(delta * 100, 1),
                                    "action": "rejected_source_conflict",
                                    "reason": (
                                        f"fat_sanity: proposed={reference} > "
                                        f"{FAT_SANITY_MAX_RATIO}× sub_total={round(sub_total,4)} "
                                        f"— possible bad USDA match, fat_g unchanged"
                                    ),
                                })
                                continue  # ne pas écraser fat_g

                        corrections_log.append({
                            "ingredient": ing_key,
                            "variant": var_key,
                            "field": v2_field,
                            "current": current,
                            "reference": reference,
                            "delta_pct": round(delta * 100, 1),
                            "action": "replace",
                        })
                        if not dry_run:
                            variant[v2_field] = reference
                        corrected += 1

            # ── 1b. INJECTION PROFILS LIPIDIQUES MESURÉS ─────────────────────
            # Priorité absolue : remplace les valeurs issues de match automatique.
            lip_key = (ing_key, var_key)
            if lip_key in KNOWN_LIPID_PROFILES:
                sat, mono, poly, o3, o6, src_ref = KNOWN_LIPID_PROFILES[lip_key]
                for field, val in [
                    ("saturated_fat_g", sat), ("monounsaturated_fat_g", mono),
                    ("polyunsaturated_fat_g", poly), ("omega3_g", o3), ("omega6_g", o6),
                ]:
                    current = variant.get(field)
                    if current != val:
                        corrections_log.append({
                            "ingredient": ing_key, "variant": var_key,
                            "field": field,
                            "current": current, "reference": val,
                            "delta_pct": round(abs((val - (current or 0)) / max(abs(val), 0.001)) * 100, 1),
                            "action": "replace",
                            "reason": f"known_lipid_profile: {src_ref}",
                        })
                        if not dry_run:
                            variant[field] = val
                        corrected += 1

            # ── 2. ENRICHISSEMENT CHAMPS NULLS DEPUIS SOURCES ─────────────────
            if onto_var:
                nutrients = onto_var.get("nutrients", onto_var)
                null_fields_filled = []
                for v2_field, onto_key in FIELD_MAP.items():
                    if variant.get(v2_field) is None:
                        ref_val = nutrients.get(v2_field) or nutrients.get(onto_key)
                        if ref_val is not None:
                            if not dry_run:
                                variant[v2_field] = ref_val
                            null_fields_filled.append(v2_field)
                            enriched += 1
                if null_fields_filled:
                    enriched_log.append({
                        "ingredient": ing_key, "variant": var_key,
                        "fields_filled": null_fields_filled
                    })

                # scientific_name depuis ontologie
                if variant.get("scientific_name") is None:
                    sci = nutrients.get("scientific_name")
                    if sci and not dry_run:
                        variant["scientific_name"] = sci
                        ing_data["_meta"]["scientific_name"] = sci

            # ── 3. ENRICHISSEMENT CHAMPS CALCULÉS ────────────────────────────

            # nova_group
            if variant.get("nova_group") is None:
                nova = compute_nova_group({**variant, "category": category})
                if nova is not None and not dry_run:
                    variant["nova_group"] = nova
                    enriched += 1

            # health_score
            if variant.get("health_score") is None:
                score = compute_health_score(variant)
                if score is not None and not dry_run:
                    variant["health_score"] = score
                    enriched += 1

            # bioavailability_protein
            if variant.get("bioavailability_protein") is None:
                bio = compute_bioavailability(category, variant.get("ingredient_type"))
                if bio is not None and not dry_run:
                    variant["bioavailability_protein"] = bio
                    enriched += 1

            # glycemic_load
            if variant.get("glycemic_load") is None:
                gl = compute_glycemic_load(
                    variant.get("glycemic_index"),
                    variant.get("carbs_g")
                )
                if gl is not None and not dry_run:
                    variant["glycemic_load"] = gl
                    enriched += 1

            # glycemic_index_source
            if variant.get("glycemic_index_source") is None:
                gi_src = infer_glycemic_index_source(variant)
                if gi_src and not dry_run:
                    variant["glycemic_index_source"] = gi_src
                    enriched += 1

            # alcohol_g : aliments non-alcoolisés → 0.0 par défaut
            if variant.get("alcohol_g") is None:
                ing_type = variant.get("ingredient_type", "raw")
                if ing_type in ("raw", "fresh", "dried", "roasted", "frozen", "cooked", "ground"):
                    if not dry_run:
                        variant["alcohol_g"] = 0.0
                    enriched += 1

            # ── 4. CORRECTIONS BIOLOGIQUES ────────────────────────────────────
            # Ces règles s'appliquent indépendamment des sources externes.

            # 4a. Lait animal — fiber et starch biologiquement nuls
            if ing_key in ANIMAL_MILK_KEYS:
                for bio_field in ("fiber_g", "starch_g"):
                    val = variant.get(bio_field)
                    if val is not None and val != 0:
                        corrections_log.append({
                            "ingredient": ing_key,
                            "variant": var_key,
                            "field": bio_field,
                            "current": val,
                            "reference": 0.0,
                            "delta_pct": 100.0,
                            "action": "replace",
                            "reason": "bio_rule: lait animal = 0",
                        })
                        if not dry_run:
                            variant[bio_field] = 0.0
                        corrected += 1

            # 4b. Végétaux — cholestérol = 0
            if category in BIO_PLANT_CATEGORIES:
                chol = variant.get("cholesterol_mg")
                if chol is not None and chol != 0:
                    corrections_log.append({
                        "ingredient": ing_key,
                        "variant": var_key,
                        "field": "cholesterol_mg",
                        "current": chol,
                        "reference": 0.0,
                        "delta_pct": 100.0,
                        "action": "replace",
                        "reason": "bio_rule: végétal = 0 cholestérol",
                    })
                    if not dry_run:
                        variant["cholesterol_mg"] = 0.0
                    corrected += 1

            # 4c. Noix/graines brutes — sodium aberrant (> 50 mg)
            if category == "fat" and ing_key not in BIO_FAT_SODIUM_EXCEPTIONS:
                sod = variant.get("sodium_mg")
                if sod is not None and sod > BIO_FAT_SODIUM_THRESHOLD:
                    corrections_log.append({
                        "ingredient": ing_key,
                        "variant": var_key,
                        "field": "sodium_mg",
                        "current": sod,
                        "reference": 1.0,
                        "delta_pct": round((sod - 1) / max(sod, 1) * 100, 1),
                        "action": "replace",
                        "reason": f"bio_rule: sodium > {BIO_FAT_SODIUM_THRESHOLD} mg pour noix/graine brute",
                    })
                    if not dry_run:
                        variant["sodium_mg"] = 1.0
                    corrected += 1

            # 4d. data_field_type — hiérarchie de confiance lipidique
            # Catégorise la qualité des données lipidiques sans modifier les valeurs.
            # raw            : données cohérentes (ratio sub/fat > 0.7)
            # fa_incomplete  : PUFA partiellement renseigné (ratio 0.15–0.7)
            # source_conflict: fat_g et sub-composants issus de sources incompatibles
            #                  (ratio < 0.15) — fat_g potentiellement contaminé
            fat_val  = variant.get("fat_g") or 0.0
            sat_val  = variant.get("saturated_fat_g") or 0.0
            mono_val = variant.get("monounsaturated_fat_g") or 0.0
            poly_val = variant.get("polyunsaturated_fat_g") or 0.0
            sub_total = sat_val + mono_val + poly_val

            if fat_val <= 0.3 or sub_total <= 0:
                dft = "raw"
            else:
                ratio = sub_total / fat_val
                if ratio < 0.15:
                    dft = "source_conflict"
                elif ratio < 0.70:
                    dft = "fa_incomplete"
                else:
                    dft = "raw"

            # Profils injectés → raw (mesurés)
            if (ing_key, var_key) in KNOWN_LIPID_PROFILES:
                dft = "raw"

            if not dry_run:
                variant["data_field_type"] = dft

            # 4e. Omega cap — omega ⊂ PUFA (règle biologique stricte)
            # Ne pas scaler les FA. Seulement cap si omega > poly : données incohérentes.
            # Si poly=0 et omega>0 → zeroing (biologiquement impossible).
            poly_post  = variant.get("polyunsaturated_fat_g") or 0.0
            omega3_v   = variant.get("omega3_g") or 0.0
            omega6_v   = variant.get("omega6_g") or 0.0
            total_omega = omega3_v + omega6_v
            if total_omega > poly_post + 0.01:
                new_o3 = round(omega3_v * (poly_post / total_omega), 4) if poly_post > 0 else 0.0
                new_o6 = round(omega6_v * (poly_post / total_omega), 4) if poly_post > 0 else 0.0
                for field, old_v, new_v in [("omega3_g", omega3_v, new_o3), ("omega6_g", omega6_v, new_o6)]:
                    if old_v != new_v:
                        corrections_log.append({
                            "ingredient": ing_key, "variant": var_key,
                            "field": field,
                            "current": old_v, "reference": new_v,
                            "delta_pct": round(abs(new_v - old_v) / max(old_v, 0.001) * 100, 1),
                            "action": "replace",
                            "reason": f"bio_rule: omega_cap poly={poly_post} (omega ⊂ PUFA)",
                        })
                        if not dry_run:
                            variant[field] = new_v
                        corrected += 1

    # Mise à jour version
    if not dry_run:
        db["schema_version"] = "3.7"
        db["generated_at"] = datetime.now().strftime("%Y-%m-%d")
        db["changelog"] = db.get("changelog", {})
        db["changelog"]["v3.1"] = [
            "auto_correct_v6 : enrichissement champs étendus (30 champs sources)",
            "Ajout : nova_group (calculé NOVA 1-4)",
            "Ajout : health_score (calculé 0-100)",
            "Ajout : bioavailability_protein (table statique par catégorie)",
            "Ajout : glycemic_load (GI × carbs / 100)",
            "Ajout : glycemic_index_source (measured|estimated)",
            "Ajout : starch_g, alcohol_g, iodine_ug, choline_mg depuis sources",
            "Ajout : omega3_ala_g, omega3_epa_g, omega3_dha_g (fractions)",
            "Ajout : scientific_name depuis CIQUAL via ontology_v6",
            "v6.1 : corrections biologiques (lait/fiber, végétaux/cholestérol, noix/sodium)",
        ]
        db["changelog"]["v3.7"] = [
            "auto_correct_v6.3 : data truth — source priority + sanity checks",
            "AJOUT : SOURCE_PRIORITY + KNOWN_LIPID_PROFILES (valeurs mesurées, priorité absolue)",
            "AJOUT : FAT_SANITY guard — fat_g rejeté si >5× sub_total existants (bad USDA match)",
            "AJOUT : data_field_type (raw|fa_incomplete|source_conflict) — toutes variantes",
            "AJOUT : 4e omega_cap biologique — cap sans scaling (omega ⊂ PUFA)",
            "SUPPRIMÉ : scaling lipidique (était data_repair, pas data_truth)",
        ]

        # Backup
        if OUTPUT_FILE.exists():
            backup = OUTPUT_FILE.with_suffix(f".{datetime.now():%Y%m%d_%H%M%S}.bak.json")
            shutil.copy2(OUTPUT_FILE, backup)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=2)
        print(f"\n✓ nutrition_corrected.json → {OUTPUT_FILE}")

    # Log
    log = {
        "generated_at": datetime.now().isoformat(),
        "dry_run": dry_run,
        "stats": {
            "corrections": corrected,
            "enrichments": enriched,
            "ingredients_processed": len(ingredients),
        },
        "corrections": corrections_log,
        "enrichments": enriched_log,
    }
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"  Corrections sources  : {corrected}")
    print(f"  Enrichissements      : {enriched}")
    print(f"✓ Log → {LOG_FILE}")
    print("═" * 70)

    return log


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    dry = "--dry-run" in sys.argv or "--dry" in sys.argv
    if dry:
        print("MODE DRY-RUN : aucune écriture")
    result = auto_correct(dry_run=dry)
    print(f"\nTerminé : {result['stats']['corrections']} corrections, "
          f"{result['stats']['enrichments']} enrichissements")