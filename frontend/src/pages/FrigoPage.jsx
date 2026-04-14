/**
 * FrigoPage.jsx — "Qu'est-ce que je peux cuisiner ?"
 *
 * Feature la plus différenciante d'ALIM.
 * Route backend : POST /frigo/suggestions (public, pas d'auth requise)
 */

import { useState, useRef, useEffect } from 'react';
import { frigo as frigoApi, ingredients as ingApi } from '../api';
import { navigate } from '../Router';

// ── Catégories de base pour la saisie rapide ──────────────────────────────────

const QUICK_PICKS = [
  { label: 'Féculents',    items: ['pasta', 'rice', 'lentils', 'chickpea', 'quinoa', 'bread'] },
  { label: 'Légumes',      items: ['tomato', 'onion', 'garlic', 'carrot', 'zucchini', 'spinach', 'eggplant', 'bell_pepper'] },
  { label: 'Protéines',    items: ['egg', 'tofu', 'tempeh', 'feta', 'mozzarella'] },
  { label: 'Condiments',   items: ['olive_oil', 'butter', 'soy_sauce', 'lemon', 'cumin', 'turmeric'] },
  { label: 'Laitiers',     items: ['milk', 'cream', 'yogurt', 'parmesan', 'goat_cheese'] },
];

const FR_LABELS = {
  pasta: 'Pâtes', rice: 'Riz', lentils: 'Lentilles', chickpea: 'Pois chiches',
  quinoa: 'Quinoa', bread: 'Pain', tomato: 'Tomate', onion: 'Oignon', garlic: 'Ail',
  carrot: 'Carotte', zucchini: 'Courgette', spinach: 'Épinard', eggplant: 'Aubergine',
  bell_pepper: 'Poivron', egg: 'Œuf', tofu: 'Tofu', tempeh: 'Tempeh', feta: 'Feta',
  mozzarella: 'Mozzarella', olive_oil: 'Huile d\'olive', butter: 'Beurre',
  soy_sauce: 'Sauce soja', lemon: 'Citron', cumin: 'Cumin', turmeric: 'Curcuma',
  milk: 'Lait', cream: 'Crème', yogurt: 'Yaourt', parmesan: 'Parmesan', goat_cheese: 'Chèvre',
};

// ── Carte résultat ─────────────────────────────────────────────────────────────

function FrigoResultCard({ result }) {
  const pct      = Math.round(result.completeness * 100);
  const isFull   = result.n_missing === 0;
  const isAlmost = result.n_missing === 1;

  return (
    <div
      className={`frigo-card ${isFull ? 'frigo-card--full' : ''} ${isAlmost ? 'frigo-card--almost' : ''}`}
      onClick={() => navigate(`/recette/${result.id}`)}
    >
      <div className="frigo-card-top">
        <div>
          <h3 className="frigo-card-title">{result.title_fr}</h3>
          {result.total_time_min && (
            <span className="frigo-card-time">⏱ {result.total_time_min} min</span>
          )}
        </div>
        <div className="frigo-completeness">
          <svg viewBox="0 0 36 36" className="frigo-ring">
            <circle cx="18" cy="18" r="15" className="ring-bg" />
            <circle
              cx="18" cy="18" r="15"
              className="ring-fill"
              strokeDasharray={`${pct * 0.942} 94.2`}
              strokeDashoffset="23.55"
            />
          </svg>
          <span className="frigo-pct">{pct}%</span>
        </div>
      </div>

      {result.missing.length > 0 && (
        <div className="frigo-missing">
          <span className="frigo-missing-label">Il manque :</span>
          {result.missing.slice(0, 4).map((m) => (
            <span key={m} className="frigo-tag frigo-tag--missing">
              {FR_LABELS[m] || m.replace(/_/g, ' ')}
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
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function FrigoPage() {
  const [selected,    setSelected]    = useState(new Set());
  const [customInput, setCustomInput] = useState('');
  const [maxMissing,  setMaxMissing]  = useState(2);
  const [diet,        setDiet]        = useState('');
  const [results,     setResults]     = useState(null);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState(null);
  const inputRef = useRef();

  const toggle = (item) => {
    setSelected((prev) => {
      const next = new Set(prev);
      next.has(item) ? next.delete(item) : next.add(item);
      return next;
    });
  };

  const addCustom = () => {
    const val = customInput.trim().toLowerCase().replace(/\s+/g, '_');
    if (!val) return;
    setSelected((prev) => new Set([...prev, val]));
    setCustomInput('');
    inputRef.current?.focus();
  };

  const handleSearch = async () => {
    if (selected.size === 0) return;
    setLoading(true);
    setError(null);
    setResults(null);
    try {
      const data = await frigoApi.suggestions({
        ingredients: [...selected],
        max_missing: maxMissing,
        diet: diet || undefined,
        limit: 20,
      });
      setResults(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

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
                {[...selected].map((item) => (
                  <button
                    key={item}
                    className="frigo-chip frigo-chip--active"
                    onClick={() => toggle(item)}
                  >
                    {FR_LABELS[item] || item.replace(/_/g, ' ')} ✕
                  </button>
                ))}
              </div>
            )}

            {/* Saisie libre */}
            <div className="frigo-custom-input">
              <input
                ref={inputRef}
                type="text"
                placeholder="Ajouter un ingrédient…"
                value={customInput}
                onChange={(e) => setCustomInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addCustom()}
                className="search-input"
                style={{ fontSize: 14, padding: '10px 14px' }}
              />
              <button onClick={addCustom} className="search-button" style={{ padding: '0 16px', fontSize: 14 }}>
                +
              </button>
            </div>

            {/* Sélection rapide par catégorie */}
            {QUICK_PICKS.map(({ label, items }) => (
              <div key={label} className="frigo-category">
                <span className="frigo-category-label">{label}</span>
                <div className="frigo-chips">
                  {items.map((item) => (
                    <button
                      key={item}
                      className={`frigo-chip ${selected.has(item) ? 'frigo-chip--active' : ''}`}
                      onClick={() => toggle(item)}
                    >
                      {FR_LABELS[item]}
                    </button>
                  ))}
                </div>
              </div>
            ))}
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

            <label className="frigo-opt-label">
              Régime
              <select
                value={diet}
                onChange={(e) => setDiet(e.target.value)}
                className="search-input"
                style={{ marginTop: 6, padding: '8px 12px', fontSize: 14 }}
              >
                <option value="">Tous</option>
                <option value="vegan">Vegan</option>
                <option value="vegetarian">Végétarien</option>
              </select>
            </label>
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
                  {results.total === 0
                    ? 'Aucune recette trouvée'
                    : `${results.total} recette${results.total > 1 ? 's' : ''} possible${results.total > 1 ? 's' : ''}`}
                </h2>
                {results.total > 0 && (
                  <p className="page-sub">
                    Avec {results.fridge_ingredients?.length || 0} ingrédients — triées par complétude
                  </p>
                )}
              </div>

              <div className="frigo-cards">
                {results.results?.map((r) => (
                  <FrigoResultCard key={r.id} result={r} />
                ))}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
