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
from backend.core.data_io import load_json, load_nutrition_graph as _load_nutrition_graph
from backend.core.data_io import _MtimeCache
from backend.engine.config import DATA_ROOT

logger = logging.getLogger(__name__)

_cycle_cache = _MtimeCache("cycle_engine")

def _load_cycle_data() -> dict:
    """
    Chargement via _MtimeCache — rechargé automatiquement si female_cycle_nutrition.json
    est modifié, contrairement à @lru_cache qui nécessitait un redémarrage du serveur.
    """
    path = DATA_ROOT / "modules" / "female_cycle_nutrition.json"
    return _cycle_cache.get(path, lambda: load_json(path, default={}))


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


def get_phase_info(phase: str) -> dict:
    """Retourne les infos nutritionnelles d'une phase."""
    data   = _load_cycle_data()
    phases = data.get("cycle_phases", {})
    return phases.get(phase, {})


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
    rec_ids    = set(info.get("ingredient_ids", []))
    avoid_ids  = set(info.get("avoid_ingredient_ids", []))
    ings       = set(recipe.get("ingredients", []))

    present_rec   = sorted(ings & rec_ids)
    present_avoid = sorted(ings & avoid_ids)

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
        "omega_3":    any(i in ings for i in
                         ["chia_seeds","flaxseed_oil","walnut","hemp_seeds"]),
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
