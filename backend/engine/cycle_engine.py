"""
Cycle Engine
=============
Adapte le scoring nutritionnel aux phases du cycle menstruel.

Spec : Cycle adaptation | Nutrition needs | Adjust scoring | Scientific

Phases :
  menstrual   (j1-5)   → fer, magnésium, oméga-3, vitamine C
  follicular  (j6-13)  → protéines, vitamine B, fibres
  ovulatory   (j14-16) → antioxydants, vitamine C, zinc
  luteal      (j17-28) → magnésium, vitamine B6, calcium, tryptophane

Sources : données female_cycle_nutrition.json du projet
"""

import json as _j
import logging
from datetime import datetime
from backend.core.data_io import load_cycle_data as _load_cycle_data
from backend.core.data_io import load_nutrition_graph as _load_nutrition_graph
from backend.engine.config import DATA_ROOT

logger = logging.getLogger(__name__)


PHASE_FROM_DAY = {
    range(1,  6):  "menstrual_phase",
    range(6,  14): "follicular_phase",
    range(14, 17): "ovulatory_phase",
    range(17, 29): "luteal_phase",
}


def get_phase(cycle_day: int) -> str:
    """Retourne le nom de la phase pour un jour du cycle donné."""
    for day_range, phase in PHASE_FROM_DAY.items():
        if cycle_day in day_range:
            return phase
    return "follicular_phase"   # défaut


# ── Concepts du fichier → identifiants CIQUAL des recettes ───────────────────
# female_cycle_nutrition.json nomme les ingrédients par concept : noms courts
# d'avant la migration CIQUAL (ingredient_ids : 'spinach', 'beet') et noms
# français (recommended_foods : 'épinards'). Les recettes utilisent les ids
# CIQUAL ('spinach_raw_baby', 'beetroot_raw_root') : comparés tels quels, le
# filtre cycle trouvait 4 / 0 / 5 / 0 recettes selon la phase. Table explicite
# et relue ; 'legumes_crus' (trop vague) et 'riz_complet' (absent) restent sans
# correspondance. Le fichier garde ses concepts, affichés tels quels par l'API.
CYCLE_CONCEPT_IDS: dict[str, tuple[str, ...]] = {
    "turmeric":       ("turmeric_powder",),
    "dark_chocolate": ("dark_chocolate_40_cocoa_baking_tablet", "cocoa_powder_unsweetened"),
    "chocolat_noir":  ("dark_chocolate_40_cocoa_baking_tablet", "cocoa_powder_unsweetened"),
    "red_bean_cooked": ("kidney_bean_boiled", "kidney_bean_dried"),
    "pomegranate":    ("pomegranate_raw", "pomegranate_juice_plain"),
    "grenade":        ("pomegranate_raw", "pomegranate_juice_plain"),
    "chickpea":       ("chickpea_boiled", "chickpea_raw_dried", "chickpea_rinsed_canned",
                       "roasted_chickpea", "chana_dal", "chickpea_flour"),
    "pois_chiches":   ("chickpea_boiled", "chickpea_raw_dried", "chickpea_rinsed_canned",
                       "roasted_chickpea", "chana_dal", "chickpea_flour"),
    "red_lentil":     ("red_lentil_dried",),
    "green_lentil":   ("green_lentil_boiled", "green_lentil_dried"),
    "lentilles":      ("red_lentil_dried", "green_lentil_boiled", "green_lentil_dried",
                       "urad_lentil"),
    "sesame":         ("sesame_raw_seed", "sesame_seed_hulled_dried", "black_sesame",
                       "sesame_tahini_raw_butter_seed_plant"),
    "spinach":        ("spinach", "spinach_cooked", "spinach_raw_baby", "spinach_raw_mature"),
    "épinards":       ("spinach", "spinach_cooked", "spinach_raw_baby", "spinach_raw_mature"),
    "ginger":         ("ginger_raw_root_fresh", "ginger_powder"),
    "beet":           ("beetroot_raw_root", "beetroot_cooked_root"),
    "betterave":      ("beetroot_raw_root", "beetroot_cooked_root"),
    "tofu":           ("tofu_plain_pre_packaged", "tofu_smoked_pre_packaged",
                       "silken_tofu_pre_packaged"),
    "graines_de_lin": ("flaxseed_linseed_ground",),
    "flaxseed_oil":   ("flaxseed_linseed_ground",),
    "walnut":         ("walnut_shelled_dried",),
    "noix":           ("walnut_shelled_dried",),
    "broccoli":       ("broccoli_raw", "chinese_broccoli_cooked"),
    "brocoli":        ("broccoli_raw", "chinese_broccoli_cooked"),
    "pumpkin_seeds":  ("pumpkin_squash_raw_seed",),
    "graines_de_courge": ("pumpkin_squash_raw_seed",),
    "green_bean":     ("french_bean_raw",),
    "carrot":         ("carrot_raw",),
    "avocado":        ("avocado_raw",),
    "avocat":         ("avocado_raw",),
    "quinoa_grain":   ("quinoa_raw_dried",),
    "quinoa":         ("quinoa_raw_dried",),
    "cauliflower":    ("cauliflower_raw_flower",),
    "chia_seeds":     ("chia_raw_seed_dried",),
    "oats":           ("oat_flakes_whole_seed",),
    "avoine":         ("oat_flakes_whole_seed",),
    "amandes":        ("almond_raw_skinless_unsalted", "almond_raw_with_skin_unsalted",
                       "almond_butter_plain_plant", "almond_flour"),
    "cherry_tomato":  ("cherry_tomato_raw",),
    "tomato":         ("tomato_raw_ripe", "cherry_tomato_raw", "tomato_crushed_canned",
                       "tomato_paste_unsalted_canned", "tomato_dried", "tomato_dried_in_oil",
                       "tomato_sauce_salted_canned"),
    "tomate":         ("tomato_raw_ripe", "cherry_tomato_raw", "tomato_crushed_canned",
                       "tomato_paste_unsalted_canned", "tomato_dried", "tomato_dried_in_oil",
                       "tomato_sauce_salted_canned"),
    "onion":          ("onion_raw", "yellow_onion_raw", "white_onion_raw", "red_onion_raw",
                       "sweet_onion_raw"),
    "garlic":         ("garlic_raw",),
    "bell_pepper":    ("red_bell_pepper_raw", "green_bell_pepper_raw"),
    "poivron":        ("red_bell_pepper_raw", "green_bell_pepper_raw"),
    "corn":           ("sweet_corn_canned", "sweet_corn_on_the_cob_cooked", "sweet_corn_raw_fresh"),
    "baies":          ("strawberry", "raspberry_raw", "blueberry", "blueberry_raw",
                       "bilberry_raw", "mixed_berries", "lingonberry"),
    "fennel":         ("fennel_raw",),
    "sweet_potato":   ("sweet_potato_raw",),
    "patate_douce":   ("sweet_potato_raw",),
    "banana":         ("banana_raw",),
    "banane":         ("banana_raw",),
    "yogurt":         ("yogurt_fermented_plain", "yogurt_greek_plain_4pct",
                       "yogurt_greek_style_plain_8pct", "yogurt_plain_3pct",
                       "soybean_yogurt_plain_plant"),
    "lait_coco":      ("coconut_milk_plant",),
    "salt":           ("table_salt_unenriched", "fleur_de_sel_unenriched"),
}

# Sources d'oméga-3 (bonus focus « omega_3 ») : concepts et ids CIQUAL
_OMEGA3_IDS = frozenset({"chia_seeds", "flaxseed_oil", "walnut", "hemp_seeds",
                         "chia_raw_seed_dried", "flaxseed_linseed_ground",
                         "walnut_shelled_dried", "hemp_seed_hulled"})


def _phase_key(phase: str) -> str:
    """'menstrual' → 'menstrual_phase' (les deux formes circulent dans l'API)."""
    phase = (phase or "").strip().lower()
    return phase if phase.endswith("_phase") else f"{phase}_phase"


def get_phase_info(phase: str) -> dict:
    """Retourne les infos nutritionnelles d'une phase (forme courte ou longue)."""
    data   = _load_cycle_data()
    phases = data.get("cycle_phases", {})
    return phases.get(_phase_key(phase), {})


def cycle_id_map(phase: str, avoid: bool = False) -> dict[str, str]:
    """{id d'ingrédient: concept} pour une phase.

    avoid=False : ingredient_ids + recommended_foods ; avoid=True :
    avoid_ingredient_ids. Chaque concept se correspond à lui-même (anciens
    formats) et à ses ids CIQUAL (CYCLE_CONCEPT_IDS).
    """
    info = get_phase_info(phase)
    if avoid:
        concepts = info.get("avoid_ingredient_ids", [])
    else:
        concepts = list(info.get("ingredient_ids", [])) + list(info.get("recommended_foods", []))
    result: dict[str, str] = {}
    for concept in concepts:
        c = str(concept).lower()
        result.setdefault(c, c)
        for iid in CYCLE_CONCEPT_IDS.get(c, ()):
            result.setdefault(iid, c)
    return result


def _recipe_ingredient_ids(recipe: dict) -> set[str]:
    """Ids d'ingrédients : composition[] (schéma actuel) et ingredients[] (ancien)."""
    ids = set()
    for item in recipe.get("composition") or []:
        if isinstance(item, dict) and item.get("ingredient"):
            ids.add(str(item["ingredient"]).lower())
    for item in recipe.get("ingredients") or []:
        raw = item.get("ingredient_id", "") if isinstance(item, dict) else item
        if raw:
            ids.add(str(raw).lower())
    return ids


def cycle_score(recipe: dict, phase: str | None = None,
                cycle_day: int | None = None) -> dict:
    """
    Calcule le score d'adéquation d'une recette pour une phase du cycle.

    Args:
        recipe     : dict recette
        phase      : nom de la phase (sinon inféré depuis cycle_day)
        cycle_day  : jour du cycle 1-28 (optionnel si phase fournie)

    Returns:
        {
          "score":        float 0-10,
          "phase":        str,
          "phase_days":   str,
          "recommended":  list[str],  # ingrédients recommandés présents
          "to_avoid":     list[str],  # ingrédients à éviter présents
          "focus":        list[str],  # nutriments ciblés
          "notes":        str,
        }
    """
    if phase is None and cycle_day is not None:
        phase = get_phase(cycle_day)
    elif phase is None:
        phase = "follicular_phase"

    info       = get_phase_info(phase)
    rec_map    = cycle_id_map(phase)
    avoid_map  = cycle_id_map(phase, avoid=True)
    # Ne lisait que l'ancien ingredients[] : 0 sur toute vraie recette
    ings       = _recipe_ingredient_ids(recipe)

    # Concepts présents (deux variantes du même concept comptent une fois)
    present_rec   = sorted({rec_map[i] for i in ings if i in rec_map})
    present_avoid = sorted({avoid_map[i] for i in ings if i in avoid_map})

    # Score : +1 par ingrédient recommandé présent, -0.5 par ingrédient à éviter
    raw   = len(present_rec) * 1.0 - len(present_avoid) * 0.5
    score = round(min(max(raw, 0.0), 10.0), 2)

    # Bonus si la recette couvre plusieurs nutriments focus
    focus       = info.get("focus", [])
    nutr_ng     = {}
    try:
        # Utilise le loader déjà mis en cache (load_nutrition_graph est @lru_cache
        # dans data_io) au lieu de relire le fichier 336 KB à chaque cycle_score().
        ng      = _load_nutrition_graph()
        nutr_ng = ng.get(str(recipe.get("id", "")), {}) or {}
    except Exception as _e:
        logger.debug("cycle_engine: graphe nutrition indisponible -- %s", _e)

    nutr_bonuses = {
        "iron":       (nutr_ng.get("iron",     0) or 0) > 3,
        "protein":    (nutr_ng.get("protein",  0) or 0) >= 12,
        "fiber":      (nutr_ng.get("fiber",    0) or 0) >= 8,
        "calcium":    (nutr_ng.get("calcium",  0) or 0) > 100,
        "magnesium":  (nutr_ng.get("magnesium",0) or 0) > 50,
        "vitamin_c":  (nutr_ng.get("vitamin_c",0) or 0) > 20,
        "omega_3":    bool(ings & _OMEGA3_IDS),
    }
    focus_covered = sum(1 for f in focus if nutr_bonuses.get(f, False))
    score = round(min(score + focus_covered * 0.5, 10.0), 2)

    return {
        "score":       score,
        "phase":       phase,
        "phase_days":  info.get("days", ""),
        "focus":       focus,
        "recommended": present_rec,
        "to_avoid":    present_avoid,
        "notes":       info.get("notes", ""),
    }


def adjust_ranking(recipes: list[dict],
                   phase: str | None = None,
                   cycle_day: int | None = None,
                   weight: float = 0.25) -> list[dict]:
    """
    Ajuste le classement d'une liste de recettes selon la phase du cycle.

    Args:
        recipes    : liste triée par score de base
        phase/cycle_day : phase ou jour du cycle
        weight     : poids du score cycle dans le score final (0-1)

    Returns:
        Recettes re-classées avec '_cycle_score' attaché
    """
    result = []
    for r in recipes:
        cs = cycle_score(r, phase, cycle_day)

        # Priorité de lecture du score de base :
        #   1. final_score   — injecté par scoring.batch_score (pipeline reco)
        #   2. global_score  — injecté par pipeline.run() (pipeline batch)
        #   3. adaptive_score — ancien champ pré-v6
        #   4. 5.0           — fallback neutre
        base = float(
            r.get("final_score")
            or r.get("global_score")
            or r.get("adaptive_score")
            or 5.0
        )

        # Score composite = score_base × (1-weight) + cycle_score × weight
        adjusted = round(base * (1 - weight) + cs["score"] * weight, 2)

        # Copie pour ne pas muter le dict original
        enriched = dict(r)
        enriched["_cycle_score"]    = cs
        enriched["_adjusted_score"] = adjusted
        result.append(enriched)

    result.sort(key=lambda x: -x["_adjusted_score"])
    return result
