"""
reco_engine/learning.py — Personnalisation du scoring par apprentissage des préférences.

Principe : à partir de l'historique d'interactions (likes, skips, vues),
construire un profil de préférences implicites et appliquer un bonus/malus
sur le score final de recommandation.

Dimensions apprises :
  - cuisines_favorites     : cuisines likées > cuisines skippées
  - techniques_preferees   : techniques des recettes likées
  - difficulty_comfort     : niveau de difficulté typique des likes
  - time_window_minutes    : durée typique des recettes likées
  - diet_preference        : flags diet les plus fréquents dans les likes

Sources de données (par ordre de priorité) :
  1. RecipeHistoryRepository (DB SQLAlchemy) — si disponible
  2. Fichier JSON local par utilisateur     — fallback léger

Intégration :
  - scoring_service.score_recipe()  → appelle apply_learning_bonus()
  - advanced_scoring.recommend()    → appelle rank_with_learning()
  - Route POST /recettes/recommend  → personnalisation transparente

Limitations volontaires :
  - Minimum 5 likes pour activer la personnalisation (évite le sur-ajustement)
  - Bonus max : ±2.0 points sur le score final (CDC_03c = 10 pts)
  - Pas de filtrage : on booste, on ne supprime pas
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from backend.engine.config import DATA_ROOT

logger = logging.getLogger(__name__)

# ── Constantes (importées depuis config pour cohérence projet) ────────────────

from backend.engine.config import MIN_LIKES_TO_ACTIVATE, MAX_LEARNING_BONUS as MAX_BONUS

# Bonus par dimension (locaux — usage interne uniquement)
BONUS_CUISINE    = 0.8
BONUS_TECHNIQUE  = 0.4
BONUS_DIFFICULTY = 0.3
BONUS_TIME       = 0.3
MALUS_DISLIKED   = -1.5
_HISTORY_DIR = DATA_ROOT.parent / "users" / "history"


# ── Chargement de l'historique ────────────────────────────────────────────────

def _load_history_from_db(email: str) -> dict:
    """
    Charge l'historique depuis RecipeHistoryRepository.
    Retourne un dict normalisé ou {} si DB indisponible.
    """
    # Utilisation de db_session() (context manager) plutot que next(get_db()).
    # next(get_db()) ne declenche jamais le finally:db.close() du generateur
    # FastAPI hors injection de dependance -> fuite de connexion sous charge.
    try:
        from backend.db.session import db_session
        from backend.db.repositories import RecipeHistoryRepository
        with db_session() as db:
            repo = RecipeHistoryRepository(db)
            recent = repo.get_recent(email, limit=200)
            liked    = set(repo.get_liked_recipe_ids(email))
            disliked = set(repo.get_disliked_recipe_ids(email))
            viewed   = {e.recipe_id for e in recent}
            return {
                "liked":    liked,
                "disliked": disliked,
                "viewed":   viewed,
                "raw":      [(e.recipe_id, e.action) for e in recent],
            }
    except Exception as e:
        logger.debug("DB indisponible pour learning_engine (%s) — fallback JSON", e)
        return {}


def _load_history_from_json(email: str) -> dict:
    """
    Charge l'historique depuis un fichier JSON local (fallback léger).
    Format : { liked: [ids], disliked: [ids], viewed: [ids] }
    """
    safe_email = email.replace("@", "_at_").replace(".", "_")
    path = _HISTORY_DIR / f"{safe_email}.json"
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return {
            "liked":    set(data.get("liked", [])),
            "disliked": set(data.get("disliked", [])),
            "viewed":   set(data.get("viewed", [])),
            "raw":      data.get("raw", []),
        }
    except Exception as e:
        logger.warning("Erreur chargement historique JSON %s : %s", email, e)
        return {}


def load_history(email: str) -> dict:
    """
    Charge l'historique utilisateur (DB → JSON fallback).

    Returns:
        {
          "liked":    set[int],   # recipe_ids likés
          "disliked": set[int],   # recipe_ids dislikés
          "viewed":   set[int],   # recipe_ids vus
          "raw":      list        # liste brute (recipe_id, action)
        }
    """
    history = _load_history_from_db(email)
    if not history:
        history = _load_history_from_json(email)
    return history or {"liked": set(), "disliked": set(), "viewed": set(), "raw": []}


def save_interaction(email: str, recipe_id: int, action: str,
                     score_shown: Optional[float] = None,
                     profile_used: Optional[str] = None) -> bool:
    """
    Enregistre une interaction utilisateur.

    Action : "view" | "like" | "dislike" | "plan" | "cook" | "skip"

    Essaie d'abord la DB, puis le fichier JSON en fallback.
    """
    # Tentative DB : db_session() garantit db.close() via finally,
    # meme en cas d'exception apres le commit.
    # db_session() appelle aussi db.commit() automatiquement en sortie normale.
    try:
        from backend.db.session import db_session
        from backend.db.repositories import RecipeHistoryRepository
        with db_session() as db:
            RecipeHistoryRepository(db).record(
                user_email   = email,
                recipe_id    = recipe_id,
                action       = action,
                score_shown  = int(score_shown * 10) if score_shown else None,
                profile_used = profile_used,
            )
        return True
    except Exception:
        pass  # Fallback JSON ci-dessous

    # Fallback JSON
    try:
        _HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        safe_email = email.replace("@", "_at_").replace(".", "_")
        path = _HISTORY_DIR / f"{safe_email}.json"
        data = {"liked": [], "disliked": [], "viewed": [], "raw": []}
        if path.exists():
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        if action == "like"    and recipe_id not in data["liked"]:
            data["liked"].append(recipe_id)
        if action == "dislike" and recipe_id not in data["disliked"]:
            data["disliked"].append(recipe_id)
        data["viewed"] = list(set(data.get("viewed", []) + [recipe_id]))[-500:]
        data["raw"]    = (data.get("raw", []) + [[recipe_id, action]])[-200:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error("save_interaction erreur : %s", e)
        return False


# ── Extraction des préférences ────────────────────────────────────────────────

def _get_liked_recipes(liked_ids: set, all_recipes: list) -> list:
    """Retourne les dicts recette pour les ids likés."""
    id_map = {r["id"]: r for r in all_recipes}
    return [id_map[i] for i in liked_ids if i in id_map]


def extract_preferences(email: str) -> dict:
    """
    Déduit les préférences implicites depuis l'historique.

    Returns:
        {
          "active":              bool   — suffisamment de data pour personnaliser
          "liked_count":         int
          "cuisines_favorite":   set[str]  — cuisines > médiane
          "techniques_preferred":set[str]  — techniques fréquentes dans likes
          "difficulty_comfort":  int | None — 1/2/3
          "time_window":         tuple[int,int] | None — (min, max) minutes
          "disliked_ids":        set[int]
        }
    """
    from backend.core.data_io import load_recipes
    history      = load_history(email)
    liked_ids    = history.get("liked", set())
    disliked_ids = history.get("disliked", set())

    prefs = {
        "active":               False,
        "liked_count":          len(liked_ids),
        "cuisines_favorite":    set(),
        "techniques_preferred": set(),
        "difficulty_comfort":   None,
        "time_window":          None,
        "disliked_ids":         disliked_ids,
    }

    if len(liked_ids) < MIN_LIKES_TO_ACTIVATE:
        return prefs

    all_recipes   = load_recipes()
    liked_recipes = _get_liked_recipes(liked_ids, all_recipes)

    if not liked_recipes:
        return prefs

    prefs["active"] = True

    # Cuisines
    cuisine_count: dict[str, int] = {}
    for r in liked_recipes:
        cuisine = (r.get("iconic_status") or {}).get("cuisine_origin", "") or \
                  r.get("cuisine_origin", "")
        if cuisine:
            cuisine_count[cuisine] = cuisine_count.get(cuisine, 0) + 1
    if cuisine_count:
        median = sorted(cuisine_count.values())[len(cuisine_count) // 2]
        prefs["cuisines_favorite"] = {c for c, n in cuisine_count.items() if n >= median}

    # Techniques
    tech_count: dict[str, int] = {}
    for r in liked_recipes:
        for t in (r.get("technique") or []):
            tech_count[t] = tech_count.get(t, 0) + 1
    if tech_count:
        top_n = max(1, len(tech_count) // 3)
        prefs["techniques_preferred"] = {
            t for t, n in sorted(tech_count.items(), key=lambda x: -x[1])[:top_n]
        }

    # Difficulté confortable (mode)
    diffs = [r.get("difficulty") for r in liked_recipes if r.get("difficulty")]
    if diffs:
        from collections import Counter
        prefs["difficulty_comfort"] = Counter(diffs).most_common(1)[0][0]

    # Fenêtre de temps (25e–75e percentile)
    times = sorted([r.get("timing", {}).get("total_min") or 0 for r in liked_recipes if r.get("timing", {}).get("total_min")])
    if len(times) >= 3:
        lo = times[len(times) // 4]
        hi = times[3 * len(times) // 4]
        prefs["time_window"] = (max(0, lo - 10), hi + 10)

    return prefs


# ── Application du bonus ──────────────────────────────────────────────────────

def compute_learning_bonus(recipe: dict, prefs: dict) -> float:
    """
    Calcule le bonus de personnalisation pour une recette.

    Returns:
        float dans [-MAX_BONUS, +MAX_BONUS]
    """
    if not prefs.get("active"):
        return 0.0

    rid = recipe.get("id")
    bonus = 0.0

    # Malus dislike immédiat
    if rid in prefs.get("disliked_ids", set()):
        return MALUS_DISLIKED

    # Cuisine favorite
    cuisine = (recipe.get("iconic_status") or {}).get("cuisine_origin", "") or \
              recipe.get("cuisine_origin", "")
    if cuisine and cuisine in prefs.get("cuisines_favorite", set()):
        bonus += BONUS_CUISINE

    # Technique préférée
    recipe_techs = set(recipe.get("technique") or [])
    if recipe_techs & prefs.get("techniques_preferred", set()):
        bonus += BONUS_TECHNIQUE

    # Difficulté confortable
    diff = recipe.get("difficulty")
    if diff and diff == prefs.get("difficulty_comfort"):
        bonus += BONUS_DIFFICULTY

    # Fenêtre de temps
    t = recipe.get("timing", {}).get("total_min")
    tw = prefs.get("time_window")
    if t and tw and tw[0] <= t <= tw[1]:
        bonus += BONUS_TIME

    return round(max(-MAX_BONUS, min(MAX_BONUS, bonus)), 3)


def apply_learning_bonus(recipe: dict, base_score: float,
                         prefs: dict) -> tuple[float, float]:
    """
    Applique le bonus sur le score de base.

    Returns:
        (final_score, bonus_applied)
    """
    bonus      = compute_learning_bonus(recipe, prefs)
    final      = round(max(0.0, min(10.0, base_score + bonus)), 2)
    return final, bonus


# ── API de haut niveau ────────────────────────────────────────────────────────

def rank_with_learning(recipes: list[dict], email: str,
                       score_field: str = "final_score") -> list[dict]:
    """
    Réordonne une liste de recettes scorées en appliquant les préférences
    apprises de l'utilisateur.

    Args:
        recipes     : liste de recettes déjà scorées (contiennent score_field)
        email       : email utilisateur
        score_field : nom du champ score à utiliser comme base

    Returns:
        Liste triée par score personnalisé décroissant.
        Chaque recette reçoit `_learning_bonus` et `_personalized_score`.
    """
    if not email:
        return recipes

    prefs = extract_preferences(email)

    for recipe in recipes:
        base  = float(recipe.get(score_field, 0))
        final, bonus = apply_learning_bonus(recipe, base, prefs)
        recipe["_learning_bonus"]     = bonus
        recipe["_personalized_score"] = final

    recipes.sort(key=lambda r: r.get("_personalized_score", 0), reverse=True)
    return recipes


def get_user_stats(email: str) -> dict:
    """
    Retourne les statistiques d'apprentissage pour un utilisateur.

    Utile pour le debug et l'affichage dans le profil utilisateur.
    """
    history = load_history(email)
    prefs   = extract_preferences(email)

    return {
        "email":              email,
        "liked_count":        len(history.get("liked", set())),
        "disliked_count":     len(history.get("disliked", set())),
        "viewed_count":       len(history.get("viewed", set())),
        "personalization_active": prefs["active"],
        "min_likes_required": MIN_LIKES_TO_ACTIVATE,
        "preferences":        {
            "cuisines_favorite":    list(prefs.get("cuisines_favorite", set())),
            "techniques_preferred": list(prefs.get("techniques_preferred", set())),
            "difficulty_comfort":   prefs.get("difficulty_comfort"),
            "time_window":          prefs.get("time_window"),
        } if prefs["active"] else {},
    }
