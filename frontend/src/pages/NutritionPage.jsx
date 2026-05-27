/**
 * NutritionPage.jsx — Suivi AJR + Détection de carences
 *
 * Utilise deux endpoints :
 *   POST /nutrition/ajr_score          → score global + détails par nutriment (public)
 *   POST /nutrition/detect_deficiencies → carences avec sévérité (auth requis)
 *
 * La page fonctionne en deux modes :
 *   - Mode public  : saisie manuelle → /ajr_score (pas besoin d'être connecté)
 *   - Mode auth    : idem + /detect_deficiencies pour l'analyse de carences
 */

import { useState, useMemo, useEffect } from 'react';
import { nutrition as nutritionApi, recipes as recipesApi, recipeStore } from '../api';
import { navigate } from '../Router';

const PLAN_KEY = 'alim_plan_weekly';
const MEAL_ORDER = ['breakfast','lunch','dinner'];
const DAYS_KEY   = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche'];
const DAYS_FR    = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'];

// ── Config des nutriments affichés ───────────────────────────────────────────

const NUTRIENT_META = {
  calories:    { label: 'Calories',       unit: 'kcal', icon: '🔥', group: 'macro',  ajr: 2000,  color: '#f0883e' },
  protein:     { label: 'Protéines',      unit: 'g',    icon: '💪', group: 'macro',  ajr: 50,    color: '#58a6ff' },
  carbs:       { label: 'Glucides',       unit: 'g',    icon: '🌾', group: 'macro',  ajr: 275,   color: '#f0c27f' },
  fat:         { label: 'Lipides',        unit: 'g',    icon: '🫒', group: 'macro',  ajr: 70,    color: '#a371f7' },
  fiber:       { label: 'Fibres',         unit: 'g',    icon: '🥦', group: 'macro',  ajr: 30,    color: '#3fb950' },
  iron:        { label: 'Fer',            unit: 'mg',   icon: '🩸', group: 'micro',  ajr: 14,    color: '#f85149' },
  calcium:     { label: 'Calcium',        unit: 'mg',   icon: '🦴', group: 'micro',  ajr: 1000,  color: '#58a6ff' },
  vitamin_b12: { label: 'Vitamine B12',   unit: 'µg',   icon: '🧬', group: 'micro',  ajr: 2.5,   color: '#3fb950' },
  zinc:        { label: 'Zinc',           unit: 'mg',   icon: '⚡', group: 'micro',  ajr: 10,    color: '#f0883e' },
  vitamin_d:   { label: 'Vitamine D',     unit: 'µg',   icon: '☀️', group: 'micro',  ajr: 15,    color: '#f0c27f' },
  magnesium:   { label: 'Magnésium',      unit: 'mg',   icon: '🌿', group: 'micro',  ajr: 400,   color: '#a371f7' },
  vitamin_c:   { label: 'Vitamine C',     unit: 'mg',   icon: '🍊', group: 'micro',  ajr: 90,    color: '#f0883e' },
};

const NUTRIENT_LABELS = {
  calories: 'Calories', protein: 'Protéines', carbs: 'Glucides', fat: 'Lipides',
  fiber: 'Fibres', iron: 'Fer', calcium: 'Calcium', vitamin_b12: 'Vitamine B12',
  zinc: 'Zinc', vitamin_d: 'Vitamine D', magnesium: 'Magnésium', vitamin_c: 'Vitamine C',
  potassium: 'Potassium', phosphorus: 'Phosphore', sodium: 'Sodium',
};

const SEVERITY_CONFIG = {
  high:   { label: 'Carence critique',  color: '#f85149', bg: 'rgba(248,81,73,0.08)',   border: 'rgba(248,81,73,0.25)',  icon: '🚨' },
  medium: { label: 'Carence modérée',   color: '#f0883e', bg: 'rgba(240,136,62,0.08)',  border: 'rgba(240,136,62,0.25)', icon: '⚠️' },
};

// Conseils par nutriment
const NUTRIENT_TIPS = {
  iron:        'Légumineuses, tofu, graines de citrouille, lentilles. Consommer avec de la vitamine C pour améliorer l\'absorption.',
  calcium:     'Tofu (calcium), boissons végétales enrichies, brocoli, chou kale, amandes.',
  vitamin_b12: 'Nécessite une supplémentation en alimentation végane. Levure nutritionnelle enrichie, aliments fortifiés.',
  zinc:        'Légumineuses, graines de courge, noix de cajou. Le trempage améliore la biodisponibilité.',
  vitamin_d:   'Exposition solaire, champignons UV, aliments enrichis. Supplémentation souvent recommandée.',
  magnesium:   'Graines, noix, légumineuses, céréales complètes, cacao.',
  vitamin_c:   'Poivron rouge, agrumes, kiwi, fraise, brocoli. Sensible à la chaleur.',
  protein:     'Légumineuses, tofu, tempeh, seitan, quinoa, graines de chanvre.',
  fiber:       'Légumineuses, céréales complètes, fruits, légumes, graines de lin.',
  potassium:   'Banane, patate douce, avocat, légumineuses, épinards.',
};

// ── Score gauge ───────────────────────────────────────────────────────────────

function ScoreGauge({ score }) {
  const clamped = Math.max(0, Math.min(10, score));
  const pct     = clamped / 10;
  const angle   = -140 + pct * 280; // de -140° à +140°

  const color = clamped >= 7 ? '#3fb950' : clamped >= 4 ? '#f0883e' : '#f85149';
  const label = clamped >= 7 ? 'Excellent' : clamped >= 5 ? 'Correct' : clamped >= 3 ? 'Insuffisant' : 'Critique';

  return (
    <div className="nutr-gauge-wrap">
      <svg viewBox="0 0 200 110" className="nutr-gauge-svg">
        {/* Arc fond */}
        <path
          d="M 20 100 A 80 80 0 1 1 180 100"
          fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="14" strokeLinecap="round"
        />
        {/* Arc rempli */}
        <path
          d="M 20 100 A 80 80 0 1 1 180 100"
          fill="none"
          stroke={color}
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${pct * 251.3} 251.3`}
          style={{ filter: `drop-shadow(0 0 6px ${color}80)`, transition: 'all 0.8s cubic-bezier(0.34,1.56,0.64,1)' }}
        />
        {/* Aiguille */}
        <line
          x1="100" y1="100"
          x2={100 + 60 * Math.cos(((angle - 90) * Math.PI) / 180)}
          y2={100 + 60 * Math.sin(((angle - 90) * Math.PI) / 180)}
          stroke={color} strokeWidth="2.5" strokeLinecap="round"
          style={{ transition: 'all 0.8s cubic-bezier(0.34,1.56,0.64,1)' }}
        />
        <circle cx="100" cy="100" r="5" fill={color} />
        {/* Valeur */}
        <text x="100" y="88" textAnchor="middle" fill={color}
          style={{ fontSize: 26, fontWeight: 700, fontFamily: 'Outfit, sans-serif' }}>
          {clamped.toFixed(1)}
        </text>
        <text x="100" y="100" textAnchor="middle" fill="#8b949e" style={{ fontSize: 9 }}>
          / 10
        </text>
      </svg>
      <div className="nutr-gauge-label" style={{ color }}>{label}</div>
    </div>
  );
}

// ── Barre AJR ─────────────────────────────────────────────────────────────────

function AJRBar({ nutrient, value, ajr, color }) {
  const pct  = Math.min(100, (value / ajr) * 100);
  const ok   = pct >= 50;
  const meta = NUTRIENT_META[nutrient];

  return (
    <div className="ajr-bar-row">
      <div className="ajr-bar-header">
        <span className="ajr-bar-icon">{meta?.icon || '●'}</span>
        <span className="ajr-bar-name">{meta?.label || nutrient}</span>
        <span className="ajr-bar-value" style={{ color: ok ? color : '#f85149' }}>
          {value < 10 ? value.toFixed(1) : Math.round(value)} {meta?.unit}
        </span>
        <span className="ajr-bar-pct" style={{ color: ok ? 'var(--mut)' : '#f85149' }}>
          {Math.round(pct)}%
        </span>
      </div>
      <div className="ajr-bar-track">
        <div
          className="ajr-bar-fill"
          style={{
            width: `${pct}%`,
            background: pct >= 100
              ? 'linear-gradient(90deg, #3fb950, #2ea043)'
              : pct >= 50
              ? `linear-gradient(90deg, ${color}, ${color}aa)`
              : 'linear-gradient(90deg, #f85149, #f85149aa)',
            boxShadow: `0 0 8px ${pct >= 50 ? color : '#f85149'}40`,
          }}
        />
        {/* Marqueur 50% */}
        <div className="ajr-bar-marker ajr-bar-marker--50" />
      </div>
      <div className="ajr-bar-footer">
        <span>0</span>
        <span className="ajr-bar-target">AJR : {ajr >= 100 ? Math.round(ajr) : ajr} {meta?.unit}</span>
      </div>
    </div>
  );
}

// ── Carte carence ─────────────────────────────────────────────────────────────

function DeficiencyCard({ deficiency }) {
  const { nutrient, ratio, severity } = deficiency;
  const cfg  = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;
  const tip  = NUTRIENT_TIPS[nutrient];
  const name = NUTRIENT_LABELS[nutrient] || nutrient;
  const pct  = Math.round(ratio * 100);

  return (
    <div className="deficiency-card" style={{ borderColor: cfg.border, background: cfg.bg }}>
      <div className="deficiency-card-header">
        <span className="deficiency-icon">{cfg.icon}</span>
        <div className="deficiency-info">
          <span className="deficiency-name">{name}</span>
          <span className="deficiency-severity" style={{ color: cfg.color }}>{cfg.label}</span>
        </div>
        <div className="deficiency-pct" style={{ color: cfg.color }}>{pct}%</div>
      </div>
      <div className="deficiency-bar-track">
        <div className="deficiency-bar-fill" style={{ width: `${pct}%`, background: cfg.color }} />
      </div>
      {tip && (
        <p className="deficiency-tip">
          <span style={{ color: cfg.color }}>💡</span> {tip}
        </p>
      )}
    </div>
  );
}

// ── Vue recette — AJR depuis recipe.nutrition ──────────────────────────────────

function RecipeNutritionView() {
  const [recipe,  setRecipe]  = useState(null);
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);

  // Écoute l'event + lit la recette en attente stockée avant navigation
  useEffect(() => {
    if (window.__alim_pending_recipe) {
      setRecipe(window.__alim_pending_recipe);
      window.__alim_pending_recipe = null;
    }
    const handler = (e) => {
      setRecipe(e.detail);
      setResult(null);
      setError(null);
    };
    window.addEventListener('alim:recipe-selected', handler);
    return () => window.removeEventListener('alim:recipe-selected', handler);
  }, []);

  const nutrRaw = recipe?.nutrition || recipe?._nutrition || {};

  // Map recipe nutrition keys → NUTRIENT_META keys
  const normalize = (n) => {
    const out = { ...n };
    if (out.proteins !== undefined && out.protein === undefined) out.protein = out.proteins;
    if (out.kcal_per_serving !== undefined && out.calories === undefined) out.calories = out.kcal_per_serving;
    return out;
  };

  const nutr = normalize(nutrRaw);

  const analyzeRecipe = async () => {
    if (!recipe) return;
    setLoading(true); setError(null); setResult(null);
    try {
      const data = await nutritionApi.ajrScore({ nutrition: nutr });
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const detailEntries = useMemo(() => {
    if (!result?.details) return [];
    return Object.entries(result.details)
      .map(([key, d]) => ({ key, ...d }))
      .sort((a, b) => a.ratio - b.ratio);
  }, [result]);

  if (!recipe) {
    return (
      <div className="nutr-empty" style={{ marginTop: 40 }}>
        <div className="nutr-empty-icon">◉</div>
        <h3>Aucune recette sélectionnée</h3>
        <p style={{ marginBottom: 20 }}>
          Cliquez sur <strong>"Voir l'AJR"</strong> depuis une fiche recette pour analyser sa contribution nutritionnelle.
        </p>
        <button onClick={() => navigate('/')} style={{
          padding: '10px 20px', borderRadius: 8, background: 'var(--grn)',
          color: 'var(--bg)', border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 500,
        }}>
          Explorer les recettes →
        </button>
      </div>
    );
  }

  const title = recipe.titles?.fr || recipe.title_fr || recipe.title || 'Recette';

  // AJR direct depuis nutrition du recipe (sans appel API)
  const directBars = Object.entries(NUTRIENT_META)
    .filter(([k]) => nutr[k] != null && nutr[k] > 0)
    .map(([k, meta]) => ({
      key: k, value: nutr[k], ajr: meta.ajr, color: meta.color,
      ratio: nutr[k] / meta.ajr,
    }))
    .sort((a, b) => a.ratio - b.ratio);

  return (
    <div>
      {/* Recipe header */}
      <div className="frigo-panel" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 4 }}>
            RECETTE ANALYSÉE
          </div>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 500 }}>{title}</h3>
          {recipe.total_time_min && (
            <span style={{ fontSize: 12, color: 'var(--mut)' }}>⏱ {recipe.total_time_min} min</span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button onClick={() => navigate(`/recette/${recipe.id || recipe._id}`)}
            style={{ padding: '8px 14px', borderRadius: 8, background: 'transparent', border: '1px solid var(--brd)', color: 'var(--txt2)', cursor: 'pointer', fontSize: 13 }}>
            Voir la recette →
          </button>
          <button onClick={analyzeRecipe} disabled={loading}
            style={{ padding: '8px 14px', borderRadius: 8, background: 'var(--grn)', border: 'none', color: 'var(--bg)', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>
            {loading ? '…' : '◉ Analyse IA'}
          </button>
        </div>
      </div>

      {error && <div className="state-msg state-msg--error" style={{ marginBottom: 16 }}>{error}</div>}

      {/* AJR direct depuis nutrition */}
      {directBars.length > 0 ? (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
            <h4 style={{ margin: 0, fontSize: 15, fontWeight: 500 }}>Contribution AJR · par portion</h4>
            <span style={{ fontSize: 11, color: 'var(--mut)' }}>AJR = Apports Journaliers Recommandés (ANSES)</span>
          </div>
          <div className="nutr-bars-grid">
            {directBars.map(({ key, value, ajr, color }) => (
              <AJRBar key={key} nutrient={key} value={value} ajr={ajr} color={color} />
            ))}
          </div>
        </div>
      ) : (
        <div className="state-msg" style={{ marginBottom: 16 }}>
          Données nutritionnelles non disponibles pour cette recette.
        </div>
      )}

      {/* Résultat analyse IA */}
      {result && (
        <div style={{ marginTop: 24 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <ScoreGauge score={result.ajr_score} />
            <div>
              <div style={{ fontSize: 13, color: 'var(--mut)' }}>Score AJR global</div>
              {result.deficiencies?.length > 0 && (
                <div style={{ fontSize: 12, color: '#f0883e', marginTop: 4 }}>
                  ⚠ {result.deficiencies.length} nutriment{result.deficiencies.length > 1 ? 's' : ''} en carence
                </div>
              )}
            </div>
          </div>
          {detailEntries.length > 0 && (
            <div className="nutr-details-table">
              {detailEntries.map(({ key, value, ref, ratio, ok }) => {
                const meta = NUTRIENT_META[key];
                const pct  = Math.round(ratio * 100);
                return (
                  <div key={key} className="nutr-detail-row">
                    <span className="nutr-detail-icon">{meta?.icon || '●'}</span>
                    <span className="nutr-detail-name">{meta?.label || key}</span>
                    <div className="nutr-detail-bar-wrap">
                      <div className="nutr-detail-bar-track">
                        <div className="nutr-detail-bar-fill" style={{
                          width: `${Math.min(100, pct)}%`,
                          background: ok ? (meta?.color || '#3fb950') : (pct >= 25 ? '#f0883e' : '#f85149'),
                        }} />
                      </div>
                    </div>
                    <span className="nutr-detail-pct" style={{ color: ok ? 'var(--grn)' : pct >= 25 ? '#f0883e' : '#f85149' }}>
                      {pct}%
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Vue semaine — AJR agrégé depuis le planning localStorage ──────────────────

function WeekNutritionView() {
  const [weekData, setWeekData] = useState(null);
  const [loading, setLoading]   = useState(false);

  const loadWeek = async () => {
    setLoading(true);
    try {
      const raw  = localStorage.getItem(PLAN_KEY);
      const plan = raw ? JSON.parse(raw) : null;
      if (!plan) { setWeekData({ empty: true }); return; }

      // Collect all recipe IDs from plan
      const recipeMap = {};
      for (const dk of DAYS_KEY) {
        for (const m of MEAL_ORDER) {
          const slot = plan[dk]?.[m];
          if (!slot || slot.skip) continue;
          for (const r of (slot.recipes || [])) {
            if (r?.id) {
              const cached = recipeStore.get(r.id);
              recipeMap[r.id] = cached || { id: r.id, title_fr: r.title_fr || r.title || r.id, _fromPlan: true };
            }
          }
        }
      }

      const recipes = Object.values(recipeMap);
      if (recipes.length === 0) { setWeekData({ empty: true }); return; }

      // Aggregate nutrition
      const agg = {};
      let count = 0;
      for (const r of recipes) {
        const n = r.nutrition || r._nutrition || {};
        const norm = { ...n };
        if (norm.proteins !== undefined && norm.protein === undefined) norm.protein = norm.proteins;
        if (norm.kcal_per_serving !== undefined && norm.calories === undefined) norm.calories = norm.kcal_per_serving;
        let hasData = false;
        for (const [k, meta] of Object.entries(NUTRIENT_META)) {
          if (norm[k] != null && norm[k] > 0) {
            agg[k] = (agg[k] || 0) + norm[k];
            hasData = true;
          }
        }
        if (hasData) count++;
      }

      setWeekData({ recipes, agg, count, total: recipes.length });
    } catch { setWeekData({ empty: true }); }
    finally { setLoading(false); }
  };

  useEffect(() => { loadWeek(); }, []);

  if (loading) return (
    <div className="nutr-loading"><div className="nutr-loading-ring" /><p>Chargement du planning…</p></div>
  );

  if (!weekData || weekData.empty) return (
    <div className="nutr-empty" style={{ marginTop: 40 }}>
      <div className="nutr-empty-icon">▦</div>
      <h3>Aucun planning trouvé</h3>
      <p>Créez un planning hebdomadaire pour voir l'analyse nutritionnelle de la semaine.</p>
      <button onClick={() => navigate('/planning')} style={{
        marginTop: 12, padding: '10px 20px', borderRadius: 8, background: 'var(--grn)',
        color: 'var(--bg)', border: 'none', cursor: 'pointer', fontSize: 14, fontWeight: 500,
      }}>
        Créer un planning →
      </button>
    </div>
  );

  const { recipes, agg, count, total } = weekData;
  const weekBars = Object.entries(NUTRIENT_META)
    .filter(([k]) => agg[k] != null && agg[k] > 0)
    .map(([k, meta]) => ({
      key: k,
      value: Math.round(agg[k] * 10) / 10,
      ajr: meta.ajr * 7,  // AJR × 7 jours
      color: meta.color,
      ratio: agg[k] / (meta.ajr * 7),
    }))
    .sort((a, b) => a.ratio - b.ratio);

  return (
    <div>
      {/* Summary header */}
      <div className="frigo-panel" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 20, flexWrap: 'wrap' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 4 }}>
            SEMAINE EN COURS
          </div>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 500 }}>Bilan nutritionnel hebdomadaire</h3>
          <div style={{ fontSize: 13, color: 'var(--txt2)', marginTop: 6 }}>
            {total} recette{total > 1 ? 's' : ''} dans le planning
            {count < total && ` · ${count} avec données nutritionnelles`}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={loadWeek} style={{ padding: '8px 14px', borderRadius: 8, background: 'transparent', border: '1px solid var(--brd)', color: 'var(--txt2)', cursor: 'pointer', fontSize: 13 }}>
            ↺ Actualiser
          </button>
          <button onClick={() => navigate('/planning')} style={{ padding: '8px 14px', borderRadius: 8, background: 'var(--grn)', border: 'none', color: 'var(--bg)', cursor: 'pointer', fontSize: 13, fontWeight: 500 }}>
            Voir le planning →
          </button>
        </div>
      </div>

      {/* Recipes list */}
      <div style={{ marginBottom: 20 }}>
        <h4 style={{ fontSize: 14, fontWeight: 500, marginBottom: 10 }}>Recettes analysées</h4>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
          {recipes.map(r => (
            <span key={r.id} onClick={() => navigate(`/recette/${r.id}`)} style={{
              padding: '5px 12px', borderRadius: 999, fontSize: 12,
              background: 'var(--sur2)', border: '1px solid var(--brd)',
              color: 'var(--txt2)', cursor: 'pointer',
            }}>
              {r.titles?.fr || r.title_fr || r.id}
            </span>
          ))}
        </div>
      </div>

      {/* Weekly AJR bars */}
      {weekBars.length > 0 ? (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 14 }}>
            <h4 style={{ margin: 0, fontSize: 15, fontWeight: 500 }}>Apports cumulés sur 7 jours</h4>
            <span style={{ fontSize: 11, color: 'var(--mut)' }}>vs AJR × 7 jours</span>
          </div>
          <div className="nutr-bars-grid">
            {weekBars.map(({ key, value, ajr, color }) => (
              <AJRBar key={key} nutrient={key} value={value} ajr={ajr} color={color} />
            ))}
          </div>
        </div>
      ) : (
        <div className="state-msg">
          Aucune donnée nutritionnelle trouvée pour les recettes du planning.<br />
          <span style={{ fontSize: 12, color: 'var(--mut)' }}>Essayez de consulter les fiches recettes pour charger leurs données.</span>
        </div>
      )}
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function NutritionPage() {
  const [view,     setView]     = useState(() => {
    // Auto-switch to recipe view if triggered by event
    return localStorage.getItem('alim_nutr_view') || 'apports';
  });
  const [intake,   setIntake]   = useState({});
  const [result,   setResult]   = useState(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState(null);
  const [activeTab, setActiveTab] = useState('macro');

  // Auto-switch to recipe view si recette en attente ou event
  useEffect(() => {
    if (window.__alim_pending_recipe) setView('recette');
    const handler = () => setView('recette');
    window.addEventListener('alim:recipe-selected', handler);
    return () => window.removeEventListener('alim:recipe-selected', handler);
  }, []);

  // Persist view preference
  useEffect(() => { localStorage.setItem('alim_nutr_view', view); }, [view]);

  const macros = Object.entries(NUTRIENT_META).filter(([, m]) => m.group === 'macro');
  const micros = Object.entries(NUTRIENT_META).filter(([, m]) => m.group === 'micro');
  const displayed = activeTab === 'macro' ? macros : micros;

  const analyze = async () => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await nutritionApi.ajrScore({ nutrition: intake });
      setResult(data);
    } catch (err) {
      setError(err.message || 'Erreur lors de l\'analyse.');
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setIntake({});
    setResult(null);
    setError(null);
  };

  const defGroups = useMemo(() => {
    if (!result?.deficiencies) return { high: [], medium: [] };
    return {
      high:   result.deficiencies.filter(d => d.severity === 'high'),
      medium: result.deficiencies.filter(d => d.severity === 'medium'),
    };
  }, [result]);

  const hasDeficiencies = defGroups.high.length + defGroups.medium.length > 0;

  const detailEntries = useMemo(() => {
    if (!result?.details) return [];
    return Object.entries(result.details)
      .map(([key, d]) => ({ key, ...d }))
      .sort((a, b) => a.ratio - b.ratio);
  }, [result]);

  return (
    <div className="page-nutrition">
      {/* ── Header ── */}
      <div className="page-header">
        <h1 className="page-title">
          <span className="page-icon">◉</span>
          Nutrition & AJR
        </h1>
        <p className="page-sub">
          Analysez vos apports journaliers et identifiez les carences fréquentes
          en alimentation végétale (ANSES/OMS).
        </p>
      </div>

      {/* ── Sélecteur de vue ── */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
        {[
          { key: 'apports', label: 'Mes apports',    icon: '✏️' },
          { key: 'recette', label: 'Recette',         icon: '🍽️' },
          { key: 'semaine', label: 'Ma semaine',      icon: '▦' },
        ].map(v => (
          <button key={v.key} onClick={() => setView(v.key)} style={{
            padding: '9px 18px', borderRadius: 10, fontSize: 13,
            border: `1px solid ${view === v.key ? 'var(--grn)' : 'var(--brd)'}`,
            background: view === v.key ? 'var(--grn)' : 'transparent',
            color: view === v.key ? 'var(--bg)' : 'var(--txt2)',
            cursor: 'pointer', fontFamily: 'inherit', fontWeight: view === v.key ? 500 : 400,
            display: 'inline-flex', alignItems: 'center', gap: 7, transition: 'all .12s',
          }}>
            <span>{v.icon}</span> {v.label}
          </button>
        ))}
      </div>

      {/* ── Vue Recette ── */}
      {view === 'recette' && <RecipeNutritionView />}

      {/* ── Vue Semaine ── */}
      {view === 'semaine' && <WeekNutritionView />}

      {/* ── Vue Apports (originale) ── */}
      {view === 'apports' && <div className="nutr-layout">
        {/* ── Panneau de saisie ── */}
        <div className="nutr-input-panel">
          <div className="nutr-panel-header">
            <h3 className="frigo-panel-title">Vos apports du jour</h3>
            {Object.keys(intake).length > 0 && (
              <button className="nutr-reset-btn" onClick={reset}>Réinitialiser</button>
            )}
          </div>

          {/* Tabs macro/micro */}
          <div className="nutr-tabs">
            {[['macro', 'Macronutriments'], ['micro', 'Micronutriments']].map(([t, l]) => (
              <button
                key={t}
                className={`nutr-tab ${activeTab === t ? 'nutr-tab--active' : ''}`}
                onClick={() => setActiveTab(t)}
              >
                {l}
              </button>
            ))}
          </div>

          <div className="nutr-inputs-list">
            {displayed.map(([key, meta]) => {
              const val    = intake[key] || '';
              const pct    = val ? Math.min(100, (parseFloat(val) / meta.ajr) * 100) : 0;
              const okRing = pct >= 50;
              return (
                <div key={key} className="nutr-input-row">
                  <div className="nutr-input-label">
                    <span className="nutr-input-icon">{meta.icon}</span>
                    <div>
                      <div className="nutr-input-name">{meta.label}</div>
                      <div className="nutr-input-ajr">AJR : {meta.ajr >= 100 ? Math.round(meta.ajr) : meta.ajr} {meta.unit}</div>
                    </div>
                  </div>
                  <div className="nutr-input-field-wrap">
                    <input
                      type="number"
                      min={0}
                      step={key === 'calories' ? 10 : 0.1}
                      placeholder="0"
                      value={val}
                      onChange={(e) => setIntake(p => ({ ...p, [key]: parseFloat(e.target.value) || 0 }))}
                      className="nutr-number-input"
                      style={{ borderColor: val && okRing ? meta.color + '60' : '' }}
                    />
                    <span className="nutr-input-unit">{meta.unit}</span>
                  </div>
                  {val > 0 && (
                    <div className="nutr-mini-bar-track">
                      <div
                        className="nutr-mini-bar-fill"
                        style={{
                          width: `${pct}%`,
                          background: okRing ? meta.color : '#f85149',
                        }}
                      />
                    </div>
                  )}
                </div>
              );
            })}
          </div>

          <button
            className="nutr-analyze-btn"
            onClick={analyze}
            disabled={loading || Object.keys(intake).length === 0}
          >
            {loading ? (
              <span className="nutr-btn-spinner" />
            ) : (
              <>◉ Analyser mes apports</>
            )}
          </button>

          {error && <div className="state-msg state-msg--error" style={{ marginTop: 16 }}>{error}</div>}
        </div>

        {/* ── Résultats ── */}
        <div className="nutr-results">
          {!result && !loading && (
            <div className="nutr-empty">
              <div className="nutr-empty-icon">◉</div>
              <h3>Saisissez vos apports</h3>
              <p>Entrez les quantités de chaque nutriment consommé aujourd'hui,
                puis cliquez sur « Analyser » pour obtenir votre bilan AJR.</p>
              <ul className="nutr-tips-list">
                <li>🌿 Commencez par les <strong>macronutriments</strong> (calories, protéines…)</li>
                <li>🔬 Ajoutez les <strong>micronutriments</strong> pour détecter les carences</li>
                <li>🎯 Référence ANSES/OMS pour un adulte standard de 2000 kcal/jour</li>
              </ul>
            </div>
          )}

          {loading && (
            <div className="nutr-loading">
              <div className="nutr-loading-ring" />
              <p>Analyse en cours…</p>
            </div>
          )}

          {result && (
            <div className="nutr-result-panel">

              {/* ── Score global ── */}
              <div className="nutr-score-card">
                <div className="nutr-score-left">
                  <ScoreGauge score={result.ajr_score} />
                  <div className="nutr-coverage">
                    Couverture : <strong>{Math.round((result.coverage || 0) * 100)}%</strong> des nutriments renseignés
                  </div>
                </div>
                <div className="nutr-score-summary">
                  <h3>Résumé de l'analyse</h3>
                  {!hasDeficiencies ? (
                    <div className="nutr-ok-msg">
                      <span>✅</span>
                      <span>Tous les apports renseignés couvrent au minimum 50% des AJR. Excellent travail !</span>
                    </div>
                  ) : (
                    <div className="nutr-defi-summary">
                      {defGroups.high.length > 0 && (
                        <div className="nutr-summary-pill nutr-summary-pill--high">
                          🚨 {defGroups.high.length} carence{defGroups.high.length > 1 ? 's' : ''} critique{defGroups.high.length > 1 ? 's' : ''}
                        </div>
                      )}
                      {defGroups.medium.length > 0 && (
                        <div className="nutr-summary-pill nutr-summary-pill--medium">
                          ⚠️ {defGroups.medium.length} carence{defGroups.medium.length > 1 ? 's' : ''} modérée{defGroups.medium.length > 1 ? 's' : ''}
                        </div>
                      )}
                    </div>
                  )}

                  {/* Détails par nutriment (table compacte) */}
                  {detailEntries.length > 0 && (
                    <div className="nutr-details-table">
                      {detailEntries.map(({ key, value, ref, ratio, ok }) => {
                        const meta = NUTRIENT_META[key];
                        const pct  = Math.round(ratio * 100);
                        return (
                          <div key={key} className="nutr-detail-row">
                            <span className="nutr-detail-icon">{meta?.icon || '●'}</span>
                            <span className="nutr-detail-name">{meta?.label || key}</span>
                            <div className="nutr-detail-bar-wrap">
                              <div className="nutr-detail-bar-track">
                                <div
                                  className="nutr-detail-bar-fill"
                                  style={{
                                    width: `${Math.min(100, pct)}%`,
                                    background: ok ? (meta?.color || '#3fb950') : (pct >= 25 ? '#f0883e' : '#f85149'),
                                  }}
                                />
                              </div>
                            </div>
                            <span
                              className="nutr-detail-pct"
                              style={{ color: ok ? 'var(--grn)' : pct >= 25 ? '#f0883e' : '#f85149' }}
                            >
                              {pct}%
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </div>
              </div>

              {/* ── Barres AJR complètes ── */}
              {detailEntries.length > 0 && (
                <div className="nutr-bars-section">
                  <h4 className="nutr-section-title">Détail par nutriment</h4>
                  <div className="nutr-bars-grid">
                    {detailEntries.map(({ key, value, ref }) => (
                      <AJRBar
                        key={key}
                        nutrient={key}
                        value={value}
                        ajr={ref}
                        color={NUTRIENT_META[key]?.color || '#58a6ff'}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* ── Carences ── */}
              {hasDeficiencies && (
                <div className="nutr-deficiencies-section">
                  <h4 className="nutr-section-title">
                    Carences détectées
                    <span className="nutr-section-badge">{defGroups.high.length + defGroups.medium.length}</span>
                  </h4>
                  <p className="nutr-section-sub">
                    Les nutriments suivants sont en dessous de 50% des apports journaliers recommandés.
                    Des conseils alimentaires végétaux vous sont proposés.
                  </p>

                  {defGroups.high.length > 0 && (
                    <>
                      <div className="nutr-severity-label" style={{ color: '#f85149' }}>
                        🚨 Carences critiques (&lt; 25% AJR)
                      </div>
                      <div className="nutr-defi-grid">
                        {defGroups.high.map(d => <DeficiencyCard key={d.nutrient} deficiency={d} />)}
                      </div>
                    </>
                  )}

                  {defGroups.medium.length > 0 && (
                    <>
                      <div className="nutr-severity-label" style={{ color: '#f0883e', marginTop: defGroups.high.length ? 24 : 0 }}>
                        ⚠️ Carences modérées (25–50% AJR)
                      </div>
                      <div className="nutr-defi-grid">
                        {defGroups.medium.map(d => <DeficiencyCard key={d.nutrient} deficiency={d} />)}
                      </div>
                    </>
                  )}
                </div>
              )}

            </div>
          )}
        </div>
      </div>}
    </div>
  );
}
