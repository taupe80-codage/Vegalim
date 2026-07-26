"""
planner.py — Génération du plan de repas hebdomadaire.
Fusionne : meal_planner + ingredient_reuse_optimizer

API :
    generate_plan(params) → dict  (plan 7 jours)
"""
from __future__ import annotations
import logging
import math
import random
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
    diet:            str | None   = None,
    max_calories:    float | None = None,
    min_protein:     float | None = None,
    month:           int | None   = None,
    exclude_ids:     list[int]    = None,
    batch_cooking:   bool         = False,
    limit_per_slot:  int          = 3,
    # Filtres étendus
    max_time:        int | None   = None,
    allergen_exclude: list[str]   = None,   # tags.allergens names ("eggs", "gluten"…)
    # Flags boolean allergens — même logique que filter_service.apply_filters
    gluten_free:     bool         = False,
    lactose_free:    bool         = False,
    nut_free:        bool         = False,
    egg_free:        bool         = False,
    dairy_free:      bool         = False,
    soy_free:        bool         = False,
    cuisine:         str | None   = None,
    dish_type:       str | None   = None,
    difficulty:      str | None   = None,
    # Diversité : 0.0 = toujours le meilleur score (déterministe),
    #             1.0 = tirage quasi-aléatoire parmi le top pool
    diversity:       float        = 0.5,
    pool_size:       int          = 12,   # nb de candidats dans lequel piocher
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

    # ── Filtres ───────────────────────────────────────────────────────────────
    if diet:
        recipes = get_data.recipes.filter_by_diet(recipes, diet)
    if exclude_ids:
        recipes = get_data.recipes.exclude_ids(recipes, exclude_ids)

    # Temps max par recette
    if max_time:
        recipes = [r for r in recipes
                   if ((r.get("timing") or {}).get("total_min") or 999) <= max_time]

    # Allergènes à exclure via tags.allergens (présence de l'allergène dans la recette)
    if allergen_exclude:
        excl = {a.lower() for a in allergen_exclude}
        def _has_allergen(r):
            tags = r.get("tags") or {}
            allergens_in_recipe = set(a.lower() for a in (tags.get("allergens") or []))
            return bool(allergens_in_recipe & excl)
        recipes = [r for r in recipes if not _has_allergen(r)]

    # Flags boolean allergens — utilise apply_filters (même logique que HomePage/recherche)
    # gluten_free / lactose_free / nut_free → diet_flags (fiables, présents sur toutes les recettes)
    # egg_free / dairy_free / soy_free       → vérification par ingrédient (allergen_flags)
    _any_bool_allergen = gluten_free or lactose_free or nut_free or egg_free or dairy_free or soy_free
    if _any_bool_allergen:
        try:
            from backend.services.filter_service import apply_filters
            recipes, _ = apply_filters(
                recipes,
                skip=0, limit=len(recipes),
                gluten_free=gluten_free,
                lactose_free=lactose_free,
                nut_free=nut_free,
                egg_free=egg_free,
                dairy_free=dairy_free,
                soy_free=soy_free,
            )
        except Exception as _e:
            logger.warning("apply_filters allergen error: %s", _e)

    # Cuisine
    if cuisine:
        cuis_low = cuisine.lower()
        recipes = [r for r in recipes
                   if cuis_low in ((r.get("origin") or {}).get("cuisine", "")).lower()]

    # Type de plat
    if dish_type:
        recipes = [r for r in recipes
                   if r.get("dish_type", "").lower() == dish_type.lower()]

    # Difficulté
    if difficulty:
        diff_map = {"easy": {"easy", "facile"}, "medium": {"medium", "intermédiaire", "moyen"},
                    "hard": {"hard", "difficile"}}
        allowed_diffs = diff_map.get(difficulty.lower(), {difficulty.lower()})
        recipes = [r for r in recipes
                   if (r.get("difficulty_level") or r.get("difficulty") or "").lower() in allowed_diffs]

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

            # Candidats non encore utilisés
            candidates = [r for r in recipes if r.get("id") not in used_ids]

            # Scorer tous les candidats
            def _score(r):
                s = float(r.get("scoring", {}).get("iconic", {}).get("score") or 50) / 100.0 * 5.0
                s += _season_bonus(r, month)
                s += _reuse_score(r, planned_ings)
                if meal == "lunch" and meal_type(r) in ("soup", "salad"):
                    s += 1.0
                return s

            # ── Sélection pondérée par score (softmax sur le top-pool) ────────
            # diversity 0 → déterministe (toujours le #1), 1 → très aléatoire
            # temperature = diversity * 5 + 0.05  (plage ~0.05 à 5.05)
            temperature = max(0.05, float(diversity) * 5.0)

            scored = sorted(
                ((r, _score(r)) for r in candidates),
                key=lambda x: -x[1],
            )
            pool = scored[:max(pool_size, 1)]

            if not pool:
                chosen = recipes[day_i % len(recipes)]
            elif len(pool) == 1 or diversity <= 0.0:
                chosen = pool[0][0]
            else:
                best_s = pool[0][1]
                weights = [
                    math.exp((s - best_s) / temperature)
                    for _, s in pool
                ]
                chosen = random.choices([r for r, _ in pool], weights=weights, k=1)[0]

            plan[day][meal] = {
                "id":       chosen.get("id"),
                "title_fr": chosen.get("titles", {}).get("fr", ""),
                "servings": chosen.get("servings", 4),
            }
            used_ids.add(chosen.get("id"))

            # Mettre à jour le compteur d'ingrédients (composition CDC v4 ou legacy)
            for ing in (chosen.get("composition") or chosen.get("ingredients", [])):
                key = (ing.get("ingredient") or ing.get("ingredient_id") or str(ing)
                       if isinstance(ing, dict) else str(ing)).lower()
                if key:
                    planned_ings[key] += 1

    plan["meta"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "diet":         diet,
        "month":        month,
        "n_recipes":    len(used_ids),
        "batch_cooking": batch_cooking,
    }
    return plan
