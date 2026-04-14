"""
user_service.py — Gestion des comptes B2C.

Corrections P0+P1 :
  P0 : threading.RLock sur toutes les opérations read-modify-write JSON.
  P1.2 : is_db_available() au lieu de _USE_DB capturé à l'import.
         Le fallback JSON est toujours défini (indépendamment du mode DB),
         ce qui permet un basculement transparent si la DB tombe en cours
         de route sans nécessiter de redémarrage.
"""
import json
import logging
import os
import re
import tempfile
import threading
from pathlib import Path

from backend.core.security import hash_password, verify_password

logger = logging.getLogger(__name__)

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

# ── Tentative import DB — ne bloque jamais le démarrage ───────────────────────
_DB_IMPORT_OK = False
try:
    from backend.db.session import db_session, is_db_available
    from backend.db.repositories import UserRepository
    _DB_IMPORT_OK = True
    logger.info("user_service : imports DB OK")
except Exception as e:
    logger.warning("user_service : import DB impossible (%s) — JSON uniquement", e)


def _use_db() -> bool:
    """
    Vérifie la disponibilité DB à l'instant de l'appel.
    P1.2 FIX : ne capture plus DB_AVAILABLE à l'import.
    """
    if not _DB_IMPORT_OK:
        return False
    return is_db_available()


# ── Fallback JSON — toujours disponible ───────────────────────────────────────
# Défini inconditionnellement : sert de fallback si la DB est indisponible
# au moment d'un appel, même si elle était disponible au démarrage.

_FILE = Path(__file__).resolve().parent.parent / "data" / "user_profiles" / "users.json"

# P0 FIX : RLock sur les opérations read-modify-write
_json_lock = threading.RLock()


def _load() -> dict:
    """Lecture brute. Appeler sous _json_lock."""
    if not _FILE.exists():
        return {}
    try:
        with open(_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        logger.error("Lecture users.json : %s", e)
        return {}


def _save(data: dict) -> None:
    """Écriture atomique (tempfile + os.replace). Appeler sous _json_lock."""
    _FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=_FILE.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_path, _FILE)
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise


# ── API publique ───────────────────────────────────────────────────────────────

def create_user(email: str, password: str) -> None:
    """Crée un utilisateur. Lève ValueError si email invalide ou déjà existant."""
    if not _EMAIL_RE.match(email):
        raise ValueError(f"Format email invalide : {email}")

    if _use_db():
        with db_session() as db:
            UserRepository(db).create(email, hash_password(password))
    else:
        with _json_lock:
            users = _load()
            if email in users:
                raise ValueError(f"L'email {email} est déjà enregistré")
            users[email] = {"password": hash_password(password)}
            _save(users)

    logger.info("Compte créé : %s", email)


def authenticate(email: str, password: str) -> dict | None:
    """Vérifie les identifiants. Retourne {email} ou None."""
    if _use_db():
        with db_session() as db:
            user = UserRepository(db).get_by_email(email)
            if not user or not user.is_active:
                return None
            if not verify_password(password, user.password_hash):
                return None
            logger.info("Authentification réussie : %s", email)
            return {"email": email}
    else:
        with _json_lock:
            users = _load()
        user = users.get(email)
        if not user or not verify_password(password, user["password"]):
            return None
        logger.info("Authentification réussie (JSON) : %s", email)
        return {"email": email}


def delete_user(email: str) -> bool:
    """Supprime le compte. Retourne True si supprimé."""
    if _use_db():
        with db_session() as db:
            deleted = UserRepository(db).delete(email)
            if deleted:
                logger.info("Compte supprimé : %s", email)
            return deleted
    else:
        with _json_lock:
            users = _load()
            if email not in users:
                return False
            del users[email]
            _save(users)
        logger.info("Compte supprimé (JSON) : %s", email)
        return True


def update_password(email: str, new_password: str) -> bool:
    """
    Met à jour le mot de passe. Utilisé par reset-password.
    Retourne True si la mise à jour a eu lieu.
    """
    if _use_db():
        # La mise à jour via DB se fait via UserRepository dans auth.py
        raise RuntimeError("update_password JSON appelé en mode DB — utiliser UserRepository")

    with _json_lock:
        users = _load()
        if email not in users:
            return False
        users[email]["password"] = hash_password(new_password)
        _save(users)

    logger.info("Mot de passe mis à jour (JSON) : %s", email)
    return True
