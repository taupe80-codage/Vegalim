import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
sys.path.append(str(BASE_DIR / "scripts"))

import pandas as pd
import json
import re
from pathlib import Path
from collections import defaultdict

from core.diet_classifier import classify_ingredient
from core.load_ontology import load_ontology

# =====================================================
# PATHS
# =====================================================

BASE_DIR    = Path(__file__).resolve().parents[2]
CNF_DIR     = BASE_DIR / "backend/data/nutrition/cnf"
OUTPUT      = BASE_DIR / "backend/data/nutrition/raw/cnf_full_v5.json"

ONTOLOGY = load_ontology()

# =====================================================
# EXCLUSIONS — groupes et items validés v5
# =====================================================

# FoodGroupIDs entièrement exclus
# (Pork=10, Beef=13 déjà filtrés par diet_classifier)
EXCLUDED_GROUP_IDS = {
    3,   # Babyfoods
    5,   # Poultry Products
    7,   # Sausages and Luncheon meats
    10,  # Pork Products  (défense double)
    13,  # Beef Products   (défense double)
    15,  # Finfish and Shellfish Products
    17,  # Lamb, Veal and Game
    21,  # Fast Foods
}

# Items spécifiques à exclure dans les groupes mixtes
EXCLUDED_ITEM_NAMES = {
    # Mixed Dishes — avec viande ou hors-scope
    "Chop suey, with meat, canned",
    "Pasta with sliced franks in tomato sauce, canned",
    "Salisbury steak in gravy with macaroni and cheese, frozen",
    "Breakfast, scrambled eggs & sausage with hashed brown potatoes, frozen",
    "Pizza, pepperoni, frozen, cooked",
    "Chili con carne with beans, canned",
    "Chili without beans, canned",
    "Spaghetti, with meatballs in tomato sauce, canned",
    "Tamale (Navajo)",
    "Meatballs, sweet and sour",
    "Shepherd's pie with corn",
    "Egg roll, assorted, restaurant prepared",
    "Corn dog, wiener/sausage with cornflour coating, frozen, prepared",
    "Pasta mix, classic cheeseburger macaroni, unprepared",
    "Spaghetti and meatballs, restaurant prepared",
    "Meatball, Italian style, frozen",
    "Spaghetti, without meat, canned",
    # Snacks — industriels de marque sans valeur pour recettes
    "Snacks, corn-based, extruded, chips, plain",
    "Snacks, corn-based, extruded, chips, barbecue",
    "Snacks, corn-based, extruded, cones, plain",
    "Snacks, corn-based, extruded, onion",
    "Snacks, corn-based, extruded, puffs or twists, cheese",
    "Snacks, corn-based, extruded, puffs or twists, cheese, baked, low fat",
    "Snacks, corn-based, extruded, chips, unsalted",
    "Snacks, corn nuts, barbecue",
    "Snacks, crisped rice bar, chocolate chip",
    "Snacks, crisped rice bar, almond",
    "Snacks, oriental mix, rice-based",
    "Snacks, popcorn, caramel-coated, with peanuts",
    "Snacks, popcorn, caramel-coated, without peanuts",
    "Snacks, popcorn, cheese flavour",
    "Snacks, popcorn, sugar syrup/caramel, fat free",
    "Snacks, potato chips, barbecue flavour",
    "Snacks, potato chips, sour cream and onion",
    "Snacks, potato chips, dried potatoes, light",
    "Snacks, potato chips, dried potatoes, sour cream and onion",
    "Snacks, potato chips, dried potatoes, plain",
    "Snacks, potato chips, dried potatoes, cheese",
    "Snacks, potato chips, cheese",
    "Snacks, potato chips, plain, salted",
    "Snacks, potato chips, lightly salted",
    "Snacks, potato chips, white, restructured, baked",
    "Snacks, potato sticks",
    "Snacks, pretzels, hard, whole-wheat, including both salted and unsalted",
    "Snacks, pretzels, hard, plain, unsalted",
    "Snacks, pretzels, hard, plain, salted",
    "Snacks, pretzels, soft",
    "Snacks, pretzels, soft, unsalted",
    "Snacks, pretzels, hard, chocolate coated",
    "Snacks, tortilla chips, plain",
    "Snacks, tortilla chips, nacho",
    "Snacks, tortilla chips, ranch",
    "Snacks, tortilla chips, taco",
    "Snacks, tortilla chips, nacho, light",
    "Snacks, tortilla chips, low fat, baked without fat",
    "Snacks, tortilla chips, unsalted",
    "Snacks, tortilla chips, unsalted, low fat",
    "Snacks, tortilla chips, light (baked with less oil)",
    "Snacks, tortilla chips, plain, yellow corn",
    "Snacks, RICE KRISPIES SQUARES",
    "Snacks, SUNCHIPS, French Onion flavour",
    "Snacks, SUNCHIPS, Harvest Cheddar flavour",
    "Snacks, Clif bar, all flavours",
    "Snacks, multigrain chips, plain",
    "Snacks, bagel chips",
    "Snacks, brown rice chips",
    "Cracker, honey sesame",
    "Snacks, sesame sticks, wheat-based, salted",
    "Snacks, sesame sticks, wheat-based, unsalted",
    # Soups/Sauces — viande, poisson, ou marque
    "Soup, scotch broth, canned, condensed",
    "Soup, scotch broth, canned, condensed, water added",
    "Soup, oxtail, dehydrated",
    "Soup, oxtail, dehydrated, water added",
    "Gravy, au jus, canned",
    "Gravy, au jus, dehydrated",
    "Gravy, unspecified, dehydrated",
    "Sauce, oyster, ready-to-serve",
    "Sauce, worcestershire, ready-to-serve",
    "Sauce, cocktail, ready-to-serve",
    "Soup, clam chowder, New England, ready-to-serve",
    "Soup, clam chowder, New England, ready-to-serve, reduced sodium",
    "Soup, clam chowder, manhattan, ready-to-serve",
    "Soup, wonton (won ton), restaurant prepared",
    "Soup, wonton (won ton), canned, ready-to-serve",
    "Soup, Italian wedding, ready-to-serve",
    "Soup, NISSIN, OODLES OF NOODLES TOP RAMEN, ramen noodles, oriental flavour, dry",
    "Soup, NISSIN, OODLES OF NOODLES TOP RAMEN ramen noodles, oriental flavour, dry, water added",
    "Soup, ramen noodles, any flavour, dry",
    "Chinese dish, soup, hot and sour, restaurant prepared",
    "Soup, consomme, dehydrated",
    "Soup, consomme, dehydrated, water added",
    "Sauce, steak, tomato based, ready-to-serve",
}

# Items Mixed Dishes + soupes maison à flagger coherence_check_only
COHERENCE_CHECK_NAMES = {
    "Cheese souffle",
    "Macaroni and cheese, canned entree",
    "Pasta, fresh-refrigerated, tortellini with cheese filling, as purchased",
    "Lasagna, cheese, frozen, prepared",
    "Burrito, bean and cheese, frozen",
    "Burrito, bean and cheese, microwaved",
    "Egg roll, vegetable, refrigerated, heated",
    "Lasagna, vegetable, frozen, baked",
    "Salad, garden, with Italian dressing, homemade",
    "Salad, Greek, homemade",
    "Salad, taco, with salsa, homemade",
    "Salad, caesar, homemade",
    "Lasagna, vegetarian, homemade",
    "Pasta salad with vegetables, prepared with Italian dressing, homemade",
    "Sandwich, egg salad, homemade",
    "Indien, samosa, vegetarian",
    "Sandwich, vegetarian burger (veggie burger) + vegetables + mayonnaise",
    "Zucchini, battered and fried",
    "Spaghetti with cream sauce",
    "Stir fry with tofu",
    "Poutine",
    "Mozzarella sticks, fried",
    "Tamale, corn",
    "Ravioli, cheese and tomato sauce, frozen, not prepared",
    "Potato salad with egg",
    "Macaroni and cheese, frozen",
    "Ravioli, cheese-filled, canned",
    "Macaroni and cheese, box mix with cheese sauce, unprepared",
    "Macaroni and cheese, box mix with cheese sauce, prepared",
    "Chinese dish, fried rice without meat, restaurant prepared",
    "Pizza roll, frozen, unprepared",
    "Turnover, cheese-filled, tomato-based sauce, frozen, unprepared",
    "Lasagna, cheese, frozen, unprepared",
    "Chinese dish, lo mein, vegetable, without meat, restaurant prepared",
    "Quinoa burger patty, frozen",
    "Rice, spanish rice mix, unprepared",
    "Rice, spanish rice mix, prepared",
    "Spaghetti with pomodoro sauce (tomato sauce)",
    "Quesadilla with cheese",
    "Ravioli, cheese-filled with marinara sauce",
    "Tamale, cheese",
    "Rice, Spanish rice",
    # Soupes maison / restaurant complètes
    "Soup, lentil, homemade",
    "Soup, vegetable, homemade",
    "Soup, cream of vegetable, made with 2% M.F. milk, homemade",
    "Soup, French onion, homemade (with bread and cheese)",
    "Chinese dish, soup, egg drop, restaurant prepared",
}

# =====================================================
# NUTRIENT ID MAP — direct, sans ambiguïté de string
# =====================================================
# Fixes v5 :
#   - 208  : kcal uniquement (v4 confondait avec kJ 268 → 54% couverture)
#   - 291  : FIBRE (v4 cherchait "fiber" → 0% couverture)
#   - 814  : Retinol Activity Equivalents = vitamin_a (v4 cherchait "vitamin a" → 0%)
#   - 339  : Vitamin D (D2+D3) µg — nouveau
NUTRIENT_ID_MAP = {
    208: "calories_kcal",    # ENERGY (KILOCALORIES)
    203: "protein_g",        # PROTEIN
    204: "fat_g",            # FAT (TOTAL LIPIDS)
    205: "carbs_g",          # CARBOHYDRATE, TOTAL
    291: "fiber_g",          # FIBRE, TOTAL DIETARY
    269: "sugar_g",          # SUGARS, TOTAL
    401: "vitamin_c_mg",     # VITAMIN C
    814: "vitamin_a_ug",     # RETINOL ACTIVITY EQUIVALENTS (RAE)
    301: "calcium_mg",       # CALCIUM
    303: "iron_mg",          # IRON
    306: "potassium_mg",     # POTASSIUM
    304: "magnesium_mg",     # MAGNESIUM
    307: "sodium_mg",        # SODIUM
    309: "zinc_mg",          # ZINC
    339: "vitamin_d_ug",     # VITAMIN D (D2 + D3)
}

# =====================================================
# ROBUST CSV LOADER
# =====================================================

def load_csv(name):
    path = CNF_DIR / name
    if not path.exists():
        print(f"❌ Missing: {path}")
        print("  Available:", [f.name for f in CNF_DIR.glob("*.csv")])
        raise FileNotFoundError(name)

    for enc in ["utf-8", "latin1", "cp1252"]:
        for sep in [",", ";", "\t"]:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep)
                if len(df.columns) > 2:
                    print(f"  ✔ {name:<30} {enc} | '{sep}' | {len(df)} rows")
                    return df
            except Exception:
                continue

    raise Exception(f"❌ Cannot read {name}")

# =====================================================
# TEXT UTILITIES
# =====================================================

def clean(text):
    if not isinstance(text, str):
        return ""
    text = text.lower()
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.strip()

def tokenize(text):
    return [t for t in clean(text).split() if len(t) > 1]

def extract_core(name):
    name_c = clean(name)
    for sep in [" with ", " and ", ","]:
        if sep in name_c:
            return name_c.split(sep)[0].strip()
    return name_c

def make_id(name, fid, seen_ids):
    """Génère un ID unique — suffixe FoodID si collision."""
    base = clean(name).replace(" ", "_")
    if base not in seen_ids:
        seen_ids.add(base)
        return base
    unique = f"{base}_{fid}"
    seen_ids.add(unique)
    return unique

# =====================================================
# LOAD CSVs
# =====================================================

print("\n─── Loading CNF source files ───")
food          = load_csv("FOOD_NAME.csv")
group         = load_csv("FOOD_GROUP.csv")
nutrient_name = load_csv("NUTRIENT_NAME.csv")
nutrient_amt  = load_csv("NUTRIENT_AMOUNT.csv")
refuse        = load_csv("REFUSE_AMOUNT.csv")
yield_df      = load_csv("YIELD_AMOUNT.csv")

# =====================================================
# LOOKUPS
# =====================================================

group_map   = dict(zip(group["FoodGroupID"],   group["FoodGroupName"]))
group_map_fr= dict(zip(group["FoodGroupID"],   group["FoodGroupNameF"]))

# =====================================================
# BUILD NUTRIENT INDEX — par FoodID, ciblé par NutrientID
# =====================================================

print("\n─── Indexing nutrients ───")
nutrients = defaultdict(dict)

for _, r in nutrient_amt.iterrows():
    fid = r.get("FoodID")
    nid = r.get("NutrientID")
    val = r.get("NutrientValue")

    if fid is None or nid is None or val is None:
        continue

    key = NUTRIENT_ID_MAP.get(nid)
    if key:
        try:
            nutrients[fid][key] = float(val)
        except (TypeError, ValueError):
            pass

# =====================================================
# REFUSE / YIELD INDEXES
# =====================================================

refuse_map = {}
for _, r in refuse.iterrows():
    fid = r.get("FoodID")
    val = r.get("RefuseAmount")
    if fid is not None and val is not None:
        try:
            refuse_map[fid] = float(val)
        except (TypeError, ValueError):
            pass

yield_map = defaultdict(dict)
for _, r in yield_df.iterrows():
    fid = r.get("FoodID")
    yid = r.get("YieldID")
    val = r.get("YieldAmount")
    if fid and yid and val is not None:
        try:
            yield_map[fid][str(yid)] = float(val)
        except (TypeError, ValueError):
            pass

# =====================================================
# VALIDATION — seuils calibrés sur les vraies unités CNF
# =====================================================

def validate(n):
    issues = []

    kcal = n.get("calories_kcal")
    # Max CNF réel = 902 kcal (graisses pures) — seuil à 910 pour tolérance
    if kcal is not None and kcal > 910:
        issues.append("energy_aberrant")

    carbs  = n.get("carbs_g")
    sugar  = n.get("sugar_g")
    fiber  = n.get("fiber_g")

    if carbs is not None and sugar is not None and sugar > carbs + 0.5:
        issues.append("sugar>carbs")

    if carbs is not None and fiber is not None and fiber > carbs + 0.5:
        issues.append("fiber>carbs")

    total_macro = sum(n.get(k, 0) or 0 for k in ["protein_g", "carbs_g", "fat_g"])
    if total_macro > 105:
        issues.append("macro_sum>100")

    return issues

# =====================================================
# CONFIDENCE
# =====================================================

NUTRIENT_KEYS = list(NUTRIENT_ID_MAP.values())
N_KEYS = len(NUTRIENT_KEYS)

def compute_confidence(n, issues):
    filled = sum(1 for k in NUTRIENT_KEYS if n.get(k) is not None)
    base    = filled / N_KEYS
    penalty = len(issues) * 0.08
    if n.get("calories_kcal") is None:
        penalty += 0.15
    if n.get("protein_g") is None or n.get("carbs_g") is None or n.get("fat_g") is None:
        penalty += 0.10
    return round(max(0.0, min(1.0, base - penalty)), 3)

# =====================================================
# BUILD
# =====================================================

print("\n─── Building CNF v5 ───")

result   = []
seen_ids = set()
stats    = defaultdict(int)

for _, row in food.iterrows():

    fid   = row.get("FoodID")
    name  = row.get("FoodDescription")
    namef = row.get("FoodDescriptionF", "")
    grp_id= row.get("FoodGroupID")
    grp   = group_map.get(grp_id)

    # ── Filtre 1 : groupes entièrement exclus
    if grp_id in EXCLUDED_GROUP_IDS:
        stats["excluded_group"] += 1
        continue

    # ── Filtre 2 : items spécifiques exclus
    if name in EXCLUDED_ITEM_NAMES:
        stats["excluded_item"] += 1
        continue

    # ── Filtre 3 : diet_classifier (défense principale)
    diet = classify_ingredient(name, ONTOLOGY)
    if diet["label"] == "non_vegetarian":
        stats["excluded_diet"] += 1
        continue

    # ── Nutriments
    n      = nutrients.get(fid, {})
    issues = validate(n)
    conf   = compute_confidence(n, issues)

    # ── ID unique
    item_id = make_id(name, fid, seen_ids)

    # ── Flag coherence_check_only
    meta_usage = "coherence_check_only" if name in COHERENCE_CHECK_NAMES else None

    meta = {
        "fid":            fid,
        "confidence":     conf,
        "nutrient_count": len(n),
        "source":         "CNF V5",
    }
    if meta_usage:
        meta["usage"] = meta_usage

    result.append({
        "id":         item_id,
        "clean_name": clean(name),
        "core_name":  extract_core(name),
        "name":       name,
        "name_fr":    namef if isinstance(namef, str) else "",
        "group":      grp,

        "diet": {
            "vegetarian": True,
            "confidence": diet["confidence"],
            "reason":     diet["reason"],
        },

        "nutrition": n,

        "quality": {
            "issues": issues,
            "valid":  len(issues) == 0,
        },

        "processing": {
            "yield":          dict(yield_map.get(fid, {})),
            "refuse_percent": refuse_map.get(fid),
        },

        "matching": {
            "tokens":  tokenize(name),
            "aliases": list({extract_core(name), clean(name)} - {""}),
        },

        "meta": meta,
    })

    stats["kept"] += 1
    if meta_usage == "coherence_check_only":
        stats["flagged_coherence"] += 1

# =====================================================
# SAVE
# =====================================================

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

payload = {
    "_meta": {
        "version":         "CNF V5",
        "total":           len(result),
        "nutrient_fields": NUTRIENT_KEYS,
        "excluded_groups": [group_map[g] for g in EXCLUDED_GROUP_IDS if g in group_map],
    },
    "foods": result,
}

with open(OUTPUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2, ensure_ascii=False)

# =====================================================
# REPORT
# =====================================================

print(f"\n{'═' * 50}")
print(f"  CNF V5 — BUILD REPORT")
print(f"{'═' * 50}")
print(f"  Input  FOOD_NAME          : {len(food)}")
print(f"  Exclus groupe             : {stats['excluded_group']}")
print(f"  Exclus item spécifique    : {stats['excluded_item']}")
print(f"  Exclus diet_classifier    : {stats['excluded_diet']}")
print(f"  ─────────────────────────")
print(f"  Conservés                 : {stats['kept']}")
print(f"  dont coherence_check_only : {stats['flagged_coherence']}")
print(f"\n  Nutriments mappés ({N_KEYS}):")
for k in NUTRIENT_KEYS:
    count = sum(1 for f in result if f["nutrition"].get(k) is not None)
    pct   = count / len(result) * 100
    bar   = "█" * int(pct / 5)
    print(f"    {k:<22} {count:4d}/{len(result)} ({pct:5.1f}%)  {bar}")

print(f"\n  ✔ Output: {OUTPUT}")