# Plan de migration v1.2 — code applicatif vers `ingredients_dictionary_v2`

**Périmètre :** ajuster `api/`, `core/`, `db/`, `services/`, `engine/` et les fichiers `data/` auxiliaires pour qu'ils consomment le nouveau `ingredients_dictionary_v2.json` (structure hiérarchique + `alias_index`) en restant alignés avec `nutrition_v2.json`.

**État :** v1.2 — 4 décisions métier + 4 décisions produit verrouillées. Audit KG terminé : périmètre réel = 175 ingrédients non résolus (et non 596). Audit engines terminé : 2 nouveaux couplages identifiés. Validation produit terminée : décisions UX consignées au § 0bis.

---

## 0. Décisions métier verrouillées

| # | Question | Décision | Détail |
|---|----------|----------|--------|
| 1 | Cible canonique pour `huile_friture` | `sunflower` (dans `fats_and_oils/oils`) | Le `group_id` `sunflower` est unique au dict et désigne l'huile (CIQUAL). Note : `sunflower` est aussi le nom court côté `nuts_and_seeds` pour la graine — voir § 7 risque collisions. |
| 2 | Cible canonique pour `lait` | `whole_milk_uht_uht_whole` | Lait entier UHT — consommation FR dominante. |
| 3 | Stratégie `nutrition_flags` | Recalculer avant go-live | 6 flags re-dérivés depuis `nutrition_v2` avec seuils explicites (cf. § 2.6). |
| 4 | Audit KG unifié | Avant implémentation, **terminé** | Périmètre vrai = 175 ingrédients non résolus (pas 596). Détails dans `AUDIT_KG_UNMATCHED.md`. |

## 0bis. Décisions produit verrouillées (validation UX des catégories)

Document support : `VALIDATION_PRODUIT_CATEGORIES.md`. Quatre décisions retenues :

| # | Sujet | Décision retenue | Implication code |
|---|-------|------------------|------------------|
| **A.3** | Fusion `dairy` + `dairy_alternative` dans `dairy_products` | **Séparation logique côté backend.** Dans `planning_engine/shopping.py`, post-traiter : tout groupe `dairy_products` avec `diet_profile.vegan = True` est ré-étiqueté `dairy_products_vegan` pour l'affichage. | +1 h sur § 2.11 |
| **B.1** | Éclatement des condiments sur 7 catégories | **Accepter le classement CIQUAL.** Pas de liste blanche backend. Le tahini reste dans `nuts_and_seeds`, le miso dans `legumes`, le pesto dans `prepared_dishes_and_mixes`. | 0 — neutre |
| **C.2** | Disparition du tag `superfood` | **Filtre dérivé.** Tout client cherchant "superaliments" passe par : `nutrition_flags.minerals == True AND nutrition_flags.vitamins == True` (les flags sont eux-mêmes dérivés de `nutrition_v2`, cf. § 2.6). | 0 — déjà couvert par § 2.6 |
| **D** | Libellés FR des 15 catégories racines | **Tableau § 1.2 du doc produit retenu.** Mapping à matérialiser dans `core/i18n/categories_fr.json` (nouveau fichier — modifiable sans déploiement code). | +30 min — nouveau fichier i18n |

---

## 1. Photographie du nouveau schéma

### 1.1 Structure `ingredients_dictionary_v2.json`

```
{
  "_schema": { version: "2.0", total_entries: 2125, total_aliases: 257, ... },
  "categories": {                              ← 15 catégories
    "<cat_id>": {
      "id": "...",
      "subcategories": {
        "<sub_id>": {
          "id": "...",
          "ingredient_groups": {
            "<group_id>": { ...payload... }    ← 2 105 groupes uniques (= 2 125 entrées
          }                                       car ≈ 20 doublons cross-catégorie)
        }
      }
    }
  },
  "alias_index": { "<alias>": "<group_id>", … },   ← 257 entrées, 100 % résolues
  "orphans": []
}
```

### 1.2 Payload d'un `ingredient_group`

| Champ                        | Nature                         | Remplace l'ancien…     |
|------------------------------|--------------------------------|------------------------|
| `v32_ing_id`, `v32_var_id`   | IDs legacy                     | —                      |
| `source`, `source_id`, `source_label` | CNF / CIQUAL / USDA   | —                      |
| **`canonical_name_fr`**      | str — nom FR de référence      | **`name_fr`**          |
| **`canonical_name_en`**      | str — nom EN de référence      | **`name_en`**          |
| `axes`                       | dict — dimensions de variant (`form`, `seasoning`, `etat_cuisson`, …) | `variant_dimensions` |
| `aliases`                    | list — **toujours vide** (résolution via `alias_index` global) | `synonyms` |
| **`diet_profile`**           | dict — `vegan, vegetarian, gluten_free, lactose_free, nut_free, soy_free, egg_free, high_protein, high_fiber, high_fat, diabetic_friendly` | **`diet_profile`** (conservé) + absorbe `nutrition_flags.high_*` |
| **`allergens_eu`**           | list — `sulphites, milk, eggs, gluten, …` | **`allergen_flags`** (changement de format : liste au lieu de dict) |
| `nova_group`                 | int 1-4 — classification NOVA  | —                      |
| `bioavailability_protein`    | float                          | —                      |
| `culinary`                   | dict — `properties, flavor_profile, cooking_behavior, substitutions` | `flavor_profile` (déplacé) + `substitutions` (déplacé) |
| `alt_sources`                | list — sources nutritionnelles alternatives | — |

### 1.3 Champs disparus de l'ancien dict (impact code)

| Ancien champ         | Devient…                                            |
|----------------------|-----------------------------------------------------|
| `name_fr`            | `canonical_name_fr`                                 |
| `name_en`            | `canonical_name_en`                                 |
| `id`                 | clé du dict (`group_id`)                             |
| `nutrition_key`      | implicite — `group_id` = clé `nutrition_v2`         |
| `category`, `family`, `parent` | position dans l'arbre                     |
| `synonyms`           | `alias_index` global (top-level)                    |
| `allergen_flags`     | `allergens_eu` (passe d'un **dict** booléen à une **liste**) |
| `nutrition_flags`    | absorbé par `diet_profile.high_protein/high_fiber/high_fat` (les `*_calcium/iron/…` disparaissent — à recalculer côté code ou à oublier) |
| `flavor_profile`     | `culinary.flavor_profile`                           |
| `substitutions`      | `culinary.substitutions`                            |

### 1.4 Chemins (confirmés par `engine/config.py`)

```python
DATA_ROOT      = backend/data
RECIPES_PATH   = .../recipes/recipes.json
DICT_PATH      = .../ingredients/ingredients_dictionary.json     ← à pointer vers v2
NUTRITION_PATH = .../nutrition/processed/nutrition_v2.json       ← déjà OK
```

**Décision recommandée — § 2.0 ci-dessous.**

---

## 2. Code applicatif — modifications fichier par fichier

### 2.0 `engine/config.py` (décision préalable)

Deux stratégies :

| Option | Action | Avantage | Inconvénient |
|--------|--------|----------|--------------|
| **A — Renommer le fichier** | Remplacer `ingredients_dictionary.json` par le nouveau (renommé en place) | Aucun changement de code de chargement | Perte de la traçabilité du versioning |
| **B — Modifier `DICT_PATH`** | `DICT_PATH = DATA_ROOT / "ingredients" / "ingredients_dictionary_v2.json"` | Traçabilité, rollback trivial | 1 ligne à éditer + déploiement coordonné |

**Recommandation : option B.** Modification minimale, rollback en une ligne, alignement avec `NUTRITION_PATH` (qui porte déjà `_v2`).

### 2.1 `core/data_io.py` — `load_ingredients_dict()` (l. 191-201)

**Avant :**
```python
ings = raw.get("ingredients", raw) if isinstance(raw, dict) else raw
return {i["id"]: i for i in ings if isinstance(i, dict) and "id" in i}
```

**Après — aplatir l'arbre :**
```python
def _loader():
    raw = load_json(_path, default={})
    flat: dict[str, dict] = {}
    for cat in raw.get("categories", {}).values():
        for sub in cat.get("subcategories", {}).values():
            for gid, entry in sub.get("ingredient_groups", {}).items():
                # Injection rétro-compat : l'id du groupe est sa clé
                entry.setdefault("id", gid)
                flat[gid] = entry
    return flat
return _ingredients_cache.get(_path, _loader)
```

**Nouveau loader complémentaire :**
```python
_alias_index_cache = _MtimeCache("load_alias_index")

def load_alias_index() -> dict[str, str]:
    _path = DATA_ROOT / "ingredients" / "ingredients_dictionary_v2.json"
    def _loader():
        raw = load_json(_path, default={})
        return raw.get("alias_index", {})
    return _alias_index_cache.get(_path, _loader)
```

Exposer également `load_alias_index.cache_clear`.

### 2.2 `db/culinary_repositories.py`

#### `_ingredients_raw()` (l. 187-194) — adapter au retour de `load_ingredients_dict`

`load_ingredients_dict()` retourne désormais un **dict aplati** plutôt qu'une liste. Choix d'API :

```python
@lru_cache(maxsize=1)
def _ingredients_raw() -> list[dict]:
    """Liste des ingredient_groups aplatis (id injecté)."""
    from backend.core.data_io import load_ingredients_dict
    return list(load_ingredients_dict().values())
```

#### `_ingredients_index()` (l. 203-210) — réécrire avec `alias_index`

```python
@lru_cache(maxsize=1)
def _ingredients_index() -> dict[str, dict]:
    """Index multi-clé → ingredient_group. Prend en compte alias_index."""
    from backend.core.data_io import load_ingredients_dict, load_alias_index
    groups       = load_ingredients_dict()
    alias_index  = load_alias_index()
    index: dict[str, dict] = {}

    # 1. Clé canonique du groupe
    for gid, entry in groups.items():
        index[gid.lower()] = entry
        for name_field in ("canonical_name_fr", "canonical_name_en"):
            val = entry.get(name_field)
            if val:
                index[val.lower()] = entry

    # 2. alias_index : <alias> → <group_id>
    for alias, gid in alias_index.items():
        target = groups.get(gid)
        if target is not None:
            index.setdefault(alias.lower(), target)

    return index
```

#### `invalidate_caches()` (l. 411-422) — ajouter alias

```python
load_alias_index.cache_clear()           # via data_io
_alias_index_raw.cache_clear()           # si un cache local est ajouté
```

#### `IngredientRepository` (l. 890-1040)

- `get_by_name`, `get_by_id` : OK tels quels — l'index `_ingredients_index()` couvre déjà `group_id`, `canonical_name_fr/en`, et les aliases.
- `get_substitutions(name)` : déplacer le chemin de lecture : `item.get("culinary", {}).get("substitutions", [])` au lieu de `item.get("substitutions")`.
- `get_nutrition_key(name)` : retourner directement la clé du groupe (l'`group_id` est désormais la clé `nutrition_v2`). Code-pattern :
  ```python
  for gid, entry in load_ingredients_dict().items():
      if entry is item: return gid
  ```
  ou plus propre : injecter `_group_id` dans `_loader` de `data_io` (déjà fait via `entry.setdefault("id", gid)` au § 2.1).
- `list_by_category(category)` : nouvelle implémentation
  ```python
  def list_by_category(self, category: str) -> list[dict]:
      from backend.core.data_io import load_json
      from backend.engine.config import DICT_PATH
      raw = load_json(DICT_PATH, default={})
      cat = raw.get("categories", {}).get(category.lower(), {})
      result = []
      for sub in cat.get("subcategories", {}).values():
          result.extend(sub.get("ingredient_groups", {}).values())
      return result
  ```
- `list_categories()` : retourner `list(raw["categories"].keys())`.

### 2.3 `engine/search_engine/resolver.py` (l. 30-65) — refonte complète

**Avant** : construction d'un `_synonym_map()` qui itère et lit `("name_fr", "name_en", "id")` + `item.get("synonyms")`.

**Après** : l'`alias_index` du dict v2 **fait déjà ce travail**. Le code devient :

```python
@lru_cache(maxsize=1)
def _synonym_map() -> dict[str, str]:
    """Synonyme normalisé → group_id canonique."""
    from backend.core.data_io import load_ingredients_dict, load_alias_index
    groups, aliases = load_ingredients_dict(), load_alias_index()
    mapping: dict[str, str] = {}

    # Canoniques : nom FR, nom EN, group_id
    for gid, entry in groups.items():
        mapping[_normalize(gid)] = gid
        for f in ("canonical_name_fr", "canonical_name_en"):
            val = entry.get(f)
            if val:
                mapping[_normalize(val)] = gid

    # Aliases globaux
    for alias, gid in aliases.items():
        mapping.setdefault(_normalize(alias), gid)

    return mapping
```

**Bénéfice :** suppression de l'itération sur `item.get("synonyms")` (champ disparu). Code plus court, plus rapide, plus exact (l'`alias_index` est curé par le pipeline).

### 2.4 `engine/search_token_generator.py` (l. 200-225, 320-322)

- L. 209 : `for name_field in ("name_fr", "name_en")` → `("canonical_name_fr", "canonical_name_en")`.
- L. 217 : `cat = d.get("category", "")` → la catégorie n'existe plus en champ direct. Deux options :
  - (a) Recalculer côté code par inversion (`{group_id: category_id}` construit au chargement de `data_io`).
  - (b) Supprimer cette logique de tokenisation si elle n'apporte plus assez de signal — _à arbitrer selon la couverture des `_CATEGORY_TOKENS`._
  
  **Recommandation (a)** : ajouter dans `data_io` un `load_group_to_category()` cached, retournant `{group_id: cat_id}`. Léger (≈ 2 000 entrées str→str) et n'introduit pas de régression.

### 2.5 `engine/score_engine/quality.py` (l. ~117)

- `profiles = [str(d["ings"].get(i, {}).get("flavor_profile", ""))]` → `…get("culinary", {}).get("flavor_profile", [])`.
- **Attention :** `culinary.flavor_profile` est une **liste**, pas une string. Adapter la jointure :
  ```python
  profiles_raw = [d["ings"].get(i, {}).get("culinary", {}).get("flavor_profile", []) for i in ings]
  profiles = [p for sub in profiles_raw for p in sub]
  ```

### 2.6 `services/enrichment_service.py` (l. 122-150, 307)

- `diet_profile` : OK — même clé, mêmes flags `vegan, vegetarian, gluten_free, lactose_free, nut_free, soy_free, egg_free` + `high_protein, high_fiber, high_fat`.
- `allergen_flags` → `allergens_eu` : **changement de structure**. La logique
  ```python
  af = ing_data.get("allergen_flags", {})
  if af.get("eggs"): agg_diet["egg_free"] = False
  ```
  devient :
  ```python
  af = ing_data.get("allergens_eu", [])
  if "eggs" in af: agg_diet["egg_free"] = False
  if "milk" in af: agg_diet["dairy_free"] = False
  if "soy"  in af: agg_diet["soy_free"]   = False
  ```
  (les codes EU sont : `milk, eggs, gluten, soy, peanuts, nuts, sesame, fish, crustaceans, molluscs, celery, mustard, lupin, sulphites`.)

#### Recalcul des 6 `nutrition_flags` depuis `nutrition_v2.json` (décision § 0.3)

Implémenter une fonction utilitaire **`_derive_nutrition_flags(group_id, nutr_db)`** dans `core/data_io.py`, cached, qui retourne un dict `{vitamins, minerals, omega3, antioxidant, low_sugar, low_sodium}`. Seuils proposés (référencés au **règlement UE 1924/2006** quand applicable) :

| Flag             | Seuil "True" si…                                                                 | Source du seuil |
|------------------|----------------------------------------------------------------------------------|-----------------|
| `vitamins`       | Au moins 1 vitamine ≥ 15 % de l'AR par 100 g (`vitamin_a_ug ≥ 120`, `vitamin_c_mg ≥ 12`, `vitamin_d_ug ≥ 0.75`, `vitamin_e_mg ≥ 1.8`, `vitamin_b9 (folate_ug) ≥ 30`, `vitamin_b12_ug ≥ 0.375`) | UE 1924 « source de » |
| `minerals`       | Au moins 1 minéral ≥ 15 % AR : `calcium_mg ≥ 120`, `iron_mg ≥ 2.1`, `magnesium_mg ≥ 56`, `zinc_mg ≥ 1.5`, `potassium_mg ≥ 300`, `selenium_ug ≥ 8.25` | UE 1924 |
| `omega3`         | `omega3_ala_g ≥ 0.3` **OU** `omega3_epa_g + omega3_dha_g ≥ 0.04`                  | UE 1924 « source d'oméga-3 » |
| `antioxidant`    | `vitamin_c_mg ≥ 12` **OU** `vitamin_e_mg ≥ 1.8` (pas de seuil officiel pour polyphénols → on s'aligne sur vit C/E « source ») | Proxy UE 1924 |
| `low_sugar`      | `sugar_g ≤ 5.0` (allégation « faible teneur en sucres » pour aliment solide)     | UE 1924 |
| `low_sodium`     | `sodium_mg ≤ 120` (allégation « faible teneur en sodium »)                       | UE 1924 |

Pseudo-code :
```python
def _derive_nutrition_flags(gid: str, nutr_db: dict | None = None) -> dict:
    nutr_db = nutr_db or load_nutrition_db()
    v = nutr_db.get(gid, {}).get("variants", {}).get("default", {})
    g = lambda k: float(v.get(k, 0) or 0)
    vitamins = any([
        g("vitamin_a_ug") >= 120, g("vitamin_c_mg") >= 12,
        g("vitamin_d_ug") >= 0.75, g("vitamin_e_mg") >= 1.8,
        g("folate_ug") >= 30, g("vitamin_b12_ug") >= 0.375,
    ])
    minerals = any([
        g("calcium_mg") >= 120, g("iron_mg") >= 2.1,
        g("magnesium_mg") >= 56, g("zinc_mg") >= 1.5,
        g("potassium_mg") >= 300, g("selenium_ug") >= 8.25,
    ])
    omega3 = g("omega3_ala_g") >= 0.3 or (g("omega3_epa_g") + g("omega3_dha_g")) >= 0.04
    antioxidant = g("vitamin_c_mg") >= 12 or g("vitamin_e_mg") >= 1.8
    return {
        "vitamins":    vitamins,
        "minerals":    minerals,
        "omega3":      omega3,
        "antioxidant": antioxidant,
        "low_sugar":   g("sugar_g") <= 5.0,
        "low_sodium":  g("sodium_mg") <= 120,
    }
```

Dans `enrichment_service.enrich_why()`, remplacer la lecture `ing_data.get("nutrition_flags", {})` par un appel à cette fonction :
```python
nf = _derive_nutrition_flags(iid)
if nf["vitamins"]:    agg_nutr["vitamins"]   = True
if nf["minerals"]:    agg_nutr["minerals"]   = True
if nf["omega3"]:      agg_nutr["omega3"]     = True
if nf["antioxidant"]: agg_nutr["antioxidant"]= True
```

**Validation cible :** sur les 2 105 `ingredient_groups`, on attend approximativement :
- ~30 % avec `vitamins=True` (fruits, légumes, foie, abats),
- ~25 % avec `minerals=True` (légumineuses, oléagineux, abats),
- ~5 % avec `omega3=True` (poissons gras, graines de lin/chia, noix, huile de colza),
- la quasi-totalité des huiles avec `low_sugar=low_sodium=True`.

Un test paramétré couvre ces ordres de grandeur (`tests/test_nutrition_flags_derivation.py`).

### 2.7 `services/filter_service.py` (l. 274)

`d.get("diet_profile", {})` — pas de changement. ✅

### 2.8 Routes API — substitutions textuelles

| Fichier | Lignes | Avant → Après |
|---------|--------|---------------|
| `api/routes/ingredients.py` | 88-91, 128-130, 143-144 | `name_fr` → `canonical_name_fr` ; `name_en` → `canonical_name_en` |
| `api/routes/nutrition.py`   | 237, 332, 380, 386 | idem |
| `api/routes/nutrition.py`   | 199, 277 | strings codées `"name_fr": "lait d'avoine"` à transformer en clé dynamique tirée du dict |
| `api/routes/frigo.py`       | 137 | `d.get("name_fr", iid)` → `d.get("canonical_name_fr", iid)` |
| `api/routes/planning.py`    | 124 | idem |

Ces 7 fichiers se traitent en `Edit` ciblés, ≤ 15 minutes au total.

### 2.9 `engine/pipeline.py`, `engine/nutrition_engine.py`

- `pipeline.py` ne consomme `ings_d` qu'en le passant aux engines → pas de modification directe (les engines en aval sont déjà couverts).
- `nutrition_engine.py` : référence en docstring (l. 10) — informationnel, à mettre à jour.

### 2.10 `engine/nutrition_engine.py` L. 222 — `ing.get("category", "")` (audit complémentaire)

**Usage** : estimation de quantité par défaut quand la composition d'une recette est absente.
```python
cat = ing.get("category", "") if ing else ""
if cat in ("spice", "spice_mix", "herb", "seasoning"):  qty_g = 5.0
elif cat in ("fat_oil", "fat"):                          qty_g = 15.0
elif cat == "condiment":                                  qty_g = 20.0
else:                                                     qty_g = 100.0
```

**Action** : utiliser le `load_group_to_category()` introduit au § 2.4, qui retourne le `cat_id` racine du dict v2. Mapping testé :

| Ancienne valeur (`category`)               | Nouveau `cat_id` racine    |
|---------------------------------------------|----------------------------|
| `spice`, `spice_mix`, `herb`, `seasoning`   | `herbs_and_spices`         |
| `fat_oil`, `fat`                            | `fats_and_oils`            |
| `condiment`                                 | `condiments_and_sauces`    |

Code patch :
```python
from backend.core.data_io import load_group_to_category
g2c = load_group_to_category()
cat = g2c.get(token, "")
if cat == "herbs_and_spices":          qty_g = 5.0
elif cat == "fats_and_oils":            qty_g = 15.0
elif cat == "condiments_and_sauces":    qty_g = 20.0
else:                                    qty_g = 100.0
```

### 2.11 `engine/planning_engine/shopping.py` L. 80 — regroupement liste de courses (avec décision A.3)

**Usage** : grouper les ingrédients d'une liste de courses par catégorie pour l'affichage UI.
```python
ing_data = get_data.ingredients.get_by_name(item["ingredient"])
cat      = (ing_data or {}).get("category", "autre")
by_cat[cat].append(...)
```

**Action — patch combinant les décisions A.3 + B.1 + D** :

```python
from backend.core.data_io import load_group_to_category, load_ingredients_dict
g2c    = load_group_to_category()
groups = load_ingredients_dict()

raw_cat = g2c.get(item["ingredient"], "autre")
# Décision A.3 : isoler les alternatives végétales en dairy_products_vegan
if raw_cat == "dairy_products":
    entry = groups.get(item["ingredient"], {})
    if entry.get("diet_profile", {}).get("vegan") is True:
        raw_cat = "dairy_products_vegan"
by_cat[raw_cat].append(...)
```

**Libellés FR (décision D)** : matérialisés dans le nouveau fichier `backend/core/i18n/categories_fr.json` :

```json
{
  "fruits":                          "Fruits",
  "vegetables":                      "Légumes",
  "herbs_and_spices":                "Herbes & épices",
  "cereals_and_grains":              "Céréales & grains",
  "legumes":                         "Légumineuses",
  "dairy_products":                  "Produits laitiers",
  "dairy_products_vegan":            "Alternatives végétales",
  "fats_and_oils":                   "Matières grasses & huiles",
  "nuts_and_seeds":                  "Fruits à coque & graines",
  "condiments_and_sauces":           "Condiments & sauces",
  "sugars_honeys_and_confectionery": "Sucres, miels & confiseries",
  "prepared_dishes_and_mixes":       "Plats préparés & mélanges",
  "beverages":                       "Boissons",
  "eggs":                            "Œufs",
  "seaweeds_and_sea_vegetables":     "Algues & légumes marins",
  "leavening_agents_and_additives":  "Levures & additifs",
  "autre":                           "Autre"
}
```

Le rendu côté API peut soit retourner directement les `cat_id` techniques (et laisser le front faire la traduction via ce JSON), soit injecter le libellé FR côté backend. **Recommandation backend : injection au sein de la response du endpoint `/api/planning/shopping-list`** — l'i18n côté backend permet d'avoir un seul point de modification. Charger via :

```python
from backend.core.data_io import load_json
from backend.engine.config import PROJECT_ROOT
_CAT_FR = load_json(PROJECT_ROOT / "backend" / "core" / "i18n" / "categories_fr.json", default={})
```

avec un `_MtimeCache` pour reload sans redémarrage.

**Décision B.1 (acceptée)** : pas de liste blanche supplémentaire. Le tahini, miso, pesto, etc. tombent là où CIQUAL les met. C'est documenté dans la spec API.

### 2.12 Engines confirmés sans couplage au dict v1

Le grep complémentaire (§ 7.3 résolu) a confirmé que les fichiers suivants ne contiennent aucune référence aux champs disparus du dict v1 (`name_fr`, `name_en`, `nutrition_flags`, `allergen_flags`, `category` direct sur item, `synonyms`, `nutrition_key`, `flavor_profile` direct, `substitutions` direct, `aliases` direct) :

- `engine/correction_engine.py`
- `engine/culinary_product_engine.py`
- `engine/culinary_data_quality_engine.py`
- `engine/multi_profile_nutrition_engine.py`
- `engine/cycle_engine.py`
- `engine/graph_engine/core.py`
- `engine/planning_engine/budget.py`, `planner.py`, `servings.py`, `structure.py`
- `engine/reco_engine/learning.py`, `orchestrator.py`, `personalization.py`, `scoring.py`
- `engine/rule_engine/carbon.py`, `diet.py`, `seasonality.py`, `validation.py`, `variants.py`
- `engine/score_engine/ajr.py`, `explainer.py`, `health.py`, `reliability.py`
- `engine/search_engine/core.py`, `similar.py`
- `engine/nutrition_form_engine.py`, `duplicate_recipe_detector.py`, `auth_middleware.py`, `compat.py`

Ces fichiers consomment uniquement les loaders `data_io` qui retournent les nouvelles structures de manière transparente — aucun changement requis.

⚠️ **Note `rule_engine/carbon.py`** : consomme `load_carbon_footprint()` directement. Les clés FR du fichier ont été vérifiées (cf. § 3 — pas de clés FR de surface), mais si une recette appelle ce module avec un id ingrédient FR hérité (`huile_friture`, `lait_coco`), le lookup retournera 0 silencieusement. Couvert par le script de migration des graphes/configs (§ 3.2).

---

## 3. Données auxiliaires (`data/`) — clés FR héritées

### 3.1 Remap canonique FR → EN (verrouillé)

| Ancienne clé              | Nouvelle clé canonique (= `group_id`) | Statut |
|---------------------------|----------------------------------------|--------|
| `pommes_de_terre`         | `potato` (cibler le variant `potato_raw_with_skin` ou `potato_boiled_no_skin` selon contexte) | ✅ |
| `oeuf`                    | `egg` (cibler `whole_egg_raw_raw` par défaut)  | ✅ |
| `oeufs_dur`               | `whole_egg_hard_boiled_hard_boiled` (à vérifier dans le dict — sinon `whole_egg_raw_raw`) | à confirmer côté dict |
| `lait_coco`               | `coconut_milk`                        | ✅ |
| `huile_friture`           | **`sunflower`** (= huile de tournesol dans `fats_and_oils/oils`) — décision § 0.1 | ✅ |
| `huile_de_palme`          | `palm` (dans `fats_and_oils/oils`)    | ✅ |
| `farine_de_manioc`        | `cassava_flour`                       | ✅ |
| `farine_de_pois_chiche`   | `chickpea_flour`                      | ✅ |
| `farine_de_seigle`        | `rye_flour`                           | ✅ |
| `farine_de_teff`          | `teff_flour`                          | ✅ |
| `sauce_soja`              | `soy_sauce`                           | ✅ |
| `haricots_geant`          | `giant_bean` (à confirmer dans le dict) | à confirmer |
| `tofu_soyeux`             | `silken_tofu`                         | ✅ |
| `lait`                    | **`whole_milk_uht_uht_whole`** — décision § 0.2 | ✅ |

### 3.2 Fichiers à patcher

1. `data/graphs/ingredient_relation_graph.json` — 10 clés FR top-level.
2. `data/graphs/ingredient_cost_graph_v1.json` — mêmes 10.
3. `data/graphs/flavor_graph.json` — mêmes 10.
4. `data/graphs/ingredient_substitution_rules_graph_v1.json` — `haricots_geant`, `tofu_soyeux` + revue des valeurs.
5. `data/config/prices.json` — 7 clés FR.
6. `data/graphs/knowledge_graph_unified_v1.json` — audit séparé (591 nœuds non rattachables).

### 3.3 Script de migration recommandé

`scripts/migrate_graph_keys.py` :
1. Charge le remap (table § 3.1) depuis un YAML versionné.
2. Itère sur la liste des fichiers à patcher.
3. Renomme les clés **top-level** et les **références internes** (substitutions, paires, listes).
4. Mode `--dry-run` produisant un diff lisible.
5. Écriture atomique (tempfile + `os.replace`).

---

## 4. Audit `knowledge_graph_unified_v1.json` — RÉSULTATS

**Périmètre réel après filtrage** (voir `AUDIT_KG_UNMATCHED.md` à la racine du projet) :

| Catégorie | Compte | Action |
|-----------|--------|--------|
| Total nœuds KG | 747 | — |
| **Nœuds = IDs de recettes** (entiers, issus de `recipe_nutrition_graph_v1`) | **421** | ✅ **À ignorer** — c'est légitime, ce ne sont pas des ingrédients |
| Nœuds = ingrédients | 326 | — |
| Ingrédients résolus dans dict v2 + alias_index | 151 | ✅ aucune action |
| **Ingrédients NON résolus** | **175** | À traiter (cf. ci-dessous) |

**Décomposition des 175 inconnus :**
- **29 termes FR non accentués** → remap par script (cf. § 3.1, table étendue ci-dessous).
- **1 pluralisation triviale** (`lentil` → `lentils`) → alias.
- **145 termes EN simples à aliaser** (`bamboo_shoot`, `bok_choy`, `chana_dal`, `coconut_oil`, `bell_pepper`, `curry_leaf`, `dark_chocolate`, …) → ajout `alias_index` dans le dict v2.

### 4.1 Extension de `alias_index` du dict v2

Sur les 145 termes EN à aliaser, **validation manuelle requise** pour mapper chacun vers le `group_id` correct. Procédure :
1. Générer un fichier `scripts/alias_proposals.yaml` listant `<term> → <suggested_group_id>` (suggestion automatique par fuzzy-match sur `canonical_name_en`).
2. Revue manuelle / commit.
3. Patcher `ingredients_dictionary_v2.json` (section `alias_index`) avec les paires validées.

Une fois ces 145 aliases ajoutés, l'`alias_index` passe de 257 à ≈ 402 entrées et le KG est entièrement rattaché — ce qui retire la dette pour de bon, plutôt que de migrer 4-5 graphes individuellement.

### 4.2 Élargissement du remap FR § 3.1

L'audit révèle 29 termes FR (au lieu des 13 initiaux). Liste complète à ajouter au YAML de remap :
```
bouillon_dashi_vegetarien   → dashi_broth_vegetarian (à confirmer dans dict)
concentre_de_tomate         → tomato_paste
etoile_de_badiane           → star_anise
fecule_de_tapioca           → tapioca_starch
feuille_laurier             → bay_leaf
feuilles_de_taro            → taro_leaves
feuilles_filo               → filo_pastry
feuilles_nori               → nori_sheets
flocons_d_avoine            → oat_flakes (ou rolled_oats)
gateaux_de_riz              → rice_cake
graines_de_moutarde         → mustard_seed
jus_de_citron_vert          → lime_juice
noix_de_muscade             → nutmeg
nouilles_de_patate_douce    → sweet_potato_noodles
nouilles_ramen              → ramen_noodles
nouilles_reshteh            → reshteh_noodles (à confirmer)
sauce_brune_vegetarienne    → vegetarian_brown_sauce (à confirmer)
sauce_okonomiyaki           → okonomiyaki_sauce
sauce_tomate                → tomato_sauce
+ les 13 entrées de § 3.1
```

Chaque ligne `à confirmer` nécessite une vérification dans le dict v2 avant écriture du YAML final.

---

## 5. Tests et validation

### 5.1 Tests à ajouter

| Fichier de test                       | Vérifie |
|---------------------------------------|---------|
| `tests/test_data_io.py`               | `load_ingredients_dict()` retourne 2 105 entrées avec `canonical_name_fr` présent ; `load_alias_index()` retourne 257 entrées dont 100 % pointent vers un `group_id` existant |
| `tests/test_culinary_repositories.py` | `IngredientRepository.get_by_name("pomme de terre")` → `potato` via alias ; `list_categories()` → 15 entrées ; `get_substitutions("spirulina_dried")` → `["spinach", "kale"]` |
| `tests/test_search_resolver.py`       | `resolve("almond")` → `almonds_whole_raw_whole` ; `resolve("crème de tartre")` → `leavening_agent_cream_of_tartar` |
| `tests/test_routes_ingredients.py`    | `GET /ingredients/{id}` expose `canonical_name_fr` / `canonical_name_en` ; pas de clé `name_fr`/`name_en` résiduelle |
| `tests/test_migration_data_keys.py`   | Aucun fichier sous `data/graphs/` ou `data/config/` ne contient les 13 clés FR de § 3.1 |
| `tests/test_score_quality.py`         | `_d_flavor()` digère `culinary.flavor_profile` (liste) sans crash |

### 5.2 Vérifications manuelles post-déploiement

- `/api/recipes/today` → enrichments (`_why`, `_nutrition`) complets, aucun champ vide.
- `/api/ingredients?diet=vegan` → cardinalité ≈ identique pré/post migration.
- `/api/nutrition/lait%20d'avoine` → résolution OK via `alias_index`.
- `missing_ingredients_report.json` : surveiller 24 h, aucune **nouvelle** entrée FR récurrente.

---

## 6. Ordre d'exécution recommandé (v1.1)

| Étape | Livrable | Durée |
|-------|----------|-------|
| **Pré-0** | Audit KG § 4 (TERMINÉ — `AUDIT_KG_UNMATCHED.md`) | ✅ |
| **Pré-1** | Validation manuelle des 145 termes EN à aliaser → `alias_proposals.yaml` | 1 h (humain) |
| **Pré-2** | Validation manuelle des 19 « à confirmer » du remap FR | 30 min (humain) |
| **Pré-3** | Grep ciblé sur les 7 engines non audités (TERMINÉ — § 2.10/2.11/2.12) | ✅ |
| 1 | Patch `ingredients_dictionary_v2.json` : `alias_index` étendu (+145) | 15 min |
| 2 | `engine/config.py` : pointer `DICT_PATH` vers v2 | 5 min |
| 3 | `core/data_io.py` : loader aplati + `load_alias_index` + `_derive_nutrition_flags` + détection collisions § 7.1 | 1 h 30 |
| 4 | `db/culinary_repositories.py` : `_ingredients_*`, `IngredientRepository.*` | 1 h |
| 5 | `engine/search_engine/resolver.py` : refonte `_synonym_map` | 20 min |
| 6 | `engine/search_token_generator.py` : `canonical_name_*` + `group_to_category` | 30 min |
| 7 | `engine/score_engine/quality.py` : `culinary.flavor_profile` (liste) | 15 min |
| 8 | `services/enrichment_service.py` : `allergens_eu` + appel `_derive_nutrition_flags` | 1 h |
| 9 | `engine/nutrition_engine.py` L. 222 + `engine/planning_engine/shopping.py` L. 80 : `load_group_to_category()` + post-traitement A.3 (vegan) | 1 h |
| 9bis | Création `backend/core/i18n/categories_fr.json` + intégration dans response `/shopping-list` (D) | 30 min |
| 10 | Routes API (7 fichiers) : `name_fr/en` → `canonical_name_*` | 30 min |
| 11 | `scripts/migrate_graph_keys.py` + YAML de remap final | 1 h |
| 12 | Exécution dry-run → revue diff → écriture | 1 h |
| 13 | Tests § 5.1 (6 nouveaux fichiers) + test_shopping_list_categories_fr | 2 h 30 |
| **Total** | | **≈ 12 h 30** (dont 2 h validation humaine) |

Chaque étape est livrable indépendamment. Aucune ne nécessite de coupure de service en déploiement progressif (les anciens champs peuvent rester ignorés silencieusement le temps du recouvrement).

---

## 7. Risques résiduels et points d'attention (mis à jour v1.1)

### 7.1 ⚠️ **Collisions cross-catégorie du dict v2 — 18 cas confirmés**

L'aplatissement naïf `{group_id: entry}` écrase silencieusement les doublons. Les 18 cas relevés :

| `group_id` | Localisations dans l'arbre |
|------------|----------------------------|
| `almond`        | `fats_and_oils/oils` (huile) + `nuts_and_seeds/almonds` (amande) |
| `coconut`       | `fats_and_oils/oils` + `nuts_and_seeds/coconut` |
| `corn`          | `vegetables/corn` + `fats_and_oils/oils` |
| `mustard`       | `condiments_and_sauces/mustards` + `fats_and_oils/oils` |
| `oat`           | `cereals_and_grains/oats` + `fats_and_oils/oils` |
| `onion`         | `herbs_and_spices/onion` + `vegetables/onions` |
| `poppy_seed`    | 3 emplacements |
| `rice_bran`     | `cereals_and_grains/rice` + `fats_and_oils/oils` |
| `sesame`, `soy`, `wheat_germ`, `wheat_flour`, `caraway_seed`, `cumin_seed`, `fennel_seed`, `fenugreek_seed`, `pickles_cucumber`, `prune_cooked_dried` | … |

**Impact direct sur la décision § 0.1 :** le remap `huile_friture → sunflower` est sans ambiguïté côté graphe, mais dans le dict aplati, `sunflower` est unique (n'est pas dans la liste de collisions ci-dessus) donc OK. À l'inverse, `almond`, `coconut`, `sesame`, `soy` (utilisés dans les graphes) sont AMBIGUS — l'aplatissement décidera arbitrairement entre l'huile et la graine.

**Solution recommandée :** dans `data_io.load_ingredients_dict()`, **ne pas écraser silencieusement** :
```python
if gid in flat:
    logger.warning("collision dict v2 : %s déjà placé sous %s, écrasé par %s",
                   gid, flat[gid].get("_path"), f"{cat_id}/{sub_id}")
    # Option : préfixer la clé du second occurrent (gid_oil) ou refuser et lever
entry["_path"] = f"{cat_id}/{sub_id}"
flat[gid] = entry
```
Et **plus solide** : à terme, le pipeline qui génère le dict v2 doit produire des `group_id` désambiguïsés (ex. `sunflower_oil` vs `sunflower_seed`).

### 7.2 ⚠️ Termes ambigus restants

- `huile_friture`, `lait` → décisions § 0.1/0.2 prises.
- 19 termes de la table § 4.2 marqués « à confirmer » dans le dict avant exécution.

### 7.3 Engines non audités — RÉSOLU

Grep complémentaire effectué (cf. § 2.10 à § 2.12). **Résultat** :
- 2 nouveaux couplages identifiés : `nutrition_engine.py` L. 222 et `planning_engine/shopping.py` L. 80 (tous deux sur l'ancien champ `category`).
- 25 autres fichiers confirmés sans couplage au dict v1.
- 1 attention : `rule_engine/carbon.py` consomme `carbon_footprint.json` qui ne contient pas de clés FR de surface, mais peut recevoir des IDs FR hérités en argument — couvert par le script § 3.

### 7.4 Politique de validation `--dry-run` pour les graphes

Le script `migrate_graph_keys.py` doit produire un diff lisible **avant** toute écriture. Aucune écriture ne doit avoir lieu sans revue humaine sur les fichiers de `data/graphs/`.
