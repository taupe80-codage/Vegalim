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


# ── /profil : sauvegarde sans objectif, consentement, révocation ──────────────

@pytest.fixture
def profil_client(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    from backend.api.main import app
    from backend.core.auth_deps import get_user
    from backend.services import profile_service

    monkeypatch.setattr(profile_service, "_use_db", lambda: False)
    monkeypatch.setattr(profile_service, "_FILE", tmp_path / "user_profiles.json")
    app.dependency_overrides[get_user] = lambda: {"email": "profil@exemple.com"}
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_user, None)


def test_profil_regime_et_objectif_vide_sans_consentement(profil_client):
    # La page envoyait toujours goal="" : 403 à chaque sauvegarde
    res = profil_client.post("/profil/update", json={"diet": "vegan", "goal": ""})
    assert res.status_code == 200, res.text
    assert profil_client.get("/profil/").json()["diet"] == "vegan"


def test_profil_objectif_exige_le_consentement(profil_client):
    assert profil_client.post("/profil/update", json={"goal": "energie"}).status_code == 403
    assert profil_client.patch("/profil/consent", json={"health_consent": True}).status_code == 200
    assert profil_client.post("/profil/update", json={"goal": "energie"}).status_code == 200
    assert profil_client.get("/profil/").json()["health_goal"] == "energie"


def test_profil_revocation_efface_les_donnees_de_sante(profil_client):
    profil_client.patch("/profil/consent", json={"health_consent": True})
    profil_client.post("/profil/update", json={"goal": "energie", "diet": "vegan"})
    res = profil_client.patch("/profil/consent", json={"health_consent": False})
    assert res.status_code == 200
    p = profil_client.get("/profil/").json()
    assert not p.get("health_goal") and not p.get("goal") and not p.get("cycle_phase")
    assert p["health_consent"] is False
    assert p["diet"] == "vegan"
