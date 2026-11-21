"""
notification_service.py — Notifications affichées dans l'application.

push() enregistre une nouveauté pour un compte (cloche de la barre de
navigation). Elle est créée que l'e-mail parte ou non : sans SMTP configuré,
c'est le seul moyen pour l'auteur d'apprendre une décision.
Jamais bloquant : une erreur est journalisée, la requête continue.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

KEEP_PER_USER = 100
KEEP_DAYS = 90


def push(db: Session, email: str, kind: str, title: str,
         body: str | None = None, link: str | None = None) -> bool:
    from backend.db.models import Notification, User
    try:
        if not email or db.get(User, email) is None:
            return False
        db.add(Notification(user_email=email, kind=kind, title=title[:200],
                            body=(body or None) and body[:2000], link=(link or None) and link[:300]))
        db.flush()
        old = datetime.now(timezone.utc) - timedelta(days=KEEP_DAYS)
        db.query(Notification).filter(Notification.user_email == email,
                                      Notification.created_at < old).delete(synchronize_session=False)
        ids = [n.id for n in db.query(Notification.id).filter(Notification.user_email == email)
                                .order_by(Notification.created_at.desc(), Notification.id.desc())
                                .offset(KEEP_PER_USER).all()]
        if ids:
            db.query(Notification).filter(Notification.id.in_(ids)).delete(synchronize_session=False)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.warning("Notification non enregistrée pour %s (%s) : %s", email, kind, e)
        return False


__all__ = ["push", "KEEP_PER_USER", "KEEP_DAYS"]
