/**
 * BatchSession.jsx — Onglet « Batch cooking » du planning.
 *
 * La semaine planifiée devient une session de préparation du dimanche
 * (POST /planning/batch_session, backend/engine/planning_engine/batch.py) :
 * trempage la veille, cuissons, préparations maison, légumes à tailler, plats
 * entiers au choix ; conservation et part à congeler ou à préparer plus tard.
 * Les cases cochées sont gardées pour la semaine (localStorage).
 */
import { useEffect, useState } from 'react';
import { planning as planningApi } from '../api';
import { navigate } from '../Router';
import HelpTip from './HelpTip';

const DAY_SHORT = { lundi: 'lun.', mardi: 'mar.', mercredi: 'mer.', jeudi: 'jeu.', vendredi: 'ven.', samedi: 'sam.', dimanche: 'dim.' };
const DONE_KEY = 'alim_batch_done';

function fmtMin(min) {
  const m = Math.round(min || 0);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60), r = m % 60;
  return r ? `${h} h ${String(r).padStart(2, '0')}` : `${h} h`;
}
const fmtG = (g) => (g >= 1000 ? `${(Math.round(g / 100) / 10).toLocaleString('fr-FR')} kg` : `${Math.round(g)} g`);
const daysOf = (uses) => [...new Set(uses.map(u => DAY_SHORT[u.day] || u.day))].join(', ');
const lateTxt = (days) => days.map(d => DAY_SHORT[d] || d).join(', ');

function Item({ it, done, onToggle }) {
  const st = it.storage || {};
  // Légumes et herbes : seuls les jours couverts par la session (le reste se
  // taille en milieu de semaine) ; cuissons et préparations : tous les jours,
  // la part des derniers étant congelée
  const uses = it.later_grams > 0 ? it.uses.filter(u => !st.late_days?.includes(u.day)) : it.uses;
  return (
    <li className={`batch-item${done ? ' is-done' : ''}`}>
      <label>
        <input type="checkbox" checked={done} onChange={onToggle} />
        <span className="batch-item-main">
          <strong>{it.name}</strong>
          {it.grams > 0 && <> · {fmtG(it.grams)}{it.kind === 'legume' || it.kind === 'grain' ? ' sec' : ''}</>}
          {it.cooked_grams > 0 && <> → ≈ {fmtG(it.cooked_grams)} cuits</>}
          {it.cook_min > 0 && <span className="batch-meta"> · cuisson {fmtMin(it.cook_min)}{it.soak ? ' (après trempage)' : ''}</span>}
          {it.kind === 'base' && <span className="batch-meta"> · {fmtMin(it.active_min)}{it.passive_min > 0 ? ` + ${fmtMin(it.passive_min)} de repos` : ''}</span>}
        </span>
      </label>
      <div className="batch-item-sub">
        Pour {daysOf(uses)}
        {st.fridge_days > 0 && <> · se garde {st.fridge_days === 1 ? '24 h' : `${st.fridge_days} jours`} au frais</>}
        {it.freeze_grams > 0 && <span className="batch-freeze"> · ❄️ congeler la part de {lateTxt(st.late_days)}</span>}
        {it.later_grams > 0 && <span className="batch-later"> · le reste ({fmtG(it.later_grams)}) en milieu de semaine</span>}
      </div>
    </li>
  );
}

export default function BatchSession({ plan }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [done, setDone] = useState(() => {
    try { return new Set(JSON.parse(localStorage.getItem(DONE_KEY) || '[]')); } catch { return new Set(); }
  });
  const planKey = JSON.stringify(plan || {});

  useEffect(() => {
    let cancelled = false;
    planningApi.batchSession({ plan })
      .then(res => { if (!cancelled) { setData(res); setError(null); } })
      .catch(e => { if (!cancelled) setError(e.message || 'Session indisponible'); });
    return () => { cancelled = true; };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planKey]);

  const toggle = (key) => setDone(s => {
    const n = new Set(s);
    if (n.has(key)) n.delete(key); else n.add(key);
    try { localStorage.setItem(DONE_KEY, JSON.stringify([...n])); } catch { /* indisponible */ }
    return n;
  });

  if (error) return <div className="state-msg">{error}</div>;
  if (!data) return <div className="state-msg">Préparation de la session…</div>;
  const steps = data.steps.filter(s => s.items.length);
  if (!steps.length && !data.dishes.length) return (
    <div className="state-msg">Rien à préparer à l'avance dans ce planning : pas de légumineuses, céréales,
      préparations maison ni légumes à tailler.</div>
  );

  let n = 0;
  return (
    <div className="batch">
      <div className="batch-head">
        <div>
          <div className="batch-kicker">SESSION DU DIMANCHE</div>
          <h3>Batch cooking de la semaine</h3>
          <p className="batch-sub">
            {data.total_min > data.active_min
              ? <>≈ {fmtMin(data.total_min)} en cuisine, dont {fmtMin(data.active_min)} actives</>
              : <>≈ {fmtMin(data.active_min)} de préparation (les cuissons mijotent pendant ce temps)</>}
            {' '}· {data.meals_helped} repas sur {data.meals} avancés. Rien n'oblige à tout faire : cochez ce qui vous sert.
          </p>
        </div>
        <HelpTip label="Batch cooking">
          Le dimanche, on cuit et on prépare d'avance ce qui servira dans la semaine : légumineuses,
          céréales, préparations maison (sauces, pâtes, bouillons…), légumes lavés et taillés. En semaine,
          il ne reste qu'à assembler et réchauffer.
          <br /><br />
          Conservation au réfrigérateur, par prudence : riz cuit 24 h, autres céréales et légumineuses
          4 jours, légumes taillés 3 jours, plats mijotés 3 jours. Au-delà, la part concernée est à congeler
          (ou, pour les légumes, à tailler en milieu de semaine).
        </HelpTip>
      </div>

      {data.eve.length > 0 && (
        <section className="batch-section batch-section--eve">
          <h4>La veille au soir</h4>
          <p className="batch-tip">Faire tremper dans trois fois leur volume d'eau froide :</p>
          <ul className="batch-list">
            {data.eve.map(e => (
              <li key={e.key} className={`batch-item${done.has(`eve:${e.key}`) ? ' is-done' : ''}`}>
                <label>
                  <input type="checkbox" checked={done.has(`eve:${e.key}`)} onChange={() => toggle(`eve:${e.key}`)} />
                  <span className="batch-item-main"><strong>{e.name}</strong> · {fmtG(e.grams)} sec</span>
                </label>
              </li>
            ))}
          </ul>
        </section>
      )}

      {steps.map(s => (
        <section key={s.id} className="batch-section">
          <h4><span className="batch-num">{++n}</span> {s.title}</h4>
          <p className="batch-tip">{s.tip}</p>
          <ul className="batch-list">
            {s.items.map(it => (
              <Item key={it.key} it={it} done={done.has(`${s.id}:${it.key}`)} onToggle={() => toggle(`${s.id}:${it.key}`)} />
            ))}
          </ul>
        </section>
      ))}

      {data.later?.length > 0 && (
        <section className="batch-section">
          <h4>En milieu de semaine</h4>
          <p className="batch-tip">Ces légumes servent après 3 jours : taillez-les mercredi soir, ils resteront frais.</p>
          <ul className="batch-list batch-list--plain">
            {data.later.map(l => (
              <li key={l.key}><strong>{l.name}</strong> · {fmtG(l.grams)} <span className="batch-meta">pour {lateTxt(l.days)}</span></li>
            ))}
          </ul>
        </section>
      )}

      {data.dishes.length > 0 && (
        <section className="batch-section">
          <h4>Au choix : plats entiers à cuisiner d'avance</h4>
          <p className="batch-tip">Soupes, dals, curries et mijotés se réchauffent très bien, souvent meilleurs le lendemain.</p>
          <ul className="batch-list batch-list--plain">
            {data.dishes.map((d, i) => (
              <li key={`${d.id}-${i}`}>
                <button type="button" className="batch-link" onClick={() => navigate(`/recette/${d.id}`)}>{d.title}</button>
                <span className="batch-meta"> · {DAY_SHORT[d.day]} {d.meal} · {d.servings} pers. · </span>
                {d.storage.late_days.length
                  ? <span className="batch-freeze">❄️ à congeler (servi après 3 jours)</span>
                  : <span className="batch-meta">au frais jusqu'au service</span>}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
