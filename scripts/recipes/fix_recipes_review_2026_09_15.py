#!/usr/bin/env python3
"""
fix_recipes_review_2026_09_15.py — correctifs systématiques issus de la relecture
des 820 recettes (docs/revue_recettes_2026-09-15/constats_par_recette.md).

Chaque liste est explicite (vérifiée sur le texte des recettes) :
  1. Légumineuses comptées cuites (*_boiled) alors que le texte les trempe /
     cuit depuis le sec : fiche sèche, quantité = poids sec du texte.
  2. Riz compté cru alors que le texte utilise du riz cuit froid : fiche cuite.
  3. Sel absent (sodium < 150 mg) alors que le texte sale ou assaisonne.
  4. Temps : cook_min des préparations sans cuisson → 0 (attente déplacée en
     passif) ; trempage, froid, fermentation, marinade et levée du texte
     ajoutés au temps passif.
  5. kid_friendly retiré (piment ≥ 10 g, pâtes de piment, roquefort, alcool
     flambé) et régime raw retiré des recettes cuites.
  6. Types de plat erronés (pad thaï, currys, tamales classés « soup »…).
  7. Titres mal encodés.

Idempotent. Relancer ensuite fix_recipe_diet_allergens.py,
build_derived_base_registry.py, rebuild_graphs.py et build_index.py.

Usage :
    python scripts/recipes/fix_recipes_review_2026_09_15.py --dry-run
    python scripts/recipes/fix_recipes_review_2026_09_15.py
"""
import argparse, json, logging, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
logging.disable(logging.WARNING)

from backend.engine.config import RECIPES_PATH

# 1. (recette, fiche cuite, fiche sèche, quantité sèche du texte ou None = inchangée)
LEGUMES_SECS = [
    ("dal_basic_k3d2p1", "green_lentil_boiled", "green_lentil_dried", None),
    ("dal_chole_curry_de_pois_chiches_851fca", "chickpea_boiled", "chickpea_raw_dried", None),
    ("dal_dal_makhani_c9ce94", "kidney_bean_boiled", "kidney_bean_dried", None),
    ("dal_falafel_traditionnels_214e07", "chickpea_boiled", "chickpea_raw_dried", None),
    ("dal_lebanese_lentil_soup_eae561", "green_lentil_boiled", "green_lentil_dried", None),
    ("dal_lentilles_corail_au_lait_de_co_19d485", "red_lentil_boiled", "red_lentil_dried", None),
    ("dal_makhani_vegan_259219", "green_lentil_boiled", "green_lentil_dried", 50),
    ("dal_makhani_vegan_259219", "kidney_bean_boiled", "kidney_bean_dried", 150),
    ("dal_mercimek_koftesi_34f72d", "red_lentil_boiled", "red_lentil_dried", None),
    ("dal_revithia_922f79", "chickpea_boiled", "chickpea_raw_dried", None),
    ("dal_salade_de_lentilles_ethiopienn_5a9dd6", "green_lentil_boiled", "green_lentil_dried", None),
    ("dal_salade_de_pois_chiches_2e32de", "chickpea_boiled", "chickpea_raw_dried", None),
    ("dal_sambar_indien_fcf6d8", "red_lentil_boiled", "red_lentil_dried", None),
    ("dal_shorbat_adas_d4f98a", "red_lentil_boiled", "red_lentil_dried", None),
    ("dal_sri_lankan_dhal_curry_fae1be", "red_lentil_boiled", "red_lentil_dried", None),
    ("dip_hummus_classic_v6_u4k9p2", "chickpea_boiled", "chickpea_raw_dried", 200),
    ("entry_rillettes_lentilles_corai_40d7dc", "red_lentil_boiled", "red_lentil_dried", None),
    ("main_fasolada_grecque_d70275", "white_bean_boiled", "white_bean_raw", None),
    ("main_greek_fasolada_612a6f", "white_bean_boiled", "white_bean_raw", None),
    ("main_lobio_5cdec6", "kidney_bean_boiled", "kidney_bean_dried", None),
    ("rice_mujadara_classic_ee2456", "green_lentil_boiled", "green_lentil_dried", None),
    ("salad_de_haricots_aux_yeux_noir_f442f9", "black_eyed_peas_cowpeas_boiled", "black_eyed_peas_cowpeas_dried", None),
    ("salad_lentil_classic_v3_r7p2k8", "red_lentil_boiled", "red_lentil_dried", None),
    ("soup_de_haricots_grecs_a96296", "white_bean_boiled", "white_bean_raw", None),
    # le texte cuit 150 g de « lentilles corail » 25–30 min
    ("soup_harira_classic_v3_p9x4k2", "green_lentil_boiled", "red_lentil_dried", None),
    ("soup_lentilles_turque_vegan_c2febf", "red_lentil_boiled", "red_lentil_dried", None),
    ("soup_turkish_mercimek_soup_veg_f30ebc", "red_lentil_boiled", "red_lentil_dried", None),
    ("stew_cassoulet_938fd4", "white_bean_boiled", "white_bean_raw", None),
    ("stew_croatian_bean_stew_4dfb05", "white_bean_boiled", "white_bean_raw", None),
    ("stew_lentil_basic_v2_x7k2m9", "green_lentil_boiled", "green_lentil_dried", None),
    ("stew_lentil_classic_0adae5", "green_lentil_boiled", "green_lentil_dried", None),
]

# 2. Riz cuit froid (le texte ne cuit pas le riz)
RIZ_LONG_CUIT, RIZ_ROND_CUIT = "white_rice_cooked_long_grain_seed", "white_rice_cooked_short_grain_seed"
RIZ_CUIT = {
    "main_fried_rice_a6e811": RIZ_LONG_CUIT,
    "rice_fried_classic_v2_k4m8t1": RIZ_LONG_CUIT,
    "rice_fried_rice_chinois_vegan_c2b92d": RIZ_LONG_CUIT,
    "rice_kimchi_bokkeumbap_2cbfe6": RIZ_ROND_CUIT,
    "rice_kimchi_fried_rice_1f3e90": RIZ_LONG_CUIT,
    "rice_nasi_goreng_edfce4": RIZ_LONG_CUIT,
    "rice_nasi_goreng_vegan_bcc9cb": RIZ_LONG_CUIT,
    "rice_pad_krapow_63acfb": RIZ_LONG_CUIT,
    "rice_riz_frit_2763d3": RIZ_LONG_CUIT,
    "rice_vegetable_fried_rice_cd489b": RIZ_LONG_CUIT,
    "side_riz_frit_vegan_d17d25": RIZ_LONG_CUIT,
    "rice_riz_citronne_indien_05c717": RIZ_LONG_CUIT,
}
RIZ_CRUS = ("white_rice_raw_seed_unenriched", "white_rice_short_grain_seed_dried")

# 3. Sel
SALT_ID = "table_salt_unenriched"
SALT_DISH_TYPES = {"main", "soup", "starter", "side"}
SALT_TEXT = re.compile(r"\bsel\b|\bsale[rz]?\b|\bsalée?\b|assaisonn", re.I)
SODIUM_BAS_MG = 150

# 4. Temps
SANS_CUISSON = [  # cook_min → 0
    "base_almond_milk_226291", "base_green_curry_paste_250117", "base_hemp_milk_9248fe",
    "base_mayonnaise_0d3e4e", "base_pesto_905db7", "base_vegan_mayonnaise_b68322",
    "brkf_granola_bowl_yaourt_fruit_980183", "brkf_smoothie_vert_epinards_ba_eb4142",
    "dessert_chia_pudding_coco_mangue_d61cff", "entry_carottes_rapees_e66bae",
    "entry_celeri_remoulade_d5d1b9", "entry_gaspacho_de_melon_menthe_ee9907",
    "entry_mousse_avocat_wasabi_773105", "entry_tapenade_d_olives_noires_ed6d5d",
    "entry_tzatziki_grec_2b21fb", "entry_verrines_avocat_mangue_c5f8c6", "dip_guacamole_970186",
    "main_bulgarian_shopska_salad_d473eb", "main_tofu_froid_japonais_506c62",
    "main_pico_de_gallo_31e006", "main_papaya_salad_918f58", "red_curry_paste_3ee8f5",
    "salad_andine_au_fromage_vegan_566f05", "salad_asiatique_sesame_948f03",
    "salad_bulgarian_shopska_salad_v_adc716", "salad_mixed_structured_v2_p9x4m2",
    "salad_shopska_04dd73", "sauce_vinaigrette_174a79", "samosa_dough_c03717",
    "salad_dattieke_7824bf",
]
CUISSON_EN_PASSIF = ["base_salted_ricotta_1ecd1c", "main_kimchi_1dc648"]  # attente comptée en cuisson

_DUREE = r"(\d+(?:[.,]\d+)?)\s*(heures?|h\b|minutes?|min\b|jours?)"
ATTENTES = {
    "trempage": re.compile(r"(?:tremp\w*|réhydrat\w*)(?![^.]{0,30}\b(?:tortilla|pâte|morceau|chaque|feuille))"
                           r"[^.]{0,70}?(?:" + _DUREE + r"|toute la (nuit)|(nuit))", re.I),
    "froid": re.compile(r"(?:réfrigér\w*|au réfrigérateur|au frais)(?![^.]{0,20}jours)[^.]{0,60}?" + _DUREE, re.I),
    "fermentation": re.compile(r"ferment\w*[^.]{0,60}?" + _DUREE, re.I),
    "marinade": re.compile(r"marin\w*[^.]{0,50}?" + _DUREE, re.I),
    "levée": re.compile(r"(?:lever|levée|pousser)[^.]{0,50}?" + _DUREE, re.I),
}
CONSERVATION = re.compile(r"conserv|se garde|jusqu'à \d+ jours", re.I)

# 5. Régimes
PAS_KID_FRIENDLY = [
    "base_laksa_paste_bc7fd5", "base_mole_d0034f", "base_pate_piment_b6904a", "chili_paste_95cb92",
    "dal_pakora_b418ab", "dip_guacamole_970186", "egg_makdous_cf5efa",
    "main_epinards_assaisonnes_core_b596b9", "main_haricots_frits_mexicains_a78841",
    "main_haricots_rouges_a_la_toma_c44560", "main_kimchi_1dc648", "main_nepali_tomato_achar_9575d1",
    "main_pico_de_gallo_31e006", "main_pozole_82d096", "pasta_puttanesca_v1x9q2",
    "rice_riz_saute_au_kimchi_vegan_af038b", "rice_tteokbokki_0861f2",
    "salad_de_papaye_vietnamienne_add574", "salad_de_pousses_de_soja_coreen_d07502",
    "sauce_pommes_de_terre_sauce_hua_3304de", "soup_thai_basil_tofu_c7e4ad",
    "stew_ragout_de_plantain_2140eb", "yellow_curry_paste_077f54", "base_sauce_peanut_d92c5c",
    "wok_pad_krapow_vegetarien_565aa9", "main_patatas_bravas_98ec00", "entry_salmorejo_vegan_d0b7f7",
    "entry_skordalia_18cd77",
    "main_tarte_roquefort_et_noix_b24bec", "salad_salade_mache_aux_noix_081567",
    "dessert_tiramisu_classique_ea8ddb", "soup_bisque_de_champignons_63fa25",
]
PAS_RAW = ["rice_salad_k3d2p1", "salad_andine_au_fromage_vegan_566f05",
           "snack_tostadas_vegan_f7257b", "entry_salmorejo_vegan_d0b7f7"]

# 6. Types de plat
DISH_TYPE = {
    "soup_pad_thai_cfe090": "main", "soup_tamales_7dd98a": "main",
    "soup_thai_basil_tofu_c7e4ad": "main", "soup_thai_green_curry_56dfda": "main",
    "soup_thai_red_curry_f6bb3c": "main", "soup_courge_mijotee_japonaise_3852ae": "side",
    "main_kimchi_1dc648": "side", "main_nepali_tomato_achar_9575d1": "condiment",
    "main_ajvar_puree_de_poivrons_5d2e79": "starter", "main_caviar_d_aubergine_0e824d": "starter",
}

# 6 bis. Portions devenues irréalistes avec le poids sec (texte : ~23 falafels de 35 g)
PORTIONS = {"dal_falafel_traditionnels_214e07": 5}

# 7. Titres
TITRES = {
    "rice_serbian_uve_4a83e2": {"original": "Serbian Đuveč", "fr": "Đuveč serbe", "en": "Serbian Đuveč"},
    "main_romanian_zacusc_a929ee": {"original": "Romanian Zacuscă", "fr": "Zacuscă roumaine",
                                    "en": "Romanian Zacuscă"},
}


def _minutes(m) -> float:
    g = [x for x in m.groups() if x]
    if len(g) == 1:
        return 480.0  # « toute la nuit »
    v, u = float(g[0].replace(",", ".")), g[1].lower()
    return v * (60 if u.startswith("h") else 1440 if u.startswith("jour") else 1)


def attente_du_texte(recipe: dict) -> int:
    """Somme des attentes du texte (max par catégorie), hors conservation."""
    phrases = re.split(r"(?<=[.!])\s+", " ".join(recipe.get("instructions") or []))
    total = 0.0
    for pat in ATTENTES.values():
        vals = [_minutes(m) for p in phrases if not CONSERVATION.search(p) for m in pat.finditer(p)]
        total += max(vals, default=0)
    return int(round(total))


def salt_grams(recipe: dict, servings: int) -> float:
    """Quantité du texte (« 5 g de sel », « une pincée »), sinon 1,25 g par portion."""
    txt = " ".join(recipe.get("instructions") or [])
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*g(?:rammes)? de sel", txt, re.I)
    if m:
        return float(m.group(1).replace(",", "."))
    if re.search(r"pincée de sel", txt, re.I):
        return 1
    return max(2, round(1.25 * servings))


def _set_total(t: dict):
    t["total_min"] = sum(int(t.get(k) or 0) for k in ("prep_active_min", "prep_passive_min", "cook_min"))


def _drop_flag(r: dict, flag: str) -> bool:
    changed = False
    if (r.get("diet_flags") or {}).get(flag):
        r["diet_flags"][flag] = False
        changed = True
    diet = (r.get("tags") or {}).get("diet")
    if isinstance(diet, list) and flag in diet:
        diet.remove(flag)
        changed = True
    return changed


def apply(recipes: list[dict]) -> list[str]:
    from backend.engine import nutrition_engine as ne
    by_id = {r["id"]: r for r in recipes}
    log = []

    # recettes supprimées depuis (doublons, remove_duplicate_recipes_2026_09_15.py) : ignorées
    ABSENTE = {"composition": [], "timing": {}}

    def need(rid):
        return by_id.get(rid, ABSENTE)

    for rid, cuit, sec, qty in LEGUMES_SECS:
        for c in need(rid)["composition"]:
            if c["ingredient"] == cuit and (c.get("meta") or {}).get("role") != "serving_suggestion":
                c["ingredient"] = sec
                c.setdefault("meta", {})["state"] = "dried"
                if qty is not None:
                    c["quantity"] = qty
                log.append(f"légumineuse sèche  {rid}: {cuit} → {sec} {c['quantity']} g")

    for rid, cuit in RIZ_CUIT.items():
        for c in need(rid)["composition"]:
            if c["ingredient"] in RIZ_CRUS:
                log.append(f"riz cuit           {rid}: {c['ingredient']} → {cuit}")
                c["ingredient"] = cuit
                c.setdefault("meta", {})["state"] = "cooked"

    for r in recipes:
        if r.get("dish_type") not in SALT_DISH_TYPES:
            continue
        comp = r.get("composition") or []
        if any(c.get("ingredient") == SALT_ID for c in comp):
            continue
        if not SALT_TEXT.search(" ".join(r.get("instructions") or [])):
            continue
        if (ne.compute_nutrition(r).get("sodium") or 0) >= SODIUM_BAS_MG:
            continue
        g = salt_grams(r, ne.resolve_servings(r))
        comp.append({"ingredient": SALT_ID, "quantity": g, "unit": "g",
                     "meta": {"role": "seasoning", "form": "", "state": "raw", "preparation": ""}})
        log.append(f"sel ajouté         {r['id']}: {g} g")

    for rid in SANS_CUISSON:
        t = need(rid)["timing"]
        if t.get("cook_min"):
            log.append(f"cuisson → 0        {rid}: {t['cook_min']} min")
            t["cook_min"] = 0
            _set_total(t)
    for rid in CUISSON_EN_PASSIF:
        t = need(rid)["timing"]
        if t.get("cook_min"):
            log.append(f"cuisson → passif   {rid}: {t['cook_min']} min")
            t["prep_passive_min"] = int(t.get("prep_passive_min") or 0) + int(t["cook_min"])
            t["cook_min"] = 0
            _set_total(t)
    for r in recipes:
        t = r.get("timing") or {}
        besoin, actuel = attente_du_texte(r), int(t.get("prep_passive_min") or 0)
        if besoin > actuel * 1.2 + 5:
            t["prep_passive_min"] = besoin
            _set_total(t)
            log.append(f"temps passif       {r['id']}: {actuel} → {besoin} min")

    for rid in PAS_KID_FRIENDLY:
        if _drop_flag(need(rid), "kid_friendly"):
            log.append(f"kid_friendly retiré {rid}")
    for rid in PAS_RAW:
        if _drop_flag(need(rid), "raw"):
            log.append(f"raw retiré         {rid}")

    for rid, dt in DISH_TYPE.items():
        r = need(rid)
        if r is not ABSENTE and r.get("dish_type") != dt:
            log.append(f"type de plat       {rid}: {r.get('dish_type')} → {dt}")
            r["dish_type"] = dt

    for rid, n in PORTIONS.items():
        r = need(rid)
        if r is not ABSENTE and r.get("servings") != n:
            log.append(f"portions           {rid}: {r.get('servings')} → {n}")
            r["servings"] = n
            if "servings_default" in r:
                r["servings_default"] = n

    for rid, titles in TITRES.items():
        r = by_id.get(rid)
        if not r:
            continue
        for lang, title in titles.items():
            if r.setdefault("titles", {}).get(lang) != title:
                log.append(f"titre              {rid} [{lang}]: {r['titles'].get(lang)} → {title}")
                r["titles"][lang] = title
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    raw = json.loads(Path(RECIPES_PATH).read_text(encoding="utf-8"))
    log = apply(raw["recipes"])
    for line in log:
        print(line)
    print(f"\n{len(log)} modifications")
    if args.dry_run or not log:
        return
    tmp = Path(RECIPES_PATH).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(RECIPES_PATH)
    print(f"écrit : {RECIPES_PATH}")


if __name__ == "__main__":
    main()
