# Validation produit — Impact UX de la migration des catégories ingrédients

**Statut : ✅ VALIDÉ** — décisions A.3 + B.1 + C.2 + D retenues (voir § 5).

**Contexte.** La liste de courses (`/api/planning/shopping-list`) et l'estimation de quantités par défaut dans le moteur nutrition utilisent le champ `category` de chaque ingrédient. Le nouveau dictionnaire (`ingredients_dictionary_v2`) remplace ce champ par la **position dans une hiérarchie à 3 niveaux** (`categories → subcategories → ingredient_groups`).

**Ce document liste** les écarts entre l'ancien et le nouveau schéma, identifie 5 régressions UX, propose un mapping FR pour l'affichage et 4 décisions à valider.

---

## 1. Photographie de l'écart

### Ancien schéma — 19 catégories à plat (510 ingrédients)

| Catégorie       | Ingrédients | | Catégorie         | Ingrédients |
|-----------------|-------------|---|-------------------|-------------|
| `vegetable`     | 85          | | `dairy_alternative` | 13        |
| `grain`         | 84          | | `liquid`          | 11          |
| `herb_spice`    | 74          | | `protein_plant`   | 10          |
| `fruit`         | 54          | | `nut_seed`        | 9           |
| `condiment`     | 52          | | `superfood`       | 5           |
| `legume`        | 32          | | `fermented`       | 5           |
| `fat`           | 28          | | `leavening`       | 3           |
| `dairy`         | 25          | | `egg`             | 3           |
| `sweetener`     | 15          | | `alcohol`         | 1           |
| | | | `additive`        | 1           |

### Nouveau schéma — 15 catégories racines (2 105 groupes)

| `cat_id` (technique)                | Libellé FR proposé        | Nombre approx. de groupes |
|-------------------------------------|---------------------------|---------------------------|
| `fruits`                            | Fruits                    | ~210                      |
| `vegetables`                        | Légumes                   | ~290                      |
| `herbs_and_spices`                  | Herbes & épices           | ~270                      |
| `cereals_and_grains`                | Céréales & grains         | ~240                      |
| `legumes`                           | Légumineuses              | ~110                      |
| `dairy_products`                    | Produits laitiers & alternatives | ~210               |
| `fats_and_oils`                     | Matières grasses & huiles | ~43                       |
| `nuts_and_seeds`                    | Fruits à coque & graines  | ~155                      |
| `condiments_and_sauces`             | Condiments & sauces       | ~110                      |
| `sugars_honeys_and_confectionery`   | Sucres, miels & confiseries | ~80                     |
| `prepared_dishes_and_mixes`         | Plats préparés & mélanges | ~140                      |
| `beverages`                         | Boissons                  | ~80                       |
| `eggs`                              | Œufs                      | ~25                       |
| `seaweeds_and_sea_vegetables`       | Algues & légumes marins   | ~40                       |
| `leavening_agents_and_additives`    | Levures & additifs        | ~30                       |

---

## 2. Migration observée — granularité préservée

Mapping calculé sur les 510 ingrédients de l'ancien dict pour lesquels un `group_id` correspondant existe dans le nouveau :

| Ancienne catégorie     | Nouvelle dominante (% si ≥ 80 %) | Verdict |
|------------------------|----------------------------------|---------|
| `vegetable`            | `vegetables` (90 %)              | ✅ stable |
| `fruit`                | `fruits` (88 %)                  | ✅ stable |
| `grain`                | `cereals_and_grains` (85 %)      | ✅ stable |
| `legume`               | `legumes` (91 %)                 | ✅ stable |
| `dairy`                | `dairy_products` (100 %)         | ✅ stable |
| `egg`                  | `eggs` (100 %)                   | ✅ stable |
| `additive`             | `leavening_agents_and_additives` (100 %) | ✅ stable |
| `leavening`            | `leavening_agents_and_additives` (100 %) | ✅ stable |
| `alcohol`              | `beverages` (100 %)              | ✅ stable |
| `fermented`            | `legumes` (100 %)                | ⚠️ glissement sémantique (miso/tempeh/natto = légumes ? techniquement oui — soja fermenté) |

---

## 3. Régressions UX identifiées

### Régression 1 — Fusion **`dairy` + `dairy_alternative` → `dairy_products`**

| Ancienne situation | Nouvelle situation |
|--------------------|--------------------|
| 25 produits laitiers d'origine animale dans une catégorie séparée des 13 alternatives végétales | Les 38 produits se retrouvent dans une catégorie unique `dairy_products` |

**Impact utilisateur** : un utilisateur vegan qui consulte sa liste de courses verra son lait d'amande à côté du lait de vache de son colocataire. Le filtre `diet=vegan` enlève les produits animaux mais le **regroupement visuel** disparaît.

**Décision requise :** voir option § 4.A.

---

### Régression 2 — Disparition du regroupement **`condiment`**

L'ancienne catégorie `condiment` (52 ingrédients) éclate dans 7 catégories nouvelles :

| Destination dans le nouveau schéma | Exemples | % |
|-----------------------------------|----------|---|
| `condiments_and_sauces`            | moutarde, ketchup, mayo, sauce piquante | 36 % |
| `fruits`                           | olives, câpres, citron confit | 18 % |
| `nuts_and_seeds`                   | tahini, beurre de cacahuète, pistou | 9 % |
| `legumes`                          | miso, tempeh, sauce soja artisanale | 9 % |
| `vegetables`                       | concentré de tomate, ail confit | 9 % |
| `prepared_dishes_and_mixes`        | pesto, harissa, chutney | 9 % |
| `sugars_honeys_and_confectionery`  | sirop d'érable salé, miel infusé | 9 % |

**Impact utilisateur** : section "Condiments" dans la liste de courses devient orpheline ; le rayon "épicerie fine" mental du client n'a plus d'équivalent en backend.

**Décision requise :** voir option § 4.B.

---

### Régression 3 — Catégorie **`liquid`** dispersée

11 ingrédients dispersés en 4 catégories : `beverages` (40 %), `dairy_products` (20 %), `legumes` (20 %), `prepared_dishes_and_mixes` (20 %). Bouillons, eaux florales, jus, court-bouillons cessent d'avoir un regroupement unique.

**Impact :** mineur — les liquides ne sont pas une catégorie d'achat traditionnelle.

---

### Régression 4 — Catégorie **`superfood`** disparue

5 ingrédients passent à `seaweeds_and_sea_vegetables` (spiruline) ou `vegetables` (chou kale, baies de goji rangées comme fruits). Le tag marketing "superfood" disparaît du data layer.

**Impact :** côté liste de courses, mineur. Mais si l'UI a un filtre "Superaliments" exposé au front, il faut le re-câbler (via `diet_profile.high_protein`/`high_fiber` ou un nouveau filtre dérivé).

---

### Régression 5 — Catégorie **`herb_spice`** scindée

64 % restent dans `herbs_and_spices`, mais **28 % migrent en `vegetables`** : ail, oignon, échalote, ciboulette, certaines variétés de poivron. La logique du dict v2 (CIQUAL) traite l'ail comme un légume, pas une épice.

**Impact :** un utilisateur cherchant "épices" dans sa liste de courses ne verra plus l'ail. Côté supermarché c'est faux (l'ail est au rayon fruits & légumes), donc **le nouveau classement est en réalité plus correct**, mais il faut le savoir.

---

## 4. Décisions à valider avec le produit

### Décision A — Fusion dairy / dairy_alternative

**Options :**

| Option | Description | Effort |
|--------|-------------|--------|
| **A.1** | Accepter la fusion. Tout dans "Produits laitiers & alternatives". | 0 |
| **A.2** | Créer un sous-regroupement UI : `dairy_products` → afficher 2 sous-sections "Animal" / "Végétal" en se basant sur `diet_profile.vegan` | 2 h front |
| **A.3** | Conserver les deux catégories distinctes dans l'API en post-traitement : `dairy_products` + `vegan = True` → libellé "Alternatives végétales" | 1 h back |

**Recommandation backend : A.3.** Conserve la sémantique métier (alimentation végétale = catégorie à part entière), évite de toucher au front, code isolé dans `planning_engine/shopping.py`.

---

### Décision B — Regroupement des condiments éclatés

**Options :**

| Option | Description | Effort |
|--------|-------------|--------|
| **B.1** | Accepter l'éclatement. Les condiments tombent là où la classification CIQUAL les met. | 0 |
| **B.2** | Backend : maintenir une **liste blanche** d'`group_id` qu'on force en catégorie d'affichage `"condiments"` (tahini, miso, pesto, harissa, sauce soja, …) | 2 h back + curation manuelle |
| **B.3** | Front : créer une vue UX "Condiments & sauces" qui agrège dynamiquement plusieurs `cat_id` selon des règles (ex. tout `prepared_dishes_and_mixes` + items spécifiques) | 4 h front |

**Recommandation : B.2** si le rayon "épicerie / condiments" est important côté produit. Sinon B.1 est défendable (CIQUAL fait foi).

---

### Décision C — Catégorie `superfood`

**Options :**

| Option | Description |
|--------|-------------|
| **C.1** | Supprimer le filtre "Superaliments" du front (s'il existe). |
| **C.2** | Remplacer par un filtre dérivé : `nutrition_flags.minerals = True AND nutrition_flags.vitamins = True` (sera dérivé automatiquement par `_derive_nutrition_flags` après migration, cf. § 2.6 du plan technique) |

**Recommandation : C.2.** Plus rigoureux qu'un tag marketing, et automatique.

---

### Décision D — Libellés FR pour l'affichage

Valider le mapping `cat_id` → libellé FR du tableau § 1.2 ci-dessus. Suggestions ouvertes :

| `cat_id`                            | Proposition principale         | Alternative              |
|-------------------------------------|--------------------------------|--------------------------|
| `dairy_products`                    | Produits laitiers & alternatives | Crémerie               |
| `fats_and_oils`                     | Matières grasses & huiles      | Huiles                   |
| `condiments_and_sauces`             | Condiments & sauces            | Épicerie fine            |
| `sugars_honeys_and_confectionery`   | Sucres, miels & confiseries    | Sucres & douceurs        |
| `prepared_dishes_and_mixes`         | Plats préparés & mélanges      | Traiteur                 |
| `leavening_agents_and_additives`    | Levures & additifs             | Pâtisserie technique     |
| `seaweeds_and_sea_vegetables`       | Algues & légumes marins        | Saveurs marines          |

Le mapping est centralisé dans `core/i18n/categories_fr.json` (à créer) — modification simple par le produit sans redéploiement code.

---

## 5. Synthèse des décisions RETENUES

| Décision | Question | Choix retenu | Conséquence code |
|----------|----------|--------------|------------------|
| **A.3** | Fusion dairy / alternatives ? | **Séparation logique côté backend** : tag `dairy_products_vegan` injecté en post-traitement quand `diet_profile.vegan = True`. | +1 h dans `planning_engine/shopping.py` |
| **B.1** | Regroupement des condiments ? | **Accepter le classement CIQUAL.** Tahini, miso, pesto, etc. restent éclatés sur 7 catégories selon la nomenclature officielle. | 0 |
| **C.2** | Tag superfood ? | **Filtre dérivé** `nutrition_flags.minerals == True AND nutrition_flags.vitamins == True`. Aucun tag marketing résiduel. | 0 (déjà couvert par le recalcul des `nutrition_flags`) |
| **D** | Libellés FR ? | **Validé** — tableau § 4.D retenu. Matérialisé dans `backend/core/i18n/categories_fr.json` (nouveau, modifiable sans redéploiement code). | +30 min |

**Impact total sur le plan technique : +1 h 30** — le plan passe de 11 h 30 à 12 h 30.

Les patches précis sont consignés dans `PLAN_MIGRATION_v7.md` § 2.11 et § 6 (étapes 9 et 9bis).

---

## 6. Annexe — Exemples concrets de liste de courses

### Avant migration

```
🥦 Légumes      : tomate, courgette, ail, oignon
🌿 Herbes/épices: persil, cumin, ail noir
🥛 Laitiers     : crème fraîche
🌱 Alt. végétales: lait d'amande
🍯 Condiments   : moutarde, tahini, sauce soja, pesto
```

### Après migration (sans correctifs A.3 / B.2)

```
🍅 Légumes              : tomate, courgette, ail, oignon, ail noir, concentré de tomate
🌿 Herbes & épices      : persil, cumin
🥛 Produits laitiers    : crème fraîche, lait d'amande
🌰 Fruits à coque       : tahini
🫘 Légumineuses         : sauce soja, miso
🍴 Plats préparés       : pesto
🌶 Condiments & sauces  : moutarde
```

### Après migration (avec correctifs A.3 + B.2)

```
🍅 Légumes              : tomate, courgette, ail, oignon, ail noir
🌿 Herbes & épices      : persil, cumin
🥛 Produits laitiers    : crème fraîche
🌱 Alternatives végét.  : lait d'amande
🌶 Condiments & sauces  : moutarde, tahini, sauce soja, pesto, miso, concentré de tomate
```

---

**Action attendue du produit.** Valider les 4 décisions (A/B/C/D). Une réponse type "A.3 + B.2 + C.2 + libellés OK avec quelques retouches" suffit à débloquer l'implémentation backend.
