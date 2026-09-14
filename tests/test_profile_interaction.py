"""
tests/test_profile_interaction.py — POST /profil/interaction accepte les identifiants textuels.

Régression 2026-09-14 : recipe_id était typé int, toutes les interactions
(like, view…) répondaient 422 et la personnalisation ne s'activait jamais.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app
from backend.core.auth_deps import get_user
from backend.core.data_io import load_recipes


@pytest.fixture
def client(monkeypatch):
    import backend.services.interaction_service as svc
    calls = []
    monkeypatch.setattr(svc, "save_interaction", lambda **kw: calls.append(kw) or True)
    app.dependency_overrides[get_user] = lambda: {"email": "test@exemple.com"}
    try:
        yield TestClient(app), calls
    finally:
        app.dependency_overrides.pop(get_user, None)


def test_like_avec_identifiant_textuel(client):
    c, calls = client
    rid = load_recipes()[0]["id"]
    res = c.post("/profil/interaction", json={"recipe_id": rid, "action": "like"})
    assert res.status_code == 204, res.text
    assert calls == [{"email": "test@exemple.com", "recipe_id": rid, "action": "like",
                      "score_shown": None, "profile_used": None}]


def test_recette_inconnue_404_action_invalide_400(client):
    c, calls = client
    rid = load_recipes()[0]["id"]
    assert c.post("/profil/interaction", json={"recipe_id": "n_existe_pas", "action": "like"}).status_code == 404
    assert c.post("/profil/interaction", json={"recipe_id": rid, "action": "hack"}).status_code == 400
    assert not calls
