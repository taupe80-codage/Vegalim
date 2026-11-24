/**
 * useProfileDiet.js — Régime et objectif santé du profil de l'utilisateur connecté.
 *
 * Le régime sert de valeur par défaut aux filtres : un profil vegan coche
 * « Vegan » dans tous les panneaux de filtres (accueil, planning, frigo, cycle,
 * astro). L'objectif santé (donnée de santé, enregistrée avec consentement)
 * adapte la fiche recette : « diabete » y affiche les ingrédients à surveiller.
 * Renvoient '' hors connexion ou si le profil est indisponible.
 */
import { useEffect, useState } from 'react';
import { useAuth } from './AuthContext';
import { profile as profileApi } from './api';

function useProfileField(field) {
  const { user } = useAuth() || {};
  const [value, setValue] = useState('');

  useEffect(() => {
    if (!user) return undefined;
    let cancelled = false;
    profileApi.get()
      .then(p => { if (!cancelled) setValue(p?.[field] || ''); })
      .catch(() => { /* profil indisponible : pas de valeur par défaut */ });
    return () => { cancelled = true; };
  }, [user, field]);

  return user ? value : '';
}

export function useProfileDiet() {
  return useProfileField('diet');
}

export function useProfileGoal() {
  return useProfileField('health_goal');
}

/** Coche « Régime » par défaut pour un régime de profil donné. */
export function defaultDietFilter(profileDiet) {
  return profileDiet === 'vegan' ? 'vegan' : '';
}
