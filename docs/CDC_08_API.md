# CDC 08 — API Publique

## Positionnement

L'API est un **produit B2B à part entière**, documentée, versionnée
et tarifée indépendamment du produit grand public.

Cas d'usage B2B prioritaires identifiés :
1. Scorer nutritionnellement une recette externe (ne venant pas du dataset)
2. Intégrer le moteur de recherche/recommandation végétarien dans une app tierce
3. Accéder au dataset de recettes + données nutritionnelles

---

## Fonctionnalités API — priorités B2B

### Tier 1 — Valeur différenciante maximale

**Scoring nutritionnel d'une recette externe**
```
POST /score/external_recipe
Payload : {title, ingredients, servings, diet}
Retour  : {global_score, nutrition_score, ajr_coverage,
           deficiencies, reliability_label}
```
> Cas d'usage : une app tierce soumet une recette de son propre dataset
> et reçoit un score nutritionnel complet basé sur CIQUAL.

**Recherche et recommandation**
```
POST /search/v3            → Recherche fuzzy + scoring adaptatif
POST /recommend            → Pipeline recommandation complet
POST /search/semantic      → Recherche par concept
GET  /recipes/top          → Top recettes selon profil
```

**Accès dataset**
```
GET  /recipes              → Liste paginée des recettes (skip/limit)
GET  /recipes/{id}         → Fiche recette complète
GET  /ingredients          → Dictionnaire des 302 ingrédients
GET  /nutrition/{id}       → Données nutritionnelles par recette
```

### Tier 2 — Fonctionnalités complémentaires

```
POST /mealplan             → Génération plan repas
POST /detect_deficiencies  → Carences sur un ensemble de recettes
POST /substitution/{id}    → Substituts d'un ingrédient
POST /score/unified        → Score global + adaptatif réconciliés
POST /vegan_variant/{id}   → Version vegan d'une recette
```

### Tier 3 — Modules spécialisés (plans Pro/Enterprise)

```
POST /cycle/score          → Adéquation recette × phase cycle
POST /multi_profile_score  → Score multi-profil (vegan+athlete...)
POST /enrich_nutrition_smart → Enrichissement base nutritionnelle
POST /simulate_recipe_world → Simulation coût + carbone + nutrition
```

---

## Authentification & sécurité

```
Header : X-API-Key: <clé>
```

- Clés générées par SHA-256 (`core/api_key.py`)
- Rate limiting par plan (100 req/60s par défaut)
- Validation des payloads via Pydantic
- Logs d'usage par clé (analytics)

---

## Versionnage

- Version actuelle : **v1** (routes sans préfixe de version)
- v2 prévue : préfixe `/v2/` pour ruptures de compatibilité
- Dépréciation : 6 mois de préavis avant suppression d'une route

---

## Documentation API

- **Swagger UI** auto-généré par FastAPI : `/docs`
- **ReDoc** : `/redoc`
- Guide d'intégration en français + anglais (v2)
- Collection Postman publique (v2)

---

## Intégrations tierces

### v1 — Google Calendar (déjà implémenté)

```
POST /mealplan/export_ics
Retour : fichier .ics compatible Google Calendar, Apple Calendar, Outlook
```

Permet à l'utilisateur d'importer son plan repas directement
dans son agenda personnel.

### v2 — Stripe (paiements)

Gestion des abonnements Premium et Famille + plans API B2B.
- Webhooks Stripe pour activation/désactivation des plans
- Jamais de données CB stockées en interne

### Hors périmètre v1

| Intégration | Raison du report |
|---|---|
| LLM externe (GPT, Claude) | Coût variable, latence, dépendance externe |
| Apps de courses (Bring!, AnyList) | API tierces instables, priorité faible |
| Appareils connectés | Complexité IoT, audience de niche |

---

## Routes actuelles (101 routes — v177)

Catégories principales :
- Scoring & évaluation : `/score/*`, `/ajr_score`, `/detect_deficiencies`
- Recherche : `/search/*`, `/recommend`, `/similar_recipes`
- Planification : `/mealplan`, `/mealplan/export_ics`, `/mealplan/diversity_score`
- Nutrition : `/nutrition/*`, `/multi_profile_score`
- Adaptation : `/adapt_recipe`, `/vegan_variant/*`, `/substitution/*`
- Utilisateurs : `/user/*`, `/create_user`, `/generate_api_key`
- Données : `/ingredients`, `/recipes`, `/normalize_recipe`
- Qualité : `/data_quality_audit`, `/validate_recipe_strict`
- Services : `/recommend`, `/recommend/dietary_filter`
