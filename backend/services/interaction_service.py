"""
backend/services/interaction_service.py — Façade learning pour les routes profil.

Rôle : exposer les 3 fonctions attendues par profile.py en déléguant
       directement à reco_engine.learning, qui contient toute la logique
       (DB → JSON fallback, extraction préférences, stats).

Fonctions exposées :
  - save_interaction(email, recipe_id, action, score_shown, profile_used)
  - get_user_stats(email)
  - load_history(email)

Aucune logique métier ici — tout est dans reco_engine/learning.py.
"""
from backend.engine.reco_engine.learning import (
    save_interaction,   # noqa: F401  (re-export)
    get_user_stats,     # noqa: F401
    load_history,       # noqa: F401
)

__all__ = ["save_interaction", "get_user_stats", "load_history"]
