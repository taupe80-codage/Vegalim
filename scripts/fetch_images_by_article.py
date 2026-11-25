"""
Vegalim — Photos choisies par article encyclopédique, désigné à la main
=======================================================================

Les recherches automatiques (fetch_recipe_images_free.py, fetch_images_by_dish.py)
ont laissé ~220 recettes sans photo : leur titre ne permet pas de deviner le
plat (« Kadhi gujarati sucré-acidulé… », « Pois chiches rôtis » = leblebi).
Ici, chaque recette est associée À LA MAIN à l'article Wikipédia de son plat
(ARTICLES), et l'on prend l'image principale de cet article.

Les garde-fous de fetch_recipe_images_free.py restent appliqués : licence libre
(ni NC ni ND), viande ou poisson dans le titre ou les catégories de l'image,
liste noire des photos déjà écartées.

Deux temps, parce que l'image d'un article de plat montre souvent la version
carnée (bigos, plov, caldo verde au chouriço) et que seul l'œil le voit :

    python scripts/fetch_images_by_article.py --stage DIR
        télécharge dans DIR, écrit DIR/_manifest.json et une planche-contact
    python scripts/fetch_images_by_article.py --publish DIR --reject id1 id2 … --pick id3=2 …
        copie les photos retenues dans frontend/public/images/recipes, crédite,
        et met les rejetées en liste noire

--candidates N garde jusqu'à N photos par recherche Commons (planches
DIR/_planche_NN.jpg numérotées) ; --pick id=k retient la k-ième.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import shutil
import sys
import time
import unicodedata
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "fetch_free", Path(__file__).parent / "fetch_recipe_images_free.py")
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)

import requests  # noqa: E402

# Agent générique : aucune donnée personnelle dans les requêtes.
UA = "VegalimRecipePhotos/1.0 (recipe photo lookup on Wikipedia/Commons)"
F.UA_DOWNLOAD = UA

# id (ou début d'id, sans ambiguïté) de recette → articles candidats
# « langue:Titre », essayés dans l'ordre.
ARTICLES: dict[str, list[str]] = {
    "brkf_crepes_sucrees_e5d14e": ["en:Crêpe"],
    "dessert_crepes_bretonnes_7b9": ["en:Crêpe"],
    "brkf_ojja_vegan_dbbad8": ["en:Ojja", "fr:Ojja"],
    "egg_ojja_5bdbea": ["en:Ojja", "fr:Ojja"],
    "brkf_tofu_brouille_aux_herbe": ["en:Tofu scramble"],
    "crepe_galette_de_teff_a1a8d3": ["en:Injera"],
    "curry_japanese_classic_v3_m8": ["en:Japanese curry"],
    "curry_japonais_1caddf": ["en:Japanese curry"],
    "dal_ethiopian_atkilt_wat_afd": ["en:Atakilt wat"],
    "side_atakilt_wat_2f66c9": ["en:Atakilt wat"],
    "dal_kadhi_pakora_078de2": ["en:Kadhi"],
    "dal_kadhi_pakora_vegan_5cb5d": ["en:Kadhi"],
    "dal_makhani_vegan_259219": ["en:Rajma"],
    "main_rajma_masala_bce2a4": ["en:Rajma"],
    "dal_pois_chiches_rotis_ff8cc": ["en:Leblebi"],
    "dal_salade_de_lentilles_ethi": ["en:Azifa"],
    "dal_sambar_581de8": ["en:Sambar (dish)"],
    "dal_sambar_indien_fcf6d8": ["en:Sambar (dish)"],
    "dal_soupe_de_pois_chiches_tu": ["en:Lablabi"],
    "dal_turkish_mercimek_soup_a7": ["en:Mercimek çorbası", "tr:Mercimek çorbası"],
    "dal_soupe_lentilles_turque_e": ["en:Mercimek çorbası", "tr:Mercimek çorbası"],
    "dessert_far_breton_aux_prune": ["en:Far breton"],
    "dessert_halva_de_sesame_87a7": ["en:Tahini halva", "en:Halva"],
    "dessert_tarte_tatin_9c0f67": ["en:Tarte Tatin"],
    "egg_galettes_de_pommes_de_terre_tc_4f360c": ["en:Potato pancake"],
    "egg_quiche_lorraine_vegetari": ["en:Quiche"],
    "tarte_quiche_vegetarienne_b8": ["en:Quiche"],
    "entry_salmorejo_vegan_d0b7f7": ["en:Ajoblanco"],
    "main_aligot_c03237": ["en:Aligot", "fr:Aligot"],
    "main_aubergines_sichuan_ff99": ["en:Yuxiang eggplant", "en:Fish-fragrant eggplant"],
    "main_briam_f33bb8": ["en:Briam"],
    "main_greek_briam_4091c5": ["en:Briam"],
    "main_greek_briam_vegan_3fb05": ["en:Briam"],
    "main_caldo_verde_72b654": ["en:Caldo verde", "pt:Caldo verde"],
    "main_crepe_complete_1d0fb7": ["fr:Galette de sarrasin", "en:Galette"],
    "main_galettes_sarrasin_ce9f4": ["fr:Galette de sarrasin", "en:Galette"],
    "main_fried_rice_a6e811": ["en:Egg fried rice"],
    "base_fried_rice_f230b0": ["en:Fried rice"],
    "main_haricots_blancs_au_four": ["en:Baked beans"],
    "main_horta_b898d5": ["en:Horta (food)"],
    "main_kimchi_1dc648": ["en:Kimchi"],
    "main_polenta_aux_champignons_5af074": ["en:Polenta"],
    "main_varenyky_pomme_de_terre": ["en:Varenyky"],
    "pasta_gnocchis_a_la_tomate_v": ["en:Gnocchi"],
    "pasta_lagman_aaae70": ["en:Lagman (food)"],
    "pasta_mac_and_cheese_b3073b": ["en:Macaroni and cheese"],
    "pasta_pasta_alla_norma_a_la_": ["en:Pasta alla Norma"],
    "protein_pad_thai_vegan_33c0f": ["en:Pad thai"],
    "wok_thai_veg_eb92db": ["en:Pad thai"],
    "protein_paneer_butter_masala": ["en:Navratan korma"],
    "rice_dolma_au_persil_6aeb1e": ["en:Dolma"],
    "rice_goi_cuon_efb313": ["en:Gỏi cuốn"],
    "starter_rouleaux_crus_cacahu": ["en:Gỏi cuốn"],
    "rice_jeera_rice_a4633c": ["en:Jeera rice"],
    "rice_kimbap_4cb3da": ["en:Gimbap"],
    "rice_nasi_goreng_edfce4": ["en:Nasi goreng"],
    "rice_nasi_goreng_vegan_bcc9c": ["en:Nasi goreng"],
    "rice_risotto_ai_funghi_vegan": ["it:Risotto ai funghi", "en:Risotto"],
    "rice_risotto_aux_champignon_": ["it:Risotto ai funghi", "en:Risotto"],
    "rice_sabzi_polo_e099d2": ["en:Sabzi polo"],
    "rice_serbian_uve_4a83e2": ["en:Đuveč"],
    "rice_tacu_tacu_9e0073": ["en:Tacu tacu"],
    "salad_achichuk_e3f0c9": ["en:Achichuk"],
    "salad_gadogado_indonesien_ve": ["en:Pecel"],
    "salad_grecque_classique_vega": ["en:Greek salad"],
    "salad_tabbouleh_f7x2p9": ["en:Tabbouleh"],
    "salad_turque_coban_cdd8c4": ["en:Çoban salatası"],
    "side_eggplant_k1d1p1": ["en:Wambatu moju"],
    "side_farofa_bresilienne_vega": ["en:Farofa"],
    "side_riz_pilaf_turc_vegan_3b": ["en:İç pilav"],
    "side_rosti_4ec9f8": ["en:Rösti"],
    "snack_rosti_vegan_be15a2": ["en:Rösti"],
    "side_tian_provencal_vegan_88": ["en:Tian (food)", "fr:Tian (cuisine)"],
    "snack_gozleme_aux_epinards_v": ["en:Gözleme"],
    "snack_humita_andine_vegan_1f": ["en:Humita"],
    "soup_a_l_oignon_gratinee_veg": ["en:French onion soup"],
    "soup_soup_k3d2p1": ["en:French onion soup"],
    "soup_potage_parmentier_9685a": ["fr:Potage Parmentier", "en:Leek soup"],
    "wrap_quesadillas_au_fromage_ve_9794c7": ["en:Quesadilla"],
    "side_gomen_ethiopien_4d10a7": ["en:Gomen (dish)", "en:Gomen"],
    "main_red_red_ghaneen_1c8f70": ["en:Red red"],
    "soup_arachide_legumes_5f21b4": ["en:Groundnut soup", "en:Peanut soup"],
    "main_mafe_legumes_9c40d7": ["en:Maafe"],
    "noodle_khao_soi_vegetarien_6": ["en:Khao soi"],
    "curry_massaman_legumes_9d51a": ["en:Massaman curry"],
    "salad_yam_woon_sen_2d95e8": ["en:Yam wun sen"],
    "pasta_al_limone_2a68d3": ["en:Pasta al limone"],
    "soup_oeufs_mais_chinoise_5c3": ["en:Egg drop soup"],
    "soup_sopa_de_ajo_9e12b7": ["en:Sopa de ajo", "en:Garlic soup"],
    "brkf_congee_gingembre_8b5d24": ["en:Congee"],
    "starter_balila_pois_chiches_": ["en:Balila"],
    "stew_porotos_granados_6a35c9": ["en:Porotos granados"],
    "stew_locro_courge_mais_3c7e9": ["en:Locro"],
    "main_vatapa_legumes_7d19c3": ["en:Vatapá"],
    "rice_moros_y_cristianos_6c83": ["en:Moros y Cristianos (dish)", "en:Moros y cristianos"],
    "soup_ajiaco_legumes_8e40b6": ["en:Ajiaco"],
    "soup_gumbo_z_herbes_8c52b3": ["en:Gumbo z'herbes"],
    "snack_chou_fleur_buffalo_9a4": ["en:Buffalo cauliflower"],
    "brkf_burrito_dejeuner_8d05c2": ["en:Breakfast burrito"],
    "dessert_pumpkin_pie_4f85b0": ["en:Pumpkin pie"],
    "dessert_tarte_au_sucre_9b18e": ["en:Sugar pie"],
    "soup_zurek_vegetarien_7d41c9": ["en:Żurek"],
    "entry_korozott_3e94b2": ["en:Körözött"],
    "side_knedliky_7b53c2": ["en:Knedlík", "en:Czech dumplings"],
    "side_kacha_sarrasin_champign": ["en:Kasha"],
    "salad_olivier_vegetarienne_8": ["en:Olivier salad"],
    "beverage_lassi_mangue_6c28f1": ["en:Lassi"],
    # « en:Agua fresca » est illustré par de l'horchata : écarté
    "beverage_agua_fresca_pastequ": [],
    "brkf_chilla_pois_chiches_2f9": ["en:Cheela", "en:Chilla (food)"],
    "main_tomates_oeufs_sautes_5f": ["en:Stir-fried tomato and scrambled eggs"],
    "side_haricots_verts_sichuan_": ["en:Dry-fried green beans"],
    "noodle_nouilles_froides_sesa": ["en:Cold noodles with sesame sauce"],
    "side_pommes_terre_aigre_piqu": ["en:Hot and sour shredded potatoes"],
    "side_kootu_courge_lentilles_": ["en:Kootu"],
    "main_kottu_roti_legumes_7e19": ["en:Kottu"],
    "snack_chatamari_nepalaise_2b": ["en:Chatamari"],
    "entry_cacik_9d1f4e": ["en:Cacık", "en:Tzatziki"],
    "snack_mucver_51d9c4": ["en:Mücver"],
    "side_loubieh_bi_zeit_6f2b19": ["en:Loubieh"],
    "main_bamia_8d40f6": ["en:Bamia"],
    "main_khoresh_bademjan_b62c85": ["en:Khoresh bademjan"],
    "beverage_sahlab_8c04f2": ["en:Salep"],
    "side_rotkohl_9c4e21": ["de:Rotkohl"],
    "main_stamppot_boerenkool_8f5": ["en:Stamppot"],
    "soup_erwtensoep_2d19b6": ["en:Snert"],
    "snack_festival_jamaicain_c3f": ["en:Festival (food)"],
    "main_colombo_legumes_58a0e1": ["en:Colombo (dish)", "fr:Colombo (cuisine)"],
    "dessert_ladob_banane_9b6318": ["en:Ladob"],
    "brkf_msemen_6e1a38": ["en:Msemen"],
    "snack_brik_oeuf_2a7e64": ["en:Brik"],
    "beverage_barley_water_citron": ["en:Barley water"],
    "brkf_oeufs_brouilles_ciboule": ["en:Scrambled eggs"],
    # ── 2026-11-20 : plats jamais tentés, dont les lots n15-n17 ──────────────────────────
    # (articles dont l'image principale montre presque sûrement la version carnée laissés
    # de côté : bigos, plov, bun cha, niçoise, pot-au-feu, navarin, waterzooi, köttbullar…)
    "dal_armenian_lentil_soup_0f1067": ["en:Lentil soup"],
    "dal_persian_lentil_soup_71e221": ["en:Adasi", "fa:عدسی"],
    "main_haricots_rouges_a_la_toma_c44560": ["en:Red red"],
    "rice_risotto_citron_asperges_f2f765": ["it:Asparago bianco di Bassano"],
    "salad_de_poivrons_et_tomates_d5f4ec": ["en:Taktouka", "fr:Taktouka"],
    "side_jeera_rice_vegan_694fd1": ["en:Jeera rice"],
    "wok_pad_pak_ruam_4f27b6": ["en:Phat phak ruam"],
    "side_bharwa_bhindi_3e74a9": ["en:Bhindi masala"],
    "noodle_mine_frite_5d9c02": ["en:Mine frite", "fr:Mine frite"],
    "pasta_orecchiette_brocoli_3a71c4": ["en:Orecchiette"],
    "egg_anda_curry_7f13b8": ["en:Egg curry"],
    "bread_piadina_legumes_grilles_2c86f9": ["en:Piadina"],
    "pasta_spaghetti_nerano_courgettes_e5c3a0": ["it:Spaghetti alla Nerano", "en:Spaghetti alla Nerano"],
    "brkf_sabudana_khichdi_c8f461": ["en:Sabudana khichadi"],
    "brkf_pesarattu_mungo_7d2c39": ["en:Pesarattu"],
    "brkf_porridge_sarrasin_pomme_b37e90": ["en:Kasha"],
    "brkf_bubur_ketan_hitam_4a8d16": ["en:Bubur ketan hitam", "id:Bubur ketan hitam"],
    "brkf_granola_sarrasin_noisettes_0f5a72": ["en:Granola"],
    "pasta_pizzoccheri_valtellina_6e2d81": ["en:Pizzoccheri"],
    "pasta_croziflette_poireaux_1b47c9": ["fr:Croziflette"],
    "side_hutspot_carottes_oignons_a4e7f3": ["en:Hutspot"],
    "curry_pois_chiches_tofu_coco_6a2f95": ["en:Kadala curry"],
    "stew_vignarola_romaine_5e1a07": ["it:Vignarola", "en:Vignarola"],
    "egg_revuelto_esparragos_trigueros_6a2b38": ["es:Revuelto"],
    "curry_matar_paneer_4a7c19": ["en:Mattar paneer"],
    "starter_asperges_a_la_flamande_1e6b84": ["nl:Asperges op Vlaamse wijze"],
    "side_asperges_goma_ae_8c1f47": ["en:Goma-ae"],
    "soup_potage_oseille_0f7d29": ["en:Sorrel soup"],
    "dessert_rhubarb_crumble_6d2f80": ["en:Crumble"],
    "dessert_eton_mess_fraises_2b7a94": ["en:Eton mess"],
    "dessert_kirschenmichel_cerises_7e3c06": ["de:Kirschenmichel"],
    "side_dauphinois_vegan_c584cb": ["fr:Gratin dauphinois"],
    "side_lentilles_du_puy_echalote_37c76e": ["fr:Lentille verte du Puy"],
    "protein_halloumi_pois_chiches_rotis_7c40e2": ["en:Halloumi"],
    # 2026-11-20 : 3e passe, plats qui ont un article (les autres sont génériques)
    "dal_lebanese_lentil_soup_eae561": ["en:Adas bi hamod", "en:Lentil soup"],
    "main_chili_sin_carne_125ff2": ["en:Vegetarian chili", "fr:Chili sin carne", "commons:vegetarian chili beans"],
    "salad_nicoise_3b123f": ["en:Salade niçoise", "fr:Salade niçoise"],
    "soup_de_potiron_caribeenne_a0fabd": ["en:Pumpkin soup", "fr:Soupe au potiron"],
    "soup_potage_de_patate_douce_e4b521": ["en:Sweet potato soup", "commons:sweet potato soup bowl"],
    "soup_soupe_courge_butternut_2f5cf3": ["en:Butternut squash soup", "en:Pumpkin soup"],
    "stew_persian_herb_stew_485f3e": ["en:Ghormeh sabzi"],
    "side_kale_massee_avocat_3d18e7": ["en:Kale salad", "commons:kale salad"],
    "rice_khao_pad_sapparot_9a40d3": ["en:Pineapple fried rice", "th:ข้าวผัดสับปะรด"],
    "brkf_muffins_polenta_myrtilles_e2b947": ["en:Corn muffin", "commons:blueberry cornmeal muffins"],
    "soup_veloute_panais_poire_5d0c8a": ["en:Parsnip soup", "commons:parsnip soup"],
    "protein_tofu_tikka_masala_3e8f45": ["en:Paneer tikka masala"],
    "stew_anginares_a_la_polita_8b2c46": ["el:Αγκινάρες α λα πολίτα", "en:Artichokes à la polita"],
    # 2026-11-20 : 4e passe, plats génériques sans article — recherche Commons choisie à la main
    "side_carottes_glacees_a_lerabl_1d1c44": ["commons:roasted carrots sesame"],
    "side_champignons_sautes_ail_pe_b477e2": ["commons:sauteed mushrooms parsley garlic"],
    "side_fenouil_braise_a_l_orange_a75916": ["commons:braised fennel"],
    "wok_pak_choi_saute_62b974": ["commons:stir fried bok choy"],
    "wok_tofu_saute_gingembre_soja_6e901c": ["commons:stir fried tofu ginger"],
    "salad_pois_chiches_express_b39e57": ["commons:chickpea salad feta"],
    "snack_toast_haricots_romarin_5f80d2": ["commons:white bean toast"],
    "wok_tofu_aigre_doux_ananas_8c2e15": ["commons:sweet and sour tofu pineapple"],
    "salad_lentilles_feta_croquante_4d95a1": ["commons:lentil salad feta"],
    "side_gratin_celeri_rave_noix_7a19e6": ["commons:celeriac gratin"],
    "side_endives_braisees_orange_3c5b17": ["commons:braised endives"],
    "side_choux_bruxelles_miso_sesame_8b26f0": ["commons:roasted brussels sprouts"],
    "side_panais_carottes_miel_thym_2e9d61": ["commons:roasted parsnips carrots"],
    "salad_lentilles_puy_tofu_fume_9a1c63": ["commons:puy lentil salad"],
    "protein_tempeh_patate_douce_cacahuete_4b7e90": ["commons:tempeh peanut sauce"],
    "soup_haricots_kale_tofu_fume_1d84c6": ["commons:white bean kale soup"],
    "side_radis_glaces_miel_3a8e51": ["commons:glazed radishes"],
    # 2026-11-24 : recettes jamais tentées (lots récents compris), recherche
    # Commons triée par pertinence et plusieurs candidats (--candidates).
    "bread_gong_bao_tofu_3f7cc1": ["commons:kung pao tofu"],
    "bread_katsu_bf3f1e": ["commons:tofu katsu curry"],
    "curry_aubergine_sri_lanka_bf8bcd": ["en:Wambatu moju", "commons:sri lankan eggplant curry"],
    "curry_d_aubergine_sri_lankais_72254d": ["en:Wambatu moju", "commons:sri lankan eggplant curry"],
    "curry_katsu_vegan_f2e6a3": ["commons:eggplant katsu curry"],
    "dal_afghan_sabzi_chalaw_18f6a5": ["commons:sabzi chalow"],
    "dal_boulettes_suedoises_2ac55d": ["commons:vegetarian meatballs lingonberry"],
    "dal_boulettes_suedoises_vegan_fea9f6": ["commons:vegan swedish meatballs"],
    "dal_galettes_de_pois_chiches_db4c7a": ["commons:chickpea patties"],
    "dal_lentil_shepherds_pie_vega_27455d": ["commons:vegan shepherd's pie"],
    "dal_soupe_de_lentilles_621239": ["commons:lentil vegetable soup"],
    "entry_pate_de_champignons_vegan_b2af97": ["commons:mushroom pâté"],
    "entry_terrine_legumes_du_soleil_e5e24a": ["commons:vegetable terrine"],
    "main_endives_au_gratin_6b58ee": ["commons:gratin d'endives"],
    "main_garbure_gasconne_545667": ["fr:Garbure"],
    "main_legumes_braises_7030b7": ["commons:braised vegetables"],
    "main_polenta_aux_champignons_v_b0e1ad": ["commons:polenta fries"],
    "main_potee_auvergnate_fcc003": ["fr:Potée auvergnate"],
    "pasta_lasagnes_de_legumes_ultra_9b6a4e": ["commons:vegetable lasagna"],
    "protein_bulgogi_tofu_fc5de9": ["commons:tofu bulgogi"],
    "protein_bun_f5c7db": ["commons:bún chay"],
    "protein_palak_paneer_vegan_bdac46": ["commons:chana palak"],
    "protein_tofu_braise_aux_champigno_c515dd": ["commons:braised tofu mushrooms"],
    "rice_bigos_497b21": ["commons:vegetarian bigos"],
    "rice_pad_krapow_63acfb": ["commons:pad kra pao tofu"],
    "rice_plov_903de4": ["commons:vegetarian plov"],
    "rice_poke_bowl_ee65ef": ["commons:tofu poke bowl"],
    "salad_andine_au_fromage_vegan_566f05": ["commons:quinoa black bean salad"],
    "salad_mexicaine_aux_haricots_949e62": ["commons:mexican bean salad"],
    "side_brocoli_roti_sauce_gribic_694128": ["commons:roasted broccoli"],
    "side_haricots_verts_a_la_greno_f1bdca": ["commons:green beans capers"],
    "soup_bouillabaisse_vegetarienne_1d9c92": ["commons:vegetable bouillabaisse"],
    "soup_haricots_au_lait_de_coco_207254": ["en:Maharagwe", "commons:beans coconut milk"],
    "soup_hot_pot_e7fc15": ["commons:vegetarian hot pot"],
    "stew_eggplant_classic_5d46a1": ["commons:eggplant stew"],
    "wok_pad_krapow_vegetarien_565aa9": ["commons:pad kra pao vegetarian"],
    "wok_seitan_poivrons_3f81c4": ["commons:seitan stir fry"],
    "stew_seitan_champignons_moutarde_7ac502": ["commons:seitan stew"],
    "salad_larb_champignons_2c7b40": ["commons:mushroom larb"],
    "curry_ca_ri_chay_5d90c8": ["commons:cà ri chay"],
    "noodle_vermicelles_tofu_citronnelle_8c33d1": ["commons:lemongrass tofu vermicelli"],
    "protein_tofu_adobo_8d40f3": ["commons:tofu adobo"],
    "salad_haricots_blancs_roquette_9c5b02": ["commons:white bean salad arugula"],
    "entry_carpaccio_courgettes_citron_9a26d4": ["commons:zucchini carpaccio"],
    "entry_roules_courgette_ricotta_c8a460": ["commons:involtini di zucchine"],
    "brkf_full_breakfast_vegetarien_6e05b3": ["commons:vegetarian full breakfast"],
    "side_salade_fenouil_cru_0b48e5": ["commons:fennel salad olives"],
    "side_chou_rouge_pomme_noix_5d7c19": ["commons:red cabbage apple salad"],
    "wrap_fajitas_champignons_5b9d02": ["commons:mushroom fajitas"],
    "pasta_epinards_ricotta_citron_d40a6e": ["commons:pasta spinach ricotta"],
    "bread_pita_pois_chiches_tzatziki_6b0e27": ["commons:chickpea pita"],
    "brkf_toasts_patate_douce_cacahuete_5c71e3": ["commons:sweet potato toast"],
    "stew_waterzooi_legumes_9c3a52": ["commons:vegetable waterzooi"],
    "stew_pot_au_feu_legumes_4f80d7": ["commons:vegetable pot-au-feu"],
    "tarte_tatin_legumes_racines_0d6b44": ["commons:vegetable tarte tatin"],
    "side_topinambours_marrons_6f31b2": ["commons:jerusalem artichoke chestnuts"],
    "protein_polpette_lenticchie_8d52c0": ["commons:lentil meatballs tomato sauce"],
    "protein_roti_seitan_herbes_2f6d18": ["commons:seitan roast"],
    "protein_tofu_chimichurri_haricots_5e93a7": ["commons:tofu chimichurri"],
    "main_spargel_sauce_hollandaise_3d9f15": ["commons:Spargel Sauce hollandaise Kartoffeln"],
    "stew_navarin_printanier_legumes_c47e90": ["commons:spring vegetable stew"],
    "tofu_saute_asperges_mange_tout_9f4d21": ["commons:tofu asparagus snow peas"],
    "tart_asperges_vertes_ricotta_2c85b3": ["commons:asparagus ricotta tart"],
    "pasta_fave_piselli_pecorino_7d3e52": ["commons:pasta fava beans peas"],
    "side_foul_akhdar_bi_zeit_5b9a63": ["commons:fresh fava beans olive oil"],
    "breakfast_tartine_petits_pois_feta_9a4b72": ["commons:smashed peas toast"],
    "main_soba_tofu_pak_choi_cacahuetes_4e81c2": ["commons:soba tofu bok choy"],
    "main_dahl_express_poireau_epinards_9c3a7e": ["commons:red lentil dal spinach"],
    "main_pois_chiches_kale_tahini_boulgour_7b2f41": ["commons:chickpeas kale tahini"],
    "main_tempeh_erable_choux_bruxelles_2d9e60": ["commons:tempeh brussels sprouts"],
    "main_seitan_poireaux_moutarde_5f0c38": ["commons:seitan leeks"],
    "main_frittata_epinards_feta_8a4d17": ["commons:spinach feta frittata"],
    "pasta_haricots_blancs_kale_parmesan_3e6b92": ["commons:pasta white beans kale"],
    "main_chili_sin_carne_lentilles_express_6c1e05": ["commons:lentil chili"],
    "main_tofu_croustillant_sesame_brocoli_0a7d53": ["commons:sesame tofu broccoli"],
    "main_quesadillas_haricots_noirs_cheddar_b5e294": ["commons:black bean quesadilla"],
    "salad_lentilles_chou_rouge_noix_feta_d40c8b": ["commons:lentil red cabbage salad"],
    "soup_miso_soba_tofu_epinards_71f6aa": ["commons:miso soba soup"],
    "brkf_tofu_brouille_champignons_epinards_e2c946": ["commons:tofu scramble mushrooms"],
    "brkf_porridge_soja_cacahuete_chanvre_58bd03": ["commons:peanut butter banana oatmeal"],
    "dess_poires_poelees_erable_noix_6f3b21": ["commons:pan fried pears"],
    "dess_glace_minute_banane_cacao_9a52e7": ["commons:banana nice cream"],
    "dess_pommes_poelees_crumble_avoine_c7e408": ["commons:sauteed apples oat crumble"],
    "dess_agrumes_hiver_pistaches_fleur_oranger_14d9b3": ["commons:citrus salad pistachio"],
    "main_potee_lentilles_chou_tofu_fume_8d1f52": ["commons:lentil cabbage stew"],
    "main_pot_au_feu_seitan_legumes_hiver_3a6c94": ["commons:vegetable pot-au-feu"],
    "main_curry_potimarron_pois_chiches_epinards_5c27e1": ["commons:pumpkin chickpea curry"],
    "main_galettes_sarrasin_poireaux_emmental_e04b77": ["commons:buckwheat galette leek"],
    "main_gnocchis_choux_bruxelles_sauge_noisettes_2b8a6d": ["commons:gnocchi brussels sprouts"],
    "main_chou_fleur_roti_epices_tahini_6e93c0": ["commons:roasted cauliflower tahini"],
    "side_topinambours_rotis_noisette_persil_8a2e10": ["commons:roasted jerusalem artichokes"],
    "side_navets_carottes_glaces_erable_0f5b92": ["commons:glazed turnips carrots"],
    "main_bourguignon_champignons_panais_4f2a81": ["commons:mushroom bourguignon"],
    "main_choux_bruxelles_tofu_fume_puree_panais_8c5d13": ["commons:parsnip puree"],
    "main_tajine_legumes_hiver_pois_chiches_2e9b70": ["commons:vegetable tagine"],
    "main_chili_butternut_haricots_noirs_6b0e42": ["commons:butternut squash black bean chili"],
    "soup_chou_fleur_celeri_rave_curry_3d7f50": ["commons:cauliflower soup"],
    "side_chou_rouge_saute_balsamique_graines_7a91c4": ["commons:sauteed red cabbage"],
    "dess_poires_pochees_vin_rouge_epices_5a1c8e": ["commons:poached pears red wine"],
    "dess_salade_oranges_kiwis_menthe_9d3f27": ["commons:orange kiwi salad"],
    "main_riz_saute_tofu_pak_choi_lowfodmap_1a4c7e": ["commons:tofu fried rice"],
    "main_curry_tofu_coco_courgette_lowfodmap_5e2b90": ["commons:tofu coconut curry"],
    "main_bowl_quinoa_legumes_rotis_feta_lowfodmap_8c3f14": ["commons:quinoa bowl roasted vegetables"],
    "main_tortilla_pommes_de_terre_ciboulette_lowfodmap_2f8d61": ["en:Spanish omelette"],
    "main_polenta_legumes_soleil_parmesan_lowfodmap_7b1e35": ["commons:creamy polenta vegetables"],
    "main_vermicelles_riz_tofu_oeuf_cacahuetes_lowfodmap_4d6a28": ["commons:vegetarian pad thai"],
    "main_tempeh_grille_pommes_persillees_haricots_lowfodmap_9e0c47": ["commons:grilled tempeh"],
    "main_galettes_quinoa_carottes_tahini_lowfodmap_3c5b82": ["commons:quinoa patties"],
    "main_oeufs_brouilles_epinards_cheddar_pdt_lowfodmap_6f2d19": ["commons:scrambled eggs spinach"],
    "salad_riz_concombre_tomate_feta_lowfodmap_0b7e53": ["commons:rice salad feta"],
    "soup_miso_vermicelles_tofu_pak_choi_lowfodmap_8d4a90": ["commons:miso soup tofu bok choy"],
    "soup_veloute_carottes_gingembre_coco_lowfodmap_2e6f71": ["commons:carrot ginger soup"],
    "soup_courgettes_pommes_de_terre_basilic_lowfodmap_5a9c03": ["commons:zucchini soup"],
    "brkf_porridge_amande_fraises_graines_lowfodmap_7c1d58": ["commons:oatmeal strawberries"],
    "dess_riz_coco_ananas_roti_lowfodmap_4b8e26": ["commons:coconut rice pudding pineapple"],
    "dess_salade_ananas_kiwi_fraises_menthe_lowfodmap_9f3a12": ["commons:pineapple kiwi strawberry salad"],
}

# 2026-11-24 : recettes dont l'article n'a rien donné AVANT le tri par
# pertinence de search_commons. Les articles sont épuisés (pas d'image libre,
# ou image carnée déjà écartée) : seule la recherche Commons est retentée.
# Clé = id de recette (ou début d'id) ; remplace la spec d'ARTICLES.
COMMONS_RETRY: dict[str, str] = {
    "brkf_ojja_vegan_dbbad8": "ojja tunisian",
    "brkf_tofu_brouille_aux_herbes": "tofu scramble herbs",
    "curry_japanese_classic_v3_m8": "vegetable japanese curry rice",
    "curry_japonais_1caddf": "kare raisu vegetable",
    "dal_ethiopian_atkilt_wat_afd": "atakilt wat",
    "dal_lebanese_lentil_soup": "adas bi hamod",
    "dal_persian_lentil_soup": "adasi lentil",
    "dal_salade_de_lentilles_ethi": "azifa lentil salad",
    "dal_soupe_de_pois_chiches_tu": "lablabi",
    "dal_soupe_lentilles_turque_e": "red lentil soup lemon",
    "dal_turkish_mercimek_soup_a7": "mercimek çorbası",
    "egg_galettes_de_pommes_de_terre_tc": "bramboráky",
    "egg_ojja_5bdbea": "ojja eggs",
    "egg_quiche_lorraine_vegetarienne": "onion quiche",
    "main_aligot": "aligot",
    "main_aubergines_sichuan": "yuxiang eggplant",
    "main_crepe_complete": "galette sarrasin oeuf fromage",
    "main_fried_rice": "egg fried rice scallions",
    "main_galettes_sarrasin_ce9f40": "galette sarrasin champignons",
    "main_haricots_rouges_a_la_toma": "red beans tomato stew",
    "main_horta": "horta greens olive oil",
    "main_polenta_aux_champignons_5af074": "grilled polenta mushrooms",
    "pasta_lagman": "lagman vegetarian",
    "protein_pad_thai_vegan": "vegan pad thai",
    "protein_paneer_butter_masala_vega": "vegetable korma",
    "rice_goi_cuon": "vegetarian spring rolls rice paper",
    "rice_kimbap": "vegetable kimbap",
    "rice_nasi_goreng_edfce4": "nasi goreng fried egg",
    "rice_nasi_goreng_vegan": "tempeh nasi goreng",
    "rice_risotto_ai_funghi_vegan": "mushroom risotto",
    "rice_risotto_aux_champignon": "risotto pleurotes",
    "rice_sabzi_polo": "sabzi polo tahdig",
    "rice_serbian_uve": "đuveč",
    "rice_tacu_tacu": "tacu tacu",
    "salad_achichuk": "achichuk",
    "salad_de_poivrons_et_tomates": "taktouka",
    "salad_nicoise": "vegetarian niçoise salad",
    "salad_turque_coban": "çoban salatası",
    "side_eggplant_k1d1p1": "wambatu moju",
    "side_lentilles_du_puy_echalote": "lentilles vertes du Puy",
    "side_riz_pilaf_turc_vegan": "iç pilav",
    "soup_potage_parmentier": "potato leek soup",
    "stew_persian_herb_stew": "ghormeh sabzi vegetarian",
    "tarte_quiche_vegetarienne": "vegetable quiche",
    "wok_thai_veg": "pad thai tofu egg",
    "side_gomen_ethiopien": "gomen collard greens",
    "side_atakilt_wat": "atakilt wat",
    "main_red_red_ghaneen": "red red plantain",
    "soup_arachide_legumes": "peanut soup vegetables",
    "main_mafe_legumes": "vegetable peanut stew",
    "noodle_khao_soi_vegetarien": "khao soi vegetarian",
    "curry_massaman_legumes": "massaman curry vegetable",
    "salad_yam_woon_sen": "yam woon sen",
    "wok_pad_pak_ruam": "thai stir fried vegetables",
    "pasta_al_limone": "pasta al limone",
    "soup_oeufs_mais_chinoise": "corn egg drop soup",
    "brkf_congee_gingembre": "congee mushrooms",
    "starter_balila_pois_chiches": "balila chickpeas",
    "stew_locro_courge_mais": "locro de zapallo",
    "main_vatapa_legumes": "vatapá",
    "rice_moros_y_cristianos": "moros y cristianos",
    "soup_ajiaco_legumes": "ajiaco",
    "soup_gumbo_z_herbes": "gumbo z'herbes",
    "snack_chou_fleur_buffalo": "buffalo cauliflower",
    "brkf_burrito_dejeuner": "breakfast burrito eggs beans",
    "soup_zurek_vegetarien": "żurek",
    "salad_olivier_vegetarienne": "olivier salad",
    "beverage_agua_fresca_pasteque": "watermelon agua fresca",
    "brkf_chilla_pois_chiches": "besan chilla",
    "starter_rouleaux_crus_cacahuete": "fresh spring rolls peanut sauce",
    "side_haricots_verts_sichuan": "dry fried green beans",
    "noodle_nouilles_froides_sesame": "sesame cold noodles",
    "side_pommes_terre_aigre_piquantes": "hot and sour shredded potatoes",
    "side_bharwa_bhindi": "bharwa bhindi",
    "main_kottu_roti_legumes": "vegetable kottu",
    "snack_chatamari_nepalaise": "chatamari",
    "snack_mucver": "mücver",
    "side_loubieh_bi_zeit": "loubieh bi zeit",
    "main_bamia": "bamia okra stew",
    "main_khoresh_bademjan": "khoresh bademjan",
    "beverage_sahlab": "sahlab",
    "side_rotkohl": "Rotkohl",
    "main_stamppot_boerenkool": "boerenkoolstamppot",
    "snack_festival_jamaicain": "festival jamaican",
    "main_colombo_legumes": "colombo curry",
    "noodle_mine_frite": "mine frite",
    "dessert_ladob_banane": "ladob",
    "beverage_barley_water_citron": "barley water lemon",
    "brkf_oeufs_brouilles_ciboulette": "scrambled eggs chives",
    "pasta_orecchiette_brocoli": "orecchiette broccoli",
    "egg_anda_curry": "egg curry",
    "bread_piadina_legumes_grilles": "piadina vegetables",
    "pasta_spaghetti_nerano_courgettes": "spaghetti alla nerano",
    "rice_khao_pad_sapparot": "pineapple fried rice",
    "bread_croque_champignons_comte_1e7b58": "croque champignons",
    "brkf_sabudana_khichdi": "sabudana khichdi",
    "brkf_bubur_ketan_hitam": "bubur ketan hitam",
    "pasta_croziflette_poireaux": "croziflette",
    "protein_tofu_tikka_masala": "tofu tikka masala",
    "curry_pois_chiches_tofu_coco": "chickpea coconut curry",
    "stew_vignarola_romaine": "vignarola",
    "stew_anginares_a_la_polita": "anginares a la polita",
    "egg_revuelto_esparragos_trigueros": "revuelto de espárragos",
    "starter_asperges_a_la_flamande": "asperges à la flamande",
    "side_asperges_goma_ae": "asparagus goma-ae",
}

# 2026-11-26 : photos retirées à la relecture (remove_wrong_photos_2026_11_26.py :
# viande visible, autre plat, personne). Recherche Commons à nouveau, avec
# plusieurs candidats (--candidates 3) ; les photos retirées sont en liste noire.
COMMONS_RETRY.update({
    "rice_adas_polo_74c1d9": "adas polo",
    "main_arepas_fromage_e3a54c": "arepa queso",
    "main_arepas_fromage_vegan_3a4125": "arepa avocado",
    "main_arepas_vegan_01b62b": "arepas",
    "pasta_persian_ash_reshteh_8cb79c": "ash reshteh",
    "side_sabzi_polo_vegan_7bf9df": "baghali polo",
    "side_baked_beans_melasse_5c93e7": "boston baked beans",
    "main_beignets_de_legumes_indon_e74ee9": "bakwan sayur",
    "base_peanut_butter_81c37b": "peanut butter jar",
    "rice_bibimbap_tofu_a265dc": "tofu bibimbap",
    "rice_bibimbap_classic_k91x2a": "vegetable bibimbap",
    "brkf_cachapa_fromage_4a2c85": "cachapa queso de mano",
    "entry_celeri_remoulade_d5d1b9": "céleri rémoulade",
    "base_buckwheat_crepe_03db22": "buckwheat crepe",
    "curry_japanese_4533d1": "kabocha curry",
    "rice_donburi_tofu_teriyaki_a71cfc": "tofu donburi",
    "side_epinards_a_la_creme_vegan_10afc3": "creamed spinach",
    "main_fasolakia_grecques_67b6d9": "fasolakia",
    "main_feijoada_2f6754": "vegan feijoada",
    "side_flageolets_a_la_bretonne_a2af15": "flageolets",
    "brkf_galette_sarrasin_champign_f6a798": "galette sarrasin champignons",
    "egg_galettes_de_pommes_de_terre_su_0d7814": "rårakor",
    "entry_gaspacho_de_melon_menthe_ee9907": "melon gazpacho",
    "dessert_gateau_au_yaourt_citron_f27832": "gâteau au yaourt",
    "pasta_gnocchi_al_pesto_vegan_954303": "gnocchi pesto",
    "main_gratin_de_navets_e164d6": "turnip gratin",
    "entry_halloumi_grille_2d6c85": "grilled halloumi",
    "soup_harira_classic_v3_p9x4k2": "harira",
    "noodle_hiyashi_chuka_8f42c1": "hiyashi chuka",
    "main_hoppin_john_4d80a9": "hoppin john",
    "dessert_ile_flottante_4623ef": "île flottante",
    "main_aubergines_parmigiana_sim_ad314c": "involtini di melanzane",
    "noodle_japchae_6e27b4": "japchae",
    "dessert_kheer_au_riz_ee0837": "rice kheer",
    "main_kibbeh_3d2be1": "pumpkin kibbeh",
    "rice_kimchi_bokkeumbap_2cbfe6": "kimchi fried rice cheese",
    "main_manakish_zaatar_580150": "manakish zaatar",
    "rice_maqluba_legumes_c15e82": "maqluba",
    "dal_de_lentilles_corail_vegan_8cc6a7": "masoor dal",
    "base_mayonnaise_0d3e4e": "mayonnaise bowl",
    "egg_menemen_681f60": "menemen",
    "dal_mercimek_koftesi_34f72d": "mercimek köftesi",
    "egg_mirza_ghasemi_454e24": "mirza ghasemi",
    "protein_moqueca_a65174": "moqueca de banana",
    "tarte_moussaka_veg_d55fa8": "vegetarian moussaka",
    "rice_mujadara_classic_ee2456": "mujaddara",
    "rice_nasi_lemak_vegetarien_9e4c60": "nasi lemak",
    "egg_pain_au_fromage_bresilien_603bf5": "pão de queijo",
    "dessert_pain_d_epices_754c93": "pain d'épices",
    "main_papaya_salad_918f58": "som tam",
    "main_aubergines_parmigiana_sim_e5028f": "parmigiana di melanzane",
    "main_baked_ziti_vegan_ad57f8": "baked ziti",
    "base_laksa_paste_bc7fd5": "laksa paste",
    "pasta_plain_k2d1p1": "pasta in bianco",
    "soup_pho_ba7e1e": "pho chay",
    "dumpling_pierogi_aux_pommes_de_ter_24a890": "pierogi ruskie",
    "pasta_pierogi_aux_pommes_de_6b3efe": "pierogi z kaszą",
    "dumpling_pierogi_aux_champignons_v_beca85": "pierogi z kapustą i grzybami",
    "main_plantain_frit_nature_323054": "fried plantain",
    "entry_provoleta_origan_5b81c7": "provoleta",
    "rice_white_k1d1p1": "bowl of white rice",
    "bread_roti_canai_5a2b71": "roti canai",
    "salad_de_pousses_de_soja_coreen_d07502": "kongnamul muchim",
    "salad_salade_mache_aux_noix_081567": "mâche salad",
    "main_sancocho_733f70": "sancocho",
    "main_sarmale_de_post_9f24b7": "sarmale",
    "egg_shakshuka_eb137b": "shakshuka",
    "brkf_smoothie_vert_epinards_ba_eb4142": "green smoothie spinach",
    "egg_sopa_paraguaya_43987c": "sopa paraguaya",
    "curry_sri_lankan_pumpkin_7f1edb": "pumpkin curry",
    "falafel_optimise_2f1451": "ta'amiya",
    "bread_tacos_6fd5c2": "vegetarian tacos",
    "main_tajine_citron_confit_c082f4": "vegetable tagine",
    "brkf_tamagoyaki_4d61c9": "tamagoyaki",
    "dessert_tarte_tatin_vegan_1ae13b": "pear tarte tatin",
    "main_tempura_de_legumes_20cc9f": "vegetable tempura",
    "entry_terrine_de_legumes_e52466": "vegetable terrine",
    "main_tian_provencal_4c7999": "tian provençal",
    "bread_tostadas_06442e": "bean tostada",
    "rice_uzbek_vegetable_plov_2ff045": "vegetable plov",
    "snack_welsh_rarebit_0b7d52": "welsh rarebit",
    "noodle_yaki_udon_legumes_38c0b4": "yaki udon",
})
for _rid, _q in COMMONS_RETRY.items():
    _key = next((k for k in ARTICLES if _rid.startswith(k) or k.startswith(_rid)), _rid)
    ARTICLES[_key] = [f"commons:{_q}"]


def slugify(t: str) -> str:
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower().strip()
    t = re.sub(r"[\s_/\\]+", "-", t)
    t = re.sub(r"[^a-z0-9-]", "", t)
    return re.sub(r"-+", "-", t).strip("-")


def commons_images(session: requests.Session, query: str, n: int = 1) -> list[dict]:
    """Premières photos libres (n au plus) d'une recherche Wikimedia Commons
    choisie à la main (« commons:roasted brussels sprouts »), hors liste noire et
    viande/poisson : pour les plats génériques qui n'ont pas d'article."""
    blocked = F.load_blocklist()
    out = []
    for c in F.search_commons(session, query):
        if " ".join(F.words(c["title"])) in blocked or F.rejected_for(f"{c['title']} {c['categories']}"):
            continue
        c["article"] = f"commons:{query}"
        out.append(c)
        if len(out) >= n:
            break
    return out


def article_image(session: requests.Session, spec: str) -> dict | None:
    """Image principale (libre) de l'article « langue:Titre », redirections suivies."""
    lang, title = spec.split(":", 1)
    data = F.api_get(session, f"https://{lang}.wikipedia.org/w/api.php", {
        "action": "query", "format": "json", "titles": title, "redirects": "1",
        "prop": "pageimages", "piprop": "name",
    })
    for page in ((data or {}).get("query") or {}).get("pages", {}).values():
        if "missing" in page or not page.get("pageimage"):
            continue
        cand = F.commons_file(session, page["pageimage"])
        if cand:
            cand["article"] = f"{lang}:{page.get('title', title)}"
            cand["source"] = f"Wikipédia ({lang}) · Wikimedia Commons"
            return cand
    return None


def spec_images(session: requests.Session, spec: str, n: int) -> list[dict]:
    """Candidats d'une spec : n au plus pour « commons:requête », un pour un article."""
    if spec.startswith("commons:"):
        return commons_images(session, spec.split(":", 1)[1], n)
    c = article_image(session, spec)
    return [c] if c else []


def alt_file(slug: str, k: int) -> str:
    """Fichier du k-ième candidat (1 = slug.jpg)."""
    return f"{slug}.jpg" if k == 1 else f"{slug}~{k}.jpg"


def contact_sheets(out: Path, manifest: dict, per_sheet: int = 10) -> list[Path]:
    """Planches de relecture : une ligne par recette, candidats numérotés."""
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415
    tw, th, label_h, pad = 300, 200, 34, 8
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except OSError:
        font = ImageFont.load_default()
    items = list(manifest.items())
    sheets = []
    for start in range(0, len(items), per_sheet):
        chunk = items[start:start + per_sheet]
        ncol = max(len(m["alts"]) for _, m in chunk)
        sheet = Image.new("RGB", (pad + ncol * (tw + pad), len(chunk) * (th + label_h + pad) + pad), "white")
        draw = ImageDraw.Draw(sheet)
        for row, (rid, m) in enumerate(chunk):
            y = pad + row * (th + label_h + pad)
            draw.text((pad, y), f"#{start + row + 1}  {m['recipe'][:80]}", fill="black", font=font)
            draw.text((pad, y + 17), rid[:60], fill="gray", font=font)
            for k, alt in enumerate(m["alts"], 1):
                x = pad + (k - 1) * (tw + pad)
                try:
                    im = Image.open(out / alt["file"]).convert("RGB")
                    im.thumbnail((tw, th))
                    sheet.paste(im, (x, y + label_h))
                except OSError:
                    continue
                draw.rectangle((x, y + label_h, x + 22, y + label_h + 20), fill="black")
                draw.text((x + 6, y + label_h + 2), str(k), fill="white", font=font)
        path = out / f"_planche_{start // per_sheet + 1:02d}.jpg"
        sheet.save(path, quality=82)
        sheets.append(path)
    return sheets


def stage(out: Path, only: list[str] | None, n_cand: int = 1) -> None:
    from backend.core.data_io import load_recipes  # noqa: PLC0415
    recipes = {r["id"]: r for r in load_recipes()}
    img_dir = F.OUT
    blocked = F.load_blocklist()
    session = requests.Session()
    session.headers["User-Agent"] = UA
    out.mkdir(parents=True, exist_ok=True)
    manifest, cache = {}, {}
    for key, specs in ARTICLES.items():
        found = [i for i in recipes if i == key or i.startswith(key)]
        if len(found) != 1:
            print(f"?? {key} : {len(found)} recettes correspondent")
            continue
        rid = found[0]
        if only and rid not in only and key not in only:
            continue
        r = recipes[rid]
        slug = slugify(r["titles"].get("fr") or r["titles"].get("en"))
        if (img_dir / f"{slug}.jpg").exists():
            print(f"= {rid} : a déjà une photo")
            continue
        cands, why = [], "aucun article illustré sous licence libre"
        for spec in specs:
            if spec not in cache:
                # Sous forte sollicitation, l'API répond 429 même après les
                # reprises d'api_get : un « pas d'image » peut n'être qu'un refus.
                for pause in (0, 8, 20):
                    time.sleep(pause or F.DELAY)
                    cache[spec] = spec_images(session, spec, n_cand)
                    if cache[spec]:
                        break
            for c in cache[spec]:
                if " ".join(F.words(c["title"])) in blocked:
                    why = f"{c['title']} déjà écartée"
                    continue
                reason = F.rejected_for(f"{c['title']} {c['categories']} {c['article']}")
                if reason:
                    why = f"{c['title']} : {reason}"
                    continue
                cands.append(c)
            if cands:
                break
        alts = []
        for c in cands:
            name = alt_file(slug, len(alts) + 1)
            if not (out / name).exists() and not F.download(session, c["download"], out / name):
                continue
            alts.append({"file": name, **{
                k: c[k] for k in ("source", "title", "author", "license", "page", "article")}})
        if not alts:
            print(f"-- {rid} : {why if not cands else 'téléchargement KO'}")
            continue
        manifest[rid] = {"slug": slug, "recipe": r["titles"].get("fr"), "alts": alts}
        print(f"OK {rid} ← {alts[0]['article']} ({len(alts)} candidat(s))")
    (out / "_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    sheets = contact_sheets(out, manifest) if manifest else []
    print(f"\n{len(manifest)} recettes à relire dans {out} ({len(sheets)} planches)")


def publish(src: Path, picks: dict[str, int], rejects: set[str]) -> None:
    """Publie le candidat choisi (--pick id=k, 1 par défaut) ; les recettes
    écartées mettent tous leurs candidats en liste noire."""
    manifest = json.loads((src / "_manifest.json").read_text(encoding="utf-8"))
    credits = F.load_credits()
    blocklist = json.loads(F.BLOCKLIST.read_text(encoding="utf-8")) if F.BLOCKLIST.exists() else []
    n = 0
    # Une même photo peut sortir pour deux recettes : retenue pour l'une, elle
    # n'entre pas en liste noire parce que l'autre est écartée.
    chosen = {(m.get("alts") or [m])[picks.get(rid, 1) - 1]["title"]
              for rid, m in manifest.items() if rid not in rejects}
    for rid, m in manifest.items():
        alts = m.get("alts") or [{"file": f"{m['slug']}.jpg", **m}]   # ancien manifeste
        if rid in rejects:
            blocklist.extend(a["title"] for a in alts
                             if a["title"] not in blocklist and a["title"] not in chosen)
            continue
        alt = alts[picks.get(rid, 1) - 1]
        dest = F.OUT / f"{m['slug']}.jpg"
        if dest.exists():
            continue
        shutil.copyfile(src / alt["file"], dest)
        credits[m["slug"]] = {"recipe": m["recipe"], "source": alt["source"], "title": alt["title"],
                              "author": alt["author"], "license": alt["license"],
                              "page": alt["page"], "query": alt["article"]}
        n += 1
    F.save_credits(credits)
    with open(F.BLOCKLIST, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(sorted(set(blocklist)), ensure_ascii=False, indent=1))
    # save_credits écrit avec les fins de ligne du système : le dépôt est en LF
    for f in (F.CREDITS_JSON, F.CREDITS_MD):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    print(f"{n} photos publiées, {len(rejects & set(manifest))} écartées (liste noire)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", type=Path, help="télécharger pour relecture dans ce dossier")
    ap.add_argument("--only", nargs="*", help="ids de recette à traiter")
    ap.add_argument("--publish", type=Path, help="publier depuis ce dossier relu")
    ap.add_argument("--reject", nargs="*", default=[], help="ids écartés à la relecture")
    ap.add_argument("--candidates", type=int, default=1,
                    help="candidats par recherche Commons (planche de relecture)")
    ap.add_argument("--pick", nargs="*", default=[], help="id=k : k-ième candidat retenu")
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT))
    if args.stage:
        stage(args.stage, args.only, args.candidates)
    elif args.publish:
        picks = {p.split("=")[0]: int(p.split("=")[1]) for p in args.pick}
        publish(args.publish, picks, set(args.reject))
    else:
        ap.error("--stage DIR ou --publish DIR")


if __name__ == "__main__":
    main()
