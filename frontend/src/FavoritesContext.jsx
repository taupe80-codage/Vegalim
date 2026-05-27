/**
 * FavoritesContext.jsx — Favoris persistants (localStorage)
 *
 * Fonctionne sans compte. Les favoris sont stockés localement
 * et synchronisés entre toutes les RecipeCard via contexte React.
 *
 * Usage :
 *   const { favorites, toggle, isFavorite } = useFavorites();
 *   isFavorite(recipe.id)   → boolean
 *   toggle(recipe)           → ajoute ou retire
 */

import { createContext, useContext, useState, useCallback } from 'react';

const STORAGE_KEY = 'alim_favorites';
const MAX_ITEMS   = 100;

function load() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'); }
  catch { return []; }
}
function save(items) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(items)); }
  catch { /* quota exceeded */ }
}

/** Snapshot léger compatible RecipeCard */
function snapshot(recipe) {
  return {
    id:          recipe.id,
    title_fr:    recipe.titles?.fr || recipe.title_fr || recipe.id,
    titles:      recipe.titles    || {},
    dish_type:   recipe.dish_type || '',
    image_url:   recipe.image_url,
    final_score: recipe.final_score  ?? recipe.scoring?.iconic?.score ?? 0,
    iconic_score: recipe.scoring?.iconic?.score ?? 0,
    diet_flags:           recipe.diet_flags          || {},
    diet_flags_enriched:  recipe.diet_flags_enriched || {},
    tags:                 recipe.tags                || {},
    origin:               recipe.origin              || {},
    difficulty:           recipe.difficulty_level    || recipe.difficulty,
    servings:             recipe.servings            || 4,
    total_time_min:       recipe.total_time_min      || recipe.timing?.total_min,
    nutrition:            recipe.nutrition           || {},
    health_scores:        recipe.health_scores       || {},
    nutrition_highlights: recipe.nutrition_highlights || {},
    technique:            recipe.technique           || [],
    saved_at:             Date.now(),
  };
}

const FavoritesContext = createContext(null);

export function FavoritesProvider({ children }) {
  const [favorites, setFavorites] = useState(load);

  const toggle = useCallback((recipe) => {
    setFavorites(prev => {
      const exists = prev.some(r => r.id === recipe.id);
      const next   = exists
        ? prev.filter(r => r.id !== recipe.id)
        : [snapshot(recipe), ...prev].slice(0, MAX_ITEMS);
      save(next);
      return next;
    });
  }, []);

  const isFavorite = useCallback((id) => {
    return favorites.some(r => r.id === id);
  }, [favorites]);

  const clear = useCallback(() => {
    save([]);
    setFavorites([]);
  }, []);

  return (
    <FavoritesContext.Provider value={{ favorites, toggle, isFavorite, clear }}>
      {children}
    </FavoritesContext.Provider>
  );
}

export function useFavorites() {
  const ctx = useContext(FavoritesContext);
  if (!ctx) throw new Error('useFavorites() doit être dans un <FavoritesProvider>');
  return ctx;
}
