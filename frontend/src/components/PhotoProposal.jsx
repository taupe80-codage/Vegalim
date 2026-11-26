/**
 * PhotoProposal.jsx — « Proposer une photo » sur la fiche d'un plat du catalogue.
 *
 * Un membre connecté envoie sa photo du plat ; la modération la relit
 * (#/moderation, onglet Photos) avant qu'elle devienne la photo de la recette.
 * Affiche aussi le crédit d'une photo de membre déjà publiée.
 */

import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { photoProposals } from '../api';
import { useAuth } from '../AuthContext';
import { useToast } from '../ToastContext';
import HelpTip from './HelpTip';
import { PHOTO_TYPES, checkPhotoForm } from '../photoForm';


function ProposalModal({ recipe, hasPhoto, onClose, onSent }) {
  const { user } = useAuth();
  const toast = useToast();
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState('');
  const [author, setAuthor] = useState(user?.name || '');
  const [consent, setConsent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');
  const closeRef = useRef(null);

  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e) => { if (e.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  useEffect(() => () => { if (preview) URL.revokeObjectURL(preview); }, [preview]);

  const pick = (f) => {
    setError('');
    setFile(f || null);
    setPreview(f ? URL.createObjectURL(f) : '');
  };

  const send = async () => {
    const problem = checkPhotoForm({ file, author, consent });
    if (problem) { setError(problem); return; }
    setSending(true);
    try {
      const res = await photoProposals.propose(recipe.id, file, author.trim(), consent);
      toast('Merci ! Votre photo sera relue avant publication.');
      onSent(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setSending(false);
    }
  };

  const title = recipe.titles?.fr || recipe.title_fr || 'ce plat';
  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box pp-modal" role="dialog" aria-modal="true" aria-labelledby="pp-title"
        onClick={e => e.stopPropagation()}>
        <button ref={closeRef} type="button" className="modal-close" onClick={onClose} aria-label="Fermer">✕</button>
        <div className="modal-header" style={{ marginBottom: 18 }}>
          <h2 id="pp-title" className="modal-title" style={{ fontSize: 21 }}>
            {hasPhoto ? 'Proposer une autre photo' : 'Proposer une photo'}
          </h2>
          <p className="modal-sub">{title}</p>
        </div>

        <ul className="pp-rules">
          <li>Une photo <strong>prise par vous</strong> de ce plat, tel que vous l'avez cuisiné.</li>
          <li>Sans viande ni poisson, sans personne reconnaissable, sans texte ni filigrane.</li>
          <li>De préférence à la lumière du jour, le plat bien visible.</li>
        </ul>

        <label className="pp-drop">
          <input type="file" accept={PHOTO_TYPES.join(',')} onChange={e => pick(e.target.files?.[0])} />
          {preview
            ? <img src={preview} alt="Aperçu de votre photo" className="pp-preview" />
            : <span>📷 Choisir une photo (JPEG, PNG ou WebP, 8 Mo maximum)</span>}
        </label>

        <div className="form-field" style={{ marginTop: 14 }}>
          <label htmlFor="pp-author">Pseudo affiché sous la photo</label>
          <input id="pp-author" type="text" value={author} maxLength={40}
            onChange={e => setAuthor(e.target.value)} autoComplete="nickname" />
        </div>

        <label className="ct-consent" style={{ marginTop: 14 }}>
          <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />
          <span>
            J'ai pris cette photo moi-même. J'accepte qu'ALIM l'affiche sur la fiche de cette recette, sous mon pseudo,
            après relecture. Je peux la retirer à tout moment depuis « Mes recettes ».
          </span>
        </label>

        {error && <p className="form-error" role="alert" style={{ marginTop: 14 }}>{error}</p>}

        <div className="ct-actions" style={{ marginTop: 18 }}>
          <button type="button" className="ct-btn ct-btn--primary" disabled={sending} onClick={send}>
            {sending ? 'Envoi…' : 'Envoyer la photo'}
          </button>
          <button type="button" className="ct-btn" onClick={onClose}>Annuler</button>
        </div>
      </div>
    </div>,
    document.body,
  );
}

/**
 * Bandeau sous la photo de la fiche : crédit d'un membre, bouton pour proposer
 * une photo, ou rappel qu'une proposition est en relecture.
 */
export default function PhotoProposal({ recipe, hasPhoto, onAuthClick }) {
  const { user } = useAuth();
  const [info, setInfo] = useState(null);
  const [open, setOpen] = useState(false);
  // Recettes proposées par les membres : la photo est celle de leur auteur
  const eligible = !!recipe?.id && !recipe.image_url;

  useEffect(() => {
    if (!eligible) return undefined;
    let alive = true;
    photoProposals.forRecipe(recipe.id).then(r => { if (alive) setInfo(r); }).catch(() => {});
    return () => { alive = false; };
  }, [recipe?.id, eligible, user?.email]);

  if (!eligible) return null;
  const pending = info?.my_pending;

  return (
    <div className="pp-bar">
      {info?.credit && <span className="pp-credit">📷 Photo : {info.credit.author_name}</span>}
      {pending
        ? <span className="pp-pending">Votre photo est en relecture.</span>
        : (
          <span className="pp-cta">
            <button type="button" className="pp-link" onClick={() => (user ? setOpen(true) : onAuthClick?.())}>
              📷 {hasPhoto ? 'Proposer une autre photo' : 'Proposer une photo de ce plat'}
            </button>
            <HelpTip label="Proposer une photo">
              Vous avez cuisiné ce plat ? Envoyez votre photo : après relecture par l'équipe, elle devient la photo
              de la recette, avec votre pseudo. Il faut être connecté.
            </HelpTip>
          </span>
        )}
      {open && (
        <ProposalModal recipe={recipe} hasPhoto={hasPhoto} onClose={() => setOpen(false)}
          onSent={(res) => { setOpen(false); setInfo(i => ({ ...(i || {}), my_pending: res })); }} />
      )}
    </div>
  );
}
