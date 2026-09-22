# CDC 11 — Modèle Économique

## Stratégie globale

Deux axes de revenus indépendants :
1. **B2C Freemium** — grand public végétarien
2. **B2B API** — développeurs et entreprises

---

## Axe 1 — B2C Freemium

### Plan Gratuit (toujours disponible)
Accès suffisant pour découvrir et utiliser le produit au quotidien.

| Fonctionnalité | Gratuit |
|---|---|
| Recherche de recettes | ✅ Illimité |
| Fiche recette complète avec nutrition | ✅ |
| Filtres régime / allergie / budget | ✅ |
| Mon frigo | ✅ |
| Plan semaine (générique, sans profil) | ✅ |
| Liste de courses basique | ✅ |
| Variante vegan | ✅ |
| Historique personnel | ❌ |
| Apprentissage des préférences | ❌ |
| Alertes carences personnalisées | ❌ |
| Export calendrier .ics | ❌ |
| Cycle féminin | ❌ |
| Multi-profils | ❌ |

### Plan Premium (abonnement individuel)
Pour l'utilisateur qui veut une expérience pleinement personnalisée.

| Fonctionnalité | Premium |
|---|---|
| Tout le plan gratuit | ✅ |
| Profil persistant + historique | ✅ |
| Apprentissage des préférences | ✅ |
| Alertes carences personnalisées | ✅ |
| Export plan semaine en .ics | ✅ |
| Cycle féminin — plan adapté par phase | ✅ |
| Score de diversité hebdomadaire | ✅ |
| Bilan nutritionnel semaine complet | ✅ |
| Objectifs santé (sportif, diabète, anémie…) | ✅ |

### Plan Famille (abonnement multi-profils)
Pour les foyers avec des régimes différents.

| Fonctionnalité | Famille |
|---|---|
| Tout le plan Premium | ✅ |
| Jusqu'à 5 profils sous un compte | ✅ |
| Plan semaine combiné (profils différents) | ✅ |
| Liste de courses unifiée pour le foyer | ✅ |

### Tarification indicative (à valider)

| Plan | Prix |
|---|---|
| Gratuit | 0 € |
| Premium | ~4–6 € / mois ou ~40–50 € / an |
| Famille | ~8–10 € / mois ou ~70–90 € / an |

---

## Axe 2 — B2B API (produit à part entière)

L'API est un produit indépendant avec sa propre documentation,
ses propres clés d'accès et sa propre grille tarifaire.

### Cas d'usage B2B ciblés
- Applications de nutrition ou de bien-être
- Services de meal planning ou livraison de repas
- Applications de santé féminine (cycle + nutrition)
- Intégrateurs souhaitant un moteur végétarien clé en main

### Plans API

| Plan | Requêtes/mois | Accès |
|---|---|---|
| Découverte (gratuit) | 1 000 req/mois | Routes publiques |
| Starter | 50 000 req/mois | Toutes routes hors cycle + IA |
| Pro | 500 000 req/mois | Accès complet + support |
| Enterprise | Illimité | Accès complet + SLA + données personnalisées |

### Fonctionnalités API différenciantes
- Moteur de recommandation végétarien prêt à l'emploi
- Scoring nutritionnel adaptatif (6+ profils santé)
- 731 recettes mondiales documentées (extensible à 10 000+)
- Détection de carences et recettes correctrices
- Adaptation cycle féminin
- Moteur de substitution (261 ingrédients couverts)

### Authentification API
- Clés API générées par SHA-256 (`core/api_key.py`)
- Rate limiting intégré (100 req/60s par défaut, configurable par plan)
- Validation de requête (`core/security.py`)

---

## Modèle de croissance

```
Phase 1 — Traction (prototype → v1)
  Gratuit uniquement, accumulation d'utilisateurs et de feedback

Phase 2 — Monétisation (v1 stable)
  Activation Premium + Famille
  Objectif : 500 abonnés payants = ~2 000–3 000 €/mois

Phase 3 — B2B (v2)
  Ouverture API publique documentée
  Premier partenariat intégrateur
```

---

## Ce qui est hors périmètre

- Publicité / affiliation (incompatible avec l'expérience sans friction)
- Vente de données utilisateurs (incompatible avec RGPD et valeurs projet)
- Marketplace de recettes payantes par des tiers (complexité modération)

---

## Financement & coûts (Q45-Q46)

### Modèle de financement
**Autofinancé sur fonds propres** — indépendance totale, pas de dilution,
pas de pression externe sur le calendrier ou les fonctionnalités.

Implication : chaque euro dépensé doit être justifié.
Priorité absolue aux outils gratuits ou à faible coût jusqu'au premier revenu.

---

### Budget de lancement estimé

**Coûts fixes mensuels (post-lancement)**

| Poste | Outil recommandé | Coût estimé / mois |
|---|---|---|
| VPS production | Hetzner CX31 (4Go RAM) | ~10 € |
| Nom de domaine | OVH ou Namecheap | ~1 € |
| SSL | Let's Encrypt | Gratuit |
| Monitoring uptime | UptimeRobot | Gratuit |
| Monitoring erreurs | Sentry (plan gratuit) | Gratuit |
| Email transactionnel | Brevo (ex-Sendinblue, 300 emails/jour) | Gratuit |
| Stockage backups | Hetzner Object Storage | ~2 € |
| **Total récurrent minimal** | | **~13 €/mois** |

**Coûts ponctuels (lancement)**

| Poste | Estimation |
|---|---|
| Design UI (si prestataire) | 500–2 000 € ou 0 € (shadcn/ui + Tailwind) |
| Relecture CGU + politique confidentialité | 300–800 € (avocat) ou template adapté |
| Acquisition utilisateurs v1 (Meta/Google Ads) | 200–500 € budget test |
| Outils design (Figma) | Gratuit (plan free suffisant) |
| **Total ponctuel estimé** | **500–3 300 €** |

**Données nutritionnelles**
- CIQUAL (ANSES) : **gratuit et open data** — déjà intégré ✅
- USDA FoodData Central : **gratuit** — déjà intégré ✅
- Pas de licence payante nécessaire pour les sources actuelles

---

### Seuil de rentabilité

```
Coûts fixes mensuels : ~13 €
Coût par abonné (infrastructure) : négligeable jusqu'à ~1 000 abonnés

Seuil de rentabilité opérationnelle :
  → Plan Premium à 5 €/mois : 3 abonnés couvrent les frais fixes
  → Objectif confort : 100 abonnés = 500 €/mois
  → Objectif indépendance : 500 abonnés = 2 500 €/mois
```

### Stratégie d'acquisition v1
Budget publicitaire **limité et ciblé** au lancement :
- Communautés végétariennes FR (Reddit r/vegan, Facebook groupes)
- Partenariats micro-influenceurs végétariens (échange visibilité, pas rémunéré)
- SEO organique (fiches ingrédients + recettes indexées par Google)
- Publicité payante Meta/Google : test 200–500 € pour valider le CAC
  avant de scaler
