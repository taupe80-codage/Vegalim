"""
backend/core/config.py — Configuration centralisée ALIM.

Charge les variables d'environnement une seule fois à l'import.
Fournit des valeurs par défaut sécurisées et documente chaque variable.

Usage :
    from backend.core.config import settings

    if settings.is_production:
        ...

Ne jamais lire os.getenv() directement dans le code applicatif —
passer par ce module pour garantir la cohérence et la traçabilité.
"""
from __future__ import annotations

import os
import secrets
import logging

logger = logging.getLogger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _required(key: str) -> str:
    """Lit une variable obligatoire. Lève ValueError si absente."""
    v = os.getenv(key)
    if not v:
        raise ValueError(
            f"Variable d'environnement obligatoire absente : {key}\n"
            f"Ajoutez-la dans votre fichier .env ou dans les secrets du déployeur."
        )
    return v


def _optional(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def _bool_env(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).lower() in ("1", "true", "yes", "on")


def _int_env(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


# ── Configuration ─────────────────────────────────────────────────────────────

class _Settings:
    """Singleton chargé une seule fois à l'import."""

    def __init__(self) -> None:
        # ── JWT ──────────────────────────────────────────────────────────────
        # Obligatoire : une clé aléatoire doit être définie (jamais la valeur par défaut)
        self.secret_key: str = os.getenv("SECRET_KEY", "")
        self._secret_key_from_env = bool(self.secret_key)
        if not self.secret_key:
            self.secret_key = secrets.token_urlsafe(64)
            logger.warning(
                "SECRET_KEY absente — clé temporaire générée. "
                "Définissez SECRET_KEY dans .env pour la production."
            )

        self.jwt_algorithm:      str = _optional("JWT_ALGORITHM",       "HS256")
        self.jwt_expire_minutes: int = _int_env("JWT_EXPIRE_MINUTES",  1440)  # 24h par défaut

        # ── Base de données ───────────────────────────────────────────────────
        self.database_url: str = _optional("DATABASE_URL", "")

        # ── CORS ──────────────────────────────────────────────────────────────
        _raw_cors = _optional("CORS_ORIGINS", "*")
        self.cors_origins: list[str] = [o.strip() for o in _raw_cors.split(",") if o.strip()]
        self.cors_open:    bool      = self.cors_origins == ["*"]

        # ── Sécurité ─────────────────────────────────────────────────────────
        # Clé de chiffrement AES des données de santé (RGPD Art. 9)
        self.health_data_key: str = _optional("HEALTH_DATA_KEY", "")

        # ── Redis (rate limiter multi-process) ────────────────────────────────
        self.redis_url: str = _optional("REDIS_URL", "")

        # ── Logs ──────────────────────────────────────────────────────────────
        self.log_level:  str  = _optional("LOG_LEVEL",  "INFO").upper()
        self.log_format: str  = _optional("LOG_FORMAT", "text").lower()  # text | json

        # ── Environnement ─────────────────────────────────────────────────────
        # APP_ENV est la seule variable lue (ALIM_ENV accepté en rétro-compat).
        # Non défini → "development" pour le confort local, MAIS env_explicit=False :
        # les comportements dangereux (jeton de reset renvoyé dans la réponse)
        # exigent APP_ENV=development écrit explicitement.
        _raw_env = os.getenv("APP_ENV") or os.getenv("ALIM_ENV")
        self.env_explicit: bool = bool(_raw_env)
        self.env: str         = (_raw_env or "development").lower()

        # ── Administration ────────────────────────────────────────────────────
        # Emails autorisés sur /admin/* (en plus d'une clé API valide).
        # Vide = administration désactivée.
        self.admin_emails: set[str] = {
            e.strip().lower() for e in _optional("ADMIN_EMAILS", "").split(",") if e.strip()
        }

        # ── Rate Limiter ──────────────────────────────────────────────────────
        self.rate_limit_default: int = _int_env("RATE_LIMIT_DEFAULT", 60)
        self.rate_limit_window:  int = _int_env("RATE_LIMIT_WINDOW",  60)

    @property
    def is_production(self) -> bool:
        return self.env == "production"

    @property
    def is_development(self) -> bool:
        return self.env in ("development", "dev", "local")

    @property
    def is_explicit_development(self) -> bool:
        """APP_ENV=development écrit explicitement (pas seulement par défaut)."""
        return self.env_explicit and self.is_development

    def validate_production(self) -> list[str]:
        """
        Vérifie que la configuration est sécurisée pour un déploiement production.
        Retourne une liste de problèmes (vide = OK).
        """
        issues: list[str] = []

        if not self._secret_key_from_env:
            issues.append("SECRET_KEY non définie — tokens JWT invalides entre redémarrages")

        if self.cors_open:
            issues.append("CORS_ORIGINS=* — remplacez par votre domaine de production")

        if not self.health_data_key:
            issues.append(
                "HEALTH_DATA_KEY absente — données santé non chiffrées (violation RGPD Art. 9)"
            )

        if not self.database_url:
            issues.append("DATABASE_URL absente — SQLite utilisé (non recommandé en production)")

        if not self.redis_url:
            issues.append("REDIS_URL absente — rate limiter en mémoire (inefficace multi-process)")

        return issues

    def log_startup_status(self, log: logging.Logger) -> None:
        """Log le bilan de configuration au démarrage."""
        issues = self.validate_production() if self.is_production else []

        if self.is_production and issues:
            # SECRET_KEY + HEALTH_DATA_KEY → bloquants (levés dans _check_production_secrets)
            # CORS / DB / Redis → warnings non-bloquants (dégradé accepté)
            _blocking = {"SECRET_KEY", "HEALTH_DATA_KEY"}
            for issue in issues:
                if any(k in issue for k in _blocking):
                    log.error("CONFIG PROD [BLOQUANT] : %s", issue)
                else:
                    log.warning("CONFIG PROD [ATTENTION] : %s", issue)
        elif not self.is_production:
            if not self.env_explicit:
                log.warning(
                    "APP_ENV non défini — mode development par défaut (Swagger et /metrics "
                    "ouverts, secrets non exigés). Définissez APP_ENV=production pour un déploiement."
                )
            # En dev, on affiche les warnings non-bloquants
            warnings = self.validate_production()
            for w in warnings:
                log.warning("CONFIG [dev] : %s", w)

        log.info(
            "Configuration : env=%s | cors=%s | db=%s | redis=%s | log=%s",
            self.env,
            "ouvert (*)" if self.cors_open else ",".join(self.cors_origins),
            "PostgreSQL" if self.database_url else "SQLite",
            "Redis" if self.redis_url else "mémoire",
            self.log_level,
        )


# Singleton — import-safe
settings = _Settings()

__all__ = ["settings"]
