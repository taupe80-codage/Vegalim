/**
 * ErrorBoundary.jsx — Capture les erreurs JS non gérées dans l'arbre React.
 *
 * Utilisé dans main.jsx pour envelopper toute l'application.
 * En cas de crash d'un composant, affiche un écran de secours au lieu d'une
 * page blanche — l'utilisateur peut relancer sans recharger l'onglet.
 *
 * Note : les ErrorBoundary doivent rester des class components (limitation React).
 * Le hook useErrorBoundary n'existe pas nativement en React 19 sans lib externe.
 */

import { Component } from 'react';

// ── Écran de secours ──────────────────────────────────────────────────────────

function FallbackUI({ error, onRetry }) {
  const isNetworkError = error?.message?.toLowerCase().includes('fetch') ||
                         error?.message?.toLowerCase().includes('network') ||
                         error?.message?.toLowerCase().includes('erreur 5');

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
      fontFamily: 'system-ui, sans-serif',
      background: '#fafaf8',
      color: '#2d2d2d',
      textAlign: 'center',
      gap: '1rem',
    }}>
      <div style={{ fontSize: '3rem' }}>🥦</div>

      <h2 style={{ margin: 0, fontWeight: 600, fontSize: '1.4rem' }}>
        {isNetworkError ? 'Connexion interrompue' : 'Une erreur est survenue'}
      </h2>

      <p style={{ margin: 0, color: '#666', maxWidth: '420px', lineHeight: 1.6 }}>
        {isNetworkError
          ? "L'API ALIM est momentanément indisponible. Vérifiez votre connexion ou réessayez dans quelques instants."
          : "L'application a rencontré un problème inattendu. Vos données sont préservées."
        }
      </p>

      {/* Détail technique — affiché uniquement en dev */}
      {import.meta.env.DEV && error?.message && (
        <pre style={{
          background: '#f0f0f0',
          padding: '0.75rem 1rem',
          borderRadius: '6px',
          fontSize: '0.75rem',
          color: '#c0392b',
          maxWidth: '600px',
          overflowX: 'auto',
          textAlign: 'left',
        }}>
          {error.message}
        </pre>
      )}

      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
        <button
          onClick={onRetry}
          style={{
            padding: '0.6rem 1.4rem',
            background: '#2d6a4f',
            color: '#fff',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            fontWeight: 500,
            fontSize: '0.95rem',
          }}
        >
          Réessayer
        </button>
        <button
          onClick={() => window.location.reload()}
          style={{
            padding: '0.6rem 1.4rem',
            background: 'transparent',
            color: '#555',
            border: '1px solid #ccc',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '0.95rem',
          }}
        >
          Recharger la page
        </button>
      </div>
    </div>
  );
}

// ── ErrorBoundary class ───────────────────────────────────────────────────────

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
    this._handleRetry = this._handleRetry.bind(this);
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, info) {
    // Log structuré — récupérable dans Sentry / Datadog si branché
    console.error('[ALIM] Erreur non gérée :', {
      message:    error?.message,
      stack:      error?.stack,
      component:  info?.componentStack,
    });
  }

  _handleRetry() {
    this.setState({ hasError: false, error: null });
  }

  render() {
    if (this.state.hasError) {
      return (
        <FallbackUI
          error={this.state.error}
          onRetry={this._handleRetry}
        />
      );
    }
    return this.props.children;
  }
}
