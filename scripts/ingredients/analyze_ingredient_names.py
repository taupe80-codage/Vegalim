#!/usr/bin/env python3
"""
scripts/ingredients/analyze_ingredient_names.py
================================================
Analyse les noms des ingredient_groups du tree en les confrontant aux noms
SOURCE (CIQUAL/USDA/CNF) pour identifier :

  1. La partie "base" du nom (invariante entre tous les variants du groupe)
  2. Les qualificateurs (tokens variables) → axes existants ou à créer
  3. Le nom simplifié proposé (EN + FR)
  4. Les qualificateurs inconnus → nouveaux axes à créer

Algorithme par groupe :
  - Récupérer les noms sources de TOUS ses variants via source_id
  - Tokeniser : "Egg, yolk, raw, fresh" → ["Egg", "yolk", "raw", "fresh"]
  - Trouver les tokens COMMUNS à tous les variants → base candidate
  - Tokens VARIABLES d'un variant à l'autre → qualificateurs (= axes)
  - Pour chaque qualificateur → mapper vers un axis type/value connu
  - Qualificateurs sans mapping → flaggés "unknown" → nouveaux axes à créer

Sorties :
  review_ingredient_names.json   ← rapport complet par groupe
  review_ingredient_names_summary.txt ← résumé stats + unknowns

Usage :
  python scripts/ingredients/analyze_ingredient_names.py
  python scripts/ingredients/analyze_ingredient_names.py --limit 50
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT        = Path(__file__).resolve().parents[2]
DATA        = ROOT / "backend/data"
TREE_FILE   = DATA / "ingredients/ingredients_tree.json"
SCHEMA_FILE = DATA / "ingredients/axes_schema.json"
N2_FILE     = DATA / "nutrition/processed/nutrition_v2.json"
RAW_DIR     = DATA / "nutrition/raw"
OUT_DIR     = ROOT / "scripts/ingredients"

CIQUAL_FILE = RAW_DIR / "Table_Ciqual_2025_FR_2025_11_03.xlsx"
USDA_FILE   = RAW_DIR / "FoodData_Central_foundation_food_json_2025-12-18.json"
CNF_FILE    = RAW_DIR / "cnf/FOOD_NAME.csv"


def load_axes_schema() -> dict:
    """Charge axes_schema.json et construit un index bidirectionnel EN↔FR."""
    schema = json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))
    axes   = schema.get("axes", {})
    # EN key → set of all FR tree keys (tree_key_fr peut être str ou list)
    en_to_fr: dict[str, set] = {}
    # Normalized FR tree key → EN canonical key
    fr_norm_to_en: dict[str, str] = {}
    for en_key, defn in axes.items():
        tree_fr = defn.get("tree_key_fr")
        if tree_fr is None:
            en_to_fr[en_key] = set()
        elif isinstance(tree_fr, list):
            en_to_fr[en_key] = set(tree_fr)
            for f in tree_fr:
                fr_norm_to_en[_strip(f)] = en_key
        else:
            en_to_fr[en_key] = {tree_fr}
            fr_norm_to_en[_strip(tree_fr)] = en_key
        fr_norm_to_en[_strip(en_key)] = en_key
    return {"axes": axes, "en_to_fr": en_to_fr, "fr_norm_to_en": fr_norm_to_en}


_SCHEMA: dict = {}  # chargé une fois dans main()


# ══════════════════════════════════════════════════════════════════════════════
# TABLE DE MAPPING QUALIFICATEUR → AXE
# Format : token (minuscule, sans accent) → (axis_type, axis_value_en)
# ══════════════════════════════════════════════════════════════════════════════

def _strip(s: str) -> str:
    """Normalise un token : minuscules, sans accents, sans ponctuation."""
    import unicodedata
    s = unicodedata.normalize("NFD", s.lower().strip())
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


# Chaque entrée : token normalisé → (axis_type, axis_value)
QUALIFIER_MAP: dict[str, tuple[str, str]] = {
    # ── cooking_state ──────────────────────────────────────────────
    "raw":               ("cooking_state", "raw"),
    "cru":               ("cooking_state", "raw"),
    "crue":              ("cooking_state", "raw"),
    "cooked":            ("cooking_state", "cooked"),
    "cuit":              ("cooking_state", "cooked"),
    "cuite":             ("cooking_state", "cooked"),
    "boiled":            ("cooking_state", "boiled"),
    "bouilli":           ("cooking_state", "boiled"),
    "bouillie":          ("cooking_state", "boiled"),
    "steamed":           ("cooking_state", "steamed"),
    "vapeur":            ("cooking_state", "steamed"),
    "fried":             ("cooking_state", "fried"),
    "frit":              ("cooking_state", "fried"),
    "frite":             ("cooking_state", "fried"),
    "deep fried":        ("cooking_state", "deep_fried"),
    "roasted":           ("cooking_state", "roasted"),
    "roti":              ("cooking_state", "roasted"),
    "rotie":             ("cooking_state", "roasted"),
    "baked":             ("cooking_state", "baked"),
    "au four":           ("cooking_state", "baked"),
    "grilled":           ("cooking_state", "grilled"),
    "grille":            ("cooking_state", "grilled"),
    "stir fried":        ("cooking_state", "stir_fried"),
    "saute":             ("cooking_state", "sauteed"),
    "sauteed":           ("cooking_state", "sauteed"),
    "poached":           ("cooking_state", "poached"),
    "poché":             ("cooking_state", "poached"),
    "poche":             ("cooking_state", "poached"),
    "braised":           ("cooking_state", "braised"),
    "braise":            ("cooking_state", "braised"),
    "pan fried":         ("cooking_state", "pan_fried"),
    "pan dried":         ("cooking_state", "pan_dried"),
    "microwaved":        ("cooking_state", "microwaved"),
    "scrambled":         ("cooking_state", "scrambled"),
    "hard boiled":       ("cooking_state", "hard_boiled"),
    "soft boiled":       ("cooking_state", "soft_boiled"),
    "dur":               ("cooking_state", "hard_boiled"),
    "a la coque":        ("cooking_state", "soft_boiled"),
    "plat":              ("cooking_state", "fried_flat"),
    "brouille":          ("cooking_state", "scrambled"),
    "omelette":          ("cooking_state", "omelette"),
    "precooked":         ("cooking_state", "precooked"),
    "precuit":           ("cooking_state", "precooked"),
    "precuite":          ("cooking_state", "precooked"),

    # ── thermal_state ──────────────────────────────────────────────
    "fresh":             ("thermal_state", "fresh"),
    "frais":             ("thermal_state", "fresh"),
    "fraiche":           ("thermal_state", "fresh"),
    "fresh herb":        ("thermal_state", "fresh"),
    "dried":             ("thermal_state", "dried"),
    "seche":             ("thermal_state", "dried"),
    "sechee":            ("thermal_state", "dried"),
    "deshydrate":        ("thermal_state", "dehydrated"),
    "dehydrated":        ("thermal_state", "dehydrated"),
    "freeze dried":      ("thermal_state", "freeze_dried"),
    "lyophilise":        ("thermal_state", "freeze_dried"),
    "frozen":            ("thermal_state", "frozen"),
    "surgele":           ("thermal_state", "frozen"),
    "congelé":           ("thermal_state", "frozen"),
    "congele":           ("thermal_state", "frozen"),
    "uht":               ("thermal_state", "uht"),
    "pasteurized":       ("thermal_state", "pasteurized"),
    "pasteurise":        ("thermal_state", "pasteurized"),
    "pasteurisé":        ("thermal_state", "pasteurized"),
    "sterilized":        ("thermal_state", "sterilized"),
    "sterilise":         ("thermal_state", "sterilized"),
    "refrigerated":      ("thermal_state", "refrigerated"),
    "rehydrated":        ("thermal_state", "rehydrated"),
    "rehydrate":         ("thermal_state", "rehydrated"),

    # ── form ───────────────────────────────────────────────────────
    "whole":             ("form", "whole"),
    "entier":            ("form", "whole"),
    "entiere":           ("form", "whole"),
    "ground":            ("form", "ground"),
    "moulu":             ("form", "ground"),
    "moulue":            ("form", "ground"),
    "powder":            ("form", "powder"),
    "poudre":            ("form", "powder"),
    "flour":             ("form", "flour"),
    "farine":            ("form", "flour"),
    "flakes":            ("form", "flakes"),
    "flocons":           ("form", "flakes"),
    "sliced":            ("form", "sliced"),
    "tranche":           ("form", "sliced"),
    "tranchee":          ("form", "sliced"),
    "diced":             ("form", "diced"),
    "coupe":             ("form", "diced"),
    "chopped":           ("form", "chopped"),
    "hache":             ("form", "chopped"),
    "pureed":            ("form", "pureed"),
    "puree":             ("form", "pureed"),
    "juice":             ("form", "juice"),
    "jus":               ("form", "juice"),
    "paste":             ("form", "paste"),
    "pate":              ("form", "paste"),
    "butter":            ("form", "butter"),
    "beurre":            ("form", "butter"),
    "oil":               ("form", "oil"),
    "huile":             ("form", "oil"),
    "cream":             ("form", "cream"),
    "creme":             ("form", "cream"),
    "extract":           ("form", "extract"),
    "extrait":           ("form", "extract"),
    "zest":              ("form", "zest"),
    "zeste":             ("form", "zest"),
    "concentrate":       ("form", "concentrated"),
    "concentre":         ("form", "concentrated"),
    "condensed":         ("form", "condensed"),
    "condense":          ("form", "condensed"),
    "spray dried":       ("form", "spray_dried"),
    "instant":           ("form", "instant"),
    "grated":            ("form", "grated"),
    "rape":              ("form", "grated"),
    "crushed":           ("form", "crushed"),
    "broye":             ("form", "crushed"),
    "minced":            ("form", "minced"),
    "emince":            ("form", "minced"),
    "pelleted":          ("form", "pelleted"),
    "rolled":            ("form", "rolled"),
    "nibs":              ("form", "nibs"),
    "meal":              ("form", "meal"),

    # ── partie (part) ──────────────────────────────────────────────
    "yolk":              ("part", "yolk"),
    "jaune":             ("part", "yolk"),
    "white":             ("part", "white"),
    "blanc":             ("part", "white"),
    "leaf":              ("part", "leaf"),
    "feuille":           ("part", "leaf"),
    "leaves":            ("part", "leaf"),
    "seed":              ("part", "seed"),
    "graine":            ("part", "seed"),
    "seeds":             ("part", "seed"),
    "graines":           ("part", "seed"),
    "root":              ("part", "root"),
    "racine":            ("part", "root"),
    "skin":              ("part", "skin"),
    "peau":              ("part", "skin"),
    "flesh":             ("part", "flesh"),
    "chair":             ("part", "flesh"),
    "peel":              ("part", "peel"),
    "pelure":            ("part", "peel"),
    "shell":             ("part", "shell"),
    "coquille":          ("part", "shell"),
    "core":              ("part", "core"),
    "stem":              ("part", "stem"),
    "tige":              ("part", "stem"),
    "bulb":              ("part", "bulb"),
    "flower":            ("part", "flower"),
    "fleur":             ("part", "flower"),
    "pod":               ("part", "pod"),
    "gousse":            ("part", "pod"),
    "kernel":            ("part", "kernel"),
    "grain":             ("part", "kernel"),
    "sprout":            ("part", "sprout"),
    "germe":             ("part", "sprout"),
    "tip":               ("part", "tip"),
    "pointe":            ("part", "tip"),
    "inner":             ("part", "inner"),
    "outer":             ("part", "outer"),
    "pitted":            ("part", "pitted"),
    "denoyaute":         ("part", "pitted"),
    "peeled":            ("part", "peeled"),
    "pele":              ("part", "peeled"),

    # ── fat_content ────────────────────────────────────────────────
    "skimmed":           ("fat_content", "skimmed"),
    "skim":              ("fat_content", "skimmed"),
    "ecreme":            ("fat_content", "skimmed"),
    "ecrémé":            ("fat_content", "skimmed"),
    "semi skimmed":      ("fat_content", "semi_skimmed"),
    "demi ecreme":       ("fat_content", "semi_skimmed"),
    "low fat":           ("fat_content", "low_fat"),
    "allege":            ("fat_content", "light"),
    "light":             ("fat_content", "light"),
    "full fat":          ("fat_content", "full_fat"),
    "whole milk":        ("fat_content", "whole"),
    "entier":            ("fat_content", "whole"),   # lait entier
    "reduced fat":       ("fat_content", "reduced_fat"),
    "fat free":          ("fat_content", "fat_free"),

    # ── seasoning / assaisonnement ─────────────────────────────────
    "unsalted":          ("seasoning", "unsalted"),
    "non sale":          ("seasoning", "unsalted"),
    "sans sel":          ("seasoning", "unsalted"),
    "salted":            ("seasoning", "salted"),
    "sale":              ("seasoning", "salted"),
    "sweetened":         ("seasoning", "sweetened"),
    "sucre":             ("seasoning", "sweetened"),
    "unsweetened":       ("seasoning", "unsweetened"),
    "nature":            ("seasoning", "plain"),
    "plain":             ("seasoning", "plain"),
    "flavored":          ("seasoning", "flavored"),
    "aromatise":         ("seasoning", "flavored"),
    "spiced":            ("seasoning", "spiced"),
    "epice":             ("seasoning", "spiced"),

    # ── treatment / traitement ─────────────────────────────────────
    "smoked":            ("treatment", "smoked"),
    "fume":              ("treatment", "smoked"),
    "cured":             ("treatment", "cured"),
    "fermented":         ("treatment", "fermented"),
    "fermente":          ("treatment", "fermented"),
    "aged":              ("treatment", "aged"),
    "affine":            ("treatment", "aged"),
    "blanched":          ("treatment", "blanched"),
    "blanchie":          ("treatment", "blanched"),
    "enriched":          ("treatment", "enriched"),
    "enrichi":           ("treatment", "enriched"),
    "fortified":         ("treatment", "fortified"),
    "fortifie":          ("treatment", "fortified"),
    "iodized":           ("treatment", "iodized"),
    "iode":              ("treatment", "iodized"),
    "bleached":          ("treatment", "bleached"),
    "refined":           ("treatment", "refined"),
    "raffine":           ("treatment", "refined"),
    "unrefined":         ("treatment", "unrefined"),
    "marinated":         ("treatment", "marinated"),
    "marine":            ("treatment", "marinated"),
    "pickled":           ("treatment", "pickled"),
    "lacto fermented":   ("treatment", "lacto_fermented"),
    "sprouted":          ("treatment", "sprouted"),
    "germe":             ("treatment", "sprouted"),
    "hulled":            ("treatment", "hulled"),
    "decortique":        ("treatment", "hulled"),
    "roasted":           ("treatment", "roasted"),   # pour grains/noix
    "grille":            ("treatment", "roasted"),
    "toasted":           ("treatment", "toasted"),
    "grille a sec":      ("treatment", "dry_roasted"),
    "dry roasted":       ("treatment", "dry_roasted"),
    "oil roasted":       ("treatment", "oil_roasted"),
    "blanched":          ("treatment", "blanched"),
    "emulsified":        ("treatment", "emulsified"),
    "homogenized":       ("treatment", "homogenized"),
    "homogeneise":       ("treatment", "homogenized"),
    "probiotic":         ("treatment", "probiotic"),
    "virgin":            ("treatment", "virgin"),
    "vierge":            ("treatment", "virgin"),
    "extra virgin":      ("treatment", "extra_virgin"),
    "extra vierge":      ("treatment", "extra_virgin"),
    "cold pressed":      ("treatment", "cold_pressed"),
    "pression a froid":  ("treatment", "cold_pressed"),
    "parboiled":         ("treatment", "parboiled"),
    "etuve":             ("treatment", "parboiled"),
    "textured":          ("treatment", "textured"),
    "texture":           ("treatment", "textured"),

    # ── packaging / conditionnement ────────────────────────────────
    "canned":            ("packaging", "canned"),
    "en conserve":       ("packaging", "canned"),
    "conserve":          ("packaging", "canned"),
    "jarred":            ("packaging", "jarred"),
    "bottled":           ("packaging", "bottled"),
    "vacuum":            ("packaging", "vacuum"),
    "sous vide":         ("packaging", "vacuum"),
    "prepackaged":       ("packaging", "prepackaged"),
    "preemballe":        ("packaging", "prepackaged"),
    "commercial":        ("packaging", "commercial"),
    "industrial":        ("packaging", "commercial"),

    # ── draining / egouttage ───────────────────────────────────────
    "drained":           ("draining", "drained"),
    "egoutte":           ("draining", "drained"),
    "in oil":            ("draining", "in_oil"),
    "a l huile":         ("draining", "in_oil"),
    "in water":          ("draining", "in_water"),
    "in brine":          ("draining", "in_brine"),
    "in syrup":          ("draining", "in_syrup"),
    "au sirop":          ("draining", "in_syrup"),
    "in vinegar":        ("draining", "in_vinegar"),

    # ── origine ────────────────────────────────────────────────────
    "chicken":           ("origin", "chicken"),
    "poule":             ("origin", "chicken"),
    "poulet":            ("origin", "chicken"),
    "cow":               ("origin", "cow"),
    "vache":             ("origin", "cow"),
    "goat":              ("origin", "goat"),
    "chevre":            ("origin", "goat"),
    "sheep":             ("origin", "sheep"),
    "brebis":            ("origin", "sheep"),
    "buffalo":           ("origin", "buffalo"),
    "bufflonne":         ("origin", "buffalo"),
    "plant":             ("origin", "plant"),
    "vegetal":           ("origin", "plant"),
    "animal":            ("origin", "animal"),
    "organic":           ("origin", "organic"),
    "bio":               ("origin", "organic"),
    "wild":              ("origin", "wild"),
    "sauvage":           ("origin", "wild"),
    "cultivated":        ("origin", "cultivated"),
    "cultive":           ("origin", "cultivated"),

    # ── ripeness / maturite ────────────────────────────────────────
    "ripe":              ("ripeness", "ripe"),
    "mur":               ("ripeness", "ripe"),
    "mure":              ("ripeness", "ripe"),
    "unripe":            ("ripeness", "unripe"),
    "vert":              ("ripeness", "unripe"),
    "overripe":          ("ripeness", "overripe"),
    "sun dried":         ("ripeness", "sun_dried"),

    # ── color (non-axe standard mais fréquent) ────────────────────
    "red":               ("color", "red"),
    "rouge":             ("color", "red"),
    "green":             ("color", "green"),
    "vert":              ("color", "green"),
    "black":             ("color", "black"),
    "noir":              ("color", "black"),
    "noire":             ("color", "black"),
    "white":             ("color", "white"),
    "blanc":             ("color", "white"),
    "blanche":           ("color", "white"),
    "yellow":            ("color", "yellow"),
    "jaune":             ("color", "yellow"),
    "purple":            ("color", "purple"),
    "violet":            ("color", "purple"),
    "orange":            ("color", "orange"),
    "pink":              ("color", "pink"),
    "rose":              ("color", "pink"),
    "golden":            ("color", "golden"),
    "dore":              ("color", "golden"),
    "brown":             ("color", "brown"),
    "brun":              ("color", "brown"),
    "dark":              ("color", "dark"),
    "fonce":             ("color", "dark"),
    "light":             ("color", "light"),

    # ── size / taille ─────────────────────────────────────────────
    "large":             ("size", "large"),
    "grand":             ("size", "large"),
    "grande":            ("size", "large"),
    "medium":            ("size", "medium"),
    "moyen":             ("size", "medium"),
    "moyenne":           ("size", "medium"),
    "small":             ("size", "small"),
    "petit":             ("size", "small"),
    "petite":            ("size", "small"),
    "baby":              ("size", "baby"),
    "mini":              ("size", "mini"),
    "giant":             ("size", "giant"),
    "cherry":            ("size", "cherry"),   # tomate cerise etc.

    # ── ripening / affinage ────────────────────────────────────────
    "young":             ("ripening", "young"),
    "jeune":             ("ripening", "young"),
    "mature":            ("ripening", "mature"),
    "aged":              ("ripening", "aged"),
    "old":               ("ripening", "old"),
    "soft":              ("ripening", "soft"),
    "hard":              ("ripening", "hard"),
    "semi hard":         ("ripening", "semi_hard"),
    "firm":              ("ripening", "firm"),

    # ── variete (variété spécifique de l'espèce) ──────────────────
    "granny smith":      ("variety", "granny_smith"),
    "golden delicious":  ("variety", "golden_delicious"),
    "fuji":              ("variety", "fuji"),
    "gala":              ("variety", "gala"),
    "basmati":           ("variety", "basmati"),
    "jasmine":           ("variety", "jasmine"),
    "arborio":           ("variety", "arborio"),
    "camargue":          ("variety", "camargue"),
    "beluga":            ("variety", "beluga"),
    "puy":               ("variety", "puy"),
    "blonde":            ("variety", "blonde"),
    "coral":             ("variety", "coral"),
    "green":             ("variety", "green"),
    "red":               ("variety", "red"),
    "black":             ("variety", "black"),
    "kidney":            ("variety", "kidney"),
    "cannellini":        ("variety", "cannellini"),
    "borlotti":          ("variety", "borlotti"),
    "flageolet":         ("variety", "flageolet"),
    "pinto":             ("variety", "pinto"),
    "navy":              ("variety", "navy"),
    "azuki":             ("variety", "azuki"),

    # ── sodium / sel ──────────────────────────────────────────────
    "low sodium":        ("sodium", "low"),
    "reduced sodium":    ("sodium", "reduced"),
    "sodium free":       ("sodium", "free"),
    "no salt added":     ("sodium", "no_added"),
    "sans sel ajoute":   ("sodium", "no_added"),
    "sodium added":      ("sodium", "added"),
    "with added sodium": ("sodium", "added"),

    # ── draining (multi-mots manquants) ──────────────────────────
    "drained and rinsed": ("draining", "drained"),
    "egoutte et rince":   ("draining", "drained"),

    # ── état cru sans virgule ─────────────────────────────────────
    "uncooked":          ("cooking_state", "raw"),
    "non cuite":         ("cooking_state", "raw"),
    "dry":               ("thermal_state", "dried"),
}

# Tokens à ignorer systématiquement (ne font ni base ni axe)
IGNORE_TOKENS = {
    "and", "et", "with", "avec", "or", "ou", "from", "de", "du", "des",
    "in", "en", "a", "an", "the", "le", "la", "les", "nfs", "n.f.s",
    "prepared", "prepare", "generic", "generique", "aliment moyen",
    "average", "moyen", "moyenne", "type", "similar", "similaire",
    "product", "produit", "ingredient", "food", "aliment",
    "not further specified", "non specifie",
    # Préfixes de catégorie CNF souvent redondants
    "spices", "epices", "vegetable oil", "huile vegetale",
    "fluid", "liquide", "grains", "grains cerealiers",
}


# ══════════════════════════════════════════════════════════════════════════════
# CHARGEMENT SOURCES
# ══════════════════════════════════════════════════════════════════════════════

def load_ciqual() -> dict[str, str]:
    """alim_code (str) → alim_nom_fr"""
    try:
        import openpyxl
        wb  = openpyxl.load_workbook(str(CIQUAL_FILE), read_only=True, data_only=True)
        ws  = wb.active
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            return {}
        header = [str(c).strip() if c else "" for c in rows[0]]
        try:
            i_code = header.index("alim_code")
            i_name = header.index("alim_nom_fr")
        except ValueError:
            # Fallback positions historiques
            i_code, i_name = 6, 7
        result = {}
        for row in rows[1:]:
            if row and len(row) > max(i_code, i_name):
                code = str(row[i_code]).strip() if row[i_code] is not None else ""
                name = str(row[i_name]).strip() if row[i_name] is not None else ""
                if code and name:
                    result[code] = name
        print(f"  CIQUAL chargé : {len(result)} entrées")
        return result
    except Exception as e:
        print(f"  CIQUAL ERREUR : {e}")
        return {}


def load_usda() -> dict[str, str]:
    """fdcId (str) → description EN"""
    try:
        with open(USDA_FILE, encoding="utf-8") as f:
            data = json.load(f)
        foods  = data.get("FoundationFoods", data.get("foods", []))
        result = {str(fd["fdcId"]): fd.get("description", "") for fd in foods if fd.get("fdcId")}
        print(f"  USDA chargé : {len(result)} entrées")
        return result
    except Exception as e:
        print(f"  USDA ERREUR : {e}")
        return {}


def load_cnf() -> dict[str, dict]:
    """FoodID (str) → {en: FoodDescription, fr: FoodDescriptionF}"""
    try:
        result = {}
        with open(CNF_FILE, encoding="utf-8-sig", errors="replace") as f:
            reader = csv.DictReader(f)
            for row in reader:
                fid = str(row.get("FoodID", row.get("﻿FoodID", ""))).strip()
                if fid:
                    result[fid] = {
                        "en": row.get("FoodDescription", "").strip(),
                        "fr": row.get("FoodDescriptionF", "").strip(),
                    }
        print(f"  CNF chargé : {len(result)} entrées")
        return result
    except Exception as e:
        print(f"  CNF ERREUR : {e}")
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# TOKENISATION ET ANALYSE
# ══════════════════════════════════════════════════════════════════════════════

def _strip_parens(s: str) -> str:
    """Retire le contenu entre parenthèses (synonymes CIQUAL)."""
    return re.sub(r"\([^)]*\)", "", s).strip()


def tokenize(name: str) -> list[str]:
    """Découpe un nom source sur les virgules, normalise chaque token.
    Retire d'abord le contenu entre parenthèses (variantes CIQUAL)."""
    name = _strip_parens(name)
    return [_strip(t) for t in re.split(r",\s*", name) if _strip(t)]


def tokenize_display(name: str) -> list[str]:
    """Même découpe que tokenize() mais conserve les caractères originaux
    (pour reconstruire les noms FR lisibles sans perdre les apostrophes)."""
    name = _strip_parens(name)
    return [t.strip() for t in re.split(r",\s*", name) if t.strip()]


def classify_tokens(tokens: list[str]) -> tuple[list[str], list[tuple]]:
    """
    Classe chaque token comme :
      - base_token (pas dans QUALIFIER_MAP, pas ignoré)
      - qualifier  (dans QUALIFIER_MAP → axis_type, axis_value)
    Retourne (base_tokens, [(token, axis_type, axis_value), ...])
    """
    base, quals = [], []
    # Essai des bi-grams et tri-grams d'abord
    i = 0
    while i < len(tokens):
        matched = False
        # Tenter tri-gram
        if i + 2 < len(tokens):
            tri = tokens[i] + " " + tokens[i+1] + " " + tokens[i+2]
            if tri in QUALIFIER_MAP:
                quals.append((tri, *QUALIFIER_MAP[tri]))
                i += 3
                matched = True
        if not matched and i + 1 < len(tokens):
            bi = tokens[i] + " " + tokens[i+1]
            if bi in QUALIFIER_MAP:
                quals.append((bi, *QUALIFIER_MAP[bi]))
                i += 2
                matched = True
        if not matched:
            tok = tokens[i]
            if tok in IGNORE_TOKENS:
                i += 1
            elif tok in QUALIFIER_MAP:
                quals.append((tok, *QUALIFIER_MAP[tok]))
                i += 1
            else:
                base.append(tok)
                i += 1
    return base, quals


def source_names_for_variant(vr: dict, ciqual: dict, usda: dict, cnf: dict) -> dict:
    """Retourne les noms sources disponibles pour un variant du tree."""
    src    = vr.get("source", "")
    sid    = str(vr.get("source_id", "")).strip()
    result: dict = {}

    if src == "CIQUAL" and sid in ciqual:
        result["fr"] = ciqual[sid]
    elif src == "USDA" and sid in usda:
        result["en"] = usda[sid]
    elif src == "CNF" and sid in cnf:
        entry = cnf[sid]
        if entry.get("en"): result["en"] = entry["en"]
        if entry.get("fr"): result["fr"] = entry["fr"]

    return result


def analyze_group(ig: dict, ciqual: dict, usda: dict, cnf: dict) -> dict:
    """
    Analyse un ingredient_group : retourne le rapport pour ce groupe.
    """
    ig_id     = ig.get("id", "")
    name_en   = ig.get("canonical_name_en") or ""
    name_fr   = ig.get("canonical_name_fr") or ""
    variants  = ig.get("variants", [])
    tree_axes = ig.get("axes", {})   # axes documentés au niveau du groupe

    # ── Collecter les noms sources par variant ────────────────────
    variant_data = []
    for vr in variants:
        src_names = source_names_for_variant(vr, ciqual, usda, cnf)
        entry = {
            "variant_id":  vr.get("id", ""),
            "source":      vr.get("source", ""),
            "source_id":   str(vr.get("source_id", "")),
            "tree_axes":   vr.get("axes", {}),
            "source_names": src_names,
            "tokens_en":   tokenize(src_names.get("en", "")),
            "tokens_fr":   tokenize(src_names.get("fr", "")),
        }
        # Classer les tokens
        base_en, quals_en = classify_tokens(entry["tokens_en"])
        base_fr, quals_fr = classify_tokens(entry["tokens_fr"])
        entry["base_tokens_en"]  = base_en
        entry["base_tokens_fr"]  = base_fr
        entry["qualifiers_en"]   = quals_en   # [(token, axis_type, axis_value)]
        entry["qualifiers_fr"]   = quals_fr
        variant_data.append(entry)

    # ── Calculer base commune (tokens présents dans TOUS les variants) ─
    def common_base(key: str) -> list[str]:
        all_bases = [set(vd[key]) for vd in variant_data if vd[key]]
        if not all_bases:
            return []
        common = all_bases[0]
        for s in all_bases[1:]:
            common = common & s
        # Réordonner selon le premier variant
        if variant_data:
            ordered = [t for t in variant_data[0][key] if t in common]
            return ordered
        return list(common)

    common_en = common_base("base_tokens_en")
    common_fr = common_base("base_tokens_fr")

    # ── Proposer le nom simplifié ─────────────────────────────────
    def to_name(tokens: list[str]) -> str:
        return " ".join(t.capitalize() if i == 0 else t for i, t in enumerate(tokens))

    # EN : dériver depuis les tokens sources communs (source EN fiable)
    proposed_en = to_name(common_en) if common_en else ""
    if not proposed_en:
        toks = tokenize(name_en)
        base, _ = classify_tokens(toks)
        proposed_en = to_name(base) if base else name_en

    # FR : partir du canonical_name_fr du tree, en préférant le nom entre parenthèses
    # (CIQUAL place souvent le nom commun usuel entre parenthèses, ex. "oeuf, blanc (blanc d'oeuf)")
    all_qualifier_norm = set()
    for vd in variant_data:
        for tok, _, _ in vd.get("qualifiers_en", []) + vd.get("qualifiers_fr", []):
            all_qualifier_norm.add(_strip(tok))

    def _simplify_fr(source: str) -> str:
        """Retire les qualificateurs d'un nom FR, conserve les apostrophes."""
        toks = tokenize_display(source)
        base = [t for t in toks if _strip(t) not in all_qualifier_norm and _strip(t) not in IGNORE_TOKENS]
        if not base:
            return source
        first = base[0]
        result = first[0].upper() + first[1:] if first else ""
        if len(base) > 1:
            result += ", " + ", ".join(base[1:])
        return result

    def _paren_is_usable(content: str) -> bool:
        """Renvoie False si le contenu entre parenthèses est un nom scientifique, anglais ou étranger.
        On garde uniquement les noms manifestement français : avec accents ou apostrophe de génitif."""
        c = content.strip()
        # Noms scientifiques : contiennent "sp.", "var.", "cf.", "ssp.", un point, etc.
        if re.search(r'\bsp\b|\bvar\b|\bssp\b|\.', c):
            return False
        # Trop court (initiale, code)
        if len(c) < 3:
            return False
        # Marqueur français : apostrophe de génitif (d', l', j'…) ou caractère accentué
        has_french_marker = "'" in c or any(ord(ch) > 127 for ch in c)
        return has_french_marker

    paren_match = re.search(r'\(([^)]+)\)', name_fr)
    if paren_match and _paren_is_usable(paren_match.group(1)):
        # Priorité au nom usuel entre parenthèses — souvent le nom commun simplifié
        proposed_fr = _simplify_fr(paren_match.group(1).strip())
    else:
        proposed_fr = _simplify_fr(name_fr)

    # ── Collecter tous les axes suggérés ─────────────────────────
    all_axes_en: dict[str, list] = defaultdict(list)  # axis_type → [values]
    all_axes_fr: dict[str, list] = defaultdict(list)
    for vd in variant_data:
        for tok, atype, aval in vd["qualifiers_en"]:
            if aval not in all_axes_en[atype]:
                all_axes_en[atype].append(aval)
        for tok, atype, aval in vd["qualifiers_fr"]:
            if aval not in all_axes_fr[atype]:
                all_axes_fr[atype].append(aval)

    # Axes suggérés = union EN + FR
    axes_suggested: dict[str, list] = {}
    all_types = set(all_axes_en.keys()) | set(all_axes_fr.keys())
    for atype in all_types:
        vals = list(dict.fromkeys(all_axes_en.get(atype, []) + all_axes_fr.get(atype, [])))
        axes_suggested[atype] = vals

    # ── Qualifier les axes : existants dans le tree vs nouveaux ──
    # On consulte le schema pour résoudre la correspondance FR↔EN
    fr_norm_to_en = _SCHEMA.get("fr_norm_to_en", {})
    schema_axes   = set(_SCHEMA.get("axes", {}).keys())   # axes EN connus du schema

    # Clés d'axes présentes sur ce groupe/variants (FR ou EN)
    axes_on_group: set[str] = set(tree_axes.keys())
    for vr in variants:
        axes_on_group.update(vr.get("axes", {}).keys())

    # Résoudre chaque clé présente → EN canonique via schema
    axes_resolved_en: set[str] = set()
    for raw_key in axes_on_group:
        norm = _strip(raw_key)
        en = fr_norm_to_en.get(norm) or (raw_key if raw_key in schema_axes else None)
        if en:
            axes_resolved_en.add(en)

    axes_confirmed = {}   # axes suggérés dont l'équivalent existe dans le tree (FR ou EN)
    axes_new       = {}   # axes suggérés ABSENTS du schema (vraiment nouveaux)
    axes_rename    = {}   # axes qui existent en FR dans le tree mais pas encore en EN
    for atype, vals in axes_suggested.items():
        if atype in axes_resolved_en:
            axes_confirmed[atype] = vals   # axe déjà présent sur ce groupe
        elif atype in schema_axes:
            axes_rename[atype] = vals      # connu du schema, pas encore sur ce groupe
        else:
            axes_new[atype] = vals         # vraiment nouveau, absent du schema

    # ── Tokens inconnus (ni base ni qualifier mappé) ──────────────
    unknown_tokens_en = []
    unknown_tokens_fr = []
    for vd in variant_data:
        src_en = vd.get("source_names", {}).get("en", "")
        src_fr = vd.get("source_names", {}).get("fr", "")
        if src_en:
            toks = tokenize(src_en)
            base, quals = classify_tokens(toks)
            extra = [t for t in base if t not in common_en and t not in IGNORE_TOKENS]
            unknown_tokens_en.extend(extra)
        if src_fr:
            toks = tokenize(src_fr)
            base, quals = classify_tokens(toks)
            extra = [t for t in base if t not in common_fr and t not in IGNORE_TOKENS]
            unknown_tokens_fr.extend(extra)

    # Dédupliquer
    unknown_tokens_en = list(dict.fromkeys(unknown_tokens_en))
    unknown_tokens_fr = list(dict.fromkeys(unknown_tokens_fr))

    # ── Déterminer si le nom a changé ─────────────────────────────
    name_changed = (
        _strip(proposed_en) != _strip(name_en) or
        _strip(proposed_fr) != _strip(name_fr)
    )

    # ── Données par variant pour le rapport ───────────────────────
    variants_report = []
    for vd in variant_data:
        variants_report.append({
            "variant_id":   vd["variant_id"],
            "source":       vd["source"],
            "source_id":    vd["source_id"],
            "source_names": vd["source_names"],
            "tree_axes":    vd["tree_axes"],
            "qualifiers_mapped_en": [
                {"token": q[0], "axis_type": q[1], "axis_value": q[2]}
                for q in vd["qualifiers_en"]
            ],
            "qualifiers_mapped_fr": [
                {"token": q[0], "axis_type": q[1], "axis_value": q[2]}
                for q in vd["qualifiers_fr"]
            ],
        })

    return {
        "ig_id":          ig_id,
        "current_name_en": name_en,
        "current_name_fr": name_fr,
        "proposed_name_en": proposed_en,
        "proposed_name_fr": proposed_fr,
        "name_changed":   name_changed,
        "nb_variants":    len(variants),
        "nb_variants_with_source": sum(1 for vd in variant_data if vd["source_names"]),
        "axes_tree":      dict(tree_axes),
        "axes_confirmed": axes_confirmed,  # EN key déjà présent sur ce groupe (FR ou EN)
        "axes_rename":    axes_rename,     # EN key dans schema mais pas encore sur ce groupe
        "axes_new":       axes_new,        # vraiment absent du schema → à créer
        "unknown_tokens_en": unknown_tokens_en,
        "unknown_tokens_fr": unknown_tokens_fr,
        "variants":       variants_report,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main() -> int:
    parser = argparse.ArgumentParser(description="Analyse les noms des ingredient_groups vs sources")
    parser.add_argument("--limit", type=int, default=0, help="Limiter à N groupes (debug)")
    parser.add_argument("--cat",   type=str, default="",  help="Filtrer sur une catégorie")
    args = parser.parse_args()

    print("\n" + "="*65)
    print("  ANALYSE NOMS INGRÉDIENTS — tree vs CIQUAL/USDA/CNF")
    print("="*65)

    # ── Chargement ────────────────────────────────────────────────
    global _SCHEMA
    print("\nChargement axes_schema :")
    _SCHEMA = load_axes_schema()
    print(f"  {len(_SCHEMA['axes'])} axes définis dans le schema")

    print("\nChargement sources :")
    ciqual = load_ciqual()
    usda   = load_usda()
    cnf    = load_cnf()

    print("\nChargement tree :")
    tree = json.loads(TREE_FILE.read_text(encoding="utf-8"))
    cats = tree.get("categories", [])
    print(f"  {len(cats)} catégories")

    # ── Analyse par groupe ────────────────────────────────────────
    print("\nAnalyse des groupes...")
    all_reports  = []
    total_groups = 0
    processed    = 0

    for cat in cats:
        cat_label = cat.get("label", "")
        if args.cat and args.cat.lower() not in cat_label.lower():
            continue
        for sub in cat.get("subcategories", []):
            for ig in sub.get("ingredient_groups", []):
                total_groups += 1
                if args.limit and processed >= args.limit:
                    continue
                report = analyze_group(ig, ciqual, usda, cnf)
                report["category"]    = cat_label
                report["subcategory"] = sub.get("label", "")
                all_reports.append(report)
                processed += 1

    # ── Statistiques ──────────────────────────────────────────────
    changed          = [r for r in all_reports if r["name_changed"]]
    with_source      = [r for r in all_reports if r["nb_variants_with_source"] > 0]
    with_new_axes    = [r for r in all_reports if r["axes_new"]]
    with_rename_axes = [r for r in all_reports if r["axes_rename"]]
    with_unknown_tok = [r for r in all_reports if r["unknown_tokens_en"] or r["unknown_tokens_fr"]]

    # Collecter axes vraiment nouveaux (absents du schema)
    all_new_axes: dict[str, set] = defaultdict(set)
    for r in with_new_axes:
        for atype, vals in r["axes_new"].items():
            all_new_axes[atype].update(vals)

    # Collecter axes à ajouter sur des groupes (dans schema, pas encore sur le groupe)
    all_rename_axes: dict[str, set] = defaultdict(set)
    for r in with_rename_axes:
        for atype, vals in r["axes_rename"].items():
            all_rename_axes[atype].update(vals)

    # Collecter tous les tokens inconnus
    all_unknowns_en: dict[str, int] = defaultdict(int)
    all_unknowns_fr: dict[str, int] = defaultdict(int)
    for r in all_reports:
        for t in r["unknown_tokens_en"]: all_unknowns_en[t] += 1
        for r2 in [r]:
            for t in r2["unknown_tokens_fr"]: all_unknowns_fr[t] += 1

    # ── Écriture rapport JSON ─────────────────────────────────────
    out_json = OUT_DIR / "review_ingredient_names.json"
    report_data = {
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "stats": {
            "total_groups_in_tree":   total_groups,
            "groups_analyzed":        processed,
            "groups_with_source":     len(with_source),
            "names_changed":          len(changed),
            "groups_with_axes_to_add_en": len(with_rename_axes),
            "groups_with_truly_new_axes": len(with_new_axes),
            "groups_with_unknown_tokens": len(with_unknown_tok),
        },
        "axes_to_add_en":  {k: sorted(v) for k, v in sorted(all_rename_axes.items())},
        "axes_truly_new":  {k: sorted(v) for k, v in sorted(all_new_axes.items())},
        "new_axes_suggested": {k: sorted(v) for k, v in sorted(all_new_axes.items())},
        "unknown_tokens_en_frequency": dict(sorted(all_unknowns_en.items(), key=lambda x: -x[1])[:50]),
        "unknown_tokens_fr_frequency": dict(sorted(all_unknowns_fr.items(), key=lambda x: -x[1])[:50]),
        "groups": all_reports,
    }
    out_json.write_text(json.dumps(report_data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n  Rapport JSON    : {out_json.name}")

    # ── Écriture résumé texte ─────────────────────────────────────
    out_txt = OUT_DIR / "review_ingredient_names_summary.txt"
    lines   = [
        "ANALYSE NOMS INGRÉDIENTS — tree vs CIQUAL/USDA/CNF",
        "=" * 65,
        f"  Groupes dans le tree          : {total_groups}",
        f"  Groupes analysés              : {processed}",
        f"  Groupes avec source trouvée   : {len(with_source)}",
        f"  Noms à simplifier             : {len(changed)}",
        f"  Groupes avec équivalent EN à ajouter : {len(with_rename_axes)} (axes FR existants, EN manquant)",
        f"  Groupes avec axes vraiment nouveaux  : {len(with_new_axes)} (absents du schema)",
        f"  Groupes avec tokens inconnus  : {len(with_unknown_tok)}",
        "",
        "── NOMS PROPOSÉS CHANGÉS (50 premiers) " + "─"*27,
    ]
    for r in changed[:50]:
        lines += [
            f"  [{r['ig_id']}] {r['category']}/{r['subcategory']}",
            f"    EN  : {r['current_name_en']!r:40}  →  {r['proposed_name_en']!r}",
            f"    FR  : {r['current_name_fr']!r:40}  →  {r['proposed_name_fr']!r}",
        ]
        if r["axes_new"]:
            lines.append(f"    AXES NOUVEAUX : {r['axes_new']}")
        if r["unknown_tokens_en"]:
            lines.append(f"    INCONNUS EN   : {r['unknown_tokens_en']}")
        if r["unknown_tokens_fr"]:
            lines.append(f"    INCONNUS FR   : {r['unknown_tokens_fr']}")
        lines.append("")

    lines += [
        "",
        "── AXES EN À AJOUTER (équivalents FR existent déjà) " + "─"*14,
    ]
    for atype, vals in sorted(all_rename_axes.items()):
        fr_key = _SCHEMA["axes"].get(atype, {}).get("tree_key_fr", "?")
        lines.append(f"  {atype:<20} (FR: {fr_key}) : {sorted(vals)[:6]}")

    lines += [
        "",
        "── AXES VRAIMENT NOUVEAUX (absents du schema) " + "─"*20,
    ]
    for atype, vals in sorted(all_new_axes.items()):
        lines.append(f"  {atype:<20} : {sorted(vals)}")

    lines += [
        "",
        "── TOKENS EN INCONNUS (fréquence) " + "─"*31,
    ]
    for tok, cnt in sorted(all_unknowns_en.items(), key=lambda x: -x[1])[:40]:
        lines.append(f"  {tok:<30} : {cnt} occurrence(s)")

    lines += [
        "",
        "── TOKENS FR INCONNUS (fréquence) " + "─"*31,
    ]
    for tok, cnt in sorted(all_unknowns_fr.items(), key=lambda x: -x[1])[:40]:
        lines.append(f"  {tok:<30} : {cnt} occurrence(s)")

    out_txt.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Résumé texte    : {out_txt.name}")

    # ── Affichage console rapide ──────────────────────────────────
    print(f"\n{'─'*65}")
    print(f"  Groupes analysés              : {processed} / {total_groups}")
    print(f"  Noms à simplifier             : {len(changed)}")
    print(f"  Axes EN à ajouter (FR existe) : {len(all_rename_axes)} types  ({len(with_rename_axes)} groupes)")
    print(f"  Axes vraiment nouveaux        : {len(all_new_axes)} types  ({len(with_new_axes)} groupes)")
    print(f"  Tokens EN inconnus uniques    : {len(all_unknowns_en)}")
    print(f"  Tokens FR inconnus uniques    : {len(all_unknowns_fr)}")

    if all_rename_axes:
        print(f"\n  Axes EN manquants (FR existe dans le schema) :")
        for atype, vals in sorted(all_rename_axes.items()):
            fr_key = _SCHEMA["axes"].get(atype, {}).get("tree_key_fr", "?")
            print(f"    {atype:<20} (FR: {fr_key}) : {sorted(vals)[:4]}")

    if all_new_axes:
        print(f"\n  Axes vraiment nouveaux (absents du schema) :")
        for atype, vals in sorted(all_new_axes.items()):
            print(f"    {atype:<20} : {sorted(vals)[:5]}")

    if all_unknowns_en:
        top_unk = sorted(all_unknowns_en.items(), key=lambda x: -x[1])[:10]
        print(f"\n  Top tokens EN non classés :")
        for tok, cnt in top_unk:
            print(f"    {tok!r:<30} {cnt}x")

    print(f"\n{'='*65}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
