/**
 * HomePage.jsx — Recherche + Grille de recettes
 */

import { useState, useEffect, useCallback } from 'react';
import { recipes as recipesApi } from '../api';
import RecipeCard from '../components/RecipeCard';
import RecipeLegend from '../components/RecipeLegend';

const DIET_OPTIONS = [
  { value: '',           label: 'Régime : Tous' },
  { value: 'vegan',      label: 'Vegan' },
  { value: 'vegetarian', label: 'Végétarien' }
];

const ALLERGEN_OPTIONS = [
  { value: '',               label: 'Allergènes : Tous' },
  { value: 'gluten_free',    label: 'Sans Gluten' },
  { value: 'lactose_free',   label: 'Sans Lactose' },
  { value: 'nut_free',       label: 'Sans Fruits à Coque' }
];

const HEALTH_OPTIONS = [
  { value: '',             label: 'Santé : Tous' },
  { value: 'high_protein', label: 'Hyper Protéiné' },
  { value: 'low_calorie',  label: 'Faible en Calories' },
  { value: 'high_fiber',   label: 'Riche en Fibres' },
  { value: 'low_fodmap',   label: 'Low FODMAP' },
  { value: 'low_ig',       label: 'Diabète / Low IG' }
];

const HOLISTIC_OPTIONS = [
  { value: '',               label: 'Holistique : Tous' },
  { value: 'menstrual',      label: 'Phase Menstruelle' },
  { value: 'follicular',     label: 'Phase Folliculaire' },
  { value: 'ovulatory',      label: 'Phase Ovulatoire' },
  { value: 'luteal',         label: 'Phase Lutéale' },
  { value: 'astro_eau',      label: 'Élément Astro: Eau' },
  { value: 'astro_feu',      label: 'Élément Astro: Feu' },
  { value: 'astro_air',      label: 'Élément Astro: Air' },
  { value: 'astro_terre',    label: 'Élément Astro: Terre' }
];

const SORT_OPTIONS = [
  { value: 'pertinence', label: 'Pertinence' },
  { value: 'alpha',      label: 'A → Z' },
  { value: 'score',      label: 'Score ↓' },
  { value: 'time',       label: 'Temps ↑' },
];

export default function HomePage() {
  const [query,      setQuery]      = useState('');
  const [diet,       setDiet]       = useState('');
  const [allergen,   setAllergen]   = useState('');
  const [health,     setHealth]     = useState('');
  const [holistic,   setHolistic]   = useState('');
  
  const [sortOrder,  setSortOrder]  = useState('pertinence');
  const [maxTime,    setMaxTime]    = useState('');
  const [recipes,    setRecipes]    = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [error,      setError]      = useState(null);

  const fetchRecipes = useCallback(async (q = query, d = diet, a = allergen, h = health, holi = holistic, mt = maxTime) => {
    setLoading(true);
    setError(null);
    try {
      const hasFilter = q || d || mt || a || h || holi;
      let data;
      
      const payload = { query: q, limit: 40 };
      if (d) payload.filtre = d;
      if (mt) payload.max_time = parseInt(mt);
      
      if (a === 'gluten_free') payload.gluten_free = true;
      if (a === 'lactose_free') payload.lactose_free = true;
      if (a === 'nut_free') payload.nut_free = true;
      
      if (h === 'high_protein') payload.high_protein = true;
      if (h === 'low_calorie') payload.low_calorie = true;
      if (h === 'high_fiber') payload.high_fiber = true;
      if (h === 'low_fodmap') payload.fodmap = 'low';
      if (h === 'low_ig') payload.low_ig = true;
      
      if (holi) {
        if (holi.startsWith('astro_')) payload.astro_element = holi.replace('astro_', '');
        else payload.cycle_phase = holi;
      }

      if (hasFilter) {
        data = await recipesApi.search(payload);
      } else {
        data = await recipesApi.list({ limit: 40 });
      }
      
      const results = Array.isArray(data) ? data : (data.results || data.recipes || []);
      setRecipes(results);
    } catch (err) {
      setError(err.message || 'Erreur de connexion au backend.');
    } finally {
      setLoading(false);
    }
  }, [query, diet, allergen, health, holistic, maxTime]);

  useEffect(() => { fetchRecipes('', '', '', '', '', ''); }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchRecipes();
  };

  const handleFilterChange = (setter) => (e) => {
    const val = e.target.value;
    setter(val);
    // Note: React state hasn't updated yet in this closure, so standard approach is to use useEffect or we just handle it eagerly:
    // But since fetchRecipes uses state variables, it's better to pass explicitly if needed, or rely on a generic trigger.
  };

  // Eager fetching when dropdown values change
  useEffect(() => {
    // Only fetch if user intentionally clicks (skips the initial double fetch)
    const timeout = setTimeout(() => {
      fetchRecipes(query, diet, allergen, health, holistic, maxTime);
    }, 300);
    return () => clearTimeout(timeout);
  }, [diet, allergen, health, holistic]);

  let displayed = [...recipes];
  if (sortOrder === 'alpha') {
    displayed.sort((a, b) =>
      (a.titles?.fr || a.title_fr || '').localeCompare(b.titles?.fr || b.title_fr || ''));
  } else if (sortOrder === 'score') {
    displayed.sort((a, b) => {
      const sa = a.final_score || (a.iconic_score || 0) / 10;
      const sb = b.final_score || (b.iconic_score || 0) / 10;
      return sb - sa;
    });
  } else if (sortOrder === 'time') {
    displayed.sort((a, b) => {
      const ta = a.total_time_min || a.timing?.total_min || 999;
      const tb = b.total_time_min || b.timing?.total_min || 999;
      return ta - tb;
    });
  }

  return (
    <div className="page-home">
      <div className="home-hero">
        <h1 className="home-headline">
          Cuisinez <span className="accent">mieux</span>,<br />mangez <span className="accent">végétal</span>
        </h1>
        <form className="search-container" onSubmit={handleSearch}>
          <input
            type="text"
            className="search-input"
            placeholder="Rechercher une recette, un ingrédient…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          <button type="submit" className="search-button">Explorer</button>
        </form>
      </div>

      <div className="filters-row" style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
        <RecipeLegend />
        
        <div className="dropdown-filters" style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <select className="filter-select" value={diet} onChange={(e) => setDiet(e.target.value)}>
            {DIET_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className="filter-select" value={allergen} onChange={(e) => setAllergen(e.target.value)}>
             {ALLERGEN_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className="filter-select" value={health} onChange={(e) => setHealth(e.target.value)}>
             {HEALTH_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          <select className="filter-select" value={holistic} onChange={(e) => setHolistic(e.target.value)}>
             {HOLISTIC_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>

        <div className="sort-row">
          {SORT_OPTIONS.map(({ value, label }) => (
            <button
              key={value}
              className={`pill pill--sm ${sortOrder === value ? 'pill--active' : ''}`}
              onClick={() => setSortOrder(value)}
            >
              {label}
            </button>
          ))}
          <div className="time-filter">
            <input
              type="number"
              placeholder="≤ min"
              value={maxTime}
              min="5"
              max="480"
              className="time-input"
              onChange={(e) => {
                setMaxTime(e.target.value);
                if (!e.target.value) fetchRecipes(query, diet, allergen, health, holistic, '');
              }}
              onBlur={() => maxTime && fetchRecipes(query, diet, allergen, health, holistic, maxTime)}
            />
          </div>
        </div>
      </div>

      {loading && (
        <div className="skeleton-grid">
          {Array.from({ length: 9 }).map((_, i) => (
            <div key={i} className="skeleton-card">
              <div className="skeleton skeleton-img" />
              <div className="skeleton skeleton-line" style={{ width: '70%' }} />
              <div className="skeleton skeleton-line" style={{ width: '45%' }} />
            </div>
          ))}
        </div>
      )}

      {error && <div className="state-msg state-msg--error">{error}</div>}

      {!loading && !error && displayed.length === 0 && (
        <div className="state-msg">Aucune recette trouvée avec ces critères.</div>
      )}

      {!loading && !error && displayed.length > 0 && (
        <>
          <p className="results-count">{displayed.length} recette{displayed.length > 1 ? 's' : ''}</p>
          <div className="recipe-grid">
            {displayed.map((r, i) => (
              <RecipeCard key={r.id || i} recipe={r} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
