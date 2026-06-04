import json, sys, io
from collections import Counter
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

tree = json.load(open('ingredients_tree_enriched_v2.json', encoding='utf-8'))

ORIGINS = {
    # VACHE
    'ing_04966':'vache', 'ing_04968':'vache', 'ing_04970':'vache',
    'ing_04974':'vache', 'ing_04976':'vache', 'ing_04978':'vache',
    'ing_04983':'vache', 'ing_04985':'vache', 'ing_04987':'vache',
    'ing_04989':'vache', 'ing_04991':'vache', 'ing_04993':'vache',
    'ing_04995':'vache', 'ing_04999':'vache', 'ing_05001':'vache',
    'ing_05003':'vache', 'ing_05005':'vache', 'ing_05007':'vache',
    'ing_05009':'vache', 'ing_05011':'vache', 'ing_05015':'vache',
    'ing_05017':'vache', 'ing_05019':'vache', 'ing_05023':'vache',
    'ing_05029':'vache', 'ing_05033':'vache', 'ing_05035':'vache',
    'ing_05037':'vache', 'ing_05039':'vache', 'ing_05041':'vache',
    'ing_05043':'vache', 'ing_05045':'vache', 'ing_05047':'vache',
    'ing_05049':'vache', 'ing_05059':'vache', 'ing_05063':'vache',
    'ing_05065':'vache', 'ing_05075':'vache', 'ing_05077':'vache',
    'ing_05081':'vache', 'ing_05083':'vache', 'ing_05087':'vache',
    'ing_05091':'vache', 'ing_05095':'vache', 'ing_05097':'vache',
    'ing_05099':'vache', 'ing_05103':'vache', 'ing_05110':'vache',
    'ing_05118':'vache', 'ing_05120':'vache', 'ing_05126':'vache',
    'ing_05128':'vache', 'ing_05130':'vache', 'ing_05132':'vache',
    'ing_05134':'vache', 'ing_05170':'vache', 'ing_05172':'vache',
    'ing_05174':'vache', 'ing_05176':'vache', 'ing_05196':'vache',
    'ing_05198':'vache', 'ing_05202':'vache', 'ing_05204':'vache',
    'ing_05206':'vache', 'ing_05208':'vache', 'ing_05210':'vache',
    'ing_05212':'vache', 'ing_05214':'vache', 'ing_05216':'vache',
    'ing_05218':'vache', 'ing_05220':'vache', 'ing_05222':'vache',
    'ing_05224':'vache', 'ing_05228':'vache', 'ing_05232':'vache',
    'ing_05234':'vache', 'ing_05244':'vache', 'ing_05252':'vache',
    'ing_05254':'vache', 'ing_05256':'vache', 'ing_05258':'vache',
    'ing_05260':'vache', 'ing_05266':'vache', 'ing_05268':'vache',
    'ing_05270':'vache', 'ing_05272':'vache', 'ing_05274':'vache',
    'ing_05280':'vache', 'ing_05284':'vache', 'ing_05286':'vache',
    'ing_05288':'vache', 'ing_05290':'vache', 'ing_05293':'vache',
    'ing_05297':'vache', 'ing_05301':'vache', 'ing_05303':'vache',
    'ing_05305':'vache', 'ing_05309':'vache', 'ing_05313':'vache',
    'ing_05315':'vache', 'ing_05349':'vache', 'ing_05355':'vache',
    'ing_05357':'vache', 'ing_05361':'vache', 'ing_05365':'vache',
    'ing_05367':'vache', 'ing_05373':'vache', 'ing_05387':'vache',
    'ing_04395':'vache',
    # BREBIS
    'ing_05025':'brebis', 'ing_05085':'brebis', 'ing_05136':'brebis',
    'ing_05138':'brebis', 'ing_05140':'brebis', 'ing_05264':'brebis',
    'ing_05369':'brebis',
    # CHEVRE
    'ing_05031':'chèvre', 'ing_05093':'chèvre', 'ing_05101':'chèvre',
    'ing_05142':'chèvre', 'ing_05144':'chèvre', 'ing_05146':'chèvre',
    'ing_05148':'chèvre', 'ing_05152':'chèvre', 'ing_05154':'chèvre',
    'ing_05156':'chèvre', 'ing_05158':'chèvre', 'ing_05242':'chèvre',
    'ing_05246':'chèvre', 'ing_05250':'chèvre', 'ing_05262':'chèvre',
    'ing_05371':'chèvre', 'ing_05408':'chèvre',
    # BUFFLONNE
    'ing_05051':'bufflonne', 'ing_05053':'bufflonne',
    'ing_05055':'bufflonne', 'ing_05057':'bufflonne',
}

ORIGINS_EN = {
    'vache':'cow', 'brebis':'sheep', 'chèvre':'goat', 'bufflonne':'buffalo'
}

ing_map = {}
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        for ing in cat2.get('ingredient_groups', []):
            ing_map[ing['id']] = ing

already_ok, added, skipped = 0, 0, 0
for ing_id, origine in ORIGINS.items():
    ing = ing_map.get(ing_id)
    if not ing:
        skipped += 1
        continue
    current = ing.get('axes_fr', {}).get('origine')
    if current == origine:
        already_ok += 1
    else:
        ing.setdefault('axes_fr', {})['origine'] = origine
        ing.setdefault('axes_en', {})['origin']  = ORIGINS_EN[origine]
        added += 1

json.dump(tree, open('ingredients_tree_enriched_v2.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

print(f'Deja corrects   : {already_ok}')
print(f'Ajoutes/corriges: {added}')
print(f'Introuvables    : {skipped}')
print()

counts = Counter()
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        if cat2.get('label') == 'cheeses':
            for ing in cat2.get('ingredient_groups', []):
                orig = ing.get('axes_fr', {}).get('origine', 'MANQUANT')
                counts[orig] += 1

print('Repartition origines :')
for k, v in sorted(counts.items()):
    print(f'  {k}: {v}')

no_orig = []
for cat1 in tree['categories']:
    for cat2 in cat1['subcategories']:
        if cat2.get('label') == 'cheeses':
            for ing in cat2.get('ingredient_groups', []):
                if not ing.get('axes_fr', {}).get('origine'):
                    no_orig.append(f"{ing['id']}  {ing.get('canonical_name_fr','')}")
if no_orig:
    print(f'\nSans origine ({len(no_orig)}) :')
    for x in no_orig:
        print(' ', x)
else:
    print('\nTous les fromages ont une origine.')
print('OK.')
