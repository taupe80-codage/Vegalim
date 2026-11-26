import { describe, expect, it } from 'vitest';
import { compareText } from '../carbonText';

describe('empreinte carbone : comparaison', () => {
  it('à la moyenne des plats', () => {
    expect(compareText(0.33, 0.37)).toBe('11 % de moins que la moyenne des plats ALIM');
    expect(compareText(0.5, 0.37)).toBe('35 % de plus que la moyenne des plats ALIM');
    expect(compareText(0.37, 0.37)).toBe('dans la moyenne des plats ALIM');
    expect(compareText(0.3, null)).toBe('');
  });
});
