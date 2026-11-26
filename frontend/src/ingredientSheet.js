/**
 * ingredientSheet.js — Calculs de la fiche ingrédient (fonctions pures).
 *
 * Le lien depuis une recette porte la quantité utilisée :
 *   #/ingredient/eggplant_raw?q=400&u=g&p=4&r=<id recette>
 * (quantité pour la recette entière, unité, nombre de portions).
 */

/** Lien vers la fiche, depuis une ligne de recette. */
export function ingredientHref(iid, { quantity, unit, servings, recipeId } = {}) {
  const sp = new URLSearchParams();
  if (quantity > 0 && (unit === 'g' || unit === 'ml')) {
    sp.set('q', String(Math.round(quantity * 10) / 10));
    sp.set('u', unit);
    if (servings > 0) sp.set('p', String(servings));
  }
  if (recipeId) sp.set('r', recipeId);
  const qs = sp.toString();
  return `/ingredient/${encodeURIComponent(iid)}${qs ? `?${qs}` : ''}`;
}

/** Quantité de recette lue dans l'adresse (null si absente ou illisible). */
export function readRecipeQty(search) {
  const q = parseFloat(search?.get?.('q') || '');
  const u = search?.get?.('u');
  if (!Number.isFinite(q) || q <= 0 || (u !== 'g' && u !== 'ml')) return null;
  const p = parseInt(search.get('p') || '', 10);
  return { quantity: q, unit: u, portions: Number.isFinite(p) && p > 0 ? p : 1 };
}

/** Valeur pour une quantité donnée (g ; ml ≈ g) à partir de la valeur pour 100 g. */
export function scaleFrom100(value, grams) {
  if (value == null || !Number.isFinite(value)) return null;
  return (value * grams) / 100;
}

/** Nombre lisible à la française : 0,98 ; 22,9 ; 229. */
export function fmt(v) {
  if (v == null || !Number.isFinite(v)) return '—';
  const r = v >= 100 ? Math.round(v) : v >= 10 ? Math.round(v * 10) / 10 : v >= 1 ? Math.round(v * 100) / 100
    : Math.round(v * 1000) / 1000;
  return String(r).replace('.', ',');
}

/** Lignes du tableau « dans la recette » : par portion, pour les nutriments principaux. */
export const PORTION_KEYS = [
  ['calories_kcal', 'Énergie', 'kcal'], ['protein_g', 'Protéines', 'g'], ['carbs_g', 'Glucides', 'g'],
  ['fat_g', 'Lipides', 'g'], ['fiber_g', 'Fibres', 'g'], ['iron_mg', 'Fer', 'mg'], ['calcium_mg', 'Calcium', 'mg'],
];

export function portionRows(per100, { quantity, portions }) {
  const g = quantity / (portions || 1);
  return PORTION_KEYS
    .filter(([k]) => per100?.[k] != null)
    .map(([k, label, unit]) => ({ key: k, label, unit, value: scaleFrom100(per100[k], g) }));
}

export const MONTHS_SHORT = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'];
export const MONTHS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet', 'août',
  'septembre', 'octobre', 'novembre', 'décembre'];
