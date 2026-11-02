import { describe, it, expect } from 'vitest';
import { planToShoppingFormat } from '../planShopping';

describe('planToShoppingFormat', () => {
  it('transmet les portions du créneau (le backend ne recevait que {id, title})', () => {
    const plan = {
      lundi: {
        breakfast: { servings: 2, skip: false, recipes: [{ id: 'a', title_fr: 'A' }] },
        lunch:     { servings: 6, skip: false, recipes: [{ id: 'b', title_fr: 'B' }, { id: 'c' }] },
        dinner:    { servings: 4, skip: true,  recipes: [{ id: 'd' }] },
      },
    };
    const out = planToShoppingFormat(plan);
    expect(out.lundi).toEqual({
      breakfast_0: { id: 'a', title: 'A', servings: 2 },
      lunch_1:     { id: 'b', title: 'B', servings: 6 },
      lunch_2:     { id: 'c', title: '',  servings: 6 },
    });
    expect(out.mardi).toEqual({});
  });
});
