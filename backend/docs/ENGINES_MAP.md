# ENGINES_MAP — CDC → Engine → Fichier

## Dataset
- **791 recettes** (Migrées schema v6 unifié)
- **310 ingrédients** dans le dictionnaire
- **20 fichiers de tests**

## Engines actifs (37)

| CDC Requis | Engine | Fonction clé | Statut |
|------------|--------|--------------|--------|
| Recommandation unique | recommendation_engine | `recommend()` | ✅ Orchestrateur |
| Scoring 7 dim CDC_03c | global_score_engine | `compute_global_score()` | ✅ BaseEngine |
| Profils adaptatifs | adaptive_score_engine_v4 | `score()` | ✅ BaseEngine |
| Scoring façade | scoring_service | `score_recipe()` | ✅ Actif |
| Nutrition CIQUAL | nutrition_engine | `compute_nutrition()` | ✅ Actif |
| Nutrition formes cru/cuit | nutrition_form_engine | `adjust_for_form()` | ✅ CDC_05 |
| AJR / carences | ajr_scoring_engine | `compute_ajr_score()` | ✅ Actif |
| Détection carences | deficiency_detection_engine | `detect_deficiencies()` | ✅ Actif |
| Cycle féminin | cycle_engine | `cycle_score()` | ✅ Actif |
| Recherche | search_engine_v3 | `search()` | ✅ Actif |
| Orchestration recherche | search_orchestrator | `search()` | ✅ Actif |
| Similarité recettes | similarity_engine | `find_similar()` | ✅ Actif |
| Flags régime auto | diet_flag_auto_engine | `compute_flags()` | ✅ Actif |
| Taxonomies régime | diet_flag_engine | `NON_VEGAN` | ✅ Source unique |
| Apprentissage | learning_engine | `rank_with_learning()` | ✅ Actif |
| Fiabilité score | score_reliability_engine | `compute()` | ✅ Actif |
| Explicabilité | score_explainer | `explain()` | ✅ Actif |
| Durabilité CO₂ | sustainability_engine | `recipe_carbon_score()` | ✅ CDC_03c |
| Prix / budget | ingredient_price_engine | `recipe_price()` | ✅ CDC_03 |
| Doublons dataset | duplicate_recipe_detector | `report()` | ✅ CDC_04 |
| Règles culinaires | culinary_rule_engine | `validate()` | ✅ CDC_04 |
| Qualité données | culinary_data_quality_engine | `audit()` | ✅ Actif |
| Filtrage régimes | filter_service | `apply_diet_filter()` | ✅ Actif |
| Substitutions vegan | vegan_variant_engine | `get_vegan_variant()` | ✅ Actif |
| Plan repas hebdo | meal_planner | `generate_weekly_plan()` | ✅ Actif |
| Liste de courses | shopping_engine | `generate_shopping_list()` | ✅ Actif |
| Saisonnalité | seasonality_engine | `ingredients_in_season()` | ✅ Actif |
| Portions | servings_engine | `scale_recipe()` | ✅ Actif |
| Réutilisation ingrédients | ingredient_reuse_optimizer | `analyze()` | ✅ Actif |
| Synonymes ingrédients | ingredient_synonym_resolver | `resolve()` | ✅ Actif |
| Health score | health_score_engine | `compute_health_score()` | ✅ Actif |
| Multi-profils nutrition | multi_profile_nutrition_engine | `adapt_ajr_multi()` | ✅ Actif |
| Pipeline batch | pipeline | `run()` | ✅ Actif |
| Graphe ingrédients | graph_engine | `analyze_recipe()` | ✅ Actif |
| Dictionnaire ingrédients | dictionary_engine | `normalize()` | ✅ Actif |
| Embedding sémantique | embedding_engine | `search()` | ✅ Via search_orchestrator |
| Tokens de recherche | search_token_generator | `batch_generate()` | ✅ 53 tokens/recette |

## Constantes métier centralisées — `backend/engine/config.py`

| Constante | Valeur | Usage |
|-----------|--------|-------|
| `W_QUALITY` | 0.65 | Poids score qualité CDC_03c |
| `W_RELEVANCE` | 0.35 | Poids pertinence recherche |
| `MIN_LIKES_TO_ACTIVATE` | 5 | Seuil learning_engine |
| `MAX_LEARNING_BONUS` | 2.0 | Bonus/malus learning (±) |
| `RELIABILITY_HIGH` | 0.80 | Seuil 🟢 score fiabilité |
| `RELIABILITY_MEDIUM` | 0.50 | Seuil 🟡 score fiabilité |
| `SERVINGS_DEFAULT` | 4 | Portions par défaut |
| `FRYING_CAP_G` | 20 | Huile friture max (g) |

## Archivés — `backend/engine/_archive/`

Logique remplacée par data_io, admin routes ou repositories.
Voir `_archive/README.md`.
