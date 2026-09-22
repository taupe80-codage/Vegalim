# BRIEF PROJET ALIM_V2 — Pour collaboration avec ChatGPT

> **Document historique (état d'avril 2026, projet ALIM_V2).** Les chiffres qui suivent
> (529 recettes, 161 tests, 23 routes…) sont périmés : voir `README.md` pour l'état actuel
> (731 recettes, 99 cuisines).

## Contexte

Ce document décrit l'état exact du projet **ALIM_V2** afin que tu puisses
contribuer efficacement sans régression. Le projet est une plateforme de
recommandation culinaire végétarienne mondiale.

**Règle absolue : ne jamais proposer de remplacer un fichier existant
par une version plus simple. Toujours construire par-dessus ce qui existe.**

---

## Stack technique

```
Backend  : Python 3.12 + FastAPI
Auth B2C : JWT Bearer (passlib bcrypt + python-jose)
Auth B2B : API key SHA-256 + plans free/starter/pro
BDD      : PostgreSQL via SQLAlchemy 2.0 (fallback SQLite en dev)
Tests    : pytest + TestClient FastAPI + unittest.mock
```

---

## Structure du projet (ne pas modifier)

```
ALIM_V2/
├── backend/
│   ├── api/
│   │   ├── main.py              ← point d'entrée FastAPI + lifespan
│   │   ├── router.py            ← agrégateur de routeurs
│   │   └── routes/
│   │       ├── auth.py          ← POST /auth/register /auth/login DELETE /auth/account
│   │       ├── profile.py       ← GET/POST/DELETE /profil/
│   │       ├── recipes.py       ← POST /recettes/recherche GET /recettes/top + graphe
│   │       ├── nutrition.py     ← AJR, carences, cycle féminin
│   │       ├── planning.py      ← plan semaine, courses, export .ics
│   │       └── admin.py         ← audit qualité, stats, pipeline
│   │
│   ├── core/                    ← NE PAS TOUCHER sauf ajout
│   │   ├── logger.py            ← get_logger(__name__)
│   │   ├── validators.py        ← is_valid_recipe(), safe_float(), is_valid_diet()
│   │   ├── data_io.py           ← load_json() sécurisé + cache
│   │   ├── security.py          ← bcrypt hash/verify
│   │   ├── jwt_handler.py       ← JWT (SECRET_KEY depuis env)
│   │   ├── deps.py              ← get_user() Bearer + get_db()
│   │   ├── rate_limiter.py      ← 10 req/min/IP sur /auth/login
│   │   └── auth_deps.py         ← get_user JWT + require_api_key + require_feature
│   │
│   ├── db/                      ← NE PAS TOUCHER sauf ajout
│   │   ├── models.py            ← 5 tables : users, user_profiles, api_users, api_keys, daily_quotas
│   │   ├── session.py           ← connexion PG + fallback SQLite + get_db()
│   │   ├── repositories.py      ← UserRepository, UserProfileRepository, ApiKeyRepository, QuotaRepository
│   │   └── migrations.py        ← init_db() + migrate_from_json()
│   │
│   ├── engine/                  ← 28 moteurs actifs
│   │   ├── config.py            ← DATA_ROOT (chemin données)
│   │   ├── global_score_engine  ← score 7D CDC_03c (nutrition 40%)
│   │   ├── graph_engine         ← graphe ingrédients (benefits/risks/cycle/subs)
│   │   ├── search_engine_v3     ← recherche fuzzy + adaptatif + saisonnalité
│   │   ├── cycle_engine         ← 4 phases cycle féminin
│   │   ├── meal_planner         ← plan 7 jours
│   │   ├── auth_middleware      ← clés API + plans B2B
│   │   ├── embedding_engine     ← TF-IDF sémantique
│   │   ├── nutrition_engine     ← calcul nutrition depuis CIQUAL
│   │   ├── ajr_scoring_engine   ← AJR (apports journaliers recommandés)
│   │   ├── deficiency_detection ← carences nutritionnelles
│   │   ├── health_score_engine  ← score santé plan semaine
│   │   ├── vegan_variant_engine ← variantes vegan
│   │   └── ... 15 autres ...
│   │
│   ├── services/                ← orchestration métier
│   │   ├── user_service.py      ← create/authenticate/delete + fallback JSON→PG
│   │   ├── profile_service.py   ← get/set/delete profil + whitelist champs
│   │   ├── filter_service.py    ← apply_diet_filter() 5 régimes
│   │   ├── reco_service.py      ← pipeline recommend() normalisé 0-10
│   │   ├── recommendation_service.py ← pipeline étendu avec health_score
│   │   ├── scoring_service.py   ← score_recipe() global+adaptatif
│   │   ├── substitution_service ← apply_substitutions() avec tracking
│   │   └── dietary_service.py   ← filtres avancés (diabète, cycle, astro)
│   │
│   └── data/
│       ├── culinary_project/    ← dataset complet
│       │   ├── recipes/recipes.json          ← 529 recettes (40+ cuisines)
│       │   ├── graphs/recipe_nutrition_graph_v1.json  ← nutrition CIQUAL 529 recettes
│       │   ├── graphs/recipe_scoring_graph_v1.json    ← scores pré-calculés
│       │   ├── data/ingredients_dictionary.json       ← 302 ingrédients
│       │   └── data/nutrition_database.json           ← base nutritionnelle CIQUAL
│       ├── graph/ingredient_graph.json  ← 19 ingrédients avec benefits/risks/cycle
│       ├── users.json           ← comptes B2C (ou PostgreSQL si configuré)
│       └── substitutions.json   ← 6 règles de substitution
│
├── tests/
│   ├── test_engines.py    ← 15 tests engines core
│   ├── test_routes.py     ← 18 tests API (TestClient FastAPI)
│   ├── test_db.py         ← 20 tests BDD (SQLite en mémoire)
│   ├── test_stability.py  ← 20 tests robustesse (validators, data_io)
│   ├── test_pipeline.py   ← 24 tests dataset v177
│   └── test_missing.py    ← 64 tests services/engines précédemment non couverts
│                             TOTAL : 161 tests
│
├── cahier_des_charges/    ← 17 fichiers CDC (vision, scoring, roadmap…)
├── requirements.txt
└── README.md
```

---

## Routes API actives (23 routes)

### Auth B2C — JWT Bearer
```
POST   /auth/register          Corps : {email, password (≥8 chars)}
POST   /auth/login             Corps : {email, password} → {token, token_type}
DELETE /auth/account           Header : Authorization: Bearer <token>
```

### Profil utilisateur
```
GET    /profil/                Header : Authorization: Bearer <token>
POST   /profil/update          Header : Bearer | Corps : {diet?, allergies?, budget?...}
DELETE /profil/                Header : Bearer
```

Champs profil autorisés (whitelist stricte) :
`diet`, `allergies`, `budget`, `servings`, `cycle_phase`, `health_goal`,
`liked_ingredients`, `disliked_ingredients`

Régimes valides : `vegetarien`, `vegan`, `diabete`, `hyperproteine`, `gluten_free`

### Recettes & Recommandations
```
POST   /recettes/recherche     Bearer | {query, filtre?} + ?skip=0&limit=20
GET    /recettes/top           Bearer | ?skip=0&limit=20
GET    /recettes/graph/ingredient/{name}   Bearer
GET    /recettes/graph/cycle/{phase}       Bearer
POST   /recettes/graph/analyze             Bearer | {recipe, profile}
```

### Nutrition
```
POST   /nutrition/ajr_score           {recipe_id} ou {nutrition: dict}
POST   /nutrition/detect_deficiencies {nutrition, profiles?}
POST   /nutrition/cycle_score         {recipe, phase} ou {recipe, cycle_day}
POST   /nutrition/alerts              {plan} ou {recipe_ids}
```

### Planification
```
GET    /planning/mealplan              API key X-API-Key | ?diet&servings&month
POST   /planning/mealplan/export_ics  {plan, start_date}
POST   /planning/shopping_list         {plan}
GET    /planning/seasonal              ?month=1..12
POST   /planning/diversity_score       {plan}
```

### Admin
```
GET    /admin/quality_audit    API key (plan quality_audit)
GET    /admin/api_stats        API key
POST   /admin/pipeline         API key | {profile?, limit?, skip_errors?}
```

### Prototype (sans auth)
```
GET    /prototype/recommend    ?vegetarian&vegan&high_protein&low_sugar&diabetes&gluten_free&limit
```

---

## Score final — CDC_03c (7 dimensions, immuable)

```python
global_score = (
    nutrition     * 0.40 +  # CIQUAL — priorité absolue
    authenticity  * 0.20 +  # iconic_score × prestige cuisine
    accessibility * 0.15 +  # disponibilité en France
    cost          * 0.15 +  # budget €/portion
    ease          * 0.05 +  # complexité technique
    carbon        * 0.03 +  # empreinte CO₂
    flavor        * 0.02    # cohérence profil gustatif
)
# Tous les scores sont normalisés [0, 10] et retournés dans la réponse
```

---

## Authentification — deux systèmes

### B2C (utilisateurs) — JWT Bearer
```python
# Header obligatoire sur toutes les routes protégées
Authorization: Bearer <token_jwt>

# Obtenir le token
POST /auth/login {"email": "user@example.com", "password": "motdepasse123"}
→ {"token": "eyJ...", "token_type": "Bearer"}
```

### B2B (développeurs) — API key SHA-256
```python
# Header
X-API-Key: <clé_api_brute>

# Plans disponibles
free    → 50 req/jour  | mealplan ✗
starter → 500 req/jour | mealplan ✓
pro     → 5000 req/jour| tout ✓

# Créer un compte B2B
POST /create_user {"email": "dev@company.com", "plan": "starter"}
```

---

## Base de données — PostgreSQL

### Tables (SQLAlchemy)
```
users         : email (PK), password_hash, plan, is_active, timestamps
user_profiles : id, user_email (FK), diet, allergies, liked_ingredients,
                disliked_ingredients, budget, servings, cycle_phase,
                health_goal, timestamps
api_users     : user_id (UUID PK), email, plan, is_active
api_keys      : key_hash (SHA-256 PK), user_id (FK), is_active, expires_at
daily_quotas  : key_hash, quota_date, count
```

### Démarrage
```bash
export SECRET_KEY="cle-longue-aleatoire"
export DATABASE_URL="postgresql://user:pwd@host:5432/alim_db"
python -m backend.db.migrations    # crée tables + migre JSON → PG
uvicorn backend.api.main:app --reload
```

### Fallback automatique
Si `DATABASE_URL` n'est pas défini → SQLite `alim_dev.db` automatiquement.
Les services `user_service` et `profile_service` détectent la disponibilité
de la BDD et basculent sur JSON si indisponible.

---

## Conventions de code — OBLIGATOIRES

### Logging
```python
from backend.core.logger import get_logger
logger = get_logger(__name__)
logger.info("Message avec %s", variable)   # jamais de f-string dans les logs
```

### Chargement JSON
```python
from backend.core.data_io import load_json, load_recipes
data = load_json(path, default={})   # jamais json.load(open(...)) directement
```

### Validation
```python
from backend.core.validators import is_valid_recipe, safe_float, is_valid_diet
if not is_valid_recipe(recipe):
    continue   # log automatique dans is_valid_recipe()
```

### Imports depuis backend/
```python
from backend.core.xxx import ...    # depuis routes/ et services/
from engine.xxx import ...          # depuis engine/ (chemin relatif)
```

### Gestion d'erreur
```python
# Chaque étape critique dans un try/except avec log
try:
    results = some_engine_call()
    logger.debug("Résultat : %d éléments", len(results))
except Exception as e:
    logger.error("Erreur engine : %s", e)
    results = []
```

---

## Tests — comment les écrire

```python
# Modèle à suivre (voir tests/test_missing.py)
from unittest.mock import patch

def test_mon_service():
    with patch("engine.mon_engine.ma_fonction", return_value={"score": 7.5}):
        from backend.services.mon_service import ma_fonction
        result = ma_fonction({"ingredients": ["lentils"]})
    assert result["score"] >= 0

# Pour les tests de routes (voir tests/test_routes.py)
from fastapi.testclient import TestClient
from backend.api.main import app
client = TestClient(app)

def test_ma_route(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.services.user_service._FILE", tmp_path / "u.json")
    r = client.post("/auth/register", json={"email": "t@t.com", "password": "password123"})
    assert r.status_code == 201
```

---

## Ce qui est EN DEHORS du périmètre V2

Ces engines existent dans l'archive mais ne sont PAS dans V2 (orphelins).
À réinjecter uniquement si une route spécifique en a besoin :

```
advanced_recipe_search_engine, ai_confidence_engine, ai_recipe_generator,
auto_learning_engine, auto_menu_generator, connected_correction_engine,
culinary_graph_orchestrator, culinary_knowledge_graph_engine,
culinary_learning_engine, culinary_rule_engine, culinary_self_improvement_engine,
culinary_simulation_engine, culinary_world_simulation_engine,
data_layer_manager, dish_canonicalization_engine, dish_dictionary_builder,
dish_registry_engine, dish_similarity_graph_engine, dish_validation_engine,
duplicate_recipe_detector, flavor_chemistry_engine, fridge_engine,
graph_orchestrator_engine, graph_query_engine, ingredient_composite_resolver,
ingredient_price_engine, ingredient_price_intelligence_engine,
ingredient_reuse_optimizer, ingredient_roles_engine, ingredient_synonym_resolver,
ingredient_transformation_engine, intelligence_layer_engine, learning_engine,
meal_plan_optimizer, meal_structure_engine (stub), meta_graph_engine (stub),
multi_site_scraper, orchestrator_engine, quality_scoring_engine,
quantity_adjustment_engine, real_recipe_extractor_engine,
recipe_adaptation_engine, recipe_evolution_engine, recipe_import_factory,
recipe_import_pipeline, recipe_ranking_engine, recipe_search_engine,
recipe_validator_engine, safe_normalization_engine, score_comparison_engine,
score_reliability_engine, search_engine_v2, search_orchestrator,
search_pipeline_connector, servings_engine, similarity_engine,
smart_grocery_engine, smart_grocery_optimization_engine,
smart_nutrition_enrichment_engine, smart_recipe_adaptation_engine,
smart_scraper_controller, substitution_scoring_engine, taste_profile_engine,
technique_learning_engine, title_normalization_engine, validation_engine,
vegetarian_detection_engine, weekly_nutrition_engine
```

**Procédure pour en réinjecter un :**
1. Copier le fichier dans `ALIM_V2/backend/engine/`
2. Créer ou étendre une route dans `backend/api/routes/`
3. Ajouter au moins 3 tests dans `tests/`

---

## Prochaines étapes (roadmap CDC)

1. **Dataset → 1 000 recettes** (priorité n°1 CDC_12)
   - Cuisines manquantes : Afrique subsaharienne, Amérique Latine, raw food
   - Chaque recette : id, title_fr, title_original, ingredients[], nutrition{},
     diet_flags{}, tags[], prep_time_min, cook_time_min, difficulty, recipe_origin

2. **Interface Next.js** (priorité n°2 CDC_12)
   - Stack : Next.js 14 + Tailwind + shadcn/ui
   - Pages minimales : /search, /recipe/[id], /profile, /plan

3. **photo_url** sur les 529 recettes (0% actuellement)

---

## Questions à poser avant de coder

Avant de proposer du code, réponds à ces questions :
1. Le fichier que je veux créer/modifier existe-t-il déjà dans V2 ?
2. Mon code utilise-t-il `get_logger(__name__)` pour le logging ?
3. Mon code utilise-t-il `load_json()` au lieu de `json.load(open())` ?
4. Ai-je écrit au moins 3 tests pour ce que j'ajoute ?
5. L'engine que j'utilise est-il dans les 28 actifs de V2, ou dois-je le réinjecter ?

---

## Exemple de contribution correcte

**Contexte :** ajouter une route `GET /recettes/fridge` qui retourne
les recettes faisables avec les ingrédients du frigo.

**Étape 1 — Réinjecter l'engine :**
```bash
cp ALIM_ARCHIVE/backend/engine/fridge_engine.py ALIM_V2/backend/engine/
```

**Étape 2 — Ajouter la route dans recipes.py :**
```python
@router.get("/fridge", tags=["Recettes"])
def fridge(
    items: str = Query(..., description="Ingrédients séparés par virgule"),
    max_missing: int = Query(default=2, ge=0, le=5),
    user: dict = Depends(get_user),
):
    """Recettes faisables avec les ingrédients du frigo."""
    try:
        from backend.engine.fridge_engine import recipes_from_ingredients
        result = recipes_from_ingredients(items.split(","), max_missing)
        logger.info("Fridge query : %d ingrédients → %d recettes", len(items.split(",")), len(result))
        return {"items": items.split(","), "results": result}
    except Exception as e:
        logger.error("fridge_engine : %s", e)
        raise HTTPException(status_code=500, detail=str(e))
```

**Étape 3 — Tests :**
```python
def test_fridge_retourne_resultats(monkeypatch, tmp_path):
    monkeypatch.setattr("backend.services.user_service._FILE", tmp_path / "u.json")
    # ...
```

---

*Document généré depuis ALIM_V2 — état au 22 mars 2026*
*161 tests | 84 fichiers Python | 529 recettes | 23 routes actives*
