#!/usr/bin/env python3
"""
sync_nutrition_to_dict.py
=========================
Synchronise ingredients_dictionary.json depuis nutrition_v2.json
après chaque passage du pipeline de génération nutritionnelle.

Usage :
    python sync_nutrition_to_dict.py
    python sync_nutrition_to_dict.py --dry-run
    python sync_nutrition_to_dict.py --input nutrition_v2.json --dict ingredients_dictionary.json

Ce que fait ce script :
    1. Rebuild nutrition_key → "base/variant" précis
       Chaque entry dict pointe sur le variant exact dans nutrition_v2.
       Résolution par ordre de priorité :
         a) id dict == base_name direct
         b) id dict == variant_name dans la base
         c) suffix de l'id après _ == variant_name
         d) name_fr / aliases correspondent à un variant
         e) overrides manuels (cas ambigus ou ombrelles)
         f) fr_to_en_mapping[id] → base_name
         g) v32 canonical_name_en → base_name  ← v2 NOUVEAU
         h) base seule si multi-variant irréductible

    1b. Routage plant-based depuis v32 axes (v2 NOUVEAU)
        Si axes.origine='végétal' et base résolue est animale (milk_animal,
        yogurt_animal, cream_animal) → rerouter vers l'équivalent végétal.

    1c. Affinement dairy depuis v32 teneur_MG (v2 NOUVEAU)
        Si teneur_MG connue et base = milk_animal/fromage_blanc/cream_animal
        → essayer de pointer sur le variant de matière grasse exact.

    2. Sync allergens_eu depuis nutrition_v2[base][variant].allergens
       Source de vérité : nutrition_v2 (CIQUAL/USDA).
       Mise à jour seulement si les listes divergent.

    3. Migration bioavailability_protein
       Stable entre variants (propriété de la catégorie d'ingrédient).
       Stockée une fois dans le dict, pas répétée dans chaque variant.

    4. Nettoyage des proxies nutritionnels
       health_score, nova_group, data_field_type sont variant-dépendants.
       Les stocker dans le dict crée une fausse précision.
       → supprimés du dict, récupérés en direct via nutrition_key.

Principe d'architecture :
    dict[id]          → identité culinaire (allergens, diet_profile,
                         substitutions, culinary_properties, bap…)
                         nutrition_key = "base/variant"
                                ↓
    nutr[base][variant] → vérité nutritionnelle mesurée

Le script est idempotent : peut être relancé sans effet de bord.
"""

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# Encodage UTF-8 sur stdout/stderr pour éviter UnicodeEncodeError sur console Windows (cp1252)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────
# Chemins par défaut (relatifs au projet ALIM)
# ─────────────────────────────────────────────────────────────────
DEFAULT_NUTR = Path("backend/data/nutrition/processed/nutrition_v2.json")
DEFAULT_DICT = Path("backend/data/ingredients/ingredients_dictionary.json")
# Dictionnaire v32 — source des axes structurés pour enrichissement NK
DEFAULT_V32  = Path("backend/data/ingredients/ingredients_v32.json")
# Carte de résolution produite par build_ontology_v6
DEFAULT_V32_MAP = Path("backend/data/ingredients/v32_resolution_map.json")

# ─────────────────────────────────────────────────────────────────
# Routage plant-based (v2) — Résout ISSUE-2 (axes.origine non mappé)
# ─────────────────────────────────────────────────────────────────
_ANIMAL_TO_PLANT: dict[str, str] = {
    "milk_animal":   "milk_plant",
    "yogurt_animal": "yogurt_plant",
    "cream_animal":  "milk_plant",
    "butter":        "oil",
}

# ─────────────────────────────────────────────────────────────────
# Affinement dairy par teneur_MG (v2)
# ─────────────────────────────────────────────────────────────────
_MG_TO_VARIANT: list[tuple[str, float, str]] = [
    ("milk_animal",    0.5,   "skim"),
    ("milk_animal",    2.5,   "semi_skim"),
    ("milk_animal",    99.0,  "whole"),
    ("fromage_blanc",  0.5,   "skim"),
    ("fromage_blanc",  5.0,   "low_fat"),
    ("fromage_blanc",  99.0,  "whole"),
    ("cream_animal",   22.0,  "light"),
    ("cream_animal",   32.0,  "whipping"),
    ("cream_animal",   99.0,  "whole"),
]


def _build_v32_tag_index(v32_path: Path) -> dict[str, dict]:
    """
    Construit un index de tagging : cfr_slug → {ing_id, axes, cen}
    pour associer chaque entrée du dictionnaire à son ing_id v32.

    Pour les canonicals ambigus (même cfr, axes différents), on garde
    l'entrée la plus générique (axes={} > etat_cuisson=cru > autre).
    """
    if not v32_path.exists():
        return {}

    with open(v32_path, encoding="utf-8") as f:
        v32 = json.load(f)

    # Score de généricité : moins d'axes = plus générique = prioritaire
    def _genericity(axes: dict) -> int:
        if not axes:
            return 0
        if set(axes.keys()) == {"etat_cuisson"} and axes.get("etat_cuisson") == "cru":
            return 1
        return len(axes) + 2

    raw_index: dict[str, list] = {}

    def _walk(node):
        if "subcategories" in node:
            for s in node["subcategories"]: _walk(s)
        if "ingredient_groups" in node:
            for g in node["ingredient_groups"]:
                cfr = (g.get("canonical_name_fr") or "").strip().lower()
                if not cfr: continue
                slug = re.sub(r"[^a-z0-9\u00e0-\u00fc]+", "_", cfr).strip("_")
                entry = {
                    "ing_id": g["id"],
                    "axes":   g.get("axes") or {},
                    "cen":    g.get("canonical_name_en") or "",
                    "score":  _genericity(g.get("axes") or {}),
                }
                raw_index.setdefault(slug, []).append(entry)

    for cat in v32.get("categories", []):
        _walk(cat)

    # Pour chaque slug, garder l'entrée la plus générique
    return {
        slug: min(entries, key=lambda e: e["score"])
        for slug, entries in raw_index.items()
    }


def _tag_dict_entries(
    ingrs: list[dict],
    v32_tag_index: dict,
    dry_run: bool = False,
) -> tuple[int, int]:
    """
    Ajoute v32_ing_id à chaque entrée dict si pas encore défini.
    Stratégie de matching par ordre de priorité :
      1. slug(dict.name_fr) == slug(v32.canonical_name_fr) → exact
      2. slug(dict.id) == slug(v32.canonical_name_fr) → id-based
      3. slug(dict.name_fr) préfixe de slug(v32.cfr) → générique

    Retourne (tagged_count, already_set_count).
    """
    tagged = already = 0
    for e in ingrs:
        if e.get("v32_ing_id"):
            already += 1
            continue

        name_fr = (e.get("name_fr") or "").strip().lower()
        dict_id  = (e.get("id") or "").strip().lower()

        # Slugifier les candidats de recherche
        slug_fr = re.sub(r"[^a-z0-9\u00e0-\u00fc]+", "_", name_fr).strip("_")
        slug_id = re.sub(r"[^a-z0-9\u00e0-\u00fc]+", "_", dict_id).strip("_")

        v32e = (v32_tag_index.get(slug_fr)
                or v32_tag_index.get(slug_id)
                or v32_tag_index.get(slug_fr.split("_")[0])   # premier mot
                or v32_tag_index.get(slug_id.split("_")[0]))

        if v32e:
            if not dry_run:
                e["v32_ing_id"] = v32e["ing_id"]
            tagged += 1

    return tagged, already

# ─────────────────────────────────────────────────────────────────
# Champs proxy à supprimer du dict (variant-dépendants)
# ─────────────────────────────────────────────────────────────────
PROXY_FIELDS = {"health_score", "nova_group", "data_field_type"}

# ─────────────────────────────────────────────────────────────────
# Ingrédients forcés à rester "unresolved" — aucune résolution
# automatique ni override ne peut écraser ces entrées.
# Utiliser quand le proxy le plus proche est nutritionnellement
# incorrect et qu'aucune variante adéquate n'existe dans nutrition_v2.
# Pour chaque entrée, documenter la raison et la cible future.
# ─────────────────────────────────────────────────────────────────
NK_FORCE_UNRESOLVED: set[str] = {
    # kashk retiré — proxy fresh_cheese/default ajouté dans MANUAL_NK_OVERRIDES (2026-05-08)
}

# ─────────────────────────────────────────────────────────────────
# Overrides manuels : dict_id → "base/variant"
# Cas ambigus ou ombrelles non inférables automatiquement.
# À compléter au fur et à mesure des nouveaux ingrédients.
# ─────────────────────────────────────────────────────────────────
MANUAL_NK_OVERRIDES: dict[str, str] = {
    "lait_coco":            "milk_plant/coconut",
    "mushroom":             "mushroom/button",
    "cabbage":              "cabbage/green",
    "vegetable_oil":        "oil/neutral",
    "oil":                  "oil/olive",
    "riz_rond":             "rice/risotto",
    "miso_paste":           "broth/miso",
    "tempura_flour":        "flour/wheat",
    "flour":                "flour/wheat",
    # Corrections nutrition_key cassés (v3)
    "shiitake_mushroom":    "shiitake_mushroom/default",
    "wood_ear_mushroom":    "wood_ear_mushroom/default",
    "fava_bean":            "bean/fava",
    "coconut_oil":          "oil/coconut",
    "sunflower_oil":        "oil/sunflower",
    "doubanjiang_paste":    "fermented_bean_paste/default",

    # ── Non résolus identifiés run 2026-05-01 (sync log) ─────────────────
    "feuilles_de_taro":     "taro/default",      # feuilles consommées comme légume
    "taro_leaf":            "taro/default",      # idem en anglais
    "wild_chicory":         "chicory/default",   # chicorée sauvage
    "preserved_lemon":      "citrus/lemon",      # citron confit, proxy citron
    "dried_seaweed":        "seaweed/wakame",    # algue séchée générique, proxy wakame
    # "legume" : catégorie ombrelle sans NK possible — laissé non résolu

    # ── kashk — laitage fermenté persan ─────────────────────────────────────────
    # Kashk = lactosérum concentré fermenté. Nutritionnellement proche du fromage blanc 20% MG.
    # fresh_cheese/default : cal=91, prot=7.5, fat=5.3, carbs=4.4 — proxy valide.

    # ── V13 — Non résolus identifiés run 2026-05-02 ───────────────────────────
    # Agrumes dérivés → variante citrus existante
    "lemon_zest":           "citrus/lemon",
    "lime_juice":           "citrus/lime",
    "orange_juice":         "citrus/orange",
    "orange_blossom_water": "citrus/orange",
    "rose_water":           "water/default",
    # Fruits dérivés / superfoods
    "acai_puree":           "acai/default",
    "candied_fruit":        "citrus/lemon",
    # Thés / infusions
    "matcha":               "matcha_tea/default",
    "matcha_tea":           "matcha_tea/default",
    "green_tea":            "green_tea/default",
    # Pâtes / boulangerie
    "pie_dough":            "pastry/default",
    "gnocchi_vegan":        "pasta/noodles",
    "soba_noodles":         "pasta/rice_noodles",
    "wide_rice_noodles":    "pasta/rice_noodles",
    # Piments / épices
    # Légumineuses (sous-types → base générique)
    "red_bean":             "bean/default",
    "black_eyed_pea":       "bean/default",
    "dried_peas":           "bean/default",
    "dried_fava_bean":      "bean/fava",
    "flageolet_bean":       "bean/default",
    "peas":                 "bean/default",
    "puy_lentil":           "lentil/default",
    "brown_lentils":        "lentil/default",
    "yellow_lentils":       "lentil/default",
    "red_lentils":          "lentil/default",
    "lentil":               "lentil/default",
    # Laitiers / fermentés dérivés
    "coconut_yogurt":       "yogurt_plant/default",
    "red_bean_paste":       "bean/default",
    "coconut_cream":        "milk_plant/coconut",
    "soy_cream":            "milk_plant/soy",
    "milk":                 "milk_animal/whole",
    # Pousses
    "sprouts":              "bean_sprouts/default",

    # ── V15 — Non résolus identifiés run 2026-05-09 ──────────────────────────
    # Post-restructure : nodes ombrelles + leaves réabsorbées
    "ancho_chili":          "chili/ancho",        # leaf déplacée → chili/ancho
    "baking":               "baking/default",     # node ombrelle créé par restructure
    "green_mango":          "mango/default",
    "gochujang":            "chili/default",
    "kombucha":             "vinegar/apple_cider",  # fermenté, proxy vinaigre ACV
    "macadamia":            "nut/macadamia",
    "pecan":                "nut/pecan",
    "pistachio":            "nut/pistachio",
    "walnut":               "nut/walnut",
    "bell_pepper_yellow":   "bell_pepper/yellow",
    "green_cabbage":        "cabbage/green",
    "coconut_flesh":        "coconut/default",
    "corn_husk":            "corn/default",       # feuille de maïs — proxy maïs
    "smoked_paprika":       "paprika/default",

    # ── V15b — Overrides résiduels run 2026-05-09 (77 non-résolus) ──────────────
    # Ces entrées ont une nk stale "base/default" qui ne correspond plus
    # à aucun variant post-restructure. On corrige vers la bonne clé.
    # Pour les bases dont le nom exact du variant est inconnu, on pointe
    # vers la base seule — resolve_nutrition_key prend alors le mono-variant.
    "allspice":             "spices",
    "amchoor_powder":       "spices",
    "baking_powder":        "baking",
    "baking_soda":          "baking",
    "bechamel":             "bechamel",
    "berbere":              "spices",
    "black_beans":          "bean",
    "black_pepper":         "pepper",
    "cacahuete":            "peanut",
    "cashew":               "nut",
    "cheddar":              "cheese",
    "cheese_curds":         "cheese",
    "chili_default":        "chili",
    "chili_paste":          "chili",
    "comte":                "cheese",
    "coriander_ground":     "coriander",
    "crackers":             "bread",
    "creme_fraiche":        "cream_animal",
    "dragon_fruit":         "dragon_fruit",
    "dried_chili":          "chili",
    "dried_pea":            "pea",
    "dried_raisins":        "dried_raisins",
    "empanada_dough":       "pastry",
    "feta":                 "cheese",
    "fresh_cheese":         "fresh_cheese",
    "fried_onion":          "onion",
    "fromage_blanc":        "fromage_blanc",
    "fromage_en_grain":     "cheese",
    "gigante_bean":         "bean",
    "gnocchi":              "pasta",
    "gochugaru":            "chili",
    "grain":                "grain",
    "greek_yogurt":         "yogurt_animal",
    "green_apple":          "apple",
    "green_peas":           "pea",
    "ground_cumin":         "cumin",
    "gruyere":              "cheese",
    "gruyere_cheese":       "cheese",
    "halloumi":             "halloumi",
    "haricots_geant":       "bean",
    "harissa":              "chili",
    "hazelnut":             "nut",
    "huile_friture":        "oil",
    "kashk":                "fresh_cheese",
    "korean_chili_pepper":  "chili",
    "lupine":               "lupine",
    "lychee":               "lychee",
    "mala_broth":           "broth",
    "mole_sauce":           "mole_sauce",
    "mozzarella":           "cheese",
    "nouilles_ramen":       "pasta",
    "oeufs_dur":            "egg",
    "palm_sugar":           "sugar",
    "paneer":               "cheese",
    "parmesan":             "cheese",
    "passion_fruit":        "passion_fruit",
    "pate_piment":          "chili",
    "pesto":                "sauce",
    "pistou":               "sauce",
    "raisins_sec":          "dried_raisins",
    "red_apple":            "apple",
    "ricotta":              "cheese",
    "salted_ricotta":       "cheese",
    "sambar_powder":        "spices",
    "sichuan_pepper":       "pepper",
    "snow_pea":             "pea",
    "snow_peas":            "pea",
    "spices":               "spices",
    "sri_lankan_curry_powder": "spices",
    "starch":               "starch",
    "sugar_snap_pea":       "pea",
    "tahini":               "tahini",
    "thai_basil":           "basil",
    "turmeric_fresh":       "turmeric",
    "tuscan_bread":         "bread",
    "vegetarian_oyster_sauce": "sauce",
    "yellow_lentil":        "lentil",
}


# Helpers
# ─────────────────────────────────────────────────────────────────
def norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).strip().lower())

def deaccent(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )

def resolve_nutrition_key(
    dict_id: str,
    name_fr: str,
    old_nk: str,
    nutr_ingr: dict,
    fr_en_mapping: dict,
    lookup: dict,
    v32_index: dict | None = None,
    v32_res_map: dict | None = None,
    v32_ing_id: str | None = None,
) -> str | None:
    """
    Résout dict_id → "base/variant" ou "base" dans nutrition_v2.

    Ordre de priorité :
      0. Force-unresolved
      1. Override manuel (MANUAL_NK_OVERRIDES)
      1.5. v32_ing_id → v32_resolution_map → base/variant  ← FIABLE (source_id)
      2. Ancien nutrition_key déjà précis (base/variant valide)
      3. id direct == base_name
      4. id direct == variant dans une base (cherche partout)
      5. suffix de l'id après _ == variant_name
      6. name_fr / aliases correspondent à un variant
      7. fr_en_mapping[id] → base_name
      g. v32_index : canonical_name_en → base_name
      8. lookup[name_fr] → base/variant
      9. Base seule si multi-variant irréductible
    """
    nutr_bases = set(nutr_ingr.keys())

    # 0. Force-unresolved — bloque toute résolution automatique ou override
    if dict_id in NK_FORCE_UNRESOLVED:
        return None

    # 1. Override manuel
    if dict_id in MANUAL_NK_OVERRIDES:
        ov = MANUAL_NK_OVERRIDES[dict_id]
        base_ov = ov.split("/")[0]
        var_ov  = ov.split("/")[1] if "/" in ov else None
        if base_ov in nutr_ingr:
            if var_ov is None or var_ov in nutr_ingr[base_ov].get("variants", {}):
                return ov
            return base_ov
        return ov

    # 1.5. v32_ing_id → v32_resolution_map — lien source_id, le plus fiable
    # Produit par build_ontology_v6 : évite tout text matching.
    if v32_ing_id and v32_res_map and v32_ing_id in v32_res_map:
        res = v32_res_map[v32_ing_id]
        _b, _v = res.get("base", ""), res.get("variant", "")
        if _b in nutr_ingr:
            if _v and _v in nutr_ingr[_b].get("variants", {}):
                return f"{_b}/{_v}"
            return _b
    if old_nk and "/" in old_nk:
        b, v = old_nk.split("/", 1)
        if b in nutr_ingr and v in nutr_ingr[b].get("variants", {}):
            return old_nk

    # Résolution de la base
    base = None
    # 3. id direct == base_name
    if dict_id in nutr_bases:
        base = dict_id
    # 7. fr_en_mapping[id]
    elif dict_id in fr_en_mapping and fr_en_mapping[dict_id] in nutr_bases:
        base = fr_en_mapping[dict_id]
    # g. v32_index : canonical_name_en slugifié → base_name  (v2 — ISSUE-2)
    # Utilise le canonical_name_en du dictionnaire v32 comme clé additionnelle.
    # Chaîne : dict_id → v32_entry → canonical_name_en → slug → nutr_base.
    elif v32_index and dict_id in v32_index:
        _cen = v32_index[dict_id].get("canonical_name_en") or ""
        if _cen:
            # Essai 1 : slug direct de l'EN
            _cen_slug = re.sub(r"[^a-z0-9]+", "_", _cen.lower()).strip("_")
            if _cen_slug in nutr_bases:
                base = _cen_slug
            else:
                # Essai 2 : premier mot de l'EN (ex: 'oat milk' → 'oat')
                _cen_first = _cen_slug.split("_")[0]
                if _cen_first in nutr_bases:
                    base = _cen_first
                # Essai 3 : chercher via fr_en_mapping avec le slug EN
                elif _cen_slug in fr_en_mapping and fr_en_mapping[_cen_slug] in nutr_bases:
                    base = fr_en_mapping[_cen_slug]
    # 8. lookup[name_fr]
    elif norm(name_fr) in lookup:
        lu = lookup[norm(name_fr)]
        return f"{lu['base']}/{lu['variant']}"
    elif deaccent(norm(name_fr)) in lookup:
        lu = lookup[deaccent(norm(name_fr))]
        return f"{lu['base']}/{lu['variant']}"
    # Ancien nk sans variant
    elif old_nk and "/" not in old_nk and old_nk in nutr_bases:
        base = old_nk

    if base is None:
        return None

    variants = nutr_ingr[base].get("variants", {})

    # Base sans variant → retourne la base seule (edge case)
    if not variants:
        return base

    # Base mono-variant → précise automatiquement
    if len(variants) == 1:
        return f"{base}/{list(variants.keys())[0]}"

    # Multi-variant : inférence
    # 4. id == variant_name direct
    if dict_id in variants:
        return f"{base}/{dict_id}"

    # 5. Suffix de l'id
    suffix = dict_id.split("_")[-1]
    if suffix in variants:
        return f"{base}/{suffix}"

    # 6. name_fr / aliases
    nfr = norm(name_fr)
    nfr_d = deaccent(nfr)
    for vname, vdata in variants.items():
        vname_fr = norm(vdata.get("name_fr", ""))
        aliases  = [norm(a) for a in vdata.get("aliases", [])]
        if nfr and (nfr == vname_fr or nfr in aliases):
            return f"{base}/{vname}"
        if nfr_d and (nfr_d == deaccent(vname_fr) or nfr_d in [deaccent(a) for a in aliases]):
            return f"{base}/{vname}"

    # Irréductible → base seule
    return base


def get_variant_data(nk: str, nutr_ingr: dict) -> dict:
    """Retourne le dict du variant pointé par nutrition_key, ou {}."""
    if not nk:
        return {}
    if "/" in nk:
        base, var = nk.split("/", 1)
        return nutr_ingr.get(base, {}).get("variants", {}).get(var, {})
    # Base seule → default ou premier variant
    variants = nutr_ingr.get(nk, {}).get("variants", {})
    return variants.get("default") or (list(variants.values())[0] if variants else {})


# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
def run(nutr_path: Path, dict_path: Path, dry_run: bool = False,
        v32_path: Path | None = None):

    with open(nutr_path, encoding="utf-8") as f:
        nutr = json.load(f)
    with open(dict_path, encoding="utf-8") as f:
        dic  = json.load(f)

    # Charger nutrition_index si disponible (lookup préconstruit)
    nutr_idx_path = nutr_path.parent / "nutrition_index.json"
    lookup: dict = {}
    if nutr_idx_path.exists():
        with open(nutr_idx_path, encoding="utf-8") as f:
            lookup = json.load(f).get("lookup", {})

    # Charger fr_to_en_mapping si disponible
    fr_en_path = dict_path.parent / "fr_to_en_mapping.json"
    fr_en_mapping: dict = {}
    if fr_en_path.exists():
        with open(fr_en_path, encoding="utf-8") as f:
            fr_en_mapping = json.load(f).get("mapping", {})

    # ── Charger v32 index pour enrichissement NK (v2) ────────────────────────
    v32_index: dict = {}
    v32_res_map: dict = {}
    _v32_file = v32_path or (dict_path.parent / "ingredients_v32.json")
    if _v32_file.exists():
        with open(_v32_file, encoding="utf-8") as f:
            _v32_data = json.load(f)

        def _v32_walk(node):
            if "subcategories" in node:
                for s in node["subcategories"]: _v32_walk(s)
            if "ingredient_groups" in node:
                for g in node["ingredient_groups"]:
                    cfr  = (g.get("canonical_name_fr") or "").strip().lower()
                    cfr_slug = re.sub(r"[^a-z0-9\u00e0-\u00fc]+", "_", cfr).strip("_")
                    if cfr_slug:
                        v32_index[cfr_slug] = {
                            "canonical_name_en":  g.get("canonical_name_en") or "",
                            "axes":               g.get("axes") or {},
                            "conditioning_types": g.get("conditioning_types") or [],
                            "ing_id":             g.get("id") or "",
                        }
        for _cat in _v32_data.get("categories", []):
            _v32_walk(_cat)
        print(f"  Dict v32 : {len(v32_index)} entrées indexées")
    else:
        print(f"  ⚠  ingredients_v32.json absent ({_v32_file}) — enrichissement NK désactivé")

    # ── Charger v32_resolution_map (produit par build_ontology_v6) ────────────
    _v32_map_file = dict_path.parent / "v32_resolution_map.json"
    if _v32_map_file.exists():
        with open(_v32_map_file, encoding="utf-8") as f:
            v32_res_map = json.load(f).get("resolution", {})
        print(f"  v32 resolution map : {len(v32_res_map)} ing_id → base/variant")
    else:
        print(f"  ⚠  v32_resolution_map.json absent — résolution step 1.5 désactivée")
        print(f"     Lancer build_ontology_v6.py pour le générer")

    nutr_ingr   = nutr["ingredients"]
    ingrs       = dic["ingredients"]

    # ── Passe 0 : tagging v32_ing_id (lien stable dict → v32) ───────────────
    # Associe chaque entrée dict à son ing_id v32 via canonical_name_fr.
    # Persisté dans le dict — pas recalculé à chaque run (idempotent).
    v32_tag_index = _build_v32_tag_index(_v32_file)
    tagged_new, tagged_existing = _tag_dict_entries(ingrs, v32_tag_index, dry_run=dry_run)
    if tagged_new:
        print(f"  Tagging v32_ing_id : {tagged_new} nouveaux, {tagged_existing} déjà définis")

    # ── Suppression des entrées non-ingrédients ───────────────────────────────
    # Ces IDs sont des catégories ombrelles ou entrées erronées sans valeur
    # nutritionnelle propre. Ils ne doivent pas exister dans le dictionnaire.
    INVALID_DICT_IDS: frozenset[str] = frozenset({
        "legume",       # catégorie générique (légumineuses) — pas un ingrédient
    })
    removed_invalid = [e["id"] for e in ingrs if e.get("id") in INVALID_DICT_IDS]
    if removed_invalid:
        ingrs[:] = [e for e in ingrs if e.get("id") not in INVALID_DICT_IDS]
        for rid in removed_invalid:
            print(f"  🗑  Supprimé (non-ingrédient) : {rid}")

    stats = {
        "nk_upgraded":             0,
        "nk_added":                0,
        "nk_unchanged":            0,
        "nk_unresolved":           0,
        "nk_via_v32_res_map":      0,  # résolu via v32_resolution_map (step 1.5)
        "nk_plant_rerouted":       0,
        "nk_mg_refined":           0,
        "allergens_synced":        0,
        "bioavailability_added":   0,
        "bioavailability_updated": 0,
        "proxy_removed":           0,
        "v32_tagged":              tagged_new,
    }
    # Collecte des non-résolus pendant la boucle — critère identique au compteur.
    # Bug corrigé : l'ancienne approche post-boucle filtrait `not e.get("nutrition_key")`
    # ce qui manquait les entrées avec une nutrition_key stale/incorrecte.
    unresolved_ids: list[str] = []

    for e in ingrs:
        eid     = e["id"]
        name_fr = e.get("name_fr", "")
        old_nk  = e.get("nutrition_key", "") or ""

        # ── 1. Rebuild nutrition_key ──────────────────────────────
        new_nk = resolve_nutrition_key(
            eid, name_fr, old_nk, nutr_ingr, fr_en_mapping, lookup,
            v32_index=v32_index,
            v32_res_map=v32_res_map,
            v32_ing_id=e.get("v32_ing_id"),
        )

        # Compter les résolutions via v32_resolution_map (step 1.5)
        if new_nk and e.get("v32_ing_id") and v32_res_map:
            _res = v32_res_map.get(e["v32_ing_id"], {})
            if _res and new_nk.startswith(_res.get("base", "___NOMATCH___")):
                stats["nk_via_v32_res_map"] += 1

        # ── 1b. Routage plant-based depuis axes.origine (v2) ──────
        # Si v32 indique origine='végétal' et NK pointe vers une base
        # animale → rerouter vers l'équivalent végétal.
        if new_nk and v32_index:
            _eid_slug = re.sub(r"[^a-z0-9\u00e0-\u00fc]+", "_",
                               eid.lower()).strip("_")
            _v32e = v32_index.get(_eid_slug, {})
            if _v32e.get("axes", {}).get("origine") == "végétal":
                _resolved_base = new_nk.split("/")[0]
                _plant_base = _ANIMAL_TO_PLANT.get(_resolved_base)
                if _plant_base and _plant_base in nutr_ingr:
                    new_nk = _plant_base  # sera précisé en mono-variant ci-dessous
                    stats.setdefault("nk_plant_rerouted", 0)
                    stats["nk_plant_rerouted"] += 1

        # ── 1c. Affinement dairy par teneur_MG (v2) ──────────────
        # Si v32 fournit axes.teneur_MG et base est un laitier,
        # essayer de préciser le variant (skim/semi_skim/whole…).
        if new_nk and v32_index:
            _eid_slug = re.sub(r"[^a-z0-9\u00e0-\u00fc]+", "_",
                               eid.lower()).strip("_")
            _v32e = v32_index.get(_eid_slug, {})
            _tmg_raw = _v32e.get("axes", {}).get("teneur_MG")
            if _tmg_raw is not None:
                try:
                    _tmg = float(str(_tmg_raw).split("-")[-1].strip().rstrip("%"))
                    _resolved_base = new_nk.split("/")[0]
                    _target_var = None
                    for _base_pat, _max_mg, _var in _MG_TO_VARIANT:
                        if _resolved_base == _base_pat and _tmg <= _max_mg:
                            _target_var = _var
                            break
                    if _target_var:
                        _variants = nutr_ingr.get(_resolved_base, {}).get("variants", {})
                        if _target_var in _variants:
                            new_nk = f"{_resolved_base}/{_target_var}"
                            stats.setdefault("nk_mg_refined", 0)
                            stats["nk_mg_refined"] += 1
                except (ValueError, TypeError):
                    pass

        if new_nk:
            if not old_nk:
                if not dry_run:
                    e["nutrition_key"] = new_nk
                stats["nk_added"] += 1
            elif new_nk != old_nk:
                if not dry_run:
                    e["nutrition_key"] = new_nk
                if "/" not in old_nk and "/" in new_nk:
                    stats["nk_upgraded"] += 1
                else:
                    stats["nk_added"] += 1
            else:
                stats["nk_unchanged"] += 1
        else:
            stats["nk_unresolved"] += 1
            unresolved_ids.append(eid)

        # Récupérer le variant résolu pour les passes suivantes
        effective_nk = new_nk or old_nk or ""
        vdata = get_variant_data(effective_nk, nutr_ingr)

        # ── 2. Sync allergens_eu ──────────────────────────────────
        nutr_al = sorted(vdata.get("allergens") or [])
        dict_al = sorted(e.get("allergens_eu") or [])
        if nutr_al != dict_al:
            if not dry_run:
                e["allergens_eu"] = nutr_al
            stats["allergens_synced"] += 1

        # ── 3. Migration bioavailability_protein ──────────────────
        # Stable entre variants → propriété du dict.
        # On met à jour si absent ou si la valeur a changé dans nutrition.
        bap_nutr = vdata.get("bioavailability_protein")
        if bap_nutr is None:
            # Fallback : chercher dans les autres variants de la base
            base = effective_nk.split("/")[0] if effective_nk else ""
            for v in nutr_ingr.get(base, {}).get("variants", {}).values():
                if v.get("bioavailability_protein") is not None:
                    bap_nutr = v["bioavailability_protein"]
                    break

        if bap_nutr is not None:
            if "bioavailability_protein" not in e:
                if not dry_run:
                    e["bioavailability_protein"] = bap_nutr
                stats["bioavailability_added"] += 1
            elif e["bioavailability_protein"] != bap_nutr:
                if not dry_run:
                    e["bioavailability_protein"] = bap_nutr
                stats["bioavailability_updated"] += 1

        # ── 4. Suppression des proxies nutritionnels ──────────────
        # health_score, nova_group, data_field_type varient par variant.
        # Aucun sens de les stocker dans le dict — ils trompent.
        for pf in PROXY_FIELDS:
            if pf in e:
                if not dry_run:
                    del e[pf]
                stats["proxy_removed"] += 1

    # ── Metadata ─────────────────────────────────────────────────
    if not dry_run:
        prev_version = dic.get("version", "unknown")
        # Incrémenter le minor version
        parts = prev_version.split("-diet_v")
        if len(parts) == 2 and parts[1].isdigit():
            new_version = f"{parts[0]}-diet_v{int(parts[1]) + 1}"
        else:
            new_version = f"{prev_version}_synced"

        dic["version"]              = new_version
        dic["nutrition_version"]    = nutr.get("schema_version", "?")
        dic["synced_at"]            = datetime.now(timezone.utc).isoformat()
        dic["total_ingredients"]    = len(ingrs)
        dic["sync_stats"]           = stats

        with open(dict_path, "w", encoding="utf-8") as f:
            json.dump(dic, f, ensure_ascii=False, indent=2)

    # ── Rapport ──────────────────────────────────────────────────
    nutr_version = nutr.get("schema_version", "?")
    total = len(ingrs)
    mode  = "[DRY-RUN]" if dry_run else "[EXÉCUTION]"

    print(f"{'═'*60}")
    print(f"  SYNC NUTRITION → DICT  {mode}")
    print(f"{'═'*60}")
    print(f"  nutrition_v2      : v{nutr_version} ({len(nutr_ingr)} bases)")
    print(f"  dict              : {total} ingrédients")
    print()
    print(f"  ── nutrition_key ──────────────────────────────")
    print(f"  upgradés base → base/variant  : {stats['nk_upgraded']}")
    print(f"  ajoutés                        : {stats['nk_added']}")
    print(f"  inchangés (déjà corrects)      : {stats['nk_unchanged']}")
    print(f"  non résolus                    : {stats['nk_unresolved']}")
    if stats.get('nk_via_v32_res_map'):
        print(f"  via v32 resolution map (1.5)   : {stats['nk_via_v32_res_map']}")
    if stats.get('nk_plant_rerouted'):
        print(f"  reroutés animal → plant (v2)   : {stats['nk_plant_rerouted']}")
    if stats.get('nk_mg_refined'):
        print(f"  affinés par teneur_MG (v2)     : {stats['nk_mg_refined']}")
    if stats.get('v32_tagged'):
        print(f"  entrées taguées v32_ing_id     : {stats['v32_tagged']}")
    print()
    print(f"  ── champs synchronisés ────────────────────────")
    print(f"  allergens_eu syncs             : {stats['allergens_synced']}")
    print(f"  bioavailability ajoutés        : {stats['bioavailability_added']}")
    print(f"  bioavailability mis à jour     : {stats['bioavailability_updated']}")
    print()
    print(f"  ── proxies nettoyés ───────────────────────────")
    print(f"  health_score/nova/dft retirés  : {stats['proxy_removed']}")
    print(f"  (récupérables via nk→variant)  ")
    print()

    if stats["nk_unresolved"] > 0:
        print(f"  ⚠ Non résolus ({len(unresolved_ids)}) :")
        for uid in sorted(unresolved_ids):
            old_nk = next((e.get("nutrition_key", "") for e in ingrs if e["id"] == uid), "")
            suffix = f"  [nk actuelle: {old_nk}]" if old_nk else ""
            print(f"    - {uid}{suffix}")
        print(f"    → Ajouter dans MANUAL_NK_OVERRIDES ou enrichir nutrition_v2")
        print()

    if not dry_run:
        print(f"  ✓ Sauvegardé → {dict_path}")
    print(f"{'═'*60}")


# ─────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Synchronise ingredients_dictionary depuis nutrition_v2"
    )
    parser.add_argument(
        "--input", type=Path, default=DEFAULT_NUTR,
        help=f"nutrition_v2.json (défaut : {DEFAULT_NUTR})"
    )
    parser.add_argument(
        "--dict", type=Path, default=DEFAULT_DICT,
        help=f"ingredients_dictionary.json (défaut : {DEFAULT_DICT})"
    )
    parser.add_argument(
        "--v32", type=Path, default=None,
        help="ingredients_v32.json (optionnel, auto-détecté si absent)"
    )
    parser.add_argument(
        "--v32-map", type=Path, default=None,
        help="v32_resolution_map.json produit par build_ontology_v6 (optionnel)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Affiche le rapport sans modifier les fichiers"
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"nutrition_v2 introuvable : {args.input}")
    if not args.dict.exists():
        raise FileNotFoundError(f"ingredients_dictionary introuvable : {args.dict}")

    run(args.input, args.dict, dry_run=args.dry_run, v32_path=args.v32)
