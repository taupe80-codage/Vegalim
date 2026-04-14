"""
build_nutrition_aliases.py
──────────────────────────
Génère nutrition_aliases_v5.json :
  mapping  { clé_nutrition_v2 → clé_base_ontologie }

Stratégies de résolution (dans l'ordre) :
  1. Direct match  : clé existe telle quelle dans l'ontologie
  2. EN→FR inverse : fr_to_en_mapping inversé → candidats FR → fuzzy vs ontologie
  3. Variantes auto: singular/plural, underscores, préfixes typiques (cheese_, walnut_…)
  4. Manuel        : surcharges dans MANUAL_OVERRIDES

Usage :
  python scripts/nutrition/build_nutrition_aliases.py

Sortie :
  backend/data/nutrition/reference/nutrition_aliases_v5.json
"""

import json
import re
import time
from pathlib import Path
from difflib import get_close_matches

try:
    import requests as _requests
    _REQUESTS_OK = True
except ImportError:
    _REQUESTS_OK = False

# ── Chemins ──────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]

def find_file(root: Path, filename: str) -> Path:
    """Cherche un fichier dans tout l'arbre du projet."""
    matches = list(root.rglob(filename))
    if not matches:
        raise FileNotFoundError(
            f"Fichier '{filename}' introuvable sous {root}\n"
            f"Vérifier le nom exact avec : dir /s /b {filename}"
        )
    if len(matches) > 1:
        # Priorité : chemin le plus court (le moins imbriqué)
        matches.sort(key=lambda p: len(p.parts))
        print(f"  ⚠ Plusieurs '{filename}' trouvés, utilisation de : {matches[0]}")
    return matches[0]

ONTO_PATH   = find_file(ROOT, "ontology_v5.json")
NUT_PATH    = find_file(ROOT, "nutrition_v2.json")
MAP_PATH    = find_file(ROOT, "fr_to_en_mapping.json")
OUT_PATH    = ONTO_PATH.parent / "nutrition_aliases_v5.json"

# ── Surcharges manuelles (cas ambigus / non-résolvables automatiquement) ─────
# Clés ontologie candidates pour chaque ingrédient no-match.
# Ordre de priorité décroissant par paire : on prend la première qui existe dans l'onto.
MANUAL_OVERRIDES_CANDIDATES: dict[str, list[str]] = {
    # Laitiers génériques
    "cream_animal":      ["cream", "creme", "heavy_cream"],
    "cream_plant":       ["cream", "creme"],
    "milk_animal":       ["milk", "lait", "whole_milk"],
    "milk_plant":        ["milk", "lait"],
    "yogurt_animal":     ["yogurt", "yaourt"],
    "yogurt_plant":      ["yogurt", "yaourt"],
    "greek_yogurt":      ["greek_yogurt", "yaourt_grec", "yogurt"],
    "hemp_milk":         ["milk", "lait"],

    # Céréales / légumineuses
    "lentil":            ["lentils", "lentilles"],
    "fine_bulgur":       ["bulgur", "bulgur_ble", "boulgour"],
    "barley":            ["barley_complete", "barley_perlee", "barley", "orge"],
    "couscous":          ["graine_couscous", "couscous", "semoule_couscous"],
    "tortillas":         ["tortilla_ble", "tortilla_corn", "tortilla"],
    "fried_rice":        ["rice_blanc", "riz_blanc", "rice"],
    "rice_paper":        ["rice_blanc", "riz_blanc", "rice"],
    "glass_noodles":     ["rice", "rice_blanc"],  # proxy
    "soybean":           ["soybean", "soja", "beans"],
    "green_bean":        ["haricots_verts", "haricot_vert", "green_beans", "beans"],
    "gigante_bean":      ["haricot_blanc", "white_bean", "beans"],
    "buckwheat_crepe":   ["buckwheat", "farine_sarrasin", "buckwheat_flour"],
    "edamame":           ["beans"],  # pas de clé edamame dans onto
    "bean_sprouts":      ["beans", "isolat_soy_beans"],
    "gnocchi":           ["gnocchi", "potato"],
    "starch":            ["cornstarch_apple_terre", "corn_flour"],

    # Noix / graines
    "nut":               ["nuts", "noix"],
    "peanut":            ["peanuts", "arachide"],
    "pecan":             ["walnut_pecan", "noix_pecan"],
    "macadamia":         ["walnut_macadamia", "noix_macadamia"],
    "nutritional_yeast": ["yeast_beer", "levure_maltee", "levure_biere"],
    "flax_egg":          ["flaxseed", "graine_lin"],
    "pea_protein":       ["peas_protein", "proteine_pois", "green_peas"],

    # Légumes / tubercules
    "swiss_chard":       ["chard", "chard_carde", "bette"],
    "snow_pea":          ["peas_snow_peas", "pois_gourmand", "mange_tout"],
    "snow_peas":         ["peas_snow_peas", "pois_gourmand"],
    "sugar_snap_pea":    ["peas_snow_peas", "pois_gourmand"],
    "green_cabbage":     ["cabbage", "chou_vert", "cabbage_milan_(savoie)"],
    "red_apple":         ["apple", "pomme"],
    "green_apple":       ["apple", "pomme"],
    "green_mango":       ["mango", "mangue"],
    "green_papaya":      ["papaya", "papaye"],
    "watercress":        ["lettuce", "laitue"],  # proxy
    "salsify":           ["salsifis", "salsifis_noir"],
    "celery_root":       ["celeriac", "celery_rave", "celery_branche"],
    "bell_pepper_yellow":["yellow_bell_pepper", "poivron_jaune", "peppers"],
    "bitter_gourd":      ["cucumber", "zucchini"],  # proxy légume vert
    "kohlrabi":          ["cabbage", "chou_vert", "turnip"],  # proxy
    "pak_choi":          ["bok_choy", "pak_choi", "chou_pak_choi"],
    "corn_husk":         ["corn", "mais"],
    "bamboo_shoots":     ["bambou_pousse", "bambou", "bamboo_shoots"],
    "hard_boiled_egg":   ["egg", "oeuf_dur", "oeuf"],

    # Fruits / sucrants
    "dried_raisins":     ["raisins", "raisins_secs", "raisin_sec"],
    "icing_sugar":       ["sugar_blanc", "sucre_glace", "sugars"],
    "sugar":             ["sugars", "sucre", "sugar_blanc"],
    "agave":             ["agave_syrup", "sirop_agave", "agave"],
    "citrus":            ["lemon", "citron", "orange"],
    "dragon_fruit":      ["kiwi", "fruits"],  # proxy fruit exotique
    "chestnut":          ["chestnut", "chataigne", "marron"],
    "lemon_verbena":     ["lemon_verbena", "verveine_citron", "lemon"],
    "matcha_tea":        ["tea", "the_vert", "green_tea"],  # proxy
    "dill":              ["aneth", "dill"],
    "galangal":          ["galanga", "galangal", "ginger"],
    "caraway":           ["caraway", "carvi"],
    "aquafaba":          ["aquafaba", "chickpea"],

    # Épices / aromates
    "marjoram":          ["marjolaine", "marjoram", "oregano"],
    "lemongrass":        ["citronelle_(lemon_grass)", "citronnelle", "lemongrass"],
    "lemongrass_stalk":  ["citronelle_(lemon_grass)", "citronnelle"],
    "ground_coriander":  ["coriander", "coriandre"],
    "ground_cumin":      ["cumin"],
    "turmeric_fresh":    ["turmeric", "curcuma"],
    "smoked_paprika":    ["smoked_paprika", "paprika"],
    "goji_berry":        ["baie_goji", "goji_berry"],
    "star_anise":        ["spices", "anise"],  # proxy épice
    "kaffir_lime_leaf":  ["lemon", "lime"],  # proxy aromatique
    "curry":             ["curry_powder", "curry_en_poudre", "curry"],
    "curry_leaves":      ["curry", "curry_powder", "spices"],  # proxy
    "curry_paste":       ["curry", "curry_powder"],  # proxy
    "garam_masala":      ["spices", "curry_powder"],  # proxy mélange épices
    "nutmeg_whole":      ["nutmeg", "noix_muscade", "muscade"],
    "sumac":             ["lemon", "vinegar"],  # proxy acidulé
    "chili":             ["chili", "piment", "chili_powder"],
    "chili_paste":       ["chili", "piment", "peppers"],  # proxy
    "liquid_smoke":      ["vinegar", "tamari"],  # proxy aromatique
    "ras_el_hanout":     ["spices", "garam_masala", "curry_powder"],  # proxy

    # Produits transformés / condiments
    "tahini":            ["tahin", "tahini"],
    "mozzarella":        ["cheese_mozzarella", "mozzarella_milk_vache", "mozzarella"],
    "yeast":             ["yeast_boulanger", "levure_boulangere", "yeast"],
    "capers":            ["caper", "capre"],
    "lupine":            ["lupin", "lupins"],
    "corn_starch":       ["cornstarch_apple_terre", "corn_flour"],
    "tapioca_starch":    ["tapioca", "starch_corn", "starch_rice"],
    "vine_leaves":       ["lettuce", "spinach"],  # proxy feuille
    "umeboshi_plum":     ["plum", "prune"],
    "thai_basil":        ["basil", "thai_basil"],
    "fresh_coriander":   ["coriander", "coriandre"],
    "mayonnaise":        ["mayonnaise", "mayonnaise_70%_mg", "mayonnaise_allegee"],
    "halloumi":          ["cheese", "fromage", "feta"],  # proxy
    "pastry":            ["filo_pastry", "pate_brisee", "pate_feuilletee"],
    "tamarind_paste":    ["tamarind", "tamarind_paste", "pate_tamarin"],
    "coconut_flesh":     ["coconut", "noix_coco", "pulpe_coco"],
    "maca":              ["oats", "wheat_germ"],  # proxy poudre nutritive
    "stevia":            ["sugars", "sugar_blanc"],  # proxy sucrant
    "kefir_water":       ["kefir_water", "kefir"],
    "wheat_germ":        ["wheat_germ", "germe_ble", "son_ble"],
    "wheat_grass":       ["wheat_grass", "ble"],
    "paneer":            ["cheese", "fromage", "ricotta"],  # proxy
    "pesto":             ["basil", "basilic"],  # proxy

    # ── Proxies pour les 26 non-résolus persistants ──────────────────────────
    # Ces ingrédients sont absents de CIQUAL/USDA/CNF ; on leur assigne
    # la clé ontologique la plus proche nutritionnellement.

    # Fruits exotiques / superfoods
    # "acai" : NE PAS PROXYFIER — déjà complet dans nutrition_v2.json
    #          (confidence=1.0, data_quality=exact, sources CIQUAL+USDA+Phenol-Explorer)
    #          Un no-match ici = auto_correct_v5 laisse ses valeurs intactes. Correct.
    # Clés confirmées présentes dans l'ontologie (déduites des overrides originaux valides) :
    #   yogurt, cream, milk, egg, lemon, vinegar, tamari, basil, oregano, spices,
    #   cabbage, chou_vert, spinach, soybean, soja, beans, oats, buckwheat,
    #   sugars, sugar_blanc, corn, mais, kiwi, chili, piment, chili_powder,
    #   tapioca, cornstarch_apple_terre, corn_flour, pate_brisee, filo_pastry,
    #   peanuts, lupin, aquafaba, chickpea, ginger, cumin, turmeric, paprika,
    #   coriander, flaxseed, green_peas, peas_snow_peas, rice, rice_blanc,
    #   apple, mango, lentils, couscous, graine_couscous, raisins

    # Laitiers / fermentés
    "kashk":               ["yogurt", "cream", "milk"],                    # lactosérum fermenté persan (yogurt en tête, clé onto confirmée)
    "baobab":              ["kiwi", "lemon", "apple"],                     # poudre de fruit exotique

    # Bouillon / liquides
    # broth = liquide très dilué ; proxy le moins calorique disponible dans onto
    "broth":               ["lemon", "vinegar", "spinach"],                # bouillon (proxy: ingrédient très bas en cal)
    "bechamel":            ["milk", "cream", "oats"],                      # sauce beurre/lait/farine (milk en tête, confirmé)

    # Boulangerie / pâtes
    "crackers":            ["oats", "buckwheat", "cornstarch_apple_terre"],# biscuit sec (céréale de base confirmée)
    "empanada_dough":      ["pate_brisee", "filo_pastry", "oats"],        # pâte à tarte
    "gyoza_wrapper":       ["oats", "buckwheat", "egg"],                   # feuille de pâte fine (oats/egg confirmés)
    "reshteh_noodles":     ["oats", "buckwheat", "lentils"],               # nouilles perses (céréale + légumineuse)
    "spaetzle":            ["egg", "oats", "buckwheat"],                   # pâtes alsaciennes (egg confirmé en tête)

    # Condiments / sauces fermentées
    "fermented_bean_paste":["soybean", "soja", "beans"],                   # doenjang / tianmianjiang
    "gochujang":           ["chili", "piment", "chili_powder"],            # pâte piment fermentée
    "mirin":               ["sugar_blanc", "sugars", "rice"],              # alcool de riz sucré
    "ponzu":               ["lemon", "tamari", "vinegar"],                 # sauce citrus-soja (soy_sauce → tamari confirmé)
    "sriracha":            ["chili", "piment", "chili_powder"],            # sauce piment
    "worcestershire_vegan":["vinegar", "tamari", "lemon"],                 # sauce umami (soy_sauce → tamari confirmé)
    "za_atar":             ["oregano", "spices", "coriander"],             # mélange thym/sésame/sumac (thyme incertain → oregano confirmé)

    # Fermentés / vivants
    "gundruk":             ["spinach", "cabbage", "chou_vert"],            # légume fermenté népalais
    "kimchi":              ["cabbage", "chou_vert"],                       # chou fermenté coréen
    "natto":               ["soybean", "soja", "beans"],                   # soja fermenté japonais
    "sauerkraut":          ["cabbage", "chou_vert"],                       # choucroute

    # Protéines végétales transformées
    "soy_pave":            ["soybean", "soja", "beans"],                   # pavé de soja (tofu incertain → soybean confirmé)
    "tvp":                 ["isolat_soy_beans", "soybean", "soja"],        # protéine de soja texturée

    # Herbes / agrumes exotiques
    "shiso":               ["basil", "coriander", "oregano"],              # basilic japonais (herbs incertain → oregano confirmé)
    "yuzu":                ["lemon", "citron", "apple"],                   # agrume japonais (lime incertain → apple confirmé)

    # Gélifiants / édulcorants
    # vegan_gelatin = agar-agar (algue) — aucun proxy direct dans onto CIQUAL/USDA
    # Proxy nutritionnel : tapioca (fécule neutre, calories proches ~350 kcal/100g sec)
    "vegan_gelatin":       ["tapioca", "cornstarch_apple_terre", "corn_flour"], # agar proxy (agar/seaweed absents de onto)
    "xylitol":             ["sugars", "sugar_blanc"],                      # polyol sucrant

    # Maïs transformé
    "hominy":              ["corn", "mais"],                               # maïs nixtamalisé

    # Divers
    "molasses":            ["sugars", "sugar_blanc", "raisins"],           # mélasse (honey incertain → raisins confirmé)
}


def build_manual_overrides(candidates: dict[str, list[str]], onto_keys: set[str]) -> dict[str, str]:
    """Résout chaque candidat en prenant la première clé qui existe dans l'ontologie."""
    resolved = {}
    invalid  = []
    for ing, options in candidates.items():
        match = next((o for o in options if o in onto_keys), None)
        if match:
            resolved[ing] = match
        else:
            invalid.append((ing, options))
    if invalid:
        print(f"  ⚠ {len(invalid)} MANUAL_OVERRIDES sans cible valide dans l'ontologie :")
        for ing, opts in invalid:
            print(f"    {ing:30} candidates={opts}")
    return resolved

MANUAL_OVERRIDES: dict[str, str] = {}  # sera rempli dans main() après chargement onto


def load_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def build_en_to_fr(fr_to_en: dict) -> dict[str, list[str]]:
    """Inverse fr_to_en_mapping : EN_canonical → [FR_keys…]"""
    inv: dict[str, list[str]] = {}
    for fr_key, en_val in fr_to_en.items():
        inv.setdefault(en_val, []).append(fr_key)
    return inv


def get_ontology_keys(onto: dict) -> set[str]:
    keys = set()
    for entry in onto.get("bases", {}).values():
        # format attendu : {"base_key": ..., "variants": {...}}
        # ou liste d'objets avec "base_key"
        pass
    # Fallback : si onto est un dict plat keyed par base_key
    if isinstance(onto, dict):
        # Essai structure {"bases": {"lentils": {...}, ...}}
        if "bases" in onto:
            keys.update(onto["bases"].keys())
        else:
            keys.update(onto.keys())
    return keys


def normalize(key: str) -> str:
    return key.lower().replace("-", "_").replace(" ", "_")


def try_variants(key: str, onto_keys: set) -> str | None:
    """Essaie des transformations simples sur la clé."""
    candidates = [
        key,
        key + "s",          # lentil → lentils
        key.rstrip("s"),    # capers → caper
        "cheese_" + key,    # mozzarella → cheese_mozzarella
        "walnut_" + key,    # pecan → walnut_pecan
        "peas_" + key,      # snow_pea → peas_snow_pea
        key.replace("_animal", "").replace("_plant", ""),
    ]
    for c in candidates:
        if c in onto_keys:
            return c
    return None


def resolve_key(key: str, onto_keys: set, en_to_fr: dict, cutoff=0.75) -> str | None:
    key_n = normalize(key)

    # 1. Direct
    if key_n in onto_keys:
        return key_n

    # 2. Variantes simples
    v = try_variants(key_n, onto_keys)
    if v:
        return v

    # 3. EN→FR inverse : les FR keys sont candidats pour l'ontologie
    fr_candidates = en_to_fr.get(key_n, [])
    for fr_c in fr_candidates:
        if fr_c in onto_keys:
            return fr_c
        matches = get_close_matches(fr_c, onto_keys, n=1, cutoff=cutoff)
        if matches:
            return matches[0]

    # 4. Fuzzy direct sur la clé EN
    matches = get_close_matches(key_n, onto_keys, n=1, cutoff=cutoff)
    if matches:
        return matches[0]

    return None


# ── Caches réseau (évite les appels dupliqués) ───────────────────────────────
_OFF_CACHE: dict[str, str | None] = {}
_WD_CACHE:  dict[str, str | None] = {}

# Circuit breaker : désactive OFF après N échecs consécutifs
_OFF_CONSECUTIVE_ERRORS = 0
_OFF_MAX_ERRORS         = 3   # après 3 KO d'affilée → skip le reste
_OFF_DISABLED           = False


def _match_labels_to_onto(
    labels: list[str],
    onto_keys: set[str],
    en_to_fr: dict[str, list[str]],
    cutoff: float = 0.75,
) -> str | None:
    """
    Tente de mapper une liste de labels (API externe) vers une clé ontologie.
    Applique normalisation + resolve_key sur chaque candidat.
    Retourne la première correspondance trouvée, ou None.
    """
    for label in labels:
        candidate = normalize(label)
        resolved = resolve_key(candidate, onto_keys, en_to_fr, cutoff=cutoff)
        if resolved:
            return resolved
    return None


_OFF_UA = "nutrition-pipeline/1.0 (build_nutrition_aliases; contact: pipeline@local)"


def resolve_via_off(
    key: str,
    onto_keys: set[str],
    en_to_fr: dict[str, list[str]],
    max_results: int = 5,
) -> str | None:
    """
    Stratégie 5 — Open Food Facts API v2.

    Circuit breaker intégré : si OFF renvoie N erreurs consécutives
    (ex. 503 service indisponible), le resolver se désactive automatiquement
    pour les requêtes suivantes.
    """
    global _OFF_DISABLED, _OFF_CONSECUTIVE_ERRORS

    if not _REQUESTS_OK or _OFF_DISABLED:
        return None
    if key in _OFF_CACHE:
        return _OFF_CACHE[key]

    try:
        resp = _requests.get(
            "https://world.openfoodfacts.org/api/v2/search",
            params={
                "search_terms": key.replace("_", " "),
                "page_size":    max_results,
                "fields":       "product_name,generic_name,categories_tags",
                "json":         1,
            },
            headers={"User-Agent": _OFF_UA},
            timeout=8,
        )
        resp.raise_for_status()
        products = resp.json().get("products", [])
        _OFF_CONSECUTIVE_ERRORS = 0   # succès → reset compteur
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        _OFF_CONSECUTIVE_ERRORS += 1
        short = str(exc).split("\n")[0][:100]
        print(f"    ⚠ OFF [{key}] : {short}")
        if _OFF_CONSECUTIVE_ERRORS >= _OFF_MAX_ERRORS:
            _OFF_DISABLED = True
            print(f"    ✖ OFF désactivé après {_OFF_MAX_ERRORS} échecs consécutifs"
                  f" — passage direct à Wikidata")
        _OFF_CACHE[key] = None
        return None
    finally:
        time.sleep(0.3)   # courtoisie : ≤ 3 req/s

    # Collecte des labels bruts à tester
    labels: list[str] = []
    for p in products:
        for field in ("generic_name", "product_name"):
            raw = p.get(field, "")
            if raw:
                cleaned = re.sub(
                    r"\b(organic|bio|premium|fresh|brand|label|farm)\b",
                    "",
                    raw.lower(),
                    flags=re.I,
                ).strip()
                if cleaned:
                    labels.append(cleaned)
        for tag in p.get("categories_tags", []):
            lang, _, term = tag.partition(":")
            if lang in ("en", "fr") and term:
                labels.append(term.replace("-", "_"))

    result = _match_labels_to_onto(labels, onto_keys, en_to_fr)
    _OFF_CACHE[key] = result
    return result


def resolve_via_wikidata(
    key: str,
    onto_keys: set[str],
    en_to_fr: dict[str, list[str]],
) -> str | None:
    """
    Stratégie 6 — Wikidata API (wbsearchentities + P31 food filter).

    Recherche `key` en anglais, filtre les entités dont la description
    contient un mot clé alimentaire, puis tente de résoudre le label
    et ses alias contre l'ontologie.

    Requiert le package `requests`.
    """
    if not _REQUESTS_OK:
        return None
    if key in _WD_CACHE:
        return _WD_CACHE[key]

    # ── Étape 1 : recherche d'entités ────────────────────────────────────────
    try:
        resp = _requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action":    "wbsearchentities",
                "search":    key.replace("_", " "),
                "language":  "en",
                "format":    "json",
                "limit":     5,
            },
            headers={"User-Agent": "nutrition-pipeline/1.0 (build_nutrition_aliases)"},
            timeout=8,
        )
        resp.raise_for_status()
        search_hits = resp.json().get("search", [])
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        short = str(exc).split("\n")[0][:120]
        print(f"    ⚠ Wikidata search [{key}] : {short}")
        _WD_CACHE[key] = None
        return None
    finally:
        time.sleep(0.3)

    # ── Filtre sémantique : garder uniquement les entités alimentaires ────────
    FOOD_KEYWORDS = {
        "food", "ingredient", "spice", "herb", "vegetable", "fruit",
        "legume", "grain", "cereal", "nut", "seed", "condiment",
        "sauce", "fermented", "dish", "beverage", "drink", "edible",
        "aliment", "épice", "légume", "graine",
    }
    entity_ids: list[str] = []
    for hit in search_hits:
        desc = (hit.get("description") or "").lower()
        if any(kw in desc for kw in FOOD_KEYWORDS):
            entity_ids.append(hit["id"])

    if not entity_ids:
        _WD_CACHE[key] = None
        return None

    # ── Étape 2 : récupère labels + alias EN/FR du meilleur candidat ─────────
    try:
        resp2 = _requests.get(
            "https://www.wikidata.org/w/api.php",
            params={
                "action":      "wbgetentities",
                "ids":         "|".join(entity_ids[:3]),
                "props":       "labels|aliases",
                "languages":   "en|fr",
                "format":      "json",
            },
            headers={"User-Agent": "nutrition-pipeline/1.0 (build_nutrition_aliases)"},
            timeout=8,
        )
        resp2.raise_for_status()
        entities = resp2.json().get("entities", {})
    except KeyboardInterrupt:
        raise
    except Exception as exc:
        short = str(exc).split("\n")[0][:120]
        print(f"    ⚠ Wikidata entities [{key}] : {short}")
        _WD_CACHE[key] = None
        return None
    finally:
        time.sleep(0.3)

    labels: list[str] = []
    for eid, edata in entities.items():
        for lang in ("en", "fr"):
            lbl = edata.get("labels", {}).get(lang, {}).get("value", "")
            if lbl:
                labels.append(lbl)
            for alias_entry in edata.get("aliases", {}).get(lang, []):
                labels.append(alias_entry.get("value", ""))

    result = _match_labels_to_onto(labels, onto_keys, en_to_fr)
    _WD_CACHE[key] = result
    return result


def main():
    print("─── build_nutrition_aliases ───")

    onto    = load_json(ONTO_PATH)
    nut     = load_json(NUT_PATH)
    mapping = load_json(MAP_PATH)

    fr_mapping = mapping.get("mapping", mapping)  # support format avec/sans wrapper
    en_to_fr   = build_en_to_fr(fr_mapping)
    onto_keys  = get_ontology_keys(onto)

    global MANUAL_OVERRIDES
    MANUAL_OVERRIDES = build_manual_overrides(MANUAL_OVERRIDES_CANDIDATES, onto_keys)
    print(f"  Overrides manuels valides : {len(MANUAL_OVERRIDES)}")

    print(f"  Ontologie  : {len(onto_keys)} clés bases")
    # print provisoire, mis à jour après extraction
    print(f"  FR→EN map  : {len(fr_mapping)} entrées")

    aliases: dict[str, str] = {}
    unresolved: list[str]   = []

    # Ingrédients dans nutrition_v2 (clés directes)
    # Extraction complète : agrège toutes les clés ingrédients
    # (nutrition_v2 peut avoir ingredients + standalone_bases + partial_variants…)
    METADATA_KEYS = {
        # Champs scalaires / listes du niveau racine — ne sont pas des ingrédients
        "generated_at", "schema_version", "migrated_from", "version",
        "total_bases", "total_variants", "standalone_bases", "partial_variants",
        "sources", "field_coverage", "notes", "description",
        # Schema v3.x : clés supplémentaires
        "changelog",        # dict {"v3.0": [...], "v3.1": [...]} — ses clés ne sont PAS des ingrédients
        "promoted_date", "promoted_from", "previous_version",
        "aliases", "unresolved", "total", "_meta",
    }
    nut_keys: list[str] = []

    def collect_keys(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in METADATA_KEYS and not isinstance(v, dict):
                    continue          # ignorer les métadonnées scalaires
                if isinstance(v, dict) and any(
                    isinstance(vv, (dict, int, float)) for vv in v.values()
                ):
                    # c'est un dict d'ingrédients
                    nut_keys.extend(v.keys())
                elif isinstance(v, list):
                    nut_keys.extend(
                        e.get("id", e.get("key", str(i)))
                        for i, e in enumerate(v) if isinstance(e, dict)
                    )

    if isinstance(nut, dict):
        # Niveau 1 : clé "ingredients" explicite
        if "ingredients" in nut and isinstance(nut["ingredients"], dict):
            nut_keys.extend(nut["ingredients"].keys())
        # Niveau 1 : autres clés dict qui ressemblent à des ingrédients
        for k, v in nut.items():
            if k in METADATA_KEYS:
                continue
            if k not in ("ingredients",) and isinstance(v, dict):
                # Guard : ne pas itérer les dicts dont les valeurs sont des listes
                # (ex: changelog = {"v3.0": [...]} → ses clés ne sont pas des ingrédients)
                if any(isinstance(vv, (dict, int, float)) for vv in v.values()):
                    nut_keys.extend(v.keys())
            elif isinstance(v, list):
                nut_keys.extend(
                    e.get("id", e.get("key", ""))
                    for e in v if isinstance(e, dict) and ("id" in e or "key" in e)
                )
        # Fallback : si nut lui-même contient les ingrédients
        if not nut_keys:
            nut_keys = [k for k in nut.keys() if k not in METADATA_KEYS]
    elif isinstance(nut, list):
        nut_keys = [e.get("id", e.get("key", str(i))) for i, e in enumerate(nut)]

    # Dédupliquer tout en gardant l'ordre
    seen = set(); nut_keys_dedup = []
    for k in nut_keys:
        if k not in seen: seen.add(k); nut_keys_dedup.append(k)
    nut_keys = nut_keys_dedup

    print(f"  Nutrition  : {len(nut_keys)} ingrédients")

    for key in nut_keys:
        key_n = normalize(key)

        # Priorité 1 : surcharge manuelle
        if key_n in MANUAL_OVERRIDES:
            aliases[key_n] = MANUAL_OVERRIDES[key_n]
            continue

        # Priorité 2 : résolution automatique
        resolved = resolve_key(key_n, onto_keys, en_to_fr)
        if resolved and resolved != key_n:   # inutile d'aliaser vers soi-même
            aliases[key_n] = resolved
        elif resolved is None:
            unresolved.append(key_n)

    # ── Stratégie 5 : Open Food Facts (fallback réseau) ─────────────────────
    if not _REQUESTS_OK:
        print("\n  ⚠ 'requests' non installé — stratégies OFF + Wikidata ignorées")
        print("    → pip install requests")
    else:
        still_unresolved: list[str] = []
        off_resolved = 0
        print(f"\n  Stratégie 5 — Open Food Facts ({len(unresolved)} no-match) …")
        for key_n in unresolved:
            resolved = resolve_via_off(key_n, onto_keys, en_to_fr)
            if resolved and resolved != key_n:
                aliases[key_n] = resolved
                off_resolved += 1
            else:
                still_unresolved.append(key_n)
        print(f"    Résolus via OFF      : {off_resolved}")

        # ── Stratégie 6 : Wikidata (dernier recours) ─────────────────────────
        wd_resolved = 0
        print(f"  Stratégie 6 — Wikidata ({len(still_unresolved)} no-match) …")
        truly_unresolved: list[str] = []
        for key_n in still_unresolved:
            resolved = resolve_via_wikidata(key_n, onto_keys, en_to_fr)
            if resolved and resolved != key_n:
                aliases[key_n] = resolved
                wd_resolved += 1
            else:
                truly_unresolved.append(key_n)
        print(f"    Résolus via Wikidata : {wd_resolved}")
        unresolved = truly_unresolved

    # Résumé
    print(f"\n  Aliases générés : {len(aliases)}")
    print(f"  Non-résolus     : {len(unresolved)}")
    if unresolved:
        print(f"\n  Ingrédients sans alias (no-match persistant) :")
        for u in sorted(unresolved):
            print(f"    {u}")

    # Écriture
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "version": "v5",
        "description": "Alias nutrition_v2 keys → ontology_v5 base keys",
        "total": len(aliases),
        "unresolved": sorted(unresolved),
        "aliases": dict(sorted(aliases.items()))
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n  ✔ {OUT_PATH}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  ⚠ Interrompu (Ctrl-C) — fichier non écrit.")
        raise SystemExit(1)