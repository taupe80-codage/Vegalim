"""
routes/photo_proposals.py — Photos de plats proposées par les membres.

Membre connecté :
  POST   /photo-proposals/{recipe_id}       proposer une photo (corps brut image/jpeg|png|webp,
                                            ?author_name=…&consent=true)
  GET    /photo-proposals/mine              mes photos proposées
  DELETE /photo-proposals/{id}              retirer ma proposition (ou ma photo publiée)

Public :
  GET    /photo-proposals/recipe/{recipe_id}  crédit de la photo publiée (+ ma proposition en cours)
  GET    /photo-proposals/credits             toutes les photos publiées des membres
  GET    /images/recipes/{slug}.jpg           photo d'une recette : celle d'un membre si
                                              elle a été acceptée, sinon celle du site

Modération (ADMIN_EMAILS) :
  GET    /photo-proposals/moderation/queue?status=submitted|approved|rejected
  POST   /photo-proposals/moderation/{id}/approve   devient la photo de la recette
  POST   /photo-proposals/moderation/{id}/reject    motif obligatoire
  POST   /photo-proposals/moderation/{id}/remove    retirer une photo publiée (motif obligatoire)

La photo est ré-encodée en JPEG sans métadonnées (contribution_service.save_photo).
Acceptée, elle est copiée en user_content/recipe_photos/<slug>.jpg, dossier
servi avant les photos du dépôt : la fiche, les cartes et les pages /recette
la montrent à la même adresse, sans reconstruire le site.
"""
from __future__ import annotations

import logging
import re
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.routes.contributions import is_moderator, require_moderator, wants_email
from backend.core.auth_deps import get_optional_user, get_user
from backend.core.rate_limiter import check_rate_limit
from backend.db.models import PhotoSubmission
from backend.db.session import get_db
from backend.services import contribution_service as cs
from backend.services import mail_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Photos proposées"])

_ROOT = Path(__file__).resolve().parents[3]
RECIPE_PHOTO_DIR = _ROOT / "backend" / "data" / "user_content" / "recipe_photos"
# Photos du site : le build (dist) s'il existe, sinon les sources (dev sans build)
SITE_PHOTO_DIRS = [_ROOT / "frontend" / "dist" / "images" / "recipes",
                   _ROOT / "frontend" / "public" / "images" / "recipes"]

STATUSES = ("submitted", "approved", "rejected")
MAX_PENDING_PER_USER = 5
_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_SLUG_RE = re.compile(r"[a-z0-9-]{1,200}")


class MessagePayload(BaseModel):
    message: str = Field(default="", max_length=1500)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _catalogue_recipe(recipe_id: str) -> dict:
    from backend.core.data_io import load_catalogue_recipes
    rec = next((r for r in load_catalogue_recipes() if r.get("id") == recipe_id), None)
    if rec is None:
        raise HTTPException(status_code=404, detail="Recette introuvable (les recettes proposées par les "
                                                    "membres gardent la photo de leur auteur).")
    return rec


def _slug(rec: dict) -> str:
    from backend.services.seo_pages import slugify
    t = rec.get("titles") or {}
    return slugify(t.get("fr") or t.get("en") or t.get("original") or "")


def member_photo(slug: str) -> Path | None:
    p = RECIPE_PHOTO_DIR / f"{slug}.jpg"
    return p if slug and p.exists() else None


def site_photo(slug: str) -> Path | None:
    for d in SITE_PHOTO_DIRS:
        p = d / f"{slug}.jpg"
        if slug and p.exists():
            return p
    return None


def _serialize(s: PhotoSubmission, *, for_moderator: bool = False) -> dict:
    out = {
        "id": s.id, "recipe_id": s.recipe_id, "recipe_title": s.recipe_title,
        "author_name": s.author_name, "status": s.status,
        "photo_url": cs.photo_url(s.photo_token),
        "moderator_note": s.moderator_note,
        "created_at": _iso(s.created_at), "reviewed_at": _iso(s.reviewed_at),
    }
    if for_moderator:
        out["user_email"] = s.user_email
        out["current_photo_url"] = f"/images/recipes/{s.recipe_slug}.jpg" if (
            member_photo(s.recipe_slug) or site_photo(s.recipe_slug)) else None
        out["current_is_member_photo"] = bool(member_photo(s.recipe_slug))
    return out


def _unpublish_file(s: PhotoSubmission) -> None:
    """Retire le fichier publié d'une photo acceptée (la recette retrouve la photo du site)."""
    p = member_photo(s.recipe_slug)
    if p:
        try:
            p.unlink()
        except OSError:
            logger.warning("photo publiée non supprimée : %s", p, exc_info=True)


def _require_message(message: str) -> str:
    text = cs._text(message, 1500, multiline=True)
    if len(text) < 10:
        raise HTTPException(status_code=422, detail="Expliquez la raison au membre (10 caractères au moins).")
    return text


# ── E-mails et notifications ─────────────────────────────────────────────────

_MAILS = {
    "approved": ("Votre photo de « {title} » est en ligne",
                 ["Merci ! Votre photo de la recette « {title} » a été relue : c'est désormais la photo "
                  "de la recette, avec votre pseudo {author}."],
                 ("Voir la recette", "/recette/{rid}")),
    "rejected": ("Votre photo de « {title} » n'a pas été retenue",
                 ["Votre photo de la recette « {title} » n'a pas été retenue.", "Motif :\n{note}"],
                 ("Mes recettes", "/mes-recettes")),
    "removed":  ("Votre photo de « {title} » a été retirée",
                 ["Votre photo de la recette « {title} » a été retirée du site.", "Motif :\n{note}"],
                 ("Mes recettes", "/mes-recettes")),
}


def _send(background: BackgroundTasks | None, *args) -> None:
    if background is not None:
        background.add_task(mail_service.send, *args)
    else:
        mail_service.send(*args)


def notify_member(background: BackgroundTasks | None, db: Session, s: PhotoSubmission, kind: str) -> None:
    from backend.services import notification_service
    subject, paragraphs, link = _MAILS[kind]
    values = {"title": s.recipe_title, "author": s.author_name, "note": s.moderator_note or "",
              "rid": s.recipe_id}
    notification_service.push(db, s.user_email, f"photo.{kind}", subject.format(**values),
                              s.moderator_note or None, link[1].format(**values))
    if wants_email(db, s.user_email):
        _send(background, s.user_email, subject.format(**values), [p.format(**values) for p in paragraphs],
              (link[0], mail_service.app_url(link[1].format(**values))))


def notify_moderators(background: BackgroundTasks | None, db: Session, s: PhotoSubmission) -> None:
    from backend.core.config import settings
    from backend.services import notification_service
    if not settings.admin_emails:
        return
    title = f"Photo à relire : « {s.recipe_title} »"
    for email in sorted(settings.admin_emails):
        notification_service.push(db, email, "moderation.photo", title,
                                  f"Proposée par {s.author_name}.", "/moderation")
    _send(background, sorted(settings.admin_emails), title,
          [f"{s.author_name} propose une photo pour la recette « {s.recipe_title} »."],
          ("Ouvrir la modération", mail_service.app_url("/moderation")))


# ── Photo servie aux pages ────────────────────────────────────────────────────

# Seules les .jpg passent ici : _credits.json et les autres fichiers du dossier
# restent servis par le montage statique /images (main.py).
@router.get("/images/recipes/{slug}.jpg", include_in_schema=False)
def recipe_image(slug: str):
    """Photo d'une recette : celle d'un membre si elle a été acceptée, sinon celle du site. **Public.**"""
    if not _SLUG_RE.fullmatch(slug):
        raise HTTPException(status_code=404, detail="Photo introuvable")
    path = member_photo(slug) or site_photo(slug)
    if not path:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    # revalidation courte : une photo acceptée remplace l'ancienne à la même adresse
    return FileResponse(str(path), media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=3600"})


# ── Membre ────────────────────────────────────────────────────────────────────

@router.post("/photo-proposals/{recipe_id}", status_code=status.HTTP_201_CREATED)
async def propose_photo(recipe_id: str, request: Request, background: BackgroundTasks,
                        author_name: str = Query(..., min_length=2, max_length=40),
                        consent: bool = Query(default=False),
                        user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Propose une photo pour un plat du catalogue (corps brut de l'image). Relue avant publication."""
    check_rate_limit(request, limit=10, window_seconds=600, email=user["email"])
    if not consent:
        raise HTTPException(status_code=422, detail="Cochez la case : la photo doit être la vôtre et vous "
                                                    "acceptez sa publication avec votre pseudo.")
    rec = _catalogue_recipe(recipe_id)
    pseudo = cs._text(author_name, 40)
    if len(pseudo) < 2:
        raise HTTPException(status_code=422, detail="Indiquez un pseudo (2 caractères au moins).")
    mine = db.query(PhotoSubmission).filter(PhotoSubmission.user_email == user["email"],
                                            PhotoSubmission.status == "submitted")
    if mine.filter(PhotoSubmission.recipe_id == recipe_id).count():
        raise HTTPException(status_code=409, detail="Vous avez déjà une photo en relecture pour cette recette.")
    if mine.count() >= MAX_PENDING_PER_USER:
        raise HTTPException(status_code=429, detail=f"{MAX_PENDING_PER_USER} photos au plus en attente de "
                                                    "relecture : patientez un peu.")
    ctype = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ctype not in _IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Format accepté : JPEG, PNG ou WebP.")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > cs.LIMITS["photo_max_bytes"]:
        raise HTTPException(status_code=413, detail="Photo trop lourde (8 Mo maximum).")
    try:
        token = cs.save_photo(await request.body())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    s = PhotoSubmission(id=str(uuid.uuid4()), recipe_id=recipe_id, recipe_slug=_slug(rec),
                        recipe_title=(rec.get("titles") or {}).get("fr") or recipe_id,
                        user_email=user["email"], author_name=pseudo, photo_token=token,
                        status="submitted", created_at=_now())
    db.add(s)
    db.commit()
    db.refresh(s)
    notify_moderators(background, db, s)
    return _serialize(s)


@router.get("/photo-proposals/mine")
def my_photos(user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Mes photos proposées, les plus récentes d'abord."""
    subs = (db.query(PhotoSubmission).filter(PhotoSubmission.user_email == user["email"])
              .order_by(PhotoSubmission.created_at.desc()).limit(200).all())
    return {"results": [_serialize(s) for s in subs]}


@router.delete("/photo-proposals/{pid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_photo(pid: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Retire ma proposition ; une photo déjà publiée quitte aussi la fiche."""
    s = db.get(PhotoSubmission, pid)
    if not s or s.user_email != user["email"]:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    if s.status == "approved":
        _unpublish_file(s)
    cs.delete_photo(s.photo_token)
    db.delete(s)
    db.commit()


@router.get("/photo-proposals/recipe/{recipe_id}")
def recipe_photo_info(recipe_id: str, user: dict | None = Depends(get_optional_user),
                      db: Session = Depends(get_db)):
    """Crédit de la photo d'un membre (s'il y en a une) et ma proposition en cours. **Public.**"""
    approved = (db.query(PhotoSubmission)
                  .filter(PhotoSubmission.recipe_id == recipe_id, PhotoSubmission.status == "approved")
                  .order_by(PhotoSubmission.reviewed_at.desc()).first())
    credit = None
    if approved and member_photo(approved.recipe_slug):
        credit = {"author_name": approved.author_name, "approved_at": _iso(approved.reviewed_at)}
    pending = None
    if user and user.get("email"):
        mine = (db.query(PhotoSubmission)
                  .filter(PhotoSubmission.recipe_id == recipe_id, PhotoSubmission.user_email == user["email"],
                          PhotoSubmission.status == "submitted").first())
        pending = _serialize(mine) if mine else None
    return {"credit": credit, "my_pending": pending}


@router.get("/photo-proposals/credits")
def photo_credits(db: Session = Depends(get_db)):
    """Photos des membres publiées sur le site (page Crédits). **Public.**"""
    subs = (db.query(PhotoSubmission).filter(PhotoSubmission.status == "approved")
              .order_by(PhotoSubmission.recipe_title).all())
    return {"results": [{"recipe_id": s.recipe_id, "recipe_title": s.recipe_title, "slug": s.recipe_slug,
                         "author_name": s.author_name, "approved_at": _iso(s.reviewed_at)}
                        for s in subs if member_photo(s.recipe_slug)]}


# ── Modération ────────────────────────────────────────────────────────────────

@router.get("/photo-proposals/moderation/queue")
def moderation_queue(status_filter: str = Query(default="submitted", alias="status"),
                     _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Photos par statut ; « submitted » : la plus ancienne d'abord."""
    if status_filter not in STATUSES:
        raise HTTPException(status_code=400, detail="Statut inconnu")
    q = db.query(PhotoSubmission).filter(PhotoSubmission.status == status_filter)
    q = q.order_by(PhotoSubmission.created_at if status_filter == "submitted"
                   else PhotoSubmission.reviewed_at.desc())
    counts = {k: db.query(PhotoSubmission).filter(PhotoSubmission.status == k).count() for k in STATUSES}
    return {"status": status_filter, "counts": counts,
            "results": [_serialize(s, for_moderator=True) for s in q.limit(200).all()]}


def _get_pending(db: Session, pid: str) -> PhotoSubmission:
    s = db.get(PhotoSubmission, pid)
    if not s:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    if s.status != "submitted":
        raise HTTPException(status_code=409, detail="Cette photo n'est plus en attente de relecture.")
    return s


@router.post("/photo-proposals/moderation/{pid}/approve")
def moderation_approve(pid: str, background: BackgroundTasks, payload: MessagePayload = MessagePayload(),
                       mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Accepte la photo : elle remplace la photo actuelle de la recette."""
    s = _get_pending(db, pid)
    src = cs.photo_path(s.photo_token)
    if not src:
        raise HTTPException(status_code=410, detail="Le fichier de cette photo a disparu.")
    RECIPE_PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    tmp = RECIPE_PHOTO_DIR / f"{s.recipe_slug}.jpg.tmp"
    shutil.copyfile(src, tmp)
    tmp.replace(RECIPE_PHOTO_DIR / f"{s.recipe_slug}.jpg")
    for old in (db.query(PhotoSubmission)
                  .filter(PhotoSubmission.recipe_id == s.recipe_id, PhotoSubmission.status == "approved",
                          PhotoSubmission.id != s.id).all()):
        old.status = "replaced"
    s.status = "approved"
    s.reviewed_at = _now()
    s.moderator_email = mod["email"]
    s.moderator_note = cs._text(payload.message, 1500, multiline=True) or None
    db.commit()
    db.refresh(s)
    notify_member(background, db, s, "approved")
    return _serialize(s, for_moderator=True)


@router.post("/photo-proposals/moderation/{pid}/reject")
def moderation_reject(pid: str, payload: MessagePayload, background: BackgroundTasks,
                      mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Refuse la photo avec un motif envoyé au membre."""
    s = _get_pending(db, pid)
    s.moderator_note = _require_message(payload.message)
    s.status = "rejected"
    s.reviewed_at = _now()
    s.moderator_email = mod["email"]
    db.commit()
    db.refresh(s)
    notify_member(background, db, s, "rejected")
    return _serialize(s, for_moderator=True)


@router.post("/photo-proposals/moderation/{pid}/remove")
def moderation_remove(pid: str, payload: MessagePayload, background: BackgroundTasks,
                      mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Retire une photo publiée : la recette retrouve la photo du site (ou aucune)."""
    s = db.get(PhotoSubmission, pid)
    if not s or s.status != "approved":
        raise HTTPException(status_code=409, detail="Cette photo n'est pas publiée.")
    s.moderator_note = _require_message(payload.message)
    _unpublish_file(s)
    s.status = "rejected"
    s.reviewed_at = _now()
    s.moderator_email = mod["email"]
    db.commit()
    db.refresh(s)
    notify_member(background, db, s, "removed")
    return _serialize(s, for_moderator=True)


# ── Suppression du compte ─────────────────────────────────────────────────────

def delete_user_photos(db: Session, email: str) -> int:
    """RGPD : propositions et photos publiées du membre."""
    subs = db.query(PhotoSubmission).filter(PhotoSubmission.user_email == email).all()
    for s in subs:
        if s.status == "approved":
            _unpublish_file(s)
        cs.delete_photo(s.photo_token)
        db.delete(s)
    db.commit()
    return len(subs)


__all__ = ["router", "delete_user_photos", "member_photo", "site_photo", "is_moderator"]
