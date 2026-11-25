/**
 * cookTimers.js — Durées citées dans les étapes d'une recette (mode cuisine).
 *
 *   findDurations("Cuire 10 à 12 minutes puis laisser reposer 1 h 30")
 *   → [{ start, end, label: "10 à 12 minutes", seconds: 600 },
 *      { start, end, label: "1 h 30", seconds: 5400 }]
 *
 * Une fourchette (« 10 à 12 minutes ») démarre sur la borne basse : on vérifie
 * la cuisson à la fin du minuteur. Au-delà de LONG_SECONDS (trempage d'une
 * nuit, levée de 8 h), la durée est signalée sans minuteur (long: true).
 */

export const LONG_SECONDS = 6 * 3600;

const NUM = String.raw`(\d+(?:[.,]\d+)?)`;
const UNIT = String.raw`(heures?|h|minutes?|min|mn|secondes?|sec)`;
// Pas de lettre juste après l'unité (« 1h30 » reste lisible, « 5 hachées » non)
const RE = new RegExp(
  `${NUM}(?:\\s*(?:à|-|–|ou)\\s*${NUM})?\\s*${UNIT}(?![a-zà-ÿ])(?:\\s*(\\d{1,2})(?!\\d|[.,]\\d)(?:\\s*(?:minutes?|min|mn)(?![a-zà-ÿ]))?)?`,
  'gi',
);

const toNum = (s) => parseFloat(String(s).replace(',', '.'));

function unitSeconds(unit) {
  const u = unit.toLowerCase();
  if (u.startsWith('h')) return 3600;
  if (u.startsWith('s')) return 1;
  return 60;
}

export function findDurations(text) {
  const out = [];
  if (!text) return out;
  RE.lastIndex = 0;
  let m;
  while ((m = RE.exec(text)) !== null) {
    const [full, a, , unit, extraMin] = m;
    const per = unitSeconds(unit);
    // Minutes après des heures seulement (« 1 h 30 ») ; sinon on ne garde que l'unité
    const hasExtra = extraMin !== undefined && per === 3600;
    let label = full;
    let seconds = toNum(a) * per;
    if (hasExtra) {
      seconds += parseInt(extraMin, 10) * 60;
    } else if (extraMin !== undefined) {
      label = full.slice(0, full.length - full.slice(full.search(new RegExp(`${unit}`, 'i')) + unit.length).length);
    }
    label = label.trim();
    seconds = Math.round(seconds);
    if (seconds <= 0) continue;
    out.push({ start: m.index, end: m.index + label.length, label, seconds, long: seconds > LONG_SECONDS });
  }
  return out;
}

/** « Étape 3 : Faire… » → « Faire… » */
export function cleanStep(step) {
  return String(step || '')
    .replace(/^(é|e)tape\s*\d+\s*[-:.]\s*/i, '')
    .replace(/^step\s*\d+\s*[-:.]\s*/i, '')
    .trim();
}

/** 90 → « 1:30 » ; 3725 → « 1:02:05 » */
export function formatClock(totalSeconds) {
  const s = Math.max(0, Math.round(totalSeconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const pad = (n) => String(n).padStart(2, '0');
  return h ? `${h}:${pad(m)}:${pad(sec)}` : `${m}:${pad(sec)}`;
}
