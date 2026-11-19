/**
 * Fiche recette : saison du mois et empreinte carbone (carbon_data, seasonal_tag
 * fournis par enrich_one). Rendu statique, sans JSX (voir CreditsPage.test.js).
 */
import { describe, it, expect } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { SeasonCarbon } from '../pages/RecipeDetailPage';

const recipe = {
  servings: 4,
  seasonal_tag: 'hors_saison',
  seasonal_ratio: 0.2,
  season_month: 1,
  carbon_data: {
    per_portion_kg: 0.53, label: '🟡 Moyen', month: 1,
    ingredients_co2: [{ ingredient: 'tomato_raw_ripe', kg_co2: 1.6 }],
  },
  ingredients_meta: { tomato_raw_ripe: { name_fr: 'tomate' } },
};

const render = (props) => renderToStaticMarkup(createElement(SeasonCarbon, props));

describe('SeasonCarbon', () => {
  it('affiche la saison du mois et l’empreinte par portion', () => {
    const html = render({ recipe });
    expect(html).toContain('Hors saison en janvier');
    expect(html).toContain('0,53 kg CO₂e / pers.');
    expect(html).toContain('empreinte moyenne');
  });

  it('détaille les ingrédients qui pèsent le plus et la source', () => {
    const html = render({ recipe, defaultOpen: true });
    expect(html).toContain('tomate (0,40 kg)');
    expect(html).toContain('AGRIBALYSE 3.2');
  });

  it('ne dit pas « en janvier » pour des ingrédients de toute l’année', () => {
    const html = render({ recipe: { ...recipe, seasonal_tag: 'année_entière' } });
    expect(html).toContain('toute l');
    expect(html).not.toContain('en janvier</span>');
  });

  it('ne rend rien sans données', () => {
    expect(render({ recipe: {} })).toBe('');
  });
});
