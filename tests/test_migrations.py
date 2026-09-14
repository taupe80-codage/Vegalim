"""
tests/test_migrations.py — Les migrations Alembic construisent le schéma des modèles.

Régression 2026-09-14 : la migration initiale était vide, `alembic upgrade head`
échouait sur une base neuve (ALTER TABLE user_profiles inexistante) et l'API se
rabattait silencieusement sur create_all() avec alembic_version bloquée.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("alembic")

ROOT = Path(__file__).resolve().parents[1]


def _alembic(db: Path, *args: str) -> subprocess.CompletedProcess:
    import os
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{db.as_posix()}", "PYTHONIOENCODING": "utf-8"}
    return subprocess.run([sys.executable, "-m", "alembic", *args], cwd=ROOT, env=env,
                          capture_output=True, text=True, encoding="utf-8", errors="replace")


def test_upgrade_head_sur_base_vierge_puis_schema_conforme(tmp_path):
    db = tmp_path / "fresh.db"
    up = _alembic(db, "upgrade", "head")
    assert up.returncode == 0, up.stderr[-2000:]
    check = _alembic(db, "check")
    assert check.returncode == 0, (
        "Modèles SQLAlchemy et migrations divergent — générer une migration :\n"
        + check.stdout[-1500:] + check.stderr[-1500:]
    )


def test_aller_retour_downgrade_upgrade(tmp_path):
    db = tmp_path / "roundtrip.db"
    for args in (("upgrade", "head"), ("downgrade", "base"), ("upgrade", "head")):
        res = _alembic(db, *args)
        assert res.returncode == 0, (args, res.stderr[-2000:])


def test_migrations_sur_base_creee_par_create_all(tmp_path):
    """Bases initialisées par le repli create_all() : les migrations doivent passer."""
    db = tmp_path / "create_all.db"
    code = (
        "import sys; sys.path.insert(0, '.');"
        "from sqlalchemy import create_engine;"
        "from backend.db.models import Base;"
        f"Base.metadata.create_all(create_engine('sqlite:///{db.as_posix()}'))"
    )
    subprocess.run([sys.executable, "-c", code], cwd=ROOT, check=True)
    up = _alembic(db, "upgrade", "head")
    assert up.returncode == 0, up.stderr[-2000:]
    assert _alembic(db, "check").returncode == 0
