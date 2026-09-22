#!/usr/bin/env python3
"""
propose_servings.py — Propose un nombre de portions réaliste par recette.

Constat (2026-09-14) : `servings` n'a jamais été renseigné recette par recette —
toutes les recettes ont la valeur par défaut de leur dish_type (petit-déj /
en-cas = 2, plat = 4, dessert = 6). Les préparations en lot (granola 300 g de
flocons, brioche 500 g de farine…) sortent donc à 1 500-1 900 kcal « par
portion ».

Méthode : ÉNERGIE, pas poids. Le poids trompe dans les deux sens (80 g de riz
cru = une vraie portion ; 600 g de légumes = une portion légère). On ne
signale que les recettes dont les kcal/portion dépassent la plage plausible
du type de plat (KCAL_MAX), et on propose le nombre de portions qui ramène
à une valeur typique (KCAL_TARGET), sans passer sous PORTION_MIN_G de poids
hors eau par portion (garde-fou contre les plats très gras mais légers).
Les plats peu caloriques (soupe miso, tom yum) ne sont pas touchés.

Deux temps :
    python scripts/recipes/propose_servings.py                 # écrit la proposition (CSV à valider)
    python scripts/recipes/propose_servings.py --apply FICHIER # applique les lignes validées (colonne valider = oui)

Le CSV contient une colonne `valider` (oui/non) et `servings_valides`
(modifiable) : seules les lignes marquées « oui » sont appliquées.

Préparations de base (--components) : l'énergie ne convient pas (un ghee est
dense par nature). On part d'une PORTION DE RÉFÉRENCE en grammes de
préparation (COMPONENT_PORTION_G : cuillère de ghee 10 g, confiture 20 g,
verre de lait végétal 250 ml…) et du poids total préparé (eau comprise) :
servings = poids total / portion. Seules les préparations dont la portion
actuelle s'écarte de plus de 30 % de la référence sont proposées. Le poids
tient compte du rendement `yield_factor` de la recette (concentré de tomate
0,35, paneer 0,2…), aussi utilisé par build_derived_base_registry.py.
"""
import argparse, csv, json, logging, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
logging.disable(logging.WARNING)

from backend.engine.config import RECIPES_PATH
from backend.core.data_io import load_recipes, load_nutrition_graph, is_component_recipe
from backend.engine import nutrition_engine as ne

# kcal/portion : au-delà de KCAL_MAX la portion est irréaliste, KCAL_TARGET = valeur typique
KCAL_MAX = {
    'main': 1000, 'pasta': 1000, 'soup': 750, 'side': 600, 'starter': 600,
    'dessert': 700, 'breakfast': 750, 'snack': 650, 'bread': 700,
    'pastry': 700, 'beverage': 450,
}
KCAL_TARGET = {
    'main': 600, 'pasta': 600, 'soup': 400, 'side': 300, 'starter': 300,
    'dessert': 380, 'breakfast': 450, 'snack': 380, 'bread': 350,
    'pastry': 380, 'beverage': 250,
}
# poids hors eau minimal d'une portion (g)
PORTION_MIN_G = {
    'main': 150, 'pasta': 150, 'soup': 120, 'side': 80, 'starter': 60,
    'dessert': 60, 'breakfast': 90, 'snack': 60, 'bread': 50,
    'pastry': 40, 'beverage': 100,
}
MAX_SERVINGS = 12

# Portion de référence (g ou ml de préparation) des préparations de base.
# Absentes : pâtes, nouilles, galettes, bases de plats — portions déjà plausibles.
COMPONENT_PORTION_G = {
    # matières grasses, crèmes, tartinables
    'base_ghee_ec9064': 10, 'base_creme_fraiche_b536c1': 30,
    'base_peanut_butter_81c37b': 15, 'base_tahini_030e18': 15,
    'base_mayonnaise_0d3e4e': 15, 'base_vegan_mayonnaise_b68322': 15,
    'sauce_vinaigrette_174a79': 15, 'base_pesto_905db7': 20, 'base_pistou_43e29a': 20,
    'base_cream_cheese_c6e3b6': 30, 'base_coconut_cream_10c770': 30,
    'base_oat_cream_954865': 30, 'base_soy_cream_4dc027': 30,
    # sucré
    'base_strawberry_jam_1e5515': 20, 'salted_butter_caramel_096c73': 20,
    'base_strawberry_coulis_49d4ea': 40,
    # condiments, sauces piquantes et fermentées, pâtes aromatiques
    'base_sriracha_19895c': 15, 'base_harissa_ef842f': 15, 'base_gochujang_41da6e': 15,
    'base_doubanjiang_paste_340399': 15, 'base_hoisin_033e33': 15, 'base_teriyaki_03b2ff': 15,
    'base_ponzu_7479fe': 15, 'base_vegetarian_fish_sauce_536a33': 10,
    'base_vegetarian_oyster_sauce_b74b2': 15, 'base_worcestershire_vegan_5f26ec': 10,
    'base_okonomiyaki_1e5fba': 15, 'base_pate_piment_b6904a': 15, 'base_laksa_paste_bc7fd5': 15,
    'base_curry_paste_49c97f': 15, 'base_green_curry_paste_250117': 15,
    'red_curry_paste_3ee8f5': 15, 'yellow_curry_paste_077f54': 15, 'chili_paste_95cb92': 15,
    'tamarind_paste_b740bb': 15, 'base_japanese_curry_roux_385e52': 20,
    'base_miso_paste_1faeef': 20, 'base_fermented_bean_paste_817412': 20,
    'base_tomato_paste_26412f': 20, 'base_ras_el_hanout_7cd544': 5, 'base_za_atar_2badf3': 5,
    'base_fried_onion_217e6a': 30, 'base_gundruk_94c079': 50, 'base_kimchi_61791a': 80,
    # sauces d'accompagnement
    'base_bechamel_7db18f': 60, 'base_bechamel_vegane_7a210c': 60,
    'base_sauce_tomate_926bfa': 100, 'base_sauce_yogurt_0bfeaf': 40,
    'base_sauce_peanut_d92c5c': 30, 'base_mole_d0034f': 60, 'vegetarian_brown_sauce_4233df': 60,
    # fromages et alternatives
    'base_cheddar_vegane_529b97': 30, 'base_mozzarella_vegane_fca8c8': 30,
    'base_vegan_cheddar_024998': 30, 'base_cashew_ricotta_5c62e9': 30,
    'base_salted_ricotta_1ecd1c': 30, 'base_kashk_fd3ac6': 20,
    # boissons et bouillons (verre / bol de 250 ml ; lait de coco : usage cuisine)
    'base_almond_milk_226291': 250, 'base_cashew_milk_71947e': 250, 'base_coconut_milk_1ebad9': 100,
    'base_hemp_milk_9248fe': 250, 'base_oat_milk_3519f4': 250, 'base_rice_milk_128001': 250,
    'base_soy_milk_827b25': 250, 'base_vegetable_broth_303b7d': 250,
    'base_dashi_broth_a3a517': 250, 'miso_broth_618f1e': 250, 'base_mala_broth_1ab129': 250,
}
COMPONENT_TOLERANCE = 0.30
MAX_COMPONENT_SERVINGS = 60


def solid_weight_g(recipe: dict) -> float:
    total = 0.0
    for c in recipe.get('composition', []):
        if (c.get('meta') or {}).get('role') == 'serving_suggestion':
            continue
        iid = c.get('ingredient', '')
        if iid.startswith('water'):
            continue
        g = ne._qty_to_g(iid, c)
        if ne._is_frying_bath(iid, g):
            continue
        total += g
    return total


def recipe_yield(recipe: dict) -> float:
    """Rendement `yield_factor` de la recette (réduction, égouttage, filtrage) — défaut 1."""
    y = recipe.get('yield_factor')
    return float(y) if isinstance(y, (int, float)) and 0 < y <= 1 else 1.0


def total_weight_g(recipe: dict) -> float:
    """Poids préparé, eau comprise (hors suggestions de service et bain de friture)."""
    total = 0.0
    for c in recipe.get('composition', []):
        if (c.get('meta') or {}).get('role') == 'serving_suggestion':
            continue
        iid = c.get('ingredient', '')
        g = ne._qty_to_g(iid, c)
        if ne._is_frying_bath(iid, g):
            continue
        total += g
    return total


def component_proposals() -> list[dict]:
    ng = load_nutrition_graph()
    out = []
    for r in load_recipes():
        ref = COMPONENT_PORTION_G.get(r['id'])
        if ref is None:
            continue
        current = ne.resolve_servings(r)
        weight = total_weight_g(r) * recipe_yield(r)
        per_portion = weight / current
        if abs(per_portion - ref) / ref <= COMPONENT_TOLERANCE:
            continue
        proposed = max(1, min(MAX_COMPONENT_SERVINGS, round(weight / ref)))
        if proposed == current:
            continue
        kcal_total = (ng.get(r['id'], {}).get('calories') or 0) * current
        out.append({
            'id': r['id'],
            'titre': (r.get('titles') or {}).get('fr', ''),
            'dish_type': r.get('dish_type'),
            'poids_obtenu_g': round(weight),
            'rendement': recipe_yield(r),
            'portion_reference_g': ref,
            'servings_actuels': current,
            'g_par_portion_actuel': round(per_portion),
            'kcal_par_portion_actuel': round(kcal_total / current),
            'servings_proposes': proposed,
            'g_par_portion_propose': round(weight / proposed),
            'kcal_par_portion_propose': round(kcal_total / proposed),
            'valider': 'oui',
            'servings_valides': proposed,
        })
    return sorted(out, key=lambda x: (x['dish_type'], x['id']))


def proposals() -> list[dict]:
    ng = load_nutrition_graph()
    out = []
    for r in load_recipes():
        if is_component_recipe(r):
            continue
        dt = r.get('dish_type')
        if dt not in KCAL_MAX:
            continue
        current = ne.resolve_servings(r)
        kcal_portion = ng.get(r['id'], {}).get('calories') or 0
        if kcal_portion <= KCAL_MAX[dt]:
            continue
        solids = solid_weight_g(r)
        per_portion = solids / current
        kcal_total = kcal_portion * current
        proposed = round(kcal_total / KCAL_TARGET[dt])
        proposed = min(proposed, int(solids // PORTION_MIN_G[dt]) or 1)
        proposed = max(1, min(MAX_SERVINGS, proposed))
        if proposed <= current:
            continue
        out.append({
            'id': r['id'],
            'titre': (r.get('titles') or {}).get('fr', ''),
            'dish_type': r.get('dish_type'),
            'poids_hors_eau_g': round(solids),
            'servings_actuels': current,
            'g_par_portion_actuel': round(per_portion),
            'kcal_par_portion_actuel': round(kcal_total / current),
            'servings_proposes': proposed,
            'g_par_portion_propose': round(solids / proposed),
            'kcal_par_portion_propose': round(kcal_total / proposed),
            'valider': 'oui',
            'servings_valides': proposed,
        })
    return sorted(out, key=lambda x: (x['dish_type'], x['id']))


def apply(csv_path: Path) -> None:
    with open(csv_path, encoding='utf-8-sig', newline='') as f:
        rows = [row for row in csv.DictReader(f, delimiter=';')
                if row.get('valider', '').strip().lower() in ('oui', 'o', 'yes', 'y', '1')]
    wanted = {row['id']: int(row['servings_valides']) for row in rows}
    raw = json.loads(Path(RECIPES_PATH).read_text(encoding='utf-8'))
    done = 0
    for r in raw['recipes']:
        if r['id'] in wanted:
            n = wanted.pop(r['id'])
            r['servings'] = n
            r['servings_default'] = n
            done += 1
    if wanted:
        print(f'  ⚠ ids introuvables : {sorted(wanted)}')
    tmp = Path(RECIPES_PATH).with_suffix('.tmp')
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding='utf-8', newline='\n')
    tmp.replace(RECIPES_PATH)
    print(f'  {done} recettes mises à jour → {RECIPES_PATH}')
    print('  Relancer ensuite : build_derived_base_registry.py puis rebuild_graphs.py')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'scripts/recipes/servings_proposals.csv'))
    ap.add_argument('--apply', metavar='CSV')
    ap.add_argument('--components', action='store_true',
                    help='préparations de base : portions de référence en grammes')
    args = ap.parse_args()
    if args.apply:
        apply(Path(args.apply))
        return
    if args.components and args.out.endswith('servings_proposals.csv'):
        args.out = str(ROOT / 'scripts/recipes/servings_components_proposals.csv')
    rows = component_proposals() if args.components else proposals()
    out = Path(args.out)
    with open(out, 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ['id'], delimiter=';', lineterminator='\n')
        w.writeheader()
        w.writerows(rows)
    print(f'  {len(rows)} propositions → {out}')


if __name__ == '__main__':
    main()
