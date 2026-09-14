"""
encryption.py — Chiffrement des données de santé sensibles (Art. 9 RGPD).

Utilise Fernet (AES-128-CBC + HMAC-SHA256) via la bibliothèque `cryptography`.

Colonnes concernées dans UserProfile :
  - cycle_phase  (phase du cycle menstruel)
  - health_goal  (objectif santé : anémie, diabète…)

Configuration :
  Variable d'environnement HEALTH_DATA_KEY (Fernet key en base64-urlsafe).
  Générer : python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

Mode dégradé :
  Si HEALTH_DATA_KEY est absent (développement), données stockées en clair
  avec avertissement. Ne jamais déployer sans cette clé.
"""
import logging
import os

logger = logging.getLogger(__name__)

_fernet = None
_warned = False


def _get_fernet():
    global _fernet, _warned
    if _fernet is not None:
        return _fernet
    key = os.getenv("HEALTH_DATA_KEY")
    if not key:
        if not _warned:
            logger.warning(
                "HEALTH_DATA_KEY non défini — données santé stockées en clair. "
                "Non conforme RGPD Art. 9 en production."
            )
            _warned = True
        return None
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
        return _fernet
    except Exception as e:
        logger.error("Erreur initialisation Fernet : %s", e)
        return None


def encrypt_health(value: str | None) -> str | None:
    """Chiffre une valeur de santé. Mode dégradé si pas de clé."""
    if value is None:
        return None
    f = _get_fernet()
    if f is None:
        return value
    return f.encrypt(value.encode()).decode()


def decrypt_health(value: str | None) -> str | None:
    """Déchiffre une valeur de santé. Tolérance texte clair pour migration."""
    if value is None:
        return None
    f = _get_fernet()
    if f is None:
        return value
    try:
        return f.decrypt(value.encode()).decode()
    except Exception:
        logger.debug("decrypt_health : erreur ignorée (repli)", exc_info=False)
        return value  # Valeur stockée en clair (migration)


# ── TypeDecorator SQLAlchemy (import lazy) ────────────────────────────────────

def EncryptedString(length: int = 255):
    """
    Factory qui retourne un TypeDecorator SQLAlchemy pour chiffrement transparent.

    Import de SQLAlchemy différé pour ne pas bloquer les tests sans SQLAlchemy.

    Usage dans models.py :
        from backend.core.encryption import EncryptedString
        cycle_phase = Column(EncryptedString(120), nullable=True)
    """
    from sqlalchemy import String
    from sqlalchemy.types import TypeDecorator

    class _EncryptedString(TypeDecorator):
        impl     = String
        cache_ok = True

        def process_bind_param(self, value, dialect):
            return encrypt_health(value)

        def process_result_value(self, value, dialect):
            return decrypt_health(value)

    return _EncryptedString(length)
