"""
tests/test_reviews.py — Notes et commentaires sur les recettes.

Un avis par compte et par recette (modifiable), moyenne et répartition,
« utile », signalement avec masquage automatique, modération, l'auteur d'une
recette proposée ne note pas la sienne, suppression du compte.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.core import data_io
from backend.core.auth_deps import get_user, get_optional_user
from backend.db.models import Base, User
from backend.db.session import get_db

USERS = ["a@exemple.com", "b@exemple.com", "c@exemple.com", "d@exemple.com"]
MOD = "moderation@exemple.com"


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        for e in USERS + [MOD]:
            db.add(User(email=e, password_hash="x"))
        db.commit()

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    from backend.core.config import settings
    monkeypatch.setattr(settings, "admin_emails", {MOD})
    monkeypatch.setattr(data_io, "COMMUNITY_RECIPES_PATH", tmp_path / "community_recipes.json")
    import backend.api.routes.reviews as routes
    import backend.api.routes.contributions as croutes
    monkeypatch.setattr(routes, "check_rate_limit", lambda *a, **k: None)
    monkeypatch.setattr(croutes, "check_rate_limit", lambda *a, **k: None)
    who = {"email": USERS[0]}
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_user] = lambda: dict(who)
    app.dependency_overrides[get_optional_user] = lambda: dict(who)
    data_io.load_recipes.cache_clear()
    try:
        yield TestClient(app), who, Session
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_user, None)
        app.dependency_overrides.pop(get_optional_user, None)
        data_io.load_recipes.cache_clear()


RID = None


def _rid():
    global RID
    if RID is None:
        RID = data_io.load_recipes()[0]["id"]
    return RID


def _review(c, who, email, rating, comment="", made_it=False):
    who["email"] = email
    res = c.put(f"/avis/recette/{_rid()}", json={"rating": rating, "comment": comment,
                                                "made_it": made_it, "author_name": email.split("@")[0].upper() * 2})
    assert res.status_code == 200, res.text
    return res.json()


def test_un_avis_par_compte_moyenne_et_repartition(env):
    c, who, _ = env
    _review(c, who, USERS[0], 5, "Délicieux, toute la famille a adoré.", made_it=True)
    _review(c, who, USERS[1], 3)                                   # note seule
    out = _review(c, who, USERS[0], 4, "Délicieux, un peu salé la seconde fois.")   # modifie
    s = out["summary"]
    assert s["count"] == 2 and s["average"] == 3.5
    assert s["distribution"]["4"] == 1 and s["distribution"]["3"] == 1 and s["distribution"]["5"] == 0
    assert s["made_it"] == 0 and s["comments"] == 1

    data = c.get(f"/avis/recette/{_rid()}").json()
    assert data["total"] == 1                                       # seuls les commentaires sont listés
    assert data["reviews"][0]["comment"].startswith("Délicieux, un peu salé")
    assert data["mine"]["rating"] == 4 and data["can_review"]

    summaries = c.post("/avis/resume", json={"ids": [_rid(), "inconnue"]}).json()["summaries"]
    assert summaries == {_rid(): {"average": 3.5, "count": 2}}


def test_validation(env):
    c, who, _ = env
    assert c.put(f"/avis/recette/{_rid()}", json={"rating": 6, "author_name": "Léa"}).status_code == 422
    assert c.put(f"/avis/recette/{_rid()}", json={"rating": 4, "author_name": "x"}).status_code == 422
    res = c.put(f"/avis/recette/{_rid()}", json={"rating": 4, "author_name": "Léa",
                                                "comment": "Voir https://exemple.com"})
    assert res.status_code == 422
    assert c.put("/avis/recette/n_existe_pas", json={"rating": 4, "author_name": "Léa"}).status_code == 404


def test_utile_et_signalement_masquage_automatique(env):
    c, who, _ = env
    rid = _review(c, who, USERS[0], 2, "Pas terrible, trop fade à mon goût.")["review"]["id"]
    # on ne vote pas pour soi
    assert c.post(f"/avis/{rid}/utile").status_code == 403
    who["email"] = USERS[1]
    assert c.post(f"/avis/{rid}/utile").json() == {"helpful_count": 1, "voted": True}
    assert c.post(f"/avis/{rid}/utile").json() == {"helpful_count": 0, "voted": False}
    for i, email in enumerate(USERS[1:]):
        who["email"] = email
        res = c.post(f"/avis/{rid}/signaler", json={"reason": "offensive"})
        assert res.status_code == 200
        assert res.json()["hidden"] is (i == 2)                     # masqué au 3e signalement
    assert c.post(f"/avis/{rid}/signaler", json={"reason": "spam"}).status_code == 409
    assert c.get(f"/avis/recette/{_rid()}").json()["summary"]["count"] == 0

    # la modération le retrouve, le rétablit
    assert c.get("/avis/moderation").status_code == 403
    who["email"] = MOD
    hidden = c.get("/avis/moderation?status=hidden").json()
    assert hidden["results"][0]["id"] == rid
    assert hidden["results"][0]["reasons"] == {"Propos insultants ou inappropriés": 3}
    assert c.post(f"/avis/moderation/{rid}/restore").json()["status"] == "visible"
    assert c.get(f"/avis/recette/{_rid()}").json()["summary"]["count"] == 1
    assert c.delete(f"/avis/moderation/{rid}").status_code == 204
    assert c.get(f"/avis/recette/{_rid()}").json()["summary"]["count"] == 0


def test_retirer_son_avis(env):
    c, who, _ = env
    _review(c, who, USERS[0], 5, "Parfait pour un dîner rapide.")
    assert c.delete(f"/avis/recette/{_rid()}").json()["summary"]["count"] == 0
    assert c.delete(f"/avis/recette/{_rid()}").status_code == 404


def test_l_auteur_ne_note_pas_sa_propre_recette(env):
    from tests.test_contributions import GOOD
    c, who, _ = env
    who["email"] = USERS[0]
    sid = c.post("/contributions", json={"data": GOOD, "author_name": "Léa"}).json()["id"]
    c.post(f"/contributions/{sid}/submit", json={"author_name": "Léa", "consent": True})
    who["email"] = MOD
    rid = c.post(f"/contributions/moderation/{sid}/publish", json={}).json()["published_recipe_id"]
    who["email"] = USERS[0]
    assert c.get(f"/avis/recette/{rid}").json()["own_recipe"] is True
    assert c.put(f"/avis/recette/{rid}", json={"rating": 5, "author_name": "Léa"}).status_code == 403
    who["email"] = USERS[1]
    assert c.put(f"/avis/recette/{rid}", json={"rating": 5, "author_name": "Paul"}).status_code == 200


def test_suppression_du_compte_recalcule_les_compteurs(env):
    from backend.api.routes.reviews import delete_user_reviews
    c, who, Session = env
    rid = _review(c, who, USERS[0], 4, "Très bon avec du riz basmati.")["review"]["id"]
    _review(c, who, USERS[1], 2, "Trop épicé pour moi, dommage.")
    who["email"] = USERS[1]
    c.post(f"/avis/{rid}/utile")
    with Session() as db:
        assert delete_user_reviews(db, USERS[1]) == 1
    data = c.get(f"/avis/recette/{_rid()}").json()
    assert data["summary"]["count"] == 1
    assert data["reviews"][0]["helpful_count"] == 0
