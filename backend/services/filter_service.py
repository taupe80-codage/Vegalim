"""
filter_service.py — Filtrage des recettes par régime alimentaire.

Correction v6.17 :
    apply_diet_filter() délégait à RecipeRepository.filter_by_diet() qui
    ignorait les alias français et ne connaissait pas la majorité des régimes.
    Fix : utilisation directe de match_diet() avec logique canonique complète.

Correction v6.18 :
    Import ALLOWED_DIETS rendu résilient (try/except). Halal/kosher retirés
    (hors taxonomie projet). Fallback local aligné sur validators.

Correction v6.19 :
    Refonte complète. Ce module ne contient plus aucune liste d'alias —
    validators.DIET_CANONICAL est la source unique de vérité.
    lactose_free et nut_free intégrés à la taxonomie.
    Baseline végétarien appliquée sur tous les appels à match_diet().

Correction v6.20 — Gap données / filtrage (audit mai 2026) :
    PROBLÈME : recipes.json ne contient jamais health_scores ni nutrition_flags.
    Ces champs sont calculés à la demande par diet.py/enrichment_service mais
    APRÈS le filtrage → apply_filters() lisait des dicts vides → 0 résultats
    pour tous les filtres santé et micronutriments.

    FIX 1 — Cache health_scores paresseux (lazy) :
        _build_hs_cache() calcule health_scores pour les 845 recettes depuis
        recipe_nutrition_graph_v1.json (valeurs par portion déjà présentes).
        Résultat mis en cache thread-safe au premier appel de apply_filters().
        Micronutriments (calcium, fer, magnésium, potassium, vit C, zinc)
        calculés directement depuis la graph avec seuils AJR 15% / 30%.

    FIX 2 — Seuil glycémique corrigé :
        glycemic_index dans la graph suit l'échelle standard 0-100 (médiane=27).
        Anciens seuils <8/<12 ne qualifiaient qu'1 seule recette.
        Nouveaux seuils : low <55 / medium 55-70 / high ≥70 (classification OMS).

    FIX 3 — Fallback tags.diet pour les flags absents de diet_flags :
        diet_flags.raw n'est jamais persisté dans recipes.json.
        match_diet() cherche maintenant dans tags.diet comme source secondaire.

    FIX 4 — Alias difficulty hard → advanced :
        Les données utilisent 'advanced' ; le frontend envoie 'hard'.

Architecture :
    validators.DIET_ALIASES   → groupes canoniques + aliases (éditer là-bas)
    validators.DIET_CANONICAL → map alias → canonique (généré automatiquement)
    _DIET_FLAG_MAP             → canonique → clé diet_flags  (ici)
    _DIET_HEALTH_MAP           → canonique → prédicat health_scores (ici)
    _hs_cache                  → {recipe_id: health_scores} calculé depuis graph
"""
from __future__ import annotations

import logging
import threading as _threading

logger = logging.getLogger(__name__)


# ── Import validators — source de vérité des alias ────────────────────────────

try:
    from backend.core.validators import DIET_CANONICAL, ALLOWED_DIETS
except ImportError:
    logger.critical(
        "filter_service: impossible d'importer validators. "
        "DIET_CANONICAL et ALLOWED_DIETS indisponibles — aucun filtrage ne fonctionnera."
    )
    DIET_CANONICAL: dict[str, str] = {}
    ALLOWED_DIETS:  frozenset[str] = frozenset()


# ── Ingrédients marqueurs de saison ─────────────────────────────────────────
# Source : calendrier de saisonnalité France métropolitaine (ADEME / Agrilocal).
# Logique : une recette appartient à une saison si elle contient AU MOINS UN
# ingrédient marqueur. Les ingrédients neutres (légumineuses, céréales, épices)
# ne déclenchent aucune saison — ils apparaissent dans tous les résultats.
_SEASON_MARKERS: dict[str, frozenset[str]] = {
    "spring": frozenset({
        "asparagus", "spinach", "pea", "radish", "artichoke", "rhubarb",
        "strawberry", "fraise", "asperge", "epinard", "petit_pois",
        "radis", "artichaut", "rhubarbe", "watercress", "cresson",
        "sorrel", "oseille", "lettuce", "laitue", "fennel_bulb",
        "broad_bean", "feve",
    }),
    "summer": frozenset({
        "tomato", "zucchini", "eggplant", "bell_pepper", "corn", "cucumber",
        "basil", "watermelon", "peach", "apricot", "cherry", "fig",
        "raspberry", "blueberry", "blackcurrant", "green_bean", "snap_pea",
        "tomate", "courgette", "aubergine", "poivron", "mais", "concombre",
        "basilic", "pasteque", "peche", "abricot", "cerise", "figue",
        "framboise", "myrtille", "cassis", "haricot_vert",
        "nectarine", "plum", "prune", "melon",
    }),
    "autumn": frozenset({
        "pumpkin", "squash", "butternut", "apple", "pear", "mushroom",
        "grape", "chestnut", "quince", "pear", "leek", "parsnip",
        "citrouille", "courge", "butternut_squash", "pomme", "poire",
        "champignon", "shiitake", "raisin", "chataigne", "marron",
        "coing", "poireau", "panais", "broccoli", "cauliflower",
        "brocoli", "chou_fleur", "sweet_potato", "patate_douce",
        "fig", "figue", "plum", "prune", "celery_root", "celeriac",
    }),
    "winter": frozenset({
        "orange", "clementine", "grapefruit", "lemon", "kiwi",
        "carrot", "turnip", "rutabaga", "celery", "parsnip",
        "brussel_sprout", "cabbage", "red_cabbage", "sauerkraut",
        "orange", "clementine", "pamplemousse", "citron", "kiwi",
        "carotte", "navet", "rutabaga", "celeri", "panais",
        "chou_bruxelles", "chou", "chou_rouge", "choucroute",
        "pomelo", "mandarine", "persimmon", "kaki",
        "leek", "poireau", "endive", "witloof",
    }),
}

# ── Cache health_scores (calculé depuis nutrition graph) ─────────────────────
#
# recipes.json ne stocke jamais health_scores. Ce cache est construit une fois
# au premier appel d'apply_filters() depuis recipe_nutrition_graph_v1.json.
# Seuils calés sur les distributions réelles (845 recettes) et les AJR ANSES/OMS.

_hs_cache: dict[str, dict] | None = None
_hs_lock = _threading.Lock()

# Correspondance difficulty frontend → données JSON
_DIFFICULTY_ALIASES: dict[str, str] = {
    "hard":     "advanced",   # données: 'advanced', frontend envoie 'hard'
    "advanced": "advanced",
    "medium":   "medium",
    "easy":     "easy",
}


def _build_hs_cache() -> dict[str, dict]:
    """
    Pré-calcule health_scores + flags micronutriments pour chaque recette
    à partir de recipe_nutrition_graph_v1.json (valeurs par portion).

    Appelé une seule fois — thread-safe via _hs_lock.
    """
    from backend.core.data_io import load_nutrition_graph, load_recipes
    from backend.engine.rule_engine.diet import (
        _extract_ids, HIGH_FODMAP_IDS, MEDIUM_FODMAP_IDS,
        FODMAP_THRESHOLDS, _extract_quantities, FODMAP_CATEGORY_MAP,
        _GOS_HIGH,
    )

    ng      = load_nutrition_graph()
    recipes = load_recipes()
    cache: dict[str, dict] = {}

    for recipe in recipes:
        rid  = str(recipe.get("id", ""))
        nutr = ng.get(rid, {})

        # ── Valeurs par portion ───────────────────────────────────────────────
        kcal   = float(nutr.get("calories",      0) or 0)
        prot   = float(nutr.get("protein",       0) or 0)
        fiber  = float(nutr.get("fiber",         0) or 0)
        sodium = float(nutr.get("sodium",        0) or 0)
        sugar  = float(nutr.get("sugar",         0) or 0)
        gi     = float(nutr.get("glycemic_index",0) or 0)
        sat_fat = float(nutr.get("saturated_fat",0) or 0)
        omega3  = float(nutr.get("omega_3",      0) or 0)

        # ── Micronutriments ───────────────────────────────────────────────────
        vc  = float(nutr.get("vitamin_c",  0) or 0)
        ca  = float(nutr.get("calcium",    0) or 0)
        fe  = float(nutr.get("iron",       0) or 0)
        mg  = float(nutr.get("magnesium",  0) or 0)
        k   = float(nutr.get("potassium",  0) or 0)
        zn  = float(nutr.get("zinc",       0) or 0)

        # ── FODMAP — scoring quantitatif (Monash) + fallback liste ──────────
        ids = _extract_ids(recipe)
        techniques_set = {str(t).lower() for t in (recipe.get("technique") or [])}
        is_sourdough     = any(k in techniques_set for k in ("sourdough", "levain", "long_fermentation"))
        is_rinsed_legume = any(k in techniques_set for k in ("canned", "rince", "rinced", "rinsed"))

        qty_map = _extract_quantities(recipe)
        fodmap_score  = 0
        fodmap_cats: set[str] = set()
        scored_by_qty: set[str] = set()
        wheat_ids = {"wheat", "flour", "bread", "pasta", "ble", "farine", "pain"}
        has_wheat = False

        for base, grams in qty_map.items():
            thresh = FODMAP_THRESHOLDS.get(base)
            if thresh is None:
                continue
            scored_by_qty.add(base)
            for cat in thresh["cats"]:
                fodmap_cats.add(cat)
            if grams > thresh["medium"]:
                fodmap_score += 2
            elif grams > thresh["safe"]:
                fodmap_score += 1
            if base in wheat_ids:
                has_wheat = True

        for ing in ids:
            if ing in scored_by_qty:
                continue
            if ing in HIGH_FODMAP_IDS:
                fodmap_score += 2
                for cat in FODMAP_CATEGORY_MAP.get(ing, []):
                    fodmap_cats.add(cat)
            elif ing in MEDIUM_FODMAP_IDS:
                fodmap_score += 1
                for cat in FODMAP_CATEGORY_MAP.get(ing, []):
                    fodmap_cats.add(cat)
            if ing in wheat_ids:
                has_wheat = True

        if is_sourdough and has_wheat:
            fodmap_score = max(0, fodmap_score - 2)
        if is_rinsed_legume and (_GOS_HIGH & ids):
            fodmap_score = max(0, fodmap_score - 1)

        cat_labels = {"F": "fructanes", "G": "GOS", "D": "lactose", "M": "fructose", "P": "polyols"}
        fodmap_categories = sorted(cat_labels[c] for c in fodmap_cats if c in cat_labels)
        fodmap_level = "low" if fodmap_score == 0 else "medium" if fodmap_score <= 2 else "high"

        # ── Health scores ─────────────────────────────────────────────────────
        # Seuil GI corrigé : échelle standard 0-100 (OMS)
        # low < 55 / medium 55-70 / high ≥ 70
        # (ancien seuil <8/<12 ne qualifiait qu'1 recette sur 845)
        hs: dict = {
            # Macros
            "kcal":              round(kcal),
            "high_protein":      prot  >= 20.0,
            "good_source_protein": prot >= 10.0,
            "low_calorie":       kcal  <  300.0,
            "high_fiber":        fiber >= 8.0,
            "good_source_fiber": fiber >= 4.0,
            "low_sodium":        sodium < 200.0,
            "sodium_mg":         round(sodium),
            "low_sugar":         sugar  < 5.0,
            "protein_g":         round(prot,  1),
            "fiber_g":           round(fiber, 1),
            "low_sat_fat":       sat_fat < 5.0,
            # Glycémie — échelle 0-100
            "glycemic_category": (
                "low"    if gi < 55  else
                "medium" if gi < 70  else
                "high"
            ),
            # FODMAP
            "fodmap_level":      fodmap_level,
            "fodmap_score":      fodmap_score,
            "fodmap_categories": fodmap_categories,
            # Anti-inflammatoire (proxy omega-3 si disponible)
            "anti_inflammatory_score": (
                "high"   if omega3 >= 1.0 else
                "medium" if omega3 >= 0.3 else
                "low"
            ),
            # ── Micronutriments — seuils AJR ANSES/OMS ───────────────────────
            # Calibrés sur les distributions réelles du dataset (845 recettes
            # végétariennes/veganes, valeurs par portion).
            # Les valeurs plant-based sont naturellement élevées en zinc/fer :
            # légumineuses, graines, céréales complètes dominent le dataset.
            #
            # AJR : vitamine C 90mg | calcium 1000mg | fer 14mg
            #        magnésium 400mg | potassium 3500mg | zinc 10mg
            #
            # "bonne source" → seuil discriminant 15-25% AJR
            # "riche en"     → seuil discriminant 40-70% AJR
            # (seuils EU Règlement 1924/2006 adaptés aux distributions observées)
            "high_vitamin_c":         vc >= 27.0,    # 30% AJR  → ~47% recettes
            "source_vitamin_c":       vc >= 13.5,    # 15% AJR  → ~68% recettes
            "high_calcium":           ca >= 150.0,   # 15% AJR  → ~20% recettes
            "high_iron":              fe >= 4.2,     # 30% AJR  → ~22% recettes
            "good_source_iron":       fe >= 2.1,     # 15% AJR  → ~68% recettes
            "high_magnesium":         mg >= 100.0,   # 25% AJR  → ~14% recettes
            "source_magnesium":       mg >= 60.0,    # 15% AJR  → ~48% recettes
            "high_potassium":         k  >= 1050.0,  # 30% AJR  → ~11% recettes
            "good_source_potassium":  k  >= 525.0,   # 15% AJR  → ~58% recettes
            "high_zinc":              zn >= 6.0,     # 60% AJR  → ~31% recettes
            "source_zinc":            zn >= 3.0,     # 30% AJR  → ~67% recettes
            # ── Valeurs brutes (mg/g) pour affichage frontend ─────────────────
            "vitamin_c_mg":   round(vc, 1),
            "calcium_mg":     round(ca, 1),
            "iron_mg":        round(fe, 2),
            "magnesium_mg":   round(mg, 1),
            "potassium_mg":   round(k,  1),
            "zinc_mg":        round(zn, 2),
            # Antioxydants — vitamine C réelle ≥ 40mg (30% AJR, seuil discriminant ~30% recettes)
            "antioxidant_rich": vc >= 40.0,
        }
        cache[rid] = hs

    logger.info(
        "filter_service: cache health_scores construit — %d recettes",
        len(cache),
    )
    return cache


def _hs(recipe: dict) -> dict:
    """
    Retourne les health_scores d'une recette depuis le cache paresseux.
    Construit le cache au premier appel (thread-safe).
    """
    global _hs_cache
    if _hs_cache is None:
        with _hs_lock:
            if _hs_cache is None:
                _hs_cache = _build_hs_cache()
    return _hs_cache.get(str(recipe.get("id", "")), {})


def invalidate_hs_cache() -> None:
    """Force la reconstruction du cache au prochain appel (ex: après import pipeline)."""
    global _hs_cache
    with _hs_lock:
        _hs_cache = None
    logger.info("filter_service: cache health_scores invalidé")


# ── Tables de résolution ───────────────────────────────────────────────────────
#
# _DIET_FLAG_MAP   : clé canonique → champ dans recipe["diet_flags"]
# _DIET_HEALTH_MAP : clé canonique → prédicat sur recipe["health_scores"]
#
# Chaque clé canonique de DIET_ALIASES doit apparaître dans l'une des deux.
# Si un nouveau régime est ajouté dans validators, compléter ici.

_DIET_FLAG_MAP: dict[str, str] = {
    "vegan":        "vegan",
    "vegetarien":   "vegetarian",   # flag EN produit par compute_diet_flags()
    "gluten_free":  "gluten_free",
    "lactose_free": "lactose_free",
    "nut_free":     "nut_free",
    "raw":          "raw",
    "kid_friendly": "kid_friendly",
}

_DIET_HEALTH_MAP: dict[str, object] = {
    "diabete":       lambda hs: hs.get("glycemic_category") == "low",
    "hyperproteine": lambda hs: bool(hs.get("high_protein")),
}


# ── Logique de matching ────────────────────────────────────────────────────────

def match_diet(recipe: dict, diet: str) -> bool:
    """
    Vérifie si une recette correspond à un régime donné.

    Étapes :
      1. Normalise l'alias via DIET_CANONICAL → clé canonique
      2. Vérifie la baseline végétarienne du projet
      3. Résout via _DIET_FLAG_MAP (diet_flags) ou _DIET_HEALTH_MAP (health_scores)

    Args:
        recipe : dict recette (doit avoir diet_flags et health_scores)
        diet   : identifiant de régime — alias FR/EN acceptés

    Returns:
        True si la recette correspond au régime (ou si diet est vide).
        False si le flag est absent ou à False.
        True (pass-through + warning) si le régime est inconnu.
    """
    if not diet:
        return True

    if not isinstance(recipe, dict):
        logger.warning(
            "match_diet: élément non-dict ignoré (type=%s)", type(recipe).__name__
        )
        return False

    # ── 1. Normalisation alias → canonique ────────────────────────────────────
    raw      = diet.strip().lower().replace("-", "_").replace(" ", "_")
    canonical = DIET_CANONICAL.get(raw, raw)

    flags  = recipe.get("diet_flags")  or {}
    health = recipe.get("health_scores") or {}

    # ── 2. Baseline végétarienne (contrainte projet) ───────────────────────────
    # Appliquée sur tous les régimes sauf "vegetarien" lui-même (évite le double check).
    # Si le flag est absent (recette non encore scorée), on laisse passer
    # pour ne pas bloquer les données partielles en cours d'indexation.
    if canonical != "vegetarien":
        vegetarian_flag = flags.get("vegetarian")
        if vegetarian_flag is not None and not vegetarian_flag:
            logger.warning(
                "match_diet: recette id=%s écartée — non-végétarienne (baseline projet)",
                recipe.get("id", "?"),
            )
            return False

    # ── 3a. Résolution via diet_flags ─────────────────────────────────────────
    if canonical in _DIET_FLAG_MAP:
        flag_key = _DIET_FLAG_MAP[canonical]
        flag_val = flags.get(flag_key)
        if flag_val is None:
            # Fallback : certains flags (raw, kid_friendly) ne sont pas persistés
            # dans diet_flags du JSON — chercher dans tags.diet comme source
            # secondaire avant de conclure à l'absence de conformité.
            diet_tags = set((recipe.get("tags") or {}).get("diet", []))
            if diet_tags:
                return canonical in diet_tags or flag_key in diet_tags
            # diet_flags vide {} → recette non encore scorée → pass-through
            # diet_flags renseigné mais flag absent → non conforme
            return not bool(flags)
        return bool(flag_val)

    # ── 3b. Résolution via health_scores ──────────────────────────────────────
    if canonical in _DIET_HEALTH_MAP:
        return bool(_DIET_HEALTH_MAP[canonical](health))

    # ── 4. Régime inconnu ─────────────────────────────────────────────────────
    logger.warning(
        "match_diet: régime inconnu '%s' (canonique: '%s') — pass-through. "
        "Ajouter l'alias dans validators.DIET_ALIASES.",
        diet, canonical,
    )
    return True


def apply_diet_filter(recipes: list, diet: str) -> list:
    """
    Filtre une liste de recettes par régime alimentaire.

    Délègue entièrement à match_diet(). L'ordre de la liste est préservé.

    Args:
        recipes : liste de dicts recettes
        diet    : identifiant de régime (vide = pas de filtre)

    Returns:
        Sous-liste des recettes correspondant au régime.
    """
    if not diet:
        return recipes

    valid = [r for r in recipes if isinstance(r, dict)]
    skipped = len(recipes) - len(valid)
    if skipped:
        logger.warning(
            "apply_diet_filter '%s' : %d élément(s) non-dict ignoré(s)",
            diet, skipped,
        )
    filtered = [r for r in valid if match_diet(r, diet)]
    logger.debug(
        "apply_diet_filter '%s' : %d → %d recettes",
        diet, len(recipes), len(filtered),
    )
    return filtered


# Alias de compatibilité (anciens imports)
filter_recipes = apply_diet_filter


# ── Filtres combinés ────────────────────────────────────────────────────────────────────────

def apply_filters(
    recipes:      list,
    diet:         str | None   = None,
    cuisine:      str | None   = None,
    technique:    str | None   = None,
    max_time:     int | None   = None,
    gluten_free:  bool         = False,
    skip:         int          = 0,
    limit:        int          = 20,
    # ── Filtres diététiques étendus ─────────────────────────────────────────────
    lactose_free:   bool         = False,
    nut_free:       bool         = False,
    egg_free:       bool         = False,
    dairy_free:     bool         = False,
    soy_free:       bool         = False,
    fermented_free: bool         = False,
    fodmap:         str | None   = None,
    low_sugar:      bool         = False,
    low_sodium:     bool         = False,
    # ── Health scores — macros ─────────────────────────────────────────────────────
    high_protein:         bool         = False,
    good_source_protein:  bool         = False,
    low_calorie:          bool         = False,
    high_fiber:           bool         = False,
    good_source_fiber:    bool         = False,
    low_ig:               bool         = False,
    moderate_ig:          bool         = False,
    max_kcal:             int | None   = None,
    # ── Micronutriments (via nutrition_highlights agrégés par enrich_why) ──────────
    high_vitamin_c:        bool        = False,
    source_vitamin_c:      bool        = False,
    high_vitamin_d:        bool        = False,
    source_vitamin_d:      bool        = False,
    high_folate:           bool        = False,
    source_folate:         bool        = False,
    high_calcium:          bool        = False,
    high_iron:             bool        = False,
    good_source_iron:      bool        = False,
    high_magnesium:        bool        = False,
    source_magnesium:      bool        = False,
    high_potassium:        bool        = False,
    good_source_potassium: bool        = False,
    high_zinc:             bool        = False,
    source_zinc:           bool        = False,
    high_omega3:           bool        = False,
    source_omega3:         bool        = False,
    antioxidant_rich:      bool        = False,
    # ── Type de plat (dish_types = OR multi-select) ───────────────────────────────
    dish_type:    str | None   = None,
    dish_types:   list[str]    | None = None,
    # ── Cuisine multi-select (cuisines = OR) ──────────────────────────────────────
    cuisines:     list[str]    | None = None,
    # ── Difficulté & saison ───────────────────────────────────────────────────────
    difficulty:   str | None   = None,
    season:       str | None   = None,
    # ── Filtres holistiques ────────────────────────────────────────────────────────────
    astro_element: str | None  = None,
    moon_phase:   str | None   = None,
    cycle_phase:  str | None   = None,
) -> tuple[list, int]:
    """
    Filtre une liste de recettes selon des critères combinés et la pagine.

    Retourne (page, total) où :
      page  = recettes pour la page demandée [skip:skip+limit]
      total = nombre total après filtrage (avant pagination)

    Extraite de routes/recipes.py (SRP — la logique de filtrage ne doit
    pas vivre dans une route HTTP).
    """
    result = list(recipes)   # copie pour ne pas muter l'original

    # ── Régime alimentaire ────────────────────────────────────────────────────
    if diet:         result = apply_diet_filter(result, diet)
    if gluten_free:  result = apply_diet_filter(result, "gluten_free")
    if lactose_free: result = apply_diet_filter(result, "lactose_free")
    if nut_free:     result = apply_diet_filter(result, "nut_free")

    # BUG2 FIX — egg_free/dairy_free/soy_free/fermented_free : calculés à la volée
    # depuis les ingrédients (diet_flags_enriched absent hors enrich_one)
    if egg_free or dairy_free or soy_free or fermented_free:
        try:
            from backend.core.data_io import load_ingredients_dict
            ings_dict = load_ingredients_dict()
        except Exception:
            ings_dict = {}

        def _check_diet_flags(recipe: dict) -> dict:
            flags = {"egg_free": True, "dairy_free": True, "soy_free": True, "fermented_free": True}
            composition = recipe.get("composition", recipe.get("ingredients", []))
            for ing in composition:
                iid = (ing.get("ingredient") or ing.get("ingredient_id")
                       if isinstance(ing, dict) else str(ing))
                if not iid:
                    continue
                d = ings_dict.get(iid, {})
                dp = d.get("diet_profile", {})
                af = d.get("allergens_eu", [])
                if dp.get("egg_free") is False or dp.get("sans_oeuf") is False or "eggs" in af:
                    flags["egg_free"] = False
                if dp.get("dairy_free") is False or dp.get("sans_lactose") is False or "milk" in af:
                    flags["dairy_free"] = False
                if dp.get("soy_free") is False or dp.get("sans_soja") is False or "soybeans" in af:
                    flags["soy_free"] = False
                if dp.get("fermented") is True:
                    flags["fermented_free"] = False
            return flags

        def _passes_diet(recipe: dict) -> bool:
            f = _check_diet_flags(recipe)
            if egg_free and not f["egg_free"]:       return False
            if dairy_free and not f["dairy_free"]:   return False
            if soy_free and not f["soy_free"]:       return False
            if fermented_free and not f["fermented_free"]: return False
            return True

        result = [r for r in result if _passes_diet(r)]

    # ── Type de plat — single OU multi (OR) ──────────────────────────────────
    active_dish_types = set()
    if dish_types:
        active_dish_types.update(t.lower() for t in dish_types)
    if dish_type:
        active_dish_types.add(dish_type.lower())
    if active_dish_types:
        result = [r for r in result if r.get("dish_type", "").lower() in active_dish_types]

    # ── Health scores — macros (depuis cache _hs, construit sur nutrition graph) ─
    if fodmap == "not_high":
        result = [r for r in result if _hs(r).get("fodmap_level") != "high"]
    elif fodmap:
        result = [r for r in result if _hs(r).get("fodmap_level") == fodmap]
    if high_protein:
        result = [r for r in result if _hs(r).get("high_protein")]
    if good_source_protein:
        result = [r for r in result if _hs(r).get("good_source_protein") or _hs(r).get("high_protein")]
    if low_calorie:
        result = [r for r in result if _hs(r).get("low_calorie")]
    if high_fiber:
        result = [r for r in result if _hs(r).get("high_fiber")]
    if good_source_fiber:
        result = [r for r in result if _hs(r).get("good_source_fiber") or _hs(r).get("high_fiber")]
    if low_ig:
        result = [r for r in result if _hs(r).get("glycemic_category") == "low"]
    if moderate_ig:
        result = [r for r in result if _hs(r).get("glycemic_category") in ("low", "medium")]
    if max_kcal is not None:
        result = [r for r in result if (_hs(r).get("kcal") or 9999) <= max_kcal]
    if low_sugar:
        result = [r for r in result if _hs(r).get("low_sugar")]
    if low_sodium:
        result = [r for r in result if _hs(r).get("low_sodium")]

    # ── Micronutriments — depuis cache _hs (nutrition graph par portion) ─────────
    # Ancienne approche : lecture des nutrition_flags sur chaque ingrédient via
    # ingredients_dictionary.json → ce fichier n'a jamais eu ce champ → 0 résultats.
    # Nouvelle approche : seuils AJR calculés depuis recipe_nutrition_graph_v1.json
    # (voir _build_hs_cache). Flags non disponibles dans le graph (vitamin_d, omega3,
    # folate) valent False dans le cache → comportement honnête (0 résultats).
    _micro_needed = (high_vitamin_c or source_vitamin_c or high_vitamin_d or source_vitamin_d
                     or high_folate or source_folate or high_calcium or high_iron
                     or good_source_iron or high_magnesium or source_magnesium
                     or high_potassium or good_source_potassium or high_zinc or source_zinc
                     or high_omega3 or source_omega3 or antioxidant_rich)
    if _micro_needed:
        checks = [
            (high_vitamin_c,        "high_vitamin_c"),
            (source_vitamin_c,      "source_vitamin_c"),
            (high_vitamin_d,        "high_vitamin_d"),
            (source_vitamin_d,      "source_vitamin_d"),
            (high_folate,           "high_folate"),
            (source_folate,         "source_folate"),
            (high_calcium,          "high_calcium"),
            (high_iron,             "high_iron"),
            (good_source_iron,      "good_source_iron"),
            (high_magnesium,        "high_magnesium"),
            (source_magnesium,      "source_magnesium"),
            (high_potassium,        "high_potassium"),
            (good_source_potassium, "good_source_potassium"),
            (high_zinc,             "high_zinc"),
            (source_zinc,           "source_zinc"),
            (high_omega3,           "high_omega3"),
            (source_omega3,         "source_omega3"),
            (antioxidant_rich,      "antioxidant_rich"),
        ]

        def _passes_micro(recipe: dict) -> bool:
            hs = _hs(recipe)
            for flag, key in checks:
                if flag and not hs.get(key):
                    return False
            return True

        result = [r for r in result if _passes_micro(r)]

    # ── Filtres holistiques (astrologie & lune) ──────────────────────────────────
    if astro_element or moon_phase:
        from backend.core.data_io import load_astro_nutrition
        astro_data = load_astro_nutrition()

        def _recipe_matches_astro(r: dict) -> bool:
            ings = r.get("composition", [])
            if not ings:
                return False
            for ing in ings:
                ing_id = (
                    ing.get("ingredient", "") if isinstance(ing, dict) else str(ing)
                ).lower()
                meta = astro_data.get(ing_id, {})
                if astro_element and meta.get("element", "").lower() == astro_element.lower():
                    return True
                if moon_phase and moon_phase.lower() in [
                    p.lower() for p in meta.get("moon_phases", [])
                ]:
                    return True
            return False

        result = [r for r in result if _recipe_matches_astro(r)]

    # ── Filtre cycle féminin ──────────────────────────────────────────────────────────────────
    if cycle_phase:
        try:
            from backend.engine.graph_engine import get_cycle_ingredients
            good_ings = {i.lower() for i in get_cycle_ingredients(cycle_phase)}
        except ImportError:
            good_ings = set()
            logger.warning("apply_filters: graph_engine indisponible — filtre cycle ignoré")

        if good_ings:
            def _recipe_matches_cycle(r: dict) -> bool:
                ings = r.get("composition", [])
                return any(
                    (ing.get("ingredient", "") if isinstance(ing, dict) else str(ing)).lower()
                    in good_ings
                    for ing in ings
                )
            result = [r for r in result if _recipe_matches_cycle(r)]

    # ── Autres filtres texte & numériques ────────────────────────────────────────────────────
    # ── Cuisine — single OU multi (OR) ──────────────────────────────────────
    active_cuisines = set()
    if cuisines:
        active_cuisines.update(c.lower() for c in cuisines)
    if cuisine:
        active_cuisines.add(cuisine.lower())
    if active_cuisines:
        def _cuisine_match(r: dict) -> bool:
            origin = r.get("origin", {})
            c_val = (
                origin.get("cuisine", "")
                or r.get("iconic_status", {}).get("cuisine_origin", "")
                or ""
            ).lower()
            return any(c in c_val for c in active_cuisines)
        result = [r for r in result if _cuisine_match(r)]

    if technique:
        result = [
            r for r in result
            if technique.lower() in [
                t.lower() for t in (r.get("technique") or [])
            ]
        ]
    if max_time is not None:
        result = [r for r in result
                  if (r.get("timing", {}).get("total_min") or 999) <= max_time]

    # ── Difficulté ────────────────────────────────────────────────────────────
    # Alias : le frontend envoie 'hard', les données stockent 'advanced'.
    if difficulty:
        diff_norm = _DIFFICULTY_ALIASES.get(difficulty.lower(), difficulty.lower())
        result = [r for r in result
                  if r.get("difficulty_level", "").lower() == diff_norm]

    # ── Saison — détection par ingrédients marqueurs ─────────────────────────
    if season:
        _SEASON_ALIASES = {
            "printemps": "spring", "été": "summer", "ete": "summer",
            "automne": "autumn", "fall": "autumn", "hiver": "winter",
        }
        season_key = _SEASON_ALIASES.get(season.lower(), season.lower())
        markers = _SEASON_MARKERS.get(season_key, set())
        all_markers = frozenset().union(*_SEASON_MARKERS.values())
        if markers:
            def _ing_bases(recipe: dict) -> list[str]:
                return [
                    str(i.get("ingredient", "") if isinstance(i, dict) else i).split("/")[0].lower()
                    for i in (recipe.get("composition") or [])
                ]
            def _recipe_season_ok(recipe: dict) -> bool:
                bases = _ing_bases(recipe)
                # Recette neutre (aucun marqueur saisonnier) → toutes saisons
                if not any(b in all_markers for b in bases):
                    return True
                # Sinon : doit contenir au moins un marqueur de la saison demandée
                return any(b in markers for b in bases)
            result = [r for r in result if _recipe_season_ok(r)]

    total = len(result)
    page  = result[skip: skip + limit]
    logger.debug(
        "apply_filters : %d recettes --> %d après filtres, page [%d:%d]",
        len(recipes), total, skip, skip + limit,
    )
    return page, total