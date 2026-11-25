import { describe, it, expect } from 'vitest';
import { parseCommand, wordsToDigits, speakable } from '../cookVoice';

const type = (t) => parseCommand(t)?.type ?? null;

describe('parseCommand', () => {
  it('navigation', () => {
    expect(type('Suivante')).toBe('next');
    expect(type('étape suivante')).toBe('next');
    expect(type('ok après')).toBe('next');
    expect(type('étape précédente')).toBe('prev');
    expect(type('retour')).toBe('prev');
  });
  it('lecture', () => {
    expect(type('répète')).toBe('repeat');
    expect(type('relis l\u2019étape')).toBe('repeat');
    expect(type('stop')).toBe('stop');
    expect(type('arrête de lire')).toBe('stop');
  });
  it('minuteurs', () => {
    expect(parseCommand('lance le minuteur')).toEqual({ type: 'timer' });
    expect(parseCommand('minuteur 5 minutes')).toMatchObject({ type: 'timer', seconds: 300 });
    expect(parseCommand('minuteur cinq minutes')).toMatchObject({ type: 'timer', seconds: 300 });
    expect(parseCommand('chrono vingt-cinq minutes')).toMatchObject({ type: 'timer', seconds: 1500 });
  });
  it('panneau et sortie', () => {
    expect(type('ingrédients')).toBe('ingredients');
    expect(type('quitter')).toBe('close');
    expect(type('ferme le mode cuisine')).toBe('close');
  });
  it('phrase sans commande', () => {
    expect(type('il fait beau aujourd\u2019hui')).toBe(null);
    expect(type('')).toBe(null);
  });
});

describe('utilitaires', () => {
  it('wordsToDigits', () => {
    expect(wordsToDigits('minuteur dix-huit minutes')).toBe('minuteur 18 minutes');
    expect(wordsToDigits('deux heures')).toBe('2 heures');
  });
  it('speakable', () => {
    expect(speakable('Ajouter 15 ml d\u2019huile et 75 g d\u2019oignon, 5 min à 180 °C'))
      .toBe('Ajouter 15 millilitres d\u2019huile et 75 grammes d\u2019oignon, 5 minutes à 180 degrés');
  });
});
