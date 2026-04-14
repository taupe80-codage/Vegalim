# CDC 06 — Personnalisation & Profil Utilisateur

## Modèle d'accès

**Compte optionnel** — deux niveaux d'expérience :

| Sans compte | Avec compte |
|---|---|
| Recherche de recettes | Tout ce qui est à gauche |
| Filtres de base (régime, saison) | Profil personnalisé persistant |
| Plan semaine générique | Plan semaine adapté au foyer |
| Infos nutritionnelles | Suivi carences sur la semaine |
| — | Historique et apprentissage des préférences |
| — | Alertes nutritionnelles personnalisées |
| — | Export calendrier (.ics) |

> Aucune fonctionnalité essentielle ne doit être bloquée derrière un compte.
> Le compte est une récompense, pas un prérequis.

## Profil utilisateur v1 — champs obligatoires

### 1. Régime alimentaire
```
vegetarian        → ovo-lacto végétarien (défaut)
vegan             → aucun produit animal
vegan_processed   → avec substituts vegan transformés
gluten_free       → sans gluten
raw               → alimentation crue (< 42°C)
```
Combinaisons possibles : `vegan + gluten_free`, `vegetarian + raw`, etc.

### 2. Allergies & intolérances
Les 14 allergènes réglementaires EU + intolérances courantes :
```
gluten, crustacés, œufs, poissons, arachides, soja,
lait, fruits à coque, céleri, moutarde, sésame,
anhydride sulfureux/sulfites, lupin, mollusques
+ lactose, fructose (intolérances non-allergiques)
```
Toute recette contenant un allergène déclaré est **masquée** ou **marquée**.

### 3. Budget par repas
```
économique     → < 2 € / personne / repas
standard       → 2 – 4 € / personne / repas
confort        → 4 – 8 € / personne / repas
sans limite    → pas de filtre prix
```

### 4. Nombre de convives
```
1 personne
2 personnes
3-4 personnes
5+ personnes / famille
```
→ Les quantités et la liste de courses sont automatiquement ajustées
via `servings_engine`.

## Profil utilisateur v2 — champs optionnels enrichis

| Champ | Utilisation |
|---|---|
| Ingrédients aimés / détestés | Boost / pénalité dans le scoring adaptatif |
| Phase du cycle féminin | `cycle_engine` — recettes adaptées par phase |
| Objectif santé | `adaptive_score_engine_v3` — profil diabetic / athlete / anemia |
| Niveau culinaire | Filtre sur la complexité des techniques |
| Temps de préparation | Filtre durée |
| Cuisines préférées | Boost géographique dans la recommandation |

## Moteur d'apprentissage

Le système apprend des interactions de l'utilisateur connecté :
- Recettes notées, consultées, cuisinées
- Ingrédients récurrents dans les recettes aimées
- Cuisines d'origine préférées
- Décroissance exponentielle (les interactions récentes pèsent plus)

→ `learning_engine.py` : `compute_preference_weights()` + `rank_by_preference()`

## Persistance des données

- Profil : stocké côté serveur lié à l'identifiant utilisateur
- Historique : 500 entrées max (glissant)
- Format : JSON dans `data/history_{user_id}.json`
- RGPD : données supprimables à la demande, aucune transmission à des tiers

## Schéma du profil (structure technique)

```json
{
  "user_id": "string",
  "diet_preferences": ["vegetarian"],
  "allergies": ["gluten", "arachides"],
  "budget_per_meal": "standard",
  "servings": 2,
  "liked_ingredients": [],
  "disliked_ingredients": [],
  "health_goal": null,
  "cycle_phase": null,
  "created_at": "ISO8601",
  "updated_at": "ISO8601"
}
```

---

## Moteur d'apprentissage des préférences (Q37-38)

### Signaux collectés

Trois signaux retenus, par ordre de fiabilité décroissante :

| Signal | Poids | Fiabilité | Stockage |
|---|---|---|---|
| **Note explicite** (1–5 étoiles) | Fort | Haute — intention déclarée | `score` dans historique |
| **Ajout au plan semaine** | Moyen | Haute — action intentionnelle | Entrée historique `planned` |
| **Ingrédients aimés/détestés** | Fort | Haute — déclaration directe | `liked_ingredients` dans profil |

Signaux **non collectés en v1** :
- Temps de lecture (complexité technique, vie privée)
- Recettes cuisinées marquées manuellement (friction trop élevée pour débuter)
- Partage (v2)

### Algorithme d'apprentissage (`learning_engine.py`)

```python
# Décroissance exponentielle : les interactions récentes pèsent plus
poids_interaction(i) = decay^i × score / 10.0
    où decay = 0.9, i = rang depuis le plus récent

# Préférences calculées
preferred_ingredients → top 20 tokens pondérés
preferred_cuisines    → top 5 cuisines pondérées
avg_score             → score moyen de l'historique
diet_preference       → vegan si > 60% des recettes aimées sont vegan
```

### Utilisation des préférences

Les préférences apprises ajustent le score de recommandation :
```
score_personnel =
    score_global × base
    + overlap_ingrédients_favoris × bonus
    + cuisine_préférée × bonus
→ Résultat clampé [0, 10]
```

### Amélioration des algorithmes (Q38 — à décider)

**Position actuelle : non décidé — à trancher avant le lancement v1**

Options :
- **Option A** (conservatrice) : données uniquement personnelles, jamais
  utilisées pour améliorer les modèles communs
- **Option B** (agrégée) : données anonymisées et agrégées pour améliorer
  les pondérations globales du moteur de recommandation
- **Option C** (avec consentement) : opt-in explicite par l'utilisateur

> Recommandation technique : l'Option B est la plus utile pour la qualité
> du produit et la moins risquée RGPD si correctement anonymisée.
> À décider avant la rédaction des CGU.

---

## Moteur d'apprentissage — signaux retenus (Q37)

Trois signaux prioritaires, hiérarchisés par force du signal :

| Signal | Poids | Justification |
|---|---|---|
| **Note 1–5 étoiles** | Fort | Signal explicite, intention claire |
| **Ajout au plan semaine** | Moyen | Signal implicite d'intérêt réel |
| **Ingrédients aimés / détestés** | Fort | Signal déclaratif, fiable |

### Ce qui n'est PAS retenu en v1
- Temps de lecture : trop ambigu (peut signifier confusion, pas intérêt)
- Recettes "cuisinées" : difficile à vérifier, risque de faux positifs
- Partage : fonctionnalité absente en v1

### Fonctionnement du moteur (`learning_engine.py`)

```python
# Décroissance exponentielle — les interactions récentes pèsent plus
weight = (0.9 ** age_en_jours) × note / 10

# Signaux combinés
score_personnel(recette) =
    score_global(recette) × 0.4
    + affinité_ingrédients × 0.35    # overlap ingrédients aimés
    + affinité_cuisine × 0.25        # cuisines préférées détectées
```

### Transparence pour l'utilisateur
- Affichage dans le profil : "Vos cuisines préférées apprises : Indienne (87%), Japonaise (72%)"
- Bouton "Réinitialiser mes préférences" disponible à tout moment
- Les préférences apprises n'impactent que l'ordre des résultats —
  aucune recette n'est masquée définitivement

---

## Amélioration des algorithmes par les données (Q38)

**Position actuelle : non décidé — à trancher avant le lancement**

### Option A — Anonymisé et agrégé uniquement *(recommandation)*
- Les patterns agrégés (recettes les plus cuisinées, ingrédients les plus aimés)
  servent à améliorer les pondérations globales du moteur
- Aucun profil individuel n'est utilisé
- Transparence : mention dans la politique de confidentialité
- Pas de consentement supplémentaire nécessaire (intérêt légitime)

### Option B — Avec consentement explicite
- L'utilisateur choisit activement de contribuer à l'amélioration
- Opt-in visible dans les paramètres de compte
- Avantage : contribution valorisée (badge "Contributeur", accès beta features)

### Option C — Jamais
- Algorithmes améliorés uniquement par le travail interne
- Maximum de confiance utilisateur, zéro risque perçu
- Inconvénient : apprentissage plus lent

> **Décision à prendre avant le lancement v1.**
> La recommandation est l'Option A — elle est standard dans l'industrie,
> ne nécessite pas de consentement supplémentaire si bien documentée,
> et permet d'améliorer le produit sans compromettre la vie privée.
