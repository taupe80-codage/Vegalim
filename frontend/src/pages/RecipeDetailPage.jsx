/**
 * RecipeDetailPage.jsx — Fiche recette complète
 */

import { useState, useEffect } from 'react';
import { useRouter, navigate } from '../Router';
import { recipes as recipesApi } from '../api';
import translations from '../translations.json';

export default function RecipeDetailPage() {
  const { params }       = useRouter();
  const [recipe, setRecipe]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState(null);
  const [servings, setServings] = useState(4);

  useEffect(() => {
    if (!params.id) return;
    setLoading(true);
    setError(null);

    recipesApi.byId(params.id)
      .then((data) => {
        setRecipe(data);
        setServings(data.servings || 4);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [params.id]);

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

  const ratio        = servings / (recipe.servings || 4);
  const isVegan      = recipe.diet_flags?.vegan;
  const isVeggie     = recipe.diet_flags?.vegetarian || recipe.diet_flags?.vegetarien;
  const isGF         = recipe.diet_flags?.gluten_free || recipe.diet_flags?.sans_gluten;
  const score        = recipe.final_score
    ? recipe.final_score.toFixed(1)
    : recipe.iconic_score ? (recipe.iconic_score / 10).toFixed(1) : null;
  const timeInfo     = recipe.timing || {};
  const ingredients  = recipe.composition || recipe.ingredients || [];

  return (
    <div className="recipe-detail-container">
      <button className="back-button" onClick={() => navigate('/')}>
        ← Retour aux résultats
      </button>

      <div className="detail-header">
        <div className="detail-hero">
          <div className="recipe-placeholder large-placeholder">
            {(recipe.titles?.fr || recipe.title_fr || '?')[0].toUpperCase()}
          </div>
        </div>
        <div className="detail-header-content">
          <h1 className="detail-title">{recipe.titles?.fr || recipe.title_fr || 'Recette'}</h1>
          {recipe.description && <p className="detail-description">{recipe.description}</p>}

          <div className="badges detail-badges">
            {isVegan  && <span className="badge vegan">Vegan</span>}
            {isVeggie && !isVegan && <span className="badge vegan">Végétarien</span>}
            {isGF     && <span className="badge">Sans Gluten</span>}
            {score    && <span className="badge score">Score : {score}/10</span>}
            {recipe.difficulty_level && <span className="badge">{recipe.difficulty_level}</span>}
            {recipe.origin?.country && <span className="badge">{recipe.origin.country}</span>}
          </div>

          <div className="detail-stats">
            {[
              { label: 'Total',        value: timeInfo.total_min || timeInfo.total_expected },
              { label: 'Cuisson',      value: timeInfo.cook_min },
              { label: 'Préparation',  value: timeInfo.prep_active_min },
            ].map(({ label, value }) => (
              <div key={label} className="stat-box">
                <span className="stat-label">{label}</span>
                <span className="stat-value">{value ? `${value} min` : '--'}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

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

          <ul className="ingredient-list">
            {ingredients.map((ing, idx) => {
              const rawName = ing.ingredient || ing.name || ing || '';
              const nameStr = typeof rawName === 'string' ? rawName : '';
              const name    = translations[nameStr] || nameStr;
              let qtyStr    = '';
              if (ing.quantity) {
                const q = ing.quantity * ratio;
                qtyStr  = `${q < 10 && q % 1 !== 0 ? q.toFixed(1) : Math.round(q)} ${ing.unit || ''}`.trim();
              }
              return (
                <li key={idx}>
                  <span className="ing-qty">{qtyStr}</span>
                  <span className="ing-name">
                    {name.replace(/_/g, ' ')}
                    {ing.meta?.state && <span className="ing-meta"> ({ing.meta.state})</span>}
                  </span>
                </li>
              );
            })}
          </ul>
        </div>

        {/* Instructions */}
        <div className="detail-instructions">
          <h3>Préparation</h3>
          {recipe.instructions?.length > 0 ? (
            <ol className="instruction-list">
              {recipe.instructions.map((step, idx) => (
                <li key={idx}>{step}</li>
              ))}
            </ol>
          ) : (
            <p className="no-instructions">
              Les étapes de préparation ne sont pas encore disponibles pour cette recette.
            </p>
          )}

          {/* Nutrition si disponible */}
          {recipe.nutrition && (
            <div className="nutrition-panel">
              <h4>Valeurs nutritionnelles <span>(par portion)</span></h4>
              <div className="nutrition-grid">
                {[
                  { key: 'calories',  label: 'Calories', unit: 'kcal' },
                  { key: 'proteins',  label: 'Protéines', unit: 'g' },
                  { key: 'carbs',     label: 'Glucides', unit: 'g' },
                  { key: 'fat',       label: 'Lipides', unit: 'g' },
                  { key: 'fiber',     label: 'Fibres', unit: 'g' },
                ].filter(({ key }) => recipe.nutrition[key] !== undefined).map(({ key, label, unit }) => (
                  <div key={key} className="nutr-item">
                    <span className="nutr-val">{Math.round(recipe.nutrition[key] / ratio)}</span>
                    <span className="nutr-unit">{unit}</span>
                    <span className="nutr-label">{label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
