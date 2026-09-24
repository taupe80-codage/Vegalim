# ALIM — Documentation technique globale

> Document vivant — à mettre à jour après chaque évolution majeure.
> Dernière mise à jour : avril 2026

---

## 1. Présentation du projet

**ALIM** est une plateforme française de recommandation culinaire végétarienne/végane.
Elle fournit des recettes scorées, filtrées et planifiées selon des profils nutritionnels
et diététiques précis.

**Principe fondateur** : chaque ingrédient est résolu jusqu'au **variant exact** dans
`nutrition_v2.json` avant tout calcul nutritionnel. Les proxies agrégés sont interdits.

**Stack** : FastAPI · Python · PostgreSQL · SQLAlchemy  
**Frontends** : React (B2C) + HTML vanilla (admin/B2B)  
**Recettes** : 980 recettes JSON, schéma CDC v4

---

## 2. Architecture des données

### 2.1 Séparation des responsabilités

```
ingredients_dictionary.json   →  identité culinaire
                                  (allergens_eu, diet_profile, substitutions,
                                   culinary_properties, flavor_profile,
                                   cooking_behavior, bioavailability_protein)
                                  nutrition_key = "base/variant"
                                         ↓
nutrition_v2.json              →  vérité nutritionnelle mesurée
  [base][variant]                  (macros, micros, lipides, vitamines,
                                    glycemic_index, health_score, nova_group,
                                    data_field_type, validation_score…)
```

**Règle stricte** : aucun champ nutritionnel (health_score, nova_group, fat_g…)
ne doit être stocké dans `ingredients_dictionary`. Ces valeurs sont variant-dépendantes
et doivent être lues en direct via `nutrition_key`.

### 2.2 Arborescence des fichiers de données

```
backend/data/
├── nutrition/
│   ├── processed/
│   │   ├── nutrition_v2.json              ← source de vérité nutritionnelle (v3.7+)
│   │   └── archive/
│   │       └── nutrition_v3.x.json        ← archives versionnées
│   ├── reference/
│   │   ├── nutrition_corrected.json       ← sortie auto_correct, input validator
│   │   ├── ontology_v6.json              ← base de correspondances nutritionnelles
│   │   └── nutrition_index.json          ← index lookup alias→données (généré)
│   ├── raw/
│   │   ├── ciqual_flat.json              ← CIQUAL 2025 (~2800 aliments)
│   │   ├── usda_flat.json                ← USDA FoodData Central (~2500)
│   │   └── cnf_full_v5.json              ← CNF Canada (3444)
│   ├── sources/                          ← versions light pour dev
│   └── logs/
│       └── corrections_log.json
├── ingredients/
│   ├── ingredients_dictionary.json        ← identité culinaire (v4+)
│   ├── ingredient_token_index.json        ← tokens alias→bases (v4.1+)
│   ├── ingredient_physical.json           ← données physiques unités→grammes
│   └── fr_to_en_mapping.json             ← mapping FR→base_name (v2.1+)
├── recipes/
│   └── recipes.json                      ← 980 recettes CDC v4
└── outputs/                              ← rapports validator
    ├── validation_report.json
    └── correction_proposals.json
```

---

## 3. Structure de nutrition_v2.json

### 3.1 Schéma hiérarchique (v3.7)

```json
{
  "schema_version": "3.7",
  "ingredients": {
    "<base_name>": {
      "_meta": { "category", "name_fr", "scientific_name", "is_standalone" },
      "variants": {
        "<variant_name>": {
          // Identité
          "name_fr", "name_en", "scientific_name", "aliases",
          "ingredient_type",        // raw | processed | refined | cooked…

          // Macros
          "calories_kcal", "protein_g", "carbs_g", "fat_g",
          "fiber_g", "sugar_g", "starch_g", "added_sugar", "alcohol_g",

          // Lipides détaillés
          "saturated_fat_g", "monounsaturated_fat_g", "polyunsaturated_fat_g",
          "omega3_g", "omega6_g", "omega3_ala_g",

          // Micronutriments
          "cholesterol_mg", "sodium_mg", "calcium_mg", "iron_mg",
          "magnesium_mg", "phosphorus_mg", "potassium_mg", "zinc_mg",
          "copper_mg", "manganese_mg", "selenium_ug",
          "vitamin_a_ug", "vitamin_b1_mg", "vitamin_b2_mg", "vitamin_b3_mg",
          "vitamin_b5_mg", "vitamin_b6_mg", "vitamin_b12_ug",
          "vitamin_c_mg", "vitamin_d_ug", "vitamin_e_mg", "vitamin_k1_ug",
          "folate_ug", "beta_carotene_ug",

          // Scores et classification
          "glycemic_index", "glycemic_index_source", "glycemic_load",
          "nova_group",               // NOVA 1-4
          "health_score",             // 0-100, calculé
          "bioavailability_protein",  // 0-1, par catégorie

          // Qualité de la donnée
          "data_field_type",   // raw | fa_incomplete | source_conflict
          "validation_score",  // 0-1, cohérence structurelle
          "errors_detected", "warnings_detected",
          "confidence", "sources", "data_quality"
        }
      }
    }
  }
}
```

### 3.2 Champ data_field_type — hiérarchie de confiance lipidique

| Valeur | Condition | Interprétation |
|--------|-----------|----------------|
| `raw` | `ratio ≥ 0.70` ou sub=0 | Données cohérentes — utiliser directement |
| `fa_incomplete` | `0.15 ≤ ratio < 0.70` | PUFA partiellement renseigné — fat_g fiable, FA partielles |
| `source_conflict` | `ratio < 0.15` | fat_g potentiellement contaminé par mauvais match USDA |

`ratio = (sat + mono + poly) / fat_g`

Les 29 `source_conflict` actuels nécessitent un reload manuel CIQUAL/USDA avec le bon
`alim_code`. Listés dans `nutrition_index.json → source_conflicts`.

---

## 4. Pipeline nutrition

### 4.1 Ordre d'exécution complet

```bash
# 1. Construire l'ontologie de référence (si sources raw modifiées)
python scripts/nutrition/build_ontology_v6.py

# 2. Corriger et enrichir nutrition_v2 → nutrition_corrected
python scripts/nutrition/auto_correct_v6.py

# 3. Valider la cohérence interne
python scripts/nutrition/validator_v11.py --audit

# 4. Validation croisée CIQUAL/USDA (optionnel, nécessite sources complètes)
python scripts/nutrition/validator_v11.py

# 5. Promouvoir nutrition_corrected → nutrition_v2 (bump version)
python scripts/nutrition/promote_nutrition.py --confirm

# 6. Synchroniser ingredients_dictionary depuis nutrition_v2
python scripts/nutrition/sync_nutrition_to_dict.py
```

### 4.2 Flux de données

```
raw/ciqual_flat.json ──┐
raw/usda_flat.json   ──┤→ build_ontology_v6.py → ontology_v6.json
raw/cnf_full_v5.json ──┘

nutrition_v2.json + ontology_v6.json
    → auto_correct_v6.py
        → nutrition_corrected.json  +  corrections_log.json

nutrition_corrected.json
    → validator_v11.py --audit       → rapport console (0 critical = OK)
    → validator_v11.py               → validation_report.json
                                       correction_proposals.json

nutrition_corrected.json
    → promote_nutrition.py --confirm → nutrition_v2.json (vX.Y)
                                       archive/nutrition_vX.(Y-1).json

nutrition_v2.json
    → sync_nutrition_to_dict.py     → ingredients_dictionary.json (sync)
```

### 4.3 Règles biologiques appliquées par auto_correct_v6

| Règle | Condition | Action |
|-------|-----------|--------|
| 4a. Lait animal | `category ∈ {milk_animal, cream_animal}` | `fiber_g = starch_g = 0` |
| 4b. Végétaux | `category ∈ BIO_PLANT_CATEGORIES` | `cholesterol_mg = 0` |
| 4c. Noix/graines | `category = fat` et sodium > 50mg | `sodium_mg = 1.0` |
| 4d. Fat sanity | `fat_new > 5 × sub_total_existant` | Rejet du match USDA (`source_conflict`) |
| 4e. Omega cap | `omega3 + omega6 > poly` | Cap biologique, rescale proportionnel |

### 4.4 Règles du validator_v11 (V13)

| Type | Sévérité | Condition |
|------|----------|-----------|
| `energy_mismatch` | warning/critical | `|kcal_déclaré - Atwater| > seuil` |
| `fiber_gt_carbs` | critical | `fiber > carbs + 0.5` |
| `sugar_gt_carbs` | warning | `sugar > carbs + 0.5` |
| `saturated_fat_gt_fat` | critical | `sat > fat + 0.5` |
| `macro_sum_impossible` | critical | `protein + carbs + fat > 105` |
| `lipid_sub_incoherence` | warning/critical | ratio sub/fat hors seuil (V13) |
| `omega_gt_poly` | critical | `omega3 + omega6 > poly` (V13) |
| `data_truth_score` | info | Score 0-1 de vérité scientifique (V13) |

---

## 5. Structure de ingredients_dictionary.json

### 5.1 Schéma d'une entrée (v4+)

```json
{
  "id": "almond",
  "name_fr": "amande",
  "category": "nut_seed",
  "nutrition_key": "almond/default",
  "allergens_eu": [],
  "bioavailability_protein": 0.7,
  "diet_profile": {
    "vegan": true, "vegetarian": true, "sans_gluten": true,
    "sans_lactose": true, "sans_fruits_a_coque": false,
    "hyper_proteine": true, "diabet_free": true,
    "sans_soja": true, "sans_oeuf": true, "riche_en_fibres": false
  },
  "substitutions": ["pine_nut", "walnut", "sesame"],
  "culinary_properties": ["fat", "protein"],
  "flavor_profile": ["nutty", "sweet", "bitter"],
  "cooking_behavior": { "roasted": "croquant", "time_minutes": 8 }
}
```

### 5.2 Résolution nutrition_key

```python
base, variant = entry["nutrition_key"].split("/")
variant_data  = nutrition_v2["ingredients"][base]["variants"][variant]
# → accès direct aux 60+ champs nutritionnels du variant exact
```

Pour les bases ombrelles sans variant précisable (flour, oil, rice…),
`nutrition_key` reste `"base"`. Le moteur de recette choisit le variant
selon le contexte de la recette.

---

## 6. Index de lookup

### 6.1 ingredient_token_index.json (v4.1)

```
token (str normalisé) → [base_name, ...]
```

- 2 959 tokens couvrant 292 bases
- Formes indexées : originale, déaccentuée, underscore↔espace
- Usage : résolution rapide d'un texte recette → base(s) nutrition

### 6.2 nutrition_index.json (v1.0)

```
lookup : alias_normalisé → { base, variant, macros, data_field_type, validation_score }
bases  : base_name → { category, variants, default_variant }
source_conflicts : [ { base, variant, fat_g, sub_total, validation_score } ]
```

- 2 912 clés de lookup
- Utilisé par le scoring engine pour accès O(1) sans traverser nutrition_v2
- `source_conflicts` = liste prête à consommer pour batch reload CIQUAL/USDA

---

## 7. Fichiers de scripts — état actuel

| Script | Version | Rôle | Statut |
|--------|---------|------|--------|
| `build_ontology_v6.py` | v6 | Construit ontology_v6.json depuis raw sources | ✅ |
| `auto_correct_v6.py` | v6.3 | Corrige nutrition_v2 + règles biologiques | ✅ v3.7 |
| `validator_v11.py` | V13 | Audit cohérence + data_truth_score | ✅ v3.7 |
| `promote_nutrition.py` | — | Promeut corrected → v2, archive | ✅ |
| `sync_nutrition_to_dict.py` | v1 | Sync dict depuis nutrition_v2 | ✅ **NOUVEAU** |
| `patch_nutrition.py` | — | Patches ponctuels (alcohol, starch, scientific_name) | ✅ |
| `build_nutrition_aliases.py` | — | Construit les alias de lookup | ✅ |
| `_diagnose_v2.py` | v2 | Diagnostic rapide console | ✅ |

---

## 8. Versions actuelles des fichiers de données

| Fichier | Version | Bases/Entrées | Dernière évolution |
|---------|---------|---------------|-------------------|
| `nutrition_v2.json` | **3.7** | 292 bases, 422 variants | Suppression scaling lipidique, data_field_type, KNOWN_LIPID_PROFILES |
| `ingredients_dictionary.json` | **diet_v4** | 310 entrées | Séparation identité/nutrition, nk→base/variant |
| `ingredient_token_index.json` | **4.1** | 2 959 tokens | Rebuild depuis nutrition_v2 v3.7 |
| `nutrition_index.json` | **1.0** | 2 912 lookup keys | Création, lookup O(1) |
| `fr_to_en_mapping.json` | **2.1** | 1 284 mappings | +182 bases nutrition, 55 orphelins corrigés |
| `ingredient_physical.json` | **1.0** | 580 entrées | Indépendant de nutrition, pas de sync |

---

## 9. Décisions d'architecture — journal

### Séparation identité / nutrition (v4, avril 2026)

**Contexte** : `health_score`, `nova_group`, `data_field_type` présents dans
`ingredients_dictionary` → fausse précision (valeur d'un variant arbitraire).

**Décision** : ces champs sont variant-dépendants et ne doivent vivre que dans
`nutrition_v2`. Le dict porte uniquement l'identité culinaire stable.

**Champs migrés vers le dict** : `bioavailability_protein` (stable entre variants,
propriété de la catégorie). `allergens_eu` reste dans le dict (réglementaire EU,
stable par ingrédient).

### Data truth vs data repair (v3.7, avril 2026)

**Contexte** : le patch v3.6 scalait `sat/mono/poly` pour les faire coïncider avec
`fat_g`. Problème fondamental : si les sub-composants étaient corrects et `fat_g`
contaminé par un mauvais match USDA, le scaling amplifiait l'erreur (×8 à ×350).

**Décision** : interdiction du scaling. À la place :
- `FAT_SANITY_MAX_RATIO = 5` dans `auto_correct` : rejette tout match USDA
  proposant `fat_g > 5 × sub_total_existant`
- `KNOWN_LIPID_PROFILES` : table de valeurs mesurées à priorité absolue
- `data_field_type` : flag la qualité plutôt que corriger

**Principe** : `data incohérente → remplacée par source fiable`
(pas `data incohérente → corrigée mathématiquement`)

---

## 10. Problèmes connus et actions requises

### Priorité haute

| Problème | Volume | Action |
|----------|--------|--------|
| `source_conflict` : fat_g contaminé | 29 variants | Reload manuel CIQUAL avec alim_code correct |
| `fa_incomplete` : PUFA partiels | 54 variants | Enrichissement optionnel USDA |
| 13 ingrédients sans nutrition_key | 13 entries dict | Ajouter dans nutrition_v2 ou MANUAL_NK_OVERRIDES |

### Priorité normale

| Problème | Volume | Action |
|----------|--------|--------|
| 144 self-maps morts dans fr_to_en | 144 | Ingrédients absents de nutrition_v2 (camembert, creme_fraiche…) |
| Calories non entières (ex: 24.58) | ~30 | Arrondi ou correction source (résidu de moyennes pondérées) |
| `ingredient_physical` sans couverture nutrition | 100 bases | Données physiques à ajouter |

### Non-bloquant

| Problème | Note |
|----------|------|
| `omega3_ala/epa/dha_g` parfois nuls | Fractions non disponibles dans toutes les sources |
| `scientific_name` absent sur ~40% des bases | CIQUAL coverage, enrichissable |

---

## 11. Extensibilité

### Ajouter un ingrédient à nutrition_v2

1. Ajouter l'entrée dans `nutrition_v2.json` sous `ingredients`
2. Relancer `auto_correct_v6.py` (enrichissement depuis ontologie)
3. `validator_v11.py --audit` (vérification 0 critical)
4. `promote_nutrition.py --confirm`
5. `sync_nutrition_to_dict.py` (sync dict automatique)

### Ajouter un profil lipidique mesuré

Dans `auto_correct_v6.py`, section `KNOWN_LIPID_PROFILES` :

```python
KNOWN_LIPID_PROFILES: dict[tuple, tuple] = {
    ("base_name", "variant_name"): (sat_g, mono_g, poly_g, omega3_g, omega6_g, "source_ref"),
    # ex: ("cashew", "default"): (7.78, 23.80, 7.84, 0.14, 7.69, "USDA FDC #1100509"),
}
```

### Ajouter un override dict ambigu

Dans `sync_nutrition_to_dict.py`, section `MANUAL_NK_OVERRIDES` :

```python
MANUAL_NK_OVERRIDES: dict[str, str] = {
    "dict_id": "base_name/variant_name",
}
```
