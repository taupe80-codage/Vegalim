"""
api_key.py — Shim de compatibilité
=====================================
Ce module délègue à auth_middleware qui est le système d'authentification
officiel de la plateforme (plans, quotas, stockage JSON).

Conservé pour compatibilité ascendante avec les imports existants.
Ne pas utiliser directement — utiliser engine.auth_middleware.
"""

# Ré-exports depuis auth_middleware
from backend.engine.auth_middleware import (
    generate_api_key,
    validate_api_key,
    require_api_key,
    require_plan,
    APIUser,
    get_api_stats,
)

__all__ = [
    "generate_api_key",
    "validate_api_key",
    "require_api_key",
    "require_plan",
    "APIUser",
    "get_api_stats",
]
