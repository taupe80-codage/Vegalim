/**
 * FavoritesContext.jsx — Favoris persistants (localStorage)
 *
 * Fonctionne sans compte. Les favoris sont stockés localement
 * et synchronisés entre toutes les RecipeCard via contexte React.
 * Connecté : chaque favori est aussi un like côté API (personnalisation),
 * fusionné avec les likes du compte à la connexion (favoritesSync.js).
 *
 * Usage :
 *   const { favorites, toggle, isFavorite } = useFavorites();
 *   isFavorite(recipe.id)   → boolean
 *   toggle(recipe)           → ajoute ou retire
 */

import { createContext, useContext, useState, useCallback, useEffect } from 'react';
import { useAuth } from './AuthContext';
import { profile as profileApi, recipes as recipesApi } from './api';
import { syncFavorites, sendInteraction } from './favoritesSync';

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
  const { user } = useAuth() || {};
  const loggedIn = !!user;

  // Connexion : fusion favoris locaux ↔ likes du compte
  useEffect(() => {
    if (!loggedIn) return;
    let cancelled = false;
    syncFavorites(load(), {
      likes:       profileApi.likes,
      interaction: profileApi.interaction,
      fetchRecipe: recipesApi.byId,
    }, MAX_ITEMS)
      .then(fetched => {
        if (cancelled || !fetched.length) return;
        setFavorites(prev => {
          const ids  = new Set(prev.map(r => r.id));
          const next = [...prev, ...fetched.filter(r => !ids.has(r.id)).map(snapshot)].slice(0, MAX_ITEMS);
          save(next);
          return next;
        });
      })
      .catch(() => { /* API indisponible : les favoris locaux restent utilisables */ });
    return () => { cancelled = true; };
  }, [loggedIn]);

  const toggle = useCallback((recipe) => {
    const exists = load().some(r => r.id === recipe.id);
    setFavorites(prev => {
      const next = exists
        ? prev.filter(r => r.id !== recipe.id)
        : [snapshot(recipe), ...prev].slice(0, MAX_ITEMS);
      save(next);
      return next;
    });
    if (loggedIn) sendInteraction(profileApi.interaction, recipe.id, exists ? 'unlike' : 'like');
  }, [loggedIn]);

  const isFavorite = useCallback((id) => {
    return favorites.some(r => r.id === id);
  }, [favorites]);

  const clear = useCallback(() => {
    if (loggedIn) load().forEach(r => sendInteraction(profileApi.interaction, r.id, 'unlike'));
    save([]);
    setFavorites([]);
  }, [loggedIn]);

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
