# PIPELINE NUTRITION — ALIM v6
> Mise à jour : 2026-05-01
> État : ✅ Stable (Critical: 0, Warning: 8, data_truth_score: 0.9999)

---

## État courant du pipeline

| Métrique | Valeur | Tendance |
|---|---|---|
| Criticals validator | **0** | ✅ Stable depuis v6.17 |
| Warnings validator | **8** | Exceptions biologiques non corrigeables |
| data_truth_score | **0.9999 avg** | Maximum atteint |
| Ingrédients nutrition_v2 | **283** | −6 migrés vers recipes.json (2026-05-01) |
| Bases ontologie | **1 358** | +3 depuis ajout overrides |
| Variants ontologie | **1 781** | |
| Aliases ALIM | **52 résolus / 19 manquants** | |
| nutrition_v2 version | **6.18** | |

---

## Prérequis

```powershell
# Python 3.10+ requis (union types X | Y)
python --version

# Dépendances
pip install openpyxl rapidfuzz

# Configuration console (Windows)
cd C:\...\project_final_v6_migrated
$env:PYTHONIOENCODING = "utf-8"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

---

## Commandes — ordre d'exécution

### ÉTAPE 0 — Builders sources [uniquement si nouvelles sources]

```powershell
# 0-a. CIQUAL (nouveau XLSX Anses)
python scripts\nutrition\build_ciqual_flat_v3.py `
  --input  "backend\data\nutrition\raw\Table_Ciqual_2025_FR_*.xlsx" `
  --output backend\data\nutrition\outputs\ciqual_flat_v3.json

# 0-b. USDA (nouveau JSON USDA FoodData Central)
python scripts\nutrition\usda_refactor_v2.py `
  --input  "backend\data\nutrition\raw\FoodData_Central_*.json" `
  --output backend\data\nutrition\outputs\usda_flat_v2.json

# 0-c. CNF (CSV modifié)
python scripts\nutrition\build_cnf_full_v10.py `
  --output backend\data\nutrition\outputs\cnf_full_v10.json
```

| Builder | Indicateur | Valeur attendue |
|---|---|---|
| build_ciqual_flat_v3 | foods_flat net | ~1 650 aliments |
| usda_refactor_v2 | aliments conservés | ~263 aliments |
| build_cnf_full_v10 | aliments | ~1 833 aliments |

---

### ÉTAPE 0-diag — Diagnostic initial [optionnel]

```powershell
python scripts\nutrition\_diagnose_v2.py --section pipeline
python scripts\nutrition\_diagnose_v2.py --section onto
```

---

### ÉTAPE 1 — Construire l'ontologie v6

```powershell
python scripts\nutrition\build_ontology_v6.py
```

**Indicateurs de succès :**
```
Total bases : 1358 | Variants : 1781 | Alias : 52 | Taxonomy : 374/1358
```

**Avertissements normaux :**
- `⚠ nutrition_v2 absent → filtre base_recipe désactivé` — normal au premier run
- `⚠ CIQUAL schema 7.0 détecté` — non bloquant

**Sorties :**
```
backend\data\nutrition\reference\ontology_v6.json
backend\data\nutrition\reference\ontology_v6_report.json
backend\data\nutrition\reference\reference_db.json
```

---

### ÉTAPE 2 — Correction + enrichissement

```powershell
python scripts\nutrition\auto_correct_v6.py
```

**Indicateurs de succès :**
```
Corrections sources : 26
Enrichissements     : 6
```

**Sortie :**
```
backend\data\nutrition\reference\nutrition_corrected.json
backend\data\logs\corrections_log.json
```

---

### ÉTAPE 3 — Validation + application proposals

```powershell
# Validation croisée → génère correction_proposals.json
python scripts\nutrition\validator_v11.py

# (manuel) Réviser correction_proposals.json :
# passer "action": "replace" → "keep" pour refuser une correction

# Application sélective (score >= 0.90, severity >= warning)
python scripts\nutrition\validator_v11.py --apply --severity=warning --score=0.90
```

**Sorties :**
```
backend\data\nutrition\outputs\validation_report.json
backend\data\nutrition\outputs\correction_proposals.json
```

---

### ÉTAPE 4 — Patch criticals

```powershell
python scripts\nutrition\patch_nutrition_v8.py
```

**Indicateurs de succès :**
```
urgent_fixes_applied    : 60
proposals_applied       : 39
proposals_rejected      : 2715
residual_fiber_critical : 0
```

**Sortie :**
```
backend\data\nutrition\reference\nutrition_patched_v8.json
backend\data\nutrition\outputs\patch_report_v8.json
```

---

### ÉTAPE 4b — Validation post-patch [GATE DE QUALITÉ ⛔]

```powershell
python scripts\nutrition\validator_v11.py --audit `
  --input backend\data\nutrition\reference\nutrition_patched_v8.json
```

**Requis : `Critical: 0` avant de continuer.**
Si des criticals apparaissent → corriger `patch_nutrition_v8.py` et relancer depuis l'étape 2.

---

### ÉTAPE 5 — Diagnostic final [optionnel]

```powershell
python scripts\nutrition\_diagnose_v2.py --section log
python scripts\nutrition\_diagnose_v2.py --section coverage
python scripts\nutrition\_diagnose_v2.py --section patch
```

---

### ÉTAPE 6 — Promouvoir vers nutrition_v2

```powershell
# Dry-run (aperçu sans écriture)
python scripts\nutrition\promote_nutrition.py

# Exécution
python scripts\nutrition\promote_nutrition.py --confirm

# Exécution + suppression de nutrition_patched_v8.json
python scripts\nutrition\promote_nutrition.py --confirm --clean
```

**Séquence interne de `promote_nutrition.py --confirm` :**

| Step | Action |
|---|---|
| 1 | Archive `nutrition_v2.json` → `processed\archive\nutrition_v6.N.json` |
| 2 | Copie source + update `_meta` (schema_version, promoted_date) |
| 3 | (optionnel) Supprime la source si `--clean` |
| 4 | Injecte items CIQUAL `mapped=ABSENT` |
| 5 | Applique règles allergènes EU 1169/2011 |
| 6 | Applique classification NOVA (Monteiro 2019) |
| 7 | Purge `BASE_RECIPE_MODES = "base_recipe"` |
| 8 | Fusionne doublons sémantiques (`snow_peas→snow_pea`, `capers→caper`) ← **2026-05-01** |
| 9 | Recalcule compteurs top-level (`total_bases`, `total_variants`, `standalone_bases`) ← **2026-05-01** |

**`BASE_RECIPE_MODES` — état actuel :**

| Ingrédient | Mode | Effet |
|---|---|---|
| `harissa`, `pesto`, `gochujang`, `chili_paste`, `empanada_dough`, `natto`, `tamarind_paste`, `falafel` | `"base_recipe"` | **Supprimé** — valeur calculée depuis la recette |
| `kombucha`, `buckwheat_crepe`, `crackers`, `fried_rice`, `gnocchi`, `fried_onion` | `"base_recipe"` | **Supprimé** — migré vers `recipes.json` (2026-05-01) |
| `seitan`, `tahini` | `"indus"` | **Conservé** — données CIQUAL/USDA validées |

**`SEMANTIC_DUPLICATES` — état actuel :**

| Alias supprimé | Canonique conservé | Note |
|---|---|---|
| `snow_peas` | `snow_pea` | Données identiques |
| `capers` | `caper` | Micro-écart protein 2.36→2.4 — singulier fait foi |

**Indicateurs de succès :**
```
✅ Promo    → nutrition_v2.json  (v6.18, 283 ingrédients)
Entrees supprimees (base_recipe) : [...]
Doublons fusionnés (2) : snow_peas → snow_pea | capers → caper
Compteurs recalculés :
  total_bases:      292 → 283  ← corrigé
  total_variants:   422 → 463  ← corrigé
  standalone_bases: 240 → 248  ← corrigé
```

**Sortie :**
```
backend\data\nutrition\processed\nutrition_v2.json
```

---

### ÉTAPE 7 — Scripts post-promote

Ces scripts opèrent sur `nutrition_v2.json` après promotion. Ordre strict.

```powershell
# 7a. Corrections ciblées (water, oil variants, pepper starch, quinoa, butter almond)
python scripts\nutrition\patch_nutrition_critical.py

# 7b. Cohérence macro (carbs_basis flags + starch overflow)
python scripts\nutrition\patch_macro_coherence.py

# 7c. Génération aliases nutrition
python scripts\nutrition\build_nutrition_aliases.py

# 7d. Synchro dictionnaire ingrédients
python scripts\nutrition\sync_nutrition_to_dict.py
```

**Sorties :**
```
backend\data\nutrition\reference\nutrition_aliases_v6.json
backend\data\ingredients\ingredients_dictionary.json
backend\data\logs\critical_patches_log.json
```

---

### ÉTAPE 8 — Cohérence recettes

```powershell
# Dry-run (audit uniquement)
python scripts\nutrition\fix_recipes_coherence.py

# Application
python scripts\nutrition\fix_recipes_coherence.py --apply
```

**Contrôles C1-C8 :**
- C1 `lactose_free` — flag vs présence lait/crème/fromage
- C2 `vegan` — flag vs présence œufs/produits laitiers
- C3 `vegetarian` — flag vs présence viande/poisson
- C4 Timing — `prep_time + cook_time != total_time`
- C5 Description manquante ou vide
- C6 `servings` non calibrés par `dish_type`
- C7 `difficulty` manquant
- C8 Ingrédients sans équivalent dans `nutrition_v2`

**Sorties :**
```
backend\data\recipes\recipes.json
backend\data\logs\coherence_corrections_log.json
```

---

## Pipeline complet automatique — reset_pipeline.bat [v2.1]

```powershell
cd C:\...\project_final_v6_migrated
scripts\nutrition\reset_pipeline.bat
```

Exécute les étapes 1→8 dans l'ordre avec vérification d'erreur entre chaque étape.
**Inclut la gate de qualité `--audit` étape 4b** — s'arrête si `Critical > 0` avant promotion.

---

## Flux de données complet

```
Sources brutes
  CIQUAL 2025 XLSX  → build_ciqual_flat_v3.py  → outputs\ciqual_flat_v3.json
  USDA FDC JSON     → usda_refactor_v2.py       → outputs\usda_flat_v2.json
  CNF CSV           → build_cnf_full_v10.py      → outputs\cnf_full_v10.json
                                  ↓
                    build_ontology_v6.py
                    (weighted avg CIQUAL=0.95 / USDA=0.85 / CNF=0.75)
                    (+ CIQUAL_KEY_OVERRIDES + CNF_KEY_OVERRIDES)
                                  ↓
                    reference\ontology_v6.json  (1 358 bases, 1 781 variants)
                                  ↓
                    auto_correct_v6.py
                                  ↓
                    reference\nutrition_corrected.json  (299 ingrédients)
                                  ↓
                    validator_v11.py --apply
                                  ↓
                    patch_nutrition_v8.py
                                  ↓
                    reference\nutrition_patched_v8.json
                                  ↓
                    validator_v11.py --audit  ← GATE: Critical = 0
                                  ↓
                    promote_nutrition.py --confirm
                    ├── purge BASE_RECIPE_MODES
                    ├── fusion SEMANTIC_DUPLICATES          ← 2026-05-01
                    └── recalcul compteurs top-level        ← 2026-05-01
                                  ↓
                    processed\nutrition_v2.json  (v6.18, 283 ingrédients)
                                  ↓
              ┌───────────────────┼───────────────────┐
              ↓                   ↓                   ↓
  patch_nutrition_critical   patch_macro_coherence  build_nutrition_aliases
  (C1-C7 post-promote)       (carbs_basis flags)    → nutrition_aliases_v6.json
              ↓
  sync_nutrition_to_dict
  → ingredients_dictionary.json
              ↓
  fix_recipes_coherence --apply
  → recipes.json
```

---

## Tableau de bord — indicateurs de succès

| Étape | Script | Indicateur clé | Valeur actuelle |
|---|---|---|---|
| 0-a | build_ciqual_flat_v3.py | foods_flat net | ~1 650 aliments |
| 0-b | usda_refactor_v2.py | aliments conservés | 263 aliments |
| 0-c | build_cnf_full_v10.py | aliments | ~1 833 aliments |
| 1 | build_ontology_v6.py | Total bases / Variants | 1 358 / 1 781 |
| 2 | auto_correct_v6.py | Corrections / Enrichissements | 26 / 6 |
| 3 | validator_v11.py | Critical avant apply | < 15 |
| 4 | patch_nutrition_v8.py | urgent_fixes_applied | 60 |
| **4b** | **validator_v11.py --audit** | **Critical = 0** | **✅ 0** |
| 6 | promote_nutrition.py | Ingrédients / Doublons fusionnés | 283 / 2 |
| 7a | patch_nutrition_critical.py | C1-C7 appliqués | 7 corrections |
| 7b | patch_macro_coherence.py | Flags carbs_basis | ~36 ingrédients |
| 7c | build_nutrition_aliases.py | aliases générés | — |
| 7d | sync_nutrition_to_dict.py | nutrition_key rebuildée | idempotent |
| 8 | fix_recipes_coherence.py | critical = 0 | idempotent |

---

## Sources des fichiers

| Fichier | Script générateur | Fréquence MAJ |
|---|---|---|
| `outputs/ciqual_flat_v3.json` | build_ciqual_flat_v3.py | Annuelle (Anses) |
| `outputs/usda_flat_v2.json` | usda_refactor_v2.py | Annuelle (USDA) |
| `outputs/cnf_full_v10.json` | build_cnf_full_v10.py | Rare |
| `reference/ontology_v6.json` | build_ontology_v6.py | Après MAJ sources |
| `reference/nutrition_corrected.json` | auto_correct_v6.py | Après MAJ ontologie |
| `reference/nutrition_patched_v8.json` | patch_nutrition_v8.py | Après validation |
| `processed/nutrition_v2.json` | promote_nutrition.py | Après patch validé |
| `reference/nutrition_aliases_v6.json` | build_nutrition_aliases.py | Après MAJ nutrition_v2 |
| `ingredients/ingredients_dictionary.json` | sync_nutrition_to_dict.py | Après MAJ nutrition_v2 |
| `ingredients/fr_to_en_mapping.json` | Manuel | Lors d'ajout d'ingrédients |
| `logs/corrections_log.json` | auto_correct_v6.py | Après chaque run |
| `logs/critical_patches_log.json` | patch_nutrition_critical.py | Après chaque run |
| `logs/coherence_corrections_log.json` | fix_recipes_coherence.py | Après MAJ recettes |
| `data/recipes/recipes.json` | fix_recipes_coherence.py | Après MAJ recettes |

---

## Versions des scripts

| Script | Version | Dernière MAJ | Notes |
|---|---|---|---|
| `food_schema_v2.py` | v2.1 | Avr 2026 | Module commun — source unique de vérité |
| `build_ciqual_flat_v3.py` | v5.1 | Avr 2026 | Schema state v2 + nutrients imbriqués, output schema 7.0 |
| `usda_refactor_v2.py` | v5.0 | Avr 2026 | ⚠ flatten nutrients manquant (CRIT-2) |
| `build_cnf_full_v10.py` | v10.0 | Avr 2026 | ⚠ multi_variant_groups=0 (WARN-1) |
| `build_ontology_v6.py` | v6.2 | Mai 2026 | +CIQUAL_KEY_OVERRIDES +CNF_KEY_OVERRIDES |
| `auto_correct_v6.py` | v6.0 | Avr 2026 | |
| `validator_v11.py` | v14 | Mai 2026 | nutrients_v6, data_truth_score, carbs_schema |
| `patch_nutrition_v8.py` | v8.2 | Mai 2026 | 60 urgent fixes, BLOCKED_PROPOSALS 14 ingrédients |
| `promote_nutrition.py` | v2.1 | **Mai 2026** | +SEMANTIC_DUPLICATES +_recompute_meta_counters +6 base_recipe |
| `patch_nutrition_critical.py` | v1.0 | Avr 2026 | 7 corrections C1-C7 post-promote |
| `patch_macro_coherence.py` | v1.0 | Avr 2026 | carbs_basis flags + starch overflow |
| `build_nutrition_aliases.py` | — | Avr 2026 | |
| `fix_recipes_coherence.py` | v1.0 | Avr 2026 | 8 contrôles, --apply/--quiet, idempotent |
| `sync_nutrition_to_dict.py` | v1.0 | Avr 2026 | idempotent |
| `_diagnose_v2.py` | v2.2 | Mai 2026 | 7 sections |
| `_cnf_groups.py` | util | Avr 2026 | inventaire groupes CNF |
| `taxonomy_loader.py` | — | Avr 2026 | |
| `reset_pipeline.bat` | v2.1 | Mai 2026 | +gate 4b validator --audit |
| `fr_to_en_mapping.json` | v3.2 | Mai 2026 | 1 171 entrées |

---

## Issues connues (non bloquantes)

### ⚠ CRIT-1 — CIQUAL schema 7.0 (résolu partiellement)
`ciqual_flat_v3.json` exporte `schema_version: 7.0`. `build_ontology_v6.py` détecte et log le warning mais ne traite pas nativement les champs spécifiques v7 (`ingredient_key`, `family_key`, `generic_type`). Ces champs sont ignorés silencieusement.
**Impact actuel :** Nul sur les données nutritionnelles.

### ⚠ CRIT-2 — USDA micronutriments partiels
`usda_refactor_v2.py` stocke les micronutriments dans un bloc imbriqué `nutrients{}` mais `build_ontology_v6.py` lit des champs plats au niveau racine. Couverture réelle : selenium 39%, iodine 12%, vitamines B 8-14%.
**Impact actuel :** Vitamines et minéraux USDA sous-représentés dans l'ontologie.

### ⚠ WARN-1 — CNF multi_variant_groups = 0
`build_cnf_full_v10.py` détecte 0 groupes multi-variants (attendu ~384). Les variants CNF (cru/cuit/séché) ne sont pas correctement regroupés.
**Impact actuel :** Variants CNF arrivent comme entrées séparées plutôt que comme sous-variantes d'un même ingrédient.

### ℹ INFO — 19 aliases ALIM sans cible dans l'onto
`dried_fig`, `black_beans`, `pea_protein`, `halloumi`, `nutritional_yeast`, `sriracha`, `pumpkin_seeds`, `cream_plant` — ingrédients avec entrée dans le mapping mais sans clé correspondante dans l'ontologie (P3 — données absentes des raws CIQUAL/USDA/CNF).

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Source CIQUAL introuvable` | `ciqual_flat_v3.json` absent dans `outputs\` | Lancer `build_ciqual_flat_v3.py` |
| `⚠ nutrition_v2 absent → filtre base_recipe désactivé` | Premier run du pipeline | Normal — continuer, le filtre s'active au 2ème run |
| `Critical > 0` après `--audit` | Nouvelle corruption détectée | Identifier dans `patch_report_v8.json`, ajouter dans `URGENT_FIXES` |
| `proposals_applied` remonte | Nouvelle proposal écrase un urgent fix | Ajouter l'ingrédient dans `BLOCKED_PROPOSALS` |
| `SKIP (variant not found): xxx[yyy]` dans patch_v8 | Variant nommé différemment dans nutrition_corrected | Utiliser détection dynamique (section [3b]) ou vérifier `auto_correct` |
| Ingrédient absent de l'onto mais dans nc | Clé nc absente de `fr_to_en_mapping.json` | Ajouter dans mapping ou `CIQUAL_KEY_OVERRIDES` |
| `Alias manquants: xxx → xxx (cible absente)` | Clé cible absente de l'onto (P3) | Ajouter données dans un raw ou créer manuellement dans nutrition_v2 |
| `ModuleNotFoundError: food_schema_v2` | `sys.path` incomplet | Lancer depuis la RACINE du projet |
| `ModuleNotFoundError: openpyxl` | Package absent | `pip install openpyxl` |
| `ModuleNotFoundError: rapidfuzz` | Package absent | `pip install rapidfuzz` |
| Caractères cassés dans la console | Console cp1252 | `$env:PYTHONIOENCODING = "utf-8"` |
| `TypeError: X \| Y (union type)` | Python < 3.10 | Mettre à jour Python vers 3.10+ |
| `Entrees supprimees (STATIC)` contient seitan ou tahini | Ancienne version de `promote_nutrition.py` | Mettre à jour — ces deux ingrédients doivent être en mode `"indus"` |
| `Doublons sémantiques` non fusionnés | Ancienne version de `promote_nutrition.py` | Mettre à jour vers v2.1 — ajoute `_merge_semantic_duplicates` |
| Compteurs `total_bases` / `total_variants` incohérents | Ancienne version de `promote_nutrition.py` | Mettre à jour vers v2.1 — ajoute `_recompute_meta_counters` |
