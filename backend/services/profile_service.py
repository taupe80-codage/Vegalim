"""
profile_service.py — Gestion des profils utilisateurs B2C.
Migré de JSON vers PostgreSQL via UserProfileRepository.
Fallback transparent sur JSON si BDD indisponible.
"""
import logging

logger = logging.getLogger(__name__)

# ── Connexion DB — singleton partagé avec user_service ────────────────────────
# P1.2 FIX : ne pas capturer DB_AVAILABLE (booléen) à l'import —
# sa valeur est toujours False au moment où ce module est chargé en Docker
# (le lifespan FastAPI n'a pas encore appelé refresh_db_availability()).
# Utiliser is_db_available() à chaque appel pour lire la valeur courante.
_DB_IMPORTS_OK = False
try:
    from backend.db.session      import db_session, is_db_available
    from backend.db.repositories import UserProfileRepository
    _DB_IMPORTS_OK = True
    logger.info("profile_service : imports DB OK — disponibilité vérifiée à chaque appel")
except Exception as e:
    logger.warning("profile_service : import BDD impossible (%s) — fallback JSON permanent", e)

def _use_db() -> bool:
    """Retourne True si la DB est disponible à l'instant de l'appel."""
    return _DB_IMPORTS_OK and is_db_available()

# Whitelist — identique dans les deux backends
ALLOWED_FIELDS = frozenset({
    "diet", "allergies", "budget", "servings", "goal",
    "cycle_phase", "health_goal",
    "liked_ingredients", "disliked_ingredients",
})

# Fallback JSON — toujours importé, utilisé si _use_db() retourne False
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
    if _use_db():
        with db_session() as db:
            result = UserProfileRepository(db).upsert(email, updates)
            logger.debug("Profil DB mis à jour : %s", email)
            return result
    else:
        safe     = {k: v for k, v in updates.items() if k in ALLOWED_FIELDS}
        # Normaliser le diet vers la clé canonique avant stockage
        # (ex: "sans_gluten" → "gluten_free") pour cohérence avec le mode DB.
        if "diet" in safe and safe["diet"]:
            try:
                from backend.core.validators import normalize_diet
                safe["diet"] = normalize_diet(safe["diet"])
            except Exception as exc:
                logger.warning("profile_service: normalize_diet échoué (%s) — stockage brut", exc)
        profiles = _load()
        existing = profiles.get(email, {})
        existing.update(safe)
        profiles[email] = existing
        _save(profiles)
        logger.debug("Profil JSON mis à jour : %s → %s", email, list(safe.keys()))
        return existing


def get_profile(email: str) -> dict:
    """Retourne le profil ou {} s'il n'existe pas."""
    if _use_db():
        with db_session() as db:
            return UserProfileRepository(db).get_as_dict(email)
    else:
        return _load().get(email, {})


def delete_profile(email: str) -> bool:
    """Supprime le profil. Retourne True si supprimé."""
    if _use_db():
        with db_session() as db:
            return UserProfileRepository(db).delete(email)
    else:
        profiles = _load()
        if email not in profiles:
            return False
        del profiles[email]
        _save(profiles)
        return True