# CDC 03 — Fonctionnalités

## Priorités v1 — classement décisionnel

| Priorité | Fonctionnalité | Statut technique |
|---|---|---|
| ⭐⭐⭐ 1 | **Recherche de recettes** (texte libre, ingrédients, cuisine) | ✅ Opérationnel (search_engine v1/v2/v3) |
| ⭐⭐⭐ 2 | **Infos nutritionnelles détaillées** par recette | ✅ Opérationnel (CIQUAL 100%) |
| ⭐⭐⭐ 3 | **Plan repas 7 jours** personnalisé | ✅ Opérationnel (meal_planner + optimizer) |
| ⭐⭐⭐ 4 | **Liste de courses** générée automatiquement | ✅ Opérationnel (shopping_engine) |
| ⭐⭐ 5 | **Mon frigo** — recettes depuis ce que j'ai à la maison | ✅ Opérationnel (fridge_engine) |
| ⭐⭐ 6 | **Variante vegan** automatique de n'importe quelle recette | ✅ Opérationnel (108 variantes indexées) |
| ⭐ 7 | **Score et classement** des recettes | ✅ Opérationnel (global_score + adaptive_v3) |

## Détail par fonctionnalité

### 1. Recherche de recettes ⭐⭐⭐
Trois modes complémentaires :
- **Texte libre** — fuzzy matching sur titres, ingrédients, cuisine d'origine
- **Par ingrédients** — "qu'est-ce que je peux faire avec des lentilles et des épinards ?"
- **Par cuisine** — filtrer par origine géographique (Indienne, Japonaise, Mexicaine…)
- **Sémantique** — recherche par concept ("soupe réconfortante", "repas rapide protéiné")

Filtres combinables : régime, saison, budget, temps de préparation, technique

### 2. Infos nutritionnelles détaillées ⭐⭐⭐
Par recette et par portion :
- Macronutriments (calories, protéines, glucides, lipides, fibres)
- Micronutriments clés végétariens (B12, fer, calcium, zinc, vitC, magnésium…)
- Score AJR — % des apports journaliers recommandés couverts
- Indicateur de fiabilité du score (reliable / approximate / unreliable)
- Alertes carences si le plan semaine est déséquilibré

### 3. Plan repas 7 jours ⭐⭐⭐
- Génération automatique selon profil (régime, budget, convives, saison)
- Optimisation nutritionnelle sur la semaine (backtracking)
- Diversité garantie : cuisines, techniques, couleurs
- Export en calendrier (.ics) pour intégration agenda
- Score de diversité hebdomadaire

### 4. Liste de courses ⭐⭐⭐
- Générée automatiquement depuis le plan semaine
- Consolidation intelligente des ingrédients communs
- Optimisation budget et réutilisation des ingrédients
- Indication des articles déjà dans le frigo
- Estimation du coût total en euros

### 5. Mon frigo ⭐⭐
- L'utilisateur saisit les ingrédients disponibles
- Le moteur retourne les recettes réalisables immédiatement
- Puis les recettes "presque possibles" (1-2 ingrédients manquants)
- Tri par score de complétude + score nutritionnel

### 6. Variante vegan ⭐⭐
- Pour toute recette végétarienne non-vegan, proposer automatiquement
  une version vegan avec substitutions cohérentes
- Substitutions documentées (beurre → huile de coco, fromage → levure maltée…)
- Score nutritionnel comparé original vs. variante

### 7. Score et classement ⭐
- Score global /10 composite : nutrition (40%), goût/cohérence (30%), prix (20%), iconicité (10%)
- Score adaptatif selon profil utilisateur (diabétique, sportif, budget…)
- Classement dynamique selon contexte (saison, phase du cycle…)

---

## Génération de recettes par IA

**Positionnement : secondaire, conditionnel à la maturité de la base**

- **v1** : hors périmètre — la priorité est la qualité des recettes existantes
- **v2** : activable si la base dépasse 2 000 recettes validées
- **Contraintes** : toute recette IA doit passer les mêmes validations
  que les recettes originales (règles culinaires, nutrition, qualité)
- **Transparence** : champ `recipe_origin: "ai_generated"` obligatoire,
  visible de l'utilisateur
- **Usage** : combler des lacunes géographiques ou diététiques identifiées

---

## Fonctionnalités v2+ (hors périmètre v1)

| Fonctionnalité | Justification report |
|---|---|
| Import de recettes externes (scraping) | Infrastructure présente, à finaliser |
| Astrologie culinaire | Module présent, audience de niche |
| Simulation carbone détaillée | Données à compléter |
| Recommandations by IA conversationnelle | Dépend d'un LLM externe |
| Partage social / communauté | Nécessite modération |

---

## Contenu éditorial

### Fiches ingrédients détaillées (v1)
Une fiche par ingrédient du dictionnaire (302 ingrédients indexés) :

| Section | Contenu |
|---|---|
| Identité | Nom FR / EN, famille botanique, sous-famille, catégorie |
| Profil nutritionnel | Macros + micros pour 100g, forme de référence |
| Bienfaits spécifiques | Points forts nutritionnels (ex : "Excellente source de fer non-héminique") |
| Formes & cuisson | Raw / cuit / séché / fermenté — impact nutritionnel par forme |
| Conservation | Durée, conditions, signes de fraîcheur |
| Saison | Mois de disponibilité optimale en France |
| Substituts | 3–5 alternatives culinaires avec note de compatibilité |
| Recettes associées | Top 5 recettes utilisant cet ingrédient |
| Allergènes | Signalement si allergène EU |

Source technique : `ingredients_dictionary.json` (302 ingrédients)
enrichi par `flavor_profile`, `sub_family`, `cooking_behavior`, `seasonality.json`

### Ce qui n'est pas prévu en v1
- Blog / articles → hors périmètre, charge éditoriale trop lourde
- Vidéos → nécessite infrastructure média
- Newsletter → envisageable v2 (plan semaine de saison automatisé)
- Guides par cuisine → v2 si pertinent

---

## Communauté

**Hors périmètre v1** — la modération est une charge opérationnelle significative.

Fonctionnalités envisageables en v2 :
- Notes et avis sur les recettes (1–5 étoiles + commentaire court)
- Soumission de recettes par les utilisateurs (avec validation éditoriale)
- Partage de plans semaine entre utilisateurs

Contrainte v2 : tout contenu utilisateur doit passer par
`duplicate_recipe_detector` + `culinary_rule_engine` + validation humaine
avant publication.

---

## Module astrologie culinaire (Q31)

**Dans le périmètre — différenciateur original de niche**

Principe : proposer des recettes selon le signe astrologique de l'utilisateur,
les influences planétaires du moment, les affinités élémentaires (feu, terre,
eau, air) et les cycles astrologiques.

Infrastructure déjà présente :
- 9 graphs astrologiques dans `data/culinary_project/modules/astrology/`
- `astro_element_food_graph_v1.json` — correspondances éléments/aliments
- `zodiac_nutrition_affinity_graph_v1.json` — affinités nutritionnelles par signe
- `planet_food_influence_graph_v1.json` — influences planétaires

**Positionnement produit :**
- Module optionnel, activable depuis le profil utilisateur
- Jamais présenté comme scientifique — clairement labellisé "pour le plaisir"
- Différenciateur d'image : crée une conversation, de la curiosité, du partage
- Audience cible : femmes 25–40 ans déjà sensibles à l'astrologie

**Intégration v1 :**
- Section "Votre recette du jour selon les astres" sur l'accueil (optionnelle)
- Filtre "Compatible avec mon signe" dans la recherche (optionnel)
- Aucun impact sur le score nutritionnel — dimension séparée

---

## Impact environnemental CO₂ (Q32)

**Hors périmètre v1 — intégration en v2 quand les données seront meilleures**

Infrastructure déjà présente :
- `data/culinary_project/carbon_footprint.json`
- `sustainability_engine.py` — `recipe_carbon_score()`
- Dimension carbone dans `global_score_engine` (poids 3%)

**Raison du report :**
Les données CO₂ par ingrédient sont actuellement partielles et
peu fiables pour les spécificités végétariennes françaises.
Mieux vaut ne pas afficher un score trompeur.

**Conditions de déclenchement v2 :**
- Base carbone complète sur les 302 ingrédients (source Agribalyse ADEME)
- Prise en compte de la saisonnalité (tomate de saison ≠ tomate importée)
- Validation par une source reconnue (ADEME, Bon pour le Climat...)

**Format d'affichage prévu v2 :**
```
🌱 Impact carbone : 0.8 kg CO₂e / portion   [Faible]
   ██░░░░░░░░  vs. repas omnivore moyen (3.5 kg)
```

---

## Budget — filtre secondaire (Q33)

Le budget est un **filtre combinable parmi d'autres**, pas un axe structurant
du produit. Il doit être présent, visible et fonctionnel sans dominer l'UX.

**Implémentation :**
- 4 niveaux : économique (< 2€) / standard (2–4€) / confort (4–8€) / libre
- Estimation basée sur `ingredient_price_engine` (prix moyens GMS France)
- Affichage systématique du coût estimé sur chaque fiche recette
- Filtre accessible depuis la recherche et la génération de plan semaine
- Profil adaptatif `budget` dans `adaptive_score_engine_v3`

**Limites assumées :**
Les prix varient selon les régions, les magasins et les saisons.
L'estimation est indicative, pas contractuelle. Mention explicite dans l'UI.

---

## Organisation culinaire (Q34)

### Batch cooking ⭐⭐ (v1)
Optimisation de la session cuisine pour préparer plusieurs repas d'un coup.

**Fonctionnement :**
- Dans le plan semaine, détecter les ingrédients partagés entre recettes
- Proposer une organisation : "Cuisinez les lentilles en une fois pour 3 repas"
- Indiquer le temps total de session et les étapes dans l'ordre optimal
- Badge "Batch cooking" sur les recettes adaptées (cuisson divisible)

**Lien avec la liste de courses :**
La liste met en évidence les ingrédients réutilisés (déjà prévu CDC_03b).

### Zéro gaspillage ⭐ (v2)
Recettes utilisant les restes ou les fins de frigo.

**Fonctionnement cible :**
- L'utilisateur indique ce qu'il lui reste (½ chou-fleur, du riz cuit, etc.)
- Recettes "zéro déchet" suggérées
- Lien avec "Mon frigo" — même interface, logique complémentaire

**Différence avec Mon frigo :**
Mon frigo : "j'ai ces ingrédients, que puis-je faire ?"
Zéro gaspillage : "j'ai ces restes (petites quantités), comment les utiliser ?"

Report en v2 car nécessite un enrichissement des données
(quantités minimales par recette).

### Techniques de base ⭐ (v2 — fiches ingrédients)
Intégrées dans les **fiches ingrédients** (déjà prévues CDC_03) :
- Comment cuire les légumineuses (trempage, durées, ratio eau)
- Comment couper les légumes difficiles (courge, chou-fleur, artichaut)
- Techniques de fermentation simples (lacto-fermentation, kimchi)
- Conservation optimale de chaque ingrédient

Format : texte court + infographie simple (pas de vidéo en v1).
Lien depuis la fiche recette vers la fiche ingrédient associée.

---

## Budget

**Rôle : filtre secondaire — un critère parmi d'autres**

- Affiché systématiquement sur chaque recette (coût estimé / portion)
- Disponible comme filtre dans la recherche et le plan semaine
- Pas de fonctionnalité de suivi budgétaire global
- Estimation basée sur `ingredient_price_engine` (prix moyens GMS France)
- Avertissement affiché : *"Prix indicatifs — varient selon magasin et saison"*

---

## Organisation culinaire (v1 partiel, v2 complet)

### Batch cooking ⭐⭐ (v1)
Optimisation du plan semaine pour cuisiner en une seule session :
- Mise en évidence des ingrédients partagés entre plusieurs recettes
- Suggestion d'ordre de préparation (ce qui cuit le plus longtemps en premier)
- Badge "batch cooking" sur les recettes qui se conservent bien
- Liste de courses avec regroupement batch (quantités cumulées)

Infrastructure technique : `ingredient_reuse_optimizer.py` déjà opérationnel.

### Zéro gaspillage ⭐⭐ (v1 — via "Mon frigo")
La fonctionnalité "Mon frigo" couvre déjà ce besoin :
- L'utilisateur saisit ses restes → recettes qui les utilisent
- Recettes triées par "utilise le plus d'ingrédients disponibles"
- À enrichir : filtre explicite "recettes avec restes" sur la recherche

Extension v2 : recettes pensées pour les fins de frigo
(légumes fanés, fond de bocaux, pain rassis).

### Techniques de base expliquées ⭐ (v2)
Fiches techniques courtes accessibles depuis les fiches recettes :
- Lien contextuel : *"Première fois avec des lentilles corail ? → Voir la fiche"*
- Contenu : temps de cuisson, rapport eau/légumineuse, signes de cuisson
- Format texte + illustration (pas de vidéo en v1)
- Couverture initiale : 20 techniques de base végétariennes
  (cuire des légumineuses, préparer du tofu, tailler une courge…)

Lié aux fiches ingrédients (`cooking_behavior` dans `ingredients_dictionary.json`).
