# CDC 12 — Roadmap & Jalons

## Horizon de lancement : < 3 mois

### Critères de succès v1
1. **1 000 recettes dans le dataset** (actuellement 529 — besoin : +471)
2. **Stabilité technique** : 0 bug bloquant, < 500ms par recherche,
   100 utilisateurs simultanés supportés

---

## Phase 0 — Consolidation (actuel → J+2 semaines)

**Objectif** : finir le socle technique avant de construire la v1

| Tâche | Priorité | Statut |
|---|---|---|
| Recalibrer les poids du score global (Q15) | Haute | 🔄 À faire |
| Compléter les fiches ingrédients (cooking_behavior) | Haute | 🔄 À faire |
| Enrichir les données accessibilité ingrédients France | Haute | 🔄 À faire |
| Ajouter champ `preparation_time` aux recettes | Haute | 🔄 À faire |
| Recalibrer `global_score_engine` selon nouvelles pondérations | Haute | 🔄 À faire |
| Tests de charge (100 utilisateurs simultanés) | Moyenne | 🔄 À faire |
| Documentation API Swagger complète | Moyenne | ✅ Auto-générée |
| Backups graphs automatisés (graph_versioning) | Basse | ✅ Fait |

---

## Phase 1 — Dataset 1 000 recettes (J+2 → J+5 semaines)

**Objectif** : atteindre le seuil de 1 000 recettes de qualité

| Tâche | Volume cible |
|---|---|
| Cuisines sous-représentées (Africaines, Amérique Latine, Asie du Sud-Est) | +150 recettes |
| Recettes sans gluten identifiées et flagguées | +80 recettes |
| Recettes raw food | +30 recettes |
| Recettes avec produits vegan transformés (fromage vegan, lait végétal) | +50 recettes |
| Recettes rapides (< 20 min) — manquantes dans le dataset actuel | +60 recettes |
| Recettes petits-déjeuners végétariens | +40 recettes |
| Variantes vegan auto-générées sur nouvelles recettes | ~60 automatiques |

**Process de validation pour chaque recette :**
```
1. Recherche plat traditionnel végétarien authentique
2. Vérification ingredients accessibles en France
3. Calcul nutritionnel CIQUAL (couverture ≥ 95%)
4. Passage culinary_data_quality_engine (score ≥ 95/100)
5. Détection doublon (similarity < 0.85 vs existants)
6. Attribution iconic_score différencié
```

---

## Phase 2 — Interface web v1 (J+3 → J+8 semaines)

**Objectif** : remplacer Streamlit par une vraie interface web React/Next.js

| Page | Priorité | Complexité |
|---|---|---|
| Page recherche + résultats | ⭐⭐⭐ | Moyenne |
| Fiche recette complète | ⭐⭐⭐ | Haute |
| Plan semaine | ⭐⭐⭐ | Haute |
| Liste de courses | ⭐⭐⭐ | Moyenne |
| Mon frigo | ⭐⭐ | Faible |
| Profil utilisateur | ⭐⭐ | Moyenne |
| Accueil / découverte | ⭐⭐ | Moyenne |
| Fiche ingrédient | ⭐ | Faible |

**Stack** : Next.js 14 (App Router) + Tailwind CSS + shadcn/ui
**API** : FastAPI existant en backend (pas de réécriture)

---

## Phase 3 — Infrastructure & lancement (J+8 → J+12 semaines)

**Objectif** : déploiement production stable, premiers utilisateurs réels

| Tâche | Description |
|---|---|
| Hébergement VPS | Hetzner ou OVH — 4Go RAM, 2 vCPU |
| PostgreSQL | Comptes utilisateurs, sessions |
| Redis | Cache API, rate limiting |
| CI/CD | GitHub Actions → déploiement automatique |
| Monitoring | Uptime, erreurs, performances (Sentry + UptimeRobot) |
| HTTPS | Let's Encrypt auto |
| RGPD | CGU, politique de confidentialité, cookies |
| Beta test | 20–50 testeurs recrutés (réseau personnel, communautés végé) |

---

## Phase 4 — v2 (> 3 mois post-lancement)

Déclenchée après validation de la v1 (feedback utilisateurs + stabilité).

| Fonctionnalité | Condition de déclenchement |
|---|---|
| Abonnements Premium + Famille (Stripe) | 100+ utilisateurs actifs |
| Application mobile React Native | 500+ utilisateurs web actifs |
| API B2B publique documentée | 1 premier partenaire intéressé |
| Jeûne intermittent | Demande utilisateurs confirmée |
| Génération recettes IA | Dataset ≥ 2 000 recettes validées |
| Newsletter recettes de saison | Base emails ≥ 500 inscrits |
| Multilingue (EN) | Traction internationale détectée |

---

## Risques identifiés

| Risque | Probabilité | Impact | Mitigation |
|---|---|---|---|
| Dataset insuffisant en qualité | Moyenne | Élevé | Process validation strict, prioriser qualité |
| Interface web trop longue à développer | Haute | Élevé | Partir de composants shadcn/ui, design simple |
| Performances insuffisantes | Faible | Élevé | Cache Redis, tests de charge Phase 3 |
| Faible adoption initiale | Moyenne | Moyen | Beta test précoce, communautés végé FR |
| Score nutritionnel contesté | Faible | Moyen | Sources CIQUAL affichées, indicateur fiabilité |

---

## Modules IA avancés — priorités réelles (Q43)

Deux modules identifiés comme prioritaires parmi les 102 engines existants :

### 1. Auto-amélioration du système ⭐⭐ (v2)
`culinary_self_improvement_engine.py` — les engines apprennent de leurs erreurs.

**Fonctionnement cible :**
- Détection des recettes systématiquement mal notées par les utilisateurs
  malgré un bon score algorithmique → révision des pondérations
- Détection des substitutions qui échouent (ingrédient non accepté en pratique)
- Feedback loop : `auto_corrections_log.json` → analyse → ajustement des poids

**Condition de déclenchement :** minimum 1 000 interactions utilisateurs
pour que les patterns soient statistiquement significatifs.

### 2. Simulation culinaire complète ⭐ (v2)
`culinary_world_simulation_engine.py` — un seul appel retourne :
coût + carbone + nutrition + compatibilité culturelle + saveurs.

**Cas d'usage :**
- "Si je remplace le beurre par de l'huile de coco dans cette recette,
  que se passe-t-il nutritionnellement, gustativement et en termes de coût ?"
- Outil de décision pour les substitutions complexes

**Condition de déclenchement :** données carbone complètes (Agribalyse)
+ données de prix stabilisées.

### Modules déprioritisés
- Moteur de règles culinaires → infrastructure présente, valeur B2C faible
- Graphe de connaissances → utile B2B/API, pas B2C v1
- Simulateur substitution seul → couvert par `smart_recipe_adaptation_engine`
