/**
 * Reviews.jsx — Notes et commentaires des recettes.
 *
 *  - StarDisplay   : étoiles en lecture (moyenne à la demi-étoile près)
 *  - StarInput     : choix d'une note 1-5 (groupe de boutons radio, clavier)
 *  - RatingBadge   : « ★ 4,5 (12) » sur les cartes (notes chargées par lots)
 *  - RecipeReviews : section « Avis » de la fiche recette
 */

import { useEffect, useId, useState } from 'react';
import { reviews as api } from '../api';
import { useAuth } from '../AuthContext';
import { useToast } from '../ToastContext';
import { formatAverage, setRating, useRating } from '../ratings';

const LABELS = ['', 'Décevante', 'Moyenne', 'Bonne', 'Très bonne', 'Excellente'];

export function StarDisplay({ value, size = 16, label }) {
  const pct = Math.max(0, Math.min(100, ((value || 0) / 5) * 100));
  return (
    <span className="rv-stars" style={{ fontSize: size }} role="img"
      aria-label={label || `${formatAverage(value)} sur 5`}>
      <span className="rv-stars-bg" aria-hidden="true">★★★★★</span>
      <span className="rv-stars-fg" aria-hidden="true" style={{ width: `${pct}%` }}>★★★★★</span>
    </span>
  );
}

export function StarInput({ value, onChange }) {
  const name = useId();
  const [hover, setHover] = useState(0);
  const shown = hover || value;
  return (
    <div className="rv-star-input" role="radiogroup" aria-label="Votre note" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map(n => (
        <label key={n} className={n <= shown ? 'is-on' : ''} onMouseEnter={() => setHover(n)}>
          <input type="radio" name={name} value={n} checked={value === n} onChange={() => onChange(n)} />
          <span aria-hidden="true">★</span>
          <span className="sr-only">{n} sur 5 — {LABELS[n]}</span>
        </label>
      ))}
      <span className="rv-star-label" aria-hidden="true">{shown ? LABELS[shown] : 'Choisissez une note'}</span>
    </div>
  );
}

export function RatingBadge({ recipeId }) {
  const r = useRating(recipeId);
  if (!r || !r.count) return null;
  return (
    <span className="recipe-meta-item rv-badge" title={`${formatAverage(r.average)} sur 5 — ${r.count} note${r.count > 1 ? 's' : ''}`}>
      <span aria-hidden="true">★</span>
      <span className="sr-only">Note moyenne </span>{formatAverage(r.average)}
      <span className="rv-badge-count">({r.count})</span>
    </span>
  );
}

function formatDate(iso) {
  try { return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }); }
  catch { return ''; }
}

function ReviewItem({ r, user, reasons, onChange, canReply }) {
  const toast = useToast();
  const [reporting, setReporting] = useState(false);
  const [reason, setReason] = useState('');
  const [replying, setReplying] = useState(false);
  const [replyText, setReplyText] = useState(r.author_reply || '');

  const sendReply = async () => {
    try {
      const res = await api.reply(r.id, replyText);
      onChange({ ...r, author_reply: res.review.author_reply, author_reply_at: res.review.author_reply_at });
      setReplying(false);
      toast('Réponse publiée');
    } catch (e) { toast(e.message, 'error'); }
  };
  const removeReply = async () => {
    try {
      await api.deleteReply(r.id);
      onChange({ ...r, author_reply: '', author_reply_at: null });
      setReplyText('');
    } catch (e) { toast(e.message, 'error'); }
  };

  const helpful = async () => {
    try {
      const res = await api.helpful(r.id);
      onChange({ ...r, helpful_count: res.helpful_count, voted: res.voted });
    } catch (e) { toast(e.message, 'error'); }
  };
  const report = async () => {
    if (!reason) return;
    try {
      const res = await api.report(r.id, reason);
      onChange({ ...r, reported: true, hidden: res.hidden });
      setReporting(false);
      toast('Merci, l\'équipe va regarder cet avis.', 'info');
    } catch (e) { toast(e.message, 'error'); }
  };

  return (
    <li className="rv-item">
      <div className="rv-item-head">
        <StarDisplay value={r.rating} size={14} label={`${r.rating} sur 5`} />
        <strong>{r.author_name}</strong>
        {r.made_it && <span className="rv-made">✓ a réalisé la recette</span>}
        <span className="rv-date">{formatDate(r.created_at)}{r.edited ? ' · modifié' : ''}</span>
      </div>
      <p className="rv-comment">{r.comment}</p>
      <div className="rv-item-actions">
        {!r.is_mine && user && (
          <button type="button" className={`rv-link ${r.voted ? 'is-on' : ''}`} aria-pressed={r.voted} onClick={helpful}>
            👍 Utile{r.helpful_count ? ` (${r.helpful_count})` : ''}
          </button>
        )}
        {(r.is_mine || !user) && r.helpful_count > 0 && (
          <span className="rv-date">{r.helpful_count} personne{r.helpful_count > 1 ? 's ont' : ' a'} trouvé cet avis utile</span>
        )}
        {!r.is_mine && user && !r.reported && !reporting && (
          <button type="button" className="rv-link rv-link--muted" onClick={() => setReporting(true)}>Signaler</button>
        )}
        {r.reported && <span className="rv-date">Signalé</span>}
        {canReply && !replying && (
          <button type="button" className="rv-link" onClick={() => setReplying(true)}>
            {r.author_reply ? 'Modifier ma réponse' : 'Répondre'}
          </button>
        )}
      </div>
      {r.author_reply && !replying && (
        <div className="rv-reply">
          <p className="rv-reply-head">Réponse de l'auteur de la recette
            {r.author_reply_at && <span className="rv-date"> · {formatDate(r.author_reply_at)}</span>}</p>
          <p className="rv-comment">{r.author_reply}</p>
          {canReply && <button type="button" className="rv-link rv-link--muted" onClick={removeReply}>Retirer ma réponse</button>}
        </div>
      )}
      {replying && (
        <div className="rv-reply rv-reply--form">
          <label className="ct-label" htmlFor={`rv-reply-${r.id}`}>Votre réponse à {r.author_name}</label>
          <textarea id={`rv-reply-${r.id}`} className="ct-input" rows={2} maxLength={1000} value={replyText}
            onChange={e => setReplyText(e.target.value)} />
          <div className="ct-actions">
            <button type="button" className="ct-btn ct-btn--sm ct-btn--primary" disabled={replyText.trim().length < 3} onClick={sendReply}>Publier la réponse</button>
            <button type="button" className="ct-btn ct-btn--sm" onClick={() => { setReplying(false); setReplyText(r.author_reply || ''); }}>Annuler</button>
          </div>
        </div>
      )}
      {reporting && (
        <div className="rv-report">
          <label className="sr-only" htmlFor={`rv-reason-${r.id}`}>Motif du signalement</label>
          <select id={`rv-reason-${r.id}`} className="ct-input" value={reason} onChange={e => setReason(e.target.value)}>
            <option value="">Motif du signalement…</option>
            {Object.entries(reasons || {}).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
          <button type="button" className="ct-btn ct-btn--sm" disabled={!reason} onClick={report}>Signaler</button>
          <button type="button" className="ct-btn ct-btn--sm" onClick={() => setReporting(false)}>Annuler</button>
        </div>
      )}
    </li>
  );
}

export function RecipeReviews({ recipeId, onAuthClick }) {
  const { user } = useAuth();
  const toast = useToast();
  const [data, setData]     = useState(null);
  const [sort, setSort]     = useState('helpful');
  const [items, setItems]   = useState([]);
  const [editing, setEditing] = useState(false);
  const [form, setForm]     = useState({ rating: 0, comment: '', made_it: false, author_name: '' });
  const [busy, setBusy]     = useState(false);
  const [error, setError]   = useState('');

  useEffect(() => {
    let alive = true;
    api.forRecipe(recipeId, sort)
      .then(d => {
        if (!alive) return;
        setError('');
        setData(d);
        setItems(d.reviews);
        setRating(recipeId, d.summary);
        const m = d.mine;
        setForm({ rating: m?.rating || 0, comment: m?.comment || '', made_it: !!m?.made_it,
                  author_name: m?.author_name || user?.name || '' });
      })
      .catch(e => { if (alive) setError(e.message || 'Avis indisponibles'); });
    return () => { alive = false; };
  }, [recipeId, sort, user]);

  const more = async () => {
    try {
      const d = await api.forRecipe(recipeId, sort, items.length);
      setItems(list => [...list, ...d.reviews.filter(r => !list.some(x => x.id === r.id))]);
    } catch (e) { toast(e.message, 'error'); }
  };

  const save = async (e) => {
    e.preventDefault();
    if (!form.rating) { toast('Choisissez une note de 1 à 5 étoiles.', 'info'); return; }
    setBusy(true);
    try {
      const res = await api.save(recipeId, form);
      setData(d => ({ ...d, mine: res.review, summary: res.summary }));
      setRating(recipeId, res.summary);
      setItems(list => {
        const others = list.filter(x => !x.is_mine);
        return res.review.comment ? [res.review, ...others] : others;
      });
      setEditing(false);
      toast(data?.mine ? 'Avis modifié' : 'Merci pour votre avis !');
    } catch (err) {
      toast(err.message || 'Avis non enregistré', 'error');
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    setBusy(true);
    try {
      const res = await api.remove(recipeId);
      setData(d => ({ ...d, mine: null, summary: res.summary }));
      setRating(recipeId, res.summary);
      setItems(list => list.filter(x => !x.is_mine));
      setForm(f => ({ ...f, rating: 0, comment: '', made_it: false }));
      setEditing(false);
      toast('Avis retiré');
    } catch (err) { toast(err.message, 'error'); }
    finally { setBusy(false); }
  };

  if (error) return null;           // les avis ne doivent jamais casser la fiche
  if (!data) return <section className="rv-section" aria-busy="true"><h2 className="rv-title">Avis</h2></section>;

  const s = data.summary;
  const showForm = user && data.can_review && (editing || !data.mine);

  return (
    <section className="rv-section" aria-labelledby="rv-title">
      <h2 className="rv-title" id="rv-title">Avis {s.count > 0 && <span className="rv-title-count">({s.count})</span>}</h2>

      <div className="rv-top">
        <div className="rv-summary">
          {s.count > 0 ? (
            <>
              <div className="rv-avg">{formatAverage(s.average)}<span>/5</span></div>
              <StarDisplay value={s.average} size={20} />
              <p className="rv-muted">
                {s.count} note{s.count > 1 ? 's' : ''}
                {s.made_it > 0 && ` · ${s.made_it} l'${s.made_it > 1 ? 'ont' : 'a'} réalisée`}
              </p>
              <ul className="rv-dist" aria-label="Répartition des notes">
                {[5, 4, 3, 2, 1].map(n => {
                  const c = s.distribution[String(n)] || 0;
                  return (
                    <li key={n}>
                      <span>{n} ★</span>
                      <span className="rv-bar" aria-hidden="true"><span style={{ width: `${s.count ? (c / s.count) * 100 : 0}%` }} /></span>
                      <span className="rv-muted">{c}</span>
                    </li>
                  );
                })}
              </ul>
            </>
          ) : (
            <p className="rv-muted">Pas encore de note. Vous l'avez cuisinée ? Dites-nous ce que vous en pensez.</p>
          )}
        </div>

        <div className="rv-mine">
          {!user && (
            <div className="rv-cta">
              <p>Vous avez réalisé cette recette ?</p>
              <button type="button" className="ct-btn ct-btn--primary" onClick={onAuthClick}>Se connecter pour donner son avis</button>
            </div>
          )}
          {user && data.own_recipe && <p className="rv-muted">C'est votre recette : les avis viennent des autres cuisiniers, et vous pouvez leur répondre sous chaque commentaire.</p>}
          {user && data.mine && !editing && (
            <div className="rv-cta">
              <p>Votre avis : <StarDisplay value={data.mine.rating} size={15} label={`${data.mine.rating} sur 5`} />
                {data.mine.hidden && <span className="rv-muted"> (masqué par la modération)</span>}</p>
              {data.mine.comment && <p className="rv-comment">« {data.mine.comment} »</p>}
              <div className="ct-actions">
                <button type="button" className="ct-btn ct-btn--sm" onClick={() => setEditing(true)}>Modifier</button>
                <button type="button" className="ct-btn ct-btn--sm" onClick={remove} disabled={busy}>Retirer</button>
              </div>
            </div>
          )}
          {showForm && (
            <form className="rv-form" onSubmit={save}>
              <h3>{data.mine ? 'Modifier mon avis' : 'Donner mon avis'}</h3>
              <StarInput value={form.rating} onChange={n => setForm(f => ({ ...f, rating: n }))} />
              <label className="ct-consent">
                <input type="checkbox" checked={form.made_it} onChange={e => setForm(f => ({ ...f, made_it: e.target.checked }))} />
                <span>J'ai réalisé cette recette</span>
              </label>
              <label className="ct-label" htmlFor="rv-comment">Commentaire (facultatif)</label>
              <textarea id="rv-comment" className="ct-input" rows={3} maxLength={1000} value={form.comment}
                placeholder="Ce qui vous a plu, vos ajustements (cuisson, épices, variante)…"
                onChange={e => setForm(f => ({ ...f, comment: e.target.value }))} />
              <label className="ct-label" htmlFor="rv-author">Pseudo affiché</label>
              <input id="rv-author" className="ct-input" maxLength={40} value={form.author_name}
                onChange={e => setForm(f => ({ ...f, author_name: e.target.value }))} />
              <div className="ct-actions">
                <button type="submit" className="ct-btn ct-btn--primary" disabled={busy || !form.rating || form.author_name.trim().length < 2}>
                  {data.mine ? 'Enregistrer' : 'Publier mon avis'}
                </button>
                {editing && <button type="button" className="ct-btn" onClick={() => setEditing(false)}>Annuler</button>}
              </div>
            </form>
          )}
        </div>
      </div>

      {data.total > 0 && (
        <div className="rv-list-head">
          <h3>{data.total} commentaire{data.total > 1 ? 's' : ''}</h3>
          <label className="sr-only" htmlFor="rv-sort">Trier les commentaires</label>
          <select id="rv-sort" className="ct-input rv-sort" value={sort} onChange={e => setSort(e.target.value)}>
            <option value="helpful">Les plus utiles</option>
            <option value="recent">Les plus récents</option>
            <option value="high">Meilleures notes</option>
            <option value="low">Notes les plus basses</option>
          </select>
        </div>
      )}
      <ul className="rv-list">
        {items.filter(r => !r.hidden).map(r => (
          <ReviewItem key={r.id} r={r} user={user} reasons={data.report_reasons} canReply={!!user && data.own_recipe}
            onChange={nr => setItems(list => list.map(x => (x.id === nr.id ? nr : x)))} />
        ))}
      </ul>
      {items.length < data.total && (
        <button type="button" className="ct-btn ct-btn--add" onClick={more}>Voir plus de commentaires</button>
      )}
    </section>
  );
}
