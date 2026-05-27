/**
 * ThemeContext.jsx — Gestion dark/light mode ALIM v6
 *
 * Usage :
 *   const { theme, toggleTheme } = useTheme();
 *
 * Le thème est persisté dans localStorage et appliqué via
 * l'attribut data-theme="dark" sur <html>.
 * Par défaut : light (jour) — direction Maraîcher day-first.
 */

import { createContext, useContext, useState, useEffect } from 'react';

const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    // Lire la préférence sauvegardée, sinon light par défaut (Maraîcher = jour-first)
    return localStorage.getItem('alim-theme') || 'light';
  });

  // Appliquer l'attribut sur <html> à chaque changement
  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'dark') {
      root.setAttribute('data-theme', 'dark');
    } else {
      root.removeAttribute('data-theme');
    }
    localStorage.setItem('alim-theme', theme);
  }, [theme]);

  const toggleTheme = () =>
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'));

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
}

export const useTheme = () => useContext(ThemeContext);
