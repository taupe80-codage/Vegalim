"""
routes/notifications.py — Nouveautés affichées sous la cloche.

  GET  /notifications             les 50 dernières + nombre de non lues
  GET  /notifications/count       nombre de non lues (appel léger, régulier)
  POST /notifications/{id}/lu     marquer une notification comme lue
  POST /notifications/lu          tout marquer comme lu
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.core.auth_deps import get_user
from backend.db.models import Notification, as_utc
from backend.db.session import get_db

router = APIRouter(prefix="/notifications", tags=["Notifications"])


def _unread(db: Session, email: str) -> int:
    return (db.query(Notification)
              .filter(Notification.user_email == email, Notification.read_at.is_(None)).count())


def _serialize(n: Notification) -> dict:
    return {
        "id": n.id, "kind": n.kind, "title": n.title, "body": n.body or "", "link": n.link,
        "created_at": as_utc(n.created_at).isoformat() if n.created_at else None,
        "read": n.read_at is not None,
    }


@router.get("")
def list_notifications(limit: int = Query(default=50, ge=1, le=100),
                       user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Les dernières notifications du compte, de la plus récente à la plus ancienne."""
    rows = (db.query(Notification).filter(Notification.user_email == user["email"])
              .order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit).all())
    return {"unread": _unread(db, user["email"]), "results": [_serialize(n) for n in rows]}


@router.get("/count")
def count_notifications(user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Nombre de notifications non lues (pastille de la cloche)."""
    return {"unread": _unread(db, user["email"])}


@router.post("/lu")
def mark_all_read(user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Marque toutes mes notifications comme lues."""
    (db.query(Notification)
       .filter(Notification.user_email == user["email"], Notification.read_at.is_(None))
       .update({Notification.read_at: datetime.now(timezone.utc)}, synchronize_session=False))
    db.commit()
    return {"unread": 0}


@router.post("/{notification_id}/lu")
def mark_read(notification_id: int, user: dict = Depends(get_user), db: Session = Depends(get_db)):
    """Marque une notification comme lue."""
    n = db.get(Notification, notification_id)
    if not n or n.user_email != user["email"]:
        raise HTTPException(status_code=404, detail="Notification introuvable")
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        db.commit()
    return {"unread": _unread(db, user["email"])}
