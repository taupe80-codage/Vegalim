# CDC 01 — Vision & Positionnement

## Phrase de présentation

Plateforme culinaire végétarienne mondiale qui propose des recettes personnalisées
selon le profil de l'utilisateur (santé, budget, goûts, cycle, saison) et qui
s'adapte intelligemment à ses préférences au fil du temps.

> En une phrase grand public : **une app qui propose des recettes végétariennes
> du monde entier personnalisées selon mon profil, et un assistant culinaire
> qui s'adapte à ma santé, mon budget et mes goûts.**

## Positionnement

- Plateforme d'**intelligence nutritionnelle végétarienne**
- Moteur de recommandation **adaptatif** (pas une simple base de recettes)
- Accent sur la **diversité mondiale** des cuisines végétariennes
- **Nutrition-first** : chaque recette est évaluée scientifiquement

## Stade actuel

**Prototype personnel / laboratoire technique**

- 936 recettes végétariennes indexées (dont 99 préparations de base)
- 102 moteurs Python opérationnels
- 101 routes API FastAPI
- Interface Streamlit fonctionnelle
- Base nutritionnelle CIQUAL/USDA couvrant 100% des ingrédients

## Utilisateurs cibles

### Cible principale — Consommateurs végétariens & flexitariens (B2C)
- Personnes végétariennes ou en transition
- Flexitariens cherchant à réduire leur consommation de viande
- Personnes avec contraintes santé (diabète, anémie, cycle féminin…)
- Familles souhaitant diversifier leur alimentation végétarienne

### Cible secondaire — Développeurs & entreprises (B2B via API)
- Développeurs souhaitant intégrer un moteur de recommandation végétarien
- Applications de nutrition, de santé, de livraison de repas
- Services de meal planning professionnel

## Questions restantes (Q 4–50)
*À compléter au fil de l'entretien*

## Motivation fondatrice

Trois piliers indissociables :

1. **Éthique & environnement** — conviction personnelle que le végétarisme est
   une réponse concrète aux enjeux environnementaux et au bien-être animal.

2. **Santé & nutrition** — le végétarisme mal pratiqué génère des carences
   réelles (B12, fer, calcium, zinc, oméga-3). La plateforme existe pour
   combler ces lacunes intelligemment, sans que l'utilisateur ait à devenir
   nutritionniste.

3. **Opportunité de marché** — segment en forte croissance mondiale.
   Le végétarisme et le flexitarisme représentent une tendance de fond,
   pas un effet de mode.

## Ancrage personnel

Le projet est porté par un végétarien convaincu — ce qui garantit
l'authenticité des choix fonctionnels et l'adéquation avec les vrais besoins
du quotidien végétarien.

## Géographie & internationalisation

### Déploiement par phases
- **Phase 1 (v1)** — France + pays francophones (Belgique, Suisse, Canada)
- **Phase 2 (v2)** — International, toutes langues

### Langues
- **v1** : Français uniquement (interface + données)
- **v2** : Multilingue complet (FR, EN, ES, DE, …) dès stabilisation

### Cuisine mondiale — axe fondamental
Les recettes couvrent **l'intégralité des cuisines du monde** sans restriction
géographique. C'est un différenciateur fort : l'utilisateur français accède
au Dal Tadka, au Pad Thaï, au Mole, à l'Ajapsandali… tous végétariens,
tous sourcés dans leurs traditions culinaires d'origine.

> Principe : les ingrédients doivent rester **accessibles en France**
> même pour les recettes du monde entier.

## Différenciateurs concurrentiels

### Positionnement : aucun concurrent direct identifié

Le projet occupe une intersection de fonctionnalités qu'aucun produit existant
ne couvre simultanément :

| Fonctionnalité | Marmiton/750g | Yummly | Cronometer | MyFitnessPal | **Ce projet** |
|---|---|---|---|---|---|
| Recettes végétariennes uniquement | ❌ | ❌ | ❌ | ❌ | ✅ |
| Cuisines mondiales (40+) | Partiel | Partiel | ❌ | ❌ | ✅ |
| Profondeur nutritionnelle CIQUAL | ❌ | ❌ | ✅ | Partiel | ✅ |
| Détection carences végétariennes | ❌ | ❌ | Partiel | ❌ | ✅ |
| Adaptation cycle féminin | ❌ | ❌ | ❌ | ❌ | ✅ |
| Score transparent & expliqué | ❌ | ❌ | Partiel | ❌ | ✅ |
| Moteur de substitution | ❌ | Partiel | ❌ | ❌ | ✅ |
| Sans publicité | ❌ | ❌ | ❌ | ❌ | ✅ |
| API ouverte B2B | ❌ | ❌ | ❌ | ❌ | ✅ |

### Les 5 différenciateurs fondamentaux

**1. Diversité mondiale des cuisines végétariennes**
Les 40+ cuisines du monde, chacune avec ses plats végétariens emblématiques
authentiques — pas des adaptations de plats carnés. Dal Tadka, Pad Thaï vegan,
Ajapsandali géorgien, Mole mexicain… Un répertoire culinaire que personne
n'a constitué de cette façon.

**2. Profondeur nutritionnelle scientifique**
Base CIQUAL/USDA intégrale, micronutriments critiques végétariens, résolution
par forme d'ingrédient (cru vs cuit vs fermenté). Niveau de précision équivalent
à Cronometer, mais appliqué aux recettes complètes plutôt qu'aux aliments isolés.

**3. Adaptation au cycle féminin**
Fonctionnalité absente de tout concurrent identifié. Les besoins nutritionnels
varient significativement selon la phase du cycle — ce module répond à un besoin
réel et non adressé des végétariennes (majoritaires dans la population végétarienne).

**4. Score transparent et expliqué**
Chaque note est décomposée par dimension visible. L'utilisateur comprend
*pourquoi* une recette est recommandée, pas seulement *qu'elle l'est*.
Crée de la confiance et de l'éducation nutritionnelle.

**5. Focus 100% végétarien natif**
Pas une app généraliste avec un filtre "sans viande". Le végétarisme est le
point de départ, pas une option. Toute la logique de scoring, de substitution
et de détection de carences est construite pour le végétarisme.

## Vision à 5 ans

**Une app grand public rentable (B2C)**

Pas de dépendance à des clients B2B, pas d'exit forcé, pas de dérive
open source. Un produit végétarien de référence en France et en Europe,
qui génère des revenus suffisants pour être maintenu et développé
indépendamment.

### Indicateurs de succès à 5 ans
- 50 000+ utilisateurs actifs mensuels
- 5 000+ abonnés payants (Premium + Famille)
- Dataset 10 000+ recettes, 50+ cuisines
- App mobile disponible (iOS + Android)
- Référence numéro 1 en France pour la nutrition végétarienne

### Ce que le projet n'est PAS destiné à devenir
- Une plateforme B2B pure (l'API est un revenu secondaire, pas le cœur)
- Un projet vendu ou racheté sauf opportunité exceptionnelle
- Un réseau social culinaire (la modération communautaire est hors ambition)
- Un agrégateur de recettes généraliste avec filtre végétarien

## Diagnostic actuel — deux chantiers prioritaires (Q48)

### 1. Les données — vrai point bloquant
936 recettes ne suffisent pas pour un lancement crédible.
L'objectif de 1 000 recettes (Phase 1 de la roadmap) est non-négociable
avant d'ouvrir au public.

Points de friction identifiés :
- Métadonnées manquantes (temps de préparation, difficulté, photos)
- Couverture des cuisines africaines, Amérique Latine, Asie du Sud-Est insuffisante
- Recettes enfant-friendly, raw food et produits vegan transformés absentes

### 2. L'interface utilisateur — vrai chantier
La technique backend est solide (102 engines, 101 routes, 936 recettes,
nutrition CIQUAL 100%). Streamlit est un outil de prototype, pas un produit.

La migration vers React / Next.js est le chantier structurant de la v1 —
c'est ce qui transforme un laboratoire technique en produit utilisable.

### Fonctionnalités techniques à mettre en avant dans l'UI (Q47)

Deux fonctionnalités différenciantes à rendre immédiatement visibles :

**1. Plan semaine avec optimisation nutritionnelle sur 7 jours**
Le `meal_plan_optimizer` avec backtracking est techniquement avancé.
L'interface doit le valoriser : bilan nutritionnel hebdomadaire visible,
score de diversité, export calendrier.

**2. Adaptation multi-profil (vegan + sport + diabète)**
L'`adaptive_score_engine_v3` avec 6+ profils combinables est un vrai
différenciateur. L'UI doit permettre de le sélectionner facilement
et de voir en temps réel l'impact sur le classement des recettes.
