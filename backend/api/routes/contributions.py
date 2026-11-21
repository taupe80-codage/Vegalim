"""
routes/contributions.py — Recettes proposées par les utilisateurs.

Contributeur (compte connecté) :
  GET    /contributions/options              listes du formulaire (public)
  POST   /contributions/analyse              vérifications pendant la saisie
  POST   /contributions/ingredients/parse    « 200 g de farine » → lignes
  GET    /contributions/ingredients/suggest  suggestions du catalogue
  GET    /contributions/mine                 mes propositions
  POST   /contributions                      nouveau brouillon
  GET    /contributions/{id}                 une proposition
  PUT    /contributions/{id}                 enregistrer (brouillon / à corriger)
  DELETE /contributions/{id}                 supprimer (retire aussi la recette publiée)
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
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.auth_deps import get_user, get_optional_user
from backend.core.rate_limiter import check_rate_limit
from backend.db.models import RecipeSubmission
from backend.db.session import get_db
from backend.services import contribution_service as cs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/contributions", tags=["Recettes proposées"])

MAX_OPEN_PER_USER = 20       # brouillons + en relecture + à corriger
MAX_PENDING_PER_USER = 5     # envoyées en attente de relecture


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


# ── Helpers ───────────────────────────────────────────────────────────────────

def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _author(name: str | None) -> str:
    return cs._text(name, cs.LIMITS["author_max"])


def _serialize(sub: RecipeSubmission, *, for_moderator: bool = False) -> dict:
    out = {
        "id": sub.id,
        "status": sub.status,
        "status_label": cs.STATUSES.get(sub.status, sub.status),
        "editable": sub.status in cs.EDITABLE_STATUSES,
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
        cs.delete_photo(s.photo_token)
        db.delete(s)
    db.commit()
    if had_published:
        rebuild_community_file(db)
    return len(subs)


# ── Formulaire ────────────────────────────────────────────────────────────────

@router.get("/options")
def get_options(user: dict | None = Depends(get_optional_user)):
    """Listes et bornes du formulaire. **Public.**"""
    out = cs.options()
    out["is_moderator"] = is_moderator((user or {}).get("email"))
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
def update_submission(sid: str, payload: DraftPayload,
                      user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Enregistre un brouillon ou une recette renvoyée « à corriger »."""
    sub = _get_own(db, sid, user["email"])
    if sub.status not in cs.EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail=(
            "Cette recette n'est plus modifiable : elle est "
            f"« {cs.STATUSES.get(sub.status, sub.status).lower()} »."))
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
    cs.delete_photo(sub.photo_token)
    db.delete(sub)
    db.commit()
    if was_published:
        rebuild_community_file(db)


@router.post("/{sid}/submit")
def submit_submission(sid: str, payload: SubmitPayload, request: Request,
                      user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Envoie en relecture : consentement, pseudo et points bloquants vérifiés."""
    check_rate_limit(request, limit=10, window_seconds=3600, email=user["email"])
    sub = _get_own(db, sid, user["email"])
    if sub.status not in cs.EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Cette recette a déjà été envoyée.")
    if not payload.consent:
        raise HTTPException(status_code=422, detail=(
            "Cochez la case qui certifie que la recette est la vôtre et que vous acceptez sa publication."))
    author = _author(payload.author_name)
    if len(author) < cs.LIMITS["author_min"]:
        raise HTTPException(status_code=422, detail="Indiquez le nom ou pseudo à afficher (2 caractères au moins).")
    if cs._NON_VEG_RE.search(author) or cs._LINK_RE.search(author) or "@" in author:
        raise HTTPException(status_code=422, detail="Ce pseudo ne peut pas être affiché : choisissez-en un autre.")
    pending = (db.query(RecipeSubmission)
                 .filter(RecipeSubmission.user_email == user["email"],
                         RecipeSubmission.status == "submitted")
                 .count())
    if pending >= MAX_PENDING_PER_USER:
        raise HTTPException(status_code=429, detail=(
            f"{pending} de vos recettes attendent déjà une relecture : patientez avant d'en envoyer d'autres."))
    analysis = cs.analyze(sub.data or {}, submission_id=sub.id, author_name=author)
    if not analysis["ready"]:
        blocking = [i["message"] for i in analysis["issues"] if i["level"] == "blocking"]
        raise HTTPException(status_code=422, detail="À compléter avant l'envoi : " + " ".join(blocking))
    sub.author_name = author
    sub.status = "submitted"
    sub.submitted_at = _now()
    db.commit()
    db.refresh(sub)
    return _serialize(sub)


# ── Photo ─────────────────────────────────────────────────────────────────────

_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.put("/{sid}/photo")
async def upload_photo(sid: str, request: Request,
                       user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Corps brut de l'image (Content-Type image/jpeg, image/png ou image/webp)."""
    check_rate_limit(request, limit=20, window_seconds=600, email=user["email"])
    sub = _get_own(db, sid, user["email"])
    if sub.status not in cs.EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Cette recette n'est plus modifiable.")
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
    cs.delete_photo(sub.photo_token)
    sub.photo_token = token
    db.commit()
    return {"photo_url": cs.photo_url(token)}


@router.delete("/{sid}/photo", status_code=status.HTTP_204_NO_CONTENT)
def delete_photo(sid: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Retire la photo d'une proposition modifiable."""
    sub = _get_own(db, sid, user["email"])
    if sub.status not in cs.EDITABLE_STATUSES:
        raise HTTPException(status_code=409, detail="Cette recette n'est plus modifiable.")
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

@router.get("/moderation/queue")
def moderation_queue(status_filter: str = Query(default="submitted", alias="status"),
                     _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    if status_filter not in cs.STATUSES:
        raise HTTPException(status_code=400, detail="Statut inconnu")
    order = RecipeSubmission.submitted_at.asc() if status_filter == "submitted" else RecipeSubmission.updated_at.desc()
    subs = db.query(RecipeSubmission).filter(RecipeSubmission.status == status_filter).order_by(order).limit(200).all()
    counts = {k: db.query(RecipeSubmission).filter(RecipeSubmission.status == k).count() for k in cs.STATUSES}
    return {"status": status_filter, "counts": counts,
            "results": [_serialize(s, for_moderator=True) for s in subs]}


@router.get("/moderation/{sid}")
def moderation_get(sid: str, _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    sub = _get_any(db, sid)
    out = _serialize(sub, for_moderator=True)
    out["analysis"] = cs.analyze(sub.data or {}, submission_id=sub.id, author_name=sub.author_name or "")
    out["author_published"] = (db.query(RecipeSubmission)
                                 .filter(RecipeSubmission.user_email == sub.user_email,
                                         RecipeSubmission.status == "published").count())
    return out


@router.put("/moderation/{sid}")
def moderation_edit(sid: str, payload: DraftPayload,
                    _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Corrections de la modération (rattacher un ingrédient, coquille) avant publication."""
    sub = _get_any(db, sid)
    if sub.status != "submitted":
        raise HTTPException(status_code=409, detail="Seule une recette en relecture se corrige ici.")
    _set_data(sub, payload.data)
    db.commit()
    db.refresh(sub)
    return _serialize(sub, for_moderator=True)


@router.post("/moderation/{sid}/publish")
def moderation_publish(sid: str, payload: MessagePayload = MessagePayload(),
                       mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Publie la recette dans le catalogue (aucun point bloquant ni ingrédient hors base)."""
    sub = _get_any(db, sid)
    if sub.status != "submitted":
        raise HTTPException(status_code=409, detail="Seule une recette en relecture peut être publiée.")
    analysis = cs.analyze(sub.data or {}, submission_id=sub.id, author_name=sub.author_name or "")
    if not analysis["ready"]:
        raise HTTPException(status_code=422, detail="Points bloquants restants : " + " ".join(
            i["message"] for i in analysis["issues"] if i["level"] == "blocking"))
    if analysis["unmatched"]:
        raise HTTPException(status_code=422, detail=(
            "Rattachez d'abord ces ingrédients au catalogue : " + ", ".join(analysis["unmatched"])))
    sub.status = "published"
    sub.reviewed_at = _now()
    sub.moderator_email = mod["email"]
    sub.moderator_note = cs._text(payload.message, 1500, multiline=True) or None
    if not sub.published_recipe_id:
        sub.published_recipe_id = cs.recipe_id_for(sub.id, sub.title)
    db.commit()
    rebuild_community_file(db)
    db.refresh(sub)
    return _serialize(sub, for_moderator=True)


def _send_back(db: Session, sub: RecipeSubmission, mod: dict, new_status: str, message: str) -> None:
    text = cs._text(message, 1500, multiline=True)
    if len(text) < 10:
        raise HTTPException(status_code=422, detail="Expliquez à l'auteur ce qui doit changer (10 caractères au moins).")
    was_published = sub.status == "published"
    sub.status = new_status
    sub.moderator_note = text
    sub.moderator_email = mod["email"]
    sub.reviewed_at = _now()
    db.commit()
    if was_published:
        rebuild_community_file(db)


@router.post("/moderation/{sid}/request-changes")
def moderation_request_changes(sid: str, payload: MessagePayload,
                               mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    sub = _get_any(db, sid)
    if sub.status != "submitted":
        raise HTTPException(status_code=409, detail="Seule une recette en relecture peut être renvoyée.")
    _send_back(db, sub, mod, "changes_requested", payload.message)
    db.refresh(sub)
    return _serialize(sub, for_moderator=True)


@router.post("/moderation/{sid}/reject")
def moderation_reject(sid: str, payload: MessagePayload,
                      mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    sub = _get_any(db, sid)
    if sub.status not in {"submitted", "changes_requested"}:
        raise HTTPException(status_code=409, detail="Cette recette ne peut pas être refusée dans son état actuel.")
    _send_back(db, sub, mod, "rejected", payload.message)
    db.refresh(sub)
    return _serialize(sub, for_moderator=True)


@router.post("/moderation/{sid}/unpublish")
def moderation_unpublish(sid: str, payload: MessagePayload,
                         mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Retire une recette publiée et la renvoie à son auteur avec un message."""
    sub = _get_any(db, sid)
    if sub.status != "published":
        raise HTTPException(status_code=409, detail="Cette recette n'est pas publiée.")
    _send_back(db, sub, mod, "changes_requested", payload.message)
    db.refresh(sub)
    return _serialize(sub, for_moderator=True)
