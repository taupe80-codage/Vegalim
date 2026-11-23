"""
routes/contributions.py — Recettes proposées par les utilisateurs.

Contributeur (compte connecté) :
  GET    /contributions/options              listes du formulaire (public)
  POST   /contributions/analyse              vérifications pendant la saisie
  POST   /contributions/ingredients/parse    « 200 g de farine » → lignes
  GET    /contributions/ingredients/suggest  suggestions du catalogue
  GET    /contributions/mine                 mes propositions
  GET|PUT /contributions/preferences         e-mails de suivi (oui / non)
  POST   /contributions                      nouveau brouillon
  GET    /contributions/{id}                 une proposition
  PUT    /contributions/{id}                 enregistrer (brouillon, à corriger,
                                             ou modification d'une recette publiée)
  DELETE /contributions/{id}                 supprimer (retire aussi la recette publiée)
  DELETE /contributions/{id}/revision        abandonner la modification en cours
  POST   /contributions/{id}/submit          envoyer en relecture
  PUT    /contributions/{id}/photo           photo (corps brut image/jpeg|png|webp)
  DELETE /contributions/{id}/photo
  GET    /contributions/photos/{token}.jpg   photo (public)

Modération (compte dont l'email figure dans ADMIN_EMAILS) :
  GET    /contributions/moderation/queue
  GET    /contributions/moderation/{id}
  PUT    /contributions/moderation/{id}      corriger (rattacher un ingrédient…)
  POST   /contributions/moderation/{id}/publish
  POST   /contributions/moderation/{id}/request-changes
  POST   /contributions/moderation/{id}/reject
  POST   /contributions/moderation/{id}/unpublish

Recette déjà publiée : l'auteur peut la modifier. La version en ligne reste
affichée ; la modification (revision_*) est relue comme une nouvelle
proposition puis remplace la version en ligne, à la même adresse.

Chaque décision de la modération est envoyée par e-mail à l'auteur (s'il ne
l'a pas désactivé) ; chaque envoi en relecture prévient la modération.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import or_, and_
from sqlalchemy.orm import Session

from backend.core.auth_deps import get_user, get_optional_user
from backend.core.rate_limiter import check_rate_limit
from backend.db.models import RecipeSubmission, User, as_utc
from backend.db.session import get_db
from backend.services import contribution_service as cs
from backend.services import mail_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contributions", tags=["Recettes proposées"])

MAX_OPEN_PER_USER = 20       # brouillons + en relecture + à corriger
MAX_PENDING_PER_USER = 5     # envoyées en attente de relecture
PHOTO_REMOVED = "-"          # révision : retirer la photo à la publication

REVISION_STATUSES = {
    "draft":             "Modification en cours",
    "submitted":         "Modification en relecture",
    "changes_requested": "Modification à corriger",
}

# Libellés des champs comparés entre la version en ligne et la modification
_FIELD_LABELS = {
    "title": "titre", "description": "présentation", "diet": "régime",
    "dish_type": "type de plat", "cuisine": "cuisine", "difficulty": "difficulté",
    "servings": "portions", "prep_min": "préparation", "cook_min": "cuisson",
    "rest_min": "repos", "ingredients": "ingrédients", "steps": "étapes", "tip": "astuce",
}


# ── Droits ────────────────────────────────────────────────────────────────────

def is_moderator(email: str | None) -> bool:
    from backend.core.config import settings
    return bool(email) and str(email).lower() in settings.admin_emails


def require_moderator(user: dict = Depends(get_user)) -> dict:
    if not is_moderator(user.get("email")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès réservé à la modération")
    return user


# ── Modèles ───────────────────────────────────────────────────────────────────

class DraftPayload(BaseModel):
    data:        dict          = Field(default_factory=dict)
    author_name: Optional[str] = Field(default=None, max_length=60)


class SubmitPayload(BaseModel):
    author_name: str  = Field(..., max_length=60)
    consent:     bool = Field(default=False, description="L'auteur certifie que la recette est la sienne")


class ParsePayload(BaseModel):
    text: str = Field(..., max_length=6000)


class MessagePayload(BaseModel):
    message: str = Field(default="", max_length=1500)


class PreferencesPayload(BaseModel):
    email_notifications: bool


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return as_utc(dt).isoformat() if dt else None


def _author(name: str | None) -> str:
    return cs._text(name, cs.LIMITS["author_max"])


def _is_published(sub: RecipeSubmission) -> bool:
    return sub.status == "published"


def _editable(sub: RecipeSubmission) -> bool:
    """Modifiable par l'auteur : brouillon, à corriger, ou publiée sans modification en relecture."""
    if _is_published(sub):
        return sub.revision_status != "submitted"
    return sub.status in cs.EDITABLE_STATUSES


def _revision_form(sub: RecipeSubmission) -> dict:
    """Formulaire de la modification (sans la clé technique du pseudo)."""
    return {k: v for k, v in (sub.revision_data or {}).items() if not k.startswith("_")}


def _revision_photo_url(sub: RecipeSubmission) -> str | None:
    tok = sub.revision_photo_token
    if tok == PHOTO_REMOVED:
        return None
    return cs.photo_url(tok) if tok else cs.photo_url(sub.photo_token)


def _changed_fields(old: dict, new: dict) -> list[str]:
    a, b = cs.normalize(old), cs.normalize(new)
    return [label for key, label in _FIELD_LABELS.items() if a.get(key) != b.get(key)]


def _serialize(sub: RecipeSubmission, *, for_moderator: bool = False) -> dict:
    out = {
        "id": sub.id,
        "status": sub.status,
        "status_label": cs.STATUSES.get(sub.status, sub.status),
        "editable": _editable(sub),
        "title": sub.title,
        "author_name": sub.author_name or "",
        "data": sub.data or {},
        "photo_url": cs.photo_url(sub.photo_token),
        "moderator_note": sub.moderator_note or "",
        "published_recipe_id": sub.published_recipe_id,
        "created_at": _iso(sub.created_at),
        "updated_at": _iso(sub.updated_at),
        "submitted_at": _iso(sub.submitted_at),
        "reviewed_at": _iso(sub.reviewed_at),
        "revision": None,
    }
    if sub.revision_status:
        out["revision"] = {
            "status": sub.revision_status,
            "status_label": REVISION_STATUSES.get(sub.revision_status, sub.revision_status),
            "data": _revision_form(sub),
            "author_name": (sub.revision_data or {}).get("_author_name") or sub.author_name or "",
            "photo_url": _revision_photo_url(sub),
            "submitted_at": _iso(sub.revision_submitted_at),
            "changes": _changed_fields(sub.data or {}, _revision_form(sub)),
        }
    if for_moderator:
        out["user_email"] = sub.user_email
    return out


def _get_own(db: Session, sid: str, email: str) -> RecipeSubmission:
    sub = db.get(RecipeSubmission, sid)
    if not sub or sub.user_email != email:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    return sub


def _get_any(db: Session, sid: str) -> RecipeSubmission:
    sub = db.get(RecipeSubmission, sid)
    if not sub:
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    return sub


def _set_data(sub: RecipeSubmission, data: dict) -> None:
    clean = cs.normalize(data)
    sub.data = clean
    sub.title = clean["title"][:120]


def _set_revision(sub: RecipeSubmission, data: dict, author_name: str | None = None) -> None:
    clean = cs.normalize(data)
    pseudo = (sub.revision_data or {}).get("_author_name")
    if author_name is not None:
        pseudo = _author(author_name) or None
    if pseudo:
        clean["_author_name"] = pseudo
    sub.revision_data = clean
    if sub.revision_status not in {"changes_requested"}:
        sub.revision_status = "draft"


def _discard_revision(sub: RecipeSubmission) -> None:
    if sub.revision_photo_token and sub.revision_photo_token != PHOTO_REMOVED:
        cs.delete_photo(sub.revision_photo_token)
    sub.revision_data = None
    sub.revision_status = None
    sub.revision_photo_token = None
    sub.revision_submitted_at = None


def _apply_revision(sub: RecipeSubmission) -> None:
    """La modification relue remplace la version en ligne (même adresse)."""
    rev = sub.revision_data or {}
    if rev.get("_author_name"):
        sub.author_name = rev["_author_name"]
    _set_data(sub, _revision_form(sub))
    tok = sub.revision_photo_token
    if tok:
        cs.delete_photo(sub.photo_token)
        sub.photo_token = None if tok == PHOTO_REMOVED else tok
        sub.revision_photo_token = None          # déjà déplacée : ne pas la supprimer
    _discard_revision(sub)


def _pending_review(sub: RecipeSubmission) -> bool:
    return sub.status == "submitted" or (_is_published(sub) and sub.revision_status == "submitted")


def _form_under_review(sub: RecipeSubmission) -> dict:
    return _revision_form(sub) if (_is_published(sub) and sub.revision_status) else (sub.data or {})


def rebuild_community_file(db: Session) -> int:
    """Régénère community_recipes.json depuis les propositions publiées."""
    from backend.core import data_io
    subs = (db.query(RecipeSubmission)
              .filter(RecipeSubmission.status == "published")
              .order_by(RecipeSubmission.reviewed_at)
              .all())
    recipes = []
    for s in subs:
        r = cs.build_recipe(s.data or {}, submission_id=s.id, author_name=s.author_name or "",
                            photo_url=cs.photo_url(s.photo_token),
                            published_at=_iso(s.reviewed_at))
        if s.published_recipe_id:
            r["id"] = s.published_recipe_id     # adresse stable même si le titre change
        recipes.append(r)
    cs.write_community_file(recipes, data_io.COMMUNITY_RECIPES_PATH)
    data_io.load_recipes.cache_clear()
    return len(recipes)


def delete_user_contributions(db: Session, email: str) -> int:
    """Suppression du compte (RGPD) : propositions, photos et recettes publiées."""
    subs = db.query(RecipeSubmission).filter(RecipeSubmission.user_email == email).all()
    had_published = any(s.status == "published" for s in subs)
    for s in subs:
        _discard_revision(s)
        cs.delete_photo(s.photo_token)
        db.delete(s)
    db.commit()
    if had_published:
        rebuild_community_file(db)
    return len(subs)


# ── E-mails ───────────────────────────────────────────────────────────────────

def wants_email(db: Session, email: str) -> bool:
    user = db.get(User, email)
    return bool(user is None or user.email_notifications)


_AUTHOR_MAILS = {
    "published": (
        "Votre recette « {title} » est publiée",
        ["Bonne nouvelle : votre recette « {title} » a été relue et publiée sur ALIM, sous le nom {author}.",
         "Merci de partager votre cuisine !"],
        ("Voir la recette", "/recette/{rid}"),
    ),
    "changes_requested": (
        "Votre recette « {title} » : quelques corrections",
        ["L'équipe a relu votre recette « {title} » et vous demande quelques modifications avant de la publier.",
         "Message de l'équipe :\n{note}"],
        ("Corriger ma recette", "/proposer/{sid}"),
    ),
    "rejected": (
        "Votre recette « {title} » n'a pas été retenue",
        ["Votre recette « {title} » n'a pas été retenue pour publication.", "Motif :\n{note}"],
        ("Mes recettes", "/mes-recettes"),
    ),
    "unpublished": (
        "Votre recette « {title} » est retirée en attendant des corrections",
        ["Votre recette « {title} » a été retirée du site le temps de quelques corrections.",
         "Message de l'équipe :\n{note}"],
        ("Corriger ma recette", "/proposer/{sid}"),
    ),
    "revision_published": (
        "Vos modifications de « {title} » sont en ligne",
        ["Vos modifications de la recette « {title} » ont été relues : la nouvelle version est en ligne."],
        ("Voir la recette", "/recette/{rid}"),
    ),
    "revision_changes_requested": (
        "Vos modifications de « {title} » : quelques corrections",
        ["L'équipe a relu vos modifications de « {title} ». La version en ligne reste inchangée en attendant.",
         "Message de l'équipe :\n{note}"],
        ("Reprendre mes modifications", "/proposer/{sid}"),
    ),
    "revision_rejected": (
        "Vos modifications de « {title} » n'ont pas été retenues",
        ["Vos modifications de la recette « {title} » n'ont pas été retenues ; la version en ligne reste inchangée.",
         "Motif :\n{note}"],
        ("Mes recettes", "/mes-recettes"),
    ),
}


def notify_author(background: BackgroundTasks | None, db: Session, sub: RecipeSubmission, kind: str) -> None:
    """Décision de la modération : notification dans l'application, et e-mail
    à l'auteur sauf s'il les a désactivés."""
    from backend.services import notification_service
    if kind not in _AUTHOR_MAILS:
        return
    subject, paragraphs, link = _AUTHOR_MAILS[kind]
    values = {"title": sub.title or "sans titre", "author": sub.author_name or "vous",
              "note": sub.moderator_note or "", "rid": sub.published_recipe_id or "", "sid": sub.id}
    notification_service.push(db, sub.user_email, f"contribution.{kind}", subject.format(**values),
                              sub.moderator_note or None, link[1].format(**values))
    if not wants_email(db, sub.user_email):
        return
    args = (sub.user_email, subject.format(**values), [p.format(**values) for p in paragraphs],
            (link[0], mail_service.app_url(link[1].format(**values))))
    if background is not None:
        background.add_task(mail_service.send, *args)
    else:
        mail_service.send(*args)


def notify_moderators(background: BackgroundTasks | None, db: Session, sub: RecipeSubmission, *,
                      revision: bool) -> None:
    from backend.core.config import settings
    from backend.services import notification_service
    if not settings.admin_emails:
        return
    what = "Modification d'une recette publiée" if revision else "Nouvelle recette"
    for email in sorted(settings.admin_emails):
        notification_service.push(db, email, "moderation.submitted", f"{what} à relire : « {sub.title} »",
                                  f"Proposée par {sub.author_name or 'un membre'}.", "/moderation")
    args = (sorted(settings.admin_emails), f"{what} à relire : « {sub.title} »",
            [f"{what} proposée par {sub.author_name or 'un membre'} : « {sub.title} »."],
            ("Ouvrir la modération", mail_service.app_url("/moderation")))
    if background is not None:
        background.add_task(mail_service.send, *args)
    else:
        mail_service.send(*args)


# ── Formulaire ────────────────────────────────────────────────────────────────

@router.get("/options")
def get_options(user: dict | None = Depends(get_optional_user)):
    """Listes et bornes du formulaire. **Public.**"""
    out = cs.options()
    out["is_moderator"] = is_moderator((user or {}).get("email"))
    out["revision_statuses"] = REVISION_STATUSES
    return out


@router.post("/analyse")
def analyse(payload: DraftPayload, request: Request, user: dict = Depends(get_user)):
    """Vérifications automatiques d'un formulaire (sans l'enregistrer)."""
    check_rate_limit(request, limit=90, window_seconds=60, email=user["email"])
    return cs.analyze(payload.data, author_name=_author(payload.author_name))


@router.post("/ingredients/parse")
def parse_ingredients(payload: ParsePayload, request: Request, user: dict = Depends(get_user)):
    """Liste collée (une ligne par ingrédient) → lignes structurées + suggestions."""
    check_rate_limit(request, limit=30, window_seconds=60, email=user["email"])
    return {"lines": cs.parse_ingredient_lines(payload.text)}


@router.get("/ingredients/suggest")
def suggest_ingredients(request: Request, q: str = Query(..., min_length=1, max_length=80),
                        user: dict = Depends(get_user)):
    """Suggestions du catalogue, avec la précision qui distingue les homonymes."""
    check_rate_limit(request, limit=120, window_seconds=60, email=user["email"])
    blocked = bool(cs._NON_VEG_RE.search(q))
    return {"query": q, "non_vegetarian": blocked, "results": [] if blocked else cs.match_ingredient(q, limit=8)}


# ── Préférences ───────────────────────────────────────────────────────────────

@router.get("/preferences")
def get_preferences(user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """E-mails de suivi des recettes proposées : activés ou non."""
    return {"email_notifications": wants_email(db, user["email"]),
            "email_configured": mail_service.is_configured()}


@router.put("/preferences")
def set_preferences(payload: PreferencesPayload, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Active ou désactive les e-mails de suivi."""
    row = db.get(User, user["email"])
    if not row:
        raise HTTPException(status_code=404, detail="Compte introuvable")
    row.email_notifications = payload.email_notifications
    db.commit()
    return {"email_notifications": row.email_notifications, "email_configured": mail_service.is_configured()}


# ── Propositions de l'utilisateur ─────────────────────────────────────────────

@router.get("/mine")
def my_submissions(user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Mes propositions, de la plus récemment modifiée à la plus ancienne."""
    subs = (db.query(RecipeSubmission)
              .filter(RecipeSubmission.user_email == user["email"])
              .order_by(RecipeSubmission.updated_at.desc())
              .all())
    return {"results": [_serialize(s) for s in subs]}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_submission(payload: DraftPayload, request: Request,
                      user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Crée un brouillon (20 recettes en cours au plus par compte)."""
    check_rate_limit(request, limit=10, window_seconds=600, email=user["email"])
    open_count = (db.query(RecipeSubmission)
                    .filter(RecipeSubmission.user_email == user["email"],
                            RecipeSubmission.status.in_(["draft", "submitted", "changes_requested"]))
                    .count())
    if open_count >= MAX_OPEN_PER_USER:
        raise HTTPException(status_code=409, detail=(
            f"Vous avez déjà {open_count} recettes en cours : terminez-en ou supprimez-en avant d'en commencer une autre."))
    sub = RecipeSubmission(id=str(uuid.uuid4()), user_email=user["email"], status="draft",
                           author_name=_author(payload.author_name) or None)
    _set_data(sub, payload.data)
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return _serialize(sub)


@router.get("/{sid}")
def get_submission(sid: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Une de mes propositions."""
    return _serialize(_get_own(db, sid, user["email"]))


@router.put("/{sid}")
def update_submission(sid: str, payload: DraftPayload, request: Request,
                      user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Enregistre un brouillon, une recette « à corriger » ou la modification d'une recette publiée."""
    # enregistrement automatique toutes les 1,5 s au plus pendant la saisie
    check_rate_limit(request, limit=120, window_seconds=60, email=user["email"])
    sub = _get_own(db, sid, user["email"])
    if not _editable(sub):
        what = "sa modification est en relecture" if _is_published(sub) else \
            f"elle est « {cs.STATUSES.get(sub.status, sub.status).lower()} »"
        raise HTTPException(status_code=409, detail=f"Cette recette n'est pas modifiable pour l'instant : {what}.")
    if _is_published(sub):
        _set_revision(sub, payload.data, payload.author_name)
    else:
        _set_data(sub, payload.data)
        if payload.author_name is not None:
            sub.author_name = _author(payload.author_name) or None
    db.commit()
    db.refresh(sub)
    return _serialize(sub)


@router.delete("/{sid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_submission(sid: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Supprime une proposition ; publiée, elle quitte aussi le catalogue."""
    sub = _get_own(db, sid, user["email"])
    was_published = sub.status == "published"
    _discard_revision(sub)
    cs.delete_photo(sub.photo_token)
    db.delete(sub)
    db.commit()
    if was_published:
        rebuild_community_file(db)


@router.delete("/{sid}/revision", status_code=status.HTTP_204_NO_CONTENT)
def discard_revision(sid: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Abandonne la modification en cours d'une recette publiée (la version en ligne ne change pas)."""
    sub = _get_own(db, sid, user["email"])
    if not sub.revision_status:
        raise HTTPException(status_code=404, detail="Aucune modification en cours")
    _discard_revision(sub)
    db.commit()


@router.post("/{sid}/submit")
def submit_submission(sid: str, payload: SubmitPayload, request: Request, background: BackgroundTasks,
                      user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Envoie en relecture : consentement, pseudo et points bloquants vérifiés."""
    check_rate_limit(request, limit=10, window_seconds=3600, email=user["email"])
    sub = _get_own(db, sid, user["email"])
    revision = _is_published(sub)
    if not _editable(sub):
        raise HTTPException(status_code=409, detail="Cette recette a déjà été envoyée.")
    if revision and not sub.revision_status:
        raise HTTPException(status_code=409, detail="Aucune modification à envoyer.")
    if not payload.consent:
        raise HTTPException(status_code=422, detail=(
            "Cochez la case qui certifie que la recette est la vôtre et que vous acceptez sa publication."))
    author = _author(payload.author_name)
    if len(author) < cs.LIMITS["author_min"]:
        raise HTTPException(status_code=422, detail="Indiquez le nom ou pseudo à afficher (2 caractères au moins).")
    if cs._NON_VEG_RE.search(author) or cs._LINK_RE.search(author) or "@" in author or cs.is_reserved_name(author):
        raise HTTPException(status_code=422, detail="Ce pseudo ne peut pas être affiché : choisissez-en un autre.")
    pending = (db.query(RecipeSubmission)
                 .filter(RecipeSubmission.user_email == user["email"],
                         or_(RecipeSubmission.status == "submitted",
                             RecipeSubmission.revision_status == "submitted"))
                 .count())
    if pending >= MAX_PENDING_PER_USER:
        raise HTTPException(status_code=429, detail=(
            f"{pending} de vos recettes attendent déjà une relecture : patientez avant d'en envoyer d'autres."))
    form = _revision_form(sub) if revision else (sub.data or {})
    analysis = cs.analyze(form, submission_id=sub.id, author_name=author)
    if not analysis["ready"]:
        blocking = [i["message"] for i in analysis["issues"] if i["level"] == "blocking"]
        raise HTTPException(status_code=422, detail="À compléter avant l'envoi : " + " ".join(blocking))
    if revision:
        if not _changed_fields(sub.data or {}, form) and not sub.revision_photo_token \
                and author == (sub.author_name or ""):
            raise HTTPException(status_code=422, detail="Aucune différence avec la version en ligne.")
        sub.revision_data = {**(sub.revision_data or {}), "_author_name": author}
        sub.revision_status = "submitted"
        sub.revision_submitted_at = _now()
    else:
        sub.author_name = author
        sub.status = "submitted"
        sub.submitted_at = _now()
    db.commit()
    db.refresh(sub)
    notify_moderators(background, db, sub, revision=revision)
    return _serialize(sub)


# ── Photo ─────────────────────────────────────────────────────────────────────

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.put("/{sid}/photo")
async def upload_photo(sid: str, request: Request,
                       user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Corps brut de l'image (Content-Type image/jpeg, image/png ou image/webp)."""
    check_rate_limit(request, limit=20, window_seconds=600, email=user["email"])
    sub = _get_own(db, sid, user["email"])
    if not _editable(sub):
        raise HTTPException(status_code=409, detail="Cette recette n'est pas modifiable pour l'instant.")
    ctype = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if ctype not in _IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Format accepté : JPEG, PNG ou WebP.")
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > cs.LIMITS["photo_max_bytes"]:
        raise HTTPException(status_code=413, detail="Photo trop lourde (8 Mo maximum).")
    raw = await request.body()
    try:
        token = cs.save_photo(raw)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if _is_published(sub):
        # la photo en ligne ne change qu'à la publication de la modification
        if sub.revision_photo_token and sub.revision_photo_token != PHOTO_REMOVED:
            cs.delete_photo(sub.revision_photo_token)
        sub.revision_photo_token = token
        if not sub.revision_status:
            sub.revision_data = dict(sub.data or {})
            sub.revision_status = "draft"
    else:
        cs.delete_photo(sub.photo_token)
        sub.photo_token = token
    db.commit()
    return {"photo_url": cs.photo_url(token)}


@router.delete("/{sid}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(sid: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Retire la photo d'une proposition modifiable."""
    sub = _get_own(db, sid, user["email"])
    if not _editable(sub):
        raise HTTPException(status_code=409, detail="Cette recette n'est pas modifiable pour l'instant.")
    if _is_published(sub):
        if sub.revision_photo_token and sub.revision_photo_token != PHOTO_REMOVED:
            cs.delete_photo(sub.revision_photo_token)
        sub.revision_photo_token = PHOTO_REMOVED
        if not sub.revision_status:
            sub.revision_data = dict(sub.data or {})
            sub.revision_status = "draft"
    else:
        cs.delete_photo(sub.photo_token)
        sub.photo_token = None
    db.commit()


@router.get("/photos/{token}.jpg", include_in_schema=False)
def get_photo(token: str):
    """Photo d'une proposition (JPEG ré-encodé, sans métadonnées). **Public.**"""
    path = cs.photo_path(token)
    if not path:
        raise HTTPException(status_code=404, detail="Photo introuvable")
    return FileResponse(str(path), media_type="image/jpeg",
                        headers={"Cache-Control": "public, max-age=604800, immutable"})


# ── Modération ────────────────────────────────────────────────────────────────

def _queue_filter(status_filter: str):
    if status_filter == "submitted":
        return or_(RecipeSubmission.status == "submitted",
                   and_(RecipeSubmission.status == "published", RecipeSubmission.revision_status == "submitted"))
    return RecipeSubmission.status == status_filter


@router.get("/moderation/queue")
def moderation_queue(status_filter: str = Query(default="submitted", alias="status"),
                     _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """File de modération par statut ; « submitted » inclut les modifications de recettes publiées."""
    if status_filter not in cs.STATUSES:
        raise HTTPException(status_code=400, detail="Statut inconnu")
    subs = db.query(RecipeSubmission).filter(_queue_filter(status_filter)).limit(200).all()
    if status_filter == "submitted":
        subs.sort(key=lambda s: (s.revision_submitted_at if s.status == "published" else s.submitted_at) or s.updated_at)
    else:
        subs.sort(key=lambda s: s.updated_at, reverse=True)
    counts = {k: db.query(RecipeSubmission).filter(_queue_filter(k)).count() for k in cs.STATUSES}
    results = []
    for s in subs:
        item = _serialize(s, for_moderator=True)
        item["is_revision"] = status_filter == "submitted" and _is_published(s)
        results.append(item)
    return {"status": status_filter, "counts": counts, "results": results}


@router.get("/moderation/{sid}")
def moderation_get(sid: str, _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Proposition avec ses vérifications automatiques (sur la modification s'il y en a une)."""
    sub = _get_any(db, sid)
    out = _serialize(sub, for_moderator=True)
    out["is_revision"] = _is_published(sub) and bool(sub.revision_status)
    out["analysis"] = cs.analyze(_form_under_review(sub), submission_id=sub.id, author_name=sub.author_name or "")
    out["author_published"] = (db.query(RecipeSubmission)
                                 .filter(RecipeSubmission.user_email == sub.user_email,
                                         RecipeSubmission.status == "published").count())
    return out


@router.put("/moderation/{sid}")
def moderation_edit(sid: str, payload: DraftPayload,
                    _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Corrections de la modération (rattacher un ingrédient, coquille) avant publication."""
    sub = _get_any(db, sid)
    if not _pending_review(sub):
        raise HTTPException(status_code=409, detail="Seule une recette en relecture se corrige ici.")
    if _is_published(sub):
        pseudo = (sub.revision_data or {}).get("_author_name")
        clean = cs.normalize(payload.data)
        if pseudo:
            clean["_author_name"] = pseudo
        sub.revision_data = clean
    else:
        _set_data(sub, payload.data)
    db.commit()
    db.refresh(sub)
    return _serialize(sub, for_moderator=True)


@router.post("/moderation/{sid}/publish")
def moderation_publish(sid: str, background: BackgroundTasks, payload: MessagePayload = MessagePayload(),
                       mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Publie la recette (ou sa modification) : aucun point bloquant ni ingrédient hors base."""
    sub = _get_any(db, sid)
    if not _pending_review(sub):
        raise HTTPException(status_code=409, detail="Seule une recette en relecture peut être publiée.")
    revision = _is_published(sub)
    analysis = cs.analyze(_form_under_review(sub), submission_id=sub.id, author_name=sub.author_name or "")
    if not analysis["ready"]:
        raise HTTPException(status_code=422, detail="Points bloquants restants : " + " ".join(
            i["message"] for i in analysis["issues"] if i["level"] == "blocking"))
    if analysis["unmatched"]:
        raise HTTPException(status_code=422, detail=(
            "Rattachez d'abord ces ingrédients au catalogue : " + ", ".join(analysis["unmatched"])))
    if revision:
        _apply_revision(sub)
    else:
        sub.status = "published"
        if not sub.published_recipe_id:
            sub.published_recipe_id = cs.recipe_id_for(sub.id, sub.title)
    sub.reviewed_at = _now()
    sub.moderator_email = mod["email"]
    sub.moderator_note = cs._text(payload.message, 1500, multiline=True) or None
    db.commit()
    rebuild_community_file(db)
    db.refresh(sub)
    notify_author(background, db, sub, "revision_published" if revision else "published")
    return _serialize(sub, for_moderator=True)


def _require_message(message: str) -> str:
    text = cs._text(message, 1500, multiline=True)
    if len(text) < 10:
        raise HTTPException(status_code=422, detail="Expliquez à l'auteur ce qui doit changer (10 caractères au moins).")
    return text


def _send_back(db: Session, sub: RecipeSubmission, mod: dict, new_status: str, message: str) -> None:
    text = _require_message(message)
    was_published = sub.status == "published"
    if was_published and sub.revision_data:
        # la dernière version de l'auteur devient le brouillon à corriger
        _apply_revision(sub)
    sub.status = new_status
    sub.moderator_note = text
    sub.moderator_email = mod["email"]
    sub.reviewed_at = _now()
    db.commit()
    if was_published:
        rebuild_community_file(db)


@router.post("/moderation/{sid}/request-changes")
def moderation_request_changes(sid: str, payload: MessagePayload, background: BackgroundTasks,
                               mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Renvoie la recette (ou sa modification) à l'auteur avec un message."""
    sub = _get_any(db, sid)
    if not _pending_review(sub):
        raise HTTPException(status_code=409, detail="Seule une recette en relecture peut être renvoyée.")
    if _is_published(sub):
        sub.moderator_note = _require_message(payload.message)
        sub.revision_status = "changes_requested"
        sub.moderator_email = mod["email"]
        db.commit()
        kind = "revision_changes_requested"
    else:
        _send_back(db, sub, mod, "changes_requested", payload.message)
        kind = "changes_requested"
    db.refresh(sub)
    notify_author(background, db, sub, kind)
    return _serialize(sub, for_moderator=True)


@router.post("/moderation/{sid}/reject")
def moderation_reject(sid: str, payload: MessagePayload, background: BackgroundTasks,
                      mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Refuse la recette, ou sa modification (la version en ligne reste alors inchangée)."""
    sub = _get_any(db, sid)
    if _is_published(sub) and sub.revision_status in {"submitted", "changes_requested"}:
        sub.moderator_note = _require_message(payload.message)
        sub.moderator_email = mod["email"]
        _discard_revision(sub)
        db.commit()
        kind = "revision_rejected"
    elif sub.status in {"submitted", "changes_requested"}:
        _send_back(db, sub, mod, "rejected", payload.message)
        kind = "rejected"
    else:
        raise HTTPException(status_code=409, detail="Cette recette ne peut pas être refusée dans son état actuel.")
    db.refresh(sub)
    notify_author(background, db, sub, kind)
    return _serialize(sub, for_moderator=True)


@router.post("/moderation/{sid}/unpublish")
def moderation_unpublish(sid: str, payload: MessagePayload, background: BackgroundTasks,
                         mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Retire une recette publiée et la renvoie à son auteur avec un message."""
    sub = _get_any(db, sid)
    if sub.status != "published":
        raise HTTPException(status_code=409, detail="Cette recette n'est pas publiée.")
    _send_back(db, sub, mod, "changes_requested", payload.message)
    db.refresh(sub)
    notify_author(background, db, sub, "unpublished")
    return _serialize(sub, for_moderator=True)
