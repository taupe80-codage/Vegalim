#!/usr/bin/env python3
"""
ALIM — Réécriture Chef v7.1

Corrections v7.1 (bugfixes)
─────────────────────────────────────────────────────────────────────
  - description_longue : pénalité silencieuse → issue déclarée + signalée au LLM
  - _build_fresh_dry_pairs : condition form_a élargie aux form root/leaf/bulb
  - _recipe_is_vegan : vegan_flag_but_animal exclut le path vegan (était inversé)
  - detect_description_fictive : _GENERIC_FOOD_WORDS maintenant appliqué
  - merge_and_save : total_min recalculé une seule fois après les deux corrections
  - --report : eligible_ids/processed non vides (reconstruction depuis recettes)
  - Seuil description courte unifié à DESC_MIN_LEN (était 100 dans la boucle)
  - Prompt : toutes les recettes sont au minimum végétariennes (miel OK)

v7.0 — Normalisation canonique des ingrédients + serving_suggestions

  1. SYSTÈME DE NOMMAGE CANONIQUE
     Chaque clé ingrédient est résolue vers sa forme canonique
     nutri_id/var_key via ingredient_map + nutrition_v2.
     Les axes (thermal_state, cooking_state, form, part…) guident
     le LLM pour choisir le bon variant (frais vs séché, etc.).

  2. DÉTECTION FRAIS/SEC
     Paires frais/sec détectées via axes thermal_state dans n2.
     Quand une clé est générique (thyme sans état), le LLM reçoit
     les deux formes canoniques et choisit selon le contexte.

  3. DESCRIPTION — INGRÉDIENTS FICTIFS INTERDITS
     Le rewriter ne peut mentionner dans la description QUE des
     ingrédients présents dans la composition de la recette.
     Détecteur : compare les noms FR des ingrédients cités dans
     la description vs la liste de composition.

  4. SERVING SUGGESTIONS
     Le LLM peut proposer des ingrédients optionnels d'accompagnement
     (garnish, sauce, side dish…) en tant que "serving_suggestions"
     dans la composition, avec role="serving_suggestion" et
     optional=true. Le frontend les affichera séparément pour que
     l'utilisateur choisisse de les ajouter ou non.

  5. SUPPRESSION ÉTAPE NUNUCHE
     Détection de la dernière étape "appréciation" sans action
     concrète. Le rewriter finit sur la façon de servir.

  6. --ingredient-map
     Fichier ingredient_map_YYYY-MM-DD.json → résolution canonique.

Historique
──────────
v6.1 — Fix vegan injection + prep_passive_min + eggplant FP
v6.0 — Score-based filtering + rapport enrichi
"""

import json
import re
import time
import sys
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# ===================== CONFIG =====================
BATCH_SIZE   = 1
DELAY_S      = 23
MAX_RETRIES  = 6
TEMPERATURE  = 0.60

DESC_MIN_LEN       = 150
STEP_MIN_LEN       = 120
MIN_VAGUE_STEPS    = 2
STEP_GENERIC_MAX   = 80

DEFAULT_SCORE_THRESHOLD = 8.5

OUTPUT_SUFFIX   = "_chef_rewrite_smart.json"
PROGRESS_SUFFIX = ".rewrite_progress_smart.json"

# ===================== WHITELIST COOK_MIN=0 =====================
COOK_ZERO_LEGITIMATE_PATTERNS = [
    r'\bsorbet\b', r'\bcarpaccio\b', r'\bguacamole\b', r'\btartare\b',
    r'\bceviche\b', r'\bcrudités\b', r'\bgazpacho\b', r'\bsalade\b',
    r'\btaboulé\b', r'\bpanzanella\b',
    r'\bconcombre\b.{0,20}\bjaponaise?\b',
    r'\bcrème fraîche maison\b', r'\blait de coco maison\b',
]

# ===================== GLOBALS =====================
_VARIANT_INDEX:   dict | None = None
_SK_INDEX:        dict | None = None
_ALIAS_INDEX:     dict | None = None
INGREDIENT_FR_MAP: dict[str, list[str]] = {}

# v7
_INGREDIENT_MAP:   dict | None = None
_CANONICAL_INDEX:  dict | None = None
_FRESH_DRY_PAIRS:  dict | None = None
_N2_FULL:          dict | None = None


# ===================== CANONICAL INDEX =====================

def _build_canonical_index() -> None:
    global _CANONICAL_INDEX
    _CANONICAL_INDEX = {}
    if not _INGREDIENT_MAP or not _N2_FULL:
        return
    for recipe_key, map_entry in _INGREDIENT_MAP.items():
        nutri_id = map_entry.get("nutri_id")
        if not nutri_id or nutri_id not in _N2_FULL:
            _CANONICAL_INDEX[recipe_key] = None
            continue
        variants = _N2_FULL[nutri_id].get("variants", {})
        if not variants:
            _CANONICAL_INDEX[recipe_key] = None
            continue
        options = [
            {
                "canonical": f"{nutri_id}/{vk}",
                "nutri_id":  nutri_id,
                "var_key":   vk,
                "axes":      vd.get("axes", {}),
                "name_fr":   vd.get("name_fr", ""),
            }
            for vk, vd in variants.items()
        ]
        if len(options) == 1:
            _CANONICAL_INDEX[recipe_key] = {
                **options[0],
                "is_ambiguous": False,
                "options":      options,
                "status":       map_entry.get("status", ""),
            }
        else:
            best = options[0]
            if "/" in recipe_key:
                _, rvar = recipe_key.split("/", 1)
                for opt in options:
                    if opt["var_key"] == rvar:
                        best = opt
                        break
            _CANONICAL_INDEX[recipe_key] = {
                **best,
                "is_ambiguous": True,
                "options":      options,
                "status":       map_entry.get("status", ""),
            }


def _build_fresh_dry_pairs() -> None:
    global _FRESH_DRY_PAIRS
    _FRESH_DRY_PAIRS = {}
    if not _N2_FULL:
        return
    _FRESH_FORMS = {"fresh_herb", "root", "leaf", "bulb", "stem", ""}
    for base_a, entry_a in _N2_FULL.items():
        for var_a, vd_a in entry_a.get("variants", {}).items():
            axes_a = vd_a.get("axes", {})
            ts_a   = axes_a.get("thermal_state", "")
            form_a = axes_a.get("form", "")
            if ts_a != "fresh" or form_a not in _FRESH_FORMS:
                continue
            root = re.sub(r"_fresh.*", "", base_a).rstrip("_")
            if not root or root in _FRESH_DRY_PAIRS:
                continue
            for base_b, entry_b in _N2_FULL.items():
                if base_b == base_a or not base_b.startswith(root):
                    continue
                for var_b, vd_b in entry_b.get("variants", {}).items():
                    axes_b = vd_b.get("axes", {})
                    ts_b   = axes_b.get("thermal_state", "")
                    form_b = axes_b.get("form", "")
                    if ts_b == "dried" or form_b in ("spice", "powder"):
                        rk_fresh, rk_dried = [], []
                        if _INGREDIENT_MAP:
                            for rk, me in _INGREDIENT_MAP.items():
                                nid = me.get("nutri_id", "")
                                if nid == base_a:   rk_fresh.append(rk)
                                elif nid == base_b: rk_dried.append(rk)
                        _FRESH_DRY_PAIRS[root] = {
                            "fresh":             f"{base_a}/{var_a}",
                            "dried":             f"{base_b}/{var_b}",
                            "fresh_axes":        axes_a,
                            "dried_axes":        axes_b,
                            "recipe_keys_fresh": rk_fresh,
                            "recipe_keys_dried": rk_dried,
                        }
                        break
                if root in _FRESH_DRY_PAIRS:
                    break


def _build_ingredient_fr_map() -> None:
    global INGREDIENT_FR_MAP
    INGREDIENT_FR_MAP = {}
    if not _VARIANT_INDEX:
        return
    for base_key, var_map in _VARIANT_INDEX.items():
        if base_key == "__base_recipes__":
            continue
        base_names: list[str] = []
        for var_key, name_fr in var_map.items():
            if not name_fr:
                continue
            full_key = f"{base_key}/{var_key}"
            entry = INGREDIENT_FR_MAP.setdefault(full_key, [])
            if name_fr not in entry:
                entry.append(name_fr)
            if name_fr not in base_names:
                base_names.append(name_fr)
        if base_names:
            INGREDIENT_FR_MAP[base_key] = base_names


# ===================== CONSTANTES MODULE =====================
_BASE_DISH_TYPES = {"sauce", "condiment", "broth", "paste", "roux", "ingredient"}


# ===================== INIT =====================

def init_variant_index(
    nutrition_path:   str | None,
    recipes_ref_path: str | None,
    imap_path:        str | None = None,
) -> None:
    global _VARIANT_INDEX, _SK_INDEX, _ALIAS_INDEX, _N2_FULL, _INGREDIENT_MAP
    _VARIANT_INDEX = {}
    _SK_INDEX      = {}
    _ALIAS_INDEX   = {}
    _N2_FULL       = {}

    if nutrition_path:
        try:
            with open(nutrition_path, encoding="utf-8") as f:
                nutr = json.load(f)
            _N2_FULL = nutr.get("ingredients", {})
            for base_key, entry in _N2_FULL.items():
                variants = entry.get("variants", {})
                var_map  = {}
                for var_key, var_data in variants.items():
                    name_fr = var_data.get("name_fr", var_key)
                    var_map[var_key] = name_fr
                    sk = var_data.get("source_key")
                    if sk:
                        _SK_INDEX[sk] = (base_key, var_key)
                    for alias in var_data.get("aliases", []):
                        _ALIAS_INDEX[alias.lower()] = (base_key, var_key)
                if var_map:
                    _VARIANT_INDEX[base_key] = var_map
            _build_ingredient_fr_map()
            print(f"📚 nutrition_v2 chargé : {len(_VARIANT_INDEX)} bases, "
                  f"{sum(len(v) for v in _VARIANT_INDEX.values())} variants")
        except Exception as e:
            print(f"⚠️  Impossible de charger nutrition : {e}")

    if imap_path:
        try:
            with open(imap_path, encoding="utf-8") as f:
                _INGREDIENT_MAP = json.load(f)
            matched = sum(1 for v in _INGREDIENT_MAP.values() if v.get("nutri_id"))
            print(f"📚 ingredient_map chargé : {len(_INGREDIENT_MAP)} entrées "
                  f"({matched} matchées, {len(_INGREDIENT_MAP)-matched} unmatched)")
            _build_canonical_index()
            _build_fresh_dry_pairs()
            print(f"🔗 Index canonique : {len(_CANONICAL_INDEX or {})} clés résolues, "
                  f"{len(_FRESH_DRY_PAIRS or {})} paires frais/sec")
        except Exception as e:
            print(f"⚠️  Impossible de charger ingredient_map : {e}")

    if recipes_ref_path:
        try:
            with open(recipes_ref_path, encoding="utf-8") as f:
                ref_data = json.load(f)
            ref_recipes = ref_data if isinstance(ref_data, list) else ref_data.get("recipes", [])
            added = 0
            for r in ref_recipes:
                if r.get("dish_type") not in _BASE_DISH_TYPES:
                    continue
                rid   = r["id"]
                title = r.get("titles", {}).get("fr") or rid
                if "__base_recipes__" not in _VARIANT_INDEX:
                    _VARIANT_INDEX["__base_recipes__"] = {}
                _VARIANT_INDEX["__base_recipes__"][rid] = title
                _ALIAS_INDEX[title.lower()] = ("__base_recipes__", rid)
                added += 1
            print(f"📚 base_recipes chargées : {added} recettes-base indexées")
        except Exception as e:
            print(f"⚠️  Impossible de charger recipes-ref : {e}")


# ===================== RÉSOLUTION / LOOKUP =====================

def resolve_ingredient_to_base(ing_key: str) -> tuple[str, str] | None:
    if _VARIANT_INDEX is None:
        return None
    if ing_key in _VARIANT_INDEX:
        return (ing_key, "default")
    if "/" in ing_key:
        b, v = ing_key.split("/", 1)
        if b in _VARIANT_INDEX and v in _VARIANT_INDEX[b]:
            return (b, v)
    if ing_key in _SK_INDEX:
        return _SK_INDEX[ing_key]
    if ing_key.lower() in _ALIAS_INDEX:
        return _ALIAS_INDEX[ing_key.lower()]
    return None


def get_available_variants(base_key: str) -> dict[str, str]:
    if _VARIANT_INDEX is None:
        return {}
    return {k: v for k, v in _VARIANT_INDEX.get(base_key, {}).items() if k != "default"}


def get_canonical(recipe_key: str) -> dict | None:
    if _CANONICAL_INDEX is None:
        return None
    return _CANONICAL_INDEX.get(recipe_key)


def get_fresh_dry_pair(recipe_key: str) -> dict | None:
    if not _FRESH_DRY_PAIRS:
        return None
    explicit = any(w in recipe_key for w in ("fresh", "dried", "spice_dried", "ground"))
    if explicit:
        return None
    for pair in _FRESH_DRY_PAIRS.values():
        if recipe_key in pair.get("recipe_keys_fresh", []) \
                or recipe_key in pair.get("recipe_keys_dried", []):
            return pair
    return None


def analyze_generic_ingredients(r: dict) -> tuple[list[dict], list[str]]:
    if _VARIANT_INDEX is None:
        return [], []
    upgradeable = []
    missing     = []
    for c in r.get("composition", []):
        ing = c.get("ingredient", "")
        if not ing:
            continue
        resolved = resolve_ingredient_to_base(ing)
        if resolved is None:
            missing.append(ing)
            continue
        base_key, var_key = resolved
        non_default = get_available_variants(base_key)
        if var_key in ("default", None) and non_default:
            upgradeable.append({
                "ing_key":            ing,
                "base_key":           base_key,
                "current_var":        var_key,
                "available_variants": non_default,
            })
    return upgradeable, missing


def _get_noncanonical_ingredients(r: dict) -> list[dict]:
    """v7 — Ingrédients dont la clé n'est pas au format nutri_id/var_key."""
    if _CANONICAL_INDEX is None:
        return []
    results = []
    seen    = set()
    for c in r.get("composition", []):
        # Ignorer les serving_suggestions déjà canoniques
        if c.get("meta", {}).get("role") == "serving_suggestion":
            continue
        ing_key = c.get("ingredient", "")
        if not ing_key or ing_key in seen:
            continue
        seen.add(ing_key)
        canon_entry = get_canonical(ing_key)
        fresh_dry   = get_fresh_dry_pair(ing_key)
        if canon_entry is None:
            continue
        current_canonical = canon_entry.get("canonical", "")
        is_ambiguous      = canon_entry.get("is_ambiguous", False)
        needs_flag = ing_key != current_canonical or fresh_dry or is_ambiguous
        if not needs_flag:
            continue
        entry = {
            "recipe_key":        ing_key,
            "current_canonical": current_canonical,
            "flag":              (
                "fresh_dry_ambigu" if fresh_dry and ing_key == current_canonical
                else "noncanonique"
            ),
            "options": canon_entry.get("options", []),
        }
        if fresh_dry:
            entry["fresh_dry_pair"] = {
                "fresh": {"canonical": fresh_dry["fresh"], "axes": fresh_dry["fresh_axes"]},
                "dried": {"canonical": fresh_dry["dried"], "axes": fresh_dry["dried_axes"]},
            }
        results.append(entry)
    return results


# ===================== DÉTECTION DESCRIPTION FICTIVE =====================

def _get_composition_fr_names(r: dict) -> set[str]:
    """
    Retourne l'ensemble des noms FR (normalisés en minuscules, lemmes simples)
    des ingrédients présents dans la composition d'une recette.
    """
    names = set()
    for c in r.get("composition", []):
        if c.get("meta", {}).get("role") == "serving_suggestion":
            continue  # les suggestions ne sont pas encore dans la recette
        ing_key = c.get("ingredient", "")
        if not ing_key:
            continue
        # Chercher via INGREDIENT_FR_MAP
        fr_terms = INGREDIENT_FR_MAP.get(ing_key, [])
        if not fr_terms and "/" in ing_key:
            fr_terms = INGREDIENT_FR_MAP.get(ing_key.split("/")[0], [])
        for term in fr_terms:
            names.add(term.lower())
        # Ajouter aussi la clé elle-même nettoyée
        clean = ing_key.replace("/", " ").replace("_", " ").lower()
        names.add(clean)
    return names


# Tokens génériques à ignorer dans la détection (articles, adjectifs culinaires courants)
_DESC_IGNORE_TOKENS = {
    "de", "du", "des", "le", "la", "les", "et", "en", "à", "au", "avec",
    "un", "une", "par", "sur", "sous", "dans", "qui", "que", "ce", "se",
    "sa", "son", "ses", "est", "sont", "ou", "il", "elle", "on",
    "doux", "douce", "épicé", "épicée", "frais", "fraîche", "léger", "légère",
    "chaud", "chaude", "froid", "froide", "cuit", "cuite", "grillé", "grillée",
    "mijoté", "mijotée", "sauté", "sautée", "croustillant", "moelleux",
    "onctueux", "savoureux", "délicat", "végétalien", "végétal", "végétarien",
    "maison", "traditionnel", "classique", "rustique", "raffiné",
}

# Noms propres de plats/cuisines qui ne sont pas des ingrédients
_CUISINE_NOUNS = re.compile(
    r'\b(curry|gratin|tarte|quiche|risotto|pilaf|dahl|dal|wok|soupe|potage|'
    r'velouté|crème|purée|ragù|ragout|sauté|mijoté|poêlée|galette|'
    r'casserole|tajine|tagine|bowl|bao|focaccia|pizza|pasta|lasagne)\b',
    re.IGNORECASE
)


def detect_description_fictive(r: dict) -> bool:
    """
    v7 — Retourne True si la description cite des ingrédients additionnels
    spécifiques (condiments, herbes, accompagnements…) qui ne figurent PAS
    dans la composition de la recette.

    Approche ciblée sur les ingrédients ADDITIONNELS (herbes, épices, sauces,
    condiments, garnitures) qui modifient le goût et seraient trompeurs si absents.
    On ignore : le titre du plat lui-même, les termes génériques (lait, crème,
    pâtes) qui peuvent désigner le plat produit, et les mots trop courts.

    Seuls les faux positifs significatifs sont signalés.
    """
    if not INGREDIENT_FR_MAP:
        return False
    desc = (r.get("description") or "").lower()
    if not desc or len(desc) < 50:
        return False

    title_fr = (r.get("titles") or {}).get("fr", "").lower()
    title_en = (r.get("titles") or {}).get("en", "").lower()

    comp_names = _get_composition_fr_names(r)
    if not comp_names:
        return False

    # Catégories d'ingrédients qui COMPTENT si absents (herbes fraîches,
    # épices caractéristiques, condiments distinctifs, garnitures concrètes).
    # On exclut les ingrédients trop génériques (lait, crème, pâtes, etc.)
    # qui peuvent être le produit lui-même ou une substitution évidente.
    _GENERIC_FOOD_WORDS = {
        "lait", "crème", "beurre", "huile", "eau", "sel", "sucre", "farine",
        "pain", "pâtes", "riz", "fromage", "yaourt", "sauce", "sirop",
        "jus", "bouillon", "fond", "vinaigre", "moutarde", "tomate",
        "oignon", "ail", "herbe", "épice", "légume", "fruit",
        # noms de plats produits
        "lait d", "crème d", "pâte d", "purée", "soupe", "gratin",
    }

    # Meta-catégories d'ingrédients à surveiller : herbes fraîches distinctives,
    # épices caractéristiques, condiments fins, garnitures
    _WATCH_PATTERNS = [
        # Herbes fraîches (absentes = trompeur)
        r'\b(coriandre|basilic|persil|menthe|estragon|ciboulette|aneth|thym frais|romarin frais)\b',
        # Épices caractéristiques (distinctives du plat)
        r'\b(safran|cardamome|fenugrec|za.atar|sumac|ras.el.hanout|gochujang|miso|tahini|wasabi)\b',
        # Condiments distinctifs
        r'\b(harissa|sambal|chimichurri|chermoula|dukkah|furikake|ponzu)\b',
        # Garnitures distinctives
        r'\b(grenade|pistache|noix de cajou|amande|noisette|graines de sésame)\b',
        # Fruits distinctifs (pas les "pommes" génériques)
        r'\b(mangue|papaye|fruit de la passion|litchi|goyave|physalis)\b',
    ]

    fictive_found = set()
    for pattern in _WATCH_PATTERNS:
        matches = re.findall(pattern, desc, re.IGNORECASE)
        for match in matches:
            match_lc = match.lower().strip()
            # Ignorer les termes alimentaires trop génériques
            if any(match_lc == gw or match_lc.startswith(gw) for gw in _GENERIC_FOOD_WORDS):
                continue
            # Est-ce dans le titre ? (le plat peut s'appeler "Salade à la coriandre")
            if match_lc in title_fr or match_lc in title_en:
                continue
            # Est-ce dans la composition ?
            if any(match_lc in cn or cn in match_lc for cn in comp_names):
                continue
            # Vérification : cet ingrédient est-il connu dans N2 ou l'imap ?
            # (éviter de signaler des mots qui ne sont pas des ingrédients)
            found_in_n2 = any(
                match_lc in fr_name
                for fr_names in INGREDIENT_FR_MAP.values()
                for fr_name in fr_names
            )
            if found_in_n2:
                fictive_found.add(match_lc)

    return len(fictive_found) > 0


# ===================== DÉTECTEURS =====================

_AUTO_DESC_PATTERNS = [
    r'à base de (water|white bean|cauliflower|red lentil|peas\b|potato\b|gnocchi|dried fava|kabocha|dashi)',
    r'aux saveurs (equilibre|doux|profond)$',
    r'^(Plat|Soupe|Préparation) (indienne?|marocaine?|levantin[e]?|italienne?|japonaise?|coréenne?|espagnole?) à base de',
    r'Plat (indienne?|marocaine?|coréenne?) à base de',
    r'\b(white bean|water\b|cauliflower|red lentil|dried fava|kabocha squash|vegetarian dashi)\b',
    r'aux saveurs umami',
    r'saveurs umami et (profond|équilibr)',
    r'aux saveurs équilibrées?\b',
    r'saveurs équilibrées?$',
    r'(Soupe|Plat|Préparation).{0,50}aux saveurs (umami|équilibr)',
    r'\baux saveurs profond(es?)?',
    r'Délicieux .{0,30}(saveurs équilibrées|saveurs umami)',
]

_GENERIC_KWORDS = ['servir immédiatement', 'vérifier la texture']
_OVEN_PATTERN   = re.compile(r'\bfour\b|\bgril\b|\bgratin|\brôti', re.IGNORECASE)
_TEMP_PATTERN   = re.compile(r'\d+\s*°[CF]')
_LEVAISON_RE    = re.compile(
    r'\b(lever?|levée|laisser lever|laisser repo|repos(?:er)?|ferment|pousser)\b',
    re.IGNORECASE
)
_YEAST_INGS = {'yeast', 'levure', 'sourdough', 'starter', 'poolish', 'levain'}

# Patterns étape nunuche (appréciation sans action concrète)
_NUNUCHE_PATTERNS = [
    r'\bappréciez\b',
    r'\bsavourez\b',
    r'\bdégustez\b(?!.*(?:chaud|froid|tiède|avec|dans|sur|accompagn))',
    r'\brégalez[\s-]vous\b',
    r'\bsavourant les saveurs\b',
    r'\bpartager avec plaisir\b',
    r'\bdécouvrez la saveur\b',
    r'\bsaveur combinée\b',
    r'\bservir et partager\b',
    r'\bla magie\b.*\bsaveurs\b',
]
# Verbes de service concrets → l'étape n'est PAS nunuche si présents
_SERVICE_ACTIONS = re.compile(
    r'\b(dresser|napper|garnir|saupoudrer|décorer|disposer|répartir|verser|'
    r'démouler|trancher|couper|arroser|'
    r'servir.{1,60}(chaud|tiède|froid|avec|dans|sur|accompagn|immédiatement))\b',
    re.IGNORECASE
)


def _is_nunuche_step(step: str) -> bool:
    sl = step.lower()
    has_pattern = any(re.search(p, sl, re.IGNORECASE) for p in _NUNUCHE_PATTERNS)
    if not has_pattern:
        return False
    return not bool(_SERVICE_ACTIONS.search(step))


def detect_issues(r: dict) -> list[str]:
    issues    = []
    desc      = r.get("description", "") or ""
    instrs    = r.get("instructions", []) or []
    instr_text = " ".join(instrs)

    if any(re.search(p, desc, re.IGNORECASE) for p in _AUTO_DESC_PATTERNS):
        issues.append("description_auto")
    if len(desc) < DESC_MIN_LEN and "description_auto" not in issues:
        issues.append("description_courte")
    if len(desc) > 250 and "description_auto" not in issues:
        issues.append("description_longue")

    vague = [s for s in instrs if isinstance(s, str) and len(s.strip()) < STEP_MIN_LEN]
    if len(vague) >= MIN_VAGUE_STEPS:
        issues.append("etapes_vagues")

    if _OVEN_PATTERN.search(instr_text) and not _TEMP_PATTERN.search(instr_text):
        issues.append("four_sans_temp")

    for s in instrs:
        sl = s.lower().strip()
        if any(kw in sl for kw in _GENERIC_KWORDS):
            has_criterion = re.search(
                r"(doit être|qui doit|légèrement|texture\s+\w+|couleur|soyeuse|ferme|crémeux|en appréci)", sl
            )
            if not has_criterion or len(s) < STEP_GENERIC_MAX:
                issues.append("generique")
                break

    flags = r.get("_flags", []) or []
    if any("BLOQUANT" in f or "vegan_alert" in f or "vegan_flag_but_animal" in f for f in flags):
        issues.append("flags_bloquants")

    timing_check = r.get("timing") or {}
    if (timing_check.get("prep_passive_min", 0) or 0) == 0:
        has_yeast_ing = any(
            any(y in c.get("ingredient", "").lower() for y in _YEAST_INGS)
            for c in r.get("composition", [])
        )
        if has_yeast_ing and _LEVAISON_RE.search(instr_text):
            issues.append("passive_time_manquant")

    if _VARIANT_INDEX is not None:
        upgradeable, _ = analyze_generic_ingredients(r)
        if upgradeable:
            issues.append("ingredients_generiques")

    if INGREDIENT_FR_MAP and instr_text:
        instr_lower = instr_text.lower()
        for c in r.get("composition", []):
            if c.get("meta", {}).get("role") == "serving_suggestion":
                continue
            ing_key  = c.get("ingredient", "")
            fr_terms = INGREDIENT_FR_MAP.get(ing_key)
            if not fr_terms:
                continue
            if not any(term.lower() in instr_lower for term in fr_terms):
                issues.append("ingredients_non_couverts")
                break

    # v7 — clés non-canoniques
    if _CANONICAL_INDEX is not None:
        if _get_noncanonical_ingredients(r):
            issues.append("ingredient_noncanonique")

    # v7 — description cite un ingrédient absent de la composition
    if INGREDIENT_FR_MAP and detect_description_fictive(r):
        issues.append("description_ingredient_fictif")

    # v7 — étape finale nunuche
    instrs_real = [s for s in instrs if isinstance(s, str)]
    if instrs_real and _is_nunuche_step(instrs_real[-1]):
        issues.append("derniere_etape_inutile")

    return issues


# ===================== SCORING =====================

_SCORE_PENALTIES: dict[str, float] = {
    "description_auto":                2.5,
    "description_courte":              1.5,
    "description_longue":              0.5,   # v7.1 — était une pénalité silencieuse
    "etapes_vagues":                   1.5,
    "four_sans_temp":                  1.0,
    "generique":                       0.5,
    "flags_bloquants":                 2.0,
    "ingredients_non_couverts":        0.5,
    "ingredients_generiques":          0.25,
    "passive_time_manquant":           1.0,
    # v7
    "ingredient_noncanonique":         0.75,
    "description_ingredient_fictif":   1.0,
    "derniere_etape_inutile":          0.5,
}


def score_recipe(r: dict, issues: list[str] | None = None) -> float:
    if issues is None:
        issues = detect_issues(r)
    penalty = sum(_SCORE_PENALTIES.get(i, 0.0) for i in issues)
    return round(max(0.0, 10.0 - penalty), 2)


def score_label(score: float) -> str:
    if score >= 9.5: return "🟢 excellent"
    if score >= 8.5: return "🟡 bon"
    if score >= 7.0: return "🟠 moyen"
    if score >= 5.5: return "🔴 faible"
    return "⛔ critique"


# ===================== PROMPT SYSTÈME =====================

CHEF_SYSTEM = """\
Tu es un chef cuisinier français professionnel, passionné, rigoureux et pédagogue, avec plus de 15 ans d'expérience dans la cuisine végétarienne et végétalienne créative et savoureuse.

Ton style est élégant, précis, chaleureux et naturel. Tu rédiges comme si tu expliquais à un élève motivé et exigeant.

═══ CONTEXTE FONDAMENTAL ═══

⚠️  TOUTES LES RECETTES DE CE CATALOGUE SONT AU MINIMUM VÉGÉTARIENNES.
Il n'y a aucune viande, aucun poisson, aucun fruit de mer dans aucune recette.
Les ingrédients d'origine animale autorisés en mode végétarien (non vegan) sont :
  ✓ Produits laitiers (lait, crème, beurre, fromage, yaourt…)
  ✓ Œufs
  ✓ Miel
Ne remplace JAMAIS ces ingrédients sauf si `is_vegan_recipe` est `true`.

═══ RÈGLES ABSOLUES ═══

① RÉGIME — LIS `is_vegan_recipe` AVANT TOUT

   SI `is_vegan_recipe` est `true` (recette VEGAN) :
   • La recette ne doit contenir AUCUN produit d'origine animale.
   • Remplace tout produit animal dans description ET instructions :
       lait → lait de coco ou lait d'avoine
       crème / crème fraîche → crème de coco
       fromage / parmesan → fromage végétal râpé ou levure nutritionnelle
       beurre → huile de coco ou huile d'olive
       yaourt → yaourt de coco
       miel → sirop d'érable ou agave
       œuf (liant) → œuf de lin (1 c. à soupe graines + 3 c. à soupe eau)
   • Si un flag "BLOQUANT" ou "vegan_alert" est signalé, corrige impérativement.

   SI `is_vegan_recipe` est `false` (recette VÉGÉTARIENNE) :
   • NE REMPLACE PAS les produits laitiers, œufs, fromage, beurre, miel.
   • Ces ingrédients sont légitimes et attendus dans ce contexte.

② DESCRIPTION — RÈGLES STRICTES
   • Longueur : STRICTEMENT entre 150 et 250 caractères.
   • Si "description_courte" est dans audit_issues : la description actuelle est trop courte, allonge-la.
   • Si "description_longue" est dans audit_issues : la description actuelle dépasse 250 caractères, raccourcis-la.
   • Structure : technique principale → texture attendue → origine/contexte culinaire.
   • Aucun terme anglais (pas de "crispy", "bowl", "mix", "dash"…).
   • INTERDIT :
       ✗ « à base de [ingrédient EN] »
       ✗ « aux saveurs umami et profond »  /  « saveurs équilibrées » seul
       ✗ « Soupe [pays] à base de [ingr], aux saveurs X »
   • OBLIGATOIRE : ≥ 1 repère sensoriel CONCRET + ≥ 1 élément d'origine/technique.

   ⚠️  RÈGLE CRITIQUE — INGRÉDIENTS FICTIFS INTERDITS :
   La description NE PEUT mentionner QUE des ingrédients effectivement présents
   dans la liste "composition" de la recette. Il est STRICTEMENT INTERDIT de citer
   un ingrédient dans la description s'il n'apparaît pas dans la composition.
   Si "description_ingredient_fictif" est dans audit_issues, relis la composition
   et réécris la description en ne citant QUE des ingrédients présents.
   Exemples de violation :
     ✗ Description qui mentionne "citron" si citron absent de la composition
     ✗ Description qui mentionne "coriandre" si absent de la composition
     ✗ Description qui mentionne "piment" si piment absent de la composition

③ INSTRUCTIONS — QUALITÉ CHEF
   • 7–11 étapes pour un plat principal, 4–7 pour une entrée/base.
   • Chaque étape ≥ 120 caractères : action précise + repère (temps, texture, couleur) + quantité.
   • Four/gril mentionné → température °C OBLIGATOIRE.
   • INTERDIT en étape standalone : "Servir immédiatement." / "Vérifier la texture."

④ COUVERTURE INGRÉDIENTS
   • Chaque ingrédient de la composition (hors serving_suggestions) doit apparaître
     en français dans les instructions.
   • Si "ingredients_non_couverts" est dans le payload, utilise EXACTEMENT l'un des "noms_fr".

⑤ TIMING
   • Si "cook_min_issue" → fournis "cook_min_corrige" (entier, minutes).
   • Si "passive_time_manquant" → fournis "prep_passive_min_corrige" (entier, minutes).

⑥ INGRÉDIENTS GÉNÉRIQUES (si "upgradeable_ingredients" fourni)
   • Choisis le variant le PLUS COHÉRENT parmi "available_variants".
   • Tu ne peux choisir QUE parmi les variants listés.

⑦ NORMALISATION CANONIQUE (si "ingredients_canoniques" fourni)
   Pour chaque ingrédient listé, lis comment il est utilisé dans la recette et
   choisis l'option canonique dont les AXES correspondent :
     thermal_state=fresh  → ingrédient frais (thym frais, gingembre frais…)
     thermal_state=dried  → ingrédient séché/moulu (thym sec, gingembre en poudre…)
     cooking_state=raw    → cru, non transformé
     form=spice           → épice moulue/séchée
   RÈGLE FRAIS/SEC : si la recette parle de "brins", "feuilles", "ciselé" → fresh.
   Si "séché", "moulu", "poudre", "c. à café" → dried.
   Inclus le résultat dans "ingredient_canonical" :
     {"recipe_key_actuelle": "nutri_id/var_key_canonique"}

⑧ DERNIÈRE ÉTAPE — SERVICE CONCRET OBLIGATOIRE
   La dernière étape décrit COMMENT servir : température, contenant, garniture,
   accompagnement ou présentation visuelle.
   INTERDIT comme dernière étape :
     ✗ "Appréciez [description émotionnelle des saveurs]"
     ✗ "Savourez / Dégustez ce plat aux saveurs…"
     ✗ "Servir et partager avec plaisir, en savourant les saveurs…"
   → SUPPRIME ou REMPLACE ces étapes par une instruction de service concrète.
   EXEMPLES CORRECTS :
     ✓ "Servir aussitôt dans des bols préchauffés, garni de coriandre ciselée et
        d'un filet d'huile d'olive. Accompagner d'un pain pita tiède ou de riz basmati."
     ✓ "Démouler sur un plat de service, napper de sauce et découper en parts.
        Se déguste chaud ou tiède, accompagné d'une salade verte."

⑨ SUGGESTIONS DE SERVICE — serving_suggestions (NOUVEAU)
   En plus de réécrire la recette, tu peux proposer 1 à 4 ingrédients optionnels
   d'accompagnement ou de service que l'utilisateur pourra CHOISIR d'ajouter.
   Ces suggestions enrichissent l'expérience sans modifier la recette de base.

   FORMAT : champ "serving_suggestions" dans la réponse, liste d'objets :
   [
     {
       "ingredient_fr": "coriandre fraîche ciselée",
       "ingredient_key": "coriander",
       "role": "garnish",
       "note": "Quelques feuilles pour la fraîcheur",
       "quantity_suggestion": "1 poignée",
       "optional": true
     }
   ]
   Rôles possibles : "garnish", "sauce", "side_dish", "condiment", "bread", "beverage"
   RÈGLES :
   • Ne propose QUE des accompagnements qui ont du sens culinaire réel pour ce plat.
   • 1–4 suggestions maximum — ne surcharge pas.
   • Les serving_suggestions NE sont PAS dans les instructions, juste proposées.
   • ingredient_key doit être une clé valide en snake_case (ex: "lemon_juice", "fresh_mint").
   • Si aucun accompagnement pertinent, omets le champ.

═══ FORMAT DE RÉPONSE ═══
JSON valide UNIQUEMENT, aucun texte avant/après :
{
  "recipes": [
    {
      "id": "...",
      "description": "...",
      "instructions": ["Étape 1 : ...", "Étape 2 : ..."],
      "serving_suggestions": [
        {
          "ingredient_fr": "...",
          "ingredient_key": "...",
          "role": "garnish",
          "note": "...",
          "quantity_suggestion": "...",
          "optional": true
        }
      ],
      "ingredient_canonical": {"recipe_key": "nutri_id/var_key"},
      "cook_min_corrige": 25,
      "prep_passive_min_corrige": 60,
      "ingredient_variants": {"ing_key": "variant_key"},
      "note": "Résumé des corrections effectuées"
    }
  ]
}
(serving_suggestions, ingredient_canonical, cook_min_corrige,
 prep_passive_min_corrige et ingredient_variants sont optionnels)
"""


# ===================== API CALLS =====================

def call_groq(batch_data: list, api_key: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model":       "llama-3.3-70b-versatile",
        "temperature": TEMPERATURE,
        "max_tokens":  8000,
        "messages": [
            {"role": "system", "content": CHEF_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Réécris ces recettes en corrigeant TOUS les problèmes signalés "
                    "dans le champ \"audit_issues\" de chaque recette :\n\n"
                    + json.dumps(batch_data, ensure_ascii=False, indent=2)
                )
            }
        ]
    }
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent":    "Mozilla/5.0 (compatible; ALIM-Chef/7.0)",
    }
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]


def call_anthropic(batch_data: list, api_key: str) -> str:
    url = "https://api.anthropic.com/v1/messages"
    payload = {
        "model":      "claude-sonnet-4-20250514",
        "max_tokens": 8000,
        "system":     CHEF_SYSTEM,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Réécris ces recettes en corrigeant TOUS les problèmes signalés "
                    "dans le champ \"audit_issues\" de chaque recette :\n\n"
                    + json.dumps(batch_data, ensure_ascii=False, indent=2)
                )
            }
        ]
    }
    headers = {
        "Content-Type":      "application/json",
        "x-api-key":         api_key,
        "anthropic-version": "2023-06-01",
    }
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        text_blocks = [b["text"] for b in result.get("content", []) if b.get("type") == "text"]
        return "\n".join(text_blocks)


# ===================== PARSING =====================

def parse_response(text: str) -> dict | None:
    m = re.search(r'```json\s*([\s\S]*?)```', text)
    if m:
        try: return json.loads(m.group(1))
        except json.JSONDecodeError: pass
    m = re.search(r'(\{"recipes"\s*:[\s\S]*\})', text)
    if m:
        try: return json.loads(m.group(1))
        except json.JSONDecodeError: pass
    m = re.search(r'(\{[\s\S]+\})', text)
    if m:
        try: return json.loads(m.group(1))
        except json.JSONDecodeError: pass
    return None


# ===================== CHARGEMENT =====================

def load_recipes(path: Path) -> tuple[list, dict | list, bool]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data, data, True
    return data.get("recipes", []), data, False


def load_recipes_safe(path: Path) -> tuple[list, dict | list, bool] | None:
    try:
        return load_recipes(path)
    except json.JSONDecodeError as e:
        print(f"⚠️  Fichier de sortie corrompu ({path.name}) — ignoré : {e}")
        backup = path.with_suffix(".corrupted.json")
        try:
            path.rename(backup)
            print(f"   → Corrompu sauvegardé sous : {backup.name}")
        except Exception:
            pass
        return None


# ===================== BUILD BATCH ITEM =====================

def _recipe_is_vegan(r: dict) -> bool:
    flags    = r.get("_flags", []) or []
    # vegan_flag_but_animal = recette marquée vegan MAIS contient du contenu animal
    # → on ne la traite PAS comme vegan pour éviter des substitutions incorrectes
    if any("vegan_flag_but_animal" in f for f in flags):
        return False
    if r.get("diet_flags", {}).get("vegan", False):
        return True
    titles   = r.get("titles") or {}
    title_fr = titles.get("fr", "").lower()
    title_en = titles.get("en", "").lower()
    return (
        "vegan" in title_fr or "végan" in title_fr or "vegan" in title_en
        or any("vegan_alert" in f for f in flags)
    )


def build_batch_item(r: dict, issues: list[str]) -> dict:
    # Composition : séparer les ingrédients actifs des serving_suggestions existantes
    comp_active = [
        {
            "ingredient": c.get("ingredient"),
            "quantity":   c.get("quantity"),
            "unit":       c.get("unit"),
        }
        for c in r.get("composition", [])
        if c.get("meta", {}).get("role") != "serving_suggestion"
    ]

    item = {
        "id":              r["id"],
        "titles":          r.get("titles"),
        "description":     r.get("description"),
        "composition":     comp_active,
        "instructions":    r.get("instructions"),
        "audit_issues":    issues,
        "is_vegan_recipe": _recipe_is_vegan(r),
    }

    # Timing
    timing          = r.get("timing", {})
    title_fr        = (r.get("titles") or {}).get("fr", "").lower()
    cook_min_val    = timing.get("cook_min", -1)
    passive_min_val = timing.get("prep_passive_min", 0) or 0
    is_legitimate_zero = cook_min_val == 0 and any(
        re.search(pat, title_fr, re.IGNORECASE)
        for pat in COOK_ZERO_LEGITIMATE_PATTERNS
    )
    needs_timing = (
        "four_sans_temp" in issues
        or "etapes_vagues" in issues
        or "passive_time_manquant" in issues
        or (cook_min_val == 0 and not is_legitimate_zero)
    )
    if needs_timing:
        item["timing"] = {
            "cook_min":         cook_min_val,
            "prep_passive_min": passive_min_val,
            "total_min":        timing.get("total_min"),
        }
        if cook_min_val == 0 and not is_legitimate_zero:
            item["cook_min_issue"] = True
        if "passive_time_manquant" in issues:
            item["passive_time_issue"] = True

    flags = r.get("_flags", [])
    if flags:
        item["_flags"] = flags

    # Ingrédients génériques
    if "ingredients_generiques" in issues and _VARIANT_INDEX is not None:
        upgradeable, missing = analyze_generic_ingredients(r)
        if upgradeable:
            item["upgradeable_ingredients"] = [
                {
                    "ing_key":            u["ing_key"],
                    "base_key":           u["base_key"],
                    "available_variants": u["available_variants"],
                }
                for u in upgradeable
            ]
        if missing:
            item["_missing_variants"] = missing

    # Ingrédients non couverts dans les instructions
    if "ingredients_non_couverts" in issues:
        instr_lower  = " ".join(r.get("instructions", [])).lower()
        non_couverts = []
        for c in r.get("composition", []):
            if c.get("meta", {}).get("role") == "serving_suggestion":
                continue
            ing_key  = c.get("ingredient", "")
            fr_terms = INGREDIENT_FR_MAP.get(ing_key)
            if not fr_terms:
                continue
            if not any(term.lower() in instr_lower for term in fr_terms):
                non_couverts.append({"ing_key": ing_key, "noms_fr": fr_terms})
        if non_couverts:
            item["ingredients_non_couverts"] = non_couverts

    # v7 — normalisation canonique
    if "ingredient_noncanonique" in issues and _CANONICAL_INDEX is not None:
        noncanon = _get_noncanonical_ingredients(r)
        if noncanon:
            payload_canon = []
            for nc in noncanon:
                entry = {
                    "recipe_key": nc["recipe_key"],
                    "flag":       nc["flag"],
                    "options": [
                        {
                            "canonical": opt["canonical"],
                            "axes":      opt["axes"],
                            "name_fr":   opt["name_fr"],
                        }
                        for opt in nc["options"]
                    ],
                }
                if "fresh_dry_pair" in nc:
                    entry["fresh_dry_pair"] = nc["fresh_dry_pair"]
                payload_canon.append(entry)
            item["ingredients_canoniques"] = payload_canon

    # v7 — signal description fictive : liste des ingrédients de la composition
    if "description_ingredient_fictif" in issues:
        comp_fr = []
        for c in r.get("composition", []):
            if c.get("meta", {}).get("role") == "serving_suggestion":
                continue
            ing_key  = c.get("ingredient", "")
            fr_terms = INGREDIENT_FR_MAP.get(ing_key, [])
            if fr_terms:
                comp_fr.append({"ingredient_key": ing_key, "noms_fr_valides": fr_terms})
        item["composition_fr_autorisee"] = comp_fr

    # v7 — signal étape nunuche
    if "derniere_etape_inutile" in issues:
        item["derniere_etape_signal"] = True

    return item


# ===================== VALIDATION SERVING SUGGESTIONS =====================

_VALID_SS_ROLES = {"garnish", "sauce", "side_dish", "condiment", "bread", "beverage"}


def _validate_serving_suggestions(suggestions: list) -> tuple[list, list]:
    """Valide et nettoie les serving_suggestions retournées par le LLM."""
    valid   = []
    invalid = []
    for s in suggestions:
        if not isinstance(s, dict):
            invalid.append(str(s))
            continue
        ing_fr  = s.get("ingredient_fr", "").strip()
        ing_key = s.get("ingredient_key", "").strip()
        role    = s.get("role", "garnish")
        if not ing_fr or not ing_key:
            invalid.append(f"missing fields: {s}")
            continue
        if role not in _VALID_SS_ROLES:
            role = "garnish"
        valid.append({
            "ingredient_fr":        ing_fr,
            "ingredient_key":       re.sub(r"[^a-z0-9_]", "_", ing_key.lower()),
            "role":                 role,
            "note":                 s.get("note", ""),
            "quantity_suggestion":  s.get("quantity_suggestion", ""),
            "optional":             True,
        })
    return valid, invalid


# ===================== FUSION & SAUVEGARDE =====================

def _validate_canonical(canonical: str) -> bool:
    if not _N2_FULL or "/" not in canonical:
        return False
    base, var = canonical.split("/", 1)
    return base in _N2_FULL and var in _N2_FULL[base].get("variants", {})


def merge_and_save(
    recipes: list,
    processed: dict,
    output_path: Path,
    data: dict | list,
    data_is_list: bool,
) -> int:
    today     = str(datetime.now().date())
    log_entry = f"chef_rewrite_v7.1_{today}"
    updated   = 0

    for r in recipes:
        patch = processed.get(r["id"])
        if not patch:
            continue

        r["description"]  = patch.get("description",  r.get("description"))
        r["instructions"] = patch.get("instructions", r.get("instructions"))

        # Nettoyage post-traitement : retirer étape nunuche si subsiste
        instrs = r.get("instructions") or []
        if instrs and _is_nunuche_step(instrs[-1]):
            r["instructions"] = instrs[:-1]
            r.setdefault("_corrections_log", [])
            if f"nunuche_step_removed_{today}" not in r["_corrections_log"]:
                r["_corrections_log"].append(f"nunuche_step_removed_{today}")

        # cook_min
        if "cook_min_corrige" in patch:
            try:
                new_cook = int(patch["cook_min_corrige"])
                timing   = r.setdefault("timing", {})
                old_cook = timing.get("cook_min", 0)
                timing["cook_min"] = new_cook
                r["_flags"] = [f for f in r.get("_flags", []) if "cook_zero" not in f]
                if "cook_min_correction" not in r:
                    r["cook_min_correction"] = {"from": old_cook, "to": new_cook, "by": log_entry}
            except (ValueError, TypeError):
                pass

        # prep_passive_min
        if "prep_passive_min_corrige" in patch:
            try:
                new_passive = int(patch["prep_passive_min_corrige"])
                timing      = r.setdefault("timing", {})
                old_passive = timing.get("prep_passive_min", 0) or 0
                timing["prep_passive_min"] = new_passive
                r["_flags"] = [f for f in r.get("_flags", []) if "passive_time" not in f]
                if "prep_passive_correction" not in r:
                    r["prep_passive_correction"] = {
                        "from": old_passive, "to": new_passive, "by": log_entry
                    }
            except (ValueError, TypeError):
                pass

        # Recalcul total_min une seule fois après les deux corrections éventuelles
        if "cook_min_corrige" in patch or "prep_passive_min_corrige" in patch:
            timing       = r.setdefault("timing", {})
            prep_active  = timing.get("prep_active_min",  0) or 0
            prep_passive = timing.get("prep_passive_min", 0) or 0
            cook         = timing.get("cook_min",         0) or 0
            timing["total_min"] = prep_active + prep_passive + cook

        # v7 — serving_suggestions : ajouter à la composition avec role=serving_suggestion
        raw_suggestions = patch.get("serving_suggestions", [])
        if raw_suggestions and isinstance(raw_suggestions, list):
            valid_ss, rejected_ss = _validate_serving_suggestions(raw_suggestions)
            if valid_ss:
                # Retirer les anciennes serving_suggestions existantes (remplacées)
                r["composition"] = [
                    c for c in r.get("composition", [])
                    if c.get("meta", {}).get("role") != "serving_suggestion"
                ]
                for ss in valid_ss:
                    r["composition"].append({
                        "ingredient":    ss["ingredient_key"],
                        "quantity":      None,
                        "unit":          ss.get("quantity_suggestion") or None,
                        "meta": {
                            "role":                 "serving_suggestion",
                            "ingredient_fr":        ss["ingredient_fr"],
                            "note":                 ss["note"],
                            "optional":             True,
                            "added_by":             log_entry,
                        }
                    })
                r.setdefault("_serving_suggestions_log", []).append({
                    "by":      log_entry,
                    "added":   [s["ingredient_fr"] for s in valid_ss],
                })
            if rejected_ss:
                r.setdefault("_serving_suggestions_rejected", []).extend(rejected_ss)

        # v7 — normalisation canonique
        ing_canonical = patch.get("ingredient_canonical", {})
        if ing_canonical and _N2_FULL:
            applied_canon  = []
            rejected_canon = []
            for c in r.get("composition", []):
                if c.get("meta", {}).get("role") == "serving_suggestion":
                    continue
                old_key = c.get("ingredient", "")
                if old_key not in ing_canonical:
                    continue
                new_canon = ing_canonical[old_key]
                if not _validate_canonical(new_canon):
                    rejected_canon.append(f"{old_key}→{new_canon} (non valide dans n2)")
                    continue
                base, var = new_canon.split("/", 1)
                var_data  = _N2_FULL[base]["variants"][var]
                c["ingredient"]       = new_canon
                c["_nutri_canonical"] = True
                c["variant"]          = var
                c["variant_name_fr"]  = var_data.get("name_fr", "")
                applied_canon.append(f"{old_key} → {new_canon}")
            if applied_canon:
                r.setdefault("_canonical_log", []).append({
                    "by": log_entry, "applied": applied_canon
                })
            if rejected_canon:
                r.setdefault("_canonical_rejected", []).extend(rejected_canon)

        # Variants ingrédients (mécanisme v6 conservé)
        ing_variants = patch.get("ingredient_variants", {})
        if ing_variants and _VARIANT_INDEX is not None:
            applied  = []
            rejected = []
            for c in r.get("composition", []):
                if c.get("meta", {}).get("role") == "serving_suggestion":
                    continue
                ing_key = c.get("ingredient", "")
                if ing_key not in ing_variants:
                    continue
                chosen_var = ing_variants[ing_key]
                resolved   = resolve_ingredient_to_base(ing_key)
                if resolved is None:
                    rejected.append(f"{ing_key}→{chosen_var} (base inconnue)")
                    continue
                base_key, _ = resolved
                available   = get_available_variants(base_key)
                if chosen_var not in available:
                    rejected.append(f"{ing_key}→{chosen_var} (variant hors index)")
                    continue
                old_ing = c["ingredient"]
                c["ingredient"]      = f"{base_key}/{chosen_var}"
                c["variant"]         = chosen_var
                c["variant_name_fr"] = available[chosen_var]
                applied.append(f"{old_ing} → {c['ingredient']} ({available[chosen_var]})")
            if applied:
                r.setdefault("_ingredient_variants_log", []).append({
                    "by": log_entry, "applied": applied
                })
            if rejected:
                r.setdefault("_ingredient_variants_rejected", []).extend(rejected)

        # Missing variants payload
        for m in patch.get("_missing_variants_payload", []):
            r.setdefault("_missing_variants", [])
            if m not in r["_missing_variants"]:
                r["_missing_variants"].append(m)

        if "_corrections_log" not in r:
            r["_corrections_log"] = []
        if log_entry not in r["_corrections_log"]:
            r["_corrections_log"].append(log_entry)

        updated += 1

    output_data = recipes if data_is_list else data
    tmp_path    = output_path.with_suffix(".tmp.json")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(output_path)
    return updated


# ===================== RAPPORT =====================

def print_audit_report(
    recipes: list,
    eligible_ids: set,
    processed: set,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD,
) -> None:
    print("\n" + "─" * 65)
    print("📊 RAPPORT FINAL v7.1")
    print("─" * 65)

    counts     = {k: 0 for k in _SCORE_PENALTIES}
    all_scores = []
    below_threshold = []

    for r in recipes:
        issues = detect_issues(r)
        sc     = score_recipe(r, issues)
        all_scores.append(sc)
        for issue in issues:
            counts[issue] = counts.get(issue, 0) + 1
        if sc < score_threshold:
            below_threshold.append((sc, r))

    labels = {
        "description_auto":                "Descriptions auto-générées",
        "description_courte":              f"Descriptions < {DESC_MIN_LEN} chars",
        "description_longue":              "Descriptions > 250 chars (v7.1)",
        "etapes_vagues":                   f"Recettes ≥{MIN_VAGUE_STEPS} étapes vagues (<{STEP_MIN_LEN}c)",
        "four_sans_temp":                  "Four/gril sans température °C",
        "generique":                       "Formules génériques standalone",
        "flags_bloquants":                 "Flags bloquants / vegan alerts",
        "ingredients_generiques":          "Ingrédients génériques améliorables",
        "ingredients_non_couverts":        "Ingrédients non couverts dans instructions",
        "ingredient_noncanonique":         "Clés hors format nutri_id/var_key (v7)",
        "description_ingredient_fictif":   "Descriptions citant un ingrédient absent (v7)",
        "derniere_etape_inutile":          "Étape finale appréciation sans service (v7)",
        "passive_time_manquant":           "Levée sans prep_passive_min",
    }
    for k, label in labels.items():
        cnt = counts.get(k, 0)
        if cnt:
            print(f"  {label:<54} : {cnt}")

    print()
    print("  Distribution des scores :")
    thresholds   = [10.0, 9.5, 9.0, 8.5, 8.0, 7.5, 7.0, 5.5, 0.0]
    labels_score = ["10.0", "9.5–9.9", "9.0–9.4", "8.5–8.9", "8.0–8.4",
                    "7.5–7.9", "7.0–7.4", "5.5–6.9", "< 5.5"]
    bands = [0] * len(thresholds)
    for sc in all_scores:
        for i, t in enumerate(thresholds):
            if sc >= t:
                bands[i] += 1
                break
        else:
            bands[-1] += 1
    for label, count in zip(labels_score, bands):
        bar = "█" * (count // 5)
        print(f"    {label:<8} : {count:>4}  {bar}")

    avg = sum(all_scores) / len(all_scores) if all_scores else 0
    print(f"\n  Score moyen global        : {avg:.2f}/10")
    print(f"  Recettes ≥ {score_threshold}            : {sum(1 for s in all_scores if s >= score_threshold)}")
    print(f"  Recettes < {score_threshold} (à traiter) : {len(below_threshold)}")

    if below_threshold:
        below_threshold.sort(key=lambda x: x[0])
        print(f"\n  Top 10 pires recettes restantes :")
        for sc, r in below_threshold[:10]:
            title  = r.get("titles", {}).get("fr", r["id"])
            issues = detect_issues(r)
            print(f"    {sc:.1f}  {score_label(sc)}  {title[:40]:<40}  [{', '.join(issues)}]")

    # Stats v7
    total_canon     = sum(len(r.get("_canonical_log", [])) for r in recipes)
    total_ss        = sum(len(r.get("_serving_suggestions_log", [])) for r in recipes)
    nunuche_removed = sum(
        1 for r in recipes
        if any("nunuche_step_removed" in (l or "") for l in r.get("_corrections_log", []))
    )
    if total_canon or total_ss or nunuche_removed:
        print()
        if total_canon:
            print(f"  {'Corrections canoniques appliquées':<44} : {total_canon}")
        if total_ss:
            print(f"  {'Recettes avec serving_suggestions ajoutées':<44} : {total_ss}")
        if nunuche_removed:
            print(f"  {'Étapes nunuche supprimées':<44} : {nunuche_removed}")

    total_var_applied  = sum(len(r.get("_ingredient_variants_log", [])) for r in recipes)
    total_var_rejected = sum(len(r.get("_ingredient_variants_rejected", [])) for r in recipes)
    total_missing      = sum(len(r.get("_missing_variants", [])) for r in recipes)
    if total_var_applied or total_var_rejected or total_missing:
        print()
        if total_var_applied:
            print(f"  {'Variants ingrédients appliqués':<44} : {total_var_applied}")
        if total_var_rejected:
            print(f"  {'Variants rejetés (hors index)':<44} : {total_var_rejected}")
        if total_missing:
            print(f"  {'Ingrédients hors index':<44} : {total_missing}")

    print(f"\n  Éligibles traités dans ce run : {len(processed & eligible_ids)} / {len(eligible_ids)}")
    print("─" * 65)


# ===================== MAIN =====================

def main():
    parser = argparse.ArgumentParser(
        description="Réécriture chef v7.1 — bugfixes canonical/vegan/scoring + description_longue"
    )
    parser.add_argument("--key",             default=None, help="Clé API Groq (gsk_...)")
    parser.add_argument("--key-anthropic",   default=None, help="Clé API Anthropic (sk-ant-...)")
    parser.add_argument("--mode",            choices=["groq", "anthropic"], default="groq")
    parser.add_argument("--input",           default="recipes.json")
    parser.add_argument("--nutrition",       default=None, help="nutrition_v2.json")
    parser.add_argument("--ingredient-map",  default=None,
                        help="ingredient_map_YYYY-MM-DD.json")
    parser.add_argument("--recipes-ref",     default=None)
    parser.add_argument("--score-threshold", type=float, default=DEFAULT_SCORE_THRESHOLD)
    parser.add_argument("--target",
                        choices=["all", "description_auto", "description_courte",
                                 "description_longue",
                                 "etapes_vagues", "four_sans_temp", "generique",
                                 "flags_bloquants", "ingredients_generiques",
                                 "ingredients_non_couverts", "passive_time_manquant",
                                 "ingredient_noncanonique", "description_ingredient_fictif",
                                 "derniere_etape_inutile"],
                        default="all")
    parser.add_argument("--limit",           type=int, default=0)
    parser.add_argument("--dry-run",         action="store_true")
    parser.add_argument("--show-scores",     action="store_true")
    parser.add_argument("--clean-progress",  action="store_true")
    parser.add_argument("--repair-progress", action="store_true")
    parser.add_argument("--report",          action="store_true")
    args = parser.parse_args()

    # ── Chargement index ─────────────────────────────────────────────
    if args.nutrition or args.recipes_ref or args.ingredient_map:
        init_variant_index(args.nutrition, args.recipes_ref, args.ingredient_map)
    else:
        print("ℹ️  --nutrition non fourni : détecteurs avancés désactivés")

    if not args.ingredient_map:
        print("ℹ️  --ingredient-map non fourni : normalisation canonique v7 désactivée")

    # Validation clé API
    if not args.dry_run and not args.report and not args.clean_progress and not args.repair_progress:
        if args.mode == "groq" and not args.key:
            print("❌ --key requis pour le mode groq"); sys.exit(1)
        if args.mode == "anthropic" and not args.key_anthropic:
            print("❌ --key-anthropic requis pour le mode anthropic"); sys.exit(1)

    input_path    = Path(args.input)
    output_path   = input_path.with_name(input_path.stem + OUTPUT_SUFFIX)
    progress_path = input_path.with_name(input_path.stem + PROGRESS_SUFFIX)

    if args.clean_progress:
        if progress_path.exists():
            progress_path.unlink()
            print(f"🗑  Progression supprimée : {progress_path.name}")
        else:
            print("ℹ  Aucun fichier de progression à supprimer.")
        sys.exit(0)

    if args.repair_progress:
        if not output_path.exists():
            print(f"❌ Aucun fichier de sortie trouvé : {output_path.name}"); sys.exit(1)
        result = load_recipes_safe(output_path)
        if result is None:
            print("❌ Fichier de sortie illisible."); sys.exit(1)
        out_recipes, _, _ = result
        progress = {}
        for r in out_recipes:
            if not r.get("_corrections_log"):
                continue
            entry = {"id": r["id"], "description": r.get("description", ""),
                     "instructions": r.get("instructions", [])}
            if "cook_min_correction" in r:
                entry["cook_min_corrige"] = r["cook_min_correction"]["to"]
            progress[r["id"]] = entry
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        print(f"✅ Progression reconstruite : {len(progress)} → {progress_path.name}")
        sys.exit(0)

    if not input_path.exists():
        print(f"❌ Fichier non trouvé : {input_path}"); sys.exit(1)

    source_recipes, _, _ = load_recipes(input_path)
    print(f"📊 {len(source_recipes)} recettes dans la source")

    if output_path.exists():
        print(f"♻️  Sortie existante — utilisée comme base : {output_path.name}")
        _loaded = load_recipes_safe(output_path)
        if _loaded is not None:
            recipes, data, data_is_list = _loaded
        else:
            print("🔄 Bascule sur la source après corruption.")
            _, data, data_is_list = load_recipes(input_path)
            recipes = source_recipes
    else:
        print("🆕 Démarrage depuis la source.")
        _, data, data_is_list = load_recipes(input_path)
        recipes = source_recipes

    recipe_index       = {r["id"]: r for r in recipes}
    recipe_index_lower = {k.lower(): k for k in recipe_index}
    source_index       = {r["id"]: r for r in source_recipes}

    if args.report:
        eligible_report: dict[str, tuple[list[str], float]] = {}
        for r in recipes:
            issues = detect_issues(r)
            if issues:
                eligible_report[r["id"]] = (issues, score_recipe(r, issues))
        processed_report = {
            r["id"] for r in recipes if r.get("_corrections_log")
        }
        print_audit_report(
            recipes,
            set(eligible_report.keys()),
            processed_report,
            args.score_threshold,
        )
        sys.exit(0)

    # ── Détection des éligibles ──────────────────────────────────────
    eligible: dict[str, tuple[list[str], float]] = {}
    for r in recipes:
        issues = detect_issues(r)
        if not issues:
            continue
        if args.target != "all" and args.target not in issues:
            continue
        sc = score_recipe(r, issues)
        if sc >= args.score_threshold:
            continue
        eligible[r["id"]] = (issues, sc)

    eligible_ids = set(eligible.keys())
    print(f"🎯 Score seuil : < {args.score_threshold}/10")
    print(f"🔍 {len(eligible_ids)} recettes éligibles")

    type_counts: dict[str, int] = {}
    for issues, _ in eligible.values():
        for i in issues:
            type_counts[i] = type_counts.get(i, 0) + 1
    for k, v in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"   • {k:<44} : {v}")

    if not eligible_ids:
        print(f"✅ Aucune recette sous {args.score_threshold}/10.")
        sys.exit(0)

    if args.dry_run:
        sorted_eligible = sorted(eligible.items(), key=lambda x: x[1][1])
        print(f"\n── DRY RUN — {len(eligible_ids)} recettes ──")
        for rid, (issues, sc) in sorted_eligible:
            r     = recipe_index.get(rid, {})
            title = r.get("titles", {}).get("fr", rid)
            si    = f"  [{sc:.1f}]" if args.show_scores else ""
            print(f"  {si} [{', '.join(issues)}] {title}")
        sys.exit(0)

    # ── Chargement progression ───────────────────────────────────────
    processed: dict = {}
    if progress_path.exists():
        with open(progress_path, encoding="utf-8") as f:
            raw_progress = json.load(f)
        processed = {k: v for k, v in raw_progress.items() if k in eligible_ids}
        orphans   = len(raw_progress) - len(processed)
        msg = f"🔁 Reprise — {len(processed)} recettes déjà traitées"
        if orphans:
            msg += f" ({orphans} IDs orphelins ignorés)"
        print(msg)
    else:
        print("🆕 Aucun fichier de progression — démarrage complet.")

    # ── Recettes restantes ───────────────────────────────────────────
    to_process = [
        (rid, eligible[rid][0], eligible[rid][1])
        for rid in eligible_ids if rid not in processed
    ]
    PRIORITY = {
        "description_auto":               0,
        "flags_bloquants":                1,
        "four_sans_temp":                 2,
        "passive_time_manquant":          2,
        "description_courte":             3,
        "description_ingredient_fictif":  3,
        "etapes_vagues":                  4,
        "generique":                      5,
        "ingredient_noncanonique":        5,
        "derniere_etape_inutile":         6,
        "ingredients_non_couverts":       6,
        "ingredients_generiques":         7,
    }
    to_process.sort(key=lambda x: (x[2], min(PRIORITY.get(i, 9) for i in x[1])))

    if args.limit > 0:
        to_process = to_process[:args.limit]
        print(f"⚠️  Limité à {args.limit} recettes (--limit)")

    print(f"⏭  {len(to_process)} recettes restantes à traiter")
    if not to_process:
        print("✅ Toutes les recettes éligibles ont été traitées.")

    def call_api(batch_data: list) -> str:
        if args.mode == "anthropic":
            return call_anthropic(batch_data, args.key_anthropic)
        return call_groq(batch_data, args.key)

    # ── Boucle principale ────────────────────────────────────────────
    total_lots      = (len(to_process) + BATCH_SIZE - 1) // BATCH_SIZE if to_process else 0
    newly_processed = set()

    for lot_i, (rid, issues, sc) in enumerate(to_process, start=1):
        r = recipe_index.get(rid) or source_index.get(rid)
        if not r:
            print(f"   ⚠ ID {rid} introuvable — ignoré")
            continue

        title = r.get("titles", {}).get("fr", rid)
        print(f"\n🔄 {lot_i}/{total_lots} — {title}  [{sc:.1f}/10 {score_label(sc)}]")
        print(f"   Issues : {', '.join(issues)}")

        batch_data = [build_batch_item(r, issues)]
        success    = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                text   = call_api(batch_data)
                result = parse_response(text)
                if result is None:
                    raise ValueError("Impossible d'extraire un JSON valide")

                for item in result.get("recipes", []):
                    item_id = item.get("id", "")
                    if item_id not in recipe_index:
                        canonical_id = recipe_index_lower.get(item_id.lower())
                        if canonical_id:
                            print(f"   ℹ️  ID normalisé : '{item_id}' → '{canonical_id}'")
                            item["id"] = canonical_id
                            item_id    = canonical_id
                        else:
                            print(f"   ⚠️  ID inconnu ignoré : '{item_id}'")
                            continue

                    new_desc = item.get("description", "")
                    if len(new_desc) < DESC_MIN_LEN:
                        print(f"   ⚠️  Description trop courte ({len(new_desc)} chars)")

                    batch_item        = batch_data[0] if batch_data else {}
                    missing_in_payload = batch_item.get("_missing_variants", [])
                    if missing_in_payload:
                        item["_missing_variants_payload"] = missing_in_payload

                    processed[item_id] = item
                    newly_processed.add(item_id)

                success    = True
                first_item = result.get("recipes", [{}])[0]
                note       = first_item.get("note", "")
                cook_fix   = first_item.get("cook_min_corrige")
                ing_vars   = first_item.get("ingredient_variants", {})
                ing_canon  = first_item.get("ingredient_canonical", {})
                ss_count   = len(first_item.get("serving_suggestions", []))
                status = f"✅ Lot {lot_i} OK (tentative {attempt})"
                if cook_fix is not None:
                    status += f" | cook_min → {cook_fix} min"
                if ing_vars:
                    status += f" | {len(ing_vars)} variant(s)"
                if ing_canon:
                    status += f" | {len(ing_canon)} canonical(s)"
                if ss_count:
                    status += f" | {ss_count} serving_suggestion(s)"
                if note:
                    status += f" | {note[:60]}"
                print(f"   {status}")
                break

            except urllib.error.HTTPError as e:
                if e.code == 429:
                    wait = min(30 * attempt, 180)
                    print(f"   ⏳ Rate limit 429 — attente {wait}s...")
                    time.sleep(wait)
                else:
                    print(f"   ⚠ Tentative {attempt}/{MAX_RETRIES} — HTTP {e.code}: {e}")
                    if attempt < MAX_RETRIES:
                        time.sleep(2 * attempt)
            except Exception as e:
                print(f"   ⚠ Tentative {attempt}/{MAX_RETRIES} échouée : {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(2 * attempt)

        if not success:
            print(f"   ❌ Définitivement échoué — recette ignorée : {rid}")
        else:
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(processed, f, ensure_ascii=False, indent=2)
            merge_and_save(recipes, processed, output_path, data, data_is_list)
            print(f"   💾 {len(processed)} / {len(eligible_ids)} sauvegardées → {output_path.name}")
            time.sleep(DELAY_S)

    # ── Fusion finale ────────────────────────────────────────────────
    print("\n🔀 Fusion finale...")
    updated_count = merge_and_save(recipes, processed, output_path, data, data_is_list)
    print(f"✅ {updated_count} recettes mises à jour")
    print(f"   dont {len(newly_processed)} dans ce run")
    print(f"📁 Fichier de sortie : {output_path}")

    recipes_final, _, _ = load_recipes(output_path)
    print_audit_report(
        recipes_final, eligible_ids,
        newly_processed | set(processed.keys()),
        args.score_threshold,
    )
    print("\nℹ️  Progression conservée pour reprise éventuelle.")
    print(f"   Pour la supprimer : python rewrite_smart_v7.py --input {input_path} --clean-progress")


if __name__ == "__main__":
    main()
