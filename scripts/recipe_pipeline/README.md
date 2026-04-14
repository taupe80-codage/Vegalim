# ALIM — Moteur de Reconstitution Culinaire

Pipeline Python modulaire en 7 étapes, **100% gratuit**, pour collecter,
normaliser, dédupliquer, regrouper par variantes et synthétiser des recettes
végétariennes internationales au format CDC v4.

```
alim_engine/
├── config/
│   └── schema.py          # Schéma CDC v4, constantes, dictionnaires
├── sources/
│   └── collector.py       # TheMealDB · Wikibooks · RecipeNLG
├── engine/
│   ├── parser.py          # Normalisation brute → CDC v4
│   ├── clusterer.py       # TF-IDF + clustering agglomératif
│   ├── synthesizer.py     # Groq / Ollama / stub
│   └── validator.py       # Règles métier + quality_score
├── pipeline.py            # Runner principal (CLI)
└── requirements.txt
```

---

## Installation

```bash
pip install -r requirements.txt
```

Pour la synthèse LLM (optionnel — le pipeline tourne sans) :

```bash
# Option A : Groq (gratuit, ~500 req/jour, ultra-rapide)
export GROQ_API_KEY=gsk_...

# Option B : Ollama local (zéro coût, nécessite GPU recommandé)
curl -fsSL https://ollama.com/install.sh | sh
ollama pull mistral
```

---

## Utilisation

### Pipeline complet (TheMealDB → JSON CDC v4)

```bash
python pipeline.py --sources mealdb wikibooks --output output/recipes.json
```

### Avec synthèse Groq

```bash
GROQ_API_KEY=gsk_... python pipeline.py \
  --sources mealdb wikibooks \
  --output output/recipes.json \
  --llm-backend groq
```

### Valider + corriger un fichier CDC existant (gratuit, sans LLM)

```bash
python pipeline.py \
  --from-cdc recipes_v2.json \
  --validate-only \
  --output recipes_v3.json
```

### Depuis des données brutes déjà collectées

```bash
python pipeline.py \
  --from-raw raw_collected.json \
  --output output/recipes.json \
  --llm-backend stub
```

### Debug sur un petit échantillon

```bash
python pipeline.py \
  --sources mealdb \
  --max-recipes 20 \
  --max-clusters 5 \
  --output output/test.json \
  --llm-backend stub
```

---

## Utilisation modulaire (Python)

```python
from sources.collector import collect_mealdb, search_mealdb
from engine.parser import parse_batch
from engine.clusterer import cluster_recipes, deduplicate
from engine.synthesizer import RecipeSynthesizer
from engine.validator import validate_batch, quality_report

# 1. Collecter
raw = collect_mealdb(categories=["Vegetarian"], max_per_category=30)

# 2. Parser
recipes = parse_batch(raw)

# 3. Dédupliquer
recipes = deduplicate(recipes, similarity_threshold=0.92)

# 4. Cluster
clusters, stats = cluster_recipes(recipes, similarity_threshold=0.65)

# 5. Synthétiser (stub = pas de LLM)
synth = RecipeSynthesizer(force_backend="stub")
synthesized = synth.synthesize_batch(clusters)

# 6. Valider
valid, reports, agg = validate_batch(synthesized, auto_fix=True, min_score=0.5)
print(quality_report(reports))
```

---

## Paramètres clés

| Paramètre | Défaut | Description |
|---|---|---|
| `--cluster-threshold` | 0.65 | Distance cosinus max dans un cluster (0=clone, 1=différent) |
| `--dedup-threshold` | 0.92 | Seuil de déduplication (plus haut = moins agressif) |
| `--min-score` | 0.40 | Score qualité minimum pour conserver une recette |
| `--max-variants` | 5 | Variantes max par cluster envoyées au LLM |
| `--llm-backend` | auto | `groq` / `ollama` / `stub` |

---

## Schéma CDC v4

Chaque recette exportée suit ce schéma :

```json
{
  "id": "hummus_libanais_a3f9c2",
  "titles": {"original": "Hummus", "fr": "Houmous libanais", "en": "Lebanese Hummus"},
  "description": "...",
  "origin": {"cuisine": "levantine", "country": "lebanon", "region": "", "city": ""},
  "servings": 4,
  "timing": {"prep_active_min": 15, "prep_passive_min": 0, "cook_min": 0, "total_min": 15},
  "composition": [
    {"ingredient": "chickpeas", "quantity": 400, "unit": "g", "meta": {"role": "base", ...}}
  ],
  "instructions": ["Étape 1...", "Étape 2..."],
  "tags": {"diet": ["vegan", "gluten_free"], "allergens": ["sesame"], "technique": [], "process": []},
  "diet_flags": {"vegan": true, "vegetarian": true, "gluten_free": true, ...},
  "equipment": ["blender"],
  "difficulty_level": "easy",
  "dish_type": "dip",
  "nutrition": {"kcal": null, ...},
  "_source": "synthesized",
  "_cluster_id": "cluster_0042",
  "_quality_score": 0.87,
  "_flags": [],
  "_corrections_log": ["tag_vegan_added", "allergens_added:sesame"]
}
```

---

## Architecture des flux de données

```
TheMealDB API ──┐
Wikibooks HTML ─┼──► collect_all() ──► parse_batch() ──► deduplicate()
RecipeNLG parq ─┘
                                                              │
                                                    cluster_recipes()
                                                              │
                                                    RecipeSynthesizer
                                                    (Groq/Ollama/stub)
                                                              │
                                                    validate_batch()
                                                              │
                                                    CDC v4 JSON + report
```
