"""
ALIM v5 — Point d'entrée FastAPI.

Architecture propre :
  core/     → sécurité, JWT, rate limiting, logging, validation
  db/       → PostgreSQL via SQLAlchemy (fallback SQLite dev)
  services/ → logique métier orchestrée
  engine/   → 26 moteurs actifs (sur 103 disponibles dans l'archive)
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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path as _Path

from backend.core.logger import get_logger
from backend.api.router  import router

logger = get_logger("startup")


# 🔥 LIFESPAN CORRIGÉ

def _startup_checks(log) -> None:
    """Vérifie la configuration au démarrage — centralise tous les warnings."""
    cors = os.getenv("CORS_ORIGINS", "*")
    if cors == "*":
        log.warning(
            "⚠️  CORS ouvert (*) — définissez CORS_ORIGINS=https://votre-domaine.com en production"
        )
    else:
        log.info("CORS restreint à : %s", cors)

    if not os.getenv("HEALTH_DATA_KEY"):
        log.warning(
            "⚠️  HEALTH_DATA_KEY absent — données santé non chiffrées (non conforme RGPD Art. 9)"
        )

    if not os.getenv("SECRET_KEY") or os.getenv("SECRET_KEY", "").startswith("CHANGEZ"):
        log.warning("⚠️  SECRET_KEY non sécurisée — générez une clé aléatoire pour la production")

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        log.info("ℹ️  REDIS_URL absent — rate limiter en mémoire (inefficace multi-process)")

    log.info("✅ Configuration vérifiée")

    if os.getenv("LOG_FORMAT", "").lower() == "json":
        from backend.core.logger import _configure_json_logging
        _configure_json_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("═══ ALIM démarrage ═══")

    # ── Warm-up des caches ──
    try:
        from backend.core.data_io import (
            load_recipes, load_nutrition_graph, load_score_graph,
            load_availability_graph, load_ingredients_dict, load_prices,
            load_seasonality, load_scoring_profiles,
        )
        recipes = load_recipes()
        logger.info("Dataset chargé : %d recettes", len(recipes))
        load_nutrition_graph()
        load_score_graph()
        load_availability_graph()
        load_ingredients_dict()
        load_prices()
        load_seasonality()
        load_scoring_profiles()
        logger.info("Caches warm-up : 8 loaders prêts")
    except Exception as e:
        logger.warning("Warm-up partiel : %s", e)

    # 🔥 FIX CRITIQUE — TOUJOURS INITIALISER LA DB
    try:
        from backend.db.session import init_db
        init_db()
        logger.info("DB initialisée — tables garanties")
    except Exception as e:
        logger.error("Erreur init DB : %s", e)

    # (optionnel) vérifier la connexion
    try:
        from backend.db.session import check_connection
        if check_connection():
            logger.info("Connexion DB OK")
        else:
            logger.warning("DB non accessible")
    except Exception as e:
        logger.warning("Check DB : %s", e)

    _startup_checks(logger)

    logger.info("Application prête")
    yield
    logger.info("═══ ALIM arrêt ═══")


# ── Application FastAPI ──
app = FastAPI(
    title       = "ALIM — Plateforme Culinaire Végétarienne",
    description = (
        "API de recommandation végétarienne. 529 recettes, 40+ cuisines. "
        "Score CDC_03c 7 dimensions. Auth JWT (B2C) + API key (B2B). "
        "PostgreSQL avec fallback SQLite."
    ),
    version     = "5.0.0",
    lifespan    = lifespan,
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

# ── CORS ──
# En production, remplacer "*" par les domaines autorisés
_CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(RequestIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True if _CORS_ORIGINS != ["*"] else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes API ──
app.include_router(router)


# ── Sélection du frontend ──────────────────────────────────────────────────────
#
# ALIM_FRONTEND (variable d'environnement) :
#   auto    (défaut) → React build si frontend/dist/ existe, sinon vanilla
#   react           → React build  : frontend/dist/  (npm run build requis)
#   vanilla         → HTML mono-fichier : frontend_vanilla/
#
# Architecture des deux frontends :
#   frontend/         — React 19 + Vite (hash router, aucune dépendance serveur)
#                       Lancer : cd frontend && npm install && npm run build
#   frontend_vanilla/ — HTML+JS sans build step (dev sans Node.js)
#
_PROJECT_ROOT   = _Path(__file__).resolve().parent.parent.parent
_DIST           = _PROJECT_ROOT / "frontend" / "dist"
_VANILLA        = _PROJECT_ROOT / "frontend_vanilla"
_FRONTEND_MODE  = os.getenv("ALIM_FRONTEND", "auto").lower()

def _resolve_frontend() -> tuple[str, _Path]:
    """Retourne (mode_actif, chemin_index_html)."""
    if _FRONTEND_MODE == "react":
        if not _DIST.exists():
            raise RuntimeError(
                "ALIM_FRONTEND=react mais frontend/dist/ absent. "
                "Lancer : cd frontend && npm install && npm run build"
            )
        return "react", _DIST / "index.html"
    if _FRONTEND_MODE == "vanilla":
        return "vanilla", _VANILLA / "index.html"
    # auto : react si dist présent, sinon vanilla
    if _DIST.exists() and (_DIST / "index.html").exists():
        return "react", _DIST / "index.html"
    return "vanilla", _VANILLA / "index.html"

_frontend_mode, _frontend_index = _resolve_frontend()
logger.info("Frontend : %s → %s", _frontend_mode, _frontend_index)

# ── Montage des assets statiques ───────────────────────────────────────────────
if _frontend_mode == "react" and (_DIST / "assets").exists():
    # Build Vite : assets hashés sous /assets/
    app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")
    # favicon depuis dist/
    if (_DIST / "favicon.svg").exists():
        @app.get("/favicon.svg", include_in_schema=False)
        def favicon_react():
            return FileResponse(str(_DIST / "favicon.svg"))
elif _VANILLA.exists():
    # Vanilla : assets servis sous /static/
    app.mount("/static", StaticFiles(directory=str(_VANILLA)), name="static")


@app.get("/ui", include_in_schema=False)
@app.get("/ui/{path:path}", include_in_schema=False)
def frontend_app(path: str = ""):
    """
    Frontend ALIM.

    - react   : React 19 build Vite (frontend/dist/index.html)
    - vanilla : HTML mono-fichier  (frontend_vanilla/index.html)

    Hash router côté client → un seul index.html pour toutes les routes.
    """
    if not _frontend_index.exists():
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={
                "detail": "Frontend non disponible.",
                "hint":   "react → cd frontend && npm run build | vanilla → frontend_vanilla/ requis",
                "mode":   _frontend_mode,
            }
        )
    return FileResponse(str(_frontend_index))


# ── Middleware headers quota (B2B) ─────────────────────────────────────────────

@app.middleware("http")
async def add_quota_headers(request, call_next):
    """Injecte X-Plan et X-RateLimit-* dans les réponses des routes API key."""
    response = await call_next(request)
    # Déjà géré par auth_middleware._require_plan pour le 429
    # Ici on s'assure que X-Plan est présent si l'header X-Api-Key est fourni
    if "x-api-key" in request.headers and "x-plan" not in response.headers:
        response.headers["X-API-Version"] = "5.0.0"
    return response


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
        c = (r.get("iconic_status") or {}).get("cuisine_origin", "")
        if c:
            cuisines[c] += 1

    # Plans B2B avec quotas
    plans_info = {
        name: {
            "daily_limit": plan.get("daily_limit", 0),
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
        "version":      "5.0.0",
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

    # Statut global
    all_ok = all(v.get("status") == "ok"
                 for k, v in checks.items() if k != "database")
    status_code = 200 if all_ok else 503

    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=status_code,
        content={
            "status":  "healthy" if all_ok else "degraded",
            "version": "5.0.0",
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
        "version":      "5.0.0",
        "dataset_size": n,
        "db":           "connected" if db_ok else "unavailable",
    }

@app.get("/test", tags=["Sante"])
def test_recherche():
    """Test pipeline reco"""
    try:
        from backend.services.reco_service import recommend
        res = recommend("curry")
        return {
            "status": "ok",
            "message": f"{len(res)} recettes trouvées",
            "exemple": res[0].get("title_fr") if res else None,
        }
    except Exception as e:
        return {"status": "erreur", "detail": str(e)}


# ── Health check ──
@app.get("/", tags=["Santé"])
def health():
    return {
        "status":  "ok",
        "version": "5.0.0",
        "project": "ALIM",
        "docs":    "/docs",
    }