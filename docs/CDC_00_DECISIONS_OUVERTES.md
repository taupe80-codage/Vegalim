# Décisions non tranchées — à résoudre avant lancement v1

| # | Décision | Options | Impact | Urgence |
|---|---|---|---|---|
| 1 | **Nom du projet / produit** | À trouver — court, mémorisable, international, `.com` dispo | Identité de marque complète | 🔴 Avant tout |
| 2 | **Priorité : données vs interface** | Option A : finir 1000 recettes PUIS interface — Option B : interface en parallèle | Planning et focus des 3 prochains mois | 🔴 Cette semaine |
| 3 | **Stack frontend** | Next.js 14 (recommandé) vs Vue.js vs autre | Architecture long terme | 🟠 Avant démarrage interface |
| 4 | **Positionnement premium vs accessible** | Produit premium justifié (5–8€/mois) vs produit accessible (2–3€/mois) | Persona cible, acquisition, revenus | 🟠 Avant lancement |
| 5 | **Modèle de pricing exact** | Tarifs mensuels / annuels, différence Premium vs Famille | Page de paiement, Stripe config | 🟡 Avant monétisation |
| 6 | **Données IA → amélioration algo** | Option A (anonymisé agrégé) vs B (consentement) vs C (jamais) | RGPD, CGU, confiance | 🟡 Avant lancement |

## Recommandations

**Décision 2 — Priorité données vs interface (la plus urgente)**
Recommandation : **Option A — données en premier**.
Raison : une belle interface sur 763 recettes créera de la frustration
(manque de diversité, métadonnées incomplètes). 1 000 recettes bien
documentées avant l'interface = meilleure first impression.
Durée estimée : 3–4 semaines à plein temps.

**Décision 3 — Stack frontend**
Recommandation : **Next.js 14 avec App Router + Tailwind + shadcn/ui**.
Raison : standard de l'industrie 2024, documentation excellente,
composants UI prêts à l'emploi, déploiement simplifié (Vercel gratuit
pour le frontend, FastAPI séparé sur VPS).

**Décision 4 — Positionnement**
Recommandation : **accessible** (2–3€/mois).
Raison : les personas Léa (étudiante budget serré) et Thomas
(confirmé mais pas encore fidélisé) sont plus sensibles au prix
que Sophie. Un produit à 2€/mois avec 500 abonnés = 1 000€/mois,
objectif plus réaliste à 6 mois qu'un produit à 8€ avec 125 abonnés.
