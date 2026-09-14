/**
 * ShoppingListPage.jsx — Liste de courses autonome
 *
 * Deux modes :
 *   ▦ Planning  → lit alim_plan_weekly (localStorage) et génère depuis le plan
 *   🍽️ Recettes → recherche + sélection libre de recettes
 *
 * La dernière liste générée est persistée en localStorage jusqu'à
 * ce que l'utilisateur clique « Recalculer ».
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useToast } from '../ToastContext';
import { planning as planningApi, recipes as recipesApi } from '../api';
import { navigate } from '../Router';
import PriceEditInline from '../components/PriceEditInline';

// ── Constantes ────────────────────────────────────────────────────────────────

const PLAN_KEY         = 'alim_plan_weekly';
const CHECKED_KEY      = 'alim_sl_checked';
const SHOPPING_KEY     = 'alim_sl_shopping';          // persistance liste
const FRIGO_QTYS_KEY   = 'alim_shopping_frigo_qtys';  // partagé avec PlanningPage
const FRIGO_SUF_KEY    = 'alim_shopping_frigo_sufficient';

const DAYS_KEY   = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche'];
const DAYS_FR    = ['Lun','Mar','Mer','Jeu','Ven','Sam','Dim'];
const MEAL_ORDER = ['breakfast','lunch','dinner'];
const MEAL_ICONS = { breakfast:'🌅', lunch:'☀️', dinner:'🌙' };

const CAT_ICONS = {
  'légumes':'🥦','légumineuses':'🫘','protéines':'🥩','protéines végétales':'🌱',
  'viandes':'🥩','volaille':'🍗','poissons':'🐟','poissons & fruits de mer':'🦐',
  'produits laitiers':'🧀','alternatives laitières':'🥛','oeufs':'🥚',
  'fruits':'🍎','céréales & féculents':'🌾','noix & graines':'🥜',
  'condiments & sauces':'🫙','épices & aromates':'🌶️','herbes fraîches':'🌿',
  'huiles & matières grasses':'🫒','sucres & édulcorants':'🍯',
  'liquides & bouillons':'🫗','boissons':'🥤',
  'pâtisserie':'🧁','conserves':'🥫','surgelés':'🧊',
  'superaliments':'⚡','fermentés':'🧫','levures & poudres':'🧂',
  'additifs':'🧪','alcools':'🍷','autre':'📦',
};

// ── LocalStorage helpers ──────────────────────────────────────────────────────

const _ls = {
  get: (k, fb) => { try { const r = localStorage.getItem(k); return r ? JSON.parse(r) : fb; } catch { return fb; } },
  set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* localStorage indisponible */ } },
  del: (k)    => { try { localStorage.removeItem(k); } catch { /* localStorage indisponible */ } },
};

function loadFrigo() {
  // alim_frigo_selected est un tableau de strings (Set sérialisé depuis FrigoPage)
  const raw = _ls.get('alim_frigo_selected', []);
  return new Set(Array.isArray(raw) ? raw : []);
}

function loadPlan() {
  return _ls.get(PLAN_KEY, null);
}

function planHasRecipes(plan) {
  if (!plan) return false;
  return DAYS_KEY.some(dk => MEAL_ORDER.some(m => (plan[dk]?.[m]?.recipes?.length || 0) > 0));
}

function getPlanSummary(plan) {
  if (!plan) return [];
  return DAYS_KEY.map((dk, i) => {
    const counts = {};
    let total = 0;
    for (const m of MEAL_ORDER) {
      const n = plan[dk]?.[m]?.recipes?.length || 0;
      if (n > 0) { counts[m] = n; total += n; }
    }
    return { key: dk, label: DAYS_FR[i], counts, total };
  });
}

function planToShoppingFormat(plan) {
  const out = {};
  for (const dk of DAYS_KEY) {
    out[dk] = {};
    let i = 0;
    for (const m of MEAL_ORDER) {
      const slot = plan[dk]?.[m];
      if (!slot || slot.skip) continue;
      for (const r of (slot.recipes || [])) {
        if (r?.id) out[dk][`${m}_${i++}`] = { id: r.id, title: r.title_fr || r.title || '' };
      }
    }
  }
  return out;
}

function fridgeMatchesIng(fid, rid) {
  const f = fid.toLowerCase(), r = rid.toLowerCase();
  if (f === r) return true;
  if (r.startsWith(f + '/') || r.startsWith(f + '_')) return true;
  if (r.endsWith('_' + f)) return true;
  const parts = r.split('/');
  if (parts.length > 1) { const l = parts[parts.length - 1]; if (l === f || l.startsWith(f + '_')) return true; }
  return false;
}

function _fmtNet(value, unit) {
  if (value == null) return null;
  const v = value === Math.round(value) ? Math.round(value) : Math.round(value * 10) / 10;
  const label = { g:'g', ml:'ml', kg:'kg', piece:'pièce', pieces:'pièces',
    pinch:'pincée', leaf:'feuille', tbsp:'c. à s.', tsp:'c. à c.' };
  return `${v} ${label[unit] || unit}`;
}

// ── ShoppingCategory ──────────────────────────────────────────────────────────

function ShoppingCategory({ cat, items, checked, fridgeIds, fridgeQtys, fridgeSufficient,
                             onFridgeQtyChange, onFridgeSufficient, onToggle, onItemPriceUpdate }) {
  const icon = CAT_ICONS[cat.toLowerCase()] || '📦';

  const doneCount = items.filter(i => {
    const inFrigo = [...fridgeIds].some(f => fridgeMatchesIng(f, i.ingredient));
    if (!inFrigo) return checked.has(i.ingredient);
    if (fridgeSufficient.has(i.ingredient)) return true;
    const fQty = fridgeQtys[i.ingredient] || 0;
    return i.qty_value != null ? fQty >= i.qty_value : false;
  }).length;

  return (
    <div className={`shopping-category${doneCount === items.length ? ' shopping-category--done' : ''}`}>
      <div className="shopping-cat-header">
        <span className="shopping-cat-icon">{icon}</span>
        <span className="shopping-cat-label">{cat}</span>
        <span className="shopping-cat-count">{doneCount}/{items.length}</span>
      </div>
      <ul className="shopping-items">
        {items.map(item => {
          const id         = item.ingredient;
          const inFrigo    = [...fridgeIds].some(f => fridgeMatchesIng(f, id));
          const sufficient = inFrigo && fridgeSufficient.has(id);
          const fQty       = inFrigo && !sufficient ? (fridgeQtys[id] || 0) : 0;
          const netValue   = sufficient ? 0 : (item.qty_value != null ? Math.max(0, item.qty_value - fQty) : item.qty_value);
          const fullyCovered = sufficient || (inFrigo && item.qty_value != null && fQty >= item.qty_value);
          const isDone     = checked.has(id) || fullyCovered;
          const netStr     = !sufficient && netValue != null && inFrigo && fQty > 0
            ? _fmtNet(netValue, item.qty_unit) : null;

          return (
            <li key={id} className={`shopping-item${isDone ? ' shopping-item--checked' : ''}${inFrigo ? ' shopping-item--frigo' : ''}`}>
              <div className="shopping-item-label">
                <input type="checkbox" className="shopping-item-check" checked={isDone}
                  onChange={() => !fullyCovered && onToggle(id)} disabled={fullyCovered} />
                <span className="shopping-item-name">{item.name_fr || id.replace(/_/g, ' ')}</span>
                <span className="shopping-item-qty-wrap">
                  {sufficient
                    ? <span className="shopping-item-qty shopping-item-qty--net">✓ suffisant</span>
                    : netStr
                      ? <><span className="shopping-item-qty shopping-item-qty--net">à acheter : {netStr}</span>
                          <span className="shopping-item-qty shopping-item-qty--orig">{item.qty_str}</span></>
                      : item.qty_str
                        ? <span className="shopping-item-qty">{item.qty_str}</span>
                        : item.occurrences > 1 && <span className="shopping-item-qty">×{item.occurrences}</span>
                  }
                  {!isDone && (item.price_unknown
                    ? <span className="shopping-price-unknown">⚠ prix inconnu</span>
                    : <PriceEditInline item={item} onSaved={updated => onItemPriceUpdate?.(updated)} />
                  )}
                </span>
              </div>
              {inFrigo && (
                <div className="shopping-frigo-row">
                  <label className="shopping-frigo-sufficient">
                    <input type="checkbox" checked={sufficient} onChange={() => onFridgeSufficient(id)} />
                    En stock ✓
                  </label>
                  {!sufficient && <>
                    <span className="shopping-frigo-sep">ou</span>
                    <span className="shopping-frigo-label">quantité :</span>
                    <input type="number" min="0" step="any" className="shopping-frigo-input" placeholder="0"
                      value={fridgeQtys[id] != null ? fridgeQtys[id] : ''}
                      onChange={e => onFridgeQtyChange(id, e.target.value === '' ? 0 : parseFloat(e.target.value) || 0)} />
                    {item.qty_unit && <span className="shopping-frigo-unit">{item.qty_unit}</span>}
                    {fullyCovered && !sufficient && <span className="shopping-frigo-ok">✓ couvert</span>}
                  </>}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

// ── ShoppingResult ────────────────────────────────────────────────────────────

function ShoppingResult({ shopping, checked, fridgeIds, fridgeQtys, fridgeSufficient,
                          onFridgeQtyChange, onFridgeSufficient, onToggle, onClearAll,
                          onReset, onRecalculate, recalcLoading, onItemPriceUpdate }) {
  const { by_category, estimated_cost, n_recipes } = shopping;
  const allItems  = shopping.items || [];
  const nUnknown  = shopping.n_unknown_price || 0;
  const total     = allItems.length;
  const nChecked  = allItems.filter(i => checked.has(i.ingredient)).length;
  const nFridge   = allItems.filter(i => [...fridgeIds].some(f => fridgeMatchesIng(f, i.ingredient))).length;
  const done      = nChecked + nFridge;
  const [copyDone, setCopyDone]     = useState(false);
  const [pantryOpen, setPantryOpen] = useState(true);

  const pantryItems = allItems.filter(i => i.pantry && ![...fridgeIds].some(f => fridgeMatchesIng(f, i.ingredient)));

  // Items nets pour impression + partage
  const netItems = allItems.map(item => {
    const id         = item.ingredient;
    const inFrigo    = [...fridgeIds].some(f => fridgeMatchesIng(f, id));
    const sufficient = inFrigo && fridgeSufficient.has(id);
    const fQty       = inFrigo && !sufficient ? (fridgeQtys[id] || 0) : 0;
    const netValue   = sufficient ? 0 : (item.qty_value != null ? Math.max(0, item.qty_value - fQty) : item.qty_value);
    return { ...item, netValue, netQtyStr: netValue != null ? _fmtNet(netValue, item.qty_unit) : item.qty_str };
  }).filter(i => !checked.has(i.ingredient) && i.netValue !== 0);

  const netByCat = {};
  for (const item of netItems) {
    const cat = Object.entries(by_category).find(([, its]) => its.some(x => x.ingredient === item.ingredient))?.[0] || 'Autre';
    if (!netByCat[cat]) netByCat[cat] = [];
    netByCat[cat].push(item);
  }

  function buildShareText() {
    const lines = [`🛒 Liste de courses — ${n_recipes} recette${n_recipes > 1 ? 's' : ''}\n`];
    const pantryToBuy = pantryItems.filter(i =>
      !checked.has(i.ingredient) && !fridgeSufficient.has(i.ingredient) &&
      !(i.qty_value != null && (fridgeQtys[i.ingredient] || 0) >= i.qty_value)
    );
    if (pantryToBuy.length > 0) {
      lines.push('\n🗄️ Placard (à vérifier)');
      for (const item of pantryToBuy) {
        const qty   = item.qty_str || '';
        const price = !item.price_unknown && item.package_label ? ` [${item.package_label} · ${item.price_eur?.toFixed(2)} €]` : '';
        lines.push(`  ☐ ${item.name_fr || item.ingredient.replace(/_/g, ' ')}${qty ? ' — ' + qty : ''}${price}`);
      }
    }
    for (const [cat, catItems] of Object.entries(netByCat)) {
      lines.push(`\n${CAT_ICONS[cat.toLowerCase()] || '📦'} ${cat}`);
      for (const item of catItems) {
        const qty   = item.netQtyStr || (item.occurrences > 1 ? `×${item.occurrences}` : '');
        const price = !item.price_unknown && item.package_label ? ` [${item.package_label} · ${item.price_eur?.toFixed(2)} €]` : '';
        lines.push(`  ☐ ${item.name_fr || item.ingredient.replace(/_/g, ' ')}${qty ? ' — ' + qty : ''}${price}`);
      }
    }
    const totalCost = [...netItems, ...pantryItems.filter(i =>
      !checked.has(i.ingredient) && !fridgeSufficient.has(i.ingredient))
    ].reduce((s, i) => s + (i.price_eur || 0), 0);
    if (totalCost > 0) lines.push(`\n💶 Total estimé : ~${totalCost.toFixed(2)} €`);
    if (nFridge > 0) lines.push('◈ Quantités du frigo déjà déduites.');
    return lines.join('\n');
  }

  const handleShare = async () => {
    const text = buildShareText();
    if (navigator.share) {
      try { await navigator.share({ title: '🛒 Liste de courses', text }); } catch { /* partage annulé */ }
    } else {
      try {
        await navigator.clipboard.writeText(text);
        setCopyDone(true);
        setTimeout(() => setCopyDone(false), 2500);
      } catch { /* presse-papier refusé par le navigateur */ }
    }
  };

  return (
    <div className="shopping-view">
      {/* Header */}
      <div className="shopping-header no-print">
        <div className="shopping-stats">
          <div className="shopping-stat"><span className="shopping-stat-val">{n_recipes}</span><span className="shopping-stat-lbl">recette{n_recipes > 1 ? 's' : ''}</span></div>
          <div className="shopping-stat"><span className="shopping-stat-val">{total}</span><span className="shopping-stat-lbl">articles</span></div>
          <div className="shopping-stat shopping-stat--done"><span className="shopping-stat-val">{done}/{total}</span><span className="shopping-stat-lbl">obtenus</span></div>
          {nFridge > 0 && <div className="shopping-stat shopping-stat--frigo"><span className="shopping-stat-val">{nFridge}</span><span className="shopping-stat-lbl">◈ frigo</span></div>}
          {estimated_cost > 0 && <div className="shopping-stat shopping-stat--cost"><span className="shopping-stat-val">~{estimated_cost.toFixed(2)} €</span><span className="shopping-stat-lbl">estimé</span></div>}
          {nUnknown > 0 && <div className="shopping-stat shopping-stat--warn" title={`${nUnknown} ingrédient(s) sans prix`}><span className="shopping-stat-val">⚠ {nUnknown}</span><span className="shopping-stat-lbl">prix inconnus</span></div>}
        </div>
        <div className="shopping-progress-wrap">
          <div className="shopping-progress-bar" style={{ width: total > 0 ? `${Math.round((done / total) * 100)}%` : '0%' }} />
        </div>
        <div className="shopping-header-actions">
          {nChecked > 0 && <button className="shopping-clear-btn" onClick={onClearAll}>Tout décocher</button>}
          <button className="shopping-share-btn" onClick={handleShare} title={navigator.share ? 'Partager' : 'Copier dans le presse-papier'}>
            {copyDone ? '✓ Copié !' : navigator.share ? '↗ Partager' : '⎘ Copier'}
          </button>
          <button className="shopping-print-btn" onClick={() => window.print()}>🖨️ Imprimer</button>
          <button className="sl-recalc-btn" onClick={onRecalculate} disabled={recalcLoading} title="Recalculer depuis le planning ou la sélection actuelle">
            {recalcLoading ? '⏳' : '↺'} Recalculer
          </button>
          <button className="sl-action-btn sl-action-btn--reset" onClick={onReset}>✕ Modifier</button>
        </div>
      </div>

      {/* Section Placard */}
      {pantryItems.length > 0 && (
        <div className="shopping-pantry-section no-print">
          <button className="shopping-pantry-toggle" onClick={() => setPantryOpen(o => !o)}>
            <span>🗄️ Placard <span className="shopping-pantry-count">{pantryItems.length} article{pantryItems.length > 1 ? 's' : ''}</span></span>
            <span className="shopping-pantry-chevron">{pantryOpen ? '▾' : '▸'}</span>
          </button>
          {pantryOpen && (
            <div className="shopping-pantry-list">
              {pantryItems.map(item => {
                const id           = item.ingredient;
                const sufficient   = fridgeSufficient.has(id);
                const fQty         = !sufficient ? (fridgeQtys[id] || 0) : 0;
                const fullyCovered = sufficient || (item.qty_value != null && fQty >= item.qty_value);
                const isDone       = checked.has(id) || fullyCovered;
                return (
                  <div key={id} className={`shopping-pantry-item${isDone ? ' shopping-pantry-item--done' : ''}`}>
                    <div className="shopping-item-label">
                      <input type="checkbox" className="shopping-item-check" checked={isDone}
                        onChange={() => !fullyCovered && onToggle(id)} disabled={fullyCovered} />
                      <span className="shopping-item-name">{item.name_fr || id.replace(/_/g, ' ')}</span>
                      <span className="shopping-item-qty-wrap">
                        {sufficient
                          ? <span className="shopping-item-qty shopping-item-qty--net">✓ suffisant</span>
                          : item.qty_str && <span className="shopping-item-qty">{item.qty_str}</span>
                        }
                        {!isDone && (item.price_unknown
                          ? <span className="shopping-price-unknown">⚠ prix inconnu</span>
                          : !isDone && <PriceEditInline item={item} onSaved={updated => onItemPriceUpdate?.(updated)} />
                        )}
                      </span>
                    </div>
                    <div className="shopping-frigo-row">
                      <label className="shopping-frigo-sufficient">
                        <input type="checkbox" checked={sufficient} onChange={() => onFridgeSufficient(id)} />
                        En stock ✓
                      </label>
                      {!sufficient && <>
                        <span className="shopping-frigo-sep">ou</span>
                        <span className="shopping-frigo-label">quantité :</span>
                        <input type="number" min="0" step="any" className="shopping-frigo-input" placeholder="0"
                          value={fridgeQtys[id] != null ? fridgeQtys[id] : ''}
                          onChange={e => onFridgeQtyChange(id, e.target.value === '' ? 0 : parseFloat(e.target.value) || 0)} />
                        {item.qty_unit && <span className="shopping-frigo-unit">{item.qty_unit}</span>}
                      </>}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Liste principale */}
      <div className="shopping-categories no-print">
        {Object.entries(by_category).map(([cat, catItems]) => (
          <ShoppingCategory key={cat} cat={cat} items={catItems} checked={checked}
            fridgeIds={fridgeIds} fridgeQtys={fridgeQtys} fridgeSufficient={fridgeSufficient}
            onFridgeQtyChange={onFridgeQtyChange} onFridgeSufficient={onFridgeSufficient}
            onToggle={onToggle} onItemPriceUpdate={onItemPriceUpdate} />
        ))}
      </div>

      {/* Vue impression */}
      <div className="shopping-print-view print-only">
        <h2 className="shopping-print-title">🛒 Liste de courses</h2>
        <p className="shopping-print-sub">{n_recipes} recette{n_recipes > 1 ? 's' : ''} · {netItems.length} article{netItems.length > 1 ? 's' : ''} à acheter</p>
        {pantryItems.filter(i => !checked.has(i.ingredient) && !fridgeSufficient.has(i.ingredient)).length > 0 && (
          <div className="shopping-print-cat">
            <div className="shopping-print-cat-label">🗄️ Placard (à vérifier)</div>
            <ul className="shopping-print-items">
              {pantryItems.filter(i => !checked.has(i.ingredient) && !fridgeSufficient.has(i.ingredient)).map(item => (
                <li key={item.ingredient} className="shopping-print-item">
                  <span className="shopping-print-item-check">☐</span>
                  <span className="shopping-print-item-name">{item.name_fr || item.ingredient.replace(/_/g, ' ')}</span>
                  <span className="shopping-print-item-qty">{item.qty_str || ''}</span>
                  {!item.price_unknown && item.package_label && <span className="shopping-print-item-price">{item.package_label} · {item.price_eur?.toFixed(2)} €</span>}
                </li>
              ))}
            </ul>
          </div>
        )}
        {Object.entries(netByCat).map(([cat, catItems]) => (
          <div key={cat} className="shopping-print-cat">
            <div className="shopping-print-cat-label">{CAT_ICONS[cat.toLowerCase()] || '📦'} {cat}</div>
            <ul className="shopping-print-items">
              {catItems.map(item => (
                <li key={item.ingredient} className="shopping-print-item">
                  <span className="shopping-print-item-check">☐</span>
                  <span className="shopping-print-item-name">{item.name_fr || item.ingredient.replace(/_/g, ' ')}</span>
                  <span className="shopping-print-item-qty">{item.netQtyStr || (item.occurrences > 1 ? `×${item.occurrences}` : '')}</span>
                  {!item.price_unknown && item.package_label && <span className="shopping-print-item-price">{item.package_label} · {item.price_eur?.toFixed(2)} €</span>}
                </li>
              ))}
            </ul>
          </div>
        ))}
        {estimated_cost > 0 && <p className="shopping-print-total">💶 Total estimé : ~{estimated_cost.toFixed(2)} €</p>}
        {nFridge > 0 && <p className="shopping-print-frigo-note">◈ Quantités déjà disponibles dans votre frigo déduites.</p>}
      </div>
    </div>
  );
}

// ── PlanMode ──────────────────────────────────────────────────────────────────

function PlanMode({ onResult }) {
  const [plan]    = useState(loadPlan);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState(null);
  const summary = getPlanSummary(plan);
  const hasPlan = planHasRecipes(plan);

  const generate = async () => {
    setLoading(true); setError(null);
    try {
      const data = await planningApi.shoppingList({ plan: planToShoppingFormat(plan) });
      onResult(data);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  if (!plan || !hasPlan) {
    return (
      <div className="sl-empty-state">
        <span className="sl-empty-icon">▦</span>
        <p className="sl-empty-title">Aucun planning trouvé</p>
        <p className="sl-empty-sub">Générez d'abord votre plan hebdomadaire pour obtenir une liste de courses.</p>
        <button className="frigo-search-btn" style={{ maxWidth: 260 }} onClick={() => navigate('/planning')}>
          ▦ Aller au planning
        </button>
      </div>
    );
  }

  return (
    <div className="sl-plan-mode">
      <div className="sl-plan-summary">
        {summary.map(({ key, label, counts, total }) => (
          <div key={key} className={`sl-day-badge${total > 0 ? ' sl-day-badge--active' : ''}`}>
            <span className="sl-day-label">{label}</span>
            {total > 0 && (
              <span className="sl-day-meals">
                {Object.entries(counts).map(([m]) => (
                  <span key={m} className="sl-day-meal-dot">{MEAL_ICONS[m]}</span>
                ))}
              </span>
            )}
          </div>
        ))}
      </div>
      {error && <div className="state-msg state-msg--error" style={{ marginBottom: 12 }}>{error}</div>}
      <div className="sl-generate-area">
        <p className="sl-generate-hint">
          {summary.reduce((s, d) => s + d.total, 0)} recette(s) dans votre planning — générez la liste de courses complète.
        </p>
        <button className="frigo-search-btn" onClick={generate} disabled={loading} style={{ maxWidth: 300 }}>
          {loading ? '⏳ Génération…' : '🛒 Générer la liste de courses'}
        </button>
      </div>
    </div>
  );
}

// ── RecipesMode ───────────────────────────────────────────────────────────────

function RecipesMode({ onResult }) {
  const toast = useToast();
  const [query,     setQuery]     = useState('');
  const [results,   setResults]   = useState([]);
  const [searching, setSearching] = useState(false);
  const [selected,  setSelected]  = useState([]);
  const [loading,   setLoading]   = useState(false);
  const [error,     setError]     = useState(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (!query.trim()) { setResults([]); return; }
    const t = setTimeout(async () => {
      setSearching(true);
      try {
        const data = await recipesApi.search({ query: query.trim(), limit: 12 });
        setResults(Array.isArray(data) ? data : (data?.results || data?.recipes || []));
      } catch (err) {
        toast(`Recherche impossible : ${err.message || 'erreur réseau'}`, 'error');
      }
      finally { setSearching(false); }
    }, 300);
    return () => clearTimeout(t);
  }, [query, toast]);

  const addRecipe = (r) => {
    if (selected.some(s => s.id === r.id)) return;
    setSelected(prev => [...prev, { id: r.id, title: r.titles?.fr || r.title_fr || r.title || r.id }]);
    setQuery(''); setResults([]); inputRef.current?.focus();
  };

  const generate = async () => {
    if (!selected.length) return;
    setLoading(true); setError(null);
    try {
      const data = await planningApi.shoppingListFromRecipes({ recipe_ids: selected.map(r => r.id) });
      onResult(data);
    } catch (err) { setError(err.message); }
    finally { setLoading(false); }
  };

  return (
    <div className="sl-recipes-mode">
      <div className="sl-search-wrap">
        <div className="sl-search-input-row">
          <span className="sl-search-icon">🔍</span>
          <input ref={inputRef} className="sl-search-input" placeholder="Chercher une recette à ajouter…"
            value={query} onChange={e => setQuery(e.target.value)} autoComplete="off" />
          {query && <button className="sl-search-clear" onClick={() => { setQuery(''); setResults([]); }}>✕</button>}
        </div>
        {(results.length > 0 || searching) && (
          <div className="sl-search-results">
            {searching && <div className="sl-search-loading">Recherche…</div>}
            {!searching && results.map(r => {
              const title     = r.titles?.fr || r.title_fr || r.title || r.id;
              const isAlready = selected.some(s => s.id === r.id);
              return (
                <button key={r.id} className={`sl-search-result${isAlready ? ' sl-search-result--added' : ''}`}
                  onClick={() => !isAlready && addRecipe(r)} disabled={isAlready}>
                  <span className="sl-search-result-title">{title}</span>
                  {isAlready ? <span className="sl-search-result-badge">✓</span>
                             : <span className="sl-search-result-add">+ Ajouter</span>}
                </button>
              );
            })}
          </div>
        )}
      </div>
      {selected.length > 0 ? (
        <div className="sl-selected-wrap">
          <div className="sl-selected-header">
            <span className="sl-selected-count">{selected.length} recette{selected.length > 1 ? 's' : ''} sélectionnée{selected.length > 1 ? 's' : ''}</span>
            <button className="sl-selected-clear" onClick={() => setSelected([])}>Tout effacer</button>
          </div>
          <ul className="sl-selected-list">
            {selected.map(r => (
              <li key={r.id} className="sl-sel-chip">
                <span className="sl-sel-chip-title">{r.title}</span>
                <button className="sl-sel-chip-remove" onClick={() => setSelected(p => p.filter(x => x.id !== r.id))}>✕</button>
              </li>
            ))}
          </ul>
          {error && <div className="state-msg state-msg--error" style={{ marginBottom: 12 }}>{error}</div>}
          <div className="sl-generate-area">
            <button className="frigo-search-btn" onClick={generate} disabled={loading} style={{ maxWidth: 300 }}>
              {loading ? '⏳ Génération…' : '🛒 Générer la liste de courses'}
            </button>
          </div>
        </div>
      ) : (
        <div className="sl-empty-state sl-empty-state--inline">
          <span className="sl-empty-icon">🍽️</span>
          <p className="sl-empty-sub">Recherchez et ajoutez des recettes pour générer votre liste.</p>
        </div>
      )}
    </div>
  );
}

// ── Page principale ───────────────────────────────────────────────────────────

export default function ShoppingListPage() {
  const toast = useToast();
  const [mode,     setMode]     = useState('plan');
  const [shopping, setShopping] = useState(() => _ls.get(SHOPPING_KEY, null));
  const [checked,  setChecked]  = useState(() => new Set(_ls.get(CHECKED_KEY, [])));
  const [fridgeIds]             = useState(loadFrigo);
  const [fridgeQtys,       setFridgeQtys]       = useState(() => _ls.get(FRIGO_QTYS_KEY, {}));
  const [fridgeSufficient, setFridgeSufficient] = useState(() => new Set(_ls.get(FRIGO_SUF_KEY, [])));
  const [recalcLoading, setRecalcLoading] = useState(false);
  // Pour pouvoir recalculer : garde la dernière source en mémoire
  const lastSourceRef = useRef(null);

  // Persistance
  useEffect(() => { _ls.set(CHECKED_KEY, [...checked]); }, [checked]);
  useEffect(() => { if (shopping) _ls.set(SHOPPING_KEY, shopping); else _ls.del(SHOPPING_KEY); }, [shopping]);
  useEffect(() => { _ls.set(FRIGO_QTYS_KEY, fridgeQtys); }, [fridgeQtys]);
  useEffect(() => { _ls.set(FRIGO_SUF_KEY, [...fridgeSufficient]); }, [fridgeSufficient]);

  const toggleChecked    = useCallback(id => setChecked(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; }), []);
  const setFridgeQty     = useCallback((id, val) => setFridgeQtys(p => ({ ...p, [id]: val })), []);
  const toggleFridgeSuf  = useCallback(id => setFridgeSufficient(p => { const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n; }), []);

  const handleItemPriceUpdate = useCallback(updated => {
    setShopping(prev => {
      if (!prev) return prev;
      const patch    = arr => arr.map(i => i.ingredient === updated.ingredient ? { ...i, ...updated } : i);
      const patchCat = by_cat => Object.fromEntries(
        Object.entries(by_cat).map(([cat, its]) => [cat, patch(its)])
      );
      return { ...prev, items: patch(prev.items || []), by_category: patchCat(prev.by_category || {}) };
    });
  }, []);

  const handleResult = (data, source) => {
    if (source) lastSourceRef.current = source;
    setShopping(data);
    setChecked(new Set());
  };

  const handleReset = () => { setShopping(null); lastSourceRef.current = null; };

  const handleRecalculate = async () => {
    const src = lastSourceRef.current;
    if (!src) return;
    setRecalcLoading(true);
    try {
      let data;
      if (src.type === 'plan') {
        data = await planningApi.shoppingList({ plan: planToShoppingFormat(loadPlan()) });
      } else {
        data = await planningApi.shoppingListFromRecipes({ recipe_ids: src.ids });
      }
      setShopping(data); // garde les coches existantes
    } catch (err) {
      toast(`Liste de courses non mise à jour : ${err.message || 'erreur réseau'}`, 'error');
    }
    finally { setRecalcLoading(false); }
  };

  const switchMode = (m) => { setMode(m); if (!shopping) return; };

  return (
    <div className="page-shopping">
      <div className="page-header">
        <h1 className="page-title"><span className="page-icon">🛒</span> Liste de courses</h1>
        <p className="page-sub">Depuis votre planning hebdomadaire ou une sélection libre de recettes.</p>
      </div>

      {/* Sélecteur de mode — visible seulement sans liste active */}
      {!shopping && (
        <div className="sl-mode-bar">
          <button className={`sl-mode-btn${mode === 'plan' ? ' sl-mode-btn--active' : ''}`} onClick={() => switchMode('plan')}>
            <span>▦</span> Depuis le planning
          </button>
          <button className={`sl-mode-btn${mode === 'recipes' ? ' sl-mode-btn--active' : ''}`} onClick={() => switchMode('recipes')}>
            <span>🍽️</span> Sélection de recettes
          </button>
        </div>
      )}

      <div className="sl-content">
        {shopping ? (
          <ShoppingResult
            shopping={shopping}
            checked={checked}
            fridgeIds={fridgeIds}
            fridgeQtys={fridgeQtys}
            fridgeSufficient={fridgeSufficient}
            onFridgeQtyChange={setFridgeQty}
            onFridgeSufficient={toggleFridgeSuf}
            onToggle={toggleChecked}
            onClearAll={() => setChecked(new Set())}
            onReset={handleReset}
            onRecalculate={handleRecalculate}
            recalcLoading={recalcLoading}
            onItemPriceUpdate={handleItemPriceUpdate}
          />
        ) : mode === 'plan' ? (
          <PlanMode onResult={(data) => handleResult(data, { type: 'plan' })} />
        ) : (
          <RecipesMode onResult={(data, ids) => handleResult(data, { type: 'recipes', ids })} />
        )}
      </div>
    </div>
  );
}
