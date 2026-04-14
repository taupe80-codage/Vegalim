import { useState, useEffect } from 'react';
import { cycle as cycleApi, recipes as recipesApi } from '../api';
import RecipeCard from '../components/RecipeCard';

import translations from '../translations.json';

const CYCLE_PHASES = [
  {
    id: 'menstrual',
    label: 'Menstruelle (J1-J5)',
    title: 'Recharge en fer et réconfort corporel',
    desc: 'Le corps perd du sang et du fer. La fatigue, les crampes et l\'inflammation sont fréquentes. L\'alimentation doit compenser les pertes en fer, réduire l\'inflammation avec des oméga-3 et soutenir le système nerveux avec du magnésium.',
    needs: [
      { icon: '🩸', label: 'Fer', detail: 'Compenser les pertes sanguines — lentilles, épinards, betterave' },
      { icon: '🧲', label: 'Magnésium', detail: 'Anti-crampes et relaxant musculaire — chocolat noir, noix' },
      { icon: '🐟', label: 'Oméga-3', detail: 'Anti-inflammatoire naturel — graines de lin, noix' },
      { icon: '🍊', label: 'Vitamine C', detail: 'Booste l\'absorption du fer — agrumes, poivron, grenade' },
    ],
    priorityNutrients: ['iron', 'magnesium', 'vitamin_c'],
  },
  {
    id: 'follicular',
    label: 'Folliculaire (J6-J14)',
    title: 'Hydratation et énergie légère',
    desc: 'Les œstrogènes remontent, l\'énergie revient. C\'est le moment idéal pour des aliments légers et riches en protéines végétales qui soutiennent la croissance cellulaire et la préparation à l\'ovulation.',
    needs: [
      { icon: '💪', label: 'Protéines', detail: 'Soutien musculaire et cellulaire — quinoa, tofu, pois chiches' },
      { icon: '🥦', label: 'Vitamine B', detail: 'Énergie et métabolisme — brocoli, avocat, légumineuses' },
      { icon: '🌾', label: 'Fibres', detail: 'Équilibre digestif et satiété — avoine, graines de chia' },
      { icon: '💧', label: 'Hydratation', detail: 'Concombre, courgette, bouillons légers' },
    ],
    priorityNutrients: ['protein', 'fiber', 'magnesium'],
  },
  {
    id: 'ovulatory',
    label: 'Ovulatoire (J15-J17)',
    title: 'Soutien hépatique et métabolique maximal',
    desc: 'Pic hormonal (œstrogènes + LH). Le foie travaille davantage pour métaboliser les hormones. Les antioxydants et le zinc protègent les cellules, tandis que les fibres aident l\'élimination hormonale.',
    needs: [
      { icon: '🫐', label: 'Antioxydants', detail: 'Protection cellulaire au pic hormonal — baies, tomate, grenade' },
      { icon: '🍋', label: 'Vitamine C', detail: 'Soutien immunitaire et collagène — poivron, agrumes' },
      { icon: '⚡', label: 'Zinc', detail: 'Fertilité et immunité — graines de courge, sésame' },
      { icon: '🥬', label: 'Crucifères', detail: 'Soutien hépatique et détox hormonale — brocoli, chou-fleur' },
    ],
    priorityNutrients: ['vitamin_c', 'zinc', 'fiber'],
  },
  {
    id: 'luteal',
    label: 'Lutéale (J18-J28)',
    title: 'Fibres et maintien de la glycémie',
    desc: 'La progestérone domine, les envies sucrées et l\'irritabilité apparaissent. Les glucides complexes stabilisent la glycémie, le magnésium réduit le syndrome prémenstruel (SPM), et la vitamine B6 régule l\'humeur.',
    needs: [
      { icon: '🧲', label: 'Magnésium', detail: 'Anti-SPM et antistress — chocolat noir, amandes, banane' },
      { icon: '🍠', label: 'Glucides complexes', detail: 'Stabilisateur de glycémie — patate douce, riz complet, avoine' },
      { icon: '🧠', label: 'Vitamine B6', detail: 'Régulateur d\'humeur et de sérotonine — banane, lentilles' },
      { icon: '🌿', label: 'Fibres', detail: 'Élimination hormonale et transit — légumineuses, graines' },
    ],
    priorityNutrients: ['magnesium', 'fiber', 'potassium'],
  },
];

const ASTRO_SIGNS = [
  { id: 'bélier',    label: '♈ Bélier',     element: 'Feu',   reco: 'Épices chaudes, protéines rapides.' },
  { id: 'taureau',   label: '♉ Taureau',    element: 'Terre', reco: 'Plats mijotés réconfortants, racines.' },
  { id: 'gémeaux',   label: '♊ Gémeaux',    element: 'Air',   reco: 'Snacks variés, textures croquantes.' },
  { id: 'cancer',    label: '♋ Cancer',     element: 'Eau',   reco: 'Soupes, plats doux et familiaux.' },
  { id: 'lion',      label: '♌ Lion',       element: 'Feu',   reco: 'Ingrédients nobles (safran, agrumes).' },
  { id: 'vierge',    label: '♍ Vierge',     element: 'Terre', reco: 'Céréales complètes, aliments détox.' },
  { id: 'balance',   label: '♎ Balance',    element: 'Air',   reco: 'Desserts raffinés, équilibre sucré-salé.' },
  { id: 'scorpion',  label: '♏ Scorpion',   element: 'Eau',   reco: 'Saveurs intenses, aliments fermentés.' },
  { id: 'sagittaire',label: '♐ Sagittaire', element: 'Feu',   reco: 'Cuisine du monde, saveurs exotiques.' },
  { id: 'capricorne',label: '♑ Capricorne', element: 'Terre', reco: 'Ingrédients bruts, plats traditionnels.' },
  { id: 'verseau',   label: '♒ Verseau',    element: 'Air',   reco: 'Associations inattendues, super-aliments.' },
  { id: 'poissons',  label: '♓ Poissons',   element: 'Eau',   reco: 'Algues, bouillons légers, repas fluides.' },
];

export default function CycleAstroPage() {
  const [tab, setTab] = useState('cycle'); // 'cycle' ou 'astro'
  
  // States Cycle
  const [phase, setPhase] = useState('menstrual');
  const [cycleData, setCycleData] = useState(null);
  const [loadingCycle, setLoadingCycle] = useState(false);
  const [errorCycle, setErrorCycle] = useState(null);

  // States Astro
  const [sign, setSign] = useState('bélier');

  const [cycleRecipes, setCycleRecipes] = useState([]);
  const [loadingCycleRecipes, setLoadingCycleRecipes] = useState(false);
  const [cycleVisible, setCycleVisible] = useState(20);
  const [cycleSort, setCycleSort] = useState('pertinence');
  const [cycleMaxTime, setCycleMaxTime] = useState('');

  const [astroSort, setAstroSort] = useState('pertinence');
  const [astroMaxTime, setAstroMaxTime] = useState('');

  const SORT_OPTIONS = [
    { value: 'pertinence',  label: 'Pertinence',      icon: '🏆' },
    { value: 'alpha',       label: 'A → Z',            icon: '🔤' },
    { value: 'time_asc',    label: 'Temps ↑',          icon: '⏱' },
    { value: 'kcal_asc',    label: 'Calories ↑',       icon: '🔥' },
    { value: 'iron',        label: 'Fer max',           icon: '🩸' },
    { value: 'protein',     label: 'Protéines max',     icon: '💪' },
    { value: 'fiber',       label: 'Fibres max',        icon: '🌾' },
    { value: 'magnesium',   label: 'Magnésium max',     icon: '🧲' },
    { value: 'vitamin_c',   label: 'Vitamine C max',    icon: '🍊' },
    { value: 'zinc',        label: 'Zinc max',           icon: '⚡' },
    { value: 'calcium',     label: 'Calcium max',       icon: '🦴' },
    { value: 'potassium',   label: 'Potassium max',     icon: '🍌' },
  ];

  const sortRecipes = (list, sortKey, maxTime) => {
    let filtered = [...list];
    // Filtre par temps max
    if (maxTime) {
      const mt = parseInt(maxTime);
      filtered = filtered.filter(r => (r.timing?.total_min || r.total_time_min || 999) <= mt);
    }
    // Tri
    switch (sortKey) {
      case 'alpha':
        filtered.sort((a, b) => (a.titles?.fr || '').localeCompare(b.titles?.fr || ''));
        break;
      case 'time_asc':
        filtered.sort((a, b) => (a.timing?.total_min || 999) - (b.timing?.total_min || 999));
        break;
      case 'kcal_asc':
        filtered.sort((a, b) => (a._nutrition?.calories?.value || 999) - (b._nutrition?.calories?.value || 999));
        break;
      case 'iron': case 'protein': case 'fiber': case 'magnesium':
      case 'vitamin_c': case 'zinc': case 'calcium': case 'potassium':
        filtered.sort((a, b) => (b._nutrition?.[sortKey]?.pct_ajr || 0) - (a._nutrition?.[sortKey]?.pct_ajr || 0));
        break;
      default: // pertinence — garder l'ordre du backend
        break;
    }
    return filtered;
  };

  useEffect(() => {
    if (tab === 'cycle') {
      const fetchCycleData = async () => {
        setLoadingCycle(true);
        setErrorCycle(null);
        try {
          // L'API renvoie { phase, ingredients: [], count }
          const res = await cycleApi.getIngredients(phase);
          setCycleData(res);
        } catch (err) {
          setErrorCycle(err.message);
        } finally {
          setLoadingCycle(false);
        }

        setLoadingCycleRecipes(true);
        try {
          const data = await recipesApi.list({ cycle_phase: phase, limit: 500 });
          const allRecipes = data.results || [];
          setCycleRecipes(allRecipes);
          setCycleVisible(20); // Reset on phase change
        } catch (err) {
          console.error(err);
        } finally {
          setLoadingCycleRecipes(false);
        }
      };
      fetchCycleData();
    }
  }, [tab, phase]);

  const renderCycleTab = () => {
    const activePhase = CYCLE_PHASES.find(p => p.id === phase);
    const sortedCycle = sortRecipes(cycleRecipes, cycleSort, cycleMaxTime);
    return (
      <div className="tab-content" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <p className="page-sub">
          Adaptez votre alimentation aux variations hormonales de votre cycle pour un meilleur bien-être corporel.
        </p>
        <div className="diet-pills" style={{ marginBottom: '24px' }}>
          {CYCLE_PHASES.map(p => (
            <button
              key={p.id}
              className={`pill ${phase === p.id ? 'pill--active' : ''}`}
              onClick={() => setPhase(p.id)}
            >
              {p.label}
            </button>
          ))}
        </div>
        
        <div className="frigo-panel">
          <h3 className="frigo-panel-title">{activePhase.title}</h3>
          <p style={{ color: 'var(--mut)', marginBottom: '16px', lineHeight: 1.6 }}>{activePhase.desc}</p>
          
          {/* Besoins nutritionnels de la phase */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '10px', marginBottom: '20px' }}>
            {activePhase.needs.map((n, i) => (
              <div key={i} style={{ padding: '10px 14px', borderRadius: '10px', background: 'var(--bg)', border: '1px solid var(--brd)', display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                <span style={{ fontSize: '20px', flexShrink: 0 }}>{n.icon}</span>
                <div>
                  <strong style={{ fontSize: '13px' }}>{n.label}</strong>
                  <p style={{ margin: '2px 0 0', fontSize: '11px', color: 'var(--mut)', lineHeight: 1.4 }}>{n.detail}</p>
                </div>
              </div>
            ))}
          </div>

          {loadingCycle && <div className="skeleton skeleton-line" style={{ width: '100%', height: '80px' }} />}
          {errorCycle && <div className="state-msg state-msg--error">{errorCycle}</div>}
          
          {!loadingCycle && !errorCycle && cycleData && (
            <div>
              <h4 style={{ marginBottom: '10px' }}>Ingrédients recommandés</h4>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {cycleData.ingredients && cycleData.ingredients.length > 0 ? (
                  cycleData.ingredients.map((ing, idx) => (
                    <span key={idx} className="badge" style={{ background: 'var(--bg2)', color: 'var(--fg)', border: '1px solid var(--brd)' }}>
                      {(translations[ing] || ing.replace(/_/g, ' ')).replace(/_/g, ' ')}
                    </span>
                  ))
                ) : (
                  <span style={{ color: 'var(--mut)' }}>Aucun ingrédient spécifique identifié.</span>
                )}
              </div>
            </div>
          )}
        </div>

        {/* SECTION RECETTES */}
        <div>
          <h3 style={{ marginBottom: '12px' }}>Recettes · {activePhase.title}</h3>

          {/* ── Barre de tri/filtres ── */}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '16px', padding: '12px', background: 'var(--bg)', borderRadius: '10px', border: '1px solid var(--brd)' }}>
            <select
              value={cycleSort}
              onChange={e => { setCycleSort(e.target.value); setCycleVisible(20); }}
              className="search-input"
              style={{ padding: '8px 12px', fontSize: '13px', flex: '1 1 180px', minWidth: '160px' }}
            >
              {SORT_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.icon} {o.label}</option>
              ))}
            </select>
            <input
              type="number"
              placeholder="Temps max (min)"
              value={cycleMaxTime}
              onChange={e => { setCycleMaxTime(e.target.value); setCycleVisible(20); }}
              className="search-input"
              min="5" max="300" step="5"
              style={{ padding: '8px 12px', fontSize: '13px', width: '140px' }}
            />
            {(cycleSort !== 'pertinence' || cycleMaxTime) && (
              <button
                onClick={() => { setCycleSort('pertinence'); setCycleMaxTime(''); setCycleVisible(20); }}
                style={{ padding: '6px 14px', fontSize: '12px', background: 'transparent', border: '1px solid var(--brd)', borderRadius: '6px', color: 'var(--mut)', cursor: 'pointer' }}
              >
                ✕ Réinitialiser
              </button>
            )}
          </div>

          {loadingCycleRecipes ? (
            <div className="skeleton-grid">
              {[1, 2, 3].map(i => (
                <div key={i} className="skeleton-card" style={{ height: 120 }}>
                  <div className="skeleton skeleton-img" style={{ height: 80 }} />
                </div>
              ))}
            </div>
          ) : sortedCycle.length > 0 ? (
            <>
              <p style={{ fontSize: '12px', color: 'var(--mut)', marginBottom: '10px' }}>
                {sortedCycle.length} recettes{cycleMaxTime ? ` (≤ ${cycleMaxTime} min)` : ''} — {Math.min(cycleVisible, sortedCycle.length)} affichées
              </p>
              <div className="grid">
                {sortedCycle.slice(0, cycleVisible).map(recipe => (
                  <RecipeCard key={recipe.id || recipe._id} recipe={recipe} />
                ))}
              </div>
              {cycleVisible < sortedCycle.length && (
                <button
                  className="frigo-search-btn"
                  onClick={() => setCycleVisible(v => v + 20)}
                  style={{ marginTop: '16px', alignSelf: 'center' }}
                >
                  Voir plus ({sortedCycle.length - cycleVisible} restantes)
                </button>
              )}
            </>
          ) : (
            <p style={{ color: 'var(--mut)' }}>Aucune recette trouvée{cycleMaxTime ? ` en ≤ ${cycleMaxTime} min` : ''}.</p>
          )}
        </div>
      </div>
    );
  };

  const [astroRecipes, setAstroRecipes] = useState([]);
  const [loadingAstro, setLoadingAstro] = useState(false);
  const [astroVisible, setAstroVisible] = useState(20);

  useEffect(() => {
    if (tab === 'astro') {
      const activeSign = ASTRO_SIGNS.find(s => s.id === sign);
      const fetchAstro = async () => {
        setLoadingAstro(true);
        try {
          const data = await recipesApi.list({ astro_element: activeSign.element.toLowerCase(), limit: 500 });
          const allRecipes = data.results || [];
          setAstroRecipes(allRecipes);
          setAstroVisible(20); // Reset on sign change
        } catch (err) {
          console.error(err);
        } finally {
          setLoadingAstro(false);
        }
      };
      fetchAstro();
    }
  }, [tab, sign]);

  const renderAstroTab = () => {
    const activeSign = ASTRO_SIGNS.find(s => s.id === sign);
    const sortedAstro = sortRecipes(astroRecipes, astroSort, astroMaxTime);
    return (
      <div className="tab-content" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <p className="page-sub">
          Découvrez la cuisine qui résonne avec votre signe astrologique et votre élément.
        </p>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'flex-start' }}>
          <div className="frigo-panel" style={{ flex: 1 }}>
            <h3 className="frigo-panel-title">Choisissez votre signe</h3>
            <select
              value={sign}
              onChange={(e) => setSign(e.target.value)}
              className="search-input"
              style={{ width: '100%', padding: '12px', fontSize: '15px' }}
            >
              {ASTRO_SIGNS.map(s => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </div>
          
          <div className="frigo-panel" style={{ flex: 2 }}>
            <h3 className="frigo-panel-title">Inspiration Végétale pour {activeSign.label}</h3>
            <div style={{ background: 'var(--bg-card)', padding: '16px', borderRadius: '8px', border: '1px solid var(--brd)' }}>
              <p><strong>Élément :</strong> <span className="badge" style={{ background: 'var(--bg)', color: 'var(--fg)' }}>{activeSign.element}</span></p>
              <p style={{ marginTop: '12px', color: 'var(--mut)' }}>{activeSign.reco}</p>
            </div>
            <p style={{ marginTop: '16px', fontSize: '12px', color: 'var(--mut)', fontStyle: 'italic' }}>
              Note: Voici une sélection de recettes contenant une majorité d'ingrédients associés à votre élément.
            </p>
          </div>
        </div>

        {/* SECTION RECETTES */}
        <div>
          <h3 style={{ marginBottom: '12px' }}>Recettes recommandées (Élément {activeSign.element})</h3>

          {/* ── Barre de tri/filtres ── */}
          <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center', marginBottom: '16px', padding: '12px', background: 'var(--bg)', borderRadius: '10px', border: '1px solid var(--brd)' }}>
            <select
              value={astroSort}
              onChange={e => { setAstroSort(e.target.value); setAstroVisible(20); }}
              className="search-input"
              style={{ padding: '8px 12px', fontSize: '13px', flex: '1 1 180px', minWidth: '160px' }}
            >
              {SORT_OPTIONS.map(o => (
                <option key={o.value} value={o.value}>{o.icon} {o.label}</option>
              ))}
            </select>
            <input
              type="number"
              placeholder="Temps max (min)"
              value={astroMaxTime}
              onChange={e => { setAstroMaxTime(e.target.value); setAstroVisible(20); }}
              className="search-input"
              min="5" max="300" step="5"
              style={{ padding: '8px 12px', fontSize: '13px', width: '140px' }}
            />
            {(astroSort !== 'pertinence' || astroMaxTime) && (
              <button
                onClick={() => { setAstroSort('pertinence'); setAstroMaxTime(''); setAstroVisible(20); }}
                style={{ padding: '6px 14px', fontSize: '12px', background: 'transparent', border: '1px solid var(--brd)', borderRadius: '6px', color: 'var(--mut)', cursor: 'pointer' }}
              >
                ✕ Réinitialiser
              </button>
            )}
          </div>

          {loadingAstro ? (
            <div className="skeleton-grid">
              {[1, 2, 3].map(i => (
                <div key={i} className="skeleton-card" style={{ height: 120 }}>
                  <div className="skeleton skeleton-img" style={{ height: 80 }} />
                </div>
              ))}
            </div>
          ) : sortedAstro.length > 0 ? (
            <>
              <p style={{ fontSize: '12px', color: 'var(--mut)', marginBottom: '10px' }}>
                {sortedAstro.length} recettes{astroMaxTime ? ` (≤ ${astroMaxTime} min)` : ''} — {Math.min(astroVisible, sortedAstro.length)} affichées
              </p>
              <div className="grid">
                {sortedAstro.slice(0, astroVisible).map(recipe => (
                  <RecipeCard key={recipe.id || recipe._id} recipe={recipe} />
                ))}
              </div>
              {astroVisible < sortedAstro.length && (
                <button
                  className="frigo-search-btn"
                  onClick={() => setAstroVisible(v => v + 20)}
                  style={{ marginTop: '16px', alignSelf: 'center' }}
                >
                  Voir plus ({sortedAstro.length - astroVisible} restantes)
                </button>
              )}
            </>
          ) : (
            <p style={{ color: 'var(--mut)' }}>Aucune recette trouvée pour cet élément.</p>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="page-home" style={{ padding: '0 24px', maxWidth: '1000px', margin: '0 auto' }}>
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <h1 className="page-title"><span className="page-icon">🌙</span> Bien-être : Cycle & Astro</h1>
      </div>

      <div className="sort-row" style={{ marginBottom: '24px', borderBottom: '1px solid var(--brd)', paddingBottom: '16px' }}>
        <button
          className={`pill ${tab === 'cycle' ? 'pill--active' : ''}`}
          onClick={() => setTab('cycle')}
        >
          Cycle Féminin
        </button>
        <button
          className={`pill ${tab === 'astro' ? 'pill--active' : ''}`}
          onClick={() => setTab('astro')}
        >
          Astrologie Culinaire
        </button>
      </div>

      {tab === 'cycle' ? renderCycleTab() : renderAstroTab()}
    </div>
  );
}
