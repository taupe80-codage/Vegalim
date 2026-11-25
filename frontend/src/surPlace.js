/**
 * surPlace.js — Saisie du mode « Sur place » (pages/SurPlacePage.jsx).
 *
 *   splitFoods("pâtes, tomates et feta") → ['pâtes', 'tomates', 'feta']
 */
export function splitFoods(text) {
  return String(text || '')
    .split(/[,;\n+/]|\s+et\s+/i)
    .map(s => s.trim())
    .filter(s => s.length > 1)
    .slice(0, 10);
}
