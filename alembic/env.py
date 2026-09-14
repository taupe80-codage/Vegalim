"""
alembic/env.py — Configuration Alembic pour ALIM v6.

Utilise DATABASE_URL depuis les variables d'environnement (même source que l'API).
Les modèles SQLAlchemy sont importés depuis backend.db.models pour l'autogenerate.

Usage :
    alembic upgrade head          # appliquer toutes les migrations
    alembic revision --autogenerate -m "description"  # générer une migration
    alembic downgrade -1          # revenir en arrière d'une migration
    alembic current               # voir la version courante
    alembic history               # historique des migrations
"""
import logging
import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool, text
from alembic import context

# ── Chargement .env (développement) ──────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
except ImportError:
    pass

# ── Import des modèles pour autogenerate ─────────────────────────────────────
from backend.db.models import Base          # noqa: E402
from backend.db.session import DATABASE_URL # noqa: E402

# ── Config Alembic ────────────────────────────────────────────────────────────
config = context.config

# Injecter l'URL de connexion (priorité : env var > alembic.ini)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Logs d'alembic.ini uniquement si personne n'a configuré le logging (CLI brute).
# Au démarrage de l'API (upgrade dans le lifespan), fileConfig remplaçait le
# handler racine (niveau WARNING, format JSON perdu) et désactivait les loggers
# existants : plus aucun log applicatif après la migration (constaté 2026-09-14).
if config.config_file_name is not None and not logging.getLogger().handlers:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Métadata cible pour --autogenerate
target_metadata = Base.metadata

_MIGRATION_LOCK_KEY = 0x414C494D  # « ALIM »


# ── Migrations hors ligne (sans connexion DB active) ─────────────────────────
def run_migrations_offline() -> None:
    """Génère le SQL sans connexion DB (utile pour review)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Migrations en ligne (connexion DB active) ─────────────────────────────────
def run_migrations_online() -> None:
    """Applique les migrations directement sur la DB."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        if connection.dialect.name == "postgresql":
            # Uvicorn --workers N : chaque worker lance `upgrade head` au démarrage.
            # Sans verrou, deux workers migrent en parallèle une base neuve
            # (DuplicateTable) et le perdant se rabat sur create_all().
            connection.execute(text("SELECT pg_advisory_lock(:k)"), {"k": _MIGRATION_LOCK_KEY})
            connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,           # détecte les changements de type de colonne
            compare_server_default=True, # détecte les changements de valeur par défaut
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
