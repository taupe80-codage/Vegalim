import json
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
tree = json.load(open(BASE / 'ingredients_tree.json', encoding='utf-8'))

# Tous les ing_ concernes (originaux + nouveaux)
check_ids = [
    'ing_01059','ing_05735',          # figue sechee
    'ing_01408','ing_05736',          # jus orange
    'ing_01540','ing_05737',          # pomme
    'ing_05428','ing_05749',          # lait UHT
    'ing_05507','ing_05750',          # lait poudre
    'ing_01605','ing_05738',          # pomme de terre rouge
    'ing_03777','ing_05741',          # haricot cannellini
    'ing_01670','ing_05739',          # pomme de terre nouvelle
    'ing_03858','ing_05742',          # haricot blanc / great northern
    'ing_01676','ing_05740',          # pomme de terre rotie
    'ing_03921','ing_05743',          # haricot navy
    'ing_03925','ing_05744',          # haricot pinto
    'ing_05688','ing_05745','ing_05746','ing_05747','ing_05748',  # oeufs
]

# Etat attendu : axes_fr attendu + coherence avec variant
EXPECTED = {
    # figues
    'ing_01059': {'axes_fr': {'etat_thermique': 'séché', 'etat_cuisson': 'cuit'},     'nb_variants': 1, 'source_key': 'Fig, dried, cooked'},
    'ing_05735': {'axes_fr': {'etat_thermique': 'séché'},                              'nb_variants': 1, 'source_key': 'Fig, dried, uncooked'},
    # jus orange
    'ing_01408': {'axes_fr': {'forme': 'jus', 'traitement': 'sans pulpe', 'etat_thermique': 'réfrigéré'}, 'nb_variants': 1, 'source_key': 'not from concentrate'},
    'ing_05736': {'axes_fr': {'forme': 'jus', 'traitement': 'à base de concentré', 'etat_thermique': 'réfrigéré'}, 'nb_variants': 1, 'source_key': 'from concentrate'},
    # pomme
    'ing_01540': {'axes_fr': {'etat_cuisson': 'cru'},                                  'nb_variants': 1, 'source_key': 'with skin'},
    'ing_05737': {'axes_fr': {'etat_cuisson': 'cru', 'partie': 'sans peau'},           'nb_variants': 1, 'source_key': 'without skin'},
    # lait UHT
    'ing_05428': {'axes_fr': {'teneur_MG': 'écrémé', 'etat_thermique': 'UHT'},        'nb_variants': 1, 'source_key': 'écrémé, UHT'},
    'ing_05749': {'axes_fr': {'teneur_MG': 'demi-écrémé', 'etat_thermique': 'UHT'},   'nb_variants': 1, 'source_key': 'demi-écrémé, UHT'},
    # lait poudre
    'ing_05507': {'axes_fr': {'forme': 'poudre', 'teneur_MG': 'écrémé'},              'nb_variants': 1, 'source_key': 'écrémé'},
    'ing_05750': {'axes_fr': {'forme': 'poudre', 'teneur_MG': 'demi-écrémé'},         'nb_variants': 1, 'source_key': 'demi-écrémé'},
    # pdt rouge
    'ing_01605': {'axes_fr': {'etat_cuisson': 'cru', 'partie': 'avec peau'},           'nb_variants': 1, 'source_key': 'flesh and skin'},
    'ing_05738': {'axes_fr': {'etat_cuisson': 'cru', 'partie': 'sans peau'},           'nb_variants': 1, 'source_key': 'without skin'},
    # cannellini
    'ing_03777': {'axes_fr': {'etat_thermique': 'séché'},                              'nb_variants': 1, 'source_key': 'dry'},
    'ing_05741': {'axes_fr': {'conditionnement': 'conserve', 'egouttage': 'égoutté'}, 'nb_variants': 1, 'source_key': 'canned'},
    # pdt nouvelle
    'ing_01670': {'axes_fr': {'etat_cuisson': 'bouilli'},                              'nb_variants': 1, 'source_key': 'bouillie'},
    'ing_05739': {'axes_fr': {'etat_cuisson': 'bouilli', 'partie': 'sans peau'},       'nb_variants': 1, 'source_key': 'sans peau'},
    # haricot blanc / great northern
    'ing_03858': {'axes_fr': {'etat_thermique': 'séché'},                              'nb_variants': 1, 'source_key': 'sec'},
    'ing_05742': {'axes_fr': {'conditionnement': 'conserve', 'egouttage': 'égoutté'}, 'nb_variants': 1, 'source_key': 'canned'},
    # pdt rotie
    'ing_01676': {'axes_fr': {'etat_cuisson': 'rôti'},                                 'nb_variants': 1, 'source_key': 'rôtie'},
    'ing_05740': {'axes_fr': {'etat_cuisson': 'rôti', 'partie': 'sans peau'},          'nb_variants': 1, 'source_key': 'sans peau'},
    # navy
    'ing_03921': {'axes_fr': {'etat_thermique': 'séché'},                              'nb_variants': 1, 'source_key': 'dry'},
    'ing_05743': {'axes_fr': {'conditionnement': 'conserve', 'egouttage': 'égoutté'}, 'nb_variants': 1, 'source_key': 'canned'},
    # pinto
    'ing_03925': {'axes_fr': {'etat_thermique': 'séché'},                              'nb_variants': 1, 'source_key': 'dry'},
    'ing_05744': {'axes_fr': {'conditionnement': 'conserve', 'egouttage': 'égoutté'}, 'nb_variants': 1, 'source_key': 'canned'},
    # oeufs
    'ing_05688': {'axes_fr': {'etat_cuisson': 'dur'},     'nb_variants': 1, 'source_key': 'dur'},
    'ing_05745': {'axes_fr': {'etat_cuisson': 'au plat'}, 'nb_variants': 1, 'source_key': 'au plat'},
    'ing_05746': {'axes_fr': {'etat_cuisson': 'coque'},   'nb_variants': 1, 'source_key': 'coque'},
    'ing_05747': {'axes_fr': {'etat_cuisson': 'poché'},   'nb_variants': 1, 'source_key': 'poché'},
    'ing_05748': {'axes_fr': {'etat_cuisson': 'brouillé'},'nb_variants': 1, 'source_key': 'brouillé'},
}

ing_map = {}
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        for ing in cat2.get('ingredient_groups', []):
            if ing['id'] in check_ids:
                ing_map[ing['id']] = ing

ok = 0
ko = []

print('VERIFICATION des axes_fr apres split')
print('=' * 72)

for ing_id in check_ids:
    ing = ing_map.get(ing_id)
    exp = EXPECTED.get(ing_id, {})
    if not ing:
        ko.append(ing_id + ' : NON TROUVE dans le tree')
        continue

    errors = []
    actual_axes = ing.get('axes_fr', {})
    expected_axes = exp.get('axes_fr', {})
    nb_var = len(ing.get('variants', []))
    exp_nb  = exp.get('nb_variants', 1)

    # Verifier axes_fr
    if actual_axes != expected_axes:
        errors.append('axes_fr KO  attendu=' + str(expected_axes) + '  reel=' + str(actual_axes))

    # Verifier nb variants
    if nb_var != exp_nb:
        errors.append('nb_variants KO  attendu=' + str(exp_nb) + '  reel=' + str(nb_var))

    # Verifier coherence axes_fr ing == axes_fr variant (si 1 seul variant)
    variants = ing.get('variants', [])
    if variants:
        var = variants[0]
        var_axes = var.get('axes_fr', {})
        # Les axes de l'ing doivent etre un sous-ensemble ou egal aux axes du variant
        inconsistent = {k: v for k, v in actual_axes.items() if k in var_axes and var_axes[k] != v}
        if inconsistent:
            errors.append('incoherence ing/variant axes: ' + str(inconsistent))

    cfr = ing.get('canonical_name_fr', '')
    cen = ing.get('canonical_name_en', '')

    if errors:
        ko.append(ing_id)
        print('KO  ' + ing_id + '  ' + cfr)
        for e in errors:
            print('      ' + e)
    else:
        ok += 1
        src = exp.get('source_key', '')
        print('OK  ' + ing_id + '  ' + cfr + '  axes=' + str(actual_axes))

print()
print('=' * 72)
print('OK : ' + str(ok) + '/' + str(len(check_ids)))
if ko:
    print('KO : ' + str(len(ko)))
    for k in ko:
        print('  ' + k)
else:
    print('Tous les axes sont corrects.')
