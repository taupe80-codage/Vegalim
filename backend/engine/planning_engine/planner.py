"""
planner.py — Génération du plan de repas hebdomadaire.
Fusionne : meal_planner + ingredient_reuse_optimizer

API :
    generate_plan(params) → dict  (plan 7 jours)
"""
from __future__ import annotations
import logging
from collections import Counter
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

_DAYS    = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
_MEALS   = ["lunch", "dinner"]


def _season_bonus(recipe: dict, month: int | None) -> float:
    if month is None: return 0.0
    try:
        from backend.engine.rule_engine.seasonality import season_bonus
        return season_bonus(recipe, month)
    except Exception:
        return 0.0


def _reuse_score(recipe: dict, planned_ings: Counter) -> float:
    """Bonus si la recette partage des ingrédients avec ceux déjà planifiés."""
    ings = {(i.get("ingredient_id", str(i)) if isinstance(i, dict) else str(i)).lower()
            for i in recipe.get("ingredients", [])}
    shared = sum(planned_ings[i] for i in ings if i in planned_ings)
    return min(2.0, shared * 0.3)


def generate_plan(
    diet:          str | None  = None,
    max_calories:  float | None = None,
    min_protein:   float | None = None,
    month:         int | None  = None,
    exclude_ids:   list[int]   = None,
    batch_cooking: bool        = False,
    limit_per_slot: int        = 3,
) -> dict:
    """
    Génère un plan de repas hebdomadaire (7 jours × 2 repas).

    Args:
        diet           : filtre régime ("vegan", "vegetarian"…)
        max_calories   : calories max par portion
        min_protein    : protéines min par portion
        month          : mois 1-12 pour bonus saisonnalité
        exclude_ids    : ids à exclure (déjà vus, allergies)
        batch_cooking  : si True, repas du soir = déjeuner du lendemain
        limit_per_slot : candidats évalués par créneau

    Returns:
        Plan semaine {lundi: {lunch: recipe, dinner: recipe}, ..., meta: {}}
    """
    from backend.db.data_access import get_data
    from backend.engine.planning_engine.structure import meal_type
    from backend.engine.planning_engine.budget    import estimate_price

    recipes = get_data.recipes.list_all()

    # Filtres
    if diet:
        recipes = get_data.recipes.filter_by_diet(recipes, diet)
    if exclude_ids:
        recipes = get_data.recipes.exclude_ids(recipes, exclude_ids)

    # Filtres nutritionnels
    if max_calories or min_protein:
        filtered = []
        for r in recipes:
            nutr = get_data.recipes.get_nutrition(r.get("id")) or {}
            cal  = float(nutr.get("calories", 999) or 999)
            prot = float(nutr.get("protein",  0)   or 0)
            if max_calories and cal > max_calories: continue
            if min_protein  and prot < min_protein: continue
            filtered.append(r)
        recipes = filtered

    if not recipes:
        logger.warning("generate_plan: aucune recette disponible après filtres")
        return {"meta": {"error": "no_recipes", "filters": {"diet": diet}}}

    plan          = {}
    used_ids      = set()
    planned_ings  = Counter()

    for day_i, day in enumerate(_DAYS):
        plan[day] = {}

        for meal in _MEALS:
            # Si batch cooking : dîner du lundi = déjeuner du mardi
            if batch_cooking and meal == "dinner" and day_i < 6:
                lunch_recipe = plan[day].get("lunch")
                if lunch_recipe:
                    plan[day][meal] = lunch_recipe
                    continue

            # Candidats non encore utilisés, triés par score composite
            candidates = [r for r in recipes if r.get("id") not in used_ids]

            # Scorer les candidats
            def _score(r):
                s = float(r.get("scoring", {}).get("iconic", {}).get("score") or 50) / 100.0 * 5.0  # base
                s += _season_bonus(r, month)
                s += _reuse_score(r, planned_ings)
                # Diversifier les types de repas
                if meal == "lunch" and meal_type(r) in ("soup", "salad"):
                    s += 1.0
                return s

            candidates.sort(key=_score, reverse=True)
            chosen = candidates[0] if candidates else (recipes[day_i % len(recipes)])

            plan[day][meal] = {
                "id":       chosen.get("id"),
                "title_fr": chosen.get("titles", {}).get("fr", ""),
                "servings": chosen.get("servings", 4),
            }
            used_ids.add(chosen.get("id"))

            # Mettre à jour le compteur d'ingrédients
            for ing in chosen.get("ingredients", []):
                planned_ings[str(ing).lower()] += 1

    plan["meta"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "diet":         diet,
        "month":        month,
        "n_recipes":    len(used_ids),
        "batch_cooking": batch_cooking,
    }
    return plan
