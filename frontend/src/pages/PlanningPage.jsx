import { useState } from 'react';
import { planning as planningApi } from '../api';
import { useAuth } from '../AuthContext';

const DAYS    = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche'];
const MEALS   = ['Déjeuner', 'Dîner'];

export default function PlanningPage() {
  const { user }         = useAuth();
  const [plan, setPlan]  = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);
  const [diet, setDiet]       = useState('');
  const [budget, setBudget]   = useState(50);

  const generatePlan = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await planningApi.mealplan({ diet: diet || undefined, budget });
      setPlan(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-planning">
      <div className="page-header">
        <h1 className="page-title"><span className="page-icon">▦</span> Planning</h1>
        <p className="page-sub">Votre plan de repas sur 7 jours, généré automatiquement.</p>
      </div>

      <div className="planning-controls">
        <select
          value={diet}
          onChange={(e) => setDiet(e.target.value)}
          className="search-input"
          style={{ maxWidth: 180, padding: '10px 14px', fontSize: 14 }}
        >
          <option value="">Tous les régimes</option>
          <option value="vegan">Vegan</option>
          <option value="vegetarian">Végétarien</option>
        </select>

        <label className="frigo-opt-label" style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          Budget semaine : <strong>{budget} €</strong>
          <input
            type="range" min={20} max={150} value={budget}
            onChange={(e) => setBudget(+e.target.value)}
            className="frigo-slider"
          />
        </label>

        <button className="search-button" onClick={generatePlan} disabled={loading}>
          {loading ? 'Génération…' : 'Générer mon planning'}
        </button>
      </div>

      {error && <div className="state-msg state-msg--error">{error}</div>}

      {!plan && !loading && (
        <div className="planning-empty">
          <div className="planning-empty-grid">
            {DAYS.map((day) => (
              <div key={day} className="planning-day-col planning-day-col--empty">
                <div className="planning-day-header">{day}</div>
                {MEALS.map((m) => (
                  <div key={m} className="planning-meal-slot planning-meal-slot--empty">
                    <span className="planning-meal-label">{m}</span>
                    <div className="planning-meal-placeholder" />
                  </div>
                ))}
              </div>
            ))}
          </div>
          <p className="planning-hint">Cliquez sur "Générer mon planning" pour commencer.</p>
        </div>
      )}

      {loading && (
        <div className="skeleton-grid">
          {Array.from({ length: 7 }).map((_, i) => (
            <div key={i} className="skeleton-card">
              <div className="skeleton skeleton-line" style={{ width: '50%', marginBottom: 12 }} />
              <div className="skeleton skeleton-img" style={{ height: 60 }} />
              <div className="skeleton skeleton-img" style={{ height: 60, marginTop: 8 }} />
            </div>
          ))}
        </div>
      )}

      {plan && !loading && (
        <div className="planning-grid">
          {DAYS.map((day, di) => {
            const dayMeals = plan.days?.[di] || plan[day.toLowerCase()] || {};
            return (
              <div key={day} className="planning-day-col">
                <div className="planning-day-header">{day}</div>
                {MEALS.map((meal, mi) => {
                  const recipe = dayMeals[meal.toLowerCase()] || dayMeals[mi];
                  return (
                    <div key={meal} className="planning-meal-slot">
                      <span className="planning-meal-label">{meal}</span>
                      {recipe ? (
                        <div className="planning-meal-card">
                          <span className="planning-meal-initial">
                            {(recipe.title_fr || recipe.title || '?')[0]}
                          </span>
                          <span className="planning-meal-name">
                            {recipe.title_fr || recipe.title || '—'}
                          </span>
                        </div>
                      ) : (
                        <div className="planning-meal-empty">—</div>
                      )}
                    </div>
                  );
                })}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
