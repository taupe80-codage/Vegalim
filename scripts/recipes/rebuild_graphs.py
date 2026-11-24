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
    load_catalogue_recipes as load_recipes, save_json,  # recipes.json seul : il est réécrit (search_tokens)
    load_nutrition_db, load_ingredients_dict, load_ingredient_physical,
)
from backend.engine.search_token_generator import batch_generate
from backend.engine.recipe_graphs import graph_entries


def rebuild_graphs_and_index():
    print("Chargement des donnees...")
    recipes = list(load_recipes())
    print(f"  {len(recipes)} recettes")

    # Prechauffer les caches (evite les rechargements disque par recette)
    load_nutrition_db()
    load_ingredients_dict()
    load_ingredient_physical()

    print("Reconstruction nutrition + scoring graphs...")
    # Calcul partagé avec data_io, qui l'applique à la volée aux recettes
    # proposées publiées (absentes de ces fichiers).
    nutrition_graph, scoring_graph = graph_entries(recipes)

    save_json(DATA_ROOT / "graphs" / "recipe_nutrition_graph_v1.json", nutrition_graph)
    save_json(DATA_ROOT / "graphs" / "recipe_scoring_graph_v1.json", scoring_graph)
    print(f"  OK - Graphs mis a jour ({len(nutrition_graph)} recettes).")

    # Mots-clés APRÈS les graphes : ils lisent la nutrition par portion du
    # graphe (« léger », « riche en protéines »…). Générés avant, une recette
    # nouvelle ne les recevait qu'à la reconstruction suivante (2026-11-23).
    print("Reconstruction search_tokens...")
    stats = batch_generate(recipes, save=True)
    print(f"  {stats}")


if __name__ == "__main__":
    rebuild_graphs_and_index()
