/**
 * MyRecipesPage.jsx — « Mes recettes proposées » (/mes-recettes).
 *
 * Suivi de chaque proposition : brouillon, en relecture, à corriger (avec le
 * message de l'équipe), publiée (lien vers la fiche) ou refusée (motif).
 */

import { useEffect, useState } from 'react';
import { contributions, apiUrl, photoProposals, recipeVersions } from '../api';
import { useAuth } from '../AuthContext';
import { Link, navigate } from '../Router';
import { useToast } from '../ToastContext';
import { StatusBadge } from '../components/ContributionParts';
import { changeLabel } from '../recipeEdits';

const ORDER = ['changes_requested', 'draft', 'submitted', 'published', 'rejected'];

const PHOTO_STATUS = {
  submitted: { status: 'submitted', label: 'En relecture' },
  approved:  { status: 'published', label: 'Publiée' },
  rejected:  { status: 'rejected',  label: 'Non retenue' },
  replaced:  { status: 'draft',     label: 'Remplacée par une photo plus récente' },
};

/** Photos de plats proposées par le membre (PhotoProposal.jsx sur les fiches). */
function MyPhotos() {
  const toast = useToast();
  const [photos, setPhotos] = useState(null);
  const [confirm, setConfirm] = useState(null);
  useEffect(() => { photoProposals.mine().then(r => setPhotos(r.results || [])).catch(() => setPhotos([])); }, []);
  if (!photos || photos.length === 0) return null;

  const remove = async (p) => {
    if (confirm !== p.id) { setConfirm(p.id); return; }
    try {
      await photoProposals.remove(p.id);
      setPhotos(list => list.filter(x => x.id !== p.id));
      toast(p.status === 'approved' ? 'Photo retirée du site' : 'Photo supprimée');
    } catch (e) {
      toast(e.message || 'Suppression impossible', 'error');
    } finally {
      setConfirm(null);
    }
  };

  return (
    <section aria-labelledby="mr-photos" style={{ marginTop: 32 }}>
      <h2 id="mr-photos" className="ct-card-title">Mes photos de plats</h2>
      <ul className="ct-list">
        {photos.map(p => {
          const st = PHOTO_STATUS[p.status] || PHOTO_STATUS.submitted;
          return (
            <li key={p.id} className="ct-item pp-mine">
              <img src={apiUrl(p.photo_url)} alt={`Votre photo de ${p.recipe_title}`} />
              <div className="ct-item-body">
                <div className="ct-item-head">
                  <h3 className="ct-item-title"><Link to={`/recette/${p.recipe_id}`}>{p.recipe_title}</Link></h3>
                  <span className="ct-badges"><StatusBadge status={st.status} label={st.label} /></span>
                </div>
                <p className="ct-muted ct-item-dates">Envoyée le {formatDate(p.created_at)}</p>
                {p.moderator_note && <blockquote className="ct-modnote"><strong>Message de l'équipe :</strong> {p.moderator_note}</blockquote>}
                <div className="ct-actions">
                  <button type="button" className={`ct-btn ct-btn--sm ${confirm === p.id ? 'ct-btn--danger' : ''}`} onClick={() => remove(p)}
                    onBlur={() => setTimeout(() => setConfirm(c => (c === p.id ? null : c)), 200)}>
                    {confirm === p.id
                      ? (p.status === 'approved' ? 'Confirmer : retirer du site' : 'Confirmer la suppression')
                      : (p.status === 'approved' ? 'Retirer du site' : 'Supprimer')}
                  </button>
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// Recettes du catalogue modifiées et enregistrées (ingrédients, quantités)
function MyVersions() {
  const toast = useToast();
  const [versions, setVersions] = useState(null);
  const [confirm, setConfirm] = useState(null);
  useEffect(() => { recipeVersions.mine().then(r => setVersions(r.results || [])).catch(() => setVersions([])); }, []);
  if (!versions || versions.length === 0) return null;

  const remove = async (v) => {
    if (confirm !== v.recipe_id) { setConfirm(v.recipe_id); return; }
    try {
      await recipeVersions.remove(v.recipe_id);
      setVersions(list => list.filter(x => x.recipe_id !== v.recipe_id));
      toast("Version supprimée : la fiche montre de nouveau la recette d'origine");
    } catch (e) {
      toast(e.message || 'Suppression impossible', 'error');
    } finally {
      setConfirm(null);
    }
  };

  return (
    <section aria-labelledby="mr-versions" style={{ marginTop: 32 }}>
      <h2 id="mr-versions" className="ct-card-title">Mes recettes modifiées</h2>
      <p className="ct-muted">Les fiches s'ouvrent sur votre version ; « Voir l'originale » reste possible.</p>
      <ul className="ct-list">
        {versions.map(v => (
          <li key={v.recipe_id} className="ct-item">
            <div className="ct-item-body">
              <div className="ct-item-head">
                <h3 className="ct-item-title"><Link to={`/recette/${v.recipe_id}`}>{v.title}</Link></h3>
                {v.base === 'vegan' && <span className="ct-badges"><span className="badge">🌿 vegan</span></span>}
              </div>
              <p className="ct-muted ct-item-dates">Modifiée le {formatDate(v.updated_at)}</p>
              {v.changes?.length > 0 && (
                <ul className="mr-version-changes">
                  {v.changes.slice(0, 6).map((ch, i) => <li key={i}>{changeLabel(ch)}</li>)}
                  {v.changes.length > 6 && <li>… et {v.changes.length - 6} autre(s)</li>}
                </ul>
              )}
              <div className="ct-actions">
                <button type="button" className={`ct-btn ct-btn--sm ${confirm === v.recipe_id ? 'ct-btn--danger' : ''}`}
                  onClick={() => remove(v)}
                  onBlur={() => setTimeout(() => setConfirm(c => (c === v.recipe_id ? null : c)), 200)}>
                  {confirm === v.recipe_id ? 'Confirmer la suppression' : 'Supprimer ma version'}
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function formatDate(iso) {
  if (!iso) return '';
  try { return new Date(iso).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' }); }
  catch { return ''; }
}

export default function MyRecipesPage({ onAuthClick }) {
  const { user, loading: authLoading } = useAuth();
  const toast = useToast();
  const [items, setItems]   = useState(null);
  const [error, setError]   = useState('');
  const [confirm, setConfirm] = useState(null);
  const [prefs, setPrefs]   = useState(null);

  const load = () => {
    contributions.mine()
      .then(res => { setError(''); setItems(res.results || []); })
      .catch(e => setError(e.message || 'Chargement impossible'));
  };

  useEffect(() => { if (user) load(); }, [user]);
  useEffect(() => {
    if (user) contributions.preferences().then(setPrefs).catch(() => setPrefs(null));
  }, [user]);

  const toggleEmails = async (on) => {
    try {
      setPrefs(await contributions.setPreferences(on));
      toast(on ? 'E-mails de suivi activés' : 'E-mails de suivi désactivés', 'info');
    } catch (e) { toast(e.message, 'error'); }
  };

  const remove = async (s) => {
    if (confirm !== s.id) { setConfirm(s.id); return; }
    try {
      await contributions.remove(s.id);
      setItems(list => list.filter(x => x.id !== s.id));
      toast(s.status === 'published' ? 'Recette retirée du site' : 'Recette supprimée');
    } catch (e) {
      toast(e.message || 'Suppression impossible', 'error');
    } finally {
      setConfirm(null);
    }
  };

  const header = (
    <header className="page-header">
      <h1 className="page-title"><span className="page-icon" aria-hidden="true">📒</span> Mes recettes proposées</h1>
      <p className="page-sub">Suivez la relecture de vos recettes, reprenez un brouillon ou retirez une recette publiée.</p>
    </header>
  );

  if (authLoading) return <div className="ct-page">{header}</div>;
  if (!user) {
    return (
      <div className="ct-page">
        {header}
        <div className="ct-login-card">
          <p>Connectez-vous pour retrouver vos recettes.</p>
          <button type="button" className="ct-btn ct-btn--primary" onClick={onAuthClick}>Se connecter</button>
        </div>
      </div>
    );
  }

  const sorted = [...(items || [])].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status));

  return (
    <div className="ct-page">
      {header}
      <div className="ct-toolbar">
        <span className="ct-muted">{items ? `${items.length} recette${items.length > 1 ? 's' : ''}` : 'Chargement…'}</span>
        <Link to="/proposer" className="ct-btn ct-btn--primary">+ Proposer une recette</Link>
      </div>
      {prefs && (
        <label className="ct-consent ct-prefs">
          <input type="checkbox" checked={prefs.email_notifications} onChange={e => toggleEmails(e.target.checked)} />
          <span>Me prévenir par e-mail quand l'équipe publie, renvoie ou refuse une de mes recettes ou de mes photos, quand quelqu'un commente l'une d'elles ou répond à mes avis.</span>
        </label>
      )}
      {error && <p className="ct-error" role="alert">{error}</p>}

      {items && items.length === 0 && (
        <div className="ct-empty">
          <p className="ct-empty-icon" aria-hidden="true">🥕</p>
          <p>Vous n'avez pas encore proposé de recette.</p>
          <p className="ct-muted">Un plat vegan ou végétarien que vos proches redemandent ? Partagez-le : il sera relu puis publié sous votre pseudo.</p>
          <Link to="/proposer" className="ct-btn ct-btn--primary">Proposer ma première recette</Link>
        </div>
      )}

      <ul className="ct-list">
        {sorted.map(s => (
          <li key={s.id} className="ct-item">
            <div className="ct-item-thumb">
              {s.photo_url ? <img src={apiUrl(s.photo_url)} alt="" /> : <span aria-hidden="true">🍽️</span>}
            </div>
            <div className="ct-item-body">
              <div className="ct-item-head">
                <h2 className="ct-item-title">{s.title || 'Recette sans titre'}</h2>
                <span className="ct-badges">
                  <StatusBadge status={s.status} label={s.status_label} />
                  {s.revision && <StatusBadge status={s.revision.status === 'changes_requested' ? 'changes_requested' : s.revision.status === 'submitted' ? 'submitted' : 'draft'} label={s.revision.status_label} />}
                </span>
              </div>
              <p className="ct-muted ct-item-dates">
                {s.status === 'published' && s.reviewed_at ? `Publiée le ${formatDate(s.reviewed_at)}`
                  : s.status === 'submitted' && s.submitted_at ? `Envoyée le ${formatDate(s.submitted_at)} — relecture en cours`
                  : `Modifiée le ${formatDate(s.updated_at)}`}
              </p>
              {s.moderator_note && (s.status === 'changes_requested' || s.status === 'rejected' || s.status === 'published')
                && !(s.status === 'published' && s.revision && s.revision.status !== 'changes_requested') && (
                <blockquote className="ct-modnote"><strong>Message de l'équipe :</strong> {s.moderator_note}</blockquote>
              )}
              <div className="ct-actions">
                {s.editable && s.status !== 'published' && (
                  <button type="button" className="ct-btn ct-btn--sm ct-btn--primary" onClick={() => navigate(`/proposer/${s.id}`)}>
                    {s.status === 'changes_requested' ? 'Corriger et renvoyer' : 'Continuer'}
                  </button>
                )}
                {!s.editable && s.status !== 'published' && (
                  <button type="button" className="ct-btn ct-btn--sm" onClick={() => navigate(`/proposer/${s.id}`)}>Voir</button>
                )}
                {s.status === 'published' && s.published_recipe_id && (
                  <Link to={`/recette/${s.published_recipe_id}`} className="ct-btn ct-btn--sm ct-btn--primary">Voir la fiche publiée</Link>
                )}
                {s.status === 'published' && (
                  <button type="button" className="ct-btn ct-btn--sm" onClick={() => navigate(`/proposer/${s.id}`)}>
                    {s.revision?.status === 'submitted' ? 'Voir mes modifications'
                      : s.revision ? 'Reprendre mes modifications' : 'Modifier'}
                  </button>
                )}
                <button type="button" className={`ct-btn ct-btn--sm ${confirm === s.id ? 'ct-btn--danger' : ''}`} onClick={() => remove(s)}
                  onBlur={() => setTimeout(() => setConfirm(c => (c === s.id ? null : c)), 200)}>
                  {confirm === s.id
                    ? (s.status === 'published' ? 'Confirmer : retirer du site' : 'Confirmer la suppression')
                    : (s.status === 'published' ? 'Retirer du site' : 'Supprimer')}
                </button>
              </div>
            </div>
          </li>
        ))}
      </ul>
      <MyPhotos />
      <MyVersions />
    </div>
  );
}
