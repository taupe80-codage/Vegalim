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
        logger.warning("_season_bonus : erreur ignorée (repli)", exc_info=True)
        return 0.0


# ── Anti-gaspillage ──────────────────────────────────────────────────────────
# Revu le 2026-11-24 : _reuse_score lisait recipe["ingredients"], champ absent
# des recettes (elles ont « composition ») — le bonus valait toujours 0 et la
# réutilisation des ingrédients n'avait jamais agi. Il porte désormais sur ce
# qui se gâche : les ingrédients achetés pour la recette (crème, lait de coco,
# feta, chou, tofu…), puis les produits courants et les herbes fraîches (une
# botte entamée). Sel, huile, épices sèches : sans objet.
REUSE_WEIGHT = {"special": 1.0, "common": 0.5, "fresh_herb": 0.6}
REUSE_PER_SHARE = 0.8      # points par ingrédient déjà entamé dans la semaine
REUSE_CAP = 3.0            # plafond : la saison et la qualité restent décisives
# Mesuré sur 20 semaines (plats, novembre) : 12,5 → 18,6 produits frais réutilisés,
# 38,1 → 34,9 produits frais différents à acheter, part de saison 0,96 → 0,93.
# Produits secs ou de longue conservation : un reste ne se perd pas
_KEEPS = ("_dried", "dried_", "_dry", "spice", "powder", "flour", "sugar", "_seed", "pasta",
          "rice", "noodle", "vermicelli", "couscous", "bulgur", "quinoa", "oat", "vinegar",
          "soy_sauce", "syrup", "honey", "nuts", "almond", "cashew", "peanut", "walnut",
          "hazelnut", "pistachio", "oil", "salt", "stock", "canned_in", "jam", "chocolate", "cocoa")


def _reuse_kind(item: dict) -> str | None:
    """Catégorie anti-gaspillage d'une ligne de composition (None : sans objet)."""
    from backend.services.fridge_scoring import tier_of_id, SPECIAL, COMMON
    iid = str(item.get("ingredient") or "").lower()
    if not iid or iid.startswith("base_") or (item.get("meta") or {}).get("role") == "serving_suggestion":
        return None
    if "fresh_herb" in iid or ("fresh" in iid and iid.endswith(("_herb", "_leaf"))):
        return "fresh_herb"
    if any(k in iid for k in _KEEPS):
        return None
    # Nature de l'ingrédient seule (pas le rôle) : un lait de coco employé comme
    # matière grasse laisse quand même une demi-boîte entamée.
    tier = tier_of_id(iid)
    return "special" if tier == SPECIAL else "common" if tier == COMMON else None


def _perishables(recipe: dict) -> dict[str, str]:
    """{ingrédient: catégorie} des ingrédients d'une recette qui se gâchent."""
    out = {}
    for item in recipe.get("composition") or []:
        if isinstance(item, dict):
            kind = _reuse_kind(item)
            if kind:
                out[str(item["ingredient"]).lower()] = kind
    return out


def _reuse_score(recipe: dict, planned_ings: Counter, perishables: dict | None = None) -> float:
    """Bonus si la recette réutilise des ingrédients déjà entamés dans la semaine."""
    items = perishables if perishables is not None else _perishables(recipe)
    shared = sum(REUSE_WEIGHT[kind] for iid, kind in items.items() if planned_ings.get(iid))
    return min(REUSE_CAP, shared * REUSE_PER_SHARE)


def _practical_score(recipe: dict, day_i: int, protein: float | None) -> float:
    """Préférences d'un planning réaliste (bonus/malus, jamais d'exclusion) :
    - en semaine (lundi-vendredi), malus pour un plat long à préparer et, plus
      fort, pour un trempage ou une marinade de la veille (temps passif ≥ 4 h :
      ghormeh sabzi 845 min ou locro 560 min tombaient un jeudi midi) ;
    - plat principal : bonus à 15 g de protéines par portion ou plus, malus sous
      10 g (stamppot, sarson ka saag, locro à 8-9 g étaient servis comme repas)."""
    t = recipe.get("timing") or {}
    active = (t.get("prep_active_min") or 0) + (t.get("cook_min") or 0)
    passive = t.get("prep_passive_min") or 0
    s = 0.0
    if day_i < 5:
        if passive >= 240:
            s -= 1.5
        elif active > 90:
            s -= 0.75
    if protein is not None and str(recipe.get("dish_type") or "").lower() == "main":
        if protein >= 15:
            s += 0.5
        elif protein < 10:
            s -= 0.75
    return s


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
    # Autres filtres de filter_service.apply_filters (santé, cuisines, saison…),
    # transmis tels quels : mêmes clés et même logique que la recherche
    filters:         dict | None  = None,
    # Diversité : 0.0 = toujours le meilleur score (déterministe),
    #             1.0 = tirage quasi-aléatoire parmi le top pool
    diversity:       float        = 0.5,
    pool_size:       int          = 12,   # nb de candidats dans lequel piocher
    # Anti-gaspillage : favorise les recettes qui finissent les ingrédients
    # entamés plus tôt dans la semaine (case du planning, cochée par défaut)
    anti_waste:      bool         = True,
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

    from backend.core.data_io import is_component_recipe
    # Les sous-recettes (base_… : pâtes, sauces, crème fraîche) ne sont pas
    # des repas : elles sortaient même avec dish_type=main.
    recipes = [r for r in get_data.recipes.list_all() if not is_component_recipe(r)]

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

    if filters:
        from backend.services.filter_service import apply_filters
        recipes, _ = apply_filters(recipes, skip=0, limit=len(recipes), **filters)

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
        return {"meta": {"error": "no_recipes", "filters": {"diet": diet, **(filters or {})}}}

    plan          = {}
    used_ids      = set()
    planned_ings  = Counter()
    perish_of     = {r.get("id"): _perishables(r) for r in recipes} if anti_waste else {}
    from backend.core.data_io import load_nutrition_graph
    _ng = load_nutrition_graph() or {}
    _ng = _ng.get("recipes", _ng) if isinstance(_ng, dict) else {}
    protein_of = {r.get("id"): float((_ng.get(r.get("id")) or {}).get("protein") or 0) or None
                  for r in recipes}

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
                if anti_waste:
                    s += _reuse_score(r, planned_ings, perish_of.get(r.get("id")))
                if meal == "lunch" and meal_type(r) in ("soup", "salad"):
                    s += 1.0
                s += _practical_score(r, day_i, protein_of.get(r.get("id")))
                return s

            # ── Sélection pondérée par score (softmax sur le top-pool) ────────
            # diversity 0 → déterministe (toujours le #1), 1 → très aléatoire
            # temperature = diversity (plage 0.05 à 1)
            # (température ≤ 1 : le vivier élargi garde la préférence pour les plats de
            # saison et protéinés — 30 semaines à 0,5 : 49 plats distincts, 85 % de saison)
            temperature = max(0.05, float(diversity) * 1.0)

            scored = sorted(
                ((r, _score(r)) for r in candidates),
                key=lambda x: -x[1],
            )
            # Le vivier grandit avec la variété demandée : à 12 candidats fixes, 30
            # semaines générées ne puisaient que dans ~25 plats (régénérer redonnait
            # les mêmes). 0 → 12, 0,5 → 52, 1 → 92 candidats.
            pool = scored[:max(pool_size + int(80 * float(diversity)), 1)]

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
                # trempage, marinade ou repos de 4 h et plus : à lancer la veille
                "prep_ahead": ((chosen.get("timing") or {}).get("prep_passive_min") or 0) >= 240,
            }
            used_ids.add(chosen.get("id"))

            # Ingrédients entamés cette semaine (ceux qui se gâchent seulement)
            for key in perish_of.get(chosen.get("id")) or _perishables(chosen):
                planned_ings[key] += 1

    plan["meta"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "diet":         diet,
        "month":        month,
        "n_recipes":    len(used_ids),
        "batch_cooking": batch_cooking,
    }
    return plan
