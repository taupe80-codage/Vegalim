"""
tests/test_seasonality.py — Saisonnalité, réutilisation d'ingrédients du planner
et CSP des polices (vérification fonctionnelle du site, 2026-10-17).

Régressions couvertes :
    seasonal_ingredients  lisait un graphe « seasonality » inexistant → toujours []
    season_bonus          lisait recipe["ingredients"] (absent des recettes) → toujours 0
    _reuse_score          idem : le bonus de réutilisation du plan de repas était toujours 0
    CSP                   Google Fonts (index.html, index.css) refusé par le navigateur
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.engine.planning_engine.planner import _reuse_score
from backend.engine.rule_engine.seasonality import (
    in_season,
    season_bonus,
    seasonal_ingredients,
)


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def _recipe(*ingredients: str) -> dict:
    return {"composition": [{"ingredient": i, "quantity": 100, "unit": "g"} for i in ingredients]}


def test_seasonal_ingredients_non_vide():
    assert "asparagus" in seasonal_ingredients(4)
    assert "asparagus" not in seasonal_ingredients(11)
    assert in_season("asparagus", 4) and not in_season("asparagus", 11)


def test_route_seasonal_renvoie_des_ingredients(client):
    r = client.get("/planning/seasonal", params={"month": 4})
    assert r.status_code == 200
    assert "asparagus" in r.json()["ingredients"]


def test_season_bonus_lit_la_composition():
    recipe = _recipe("asparagus", "artichoke", "salt")
    assert season_bonus(recipe, 4) == 2.0
    assert season_bonus(recipe, 11) == 0.0
    assert season_bonus(recipe, None) == 0.0


def test_season_bonus_ignore_les_ingredients_de_toute_l_annee():
    assert season_bonus(_recipe("tomato", "salt"), 1) == 0.0


def test_season_bonus_repli_par_prefixe():
    assert season_bonus(_recipe("asparagus_cooked"), 4) == 2.0


def test_reuse_score_lit_la_composition():
    from collections import Counter
    planned = Counter({"lentils": 2, "carrot": 1})
    assert _reuse_score(_recipe("lentils", "carrot"), planned) > 0
    assert _reuse_score(_recipe("quinoa"), planned) == 0


def test_csp_frontend_autorise_google_fonts(client):
    csp = client.get("/ui/").headers["content-security-policy"]
    directives = {d.split()[0]: d.split()[1:] for d in csp.split(";") if d.strip()}
    assert "https://fonts.googleapis.com" in directives["style-src"]
    assert "https://fonts.gstatic.com" in directives["font-src"]
    # le reste de la politique reste strict
    assert directives["script-src"] == ["'self'"]
    assert directives["connect-src"] == ["'self'"]
