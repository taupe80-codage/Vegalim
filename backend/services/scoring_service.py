"""
scoring_service.py — Orchestrateur du scoring recette.

Rôle : résoudre le profil utilisateur et déléguer le calcul
à adaptive_score_engine_v4, qui lui-même s'appuie sur global_score_engine.

Pipeline :
  profile_data → resolve_profile → adaptive_score_v4(7 dims CDC_03c) → result
"""
import logging
logger = logging.getLogger(__name__)

from backend.engine.score_engine.quality import score_recipe as core_score_recipe, PROFILES


# ── Résolution du profil depuis profile_data ──────────────────────────────────

_HEALTH_GOAL_TO_PROFILE = {
    "muscle":   "athlete",
    "anemia":   "anemia",
    "diabete":  "diabetic",
    "eco":      "eco",
    "quick":    "quick",
}

def _resolve_profile(profile: str, profile_data: dict) -> str:
    """
    Détermine le profil adaptatif à utiliser.
    Priorité : profil explicite > health_goal > budget > default.
    """
    if profile and profile != "default" and profile in PROFILES:
        return profile
    health_goal = profile_data.get("health_goal", "")
    if health_goal in _HEALTH_GOAL_TO_PROFILE:
        return _HEALTH_GOAL_TO_PROFILE[health_goal]
    if profile_data.get("budget") == "low":
        return "budget"
    return "default"


def _build_context(profile_data: dict) -> dict:
    """Construit le contexte de pondération dynamique depuis le profil."""
    return {
        "strict_budget":  profile_data.get("budget") == "low",
        "high_protein":   profile_data.get("health_goal") == "muscle",
    }


# ── API publique ──────────────────────────────────────────────────────────────

def score_recipe(recipe: dict, profile: str = "default", profile_data: dict = None) -> dict:
    """
    Score une recette selon le profil utilisateur.

    Utilise les 7 dimensions CDC_03c via adaptive_score_engine_v4.
    Le score retourné est cohérent avec global_score_engine.

    Returns:
        {
          global_score   : float  (score CDC_03c non adapté, référence)
          adaptive_score : float  (score ajusté au profil — score affiché)
          final_score    : float  (= adaptive_score, exposé pour compatibilité)
          profile        : str
          details        : dict   (dims, weights, bonuses)
        }
    """
    profile_data = profile_data or {}
    effective_profile = _resolve_profile(profile, profile_data)
    context           = _build_context(profile_data)

    result = core_score_recipe(recipe, profile=effective_profile, context=context)

    # Exposer les 7 dims dans details pour transparence CDC_03c
    dims = {k: result.get("details", {}).get(k, result.get(k, 0.0))
            for k in ("nutrition","authenticity","accessibility",
                       "cost","ease","carbon","flavor")}
    merged = {**result, **dims}
    return {
        "global_score":   result.get("global_score", 0.0),
        "adaptive_score": result["score"],
        "final_score":    result["score"],
        "profile":        effective_profile,
        "details":        merged,
    }


def score_batch(recipes: list[dict], profile: str = "default",
                profile_data: dict | None = None) -> list[dict]:
    """
    Score une liste de recettes et retourne la liste triée par score décroissant.

    Chaque recette reçoit un champ `_score` avec le détail complet.
    """
    profile_data = profile_data or {}
    scored = []
    for recipe in recipes:
        try:
            result = score_recipe(recipe, profile=profile, profile_data=profile_data)
            r = dict(recipe)
            r["_score"]      = result
            r["final_score"] = result["final_score"]
            scored.append(r)
        except Exception as e:
            logger.warning("score_batch erreur recette %s : %s", recipe.get("id"), e)
            scored.append(dict(recipe))
    scored.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return scored

def normalize(value: float, max_val: float, default: float = 5.0) -> float:
    """Normalise une valeur dans [0, 10]. Si max_val=0 retourne default."""
    if max_val == 0:
        return default
    return round(max(0.0, min(10.0, value / max_val * 10.0)), 2)
