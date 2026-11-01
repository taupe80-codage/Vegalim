"""
tests/test_audit_2026_11_01.py — Régressions relevées par l'audit de cohérence du 2026-11-01.
"""
from __future__ import annotations

import pytest

from backend.core.data_io import load_recipes
from backend.services.filter_service import apply_filters


# ── Filtre difficulté : « Difficile » renvoyait 0 recette ────────────────────

@pytest.mark.parametrize("value", ["hard", "difficile", "advanced"])
def test_filtre_difficile_trouve_les_recettes_hard(value):
    recipes = load_recipes()
    page, total = apply_filters(recipes, difficulty=value, limit=len(recipes))
    expected = sum(1 for r in recipes if r.get("difficulty_level") == "hard")
    assert expected > 0
    assert total == expected
    assert all(r["difficulty_level"] == "hard" for r in page)


# ── Filtre technique : lisait r["technique"], absent des données ──────────────

def test_filtre_technique_lit_tags_technique():
    recipes = load_recipes()
    page, total = apply_filters(recipes, technique="Blending", limit=len(recipes))
    expected = sum(1 for r in recipes if "blending" in r["tags"].get("technique", []))
    assert expected > 0
    assert total == expected


# ── GET /ingredients/{id} : recettes associées lues dans composition[] ────────

def test_fiche_ingredient_liste_ses_recettes():
    from fastapi.testclient import TestClient
    from backend.api.main import app

    recipes = load_recipes()
    iid = recipes[0]["composition"][0]["ingredient"]
    expected = sum(1 for r in recipes if any(c.get("ingredient") == iid for c in r["composition"]))
    res = TestClient(app).get(f"/ingredients/{iid}")
    assert res.status_code == 200, res.text
    assert res.json()["recipes_count"] == expected > 0


# ── /nutrition : identifiants de recette textuels (répondaient 422) ───────────

def test_nutrition_accepte_les_ids_textuels():
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.core.auth_deps import get_user

    rid = load_recipes()[0]["id"]
    app.dependency_overrides[get_user] = lambda: {"email": "test@exemple.com"}
    try:
        c = TestClient(app)
        res = c.post("/nutrition/ajr_score", json={"recipe_id": rid})
        assert res.status_code == 200, res.text
        assert res.json()["ajr_score"] > 0
        res = c.post("/nutrition/alerts", json={"recipe_ids": [rid]})
        assert res.status_code == 200, res.text
        assert res.json()["avg_per_meal"].get("calories", 0) > 0
    finally:
        app.dependency_overrides.pop(get_user, None)
