"""Ajoute des fiches MANUAL absentes des sources officielles (idempotent).

- tteok : gâteau de riz coréen (garaetteok), cuit à la vapeur, prêt à l'emploi
- green_papaya : papaye verte (non mûre), crue — la fiche `papaya_raw` est celle du fruit mûr

Valeurs pour 100 g, d'après les tables coréennes (RDA) et USDA pour la papaye verte ;
arrondies, micronutriments non renseignés laissés à 0 comme pour les autres fiches MANUAL.

Fichiers touchés : nutrition_manual_supplements.json (source de vérité), nutrition_v2.json
(injection directe, identique à celle de build_n2_direct.py), ingredients_dictionary.json,
nutrition_aliases_v6.json, ingredient_price_map.json, prices_catalog.json, ingredient_map_v2.json,
ingredient_availability_graph_v1.json.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "backend" / "data"

ZERO = ["alcohol_g", "fa_mufa_g", "fa_pufa_g", "fa_18_3_ala_g", "fa_20_5_epa_g", "fa_22_6_dha_g",
        "fa_18_2_linoleic_g", "cholesterol_mg", "zinc_mg", "copper_mg", "manganese_mg", "selenium_ug",
        "retinol_ug", "vitamin_d_ug", "alpha_tocopherol_mg", "vitamin_k1_ug", "vitamin_b2_mg",
        "vitamin_b3_mg", "vitamin_b5_mg", "vitamin_b6_mg", "vitamin_b12_ug", "omega3_g"]

NEW = {
    "tteok": {
        "ig_id": "ing_manual_026", "var_id": "var_manual_026",
        "name_fr": "tteok (gâteau de riz coréen)", "name_en": "tteok (Korean rice cake)",
        "cat": ("cereals_and_grains", "rice"), "properties": ["starch"], "protein_bio": 0.67,
        "diet": {"high_protein": False, "high_fiber": False, "high_fat": False},
        "nutrients": {"calories_kcal": 230, "protein_g": 4.0, "carbs_g": 51.0, "fat_g": 0.5, "fiber_g": 0.5,
                      "sugar_g": 0.3, "water_g": 44.0, "fa_saturated_g": 0.1, "salt_g": 0.38, "sodium_mg": 150,
                      "calcium_mg": 4, "iron_mg": 0.3, "magnesium_mg": 10, "phosphorus_mg": 45,
                      "potassium_mg": 40, "beta_carotene_ug": 0, "vitamin_c_mg": 0, "vitamin_b1_mg": 0.03,
                      "folate_ug": 3},
        "avail": {"available_in_france": "partial", "category": "cereals and grains", "name_fr": "tteok (gâteau de riz coréen)"},
        "price": {"name_fr": "Tteok (gâteaux de riz coréens)", "pantry": True,
                  "packages": [{"qty": 500, "unit": "g", "price": 3.5, "label": "sachet 500g (épicerie asiatique)"}]},
    },
    "green_papaya": {
        "ig_id": "ing_manual_027", "var_id": "var_manual_027",
        "name_fr": "papaye verte (non mûre), crue", "name_en": "green papaya, raw",
        "cat": ("fruits", "papayas"), "properties": ["fresh", "fiber"], "protein_bio": 0.6,
        "diet": {"high_protein": False, "high_fiber": False, "high_fat": False},
        "nutrients": {"calories_kcal": 27, "protein_g": 0.6, "carbs_g": 6.0, "fat_g": 0.1, "fiber_g": 1.8,
                      "sugar_g": 2.0, "water_g": 92.0, "fa_saturated_g": 0.0, "salt_g": 0.02, "sodium_mg": 8,
                      "calcium_mg": 24, "iron_mg": 0.3, "magnesium_mg": 20, "phosphorus_mg": 10,
                      "potassium_mg": 180, "beta_carotene_ug": 100, "vitamin_c_mg": 40, "vitamin_b1_mg": 0.02,
                      "folate_ug": 30},
        "avail": {"available_in_france": "partial", "category": "fruit", "name_fr": "papaye verte"},
        "price": None,  # `green_papaya` existe déjà au catalogue
    },
}


def load(p):
    return json.loads(p.read_text(encoding="utf-8"))


def save(p, d):
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    changed = []
    supp_p = DATA / "nutrition/reference/nutrition_manual_supplements.json"
    n2_p = DATA / "nutrition/processed/nutrition_v2.json"
    dict_p = DATA / "ingredients/ingredients_dictionary.json"
    alias_p = DATA / "nutrition/reference/nutrition_aliases_v6.json"
    pmap_p = DATA / "config/ingredient_price_map.json"
    cat_p = DATA / "config/prices_catalog.json"
    supp, n2, dic, alias, pmap, cat = map(load, (supp_p, n2_p, dict_p, alias_p, pmap_p, cat_p))

    for key, e in NEW.items():
        nutrients = {**{k: 0 for k in ZERO}, **e["nutrients"]}
        if key not in supp["supplements"]:
            supp["supplements"][key] = {"ig_id": e["ig_id"], "var_id": e["var_id"], "name_fr": e["name_fr"],
                                        "name_en": e["name_en"], "nutrients": nutrients}
            supp["_meta"]["count"] = len(supp["supplements"])
            changed.append(f"supplément {key}")
        c1, c2 = e["cat"]
        sub = dic["categories"][c1]["subcategories"][c2]
        if key not in n2["ingredients"]:
            n2["ingredients"][key] = {
                "taxonomy": {"cat1": c1, "cat1_fr": dic["categories"][c1].get("name_fr", c1), "cat2": c2,
                             "cat2_fr": sub.get("name_fr", c2), "cat2_type": "ombrelle", "v32_id": e["ig_id"],
                             "name_fr": e["name_fr"], "name_en": e["name_en"]},
                "ingredient_type": "ombrelle", "variant_dimensions": [], "variant_dimensions_fr": [],
                "indus_conditionne": False, "indus_conditionne_only": False, "conditioning_types": [],
                "aliases_fr": [], "_v32_id": e["ig_id"],
                "variants": {"default": {"_source": "MANUAL", "_source_id": None, "_v32_ing_id": e["ig_id"],
                                         "_v32_var_id": e["var_id"], "axes": {}, "axes_fr": {},
                                         "name_fr": e["name_fr"], "name_en": e["name_en"],
                                         "indus_conditionne": False, "conditioning_types": [], **nutrients}},
            }
            n2["total_bases"] = len(n2["ingredients"])
            n2["total_variants"] = sum(len(b.get("variants", {})) for b in n2["ingredients"].values())
            changed.append(f"nutrition_v2 {key}")
        groups = sub.setdefault("ingredient_groups", {})
        if key not in groups:
            groups[key] = {"v32_ing_id": e["ig_id"], "v32_var_id": e["var_id"], "source": "MANUAL", "source_id": None,
                           "source_label": e["name_fr"], "canonical_name_fr": e["name_fr"],
                           "canonical_name_en": e["name_en"], "axes": {}, "axes_fr": {}, "aliases": [],
                           "diet_profile": {"vegan": True, "vegetarian": True, "gluten_free": True,
                                            "lactose_free": True, "dairy_free": True, "nut_free": True,
                                            "soy_free": True, "egg_free": True, **e["diet"]},
                           "allergens_eu": [], "nova_group": 1 if key == "green_papaya" else 3,
                           "bioavailability_protein": e["protein_bio"], "culinary": {"properties": e["properties"]}}
            changed.append(f"dictionnaire {key}")
        if alias["aliases"].get(key) != key:
            alias["aliases"][key] = key
            alias["total"] = len(alias["aliases"])
            changed.append(f"alias {key}")
        if key not in pmap:
            pmap[key] = key
            changed.append(f"prix {key}")
        if e["price"] and key not in cat:
            cat[key] = {**e["price"], "last_updated": "2026-09-22"}
            changed.append(f"catalogue {key}")

    # ingredient_map_v2 renvoyait `green_papaya` vers la papaye mûre (étape 0 de la résolution)
    imap_p = DATA / "recipes/ingredient_map_v2.json"
    imap = load(imap_p)
    gp = imap.get("green_papaya")
    if gp and gp.get("group_id_v2") != "green_papaya":
        gp.update({"nutri_id_v1": "green_papaya", "group_id_v2": "green_papaya", "canonical_name_en": "green papaya",
                   "method": "manual_2026_09_22", "cooking_variants": {"raw": "green_papaya", "default": "green_papaya"}})
        save(imap_p, imap)
        changed.append("ingredient_map_v2 green_papaya")

    avail_p = DATA / "graphs/ingredient_availability_graph_v1.json"
    avail = load(avail_p)
    for key, e in NEW.items():
        if key not in avail:
            avail[key] = e["avail"]
            changed.append(f"disponibilité {key}")
    save(avail_p, avail)

    for p, d in ((supp_p, supp), (n2_p, n2), (dict_p, dic), (alias_p, alias), (pmap_p, pmap), (cat_p, cat)):
        save(p, d)
    print("\n".join(changed) if changed else "rien à ajouter")


if __name__ == "__main__":
    main()
