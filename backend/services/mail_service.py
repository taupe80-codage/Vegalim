"""
mail_service.py — Envoi d'e-mails (SMTP), sans dépendance externe.

Configuration (.env) :
  SMTP_HOST, SMTP_PORT (587), SMTP_USER, SMTP_PASSWORD,
  SMTP_FROM (« ALIM <no-reply@exemple.fr> »), SMTP_SECURITY (starttls | ssl | none),
  APP_BASE_URL (adresse de l'interface, pour les liens : https://alim.exemple.fr/ui)

Sans SMTP_HOST, les e-mails ne partent pas : ils sont seulement journalisés
(utile en développement, jamais bloquant). Les envois passent par les tâches
de fond FastAPI : une panne SMTP ne fait jamais échouer la requête.
"""
from __future__ import annotations

import html
import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

logger = logging.getLogger(__name__)

# Derniers messages « envoyés » quand SMTP n'est pas configuré (tests, dev)
OUTBOX: list[dict] = []
_OUTBOX_MAX = 50


def _cfg() -> dict:
    return {
        "host": os.getenv("SMTP_HOST", "").strip(),
        "port": int(os.getenv("SMTP_PORT", "587") or 587),
        "user": os.getenv("SMTP_USER", "").strip(),
        "password": os.getenv("SMTP_PASSWORD", ""),
        "from": os.getenv("SMTP_FROM", "").strip() or "ALIM <no-reply@localhost>",
        "security": (os.getenv("SMTP_SECURITY", "starttls") or "starttls").lower(),
    }


def app_url(path: str = "") -> str:
    """Lien vers l'interface : APP_BASE_URL + route en hash (« /mes-recettes »)."""
    base = (os.getenv("APP_BASE_URL", "") or "http://localhost:8000/ui").rstrip("/")
    return f"{base}/#{path}" if path else base


def is_configured() -> bool:
    return bool(_cfg()["host"])


def _html(paragraphs: list[str], link: tuple[str, str] | None) -> str:
    body = "".join(f"<p style=\"margin:0 0 14px\">{html.escape(p).replace(chr(10), '<br>')}</p>" for p in paragraphs)
    if link:
        label, url = link
        body += (f"<p style=\"margin:22px 0\"><a href=\"{html.escape(url)}\" style=\"background:#1d6b40;color:#fff;"
                 f"padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600\">{html.escape(label)}</a></p>")
    return (
        "<!doctype html><html lang=\"fr\"><body style=\"font-family:system-ui,sans-serif;color:#0d1f13;"
        "background:#eef5f0;padding:24px\"><div style=\"max-width:560px;margin:auto;background:#fff;"
        "border-radius:12px;padding:24px\">"
        f"<p style=\"font-weight:700;font-size:18px;color:#1d6b40;margin:0 0 18px\">ALIM</p>{body}"
        "<p style=\"color:#4b6f5a;font-size:12px;margin-top:28px\">Vous recevez cet e-mail car vous avez un compte ALIM. "
        f"Pour ne plus en recevoir : <a href=\"{html.escape(app_url('/mes-recettes'))}\">Mes recettes proposées</a>.</p>"
        "</div></body></html>"
    )


def send(to: str | list[str], subject: str, paragraphs: list[str],
         link: tuple[str, str] | None = None) -> bool:
    """Envoie un e-mail texte + HTML. Ne lève jamais : renvoie False en cas d'échec."""
    recipients = [to] if isinstance(to, str) else [t for t in to if t]
    if not recipients:
        return False
    text = "\n\n".join(paragraphs) + (f"\n\n{link[0]} : {link[1]}" if link else "")
    cfg = _cfg()
    if not cfg["host"]:
        OUTBOX.append({"to": recipients, "subject": subject, "text": text})
        del OUTBOX[:-_OUTBOX_MAX]
        logger.info("E-mail non envoyé (SMTP_HOST absent) → %s : %s", ", ".join(recipients), subject)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["from"]
    msg["To"] = ", ".join(recipients)
    msg["Message-ID"] = make_msgid(domain=cfg["from"].rsplit("@", 1)[-1].strip("> ") or "localhost")
    msg.set_content(text)
    msg.add_alternative(_html(paragraphs, link), subtype="html")
    try:
        ctx = ssl.create_default_context()
        if cfg["security"] == "ssl":
            server = smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx, timeout=15)
        else:
            server = smtplib.SMTP(cfg["host"], cfg["port"], timeout=15)
            if cfg["security"] == "starttls":
                server.starttls(context=ctx)
        with server:
            if cfg["user"]:
                server.login(cfg["user"], cfg["password"])
            server.send_message(msg)
        logger.info("E-mail envoyé → %s : %s", ", ".join(recipients), subject)
        return True
    except Exception as e:  # SMTP indisponible : on journalise, on ne casse rien
        logger.error("Échec d'envoi d'e-mail → %s (%s) : %s", ", ".join(recipients), subject, e)
        return False


__all__ = ["send", "app_url", "is_configured", "OUTBOX", "formataddr"]
