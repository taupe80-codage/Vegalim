/**
 * constants.js — Constantes partagées entre toutes les pages.
 *
 * Source de vérité unique pour les types de plat, régimes, etc.
 * Toujours importer depuis ici plutôt que de redéfinir localement.
 */

// Type de plat — aligné sur dish_type dans recipes.json
// Utilisé par : HomePage (filtres), FrigoPage (filtre), RecipeCard (badge)
export const DISH_OPTIONS = [
  { value: 'starter',   label: '🥣 Entrée' },
  { value: 'main',      label: '🍽️ Plat principal' },
  { value: 'side',      label: '🫕 Accompagnement' },
  { value: 'soup',      label: '🍲 Soupe / Velouté' },
  { value: 'dessert',   label: '🍰 Dessert' },
  { value: 'breakfast', label: '🌅 Petit-déjeuner' },
  { value: 'snack',     label: '⚡ Snack' },
  { value: 'sauce',     label: '🥫 Sauce / Condiment' },
];

/** Retourne le label d'un dish_type ou le type brut si inconnu. */
export function dishTypeLabel(type) {
  return DISH_OPTIONS.find(o => o.value === type)?.label ?? type;
}
