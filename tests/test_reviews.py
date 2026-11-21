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


def _community_recipe(c, who, author):
    from tests.test_contributions import GOOD
    who["email"] = author
    sid = c.post("/contributions", json={"data": GOOD, "author_name": "Léa"}).json()["id"]
    c.post(f"/contributions/{sid}/submit", json={"author_name": "Léa", "consent": True})
    who["email"] = MOD
    return c.post(f"/contributions/moderation/{sid}/publish", json={}).json()["published_recipe_id"]


def test_reponse_de_l_auteur_et_emails(env, monkeypatch):
    from backend.services import mail_service
    monkeypatch.delenv("SMTP_HOST", raising=False)
    c, who, _ = env
    rid = _community_recipe(c, who, USERS[0])
    mail_service.OUTBOX.clear()
    who["email"] = USERS[1]
    res = c.put(f"/avis/recette/{rid}", json={"rating": 4, "comment": "Très bon, j'ai ajouté du gingembre.",
                                              "author_name": "Paul"})
    review_id = res.json()["review"]["id"]
    # l'auteur de la recette est prévenu du nouvel avis (une seule fois)
    assert [m["subject"] for m in mail_service.OUTBOX if USERS[0] in m["to"]] == [
        "Nouvel avis sur votre recette « Dahl de lentilles corail au potimarron rôti »"]
    c.put(f"/avis/recette/{rid}", json={"rating": 5, "comment": "Encore meilleur réchauffé.", "author_name": "Paul"})
    assert len([m for m in mail_service.OUTBOX if USERS[0] in m["to"]]) == 1

    # seul l'auteur de la recette répond
    assert c.put(f"/avis/{review_id}/reponse", json={"text": "Merci !"}).status_code == 403
    who["email"] = USERS[0]
    res = c.put(f"/avis/{review_id}/reponse", json={"text": "Merci Paul, bonne idée le gingembre !"})
    assert res.status_code == 200 and res.json()["review"]["author_reply"].startswith("Merci Paul")
    assert any(USERS[1] in m["to"] and "vous a répondu" in m["subject"] for m in mail_service.OUTBOX)
    data = c.get(f"/avis/recette/{rid}").json()
    assert data["reviews"][0]["author_reply"].startswith("Merci Paul") and data["own_recipe"]
    # pas de réponse sur une recette du catalogue
    who["email"] = USERS[2]
    cat_review = _review(c, who, USERS[2], 4, "Bonne recette du catalogue.")["review"]["id"]
    who["email"] = USERS[0]
    assert c.put(f"/avis/{cat_review}/reponse", json={"text": "Merci"}).status_code == 403
    # retrait de la réponse
    assert c.delete(f"/avis/{review_id}/reponse").json()["review"]["author_reply"] == ""


def test_les_notes_nourrissent_la_personnalisation_pas_les_favoris(env, monkeypatch):
    from backend.engine.reco_engine import learning
    from backend.db import session as db_session_mod
    c, who, Session = env
    from contextlib import contextmanager

    @contextmanager
    def _session():
        db = Session()
        try:
            yield db
            db.commit()
        finally:
            db.close()
    monkeypatch.setattr(db_session_mod, "db_session", _session)
    ids = [r["id"] for r in data_io.load_recipes()[:3]]
    who["email"] = USERS[3]
    for rid, rating in zip(ids, (5, 4, 1)):
        assert c.put(f"/avis/recette/{rid}", json={"rating": rating, "author_name": "Zoé"}).status_code == 200
    monkeypatch.setattr(learning, "load_history",
                        lambda email: {"liked": set(), "disliked": {ids[0]}, "viewed": set(), "raw": []})
    taste = learning.load_taste_history(USERS[3])
    # 4-5 ★ → like, 1-2 ★ → dislike ; le dislike explicite l'emporte sur le 5 ★
    assert taste["liked"] == {ids[1]}
    assert taste["disliked"] == {ids[0], ids[2]}
    # les favoris (/profil/likes) ne contiennent pas les recettes notées
    assert learning.load_history(USERS[3])["liked"] == set()
