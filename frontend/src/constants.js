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
  // Toutes les sous-recettes (béchamel, laits maison, pâtes…), masquées sinon
  { value: 'base',      label: '🧂 Préparations de base' },
];

// Sous-recettes : même règle que data_io.is_component_recipe (backend)
const COMPONENT_DISH_TYPES = new Set(['sauce', 'condiment', 'paste', 'base', 'ingredient', 'broth', 'roux', 'dairy']);

export function isComponentRecipe(recipe) {
  return String(recipe?.id || '').startsWith('base_')
    || COMPONENT_DISH_TYPES.has(String(recipe?.dish_type || '').toLowerCase());
}

/** Filtre « type de plat » : « base » regroupe toutes les sous-recettes ;
 *  sans filtre qui les demande, elles sont masquées. */
export function matchesDishFilters(recipe, dishFilters) {
  const wanted = [...(dishFilters || [])];
  if (wanted.length === 0) return !isComponentRecipe(recipe);
  return wanted.includes(recipe?.dish_type)
    || (wanted.includes('base') && isComponentRecipe(recipe));
}

/** Retourne le label d'un dish_type ou le type brut si inconnu. */
export function dishTypeLabel(type) {
  return DISH_OPTIONS.find(o => o.value === type)?.label ?? type;
}
