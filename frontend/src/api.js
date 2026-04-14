/**
 * api.js — Couche d'accès ALIM v6
 *
 * Centralise : base URL, headers, token JWT, gestion d'erreurs.
 * Toutes les routes backend passent ici — jamais de fetch() nu dans les composants.
 */

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// ── Token JWT ────────────────────────────────────────────────────────────────

export const getToken = () => localStorage.getItem('alim_token');
export const setToken = (t) => t ? localStorage.setItem('alim_token', t) : localStorage.removeItem('alim_token');

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── Fetch de base ─────────────────────────────────────────────────────────────

async function request(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
  };
  if (body !== null) opts.body = JSON.stringify(body);

  const res = await fetch(`${BASE}${path}`, opts);

  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {}
    throw new Error(detail);
  }

  // 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

const get  = (path)        => request('GET',  path);
const post = (path, body)  => request('POST', path, body);

// ── Auth ──────────────────────────────────────────────────────────────────────

export const auth = {
  login:          (email, password) => post('/auth/login',    { email, password }),
  register:       (email, password, name) => post('/auth/register', { email, password, name }),
  me:             ()                => get('/auth/me'),
  forgotPassword: (email)           => post('/auth/forgot-password', { email }),
  resetPassword:  (token, new_password) => post('/auth/reset-password', { token, new_password }),
};

// ── Recipe store (cache en mémoire) ──────────────────────────────────────────
// Évite un aller-retour réseau quand on navigue depuis la grille.
// Les IDs dataset sont des strings (ex: "dip_baba_ghanoush_dbd030").

const _store = new Map(); // id → recipe object

export const recipeStore = {
  set:    (recipe) => { if (recipe?.id) _store.set(String(recipe.id), recipe); },
  setAll: (list)   => { list.forEach(r => recipeStore.set(r)); },
  get:    (id)     => _store.get(String(id)) || null,
};

// ── Recettes ──────────────────────────────────────────────────────────────────

async function _listAndStore(path) {
  const data = await get(path);
  const list = Array.isArray(data) ? data : (data?.results || data?.recipes || []);
  recipeStore.setAll(list);
  return data;
}

export const recipes = {
  list: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== '')
    ).toString();
    return _listAndStore(`/recettes${qs ? '?' + qs : ''}`);
  },
  search: async (payload) => {
    const data = await post('/recettes/recherche', payload);
    const list = Array.isArray(data) ? data : (data?.results || data?.recipes || []);
    recipeStore.setAll(list);
    return data;
  },
  // byId : cherche d'abord dans le store, puis tente l'API avec l'id string
  byId: async (id) => {
    const cached = recipeStore.get(id);
    if (cached) return cached;
    // L'API backend attend un int — on tente quand même (marche si l'id est numérique)
    try {
      const data = await get(`/recettes/${encodeURIComponent(id)}`);
      recipeStore.set(data);
      return data;
    } catch {
      // Fallback : chercher via POST recherche avec le titre extrait de l'id
      const query = id.replace(/_[a-z0-9]{6,}$/, '').replace(/_/g, ' ');
      const res = await post('/recettes/recherche', { query, limit: 50 });
      const list = Array.isArray(res) ? res : (res?.results || res?.recipes || []);
      recipeStore.setAll(list);
      const found = list.find(r => String(r.id) === String(id));
      if (found) return found;
      throw new Error('Recette introuvable');
    }
  },
  top:      ()        => get('/recettes/top'),
  similar:  (id)      => get(`/recettes/${encodeURIComponent(id)}/similaires`),
  vegan:    (id)      => post(`/recettes/${encodeURIComponent(id)}/variante`, {}),
  recommend:(payload) => post('/recettes/recommend', payload),
};

// ── Frigo ────────────────────────────────────────────────────────────────────

export const frigo = {
  suggestions: (payload) => post('/frigo/suggestions', payload),
  manquants:   (payload) => post('/frigo/manquants',   payload),
};

// ── Nutrition ─────────────────────────────────────────────────────────────────

export const nutrition = {
  ajrScore:        (payload) => post('/nutrition/ajr_score',        payload),
  detectDeficiencies: (payload) => post('/nutrition/detect_deficiencies', payload),
  cycleScore:      (payload) => post('/nutrition/cycle_score',       payload),
  alerts:          (payload) => post('/nutrition/alerts',            payload),
};

// ── Cycle & Graphe ────────────────────────────────────────────────────────────
export const cycle = {
  getIngredients: (phase) => get(`/recettes/graph/cycle/${phase}`),
};

// ── Planning ──────────────────────────────────────────────────────────────────

export const planning = {
  mealplan:     (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== '')
    ).toString();
    return get(`/planning/mealplan${qs ? '?' + qs : ''}`);
  },
  shoppingList: (payload)     => post('/planning/shopping_list', payload),
  seasonal:     (month)       => get(`/planning/seasonal?month=${month}`),
  exportIcs:    (payload)     => post('/planning/mealplan/export_ics', payload),
};

// ── Profil ────────────────────────────────────────────────────────────────────

export const profile = {
  get:    ()        => get('/profil'),
  update: (payload) => post('/profil/update', payload),
};

// ── Ingrédients ───────────────────────────────────────────────────────────────

export const ingredients = {
  search: (q) => get(`/ingredients/search?q=${encodeURIComponent(q)}`),
  byId:   (id) => get(`/ingredients/${id}`),
};
