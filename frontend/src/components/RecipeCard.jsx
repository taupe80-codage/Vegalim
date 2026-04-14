import { navigate } from '../Router';

export function getRecipeBadges(recipe) {
  const badges = [];
  const flags = recipe.diet_flags || {};
  const health = recipe.health_scores || {};
  
  if (flags.vegan) badges.push({ id: 'vegan', label: 'Vegan', symbol: '🌿', color: 'var(--green)' });
  else if (flags.vegetarian) badges.push({ id: 'vegetarian', label: 'Végétarien', symbol: '🥗', color: '#8BC34A' });
  
  if (flags.gluten_free) badges.push({ id: 'gluten_free', label: 'Sans Gluten', symbol: '🚫🌾' });
  if (flags.lactose_free) badges.push({ id: 'lactose_free', label: 'Sans Lactose', symbol: '🚫🍼' });
  if (flags.nut_free) badges.push({ id: 'nut_free', label: 'Sans Fruits à Coque', symbol: '🚫🥜' });
  
  if (health.high_protein) badges.push({ id: 'high_protein', label: 'Hyper Protéiné', symbol: '💪' });
  if (health.low_calorie) badges.push({ id: 'low_calorie', label: 'Faible en Calories', symbol: '📉' });
  if (health.high_fiber) badges.push({ id: 'high_fiber', label: 'Riche en Fibres', symbol: '🌾✨' });
  
  if (health.fodmap_level === 'low') badges.push({ id: 'low_fodmap', label: 'Low FODMAP', symbol: '🍏' });
  if (health.low_ig || health.diabetes_friendly) badges.push({ id: 'diabetes', label: 'Index Glycémique Bas', symbol: '🩸' });

  return badges;
}

export default function RecipeCard({ recipe }) {
  const score = recipe.final_score
    ? Math.round(recipe.final_score * 10)
    : recipe.iconic_score
    ? Math.round(recipe.iconic_score)
    : null;
    
  const time = recipe.total_time_min || recipe.timing?.total_expected || recipe.timing?.total_min;
  const initial = (recipe.titles?.fr || recipe.title_fr || '?')[0].toUpperCase();

  const handleClick = () => {
    const id = recipe.id || recipe._id;
    navigate(`/recette/${id}`);
  };

  const badges = getRecipeBadges(recipe);

  return (
    <div className="recipe-card" onClick={handleClick}>
      <div className="recipe-image">
        <div className="recipe-placeholder">{initial}</div>
        {score && (
          <div className="recipe-score-badge">
            ⭐ {score}/100
          </div>
        )}
      </div>
      <div className="recipe-content">
        <h3 className="recipe-title">{recipe.titles?.fr || recipe.title_fr || 'Recette'}</h3>
        <div className="recipe-meta">
          {time && <span>⏱ {time} min</span>}
          <span>🍽 {recipe.servings || 4} pers.</span>
        </div>
        
        <div className="badges" style={{ gap: '6px', flexWrap: 'wrap', marginTop: '6px' }}>
          {badges.map(b => (
            <span key={b.id} className="badge icon-badge" title={b.label} style={b.color ? { backgroundColor: b.color, color: '#fff', border: 'none' } : {}}>
              {b.symbol} {b.color ? b.label : ''}
            </span>
          ))}
          
          {recipe.completeness !== undefined && (
            <span className="badge" style={{ color: 'var(--amber)' }}>
              {Math.round(recipe.completeness * 100)}% frigo
            </span>
          )}
        </div>

        {recipe._why && (
          <p style={{ margin: '8px 0 0', fontSize: '11px', color: 'var(--green, #4caf50)', fontWeight: 600, lineHeight: 1.3 }}>
             {recipe._why}
          </p>
        )}
      </div>
    </div>
  );
}
