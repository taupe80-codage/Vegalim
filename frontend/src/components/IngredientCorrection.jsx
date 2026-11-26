/**
 * IngredientCorrection.jsx — « Signaler une erreur » sur une fiche ingrédient.
 *
 * Valeur nutritionnelle (pour 100 g) ou autre information, valeur proposée et
 * source obligatoire (référence + lien). Relue par la modération ; acceptée,
 * elle s'applique par-dessus la base et la fiche la signale.
 */
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { ingredientCorrections } from '../api';
import { useAuth } from '../AuthContext';
import { useToast } from '../ToastContext';
import { checkCorrection } from '../ingredientCorrection';
import { fmt } from '../ingredientSheet';

export default function IngredientCorrection({ ingredient, onClose, onAuthClick }) {
  const { user } = useAuth();
  const toast = useToast();
  const rows = ingredient.nutrition.flatMap(g => g.rows);
  const [field, setField] = useState('protein_g');
  const [value, setValue] = useState('');
  const [sourceRef, setSourceRef] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [comment, setComment] = useState('');
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const closeRef = useRef(null);
  const row = rows.find(r => r.key === field);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  const send = async () => {
    const form = { field, value, sourceRef, sourceUrl, comment, current: row?.value ?? null };
    const problem = checkCorrection(form);
    if (problem) { setError(problem); return; }
    setSending(true);
    try {
      await ingredientCorrections.propose({
        ingredient_id: ingredient.id, field,
        proposed_value: field === 'other' ? null : parseFloat(String(value).replace(',', '.')),
        source_ref: sourceRef.trim(), source_url: sourceUrl.trim() || null, comment: comment.trim() || null,
      });
      toast('Merci ! Votre correction sera relue par l’équipe.', 'success');
      onClose();
    } catch (e) {
      setError(e.message && !e.message.startsWith('[object') ? e.message : 'Envoi impossible : vérifiez le formulaire.');
    } finally {
      setSending(false);
    }
  };

  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box pp-modal" role="dialog" aria-modal="true" aria-labelledby="ic-title"
        onClick={e => e.stopPropagation()} onInput={() => setError('')}>
        <button ref={closeRef} type="button" className="modal-close" onClick={onClose} aria-label="Fermer">✕</button>
        <div className="modal-header" style={{ marginBottom: 14 }}>
          <h2 id="ic-title" className="modal-title" style={{ fontSize: 21 }}>Signaler une erreur</h2>
          <p className="modal-sub">{ingredient.name_fr} — source actuelle : {ingredient.source?.name}{ingredient.source?.id ? `, code ${ingredient.source.id}` : ''}</p>
        </div>

        {!user ? (
          <>
            <p className="ig-muted">Il faut être connecté pour proposer une correction : elle est relue et nous pouvons vous répondre.</p>
            <div className="ct-actions" style={{ marginTop: 16 }}>
              <button type="button" className="ct-btn ct-btn--primary" onClick={() => { onClose(); onAuthClick?.(); }}>Se connecter</button>
              <button type="button" className="ct-btn" onClick={onClose}>Annuler</button>
            </div>
          </>
        ) : (
          <>
            <div className="form-field">
              <label htmlFor="ic-field">Ce qui est faux</label>
              <select id="ic-field" value={field} onChange={e => { setField(e.target.value); setError(''); }}>
                {ingredient.nutrition.map(g => (
                  <optgroup key={g.title} label={g.title}>
                    {g.rows.map(r => <option key={r.key} value={r.key}>{r.label.replace(/^dont /, '— dont ')} ({r.unit})</option>)}
                  </optgroup>
                ))}
                <option value="other">Autre information (nom, allergène, saison, prix…)</option>
              </select>
            </div>

            {field !== 'other' && (
              <div className="ic-values">
                <div className="form-field">
                  <span className="ic-label">Valeur affichée</span>
                  <span className="ic-current">{row?.value == null ? 'non renseignée' : `${fmt(row.value)} ${row.unit}`}</span>
                </div>
                <div className="form-field">
                  <label htmlFor="ic-value">Valeur juste pour 100 g</label>
                  <span className="ic-input-unit">
                    <input id="ic-value" type="text" inputMode="decimal" value={value} onChange={e => setValue(e.target.value)} />
                    <span>{row?.unit}</span>
                  </span>
                </div>
              </div>
            )}

            <div className="form-field">
              <label htmlFor="ic-ref">Source (obligatoire)</label>
              <input id="ic-ref" type="text" maxLength={300} value={sourceRef} onChange={e => setSourceRef(e.target.value)}
                placeholder="Ex. : Table Ciqual 2020, code 20053 ; étiquette de la marque X" />
            </div>
            <div className="form-field">
              <label htmlFor="ic-url">Lien vers la source</label>
              <input id="ic-url" type="url" maxLength={500} value={sourceUrl} onChange={e => setSourceUrl(e.target.value)}
                placeholder="https://…" />
            </div>
            <div className="form-field">
              <label htmlFor="ic-comment">{field === 'other' ? 'Ce qu’il faut corriger (obligatoire)' : 'Commentaire'}</label>
              <textarea id="ic-comment" rows={3} maxLength={1000} value={comment} onChange={e => setComment(e.target.value)} />
            </div>

            {error && <p className="form-error" role="alert">{error}</p>}
            <div className="ct-actions" style={{ marginTop: 14 }}>
              <button type="button" className="ct-btn ct-btn--primary" disabled={sending} onClick={send}>
                {sending ? 'Envoi…' : 'Envoyer la correction'}
              </button>
              <button type="button" className="ct-btn" onClick={onClose}>Annuler</button>
            </div>
          </>
        )}
      </div>
    </div>,
    document.body,
  );
}
