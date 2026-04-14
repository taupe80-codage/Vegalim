"""
graph_engine.py — Scoring et analyse depuis le graphe d'ingrédients.

Structure du graphe (format extensible) :
  benefits  : list[str]  — "high_protein", "diabete_safe"
  risks     : list[str]  — "diabetes"
  tags      : list[str]  — "vegan"
  substitutes: list[str] — première entrée = substitut recommandé
  cycle     : list[str]  — phases du cycle féminin supportées
  cycle_reason: str      — explication de la pertinence cycle

Migration depuis l'ancien format booléen :
  protein_boost → benefits: ["high_protein"]
  diabete_safe  → benefits: ["diabete_safe"]
  diabete_risk  → risks: ["diabetes"]
  vegan         → tags: ["vegan"]
"""
import logging
from functools import lru_cache
from pathlib import Path

from backend.core.data_io import load_json

logger = logging.getLogger(__name__)

_GRAPH_PATH = Path(__file__).resolve().parent.parent / "data" / "graphs" / "ingredient_relation_graph.json"

# Pondérations par bénéfice selon le profil
_BENEFIT_SCORE = {
    "high_protein": {"default": 2.0, "hyperproteine": 4.0},
    "diabete_safe": {"default": 1.0, "diabete": 2.0},
}
_RISK_PENALTY = {
    "diabetes": {"default": -3.0, "diabete": -6.0},
}


@lru_cache(maxsize=1)
def _load_graph() -> dict:
    """Chargement immutable via data_io — sécurisé et mis en cache."""
    data = load_json(_GRAPH_PATH, default={})
    # Copie profonde pour protéger le cache
    return {k: dict(v) for k, v in data.items()}


def compute_graph_score(ingredients: list[str], profile: dict | None = None) -> float:
    """
    Calcule le score d'une recette depuis le graphe d'ingrédients.

    Args:
        ingredients : liste d'ingrédients (tokens)
        profile     : dict avec 'diet' optionnel

    Returns:
        score brut (avant normalisation)
    """
    graph = _load_graph()
    diet  = (profile or {}).get("diet", "")
    score = 0.0

    for ing in ingredients:
        data = graph.get(ing.lower(), {})

        for benefit in data.get("benefits", []):
            weights = _BENEFIT_SCORE.get(benefit, {"default": 1.0})
            score  += weights.get(diet, weights["default"])

        for risk in data.get("risks", []):
            penalties = _RISK_PENALTY.get(risk, {"default": -2.0})
            score    += penalties.get(diet, penalties["default"])

    return round(score, 2)


def analyze_recipe(recipe: dict, profile: dict | None = None) -> dict:
    """
    Analyse complète d'une recette depuis le graphe.
    Retourne score, risques, substitutions, et pertinence cycle.

    Returns :
        {
          score        : float
          risks        : list[str]   — risques alimentaires détectés
          substitutes  : list[dict]  — [{from, to}]
          cycle_match  : list[str]   — phases du cycle supportées
          cycle_bonus  : float       — bonus score si cycle match
          tags         : list[str]   — tags alimentaires (vegan, etc.)
        }
    """
    graph = _load_graph()
    diet  = (profile or {}).get("diet", "")
    cycle_phase = (profile or {}).get("cycle_phase", "")

    score       = 0.0
    cycle_bonus = 0.0
    risks       = []
    substitutes = []
    cycle_match = []
    tags_found  = []

    for ing in recipe.get("ingredients", []):
        data = graph.get(ing.lower(), {})

        # Bénéfices → score
        for benefit in data.get("benefits", []):
            weights = _BENEFIT_SCORE.get(benefit, {"default": 1.0})
            score  += weights.get(diet, weights["default"])

        # Risques → pénalité + liste exposée
        for risk in data.get("risks", []):
            penalties = _RISK_PENALTY.get(risk, {"default": -2.0})
            score    += penalties.get(diet, penalties["default"])
            if risk not in risks:
                risks.append(risk)

        # Substitutions
        subs = data.get("substitutes", [])
        if subs:
            substitutes.append({"from": ing, "to": subs[0]})

        # Cycle féminin
        ing_cycle = data.get("cycle", [])
        if cycle_phase and cycle_phase in ing_cycle:
            cycle_match.append(ing)
            cycle_bonus += 3.0
            logger.debug("Cycle match : %s → %s (%s)", ing, cycle_phase,
                         data.get("cycle_reason", ""))
        elif ing_cycle:
            cycle_match.extend(ing_cycle)

        # Tags
        tags_found.extend(data.get("tags", []))

    return {
        "score":       round(score + cycle_bonus, 2),
        "graph_score": round(score, 2),
        "cycle_bonus": round(cycle_bonus, 2),
        "risks":       list(set(risks)),
        "substitutes": substitutes,
        "cycle_match": list(set(cycle_match)),
        "tags":        list(set(tags_found)),
    }


def get_substitutes(ingredient: str) -> list[str]:
    """Retourne les substituts d'un ingrédient depuis le graphe."""
    return _load_graph().get(ingredient.lower(), {}).get("substitutes", [])


def get_cycle_ingredients(phase: str) -> list[str]:
    """Retourne les ingrédients recommandés pour une phase du cycle.

    Accepte les noms courts (follicular, menstrual, ovulatory, luteal)
    ou longs (follicular_phase, ...).
    Source : female_cycle_nutrition.json
    """
    import json as _json
    from backend.engine.config import DATA_ROOT
    _cycle_path = DATA_ROOT / "modules" / "female_cycle_nutrition.json"
    try:
        with open(_cycle_path, encoding="utf-8") as _f:
            cycle_data = _json.load(_f)
    except Exception:
        return []
    phases = cycle_data.get("cycle_phases", {})
    key = phase if phase in phases else f"{phase}_phase"
    p = phases.get(key, {})
    ids   = p.get("ingredient_ids", [])
    foods = p.get("recommended_foods", [])
    return list(dict.fromkeys(ids + foods))
