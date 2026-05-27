"""Routes d'authentification — ALIM v6.

Corrections P0+P1 :
  P0 : _dev_reset_token conditionné à ALIM_ENV=development.
  P0 : threading.RLock sur le fallback mémoire _reset_tokens.
  P0 : consommation atomique du token (usage unique).
  P1.1 : tokens de reset persistés en base (PasswordResetRepository).
         Compatible multi-worker uvicorn (--workers N).
         Fallback transparent vers le store mémoire si DB indisponible.
"""
import logging
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, field_validator

from backend.services.user_service    import create_user, authenticate, delete_user
from backend.services.profile_service import delete_profile
from backend.core.jwt_handler   import create_token
from backend.core.auth_deps     import get_user
from backend.core.rate_limiter  import check_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentification"])

PASSWORD_MIN_LEN = 8
_RESET_TTL_MINUTES = int(os.getenv("RESET_TOKEN_TTL_MINUTES", "30"))

# ── Environnement ──────────────────────────────────────────────────────────────
# APP_ENV est la variable canonique (docker-compose, Dockerfile).
# ALIM_ENV conservé en fallback pour rétro-compatibilité.
_IS_DEV = os.getenv("APP_ENV", os.getenv("ALIM_ENV", "production")).lower() != "production"

# ── Tentative import DB pour les reset tokens ─────────────────────────────────
_RESET_DB_OK = False
try:
    from backend.db.session import db_session, is_db_available
    from backend.db.repositories import PasswordResetRepository
    _RESET_DB_OK = True
except Exception as e:
    logger.warning("auth : import PasswordResetRepository impossible (%s) — fallback mémoire", e)


# ── Fallback mémoire — actif si DB indisponible ───────────────────────────────
_reset_tokens: dict[str, dict] = {}
_reset_lock   = threading.RLock()


def _purge_expired() -> None:
    """Supprime les tokens expirés du store mémoire. Appeler sous _reset_lock."""
    now     = datetime.now(timezone.utc)
    expired = [t for t, v in _reset_tokens.items() if v["expires"] < now]
    for t in expired:
        del _reset_tokens[t]
    if expired:
        logger.debug("Tokens mémoire expirés purgés : %d", len(expired))


# ── API reset tokens (DB si dispo, sinon mémoire) ────────────────────────────

def _store_reset_token(token: str, email: str) -> None:
    if _RESET_DB_OK and is_db_available():
        with db_session() as db:
            PasswordResetRepository(db).store(token, email, _RESET_TTL_MINUTES)
        return
    # Fallback mémoire
    with _reset_lock:
        _purge_expired()
        _reset_tokens[token] = {
            "email":   email,
            "expires": datetime.now(timezone.utc) + timedelta(minutes=_RESET_TTL_MINUTES),
        }


def _consume_reset_token(token: str) -> str | None:
    """
    Valide et consomme un token. Retourne l'email ou None si invalide/expiré.
    Usage unique garanti : le token est détruit avant tout retour.
    """
    if _RESET_DB_OK and is_db_available():
        with db_session() as db:
            return PasswordResetRepository(db).consume(token)
    # Fallback mémoire
    with _reset_lock:
        _purge_expired()
        entry = _reset_tokens.pop(token, None)
        if not entry:
            return None
        return entry["email"]


# ── Schémas Pydantic ──────────────────────────────────────────────────────────

class UserCredentials(BaseModel):
    email: EmailStr
    password: str
    name: str | None = None     # Nom d'affichage optionnel — porté par le JWT, pas stocké en DB

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LEN:
            raise ValueError(f"Mot de passe trop court — minimum {PASSWORD_MIN_LEN} caractères")
        return v

    @field_validator("name")
    @classmethod
    def name_clean(cls, v: str | None) -> str | None:
        """Sanitise le nom d'affichage (max 80 chars, pas de HTML)."""
        if v is None:
            return None
        v = v.strip()
        if not v:
            return None
        if len(v) > 80:
            raise ValueError("Nom d'affichage trop long — maximum 80 caractères")
        # Retirer les balises HTML basiques
        import re as _re
        v = _re.sub(r"<[^>]+>", "", v).strip()
        return v or None


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LEN:
            raise ValueError(f"Mot de passe trop court — minimum {PASSWORD_MIN_LEN} caractères")
        return v


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(credentials: UserCredentials):
    """Crée un nouveau compte et retourne directement un token JWT."""
    try:
        create_user(str(credentials.email), credentials.password)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    # Inclure 'name' dans le JWT si fourni — retournable via GET /auth/me sans colonne DB
    token_payload: dict = {"email": str(credentials.email)}
    if credentials.name:
        token_payload["name"] = credentials.name
    token = create_token(token_payload)
    return {"access_token": token, "token_type": "Bearer", "message": "Compte créé avec succès"}


@router.post("/login")
def login(credentials: UserCredentials, request: Request):
    """Authentifie un utilisateur. Retourne un token JWT Bearer."""
    check_rate_limit(request, limit=10, window_seconds=60)
    user = authenticate(str(credentials.email), credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou mot de passe incorrect",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {"access_token": create_token(user), "token_type": "Bearer"}


@router.get("/me")
def me(user: dict = Depends(get_user)):
    """Retourne les informations de l'utilisateur connecté depuis son token JWT."""
    return {"email": user.get("email"), "name": user.get("name", "")}


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user: dict = Depends(get_user)):
    """Supprime définitivement le compte (RGPD droit à l'effacement)."""
    delete_user(user["email"])
    delete_profile(user["email"])


@router.post("/refresh")
def refresh_token(user: dict = Depends(get_user)):
    """Renouvelle un token JWT valide avant expiration."""
    new_token = create_token({"email": user["email"]})
    return {"access_token": new_token, "token_type": "Bearer"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, request: Request):
    """
    Demande de réinitialisation de mot de passe.
    Token persisté en DB (multi-worker) avec fallback mémoire.

    Réponse identique qu'un compte existe ou non (anti-énumération).
    En développement (ALIM_ENV=development) : token inclus dans la réponse.
    En production : token à transmettre par email uniquement.
    """
    check_rate_limit(request, limit=3, window_seconds=300)
    email       = str(payload.email)
    reset_token = secrets.token_urlsafe(32)
    _store_reset_token(reset_token, email)
    logger.info("Reset token généré pour %s (db=%s dev=%s)",
                email, _RESET_DB_OK and is_db_available() if _RESET_DB_OK else False, _IS_DEV)

    response: dict = {
        "message": "Si cette adresse existe, un lien de réinitialisation a été envoyé.",
    }
    if _IS_DEV:
        response["_dev_reset_token"] = reset_token
        logger.warning("APP_ENV!=production — token de reset inclus dans la réponse (dev uniquement).")

    return response


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest):
    """
    Réinitialise le mot de passe avec un token valide.
    Consommation atomique — usage unique garanti.
    """
    email = _consume_reset_token(payload.token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token de réinitialisation invalide ou expiré",
        )

    from backend.core.security import hash_password
    from backend.services.user_service import _use_db

    if _use_db():
        from backend.db.session import db_session as _db_session
        from backend.db.repositories import UserRepository
        with _db_session() as db:
            user = UserRepository(db).get_by_email(email)
            if user:
                user.password_hash = hash_password(payload.new_password)
    else:
        from backend.services.user_service import _load, _save, _json_lock
        with _json_lock:
            users = _load()
            if email in users:
                users[email]["password"] = hash_password(payload.new_password)
                _save(users)

    logger.info("Mot de passe réinitialisé pour %s", email)
    return {"message": "Mot de passe modifié avec succès. Vous pouvez vous reconnecter."}
