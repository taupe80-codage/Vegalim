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
 *   const { route, params, search, setSearch } = useRouter();
 *
 * Persistance état HomePage :
 *   Le hash supporte une query string : #/?q=soupe&diet=vegan&sort=score&time=30&al=gluten_free,nut_free&hf=high_protein
 *   → le state de HomePage est encodé dans l'URL, restauré au retour arrière nativement.
 */

import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const RouterContext = createContext(null);

// ── Parsing du hash ───────────────────────────────────────────────────────────

function parseHash() {
  // hash peut être :  #/recette/42  ou  #/?q=soupe&diet=vegan
  const raw = window.location.hash.replace(/^#/, '') || '/';
  const [pathPart, searchPart] = raw.split('?');
  const path = pathPart.startsWith('/') ? pathPart : '/' + pathPart;
  const search = searchPart ? new URLSearchParams(searchPart) : new URLSearchParams();
  return { path, search };
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
  { pattern: '/',            page: 'home'       },
  { pattern: '/recette/:id', page: 'recipe'     },
  { pattern: '/frigo',       page: 'frigo'      },
  { pattern: '/planning',    page: 'planning'   },
  { pattern: '/nutrition',   page: 'nutrition'  },
  { pattern: '/profil',      page: 'profil'     },
  { pattern: '/favoris',     page: 'favoris'    },
  { pattern: '/cycle',       page: 'cycle'      },
  { pattern: '/astro',       page: 'astro'      },
  { pattern: '/cycle-astro', page: 'cycle-astro'},
  { pattern: '/courses',    page: 'courses'    },
  { pattern: '/fodmap',     page: 'fodmap'     },
  { pattern: '/faq',        page: 'faq'        },
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
  const [loc, setLoc] = useState(parseHash);

  useEffect(() => {
    const handler = () => setLoc(parseHash());
    window.addEventListener('hashchange', handler);
    return () => window.removeEventListener('hashchange', handler);
  }, []);

  // navigate vers un chemin, en préservant ou écrasant la query string
  const navigate = useCallback((to, searchParams) => {
    if (searchParams !== undefined) {
      const qs = searchParams.toString();
      window.location.hash = qs ? `${to}?${qs}` : to;
    } else {
      window.location.hash = to;
    }
  }, []);

  // Met à jour uniquement la query string du hash courant (sans changer la page)
  const setSearch = useCallback((searchParams) => {
    const qs = searchParams.toString();
    window.location.hash = qs ? `${loc.path}?${qs}` : loc.path;
  }, [loc.path]);

  const { page, params } = resolve(loc.path);

  return (
    <RouterContext.Provider value={{
      location: loc.path,
      page,
      params,
      search: loc.search,   // URLSearchParams courant
      navigate,
      setSearch,            // met à jour la QS sans changer de page
    }}>
      {children}
    </RouterContext.Provider>
  );
}

// ── Hooks et composants publics ───────────────────────────────────────────────

export const useRouter = () => useContext(RouterContext);

export function Link({ to, children, className, style, onClick, 'aria-current': ariaCurrent, 'aria-label': ariaLabel }) {
  return (
    <a
      href={`#${to}`}
      className={className}
      style={style}
      onClick={onClick}
      aria-current={ariaCurrent}
      aria-label={ariaLabel}
    >
      {children}
    </a>
  );
}

export function navigate(to) {
  window.location.hash = to;
}
