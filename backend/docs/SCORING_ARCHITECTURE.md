# Architecture du Scoring ALIM — CDC_03c

## Pipeline de recommandation

```
Requête utilisateur
        │
        ▼
┌─────────────────────────────────────────────────┐
│  recommendation_engine.py  (orchestrateur unique) │
│                                                   │
│  1. Profil utilisateur     profile_service        │
│  2. Recherche              search_engine_v3       │
│  3. Filtrage régime        filter_service         │
│  4. Scoring qualité   ──►  global_score_engine    │
│                       └──► adaptive_score_v4      │
│  5. Scoring pertinence     search_v3.final_score  │
│  6. Fusion                 0.65×quality + 0.35×rel│
│  7. Substitutions vegan    vegan_variant_engine   │
│  8. Personnalisation       learning_engine        │
│  9. Explicabilité          score_explainer        │
└─────────────────────────────────────────────────┘
        │
        ▼
   RecommendationResult
   {recipes, meta, timing_ms, profile_used}
```

## Formule de score final (CDC_03c §scoring)

```
final_score = W_QUALITY × quality_score + W_RELEVANCE × relevance_score + learning_bonus

où :
  W_QUALITY   = 0.65   (poids score qualité CDC_03c)
  W_RELEVANCE = 0.35   (poids pertinence recherche)
  learning_bonus ∈ [-2.0, +2.0]  (activé après 5 likes)
```

## Score qualité — 7 dimensions CDC_03c

| Dimension | Poids | Source |
|-----------|-------|--------|
| nutrition | 40% | recipe_scoring_graph_v1.json (CIQUAL) |
| authenticity | 20% | iconic_score × prestige cuisine |
| accessibility | 15% | ingredient_availability_graph (302 ingrédients) |
| cost | 15% | prices.json (budget €/portion) |
| ease | 5% | techniques + nb ingrédients + difficulty |
| carbon | 3% | carbon_footprint.json |
| flavor | 2% | flavor_pairing_graph + profil gustatif |

Calculé dans `global_score_engine.compute_global_score()`.

## Profils adaptatifs (adaptive_score_engine_v4)

Redistribuent les poids CDC sur les 7 dimensions :

| Profil | Priorité | Activé par |
|--------|----------|------------|
| default | Équilibre CDC | — |
| health_focus | nutrition +15% | health_goal=health |
| budget | cost +13%, accessibility +5% | budget=low |
| eco | carbon +15% | health_goal=eco |
| quick | ease +13% | — |
| diabetic | nutrition +15%, bonus IG bas | diet=diabete |
| anemia | nutrition +15%, bonus fer | health_goal=anemia |
| athlete | nutrition +10%, bonus protéines | health_goal=muscle |

## Score de pertinence

Issu de `search_engine_v3` : score normalisé [0-10] combinant :
- correspondance titres (fuzzy Levenshtein)
- correspondance ingrédients
- bonus saisonnalité

## Learning engine

Actif après ≥5 likes. Ajoute ±bonus sur `final_score` :
- +0.8 si cuisine favorite
- +0.4 si technique préférée
- +0.3 si difficulté habituelle
- +0.3 si durée habituelle
- -1.5 si recette explicitement dislikée

## Explicabilité

`score_explainer.explain(score_result)` → list[str]
Traduit les dims en labels : `"riche_en_nutriments"`, `"budget_économique"`, etc.
Exposé dans chaque recette via `score_reasons`.

## Fichiers clés

| Rôle | Fichier |
|------|---------|
| Orchestrateur | `backend/engine/recommendation_engine.py` |
| 7 dimensions | `backend/engine/global_score_engine.py` |
| Profils adaptatifs | `backend/engine/adaptive_score_engine_v4.py` |
| Scoring façade | `backend/services/scoring_service.py` |
| Explicabilité | `backend/engine/score_explainer.py` |
| Constantes | `backend/engine/config.py` |
