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

  // Données descriptives pour les 4 éléments
  const ELEMENTS_DESC = [
    {
      id: 'Feu', icon: '🔥', color: ELEMENT_COLOR.Feu,
      tagline: 'Intensité & Vitalité',
      desc: "L'élément Feu incarne l'énergie brute et la chaleur. En cuisine, il se traduit par des saveurs franches et percutantes : épices vives, agrumes zestés, cuissons rapides à feu vif. Les signes Feu (Bélier, Lion, Sagittaire) sont attirés par des plats qui réveillent et nourrissent leur ardeur naturelle.",
      keywords: ['Épices', 'Agrumes', 'Grillé', 'Piment', 'Curcuma', 'Gingembre'],
      signs: ['♈', '♌', '♐'],
    },
    {
      id: 'Terre', icon: '🌿', color: ELEMENT_COLOR.Terre,
      tagline: 'Ancrage & Profondeur',
      desc: "L'élément Terre évoque la patience, la durée et la richesse du sol. Les plats mijotés, les légumes-racines, les céréales complètes et les saveurs umami profondes en sont l'expression culinaire naturelle. Les signes Terre (Taureau, Vierge, Capricorne) trouvent leur équilibre dans des repas nourrissants et réconfortants.",
      keywords: ['Racines', 'Mijoté', 'Céréales', 'Champignons', 'Légumineuses', 'Miso'],
      signs: ['♉', '♍', '♑'],
    },
    {
      id: 'Air', icon: '🌬️', color: ELEMENT_COLOR.Air,
      tagline: 'Légèreté & Diversité',
      desc: "L'élément Air symbolise la mobilité, la curiosité et l'échange. En cuisine, il se manifeste par des textures légères, des salades croquantes, des associations inattendues et des bouchées variées à partager. Les signes Air (Gémeaux, Balance, Verseau) aiment la diversité, la fusion et les repas conviviaux.",
      keywords: ['Crudités', 'Fusion', 'Croquant', 'Herbes fraîches', 'Salades', 'Snacks'],
      signs: ['♊', '♎', '♒'],
    },
    {
      id: 'Eau', icon: '💧', color: ELEMENT_COLOR.Eau,
      tagline: 'Douceur & Intuition',
      desc: "L'élément Eau représente la fluidité, la sensibilité et la profondeur émotionnelle. Les bouillons apaisants, les soupes veloutées, les poissons délicats et les saveurs douces et enveloppantes en sont le reflet. Les signes Eau (Cancer, Scorpion, Poissons) cherchent des plats qui réconfortent l'âme autant que le corps.",
      keywords: ['Bouillons', 'Soupes', 'Vapeur', 'Algues', 'Douceur', 'Fermentés'],
      signs: ['♋', '♏', '♓'],
    },
  ];

  return (
    <div className="page-home" style={{ padding: '0 24px', maxWidth: 1100, margin: '0 auto' }}>

      {/* ── En-tête développé ── */}
      <div style={{ marginBottom: 36 }}>
        <h1 className="page-title" style={{ marginBottom: 12 }}>
          <span className="page-icon">✨</span> Astrologie Culinaire
        </h1>

        {/* Intro principale */}
        <p style={{ fontSize: 16, color: 'var(--txt2)', lineHeight: 1.75, maxWidth: 780, margin: '0 0 10px' }}>
          Depuis l'Antiquité, les traditions culinaires du monde entier ont associé les aliments à des qualités élémentaires —
          chaleur, ancrage, légèreté, fluidité. L'astrologie culinaire s'en inspire pour proposer
          une lecture intuitive de votre rapport à la nourriture, selon les grandes énergies portées par votre signe.
        </p>
        <p style={{ fontSize: 15, color: 'var(--mut)', lineHeight: 1.65, maxWidth: 740, margin: '0 0 28px' }}>
          Chaque signe appartient à l'un des quatre éléments — <strong style={{ color: ELEMENT_COLOR.Feu }}>Feu</strong>,{' '}
          <strong style={{ color: ELEMENT_COLOR.Terre }}>Terre</strong>,{' '}
          <strong style={{ color: ELEMENT_COLOR.Air }}>Air</strong>,{' '}
          <strong style={{ color: ELEMENT_COLOR.Eau }}>Eau</strong> — qui résonne avec
          des saveurs, des textures et des modes de cuisson précis. Explorez les recettes qui vibrent avec votre énergie naturelle.
        </p>

        {/* 4 cartes éléments */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 8 }}>
          {ELEMENTS_DESC.map(el => (
            <div key={el.id} style={{
              borderRadius: 14, padding: 18,
              border: `1px solid ${el.color}30`,
              background: `color-mix(in srgb, ${el.color} 6%, var(--sur))`,
              display: 'flex', flexDirection: 'column', gap: 10,
              position: 'relative', overflow: 'hidden',
            }}>
              {/* Fond watermark */}
              <span style={{
                position: 'absolute', right: -8, bottom: -12, fontSize: 72,
                opacity: 0.06, lineHeight: 1, pointerEvents: 'none', userSelect: 'none',
              }}>{el.icon}</span>

              {/* Header élément */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{
                  width: 36, height: 36, borderRadius: 10, fontSize: 18,
                  background: `color-mix(in srgb, ${el.color} 16%, transparent)`,
                  display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
                }}>{el.icon}</span>
                <div>
                  <div style={{ fontSize: 15, fontWeight: 700, color: el.color, lineHeight: 1.1 }}>
                    {el.id}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--mut)', fontWeight: 500, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
                    {el.tagline}
                  </div>
                </div>
              </div>

              {/* Description */}
              <p style={{ fontSize: 12.5, color: 'var(--txt2)', lineHeight: 1.6, margin: 0 }}>
                {el.desc}
              </p>

              {/* Mots-clés */}
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5 }}>
                {el.keywords.map(kw => (
                  <span key={kw} style={{
                    fontSize: 11, padding: '3px 9px', borderRadius: 20,
                    background: `color-mix(in srgb, ${el.color} 12%, transparent)`,
                    color: el.color, fontWeight: 500, border: `1px solid ${el.color}28`,
                  }}>{kw}</span>
                ))}
              </div>

              {/* Signes associés */}
              <div style={{ display: 'flex', gap: 6, alignItems: 'center', borderTop: `1px solid ${el.color}20`, paddingTop: 10 }}>
                <span style={{ fontSize: 10, color: 'var(--mut)', textTransform: 'uppercase', letterSpacing: '0.06em' }}>Signes</span>
                {el.signs.map(g => (
                  <span key={g} style={{ fontSize: 16, color: el.color }}>{g}</span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* Note de bas d'intro */}
        <p style={{ fontSize: 12.5, color: 'var(--mut)', margin: '12px 0 0', fontStyle: 'italic', lineHeight: 1.5 }}>
          ✦ L'astrologie culinaire est une approche ludique et culturelle — elle invite à l'exploration, non à la prescription.
          Faites confiance à votre curiosité gustative autant qu'à votre thème astral.
        </p>
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
