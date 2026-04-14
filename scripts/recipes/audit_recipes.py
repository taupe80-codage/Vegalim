"""
scripts/audit_coherence_recettes.py
====================================
Audit de cohérence des données de recettes basé sur les données de référence vérifiées.

Vérifie :
  A. Ingrédients inconnus du dictionnaire
  B. Cohérence diet_flags vs ingrédients (vegan/végétarien/gluten/lactose/soja/œufs/noix)
  C. Cohérence allergènes tags vs dictionnaire ingrédients
  D. Quantités aberrantes (trop grandes ou nulles)
  E. Unités incohérentes (liquides en g, solides en ml)
  F. Couverture nutrition_graph (recettes absentes)
  G. Valeurs nutritionnelles suspectes (calories anormales, macros incohérentes)
  H. Doublons de composition
  I. Champs obligatoires manquants
  J. Recettes en double (même titre)

Usage :
  python scripts/audit_coherence_recettes.py
  python scripts/audit_coherence_recettes.py --verbose
  python scripts/audit_coherence_recettes.py --fix        (génère un rapport JSON)
  python scripts/audit_coherence_recettes.py --export     (exporte CSV des anomalies)
"""

import sys
import json
import csv
import argparse
from pathlib import Path
from collections import defaultdict
from datetime import datetime

# Fix encodage Windows (cp1252 -> utf-8)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")


# ─── Chemins ──────────────────────────────────────────────────────────────────
ROOT        = Path(__file__).resolve().parent.parent
RECIPES_F   = ROOT / "backend/data/recipes/recipes.json"
DICT_F      = ROOT / "backend/data/ingredients/ingredients_dictionary.json"
NUTRITION_F = ROOT / "backend/data/nutrition/nutrition_database.json"
NG_F        = ROOT / "backend/data/graphs/recipe_nutrition_graph_v1.json"
PHYS_F      = ROOT / "backend/data/ingredients/ingredient_physical.json"
REPORT_DIR  = ROOT / "backend/data/logs"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ─── Ingrédients non-vegan / non-végétariens (liste de référence) ─────────────
NON_VEGAN = {
    "egg", "oeuf", "oeufs", "eggs",
    "milk", "lait", "butter", "beurre", "cream", "creme", "creme_fraiche",
    "yogurt", "yaourt", "yoghurt", "cheese", "fromage", "parmesan",
    "ghee", "honey", "miel",
    "anchovies", "anchois", "worcestershire_sauce",
}
NON_VEGETARIAN = {
    "chicken", "beef", "pork", "lamb", "fish", "tuna", "salmon",
    "shrimp", "prawn", "gelatin", "gelatine", "lard",
    "bouillon_cube", "fond_de_veau",
}

# Ingrédients contenant du gluten
GLUTEN_INGREDIENTS = {
    "flour", "farine", "wheat", "ble", "gluten", "bread", "pain",
    "pasta", "pates", "semolina", "semoule", "couscous", "bulgur",
    "barley", "orge", "rye", "seigle", "spelt", "epeautre",
    "seitan", "soy_sauce", "sauce_soja", "tamari",
    "gochujang",  # contient souvent du blé
    "miso",
    "breadcrumbs", "chapelure",
}

# Ingrédients contenant du lactose
LACTOSE_INGREDIENTS = {
    "milk", "lait", "butter", "beurre", "cream", "creme", "creme_fraiche",
    "yogurt", "yaourt", "yoghurt", "cheese", "fromage", "parmesan",
    "mozzarella", "ricotta", "feta", "brie", "camembert",
    "ghee", "whey", "lait_concentre", "lait_coco",  # lait_coco est sans lactose !
}
LACTOSE_INGREDIENTS.discard("lait_coco")

# Ingrédients contenant du soja
SOY_INGREDIENTS = {
    "tofu", "soy_sauce", "sauce_soja", "tamari", "tempeh",
    "edamame", "miso", "soy_milk", "lait_soja",
    "gochujang",  # peut contenir du soja
}

# Ingrédients contenant des œufs
EGG_INGREDIENTS = {
    "egg", "oeuf", "oeufs", "eggs", "mayonnaise",
}

# Ingrédients = fruits à coque
NUT_INGREDIENTS = {
    "almond", "amande", "walnut", "noix", "cashew", "noix_de_cajou",
    "pistachio", "pistache", "pecan", "hazelnut", "noisette",
    "pine_nut", "pignon", "macadamia", "peanut", "cacahuete",
    "tahini", "sesame", "sesame_seed", "sesame_oil", "huile_sesame",
}

# Ingrédients liquides typiques (doivent être en ml ou L)
LIQUID_INGREDIENTS = {
    "oil", "olive_oil", "vegetable_oil", "sesame_oil", "coconut_oil",
    "milk", "lait", "lait_coco", "water", "eau", "broth", "bouillon",
    "vinegar", "vinaigre", "soy_sauce", "sauce_soja", "tamari",
    "lemon_juice", "jus_citron", "tahini", "cream", "creme",
    "wine", "vin", "beer", "biere", "honey", "miel",
    "maple_syrup", "sirop_erable", "vegetable_stock",
}

# Seuils quantités aberrantes (g ou ml par portion)
MAX_INGREDIENT_G   = 1500  # > 1.5kg d'un ingrédient = très suspect
MIN_INGREDIENT_G   = 0     # 0 = absurde
MAX_SALT_G         = 30    # > 30g de sel = dangereux
MAX_SUGAR_G        = 200   # > 200g de sucre = anormal
MAX_OIL_ML         = 300   # > 300ml d'huile = anormal


# ─── Chargement des données ───────────────────────────────────────────────────
def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_all():
    print("  Chargement des fichiers de référence...")
    data       = load_json(RECIPES_F)
    recipes    = data.get("recipes", data) if isinstance(data, dict) else data
    if isinstance(data, dict) and "recipes" in data:
        recipes = data["recipes"]
    elif isinstance(data, list):
        recipes = data

    dict_data  = load_json(DICT_F)
    ings_list  = dict_data.get("ingredients", [])
    ings_dict  = {i["id"].lower(): i for i in ings_list}

    nutri_data = load_json(NUTRITION_F)
    nutri_db   = nutri_data.get("ingredients", nutri_data)

    # Construire lookup étendu : id + aliases
    nutri_lookup = {}
    for k, v in nutri_db.items():
        nutri_lookup[k.lower()] = v
        for alias in v.get("aliases", []):
            nutri_lookup[alias.lower()] = v

    ng = load_json(NG_F)

    return recipes, ings_dict, nutri_db, nutri_lookup, ng


# ─── A. Ingrédients inconnus ─────────────────────────────────────────────────
def check_unknown_ingredients(recipes, ings_dict, nutri_lookup):
    issues = []
    known_ids = set(ings_dict.keys()) | set(nutri_lookup.keys())
    unknown_global = defaultdict(list)

    for r in recipes:
        rid = r["id"]
        for item in r.get("composition", []):
            if not isinstance(item, dict):
                continue
            ing = item.get("ingredient", "").lower().strip()
            if not ing:
                continue
            if ing not in known_ids:
                unknown_global[ing].append(rid)

    for ing, rids in sorted(unknown_global.items()):
        issues.append({
            "type": "unknown_ingredient",
            "ingredient": ing,
            "recipes": rids[:5],
            "count": len(rids),
            "severity": "warning" if len(rids) < 3 else "error",
        })
    return issues


# ─── B. Cohérence diet_flags ──────────────────────────────────────────────────
def check_diet_flags(recipes):
    issues = []
    for r in recipes:
        rid = r["id"]
        flags = r.get("diet_flags", {})
        if not flags:
            continue

        ings = {
            item.get("ingredient", "").lower()
            for item in r.get("composition", [])
            if isinstance(item, dict)
        }

        # Vegan
        if flags.get("vegan"):
            bad = ings & (NON_VEGAN | NON_VEGETARIAN)
            if bad:
                issues.append({
                    "type": "diet_flag_mismatch",
                    "recipe_id": rid,
                    "flag": "vegan=True",
                    "problem": f"Contient: {', '.join(sorted(bad))}",
                    "severity": "error",
                })

        # Végétarien
        if flags.get("vegetarian"):
            bad = ings & NON_VEGETARIAN
            if bad:
                issues.append({
                    "type": "diet_flag_mismatch",
                    "recipe_id": rid,
                    "flag": "vegetarian=True",
                    "problem": f"Contient: {', '.join(sorted(bad))}",
                    "severity": "error",
                })

        # Vegan implique végétarien
        if flags.get("vegan") and not flags.get("vegetarian"):
            issues.append({
                "type": "diet_flag_mismatch",
                "recipe_id": rid,
                "flag": "vegan=True mais vegetarian=False",
                "problem": "Incohérence logique : vegan ⊂ végétarien",
                "severity": "error",
            })

        # Gluten-free
        if flags.get("gluten_free"):
            bad = ings & GLUTEN_INGREDIENTS
            if bad:
                issues.append({
                    "type": "diet_flag_mismatch",
                    "recipe_id": rid,
                    "flag": "gluten_free=True",
                    "problem": f"Contient gluten potentiel: {', '.join(sorted(bad))}",
                    "severity": "warning",
                })

        # Lactose-free
        if flags.get("lactose_free"):
            bad = ings & LACTOSE_INGREDIENTS
            if bad:
                issues.append({
                    "type": "diet_flag_mismatch",
                    "recipe_id": rid,
                    "flag": "lactose_free=True",
                    "problem": f"Contient lactose potentiel: {', '.join(sorted(bad))}",
                    "severity": "warning",
                })

        # Nut-free
        if flags.get("nut_free"):
            bad = ings & NUT_INGREDIENTS
            if bad:
                issues.append({
                    "type": "diet_flag_mismatch",
                    "recipe_id": rid,
                    "flag": "nut_free=True",
                    "problem": f"Contient fruits à coque/sésame: {', '.join(sorted(bad))}",
                    "severity": "warning",
                })

    return issues


# ─── C. Cohérence allergènes tags ─────────────────────────────────────────────
def check_allergen_tags(recipes, ings_dict, nutri_lookup):
    """Vérifie que les tags allergènes reflètent les ingrédients réels."""
    issues = []

    # Mapping allergène EU → ingrédients déclencheurs (aligné avec tag_allergens.py)
    ALLERGEN_TRIGGERS = {
        "gluten": {
            "flour", "wheat_flour", "whole_wheat_flour", "rye_flour", "spelt_flour",
            "bread", "baguette", "sourdough_bread", "pain_pita", "pita",
            "breadcrumbs", "panko_breadcrumbs", "pasta", "noodles", "udon",
            "soba_noodles", "ramen", "couscous", "bulgur", "boulgour", "semolina",
            "semoule", "seitan", "wheat_gluten", "oats", "rolled_oats", "oat",
            "barley", "wonton_wrapper", "gyoza_wrapper", "empanada_dough",
            "filo_pastry", "puff_pastry", "pie_dough", "shortcrust_pastry",
            "ladyfinger", "digestive_biscuit", "reshteh_noodles",
            "soy_sauce", "sauce_soja", "dark_soy_sauce", "light_soy_sauce",
            "gochujang", "miso",
        },
        "oeufs": {
            "egg", "oeuf", "oeufs", "eggs", "egg_white", "egg_yolk",
            "mayonnaise", "ladyfinger", "creme_anglaise", "custard",
        },
        "lait": {
            "milk", "lait", "butter", "beurre", "salted_butter", "clarified_butter",
            "cream", "creme", "creme_fraiche", "heavy_cream", "whipping_cream", "sour_cream",
            "yogurt", "yaourt", "yoghurt", "ghee",
            "fromage", "cheese", "parmesan", "pecorino_romano", "mozzarella",
            "ricotta", "ricotta_salata", "feta", "brie", "camembert", "comte",
            "gruyere", "gruyere_cheese", "manchego", "cheddar", "emmental",
            "cream_cheese", "fromage_blanc", "fromage_frais", "paneer",
            "mascarpone", "kashk", "queijo", "fresh_tome_cheese", "roquefort",
            "blue_cheese", "goat_cheese", "chevre", "labneh", "kefir",
            "condensed_milk", "creme_chantilly", "lait_concentre", "whey",
        },
        "soja": {
            "tofu", "tofu_soyeux", "sauce_soja", "soy_sauce", "dark_soy_sauce",
            "light_soy_sauce", "tamari", "tempeh", "edamame", "soybean",
            "lait_soja", "soy_milk", "miso",
        },
        "sesame": {
            "sesame", "sesame_seed", "sesame_oil", "tahini", "huile_sesame",
            "black_sesame_seeds", "sesame_paste",
        },
        "arachides": {
            "peanut", "cacahuete", "peanut_butter", "pate_d_arachide",
        },
        "fruits_a_coque": {
            "almond", "amande", "almonds", "almond_butter", "almond_oil",
            "walnut", "noix", "walnuts", "walnut_oil",
            "cashew", "cashews", "noix_de_cajou", "cashew_cream",
            "pistachio", "pistache", "pistachios",
            "hazelnut", "noisette", "hazelnuts", "hazelnut_oil",
            "pecan", "pecans", "pine_nut", "pine_nuts", "pignon",
            "macadamia", "brazil_nut",
        },
        "celeri": {
            "celery", "celeri", "celeriac", "celery_root", "celery_salt", "celeri_rave",
        },
        "moutarde": {
            "mustard", "moutarde", "mustard_seeds", "dijon_mustard",
            "whole_grain_mustard", "moutarde_en_grains",
        },
        "sulfites": {
            "wine", "red_wine", "white_wine", "wine_vinegar", "sherry_vinegar",
            "balsamic_vinegar", "vinaigre_balsamique", "dried_fruit",
            "dried_apricot", "dried_fig",
        },
        "lupin": {"lupin_flour", "lupin"},
    }

    for r in recipes:
        rid = r["id"]
        allergen_tags = {t.lower() for t in r.get("tags", {}).get("allergens", [])}
        ings = {
            item.get("ingredient", "").lower()
            for item in r.get("composition", [])
            if isinstance(item, dict)
        }

        for allergen, triggers in ALLERGEN_TRIGGERS.items():
            declared = allergen in allergen_tags
            present  = bool(ings & triggers)

            if present and not declared:
                issues.append({
                    "type": "allergen_not_declared",
                    "recipe_id": rid,
                    "allergen": allergen,
                    "problem": f"Ingrédient déclencheur présent mais allergène non déclaré: {ings & triggers}",
                    "severity": "error",
                })
            # Note: ne pas signaler si déclaré sans ingrédient connu (peut être dans sauce composite)

    return issues




# ─── D & E. Quantités et unités aberrantes ────────────────────────────────────
def check_quantities_and_units(recipes, nutri_lookup):
    issues = []

    for r in recipes:
        rid = r["id"]
        servings = max(1, r.get("servings") or 1)

        for item in r.get("composition", []):
            if not isinstance(item, dict):
                continue
            ing  = item.get("ingredient", "").lower()
            qty  = item.get("quantity") or 0
            unit = (item.get("unit") or "g").lower()

            # D. Quantité nulle ou négative
            if qty <= 0:
                issues.append({
                    "type": "qty_zero_or_negative",
                    "recipe_id": rid,
                    "ingredient": ing,
                    "quantity": qty,
                    "unit": unit,
                    "severity": "error",
                })
                continue

            # D. Quantité extrêmement élevée
            if unit in ("g", "ml") and qty > MAX_INGREDIENT_G:
                issues.append({
                    "type": "qty_abnormally_high",
                    "recipe_id": rid,
                    "ingredient": ing,
                    "quantity": qty,
                    "unit": unit,
                    "severity": "warning" if qty < 3000 else "error",
                })

            # D. Sel excessif
            if ing in ("salt", "sel") and unit == "g" and qty > MAX_SALT_G:
                issues.append({
                    "type": "qty_salt_excessive",
                    "recipe_id": rid,
                    "ingredient": ing,
                    "quantity": qty,
                    "unit": unit,
                    "severity": "error",
                })

            # D. Sucre excessif
            if ing in ("sugar", "sucre") and unit in ("g", "ml") and qty > MAX_SUGAR_G:
                issues.append({
                    "type": "qty_sugar_excessive",
                    "recipe_id": rid,
                    "ingredient": ing,
                    "quantity": qty,
                    "unit": unit,
                    "severity": "warning",
                })

            # E. Liquide en grammes (sauf ingrédients ambigus)
            if ing in LIQUID_INGREDIENTS and unit == "g" and qty > 5:
                # Tolérance : tahini, miel, miso peuvent être en g
                ambiguous = {"tahini", "honey", "miel", "miso", "paste", "pate", "butter", "beurre"}
                if not any(a in ing for a in ambiguous):
                    issues.append({
                        "type": "unit_liquid_in_g",
                        "recipe_id": rid,
                        "ingredient": ing,
                        "quantity": qty,
                        "unit": unit,
                        "severity": "warning",
                    })

            # E. Solide en ml  (sauf condiments liquides)
            if unit == "ml" and ing not in LIQUID_INGREDIENTS and qty > 5:
                # Vérifie si c'est vraiment solide (dans nutrition_db)
                nutri = nutri_lookup.get(ing, {})
                # Si pas dans liquide et pas un condiment
                condiments = {"yogurt", "yaourt", "ketchup", "sauce", "paste", "pate"}
                if not any(c in ing for c in condiments):
                    issues.append({
                        "type": "unit_solid_in_ml",
                        "recipe_id": rid,
                        "ingredient": ing,
                        "quantity": qty,
                        "unit": unit,
                        "severity": "info",
                    })

    return issues


# ─── F. Couverture nutrition_graph ───────────────────────────────────────────
def check_nutrition_coverage(recipes, ng):
    issues = []
    for r in recipes:
        rid = r["id"]
        if rid not in ng:
            issues.append({
                "type": "missing_nutrition_graph",
                "recipe_id": rid,
                "title": r.get("titles", {}).get("fr", ""),
                "severity": "error",
            })
    return issues


# ─── G. Valeurs nutritionnelles suspectes ────────────────────────────────────
def check_nutrition_values(recipes, ng):
    issues = []
    for r in recipes:
        rid = r["id"]
        servings = max(1, r.get("servings") or 1)
        if rid not in ng:
            continue
        nutri = ng[rid]

        cal = nutri.get("calories", 0)
        prot = nutri.get("protein", 0)
        carbs = nutri.get("carbs", 0)
        fat = nutri.get("fat", 0)
        fiber = nutri.get("fiber", 0)

        # Calories totales (pour toute la recette)
        cal_total = cal * servings if cal < 2000 else cal  # pour gérer les cas où cal = total

        # G1. Calories par portion anormalement élevées (>1200 kcal)
        cal_per_serving = cal
        if cal_per_serving > 1200:
            issues.append({
                "type": "calories_too_high",
                "recipe_id": rid,
                "calories_per_serving": cal_per_serving,
                "severity": "error" if cal_per_serving > 2000 else "warning",
            })

        # G2. Calories anormalement basses (<30 kcal pour un plat)
        if 0 < cal_per_serving < 30:
            issues.append({
                "type": "calories_too_low",
                "recipe_id": rid,
                "calories_per_serving": cal_per_serving,
                "severity": "warning",
            })

        # G3. Fibres > glucides (impossibilité biochimique)
        if fiber > carbs and carbs > 0:
            issues.append({
                "type": "fiber_exceeds_carbs",
                "recipe_id": rid,
                "fiber": fiber,
                "carbs": carbs,
                "severity": "error",
            })

        # G4. Macros totales peu cohérentes avec les calories théoriques
        # Calories théoriques = prot*4 + carbs*4 + fat*9
        cal_theo = prot * 4 + carbs * 4 + fat * 9
        if cal > 10 and cal_theo > 10:
            ratio = abs(cal - cal_theo) / max(cal, cal_theo)
            if ratio > 0.40:  # Écart > 40%
                issues.append({
                    "type": "macro_calorie_mismatch",
                    "recipe_id": rid,
                    "calories_declared": cal,
                    "calories_computed": round(cal_theo, 1),
                    "ecart_pct": round(ratio * 100, 1),
                    "severity": "warning",
                })

        # G5. Sodium extrêmement élevé par portion (>3000mg)
        sodium = nutri.get("sodium", 0)
        if sodium > 3000:
            issues.append({
                "type": "sodium_very_high",
                "recipe_id": rid,
                "sodium_mg": sodium,
                "severity": "warning",
            })

    return issues


# ─── H. Doublons de composition ──────────────────────────────────────────────
def check_composition_duplicates(recipes):
    issues = []
    for r in recipes:
        rid = r["id"]
        seen = {}
        for item in r.get("composition", []):
            if not isinstance(item, dict):
                continue
            ing = item.get("ingredient", "").lower()
            if ing in seen:
                issues.append({
                    "type": "duplicate_ingredient",
                    "recipe_id": rid,
                    "ingredient": ing,
                    "severity": "error",
                })
            seen[ing] = True
    return issues


# ─── I. Champs obligatoires manquants ────────────────────────────────────────
REQUIRED_FIELDS = ["id", "titles", "composition", "instructions", "servings", "diet_flags"]
REQUIRED_TITLE_FIELDS = ["original", "fr"]

def check_required_fields(recipes):
    issues = []
    for r in recipes:
        rid = r.get("id", "??")
        for field in REQUIRED_FIELDS:
            if field not in r or r[field] is None:
                issues.append({
                    "type": "missing_required_field",
                    "recipe_id": rid,
                    "field": field,
                    "severity": "error",
                })

        # Titres
        titles = r.get("titles", {})
        for tf in REQUIRED_TITLE_FIELDS:
            if not titles.get(tf):
                issues.append({
                    "type": "missing_title",
                    "recipe_id": rid,
                    "field": f"titles.{tf}",
                    "severity": "warning",
                })

        # Composition vide
        if not r.get("composition"):
            issues.append({
                "type": "empty_composition",
                "recipe_id": rid,
                "severity": "error",
            })

        # Instructions vides
        if not r.get("instructions"):
            issues.append({
                "type": "empty_instructions",
                "recipe_id": rid,
                "severity": "warning",
            })

        # Servings = 0 ou None
        s = r.get("servings")
        if not s or s <= 0:
            issues.append({
                "type": "invalid_servings",
                "recipe_id": rid,
                "servings": s,
                "severity": "warning",
            })

    return issues


# ─── J. Recettes en double (titre) ───────────────────────────────────────────
def check_duplicate_titles(recipes):
    issues = []
    title_map = defaultdict(list)
    for r in recipes:
        title_fr = r.get("titles", {}).get("fr", "").strip().lower()
        if title_fr:
            title_map[title_fr].append(r["id"])

    for title, ids in title_map.items():
        if len(ids) > 1:
            issues.append({
                "type": "duplicate_title",
                "title_fr": title,
                "recipe_ids": ids,
                "count": len(ids),
                "severity": "warning",
            })
    return issues


# ─── Rapport final ────────────────────────────────────────────────────────────
def severity_color(s):
    return {"error": "❌", "warning": "⚠️ ", "info": "ℹ️ "}.get(s, "❓")


def print_section(name, issues, verbose, max_show=5):
    errors   = [i for i in issues if i.get("severity") == "error"]
    warnings = [i for i in issues if i.get("severity") == "warning"]
    infos    = [i for i in issues if i.get("severity") == "info"]

    total = len(issues)
    ok    = total == 0

    icon = "✅" if ok else ("❌" if errors else "⚠️ ")
    print(f"  {icon} {name}  ({len(errors)} erreurs, {len(warnings)} avertissements, {len(infos)} infos)")

    if verbose and not ok:
        shown = issues[:max_show]
        for iss in shown:
            sev  = severity_color(iss.get("severity", "info"))
            typ  = iss.get("type", "")
            rid  = iss.get("recipe_id", iss.get("ingredient", ""))
            prob = iss.get("problem", iss.get("field", iss.get("allergen",
                   iss.get("ingredient", iss.get("title_fr", "")))))
            qty  = iss.get("quantity", "")
            unit = iss.get("unit", "")
            qty_str = f" {qty}{unit}" if qty else ""
            print(f"       {sev} [{typ}] {rid}{qty_str}" + (f" → {prob}" if prob else ""))
        if len(issues) > max_show:
            print(f"       … et {len(issues) - max_show} autre(s)")

    return ok, errors, warnings


def main():
    parser = argparse.ArgumentParser(description="Audit de cohérence des recettes ALIM v6")
    parser.add_argument("--verbose", "-v", action="store_true", help="Affichage détaillé")
    parser.add_argument("--fix",     "-f", action="store_true", help="Exporter rapport JSON")
    parser.add_argument("--export",  "-e", action="store_true", help="Exporter CSV des anomalies")
    args = parser.parse_args()

    verbose = args.verbose

    print()
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║  ALIM v6 — Audit de Cohérence des Recettes                 ║")
    print(f"║  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print()

    # Chargement
    recipes, ings_dict, nutri_db, nutri_lookup, ng = load_all()
    total_recipes = len(recipes)
    print(f"  📦 {total_recipes} recettes chargées | {len(ings_dict)} ingrédients dict | {len(ng)} dans nutrition_graph")
    print()

    all_issues = []
    section_results = []

    def run_section(label, func, *fargs):
        issues = func(*fargs)
        ok, errors, warnings = print_section(label, issues, verbose)
        all_issues.extend(issues)
        section_results.append((label, ok, len(errors), len(warnings)))
        return issues

    # ── Exécution des vérifications ──────────────────────────────────────────
    print("A. Ingrédients inconnus du dictionnaire")
    run_section("Ingrédients reconnus",    check_unknown_ingredients, recipes, ings_dict, nutri_lookup)

    print("\nB. Cohérence diet_flags")
    run_section("diet_flags cohérents",    check_diet_flags, recipes)

    print("\nC. Cohérence allergènes déclarés")
    run_section("Allergènes déclarés",     check_allergen_tags, recipes, ings_dict, nutri_lookup)

    print("\nD-E. Quantités & Unités")
    run_section("Quantités & Unités",      check_quantities_and_units, recipes, nutri_lookup)

    print("\nF. Couverture nutrition_graph")
    run_section("Recettes dans nu. graph", check_nutrition_coverage, recipes, ng)

    print("\nG. Valeurs nutritionnelles")
    run_section("Nutritions cohérentes",   check_nutrition_values, recipes, ng)

    print("\nH. Doublons de composition")
    run_section("Pas de doublons ing.",    check_composition_duplicates, recipes)

    print("\nI. Champs obligatoires")
    run_section("Champs complets",         check_required_fields, recipes)

    print("\nJ. Titres doublons")
    run_section("Titres uniques",          check_duplicate_titles, recipes)

    # ── Score de maturité ────────────────────────────────────────────────────
    total_errors   = sum(i.get("severity") == "error"   for i in all_issues)
    total_warnings = sum(i.get("severity") == "warning" for i in all_issues)
    total_infos    = sum(i.get("severity") == "info"    for i in all_issues)

    ok_sections = sum(1 for _, ok, _, _ in section_results if ok)
    score = round(ok_sections / len(section_results) * 100)

    # Pénalités sur le score
    penalty_errors   = min(30, total_errors   * 2)
    penalty_warnings = min(15, total_warnings * 0.5)
    score_adjusted = max(0, score - penalty_errors - penalty_warnings)

    print()
    print(f"{'═' * 64}")
    print(f"  📊 Score de maturité dataset : {score_adjusted:.0f}/100")
    print(f"     Sections OK  : {ok_sections}/{len(section_results)}")
    print(f"     ❌ Erreurs   : {total_errors}")
    print(f"     ⚠️  Avertiss.: {total_warnings}")
    print(f"     ℹ️  Infos    : {total_infos}")

    if total_errors == 0 and total_warnings == 0:
        print("  ✨ Dataset en parfaite cohérence !")
    elif total_errors == 0:
        print("  ✅ Aucune erreur critique — corriger les avertissements.")
    else:
        print(f"  ⚠️  {total_errors} erreur(s) critique(s) à corriger.")

    print(f"{'═' * 64}")
    print()

    # ── Export JSON ──────────────────────────────────────────────────────────
    if args.fix or args.export:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    if args.fix:
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_recipes": total_recipes,
            "score": score_adjusted,
            "summary": {
                "errors": total_errors,
                "warnings": total_warnings,
                "infos": total_infos,
            },
            "sections": [
                {"label": l, "ok": ok, "errors": e, "warnings": w}
                for l, ok, e, w in section_results
            ],
            "issues": all_issues,
        }
        out_path = REPORT_DIR / f"coherence_report_{ts}.json"
        out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  📄 Rapport JSON → {out_path}")

    if args.export:
        csv_path = REPORT_DIR / f"coherence_anomalies_{ts}.csv"
        fields = ["type", "severity", "recipe_id", "ingredient", "problem", "field",
                  "allergen", "quantity", "unit", "title_fr", "count"]
        with csv_path.open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            w.writeheader()
            w.writerows(all_issues)
        print(f"  📊 Export CSV   → {csv_path}")

    return 0 if score_adjusted >= 75 else 1


if __name__ == "__main__":
    sys.exit(main())
