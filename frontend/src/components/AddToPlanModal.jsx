/**
 * AddToPlanModal — Ajouter une recette au planning hebdomadaire.
 * Lit/écrit directement dans localStorage (alim_plan_weekly) sans backend.
 */
import { useState } from 'react';
import { createPortal } from 'react-dom';

const PLAN_KEY = 'alim_plan_weekly';
const DAYS_KEY = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche'];
const DAYS_FR  = ['Lundi','Mardi','Mercredi','Jeudi','Vendredi','Samedi','Dimanche'];
const MEALS = [
  { key: 'breakfast', label: 'Petit-déj', icon: '🌅' },
  { key: 'lunch',     label: 'Déjeuner',  icon: '☀️' },
  { key: 'dinner',    label: 'Dîner',     icon: '🌙' },
];

const MEAL_DEFAULTS = {
  breakfast: { dishTypes: ['breakfast'], servings: 2 },
  lunch:     { dishTypes: ['main'],      servings: 4 },
  dinner:    { dishTypes: ['main'],      servings: 4 },
};

function addToPlan(recipe, dayKey, mealKey) {
  try {
    const raw  = localStorage.getItem(PLAN_KEY);
    const plan = raw ? JSON.parse(raw) : null;

    // Bootstrap the plan structure if it doesn't exist or is incomplete
    const ensured = plan && plan[dayKey] ? plan : (() => {
      const p = plan || { meta: {} };
      for (const dk of DAYS_KEY) {
        if (!p[dk]) p[dk] = {};
        for (const [m, d] of Object.entries(MEAL_DEFAULTS)) {
          if (!p[dk][m]) p[dk][m] = { dishTypes: [...d.dishTypes], servings: d.servings, skip: false, recipes: [] };
        }
      }
      return p;
    })();

    const slot = ensured[dayKey][mealKey];
    if (!slot.recipes) slot.recipes = [];
    slot.recipes.push({
      id:         recipe.id || recipe._id,
      title_fr:   recipe.titles?.fr || recipe.title_fr || recipe.title || '',
      title:      recipe.titles?.original || recipe.title || '',
      _dish_type: slot.dishTypes?.[0] || 'main',
    });
    localStorage.setItem(PLAN_KEY, JSON.stringify(ensured));
    return true;
  } catch { return false; }
}

export default function AddToPlanModal({ recipe, onClose }) {
  const today   = new Date().getDay(); // 0=dim, 1=lun...
  const todayIdx = today === 0 ? 6 : today - 1; // map to 0=lun..6=dim
  const [day,  setDay]  = useState(DAYS_KEY[todayIdx] || 'lundi');
  const [meal, setMeal] = useState('dinner');
  const [done, setDone] = useState(false);

  const confirm = () => {
    addToPlan(recipe, day, meal);
    setDone(true);
    setTimeout(onClose, 1400);
  };

  const title = recipe.titles?.fr || recipe.title_fr || recipe.title || 'Recette';

  return createPortal(
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 1000,
        background: 'rgba(0,0,0,0.55)', backdropFilter: 'blur(4px)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
      }}
      onClick={onClose}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--sur)', border: '1px solid var(--brd)',
          borderRadius: 16, padding: '28px 24px', width: 360, maxWidth: '100%',
          boxShadow: '0 24px 64px rgba(0,0,0,0.3)',
        }}
      >
        {done ? (
          <div style={{ textAlign: 'center', padding: '20px 0' }}>
            <div style={{ fontSize: 44, marginBottom: 12 }}>✓</div>
            <p style={{ fontSize: 15, color: 'var(--grn)', fontWeight: 500, margin: 0 }}>
              Ajouté au planning !
            </p>
            <p style={{ fontSize: 12, color: 'var(--mut)', marginTop: 6 }}>
              {DAYS_FR[DAYS_KEY.indexOf(day)]} · {MEALS.find(m => m.key === meal)?.label}
            </p>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 20 }}>
              <div>
                <h3 style={{ margin: 0, fontSize: 17, fontWeight: 500 }}>Ajouter au planning</h3>
                <p style={{ margin: '4px 0 0', fontSize: 12, color: 'var(--txt2)', lineHeight: 1.4, maxWidth: 260 }}>
                  {title}
                </p>
              </div>
              <button onClick={onClose} style={{
                background: 'transparent', border: 'none', cursor: 'pointer',
                fontSize: 18, color: 'var(--mut)', padding: '0 4px', lineHeight: 1,
              }}>✕</button>
            </div>

            {/* Jour */}
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 8 }}>
                Jour
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
                {DAYS_KEY.map((dk, i) => (
                  <button key={dk} onClick={() => setDay(dk)} style={{
                    padding: '6px 2px', borderRadius: 6, fontSize: 11,
                    border: `1px solid ${day === dk ? 'var(--grn)' : 'var(--brd)'}`,
                    background: day === dk ? 'var(--grn)' : 'transparent',
                    color: day === dk ? 'var(--bg)' : 'var(--txt2)',
                    cursor: 'pointer', fontFamily: 'inherit', fontWeight: day === dk ? 500 : 400,
                    textAlign: 'center',
                  }}>
                    {DAYS_FR[i].slice(0, 3)}
                  </button>
                ))}
              </div>
            </div>

            {/* Repas */}
            <div style={{ marginBottom: 24 }}>
              <div style={{ fontSize: 11, letterSpacing: '0.08em', textTransform: 'uppercase', color: 'var(--mut)', marginBottom: 8 }}>
                Repas
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                {MEALS.map(m => (
                  <button key={m.key} onClick={() => setMeal(m.key)} style={{
                    flex: 1, padding: '10px 4px', borderRadius: 10, fontSize: 12,
                    border: `1px solid ${meal === m.key ? 'var(--grn)' : 'var(--brd)'}`,
                    background: meal === m.key ? 'var(--grn)' : 'transparent',
                    color: meal === m.key ? 'var(--bg)' : 'var(--txt2)',
                    cursor: 'pointer', fontFamily: 'inherit', fontWeight: meal === m.key ? 500 : 400,
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 5,
                    transition: 'all .12s',
                  }}>
                    <span style={{ fontSize: 20 }}>{m.icon}</span>
                    <span>{m.label}</span>
                  </button>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 10 }}>
              <button onClick={onClose} style={{
                flex: 1, padding: '10px', borderRadius: 8, fontSize: 14,
                background: 'transparent', border: '1px solid var(--brd)',
                color: 'var(--txt2)', cursor: 'pointer', fontFamily: 'inherit',
              }}>
                Annuler
              </button>
              <button onClick={confirm} style={{
                flex: 2, padding: '10px', borderRadius: 8, fontSize: 14,
                background: 'var(--grn)', border: 'none',
                color: 'var(--bg)', cursor: 'pointer', fontWeight: 500, fontFamily: 'inherit',
              }}>
                ▦ Ajouter
              </button>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body
  );
}
