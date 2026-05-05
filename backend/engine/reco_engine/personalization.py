"""
personalization.py — Résolution du profil et personnalisation par apprentissage.

Responsabilité UNIQUE : répondre à la question
    "Qui est cet utilisateur et quelles sont ses préférences ?"

Ce module ne calcule PAS de score — il enrichit le contexte
et réordonne les résultats déjà scorés.

API :
    resolve_user_context(email, diet_override) → UserContext
    apply_learning(recipes, context)           → list[dict]  (réordonné)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# ── UserContext ───────────────────────────────────────────────────────────────

@dataclass
class UserContext:
    """
    Contexte utilisateur résolu, passé à toutes les étapes du pipeline.

    Produit par resolve_user_context() — consommé par scoring et orchestrator.
    """
    email:            str | None = None
    profile:          dict       = field(default_factory=dict)
    diet:             str | None = None
    profile_used:     str        = "default"
    effective_profile: dict      = field(default_factory=dict)

    # Flags de capacités (activent/désactivent des features du pipeline)
    has_learning:     bool       = False   # True si assez de likes (≥5)
    has_cycle:        bool       = False   # True si cycle_phase renseignée


# ── Résolution du profil ──────────────────────────────────────────────────────

def resolve_user_context(
    email:         str | None,
    diet_override: str | None = None,
) -> UserContext:
    """
    Résout le contexte complet d'un utilisateur à partir de son email.

    Étapes :
        1. Charge le profil depuis profile_service (DB → fallback JSON)
        2. Fusionne le diet_override avec le profil
        3. Détermine le profil adaptatif (scoring_service.resolve_profile)
        4. Détecte les capacités (learning actif, cycle renseigné)

    Returns:
        UserContext prêt à être consommé par le pipeline.
    """
    if not email:
        return UserContext(diet=diet_override, effective_profile={"diet": diet_override} if diet_override else {})

    # 1. Chargement profil
    try:
        from backend.services.profile_service import get_profile
        profile = get_profile(email) or {}
    except Exception as e:
        logger.debug("personalization: profil indisponible pour %s — %s", email, e)
        profile = {}

    # 2. Résolution du régime (override > profil)
    diet = diet_override or profile.get("diet")
    effective_profile = {**profile, "diet": diet} if diet else dict(profile)

    # 3. Profil adaptatif
    try:
        from backend.services.scoring_service import resolve_profile
        profile_used = resolve_profile("default", effective_profile)
    except Exception:
        profile_used = "default"

    # 4. Capacités
    has_learning = _check_learning_eligibility(email)
    has_cycle    = bool(profile.get("cycle_phase"))

    return UserContext(
        email             = email,
        profile           = profile,
        diet              = diet,
        profile_used      = profile_used,
        effective_profile = effective_profile,
        has_learning      = has_learning,
        has_cycle         = has_cycle,
    )


def _check_learning_eligibility(email: str) -> bool:
    """
    Vérifie si l'utilisateur a assez de likes pour activer le learning.
    Ne lève jamais d'exception — retourne False en cas d'erreur.
    """
    try:
        from backend.engine.config import MIN_LIKES_TO_ACTIVATE
        from backend.db.session import db_session
        from backend.db.repositories import RecipeHistoryRepository
        with db_session() as db:
            repo = RecipeHistoryRepository(db)
            return len(repo.get_liked_recipe_ids(email)) >= MIN_LIKES_TO_ACTIVATE
    except Exception:
        return False


# ── Personnalisation par apprentissage ────────────────────────────────────────

def apply_learning(recipes: list[dict], context: UserContext) -> list[dict]:
    """
    Réordonne les recettes selon les préférences apprises de l'utilisateur.

    Ne modifie les scores QUE si context.has_learning est True.
    En cas d'erreur, retourne la liste originale sans exception.

    Args:
        recipes : liste de recettes déjà scorées (champ final_score requis)
        context : contexte utilisateur résolu

    Returns:
        Liste réordonnée (ou inchangée si learning indisponible).
    """
    if not context.email or not context.has_learning:
        return recipes

    try:
        from backend.engine.learning_engine import rank_with_learning
        return rank_with_learning(recipes, context.email, score_field="final_score")
    except Exception as e:
        logger.debug("personalization: learning_engine indisponible — %s", e)
        return recipes


# ── Exclusions historique ─────────────────────────────────────────────────────

def get_excluded_ids(context: UserContext) -> list[int]:
    """
    Retourne les ids de recettes à exclure pour cet utilisateur.

    Exclut les recettes avec action='dislike' dans l'historique.
    Retourne [] si pas d'email ou DB indisponible.
    """
    if not context.email:
        return []
    try:
        from backend.db.session import db_session
        from backend.db.repositories import RecipeHistoryRepository
        with db_session() as db:
            repo = RecipeHistoryRepository(db)
            return repo.get_disliked_recipe_ids(context.email)
    except Exception as e:
        logger.debug("personalization: impossible de charger les exclusions — %s", e)
        return []
