/**
 * La page Crédits porte une obligation légale : les licences Creative Commons
 * imposent de citer l'auteur, la licence et la source. On vérifie donc qu'elle
 * rend sans erreur et qu'elle énonce bien ces obligations.
 *
 * Pas de JSX ici : la config vitest du projet ne charge pas le plugin React.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import CreditsPage from '../pages/CreditsPage';

beforeEach(() => {
  // Le rendu statique n'exécute pas les effets, mais le composant ne doit pas
  // dépendre d'un fetch présent au moment de l'import.
  vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})));
});

describe('CreditsPage', () => {
  it('rend sans erreur avant le chargement des crédits', () => {
    const html = renderToStaticMarkup(createElement(CreditsPage));
    expect(html).toContain('Crédits photos');
    expect(html).toContain('Chargement des crédits');
  });

  it('énonce les obligations des licences Creative Commons', () => {
    const html = renderToStaticMarkup(createElement(CreditsPage));
    expect(html).toContain('Creative Commons');
    // React échappe l'apostrophe en &#x27; dans le rendu statique
    expect(html).toMatch(/citer l(&#x27;|')auteur/i);
    expect(html).toMatch(/indiquer la licence/i);
    expect(html).toMatch(/renvoyer vers la source/i);
  });
});
