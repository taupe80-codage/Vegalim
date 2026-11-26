/**
 * recipeEdits.js — Recette modifiée par le membre (fonctions pures).
 *
 * Les modifications sont décrites comme côté serveur (backend/services/recipe_edits.py) :
 *   { base: 'original' | 'vegan',
 *     rows: [{ src, orig, ingredient, quantity, unit }] }
 * src : ligne de la composition de départ (null : ingrédient ajouté) ; une ligne
 * absente de rows est retirée. Quantités pour les portions de la recette.
 */

export const NUMERIC_UNITS = ['g', 'ml'];

export const isNumericUnit = (u) => NUMERIC_UNITS.includes(u);

/** Lignes de départ : la composition telle quelle (aucune modification). */
export function baseRows(composition = []) {
  return composition.map((c, i) => ({
    src: i,
    orig: c.ingredient || c.ingredient_id || '',
    ingredient: c.ingredient || c.ingredient_id || '',
    quantity: c.quantity ?? null,
    unit: isNumericUnit(c.unit) ? c.unit : null,
  }));
}

/** Quantité affichée pour le nombre de portions choisi. */
export function toDisplayQty(q, ratio = 1) {
  if (q == null) return '';
  const v = q * ratio;
  return v >= 10 ? String(Math.round(v)) : String(Math.round(v * 10) / 10).replace('.', ',');
}

/** Quantité saisie (pour les portions choisies) → quantité de la recette ; null si illisible. */
export function fromDisplayQty(text, ratio = 1) {
  const v = parseFloat(String(text ?? '').replace(',', '.').trim());
  if (!Number.isFinite(v) || v <= 0 || !ratio) return null;
  return Math.round((v / ratio) * 10) / 10;
}

/** Une ligne diffère-t-elle de la composition de départ ? */
export function rowChanged(row, composition = []) {
  if (row.src == null) return true;
  const c = composition[row.src];
  if (!c) return true;
  if ((c.ingredient || c.ingredient_id) !== row.ingredient) return true;
  if (row.quantity == null) return false;
  return Math.abs((c.quantity ?? 0) - row.quantity) >= 0.05
    || (isNumericUnit(c.unit) ? c.unit : 'g') !== (row.unit || c.unit);
}

/** Des modifications par rapport à la composition de départ ? */
export function hasChanges(rows, composition = []) {
  if (!rows) return false;
  const kept = new Set(rows.filter(r => r.src != null).map(r => r.src));
  if (composition.some((_, i) => !kept.has(i))) return true;
  return rows.some(r => rowChanged(r, composition));
}

/** Mêmes modifications (pour ne pas recalculer ni réenregistrer pour rien). */
export function sameEdits(a, b) {
  if (!a || !b) return a === b;
  return (a.base || 'original') === (b.base || 'original')
    && JSON.stringify(a.rows || []) === JSON.stringify(b.rows || []);
}

const cap = (s) => (s ? s.charAt(0).toUpperCase() + s.slice(1) : '');

/** Libellé d'une modification renvoyée par le serveur (_custom.changes). */
export function changeLabel(ch) {
  const qty = ch.before && ch.after && ch.before !== ch.after ? ` (${ch.before} → ${ch.after})` : '';
  switch (ch.kind) {
    case 'replaced': return `${cap(ch.name)} → ${ch.new_name}${qty}`;
    case 'quantity': return `${cap(ch.name)} : ${ch.before} → ${ch.after}`;
    case 'removed':  return `${cap(ch.name)} retiré`;
    case 'added':    return `${cap(ch.name)} ajouté${ch.after ? ` (${ch.after})` : ''}`;
    default:         return cap(ch.name || '');
  }
}

/** Message d'erreur lisible (le détail d'une erreur 422 de FastAPI peut être une liste). */
export function editErrorMessage(err) {
  const m = err?.message || '';
  return !m || m.startsWith('[object') ? 'Modification impossible : vérifiez les quantités.' : m;
}
