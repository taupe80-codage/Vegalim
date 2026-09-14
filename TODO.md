# TODO — pistes à traiter plus tard

Fichier de suivi technique local (hors CDC produit dans `docs/`). Une
entrée par piste identifiée mais volontairement non lancée dans l'immédiat
— contexte suffisant pour reprendre sans avoir à tout reconstruire.

## Prix des ingrédients — sources de données réelles

**Piste : programmes d'affiliation des grandes surfaces (Carrefour, Amazon...)**

Alternative à Open Food Facts / Open Prices (base crowdsourcée, sparse sur
~110 ingrédients du catalogue — voir `scripts/ingredient_price_map_review.md`
et l'historique de `backend/data/config/prices_catalog.json`).

- Carrefour, Auchan et d'autres ont des programmes d'affiliation (souvent
  via des réseaux comme Awin ou Affilae) qui donnent accès à un **flux
  produit** (CSV/XML) avec prix — plus légitime que du scraping, puisque
  c'est l'usage prévu de ces flux.
- **Amazon Associates** a une vraie API (Product Advertising API) avec prix
  en temps réel, et vend aussi de l'épicerie/produits secs.
- Frictions à évaluer avant de se lancer :
  - Inscription avec validation (pas d'accès instantané) et intention
    commerciale attendue (liens affiliés visibles, mention obligatoire) —
    à vérifier si compatible avec un usage interne (calculateur de coût de
    recette, pas de redirection d'achat).
  - Couverture probablement faible sur les produits frais (légumes,
    fruits, viande) — précisément la moitié du catalogue actuel — ces
    flux favorisent les produits emballés/marqués.
  - Un connecteur par enseigne (formats de flux différents).
- Scraping direct des sites (Carrefour.fr, Leclerc, Lidl...) écarté :
  CGU l'interdisent généralement, protections anti-bot, prix
  variables par magasin/région.

**Prochaine étape si on reprend ce sujet** : lister précisément quels
programmes d'affiliation sont ouverts aujourd'hui et leurs conditions
d'inscription, avant d'investir du temps d'intégration.

## Nutrition des ingrédients composites

**Piste (reprise du README) : calcul depuis `composite_ingredients.json`**

Pour X grammes d'un ingrédient composite (ex. garam masala) :

```python
ratio = x / batch_yield["quantity"]   # 10 g sur un lot de 50 g = 0.2
for comp in components:
    contrib = comp["quantity"] * ratio  # quantité effective du composant
    # → lookup dans la table nutrition
```
