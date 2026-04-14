# CDC 09 — Interface Utilisateur & UX

## Roadmap interface

| Phase | Interface | Technologie |
|---|---|---|
| Prototype (actuel) | Streamlit | Python / Streamlit |
| v1 — Web | Application web responsive | React / Next.js |
| v2 — Mobile | Application mobile native | React Native ou Flutter |

## Philosophie UX

**Professionnelle et data-driven** — l'interface assume que l'utilisateur
veut comprendre ce qu'il mange. Les scores, graphiques et données nutritionnelles
sont visibles et lisibles, pas cachés derrière des menus.

> Références à viser : Cronometer (densité nutritionnelle), Notion (clarté),
> Yummly (expérience culinaire) — en combinant les trois.

## Style visuel

- **Data-driven** : scores /10 visibles, graphiques AJR, histogrammes nutritionnels
- **Culinaire** : photos de recettes, couleurs chaudes, typographie lisible
- **Épuré** : pas de surcharge, chaque élément a sa raison d'être
- **Palette** : tons verts (végétal), blancs et gris clairs, accents ambrés / ocre
- **Accessibilité** : contraste WCAG AA minimum, tailles de police adaptables

## Pages et écrans v1 (web)

### 🏠 Accueil
- Top recettes du moment (filtrées selon profil)
- Barre de recherche centrale
- Filtres rapides : régime, cuisine, temps, budget
- Alerte carence si plan semaine déséquilibré

### 🔍 Recherche
- Recherche texte libre + par ingrédients + par cuisine
- Résultats avec score visible, temps de préparation, budget estimé
- Filtres latéraux combinables
- Tri : pertinence / score nutritionnel / popularité / budget

### 📋 Fiche recette
- Photo (si disponible)
- Ingrédients avec quantités ajustables (servings_engine)
- Instructions étape par étape
- Tableau nutritionnel complet avec % AJR
- Score global + détail (nutrition / goût / prix / iconicité)
- Indicateur de fiabilité nutritionnelle
- Bouton "Variante vegan" si applicable
- Recettes similaires (3 suggestions)
- Bouton "Ajouter au plan semaine"

### 📅 Plan semaine
- Vue calendrier 7 jours (déjeuner + dîner)
- Score de diversité hebdomadaire (cuisines, techniques)
- Bilan nutritionnel de la semaine avec graphique AJR
- Bouton export .ics
- Génération / régénération en un clic

### 🛒 Liste de courses
- Ingrédients consolidés par catégorie (légumes, féculents, épices…)
- Estimation du coût total
- Cases à cocher (usage en magasin)
- Soustraction des articles déjà dans le frigo

### 🧊 Mon frigo
- Saisie rapide des ingrédients disponibles
- Résultats : "Faisable maintenant" + "Presque faisable"
- Badge sur les ingrédients manquants

### 👤 Mon profil
- Régime alimentaire + allergies
- Budget et nombre de convives
- Historique des recettes cuisinées
- Préférences apprises (ingrédients et cuisines favoris)
- Phase du cycle (optionnel)

### 📊 Nutrition (tableau de bord)
- Bilan nutritionnel de la semaine
- Carences détectées avec recettes correctrices suggérées
- Évolution dans le temps (connecté)

## Interface actuelle — Streamlit

Conservée comme outil de **prototype et démonstration interne**.
Pas destinée aux utilisateurs finaux mais utile pour :
- Valider les algorithmes en conditions réelles
- Démontrer le produit à des partenaires ou investisseurs
- Tests de régression fonctionnelle

Pages Streamlit actuelles : Accueil, Recherche, Mon Frigo,
Plan Semaine, Audit Qualité.

## Application mobile v2

- **Technologie** : React Native ou Flutter (décision en v2)
- **Fonctionnalités prioritaires mobile** :
  - Consultation de recettes (offline partiel)
  - Liste de courses (utilisation en magasin)
  - Mon frigo (saisie rapide)
  - Notifications : rappels plan repas, alertes carences
- **Spécifique mobile** : scan de code-barres pour identifier les ingrédients

## Internationalisation de l'interface

- v1 : Français uniquement
- v2 : i18n complet via fichiers de traduction (FR, EN, ES, DE)
- Les données (recettes, ingrédients) sont bilingues FR/EN dès maintenant
  (`title_fr` + `title_original` dans chaque recette)

---

## Accessibilité

### v1 — Standard minimum
Pas de contrainte d'accessibilité spécifique imposée en v1.
Application des bonnes pratiques de base sans surcharge :
- Contrastes WCAG AA (automatique avec Tailwind bien configuré)
- Textes alternatifs sur les images
- Navigation clavier fonctionnelle

### v2 — Accessibilité complète si la base utilisateurs l'indique
WCAG 2.1 AA complet, tests avec lecteurs d'écran, si l'analyse
des utilisateurs révèle un besoin.

---

## Communication & notifications (Q39)

**Posture : pull uniquement — l'utilisateur revient quand il veut**

Pas d'emails marketing, pas de push agressifs.
La valeur du produit doit suffire à faire revenir l'utilisateur.

**Ce qui est autorisé (transactionnel uniquement) :**
- Confirmation d'inscription / de paiement
- Lien de réinitialisation de mot de passe
- Reçu d'abonnement

**Ce qui est exclu :**
- Newsletter (même optionnelle en v1)
- Notifications push "Tu n'as pas cuisiné depuis 3 jours"
- Emails de relance ou de reengagement

> Cohérent avec l'absence de publicité et le positionnement
> respectueux des données utilisateurs.
> En v2, une newsletter 100% opt-in sur les recettes de saison
> pourra être envisagée si les utilisateurs la demandent.

---

## Identité de marque (Q40)

**Statut : à construire entièrement**

Aucun nom, domaine, logo ni charte graphique définis à ce stade.

**Éléments à définir avant le lancement v1 :**

| Élément | Contraintes | Priorité |
|---|---|---|
| Nom du produit | Court, mémorisable, international, `.com` ou `.fr` disponible | ⭐⭐⭐ |
| Nom de domaine | Cohérent avec le nom, disponible EN et FR | ⭐⭐⭐ |
| Logo | Vectoriel, lisible en petit (favicon), évoque végétal + intelligence | ⭐⭐ |
| Palette de couleurs | Verts végétaux + tons chauds, accessibilité WCAG | ⭐⭐ |
| Typographie | Lisible, moderne, disponible en variable font | ⭐ |

**Pistes de positionnement nom :**
- Axe nature + intelligence : *Verdis, Floora, Herbio, Nutriveg…*
- Axe mondial + végétal : *Verdana, Terraplate, Greenfork…*
- Axe simple + mémorisable : *Vegly, Planeat, Herbly…*

> Recommandation : choisir le nom en priorité — tout le reste (domaine,
> logo, charte) s'aligne ensuite. Tester la disponibilité sur Namecheckr
> et vérifier l'absence de marque déposée (INPI).
