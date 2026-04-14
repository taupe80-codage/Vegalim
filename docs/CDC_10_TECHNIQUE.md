# CDC 10 — Architecture Technique

## Stack actuelle (prototype v177)

| Couche | Technologie | Rôle |
|---|---|---|
| API backend | FastAPI (Python) | 101 routes, authentification, rate limiting |
| Interface prototype | Streamlit (Python) | Démo et tests internes |
| Données | Fichiers JSON | Dataset recettes, graphs, index |
| Moteurs | 102 modules Python | Scoring, recherche, nutrition, planification |
| Chiffrement données | Fernet (cryptography) | Protection du dataset réel |

---

## Recommandations d'hébergement

### Pour la v1 (lancement) — recommandation : **VPS simple**

**Pourquoi ?** Contrôle total, coût maîtrisé, simple à gérer, idéal pour
un projet en croissance progressive.

**Prestataires recommandés :**

| Prestataire | Avantage | Prix indicatif |
|---|---|---|
| **Hetzner** (🇩🇪) | Excellent rapport qualité/prix, RGPD EU | ~6–15 €/mois |
| **OVH** (🇫🇷) | Hébergement français, support FR, RGPD | ~7–20 €/mois |
| **DigitalOcean** | Interface simple, documentation excellente | ~12–24 €/mois |

**Configuration recommandée pour 100 utilisateurs simultanés :**
- 4 Go RAM, 2 vCPU, 80 Go SSD
- OS : Ubuntu 22.04 LTS
- Reverse proxy : Nginx
- Process manager : Gunicorn + Uvicorn workers

### Pour la v2 (croissance) — migration vers **PaaS ou Cloud**
- Railway / Render : déploiement simplifié, auto-scaling
- AWS / GCP : si besoin de monter à 10 000+ utilisateurs simultanés

---

## Recommandations base de données

### Pour la v1 — recommandation : **Garder JSON + PostgreSQL pour les comptes**

**Pourquoi deux systèmes ?**

Les **recettes et graphs** (données structurées stables) fonctionnent bien
en JSON avec le cache `lru_cache` déjà en place. Migrer vers une BDD
n'apporte pas de valeur immédiate pour ce type de données.

Les **comptes utilisateurs, historiques et abonnements** nécessitent
une vraie base relationnelle pour la cohérence et la sécurité.

| Données | Solution recommandée | Justification |
|---|---|---|
| Recettes, graphs, index | **JSON + lru_cache** (actuel) | Performant, simple, déjà optimisé |
| Comptes utilisateurs | **PostgreSQL** | Transactions, RGPD, relations |
| Historiques & préférences | **PostgreSQL** | Requêtes complexes, partage famille |
| Sessions & cache API | **Redis** | TTL automatique, rapidité |
| Paiements | **Stripe** (externe) | Ne jamais stocker les données CB en interne |

### Pour la v2 — migration complète vers PostgreSQL
Quand le dataset dépasse 5 000 recettes, migrer les JSON vers PostgreSQL
avec indexes full-text pour les recherches.

---

## Exigences de performance

| Indicateur | Cible v1 |
|---|---|
| Temps de réponse recherche | < 500 ms |
| Temps de réponse fiche recette | < 200 ms |
| Utilisateurs simultanés | 100 minimum |
| Disponibilité | 99.5% (hors maintenance) |
| Temps de génération plan semaine | < 2 secondes |

### Optimisations déjà en place
- `@lru_cache` sur les 6 sources de données statiques (graphs, nutrition_db…)
- Pagination `skip/limit` sur les routes de recherche et classement
- Graphs précalculés (nutrition, scoring) — pas de recalcul à chaque requête
- `DataLoader` singleton — chargement unique au démarrage

### Optimisations à implémenter en v1
- CDN pour les images de recettes (Cloudflare, BunnyCDN)
- Cache Redis pour les requêtes API fréquentes (plan semaine, top recettes)
- Compression Gzip sur les réponses API

---

## Architecture cible v1

```
Internet
    │
    ▼
Cloudflare (CDN + protection DDoS)
    │
    ▼
Nginx (reverse proxy + SSL Let's Encrypt)
    ├── /api/*     → FastAPI (Uvicorn, 4 workers)
    └── /*         → Next.js (interface web)
         │
         ├── PostgreSQL (comptes, historiques, abonnements)
         ├── Redis (cache sessions, rate limiting)
         └── Fichiers JSON (recettes, graphs) ← lru_cache Python
```

---

## Sécurité

| Aspect | Solution |
|---|---|
| HTTPS | Let's Encrypt (certificat gratuit, auto-renouvellement) |
| Authentification API | Clés SHA-256 + rate limiting (100 req/60s) |
| Mots de passe | bcrypt (jamais en clair) |
| Données utilisateurs | Chiffrées au repos (PostgreSQL encryption) |
| Dataset réel | Fernet AES-128 (`secure_loader.py`) |
| RGPD | Droit à l'effacement, export données, consentement explicite |
| Injections | Validation Pydantic sur toutes les entrées API |

---

## Environnements

| Environnement | Usage | `DATA_MODE` |
|---|---|---|
| Développement local | Tests, développement | `fake` (300 recettes synthétiques) |
| Staging | Recette avant production | `secure` (dataset chiffré) |
| Production | Utilisateurs réels | `real` (dataset complet) |

---

## RGPD & Protection des données

### Données collectées et bases légales

| Donnée | Catégorie RGPD | Base légale | Durée de rétention |
|---|---|---|---|
| Profil (régime, allergies, budget) | Données ordinaires | Consentement | Durée du compte |
| Historique recettes | Données ordinaires | Exécution contrat | 2 ans glissants |
| **Données de santé (cycle, objectifs)** | **Données sensibles — Art. 9** | **Consentement explicite renforcé** | Durée du compte |
| Préférences apprises (IA) | Données ordinaires | Intérêt légitime | Durée du compte |
| Données de paiement | Données financières | Exécution contrat | Délégué à Stripe |

> ⚠️ **Alerte réglementaire** : les données de cycle féminin et d'objectifs
> de santé constituent des **données de santé au sens de l'article 9 du RGPD**.
> Elles nécessitent un consentement explicite distinct, séparé du consentement général,
> avec information claire sur l'usage.

### Mesures non-négociables

**1. Hébergement en Europe**
Serveurs exclusivement en UE (Hetzner DE, OVH FR).
Aucun transfert de données hors UE sans garanties adéquates.

**2. Chiffrement des données sensibles**
- Données de santé (cycle, objectifs) : chiffrées au repos (AES-256)
- Mots de passe : bcrypt (jamais en clair, jamais stockés)
- Dataset recettes réel : Fernet AES-128 (`secure_loader.py`)
- Communications : HTTPS TLS 1.3 obligatoire

**3. Droit à l'effacement — bouton "Supprimer mon compte"**
Suppression complète en un clic :
- Profil utilisateur
- Historique de navigation et de consommation
- Préférences apprises
- Données de santé
- Compte et identifiants

Délai d'exécution : immédiat pour les données actives,
30 jours pour les purges de backups.

**4. Zéro cookie tiers / tracking publicitaire**
- Pas de Google Analytics (remplacé par Plausible ou Umami — RGPD natif)
- Pas de pixels Facebook / Meta
- Pas de retargeting publicitaire
- Cookies strictement fonctionnels uniquement (session, préférences)
- Bannière de consentement minimaliste (pas de dark patterns)

### Consentements requis

```
Compte créé → Consentement général (CGU + données profil)
             + Consentement spécifique santé si activation cycle/objectifs santé
             + Consentement analytics (optionnel, refusable)
```

### Registre des traitements (obligatoire RGPD)

À tenir à jour avant lancement :
- Finalité de chaque traitement
- Base légale
- Durée de conservation
- Sous-traitants (Stripe, hébergeur)
- Mesures de sécurité

### Responsable de traitement

Le porteur du projet est responsable de traitement au sens du RGPD.
En cas de lancement commercial, désignation d'un DPO recommandée
à partir de 250 utilisateurs ou dès traitement de données de santé à grande échelle.

---

## RGPD & Confidentialité

### Données collectées

| Catégorie | Données | Sensibilité | Base légale |
|---|---|---|---|
| Profil | Régime, allergies, budget, convives | Standard | Consentement |
| Historique | Recettes consultées et cuisinées | Standard | Consentement |
| Santé | Cycle féminin, objectifs santé | **Sensible (catégorie spéciale RGPD)** | Consentement explicite |
| Comportement | Pages vues, clics, temps passé | Standard | Intérêt légitime / Consentement |
| Paiement | Abonnement (via Stripe — jamais stocké en interne) | — | Exécution contrat |
| IA | Préférences apprises par `learning_engine` | Standard | Consentement |

> ⚠️ Les données de cycle féminin relèvent de l'**article 9 RGPD**
> (données de santé — catégorie spéciale). Consentement explicite séparé
> obligatoire. Chiffrement en base obligatoire.

### Mesures non-négociables

| Mesure | Implémentation |
|---|---|
| **Hébergement EU** | Hetzner DE ou OVH FR — hors US Cloud Act |
| **Pas de tracking publicitaire** | Aucun cookie tiers, aucune régie pub |
| **Chiffrement données sensibles** | Champ cycle/santé chiffrés en base PostgreSQL |
| **Droit à l'effacement** | Bouton "Supprimer mon compte" → suppression complète sous 72h |
| **Consentement explicite** | Opt-in séparé pour : profil, historique, données santé |
| **Audit sécurité** | Avant lancement : revue des routes API, tests injection, headers HTTP |

### Registre des traitements (extrait)

| Traitement | Finalité | Durée conservation |
|---|---|---|
| Profil utilisateur | Personnalisation | Durée du compte + 30 jours |
| Historique recettes | Apprentissage préférences | 500 entrées glissantes |
| Données cycle | Recommandations phase | Durée du compte |
| Logs API | Sécurité / facturation | 90 jours |
| Données paiement | Stripe (externe) | Selon CGU Stripe |

### Ce qui ne sera jamais fait
- Vente ou partage de données à des tiers
- Profilage à des fins publicitaires
- Stockage des données de paiement en interne
- Transfert de données hors UE

---

## Stratégie de test (Q41)

### Tests actuellement en place
- **21 tests automatisés** dans `tests/test_pipeline.py`
  couvrant dataset, nutrition, engines, filtres, substitutions, variantes vegan

### Avant lancement v1 — à compléter

**Tests d'intégration API**
```python
# À créer : tests/test_api.py
# Couvrir les routes critiques :
POST /search/v3            → résultats + scoring
POST /mealplan             → plan complet + nutrition
POST /recommend            → pipeline recommandation
GET  /recipes/{id}         → fiche complète
POST /ajr_score            → calcul AJR
POST /detect_deficiencies  → carences
```

**Tests de performance**
- Outil : `locust` ou `k6` (open source, simple)
- Scénario : 100 utilisateurs simultanés, 5 minutes
- Métriques cibles : < 500ms p95 sur `/search/v3`, < 200ms sur `/recipes/{id}`
- À lancer depuis un VPS séparé pour simuler le trafic réel

**Monitoring production**
| Outil | Usage | Coût |
|---|---|---|
| UptimeRobot | Ping toutes les 5 min, alerte email si down | Gratuit |
| Sentry | Capture des erreurs Python avec stack trace | Gratuit jusqu'à 5k erreurs/mois |
| Grafana / Prometheus | Métriques temps de réponse, CPU, RAM | Gratuit (auto-hébergé) |

---

## Contexte de développement (Q42)

**Projet solo indépendant**

Implications sur les choix techniques et de priorité :

| Contrainte | Conséquence |
|---|---|
| Ressource unique | Prioriser les fonctionnalités à fort impact, éviter la dette technique |
| Pas de revue de code externe | Tests automatisés d'autant plus critiques |
| Charge de maintenance | Préférer les solutions simples et éprouvées (pas de stack exotique) |
| Rythme flexible | Pas de deadline d'équipe, avancement à son rythme |
| Connaissance globale | Pas de silos — une seule personne connaît toute la codebase |

**Recommandations spécifiques au contexte solo :**
- Conserver le `tests/test_pipeline.py` et l'enrichir — c'est le filet de sécurité
- `graph_versioning.py` déjà en place — ne jamais écraser sans backup
- `DATA_MODE=fake` pour tous les développements locaux — protège le dataset réel
- Documenter les décisions techniques dans le CDC au fur et à mesure
- Utiliser des branches Git par fonctionnalité — même seul, facilite les rollbacks
