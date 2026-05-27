/**
 * RecipeCard.jsx — Carte recette redesignée ALIM v7
 *
 * Nouveautés v7 :
 *  - CUISINE_COLOR_MAP : couleur accent par origine cuisine (point coloré, pas d'icône)
 *  - getCuisineColor() exportée pour RecipeDetailPage
 *  - Badge +N cliquable avec popover
 *  - Difficulté repositionnée dans le détail au niveau des durées
 */
import { useState, useRef, useEffect } from 'react';
import { navigate } from '../Router';
import { useFavorites } from '../FavoritesContext';
import AddToPlanModal from './AddToPlanModal';

// ── Couleur accent par origine cuisine ────────────────────────────────────────

export const CUISINE_COLOR_MAP = {
  // Maghreb / Moyen-Orient
  moroccan:        '#E07B39',
  tunisian:        '#E07B39',
  egyptian:        '#C68642',
  levantine:       '#C68642',
  turkish:         '#C0392B',
  persian:         '#9B59B6',
  armenian:        '#C0392B',

  // Asie de l'Est
  japanese:        '#E94560',
  korean:          '#E94560',
  chinese:         '#C0392B',

  // Asie du Sud-Est
  thai:            '#27AE60',
  vietnamese:      '#27AE60',
  indonesian:      '#27AE60',
  malaysian:       '#27AE60',
  philippine:      '#2980B9',
  sri_lankan:      '#E08020',

  // Asie du Sud
  indian:          '#E08020',
  nepali:          '#E08020',
  uzbek:           '#C68642',

  // Europe du Sud
  italian:         '#C0392B',
  spanish:         '#C0392B',
  greek:           '#2980B9',
  french:          '#7b2d8b',
  french_provencal:'#7b2d8b',

  // Europe centrale / Est
  german:          '#7F8C8D',
  polish:          '#C0392B',
  bulgarian:       '#27AE60',
  slovak:          '#27AE60',
  croatian:        '#2980B9',
  swiss:           '#C0392B',
  eastern_european:'#7F8C8D',

  // Amériques
  mexican:         '#27AE60',
  american:        '#2980B9',
  caribbean:       '#27AE60',

  // Afrique
  african:         '#C68642',

  // Défaut
  international:   '#2980B9',
};

export function getCuisineColor(recipe) {
  const cuisine = (recipe?.origin?.cuisine || '').toLowerCase();
  return CUISINE_COLOR_MAP[cuisine] || '#888780';
}

// ── Noms de cuisines en français ──────────────────────────────────────────────

export const CUISINE_LABEL_FR = {
  moroccan:         'Marocaine',
  tunisian:         'Tunisienne',
  egyptian:         'Égyptienne',
  levantine:        'Levantine',
  turkish:          'Turque',
  persian:          'Persane',
  armenian:         'Arménienne',
  japanese:         'Japonaise',
  korean:           'Coréenne',
  chinese:          'Chinoise',
  thai:             'Thaïlandaise',
  vietnamese:       'Vietnamienne',
  indonesian:       'Indonésienne',
  malaysian:        'Malaisienne',
  philippine:       'Philippine',
  sri_lankan:       'Sri Lankaise',
  indian:           'Indienne',
  south_indian:     'Indienne du Sud',
  indian_street:    'Street food indien',
  nepali:           'Népalaise',
  uzbek:            'Ouzbèke',
  italian:          'Italienne',
  spanish:          'Espagnole',
  greek:            'Grecque',
  french:           'Française',
  french_provencal: 'Provençale',
  french_alsatian:  'Alsacienne',
  german:           'Allemande',
  polish:           'Polonaise',
  bulgarian:        'Bulgare',
  slovak:           'Slovaque',
  croatian:         'Croate',
  swiss:            'Suisse',
  eastern_european: "Europe de l'Est",
  georgian:         'Géorgienne',
  mexican:          'Mexicaine',
  american:         'Américaine',
  caribbean:        'Caribéenne',
  peruvian:         'Péruvienne',
  african:          'Africaine',
  west_african:     "Afrique de l'Ouest",
  east_african:     "Afrique de l'Est",
  ethiopian:        'Éthiopienne',
  bangladeshi:      'Bangladaise',
  pakistani:        'Pakistanaise',
  international:    'Internationale',
};

// ── Mapping cuisine → gradient + emoji ────────────────────────────────────────

const CUISINE_THEME = {
  french:          { grad: ['#2d1b4e', '#7b2d8b'], emoji: '🥐' },
  french_provencal:{ grad: ['#8b4513', '#d4a853'], emoji: '🌿' },
  italian:         { grad: ['#8b0000', '#d4380d'], emoji: '🍝' },
  japanese:        { grad: ['#1a1a2e', '#e94560'], emoji: '🍱' },
  chinese:         { grad: ['#7b0000', '#d4380d'], emoji: '🥢' },
  indian:          { grad: ['#7c3d00', '#e08020'], emoji: '🍛' },
  thai:            { grad: ['#1b4332', '#40916c'], emoji: '🌶️' },
  vietnamese:      { grad: ['#003153', '#1a6b3a'], emoji: '🍜' },
  levantine:       { grad: ['#4a2c0a', '#c68642'], emoji: '🧆' },
  moroccan:        { grad: ['#5c1a1a', '#b5451b'], emoji: '🫖' },
  tunisian:        { grad: ['#6b0000', '#cc2200'], emoji: '🌶️' },
  egyptian:        { grad: ['#3d2b0a', '#9c6b00'], emoji: '🌾' },
  mexican:         { grad: ['#1a3a00', '#4a7c00'], emoji: '🌮' },
  american:        { grad: ['#1c2c5c', '#2e4db0'], emoji: '🍔' },
  caribbean:       { grad: ['#0d4b1a', '#1a8c35'], emoji: '🌴' },
  spanish:         { grad: ['#6b0000', '#b81c00'], emoji: '🥘' },
  greek:           { grad: ['#002b7f', '#0053a0'], emoji: '🫒' },
  turkish:         { grad: ['#6b0000', '#a50000'], emoji: '🥙' },
  persian:         { grad: ['#2d1b69', '#6b3fa0'], emoji: '🌺' },
  indonesian:      { grad: ['#1b3a00', '#3d7a00'], emoji: '🌴' },
  malaysian:       { grad: ['#0d3b00', '#246b00'], emoji: '🥥' },
  sri_lankan:      { grad: ['#3b0d00', '#7a2000'], emoji: '🌶️' },
  philippine:      { grad: ['#001a4d', '#00308f'], emoji: '🍚' },
  nepali:          { grad: ['#1a0a2e', '#4b1680'], emoji: '🏔️' },
  uzbek:           { grad: ['#2e1a00', '#7a4500'], emoji: '🍖' },
  armenian:        { grad: ['#4d0000', '#990000'], emoji: '🫐' },
  bulgarian:       { grad: ['#1a2e00', '#3d6e00'], emoji: '🌿' },
  polish:          { grad: ['#1a002e', '#3d0070'], emoji: '🥟' },
  german:          { grad: ['#1a1a00', '#4d4d00'], emoji: '🥨' },
  swiss:           { grad: ['#1a0000', '#660000'], emoji: '🧀' },
  slovak:          { grad: ['#002e1a', '#006b40'], emoji: '🌲' },
  croatian:        { grad: ['#0d1a4d', '#1a3399'], emoji: '🐟' },
  eastern_european:{ grad: ['#1a0d2e', '#3d2270'], emoji: '🌾' },
  international:   { grad: ['#0d1f3c', '#1a4080'], emoji: '🌍' },
  korean:          { grad: ['#3d0000', '#7a0000'], emoji: '🥩' },
  african:         { grad: ['#3b1a00', '#7a3800'], emoji: '🌍' },
};
const DEFAULT_THEME = { grad: ['#161b22', '#1c2840'], emoji: '🍽️' };

const TITLE_EMOJI_MAP = [
  [['soupe', 'soup', 'bouillon', 'potage', 'velouté'],         '🍲'],
  [['salade', 'salad'],                                         '🥗'],
  [['tarte', 'quiche', 'pie'],                                  '🥧'],
  [['cake', 'gâteau', 'brownie', 'cookie', 'biscuit'],         '🎂'],
  [['risotto', 'riz', 'rice', 'pilaf', 'biryani'],             '🍚'],
  [['pâtes', 'pasta', 'spaghetti', 'tagliatelle', 'gnocchi'], '🍝'],
  [['pizza'],                                                   '🍕'],
  [['burger', 'sandwich'],                                      '🥪'],
  [['curry', 'massaman', 'korma', 'tikka'],                    '🍛'],
  [['smoothie', 'jus', 'juice'],                               '🥤'],
  [['glace', 'sorbet', 'ice cream'],                           '🍦'],
  [['tofu', 'tempeh', 'seitan'],                               '🌿'],
  [['hummus', 'houmous'],                                       '🧆'],
  [['wok', 'stir-fry', 'poêlée'],                              '🥡'],
  [['pancake', 'crêpe', 'waffle', 'gaufre'],                   '🥞'],
  [['pain', 'bread', 'brioche', 'naan', 'focaccia'],           '🍞'],
  [['chocolat', 'chocolate'],                                   '🍫'],
  [['mango', 'mangue', 'tropical'],                             '🥭'],
  [['avocat', 'avocado', 'guacamole'],                         '🥑'],
  [['lentil', 'lentille', 'dal', 'dahl'],                      '🫘'],
];

export function getRecipeTheme(recipe) {
  const cuisine = (recipe.origin?.cuisine || '').toLowerCase();
  const theme   = CUISINE_THEME[cuisine] || DEFAULT_THEME;
  const title   = (recipe.titles?.fr || recipe.title_fr || '').toLowerCase();
  let emoji     = theme.emoji;
  for (const [keywords, e] of TITLE_EMOJI_MAP) {
    if (keywords.some(k => title.includes(k))) { emoji = e; break; }
  }
  return { grad: theme.grad, emoji };
}

// ── Mapping sous-filtre → badge prioritaire ──────────────────────────────────
// nutriKey : clés réelles dans recipe.nutrition (calories, proteins, carbs, fiber)
// healthKey : clé dans recipe.health_scores pour confirmer la présence
// Pour les micronutriments non disponibles en valeur brute → nutriKey: null

const SUB_FILTER_BADGE_MAP = {
  // Protéines — recipe.nutrition.proteins
  protein_high:       { id: 'high_protein', label: 'Protéiné',          symbol: '💪', cls: 'badge-health', nutriKey: 'proteins',  unit: 'g prot.',    healthKey: 'high_protein' },
  protein_source:     { id: 'high_protein', label: 'Protéiné',          symbol: '💪', cls: 'badge-health', nutriKey: 'proteins',  unit: 'g prot.',    healthKey: 'high_protein' },
  // Fibres — recipe.nutrition.fiber
  fiber_high:         { id: 'high_fiber',   label: 'Fibres',            symbol: '🫘', cls: 'badge-health', nutriKey: 'fiber',     unit: 'g fibres',   healthKey: 'high_fiber' },
  fiber_source:       { id: 'high_fiber',   label: 'Fibres',            symbol: '🫘', cls: 'badge-health', nutriKey: 'fiber',     unit: 'g fibres',   healthKey: 'high_fiber' },
  // Poids — recipe.nutrition.calories
  low_calorie:        { id: 'low_calorie',  label: 'Léger',             symbol: '⚖️', cls: 'badge-health', nutriKey: 'calories',  unit: 'kcal',       healthKey: 'low_calorie' },
  low_sugar:          { id: 'low_sugar',    label: 'Faible sucre',      symbol: '🍬', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  low_sodium:         { id: 'low_sodium',   label: 'Faible sel',        symbol: '🧂', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  // Énergie — recipe.nutrition.calories
  energisant:         { id: 'energisant',   label: 'Énergisant',        symbol: '⚡', cls: 'badge-health', nutriKey: 'calories',  unit: 'kcal',       healthKey: null },
  high_carb_complex:  { id: 'high_carb',    label: 'Glucides complexes',symbol: '🌾', cls: 'badge-health', nutriKey: 'carbs',     unit: 'g glucides', healthKey: null },
  sustained_energy:   { id: 'sustained',    label: 'Énergie durable',   symbol: '⚡', cls: 'badge-health', nutriKey: 'calories',  unit: 'kcal',       healthKey: null },
  // IG — pas de valeur brute disponible
  low_ig:             { id: 'diabetes',     label: 'IG bas',            symbol: '🩸', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: 'low_ig' },
  moderate_ig:        { id: 'moderate_ig',  label: 'IG modéré',         symbol: '🩸', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  // Oméga-3 — pas de valeur brute disponible sur la card
  omega3_ala:         { id: 'omega3',       label: 'Oméga-3 ALA',       symbol: '🐟', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: 'omega3' },
  omega3_epa_dha:     { id: 'omega3',       label: 'EPA/DHA',           symbol: '🐟', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: 'omega3' },
  // Vitamines — pas de valeur brute sur la card
  vitamin_c:          { id: 'vitamin_c',    label: 'Riche en vit. C',   symbol: '🍊', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  vitamin_d:          { id: 'vitamin_d',    label: 'Riche en vit. D',   symbol: '☀️', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  folate:             { id: 'folate',       label: 'Riche en folate',   symbol: '🧬', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  // Minéraux — pas de valeur brute sur la card
  calcium:            { id: 'calcium',      label: 'Riche en calcium',  symbol: '🦴', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  iron:               { id: 'iron',         label: 'Riche en fer',      symbol: '🩸', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  magnesium:          { id: 'magnesium',    label: 'Riche en magnésium',symbol: '🌿', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  potassium:          { id: 'potassium',    label: 'Riche en potassium',symbol: '🍌', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  zinc:               { id: 'zinc',         label: 'Riche en zinc',     symbol: '⚡', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  // Antioxydants — pas de valeur brute
  antioxidant_rich:   { id: 'antioxidant',  label: 'Antioxydants',      symbol: '🌟', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: 'antioxidant_rich' },
  high_polyphenol:    { id: 'polyphenol',   label: 'Polyphénols',       symbol: '🌟', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
  high_beta_carotene: { id: 'beta_carotene',label: 'Bêta-carotène',     symbol: '🥕', cls: 'badge-health', nutriKey: null,        unit: null,         healthKey: null },
};

const HEALTH_GROUP_DEFAULT_SUB = {
  high_protein: 'protein_high',
  high_fiber:   'fiber_high',
  poids:        'low_calorie',
  energie:      'energisant',
  low_ig:       'low_ig',
  omega3:       'omega3_ala',
  vitamins:     'vitamin_c',
  minerals:     'calcium',
  antioxidant:  'antioxidant_rich',
};

// Récupère la valeur depuis recipe.nutrition avec les vraies clés de l'API
function getNutrientValue(recipe, nutriKey) {
  if (!nutriKey) return null;
  const n = recipe.nutrition || {};
  // Les clés réelles : calories, proteins, carbs, fat, fiber
  const val = n[nutriKey] ?? null;
  if (val == null || isNaN(val)) return null;
  const rounded = Math.round(val * 10) / 10;
  return rounded > 0 ? rounded : null;
}

// ── Badges colorés par catégorie ─────────────────────────────────────────────

export function getRecipeBadges(recipe, activeHealthFilters = new Set(), activeSubFilters = new Set()) {
  const badges = [];
  const flags  = recipe.diet_flags    || {};
  const health = recipe.health_scores || {};
  const tags   = recipe.tags?.diet    || [];

  // ── Badges prioritaires : filtres actifs en premier ──────────────────────
  const priorityBadgeIds = new Set();

  for (const sf of activeSubFilters) {
    const def = SUB_FILTER_BADGE_MAP[sf];
    if (!def) continue;
    const val = getNutrientValue(recipe, def.nutriKey);
    const labelWithVal = val != null ? `${val} ${def.unit}` : def.label;
    badges.push({ ...def, label: labelWithVal, priority: true });
    priorityBadgeIds.add(def.id);
  }

  for (const hf of activeHealthFilters) {
    const defaultSub = HEALTH_GROUP_DEFAULT_SUB[hf];
    if (!defaultSub) continue;
    const def = SUB_FILTER_BADGE_MAP[defaultSub];
    if (!def || priorityBadgeIds.has(def.id)) continue;
    const val = getNutrientValue(recipe, def.nutriKey);
    const labelWithVal = val != null ? `${val} ${def.unit}` : def.label;
    badges.push({ ...def, label: labelWithVal, priority: true });
    priorityBadgeIds.add(def.id);
  }

  // ── Badges standards ─────────────────────────────────────────────────────

  const enriched   = recipe.diet_flags_enriched  || {};
  const highlights = recipe.nutrition_highlights || {};

  // Régime → vert
  if (flags.vegan)
    badges.push({ id: 'vegan',        label: 'Vegan',                   symbol: '🌿', cls: 'badge-diet' });
  if (enriched.egg_free === true)
    badges.push({ id: 'egg_free',     label: 'Sans Œufs',               symbol: '🥚', cls: 'badge-diet' });
  if (enriched.dairy_free === true)
    badges.push({ id: 'dairy_free',   label: 'Sans Produits Laitiers',  symbol: '🧀', cls: 'badge-diet' });
  if (enriched.soy_free === true)
    badges.push({ id: 'soy_free',     label: 'Sans Soja',               symbol: '🫘', cls: 'badge-diet' });

  // Allergènes → amber
  if (flags.gluten_free  || tags.includes('gluten_free'))
    badges.push({ id: 'gluten_free',     label: 'Sans Gluten',    symbol: '🌾', cls: 'badge-allergen' });
  if (flags.lactose_free || tags.includes('lactose_free'))
    badges.push({ id: 'lactose_free',    label: 'Sans Lactose',   symbol: '🥛', cls: 'badge-allergen' });
  if (flags.nut_free     || tags.includes('nut_free'))
    badges.push({ id: 'nut_free',        label: 'Sans Noix',      symbol: '🥜', cls: 'badge-allergen' });
  if (enriched.fermented_free === true)
    badges.push({ id: 'fermented_free',  label: 'Sans Fermentés', symbol: '🧪', cls: 'badge-allergen' });

  // Santé → bleu (non dupliqués)
  if (!priorityBadgeIds.has('high_protein') && (health.high_protein || tags.includes('high_protein')))
    badges.push({ id: 'high_protein', label: 'Protéiné',    symbol: '💪', cls: 'badge-health' });
  if (!priorityBadgeIds.has('high_fiber') && (health.high_fiber || tags.includes('high_fiber')))
    badges.push({ id: 'high_fiber',   label: 'Fibres',      symbol: '🫘', cls: 'badge-health' });
  if (!priorityBadgeIds.has('low_calorie') && (health.low_calorie || tags.includes('low_calorie')))
    badges.push({ id: 'low_calorie',  label: 'Léger',       symbol: '⚖️', cls: 'badge-health' });
  if (health.fodmap_level === 'low' || tags.includes('low_fodmap'))
    badges.push({ id: 'low_fodmap',   label: 'Low FODMAP',  symbol: '🍏', cls: 'badge-health' });
  if (!priorityBadgeIds.has('diabetes') && (health.low_ig || health.diabetes_friendly || tags.includes('diabetes_friendly') || tags.includes('low_ig')))
    badges.push({ id: 'diabetes',     label: 'Low IG',      symbol: '🩸', cls: 'badge-health' });
  if (highlights.vitamins)
    badges.push({ id: 'vitamins',     label: 'Vitamines',   symbol: '🍊', cls: 'badge-health' });
  if (highlights.minerals)
    badges.push({ id: 'minerals',     label: 'Minéraux',    symbol: '🦴', cls: 'badge-health' });
  if (!priorityBadgeIds.has('omega3') && highlights.omega3)
    badges.push({ id: 'omega3',       label: 'Oméga-3',     symbol: '🐟', cls: 'badge-health' });
  if (!priorityBadgeIds.has('antioxidant') && highlights.antioxidant)
    badges.push({ id: 'antioxidant',  label: 'Antioxydants', symbol: '🌟', cls: 'badge-health' });
  if (highlights.low_sugar || highlights.low_sodium)
    badges.push({ id: 'low_sugar',    label: 'Faible sucre/sel', symbol: '🧂', cls: 'badge-health' });

  // Holistique → violet
  const holisticTags = recipe.tags?.holistic || [];
  const cyclePhases  = { menstrual: 'Menstruelle', follicular: 'Folliculaire', ovulatory: 'Ovulatoire', luteal: 'Lutéale' };
  for (const [key, label] of Object.entries(cyclePhases)) {
    if (holisticTags.includes(key))
      badges.push({ id: key, label, symbol: '🌙', cls: 'badge-holistic' });
  }
  const astroMap = { astro_eau: 'Eau 💧', astro_feu: 'Feu 🔥', astro_air: 'Air 🌬️', astro_terre: 'Terre 🌿' };
  for (const [key, label] of Object.entries(astroMap)) {
    if (holisticTags.includes(key))
      badges.push({ id: key, label, symbol: '✨', cls: 'badge-holistic' });
  }

  return badges;
}

// ── AJR de référence (UE Règl. 1169/2011 / ANSES) ───────────────────────────
// Unités : g pour macros/fibres, mg pour minéraux/vitamines sauf vitD (µg)

const NUTR_AJR = {
  protein:   50,   // g
  fiber:     25,   // g
  iron:      14,   // mg
  calcium:   800,  // mg
  zinc:      10,   // mg
  vitamin_c: 80,   // mg
  vitamin_d: 5,    // µg
  magnesium: 375,  // mg
  sodium:    2300, // mg  (sel ≈ sodium × 2.5 — si recipe.nutrition.salt en g, convertir)
};

// Construit une map { nutrient: pct_ajr } depuis toutes les sources disponibles.
// Priorité : recipe._nutrition[key].pct_ajr → calculé depuis recipe.nutrition valeurs brutes.
function buildNutrPctMap(recipe) {
  const map = {};

  // 1. Données précalculées (_nutrition avec pct_ajr) — format haut de gamme
  const pre = recipe._nutrition;
  if (pre && typeof pre === 'object') {
    for (const [key, ajr] of Object.entries(NUTR_AJR)) {
      const pct = pre[key]?.pct_ajr;
      if (pct != null && !isNaN(pct)) map[key] = pct;
    }
  }

  // 2. Fallback : calculer depuis recipe.nutrition (valeurs brutes g/mg)
  const raw = recipe.nutrition || {};
  for (const [key, ajr] of Object.entries(NUTR_AJR)) {
    if (map[key] != null) continue; // déjà rempli via _nutrition

    // Alias courants : proteins, fibers, vitaminc…
    const val = raw[key] ?? raw[key + 's'] ?? null;

    if (val != null && !isNaN(val) && val > 0) {
      map[key] = Math.round((val / ajr) * 100);
    } else if (key === 'sodium' && raw.salt != null && raw.salt > 0) {
      // sel (g) → sodium (mg) : 1 g sel ≈ 400 mg sodium
      map[key] = Math.round((raw.salt * 400) / ajr * 100);
    }
  }

  return Object.keys(map).length > 0 ? map : null;
}

// ── Score NRF8v (0–100) basé sur les % AJR de 8 nutriments ──────────────────

const NRF_WEIGHTS = {
  iron: 2.0, vitamin_d: 2.0, calcium: 2.0, zinc: 2.0,
  fiber: 1.5, vitamin_c: 1.5, magnesium: 1.5, protein: 1.0,
};
const NRF_TOTAL_WEIGHT = Object.values(NRF_WEIGHTS).reduce((s, w) => s + w, 0);

const FILTER_NUTRIENT_MAP = {
  protein_high: 'protein', protein_source: 'protein',
  fiber_high: 'fiber', fiber_source: 'fiber',
  calcium: 'calcium', iron: 'iron', magnesium: 'magnesium', zinc: 'zinc',
  vitamin_c: 'vitamin_c', vitamin_d: 'vitamin_d',
};
const HEALTH_NUTRIENT_MAP = { high_protein: 'protein', high_fiber: 'fiber' };

export function computeNRFScore(recipe, activeHealthFilters = new Set(), activeSubFilters = new Set()) {
  const pct = buildNutrPctMap(recipe);
  if (!pct) return null;

  let weightedSum = 0;
  let hasAnyData  = false;
  for (const [key, weight] of Object.entries(NRF_WEIGHTS)) {
    const p = pct[key];
    if (p != null && !isNaN(p)) {
      weightedSum += Math.min(p, 100) * weight;
      hasAnyData = true;
    }
  }
  if (!hasAnyData) return null;

  // Score brut 0-100 : en théorie 100 si 100% AJR pour chaque nutriment,
  // en pratique ~25-45 pour les meilleurs plats réels (pas de repas qui couvre
  // 100% AJR de tous les micronutriments en une portion).
  // → on applique ×2 pour que l'échelle soit lisible (meilleurs plats → 75-95).
  let score = (weightedSum / NRF_TOTAL_WEIGHT) * 2;

  // Pénalité sodium élevé (conservée, elle reste faible face au rescaling)
  if ((pct.sodium ?? 0) > 80) score -= 8;

  // Bonus régime végétal
  const flags = recipe.diet_flags || {};
  const tags  = recipe.tags?.diet || [];
  if (flags.vegan || tags.includes('vegan')) score += 10;
  else if (flags.vegetarian || tags.includes('vegetarian') || flags.lacto_vegetarian) score += 5;

  // Bonus/malus filtres santé actifs
  for (const sf of activeSubFilters) {
    const nk = FILTER_NUTRIENT_MAP[sf];
    if (nk && pct[nk] != null)
      score += pct[nk] >= 50 ? 3 : -3;
  }
  for (const hf of activeHealthFilters) {
    const nk = HEALTH_NUTRIENT_MAP[hf];
    if (nk && pct[nk] != null)
      score += pct[nk] >= 50 ? 3 : -3;
  }

  return Math.max(0, Math.min(100, Math.round(score)));
}

// ── Score ALIM Végé-centré (0–100) ──────────────────────────────────────────
//
// Système propre à ALIM v6 — pas un score officiel.
// Objectif : refléter la qualité nutritionnelle végé d'une recette.
//
// Critères et pondération max :
//  1. Régime végétal          → 0-28 pts  (vegan +28, végé +18)
//  2. Protéines               → 0-22 pts  (flag high_protein OU g/portion)
//  3. Fibres                  → 0-18 pts  (flag high_fiber OU g/portion)
//  4. Santé — flags cumulés   → 0-18 pts  (IG bas, antioxydants, oméga-3…)
//  5. Équilibre calorique     → 0-8  pts
//  6. Micronutriments AJR     → 0-12 pts  (bonus si _nutrition disponible)
// Pénalités : sodium > 90 % AJR (-12), > 60 % (-6), kcal > 800 (-5)
//
// Étalonnage indicatif :
//   85-100 → Exceptionnel (vegan dense + tous flags + micros)
//   70-85  → Excellent    (vegan/végé + bons macros + quelques flags)
//   55-70  → Très bien    (végé équilibré, bons macros)
//   35-55  → Correct      (omnivore nutritif ou végé léger)
//   0-35   → Limité       (peu de données ou recette peu végé-friendly)

export function computeAlimScore(recipe, { isVeganFilter = false } = {}) {
  const flags  = recipe.diet_flags           || {};
  const health = recipe.health_scores        || {};
  const tags   = recipe.tags?.diet           || [];
  const nutr   = recipe.nutrition            || {};
  const hi     = recipe.nutrition_highlights || {};
  // pctMap : % AJR calculés depuis _nutrition ou recipe.nutrition brut
  const pctMap = buildNutrPctMap(recipe);

  let score = 0;
  // Fallback : health_scores contient protein_g / fiber_g / kcal (calculés par
  // _hs côté backend) — disponibles sur les pages liste où recipe.nutrition n'est pas envoyé.
  const proteins = nutr.proteins ?? nutr.protein ?? health.protein_g ?? 0;
  const fiber    = nutr.fiber ?? health.fiber_g ?? 0;
  const kcal     = nutr.calories ?? nutr.kcal_per_serving ?? health.kcal ?? 0;

  // ── 1. Régime végétal (0-28) ──────────────────────────────────────────────
  const isVegan = flags.vegan || tags.includes('vegan');
  const isVege  = flags.vegetarian || tags.includes('vegetarian') || flags.lacto_vegetarian;
  if (isVegan)      score += 28;
  else if (isVege)  score += 18;

  // ── 2. Protéines (0-22) — flag prioritaire, sinon grammes, sinon % AJR ──
  const pp = pctMap?.protein ?? 0;
  if (health.high_protein || tags.includes('high_protein')) {
    score += 22;
  } else if (proteins >= 20 || pp >= 80) { score += 22; }
  else if (proteins >= 15 || pp >= 60)   { score += 17; }
  else if (proteins >= 10 || pp >= 40)   { score += 12; }
  else if (proteins >= 7  || pp >= 28)   { score += 8;  }
  else if (proteins >= 4  || pp >= 16)   { score += 4;  }
  else if (proteins >= 2  || pp >= 8)    { score += 2;  }

  // ── 3. Fibres (0-18) — flag prioritaire, sinon grammes, sinon % AJR ─────
  const fp = pctMap?.fiber ?? 0;
  if (health.high_fiber || tags.includes('high_fiber')) {
    score += 18;
  } else if (fiber >= 10 || fp >= 80) { score += 18; }
  else if (fiber >= 7  || fp >= 56)   { score += 14; }
  else if (fiber >= 5  || fp >= 40)   { score += 10; }
  else if (fiber >= 3  || fp >= 24)   { score += 6;  }
  else if (fiber >= 1.5|| fp >= 12)   { score += 3;  }

  // ── 4. Qualité santé — flags cumulatifs (plafonné à 18) ──────────────────
  let hPts = 0;
  // health.glycemic_category est calculé par _hs() côté backend (low/moderate/high)
  const glyCat = health.glycemic_category || '';
  if (health.low_ig || tags.includes('low_ig') || health.diabetes_friendly || glyCat === 'low') hPts += 7;
  else if (health.moderate_ig || glyCat === 'moderate') hPts += 3;
  if (hi.antioxidant || health.antioxidant_rich) hPts += 6;
  if (hi.omega3 || health.source_omega3 || health.omega3)  hPts += 5;
  if (hi.vitamins  || health.vitamins)  hPts += 4;
  if (hi.minerals  || health.minerals)  hPts += 3;
  score += Math.min(18, hPts);

  // ── 5. Équilibre calorique (0-8) ─────────────────────────────────────────
  if      (health.low_calorie || (kcal > 0 && kcal < 300)) score += 8;
  else if (kcal > 0 && kcal < 400) score += 6;
  else if (kcal > 0 && kcal < 550) score += 3;
  else if (kcal > 0 && kcal < 700) score += 1;

  // ── 6. Micronutriments AJR (0-12 — calculés depuis pctMap) ──────────────
  if (pctMap) {
    const ip = pctMap.iron      ?? 0;
    const vp = pctMap.vitamin_c ?? 0;
    const cp = pctMap.calcium   ?? 0;
    const mp = pctMap.magnesium ?? 0;
    if (ip >= 30) score += 4; else if (ip >= 15) score += 2; else if (ip >= 5) score += 1;
    if (vp >= 30) score += 3; else if (vp >= 15) score += 1;
    if (cp >= 25) score += 3; else if (cp >= 12) score += 1;
    if (mp >= 25) score += 2; else if (mp >= 12) score += 1;
  }

  // ── Bonus filtre vegan actif ──────────────────────────────────────────────
  if (isVeganFilter && isVegan) score += 3;

  // ── Pénalités ─────────────────────────────────────────────────────────────
  const sodiumPct = pctMap?.sodium ?? 0;
  if      (sodiumPct > 90) score -= 12;
  else if (sodiumPct > 60) score -= 6;
  if      (kcal > 800)             score -= 5;
  else if (kcal > 650 && kcal > 0) score -= 2;

  return Math.max(0, Math.min(100, Math.round(score)));
}

// ── Utilitaire slug → chemin image locale ─────────────────────────────────────

function slugify(text) {
  return (text || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLowerCase().trim()
    .replace(/[\s_/\\]+/g, '-')
    .replace(/[^a-z0-9-]/g, '')
    .replace(/-+/g, '-').replace(/^-|-$/g, '');
}

export function getRecipeImageUrl(recipe) {
  const name = recipe?.titles?.fr || recipe?.titles?.en || recipe?.titles?.original || '';
  if (!name) return null;
  return `/images/recipes/${slugify(name)}.jpg`;
}

// ── RecipeVisual — image réelle ou gradient fallback ─────────────────────────

export function RecipeVisual({ recipe, size = 'card', score = null, alimScore = null }) {
  // Priorité : image_url API → image locale slugifiée → gradient emoji
  const imgUrl = recipe.image_url || recipe.image || getRecipeImageUrl(recipe);
  const [imgFailed, setImgFailed] = useState(false);
  const { grad, emoji } = getRecipeTheme(recipe);
  const [c1, c2] = grad;
  const isLarge  = size === 'large';
  const height   = isLarge ? '280px' : '200px';
  const emojiSz  = isLarge ? '64px' : '48px';
  const showReal = imgUrl && !imgFailed;

  return (
    <div className="recipe-image" style={{ height }}>
      {showReal ? (
        <img
          src={imgUrl}
          alt={recipe.titles?.fr || recipe.title_fr || 'Recette'}
          className="recipe-img-real"
          onError={() => setImgFailed(true)}
        />
      ) : (
        <>
          <div style={{
            position: 'absolute', inset: 0,
            background: `linear-gradient(135deg, ${c1} 0%, ${c2} 100%)`,
          }} />
          <div style={{
            position: 'absolute', inset: 0,
            background: `radial-gradient(circle at 30% 70%, ${c2}60 0%, transparent 60%),
                         radial-gradient(circle at 80% 20%, ${c1}80 0%, transparent 50%)`,
          }} />
          <div style={{
            position: 'absolute', inset: 0,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: emojiSz,
            filter: 'drop-shadow(0 4px 12px rgba(0,0,0,0.5))',
            userSelect: 'none',
          }}>
            {emoji}
          </div>
        </>
      )}

      {recipe.origin?.cuisine && (
        <div className="recipe-badge-origin" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{
            width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
            background: getCuisineColor(recipe),
            display: 'inline-block',
          }} />
          {CUISINE_LABEL_FR[(recipe.origin.cuisine || '').toLowerCase()] || recipe.origin.cuisine.replace(/_/g, ' ')}
        </div>
      )}
      {(() => {
        const d = recipe.difficulty_level || recipe.difficulty;
        if (!d) return null;
        const lvl   = d === 'easy'   || d === 'facile'        ? 1
                    : d === 'medium' || d === 'intermédiaire'  ? 2
                    : d === 'hard'   || d === 'difficile'      ? 3 : null;
        if (!lvl) return null;
        const color = lvl === 1 ? '#1D9E75' : lvl === 2 ? '#E07B39' : '#C0392B';
        const label = lvl === 1 ? 'Facile'  : lvl === 2 ? 'Moyen'   : 'Difficile';
        return (
          <div className="recipe-badge-difficulty" title={label} aria-label={`Difficulté : ${label}`}>
            <span style={{
              width: 8, height: 8, borderRadius: '50%',
              background: color,
              display: 'inline-block',
              boxShadow: `0 0 0 2px rgba(0,0,0,0.25)`,
            }} />
            <span style={{ fontSize: 11, fontWeight: 600, color: '#fff', lineHeight: 1 }}>{label}</span>
          </div>
        );
      })()}
      {alimScore !== null && alimScore > 0 && (
        <div className="recipe-alim-score-pill">
          <span style={{ fontSize: 13, lineHeight: 1 }}>⭐</span>
          <span>
            {alimScore}
            <span style={{ fontSize: 9, opacity: 0.75, marginLeft: 1 }}>/100</span>
          </span>
        </div>
      )}

      <div className="recipe-hover-overlay">
        <span className="recipe-cta">Voir la recette →</span>
      </div>
    </div>
  );
}

// ── RecipeCardSkeleton — affiché pendant le fetch API ────────────────────────

/**
 * Remplace une RecipeCard pendant le chargement.
 * Structure identique à la vraie carte : image 200px + contenu (titre, meta, badges).
 * Usage :
 *   {loading
 *     ? Array.from({ length: 6 }, (_, i) => <RecipeCardSkeleton key={i} />)
 *     : recipes.map(r => <RecipeCard key={r.id} recipe={r} />)
 *   }
 */
export function RecipeCardSkeleton() {
  return (
    <article className="skeleton-card" aria-hidden="true">
      {/* Zone image */}
      <div className="skeleton skeleton-img" />

      {/* Zone contenu */}
      <div className="skeleton-content">
        {/* Titre */}
        <div className="skeleton skeleton-line skeleton-line--title" />

        {/* Méta (temps, couverts, kcal) */}
        <div className="skeleton-meta">
          <div className="skeleton skeleton-meta-item" />
          <div className="skeleton skeleton-meta-item" />
          <div className="skeleton skeleton-meta-item" />
        </div>

        {/* Badges */}
        <div className="skeleton-badges">
          <div className="skeleton skeleton-badge" />
          <div className="skeleton skeleton-badge" />
          <div className="skeleton skeleton-badge" />
        </div>

        {/* Ligne "why" optionnelle */}
        <div className="skeleton skeleton-line skeleton-line--short" />
      </div>
    </article>
  );
}

// ── BadgeMorePopover — badge +N avec bulle au survol ─────────────────────────

function BadgeMorePopover({ badges }) {
  const [open, setOpen] = useState(false);
  const timerRef = useRef(null);

  const show = () => { clearTimeout(timerRef.current); setOpen(true); };
  const hide = () => { timerRef.current = setTimeout(() => setOpen(false), 120); };

  return (
    <span
      className="badge-more-wrapper"
      style={{ position: 'relative', display: 'inline-block' }}
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      <span
        className="badge badge-more"
        aria-label={`Voir ${badges.length} tags supplémentaires`}
      >
        +{badges.length}
      </span>
      {open && (
        <div
          className="badge-more-popover"
          role="tooltip"
          onMouseEnter={show}
          onMouseLeave={hide}
          onClick={(e) => e.stopPropagation()}
        >
          {badges.map(b => (
            <span key={b.id} className={`badge ${b.cls || ''}`} style={{ margin: '2px' }}>
              <span className="badge-symbol">{b.symbol}</span>
              <span className="badge-label">{b.label}</span>
            </span>
          ))}
        </div>
      )}
    </span>
  );
}

// ── RecipeCard principal ──────────────────────────────────────────────────────

export default function RecipeCard({ recipe, activeHealthFilters = new Set(), activeSubFilters = new Set(), isVeganFilter = false }) {
  const { toggle, isFavorite } = useFavorites();
  const isFav = isFavorite(recipe.id);
  const [showPlanModal, setShowPlanModal] = useState(false);

  const alimScore = computeAlimScore(recipe, { isVeganFilter });

  const time   = recipe.total_time_min || recipe.timing?.total_expected || recipe.timing?.total_min;
  const kcal   = recipe.nutrition?.kcal_per_serving || recipe.kcal;
  const diff   = recipe.difficulty;
  const badges = getRecipeBadges(recipe, activeHealthFilters, activeSubFilters);

  const handleClick = () => navigate(`/recette/${recipe.id || recipe._id}`);

  return (
    <article
      className="recipe-card"
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && handleClick()}
    >
      <RecipeVisual recipe={recipe} size="card" alimScore={alimScore} />
      <button
        className={`recipe-fav-btn${isFav ? ' recipe-fav-btn--active' : ''}`}
        onClick={(e) => { e.stopPropagation(); toggle(recipe); }}
        aria-label={isFav ? 'Retirer des favoris' : 'Ajouter aux favoris'}
        aria-pressed={isFav}
      >
        {isFav ? '♥' : '♡'}
      </button>
      <button
        className="recipe-plan-btn"
        onClick={(e) => { e.stopPropagation(); setShowPlanModal(true); }}
        aria-label="Ajouter au planning"
        title="Ajouter au planning"
      >
        ▦
      </button>
      <button
        className="recipe-nutr-btn"
        onClick={(e) => {
          e.stopPropagation();
          // Stocker la recette avant navigation (NutritionPage monte après l'event)
          window.__alim_pending_recipe = recipe;
          window.dispatchEvent(new CustomEvent('alim:recipe-selected', { detail: recipe }));
          navigate('/nutrition');
        }}
        aria-label="Voir la nutrition"
        title="Analyse nutritionnelle"
      >
        ◉
      </button>
      {showPlanModal && (
        <AddToPlanModal recipe={recipe} onClose={() => setShowPlanModal(false)} />
      )}

      <div className="recipe-content">
        <h3 className="recipe-title">
          {recipe.titles?.fr || recipe.title_fr || 'Recette'}
        </h3>

        <div className="recipe-meta">
          {time && (
            <span className="recipe-meta-item">
              <span className="recipe-meta-icon">⏱</span> {time} min
            </span>
          )}
          <span className="recipe-meta-item">
            <span className="recipe-meta-icon">🍽</span> {recipe.servings || 4} pers.
          </span>
          {kcal && (
            <span className="recipe-meta-item">
              <span className="recipe-meta-icon">🔥</span> {Math.round(kcal)} kcal
            </span>
          )}
          {diff && (() => {
              const lvl    = typeof diff === 'number' ? diff
                           : diff === 'easy'   || diff === 'facile'        ? 1
                           : diff === 'medium' || diff === 'intermédiaire' ? 2
                           : diff === 'hard'   || diff === 'difficile'     ? 3 : null;
              if (!lvl) return null;
              const color  = lvl === 1 ? '#1D9E75' : lvl === 2 ? '#E07B39' : '#C0392B';
              const dlabel = lvl === 1 ? 'Facile' : lvl === 2 ? 'Intermédiaire' : 'Difficile';
              return (
                <span className="recipe-meta-item recipe-difficulty" title={dlabel} style={{ display: 'flex', alignItems: 'center', gap: 4, marginLeft: 'auto' }}>
                  {[1,2,3].map(i => (
                    <span key={i} style={{
                      width: 7, height: 7, borderRadius: '50%',
                      background: i <= lvl ? color : 'currentColor',
                      opacity: i <= lvl ? 1 : 0.2,
                      display: 'inline-block',
                    }} />
                  ))}
                </span>
              );
            })()}
        </div>

        {badges.length > 0 && (
          <div className="badges">
            {badges.slice(0, 3).map(b => (
              <span key={b.id} className={`badge ${b.cls || ''}`} title={b.label}>
                <span className="badge-symbol">{b.symbol}</span>
                <span className="badge-label">{b.label}</span>
              </span>
            ))}
            {badges.length > 3 && (
              <BadgeMorePopover badges={badges.slice(3)} />
            )}
          </div>
        )}

        {recipe._why && (
          <p className="recipe-why">{recipe._why}</p>
        )}

        {recipe.completeness !== undefined && (
          <div className="recipe-completeness">
            <div className="recipe-completeness-bar"
              style={{ width: `${Math.round(recipe.completeness * 100)}%` }} />
            <span className="recipe-completeness-label">
              {Math.round(recipe.completeness * 100)}% dans mon frigo
            </span>
          </div>
        )}
      </div>
    </article>
  );
}
