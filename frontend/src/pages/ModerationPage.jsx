/**
 * ModerationPage.jsx — Relecture des recettes proposées (/moderation).
 *
 * Réservée aux comptes dont l'email figure dans ADMIN_EMAILS. File d'attente
 * par statut (la plus ancienne d'abord), aperçu fidèle, vérifications
 * automatiques, rattachement des ingrédients hors catalogue, puis : publier,
 * demander des corrections, refuser ou retirer une recette publiée.
 */

import { useEffect, useState } from 'react';
import { apiUrl, contributions, photoProposals, reviews } from '../api';
import { useAuth } from '../AuthContext';
import { Link } from '../Router';
import { useToast } from '../ToastContext';
import { formFromServer, toPayload } from '../contribution';
import { ChecksPanel, IngredientPicker, RecipePreview, StatusBadge } from '../components/ContributionParts';
import { StarDisplay } from '../components/Reviews';

const TABS = [
  { value: 'submitted',         label: 'À relire' },
  { value: 'changes_requested', label: 'Renvoyées' },
  { value: 'published',         label: 'Publiées' },
  { value: 'rejected',          label: 'Refusées' },
  { value: 'reviews:reported',  label: 'Avis signalés' },
  { value: 'reviews:hidden',    label: 'Avis masqués' },
  { value: 'photos:submitted',  label: 'Photos à relire' },
  { value: 'photos:approved',   label: 'Photos publiées' },
];

const TEMPLATES = [
  { label: 'Quantités', text: 'Merci pour votre recette ! Pouvez-vous préciser les quantités de chaque ingrédient (en grammes ou en cuillères) ?' },
  { label: 'Étapes', text: 'Merci ! Les étapes gagneraient à être plus détaillées : temps de cuisson, feu, repères visuels.' },
  { label: 'Vegan', text: 'La recette est annoncée vegan mais contient un ingrédient d\'origine animale : remplacez-le ou annoncez-la végétarienne.' },
  { label: 'Photo', text: 'La photo ne montre pas le plat ou n\'est pas de vous : remplacez-la par une photo de votre réalisation, ou retirez-la.' },
  { label: 'Copie', text: 'Cette recette semble reprise d\'un livre ou d\'un site : nous ne publions que des recettes personnelles.' },
  { label: 'Doublon', text: 'Une recette très proche est déjà publiée : précisez ce qui rend la vôtre différente (ingrédient, technique, origine).' },
];

function Review({ id, onDone }) {
  const toast = useToast();
  const [sub, setSub]       = useState(null);
  const [form, setForm]     = useState(null);
  const [options, setOptions] = useState(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy]     = useState(false);
  const [error, setError]   = useState('');

  const load = () => contributions.review(id)
    .then(s => { setSub(s); setForm(formFromServer(s.is_revision ? s.revision.data : s.data)); })
    .catch(e => setError(e.message));

  useEffect(() => { setSub(null); setMessage(''); load(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { contributions.options().then(setOptions).catch(() => {}); }, []);

  if (error) return <p className="ct-error" role="alert">{error}</p>;
  if (!sub || !form) return <p className="ct-muted">Chargement…</p>;

  const a = sub.analysis;
  const isRevision = !!sub.is_revision;
  const pending = sub.status === 'submitted' || (isRevision && sub.revision?.status === 'submitted');
  const unmatched = form.ingredients.map((ing, i) => ({ ing, i })).filter(x => (x.ing.name || '').trim() && !x.ing.ingredient_id);

  const run = async (fn, okMsg) => {
    setBusy(true);
    try {
      await fn();
      toast(okMsg);
      onDone();
    } catch (e) {
      toast(e.message || 'Action impossible', 'error');
    } finally {
      setBusy(false);
    }
  };

  const mapIngredient = async (i, it) => {
    const next = { ...form, ingredients: form.ingredients.map((x, k) => (k === i ? { ...x, ingredient_id: it.id } : x)) };
    setForm(next);
    try {
      await contributions.modSave(id, toPayload(next));
      await load();
      toast(`« ${form.ingredients[i].name} » rattaché à ${it.name_fr}`, 'info');
    } catch (e) { toast(e.message, 'error'); }
  };

  return (
    <div className="ct-review">
      <div className="ct-review-head">
        <div>
          <h2 className="ct-review-title">{sub.title || 'Sans titre'}</h2>
          <p className="ct-muted">
            Par <strong>{sub.author_name || '—'}</strong> ({sub.user_email})
            {sub.author_published > 0 && ` · ${sub.author_published} recette${sub.author_published > 1 ? 's' : ''} déjà publiée${sub.author_published > 1 ? 's' : ''}`}
          </p>
        </div>
        <span className="ct-badges">
          <StatusBadge status={sub.status} label={sub.status_label} />
          {sub.revision && <StatusBadge status={sub.revision.status === 'changes_requested' ? 'changes_requested' : 'submitted'} label={sub.revision.status_label} />}
        </span>
      </div>
      {isRevision && (
        <div className="ct-banner ct-banner--changes_requested">
          <span>
            Modification d'une recette publiée
            {sub.revision.changes?.length > 0 && <> — modifié : <strong>{sub.revision.changes.join(', ')}</strong></>}.
            {' '}La version en ligne reste affichée tant que vous ne publiez pas.
          </span>
          <Link to={`/recette/${sub.published_recipe_id}`}>Comparer avec la version en ligne</Link>
        </div>
      )}

      <div className="ct-layout">
        <div className="ct-main">
          {unmatched.length > 0 && pending && (
            <section className="ct-card ct-card--warn">
              <h3 className="ct-card-title">Ingrédients à rattacher au catalogue</h3>
              <p className="ct-hint">La publication attend que chaque ingrédient soit reconnu (nutrition, allergènes, régime).</p>
              {unmatched.map(({ ing, i }) => (
                <div key={i} className="ct-map-row">
                  <span className="ct-map-name">« {ing.name} »</span>
                  <IngredientPicker
                    inputId={`ct-map-${i}`}
                    value={ing._search ?? ing.name}
                    matched={false}
                    onChange={v => setForm(f => ({ ...f, ingredients: f.ingredients.map((x, k) => (k === i ? { ...x, _search: v } : x)) }))}
                    onPick={it => mapIngredient(i, it)}
                  />
                </div>
              ))}
            </section>
          )}
          <RecipePreview form={form} options={options}
            photoUrl={isRevision ? sub.revision.photo_url : sub.photo_url}
            authorName={isRevision ? sub.revision.author_name : sub.author_name} analysis={a} />
        </div>
        <aside className="ct-side">
          <ChecksPanel analysis={a} compact />
          <section className="ct-card ct-decision">
            <h3 className="ct-card-title">Décision</h3>
            <label htmlFor="ct-mod-msg" className="ct-label">Message à l'auteur</label>
            <div className="ct-templates">
              {TEMPLATES.map(t => (
                <button key={t.label} type="button" className="ct-btn ct-btn--sm" onClick={() => setMessage(t.text)}>{t.label}</button>
              ))}
            </div>
            <textarea id="ct-mod-msg" className="ct-input" rows={4} value={message} maxLength={1500}
              placeholder="Obligatoire pour renvoyer ou refuser ; facultatif pour publier (mot de remerciement)."
              onChange={e => setMessage(e.target.value)} />
            <div className="ct-actions ct-actions--col">
              {pending && (
                <>
                  <button type="button" className="ct-btn ct-btn--primary" disabled={busy || !a.ready || a.unmatched.length > 0}
                    onClick={() => run(() => contributions.publish(id, message), isRevision ? 'Modification publiée' : 'Recette publiée')}>
                    {isRevision ? 'Publier la modification' : 'Publier'}
                  </button>
                  <button type="button" className="ct-btn" disabled={busy || message.trim().length < 10}
                    onClick={() => run(() => contributions.requestChanges(id, message), 'Renvoyée à l\'auteur')}>Demander des corrections</button>
                </>
              )}
              {(pending || sub.status === 'changes_requested' || sub.revision?.status === 'changes_requested') && (
                <button type="button" className="ct-btn ct-btn--danger" disabled={busy || message.trim().length < 10}
                  onClick={() => run(() => contributions.reject(id, message), isRevision ? 'Modification refusée' : 'Recette refusée')}>
                  {isRevision ? 'Refuser la modification' : 'Refuser'}
                </button>
              )}
              {sub.status === 'published' && !pending && (
                <>
                  <Link to={`/recette/${sub.published_recipe_id}`} className="ct-btn">Voir la fiche</Link>
                  <button type="button" className="ct-btn ct-btn--danger" disabled={busy || message.trim().length < 10}
                    onClick={() => run(() => contributions.unpublish(id, message), 'Recette retirée et renvoyée')}>Retirer et renvoyer à l'auteur</button>
                </>
              )}
            </div>
            {pending && (!a.ready || a.unmatched.length > 0) && (
              <p className="ct-hint">Publication possible une fois les points bloquants levés et les ingrédients rattachés.</p>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}

function ReviewModeration({ status }) {
  const toast = useToast();
  const [data, setData] = useState(null);
  const load = () => reviews.modList(status).then(setData).catch(e => toast(e.message, 'error'));
  useEffect(() => { load(); }, [status]); // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (fn, msg) => {
    try { await fn(); toast(msg); load(); } catch (e) { toast(e.message, 'error'); }
  };
  if (!data) return <p className="ct-muted">Chargement…</p>;
  if (!data.results.length) return <p className="ct-muted ct-empty">Rien à afficher ici.</p>;
  return (
    <ul className="ct-list">
      {data.results.map(r => (
        <li key={r.id} className="ct-review-card">
          <div className="rv-item-head">
            <StarDisplay value={r.rating} size={14} label={`${r.rating} sur 5`} />
            <strong>{r.author_name}</strong>
            <span className="rv-date">({r.user_email}) · {new Date(r.created_at).toLocaleDateString('fr-FR')}</span>
          </div>
          <p className="ct-muted">Sur <Link to={`/recette/${r.recipe_id}`}>{r.recipe_title}</Link></p>
          <p className="rv-comment">{r.comment || <em>(note sans commentaire)</em>}</p>
          {r.author_reply && (
            <div className="rv-reply">
              <p className="rv-reply-head">Réponse de l'auteur de la recette</p>
              <p className="rv-comment">{r.author_reply}</p>
              <button type="button" className="rv-link rv-link--muted" onClick={() => act(() => reviews.modDeleteReply(r.id), 'Réponse retirée')}>Retirer la réponse</button>
            </div>
          )}
          {r.report_count > 0 && (
            <p className="ct-muted">
              {r.report_count} signalement{r.report_count > 1 ? 's' : ''} : {Object.entries(r.reasons).map(([k, v]) => `${k} (${v})`).join(', ')}
            </p>
          )}
          <div className="ct-actions">
            {status === 'reported'
              ? <button type="button" className="ct-btn ct-btn--sm" onClick={() => act(() => reviews.modHide(r.id), 'Avis masqué')}>Masquer</button>
              : null}
            <button type="button" className="ct-btn ct-btn--sm" onClick={() => act(() => reviews.modRestore(r.id), 'Avis rétabli')}>
              {status === 'reported' ? 'Garder (ignorer les signalements)' : 'Rétablir'}
            </button>
            <button type="button" className="ct-btn ct-btn--sm ct-btn--danger" onClick={() => act(() => reviews.modDelete(r.id), 'Avis supprimé')}>Supprimer</button>
          </div>
        </li>
      ))}
    </ul>
  );
}

function PhotoModeration({ status, onChange }) {
  const toast = useToast();
  const [data, setData] = useState(null);
  const [notes, setNotes] = useState({});
  const load = () => photoProposals.queue(status).then(setData).catch(e => toast(e.message, 'error'));
  useEffect(() => { load(); }, [status]); // eslint-disable-line react-hooks/exhaustive-deps
  const act = async (fn, msg) => {
    try { await fn(); toast(msg); load(); onChange?.(); } catch (e) { toast(e.message, 'error'); }
  };
  if (!data) return <p className="ct-muted">Chargement…</p>;
  if (!data.results.length) return <p className="ct-muted ct-empty">Rien à afficher ici.</p>;
  return (
    <ul className="ct-list">
      {data.results.map(p => {
        const note = notes[p.id] || '';
        const setNote = (v) => setNotes(n => ({ ...n, [p.id]: v }));
        return (
          <li key={p.id} className="ct-review-card">
            <div className="rv-item-head">
              <strong>{p.author_name}</strong>
              <span className="rv-date">({p.user_email || 'compte supprimé'}) · {new Date(p.created_at).toLocaleDateString('fr-FR')}</span>
            </div>
            <p className="ct-muted">Pour <Link to={`/recette/${p.recipe_id}`}>{p.recipe_title}</Link></p>
            <div className="pp-mod-photos">
              <figure>
                <a href={apiUrl(p.photo_url)} target="_blank" rel="noreferrer"><img src={apiUrl(p.photo_url)} alt={`Photo proposée pour ${p.recipe_title}`} /></a>
                <figcaption>{status === 'approved' ? 'Photo publiée' : 'Photo proposée'}</figcaption>
              </figure>
              {status === 'submitted' && (
                <figure>
                  {p.current_photo_url
                    ? <img src={apiUrl(p.current_photo_url)} alt={`Photo actuelle de ${p.recipe_title}`} />
                    : <div className="pp-none ct-muted">Pas de photo</div>}
                  <figcaption>{p.current_is_member_photo ? "Photo actuelle (d'un membre)" : 'Photo actuelle'}</figcaption>
                </figure>
              )}
            </div>
            <p className="ct-muted">Vérifier : c'est bien ce plat, sans viande ni poisson, sans personne reconnaissable, sans texte ni filigrane.</p>
            <label className="ct-label" htmlFor={`pp-note-${p.id}`}>Message au membre {status === 'submitted' ? '(obligatoire pour refuser)' : '(obligatoire pour retirer)'}</label>
            <textarea id={`pp-note-${p.id}`} className="ct-input" rows={2} value={note} maxLength={1500}
              onChange={e => setNote(e.target.value)} />
            <div className="ct-actions">
              {status === 'submitted' ? (
                <>
                  <button type="button" className="ct-btn ct-btn--sm ct-btn--primary"
                    onClick={() => act(() => photoProposals.approve(p.id, note), 'Photo publiée')}>
                    {p.current_photo_url ? 'Publier (remplace la photo actuelle)' : 'Publier'}
                  </button>
                  <button type="button" className="ct-btn ct-btn--sm ct-btn--danger"
                    onClick={() => act(() => photoProposals.reject(p.id, note), 'Photo refusée')}>Refuser</button>
                </>
              ) : (
                <button type="button" className="ct-btn ct-btn--sm ct-btn--danger"
                  onClick={() => act(() => photoProposals.unpublish(p.id, note), 'Photo retirée')}>Retirer du site</button>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export default function ModerationPage({ onAuthClick }) {
  const { user, loading: authLoading } = useAuth();
  const [tab, setTab]       = useState('submitted');
  const [data, setData]     = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError]   = useState('');

  const reviewTab = tab.startsWith('reviews:');
  const photoTab = tab.startsWith('photos:');
  const otherTab = reviewTab || photoTab;
  const [reviewCounts, setReviewCounts] = useState(null);
  const [photoCounts, setPhotoCounts] = useState(null);
  const loadPhotoCounts = () => photoProposals.queue('submitted').then(r => setPhotoCounts(r.counts)).catch(() => {});

  const load = (status = tab) => {
    reviews.modList('reported').then(r => setReviewCounts(r.counts)).catch(() => {});
    loadPhotoCounts();
    if (status.startsWith('reviews:') || status.startsWith('photos:')) return;
    contributions.queue(status)
      .then(res => {
        setError('');
        setData(res);
        if (!res.results.some(r => r.id === selected)) setSelected(res.results[0]?.id || null);
      })
      .catch(e => setError(e.message));
  };

  useEffect(() => { if (user?.is_moderator) load(tab); }, [user, tab]); // eslint-disable-line react-hooks/exhaustive-deps

  const header = (
    <header className="page-header">
      <h1 className="page-title"><span className="page-icon" aria-hidden="true">🛡</span> Modération des recettes</h1>
      <p className="page-sub">Relisez les recettes proposées et leurs modifications, rattachez les ingrédients hors catalogue, puis publiez ou renvoyez à l'auteur. Les avis signalés et les photos de plats proposées par les membres arrivent aussi ici.</p>
    </header>
  );

  if (authLoading) return <div className="ct-page">{header}</div>;
  if (!user) {
    return <div className="ct-page">{header}<button type="button" className="ct-btn ct-btn--primary" onClick={onAuthClick}>Se connecter</button></div>;
  }
  if (!user.is_moderator) {
    return <div className="ct-page">{header}<p className="ct-error" role="alert">Cette page est réservée à l'équipe de modération.</p></div>;
  }

  return (
    <div className="ct-page ct-page--wide">
      {header}
      <div className="ct-tabs" role="tablist" aria-label="Statut">
        {TABS.map(t => (
          <button key={t.value} type="button" role="tab" aria-selected={tab === t.value}
            className={tab === t.value ? 'is-on' : ''} onClick={() => { setTab(t.value); setSelected(null); }}>
            {t.label}
            {(() => {
              const n = t.value.startsWith('reviews:') ? reviewCounts?.[t.value.slice(8)]
                : t.value.startsWith('photos:') ? photoCounts?.[t.value.slice(7)] : data?.counts?.[t.value];
              return n ? <span className="ct-count-pill">{n}</span> : null;
            })()}
          </button>
        ))}
      </div>
      {error && <p className="ct-error" role="alert">{error}</p>}
      {reviewTab && <ReviewModeration status={tab.slice(8)} />}
      {photoTab && <PhotoModeration status={tab.slice(7)} onChange={loadPhotoCounts} />}
      {!otherTab && data && data.results.length === 0 && <p className="ct-muted ct-empty">Rien à afficher ici.</p>}
      {!otherTab && data && data.results.length > 0 && (
        <div className="ct-mod-layout">
          <ul className="ct-queue" aria-label="Recettes">
            {data.results.map(s => (
              <li key={s.id}>
                <button type="button" className={`ct-queue-item ${selected === s.id ? 'is-on' : ''}`} onClick={() => setSelected(s.id)}>
                  <span className="ct-queue-title">{s.title || 'Sans titre'}</span>
                  {s.is_revision && <span className="ct-chip">Modification</span>}
                  <span className="ct-muted">{s.author_name || '—'} · {new Date(s.submitted_at || s.updated_at).toLocaleDateString('fr-FR')}</span>
                </button>
              </li>
            ))}
          </ul>
          <div>{selected && <Review id={selected} onDone={() => load(tab)} />}</div>
        </div>
      )}
    </div>
  );
}
