/**
 * planShopping.js — Plan hebdomadaire → format attendu par /planning/shopping_list.
 *
 * Partagé par PlanningPage et ShoppingListPage (deux copies existaient).
 * Les portions du créneau (compteur − / + du planning) sont transmises :
 * le backend met les quantités à l'échelle (servings du créneau / servings
 * de la recette) mais ne recevait que {id, title}.
 */
const DAYS_KEY   = ['lundi','mardi','mercredi','jeudi','vendredi','samedi','dimanche'];
const MEAL_ORDER = ['breakfast','lunch','dinner'];

export function planToShoppingFormat(plan) {
  const out = {};
  for (const dk of DAYS_KEY) {
    out[dk] = {};
    let i = 0;
    for (const m of MEAL_ORDER) {
      const slot = plan?.[dk]?.[m];
      if (!slot || slot.skip) continue;
      for (const r of (slot.recipes || [])) {
        if (!r?.id) continue;
        const entry = { id: r.id, title: r.title_fr || r.title || '' };
        if (slot.servings > 0) entry.servings = slot.servings;
        out[dk][`${m}_${i++}`] = entry;
      }
    }
  }
  return out;
}
