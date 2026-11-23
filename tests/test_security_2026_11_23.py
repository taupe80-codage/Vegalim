"""
tests/test_security_2026_11_23.py — Revue de sécurité des fonctions ouvertes au public.

- corps de requête limités (1 Mo, 9 Mo pour une photo) ;
- bombe de décompression refusée avant décodage ;
- pseudos réservés à l'équipe refusés ;
- un seul e-mail de réinitialisation par adresse toutes les 10 minutes.
"""
from __future__ import annotations

import io

import pytest
from fastapi.testclient import TestClient

from backend.api.main import app


def test_corps_json_trop_gros_refuse():
    c = TestClient(app)
    big = b'{"text": "' + b"a" * (1024 * 1024 + 10) + b'"}'
    res = c.post("/contributions/ingredients/parse", content=big, headers={"Content-Type": "application/json"})
    assert res.status_code == 413


def test_corps_en_flux_sans_taille_annoncee_refuse():
    c = TestClient(app)

    def gen():
        for _ in range(20):
            yield b"x" * (100 * 1024)          # 2 Mo, sans Content-Length

    res = c.post("/auth/login", content=gen(), headers={"Content-Type": "application/json"})
    assert res.status_code == 413


def test_limites_par_route():
    from backend.core.body_limit import limit_for, DEFAULT_LIMIT, PHOTO_LIMIT
    assert limit_for("PUT", "/contributions/abc/photo") == PHOTO_LIMIT
    assert limit_for("PUT", "/contributions/abc") == DEFAULT_LIMIT
    assert limit_for("POST", "/contributions/abc/photo") == DEFAULT_LIMIT


def test_bombe_de_decompression_refusee():
    from PIL import Image
    from backend.services import contribution_service as cs
    buf = io.BytesIO()
    Image.new("1", (9000, 9000)).save(buf, "PNG")      # 81 Mpx, quelques Ko compressés
    assert len(buf.getvalue()) < 200_000
    with pytest.raises(ValueError, match="40 mégapixels|lisible"):
        cs.save_photo(buf.getvalue())


@pytest.mark.parametrize("name, reserved", [
    ("ALIM", True), ("Équipe ALIM", True), ("Modération", True), ("admin", True),
    ("Léa", False), ("Alimata", False), ("Camille", False),
])
def test_pseudos_reserves(name, reserved):
    from backend.services import contribution_service as cs
    assert cs.is_reserved_name(name) is reserved


def test_un_seul_email_de_reinitialisation_par_adresse(monkeypatch):
    import backend.api.routes.auth as auth
    from backend.services import mail_service, user_service
    monkeypatch.delenv("SMTP_HOST", raising=False)
    monkeypatch.setattr(auth, "check_rate_limit", lambda *a, **k: None)
    monkeypatch.setattr(auth, "_RESET_DB_OK", False)          # stockage mémoire
    monkeypatch.setattr(auth, "_reset_tokens", {})
    monkeypatch.setattr(user_service, "account_is_active", lambda e: True)
    mail_service.OUTBOX.clear()
    c = TestClient(app)
    for _ in range(4):                                         # IP différentes : même effet
        assert c.post("/auth/forgot-password", json={"email": "victime@exemple.com"}).status_code == 200
    assert len([m for m in mail_service.OUTBOX if "victime@exemple.com" in m["to"]]) == 1
