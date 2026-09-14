"""
ALIM v6 — Point d'entrée FastAPI.

Architecture propre :
  core/     → sécurité, JWT, rate limiting, logging, validation
  db/       → PostgreSQL via SQLAlchemy (fallback SQLite dev)
  services/ → logique métier orchestrée
  engine/   → moteurs actifs (nutrition, scoring, recherche, planning…)
  api/      → routes modulaires par domaine

Lancement :
    export SECRET_KEY="votre-cle-secrete"
    uvicorn backend.api.main:app --reload

Documentation : http://localhost:8000/docs
"""

import logging
import os
from contextlib import asynccontextmanager

# Chargement automatique du fichier .env (developpement)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv optionnel — utilisez les variables d'environnement systeme

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path as _Path

from backend.core.logger           import get_logger
from backend.api.router            import router
from backend.core.config           import settings
from backend.core.security_headers import SecurityHeadersMiddleware

logger = get_logger("startup")


# 🔥 LIFESPAN CORRIGÉ

def _startup_checks(log) -> None:
    """Délègue la vérification de config à settings.log_startup_status()."""
    settings.log_startup_status(log)

    if settings.log_format == "json":
        from backend.core.logger import _configure_json_logging
        _configure_json_logging()

def _check_production_secrets() -> None:
    """
    Bloque le démarrage en production si des secrets critiques sont absents.
    En développement, logue des avertissements sans bloquer.
    """
    if not settings.is_production:
        return

    missing = []

    if not settings._secret_key_from_env:
        missing.append(
            "SECRET_KEY manquante — tokens JWT invalidés à chaque redémarrage.\n"
            "  Générer : python -c \"import secrets; print(secrets.token_urlsafe(64))\""
        )

    if not settings.health_data_key:
        missing.append(
            "HEALTH_DATA_KEY manquante — données santé (cycle, objectifs) stockées en CLAIR.\n"
            "  Violation RGPD Art. 9. Générer :\n"
            "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )

    if missing:
        border = "═" * 70
        msg = f"\n{border}\n  ALIM — DÉMARRAGE BLOQUÉ (APP_ENV=production)\n{border}\n"
        for i, m in enumerate(missing, 1):
            msg += f"\n  [{i}] {m}\n"
        msg += f"\n  Corriger .env puis relancer.\n{border}\n"
        raise RuntimeError(msg)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("═══ ALIM démarrage ═══")

    # ── Guard secrets production ──
    _check_production_secrets()

    # ── Warm-up des caches ──
    try:
        from backend.core.data_io import (
            load_recipes, load_nutrition_graph, load_score_graph,
            load_availability_graph, load_ingredients_dict, load_prices,
            load_seasonality, load_search_index,
        )
        recipes = load_recipes()
        logger.info("Dataset chargé : %d recettes", len(recipes))
        load_nutrition_graph()
        load_score_graph()
        load_availability_graph()
        load_ingredients_dict()
        load_prices()
        load_seasonality()
        load_search_index()
        logger.info("Caches warm-up : 8 loaders prêts")
    except Exception as e:
        logger.error("Warm-up partiel : %s — certaines fonctionnalités seront indisponibles", e)

    # ── Migrations Alembic ────────────────────────────────────────────────────
    # alembic upgrade head : applique toutes les migrations manquantes.
    # Remplace create_all() qui ne gère pas les changements de schéma existants.
    try:
        from alembic.config import Config as AlembicConfig
        from alembic import command as alembic_command
        from pathlib import Path as _P
        _alembic_cfg = AlembicConfig(str(_P(__file__).resolve().parents[2] / "alembic.ini"))
        alembic_command.upgrade(_alembic_cfg, "head")
        logger.info("DB migrée — alembic upgrade head OK")
    except Exception as e:
        logger.error("Erreur migration DB : %s — fallback create_all", e)
        try:
            from backend.db.session import init_db
            init_db()
        except Exception as e2:
            logger.error("Erreur fallback init DB : %s", e2)

    # (optionnel) vérifier la connexion
    try:
        from backend.db.session import check_connection, refresh_db_availability
        if check_connection():
            refresh_db_availability()   # FIX #2 : met DB_AVAILABLE=True si OK
            logger.info("Connexion DB OK — DB_AVAILABLE=True")
        else:
            logger.warning("DB non accessible — fallback JSON actif")
    except Exception as e:
        logger.warning("Check DB : %s", e)

    _startup_checks(logger)

    logger.info("Application prête")
    yield
    logger.info("═══ ALIM arrêt ═══")


# ── Application FastAPI ──
# /docs et /openapi.json désactivés en production — Swagger UI expose
# l'ensemble des routes, modèles et permet de tester l'API sans auth.
_docs_url    = None if settings.is_production else "/docs"
_redoc_url   = None if settings.is_production else "/redoc"
_openapi_url = None if settings.is_production else "/openapi.json"

app = FastAPI(
    title       = "ALIM — Plateforme Culinaire Végétarienne",
    description = (
        "API de recommandation végétarienne. 40+ cuisines. "
        "Score CDC_03c 7 dimensions. Auth JWT (B2C) + API key (B2B). "
        "PostgreSQL avec fallback SQLite."
    ),
    version     = "6.0.0",
    lifespan    = lifespan,
    docs_url    = _docs_url,
    redoc_url   = _redoc_url,
    openapi_url = _openapi_url,
)




# ── Middleware Request ID ──────────────────────────────────────────────────────

import uuid
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Injecte un X-Request-ID unique dans chaque requête.
    Permet de corréler les logs d'une même requête de bout en bout.
    """
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        import contextvars
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

# ── Middlewares ───────────────────────────────────────────────────────────────
# Ordre d'exécution LIFO : le dernier add_middleware() s'exécute EN PREMIER.
# SecurityHeaders → RequestID → CORS → handler

# CORS — Settings : CORS_ORIGINS (virgule-séparé) | défaut "*" (dev uniquement)
# Exemple prod : CORS_ORIGINS=https://alim.app,https://www.alim.app
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.cors_origins,
    allow_credentials = not settings.cors_open,   # False si "*" (incompatible avec credentials)
    allow_methods     = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers     = ["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
)

# Request ID — corrélation des logs bout en bout
app.add_middleware(RequestIDMiddleware)

# Security headers — X-Frame-Options, CSP, Referrer-Policy…
# Posé en dernier → s'exécute en premier, couvre toutes les réponses
app.add_middleware(SecurityHeadersMiddleware)


# ── Routes API ──
app.include_router(router)


# ── Frontend ───────────────────────────────────────────────────────────────────
#
# Frontend unique : React 19 + Vite (frontend/), servi depuis frontend/dist/.
#   cd frontend && npm install && npm run build
#
# Le repli « frontend_vanilla/ » documenté auparavant n'a jamais existé dans le
# dépôt : sans build, /ui répondait 503 dans les deux modes.
# ALIM_FRONTEND=react (Docker) rend le build obligatoire au démarrage.
#
_PROJECT_ROOT   = _Path(__file__).resolve().parent.parent.parent
_DIST           = _PROJECT_ROOT / "frontend" / "dist"
_FRONTEND_INDEX = _DIST / "index.html"

if os.getenv("ALIM_FRONTEND", "").lower() == "react" and not _FRONTEND_INDEX.exists():
    raise RuntimeError(
        "ALIM_FRONTEND=react mais frontend/dist/ absent. "
        "Lancer : cd frontend && npm install && npm run build"
    )
logger.info("Frontend : %s", _FRONTEND_INDEX if _FRONTEND_INDEX.exists() else "absent (npm run build)")

# ── Montage des assets statiques ───────────────────────────────────────────────
if (_DIST / "assets").exists():
    # Build Vite : assets hashés sous /assets/
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")
    # images des recettes servies depuis dist/images/ (copiées depuis public/, Git LFS)
    if (_DIST / "images").exists():
        app.mount("/images", StaticFiles(directory=str(_DIST / "images")), name="images")
    # favicon depuis dist/
    if (_DIST / "favicon.svg").exists():
        @app.get("/favicon.svg", include_in_schema=False)
        def favicon_react():
            return FileResponse(str(_DIST / "favicon.svg"))


@app.get("/ui", include_in_schema=False)
@app.get("/ui/{path:path}", include_in_schema=False)
def frontend_app(path: str = ""):
    """
    Frontend ALIM (React 19, build Vite frontend/dist/index.html).

    Hash router côté client → un seul index.html pour toutes les routes.
    """
    if not _FRONTEND_INDEX.exists():
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Frontend non disponible.",
                "hint":   "cd frontend && npm install && npm run build",
            }
        )
    return FileResponse(str(_FRONTEND_INDEX))


# ── Middleware headers quota (B2B) ─────────────────────────────────────────────

@app.middleware("http")
async def add_quota_headers(request, call_next):
    """Injecte X-Plan et X-RateLimit-* dans les réponses des routes API key."""
    response = await call_next(request)
    # Déjà géré par auth_middleware._require_plan pour le 429
    # Ici on s'assure que X-Plan est présent si l'header X-Api-Key est fourni
    if "x-api-key" in request.headers and "x-plan" not in response.headers:
        response.headers["X-API-Version"] = "6.0.0"
    return response


# ── Middleware métriques ───────────────────────────────────────────────────────

@app.middleware("http")
async def metrics_middleware(request, call_next):
    """
    Mesure la durée de chaque requête et alimente le store de métriques.
    Exclut les routes de health check pour éviter le bruit.
    """
    import time as _time
    from backend.core.metrics import record_request

    _EXCLUDED = {"/health", "/healthz", "/metrics", "/favicon.svg"}
    path = request.url.path

    if path in _EXCLUDED:
        return await call_next(request)

    t0 = _time.monotonic()
    response = await call_next(request)
    duration_ms = (_time.monotonic() - t0) * 1000

    record_request(
        route      = path,
        status_code= response.status_code,
        duration_ms= duration_ms,
    )
    return response


@app.get("/metrics", tags=["Monitoring"])
def get_metrics_endpoint(request: Request):
    """
    Métriques runtime : requêtes, latences, erreurs, top routes.

    **Protégé en production** — fournir le header :
        `X-Metrics-Token: <METRICS_TOKEN>`
    En développement, accessible sans token.

    Compatible dashboards JSON simples (Grafana JSON datasource, etc.)
    """
    from fastapi import HTTPException
    from fastapi.responses import JSONResponse
    from backend.core.metrics import get_metrics

    if settings.is_production:
        expected = os.getenv("METRICS_TOKEN", "")
        provided = request.headers.get("X-Metrics-Token", "")
        if not expected or provided != expected:
            raise HTTPException(status_code=403, detail="Token métriques invalide ou absent.")

    return JSONResponse(content=get_metrics())


@app.get("/stats", tags=["Plateforme"])
def platform_stats():
    """
    Statistiques publiques de la plateforme ALIM.
    Inclut le catalogue, les cuisines et les plans B2B disponibles.
    **Public** — utile pour les dashboards B2B et les pages de présentation.
    """
    from backend.core.data_io import load_recipes, load_ingredients_dict
    from backend.engine.auth_middleware import PLANS
    from collections import Counter
    recipes = load_recipes()
    d = load_ingredients_dict()

    flags = {"vegan": 0, "vegetarian": 0, "gluten_free": 0,
             "raw": 0, "kid_friendly": 0}
    cuisines = Counter()
    for r in recipes:
        for k in flags:
            if r.get("diet_flags", {}).get(k):
                flags[k] += 1
        c = (r.get("origin") or {}).get("cuisine", "")
        if c:
            cuisines[c] += 1

    # Plans B2B avec quotas
    plans_info = {
        name: {
            "daily_limit": plan.get("requests_per_day", 0),   # clé réelle de PLANS
            "description": plan.get("description", ""),
            "features":    plan.get("features", {}),
        }
        for name, plan in PLANS.items()
    } if PLANS else {}

    return {
        "recipes":      len(recipes),
        "ingredients":  len(d),
        "cuisines":     len(cuisines),
        "top_cuisines": dict(cuisines.most_common(10)),
        "diet_flags":   flags,
        "version":      "6.0.0",
        "api_plans":    plans_info,
        "endpoints":    {
            "docs":    "/docs",
            "openapi": "/openapi.json",
            "health":  "/healthz",
            "quota":   "/admin/quota (API key requise)",
        },
    }


@app.get("/legal/cgu", tags=["Légal"])
def get_cgu():
    """
    Conditions Générales d'Utilisation et Politique de Confidentialité.
    **Public** — requis pour la conformité RGPD avant inscription.
    """
    from pathlib import Path as _P
    cgu_path = _P(__file__).resolve().parent.parent.parent / "docs" / "CGU.md"
    if cgu_path.exists():
        return {"content": cgu_path.read_text(encoding="utf-8"), "format": "markdown"}
    return {"content": "CGU non disponible.", "format": "text"}


@app.get("/healthz", tags=["Santé"])
def healthz():
    """
    Health check détaillé pour monitoring production.
    Vérifie DB, dataset, graphes. Retourne 200 ou 503.
    """
    from backend.core.data_io import load_recipes, load_nutrition_graph, load_score_graph
    from backend.db.session import check_connection
    checks = {}

    # Dataset
    try:
        r = load_recipes()
        checks["recipes"] = {"status": "ok", "count": len(r)}
        assert len(r) > 0
    except Exception as e:
        checks["recipes"] = {"status": "error", "detail": str(e)}

    # Graphes nutrition + scoring
    try:
        ng = load_nutrition_graph()
        sg = load_score_graph()
        checks["graphs"] = {"status": "ok",
                            "nutrition": len(ng), "scoring": len(sg)}
        assert len(ng) > 0 and len(sg) > 0
    except Exception as e:
        checks["graphs"] = {"status": "error", "detail": str(e)}

    # Base de données
    try:
        db_ok = check_connection()
        checks["database"] = {"status": "ok" if db_ok else "unavailable"}
    except Exception as e:
        checks["database"] = {"status": "error", "detail": str(e)}

    # Statut global — DB dégradé = degraded (pas critique, fallback JSON actif)
    all_ok = all(v.get("status") == "ok" for v in checks.values())
    status_code = 200 if all_ok else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status":  "healthy" if all_ok else "degraded",
            "version": "6.0.0",
            "checks":  checks,
        }
    )

@app.get("/health", tags=["Santé"])
def health_check():
    """
    Health check pour load balancers et monitoring.
    **Public** — aucune authentification requise.
    """
    from backend.core.data_io import load_recipes
    from backend.db.session import check_connection
    try:
        n = len(load_recipes())
        db_ok = check_connection()
    except Exception:
        n, db_ok = 0, False
    return {
        "status":       "ok",
        "version":      "6.0.0",
        "dataset_size": n,
        "db":           "connected" if db_ok else "unavailable",
    }


# ── Health check ──
@app.get("/", tags=["Santé"])
def health():
    return {
        "status":  "ok",
        "version": "6.0.0",
        "project": "ALIM",
        "docs":    "/docs",
    }