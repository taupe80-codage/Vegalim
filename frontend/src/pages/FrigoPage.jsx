/**
 * FrigoPage.jsx — "Qu'est-ce que je peux cuisiner ?"
 *
 * Feature la plus différenciante d'ALIM.
 * Route backend : POST /frigo/suggestions (public, pas d'auth requise)
 */

import { useState, useRef, useEffect } from 'react';
import { frigo as frigoApi, ingredients as ingApi } from '../api';
import { navigate } from '../Router';
import { RecipeVisual } from '../components/RecipeCard';
import {
  useFilterState, FiltersBlock, localFilterRecipes,
} from '../components/RecipeFiltersShared';

const FRIGO_SELECTED_KEY = 'alim_frigo_selected';
const FRIGO_FILTERS_KEY  = 'alim_frigo_recipe_filters';

function _loadFrigoFilters() {
  try {
    const raw = localStorage.getItem(FRIGO_FILTERS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}
const FRIGO_LABELS_KEY   = 'alim_frigo_labels';

// ── Catégories d'ingrédients avec onglets ─────────────────────────────────────

const INGREDIENT_CATS = [
  {
    id: 'legumes', label: '🥬 Légumes',
    items: [
      { key: 'tomato',       label: 'Tomate' },
      { key: 'onion',        label: 'Oignon' },
      { key: 'garlic',       label: 'Ail' },
      { key: 'carrot',       label: 'Carotte' },
      { key: 'zucchini',     label: 'Courgette' },
      { key: 'spinach',      label: 'Épinards' },
      { key: 'eggplant',     label: 'Aubergine' },
      { key: 'bell_pepper',  label: 'Poivron rouge' },
      { key: 'broccoli',     label: 'Brocoli' },
      { key: 'cauliflower',  label: 'Chou-fleur' },
      { key: 'sweet_potato', label: 'Patate douce' },
      { key: 'mushroom',     label: 'Champignons' },
      { key: 'butternut',    label: 'Courge butternut' },
      { key: 'leek',         label: 'Poireau' },
      { key: 'beet',         label: 'Betterave' },
      { key: 'cucumber',     label: 'Concombre' },
      { key: 'celery',       label: 'Céleri' },
      { key: 'kale',         label: 'Chou kale' },
    ],
  },
  {
    id: 'fruits', label: '🍎 Fruits',
    items: [
      { key: 'lemon',        label: 'Citron' },
      { key: 'lime',         label: 'Citron vert' },
      { key: 'avocado',      label: 'Avocat' },
      { key: 'apple',        label: 'Pomme' },
      { key: 'orange',       label: 'Orange' },
      { key: 'banana',       label: 'Banane' },
      { key: 'pomegranate',  label: 'Grenade' },
      { key: 'tomato',       label: 'Tomate cerise' },
    ],
  },
  {
    id: 'legumineuses', label: '🫘 Légumineuses',
    items: [
      { key: 'lentils',       label: 'Lentilles corail' },
      { key: 'green_lentils', label: 'Lentilles vertes' },
      { key: 'chickpea',      label: 'Pois chiches' },
      { key: 'black_beans',   label: 'Haricots noirs' },
      { key: 'kidney_beans',  label: 'Haricots rouges' },
      { key: 'edamame',       label: 'Edamame' },
      { key: 'split_peas',    label: 'Pois cassés' },
    ],
  },
  {
    id: 'cereales', label: '🌾 Céréales',
    items: [
      { key: 'rice',       label: 'Riz basmati' },
      { key: 'brown_rice', label: 'Riz complet' },
      { key: 'quinoa',     label: 'Quinoa' },
      { key: 'pasta',      label: 'Pâtes' },
      { key: 'bulgur',     label: 'Boulgour' },
      { key: 'buckwheat',  label: 'Sarrasin' },
      { key: 'oats',       label: 'Avoine' },
      { key: 'semolina',   label: 'Semoule' },
      { key: 'bread',      label: 'Pain complet' },
    ],
  },
  {
    id: 'proteines', label: '🌱 Protéines végé',
    items: [
      { key: 'tofu',   label: 'Tofu ferme' },
      { key: 'tempeh', label: 'Tempeh' },
      { key: 'seitan', label: 'Seitan' },
      { key: 'egg',    label: 'Œufs' },
    ],
  },
  {
    id: 'laitiers', label: '🧀 Laitiers',
    items: [
      { key: 'feta',        label: 'Feta' },
      { key: 'mozzarella',  label: 'Mozzarella' },
      { key: 'parmesan',    label: 'Parmesan' },
      { key: 'goat_cheese', label: 'Chèvre frais' },
      { key: 'yogurt',      label: 'Yaourt nature' },
      { key: 'cream',       label: 'Crème' },
      { key: 'milk',        label: 'Lait' },
    ],
  },
  {
    id: 'noix', label: '🌰 Noix & graines',
    items: [
      { key: 'almond',        label: 'Amandes' },
      { key: 'walnut',        label: 'Noix' },
      { key: 'cashew',        label: 'Noix de cajou' },
      { key: 'pumpkin_seeds', label: 'Graines de courge' },
      { key: 'sesame',        label: 'Sésame' },
      { key: 'tahini',        label: 'Tahini' },
      { key: 'flax_seeds',    label: 'Graines de lin' },
    ],
  },
  {
    id: 'herbes', label: '🌿 Herbes & épices',
    items: [
      { key: 'basil',     label: 'Basilic' },
      { key: 'coriander', label: 'Coriandre' },
      { key: 'parsley',   label: 'Persil' },
      { key: 'cumin',     label: 'Cumin' },
      { key: 'turmeric',  label: 'Curcuma' },
      { key: 'ginger',    label: 'Gingembre' },
      { key: 'soy_sauce', label: 'Sauce soja' },
      { key: 'olive_oil', label: 'Huile d\'olive' },
    ],
  },
];

// Labels statiques (chips prédéfinis)
const STATIC_LABELS = Object.fromEntries(
  INGREDIENT_CATS.flatMap(cat => cat.items.map(item => [item.key, item.label]))
);

// ── Carte résultat ─────────────────────────────────────────────────────────────

function FrigoResultCard({ result, getLabel }) {
  const pct      = Math.round(result.completeness * 100);
  const isFull   = result.n_missing === 0;
  const isAlmost = result.n_missing === 1;

  return (
    <div
      className={`frigo-card ${isFull ? 'frigo-card--full' : ''} ${isAlmost ? 'frigo-card--almost' : ''}`}
      onClick={() => navigate(`/recette/${result.id}`)}
    >
      {/* Image + anneau de complétude en overlay */}
      <div className="frigo-card-img">
        <RecipeVisual recipe={result} size="card" />
        <div className="frigo-ring-badge">
          <svg viewBox="0 0 36 36" className="frigo-ring">
            <circle cx="18" cy="18" r="15" className="ring-bg" />
            <circle
              cx="18" cy="18" r="15"
              className={`ring-fill${isFull ? ' ring-fill--full' : ''}`}
              strokeDasharray={`${pct * 0.942} 94.2`}
              strokeDashoffset="23.55"
            />
          </svg>
          <span className="frigo-pct">{pct}%</span>
        </div>
      </div>

      {/* Contenu texte */}
      <div className="frigo-card-body">
        <div className="frigo-card-info">
          <h3 className="frigo-card-title">{result.title_fr || result.titles?.fr}</h3>
          {result.total_time_min && (
            <span className="frigo-card-time">⏱ {result.total_time_min} min</span>
          )}
        </div>

        {result.missing.length > 0 && (
          <div className="frigo-missing">
            <span className="frigo-missing-label">Il manque :</span>
            {result.missing.slice(0, 4).map((m) => (
              <span key={typeof m === 'object' ? (m.id || JSON.stringify(m)) : m} className="frigo-tag frigo-tag--missing">
                {getLabel(m)}
              </span>
            ))}
            {result.missing.length > 4 && (
              <span className="frigo-tag frigo-tag--more">+{result.missing.length - 4}</span>
            )}
          </div>
        )}

        {isFull && (
          <div className="frigo-ready">✓ Tout est là — cuisinez maintenant !</div>
        )}
      </div>
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function FrigoPage() {
  // Persistent selected ingredients
  const [selected, setSelected] = useState(() => {
    try {
      const saved = localStorage.getItem(FRIGO_SELECTED_KEY);
      return saved ? new Set(JSON.parse(saved)) : new Set();
    } catch { return new Set(); }
  });

  // Extra labels for API-sourced ingredients (persisted so chips display correctly)
  const [extraLabels, setExtraLabels] = useState(() => {
    try { return JSON.parse(localStorage.getItem(FRIGO_LABELS_KEY) || '{}'); }
    catch { return {}; }
  });

  const [customInput,  setCustomInput]  = useState('');
  const [suggestions,  setSuggestions]  = useState([]);
  const [maxMissing,   setMaxMissing]   = useState(2);
  const [results,      setResults]      = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState(null);
  const [activeCat,    setActiveCat]    = useState('legumes');
  const [filtersOpen,  setFiltersOpen]  = useState(false);

  // Filtres recette complets — initialisés depuis localStorage
  const _sf = _loadFrigoFilters();
  const fs = useFilterState({
    diet:         _sf.diet         || '',
    dietExtras:   _sf.dietExtras   || [],
    season:       _sf.season       || '',
    difficulty:   _sf.difficulty   || '',
    allergens:    _sf.allergens    || [],
    healthFilters:_sf.healthFilters|| [],
    subFilters:   _sf.subFilters   || [],
    dishFilters:  _sf.dishFilters  || [],
    origins:      _sf.origins      || [],
  });

  const inputRef    = useRef();
  const dropdownRef = useRef();
  const activeItems = INGREDIENT_CATS.find(c => c.id === activeCat)?.items || [];

  // Persist selected ingredients to localStorage
  useEffect(() => {
    localStorage.setItem(FRIGO_SELECTED_KEY, JSON.stringify([...selected]));
  }, [selected]);

  // Persist recipe filters to localStorage
  useEffect(() => {
    try {
      localStorage.setItem(FRIGO_FILTERS_KEY, JSON.stringify({
        diet:          fs.diet,
        dietExtras:    [...fs.dietExtras],
        season:        fs.season,
        difficulty:    fs.difficulty,
        allergens:     [...fs.allergens],
        healthFilters: [...fs.healthFilters],
        subFilters:    [...fs.subFilters],
        dishFilters:   [...fs.dishFilters],
        origins:       [...fs.origins],
      }));
    } catch {}
  }, [fs.diet, fs.dietExtras, fs.season, fs.difficulty, fs.allergens,
      fs.healthFilters, fs.subFilters, fs.dishFilters, fs.origins]);

  // Autocomplete: debounced search as user types
  useEffect(() => {
    const q = customInput.trim();
    if (q.length < 2) { setSuggestions([]); return; }
    const tid = setTimeout(async () => {
      try {
        const res = await ingApi.search(q);
        setSuggestions(res?.results || []);
      } catch { setSuggestions([]); }
    }, 280);
    return () => clearTimeout(tid);
  }, [customInput]);

  const getLabel = (key) => {
    if (key === null || key === undefined) return '';
    // L'API renvoie parfois des objets {id, name_fr} au lieu de strings
    if (typeof key === 'object') key = key.name_fr || key.name || key.id || '';
    key = String(key);
    return STATIC_LABELS[key] || extraLabels[key] || key.replace(/_/g, ' ');
  };

  const toggle = (key) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(key) ? next.delete(key) : next.add(key);
      return next;
    });
  };

  const selectSuggestion = (s) => {
    setSelected(prev => new Set([...prev, s.id]));
    if (s.name_fr) {
      setExtraLabels(prev => {
        const next = { ...prev, [s.id]: s.name_fr };
        localStorage.setItem(FRIGO_LABELS_KEY, JSON.stringify(next));
        return next;
      });
    }
    setCustomInput('');
    setSuggestions([]);
    inputRef.current?.focus();
  };

  const addCustom = () => {
    const val = customInput.trim().toLowerCase().replace(/\s+/g, '_');
    if (!val) return;
    setSelected(prev => new Set([...prev, val]));
    setCustomInput('');
    setSuggestions([]);
    inputRef.current?.focus();
  };

  const handleSearch = async () => {
    if (selected.size === 0) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data = await frigoApi.suggestions({
        ingredients:  [...selected],
        max_missing:  maxMissing,
        diet:         fs.diet || undefined,
        dish_types:   fs.dishFilters.size > 0 ? [...fs.dishFilters] : [],
        limit:        50,
      });
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  // Filtrage client-side sur les résultats backend
  const displayedResults = results?.results
    ? localFilterRecipes(results.results, { ...fs.filterState, maxTime: '' })
    : null;

  return (
    <div className="page-frigo">
      {/* En-tête */}
      <div className="page-header">
        <h1 className="page-title">
          <span className="page-icon">◈</span> Mon frigo
        </h1>
        <p className="page-sub">
          Sélectionnez les ingrédients que vous avez — on vous dit quoi cuisiner.
        </p>
      </div>

      {/* ── Bloc filtres recette ───────────────────────────────────────────── */}
      <div className="frigo-filters-wrap">
        <button
          className="frigo-filters-toggle"
          onClick={() => setFiltersOpen(o => !o)}
          aria-expanded={filtersOpen}
        >
          <span>🔍 Filtres recettes</span>
          {fs.hasActiveFilters && <span className="frigo-filters-dot" />}
          <span className="frigo-filters-chevron">{filtersOpen ? '▾' : '▸'}</span>
        </button>

        {filtersOpen && (
          <FiltersBlock
            diet={fs.diet}             setDiet={fs.setDiet}
            dietExtras={fs.dietExtras} toggleDietExtra={fs.toggleDietExtra}
            season={fs.season}         setSeason={fs.setSeason}
            difficulty={fs.difficulty} setDifficulty={fs.setDifficulty}
            allergens={fs.allergens}   toggleAllergen={fs.toggleAllergen}
            healthFilters={fs.healthFilters} subFilters={fs.subFilters}
            toggleHealth={fs.toggleHealth}   toggleSub={fs.toggleSub}
            dishFilters={fs.dishFilters}     toggleDish={fs.toggleDish}
            origins={fs.origins}       toggleOrigin={fs.toggleOrigin}
            bulkToggleOrigins={fs.bulkToggleOrigins}
            openSections={fs.openSections} toggleSection={fs.toggleSection}
            hasActiveFilters={fs.hasActiveFilters} clearAll={fs.clearAll}
          />
        )}
      </div>

      <div className="frigo-layout">
        {/* Panneau de sélection */}
        <aside className="frigo-sidebar">
          <div className="frigo-panel">
            <h3 className="frigo-panel-title">
              Vos ingrédients
              {selected.size > 0 && (
                <span className="frigo-count">{selected.size}</span>
              )}
            </h3>

            {/* Chips sélectionnés */}
            {selected.size > 0 && (
              <div className="frigo-selected-chips">
                {[...selected].map((key) => (
                  <button
                    key={key}
                    className="frigo-chip frigo-chip--active"
                    onClick={() => toggle(key)}
                  >
                    {getLabel(key)} ✕
                  </button>
                ))}
              </div>
            )}

            {/* Saisie libre avec autocomplete */}
            <div className="frigo-custom-input" style={{ position: 'relative' }}>
              <input
                ref={inputRef}
                type="text"
                placeholder="Ajouter un ingrédient…"
                value={customInput}
                onChange={(e) => setCustomInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') { suggestions.length > 0 ? selectSuggestion(suggestions[0]) : addCustom(); }
                  if (e.key === 'Escape') { setSuggestions([]); }
                }}
                onBlur={() => setTimeout(() => setSuggestions([]), 160)}
                className="search-input"
                style={{ fontSize: 14, padding: '10px 14px' }}
              />
              <button onClick={addCustom} className="search-button" style={{ padding: '0 16px', fontSize: 14 }}>
                +
              </button>

              {/* Dropdown autocomplete */}
              {suggestions.length > 0 && (
                <div ref={dropdownRef} style={{
                  position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 200,
                  background: 'var(--sur)', border: '1px solid var(--brd)',
                  borderRadius: 10, overflow: 'hidden',
                  boxShadow: '0 8px 24px rgba(0,0,0,0.12)', marginTop: 4,
                }}>
                  {suggestions.slice(0, 8).map((s) => (
                    <button
                      key={s.id}
                      onMouseDown={() => selectSuggestion(s)}
                      style={{
                        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                        width: '100%', textAlign: 'left',
                        padding: '9px 14px', background: 'transparent',
                        border: 'none', borderBottom: '1px solid var(--brd)',
                        cursor: 'pointer', fontSize: 13, color: 'var(--txt)', fontFamily: 'inherit',
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--sur2)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <span>{s.name_fr}</span>
                      <span style={{ fontSize: 11, color: 'var(--mut)' }}>{s.name_en}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Onglets catégories */}
            <div className="frigo-cat-tabs">
              {INGREDIENT_CATS.map(cat => (
                <button
                  key={cat.id}
                  className={`frigo-cat-tab ${activeCat === cat.id ? 'frigo-cat-tab--active' : ''}`}
                  onClick={() => setActiveCat(cat.id)}
                >
                  {cat.label}
                </button>
              ))}
            </div>

            {/* Ingrédients de la catégorie active */}
            <div className="frigo-chips">
              {activeItems.map(item => (
                <button
                  key={item.key}
                  className={`frigo-chip ${selected.has(item.key) ? 'frigo-chip--active' : ''}`}
                  onClick={() => toggle(item.key)}
                >
                  {selected.has(item.key) && <span style={{ fontSize: 10, marginRight: 3 }}>✓</span>}
                  {item.label}
                </button>
              ))}
            </div>
          </div>

          {/* Options */}
          <div className="frigo-options">
            <label className="frigo-opt-label">
              Ingrédients manquants tolérés
              <div className="frigo-slider-row">
                <input
                  type="range"
                  min={0} max={5}
                  value={maxMissing}
                  onChange={(e) => setMaxMissing(+e.target.value)}
                  className="frigo-slider"
                />
                <span className="frigo-slider-val">{maxMissing}</span>
              </div>
            </label>

            {selected.size > 0 && (
              <button
                onClick={() => { setSelected(new Set()); localStorage.removeItem(FRIGO_SELECTED_KEY); }}
                style={{
                  marginTop: 4, padding: '6px 12px', fontSize: 12, width: '100%',
                  background: 'transparent', border: '1px solid var(--brd)',
                  borderRadius: 6, color: 'var(--mut)', cursor: 'pointer',
                }}
              >
                Vider la sélection
              </button>
            )}
          </div>

          <button
            className="frigo-search-btn"
            onClick={handleSearch}
            disabled={selected.size === 0 || loading}
          >
            {loading ? 'Recherche…' : `Trouver des recettes (${selected.size} ingrédient${selected.size > 1 ? 's' : ''})`}
          </button>
        </aside>

        {/* Résultats */}
        <main className="frigo-results">
          {!results && !loading && !error && (
            <div className="frigo-empty">
              <div className="frigo-empty-icon">◈</div>
              <p>Sélectionnez vos ingrédients pour découvrir ce que vous pouvez cuisiner.</p>
            </div>
          )}

          {loading && (
            <div className="skeleton-grid">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="skeleton-card">
                  <div className="skeleton skeleton-img" style={{ height: 80 }} />
                  <div className="skeleton skeleton-line" style={{ width: '65%' }} />
                  <div className="skeleton skeleton-line" style={{ width: '40%' }} />
                </div>
              ))}
            </div>
          )}

          {error && <div className="state-msg state-msg--error">{error}</div>}

          {results && !loading && (
            <>
              <div className="frigo-results-header">
                <h2>
                  {displayedResults?.length === 0
                    ? 'Aucune recette trouvée'
                    : `${displayedResults?.length ?? 0} recette${(displayedResults?.length ?? 0) > 1 ? 's' : ''} possible${(displayedResults?.length ?? 0) > 1 ? 's' : ''}`}
                </h2>
                {(displayedResults?.length ?? 0) > 0 && (
                  <p className="page-sub">
                    Avec {results.fridge_ingredients?.length || 0} ingrédients — triées par complétude
                    {fs.hasActiveFilters && ' · filtres actifs'}
                  </p>
                )}
              </div>

              <div className="frigo-cards">
                {displayedResults?.map((r) => (
                  <FrigoResultCard key={r.id} result={r} getLabel={getLabel} />
                ))}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
