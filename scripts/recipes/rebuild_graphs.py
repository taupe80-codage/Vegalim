"""
rebuild_graphs.py
=================
Reconstruit recipe_nutrition_graph_v1.json et recipe_scoring_graph_v1.json
a partir de recipes.json + nutrition_v2.json.

A relancer apres toute modification de recipes.json (diet_flags, allergens...)
ou apres un rebuild du pipeline nutrition.

Usage :
    python scripts/recipes/rebuild_graphs.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from backend.engine.config import DATA_ROOT
from backend.core.data_io import (
    load_recipes, save_json,
    load_nutrition_db, load_ingredients_dict, load_ingredient_physical,
)
from backend.engine.search_token_generator import batch_generate
from backend.engine.nutrition_engine import compute_nutrition, resolve_servings
from backend.engine.score_engine.ajr import meal_score
import backend.engine.score_engine.quality as quality


def recipe_nutrition(r: dict, registry: dict) -> dict:
    """
    Nutrition par portion. Les préparations dotées d'une `nutrition_reference`
    (fromages caillés maison…) reprennent la fiche de référence du registre
    des sous-recettes, rapportée au poids obtenu par portion — le calcul depuis
    les ingrédients y compterait le petit-lait égoutté.
    """
    entry = registry.get(str(r.get("id"))) if r.get("nutrition_reference") else None
    if not entry:
        return compute_nutrition(r)
    srv = resolve_servings(r)
    factor = entry["total_weight_g"] / srv / 100.0
    nutr = {k: (round(v * factor, 1) if isinstance(v, (int, float)) else v)
            for k, v in entry["nutrition_per_100g"].items()}
    nutr["calories"] = round(entry["nutrition_per_100g"]["calories"] * factor)
    nutr["sodium"] = round(entry["nutrition_per_100g"]["sodium"] * factor)
    nutr["salt"] = round(entry["nutrition_per_100g"].get("salt", 0) * factor, 2)
    if nutr.get("glycemic_index") is None:
        nutr.pop("glycemic_index", None)
    nutr["servings_used"] = srv
    nutr["source"] = "nutrition_reference"
    return nutr


def rebuild_graphs_and_index():
    print("Chargement des donnees...")
    recipes = list(load_recipes())
    print(f"  {len(recipes)} recettes")

    # Prechauffer les caches (evite les rechargements disque par recette)
    load_nutrition_db()
    load_ingredients_dict()
    load_ingredient_physical()

    print("Reconstruction search_index...")
    stats = batch_generate(recipes, save=True)
    print(f"  {stats}")

    print("Reconstruction nutrition + scoring graphs...")
    nutrition_graph = {}
    scoring_graph = {}
    d = quality._load_data()
    from backend.db.culinary_repositories import _derived_registry
    registry = _derived_registry()

    for i, r in enumerate(recipes):
        rid = str(r.get("id"))
        nutr = recipe_nutrition(r, registry)
        nutrition_graph[rid] = nutr

        # Score d'une PORTION (1/3 des AJR, pénalités calories/sodium/sucres/
        # graisses saturées) : l'ancien score AJR journalier récompensait les
        # plats les plus caloriques.
        nutr_score = round(meal_score(nutr)["score"], 1)

        try:
            flavor_score = float(quality._d_flavor(r, d))
        except Exception:
            flavor_score = 5.0

        scoring_graph[rid] = {
            "nutrition_score": nutr_score,
            "flavor_score": round(flavor_score, 1),
            "overall_score": round((nutr_score + flavor_score) / 2.0, 1),
            "calories": nutr.get("calories", 0),
            "protein": nutr.get("protein", 0),
            "fiber": nutr.get("fiber", 0),
            "glycemic_index": nutr.get("glycemic_index", 0),
        }

        if (i + 1) % 200 == 0:
            print(f"  {i + 1}/{len(recipes)}...")

    save_json(DATA_ROOT / "graphs" / "recipe_nutrition_graph_v1.json", nutrition_graph)
    save_json(DATA_ROOT / "graphs" / "recipe_scoring_graph_v1.json", scoring_graph)
    print(f"  OK - Graphs mis a jour ({len(nutrition_graph)} recettes).")


if __name__ == "__main__":
    rebuild_graphs_and_index()
