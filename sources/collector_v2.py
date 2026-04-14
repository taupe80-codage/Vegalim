"""
collector_v2.py
═══════════════════════════════════════════════════════════════════════════
Sources connector — version 2.0

Remplace : sources/collector.py (v1, 6 champs seulement)

Nouveautés v2 :
  ✦ Connecte aux versions COMPLÈTES des sources :
      → usda_flat.json        (Foundation Foods, ~2500 aliments)
      → ciqual_flat.json      (CIQUAL 2025, ~2800 aliments)
      → cnf_full_v5.json      (CNF Canadien v5, 3444 aliments)
  ✦ Champs étendus alignés sur nutrition_v2 schema v3.0 :
      Tous les champs existants + nouveaux :
        starch_g, alcohol_g, iodine_ug, choline_mg,
        trans_fat_g, beta_carotene_ug, vitamin_k2_ug,
        polyols_g, organic_acids_g,
        omega3_ala_g, omega3_epa_g, omega3_dha_g (split)
  ✦ scientific_name extrait de CIQUAL (présent dans la source)
  ✦ Normalisation omega3 : USDA fournit les 3 fractions séparément
  ✦ below_detection_limit géré (CIQUAL → 0.0 avec flag, pas null)

Inputs  (versions LIGHT pour dev, FULL pour prod) :
  raw/usda_flat.json          ← USDA FDC Foundation Foods
  raw/ciqual_flat.json        ← CIQUAL 2025 ANSES
  raw/cnf_full_v5.json        ← Canadian Nutrient File v5

Outputs :
  Aucun fichier — fournit des loaders Python utilisés par build_ontology_v6.py

Poids de confiance sources :
  CIQUAL  → 1.00  (référence officielle FR)
  USDA    → 0.85  (référence officielle US)
  CNF     → 0.75  (référence officielle CA)
═══════════════════════════════════════════════════════════════════════════
"""

import json
import unicodedata
from pathlib import Path
from typing import Optional

# ══════════════════════════════════════════════════════════════════════════════
# CHEMINS — adapter selon environnement
# ══════════════════════════════════════════════════════════════════════════════

BASE_DIR   = Path(__file__).resolve().parents[2]
RAW_DIR    = BASE_DIR / "backend/data/nutrition/raw"

# Versions complètes (prod)
USDA_FULL   = RAW_DIR / "usda_flat.json"
CIQUAL_FULL = RAW_DIR / "ciqual_flat.json"
CNF_FULL    = RAW_DIR / "cnf_full_v5.json"

# Versions light (dev / fallback)
USDA_LIGHT   = RAW_DIR / "usda_flat_light.json"
CIQUAL_LIGHT = RAW_DIR / "ciqual_flat_light.json"
CNF_LIGHT    = RAW_DIR / "cnf_v5_light.json"

SOURCE_WEIGHTS = {"CIQUAL": 1.0, "USDA": 0.85, "CNF": 0.75}


# ══════════════════════════════════════════════════════════════════════════════
# UTILITAIRES
# ══════════════════════════════════════════════════════════════════════════════

def normalize(text: str) -> str:
    """Normalise un texte : minuscules, sans accents, strip."""
    if not text:
        return ""
    text = str(text).lower().strip()
    return "".join(
        c for c in unicodedata.normalize("NFD", text)
        if unicodedata.category(c) != "Mn"
    )


def _resolve_path(full: Path, light: Path) -> Path:
    """Retourne la version complète si disponible, sinon light."""
    if full.exists():
        return full
    if light.exists():
        print(f"  ⚠ Version light utilisée : {light.name} (version complète absente)")
        return light
    raise FileNotFoundError(f"Source introuvable : {full} ni {light}")


# ══════════════════════════════════════════════════════════════════════════════
# MAPPING CHAMPS SOURCES → SCHEMA v3.0
# ══════════════════════════════════════════════════════════════════════════════

# Champs CIQUAL → nutrition_v2 (correspondance directe ou transformation)
CIQUAL_FIELD_MAP: dict[str, str] = {
    "calories_kcal":           "calories_kcal",
    "protein_g":               "protein_g",
    "fat_g":                   "fat_g",
    "carbs_g":                 "carbs_g",
    "fiber_g":                 "fiber_g",
    "sugar_g":                 "sugar_g",
    "starch_g":                "starch_g",          # ← manquant dans v2 (69%)
    "alcohol_g":               "alcohol_g",          # ← manquant dans v2 (99%)
    "saturated_fat_g":         "saturated_fat_g",
    "monounsaturated_fat_g":   "monounsaturated_fat_g",
    "polyunsaturated_fat_g":   "polyunsaturated_fat_g",
    "omega3_ala_g":            "omega3_ala_g",       # ← nouveau (fraction ALA)
    "omega3_epa_g":            "omega3_epa_g",       # ← nouveau (fraction EPA)
    "omega3_dha_g":            "omega3_dha_g",       # ← nouveau (fraction DHA)
    "omega6_linoleic_g":       "omega6_g",
    "cholesterol_mg":          "cholesterol_mg",
    "sodium_mg":               "sodium_mg",
    "calcium_mg":              "calcium_mg",
    "iron_mg":                 "iron_mg",
    "magnesium_mg":            "magnesium_mg",
    "phosphorus_mg":           "phosphorus_mg",
    "potassium_mg":            "potassium_mg",
    "zinc_mg":                 "zinc_mg",
    "copper_mg":               "copper_mg",
    "manganese_mg":            "manganese_mg",
    "selenium_ug":             "selenium_ug",
    "iodine_ug":               "iodine_ug",          # ← nouveau champ CIQUAL
    "vitamin_a_retinol_ug":    "vitamin_a_ug",       # retinol → RAE approx.
    "beta_carotene_ug":        "beta_carotene_ug",   # ← nouveau
    "vitamin_d_ug":            "vitamin_d_ug",
    "vitamin_e_mg":            "vitamin_e_mg",
    "vitamin_k1_ug":           "vitamin_k1_ug",
    "vitamin_k2_ug":           "vitamin_k2_ug",      # ← nouveau
    "vitamin_c_mg":            "vitamin_c_mg",
    "vitamin_b1_mg":           "vitamin_b1_mg",
    "vitamin_b2_mg":           "vitamin_b2_mg",
    "vitamin_b3_mg":           "vitamin_b3_mg",
    "vitamin_b5_mg":           "vitamin_b5_mg",
    "vitamin_b6_mg":           "vitamin_b6_mg",
    "folate_ug":               "folate_ug",
    "vitamin_b12_ug":          "vitamin_b12_ug",
    "polyols_g":               "polyols_g",          # ← nouveau
    "organic_acids_g":         "organic_acids_g",    # ← nouveau
    "scientific_name":         "scientific_name",    # ← extrait de CIQUAL !
}

# Champs USDA → nutrition_v2
USDA_FIELD_MAP: dict[str, str] = {
    "calories_kcal":           "calories_kcal",
    "protein_g":               "protein_g",
    "fat_g":                   "fat_g",
    "carbs_g":                 "carbs_g",
    "fiber_g":                 "fiber_g",
    "sugar_g":                 "sugar_g",
    "starch_g":                "starch_g",           # ← manquant dans v2
    "water_g":                 "water_g",
    "saturated_fat_g":         "saturated_fat_g",
    "monounsaturated_fat_g":   "monounsaturated_fat_g",
    "polyunsaturated_fat_g":   "polyunsaturated_fat_g",
    "trans_fat_g":             "trans_fat_g",        # ← nouveau
    "omega3_ala_g":            "omega3_ala_g",
    "omega3_epa_g":            "omega3_epa_g",
    "omega3_dha_g":            "omega3_dha_g",
    "omega6_g":                "omega6_g",
    "cholesterol_mg":          "cholesterol_mg",
    "sodium_mg":               "sodium_mg",
    "calcium_mg":              "calcium_mg",
    "iron_mg":                 "iron_mg",
    "magnesium_mg":            "magnesium_mg",
    "phosphorus_mg":           "phosphorus_mg",
    "potassium_mg":            "potassium_mg",
    "zinc_mg":                 "zinc_mg",
    "copper_mg":               "copper_mg",
    "manganese_mg":            "manganese_mg",
    "selenium_ug":             "selenium_ug",
    "vitamin_a_ug":            "vitamin_a_ug",
    "vitamin_d_ug":            "vitamin_d_ug",
    "vitamin_e_mg":            "vitamin_e_mg",
    "vitamin_k_ug":            "vitamin_k1_ug",      # USDA = K total ≈ K1
    "vitamin_c_mg":            "vitamin_c_mg",
    "vitamin_b1_mg":           "vitamin_b1_mg",
    "vitamin_b2_mg":           "vitamin_b2_mg",
    "vitamin_b3_mg":           "vitamin_b3_mg",
    "vitamin_b5_mg":           "vitamin_b5_mg",
    "vitamin_b6_mg":           "vitamin_b6_mg",
    "folate_ug":               "folate_ug",
    "vitamin_b12_ug":          "vitamin_b12_ug",
    "choline_mg":              "choline_mg",         # ← nouveau
    "portions":                "portions",
}

# Champs CNF → nutrition_v2 (CNF a moins de champs)
CNF_FIELD_MAP: dict[str, str] = {
    "calories_kcal": "calories_kcal",
    "protein_g":     "protein_g",
    "fat_g":         "fat_g",
    "carbs_g":       "carbs_g",
    "fiber_g":       "fiber_g",
    "sugar_g":       "sugar_g",
    "calcium_mg":    "calcium_mg",
    "iron_mg":       "iron_mg",
    "magnesium_mg":  "magnesium_mg",
    "potassium_mg":  "potassium_mg",
    "sodium_mg":     "sodium_mg",
    "zinc_mg":       "zinc_mg",
    "vitamin_d_ug":  "vitamin_d_ug",
    "vitamin_c_mg":  "vitamin_c_mg",
    "vitamin_a_ug":  "vitamin_a_ug",
}


# ══════════════════════════════════════════════════════════════════════════════
# LOADERS
# ══════════════════════════════════════════════════════════════════════════════

class CIQUALLoader:
    """
    Charge ciqual_flat.json (version complète ou light).
    
    Spécificités CIQUAL :
      - below_detection_limit : valeurs < seuil détection → traitées comme 0.0
      - scientific_name : présent dans la source → extrait dans v2
      - alcohol_g : toujours présent (même 0.0)
      - starch_g : ~57% des aliments renseignés
    """

    def __init__(self):
        path = _resolve_path(CIQUAL_FULL, CIQUAL_LIGHT)
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self.foods: list[dict] = raw.get("foods", [])
        self._index: dict[str, dict] = {}
        self._build_index()
        print(f"  ✓ CIQUAL chargé : {len(self.foods)} aliments")

    def _build_index(self):
        for food in self.foods:
            desc = normalize(food.get("description", ""))
            self._index[desc] = food
            # Index par nom normalisé sans ponctuation
            key2 = desc.replace(",", "").replace(".", "").replace("  ", " ").strip()
            if key2 != desc:
                self._index[key2] = food

    def lookup(self, name: str) -> Optional[dict]:
        """Cherche un aliment par nom normalisé."""
        key = normalize(name)
        return self._index.get(key)

    def extract(self, food: dict) -> dict:
        """
        Extrait tous les champs mappés vers le schema v3.0.
        Gère below_detection_limit : ces valeurs sont 0.0 (pas null).
        """
        bdl = food.get("below_detection_limit", {})
        result = {}
        for src_field, dst_field in CIQUAL_FIELD_MAP.items():
            val = food.get(src_field)
            # below_detection_limit → valeur 0.0 confirmée (traces)
            if val is None and src_field in bdl:
                val = 0.0
            result[dst_field] = val

        # omega3_g total (somme ALA+EPA+DHA si disponibles)
        ala = result.get("omega3_ala_g")
        epa = result.get("omega3_epa_g")
        dha = result.get("omega3_dha_g")
        if any(v is not None for v in [ala, epa, dha]):
            result["omega3_g"] = sum(v for v in [ala, epa, dha] if v is not None)

        result["_source"] = "CIQUAL"
        result["_weight"] = SOURCE_WEIGHTS["CIQUAL"]
        return result


class USDALoader:
    """
    Charge usda_flat.json (version complète ou light).

    Spécificités USDA :
      - omega3 en 3 fractions (ALA, EPA, DHA)
      - choline_mg présent
      - trans_fat_g présent
      - portions : liste de {unit, abbr, grams_per_unit}
      - calories_source : "direct" | "atwater_spec" | "atwater_gen"
    """

    def __init__(self):
        path = _resolve_path(USDA_FULL, USDA_LIGHT)
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self.foods: list[dict] = raw.get("foods", [])
        self._index: dict[str, dict] = {}
        self._build_index()
        print(f"  ✓ USDA chargé : {len(self.foods)} aliments")

    def _build_index(self):
        for food in self.foods:
            desc = normalize(food.get("description", ""))
            self._index[desc] = food
            # Index première partie (avant virgule)
            base = desc.split(",")[0].strip()
            if base not in self._index:
                self._index[base] = food

    def lookup(self, name: str) -> Optional[dict]:
        key = normalize(name)
        if key in self._index:
            return self._index[key]
        base = key.split(",")[0].strip()
        return self._index.get(base)

    def extract(self, food: dict) -> dict:
        result = {}
        for src_field, dst_field in USDA_FIELD_MAP.items():
            val = food.get(src_field)
            result[dst_field] = val

        # omega3_g total
        ala = result.get("omega3_ala_g")
        epa = result.get("omega3_epa_g")
        dha = result.get("omega3_dha_g")
        if any(v is not None for v in [ala, epa, dha]):
            result["omega3_g"] = sum(v for v in [ala, epa, dha] if v is not None)

        result["_source"] = "USDA"
        result["_weight"] = SOURCE_WEIGHTS["USDA"]
        result["_calories_source"] = food.get("calories_source")
        return result


class CNFLoader:
    """
    Charge cnf_full_v5.json (version complète ou light).

    Spécificités CNF :
      - Champs nutrition imbriqués sous "nutrition" {}
      - id snake_case (ex: "cheese_souffle")
      - name_fr disponible
      - diet.vegetarian disponible
      - matching.aliases disponible
    """

    def __init__(self):
        path = _resolve_path(CNF_FULL, CNF_LIGHT)
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self.foods: list[dict] = raw.get("foods", [])
        self._index: dict[str, dict] = {}
        self._build_index()
        print(f"  ✓ CNF chargé : {len(self.foods)} aliments")

    def _build_index(self):
        for food in self.foods:
            # Index par id
            fid = food.get("id", "")
            if fid:
                self._index[fid] = food
            # Index par clean_name
            clean = normalize(food.get("clean_name", ""))
            if clean:
                self._index[clean] = food
            # Index par core_name
            core = normalize(food.get("core_name", ""))
            if core and core not in self._index:
                self._index[core] = food
            # Index par aliases
            for alias in food.get("matching", {}).get("aliases", []):
                key = normalize(alias)
                if key not in self._index:
                    self._index[key] = food

    def lookup(self, name: str) -> Optional[dict]:
        key = normalize(name).replace(" ", "_")
        if key in self._index:
            return self._index[key]
        key2 = normalize(name)
        return self._index.get(key2)

    def extract(self, food: dict) -> dict:
        nutrition = food.get("nutrition", {})
        result = {}
        for src_field, dst_field in CNF_FIELD_MAP.items():
            result[dst_field] = nutrition.get(src_field)

        # Métadonnées utiles depuis CNF
        result["name_fr"] = food.get("name_fr")
        result["diet_vegetarian"] = food.get("diet", {}).get("vegetarian")

        result["_source"] = "CNF"
        result["_weight"] = SOURCE_WEIGHTS["CNF"]
        return result


# ══════════════════════════════════════════════════════════════════════════════
# INTERFACE PUBLIQUE
# ══════════════════════════════════════════════════════════════════════════════

def load_all_sources() -> tuple[CIQUALLoader, USDALoader, CNFLoader]:
    """
    Charge les 3 sources. Utilise les versions complètes si disponibles,
    les versions light sinon.
    
    Usage :
        ciqual, usda, cnf = load_all_sources()
        food_ciqual = ciqual.lookup("Avocat, cru")
        data = ciqual.extract(food_ciqual)
    """
    print("Chargement des sources nutritionnelles...")
    ciqual = CIQUALLoader()
    usda   = USDALoader()
    cnf    = CNFLoader()
    print(f"  → Total : {len(ciqual.foods) + len(usda.foods) + len(cnf.foods)} entrées sources")
    return ciqual, usda, cnf


def get_source_coverage() -> dict:
    """Retourne un résumé de la couverture des champs par source."""
    return {
        "CIQUAL": {
            "weight": SOURCE_WEIGHTS["CIQUAL"],
            "unique_fields": [
                "scientific_name", "starch_g", "alcohol_g", "iodine_ug",
                "beta_carotene_ug", "vitamin_k2_ug", "polyols_g",
                "organic_acids_g", "omega3_ala_g", "omega3_epa_g", "omega3_dha_g"
            ],
            "full_path": str(CIQUAL_FULL),
            "light_path": str(CIQUAL_LIGHT),
        },
        "USDA": {
            "weight": SOURCE_WEIGHTS["USDA"],
            "unique_fields": [
                "choline_mg", "trans_fat_g", "portions",
                "omega3_ala_g", "omega3_epa_g", "omega3_dha_g"
            ],
            "full_path": str(USDA_FULL),
            "light_path": str(USDA_LIGHT),
        },
        "CNF": {
            "weight": SOURCE_WEIGHTS["CNF"],
            "unique_fields": ["diet_vegetarian", "name_fr"],
            "note": "15 champs de base uniquement",
            "full_path": str(CNF_FULL),
            "light_path": str(CNF_LIGHT),
        },
        "computed_fields": {
            "nova_group": "Règles NOVA 1-4 (degré de transformation)",
            "health_score": "Score 0-100 calculé depuis profil nutritionnel",
            "bioavailability_protein": "Table statique par catégorie d'aliment",
            "glycemic_load": "Calculé : GI × carbs_g / 100",
            "glycemic_index_source": "Métadonnée : 'measured' | 'estimated' selon origine GI",
            "omega3_g": "Somme ALA + EPA + DHA si fractions disponibles",
        }
    }
