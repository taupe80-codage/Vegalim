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
    python scripts/fetch_images_by_article.py --publish DIR --reject id1 id2 …
        copie les photos retenues dans frontend/public/images/recipes, crédite,
        et met les rejetées en liste noire
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
}


def slugify(t: str) -> str:
    t = unicodedata.normalize("NFD", t or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower().strip()
    t = re.sub(r"[\s_/\\]+", "-", t)
    t = re.sub(r"[^a-z0-9-]", "", t)
    return re.sub(r"-+", "-", t).strip("-")


def commons_image(session: requests.Session, query: str) -> dict | None:
    """Première photo libre d'une recherche Wikimedia Commons choisie à la main
    (« commons:roasted brussels sprouts »), hors liste noire et viande/poisson : pour
    les plats génériques qui n'ont pas d'article."""
    blocked = F.load_blocklist()
    for c in F.search_commons(session, query):
        if " ".join(F.words(c["title"])) in blocked or F.rejected_for(f"{c['title']} {c['categories']}"):
            continue
        c["article"] = f"commons:{query}"
        return c
    return None


def article_image(session: requests.Session, spec: str) -> dict | None:
    """Image principale (libre) de l'article « langue:Titre », redirections suivies ;
    « commons:requête » : recherche Commons (commons_image)."""
    if spec.startswith("commons:"):
        return commons_image(session, spec.split(":", 1)[1])
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


def stage(out: Path, only: list[str] | None) -> None:
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
        cand, why = None, "aucun article illustré sous licence libre"
        for spec in specs:
            if spec not in cache:
                # Sous forte sollicitation, l'API répond 429 même après les
                # reprises d'api_get : un « pas d'image » peut n'être qu'un refus.
                for pause in (0, 8, 20):
                    time.sleep(pause or F.DELAY)
                    cache[spec] = article_image(session, spec)
                    if cache[spec]:
                        break
            c = cache[spec]
            if not c:
                continue
            if " ".join(F.words(c["title"])) in blocked:
                why = f"{c['title']} déjà écartée"
                continue
            reason = F.rejected_for(f"{c['title']} {c['categories']} {c['article']}")
            if reason:
                why = f"{c['title']} : {reason}"
                continue
            cand = c
            break
        if not cand:
            print(f"-- {rid} : {why}")
            continue
        dest = out / f"{slug}.jpg"
        if not dest.exists() and not F.download(session, cand["download"], dest):
            print(f"!! {rid} : téléchargement KO")
            continue
        manifest[rid] = {"slug": slug, "recipe": r["titles"].get("fr"), **{
            k: cand[k] for k in ("source", "title", "author", "license", "page", "article")}}
        print(f"OK {rid} ← {cand['article']} ({cand['license']})")
    (out / "_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1),
                                        encoding="utf-8")
    print(f"\n{len(manifest)} photos à relire dans {out}")


def publish(src: Path, rejects: set[str]) -> None:
    manifest = json.loads((src / "_manifest.json").read_text(encoding="utf-8"))
    credits = F.load_credits()
    blocklist = json.loads(F.BLOCKLIST.read_text(encoding="utf-8")) if F.BLOCKLIST.exists() else []
    n = 0
    for rid, m in manifest.items():
        if rid in rejects:
            if m["title"] not in blocklist:
                blocklist.append(m["title"])
            continue
        dest = F.OUT / f"{m['slug']}.jpg"
        if dest.exists():
            continue
        shutil.copyfile(src / f"{m['slug']}.jpg", dest)
        credits[m["slug"]] = {"recipe": m["recipe"], "source": m["source"], "title": m["title"],
                              "author": m["author"], "license": m["license"],
                              "page": m["page"], "query": m["article"]}
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
    args = ap.parse_args()
    sys.path.insert(0, str(ROOT))
    if args.stage:
        stage(args.stage, args.only)
    elif args.publish:
        publish(args.publish, set(args.reject))
    else:
        ap.error("--stage DIR ou --publish DIR")


if __name__ == "__main__":
    main()
