/**
 * ContributePage.jsx — « Proposer une recette » (vegan ou végétarienne).
 *
 * Routes : /proposer (nouvelle) et /proposer/:id (reprendre un brouillon).
 *
 * Ce que reprend ce formulaire des sites de recettes qui marchent bien :
 *  - ingrédients structurés (quantité + unité + ingrédient) avec suggestions,
 *    et « coller une liste » qui découpe « 200 g de farine » tout seul ;
 *  - étapes une par une, réordonnables ; astuce du chef à part ;
 *  - enregistrement automatique du brouillon, reprise plus tard ;
 *  - vérifications en direct : régime (vegan tenu ?), allergènes, nutrition
 *    par portion, recettes proches déjà publiées ;
 *  - aperçu fidèle avant l'envoi, relecture par l'équipe, pseudo affiché.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { contributions, apiUrl } from '../api';
import { useAuth } from '../AuthContext';
import { useRouter, Link } from '../Router';
import { useToast } from '../ToastContext';
import {
  DRAFT_STORAGE_KEY, emptyForm, emptyIngredient, formFromServer, toPayload,
  moveItem, sectionStatus, formatMinutes,
} from '../contribution';
import { ChecksPanel, IngredientPicker, RecipePreview, StatusBadge } from '../components/ContributionParts';

const SAVE_DELAY_MS = 1500;
const ANALYSE_DELAY_MS = 800;

function readLocalDraft() {
  try {
    const raw = localStorage.getItem(DRAFT_STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch { return null; }
}
function writeLocalDraft(form) {
  try { localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(form)); } catch { /* stockage indisponible */ }
}
function clearLocalDraft() {
  try { localStorage.removeItem(DRAFT_STORAGE_KEY); } catch { /* stockage indisponible */ }
}

function Field({ id, label, hint, children, counter }) {
  return (
    <div className="ct-field">
      <div className="ct-field-head">
        <label htmlFor={id}>{label}</label>
        {counter}
      </div>
      {children}
      {hint && <p className="ct-hint" id={`${id}-hint`}>{hint}</p>}
    </div>
  );
}

function Segmented({ name, value, options, onChange }) {
  return (
    <div className="ct-segmented" role="radiogroup" aria-label={name}>
      {options.map(o => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          className={value === o.value ? 'is-on' : ''}
          onClick={() => onChange(o.value)}
        >{o.label}</button>
      ))}
    </div>
  );
}

export default function ContributePage({ onAuthClick }) {
  const { user, loading: authLoading } = useAuth();
  const { params, navigate } = useRouter();
  const toast = useToast();
  const routeId = params?.id || null;

  const [options, setOptions]   = useState(null);
  const [form, setForm]         = useState(() => (routeId ? emptyForm() : formFromServer(readLocalDraft())));
  const [subId, setSubId]       = useState(routeId);
  const [sub, setSub]           = useState(null);          // proposition serveur (statut…)
  const [author, setAuthor]     = useState('');
  const [consent, setConsent]   = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [analysing, setAnalysing] = useState(false);
  const [saveState, setSaveState] = useState('idle');      // idle | saving | saved | error
  const [savedAt, setSavedAt]   = useState(null);
  const [loadError, setLoadError] = useState('');
  const [showPaste, setShowPaste] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const [parsing, setParsing]   = useState(false);
  const [preview, setPreview]   = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [photoBusy, setPhotoBusy] = useState(false);

  const dirty = useRef(false);
  const saveTimer = useRef(null);
  const analyseTimer = useRef(null);
  const creating = useRef(null);
  const analyseReq = useRef(0);

  const editable = !sub || sub.editable;
  const isPublished = sub?.status === 'published';
  // photo affichée : celle de la modification en cours, sinon celle en ligne
  const photoUrl = isPublished && sub.revision && 'photo_url' in sub.revision ? sub.revision.photo_url : sub?.photo_url;

  // Listes du formulaire
  useEffect(() => {
    contributions.options().then(setOptions).catch(() => setOptions(null));
  }, []);

  // Pseudo par défaut : nom du compte
  useEffect(() => {
    if (user && !author) setAuthor(user.name || '');
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  // Début de recette saisi avant la connexion : enregistré dès la connexion
  useEffect(() => {
    if (user && !routeId && !subId && readLocalDraft()) {
      dirty.current = true;
      setForm(f => ({ ...f }));
    }
  }, [user]); // eslint-disable-line react-hooks/exhaustive-deps

  // Reprise d'un brouillon (/proposer/:id)
  useEffect(() => {
    if (!routeId || !user) return;
    if (sub && sub.id === routeId) return;
    setLoadError('');
    contributions.get(routeId)
      .then(s => {
        setSub(s);
        setSubId(s.id);
        // recette publiée : on reprend la modification en cours s'il y en a une
        setForm(formFromServer(s.revision?.data || s.data));
        const pseudo = s.revision?.author_name || s.author_name;
        if (pseudo) setAuthor(pseudo);
        dirty.current = false;
      })
      .catch(e => setLoadError(e.message || 'Recette introuvable'));
  }, [routeId, user]); // eslint-disable-line react-hooks/exhaustive-deps

  // Nouvelle proposition : repartir d'un formulaire vide quand on revient sur /proposer
  useEffect(() => {
    if (routeId) return;
    if (subId) { setSubId(null); setSub(null); setForm(emptyForm()); setAnalysis(null); }
  }, [routeId]); // eslint-disable-line react-hooks/exhaustive-deps

  const payload = useMemo(() => toPayload(form), [form]);
  const sections = useMemo(() => sectionStatus(form), [form]);

  // ── Enregistrement automatique ──────────────────────────────────────────────
  // Renvoie la proposition enregistrée (null en cas d'échec)
  const save = useCallback(async () => {
    if (!user || !editable) return null;
    setSaveState('saving');
    try {
      let saved;
      if (!subId) {
        if (!creating.current) {
          creating.current = contributions.create(payload, author);
        }
        saved = await creating.current;
        creating.current = null;
        setSubId(saved.id);
        clearLocalDraft();
        // l'adresse garde le brouillon (rechargement, retour arrière)
        window.history.replaceState(null, '', `#/proposer/${saved.id}`);
      } else {
        saved = await contributions.save(subId, payload, author);
      }
      setSub(saved);
      dirty.current = false;
      setSaveState('saved');
      setSavedAt(new Date());
      return saved;
    } catch (e) {
      creating.current = null;
      setSaveState('error');
      toast(e.message || 'Enregistrement impossible', 'error');
      return null;
    }
  }, [user, editable, subId, payload, author, toast]);

  useEffect(() => {
    if (!dirty.current) return;
    if (!user) { writeLocalDraft(form); return; }
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(save, SAVE_DELAY_MS);
    return () => clearTimeout(saveTimer.current);
  }, [form, author, user, save]);

  // Avertir avant de quitter avec des modifications non enregistrées
  useEffect(() => {
    const h = (e) => { if (dirty.current && user) { e.preventDefault(); e.returnValue = ''; } };
    window.addEventListener('beforeunload', h);
    return () => window.removeEventListener('beforeunload', h);
  }, [user]);

  // ── Analyse en direct ───────────────────────────────────────────────────────
  useEffect(() => {
    if (!user) return;
    const empty = !payload.title && !payload.ingredients.length && !payload.steps.length;
    if (empty) { setAnalysis(null); return; }
    clearTimeout(analyseTimer.current);
    analyseTimer.current = setTimeout(async () => {
      const id = ++analyseReq.current;
      setAnalysing(true);
      try {
        const a = await contributions.analyse(payload, author);
        if (id === analyseReq.current) setAnalysis(a);
      } catch { /* l'analyse est un confort : la saisie continue */ }
      finally { if (id === analyseReq.current) setAnalysing(false); }
    }, ANALYSE_DELAY_MS);
    return () => clearTimeout(analyseTimer.current);
  }, [payload, author, user]);

  // ── Édition ─────────────────────────────────────────────────────────────────
  const update = (patch) => { dirty.current = true; setForm(f => ({ ...f, ...patch })); };
  const setIng = (i, patch) => update({ ingredients: form.ingredients.map((x, k) => (k === i ? { ...x, ...patch } : x)) });
  const setStep = (i, v) => update({ steps: form.steps.map((x, k) => (k === i ? v : x)) });

  const replaceIngredient = (index, substitute) => {
    setIng(index, { ingredient_id: substitute.id, name: substitute.name_fr });
    toast(`Remplacé par ${substitute.name_fr}`, 'info');
  };

  const fieldIssue = (prefix) => analysis?.issues.some(i => i.level === 'blocking' && i.field === prefix);

  const applyPaste = async () => {
    if (!pasteText.trim()) return;
    setParsing(true);
    try {
      const res = await contributions.parse(pasteText);
      const lines = (res.lines || []).map(l => ({
        name: l.candidates?.[0]?.name_fr && l.ingredient_id ? l.candidates[0].name_fr : l.name,
        ingredient_id: l.ingredient_id,
        quantity: l.quantity ?? '',
        unit: l.unit,
        note: l.note || '',
      }));
      if (!lines.length) { toast('Aucun ingrédient reconnu : une ligne par ingrédient.', 'info'); return; }
      const kept = form.ingredients.filter(i => (i.name || '').trim() || i.ingredient_id);
      update({ ingredients: [...kept, ...lines].slice(0, options?.limits?.ingredients_max || 40) });
      const free = lines.filter(l => !l.ingredient_id).length;
      toast(`${lines.length} ingrédient${lines.length > 1 ? 's' : ''} ajouté${lines.length > 1 ? 's' : ''}`
        + (free ? ` — ${free} à préciser` : ''), free ? 'info' : 'success');
      setPasteText('');
      setShowPaste(false);
    } catch (e) {
      toast(e.message || 'Lecture impossible', 'error');
    } finally {
      setParsing(false);
    }
  };

  // ── Photo ───────────────────────────────────────────────────────────────────
  const onPhoto = async (file) => {
    if (!file) return;
    if (file.size > (options?.limits?.photo_max_bytes || 8 * 1024 * 1024)) {
      toast('Photo trop lourde (8 Mo maximum).', 'error');
      return;
    }
    setPhotoBusy(true);
    try {
      const id = subId || (await save())?.id;
      if (!id) throw new Error('Enregistrez d\'abord la recette.');
      const res = await contributions.uploadPhoto(id, file);
      setSub(s => (s?.status === 'published'
        ? { ...s, revision: { ...(s.revision || { status: 'draft', changes: [] }), photo_url: res.photo_url } }
        : { ...(s || {}), photo_url: res.photo_url }));
      toast('Photo ajoutée');
    } catch (e) {
      toast(e.message || 'Photo refusée', 'error');
    } finally {
      setPhotoBusy(false);
    }
  };

  const removePhoto = async () => {
    if (!subId) return;
    try {
      await contributions.deletePhoto(subId);
      setSub(s => (s.status === 'published'
        ? { ...s, revision: { ...(s.revision || { status: 'draft', changes: [] }), photo_url: null } }
        : { ...s, photo_url: null }));
    } catch (e) { toast(e.message, 'error'); }
  };

  const discardRevision = async () => {
    try {
      await contributions.discardRevision(subId);
      const s = await contributions.get(subId);
      setSub(s);
      setForm(formFromServer(s.data));
      if (s.author_name) setAuthor(s.author_name);
      dirty.current = false;
      toast('Modifications abandonnées : la version en ligne est inchangée.', 'info');
    } catch (e) { toast(e.message, 'error'); }
  };

  // ── Envoi ───────────────────────────────────────────────────────────────────
  const submit = async () => {
    setSubmitting(true);
    try {
      clearTimeout(saveTimer.current);
      const saved = (dirty.current || !subId) ? await save() : null;
      const id = saved?.id || subId;
      if (!id) throw new Error('Enregistrement impossible : réessayez.');
      const s = await contributions.submit(id, author, consent);
      setSub(s);
      dirty.current = false;
      toast(isPublished ? 'Vos modifications sont envoyées en relecture.' : 'Merci ! Votre recette est envoyée en relecture.');
      navigate('/mes-recettes');
    } catch (e) {
      toast(e.message || 'Envoi impossible', 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // ── Rendu ───────────────────────────────────────────────────────────────────
  const L = options?.limits || {};
  const canSubmit = editable && analysis?.ready && consent && author.trim().length >= 2 && !submitting;
  const submitHint = !analysis?.ready
    ? 'Complétez les points bloquants signalés à droite.'
    : !consent ? 'Cochez la case de certification.'
    : author.trim().length < 2 ? 'Indiquez votre pseudo.' : '';

  const header = (
    <header className="page-header ct-header">
      <h1 className="page-title"><span className="page-icon" aria-hidden="true">✍</span> Proposer une recette</h1>
      <p className="page-sub">
        Une recette vegan ou végétarienne que vous cuisinez vraiment. L'équipe la relit avant
        de la publier, avec votre pseudo.
      </p>
      <div className="ct-header-links">
        <Link to="/mes-recettes">Mes recettes proposées</Link>
        {user?.is_moderator && <Link to="/moderation">Modération</Link>}
      </div>
    </header>
  );

  if (authLoading) return <div className="ct-page">{header}<p className="ct-muted">Chargement…</p></div>;

  if (!user) {
    return (
      <div className="ct-page">
        {header}
        <div className="ct-login-card">
          <h2>Connectez-vous pour proposer une recette</h2>
          <ul>
            <li>Votre brouillon est enregistré au fur et à mesure : vous le terminez quand vous voulez.</li>
            <li>Régime, allergènes et nutrition sont vérifiés pendant la saisie.</li>
            <li>Vous suivez la relecture et pouvez retirer votre recette à tout moment.</li>
          </ul>
          <button type="button" className="ct-btn ct-btn--primary" onClick={onAuthClick}>Se connecter ou créer un compte</button>
          {readLocalDraft() && <p className="ct-muted">Le début de recette saisi sur cet appareil sera repris après la connexion.</p>}
        </div>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="ct-page">
        {header}
        <p className="ct-error" role="alert">{loadError}</p>
        <Link to="/proposer" className="ct-btn">Commencer une nouvelle recette</Link>
      </div>
    );
  }

  return (
    <div className="ct-page">
      {header}

      {isPublished && (
        <div className="ct-banner ct-banner--published" role="status">
          <StatusBadge status="published" label="Publiée" />
          {sub.revision && <StatusBadge status={sub.revision.status === 'changes_requested' ? 'changes_requested' : 'submitted'} label={sub.revision.status_label} />}
          <span>
            {sub.revision?.status === 'submitted'
              ? 'Vos modifications sont en relecture ; la version en ligne reste affichée en attendant.'
              : 'Vous modifiez une recette publiée : vos changements seront relus avant de remplacer la version en ligne.'}
            {' '}<Link to={`/recette/${sub.published_recipe_id}`}>Voir la version en ligne</Link>
          </span>
          {sub.revision?.changes?.length > 0 && <span className="ct-muted">Modifié : {sub.revision.changes.join(', ')}.</span>}
          {sub.revision && sub.revision.status !== 'submitted' && (
            <button type="button" className="ct-btn ct-btn--sm" onClick={discardRevision}>Abandonner mes modifications</button>
          )}
          {sub.revision?.status === 'changes_requested' && sub.moderator_note && <blockquote className="ct-modnote">{sub.moderator_note}</blockquote>}
        </div>
      )}

      {sub && sub.status !== 'draft' && !isPublished && (
        <div className={`ct-banner ct-banner--${sub.status}`} role="status">
          <StatusBadge status={sub.status} label={sub.status_label} />
          {sub.status === 'changes_requested' && <span>L'équipe vous demande quelques modifications avant publication.</span>}
          {sub.status === 'submitted' && <span>Votre recette est en relecture : elle n'est plus modifiable d'ici là.</span>}
          {sub.status === 'rejected' && <span>Cette recette n'a pas été retenue.</span>}
          {sub.moderator_note && <blockquote className="ct-modnote">{sub.moderator_note}</blockquote>}
        </div>
      )}

      <div className="ct-toolbar">
        <span className={`ct-save ct-save--${saveState}`} aria-live="polite">
          {saveState === 'saving' && 'Enregistrement…'}
          {saveState === 'saved' && savedAt && `${isPublished ? 'Modifications enregistrées' : 'Brouillon enregistré'} à ${savedAt.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}`}
          {saveState === 'error' && 'Non enregistré — nouvel essai à la prochaine modification'}
          {saveState === 'idle' && (isPublished ? 'Version en ligne' : subId ? 'Brouillon' : 'Nouveau brouillon')}
        </span>
        <button type="button" className="ct-btn" onClick={() => setPreview(p => !p)} aria-pressed={preview}>
          {preview ? '✎ Revenir à la saisie' : '👁 Aperçu'}
        </button>
      </div>

      <div className="ct-layout">
        <div className="ct-main">
          {preview ? (
            <RecipePreview form={form} options={options} photoUrl={photoUrl} authorName={author} analysis={analysis} />
          ) : (
            <fieldset className="ct-fieldset" disabled={!editable}>
              {/* 1. L'essentiel */}
              <section className="ct-card" id="ct-essentiel" aria-labelledby="ct-h-essentiel">
                <h2 id="ct-h-essentiel" className="ct-card-title"><span className="ct-num">1</span> L'essentiel</h2>
                <Field id="ct-title" label="Titre" counter={<span className="ct-count">{form.title.length}/{L.title_max || 100}</span>}
                  hint="Le nom du plat et ce qui le distingue : « Curry de pois chiches au lait de coco et épinards ».">
                  <input id="ct-title" className={`ct-input ${fieldIssue('title') ? 'ct-input--invalid' : ''}`} type="text"
                    value={form.title} maxLength={L.title_max || 100} onChange={e => update({ title: e.target.value })}
                    aria-describedby="ct-title-hint" />
                </Field>
                <Field id="ct-desc" label="Présentation (facultatif)" counter={<span className="ct-count">{form.description.length}/{L.description_max || 500}</span>}
                  hint="Deux ou trois phrases : origine, goût, occasion.">
                  <textarea id="ct-desc" className="ct-input" rows={3} value={form.description}
                    maxLength={L.description_max || 500} onChange={e => update({ description: e.target.value })} aria-describedby="ct-desc-hint" />
                </Field>
                <div className="ct-row">
                  <div className="ct-field">
                    <span className="ct-label" id="ct-diet-label">Régime</span>
                    <Segmented name="Régime" value={form.diet}
                      options={[{ value: 'vegetarian', label: '🥚 Végétarien' }, { value: 'vegan', label: '🌱 Vegan' }]}
                      onChange={v => update({ diet: v })} />
                    <p className="ct-hint">Vegan : sans lait, œuf, miel ni aucun produit animal. C'est vérifié ingrédient par ingrédient.</p>
                  </div>
                  <div className="ct-field">
                    <span className="ct-label">Difficulté</span>
                    <Segmented name="Difficulté" value={form.difficulty}
                      options={options?.difficulties || [{ value: 'easy', label: 'Facile' }, { value: 'medium', label: 'Moyen' }, { value: 'hard', label: 'Difficile' }]}
                      onChange={v => update({ difficulty: v })} />
                  </div>
                </div>
                <div className="ct-row">
                  <Field id="ct-dish" label="Type de plat">
                    <select id="ct-dish" className={`ct-input ${fieldIssue('dish_type') ? 'ct-input--invalid' : ''}`} value={form.dish_type} onChange={e => update({ dish_type: e.target.value })}>
                      <option value="">Choisir…</option>
                      {(options?.dish_types || []).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </Field>
                  <Field id="ct-cuisine" label="Cuisine (facultatif)">
                    <select id="ct-cuisine" className="ct-input" value={form.cuisine} onChange={e => update({ cuisine: e.target.value })}>
                      <option value="">Non précisée</option>
                      {(options?.cuisines || []).map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
                    </select>
                  </Field>
                </div>
              </section>

              {/* 2. Ingrédients */}
              <section className="ct-card" id="ct-ingredients" aria-labelledby="ct-h-ingredients">
                <div className="ct-card-head">
                  <h2 id="ct-h-ingredients" className="ct-card-title"><span className="ct-num">2</span> Ingrédients</h2>
                  <button type="button" className="ct-btn ct-btn--sm" onClick={() => setShowPaste(s => !s)} aria-expanded={showPaste}>
                    📋 Coller une liste
                  </button>
                </div>
                <p className="ct-hint">Pour {form.servings || 4} portion{Number(form.servings) > 1 ? 's' : ''}. Choisissez l'ingrédient dans les suggestions : la nutrition et les allergènes en dépendent.</p>

                {showPaste && (
                  <div className="ct-paste">
                    <label htmlFor="ct-paste-text" className="ct-label">Une ligne par ingrédient</label>
                    <textarea id="ct-paste-text" className="ct-input" rows={6} value={pasteText}
                      placeholder={'200 g de lentilles corail\n1 oignon, émincé\n2 c. à soupe d\'huile d\'olive\nsel selon le goût'}
                      onChange={e => setPasteText(e.target.value)} />
                    <div className="ct-actions">
                      <button type="button" className="ct-btn ct-btn--primary ct-btn--sm" onClick={applyPaste} disabled={parsing || !pasteText.trim()}>
                        {parsing ? 'Lecture…' : 'Ajouter ces ingrédients'}
                      </button>
                      <button type="button" className="ct-btn ct-btn--sm" onClick={() => setShowPaste(false)}>Annuler</button>
                    </div>
                  </div>
                )}

                <div className="ct-ings" role="list">
                  <div className="ct-ing ct-ing--head" aria-hidden="true">
                    <span>Quantité</span><span>Unité</span><span>Ingrédient</span><span>Précision</span><span />
                  </div>
                  {form.ingredients.map((ing, i) => {
                    const nonVegan = analysis?.diet.non_vegan_ingredients?.find(x => x.index === i);
                    return (
                      <div className={`ct-ing ${nonVegan && form.diet === 'vegan' ? 'ct-ing--warn' : ''}`} role="listitem" key={i}>
                        <input className={`ct-input ${fieldIssue(`ingredients.${i}`) ? 'ct-input--invalid' : ''}`} type="text" inputMode="decimal"
                          aria-label={`Quantité, ingrédient ${i + 1}`} value={ing.unit === 'to_taste' ? '' : ing.quantity}
                          disabled={ing.unit === 'to_taste'} placeholder={ing.unit === 'to_taste' ? '—' : '200'}
                          onChange={e => setIng(i, { quantity: e.target.value.replace(/[^\d.,/]/g, '') })} />
                        <select className="ct-input" aria-label={`Unité, ingrédient ${i + 1}`} value={ing.unit}
                          onChange={e => setIng(i, { unit: e.target.value })}>
                          {(options?.units || [{ value: 'g', label: 'g' }]).map(u => <option key={u.value} value={u.value}>{u.label}</option>)}
                        </select>
                        <IngredientPicker
                          inputId={`ct-ing-${i}`}
                          value={ing.name}
                          matched={!!ing.ingredient_id}
                          invalid={fieldIssue(`ingredients.${i}`)}
                          onChange={v => setIng(i, { name: v, ingredient_id: null })}
                          onPick={it => setIng(i, { name: it.name_fr, ingredient_id: it.id })}
                        />
                        <input className="ct-input" type="text" aria-label={`Précision, ingrédient ${i + 1}`} value={ing.note}
                          placeholder="émincé, rincé…" maxLength={L.ingredient_note_max || 60}
                          onChange={e => setIng(i, { note: e.target.value })} />
                        <div className="ct-row-tools">
                          <button type="button" className="ct-icon" aria-label={`Monter l'ingrédient ${i + 1}`} disabled={i === 0}
                            onClick={() => update({ ingredients: moveItem(form.ingredients, i, -1) })}>↑</button>
                          <button type="button" className="ct-icon" aria-label={`Descendre l'ingrédient ${i + 1}`} disabled={i === form.ingredients.length - 1}
                            onClick={() => update({ ingredients: moveItem(form.ingredients, i, 1) })}>↓</button>
                          <button type="button" className="ct-icon ct-icon--del" aria-label={`Retirer l'ingrédient ${i + 1}`}
                            onClick={() => update({ ingredients: form.ingredients.length > 1 ? form.ingredients.filter((_, k) => k !== i) : [emptyIngredient()] })}>✕</button>
                        </div>
                        {nonVegan && form.diet === 'vegan' && (
                          <div className="ct-ing-note">
                            Pas vegan.
                            {nonVegan.substitute?.id && (
                              <button type="button" className="ct-link" onClick={() => replaceIngredient(i, nonVegan.substitute)}>
                                Remplacer par {nonVegan.substitute.name_fr}
                              </button>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
                <button type="button" className="ct-btn ct-btn--add" disabled={form.ingredients.length >= (L.ingredients_max || 40)}
                  onClick={() => update({ ingredients: [...form.ingredients, emptyIngredient()] })}>+ Ajouter un ingrédient</button>
              </section>

              {/* 3. Étapes */}
              <section className="ct-card" id="ct-etapes" aria-labelledby="ct-h-etapes">
                <h2 id="ct-h-etapes" className="ct-card-title"><span className="ct-num">3</span> Étapes</h2>
                <p className="ct-hint">Une action par étape, avec les temps et les repères visuels (« jusqu'à ce que l'oignon soit translucide »).</p>
                <ol className="ct-steps">
                  {form.steps.map((s, i) => (
                    <li key={i} className="ct-step">
                      <label htmlFor={`ct-step-${i}`} className="ct-step-num">Étape {i + 1}</label>
                      <textarea id={`ct-step-${i}`} className="ct-input" rows={3} value={s} maxLength={L.step_max || 800}
                        onChange={e => setStep(i, e.target.value)} />
                      <div className="ct-row-tools">
                        <button type="button" className="ct-icon" aria-label={`Monter l'étape ${i + 1}`} disabled={i === 0}
                          onClick={() => update({ steps: moveItem(form.steps, i, -1) })}>↑</button>
                        <button type="button" className="ct-icon" aria-label={`Descendre l'étape ${i + 1}`} disabled={i === form.steps.length - 1}
                          onClick={() => update({ steps: moveItem(form.steps, i, 1) })}>↓</button>
                        <button type="button" className="ct-icon ct-icon--del" aria-label={`Retirer l'étape ${i + 1}`}
                          onClick={() => update({ steps: form.steps.length > 1 ? form.steps.filter((_, k) => k !== i) : [''] })}>✕</button>
                      </div>
                    </li>
                  ))}
                </ol>
                <button type="button" className="ct-btn ct-btn--add" disabled={form.steps.length >= (L.steps_max || 30)}
                  onClick={() => update({ steps: [...form.steps, ''] })}>+ Ajouter une étape</button>
                <Field id="ct-tip" label="Astuce (facultatif)" hint="Variante, conservation, ce qui fait la différence.">
                  <textarea id="ct-tip" className="ct-input" rows={2} value={form.tip} maxLength={L.tip_max || 500}
                    onChange={e => update({ tip: e.target.value })} aria-describedby="ct-tip-hint" />
                </Field>
              </section>

              {/* 4. Temps, portions, photo */}
              <section className="ct-card" id="ct-details" aria-labelledby="ct-h-details">
                <h2 id="ct-h-details" className="ct-card-title"><span className="ct-num">4</span> Temps, portions et photo</h2>
                <div className="ct-row ct-row--4">
                  <Field id="ct-servings" label="Portions">
                    <input id="ct-servings" className="ct-input" type="number" min={1} max={L.servings_max || 24}
                      value={form.servings} onChange={e => update({ servings: e.target.value })} />
                  </Field>
                  <Field id="ct-prep" label="Préparation (min)">
                    <input id="ct-prep" className={`ct-input ${fieldIssue('timing') ? 'ct-input--invalid' : ''}`} type="number" min={0}
                      value={form.prep_min} onChange={e => update({ prep_min: e.target.value })} />
                  </Field>
                  <Field id="ct-cook" label="Cuisson (min)">
                    <input id="ct-cook" className="ct-input" type="number" min={0}
                      value={form.cook_min} onChange={e => update({ cook_min: e.target.value })} />
                  </Field>
                  <Field id="ct-rest" label="Repos (min)">
                    <input id="ct-rest" className="ct-input" type="number" min={0}
                      value={form.rest_min} onChange={e => update({ rest_min: e.target.value })} />
                  </Field>
                </div>
                <p className="ct-hint">Temps total : {formatMinutes((Number(form.prep_min) || 0) + (Number(form.cook_min) || 0) + (Number(form.rest_min) || 0))}</p>

                <div className="ct-photo">
                  {photoUrl ? (
                    <figure className="ct-photo-fig">
                      <img src={apiUrl(photoUrl)} alt="Photo de votre recette" />
                      <button type="button" className="ct-btn ct-btn--sm" onClick={removePhoto}>Retirer la photo</button>
                    </figure>
                  ) : (
                    <label className={`ct-photo-drop ${photoBusy ? 'is-busy' : ''}`}>
                      <input type="file" accept="image/jpeg,image/png,image/webp" onChange={e => onPhoto(e.target.files?.[0])} disabled={photoBusy} />
                      <span className="ct-photo-icon" aria-hidden="true">📷</span>
                      <span>{photoBusy ? 'Envoi de la photo…' : 'Ajouter une photo de votre plat'}</span>
                      <span className="ct-hint">Prise par vous, en lumière naturelle de préférence. JPEG, PNG ou WebP, 8 Mo au plus. Les données de localisation sont retirées.</span>
                    </label>
                  )}
                </div>
              </section>
            </fieldset>
          )}

          {/* 5. Envoi */}
          {editable && (
            <section className="ct-card ct-send" aria-labelledby="ct-h-send">
              <h2 id="ct-h-send" className="ct-card-title"><span className="ct-num">5</span> Envoyer en relecture</h2>
              <Field id="ct-author" label="Nom ou pseudo affiché" hint="Visible sous la recette publiée. Pas d'adresse e-mail.">
                <input id="ct-author" className="ct-input" type="text" value={author} maxLength={L.author_max || 40}
                  onChange={e => { dirty.current = true; setAuthor(e.target.value); }} aria-describedby="ct-author-hint" />
              </Field>
              <label className="ct-consent">
                <input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} />
                <span>
                  Je certifie que cette recette est la mienne (elle n'est pas recopiée d'un livre ou d'un site) et que la photo
                  est de moi. J'accepte qu'ALIM la publie après relecture, éventuellement corrigée, sous mon pseudo. Je peux la
                  retirer à tout moment depuis « Mes recettes » ; supprimer mon compte la retire aussi.
                </span>
              </label>
              <div className="ct-actions">
                <button type="button" className="ct-btn ct-btn--primary" disabled={!canSubmit} onClick={submit}>
                  {submitting ? 'Envoi…' : isPublished ? 'Envoyer mes modifications' : 'Envoyer en relecture'}
                </button>
                <button type="button" className="ct-btn" onClick={() => { setPreview(true); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>Voir l'aperçu</button>
              </div>
              {!canSubmit && submitHint && <p className="ct-hint">{submitHint}</p>}
            </section>
          )}
        </div>

        <aside className="ct-side" aria-label="Vérifications automatiques">
          <ChecksPanel analysis={analysis} loading={analysing} sections={sections} onReplace={editable ? replaceIngredient : null} />
        </aside>
      </div>
    </div>
  );
}
