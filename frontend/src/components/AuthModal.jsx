/**
 * AuthModal.jsx — Modal Login / Register / Forgot Password
 */

import { useState } from 'react';
import { useAuth } from '../AuthContext';
import { auth as authApi } from '../api';

export default function AuthModal({ onClose }) {
  const [mode,     setMode]     = useState('login'); // 'login' | 'register' | 'forgot' | 'reset'
  const [email,    setEmail]    = useState('');
  const [password, setPassword] = useState('');
  const [name,     setName]     = useState('');
  const [error,    setError]    = useState('');
  const [success,  setSuccess]  = useState('');
  const [loading,  setLoading]  = useState(false);
  const [resetToken, setResetToken] = useState('');
  const [newPassword, setNewPassword] = useState('');

  const { login, register } = useAuth();

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
        // En dev : afficher le token pour test
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

  return (
    <div className="modal-backdrop" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal-box">
        <button className="modal-close" onClick={onClose}>✕</button>

        <div className="modal-header">
          <h2 className="modal-title">
            {mode === 'login' && 'Connexion'}
            {mode === 'register' && 'Créer un compte'}
            {mode === 'forgot' && 'Mot de passe oublié'}
            {mode === 'reset' && 'Nouveau mot de passe'}
          </h2>
          <p className="modal-sub">
            {mode === 'login' && 'Accédez à votre planning, nutrition et frigo.'}
            {mode === 'register' && 'Gratuit. Toujours.'}
            {mode === 'forgot' && 'Entrez votre email pour recevoir un lien de réinitialisation.'}
            {mode === 'reset' && 'Choisissez un nouveau mot de passe sécurisé.'}
          </p>
        </div>

        <form className="modal-form" onSubmit={handleSubmit}>
          {mode === 'register' && (
            <div className="form-field">
              <label>Prénom</label>
              <input
                type="text"
                placeholder="Marie"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
            </div>
          )}

          {(mode === 'login' || mode === 'register' || mode === 'forgot') && (
            <div className="form-field">
              <label>Email</label>
              <input
                type="email"
                placeholder="marie@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoFocus={mode === 'login' || mode === 'forgot'}
                required
              />
            </div>
          )}

          {(mode === 'login' || mode === 'register') && (
            <div className="form-field">
              <label>Mot de passe</label>
              <input
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          )}

          {mode === 'reset' && (
            <div className="form-field">
              <label>Nouveau mot de passe</label>
              <input
                type="password"
                placeholder="••••••••"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoFocus
                required
                minLength={8}
              />
            </div>
          )}

          {error && <p className="form-error">{error}</p>}
          {success && <p className="form-success" style={{ color: 'var(--green)', fontSize: '13px', marginBottom: '8px' }}>{success}</p>}

          <button type="submit" className="form-submit" disabled={loading}>
            {loading
              ? 'Chargement…'
              : mode === 'login' ? 'Se connecter'
              : mode === 'register' ? 'Créer mon compte'
              : mode === 'forgot' ? 'Envoyer le lien'
              : 'Réinitialiser'}
          </button>
        </form>

        <div className="modal-switch">
          {mode === 'login' && (
            <>
              <span>Pas encore de compte ?{' '}
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
            <>Déjà un compte ?{' '}
              <button onClick={() => switchTo('login')}>Connexion</button>
            </>
          )}
          {(mode === 'forgot' || mode === 'reset') && (
            <>
              <button onClick={() => switchTo('login')}>← Retour à la connexion</button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
