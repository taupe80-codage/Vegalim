# ALIM v6 — Plateforme Culinaire Végétarienne

API de recommandation végétarienne. 529+ recettes, 40+ cuisines.
Score CDC v4 7 dimensions. Auth JWT (B2C) + API key (B2B).
PostgreSQL avec fallback SQLite.

---

## Lancement rapide

```bash
# 1. Dépendances Python
pip install -r requirements.txt

# 2. Variables d'environnement (minimum)
export SECRET_KEY="votre-cle-secrete-longue-et-aleatoire"

# 3. Démarrage
uvicorn backend.api.main:app --reload
# API : http://localhost:8000/docs
# UI  : http://localhost:8000/ui
```

---

## Frontends

Deux frontends coexistent. `ALIM_FRONTEND` détermine lequel est servi.

| Mode | Variable | Prérequis | Usage |
|---|---|---|---|
| `auto` (défaut) | — | — | React si `frontend/dist/` existe, sinon vanilla |
| `react` | `ALIM_FRONTEND=react` | `npm run build` | Production |
| `vanilla` | `ALIM_FRONTEND=vanilla` | — | Dev sans Node.js |

### Build React (une fois)

```bash
cd frontend
npm install   # ~96 Mo — jamais commité (voir .gitignore)
npm run build # génère frontend/dist/
```

### Vanilla (sans Node.js)

`frontend_vanilla/index.html` — HTML + JS mono-fichier, aucune dépendance.
Servi automatiquement si `frontend/dist/` est absent.

---

## Variables d'environnement

| Variable | Description | Défaut |
|---|---|---|
| `SECRET_KEY` | Clé JWT — **obligatoire en prod** | clé éphémère (dev) |
| `DATABASE_URL` | `postgresql://user:pwd@host:5432/db` | SQLite `alim_dev.db` |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Paramètres PG individuels | — |
| `ALIM_ENV` | `development` → active les helpers dev (reset token visible) | `production` |
| `ALIM_FRONTEND` | `auto` \| `react` \| `vanilla` | `auto` |
| `CORS_ORIGINS` | Origines CORS (virgule-séparées) | `*` |
| `HEALTH_DATA_KEY` | Clé chiffrement données santé (RGPD Art. 9) | — |
| `REDIS_URL` | Rate limiter Redis (multi-process) | mémoire (dev) |
| `LOG_LEVEL` | `DEBUG` \| `INFO` \| `WARNING` | `INFO` |
| `LOG_FORMAT` | `json` → logs structurés | texte |
| `DB_ECHO` | `true` → logs SQL SQLAlchemy | `false` |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | Pool PG | `5` / `10` |
| `RESET_TOKEN_TTL_MINUTES` | TTL tokens reset mot de passe | `30` |

---

## Structure

```
project_final_v6_migrated/
├── backend/              ← FastAPI (API + moteurs + DB)
│   ├── api/              ← Routes + main.py + router.py
│   │   └── routes/       ← auth, recipes, nutrition, planning, admin, ingredients, frigo
│   ├── core/             ← Sécurité, JWT, rate limiting, data_io, logger, validators
│   ├── db/               ← SQLAlchemy (models, session, migrations, repositories)
│   ├── engine/           ← 20+ moteurs Python (reco, score, search, cycle, nutrition…)
│   │   ├── reco_engine/  ← orchestrator, personalization, scoring
│   │   ├── score_engine/ ← quality, reliability, ajr, health, explainer
│   │   ├── search_engine/← core, similar, resolver
│   │   ├── rule_engine/  ← diet, seasonality, validation, carbon, variants
│   │   └── planning_engine/ ← servings, budget
│   └── services/         ← Couche service (scoring, reco, filter, profile, user…)
├── frontend/             ← React 19 + Vite + hash router custom
│   └── src/
│       ├── pages/        ← 7 pages (Home, RecipeDetail, Frigo, Planning, Nutrition, Profile, CycleAstro)
│       ├── components/   ← 4 composants (Navbar, RecipeCard, AuthModal, RecipeLegend)
│       ├── api.js        ← Couche client centralisée
│       ├── Router.jsx    ← Hash router custom (zéro dépendance)
│       └── AuthContext.jsx
├── alim_engine/          ← Scripts batch autonomes (corrector, rewriter, pipeline)
├── backend/data/         ← Dataset JSON
│   ├── recipes/          ← recipes.json (4.4 MB), recipes_v2.json (4.8 MB)
│   ├── ingredients/      ← dictionnaire, fr_to_en_mapping, ingredient_physical
│   ├── graphs/           ← 28 graphes JSON (nutrition, scoring, flavor, cycle…)
│   ├── nutrition/        ← nutrition_database.json
│   └── modules/          ← seasonality, astro_nutrition
├── tests/                ← 12 fichiers pytest (intégration, DB, engines, routes…)
├── scripts/              ← Scripts utilitaires (build_index, import_data…)
└── docs/                 ← CGU + documentation
```

---

## Routes API principales

| Méthode | Route | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | — | Créer un compte |
| POST | `/auth/login` | — | Token JWT |
| POST | `/auth/forgot-password` | — | Demande reset |
| POST | `/auth/reset-password` | — | Reset mot de passe |
| POST | `/auth/refresh` | JWT | Renouveler token |
| DELETE | `/auth/account` | JWT | Supprimer compte (RGPD) |
| GET | `/profil/` | JWT | Lire profil |
| POST | `/profil/update` | JWT | Mettre à jour |
| POST | `/recettes/recherche` | JWT | Recherche paginée |
| GET | `/recettes/top` | JWT | Top recettes |
| POST | `/recommend` | JWT | Recommandation personnalisée |
| GET | `/nutrition/ajr_score` | — | Score AJR |
| GET | `/planning/mealplan` | API key | Plan 7 jours |
| POST | `/planning/shopping_list` | — | Liste de courses |
| POST | `/admin/pipeline` | API key | Relancer pipeline |
| POST | `/admin/diet_flags/rebuild` | API key | Recalculer diet flags |
| GET | `/healthz` | — | Health check détaillé |
| GET | `/stats` | — | Statistiques plateforme |
| GET | `/ui` | — | Interface utilisateur |

---

## Tests

```bash
# Tous les tests
pytest

# Par catégorie
pytest tests/test_data_integrity.py   # invariants dataset
pytest tests/test_routes.py           # logique API
pytest tests/test_db.py               # base de données
pytest tests/test_pipeline.py         # pipeline scoring
```

---

## Production

```bash
# PostgreSQL + workers multiples
export DATABASE_URL="postgresql://user:pwd@host:5432/alim_db"
export SECRET_KEY="$(openssl rand -hex 32)"
export ALIM_ENV="production"
export CORS_ORIGINS="https://votre-domaine.com"

uvicorn backend.api.main:app --workers 4 --host 0.0.0.0 --port 8000
```

> `ALIM_ENV=production` désactive `_dev_reset_token` dans les réponses auth.
> `HEALTH_DATA_KEY` requis pour le chiffrement RGPD des données de santé.

## a faire
corriger pipeline pour composite_ingredients.json
La formule de calcul pour le pipeline sera:
# Nutrition de X grammes de composite_ingredient
ratio = x / batch_yield["quantity"]  # ex: 10g de garam_masala sur batch de 50g = 0.2
for comp in components:
    contrib = comp["quantity"] * ratio  # quantité effective de ce composant
    # → lookup dans nutrition table

