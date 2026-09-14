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


# ── RecipeHistoryRepository : un avis par recette, favoris jamais purgés ──────

@pytest.fixture
def history_repo():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.db.models import Base, User
    from backend.db.repositories import RecipeHistoryRepository
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(User(email="h@exemple.com", password_hash="x"))
    db.flush()
    yield RecipeHistoryRepository(db)
    db.close()


def test_like_idempotent_et_remplace_dislike(history_repo):
    repo, e = history_repo, "h@exemple.com"
    repo.record(e, "r1", "like")
    repo.record(e, "r1", "like")
    assert repo.get_liked_recipe_ids(e) == ["r1"]
    repo.record(e, "r1", "dislike")
    assert repo.get_liked_recipe_ids(e) == [] and repo.get_disliked_recipe_ids(e) == ["r1"]


def test_unlike_retire_le_favori_sans_trace(history_repo):
    repo, e = history_repo, "h@exemple.com"
    repo.record(e, "r1", "view")
    repo.record(e, "r1", "like")
    assert repo.record(e, "r1", "unlike") is None
    assert repo.get_liked_recipe_ids(e) == []
    assert [x.action for x in repo.get_recent(e)] == ["view"]


def test_likes_ordonnes_du_plus_recent(history_repo):
    repo, e = history_repo, "h@exemple.com"
    for rid in ("a", "b", "c"):
        repo.record(e, rid, "like")
    assert repo.get_liked_recipe_ids(e) == ["c", "b", "a"]


def test_purge_ne_supprime_jamais_les_favoris(history_repo, monkeypatch):
    repo, e = history_repo, "h@exemple.com"
    monkeypatch.setattr(type(repo), "MAX_HISTORY", 3)
    repo.record(e, "fav", "like")
    for i in range(10):
        repo.record(e, f"v{i}", "view")
    assert repo.get_liked_recipe_ids(e) == ["fav"]
    assert sum(1 for x in repo.get_recent(e, limit=50) if x.action == "view") == 3


def test_route_likes_renvoie_ordre_du_compte(client, monkeypatch):
    c, _ = client
    import backend.services.interaction_service as svc
    monkeypatch.setattr(svc, "load_history",
                        lambda email: {"liked_order": ["b", "a"], "liked": {"a", "b"}})
    res = c.get("/profil/likes")
    assert res.status_code == 200 and res.json() == {"liked": ["b", "a"]}


def test_unlike_accepte(client):
    c, calls = client
    rid = load_recipes()[0]["id"]
    assert c.post("/profil/interaction", json={"recipe_id": rid, "action": "unlike"}).status_code == 204
    assert calls[-1]["action"] == "unlike"
