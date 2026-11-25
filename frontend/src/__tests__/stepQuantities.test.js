import { describe, it, expect } from 'vitest';
import { scaleStepText, scaleSegments } from '../stepQuantities';

const half = (t) => scaleStepText(t, 0.5);

describe('scaleStepText', () => {
  it('ratio 1 : texte inchangé', () => {
    expect(scaleStepText('Ajouter 150 g de farine.', 1)).toBe('Ajouter 150 g de farine.');
  });
  it('masses et volumes', () => {
    expect(half('Faire revenir 150 g d\'oignon dans 30 ml d\'huile.')).toBe('Faire revenir 75 g d\'oignon dans 15 ml d\'huile.');
    expect(half('Ajouter 3 g de curcuma')).toBe('Ajouter 1,5 g de curcuma');
    expect(half('Verser 250ml de lait')).toBe('Verser 125 ml de lait');
    expect(half("Verser 45ml d'huile")).toBe("Verser 22,5 ml d'huile");
    expect(half('Incorporer 3 grammes de thym')).toBe('Incorporer 1,5 g de thym');
    expect(half("Ajouter 2 l'un après l'autre")).toBe("Ajouter 2 l'un après l'autre");
  });
  it('unité la plus lisible', () => {
    expect(half('Porter 1,2 L d\'eau à ébullition')).toBe('Porter 600 ml d\'eau à ébullition');
    expect(scaleStepText('Ajouter 800 g de pommes de terre', 2)).toBe('Ajouter 1,6 kg de pommes de terre');
    expect(half('Verser 20 cl de crème')).toBe('Verser 100 ml de crème');
  });
  it('arrondis', () => {
    expect(scaleStepText('Ajouter 250 g de riz', 1.5)).toBe('Ajouter 375 g de riz');
    expect(scaleStepText('Ajouter 333 g de riz', 0.5)).toBe('Ajouter 165 g de riz');
  });
  it('pièces : œufs, gousses, au singulier si besoin', () => {
    expect(half('Battre 2 œufs')).toBe('Battre 1 œuf');
    expect(half('Hacher 3 gousses d\'ail')).toBe('Hacher 1,5 gousses d\'ail');
    expect(scaleStepText('Ajouter 1 œuf', 2)).toBe('Ajouter 2 œufs');
  });
  it('fourchette', () => {
    expect(half('Ajouter 2 à 3 gousses d\'ail')).toBe('Ajouter 1 à 1,5 gousses d\'ail');
  });
  it('durées, températures et tailles intactes', () => {
    const t = 'Cuire 25 minutes à 180 °C, couper en dés de 2 cm, 1 h 30 de repos.';
    expect(half(t)).toBe(t);
  });
  it('segments : la valeur d’origine est gardée', () => {
    const segs = scaleSegments('Ajouter 150 g de riz', 0.5);
    expect(segs).toEqual([{ text: 'Ajouter ' }, { text: '75 g', original: '150 g' }, { text: ' de riz' }]);
  });
});
