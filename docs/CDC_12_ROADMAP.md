# CDC 12 — Roadmap & Jalons

> **Mise à jour 2026-07-30** — Ce document datait de l'établissement initial
> du CDC (mars 2026) et n'avait pas suivi l'avancement réel du projet.
> Statuts ci-dessous vérifiés directement dans le code à cette date. Les
> points marqués « non vérifié » n'ont pas été audités — ne pas les
> supposer faits ou non faits sans re-checker.

## Horizon de lancement : < 3 mois

### Critères de succès v1
1. **1 000 recettes dans le dataset** (actuellement **733** — besoin : +267,
   pas +471 comme initialement estimé)
2. **Stabilité technique** : 0 bug bloquant, < 500ms par recherche,
   100 utilisateurs simultanés supportés — *tests de charge non trouvés
   dans le repo, à faire*

---

## Phase 0 — Consolidation (actuel → J+2 semaines)

**Objectif** : finir le socle technique avant de construire la v1

| Tâche | Priorité | Statut |
|---|---|---|
| Recalibrer les poids du score global (Q15) | Haute | ⚠️ Non vérifié — `backend/engine/score_engine/` existe, recalibration non confirmée |
| Compléter les fiches ingrédients (cooking_behavior) | Haute | 🔄 À faire — 0/1915 ingredient_groups ont ce champ |
| Enrichir les données accessibilité ingrédients France | Haute | 🔄 À faire — 0/1915 ingredient_groups ont ce champ |
| Ajouter champ `preparation_time` aux recettes | Haute | ✅ Couvert autrement — champ `timing` (prep_active_min/prep_passive_min/cook_min/total_min) déjà présent sur toutes les recettes, juste pas sous ce nom exact |
| Recalibrer `global_score_engine` selon nouvelles pondérations | Haute | ⚠️ Non vérifié (doublon de la ligne Q15 ci-dessus) |
| Tests de charge (100 utilisateurs simultanés) | Moyenne | 🔄 À faire — aucun outil (locust/k6/...) trouvé dans le repo |
| Documentation API Swagger complète | Moyenne | ✅ Auto-générée |
| Backups graphs automatisés (graph_versioning) | Basse | ✅ Fait |

---

## Phase 1 — Dataset 1 000 recettes (J+2 → J+5 semaines)

**Objectif** : atteindre le seuil de 1 000 recettes de qualité

**733/1000 recettes actuellement (+267 restantes)** — la répartition
par sous-catégorie ci-dessous date de l'estimation initiale (quand la
base était à 529) et n'a pas été revérifiée poste par poste ; à
recompter avant de s'en servir pour prioriser le travail restant.

| Tâche | Volume cible (estimation initiale, non revérifiée) |
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

**Objectif** : ~~remplacer Streamlit par~~ une vraie interface web React

**Bien plus avancée que le statut initial ne le laissait penser.** Le
frontend React existe déjà (`frontend/src/pages/`, 14 pages), Streamlit a
déjà été laissé derrière. Divergence par rapport à la décision
« recommandée » du CDC (Next.js 14 + shadcn/ui) : stack réellement
utilisée = React + Vite, routing manuel (`Router.jsx`), pas de framework
Next.js. À trancher formellement dans `CDC_00_DECISIONS_OUVERTES.md`
(décision #3) si ce n'est pas déjà acté de facto.

| Page | Priorité | Statut |
|---|---|---|
| Page recherche + résultats | ⭐⭐⭐ | ✅ `HomePage.jsx` (à confirmer que la recherche y est) |
| Fiche recette complète | ⭐⭐⭐ | ✅ `RecipeDetailPage.jsx` |
| Plan semaine | ⭐⭐⭐ | ✅ `PlanningPage.jsx` |
| Liste de courses | ⭐⭐⭐ | ✅ `ShoppingListPage.jsx` |
| Mon frigo | ⭐⭐ | ✅ `FrigoPage.jsx` |
| Profil utilisateur | ⭐⭐ | ✅ `ProfilePage.jsx` |
| Accueil / découverte | ⭐⭐ | ✅ `HomePage.jsx` |
| Fiche ingrédient | ⭐ | 🔄 À faire — aucune page dédiée trouvée |
| *Hors périmètre initial, déjà construites* | — | Favoris, Nutrition, FODMAP, Astro, Cycle, FAQ |

**Stack réelle** : React 19 + Vite (pas Next.js — divergence à trancher, voir ci-dessus)
**API** : FastAPI existant en backend (pas de réécriture)

---

## Phase 3 — Infrastructure & lancement (J+8 → J+12 semaines)

**Objectif** : déploiement production stable, premiers utilisateurs réels

**Plus avancée que prévu côté configuration** : `docker-compose.yml`
définit déjà Caddy (reverse proxy HTTPS Let's Encrypt), PostgreSQL et
Redis ; `backend/db/` a des modèles SQLAlchemy et 2 migrations Alembic ;
`backend/docs/CGU.md` existe. Non vérifié : si un VPS réel tourne
actuellement, CI/CD, monitoring, et si une politique de confidentialité
formelle existe (CGU ≠ politique de confidentialité).

| Tâche | Description | Statut |
|---|---|---|
| Hébergement VPS | Hetzner ou OVH — 4Go RAM, 2 vCPU | ⚠️ Non vérifié |
| PostgreSQL | Comptes utilisateurs, sessions | ✅ Modèles + migrations Alembic en place (`backend/db/`) |
| Redis | Cache API, rate limiting | ✅ Configuré dans `docker-compose.yml` |
| CI/CD | GitHub Actions → déploiement automatique | ⚠️ Non vérifié |
| Monitoring | Uptime, erreurs, performances (Sentry + UptimeRobot) | ⚠️ Non vérifié |
| HTTPS | Let's Encrypt auto | ✅ Caddy configuré dans `docker-compose.yml` |
| RGPD | CGU, politique de confidentialité, cookies | 🔄 Partiel — `CGU.md` existe, politique de confidentialité séparée non trouvée |
| Beta test | 20–50 testeurs recrutés (réseau personnel, communautés végé) | ⚠️ Non vérifiable depuis le code |

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
| Interface web trop longue à développer | Haute | Élevé | *Risque en grande partie résorbé — 14 pages React déjà développées, voir Phase 2* |
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
