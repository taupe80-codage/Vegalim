/**
 * CookMode.jsx — Mode cuisine : une étape à la fois, en grand, écran allumé.
 *
 * - Étapes une par une (boutons, flèches du clavier, balayage sur mobile).
 * - Ingrédients cochables, quantités ajustées aux portions choisies.
 * - Minuteurs lancés depuis les durées du texte (« ⏱ 25 minutes »), plusieurs
 *   à la fois, qui continuent d'une étape à l'autre ; sonnerie et vibration.
 * - Écran maintenu allumé (Screen Wake Lock) quand le navigateur le permet.
 * - Échap ou ✕ pour quitter ; la page dessous ne défile pas.
 */
import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { findDurations, formatClock } from '../cookTimers';

function StepText({ text, onTimer }) {
  const parts = [];
  let last = 0;
  for (const d of findDurations(text)) {
    if (d.start > last) parts.push(text.slice(last, d.start));
    parts.push(d.long ? (
      <span key={d.start} className="cook-dur cook-dur--long" title="Longue attente : à prévoir à l'avance">
        ⏳ {d.label}
      </span>
    ) : (
      <button key={d.start} type="button" className="cook-dur"
        onClick={() => onTimer(d.seconds, d.label)} aria-label={`Lancer un minuteur de ${d.label}`}>
        ⏱ {d.label}
      </button>
    ));
    last = d.end;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <p className="cook-step-text">{parts}</p>;
}

function beep(ctx) {
  if (!ctx) return;
  try {
    const t0 = ctx.currentTime;
    for (let i = 0; i < 3; i++) {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = 'sine';
      o.frequency.value = 880;
      g.gain.setValueAtTime(0.0001, t0 + i * 0.45);
      g.gain.exponentialRampToValueAtTime(0.35, t0 + i * 0.45 + 0.02);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + i * 0.45 + 0.35);
      o.connect(g).connect(ctx.destination);
      o.start(t0 + i * 0.45);
      o.stop(t0 + i * 0.45 + 0.36);
    }
  } catch { /* son indisponible */ }
}

export default function CookMode({ title, steps, ingredients, servings, recipeServings, onClose }) {
  const [idx, setIdx]         = useState(0);
  const [checked, setChecked] = useState(() => new Set());
  const [showIngr, setShowIngr] = useState(false);       // panneau ingrédients (mobile)
  const [timers, setTimers]   = useState([]);             // {id, label, endsAt, total, done}
  const [now, setNow]         = useState(() => Date.now());
  const [wake, setWake]       = useState('pending');      // on | off | unsupported
  const audioRef  = useRef(null);
  const timersRef = useRef(timers);
  const touchRef  = useRef(null);
  const n = steps.length;
  const last = idx === n - 1;

  useEffect(() => { timersRef.current = timers; }, [timers]);

  // Écran allumé : verrou repris au retour sur l'onglet (le navigateur le lâche)
  useEffect(() => {
    let lock = null;
    let alive = true;
    const acquire = async () => {
      if (!('wakeLock' in navigator)) { if (alive) setWake('unsupported'); return; }
      if (document.visibilityState !== 'visible') return;
      try {
        lock = await navigator.wakeLock.request('screen');
        if (alive) setWake('on');
        lock.addEventListener?.('release', () => { if (alive) setWake('off'); });
      } catch { if (alive) setWake('off'); }
    };
    acquire();
    const onVis = () => { if (document.visibilityState === 'visible') acquire(); };
    document.addEventListener('visibilitychange', onVis);
    return () => {
      alive = false;
      document.removeEventListener('visibilitychange', onVis);
      lock?.release?.().catch(() => {});
    };
  }, []);

  // Page dessous figée ; clavier : ← → pour naviguer, Échap pour quitter
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
      else if (e.key === 'ArrowRight') setIdx(i => Math.min(n - 1, i + 1));
      else if (e.key === 'ArrowLeft') setIdx(i => Math.max(0, i - 1));
    };
    document.addEventListener('keydown', onKey);
    return () => { document.body.style.overflow = prev; document.removeEventListener('keydown', onKey); };
  }, [n, onClose]);

  // Minuteurs : tic toutes les 500 ms tant qu'un minuteur tourne
  useEffect(() => {
    if (!timers.some(t => !t.done)) return undefined;
    const id = setInterval(() => {
      const t = Date.now();
      setNow(t);
      const ended = timersRef.current.filter(x => !x.done && x.endsAt <= t);
      if (ended.length) {
        beep(audioRef.current);
        navigator.vibrate?.([300, 150, 300, 150, 300]);
        setTimers(ts => ts.map(x => (ended.some(e => e.id === x.id) ? { ...x, done: true } : x)));
      }
    }, 500);
    return () => clearInterval(id);
  }, [timers]);

  const startTimer = (seconds, label) => {
    // Le son doit être débloqué par un geste de l'utilisateur : c'est le moment
    try {
      if (!audioRef.current) audioRef.current = new (window.AudioContext || window.webkitAudioContext)();
      audioRef.current.resume?.();
    } catch { /* son indisponible */ }
    const t = Date.now();
    setNow(t);
    setTimers(ts => [...ts, { id: `${t}-${Math.random()}`, label, total: seconds, endsAt: t + seconds * 1000, done: false, step: idx + 1 }]);
  };
  const addMinute = (id) => setTimers(ts => ts.map(x => (x.id === id ? { ...x, endsAt: Math.max(x.endsAt, Date.now()) + 60000, done: false } : x)));
  const removeTimer = (id) => setTimers(ts => ts.filter(x => x.id !== id));

  const toggle = (i) => setChecked(s => { const c = new Set(s); if (c.has(i)) c.delete(i); else c.add(i); return c; });
  const go = (d) => setIdx(i => Math.max(0, Math.min(n - 1, i + d)));

  const onTouchStart = (e) => { touchRef.current = e.touches[0].clientX; };
  const onTouchEnd = (e) => {
    if (touchRef.current == null) return;
    const dx = e.changedTouches[0].clientX - touchRef.current;
    touchRef.current = null;
    if (Math.abs(dx) > 60) go(dx < 0 ? 1 : -1);
  };

  const ingrList = (
    <ul className="cook-ingr-list">
      {ingredients.map((ing, i) => (
        <li key={i}>
          <label className={checked.has(i) ? 'is-done' : ''}>
            <input type="checkbox" checked={checked.has(i)} onChange={() => toggle(i)} />
            <span className="cook-ingr-qty">{ing.qtyStr}</span>
            <span>{ing.name}{ing.stateFr ? ` (${ing.stateFr})` : ''}</span>
          </label>
        </li>
      ))}
    </ul>
  );

  return createPortal(
    <div className="cook-overlay" role="dialog" aria-modal="true" aria-label={`Mode cuisine : ${title}`}>
      <header className="cook-head">
        <div className="cook-head-title">
          <span className="cook-kicker">👨‍🍳 Mode cuisine</span>
          <strong>{title}</strong>
        </div>
        <span className={`cook-wake cook-wake--${wake}`}>
          {wake === 'on' ? '☀️ Écran maintenu allumé'
            : wake === 'unsupported' ? 'Écran : réglez la mise en veille de l\'appareil'
            : wake === 'off' ? 'Écran : veille possible' : ''}
        </span>
        <button type="button" className="cook-close" onClick={onClose} aria-label="Quitter le mode cuisine">✕</button>
      </header>

      <div className="cook-progress" aria-hidden="true">
        <div style={{ width: `${((idx + 1) / n) * 100}%` }} />
      </div>

      <div className="cook-body">
        <aside className={`cook-ingr${showIngr ? ' is-open' : ''}`} aria-label="Ingrédients">
          <h2>Ingrédients <span className="cook-ingr-count">{checked.size}/{ingredients.length}</span></h2>
          {servings !== recipeServings && (
            <p className="cook-note">Quantités pour {servings} portions ; celles des étapes sont pour {recipeServings}.</p>
          )}
          {ingrList}
        </aside>

        <main className="cook-step" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
          <div className="cook-step-num" aria-live="polite">Étape {idx + 1} / {n}</div>
          <StepText text={steps[idx]} onTimer={startTimer} />
          {!last && <p className="cook-next"><span>Ensuite :</span> {steps[idx + 1]}</p>}
        </main>
      </div>

      {timers.length > 0 && (
        <div className="cook-timers" aria-live="polite">
          {timers.map(t => {
            const left = Math.ceil((t.endsAt - now) / 1000);
            return (
              <div key={t.id} className={`cook-timer${t.done ? ' is-done' : ''}`}>
                <span className="cook-timer-label">Étape {t.step} · {t.label}</span>
                <strong className="cook-timer-clock">{t.done ? 'Terminé !' : formatClock(left)}</strong>
                <button type="button" onClick={() => addMinute(t.id)} aria-label="Ajouter une minute">+1 min</button>
                <button type="button" onClick={() => removeTimer(t.id)} aria-label="Arrêter le minuteur">✕</button>
              </div>
            );
          })}
        </div>
      )}

      <footer className="cook-foot">
        <button type="button" className="cook-ingr-toggle" onClick={() => setShowIngr(v => !v)} aria-expanded={showIngr}
          aria-label={`Ingrédients (${checked.size} sur ${ingredients.length} cochés)`}>
          🧾 {checked.size}/{ingredients.length}
        </button>
        <button type="button" className="cook-nav cook-nav--prev" onClick={() => go(-1)} disabled={idx === 0}
          aria-label="Étape précédente">
          ← <span className="cook-nav-lbl">Précédente</span>
        </button>
        {last
          ? <button type="button" className="cook-nav cook-nav--primary" onClick={onClose}>Terminer 🎉</button>
          : <button type="button" className="cook-nav cook-nav--primary" onClick={() => go(1)}>Suivante →</button>}
      </footer>
    </div>,
    document.body,
  );
}

