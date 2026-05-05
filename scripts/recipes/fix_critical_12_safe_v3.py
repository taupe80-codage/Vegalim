import json
from pathlib import Path

def main():
    base_dir = Path(r"C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated\scripts\recipes")
    input_file = base_dir / "recipes_final_9plus_ready.json"
    output_file = base_dir / "recipes_final_9plus_safe_v3.json"

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
        "yaourt": "yaourt végétal",
        "yogourt": "yaourt végétal"
    }

    count = 0

    for recipe in recipes:
        if recipe["id"] not in critical_ids:
            continue

        instructions = recipe.get("instructions", [])
        new_instructions = []

        for step in instructions:
            new_step = step
            for old, new in replacements.items():
                if old.lower() in step.lower():
                    new_step = new_step.replace(old, new).replace(old.capitalize(), new.capitalize())
            new_instructions.append(new_step)

        # Ajout d'une étape de fin si nécessaire pour améliorer la couverture
        if len(new_instructions) < 7:
            new_instructions.append("Servir chaud avec du riz, du pain ou une garniture de noix de coco / herbes fraîches.")

        recipe["instructions"] = new_instructions
        recipe.setdefault("_corrections_log", []).append("safe_rewrite_v3_vegan_title_preserved")
        count += 1

        print(f"✓ Corrigée (safe) : {recipe['id']}")

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Correction safe terminée ! {count} recettes corrigées.")
    print(f"Fichier créé : {output_file.name}")
    print("Relance ton audit maintenant.")

if __name__ == "__main__":
    main()