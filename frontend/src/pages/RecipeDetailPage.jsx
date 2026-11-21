/**
 * RecipeDetailPage.jsx — Fiche recette complète
 *
 * Améliorations :
 *   - Visuel dynamique gradient/emoji (RecipeVisual) au lieu du placeholder
 *   - Section "Recettes similaires" (GET /recettes/:id/similaires)
 *   - Bouton "Version Vegan" (POST /recettes/:id/variante) — si non vegan
 */

import { useState, useEffect, useMemo } from 'react';
import { useRouter, navigate, Link } from '../Router';
import { recipes as recipesApi, profile as profileApi } from '../api';
import { useAuth } from '../AuthContext';
import { useProfileDiet, defaultDietFilter } from '../useProfileDiet';
import { recordViewOnce } from '../favoritesSync';
import translations from '../translations.json';
import physData from '../ingredientPhysical.json';
import { formatIngredientQty } from '../formatIngredientQty';
import RecipeCard, { RecipeVisual, getRecipeBadges, getCuisineColor, getRecipeImageUrl, computeNRFScore, computeAlimScore } from '../components/RecipeCard';
import { addToRecentlyViewed } from '../useRecentlyViewed';
import AddToPlanModal from '../components/AddToPlanModal';
import { useToast } from '../ToastContext';

// ── États des ingrédients → français ─────────────────────────────────────────
// États implicites ou relevant des instructions : ne pas afficher dans la liste
const INGREDIENT_STATE_IMPLICIT = new Set([
  'raw', 'cooked', 'sauteed', 'grilled', 'blanched', 'beaten',
  'active', 'added_at_end',
]);

// État déjà dit par le nom : pas de « Abricot sec (poids sec) »
const INGREDIENT_STATE_REDUNDANT = {
  dried: /\bsecs?\b|\bsèches?\b|séch/i,
};

const INGREDIENT_STATE_FR = {
  active:            'actif',
  added_at_end:      'ajouté en fin',
  beaten:            'battu',
  blanched:          'blanchi',
  cleaned:           'nettoyé',
  cold:              'froid',
  cooked:            'cuit',
  drained:           'égoutté',
  dried:             'poids sec',
  dry:               'sec',
  firm:              'ferme',
  fresh:             'frais',
  fresh_or_frozen:   'frais ou surgelé',
  frozen:            'surgelé',
  frozen_or_fresh:   'surgelé ou frais',
  germ_removed:      'germe retiré',
  grilled:           'grillé',
  hydrated:          'hydraté',
  lukewarm:          'tiède',
  pounded:           'pilé',
  raw:               'cru',
  rinsed:            'rincé',
  ripe:              'mûr',
  rubbed:            'frotté',
  sauteed:           'sauté',
  soaked:            'trempé',
  softened:          'ramolli',
  stale:             'rassis',
  surface_dried:     'séché en surface',
  toasted:           'torréfié',
  warm:              'chaud',
  washed:            'lavé',
  washed_and_dried:  'lavé et séché',
  washed_and_spun:   'lavé et essoré',
  washed_dried_spun: 'lavé, séché et essoré',
};

// ── Métadonnées nutriments + AJR (UE Règl. 1169/2011 / ANSES) ────────────────
const NUTR_META = {
  // — Macronutriments —
  calories:      { label: 'Calories',          unit: 'kcal', icon: '🔥', group: 'macro', ajr: 2000, color: '#f0883e' },
  protein:       { label: 'Protéines',          unit: 'g',    icon: '💪', group: 'macro', ajr: 50,   color: '#58a6ff' },
  carbs:         { label: 'Glucides',           unit: 'g',    icon: '🌾', group: 'macro', ajr: 260,  color: '#f0c27f' },
  fat:           { label: 'Lipides',            unit: 'g',    icon: '🫒', group: 'macro', ajr: 70,   color: '#a371f7' },
  fiber:         { label: 'Fibres',             unit: 'g',    icon: '🥦', group: 'macro', ajr: 25,   color: '#3fb950' },
  sugar:         { label: 'Sucres',             unit: 'g',    icon: '🍬', group: 'macro', ajr: 90,   color: '#f0883e', negative: true },
  saturated_fat: { label: 'Graisses saturées',  unit: 'g',    icon: '🧈', group: 'macro', ajr: 20,   color: '#a371f7', negative: true },
  salt:          { label: 'Sel',                unit: 'g',    icon: '🧂', group: 'macro', ajr: 6,    color: '#8b949e', negative: true },
  sodium:        { label: 'Sodium',             unit: 'mg',   icon: '🧂', group: 'macro', ajr: 2300, color: '#8b949e', negative: true },
  // — Micronutriments —
  iron:          { label: 'Fer',                unit: 'mg',   icon: '🩸', group: 'micro', ajr: 14,   color: '#f85149' },
  calcium:       { label: 'Calcium',            unit: 'mg',   icon: '🦴', group: 'micro', ajr: 800,  color: '#58a6ff' },
  vitamin_b12:   { label: 'Vitamine B12',       unit: 'µg',   icon: '🧬', group: 'micro', ajr: 2.5,  color: '#3fb950' },
  zinc:          { label: 'Zinc',               unit: 'mg',   icon: '⚡', group: 'micro', ajr: 10,   color: '#f0883e' },
  vitamin_d:     { label: 'Vitamine D',         unit: 'µg',   icon: '☀️', group: 'micro', ajr: 5,    color: '#f0c27f' },
  magnesium:     { label: 'Magnésium',          unit: 'mg',   icon: '🌿', group: 'micro', ajr: 375,  color: '#a371f7' },
  vitamin_c:     { label: 'Vitamine C',         unit: 'mg',   icon: '🍊', group: 'micro', ajr: 80,   color: '#f0883e' },
  potassium:     { label: 'Potassium',          unit: 'mg',   icon: '🍌', group: 'micro', ajr: 2000, color: '#3fb950' },
  phosphorus:    { label: 'Phosphore',          unit: 'mg',   icon: '⚗️', group: 'micro', ajr: 700,  color: '#58a6ff' },
  vitamin_a:     { label: 'Vitamine A',         unit: 'µg',   icon: '🥕', group: 'micro', ajr: 800,  color: '#f0883e' },
  vitamin_e:     { label: 'Vitamine E',         unit: 'mg',   icon: '🌻', group: 'micro', ajr: 12,   color: '#f0c27f' },
  vitamin_k:     { label: 'Vitamine K',         unit: 'µg',   icon: '🥬', group: 'micro', ajr: 75,   color: '#3fb950' },
  folate:        { label: 'Folates (B9)',        unit: 'µg',   icon: '🌱', group: 'micro', ajr: 200,  color: '#3fb950' },
  omega3:        { label: 'Oméga-3',            unit: 'g',    icon: '🫐', group: 'micro', ajr: 2,    color: '#58a6ff' },
};

// Alias protein/proteins — certaines recettes utilisent l'un ou l'autre
function normalizeNutrition(raw) {
  if (!raw || typeof raw !== 'object') return {};
  const n = { ...raw };
  if (n.proteins != null && n.protein == null) n.protein = n.proteins;
  return n;
}

// ── Panneau nutrition complet ─────────────────────────────────────────────────
function RecipeNutritionPanel({ nutrition: rawNutrition }) {
  const nutrition = normalizeNutrition(rawNutrition);

  const macros = Object.entries(NUTR_META).filter(([, m]) => m.group === 'macro');
  const micros = Object.entries(NUTR_META).filter(([, m]) => m.group === 'micro');

  // Micronutriments clés manquants (importants en végétarien)
  const KEY_MICROS = ['iron','calcium','vitamin_b12','zinc','vitamin_d','magnesium','vitamin_c'];
  const missingKeyMicros = KEY_MICROS
    .filter(k => nutrition[k] == null)
    .map(k => NUTR_META[k].label);

  // Couleur adaptée à un repas (~30% AJR max attendu)
  // Éléments positifs (protéines, fibres, vitamines…) : rouge<5% → orange<15% → vert<30% → jaune fluo ≥30%
  // Éléments négatifs (sel, sucres, graisses sat…)    : vert<5% → orange<15% → rouge<30% → rouge fluo ≥30%
  const getMealColor = (pct, negative) => {
    if (negative) {
      if (pct >= 30) return '#ff4444';  // excès — rouge fluo
      if (pct >= 15) return '#f85149';  // élevé  — rouge
      if (pct >= 5)  return '#e3b341';  // moyen  — orange
      return '#3fb950';                 // faible  — vert
    } else {
      if (pct >= 30) return '#d4f542';  // excellent — jaune fluo
      if (pct >= 15) return '#3fb950';  // bon       — vert
      if (pct >= 5)  return '#e3b341';  // moyen     — orange
      return '#f85149';                 // faible    — rouge
    }
  };

  const renderBar = ([key, meta]) => {
    const val = nutrition[key];
    if (val == null) return null;
    const rawPct   = (val / meta.ajr) * 100;
    const pct      = Math.min(100, rawPct);
    const color    = getMealColor(rawPct, meta.negative);
    const dispVal  = val < 10 ? Number(val.toFixed(1)) : Math.round(val);
    const ajrPct   = Math.round(rawPct);

    return (
      <div key={key} className="rn-bar-row">
        <div className="rn-bar-header">
          <span className="rn-bar-icon">{meta.icon}</span>
          <span className="rn-bar-name">{meta.label}</span>
          <span className="rn-bar-val" style={{ color }}>
            {dispVal}<span className="rn-bar-unit"> {meta.unit}</span>
          </span>
          <span className="rn-bar-pct" style={{ color }}>
            {ajrPct}%
          </span>
        </div>
        <div className="rn-bar-track">
          <div className="rn-bar-fill" style={{
            width: `${pct}%`,
            background: `linear-gradient(90deg,${color},${color}bb)`,
            boxShadow: `0 0 6px ${color}50`,
          }} />
          <div className="rn-bar-marker" />
        </div>
      </div>
    );
  };

  const macroItems = macros.map(renderBar).filter(Boolean);
  const microItems = micros.map(renderBar).filter(Boolean);
  if (macroItems.length === 0 && microItems.length === 0) return null;

  // Chips résumé (4 valeurs clés)
  const summaryKeys = ['calories','protein','carbs','fat'];

  return (
    <div className="rn-panel">
      <div className="rn-panel-header">
        <h3 className="rn-panel-title">Valeurs nutritionnelles</h3>
        <span className="rn-panel-sub">par portion · % de l'Apport Journalier de Référence (AJR)</span>
      </div>

      {/* Résumé 4 macros clés */}
      <div className="rn-summary">
        {summaryKeys.map(k => {
          const v = nutrition[k]; const m = NUTR_META[k];
          if (v == null || !m) return null;
          const pct = Math.min(100, Math.round((v / m.ajr) * 100));
          return (
            <div key={k} className="rn-chip">
              <span className="rn-chip-icon">{m.icon}</span>
              <span className="rn-chip-val" style={{ color: m.color }}>
                {k === 'calories' ? Math.round(v) : v < 10 ? v.toFixed(1) : Math.round(v)}
              </span>
              <span className="rn-chip-unit">{m.unit}</span>
              <span className="rn-chip-label">{m.label}</span>
              <span className="rn-chip-pct">{pct}% AJR</span>
            </div>
          );
        })}
      </div>

      <div className="rn-sections">
        {macroItems.length > 0 && (
          <div className="rn-section">
            <div className="rn-section-title">Macronutriments</div>
            <div className="rn-bars-grid">{macroItems}</div>
          </div>
        )}
        {microItems.length > 0 && (
          <div className="rn-section">
            <div className="rn-section-title">Micronutriments</div>
            <div className="rn-bars-grid">{microItems}</div>
          </div>
        )}
      </div>

      {missingKeyMicros.length > 0 && (
        <p className="rn-unknown-note">
          ℹ️ Valeurs non disponibles pour cette recette : {missingKeyMicros.join(', ')}.
        </p>
      )}
    </div>
  );
}

// ── Matching frigo côté client (miroir de _ingredient_matches backend) ─────────
// ── Saison et empreinte carbone (enrich_one : seasonal_tag, carbon_data) ─────────
const MONTHS_FR = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin', 'juillet',
                   'août', 'septembre', 'octobre', 'novembre', 'décembre'];

const SEASON_LABEL = {
  de_saison:      { text: 'De saison',            cls: 'sustain-pill--good' },
  presque_saison: { text: 'Presque de saison',    cls: 'sustain-pill--mid' },
  hors_saison:    { text: 'Hors saison',          cls: 'sustain-pill--bad' },
  'année_entière': { text: "Ingrédients de toute l'année", cls: '' },
};

function carbonLevel(label = '') {
  if (label.includes('Faible')) return { text: 'faible', cls: 'sustain-pill--good' };
  if (label.includes('Moyen'))  return { text: 'moyenne', cls: 'sustain-pill--mid' };
  if (label.includes('Élevé'))  return { text: 'élevée', cls: 'sustain-pill--bad' };
  return { text: '', cls: '' };
}

export function SeasonCarbon({ recipe, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen);
  const carbon = recipe.carbon_data;
  const month  = recipe.season_month || carbon?.month;
  const season = SEASON_LABEL[recipe.seasonal_tag];
  if (!season && !(carbon?.per_portion_kg > 0)) return null;

  const monthName = month ? MONTHS_FR[month - 1] : null;
  const level = carbonLevel(carbon?.label);
  const kg = carbon?.per_portion_kg;
  const nameOf = (iid) => recipe.ingredients_meta?.[iid]?.name_fr || iid.replace(/_/g, ' ');
  const top = (carbon?.ingredients_co2 || []).filter(x => x.kg_co2 > 0).slice(0, 3);
  const servings = recipe.servings || 4;

  return (
    <div className="detail-sustain">
      {season && (
        <span className={`sustain-pill ${season.cls}`}
              title={recipe.seasonal_tag === 'année_entière' ? undefined
                : `${Math.round((recipe.seasonal_ratio || 0) * 100)} % des ingrédients saisonniers sont de saison`}>
          🌱 {season.text}{monthName && recipe.seasonal_tag !== 'année_entière' ? ` en ${monthName}` : ''}
        </span>
      )}
      {kg > 0 && (
        <button type="button" className={`sustain-pill sustain-pill--btn ${level.cls}`}
                onClick={() => setOpen(o => !o)} aria-expanded={open}>
          🌍 {kg.toFixed(2).replace('.', ',')} kg CO₂e / pers.
          {level.text && <> · empreinte {level.text}</>}
          <span className="sustain-caret" aria-hidden="true">{open ? '▴' : '▾'}</span>
        </button>
      )}
      {open && kg > 0 && (
        <div className="sustain-detail">
          {top.length > 0 && (
            <p>
              Ce qui pèse le plus :{' '}
              {top.map((x, i) => (
                <span key={x.ingredient}>
                  {i > 0 && ', '}
                  {nameOf(x.ingredient)} ({(x.kg_co2 / servings).toFixed(2).replace('.', ',')} kg)
                </span>
              ))}.
            </p>
          )}
          <p className="sustain-source">
            Changement climatique, données AGRIBALYSE 3.2 (ADEME)
            {monthName ? ` ; tomates et fraises comptées selon la saison en ${monthName}` : ''}.
            Repères : faible sous 0,5 kg, élevée au-delà de 1,5 kg par portion.
          </p>
        </div>
      )}
    </div>
  );
}

function ingredientMatches(fridgeId, recipeId) {
  if (!fridgeId || !recipeId) return false;
  const fid = fridgeId.toLowerCase();
  const rid = recipeId.toLowerCase();
  if (fid === rid) return true;
  if (rid.startsWith(fid + '/') || rid.startsWith(fid + '_')) return true;
  if (rid.endsWith('_' + fid)) return true;
  const parts = rid.split('/');
  if (parts.length > 1) {
    const last = parts[parts.length - 1];
    if (last === fid || last.startsWith(fid + '_')) return true;
  }
  return false;
}

export default function RecipeDetailPage() {
  const { params, search, setSearch } = useRouter();
  const loggedIn = !!useAuth()?.user;
  const toast = useToast();

  const [recipe,   setRecipe]   = useState(null);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);
  const [servings, setServings] = useState(4);

  // Modal "Ajouter au planning"
  const [showPlanModal, setShowPlanModal] = useState(false);

  // Similaires
  const [similar,        setSimilar]        = useState([]);
  const [similarLoading, setSimilarLoading] = useState(false);

  // Variante vegan
  const [variant,        setVariant]        = useState(null);
  const [variantLoading, setVariantLoading] = useState(false);
  const [variantError,   setVariantError]   = useState(null);
  const [showVariant,    setShowVariant]    = useState(false);

  // ── Couverture frigo (depuis localStorage, calculée côté client) ────────────
  const fridgeCoverage = useMemo(() => {
    if (!recipe) return null;
    try {
      const raw = localStorage.getItem('alim_frigo_selected');
      if (!raw) return null;
      const fridgeIds = JSON.parse(raw).map(([id]) => id);
      if (fridgeIds.length === 0) return null;

      const ings = recipe.composition || recipe.ingredients || [];
      if (ings.length === 0) return null;

      const have    = [];
      const missing = [];
      for (const ing of ings) {
        const iid = (ing.ingredient_id || ing.ingredient || '').toLowerCase();
        if (!iid) continue;
        if (fridgeIds.some(fid => ingredientMatches(fid, iid))) {
          have.push(iid);
        } else {
          missing.push(iid);
        }
      }
      const total = have.length + missing.length;
      if (total === 0) return null;
      return {
        haveSet:  new Set(have),
        missing,
        pct: Math.round((have.length / total) * 100),
      };
    } catch { return null; }
  }, [recipe]);

  // ── Chargement recette principale ──────────────────────────────────────────
  useEffect(() => {
    if (!params.id) return;
    setLoading(true);
    setError(null);
    setVariant(null);
    setShowVariant(false);
    setSimilar([]);

    recipesApi.byId(params.id)
      .then((data) => {
        setRecipe(data);
        setServings(data.servings || 4);
        addToRecentlyViewed(data);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.id]);

  // ── Vue enregistrée côté compte (personnalisation), une fois par session ───
  useEffect(() => {
    if (loggedIn && recipe?.id) recordViewOnce(profileApi.interaction, recipe.id);
  }, [loggedIn, recipe?.id]);

  // ── Chargement similaires (une fois la recette chargée) ────────────────────
  // Version vegan affichée, ou profil vegan : des suggestions vegan (sinon quiche au
  // chèvre, gougères…), comme les filtres de l'accueil, du planning et du frigo
  const profileDiet = defaultDietFilter(useProfileDiet());
  const similarDiet = (showVariant && variant?.recipe) || profileDiet === 'vegan' ? 'vegan' : '';
  useEffect(() => {
    if (!recipe) return;
    setSimilarLoading(true);
    recipesApi.similar(recipe.id, similarDiet)
      .then((data) => setSimilar(data?.similar || []))
      .catch(() => setSimilar([]))
      .finally(() => setSimilarLoading(false));
  }, [recipe, similarDiet]);

  // ── Variante vegan ─────────────────────────────────────────────────────────
  // L'adresse suit la version affichée (?version=vegan) : un rechargement ou un
  // lien partagé rouvre la même version, « Voir l'originale » la retire.
  const setVersionParam = (vegan) => {
    const sp = new URLSearchParams(search);
    if (vegan) sp.set('version', 'vegan'); else sp.delete('version');
    if (sp.toString() !== search.toString()) setSearch(sp);
  };
  const generateVariant = async () => {
    setVariantLoading(true);
    setVariantError(null);
    try {
      const data = await recipesApi.vegan(recipe.id);
      // pas de version vegan fiable (plat à base d'œuf, blancs en neige…) : on ne l'affiche pas
      if (data?.source === 'unavailable') {
        setVariantError(`Pas de version vegan fiable pour ce plat : ${data.reason}.`);
        setVersionParam(false);
        return;
      }
      setVariant(data);
      setShowVariant(true);
      setVersionParam(true);
      toast(data?.source === 'partial'
        ? 'Variante générée : certains ingrédients n\'ont pas de substitut vegan'
        : 'Variante vegan générée !', 'success');
    } catch (err) {
      setVariantError(err.message || 'Connexion requise pour générer une variante.');
      toast(err.message || 'Erreur lors de la génération', 'error');
    } finally {
      setVariantLoading(false);
    }
  };

  // #/recette/:id?version=vegan (carte du planning ajoutée en version vegan) : la
  // fiche s'ouvre directement sur la version vegan (route réservée aux connectés)
  const wantVegan = search?.get('version') === 'vegan';
  useEffect(() => {
    if (wantVegan && loggedIn && recipe && recipe.id === params.id
        && !recipe.diet_flags?.vegan && recipe.vegan_variant?.available !== false
        && !variant && !variantLoading) generateVariant();
  }, [wantVegan, loggedIn, recipe?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── États de chargement / erreur ───────────────────────────────────────────
  if (loading) return (
    <div className="detail-loading">
      <div className="skeleton skeleton-img" style={{ height: 280, borderRadius: 16, marginBottom: 24 }} />
      <div className="skeleton skeleton-line" style={{ width: '55%', height: 36, marginBottom: 16 }} />
      <div className="skeleton skeleton-line" style={{ width: '80%', marginBottom: 8 }} />
      <div className="skeleton skeleton-line" style={{ width: '60%' }} />
    </div>
  );

  if (error) return (
    <div className="state-msg state-msg--error">
      Recette introuvable.<br />
      <button className="back-button" onClick={() => navigate('/')}>← Retour</button>
    </div>
  );

  if (!recipe) return null;

  // ── Calculs ────────────────────────────────────────────────────────────────
  const ratio    = servings / (recipe.servings || 4);
  const isVegan  = recipe.diet_flags?.vegan;
  const rawTime      = recipe.timing || {};

  // Scaling temporel non-linéaire selon le nombre de convives :
  // - prep  ∝ √ratio  (on optimise les gestes, on travaille en parallèle)
  // - cuisson ∝ 1 + 0.1×(ratio−1)  (le four/feu ne change presque pas)
  const scaleTime = (base, mode) => {
    if (!base || ratio === 1) return base;
    const scaled = mode === 'prep'
      ? base * Math.sqrt(ratio)
      : base * (1 + 0.1 * (ratio - 1));
    return Math.round(scaled);
  };
  const timeInfo = {
    ...rawTime,
    prep_active_min : scaleTime(rawTime.prep_active_min, 'prep'),
    cook_min        : scaleTime(rawTime.cook_min,        'cook'),
    total_expected  : scaleTime(rawTime.total_expected,  'prep'),
    get total_min() {
      const p = this.prep_active_min || 0;
      const c = this.cook_min        || 0;
      return (p || c) ? p + c : rawTime.total_min;
    },
  };

  const ingredients  = recipe.composition || recipe.ingredients || [];
  // Recette à afficher (principale ou variante)
  const displayed = showVariant && variant?.recipe ? variant.recipe : recipe;
  // Badges de la recette affichée : la variante vegan au tofu ne doit pas garder
  // le « Sans Soja » de l'original (allergènes recalculés par le serveur)
  const badges       = getRecipeBadges(displayed);

  return (
    <div className="recipe-detail-container">
      <button className="back-button" onClick={() => navigate('/')}>
        ← Retour aux résultats
      </button>

      {/* ── Header ── */}
      <div className="detail-header">
        {/* Visuel dynamique — image locale si disponible, sinon gradient */}
        <div className="detail-hero" style={{ padding: 0, overflow: 'hidden', position: 'relative' }}>
          {(() => {
            const localImg = getRecipeImageUrl(displayed);
            return localImg ? (
              <img
                src={localImg}
                alt={displayed.titles?.fr || 'Recette'}
                style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'block';
                }}
              />
            ) : null;
          })()}
          {/* width: .detail-hero est un flex centré et le visuel n'a que des
              enfants absolus : sans largeur, il s'écrasait à 0 px (cadre vide) */}
          <div style={{ display: getRecipeImageUrl(displayed) ? 'none' : 'block', height: '100%', width: '100%' }}>
            <RecipeVisual recipe={displayed} size="large" />
          </div>

        </div>

        <div className="detail-header-content">
          {/* Toggle variante */}
          {showVariant && (
            <div className="variant-banner">
              <span>{variant?.source === 'partial' ? '🌿 Version vegan incomplète' : '🌿 Version vegan générée'}</span>
              <button className="variant-toggle" onClick={() => { setShowVariant(false); setVersionParam(false); }}>
                Voir l'originale
              </button>
            </div>
          )}

          {/* Titre + badge NRF8v à droite */}
          {(() => {
            const nrf = computeNRFScore(displayed);
            // Score rescalé ×2 → meilleurs plats 75-95/100
            const bg  = nrf >= 70 ? 'rgba(21,95,50,0.92)' : nrf >= 45 ? 'rgba(29,78,154,0.90)' : 'rgba(55,65,81,0.88)';
            return (
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 10 }}>
                <h1 className="detail-title" style={{ margin: 0, flex: 1 }}>
                  {displayed.titles?.fr || displayed.title_fr || 'Recette'}
                </h1>
                {nrf !== null && (
                  <div style={{
                    flexShrink: 0,
                    width: 46, padding: '7px 4px 6px', borderRadius: 10,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                    fontFamily: 'inherit', color: '#fff', gap: 2,
                    border: '1px solid rgba(255,255,255,0.18)',
                    boxShadow: '0 3px 14px rgba(0,0,0,0.28)',
                    background: bg,
                  }}>
                    <span style={{ fontSize: 13, lineHeight: 1 }}>🌿</span>
                    <span style={{ fontSize: 18, fontWeight: 800, letterSpacing: '-0.5px', lineHeight: 1.1 }}>{nrf}</span>
                    <span style={{ fontSize: 8, fontWeight: 700, opacity: 0.72, letterSpacing: '0.08em', textTransform: 'uppercase', lineHeight: 1 }}>Nutri</span>
                    <div style={{ width: 30, height: 3, background: 'rgba(255,255,255,0.22)', borderRadius: 2, overflow: 'hidden', marginTop: 4 }}>
                      <div style={{ height: '100%', width: `${nrf}%`, background: 'rgba(255,255,255,0.80)', borderRadius: 2 }} />
                    </div>
                  </div>
                )}
              </div>
            );
          })()}

          {/* Recette proposée par un membre */}
          {recipe.community?.author_name && (
            <p className="detail-byline">
              <span aria-hidden="true">✍</span> Recette proposée par <strong>{recipe.community.author_name}</strong>
              {recipe.community.published_at && <> · {new Date(recipe.community.published_at).toLocaleDateString('fr-FR', { month: 'long', year: 'numeric' })}</>}
              {' · '}<Link to="/proposer">Proposer la vôtre</Link>
            </p>
          )}

          {/* Origine cuisine */}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 10 }}>
            {recipe.origin?.cuisine && (() => {
              const color = getCuisineColor(recipe);
              return (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  fontSize: 12, fontWeight: 500, color,
                  flexShrink: 0, marginTop: 8,
                }}>
                  <span style={{
                    width: 7, height: 7, borderRadius: '50%', flexShrink: 0,
                    background: color, display: 'inline-block',
                  }} />
                  {recipe.origin.cuisine.replace(/_/g, ' ')}
                </div>
              );
            })()}
          </div>

          {displayed.description && (
            <p className="detail-description">{displayed.description}</p>
          )}

          <div className="badges detail-badges">
            {badges.map(b => (
              <span key={b.id} className={`badge ${b.cls || ''}`} title={b.label}>
                {b.symbol} {b.label}
              </span>
            ))}
            {(() => {
              const alim = computeAlimScore(displayed);
              return alim !== null
                ? <span className="badge score" title="Score ALIM — qualité végé-nutritionnelle">⭐ {alim}/100</span>
                : null;
            })()}
          </div>

          {/* Stats durées + difficulté sur la même ligne */}
          <div className="detail-stats" style={{ marginTop: 20 }}>
            {[
              { label: 'Total',       value: timeInfo.total_min || timeInfo.total_expected },
              { label: 'Cuisson',     value: timeInfo.cook_min },
              { label: 'Préparation', value: timeInfo.prep_active_min },
            ].map(({ label, value }) => (
              <div key={label} className="stat-box">
                <span className="stat-label">{label}</span>
                <span className="stat-value">{value ? `${value} min` : '--'}</span>
              </div>
            ))}

            {displayed.price_data?.per_portion_eur > 0 && (
              <div className="stat-box" title={displayed.price_data.label}>
                <span className="stat-label">Coût estimé</span>
                <span className="stat-value">
                  {displayed.price_data.complete === false ? '≥ ' : '~'}
                  {displayed.price_data.per_portion_eur.toFixed(2).replace('.', ',')} € / pers.
                </span>
              </div>
            )}

            {recipe.difficulty && (() => {
              const raw  = recipe.difficulty;
              const lvl  = typeof raw === 'number' ? raw
                         : raw === 'easy'   || raw === 'facile'        ? 1
                         : raw === 'medium' || raw === 'intermédiaire' ? 2
                         : raw === 'hard'   || raw === 'difficile'     ? 3 : 2;
              const dlabel = lvl === 1 ? 'Facile' : lvl === 2 ? 'Intermédiaire' : 'Difficile';
              const color  = lvl === 1 ? '#1D9E75' : lvl === 2 ? '#E07B39' : '#C0392B';
              return (
                <div className="stat-box" style={{ marginLeft: 'auto' }}>
                  <span className="stat-label">Difficulté</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 7, paddingTop: 2 }}>
                    <div style={{ display: 'flex', gap: 3 }}>
                      {[1, 2, 3].map(i => (
                        <span key={i} style={{
                          width: 8, height: 8, borderRadius: '50%',
                          background: i <= lvl ? color : 'var(--mut, #888)',
                          opacity: i <= lvl ? 1 : 0.2,
                          display: 'inline-block',
                        }} />
                      ))}
                    </div>
                    <span style={{ fontSize: 14, fontWeight: 600, color }}>{dlabel}</span>
                  </div>
                </div>
              );
            })()}
          </div>
          {displayed.price_data?.unknown_ingredients?.length > 0 && (
            <p className="price-unknown-note" role="note">
              ⚠ Prix inconnu pour {displayed.price_data.unknown_ingredients.map(u => u.name_fr).join(', ')} :
              le coût estimé est incomplet.
            </p>
          )}
          {displayed.price_data?.estimated_ingredients?.length > 0 && (
            <p className="price-estimated-note" role="note">
              Prix estimé, sans relevé en magasin, pour{' '}
              {displayed.price_data.estimated_ingredients.map(u => u.name_fr).join(', ')}.
            </p>
          )}

          <SeasonCarbon recipe={displayed} />


          {/* Boutons d'action */}
          <div style={{ display:'flex', gap:10, flexWrap:'wrap', marginTop: 16 }}>
            {!isVegan && !showVariant && recipe.vegan_variant?.available !== false && (
              <button
                className="variant-btn"
                onClick={generateVariant}
                disabled={variantLoading}
              >
                {variantLoading ? (
                  <><span className="nutr-btn-spinner" style={{ width: 14, height: 14 }} /> Génération…</>
                ) : (
                  <>🌿 Version Vegan</>
                )}
              </button>
            )}
            <button className="variant-btn atp-trigger-btn" onClick={()=>setShowPlanModal(true)}>
              📅 Ajouter au planning
            </button>
            <button className="variant-btn" onClick={() => {
              // version affichée : la nutrition de la variante vegan, titre précisé
              const sent = showVariant && variant?.recipe
                ? { ...displayed, titles: { ...displayed.titles, fr: `${displayed.titles?.fr || ''} (version vegan)` } }
                : recipe;
              window.__alim_pending_recipe = sent;
              window.dispatchEvent(new CustomEvent('alim:recipe-selected', { detail: sent }));
              navigate('/nutrition');
            }}>
              ◉ Voir l'AJR
            </button>
          </div>
          {variantError && !isVegan && !showVariant && (
            <p style={{ color: 'var(--amber)', fontSize: 12, marginTop: 8 }}>
              ⚠️ {variantError}
            </p>
          )}
          {!isVegan && !variantError && recipe.vegan_variant?.available === false && (
            <p className="variant-unavailable" style={{ color: 'var(--txt2)', fontSize: 12, marginTop: 8 }}>
              🌿 Pas de version vegan pour ce plat : {recipe.vegan_variant.reason}.
            </p>
          )}
        </div>
      </div>

      {/* ── Grille ingrédients / instructions ── */}
      <div className="detail-grid">
        {/* Ingrédients */}
        <div className="detail-ingredients">
          <div className="servings-controller">
            <h3>Ingrédients</h3>
            <div className="servings-adjuster">
              <button onClick={() => setServings(Math.max(1, servings - 1))}>−</button>
              <span>{servings} pers.</span>
              <button onClick={() => setServings(servings + 1)}>+</button>
            </div>
          </div>

          {/* Panel frigo — affiché seulement si le frigo contient des ingrédients */}
          {fridgeCoverage && (
            <div className="frigo-detail-panel">
              <div className="frigo-detail-header">
                <span className="frigo-detail-icon">◈</span>
                <span className="frigo-detail-title">Mon frigo</span>
                <div className="frigo-detail-track">
                  <div className="frigo-detail-bar" style={{ width: `${fridgeCoverage.pct}%` }} />
                </div>
                <span className={`frigo-detail-pct ${fridgeCoverage.pct === 100 ? 'frigo-detail-pct--full' : fridgeCoverage.pct >= 60 ? 'frigo-detail-pct--ok' : 'frigo-detail-pct--low'}`}>
                  {fridgeCoverage.pct}%
                </span>
              </div>
              {fridgeCoverage.missing.length > 0 && (
                <div className="frigo-detail-missing">
                  <span className="frigo-detail-missing-label">
                    À acheter ({fridgeCoverage.missing.length}) :
                  </span>
                  <span className="frigo-detail-missing-list">
                    {fridgeCoverage.missing.map(iid => {
                      const iidUnd   = iid.replace(/\//g, '_');
                      const iidFirst = iid.split('/')[0];
                      const n = translations[iid] || translations[iidUnd] || translations[iidFirst]
                             || displayed.ingredients_meta?.[iid]?.name_fr
                             || iid.replace(/[_/]/g, ' ');
                      return n;
                    }).join(', ')}
                  </span>
                </div>
              )}
              {fridgeCoverage.pct === 100 && (
                <p className="frigo-detail-ok">Vous avez tout ce qu'il faut !</p>
              )}
            </div>
          )}

          <ul className="ingredient-list">
            {(displayed.composition || displayed.ingredients || ingredients).map((ing, idx) => {
              // Identifiant de l'ingrédient (clé pour ingredients_meta)
              const iid     = ing.ingredient_id || ing.ingredient || '';
              // Normalisation pour les IDs avec slash (mushroom/button → mushroom_button → mushroom)
              const iidUnd  = iid.replace(/\//g, '_');
              const iidFirst = iid.split('/')[0];
              // 1. name_fr depuis ingredients_meta (enrich_one) — source la plus fiable
              // 2. translations.json avec variantes de clé
              // 3. Fallback : identifiant brut nettoyé
              const rawName = ing.name || iid || '';
              const nameStr = typeof rawName === 'string' ? rawName : '';
              // Priorité : translations (spécifique + capitalisé) → ingredients_meta (backend dict) → brut
              const subRecipeId = displayed.ingredients_meta?.[iid]?.recipe_id;
              const metaName = displayed.ingredients_meta?.[iid]?.name_fr
                            || displayed.ingredients_meta?.[iidUnd]?.name_fr
                            || displayed.ingredients_meta?.[iidFirst]?.name_fr;
              const rawResolved = translations[iid]
                || translations[iidUnd]
                || translations[iidFirst]
                || translations[nameStr];
              // Majuscule initiale seulement : text-transform: capitalize donnait
              // « Huile De Noix De Coco ».
              const name0 = (rawResolved || metaName || nameStr).replace(/_/g, ' ');
              const name = name0.charAt(0).toUpperCase() + name0.slice(1);
              const st = ing.meta?.state;
              const stateFr = st && !INGREDIENT_STATE_IMPLICIT.has(st)
                && !INGREDIENT_STATE_REDUNDANT[st]?.test(name)
                ? (INGREDIENT_STATE_FR[st] ?? st) : null;
              let qtyStr   = '';
              let equivStr = '';
              if (ing.quantity) {
                const q  = ing.quantity * ratio;
                qtyStr   = `${q < 10 && q % 1 !== 0 ? q.toFixed(1) : Math.round(q)} ${ing.unit || ''}`.trim();
                equivStr = formatIngredientQty(iid, q, ing.unit || '', physData);
              }

              // Statut frigo pour cet ingrédient
              const iidLow  = iid.toLowerCase();
              const inFrigo = fridgeCoverage
                ? fridgeCoverage.haveSet.has(iidLow)
                : null;

              return (
                <li key={idx} className={
                  inFrigo === true  ? 'ing-in-frigo' :
                  inFrigo === false ? 'ing-missing-frigo' : ''
                }>
                  {inFrigo !== null && (
                    <span className="ing-frigo-dot" aria-hidden="true">
                      {inFrigo ? '✓' : '✗'}
                    </span>
                  )}
                  <span className="ing-qty">
                    <span className="ing-qty-val">{qtyStr}</span>
                    {equivStr && <span className="ing-equiv">{equivStr}</span>}
                  </span>
                  <span className="ing-name">
                    {subRecipeId ? (
                      // Sous-recette : lien vers sa fiche (béchamel, pâte de curry…)
                      <button type="button" className="ing-subrecipe-link"
                        onClick={() => navigate(`/recette/${subRecipeId}`)}
                        title="Voir la recette de cette préparation">
                        {name} ↗
                      </button>
                    ) : name}
                    {stateFr && <span className="ing-meta"> ({stateFr})</span>}
                  </span>
                </li>
              );
            })}
          </ul>

          {/* Substitutions vegan si variante */}
          {/* Le backend renvoie substitutions[{original, substitute, *_name}] :
              lire subs[{from, to}] n'affichait jamais rien. */}
          {showVariant && variant?.substitutions?.length > 0 && (
            <div className="variant-subs">
              <h4>🔄 Substitutions appliquées</h4>
              {variant.substitutions.map((s, i) => (
                <div key={i} className="variant-sub-row">
                  <span className="variant-sub-from">{s.original_name || (s.original || '').replace(/_/g, ' ')}</span>
                  <span className="variant-sub-arrow">→</span>
                  <span className="variant-sub-to">{s.substitute_name || (s.substitute || '').replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          )}
          {showVariant && variant?.unresolved?.length > 0 && (
            <div className="variant-subs">
              <h4>⚠️ Sans substitut vegan</h4>
              {variant.unresolved.map((u, i) => (
                <div key={i} className="variant-sub-row">
                  <span className="variant-sub-from">{u.name || (u.id || '').replace(/_/g, ' ')}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="detail-instructions">
          <h3>Préparation</h3>
          {showVariant && variant?.substitutions?.length > 0 && (
            <p className="variant-steps-note" role="note">
              {/* Les étapes sont réécrites par le serveur ; les œufs entiers cuits ou cassés
                  restent tels quels dans le texte, d'où le rappel */}
              {variant.recipe?._steps_rewritten > 0
                ? 'Étapes adaptées à la version vegan. Remplacements : '
                : "Étapes de la recette d'origine. Remplacez : "}
              {variant.substitutions.map((s, i) => (
                <span key={i}>
                  {i > 0 && (i === variant.substitutions.length - 1 ? ' et ' : ', ')}
                  {(s.original_name || '').toLowerCase()} → {(s.substitute_name || '').toLowerCase()}
                </span>
              ))}.
            </p>
          )}
          {(displayed.instructions || recipe.instructions)?.length > 0 ? (
            <ol className="instruction-list">
              {(displayed.instructions || recipe.instructions).map((step, idx) => {
                // Retire les préfixes redondants : "Étape 1 :", "Step 2.", "étape 3 -", etc.
                const cleaned = (step || '')
                  .replace(/^(é|e)tape\s*\d+\s*[-:.]\s*/i, '')
                  .replace(/^step\s*\d+\s*[-:.]\s*/i, '')
                  .trim();
                return <li key={idx}>{cleaned || step}</li>;
              })}
            </ol>
          ) : (
            <p className="no-instructions">
              Les étapes de préparation ne sont pas encore disponibles pour cette recette.
            </p>
          )}

        </div>
      </div>

      {/* ── Nutrition complète (pleine largeur) ── */}
      {displayed.nutrition && <RecipeNutritionPanel nutrition={displayed.nutrition} />}

      {/* ── Modal Ajouter au planning ── */}
      {showPlanModal && recipe && (
        <AddToPlanModal recipe={recipe} variant={showVariant && variant?.recipe ? 'vegan' : undefined}
          onClose={()=>setShowPlanModal(false)} />
      )}

      {/* ── Recettes similaires ── */}
      {(similarLoading || similar.length > 0) && (
        <div className="similar-section">
          <h3 className="similar-title">Recettes similaires</h3>
          {similarLoading ? (
            <div className="skeleton-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))' }}>
              {[1, 2, 3].map(i => (
                <div key={i} className="skeleton-card">
                  <div className="skeleton skeleton-img" />
                  <div className="skeleton skeleton-line" style={{ width: '70%' }} />
                  <div className="skeleton skeleton-line" style={{ width: '45%' }} />
                </div>
              ))}
            </div>
          ) : (
            <div className="similar-grid">
              {similar.map((r, i) => (
                <div key={r.id || i} className="similar-card-wrap">
                  <RecipeCard recipe={r} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
