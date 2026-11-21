/**
 * ModerationPage.jsx — Relecture des recettes proposées (/moderation).
 *
 * Réservée aux comptes dont l'email figure dans ADMIN_EMAILS. File d'attente
 * par statut (la plus ancienne d'abord), aperçu fidèle, vérifications
 * automatiques, rattachement des ingrédients hors catalogue, puis : publier,
 * demander des corrections, refuser ou retirer une recette publiée.
 */

import { useEffect, useState } from 'react';
import { contributions } from '../api';
import { useAuth } from '../AuthContext';
import { Link } from '../Router';
import { useToast } from '../ToastContext';
import { formFromServer, toPayload } from '../contribution';
import { ChecksPanel, IngredientPicker, RecipePreview, StatusBadge } from '../components/ContributionParts';

const TABS = [
  { value: 'submitted',         label: 'À relire' },
  { value: 'changes_requested', label: 'Renvoyées' },
  { value: 'published',         label: 'Publiées' },
  { value: 'rejected',          label: 'Refusées' },
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
    .then(s => { setSub(s); setForm(formFromServer(s.data)); })
    .catch(e => setError(e.message));

  useEffect(() => { setSub(null); setMessage(''); load(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { contributions.options().then(setOptions).catch(() => {}); }, []);

  if (error) return <p className="ct-error" role="alert">{error}</p>;
  if (!sub || !form) return <p className="ct-muted">Chargement…</p>;

  const a = sub.analysis;
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
        <StatusBadge status={sub.status} label={sub.status_label} />
      </div>

      <div className="ct-layout">
        <div className="ct-main">
          {unmatched.length > 0 && sub.status === 'submitted' && (
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
          <RecipePreview form={form} options={options} photoUrl={sub.photo_url} authorName={sub.author_name} analysis={a} />
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
              {sub.status === 'submitted' && (
                <>
                  <button type="button" className="ct-btn ct-btn--primary" disabled={busy || !a.ready || a.unmatched.length > 0}
                    onClick={() => run(() => contributions.publish(id, message), 'Recette publiée')}>Publier</button>
                  <button type="button" className="ct-btn" disabled={busy || message.trim().length < 10}
                    onClick={() => run(() => contributions.requestChanges(id, message), 'Renvoyée à l\'auteur')}>Demander des corrections</button>
                </>
              )}
              {(sub.status === 'submitted' || sub.status === 'changes_requested') && (
                <button type="button" className="ct-btn ct-btn--danger" disabled={busy || message.trim().length < 10}
                  onClick={() => run(() => contributions.reject(id, message), 'Recette refusée')}>Refuser</button>
              )}
              {sub.status === 'published' && (
                <>
                  <Link to={`/recette/${sub.published_recipe_id}`} className="ct-btn">Voir la fiche</Link>
                  <button type="button" className="ct-btn ct-btn--danger" disabled={busy || message.trim().length < 10}
                    onClick={() => run(() => contributions.unpublish(id, message), 'Recette retirée et renvoyée')}>Retirer et renvoyer à l'auteur</button>
                </>
              )}
            </div>
            {sub.status === 'submitted' && (!a.ready || a.unmatched.length > 0) && (
              <p className="ct-hint">Publication possible une fois les points bloquants levés et les ingrédients rattachés.</p>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}

export default function ModerationPage({ onAuthClick }) {
  const { user, loading: authLoading } = useAuth();
  const [tab, setTab]       = useState('submitted');
  const [data, setData]     = useState(null);
  const [selected, setSelected] = useState(null);
  const [error, setError]   = useState('');

  const load = (status = tab) => {
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
      <p className="page-sub">Relisez les recettes proposées, rattachez les ingrédients hors catalogue, puis publiez ou renvoyez à l'auteur.</p>
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
            {t.label}{data?.counts?.[t.value] ? <span className="ct-count-pill">{data.counts[t.value]}</span> : null}
          </button>
        ))}
      </div>
      {error && <p className="ct-error" role="alert">{error}</p>}
      {data && data.results.length === 0 && <p className="ct-muted ct-empty">Rien à afficher ici.</p>}
      {data && data.results.length > 0 && (
        <div className="ct-mod-layout">
          <ul className="ct-queue" aria-label="Recettes">
            {data.results.map(s => (
              <li key={s.id}>
                <button type="button" className={`ct-queue-item ${selected === s.id ? 'is-on' : ''}`} onClick={() => setSelected(s.id)}>
                  <span className="ct-queue-title">{s.title || 'Sans titre'}</span>
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
