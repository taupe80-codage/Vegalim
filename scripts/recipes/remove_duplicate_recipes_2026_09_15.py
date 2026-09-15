#!/usr/bin/env python3
"""
remove_duplicate_recipes_2026_09_15.py — supprime les doublons relevés lors de la
relecture des 820 recettes (docs/revue_recettes_2026-09-15).

Décision du 2026-09-15 : suppression sans alias (pas d'utilisateurs réels).
Pour chaque groupe, la version gardée est la plus cohérente après relecture
(quantités, texte, ingrédients) ; les paires vegan / non vegan d'un même plat
sont conservées.

Retire aussi les recettes supprimées de backend/data/config/vegan_variants_index.json.
Idempotent. Relancer ensuite rebuild_graphs.py, build_index.py et
backend/data/recipes/_scripts/extract_recipe_list.py.

Usage :
    python scripts/recipes/remove_duplicate_recipes_2026_09_15.py --dry-run
    python scripts/recipes/remove_duplicate_recipes_2026_09_15.py
"""
import argparse, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.engine.config import RECIPES_PATH, DATA_ROOT

VARIANTS_PATH = DATA_ROOT / "config" / "vegan_variants_index.json"

# recette gardée → doublons supprimés
GROUPES = {
    "couscous_traditionnel_132078": ["couscous_moroccan_vegetable_cousco_f80d61", "couscous_vegetable_classic_k1d1p7",
                                     "couscous_vegetable_quick_k5d3p1", "couscous_couscous_traditionnel_veg_46ff36"],
    "curry_chickpea_spinach_k6518f8": ["dal_curry_pois_chiches_epinards_a7ee14"],
    "curry_green_curry_tofu_2a30dd": ["curry_curry_vert_thai_6a3792", "curry_green_thai_classic_v3_m9x2k7",
                                      "soup_thai_green_curry_56dfda"],
    "dal_soupe_de_lentilles_621239": ["dal_ragout_de_lentilles_epice_7ee9be"],
    "protein_mapo_tofu_4b4458": ["protein_chinese_mapo_tofu_7edbe0", "protein_mapo_tofu_au_champignon_ba9276"],
    "rice_paella_veg_c7m3x1": ["rice_paella_e8b8b3", "rice_paella_veg_classic_v4_s9k2x1", "rice_paella_de_verduras_8e54fd"],
    "rice_poivrons_farcis_au_riz_be3ddc": ["rice_poivrons_farcis_447217", "rice_poivrons_farcis_vegetarie_f6c4f5"],
    "soup_de_pois_casses_58fc34": ["soup_de_pois_scandinave_ec245b", "soup_pois_casses_cf435c"],
    "soup_vegetable_laksa_ab0112": ["soup_laksa_thai_7b1720", "soup_soupe_laksa_coco_729105", "soup_laksa_malaisien_dd7512"],
    "soup_minestrone_9116a2": ["soup_minestrone_x7p2k1", "soup_minestrone_vegan_10bf61"],
    "bread_panzanella_italienne_307da1": ["bread_panzanella_f753c6"],
    "main_ribollita_toscane_4cae34": ["bread_ribollita_d191b3", "main_italian_ribollita_a99546"],
    "curry_palak_paneer_b4ca11": ["curry_palak_paneer_classic_v4_m8x3p1"],
    "curry_paneer_butter_masala_9e638c": ["curry_paneer_butter_masala_classic_v4_z7x3p2"],
    "pasta_persian_ash_reshteh_8cb79c": ["dal_ash_reshteh_30aac5"],
    "dal_coconut_classic_k1d1p5": ["dal_coconut_dal_ea7cdd"],
    "dal_lentil_shepherd_s_pie_477c76": ["dal_lentil_shepherd_pie_9a295e"],
    "dessert_cannele_bordelais_c55eca": ["dessert_caneles_bordelais_ea24bb"],
    "dessert_clafoutis_cerises_0731cf": ["dessert_clafoutis_aux_cerises_f81391"],
    "egg_feijo_tropeiro_bb31e4": ["egg_brazilian_feijo_tropeiro_af46ce"],
    "egg_quiche_lorraine_vegetarienne_77343c": ["tarte_quiche_lorraine_7033e4"],
    "egg_tortilla_espa_ola_51a108": ["egg_tortilla_espagnole_6cd136"],
    "main_arepas_fromage_e3a54c": ["main_arepas_a70a2e"],
    "main_aubergines_imam_bayildi_e1443e": ["main_aubergines_farcies_turque_9caa16", "main_turkish_imam_bayildi_0668d1"],
    "main_chili_sin_carne_125ff2": ["main_chili_sin_carne_epice_205657"],
    "main_haricots_frits_mexicains_a78841": ["main_haricots_frits_mexicains_4ba94a"],
    "main_pupusas_vegan_4595d8": ["main_pupusas_aux_haricots_vega_0e0c06"],
    "stew_ratatouille_k8d2p4": ["main_ratatouille_quick_6eb9af"],
    "salad_tabbouleh_f7x2p9": ["main_taboule_760c36"],
    "noodle_pad_see_ew_classic_v3_n8x4p2": ["noodle_pad_see_ew_41b095"],
    "pasta_carbonara_veg_k3d2p1": ["pasta_pates_carbonara_7e4f1a"],
    "pasta_pasta_alla_norma_a_la_ric_d282a6": ["pasta_pasta_alla_norma_vegan_6e1a92"],
    "pasta_pasta_alla_norma_5cc26e": ["pasta_pasta_alla_norma_a_la_ricotta__1538f4"],
    "pasta_pasta_e_fagioli_68905b": ["pasta_pates_et_haricots_f46830"],
    "pasta_pates_primavera_74711d": ["pasta_primavera_quick_3f5fc5"],
    "protein_pad_thai_vegan_33c0f3": ["soup_pad_thai_cfe090"],
    "main_fried_rice_a6e811": ["rice_fried_classic_v2_k4m8t1", "rice_vegetable_fried_rice_cd489b",
                               "rice_riz_frit_2763d3", "rice_fried_rice_chinois_9d1d40"],
    "rice_fried_rice_chinois_vegan_c2b92d": ["side_riz_frit_vegan_d17d25"],
    "rice_onigiri_umeboshi_7a5ef3": ["rice_onigiri_au_saumon_d_umeboshi_cba6bf"],
    "salad_fattoush_classic_x82m5c": ["salad_fattoush_035977", "salad_fattoush_au_radis_8dab85"],
    "salad_greek_classic_v2_t4m8q1": ["salad_grecque_classique_f83c30", "salad_grecque_simplifiee_34b852"],
    "salad_grecque_classique_vegan_a9f9a4": ["salad_grecque_simplifiee_vegan_ec9ed5"],
    "salad_mixed_structured_v2_p9x4m2": ["salad_mixed_classic_v2a1b2"],
    "soup_a_l_oignon_gratinee_vegan_826f59": ["soup_a_l_oignon_au_thym_vegan_bf7d2f"],
    "soup_soup_k3d2p1": ["soup_soupe_a_l_oignon_au_thym_4c6c6f", "soup_soupe_a_l_oignon_gratinee_f0fd17"],
    "soup_aigrepiquante_5245bb": ["soup_aigrepiquante_4766fe"],
    "soup_persian_ash_reshteh_vegan_968f7d": ["soup_ash_reshteh_vegan_393184"],
    "soup_miso_k2d1p1": ["soup_miso_classic_v4_r7m2k9"],
    "soup_udon_miso_ef1ceb": ["soup_udon_da9371"],
    "wok_pad_krapow_vegetarien_565aa9": ["wok_pad_krapow_tofu_v3_k9x2m7", "soup_thai_basil_tofu_c7e4ad"],
    "protein_gadogado_indonesien_200c65": ["protein_gado_gado_2412da", "protein_gadogado_c0f543"],
    "egg_shakshuka_eb137b": ["egg_shakshouka_douce_12b34f", "egg_shakshouka_epicee_759f26", "egg_shakshuka_v8f3k2"],
    "egg_spanakopita_f5da1b": ["egg_spanakopita_a_la_muscade_9f26d0"],
    "side_potatoes_k3d2p1": ["side_potato_classic_v3_z8m2k7"],
    "wok_pak_choi_saute_62b974": ["wok_bok_choy_saute_a_lail_309f8e"],
    "rice_dolma_au_persil_6aeb1e": ["rice_dolma_au_cumin_b40a25"],
    "main_greek_fasolada_612a6f": ["main_fasolada_grecque_d70275", "soup_de_haricots_grecs_a96296"],
    "main_horta_b898d5": ["main_horta_vrasta_a5fca2"],
    "rice_riz_et_pois_caribeen_72144c": ["rice_rice_and_beans_caribeen_e3de29"],
    "soup_turkish_mercimek_soup_veg_f30ebc": ["soup_lentilles_turque_vegan_c2febf"],
    "stew_lentil_classic_v5_h9k3p2": ["stew_lentil_basic_v2_x7k2m9", "stew_lentil_classic_0adae5", "dal_basic_k3d2p1"],
}
SUPPRIMEES = {rid for doublons in GROUPES.values() for rid in doublons}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    raw = json.loads(Path(RECIPES_PATH).read_text(encoding="utf-8"))
    ids = {r["id"] for r in raw["recipes"]}
    manquantes = [k for k in GROUPES if k not in ids]
    if manquantes:
        raise SystemExit(f"recettes gardées introuvables : {manquantes}")
    avant = len(raw["recipes"])
    raw["recipes"] = [r for r in raw["recipes"] if r["id"] not in SUPPRIMEES]
    retirees = avant - len(raw["recipes"])

    idx = json.loads(VARIANTS_PATH.read_text(encoding="utf-8"))
    o2v, v2o = idx.get("original_to_vegan", {}), idx.get("vegan_to_original", {})
    idx["original_to_vegan"] = {k: v for k, v in o2v.items() if k not in SUPPRIMEES}
    idx["vegan_to_original"] = {k: v for k, v in v2o.items() if v.get("original_id") not in SUPPRIMEES}
    idx["total"] = len(idx["original_to_vegan"])
    variantes = len(o2v) - len(idx["original_to_vegan"])

    print(f"{retirees} recettes supprimées ({len(raw['recipes'])} restantes), "
          f"{variantes} entrées retirées de l'index des variantes vegan")
    if args.dry_run or (not retirees and not variantes):
        return
    for path, data in ((Path(RECIPES_PATH), raw), (VARIANTS_PATH, idx)):
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        print(f"écrit : {path}")


if __name__ == "__main__":
    main()
