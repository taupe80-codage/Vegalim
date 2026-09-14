"""
backend/core/security_headers.py — Middleware HTTP security headers.

Ajoute les headers de sécurité standard sur toutes les réponses.
Distingue les routes frontend (React SPA) des routes API pures (JSON).

Headers posés :
  X-Frame-Options           → interdit l'embedding dans une iframe
  X-Content-Type-Options    → interdit le MIME-sniffing
  Referrer-Policy           → limite les infos envoyées au site tiers
  Permissions-Policy        → désactive les APIs navigateur inutilisées
  Content-Security-Policy   → restreint les sources de contenu autorisées

Note HSTS :
  Strict-Transport-Security n'est PAS posé ici — il est ajouté par le Caddyfile
  (Caddy ne le pose pas de lui-même). Le poser dans FastAPI provoquerait des boucles en
  développement HTTP.

Usage :
    from backend.core.security_headers import SecurityHeadersMiddleware
    app.add_middleware(SecurityHeadersMiddleware)
"""
from starlette.middleware.base import BaseHTTPMiddleware

# ── Content-Security-Policy ───────────────────────────────────────────────────

# Routes frontend React (SPA Vite) :
#   script-src 'self'          → seuls les scripts du même domaine (Vite génère des fichiers hashés)
#   style-src 'unsafe-inline'  → nécessaire si composants React utilisent style={{ }} inline
#   img-src data:              → certaines images sont encodées en base64
#   connect-src 'self'         → appels API vers la même origine
#   worker-src blob:           → Web Workers éventuels (Vite HMR en dev)
_CSP_FRONTEND = (
    "default-src 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self'; "
    "worker-src blob:; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

# Routes API pures (JSON) : rien de permis sauf les appels explicites
_CSP_API = "default-src 'none'; frame-ancestors 'none';"

# Préfixes identifiant une route frontend
_FRONTEND_PATHS = ("/ui", "/assets", "/static", "/favicon")


def _is_frontend(path: str) -> bool:
    return path in ("/", "/health", "/healthz") or any(
        path.startswith(p) for p in _FRONTEND_PATHS
    )


# ── Middleware ────────────────────────────────────────────────────────────────

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injecte les security headers sur toutes les réponses."""

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Headers universels
        response.headers["X-Frame-Options"]        = "DENY"
        response.headers["X-Content-Type-Options"]  = "nosniff"
        response.headers["Referrer-Policy"]         = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"]      = (
            "geolocation=(), microphone=(), camera=(), "
            "payment=(), usb=(), interest-cohort=()"
        )

        # CSP adapté au type de route
        response.headers["Content-Security-Policy"] = (
            _CSP_FRONTEND if _is_frontend(request.url.path) else _CSP_API
        )

        return response
