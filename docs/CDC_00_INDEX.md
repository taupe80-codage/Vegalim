# Cahier des Charges — Plateforme Culinaire Végétarienne Mondiale
## Index — 50 questions, 12 sections, documents complets

*Établi par entretien structuré en 50 questions — mars 2026*

---

## Documents de synthèse

| Fichier | Contenu | Statut |
|---|---|---|
| `CDC_00_PITCH.md` | Résumé exécutif — pitch du projet (1 page) | ✅ |
| `CDC_00_DECISIONS_OUVERTES.md` | 6 décisions importantes non tranchées | ✅ |

## Sections du cahier des charges

| Fichier | Section | Questions | Statut |
|---|---|---|---|
| `CDC_01_VISION.md` | Vision, positionnement, différenciateurs, vision 5 ans | Q1–Q3, Q21–Q22, Q44, Q48 | ✅ |
| `CDC_02_UTILISATEURS.md` | 3 personas, profils, comportements | Q23–Q24 | ✅ |
| `CDC_03_FONCTIONNALITES.md` | Fonctionnalités v1/v2, IA, astrologie, CO₂, éditorial, communauté, budget, organisation | Q7–Q8, Q17–Q18, Q31–Q34 | ✅ |
| `CDC_03b_PLANIFICATION.md` | Plan repas, liste de courses, batch cooking, zéro gaspillage | Q13–Q14 | ✅ |
| `CDC_03c_SCORING.md` | Formule score, pondérations, score adaptatif, transparence | Q15–Q16 | ✅ |
| `CDC_04_DONNEES.md` | Dataset, sources, régimes, métadonnées manquantes, recettes enfants | Q4–Q5, Q27–Q28, Q36 | ✅ |
| `CDC_05_NUTRITION.md` | CIQUAL, AJR, carences végétariennes, cycle féminin | Q5–Q6 | ✅ |
| `CDC_06_PERSONNALISATION.md` | Profil v1/v2, compte optionnel, apprentissage, signaux | Q6, Q37–Q38 | ✅ |
| `CDC_07_RECHERCHE.md` | Critères de recherche, découverte, moteurs techniques | Q11–Q12 | ✅ |
| `CDC_08_API.md` | API B2B, fonctionnalités, auth, intégrations | Q19–Q20 | ✅ |
| `CDC_09_INTERFACE.md` | Web/mobile, Next.js, style, pages, marque, communication | Q8–Q9, Q39–Q40 | ✅ |
| `CDC_10_TECHNIQUE.md` | Architecture, hébergement, BDD, perf, RGPD, tests, contexte solo | Q10, Q29–Q30, Q41–Q42 | ✅ |
| `CDC_11_MODELE_ECONOMIQUE.md` | Freemium, plans, API, financement, budget | Q9, Q45–Q46 | ✅ |
| `CDC_12_ROADMAP.md` | 4 phases, jalons, risques, modules IA prioritaires | Q25–Q26, Q43 | ✅ |

---

## Bilan des 50 questions

### Décisions tranchées (44/50)
- Vision et positionnement ✅
- Utilisateurs cibles et personas ✅
- Fonctionnalités v1 classées par priorité ✅
- Données, sources, gouvernance ✅
- Nutrition — posture informative, carences + cycle ✅
- Personnalisation — compte optionnel, profil v1 ✅
- Recherche — 7 critères classés, découverte séparée ✅
- API — 3 fonctionnalités B2B prioritaires ✅
- Interface — web d'abord, Next.js, data-driven ✅
- Hébergement — VPS EU recommandé ✅
- Base de données — JSON + PostgreSQL recommandé ✅
- Modèle économique — Freemium B2C + API B2B ✅
- Roadmap — < 3 mois, 1 000 recettes + interface ✅
- RGPD — hébergement EU, pas de tracking, effacement ✅
- Astrologie — dans le périmètre, optionnel ✅
- CO₂ — v2, données insuffisantes v1 ✅
- Budget — filtre secondaire ✅
- Batch cooking + zéro gaspillage ✅
- Accessibilité — standard minimum v1 ✅
- Recettes enfants — tag + 50 recettes dédiées ✅
- Apprentissage — 3 signaux (notes, plan, déclaratif) ✅
- Financement — autofinancé, < 15€/mois ✅
- Vision 5 ans — B2C rentable ✅
- Modules IA prioritaires — auto-amélioration + simulation ✅
- Communication — pull uniquement, pas d'emails marketing ✅

### Décisions non tranchées (6/50) → `CDC_00_DECISIONS_OUVERTES.md`
1. Nom du produit
2. Priorité données vs interface
3. Stack frontend exacte
4. Positionnement premium vs accessible
5. Pricing exact
6. Usage données pour amélioration algorithmique
