/**
 * AuthModal.jsx — Modal Login / Register / Forgot Password
 *
 * Axe 5 — Accessibilité :
 *  - role="dialog" + aria-modal="true" + aria-labelledby
 *  - Focus trap (Tab / Shift+Tab) + fermeture Escape
 *  - Restitution du focus à l'élément déclencheur à la fermeture
 *  - aria-live="polite" sur les messages d'erreur / succès
 *  - id + htmlFor corrects sur tous les champs
 *  - aria-label explicite sur le bouton ✕
 */

import { useState, useEffect, useRef } from 'react';
import { useAuth } from '../AuthContext';
import { auth as authApi } from '../api';

export default function AuthModal({ onClose }) {
  const [mode,        setMode]        = useState('login'); // 'login' | 'register' | 'forgot' | 'reset'
  const [email,       setEmail]       = useState('');
  const [password,    setPassword]    = useState('');
  const [name,        setName]        = useState('');
  const [error,       setError]       = useState('');
  const [success,     setSuccess]     = useState('');
  const [loading,     setLoading]     = useState(false);
  const [resetToken,  setResetToken]  = useState('');
  const [newPassword, setNewPassword] = useState('');

  const { login, register } = useAuth();
  const modalRef = useRef(null);

  // ── Focus trap ────────────────────────────────────────────────────────────
  useEffect(() => {
    const previouslyFocused = document.activeElement;

    // Focus sur le premier élément interactif
    const firstFocusable = modalRef.current?.querySelector(
      'button:not([disabled]), input, [tabindex]:not([tabindex="-1"])'
    );
    firstFocusable?.focus();

    const handleKeyDown = (e) => {
      if (e.key === 'Escape') { onClose(); return; }
      if (e.key !== 'Tab') return;

      const focusables = Array.from(
        modalRef.current?.querySelectorAll(
          'button:not([disabled]), input, [tabindex]:not([tabindex="-1"])'
        ) || []
      );
      if (!focusables.length) return;

      const first = focusables[0];
      const last  = focusables[focusables.length - 1];

      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last)  { e.preventDefault(); first.focus(); }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      previouslyFocused?.focus(); // Restituer le focus au déclencheur
    };
  }, [onClose]);

  // ── Handlers ──────────────────────────────────────────────────────────────
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);
    try {
      if (mode === 'login') {
        await login(email, password);
        onClose();
      } else if (mode === 'register') {
        await register(email, password, name);
        onClose();
      } else if (mode === 'forgot') {
        const result = await authApi.forgotPassword(email);
        setSuccess(result.message || 'Lien de réinitialisation envoyé.');
        if (result._dev_reset_token) {
          setResetToken(result._dev_reset_token);
          setMode('reset');
          setSuccess('Token généré ! Entrez votre nouveau mot de passe.');
        }
      } else if (mode === 'reset') {
        await authApi.resetPassword(resetToken, newPassword);
        setSuccess('Mot de passe modifié avec succès !');
        setTimeout(() => {
          setMode('login');
          setSuccess('');
          setPassword('');
        }, 1500);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const switchTo = (newMode) => {
    setMode(newMode);
    setError('');
    setSuccess('');
  };

  // ── Titre du dialog (pour aria-labelledby) ────────────────────────────────
  const TITLE_ID = 'auth-modal-title';
  const modeLabel = {
    login:    'Connexion',
    register: 'Créer un compte',
    forgot:   'Mot de passe oublié',
    reset:    'Nouveau mot de passe',
  }[mode];

  return (
    <div
      className="modal-backdrop"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        ref={modalRef}
        className="modal-box"
        role="dialog"
        aria-modal="true"
        aria-labelledby={TITLE_ID}
      >
        {/* Bouton fermeture */}
        <button
          className="modal-close"
          onClick={onClose}
          aria-label="Fermer la fenêtre de connexion"
        >
          ✕
        </button>

        {/* En-tête */}
        <div className="modal-header">
          <h2 id={TITLE_ID} className="modal-title">{modeLabel}</h2>
          <p className="modal-sub">
            {mode === 'login'    && 'Accédez à votre planning, nutrition et frigo.'}
            {mode === 'register' && 'Gratuit. Toujours.'}
            {mode === 'forgot'   && 'Entrez votre email pour recevoir un lien de réinitialisation.'}
            {mode === 'reset'    && 'Choisissez un nouveau mot de passe sécurisé.'}
          </p>
        </div>

        {/* Formulaire */}
        <form className="modal-form" onSubmit={handleSubmit} noValidate>

          {mode === 'register' && (
            <div className="form-field">
              <label htmlFor="auth-name">Prénom</label>
              <input
                id="auth-name"
                type="text"
                placeholder="Marie"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
                autoComplete="given-name"
              />
            </div>
          )}

          {(mode === 'login' || mode === 'register' || mode === 'forgot') && (
            <div className="form-field">
              <label htmlFor="auth-email">Email</label>
              <input
                id="auth-email"
                type="email"
                placeholder="marie@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus={mode === 'login' || mode === 'forgot'}
                autoComplete="email"
                required
              />
            </div>
          )}

          {(mode === 'login' || mode === 'register') && (
            <div className="form-field">
              <label htmlFor="auth-password">Mot de passe</label>
              <input
                id="auth-password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete={mode === 'register' ? 'new-password' : 'current-password'}
                required
              />
            </div>
          )}

          {mode === 'reset' && (
            <div className="form-field">
              <label htmlFor="auth-new-password">Nouveau mot de passe</label>
              <input
                id="auth-new-password"
                type="password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoFocus
                autoComplete="new-password"
                required
                minLength={8}
              />
            </div>
          )}

          {/* Messages annoncés aux lecteurs d'écran via aria-live */}
          <div aria-live="polite" aria-atomic="true">
            {error   && <p className="form-error">{error}</p>}
            {success && (
              <p className="form-success" style={{ color: 'var(--grn)', fontSize: '13px', marginBottom: '8px' }}>
                {success}
              </p>
            )}
          </div>

          <button type="submit" className="form-submit" disabled={loading}>
            {loading
              ? 'Chargement…'
              : mode === 'login'    ? 'Se connecter'
              : mode === 'register' ? 'Créer mon compte'
              : mode === 'forgot'   ? 'Envoyer le lien'
              : 'Réinitialiser'}
          </button>
        </form>

        {/* Liens de navigation entre modes */}
        <div className="modal-switch">
          {mode === 'login' && (
            <>
              <span>
                Pas encore de compte ?{' '}
                <button onClick={() => switchTo('register')}>Inscription</button>
              </span>
              <br />
              <button
                onClick={() => switchTo('forgot')}
                style={{ marginTop: '8px', fontSize: '12px', opacity: 0.7 }}
              >
                Mot de passe oublié ?
              </button>
            </>
          )}
          {mode === 'register' && (
            <>
              Déjà un compte ?{' '}
              <button onClick={() => switchTo('login')}>Connexion</button>
            </>
          )}
          {(mode === 'forgot' || mode === 'reset') && (
            <button onClick={() => switchTo('login')}>← Retour à la connexion</button>
          )}
        </div>
      </div>
    </div>
  );
}
