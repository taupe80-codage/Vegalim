/**
 * NotificationsPage.jsx — Toutes les notifications (#/notifications), surtout pour le mobile.
 */
import { useAuth } from '../AuthContext';
import { NotificationList } from '../components/Notifications';

export default function NotificationsPage({ onAuthClick }) {
  const { user, loading } = useAuth();
  return (
    <div className="ct-page">
      <header className="page-header">
        <h1 className="page-title"><span className="page-icon" aria-hidden="true">🔔</span> Notifications</h1>
        <p className="page-sub">Les décisions sur vos recettes, les avis reçus et les réponses à vos commentaires.</p>
      </header>
      {loading ? null : user ? (
        <div className="nt-page"><NotificationList /></div>
      ) : (
        <button type="button" className="ct-btn ct-btn--primary" onClick={onAuthClick}>Se connecter</button>
      )}
    </div>
  );
}
