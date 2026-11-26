"""
routes/ingredient_corrections.py — Corrections des fiches ingrédients (2026-11-26).

Membre connecté :
  POST   /ingredient-corrections            proposer une correction, source obligatoire
  GET    /ingredient-corrections/mine       mes corrections
  DELETE /ingredient-corrections/{id}       retirer une correction encore en attente

Modération (ADMIN_EMAILS) :
  GET    /ingredient-corrections/moderation/queue?status=submitted|accepted|rejected|reverted
  POST   /ingredient-corrections/moderation/{id}/accept   appliquée par-dessus la base
  POST   /ingredient-corrections/moderation/{id}/reject   motif obligatoire
  POST   /ingredient-corrections/moderation/{id}/revert   annuler une correction acceptée (motif)

Une valeur acceptée (pour 100 g) est écrite dans
backend/data/ingredients/ingredient_corrections.json, régénéré depuis cette
table : la fiche, les recettes (calcul CIQUAL) et la page publique la prennent
en compte sans réécrire la base source ; la fiche affiche l'ancienne valeur et
la source. « Autre information » (nom, allergène, saison…) : acceptée, elle
est traitée à la main.
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.routes.contributions import require_moderator, wants_email
from backend.core.auth_deps import get_user
from backend.core.rate_limiter import check_rate_limit
from backend.db.models import IngredientCorrection
from backend.db.session import get_db
from backend.services import ingredient_sheet as S
from backend.services import mail_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ingredient-corrections", tags=["Corrections des ingrédients"])

STATUSES = ("submitted", "accepted", "rejected", "reverted", "superseded")
MAX_PENDING_PER_USER = 10
MAX_VALUE = 100_000
_URL_RE = re.compile(r"https?://[^\s<>\"']+\.[^\s<>\"']+", re.I)


class CorrectionPayload(BaseModel):
    ingredient_id:  str             = Field(..., min_length=1, max_length=120)
    field:          str             = Field(..., min_length=1, max_length=40)
    proposed_value: Optional[float] = Field(default=None, ge=0, le=MAX_VALUE)
    source_ref:     str             = Field(..., max_length=300)
    source_url:     Optional[str]   = Field(default=None, max_length=500)
    comment:        Optional[str]   = Field(default=None, max_length=1000)


class MessagePayload(BaseModel):
    message: str = Field(default="", max_length=1500)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _clean(text: str | None, limit: int) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", text or "")).strip()[:limit]


def _serialize(c: IngredientCorrection, *, for_moderator: bool = False) -> dict:
    label, unit = (S.NUTRIENTS.get(c.field) or ("Autre information", ""))[:2]
    out = {
        "id": c.id, "ingredient_id": c.ingredient_id, "ingredient_name": c.ingredient_name,
        "field": c.field, "field_label": label, "unit": c.unit or unit,
        "current_value": c.current_value, "proposed_value": c.proposed_value,
        "source_ref": c.source_ref, "source_url": c.source_url, "comment": c.comment,
        "status": c.status, "moderator_note": c.moderator_note,
        "created_at": _iso(c.created_at), "reviewed_at": _iso(c.reviewed_at),
    }
    if for_moderator:
        out["user_email"] = c.user_email
        n = S.raw_nutrition(c.ingredient_id) or {}
        out["value_now"] = n.get(c.field) if c.field in S.NUTRIENTS else None
        out["base_source"] = S.source_info(c.ingredient_id, n, {})
    return out


def rebuild_file(db: Session) -> None:
    """Fichier des corrections appliquées, depuis les corrections acceptées."""
    rows = (db.query(IngredientCorrection)
            .filter(IngredientCorrection.status == "accepted", IngredientCorrection.field != "other").all())
    S.write_corrections([{
        "id": r.id, "ingredient_id": r.ingredient_id, "field": r.field, "source_id": r.source_id,
        "proposed_value": r.proposed_value, "current_value": r.current_value,
        "source_ref": r.source_ref, "source_url": r.source_url, "reviewed_at": _iso(r.reviewed_at),
    } for r in rows])


# ── Notifications ─────────────────────────────────────────────────────────────

_MAILS = {
    "accepted": ("Votre correction de « {name} » est appliquée",
                 ["Merci ! Votre correction de la fiche « {name} » ({label}) a été vérifiée et appliquée.",
                  "{note}"]),
    "accepted_other": ("Votre remarque sur « {name} » a été retenue",
                       ["Merci ! Votre remarque sur la fiche « {name} » a été retenue : l'équipe s'en occupe.",
                        "{note}"]),
    "rejected": ("Votre correction de « {name} » n'a pas été retenue",
                 ["Votre correction de la fiche « {name} » ({label}) n'a pas été retenue.", "Motif :\n{note}"]),
    "reverted": ("Votre correction de « {name} » a été annulée",
                 ["La correction de la fiche « {name} » ({label}) a été annulée.", "Motif :\n{note}"]),
}


def _send(background: BackgroundTasks | None, *args) -> None:
    if background is not None:
        background.add_task(mail_service.send, *args)
    else:
        mail_service.send(*args)


def notify_member(background, db: Session, c: IngredientCorrection, kind: str) -> None:
    from backend.services import notification_service
    if not c.user_email:
        return
    subject, paragraphs = _MAILS[kind]
    values = {"name": c.ingredient_name, "label": (S.NUTRIENTS.get(c.field) or ("autre information",))[0].lower(),
              "note": c.moderator_note or ""}
    link = f"/ingredient/{c.ingredient_id}"
    notification_service.push(db, c.user_email, f"correction.{kind}", subject.format(**values),
                              c.moderator_note or None, link)
    if wants_email(db, c.user_email):
        _send(background, c.user_email, subject.format(**values),
              [p.format(**values) for p in paragraphs if p.format(**values).strip()],
              ("Voir la fiche", mail_service.app_url(link)))


def notify_moderators(background, db: Session, c: IngredientCorrection) -> None:
    from backend.core.config import settings
    from backend.services import notification_service
    if not settings.admin_emails:
        return
    title = f"Correction à relire : « {c.ingredient_name} »"
    for email in sorted(settings.admin_emails):
        notification_service.push(db, email, "moderation.correction", title, c.source_ref, "/moderation")
    _send(background, sorted(settings.admin_emails), title,
          [f"Une correction de la fiche « {c.ingredient_name} » attend une relecture. Source : {c.source_ref}"],
          ("Ouvrir la modération", mail_service.app_url("/moderation")))


# ── Membre ────────────────────────────────────────────────────────────────────

@router.post("", status_code=201)
def propose(payload: CorrectionPayload, request: Request, background: BackgroundTasks,
            user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Proposer une correction d'une fiche ingrédient : source obligatoire."""
    check_rate_limit(request, limit=20, window_seconds=3600)
    from backend.core.data_io import load_ingredients_dict
    if payload.ingredient_id not in load_ingredients_dict():
        raise HTTPException(status_code=404, detail="Ingrédient introuvable.")
    field = payload.field
    if field != "other" and field not in S.NUTRIENTS:
        raise HTTPException(status_code=422, detail="Valeur inconnue.")
    source_ref = _clean(payload.source_ref, 300)
    if len(source_ref) < 4:
        raise HTTPException(status_code=422, detail="La source est obligatoire : nom de la table, de l'étude ou du produit.")
    url = (payload.source_url or "").strip() or None
    if url and not _URL_RE.fullmatch(url):
        raise HTTPException(status_code=422, detail="Le lien doit commencer par http:// ou https://.")
    comment = (payload.comment or "").strip()[:1000] or None
    n = S.raw_nutrition(payload.ingredient_id) or {}
    current = n.get(field) if field != "other" else None
    if field == "other":
        if not comment or len(comment) < 10:
            raise HTTPException(status_code=422, detail="Décrivez ce qu'il faut corriger (10 caractères au moins).")
        value = None
    else:
        if payload.proposed_value is None:
            raise HTTPException(status_code=422, detail="Indiquez la valeur juste, pour 100 g.")
        value = round(float(payload.proposed_value), 4)
        if isinstance(current, (int, float)) and abs(float(current) - value) < 1e-9:
            raise HTTPException(status_code=422, detail="C'est déjà la valeur affichée.")
    mine = db.query(IngredientCorrection).filter(IngredientCorrection.user_email == user["email"],
                                                 IngredientCorrection.status == "submitted")
    if mine.count() >= MAX_PENDING_PER_USER:
        raise HTTPException(status_code=429, detail=f"{MAX_PENDING_PER_USER} corrections en attente au plus : "
                                                    "patientez pendant leur relecture.")
    if field != "other" and mine.filter(IngredientCorrection.ingredient_id == payload.ingredient_id,
                                        IngredientCorrection.field == field).first():
        raise HTTPException(status_code=409, detail="Vous avez déjà proposé une correction de cette valeur : "
                                                    "elle est en relecture.")
    c = IngredientCorrection(
        id=str(uuid.uuid4()), ingredient_id=payload.ingredient_id,
        ingredient_name=S.display_name(payload.ingredient_id), field=field,
        unit=(S.NUTRIENTS.get(field) or (None, None))[1], current_value=current, proposed_value=value,
        source_id=str(n.get("_source_id")) if n.get("_source_id") is not None else None,
        source_ref=source_ref, source_url=url, comment=comment, user_email=user["email"],
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    notify_moderators(background, db, c)
    db.commit()
    return _serialize(c)


@router.get("/mine")
def mine(user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Mes corrections proposées, les plus récentes d'abord."""
    rows = (db.query(IngredientCorrection).filter(IngredientCorrection.user_email == user["email"])
            .order_by(IngredientCorrection.created_at.desc()).all())
    return {"results": [_serialize(c) for c in rows]}


@router.delete("/{cid}", status_code=204)
def withdraw(cid: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Retirer ma correction tant qu'elle n'est pas relue."""
    c = db.get(IngredientCorrection, cid)
    if not c or c.user_email != user["email"]:
        raise HTTPException(status_code=404, detail="Correction introuvable.")
    if c.status != "submitted":
        raise HTTPException(status_code=409, detail="Correction déjà relue : elle ne peut plus être retirée.")
    db.delete(c)
    db.commit()
    return Response(status_code=204)


# ── Modération ────────────────────────────────────────────────────────────────

@router.get("/moderation/queue")
def queue(status: str = Query(default="submitted"), _: dict = Depends(require_moderator),
          db: Session = Depends(get_db)):
    """Corrections à relire (ou déjà relues), avec la valeur actuelle de la fiche."""
    if status not in STATUSES:
        raise HTTPException(status_code=422, detail="Statut inconnu.")
    q = db.query(IngredientCorrection).filter(IngredientCorrection.status == status)
    q = q.order_by(IngredientCorrection.created_at.asc() if status == "submitted"
                   else IngredientCorrection.reviewed_at.desc())
    counts = {s: db.query(IngredientCorrection).filter(IngredientCorrection.status == s).count()
              for s in ("submitted", "accepted", "rejected")}
    return {"status": status, "counts": counts, "results": [_serialize(c, for_moderator=True) for c in q.limit(200)]}


def _get(db: Session, cid: str, status: str) -> IngredientCorrection:
    c = db.get(IngredientCorrection, cid)
    if not c:
        raise HTTPException(status_code=404, detail="Correction introuvable.")
    if c.status != status:
        raise HTTPException(status_code=409, detail="Cette correction a déjà été traitée.")
    return c


def _message(text: str, required: bool) -> str | None:
    t = (text or "").strip()[:1500]
    if required and len(t) < 10:
        raise HTTPException(status_code=422, detail="Expliquez la raison au membre (10 caractères au moins).")
    return t or None


@router.post("/moderation/{cid}/accept")
def accept(cid: str, payload: MessagePayload, background: BackgroundTasks,
           mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Accepter : la valeur s'applique par-dessus la base (fiche, recettes, page publique)."""
    c = _get(db, cid, "submitted")
    if c.field != "other":
        for old in (db.query(IngredientCorrection)
                    .filter(IngredientCorrection.ingredient_id == c.ingredient_id,
                            IngredientCorrection.field == c.field,
                            IngredientCorrection.status == "accepted").all()):
            old.status = "superseded"
        n = S.raw_nutrition(c.ingredient_id) or {}
        # code de la fiche de la base relu à l'acceptation (la base a pu changer)
        if n.get("_source_id") is not None:
            c.source_id = str(n["_source_id"])
    c.status, c.reviewed_at = "accepted", _now()
    c.moderator_note, c.moderator_email = _message(payload.message, False), mod["email"]
    db.commit()
    if c.field != "other":
        rebuild_file(db)
    notify_member(background, db, c, "accepted" if c.field != "other" else "accepted_other")
    db.commit()
    return _serialize(c, for_moderator=True)


@router.post("/moderation/{cid}/reject")
def reject(cid: str, payload: MessagePayload, background: BackgroundTasks,
           mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Refuser, motif obligatoire (envoyé au membre)."""
    c = _get(db, cid, "submitted")
    c.status, c.reviewed_at = "rejected", _now()
    c.moderator_note, c.moderator_email = _message(payload.message, True), mod["email"]
    db.commit()
    notify_member(background, db, c, "rejected")
    db.commit()
    return _serialize(c, for_moderator=True)


@router.post("/moderation/{cid}/revert")
def revert(cid: str, payload: MessagePayload, background: BackgroundTasks,
           mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Annuler une correction acceptée : la fiche revient à la valeur de la base."""
    c = _get(db, cid, "accepted")
    c.status, c.reviewed_at = "reverted", _now()
    c.moderator_note, c.moderator_email = _message(payload.message, True), mod["email"]
    db.commit()
    rebuild_file(db)
    notify_member(background, db, c, "reverted")
    db.commit()
    return _serialize(c, for_moderator=True)


def delete_user_corrections(db: Session, email: str) -> int:
    """Suppression du compte : les corrections acceptées restent (elles corrigent
    la fiche pour tous) sans lien avec l'e-mail ; les autres sont effacées."""
    kept = (db.query(IngredientCorrection)
            .filter(IngredientCorrection.user_email == email,
                    IngredientCorrection.status.in_(("accepted", "superseded", "reverted"))).all())
    for c in kept:
        c.user_email = None
    return (db.query(IngredientCorrection)
            .filter(IngredientCorrection.user_email == email).delete(synchronize_session=False))
