"""
search_token_generator.py — Génération des search_tokens pour toutes les recettes.

Enrichit chaque recette avec un champ `search_tokens: list[str]` pré-calculé
qui couvre les synonymes, thèmes, régimes et propriétés nutritionnelles.
Cela permet à search_engine_v3 de trouver des recettes via des requêtes
naturelles comme "protéines sport", "sans gluten rapide", "asiatique léger".

Groupes de tokens générés :
  1. Titres (FR + original, tokenisés)
  2. Ingrédients principaux (noms FR + EN)
  3. Cuisine d'origine + synonymes géographiques
  4. Techniques de cuisson
  5. Régimes alimentaires
  6. Profil temps (rapide / long)
  7. Profil difficulté
  8. Thèmes nutritionnels (riche protéines, fer, fibre…)
  9. Profil ingrédients (légumineuses, céréales, légumes…)
 10. Saison (si données saisonnalité disponibles)

Usage :
    from backend.engine.search_token_generator import generate_tokens, batch_generate
    tokens = generate_tokens(recipe)
    batch_generate(recipes)   # modifie en place + sauvegarde
"""
import logging
import unicodedata
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Mappings synonymes ────────────────────────────────────────────────────────

# Cuisine → tokens géographiques et culturels
_CUISINE_TOKENS: dict[str, list[str]] = {
    "Japanese":      ["japonais", "japon", "asiatique", "asia"],
    "Korean":        ["coréen", "corée", "asiatique", "asia"],
    "Chinese":       ["chinois", "chine", "asiatique", "wok"],
    "Thai":          ["thaï", "thaïlande", "asiatique", "curry"],
    "Indian":        ["indien", "inde", "curry", "épicé", "spicy"],
    "Vietnamese":    ["vietnamien", "vietnam", "asiatique"],
    "Lebanese":      ["libanais", "liban", "moyen-orient", "méditerranée"],
    "Turkish":       ["turc", "turquie", "méditerranée", "moyen-orient"],
    "Mexican":       ["mexicain", "mexique", "latino", "épicé"],
    "Italian":       ["italien", "italie", "méditerranée", "pasta", "pâtes"],
    "French":        ["français", "france", "classique"],
    "Greek":         ["grec", "grèce", "méditerranée"],
    "Spanish":       ["espagnol", "espagne", "méditerranée"],
    "Moroccan":      ["marocain", "maroc", "africain", "tajine", "épicé"],
    "Ethiopian":     ["éthiopien", "éthiopie", "africain", "épicé"],
    "Georgian":      ["géorgien", "géorgie", "caucase"],
    "American":      ["américain", "usa", "burger"],
    "Mediterranean": ["méditerranéen", "méditerranée"],
    "Asian":         ["asiatique", "asia"],
    "Middle Eastern":["moyen-orient", "méditerranée"],
    "African":       ["africain", "afrique"],
    "Latin American":["latino", "amérique latine"],
    "Brazilian":     ["brésilien", "brésil", "latino"],
    "Peruvian":      ["péruvien", "pérou", "latino", "andin"],
    "British":       ["britannique", "anglais"],
    "German":        ["allemand", "allemagne"],
    "Hungarian":     ["hongrois", "hongrie"],
    "Polish":        ["polonais", "pologne"],
    "Russian":       ["russe", "russie", "est-européen"],
    "Israeli":       ["israélien", "israël", "moyen-orient"],
    "Indonesian":    ["indonésien", "indonésie", "asiatique"],
    "Malaysian":     ["malaisien", "malaisie", "asiatique"],
    "Sri Lankan":    ["sri lankais", "sri lanka", "asiatique", "curry"],
    "Bangladeshi":   ["bangladais", "bangladesh", "asiatique"],
    "Pakistani":     ["pakistanais", "pakistan", "asiatique", "curry"],
    "Nepalese":      ["népalais", "népal", "asiatique"],
    "Afghan":        ["afghan", "afghanistan", "moyen-orient"],
    "Andean":        ["andin", "andins", "latino"],
    "Caribbean":     ["caraïbes", "antilles", "tropical"],
    "West African":  ["ouest-africain", "afrique de l'ouest"],
    "East African":  ["est-africain", "afrique de l'est"],
}

_CUISINE_KEYS = {k.lower().replace(" ", "_"): k for k in _CUISINE_TOKENS}

# Catégories d'ingrédients → thèmes de recherche
_CATEGORY_TOKENS: dict[str, list[str]] = {
    "plant_protein": ["protéines végétales", "protéines", "protein", "sport", "muscle"],
    "legume_pulse":  ["légumineuses", "légumes secs", "protéines végétales", "fibre"],
    "legume":        ["légumineuses", "légumes secs"],
    "grain_cereal":  ["céréales", "grains", "glucides", "carbs"],
    "vegetable":     ["légumes", "vegetables", "végétarien"],
    "fruit":         ["fruits", "sucré", "vitamine c"],
    "nut_seed":      ["noix", "graines", "oméga", "sain"],
    "dairy":         ["produits laitiers", "calcium"],
    "spice":         ["épicé", "épices", "aromatique"],
    "herb":          ["herbes", "frais", "aromatique"],
    "fat_oil":       ["matières grasses", "huile"],
}

# Ingrédients spécifiques → tokens nutrition/santé
_INGREDIENT_NUTRITION_TOKENS: dict[str, list[str]] = {
    # Fer
    "lentils":         ["fer", "iron", "anémie", "protéines"],
    "lentilles_vert":  ["fer", "iron", "anémie", "protéines"],
    "lentilles_corail":["fer", "iron", "anémie", "protéines"],
    "spinach":         ["fer", "iron", "épinards", "anémie", "magnésium"],
    "chickpea":        ["pois chiches", "fer", "protéines", "fibre"],
    "tofu":            ["protéines", "soja", "calcium", "sport"],
    "tempeh":          ["protéines", "probiotiques", "fermenté"],
    "quinoa":          ["protéines complètes", "sans gluten", "sport"],
    # Calcium
    "sesame":          ["calcium", "sésame", "graines"],
    "tahini":          ["calcium", "sésame", "graines"],
    "kale":            ["calcium", "vitamine k", "super aliment"],
    # Oméga-3
    "walnuts":         ["oméga-3", "noix", "cerveau"],
    "chia_seeds":      ["oméga-3", "graines", "super aliment"],
    "flaxseed":        ["oméga-3", "graines de lin"],
    # Vitamine C
    "bell_pepper":     ["vitamine c", "poivron", "antioxydants"],
    "tomato":          ["vitamine c", "lycopène", "antioxydants"],
    "lemon":           ["vitamine c", "agrume", "acidité"],
    # Probiotiques
    "miso":            ["probiotiques", "fermenté", "umami"],
    "kimchi":          ["probiotiques", "fermenté", "coréen"],
}

# Temps → tokens
def _time_tokens(total_time: int | None) -> list[str]:
    if not total_time:
        return []
    if total_time <= 20:
        return ["rapide", "express", "quick", "5 min", "10 min", "20 min"]
    if total_time <= 30:
        return ["rapide", "quick", "30 minutes", "rapide"]
    if total_time <= 45:
        return ["moyen", "45 minutes"]
    if total_time <= 60:
        return ["1 heure"]
    return ["long", "mijoté", "lent"]

# Difficulté → tokens
def _difficulty_tokens(diff: int | None) -> list[str]:
    if diff == 1:
        return ["facile", "simple", "débutant", "easy"]
    if diff == 2:
        return ["moyen", "intermédiaire"]
    if diff == 3:
        return ["complexe", "technique", "chef", "avancé"]
    return []


# ── Normalisation ─────────────────────────────────────────────────────────────

def _norm(text: str) -> str:
    t = text.lower().strip()
    t = unicodedata.normalize("NFD", t)
    return "".join(c for c in t if unicodedata.category(c) != "Mn")


# ── Génération principale ─────────────────────────────────────────────────────

def generate_tokens(recipe: dict, ings_dict: dict | None = None) -> list[str]:
    """
    Génère la liste complète de search_tokens pour une recette.

    Args:
        recipe    : dict recette
        ings_dict : dictionnaire ingrédients (optionnel, chargé si absent)

    Returns:
        Liste de tokens uniques, normalisés, triés par pertinence.
    """
    if ings_dict is None:
        from backend.core.data_io import load_ingredients_dict
        ings_dict = load_ingredients_dict()

    tokens: set[str] = set()

    # ── 1. Titres ─────────────────────────────────────────────────────────────
    titles = recipe.get("titles", {})
    for field in ("fr", "original", "en"):
        title = titles.get(field, "") or recipe.get(f"title_{field}", "") or ""
        for word in title.lower().replace("-", " ").split():
            w = _norm(word)
            if len(w) >= 3:
                tokens.add(w)

    # Variations titre : traductions courantes EN→FR pour les plats courants
    title_en = _norm(titles.get("original", titles.get("en", "")) or recipe.get("titles", {}).get("original", "") or "")
    title_fr = _norm(titles.get("fr", "") or recipe.get("titles", {}).get("fr", "") or "")
    _TITLE_VARIANTS = {
        "pasta": ["pates", "pâtes"], "noodle": ["nouilles"], "soup": ["soupe"],
        "salad": ["salade"], "rice": ["riz"], "bread": ["pain"],
        "stew": ["ragout", "mijoté"], "curry": ["curry"],
        "dumpling": ["ravioli", "bouchee"], "roll": ["rouleau"],
        "bowl": ["bol"], "burger": ["burger"], "wrap": ["wrap"],
        "smoothie": ["smoothie"], "cake": ["gateau"],
    }
    for en_word, fr_variants in _TITLE_VARIANTS.items():
        if en_word in title_en or en_word in title_fr:
            for v in fr_variants:
                tokens.add(v)

    # ── 2. Ingrédients principaux ─────────────────────────────────────────────
    ings = recipe.get("ingredients", [])
    if not ings and recipe.get("composition"):
        ings = [c["ingredient"] for c in recipe.get("composition", [])]
    for ing in ings[:12]:
        iid = ing.get("ingredient_id", "") if isinstance(ing, dict) else str(ing)
        if not iid:
            continue
        d = ings_dict.get(iid, {})
        for name_field in ("canonical_name_fr", "canonical_name_en"):
            name = d.get(name_field, iid).lower()
            for word in name.replace("-", " ").split():
                w = _norm(word)
                if len(w) >= 3:
                    tokens.add(w)
        # Tokens nutrition spécifiques
        for nutr_token in _INGREDIENT_NUTRITION_TOKENS.get(iid, []):
            tokens.add(_norm(nutr_token))
        # Tokens catégorie
        cat = d.get("category", "")
        for cat_token in _CATEGORY_TOKENS.get(cat, []):
            tokens.add(_norm(cat_token))

    # ── 3. Cuisine d'origine ──────────────────────────────────────────────────
    from backend.core.data_io import recipe_cuisine
    cuisine = recipe_cuisine(recipe)
    if cuisine:
        tokens.add(_norm(cuisine))
        # recettes : 'sri_lankan', 'french_provencal' ; table : 'Sri Lankan', 'French'
        key = _CUISINE_KEYS.get(cuisine) or _CUISINE_KEYS.get(cuisine.split("_")[0])
        for ct in _CUISINE_TOKENS.get(key, []):
            tokens.add(_norm(ct))

    # ── 4. Techniques ─────────────────────────────────────────────────────────
    tags = recipe.get("tags", {})
    techniques = recipe.get("technique") or tags.get("technique", [])
    for tech in techniques:
        tokens.add(_norm(str(tech)))

    # ── 5. Régimes alimentaires ───────────────────────────────────────────────
    flags = recipe.get("diet_flags", {})
    diet_tags = recipe.get("tags", {}).get("diet", [])
    if flags.get("vegan") or "vegan" in diet_tags:
        tokens.update(["vegan", "vegetalien", "sans produit animal"])
    if flags.get("vegetarian") or "vegetarien" in diet_tags:
        tokens.update(["vegetarien", "sans viande"])
    if flags.get("gluten_free") or "sans_gluten" in diet_tags:
        tokens.update(["sans gluten", "gluten free", "coeliaque"])
    if flags.get("raw") or "raw" in diet_tags:
        tokens.update(["cru", "raw", "vivant", "crudivorisme"])
    if flags.get("kid_friendly") or "kid_friendly" in diet_tags:
        tokens.update(["enfants", "famille", "kids", "facile enfants"])

    # ── 6. Temps ──────────────────────────────────────────────────────────────
    timing = recipe.get("timing", {})
    for tt in _time_tokens(recipe.get("timing", {}).get("total_min") or timing.get("total_min")):
        tokens.add(_norm(tt))

    # ── 7. Difficulté ─────────────────────────────────────────────────────────
    diff_val = recipe.get("difficulty")
    diff_lvl = str(recipe.get("difficulty_level") or recipe.get("difficulty level") or "").lower()
    if diff_lvl in ("easy", "facile"): diff_val = 1
    elif diff_lvl in ("medium", "intermediaire"): diff_val = 2
    elif diff_lvl in ("hard", "difficile", "complexe"): diff_val = 3
    for dt in _difficulty_tokens(diff_val):
        tokens.add(_norm(dt))

    # ── 8. Structure culinaire → thèmes ──────────────────────────────────────
    struct = recipe.get("structure_culinaire", {}) or {}
    if struct.get("proteine"):
        tokens.update(["protéines", "proteines", "protein", "sport", "muscle"])
    if struct.get("legume"):
        tokens.update(["legumes", "vegetables", "sante"])
    if struct.get("base") and any("riz" in str(b) or "rice" in str(b)
                                   for b in struct.get("base", [])):
        tokens.update(["riz", "rice", "asiatique"])

    # ── 9. Iconic level / prestige ────────────────────────────────────────────
    iconic = recipe.get("iconic_status", {}) or recipe.get("scoring", {}).get("iconic", {})
    if iconic.get("iconic_level") == "world" or "world" in iconic.get("tags", []):
        tokens.update(["traditionnel", "authentique", "iconique", "classique"])
    elif iconic.get("iconic_level") == "regional" or "regional" in iconic.get("tags", []):
        tokens.update(["traditionnel", "regional", "typique"])

    # ── 10. Santé / nutrition contextuelle ────────────────────────────────────
    from backend.core.data_io import load_nutrition_graph
    ng = load_nutrition_graph()
    rid = str(recipe.get("id", ""))
    nutr = ng.get(rid, {})
    if nutr:
        servings = max(1, recipe.get("servings", 4) or 4)
        protein_per = nutr.get("protein", 0) / servings
        fiber_per   = nutr.get("fiber", 0) / servings
        cal_per     = nutr.get("calories", 0) / servings
        iron_per    = nutr.get("iron", 0) / servings

        if protein_per >= 15:
            tokens.update(["riche en proteines", "protéines", "sport", "muscle"])
        if fiber_per >= 8:
            tokens.update(["riche en fibres", "fibre", "digestion"])
        if cal_per <= 300:
            tokens.update(["leger", "light", "minceur", "low calorie"])
        if iron_per >= 3:
            tokens.update(["fer", "iron", "anemie"])

    # Filtrage : supprimer les tokens trop courts ou vides
    return sorted({t for t in tokens if t and len(t) >= 3})


def batch_generate(recipes: list[dict],
                   save: bool = True) -> dict:
    """
    Génère et attache les search_tokens sur toute la liste de recettes.

    Args:
        recipes : liste de recettes (modifiée en place)
        save    : si True, sauvegarde le fichier recipes.json

    Returns:
        {"total": int, "avg_tokens": float, "min": int, "max": int}
    """
    from backend.core.data_io import load_ingredients_dict
    ings_dict = load_ingredients_dict()

    counts = []
    for i, recipe in enumerate(recipes):
        tokens = generate_tokens(recipe, ings_dict)
        recipe["search_tokens"] = tokens
        counts.append(len(tokens))
        if (i + 1) % 100 == 0:
            logger.info("search_token_generator : %d/%d recettes traitées", i+1, len(recipes))

    stats = {
        "total":      len(recipes),
        "avg_tokens": round(sum(counts) / len(counts), 1) if counts else 0,
        "min_tokens": min(counts) if counts else 0,
        "max_tokens": max(counts) if counts else 0,
    }
    logger.info("search_tokens générés : moy=%.1f min=%d max=%d",
                stats["avg_tokens"], stats["min_tokens"], stats["max_tokens"])

    if save:
        import json
        from backend.engine.config import DATA_ROOT
        from backend.core.data_io import save_json
        path = DATA_ROOT / "recipes" / "recipes.json"
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, dict):
            raw["recipes"] = recipes
        else:
            raw = recipes
        save_json(path, raw)
        logger.info("recipes.json sauvegardé avec search_tokens")

    return stats
