# PIPELINE NUTRITION — ALIM v7
> Mise à jour : 2026-05-17
> État : ✅ Stable — Architecture 100% déterministe, source-ID driven

---

## Architecture v7

Pipeline en **3 étapes** :

```
RAW SOURCES ────────────────────────────────────────────────────────────
  CIQUAL 2025 (xlsx)  ─┐
  USDA FDC (json)      ├─→  build_n2_direct.py  →  nutrition_v2.json
  CNF 2015 (csv)       ┘              ↑                      │
                           ingredients_v32.json               ├─→  build_indexes.py
                           (taxonomie + source_ids)           │         ↑
                                               ↓              │   ingredients_tree.json
                                   build_dict_v2.py           │
                                               ↓              ↓
                           ingredients_dictionary_v2.json   nutrition_index.json
                           ~1 975 entrées | 1 entrée = 1   ingredient_token_index.json
                           état produit | diet_profile 100% availability_graph.json
                                                           relation_graph.json
```

**Principes clés :**
- Chaque variant dans `ingredients_v32.json` porte un `source_id` officiel
- Le builder résout chaque ID directement — **zéro fuzzy matching**
- **1 entrée dictionnaire = 1 variant n2 = 1 état produit** (raw, cooked, dried…)
- `source` et `source_id` sont des champs racine de chaque entrée (lookup O(1))

---

## Prérequis

```powershell
python --version          # 3.10+ requis
pip install openpyxl
$env:PYTHONIOENCODING = "utf-8"
```

---

## Commandes — pipeline complet

### ÉTAPE 1 — Construire nutrition_v2.json

```powershell
# Dry-run (sans écriture)
python scripts\nutrition\build_n2_direct.py --dry-run

# Build + staging
python scripts\nutrition\build_n2_direct.py

# Build + promote → production
python scripts\nutrition\build_n2_direct.py --promote
```

**Indicateurs de succès :**
```
Lookup hits / misses  : 2161 / 0     ← 0 miss OBLIGATOIRE
Bases créées          : ~2 099
Total variants final  : ~1 921
```

**Sortie :** `backend\data\nutrition\processed\nutrition_v2.json`

---

### ÉTAPE 2 — Construire le dictionnaire ingrédients v2

Remplace `sync_nutrition_to_dict.py` (archivé). Pipeline unifié en un seul script.

```powershell
python scripts\nutrition\build_dict_v2.py
```

**3 phases internes :**
- **Phase 1** — Structure : 1 entrée par variant v32 (état produit), migration méta ancien dict
- **Phase 2** — Aliases : extraction depuis ancien dict (v32_ing_id, nutrition_key, normalisation)
- **Phase 3** — Enrichissement : `allergens_eu`, `nova_group`, `diet_profile`, `bioavailability_protein`

**Indicateurs de succès :**
```
Entrées dict           : ~1 975  (1 par variant n2)
Variants n2 non placés : 0       ← OBLIGATOIRE
diet_profile           : 1975/1975  (100%)
allergens_eu           : 1975/1975  (100%)
Alias index            : ~220
```

**Sortie :** `backend\data\ingredients\ingredients_dictionary_v2.json`

---

### ÉTAPE 3 — Reconstruire les indexes et graphs

À lancer après toute modification de `ingredients_tree.json` ou rebuild de `nutrition_v2.json`.

```powershell
python scripts\nutrition\build_indexes.py               # tous les fichiers
python scripts\nutrition\build_indexes.py --dry-run     # rapport sans écriture
python scripts\nutrition\build_indexes.py --target nutrition_index  # cible unique
```

**Produit 4 fichiers :**
- `backend\data\indexes\nutrition_index.json` — SOURCE:id → 40 valeurs nutritionnelles
- `backend\data\indexes\ingredient_token_index.json` — SOURCE:id → base/variant/IG context
- `backend\data\graphs\ingredient_availability_graph_v1.json` — complète les manquants
- `backend\data\graphs\ingredient_relation_graph.json` — complète les manquants

**Indicateurs de succès :**
```
Entrées totales      : ~2 109  (CIQUAL:~984 | CNF:~880 | USDA:~245)
Avec contexte IG     : 2109/2109  (100%)
```

---

### ÉTAPE 4 — Cohérence recettes [conditionnel]

À lancer uniquement si `recipes.json` ou `ingredients_dictionary_v2.json` a changé.

```powershell
python scripts\nutrition\fix_recipes_coherence.py          # audit
python scripts\nutrition\fix_recipes_coherence.py --apply  # correction
```

---

### ÉTAPE 5 — Reconstruire le search_index recettes [conditionnel]

À lancer après toute modification de `recipes.json` (ajout, correction, cohérence).
Distinct du pipeline nutrition — indexe les **recettes** (titres, ingrédients, tags, cuisine)
pour la recherche frontend.

```powershell
python scripts\build_index.py             # reconstruction complète
python scripts\build_index.py --dry-run   # stats sans écriture
```

**Sortie :** `backend\data\indexes\search_index.json`

**Indicateur de succès :**
```
X tokens uniques
Y références totales
Couverture : N/N recettes (100 %)
```

---

## Flux de données complet

```
Sources brutes (CIQUAL/USDA/CNF)
        ↓
  build_n2_direct.py
  (lookup par source_id — dérivations kcal, sugar_g, omega3)
        ↓
  nutrition_v2.json  (2 099 bases | 1 921 variants | 0 miss)
       ↙ ↘
  build_dict_v2.py          build_indexes.py
  (Phase 1 : structure)     (clé SOURCE:id)
  (Phase 2 : aliases)              ↓
  (Phase 3 : enrichissement)  nutrition_index.json
        ↓                     ingredient_token_index.json
  ingredients_dictionary_v2   availability_graph.json
  (~1 975 | 100% diet/allerg) relation_graph.json
        ↓ [si recettes modifiées]
  fix_recipes_coherence.py
        ↓
  recipes.json
```

---

## Tableau de bord — indicateurs

| Étape | Script | Indicateur clé | Valeur attendue |
|---|---|---|---|
| **1** | **build_n2_direct.py** | **Lookup misses** | **0** |
| 1 | build_n2_direct.py | Variants finaux | ~1 921 |
| 1 | build_n2_direct.py | Complets (EU) | ≥ 60% |
| **2** | **build_dict_v2.py** | **Variants non placés** | **0** |
| 2 | build_dict_v2.py | diet_profile | **100%** |
| 2 | build_dict_v2.py | allergens_eu | **100%** |
| 2 | build_dict_v2.py | Entrées totales | ~1 975 |
| **3** | **build_indexes.py** | **Avec contexte IG** | **100%** |
| 3 | build_indexes.py | Entrées totales | ~2 109 |
| 4 | fix_recipes_coherence.py | Critical | **0** |

---

## Structure d'une entrée dictionnaire v2

```json
"eggplant_aubergine_brinjal": {
  "v32_ing_id":        "ing_02220",
  "v32_var_id":        "var_02221",
  "source":            "CIQUAL",
  "source_id":         "20053",
  "source_label":      "aubergine",
  "canonical_name_fr": "aubergine",
  "canonical_name_en": "eggplant (aubergine, brinjal)",
  "axes":              {},
  "alt_sources": [{"source":"CNF","source_id":"2088","v32_var_id":"var_02222"}],
  "diet_profile": {"vegan":true,"gluten_free":true,"high_fiber":true,...},
  "allergens_eu":  [],
  "nova_group":    1,
  "bioavailability_protein": 0.55,
  "culinary": {"properties":["fresh","fiber"]}
}
```

---

## Fichiers de sortie

| Fichier | Générateur | Fréquence |
|---|---|---|
| `processed/nutrition_v2.json` | build_n2_direct.py | Après MAJ sources ou v32 |
| `processed/nutrition_v2_rebuilt.json` | build_n2_direct.py | Staging avant promote |
| `processed/nutrition_v2_backup_*.json` | build_n2_direct.py --promote | Backup auto |
| `ingredients/ingredients_dictionary_v2.json` | build_dict_v2.py | Après MAJ nutrition_v2 |
| `indexes/nutrition_index.json` | build_indexes.py | Après MAJ nutrition_v2 ou tree |
| `indexes/ingredient_token_index.json` | build_indexes.py | Après MAJ nutrition_v2 ou tree |
| `graphs/ingredient_availability_graph_v1.json` | build_indexes.py | Après MAJ nutrition_v2 |
| `graphs/ingredient_relation_graph.json` | build_indexes.py | Après MAJ nutrition_v2 ou tree |
| `data/recipes/recipes.json` | fix_recipes_coherence.py | Après MAJ recettes |
| `logs/raw_sources_manifest.json` | build_n2_direct.py --promote | SHA-256 des sources |

---

## Sources brutes

| Source | Fichier | Fréquence MAJ |
|---|---|---|
| CIQUAL | `raw/Table_Ciqual_2025_FR_*.xlsx` | Annuelle |
| USDA | `raw/FoodData_Central_foundation_food_json_*.json` | Annuelle |
| CNF | `raw/cnf/FOOD_NAME.csv` + `NUTRIENT_AMOUNT.csv` | Rare |
| Taxonomie | `ingredients/ingredients_v32.json` | Manuel (éditorial) |

**Procédure MAJ source :**
1. Remplacer le fichier raw
2. `build_n2_direct.py --dry-run` → vérifier `misses = 0`
3. Si misses > 0 → corriger `source_id` dans v32
4. `build_n2_direct.py --promote`
5. `build_dict_v2.py`
6. `build_indexes.py`
7. Si recettes impactées → `fix_recipes_coherence.py --apply`

---

## Complétude nutritionnelle (état v7.1)

| Niveau | Count | % |
|---|---|---|
| ✅ Complet (8 champs EU + enrichis) | 1 182 | 61.5% |
| 🟢 Standard | 27 | 1.4% |
| 🟡 Minimal (5-7 champs) | 593 | 30.9% |
| 🟠 Partiel (2-4 champs) | 61 | 3.2% |
| 🔴 Vide | 58 | 3.0% |

---

## Outils de diagnostic

| Script | Usage |
|---|---|
| `build_n2_direct.py --dry-run` | Vérifier 0 miss avant promote |
| `build_indexes.py --dry-run` | Rapport indexes sans écriture |
| `build_indexes.py --target nutrition_index` | Reconstruire un seul index |
| `_audit_n2_variants.py` | Audit structure variants n2 |
| `_audit_meta_coverage.py` | Couverture méta dans le dictionnaire |
| `fix_recipes_coherence.py` | Contrôles C1-C8 cohérence recettes |

---

## Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| `misses > 0` | source_id v32 absent des raws | Corriger source_id dans v32 |
| `Variants non placés > 0` | v32_var_id sans correspondant n2 | Vérifier cohérence v32/n2 |
| Rollback | Build incorrect promu | Copier `nutrition_v2_backup_*.json` → `nutrition_v2.json` |
| `ModuleNotFoundError: openpyxl` | Package absent | `pip install openpyxl` |
| Caractères cassés | Encodage cp1252 | `$env:PYTHONIOENCODING = "utf-8"` |

---

## Scripts archivés (remplacés)

| Script archivé | Remplacé par |
|---|---|
| `sync_nutrition_to_dict.py` | `build_dict_v2.py` |
| `dict_builder_v2.py` | `build_dict_v2.py` (unifié) |
| `extract_aliases_v2.py` | `build_dict_v2.py` (unifié) |
| `enrich_dict_v2.py` | `build_dict_v2.py` (unifié) |
| `build_ontology_v6.py` | `build_n2_direct.py` |
| `auto_correct_v6.py` | `build_n2_direct.py` |
| `build_ciqual_flat_v3.py` | Lecture directe dans `build_n2_direct.py` |
| `build_cnf_full_v10.py` | Lecture directe dans `build_n2_direct.py` |
| `promote_nutrition.py` | `build_n2_direct.py --promote` |
