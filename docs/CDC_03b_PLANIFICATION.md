# CDC 03b — Plan Repas & Liste de Courses

## Plan repas — structure

### Nombre de repas par jour : flexible

L'utilisateur choisit sa structure selon son mode de vie :

| Mode | Repas | Cas d'usage |
|---|---|---|
| Standard | Déjeuner + Dîner (2/jour) | Défaut — végétarien classique |
| Complet | Petit-déj + Déjeuner + Dîner (3/jour) | Familles, objectif nutrition complet |
| Jeûne intermittent | 1 ou 2 repas dans une fenêtre horaire | **À développer — v2** |
| Collations | +1 ou 2 encas par jour | Sportifs, grossesse |

### Jeûne intermittent (v2)
Protocoles à supporter :
- **16/8** — fenêtre alimentaire 12h–20h (2 repas)
- **5:2** — 5 jours normaux + 2 jours à ~500 kcal
- **OMAD** — un seul repas par jour très complet nutritionnellement

Contraintes spécifiques :
- Les recettes des jours de jeûne doivent maximiser la densité nutritionnelle
- Avertissement : recommander une consultation médicale pour les protocoles stricts
- Le moteur AJR doit recalculer les cibles sur la fenêtre alimentaire réelle

---

## Plan repas — fonctionnement

### Génération du plan
1. L'utilisateur définit : nb de repas/jour, régime, budget, convives, semaine cible
2. `meal_plan_optimizer` génère un plan par recherche locale + backtracking :
   - Équilibre nutritionnel sur 7 jours (cibles AJR hebdomadaires)
   - Diversité garantie : cuisines, techniques, couleurs d'assiette
   - Contraintes budget respectées
   - Ingrédients réutilisés intelligemment entre repas

### Affichage
- Vue calendrier 7 jours avec déjeuner / dîner
- Score de diversité hebdomadaire visible (0–100)
- Bilan nutritionnel de la semaine avec graphique % AJR
- Alerte si carence détectée sur la semaine

### Export & partage
- Export `.ics` — intégration directe dans Google Calendar, Apple Calendar, Outlook
- Impression format tableau (PDF ou impression navigateur)
- Partage par lien (plan en lecture seule) — v2

### Régénération partielle
- Remplacer un repas spécifique sans recalculer tout le plan
- "Je n'aime pas cette recette" → suggestion alternative immédiate

---

## Liste de courses — fonctionnalités

### Fonctionnalités indispensables (v1)

**1. Regroupement par rayon supermarché**
```
🥦 Fruits & légumes frais
🥚 Produits frais (laitages, œufs, tofu)
🌾 Épicerie sèche (céréales, légumineuses, farines)
🫙 Conserves & condiments
🧂 Épices & aromates
🫒 Huiles & matières grasses
🥛 Boissons & laits végétaux
❄️  Surgelés
```

**2. Prix estimé par ingrédient**
- Estimation en euros basée sur `ingredient_price_engine`
- Prix moyen grande surface France
- Total estimé de la liste affiché en haut
- Indication "économique / standard / premium" par ingrédient

**3. Mise en évidence des ingrédients réutilisés**
- Badge "× 3 recettes" sur les ingrédients partagés
- Tri possible : "ingrédients les plus réutilisés en premier"
- Quantité totale consolidée sur la semaine (pas par recette)
- Logique batch cooking visible : "Cuisiner 400g d'oignons pour 4 repas"

**4. Mode courses (cases à cocher)**
- Interface épurée pour usage en magasin (mobile-first)
- Cases à cocher persistantes (session ou compte)
- Ingrédients cochés barrés visuellement
- Progression : "12/18 articles" affiché

### Fonctionnalités v2
- Soustraction automatique du contenu du frigo déclaré
- Estimation calories et coût final réel vs. estimé
- Scan code-barres pour marquer un ingrédient comme "déjà acheté"
- Export vers applications de courses (Bring!, AnyList…)

---

## Cohérence plan ↔ courses ↔ frigo

```
Frigo déclaré
    ↓ soustraction
Plan semaine (7 jours × N repas)
    ↓ consolidation ingrédients
Liste de courses (quantités totales)
    ↓ tri par rayon + prix
Affichage mode courses
    ↓ retour frigo
Frigo mis à jour après courses
```
