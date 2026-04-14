"""
scripts/fix_validated_issues.py
================================
Corrections validées par l'utilisateur :
  1. salad_fattoush: bread 3000g → 300g + recalcul nutritionnel
  2. dal_basic + stew_lentil: lentilles crues → recalcul nutritionnel correct
  3. falafel: huile de friture → absorption partielle (~80ml effectifs)
  4. pasta_plain: sodium sel cuisson → exclu du calcul
  5. soup_onion: vérification et recalcul si nécessaire

Usage:
  python scripts/fix_validated_issues.py --dry-run   (affiche sans modifier)
  python scripts/fix_validated_issues.py             (applique les corrections)
"""
import sys
import json
import argparse
from pathlib import Path
from copy import deepcopy

ROOT      = Path(__file__).resolve().parent.parent
RECIPES_F = ROOT / "backend/data/recipes/recipes.json"
NG_F      = ROOT / "backend/data/graphs/recipe_nutrition_graph_v1.json"
NUTRI_F   = ROOT / "backend/data/nutrition/nutrition_database.json"
PHYS_F    = ROOT / "backend/data/ingredients/ingredient_physical.json"

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_json(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))

def save_json(p: Path, data, dry_run: bool):
    if dry_run:
        return
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def build_nutrition_lookup(nutri_db: dict) -> dict:
    """Construit un lookup id/alias → données nutritionnelles."""
    lookup = {}
    for k, v in nutri_db.items():
        lookup[k.lower()] = v
        for alias in v.get("aliases", []):
            lookup[alias.lower()] = v

    # Fallbacks manuels : ingrédients absents mais équivalents connus
    MANUAL_FALLBACKS = {
        # key (dans recette) → clé dans la DB
        "dried_chickpeas":     "pois chiches secs (trempes 12 h)",  # 364 kcal/100g (crus trempés)
        "green_lentils":       "lentils",
        "brown_lentils":       "lentils",
        "puy_lentil":          "lentils",
        "beluga_lentil":       "lentils",
        "ground_ginger":       "ginger",
        "porcini":             "mushroom",
        "napa_cabbage":        "cabbage",
        "chinese_broccoli":    "broccoli",
        "rolled_oats":         "oat",
        "plant_yogurt":        "yogurt",
        "dark_soy_sauce":      "soy_sauce",
        "light_soy_sauce":     "soy_sauce",
        "floury_potato":       "potato",
        "snow_peas":           "green_pea",
        "dried_peas":          "green_pea",
    }
    for recipe_key, db_key in MANUAL_FALLBACKS.items():
        if recipe_key not in lookup and db_key.lower() in lookup:
            lookup[recipe_key] = lookup[db_key.lower()]

    return lookup


def unit_to_g(ing: str, qty: float, unit: str, phys: dict) -> float:
    """Convertit une quantité en grammes équivalents."""
    u = unit.lower()
    if u in ("g", "ml"):
        return qty
    if u == "piece":
        p = phys.get(ing, {})
        w = p.get("average_unit_weight_g") or p.get("avg_weight_g")
        if w:
            return qty * w
        defaults = {
            "egg": 55, "onion": 150, "lemon": 100, "lime": 80,
            "garlic": 5, "potato": 150, "tomato": 120, "carrot": 100,
            "apple": 180, "orange": 200, "banana": 120,
        }
        return qty * defaults.get(ing, 100)
    if u in ("tbsp", "tablespoon"):
        return qty * 15
    if u in ("tsp", "teaspoon"):
        return qty * 5
    if u in ("cup",):
        return qty * 240
    return qty

# Champs nutritionnels à calculer (per 100g dans la DB)
NUTRI_KEYS = [
    "calories", "protein", "carbs", "fat", "fiber", "sugar",
    "sodium", "calcium", "iron", "magnesium", "potassium",
    "vitamin_c", "vitamin_b12", "zinc", "phosphorus",
]

def compute_nutrition_for_recipe(
    recipe: dict,
    nutri_lookup: dict,
    phys: dict,
    oil_override: float = None,    # remplacement effectif huile friture (g)
    exclude_cooking_salt: bool = False,
) -> dict:
    """
    Recalcule les nutriments d'une recette par portion à partir de la base nutrition.
    Retourne un dict avec les valeurs per serving.
    """
    servings = max(1, recipe.get("servings") or 1)
    totals = {k: 0.0 for k in NUTRI_KEYS}
    found_ings = []
    missing_ings = []

    for item in recipe.get("composition", []):
        if not isinstance(item, dict):
            continue
        ing  = item.get("ingredient", "").lower()
        qty  = float(item.get("quantity") or 0)
        unit = (item.get("unit") or "g").lower()

        # Cas spéciaux
        # 1. Sel de cuisson des pâtes → exclure du sodium
        if exclude_cooking_salt and ing == "salt" and qty >= 20:
            # sel cuisson pasta: garder seulement ~10% (portion absorbée)
            qty = qty * 0.10

        # 2. Huile de friture → absorption partielle
        if oil_override is not None and unit == "ml" and ing in (
            "sunflower_oil", "vegetable_oil", "olive_oil", "oil", "huile_friture"
        ) and qty >= 200:
            qty = oil_override  # ml effectifs absorbés

        g = unit_to_g(ing, qty, unit, phys)
        n = nutri_lookup.get(ing)
        if not n:
            missing_ings.append(ing)
            continue

        found_ings.append(ing)
        for key in NUTRI_KEYS:
            val = n.get(key, 0) or 0
            totals[key] += (val * g) / 100.0

    # Arrondi et division par portion
    result = {}
    for key in NUTRI_KEYS:
        result[key] = round(totals[key] / servings, 1)

    result["_missing_ingredients"] = missing_ings
    result["_found_ingredients"] = found_ings
    return result

# ── Corrections spécifiques ───────────────────────────────────────────────────

def fix_fattoush(recipes_list: list, nutri_lookup: dict, phys: dict,
                 ng: dict, dry_run: bool):
    """1. Fattoush: bread 3000g → 300g + recalcul."""
    RID = "salad_fattoush_classic_x82m5c"
    r = next((x for x in recipes_list if x["id"] == RID), None)
    if not r:
        print(f"  ⚠️  {RID} non trouvé")
        return

    # Corriger la composition
    old_qty = None
    for item in r["composition"]:
        if isinstance(item, dict) and item.get("ingredient") == "bread":
            old_qty = item["quantity"]
            if not dry_run:
                item["quantity"] = 300
            break

    # Recalculer total_weight_g
    new_total = sum(
        unit_to_g(i.get("ingredient",""), float(i.get("quantity",0)),
                  i.get("unit","g"), phys)
        for i in r["composition"] if isinstance(i, dict)
    )
    if not dry_run:
        r.setdefault("metrics", {})["total_weight_g"] = round(new_total)

    # Recalculer nutrition
    nutri = compute_nutrition_for_recipe(r, nutri_lookup, phys)
    nutri.pop("_missing_ingredients", None)
    nutri.pop("_found_ingredients", None)
    nutri["source"] = "ciqual_computed_fixed_bread_300g"

    old_cal = ng.get(RID, {}).get("calories", "?")
    if not dry_run:
        ng[RID].update(nutri)

    print(f"  ✅ Fattoush — bread {old_qty}g → 300g | cal: {old_cal} → {nutri['calories']} kcal/portion")
    print(f"     Total poids recette: {round(new_total)}g | Sodium: {nutri['sodium']}mg | Fibres: {nutri['fiber']}g")


def fix_lentil_recipes(recipes_list: list, nutri_lookup: dict, phys: dict,
                       ng: dict, dry_run: bool):
    """2. Dal basic + stew_lentil: recalcul avec lentilles crues."""
    targets = [
        ("dal_basic_k3d2p1",          "lentils",       "Lentilles (base)"),
        ("stew_lentil_basic_v2_x7k2m9","green_lentils", "Lentilles mijotées"),
    ]
    for rid, lentil_key, label in targets:
        r = next((x for x in recipes_list if x["id"] == rid), None)
        if not r:
            continue

        nutri = compute_nutrition_for_recipe(r, nutri_lookup, phys)
        missing = nutri.pop("_missing_ingredients", [])
        nutri.pop("_found_ingredients", None)
        nutri["source"] = "ciqual_computed_raw_lentils"

        old_cal = ng.get(rid, {}).get("calories", "?")
        if not dry_run:
            ng[rid].update(nutri)

        flag = f" [MANQUANTS: {missing}]" if missing else ""
        print(f"  ✅ {label} — cal: {old_cal} → {nutri['calories']} kcal/portion{flag}")
        print(f"     Prot: {nutri['protein']}g | Glucides: {nutri['carbs']}g | Lipides: {nutri['fat']}g")


def fix_falafel(recipes_list: list, nutri_lookup: dict, phys: dict,
                ng: dict, dry_run: bool):
    """3. Falafel: huile friture → absorption partielle (80ml effectifs)."""
    RID = "falafel_falafel_optimise_2f1451"
    r = next((x for x in recipes_list if x["id"] == RID), None)
    if not r:
        return

    # Falafels: ~16% d'absorption = 80ml sur 500ml
    OIL_ABSORBED_ML = 80.0

    nutri = compute_nutrition_for_recipe(
        r, nutri_lookup, phys, oil_override=OIL_ABSORBED_ML
    )
    missing = nutri.pop("_missing_ingredients", [])
    nutri.pop("_found_ingredients", None)
    nutri["source"] = "ciqual_computed_partial_oil_80ml"

    old_cal = ng.get(RID, {}).get("calories", "?")
    if not dry_run:
        ng[RID].update(nutri)

    flag = f" [MANQUANTS: {missing}]" if missing else ""
    print(f"  ✅ Falafel — huile: 500ml → 80ml absorbés | cal: {old_cal} → {nutri['calories']} kcal/portion{flag}")
    print(f"     Lipides: {ng.get(RID,{}).get('fat','?')} → {nutri['fat']}g | Prot: {nutri['protein']}g")


def fix_pasta_sodium(recipes_list: list, nutri_lookup: dict, phys: dict,
                     ng: dict, dry_run: bool):
    """4. Pasta plain: sel cuisson → sodium recalculé sans sel cuisson."""
    RID = "pasta_plain_k2d1p1"
    r = next((x for x in recipes_list if x["id"] == RID), None)
    if not r:
        return

    nutri = compute_nutrition_for_recipe(
        r, nutri_lookup, phys, exclude_cooking_salt=True
    )
    missing = nutri.pop("_missing_ingredients", [])
    nutri.pop("_found_ingredients", None)
    nutri["source"] = "ciqual_computed_no_cooking_salt"

    old_sodium = ng.get(RID, {}).get("sodium", "?")
    if not dry_run:
        ng[RID].update(nutri)

    print(f"  ✅ Pasta plain — sodium: {old_sodium} → {nutri['sodium']}mg/portion (sel cuisson exclu)")


def fix_soup_onion(recipes_list: list, nutri_lookup: dict, phys: dict,
                   ng: dict, dry_run: bool):
    """5. Soupe oignon: recalcul nutritionnel avec poids unitaires corrects."""
    RID = "soup_onion_french_classic_v3_t9k2m4"
    r = next((x for x in recipes_list if x["id"] == RID), None)
    if not r:
        return

    nutri = compute_nutrition_for_recipe(r, nutri_lookup, phys)
    missing = nutri.pop("_missing_ingredients", [])
    nutri.pop("_found_ingredients", None)
    nutri["source"] = "ciqual_computed_fixed_onion_weight"

    old_cal = ng.get(RID, {}).get("calories", "?")
    if not dry_run:
        ng[RID].update(nutri)

    flag = f" [MANQUANTS: {missing}]" if missing else ""
    print(f"  ✅ Soupe oignon — cal: {old_cal} → {nutri['calories']} kcal/portion{flag}")
    print(f"     Sodium: {nutri['sodium']}mg | Lipides: {nutri['fat']}g | Prot: {nutri['protein']}g")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Affiche les corrections sans modifier les fichiers")
    args = parser.parse_args()
    dry = args.dry_run

    mode = "DRY-RUN (aucune modification)" if dry else "APPLICATION des corrections"
    print(f"\n{'═'*60}")
    print(f"  ALIM v6 — Corrections validées — {mode}")
    print(f"{'═'*60}\n")

    # Chargement
    recipes_data = load_json(RECIPES_F)
    recipes_list = recipes_data["recipes"]
    ng           = load_json(NG_F)
    nutri_raw    = load_json(NUTRI_F)
    nutri_db     = nutri_raw.get("ingredients", nutri_raw)
    phys_raw     = load_json(PHYS_F)
    phys         = phys_raw.get("ingredients", phys_raw) if isinstance(phys_raw, dict) else {}
    nutri_lookup = build_nutrition_lookup(nutri_db)

    print(f"  Ingrédients dans la DB nutrition : {len(nutri_db)}")
    print(f"  Ingrédients dans phys DB         : {len(phys)}")
    print()

    print("1. Fattoush — bread 3000g → 300g")
    fix_fattoush(recipes_list, nutri_lookup, phys, ng, dry)

    print("\n2. Lentilles — recalcul avec lentilles crues")
    fix_lentil_recipes(recipes_list, nutri_lookup, phys, ng, dry)

    print("\n3. Falafel — huile friture absorption partielle (80ml)")
    fix_falafel(recipes_list, nutri_lookup, phys, ng, dry)

    print("\n4. Pasta plain — sodium sel cuisson exclu")
    fix_pasta_sodium(recipes_list, nutri_lookup, phys, ng, dry)

    print("\n5. Soupe oignon — recalcul nutritionnel")
    fix_soup_onion(recipes_list, nutri_lookup, phys, ng, dry)

    # Sauvegarde
    if not dry:
        # Ajouter entrée dans patch_history
        import datetime
        recipes_data.setdefault("metadata", {}).setdefault("patch_history", []).append({
            "date": datetime.date.today().isoformat(),
            "action": "fix_validated_issues",
            "fixes": 5,
            "description": (
                "Corrections validées: bread fattoush 3000g->300g, "
                "recalcul nutrition lentilles crues, falafel huile partielle 80ml, "
                "pasta sodium sel cuisson exclu, soupe oignon recalcul"
            )
        })
        save_json(RECIPES_F, recipes_data, dry)
        save_json(NG_F, ng, dry)
        print(f"\n  ✅ Fichiers sauvegardés :")
        print(f"     {RECIPES_F}")
        print(f"     {NG_F}")
    else:
        print(f"\n  ℹ️  Mode DRY-RUN — aucun fichier modifié")
        print(f"  Relancer sans --dry-run pour appliquer.")

    print(f"\n{'═'*60}\n")


if __name__ == "__main__":
    main()
