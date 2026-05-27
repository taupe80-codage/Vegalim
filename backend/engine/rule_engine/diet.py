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

# Ingrédients FODMAP triggers — liste scientifique (Monash University)
HIGH_FODMAP_IDS: frozenset[str] = frozenset({
    "onion", "red_onion", "white_onion", "spring_onion", "shallot", "leek",
    "garlic", "mushroom", "cauliflower", "apple", "pear", "watermelon",
    "honey", "lentil", "chickpea", "bean", "black_bean",
    "red_kidney_bean", "white_bean", "soybean", "green_peas",
    "wheat", "rye", "barley", "flour", "bread", "pasta",
    "miso", "soy_sauce",
})


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

    # Ingrédients à traces résiduelles : la recette reste lactose_free=True
    # mais on signale à l'utilisateur que des traces sont présentes.
    lactose_trace_ingredients = [i for i in ids if i in LACTOSE_TRACE_IDS]

    techniques = [str(t).lower() for t in (recipe.get("technique") or [])]
    is_raw = any(t in ("raw", "cru", "marinade", "ceviche") for t in techniques)

    strong_spices = {"chili", "piment", "harissa", "wasabi", "gochujang", "sriracha"}
    is_kid = (
        not any(i in strong_spices for i in ids) and
        len(ids) <= 8 and
        int(recipe.get("prep_time_min") or 999) <= 30
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
    omega3    = float(nutr.get("omega_3", 0) or 0)
    gi        = float(nutr.get("glycemic_index", 0) or 0)

    ids = _extract_ids(recipe)
    fodmap_count = sum(1 for i in ids if i in HIGH_FODMAP_IDS)

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
        "fodmap_level": (
            "low"    if fodmap_count == 0 else
            "medium" if fodmap_count <= 2  else
            "high"
        ),
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