import json
from pathlib import Path
from collections import defaultdict

def audit_after_fix():
    file_path = Path(r"C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\scripts\recipes\recipes_final_fixed_flags.json")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    recipes = data["recipes"]
    
    vegan_remaining = 0
    low_coverage = 0
    critical = []
    
    for recipe in recipes:
        diet = recipe.get("diet_flags", {})
        instructions = " ".join(recipe.get("instructions", [])).lower()
        title = (recipe.get("titles", {}).get("en", "") + " " + recipe.get("titles", {}).get("fr", "")).lower()
        
        is_vegan = diet.get("vegan") is True
        has_animal = any(term in instructions for term in ["crème", "lait", "beurre", "fromage", "parmesan", "oeuf", "yaourt"])
        
        if is_vegan and has_animal:
            vegan_remaining += 1
            critical.append(recipe["id"])
        
        # Vérification couverture ingrédients très basique
        comp_count = len(recipe.get("composition", []))
        if comp_count > 0 and len(recipe.get("instructions", [])) < 4:
            low_coverage += 1
    
    print("=== AUDIT APRÈS CORRECTION ===")
    print(f"Recettes restantes avec incohérence vegan : {vegan_remaining}")
    print(f"Recettes avec instructions très courtes : {low_coverage}")
    print(f"Exemples de recettes encore problématiques : {critical[:10]}")
    
    return vegan_remaining

if __name__ == "__main__":
    audit_after_fix()