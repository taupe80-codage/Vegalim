import { useState, useEffect, useRef } from 'react';

/**
 * RecipeLegend — Légende FAB générée depuis les constantes de filtres.
 * Importée ici en dur pour éviter les imports circulaires,
 * mais elle reflète exactement ce qui est filtrable dans HomePage.
 */

const LEGEND_SECTIONS = [
  {
    title: 'Régime',
    items: [
      { symbol: '🌿', label: 'Vegan' },
      { symbol: '🥦', label: 'Végétarien' },
      { symbol: '🥚', label: 'Sans Œufs' },
      { symbol: '🧀', label: 'Sans Produits Laitiers' },
      { symbol: '🫘', label: 'Sans Soja' },
    ],
  },
  {
    title: 'Allergènes',
    items: [
      { symbol: '🌾', label: 'Sans Gluten' },
      { symbol: '🥛', label: 'Sans Lactose' },
      { symbol: '🥜', label: 'Sans Noix' },
      { symbol: '🧪', label: 'Sans Fermentés' },
    ],
  },
  {
    title: 'Santé',
    items: [
      { symbol: '💪', label: 'Protéines (haut / source)' },
      { symbol: '🫘', label: 'Fibres (haut / source)' },
      { symbol: '⚖️', label: 'Faible en Calories' },
      { symbol: '🧂', label: 'Faible en Sucre / Sodium' },
      { symbol: '🩸', label: 'Index Glycémique Bas' },
      { symbol: '🍏', label: 'Low FODMAP' },
      { symbol: '🍊', label: 'Vitamines (C, D, Folate…)' },
      { symbol: '🦴', label: 'Minéraux (Ca, Fe, Mg, K, Zn)' },
      { symbol: '🐟', label: 'Oméga-3' },
      { symbol: '🌟', label: 'Antioxydants' },
    ],
  },
  {
    title: 'Type de plat',
    items: [
      { symbol: '🥣', label: 'Entrée' },
      { symbol: '🍽️', label: 'Plat principal' },
      { symbol: '🍰', label: 'Dessert' },
      { symbol: '🍲', label: 'Soupe / Velouté' },
      { symbol: '🥙', label: 'Street food' },
      { symbol: '⚡', label: 'Snack' },
      { symbol: '🫙', label: 'Base' },
      { symbol: '🥫', label: 'Sauce' },
    ],
  },
];

export default function RecipeLegend() {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return;
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [open]);

  useEffect(() => {
    const handler = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="legend-fab-wrapper" ref={ref}>
      {open && (
        <div className="legend-popover" role="dialog" aria-label="Légende des symboles">
          <div className="legend-popover-header">
            <span className="legend-popover-title">Légende</span>
            <button
              className="legend-popover-close"
              onClick={() => setOpen(false)}
              aria-label="Fermer"
            >✕</button>
          </div>
          <div className="legend-popover-body">
            {LEGEND_SECTIONS.map((section) => (
              <div key={section.title} className="legend-section">
                <span className="legend-section-title">{section.title}</span>
                <ul className="legend-popover-list">
                  {section.items.map((item, i) => (
                    <li key={i} className="legend-popover-item">
                      <span className="legend-popover-icon" aria-hidden="true">{item.symbol}</span>
                      <span className="legend-popover-label">{item.label}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        className={`legend-fab ${open ? 'legend-fab--open' : ''}`}
        onClick={() => setOpen(v => !v)}
        aria-label="Afficher la légende des symboles"
        aria-expanded={open}
      >
        <span className="legend-fab-icon" aria-hidden="true">{open ? '✕' : '📖'}</span>
        <span className="legend-fab-text">Légende</span>
      </button>
    </div>
  );
}
