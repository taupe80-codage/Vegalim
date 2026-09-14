# ALIM v6 — Plateforme Culinaire Végétarienne

API de recommandation végétarienne et application web React.
820 recettes (dont 88 préparations de base), 100 cuisines, nutrition calculée
depuis CIQUAL / CNF / USDA. Auth JWT (B2C) + clé API (B2B).
PostgreSQL en production, SQLite en développement.

---

## Prérequis

- Python 3.13+ et Node.js 24+
- **Git LFS** : les 728 photos de recettes (`frontend/public/images/`) sont stockées
  avec Git LFS. Installer puis activer avant de cloner :

```bash
git lfs install
```

---

## Lancement rapide (développement)

```bash
pip install -r requirements-dev.txt
cp .env.example .env              # à la racine du projet
cd frontend && npm install && npm run build && cd ..
uvicorn backend.api.main:app --reload
```

- API et documentation : http://localhost:8000/docs
- Application : http://localhost:8000/ui
- Frontend en mode dev (rechargement à chaud) : `cd frontend && npm run dev`

Les migrations de base de données (Alembic) sont appliquées au démarrage.

---

## Variables d'environnement

Référence complète et commentée : [`.env.example`](.env.example).

| Variable | Rôle | Défaut |
|---|---|---|
| `APP_ENV` | `production` \| `development` | `development` (avertissement au démarrage) |
| `SECRET_KEY` | Clé JWT — **bloquante en production** | clé éphémère |
| `HEALTH_DATA_KEY` | Chiffrement Fernet des données de santé (RGPD Art. 9) — **bloquante en production** | données en clair |
| `ADMIN_EMAILS` | Emails autorisés sur `/admin/*` (en plus d'une clé API) | vide = admin désactivé |
| `DATABASE_URL` | `postgresql://user:pwd@host:5432/db` | SQLite `alim_dev.db` |
| `CORS_ORIGINS` | Origines autorisées (virgules) | `*` |
| `REDIS_URL` | Rate limiting partagé entre workers | mémoire |
| `METRICS_TOKEN` | Jeton exigé pour `/metrics` en production | — |
| `JWT_EXPIRE_MINUTES` | Durée de validité des jetons | `1440` |
| `RESET_TOKEN_TTL_MINUTES` | Durée des jetons de réinitialisation | `30` |
| `LOG_LEVEL` / `LOG_FORMAT` | Niveau / `json` pour des logs structurés | `INFO` / texte |

Le jeton de réinitialisation de mot de passe n'est renvoyé dans la réponse
qu'avec `APP_ENV=development` **explicite** (jamais par défaut).

---

## Structure

```
├── backend/
│   ├── api/            ← main.py, router.py, routes/ (auth, recipes, nutrition,
│   │                     planning, profile, ingredients, frigo, graph, admin)
│   ├── core/           ← config, sécurité/JWT, rate limiting, data_io, data_cache
│   ├── db/             ← SQLAlchemy (models, session, repositories)
│   ├── engine/         ← moteurs : reco, score, search, rule (régimes, carbone…),
│   │                     planning (courses, budget), nutrition, cycle
│   ├── services/       ← couche service (reco, filtres, profils, clés API…)
│   └── data/           ← dataset JSON (recettes, ingrédients, nutrition, graphes, prix)
├── frontend/           ← React 19 + Vite, hash router maison, tests Vitest
├── alembic/            ← migrations de schéma
├── scripts/            ← pipeline nutrition, outils recettes, prix
├── tests/              ← pytest (données, routes, sécurité, migrations, moteurs…)
└── docs/               ← cahier des charges (CDC_*)
```

Les données chargées par l'API sont mises en cache et **rechargées
automatiquement** quand un fichier JSON de `backend/data/` change (pas de
redémarrage nécessaire après un rebuild).

---

## Routes principales

| Méthode | Route | Accès | Description |
|---|---|---|---|
| POST | `/auth/register`, `/auth/login` | public (limité) | Compte, jeton JWT |
| POST | `/auth/forgot-password`, `/auth/reset-password` | public (limité) | Réinitialisation |
| DELETE | `/auth/account` | JWT | Suppression du compte (RGPD) |
| GET / POST | `/profil/`, `/profil/update` | JWT | Profil utilisateur |
| GET | `/recettes/top`, `/recettes/search`, `/recettes/{id}` | public | Catalogue |
| POST | `/recettes/recherche` | public, personnalisé si connecté | Recherche filtrée |
| POST | `/recettes/recommend` | JWT | Recommandation personnalisée |
| POST | `/nutrition/ajr_score` | public | Score AJR |
| GET | `/planning/mealplan` | public, personnalisé si connecté | Plan de repas |
| POST | `/planning/shopping_list_from_recipes` | public | Liste de courses chiffrée |
| PUT | `/planning/prices/{clé}` | JWT (limité) | Corriger un prix du catalogue |
| * | `/admin/*` | clé API + `ADMIN_EMAILS` | Pipeline, audits, rebuilds |
| GET | `/healthz`, `/stats`, `/metrics` | public (`/metrics` protégé en prod) | Supervision |

Documentation interactive complète : `/docs` (désactivée en production).

---

## Tests

```bash
pytest                              # backend
cd frontend && npm run lint && npm test && npm run build
```

La CI GitHub Actions (`.github/workflows/ci.yml`) lance pytest, le lint,
les tests et le build du frontend, puis le build Docker, à chaque push sur
`master`, `main` ou `develop`.

---

## Rebuild des données

Les sources brutes (CIQUAL, CNF, USDA — 97 Mo) ne sont pas versionnées :
les placer dans `backend/data/nutrition/raw/` ; leurs empreintes attendues sont
dans `backend/data/nutrition/logs/raw_sources_manifest.json`.

```bash
python scripts/nutrition/build_n2_direct.py --promote
python scripts/nutrition/build_dict_v2.py
python scripts/nutrition/build_indexes.py
python scripts/recipes/fix_recipe_diet_allergens.py
python scripts/recipes/build_derived_base_registry.py   # alterner avec la ligne précédente jusqu'à 0 changement
python scripts/recipes/rebuild_graphs.py
```

Portions irréalistes : `python scripts/recipes/propose_servings.py` produit une
proposition CSV à valider, appliquée avec `--apply`.

---

## Production (Docker)

```bash
cp .env.example .env    # APP_ENV=production, SECRET_KEY, HEALTH_DATA_KEY, POSTGRES_PASSWORD, CORS_ORIGINS…
docker compose up --build
```

Services : `api` (FastAPI + frontend compilé), `db` (PostgreSQL 16),
`redis`, `caddy` (HTTPS), `backup` (sauvegardes PostgreSQL).
