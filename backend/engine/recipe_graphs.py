"""
recipe_graphs.py — Entrées des graphes nutrition et score d'une recette.

Une seule définition pour :
  - scripts/recipes/rebuild_graphs.py, qui écrit les graphes du catalogue
    (recipe_nutrition_graph_v1.json, recipe_scoring_graph_v1.json) ;
  - backend/core/data_io.py, qui calcule à la volée les entrées des recettes
    proposées par les utilisateurs et publiées (community_recipes.json),
    absentes de ces fichiers : sans elles, une recette publiée n'avait ni
    scores santé (filtres FODMAP, protéines, glycémie…), ni bonus d'objectif,
    et sa note nutritionnelle restait à la valeur neutre 5,0 (2026-11-24).

Ne lit pas les graphes eux-mêmes (data_io l'appelle en les chargeant).
"""
from __future__ import annotations


def recipe_nutrition(r: dict, registry: dict) -> dict:
    """
    Nutrition par portion, avec les glucides rapides (fast_carbs).

    Les préparations dotées d'une `nutrition_reference` (fromages caillés
    maison…) reprennent la fiche de référence du registre des sous-recettes,
    rapportée au poids obtenu par portion — le calcul depuis les ingrédients y
    compterait le petit-lait égoutté.
    """
    from backend.engine.diabetes import fast_carbs
    from backend.engine.nutrition_engine import compute_nutrition, resolve_servings

    entry = registry.get(str(r.get("id"))) if r.get("nutrition_reference") else None
    if not entry:
        nutr = compute_nutrition(r)
    else:
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
    # Glucides rapides par portion (ingrédients à surveiller pour le diabète) :
    # remplace l'indice glycémique, absent des données sources.
    nutr["fast_carbs"] = fast_carbs(r)
    return nutr


def recipe_scoring(r: dict, nutr: dict, flavor_graph: dict) -> dict:
    """Entrée du graphe de score depuis la nutrition par portion."""
    import backend.engine.score_engine.quality as quality
    from backend.engine.score_engine.ajr import meal_score

    # Score d'une PORTION (1/3 des AJR, pénalités calories/sodium/sucres/
    # graisses saturées) : l'ancien score AJR journalier récompensait les
    # plats les plus caloriques.
    nutr_score = round(meal_score(nutr)["score"], 1)
    try:
        flavor_score = float(quality._d_flavor(r, {"flavor": flavor_graph}))
    except Exception:
        flavor_score = 5.0
    return {
        "nutrition_score": nutr_score,
        "flavor_score": round(flavor_score, 1),
        "overall_score": round((nutr_score + flavor_score) / 2.0, 1),
        "calories": nutr.get("calories", 0),
        "protein": nutr.get("protein", 0),
        "fiber": nutr.get("fiber", 0),
        "glycemic_index": nutr.get("glycemic_index", 0),
    }


def graph_entries(recipes: list[dict]) -> tuple[dict, dict]:
    """({id: nutrition}, {id: score}) pour une liste de recettes."""
    from backend.core.data_io import load_flavor_graph
    from backend.db.culinary_repositories import _derived_registry

    registry = _derived_registry()
    flavor = load_flavor_graph()
    nutrition, scoring = {}, {}
    for r in recipes:
        rid = str(r.get("id"))
        nutr = recipe_nutrition(r, registry)
        nutrition[rid] = nutr
        scoring[rid] = recipe_scoring(r, nutr, flavor)
    return nutrition, scoring
