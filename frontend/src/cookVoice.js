/**
 * cookVoice.js — Commandes vocales du mode cuisine (interprétation).
 *
 *   parseCommand("étape suivante")        → { type: 'next' }
 *   parseCommand("minuteur cinq minutes") → { type: 'timer', seconds: 300 }
 *   parseCommand("lance le minuteur")     → { type: 'timer' }   (durée de l'étape)
 *
 * La reconnaissance (Web Speech API) et la synthèse vocale sont gérées par
 * CookMode.jsx ; ici, seulement le texte entendu → action.
 */
import { findDurations } from './cookTimers';

export const VOICE_COMMANDS = [
  ['« Suivante »', 'étape suivante'],
  ['« Précédente »', 'étape précédente'],
  ['« Répète »', 'relire l’étape à voix haute'],
  ['« Minuteur »', 'lancer le minuteur de l’étape'],
  ['« Minuteur 5 minutes »', 'minuteur de la durée dite'],
  ['« Ingrédients »', 'afficher ou masquer les ingrédients'],
  ['« Stop »', 'arrêter la lecture'],
  ['« Quitter »', 'fermer le mode cuisine'],
];

const NUMBER_WORDS = {
  un: 1, une: 1, deux: 2, trois: 3, quatre: 4, cinq: 5, six: 6, sept: 7, huit: 8, neuf: 9,
  dix: 10, onze: 11, douze: 12, treize: 13, quatorze: 14, quinze: 15, seize: 16,
  'dix-sept': 17, 'dix-huit': 18, 'dix-neuf': 19, vingt: 20, 'vingt-cinq': 25,
  trente: 30, 'trente-cinq': 35, quarante: 40, 'quarante-cinq': 45, cinquante: 50,
  soixante: 60, 'une demi': 0.5, demi: 0.5,
};

export function normalize(text) {
  return String(text || '')
    .toLowerCase()
    .normalize('NFD').replace(/[̀-ͯ]/g, '')
    .replace(/[’']/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/** « cinq minutes » → « 5 minutes » (les nombres les plus longs d'abord). */
export function wordsToDigits(text) {
  let t = ` ${text} `;
  for (const w of Object.keys(NUMBER_WORDS).sort((a, b) => b.length - a.length)) {
    t = t.replace(new RegExp(`(?<=\\s)${w}(?=\\s)`, 'g'), String(NUMBER_WORDS[w]));
  }
  return t.trim();
}

export function parseCommand(transcript) {
  const t = normalize(transcript);
  if (!t) return null;
  if (/\b(quitter|quitte|ferme(r)? (le )?mode cuisine)\b/.test(t)) return { type: 'close' };
  if (/\b(stop|silence|tais ?toi|arrete de lire|chut)\b/.test(t)) return { type: 'stop' };
  if (/\b(minuteur|chrono|chronometre|timer)\b/.test(t)) {
    const d = findDurations(wordsToDigits(t))[0];
    return d ? { type: 'timer', seconds: d.seconds, label: d.label } : { type: 'timer' };
  }
  if (/\bingredients?\b/.test(t)) return { type: 'ingredients' };
  if (/\b(precedente?|retour|reviens|en arriere)\b/.test(t)) return { type: 'prev' };
  if (/\b(suivante?|apres|ensuite|continue|continuer|avance)\b/.test(t)) return { type: 'next' };
  if (/\b(repete|repeter|relis|relire|lis|lire|redis|encore)\b/.test(t)) return { type: 'repeat' };
  return null;
}

/** Texte lu à voix haute : unités en toutes lettres (« 15 ml » → « 15 millilitres »). */
export function speakable(text) {
  return String(text || '')
    .replace(/(\d)\s*kg\b/gi, '$1 kilos')
    .replace(/(\d)\s*g\b/gi, '$1 grammes')
    .replace(/(\d)\s*ml\b/gi, '$1 millilitres')
    .replace(/(\d)\s*cl\b/gi, '$1 centilitres')
    .replace(/(\d)\s*L\b/g, '$1 litres')
    .replace(/(\d)\s*min\b/gi, '$1 minutes')
    .replace(/(\d)\s*°C\b/gi, '$1 degrés')
    .replace(/(\d)\s*cm\b/gi, '$1 centimètres');
}
