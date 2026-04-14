/**
 * Router.jsx — Hash router léger (zéro dépendance)
 *
 * Routes :
 *   /           → HomePage
 *   /recette/:id → RecipeDetailPage
 *   /frigo      → FrigoPage
 *   /planning   → PlanningPage
 *   /nutrition  → NutritionPage
 *   /profil     → ProfilePage
 *
 * Usage :
 *   <Link to="/frigo">Mon Frigo</Link>
 *   navigate('/recette/42')
 *   const { route, params } = useRouter();
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const RouterContext = createContext(null);

// ── Parsing du hash ───────────────────────────────────────────────────────────

function parseHash() {
  const raw = window.location.hash.replace(/^#/, '') || '/';
  return raw.startsWith('/') ? raw : '/' + raw;
}

function matchRoute(pattern, path) {
  const patternParts = pattern.split('/');
  const pathParts    = path.split('/');
  if (patternParts.length !== pathParts.length) return null;

  const params = {};
  for (let i = 0; i < patternParts.length; i++) {
    if (patternParts[i].startsWith(':')) {
      params[patternParts[i].slice(1)] = decodeURIComponent(pathParts[i]);
    } else if (patternParts[i] !== pathParts[i]) {
      return null;
    }
  }
  return params;
}

// ── Patterns déclarés ─────────────────────────────────────────────────────────

const ROUTES = [
  { pattern: '/',               page: 'home'   },
  { pattern: '/recette/:id',    page: 'recipe' },
  { pattern: '/frigo',          page: 'frigo'  },
  { pattern: '/planning',       page: 'planning' },
  { pattern: '/nutrition',      page: 'nutrition' },
  { pattern: '/profil',         page: 'profil' },
  { pattern: '/cycle-astro',    page: 'cycle-astro' },
];

function resolve(path) {
  for (const r of ROUTES) {
    const params = matchRoute(r.pattern, path);
    if (params !== null) return { page: r.page, params };
  }
  return { page: 'home', params: {} };
}

// ── Provider ──────────────────────────────────────────────────────────────────

export function RouterProvider({ children }) {
  const [location, setLocation] = useState(parseHash);

  useEffect(() => {
    const handler = () => setLocation(parseHash());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  const navigate = useCallback((to) => {
    window.location.hash = to;
  }, []);

  const { page, params } = resolve(location);

  return (
    <RouterContext.Provider value={{ location, page, params, navigate }}>
      {children}
    </RouterContext.Provider>
  );
}

// ── Hooks et composants publics ───────────────────────────────────────────────

export const useRouter = () => useContext(RouterContext);

export function Link({ to, children, className, style, onClick }) {
  const handleClick = (e) => {
    onClick?.(e);
  };
  return (
    <a
      href={`#${to}`}
      className={className}
      style={style}
      onClick={handleClick}
    >
      {children}
    </a>
  );
}

export function navigate(to) {
  window.location.hash = to;
}
