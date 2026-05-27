"""
rate_limiter.py — Rate limiting IP-based, Redis-aware.

Modes :
  1. Redis (recommandé en production multi-process)
     Activé si REDIS_URL est défini dans l'environnement.
     Clé Redis : "rl:{ip}:{window_start}" avec TTL = window_seconds.

  2. Mémoire (développement / serveur mono-process)
     Fallback automatique si Redis est indisponible.
     ⚠️  Inefficace avec plusieurs workers Uvicorn (limite ×N workers).

Usage dans les routes :
    check_rate_limit(request, limit=60, window_seconds=60)
    → lève HTTP 429 si l'IP dépasse la limite dans la fenêtre.

Configuration .env :
    REDIS_URL=redis://localhost:6379/0
"""
import logging
import math
import os
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# ── Backend Redis ─────────────────────────────────────────────────────────────

_redis_client = None
_redis_init_done = False


def _get_redis():
    """Retourne le client Redis ou None si indisponible."""
    global _redis_client, _redis_init_done
    if _redis_init_done:
        return _redis_client
    _redis_init_done = True
    url = os.getenv("REDIS_URL")
    if not url:
        logger.debug("REDIS_URL absent — rate limiter en mémoire (dev)")
        return None
    try:
        import redis
        _redis_client = redis.from_url(url, socket_connect_timeout=1, decode_responses=True)
        _redis_client.ping()
        logger.info("Rate limiter Redis connecté : %s", url.split("@")[-1])
        return _redis_client
    except ImportError:
        logger.warning(
            "redis-py non installé (pip install redis). "
            "Rate limiter en mémoire — inefficace en multi-process."
        )
    except Exception as e:
        logger.warning("Redis inaccessible (%s) — fallback mémoire.", e)
    return None


def _check_redis(ip: str, limit: int, window_seconds: int) -> None:
    """Rate limiting via Redis (sliding window par fenêtre fixe)."""
    r = _get_redis()
    window_start = math.floor(time.time() / window_seconds)
    key = f"rl:{ip}:{window_start}"
    count = r.incr(key)
    if count == 1:
        r.expire(key, window_seconds * 2)  # TTL 2× pour chevaucher les fenêtres
    if count > limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Limite dépassée. Réessayez dans {window_seconds} secondes.",
            headers={"Retry-After": str(window_seconds)},
        )


# ── Backend mémoire (fallback) ────────────────────────────────────────────────

_store: dict[str, list[float]] = defaultdict(list)


def _check_memory(ip: str, limit: int, window_seconds: int) -> None:
    """Rate limiting en mémoire (sliding window)."""
    now = time.monotonic()
    _store[ip] = [t for t in _store[ip] if now - t < window_seconds]
    if len(_store[ip]) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Trop de tentatives. Réessayez dans {window_seconds} secondes.",
            headers={"Retry-After": str(window_seconds)},
        )
    _store[ip].append(now)


# ── API publique ──────────────────────────────────────────────────────────────

def check_rate_limit(request: Request, limit: int, window_seconds: int,
                     email: str | None = None) -> None:
    """
    Vérifie la limite de requêtes par email (prioritaire) ou par IP.

    - Si `email` fourni : clé = email (plus juste derrière un proxy)
    - Sinon : clé = IP du client

    Utilise Redis si REDIS_URL est défini, sinon mémoire.
    Lève HTTP 429 si la limite est atteinte.
    """
    # Clé de rate limiting : email > IP
    ip = request.client.host if request.client else "unknown"
    identifier = email if email else ip
    r = _get_redis()
    if r is not None:
        _check_redis(identifier, limit, window_seconds)
    else:
        _check_memory(identifier, limit, window_seconds)
