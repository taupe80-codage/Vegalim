/**
 * FavoritesPage.jsx — Page "Mes favoris"
 *
 * Affiche les recettes sauvegardées, regroupées par type de plat.
 * Utilise FavoritesContext (localStorage) — fonctionne sans compte.
 */

import { useState } from 'react';
import { useFavorites } from '../FavoritesContext';
import RecipeCard from '../components/RecipeCard';
import { DISH_OPTIONS } from '../constants';
import { navigate } from '../Router';

// Type "Autre" pour les recettes sans dish_type connu
const UNKNOWN_GROUP = { value: '__other__', label: '📦 Autre' };

// Groupe les favoris par dish_type, dans l'ordre de DISH_OPTIONS
function groupByDishType(favorites) {
  const knownValues = new Set(DISH_OPTIONS.map(o => o.value));
  const map = {};

  for (const r of favorites) {
    const key = (r.dish_type && knownValues.has(r.dish_type))
      ? r.dish_type
      : '__other__';
    if (!map[key]) map[key] = [];
    map[key].push(r);
  }

  const groups = [];
  for (const opt of DISH_OPTIONS) {
    if (map[opt.value]?.length) {
      groups.push({ ...opt, recipes: map[opt.value] });
    }
  }
  if (map['__other__']?.length) {
    groups.push({ ...UNKNOWN_GROUP, recipes: map['__other__'] });
  }
  return groups;
}

// ── Composant principal ───────────────────────────────────────────────────────

export default function FavoritesPage() {
  const { favorites, clear } = useFavorites();
  const [confirmClear, setConfirmClear] = useState(false);

  const groups = groupByDishType(favorites);
  const total  = favorites.length;

  const handleClear = () => {
    if (confirmClear) { clear(); setConfirmClear(false); }
    else { setConfirmClear(true); }
  };

  return (
    <div className="page-home" style={{ padding: '0 24px', maxWidth: 1100, margin: '0 auto' }}>

      {/* ── En-tête ── */}
      <div className="page-header" style={{ marginBottom: 32 }}>
        <h1 className="page-title">
          <span className="page-icon">♥</span> Mes favoris
          {total > 0 && (
            <span style={{
              marginLeft: 12, fontSize: 14, fontWeight: 600,
              background: 'var(--grn-dim)', color: 'var(--grn)',
              border: '1px solid rgba(29,107,64,0.3)',
              borderRadius: 20, padding: '2px 10px',
            }}>
              {total} recette{total > 1 ? 's' : ''}
            </span>
          )}
        </h1>
        <p className="page-sub">
          Vos recettes sauvegardées, organisées par type de plat.
          Cliquez sur ♥ sur n'importe quelle carte pour ajouter ou retirer un favori.
        </p>
      </div>

      {/* ── État vide ── */}
      {total === 0 && (
        <div style={{
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', minHeight: 340, gap: 20,
          color: 'var(--mut)', textAlign: 'center',
        }}>
          <span style={{ fontSize: 64, opacity: 0.18 }}>♡</span>
          <div>
            <p style={{ fontSize: 18, fontWeight: 600, color: 'var(--txt2)', marginBottom: 8 }}>
              Aucun favori pour l'instant
            </p>
            <p style={{ fontSize: 14, maxWidth: 360, lineHeight: 1.6 }}>
              Parcourez les recettes et cliquez sur le cœur ♡ pour les sauvegarder ici.
            </p>
          </div>
          <button
            className="frigo-search-btn"
            style={{ width: 'auto', padding: '12px 28px' }}
            onClick={() => navigate('/')}
          >
            Découvrir des recettes →
          </button>
        </div>
      )}

      {/* ── Groupes par type de plat ── */}
      {groups.map(group => (
        <section key={group.value} style={{ marginBottom: 48 }}>
          {/* Titre du groupe */}
          <div style={{
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            marginBottom: 16, paddingBottom: 12,
            borderBottom: '1px solid var(--brd)',
          }}>
            <h2 style={{
              fontSize: 20, fontWeight: 600, margin: 0,
              display: 'flex', alignItems: 'center', gap: 10,
            }}>
              {group.label}
              <span style={{
                fontSize: 12, fontWeight: 600,
                background: 'var(--sur2)', color: 'var(--mut)',
                border: '1px solid var(--brd)',
                borderRadius: 20, padding: '2px 9px',
              }}>
                {group.recipes.length}
              </span>
            </h2>
          </div>

          {/* Grille de recettes */}
          <div className="recipe-grid">
            {group.recipes.map(recipe => (
              <RecipeCard key={recipe.id} recipe={recipe} />
            ))}
          </div>
        </section>
      ))}

      {/* ── Bouton effacer tout ── */}
      {total > 0 && (
        <div style={{
          marginTop: 16, paddingTop: 24,
          borderTop: '1px solid var(--brd)',
          display: 'flex', justifyContent: 'center',
        }}>
          <button
            onClick={handleClear}
            style={{
              background: confirmClear ? 'rgba(179,45,29,0.10)' : 'transparent',
              border: `1px solid ${confirmClear ? 'var(--red)' : 'var(--brd)'}`,
              color: confirmClear ? 'var(--red)' : 'var(--mut)',
              fontSize: 13, fontWeight: 500,
              padding: '8px 20px', borderRadius: 8,
              cursor: 'pointer', fontFamily: 'inherit',
              transition: 'all 0.15s',
            }}
          >
            {confirmClear ? '⚠️ Confirmer la suppression de tous les favoris' : '✕ Effacer tous les favoris'}
          </button>
          {confirmClear && (
            <button
              onClick={() => setConfirmClear(false)}
              style={{
                marginLeft: 8,
                background: 'transparent',
                border: '1px solid var(--brd)',
                color: 'var(--mut)',
                fontSize: 13, padding: '8px 16px', borderRadius: 8,
                cursor: 'pointer', fontFamily: 'inherit',
              }}
            >
              Annuler
            </button>
          )}
        </div>
      )}
    </div>
  );
}
