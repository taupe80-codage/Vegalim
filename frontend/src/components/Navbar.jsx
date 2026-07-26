/**
 * Navbar.jsx — Navigation principale ALIM v6
 *
 * Axe 5 — Accessibilité :
 *  - aria-current="page" sur le lien actif
 *  - aria-label sur les boutons icon-only (logout, avatar)
 *  - aria-expanded + aria-controls sur le hamburger mobile
 */

import { useState } from 'react';
import { Link, useRouter } from '../Router';
import { useAuth } from '../AuthContext';
import { useTheme } from '../ThemeContext';

// Icônes Unicode (pas émoji) — cohérent avec la typo Geist + le toggle ☼/☾
// Les Favoris sont accessibles via le menu Profil (◎)
const NAV_LINKS = [
  { to: '/',          label: 'Recettes',  icon: '✦'  },
  { to: '/frigo',     label: 'Mon frigo', icon: '🧊'  },
  { to: '/planning',  label: 'Planning',  icon: '▦'  },
  { to: '/courses',   label: 'Courses',   icon: '🛒'  },
  { to: '/nutrition', label: 'Nutrition', icon: '◉'  },
  { to: '/cycle',     label: 'Cycle',     icon: '🌑' },
  { to: '/astro',     label: 'Astro',     icon: '✨' },
  { to: '/fodmap',    label: 'FODMAP',    icon: '🌿' },
  { to: '/faq',       label: 'FAQ',       icon: '❓' },
];

export default function Navbar({ onAuthClick }) {
  const { page }               = useRouter();
  const { user, logout }       = useAuth();
  const { theme, toggleTheme } = useTheme();
  const [menuOpen, setMenuOpen] = useState(false);

  const isActive = (to) => {
    if (to === '/') return page === 'home' || page === 'recipe';
    return page === to.replace('/', '');
  };

  return (
    <header className="navbar">
      <div className="navbar-inner">
        {/* Logo */}
        <Link to="/" className="nav-logo">
          ALIM<span className="nav-logo-version">v6</span>
        </Link>

        {/* Links desktop */}
        <nav className="nav-links" aria-label="Navigation principale">
          {NAV_LINKS.map(({ to, label, icon }) => (
            <Link
              key={to}
              to={to}
              className={`nav-link ${isActive(to) ? 'nav-link--active' : ''}`}
              aria-current={isActive(to) ? 'page' : undefined}
            >
              <span className="nav-link-icon" aria-hidden="true">{icon}</span>
              {label}
            </Link>
          ))}
        </nav>

        {/* Auth + Theme toggle */}
        <div className="nav-auth">
          <button
            className="nav-theme-toggle"
            onClick={toggleTheme}
            aria-label={theme === 'dark' ? 'Passer en mode clair' : 'Passer en mode sombre'}
            title={theme === 'dark' ? 'Mode clair' : 'Mode sombre'}
          >
            <span aria-hidden="true">{theme === 'dark' ? '☼' : '☾'}</span>
          </button>

          {user ? (
            <div className="nav-user">
              <Link
                to="/profil"
                className="nav-avatar"
                aria-label={`Profil de ${user.name || user.email}`}
              >
                <span aria-hidden="true">
                  {(user.name || user.email || '?')[0].toUpperCase()}
                </span>
              </Link>
              <button
                className="nav-logout"
                onClick={logout}
                aria-label="Se déconnecter"
                title="Déconnexion"
              >
                <span aria-hidden="true">⤫</span>
              </button>
            </div>
          ) : (
            <button className="nav-login-btn" onClick={onAuthClick}>
              Connexion
            </button>
          )}
        </div>

        {/* Hamburger mobile */}
        <button
          className={`nav-hamburger ${menuOpen ? 'open' : ''}`}
          onClick={() => setMenuOpen(!menuOpen)}
          aria-label={menuOpen ? 'Fermer le menu' : 'Ouvrir le menu'}
          aria-expanded={menuOpen}
          aria-controls="nav-mobile-menu"
        >
          <span aria-hidden="true" /><span aria-hidden="true" /><span aria-hidden="true" />
        </button>
      </div>

      {/* Menu mobile */}
      {menuOpen && (
        <nav id="nav-mobile-menu" className="nav-mobile" aria-label="Navigation mobile">
          {NAV_LINKS.map(({ to, label, icon }) => (
            <Link
              key={to}
              to={to}
              className={`nav-mobile-link ${isActive(to) ? 'nav-link--active' : ''}`}
              aria-current={isActive(to) ? 'page' : undefined}
              onClick={() => setMenuOpen(false)}
            >
              <span aria-hidden="true">{icon}</span> {label}
            </Link>
          ))}
          {!user && (
            <button
              className="nav-login-btn"
              onClick={() => { setMenuOpen(false); onAuthClick(); }}
            >
              Connexion
            </button>
          )}
        </nav>
      )}
    </header>
  );
}
