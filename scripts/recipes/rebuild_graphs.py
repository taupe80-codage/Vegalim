import sys
import os
import json
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.engine.config import DATA_ROOT
from backend.core.data_io import load_recipes, save_json
from backend.engine.search_token_generator import batch_generate
from backend.engine.nutrition_engine import compute_nutrition, score_nutrition_values
from backend.engine.score_engine.quality import _d_flavor

def rebuild_graphs_and_index():
    print("Loading recipes...")
    recipes = list(load_recipes())
    print(f"Loaded {len(recipes)} recipes.")

    print("Rebuilding search index...")
    stats = batch_generate(recipes, save=True)
    print(f"Search index rebuild stats: {stats}")

    print("Rebuilding scoring and nutrition graphs...")
    nutrition_graph = {}
    scoring_graph = {}
    
    # Needs to get data for flavor
    import backend.engine.score_engine.quality as quality
    d = quality._load_data()
    
    for r in recipes:
        rid = str(r.get("id"))
        
        # 1. Compute Nutrition
        nutr = compute_nutrition(r)
        nutrition_graph[rid] = nutr
        
        # 2. Compute Nutrition Score (approx /10)
        nutr_score_15 = score_nutrition_values(nutr)
        nutr_score_10 = round(min(max(nutr_score_15 / 1.5, 0), 10.0), 1)
        
        # 3. Compute Flavor Score
        flavor_score = quality._d_flavor(r, d)
        
        scoring_graph[rid] = {
            "nutrition_score": nutr_score_10,
            "flavor_score": flavor_score,
            "overall_score": round((nutr_score_10 + flavor_score) / 2.0, 1), # simple base
            "calories": nutr.get("calories", 0),
            "protein": nutr.get("protein", 0),
            "fiber": nutr.get("fiber", 0),
            "glycemic_index": nutr.get("glycemic_index", 0)
        }
        
    # Save the graphs
    save_json(DATA_ROOT / "graphs" / "recipe_nutrition_graph_v1.json", nutrition_graph)
    save_json(DATA_ROOT / "graphs" / "recipe_scoring_graph_v1.json", scoring_graph)
    print("Graphs successfully rebuilt and saved.")

if __name__ == '__main__':
    rebuild_graphs_and_index()
