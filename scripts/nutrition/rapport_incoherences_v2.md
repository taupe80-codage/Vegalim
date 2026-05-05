# Rapport d'incohérences — nutrition_v2.json (v6.18)
*Analyse croisée nutrition_v2.json × validator_v11.py × patch_report_v8.json*
*290 bases · 466 variants*

---

## 🔴 Critique (4 issues)

### 1. `schema_version` drift — root vs `_meta`

| Champ | Valeur |
|---|---|
| `root.schema_version` | `6.0` |
| `_meta.schema_version` | `6.18` |

Le champ racine `schema_version` n'a jamais été mis à jour depuis la migration initiale. Il est bloqué à `6.0` pendant que `_meta` suit correctement les promotions. Si un backend lit `root.schema_version` pour valider le schéma, il voit une version 20+ mineurs en retard.

**Fix** : Dans `promote_nutrition.py`, à l'étape d'écriture du canonical, synchroniser `db["schema_version"]` avec `db["_meta"]["schema_version"]`.

---

### 2. `chocolate/powder` — energy mismatch Δ = 89%

| Champ | Valeur |
|---|---|
| `calories_kcal` | 229.0 |
| Atwater estimé | 433.3 |
| `protein_g` | 19.6 |
| `carbs_g` | 57.9 |
| `fat_g` | 13.7 |
| `fiber_g` | 33.2 |
| `carbs_schema` | `total` |

La valeur 229 kcal est correcte (USDA FDC 19165 — cacao poudre non sucré). L'écart vient de 33g de fibres + tanins qui réduisent fortement la digestibilité — exactement le même phénomène que `carob` (222 kcal, Δ~70%), qui est déjà dans `FORMULA_EXCEPTIONS`. `chocolate/powder` a été oublié.

**Fix** : Ajouter `"chocolate"` (ou au minimum `"chocolate/powder"`) à `FORMULA_EXCEPTIONS` dans `validator_v11.py` avec la justification tanins/fibres concentrées.

---

### 3. `seeds/pumpkin` — fractions lipidiques écrasées (FA coverage 0.1%)

| Champ | Valeur actuelle | Valeur USDA FDC 170556 |
|---|---|---|
| `fat_g` | 49.05 | 49.1 |
| `saturated_fat_g` | **0.015** | **8.9** |
| `monounsaturated_fat_g` | **0.005** | **16.2** |
| `polyunsaturated_fat_g` | **0.031** | **20.9** |

Contamination de patch : `fat_g` a été corrigé à 49g (USDA, bug dilution) mais les fractions lipidiques n'ont pas été mises à jour en parallèle — elles conservent des valeurs traces (~0.05g total pour 49g de fat). La correction `patch_nutrition_v8` est dans `urgent_fixes` pour les calories/macros mais n'a pas touché sat/mufa/pufa.

**Fix** : Injecter les FA correctes via `_patch_variant` dans `patch_nutrition_v8.py` :
`sat=8.91, mufa=16.24, pufa=20.96` (USDA FDC 170556 pepitas dried).

---

### 4. `water/default` — `sugar_g = 7.29` (contamination)

| Champ | Valeur |
|---|---|
| `calories_kcal` | 0 |
| `carbs_g` | 0 |
| `sugar_g` (long) | **7.29** ← contamination |
| `sugar` (court) | 0.0 ← champ court résiduel |

L'eau a 7.29g de sucre selon `sugar_g` — contamination évidente (probable fusion multi-source avec un bouillon ou une eau aromatisée). Le champ court `sugar=0.0` est un résidu d'une ancienne version. Les deux bugs coexistent sur le même variant.

**Fix** : `sugar_g` → `0` et supprimer le champ court `sugar`.

---

## 🟡 Moyen (9 issues)

### 5. `tofu/silken` — energy mismatch Δ = 21.9% + valeur suspecte

| Champ | Valeur |
|---|---|
| `calories_kcal` | 133.25 |
| Atwater estimé | 162.5 |
| `protein_g` | 10.0 |
| `carbs_g` | 7.02 |
| `fat_g` | 10.49 |

133 kcal/100g correspond au tofu **ferme** (USDA ~144 kcal). Le tofu **soyeux** (silken) est entre 55–65 kcal/100g selon USDA FDC #16127. Probable confusion de variant lors de la fusion : les macros de tofu ferme ont été associées au variant `silken`.

**Fix** : Réaligner sur USDA FDC #16127 (tofu silken) : kcal≈55, protein≈5.3g, fat≈3.0g, carbs≈1.4g.

---

### 6. `seeds/*` — fiber > carbs non exemptés (5 variants)

| Variant | `fiber_g` | `carbs_g` | `carbs_schema` |
|---|---|---|---|
| `seeds/default` | 16.9 | 9.14 | — |
| `seeds/chia` | 34.4 | 7.72 | — |
| `seeds/sesame` | 16.9 | 9.14 | — |
| `seeds/black_sesame` | 16.9 | 9.14 | — |

Ces valeurs sont correctes (glucides disponibles CIQUAL). `FIBER_GT_CARBS_EXCEPTIONS` contient `"coconut"`, `"hazelnut"`, `"flaxseed"` mais pas `"seeds"`. Les variants sesame/chia sont déjà documentés dans `patch_nutrition_v8` (`carbs_schema: available`).

**Fix** : Ajouter `"seeds"` à `FIBER_GT_CARBS_EXCEPTIONS` dans `validator_v11.py`.

---

### 7. `seaweed/*` — fiber > carbs non exemptés (2 variants)

| Variant | `fiber_g` | `carbs_g` |
|---|---|---|
| `seaweed/default` | 36.8 | 11.7 |
| `seaweed/irish_moss` | 30.99 | 15.0 |

`seaweed/nori`, `seaweed/wakame`, `seaweed/kombu` sont dans le validator comme exceptions path-level mais pas `seaweed/default` ni `seaweed/irish_moss`.

**Fix** : Ajouter `"seaweed"` (base entière) à `FIBER_GT_CARBS_EXCEPTIONS`, ou les deux variants manquants en path-level.

---

### 8. `mushroom/morel` — fiber > carbs (schéma `available`)

| Champ | Valeur |
|---|---|
| `carbs_g` | **0.1** |
| `fiber_g` | 2.8 |
| `carbs_schema` | `available` |

En schéma `available`, carbs=0.1g est plausible pour la morille (glucides digestibles très faibles). Mais le validator n'a pas cette exception → faux positif à omettre dans les rapports.

**Fix** : Ajouter `"mushroom/morel"` à `FIBER_GT_CARBS_EXCEPTIONS` dans `validator_v11.py`.

---

### 9. `basil/default` — fiber > carbs post-patch

| Champ | Valeur |
|---|---|
| `carbs_g` | 10.1 |
| `fiber_g` | 33.78 |

Le patch `urgent_fixes` a recalculé les macros de basil (kcal, protein, fat) mais pas traité le ratio fiber/carbs. Pour du basilic séché (USDA), fiber~37g, carbs disponibles~11g : valeurs correctes. Non exempté dans le validator.

**Fix** : Ajouter `"basil"` à `FIBER_GT_CARBS_EXCEPTIONS`.

---

### 10. `flour/oat` — fractions lipidiques sous-estimées (FA coverage 27%)

| Champ | Valeur actuelle | Valeur USDA attendue |
|---|---|---|
| `fat_g` | 8.4 | 8.4 |
| `saturated_fat_g` | 0.63 | ~1.5 |
| `monounsaturated_fat_g` | 0.79 | ~3.0 |
| `polyunsaturated_fat_g` | 0.81 | ~3.3 |

FA sum actuelle = 2.23g pour 8.4g de fat (27%). Les fractions sont sous-estimées d'un facteur ~3–4x. Source probable : fusion CIQUAL (fat correct) + USDA FA sur farine partiellement dégrassée.

**Fix** : Réinjecter les FA depuis USDA FDC #173904 (oat flour, whole grain).

---

### 11. Champs courts résiduels (2 variants)

| Variant | Champ court | Valeur | Champ long | Valeur |
|---|---|---|---|---|
| `water/default` | `sugar` | 0.0 | `sugar_g` | 7.29 |
| `sauce/default` | `saturated_fat` | 0.05 | `saturated_fat_g` | 0.05 |

Deux champs courts du format legacy (`_SHORT_TO_LONG`) survivent dans le fichier. `sauce/default` est un doublon propre (même valeur). `water/default` est un doublon **dangereux** car les deux champs ont des valeurs différentes — le resolver peut lire l'une ou l'autre selon le code path.

**Fix** : Supprimer les champs courts dans les deux variants. Pour `water/default`, corriger aussi `sugar_g` → 0.

---

### 12. Champ `allergens` absent (5 variants)

Les variants suivants n'ont pas du tout le champ `allergens` (ni `[]`, ni valeur) :

- `ancho_chili/default`
- `chinese_cabbage/default`
- `dandelion/default`
- `chicory/default`
- `dried_pea/default`

Ces 5 variants sont des entrées manuelles pré-pipeline qui ont échappé à `_apply_allergen_rules()` parce que leurs bases ne figurent pas dans `BASE_ALLERGEN_RULES` ou `VARIANT_ALLERGEN_RULES`. Pour ces ingrédients (sans allergène EU 1169/2011 réel), le champ doit exister avec `[]`.

**Fix** : Initialiser `allergens: []` via une passe idempotente dans `_apply_allergen_rules()` pour tout variant sans ce champ.

---

## 🟢 OK — Faux positifs résolus

Ces anomalies apparentes sont toutes légitimes et correctement justifiées :

- `macro_sum > 105g` sur huiles, épices sèches, noix → fat~100g ou fibres concentrées, physiquement corrects
- `sat_gt_fat` : 0 violation (toutes corrigées par patch_v8)
- `sugar_gt_carbs` : 0 violation hors exceptions connues
- `omega > poly` : 0 violation (3 recalculs appliqués par patch_v8)
- `nut/brazil` fiber>carbs → schema `available`, valeur CIQUAL correcte
- `corn_husk/default` energy Δ=21% → feuilles de maïs (tamales), ingrédient non comestible, impact nutritionnel nul
- Base recipes : ✅ 0 survivante (`promote_nutrition.py --confirm` bien exécuté)

---

## 📊 Couverture CIQUAL 7.0 (données manquantes, pas de bug actif)

| Champ | Couverture | Statut |
|---|---|---|
| `starch_g` | 461/466 (99%) | ✅ |
| `beta_carotene_ug` | 277/466 (59%) | 🟡 |
| `iodine_ug` | 241/466 (52%) | 🟡 |
| `organic_acids_g` | 152/466 (33%) | 🟡 |
| `choline_mg` | 133/466 (29%) | 🔴 |
| `polyols_g` | 82/466 (18%) | 🔴 |
| `vitamin_k2_ug` | 25/466 (5%) | 🔴 |
| `trans_fat_g` | 21/466 (5%) | 🔴 |

Pas d'erreur active mais les 4 champs à couverture < 20% sont des angles morts pour tout calcul nutritionnel qui les utilise (labels EU, calcul NOVA affiné).

---

## Plan d'action priorisé

| Priorité | Fix | Fichier |
|---|---|---|
| P0 | `water/default` sugar_g=7.29 → 0 + supprimer champ court | `patch_nutrition_v8.py` |
| P0 | `seeds/pumpkin` FA : sat=8.91, mufa=16.24, pufa=20.96 | `patch_nutrition_v8.py` |
| P0 | `root.schema_version` sync avec `_meta.schema_version` | `promote_nutrition.py` |
| P1 | `chocolate/powder` → `FORMULA_EXCEPTIONS` (tanins/fibres) | `validator_v11.py` |
| P1 | `tofu/silken` macros → USDA FDC #16127 | `patch_nutrition_v8.py` |
| P1 | `flour/oat` FA → USDA FDC #173904 | `patch_nutrition_v8.py` |
| P1 | `sauce/default` supprimer champ court `saturated_fat` | `patch_nutrition_v8.py` |
| P2 | `seeds`, `seaweed`, `basil`, `mushroom/morel` → `FIBER_GT_CARBS_EXCEPTIONS` | `validator_v11.py` |
| P2 | 5 variants sans `allergens` → init `[]` dans `_apply_allergen_rules` | `promote_nutrition.py` |
| P3 | CIQUAL 7.0 : enrichir `trans_fat_g`, `vitamin_k2_ug`, `polyols_g`, `choline_mg` | `build_ontology_v6.py` |
