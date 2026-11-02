import { describe, it, expect } from 'vitest';
import { defaultDietFilter } from '../useProfileDiet';

describe('defaultDietFilter', () => {
  it('coche Vegan par défaut pour un profil vegan, rien sinon', () => {
    expect(defaultDietFilter('vegan')).toBe('vegan');
    expect(defaultDietFilter('vegetarien')).toBe('');
    expect(defaultDietFilter('')).toBe('');
    expect(defaultDietFilter(undefined)).toBe('');
  });
});
