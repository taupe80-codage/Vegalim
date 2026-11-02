import { describe, it, expect } from 'vitest';
import { filtersToApiParams, ORIGIN_GROUPS, getGroupCuisines } from '../components/RecipeFiltersShared';

describe('filtersToApiParams', () => {
  it('traduit groupes et sous-filtres santé (le sous-filtre l’emporte)', () => {
    const p = filtersToApiParams({
      healthFilters: new Set(['high_protein', 'low_fodmap', 'minerals']),
      subFilters:    new Set(['protein_source', 'moderate_fodmap']),
    });
    expect(p.good_source_protein).toBe(true);
    expect(p.high_protein).toBeUndefined();
    expect(p.fodmap).toBe('not_high');
    expect(p.high_calcium).toBe(true);
  });

  it('envoie toutes les origines (une seule était envoyée, aucune au-delà)', () => {
    const p = filtersToApiParams({ origins: new Set(['italian', 'japanese']) });
    expect(p.cuisines).toEqual(['italian', 'japanese']);
    const group = ORIGIN_GROUPS[0];
    expect(filtersToApiParams({ origins: new Set([group.id]) }).cuisines)
      .toEqual([...new Set(getGroupCuisines(group))]);
  });

  it('allergènes, extras, temps, saison, difficulté', () => {
    const p = filtersToApiParams({
      allergens: new Set(['egg_free']), dietExtras: new Set(['low_sugar']),
      maxTime: '30', season: 'summer', difficulty: 'easy',
    });
    expect(p).toEqual({ egg_free: true, low_sugar: true, max_time: 30, season: 'summer', difficulty: 'easy' });
  });

  it('rien de coché → aucun paramètre', () => {
    expect(filtersToApiParams({})).toEqual({});
  });
});
