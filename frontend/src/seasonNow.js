/**
 * Plats de saison du mois en cours (GET /recettes/de-saison), chargés une seule
 * fois pour toute l'application : le badge « De saison » des cartes ne dépend
 * plus de la page qui les affiche (favoris gardés dans le navigateur, cycle,
 * astro, frigo…), et l'accueil en tire sa rubrique.
 */
import { useEffect, useState } from 'react';
import { recipes as recipesApi } from './api';

const EMPTY = { month: null, ids: new Set(), results: [], total: 0 };
let _promise = null;
let _value = null;

export function loadSeasonNow() {
  if (!_promise) {
    _promise = recipesApi.inSeason(6)
      .then(d => {
        _value = { month: d?.month ?? null, ids: new Set(d?.ids || []),
                   results: d?.results || [], total: d?.total || 0 };
        return _value;
      })
      .catch(() => { _promise = null; return EMPTY; });
  }
  return _promise;
}

export function useSeasonNow() {
  const [value, setValue] = useState(_value || EMPTY);
  useEffect(() => {
    let alive = true;
    if (!_value) loadSeasonNow().then(v => { if (alive) setValue(v); });
    return () => { alive = false; };
  }, []);
  return value;
}

/** Plat de saison : l'étiquette fournie par l'API, sinon la liste du mois. */
export function isInSeason(recipe, season) {
  if (recipe?.seasonal_tag) return recipe.seasonal_tag === 'de_saison';
  return season.ids.has(String(recipe?.id || ''));
}

export const MONTHS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
                          'août', 'septembre', 'octobre', 'novembre', 'décembre'];
