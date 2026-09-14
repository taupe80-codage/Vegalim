import { describe, it, expect } from 'vitest';
import { formatIngredientQty } from '../formatIngredientQty';

const PHYS = {
  garlic: { piece_g: 5, piece_label: 'gousse' },
  egg:    { piece_g: 60, piece_label: 'piece' },
};

describe('formatIngredientQty', () => {
  it('convertit en pièces quand le poids unitaire est connu', () => {
    expect(formatIngredientQty('garlic', 15, 'g', PHYS)).toBe('(3 gousses)');
    expect(formatIngredientQty('egg', 60, 'g', PHYS)).toBe('(1 pièce)');
  });

  it('résout les alias base/variante', () => {
    expect(formatIngredientQty('garlic/raw', 5, 'g', PHYS)).toBe('(1 gousse)');
  });

  it('propose une pincée pour les très petites quantités d’épices', () => {
    expect(formatIngredientQty('cumin', 1, 'g', PHYS)).toBe('(une pincée)');
  });

  it('convertit les liquides en cuillères', () => {
    expect(formatIngredientQty('soy_sauce', 15, 'ml', PHYS)).toBe('(1 c. à soupe)');
    expect(formatIngredientQty('soy_sauce', 5, 'ml', PHYS)).toBe('(1 c. à café)');
  });

  it('jamais de cuillère pour les herbes fraîches ni les légumes entiers', () => {
    expect(formatIngredientQty('basil', 15, 'g', PHYS)).toBe('');
    expect(formatIngredientQty('tomato', 15, 'g', PHYS)).toBe('');
  });

  it('renvoie une chaîne vide si une donnée manque', () => {
    expect(formatIngredientQty('', 10, 'g', PHYS)).toBe('');
    expect(formatIngredientQty('cumin', 0, 'g', PHYS)).toBe('');
    expect(formatIngredientQty('cumin', 10, null, PHYS)).toBe('');
  });
});
