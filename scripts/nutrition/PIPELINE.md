# PIPELINE NUTRITION — ALIM v6

> Traçabilité des scripts, fichiers, et état d'avancement

---

## Résumé des changements v6

| Composant | v5 | v6 |
|-----------|----|----|
| Champs ontologie | 15 | **42** |
| Sources connectées | light uniquement | **full + light fallback** |
| `scientific_name` | ✗ | **✓ depuis CIQUAL** |
| `starch_g` | 31% rempli | **~80% attendu** |
| `alcohol_g` | 1% rempli | **~99% attendu** |
| `nova_group` | ✗ | **✓ calculé** |
| `health_score` | ✗ | **✓ calculé** |
| `bioavailability_protein` | ✗ | **✓ table statique** |
| `glycemic_load` | 39% | **~85% attendu** |
| `glycemic_index_source` | 0% | **✓ inféré** |
| `omega3` fractions (ALA/EPA/DHA) | ✗ | **✓ CIQUAL + USDA** |
| `iodine_ug` | ✗ | **✓ CIQUAL** |
| `choline_mg` | ✗ | **✓ USDA** |

---

## Vue d'ensemble

```
RAW SOURCES (complètes)            SCRIPTS                          OUTPUTS
─────────────────────────────────────────────────────────────────────────────
sources/ciqual_flat.json      ──┐
sources/usda_flat.json        ──┤→ collector_v2.py    (loaders)
sources/cnf_full_v5.json      ──┘

raw/usda_flat.json            ──┐
raw/ciqual_flat.json          ──┤→ build_ontology_v6.py  →  reference/ontology_v6.json
raw/cnf_full_v5.json          ──┘                           reference/reference_db.json
                                                             reference/ontology_v6_report.json

processed/nutrition_v2.json  ──→  auto_correct_v6.py   →  reference/nutrition_corrected.json
                             +    [lit ontology_v6]         logs/corrections_log.json
                             ontology_v6.json

nutrition_corrected.json     ──→  validator_v11.py      →  outputs/validation_report.json
                                                            outputs/correction_proposals.json

recipes/recipes.json         ──→  audit_recipes_culinary.py  →  console / rapport

── DIAGNOSTIC ──────────────────────────────────────────────────────────────
                                  _diagnose_v2.py        →  console
```

---

## Versions LIGHT / FULL des sources

Les scripts (`collector_v2`, `build_ontology_v6`, `auto_correct_v6`) fonctionnent
en **mode dégradé automatique** : si la version complète est absente, la version
light est utilisée avec un avertissement.

| Source | Light (dev) | Full (prod) |
|--------|-------------|-------------|
| CIQUAL | `ciqual_flat_light.json` (130 aliments) | `ciqual_flat.json` (~2800) |
| USDA | `usda_flat_light.json` (20 aliments) | `usda_flat.json` (~2500) |
| CNF | `cnf_v5_light.json` (87 aliments) | `cnf_full_v5.json` (3444) |

Placer les versions complètes dans : `backend/data/nutrition/raw/`

---

## Scripts actifs — `scripts/nutrition/`

### `collector_v2.py` ✅ NOUVEAU

| Champ | Valeur |
|-------|--------|
| Version | v2 |
| Rôle | Loaders Python pour les 3 sources (CIQUAL, USDA, CNF) |
| Champs couverts | **42 champs** (vs 15 en v5) |
| Auto-fallback | ✓ full → light si absent |
| Exports | `CIQUALLoader`, `USDALoader`, `CNFLoader`, `load_all_sources()` |
| Remplace | `sources/collector.py` (v1, 6 champs) |

Champs **nouveaux** exposés par `collector_v2` :

| Champ | Source | Note |
|-------|--------|------|
| `starch_g` | CIQUAL + USDA | Amidon (manquant à 69% en v2) |
| `alcohol_g` | CIQUAL | Alcool (manquant à 99% en v2) |
| `scientific_name` | CIQUAL | Nom latin (manquant à 100% en v2) |
| `iodine_ug` | CIQUAL | Iode (absent du schema v2) |
| `choline_mg` | USDA | Choline (absent du schema v2) |
| `trans_fat_g` | USDA | Gras trans (absent du schema v2) |
| `beta_carotene_ug` | CIQUAL | Bêta-carotène (absent du schema v2) |
| `vitamin_k2_ug` | CIQUAL | Vitamine K2 (absent du schema v2) |
| `polyols_g` | CIQUAL | Polyols (absent du schema v2) |
| `organic_acids_g` | CIQUAL | Acides organiques (absent du schema v2) |
| `omega3_ala_g` | CIQUAL + USDA | ALA séparé |
| `omega3_epa_g` | CIQUAL + USDA | EPA séparé |
| `omega3_dha_g` | CIQUAL + USDA | DHA séparé |

---

### `build_ontology_v6.py` ✅ NOUVEAU

| Champ | Valeur |
|-------|--------|
| Version | v6 |
| Input | `raw/usda_flat.json`, `raw/ciqual_flat.json`, `raw/cnf_full_v5.json` |
| Output | `reference/ontology_v6.json`, `reference/reference_db.json` |
| Précédent | `build_ontology_v5.py` (15 champs) |
| Fixes v6 | 42 champs (vs 15), fractions omega3, scientific_name CIQUAL, `iodine`, `choline` |
| Compat | `reference_db.json` conservé pour `auto_correct` |
| Statut | ✅ Opérationnel |

---

### `auto_correct_v6.py` ✅ NOUVEAU

| Champ | Valeur |
|-------|--------|
| Version | v6 |
| Input | `processed/nutrition_v2.json`, `reference/ontology_v6.json` |
| Output | `reference/nutrition_corrected.json`, `logs/corrections_log.json` |
| Précédent | `auto_correct_v5.py` (15 champs sources) |
| Fixes v6 | 30 champs sources + 5 champs calculés |
| Champs calculés | `nova_group`, `health_score`, `bioavailability_protein`, `glycemic_load`, `glycemic_index_source` |
| Statut | ✅ Opérationnel |

#### Champs calculés (logique interne, pas de source externe) :

| Champ | Méthode |
|-------|---------|
| `nova_group` | Règles NOVA 1-4 : `category` + `ingredient_type` |
| `health_score` | Score 0-100 : fibres + protéines + micros − sucre − sat_fat − sodium |
| `bioavailability_protein` | Table PDCAAS/DIAAS par catégorie (0.55 à 0.97) |
| `glycemic_load` | `GI × carbs_g / 100` |
| `glycemic_index_source` | `"measured"` si CIQUAL/Sydney GI, sinon `"estimated"` |
| `alcohol_g = 0.0` | Pour tous les aliments non-alcoolisés (raw/cooked/dried...) |

---

### `validator_v11.py` ✅ ACTIF (inchangé)

| Champ | Valeur |
|-------|--------|
| Version | v11 |
| Input | `reference/nutrition_corrected.json` + CIQUAL xlsx (opt.) + USDA (opt.) |
| Output | `outputs/validation_report.json`, `outputs/correction_proposals.json` |
| Note | Lire `nutrition_corrected.json` (pas `nutrition_database_cleaned_final.json`) |

---

## Ordre d'exécution

```bash
# Étape 1 — Construire l'ontologie v6 (source de référence)
python scripts/nutrition/build_ontology_v6.py

# Étape 2 — Corriger et enrichir nutrition_v2
python scripts/nutrition/auto_correct_v6.py

# Étape 3 — Valider le résultat
python scripts/nutrition/validator_v11.py --audit

# Étape 4 — (optionnel) Appliquer les propositions de correction
python scripts/nutrition/validator_v11.py --apply --severity=critical
```

---

## Champs schema v3.0 → couverture après pipeline v6

| Champ | Avant v6 | Après v6 | Source |
|-------|----------|----------|--------|
| `scientific_name` | 0% | ~60% | CIQUAL |
| `nova_group` | 0% | **~100%** | calculé |
| `health_score` | 0% | **~95%** | calculé |
| `bioavailability_protein` | 0% | **~100%** | table statique |
| `glycemic_index_source` | 0% | **~85%** | inféré |
| `alcohol_g` | 1% | **~99%** | CIQUAL + règle |
| `starch_g` | 31% | **~75%** | CIQUAL + USDA |
| `glycemic_load` | 39% | **~82%** | calculé |
| `iodine_ug` | absent | présent | CIQUAL |
| `choline_mg` | absent | présent | USDA |
| `omega3_ala/epa/dha_g` | absent | présent | CIQUAL + USDA |

---

## Fichiers obsolètes (ne plus utiliser)

| Fichier | Remplacé par |
|---------|-------------|
| `sources/collector.py` | `sources/collector_v2.py` |
| `build_ontology_v5.py` | `build_ontology_v6.py` |
| `auto_correct_v5.py` | `auto_correct_v6.py` |
| `reference/ontology_v5.json` | `reference/ontology_v6.json` |
| `nutrition_database_cleaned_final.json` | `nutrition_corrected.json` |
