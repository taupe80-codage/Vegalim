/**
 * HomePage.jsx v6
 * Filtres partagés via RecipeFiltersShared — constants + composants dédupliqués.
 */

import { useState, useEffect, useCallback } from 'react';
import { recipes as recipesApi } from '../api';
import { navigate } from '../Router';
import RecipeCard, { RecipeCardSkeleton, getRecipeTheme, getRecipeImageUrl, CUISINE_LABEL_FR, computeAlimScore } from '../components/RecipeCard';
import { useRecentlyViewed } from '../useRecentlyViewed';
import {
  DISH_OPTIONS, DIET_OPTIONS, DIET_EXTRA_OPTIONS, SEASON_OPTIONS, DIFFICULTY_OPTIONS,
  ORIGIN_GROUPS, ALLERGEN_OPTIONS, HEALTH_GROUPS,
  getGroupCuisines, FilterSection, HealthAccordion, OriginAccordion,
} from '../components/RecipeFiltersShared';

const SORT_OPTIONS = [
  { value: 'pertinence', label: 'Pertinence' },
  { value: 'alpha',      label: 'A → Z' },
  { value: 'score',      label: 'Score ↓' },
  { value: 'time',       label: 'Temps ↑' },
];

// ── Récemment vus ─────────────────────────────────────────────────────────────

function RecentlyViewedStrip({ recent, onClear }) {
  if (!recent.length) return null;
  return (
    <section className="rv-strip" aria-label="Récemment vus">
      <div className="rv-strip-header">
        <span className="rv-strip-title">↩ Récemment vus</span>
        <button className="rv-strip-clear" onClick={onClear} aria-label="Effacer l'historique">
          Effacer
        </button>
      </div>
      <div className="rv-strip-scroll">
        {recent.map(r => {
          const { grad, emoji } = getRecipeTheme(r);
          const imgUrl = r.image_url || getRecipeImageUrl(r);
          const cuisine = (r.origin?.cuisine || '').toLowerCase();
          const cuisineLabel = CUISINE_LABEL_FR[cuisine] || cuisine.replace(/_/g, ' ');
          const title = r.title_fr || r.titles?.fr || 'Recette';
          return (
            <button
              key={r.id}
              className="rv-card"
              onClick={() => navigate(`/recette/${r.id}`)}
              title={title}
            >
              <div
                className="rv-card-img"
                style={{ background: `linear-gradient(135deg, ${grad[0]} 0%, ${grad[1]} 100%)` }}
              >
                {imgUrl ? (
                  <img
                    src={imgUrl}
                    alt=""
                    className="rv-card-img-real"
                    onError={(e) => { e.target.style.display = 'none'; }}
                  />
                ) : (
                  <span style={{ fontSize: 26, userSelect: 'none' }}>{emoji}</span>
                )}
              </div>
              <div className="rv-card-body">
                <span className="rv-card-title">{title}</span>
                {cuisineLabel && <span className="rv-card-type">{cuisineLabel}</span>}
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}

// ── HomePage ──────────────────────────────────────────────────────────────────

const HOME_FILTERS_KEY = 'alim_home_filters';

function _loadHomeFilters() {
  try {
    const raw = localStorage.getItem(HOME_FILTERS_KEY);
    if (!raw) return null;
    return JSON.parse(raw);
  } catch { return null; }
}

export default function HomePage() {
  const _saved = _loadHomeFilters();

  const [query,          setQuery]          = useState('');
  const [diet,           setDiet]           = useState(_saved?.diet || '');
  const [dietExtras,     setDietExtras]     = useState(new Set(_saved?.dietExtras || []));
  const [season,         setSeason]         = useState(_saved?.season || '');
  const [difficulty,     setDifficulty]     = useState(_saved?.difficulty || '');
  const [allergens,      setAllergens]      = useState(new Set(_saved?.allergens || []));
  const [healthFilters,  setHealthFilters]  = useState(new Set(_saved?.healthFilters || []));
  const [subFilters,     setSubFilters]     = useState(new Set(_saved?.subFilters || []));
  const [healthExpanded, setHealthExpanded] = useState(new Set());
  const [dishFilters,    setDishFilters]    = useState(new Set(_saved?.dishFilters || []));
  const [origins,        setOrigins]        = useState(new Set(_saved?.origins || []));

  const [openSections, setOpenSections] = useState(
    () => new Set(['diet', 'restrictions', 'saison', 'dish', 'allergen', 'difficulty', 'health', 'origin'])
  );
  const toggleSection = (id) => setOpenSections(prev => {
    const next = new Set(prev);
    next.has(id) ? next.delete(id) : next.add(id);
    return next;
  });
  const [sortOrder,      setSortOrder]      = useState('score');
  const [maxTime,        setMaxTime]        = useState(_saved?.maxTime || '');
  const [timeInputValue, setTimeInputValue] = useState(_saved?.maxTime || '');
  const [recipes,      setRecipes]      = useState([]);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState(null);
  const [visibleCount, setVisibleCount] = useState(18);

  useEffect(() => {
    try {
      localStorage.setItem(HOME_FILTERS_KEY, JSON.stringify({
        diet, dietExtras: [...dietExtras], season, difficulty,
        allergens: [...allergens], healthFilters: [...healthFilters],
        subFilters: [...subFilters], dishFilters: [...dishFilters],
        origins: [...origins], maxTime,
      }));
    } catch {}
  }, [diet, dietExtras, season, difficulty, allergens, healthFilters, subFilters, dishFilters, origins, maxTime]);

  const { recent, clear: clearRecent } = useRecentlyViewed();

  const toggleSet = (setter) => (val) =>
    setter(prev => {
      const next = new Set(prev);
      next.has(val) ? next.delete(val) : next.add(val);
      return next;
    });

  const toggleAllergen  = toggleSet(setAllergens);
  const toggleDish      = toggleSet(setDishFilters);
  const toggleDietExtra = toggleSet(setDietExtras);
  const toggleOrigin    = toggleSet(setOrigins);

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
    setSubFilters(prev => {
      const next = new Set(prev);
      next.has(subValue) ? next.delete(subValue) : next.add(subValue);
      return next;
    });
    setHealthFilters(prev => {
      const group = HEALTH_GROUPS.find(g => g.value === groupValue);
      const afterToggle = new Set(subFilters);
      subFilters.has(subValue) ? afterToggle.delete(subValue) : afterToggle.add(subValue);
      const anySubActive = group?.subs?.some(s => afterToggle.has(s.value));
      const next = new Set(prev);
      anySubActive ? next.add(groupValue) : next.delete(groupValue);
      return next;
    });
  };

  const hasActiveFilters = diet || dietExtras.size > 0 || season || difficulty || allergens.size > 0 || healthFilters.size > 0 || subFilters.size > 0 || dishFilters.size > 0 || origins.size > 0 || maxTime;

  const clearAllFilters = () => {
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
    setTimeInputValue('');
  };

  // ── Fetch ─────────────────────────────────────────────────────────────────

  const fetchRecipes = useCallback(async ({
    q   = query,
    d   = diet,
    de  = dietExtras,
    se  = season,
    dif = difficulty,
    al  = allergens,
    hf  = healthFilters,
    sf  = subFilters,
    df  = dishFilters,
    or  = origins,
    mt  = maxTime,
  } = {}) => {
    setLoading(true);
    setError(null);
    try {
      const payload = { query: q, limit: 200 };
      const hasFilter = q || d || de.size > 0 || se || dif || al.size > 0 || hf.size > 0 || sf.size > 0 || df.size > 0 || or.size > 0 || mt;

      if (mt) payload.max_time = parseInt(mt);

      if (d === 'vegan')      payload.filtre = 'vegan';
      if (d === 'vegetarian') payload.filtre = 'vegetarian';
      if (d === 'raw_vegan')  payload.filtre = 'raw_vegan';

      if (de.has('low_sugar'))  payload.low_sugar  = true;
      if (de.has('low_sodium')) payload.low_sodium = true;

      if (se)  payload.season     = se;
      if (dif) payload.difficulty = dif;

      if (al.has('gluten_free'))  payload.gluten_free  = true;
      if (al.has('lactose_free')) payload.lactose_free = true;
      if (al.has('nut_free'))     payload.nut_free     = true;
      if (al.has('egg_free'))     payload.egg_free     = true;
      if (al.has('dairy_free'))   payload.dairy_free   = true;
      if (al.has('soy_free'))     payload.soy_free     = true;

      // FODMAP — vérifier les sous-filtres en priorité (hf reçoit toujours la valeur groupe 'low_fodmap')
      if (sf.has('moderate_fodmap'))      payload.fodmap = 'not_high';
      else if (sf.has('low_fodmap'))      payload.fodmap = 'low';
      else if (hf.has('low_fodmap'))      payload.fodmap = 'low';
      // Glycémie — n'appliquer le fallback groupe que si aucun sous-filtre actif
      if (hf.has('low_ig') && !sf.has('low_ig') && !sf.has('moderate_ig'))
        payload.low_ig = true;
      if (hf.has('antioxidant')) payload.antioxidant_rich = true;

      const SF_MAP = {
        protein_high:    'high_protein',       protein_source:  'good_source_protein',
        fiber_high:      'high_fiber',          fiber_source:    'good_source_fiber',
        low_calorie:     'low_calorie',         low_sugar:       'low_sugar',
        low_sodium:      'low_sodium',
        low_ig:          'low_ig',              moderate_ig:     'moderate_ig',
        vitamin_c:       'high_vitamin_c',      source_vitamin_c:'source_vitamin_c',
        calcium:         'high_calcium',        iron:            'high_iron',
        magnesium:       'high_magnesium',      potassium:       'high_potassium',
        zinc:            'high_zinc',
        antioxidant_rich:'antioxidant_rich',
      };
      for (const val of sf) {
        const apiKey = SF_MAP[val];
        if (apiKey) payload[apiKey] = true;
      }

      if (hf.has('high_protein') && !sf.has('protein_high') && !sf.has('protein_source'))
        payload.high_protein = true;
      if (hf.has('high_fiber') && !sf.has('fiber_high') && !sf.has('fiber_source'))
        payload.high_fiber = true;
      if (hf.has('legerte') && !sf.has('low_calorie') && !sf.has('low_sugar') && !sf.has('low_sodium'))
        payload.low_calorie = true;
      if (hf.has('vitamin_c') && !sf.has('vitamin_c') && !sf.has('source_vitamin_c'))
        payload.high_vitamin_c = true;
      if (hf.has('minerals') && !['calcium', 'iron', 'magnesium', 'potassium', 'zinc'].some(s => sf.has(s)))
        payload.high_calcium = true;

      if (df.size > 0) payload.dish_types = [...df];

      if (or && or.size > 0) {
        const groupIds = new Set(ORIGIN_GROUPS.map(g => g.id));
        const cuisineList = [...or].flatMap(val => {
          if (groupIds.has(val)) {
            const group = ORIGIN_GROUPS.find(g => g.id === val);
            return getGroupCuisines(group);
          }
          return [val];
        });
        payload.cuisines = [...new Set(cuisineList)];
      }

      const data = hasFilter
        ? await recipesApi.search(payload)
        : await recipesApi.list({ limit: 200 });

      const results = Array.isArray(data) ? data : (data.results || data.recipes || []);
      setRecipes(results);
      setVisibleCount(18); // reset pagination à chaque nouvelle requête
    } catch (err) {
      setError(err.message || 'Erreur de connexion au backend.');
    } finally {
      setLoading(false);
    }
  }, [query, diet, dietExtras, season, difficulty, allergens, healthFilters, subFilters, dishFilters, origins, maxTime]);

  useEffect(() => { fetchRecipes({}); }, []);

  useEffect(() => {
    const t = setTimeout(() => fetchRecipes({ d: diet, de: dietExtras, se: season, dif: difficulty, al: allergens, hf: healthFilters, sf: subFilters, df: dishFilters, or: origins }), 280);
    return () => clearTimeout(t);
  }, [diet, dietExtras, season, difficulty, allergens, healthFilters, subFilters, dishFilters, origins]);

  // ── Tri local ─────────────────────────────────────────────────────────────

  let displayed = [...recipes];
  if (sortOrder === 'alpha') {
    displayed.sort((a, b) =>
      (a.titles?.fr || a.title_fr || '').localeCompare(b.titles?.fr || b.title_fr || ''));
  } else if (sortOrder === 'score') {
    displayed.sort((a, b) => {
      const isVeganFilter = diet === 'vegan';
      const sa = computeAlimScore(a, { isVeganFilter });
      const sb = computeAlimScore(b, { isVeganFilter });
      return sb - sa;
    });
  } else if (sortOrder === 'time') {
    displayed.sort((a, b) => {
      const ta = a.total_time_min || a.timing?.total_min || 999;
      const tb = b.total_time_min || b.timing?.total_min || 999;
      return ta - tb;
    });
  }

  // ── Chips actifs par section ─────────────────────────────────────────────

  const _chip = (value, label, fn) => ({ value, label, onRemove: fn });

  const dietChips = diet
    ? [_chip(diet, DIET_OPTIONS.find(o => o.value === diet)?.label, () => setDiet(''))]
    : [];

  const dietExtraChips = [...dietExtras].map(v =>
    _chip(v, DIET_EXTRA_OPTIONS.find(o => o.value === v)?.label, () => toggleDietExtra(v))
  );

  const seasonChips = season
    ? [_chip(season, SEASON_OPTIONS.find(o => o.value === season)?.label, () => setSeason(''))]
    : [];

  const dishChips = [...dishFilters].map(v =>
    _chip(v, DISH_OPTIONS.find(o => o.value === v)?.label, () => toggleDish(v))
  );

  const allergenChips = [...allergens].map(v =>
    _chip(v, ALLERGEN_OPTIONS.find(o => o.value === v)?.label, () => toggleAllergen(v))
  );

  const difficultyChips = difficulty
    ? [_chip(difficulty, DIFFICULTY_OPTIONS.find(o => o.value === difficulty)?.label, () => setDifficulty(''))]
    : [];

  const healthChips = [
    ...[...healthFilters].map(v => {
      const g = HEALTH_GROUPS.find(g => g.value === v);
      if (!g) return null;
      if (g.subs?.some(s => subFilters.has(s.value))) return null;
      return _chip(v, g.label, () => toggleHealth(v, false));
    }).filter(Boolean),
    ...[...subFilters].map(v => {
      for (const g of HEALTH_GROUPS) {
        const s = g.subs?.find(s => s.value === v);
        if (s) return _chip(v, s.label, () => toggleSub(g.value, v));
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
    _chip(v, _findOriginLabel(v), () => toggleOrigin(v))
  );

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div className="page-home">

      <div className="home-hero">
        <h1 className="home-headline">
          Cuisinez <span className="accent">mieux</span>,<br />mangez <span className="accent">végétal</span>
        </h1>
      </div>

      <RecentlyViewedStrip recent={recent} onClear={clearRecent} />

      {/* Bloc filtres */}
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
                      onClick={() => setDiet(isActive ? '' : value)}
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
                      onClick={() => toggleDietExtra(value)}
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
                      onClick={() => setSeason(isActive ? '' : value)}
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
                      onClick={() => toggleDish(value)}
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
                      onClick={() => toggleAllergen(value)}
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
                      onClick={() => setDifficulty(isActive ? '' : value)}
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
                onToggle={toggleHealth}
                onSubToggle={toggleSub}
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
                onToggle={toggleOrigin}
                onBulkToggle={bulkToggleOrigins}
              />
            </FilterSection>
          </div>
        </div>

        {/* Barre de recherche */}
        <div className="search-row">
          <form
            className="search-container search-container--large"
            onSubmit={e => { e.preventDefault(); fetchRecipes(); }}
            role="search"
          >
            <label htmlFor="recipe-search" className="sr-only">
              Rechercher une recette ou un ingrédient
            </label>
            <input
              id="recipe-search"
              type="search"
              className="search-input"
              placeholder="Rechercher une recette, un ingrédient…"
              value={query}
              onChange={e => setQuery(e.target.value)}
              aria-label="Rechercher une recette ou un ingrédient"
            />
            <button type="submit" className="search-button" disabled={loading}>
              {loading ? '…' : 'Explorer'}
            </button>
          </form>
          {hasActiveFilters && (
            <button className="filters-clear" onClick={clearAllFilters}>
              ✕ Tout effacer
            </button>
          )}
        </div>
      </div>

      {/* Zone résultats */}
      <div aria-live="polite" aria-atomic="false">

        {loading && (
          <div className="skeleton-grid" aria-busy="true" aria-label="Chargement des recettes…">
            {Array.from({ length: 9 }, (_, i) => <RecipeCardSkeleton key={i} />)}
          </div>
        )}

        {error && (
          <div className="state-msg state-msg--error" role="alert">{error}</div>
        )}

        {!loading && !error && displayed.length === 0 && (
          <div className="state-msg">Aucune recette trouvée avec ces critères.</div>
        )}

        {!loading && !error && displayed.length > 0 && (
          <>
            <div className="results-bar">
              <p className="results-count" aria-live="polite">
                {displayed.length} recette{displayed.length > 1 ? 's' : ''}
                {hasActiveFilters && <span className="results-count-filters"> — filtres actifs</span>}
              </p>
              <div className="sort-row" role="group" aria-label="Trier les résultats">
                <span className="filter-label-inline">Trier&nbsp;:</span>
                {SORT_OPTIONS.map(({ value, label }) => (
                  <button
                    key={value}
                    className={`pill pill--sm ${sortOrder === value ? 'pill--active' : ''}`}
                    onClick={() => setSortOrder(value)}
                    aria-pressed={sortOrder === value}
                  >
                    {label}
                  </button>
                ))}
                <div className="time-filter">
                  {maxTime ? (
                    <button
                      className="fao-chip"
                      onClick={() => {
                        setMaxTime('');
                        setTimeInputValue('');
                        fetchRecipes({ mt: '' });
                      }}
                      aria-label="Supprimer le filtre temps"
                    >
                      ⏱ ≤ {maxTime} min ×
                    </button>
                  ) : (
                    <>
                      <span className="filter-label-inline" aria-hidden="true">≤</span>
                      <input
                        type="number"
                        placeholder="min"
                        value={timeInputValue}
                        min="5"
                        max="480"
                        className="time-input"
                        aria-label="Temps de préparation maximum en minutes"
                        onChange={e => setTimeInputValue(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter' && timeInputValue) {
                            setMaxTime(timeInputValue);
                            fetchRecipes({ mt: timeInputValue });
                          }
                          if (e.key === 'Escape') {
                            setTimeInputValue('');
                          }
                        }}
                        onBlur={() => {
                          if (timeInputValue) {
                            setMaxTime(timeInputValue);
                            fetchRecipes({ mt: timeInputValue });
                          }
                        }}
                      />
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="recipe-grid">
              {displayed.slice(0, visibleCount).map((r, i) => (
                <RecipeCard
                  key={r.id || i}
                  recipe={r}
                  activeHealthFilters={healthFilters}
                  activeSubFilters={subFilters}
                />
              ))}
            </div>

            {visibleCount < displayed.length && (
              <div className="load-more-wrap">
                <button
                  className="load-more-btn"
                  onClick={() => setVisibleCount(v => v + 18)}
                >
                  Voir {Math.min(18, displayed.length - visibleCount)} recette{Math.min(18, displayed.length - visibleCount) > 1 ? 's' : ''} de plus
                  <span className="load-more-total"> ({displayed.length - visibleCount} restante{displayed.length - visibleCount > 1 ? 's' : ''})</span>
                </button>
              </div>
            )}
          </>
        )}
      </div>

    </div>
  );
}
