"""
diet.py — Taxonomies régimes, calcul des flags diététiques et health_scores.

Fusionne : diet_flag_engine + diet_flag_auto_engine
           + vegetarian_forbidden_ingredients_global.json (supprimé — fusionné ici)

API publique :
    compute_diet_flags(recipe)        → dict  {vegan, vegetarian, gluten_free,
                                               lactose_free, nut_free, raw, kid_friendly}
    compute_health_scores(recipe)     → dict  {glycemic_category, high_protein,
                                               low_calorie, high_fiber, low_sodium,
                                               low_sat_fat, anti_inflammatory_score,
                                               fodmap_level, kcal, protein_g, ...}
    compute_context_tags(recipe)      → dict | None   {sport, meal_timing, ...}
    apply_all_scores(recipe, force)   → dict  recette enrichie (3 colonnes JSONB)
    apply_flags(recipe, force)        → dict  rétrocompatibilité (diet_flags seuls)
    batch_update(recipes, force)      → dict  rapport de mise à jour
    audit(recipes)                    → list  divergences stocké vs calculé

Taxonomies exportées (source unique) :
    NON_VEGAN, NON_VEGETARIAN, GLUTEN_IDS, LACTOSE_IDS, NUT_IDS

NON_VEGETARIAN couvre (147 entrées) :
    viandes rouges, volailles, abats, charcuterie, poissons,
    crustacés & mollusques, œufs de poisson, graisses animales,
    agents d'origine animale (gélatine, carmin, présure…),
    insectes, condiments à base de poisson, bouillons carnés.

    Note USDA (usda_flat.json) : les catégories Beef Products, Poultry Products,
    Pork Products, Sausages and Luncheon Meats, Finfish and Shellfish Products et
    Lamb, Veal, and Game Products ont été intégralement supprimées du dataset
    (67 aliments retirés sur 365). Le matching texte exclut volontairement
    "kidney" (kidney bean) et "oyster" (champignon) pour éviter les faux positifs —
    ces mollusques/abats sont couverts par leur catégorie USDA.
"""
from __future__ import annotations

import unicodedata
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


# ── Normalisation ──────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


# ── Taxonomies (source unique pour tout le projet) ────────────────────────────

NON_VEGAN: frozenset[str] = frozenset({
    "oeuf", "egg", "hard_boiled_egg", "lait", "milk",
    "beurre", "butter", "fromage", "cheese",
    "feta", "parmesan", "mozzarella", "ricotta", "halloumi", "paneer",
    "salted_ricotta", "gruyere_cheese", "cheddar", "manchego",
    "fromage_blanc", "fromage_en_grain", "fresh_cheese", "queijo",
    "cheese_curds", "feta_fromage_blanc",
    "creme", "creme_fraiche", "cream",
    "yaourt", "yogurt", "greek_yogurt", "plain_yogurt",
    "miel", "honey", "ghee", "kashk", "mayonnaise",
    "pate_brisee", "shortcrust_pastry",
})

NON_VEGETARIAN: frozenset[str] = frozenset({
    # ── Viandes rouges ────────────────────────────────────────────────────────
    "boeuf", "beef", "veau", "veal", "porc", "pork", "lamb", "agneau",
    "goat", "horse", "bison", "venison", "wild_boar", "elk", "moose",
    "rabbit", "kangaroo", "alligator", "turtle",
    # ── Volailles ────────────────────────────────────────────────────────────
    "poulet", "chicken", "dinde", "turkey", "duck", "canard",
    "goose", "quail", "pheasant", "partridge", "guinea_fowl",
    "pigeon", "squab", "ostrich",
    # ── Abats ────────────────────────────────────────────────────────────────
    # Note : "kidney" exclu — faux positif avec "kidney bean" (légumineuse).
    "liver", "heart", "tripe", "tongue", "brain",
    "sweetbreads", "blood", "bone_marrow",
    # ── Charcuterie ──────────────────────────────────────────────────────────
    "bacon", "jambon", "ham", "lard", "prosciutto", "salami",
    "pepperoni", "chorizo", "mortadella", "bresaola", "pastrami",
    "bologna", "andouille", "kielbasa", "blood_sausage",
    "liverwurst", "headcheese", "pork_rinds", "pork_crackling",
    # ── Poissons ─────────────────────────────────────────────────────────────
    "poisson", "fish", "saumon", "salmon", "thon", "tuna",
    "anchois", "anchovies", "anchovy", "sardine", "cod", "haddock",
    "tilapia", "trout", "herring", "mackerel", "sea_bass", "sea_bream",
    "red_snapper", "halibut", "sole", "flounder", "pollock", "catfish",
    "swordfish", "monkfish", "mahi_mahi", "grouper", "carp", "perch",
    "pike", "eel", "skate", "ray", "bass",
    # ── Crustacés & mollusques ────────────────────────────────────────────────
    # Note : "oyster" exclu — faux positif avec "oyster mushroom" (champignon).
    "crevette", "shrimp", "prawn", "crab", "lobster", "crayfish",
    "moule", "mussel", "clam", "scallop", "octopus", "squid",
    "sea_urchin", "abalone", "whelk", "barnacle",
    # ── Œufs de poisson & dérivés marins ──────────────────────────────────────
    "caviar", "fish_roe", "tobiko", "ikura",
    "bonito_flakes", "katsuobushi",
    "dried_shrimp", "dried_squid",
    # ── Graisses animales ─────────────────────────────────────────────────────
    "beef_tallow", "suet", "dripping", "chicken_fat",
    "schmaltz", "duck_fat", "goose_fat",
    # ── Agents d'origine animale ──────────────────────────────────────────────
    "gelatin", "isinglass", "rennet",
    "carmine", "cochineal", "e120",
    "l_cysteine", "e920",
    "albumin",
    # ── Insectes ─────────────────────────────────────────────────────────────
    # Note : "ant" exclu — faux positif avec "cantaloupe" et autres mots composés.
    "cricket", "mealworm", "locust", "grasshopper",
    "silkworm", "black_soldier_fly_larvae",
    # ── Condiments & sauces à base de poisson ─────────────────────────────────
    "fish_sauce", "oyster_sauce", "shrimp_paste",
    "anchovy_paste", "worcestershire_sauce",
    "nam_pla", "nuoc_mam", "bagoong", "prahok",
    # ── Bouillons carnés ──────────────────────────────────────────────────────
    "viande", "meat",
    "chicken_stock", "beef_stock", "fish_stock", "lamb_stock",
    "pork_stock", "veal_stock", "game_stock",
    "bone_broth", "dashi", "meat_broth",
})

# ── Catégories USDA non-végétariennes (usda_flat.json) ────────────────────────
# Ces catégories sont intégralement non-végétariennes et doivent être exclues
# lors de tout filtrage du dataset USDA, indépendamment du matching par token.
USDA_NON_VEGETARIAN_CATEGORIES: frozenset[str] = frozenset({
    "Beef Products",
    "Poultry Products",
    "Pork Products",
    "Sausages and Luncheon Meats",
    "Finfish and Shellfish Products",
    "Lamb, Veal, and Game Products",
})

VEGAN_EXCEPTIONS: frozenset[str] = frozenset({
    "lait_amande", "lait_soja", "lait_coco", "lait_riz", "lait_avoine",
    "soy_milk", "almond_milk", "oat_milk", "coconut_milk", "rice_milk",
    "fromage_vegan", "cheddar_vegane", "mozzarella_vegane",
    "yaourt_vegan", "yaourt_coco", "coconut_yogurt", "soy_yogurt",
    "creme_vegan", "mayonnaise_vegan", "vegan_butter",
    "tofu_feta", "cashew_cheese",
    # Farines et dérivés végans à base de noix — exclus de NUT_IDS pour éviter
    # les faux positifs sur le filtre nut_free dans les recettes veganes.
    "almond_flour", "farine_amande",
    "almond_butter",                # beurre d'amande : substitut vegan courant
    "cashew_milk", "lait_cajou",    # laits végans à base de noix
})

GLUTEN_IDS: frozenset[str] = frozenset({
    "flour", "whole_wheat_flour", "spelt_flour", "rye_flour", "farine",
    "farine_de_seigle", "semolina", "semoule", "couscous_semolina",
    "bread", "baguette", "stale_bread", "pita_bread", "pain",
    "pasta", "spaghetti", "penne", "fusilli", "tagliatelle",
    "linguine", "orzo", "ziti", "spaetzle", "ramen", "ramen_noodles",
    "udon", "soba", "couscous",
    "wheat", "ble", "rye", "barley", "orge", "bulgur", "fine_bulgur",
    "breadcrumbs", "crackers", "chapelure", "croutons",
    "soy_sauce", "sauce_soja", "tamari",        # tamari peut contenir du gluten
    "miso", "white_miso", "red_miso", "miso_paste",
    "seitan",
    "wonton_wrapper", "gyoza_wrappers", "phyllo_dough",
    "puff_pastry", "shortcrust_pastry", "pizza_dough",
    "tortillas", "beer", "biere",
})

LACTOSE_IDS: frozenset[str] = frozenset({
    "milk", "lait", "cream", "creme", "creme_fraiche",
    "butter", "beurre",
    "yogurt", "greek_yogurt", "plain_yogurt", "yaourt",
    "cheese", "fromage", "fromage_blanc", "fromage_en_grain", "fresh_cheese",
    "feta", "mozzarella", "parmesan", "cheddar", "ricotta",
    "halloumi", "paneer", "cheese_curds", "feta_fromage_blanc",
    "salted_ricotta", "gruyere_cheese", "manchego", "queijo",
    # "ghee" et "kashk" déplacés dans LACTOSE_TRACE_IDS :
    # - ghee : beurre clarifié, lactose < 0.1g/100g, toléré par la majorité
    # - kashk : laitage fermenté, teneur résiduelle variable
    # Ces ingrédients n'invalident pas lactose_free=True mais déclenchent
    # un avertissement via diet_flags["lactose_trace_note"].
})

# Ingrédients lactés avec teneur résiduelle en lactose — tolérés par la plupart
# des intolérants mais signalés à l'utilisateur via diet_notes.
LACTOSE_TRACE_IDS: frozenset[str] = frozenset({
    "ghee",     # beurre clarifié — < 0.1g lactose/100g, toléré par la majorité
    "kashk",    # laitage fermenté — teneur variable selon le processus
})

NUT_IDS: frozenset[str] = frozenset({
    "almond", "walnut", "cashew", "hazelnut", "pecan", "pine_nut",
    "macadamia", "pistachio", "brazil_nut", "chestnut",
    "peanut", "peanut_butter", "peanut_sauce",
    # "almond_flour" et "almond_milk" retirés — substituts végans courants.
    # Une recette vegan utilisant du lait d'amande était incorrectement taguée
    # nut_free=False, excluant une grande partie du catalogue vegan du filtre.
    # Ces clés sont dans VEGAN_EXCEPTIONS pour être exclues de _extract_ids().
    "noix_de_cajou", "pate_d_arachide",
})

# ── FODMAP — données basées sur Monash University FODMAP Diet App ────────────
#
# Architecture en deux couches :
#
#  1. FODMAP_THRESHOLDS  (dict)
#     Table de seuils quantitatifs par ingrédient (g par portion).
#     Structure par entrée :
#       "ingredient_base": {
#           "safe":   X,    # <= X g/portion → contribue 0 (low)
#           "medium": Y,    # <= Y g/portion → contribue 1 pt (medium)
#                           # >  Y g/portion → contribue 2 pts (high)
#           "cats":  [...], # catégories FODMAP : F/G/M/P
#           "note":  "...", # optionnel — contexte Monash
#       }
#     safe=0 signifie "aucune dose sûre" (ex : ail → high dès 1g).
#     medium=999 signifie "jamais high même en grande quantité" (ex : avoccat ≤60g).
#
#  2. Fallback par liste (HIGH/MEDIUM_FODMAP_IDS)
#     Pour les ingrédients sans seuil quantitatif — scoring binaire conservateur.
#
# Note : le lactose (D) est géré séparément par LACTOSE_IDS pour le flag
# lactose_free — il n'est pas répété ici pour éviter la double comptabilisation.
# Les ingrédients de VEGAN_EXCEPTIONS sont exclus de _extract_ids() et donc
# ne déclenchent jamais les FODMAP (laits végétaux, fromages végans, etc.).
#
# Sources : Monash University FODMAP Diet App v3, King's College London
#           (Barrett & Gibson 2012, 2019 updates)

# ── Fructanes (F) ─────────────────────────────────────────────────────────────
_FRUCTAN_HIGH: frozenset[str] = frozenset({
    # Alliacées
    "onion", "red_onion", "white_onion", "yellow_onion", "brown_onion",
    "shallot", "echalote", "leek", "poireau",
    "garlic", "ail", "garlic_powder", "garlic_granules", "onion_powder",
    # Céréales à gluten (fructanes + gluten)
    "wheat", "ble", "rye", "barley", "orge",
    "flour", "whole_wheat_flour", "spelt_flour", "rye_flour", "farine",
    "bread", "baguette", "pain", "breadcrumbs", "crackers", "chapelure",
    "pasta", "spaghetti", "penne", "fusilli", "tagliatelle", "linguine",
    "orzo", "ziti", "couscous", "bulgur", "fine_bulgur", "semolina", "semoule",
    "tortillas", "pita_bread", "naan", "wonton_wrapper", "gyoza_wrappers",
    "phyllo_dough", "puff_pastry", "pizza_dough", "shortcrust_pastry",
    "seitan",  # pur gluten de blé
    # Légumes à fructanes élevés
    "artichoke", "artichaut", "jerusalem_artichoke", "topinambour",
    "fennel", "fenouil",
    "beetroot", "betterave",  # modéré mais listé ici car souvent en grande qt
    # Fruits à fructanes
    "persimmon", "kaki", "grapefruit",  # pamplemousse — fructanes + fructose
    "pomelo",
    # Légumineuses à fructanes (en plus des GOS)
    "green_peas", "petits_pois", "split_peas", "pois_casses",
    # Tisanes / arômes
    "chamomile", "camomille",  # fructanes en infusion concentrée
    "dandelion_root",
})

# ── GOS — Galacto-oligosaccharides (G) ────────────────────────────────────────
_GOS_HIGH: frozenset[str] = frozenset({
    "lentil", "lentille", "lentilles", "red_lentil", "lentille_corail",
    "chickpea", "pois_chiche", "hummus",
    "bean", "haricot", "black_bean", "haricot_noir",
    "red_kidney_bean", "white_bean", "haricot_blanc", "haricot_rouge",
    "cannellini_bean", "borlotti_bean", "pinto_bean",
    "fava_bean", "broad_bean", "feve",
    "soybean", "edamame",
    "lupin", "lupin_flour",
    # Noix à GOS élevés
    "cashew", "noix_de_cajou",  # aussi dans NUT_IDS
    "pistachio", "pistache",    # aussi dans NUT_IDS
})

# ── Fructose en excès (M) ─────────────────────────────────────────────────────
_FRUCTOSE_HIGH: frozenset[str] = frozenset({
    "apple", "pomme",
    "pear", "poire",
    "mango", "mangue",
    "cherry", "cerise",
    "watermelon", "pasteque",
    "fig", "figue",
    "lychee", "litchi",
    "quince", "coing",
    "boysenberry", "tamarillo",
    # Édulcorants / sucrants
    "honey", "miel",
    "agave", "agave_syrup", "sirop_agave",
    "high_fructose_corn_syrup", "corn_syrup",
    "apple_juice", "jus_de_pomme", "pear_juice", "jus_de_poire",
    "concentrated_fruit_juice",
    # Sauces industrielles (souvent enrichies en HFCS)
    "ketchup",  # industriel — vérifier étiquette
    "teriyaki_sauce",
    "sweet_chili_sauce",
    "hoisin_sauce",
    "plum_sauce",
})

# ── Polyols (P) ───────────────────────────────────────────────────────────────
_POLYOL_HIGH: frozenset[str] = frozenset({
    # Fruits à polyols (sorbitol/mannitol)
    "apricot", "abricot",
    "peach", "peche",
    "plum", "prune", "prune_juice",
    "nectarine",
    "blackberry", "mure",
    "cherry", "cerise",      # aussi en fructose
    "avocado", "avocat",     # sorbitol (toléré en petite qt → medium)
    # Légumes à mannitol
    "mushroom", "champignon", "shiitake", "oyster_mushroom",
    "cauliflower", "chou_fleur",
    "celery", "celeri",
    "sweet_potato",  # mannitol en grande quantité
    # Édulcorants artificiels (polyols ajoutés)
    "sorbitol", "e420",
    "mannitol", "e421",
    "xylitol", "e967",
    "maltitol", "e965",
    "lactitol", "e966",
    "erythritol",  # mieux toléré mais listé pour précaution
    "isomalt",
})

# ── Liste synthétique HIGH FODMAP (union) ─────────────────────────────────────
HIGH_FODMAP_IDS: frozenset[str] = (
    _FRUCTAN_HIGH | _GOS_HIGH | _FRUCTOSE_HIGH | _POLYOL_HIGH
)

# ── Déclencheurs modérés — tolérés en petite portion ─────────────────────────
# Source : Monash FODMAP App — portions "green" vs "orange/red"
MEDIUM_FODMAP_IDS: frozenset[str] = frozenset({
    # Fructanes modérés
    "spring_onion",     # partie verte OK, bulbe = high
    "oignon_vert",
    "cabbage", "chou",  # fructanes modérés
    "broccoli", "brocoli",   # GOS + fructanes à haute dose (80g+ = high)
    "brussel_sprout", "chou_de_bruxelles",
    "asparagus", "asperge",  # fructanes + fructose
    # GOS modérés (portion < 3 cs)
    "tofu_soft", "tofu_soyeux",  # GOS résiduel (tofu ferme = low)
    # Fructose modéré
    "grape", "raisin",       # fructose proche équilibre
    "blueberry", "myrtille", # fructose + sorbitol (portion 20g = OK)
    "pomegranate", "grenade",
    "raspberry", "framboise",
    "passion_fruit", "fruit_de_la_passion",
    "coconut_water", "eau_de_coco",  # oligosaccharides en grande qt
    # Polyols modérés
    "avocado", "avocat",  # 30g OK selon Monash
    "pumpkin", "courge",  # mannitol modéré
    "turnip", "navet",
    # Lactose — fromages frais (low si affiné, medium si frais)
    "ricotta",
    "mascarpone",
    "creme_fraiche", "cream",
    # Divers
    "soy_sauce", "sauce_soja",  # fructanes — 2 cs max
    "miso", "white_miso", "red_miso",  # fructanes (1 cs = OK)
    "tahini",   # GOS modéré
    "cashew_butter",
})

# ── Mapping ingredient → catégorie(s) FODMAP ─────────────────────────────────
# Utilisé pour enrichir health_scores avec fodmap_categories
FODMAP_CATEGORY_MAP: dict[str, list[str]] = {
    # Fructanes
    "onion": ["F"], "garlic": ["F"], "shallot": ["F"], "leek": ["F"],
    "wheat": ["F"], "bread": ["F"], "pasta": ["F"], "flour": ["F"],
    "artichoke": ["F"], "fennel": ["F"], "green_peas": ["F"],
    # GOS
    "lentil": ["G"], "chickpea": ["G"], "bean": ["G"], "soybean": ["G"],
    "edamame": ["G"], "cashew": ["G", "P"], "pistachio": ["G"],
    # Fructose
    "apple": ["M"], "pear": ["M"], "mango": ["M"], "honey": ["M"],
    "agave": ["M"], "watermelon": ["M"], "cherry": ["M", "P"],
    # Polyols
    "mushroom": ["P"], "cauliflower": ["P"], "apricot": ["P"],
    "peach": ["P"], "plum": ["P"], "avocado": ["P"],
    "xylitol": ["P"], "sorbitol": ["P"], "mannitol": ["P"],
}

# ── Seuils quantitatifs Monash (g/portion) ───────────────────────────────────
# "safe"  : <= g → low (0 pt).  safe=0 → aucune dose sûre.
# "medium": <= g → medium (1 pt).  medium=999 → jamais high.
# Valeurs issues de Monash FODMAP App v3 (2019-2023 updates).
FODMAP_THRESHOLDS: dict[str, dict] = {
    # ── Alliacées (fructanes) — aucune dose sûre
    "garlic":          {"safe": 0,   "medium": 0,   "cats": ["F"]},
    "ail":             {"safe": 0,   "medium": 0,   "cats": ["F"]},
    "garlic_powder":   {"safe": 0,   "medium": 0,   "cats": ["F"]},
    "onion":           {"safe": 0,   "medium": 15,  "cats": ["F"]},
    "red_onion":       {"safe": 0,   "medium": 15,  "cats": ["F"]},
    "white_onion":     {"safe": 0,   "medium": 15,  "cats": ["F"]},
    "yellow_onion":    {"safe": 0,   "medium": 15,  "cats": ["F"]},
    "shallot":         {"safe": 0,   "medium": 15,  "cats": ["F"]},
    "echalote":        {"safe": 0,   "medium": 15,  "cats": ["F"]},
    "leek":            {"safe": 0,   "medium": 25,  "cats": ["F"]},
    "poireau":         {"safe": 0,   "medium": 25,  "cats": ["F"]},
    "spring_onion":    {"safe": 16,  "medium": 40,  "cats": ["F"],
                        "note": "partie verte only — bulbe = high dès 1g"},
    "oignon_vert":     {"safe": 16,  "medium": 40,  "cats": ["F"]},
    # ── Céréales à gluten (fructanes)
    "wheat":           {"safe": 0,   "medium": 26,  "cats": ["F"]},
    "flour":           {"safe": 0,   "medium": 30,  "cats": ["F"]},
    "farine":          {"safe": 0,   "medium": 30,  "cats": ["F"]},
    "bread":           {"safe": 0,   "medium": 30,  "cats": ["F"]},
    "pain":            {"safe": 0,   "medium": 30,  "cats": ["F"]},
    "pasta":           {"safe": 0,   "medium": 74,  "cats": ["F"],
                        "note": "74g cuit = 1 portion Monash orange"},
    "couscous":        {"safe": 0,   "medium": 45,  "cats": ["F"]},
    "bulgur":          {"safe": 0,   "medium": 45,  "cats": ["F"]},
    # ── Légumes (fructanes / polyols)
    "artichoke":       {"safe": 0,   "medium": 0,   "cats": ["F"]},
    "artichaut":       {"safe": 0,   "medium": 0,   "cats": ["F"]},
    "fennel":          {"safe": 47,  "medium": 80,  "cats": ["F"]},
    "fenouil":         {"safe": 47,  "medium": 80,  "cats": ["F"]},
    "beetroot":        {"safe": 20,  "medium": 45,  "cats": ["F"]},
    "betterave":       {"safe": 20,  "medium": 45,  "cats": ["F"]},
    "asparagus":       {"safe": 0,   "medium": 30,  "cats": ["F"]},
    "asperge":         {"safe": 0,   "medium": 30,  "cats": ["F"]},
    "broccoli":        {"safe": 75,  "medium": 130, "cats": ["F", "G"]},
    "brocoli":         {"safe": 75,  "medium": 130, "cats": ["F", "G"]},
    "cauliflower":     {"safe": 0,   "medium": 35,  "cats": ["P"]},
    "chou_fleur":      {"safe": 0,   "medium": 35,  "cats": ["P"]},
    "celery":          {"safe": 10,  "medium": 30,  "cats": ["P"]},
    "celeri":          {"safe": 10,  "medium": 30,  "cats": ["P"]},
    "cabbage":         {"safe": 75,  "medium": 135, "cats": ["F"]},
    "chou":            {"safe": 75,  "medium": 135, "cats": ["F"]},
    "brussel_sprout":  {"safe": 0,   "medium": 38,  "cats": ["F"]},
    "sweet_potato":    {"safe": 70,  "medium": 150, "cats": ["P"]},
    "pumpkin":         {"safe": 30,  "medium": 75,  "cats": ["P"]},
    "courge":          {"safe": 30,  "medium": 75,  "cats": ["P"]},
    "turnip":          {"safe": 45,  "medium": 90,  "cats": ["P"]},
    "navet":           {"safe": 45,  "medium": 90,  "cats": ["P"]},
    "green_peas":      {"safe": 0,   "medium": 30,  "cats": ["F", "G"]},
    "petits_pois":     {"safe": 0,   "medium": 30,  "cats": ["F", "G"]},
    # ── Champignons (polyols — mannitol)
    "mushroom":        {"safe": 0,   "medium": 35,  "cats": ["P"]},
    "champignon":      {"safe": 0,   "medium": 35,  "cats": ["P"]},
    "shiitake":        {"safe": 0,   "medium": 35,  "cats": ["P"]},
    "oyster_mushroom": {"safe": 0,   "medium": 35,  "cats": ["P"]},
    # ── Légumineuses (GOS)
    "lentil":          {"safe": 46,  "medium": 100, "cats": ["G"],
                        "note": "46g cuit = 1/4 cup Monash vert"},
    "lentille":        {"safe": 46,  "medium": 100, "cats": ["G"]},
    "red_lentil":      {"safe": 46,  "medium": 100, "cats": ["G"]},
    "lentille_corail": {"safe": 46,  "medium": 100, "cats": ["G"]},
    "chickpea":        {"safe": 42,  "medium": 80,  "cats": ["G"],
                        "note": "rincées en conserve : seuil ×1.5"},
    "pois_chiche":     {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "hummus":          {"safe": 0,   "medium": 45,  "cats": ["G"]},
    "black_bean":      {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "haricot_noir":    {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "white_bean":      {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "haricot_blanc":   {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "cannellini_bean": {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "fava_bean":       {"safe": 0,   "medium": 30,  "cats": ["G"]},
    "feve":            {"safe": 0,   "medium": 30,  "cats": ["G"]},
    "edamame":         {"safe": 90,  "medium": 160, "cats": ["G"]},
    "cashew":          {"safe": 0,   "medium": 10,  "cats": ["G"],
                        "note": "10g ≈ 10 cajous — très concentré"},
    "noix_de_cajou":   {"safe": 0,   "medium": 10,  "cats": ["G"]},
    "pistachio":       {"safe": 0,   "medium": 10,  "cats": ["G"]},
    "pistache":        {"safe": 0,   "medium": 10,  "cats": ["G"]},
    # ── Fruits (fructose / polyols)
    "apple":           {"safe": 0,   "medium": 30,  "cats": ["M"]},
    "pomme":           {"safe": 0,   "medium": 30,  "cats": ["M"]},
    "pear":            {"safe": 0,   "medium": 0,   "cats": ["M"]},
    "poire":           {"safe": 0,   "medium": 0,   "cats": ["M"]},
    "mango":           {"safe": 0,   "medium": 40,  "cats": ["M"]},
    "mangue":          {"safe": 0,   "medium": 40,  "cats": ["M"]},
    "cherry":          {"safe": 0,   "medium": 0,   "cats": ["M", "P"]},
    "cerise":          {"safe": 0,   "medium": 0,   "cats": ["M", "P"]},
    "watermelon":      {"safe": 0,   "medium": 0,   "cats": ["M", "P"]},
    "pasteque":        {"safe": 0,   "medium": 0,   "cats": ["M", "P"]},
    "apricot":         {"safe": 0,   "medium": 20,  "cats": ["P"]},
    "abricot":         {"safe": 0,   "medium": 20,  "cats": ["P"]},
    "peach":           {"safe": 0,   "medium": 30,  "cats": ["P"]},
    "peche":           {"safe": 0,   "medium": 30,  "cats": ["P"]},
    "plum":            {"safe": 0,   "medium": 0,   "cats": ["P"]},
    "nectarine":       {"safe": 0,   "medium": 35,  "cats": ["P"]},
    "blackberry":      {"safe": 0,   "medium": 30,  "cats": ["P"]},
    "mure":            {"safe": 0,   "medium": 30,  "cats": ["P"]},
    "avocado":         {"safe": 30,  "medium": 60,  "cats": ["P"]},
    "avocat":          {"safe": 30,  "medium": 60,  "cats": ["P"]},
    "grape":           {"safe": 90,  "medium": 999, "cats": ["M"]},
    "raisin":          {"safe": 90,  "medium": 999, "cats": ["M"]},
    "blueberry":       {"safe": 20,  "medium": 40,  "cats": ["M", "P"]},
    "myrtille":        {"safe": 20,  "medium": 40,  "cats": ["M", "P"]},
    "raspberry":       {"safe": 60,  "medium": 999, "cats": ["M"]},
    "framboise":       {"safe": 60,  "medium": 999, "cats": ["M"]},
    "fig":             {"safe": 0,   "medium": 0,   "cats": ["M"]},
    "figue":           {"safe": 0,   "medium": 0,   "cats": ["M"]},
    # ── Banane (fructose + sorbitol — banane mûre)
    "banana":          {"safe": 0,   "medium": 35,  "cats": ["M", "P"]},
    # ── Farines de blé (fructanes — toutes variantes)
    "all_purpose_flour": {"safe": 0, "medium": 26,  "cats": ["F"]},
    "wheat_flour":     {"safe": 0,   "medium": 26,  "cats": ["F"]},
    "white_flour":     {"safe": 0,   "medium": 26,  "cats": ["F"]},
    "bread_flour":     {"safe": 0,   "medium": 26,  "cats": ["F"]},
    "whole_wheat_flour":{"safe": 0,  "medium": 26,  "cats": ["F"]},
    "t45":             {"safe": 0,   "medium": 26,  "cats": ["F"]},
    "t55":             {"safe": 0,   "medium": 26,  "cats": ["F"]},
    "t65":             {"safe": 0,   "medium": 26,  "cats": ["F"]},
    "t80":             {"safe": 0,   "medium": 26,  "cats": ["F"]},
    # ── Légumineuses vertes (GOS — variantes de lentilles)
    "green_lentils":   {"safe": 46,  "medium": 100, "cats": ["G"]},
    "red_lentils":     {"safe": 46,  "medium": 100, "cats": ["G"]},
    "black_lentils":   {"safe": 46,  "medium": 100, "cats": ["G"]},
    "puy_lentils":     {"safe": 46,  "medium": 100, "cats": ["G"]},
    "black_beans":     {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "kidney_beans":    {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "navy_beans":      {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "white_beans":     {"safe": 42,  "medium": 80,  "cats": ["G"]},
    "cannellini_beans":{"safe": 42,  "medium": 80,  "cats": ["G"]},
    # ── Flocons d'avoine
    "rolled_oats":     {"safe": 52,  "medium": 999, "cats": ["F"]},
    "oats":            {"safe": 52,  "medium": 999, "cats": ["F"]},
    "oat_flour":       {"safe": 52,  "medium": 999, "cats": ["F"]},
    # ── Sucre de coco (fructose modéré)
    "coconut_sugar":   {"safe": 7,   "medium": 20,  "cats": ["M"]},
    # ── Édulcorants / sucrants
    "honey":           {"safe": 0,   "medium": 7,   "cats": ["M"]},
    "miel":            {"safe": 0,   "medium": 7,   "cats": ["M"]},
    "agave":           {"safe": 0,   "medium": 0,   "cats": ["M"]},
    "agave_syrup":     {"safe": 0,   "medium": 0,   "cats": ["M"]},
    # ── Sauces / condiments
    "soy_sauce":       {"safe": 14,  "medium": 42,  "cats": ["F"]},
    "sauce_soja":      {"safe": 14,  "medium": 42,  "cats": ["F"]},
    "miso":            {"safe": 12,  "medium": 35,  "cats": ["F"]},
    "tahini":          {"safe": 20,  "medium": 45,  "cats": ["G"]},
    "ketchup":         {"safe": 0,   "medium": 13,  "cats": ["M"]},
}

# ── Identifiants CIQUAL des recettes → clés FODMAP ci-dessus ─────────────────
# Les tables ci-dessus utilisent les noms courts d'avant la migration CIQUAL
# ('garlic') ; les recettes utilisent 'garlic_raw' : sans cette table, 634 des
# 643 recettes à l'ail ou à l'oignon ressortaient « low FODMAP ».
# Table explicite et relue : ingredient_price_map (prix) range sous 'flour'
# la fécule de maïs ou la farine de sarrasin (low FODMAP) et sous 'cream' les
# crèmes végétales — inutilisable ici. Un id absent = pas de déclencheur connu
# (ail des ours, ciboulette, riz, maïs, sarrasin, tofu ferme… sont low).
# Les sous-recettes (base_*) ne sont pas listées : leur composition est
# dépliée au prorata (_fodmap_quantities).
FODMAP_ID_ALIASES: dict[str, str] = {
    # Alliacées
    "garlic_raw": "garlic",
    "onion_raw": "onion", "yellow_onion_raw": "onion", "white_onion_raw": "onion",
    "sweet_onion_raw": "onion", "red_onion_raw": "red_onion",
    "shallot_raw": "shallot",
    "leeks": "leek", "leeks_raw": "leek",
    "green_onion_raw": "spring_onion",
    # Bouillon déshydraté : contient presque toujours oignon et ail
    "vegetable_stock_dried": "onion_powder",
    # Blé, seigle, orge (fructanes)
    "wheat_all_purpose_flour_unenriched_unbleached": "wheat_flour",
    "wheat_flour": "wheat_flour", "wheat_flour_t55": "wheat_flour",
    "bread_flour_blanched": "wheat_flour", "whole_wheat_flour_seed": "wheat_flour",
    "tempura_flour": "wheat_flour",
    "freekeh_immature_wheat_raw_cracked_seed": "wheat",
    "vital_wheat_gluten_flour": "seitan",
    "durum_wheat_semolina": "semolina", "wheat_semolina_raw": "semolina",
    "couscous_to_cook_seed_dried": "couscous",
    "bulgur_raw_dried": "bulgur",
    "pasta_raw_dried": "pasta", "whole_wheat_pasta_raw_dried": "pasta",
    "egg_pasta_raw_dried": "pasta", "udon": "pasta",
    "bread_white_commercial": "bread", "white_bread_baguette": "bread",
    "white_bread_roasted": "bread", "white_bread_unsalted": "bread",
    "wholemeal_bread_whole": "bread", "rye_bread": "bread", "toast": "bread",
    "multigrain_toast_bread_roasted_sliced_pre_packaged": "bread",
    "bagel": "bread", "hot_dog_bun_pre_packaged": "bread",
    "indian_bread_naan": "bread", "white_pita_bread": "bread", "pain_pita": "bread",
    "croutons_dried_plain_pre_packaged": "bread", "ladyfinger": "bread",
    # sourdough_bread volontairement absent : levain long = low (Monash, 2 tranches)
    "breadcrumbs": "breadcrumbs", "breadcrumbs_dried": "breadcrumbs",
    "phyllo_filo_pastry_raw_paste": "phyllo_dough",
    "puff_pastry_all_butter_raw_paste_pre_packaged": "puff_pastry",
    "puff_pastry_vegetable_fat_raw_paste_plant": "puff_pastry",
    "shortcrust_pastry_all_butter_raw_paste_pre_packaged": "shortcrust_pastry",
    "rye_flour": "rye_flour",
    "barley_raw_whole_seed": "barley", "pearl_barley_raw_seed": "barley",
    "oat_flakes_whole_seed": "oats",
    # Légumineuses (GOS)
    "chickpea_boiled": "chickpea", "chickpea_raw_dried": "chickpea",
    "chickpea_rinsed_canned": "chickpea", "roasted_chickpea": "chickpea",
    "chickpea_flour": "chickpea", "chana_dal": "chickpea", "falafel": "chickpea",
    "red_lentil_dried": "red_lentil",
    "green_lentil_boiled": "lentil", "green_lentil_dried": "lentil", "urad_lentil": "lentil",
    "black_bean_boiled": "black_bean",
    "kidney_bean_boiled": "kidney_beans", "kidney_bean_dried": "kidney_beans",
    "white_bean_boiled": "white_bean", "white_bean_canned": "white_bean",
    "white_bean_dried_canned": "white_bean", "white_bean_raw": "white_bean",
    "gigante_bean": "white_bean", "flageolet_bean_canned": "white_bean",
    "lima_bean_boiled_canned": "white_bean",
    "pinto_bean_boiled": "pinto_bean",
    "black_eyed_peas_cowpeas_boiled": "bean", "black_eyed_peas_cowpeas_dried": "bean",
    "mung_bean_dried": "bean", "pigeon_peas_red_gram_raw": "bean",
    "red_bean_paste": "bean",
    "fava_bean_dried": "fava_bean", "broadbeans_fava_beans_boiled_fresh": "fava_bean",
    "broadbeans_fava_beans_raw_dried": "fava_bean",
    "broadbeans_fava_beans_raw_fresh": "fava_bean",
    "split_peas_dried": "split_peas",
    "green_peas_raw": "green_peas", "green_peas_boiled_frozen_salted": "green_peas",
    "snow_peas_raw": "green_peas",
    "soybean_boiled_dried": "soybean", "soybean_raw_dried": "soybean",
    "soybean_flour_raw_whole": "soybean",
    "edamame_raw": "edamame",
    "silken_tofu_pre_packaged": "tofu_soft",
    # Fruits à coque riches en GOS
    "cashew_nuts_raw": "cashew", "cashew_nuts_grilled_unsalted": "cashew",
    "cashew_butter_plain_plant": "cashew_butter",
    "pistachio_nuts_raw": "pistachio",
    # Fruits (fructose / polyols)
    "apple_raw": "apple", "apple_raw_with_skin": "apple",
    "golden_apple_raw_with_skin": "apple", "chantecler_apple_raw_skinless": "apple",
    "apple_puree_pre_packaged": "apple", "apple_juice_plain": "apple_juice",
    "pear_raw_with_skin": "pear",
    "mango": "mango", "mango_raw": "mango",
    "cherry_raw_with_skin": "cherry", "sour_cherry_raw": "cherry",
    "sour_cherry_canned_in_water": "cherry", "cherry_jam": "cherry",
    "watermelon_raw": "watermelon",
    "fig_raw": "fig",
    "apricot_pitted_dried": "apricot",
    "prune_raw_pitted_dried": "plum",
    "avocado_raw": "avocado",
    "banana_raw": "banana",
    "blueberry": "blueberry", "blueberry_raw": "blueberry", "bilberry_raw": "blueberry",
    "raspberry_raw": "raspberry",
    "green_grape_raw": "grape", "chasselas_grape_raw": "grape",
    "pomegranate_raw": "pomegranate", "pomegranate_juice_plain": "pomegranate",
    "passion_fruit_raw": "passion_fruit",
    "grapefruit_raw": "grapefruit",
    # Sucrants
    "honey": "honey", "agave_syrup": "agave_syrup", "coconut_sugar": "coconut_sugar",
    # Légumes
    "button_mushroom_raw": "mushroom", "porcini_mushroom_raw": "mushroom",
    "chanterelle_mushroom_raw": "mushroom",
    "oyster_mushroom_raw": "oyster_mushroom",
    "shiitake_mushroom_raw": "shiitake", "shiitake_mushroom_dried": "shiitake",
    "cauliflower_raw_flower": "cauliflower",
    "celery_stalk_raw": "celery",
    "sweet_potato_raw": "sweet_potato", "sweet_potato_flour": "sweet_potato",
    "pumpkin_raw": "pumpkin",
    "butternut_squash_raw": "pumpkin", "butternut_squash_raw_skinless": "pumpkin",
    "cabbage_raw": "cabbage", "green_cabbage_raw": "cabbage",
    "white_cabbage_raw": "cabbage", "red_cabbage_raw": "cabbage",
    "savoy_cabbage_raw": "cabbage",
    "sauerkraut": "cabbage", "sauerkraut_canned_low_sodium": "cabbage",
    "broccoli_raw": "broccoli", "chinese_broccoli_cooked": "broccoli",
    "asparagus_raw": "asparagus", "green_asparagus_raw": "asparagus",
    "white_asparagus_raw_peeled": "asparagus",
    "fennel_raw": "fennel",
    "beetroot_raw_root": "beetroot", "beetroot_cooked_root": "beetroot",
    "turnip_raw": "turnip",
    "jerusalem_artichoke_raw": "jerusalem_artichoke",
    # Laitiers frais (déclencheurs modérés de MEDIUM_FODMAP_IDS)
    "ricotta": "ricotta", "ricotta_whole_cow": "ricotta",
    "mascarpone": "mascarpone",
    "cream": "cream", "cream_heavy": "cream", "cream_heavy_refrigerated_18pct": "cream",
    "cream_heavy_refrigerated_30pct": "cream", "cream_liquid_uht": "cream",
    "cream_sour_18pct": "cream", "cream_sour_fermented": "cream",
    "sour_cream_fermented_18pct": "cream",
    # Sauces et pâtes
    "soy_sauce_shoyu_reduced_sodium": "soy_sauce", "soy_sauce_tamari": "soy_sauce",
    "miso_fermented": "miso",
    "sesame_tahini_raw_butter_seed_plant": "tahini",
    "tomato_ketchup_catsup_pre_packaged_normal": "ketchup",
}

# ── Conversions poids pièce → grammes ─────────────────────────────────────────
# Pour les ingrédients dont l'unité est "piece" ou "pcs" dans composition
_PIECE_WEIGHT_G: dict[str, float] = {
    "garlic": 3.0,        # 1 gousse ≈ 3g
    "ail": 3.0,
    "onion": 110.0,       # 1 oignon moyen
    "red_onion": 100.0,
    "white_onion": 110.0,
    "yellow_onion": 110.0,
    "shallot": 30.0,      # 1 échalote
    "echalote": 30.0,
    "leek": 100.0,        # 1 blanc de poireau
    "poireau": 100.0,
    "mushroom": 15.0,     # 1 champignon de Paris
    "champignon": 15.0,
    "shiitake": 15.0,
    "apple": 150.0,       # 1 pomme moyenne
    "pomme": 150.0,
    "pear": 160.0,
    "poire": 160.0,
    "avocado": 150.0,     # 1 avocat entier (sans noyau ≈ 120g)
    "avocat": 150.0,
    "apricot": 40.0,
    "abricot": 40.0,
    "peach": 130.0,
    "peche": 130.0,
    "plum": 65.0,
    "nectarine": 130.0,
    "mango": 200.0,
    "mangue": 200.0,
    "fig": 50.0,
    "figue": 50.0,
    "cherry": 8.0,        # 1 cerise
    "cerise": 8.0,
    "lemon": 60.0,        # 1 citron (jus)
    "citron": 60.0,
    "egg": 55.0,
    "oeuf": 55.0,
    "artichoke": 120.0,
    "artichaut": 120.0,
    "beetroot": 80.0,     # 1 betterave
    "betterave": 80.0,
    "brussel_sprout": 18.0,
}


def _item_grams(item: dict, base: str) -> float | None:
    """Quantité d'un item de composition en grammes (recette entière), ou None
    si elle est inconnue : quantité absente ou unité libre (« 1 poignée »,
    « 2-3 toasts »). `base` sert au poids d'une pièce (_PIECE_WEIGHT_G)."""
    raw_qty = item.get("quantity")
    if raw_qty is None:
        return None
    try:
        qty = float(raw_qty)
    except (TypeError, ValueError):
        return None
    unit = str(item.get("unit") or "g").lower().strip()

    if unit in ("g", "ml", ""):
        return qty
    if unit in ("piece", "pcs", "pièce", "pc", "unit"):
        return qty * _PIECE_WEIGHT_G.get(base, 50.0)
    if unit in ("tbsp", "cs", "cuillère à soupe", "tablespoon"):
        return qty * 15.0
    if unit in ("tsp", "cc", "cuillère à café", "teaspoon"):
        return qty * 5.0
    if unit in ("pinch", "pincée"):
        return qty * 0.5
    if unit in ("cup", "tasse"):
        return qty * 240.0
    if unit in ("kg", "l"):
        return qty * 1000.0
    return None


# ── Extraction des ids ingrédients ────────────────────────────────────────────

def _extract_ids(recipe: dict) -> set[str]:
    """Extrait et normalise tous les ids d'ingrédients d'une recette.

    Les ids sont comparés par égalité exacte de token contre les frozensets
    (NON_VEGETARIAN, GLUTEN_IDS…). Pour un matching par sous-chaîne sur du
    texte libre (descriptions USDA), utiliser USDA_NON_VEGETARIAN_CATEGORIES
    en priorité, puis un split par token avant comparaison.
    """
    ids = set()
    for i in recipe.get("ingredients", []):
        raw = (i.get("ingredient_id", "") if isinstance(i, dict) else str(i))
        ids.add(_normalize(raw))
    for c in recipe.get("composition", []):
        if isinstance(c, dict):
            raw = c.get("ingredient", "") or c.get("ingredient_id", "")
            if raw:
                ids.add(_normalize(str(raw)))
    ids -= {_normalize(e) for e in VEGAN_EXCEPTIONS}
    ids -= {""}
    return ids


# ── Verification via diet_profile du dico ──────────────────────────────────
#
# Le blocklist bare-word ci-dessus compare l'id COMPLET (ex: "milk_liquid_
# uht_3_5pct") a des tokens nus ("milk", "lait"...) - ne matche donc jamais
# les ids composes du dico actuel, meme corrects. ingredients_dictionary.json
# porte deja un diet_profile verifie par entree (vegan/vegetarian/gluten_free/
# lactose_free/nut_free) - on le consulte ici via le meme resolveur que la
# nutrition (IngredientRepository.get_by_name), en AND avec le blocklist :
# un flag ne peut etre invalide QUE si l'un des deux signaux dit False,
# jamais valide a tort par une divergence entre les deux (conservateur).

def _dict_diet_signals(recipe: dict) -> dict[str, bool]:
    """
    Retourne {flag: True/False} pour vegan/vegetarian/gluten_free/
    lactose_free/nut_free en agregeant le diet_profile du dico sur chaque
    item de composition resolu. Un flag reste True si aucun item resolu ne
    le contredit (items non-resolus par le dico = ignores, pas de signal).

    Un id de composition qui reference une AUTRE recette (sous-recette
    partagee, ex: base_paneer_04e1db, base_pesto_905db7, base_noodles_2d0ed7)
    ne resout jamais via IngredientRepository (ce n'est pas une entree du
    dico d'ingredients) et etait donc silencieusement ignore - une recette
    utilisant un paneer ou un pesto reel (laitier) via sa sous-recette
    pouvait ainsi ressortir vegan=True. On consulte alors les diet_flags
    deja calcules de cette sous-recette elle-meme, agreges avec la meme
    regle (un flag n'est invalide que par un signal positif de False).
    """
    from backend.db.culinary_repositories import IngredientRepository, _recipes_index
    repo = IngredientRepository()
    recipes_by_id = _recipes_index()
    flags = ("vegan", "vegetarian", "gluten_free", "lactose_free", "nut_free")
    signals = {f: True for f in flags}
    for c in recipe.get("composition", []) or []:
        if not isinstance(c, dict):
            continue
        cid = c.get("ingredient") or c.get("ingredient_id")
        if not cid:
            continue
        cid = str(cid)
        item = repo.get_by_name(cid)
        dp = item.get("diet_profile") if item else None
        if dp:
            for f in flags:
                if dp.get(f) is False:
                    signals[f] = False
            continue
        sub_recipe = recipes_by_id.get(cid)
        if sub_recipe:
            sub_flags = sub_recipe.get("diet_flags") or {}
            for f in flags:
                if sub_flags.get(f) is False:
                    signals[f] = False
    return signals


# ── Calcul diet_flags ─────────────────────────────────────────────────────────

def compute_diet_flags(recipe: dict) -> dict:
    """
    Calcule les 7 flags diététiques binaires d'une recette.

    Le flag `vegetarian` est False dès qu'un ingredient_id figure dans
    NON_VEGETARIAN. Pour le filtrage du dataset USDA (texte libre), utiliser
    USDA_NON_VEGETARIAN_CATEGORIES en premier rideau, puis un matching par
    token — voir USDA_NON_VEGETARIAN_CATEGORIES pour les catégories exclues
    et les notes sur "kidney" / "oyster" / "ant".

    Returns:
        {vegan, vegetarian, gluten_free, lactose_free, nut_free,
         raw, kid_friendly}
    """
    existing = recipe.get("diet_flags") or {}
    if isinstance(existing, dict) and existing.get("diet_flags_source") == "manual":
        return existing

    ids = _extract_ids(recipe)

    has_non_vegan        = any(i in NON_VEGAN for i in ids)
    has_non_vegetarian   = any(i in NON_VEGETARIAN for i in ids)
    is_vegan        = not has_non_vegan and not has_non_vegetarian
    is_vegetarian   = not has_non_vegetarian
    is_gluten_free  = not any(i in GLUTEN_IDS for i in ids)
    is_lactose_free = not any(i in LACTOSE_IDS for i in ids)
    is_nut_free     = not any(i in NUT_IDS for i in ids)

    # AND avec le diet_profile du dico (verifie, ne matche pas seulement les
    # ids en bare-word) - un flag ne peut etre invalide QUE par un signal
    # positif de "False" de l'un des deux cotes, jamais valide a tort en cas
    # de divergence.
    dict_signals = _dict_diet_signals(recipe)
    is_vegan        = is_vegan        and dict_signals["vegan"]
    is_vegetarian   = is_vegetarian   and dict_signals["vegetarian"]
    is_gluten_free  = is_gluten_free  and dict_signals["gluten_free"]
    is_lactose_free = is_lactose_free and dict_signals["lactose_free"]
    is_nut_free     = is_nut_free     and dict_signals["nut_free"]

    # Ingrédients à traces résiduelles : la recette reste lactose_free=True
    # mais on signale à l'utilisateur que des traces sont présentes.
    lactose_trace_ingredients = [i for i in ids if i in LACTOSE_TRACE_IDS]

    # NB : le champ top-level 'technique' n'existe pas dans le schéma recipes.json
    # (les techniques sont dans tags.technique) — corrigé ici, cette lecture
    # retournait toujours [] et is_raw était donc toujours False.
    techniques = [str(t).lower() for t in ((recipe.get("tags") or {}).get("technique") or [])]
    is_raw = any(t in ("raw", "cru", "marinade", "ceviche") for t in techniques)

    # Idem : 'prep_time_min' top-level n'existe pas non plus (→ timing.prep_active_min
    # + timing.prep_passive_min) — retournait toujours le défaut 999.
    timing = recipe.get("timing") or {}
    prep_time_min = (timing.get("prep_active_min") or 0) + (timing.get("prep_passive_min") or 0)

    strong_spices = {"chili", "piment", "harissa", "wasabi", "gochujang", "sriracha"}
    is_kid = (
        not any(i in strong_spices for i in ids) and
        len(ids) <= 8 and
        prep_time_min <= 30
    )

    flags: dict = {
        "vegan":         is_vegan,
        "vegetarian":    is_vegetarian,
        "gluten_free":   is_gluten_free,
        "lactose_free":  is_lactose_free,
        "nut_free":      is_nut_free,
        "raw":           is_raw,
        "kid_friendly":  is_kid,
    }
    # Si des ingrédients à traces résiduelles sont présents, on les signale
    # sans invalider le flag lactose_free. L'UI peut afficher un avertissement
    # du type "Contient du ghee (traces de lactose possibles)".
    if lactose_trace_ingredients:
        flags["lactose_trace_note"] = (
            f"Contient {', '.join(lactose_trace_ingredients)} — "
            "toléré par la plupart des intolérants au lactose, "
            "traces résiduelles possibles."
        )
    return flags


# ── FODMAP ────────────────────────────────────────────────────────────────────

_FODMAP_KEYS: frozenset[str] = frozenset(FODMAP_THRESHOLDS) | HIGH_FODMAP_IDS | MEDIUM_FODMAP_IDS
_FODMAP_CAT_SETS = (("F", _FRUCTAN_HIGH), ("G", _GOS_HIGH),
                    ("M", _FRUCTOSE_HIGH), ("P", _POLYOL_HIGH))
_FODMAP_CAT_LABELS = {"F": "fructanes", "G": "GOS", "D": "lactose",
                      "M": "fructose", "P": "polyols"}
_WHEAT_FODMAP_KEYS = frozenset({"wheat", "wheat_flour", "flour", "bread", "pasta",
                                "ble", "farine", "pain"})


def _fodmap_key(ingredient_id: str) -> str | None:
    """Clé des tables FODMAP pour un id de recette ('garlic_raw' → 'garlic'),
    ou None si l'ingrédient n'est pas un déclencheur connu."""
    iid = _normalize(str(ingredient_id).split("/")[0])
    if iid in FODMAP_ID_ALIASES:
        return FODMAP_ID_ALIASES[iid]
    return iid if iid in _FODMAP_KEYS else None


def _fodmap_quantities(recipe: dict, unknown: set[str], _depth: int = 0) -> dict[str, float]:
    """{clé FODMAP: g par portion} depuis composition[].

    Les clés dont la quantité est inconnue (voir _item_grams) sont ajoutées à
    `unknown` : compute_fodmap leur applique la règle de liste, plus prudente.
    Une sous-recette (id d'une autre recette, ex. base_pesto_905db7) est
    dépliée : chacun de ses ingrédients compte au prorata de la part utilisée
    (g utilisés / g totaux de la sous-recette).
    """
    servings = max(1, int(recipe.get("servings") or 1))
    result: dict[str, float] = defaultdict(float)
    sub_recipes = None
    for item in recipe.get("composition") or []:
        if not isinstance(item, dict):
            continue
        raw_id = str(item.get("ingredient", "") or item.get("ingredient_id", ""))
        if not raw_id:
            continue
        key = _fodmap_key(raw_id)
        if key is not None:
            grams = _item_grams(item, key)
            if grams is None:
                unknown.add(key)
            else:
                result[key] += grams / servings
            continue
        if _depth >= 3:
            continue
        if sub_recipes is None:
            from backend.core.data_io import load_recipes
            sub_recipes = {r.get("id"): r for r in load_recipes()}
        sub = sub_recipes.get(raw_id)
        if not sub:
            continue
        sub_total = sum(_item_grams(c, "") or 0 for c in sub.get("composition") or []
                        if isinstance(c, dict))
        used = _item_grams(item, "")
        sub_qty = _fodmap_quantities(sub, unknown, _depth + 1)
        if not used or sub_total <= 0:
            # Part utilisée inconnue : règle de liste pour ses déclencheurs
            unknown.update(sub_qty)
            continue
        share = used / sub_total
        sub_servings = max(1, int(sub.get("servings") or 1))
        for k, g in sub_qty.items():
            # g est par portion de la sous-recette → ramené au total, puis à la part utilisée
            result[k] += g * sub_servings * share / servings
    return dict(result)


def compute_fodmap(recipe: dict) -> dict:
    """Niveau FODMAP d'une recette : {fodmap_level, fodmap_score, fodmap_categories}.

    Score : clé à seuil quantitatif Monash → 0 / 1 / 2 pts selon g par portion ;
    sinon HIGH_FODMAP_IDS = 2 pts, MEDIUM_FODMAP_IDS = 1 pt. 0 → low, ≤ 2 → medium,
    au-delà → high. Source unique pour health_scores (ici et filter_service).
    """
    no_qty: set[str] = set()
    qty = _fodmap_quantities(recipe, no_qty)
    # Ancien format ingredients[] : ids sans quantité → règle de liste seule
    for i in recipe.get("ingredients") or []:
        raw = i.get("ingredient_id", "") if isinstance(i, dict) else str(i)
        key = _fodmap_key(raw) if raw else None
        if key:
            no_qty.add(key)
    no_qty -= set(qty)

    score = 0
    cats: set[str] = set()

    def _add_cats(key: str) -> None:
        thresh = FODMAP_THRESHOLDS.get(key)
        if thresh:
            cats.update(thresh["cats"])
        cats.update(FODMAP_CATEGORY_MAP.get(key, []))
        cats.update(c for c, s in _FODMAP_CAT_SETS if key in s)

    def _list_points(key: str) -> int:
        return 2 if key in HIGH_FODMAP_IDS else 1 if key in MEDIUM_FODMAP_IDS else 0

    for key, grams in qty.items():
        thresh = FODMAP_THRESHOLDS.get(key)
        if thresh is not None:
            pts = 2 if grams > thresh["medium"] else 1 if grams > thresh["safe"] else 0
        else:
            pts = _list_points(key)
        if pts:
            score += pts
            _add_cats(key)
    for key in no_qty:
        pts = _list_points(key)
        if pts:
            score += pts
            _add_cats(key)

    keys = set(qty) | no_qty
    from backend.core.data_io import recipe_techniques
    techniques = set(recipe_techniques(recipe))
    if techniques & {"sourdough", "levain", "long_fermentation"} and keys & _WHEAT_FODMAP_KEYS:
        score = max(0, score - 2)
    if techniques & {"canned", "rince", "rinced", "rinsed"} and keys & _GOS_HIGH:
        score = max(0, score - 1)

    return {
        "fodmap_level":      "low" if score == 0 else "medium" if score <= 2 else "high",
        "fodmap_score":      score,
        "fodmap_categories": sorted(_FODMAP_CAT_LABELS[c] for c in cats if c in _FODMAP_CAT_LABELS),
    }


# ── Calcul health_scores ──────────────────────────────────────────────────────

def compute_health_scores(recipe: dict) -> dict:
    """
    Calcule les scores de santé d'une recette depuis ses valeurs nutritionnelles
    pré-calculées (champ health_scores ou nutrition par portion recalculée).

    Seuils calés sur les distributions réelles du dataset (545 recettes) :
        kcal médiane=349  p25=264  p75=485
        protein p75=18.9g → seuil high_protein=20g
        fiber p75=9.4g → seuil high_fiber=8g
        sodium p50=98mg → seuil low_sodium=200mg
        glycemic_index p50=6.8 → low<8, medium<12, high≥12
        anti_inflammatory : proxy omega_3 (p25=0.3g, p75=1.0g)

    Si health_scores est déjà présent dans la recette, retourne tel quel.
    Pour recalculer, utiliser apply_all_scores(force=True).
    """
    existing = recipe.get("health_scores")
    if existing and isinstance(existing, dict):
        return existing

    # Nutrition par portion (peut être absente si non calculée)
    nutr = recipe.get("_nutrition_per_serving") or {}

    kcal      = float(nutr.get("calories", 0) or 0)
    prot      = float(nutr.get("protein", 0) or 0)
    fiber     = float(nutr.get("fiber", 0) or 0)
    sodium    = float(nutr.get("sodium", 0) or 0)
    sat_fat   = float(nutr.get("saturated_fat", 0) or 0)
    omega3    = float(nutr.get("omega3", nutr.get("omega_3", 0)) or 0)
    gi        = float(nutr.get("glycemic_index", 0) or 0)

    fodmap = compute_fodmap(recipe)

    return {
        "glycemic_category":      ("low" if gi < 8 else "medium" if gi < 12 else "high"),
        "high_protein":           prot >= 20,
        "protein_g":              round(prot, 1),
        "low_calorie":            kcal < 300,
        "kcal":                   round(kcal),
        "low_sodium":             sodium < 200,
        "sodium_mg":              round(sodium),
        "high_fiber":             fiber >= 8,
        "fiber_g":                round(fiber, 1),
        "low_sat_fat":            sat_fat < 5,
        "anti_inflammatory_score": (
            "high"   if omega3 >= 1.0 else
            "medium" if omega3 >= 0.3 else
            "low"
        ),
        **fodmap,   # fodmap_level, fodmap_score (brut, debug/tri), fodmap_categories
    }


# ── Calcul context_tags ───────────────────────────────────────────────────────

def compute_context_tags(recipe: dict) -> Optional[dict]:
    """
    Génère les tags contextuels optionnels (sport, meal_timing).
    Retourne None si aucun tag pertinent — évite les clés vides en base.

    Extensible : cycle_feminin, cultural, astrologie → à ajouter sur demande.
    """
    nutr  = recipe.get("_nutrition_per_serving") or {}
    kcal  = float(nutr.get("calories", 0) or 0)
    prot  = float(nutr.get("protein", 0) or 0)
    prep  = int(recipe.get("prep_time_min") or 99)
    cook  = int(recipe.get("cook_time_min") or 99)
    total = prep + cook

    sport = {}
    if prot >= 20:            sport["high_protein_sport"] = True
    if kcal < 300:            sport["low_calorie"] = True
    if kcal >= 400 and prot >= 15: sport["post_workout"] = True

    timing = {}
    if total <= 20: timing["quick"] = True
    elif total <= 30: timing["weeknight"] = True

    tags: dict = {}
    if sport:  tags["sport"] = sport
    if timing: tags["meal_timing"] = timing

    return tags if tags else None


# ── Application et batch ──────────────────────────────────────────────────────

def apply_all_scores(recipe: dict, force: bool = False) -> dict:
    """
    Applique les 3 colonnes JSONB à une recette (modification en place) :
        - diet_flags    → booléens (vegan, gluten_free, lactose_free, nut_free…)
        - health_scores → scores numériques (fodmap, gi, anti_inflam…)
        - context_tags  → tags contextuels optionnels (sport, meal_timing)

    Args:
        recipe : dict recette
        force  : si True, recalcule même si les données existent déjà

    Returns:
        La recette modifiée (même objet).
    """
    if not force and recipe.get("diet_flags_source") == "manual":
        return recipe

    # Avec force=True : masquer temporairement diet_flags_source pour que
    # compute_diet_flags recalcule au lieu de retourner l'existant.
    _saved_source = recipe.get("diet_flags", {}).get("diet_flags_source") if force else None
    if force and isinstance(recipe.get("diet_flags"), dict):
        recipe["diet_flags"].pop("diet_flags_source", None)

    recipe["diet_flags"]    = compute_diet_flags(recipe)
    recipe["health_scores"] = compute_health_scores(recipe)
    recipe["context_tags"]  = compute_context_tags(recipe)
    return recipe


def apply_flags(recipe: dict, force: bool = False) -> dict:
    """
    Rétrocompatibilité — applique uniquement diet_flags.
    Préférer apply_all_scores() pour les nouvelles installations.
    """
    if not force and recipe.get("diet_flags_source") == "manual":
        return recipe

    # Avec force=True : masquer temporairement diet_flags_source
    if force and isinstance(recipe.get("diet_flags"), dict):
        recipe["diet_flags"].pop("diet_flags_source", None)

    recipe["diet_flags"] = compute_diet_flags(recipe)
    return recipe


def batch_update(recipes: list[dict], force: bool = False) -> dict:
    """
    Recalcule les 3 colonnes JSONB sur toute une liste de recettes.

    Args:
        recipes : liste de dicts recette (modifiés en place)
        force   : si True, écrase les flags manuels

    Returns:
        {"total", "updated", "skipped", "stats"}
    """
    updated = skipped = 0
    stats: dict[str, int] = {
        "vegan": 0, "vegetarian": 0, "gluten_free": 0,
        "lactose_free": 0, "nut_free": 0,
        "raw": 0, "kid_friendly": 0,
    }

    for recipe in recipes:
        if not force and recipe.get("diet_flags_source") == "manual":
            skipped += 1
            continue

        apply_all_scores(recipe, force=force)
        updated += 1

        for flag in stats:
            if recipe.get("diet_flags", {}).get(flag):
                stats[flag] += 1

    logger.info(
        "batch_update: %d recettes traitées (%d mises à jour, %d ignorées)",
        len(recipes), updated, skipped,
    )
    return {
        "total":   len(recipes),
        "updated": updated,
        "skipped": skipped,
        "stats":   stats,
    }


def audit(recipes: list[dict]) -> list[dict]:
    """
    Compare les diet_flags stockés aux diet_flags calculés.

    Returns:
        Liste des divergences :
        [{"id", "title", "stored", "computed", "diff"}, …]
    """
    divergences = []
    for recipe in recipes:
        stored   = recipe.get("diet_flags") or {}
        computed = compute_diet_flags(recipe)

        computed_public = {k: v for k, v in computed.items() if not k.startswith("_")}
        stored_public   = {k: v for k, v in stored.items()   if not k.startswith("_")}

        diff = {
            k: {"stored": stored_public.get(k), "computed": computed_public[k]}
            for k in computed_public
            if stored_public.get(k) != computed_public[k]
        }
        if diff:
            divergences.append({
                "id":       recipe.get("id"),
                "title":    recipe.get("titles", {}).get("fr", "")[:40],
                "source":   recipe.get("diet_flags_source", "unknown"),
                "stored":   stored_public,
                "computed": computed_public,
                "diff":     diff,
            })

    return divergences