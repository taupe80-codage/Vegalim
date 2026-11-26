/**
 * RecipeEditor.jsx — Modifier les ingrédients d'une recette sur sa fiche.
 *
 * Remplacer (remplaçants proposés ou recherche), retirer, remettre, ajouter un
 * ingrédient, changer les quantités (saisies pour les portions affichées).
 * La fiche recalcule la version à chaque modification (POST /recettes/{id}/personnaliser)
 * et propose de l'enregistrer.
 */
import { useEffect, useRef, useState } from 'react';
import { ingredients as ingredientsApi, recipeVersions } from '../api';
import { fromDisplayQty, isNumericUnit, rowChanged, toDisplayQty } from '../recipeEdits';

const suggestionsCache = new Map();

function QtyInput({ value, ratio, unit, onCommit, label }) {
  // texte en cours de saisie (« 1, » n'est pas encore un nombre) ; hors saisie,
  // la quantité de la ligne pour les portions affichées
  const [draft, setDraft] = useState(null);
  return (
    <input className="re-qty" type="text" inputMode="decimal" aria-label={label}
      value={draft ?? toDisplayQty(value, ratio)}
      onFocus={() => setDraft(toDisplayQty(value, ratio))}
      onBlur={() => setDraft(null)}
      onChange={(e) => {
        setDraft(e.target.value);
        const q = fromDisplayQty(e.target.value, ratio);
        if (q != null && q <= 10000) onCommit(q, unit);
      }} />
  );
}

function ReplacePanel({ recipeId, iid, onPick, onClose }) {
  const [suggestions, setSuggestions] = useState(iid ? suggestionsCache.get(iid) || null : []);
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const inputRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);
  useEffect(() => {
    if (!iid || suggestionsCache.has(iid)) return undefined;
    let alive = true;
    recipeVersions.replacements(recipeId, iid)
      .then(r => { suggestionsCache.set(iid, r.results || []); if (alive) setSuggestions(r.results || []); })
      .catch(() => { if (alive) setSuggestions([]); });
    return () => { alive = false; };
  }, [recipeId, iid]);
  const term = q.trim();
  useEffect(() => {
    if (term.length < 2) return undefined;
    let alive = true;
    const t = setTimeout(() => {
      ingredientsApi.search(term)
        .then(r => { if (alive) setResults((r.results || []).filter(x => x.id !== iid).slice(0, 10)); })
        .catch(() => { if (alive) setResults([]); });
    }, 250);
    return () => { alive = false; clearTimeout(t); };
  }, [term, iid]);
  const shownResults = term.length < 2 ? [] : results;

  return (
    <div className="re-panel" onKeyDown={(e) => { if (e.key === 'Escape') onClose(); }}>
      {iid && (
        <div className="re-suggest">
          <span className="re-panel-label">Idées de remplacement :</span>
          {suggestions === null
            ? <span className="re-muted">recherche…</span>
            : suggestions.length === 0
              ? <span className="re-muted">aucune idée, cherchez ci-dessous</span>
              : suggestions.map(s => (
                <button key={s.id} type="button" className="re-chip" title={s.reason}
                  onClick={() => onPick(s.id, s.name_fr)}>
                  {s.name_fr}{s.reason === 'version vegan' ? ' 🌿' : ''}
                </button>
              ))}
        </div>
      )}
      <div className="re-search">
        <input ref={inputRef} type="search" value={q} onChange={e => setQ(e.target.value)}
          placeholder={iid ? 'Ou cherchez un ingrédient…' : 'Cherchez l’ingrédient à ajouter…'}
          aria-label="Chercher un ingrédient" />
        <button type="button" className="re-link" onClick={onClose}>Fermer</button>
      </div>
      {shownResults.length > 0 && (
        <ul className="re-results">
          {shownResults.map(r => (
            <li key={r.id}>
              <button type="button" onClick={() => onPick(r.id, r.name_fr)}>{r.name_fr}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * baseComposition : composition de départ (recette ou version vegan) ;
 * edits : { base, rows } ; nameOf(iid) : nom affiché ; onChange(edits).
 */
export default function RecipeEditor({ recipeId, baseComposition, edits, nameOf, ratio, onChange }) {
  const [open, setOpen] = useState(null);           // clé de la ligne dont le panneau est ouvert, ou 'add'
  const [names, setNames] = useState({});           // noms des ingrédients choisis dans la session
  const rows = edits.rows;
  const label = (iid) => {
    const n = names[iid] || nameOf(iid) || '';
    return n.charAt(0).toUpperCase() + n.slice(1);
  };

  const update = (newRows) => onChange({ ...edits, rows: newRows });
  const setRow = (row, patch) => update(rows.map(r => (r === row ? { ...r, ...patch } : r)));
  const pick = (iid, name) => setNames(n => ({ ...n, [iid]: name }));

  // lignes de départ dans l'ordre de la recette (retirées comprises), puis les ajouts
  const lines = baseComposition.map((c, i) => ({ c, i, row: rows.find(r => r.src === i) || null }));
  const added = rows.filter(r => r.src == null);

  const renderRow = (row, key, c) => {
    const numeric = row.quantity != null || (c && isNumericUnit(c.unit)) || row.src == null;
    const unit = row.unit || (c && isNumericUnit(c.unit) ? c.unit : 'g');
    const changed = c ? rowChanged(row, baseComposition) : true;
    return (
      <li key={key} className={`re-row${changed ? ' re-row--changed' : ''}`}>
        <div className="re-line">
          <span className="re-name">
            {label(row.ingredient)}
            {c && row.ingredient !== (c.ingredient || c.ingredient_id) && (
              <span className="re-was"> (au lieu de {label(c.ingredient || c.ingredient_id).toLowerCase()})</span>
            )}
          </span>
          <span className="re-amount">
            {numeric ? (
              <>
                <QtyInput value={row.quantity ?? c?.quantity} ratio={ratio} unit={unit}
                  label={`Quantité de ${label(row.ingredient)}`}
                  onCommit={(q, u) => setRow(row, { quantity: q, unit: u })} />
                <select className="re-unit" value={unit} aria-label="Unité"
                  onChange={e => setRow(row, { unit: e.target.value, quantity: row.quantity ?? c?.quantity ?? 100 })}>
                  <option value="g">g</option>
                  <option value="ml">ml</option>
                </select>
              </>
            ) : <span className="re-muted">{c?.unit || ''}</span>}
          </span>
          <span className="re-actions">
            <button type="button" className="re-btn" onClick={() => setOpen(open === key ? null : key)}
              aria-expanded={open === key}>⇄ Remplacer</button>
            {c && changed && (
              <button type="button" className="re-btn" title="Revenir à l'ingrédient et à la quantité de la recette"
                onClick={() => setRow(row, {
                  ingredient: c.ingredient || c.ingredient_id, quantity: c.quantity ?? null,
                  unit: isNumericUnit(c.unit) ? c.unit : null,
                })}>↺</button>
            )}
            <button type="button" className="re-btn re-btn--remove" aria-label={`Retirer ${label(row.ingredient)}`}
              onClick={() => { update(rows.filter(r => r !== row)); setOpen(null); }}>✕</button>
          </span>
        </div>
        {open === key && (
          <ReplacePanel recipeId={recipeId} iid={row.ingredient} onClose={() => setOpen(null)}
            onPick={(iid, name) => { pick(iid, name); setRow(row, { ingredient: iid }); setOpen(null); }} />
        )}
      </li>
    );
  };

  return (
    <div className="re-editor">
      <p className="re-hint">
        Quantités pour les portions affichées. Nutrition, prix, allergènes et étapes suivent vos modifications.
      </p>
      <ul className="re-list">
        {lines.map(({ c, i, row }) => (row
          ? renderRow(row, `s${i}`, c)
          : (
            <li key={`s${i}`} className="re-row re-row--removed">
              <div className="re-line">
                <span className="re-name"><s>{label(c.ingredient || c.ingredient_id)}</s> <span className="re-was">retiré</span></span>
                <span className="re-actions">
                  <button type="button" className="re-btn"
                    onClick={() => {
                      const back = {
                        src: i, orig: c.ingredient || c.ingredient_id, ingredient: c.ingredient || c.ingredient_id,
                        quantity: c.quantity ?? null, unit: isNumericUnit(c.unit) ? c.unit : null,
                      };
                      // remise à sa place dans l'ordre de la recette
                      const at = rows.findIndex(r => r.src != null && r.src > i);
                      update(at < 0 ? [...rows.filter(r => r.src != null), back, ...added]
                        : [...rows.slice(0, at), back, ...rows.slice(at)]);
                    }}>Remettre</button>
                </span>
              </div>
            </li>
          )))}
        {added.map((row, k) => renderRow(row, `a${k}`, null))}
      </ul>
      {open === 'add'
        ? <ReplacePanel recipeId={recipeId} iid={null} onClose={() => setOpen(null)}
            onPick={(iid, name) => {
              pick(iid, name);
              update([...rows, { src: null, orig: null, ingredient: iid, quantity: fromDisplayQty('100', ratio), unit: 'g' }]);
              setOpen(null);
            }} />
        : <button type="button" className="re-add" onClick={() => setOpen('add')}>+ Ajouter un ingrédient</button>}
    </div>
  );
}
