"""Temporary: extract suspect recipe data for validation report."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
recipes_data = json.loads((ROOT / "backend/data/recipes/recipes.json").read_text(encoding="utf-8"))
recipes = recipes_data["recipes"]
ng = json.loads((ROOT / "backend/data/graphs/recipe_nutrition_graph_v1.json").read_text(encoding="utf-8"))
recipe_map = {r["id"]: r for r in recipes}

SUSPECTS = [
    "salad_fattoush_classic_x82m5c",
    "soup_onion_french_classic_v3_t9k2m4",
    "dal_basic_k3d2p1",
    "stew_lentil_basic_v2_x7k2m9",
    "pasta_plain_k2d1p1",
    "falafel_falafel_optimise_2f1451",
]

print("=== RECETTES SUSPECTES - données pour validation ===\n")
for rid in SUSPECTS:
    r = recipe_map.get(rid)
    n = ng.get(rid, {})
    if not r:
        print(f"{rid}: NOT FOUND\n")
        continue

    srvs = r.get("servings") or 4
    comp = r.get("composition", [])
    total_g = r.get("metrics", {}).get("total_weight_g", "?")
    cal   = n.get("calories", "?")
    prot  = n.get("protein", "?")
    carbs = n.get("carbs", "?")
    fat   = n.get("fat", "?")
    sodium = n.get("sodium", "?")

    try:
        cal_theo = round(prot * 4 + carbs * 4 + fat * 9, 1)
    except Exception:
        cal_theo = "?"

    print(f"--- {rid} ---")
    print(f"  Titre FR     : {r.get('titles', {}).get('fr', '?')}")
    print(f"  Servings     : {srvs}")
    print(f"  Total poids  : {total_g}g")
    print(f"  Cal/portion  : {cal} kcal")
    if isinstance(cal, (int, float)):
        print(f"  Cal total rec: {round(cal * srvs)} kcal")
    print(f"  Proteines    : {prot}g | Glucides: {carbs}g | Lipides: {fat}g | Sodium: {sodium}mg")
    print(f"  Cal theorique: {cal_theo} kcal")
    print(f"  Composition  ({len(comp)} ing.):")
    for item in comp[:10]:
        if isinstance(item, dict):
            print(f"    - {item.get('ingredient','?'):25s}  {item.get('quantity','?'):>8}  {item.get('unit','?')}")
    if len(comp) > 10:
        print(f"    ... +{len(comp)-10} autres")
    print()

# Ingrédients > 500g (pour validation individuelle)
print("\n=== INGREDIENTS > 500g (top 25 par quantite) ===\n")
oversized = []
for r in recipes:
    rid = r["id"]
    srvs = r.get("servings") or 4
    title = r.get("titles", {}).get("fr", "")
    for item in r.get("composition", []):
        if not isinstance(item, dict):
            continue
        qty  = item.get("quantity") or 0
        unit = (item.get("unit") or "g").lower()
        ing  = item.get("ingredient", "")
        if unit == "g" and qty > 500:
            oversized.append({
                "id": rid, "title": title, "ing": ing,
                "qty": qty, "srvs": srvs, "per_srv": round(qty / srvs)
            })

oversized.sort(key=lambda x: -x["qty"])
print(f"{'ID':<45}  {'Ingredient':<25}  {'Total':>8}  {'Serv':>4}  {'g/pers':>7}")
print("-" * 95)
for o in oversized[:30]:
    print(f"{o['id']:<45}  {o['ing']:<25}  {o['qty']:>7}g  {o['srvs']:>4}  {o['per_srv']:>6}g")
print(f"\n  ... Total: {len(oversized)} cas > 500g dans le dataset")

# Liquides actuellement en g (faux: doivent être en ml)
print("\n\n=== LIQUIDES EN GRAMMES (a corriger -> ml) ===\n")
LIQUID_CORE = {
    "oil", "olive_oil", "vegetable_oil", "sesame_oil", "coconut_oil",
    "sunflower_oil", "milk", "lait", "lait_coco", "water", "eau",
    "broth", "bouillon", "vegetable_broth", "vegetable_stock",
    "vinegar", "vinaigre", "soy_sauce","sauce_soja", "tamari",
    "cream", "creme", "wine", "vin", "beer", "biere",
    "apple_juice", "orange_juice", "lemon_juice",
}
liquid_in_g = []
for r in recipes:
    rid = r["id"]
    for item in r.get("composition", []):
        if not isinstance(item, dict):
            continue
        ing  = item.get("ingredient", "").lower()
        qty  = item.get("quantity") or 0
        unit = (item.get("unit") or "g").lower()
        if unit == "g" and qty > 3 and ing in LIQUID_CORE:
            liquid_in_g.append({"id": rid, "ing": ing, "qty": qty, "unit": unit})

liquid_in_g.sort(key=lambda x: x["ing"])
print(f"{'ID':<45}  {'Ingredient':<25}  {'Qty':>7}")
print("-" * 80)
for item in liquid_in_g:
    print(f"{item['id']:<45}  {item['ing']:<25}  {item['qty']:>6}g  (→ ml ?)")
print(f"\n  Total: {len(liquid_in_g)} cas")
