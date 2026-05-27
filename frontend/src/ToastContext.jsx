/**
 * ToastContext.jsx — Système de notifications légères (snackbar)
 *
 * Usage :
 *   const toast = useToast();
 *   toast('✓ 12 recettes trouvées');               // succès par défaut
 *   toast('Erreur réseau', 'error');
 *   toast('Filtre appliqué', 'info');
 *
 * Types disponibles : 'success' | 'error' | 'info'
 * Durée par défaut  : 3 500 ms
 */

import { createContext, useContext, useState, useCallback, useRef } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const nextId = useRef(0);

  const dismiss = useCallback((id) => {
    setToasts(prev => prev.filter(t => t.id !== id));
  }, []);

  const toast = useCallback((message, type = 'success', duration = 3500) => {
    const id = ++nextId.current;
    setToasts(prev => [...prev, { id, message, type }]);
    setTimeout(() => dismiss(id), duration);
    return id;
  }, [dismiss]);

  return (
    <ToastContext.Provider value={toast}>
      {children}
      <div className="toast-container" aria-live="polite" aria-atomic="false">
        {toasts.map(t => (
          <div key={t.id} className={`toast toast--${t.type}`} role="status">
            <span className="toast-msg">{t.message}</span>
            <button
              className="toast-close"
              onClick={() => dismiss(t.id)}
              aria-label="Fermer la notification"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/** Retourne la fonction toast(message, type?, duration?) */
export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast() doit être utilisé dans un <ToastProvider>');
  return ctx;
}
