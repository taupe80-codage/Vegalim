"""
Auth Middleware
================
Système d'authentification par clé API pour la plateforme culinaire.

Architecture :
  - Stockage fichier JSON (SQLite-ready via migration future)
  - 3 plans : free / starter / pro
  - Quotas journaliers par plan
  - Dépendance FastAPI injectable sur chaque route protégée

Plans :
  free    → 50 req/jour  | mealplan ✗ | import ✗ | simulation ✗
  starter → 500 req/jour | mealplan ✓ | import ✗ | simulation ✓
  pro     → 5000 req/jour| mealplan ✓ | import ✓ | simulation ✓

Usage dans main.py :
    
    @app.get("/mealplan")
    def meal_plan(user: APIUser = Depends(require_api_key)):
        ...

    @app.post("/import_recipe")
    def import_recipe(payload: dict, user: APIUser = Depends(require_plan("pro"))):
        ...
"""

import json
import uuid
import hashlib
from datetime import datetime, date
from pathlib import Path
from functools import wraps

from fastapi import HTTPException, Security, Header
from fastapi.security import APIKeyHeader
from backend.engine.config import PRODUCT_PATH

def _safe_json(path, encoding="utf-8"):
    """Chargement JSON sécurisé avec context manager."""
    with open(path, encoding=encoding) as _f:
        return json.load(_f)


# ── Chemins de stockage ────────────────────────────────────────────────────────
USERS_PATH     = PRODUCT_PATH / "users.json"
API_KEYS_PATH  = PRODUCT_PATH / "api_keys.json"
QUOTAS_PATH    = PRODUCT_PATH / "quotas.json"
ANALYTICS_PATH = PRODUCT_PATH / "analytics.json"

# ── Plans et quotas ────────────────────────────────────────────────────────────
PLANS = {
    "free": {
        "requests_per_day": 50,
        "features": {
            "mealplan":   False,
            "import":     False,
            "simulation": False,
            "save_recipe":False,
            "quality_audit": False,
        },
        "description": "50 requêtes/jour, accès lecture seule",
    },
    "starter": {
        "requests_per_day": 500,
        "features": {
            "mealplan":   True,
            "import":     False,
            "simulation": True,
            "save_recipe":False,
            "quality_audit": False,
        },
        "description": "500 requêtes/jour, plan repas + simulation",
    },
    "pro": {
        "requests_per_day": 5000,
        "features": {
            "mealplan":   True,
            "import":     True,
            "simulation": True,
            "save_recipe":True,
            "quality_audit": True,
        },
        "description": "5000 requêtes/jour, accès complet",
    },
}

# Routes protégées et la feature requise
PROTECTED_ROUTES: dict[str, str | None] = {
    "/mealplan":              "mealplan",
    "/shoppinglist":          "mealplan",
    "/nutrition_week":        "mealplan",
    "/health_score":          "mealplan",
    "/auto_menu":             "mealplan",
    "/simulate_recipe":       "simulation",
    "/simulate_recipe_world": "simulation",
    "/import_recipe":         "import",
    "/validate_import":       "import",
    "/save_recipe":           "save_recipe",
    "/vegan_variant":         None,          # accessible à tous les plans authentifiés
    "/vegan_suggestions":     None,
    "/learning_feedback":     None,
    "/data_quality_audit":    "quality_audit",
    "/recipe_carbon":         None,
    "/get_user":              None,
    "/upgrade_plan":          None,
    "/generate_api_key":      None,
}

# ── Schéma de sécurité FastAPI ─────────────────────────────────────────────────
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


# ── Hachage des clés API ──────────────────────────────────────────────────────
def _hash_key(api_key: str) -> str:
    """
    Retourne le SHA-256 de la clé API.
    C'est ce hash qui est stocké — jamais la clé en clair.
    """
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _lookup_key(api_key: str, keys: dict) -> tuple[str | None, dict | None]:
    """
    Recherche une clé API par son hash dans le dictionnaire.
    Retourne (hash, données) ou (None, None) si non trouvée.
    """
    h = _hash_key(api_key)
    if h in keys:
        return h, keys[h]
    return None, None


# ── Helpers JSON ───────────────────────────────────────────────────────────────
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


# ── Modèle utilisateur ─────────────────────────────────────────────────────────
class APIUser:
    def __init__(self, user_id: str, email: str, plan: str, api_key: str):
        self.user_id = user_id
        self.email   = email
        self.plan    = plan
        self.api_key = api_key

    @property
    def plan_config(self) -> dict:
        return PLANS.get(self.plan, PLANS["free"])

    def can(self, feature: str) -> bool:
        return self.plan_config["features"].get(feature, False)

    def daily_limit(self) -> int:
        return self.plan_config["requests_per_day"]

    def to_dict(self) -> dict:
        return {
            "user_id":   self.user_id,
            "email":     self.email,
            "plan":      self.plan,
            "daily_limit": self.daily_limit(),
            "features":  self.plan_config["features"],
        }


# ── Gestion des quotas ─────────────────────────────────────────────────────────
def _get_quota(api_key: str) -> int:
    """Retourne le nombre de requêtes faites aujourd'hui par cette clé (indexé par hash)."""
    today    = date.today().isoformat()
    quotas   = _load(QUOTAS_PATH, {})
    key_hash = _hash_key(api_key)
    day_key  = f"{key_hash[:16]}:{today}"   # préfixe 16 chars du hash suffit
    return quotas.get(day_key, 0)

def _increment_quota(api_key: str) -> int:
    """Incrémente le compteur de requêtes. Retourne le nouveau total."""
    today    = date.today().isoformat()
    quotas   = _load(QUOTAS_PATH, {})
    key_hash = _hash_key(api_key)
    day_key  = f"{key_hash[:16]}:{today}"
    quotas[day_key] = quotas.get(day_key, 0) + 1

    # Purge des quotas de plus de 2 jours
    yesterday = date.fromordinal(date.today().toordinal() - 1).isoformat()
    quotas = {k: v for k, v in quotas.items()
              if k.split(":")[-1] >= yesterday}

    _save(QUOTAS_PATH, quotas)
    return quotas[day_key]


# ── Dépendances FastAPI ────────────────────────────────────────────────────────
def require_api_key(api_key: str = Security(api_key_header)) -> APIUser:
    """
    Dépendance FastAPI : valide la clé API et vérifie le quota journalier.
    Injecter avec : user: APIUser = Depends(require_api_key)
    """
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Clé API manquante. Ajoutez le header X-API-Key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Vérifier que la clé existe (comparaison sur le hash — jamais la clé en clair)
    keys      = _load(API_KEYS_PATH, {})
    key_hash, key_data = _lookup_key(api_key, keys)

    if key_hash is None:
        raise HTTPException(status_code=401, detail="Clé API invalide.")

    if not key_data.get("active", True):
        raise HTTPException(status_code=403, detail="Clé API désactivée.")

    # Vérifier l'expiration
    expires_at = key_data.get("expires_at")
    if expires_at:
        from datetime import datetime
        if datetime.utcnow().isoformat() > expires_at:
            raise HTTPException(
                status_code=403,
                detail="Clé API expirée. Générez une nouvelle clé via POST /generate_api_key.",
            )

    # Récupérer l'utilisateur
    users   = _load(USERS_PATH, {})
    user_id = key_data["user_id"]
    user_d  = users.get(user_id)
    if not user_d:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable.")

    user = APIUser(
        user_id = user_id,
        email   = user_d.get("email", ""),
        plan    = user_d.get("plan", "free"),
        api_key = api_key,
    )

    # Vérifier le quota journalier
    used  = _get_quota(api_key)
    limit = user.daily_limit()
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=f"Quota journalier atteint ({used}/{limit}). Passez au plan supérieur.",
            headers={"X-RateLimit-Limit": str(limit), "X-RateLimit-Used": str(used)},
        )

    # Incrémenter le compteur et logger
    new_count = _increment_quota(api_key)
    _log_event(user_id, "api_call", {"endpoint": "protected", "count": new_count})

    return user


def require_plan(feature: str):
    """
    Dépendance FastAPI factory : exige qu'un utilisateur ait accès à une feature.

    Usage : user: APIUser = Depends(require_plan("import"))
    """
    def _check(user: APIUser = Security(require_api_key)) -> APIUser:
        if not user.can(feature):
            needed = [p for p, cfg in PLANS.items() if cfg["features"].get(feature)]
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature}' non disponible avec le plan '{user.plan}'. "
                       f"Plans requis : {', '.join(needed)}.",
            )
        return user
    return _check


# ── Analytics ──────────────────────────────────────────────────────────────────
def _log_event(user_id: str, event: str, meta: dict | None = None):
    """Log un événement en arrière-plan (non bloquant)."""
    try:
        analytics = _load(ANALYTICS_PATH, [])
        analytics.append({
            "user_id": user_id,
            "event":   event,
            "meta":    meta or {},
            "time":    datetime.utcnow().isoformat(),
        })
        # Garder seulement les 10 000 derniers événements
        if len(analytics) > 10_000:
            analytics = analytics[-10_000:]
        _save(ANALYTICS_PATH, analytics)
    except Exception:
        pass  # Silencieux — le logging ne doit pas casser l'API


# ── Admin : stats ──────────────────────────────────────────────────────────────
def get_api_stats() -> dict:
    """Retourne les stats globales de l'API (pour tableau de bord admin)."""
    users    = _load(USERS_PATH, {})
    keys     = _load(API_KEYS_PATH, {})
    quotas   = _load(QUOTAS_PATH, {})
    today    = date.today().isoformat()

    plan_dist = {}
    for u in users.values():
        p = u.get("plan", "free")
        plan_dist[p] = plan_dist.get(p, 0) + 1

    today_calls = sum(v for k, v in quotas.items() if k.endswith(f":{today}"))

    return {
        "total_users":    len(users),
        "total_keys":     len(keys),
        "active_keys":    sum(1 for k in keys.values() if k.get("active", True)),
        "plan_distribution": plan_dist,
        "calls_today":    today_calls,
    }
