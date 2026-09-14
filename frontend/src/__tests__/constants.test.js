import { describe, it, expect } from 'vitest';
import { DISH_OPTIONS, dishTypeLabel } from '../constants';

describe('constants', () => {
  it('libellé connu pour chaque type de plat', () => {
    for (const { value, label } of DISH_OPTIONS) expect(dishTypeLabel(value)).toBe(label);
  });
  it('type inconnu renvoyé tel quel', () => {
    expect(dishTypeLabel('inconnu')).toBe('inconnu');
  });
});
