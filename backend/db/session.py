"""
session.py — Gestion de la connexion PostgreSQL/SQLite.

Configuration via variables d'environnement :
  DATABASE_URL  : URL complète PostgreSQL (prioritaire)
  DB_HOST       : hôte (défaut : localhost)
  DB_PORT       : port (défaut : 5432)
  DB_NAME       : nom de la base (défaut : alim_db)
  DB_USER       : utilisateur
  DB_PASSWORD   : mot de passe

Fallback développement : SQLite local (sans aucune configuration).

Correction P1.2 :
  DB_AVAILABLE est initialisé à False et mis à jour par refresh_db_availability(),
  appelé depuis le lifespan FastAPI (main.py) après init_db().
  L'ancien comportement (check_connection() au niveau module) provoquait un faux
  négatif permanent si la base n'était pas prête à l'import — typiquement en
  conteneur Docker où l'API démarre avant PostgreSQL.

Usage :
    from backend.db.session import get_db, engine

    # Dans une route FastAPI :
    def my_route(db: Session = Depends(get_db)):
        ...

    # En dehors de FastAPI :
    with db_session() as db:
        ...
"""
import logging
import os
from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, Session

logger = logging.getLogger(__name__)

# ── Construction de l'URL ─────────────────────────────────────────────────────

def _build_url() -> str:
    # 1. URL complète (Docker, Railway, Heroku, etc.)
    url = os.getenv("DATABASE_URL")
    if url:
        # SQLAlchemy 2.x exige postgresql:// au lieu de postgres://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        return url

    # 2. Paramètres individuels
    host     = os.getenv("DB_HOST", "localhost")
    port     = os.getenv("DB_PORT", "5432")
    name     = os.getenv("DB_NAME", "alim_db")
    user     = os.getenv("DB_USER")
    password = os.getenv("DB_PASSWORD")

    if user and password:
        return f"postgresql://{user}:{password}@{host}:{port}/{name}"

    # 3. Fallback SQLite (développement sans config)
    logger.warning(
        "DATABASE_URL non définie — utilisation de SQLite local. "
        "Données non persistantes entre déploiements. "
        "Définissez DATABASE_URL pour la production."
    )
    from pathlib import Path as _Path
    _project_root = _Path(__file__).resolve().parent.parent.parent
    return f"sqlite:///{_project_root}/alim_dev.db"


DATABASE_URL = _build_url()

# ── Moteur SQLAlchemy ─────────────────────────────────────────────────────────

_engine_kwargs = {
    "echo": os.getenv("DB_ECHO", "false").lower() == "true",
}

if DATABASE_URL.startswith("postgresql"):
    _engine_kwargs.update({
        "pool_size":     int(os.getenv("DB_POOL_SIZE",    "5")),
        "max_overflow":  int(os.getenv("DB_MAX_OVERFLOW", "10")),
        "pool_pre_ping": True,
        "pool_recycle":  3600,
    })
elif DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_engine_kwargs)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

logger.info("Base de données : %s",
            DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL)


# ── Dépendance FastAPI ────────────────────────────────────────────────────────

def get_db():
    """Dépendance FastAPI — fournit une session et la ferme après la requête."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Contexte manager (hors FastAPI) ──────────────────────────────────────────

@contextmanager
def db_session():
    """Usage en dehors de FastAPI : with db_session() as db: ..."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ── Initialisation des tables ─────────────────────────────────────────────────

def init_db() -> None:
    """Crée toutes les tables si elles n'existent pas encore."""
    from backend.db.models import Base
    Base.metadata.create_all(bind=engine)
    logger.info("Tables initialisées : %s",
                [t for t in Base.metadata.tables.keys()])


def check_connection() -> bool:
    """Vérifie que la base est accessible. Retourne True si OK."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error("Connexion base de données impossible : %s", e)
        return False


# ── Disponibilité DB ──────────────────────────────────────────────────────────
# P1.2 FIX : DB_AVAILABLE est initialisé à False.
# Il est mis à jour par refresh_db_availability(), appelé explicitement
# depuis le lifespan FastAPI (main.py) après init_db().
#
# Avantage : l'import du module ne provoque plus de connexion réseau,
# ce qui évitait un faux négatif permanent en cas de démarrage différé
# de PostgreSQL (typique en Docker Compose sans healthcheck).
#
# Les services qui importent DB_AVAILABLE doivent utiliser
# is_db_available() pour relire la valeur courante à chaque appel,
# plutôt que de capturer la valeur à l'import.

DB_AVAILABLE: bool = False


def is_db_available() -> bool:
    """Retourne l'état courant de la disponibilité DB (thread-safe en lecture)."""
    return DB_AVAILABLE


def refresh_db_availability() -> bool:
    """
    Réévalue la disponibilité de la base et met à jour DB_AVAILABLE.
    À appeler depuis le lifespan FastAPI après init_db().
    Peut aussi être appelé depuis /healthz pour forcer un retry.
    """
    global DB_AVAILABLE
    DB_AVAILABLE = check_connection()
    logger.info("DB_AVAILABLE mis à jour : %s", DB_AVAILABLE)
    return DB_AVAILABLE
