import { describe, it, expect } from 'vitest';
import { findDurations, cleanStep, formatClock } from '../cookTimers';

const sec = (t) => findDurations(t).map(d => d.seconds);
const lab = (t) => findDurations(t).map(d => d.label);

describe('findDurations', () => {
  it('minutes, heures, secondes', () => {
    expect(sec('Cuire 25 minutes à feu doux.')).toEqual([1500]);
    expect(sec('Mijoter 5 min.')).toEqual([300]);
    expect(sec('Laisser lever 2 heures.')).toEqual([7200]);
    expect(sec('Humidifier la galette 10 secondes.')).toEqual([10]);
  });
  it('fourchette : borne basse, libellé complet', () => {
    expect(findDurations('Cuire 10 à 12 minutes.')[0]).toMatchObject({ seconds: 600, label: '10 à 12 minutes' });
    expect(sec('Rôtir 20-25 min')).toEqual([1200]);
  });
  it('heures et minutes', () => {
    expect(sec('Cuire 1 h 30 au four')).toEqual([5400]);
    expect(sec('Cuire 1h30.')).toEqual([5400]);
    expect(sec('Compter 1 heure 15 minutes')).toEqual([4500]);
  });
  it('plusieurs durées dans une étape', () => {
    expect(sec('Faire revenir 5 minutes, puis mijoter 25 minutes.')).toEqual([300, 1500]);
  });
  it('ignore poids, volumes et températures', () => {
    expect(findDurations('Ajouter 250 g de farine, 30 ml d\'huile, four à 180 °C.')).toEqual([]);
    expect(findDurations('5 hachées finement')).toEqual([]);
  });
  it('trempage d’une nuit : signalé sans minuteur', () => {
    expect(findDurations('Faire tremper 12 heures.')[0]).toMatchObject({ seconds: 43200, long: true });
  });
  it('minutes non rattachées à des heures', () => {
    expect(lab('Cuire 8 minutes 2 fois')).toEqual(['8 minutes']);
  });
});

describe('utilitaires', () => {
  it('cleanStep retire « Étape N : »', () => {
    expect(cleanStep('Étape 3 : Faire revenir.')).toBe('Faire revenir.');
    expect(cleanStep('Step 2. Mix')).toBe('Mix');
  });
  it('formatClock', () => {
    expect(formatClock(90)).toBe('1:30');
    expect(formatClock(3725)).toBe('1:02:05');
    expect(formatClock(-3)).toBe('0:00');
  });
});
