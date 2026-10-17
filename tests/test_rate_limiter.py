"""
tests/test_rate_limiter.py — Le compteur de limite de débit est propre à chaque route.

Régression (vérification du site, 2026-10-17) : le compteur était partagé entre
toutes les routes d'une même IP. Après quelques pages vues, l'inscription (5 / 10 min)
et la connexion (10 / min) répondaient 429 à un visiteur normal.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from backend.core import rate_limiter


def _request(path: str, ip: str = "203.0.113.7"):
    return SimpleNamespace(
        client=SimpleNamespace(host=ip),
        scope={"route": SimpleNamespace(path=path)},
        url=SimpleNamespace(path=path),
    )


@pytest.fixture(autouse=True)
def memoire(monkeypatch):
    monkeypatch.setattr(rate_limiter, "_get_redis", lambda: None)
    rate_limiter._store.clear()
    yield
    rate_limiter._store.clear()


def test_limite_atteinte_sur_la_meme_route():
    req = _request("/auth/register")
    for _ in range(5):
        rate_limiter.check_rate_limit(req, limit=5, window_seconds=600)
    with pytest.raises(HTTPException) as exc:
        rate_limiter.check_rate_limit(req, limit=5, window_seconds=600)
    assert exc.value.status_code == 429


def test_la_navigation_n_epuise_pas_l_inscription():
    navigation = _request("/recettes")
    for _ in range(100):
        rate_limiter.check_rate_limit(navigation, limit=120, window_seconds=60)
    # 100 requêtes de navigation : l'inscription et la connexion restent disponibles
    rate_limiter.check_rate_limit(_request("/auth/register"), limit=5, window_seconds=600)
    rate_limiter.check_rate_limit(_request("/auth/login"), limit=10, window_seconds=60)


def test_une_route_a_fenetre_courte_ne_purge_pas_l_historique_d_une_autre(monkeypatch):
    horloge = [1000.0]
    monkeypatch.setattr(rate_limiter, "time", SimpleNamespace(monotonic=lambda: horloge[0]))
    register = _request("/auth/register")
    for _ in range(5):
        rate_limiter.check_rate_limit(register, limit=5, window_seconds=600)
    # 2 minutes plus tard, un appel à une route à fenêtre de 60 s ne doit pas
    # effacer les 5 inscriptions (toujours comptées sur 10 minutes)
    horloge[0] += 120
    rate_limiter.check_rate_limit(_request("/recettes"), limit=120, window_seconds=60)
    with pytest.raises(HTTPException):
        rate_limiter.check_rate_limit(register, limit=5, window_seconds=600)


def test_ips_distinctes_independantes():
    for _ in range(5):
        rate_limiter.check_rate_limit(_request("/auth/register", "198.51.100.1"), limit=5, window_seconds=600)
    rate_limiter.check_rate_limit(_request("/auth/register", "198.51.100.2"), limit=5, window_seconds=600)
