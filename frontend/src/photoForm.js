/**
 * photoForm.js — Vérifications du formulaire « Proposer une photo »
 * (PhotoProposal.jsx), avant l'envoi : mêmes bornes que le serveur
 * (routes/photo_proposals.py, contribution_service.save_photo).
 */

export const PHOTO_MAX_BYTES = 8 * 1024 * 1024;
export const PHOTO_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

/** Renvoie le premier problème à corriger, ou '' si l'envoi peut partir. */
export function checkPhotoForm({ file, author, consent }) {
  if (!file) return 'Choisissez une photo.';
  if (!PHOTO_TYPES.includes(file.type)) return 'Format accepté : JPEG, PNG ou WebP.';
  if (file.size > PHOTO_MAX_BYTES) return 'Photo trop lourde (8 Mo maximum).';
  if ((author || '').trim().length < 2) return 'Indiquez votre pseudo.';
  if (!consent) return 'Cochez la case pour confirmer que la photo est la vôtre.';
  return '';
}
