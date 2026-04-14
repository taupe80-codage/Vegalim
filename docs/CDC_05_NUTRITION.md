# CDC 05 — Spécifications Nutritionnelles

## Posture nutritionnelle

**Informative** — la plateforme affiche les informations nutritionnelles
complètes et détecte les carences potentielles, mais laisse l'utilisateur
prendre ses propres décisions. Elle ne remplace pas l'avis d'un professionnel
de santé.

> Principe : *"informer sans prescrire"* — l'utilisateur est adulte et
> responsable de ses choix alimentaires.

## Priorités de santé v1

### 1. Carences classiques du végétarisme
Les carences les plus fréquentes chez les végétariens sont adressées en priorité :

| Nutriment | Risque végétarien | Sources végétales clés |
|---|---|---|
| Vitamine B12 | Critique — quasi absente des végétaux | Produits laitiers, œufs, compléments |
| Fer | Élevé — fer non-héminique moins assimilable | Lentilles, épinards, tofu, graines de courge |
| Calcium | Modéré | Produits laitiers, brocoli, amandes, tahini |
| Zinc | Modéré | Légumineuses, graines de courge, noix de cajou |
| Oméga-3 | Modéré — DHA/EPA absents des végétaux | Graines de lin, chanvre, noix |
| Vitamine D | Commun (pas lié au végétarisme) | Exposition solaire, champignons |
| Iode | Modéré | Algues, sel iodé |

**Fonctionnalités associées :**
- Score AJR par recette (`ajr_scoring_engine`)
- Détection déficiences sur un plan repas (`deficiency_detection_engine`)
- Alertes nutritionnelles proactives (`/nutrition/alerts`)
- Recettes correctrices suggérées en cas de carence détectée

### 2. Cycle féminin — nutrition par phase
Adaptation des recommandations aux 4 phases du cycle menstruel :

| Phase | Jours | Priorités nutritionnelles |
|---|---|---|
| Menstruelle | J1–5 | Fer, magnésium, oméga-3, vitamine C |
| Folliculaire | J6–13 | Protéines, vitamines B, fibres |
| Ovulatoire | J14–16 | Antioxydants, vitamine C, zinc |
| Lutéale | J17–28 | Magnésium, vitamine B6, calcium, tryptophane |

**Fonctionnalités associées :**
- Score d'adéquation recette × phase (`cycle_engine`)
- Filtre plan semaine par phase du cycle
- Réorganisation du classement selon le jour renseigné

## Profils santé secondaires (v2+)
*Non prioritaires en v1, infrastructure en place :*
- Diabète / index glycémique (`adaptive_score_engine_v3` profil `diabetic`)
- Sport / haute protéine (profil `athlete`)
- Anémie ferriprive (profil `anemia`)
- Grossesse (profil `pregnancy` dans `multi_profile_nutrition_engine`)

## Scoring nutritionnel

```
score_nutrition =
    macronutriments × 0.30   (calories, protéines, glucides, lipides, fibres)
    micronutriments × 0.50   (fer, calcium, B12, zinc, vitC, magnésium…)
    équilibre       × 0.20   (diversité, rapport macro)

→ Score normalisé /10
```

Source spec complète : `specs/nutrition_scoring_spec.txt`

## Base de données nutritionnelles

- **Source primaire** : CIQUAL 2020 (ANSES France)
- **Compléments** : USDA FoodData Central
- **Couverture** : 302 ingrédients, 100% des recettes du dataset
- **Micronutriments tracés** : calories, protéines, glucides, lipides, fibres,
  sucres, sodium, calcium, fer, magnésium, potassium, vitamine C, B12, zinc, phosphore
- **Formes d'ingrédients** : pris en compte (cru, cuit, séché, fermenté…)
  via `nutrition_form_engine`

## Contraintes réglementaires

- Aucune allégation thérapeutique ou médicale
- Avertissement systématique : *"Ces informations sont indicatives.
  Consultez un professionnel de santé pour tout suivi nutritionnel."*
- Données nutritionnelles sourcées (CIQUAL/USDA) affichées avec leur origine
