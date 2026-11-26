import { describe, expect, it } from 'vitest';
import {
  baseRows, changeLabel, editErrorMessage, fromDisplayQty, hasChanges, rowChanged, sameEdits, toDisplayQty,
} from '../recipeEdits';

const COMP = [
  { ingredient: 'eggplant_raw', quantity: 500, unit: 'g' },
  { ingredient: 'coconut_milk_plant', quantity: 300, unit: 'ml' },
  { ingredient: 'coriander_raw_fresh_herb', quantity: null, unit: '1 poignée' },
];

describe('recipeEdits', () => {
  it('lignes de départ : rien de modifié', () => {
    const rows = baseRows(COMP);
    expect(rows[0]).toEqual({ src: 0, orig: 'eggplant_raw', ingredient: 'eggplant_raw', quantity: 500, unit: 'g' });
    expect(rows[2].unit).toBe(null);                 // « 1 poignée » n'est pas une unité modifiable
    expect(hasChanges(rows, COMP)).toBe(false);
  });

  it('remplacement, quantité, retrait, ajout', () => {
    const rows = baseRows(COMP);
    expect(hasChanges([{ ...rows[0], ingredient: 'green_zucchini_squash_raw' }, rows[1], rows[2]], COMP)).toBe(true);
    expect(rowChanged({ ...rows[1], quantity: 250 }, COMP)).toBe(true);
    expect(rowChanged({ ...rows[1], quantity: 300.02 }, COMP)).toBe(false);
    expect(rowChanged({ ...rows[1], unit: 'g' }, COMP)).toBe(true);
    expect(hasChanges([rows[0], rows[1]], COMP)).toBe(true);                    // coriandre retirée
    expect(hasChanges([...rows, { src: null, ingredient: 'tofu', quantity: 200, unit: 'g' }], COMP)).toBe(true);
  });

  it('quantités saisies pour les portions affichées', () => {
    expect(toDisplayQty(500, 0.5)).toBe('250');
    expect(toDisplayQty(3.8, 0.5)).toBe('1,9');
    expect(toDisplayQty(null, 1)).toBe('');
    expect(fromDisplayQty('250', 0.5)).toBe(500);
    expect(fromDisplayQty('1,5', 1)).toBe(1.5);
    expect(fromDisplayQty('', 1)).toBe(null);
    expect(fromDisplayQty('0', 1)).toBe(null);
    expect(fromDisplayQty('abc', 1)).toBe(null);
  });

  it('mêmes modifications', () => {
    const a = { base: 'original', rows: baseRows(COMP) };
    expect(sameEdits(a, { rows: baseRows(COMP) })).toBe(true);
    expect(sameEdits(a, { base: 'vegan', rows: baseRows(COMP) })).toBe(false);
    expect(sameEdits(a, null)).toBe(false);
  });

  it('libellés des modifications', () => {
    expect(changeLabel({ kind: 'replaced', name: 'aubergine', new_name: 'courgette', before: '500 g', after: '400 g' }))
      .toBe('Aubergine → courgette (500 g → 400 g)');
    expect(changeLabel({ kind: 'replaced', name: 'lait', new_name: 'lait de soja' })).toBe('Lait → lait de soja');
    expect(changeLabel({ kind: 'quantity', name: 'oignon', before: '150 g', after: '100 g' })).toBe('Oignon : 150 g → 100 g');
    expect(changeLabel({ kind: 'removed', name: 'piment' })).toBe('Piment retiré');
    expect(changeLabel({ kind: 'added', name: 'tofu', after: '200 g' })).toBe('Tofu ajouté (200 g)');
  });

  it('message d’erreur lisible', () => {
    expect(editErrorMessage(new Error('Ingrédient inconnu : x.'))).toBe('Ingrédient inconnu : x.');
    expect(editErrorMessage(new Error('[object Object]'))).toMatch(/vérifiez/);
  });
});
