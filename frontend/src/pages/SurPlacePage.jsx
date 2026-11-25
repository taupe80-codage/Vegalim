/**
 * SurPlacePage.jsx — « Sur place » : l'aliment principal qu'on a, et les
 * recettes où il est la vedette (POST /frigo/rapide).
 *
 * Pensé pour le téléphone, hors de chez soi (location, amis, marché) : une
 * ligne de saisie, quelques options de matériel et de temps, des résultats
 * classés par la place que tient l'aliment dans le plat. Ne touche pas au
 * frigo enregistré (« Mon frigo »).
 */
import { useEffect, useState } from 'react';
import { frigo as frigoApi } from '../api';
import { navigate, Link } from '../Router';
import { getRecipeImageUrl } from '../components/RecipeCard';
import HelpTip from '../components/HelpTip';
import { splitFoods } from '../surPlace';

const LAST_KEY = 'alim_surplace_last';
const EXAMPLES = ['courgette', 'pois chiches', 'feta, tomates', 'poireaux', 'œufs', 'champignons'];

function fmtTime(min) {
  if (!min) return null;
  if (min >= 240) return 'la veille';
  return min < 60 ? `${min} min` : `${Math.floor(min / 60)} h ${String(min % 60).padStart(2, '0')}`;
}

function Thumb({ r }) {
  const [failed, setFailed] = useState(false);
  const src = r.image_url || getRecipeImageUrl(r);
  if (!src || failed) return <div className="sp-thumb sp-thumb--empty" aria-hidden="true">🍽️</div>;
  return <img className="sp-thumb" src={src} alt="" loading="lazy" onError={() => setFailed(true)} />;
}

export default function SurPlacePage() {
  const saved = (() => { try { return JSON.parse(sessionStorage.getItem(LAST_KEY) || '{}'); } catch { return {}; } })();
  const [text, setText]       = useState(saved.text || '');
  const [noOven, setNoOven]   = useState(!!saved.noOven);
  const [noBlender, setNoBlender] = useState(!!saved.noBlender);
  const [quick, setQuick]     = useState(!!saved.quick);
  const [res, setRes]         = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const foods = splitFoods(text);

  const search = async (override) => {
    const list = override ? splitFoods(override) : foods;
    if (!list.length) return;
    setLoading(true); setError(null);
    try {
      const data = await frigoApi.rapide({
        ingredients: list, no_oven: noOven, no_blender: noBlender,
        max_time: quick ? 30 : undefined, limit: 40,
      });
      setRes(data);
    } catch (e) {
      setError(e.message || 'Recherche indisponible');
    } finally { setLoading(false); }
  };

  // Options changées : relancer la dernière recherche
  useEffect(() => {
    try { sessionStorage.setItem(LAST_KEY, JSON.stringify({ text, noOven, noBlender, quick })); } catch { /* indisponible */ }
  }, [text, noOven, noBlender, quick]);
  useEffect(() => {
    if (res) search();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noOven, noBlender, quick]);

  const understoodTxt = res ? Object.entries(res.understood || {})
    .map(([label, ids]) => {
      const names = [...new Set(ids.map(i => i.name_fr))];
      return names.length === 1 && names[0].toLowerCase() === label.toLowerCase() ? label : `${label} (${names.join(', ')})`;
    }) : [];

  return (
    <div className="page-surplace">
      <div className="page-header">
        <h1 className="page-title"><span className="page-icon">⚡</span> Sur place</h1>
        <p className="page-sub">
          Pas chez vous ? Dites quel aliment il y a sous la main : voici les recettes où il est la vedette.
          {' '}<Link to="/frigo">Mon frigo complet →</Link>
        </p>
      </div>

      <form className="sp-form" onSubmit={e => { e.preventDefault(); search(); }}>
        <label className="sp-label" htmlFor="sp-input">Il y a…</label>
        <div className="sp-input-row">
          <input id="sp-input" className="sp-input" type="search" enterKeyHint="search" autoComplete="off"
            placeholder="courgette, pois chiches…" value={text} onChange={e => setText(e.target.value)} />
          <button type="submit" className="sp-go" disabled={!foods.length || loading}>
            {loading ? '…' : 'Voir'}
          </button>
        </div>
        {!text && (
          <div className="sp-examples">
            {EXAMPLES.map(ex => (
              <button key={ex} type="button" className="sp-chip" onClick={() => { setText(ex); search(ex); }}>{ex}</button>
            ))}
          </div>
        )}
        <div className="sp-options">
          <label className={`sp-chip sp-chip--toggle${noOven ? ' is-on' : ''}`}>
            <input type="checkbox" checked={noOven} onChange={e => setNoOven(e.target.checked)} /> Sans four
          </label>
          <label className={`sp-chip sp-chip--toggle${noBlender ? ' is-on' : ''}`}>
            <input type="checkbox" checked={noBlender} onChange={e => setNoBlender(e.target.checked)} /> Sans mixeur
          </label>
          <label className={`sp-chip sp-chip--toggle${quick ? ' is-on' : ''}`}>
            <input type="checkbox" checked={quick} onChange={e => setQuick(e.target.checked)} /> Prêt en 30 min
          </label>
          <HelpTip label="Sur place">
            Indiquez l'aliment principal dont vous disposez (un ou plusieurs, séparés par des virgules).
            Les recettes où il tient le plus de place passent en premier : nommé dans le titre, puis
            selon sa part dans le plat (hors sel, huile et épices). Avec plusieurs aliments, celles qui
            les utilisent tous d'abord.
            <br /><br />
            « Autres ingrédients » indique combien de produits il faudra en plus. Votre frigo enregistré
            n'est pas modifié.
          </HelpTip>
        </div>
      </form>

      {error && <div className="state-msg state-msg--error">{error}</div>}

      {res && (
        <div className="sp-results">
          <p className="sp-summary">
            {res.total > 0
              ? <>{res.total} recette{res.total > 1 ? 's' : ''} avec {understoodTxt.join(', ')}</>
              : 'Aucune recette où cet aliment est la vedette avec ces options.'}
            {res.unrecognized?.length > 0 && <span className="sp-unknown"> · pas compris : {res.unrecognized.join(', ')}</span>}
          </p>
          <ul className="sp-list">
            {res.results.map(r => (
              <li key={r.id}>
                <button type="button" className="sp-row" onClick={() => navigate(`/recette/${r.id}`)}>
                  <Thumb r={r} />
                  <span className="sp-row-body">
                    <strong className="sp-row-title">{r.title_fr}</strong>
                    <span className="sp-row-match">
                      {r.matched.map(m => (
                        <span key={m.label} className="sp-share" title={`${m.label} : ${m.share_pct} % du plat (hors basiques)`}>
                          <span className="sp-share-bar"><span style={{ width: `${Math.min(100, m.share_pct)}%` }} /></span>
                          {m.label} {m.share_pct} %
                        </span>
                      ))}
                    </span>
                    <span className="sp-row-meta">
                      {[fmtTime(r.total_time_min),
                        r.n_others === 0 ? 'rien d’autre que des basiques' : `${r.n_others} autre${r.n_others > 1 ? 's' : ''} ingrédient${r.n_others > 1 ? 's' : ''}`,
                        r.needs_oven ? 'four' : null].filter(Boolean).join(' · ')}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
