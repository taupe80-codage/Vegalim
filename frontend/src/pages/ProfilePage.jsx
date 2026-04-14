import { useState, useEffect } from 'react';
import { profile as profileApi } from '../api';
import { useAuth } from '../AuthContext';

export default function ProfilePage({ onAuthClick }) {
  const { user, logout } = useAuth();
  const [prefs, setPrefs] = useState({
    diet: '', allergies: [], goal: '',
  });
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    if (!user) return;
    profileApi.get().then(setPrefs).catch(() => {});
  }, [user]);

  if (!user) {
    return (
      <div className="page-profil">
        <div className="page-header">
          <h1 className="page-title">Mon profil</h1>
        </div>
        <div className="frigo-empty">
          <div className="frigo-empty-icon" style={{ fontSize: 48 }}>◎</div>
          <p>Connectez-vous pour accéder à votre profil et personnaliser vos recommandations.</p>
          <button className="frigo-search-btn" onClick={onAuthClick} style={{ marginTop: 24 }}>
            Connexion / Inscription
          </button>
        </div>
      </div>
    );
  }

  const handleSave = async () => {
    try {
      await profileApi.update(prefs);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {}
  };

  return (
    <div className="page-profil">
      <div className="page-header">
        <h1 className="page-title">Mon profil</h1>
        <p className="page-sub">{user.email}</p>
      </div>

      <div className="profil-grid">
        <div className="frigo-panel">
          <h3 className="frigo-panel-title">Préférences alimentaires</h3>

          <div className="form-field">
            <label>Régime principal</label>
            <select
              value={prefs.diet || ''}
              onChange={(e) => setPrefs((p) => ({ ...p, diet: e.target.value }))}
              className="search-input"
              style={{ padding: '10px 14px', fontSize: 14 }}
            >
              <option value="">Aucun en particulier</option>
              <option value="vegan">Vegan</option>
              <option value="vegetarian">Végétarien</option>
            </select>
          </div>

          <div className="form-field">
            <label>Objectif nutritionnel</label>
            <select
              value={prefs.goal || ''}
              onChange={(e) => setPrefs((p) => ({ ...p, goal: e.target.value }))}
              className="search-input"
              style={{ padding: '10px 14px', fontSize: 14 }}
            >
              <option value="">Sans objectif particulier</option>
              <option value="proteines">Apport protéique élevé</option>
              <option value="poids">Gestion du poids</option>
              <option value="energie">Énergie sportive</option>
              <option value="sante">Santé générale</option>
            </select>
          </div>

          <button className="frigo-search-btn" onClick={handleSave} style={{ marginTop: 16 }}>
            {saved ? '✓ Enregistré' : 'Sauvegarder'}
          </button>
        </div>

        <div className="frigo-panel">
          <h3 className="frigo-panel-title">Compte</h3>
          <p style={{ color: 'var(--mut)', fontSize: 14, marginBottom: 20 }}>
            Connecté en tant que <strong>{user.email}</strong>
          </p>
          <button
            onClick={logout}
            className="search-button"
            style={{ background: 'transparent', border: '1px solid var(--brd)', color: 'var(--mut)' }}
          >
            Déconnexion
          </button>
        </div>
      </div>
    </div>
  );
}
