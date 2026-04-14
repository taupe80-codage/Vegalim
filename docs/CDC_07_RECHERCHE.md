# CDC 07 — Moteurs de Recherche & Recommandation

## Philosophie

La recherche répond à deux besoins distincts traités séparément :
- **Intention explicite** — l'utilisateur cherche quelque chose de précis
- **Découverte** — l'utilisateur veut être surpris et élargir son répertoire

---

## Critères de recherche — priorités

| Priorité | Critère | Moteur technique |
|---|---|---|
| ⭐⭐⭐ 1 | **Texte libre** — "soupe indienne", "recette rapide été" | `search_engine_v3` (fuzzy + sémantique) |
| ⭐⭐⭐ 2 | **Par ingrédients** — "lentilles + épinards" | `search_engine_v2` (normalisation FR→EN) |
| ⭐⭐⭐ 3 | **Profil nutritionnel** — "riche en fer", "faible index glycémique" | `adaptive_score_engine_v3` + filtres AJR |
| ⭐⭐ 4 | **Cuisine d'origine** — Japonaise, Mexicaine, Indienne… | Filtre `iconic_status.cuisine_origin` |
| ⭐⭐ 5 | **Technique** — mijoté, cru, wok, vapeur | Filtre `technique` |
| ⭐ 6 | **Budget** — moins de 2 €/personne | `ingredient_price_engine` + filtre |
| ⭐ 7 | **Temps de préparation** — prêt en 20 min | Filtre durée (à enrichir dans les données) |

Tous les critères sont **combinables** : "curry indien riche en fer, moins de 3€, prêt en 30 min".

---

## Mode 1 — Recherche intentionnelle

### Texte libre (priorité absolue)
Trois niveaux de profondeur selon la requête :

```
Niveau 1 — basic     : matching exact sur titre et ingrédients
Niveau 2 — smart     : fuzzy matching + normalisation FR↔EN
Niveau 3 — advanced  : sémantique TF-IDF + scoring adaptatif intégré
Niveau 4 — deep      : embedding sémantique + recettes similaires
```

L'utilisateur ne choisit pas le niveau — le système sélectionne
automatiquement selon la complexité de la requête.

### Recherche par ingrédients
- Normalisation automatique FR→EN (aubergine = eggplant)
- Synonymes résolus (`ingredient_synonym_resolver`)
- Résultats triés par complétude : "j'ai tous les ingrédients" en premier
- "Presque faisable" : recettes à 1-2 ingrédients près

### Recherche nutritionnelle
- Requêtes naturelles : "riche en fer", "peu calorique", "haute protéine"
- Score AJR comme critère de tri
- Alertes si la requête contredit le régime déclaré

### Filtres combinables
```
régime        → vegan / végétarien / sans gluten / raw
cuisine       → liste des 40+ cuisines du monde indexées
saison        → ingrédients de saison (mois en cours)
budget        → < 2€ / 2-4€ / 4-8€ / sans limite
temps         → < 20 min / 20-45 min / > 45 min
technique     → mijoté / wok / vapeur / cru / four / friture
difficulté    → facile / intermédiaire / élaboré  (à enrichir)
```

---

## Mode 2 — Découverte

Section séparée visuellement des résultats de recherche.

### Contenu de la section Découverte
- **Recette du jour** — sélection éditoriale algorithmique (saison + score + diversité)
- **Cuisine que vous n'avez pas encore explorée** — basé sur l'historique
- **Surprise nutritionnelle** — recette inattendue qui comble une carence détectée
- **Tendance mondiale** — recettes de cuisines sous-représentées dans les habitudes françaises
- **Recettes similaires à vos favoris** — via `recipe_embedding_engine`

### Algorithme de découverte
```
score_découverte =
    score_global × 0.3
    + diversité_vs_historique × 0.3   (cuisines non vues)
    + pertinence_nutritionnelle × 0.2  (comble une carence)
    + saisonnalité × 0.2               (ingrédients de saison)
```

---

## Moteurs techniques impliqués

| Moteur | Rôle |
|---|---|
| `search_engine_v3` | Fuzzy matching + scoring adaptatif intégré |
| `search_engine_v2` | Normalisation FR→EN, filtres combinés |
| `embedding_engine` | Recherche sémantique TF-IDF |
| `search_orchestrator` | Sélection automatique du niveau de profondeur |
| `search_pipeline_connector` | Interface unifiée search + scoring |
| `fridge_engine` | Recettes depuis ingrédients disponibles |
| `recipe_embedding_engine` | Recettes similaires |
| `similarity_engine` | Similarité 5 dimensions entre recettes |
| `adaptive_score_engine_v3` | Tri par profil utilisateur |

---

## Performance cible

- Résultats de recherche texte libre : **< 300 ms**
- Recherche par ingrédients : **< 200 ms**
- Recherche sémantique (embedding) : **< 500 ms**
- Mise en cache des requêtes fréquentes : **< 50 ms** (Redis)
