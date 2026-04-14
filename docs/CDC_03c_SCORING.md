# CDC 03c — Scoring & Classement des Recettes

## Philosophie du score

Le score est **transparent et explicable** — l'utilisateur voit toujours
pourquoi une recette est bien notée, pas seulement un chiffre opaque.

> Principe : *"Je comprends pourquoi cette recette est recommandée."*

---

## Score global /10 — pondérations décisionnelles

Classement des dimensions par priorité utilisateur (Q15) :

| Rang | Dimension | Poids actuel | **Poids cible** | Moteur |
|---|---|---|---|---|
| 1 | **Valeur nutritionnelle** | 40% | **40%** | `nutrition_engine` + AJR |
| 2 | **Authenticité culturelle** | 10% | **20%** | `iconic_score` + `iconic_status` |
| 3 | **Accessibilité ingrédients** | — | **15%** | `ingredient_availability_graph` |
| 4 | **Coût total** | 20% | **15%** | `ingredient_price_engine` |
| 5 | **Facilité de préparation** | — | **5%** | complexité technique |
| 6 | **Impact environnemental** | — | **3%** | `sustainability_engine` |
| 7 | **Diversité des saveurs** | 30% | **2%** | `flavor_chemistry_engine` |

> **Note technique** : la formule actuelle (`global_score_engine`) pondère
> goût/cohérence à 30%. À recalibrer selon ces priorités en v1.

### Formule cible

```
score_global =
    nutrition      × 0.40   (AJR, macros, micros, carences végétariennes)
    authenticité   × 0.20   (iconic_score, cuisine d'origine, niveau iconique)
    accessibilité  × 0.15   (ingrédients disponibles en France)
    coût           × 0.15   (prix estimé par portion)
    facilité       × 0.05   (nb étapes, techniques requises)
    carbone        × 0.03   (empreinte CO₂ estimée)
    saveurs        × 0.02   (cohérence profil gustatif)

→ Normalisé /10, arrondi à 1 décimale
```

---

## Score adaptatif — par profil utilisateur

Le score global est **repondéré dynamiquement** selon le profil :

| Profil | Modification |
|---|---|
| `budget` | Coût ×3, nutrition ×0.8 |
| `health_focus` | Nutrition ×2, AJR micronutriments prioritaires |
| `diabetic` | Index glycémique prioritaire, sucres pénalisés |
| `athlete` | Protéines ×2, calories densité |
| `anemia` | Fer ×3, vitamine C (absorption) boostée |
| `eco` | Carbone ×5, saisonnalité boostée |
| `quick` | Facilité ×4, temps de préparation prioritaire |

Moteur : `adaptive_score_engine_v3`

---

## Score expliqué — interface utilisateur

**Toujours visible sur la fiche recette**, sans clic supplémentaire.

### Format d'affichage

```
Score global : 8.4 / 10

├── 🥗 Nutrition        9.2 / 10  ████████████░░  [Riche en fer, B12 présent]
├── 🌍 Authenticité     8.0 / 10  ██████████░░░░  [Plat iconique Inde du Sud]
├── 🛒 Accessibilité    8.5 / 10  ██████████░░░░  [Tous les ingrédients en GMS]
├── 💶 Coût             7.5 / 10  █████████░░░░░  [~2.80 € / personne]
├── 👨‍🍳 Facilité         9.0 / 10  ███████████░░░  [Technique : mijoté simple]
├── 🌱 Carbone          6.0 / 10  ███████░░░░░░░  [Tomates hors saison]
└── 🎨 Saveurs          8.0 / 10  ██████████░░░░  [Umami + épicé + acide]
```

### Indicateur de fiabilité

Affiché sous le score :
- 🟢 **Fiable** — données CIQUAL exactes, couverture 95%+
- 🟡 **Approximatif** — estimation partielle, couverture 60–95%
- 🔴 **Indicatif** — données insuffisantes (< 60% ingrédients couverts)

Moteur : `score_reliability_engine` + `ai_confidence_engine`

---

## Score iconicité culturelle (dimension 2)

Critères de l'`iconic_score` (0–100) :

| Critère | Description |
|---|---|
| Niveau iconique | world_classic (92) → regional_classic (78) → traditional (65) → modern (52) |
| Prestige cuisine | Score de notoriété mondiale de la cuisine d'origine |
| Confiance données | Certitude sur l'authenticité de la recette |

> Exemple : Dal Tadka (Inde) → niveau `regional_classic`, cuisine `Indian` (85),
> confiance 0.9 → `iconic_score` = 74/100

---

## Accessibilité ingrédients en France (dimension 3)

Critères :
- Disponible en grande surface (GMS) toute l'année → score max
- Disponible en épicerie fine / bio → score moyen
- Importation spécialisée requise → score bas
- Ingrédient introuvable en France → pénalité forte

Source : `ingredient_availability_graph_v1.json`
À enrichir avec données de disponibilité réelles.

---

## Affichage condensé (vue liste)

Dans les résultats de recherche, score compact sur une ligne :
```
Dal Tadka   8.4★  🥗9.2  🌍8.0  💶2.80€  ⏱30min  🌱moyen
```
