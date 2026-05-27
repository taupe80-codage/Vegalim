/**
 * useRecentlyViewed.js — Historique des recettes consultées
 *
 * Stocke les 10 dernières recettes vues dans localStorage.
 * Snapshot léger : juste les champs nécessaires à RecipeCard.
 *
 * API publique :
 *   addToRecentlyViewed(recipe)  — appelé dans RecipeDetailPage au chargement
 *   useRecentlyViewed()          — hook React → { recent, clear }
 */

import { useState, useCallback } from 'react';

const STORAGE_KEY = 'alim_recently_viewed';
const MAX_ITEMS   = 10;

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]');
  } catch {
    return [];
  }
}

function save(items) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(items));
  } catch { /* quota exceeded — fail silently */ }
}

/**
 * Ajoute une recette à l'historique (dédoublonnage, max 10).
 * À appeler en dehors d'un composant React.
 */
export function addToRecentlyViewed(recipe) {
  if (!recipe?.id) return;
  const items    = load();
  const filtered = items.filter(r => r.id !== recipe.id);
  const snap = {
    id:          recipe.id,
    title_fr:    recipe.titles?.fr || recipe.title_fr || recipe.id,
    titles:      recipe.titles    || {},
    dish_type:   recipe.dish_type || '',
    image_url:   recipe.image_url,
    final_score: recipe.final_score ?? recipe.scoring?.iconic?.score ?? 0,
    iconic_score: recipe.scoring?.iconic?.score ?? 0,
    diet_flags:           recipe.diet_flags          || {},
    diet_flags_enriched:  recipe.diet_flags_enriched || {},
    tags:                 recipe.tags                || {},
    origin:               recipe.origin              || {},
    difficulty:           recipe.difficulty_level    || recipe.difficulty,
    servings:             recipe.servings            || 4,
    total_time_min:       recipe.timing?.total_min,
    nutrition:            recipe.nutrition           || {},
    health_scores:        recipe.health_scores       || {},
    nutrition_highlights: recipe.nutrition_highlights || {},
    technique:            recipe.technique           || [],
    viewed_at:            Date.now(),
  };
  save([snap, ...filtered].slice(0, MAX_ITEMS));
}

/**
 * Hook React — retourne l'historique courant et une fonction clear.
 * Se lit une seule fois au montage (SSR-safe).
 */
export function useRecentlyViewed() {
  const [recent, setRecent] = useState(() => load());

  const clear = useCallback(() => {
    try { localStorage.removeItem(STORAGE_KEY); } catch { /* */ }
    setRecent([]);
  }, []);

  return { recent, clear };
}
