/**
 * ProfilePage.jsx — Profil utilisateur enrichi ALIM v6
 *
 * Sections :
 *  - En-tête avec score de profil végé
 *  - Préférences alimentaires + objectif nutritionnel
 *  - Mon cycle (phase actuelle + besoins)
 *  - Mon signe astrologique
 *  - Mes Favoris (groupés par type de plat) — accessible uniquement ici
 *  - Récemment consultées
 */

import { useState } from 'react';
import { profile as profileApi } from '../api';
import { useAuth } from '../AuthContext';
import { useFavorites } from '../FavoritesContext';
import { useRecentlyViewed } from '../useRecentlyViewed';
import { useToast } from '../ToastContext';
import RecipeCard from '../components/RecipeCard';
import { navigate } from '../Router';
import { DISH_OPTIONS } from '../constants';

// ── Données cycle & astro (intégrées depuis maraicher-wellness) ───────────────

const CYCLE_PHASES = [
  {
    id: 'menstrual', label: 'Menstruelle', range: 'J1 – J5', moon: '🌑',
    color: '#C0392B', colorDim: 'rgba(192,57,43,0.12)',
    needs: [
      { icon: '🩸', label: 'Fer', detail: 'Lentilles, épinards, betterave' },
      { icon: '🧲', label: 'Magnésium', detail: 'Anti-crampes — chocolat noir, noix' },
      { icon: '🐟', label: 'Oméga-3', detail: 'Anti-inflammatoire — lin, noix' },
      { icon: '🍊', label: 'Vitamine C', detail: 'Booste l\'absorption du fer' },
    ],
    tip: 'Recharge en fer & réconfort. Aliments chauds, bouillons riches.',
  },
  {
    id: 'follicular', label: 'Folliculaire', range: 'J6 – J14', moon: '🌒',
    color: '#27AE60', colorDim: 'rgba(39,174,96,0.12)',
    needs: [
      { icon: '💪', label: 'Protéines', detail: 'Quinoa, tofu, pois chiches' },
      { icon: '🥦', label: 'Vitamines B', detail: 'Brocoli, avocat, légumineuses' },
      { icon: '🌾', label: 'Fibres', detail: 'Avoine, chia' },
      { icon: '💧', label: 'Hydratation', detail: 'Concombre, courgette' },
    ],
    tip: 'Énergie légère & hydratation. Phase idéale pour démarrer des projets.',
  },
  {
    id: 'ovulatory', label: 'Ovulatoire', range: 'J15 – J17', moon: '🌕',
    color: '#F39C12', colorDim: 'rgba(243,156,18,0.12)',
    needs: [
      { icon: '🫐', label: 'Antioxydants', detail: 'Baies, tomate, grenade' },
      { icon: '🍋', label: 'Vitamine C', detail: 'Poivron, agrumes' },
      { icon: '⚡', label: 'Zinc', detail: 'Graines de courge, sésame' },
      { icon: '🥬', label: 'Crucifères', detail: 'Brocoli, chou-fleur (détox hépatique)' },
    ],
    tip: 'Soutien hépatique maximal. Pic hormonal — antioxydants et zinc protègent les cellules.',
  },
  {
    id: 'luteal', label: 'Lutéale', range: 'J18 – J28', moon: '🌗',
    color: '#8E44AD', colorDim: 'rgba(142,68,173,0.12)',
    needs: [
      { icon: '🌾', label: 'Glucides complexes', detail: 'Patate douce, avoine, quinoa' },
      { icon: '🧲', label: 'Magnésium', detail: 'Réduit le SPM — graines, noix' },
      { icon: '🧬', label: 'Vitamine B6', detail: 'Régule l\'humeur — banane, pois chiches' },
      { icon: '🍫', label: 'Cacao pur', detail: 'Magnésium + plaisir anti-cravings' },
    ],
    tip: 'Glycémie stable & anti-SPM. Favorisez les glucides complexes pour limiter les fringales.',
  },
];

const ASTRO_SIGNS = [
  { id: 'aries',       glyph: '♈', label: 'Bélier',     element: 'Feu' },
  { id: 'taurus',      glyph: '♉', label: 'Taureau',    element: 'Terre' },
  { id: 'gemini',      glyph: '♊', label: 'Gémeaux',    element: 'Air' },
  { id: 'cancer',      glyph: '♋', label: 'Cancer',     element: 'Eau' },
  { id: 'leo',         glyph: '♌', label: 'Lion',       element: 'Feu' },
  { id: 'virgo',       glyph: '♍', label: 'Vierge',     element: 'Terre' },
  { id: 'libra',       glyph: '♎', label: 'Balance',    element: 'Air' },
  { id: 'scorpio',     glyph: '♏', label: 'Scorpion',   element: 'Eau' },
  { id: 'sagittarius', glyph: '♐', label: 'Sagittaire', element: 'Feu' },
  { id: 'capricorn',   glyph: '♑', label: 'Capricorne', element: 'Terre' },
  { id: 'aquarius',    glyph: '♒', label: 'Verseau',    element: 'Air' },
  { id: 'pisces',      glyph: '♓', label: 'Poissons',   element: 'Eau' },
];
const ELEMENT_COLOR = { Feu: '#C0392B', Terre: '#1d6b40', Air: '#2563a8', Eau: '#2980B9' };
const ELEMENT_ICON  = { Feu: '🔥', Terre: '🌿', Air: '🌬️', Eau: '💧' };

const LOCAL_CYCLE_KEY     = 'alim_cycle_phase';
const LOCAL_ASTRO_KEY     = 'alim_astro_sign';
const LOCAL_MENOPAUSE_KEY = 'alim_menopause';
const LOCAL_GENDER_KEY    = 'alim_gender';
const MENO_COLOR          = '#c97eb8';
const MENO_COLOR_DIM      = 'rgba(201,126,184,0.12)';

const GENDER_OPTIONS = [
  { value: 'female', label: 'Femme',       icon: '♀' },
  { value: 'male',   label: 'Homme',       icon: '♂' },
  { value: '',       label: 'Non précisé', icon: '◎' },
];

// Groupe les favoris par dish_type
function groupFavoritesByDish(favorites) {
  const knownValues = new Set(DISH_OPTIONS.map(o => o.value));
  const map = {};
  for (const r of favorites) {
    const key = (r.dish_type && knownValues.has(r.dish_type)) ? r.dish_type : '__other__';
    if (!map[key]) map[key] = [];
    map[key].push(r);
  }
  const groups = [];
  for (const opt of DISH_OPTIONS) {
    if (map[opt.value]?.length) groups.push({ ...opt, recipes: map[opt.value] });
  }
  if (map['__other__']?.length) groups.push({ value: '__other__', label: '📦 Autre', recipes: map['__other__'] });
  return groups;
}

// ── Composant principal ───────────────────────────────────────────────────────

export default function ProfilePage({ onAuthClick }) {
  const { user, logout } = useAuth();
  const { favorites, clear: clearFavorites } = useFavorites();
  const { recent, clear: clearRecent } = useRecentlyViewed();
  const toast = useToast();

  const [prefs, setPrefs]         = useState({ diet: '', goal: '' });
  const [gender, setGender] = useState(
    () => localStorage.getItem(LOCAL_GENDER_KEY) || ''
  );
  const [isMenopause, setIsMenopause] = useState(
    () => localStorage.getItem(LOCAL_MENOPAUSE_KEY) === 'true'
  );
  const [cyclePhase, setCyclePhase] = useState(
    () => localStorage.getItem(LOCAL_CYCLE_KEY) || ''
  );
  const [astroSign, setAstroSign]   = useState(
    () => localStorage.getItem(LOCAL_ASTRO_KEY) || ''
  );
  const [favExpanded, setFavExpanded] = useState(false);
  const [confirmClear, setConfirmClear] = useState(false);

  const saveGender = (val) => {
    setGender(val);
    localStorage.setItem(LOCAL_GENDER_KEY, val);
    if (val === 'male') {
      setIsMenopause(false);
      localStorage.setItem(LOCAL_MENOPAUSE_KEY, 'false');
    }
  };

  const toggleMenopause = () => {
    const next = !isMenopause;
    setIsMenopause(next);
    localStorage.setItem(LOCAL_MENOPAUSE_KEY, String(next));
    if (next) {
      setCyclePhase('');
      localStorage.removeItem(LOCAL_CYCLE_KEY);
    }
  };
  const saveCyclePhase = (id) => {
    setCyclePhase(id);
    localStorage.setItem(LOCAL_CYCLE_KEY, id);
  };
  const saveAstroSign = (id) => {
    setAstroSign(id);
    localStorage.setItem(LOCAL_ASTRO_KEY, id);
  };

  const handleSave = async () => {
    try {
      await profileApi.update(prefs);
      toast('Préférences enregistrées');
    } catch {
      toast('Erreur lors de la sauvegarde', 'error');
    }
  };

  const favGroups = groupFavoritesByDish(favorites);
  const currentPhase = CYCLE_PHASES.find(p => p.id === cyclePhase);
  const currentSign  = ASTRO_SIGNS.find(s => s.id === astroSign);

  // ── État non connecté ─────────────────────────────────────────────────────
  if (!user) {
    return (
      <div className="page-profil">
        <div className="page-header">
          <h1 className="page-title"><span className="page-icon">◎</span> Mon profil</h1>
          <p className="page-sub">Connectez-vous pour accéder à votre profil personnalisé.</p>
        </div>

        {/* Favoris accessibles sans compte */}
        {favorites.length > 0 && (
          <div style={{
            background: 'var(--sur)', border: '1px solid var(--brd)', borderRadius: 12,
            padding: 24, marginBottom: 24,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
              <h2 style={{ margin: 0, fontSize: 18, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 10 }}>
                ♥ Mes favoris
                <span style={{ fontSize: 13, fontWeight: 600, background: 'var(--sur2)', color: 'var(--mut)', border: '1px solid var(--brd)', borderRadius: 20, padding: '2px 9px' }}>
                  {favorites.length}
                </span>
              </h2>
              <button className="frigo-search-btn" style={{ width: 'auto', padding: '8px 18px', fontSize: 13 }}
                onClick={() => navigate('/favoris')}>
                Voir tous →
              </button>
            </div>
            <p style={{ fontSize: 13, color: 'var(--mut)', marginBottom: 16 }}>
              💡 Vos favoris sont sauvegardés localement — aucun compte requis.
            </p>
            <div className="recipe-grid">
              {favorites.slice(0, 3).map(r => <RecipeCard key={r.id} recipe={r} />)}
            </div>
          </div>
        )}

        <div className="frigo-empty">
          <div className="frigo-empty-icon" style={{ fontSize: 48 }}>◎</div>
          <p>Connectez-vous pour sauvegarder vos préférences, votre cycle et vos objectifs nutritionnels.</p>
          <button className="frigo-search-btn" onClick={onAuthClick} style={{ marginTop: 24 }}>
            Connexion / Inscription
          </button>
        </div>
      </div>
    );
  }

  // ── Vue connectée ─────────────────────────────────────────────────────────
  return (
    <div className="page-profil" style={{ animation: 'fadeIn 0.2s ease-out' }}>

      {/* ── En-tête profil ── */}
      <div className="page-header" style={{ marginBottom: 28 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 16 }}>
          <div>
            <h1 className="page-title" style={{ marginBottom: 6 }}>
              <span className="page-icon">◎</span> Mon profil
            </h1>
            <p className="page-sub">{user.email}</p>
          </div>
          <button
            onClick={logout}
            style={{
              background: 'transparent', border: '1px solid var(--brd)',
              color: 'var(--mut)', fontSize: 13, fontWeight: 500,
              padding: '7px 14px', borderRadius: 8, cursor: 'pointer',
              fontFamily: 'inherit', transition: 'all 0.15s',
            }}
          >
            Déconnexion
          </button>
        </div>
      </div>

      {/* ── Grille préférences ── */}
      <div className="profil-grid" style={{ marginBottom: 32 }}>

        {/* Préférences alimentaires */}
        <div className="frigo-panel">
          <h3 className="frigo-panel-title">🥗 Préférences alimentaires</h3>

          {/* Genre */}
          <div className="form-field" style={{ marginBottom: 18 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt2)', display: 'block', marginBottom: 8 }}>Je suis</label>
            <div style={{ display: 'flex', gap: 8 }}>
              {GENDER_OPTIONS.map(opt => {
                const isActive = gender === opt.value;
                return (
                  <button key={opt.value} onClick={() => saveGender(opt.value)}
                    style={{
                      flex: 1, padding: '9px 8px', borderRadius: 10, cursor: 'pointer',
                      fontFamily: 'inherit', fontSize: 13, fontWeight: isActive ? 600 : 400,
                      display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4,
                      transition: 'all 0.15s',
                      background: isActive ? 'var(--grn-dim)' : 'var(--sur2)',
                      border: `1px solid ${isActive ? 'var(--grn)' : 'var(--brd)'}`,
                      color: isActive ? 'var(--grn)' : 'var(--txt2)',
                    }}>
                    <span style={{ fontSize: 18 }}>{opt.icon}</span>
                    <span>{opt.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          <div className="form-field" style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt2)', display: 'block', marginBottom: 6 }}>Régime principal</label>
            <select
              value={prefs.diet}
              onChange={e => setPrefs(p => ({ ...p, diet: e.target.value }))}
              className="search-input"
              style={{ padding: '10px 14px', fontSize: 14 }}
            >
              <option value="">Aucun en particulier</option>
              <option value="vegan">Vegan</option>
              <option value="vegetarian">Végétarien</option>
              <option value="flexitarian">Flexitarien</option>
            </select>
          </div>

          <div className="form-field" style={{ marginBottom: 14 }}>
            <label style={{ fontSize: 13, fontWeight: 600, color: 'var(--txt2)', display: 'block', marginBottom: 6 }}>Objectif nutritionnel</label>
            <select
              value={prefs.goal}
              onChange={e => setPrefs(p => ({ ...p, goal: e.target.value }))}
              className="search-input"
              style={{ padding: '10px 14px', fontSize: 14 }}
            >
              <option value="">Sans objectif particulier</option>
              <option value="proteines">Apport protéique élevé</option>
              <option value="poids">Gestion du poids</option>
              <option value="energie">Énergie sportive</option>
              <option value="sante">Santé générale</option>
              <option value="cycle">Soutien hormonal / cycle</option>
              <option value="antioxidants">Antioxydants & longévité</option>
            </select>
          </div>

          <button className="frigo-search-btn" onClick={handleSave} style={{ marginTop: 8 }}>
            Sauvegarder
          </button>
        </div>

        {/* Mon cycle */}
        <div className="frigo-panel">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 14 }}>
            <h3 className="frigo-panel-title" style={{ margin: 0 }}>
              {gender === 'male' ? '🌑 Cycle féminin' : '🌑 Mon cycle'}
            </h3>
            {/* Toggle ménopause — uniquement pour profil féminin ou non précisé */}
            {gender !== 'male' && <button
              onClick={toggleMenopause}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, padding: '6px 12px',
                borderRadius: 20, fontSize: 12, fontWeight: 500, cursor: 'pointer',
                fontFamily: 'inherit', transition: 'all 0.15s',
                background: isMenopause ? MENO_COLOR_DIM : 'var(--sur2)',
                border: `1px solid ${isMenopause ? MENO_COLOR : 'var(--brd)'}`,
                color: isMenopause ? MENO_COLOR : 'var(--mut)',
              }}
            >
              <span style={{ fontSize: 15 }}>♀</span>
              {isMenopause ? 'Ménopausée ✓' : 'Ménopausée ?'}
            </button>}
          </div>

          {gender === 'male' ? (
            /* Vue masculine : invitation douce */
            <div style={{
              padding: '18px 16px', borderRadius: 12, textAlign: 'center',
              background: 'linear-gradient(135deg, rgba(201,126,184,0.08), rgba(88,166,255,0.06))',
              border: '1px solid rgba(201,126,184,0.25)',
            }}>
              <div style={{ fontSize: 36, marginBottom: 10 }}>🍳</div>
              <p style={{ margin: '0 0 6px', fontSize: 14, fontWeight: 600, color: 'var(--txt)' }}>
                Cuisinez pour elle
              </p>
              <p style={{ margin: '0 0 14px', fontSize: 12, color: 'var(--mut)', lineHeight: 1.6 }}>
                Activez la page Cycle pour découvrir les besoins nutritionnels selon les phases du cycle féminin — idéal pour cuisiner pour votre partenaire, fille ou amie.
              </p>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'center', flexWrap: 'wrap' }}>
                {['🩸 Fer', '🧲 Magnésium', '🫐 Antioxydants', '🧠 B6'].map(t => (
                  <span key={t} style={{ fontSize: 11, padding: '3px 10px', borderRadius: 20,
                    background: 'rgba(201,126,184,0.12)', color: MENO_COLOR,
                    border: `1px solid ${MENO_COLOR}30` }}>{t}</span>
                ))}
              </div>
              <p style={{ margin: '12px 0 0', fontSize: 11, color: 'var(--mut)', fontStyle: 'italic' }}>
                Accessible depuis la page Cycle → "Et si vous cuisiniez pour elle ?"
              </p>
            </div>
          ) : isMenopause ? (
            /* Mode ménopause activé */
            <div style={{ padding: '14px 16px', borderRadius: 10, background: MENO_COLOR_DIM, border: `1px solid ${MENO_COLOR}40` }}>
              <p style={{ margin: '0 0 8px', fontSize: 13, fontWeight: 600, color: MENO_COLOR }}>
                ♀ Mode ménopause activé
              </p>
              <p style={{ margin: 0, fontSize: 12, color: 'var(--txt2)', lineHeight: 1.6 }}>
                La page Cycle affiche les préconisations alimentaires et conseils adaptés à la ménopause — sans le suivi de cycle.
              </p>
              <button onClick={toggleMenopause}
                style={{ marginTop: 10, background: 'transparent', border: `1px solid ${MENO_COLOR}60`,
                  color: MENO_COLOR, fontSize: 11, padding: '4px 10px', borderRadius: 6,
                  cursor: 'pointer', fontFamily: 'inherit' }}>
                Désactiver
              </button>
            </div>
          ) : (
            <>
              <p style={{ fontSize: 13, color: 'var(--mut)', marginBottom: 14, lineHeight: 1.5 }}>
                Sélectionnez votre phase actuelle pour des recommandations nutritionnelles adaptées.
              </p>

              {/* Sélecteur 4 phases */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
                {CYCLE_PHASES.map(phase => {
                  const isActive = cyclePhase === phase.id;
                  return (
                    <button key={phase.id} onClick={() => saveCyclePhase(phase.id)}
                      style={{
                        padding: '10px 12px', borderRadius: 10, cursor: 'pointer',
                        border: `1px solid ${isActive ? phase.color : 'var(--brd)'}`,
                        background: isActive ? phase.colorDim : 'var(--sur2)',
                        display: 'flex', alignItems: 'center', gap: 8,
                        fontFamily: 'inherit', transition: 'all 0.15s', textAlign: 'left',
                      }}>
                      <span style={{ fontSize: 18 }}>{phase.moon}</span>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: isActive ? phase.color : 'var(--txt)' }}>
                          {phase.label}
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--mut)' }}>{phase.range}</div>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Besoins de la phase active */}
              {currentPhase && (
                <div style={{
                  padding: '12px 14px', borderRadius: 10,
                  background: currentPhase.colorDim,
                  border: `1px solid ${currentPhase.color}40`,
                }}>
                  <p style={{ fontSize: 12, fontWeight: 600, color: currentPhase.color, marginBottom: 8 }}>
                    {currentPhase.tip}
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 4 }}>
                    {currentPhase.needs.map(n => (
                      <div key={n.label} style={{ fontSize: 12, color: 'var(--txt2)', display: 'flex', gap: 5, alignItems: 'flex-start' }}>
                        <span>{n.icon}</span>
                        <span><strong>{n.label}</strong> — {n.detail}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>

      {/* ── Mon signe astrologique ── */}
      <div className="frigo-panel" style={{ marginBottom: 32 }}>
        <h3 className="frigo-panel-title">✨ Mon signe astrologique</h3>
        <p style={{ fontSize: 13, color: 'var(--mut)', marginBottom: 14 }}>
          Influence le type de recettes suggérées dans la section Astro (élément : Feu, Terre, Air, Eau).
        </p>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: 8 }}>
          {ASTRO_SIGNS.map(s => {
            const isActive = astroSign === s.id;
            const c = ELEMENT_COLOR[s.element];
            return (
              <button
                key={s.id}
                onClick={() => saveAstroSign(s.id)}
                style={{
                  padding: '10px 6px', borderRadius: 10, cursor: 'pointer',
                  border: `1px solid ${isActive ? c : 'var(--brd)'}`,
                  background: isActive ? `color-mix(in srgb, ${c} 14%, var(--sur))` : 'var(--sur2)',
                  display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3,
                  fontFamily: 'inherit', transition: 'all 0.15s',
                }}
              >
                <span style={{ fontSize: 20, color: isActive ? c : 'var(--txt)' }}>{s.glyph}</span>
                <span style={{ fontSize: 10, fontWeight: isActive ? 600 : 400, color: isActive ? c : 'var(--mut)' }}>{s.label}</span>
                <span style={{ fontSize: 8, color: 'var(--mut)' }}>{ELEMENT_ICON[s.element]}</span>
              </button>
            );
          })}
        </div>
        {currentSign && (
          <p style={{ marginTop: 12, fontSize: 13, color: 'var(--mut)' }}>
            Signe sélectionné : <strong style={{ color: ELEMENT_COLOR[currentSign.element] }}>
              {currentSign.glyph} {currentSign.label}
            </strong> — Élément {currentSign.element} {ELEMENT_ICON[currentSign.element]}
          </p>
        )}
      </div>

      {/* ── Mes Favoris ── */}
      <div style={{ marginBottom: 32 }}>
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          marginBottom: 20, paddingBottom: 14, borderBottom: '1px solid var(--brd)',
        }}>
          <h2 style={{ margin: 0, fontSize: 20, fontWeight: 600, display: 'flex', alignItems: 'center', gap: 10 }}>
            ♥ Mes favoris
            {favorites.length > 0 && (
              <span style={{
                fontSize: 13, fontWeight: 600,
                background: 'var(--grn-dim)', color: 'var(--grn)',
                border: '1px solid rgba(29,107,64,0.3)', borderRadius: 20, padding: '2px 9px',
              }}>
                {favorites.length}
              </span>
            )}
          </h2>
          <div style={{ display: 'flex', gap: 8 }}>
            {favorites.length > 0 && (
              <>
                <button
                  onClick={() => navigate('/favoris')}
                  className="frigo-search-btn"
                  style={{ width: 'auto', padding: '7px 16px', fontSize: 13 }}
                >
                  Voir la page complète →
                </button>
                <button
                  onClick={() => setFavExpanded(!favExpanded)}
                  style={{
                    background: 'transparent', border: '1px solid var(--brd)',
                    color: 'var(--mut)', fontSize: 13, padding: '7px 14px',
                    borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
                  }}
                >
                  {favExpanded ? 'Réduire ▲' : 'Tout voir ▼'}
                </button>
              </>
            )}
          </div>
        </div>

        {favorites.length === 0 ? (
          <div style={{
            padding: '40px 24px', textAlign: 'center', color: 'var(--mut)',
            background: 'var(--sur)', border: '1px solid var(--brd)', borderRadius: 12,
          }}>
            <div style={{ fontSize: 40, opacity: 0.2, marginBottom: 12 }}>♡</div>
            <p style={{ fontSize: 15, fontWeight: 500, color: 'var(--txt2)', marginBottom: 8 }}>Aucun favori</p>
            <p style={{ fontSize: 13, maxWidth: 320, margin: '0 auto' }}>
              Cliquez sur ♡ sur n'importe quelle carte recette pour la sauvegarder ici.
            </p>
          </div>
        ) : (
          <>
            {/* Aperçu compact (3 recettes max) ou liste complète par groupe */}
            {!favExpanded ? (
              <div className="recipe-grid">
                {favorites.slice(0, 3).map(r => <RecipeCard key={r.id} recipe={r} />)}
                {favorites.length > 3 && (
                  <div style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: 'var(--sur)', border: '1px solid var(--brd)', borderRadius: 10,
                    cursor: 'pointer', color: 'var(--grn)', fontWeight: 600, fontSize: 15,
                    minHeight: 100,
                  }} onClick={() => setFavExpanded(true)}>
                    +{favorites.length - 3} de plus →
                  </div>
                )}
              </div>
            ) : (
              <>
                {favGroups.map(group => (
                  <div key={group.value} style={{ marginBottom: 32 }}>
                    <h3 style={{
                      fontSize: 16, fontWeight: 600, marginBottom: 14,
                      display: 'flex', alignItems: 'center', gap: 8, color: 'var(--txt2)',
                    }}>
                      {group.label}
                      <span style={{ fontSize: 12, background: 'var(--sur2)', border: '1px solid var(--brd)', color: 'var(--mut)', borderRadius: 20, padding: '1px 8px' }}>
                        {group.recipes.length}
                      </span>
                    </h3>
                    <div className="recipe-grid">
                      {group.recipes.map(r => <RecipeCard key={r.id} recipe={r} />)}
                    </div>
                  </div>
                ))}
                {/* Bouton effacer tout */}
                <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                  <button
                    onClick={() => { if (confirmClear) { clearFavorites(); setConfirmClear(false); } else setConfirmClear(true); }}
                    style={{
                      background: confirmClear ? 'rgba(179,45,29,0.10)' : 'transparent',
                      border: `1px solid ${confirmClear ? 'var(--red)' : 'var(--brd)'}`,
                      color: confirmClear ? 'var(--red)' : 'var(--mut)',
                      fontSize: 12, fontWeight: 500, padding: '7px 16px', borderRadius: 8,
                      cursor: 'pointer', fontFamily: 'inherit', transition: 'all 0.15s',
                    }}
                  >
                    {confirmClear ? '⚠️ Confirmer la suppression' : '✕ Effacer tous les favoris'}
                  </button>
                  {confirmClear && (
                    <button onClick={() => setConfirmClear(false)} style={{
                      background: 'transparent', border: '1px solid var(--brd)', color: 'var(--mut)',
                      fontSize: 12, padding: '7px 12px', borderRadius: 8, cursor: 'pointer', fontFamily: 'inherit',
                    }}>Annuler</button>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>

      {/* ── Récemment consultées ── */}
      {recent.length > 0 && (
        <div>
          <div className="profil-section-header" style={{ marginBottom: 16, paddingBottom: 14, borderBottom: '1px solid var(--brd)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <h2 className="profil-section-title" style={{ fontSize: 20, fontWeight: 600, margin: 0 }}>
              🕐 Récemment consultées
            </h2>
            <button className="profil-clear-btn" onClick={clearRecent}>Effacer</button>
          </div>
          <div className="recipe-grid">
            {recent.map(r => <RecipeCard key={r.id} recipe={r} />)}
          </div>
        </div>
      )}
    </div>
  );
}
