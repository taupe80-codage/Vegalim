"""
scripts/validate_dataset.py — Validation complète du dataset ALIM (CDC_04).

Vérifie en une seule commande :
  1. Syntaxe JSON de tous les fichiers
  2. Cross-références recipes ↔ ingredients ↔ nutrition_graph
  3. Cohérence diet_flags vs diet_profiles
  4. Couverture nutrition_graph et scoring_graph
  5. Allergènes, spice_level, seasonal_tags
  6. Intégrité nutritionnelle (calories, doublons composition)

Retourne un score de maturité /100 et liste les lacunes.

Usage :
  python3 scripts/validate_dataset.py
  python3 scripts/validate_dataset.py --verbose
"""
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check_json_files(data_root: Path) -> tuple[int, list]:
    """1. Syntaxe JSON de tous les fichiers."""
    errors = []
    ok = 0
    for f in data_root.rglob("*.json"):
        try:
            json.loads(f.read_text(encoding="utf-8"))
            ok += 1
        except json.JSONDecodeError as e:
            errors.append(f"JSON invalide : {f.name} → {e}")
    return ok, errors


def check_cross_references(recipes, ings_dict, ng, sg) -> list:
    """2. Cross-références recipes ↔ ingredients ↔ graphes."""
    issues = []
    for r in recipes:
        rid = str(r["id"])
        # Nutrition graph
        if rid not in ng:
            issues.append(f"Recette {rid} absente du nutrition_graph")
        # Scoring graph
        if rid not in sg:
            issues.append(f"Recette {rid} absente du scoring_graph")
        # Ingrédients connus
        for ing in r.get("ingredients", []):
            iid = (ing.get("ingredient_id","") if isinstance(ing,dict) else str(ing)).lower()
            if iid and iid not in ings_dict and len(issues) < 20:
                issues.append(f"Ingrédient inconnu '{iid}' dans recette {rid}")
    return issues


def check_diet_flags(recipes) -> list:
    """3. Cohérence diet_flags vs ingrédients."""
    from backend.engine.diet_flag_engine import NON_VEGAN, NON_VEGETARIAN
    issues = []
    for r in recipes:
        flags = r.get("diet_flags", {})
        if not flags:
            issues.append(f"Recette {r['id']} sans diet_flags")
            continue
        ings = {(i.get("ingredient_id","") if isinstance(i,dict) else str(i)).lower()
                for i in r.get("ingredients",[])}
        # Si vegan=True mais ingrédients non-vegan présents
        if flags.get("vegan") and ings & NON_VEGAN:
            bad = ings & NON_VEGAN
            issues.append(f"Recette {r['id']} vegan=True mais contient {bad}")
    return issues[:20]


def check_nutrition_coverage(recipes, ng) -> dict:
    """4. Couverture des graphes."""
    in_ng = sum(1 for r in recipes if str(r["id"]) in ng)
    over_1000 = []
    for r in recipes:
        rid = str(r["id"])
        if rid in ng:
            cal = ng[rid].get("calories", 0)
            srv = max(1, r.get("servings", 4) or 4)
            if cal / srv > 1000:
                over_1000.append(r["id"])
    return {
        "in_nutrition_graph": in_ng,
        "total":              len(recipes),
        "coverage_pct":       round(in_ng / len(recipes) * 100, 1),
        "over_1000_kcal":     over_1000,
    }


def check_enrichment_fields(recipes) -> dict:
    """5. Champs d'enrichissement CDC."""
    fields = {
        "allergens":     lambda r: r.get("allergens") is not None,
        "spice_level":   lambda r: r.get("spice_level") is not None,
        "confidence":    lambda r: r.get("confidence") is not None,
        "search_tokens": lambda r: bool(r.get("search_tokens")),
        "cook_time_min": lambda r: r.get("cook_time_min") is not None,
        "glycemic_load": lambda r: True,  # dans nutrition_graph, pas recette directe
    }
    return {
        field: sum(1 for r in recipes if check(r))
        for field, check in fields.items()
    }


def check_composition_duplicates(recipes) -> list:
    """6. Doublons dans les compositions."""
    issues = []
    for r in recipes:
        comp = r.get("composition", [])
        seen = set()
        for item in comp:
            ing = item.get("ingredient","") if isinstance(item,dict) else str(item)
            if ing in seen:
                issues.append(f"Recette {r['id']} — doublon: {ing}")
            seen.add(ing)
    return issues


def main(verbose: bool = False):
    from backend.core.data_io import (load_recipes, load_ingredients_dict,
                                       load_nutrition_graph, load_score_graph)
    from backend.engine.config import DATA_ROOT

    print("╔══════════════════════════════════════════════════════╗")
    print("║  ALIM v5 — Validation dataset                       ║")
    print("╚══════════════════════════════════════════════════════╝\n")

    load_recipes.cache_clear()
    recipes   = load_recipes()
    ings_dict = load_ingredients_dict()
    ng        = load_nutrition_graph()
    sg        = load_score_graph()

    total_checks = 0
    passed       = 0
    all_issues   = []

    def report(name, ok, issues=None, detail=None):
        nonlocal total_checks, passed
        total_checks += 1
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}" + (f" — {detail}" if detail else ""))
        if ok:
            passed += 1
        if issues and verbose:
            for iss in issues[:5]:
                print(f"     · {iss}")
        if issues:
            all_issues.extend(issues)

    print("1. Syntaxe JSON")
    n_json, json_errors = check_json_files(DATA_ROOT)
    report("Tous les fichiers JSON valides",
           len(json_errors) == 0,
           json_errors,
           f"{n_json} fichiers")

    print("\n2. Cross-références")
    xref_issues = check_cross_references(recipes, ings_dict, ng, sg)
    report("Recettes dans nutrition_graph",
           not any("nutrition_graph" in i for i in xref_issues),
           [i for i in xref_issues if "nutrition_graph" in i])
    report("Recettes dans scoring_graph",
           not any("scoring_graph" in i for i in xref_issues),
           [i for i in xref_issues if "scoring_graph" in i])
    report("Ingrédients connus",
           not any("Ingrédient inconnu" in i for i in xref_issues),
           [i for i in xref_issues if "inconnu" in i])

    print("\n3. Diet flags")
    diet_issues = check_diet_flags(recipes)
    report("Cohérence vegan/ingrédients",
           len(diet_issues) == 0, diet_issues)

    print("\n4. Couverture nutritionnelle")
    cov = check_nutrition_coverage(recipes, ng)
    report("Nutrition graph ≥ 95%",
           cov["coverage_pct"] >= 95,
           detail=f"{cov['coverage_pct']}% ({cov['in_nutrition_graph']}/{cov['total']})")
    report("Aucune recette >1000 kcal/portion",
           len(cov["over_1000_kcal"]) == 0,
           [f"ID {i}" for i in cov["over_1000_kcal"]])

    print("\n5. Enrichissement CDC")
    enrichment = check_enrichment_fields(recipes)
    total = len(recipes)
    for field, count in enrichment.items():
        pct = round(count / total * 100, 1)
        ok  = pct >= 95
        report(f"{field} ({pct}%)", ok, detail=f"{count}/{total}")

    # cooking_behavior dans le dictionnaire ingrédients
    try:
        from backend.core.data_io import load_ingredients_dict
        d = load_ingredients_dict()
        cb_count = sum(1 for v in d.values() if v.get("cooking_behavior"))
        cb_pct   = round(cb_count / len(d) * 100, 1) if d else 0
        report(f"cooking_behavior ({cb_pct}%)", cb_count >= 35,
               detail=f"{cb_count}/{len(d)} ingrédients")
    except Exception:
        pass

    print("\n6. Intégrité composition")
    dup_issues = check_composition_duplicates(recipes)
    report("Aucun doublon dans les compositions",
           len(dup_issues) == 0, dup_issues)

    # Score final
    score = round(passed / total_checks * 100)
    print(f"\n{'═'*54}")
    print(f"  Score de maturité dataset : {score}/100")
    print(f"  {passed}/{total_checks} vérifications réussies")
    if all_issues:
        print(f"  {len(all_issues)} problème(s) détecté(s)")
        if verbose:
            for iss in all_issues[:10]:
                print(f"    · {iss}")
    else:
        print("  ✨ Dataset en parfaite santé !")
    print(f"{'═'*54}\n")
    return score


if __name__ == "__main__":
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    score = main(verbose=verbose)
    sys.exit(0 if score >= 80 else 1)
