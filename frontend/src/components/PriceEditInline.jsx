/**
 * PriceEditInline — bouton ✏️ + formulaire inline de correction de prix.
 *
 * Props :
 *   item          – objet shopping item (ingredient, package_label, unit_price, n_packages, price_eur)
 *   onSaved(item) – callback appelé après sauvegarde réussie avec l'item mis à jour
 */
import { useState } from 'react';
import { planning as planningApi, getToken } from '../api';

export default function PriceEditInline({ item, onSaved }) {
  const [open,    setOpen]    = useState(false);
  const [value,   setValue]   = useState('');
  const [saving,  setSaving]  = useState(false);
  const [error,   setError]   = useState(null);

  // Correction réservée aux comptes connectés (le catalogue de prix est partagé)
  if (!item || item.price_unknown || !item.package_label || !getToken()) return null;

  const handleOpen = () => {
    setValue(item.unit_price != null ? String(item.unit_price) : String(item.price_eur || ''));
    setError(null);
    setOpen(true);
  };

  const handleCancel = () => { setOpen(false); setError(null); };

  const handleSave = async () => {
    const newPrice = parseFloat(value);
    if (!newPrice || newPrice <= 0) { setError('Prix invalide'); return; }
    setSaving(true); setError(null);
    try {
      await planningApi.updatePrice(item.ingredient, item.package_label, newPrice);
      // Mise à jour locale : recalcul prix total = n_packages × nouveau_prix_unitaire
      const n          = item.n_packages || 1;
      const updatedItem = {
        ...item,
        unit_price: newPrice,
        price_eur:  Math.round(n * newPrice * 100) / 100,
      };
      setOpen(false);
      onSaved?.(updatedItem);
    } catch (e) {
      setError(e?.message || 'Erreur lors de la sauvegarde');
    } finally {
      setSaving(false);
    }
  };

  if (open) {
    return (
      <span className="price-edit-form" onClick={e => e.stopPropagation()}>
        <span className="price-edit-pkg">{item.package_label.split('× ').pop()}</span>
        <input
          type="number" min="0.01" step="0.01"
          className="price-edit-input"
          value={value}
          onChange={e => { setValue(e.target.value); setError(null); }}
          onKeyDown={e => { if (e.key === 'Enter') handleSave(); if (e.key === 'Escape') handleCancel(); }}
          autoFocus
        />
        <span className="price-edit-currency">€</span>
        <button className="price-edit-confirm" onClick={handleSave} disabled={saving} title="Valider">
          {saving ? '…' : '✓'}
        </button>
        <button className="price-edit-cancel" onClick={handleCancel} title="Annuler">✕</button>
        {error && <span className="price-edit-error">{error}</span>}
      </span>
    );
  }

  return (
    <span className="price-tag-wrap">
      <span className="shopping-price-tag">
        {item.package_label} · {item.price_eur?.toFixed(2)} €
      </span>
      <button className="price-edit-btn" onClick={handleOpen} title="Corriger le prix">✏️</button>
    </span>
  );
}
