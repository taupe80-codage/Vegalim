# CDC 04 — Dataset, Sources & Gouvernance des données

## Origine des recettes

Les recettes sont issues d'une **recherche systématique des plats traditionnels
végétariens du monde entier** — chaque cuisine nationale ou régionale est
explorée pour identifier ses plats végétariens emblématiques (iconiques ou
courants), qui existent indépendamment de toute tendance moderne.

> Principe : priorité aux recettes qui ont une existence culturelle réelle,
> pas aux adaptations végétariennes de plats carnés.

## Volume cible

| Phase | Volume | Horizon |
|---|---|---|
| Actuel (2026-09) | 892 recettes (dont 99 préparations de base ; 820 avant le dédoublonnage de sept. 2026) | Aujourd'hui |
| v1 (lancement) | 1 000 – 2 000 recettes | Court terme |
| v2 (croissance) | 5 000 recettes | Moyen terme |
| Vision long terme | 10 000+ recettes | Long terme |

La qualité prime sur la quantité : chaque recette doit être
**complète, nutritionnellement documentée et culturellement authentique**.

## Régimes alimentaires couverts

| Régime | Description | Statut |
|---|---|---|
| Végétarien (ovo-lacto) | Œufs et/ou produits laitiers autorisés | ✅ Cœur du produit |
| Vegan | Aucun produit animal | ✅ Couvert + variantes auto-générées |
| Vegan avec produits transformés | Fromages végans, laits végétaux, proteines végétales | ✅ À développer |
| Sans gluten | Recettes naturellement ou adaptées sans gluten | ✅ Flag diet_flags |
| Cru / Raw food | Aucune cuisson au-dessus de 42°C | 🔄 À développer |
| Flexitarien | Possibilité poisson rare | ❌ Hors périmètre v1 |

## Structure d'une recette (champs requis)

```
id, title_fr, title_original
instructions          — étapes détaillées
ingredients           — liste des tokens
composition           — {ingredient, quantity, unit, form, role}
nutrition             — calories, protéines, glucides, lipides, fibres + micros
diet_flags            — {vegan, vegetarian, gluten_free, raw, ...}
iconic_status         — {cuisine_origin, iconic_level, confidence}
iconic_score          — 0-100
technique             — méthodes de cuisson
servings              — nombre de portions
recipe_origin         — original | ai_generated | ai_variant | user_modified
```

## Gouvernance & qualité

- **Audit qualité automatique** : `culinary_data_quality_engine` — score 100/100 actuellement
- **Validation nutritionnelle** : couverture CIQUAL 100% (302 ingrédients)
- **Détection doublons** : `duplicate_recipe_detector` (Jaccard + Levenshtein ≥ 0.85)
- **Traçabilité** : champ `recipe_origin` sur chaque recette
- **Versionnage** : backup horodaté des graphs avant toute modification
- **Politique IA** : les recettes générées par IA sont marquées et soumises
  aux mêmes validations que les recettes originales (cf. AI_RECIPE_POLICY.md)

## Sources nutritionnelles

- **CIQUAL 2020** (ANSES) — base principale France
- **USDA FoodData Central** — compléments (spiruline, matcha, graines de chanvre…)
- Pont `ingredient_id → nutrition_key` via `ingredients_dictionary.json`

## Données à enrichir (roadmap)

- [ ] Produits vegan transformés (fromages végans, yaourts soja…)
- [ ] Recettes raw food (enzymes, germination)
- [ ] Index glycémique complet sur toutes les recettes
- [ ] Allergènes réglementaires (14 allergènes EU)

## Métadonnées manquantes — priorités d'enrichissement

### Méthode : semi-automatisée
Estimation algorithmique en premier, validation humaine en second.
Jamais de données inventées — toujours une source ou une méthode traçable.

---

### 1. Temps de préparation ⭐⭐⭐
**Absent sur la majorité des recettes — priorité haute pour le filtre "prêt en X min"**

Estimation algorithmique :
```python
temps_base = nb_étapes_instructions × 3 min
+ somme(temps_par_technique)
    # mijoté : +20 min, four : +30 min, wok : +10 min
    # vapeur : +15 min, cru : 0 min supplémentaire
+ nb_ingrédients_à_préparer × 2 min
→ validation humaine si résultat hors plage [5, 120 min]
```

Champs à ajouter dans le schéma recette :
```json
"prep_time_min": 15,
"cook_time_min": 25,
"total_time_min": 40
```

---

### 2. Niveau de difficulté culinaire ⭐⭐⭐
Estimation depuis les techniques déclarées :

| Niveau | Critères | Score |
|---|---|---|
| Facile | ≤ 2 techniques, ≤ 8 ingrédients, ≤ 30 min | 1 |
| Intermédiaire | 2–4 techniques, 8–12 ingrédients, 30–60 min | 2 |
| Élaboré | > 4 techniques ou fermentation/pâte maison, > 60 min | 3 |

```json
"difficulty": 1  // 1=facile, 2=intermédiaire, 3=élaboré
```

---

### 3. Photos des recettes ⭐⭐
**Impact UX majeur — les recettes sans photo sont moins cliquées**

Options par ordre de préférence :
1. Photos libres de droits (Unsplash, Pexels) — correspondance par titre/cuisine
2. Génération IA (DALL-E, Stable Diffusion) — recettes sans photo trouvable
3. Photos utilisateurs — v2, avec modération

Contrainte : toute photo générée par IA marquée `photo_source: "ai_generated"`
pour transparence (cohérence avec `AI_RECIPE_POLICY.md`)

```json
"photo_url": "https://...",
"photo_source": "unsplash | ai_generated | user"
```

---

### 4. Index glycémique complet ⭐⭐
Actuellement présent sur ~40% des recettes via `glycemic_index` dans le graph.

Méthode de complétion :
- IG calculé depuis la composition (`glycemic_index` par ingrédient × quantité)
- Pondéré par la proportion de glucides de chaque ingrédient
- Source : tables IG de référence (Mendosa, UNSW Sydney)

```json
"glycemic_index": 45,
"glycemic_load": 12  // IG × glucides / 100 — plus représentatif
```

---

### 5. Tags de saison automatisés ⭐⭐
Le moteur de saisonnalité (`seasonality.json`, 57 ingrédients saisonniers)
doit générer automatiquement un tag par recette selon le mois courant :

```json
"seasonal_tag": "de_saison",       // tous les ingrédients de saison
"seasonal_tag": "presque_saison",  // ≥ 70% des ingrédients de saison
"seasonal_tag": "hors_saison"      // < 70%
```

Tag recalculé dynamiquement à chaque requête selon le mois courant.
Pas de stockage statique — calculé à la volée par `seasonality_engine`.

---

### Accessibilité ingrédients en France
*(mentionné dans le scoring Q15 — non classé dans les métadonnées à enrichir)*

Enrichissement du `ingredient_availability_graph_v1.json` :
- Disponibilité GMS (grande surface) : oui/non/saisonnier
- Rayon supermarché : légumes frais / épicerie / rayon bio / surgelés / import
- Source : connaissance terrain + validation communautaire (v2)

---

### Pipeline d'enrichissement semi-automatisé

```
1. Script Python estime les valeurs manquantes (algo par champ)
2. Export CSV des estimations incertaines (hors plage normale)
3. Revue humaine des cas ambigus
4. Import des valeurs validées
5. Log dans auto_corrections_log.json
```

Outils à développer :
- `recipe_metadata_estimator.py` — nouveau module à créer
- Interface de validation légère (Streamlit admin) — pour la revue humaine

---

## Recettes enfant-friendly (Q36)

**Dans le périmètre — tag spécifique + recettes dédiées**

Les familles avec enfants représentent un segment important du Plan Famille.
Les enfants ont des contraintes spécifiques :

| Contrainte | Description |
|---|---|
| Textures | Éviter les textures rebutantes (légumes trop fibreux, textures gluantes) |
| Saveurs | Peu épicé, peu amer, légèrement sucré accepté |
| Présentation | Coloré, formes ludiques, portions adaptées |
| Nutrition | Calcium, fer, zinc essentiels pour la croissance |
| Sécurité | Pas d'allergènes non déclarés, pas de sel excessif |

**Implémentation dans le dataset :**
```json
"diet_flags": {
  "kid_friendly": true,
  "spice_level": 0,      // 0=neutre, 1=légèrement épicé, 2=épicé, 3=très épicé
  "texture": "smooth"    // smooth / tender / crunchy / mixed
}
```

**Filtre dédié dans l'interface :**
- Checkbox "Adapté aux enfants" dans les filtres de recherche
- Badge "👶 Enfant-friendly" sur les fiches recettes
- Plan Famille : possibilité de cocher "un convive est un enfant"
  → recettes filtrées automatiquement sur `kid_friendly: true`

**Volume cible :**
+50 recettes labellisées enfant-friendly dans le dataset v1
(priorité aux recettes colorées, légumineuses douces, pâtes, currys doux)
