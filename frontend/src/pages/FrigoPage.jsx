/**
 * FrigoPage.jsx — "Qu'est-ce que je peux cuisiner ?"
 *
 * Feature la plus différenciante d'ALIM.
 * Route backend : POST /frigo/suggestions (public, pas d'auth requise)
 */

import { useState, useRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
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
      { key: 'potato',       label: 'Pomme de terre' },
      { key: 'zucchini',     label: 'Courgette' },
      { key: 'spinach',      label: 'Épinards' },
      { key: 'eggplant',     label: 'Aubergine' },
      { key: 'bell_pepper',  label: 'Poivron rouge' },
      { key: 'chili_pepper', label: 'Piment' },
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
      { key: 'green_bean',   label: 'Haricots verts' },
      { key: 'corn',         label: 'Maïs' },
      { key: 'pea',          label: 'Petits pois' },
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
      { key: 'white_bean',    label: 'Haricots blancs' },
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
      { key: 'butter',      label: 'Beurre' },
      { key: 'milk',        label: 'Lait' },
      { key: 'cream',       label: 'Crème' },
      { key: 'yogurt',      label: 'Yaourt nature' },
      { key: 'feta',        label: 'Feta' },
      { key: 'mozzarella',  label: 'Mozzarella' },
      { key: 'parmesan',    label: 'Parmesan' },
      { key: 'goat_cheese', label: 'Chèvre frais' },
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
      { key: 'basil',          label: 'Basilic' },
      { key: 'mint',           label: 'Menthe' },
      { key: 'coriander',      label: 'Coriandre' },
      { key: 'parsley',        label: 'Persil' },
      { key: 'thyme',          label: 'Thym' },
      { key: 'cumin',          label: 'Cumin' },
      { key: 'paprika',        label: 'Paprika' },
      { key: 'turmeric',       label: 'Curcuma' },
      { key: 'ginger',         label: 'Gingembre' },
      { key: 'vanilla',        label: 'Vanille' },
      { key: 'cinnamon',       label: 'Cannelle' },
      { key: 'dijon_mustard',  label: 'Moutarde de Dijon' },
      { key: 'honey',          label: 'Miel' },
      { key: 'soy_sauce',      label: 'Sauce soja' },
      { key: 'olive_oil',      label: 'Huile d\'olive' },
    ],
  },
];

// Labels statiques (chips prédéfinis)
const STATIC_LABELS = Object.fromEntries(
  INGREDIENT_CATS.flatMap(cat => cat.items.map(item => [item.key, item.label]))
);

// ── Ingrédients sélectionnés par catégorie ────────────────────────────────────

function SelectedByCategory({ selected, getLabel, toggle }) {
  // Lookup rapide key → catId (premier match gagne pour les clés partagées)
  const keyToCatId = {};
  for (const cat of INGREDIENT_CATS) {
    for (const item of cat.items) {
      if (!(item.key in keyToCatId)) keyToCatId[item.key] = cat.id;
    }
  }

  // Grouper les clés sélectionnées par catégorie
  const grouped = {};
  const autres   = [];

  for (const key of selected) {
    const catId = keyToCatId[key];
    if (catId) {
      if (!grouped[catId]) grouped[catId] = [];
      grouped[catId].push(key);
    } else {
      autres.push(key);
    }
  }

  // Liste ordonnée — seulement les catégories non vides
  const catGroups = INGREDIENT_CATS
    .filter(cat => grouped[cat.id]?.length > 0)
    .map(cat => ({ id: cat.id, label: cat.label, keys: grouped[cat.id] }));

  if (autres.length > 0) {
    catGroups.push({ id: 'autres', label: '📦 Autres', keys: autres });
  }

  return (
    <div className="frigo-selected-cats">
      {catGroups.map(cat => (
        <details key={cat.id} open className="frigo-cat-group">
          <summary className="frigo-cat-group-header">
            <span className="frigo-cat-group-label">{cat.label}</span>
            <span className="frigo-cat-group-count">{cat.keys.length}</span>
            <span className="frigo-cat-group-chevron" aria-hidden="true" />
          </summary>
          <div className="frigo-cat-group-chips">
            {cat.keys.map(key => (
              <button
                key={key}
                className="frigo-chip frigo-chip--active"
                onClick={() => toggle(key)}
              >
                {getLabel(key)} ✕
              </button>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}

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

  // coveredKeys : Set des clés ayant au moins 1 recette dans le dataset
  // null = pas encore chargé → on affiche tout (fallback permissif)
  const [coveredKeys,  setCoveredKeys]  = useState(null);

  const [customInput,  setCustomInput]  = useState('');
  const [suggestions,  setSuggestions]  = useState([]);
  const [maxMissing,   setMaxMissing]   = useState(2);
  const [results,      setResults]      = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [error,        setError]        = useState(null);
  const [visibleCount, setVisibleCount] = useState(12);
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

  const inputRef      = useRef();
  const containerRef  = useRef();   // conteneur de l'input (pour calculer la position du portail)
  const [dropPos, setDropPos] = useState(null);
  const activeItems   = INGREDIENT_CATS.find(c => c.id === activeCat)?.items || [];

  // Récupère quels ingrédients ont une couverture recette effective
  useEffect(() => {
    const allKeys = [...new Set(INGREDIENT_CATS.flatMap(c => c.items.map(i => i.key)))];
    frigoApi.coverage(allKeys)
      .then(data => setCoveredKeys(new Set(data.covered)))
      .catch(() => setCoveredKeys(null)); // fallback : tout afficher
  }, []);

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

  // Position du portail dropdown — recalcule à l'apparition ET sur scroll/resize
  // Le listener capture (3ème arg true) attrape les scrolls des conteneurs parents.
  const hasSuggestions = suggestions.length > 0;
  useEffect(() => {
    if (!hasSuggestions || !containerRef.current) {
      setDropPos(null);
      return;
    }
    const updatePos = () => {
      if (!containerRef.current) return;
      const r = containerRef.current.getBoundingClientRect();
      setDropPos({ top: r.bottom + 4, left: r.left, width: r.width });
    };
    updatePos();
    window.addEventListener('scroll', updatePos, true);
    window.addEventListener('resize', updatePos);
    return () => {
      window.removeEventListener('scroll', updatePos, true);
      window.removeEventListener('resize', updatePos);
    };
  }, [hasSuggestions]);

  // Autocomplete: debounced search as user types
  useEffect(() => {
    const q = customInput.trim();
    if (q.length < 2) { setSuggestions([]); return; }
    const tid = setTimeout(async () => {
      try {
        const res = await ingApi.search(q);
        // search() backend filtre déjà recipe_count === 0
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
    setVisibleCount(12); // reset pagination à chaque recherche
    try {
      const data = await frigoApi.suggestions({
        ingredients:  [...selected],
        max_missing:  maxMissing,
        diet:         fs.diet || undefined,
        dish_types:   fs.dishFilters.size > 0 ? [...fs.dishFilters] : [],
        limit:        200,
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

        {/* ── Gauche : frigo replié + navigateur ─────────────────────────────── */}
        <aside className="frigo-browser">
          <div className="frigo-panel">

            {/* Mon frigo — accordion replié par défaut */}
            {selected.size > 0 && (
              <details className="frigo-fridge-details">
                <summary className="frigo-fridge-summary">
                  <span className="frigo-fridge-summary-label">Mon frigo</span>
                  <span className="frigo-count">{selected.size}</span>
                  <span className="frigo-fridge-chevron" aria-hidden="true" />
                </summary>
                <div className="frigo-fridge-inner">
                  <SelectedByCategory selected={selected} getLabel={getLabel} toggle={toggle} />
                  <button
                    className="frigo-clear-btn"
                    onClick={() => { setSelected(new Set()); localStorage.removeItem(FRIGO_SELECTED_KEY); }}
                  >
                    Vider la sélection
                  </button>
                </div>
              </details>
            )}

            {/* Séparateur titre */}
            <h3 className="frigo-panel-title" style={{ marginBottom: 10 }}>
              Parcourir les ingrédients
            </h3>

            {/* Saisie libre — le dropdown est rendu en portail hors du DOM */}
            <div className="frigo-custom-input" ref={containerRef}>
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
            </div>

            {/* Options de recherche */}
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
            </div>

            <button
              className="frigo-search-btn"
              onClick={handleSearch}
              disabled={selected.size === 0 || loading}
            >
              {loading ? 'Recherche…' : `Trouver des recettes (${selected.size} ingrédient${selected.size > 1 ? 's' : ''})`}
            </button>

            {/* Séparateur */}
            <div style={{ borderTop: '1px solid var(--brd)', margin: '10px 0 4px' }} />

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

            {/* Ingrédients de la catégorie active — masque ceux sans couverture */}
            <div className="frigo-chips">
              {activeItems
                .filter(item => coveredKeys === null || coveredKeys.has(item.key))
                .map(item => (
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
        </aside>

        {/* ── Centre : résultats ──────────────────────────────────────────────── */}
        <main className="frigo-results">
          {!results && !loading && !error && (
            <div className="frigo-empty">
              <div className="frigo-empty-icon">◈</div>
              <p>Sélectionnez vos ingrédients à gauche et lancez la recherche.</p>
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
                {displayedResults?.slice(0, visibleCount).map((r) => (
                  <FrigoResultCard key={r.id} result={r} getLabel={getLabel} />
                ))}
              </div>

              {displayedResults && visibleCount < displayedResults.length && (
                <div className="load-more-wrap">
                  <button
                    className="load-more-btn"
                    onClick={() => setVisibleCount(v => v + 12)}
                  >
                    Voir {Math.min(12, displayedResults.length - visibleCount)} recette{Math.min(12, displayedResults.length - visibleCount) > 1 ? 's' : ''} de plus
                    <span className="load-more-total"> ({displayedResults.length - visibleCount} restante{displayedResults.length - visibleCount > 1 ? 's' : ''})</span>
                  </button>
                </div>
              )}
            </>
          )}
        </main>

      </div>

      {/* ── Portail dropdown autocomplete ───────────────────────────────────────
          Rendu directement dans document.body — échappe à tout overflow/stacking */}
      {dropPos && createPortal(
        <div style={{
          position: 'fixed',
          top: dropPos.top,
          left: dropPos.left,
          width: dropPos.width,
          zIndex: 9999,
          background: 'var(--sur)',
          border: '1px solid var(--brd)',
          borderRadius: 10,
          overflow: 'hidden',
          boxShadow: '0 8px 24px rgba(0,0,0,0.18)',
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
        </div>,
        document.body
      )}
    </div>
  );
}
