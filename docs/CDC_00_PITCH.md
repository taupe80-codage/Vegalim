# Résumé Exécutif — Plateforme Culinaire Végétarienne Mondiale

## En une phrase

Une plateforme d'intelligence nutritionnelle végétarienne qui propose
des recettes du monde entier personnalisées selon le profil santé,
le budget et les goûts de l'utilisateur — avec un scoring transparent
et un plan repas nutritionnellement optimisé.

---

## Le problème

Les végétariens manquent d'un outil qui combine trois choses à la fois :

1. **La diversité** — les apps existantes proposent les mêmes 50 recettes
   européennes. Les 40+ cuisines végétariennes mondiales sont ignorées.

2. **La nutrition sérieuse** — manger végétarien mal équilibré génère
   des carences réelles (B12, fer, zinc). Aucune app ne guide vraiment
   l'utilisateur sans devenir un outil médical intimidant.

3. **L'adaptation personnelle** — régime, budget, cycle féminin, nombre
   de convives, saison. Aucun produit ne combine tous ces paramètres
   pour un végétarien.

---

## La solution

Une plateforme qui pense **végétarien en premier** (pas "omnivore avec filtre"),
avec :

- **778 recettes** de 96 cuisines mondiales, authentiques et culturellement
  sourcées — objectif 10 000+
- **Nutrition CIQUAL** complète : micronutriments, AJR, formes d'ingrédients,
  indicateur de fiabilité visible
- **Scoring transparent** : chaque recette notée /10 avec détail par dimension
  (nutrition, authenticité, accessibilité, coût, facilité, carbone)
- **Plan semaine optimisé** : équilibre nutritionnel sur 7 jours, diversité
  des cuisines, export calendrier
- **Adaptation cycle féminin** : fonctionnalité absente de tout concurrent
- **Moteur de substitution** : 261 ingrédients couverts, variantes vegan
  automatiques

---

## Pour qui

**Profil principal :** femmes et hommes 18–40 ans, végétariens ou en transition,
francophones, attentifs à leur santé et à l'environnement.

**Trois personas :**
- Léa, 22 ans, étudiante — budget serré, premiers pas, besoin de simplicité
- Thomas, 34 ans, confirmé — veut diversifier et optimiser sa nutrition
- Sophie, 31 ans — cycle féminin + équilibre nutritionnel, prête à payer

---

## Différenciateurs clés

| Ce que les concurrents ne font pas | Ce que nous faisons |
|---|---|
| Cuisines végétariennes mondiales (40+) | ✅ |
| Nutrition CIQUAL micros + AJR | ✅ |
| Adaptation cycle féminin | ✅ |
| Score transparent et expliqué | ✅ |
| 100% végétarien natif | ✅ |
| Sans publicité | ✅ |

---

## Modèle économique

**Freemium B2C :**
- Gratuit : accès complet aux recettes et recherche
- Premium (~3–5 €/mois) : profil persistant, cycle féminin, alertes carences
- Famille (~7–9 €/mois) : multi-profils, plan semaine combiné

**Stade :** prototype fonctionnel (v177), lancement v1 dans < 3 mois

**Financement :** autofinancé, coûts opérationnels < 15 €/mois

---

## État technique

- **102 engines Python** opérationnels (scoring, nutrition, recherche, planification)
- **101 routes FastAPI** documentées
- **100% couverture nutritionnelle** (CIQUAL/CNF/USDA) sur 778 recettes
- **Tests automatisés** : 21 tests, 0 bug bloquant
- **Stack** : Python/FastAPI (backend) → Next.js/React (frontend à construire)

---

## Les deux prochains chantiers

1. **Dataset → 1 000 recettes** (3–4 semaines)
   Cuisines manquantes, métadonnées, photos, recettes enfant-friendly

2. **Interface web React/Next.js** (6–8 semaines)
   Remplacer Streamlit par un vrai produit utilisable
