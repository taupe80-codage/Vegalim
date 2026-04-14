"""
migrations.py — Gestion des migrations de schéma.

Deux modes :
  1. init_db()       : Création initiale de toutes les tables (alembic-free)
  2. migrate_from_json() : Migration des données JSON existantes → PostgreSQL

Usage :
    python -m backend.db.migrations          # migration complète
    python -m backend.db.migrations --init   # initialisation seule
"""
import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)


def init_db() -> None:
    """Crée toutes les tables si elles n'existent pas encore."""
    from backend.db.session import engine, check_connection
    from backend.db.models  import Base

    if not check_connection():
        logger.error("Impossible de se connecter à la base de données.")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)
    tables = list(Base.metadata.tables.keys())
    logger.info("Tables créées/vérifiées : %s", tables)
    logger.info("✓ Tables initialisées : {', '.join(tables)}")


def migrate_from_json() -> dict:
    """
    Migre les données des fichiers JSON vers PostgreSQL.
    Idempotente : peut être relancée sans dupliquer les données.

    Returns:
        Rapport de migration {table: {created, skipped, errors}}
    """
    from backend.db.session       import db_session, init_db as _init
    from backend.db.repositories  import (
        UserRepository, UserProfileRepository,
        ApiUserRepository, ApiKeyRepository,
    )
    from backend.core.security import hash_password

    _init()  # S'assurer que les tables existent

    PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
    DATA_DIR     = PROJECT_ROOT / "backend" / "data"
    PRODUCT_DIR  = PROJECT_ROOT / "backend" / "data" / "culinary_project" / "product"

    report = {}

    # ── 1. Migration users.json (comptes B2C) ─────────────────────────────────
    users_path = DATA_DIR / "users.json"
    report["users"] = {"migrated": 0, "skipped": 0, "errors": 0}

    if users_path.exists():
        with open(users_path, encoding="utf-8") as _f:
            raw = json.load(_f)
        if raw:
            with db_session() as db:
                repo = UserRepository(db)
                for email, data in raw.items():
                    try:
                        if not repo.exists(email):
                            # Le hash bcrypt est déjà correct — on l'utilise directement
                            repo.create(email, data.get("password", ""), plan="free")
                            report["users"]["migrated"] += 1
                        else:
                            report["users"]["skipped"] += 1
                    except Exception as e:
                        logger.error("Erreur migration user %s : %s", email, e)
                        report["users"]["errors"] += 1
            logger.info("users.json → %d migrés, %d existants", report['users']['migrated'], report['users']['skipped'])
        else:
            logger.info("○ users.json vide — rien à migrer")
    else:
        logger.info("○ users.json absent — ignoré")

    # ── 2. Migration user_profiles.json ───────────────────────────────────────
    profiles_path = DATA_DIR / "user_profiles.json"
    report["user_profiles"] = {"migrated": 0, "skipped": 0, "errors": 0}

    if profiles_path.exists():
        with open(profiles_path, encoding="utf-8") as _f:
            raw = json.load(_f)
        if raw:
            with db_session() as db:
                repo = UserProfileRepository(db)
                for email, profile_data in raw.items():
                    try:
                        existing = repo.get(email)
                        if not existing:
                            repo.upsert(email, profile_data)
                            report["user_profiles"]["migrated"] += 1
                        else:
                            report["user_profiles"]["skipped"] += 1
                    except Exception as e:
                        logger.error("Erreur migration profil %s : %s", email, e)
                        report["user_profiles"]["errors"] += 1
            logger.info("✓ user_profiles.json → %d migrés", report['user_profiles']['migrated'])
        else:
            logger.info("○ user_profiles.json vide — rien à migrer")

    # ── 3. Migration product/users.json (comptes B2B API) ─────────────────────
    api_users_path = PRODUCT_DIR / "users.json"
    report["api_users"] = {"migrated": 0, "skipped": 0, "errors": 0}

    if api_users_path.exists():
        with open(api_users_path, encoding="utf-8") as _f:
            raw = json.load(_f)
        if raw:
            with db_session() as db:
                repo = ApiUserRepository(db)
                for user_id, data in raw.items():
                    try:
                        if not repo.get_by_id(user_id):
                            from backend.db.models import ApiUser
                            from datetime import datetime, timezone
                            api_user = ApiUser(
                                user_id   = user_id,
                                email     = data.get("email", f"{user_id}@unknown"),
                                plan      = data.get("plan", "free"),
                                is_active = data.get("active", True),
                            )
                            db.add(api_user)
                            report["api_users"]["migrated"] += 1
                        else:
                            report["api_users"]["skipped"] += 1
                    except Exception as e:
                        logger.error("Erreur migration api_user %s : %s", user_id, e)
                        report["api_users"]["errors"] += 1
            logger.info("✓ product/users.json → %d migrés", report['api_users']['migrated'])
        else:
            logger.info("○ product/users.json vide — rien à migrer")
    else:
        logger.info("○ product/users.json absent — ignoré")

    # Résumé
    total_migrated = sum(v["migrated"] for v in report.values())
    total_errors   = sum(v["errors"]   for v in report.values())
    logger.info("\n%s", "═"*40)
    logger.info("Migration terminée : %d enregistrements migrés", total_migrated)
    if total_errors:
        logger.info("⚠  %d erreurs — voir les logs", total_errors)

    return report


if __name__ == "__main__":
    import os
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    if "--init" in sys.argv:
        init_db()
    else:
        logger.info("=== Migration JSON → PostgreSQL ===\n")
        report = migrate_from_json()
        logger.info("\nRapport détaillé : %s", report)
