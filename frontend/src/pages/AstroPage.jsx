import { useState, useEffect } from 'react';
import { recipes as recipesApi } from '../api';
import RecipeCard, { computeAlimScore } from '../components/RecipeCard';
import { useFilterState, FiltersBlock, localFilterRecipes } from '../components/RecipeFiltersShared';

const ASTRO_KEY = 'alim_astro_sign';

// ── Données ───────────────────────────────────────────────────────────────────
const ASTRO_SIGNS = [
  { id: 'aries',       glyph: '♈', label: 'Bélier',     element: 'Feu',   reco: 'Épices chaudes, protéines rapides, plats vifs.' },
  { id: 'taurus',      glyph: '♉', label: 'Taureau',    element: 'Terre', reco: 'Plats mijotés réconfortants, racines, saveurs profondes.' },
  { id: 'gemini',      glyph: '♊', label: 'Gémeaux',    element: 'Air',   reco: 'Snacks variés, textures croquantes, fusion.' },
  { id: 'cancer',      glyph: '♋', label: 'Cancer',     element: 'Eau',   reco: 'Soupes, plats doux, cuisine de famille.' },
  { id: 'leo',         glyph: '♌', label: 'Lion',       element: 'Feu',   reco: 'Ingrédients nobles : safran, agrumes, épices.' },
  { id: 'virgo',       glyph: '♍', label: 'Vierge',     element: 'Terre', reco: 'Céréales complètes, détox, ingrédients précis.' },
  { id: 'libra',       glyph: '♎', label: 'Balance',    element: 'Air',   reco: 'Desserts raffinés, équilibre sucré-salé.' },
  { id: 'scorpio',     glyph: '♏', label: 'Scorpion',   element: 'Eau',   reco: 'Saveurs intenses, fermentés, umami.' },
  { id: 'sagittarius', glyph: '♐', label: 'Sagittaire', element: 'Feu',   reco: 'Cuisine du monde, saveurs exotiques, voyages.' },
  { id: 'capricorn',   glyph: '♑', label: 'Capricorne', element: 'Terre', reco: 'Ingrédients bruts, plats traditionnels.' },
  { id: 'aquarius',    glyph: '♒', label: 'Verseau',    element: 'Air',   reco: 'Super-aliments, associations inattendues.' },
  { id: 'pisces',      glyph: '♓', label: 'Poissons',   element: 'Eau',   reco: 'Algues, bouillons légers, repas fluides.' },
];

const ELEMENT_COLOR = { Feu: '#C0392B', Terre: '#8a6d3b', Air: '#6d7a76', Eau: '#2980B9' };
const ELEMENT_ICON  = { Feu: '🔥', Terre: '🌿', Air: '🌬️', Eau: '💧' };

const STAR_POS = [
  [8,12,1.6,0.9],[22,26,1.0,0.7],[38,8,1.4,0.85],[54,18,0.9,0.6],
  [68,32,1.8,1.0],[82,14,1.1,0.7],[92,38,1.3,0.8],[12,48,0.8,0.5],
  [28,62,1.5,0.9],[44,70,1.0,0.6],[60,56,1.2,0.7],[76,76,1.7,1.0],
  [88,64,0.9,0.55],[18,82,1.3,0.8],[50,86,1.5,0.9],[80,90,0.9,0.5],
  [4,36,1.2,0.7],[96,22,1.0,0.65],[40,42,1.4,0.85],[72,50,1.1,0.65],
];

// ── Composants visuels ────────────────────────────────────────────────────────

function Starfield({ density = 1, color = 'currentColor', style: sx = {} }) {
  return (
    <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', overflow: 'hidden', ...sx }} aria-hidden="true">
      {STAR_POS.map(([x, y, r, op], i) => (
        <span key={i} style={{
          position: 'absolute', left: `${x}%`, top: `${y}%`,
          width: r * 2, height: r * 2, borderRadius: '50%',
          background: color, opacity: op * density,
          boxShadow: `0 0 ${r * 3}px ${color}`,
        }} />
      ))}
    </div>
  );
}

function ConstellationArc({ color, style: sx = {} }) {
  const pts = [[5, 70], [22, 40], [42, 55], [62, 30], [85, 50]];
  return (
    <svg viewBox="0 0 100 80" preserveAspectRatio="none"
      style={{ position: 'absolute', inset: 0, pointerEvents: 'none', width: '100%', height: '100%', ...sx }} aria-hidden="true">
      <polyline points={pts.map(p => p.join(',')).join(' ')} fill="none"
        stroke={color} strokeWidth="0.25" strokeOpacity="0.5" strokeDasharray="1 1.5" />
      {pts.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="0.8" fill={color} opacity={i === 2 ? 1 : 0.65} />
      ))}
    </svg>
  );
}

// ── Tri + filtres rapides ─────────────────────────────────────────────────────
const SORT_OPTIONS = [
  { value: 'score',      label: 'Score NRF ↓',  icon: '◆' },
  { value: 'alpha',      label: 'A → Z',         icon: '🔤' },
  { value: 'time_asc',   label: 'Temps ↑',       icon: '⏱' },
  { value: 'iron',       label: 'Fer',            icon: '🩸' },
  { value: 'protein',    label: 'Protéines',      icon: '💪' },
  { value: 'fiber',      label: 'Fibres',         icon: '🌾' },
  { value: 'magnesium',  label: 'Magnésium',      icon: '🧲' },
  { value: 'vitamin_c',  label: 'Vit. C',         icon: '🍊' },
  { value: 'zinc',       label: 'Zinc',           icon: '⚡' },
];


function sortRecipes(list, sortKey, maxTime) {
  let filtered = [...list];
  if (maxTime) {
    const mt = parseInt(maxTime);
    filtered = filtered.filter(r => (r.timing?.total_min || r.total_time_min || 999) <= mt);
  }
  switch (sortKey) {
    case 'score':    filtered.sort((a, b) => computeAlimScore(b) - computeAlimScore(a)); break;
    case 'alpha':    filtered.sort((a, b) => (a.titles?.fr || '').localeCompare(b.titles?.fr || '')); break;
    case 'time_asc': filtered.sort((a, b) => (a.timing?.total_min || 999) - (b.timing?.total_min || 999)); break;
    case 'iron': case 'protein': case 'fiber': case 'magnesium':
    case 'vitamin_c': case 'zinc': case 'calcium': case 'potassium':
      filtered.sort((a, b) => (b._nutrition?.[sortKey]?.pct_ajr || 0) - (a._nutrition?.[sortKey]?.pct_ajr || 0));
      break;
    default: break;
  }
  return filtered;
}

// ── Page principale ───────────────────────────────────────────────────────────
export default function AstroPage() {
  const [sign, setSign] = useState(() => {
    const saved = localStorage.getItem(ASTRO_KEY);
    return ASTRO_SIGNS.some(s => s.id === saved) ? saved : 'aries';
  });
  const [astroRecipes, setAstroRecipes] = useState([]);
  const [loadingAstro, setLoadingAstro] = useState(false);
  const [astroVisible, setAstroVisible] = useState(20);
  const [astroSort,    setAstroSort]    = useState('score');
  const fs = useFilterState();

  // Persist sign selection
  useEffect(() => { localStorage.setItem(ASTRO_KEY, sign); }, [sign]);

  useEffect(() => {
    let cancelled = false;
    const activeSign = ASTRO_SIGNS.find(s => s.id === sign);
    const run = async () => {
      setLoadingAstro(true);
      try {
        const data = await recipesApi.list({ astro_element: activeSign.element.toLowerCase(), limit: 500 });
        if (!cancelled) { setAstroRecipes(data.results || []); setAstroVisible(20); }
      } catch { /* ignore */ } finally {
        if (!cancelled) setLoadingAstro(false);
      }
    };
    run();
    return () => { cancelled = true; };
  }, [sign]);

  const activeSign    = ASTRO_SIGNS.find(s => s.id === sign);
  const elColor       = ELEMENT_COLOR[activeSign.element];
  const filteredAstro = localFilterRecipes(astroRecipes, fs.filterState);
  const sortedAstro   = sortRecipes(filteredAstro, astroSort);

  return (
    <div className="page-home" style={{ padding: '0 24px', maxWidth: 1100, margin: '0 auto' }}>
      <div className="page-header" style={{ marginBottom: 24 }}>
        <h1 className="page-title"><span className="page-icon">✨</span> Astrologie Culinaire</h1>
        <p className="page-sub">Chaque signe a son élément — Feu, Terre, Air, Eau — qui résonne avec des saveurs et ingrédients précis.</p>
      </div>

      {/* Grille 6 × 2 signes */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 10, marginBottom: 20 }}>
        {ASTRO_SIGNS.map(s => {
          const isActive = sign === s.id;
          const c = ELEMENT_COLOR[s.element];
          return (
            <button key={s.id} onClick={() => setSign(s.id)}
              style={{
                padding: 14, borderRadius: 14,
                border: `1px solid ${isActive ? c : 'var(--brd)'}`,
                background: isActive ? `color-mix(in srgb, ${c} 14%, var(--sur))` : 'var(--sur)',
                cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5,
                fontFamily: 'inherit', position: 'relative', overflow: 'hidden', transition: 'all .15s',
              }}>
              {isActive && <Starfield density={0.5} color={c} style={{ opacity: 0.35 }} />}
              <span style={{ fontSize: 26, color: isActive ? c : 'var(--txt)', position: 'relative' }}>{s.glyph}</span>
              <span style={{ fontSize: 12, fontWeight: isActive ? 500 : 400, color: isActive ? c : 'var(--txt)', position: 'relative' }}>{s.label}</span>
              <span style={{ fontSize: 9, letterSpacing: '0.06em', textTransform: 'uppercase', color: isActive ? c : 'var(--mut)', position: 'relative' }}>
                {ELEMENT_ICON[s.element]} {s.element}
              </span>
            </button>
          );
        })}
      </div>

      {/* Panneau signe actif */}
      <div className="frigo-panel" style={{
        display: 'grid', gridTemplateColumns: '200px 1fr', gap: 24,
        alignItems: 'center', position: 'relative', overflow: 'hidden', marginBottom: 20,
      }}>
        <ConstellationArc color={elColor} style={{ opacity: 0.6 }} />
        <Starfield density={0.3} color={elColor} />
        <div style={{
          position: 'relative', aspectRatio: '1/1', borderRadius: 14,
          background: `linear-gradient(135deg, ${elColor}, ${elColor}70)`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexDirection: 'column', color: '#fff', overflow: 'hidden',
        }}>
          <Starfield density={0.6} color="#fff" style={{ opacity: 0.4 }} />
          <span style={{ fontSize: 72, lineHeight: 1, position: 'relative', textShadow: `0 0 20px ${elColor}` }}>
            {activeSign.glyph}
          </span>
          <span style={{ fontSize: 16, fontWeight: 500, marginTop: 6, position: 'relative' }}>{activeSign.label}</span>
        </div>
        <div style={{ position: 'relative' }}>
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 8,
            padding: '6px 14px',
            background: `color-mix(in srgb, ${elColor} 14%, transparent)`,
            color: elColor, borderRadius: 999, fontSize: 13, fontWeight: 500, marginBottom: 14,
          }}>
            {ELEMENT_ICON[activeSign.element]} Élément {activeSign.element}
          </div>
          <h2 style={{ margin: '0 0 10px', fontSize: 28, fontWeight: 500, letterSpacing: '-0.02em' }}>
            Pour <em style={{ fontStyle: 'italic', color: elColor }}>{activeSign.label}</em>
          </h2>
          <p style={{ fontSize: 15, color: 'var(--txt2)', lineHeight: 1.7, margin: 0 }}>{activeSign.reco}</p>
          <div style={{
            marginTop: 16, padding: '12px 16px', background: 'var(--sur2)',
            borderRadius: 10, fontSize: 13, color: 'var(--txt2)', lineHeight: 1.5,
          }}>
            <strong style={{ color: 'var(--txt)' }}>💡 Note&nbsp;:</strong>{' '}
            sélection de recettes contenant une majorité d'ingrédients associés à l'élément <strong>{activeSign.element}</strong>.
          </div>
        </div>
      </div>

      {/* Recettes */}
      <div>
        <h3 style={{ marginBottom: 12 }}>Recettes pour l'élément {activeSign.element}</h3>

        {/* Filtres identiques à la page d'accueil */}
        <FiltersBlock {...fs} onAnyChange={() => setAstroVisible(20)} />

        {/* Tri + temps */}
        <div className="sort-row" style={{ margin: '10px 0 14px' }}>
          {SORT_OPTIONS.map(o => (
            <button key={o.value}
              className={`pill pill--sm ${astroSort === o.value ? 'pill--active' : ''}`}
              onClick={() => { setAstroSort(o.value); setAstroVisible(20); }}
              aria-pressed={astroSort === o.value}
            >{o.icon} {o.label}</button>
          ))}
          <div className="time-filter">
            <span className="filter-label-inline">≤</span>
            <input type="number" placeholder="min" value={fs.maxTime}
              onChange={e => { fs.setMaxTime(e.target.value); setAstroVisible(20); }}
              className="time-input" min="5" max="300" step="5" />
          </div>
          {(astroSort !== 'score' || fs.hasActiveFilters) && (
            <button className="filters-clear" onClick={() => {
              setAstroSort('score'); fs.clearAll(); setAstroVisible(20);
            }}>✕ Réinitialiser</button>
          )}
        </div>

        {loadingAstro ? (
          <div className="skeleton-grid">
            {[1, 2, 3, 4, 5, 6].map(i => (
              <div key={i} className="skeleton-card">
                <div className="skeleton skeleton-img" />
              </div>
            ))}
          </div>
        ) : sortedAstro.length > 0 ? (
          <>
            <p style={{ fontSize: 12, color: 'var(--mut)', marginBottom: 10 }}>
              {sortedAstro.length} recette{sortedAstro.length > 1 ? 's' : ''} — {Math.min(astroVisible, sortedAstro.length)} affichées
            </p>
            <div className="recipe-grid">
              {sortedAstro.slice(0, astroVisible).map(recipe => (
                <RecipeCard key={recipe.id || recipe._id} recipe={recipe} />
              ))}
            </div>
            {astroVisible < sortedAstro.length && (
              <button className="frigo-search-btn" onClick={() => setAstroVisible(v => v + 20)} style={{ marginTop: 16 }}>
                Voir plus ({sortedAstro.length - astroVisible} restantes)
              </button>
            )}
          </>
        ) : (
          <p style={{ color: 'var(--mut)' }}>Aucune recette trouvée pour ces filtres.</p>
        )}
      </div>
    </div>
  );
}
