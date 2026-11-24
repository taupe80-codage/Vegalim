/**
 * HelpTip.jsx — Bouton (?) qui ouvre une bulle d'explication.
 *
 * Au clic (et donc au toucher sur mobile), pas au survol seul ; se ferme avec
 * Échap, un clic ailleurs ou un second clic ; suit le bouton au défilement. Accessible :
 * aria-expanded, aria-controls, bulle role="note".
 *
 * La bulle est rendue dans <body> (portail) en position fixe : dans un panneau
 * à défilement (colonne du planning), elle était coupée par le conteneur.
 *
 *   <HelpTip label="Anti-gaspillage">Texte d'aide…</HelpTip>
 */
import { useEffect, useId, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';

const GAP = 6;      // écart bouton ↔ bulle (px)
const MARGIN = 16;  // marge au bord de l'écran (px)

/**
 * Place la bulle sous le bouton, alignée sur son bord droit et gardée dans
 * l'écran ; au-dessus s'il n'y a pas la place en dessous. Placement direct par
 * le style (pas d'état React mis à jour dans un effet). Renvoie false si le
 * bouton est sorti de l'écran.
 */
function placeBubble(btn, el) {
  if (!btn || !el) return true;
  const b = btn.getBoundingClientRect();
  const vw = window.innerWidth, vh = window.innerHeight;
  if (b.bottom < 0 || b.top > vh) return false;
  const w = el.offsetWidth, h = el.offsetHeight;
  const left = Math.max(MARGIN, Math.min(b.right - w, vw - w - MARGIN));
  const below = b.bottom + GAP;
  const top = below + h > vh - MARGIN && b.top - GAP - h > MARGIN ? b.top - GAP - h : below;
  el.style.left = `${left}px`;
  el.style.top = `${top}px`;
  el.style.visibility = 'visible';
  return true;
}

export default function HelpTip({ label, children }) {
  const [open, setOpen] = useState(false);
  const btnRef    = useRef(null);
  const bubbleRef = useRef(null);
  const id = useId();

  useLayoutEffect(() => {
    if (open) placeBubble(btnRef.current, bubbleRef.current);
  }, [open]);

  useEffect(() => {
    if (!open) return undefined;
    // défilement ou redimensionnement : la bulle suit le bouton (fermée s'il sort de l'écran)
    const follow = () => { if (!placeBubble(btnRef.current, bubbleRef.current)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') { setOpen(false); btnRef.current?.focus(); } };
    const onDown = (e) => {
      if (btnRef.current?.contains(e.target) || bubbleRef.current?.contains(e.target)) return;
      setOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('touchstart', onDown);
    window.addEventListener('resize', follow);
    window.addEventListener('scroll', follow, true);   // y compris les panneaux qui défilent
    return () => {
      document.removeEventListener('keydown', onKey);
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('touchstart', onDown);
      window.removeEventListener('resize', follow);
      window.removeEventListener('scroll', follow, true);
    };
  }, [open]);

  return (
    <span className="help-tip">
      <button type="button" className="help-tip-btn" ref={btnRef}
        aria-label={`Aide : ${label}`} aria-expanded={open} aria-controls={id}
        onClick={(e) => { e.preventDefault(); e.stopPropagation(); setOpen(o => !o); }}>
        ?
      </button>
      {open && createPortal(
        <span id={id} role="note" ref={bubbleRef} className="help-tip-bubble"
          style={{ visibility: 'hidden', left: 0, top: 0 }}>
          {children}
        </span>,
        document.body,
      )}
    </span>
  );
}
