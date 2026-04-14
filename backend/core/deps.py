"""
deps.py — Dépendances FastAPI non-auth (DB, helpers).

Pour les dépendances d'authentification, utiliser auth_deps.py.
"""
import logging
logger = logging.getLogger(__name__)

# Ré-exporter pour compatibilité ascendante (imports existants depuis deps)
from backend.core.auth_deps import get_user, get_optional_user  # noqa: F401


# ── Session PostgreSQL (optionnelle) ─────────────────────────────────────────

try:
    from backend.db.session import get_db as _get_db, check_connection
    _DB_AVAILABLE = check_connection()
except Exception:
    _DB_AVAILABLE = False
    _get_db = None


def get_db():
    """
    Dépendance FastAPI : fournit une session SQLAlchemy.
    Lève 503 si la BDD est indisponible.
    """
    if not _DB_AVAILABLE or _get_db is None:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de données indisponible. Contactez l'administrateur.",
        )
    yield from _get_db()
