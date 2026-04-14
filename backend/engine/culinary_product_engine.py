"""
Culinary Product Engine
========================
Gestion des utilisateurs, clés API et analytics.
Stockage fichier JSON (production-ready pour migration SQLite/Postgres).

Routes principales :
  POST /create_user       → crée un compte + génère la première clé API
  GET  /get_user          → infos utilisateur + quota courant
  POST /generate_api_key  → génère une nouvelle clé pour un user existant
  GET  /validate_api_key  → vérifie si une clé est valide (public)
  POST /upgrade_plan      → change le plan d'un utilisateur
"""

import json
import uuid
import re
import hashlib
from datetime import datetime, date, timedelta
from pathlib import Path

from backend.engine.config import PRODUCT_PATH

def _safe_json(path, encoding="utf-8"):
    """Chargement JSON sécurisé avec context manager."""
    with open(path, encoding=encoding) as _f:
        return json.load(_f)


USERS_PATH    = PRODUCT_PATH / "users.json"
API_KEYS_PATH = PRODUCT_PATH / "api_keys.json"
QUOTAS_PATH   = PRODUCT_PATH / "quotas.json"
ANALYTICS_PATH= PRODUCT_PATH / "analytics.json"

VALID_PLANS = {"free", "starter", "pro"}


def _load(path: Path, default):
    if path.exists():
        try:
            return _safe_json(path)
        except Exception:
            return default
    return default

def _save(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _valid_email(email: str) -> bool:
    return bool(re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email or ""))


# ── Utilisateurs ───────────────────────────────────────────────────────────────

def create_user(email: str, plan: str = "free") -> dict:
    """
    Crée un utilisateur et génère automatiquement sa première clé API.

    Returns:
        {"user_id", "email", "plan", "api_key", "status"}
    """
    if not _valid_email(email):
        return {"error": "Email invalide."}
    if plan not in VALID_PLANS:
        return {"error": f"Plan invalide. Valides : {sorted(VALID_PLANS)}"}

    users = _load(USERS_PATH, {})

    # Vérifier doublon email
    existing = next((uid for uid, u in users.items() if u.get("email") == email), None)
    if existing:
        return {"error": "Email déjà enregistré.", "user_id": existing}

    user_id = str(uuid.uuid4())
    users[user_id] = {
        "email":   email,
        "plan":    plan,
        "created": datetime.utcnow().isoformat(),
        "active":  True,
    }
    _save(USERS_PATH, users)

    # Générer la première clé API
    key_result = generate_api_key(user_id)

    return {
        "user_id":    user_id,
        "email":      email,
        "plan":       plan,
        "api_key":    key_result["api_key"],
        "expires_at": key_result.get("expires_at"),
        "status":     "created",
        "message":    f"Compte créé. Votre clé API : {key_result['api_key']}",
    }


def get_user(user_id: str) -> dict:
    """Retourne les infos d'un utilisateur avec son quota courant."""
    users = _load(USERS_PATH, {})
    user  = users.get(user_id)
    if not user:
        return {"error": "Utilisateur introuvable."}

    # Trouver les clés de cet utilisateur
    keys     = _load(API_KEYS_PATH, {})
    # Les clés stockées sont des hashes — afficher seulement les 8 premiers chars
    user_keys= [{"key_hash_prefix": k[:8] + "…", "active": v.get("active", True), "created": v.get("created")}
                for k, v in keys.items() if v.get("user_id") == user_id]

    # Quota du jour (sur la clé active)
    quotas  = _load(QUOTAS_PATH, {})
    today   = date.today().isoformat()
    # Le quota est indexé par hash[:16] — récupérer la clé hash active
    active_hash = next((k for k, v in keys.items() if v.get("user_id") == user_id and v.get("active", True)), None)
    used_today  = quotas.get(f"{active_hash[:16]}:{today}", 0) if active_hash else 0

    from backend.engine.auth_middleware import PLANS
    plan_cfg = PLANS.get(user["plan"], PLANS["free"])

    return {
        "user_id":    user_id,
        "email":      user["email"],
        "plan":       user["plan"],
        "created":    user["created"],
        "active":     user.get("active", True),
        "api_keys":   user_keys,
        "quota": {
            "used_today": used_today,
            "limit_today": plan_cfg["requests_per_day"],
            "remaining":  max(0, plan_cfg["requests_per_day"] - used_today),
        },
        "features":   plan_cfg["features"],
    }


def upgrade_plan(user_id: str, new_plan: str) -> dict:
    """Change le plan d'un utilisateur."""
    if new_plan not in VALID_PLANS:
        return {"error": f"Plan invalide. Valides : {sorted(VALID_PLANS)}"}

    users = _load(USERS_PATH, {})
    if user_id not in users:
        return {"error": "Utilisateur introuvable."}

    old_plan = users[user_id]["plan"]
    users[user_id]["plan"]    = new_plan
    users[user_id]["upgraded"]= datetime.utcnow().isoformat()
    _save(USERS_PATH, users)

    return {
        "user_id":  user_id,
        "old_plan": old_plan,
        "new_plan": new_plan,
        "status":   "upgraded",
    }


# ── Clés API ───────────────────────────────────────────────────────────────────

def generate_api_key(user_id: str) -> dict:
    """Génère une nouvelle clé API pour un utilisateur existant."""
    users = _load(USERS_PATH, {})
    if user_id not in users:
        return {"error": "Utilisateur introuvable."}

    keys    = _load(API_KEYS_PATH, {})
    api_key = f"ck_{uuid.uuid4().hex}"   # préfixe "ck_" pour identifier nos clés
    key_hash= hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    created = datetime.utcnow().isoformat()

    # Stocker le HASH, jamais la clé en clair
    expires_at = (datetime.utcnow() + timedelta(days=365)).isoformat()
    keys[key_hash] = {
        "user_id":    user_id,
        "created":    created,
        "expires_at": expires_at,
        "active":     True,
    }
    _save(API_KEYS_PATH, keys)

    return {
        "api_key":    api_key,       # retourné UNE SEULE FOIS au client
        "expires_at": expires_at,
        "user_id": user_id,
        "created": created,
        "note":    "Conservez cette clé, elle ne sera plus affichée. Seul son hash est stocké.",
    }


def validate_api_key(api_key: str) -> dict:
    """Vérifie si une clé API est valide (public, sans auth)."""
    keys     = _load(API_KEYS_PATH, {})
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    if key_hash not in keys:
        return {"valid": False, "reason": "Clé inconnue."}
    if not keys[key_hash].get("active", True):
        return {"valid": False, "reason": "Clé désactivée."}

    users   = _load(USERS_PATH, {})
    user_id = keys[key_hash]["user_id"]
    user    = users.get(user_id, {})

    return {
        "valid":   True,
        "plan":    user.get("plan", "free"),
        "user_id": user_id,
    }


def revoke_api_key(api_key: str, user_id: str) -> dict:
    """Révoque une clé API (la désactive sans la supprimer)."""
    keys     = _load(API_KEYS_PATH, {})
    key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    if key_hash not in keys:
        return {"error": "Clé inconnue."}
    if keys[key_hash]["user_id"] != user_id:
        return {"error": "Cette clé n'appartient pas à cet utilisateur."}

    keys[key_hash]["active"]  = False
    keys[key_hash]["revoked"] = datetime.utcnow().isoformat()
    _save(API_KEYS_PATH, keys)
    return {"status": "revoked", "key_prefix": api_key[:8] + "…"}


# ── Analytics ──────────────────────────────────────────────────────────────────

def register_event(user_id: str, event: str, meta: dict | None = None) -> dict:
    """Enregistre un événement utilisateur."""
    analytics = _load(ANALYTICS_PATH, [])
    analytics.append({
        "user_id": user_id,
        "event":   event,
        "meta":    meta or {},
        "time":    datetime.utcnow().isoformat(),
    })
    if len(analytics) > 10_000:
        analytics = analytics[-10_000:]
    _save(ANALYTICS_PATH, analytics)
    return {"status": "logged"}


def get_user_analytics(user_id: str, limit: int = 50) -> dict:
    """Retourne l'historique des événements d'un utilisateur."""
    analytics = _load(ANALYTICS_PATH, [])
    user_events = [e for e in analytics if e.get("user_id") == user_id]
    return {
        "user_id": user_id,
        "total":   len(user_events),
        "events":  user_events[-limit:],
    }
