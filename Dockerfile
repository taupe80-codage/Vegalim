# ══════════════════════════════════════════════════════════════════════════════
# ALIM v6 — Dockerfile multi-stage
#
# Stage 1 (node)   : compile le frontend React/Vite → frontend/dist/
# Stage 2 (python) : API FastAPI + frontend compilé
#
# Build :
#   docker build --build-arg VITE_API_URL=https://api.mondomaine.com -t alim-api .
#
# L'URL de l'API est figée au moment du build (Vite remplace la variable).
# Par défaut (vide) : même origine — le frontend est servi par l'API.
# ══════════════════════════════════════════════════════════════════════════════


# ── Stage 1 : Build frontend ──────────────────────────────────────────────────
FROM node:24-alpine AS frontend-build

WORKDIR /build

# Dépendances npm en premier (cache Docker optimal)
COPY frontend/package*.json ./
RUN npm ci --silent

# Code source frontend
COPY frontend/ ./

# VITE_API_URL est injecté à la compilation — modifiable via --build-arg
ARG VITE_API_URL=
ENV VITE_API_URL=$VITE_API_URL

RUN npm run build


# ── Stage 2 : API Python ──────────────────────────────────────────────────────
FROM python:3.13-slim

WORKDIR /app

# Pas de paquet système : psycopg2-binary embarque sa propre libpq.

# Dépendances Python (couche cachée séparément du code)
COPY requirements.txt ./
RUN pip install --no-cache-dir --timeout 60 --retries 10 -r requirements.txt

# Code source backend
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Migrations Alembic (appliquées au démarrage via alembic upgrade head)
COPY alembic/ ./alembic/
COPY alembic.ini ./alembic.ini

# Frontend compilé (depuis stage 1)
COPY --from=frontend-build /build/dist ./frontend/dist

# Utilisateur non-root (bonne pratique sécurité)
RUN useradd -m -u 1001 alim \
    && chown -R alim:alim /app
USER alim

# Variables d'environnement runtime
ENV PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    ALIM_FRONTEND=react \
    APP_ENV=production

EXPOSE 8000

# 2 workers = bon équilibre mémoire/concurrence pour un VPS standard
# Ajuster selon les ressources : --workers $(nproc)
CMD ["uvicorn", "backend.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "2"]
