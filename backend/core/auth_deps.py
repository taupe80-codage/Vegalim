"""
auth_deps.py — Source unique des dépendances d'authentification.

Tous les composants d'auth sont ici. Les routes importent UNIQUEMENT depuis ce module.
deps.py contient uniquement les helpers non-auth (get_db, etc.).

Niveaux d'accès :
    get_user()           → JWT obligatoire  (plan free+)
    get_optional_user()  → JWT optionnel    (public avec personnalisation si connecté)
    require_api_key()    → API key B2B      (plan starter+)
    require_feature(f)   → API key + plan   (feature gate)
"""
import logging
import os

from fastapi import Depends, Header, HTTPException, status
from backend.core.jwt_handler import verify_token

logger = logging.getLogger(__name__)


# ── JWT Bearer — obligatoire ──────────────────────────────────────────────────

def get_user(authorization: str = Header(...)) -> dict:
    """
    Extrait l'utilisateur depuis Authorization: Bearer <token>.
    Lève 401 si token absent ou invalide.
    """
    token = authorization.removeprefix("Bearer ").strip()
    data  = verify_token(token)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide ou expiré",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return data


# ── JWT Bearer — optionnel (CDC_06 plan freemium) ─────────────────────────────

def get_optional_user(authorization: str = Header(default=None)) -> dict | None:
    """
    Auth optionnelle — retourne l'utilisateur si connecté, None sinon.

    Routes accessibles sans compte (CDC_06) : la personnalisation s'active
    automatiquement dès qu'un token valide est fourni.

    Usage :
        @router.post("/recherche")
        def recherche(user: dict | None = Depends(get_optional_user)):
            email = user["email"] if user else None
    """
    if not authorization:
        return None
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None
    try:
        data = verify_token(token)
        return data if data else None
    except Exception:
        return None


# ── API key B2B ───────────────────────────────────────────────────────────────

def require_api_key(x_api_key: str = Header(...)) -> dict:
    """
    Valide une clé API B2B (SHA-256 stockée en base).
    Lève 401 si absente ou invalide, 403 si désactivée.
    """
    from backend.engine.auth_middleware import _lookup_key
    user = _lookup_key(x_api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Clé API invalide ou absente",
        )
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clé API désactivée",
        )
    return user


# ── Feature gate (plan payant) ────────────────────────────────────────────────

def require_feature(feature: str):
    """
    Factory Depends : exige qu'un utilisateur API ait accès à une feature.

    Usage :
        @router.get("/mealplan")
        def mealplan(_user = require_feature("mealplan")):
    """
    from backend.engine.auth_middleware import require_plan
    return Depends(require_plan(feature))


# ── Classe APIUser (compat) ───────────────────────────────────────────────────

class APIUser:
    """Représentation d'un utilisateur API B2B (compatibilité auth_middleware)."""
    def __init__(self, user_id: str, email: str, plan: str = "free"):
        self.user_id = user_id
        self.email   = email
        self.plan    = plan


__all__ = [
    "get_user",
    "get_optional_user",
    "require_api_key",
    "require_feature",
    "APIUser",
]
