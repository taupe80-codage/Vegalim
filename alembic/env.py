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
import os
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
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

# Configurer les logs depuis alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Métadata cible pour --autogenerate
target_metadata = Base.metadata


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
