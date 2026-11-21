/**
 * Notifications.jsx — Cloche de la barre de navigation et liste des nouveautés.
 *
 *  - useUnreadCount : nombre de non lues, rafraîchi toutes les 60 s et au retour
 *                     sur l'onglet (léger : GET /notifications/count)
 *  - NotificationBell : cloche + pastille + liste déroulante (ordinateur)
 *  - NotificationList : la liste, réutilisée par la page #/notifications (mobile)
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { notifications as api } from '../api';
import { useAuth } from '../AuthContext';
import { navigate, Link } from '../Router';

const POLL_MS = 60000;
const listeners = new Set();
export function announceUnread(n) { listeners.forEach(cb => cb(n)); }

export function useUnreadCount() {
  const { user } = useAuth();
  const [count, setCount] = useState(0);
  useEffect(() => {
    if (!user) return undefined;
    let alive = true;
    const refresh = () => api.count().then(r => { if (alive) setCount(r.unread || 0); }).catch(() => {});
    refresh();
    const t = setInterval(refresh, POLL_MS);
    const onFocus = () => { if (document.visibilityState === 'visible') refresh(); };
    document.addEventListener('visibilitychange', onFocus);
    const cb = (n) => setCount(n);
    listeners.add(cb);
    return () => { alive = false; clearInterval(t); document.removeEventListener('visibilitychange', onFocus); listeners.delete(cb); };
  }, [user]);
  return user ? count : 0;
}

function timeAgo(iso) {
  const d = new Date(iso);
  const s = Math.max(0, (Date.now() - d.getTime()) / 1000);
  if (s < 60) return 'à l\'instant';
  if (s < 3600) return `il y a ${Math.floor(s / 60)} min`;
  if (s < 86400) return `il y a ${Math.floor(s / 3600)} h`;
  if (s < 7 * 86400) return `il y a ${Math.floor(s / 86400)} j`;
  return d.toLocaleDateString('fr-FR', { day: 'numeric', month: 'short' });
}

const ICONS = {
  'contribution.published': '✅', 'contribution.revision_published': '✅',
  'contribution.changes_requested': '✏️', 'contribution.revision_changes_requested': '✏️',
  'contribution.unpublished': '✏️', 'contribution.rejected': '✖️', 'contribution.revision_rejected': '✖️',
  'review.new': '⭐', 'review.reply': '💬', 'moderation.submitted': '🛡',
};

export function NotificationList({ onNavigate, compact = false }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    api.list().then(d => { setData(d); announceUnread(d.unread); }).catch(e => setError(e.message));
  }, []);

  const open = async (n) => {
    if (!n.read) {
      try {
        const r = await api.markRead(n.id);
        announceUnread(r.unread);
        setData(d => ({ ...d, unread: r.unread, results: d.results.map(x => (x.id === n.id ? { ...x, read: true } : x)) }));
      } catch { /* la navigation reste possible */ }
    }
    if (n.link) { navigate(n.link); onNavigate?.(); }
  };
  const all = async () => {
    try {
      await api.markAll();
      announceUnread(0);
      setData(d => ({ ...d, unread: 0, results: d.results.map(x => ({ ...x, read: true })) }));
    } catch (e) { setError(e.message); }
  };

  if (error) return <p className="ct-error">{error}</p>;
  if (!data) return <p className="ct-muted nt-pad">Chargement…</p>;
  return (
    <div className={`nt-list ${compact ? 'nt-list--compact' : ''}`}>
      <div className="nt-head">
        <strong>Notifications</strong>
        {data.unread > 0 && <button type="button" className="rv-link" onClick={all}>Tout marquer comme lu</button>}
      </div>
      {data.results.length === 0 && <p className="ct-muted nt-pad">Rien de neuf pour l'instant.</p>}
      <ul>
        {data.results.map(n => (
          <li key={n.id}>
            <button type="button" className={`nt-item ${n.read ? '' : 'is-unread'}`} onClick={() => open(n)}>
              <span className="nt-icon" aria-hidden="true">{ICONS[n.kind] || '•'}</span>
              <span className="nt-text">
                <span className="nt-title">{n.title}</span>
                {n.body && <span className="nt-body">{n.body}</span>}
                <span className="nt-time">{timeAgo(n.created_at)}{!n.read && <span className="sr-only"> — non lue</span>}</span>
              </span>
            </button>
          </li>
        ))}
      </ul>
      {compact && <Link to="/notifications" className="nt-all" onClick={onNavigate}>Voir toutes les notifications</Link>}
    </div>
  );
}

export function NotificationBell({ count = 0 }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const close = useCallback(() => setOpen(false), []);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('mousedown', onDown); document.removeEventListener('keydown', onKey); };
  }, [open]);

  return (
    <div className="nt-bell-wrap" ref={ref}>
      <button type="button" className="nav-theme-toggle nt-bell" aria-expanded={open} aria-haspopup="true"
        aria-label={count ? `Notifications : ${count} non lue${count > 1 ? 's' : ''}` : 'Notifications'}
        onClick={() => setOpen(o => !o)}>
        <span aria-hidden="true">🔔</span>
        {count > 0 && <span className="nt-badge" aria-hidden="true">{count > 9 ? '9+' : count}</span>}
      </button>
      {open && (
        <div className="nt-popover" role="dialog" aria-label="Notifications">
          <NotificationList compact onNavigate={close} />
        </div>
      )}
    </div>
  );
}
