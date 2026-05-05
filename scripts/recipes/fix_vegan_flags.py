import json
from pathlib import Path

def contains_animal_products(text: str) -> bool:
    """Détecte la présence de produits animaux dans le texte."""
    animal_terms = [
        "crème fraîche", "crème", "lait", "beurre", "fromage", "parmesan", 
        "mozzarella", "yaourt", "yogourt", "œuf", "oeuf", "gélatine", "gelatine"
    ]
    text_lower = text.lower()
    return any(term in text_lower for term in animal_terms)


def is_vegan_in_title(title_en: str, title_fr: str) -> bool:
    """Vérifie si le titre indique explicitement que la recette est vegan."""
    text = (title_en + " " + title_fr).lower()
    return any(word in text for word in ["vegan", "végan", "végétalien"])


def main():
    # === CHEMINS ADAPTÉS À TON ORDINATEUR ===
    base_dir = Path(r"C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\scripts\recipes")
    
    input_file = base_dir / "recipes_final.json"
    output_file = base_dir / "recipes_final_fixed_flags.json"
    
    # Vérification de l'existence du fichier
    if not input_file.exists():
        print(f"❌ Erreur : Fichier non trouvé !")
        print(f"Chemin recherché : {input_file}")
        return
    
    print(f"✅ Fichier trouvé : {input_file.name}")
    print("Début de la correction des flags vegan...\n")
    
    # Chargement
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    recipes = data["recipes"]
    changed_to_vegetarian = 0
    light_corrections = 0
    
    # Règles de remplacement pour les cas vegan gardés
    vegan_replacements = {
        "crème fraîche": "crème de coco",
        "crème": "crème de coco",
        "lait": "lait de coco",
        "beurre": "huile de coco",
        "parmesan": "levure nutritionnelle",
        "mozzarella": "fromage végétal",
        "yaourt": "yaourt de coco",
        "yogourt": "yaourt de coco",
        "œuf": "substitut d'œuf",
        "oeuf": "substitut d'œuf",
        "gélatine": "agar-agar"
    }
    
    for recipe in recipes:
        diet = recipe.setdefault("diet_flags", {})
        instructions = recipe.get("instructions", [])
        titles = recipe.get("titles", {})
        
        full_text = " ".join(instructions).lower() if instructions else ""
        
        currently_vegan = diet.get("vegan") is True
        has_animal = contains_animal_products(full_text)
        vegan_title = is_vegan_in_title(titles.get("en", ""), titles.get("fr", ""))
        
        if currently_vegan and has_animal:
            if vegan_title:
                # Cas 1 : Titre indique "vegan" → on garde vegan et on corrige légèrement
                modified = False
                new_instructions = []
                for step in instructions:
                    new_step = step
                    for old, new in vegan_replacements.items():
                        if old.lower() in step.lower():
                            new_step = new_step.replace(old, new).replace(old.capitalize(), new.capitalize())
                            modified = True
                    new_instructions.append(new_step)
                
                if modified:
                    recipe["instructions"] = new_instructions
                    recipe.setdefault("_corrections_log", []).append("light_vegan_replacement")
                    light_corrections += 1
                    
            else:
                # Cas 2 : Pas de "vegan" dans le titre → on passe en vegetarian only
                diet["vegan"] = False
                diet["vegetarian"] = True
                
                # Nettoyage des anciens flags d'alerte
                if "_flags" in recipe:
                    recipe["_flags"] = [f for f in recipe["_flags"] 
                                      if "vegan_flag_but_animal_product" not in f 
                                      and "vegan_alert" not in f]
                
                recipe.setdefault("_corrections_log", []).append("changed_vegan_to_vegetarian")
                changed_to_vegetarian += 1
    
    # Sauvegarde dans le même dossier
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("🎉 Correction terminée avec succès !")
    print(f"   → {changed_to_vegetarian} recettes passées de 'vegan' → 'vegetarian only'")
    print(f"   → {light_corrections} recettes vegan corrigées légèrement dans les instructions")
    print(f"\n📁 Fichier créé :")
    print(f"   {output_file}")

if __name__ == "__main__":
    main()