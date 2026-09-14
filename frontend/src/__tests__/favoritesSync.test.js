import { describe, it, expect, vi } from 'vitest';
import { planFavoritesSync, syncFavorites, recordViewOnce } from '../favoritesSync';

const fav = (id) => ({ id, title_fr: id });

describe('favoritesSync', () => {
  it('fusionne dans les deux sens sans rien supprimer', () => {
    const plan = planFavoritesSync([fav('c'), fav('b'), fav('a')], ['b', 'x', 'y']);
    expect(plan.toPush).toEqual(['a', 'c']);      // plus ancien d'abord
    expect(plan.toFetch).toEqual(['x', 'y']);
  });

  it('envoie les likes manquants et récupère les recettes du compte', async () => {
    const interaction = vi.fn().mockResolvedValue(null);
    const fetchRecipe = vi.fn(async (id) => (id === 'gone' ? Promise.reject(new Error('404')) : { id }));
    const fetched = await syncFavorites([fav('local')], {
      likes: async () => ({ liked: ['srv', 'gone'] }), interaction, fetchRecipe,
    });
    expect(interaction).toHaveBeenCalledWith('local', 'like');
    expect(fetched).toEqual([{ id: 'srv' }]);    // recette disparue ignorée
  });

  it("un échec d'envoi n'interrompt pas la synchronisation", async () => {
    const interaction = vi.fn().mockRejectedValue(new Error('offline'));
    const fetched = await syncFavorites([fav('a'), fav('b')], {
      likes: async () => ({ liked: ['s'] }), interaction, fetchRecipe: async (id) => ({ id }),
    });
    expect(interaction).toHaveBeenCalledTimes(2);
    expect(fetched).toEqual([{ id: 's' }]);
  });

  it('une seule vue par recette et par session', async () => {
    const interaction = vi.fn().mockResolvedValue(null);
    expect(recordViewOnce(interaction, 'r1')).toBe(true);
    expect(recordViewOnce(interaction, 'r1')).toBe(false);
    await Promise.resolve(); await Promise.resolve();
    expect(interaction).toHaveBeenCalledTimes(1);
    expect(interaction).toHaveBeenCalledWith('r1', 'view');
  });
});
