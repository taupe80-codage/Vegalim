import { describe, expect, it } from 'vitest';
import { fmt, ingredientHref, portionRows, readRecipeQty, scaleFrom100 } from '../ingredientSheet';
import { checkCorrection } from '../ingredientCorrection';

describe('fiche ingrédient', () => {
  it('lien depuis une recette, avec la quantité', () => {
    expect(ingredientHref('eggplant_raw', { quantity: 500, unit: 'g', servings: 4, recipeId: 'curry_1' }))
      .toBe('/ingredient/eggplant_raw?q=500&u=g&p=4&r=curry_1');
    // « 1 poignée » : pas de quantité dans le lien
    expect(ingredientHref('coriander', { quantity: null, unit: '1 poignée', recipeId: 'x' })).toBe('/ingredient/coriander?r=x');
    expect(ingredientHref('a/b')).toBe('/ingredient/a%2Fb');
  });

  it('quantité lue dans l’adresse', () => {
    expect(readRecipeQty(new URLSearchParams('q=500&u=g&p=4'))).toEqual({ quantity: 500, unit: 'g', portions: 4 });
    expect(readRecipeQty(new URLSearchParams('q=300&u=ml'))).toEqual({ quantity: 300, unit: 'ml', portions: 1 });
    expect(readRecipeQty(new URLSearchParams('q=abc&u=g'))).toBe(null);
    expect(readRecipeQty(new URLSearchParams('q=3&u=kg'))).toBe(null);
  });

  it('apport par portion', () => {
    expect(scaleFrom100(22.9, 125)).toBeCloseTo(28.6, 1);
    const rows = portionRows({ calories_kcal: 22.9, protein_g: 0.98, iron_mg: null }, { quantity: 500, portions: 4 });
    expect(rows.map(r => r.key)).toEqual(['calories_kcal', 'protein_g']);
    expect(rows[1].value).toBeCloseTo(1.225, 3);
  });

  it('nombres à la française', () => {
    expect(fmt(0.98)).toBe('0,98');
    expect(fmt(22.94)).toBe('22,9');
    expect(fmt(229.4)).toBe('229');
    expect(fmt(0.0091)).toBe('0,009');
    expect(fmt(null)).toBe('—');
  });
});

describe('signaler une erreur', () => {
  const ok = { field: 'protein_g', value: '1,2', sourceRef: 'Ciqual 2020', sourceUrl: '', comment: '', current: 0.98 };
  it('formulaire complet', () => {
    expect(checkCorrection(ok)).toBe('');
    expect(checkCorrection({ ...ok, sourceUrl: 'https://ciqual.anses.fr/x' })).toBe('');
  });
  it('erreurs', () => {
    expect(checkCorrection({ ...ok, value: '' })).toMatch(/valeur juste/);
    expect(checkCorrection({ ...ok, value: '-1' })).toMatch(/valeur juste/);
    expect(checkCorrection({ ...ok, value: '0,98' })).toMatch(/déjà la valeur/);
    expect(checkCorrection({ ...ok, sourceRef: '' })).toMatch(/source est obligatoire/);
    expect(checkCorrection({ ...ok, sourceUrl: 'ciqual.fr' })).toMatch(/http/);
    expect(checkCorrection({ ...ok, field: 'other', value: '', comment: 'court' })).toMatch(/Décrivez/);
    expect(checkCorrection({ ...ok, field: 'other', value: '', comment: 'Le nom anglais est faux.' })).toBe('');
  });
});
