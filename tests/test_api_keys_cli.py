"""
tests/test_api_keys_cli.py — scripts/api_keys.py : création, liste, révocation.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("alembic")

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def run(tmp_path):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{(tmp_path / 'keys.db').as_posix()}",
           "PYTHONIOENCODING": "utf-8", "ADMIN_EMAILS": "admin@exemple.com"}

    def _run(*args: str) -> subprocess.CompletedProcess:
        return subprocess.run([sys.executable, *args], cwd=ROOT, env=env, capture_output=True,
                              text=True, encoding="utf-8", errors="replace")

    assert _run("-m", "alembic", "upgrade", "head").returncode == 0
    return lambda *a: _run("scripts/api_keys.py", *a)


def _field(out: str, label: str) -> str:
    return next(line.split(":", 1)[1].strip() for line in out.splitlines() if line.startswith(label))


def test_cycle_create_list_revoke(run):
    created = run("create", "Admin@Exemple.com", "--plan", "pro")
    assert created.returncode == 0, created.stderr
    raw_key, key_id = _field(created.stdout, "Clé API"), _field(created.stdout, "ID clé")
    assert len(raw_key) == 64 and len(key_id) == 12
    assert "ADMIN_EMAILS" not in created.stdout  # email normalisé → reconnu admin

    listing = run("list").stdout
    assert "admin@exemple.com" in listing and key_id in listing and raw_key not in listing
    assert "oui" in listing and "active" in listing

    assert run("revoke", key_id[:6]).returncode == 0
    assert "révoquée" in run("list").stdout
    assert run("revoke", key_id).returncode == 1  # déjà révoquée


def test_cle_creee_valide_puis_revoquee_refusee(run, tmp_path):
    raw_key = _field(run("create", "b2b@exemple.com").stdout, "Clé API")
    check = (
        "import sys; sys.path.insert(0, '.');"
        "from backend.db.session import refresh_db_availability; refresh_db_availability();"
        "from backend.services.api_key_service import validate_key;"
        f"u = validate_key('{raw_key}'); print(u and u['email'])"
    )
    env_run = lambda: subprocess.run(  # noqa: E731
        [sys.executable, "-c", check], cwd=ROOT, capture_output=True, text=True,
        env={**os.environ, "DATABASE_URL": f"sqlite:///{(tmp_path / 'keys.db').as_posix()}"},
    ).stdout.strip().splitlines()[-1]
    assert env_run() == "b2b@exemple.com"
    assert run("revoke", "--email", "b2b@exemple.com").returncode == 0
    assert env_run() == "None"


def test_erreurs_explicites(run):
    assert run("revoke").returncode == 2
    assert run("revoke", "abc").returncode == 2
    assert run("plan", "inconnu@exemple.com", "pro").returncode == 1
