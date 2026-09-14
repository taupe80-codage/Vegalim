/**
 * favoritesSync.js — Synchronisation favoris locaux ↔ likes du compte
 *
 * Les favoris restent utilisables sans compte (localStorage). Une fois
 * connecté, chaque favori est aussi un « like » côté API : c'est ce qui
 * active la personnalisation des recommandations (à partir de 5 likes).
 *
 * À la connexion : fusion dans les deux sens, sans rien supprimer
 *   - favoris locaux absents du compte → envoyés (like)
 *   - likes du compte absents en local → récupérés et ajoutés
 */

/** Calcule ce qu'il faut envoyer et récupérer. `local` : plus récent d'abord. */
export function planFavoritesSync(local, likedIds) {
  const server  = new Set(likedIds);
  const localIds = new Set(local.map(r => r.id));
  return {
    // du plus ancien au plus récent : le compte conserve l'ordre d'ajout
    toPush:  local.filter(r => !server.has(r.id)).map(r => r.id).reverse(),
    toFetch: likedIds.filter(id => !localIds.has(id)),
  };
}

/**
 * Exécute la fusion. Retourne les recettes récupérées depuis le compte.
 * Les échecs réseau sont ignorés individuellement (le favori local reste).
 */
export async function syncFavorites(local, { likes, interaction, fetchRecipe }, maxFetch = 100) {
  const { liked = [] } = (await likes()) || {};
  const { toPush, toFetch } = planFavoritesSync(local, liked);
  for (const id of toPush) {
    try { await interaction(id, 'like'); } catch { /* réessayé à la prochaine connexion */ }
  }
  const fetched = await Promise.allSettled(toFetch.slice(0, maxFetch).map(fetchRecipe));
  return fetched.filter(p => p.status === 'fulfilled' && p.value).map(p => p.value);
}

/** Envoi « fire and forget » d'une interaction : ne bloque ni ne casse l'UI. */
export function sendInteraction(interaction, recipeId, action) {
  if (!recipeId) return;
  Promise.resolve()
    .then(() => interaction(recipeId, action))
    .catch(() => { /* hors ligne ou session expirée : sans impact local */ });
}

const _viewedThisSession = new Set();

/** Une vue par recette et par session suffit au moteur d'apprentissage. */
export function recordViewOnce(interaction, recipeId) {
  if (!recipeId || _viewedThisSession.has(recipeId)) return false;
  _viewedThisSession.add(recipeId);
  sendInteraction(interaction, recipeId, 'view');
  return true;
}
