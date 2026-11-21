"""
tests/test_password_reset_email.py — Le lien de réinitialisation part par e-mail.

Avant : le jeton n'était renvoyé que dans la réponse en développement ; en
production personne ne pouvait réinitialiser son mot de passe.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from backend.api.main import app


def test_lien_envoye_si_le_compte_existe_reponse_identique_sinon(monkeypatch):
    import backend.api.routes.auth as auth
    from backend.services import mail_service, user_service
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setenv("APP_BASE_URL", "https://alim.exemple.fr/ui")
    monkeypatch.setattr(auth, "check_rate_limit", lambda *a, **k: None)
    monkeypatch.setattr(auth, "_store_reset_token", lambda token, email: None)
    monkeypatch.setattr(user_service, "account_is_active", lambda email: email == "connu@exemple.com")
    mail_service.OUTBOX.clear()
    c = TestClient(app)

    r1 = c.post("/auth/forgot-password", json={"email": "connu@exemple.com"})
    r2 = c.post("/auth/forgot-password", json={"email": "inconnu@exemple.com"})
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["message"] == r2.json()["message"]          # anti-énumération

    assert [m["to"] for m in mail_service.OUTBOX] == [["connu@exemple.com"]]
    text = mail_service.OUTBOX[0]["text"]
    assert "https://alim.exemple.fr/ui/#/?reinitialiser=" in text
    assert "30 minutes" in text


def test_jeton_de_reinitialisation_sous_sqlite_date_sans_fuseau():
    """SQLite rend expires_at sans fuseau : la consommation levait TypeError (500)."""
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from backend.db.models import Base
    from backend.db.repositories import PasswordResetRepository
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    repo = PasswordResetRepository(db)
    repo.store("jeton-valide", "a@exemple.com", ttl_minutes=30)
    db.commit()
    db.expire_all()                                   # relu depuis SQLite : date sans fuseau
    assert repo.consume("jeton-valide") == "a@exemple.com"
    assert repo.consume("jeton-valide") is None       # usage unique
