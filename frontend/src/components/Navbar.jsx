/**
 * Navbar.jsx — Navigation principale ALIM v6
 */

import { useState } from 'react';
import { Link, useRouter } from '../Router';
import { useAuth } from '../AuthContext';

const NAV_LINKS = [
  { to: '/',         label: 'Recettes',  icon: '✦' },
  { to: '/frigo',    label: 'Mon frigo', icon: '◈' },
  { to: '/planning', label: 'Planning',  icon: '▦'  },
  { to: '/nutrition',label: 'Nutrition', icon: '◉'  },
  { to: '/cycle-astro',label: 'Bien-être', icon: '🌙'  },
];

export default function Navbar({ onAuthClick }) {
  const { page }            = useRouter();
  const { user, logout }    = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const isActive = (to) => {
    if (to === '/' ) return page === 'home' || page === 'recipe';
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
        <nav className="nav-links">
          {NAV_LINKS.map(({ to, label, icon }) => (
            <Link
              key={to}
              to={to}
              className={`nav-link ${isActive(to) ? 'nav-link--active' : ''}`}
            >
              <span className="nav-link-icon">{icon}</span>
              {label}
            </Link>
          ))}
        </nav>

        {/* Auth */}
        <div className="nav-auth">
          {user ? (
            <div className="nav-user">
              <Link to="/profil" className="nav-avatar" title={user.email}>
                {(user.name || user.email || '?')[0].toUpperCase()}
              </Link>
              <button className="nav-logout" onClick={logout} title="Déconnexion">
                ⤫
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
          aria-label="Menu"
        >
          <span /><span /><span />
        </button>
      </div>

      {/* Menu mobile */}
      {menuOpen && (
        <nav className="nav-mobile">
          {NAV_LINKS.map(({ to, label, icon }) => (
            <Link
              key={to}
              to={to}
              className={`nav-mobile-link ${isActive(to) ? 'nav-link--active' : ''}`}
              onClick={() => setMenuOpen(false)}
            >
              <span>{icon}</span> {label}
            </Link>
          ))}
          {!user && (
            <button className="nav-login-btn" onClick={() => { setMenuOpen(false); onAuthClick(); }}>
              Connexion
            </button>
          )}
        </nav>
      )}
    </header>
  );
}
