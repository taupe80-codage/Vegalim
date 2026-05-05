"""
Diagnostic energy_mismatch — source + schema + recalc par item
A lancer depuis la racine du projet.
"""
import json, sys

TARGETS = {
    "capers","cherry","sauerkraut","green_bean","garlic",
    "green_mango","hard_boiled_egg","mango","zucchini",
    "cashew","almond","watermelon","hominy","taro",
    "kale","pea_protein","moringa","quinoa"
}

with open("backend/data/nutrition/reference/nutrition_patched_v8.json", encoding="utf-8") as f:
    data = json.load(f)

ingredients = data.get("ingredients", data) if isinstance(data, dict) else data

def get_variants(ing):
    if isinstance(ing, dict):
        return ing.get("variants", {"default": ing})
    return {"default": ing}

def find_field(d, *keys):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return None

print(f"{'Item':<22} {'Variant':<12} {'Schema':<10} {'Source':<8} "
      f"{'kcal':>5} {'est_std':>7} {'est_pol':>7} {'Δstd':>6} {'Δpol':>6} {'polyols':>7} {'org_ac':>6}")
print("─"*105)

for name, ing in ingredients.items():
    if name not in TARGETS:
        continue
    variants = get_variants(ing)
    for vname, v in variants.items():
        if not isinstance(v, dict): continue

        kcal    = find_field(v, "calories_kcal", "calories")
        p       = find_field(v, "protein_g", "protein")
        c       = find_field(v, "carbs_g", "carbs")
        f       = find_field(v, "fat_g", "fat")
        fib     = find_field(v, "fiber_g", "fiber")
        polyols = find_field(v, "polyols_g", "polyols") or 0.0
        org_ac  = find_field(v, "organic_acids_g", "organic_acids") or 0.0
        schema  = v.get("carbs_schema") or ing.get("carbs_schema") or "total"
        source  = v.get("source") or ing.get("source") or "?"

        if not all(x is not None for x in [kcal, p, c, f]) or kcal <= 0:
            continue

        # Formule standard (actuelle validator)
        if schema == "available" and fib:
            est_std = p*4 + c*4 + fib*2 + f*9
        else:
            est_std = p*4 + c*4 + f*9

        # Formule avec polyols déduits de carbs (comme fix CIQUAL v6.15)
        c_net   = max(0, c - polyols)
        if schema == "available" and fib:
            est_pol = p*4 + c_net*4 + fib*2 + f*9 + polyols*2.4 + org_ac*3
        else:
            est_pol = p*4 + c_net*4 + f*9 + polyols*2.4 + org_ac*3

        d_std = round(abs(kcal - est_std) / kcal * 100, 1) if kcal else 0
        d_pol = round(abs(kcal - est_pol) / kcal * 100, 1) if kcal else 0

        flag_std = "⚠" if d_std >= 15 else "✅"
        flag_pol = "⚠" if d_pol >= 15 else "✅"

        print(f"{name:<22} {vname:<12} {schema:<10} {str(source)[:8]:<8} "
              f"{kcal:>5.0f} {est_std:>7.1f} {est_pol:>7.1f} "
              f"{flag_std}{d_std:>4.1f}% {flag_pol}{d_pol:>4.1f}% "
              f"{polyols:>7.2f} {org_ac:>6.2f}")
