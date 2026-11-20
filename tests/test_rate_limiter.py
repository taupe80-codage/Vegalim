"""Limiteur de requêtes : un compteur par route et par IP.

Avant, toutes les routes partageaient le compteur de l'IP : quelques pages du
catalogue suffisaient à épuiser les 5 inscriptions / 10 min de /auth/register.
"""
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from backend.core import rate_limiter
from backend.core.rate_limiter import check_rate_limit


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(rate_limiter, "_redis_client", None)
    monkeypatch.setattr(rate_limiter, "_redis_init_done", True)
    monkeypatch.setattr(rate_limiter, "_store", rate_limiter.defaultdict(list))
    app = FastAPI()

    @app.get("/catalogue")
    def catalogue(request: Request):
        check_rate_limit(request, limit=100, window_seconds=60)
        return {}

    @app.post("/inscription")
    def inscription(request: Request):
        check_rate_limit(request, limit=2, window_seconds=600)
        return {}

    @app.get("/fiche/{rid}")
    def fiche(rid: str, request: Request):
        check_rate_limit(request, limit=3, window_seconds=60)
        return {}

    return TestClient(app)


def test_parcourir_ne_consomme_pas_les_inscriptions(client):
    for _ in range(10):
        assert client.get("/catalogue").status_code == 200
    assert client.post("/inscription").status_code == 200
    assert client.post("/inscription").status_code == 200
    assert client.post("/inscription").status_code == 429
    # l'inscription épuisée ne bloque pas non plus le catalogue
    assert client.get("/catalogue").status_code == 200


def test_un_seul_compteur_pour_toutes_les_fiches(client):
    """Le chemin générique fait le compteur : changer d'identifiant ne contourne pas la limite."""
    for rid in ("a", "b", "c"):
        assert client.get(f"/fiche/{rid}").status_code == 200
    assert client.get("/fiche/d").status_code == 429


def test_route_scope_chemin_generique(client):
    seen = {}

    @client.app.get("/r/{x}")
    def r(x: str, request: Request):
        seen["scope"] = rate_limiter.route_scope(request)
        return {}

    client.get("/r/42")
    assert seen["scope"] == "GET /r/{x}"
