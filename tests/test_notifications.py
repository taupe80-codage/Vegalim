"""
tests/test_notifications.py — Nouveautés sous la cloche.

Créées aux mêmes moments que les e-mails, même quand l'e-mail est coupé ou
que SMTP n'est pas configuré ; chacun ne voit que les siennes.
"""
from __future__ import annotations

from tests.test_reviews import env, USERS, MOD  # noqa: F401  (fixture partagée)
from tests.test_contributions import GOOD


def _titles(c, who, email):
    who["email"] = email
    return [n["title"] for n in c.get("/notifications").json()["results"]]


def test_parcours_complet_des_notifications(env):  # noqa: F811
    c, who, _ = env
    author, reader = USERS[0], USERS[1]
    who["email"] = author
    # e-mails coupés : la notification dans l'application arrive quand même
    c.put("/contributions/preferences", json={"email_notifications": False})
    sid = c.post("/contributions", json={"data": GOOD, "author_name": "Léa"}).json()["id"]
    c.post(f"/contributions/{sid}/submit", json={"author_name": "Léa", "consent": True})
    assert _titles(c, who, MOD)[0].startswith("Nouvelle recette à relire")

    rid = c.post(f"/contributions/moderation/{sid}/publish", json={}).json()["published_recipe_id"]
    assert _titles(c, who, author)[0].startswith("Votre recette « Dahl")

    who["email"] = reader
    review_id = c.put(f"/avis/recette/{rid}", json={"rating": 5, "comment": "Délicieux et simple.",
                                                    "author_name": "Paul"}).json()["review"]["id"]
    assert _titles(c, who, author)[0] == "Paul a noté « Dahl de lentilles corail au potimarron rôti » 5/5"

    who["email"] = author
    c.put(f"/avis/{review_id}/reponse", json={"text": "Merci Paul !"})
    notif = c.get("/notifications").json()
    assert notif["unread"] == 2
    assert notif["results"][0]["link"] == f"/recette/{rid}"

    who["email"] = reader
    data = c.get("/notifications").json()
    assert data["unread"] == 1 and data["results"][0]["title"].endswith("vous a répondu")
    nid = data["results"][0]["id"]
    # on ne lit pas les notifications des autres
    who["email"] = author
    assert c.post(f"/notifications/{nid}/lu").status_code == 404
    who["email"] = reader
    assert c.post(f"/notifications/{nid}/lu").json() == {"unread": 0}
    assert c.get("/notifications/count").json() == {"unread": 0}

    who["email"] = author
    assert c.post("/notifications/lu").json() == {"unread": 0}
    assert c.get("/notifications/count").json() == {"unread": 0}


def test_cent_notifications_au_plus_par_compte(env):  # noqa: F811
    from backend.services import notification_service
    from backend.db.models import Notification
    c, who, Session = env
    with Session() as db:
        for i in range(105):
            notification_service.push(db, USERS[2], "test", f"n{i}")
        assert db.query(Notification).filter(Notification.user_email == USERS[2]).count() == 100
        assert not notification_service.push(db, "inconnu@exemple.com", "test", "x")
    who["email"] = USERS[2]
    assert c.get("/notifications").json()["results"][0]["title"] == "n104"


def test_dates_en_utc_explicite(env):  # noqa: F811
    """SQLite rend les dates sans fuseau : le navigateur les lisait en heure locale (« il y a 1 h »)."""
    from backend.services import notification_service
    c, who, Session = env
    with Session() as db:
        notification_service.push(db, USERS[3], "test", "à l'instant")
    who["email"] = USERS[3]
    created = c.get("/notifications").json()["results"][0]["created_at"]
    assert created.endswith("+00:00")
