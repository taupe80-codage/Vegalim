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
         f) base seule si multi-variant irréductible

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
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

# ─────────────────────────────────────────────────────────────────
# Chemins par défaut (relatifs au projet ALIM)
# ─────────────────────────────────────────────────────────────────
DEFAULT_NUTR = Path("backend/data/nutrition/processed/nutrition_v2.json")
DEFAULT_DICT = Path("backend/data/ingredients/ingredients_dictionary.json")

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
    "kashk",          # lactosérum fermenté iranien — miso/white est un proxy incorrect
                      # → créer kashk/default dans nutrition_v2 (~50kcal, riche Ca+protéines)
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
    "kashk":                "miso/white",
    "flour":                "flour/wheat",
    # Corrections nutrition_key cassés (v3)
    "oeufs_dur":            "egg/hard_boiled",
    "shiitake_mushroom":    "shiitake_mushroom/default",
    "wood_ear_mushroom":    "wood_ear_mushroom/default",
    "fava_bean":            "bean/fava",
    "coconut_oil":          "oil/coconut",
    "sunflower_oil":        "oil/sunflower",
    "fromage_blanc":        "fromage_blanc/default",
    "doubanjiang_paste":    "fermented_bean_paste/default",

    # ── Non résolus identifiés run 2026-05-01 (sync log) ─────────────────
    "huile_friture":        "oil/default",       # huile de friture générique
    "nouilles_ramen":       "pasta/default",     # ramen = blé + eau, proxy pasta
    "feuilles_de_taro":     "taro/default",      # feuilles consommées comme légume
    "taro_leaf":            "taro/default",      # idem en anglais
    "wild_chicory":         "chicory/default",   # chicorée sauvage
    "yellow_lentil":        "lentil/default",    # lentille jaune ≈ lentille générique
    "tuscan_bread":         "bread/default",     # pain toscan, proxy pain blanc
    "preserved_lemon":      "citrus/lemon",      # citron confit, proxy citron
    "dried_seaweed":        "seaweed/wakame",    # algue séchée générique, proxy wakame
    "palm_sugar":           "sugar/default",     # sucre de palme ~ sucre générique (clé n2)
    # "legume" : catégorie ombrelle sans NK possible — laissé non résolu

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
    "korean_chili_pepper":  "chili/default",
    "gochugaru":            "chili/default",
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
}

# ─────────────────────────────────────────────────────────────────
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
) -> str | None:
    """
    Résout dict_id → "base/variant" ou "base" dans nutrition_v2.

    Ordre de priorité :
      1. Override manuel (MANUAL_NK_OVERRIDES)
      2. Ancien nutrition_key déjà précis (base/variant valide)
      3. id direct == base_name
      4. id direct == variant dans une base (cherche partout)
      5. suffix de l'id après _ == variant_name
      6. name_fr / aliases correspondent à un variant
      7. fr_en_mapping[id] → base_name
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
        # Si l'override ne résout plus (base supprimée) → continuer

    # 2. Ancien nutrition_key déjà base/variant valide
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
def run(nutr_path: Path, dict_path: Path, dry_run: bool = False):

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

    nutr_ingr   = nutr["ingredients"]
    ingrs       = dic["ingredients"]

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
        "nk_upgraded":             0,  # base → base/variant
        "nk_added":                0,  # absent → résolu
        "nk_unchanged":            0,  # déjà correct
        "nk_unresolved":           0,  # non résolvable
        "allergens_synced":        0,
        "bioavailability_added":   0,
        "bioavailability_updated": 0,
        "proxy_removed":           0,
    }

    for e in ingrs:
        eid     = e["id"]
        name_fr = e.get("name_fr", "")
        old_nk  = e.get("nutrition_key", "") or ""

        # ── 1. Rebuild nutrition_key ──────────────────────────────
        new_nk = resolve_nutrition_key(
            eid, name_fr, old_nk, nutr_ingr, fr_en_mapping, lookup
        )

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
        unresolved = [e["id"] for e in ingrs if not e.get("nutrition_key")]
        print(f"  ⚠ Non résolus ({len(unresolved)}) :")
        for uid in unresolved:
            print(f"    - {uid}")
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
        "--dry-run", action="store_true",
        help="Affiche le rapport sans modifier les fichiers"
    )
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"nutrition_v2 introuvable : {args.input}")
    if not args.dict.exists():
        raise FileNotFoundError(f"ingredients_dictionary introuvable : {args.dict}")

    run(args.input, args.dict, dry_run=args.dry_run)
