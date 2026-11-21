/**
 * ContributionParts.jsx — Pièces communes à « Proposer une recette »,
 * « Mes recettes » et « Modération ».
 *
 *  - StatusBadge      : statut d'une proposition
 *  - IngredientPicker : champ ingrédient avec suggestions du catalogue
 *  - ChecksPanel      : vérifications automatiques (régime, nutrition, doublons…)
 *  - RecipePreview    : la recette telle qu'elle sera publiée
 */

import { useEffect, useId, useRef, useState } from 'react';
import { contributions, apiUrl } from '../api';
import { Link } from '../Router';
import { ingredientLine, formatMinutes, STATUS_TONES, toPayload } from '../contribution';

// ── Statut ────────────────────────────────────────────────────────────────────

export function StatusBadge({ status, label }) {
  return (
    <span className={`ct-status ct-status--${STATUS_TONES[status] || 'neutral'}`}>{label || status}</span>
  );
}

// ── Ingrédient avec suggestions ───────────────────────────────────────────────

export function IngredientPicker({ value, matched, onChange, onPick, inputId, invalid }) {
  const [open, setOpen]       = useState(false);
  const [items, setItems]     = useState([]);
  const [blocked, setBlocked] = useState(false);
  const [active, setActive]   = useState(-1);
  const timer = useRef(null);
  const reqId = useRef(0);
  const listId = useId();

  useEffect(() => () => clearTimeout(timer.current), []);

  const lookup = (q) => {
    clearTimeout(timer.current);
    if (!q || q.trim().length < 2) { setItems([]); setBlocked(false); return; }
    timer.current = setTimeout(async () => {
      const id = ++reqId.current;
      try {
        const res = await contributions.suggest(q.trim());
        if (id !== reqId.current) return;
        setItems(res.results || []);
        setBlocked(!!res.non_vegetarian);
        setActive(-1);
        setOpen(true);
      } catch { /* suggestions indisponibles : la saisie libre reste possible */ }
    }, 220);
  };

  const pick = (it) => {
    onPick(it);
    setOpen(false);
    setItems([]);
  };

  const onKeyDown = (e) => {
    if (!open || !items.length) return;
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive(a => Math.min(a + 1, items.length - 1)); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive(a => Math.max(a - 1, 0)); }
    else if (e.key === 'Enter' && active >= 0) { e.preventDefault(); pick(items[active]); }
    else if (e.key === 'Escape') { setOpen(false); }
  };

  return (
    <div className="ct-picker">
      <input
        id={inputId}
        type="text"
        className={`ct-input ${invalid ? 'ct-input--invalid' : ''}`}
        value={value}
        placeholder="ex. pois chiches"
        autoComplete="off"
        role="combobox"
        aria-expanded={open && items.length > 0}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={active >= 0 ? `${listId}-${active}` : undefined}
        onChange={(e) => { onChange(e.target.value); lookup(e.target.value); }}
        onFocus={() => { if (items.length) setOpen(true); }}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
        onKeyDown={onKeyDown}
        maxLength={80}
      />
      <span
        className={`ct-picker-state ${matched ? 'ct-picker-state--ok' : value ? 'ct-picker-state--free' : ''}`}
        title={matched ? 'Ingrédient reconnu : la nutrition le compte' : value ? 'Hors de notre base : choisissez une suggestion si possible' : ''}
        aria-hidden="true"
      >{matched ? '✓' : value ? '?' : ''}</span>
      {open && (items.length > 0 || blocked) && (
        <ul className="ct-suggest" id={listId} role="listbox">
          {blocked && <li className="ct-suggest-blocked">Viande et poisson ne sont pas acceptés.</li>}
          {items.map((it, i) => (
            <li
              key={it.id}
              id={`${listId}-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? 'is-active' : ''}
              onMouseDown={(e) => { e.preventDefault(); pick(it); }}
            >
              <span>{it.name_fr}</span>
              {it.detail && <span className="ct-suggest-detail">{it.detail}</span>}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ── Vérifications automatiques ────────────────────────────────────────────────

const LEVELS = {
  blocking: { icon: '⛔', label: 'À corriger avant l\'envoi' },
  warning:  { icon: '⚠',  label: 'À vérifier' },
  tip:      { icon: '💡', label: 'Conseils' },
};

export function ChecksPanel({ analysis, loading, sections, onReplace, compact = false }) {
  if (!analysis) {
    return (
      <div className="ct-checks">
        <h2 className="ct-checks-title">Vérifications automatiques</h2>
        <p className="ct-muted">{loading ? 'Analyse en cours…' : 'Commencez à remplir la recette : régime, allergènes et nutrition s\'affichent ici.'}</p>
      </div>
    );
  }
  const n = analysis.nutrition || {};
  const groups = ['blocking', 'warning', 'tip']
    .map(level => ({ level, items: analysis.issues.filter(i => i.level === level) }))
    .filter(g => g.items.length);
  const dietOk = analysis.diet.declared !== 'vegan' || analysis.diet.vegan;

  return (
    <div className="ct-checks" aria-live="polite">
      <h2 className="ct-checks-title">
        Vérifications automatiques {loading && <span className="ct-spinner" aria-label="Analyse en cours" />}
      </h2>

      {sections && (
        <ol className="ct-progress">
          {sections.map(s => (
            <li key={s.id} className={s.done ? 'is-done' : ''}>
              <a href={`#ct-${s.id}`} onClick={(e) => { e.preventDefault(); document.getElementById(`ct-${s.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}>
                <span aria-hidden="true">{s.done ? '✓' : '○'}</span> {s.label}
              </a>
            </li>
          ))}
        </ol>
      )}

      <div className={`ct-verdict ${analysis.ready ? 'ct-verdict--ok' : ''}`}>
        {analysis.ready
          ? (compact ? 'Aucun point bloquant' : 'Prête à être envoyée')
          : (compact ? 'Points bloquants à lever' : 'Encore quelques points à compléter')}
      </div>

      <dl className="ct-facts">
        <div>
          <dt>Régime</dt>
          <dd className={dietOk ? '' : 'ct-bad'}>
            {analysis.diet.vegan ? '🌱 Vegan' : '🥚 Végétarien'}
            {!dietOk && ' — pas vegan en l\'état'}
          </dd>
        </div>
        <div>
          <dt>Allergènes</dt>
          <dd>{analysis.allergens.length ? analysis.allergens.join(', ') : 'aucun des 14 allergènes majeurs détecté'}</dd>
        </div>
        <div>
          <dt>Temps total</dt>
          <dd>{formatMinutes(analysis.total_min)}</dd>
        </div>
      </dl>

      {n.calories > 0 && (
        <div className="ct-nutri" aria-label="Valeurs nutritionnelles par portion">
          <div><strong>{Math.round(n.calories)}</strong><span>kcal</span></div>
          <div><strong>{n.protein}</strong><span>g protéines</span></div>
          <div><strong>{n.carbs}</strong><span>g glucides</span></div>
          <div><strong>{n.fat}</strong><span>g lipides</span></div>
          <div><strong>{n.fiber}</strong><span>g fibres</span></div>
          <div><strong>{n.salt}</strong><span>g sel</span></div>
          <p className="ct-muted ct-nutri-note">par portion, calculé depuis les tables CIQUAL{analysis.unmatched.length ? ' — hors ingrédients non reconnus' : ''}</p>
        </div>
      )}

      {groups.map(g => (
        <div key={g.level} className={`ct-issues ct-issues--${g.level}`}>
          <h3><span aria-hidden="true">{LEVELS[g.level].icon}</span> {LEVELS[g.level].label}</h3>
          <ul>
            {g.items.map((it, k) => (
              <li key={k}>
                {it.message}
                {it.ingredients && onReplace && (
                  <div className="ct-replace">
                    {it.ingredients.filter(x => x.substitute?.id).map(x => (
                      <button key={x.index} type="button" className="ct-btn ct-btn--sm" onClick={() => onReplace(x.index, x.substitute)}>
                        Remplacer {x.name} par {x.substitute.name_fr}
                      </button>
                    ))}
                  </div>
                )}
                {it.similar && (
                  <ul className="ct-similar">
                    {it.similar.map(s => (
                      <li key={s.id}><Link to={`/recette/${s.id}`}>{s.title}</Link> <span className="ct-muted">({s.reason})</span></li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        </div>
      ))}
      {!compact && (
        <p className="ct-muted ct-checks-foot">
          Chaque recette est relue par l'équipe avant publication. Les points « à vérifier » n'empêchent pas l'envoi.
        </p>
      )}
    </div>
  );
}

// ── Aperçu ────────────────────────────────────────────────────────────────────

export function RecipePreview({ form, options, photoUrl, authorName, analysis }) {
  const p = toPayload(form);
  const label = (list, v) => (options?.[list] || []).find(o => o.value === v)?.label || '';
  const total = (p.prep_min || 0) + (p.cook_min || 0) + (p.rest_min || 0);
  const vegan = analysis ? analysis.diet.vegan : p.diet === 'vegan';
  return (
    <article className="ct-preview">
      {photoUrl
        ? <img className="ct-preview-photo" src={apiUrl(photoUrl)} alt={`Photo : ${p.title}`} />
        : <div className="ct-preview-photo ct-preview-photo--empty" aria-hidden="true">🍽️</div>}
      <div className="ct-preview-body">
        <h2 className="ct-preview-title">{p.title || 'Titre de la recette'}</h2>
        {authorName && <p className="ct-byline">Proposée par {authorName}</p>}
        <div className="ct-preview-meta">
          <span className="ct-chip ct-chip--diet">{vegan ? '🌱 Vegan' : '🥚 Végétarien'}</span>
          {p.dish_type && <span className="ct-chip">{label('dish_types', p.dish_type)}</span>}
          {p.cuisine && <span className="ct-chip">{label('cuisines', p.cuisine)}</span>}
          <span className="ct-chip">⏱ {formatMinutes(total)}</span>
          <span className="ct-chip">{label('difficulties', p.difficulty)}</span>
          <span className="ct-chip">{p.servings} portion{p.servings > 1 ? 's' : ''}</span>
        </div>
        {p.description && <p className="ct-preview-desc">{p.description}</p>}
        <div className="ct-preview-cols">
          <section>
            <h3>Ingrédients</h3>
            <ul className="ct-preview-ings">
              {p.ingredients.map((i, k) => <li key={k}>{ingredientLine(i)}</li>)}
            </ul>
          </section>
          <section>
            <h3>Préparation</h3>
            <p className="ct-muted ct-preview-times">
              Préparation {formatMinutes(p.prep_min)} · Cuisson {formatMinutes(p.cook_min)}
              {p.rest_min ? ` · Repos ${formatMinutes(p.rest_min)}` : ''}
            </p>
            <ol className="ct-preview-steps">
              {p.steps.map((s, k) => <li key={k}>{s}</li>)}
            </ol>
            {p.tip && <p className="ct-preview-tip"><strong>Astuce :</strong> {p.tip}</p>}
          </section>
        </div>
      </div>
    </article>
  );
}
