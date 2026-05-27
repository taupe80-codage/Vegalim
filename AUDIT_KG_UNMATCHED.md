# Audit `knowledge_graph_unified_v1.json` — nœuds non rattachés au dict v2

**Total nœuds KG :** 747
**Nœuds = IDs de recettes (à exclure de l'audit) :** 421 (issus de `recipe_nutrition_graph_v1.json`)
**Nœuds = ingrédients :** 326
**Ingrédients NON résolus dans le dict v2 / alias_index :** 175

## Stratégies par catégorie

| Catégorie | Compte | Action |
|---|---|---|
| fr_accented | 0 | **(R)** remap FR→EN dans le graphe via script |
| fr_unaccented | 29 | **(R)** remap FR→EN dans le graphe via script |
| easy_pluralization | 1 | **(A)** ajouter dans `alias_index` du dict v2 |
| likely_alias_to_add | 145 | **(A)** ajouter dans `alias_index` après validation manuelle |


## fr_accented (0)


## fr_unaccented (29)

- `bouillon_dashi_vegetarien`
- `concentre_de_tomate`
- `etoile_de_badiane`
- `farine_de_manioc`
- `farine_de_pois_chiche`
- `farine_de_seigle`
- `farine_de_teff`
- `fecule_de_tapioca`
- `feuille_laurier`
- `feuilles_de_taro`
- `feuilles_filo`
- `feuilles_nori`
- `flocons_d_avoine`
- `gateaux_de_riz`
- `graines_de_moutarde`
- `huile_de_palme`
- `huile_friture`
- `jus_de_citron_vert`
- `noix_de_muscade`
- `nouilles_de_patate_douce`
- `nouilles_ramen`
- `nouilles_reshteh`
- `oeuf`
- `oeufs_dur`
- `pommes_de_terre`
- `sauce_brune_vegetarienne`
- `sauce_okonomiyaki`
- `sauce_soja`
- `sauce_tomate`

## easy_pluralization (1)

- `lentil`

## likely_alias_to_add (145)

- `amchur`
- `aneth`
- `attieke`
- `baguette`
- `bamboo_shoot`
- `banana_oat_porridge`
- `bean`
- `bean_sprout`
- `bechamel`
- `bell_pepper`
- `berbere`
- `black_bean_cooked`
- `black_eyed_bean_cooked`
- `bok_choy`
- `bouillon`
- `bread`
- `cacahuete`
- `capre`
- `chana_dal`
- `cheese`
- `chicken`
- `chocolate`
- `coconut_oil`
- `corn_husk`
- `cream`
- `creme`
- `curry_leaf`
- `curry_paste`
- `daikon`
- `dark_chocolate`
- `default_user`
- `doubanjiang_paste`
- `dried_pea`
- `dried_seaweed`
- `empanada_dough`
- `falafel`
- `fecule`
- `fermented_leaf_gundruk`
- `flaxseed_oil`
- `flour`
- `follicular_phase`
- `fromage_en_grain`
- `galangal`
- `garam_masala`
- `ghee`
- `glass_noodles`
- `gnocchi`
- `gochugaru`
- `gochujang`
- `green_curry_paste`
- `ground_flaxseeds`
- `gyoza_wrapper`
- `haricots_geant`
- `harissa`
- `high_protein_user`
- `hoisin_sauce`
- `ingredients`
- `jackfruit`
- `japanese_curry_roux`
- `kaffir_lime_leaf`
- `kashk`
- `kimchi`
- `kombucha`
- `lait`
- `laksa_paste`
- `legume`
- `lemongrass`
- `lentil_soup`
- `loroco`
- `luteal_phase`
- `mais_hominy`
- `mala_broth`
- `marjolaine`
- `masa_harina`
- `mayonnaise`
- `menstrual_phase`
- `menthe`
- `milk`
- `mirin`
- `mole_sauce`
- `moutarde`
- `mushroom`
- `myrtill`
- `noodles`
- `oil`
- `okra`
- `olive_oil`
- `origan`
- `ovulatory_phase`
- `pain_pita`
- `palm_oil`
- `paneer`
- `panko_breadcrumbs`
- `pate_piment`
- `pepper`
- `pesto`
- `phyllo_sheet`
- `piment_coreen`
- `pistou`
- `pizza_dough`
- `poireau`
- `polenta`
- `precooked_corn_flour`
- `pumpkin_seeds`
- `ras_el_hanout`
- `recipes`
- `red_curry_paste`
- `reshteh_noodles`
- `rice_noodle`
- `rice_vinegar`
- `rice_wrapper`
- `roasted_vegetable_quinoa`
- `salmon`
- `sambar_powder`
- `sesame_oil`
- `shortcrust_pastry`
- `sichuan_pepper`
- `small_eggplant`
- `soba_noodles`
- `sparkling_water`
- `spatzle`
- `starch`
- `sumac`
- `sunflower_oil`
- `swiss_chard`
- `tahini`
- `tempura_flour`
- `teriyaki_sauce`
- `tofu_soyeux`
- `tomato_basil_salad`
- `tortilla`
- `truffle`
- `udon`
- `vegetable_oil`
- `vegetarian_fish_sauce`
- `vegetarian_oyster_sauce`
- `vegetarian_user`
- `vine_leaf`
- `water`
- `weekly_plan_luteal_example`
- `white_bean_cooked`
- `wonton_wrapper`
- `yeast`
- `zaatar`
- `ziti`
