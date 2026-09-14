/**
 * formatIngredientQty.js
 *
 * Retourne l'equivalent "pratique" d'une quantite en g ou ml.
 * Ex: 15g ail → "(3 gousses)" | 5ml sauce soja → "(1 c. a cafe)"
 *
 * @param {string} ingredientId
 * @param {number} qty          — quantite scalee (pour N personnes)
 * @param {string} unit         — "g" | "ml"
 * @param {object} physData     — import de ingredientPhysical.json
 * @returns {string}            — "(X unite)" ou ""
 */

// Vraies etiquettes avec accents
const PIECE_LABEL_DISPLAY = {
  piece:  ['pièce',   'pièces'],
  gousse: ['gousse',  'gousses'],
  tete:   ['tête',    'têtes'],
  leaf:   ['feuille', 'feuilles'],
  botte:  ['botte',   'bottes'],
  petit:  ['petit',   'petits'],
  gros:   ['gros',    'gros'],
  pc:     ['pièce',   'pièces'],
  unit:   ['unité',   'unités'],
};

// --- Ingredients pour lesquels AUCUNE conversion cuillere n'est pertinente ---

// Legumes/fruits entiers
const NO_SPOON_BASE = new Set([
  'egg', 'onion', 'red_onion', 'spring_onion', 'garlic', 'shallot',
  'lemongrass', 'lemon', 'lime', 'citrus', 'orange',
  'tomato', 'carrot', 'potato', 'sweet_potato', 'zucchini', 'eggplant',
  'bell_pepper', 'red_bell_pepper', 'chili_pepper', 'avocado',
  'apple', 'pear', 'banana', 'mango', 'peach', 'apricot', 'plum',
  'endive', 'fennel', 'artichoke', 'leek', 'celery', 'celeriac',
  'turnip', 'parsnip', 'beet', 'butternut_squash', 'squash',
  'pumpkin', 'corn', 'broccoli', 'cauliflower', 'lotus_root', 'taro',
]);

// Herbes fraiches : jamais de cuillere (se mesurent en grammes ou en botte)
const FRESH_HERBS = new Set([
  'fresh_coriander', 'coriander',
  'basil', 'thai_basil',
  'parsley', 'fresh_parsley',
  'mint', 'fresh_mint', 'spearmint',
  'dill', 'tarragon', 'chervil', 'chives',
  'sorrel', 'lovage', 'lemon_verbena',
  'thyme', 'thyme/fresh', 'rosemary', 'sage', 'oregano', 'marjoram',
  'bay_leaf', 'bouquet_garni', 'kaffir_lime_leaves',
  'shiso', 'pandanus', 'epazote', 'culantro',
]);

// Fruits/baies (30g de framboises != 2 c. a soupe)
const FRESH_FRUITS = new Set([
  'blueberry', 'raspberry', 'strawberry', 'cherry', 'grape',
  'blackberry', 'gooseberry', 'currant', 'cranberry', 'goji_berry',
  'pomegranate', 'passion_fruit', 'lychee', 'dragon_fruit', 'guava',
  'fig', 'date', 'dried_cranberry',
]);

// Zestes : se mesurent en g, pas en cuillere
const ZESTS = new Set([
  'lemon_zest', 'lime_zest', 'orange_zest', 'zest',
]);

function isNoSpoon(base, full) {
  if (NO_SPOON_BASE.has(base) || NO_SPOON_BASE.has(full)) return true;
  if (FRESH_HERBS.has(base)   || FRESH_HERBS.has(full))   return true;
  if (FRESH_FRUITS.has(base)  || FRESH_FRUITS.has(full))  return true;
  if (ZESTS.has(base)         || ZESTS.has(full))         return true;
  // Pattern : "fresh_*" ou "*/fresh"
  if (base.startsWith('fresh_') || full.endsWith('/fresh')) return true;
  return false;
}

function fmt(n) {
  if (n === Math.round(n)) return String(Math.round(n));
  const h = Math.round(n * 2) / 2;
  if (h === Math.round(h)) return String(h);
  return n.toFixed(1);
}

// Prefere c. a soupe si qty >= 10, sinon c. a cafe
// Tolerance 0.25 pour eviter les zones mortes entre 15g, 22.5g, 30g, etc.
function spoonEquiv(q, maxQty) {
  if (q > maxQty) return '';
  const tbsp   = q / 15;
  const tsp    = q / 5;
  const tbspOk = tbsp >= 0.5 && tbsp <= 5 && Math.abs(tbsp - Math.round(tbsp * 2) / 2) < 0.25;
  const tspOk  = tsp  >= 0.5 && tsp  <= 3 && Math.abs(tsp  - Math.round(tsp  * 2) / 2) < 0.25;
  if (q >= 10 && tbspOk) return '(' + fmt(Math.round(tbsp * 2) / 2) + ' c. à soupe)';
  if (tspOk)              return '(' + fmt(Math.round(tsp  * 2) / 2) + ' c. à café)';
  if (tbspOk)             return '(' + fmt(Math.round(tbsp * 2) / 2) + ' c. à soupe)';
  return '';
}

export function formatIngredientQty(ingredientId, qty, unit, physData) {
  if (!qty || !unit || !ingredientId) return '';

  // Resolution alias "base/variant" → base
  const full = ingredientId;
  const base = full.includes('/') ? full.split('/')[0] : full;
  const p    = physData[full] || physData[base] || null;

  // --- 1. Equivalent en pieces (g uniquement) ---------------------------
  if (unit === 'g' && p && p.piece_g) {
    const count = qty / p.piece_g;
    if (count >= 0.5 && count <= 20) {
      const rounded  = Math.round(count * 4) / 4;
      const labels   = PIECE_LABEL_DISPLAY[p.piece_label] || ['pièce', 'pièces'];
      const singular = labels[rounded <= 1 ? 0 : 1];
      return '(' + fmt(rounded) + ' ' + singular + ')';
    }
  }

  // --- 2. Pincee pour les tres petites quantites (epices seches) --------
  // 1 pincee ≈ 1g — seulement si pas piece_g et pas herbe fraiche/legume
  if (unit === 'g' && qty > 0 && qty <= 2 && !(p && p.piece_g) && !isNoSpoon(base, full)) {
    const n     = qty <= 1 ? 1 : 2;
    const label = n === 1 ? 'pincée' : 'pincées';
    return '(' + (n === 1 ? 'une' : n) + ' ' + label + ')';
  }

  // --- 3. Cuilleres pour liquides en ml (max 75ml = 5 c. a soupe) ------
  if (unit === 'ml' && !isNoSpoon(base, full)) {
    const r = spoonEquiv(qty, 75);
    if (r) return r;
  }

  // --- 4. Cuilleres pour solides en g (epices / poudres / pates) -------
  if (unit === 'g' && !(p && p.piece_g) && !isNoSpoon(base, full)) {
    const r = spoonEquiv(qty, 45);
    if (r) return r;
  }

  return '';
}
