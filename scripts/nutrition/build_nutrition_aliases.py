"""
build_nutrition_aliases.py
──────────────────────────
Génère nutrition_aliases_v6.json :
  mapping  { clé_nutrition_v2 → clé_base_ontologie_v6 }

Stratégies de résolution (dans l'ordre) :
  1. Direct match  : clé existe telle quelle dans l'ontologie
  2. EN→FR inverse : fr_to_en_mapping inversé → candidats FR → fuzzy vs ontologie
  3. Variantes auto: singular/plural, underscores, préfixes typiques (cheese_, walnut_…)
  4. Manuel        : surcharges dans MANUAL_OVERRIDES

Usage :
  python scripts/nutrition/build_nutrition_aliases.py

Sortie :
  backend/data/nutrition/reference/nutrition_aliases_v6.json
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

ONTO_PATH   = find_file(ROOT, "ontology_v6.json")
NUT_PATH    = find_file(ROOT, "nutrition_v2.json")
MAP_PATH    = find_file(ROOT, "fr_to_en_mapping.json")
OUT_PATH    = ONTO_PATH.parent / "nutrition_aliases_v6.json"

# ── Ingrédients avec données propres dans nutrition_v2 — pas besoin d'alias ──
# Ils sortiraient sinon dans la liste "unresolved" sans que ce soit une erreur.
NO_ALIAS_NEEDED: frozenset = frozenset({
    "acai",   # confidence=1.0, sources CIQUAL+USDA+Phenol-Explorer — données complètes
    "seitan", # ajouté dans nutrition_v2 (patch v5.5, USDA FDC 174804) — données propres complètes
})

# ── Surcharges manuelles (cas ambigus / non-résolvables automatiquement) ─────
# Clés ontologie candidates pour chaque ingrédient no-match.
# Ordre de priorité décroissant par paire : on prend la première qui existe dans l'onto.
MANUAL_OVERRIDES_CANDIDATES: dict[str, list[str]] = {
    # Laitiers génériques
    "cream_animal":      ["cream", "creme", "heavy_cream"],
    "cream_plant":       ["cream_plant"],
    "milk_animal":       ["milk", "lait", "whole_milk"],
    "milk_plant":        ["milk_plant"],
    "yogurt_animal":     ["yogurt", "yaourt"],
    "yogurt_plant":      ["yogurt_plant"],
    "greek_yogurt":      ["greek_yogurt"],              # auto-ref nutrition_v2 (données propres)
    "almond_milk":       ["almond_milk"],

    # Céréales / légumineuses
    "lentil":            ["green_lentil"],
    "fine_bulgur":       ["bulgur", "bulgur_ble", "boulgour"],
    "barley":            ["barley_complete", "barley_perlee", "barley", "orge"],
    "couscous":          ["graine_couscous", "couscous", "semoule_couscous"],
    "tortillas":         ["tortilla_corn", "tortilla"],
    "glass_noodles":     ["glass_noodles"],  
    "soybean":           ["soybean", "soja"],
    "green_bean":        ["haricots_verts", "haricot_vert", "green_beans"],
    "gigante_bean":      ["gigante_bean"],
    "edamame":           ["edamame"],  
    "bean_sprouts":      ["bean_sprouts"],
    "gnocchi":           ["gnocchi", "gnocchi_a_la_pomme_de_terre"],
    "black_beans":       ["black_beans", "black_bean"],          # auto-ref n2 passe 2

    # Noix / graines
    "nut":               ["nuts", "noix"],
    "peanut":            ["peanuts", "arachide"],
    "pecan":             ["walnut_pecan", "noix_pecan"],
    "macadamia":         ["walnut_macadamia", "noix_macadamia"],
    "nutritional_yeast": ["nutritional_yeast", "yeast_biere_paillettes", "levure_de_biere_en_paillettes"],  # clé exacte onto confirmée
    "pea_protein":       ["peas_protein", "proteine_pois"],
    "pumpkin_seeds":     ["pumpkin_seeds"],

    # Légumes / tubercules
    "swiss_chard":       ["chard", "chard_carde", "bette", "bettes"],
    "snow_pea":          ["snow_pea"],                               # clé exacte dans l'onto
    "snow_peas":         ["snow_pea"],                               # clé exacte dans l'onto
    "green_cabbage":     ["cabbage", "chou_vert"],
    "red_apple":         ["red_apple", "pomme_gala"],
    "green_apple":       ["green_apple", "pomme_granny_smith"],
    "watercress":        ["watercress"],  
    "salsify":           ["salsify"],               
    "celery_root":       ["celeriac", "celery_rave"],
    "bell_pepper_yellow":["bell_pepper_yellow", "bell_pepper_jaune"],  # clés exactes onto confirmées
    "bitter_gourd":      ["bitter_gourd"],  
    "kohlrabi":          ["kohlrabi"],  
    "pak_choi":          ["Pakchoï", "pak_choi", "chou_pak_choi"],
    "corn_husk":         ["corn_husk"],
    "bamboo_shoots":     ["bambou_pousse", "bamboo_shoots"],
    "hard_boiled_egg":   ["oeuf_dur", "hard_boiled_egg"],

    # Fruits / sucrants
    "dried_raisins":     ["dried_raisins"],                               # exact key only
    "icing_sugar":       ["sucre_glace", "icing_sugar"],
    "sugar":             ["sugars", "sucre", "sugar_blanc"],
    "agave":             ["agave"],
    "dragon_fruit":      ["dragon_fruit"],  
    "chestnut":          ["chestnut", "chataigne", "marron"],
    "lemon_verbena":     ["lemon_verbena", "verveine_citron"],
    "matcha_tea":        ["matcha", "matcha_tea"],
    "dill":              ["aneth", "dill"],
    "galangal":          ["galanga", "galangal"],
    "caraway":           ["caraway", "carvi"],
    "aquafaba":          ["aquafaba"],
    "dried_fig":         ["dried_fig"],

    # Épices / aromates
    "marjoram":          ["marjolaine", "marjoram"],
    "lemongrass":        ["citronelle_(lemon_grass)", "citronnelle", "lemongrass", "lemon_grass", "lemon_grass_(citronella)"],
    "lemongrass_stalk":  ["lemongrass", "lemon_grass_(citronella)"], # clés exactes dans l'onto
    "ground_coriander":  ["coriander"],                        # coriandre = clé FR → pas onto
    "ground_cumin":      ["cumin"],
    "turmeric_fresh":    ["turmeric", "curcuma"],
    "smoked_paprika":    ["smoked_paprika"],
    "goji_berry":        ["baie_goji", "goji_berry"],
    "star_anise":        ["star_anise", "anis_etoile"], 
    "kaffir_lime_leaf":  ["kaffir_lime_leaf", "combava"], 
    "curry":             ["curry_powder", "curry_en_poudre", "curry"],
    "curry_leaves":      ["curry_leaves"],  
    "curry_paste":       ["curry_paste"],  
    "garam_masala":      ["garam_masala"],  
    "nutmeg_whole":      ["nutmeg", "noix_muscade", "muscade"],
    "chili":             ["chili", "chili_powder"],            # piment = clé FR (→ chili), pas clé onto
    "liquid_smoke":      ["liquid_smoke"],  
    "ras_el_hanout":     ["ras_el_hanout"],  
    "sumac":             ["sumac"],


    # Produits transformés / condiments
    "mozzarella":        ["cheese_mozzarella", "mozzarella_milk_vache", "mozzarella"],
    "yeast":             ["yeast_boulanger", "levure_boulangere", "yeast"],
    "capers":            ["caper", "capre"],
    "lupine":            ["lupin", "lupins"],
    "corn_starch":       ["cornstarch_apple_terre", "corn_flour"],
    "tapioca_starch":    ["tapioca", "tapioca_starch" ],
    "vine_leaves":       ["vine_leaves"],  
    "umeboshi_plum":     ["umeboshi_plum"],
    "thai_basil":        ["thai_basil", "basilic_thai"],
    "fresh_coriander":   ["fresh_coriander", "coriander"],     # coriandre = clé FR, fresh_coriander = onto direct
    "halloumi":          ["halloumi"],  
    "pastry":            ["pastry"],
    "tamarind_paste":    ["tamarind", "tamarind_paste", "pate_tamarin"],
    "coconut_flesh":     ["coconut_flesh"],                          # clé identique dans l'onto (auto-résolvable)
    "maca":              ["maca"],  
    "stevia":            ["stevia"],  
    "kefir_water":       ["kefir_water", "kefir"],
    "wheat_germ":        ["wheat_germ", "germe_ble"],
    "wheat_grass":       ["wheat_grass"],                   
    "paneer":            ["paneer"],

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
    #   sugars, sugar_blanc, corn, mais, kiwi, chili, chili_powder,
    #   tapioca, cornstarch_apple_terre, corn_flour, pate_brisee, filo_pastry,
    #   peanuts, lupin, aquafaba, chickpea, ginger, cumin, turmeric, paprika,
    #   coriander, sesame, clove, egg, soy_sauce, flaxseed, green_peas,
    #   peas_snow_peas, rice, rice_blanc,
    #   apple, mango, lentils, couscous, graine_couscous, raisins

    # Laitiers / fermentés
    "kashk":               ["kashk"],                   
    "baobab":              ["baobab"],                    

    # Bouillon / liquides
    # broth = liquide très dilué ; proxy le moins calorique disponible dans onto
    "broth":               ["broth"],               

    # Boulangerie / pâtes
    "crackers":            ["crackers"],
    "gyoza_wrapper":       ["gyoza_wrapper"],                  
    "reshteh_noodles":     ["reshteh_noodles"],              
    "spaetzle":            ["spaetzle"],                 

    # Condiments / sauces fermentées
    "fermented_bean_paste":["fermented_bean_paste"],                
    "mirin":               ["mirin"],             
    "ponzu":               ["ponzu"],                 
    "sriracha":            ["sriracha"],            
    "worcestershire_vegan":["worcestershire_vegan"],                
    "za_atar":             ["za_atar"],           

    # Fermentés / vivants
    "gundruk":             ["gundruk"],           
    "kimchi":              ["kimchi"],                       
    "sauerkraut":          ["sauerkraut"],                      

    # Protéines végétales transformées
    "soy_pave":            ["soy_pave"],                   
    "tvp":                 ["tvp"],        

    # Herbes / agrumes exotiques
    "shiso":               ["shiso"],              
    "yuzu":                ["yuzu"],                   

    # Gélifiants / édulcorants
    # vegan_gelatin = agar-agar (algue) — aucun proxy direct dans onto CIQUAL/USDA
    # Proxy nutritionnel : tapioca (fécule neutre, calories proches ~350 kcal/100g sec)
    "vegan_gelatin":       ["vegan_gelatin"], 
    "xylitol":             ["xylitol"],                   

    # Maïs transformé
    "hominy":              ["hominy"],                             

    # ── V13 — Résolution des 6 no-match persistants ───────────────────────────
    # bran/chlorella/coconut/comte/dill/dried_raisins/jalapeno/nutritional_yeast/
    # pastry/sorghum/sugar_snap_pea → couverts par CIQUAL_ID_OVERRIDES (validator_v13)
    "cheese_curds":        ["cheese_curds"],  
    "chrysanthemum_greens":["chrysanthemum_greens"],                      
    "coconut_aminos":      ["coconut_aminos"],                    
    "tropical_fruit":      ["tropical_fruit"],                       
    "water":               ["water", "eau"],                                     # clé propre — eau pure

    # Divers
    "molasses":            ["molasses"],

    # ── V14 — Résolution des 3 no-match persistants ───────────────────────
    # Ingrédients absents de l'onto CIQUAL/USDA/CNF → auto-référence nutrition_v2
    "green_papaya":        ["green_papaya"],    # papaye fraîche (USDA #169926)
    "hemp_milk":           ["hemp_milk"],       # lait de chanvre (brand avg)
    "sugar_snap_pea":      ["sugar_snap_pea"],  # pois gourmand (USDA #169957)

    # ══════════════════════════════════════════════════════════════════════
    # ALIASES RECETTES — audit 2026-04-27
    # Ingrédients recettes sans match → clés nutrition_v2 existantes
    # ══════════════════════════════════════════════════════════════════════

    # ── Huiles ───────────────────────────────────────────────────────────

    # ── Laits végétaux / crèmes ───────────────────────────────────────────
    "almond_milk":         ["almond_milk"],

    # ── Produits laitiers ─────────────────────────────────────────────────
    "milk":                ["milk", "lait"],                          # milk_animal absent → clés onto directes
    "mascarpone":          ["mascarpone"],

    # ── Beurre / matière grasse ───────────────────────────────────────────

    # ── Sucres ────────────────────────────────────────────────────────────

    # ── Légumineuses ──────────────────────────────────────────────────────
    "red_lentils":         ["red_lentil"],
    "dried_chickpeas":     ["chickpea"],
    "flageolet_bean":      ["bean_flageolet"],                       # match exact
    "peas":                ["peas"],       

    # ── Légumes ───────────────────────────────────────────────────────────
    "shallot":             ["shallot"],
    "butternut_squash":    ["butternut"],
    "small_eggplant":      ["eggplant"],
    "lamb_lettuce":        ["lamb_lettuce"],
    "chicory":           ["chicorée", "chicory"],

    # ── Graines ───────────────────────────────────────────────────────────
    "pumpkin_seeds":       ["pumpkin_seeds"],
    "sunflower_seeds":     ["sunflower_seeds"],
    "hemp_seeds":          ["hemp_seeds"],

    # ── Tofu ──────────────────────────────────────────────────────────────

    # ── Farines ───────────────────────────────────────────────────────────

    # ── Vinaigres ─────────────────────────────────────────────────────────
    "balsamic_vinegar":    ["balsamic_vinegar"],

    # ── Chocolat ──────────────────────────────────────────────────────────
    "dark_chocolate":      ["dark_chocolate"],

    # ── Agrumes / jus ─────────────────────────────────────────────────────
    "lime_juice":          ["lime_juice", "lime"],          
    "orange_juice":        ["orange_juice", "orange"],     

    # ── Fruits / dérivés ──────────────────────────────────────────────────
    "plum":                ["prune"],
    "rhubarb":             ["rhubarb"],
    "candied_fruit":       ["candied_fruit"],

    # ── Pains / boulangerie ───────────────────────────────────────────────
    "bagel":               ["bagel"],

    # ── Riz / pâtes ───────────────────────────────────────────────────────

    # ── Condiments / sauces ───────────────────────────────────────────────

    # ── Algues ────────────────────────────────────────────────────────────

    # ── Produits fermentés / spéciaux ─────────────────────────────────────

    # ── Boissons / alcools (utilisés en cuisson) ──────────────────────────
    "marsala":             ["marsala"],
    "cognac":              ["cognac"],

    # ── Divers recettes sucrées ───────────────────────────────────────────

    # ── Ingrédients dont les clés canoniques ont été corrigées en v3.3 ────────
    # fr_to_en v3.3 : cloves→clove, coriander_ground→coriander,
    #                 oeufs_dur→egg, sesame_seeds→sesame, +soy_sauce
    # Garantir la résolution directe même si la stratégie 2 ne les atteint pas.
    "soy_sauce":         ["soy_sauce", "tamari"],              # canonique onto ; tamari = fallback sans gluten
    "egg":               ["egg", "oeuf"],                      # canonique onto ; oeufs_dur était stale
    "clove":             ["clove"],                            # cloves (pluriel) était stale
    "sesame":            ["sesame", "sesame_seed"],            # sesame_seeds/sesame_seed étaient stale


    # Clés réelles dans l'onto, jamais atteintes par les stratégies auto :
    "chlorella":           ["chlorella_(chlorella)"],                    # algue unicellulaire, clé verbatim
    "citrus":            ["citrus"],                          # clé propre nutrition_v2
    "coconut":             ["coconut_flesh"],                            # noix de coco chair
    "bran":                ["sorghum_bran"],                             # son (coupé par tri alpha dans fuzzy)
    "pastry":              ["phyllo_pastry"],                            # pâte feuilletée fine
    "nutritional_yeast":   ["nutritional_yeast"],                       # clé exacte onto confirmée
    "jalapeno":            ["jalapeno"],                              # piment frais → proxy piment séché
    "comte":               ["comte", "Comté"],                                  # pâte pressée cuite, même famille

    # Proxies approchés (ingrédient absent de l'onto CIQUAL/USDA/CNF) :
    "attieke":             ["attieke"],               # semoule de manioc fermentée
    "dill":                ["dill"],                      # herbe aromatique verte (aneth absent)
    "water":               ["water"],                   # eau pure absente → eau minérale
}


def build_manual_overrides(
    candidates: dict[str, list[str]],
    onto_keys: set[str],
    nut_keys: set | None = None,
) -> dict[str, str]:
    """Résout chaque candidat en trois passes :
      1. Première candidate présente dans l'ontologie (clé onto directe).
      2. Fallback : si l'ingrédient lui-même existe dans nutrition_v2
         → auto-référence (clé → elle-même). Cas typique : base_recipes,
         ingrédients recettes absents de l'onto CIQUAL/USDA/CNF mais présents
         dans nutrition_v2 avec leurs propres données.
      3. Si aucune des deux → invalide (loggé mais non bloquant).
    """
    nut_keys = nut_keys or set()
    resolved = {}
    invalid  = []
    autoref  = []
    for ing, options in candidates.items():
        # Passe 1 : onto
        match = next((o for o in options if o.lower() in onto_keys), None)
        if match:
            match = match.lower()  # retourner la clé normalisée
        if match:
            resolved[ing] = match
            continue
        # Passe 2 : auto-référence via nutrition_v2
        if ing in nut_keys:
            resolved[ing] = ing
            autoref.append(ing)
            continue
        # Passe 3 : invalide
        invalid.append((ing, options))
    if autoref:
        print(f"  ✓ {len(autoref)} auto-références nutrition_v2 (absent onto) :", ', '.join(autoref[:5]) + ('…' if len(autoref) > 5 else ''))
    if invalid:
        print(f"  ⚠ {len(invalid)} MANUAL_OVERRIDES sans cible valide dans l'ontologie ni nutrition_v2 :")
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
    """
    Extrait les clés bases de l'ontologie.

    Supporte plusieurs structures :
      - {"ingredients": {"apple": {...}, ...}}   ← ontology_v6.json (standard)
      - {"bases": {"apple": {...}, ...}}          ← format alternatif
      - {"reference": {"apple": {...}, ...}}      ← format legacy
      - {"apple": {...}, ...}                     ← dict plat (fallback)
    """
    if not isinstance(onto, dict):
        return set()

    # Clés candidates dans l'ordre de priorité
    # "ingredients" est la clé standard de ontology_v6.json
    for section_key in ("ingredients", "bases", "reference", "ontology"):
        section = onto.get(section_key)
        if isinstance(section, dict) and len(section) > 20:
            # Heuristique : une section avec >20 clés est le vrai index ingrédients
            return {k.lower() for k in section.keys()}

    # Fallback dict plat : onto est directement indexé par base_key
    # Filtrer les clés de métadonnées connues
    _META_KEYS = {
        "generated_at", "schema_version", "version", "total_bases",
        "total_variants", "aliases", "aliases_count", "taxonomy_coverage",
        "field_coverage", "new_fields_v6", "base_recipe_computed_keys",
        "base_recipe_dual_keys", "sources", "source_weights",
        "reference", "ontology", "ingredients", "bases", "_meta",
    }
    flat_keys = {k.lower() for k in onto.keys() if k not in _META_KEYS}
    return flat_keys


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
    print("─── build_nutrition_aliases ─── (version corrigée)")

    onto    = load_json(ONTO_PATH)
    nut     = load_json(NUT_PATH)
    mapping = load_json(MAP_PATH)

    fr_mapping = mapping.get("mapping", mapping)
    en_to_fr   = build_en_to_fr(fr_mapping)
    onto_keys  = get_ontology_keys(onto)

    print(f"  Ontologie  : {len(onto_keys)} clés bases")
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
        # ── Artefacts de log/patch qui fuient dans les clés ingrédients ───
        # Ces champs apparaissent dans nutrition_v2 comme artefacts du pipeline
        # (scripts de patch qui écrivent des clés metadata au niveau ingrédients).
        "introduced_by_patch", "net_corrections_applied",
        "notes", "preexisting_inconsistencies",
        "patch", "corrections", "log", "stats",
        # ── V13 : clés du bloc _validation (fuient dans les ingredients) ───
        # _validation = {"date": ..., "patch": ..., "net_corrections_applied": ...,
        #               "preexisting_inconsistencies": ..., "introduced_by_patch": ...}
        # Ces chaînes apparaissent dans nut_keys quand collect_keys itère _validation.
        "date", "net", "preexisting", "introduced",
        # ── Recettes composées sans données nutritionnelles propres ──────
        "falafel",          # recette calculée depuis composition
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

    # ── V13 : purger les artefacts _validation qui passent à travers METADATA_KEYS ──
    # Ces chaînes sont les VALEURS du dict _validation (date, patch, stats…)
    # qui se retrouvent dans nut_keys quand la structure est itérée.
    _VALIDATION_ARTIFACTS = {
        "introduced_by_patch", "net_corrections_applied",
        "preexisting_inconsistencies", "notes", "patch", "date",
        "stats", "corrections", "log",
    }
    nut_keys = [k for k in nut_keys if k not in _VALIDATION_ARTIFACTS]

    # Exclure les ingrédients avec données propres dans nutrition_v2 (pas besoin d'alias)
    nut_keys = [k for k in nut_keys if k not in NO_ALIAS_NEEDED]

    print(f"  Nutrition  : {len(nut_keys)} ingrédients")

    # Résolution des MANUAL_OVERRIDES maintenant que nut_keys est disponible
    # (passe 2 : auto-référence pour les ingrédients absents de l'onto mais présents dans nutrition_v2)
    global MANUAL_OVERRIDES
    MANUAL_OVERRIDES = build_manual_overrides(
        MANUAL_OVERRIDES_CANDIDATES, onto_keys, nut_keys=set(nut_keys)
    )
    print(f"  Overrides manuels valides : {len(MANUAL_OVERRIDES)}")

    for key in nut_keys:
        key_n = normalize(key)

        # Priorité 1 : surcharge manuelle
        if key_n in MANUAL_OVERRIDES:
            aliases[key_n] = MANUAL_OVERRIDES[key_n]
            continue

        # Priorité 2 : résolution automatique
        resolved = resolve_key(key_n, onto_keys, en_to_fr)
        if resolved:
            aliases[key_n] = resolved   # inclut les direct-matches onto (key==resolved)
        elif resolved is None:
            unresolved.append(key_n)

    # ── Stratégies 5-6 : OFF + Wikidata — DÉSACTIVÉES ───────────────────────
    # Ces APIs externes (Open Food Facts, Wikidata) génèrent des timeouts
    # (503/429) et bloquent le pipeline. La résolution locale (stratégies 1-4)
    # couvre tous les cas actionables. Les no-match résiduels sont des ingrédients
    # P3 (sans données dans les raws) qui nécessitent une création manuelle.
    if unresolved:
        print(f"\n  Stratégies 5-6 (OFF/Wikidata) : désactivées — {len(unresolved)} no-match résiduels")
        print(f"  Ces ingrédients sont en P3 (aucune donnée dans les raws CIQUAL/USDA/CNF).")
        print(f"  Ajouter leurs données manuellement dans nutrition_v2.json si nécessaire.")
        print(f"  Pour forcer la résolution réseau : python build_nutrition_aliases.py --online")

    # Résumé
    print(f"\n  Aliases générés : {len(aliases)}")
    print(f"  Non-résolus     : {len(unresolved)}")
    if unresolved:
        print(f"\n  Ingrédients sans alias (no-match persistant) :")
        for u in sorted(unresolved):
            print(f"    {u}")

    # ── PRESERVE SECTIONS — ne pas écraser les sections gérées manuellement ─────
    # recipe_aliases, base_recipe_aliases, base_recipe_excluded
    # sont gérés par des scripts dédiés et ne doivent pas être écrasés ici.
    existing_protected = {}
    if OUT_PATH.exists():
        try:
            _existing = json.loads(OUT_PATH.read_text(encoding="utf-8"))
            for _section in ("recipe_aliases", "recipe_aliases_meta",
                             "base_recipe_aliases", "base_recipe_aliases_meta",
                             "base_recipe_excluded"):
                if _section in _existing:
                    existing_protected[_section] = _existing[_section]
        except Exception:
            pass

    # Écriture
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "version": "v6",
        "description": "Alias nutrition_v2 keys → ontology_v6 base keys",
        "total": len(aliases),
        "unresolved": sorted(unresolved),
        "aliases": dict(sorted(aliases.items())),
        **existing_protected,
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    preserved = list(existing_protected.keys())
    print(f"\n  ✔ {OUT_PATH}")
    if preserved:
        print(f"  ✔ Sections préservées : {preserved}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  ⚠ Interrompu (Ctrl-C) — fichier non écrit.")
        raise SystemExit(1)