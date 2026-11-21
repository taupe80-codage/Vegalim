"""
routes/reviews.py — Notes et commentaires sur les recettes (catalogue et communauté).

Public :
  GET    /avis/recette/{recipe_id}       résumé (moyenne, répartition) + commentaires
  POST   /avis/resume                    moyennes de plusieurs recettes (cartes)

Compte connecté :
  PUT    /avis/recette/{recipe_id}       donner / modifier mon avis (note 1-5, commentaire)
  DELETE /avis/recette/{recipe_id}       retirer mon avis
  POST   /avis/{review_id}/utile         « utile » (bascule)
  POST   /avis/{review_id}/signaler      signaler (masqué automatiquement à 3 signalements)

Modération (ADMIN_EMAILS) :
  GET    /avis/moderation                avis signalés ou masqués
  POST   /avis/moderation/{id}/hide      masquer
  POST   /avis/moderation/{id}/restore   rétablir (signalements remis à zéro)
  DELETE /avis/moderation/{id}           supprimer

Ce que reprennent ces avis des sites de recettes de référence : une note par
compte (modifiable), « j'ai réalisé cette recette », tri par utilité,
répartition des notes, signalement par les lecteurs. L'auteur d'une recette
proposée ne peut pas noter la sienne.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.api.routes.contributions import require_moderator
from backend.core.auth_deps import get_user, get_optional_user
from backend.core.rate_limiter import check_rate_limit
from backend.db.models import RecipeReview, RecipeSubmission, ReviewReport, ReviewVote
from backend.db.session import get_db
from backend.services import contribution_service as cs

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/avis", tags=["Notes et commentaires"])

COMMENT_MAX = 1000
AUTO_HIDE_REPORTS = 3
REPORT_REASONS = {
    "spam": "Publicité ou spam",
    "offensive": "Propos insultants ou inappropriés",
    "off_topic": "Hors sujet",
    "personal": "Données personnelles",
    "other": "Autre",
}


class ReviewPayload(BaseModel):
    rating:      int           = Field(..., ge=1, le=5)
    comment:     Optional[str] = Field(default="", max_length=COMMENT_MAX + 200)
    made_it:     bool          = Field(default=False)
    author_name: str           = Field(..., max_length=60)


class ReportPayload(BaseModel):
    reason: Literal["spam", "offensive", "off_topic", "personal", "other"]


class SummaryPayload(BaseModel):
    ids: list[str] = Field(default_factory=list, max_length=300)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _recipe(recipe_id: str) -> dict:
    from backend.core.data_io import load_recipes
    r = next((x for x in load_recipes() if str(x.get("id")) == str(recipe_id)), None)
    if not r:
        raise HTTPException(status_code=404, detail="Recette introuvable")
    return r


def _is_own_recipe(db: Session, recipe: dict, email: str) -> bool:
    sid = (recipe.get("community") or {}).get("submission_id")
    if not sid:
        return False
    sub = db.get(RecipeSubmission, sid)
    return bool(sub and sub.user_email == email)


def _summary(db: Session, recipe_id: str) -> dict:
    rows = (db.query(RecipeReview.rating, func.count(RecipeReview.id))
              .filter(RecipeReview.recipe_id == recipe_id, RecipeReview.status == "visible")
              .group_by(RecipeReview.rating).all())
    dist = {str(i): 0 for i in range(1, 6)}
    for rating, n in rows:
        dist[str(rating)] = n
    count = sum(dist.values())
    avg = round(sum(int(k) * v for k, v in dist.items()) / count, 1) if count else None
    made_it = (db.query(func.count(RecipeReview.id))
                 .filter(RecipeReview.recipe_id == recipe_id, RecipeReview.status == "visible",
                         RecipeReview.made_it.is_(True)).scalar() or 0)
    comments = (db.query(func.count(RecipeReview.id))
                  .filter(RecipeReview.recipe_id == recipe_id, RecipeReview.status == "visible",
                          RecipeReview.comment.isnot(None), RecipeReview.comment != "").scalar() or 0)
    return {"average": avg, "count": count, "distribution": dist, "made_it": made_it, "comments": comments}


def _serialize(r: RecipeReview, *, me: str | None = None, voted: set[int] | None = None,
               reported: set[int] | None = None) -> dict:
    return {
        "id": r.id,
        "recipe_id": r.recipe_id,
        "author_name": r.author_name,
        "rating": r.rating,
        "comment": r.comment or "",
        "made_it": bool(r.made_it),
        "helpful_count": r.helpful_count or 0,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "edited": bool(r.updated_at and r.created_at and (r.updated_at - r.created_at).total_seconds() > 60),
        "is_mine": bool(me and r.user_email == me),
        "voted": bool(voted and r.id in voted),
        "reported": bool(reported and r.id in reported),
        "hidden": r.status != "visible",
    }


def _clean_comment(text: str | None) -> str:
    c = cs._text(text, COMMENT_MAX, multiline=True)
    if c and cs._LINK_RE.search(c):
        raise HTTPException(status_code=422, detail="Les liens ne sont pas acceptés dans les commentaires.")
    if c and len(c) < 3:
        raise HTTPException(status_code=422, detail="Commentaire trop court.")
    return c


def delete_user_reviews(db: Session, email: str) -> int:
    """Suppression du compte : avis, votes et signalements, compteurs recalculés."""
    voted = [v.review_id for v in db.query(ReviewVote).filter(ReviewVote.user_email == email).all()]
    reported = [r.review_id for r in db.query(ReviewReport).filter(ReviewReport.user_email == email).all()]
    db.query(ReviewVote).filter(ReviewVote.user_email == email).delete()
    db.query(ReviewReport).filter(ReviewReport.user_email == email).delete()
    mine = db.query(RecipeReview).filter(RecipeReview.user_email == email).all()
    mine_ids = [r.id for r in mine]
    if mine_ids:
        db.query(ReviewVote).filter(ReviewVote.review_id.in_(mine_ids)).delete(synchronize_session=False)
        db.query(ReviewReport).filter(ReviewReport.review_id.in_(mine_ids)).delete(synchronize_session=False)
    for r in mine:
        db.delete(r)
    db.flush()
    for rid in set(voted) - set(mine_ids):
        r = db.get(RecipeReview, rid)
        if r:
            r.helpful_count = db.query(ReviewVote).filter(ReviewVote.review_id == rid).count()
    for rid in set(reported) - set(mine_ids):
        r = db.get(RecipeReview, rid)
        if r:
            r.report_count = db.query(ReviewReport).filter(ReviewReport.review_id == rid).count()
    db.commit()
    return len(mine)


# ── Lecture ───────────────────────────────────────────────────────────────────

@router.get("/recette/{recipe_id}")
def recipe_reviews(recipe_id: str, request: Request,
                   sort: Literal["helpful", "recent", "high", "low"] = Query(default="helpful"),
                   skip: int = Query(default=0, ge=0), limit: int = Query(default=10, ge=1, le=50),
                   user: dict | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    """Résumé des notes et commentaires visibles d'une recette. **Public.**"""
    check_rate_limit(request, limit=120, window_seconds=60)
    recipe = _recipe(recipe_id)
    me = (user or {}).get("email")
    q = (db.query(RecipeReview)
           .filter(RecipeReview.recipe_id == recipe_id, RecipeReview.status == "visible",
                   RecipeReview.comment.isnot(None), RecipeReview.comment != ""))
    order = {
        "helpful": (RecipeReview.helpful_count.desc(), RecipeReview.created_at.desc()),
        "recent":  (RecipeReview.created_at.desc(),),
        "high":    (RecipeReview.rating.desc(), RecipeReview.helpful_count.desc()),
        "low":     (RecipeReview.rating.asc(), RecipeReview.helpful_count.desc()),
    }[sort]
    total = q.count()
    rows = q.order_by(*order).offset(skip).limit(limit).all()
    voted, reported, mine = set(), set(), None
    if me:
        ids = [r.id for r in rows]
        if ids:
            voted = {v.review_id for v in db.query(ReviewVote).filter(
                ReviewVote.user_email == me, ReviewVote.review_id.in_(ids)).all()}
            reported = {v.review_id for v in db.query(ReviewReport).filter(
                ReviewReport.user_email == me, ReviewReport.review_id.in_(ids)).all()}
        own = db.query(RecipeReview).filter(RecipeReview.recipe_id == recipe_id,
                                            RecipeReview.user_email == me).first()
        mine = _serialize(own, me=me) if own else None
    return {
        "recipe_id": recipe_id,
        "summary": _summary(db, recipe_id),
        "total": total,
        "reviews": [_serialize(r, me=me, voted=voted, reported=reported) for r in rows],
        "mine": mine,
        "can_review": bool(me) and not _is_own_recipe(db, recipe, me),
        "own_recipe": bool(me) and _is_own_recipe(db, recipe, me),
        "report_reasons": REPORT_REASONS,
    }


@router.post("/resume")
def summaries(payload: SummaryPayload, request: Request, db: Session = Depends(get_db)):
    """Note moyenne et nombre de notes de plusieurs recettes (cartes). **Public.**"""
    check_rate_limit(request, limit=120, window_seconds=60)
    ids = list(dict.fromkeys(str(i)[:100] for i in payload.ids if i))[:300]
    if not ids:
        return {"summaries": {}}
    rows = (db.query(RecipeReview.recipe_id, func.avg(RecipeReview.rating), func.count(RecipeReview.id))
              .filter(RecipeReview.recipe_id.in_(ids), RecipeReview.status == "visible")
              .group_by(RecipeReview.recipe_id).all())
    return {"summaries": {rid: {"average": round(float(avg), 1), "count": n} for rid, avg, n in rows}}


# ── Écriture ──────────────────────────────────────────────────────────────────

@router.put("/recette/{recipe_id}")
def upsert_review(recipe_id: str, payload: ReviewPayload, request: Request,
                  user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Donne ou modifie mon avis (un par recette)."""
    check_rate_limit(request, limit=20, window_seconds=3600, email=user["email"])
    recipe = _recipe(recipe_id)
    email = user["email"]
    if _is_own_recipe(db, recipe, email):
        raise HTTPException(status_code=403, detail="Vous ne pouvez pas noter votre propre recette.")
    author = cs._text(payload.author_name, cs.LIMITS["author_max"])
    if len(author) < 2 or "@" in author or cs._LINK_RE.search(author):
        raise HTTPException(status_code=422, detail="Indiquez un pseudo (2 caractères au moins, sans adresse e-mail).")
    comment = _clean_comment(payload.comment)
    review = db.query(RecipeReview).filter(RecipeReview.recipe_id == recipe_id,
                                           RecipeReview.user_email == email).first()
    if review is None:
        review = RecipeReview(recipe_id=recipe_id, user_email=email, status="visible",
                              helpful_count=0, report_count=0)
        db.add(review)
    review.author_name = author
    review.rating = payload.rating
    review.comment = comment or None
    review.made_it = payload.made_it
    review.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(review)
    return {"review": _serialize(review, me=email), "summary": _summary(db, recipe_id)}


@router.delete("/recette/{recipe_id}")
def delete_review(recipe_id: str, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Retire mon avis sur cette recette."""
    review = db.query(RecipeReview).filter(RecipeReview.recipe_id == recipe_id,
                                           RecipeReview.user_email == user["email"]).first()
    if not review:
        raise HTTPException(status_code=404, detail="Aucun avis à retirer")
    db.query(ReviewVote).filter(ReviewVote.review_id == review.id).delete()
    db.query(ReviewReport).filter(ReviewReport.review_id == review.id).delete()
    db.delete(review)
    db.commit()
    return {"summary": _summary(db, recipe_id)}


@router.post("/{review_id}/utile")
def toggle_helpful(review_id: int, request: Request, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """« Cet avis m'a été utile » : ajoute ou retire mon vote."""
    check_rate_limit(request, limit=60, window_seconds=60, email=user["email"])
    review = db.get(RecipeReview, review_id)
    if not review or review.status != "visible":
        raise HTTPException(status_code=404, detail="Avis introuvable")
    if review.user_email == user["email"]:
        raise HTTPException(status_code=403, detail="Vous ne pouvez pas voter pour votre propre avis.")
    vote = db.get(ReviewVote, (review_id, user["email"]))
    if vote:
        db.delete(vote)
        voted = False
    else:
        db.add(ReviewVote(review_id=review_id, user_email=user["email"]))
        voted = True
    db.flush()
    review.helpful_count = db.query(ReviewVote).filter(ReviewVote.review_id == review_id).count()
    db.commit()
    return {"helpful_count": review.helpful_count, "voted": voted}


@router.post("/{review_id}/signaler")
def report_review(review_id: int, payload: ReportPayload, request: Request,
                  user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Signale un avis ; masqué automatiquement à partir de 3 signalements."""
    check_rate_limit(request, limit=20, window_seconds=3600, email=user["email"])
    review = db.get(RecipeReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    if review.user_email == user["email"]:
        raise HTTPException(status_code=403, detail="Vous ne pouvez pas signaler votre propre avis.")
    if db.get(ReviewReport, (review_id, user["email"])):
        raise HTTPException(status_code=409, detail="Vous avez déjà signalé cet avis.")
    db.add(ReviewReport(review_id=review_id, user_email=user["email"], reason=payload.reason))
    db.flush()
    review.report_count = db.query(ReviewReport).filter(ReviewReport.review_id == review_id).count()
    if review.report_count >= AUTO_HIDE_REPORTS and review.status == "visible":
        review.status = "hidden"
        logger.info("Avis %s masqué automatiquement (%d signalements)", review_id, review.report_count)
    db.commit()
    return {"reported": True, "hidden": review.status != "visible"}


# ── Modération ────────────────────────────────────────────────────────────────

@router.get("/moderation")
def moderation_list(status_filter: Literal["reported", "hidden"] = Query(default="reported", alias="status"),
                    _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Avis signalés (encore visibles) ou masqués, avec les motifs de signalement."""
    from backend.core.data_io import load_recipes
    q = db.query(RecipeReview)
    q = (q.filter(RecipeReview.status == "visible", RecipeReview.report_count > 0)
         if status_filter == "reported" else q.filter(RecipeReview.status == "hidden"))
    rows = q.order_by(RecipeReview.report_count.desc(), RecipeReview.updated_at.desc()).limit(200).all()
    titles = {str(r.get("id")): (r.get("titles") or {}).get("fr", r.get("id")) for r in load_recipes()}
    counts = {
        "reported": db.query(RecipeReview).filter(RecipeReview.status == "visible", RecipeReview.report_count > 0).count(),
        "hidden": db.query(RecipeReview).filter(RecipeReview.status == "hidden").count(),
    }
    out = []
    for r in rows:
        item = _serialize(r)
        item["user_email"] = r.user_email
        item["recipe_title"] = titles.get(r.recipe_id, r.recipe_id)
        item["report_count"] = r.report_count
        reasons: dict[str, int] = {}
        for rep in db.query(ReviewReport).filter(ReviewReport.review_id == r.id).all():
            label = REPORT_REASONS.get(rep.reason, rep.reason)
            reasons[label] = reasons.get(label, 0) + 1
        item["reasons"] = reasons
        out.append(item)
    return {"status": status_filter, "counts": counts, "results": out}


@router.post("/moderation/{review_id}/hide")
def moderation_hide(review_id: int, _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Masque un avis (il ne compte plus dans la moyenne)."""
    review = db.get(RecipeReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    review.status = "hidden"
    db.commit()
    return {"status": review.status}


@router.post("/moderation/{review_id}/restore")
def moderation_restore(review_id: int, _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Rétablit un avis ; ses signalements sont remis à zéro."""
    review = db.get(RecipeReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    db.query(ReviewReport).filter(ReviewReport.review_id == review_id).delete()
    review.report_count = 0
    review.status = "visible"
    db.commit()
    return {"status": review.status}


@router.delete("/moderation/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def moderation_delete(review_id: int, _mod: dict = Depends(require_moderator), db: Session = Depends(get_db)):
    """Supprime définitivement un avis."""
    review = db.get(RecipeReview, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Avis introuvable")
    db.query(ReviewVote).filter(ReviewVote.review_id == review_id).delete()
    db.query(ReviewReport).filter(ReviewReport.review_id == review_id).delete()
    db.delete(review)
    db.commit()
