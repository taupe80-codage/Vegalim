"""
Création et vérification des tokens JWT.
La variable d'environnement SECRET_KEY est OBLIGATOIRE en production.
En développement, une clé aléatoire est générée à chaque démarrage (tokens
non persistants entre redémarrages — comportement attendu en dev).
"""
import os
import secrets
from datetime import datetime, timedelta, timezone
from jose import jwt, JWTError

# Charger .env avant de lire SECRET_KEY
# (jwt_handler est importe avant load_dotenv dans main.py)
try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
except ImportError:
    pass  # python-dotenv non installe — ok en prod avec variable systeme

_raw = os.getenv("SECRET_KEY")
if not _raw:
    import warnings
    import secrets as _secrets
    _raw = _secrets.token_urlsafe(64)
    warnings.warn(
        "SECRET_KEY non definie — cle aleatoire generee. "
        "Les tokens JWT ne survivront pas aux redemarrages. "
        "Definissez SECRET_KEY en variable d'environnement pour la production.",
        stacklevel=1,
    )

SECRET       = _raw
ALGO         = "HS256"
EXPIRE_HOURS = 24


def create_token(data: dict) -> str:
    payload = data.copy()
    payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=EXPIRE_HOURS)
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGO])
    except JWTError:
        return None
