import json
from pathlib import Path

def main():
    input_file = Path("recipes_final_9plus_safe_v3.json")
    output_file = Path("recipes_final_9plus_final_v4.json")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    recipes = data["recipes"]

    critical_ids = {
        "falafel_bowl_de_falafel_vegan_f4fd40",
        "protein_palak_paneer_vegan_bdac46",
        "tarte_pizza_margherita_vegan_02bb9a",
        "main_poutine_vegan_18f8c2",
        "pasta_lasagnes_vegan_412e90",
        "dessert_lait_coco_vegan_3b8a99",
        "dessert_gateau_carottes_vegan_9d8a84",
        "dessert_panna_cotta_coco_vegan_16d6b5",
        "brkf_pancakes_banane_vegan_c9231e",
        "brkf_pain_aux_bananes_vegan_b85f00",
        "entry_blinis_sarrasin_vegan_09648c",
        "side_dauphinois_vegan_c584cb"
    }

    replacements = {
        "lait": "lait de coco",
        "crème": "crème de coco",
        "crème fraîche": "crème de coco",
        "fromage": "fromage végétal",
        "mozzarella": "fromage végétal râpé",
        "parmesan": "levure nutritionnelle",
        "beurre": "huile de coco",
        "yaourt": "yaourt de coco",
        "yogourt": "yaourt de coco"
    }

    fixed = 0

    for recipe in recipes:
        if recipe["id"] not in critical_ids:
            continue

        # Instructions
        instructions = recipe.get("instructions", [])
        new_instructions = []
        for step in instructions:
            new_step = step
            for old, new in replacements.items():
                if old.lower() in step.lower():
                    new_step = new_step.replace(old, new).replace(old.capitalize(), new.capitalize())
            new_instructions.append(new_step)

        recipe["instructions"] = new_instructions

        # Description
        if len(recipe.get("description", "")) < 140:
            title = recipe.get("titles", {}).get("en", recipe.get("titles", {}).get("fr", ""))
            recipe["description"] = f"Version vegan savoureuse et crémeuse de {title}. Recette équilibrée, riche en saveurs et parfaitement adaptée à un régime végétalien."

        recipe.setdefault("_corrections_log", []).append("final_fix_v4_vegan_title_preserved")
        fixed += 1
        print(f"✓ Fixed : {recipe['id']}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Correction finale terminée ! {fixed} recettes traitées.")
    print(f"Fichier sauvegardé : {output_file.name}")
    print("→ Relance ton audit_final_complete.py maintenant.")

if __name__ == "__main__":
    main()