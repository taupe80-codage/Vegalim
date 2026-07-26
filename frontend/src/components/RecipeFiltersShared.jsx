/**
 * RecipeFiltersShared.jsx
 * Source de vérité unique pour tout le système de filtres recette.
 * Utilisé par : HomePage, CyclePage, AstroPage, CycleAstroPage.
 */

import { useState, useRef } from 'react';
import { DISH_OPTIONS } from '../constants';

export { DISH_OPTIONS };

// ── Constantes des filtres ────────────────────────────────────────────────────

export const DIET_OPTIONS = [
  { value: 'vegan', label: '🌿 Vegan' },
];

export const DIET_EXTRA_OPTIONS = [
  { value: 'low_sugar',  label: '🚫🍬 Sans sucre' },
  { value: 'low_sodium', label: '🚫🧂 Sans sel' },
];

export const SEASON_OPTIONS = [
  { value: 'spring', label: '🌸 Printemps' },
  { value: 'summer', label: '☀️ Été' },
  { value: 'autumn', label: '🍂 Automne' },
  { value: 'winter', label: '❄️ Hiver' },
];

export const DIFFICULTY_OPTIONS = [
  { value: 'easy',   label: '🟢 Facile' },
  { value: 'medium', label: '🟡 Moyen' },
  { value: 'hard',   label: '🔴 Difficile' },
];

export const ORIGIN_GROUPS = [
  {
    id: 'europe', label: '🌍 Europe', simple: false,
    children: [
      {
        value: 'french', label: '🇫🇷 Française',
        children: [
          { value: 'french_provencal', label: 'Provençale' },
          { value: 'french_alsatian',  label: 'Alsacienne' },
        ],
      },
      { value: 'italian',   label: 'Italienne' },
      { value: 'spanish',   label: 'Espagnole' },
      { value: 'greek',     label: 'Grecque' },
      { value: 'german',    label: 'Allemande' },
      { value: 'polish',    label: 'Polonaise' },
      { value: 'swiss',     label: 'Suisse' },
      { value: 'bulgarian', label: 'Bulgare' },
      { value: 'slovak',    label: 'Slovaque' },
      { value: 'croatian',  label: 'Croate' },
      { value: 'georgian',  label: 'Géorgienne' },
    ],
  },
  {
    id: 'maghreb_orient', label: '🌿 Maghreb & Orient', simple: false,
    children: [
      { value: 'moroccan',  label: 'Marocaine' },
      { value: 'tunisian',  label: 'Tunisienne' },
      { value: 'egyptian',  label: 'Égyptienne' },
      { value: 'levantine', label: 'Levantine' },
      { value: 'turkish',   label: 'Turque' },
      { value: 'persian',   label: 'Persane' },
      { value: 'armenian',  label: 'Arménienne' },
      { value: 'uzbek',     label: 'Ouzbèke' },
    ],
  },
  {
    id: 'asia', label: '🌏 Asie', simple: false,
    children: [
      { value: 'japanese',    label: 'Japonaise' },
      { value: 'korean',      label: 'Coréenne' },
      { value: 'chinese',     label: 'Chinoise' },
      { value: 'thai',        label: 'Thaïlandaise' },
      { value: 'vietnamese',  label: 'Vietnamienne' },
      { value: 'indonesian',  label: 'Indonésienne' },
      { value: 'malaysian',   label: 'Malaisienne' },
      { value: 'philippine',  label: 'Philippine' },
      { value: 'indian',      label: 'Indienne' },
      { value: 'nepali',      label: 'Népalaise' },
      { value: 'sri_lankan',  label: 'Sri Lankaise' },
      { value: 'bangladeshi', label: 'Bangladaise' },
      { value: 'pakistani',   label: 'Pakistanaise' },
    ],
  },
  {
    id: 'africa', label: '🌍 Afrique', simple: false,
    children: [
      { value: 'african',      label: 'Africaine' },
      { value: 'west_african', label: "Afrique de l'Ouest" },
      { value: 'east_african', label: "Afrique de l'Est" },
      { value: 'ethiopian',    label: 'Éthiopienne' },
    ],
  },
  {
    id: 'americas', label: '🌎 Amériques', simple: false,
    children: [
      { value: 'mexican',   label: 'Mexicaine' },
      { value: 'caribbean', label: 'Caribéenne' },
      { value: 'peruvian',  label: 'Péruvienne' },
      { value: 'american',  label: 'Américaine' },
    ],
  },
];

export const ALLERGEN_OPTIONS = [
  { value: 'gluten_free',  label: '🌾 Sans Gluten' },
  { value: 'lactose_free', label: '🥛 Sans Lactose' },
  { value: 'nut_free',     label: '🥜 Sans Noix' },
  { value: 'egg_free',     label: '🥚 Sans Œufs' },
  { value: 'dairy_free',   label: '🧀 Sans Produits Laitiers' },
  { value: 'soy_free',     label: '🫘 Sans Soja' },
];

export const HEALTH_GROUPS = [
  {
    value: 'high_protein', label: '💪 Protéines',
    apiKeys: ['high_protein', 'good_source_protein'],
    subs: [
      { value: 'protein_high',   label: 'Riche (≥ 20g)',        apiKey: 'high_protein' },
      { value: 'protein_source', label: 'Bonne source (≥ 10g)', apiKey: 'good_source_protein' },
    ],
  },
  {
    value: 'high_fiber', label: '🫘 Fibres',
    apiKeys: ['high_fiber', 'good_source_fiber'],
    subs: [
      { value: 'fiber_high',   label: 'Riche (≥ 8g)',        apiKey: 'high_fiber' },
      { value: 'fiber_source', label: 'Bonne source (≥ 4g)', apiKey: 'good_source_fiber' },
    ],
  },
  {
    value: 'legerte', label: '⚡ Légèreté',
    apiKeys: ['low_calorie', 'low_sugar', 'low_sodium'],
    subs: [
      { value: 'low_calorie', label: 'Faible en calories (< 300 kcal)', apiKey: 'low_calorie' },
      { value: 'low_sugar',   label: 'Faible en sucres (< 5g)',         apiKey: 'low_sugar' },
      { value: 'low_sodium',  label: 'Faible en sodium (< 200mg)',      apiKey: 'low_sodium' },
    ],
  },
  {
    value: 'low_ig', label: '🩸 Glycémie',
    apiKeys: ['low_ig', 'moderate_ig'],
    subs: [
      { value: 'low_ig',      label: 'IG bas (< 55)',    apiKey: 'low_ig' },
      { value: 'moderate_ig', label: 'IG modéré (< 70)', apiKey: 'moderate_ig' },
    ],
  },
  {
    value: 'low_fodmap', label: '🍏 FODMAP',
    apiKeys: ['low_fodmap', 'moderate_fodmap'],
    subs: [
      { value: 'low_fodmap',      label: 'Strict low FODMAP',     apiKey: 'low_fodmap' },
      { value: 'moderate_fodmap', label: 'Modéré (low + medium)', apiKey: 'moderate_fodmap' },
    ],
  },
  {
    value: 'vitamin_c', label: '🍊 Vitamine C',
    apiKeys: ['high_vitamin_c', 'source_vitamin_c'],
    subs: [
      { value: 'vitamin_c',        label: 'Riche (≥ 27mg)',          apiKey: 'high_vitamin_c' },
      { value: 'source_vitamin_c', label: 'Bonne source (≥ 13mg)',   apiKey: 'source_vitamin_c' },
    ],
  },
  {
    value: 'minerals', label: '🦴 Minéraux',
    apiKeys: ['high_calcium', 'high_iron', 'high_magnesium', 'high_potassium', 'high_zinc'],
    subs: [
      { value: 'calcium',   label: 'Calcium',   apiKey: 'high_calcium' },
      { value: 'iron',      label: 'Fer',        apiKey: 'high_iron' },
      { value: 'magnesium', label: 'Magnésium',  apiKey: 'high_magnesium' },
      { value: 'potassium', label: 'Potassium',  apiKey: 'high_potassium' },
      { value: 'zinc',      label: 'Zinc',       apiKey: 'high_zinc' },
    ],
  },
  {
    value: 'antioxidant', label: '🌟 Antioxydants',
    apiKeys: ['antioxidant_rich'],
    subs: null,
  },
];

// ── Helpers ───────────────────────────────────────────────────────────────────

export function getGroupCuisines(group) {
  if (group.simple) return group.cuisines || [group.id];
  return group.children.map(c => c.value);
}

// ── Sub-components ────────────────────────────────────────────────────────────

export function FilterSection({ id, label, isOpen, onToggle, children, hasActive, activeChips }) {
  return (
    <div className={`filter-section${isOpen ? ' filter-section--open' : ''}${hasActive ? ' filter-section--has-active' : ''}`}>
      <button
        className="filter-section-header"
        onClick={() => onToggle(id)}
        aria-expanded={isOpen}
        aria-controls={`fsec-${id}`}
      >
        <span className="filter-section-label">{label}</span>
        {hasActive && <span className="filter-section-dot" aria-hidden="true" />}
        <span className="filter-section-chevron" aria-hidden="true">{isOpen ? '▾' : '▸'}</span>
      </button>
      {!isOpen && activeChips?.length > 0 && (
        <div className="filter-section-chips">
          {activeChips.map((chip) => (
            <button
              key={chip.value}
              className="fao-chip"
              onClick={(e) => { e.stopPropagation(); chip.onRemove(); }}
            >
              {chip.label} ×
            </button>
          ))}
        </div>
      )}
      <div id={`fsec-${id}`} className="filter-section-body" aria-hidden={!isOpen}>
        {children}
      </div>
    </div>
  );
}

export function HealthAccordion({ groups, selected, subSelected, onToggle, onSubToggle }) {
  const [openGroups, setOpenGroups] = useState(new Set());

  const toggleGroup = (id) => {
    setOpenGroups(prev => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  return (
    <div className="filter-accordion">
      {groups.map(group => {
        const hasSubs  = group.subs && group.subs.length > 0;
        const isOpen   = openGroups.has(group.value);
        const isActive = selected.has(group.value);
        const anySubOn = hasSubs && group.subs.some(s => subSelected.has(s.value));

        if (!hasSubs) {
          return (
            <button
              key={group.value}
              className={`filter-accordion-pill ${(isActive || anySubOn) ? 'filter-accordion-pill--active filter-accordion-pill--active-health' : ''}`}
              onClick={() => onToggle(group.value, false)}
              aria-pressed={isActive}
            >
              {group.label}
            </button>
          );
        }

        const activeSubChips = hasSubs && !isOpen
          ? group.subs.filter(s => subSelected.has(s.value))
          : [];

        return (
          <div key={group.value} className={`filter-accordion-group ${(isActive || anySubOn) ? 'filter-accordion-group--active' : ''}`}>
            <button
              className={`filter-accordion-header ${(isActive || anySubOn) ? 'filter-accordion-header--active' : ''}`}
              onClick={() => toggleGroup(group.value)}
              aria-expanded={isOpen}
            >
              <span className="filter-accordion-label">{group.label}</span>
              <span className={`filter-accordion-arrow ${isOpen ? 'filter-accordion-arrow--open' : ''}`}>›</span>
            </button>
            {activeSubChips.length > 0 && (
              <div className="filter-section-chips">
                {activeSubChips.map(sub => (
                  <button
                    key={sub.value}
                    className="fao-chip"
                    onClick={(e) => { e.stopPropagation(); onSubToggle(group.value, sub.value); }}
                  >
                    {sub.label} ×
                  </button>
                ))}
              </div>
            )}
            {isOpen && (
              <div className="filter-accordion-children">
                {group.subs.map(sub => {
                  const subActive = subSelected.has(sub.value);
                  return (
                    <button
                      key={sub.value}
                      className={`filter-accordion-child ${subActive ? 'filter-accordion-child--active filter-accordion-child--active-health' : ''}`}
                      onClick={() => onSubToggle(group.value, sub.value)}
                      aria-pressed={subActive}
                    >
                      {subActive ? '✓ ' : ''}{sub.label}
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// Retourne tous les values feuilles d'un groupe (pour sélection entière)
function getGroupLeafValues(group) {
  return group.children.flatMap(child =>
    child.children ? [child.value, ...child.children.map(sc => sc.value)] : [child.value]
  );
}

// Retourne les items actifs d'un groupe (pour les chips "enroulés")
function getActiveItems(group, selected) {
  const items = [];
  for (const child of group.children) {
    if (selected.has(child.value)) items.push({ value: child.value, label: child.label });
    if (child.children) {
      for (const sub of child.children) {
        if (selected.has(sub.value)) items.push({ value: sub.value, label: sub.label });
      }
    }
  }
  return items;
}

export function OriginAccordion({ groups, selected, onToggle, onBulkToggle }) {
  // Utilisation de useRef pour préserver l'état ouvert/fermé même si le composant
  // est re-rendu fréquemment (changements de origins, fetch API, etc.)
  const openGroupsRef    = useRef(new Set());
  const openSubGroupsRef = useRef(new Set());
  const [, forceRender]  = useState(0);

  const toggleGroupOpen = (id) => {
    const s = openGroupsRef.current;
    s.has(id) ? s.delete(id) : s.add(id);
    forceRender(n => n + 1);
  };

  const toggleSubGroupOpen = (val) => {
    const s = openSubGroupsRef.current;
    s.has(val) ? s.delete(val) : s.add(val);
    forceRender(n => n + 1);
  };

  const openGroups    = openGroupsRef.current;
  const openSubGroups = openSubGroupsRef.current;

  return (
    <div className="fao">
      {groups.map(group => {
        const isOpen      = openGroups.has(group.id);
        const leafValues  = getGroupLeafValues(group);
        const activeCount = leafValues.filter(v => selected.has(v)).length;
        const hasActive   = activeCount > 0;
        const allActive   = activeCount === leafValues.length;
        const activeItems = !isOpen ? getActiveItems(group, selected) : [];

        return (
          <div key={group.id} className={`fao-group${hasActive ? ' fao-group--active' : ''}`}>

            {/* ── Header : [checkbox] [label] [flèche] ── */}
            <div className="fao-header">
              <button
                className={`fao-cb${allActive ? ' fao-cb--all' : hasActive ? ' fao-cb--partial' : ''}`}
                onClick={(e) => { e.stopPropagation(); onBulkToggle(leafValues, 'toggle'); }}
                title={hasActive ? 'Tout désélectionner' : 'Tout sélectionner'}
              >{allActive ? '✓' : hasActive ? '−' : ''}</button>

              <span className="fao-lbl" onClick={() => toggleGroupOpen(group.id)}>
                {group.label}
              </span>

              <button
                className={`fao-arr${isOpen ? ' fao-arr--open' : ''}`}
                onClick={() => toggleGroupOpen(group.id)}
                aria-expanded={isOpen}
              >›</button>
            </div>

            {/* ── Chips actifs visibles quand enroulé ── */}
            {!isOpen && hasActive && (
              <div className="fao-chips">
                {activeItems.map(item => (
                  <button key={item.value} className="fao-chip" onClick={() => onToggle(item.value)}>
                    {item.label} ×
                  </button>
                ))}
              </div>
            )}

            {/* ── Enfants dépliés ── */}
            {isOpen && (
              <div className="fao-children">
                {group.children.map(child => {
                  const childActive = selected.has(child.value);
                  const hasSubs     = child.children?.length > 0;
                  const isSubOpen   = openSubGroups.has(child.value);
                  const activeSubs  = hasSubs ? child.children.filter(sc => selected.has(sc.value)).length : 0;

                  if (!hasSubs) {
                    return (
                      <button key={child.value}
                        className={`fao-item${childActive ? ' fao-item--on' : ''}`}
                        onClick={() => onToggle(child.value)}
                        aria-pressed={childActive}
                      >
                        <span className="fao-item-check">{childActive ? '✓' : ''}</span>
                        <span>{child.label}</span>
                      </button>
                    );
                  }

                  // Enfant avec sous-régions (ex: Française)
                  return (
                    <div key={child.value} className={`fao-subgrp${(childActive || activeSubs > 0) ? ' fao-subgrp--active' : ''}`}>
                      <div className="fao-subrow">
                        <button
                          className={`fao-item fao-item--parent${childActive ? ' fao-item--on' : ''}`}
                          onClick={() => onToggle(child.value)}
                          aria-pressed={childActive}
                        >
                          <span className="fao-item-check">{childActive ? '✓' : ''}</span>
                          <span>{child.label}</span>
                          {activeSubs > 0 && <span className="fao-subbadge">+{activeSubs}</span>}
                        </button>
                        <button
                          className={`fao-subarr${isSubOpen ? ' fao-subarr--open' : ''}`}
                          onClick={() => toggleSubGroupOpen(child.value)}
                          aria-expanded={isSubOpen}
                        >›</button>
                      </div>
                      {isSubOpen && (
                        <div className="fao-subs">
                          {child.children.map(sub => {
                            const subOn = selected.has(sub.value);
                            return (
                              <button key={sub.value}
                                className={`fao-item fao-item--sub${subOn ? ' fao-item--on' : ''}`}
                                onClick={() => onToggle(sub.value)}
                                aria-pressed={subOn}
                              >
                                <span className="fao-item-check">{subOn ? '✓' : ''}</span>
                                <span>{sub.label}</span>
                              </button>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ── Hook d'état des filtres ───────────────────────────────────────────────────

export function useFilterState(initial = {}) {
  const [diet,          setDiet]          = useState(initial.diet || '');
  const [dietExtras,    setDietExtras]    = useState(new Set(initial.dietExtras || []));
  const [season,        setSeason]        = useState(initial.season || '');
  const [difficulty,    setDifficulty]    = useState(initial.difficulty || '');
  const [allergens,     setAllergens]     = useState(new Set(initial.allergens || []));
  const [healthFilters, setHealthFilters] = useState(new Set(initial.healthFilters || []));
  const [subFilters,    setSubFilters]    = useState(new Set(initial.subFilters || []));
  const [dishFilters,   setDishFilters]   = useState(new Set(initial.dishFilters || []));
  const [origins,       setOrigins]       = useState(new Set(initial.origins || []));
  const [maxTime,       setMaxTime]       = useState(initial.maxTime || '');
  const [openSections,  setOpenSections]  = useState(
    () => new Set(['diet', 'restrictions', 'saison', 'dish', 'allergen', 'difficulty', 'health', 'origin'])
  );
  const [healthExpanded, setHealthExpanded] = useState(new Set());

  const _toggleSet = (setter) => (val) =>
    setter(prev => {
      const next = new Set(prev);
      next.has(val) ? next.delete(val) : next.add(val);
      return next;
    });

  const toggleAllergen  = _toggleSet(setAllergens);
  const toggleDish      = _toggleSet(setDishFilters);
  const toggleDietExtra = _toggleSet(setDietExtras);
  const toggleOrigin    = _toggleSet(setOrigins);

  const bulkToggleOrigins = (values, mode) => {
    setOrigins(prev => {
      const next = new Set(prev);
      if (mode === 'add')    values.forEach(v => next.add(v));
      if (mode === 'remove') values.forEach(v => next.delete(v));
      if (mode === 'toggle') {
        const anyOn = values.some(v => next.has(v));
        anyOn ? values.forEach(v => next.delete(v)) : values.forEach(v => next.add(v));
      }
      return next;
    });
  };

  const toggleHealth = (value, hasSubs) => {
    if (hasSubs) {
      setHealthExpanded(prev => {
        const next = new Set(prev);
        next.has(value) ? next.delete(value) : next.add(value);
        return next;
      });
    } else {
      setHealthFilters(prev => {
        const next = new Set(prev);
        next.has(value) ? next.delete(value) : next.add(value);
        return next;
      });
    }
  };

  const toggleSub = (groupValue, subValue) => {
    let newSubs;
    setSubFilters(prev => {
      const next = new Set(prev);
      next.has(subValue) ? next.delete(subValue) : next.add(subValue);
      newSubs = next;
      return next;
    });
    setHealthFilters(prev => {
      const group = HEALTH_GROUPS.find(g => g.value === groupValue);
      const anySubActive = group?.subs?.some(s => newSubs?.has(s.value));
      const next = new Set(prev);
      anySubActive ? next.add(groupValue) : next.delete(groupValue);
      return next;
    });
  };

  const toggleSection = (id) => setOpenSections(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });

  const hasActiveFilters = Boolean(
    diet || dietExtras.size > 0 || season || difficulty ||
    allergens.size > 0 || healthFilters.size > 0 || subFilters.size > 0 ||
    dishFilters.size > 0 || origins.size > 0 || maxTime
  );

  const clearAll = () => {
    setDiet('');
    setDietExtras(new Set());
    setSeason('');
    setDifficulty('');
    setAllergens(new Set());
    setHealthFilters(new Set());
    setSubFilters(new Set());
    setHealthExpanded(new Set());
    setDishFilters(new Set());
    setOrigins(new Set());
    setMaxTime('');
  };

  return {
    diet, setDiet,
    dietExtras, toggleDietExtra,
    season, setSeason,
    difficulty, setDifficulty,
    allergens, toggleAllergen,
    healthFilters, subFilters, toggleHealth, toggleSub,
    dishFilters, toggleDish,
    origins, toggleOrigin, bulkToggleOrigins,
    maxTime, setMaxTime,
    openSections, toggleSection,
    hasActiveFilters, clearAll,
    filterState: {
      diet, dietExtras, season, difficulty,
      allergens, healthFilters, subFilters,
      dishFilters, origins, maxTime,
    },
  };
}

// ── FiltersBlock — le bloc de filtres 5 colonnes ──────────────────────────────

export function FiltersBlock({
  diet, setDiet,
  dietExtras, toggleDietExtra,
  season, setSeason,
  difficulty, setDifficulty,
  allergens, toggleAllergen,
  healthFilters, subFilters, toggleHealth, toggleSub,
  dishFilters, toggleDish,
  origins, toggleOrigin, bulkToggleOrigins,
  openSections, toggleSection,
  hasActiveFilters, clearAll,
  onAnyChange,
  children,
}) {
  const wrap = (fn) => (...args) => { fn(...args); onAnyChange?.(); };

  // ── Chips actifs par section ──────────────────────────────────────────────
  const chip = (value, label, fn) => ({ value, label, onRemove: () => { fn(); onAnyChange?.(); } });

  const dietChips = diet
    ? [chip(diet, DIET_OPTIONS.find(o => o.value === diet)?.label, () => setDiet(''))]
    : [];

  const dietExtraChips = [...dietExtras].map(v =>
    chip(v, DIET_EXTRA_OPTIONS.find(o => o.value === v)?.label, () => toggleDietExtra(v))
  );

  const seasonChips = season
    ? [chip(season, SEASON_OPTIONS.find(o => o.value === season)?.label, () => setSeason(''))]
    : [];

  const dishChips = [...dishFilters].map(v =>
    chip(v, DISH_OPTIONS.find(o => o.value === v)?.label, () => toggleDish(v))
  );

  const allergenChips = [...allergens].map(v =>
    chip(v, ALLERGEN_OPTIONS.find(o => o.value === v)?.label, () => toggleAllergen(v))
  );

  const difficultyChips = difficulty
    ? [chip(difficulty, DIFFICULTY_OPTIONS.find(o => o.value === difficulty)?.label, () => setDifficulty(''))]
    : [];

  const healthChips = [
    ...[...healthFilters].map(v => {
      const g = HEALTH_GROUPS.find(g => g.value === v);
      if (!g) return null;
      // Si des sous-filtres sont actifs pour ce groupe, on affiche les sous-chips seulement
      if (g.subs?.some(s => subFilters.has(s.value))) return null;
      return chip(v, g.label, () => toggleHealth(v, false));
    }).filter(Boolean),
    ...[...subFilters].map(v => {
      for (const g of HEALTH_GROUPS) {
        const s = g.subs?.find(s => s.value === v);
        if (s) return chip(v, s.label, () => toggleSub(g.value, v));
      }
      return null;
    }).filter(Boolean),
  ];

  const _findOriginLabel = (val) => {
    for (const group of ORIGIN_GROUPS) {
      for (const child of group.children) {
        if (child.value === val) return child.label;
        if (child.children) {
          for (const sub of child.children) {
            if (sub.value === val) return sub.label;
          }
        }
      }
    }
    return val;
  };
  const originChips = [...origins].map(v =>
    chip(v, _findOriginLabel(v), () => toggleOrigin(v))
  );

  return (
    <div className="filters-block">
      <div className="filters-columns">

        {/* Colonne 1 : Régime / Restrictions / Saison */}
        <div className="filter-col">
          <FilterSection id="diet" label="Régime"
            isOpen={openSections.has('diet')} onToggle={toggleSection}
            hasActive={!!diet} activeChips={dietChips}
          >
            <div className="filter-pill-col" role="group" aria-label="Régime alimentaire">
              {DIET_OPTIONS.map(({ value, label }) => {
                const isActive = diet === value;
                return (
                  <button key={value}
                    className={`pill pill--sm pill--diet ${isActive ? 'pill--active pill--active-diet' : ''}`}
                    onClick={wrap(() => setDiet(isActive ? '' : value))}
                    aria-pressed={isActive}
                  >{label}</button>
                );
              })}
            </div>
          </FilterSection>

          <FilterSection id="restrictions" label="Restrictions"
            isOpen={openSections.has('restrictions')} onToggle={toggleSection}
            hasActive={dietExtras.size > 0} activeChips={dietExtraChips}
          >
            <div className="filter-pill-col" role="group" aria-label="Restrictions alimentaires">
              {DIET_EXTRA_OPTIONS.map(({ value, label }) => {
                const isActive = dietExtras.has(value);
                return (
                  <button key={value}
                    className={`pill pill--sm pill--diet ${isActive ? 'pill--active pill--active-diet' : ''}`}
                    onClick={wrap(() => toggleDietExtra(value))}
                    aria-pressed={isActive}
                  >{label}</button>
                );
              })}
            </div>
          </FilterSection>

          <FilterSection id="saison" label="Saison"
            isOpen={openSections.has('saison')} onToggle={toggleSection}
            hasActive={!!season} activeChips={seasonChips}
          >
            <div className="filter-pill-col" role="group" aria-label="Saison">
              {SEASON_OPTIONS.map(({ value, label }) => {
                const isActive = season === value;
                return (
                  <button key={value}
                    className={`pill pill--sm pill--season ${isActive ? 'pill--active pill--active-season' : ''}`}
                    onClick={wrap(() => setSeason(isActive ? '' : value))}
                    aria-pressed={isActive}
                  >{label}</button>
                );
              })}
            </div>
          </FilterSection>
        </div>

        {/* Colonne 2 : Type de plat */}
        <div className="filter-col">
          <FilterSection id="dish" label="Type de plat"
            isOpen={openSections.has('dish')} onToggle={toggleSection}
            hasActive={dishFilters.size > 0} activeChips={dishChips}
          >
            <div className="filter-pill-col" role="group" aria-label="Type de plat">
              {DISH_OPTIONS.map(({ value, label }) => {
                const isActive = dishFilters.has(value);
                return (
                  <button key={value}
                    className={`pill pill--sm pill--dish ${isActive ? 'pill--active pill--active-dish' : ''}`}
                    onClick={wrap(() => toggleDish(value))}
                    aria-pressed={isActive}
                  >{label}</button>
                );
              })}
            </div>
          </FilterSection>
        </div>

        {/* Colonne 3 : Allergènes / Difficulté */}
        <div className="filter-col">
          <FilterSection id="allergen" label="Allergènes"
            isOpen={openSections.has('allergen')} onToggle={toggleSection}
            hasActive={allergens.size > 0} activeChips={allergenChips}
          >
            <div className="filter-pill-col" role="group" aria-label="Allergènes">
              {ALLERGEN_OPTIONS.map(({ value, label }) => {
                const isActive = allergens.has(value);
                return (
                  <button key={value}
                    className={`pill pill--sm pill--allergen ${isActive ? 'pill--active pill--active-allergen' : ''}`}
                    onClick={wrap(() => toggleAllergen(value))}
                    aria-pressed={isActive}
                  >{label}</button>
                );
              })}
            </div>
          </FilterSection>

          <FilterSection id="difficulty" label="Difficulté"
            isOpen={openSections.has('difficulty')} onToggle={toggleSection}
            hasActive={!!difficulty} activeChips={difficultyChips}
          >
            <div className="filter-pill-col" role="group" aria-label="Difficulté">
              {DIFFICULTY_OPTIONS.map(({ value, label }) => {
                const isActive = difficulty === value;
                return (
                  <button key={value}
                    className={`pill pill--sm pill--difficulty ${isActive ? 'pill--active pill--active-difficulty' : ''}`}
                    onClick={wrap(() => setDifficulty(isActive ? '' : value))}
                    aria-pressed={isActive}
                  >{label}</button>
                );
              })}
            </div>
          </FilterSection>
        </div>

        {/* Colonne 4 : Santé */}
        <div className="filter-col">
          <FilterSection id="health" label="Santé"
            isOpen={openSections.has('health')} onToggle={toggleSection}
            hasActive={healthFilters.size > 0 || subFilters.size > 0} activeChips={healthChips}
          >
            <HealthAccordion
              groups={HEALTH_GROUPS}
              selected={healthFilters}
              subSelected={subFilters}
              onToggle={(v, hasSubs) => { toggleHealth(v, hasSubs); onAnyChange?.(); }}
              onSubToggle={(gv, sv) => { toggleSub(gv, sv); onAnyChange?.(); }}
            />
          </FilterSection>
        </div>

        {/* Colonne 5 : Origine */}
        <div className="filter-col">
          <FilterSection id="origin" label="Origine"
            isOpen={openSections.has('origin')} onToggle={toggleSection}
            hasActive={origins.size > 0} activeChips={originChips}
          >
            <OriginAccordion
              groups={ORIGIN_GROUPS}
              selected={origins}
              onToggle={wrap(toggleOrigin)}
              onBulkToggle={(values, mode) => { bulkToggleOrigins(values, mode); onAnyChange?.(); }}
            />
          </FilterSection>
        </div>
      </div>

      {/* Contenu optionnel (barre de recherche pour HomePage) */}
      {children}

      {/* Bouton effacer (pour pages sans barre de recherche) */}
      {!children && hasActiveFilters && (
        <div style={{ padding: '6px 0 0', display: 'flex', justifyContent: 'flex-end' }}>
          <button className="filters-clear" onClick={clearAll}>✕ Tout effacer</button>
        </div>
      )}
    </div>
  );
}

// ── Filtrage local (pour Cycle / Astro qui pre-chargent leurs recettes) ───────

const _LOCAL_SUB_MAP = {
  protein_high:        r => r.health_scores?.high_protein,
  protein_source:      r => r.health_scores?.good_source_protein,
  fiber_high:          r => r.health_scores?.high_fiber,
  fiber_source:        r => r.health_scores?.good_source_fiber,
  low_calorie:         r => r.health_scores?.low_calorie,
  low_sugar:           r => r.health_scores?.low_sugar,
  low_sodium:          r => r.health_scores?.low_sodium,
  low_ig:              r => r.health_scores?.glycemic_category === 'low',
  moderate_ig:         r => r.health_scores?.glycemic_category !== 'high',
  vitamin_c:           r => r.health_scores?.high_vitamin_c,
  source_vitamin_c:    r => r.health_scores?.source_vitamin_c || r.health_scores?.high_vitamin_c,
  calcium:             r => r.health_scores?.high_calcium,
  iron:                r => r.health_scores?.high_iron,
  magnesium:           r => r.health_scores?.high_magnesium,
  potassium:           r => r.health_scores?.high_potassium,
  zinc:                r => r.health_scores?.high_zinc,
  antioxidant_rich:    r => r.health_scores?.antioxidant_rich,
};

const _LOCAL_GROUP_MAP = {
  high_protein:    r => r.health_scores?.high_protein || r.health_scores?.good_source_protein,
  high_fiber:      r => r.health_scores?.high_fiber   || r.health_scores?.good_source_fiber,
  legerte:         r => r.health_scores?.low_calorie  || r.health_scores?.low_sugar || r.health_scores?.low_sodium,
  low_ig:          r => r.health_scores?.glycemic_category !== 'high',
  low_fodmap:      r => r.health_scores?.fodmap_level === 'low',
  moderate_fodmap: r => r.health_scores?.fodmap_level !== 'high',
  vitamin_c:       r => r.health_scores?.source_vitamin_c || r.health_scores?.high_vitamin_c,
  minerals:        r => r.health_scores?.high_calcium || r.health_scores?.high_iron || r.health_scores?.high_magnesium,
  antioxidant:     r => r.health_scores?.antioxidant_rich,
};

export function localFilterRecipes(recipes, { diet, dietExtras, season, difficulty, allergens, healthFilters, subFilters, dishFilters, origins, maxTime }) {
  let f = [...recipes];

  if (maxTime) {
    const mt = parseInt(maxTime);
    f = f.filter(r => (r.timing?.total_min || r.total_time_min || 999) <= mt);
  }

  if (diet === 'vegan')      f = f.filter(r => r.diet_flags?.vegan);
  if (diet === 'vegetarian') f = f.filter(r => r.diet_flags?.vegetarian);
  if (diet === 'raw_vegan')  f = f.filter(r => r.diet_flags?.raw_vegan);

  if (dietExtras.has('low_sugar'))  f = f.filter(r => r.health_scores?.low_sugar  || r.diet_flags?.low_sugar);
  if (dietExtras.has('low_sodium')) f = f.filter(r => r.health_scores?.low_sodium || r.diet_flags?.low_sodium);

  if (season) {
    f = f.filter(r => {
      const s = r.seasons || r.season;
      return Array.isArray(s) ? s.includes(season) : s === season;
    });
  }

  if (difficulty) f = f.filter(r => r.difficulty === difficulty);

  // gluten_free / lactose_free / nut_free → diet_flags est fiable (présent sur toutes les recettes)
  if (allergens.has('gluten_free'))  f = f.filter(r => r.diet_flags?.gluten_free);
  if (allergens.has('lactose_free')) f = f.filter(r => r.diet_flags?.lactose_free);
  if (allergens.has('nut_free'))     f = f.filter(r => r.diet_flags?.nut_free);

  // egg_free / dairy_free / soy_free → PAS dans diet_flags côté client ; fallback sur tags.allergens
  // Logique : exclure si tags.allergens contient l'allergène, inclure si non renseigné (pass-through)
  if (allergens.has('egg_free'))   f = f.filter(r =>
    r.diet_flags?.egg_free !== undefined
      ? r.diet_flags.egg_free
      : !(r.tags?.allergens || []).includes('eggs')
  );
  if (allergens.has('dairy_free')) f = f.filter(r =>
    r.diet_flags?.dairy_free !== undefined
      ? r.diet_flags.dairy_free
      : !(r.tags?.allergens || []).some(a => a === 'milk' || a === 'lactose')
  );
  if (allergens.has('soy_free'))   f = f.filter(r =>
    r.diet_flags?.soy_free !== undefined
      ? r.diet_flags.soy_free
      : !(r.tags?.allergens || []).includes('soy')
  );

  for (const val of subFilters) {
    const check = _LOCAL_SUB_MAP[val];
    if (check) f = f.filter(check);
  }

  for (const val of healthFilters) {
    const group = HEALTH_GROUPS.find(g => g.value === val);
    if (!group) continue;
    const hasSubSelected = group.subs?.some(s => subFilters.has(s.value));
    if (!hasSubSelected) {
      const check = _LOCAL_GROUP_MAP[val];
      if (check) f = f.filter(check);
    }
  }

  if (dishFilters.size > 0) {
    f = f.filter(r => dishFilters.has(r.dish_type));
  }

  if (origins.size > 0) {
    const groupIds = new Set(ORIGIN_GROUPS.map(g => g.id));
    const cuisineSet = new Set([...origins].flatMap(val => {
      if (groupIds.has(val)) {
        const group = ORIGIN_GROUPS.find(g => g.id === val);
        return getGroupCuisines(group);
      }
      return [val];
    }));
    f = f.filter(r => cuisineSet.has(r.origin?.cuisine));
  }

  return f;
}
