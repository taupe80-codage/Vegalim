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
from backend.engine.nutrition_engine import compute_nutrition
from backend.engine.score_engine.ajr import ajr_score_with_profile as score_nutrition_values
import backend.engine.score_engine.quality as quality


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

    for i, r in enumerate(recipes):
        rid = str(r.get("id"))
        nutr = compute_nutrition(r)
        nutrition_graph[rid] = nutr

        ns_raw = score_nutrition_values(nutr)
        ns_val = ns_raw.get("score", 0) if isinstance(ns_raw, dict) else float(ns_raw)
        nutr_score = round(min(max(ns_val / 1.5, 0), 10.0), 1)

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
