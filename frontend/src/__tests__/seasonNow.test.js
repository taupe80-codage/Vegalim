/**
 * Rubrique « De saison » de l'accueil : visible sans recherche ni filtre choisi,
 * et aussi pour un profil vegan dont le « Vegan » est coché d'office.
 */
import { describe, it, expect } from 'vitest';
import { seasonStripDiet } from '../seasonNow';

describe('seasonStripDiet', () => {
  it('accueil sans filtre : rubrique sans régime', () => {
    expect(seasonStripDiet({})).toBe('');
  });

  it('profil vegan, « Vegan » coché d’office : rubrique vegan', () => {
    expect(seasonStripDiet({ diet: 'vegan', defaultDiet: 'vegan' })).toBe('vegan');
  });

  it('profil vegan qui décoche « Vegan » : rubrique sans régime', () => {
    expect(seasonStripDiet({ diet: '', defaultDiet: 'vegan' })).toBe('');
  });

  it('régime choisi à la main : rubrique masquée', () => {
    expect(seasonStripDiet({ diet: 'vegetarien' })).toBeNull();
    expect(seasonStripDiet({ diet: 'vegetarien', defaultDiet: 'vegan' })).toBeNull();
  });

  it('recherche ou autre filtre : rubrique masquée', () => {
    expect(seasonStripDiet({ query: 'soupe' })).toBeNull();
    expect(seasonStripDiet({ query: '  ' })).toBe('');
    expect(seasonStripDiet({ diet: 'vegan', defaultDiet: 'vegan', otherFilters: true })).toBeNull();
  });
});
