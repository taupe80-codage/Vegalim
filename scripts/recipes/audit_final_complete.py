import json
from pathlib import Path
from collections import defaultdict

def load_recipes(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data

def contains_animal_products(text: str) -> list:
    """Retourne la liste des termes animaux trouvés"""
    terms = ["crème fraîche", "crème", "lait", "beurre", "fromage", "parmesan", 
             "mozzarella", "yaourt", "yogourt", "œuf", "oeuf", "gélatine", 
             "crème de lait", "lait de vache"]
    found = []
    text_lower = text.lower()
    for term in terms:
        if term in text_lower:
            found.append(term)
    return found

def audit_recipe(recipe):
    diet = recipe.get("diet_flags", {})
    instructions = recipe.get("instructions", [])
    titles = recipe.get("titles", {})
    title_en = titles.get("en", "")
    title_fr = titles.get("fr", "")
    composition = recipe.get("composition", [])
    description = recipe.get("description", "")

    full_text = " ".join(instructions).lower()
    
    issues = []
    score = 10.0

    is_vegan = diet.get("vegan") is True

    # 1. Incohérence Vegan
    animal_found = contains_animal_products(full_text)
    if is_vegan and animal_found:
        issues.append(f"INCOHÉRENCE VEGAN : {', '.join(animal_found)}")
        score -= 4.0

    # 2. Instructions trop courtes
    nb_steps = len(instructions)
    if nb_steps == 0:
        issues.append("Aucune instruction")
        score -= 5.0
    elif nb_steps < 5:
        issues.append(f"Trop peu d'étapes ({nb_steps})")
        score -= 2.0
    elif nb_steps < 7:
        issues.append(f"Instructions un peu courtes ({nb_steps})")
        score -= 1.0

    # 3. Couverture des ingrédients
    comp_ings = {item.get("ingredient", "").replace("_", " ").lower() for item in composition if item.get("ingredient")}
    if comp_ings:
        covered = sum(1 for ing in comp_ings if ing in full_text)
        coverage = covered / len(comp_ings)
    else:
        coverage = 0.0

    if coverage < 0.5:
        issues.append(f"Couverture ingrédients très faible : {coverage:.1%}")
        score -= 2.5
    elif coverage < 0.75:
        issues.append(f"Couverture ingrédients faible : {coverage:.1%}")
        score -= 1.5

    # 4. Description
    if len(description) < 80:
        issues.append("Description trop courte")
        score -= 1.0
    elif len(description) < 120:
        issues.append("Description un peu courte")
        score -= 0.5

    final_score = max(0.0, round(score, 1))

    return {
        "id": recipe.get("id"),
        "title": title_en or title_fr,
        "final_score": final_score,
        "issues": issues,
        "is_vegan": is_vegan,
        "animal_terms_found": animal_found,
        "ingredient_coverage": round(coverage, 3),
        "nb_steps": nb_steps,
        "description_length": len(description)
    }


def main():
    # ←←← MODIFIE ICI LE CHEMIN SI NÉCESSAIRE ←←←
    file_path = Path(r"C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\scripts\recipes\recipes_final_9plus_final_deep.json")
    
    if not file_path.exists():
        print(f"❌ Fichier non trouvé : {file_path}")
        print("Vérifie le chemin ou le nom du fichier.")
        return

    data = load_recipes(file_path)
    recipes = data.get("recipes", [])

    print(f"🔍 Audit complet lancé sur {len(recipes)} recettes...\n")

    results = {
        "total_recipes": len(recipes),
        "problematic_recipes": [],
        "vegan_inconsistencies": [],
        "low_coverage": [],
        "low_score": [],
        "score_distribution": defaultdict(int)
    }

    for recipe in recipes:
        audit = audit_recipe(recipe)
        results["score_distribution"][int(audit["final_score"])] += 1

        if audit["issues"]:
            results["problematic_recipes"].append(audit)

            if any("VEGAN" in issue for issue in audit["issues"]):
                results["vegan_inconsistencies"].append(audit)

            if audit["ingredient_coverage"] < 0.7:
                results["low_coverage"].append(audit)

            if audit["final_score"] <= 7.5:
                results["low_score"].append(audit)

    # === RAPPORT ===
    print("=" * 100)
    print("📊 AUDIT FINAL COMPLET")
    print("=" * 100)
    print(f"Total recettes auditées          : {results['total_recipes']}")
    print(f"Recettes avec problèmes          : {len(results['problematic_recipes'])}")
    print(f"Incohérences vegan restantes     : {len(results['vegan_inconsistencies'])}")
    print(f"Recettes avec faible couverture  : {len(results['low_coverage'])}")
    print(f"Recettes avec score ≤ 7.5        : {len(results['low_score'])}")

    print("\n" + "-"*80)
    print("DISTRIBUTION DES SCORES")
    print("-"*80)
    for score in sorted(results["score_distribution"].keys(), reverse=True):
        print(f"Score {score} : {results['score_distribution'][score]} recettes")

    # Affichage des recettes les plus problématiques
    print("\n" + "-"*80)
    print("LISTE DES RECETTES LES PLUS PROBLÉMATIQUES (triées par score)")
    print("-"*80)

    sorted_problems = sorted(results["problematic_recipes"], key=lambda x: x["final_score"])

    for item in sorted_problems[:30]:   # On affiche les 30 pires
        print(f"\n• {item['id']}")
        print(f"  Titre     : {item['title']}")
        print(f"  Score     : {item['final_score']}/10")
        print(f"  Vegan     : {item['is_vegan']}")
        if item['animal_terms_found']:
            print(f"  Animaux   : {', '.join(item['animal_terms_found'])}")
        print(f"  Couverture: {item['ingredient_coverage']:.1%} ({item['nb_steps']} étapes)")
        print(f"  Problèmes :")
        for issue in item['issues']:
            print(f"    - {issue}")

    # Sauvegarde du rapport détaillé
    report_file = file_path.parent / "audit_final_complete_report.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": {
                "total_recipes": results["total_recipes"],
                "problematic": len(results["problematic_recipes"]),
                "vegan_inconsistencies": len(results["vegan_inconsistencies"]),
                "low_coverage": len(results["low_coverage"])
            },
            "score_distribution": dict(results["score_distribution"]),
            "vegan_inconsistencies": results["vegan_inconsistencies"],
            "critical_recipes": sorted_problems[:50]   # Top 50 des pires
        }, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Rapport complet sauvegardé dans : {report_file.name}")
    print("Tu peux maintenant me coller le résultat de cet audit.")

if __name__ == "__main__":
    main()