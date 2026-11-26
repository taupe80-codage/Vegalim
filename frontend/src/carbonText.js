/**
 * carbonText.js — Textes de l'empreinte carbone de la semaine.
 */

/** Phrase de comparaison avec la moyenne des plats du catalogue. */
export function compareText(perPortion, average) {
  if (!average || !perPortion) return '';
  const d = Math.round((perPortion / average - 1) * 100);
  if (Math.abs(d) < 5) return 'dans la moyenne des plats ALIM';
  return d < 0 ? `${-d} % de moins que la moyenne des plats ALIM` : `${d} % de plus que la moyenne des plats ALIM`;
}

