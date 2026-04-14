"""
profile_service.py — Gestion des profils utilisateurs B2C.
Migré de JSON vers PostgreSQL via UserProfileRepository.
Fallback transparent sur JSON si BDD indisponible.
"""
import logging

logger = logging.getLogger(__name__)

# ── Connexion DB — singleton partagé avec user_service ────────────────────────
try:
    from backend.db.session      import db_session, DB_AVAILABLE
    from backend.db.repositories import UserProfileRepository
    _USE_DB = DB_AVAILABLE
    if _USE_DB:
        logger.info("profile_service : mode base de données")
    else:
        logger.warning("profile_service : BDD indisponible — fallback JSON")
except Exception as e:
    logger.warning("profile_service : import BDD impossible (%s) — fallback JSON", e)
    _USE_DB = False

# Whitelist — identique dans les deux backends
ALLOWED_FIELDS = frozenset({
    "diet", "allergies", "budget", "servings", "goal",
    "cycle_phase", "health_goal",
    "liked_ingredients", "disliked_ingredients",
})

if not _USE_DB:
    import json, os, tempfile
    from pathlib import Path
    _FILE = Path(__file__).resolve().parent.parent / "data" / "user_profiles" / "user_profiles.json"

    def _load() -> dict:
        if not _FILE.exists():
            return {}
        try:
            with open(_FILE, encoding="utf-8") as _fh:
                return json.load(_fh)
        except Exception as e:
            logger.error("Lecture user_profiles.json : %s", e)
            return {}

    def _save(data: dict) -> None:
        tmp_fd, tmp_path = tempfile.mkstemp(dir=_FILE.parent, suffix=".tmp")
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, _FILE)
        except Exception:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise


def set_profile(email: str, updates: dict) -> dict:
    """
    Met à jour le profil par merge partiel.
    Seuls les champs ALLOWED_FIELDS sont acceptés.
    Retourne le profil complet après mise à jour.
    """
    if _USE_DB:
        with db_session() as db:
            result = UserProfileRepository(db).upsert(email, updates)
            logger.debug("Profil DB mis à jour : %s", email)
            return result
    else:
        safe     = {k: v for k, v in updates.items() if k in ALLOWED_FIELDS}
        profiles = _load()
        existing = profiles.get(email, {})
        existing.update(safe)
        profiles[email] = existing
        _save(profiles)
        logger.debug("Profil JSON mis à jour : %s → %s", email, list(safe.keys()))
        return existing


def get_profile(email: str) -> dict:
    """Retourne le profil ou {} s'il n'existe pas."""
    if _USE_DB:
        with db_session() as db:
            return UserProfileRepository(db).get_as_dict(email)
    else:
        return _load().get(email, {})


def delete_profile(email: str) -> bool:
    """Supprime le profil. Retourne True si supprimé."""
    if _USE_DB:
        with db_session() as db:
            return UserProfileRepository(db).delete(email)
    else:
        profiles = _load()
        if email not in profiles:
            return False
        del profiles[email]
        _save(profiles)
        return True