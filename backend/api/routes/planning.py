"""
Routes plan repas, liste de courses, saisonnalitÃƒÂ©.

MIGRATION ÃƒÂ©tape 3 Ã¢â‚¬â€ imports obsolÃƒÂ¨tes remplacÃƒÂ©s :
  meal_planner.generate_weekly_plan   Ã¢â€ â€™ planning_engine.planner.generate_plan
  meal_planner.rank_recipes           Ã¢â€ â€™ conservÃƒÂ© via compat (non migrÃƒÂ©)
  meal_planner._filter_diet           Ã¢â€ â€™ planning_engine : filtrage via filter_service
  shopping_engine.generate_shopping_list Ã¢â€ â€™ planning_engine.shopping.shopping_list
  seasonality_engine.ingredients_in_season Ã¢â€ â€™ rule_engine.seasonality.seasonal_ingredients
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional, List

from backend.core.auth_deps import get_user, get_optional_user

router = APIRouter(prefix="/planning", tags=["Planification"])


# Ã¢â€â‚¬Ã¢â€â‚¬ ModÃƒÂ¨les Pydantic Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

class MealPlanExportRequest(BaseModel):
    plan:       dict          = Field(..., description="Plan hebdo {lundi:{lunch:{id,title}}}")
    start_date: Optional[str] = Field(default=None, description="Date ISO YYYY-MM-DD")


class ShoppingListRequest(BaseModel):
    plan: dict = Field(..., description="Plan hebdo {lundi:{lunch:{id,title}}}")


class ShoppingFromRecipesRequest(BaseModel):
    recipe_ids: List[str] = Field(..., description="Liste d'IDs de recettes")
    eco:        bool      = Field(default=False, description="Marquer les reutilisations")


class DiversityScoreRequest(BaseModel):
    plan: dict = Field(..., description="Plan hebdo {lundi:{lunch:{id,title}}}")


class MealPlanReplaceRequest(BaseModel):
    plan:        dict              = Field(..., description="Plan hebdo existant")
    day:         str               = Field(..., description="Jour : monday|tuesday|Ã¢â‚¬Â¦")
    slot:        str               = Field(..., description="Repas : lunch|dinner|breakfast")
    exclude_ids: Optional[List[str]] = Field(default=None)
    diet:        Optional[str]     = Field(default=None)
    dish_type:   Optional[str]     = Field(default=None, description="Type de plat : main|soup|dessert|Ã¢â‚¬Â¦")


# Ã¢â€â‚¬Ã¢â€â‚¬ Routes Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬Ã¢â€â‚¬

@router.get("/mealplan")
def mealplan(
    diet:             Optional[str] = None,
    servings:         int           = 4,
    month:            Optional[int] = None,
    batch:            bool          = False,
    meals_per_day:    int           = Query(default=2, ge=2, le=3),
    # Filtres etendus
    max_time:         Optional[int] = None,
    # Allergenes — accepte les memes flags boolean que /recettes/recherche.
    # Coherence totale avec HomePage : egg_free=true, gluten_free=true, etc.
    allergens:        Optional[str] = None,   # compat legacy : "eggs,gluten"
    gluten_free:      bool          = False,
    lactose_free:     bool          = False,
    nut_free:         bool          = False,
    egg_free:         bool          = False,
    dairy_free:       bool          = False,
    soy_free:         bool          = False,
    cuisine:          Optional[str] = None,
    dish_type:        Optional[str] = None,
    difficulty:       Optional[str] = None,
    exclude_ids:      Optional[str] = None,
    diversity:        float         = Query(default=0.5, ge=0.0, le=1.0),
    user: dict | None = Depends(get_optional_user),
):
    """Genere un plan de repas hebdomadaire personnalise."""
    from backend.core.validators import is_valid_diet
    from backend.engine.planning_engine.planner import generate_plan
    if diet and not is_valid_diet(diet):
        from backend.core.validators import ALLOWED_DIETS
        raise HTTPException(status_code=422,
            detail=f"Regime invalide : '{diet}'. Valeurs acceptees : {sorted(ALLOWED_DIETS)}")

    # Mapping legacy allergens comma-string (_free suffixes -> noms tags.allergens)
    _ALLERGEN_TAG = {
        'egg_free': 'eggs', 'gluten_free': 'gluten', 'lactose_free': 'lactose',
        'nut_free': 'tree_nuts', 'dairy_free': 'milk', 'soy_free': 'soy',
    }
    allergen_list = []
    if allergens:
        for a in allergens.split(","):
            a = a.strip().lower()
            allergen_list.append(_ALLERGEN_TAG.get(a, a))

    # fix: les IDs v6 sont des strings (ex: "dip_baba_ghanoush_dbd030")
    exclude_list = [x.strip() for x in exclude_ids.split(",") if x.strip()] if exclude_ids else []

    return generate_plan(
        diet=diet or None,
        month=month,
        batch_cooking=batch,
        max_time=max_time,
        allergen_exclude=allergen_list or None,
        # Flags boolean — meme logique que filter_service.apply_filters
        gluten_free=gluten_free,
        lactose_free=lactose_free,
        nut_free=nut_free,
        egg_free=egg_free,
        dairy_free=dairy_free,
        soy_free=soy_free,
        cuisine=cuisine or None,
        dish_type=dish_type or None,
        difficulty=difficulty or None,
        exclude_ids=exclude_list or None,
        diversity=diversity,
    )


@router.post("/mealplan/export_ics")
def export_ics(payload: MealPlanExportRequest, user: dict = Depends(get_user)):
    """Exporte un plan de repas au format .ics (calendrier)."""
    from datetime import date, timedelta
    plan = payload.plan
    try:
        start = date.fromisoformat(payload.start_date) if payload.start_date else date.today()
    except ValueError:
        start = date.today()

    DAYS  = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//AlimUnified//FR",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH"]

    for i, day in enumerate(DAYS):
        for slot, info in (plan.get(day) or {}).items():
            if not isinstance(info, dict):
                continue
            d = (start + timedelta(days=i)).strftime("%Y%m%d")
            h = "120000" if slot == "lunch" else "190000"
            lines += [
                "BEGIN:VEVENT",
                f"UID:{d}-{slot}@alimunified",
                f"DTSTART;VALUE=DATE-TIME:{d}T{h}",
                "DURATION:PT30M",
                f"SUMMARY:{slot} Ã¢â‚¬â€ {info.get('title', slot)}",
                "END:VEVENT",
            ]
    lines.append("END:VCALENDAR")
    return {
        "ics_content": "\r\n".join(lines),
        "filename":    f"plan_{start.isoformat()}.ics",
    }


@router.post("/shopping_list")
def shopping_list_route(payload: ShoppingListRequest, user: dict | None = Depends(get_optional_user)):
    """GÃƒÂ©nÃƒÂ¨re la liste de courses depuis un plan hebdomadaire."""
    from backend.engine.planning_engine.shopping import shopping_list       # Ã¢Å"â€¦ migrÃƒÂ©
    return shopping_list(payload.plan)


@router.post("/shopping_list_from_recipes")
def shopping_from_recipes_route(payload: ShoppingFromRecipesRequest, user: dict | None = Depends(get_optional_user)):
    """Genere la liste de courses depuis une selection libre de recettes."""
    from backend.engine.planning_engine.shopping import shopping_list_from_recipes
    return shopping_list_from_recipes(payload.recipe_ids, eco=payload.eco)


# ── Correction de prix catalogue ──────────────────────────────────────────────

class PriceUpdateRequest(BaseModel):
    package_label: str  = Field(..., max_length=120, description="Label du paquet affiché (ex: 'sachet 500g')")
    new_price:     float = Field(..., gt=0, le=1000, description="Nouveau prix en euros")


# Garde-fous : la correction touche un catalogue PARTAGÉ par tous les utilisateurs.
PRICE_MAX_RATIO = 5.0          # refus au-delà de ×5 ou ÷5 par rapport au prix actuel
PRICE_EDITS_PER_HOUR = 20      # par utilisateur


@router.put("/prices/{ingredient_key}")
def update_ingredient_price(
    ingredient_key: str,
    body: PriceUpdateRequest,
    request: Request,
    user: dict = Depends(get_user),
):
    """Corrige le prix d'un paquet dans prices_catalog.json.

    Compte obligatoire (le catalogue est partagé : la route était ouverte
    à tous), 20 corrections/heure par utilisateur, variation limitée à ×5.
    """
    import json
    from datetime import date
    from pathlib import Path
    from backend.core.data_io import load_prices_catalog
    from backend.core.rate_limiter import check_rate_limit

    email = user.get("email", "")
    check_rate_limit(request, limit=PRICE_EDITS_PER_HOUR, window_seconds=3600, email=f"price:{email}")

    catalog_path = Path(__file__).parent.parent.parent / "data/config/prices_catalog.json"
    try:
        raw = json.loads(catalog_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lecture catalogue impossible : {e}")

    entry = raw.get(ingredient_key)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Ingrédient inconnu : {ingredient_key}")

    packages = entry.get("packages", [])
    if not packages:
        raise HTTPException(status_code=422, detail="Aucun conditionnement pour cet ingrédient")

    # Cherche le paquet par label (tolérant aux préfixes "N× "). Plus de repli
    # silencieux sur le premier paquet : il modifiait un autre conditionnement.
    clean_label = body.package_label.split("× ", 1)[-1] if "× " in body.package_label else body.package_label
    target = next((p for p in packages if p["label"] == clean_label), None)
    if target is None:
        raise HTTPException(status_code=404, detail=f"Conditionnement inconnu : {clean_label}")

    old_price = target["price"]
    if old_price > 0:
        ratio = body.new_price / old_price
        if not (1 / PRICE_MAX_RATIO <= ratio <= PRICE_MAX_RATIO):
            raise HTTPException(
                status_code=422,
                detail=f"Variation trop forte ({old_price} € → {body.new_price} €) : "
                       f"correction limitée à ×{PRICE_MAX_RATIO:g}",
            )
        for pkg in packages:
            pkg["price"] = round(pkg["price"] * ratio, 2)
    target["price"] = round(body.new_price, 2)  # exact sur le paquet cible

    entry["last_updated"]    = str(date.today())
    entry["user_corrected"]  = True

    try:
        tmp = catalog_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(catalog_path)          # écriture atomique
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Écriture catalogue impossible : {e}")

    logger.info("Prix corrigé par %s : %s [%s] %s → %s €",
                email, ingredient_key, clean_label, old_price, round(body.new_price, 2))

    # Invalide le cache pour que le prochain appel lise les nouveaux prix
    load_prices_catalog.cache_clear()

    return {"ok": True, "ingredient": ingredient_key, "package_label": clean_label,
            "old_price": old_price, "new_price": round(body.new_price, 2)}


@router.get("/seasonal")
def seasonal(month: int):
    """IngrÃƒÂ©dients de saison pour un mois donnÃƒÂ© (1-12). **Public.**"""
    from backend.engine.rule_engine.seasonality import seasonal_ingredients # Ã¢Å"â€¦ migrÃƒÂ©
    from backend.core.data_io import load_ingredients_dict
    try:
        d        = load_ingredients_dict()
        id_to_fr = {k: v.get("canonical_name_fr", k.replace("_", " ").title()) for k, v in d.items()}
    except Exception:
        id_to_fr = {}
    ids = seasonal_ingredients(month)
    return {
        "month":          month,
        "ingredients":    ids,
        "ingredients_fr": [{"id": i, "nom": id_to_fr.get(i, i)} for i in ids],
    }


class DayNutritionRequest(BaseModel):
    plan: dict = Field(..., description="Plan hebdo {lundi:{lunch:{recipes:[...]}}}")

@router.post("/daily_nutrition")
def daily_nutrition(payload: DayNutritionRequest, user: dict | None = Depends(get_optional_user)):
    """
    AgrÃ¨ge la nutrition de toutes les recettes par jour.
    Retourne pour chaque jour les totaux nutritionnels (somme des portions).
    """
    from backend.core.data_io import load_nutrition_graph
    ng = load_nutrition_graph()

    DAYS  = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
    MEALS = ["breakfast","lunch","dinner"]
    KEYS  = ["calories","protein","carbs","fat","fiber","sugar","sodium",
             "calcium","iron","vitamin_c","magnesium","potassium","zinc",
             "vitamin_b12","vitamin_a","vitamin_d","folate","omega3"]

    result = {}
    for day in DAYS:
        day_data = payload.plan.get(day, {})
        totals   = {k: 0.0 for k in KEYS}
        n_recipes = 0
        for meal in MEALS:
            slot    = day_data.get(meal, {})
            recipes = slot.get("recipes", [])
            if not recipes and isinstance(slot, dict) and slot.get("id"):
                recipes = [slot]
            for r in recipes:
                rid  = str(r.get("id", ""))
                if not rid:
                    continue
                nutr = ng.get(rid, {})
                for k in KEYS:
                    v = nutr.get(k) or 0
                    totals[k] += float(v)
                n_recipes += 1
        if n_recipes:
            result[day] = {k: round(v, 1) for k, v in totals.items()}
        else:
            result[day] = None
    return result


@router.post("/diversity_score")
def diversity_score(payload: DiversityScoreRequest, user: dict = Depends(get_user)):
    """Calcule le score de diversitÃƒÂ© nutritionnelle d'un plan hebdomadaire."""
    from backend.core.data_io import load_recipes, recipe_cuisine, recipe_techniques
    plan = payload.plan
    rmap = {r["id"]: r for r in load_recipes()}
    cuisines, techs, colors, ings = set(), set(), set(), set()
    n = 0
    for day_data in plan.values():
        if not isinstance(day_data, dict):
            continue
        for info in day_data.values():
            if not isinstance(info, dict):
                continue
            r = rmap.get(info.get("id"), {})
            n += 1
            c = recipe_cuisine(r)
            t = recipe_techniques(r)
            p = r.get("color_palette", "")
            if c: cuisines.add(c)
            techs.update(t)
            if p: colors.add(p)
            ings.update(str(i) for i in r.get("ingredients", []))
    return {
        "diversity_score": (
            min(len(cuisines) * 10, 40) +
            min(len(techs)    * 8,  30) +
            min(len(colors)   * 6,  20) +
            min(len(ings) // 3,     10)
        ),
        "cuisines":   len(cuisines),
        "techniques": len(techs),
        "n_recipes":  n,
    }


@router.post("/mealplan/replace")
def replace_meal(payload: MealPlanReplaceRequest, user: dict | None = Depends(get_optional_user)):
    """
    Remplace un seul repas dans un plan existant sans recalculer tout le plan.
    """
    from backend.core.data_io import load_recipes, load_nutrition_graph
    from backend.services.filter_service import apply_diet_filter

    VALID_DAYS  = {"monday", "tuesday", "wednesday", "thursday",
                   "friday", "saturday", "sunday",
                   "lundi", "mardi", "mercredi", "jeudi",
                   "vendredi", "samedi", "dimanche"}
    VALID_SLOTS = {"lunch", "dinner", "breakfast", "dejeuner", "diner", "petit_dejeuner"}
    if payload.day not in VALID_DAYS:
        raise HTTPException(status_code=422, detail=f"Jour invalide : {payload.day}")
    if payload.slot not in VALID_SLOTS:
        raise HTTPException(status_code=422, detail=f"Repas invalide : {payload.slot}")

    existing_ids = set(str(x) for x in (payload.exclude_ids or []))
    for day_data in payload.plan.values():
        if not isinstance(day_data, dict):
            continue
        for slot_data in day_data.values():
            if not isinstance(slot_data, dict):
                continue
            # Structure {id, title} (ancienne) ou {recipes: [{id, ...}]} (nouvelle)
            if slot_data.get("id"):
                existing_ids.add(str(slot_data["id"]))
            for r in slot_data.get("recipes", []):
                if isinstance(r, dict) and r.get("id"):
                    existing_ids.add(str(r["id"]))

    if payload.diet:
        from backend.core.validators import is_valid_diet, ALLOWED_DIETS
        if not is_valid_diet(payload.diet):
            raise HTTPException(status_code=422,
                detail=f"RÃƒÂ©gime invalide : '{payload.diet}'. Valeurs acceptÃƒÂ©es : {sorted(ALLOWED_DIETS)}")

    import random
    load_recipes.cache_clear()
    recipes    = list(load_recipes())
    candidates = apply_diet_filter(recipes, payload.diet) if payload.diet else recipes
    candidates = [r for r in candidates if str(r["id"]) not in existing_ids]

    # Filtre par dish_type si fourni
    if payload.dish_type:
        typed = [r for r in candidates if r.get("dish_type") == payload.dish_type]
        if typed:
            candidates = typed

    if not candidates:
        raise HTTPException(status_code=404,
            detail="Aucune recette disponible pour ce remplacement")

    # SÃƒÂ©lection alÃƒÂ©atoire dans le top-60 par iconic_score pour garantir qualitÃƒÂ© + variÃƒÂ©tÃƒÂ© illimitÃƒÂ©e
    candidates.sort(key=lambda r: r.get("scoring", {}).get("iconic", {}).get("score", 0), reverse=True)
    pool    = candidates[:60]
    new_rec = random.choice(pool)
    ng      = load_nutrition_graph()
    nutr    = ng.get(str(new_rec["id"]), {})

    new_slot = {
        "id":         new_rec["id"],
        "title_fr":   new_rec.get("titles", {}).get("fr") or new_rec.get("title_fr", ""),
        "title":      new_rec.get("titles", {}).get("original") or "",
        "_dish_type": new_rec.get("dish_type", payload.dish_type or "main"),
        "calories":   nutr.get("calories"),
        "protein":    nutr.get("protein"),
        "image":      new_rec.get("image"),
        "vegan":      (new_rec.get("diet_flags") or {}).get("vegan", False),
    }
    updated_plan = dict(payload.plan)
    if payload.day not in updated_plan:
        updated_plan[payload.day] = {}
    updated_plan[payload.day][payload.slot] = new_slot

    return {"plan": updated_plan, "replaced": new_slot,
            "day": payload.day, "slot": payload.slot}

