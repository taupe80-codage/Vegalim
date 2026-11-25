"""
routes/frigo.py — Mon frigo : suggestions basées sur les ingrédients disponibles.

Routes :
  POST /frigo/suggestions  — recettes réalisables avec les ingrédients fournis (public)
  POST /frigo/manquants    — ingrédients manquants pour une recette cible (authentifié)
  POST /frigo/rapide       — « Sur place » : recettes où l'aliment donné est la vedette (public)
"""
import logging
logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from typing import Optional

from backend.core.auth_deps import get_user, get_optional_user
from backend.core.data_io import load_recipes, load_ingredients_dict, sub_recipe_label
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

# Même produit sous deux ids qu'aucune règle préfixe/suffixe ne relie ;
# « rice », « lemon », « butter », « coriander » : clés des puces de Mon frigo
# (relation symétrique, voir _SYNONYM_PAIRS)
_SYNONYM_PAIRS: tuple[tuple[str, str], ...] = (
    ("lime_juice_fresh",       "lime_raw_juice_fresh"),
    ("orange_raw_juice_fresh", "orange_juice_plain"),
    ("chickpea_boiled",        "chickpea_rinsed_canned"),
    ("white_bean_boiled",      "white_bean_canned"),
    ("white_bean_boiled",      "white_bean_dried_canned"),
    ("white_bean_canned",      "white_bean_dried_canned"),
    ("sugars_granulated",      "white_sugar"),
    ("lettuce_raw",            "green_salad_raw_plain"),
    # La puce « rice » (id générique) ne couvrait aucun riz blanc précis
    ("rice",                   "white_rice_raw_seed_unenriched"),
    ("rice",                   "white_rice_long_grain_seed_dried"),
    ("rice",                   "white_rice_short_grain_seed_dried"),
    ("rice",                   "white_rice_cooked_long_grain_seed"),
    ("rice",                   "white_rice_cooked_short_grain_seed"),
    ("rice",                   "basmati_rice_raw_seed"),
    # Puces dont la clé ne ressemble à aucun id de recette
    ("beet",                   "beetroot_raw_root"),
    ("beet",                   "beetroot_cooked_root"),
    ("green_bean",             "french_bean_raw"),
    ("flax_seeds",             "flaxseed_linseed_ground"),
    ("dijon_mustard",          "mustard"),                 # moutarde préparée (ml)
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
    ("curry_powder",  "curry_leaf"),
    ("coriander",     "coriander_spice_seed"),     # graines ≠ herbe fraîche
    ("mustard",       "mustard_raw_leaf"),
    ("banana_raw",    "plantain_banana_raw"),
    ("onion_raw",     "green_onion_raw"),          # cébette ≠ oignon
    ("strawberry_raw", "strawberry_jam"),
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
        from backend.core.data_io import matches_dish_types
        allowed = {dt.lower() for dt in payload.dish_types}
        recipes = [r for r in recipes if matches_dish_types(r, allowed)]
    else:
        # Préparations de base (concentré de tomate, lait de riz maison…) : pas des
        # suggestions de repas, comme ailleurs sur le site (type « base » pour les voir)
        from backend.core.data_io import is_component_recipe
        recipes = [r for r in recipes if not is_component_recipe(r)]

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
        # 3. Sous-recette (base_halloumi_293d5e) : son titre
        label = sub_recipe_label(iid)
        if label:
            return label
        # 4. Fallback : humanise l'ID complet
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
    # Par tranches de pertinence de 0,1, puis le nombre d'ingrédients du frigo
    # utilisés : la pertinence plafonne dès qu'un ingrédient principal est là, et
    # « Riz blanc » (1 ingrédient du frigo) passait devant une soupe qui en utilise 4.
    scored.sort(key=lambda x: (-round(x["relevance"] * 10), -len(x["have"]),
                               -x["relevance"], -x["iconic_score"]))

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
            "name_fr": full_name_fr(d, iid) if d else (sub_recipe_label(iid) or iid),
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


# ── Sur place : l'aliment principal, sans frigo enregistré (2026-11-25) ──────
# Hors de chez soi (location, amis, marché) : on donne l'aliment qu'on a
# (« courgette », « pois chiches ») et l'on veut les recettes où il est la
# vedette, de la plus « à la courgette » à la moins. Le reste de la recette ne
# filtre pas ; seuls le matériel (four, mixeur) et le temps peuvent le faire.

import re as _re
import unicodedata as _ud

MIN_MAIN_SHARE = 0.15     # l'aliment pèse au moins 15 % du plat (hors basiques)…
_OVEN = _re.compile(r"\b(four|enfourn\w*|pr[ée]chauff\w*|gratiner|gratinez)\b", _re.I)
_BLEND = _re.compile(r"\b(mix(er|ez|é|ée|és|ées)|mixeur|blender|robot|mouliner|moulinez)\b", _re.I)
_OVEN_EQ = {"four", "plat_gratin", "moule_tarte", "plaque_four", "plaques_four"}
_BLEND_EQ = {"mixeur", "mixeur_plongeant", "robot_pâtissier", "blender"}


class QuickRequest(BaseModel):
    ingredients: list[str] = Field(..., min_length=1, max_length=10,
                                   description="Aliments disponibles sur place (noms en français)")
    no_oven:     bool          = Field(default=False, description="Pas de four")
    no_blender:  bool          = Field(default=False, description="Pas de mixeur")
    max_time:    Optional[int] = Field(default=None, ge=5, le=600, description="Temps total max (min)")
    diet:        Optional[str] = None
    limit:       int           = Field(default=30, ge=1, le=100)


def _fold(text: str) -> str:
    t = _ud.normalize("NFD", (text or "").lower().replace("œ", "oe"))
    return "".join(c for c in t if _ud.category(c) != "Mn")


def _needs(recipe: dict) -> tuple[bool, bool]:
    """(four, mixeur) d'après le matériel listé et le texte des étapes (le
    matériel n'est renseigné que pour la moitié des recettes)."""
    text = " ".join(recipe.get("instructions") or [])
    eq = {str(e).lower() for e in recipe.get("equipment") or []}
    return (bool(_OVEN.search(text) or eq & _OVEN_EQ), bool(_BLEND.search(text) or eq & _BLEND_EQ))


def _in_title(label: str, title: str) -> bool:
    words = [w for w in _re.split(r"[^a-z]+", _fold(label)) if len(w) > 2]
    t = _fold(title)
    return bool(words) and all(_re.search(rf"\b{_re.escape(w.rstrip('sx'))}(s|x)?\b", t) for w in words)


@router.post("/rapide")
def quick_fridge(payload: QuickRequest, request: Request,
                 user: dict | None = Depends(get_optional_user)):
    """
    « Sur place » : recettes où l'aliment donné est la vedette, triées par la
    place qu'il tient dans le plat (avec plusieurs aliments, celles qui les
    utilisent tous d'abord ; puis nommé dans le titre ; puis part du poids hors
    basiques). Ne lit ni n'écrit le frigo enregistré. **Public.**
    """
    from backend.core.data_io import is_component_recipe
    from backend.services.fridge_scoring import _mass, tier_of_item

    check_rate_limit(request, limit=60, window_seconds=60)
    labels = [i.strip() for i in payload.ingredients if i.strip()]
    keys = {l.lower() for l in labels}
    fridge, resolved, unrecognized = _resolve_fridge(keys)
    # Ids de chaque aliment saisi (une saisie peut couvrir plusieurs ids)
    ids_of = {l: (resolved.get(l.lower()) or ([l.lower()] if l.lower() in fridge else [])) for l in labels}
    ids_of = {l: ids for l, ids in ids_of.items() if ids}

    recipes = [r for r in load_recipes() if not is_component_recipe(r)]
    if payload.diet:
        from backend.services.filter_service import apply_diet_filter
        recipes = apply_diet_filter(recipes, payload.diet)

    out = []
    for r in recipes:
        total_min = (r.get("timing") or {}).get("total_min")
        if payload.max_time and isinstance(total_min, (int, float)) and total_min > payload.max_time:
            continue
        oven, blender = _needs(r)
        if (payload.no_oven and oven) or (payload.no_blender and blender):
            continue
        items = [c for c in (r.get("composition") or [])
                 if isinstance(c, dict) and (c.get("meta") or {}).get("role") != "serving_suggestion"]
        tiers = {id(c): tier_of_item(c) for c in items}
        mass = sum(_mass(c) for c in items if tiers[id(c)] != STAPLE) or 1.0
        title = (r.get("titles") or {}).get("fr") or ""
        matched = []
        for label, ids in ids_of.items():
            share = sum(_mass(c) for c in items if tiers[id(c)] != STAPLE
                        and any(_ingredient_matches(f, str(c.get("ingredient") or "").lower()) for f in ids)) / mass
            star = _in_title(label, title) and share > 0
            if share >= MIN_MAIN_SHARE or star:
                matched.append({"label": label, "share_pct": round(share * 100), "in_title": star})
        if not matched:
            continue
        main = max((c for c in items if tiers[id(c)] != STAPLE), key=_mass, default=None)
        others = [str(c.get("ingredient")) for c in items if tiers[id(c)] in (SPECIAL, COMMON)
                  and not any(_ingredient_matches(f, str(c.get("ingredient") or "").lower())
                              for ids in ids_of.values() for f in ids)]
        out.append({
            "id": r["id"], "title_fr": title, "titles": r.get("titles"),
            "image_url": r.get("image_url"), "dish_type": r.get("dish_type"),
            "total_time_min": total_min, "needs_oven": oven, "needs_blender": blender,
            "matched": sorted(matched, key=lambda m: -m["share_pct"]),
            "main_ingredient": str(main.get("ingredient")) if main else None,
            "n_others": len(set(others)),
            # plusieurs aliments donnés : ceux qui les utilisent tous d'abord
            "_score": (len(matched), max(m["in_title"] for m in matched), sum(m["share_pct"] for m in matched)),
        })
    out.sort(key=lambda x: x["_score"], reverse=True)
    out = out[: payload.limit]
    names = names_of([x["main_ingredient"] for x in out if x["main_ingredient"]])
    for x in out:
        x.pop("_score")
        x["main_ingredient_name"] = names.get(x["main_ingredient"]) if x["main_ingredient"] else None
    return {
        "understood": {l: [{"id": i, "name_fr": n} for i, n in names_of(ids).items()] for l, ids in ids_of.items()},
        "unrecognized": [l for l in labels if l not in ids_of],
        "total": len(out),
        "results": out,
    }
