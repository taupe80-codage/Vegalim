"""
Inventaire complet des groupes CNF avec comptage par groupe
pour definir la strategie d'exclusion de build_cnf_full_v6.
"""
import re
import pandas as pd
from pathlib import Path
from collections import defaultdict

BASE    = Path(__file__).resolve().parents[2]
CNF_DIR = BASE / "backend/data/nutrition/cnf"

def load_csv(name):
    path = CNF_DIR / name
    for enc in ["utf-8", "latin1", "cp1252"]:
        for sep in [",", ";", "\t"]:
            try:
                df = pd.read_csv(path, encoding=enc, sep=sep)
                if len(df.columns) > 2:
                    return df
            except Exception:
                continue
    raise FileNotFoundError(name)

food  = load_csv("FOOD_NAME.csv")
group = load_csv("FOOD_GROUP.csv")

group_map    = dict(zip(group["FoodGroupID"], group["FoodGroupName"]))
group_map_fr = dict(zip(group["FoodGroupID"], group["FoodGroupNameF"]))

# ── Compter les items par groupe ──────────────────────────────────────────────
counts  = food.groupby("FoodGroupID")["FoodID"].count().to_dict()
total   = len(food)

print("=== GROUPES CNF ===\n")
print(f"{'ID':>4}  {'Count':>6}  {'GroupName'}")
print("-" * 80)
for gid in sorted(group_map.keys()):
    cnt  = counts.get(gid, 0)
    name = group_map[gid]
    namef= group_map_fr.get(gid, "")
    print(f" {gid:>3}  [{cnt:>4}]  {name}  /  {namef}")

print(f"\nTotal foods : {total}")

# ── Analyser les noms dans chaque groupe ambigu ───────────────────────────────
AMBIGUOUS_GROUPS = [1, 2, 6, 9, 11, 12, 18, 19, 20, 22, 23, 24, 25]

NON_VEG_KW = [
    "beef", "pork", "chicken", "turkey", "duck", "lamb", "veal", "goat",
    "meat", "flesh", "steak", "ribs", "bacon", "ham", "sausage", "lard",
    "gelatin", "gelatine", "anchov", "sardine", "tuna", "salmon", "trout",
    "shrimp", "lobster", "crab", "oyster", "clam", "mussel", "squid",
    "fish", "seafood", "shellfish", "luncheon", "frankfurter", "bologna",
    "pepperoni", "chorizo", "prosciutto", "salami", "wiener",
]

COMPOSITE_PATTERNS = [re.compile(p, re.I) for p in [
    r"\bsoups?\b", r"\bchowder\b", r"\bconsomme\b", r"\bbisque\b",
    r"\bgrav(y|ies)\b",
    r"\bstews?\b", r"\bcasseroles?\b", r"\bpot\s+pie\b",
    r"\blasagna\b", r"\braviolis?\b",
    r"\bpizzas?\b", r"\bburritos?\b", r"\btamales?\b",
    r"\bquesadilla\b", r"\begg\s+roll\b", r"\bcorn\s+dog\b",
    r"\bsandwich\b|\bburger\b|\bhot\s+dog\b",
    r"commercially\s+prepared",
    r"restaurant\s+prepared",
    r"pasteurized\s+process",  # fromage fondu industriel
]]

def is_non_veg(name):
    n = name.lower()
    return any(kw in n for kw in NON_VEG_KW)

def is_composite(name):
    return any(p.search(name) for p in COMPOSITE_PATTERNS)

print("\n=== ANALYSE GROUPES AMBIGUS ===\n")
for gid in sorted(group_map.keys()):
    cnt = counts.get(gid, 0)
    if cnt == 0:
        continue
    gname = group_map[gid]
    subset = food[food["FoodGroupID"] == gid]["FoodDescription"]

    nv  = sum(1 for n in subset if is_non_veg(str(n)))
    comp= sum(1 for n in subset if is_composite(str(n)))
    clean = cnt - nv - comp

    verdict = ""
    if nv > cnt * 0.7:
        verdict = "[HARD EXCL - non-veg dominant]"
    elif nv > 0 or comp > cnt * 0.3:
        verdict = "[MIXED - selective excl]"
    elif comp > cnt * 0.5:
        verdict = "[HARD EXCL - composite dominant]"
    else:
        verdict = "[KEEP]"

    print(f"{gid:>3}  [{cnt:>4}]  {gname}")
    print(f"         non-veg={nv:>3}  composite={comp:>3}  clean={clean:>4}  {verdict}")

    # Exemples de composites dans ce groupe
    examples = [n for n in subset if is_composite(str(n))][:5]
    for ex in examples:
        print(f"           COMP: {ex}")
    examples = [n for n in subset if is_non_veg(str(n))][:3]
    for ex in examples:
        print(f"           NV  : {ex}")

print("\nDone.")
