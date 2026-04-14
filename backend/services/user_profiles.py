"""
User Profiles
==============
Gestion des profils culinaires utilisateurs.

Spec : User profiles | Diet/goal | Extensible

Séparation des responsabilités :
  - culinary_product_engine.py → compte, clé API, plan (free/starter/pro)
  - user_profiles.py           → préférences culinaires (cuisines, allergies, objectifs)
"""

import json
from datetime import datetime
from backend.engine.config import PRODUCT_PATH

PROFILES_PATH = PRODUCT_PATH / "user_culinary_profiles.json"

VALID_DIETS  = {"vegan", "vegetarian", "all"}
VALID_GOALS  = {"health", "budget", "discovery", "comfort", "default",
                "health_focus", "vegan_strict"}
VALID_PHASES = {"menstrual_phase", "follicular_phase",
                "ovulatory_phase", "luteal_phase"}
VALID_ASTRO  = {"aries","taurus","gemini","cancer","leo","virgo",
                "libra","scorpio","sagittarius","capricorn","aquarius","pisces"}


def _load() -> dict:
    if PROFILES_PATH.exists():
        try:
            with open(PROFILES_PATH, encoding="utf-8") as _f:
                return json.load(_f)
        except Exception:
            return {}
    return {}


def _save(data: dict) -> None:
    PROFILES_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def create_profile(
    user_id: str,
    diet: str = "vegetarian",
    goal: str = "default",
    cuisines: list = None,
    allergies: list = None,
    disliked: list = None,
    cycle_phase: str = None,
    astro_sign: str = None,
    max_calories: int = None,
    min_protein: float = None,
) -> dict:
    """Crée ou met à jour le profil culinaire d'un utilisateur."""
    if diet not in VALID_DIETS:
        return {"error": f"Diet invalide. Valides : {sorted(VALID_DIETS)}"}
    if goal not in VALID_GOALS:
        return {"error": f"Goal invalide. Valides : {sorted(VALID_GOALS)}"}
    if cycle_phase and cycle_phase not in VALID_PHASES:
        return {"error": f"Phase invalide. Valides : {sorted(VALID_PHASES)}"}
    if astro_sign and astro_sign.lower() not in VALID_ASTRO:
        return {"error": f"Signe invalide. Valides : {sorted(VALID_ASTRO)}"}

    profiles = _load()
    now      = datetime.utcnow().isoformat()
    existing = profiles.get(user_id, {})

    profile = {
        "user_id":      user_id,
        "diet":         diet,
        "goal":         goal,
        "cuisines":     cuisines  or [],
        "allergies":    allergies or [],
        "disliked":     disliked  or [],
        "cycle_phase":  cycle_phase,
        "astro_sign":   astro_sign.lower() if astro_sign else None,
        "max_calories": max_calories,
        "min_protein":  min_protein,
        "created_at":   existing.get("created_at", now),
        "updated_at":   now,
    }

    profiles[user_id] = profile
    _save(profiles)
    return {"status": "saved", "profile": profile}


def get_profile(user_id: str) -> dict:
    return _load().get(user_id)


def update_profile(user_id: str, **kwargs) -> dict:
    profile = get_profile(user_id)
    if not profile:
        return {"error": "Profil introuvable."}
    allowed = {"diet","goal","cuisines","allergies","disliked",
               "cycle_phase","astro_sign","max_calories","min_protein"}
    for k, v in kwargs.items():
        if k in allowed:
            profile[k] = v
    profile["updated_at"] = datetime.utcnow().isoformat()
    profiles = _load()
    profiles[user_id] = profile
    _save(profiles)
    return {"status": "updated", "profile": profile}


def delete_profile(user_id: str) -> dict:
    profiles = _load()
    if user_id not in profiles:
        return {"error": "Profil introuvable."}
    del profiles[user_id]
    _save(profiles)
    return {"status": "deleted"}


def profile_to_search_params(user_id: str) -> dict:
    """Convertit un profil en paramètres de recherche pour search_engine_v2."""
    profile = get_profile(user_id)
    if not profile:
        return {}
    goal_map = {"health":"health_focus","budget":"budget",
                "discovery":"discovery","comfort":"comfort","default":"default"}
    return {
        "diet":          profile.get("diet") if profile.get("diet") != "all" else None,
        "max_calories":  profile.get("max_calories"),
        "min_protein":   profile.get("min_protein"),
        "adaptive_profile": goal_map.get(profile.get("goal","default"),"default"),
        "exclude_ingredients": list(set(
            profile.get("allergies",[]) + profile.get("disliked",[])
        )),
        "preferred_cuisines": profile.get("cuisines",[]),
        "cycle_phase":   profile.get("cycle_phase"),
        "astro_sign":    profile.get("astro_sign"),
    }
