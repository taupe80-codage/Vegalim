# Audit de cohérence des 1 000 recettes — 2026-09-25

Revérification complète du dataset (1 000 recettes) à la recherche d'incohérences, toutes
dimensions confondues : nutrition, composition, texte des étapes, temps, régimes, métadonnées,
doublons.

## Comment reproduire

```bash
python scripts/recipes/audit_coherence.py --out docs/audit_coherence_2026-09-25.txt
python scripts/recipes/audit_text_coherence.py --out docs/audit_text_coherence_2026-09-25.txt
```

Les deux rapports détaillés (`.txt`) listent chaque recette concernée. Les corrections
appliquées le sont par `scripts/recipes/fix_coherence_2026_09_25.py` (idempotent).

Contrôles effectués : 30 règles — kcal/portion par type de plat, sodium, part lipidique,
protéines des plats principaux, poids de portion, quantités par ingrédient, doublons de ligne,
quantités nulles ou absentes, unités, recalcul indépendant des régimes (`compute_diet_flags`),
cohérence `diet_flags` ↔ `tags.diet`, somme des temps, cuisson annoncée vs décrite, régime cru
vs cuisson, nombre et numérotation des étapes, longueur des descriptions, titres FR/EN, origine,
portions, texture, technique, `spice_level` vs piment (sous-recettes comprises), `kid_friendly`
vs piment, compositions quasi identiques, titres identiques ou très proches, ingrédient de la
composition jamais cité dans les étapes, quantité citée dans le texte sans ligne correspondante.

## 1. Incohérences corrigées (189)

| Constat | Recettes | Correction |
|---|---|---|
| `tags.diet` contient `kid_friendly` / `raw` alors que le flag vaut False | 103 | tag retiré (le script `fix_recipe_diet_allergens` ne traite que les cinq régimes) |
| Étapes sans la numérotation « Étape N : » du reste du dataset | 38 | renumérotées |
| `spice_level` = 0 avec ≥ 8 g de piment, ou ≥ 3 sans ingrédient piquant | 17 | niveau ajusté (0 pour le *baek* sundubu « doux », 3 pour les enmoladas et la salade grillée tunisienne) |
| `kid_friendly` = True avec ≥ 10 g de piment ou de harissa | 5 | passé à False (ojja ×2, ragoût au berbéré, enmoladas, brik) |
| Titre anglais resté en français | 7 | traduit (crème fraîche, açorda, crème brûlée, tofu sauce ail, ramen miso, soupe thaïe, laksa) |
| `cook_min` = 0 alors que les étapes décrivent une cuisson chiffrée | 6 | temps renseigné (halloumi 20 min, chana chaat 20, pâte à samosa 5, disques de pâte 22, yaourt coco 5, houmous de betterave 2) |
| Unités hors `g`/`ml` (`pinch`, `leaf`) | 4 | converties en grammes |
| Quantité du texte ≠ composition | 3 | texte aligné (tofu frit 100 → 40 ml d'huile, oignon frit 60 → 40 ml, gözleme 5 → 2 g de sel) |
| « Saisir » employé pour « couper » / « piler » | 2 | reformulé (guacamole, papaya salad) |
| Ingrédient de la composition jamais utilisé dans les étapes | 2 | mention ajoutée (vanille du granola, huile d'olive de la soupe à l'oignon) |
| Titre génériques indistinguables | 1 | « Salade de Quinoa » → « Taboulé de quinoa au persil et au citron » (cuisine méditerranéenne) |
| Description commençant en minuscule | 1 | capitalisée |

Après correction : `python -m pytest tests -q` passe (0 échec), graphes, index et
`recipe_list` régénérés.

## 2. Constats qui demandent un arbitrage (non corrigés)

Ce sont des signaux de qualité, pas des erreurs de données : les corriger change des recettes
authentiques ou demande de trancher une convention.

| Constat | Recettes | Remarque |
|---|---|---|
| ~~`tags.technique` vide~~ | ~~269~~ | **traité le 2026-09-26** : vocabulaire normalisé (66 → 18 valeurs) et techniques déduites, plus aucune recette sans technique |
| Portion légère (< 45 % du poids hors eau attendu, avec < 350 kcal) | 182 | beaucoup de plats à base de pain, de soupes mixées et de salades : la règle `PORTION_MIN_G` de `propose_servings` est sans doute trop stricte pour ces familles |
| Plat principal sous 10 g de protéines/portion | 120 | **arbitré le 2026-09-26 : rien changé** — un dataset végétarien comporte des plats principaux légers, le filtrage se fera côté application |
| Plus de 65 % des calories en lipides | 85 → 84 | une seule recette dépassait 25 g de matière grasse par portion (la tapenade, reclassée en condiment) ; les autres sont des plats légers ou des currys au lait de coco |
| `origin.cuisine` = « international » | 69 → 19 | **traité le 2026-09-26** : 50 rattachements ; les 19 restantes (bowls, energy balls, wraps, crackers) n'ont pas d'origine réelle |
| `result.texture` vide | 20 | pâtes de curry, bouillons, préparations de base |
| `origin.country` vide | 13 | préparations de base (« international », « asian », « universal ») |
| Composition quasi identique (≥ 80 % d'ingrédients communs) | 12 | déjà revues : couscous express / traditionnel (92 %), dal tadka / rajma masala, zaalouk / salade d'aubergines, bohémienne / pisto, pâte feuilletée / brisée, onigiri nature / umeboshi… variantes légitimes mais proches |
| Sodium > 1 300 mg/portion | 2 | hot pot (bouillon, 1 434) et banitsa au fromage (1 324) — laissés en l'état, cohérents avec les recettes d'origine |
| ~~Étape de plus de 400 caractères~~ | ~~3~~ | **traité le 2026-09-26** : découpées en deux |

## 3. Faux positifs identifiés (à ne pas re-signaler)

- **Bouillon** : le texte cite le bouillon reconstitué (« 750 ml de bouillon ») là où la
  composition porte la poudre (9,4 g de `vegetable_stock_dried`) — convention du dataset,
  ~80 recettes concernées ; le contrôle de quantité exclut désormais bouillon, eau et sel.
- **Eau de cuisson** : pâtes, gnocchis, bretzels citent des litres d'eau bouillante non
  comptés dans la composition (eau jetée) — volontaire.
- **Deux lignes `water`** dans les deux couscous : 200 ml pour la semoule, 800 ml pour le
  bouillon (rôles et notes différents) — volontaire.
- **Sel des préparations de base** : halloumi (saumure) et doenjang dépassent 2,5 g de sel par
  portion de référence, ce qui est normal pour une base salée.
- **Vocabulaire** : un ingrédient cité sous un autre nom que son libellé (lemongrass /
  citronnelle, moong / mungo, pul biber / piment, daikon / radis, « fromage émietté » pour le
  roquefort, « oignon nouveau » pour l'oignon vert) — 19 des 21 cas restants de `jamais_cite`.
- **Régimes** : le recalcul indépendant par `compute_diet_flags` ne contredit aucun flag
  (0 cas) ; la noix de coco et les laits végétaux ne sont ni des fruits à coque ni du lactose
  dans le dictionnaire.

## 3 bis. Arbitrages rendus (2026-09-26)

Décisions prises sur la section 2, appliquées par
`scripts/recipes/fix_techniques_origins_2026_09_25.py` (idempotent) :

- **Plats principaux pauvres en protéines : rien changé** (décision assumée). Un dataset
  végétarien comporte des plats principaux légers ; le filtrage se fera côté application.
- **`tags.technique` : vocabulaire normalisé puis trous remplis.** Les 66 valeurs hétérogènes
  (`braising`, `braise`, `oven_cooking`, `bake`, `baking`, `fry`, `frying`, `wok`, `sauteed`…)
  sont ramenées à **18 techniques canoniques** : `raw`, `assembly`, `kneading`, `blending`,
  `marinating`, `fermenting`, `chilling`, `boiling`, `simmering`, `steaming`, `sauteing`,
  `deep_frying`, `baking`, `gratinating`, `grilling`, `toasting`, `caramelizing`, `sauce_making`.
  648 recettes normalisées, **269 techniques déduites** des verbes des étapes (trois au maximum
  par recette, la technique de cuisson structurante d'abord) : plus aucune recette sans technique.
  Comme `tags.technique` alimente les `search_tokens`, `backend/engine/search_token_generator.py`
  reçoit une table de synonymes français (`sauteing` → sauté, poêlé, wok ; `gratinating` →
  gratin, gratiné ; `simmering` → mijoté, braisé, ragoût…) pour ne rien perdre côté recherche.
- **Cuisines « international » : 50 rattachements sur 69.** Petits-déjeuners et desserts
  nord-américains (granola, overnight oats, brownie, cheesecake, carrot cake, poke bowl),
  britanniques (porridge, haricots blancs au four), français (tartines, verrines, rillettes de
  lentilles, caviar d'aubergine, soupes et potages), méditerranéens, et les plats identifiables
  (revithia → grec, ribollita → italien, khichdi et rasam → indien, tom yum → thaï, nouilles
  satay → malaisien, thukpa → népalais, manakish → levantin, pico de gallo → mexicain, attiéké →
  ivoirien, soupe de quinoa → péruvien, sautés de tofu → chinois). Les 19 restantes n'ont pas
  d'origine réelle (bowls, energy balls, wraps, crackers, pancakes sans gluten).
- **Tapenade d'olives noires** : passée de `starter` à `condiment` (37,5 g de matière grasse par
  « portion » d'entrée, alors qu'elle se sert à la cuillère).
- **Trois étapes de plus de 400 caractères découpées** : flamiche aux poireaux, ratatouille,
  wok thaï.
- **Sodium du hot pot et de la banitsa : non retenu** — les deux valeurs viennent du bouillon et
  du fromage, elles sont cohérentes avec les recettes d'origine.

## 4. Ce que l'audit confirme

- Aucun identifiant d'ingrédient inconnu, aucune quantité nulle ou négative, aucun rôle
  `serving_suggestion` mal formé.
- Aucune somme de temps incohérente (`total_min` = actif + passif + cuisson partout).
- Aucune recette au régime `raw` avec une cuisson, aucune recette vegan avec un ingrédient
  d'origine animale, aucun titre mal encodé.
- Aucune recette hors des bornes kcal/portion de son type de plat, sauf le pico de gallo
  (31 kcal, c'est une salsa).
