"""
tests/test_photo_proposals.py — Photos de plats proposées par les membres (2026-11-26).

Parcours : proposition → relecture → la photo devient celle de la recette
(servie à la même adresse /images/recipes/<slug>.jpg) → crédit ; refus avec
motif, retrait, garde-fous (consentement, une seule en attente par recette,
recettes du catalogue seulement), suppression du compte.
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.api.main import app
from backend.api.routes import photo_proposals as pp
from backend.core.auth_deps import get_optional_user, get_user
from backend.core.data_io import load_catalogue_recipes
from backend.db.models import Base, User
from backend.db.session import get_db
from backend.services import contribution_service as cs

MEMBER = "membre@exemple.com"
OTHER = "autre@exemple.com"
MOD = "moderation@exemple.com"

RECIPES = load_catalogue_recipes()
WITH_PHOTO = next(r for r in RECIPES if pp.site_photo(pp._slug(r)))
WITHOUT_PHOTO = next(r for r in RECIPES if pp._slug(r) and not pp.site_photo(pp._slug(r)))


def _jpeg(color=(200, 120, 40)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (800, 600), color).save(buf, "JPEG")
    return buf.getvalue()


@pytest.fixture
def env(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        for e in (MEMBER, OTHER, MOD):
            db.add(User(email=e, password_hash="x"))
        db.commit()

    def _db():
        db = Session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(cs, "PHOTO_DIR", tmp_path / "photos")
    monkeypatch.setattr(pp, "RECIPE_PHOTO_DIR", tmp_path / "recipe_photos")
    monkeypatch.setattr(pp, "check_rate_limit", lambda *a, **k: None)
    from backend.core.config import settings
    monkeypatch.setattr(settings, "admin_emails", {MOD})
    monkeypatch.delenv("SMTP_HOST", raising=False)

    who = {"email": MEMBER}
    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_user] = lambda: dict(who)
    app.dependency_overrides[get_optional_user] = lambda: dict(who)
    try:
        yield TestClient(app), who, Session
    finally:
        for dep in (get_db, get_user, get_optional_user):
            app.dependency_overrides.pop(dep, None)


def _propose(c, rid, *, consent=True, name="Léa", data=None, ctype="image/jpeg"):
    return c.post(f"/photo-proposals/{rid}?author_name={name}&consent={'true' if consent else 'false'}",
                  content=data if data is not None else _jpeg(), headers={"Content-Type": ctype})


def test_proposer_relire_publier(env):
    from backend.services import mail_service
    mail_service.OUTBOX.clear()
    c, who, _ = env
    rid, slug = WITHOUT_PHOTO["id"], pp._slug(WITHOUT_PHOTO)
    assert c.get(f"/images/recipes/{slug}.jpg").status_code == 404

    res = _propose(c, rid)
    assert res.status_code == 201, res.text
    pid = res.json()["id"]
    assert res.json()["status"] == "submitted"
    assert any(MOD in m["to"] and "Photo à relire" in m["subject"] for m in mail_service.OUTBOX)
    # encore invisible sur la fiche, visible dans « ma proposition en cours »
    info = c.get(f"/photo-proposals/recipe/{rid}").json()
    assert info["credit"] is None and info["my_pending"]["id"] == pid
    assert c.get(f"/images/recipes/{slug}.jpg").status_code == 404

    # un membre ne modère pas
    assert c.post(f"/photo-proposals/moderation/{pid}/approve", json={}).status_code == 403

    who["email"] = MOD
    queue = c.get("/photo-proposals/moderation/queue").json()
    assert queue["counts"]["submitted"] == 1 and queue["results"][0]["user_email"] == MEMBER
    assert queue["results"][0]["current_photo_url"] is None
    res = c.post(f"/photo-proposals/moderation/{pid}/approve", json={"message": "Superbe, merci !"})
    assert res.status_code == 200 and res.json()["status"] == "approved"

    img = c.get(f"/images/recipes/{slug}.jpg")
    assert img.status_code == 200 and img.headers["content-type"] == "image/jpeg"
    assert c.get(f"/photo-proposals/recipe/{rid}").json()["credit"]["author_name"] == "Léa"
    assert any(x["recipe_id"] == rid for x in c.get("/photo-proposals/credits").json()["results"])
    assert any(MEMBER in m["to"] and "en ligne" in m["subject"] for m in mail_service.OUTBOX)
    # la page publique /recette/{id} montre aussi la photo
    from backend.services.seo_pages import recipe_image
    assert recipe_image(WITHOUT_PHOTO) == f"/images/recipes/{slug}.jpg"


def test_photo_acceptee_remplace_celle_du_site_puis_retrait(env):
    c, who, _ = env
    rid, slug = WITH_PHOTO["id"], pp._slug(WITH_PHOTO)
    site = c.get(f"/images/recipes/{slug}.jpg").content
    pid = _propose(c, rid).json()["id"]
    who["email"] = MOD
    assert c.get("/photo-proposals/moderation/queue").json()["results"][0]["current_photo_url"]
    c.post(f"/photo-proposals/moderation/{pid}/approve", json={})
    assert c.get(f"/images/recipes/{slug}.jpg").content != site

    # retrait par la modération : motif obligatoire, la photo du site revient
    assert c.post(f"/photo-proposals/moderation/{pid}/remove", json={"message": "court"}).status_code == 422
    res = c.post(f"/photo-proposals/moderation/{pid}/remove", json={"message": "Ce n'est pas le bon plat."})
    assert res.status_code == 200
    assert c.get(f"/images/recipes/{slug}.jpg").content == site
    assert c.get(f"/photo-proposals/recipe/{rid}").json()["credit"] is None


def test_une_nouvelle_photo_acceptee_remplace_la_precedente(env):
    c, who, Session = env
    rid, slug = WITHOUT_PHOTO["id"], pp._slug(WITHOUT_PHOTO)
    first = _propose(c, rid, data=_jpeg((10, 200, 10))).json()["id"]
    who["email"] = OTHER
    second = _propose(c, rid, name="Max", data=_jpeg((10, 10, 200))).json()["id"]
    who["email"] = MOD
    c.post(f"/photo-proposals/moderation/{first}/approve", json={})
    c.post(f"/photo-proposals/moderation/{second}/approve", json={})
    assert c.get(f"/photo-proposals/recipe/{rid}").json()["credit"]["author_name"] == "Max"
    from backend.db.models import PhotoSubmission
    with Session() as db:
        assert db.get(PhotoSubmission, first).status == "replaced"


def test_refus_avec_motif(env):
    from backend.services import mail_service
    c, who, _ = env
    pid = _propose(c, WITHOUT_PHOTO["id"]).json()["id"]
    who["email"] = MOD
    assert c.post(f"/photo-proposals/moderation/{pid}/reject", json={"message": ""}).status_code == 422
    mail_service.OUTBOX.clear()
    res = c.post(f"/photo-proposals/moderation/{pid}/reject", json={"message": "On voit de la viande au fond."})
    assert res.status_code == 200 and res.json()["status"] == "rejected"
    mail = next(m for m in mail_service.OUTBOX if MEMBER in m["to"])
    assert "pas été retenue" in mail["subject"] and "viande" in mail["text"]
    who["email"] = MEMBER
    mine = c.get("/photo-proposals/mine").json()["results"]
    assert mine[0]["status"] == "rejected" and "viande" in mine[0]["moderator_note"]


def test_garde_fous(env):
    c, _, _ = env
    rid = WITHOUT_PHOTO["id"]
    assert _propose(c, rid, consent=False).status_code == 422
    assert _propose(c, rid, ctype="image/gif").status_code == 415
    assert _propose(c, rid, data=b"pas une image").status_code == 422
    assert _propose(c, "recette_qui_n_existe_pas").status_code == 404
    assert _propose(c, rid, name="L").status_code == 422
    assert _propose(c, rid).status_code == 201
    assert _propose(c, rid).status_code == 409                # déjà une en attente pour ce plat
    assert c.get("/images/recipes/..%2F..%2Fsecret.jpg").status_code == 404
    # les autres fichiers du dossier (crédits) restent servis par le montage statique
    if (pp._ROOT / "frontend" / "dist" / "images" / "recipes" / "_credits.json").exists():
        assert c.get("/images/recipes/_credits.json").status_code == 200


def test_retirer_ma_photo(env):
    c, who, _ = env
    rid, slug = WITHOUT_PHOTO["id"], pp._slug(WITHOUT_PHOTO)
    pid = _propose(c, rid).json()["id"]
    who["email"] = MOD
    c.post(f"/photo-proposals/moderation/{pid}/approve", json={})
    who["email"] = OTHER
    assert c.delete(f"/photo-proposals/{pid}").status_code == 404     # pas la sienne
    who["email"] = MEMBER
    assert c.delete(f"/photo-proposals/{pid}").status_code == 204
    assert c.get(f"/images/recipes/{slug}.jpg").status_code == 404


def test_compte_supprime_la_photo_publiee_reste_avec_son_pseudo(env):
    from backend.db.models import PhotoSubmission, User
    from backend.services import mail_service
    c, who, Session = env
    rid, slug = WITHOUT_PHOTO["id"], pp._slug(WITHOUT_PHOTO)
    published = _propose(c, rid).json()["id"]
    pending = _propose(c, WITH_PHOTO["id"]).json()["id"]
    who["email"] = MOD
    c.post(f"/photo-proposals/moderation/{published}/approve", json={})

    with Session() as db:
        assert pp.delete_user_photos(db, MEMBER) == 1                # seule la proposition en attente est effacée
        db.delete(db.get(User, MEMBER))                               # puis le compte (FK : SET NULL)
        db.commit()
        kept = db.get(PhotoSubmission, published)
        assert kept.user_email is None and kept.author_name == "Léa"
        assert db.get(PhotoSubmission, pending) is None
    assert c.get(f"/images/recipes/{slug}.jpg").status_code == 200
    assert c.get(f"/photo-proposals/recipe/{rid}").json()["credit"]["author_name"] == "Léa"

    # la modération peut encore la retirer ; personne à prévenir
    mail_service.OUTBOX.clear()
    queue = c.get("/photo-proposals/moderation/queue?status=approved").json()["results"]
    assert queue[0]["user_email"] is None
    res = c.post(f"/photo-proposals/moderation/{published}/remove", json={"message": "Photo floue, on la retire."})
    assert res.status_code == 200 and not mail_service.OUTBOX
    assert c.get(f"/images/recipes/{slug}.jpg").status_code == 404
