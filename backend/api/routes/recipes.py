"""
routes/recipes.py — Recettes : recherche, fiche, top, variante vegan, graphes.

Routes publiques (sans auth) :
  GET  /recettes              — liste paginée avec filtres
  GET  /recettes/top          — classement global
  GET  /recettes/{id}         — fiche recette complète
  POST /recettes/recherche    — recherche textuelle + filtres

Routes authentifiées (plan free+) :
  POST /recettes/{id}/variante  — variante vegan à la demande
  POST /recommend               — pipeline recommandation personnalisé

Routes graphe (authentifiées) :
  GET  /recettes/graph/ingredient/{name}
  GET  /recettes/graph/cycle/{phase}
  POST /recettes/graph/analyze

MIGRATION étape 3 — imports obsolètes remplacés :
  servings_engine.validate_servings       → planning_engine.servings.validate_servings
  score_reliability_engine.compute        → score_engine.reliability.reliability
  seasonality_engine.ingredients_in_season→ rule_engine.seasonality.seasonal_ingredients
  score_explainer.explain                 → score_engine.explainer.explain
  sustainability_engine.recipe_carbon_score → rule_engine.carbon.carbon_score
  ingredient_price_engine.recipe_price    → planning_engine.budget.estimate_price
  recommendation_engine.recommend         → reco_service.recommend (déjà importé)
  vegan_variant_engine.get_vegan_variant  → rule_engine.variants.vegan_variant
  learning_engine.*                       → learning_engine.* (conservé — pas encore migré)
  similarity_engine.find_similar_by_id   → search_engine.similar.find_similar_by_id
  graph_engine.*                          → graph_engine.* (conservé — pas encore migré)
  culinary_rule_engine.validate/score     → rule_engine.validation.validate_recipe
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional

from backend.core.auth_deps        import get_user, get_optional_user
from backend.core.rate_limiter     import check_rate_limit
from backend.services.reco_service import recommend
from backend.core.data_io          import (
    load_recipes, load_nutrition_graph, load_score_graph,
    load_ingredients_dict, load_availability_graph,
)

router = APIRouter(prefix="/recettes", tags=["Recettes"])


# ── AJR (Apports Journaliers Recommandés) pour adulte ─────────────────────────
_AJR = {
    "protein":    50,    # g
    "fiber":      25,    # g
    "iron":       14,    # mg
    "calcium":    800,   # mg
    "magnesium":  375,   # mg
    "potassium":  2000,  # mg
    "vitamin_c":  80,    # mg
    "zinc":       10,    # mg
}

_AJR_LABELS = {
    "protein": "Protéines", "fiber": "Fibres", "iron": "Fer",
    "calcium": "Calcium", "magnesium": "Magnésium", "potassium": "Potassium",
    "vitamin_c": "Vitamine C", "zinc": "Zinc",
}

# Nutriments prioritaires par phase du cycle féminin
_CYCLE_PRIORITY = {
    "menstrual":  ["iron", "magnesium", "vitamin_c"],
    "follicular": ["protein", "fiber", "magnesium"],
    "ovulatory":  ["vitamin_c", "zinc", "fiber"],
    "luteal":     ["magnesium", "fiber", "potassium"],
}


def _enrich_why(recipes: list, filters: dict = None) -> list:
    """
    Enrichit chaque recette avec :
      - `_why`        : explication contextuelle aux filtres actifs
      - `_nutrition`  : dict de valeurs brutes + %AJR
    """
    filters = filters or {}
    ng = load_nutrition_graph()
    cycle_phase = filters.get("cycle_phase")
    priority_keys = _CYCLE_PRIORITY.get(cycle_phase, [])

    for r in recipes:
        rid = str(r.get("id", ""))
        nutr = ng.get(rid, {})
        if not nutr:
            r["_why"] = None
            r["_nutrition"] = {}
            continue

        nutri_summary = {}
        all_highlights = {}
        for key, ajr in _AJR.items():
            val = nutr.get(key, 0) or 0
            pct = round((val / ajr) * 100) if val > 0 and ajr > 0 else 0
            nutri_summary[key] = {"value": round(val, 1), "pct_ajr": pct}
            if pct >= 10:
                all_highlights[key] = (pct, _AJR_LABELS[key])

        kcal = nutr.get("calories")
        nutri_summary["calories"] = {"value": kcal or 0, "pct_ajr": 0}
        r["_nutrition"] = nutri_summary

        why_parts = []
        if filters.get("high_protein") and "protein" in all_highlights:
            why_parts.append(f"💪 {nutri_summary['protein']['value']}g")
        if filters.get("low_calorie") and kcal:
            why_parts.append(f"📉 {kcal} kcal")
        if filters.get("high_fiber") and "fiber" in all_highlights:
            why_parts.append(f"🌾✨ {nutri_summary['fiber']['value']}g")
        if filters.get("diet") == "vegan":
            why_parts.append("🌿 Végétal")
        if filters.get("low_ig") and (r.get("health_scores", {}).get("diabetes_friendly") or r.get("health_scores", {}).get("low_ig")):
            why_parts.append("🩸 IG Bas")
        
        if not why_parts:
            ordered = []
            for pk in priority_keys:
                if pk in all_highlights:
                    ordered.append(all_highlights.pop(pk))
            remaining = sorted(all_highlights.values(), reverse=True)
            ordered.extend(remaining)
            top = ordered[:2]

            if top:
                why_parts = [f"{label} {pct}% AJR" for pct, label in top]
                if kcal:
                    why_parts.append(f"{kcal} kcal")
            else:
                if kcal:
                    why_parts.append(f"{kcal} kcal")

        r["_why"] = " · ".join(why_parts) if why_parts else None

    return recipes

# ── Modèles Pydantic ──────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query:       str           = Field(default="", max_length=200)
    filtre:      Optional[str] = Field(default=None, description="vegan | vegetarien | …")
    cuisine:     Optional[str] = Field(default=None)
    technique:   Optional[str] = Field(default=None)
    max_time:    Optional[int] = Field(default=None, ge=1, le=480)
    gluten_free: bool          = Field(default=False)
    # Fix : limit accepté dans le body (le frontend envoie {limit: 40} dans POST)
    limit:       int           = Field(default=20, ge=1, le=100)
    # ── Filtres de santé et holistiques ───────────────────────────────────────
    high_protein: bool         = Field(default=False)
    low_calorie: bool          = Field(default=False)
    high_fiber: bool           = Field(default=False)
    low_ig: bool               = Field(default=False)
    max_kcal:    Optional[int] = Field(default=None)
    astro_element: Optional[str] = Field(default=None)
    moon_phase:  Optional[str] = Field(default=None)
    cycle_phase: Optional[str] = Field(default=None)


class UnifiedScoreRequest(BaseModel):
    recipe:       dict         = Field(..., description="Recette à scorer")
    profile:      str          = Field(default="default")
    profile_data: dict         = Field(default_factory=dict)


class GraphAnalyzeRequest(BaseModel):
    recipe:  dict              = Field(..., description="Recette à analyser")
    profile: dict              = Field(default_factory=dict)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compute_enrichment(recipe: dict) -> dict:
    """
    Calcule les données dérivées d'une recette (nutrition, scores, disponibilité…).
    Ne modifie JAMAIS la recette originale.
    Retourne uniquement les champs calculés, prêts à être fusionnés par-dessus la recette.
    """
    rid       = str(recipe.get("id", ""))
    ng        = load_nutrition_graph()
    sg        = load_score_graph()
    av        = load_availability_graph()
    ings_dict = load_ingredients_dict()
    out: dict = {}

    # ── Nutrition par portion ─────────────────────────────────────────────────
    from backend.engine.planning_engine.servings import validate_servings   # ✅ migré
    servings = validate_servings(recipe.get("servings", 4))
    ng_total = ng.get(rid, {})
    out["nutrition"] = {
        k: round(v / servings, 2) if isinstance(v, (int, float)) else v
        for k, v in ng_total.items()
    }
    out["nutrition"]["_per_serving"] = servings
    out["score_data"] = sg.get(rid, {})

    # ── Fiabilité nutritionnelle ──────────────────────────────────────────────
    from backend.engine.score_engine.reliability import reliability          # ✅ migré
    _rel = reliability(recipe)
    out["score_reliability"] = _rel.get("status")
    out["score_coverage"]    = _rel.get("coverage")

    # ── Saisonnalité dynamique ────────────────────────────────────────────────
    from backend.engine.rule_engine.seasonality import seasonal_ingredients  # ✅ migré
    import datetime
    current_month = datetime.date.today().month
    recipe_ings   = {
        (i.get("ingredient_id", "") if isinstance(i, dict) else str(i)).lower()
        for i in recipe.get("ingredients", [])
    }
    in_season     = set(seasonal_ingredients(current_month))
    strict        = recipe_ings - {"salt", "pepper", "oil", "olive_oil", "water", "bouillon"}
    if strict:
        ratio = len(strict & in_season) / len(strict)
        out["seasonal_tag"]   = ("de_saison" if ratio >= 0.7
                                 else "presque_saison" if ratio >= 0.4
                                 else "hors_saison")
        out["seasonal_ratio"] = round(ratio, 2)
    else:
        out["seasonal_tag"]   = "année_entière"
        out["seasonal_ratio"] = 1.0

    # ── Scoring CDC_03c ───────────────────────────────────────────────────────
    from backend.engine.score_engine.explainer import explain                # ✅ migré
    from backend.services.scoring_service import score_recipe as _sr
    _scored = _sr(recipe)
    out["final_score"]     = round(_scored.get("final_score",    _scored.get("adaptive_score", 0)), 2)
    out["quality_score"]   = round(_scored.get("global_score",   0), 2)
    out["relevance_score"] = round(_scored.get("adaptive_score", 0), 2)
    out["nutrition_score"] = round(sg.get(rid, {}).get("nutrition_score", 0), 2)
    out["score_reasons"]   = explain(_scored)

    # ── Disponibilité des ingrédients ─────────────────────────────────────────
    ing_avail = {}
    for ing in recipe.get("ingredients", []):
        iid = ing.get("ingredient_id", "") if isinstance(ing, dict) else str(ing)
        ing_avail[iid] = av.get(iid, {}).get("available_in_france", True)
    out["ingredients_availability"] = ing_avail

    # ── Enrichissement noms/substitutions ────────────────────────────────────
    ings_meta = {}
    for ing in recipe.get("ingredients", []):
        iid = ing.get("ingredient_id", "") if isinstance(ing, dict) else str(ing)
        if iid and iid not in ings_meta:
            d = ings_dict.get(iid, {})
            ings_meta[iid] = {
                "name_fr":        d.get("name_fr", iid),
                "substitutions":  d.get("substitutions", []),
                "flavor_profile": d.get("flavor_profile", []),
            }
    out["ingredients_meta"] = ings_meta

    # ── Validation culinaire ──────────────────────────────────────────────────
    from backend.engine.rule_engine.validation import validate_recipe        # ✅ migré
    _result            = validate_recipe(recipe)
    out["culinary_score"]      = _result.get("score", 10)
    out["culinary_violations"] = [
        v for v in _result.get("violations", [])
        if v.get("severity") in ("critical", "warning")
    ]

    # ── Durabilité (CO₂) et prix ──────────────────────────────────────────────
    from backend.engine.rule_engine.carbon import carbon_score               # ✅ migré
    from backend.engine.planning_engine.budget import estimate_price         # ✅ migré
    out["carbon_data"] = carbon_score(recipe)
    out["price_data"]  = estimate_price(recipe)

    return out


def _apply_filters(recipes: list, diet: str | None, cuisine: str | None,
                   technique: str | None, max_time: int | None,
                   gluten_free: bool, skip: int, limit: int,
                   # ── Nouveaux filtres ──────────────────────────────────────
                   lactose_free: bool = False,
                   nut_free: bool = False,
                   fodmap: str | None = None,          # "low" | "medium" | "high"
                   high_protein: bool = False,
                   low_calorie: bool = False,
                   high_fiber: bool = False,
                   low_ig: bool = False,
                   max_kcal: int | None = None,
                   astro_element: str | None = None,
                   moon_phase: str | None = None,
                   cycle_phase: str | None = None,
                   ) -> tuple[list, int]:
    """Filtre et pagine une liste de recettes."""
    result = recipes

    # ── Régime alimentaire ────────────────────────────────────────────────────
    if diet:
        from backend.services.filter_service import apply_diet_filter
        result = apply_diet_filter(result, diet)
    if gluten_free:
        result = [r for r in result if r.get("diet_flags", {}).get("gluten_free")]
    if lactose_free:
        result = [r for r in result if r.get("diet_flags", {}).get("lactose_free")]
    if nut_free:
        result = [r for r in result if r.get("diet_flags", {}).get("nut_free")]

    # ── Health scores ─────────────────────────────────────────────────────────
    if fodmap:
        result = [r for r in result
                  if r.get("health_scores", {}).get("fodmap_level") == fodmap]
    if high_protein:
        result = [r for r in result if r.get("health_scores", {}).get("high_protein")]
    if low_calorie:
        result = [r for r in result if r.get("health_scores", {}).get("low_calorie")]
    if high_fiber:
        result = [r for r in result if r.get("health_scores", {}).get("high_fiber")]
    if low_ig:
        result = [r for r in result if r.get("health_scores", {}).get("diabetes_friendly") or r.get("health_scores", {}).get("low_ig")]
    if max_kcal is not None:
        result = [r for r in result
                  if (r.get("health_scores", {}).get("kcal") or 9999) <= max_kcal]

    # ── Filtres Holistiques (Astrologie & Lune) ───────────────────────────────
    if astro_element or moon_phase:
        import json
        from backend.engine.config import DATA_ROOT
        try:
            with open(DATA_ROOT / "modules" / "astro_nutrition.json", encoding="utf-8") as f:
                astro_data = json.load(f).get("ingredients_astro_map", {})
        except Exception:
            astro_data = {}
            
        def recipe_matches_astro(r):
            ings = r.get("composition", [])
            if not ings: return False
            matching_ings = 0
            for ing in ings:
                ing_id = (ing.get("ingredient", "") if isinstance(ing, dict) else str(ing)).lower()
                meta = astro_data.get(ing_id, {})
                if astro_element and meta.get("element", "").lower() == astro_element.lower():
                    matching_ings += 1
                elif moon_phase and moon_phase.lower() in [p.lower() for p in meta.get("moon_phases", [])]:
                    matching_ings += 1
            
            # Relaxed constraint for culinary astrology: min 1 ingredient
            return matching_ings >= 1

        result = [r for r in result if recipe_matches_astro(r)]

    # ── Filtre Cycle Féminin ──────────────────────────────────────────────────
    if cycle_phase:
        from backend.engine.graph_engine import get_cycle_ingredients
        good_ings = get_cycle_ingredients(cycle_phase)
        good_ings_lower = {i.lower() for i in good_ings}

        def recipe_matches_cycle(r):
            ings = r.get("composition", [])
            if not ings: return False
            matching = 0
            for ing in ings:
                ing_id = (ing.get("ingredient", "") if isinstance(ing, dict) else str(ing)).lower()
                if ing_id in good_ings_lower:
                    matching += 1
            # Require at least 1 beneficial ingredient 
            return matching >= 1

        result = [r for r in result if recipe_matches_cycle(r)]

    # ── Autres filtres ────────────────────────────────────────────────────────
    if cuisine:
        cuisine_l = cuisine.lower()
        result = [r for r in result
                  if cuisine_l in (r.get("iconic_status", {}).get("cuisine_origin", "") or "").lower()]
    if technique:
        result = [r for r in result
                  if technique.lower() in [t.lower() for t in (r.get("technique") or [])]]
    if max_time is not None:
        result = [r for r in result if (r.get("timing", {}).get("total_min") or 999) <= max_time]

    total = len(result)
    return result[skip: skip + limit], total


# ── Routes publiques ──────────────────────────────────────────────────────────

@router.get("")
@router.get("/")
def list_recettes(
    request: Request,
    skip:         int           = Query(default=0,   ge=0),
    limit:        int           = Query(default=20,  ge=1, le=600),
    diet:         Optional[str] = Query(default=None, description="vegan | vegetarien"),
    cuisine:      Optional[str] = Query(default=None),
    technique:    Optional[str] = Query(default=None),
    max_time:     Optional[int] = Query(default=None, ge=1),
    # ── Flags diététiques ─────────────────────────────────────────────────────
    gluten_free:  bool          = Query(default=False),
    lactose_free: bool          = Query(default=False),
    nut_free:     bool          = Query(default=False),
    # ── Health scores ─────────────────────────────────────────────────────────
    fodmap:       Optional[str] = Query(default=None, description="low | medium | high"),
    high_protein: bool          = Query(default=False, description=">20g protéines/portion"),
    low_calorie:  bool          = Query(default=False, description="<300 kcal/portion"),
    high_fiber:   bool          = Query(default=False, description=">8g fibres/portion"),
    low_ig:       bool          = Query(default=False, description="IG bas"),
    max_kcal:     Optional[int] = Query(default=None, ge=1, description="kcal max par portion"),
    astro_element: Optional[str] = Query(default=None, description="Air | Terre | Eau | Feu"),
    moon_phase:   Optional[str] = Query(default=None, description="nouvelle_lune | etc."),
    cycle_phase:  Optional[str] = Query(default=None, description="menstrual | follicular | ovulatory | luteal"),
    sort:         str           = Query(default="iconic_score"),
):
    """Liste paginée des recettes avec filtres combinables. **Public.**"""
    check_rate_limit(request, limit=120, window_seconds=60)
    recipes = list(load_recipes())
    if sort == "title_fr":
        recipes.sort(key=lambda r: r.get("titles", {}).get("fr", ""))
    else:
        recipes.sort(key=lambda r: r.get("scoring", {}).get("iconic", {}).get("score", 0), reverse=True)

    filtered, total = _apply_filters(
        recipes, diet, cuisine, technique, max_time,
        gluten_free, skip, limit,
        lactose_free=lactose_free,
        nut_free=nut_free,
        fodmap=fodmap,
        high_protein=high_protein,
        low_calorie=low_calorie,
        high_fiber=high_fiber,
        low_ig=low_ig,
        max_kcal=max_kcal,
        astro_element=astro_element,
        moon_phase=moon_phase,
        cycle_phase=cycle_phase,
    )
    return {
        "total":   total,
        "skip":    skip,
        "limit":   limit,
        "filters": {
            "diet": diet, "cuisine": cuisine, "technique": technique,
            "max_time": max_time,
            "gluten_free": gluten_free, "lactose_free": lactose_free, "nut_free": nut_free,
            "fodmap": fodmap, "high_protein": high_protein,
            "low_calorie": low_calorie, "high_fiber": high_fiber, "low_ig": low_ig, "max_kcal": max_kcal,
        },
        "results": _enrich_why(filtered, filters={"diet": diet, "high_protein": high_protein, "low_calorie": low_calorie, "high_fiber": high_fiber, "low_ig": low_ig, "cycle_phase": cycle_phase}),
    }


@router.get("/top")
def top_recettes(
    request: Request,
    skip:  int           = Query(default=0,  ge=0),
    limit: int           = Query(default=20, ge=1, le=100),
    diet:  Optional[str] = Query(default=None),
):
    """Top recettes par score global. **Public.**"""
    check_rate_limit(request, limit=60, window_seconds=60)
    results = recommend("", email=None, limit=limit * 2)
    if diet:
        from backend.services.filter_service import apply_diet_filter
        results = apply_diet_filter(results, diet)
    return {"total": len(results), "skip": skip, "limit": limit,
            "results": results[skip: skip + limit]}


@router.get("/decouverte")
def decouverte(request: Request, user: dict | None = Depends(get_optional_user)):
    """
    Mode Découverte — 3 recettes selon des logiques différentes :
    recette du jour (saisonnière), cuisine à explorer, surprise nutritionnelle.
    **Public — personnalisé si connecté.**
    """
    check_rate_limit(request, limit=30, window_seconds=60)
    import datetime, hashlib

    from backend.engine.rule_engine.seasonality import seasonal_ingredients   # ✅ migré (fix P0)

    recipes   = load_recipes()
    sg        = load_score_graph()
    ng        = load_nutrition_graph()
    email     = (user or {}).get("email")
    today     = datetime.date.today()
    month     = today.month
    in_season = set(seasonal_ingredients(month))

    # ── 1. Recette du jour ────────────────────────────────────────────────────
    def season_score(r):
        ings = {(i.get("ingredient_id", "") if isinstance(i, dict) else str(i)).lower()
                for i in r.get("ingredients", [])}
        ratio = len(ings & in_season) / max(len(ings - {"salt", "pepper", "oil"}), 1)
        base  = sg.get(str(r["id"]), {}).get("overall_score", 5.0)
        return ratio * 4 + base * 0.6

    seed_idx       = int(hashlib.md5(str(today).encode()).hexdigest(), 16) % len(recipes)
    top_seasonal   = sorted(recipes, key=season_score, reverse=True)
    recette_du_jour = top_seasonal[seed_idx % max(len(top_seasonal), 1)]

    # ── 2. Cuisine à explorer ─────────────────────────────────────────────────
    seen_cuisines = set()
    if email:
        try:
            from backend.engine.learning_engine import load_history          # conservé
            history    = load_history(email)
            viewed_ids = history.get("viewed", set())
            for r in recipes:
                if r["id"] in viewed_ids:
                    c = (r.get("iconic_status") or {}).get("cuisine_origin", "")
                    if c:
                        seen_cuisines.add(c)
        except Exception:
            pass

    cuisine_candidates = [
        r for r in recipes
        if (r.get("iconic_status") or {}).get("cuisine_origin", "") not in seen_cuisines
        and r["id"] != recette_du_jour["id"]
    ] or [r for r in recipes if r["id"] != recette_du_jour["id"]]

    cuisine_a_explorer = max(cuisine_candidates,
                             key=lambda r: sg.get(str(r["id"]), {}).get("overall_score", 0))

    # ── 3. Surprise nutritionnelle ────────────────────────────────────────────
    MICRO_FOCUS  = [("iron", "riche_en_fer"), ("calcium", "riche_en_calcium"),
                   ("vitamin_c", "riche_en_vitamine_c"), ("fiber", "riche_en_fibres")]
    used_ids     = {recette_du_jour["id"], cuisine_a_explorer["id"]}
    best_surprise, best_score, best_label = None, 0, ""
    for key, label in MICRO_FOCUS:
        for r in recipes:
            if r["id"] in used_ids:
                continue
            val = ng.get(str(r["id"]), {}).get(key, 0) or 0
            if val > best_score:
                best_score, best_surprise, best_label = val, r, label
        if best_surprise:
            break
    if not best_surprise:
        best_surprise = next((r for r in recipes if r["id"] not in used_ids), recipes[0])
        best_label = "populaire"

    return {
        "date":  str(today),
        "month": month,
        "recette_du_jour": {
            "id": recette_du_jour.get("id"),
            "title_fr": recette_du_jour.get("titles", {}).get("fr"),
            "iconic_score": recette_du_jour.get("scoring", {}).get("iconic", {}).get("score"),
            "diet_flags": recette_du_jour.get("tags", {}).get("diet", []),
            "raison": "de_saison_et_bien_notée",
        },
        "cuisine_a_explorer": {
            "id": cuisine_a_explorer.get("id"),
            "title_fr": cuisine_a_explorer.get("titles", {}).get("fr"),
            "iconic_score": cuisine_a_explorer.get("scoring", {}).get("iconic", {}).get("score"),
            "cuisine": (cuisine_a_explorer.get("scoring", {}).get("iconic") or {}).get("cuisine_origin", ""),
            "raison":  "cuisine_non_explorée",
        },
        "surprise_nutritionnelle": {
            "id": best_surprise.get("id"),
            "title_fr": best_surprise.get("titles", {}).get("fr"),
            "iconic_score": best_surprise.get("scoring", {}).get("iconic", {}).get("score"),
            "raison": best_label,
        },
    }


@router.get("/search")
def search_get(
    request:     Request,
    q:           str           = Query(default="", max_length=200),
    diet:        Optional[str] = Query(default=None),
    cuisine:     Optional[str] = Query(default=None),
    max_time:    Optional[int] = Query(default=None, ge=1, le=480),
    gluten_free: bool          = Query(default=False),
    limit:       int           = Query(default=10, ge=1, le=50),
):
    """Recherche GET — public, SEO-friendly."""
    check_rate_limit(request, limit=60, window_seconds=60)
    # recommend() vient de reco_service (importé en tête de fichier)  ✅
    result   = recommend(query=q, email=None, diet_override=diet, limit=limit * 2)
    filtered, total = _apply_filters(result, None, cuisine, None, max_time, gluten_free, 0, limit)
    return {
        "query": q, "total": total, "limit": limit,
        "filters": {"diet": diet, "cuisine": cuisine, "max_time": max_time},
        "results": filtered,
    }


@router.get("/{recipe_id}")
def get_recette(recipe_id: str, request: Request):
    """Fiche recette complète. **Public.**"""
    check_rate_limit(request, limit=120, window_seconds=60)
    recipes = load_recipes()
    recipe  = next((r for r in recipes if str(r.get("id","")) == str(recipe_id)), None)
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recette {recipe_id} introuvable")
    result = dict(recipe)
    result.update(_compute_enrichment(recipe))
    return result


@router.post("/recherche")
def recherche(
    req:     SearchRequest,
    request: Request,
    user:    dict | None = Depends(get_optional_user),
    skip:    int  = Query(default=0, ge=0),
    # limit est maintenant dans le body (req.limit) — le Query param reste
    # pour compatibilité ascendante avec les clients qui l'envoient en URL
    limit_qs: int = Query(default=0, ge=0, le=100, alias="limit"),
):
    """Recherche textuelle avec filtres. **Public — personnalisée si connecté.**"""
    check_rate_limit(request, limit=60, window_seconds=60)
    # Priorité : body > query string > défaut
    limit  = req.limit if limit_qs == 0 else limit_qs
    email  = user["email"] if user else None
    results = recommend(req.query, email=email, diet_override=req.filtre, limit=limit * 3)
    _, total   = _apply_filters(
        results, None, req.cuisine, req.technique, req.max_time, req.gluten_free, 0, len(results),
        high_protein=req.high_protein, low_calorie=req.low_calorie, high_fiber=req.high_fiber, low_ig=req.low_ig, max_kcal=req.max_kcal,
        astro_element=req.astro_element, moon_phase=req.moon_phase, cycle_phase=req.cycle_phase
    )
    filtered, _ = _apply_filters(
        results, None, req.cuisine, req.technique, req.max_time, req.gluten_free, skip, limit,
        high_protein=req.high_protein, low_calorie=req.low_calorie, high_fiber=req.high_fiber, low_ig=req.low_ig, max_kcal=req.max_kcal,
        astro_element=req.astro_element, moon_phase=req.moon_phase, cycle_phase=req.cycle_phase
    )
    
    filtered_enriched = _enrich_why(filtered, filters={"diet": req.filtre, "high_protein": req.high_protein, "low_calorie": req.low_calorie, "high_fiber": req.high_fiber, "low_ig": req.low_ig, "cycle_phase": req.cycle_phase})
    return {"query": req.query, "total": total, "skip": skip, "limit": limit,
            "results": filtered_enriched}


@router.post("/recommend")
def recommend_pipeline(
    request: Request,
    user:    dict         = Depends(get_user),
    query:   str          = Query(default=""),
    diet:    Optional[str] = Query(default=None),
    limit:   int          = Query(default=20, ge=1, le=50),
):
    """Pipeline de recommandation complet personnalisé."""
    check_rate_limit(request, limit=30, window_seconds=60)
    email   = user["email"] if user else None
    results = recommend(query, email=email, diet_override=diet, limit=limit)
    return {"query": query, "user": user["email"], "total": len(results), "results": results}


@router.post("/{recipe_id}/variante")
def vegan_variant_route(recipe_id: str, user: dict = Depends(get_user)):
    """Génère une variante vegan à la demande."""
    recipes = load_recipes()
    recipe  = next((r for r in recipes if str(r.get("id","")) == str(recipe_id)), None)
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recette {recipe_id} introuvable")
    if recipe.get("diet_flags", {}).get("vegan"):
        return {"status": "already_vegan", "recipe": recipe, "subs": []}
    from backend.engine.rule_engine.variants import vegan_variant           # ✅ migré
    try:
        result = vegan_variant(recipe)
    except Exception as e:
        logger.warning("vegan_variant échoué : %s", e)
        raise HTTPException(status_code=503,
            detail="Le moteur de variantes est temporairement indisponible.")
    if not result:
        raise HTTPException(status_code=422, detail="Impossible de générer une variante vegan")
    return result


@router.post("/score/unified")
def score_unified(payload: UnifiedScoreRequest, user: dict = Depends(get_user)):
    """Score une recette externe selon les 7 dimensions CDC_03c."""
    from backend.services.scoring_service import score_recipe
    return score_recipe(payload.recipe, profile=payload.profile,
                        profile_data=payload.profile_data)


class FeedbackRequest(BaseModel):
    action:       str            = Field(default="like",
                                        description="like | dislike | cook | skip | plan")
    score_shown:  Optional[float] = Field(default=None, ge=0, le=10)
    profile_used: Optional[str]   = None


@router.post("/{recipe_id}/feedback", status_code=204)
def recipe_feedback(recipe_id: str, payload: FeedbackRequest,
                    user: dict = Depends(get_user)):
    """Enregistre une interaction — alimente le learning_engine."""
    VALID = {"view", "like", "dislike", "plan", "cook", "skip"}
    if payload.action not in VALID:
        raise HTTPException(status_code=422,
            detail=f"Action invalide. Valeurs : {sorted(VALID)}")
    from backend.engine.learning_engine import save_interaction              # conservé
    save_interaction(
        email=user["email"], recipe_id=recipe_id,
        action=payload.action, score_shown=payload.score_shown,
        profile_used=payload.profile_used,
    )


@router.get("/{recipe_id}/similaires")
def similar_recipes(recipe_id: str, request: Request,
                    limit: int = Query(default=5, ge=1, le=20)):
    """Recettes similaires. **Public.**"""
    check_rate_limit(request, limit=60, window_seconds=60)
    from backend.engine.search_engine.similar import find_similar_by_id     # ✅ migré
    similar = find_similar_by_id(recipe_id, limit=limit)
    if not similar and not any(r["id"] == recipe_id for r in load_recipes()):
        raise HTTPException(status_code=404, detail=f"Recette {recipe_id} introuvable")
    return {"recipe_id": recipe_id, "count": len(similar), "similar": similar}


# ── Routes graphe ─────────────────────────────────────────────────────────────

@router.get("/graph/ingredient/{name}", tags=["Graphe"])
def graph_ingredient(name: str, user: dict = Depends(get_user)):
    """Propriétés d'un ingrédient depuis le graphe."""
    from backend.engine.graph_engine import _load_graph                     # conservé
    data = _load_graph().get(name.lower())
    if not data:
        raise HTTPException(status_code=404,
            detail=f"Ingrédient '{name}' absent du graphe")
    return {"ingredient": name, **data}


@router.get("/graph/cycle/{phase}", tags=["Graphe"])
def graph_cycle(phase: str, user: dict | None = Depends(get_optional_user)):
    """Ingrédients recommandés pour une phase du cycle féminin."""
    from backend.engine.graph_engine import get_cycle_ingredients            # conservé
    VALID = {"menstrual", "follicular", "ovulatory", "luteal",
             "menstrual_phase", "follicular_phase", "ovulatory_phase", "luteal_phase"}
    if phase not in VALID:
        raise HTTPException(status_code=400,
            detail=f"Phase invalide. Valeurs : {sorted({'menstrual','follicular','ovulatory','luteal'})}")
    ings = get_cycle_ingredients(phase)
    return {"phase": phase, "ingredients": ings, "count": len(ings)}


@router.post("/graph/analyze", tags=["Graphe"])
def graph_analyze(payload: GraphAnalyzeRequest, user: dict = Depends(get_user)):
    """Analyse complète d'une recette via le graphe."""
    from backend.engine.graph_engine import analyze_recipe                   # conservé
    if not payload.recipe.get("ingredients"):
        raise HTTPException(status_code=400, detail="'recipe.ingredients' requis")
    return analyze_recipe(payload.recipe, payload.profile)
