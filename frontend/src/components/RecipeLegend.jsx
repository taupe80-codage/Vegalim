export default function RecipeLegend() {
  const legendItems = [
    { symbol: '🌿', label: 'Vegan' },
    { symbol: '🥗', label: 'Végétarien' },
    { symbol: '🚫🌾', label: 'Sans Gluten' },
    { symbol: '🚫🍼', label: 'Sans Lactose' },
    { symbol: '🚫🥜', label: 'Sans Fruits à Coque' },
    { symbol: '💪', label: 'Hyper Protéiné' },
    { symbol: '📉', label: 'Faible en Calories' },
    { symbol: '🌾✨', label: 'Riche en Fibres' },
    { symbol: '🩸', label: 'Index Glycémique Bas' },
    { symbol: '🍏', label: 'Low FODMAP' }
  ];

  return (
    <div className="recipe-legend">
      <h4 style={{ margin: '0 0 10px', fontSize: '12px', textTransform: 'uppercase', color: 'var(--text-light)' }}>Légende des Symboles</h4>
      <div className="legend-grid" style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', fontSize: '13px' }}>
        {legendItems.map((item, index) => (
          <div key={index} className="legend-item" style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            <span style={{ fontSize: '16px' }}>{item.symbol}</span>
            <span style={{ color: 'var(--text)' }}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
