/**
 * useProfileDiet.js — Régime enregistré dans le profil de l'utilisateur connecté.
 *
 * Sert de valeur par défaut aux filtres : un profil vegan coche « Vegan »
 * dans tous les panneaux de filtres (accueil, planning, frigo, cycle, astro).
 * Renvoie '' hors connexion ou si le profil est indisponible.
 */
import { useEffect, useState } from 'react';
import { useAuth } from './AuthContext';
import { profile as profileApi } from './api';

export function useProfileDiet() {
  const { user } = useAuth() || {};
  const [diet, setDiet] = useState('');

  useEffect(() => {
    if (!user) return undefined;
    let cancelled = false;
    profileApi.get()
      .then(p => { if (!cancelled) setDiet(p?.diet || ''); })
      .catch(() => { /* profil indisponible : pas de valeur par défaut */ });
    return () => { cancelled = true; };
  }, [user]);

  return user ? diet : '';
}

/** Coche « Régime » par défaut pour un régime de profil donné. */
export function defaultDietFilter(profileDiet) {
  return profileDiet === 'vegan' ? 'vegan' : '';
}
