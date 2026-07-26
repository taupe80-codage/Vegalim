"""
routes/recipes.py — Recettes : recherche, fiche, top, variante vegan.

Routes publiques (sans auth) :
  GET  /recettes              — liste paginée avec filtres
  GET  /recettes/top          — classement global
  GET  /recettes/top/{id}     — fiche recette complète  
  POST /recettes/recherche    — recherche textuelle + filtres

Routes authentifiées (plan free+) :
  POST /recettes/{id}/variante  — variante vegan à la demande
  POST /recommend               — pipeline recommandation personnalisé
  POST /recettes/{id}/feedback  — enregistre une interaction

Routes graphe → routes/graph.py (séparées pour SRP)

Enrichissement nutritionnel → services/enrichment_service.py
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional

from backend.core.auth_deps        import get_user, get_optional_user
from backend.core.rate_limiter     import check_rate_limit
from backend.services.reco_service import recommend
from backend.services.filter_service import apply_diet_filter, apply_filters
from backend.services.enrichment_service import enrich_one, enrich_why
from backend.core.data_io          import (
    load_recipes, load_nutrition_graph, load_score_graph,
    load_ingredients_dict, load_availability_graph,
)

# Engines utilisés directement dans ce fichier (variante vegan + similaires)
from backend.engine.rule_engine.variants      import vegan_variant
from backend.engine.search_engine.similar     import find_similar_by_id
from backend.services.scoring_service         import score_recipe as _score_recipe

router = APIRouter(prefix="/recettes", tags=["Recettes"])


# Alias locaux pour les call sites existants dans ce fichier
_enrich_why         = enrich_why
_compute_enrichment = enrich_one

# ── Modèles Pydantic ──────────────────────────────────────────────────────────

class SearchRequest(BaseModel):
    query:       str           = Field(default="", max_length=200)
    filtre:      Optional[str] = Field(default=None, description="vegan | vegetarien | …")
    cuisine:     Optional[str] = Field(default=None)
    cuisines:    list[str]     = Field(default_factory=list, description="Filtre multi-cuisines (OR)")
    technique:   Optional[str] = Field(default=None)
    max_time:    Optional[int] = Field(default=None, ge=1, le=480)
    difficulty:  Optional[str] = Field(default=None, description="easy | medium | hard")
    season:      Optional[str] = Field(default=None, description="spring | summer | autumn | winter")
    # ── Allergènes & régime ───────────────────────────────────────────────────
    gluten_free:    bool          = Field(default=False)
    lactose_free:   bool          = Field(default=False)
    nut_free:       bool          = Field(default=False)
    egg_free:       bool          = Field(default=False)
    dairy_free:     bool          = Field(default=False)
    soy_free:       bool          = Field(default=False)
    fermented_free: bool          = Field(default=False)
    # ── Type de plat (multi — filtre OR) ─────────────────────────────────────
    dish_type:       Optional[str] = Field(default=None)
    dish_types:      list[str]     = Field(default_factory=list)
    # ── Limit ─────────────────────────────────────────────────────────────────
    limit:       int           = Field(default=20, ge=1, le=500)
    # ── Macros & énergie ──────────────────────────────────────────────────────
    high_protein:         bool         = Field(default=False)
    good_source_protein:  bool         = Field(default=False)
    low_calorie:          bool         = Field(default=False)
    high_fiber:           bool         = Field(default=False)
    good_source_fiber:    bool         = Field(default=False)
    low_ig:               bool         = Field(default=False)
    moderate_ig:          bool         = Field(default=False)
    fodmap:               Optional[str] = Field(default=None, description="low | medium | high")
    max_kcal:             Optional[int] = Field(default=None)
    low_sugar:            bool         = Field(default=False)
    low_sodium:           bool         = Field(default=False)
    # ── Micronutriments (filtrés via diet_flags_enriched post-enrich) ─────────
    high_vitamin_c:       bool         = Field(default=False)
    source_vitamin_c:     bool         = Field(default=False)
    high_vitamin_d:       bool         = Field(default=False)
    source_vitamin_d:     bool         = Field(default=False)
    high_folate:          bool         = Field(default=False)
    source_folate:        bool         = Field(default=False)
    high_calcium:         bool         = Field(default=False)
    high_iron:            bool         = Field(default=False)
    good_source_iron:     bool         = Field(default=False)
    high_magnesium:       bool         = Field(default=False)
    source_magnesium:     bool         = Field(default=False)
    high_potassium:       bool         = Field(default=False)
    good_source_potassium: bool        = Field(default=False)
    high_zinc:            bool         = Field(default=False)
    source_zinc:          bool         = Field(default=False)
    high_omega3:          bool         = Field(default=False)
    source_omega3:        bool         = Field(default=False)
    antioxidant_rich:     bool         = Field(default=False)
    # ── Holistiques ───────────────────────────────────────────────────────────
    astro_element: Optional[str] = Field(default=None)
    moon_phase:  Optional[str] = Field(default=None)
    cycle_phase: Optional[str] = Field(default=None)


class UnifiedScoreRequest(BaseModel):
    recipe:       dict         = Field(..., description="Recette à scorer")
    profile:      str          = Field(default="default")
    profile_data: dict         = Field(default_factory=dict)


# _apply_filters -> filter_service.apply_filters (alias pour call sites existants)
_apply_filters = apply_filters


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
    from backend.engine.rule_engine.seasonality import seasonal_ingredients  # fix: était absent → NameError

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
            from backend.engine.reco_engine.learning import load_history
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

    # FIX dish_type / structural filters :
    # Quand la requête texte est vide, recommend() écrête le pool à limit*3
    # recettes scorées AVANT apply_filters(). Le scoring favorisant les plats
    # principaux, les desserts/snacks/entrées n'entrent jamais dans le pool →
    # dish_types=['dessert'] retourne toujours 0 résultats.
    #
    # Solution : requête vide → charger les 845 recettes directement (même
    # comportement que GET /recettes) et trier par score iconique.
    # Requête non-vide → recommend() reste pertinent pour la recherche textuelle,
    # mais on multiplie le pool par 10 pour couvrir toutes les catégories.
    has_text_query = bool(req.query and req.query.strip())
    if not has_text_query:
        # Pas de texte : filtres structurels seuls → tout le catalogue trié par score
        results = list(load_recipes())
        results.sort(
            key=lambda r: r.get("scoring", {}).get("iconic", {}).get("score", 0),
            reverse=True,
        )
        # Appliquer le filtre régime du profil (diet_override) si présent
        if req.filtre:
            from backend.services.filter_service import apply_diet_filter
            results = apply_diet_filter(results, req.filtre)
    else:
        # Requête texte : recommend() pour pertinence, pool agrandi pour ne pas
        # écrêter les catégories de niche (desserts, snacks, breakfasts…).
        # 1000 > taille max du catalogue (845) — garantit que toutes les recettes
        # correspondant à la requête sont incluses avant le filtre dish_type.
        results = recommend(req.query, email=email, diet_override=req.filtre, limit=1000)

    # FIX #8 : une seule passe _apply_filters (total + pagination) — élimine le
    # double calcul identique qui doublait le temps de filtrage sous charge.
    all_filtered, total = _apply_filters(
        results, None, req.cuisine, req.technique, req.max_time,
        req.gluten_free, 0, len(results),
        lactose_free=req.lactose_free,   nut_free=req.nut_free,
        egg_free=req.egg_free,           dairy_free=req.dairy_free,
        soy_free=req.soy_free,           fermented_free=req.fermented_free,
        dish_type=req.dish_type,         dish_types=req.dish_types,
        cuisines=req.cuisines,
        difficulty=req.difficulty,       season=req.season,
        low_sugar=req.low_sugar,         low_sodium=req.low_sodium,
        high_protein=req.high_protein,   good_source_protein=req.good_source_protein,
        low_calorie=req.low_calorie,
        high_fiber=req.high_fiber,       good_source_fiber=req.good_source_fiber,
        low_ig=req.low_ig,               moderate_ig=req.moderate_ig,
        fodmap=req.fodmap,
        max_kcal=req.max_kcal,
        high_vitamin_c=req.high_vitamin_c,   source_vitamin_c=req.source_vitamin_c,
        high_vitamin_d=req.high_vitamin_d,   source_vitamin_d=req.source_vitamin_d,
        high_folate=req.high_folate,         source_folate=req.source_folate,
        high_calcium=req.high_calcium,
        high_iron=req.high_iron,             good_source_iron=req.good_source_iron,
        high_magnesium=req.high_magnesium,   source_magnesium=req.source_magnesium,
        high_potassium=req.high_potassium,   good_source_potassium=req.good_source_potassium,
        high_zinc=req.high_zinc,             source_zinc=req.source_zinc,
        high_omega3=req.high_omega3,         source_omega3=req.source_omega3,
        antioxidant_rich=req.antioxidant_rich,
        astro_element=req.astro_element, moon_phase=req.moon_phase,
        cycle_phase=req.cycle_phase,
    )
    filtered = all_filtered[skip: skip + limit]
    
    filtered_enriched = _enrich_why(filtered, filters={"diet": req.filtre, "high_protein": req.high_protein, "low_calorie": req.low_calorie, "high_fiber": req.high_fiber, "low_ig": req.low_ig, "cycle_phase": req.cycle_phase})
    return {"query": req.query, "total": total, "skip": skip, "limit": limit,
            "results": filtered_enriched}


class RecommendRequest(BaseModel):
    query: str           = Field(default="")
    diet:  Optional[str] = Field(default=None)
    limit: int           = Field(default=20, ge=1, le=50)


@router.post("/recommend")
def recommend_pipeline(
    payload: RecommendRequest,
    request: Request,
    user:    dict         = Depends(get_user),
    # Query params conservés pour rétro-compat (anciens clients CLI / B2B)
    q_query: str           = Query(default="",   alias="query"),
    q_diet:  Optional[str] = Query(default=None, alias="diet"),
    q_limit: int           = Query(default=0,    alias="limit", ge=0, le=50),
):
    """Pipeline de recommandation complet personnalisé.

    Accepte les paramètres depuis le **body JSON** (usage normal frontend)
    ou depuis la **query string** (rétro-compat B2B / curl).
    Priorité : query string > body > défaut.
    """
    check_rate_limit(request, limit=30, window_seconds=60)
    # Résolution : query string prime sur body si explicitement fournis
    effective_query = q_query or payload.query
    effective_diet  = q_diet  or payload.diet
    effective_limit = q_limit if q_limit > 0 else payload.limit

    email   = user["email"] if user else None
    results = recommend(effective_query, email=email, diet_override=effective_diet, limit=effective_limit)
    return {
        "query":  effective_query,
        "user":   user["email"],
        "total":  len(results),
        "results": results,
    }


@router.post("/{recipe_id}/variante")
def vegan_variant_route(recipe_id: str, user: dict = Depends(get_user)):
    """Génère une variante vegan à la demande."""
    recipes = load_recipes()
    recipe  = next((r for r in recipes if str(r.get("id","")) == str(recipe_id)), None)
    if not recipe:
        raise HTTPException(status_code=404, detail=f"Recette {recipe_id} introuvable")
    if recipe.get("diet_flags", {}).get("vegan"):
        return {"status": "already_vegan", "recipe": recipe, "subs": []}
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
    return _score_recipe(payload.recipe, profile=payload.profile,
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
    from backend.services.interaction_service import save_interaction
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
    similar = find_similar_by_id(recipe_id, limit=limit)
    if not similar and not any(r["id"] == recipe_id for r in load_recipes()):
        raise HTTPException(status_code=404, detail=f"Recette {recipe_id} introuvable")
    return {"recipe_id": recipe_id, "count": len(similar), "similar": similar}

