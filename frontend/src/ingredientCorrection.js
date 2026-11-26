/**
 * ingredientCorrection.js — Vérification du formulaire « Signaler une erreur »
 * (fiche ingrédient). Les mêmes règles sont appliquées par le serveur.
 */

export const MAX_VALUE = 100000;

/** Message d'erreur en français, ou '' si le formulaire est complet. */
export function checkCorrection({ field, value, sourceRef, sourceUrl, comment, current }) {
  if (field !== 'other') {
    const v = parseFloat(String(value ?? '').replace(',', '.').trim());
    if (!Number.isFinite(v) || v < 0 || v > MAX_VALUE) return 'Indiquez la valeur juste, pour 100 g (un nombre positif).';
    if (current != null && Math.abs(v - current) < 1e-9) return 'C’est déjà la valeur affichée.';
  } else if ((comment || '').trim().length < 10) {
    return 'Décrivez ce qu’il faut corriger (10 caractères au moins).';
  }
  if ((sourceRef || '').trim().length < 4) return 'La source est obligatoire : nom de la table, de l’étude ou du produit.';
  const url = (sourceUrl || '').trim();
  if (url && !/^https?:\/\/[^\s]+\.[^\s]+$/i.test(url)) return 'Le lien doit commencer par http:// ou https://.';
  return '';
}
