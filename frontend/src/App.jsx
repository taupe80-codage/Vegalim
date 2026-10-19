/**
 * App.jsx — Orchestrateur ALIM v6
 *
 * Responsabilités :
 *  - Fournir RouterProvider + AuthProvider
 *  - Dispatcher les pages selon la route
 *  - Gérer l'état global du modal auth
 */

import { useState } from 'react';
import { RouterProvider, useRouter } from './Router';
import { AuthProvider }     from './AuthContext';
import { ThemeProvider }    from './ThemeContext';
import { ToastProvider }    from './ToastContext';
import { FavoritesProvider } from './FavoritesContext';
import Navbar            from './components/Navbar';
import AuthModal         from './components/AuthModal';
import HomePage          from './pages/HomePage';
import RecipeDetailPage  from './pages/RecipeDetailPage';
import FrigoPage         from './pages/FrigoPage';
import PlanningPage      from './pages/PlanningPage';
import NutritionPage     from './pages/NutritionPage';
import ProfilePage       from './pages/ProfilePage';
import CyclePage         from './pages/CyclePage';
import AstroPage         from './pages/AstroPage';
import FavoritesPage     from './pages/FavoritesPage';
import ShoppingListPage  from './pages/ShoppingListPage';
import FodmapPage        from './pages/FodmapPage';
import FAQPage           from './pages/FAQPage';
import CreditsPage       from './pages/CreditsPage';
import { Link }          from './Router';
import './index.css';

// ── Dispatcher ────────────────────────────────────────────────────────────────

function PageDispatcher({ onAuthClick }) {
  const { page } = useRouter();

  switch (page) {
    case 'home':      return <HomePage />;
    case 'recipe':    return <RecipeDetailPage />;
    case 'frigo':     return <FrigoPage />;
    case 'planning':  return <PlanningPage />;
    case 'nutrition': return <NutritionPage />;
    case 'profil':    return <ProfilePage onAuthClick={onAuthClick} />;
    case 'favoris':    return <FavoritesPage />;
    case 'cycle':      return <CyclePage />;
    case 'astro':      return <AstroPage />;
    case 'cycle-astro': return <CyclePage />;
    case 'courses':     return <ShoppingListPage />;
    case 'fodmap':      return <FodmapPage />;
    case 'faq':         return <FAQPage />;
    case 'credits':     return <CreditsPage />;
    default:          return <HomePage />;
  }
}

// ── App racine ────────────────────────────────────────────────────────────────

function AppInner() {
  const [showAuth, setShowAuth] = useState(false);

  return (
    <div className="app-container">
      <Navbar onAuthClick={() => setShowAuth(true)} />

      <main className="app-main">
        <PageDispatcher onAuthClick={() => setShowAuth(true)} />
      </main>

      {/* Les photos sous licence Creative Commons imposent de citer leurs
          auteurs : le lien doit rester accessible depuis toutes les pages. */}
      <footer className="app-footer">
        <span>ALIM v6</span>
        <span aria-hidden="true">·</span>
        <Link to="/credits" className="app-footer-link">Crédits photos</Link>
        <span aria-hidden="true">·</span>
        <Link to="/faq" className="app-footer-link">FAQ</Link>
      </footer>

      {showAuth && <AuthModal onClose={() => setShowAuth(false)} />}
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <RouterProvider>
        <AuthProvider>
          <ToastProvider>
            <FavoritesProvider>
              <AppInner />
            </FavoritesProvider>
          </ToastProvider>
        </AuthProvider>
      </RouterProvider>
    </ThemeProvider>
  );
}
