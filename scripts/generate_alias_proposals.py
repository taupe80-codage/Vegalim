#!/usr/bin/env python3
"""
generate_alias_proposals.py
============================
Génère `scripts/alias_proposals.yaml` en faisant un fuzzy-match
entre les termes non résolus (AUDIT_KG_UNMATCHED.md)
et les group_ids / canonical_name_en du dict v2.

Usage :
    python scripts/generate_alias_proposals.py

Sortie :
    scripts/alias_proposals.yaml   (à relire + valider manuellement)

Légende du YAML généré :
    status: AUTO_HIGH     → confidence >= 0.80, acceptation probable directe
    status: AUTO_MED      → confidence 0.60–0.79, vérification recommandée
    status: AUTO_LOW      → confidence < 0.60, revue obligatoire
    status: SKIP          → terme sans sens nutritionnel (user/meta/phase)
    status: NO_ALIAS      → terme générique ambigu, pas d'alias pertinent
    group_id: null        → aucune suggestion trouvée
"""
from __future__ import annotations
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

# ── Chemins ─────────────────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DICT_PATH    = PROJECT_ROOT / "backend" / "data" / "ingredients" / "ingredients_dictionary.json"
OUT_PATH     = PROJECT_ROOT / "scripts" / "alias_proposals.yaml"

# ── Termes à traiter ─────────────────────────────────────────────────────────
# Catégorie A : easy_pluralization (1 terme)
EASY_PLURAL = ["lentil"]

# Catégorie B : likely_alias_to_add (145 termes)
LIKELY_ALIAS = [
    "amchur", "aneth", "attieke", "baguette", "bamboo_shoot",
    "banana_oat_porridge", "bean", "bean_sprout", "bechamel",
    "bell_pepper", "berbere", "black_bean_cooked", "black_eyed_bean_cooked",
    "bok_choy", "bouillon", "bread", "cacahuete", "capre", "chana_dal",
    "cheese", "chicken", "chocolate", "coconut_oil", "corn_husk", "cream",
    "creme", "curry_leaf", "curry_paste", "daikon", "dark_chocolate",
    "default_user", "doubanjiang_paste", "dried_pea", "dried_seaweed",
    "empanada_dough", "falafel", "fecule", "fermented_leaf_gundruk",
    "flaxseed_oil", "flour", "follicular_phase", "fromage_en_grain",
    "galangal", "garam_masala", "ghee", "glass_noodles", "gnocchi",
    "gochugaru", "gochujang", "green_curry_paste", "ground_flaxseeds",
    "gyoza_wrapper", "haricots_geant", "harissa", "high_protein_user",
    "hoisin_sauce", "ingredients", "jackfruit", "japanese_curry_roux",
    "kaffir_lime_leaf", "kashk", "kimchi", "kombucha", "lait",
    "laksa_paste", "legume", "lemongrass", "lentil_soup", "loroco",
    "luteal_phase", "mais_hominy", "mala_broth", "marjolaine", "masa_harina",
    "mayonnaise", "menstrual_phase", "menthe", "milk", "mirin",
    "mole_sauce", "moutarde", "mushroom", "myrtill", "noodles", "oil",
    "okra", "olive_oil", "origan", "ovulatory_phase", "pain_pita",
    "palm_oil", "paneer", "panko_breadcrumbs", "pate_piment", "pepper",
    "pesto", "phyllo_sheet", "piment_coreen", "pistou", "pizza_dough",
    "poireau", "polenta", "precooked_corn_flour", "pumpkin_seeds",
    "ras_el_hanout", "recipes", "red_curry_paste", "reshteh_noodles",
    "rice_noodle", "rice_vinegar", "rice_wrapper", "roasted_vegetable_quinoa",
    "salmon", "sambar_powder", "sesame_oil", "shortcrust_pastry",
    "sichuan_pepper", "small_eggplant", "soba_noodles", "sparkling_water",
    "spatzle", "starch", "sumac", "sunflower_oil", "swiss_chard", "tahini",
    "tempura_flour", "teriyaki_sauce", "tofu_soyeux", "tomato_basil_salad",
    "tortilla", "truffle", "udon", "vegetable_oil", "vegetarian_fish_sauce",
    "vegetarian_oyster_sauce", "vegetarian_user", "vine_leaf", "water",
    "weekly_plan_luteal_example", "white_bean_cooked", "wonton_wrapper",
    "yeast", "zaatar", "ziti",
]

# Termes sans sens nutritionnel (métadonnées KG / profils utilisateur)
META_TERMS = {
    "default_user", "high_protein_user", "vegetarian_user",
    "follicular_phase", "luteal_phase", "menstrual_phase", "ovulatory_phase",
    "weekly_plan_luteal_example", "ingredients", "recipes",
    "banana_oat_porridge", "tomato_basil_salad", "roasted_vegetable_quinoa",
    "lentil_soup", "mala_broth",  # plats composés — pas d'alias unique
}

# Termes trop génériques pour un alias unique fiable
GENERIC_TERMS = {
    "bean", "bread", "cheese", "chicken", "chocolate", "cream",
    "flour", "legume", "milk", "mushroom", "noodles", "oil",
    "pepper", "starch", "water",
}

# Overrides manuels connus (depuis le plan et les décisions §0)
MANUAL_OVERRIDES: dict[str, str | None] = {
    "lentil":               "lentils_whole_raw_raw",        # easy_pluralization
    "lait":                 "whole_milk_uht_uht_whole",     # décision §0.2
    "coconut_oil":          "coconut_oil_virgin_oil",
    "olive_oil":            "olive_oil_extra_virgin_oil",
    "sunflower_oil":        "sunflower_oil_oil",
    "sesame_oil":           "sesame_oil_oil",
    "flaxseed_oil":         "flaxseed_oil_oil",
    "palm_oil":             "palm_oil_oil",
    "vegetable_oil":        "vegetable_oil_oil",
    "ghee":                 "ghee_butter",
    "tahini":               "tahini_paste",
    "harissa":              "harissa_paste",
    "gochujang":            "gochujang_paste",
    "kimchi":               "kimchi_fermented",
    "miso":                 "miso_paste",
    "tofu_soyeux":          "silken_tofu_raw",
    "haricots_geant":       "giant_bean_cooked",
    "paneer":               "paneer_cheese",
    "jackfruit":            "jackfruit_raw",
    "daikon":               "daikon_radish_raw",
    "bok_choy":             "bok_choy_raw",
    "swiss_chard":          "swiss_chard_raw",
    "okra":                 "okra_raw",
    "bell_pepper":          "bell_pepper_raw",
    "bamboo_shoot":         "bamboo_shoot_canned",
    "vine_leaf":            "vine_leaf_canned",
    "corn_husk":            None,   # Emballage, pas un aliment
    "empanada_dough":       "wheat_flour_type_550",         # approximation
    "gyoza_wrapper":        "wheat_flour_type_550",
    "wonton_wrapper":       "wheat_flour_type_550",
    "phyllo_sheet":         "filo_pastry_raw",
    "tortilla":             "corn_tortilla_raw",
    "pizza_dough":          "wheat_flour_type_550",
    "shortcrust_pastry":    "shortcrust_pastry_raw",
    "gnocchi":              "potato_gnocchi_raw",
    "baguette":             "baguette_wheat_flour",
    "panko_breadcrumbs":    "breadcrumbs_panko",
    "glass_noodles":        "glass_noodles_dry",
    "rice_noodle":          "rice_noodle_dry",
    "soba_noodles":         "soba_noodle_dry",
    "udon":                 "udon_noodle_dry",
    "reshteh_noodles":      "reshteh_noodle_dry",
    "spatzle":              "spaetzle_dry",
    "ziti":                 "ziti_pasta_dry",
    "noodles":              None,   # trop générique
    "polenta":              "polenta_dry",
    "masa_harina":          "masa_harina_corn_flour",
    "precooked_corn_flour": "masa_harina_corn_flour",
    "pain_pita":            "pita_bread_wheat",
    "rice_wrapper":         "rice_paper_wrapper",
    "tempura_flour":        "wheat_flour_type_405",
    "lemongrass":           "lemongrass_stalk_raw",
    "galangal":             "galangal_root_raw",
    "kaffir_lime_leaf":     "kaffir_lime_leaf_fresh",
    "curry_leaf":           "curry_leaf_fresh",
    "aneth":                "dill_fresh",
    "menthe":               "mint_fresh",
    "marjolaine":           "marjoram_dried",
    "origan":               "oregano_dried",
    "zaatar":               "zaatar_spice_mix",
    "amchur":               "amchoor_powder",
    "berbere":              "berbere_spice_mix",
    "garam_masala":         "garam_masala_spice_mix",
    "ras_el_hanout":        "ras_el_hanout_spice_mix",
    "sambar_powder":        "sambar_powder_spice_mix",
    "gochugaru":            "gochugaru_chili_flakes",
    "piment_coreen":        "gochugaru_chili_flakes",
    "sichuan_pepper":       "sichuan_pepper_dried",
    "sumac":                "sumac_ground",
    "capre":                "caper_brine_packed",
    "moutarde":             "mustard_paste",
    "mayonnaise":           "mayonnaise_full_fat",
    "pesto":                "pesto_basil",
    "pistou":               "pesto_basil",
    "hoisin_sauce":         "hoisin_sauce_condiment",
    "mirin":                "mirin_seasoning",
    "rice_vinegar":         "rice_vinegar_seasoning",
    "teriyaki_sauce":       "teriyaki_sauce_condiment",
    "mole_sauce":           "mole_sauce_condiment",
    "doubanjiang_paste":    "doubanjiang_paste_condiment",
    "laksa_paste":          "laksa_paste_condiment",
    "curry_paste":          "red_curry_paste_condiment",
    "red_curry_paste":      "red_curry_paste_condiment",
    "green_curry_paste":    "green_curry_paste_condiment",
    "japanese_curry_roux":  "curry_roux_japanese",
    "pate_piment":          "chili_paste_condiment",
    "vegetarian_fish_sauce":    "vegetarian_fish_sauce_condiment",
    "vegetarian_oyster_sauce":  "vegetarian_oyster_sauce_condiment",
    "bechamel":             "bechamel_sauce",
    "bouillon":             "vegetable_stock_cube",
    "dried_pea":            "dried_pea_whole_raw",
    "chana_dal":            "chana_dal_raw",
    "black_bean_cooked":    "black_bean_cooked",
    "black_eyed_bean_cooked": "black_eyed_bean_cooked",
    "white_bean_cooked":    "white_bean_cooked",
    "attieke":              "attieke_fermented_cassava",
    "fermented_leaf_gundruk": "gundruk_fermented_leaf",
    "kashk":                "kashk_whey_product",
    "loroco":               "loroco_flower_bud",
    "mais_hominy":          "hominy_corn",
    "falafel":              "falafel_fried",
    "fromage_en_grain":     "cheese_curd",
    "myrtill":              "blueberry_raw",
    "salmon":               "atlantic_salmon_raw",
    "sparkling_water":      "sparkling_water_plain",
    "kombucha":             "kombucha_plain",
    "yeast":                "baker_yeast_dry",
    "fecule":               "potato_starch",
    "ground_flaxseeds":     "flaxseed_ground",
    "bean_sprout":          "mung_bean_sprout_raw",
    "dried_seaweed":        "dried_seaweed_wakame",
    "pumpkin_seeds":        "pumpkin_seed_raw",
    "small_eggplant":       "eggplant_raw",
    "poireau":              "leek_raw",
    "cacahuete":            "peanut_raw",
    "truffle":              "black_truffle_raw",
    "dark_chocolate":       "dark_chocolate_70_percent",
    "creme":                "heavy_cream_35_percent",
    "cream":                "heavy_cream_35_percent",
    "oil":                  None,   # trop générique
    "starch":               None,   # trop générique
}

# ── Normalisation ─────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    text = text.lower().strip().replace("_", " ")
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_s = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[\s\-_]+", " ", ascii_s).strip()


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, _normalize(a), _normalize(b)).ratio()


# ── Chargement du dict v2 ─────────────────────────────────────────────────────

def load_groups() -> list[tuple[str, str, str, str]]:
    """Retourne (group_id, canonical_name_en, canonical_name_fr, cat_id)."""
    with open(DICT_PATH, encoding="utf-8") as f:
        d = json.load(f)
    rows = []
    for cat_id, cat in d.get("categories", {}).items():
        for sub in cat.get("subcategories", {}).values():
            for gid, entry in sub.get("ingredient_groups", {}).items():
                rows.append((
                    gid,
                    entry.get("canonical_name_en", ""),
                    entry.get("canonical_name_fr", ""),
                    cat_id,
                ))
    return rows


def find_best_match(term: str, groups: list[tuple]) -> tuple[str | None, float, str]:
    """Retourne (group_id | None, confidence, rationale)."""
    best_gid, best_score, best_reason = None, 0.0, ""
    norm_term = _normalize(term)

    for gid, can_en, can_fr, cat_id in groups:
        # Correspondance exacte sur group_id
        if norm_term == _normalize(gid):
            return gid, 1.0, "exact_group_id"

        # Correspondance exacte sur canonical_name_en
        if can_en and norm_term == _normalize(can_en):
            return gid, 1.0, "exact_canonical_name_en"

        # Correspondance exacte sur canonical_name_fr
        if can_fr and norm_term == _normalize(can_fr):
            return gid, 1.0, "exact_canonical_name_fr"

        # starts-with group_id
        gid_norm = _normalize(gid)
        if gid_norm.startswith(norm_term) or norm_term.startswith(gid_norm):
            score = 0.85
            if score > best_score:
                best_gid, best_score, best_reason = gid, score, "prefix_group_id"

        # Fuzzy sur gid et noms canoniques
        for candidate, label in [
            (gid, "fuzzy_gid"),
            (can_en, "fuzzy_canonical_en"),
            (can_fr, "fuzzy_canonical_fr"),
        ]:
            if not candidate:
                continue
            score = _similarity(norm_term, _normalize(candidate))
            if score > best_score:
                best_gid, best_score, best_reason = gid, score, label

    return best_gid, best_score, best_reason


# ── Génération YAML ───────────────────────────────────────────────────────────

def confidence_label(score: float) -> str:
    if score >= 0.80:
        return "AUTO_HIGH"
    if score >= 0.60:
        return "AUTO_MED"
    return "AUTO_LOW"


def generate_yaml(groups: list[tuple]) -> str:
    """Génère le contenu YAML complet (sans librairie pyyaml — format simple)."""
    lines: list[str] = [
        "# alias_proposals.yaml",
        "# Généré automatiquement par scripts/generate_alias_proposals.py",
        "# Statuts : AUTO_HIGH (≥0.80) | AUTO_MED (0.60-0.79) | AUTO_LOW (<0.60)",
        "#           SKIP (terme non nutritionnel) | NO_ALIAS (terme trop générique) | MANUAL (override dur)",
        "#",
        "# Pour valider : passer `status` à ACCEPTED ou REJECTED",
        "# Le script patch_alias_index.py consommera uniquement status: ACCEPTED",
        "",
        "aliases:",
        "",
    ]

    all_terms = EASY_PLURAL + LIKELY_ALIAS
    stats = {"AUTO_HIGH": 0, "AUTO_MED": 0, "AUTO_LOW": 0, "SKIP": 0, "NO_ALIAS": 0, "MANUAL": 0}

    for term in sorted(all_terms):
        lines.append(f"  # ─── {term} ───")

        if term in META_TERMS:
            lines.append(f"  - alias: {term!r}")
            lines.append(f"    group_id: null")
            lines.append(f"    status: SKIP")
            lines.append(f"    note: 'Terme meta/utilisateur/plat composé — pas un ingrédient simple'")
            lines.append("")
            stats["SKIP"] += 1
            continue

        if term in GENERIC_TERMS:
            lines.append(f"  - alias: {term!r}")
            lines.append(f"    group_id: null")
            lines.append(f"    status: NO_ALIAS")
            lines.append(f"    note: 'Terme générique ambigu — plusieurs group_ids possibles, choisir manuellement'")
            lines.append("")
            stats["NO_ALIAS"] += 1
            continue

        if term in MANUAL_OVERRIDES:
            gid = MANUAL_OVERRIDES[term]
            # Verify gid exists
            known_gids = {g[0] for g in groups}
            if gid is None:
                lines.append(f"  - alias: {term!r}")
                lines.append(f"    group_id: null")
                lines.append(f"    status: SKIP")
                lines.append(f"    note: 'Override manuel : aucun alias pertinent'")
                lines.append("")
                stats["SKIP"] += 1
            elif gid in known_gids:
                lines.append(f"  - alias: {term!r}")
                lines.append(f"    group_id: {gid!r}")
                lines.append(f"    status: MANUAL")
                lines.append(f"    confidence: 1.00")
                lines.append(f"    note: 'Override manuel vérifié dans le dict v2'")
                lines.append("")
                stats["MANUAL"] += 1
            else:
                # gid not found in dict — fuzzy propose instead
                best_gid, best_score, best_reason = find_best_match(gid, groups)
                lines.append(f"  - alias: {term!r}")
                lines.append(f"    group_id: {best_gid!r}  # Override {gid!r} NOT FOUND in dict — fuzzy fallback")
                lines.append(f"    status: AUTO_LOW")
                lines.append(f"    confidence: {best_score:.2f}")
                lines.append(f"    match_reason: {best_reason!r}")
                lines.append(f"    note: 'ATTENTION: group_id de l overide introuvable dans le dict — vérifier manuellement'")
                lines.append("")
                stats["AUTO_LOW"] += 1
            continue

        # Fuzzy search
        best_gid, best_score, best_reason = find_best_match(term, groups)
        status = confidence_label(best_score)
        lines.append(f"  - alias: {term!r}")
        lines.append(f"    group_id: {best_gid!r}")
        lines.append(f"    status: {status}")
        lines.append(f"    confidence: {best_score:.2f}")
        lines.append(f"    match_reason: {best_reason!r}")
        lines.append("")
        stats[status] += 1

    # Stats footer
    lines.append("")
    lines.append("# ─── Statistiques ────────────────────────────────────────────────")
    for k, v in stats.items():
        lines.append(f"# {k}: {v}")
    total = sum(stats.values())
    ready = stats["AUTO_HIGH"] + stats["MANUAL"]
    lines.append(f"# Total: {total}")
    lines.append(f"# Prêts pour validation directe (AUTO_HIGH + MANUAL): {ready}")
    lines.append(f"# Nécessitent revue (AUTO_MED + AUTO_LOW + NO_ALIAS): {stats['AUTO_MED'] + stats['AUTO_LOW'] + stats['NO_ALIAS']}")

    return "\n".join(lines) + "\n"


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Chargement du dict v2...")
    groups = load_groups()
    print(f"  {len(groups)} groupes chargés.")

    print("Génération des propositions...")
    yaml_content = generate_yaml(groups)

    OUT_PATH.write_text(yaml_content, encoding="utf-8")
    print(f"Fichier généré : {OUT_PATH}")
    print(f"Lignes: {len(yaml_content.splitlines())}")

    # Print stats
    for line in yaml_content.splitlines():
        if line.startswith("# AUTO_") or line.startswith("# SKIP") or line.startswith("# MANUAL") \
           or line.startswith("# NO_ALIAS") or line.startswith("# Total") or line.startswith("# Prêts") \
           or line.startswith("# Néces"):
            print(line)


if __name__ == "__main__":
    main()
