/**
 * stepQuantities.js — Quantités des étapes ajustées aux portions choisies.
 *
 * La liste d'ingrédients suivait le compteur de portions, mais le texte des
 * étapes gardait « 150 g d'oignon » (recette pour 4) : on recalcule les
 * masses et volumes (g, kg, ml, cl, dl, L) et quelques pièces (œufs, gousses,
 * feuilles, tranches). Durées, températures, tailles (cm, mm) ne bougent pas.
 *
 *   scaleSegments("Faire revenir 150 g d'oignon 5 minutes", 0.5)
 *   → [{ text: "Faire revenir " },
 *      { text: "75 g", original: "150 g" },
 *      { text: " d'oignon 5 minutes" }]
 */

const NUM = String.raw`(\d+(?:[.,]\d+)?)`;
const MASS_VOL = String.raw`kilos?|kg|grammes?|g|millilitres?|ml|cl|dl|litres?|l`;
const PIECES = String.raw`œufs?|oeufs?|gousses?|feuilles?|tranches?`;
// nombre (ou fourchette « 2 à 3 ») puis unité, sans lettre ni apostrophe collée
// après (« 2 l'un après l'autre » n'est pas 2 litres)
const RE = new RegExp(
  `${NUM}(?:\\s*(à|-|–)\\s*${NUM})?\\s*(${MASS_VOL}|${PIECES})(?![a-zà-ÿœ'’])`,
  'gi',
);

const toNum = (s) => parseFloat(String(s).replace(',', '.'));
const fr = (v) => String(v).replace('.', ',');

function roundMass(v) {
  if (v >= 100) return Math.round(v / 5) * 5;
  if (v >= 50) return Math.round(v);
  if (v >= 2) return Math.round(v * 2) / 2;
  return Math.round(v * 10) / 10 || 0.1;
}

/** Valeur ajustée, dans l'unité la plus lisible (0,6 L → 600 ml, 1 500 g → 1,5 kg). */
function formatScaled(value, unit) {
  const u = unit.toLowerCase();
  const isPiece = /^(œuf|oeuf|gousse|feuille|tranche)/.test(u);
  if (isPiece) {
    const v = Math.max(0.5, Math.round(value * 2) / 2);
    const singular = v <= 1;
    const word = singular ? unit.replace(/s$/i, '') : (/s$/i.test(unit) ? unit : `${unit}s`);
    return `${fr(v)} ${word}`;
  }
  // tout en g ou ml pour choisir l'unité d'affichage
  let base = value;
  let kind = 'g';
  if (u === 'kg' || u.startsWith('kilo')) base = value * 1000;
  else if (u === 'g' || u.startsWith('gramme')) base = value;
  else {
    kind = 'ml';
    if (u === 'cl') base = value * 10;
    else if (u === 'dl') base = value * 100;
    else if (u === 'l' || u.startsWith('litre')) base = value * 1000;
  }
  if (base >= 1000) {
    const big = Math.round(base / 100) / 10;            // 1,2 kg / 1,5 L
    return `${fr(big)} ${kind === 'g' ? 'kg' : 'L'}`;
  }
  return `${fr(roundMass(base))} ${kind}`;
}

export function scaleSegments(text, ratio) {
  const src = String(text || '');
  if (!ratio || Math.abs(ratio - 1) < 1e-9) return [{ text: src }];
  const out = [];
  let last = 0;
  RE.lastIndex = 0;
  let m;
  while ((m = RE.exec(src)) !== null) {
    const [full, a, sep, b, unit] = m;
    if (m.index > last) out.push({ text: src.slice(last, m.index) });
    let scaled;
    if (b !== undefined) {
      // fourchette : « 2 à 3 gousses » → « 1 à 1,5 gousse »
      const hi = formatScaled(toNum(b) * ratio, unit);
      const loNum = formatScaled(toNum(a) * ratio, unit).split(' ')[0];
      const hiParts = hi.split(' ');
      scaled = `${loNum} ${sep} ${hiParts[0]} ${hiParts.slice(1).join(' ')}`;
    } else {
      scaled = formatScaled(toNum(a) * ratio, unit);
    }
    out.push({ text: scaled, original: full });
    last = m.index + full.length;
  }
  if (last < src.length) out.push({ text: src.slice(last) });
  return out;
}

/** Texte ajusté, sans balisage. */
export function scaleStepText(text, ratio) {
  return scaleSegments(text, ratio).map(s => s.text).join('');
}
