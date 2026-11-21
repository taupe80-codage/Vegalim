/**
 * contribution.js — Logique pure du formulaire « Proposer une recette ».
 *
 * Sans React ni réseau : testée dans __tests__/contribution.test.js.
 * Le serveur reste la référence (contribution_service.normalize/analyze) ;
 * ces fonctions servent l'affichage immédiat (progression, aperçu).
 */

export const DRAFT_STORAGE_KEY = 'alim_contribution_draft';

export function emptyIngredient() {
  return { name: '', ingredient_id: null, quantity: '', unit: 'g', note: '' };
}

export function emptyForm() {
  return {
    title: '',
    description: '',
    diet: 'vegetarian',
    dish_type: '',
    cuisine: '',
    difficulty: 'easy',
    servings: 4,
    prep_min: '',
    cook_min: '',
    rest_min: '',
    ingredients: [emptyIngredient(), emptyIngredient(), emptyIngredient()],
    steps: ['', ''],
    tip: '',
  };
}

/** Formulaire reçu du serveur → formulaire éditable (lignes vides en plus). */
export function formFromServer(data) {
  const base = emptyForm();
  if (!data || typeof data !== 'object') return base;
  const ings = Array.isArray(data.ingredients) && data.ingredients.length
    ? data.ingredients.map(i => ({ ...emptyIngredient(), ...i, quantity: i.quantity ?? '' }))
    : base.ingredients;
  const steps = Array.isArray(data.steps) && data.steps.length ? [...data.steps] : base.steps;
  const num = (v) => (v === 0 || v === null || v === undefined ? '' : v);
  return {
    ...base,
    ...data,
    prep_min: num(data.prep_min),
    cook_min: num(data.cook_min),
    rest_min: num(data.rest_min),
    ingredients: ings,
    steps,
  };
}

/** Formulaire → charge utile (lignes vides retirées, nombres convertis). */
export function toPayload(form) {
  const n = (v) => {
    if (v === '' || v === null || v === undefined) return null;
    const x = Number(String(v).replace(',', '.'));
    return Number.isFinite(x) ? x : null;
  };
  return {
    ...form,
    servings: n(form.servings) ?? 4,
    prep_min: n(form.prep_min) ?? 0,
    cook_min: n(form.cook_min) ?? 0,
    rest_min: n(form.rest_min) ?? 0,
    ingredients: form.ingredients
      .filter(i => (i.name || '').trim() || i.ingredient_id)
      .map(i => ({ ...i, quantity: i.unit === 'to_taste' ? null : n(i.quantity) })),
    steps: form.steps.map(s => (s || '').trim()).filter(Boolean),
  };
}

/** Déplace l'élément i d'un cran (dir = -1 ou +1) ; liste inchangée en bord. */
export function moveItem(list, i, dir) {
  const j = i + dir;
  if (j < 0 || j >= list.length) return list;
  const out = [...list];
  [out[i], out[j]] = [out[j], out[i]];
  return out;
}

/** Sections du formulaire et leur état (pour la barre de progression). */
export function sectionStatus(form) {
  const p = toPayload(form);
  return [
    { id: 'essentiel',   label: "L'essentiel", done: p.title.trim().length >= 5 && !!p.dish_type },
    { id: 'ingredients', label: 'Ingrédients', done: p.ingredients.length >= 2
        && p.ingredients.every(i => i.unit === 'to_taste' || i.quantity) },
    { id: 'etapes',      label: 'Étapes',      done: p.steps.length >= 2 },
    { id: 'details',     label: 'Temps et portions', done: (p.prep_min + p.cook_min) > 0 && p.servings > 0 },
  ];
}

export function formatMinutes(total) {
  const t = Math.round(Number(total) || 0);
  if (t <= 0) return '—';
  if (t < 60) return `${t} min`;
  const h = Math.floor(t / 60);
  const m = t % 60;
  return m ? `${h} h ${String(m).padStart(2, '0')}` : `${h} h`;
}

const UNIT_LABELS = {
  g: ['g', 'g'], kg: ['kg', 'kg'], ml: ['ml', 'ml'], cl: ['cl', 'cl'], l: ['l', 'l'],
  tbsp: ['c. à soupe', 'c. à soupe'], tsp: ['c. à café', 'c. à café'],
  pinch: ['pincée', 'pincées'], piece: ['', ''], gousse: ['gousse', 'gousses'],
  tranche: ['tranche', 'tranches'], botte: ['botte', 'bottes'], poignee: ['poignée', 'poignées'],
  feuille: ['feuille', 'feuilles'], brin: ['brin', 'brins'],
};

/** « 2 c. à soupe d'huile d'olive », « 1 oignon (émincé) », « sel, selon le goût ». */
export function ingredientLine(ing) {
  const name = (ing.name || '').trim();
  if (!name) return '';
  const note = ing.note ? ` (${ing.note})` : '';
  if (ing.unit === 'to_taste') return `${name}, selon le goût${note}`;
  const q = Number(String(ing.quantity ?? '').replace(',', '.'));
  if (!q) return `${name}${note}`;
  const qs = String(Math.round(q * 100) / 100).replace('.', ',');
  const [one, many] = UNIT_LABELS[ing.unit] || [ing.unit, ing.unit];
  const unit = q > 1 ? many : one;
  if (!unit) return `${qs} ${name}${note}`;
  const de = /^[aeiouyhâéèêîôœ]/i.test(name) ? "d'" : 'de ';
  return `${qs} ${unit} ${de}${name}${note}`;
}

export const STATUS_TONES = {
  draft: 'neutral', submitted: 'info', changes_requested: 'warn', published: 'ok', rejected: 'bad',
};
