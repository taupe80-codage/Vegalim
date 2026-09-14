"""
tests/test_security.py — Garde-fous de sécurité des routes (2026-09-14).

Couverture :
    PUT /planning/prices     compte obligatoire, variation bornée, paquet inconnu
    /admin/*                 clé API seule insuffisante (ADMIN_EMAILS)
    authentification         en-tête absent → 401 (et non 422)
    environnement            jeton de reset jamais exposé si APP_ENV non explicite
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.jwt_handler import create_token
from backend.engine.config import DATA_ROOT

CATALOG = DATA_ROOT / "config" / "prices_catalog.json"


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


@pytest.fixture()
def auth_headers():
    return {"Authorization": f"Bearer {create_token({'email': 'securite@test.fr'})}"}


def _catalog_bytes() -> bytes:
    return CATALOG.read_bytes()


# ── Correction de prix ────────────────────────────────────────────────────────

def test_prix_sans_compte_refuse(client):
    before = _catalog_bytes()
    r = client.put("/planning/prices/olive_oil", json={"package_label": "1L", "new_price": 0.01})
    assert r.status_code == 401
    assert _catalog_bytes() == before


def test_prix_variation_excessive_refusee(client, auth_headers):
    before = _catalog_bytes()
    entry = json.loads(before.decode("utf-8"))["olive_oil"]
    pkg = entry["packages"][0]
    r = client.put("/planning/prices/olive_oil", headers=auth_headers,
                   json={"package_label": pkg["label"], "new_price": round(pkg["price"] * 50, 2)})
    assert r.status_code == 422
    assert _catalog_bytes() == before


def test_prix_paquet_inconnu_ne_modifie_rien(client, auth_headers):
    before = _catalog_bytes()
    r = client.put("/planning/prices/olive_oil", headers=auth_headers,
                   json={"package_label": "paquet-qui-n-existe-pas", "new_price": 3})
    assert r.status_code == 404
    assert _catalog_bytes() == before


# ── Administration ────────────────────────────────────────────────────────────

def test_admin_cle_api_sans_email_admin_refusee(client, monkeypatch):
    from backend.core import auth_deps
    from backend.core.config import settings

    app.dependency_overrides[auth_deps.require_api_key] = lambda: {"email": "client@b2b.fr", "plan": "free"}
    try:
        monkeypatch.setattr(settings, "admin_emails", set())
        assert client.post("/admin/search_tokens/rebuild").status_code == 403

        monkeypatch.setattr(settings, "admin_emails", {"admin@alim.fr"})
        assert client.post("/admin/search_tokens/rebuild").status_code == 403
        assert client.get("/admin/diet_flags/audit").status_code == 403
    finally:
        app.dependency_overrides.pop(auth_deps.require_api_key, None)


def test_admin_email_autorise_accepte(client, monkeypatch):
    from backend.core import auth_deps
    from backend.core.config import settings

    app.dependency_overrides[auth_deps.require_api_key] = lambda: {"email": "Admin@Alim.fr", "plan": "pro"}
    try:
        monkeypatch.setattr(settings, "admin_emails", {"admin@alim.fr"})
        assert client.get("/admin/quota").status_code == 200
    finally:
        app.dependency_overrides.pop(auth_deps.require_api_key, None)


# ── Authentification ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("method,path", [
    ("GET", "/profil/"), ("GET", "/auth/me"), ("POST", "/recettes/recommend"),
])
def test_entete_absent_renvoie_401(client, method, path):
    assert client.request(method, path, json={}).status_code == 401


def test_cle_api_absente_renvoie_401(client):
    assert client.get("/admin/quota").status_code == 401


# ── Environnement ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("env,exposed", [
    ({}, False),
    ({"APP_ENV": "production"}, False),
    ({"APP_ENV": "development"}, True),
])
def test_jeton_reset_expose_seulement_en_dev_explicite(monkeypatch, env, exposed):
    from backend.core.config import _Settings
    for var in ("APP_ENV", "ALIM_ENV"):
        monkeypatch.delenv(var, raising=False)
    for k, v in env.items():
        monkeypatch.setenv(k, v)
    assert _Settings().is_explicit_development is exposed
