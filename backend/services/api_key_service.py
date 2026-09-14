"""
backend/services/api_key_service.py — Service B2B unifié.

Remplace la logique JSON dispersée dans auth_middleware.py.
Utilise ApiUserRepository + ApiKeyRepository + QuotaRepository (DB).

Même pattern que user_service.py :
  - DB-first quand disponible (is_db_available())
  - Fallback JSON si DB indisponible (fichiers product/)
  - Jamais bloquant au démarrage

Fonctions exposées :
  validate_key(raw_key)          → dict | None
  generate_key(email, plan)      → str (raw key, une seule fois)
  revoke_key(raw_key)            → bool
  get_stats()                    → dict
"""
import hashlib
import json
import logging
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Tentative import DB ───────────────────────────────────────────────────────

_DB_OK = False
try:
    from backend.db.session import db_session, is_db_available
    from backend.db.repositories import ApiUserRepository, ApiKeyRepository, QuotaRepository
    _DB_OK = True
except Exception as exc:
    logger.warning("api_key_service: import DB impossible (%s) — JSON uniquement", exc)


def _use_db() -> bool:
    return _DB_OK and is_db_available()


# ── Fallback JSON (product/ — vide en dev, utilisé en mode dégradé) ───────────

_PRODUCT = Path(__file__).resolve().parent.parent / "data" / "product"
_KEYS_FILE  = _PRODUCT / "api_keys.json"
_USERS_FILE = _PRODUCT / "users.json"

def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        logger.error("_load_json : erreur ignorée (repli)", exc_info=True)
        return default


# ── API publique ──────────────────────────────────────────────────────────────

def validate_key(raw_key: str) -> dict | None:
    """
    Valide une clé API brute.

    Retourne un dict {email, plan, user_id, key_hash} ou None si invalide/quotas dépassés.
    Lève HTTPException 429 si quota dépassé (délégué à l'appelant pour le message HTTP).
    """
    if not raw_key:
        return None

    if _use_db():
        try:
            with db_session() as db:
                api_key = ApiKeyRepository(db).lookup(raw_key)
                if not api_key:
                    logger.debug("api_key_service: clé inconnue (hash=%s…)", _sha256(raw_key)[:8])
                    return None
                if not api_key.is_active:
                    return None

                # Vérification expiration
                if api_key.expires_at:
                    from datetime import datetime, timezone
                    if datetime.now(timezone.utc) > api_key.expires_at:
                        logger.info("api_key_service: clé expirée (hash=%s…)", api_key.key_hash[:8])
                        return None

                # Quota
                allowed, used, limit = QuotaRepository(db).check_and_increment(
                    raw_key, api_key.api_user.plan
                )
                if not allowed:
                    from fastapi import HTTPException
                    raise HTTPException(
                        status_code=429,
                        detail=f"Quota journalier atteint ({used}/{limit}). Passez au plan supérieur.",
                        headers={"X-RateLimit-Limit": str(limit), "X-RateLimit-Used": str(used)},
                    )

                api_user = api_key.api_user
                return {
                    "user_id":   api_user.user_id,
                    "email":     api_user.email,
                    "plan":      api_user.plan,
                    "is_active": api_user.is_active,
                    "key_hash":  api_key.key_hash,
                }
        except Exception as exc:
            # Ne pas propager les HTTPException du quota
            from fastapi import HTTPException
            if isinstance(exc, HTTPException):
                raise
            logger.error("api_key_service: erreur DB validate_key (%s)", exc)
            return None

    # Fallback JSON (mode dégradé)
    keys  = _load_json(_KEYS_FILE,  {})
    users = _load_json(_USERS_FILE, {})
    h = _sha256(raw_key)
    key_data = keys.get(h)
    if not key_data or not key_data.get("active", True):
        return None
    user_d = users.get(key_data.get("user_id", ""), {})
    return {
        "user_id":   key_data.get("user_id"),
        "email":     user_d.get("email", ""),
        "plan":      user_d.get("plan", "free"),
        "is_active": True,
        "key_hash":  h,
    } if user_d else None


def generate_key(email: str, plan: str = "free") -> str:
    """
    Crée un compte B2B (si absent) et génère une nouvelle clé API.
    Retourne la clé brute — affichée une seule fois, non stockée.
    """
    if _use_db():
        with db_session() as db:
            api_user_repo = ApiUserRepository(db)
            api_key_repo  = ApiKeyRepository(db)

            user = api_user_repo.get_by_email(email)
            if not user:
                user = api_user_repo.create(email, plan)

            raw_key, _ = api_key_repo.generate(user.user_id)
            logger.info("api_key_service: clé générée pour %s (plan=%s)", email, plan)
            return raw_key

    # Fallback JSON
    import secrets
    raw_key = secrets.token_hex(32)
    h = _sha256(raw_key)
    _PRODUCT.mkdir(parents=True, exist_ok=True)

    import uuid
    users = _load_json(_USERS_FILE, {})
    user_id = str(uuid.uuid4())
    users[user_id] = {"email": email, "plan": plan}
    _USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")

    keys = _load_json(_KEYS_FILE, {})
    keys[h] = {"user_id": user_id, "active": True}
    _KEYS_FILE.write_text(json.dumps(keys, ensure_ascii=False, indent=2), encoding="utf-8")

    logger.info("api_key_service: clé générée (JSON) pour %s", email)
    return raw_key


def revoke_key(raw_key: str) -> bool:
    """Révoque une clé API. Retourne True si révoquée."""
    if _use_db():
        with db_session() as db:
            return ApiKeyRepository(db).revoke(raw_key)

    # Fallback JSON
    keys = _load_json(_KEYS_FILE, {})
    h = _sha256(raw_key)
    if h not in keys:
        return False
    keys[h]["active"] = False
    _KEYS_FILE.write_text(json.dumps(keys, ensure_ascii=False, indent=2), encoding="utf-8")
    return True


def get_stats() -> dict:
    """Stats globales B2B — utilisées par /admin/quota."""
    if _use_db():
        with db_session() as db:
            from backend.db.models import ApiUser, ApiKey, DailyQuota
            from sqlalchemy import func
            total_users = db.query(ApiUser).count()
            total_keys  = db.query(ApiKey).count()
            active_keys = db.query(ApiKey).filter(ApiKey.is_active.is_(True)).count()
            today_calls = (
                db.query(func.sum(DailyQuota.count))
                .filter(DailyQuota.quota_date == date.today())
                .scalar() or 0
            )
            plan_dist = {}
            for (plan,), cnt in db.query(ApiUser.plan, func.count()).group_by(ApiUser.plan).all():
                plan_dist[plan] = cnt
            return {
                "total_users":       total_users,
                "total_keys":        total_keys,
                "active_keys":       active_keys,
                "plan_distribution": plan_dist,
                "calls_today":       today_calls,
            }

    # Fallback JSON
    users = _load_json(_USERS_FILE, {})
    keys  = _load_json(_KEYS_FILE,  {})
    plan_dist = {}
    for u in users.values():
        p = u.get("plan", "free")
        plan_dist[p] = plan_dist.get(p, 0) + 1
    return {
        "total_users":       len(users),
        "total_keys":        len(keys),
        "active_keys":       sum(1 for k in keys.values() if k.get("active", True)),
        "plan_distribution": plan_dist,
        "calls_today":       0,
    }


__all__ = ["validate_key", "generate_key", "revoke_key", "get_stats"]
