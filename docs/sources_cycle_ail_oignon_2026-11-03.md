# Ail et oignon en phase ovulatoire — preuves

Relevé du 2026-11-03 sur `backend/data/modules/female_cycle_nutrition.json`
(`cycle_phases.ovulatory_phase.ingredient_ids` : `onion`, `garlic`).

## 1. Origine dans les données

- Présents depuis le premier commit du dépôt (`0abbe48`, 2026-04-14), **sans source ni
  justification** dans le fichier.
- Absents de la liste rédigée de la même phase (`recommended_foods` : tomate, poivron,
  grenade, baies, graines de courge, noix, légumes crus). La note de phase parle
  d'antioxydants, de vitamine C et de zinc — rien qui désigne l'ail ou l'oignon.
- `ingredient_ids` sert à relier la phase aux recettes (`coverage_in_recipes: 8`) :
  l'ail et l'oignon semblent y avoir été mis pour la couverture, pas pour un bénéfice.

## 2. Effet mesuré dans l'application

| Phase | Recettes recommandées (sur 894 plats) |
|---|---|
| Menstruelle | 379 |
| Folliculaire | 330 |
| **Ovulatoire** | **648** (72 %) |
| Lutéale | 213 |
| Ovulatoire **sans** ail ni oignon | 370 |

L'ail ou l'oignon sont dans 584 plats : leur présence fait recommander presque tout
le catalogue en phase ovulatoire, ce qui vide le filtre de son sens.

## 3. Ce que dit la littérature

| Source | Ce qu'elle établit |
|---|---|
| [García-Montero et al., *Nutrients* 18(7):1063, 2026 — An Overview of the Impact of the Menstrual Cycle on Nutrient Metabolism](https://pmc.ncbi.nlm.nih.gov/articles/PMC13074570/) | Revue intégrative : les données « support 'cycle-aware' but non-dogmatic nutritional strategies » ; « current evidence does not support formal clinical recommendations for cycle-phase-specific protein intake in healthy women » ; pas de « routine phase-specific dosing protocols ». Aucune mention de l'ail, de l'oignon ou des alliacées. |
| [Pfender et al., *Perspectives on Sexual and Reproductive Health* 57(2):127-132, 2025 — Sync or Swim](https://pmc.ncbi.nlm.nih.gov/articles/PMC12204122/) | Sur 100 créateurs TikTok, 54 recommandent un régime « cycle syncing », 4 seulement citent une recherche (sans référence précise) ; « research on the menstrual cycle's impact on exercise and diet is inconsistent ». |
| [Knix — Cycle-syncing nutrition (2022-07-28)](https://knix.com/blogs/knix-blog/cycle-syncing-nutrition) | Origine probable de l'idée : « Foods like allium vegetables — garlic, leaks, onions — can help metabolize estrogen ». Phrase non attribuée, **aucune étude citée**. |
| [Femia — Cycle syncing diet](https://femia.health/health-library/your-cycle/health/cycle-syncing-diet/) | Reconnaît « little solid scientific proof » pour cette pratique. |

Aucune étude relue par des pairs reliant l'ail ou l'oignon à la phase ovulatoire n'a
été trouvée.

## 4. Conflit avec le régime pauvre en FODMAP

| Source | Citation |
|---|---|
| [Monash FODMAP — High and low FODMAP foods](https://www.monashfodmap.com/about-fodmap-and-ibs/high-and-low-fodmap-foods/) | « Vegetables particularly rich in fructans include artichoke, garlic, leek, onion and spring onion » ; ail et oignon dans la liste des légumes riches en FODMAP. |
| [Méta-analyse, PMID 20662786](https://pubmed.ncbi.nlm.nih.gov/20662786/) ; [Houghton et al., *Gut* 2002](https://gut.bmj.com/content/50/4/471) ; [PMC7883586](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7883586/) | Les symptômes du côlon irritable culminent pendant les règles (pas spécifiquement à l'ovulation). |

L'application propose un filtre pauvre en FODMAP : recommander deux des aliments les
plus riches en fructanes, sans bénéfice démontré, va à contre-sens pour ces personnes.

## Conclusion

Aucune preuve ne justifie l'ail et l'oignon en phase ovulatoire ; ils gonflent la
liste jusqu'à 72 % des plats et contredisent le régime pauvre en FODMAP.
Plus largement, la nutrition « par phase » repose sur peu de preuves (revue 2026) :
le module du cycle relève du conseil général, pas de la recommandation clinique.

**Décision (2026-11-03) :** ail et oignon retirés de `ovulatory_phase.ingredient_ids` ; la phase recommande 370 plats.
