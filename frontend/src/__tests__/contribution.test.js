import { describe, it, expect } from 'vitest';
import {
  emptyForm, formFromServer, toPayload, moveItem, sectionStatus, formatMinutes, ingredientLine,
} from '../contribution';

describe('formulaire « Proposer une recette »', () => {
  it('toPayload retire les lignes vides et convertit les nombres', () => {
    const f = {
      ...emptyForm(),
      title: 'Dahl de lentilles corail',
      prep_min: '15', cook_min: '', servings: '4',
      ingredients: [
        { name: 'lentille corail', ingredient_id: 'red_lentil_dried', quantity: '250', unit: 'g', note: '' },
        { name: '', ingredient_id: null, quantity: '', unit: 'g', note: '' },
        { name: 'sel', ingredient_id: 'table_salt_unenriched', quantity: '3', unit: 'to_taste', note: '' },
        { name: 'huile', ingredient_id: null, quantity: '1,5', unit: 'tbsp', note: '' },
      ],
      steps: ['  Rincer les lentilles. ', '', 'Cuire 20 minutes.'],
    };
    const p = toPayload(f);
    expect(p.prep_min).toBe(15);
    expect(p.cook_min).toBe(0);
    expect(p.servings).toBe(4);
    expect(p.ingredients).toHaveLength(3);
    expect(p.ingredients[0].quantity).toBe(250);
    expect(p.ingredients[1].quantity).toBeNull();      // selon le goût
    expect(p.ingredients[2].quantity).toBe(1.5);       // virgule décimale
    expect(p.steps).toEqual(['Rincer les lentilles.', 'Cuire 20 minutes.']);
  });

  it('formFromServer garde des lignes à remplir et vide les temps à 0', () => {
    const f = formFromServer({ title: 'X', prep_min: 0, ingredients: [], steps: [] });
    expect(f.prep_min).toBe('');
    expect(f.ingredients.length).toBeGreaterThan(0);
    expect(f.steps.length).toBeGreaterThan(0);
    expect(formFromServer(null).title).toBe('');
  });

  it('moveItem déplace d\'un cran et ne sort pas de la liste', () => {
    expect(moveItem(['a', 'b', 'c'], 0, 1)).toEqual(['b', 'a', 'c']);
    expect(moveItem(['a', 'b', 'c'], 2, -1)).toEqual(['a', 'c', 'b']);
    const l = ['a', 'b'];
    expect(moveItem(l, 0, -1)).toBe(l);
    expect(moveItem(l, 1, 1)).toBe(l);
  });

  it('sectionStatus suit la progression', () => {
    const empty = sectionStatus(emptyForm());
    expect(empty.every(s => !s.done)).toBe(true);
    const f = {
      ...emptyForm(),
      title: 'Soupe de potimarron', dish_type: 'soup', prep_min: 10, cook_min: 30,
      ingredients: [
        { name: 'potimarron', ingredient_id: 'x', quantity: 800, unit: 'g', note: '' },
        { name: 'sel', ingredient_id: 'y', quantity: '', unit: 'to_taste', note: '' },
      ],
      steps: ['Couper.', 'Cuire.'],
    };
    expect(sectionStatus(f).every(s => s.done)).toBe(true);
    const sansQuantite = { ...f, ingredients: [{ ...f.ingredients[0], quantity: '' }, f.ingredients[1]] };
    expect(sectionStatus(sansQuantite).find(s => s.id === 'ingredients').done).toBe(false);
  });

  it('formatMinutes', () => {
    expect(formatMinutes(0)).toBe('—');
    expect(formatMinutes(45)).toBe('45 min');
    expect(formatMinutes(60)).toBe('1 h');
    expect(formatMinutes(95)).toBe('1 h 35');
  });

  it('ingredientLine écrit la ligne comme dans une recette', () => {
    expect(ingredientLine({ name: 'huile d\'olive', quantity: 2, unit: 'tbsp' })).toBe("2 c. à soupe d'huile d'olive");
    expect(ingredientLine({ name: 'farine', quantity: 200, unit: 'g' })).toBe('200 g de farine');
    expect(ingredientLine({ name: 'oignon', quantity: 1, unit: 'piece', note: 'émincé' })).toBe('1 oignon (émincé)');
    expect(ingredientLine({ name: 'ail', quantity: 3, unit: 'gousse' })).toBe("3 gousses d'ail");
    expect(ingredientLine({ name: 'sel', unit: 'to_taste' })).toBe('sel, selon le goût');
    expect(ingredientLine({ name: 'lait d\'avoine', quantity: '0.5', unit: 'l' })).toBe("0,5 l de lait d'avoine");
    expect(ingredientLine({ name: '', quantity: 1, unit: 'g' })).toBe('');
  });
});
