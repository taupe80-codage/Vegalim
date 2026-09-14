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
import { useToast } from '../ToastContext';
import { nutrition as nutritionApi, recipes as recipesApi } from '../api';
import { navigate } from '../Router';

const PLAN_KEY  = 'alim_plan_weekly';
const DAYS_KEY  = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche'];
const MEAL_KEYS = ['breakfast','lunch','dinner'];

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

// ── Profil & Journal ──────────────────────────────────────────────────────────

const PROFILE_KEY     = 'alim_nutr_profile';
const JOURNAL_KEY     = 'alim_journal_today';
const PROFILE_DEFAULT = { diet: 'vegan', sex: 'female', age: '26-35', activity: 'moderate' };

const DIET_OPTIONS = [
  { id: 'vegan',      label: 'Vegan',      icon: '🌱' },
  { id: 'vegetarian', label: 'Végétarien', icon: '🥚' },
];
const SEX_OPTIONS = [
  { id: 'female', label: 'Féminin',  icon: '♀' },
  { id: 'male',   label: 'Masculin', icon: '♂' },
];
const AGE_OPTIONS = [
  { id: '18-25', label: '18–25 ans' },
  { id: '26-35', label: '26–35 ans' },
  { id: '36-50', label: '36–50 ans' },
  { id: '51+',   label: '51 ans +'  },
];
const ACTIVITY_OPTIONS = [
  { id: 'sedentary', label: 'Sédentaire', icon: '🛋️' },
  { id: 'light',     label: 'Légère',     icon: '🚶' },
  { id: 'moderate',  label: 'Modérée',    icon: '🚴' },
  { id: 'active',    label: 'Active',     icon: '🏃' },
];
const MEAL_LABELS = {
  breakfast: '🌅 Petit-déj',
  lunch:     '☀️ Déjeuner',
  dinner:    '🌙 Dîner',
  snack:     '🍎 En-cas',
};

function calcPersonalizedAJR(p) {
  const b = {};
  for (const [k, m] of Object.entries(NUTRIENT_META)) b[k] = m.ajr;
  const cals = { sedentary: 1800, light: 2000, moderate: 2200, active: 2600 };
  const prot = { sedentary: 46,   light: 52,   moderate: 58,   active: 72   };
  b.calories = cals[p.activity] || 2000;
  b.protein  = prot[p.activity] || 50;
  if (p.sex === 'female')   b.iron     = 16;
  if (p.age === '51+')    { b.calcium  = 1200; b.vitamin_d = 20; }
  if (p.diet === 'vegan') { b.iron = Math.round((b.iron || 14) * 1.2); b.protein = Math.round(b.protein * 1.1); }
  return b;
}

// ── Données carences végétales ────────────────────────────────────────────────

const DEFICIENCIES = [
  {
    id: 'vitamin_b12', name: 'Vitamine B12', icon: '🧬', color: '#3fb950',
    riskByDiet: { vegan: 'high', vegetarian: 'medium', flexitarian: 'low', omnivore: 'low' },
    riskBySex: {}, riskByAge: { '51+': 'medium' },
    desc: "Essentielle au système nerveux et aux globules rouges. Absente des végétaux — la supplémentation est indispensable pour les vegans.",
    symptoms: ['Fatigue profonde', 'Fourmillements', 'Troubles de mémoire', 'Anémie'],
    sources: ['Levure nutritionnelle enrichie', 'Boissons végétales enrichies', 'Supplémentation 1 000 µg/sem.'],
    tip: "La B12 est le seul nutriment dont la supplémentation est obligatoire en régime vegan. Ne pas attendre les symptômes.",
    sortKey: null,
  },
  {
    id: 'iron', name: 'Fer', icon: '🩸', color: '#f85149',
    riskByDiet: { vegan: 'high', vegetarian: 'medium', flexitarian: 'low', omnivore: 'low' },
    riskBySex: { female: 'medium' }, riskByAge: {},
    desc: "Le fer végétal (non-héminique) est 2 à 3× moins absorbé que le fer animal. La vitamine C consommée au même repas multiplie son absorption.",
    symptoms: ['Fatigue & essoufflement', 'Teint pâle', 'Ongles cassants', 'Concentration difficile'],
    sources: ['Lentilles corail', 'Pois chiches', 'Tofu ferme', 'Graines de courge', 'Betterave'],
    tip: "Associez toujours une source de vitamine C (citron, kiwi, poivron) à vos aliments riches en fer végétal.",
    sortKey: 'iron',
  },
  {
    id: 'calcium', name: 'Calcium', icon: '🦴', color: '#58a6ff',
    riskByDiet: { vegan: 'high', vegetarian: 'low', flexitarian: 'low', omnivore: 'low' },
    riskBySex: { female: 'low' }, riskByAge: { '51+': 'medium' },
    desc: "Sans produits laitiers, le calcium doit venir des végétaux. Les oxalates (épinards) bloquent son absorption — préférez brocoli, kale, tofu au calcium.",
    symptoms: ['Crampes musculaires', 'Fragilité dentaire', 'Ostéoporose à long terme'],
    sources: ["Tofu au sulfate de calcium", "Chou kale & brocoli", "Amandes", "Boissons végétales enrichies"],
    tip: "Le tofu au sulfate de calcium est l'une des meilleures sources végétales — vérifiez l'étiquette.",
    sortKey: null,
  },
  {
    id: 'vitamin_d', name: 'Vitamine D', icon: '☀️', color: '#f0c27f',
    riskByDiet: { vegan: 'high', vegetarian: 'medium', flexitarian: 'low', omnivore: 'low' },
    riskBySex: {}, riskByAge: { '51+': 'high' },
    desc: "Synthétisée par la peau au soleil. En automne-hiver, la carence est quasi-universelle en Europe. Essentielle pour les os, l'immunité et l'humeur.",
    symptoms: ['Fatigue chronique', 'Douleurs osseuses', 'Immunité réduite', 'Dépression saisonnière'],
    sources: ['Exposition solaire 15–20 min/j', 'Champignons Shiitaké séchés UV', 'Supplémentation D3 vegan'],
    tip: "En automne-hiver, 1 000–2 000 UI/j de D3 est recommandé. Choisissez une D3 vegan (lichen ou algues).",
    sortKey: null,
  },
  {
    id: 'zinc', name: 'Zinc', icon: '⚡', color: '#f0883e',
    riskByDiet: { vegan: 'medium', vegetarian: 'medium', flexitarian: 'low', omnivore: 'low' },
    riskBySex: {}, riskByAge: {},
    desc: "Le zinc végétal est bloqué par les phytates des légumineuses et céréales. Trempage et fermentation améliorent sa biodisponibilité de 50%.",
    symptoms: ['Immunité réduite', 'Cicatrisation lente', 'Perte de goût', 'Chute de cheveux'],
    sources: ['Graines de courge', 'Noix de cajou', 'Tempeh', 'Avoine trempée', 'Pois chiches'],
    tip: "Faites tremper légumineuses et céréales 8–12h pour réduire les phytates jusqu'à 50%.",
    sortKey: 'zinc',
  },
  {
    id: 'omega3', name: 'Oméga-3 DHA/EPA', icon: '🌊', color: '#2980B9',
    riskByDiet: { vegan: 'high', vegetarian: 'medium', flexitarian: 'low', omnivore: 'low' },
    riskBySex: {}, riskByAge: {},
    desc: "L'ALA (lin, chia, noix) est peu converti en DHA/EPA actifs. Pour le cerveau et le cœur, l'huile d'algues est la seule source vegan directe de DHA.",
    symptoms: ['Peau & cheveux secs', 'Concentration difficile', 'Humeur instable', 'Inflammation'],
    sources: ["Graines de lin moulues", "Graines de chia", "Noix", "Algues & spiruline", "Huile d'algues DHA"],
    tip: "Visez 200–300 mg de DHA/j via huile d'algues. Les sources ALA (lin, chia) sont bénéfiques mais insuffisantes seules.",
    sortKey: null,
  },
  {
    id: 'iodine', name: 'Iode', icon: '🧂', color: '#a371f7',
    riskByDiet: { vegan: 'high', vegetarian: 'medium', flexitarian: 'low', omnivore: 'low' },
    riskBySex: {}, riskByAge: {},
    desc: "Essentiel à la thyroïde. Sans poissons ni produits laitiers, les sources végétales sont rares. Le sel iodé est la solution la plus simple.",
    symptoms: ['Hypothyroïdie', 'Fatigue', 'Prise de poids', 'Frilosité', 'Concentration réduite'],
    sources: ['Sel iodé (½ cuillère/j)', 'Algues avec modération', 'Boissons végétales enrichies'],
    tip: "Utilisez du sel iodé. Limitez les algues à 1–2 portions/semaine (le kombu contient trop d'iode).",
    sortKey: null,
  },
  {
    id: 'selenium', name: 'Sélénium', icon: '🔬', color: '#52c47a',
    riskByDiet: { vegan: 'medium', vegetarian: 'low', flexitarian: 'low', omnivore: 'low' },
    riskBySex: {}, riskByAge: {},
    desc: "Oligo-élément antioxydant essentiel. Sa teneur dans les végétaux dépend du sol — souvent faible en Europe. La noix du Brésil est la source la plus concentrée.",
    symptoms: ['Immunité réduite', 'Fatigue', 'Problèmes thyroïdiens', 'Chute de cheveux'],
    sources: ['Noix du Brésil 1–2/j', 'Graines de tournesol', 'Champignons', 'Légumineuses'],
    tip: "1 à 2 noix du Brésil par jour couvrent 100–200% des besoins en sélénium. Ne pas dépasser 3–4/jour.",
    sortKey: null,
  },
];

const RISK_CONFIG = {
  high:   { label: 'Risque élevé',  color: '#f85149', bg: 'rgba(248,81,73,0.08)',  icon: '🚨' },
  medium: { label: 'Risque modéré', color: '#f0883e', bg: 'rgba(240,136,62,0.08)', icon: '⚠️' },
  low:    { label: 'Risque faible', color: '#3fb950', bg: 'rgba(63,185,80,0.06)',  icon: '✓'  },
};

function getRisk(def, profile) {
  const lvl = { high: 3, medium: 2, low: 1 };
  const max = Math.max(
    lvl[def.riskByDiet[profile.diet] || 'low'],
    lvl[def.riskBySex[profile.sex]   || 'low'],
    lvl[def.riskByAge[profile.age]   || 'low'],
  );
  return max === 3 ? 'high' : max === 2 ? 'medium' : 'low';
}

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

// ── Vue Profil + Journal alimentaire ─────────────────────────────────────────

function ProfilJournalView() {
  const toast = useToast();
  const [profile, setProfile] = useState(() => {
    try { return { ...PROFILE_DEFAULT, ...JSON.parse(localStorage.getItem(PROFILE_KEY) || '{}') }; }
    catch { return { ...PROFILE_DEFAULT }; }
  });

  const [journal, setJournal] = useState(() => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const raw   = JSON.parse(localStorage.getItem(JOURNAL_KEY) || '{}');
      return raw.date === today ? (raw.entries || []) : [];
    } catch { return []; }
  });

  const [mealType,      setMealType]      = useState('lunch');
  const [searchQ,       setSearchQ]       = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [searching,     setSearching]     = useState(false);
  const [addingId,      setAddingId]      = useState(null);

  useEffect(() => { localStorage.setItem(PROFILE_KEY, JSON.stringify(profile)); }, [profile]);

  useEffect(() => {
    const today = new Date().toISOString().split('T')[0];
    localStorage.setItem(JOURNAL_KEY, JSON.stringify({ date: today, entries: journal }));
  }, [journal]);

  useEffect(() => {
    if (!searchQ.trim() || searchQ.length < 2) { setSearchResults([]); return; }
    const tid = setTimeout(async () => {
      setSearching(true);
      try {
        const raw  = await recipesApi.search({ query: searchQ.trim(), limit: 7 });
        setSearchResults(Array.isArray(raw) ? raw : (raw?.results || raw?.recipes || []));
      } catch { setSearchResults([]); }
      finally { setSearching(false); }
    }, 280);
    return () => clearTimeout(tid);
  }, [searchQ]);

  const addToJournal = async (recipe) => {
    setSearchQ(''); setSearchResults([]);
    setAddingId(recipe.id);
    try {
      let full = recipe;
      if (!recipe.nutrition && recipe.id) {
        try { full = await recipesApi.byId(recipe.id); } catch { /* repli sur la recette partielle déjà affichée */ }
      }
      const raw = full?.nutrition || full?._nutrition || {};
      const n = { ...raw };
      if (n.proteins !== undefined && n.protein === undefined) n.protein = n.proteins;
      if (n.kcal_per_serving !== undefined && n.calories === undefined) n.calories = n.kcal_per_serving;
      setJournal(prev => [...prev, {
        id:         `${Date.now()}-${recipe.id}`,
        mealType,
        recipeId:   String(recipe.id),
        recipeName: full?.titles?.fr || full?.title_fr || full?.title || 'Recette',
        nutrition:  n,
      }]);
    } catch (err) {
      toast(`Impossible d'ajouter la recette : ${err.message || 'erreur réseau'}`, 'error');
    } finally { setAddingId(null); }
  };

  const removeEntry = (id) => setJournal(prev => prev.filter(e => e.id !== id));

  const personalAJR = useMemo(() => calcPersonalizedAJR(profile), [profile]);

  const totalNutrition = useMemo(() => {
    const tot = {};
    for (const entry of journal) {
      for (const k of Object.keys(NUTRIENT_META)) {
        const v = entry.nutrition?.[k];
        if (v != null) tot[k] = (tot[k] || 0) + v;
      }
    }
    return tot;
  }, [journal]);

  const today = new Date().toLocaleDateString('fr-FR', { weekday: 'long', day: 'numeric', month: 'long' });

  const sectionLabel = (text) => (
    <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase',
      letterSpacing: '0.08em', color: 'var(--mut)', marginBottom: 7 }}>
      {text}
    </div>
  );

  return (
    <div>
      {/* ── Profil ── */}
      <section style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
          <span style={{ fontSize: 20 }}>🎯</span>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--txt)' }}>Mon profil nutritionnel</h3>
          <span style={{ fontSize: 11, color: 'var(--mut)' }}>· Enregistré automatiquement</span>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }}>
          {/* Régime */}
          <div>
            {sectionLabel("Régime alimentaire")}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {DIET_OPTIONS.map(o => (
                <button key={o.id} onClick={() => setProfile(p => ({ ...p, diet: o.id }))} style={{
                  padding: '7px 10px', borderRadius: 8, textAlign: 'left', cursor: 'pointer',
                  background: profile.diet === o.id ? 'var(--grn-dim)' : 'var(--sur)',
                  border: `1px solid ${profile.diet === o.id ? 'var(--grn)' : 'var(--brd)'}`,
                  color: profile.diet === o.id ? 'var(--grn)' : 'var(--txt2)',
                  fontSize: 13, fontWeight: profile.diet === o.id ? 600 : 400,
                  display: 'flex', alignItems: 'center', gap: 7, transition: 'all .12s',
                  fontFamily: 'inherit', width: '100%',
                }}>
                  <span>{o.icon}</span>{o.label}
                </button>
              ))}
            </div>
          </div>

          {/* Sexe */}
          <div>
            {sectionLabel("Sexe biologique")}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {SEX_OPTIONS.map(o => (
                <button key={o.id} onClick={() => setProfile(p => ({ ...p, sex: o.id }))} style={{
                  padding: '7px 10px', borderRadius: 8, textAlign: 'left', cursor: 'pointer',
                  background: profile.sex === o.id ? 'var(--grn-dim)' : 'var(--sur)',
                  border: `1px solid ${profile.sex === o.id ? 'var(--grn)' : 'var(--brd)'}`,
                  color: profile.sex === o.id ? 'var(--grn)' : 'var(--txt2)',
                  fontSize: 13, fontWeight: profile.sex === o.id ? 600 : 400,
                  display: 'flex', alignItems: 'center', gap: 7, transition: 'all .12s',
                  fontFamily: 'inherit', width: '100%',
                }}>
                  <span style={{ fontSize: 15 }}>{o.icon}</span>{o.label}
                </button>
              ))}
            </div>
          </div>

          {/* Âge */}
          <div>
            {sectionLabel("Tranche d'âge")}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {AGE_OPTIONS.map(o => (
                <button key={o.id} onClick={() => setProfile(p => ({ ...p, age: o.id }))} style={{
                  padding: '7px 10px', borderRadius: 8, textAlign: 'left', cursor: 'pointer',
                  background: profile.age === o.id ? 'var(--grn-dim)' : 'var(--sur)',
                  border: `1px solid ${profile.age === o.id ? 'var(--grn)' : 'var(--brd)'}`,
                  color: profile.age === o.id ? 'var(--grn)' : 'var(--txt2)',
                  fontSize: 13, fontWeight: profile.age === o.id ? 600 : 400,
                  display: 'flex', alignItems: 'center', gap: 7, transition: 'all .12s',
                  fontFamily: 'inherit', width: '100%',
                }}>
                  {o.label}
                </button>
              ))}
            </div>
          </div>

          {/* Activité */}
          <div>
            {sectionLabel("Niveau d'activité")}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 5 }}>
              {ACTIVITY_OPTIONS.map(o => (
                <button key={o.id} onClick={() => setProfile(p => ({ ...p, activity: o.id }))} style={{
                  padding: '7px 10px', borderRadius: 8, textAlign: 'left', cursor: 'pointer',
                  background: profile.activity === o.id ? 'var(--grn-dim)' : 'var(--sur)',
                  border: `1px solid ${profile.activity === o.id ? 'var(--grn)' : 'var(--brd)'}`,
                  color: profile.activity === o.id ? 'var(--grn)' : 'var(--txt2)',
                  fontSize: 13, fontWeight: profile.activity === o.id ? 600 : 400,
                  display: 'flex', alignItems: 'center', gap: 7, transition: 'all .12s',
                  fontFamily: 'inherit', width: '100%',
                }}>
                  <span>{o.icon}</span>{o.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* AJR summary strip */}
        <div style={{ marginTop: 14, padding: '10px 16px', background: 'var(--grn-dim)',
          borderRadius: 10, border: '1px solid var(--brd)',
          display: 'flex', gap: 20, flexWrap: 'wrap', alignItems: 'center' }}>
          <span style={{ fontSize: 12, color: 'var(--grn)', fontWeight: 600 }}>✓ AJR personnalisés calculés</span>
          {[['calories','🔥'],['protein','💪'],['iron','🩸'],['calcium','🦴'],['vitamin_d','☀️']].map(([k, ic]) => {
            const m = NUTRIENT_META[k];
            return (
              <span key={k} style={{ fontSize: 12, color: 'var(--txt2)' }}>
                {ic} {m.label} : <strong style={{ color: 'var(--txt)' }}>
                  {personalAJR[k] >= 100 ? Math.round(personalAJR[k]) : personalAJR[k]} {m.unit}
                </strong>
              </span>
            );
          })}
        </div>
      </section>

      {/* ── Journal du jour ── */}
      <section style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
          <span style={{ fontSize: 20 }}>📓</span>
          <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--txt)' }}>Journal du jour</h3>
          <span style={{ fontSize: 12, color: 'var(--mut)' }}>{today}</span>
          {journal.length > 0 && (
            <button onClick={() => setJournal([])} style={{
              marginLeft: 'auto', fontSize: 11, color: '#f85149',
              background: 'transparent', border: '1px solid var(--brd)',
              borderRadius: 6, padding: '3px 10px', cursor: 'pointer', fontFamily: 'inherit',
            }}>
              Vider le journal
            </button>
          )}
        </div>

        {/* Meal type selector */}
        <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
          {Object.entries(MEAL_LABELS).map(([k, l]) => (
            <button key={k} onClick={() => setMealType(k)} style={{
              padding: '6px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
              background: mealType === k ? 'var(--grn)' : 'transparent',
              color: mealType === k ? '#fff' : 'var(--txt2)',
              border: `1px solid ${mealType === k ? 'var(--grn)' : 'var(--brd)'}`,
              fontFamily: 'inherit', fontWeight: mealType === k ? 500 : 400, transition: 'all .12s',
            }}>
              {l}
            </button>
          ))}
        </div>

        {/* Recipe search */}
        <div style={{ position: 'relative', marginBottom: 14 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8,
            background: 'var(--sur)', border: '1px solid var(--brd)',
            borderRadius: 10, padding: '10px 14px' }}>
            <span style={{ color: 'var(--mut)', fontSize: 14 }}>🔍</span>
            <input
              type="text"
              value={searchQ}
              onChange={e => setSearchQ(e.target.value)}
              onBlur={() => setTimeout(() => setSearchResults([]), 200)}
              placeholder="Ajouter une recette ALIM au journal…"
              style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none',
                color: 'var(--txt)', fontSize: 13, fontFamily: 'inherit' }}
            />
            {searching && <span style={{ color: 'var(--mut)', fontSize: 12 }}>…</span>}
            {addingId && <span style={{ fontSize: 11, color: 'var(--mut)' }}>Ajout…</span>}
          </div>
          {searchResults.length > 0 && (
            <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 50,
              background: 'var(--sur)', border: '1px solid var(--brd)', borderRadius: 10,
              boxShadow: '0 8px 24px rgba(0,0,0,0.15)', marginTop: 4, overflow: 'hidden' }}>
              {searchResults.map(r => (
                <button key={r.id} onMouseDown={() => addToJournal(r)} style={{
                  display: 'block', width: '100%', padding: '10px 14px', textAlign: 'left',
                  background: 'none', border: 'none', borderBottom: '1px solid var(--brd)',
                  cursor: 'pointer', color: 'var(--txt)', fontSize: 13, fontFamily: 'inherit',
                }}>
                  <div style={{ fontWeight: 500 }}>
                    {r.titles?.fr || r.title_fr || r.title || 'Recette'}
                  </div>
                  {r.nutrition?.calories && (
                    <div style={{ fontSize: 11, color: 'var(--mut)' }}>
                      {Math.round(r.nutrition.calories)} kcal
                    </div>
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Journal entries */}
        {journal.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '28px 20px', background: 'var(--sur)',
            borderRadius: 12, border: '1px solid var(--brd)', color: 'var(--mut)', fontSize: 13 }}>
            <div style={{ fontSize: 28, marginBottom: 8 }}>📋</div>
            Aucun repas enregistré aujourd'hui.<br />
            Recherchez des recettes ALIM pour démarrer votre suivi.
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 8 }}>
            {journal.map(entry => (
              <div key={entry.id} style={{ padding: '10px 12px', background: 'var(--sur)',
                borderRadius: 10, border: '1px solid var(--brd)',
                display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontSize: 16, flexShrink: 0 }}>
                  {MEAL_LABELS[entry.mealType]?.split(' ')[0]}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--txt)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {entry.recipeName}
                  </div>
                  <div style={{ fontSize: 11, color: 'var(--mut)' }}>
                    {MEAL_LABELS[entry.mealType]?.split(' ').slice(1).join(' ')}
                    {entry.nutrition?.calories ? ` · ${Math.round(entry.nutrition.calories)} kcal` : ''}
                  </div>
                </div>
                <button onClick={() => removeEntry(entry.id)} style={{
                  background: 'none', border: 'none', color: 'var(--mut)',
                  cursor: 'pointer', fontSize: 14, padding: '2px 4px',
                  lineHeight: 1, flexShrink: 0,
                }}>✕</button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* ── Bilan AJR du jour ── */}
      {journal.length > 0 && (
        <section>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 16 }}>
            <span style={{ fontSize: 20 }}>📊</span>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--txt)' }}>
              Bilan du jour vs vos AJR personnalisés
            </h3>
          </div>
          {Object.keys(totalNutrition).length === 0 ? (
            <p style={{ color: 'var(--mut)', fontSize: 13 }}>
              Aucune donnée nutritionnelle disponible pour les recettes ajoutées.
            </p>
          ) : (
            <div className="nutr-bars-grid">
              {Object.entries(NUTRIENT_META)
                .filter(([k]) => totalNutrition[k] != null)
                .map(([k, meta]) => (
                  <AJRBar
                    key={k}
                    nutrient={k}
                    value={Math.round(totalNutrition[k] * 10) / 10}
                    ajr={personalAJR[k] || meta.ajr}
                    color={meta.color}
                  />
                ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}

// ── Vue Guide carences végétales ──────────────────────────────────────────────

function CarencesView({ onGoToProfile }) {
  const [filter,   setFilter]   = useState('all');
  const [expanded, setExpanded] = useState(null);

  const profile = useMemo(() => {
    try { return { ...PROFILE_DEFAULT, ...JSON.parse(localStorage.getItem(PROFILE_KEY) || '{}') }; }
    catch { return { ...PROFILE_DEFAULT }; }
  }, []);

  const defsWithRisk = useMemo(
    () => DEFICIENCIES.map(d => ({ ...d, riskLevel: getRisk(d, profile) })),
    [profile]
  );

  const displayed = filter === 'atrisk'
    ? defsWithRisk.filter(d => d.riskLevel !== 'low')
    : defsWithRisk;

  const dietLabel = DIET_OPTIONS.find(o => o.id === profile.diet);
  const sexLabel  = SEX_OPTIONS.find(o => o.id === profile.sex);
  const ageLabel  = AGE_OPTIONS.find(o => o.id === profile.age);

  return (
    <div>
      {/* Header + filtres */}
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
            <span style={{ fontSize: 20 }}>🔬</span>
            <h3 style={{ margin: 0, fontSize: 16, fontWeight: 600, color: 'var(--txt)' }}>
              Guide des carences végétales
            </h3>
          </div>
          <p style={{ margin: 0, fontSize: 12, color: 'var(--mut)' }}>
            Basé sur votre profil : {dietLabel?.icon} {dietLabel?.label}
            {' · '}{sexLabel?.label}{' · '}{ageLabel?.label}
            {' — '}
            <button onClick={onGoToProfile} style={{
              background: 'none', border: 'none', padding: 0,
              color: 'var(--grn)', cursor: 'pointer', fontSize: 12, fontFamily: 'inherit',
            }}>
              Modifier le profil
            </button>
          </p>
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          <button onClick={() => setFilter('all')} style={{
            padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
            background: filter === 'all' ? 'var(--grn)' : 'transparent',
            color: filter === 'all' ? '#fff' : 'var(--txt2)',
            border: `1px solid ${filter === 'all' ? 'var(--grn)' : 'var(--brd)'}`,
            fontFamily: 'inherit', transition: 'all .12s',
          }}>Toutes</button>
          <button onClick={() => setFilter('atrisk')} style={{
            padding: '7px 14px', borderRadius: 8, fontSize: 12, cursor: 'pointer',
            background: filter === 'atrisk' ? '#f85149' : 'transparent',
            color: filter === 'atrisk' ? '#fff' : 'var(--txt2)',
            border: `1px solid ${filter === 'atrisk' ? '#f85149' : 'var(--brd)'}`,
            fontFamily: 'inherit', transition: 'all .12s',
          }}>⚠ À risque pour moi</button>
        </div>
      </div>

      {/* Cards grid */}
      {displayed.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '40px 20px', background: 'var(--sur)',
          borderRadius: 12, border: '1px solid var(--brd)' }}>
          <div style={{ fontSize: 36, marginBottom: 12 }}>✅</div>
          <p style={{ color: 'var(--grn)', fontWeight: 600, margin: '0 0 8px' }}>
            Aucune carence à risque élevé ou modéré pour votre profil !
          </p>
          <p style={{ color: 'var(--mut)', fontSize: 13, margin: '0 0 14px' }}>
            Continuez à varier votre alimentation et restez vigilant en toutes saisons.
          </p>
          <button onClick={() => setFilter('all')} style={{
            padding: '8px 18px', borderRadius: 8, background: 'var(--grn)',
            color: '#fff', border: 'none', cursor: 'pointer', fontFamily: 'inherit',
          }}>
            Voir toutes les carences
          </button>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 20 }}>
          {displayed.map(def => {
            const risk = RISK_CONFIG[def.riskLevel];
            const isX  = expanded === def.id;
            return (
              <div key={def.id} style={{
                borderRadius: 14, overflow: 'hidden',
                border: `1px solid ${def.riskLevel !== 'low' ? def.color + '35' : 'var(--brd)'}`,
                background: 'var(--sur)', display: 'flex', flexDirection: 'column',
              }}>
                {/* Colored header */}
                <div style={{ padding: '13px 15px', borderBottom: `1px solid ${def.color}18`,
                  background: `color-mix(in srgb, ${def.color} 8%, var(--sur))` }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 2 }}>
                    <span style={{ fontSize: 22 }}>{def.icon}</span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 14, fontWeight: 700, color: def.color, lineHeight: 1.2 }}>
                        {def.name}
                      </div>
                    </div>
                    <span style={{
                      fontSize: 10, padding: '3px 8px', borderRadius: 20, fontWeight: 600,
                      background: risk.bg, color: risk.color,
                      border: `1px solid ${risk.color}40`, whiteSpace: 'nowrap',
                    }}>
                      {risk.icon} {risk.label}
                    </span>
                  </div>
                </div>

                {/* Body */}
                <div style={{ padding: '12px 15px', flex: 1, display: 'flex', flexDirection: 'column', gap: 10 }}>
                  <p style={{ margin: 0, fontSize: 12, color: 'var(--txt2)', lineHeight: 1.6 }}>
                    {def.desc}
                  </p>

                  {/* Symptom chips */}
                  <div>
                    <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.07em',
                      color: 'var(--mut)', fontWeight: 700, marginBottom: 5 }}>
                      Signes
                    </div>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {def.symptoms.map(s => (
                        <span key={s} style={{ fontSize: 10.5, padding: '2px 7px', borderRadius: 20,
                          background: 'var(--sur2)', color: 'var(--txt2)', border: '1px solid var(--brd)' }}>
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Expanded: sources + tip */}
                  {isX && (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                      <div>
                        <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.07em',
                          color: 'var(--mut)', fontWeight: 700, marginBottom: 5 }}>
                          Sources alimentaires
                        </div>
                        <ul style={{ margin: 0, paddingLeft: 16, fontSize: 12, color: 'var(--txt2)', lineHeight: 1.9 }}>
                          {def.sources.map(s => <li key={s}>{s}</li>)}
                        </ul>
                      </div>
                      <div style={{ padding: '8px 12px',
                        background: `color-mix(in srgb, ${def.color} 8%, transparent)`,
                        borderRadius: 8, border: `1px solid ${def.color}20` }}>
                        <span style={{ fontSize: 12, color: def.color }}>💡 </span>
                        <span style={{ fontSize: 12, color: 'var(--txt2)', lineHeight: 1.5 }}>
                          {def.tip}
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* Footer buttons */}
                <div style={{ padding: '0 15px 13px', display: 'flex', gap: 6 }}>
                  <button
                    onClick={() => setExpanded(isX ? null : def.id)}
                    style={{ flex: 1, padding: '7px 10px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                      cursor: 'pointer', background: 'transparent', color: def.color,
                      border: `1px solid ${def.color}40`, fontFamily: 'inherit', transition: 'all .12s' }}>
                    {isX ? '− Réduire' : '+ Conseils'}
                  </button>
                  <button
                    onClick={() => navigate(def.sortKey ? `/?sort=${def.sortKey}` : '/')}
                    style={{ padding: '7px 12px', borderRadius: 8, fontSize: 11, fontWeight: 600,
                      cursor: 'pointer', background: def.color, color: '#fff',
                      border: 'none', fontFamily: 'inherit', transition: 'all .12s' }}>
                    Recettes
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <p style={{ fontSize: 11, color: 'var(--mut)', fontStyle: 'italic', marginTop: 4 }}>
        ✦ Ces informations sont basées sur votre profil déclaré dans «{' '}Profil & Journal{' '}».
        À titre informatif — consultez un professionnel de santé pour un bilan personnalisé.
      </p>
    </div>
  );
}

// ── Vue recette — AJR depuis recipe.nutrition ──────────────────────────────────

function RecipeNutritionView() {
  const [recipe,        setRecipe]        = useState(null);
  const [result,        setResult]        = useState(null);
  const [loading,       setLoading]       = useState(false);
  const [error,         setError]         = useState(null);
  const [query,         setQuery]         = useState('');
  const [searchRes,     setSearchRes]     = useState([]);
  const [searching,     setSearching]     = useState(false);
  const [fetchingFull,  setFetchingFull]  = useState(false);

  // Écoute l'event + lit la recette en attente stockée avant navigation
  useEffect(() => {
    const load = async (r) => {
      setResult(null); setError(null);
      // Si la recette vient de la liste elle peut manquer de nutrition → fetch complet
      if (!r.nutrition && r.id) {
        setFetchingFull(true);
        try { r = await recipesApi.byId(r.id); } catch { /* repli sur la recette partielle déjà affichée */ }
        finally { setFetchingFull(false); }
      }
      setRecipe(r);
    };
    if (window.__alim_pending_recipe) {
      load(window.__alim_pending_recipe);
      window.__alim_pending_recipe = null;
    }
    const handler = (e) => load(e.detail);
    window.addEventListener('alim:recipe-selected', handler);
    return () => window.removeEventListener('alim:recipe-selected', handler);
  }, []);

  // Recherche debounced
  useEffect(() => {
    if (!query.trim() || query.length < 2) { setSearchRes([]); return; }
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const data = await recipesApi.search({ query: query.trim(), limit: 7 });
        const list = Array.isArray(data) ? data : (data?.results || data?.recipes || []);
        setSearchRes(list);
      } catch { setSearchRes([]); }
      finally { setSearching(false); }
    }, 350);
    return () => clearTimeout(t);
  }, [query]);

  const selectFromSearch = async (r) => {
    setQuery(''); setSearchRes([]);
    setResult(null); setError(null);
    setFetchingFull(true);
    try {
      const full = await recipesApi.byId(r.id);
      setRecipe(full || r);
    } catch { setRecipe(r); }
    finally { setFetchingFull(false); }
  };

  // Map recipe nutrition keys → NUTRIENT_META keys
  const normalize = (n) => {
    const out = { ...n };
    if (out.proteins !== undefined && out.protein === undefined) out.protein = out.proteins;
    if (out.kcal_per_serving !== undefined && out.calories === undefined) out.calories = out.kcal_per_serving;
    return out;
  };

  const nutrRaw = recipe?.nutrition || recipe?._nutrition || {};
  const nutr    = normalize(nutrRaw);

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

  // ── Barre de recherche (toujours visible) ──
  const searchBar = (
    <div style={{ position: 'relative', marginBottom: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8,
        background: 'var(--sur2)', border: '1px solid var(--brd)',
        borderRadius: 10, padding: '10px 14px' }}>
        <span style={{ color: 'var(--mut)', fontSize: 16 }}>🔍</span>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder={recipe ? 'Changer de recette…' : 'Rechercher une recette à analyser…'}
          style={{ flex: 1, background: 'transparent', border: 'none', outline: 'none',
            color: 'var(--txt)', fontSize: 14, fontFamily: 'inherit' }}
        />
        {searching && <span style={{ color: 'var(--mut)', fontSize: 12 }}>…</span>}
        {query && <button onClick={() => { setQuery(''); setSearchRes([]); }}
          style={{ background: 'none', border: 'none', color: 'var(--mut)', cursor: 'pointer', fontSize: 16 }}>×</button>}
      </div>
      {searchRes.length > 0 && (
        <div style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 20,
          background: 'var(--sur)', border: '1px solid var(--brd)', borderRadius: 10,
          marginTop: 4, overflow: 'hidden', boxShadow: '0 8px 24px rgba(0,0,0,0.3)' }}>
          {searchRes.map(r => {
            const t = r.titles?.fr || r.title_fr || r.title || r.id;
            const kcal = r.nutrition?.kcal_per_serving || r.nutrition?.calories || r.kcal;
            return (
              <div key={r.id} onClick={() => selectFromSearch(r)}
                style={{ padding: '10px 16px', cursor: 'pointer', display: 'flex',
                  justifyContent: 'space-between', alignItems: 'center',
                  borderBottom: '1px solid var(--brd)', fontSize: 14 }}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--sur2)'}
                onMouseLeave={e => e.currentTarget.style.background = ''}>
                <span>{t}</span>
                {kcal && <span style={{ fontSize: 12, color: 'var(--mut)' }}>{Math.round(kcal)} kcal</span>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );

  if (fetchingFull) return (
    <div><div className="nutr-loading"><div className="nutr-loading-ring" /><p>Chargement…</p></div></div>
  );

  if (!recipe) {
    return (
      <div>
        {searchBar}
        <div className="nutr-empty" style={{ marginTop: 16 }}>
          <div className="nutr-empty-icon">◉</div>
          <h3>Analysez une recette</h3>
          <p>Recherchez une recette ci-dessus, ou cliquez sur <strong>◉</strong> depuis une fiche recette.</p>
        </div>
      </div>
    );
  }

  const title = recipe.titles?.fr || recipe.title_fr || recipe.title || 'Recette';
  const timeMin = recipe.total_time_min || recipe.timing?.total_min;

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
      {searchBar}

      {/* Recipe header */}
      <div className="frigo-panel" style={{ marginBottom: 20, display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 4 }}>
            RECETTE ANALYSÉE
          </div>
          <h3 style={{ margin: 0, fontSize: 18, fontWeight: 500 }}>{title}</h3>
          {timeMin && <span style={{ fontSize: 12, color: 'var(--mut)' }}>⏱ {timeMin} min</span>}
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
              {detailEntries.map(({ key, ratio, ok }) => {
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

      // Collect recipe IDs + occurrences from plan.
      // Plan format (PlanningPage): {lundi: {lunch: {skip, recipes:[{id,title_fr,...}]}, dinner:{...}}, ...}
      const occurrences = {}; // rid → count
      const titles      = {}; // rid → title_fr
      for (const dk of DAYS_KEY) {
        const dayData = plan[dk];
        if (!dayData || typeof dayData !== 'object') continue;
        for (const m of MEAL_KEYS) {
          const slot = dayData[m];
          if (!slot || slot.skip) continue;
          for (const r of (slot.recipes || [])) {
            if (!r?.id) continue;
            const rid = String(r.id);
            occurrences[rid] = (occurrences[rid] || 0) + 1;
            if (!titles[rid]) titles[rid] = r.title_fr || r.title || rid;
          }
        }
      }

      const uniqueIds = Object.keys(occurrences);
      if (uniqueIds.length === 0) { setWeekData({ empty: true }); return; }

      // Fetch full recipe data (with nutrition) for each unique ID.
      // recipesApi.byId is public — no auth needed.
      const fetched = await Promise.all(
        uniqueIds.map(id => recipesApi.byId(id).catch(() => null))
      );

      // Aggregate nutrition (weighted by occurrences for batch cooking).
      const agg   = {};
      let   count = 0;
      const recipes = [];

      for (let i = 0; i < uniqueIds.length; i++) {
        const rid    = uniqueIds[i];
        const recipe = fetched[i];
        const cnt    = occurrences[rid] || 1;

        recipes.push({ id: rid, titles: recipe?.titles, title_fr: titles[rid] });

        if (!recipe) continue;

        const n    = recipe.nutrition || recipe._nutrition || {};
        const norm = { ...n };
        if (norm.proteins !== undefined && norm.protein === undefined)           norm.protein  = norm.proteins;
        if (norm.kcal_per_serving !== undefined && norm.calories === undefined)  norm.calories = norm.kcal_per_serving;

        let hasData = false;
        for (const k of Object.keys(NUTRIENT_META)) {
          if (norm[k] != null && norm[k] > 0) {
            agg[k] = (agg[k] || 0) + norm[k] * cnt;
            hasData = true;
          }
        }
        if (hasData) count++;
      }

      setWeekData({ recipes, agg, count, total: uniqueIds.length });
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
  const [view, setView] = useState(() => {
    if (window.__alim_pending_recipe) return 'recette';   // recette en attente
    const saved = localStorage.getItem('alim_nutr_view');
    return (saved && saved !== 'apports') ? saved : 'profil';
  });

  // Auto-switch to recipe view si recette en attente ou event
  useEffect(() => {
    const handler = () => setView('recette');
    window.addEventListener('alim:recipe-selected', handler);
    return () => window.removeEventListener('alim:recipe-selected', handler);
  }, []);

  // Persist view preference
  useEffect(() => { localStorage.setItem('alim_nutr_view', view); }, [view]);

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
          { key: 'profil',   label: 'Profil & Journal', icon: '🎯' },
          { key: 'recette',  label: 'Recette',            icon: '🍽️' },
          { key: 'semaine',  label: 'Ma semaine',         icon: '▦' },
          { key: 'carences', label: 'Carences',          icon: '🔬' },
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

      {/* ── Vue Profil + Journal ── */}
      {view === 'profil'   && <ProfilJournalView />}

      {/* ── Vue Carences ── */}
      {view === 'carences' && <CarencesView onGoToProfile={() => setView('profil')} />}

      {/* ── Vue Recette ── */}
      {view === 'recette' && <RecipeNutritionView />}

      {/* ── Vue Semaine ── */}
      {view === 'semaine' && <WeekNutritionView />}

    </div>
  );
}
