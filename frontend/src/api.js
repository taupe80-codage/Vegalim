/**
 * api.js — Couche d'accès ALIM v6
 *
 * Centralise : base URL, headers, token JWT, gestion d'erreurs.
 * Toutes les routes backend passent ici — jamais de fetch() nu dans les composants.
 */

// Vide ou absente : même origine (frontend servi par FastAPI sous /ui, ou
// derrière Caddy). Le mode dev pointe vers uvicorn via .env.development.
const BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '');

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
    } catch { /* corps d'erreur non JSON : on garde « Erreur <status> » */ }
    throw new Error(detail);
  }

  // 204 No Content
  if (res.status === 204) return null;
  return res.json();
}

const get  = (path)        => request('GET',  path);
const post = (path, body)  => request('POST', path, body);
const put  = (path, body)  => request('PUT',  path, body);
const patch = (path, body) => request('PATCH', path, body);

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
  // skip : pagination (paramètre de requête de /recettes/recherche)
  search: async (payload, skip = 0) => {
    const data = await post(`/recettes/recherche${skip ? `?skip=${skip}` : ''}`, payload);
    const list = Array.isArray(data) ? data : (data?.results || data?.recipes || []);
    recipeStore.setAll(list);
    return data;
  },
  // byId : toujours appeler l'API — enrich_one ajoute diet_flags_enriched,
  // nutrition_highlights et d'autres champs absents du store (issu de la liste).
  byId: async (id) => {
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
  // Plats de saison du mois : ids (badge des cartes) + premiers résultats (accueil)
  inSeason: (limit = 6, diet = '') => _listAndStore(`/recettes/de-saison?limit=${limit}${diet ? `&diet=${encodeURIComponent(diet)}` : ''}`),
  similar:  (id, diet = '') => get(`/recettes/${encodeURIComponent(id)}/similaires${diet ? `?diet=${encodeURIComponent(diet)}` : ''}`),
  vegan:    (id)      => post(`/recettes/${encodeURIComponent(id)}/variante`, {}),
  recommend:(payload) => post('/recettes/recommend', payload),
};

// ── Frigo ────────────────────────────────────────────────────────────────────

export const frigo = {
  suggestions: (payload) => post('/frigo/suggestions', payload),
  manquants:   (payload) => post('/frigo/manquants',   payload),
  rapide:      (payload) => post('/frigo/rapide',      payload),
  /** Retourne {covered, uncovered} pour une liste de clés UI */
  coverage:    (keys)    => get(`/frigo/coverage?keys=${keys.join(',')}`),
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
  shoppingList:            (payload) => post('/planning/shopping_list', payload),
  weekBalance:             (payload) => post('/planning/week_balance', payload),
  weekCost:                (payload) => post('/planning/week_cost', payload),
  batchSession:            (payload) => post('/planning/batch_session', payload),
  shoppingListFromRecipes: (payload) => post('/planning/shopping_list_from_recipes', payload),
  updatePrice: (ingredient_key, package_label, new_price) =>
    put(`/planning/prices/${encodeURIComponent(ingredient_key)}`, { package_label, new_price }),
  seasonal:     (month)       => get(`/planning/seasonal?month=${month}`),
  exportIcs:    (payload)     => post('/planning/mealplan/export_ics', payload),
};

// ── Profil ────────────────────────────────────────────────────────────────────

export const profile = {
  get:    ()        => get('/profil/'),   // route déclarée « / » : sans slash → 307
  update: (payload) => post('/profil/update', payload),
  // Consentement RGPD art. 9 : requis pour enregistrer l'objectif ; le révoquer l'efface
  consent: (health_consent) => patch('/profil/consent', { health_consent }),
  // Interactions (compte connecté) : like | unlike | view… — alimentent la personnalisation
  interaction: (recipe_id, action) => post('/profil/interaction', { recipe_id, action }),
  likes:       ()                  => get('/profil/likes'),
};

// ── Ingrédients ───────────────────────────────────────────────────────────────

export const ingredients = {
  search: (q) => get(`/ingredients/search?q=${encodeURIComponent(q)}`),
  byId:   (id) => get(`/ingredients/${id}`),
};
// ── Recettes proposées par les utilisateurs ──────────────────────────────────

const del = (path) => request('DELETE', path);

async function uploadRaw(path, file, method = 'PUT') {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': file.type || 'application/octet-stream', ...authHeaders() },
    body: file,
  });
  if (!res.ok) {
    let detail = `Erreur ${res.status}`;
    try { detail = (await res.json()).detail || detail; } catch { /* corps non JSON */ }
    throw new Error(detail);
  }
  return res.json();
}

// Photos de plats proposées par les membres (relues par la modération)
// ── Recettes modifiées par le membre (ingrédients, quantités) ───────────────
// edits = { base: 'original' | 'vegan', rows: [{ src, orig, ingredient, quantity, unit }] }
const enc = encodeURIComponent;
export const recipeVersions = {
  preview:      (id, edits)      => post(`/recettes/${enc(id)}/personnaliser`, edits),
  replacements: (id, ingredient) => get(`/recettes/${enc(id)}/remplacements?ingredient=${enc(ingredient)}`),
  mine:         ()               => get('/mes-versions'),
  get:          (id)             => get(`/mes-versions/${enc(id)}`),
  save:         (id, edits, servings) => put(`/mes-versions/${enc(id)}`, { ...edits, servings }),
  remove:       (id)             => del(`/mes-versions/${enc(id)}`),
};

export const photoProposals = {
  propose: (recipeId, file, authorName, consent) => uploadRaw(
    `/photo-proposals/${encodeURIComponent(recipeId)}?author_name=${encodeURIComponent(authorName)}&consent=${consent ? 'true' : 'false'}`,
    file, 'POST'),
  forRecipe: (recipeId) => get(`/photo-proposals/recipe/${encodeURIComponent(recipeId)}`),
  mine:      ()         => get('/photo-proposals/mine'),
  remove:    (id)       => del(`/photo-proposals/${encodeURIComponent(id)}`),
  credits:   ()         => get('/photo-proposals/credits'),
  queue:     (status = 'submitted') => get(`/photo-proposals/moderation/queue?status=${status}`),
  approve:   (id, message = '') => post(`/photo-proposals/moderation/${encodeURIComponent(id)}/approve`, { message }),
  reject:    (id, message) => post(`/photo-proposals/moderation/${encodeURIComponent(id)}/reject`, { message }),
  unpublish: (id, message) => post(`/photo-proposals/moderation/${encodeURIComponent(id)}/remove`, { message }),
};

export const contributions = {
  options:  ()                 => get('/contributions/options'),
  analyse:  (data, author_name) => post('/contributions/analyse', { data, author_name }),
  parse:    (text)             => post('/contributions/ingredients/parse', { text }),
  suggest:  (q)                => get(`/contributions/ingredients/suggest?q=${encodeURIComponent(q)}`),
  mine:     ()                 => get('/contributions/mine'),
  create:   (data, author_name) => post('/contributions', { data, author_name }),
  get:      (id)               => get(`/contributions/${encodeURIComponent(id)}`),
  save:     (id, data, author_name) => put(`/contributions/${encodeURIComponent(id)}`, { data, author_name }),
  remove:   (id)               => del(`/contributions/${encodeURIComponent(id)}`),
  discardRevision: (id)        => del(`/contributions/${encodeURIComponent(id)}/revision`),
  preferences: ()              => get('/contributions/preferences'),
  setPreferences: (email_notifications) => put('/contributions/preferences', { email_notifications }),
  submit:   (id, author_name, consent) => post(`/contributions/${encodeURIComponent(id)}/submit`, { author_name, consent }),
  uploadPhoto: (id, file)      => uploadRaw(`/contributions/${encodeURIComponent(id)}/photo`, file),
  deletePhoto: (id)            => del(`/contributions/${encodeURIComponent(id)}/photo`),
  // Modération
  queue:    (status = 'submitted') => get(`/contributions/moderation/queue?status=${status}`),
  review:   (id)               => get(`/contributions/moderation/${encodeURIComponent(id)}`),
  modSave:  (id, data)         => put(`/contributions/moderation/${encodeURIComponent(id)}`, { data }),
  publish:  (id, message = '') => post(`/contributions/moderation/${encodeURIComponent(id)}/publish`, { message }),
  requestChanges: (id, message) => post(`/contributions/moderation/${encodeURIComponent(id)}/request-changes`, { message }),
  reject:   (id, message)      => post(`/contributions/moderation/${encodeURIComponent(id)}/reject`, { message }),
  unpublish:(id, message)      => post(`/contributions/moderation/${encodeURIComponent(id)}/unpublish`, { message }),
};

/** Adresse complète d'une photo servie par l'API (même origine ou VITE_API_URL). */
export const apiUrl = (path) => (path && path.startsWith('/') ? `${BASE}${path}` : path);

// ── Notes et commentaires ────────────────────────────────────────────────────

export const reviews = {
  forRecipe: (id, sort = 'helpful', skip = 0) =>
    get(`/avis/recette/${encodeURIComponent(id)}?sort=${sort}&skip=${skip}&limit=10`),
  save:      (id, payload) => put(`/avis/recette/${encodeURIComponent(id)}`, payload),
  remove:    (id)          => del(`/avis/recette/${encodeURIComponent(id)}`),
  helpful:   (reviewId)    => post(`/avis/${reviewId}/utile`, {}),
  report:    (reviewId, reason) => post(`/avis/${reviewId}/signaler`, { reason }),
  reply:     (reviewId, text) => put(`/avis/${reviewId}/reponse`, { text }),
  deleteReply: (reviewId)  => del(`/avis/${reviewId}/reponse`),
  summaries: (ids)         => post('/avis/resume', { ids }),
  // Modération
  modList:   (status = 'reported') => get(`/avis/moderation?status=${status}`),
  modHide:   (reviewId)    => post(`/avis/moderation/${reviewId}/hide`, {}),
  modRestore:(reviewId)    => post(`/avis/moderation/${reviewId}/restore`, {}),
  modDelete: (reviewId)    => del(`/avis/moderation/${reviewId}`),
  modDeleteReply: (reviewId) => del(`/avis/moderation/${reviewId}/reponse`),
};

// ── Notifications (cloche) ───────────────────────────────────────────────────

export const notifications = {
  list:     ()   => get('/notifications'),
  count:    ()   => get('/notifications/count'),
  markRead: (id) => post(`/notifications/${id}/lu`, {}),
  markAll:  ()   => post('/notifications/lu', {}),
};
