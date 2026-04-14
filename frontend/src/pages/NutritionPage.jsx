import { useState } from 'react';
import { nutrition as nutritionApi } from '../api';

const NUTRIENTS = [
  { key: 'iron',      label: 'Fer',       unit: 'mg',  ajr: 14,  color: '#f85149' },
  { key: 'calcium',   label: 'Calcium',   unit: 'mg',  ajr: 1000, color: '#58a6ff' },
  { key: 'vitamin_b12', label: 'B12',     unit: 'µg',  ajr: 2.4, color: '#3fb950' },
  { key: 'zinc',      label: 'Zinc',      unit: 'mg',  ajr: 11,  color: '#f0883e' },
  { key: 'omega3',    label: 'Oméga-3',   unit: 'g',   ajr: 1.1, color: '#58a6ff' },
  { key: 'vitamin_d', label: 'Vitamine D',unit: 'µg',  ajr: 20,  color: '#f0c27f' },
];

export default function NutritionPage() {
  const [intake, setIntake]       = useState({});
  const [analysis, setAnalysis]   = useState(null);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);

  const analyze = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await nutritionApi.detectDeficiencies({ intake });
      setAnalysis(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-nutrition">
      <div className="page-header">
        <h1 className="page-title"><span className="page-icon">◉</span> Nutrition</h1>
        <p className="page-sub">Suivez vos apports journaliers recommandés (AJR) et détectez les carences fréquentes en alimentation végétale.</p>
      </div>

      <div className="nutr-layout">
        <div className="nutr-input-panel">
          <h3 className="frigo-panel-title">Vos apports du jour</h3>
          <p style={{ color: 'var(--mut)', fontSize: 13, marginBottom: 20 }}>
            Entrez vos apports estimés pour chaque nutriment.
          </p>

          {NUTRIENTS.map(({ key, label, unit, ajr, color }) => (
            <div key={key} className="nutr-row">
              <label className="nutr-row-label">
                <span style={{ color }}>{label}</span>
                <span style={{ color: 'var(--mut)', fontSize: 12 }}>AJR : {ajr} {unit}</span>
              </label>
              <div className="nutr-row-input">
                <input
                  type="number"
                  min={0}
                  step={0.1}
                  placeholder="0"
                  value={intake[key] || ''}
                  onChange={(e) => setIntake((p) => ({ ...p, [key]: parseFloat(e.target.value) || 0 }))}
                  className="search-input"
                  style={{ padding: '8px 12px', fontSize: 14 }}
                />
                <span style={{ color: 'var(--mut)', fontSize: 13 }}>{unit}</span>
              </div>
              <div className="nutr-bar-bg">
                <div
                  className="nutr-bar-fill"
                  style={{
                    width: `${Math.min(100, ((intake[key] || 0) / ajr) * 100)}%`,
                    background: color,
                  }}
                />
              </div>
            </div>
          ))}

          <button className="frigo-search-btn" onClick={analyze} disabled={loading} style={{ marginTop: 20 }}>
            {loading ? 'Analyse…' : 'Analyser mes apports'}
          </button>
        </div>

        <div className="nutr-results">
          {!analysis && !loading && (
            <div className="frigo-empty">
              <div className="frigo-empty-icon" style={{ fontSize: 48 }}>◉</div>
              <p>Renseignez vos apports pour obtenir une analyse personnalisée.</p>
            </div>
          )}
          {error && <div className="state-msg state-msg--error">{error}</div>}
          {analysis && (
            <div className="nutr-analysis">
              <h3>Résultat de l'analyse</h3>
              <pre style={{ color: 'var(--mut)', fontSize: 13, whiteSpace: 'pre-wrap' }}>
                {JSON.stringify(analysis, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
