"""
test_nutrition_engine_manual.py — Test manuel du nutrition_engine.

Vérifie que compute_nutrition fonctionne avec une recette simple.
Lance avec : python tests/test_nutrition_engine_manual.py
"""
from backend.engine.nutrition_engine import compute_nutrition

recipe = {
    "ingredients": ["tomato"],
    "composition": [
        {"ingredient": "tomato", "quantity": 2, "unit": "piece"}
    ],
    "servings": 2,
}

result = compute_nutrition(recipe)
print("Résultat compute_nutrition :")
for k, v in result.items():
    print(f"  {k}: {v}")
