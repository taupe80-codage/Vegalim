import { describe, it, expect } from 'vitest';
import { matchesDishFilters, isComponentRecipe } from '../constants';

const plat   = { id: 'main_curry_1', dish_type: 'main' };
const sauce  = { id: 'base_bechamel_7db18f', dish_type: 'sauce' };
const paneer = { id: 'base_paneer_04e1db', dish_type: 'dairy' };

describe('matchesDishFilters', () => {
  it('sans filtre : les sous-recettes sont masquées', () => {
    expect(matchesDishFilters(plat, new Set())).toBe(true);
    expect(matchesDishFilters(sauce, new Set())).toBe(false);
  });
  it('« Préparations de base » : toutes les sous-recettes, pas les plats', () => {
    const base = new Set(['base']);
    expect(matchesDishFilters(sauce, base)).toBe(true);
    expect(matchesDishFilters(paneer, base)).toBe(true);
    expect(matchesDishFilters(plat, base)).toBe(false);
  });
  it('un type précis garde sa correspondance exacte', () => {
    expect(matchesDishFilters(sauce, new Set(['sauce']))).toBe(true);
    expect(matchesDishFilters(plat, new Set(['main']))).toBe(true);
    expect(isComponentRecipe(plat)).toBe(false);
  });
});
