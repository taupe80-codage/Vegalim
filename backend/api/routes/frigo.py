"""
routes/frigo.py — Mon frigo : suggestions basées sur les ingrédients disponibles.

Routes :
  POST /frigo/suggestions  — recettes réalisables avec les ingrédients fournis (public)
  POST /frigo/manquants    — ingrédients manquants pour une recette cible (authentifié)
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional

from backend.core.auth_deps import get_user, get_optional_user
from backend.core.data_io import load_recipes, load_ingredients_dict
from backend.core.rate_limiter import check_rate_limit
from backend.services.ingredient_catalog import full_name_fr, names_of, resolve_names
from backend.services.fridge_scoring import (
    STAPLE, SPECIAL, COMMON, has_substance, recipe_weights, relevance, tier_of_id,
)

router = APIRouter(prefix="/frigo", tags=["Mon frigo"])


class FridgeRequest(BaseModel):
    ingredients:  list[str]      = Field(..., min_length=1,
                                         description="Liste des ingredient_id disponibles dans le frigo")
    diet:         Optional[str]  = None
    dish_types:   list[str]      = Field(default=[],
                                         description="Filtre type de plat (main, dessert, soup…). Vide = tous.")
    max_missing:  int            = Field(default=2, ge=0, le=5,
                                         description="Nombre max d'ingrédients manquants tolérés")
    limit:        int            = Field(default=50, ge=1, le=200)


class MissingRequest(BaseModel):
    fridge:    list[str] = Field(..., description="Ingrédients disponibles")
    recipe_id: str       = Field(..., description="ID de la recette cible (ex: dip_baba_ghanoush_dbd030)")


# ── Tables de correspondance sémantique ─────────────────────────────────────
#
# _SYNONYMS   : fridge_id → set d'IDs recette qui doivent AUSSI matcher
#               (écarts pluriel/singulier, vrais synonymes culinaires)
#
# _EXCLUSIONS : paires (fridge_id, recipe_id) qui NE doivent PAS matcher
#               malgré les règles préfixe/suffixe — faux-positifs confirmés
#               par audit (ex: avoir du riz ≠ avoir du vinaigre de riz)
# ─────────────────────────────────────────────────────────────────────────────

# Ids CIQUAL actuels (les anciennes tables visaient 'black_beans', 'vinegar/rice'…,
# absents des données depuis la migration : 0/11 synonymes et 2/16 exclusions
# encore réels). Vérifié par tests/test_audit_2026_11_01.py.

# Même produit sous deux ids qu'aucune règle préfixe/suffixe ne relie
# (relation symétrique, voir _SYNONYM_PAIRS)
_SYNONYM_PAIRS: tuple[tuple[str, str], ...] = (
    ("lime_juice_fresh",       "lime_raw_juice_fresh"),
    ("orange_raw_juice_fresh", "orange_juice_plain"),
    ("chickpea_boiled",        "chickpea_rinsed_canned"),
    ("white_bean_boiled",      "white_bean_canned"),
    ("white_bean_boiled",      "white_bean_dried_canned"),
    ("white_bean_canned",      "white_bean_dried_canned"),
    ("parsley_fresh_herb",     "persil"),
    ("aneth",                  "dill_weed_fresh_herb_leaf"),
    ("tomate",                 "tomato_raw_ripe"),
    ("sugars_granulated",      "white_sugar"),
    ("lettuce",                "green_salad_raw_plain"),
    # La puce « rice » (id générique) ne couvrait aucun riz blanc précis
    ("rice",                   "white_rice_raw_seed_unenriched"),
    ("rice",                   "white_rice_long_grain_seed_dried"),
    ("rice",                   "white_rice_short_grain_seed_dried"),
    ("rice",                   "white_rice_cooked_long_grain_seed"),
    ("rice",                   "white_rice_cooked_short_grain_seed"),
    ("rice",                   "basmati_rice_raw_seed"),
)
_SYNONYMS: dict[str, frozenset] = {}
for _a, _b in _SYNONYM_PAIRS:
    _SYNONYMS[_a] = _SYNONYMS.get(_a, frozenset()) | {_b}
    _SYNONYMS[_b] = _SYNONYMS.get(_b, frozenset()) | {_a}

_EXCLUSIONS: frozenset = frozenset({
    # Dérivés ou produits différents malgré le préfixe / suffixe commun
    ("rice",          "rice_flour"),
    ("rice",          "rice_paper"),
    ("rice",          "rice_vermicelli_raw_dried"),
    ("rice_flour",    "white_glutinous_rice_flour"),
    ("lemon",         "lemon_grass_fresh_herb"),   # citronnelle
    ("lemon",         "preserved_lemon"),
    ("cream",         "cream_cheese_block_whole_cow"),
    ("cream",         "cream_sour_18pct"),
    ("cream",         "cream_sour_fermented"),
    ("cream",         "vanilla_ice_cream"),
    ("butter",        "vegan_butter"),
    ("curry",         "curry_leaf"),
    ("coriander",     "coriander_spice_seed"),     # graines ≠ herbe fraîche
    ("mustard",       "mustard_raw_leaf"),
    ("banana_raw",    "plantain_banana_raw"),
    ("onion_raw",     "green_onion_raw"),          # cébette ≠ oignon
    ("strawberry",    "strawberry_jam"),
    ("water",         "orange_blossom_water"),
    ("water",         "rose_water"),
    ("water",         "sour_cherry_canned_in_water"),
})


def _get_recipe_ingredients(recipe: dict) -> set[str]:
    """Extrait les identifiants d'ingrédients d'une recette.

    Supporte les deux schemas :
     - CDC v4 : composition[].ingredient  (snake_case EN)
     - legacy  : ingredients[].ingredient_id
    """
    ids = set()
    items = recipe.get("composition") or recipe.get("ingredients", [])
    for ing in items:
        if isinstance(ing, dict):
            iid = ing.get("ingredient") or ing.get("ingredient_id", "")
        else:
            iid = str(ing)
        if iid:
            ids.add(str(iid).lower())
    return ids


def _ingredient_matches(fridge_id: str, recipe_id: str) -> bool:
    """
    Matching sémantique entre un ingrédient du frigo et un ingrédient de recette.

    Les données utilisent un système famille/variété (ex: 'tomato/fresh',
    'butter/dairy', 'citrus/lemon', 'milk_animal/whole') mais l'UI envoie
    des IDs simplifiés ('tomato', 'butter', 'lemon', 'milk').

    Ordre d'évaluation :
      0. Exclusions connues (faux-positifs) → False immédiat
      1. Synonymes explicites              → True immédiat
      2. Égalité exacte
      3. Prefix + '/'  : 'tomato'  → 'tomato/fresh'
      4. Prefix + '_'  : 'tomato'  → 'tomato_paste'
      5. Suffix '_' + fridge_id    : 'lentils' → 'green_lentils'
      6. Dernière partie après '/' : 'lemon'   → 'citrus/lemon'
         ou préfixe de cette partie: 'lemon'   → 'citrus/lemon_juice'
    """
    # 0. Exclusions prioritaires — faux-positifs confirmés
    if (fridge_id, recipe_id) in _EXCLUSIONS:
        return False

    # 1. Synonymes explicites (pluriel/singulier, vrais synonymes)
    if recipe_id in _SYNONYMS.get(fridge_id, frozenset()):
        return True

    # 2. Égalité exacte
    if fridge_id == recipe_id:
        return True

    # 3-4. Frigo est un préfixe de la recette
    if recipe_id.startswith(fridge_id + "/") or recipe_id.startswith(fridge_id + "_"):
        return True

    # 5. Frigo est un suffixe (mot complet après _)
    if recipe_id.endswith("_" + fridge_id):
        return True

    # 6. Famille/variété → regarder la dernière partie après '/'
    parts = recipe_id.split("/")
    if len(parts) > 1:
        last = parts[-1]
        if last == fridge_id or last.startswith(fridge_id + "_"):
            return True

    return False


def _fridge_coverage(fridge: set[str], needed: set[str]) -> tuple[set[str], set[str]]:
    """
    Calcule (have, missing) en tenant compte du matching hiérarchique.

    Pour chaque ingrédient de la recette, cherche s'il est couvert par
    au moins un ingrédient du frigo via _ingredient_matches().
    """
    have    = set()
    missing = set()
    for recipe_ing in needed:
        matched = any(_ingredient_matches(fridge_ing, recipe_ing) for fridge_ing in fridge)
        if matched:
            have.add(recipe_ing)
        else:
            missing.add(recipe_ing)
    return have, missing


# ── Cache des ingrédients du dataset ─────────────────────────────────────────
# Calculé une fois au premier appel de /coverage, réutilisé ensuite.
# Contient tous les ingredient IDs présents dans au moins une recette.

_recipe_ing_cache: set[str] | None = None

def _get_all_recipe_ingredient_ids() -> set[str]:
    global _recipe_ing_cache
    if _recipe_ing_cache is None:
        _recipe_ing_cache = set()
        for recipe in load_recipes():
            _recipe_ing_cache.update(_get_recipe_ingredients(recipe))
    return _recipe_ing_cache


def _resolve_fridge(keys: set[str]) -> tuple[set[str], dict[str, list[str]], list[str]]:
    """
    Rend le frigo compréhensible en français.

    Les clés déjà reconnues (puces anglaises : 'tomato', 'butter/dairy'…) sont
    gardées telles quelles.  Les autres — « poireaux », « épinards », « œufs »,
    « pomme de terre » — sont traduites en IDs recettes via le catalogue.

    Retourne (clés utilisables, {clé: ids traduits}, clés introuvables).
    """
    known = _get_all_recipe_ingredient_ids()
    usable: set[str] = set()
    pending: list[str] = []
    for key in keys:
        if any(_ingredient_matches(key, rid) for rid in known):
            usable.add(key)
        else:
            pending.append(key)

    resolved = resolve_names(pending)
    for ids in resolved.values():
        usable.update(ids)
    unrecognized = sorted(k for k in pending if k not in resolved)
    return usable, resolved, unrecognized


# ── Routes ───────────────────────────────────────────────────────────────────────

@router.get("/coverage")
def ingredient_coverage(
    request: Request,
    keys: str = Query(..., description="Clés frigo séparées par virgule"),
    user: dict | None = Depends(get_optional_user),
):
    """
    Retourne quelles clés UI ont au moins une recette correspondante dans le dataset.

    Utilisé par le frontend pour masquer dynamiquement les chips sans couverture
    (ingrédients sélectionnables mais absents de toutes les recettes actuelles).

    - `covered`   : clés actives — au moins 1 recette utilise cet ingrédient
    - `uncovered` : clés inactives — aucune recette ne correspond (à masquer)

    **Public** — pas d'authentification requise.
    """
    check_rate_limit(request, limit=120, window_seconds=60)
    fridge_keys = [k.strip() for k in keys.split(",") if k.strip()]
    if not fridge_keys:
        return {"covered": [], "uncovered": []}

    all_ings = _get_all_recipe_ingredient_ids()

    direct    = {k for k in fridge_keys
                 if any(_ingredient_matches(k, rid) for rid in all_ings)}
    resolved  = resolve_names([k for k in fridge_keys if k not in direct])
    covered   = []
    uncovered = []
    for key in fridge_keys:
        if key in direct or key in resolved:
            covered.append(key)
        else:
            uncovered.append(key)

    return {"covered": covered, "uncovered": uncovered}


@router.post("/suggestions")
def fridge_suggestions(payload: FridgeRequest, request: Request,
                        user: dict | None = Depends(get_optional_user)):
    """
    Retourne les recettes réalisables avec les ingrédients du frigo.
    **Public** — fonctionnel sans compte (CDC_11 plan gratuit).

    Tri par pertinence decroissante : un ingredient special (tofu, courge, poireau...)
    pese plus qu'un produit courant (oeufs, lait) ou un basique (sel, beurre, huile),
    puis par iconic_score. Les basiques manquants ne comptent pas dans `missing`
    (ils sont listes dans `assumed`).
    """
    check_rate_limit(request, limit=60, window_seconds=60)
    asked = {ing.lower().strip() for ing in payload.ingredients if ing.strip()}
    fridge, resolved, unrecognized = _resolve_fridge(asked)
    names = names_of([i for ids in resolved.values() for i in ids])
    recipes    = load_recipes()
    ings_dict  = load_ingredients_dict()   # pour traduire les IDs manquants en noms FR

    if payload.diet:
        from backend.services.filter_service import apply_diet_filter
        recipes = apply_diet_filter(recipes, payload.diet)

    if payload.dish_types:
        allowed = {dt.lower() for dt in payload.dish_types}
        recipes = [r for r in recipes if r.get("dish_type", "").lower() in allowed]

    def _label(iid: str) -> str:
        """
        Retourne le nom FR d'un ingredient_id.
        Fallback : reconstruit un libellé lisible depuis l'ID hiérarchique.
        Ex: 'butter/dairy' → 'beurre' (via base 'butter'), 'sugar/white' → 'sucre blanc'
        """
        # 1. Correspondance exacte dans le dictionnaire
        d = ings_dict.get(iid, {})
        if d.get("canonical_name_fr"):
            return full_name_fr(d, iid)   # « farine de riz », pas « riz »
        # 2. Correspondance sur la partie avant '/' (ex: 'butter' pour 'butter/dairy')
        base = iid.split("/")[0]
        d_base = ings_dict.get(base, {})
        if d_base.get("canonical_name_fr"):
            variant = iid.split("/")[-1].replace("_", " ")
            return f"{d_base['canonical_name_fr']} ({variant})" if variant != base else d_base["canonical_name_fr"]
        # 3. Fallback : humanise l'ID complet
        return iid.replace("_", " ").replace("/", " ")

    # Un frigo qui ne contient que des basiques (sel, huile, beurre) n'a rien
    # de plus discriminant à offrir : on ne filtre alors pas sur le fond.
    fridge_has_substance = any(tier_of_id(f) in (SPECIAL, COMMON) for f in fridge)

    scored = []
    for recipe in recipes:
        needed    = _get_recipe_ingredients(recipe)
        if not needed:
            continue
        have, missing = _fridge_coverage(fridge, needed)
        weights = recipe_weights(recipe.get("composition") or recipe.get("ingredients", []))

        # Les basiques (sel, poivre, eau, huile, beurre, farine...) sont supposes
        # presents : ils ne comptent ni dans les manquants ni dans la completude.
        assumed = {m for m in missing if weights.get(m, (0, tier_of_id(m)))[1] == STAPLE}
        missing = missing - assumed
        n_missing = len(missing)

        if n_missing > payload.max_missing:
            continue

        completeness = round(len(have) / (len(have) + n_missing), 2) if have else 0.0

        # Exclure les recettes où aucun ingrédient du frigo ne correspond :
        # avoir 0 ingrédient sur 2 avec max_missing=2 ne constitue pas une
        # suggestion utile — l'utilisateur n'a RIEN de ce qu'il faut.
        if completeness == 0.0:
            continue
        # Une recette qui ne tire du frigo que des basiques ou des aromates
        # (ail, persil...) n'est pas une suggestion : l'ingredient principal
        # doit etre la.
        if fridge_has_substance and not has_substance(weights, have):
            continue
        rel, _fit, _use = relevance(weights, have)
        iconic_score = recipe.get("scoring", {}).get("iconic", {}).get("score", 0)
        scored.append({
            # ── Identification ────────────────────────────────────────────────
            "id":             recipe["id"],
            "title_fr":       recipe.get("titles", {}).get("fr", ""),
            "titles":         recipe.get("titles", {}),

            # ── Champs pour RecipeCard ─────────────────────────────────────
            "origin":         recipe.get("origin", {}),
            "difficulty":     recipe.get("difficulty_level"),   # clé réelle dans les données
            "servings":       recipe.get("servings", 4),
            "nutrition":      recipe.get("nutrition", {}),
            "health_scores":  recipe.get("health_scores", {}),
            "tags":           recipe.get("tags", {}),
            "image_url":      recipe.get("image_url"),
            "diet_flags_enriched": recipe.get("diet_flags_enriched", {}),
            "nutrition_highlights": recipe.get("nutrition_highlights", {}),

            # ── Filtres / tri ─────────────────────────────────────────────
            "dish_type":      recipe.get("dish_type", ""),
            "iconic_score":   iconic_score,
            "final_score":    iconic_score,   # alias attendu par RecipeCard
            "diet_flags":     recipe.get("diet_flags", {}),
            "technique":      recipe.get("technique", []),
            "total_time_min": recipe.get("timing", {}).get("total_min"),

            # ── Frigo spécifique ──────────────────────────────────────────
            "completeness":   completeness,
            "have":           sorted(have),
            "missing": [
                {"id": iid, "name_fr": _label(iid)}
                for iid in sorted(missing)
            ],
            "n_missing":      n_missing,
            "assumed":        [
                {"id": iid, "name_fr": _label(iid)} for iid in sorted(assumed)
            ],
            "relevance":      round(rel, 3),
        })

    # Tri : pertinence decroissante (poids des ingredients qui portent la recette),
    # puis iconic_score en cas d'egalite
    scored.sort(key=lambda x: (-x["relevance"], -x["iconic_score"]))

    return {
        "fridge_ingredients": sorted(asked),
        "resolved":     {                # nom saisi -> ingredients retenus
            key: [{"id": i, "name_fr": names[i]} for i in ids]
            for key, ids in resolved.items()
        },
        "unrecognized": unrecognized,   # noms qu'aucun ingrédient ne reconnait
        "total":  len(scored),
        "limit":  payload.limit,
        "results": scored[: payload.limit],
    }


@router.post("/manquants")
def missing_ingredients(payload: MissingRequest, request: Request,
                         user: dict = Depends(get_user)):
    """
    Retourne les ingrédients manquants pour réaliser une recette cible
    avec les ingrédients actuels du frigo.
    """
    check_rate_limit(request, limit=60, window_seconds=60)
    recipes = load_recipes()
    recipe  = next((r for r in recipes if r["id"] == payload.recipe_id), None)
    if not recipe:
        raise HTTPException(status_code=404,
                            detail=f"Recette {payload.recipe_id} introuvable")

    fridge, _, _   = _resolve_fridge({ing.lower().strip() for ing in payload.fridge if ing.strip()})
    needed         = _get_recipe_ingredients(recipe)
    have, missing  = _fridge_coverage(fridge, needed)

    # Comme /suggestions : les basiques (sel, eau, huile…) sont supposés
    # présents et ne comptent ni dans les manquants ni dans la complétude.
    weights = recipe_weights(recipe.get("composition") or recipe.get("ingredients", []))
    assumed = {m for m in missing if weights.get(m, (0, tier_of_id(m)))[1] == STAPLE}
    missing = missing - assumed

    # Enrichir les ingrédients manquants avec leur nom FR
    ings_dict = load_ingredients_dict()
    missing_enriched = []
    for iid in sorted(missing):
        d = ings_dict.get(iid, {})
        missing_enriched.append({
            "id":      iid,
            "name_fr": full_name_fr(d, iid) if d else iid,
            "category": d.get("category", ""),
            "available_in_france": True,  # optimiste par défaut
        })

    return {
        "recipe_id":    payload.recipe_id,
        "recipe_title": recipe.get("titles", {}).get("fr", ""),
        "fridge_count": len(fridge),
        "needed_count": len(needed),
        "have_count":   len(have),
        "missing_count": len(missing),
        "completeness": round(len(have) / (len(have) + len(missing)), 2) if have or missing else 1.0,
        "have":    sorted(have),
        "missing": missing_enriched,
        "assumed": [
            {"id": iid, "name_fr": full_name_fr(ings_dict[iid], iid) if iid in ings_dict else iid}
            for iid in sorted(assumed)
        ],
    }
