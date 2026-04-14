"""
Logger centralisé — ALIM_PROJECT_UNIFIED.

Usage dans n'importe quel module :
    from backend.core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Recettes chargées : %d", len(recipes))
    logger.warning("Fichier manquant : %s", path)
    logger.error("Crash chargement JSON : %s", e)

Format : [LEVEL] [module] message
Niveau par défaut : INFO (configurable via variable d'environnement LOG_LEVEL).
"""
import logging
import os
import sys

# ── Configuration globale ─────────────────────────────────────────────────────
_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

logging.basicConfig(
    level   = getattr(logging, _LEVEL, logging.INFO),
    format  = "[%(levelname)s] [%(name)s] %(message)s",
    stream  = sys.stdout,
    force   = True,
)

# Réduire le bruit des bibliothèques tierces
for noisy in ("uvicorn.access", "passlib", "jose"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Retourne un logger nommé. Utiliser __name__ comme convention."""
    return logging.getLogger(name)

# ── Formatter JSON (production) ───────────────────────────────────────────────

class _JSONFormatter(logging.Formatter):
    """
    Formatter JSON pour les environnements de production.
    Activé via LOG_FORMAT=json dans les variables d'environnement.
    Compatible avec Datadog, CloudWatch, Loki, etc.
    """
    def format(self, record: logging.LogRecord) -> str:
        import json
        from datetime import datetime, timezone
        d = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level":     record.levelname,
            "module":    record.name,
            "message":   record.getMessage(),
        }
        if record.exc_info:
            d["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "request_id"):
            d["request_id"] = record.request_id
        if hasattr(record, "duration_ms"):
            d["duration_ms"] = record.duration_ms
        return json.dumps(d, ensure_ascii=False)


def _configure_json_logging() -> None:
    """Active le formatter JSON sur le handler root."""
    root = logging.getLogger()
    fmt  = _JSONFormatter()
    for handler in root.handlers:
        handler.setFormatter(fmt)
    logging.getLogger(__name__).info("JSON logging activé")
