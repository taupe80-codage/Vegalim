import { describe, it, expect } from 'vitest';
import { splitFoods } from '../surPlace';

describe('splitFoods', () => {
  it('virgules, « et », retours à la ligne', () => {
    expect(splitFoods('pâtes, tomates et feta')).toEqual(['pâtes', 'tomates', 'feta']);
    expect(splitFoods('courgette\npois chiches ; oignon')).toEqual(['courgette', 'pois chiches', 'oignon']);
  });
  it('garde les mots contenant « et »', () => {
    expect(splitFoods('betterave, petits pois')).toEqual(['betterave', 'petits pois']);
  });
  it('vide et limite', () => {
    expect(splitFoods('')).toEqual([]);
    expect(splitFoods(Array.from({ length: 15 }, (_, i) => `a${i}`).join(','))).toHaveLength(10);
  });
});
