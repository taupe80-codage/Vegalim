#!/usr/bin/env python3
"""
ALIM — Réécriture Chef v6.0

Améliorations vs v5.0
─────────────────────────────────────────────────────────────────────
v6.0 — Score-based filtering (cible : recettes < seuil de qualité)

  1. SCORING INTÉGRÉ (nouveau)
     Fonction score_recipe() retourne un score 0–10 par recette selon
     les problèmes détectés — utilisée pour filtrer les éligibles.
     Grille de pénalités :
       -2.5  description auto-générée (cluster umami, templates EN…)
       -1.5  description < DESC_MIN_LEN chars
       -0.5  description > 250 chars
       -1.5  ≥ MIN_VAGUE_STEPS étapes vagues (< STEP_MIN_LEN chars)
       -0.5  exactement 1 étape vague
       -1.0  four/gril sans température °C

  2. ARGUMENT --score-threshold (défaut 8.5)
     Seules les recettes avec un score STRICTEMENT INFÉRIEUR au seuil
     sont traitées. Permet de cibler exactement les recettes < 8.5.
     Exemple : --score-threshold 8.5  →  corrige toutes les < 8.5
               --score-threshold 10   →  toutes celles qui ont un problème
               --score-threshold 7.0  →  seulement les très dégradées

  3. RAPPORT ENRICHI
     - Score moyen avant/après run
     - Distribution des scores (par tranche de 0.5)
     - Classement des 10 pires recettes restantes

  4. --show-scores (nouveau)
     Affiche le score de chaque recette éligible en mode dry-run.

Historique
──────────
v6.1 — Fix vegan injection + prep_passive_min + eggplant FP + word-boundary matching
v5.0 — Correctifs audit v4 : cluster umami + seuils + mapping FR + whitelist
v4.1 — Ficelage variants ingrédients depuis nutrition_v2 + base_recipes
v4.0 — Détecteurs ciblés + prompt refondu + correction cook_min
v3.x — Base output si existant ; progression jamais supprimée ; backoff 429
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
BATCH_SIZE   = 1        # 1 recette par appel (qualité maximale)
DELAY_S      = 23       # secondes entre appels (Groq free tier ~3 req/min)
MAX_RETRIES  = 6
TEMPERATURE  = 0.60

# Seuils des détecteurs
DESC_MIN_LEN       = 150   # chars minimum description
STEP_MIN_LEN       = 120   # chars minimum par étape
MIN_VAGUE_STEPS    = 2     # nb d'étapes vagues minimum pour déclencher
STEP_GENERIC_MAX   = 80

# Seuil de score par défaut — recettes en dessous sont retraitées
DEFAULT_SCORE_THRESHOLD = 8.5

OUTPUT_SUFFIX   = "_chef_rewrite_smart.json"
PROGRESS_SUFFIX = ".rewrite_progress_smart.json"

# ===================== MAPPING INGRÉDIENT NORMALISÉ → NOMS FR =====================
# Construit dynamiquement depuis nutrition_v2 lors de l'appel à init_variant_index().
# Clés : base_key  ET  base_key/var_key  (ex: "lemon", "lemon/raw")
# Valeurs : liste des noms FR connus pour cet ingrédient/variant.
INGREDIENT_FR_MAP: dict[str, list[str]] = {}

# ===================== WHITELIST COOK_MIN=0 LÉGITIMES =====================
COOK_ZERO_LEGITIMATE_PATTERNS = [
    r'\bsorbet\b', r'\bcarpaccio\b', r'\bguacamole\b', r'\btartare\b',
    r'\bceviche\b', r'\bcrudités\b', r'\bgazpacho\b', r'\bsalade\b',
    r'\btaboulé\b', r'\bpanzanella\b',
    r'\bconcombre\b.{0,20}\bjaponaise?\b',
    r'\bcrème fraîche maison\b', r'\blait de coco maison\b',
]

# ===================== INDEX NUTRITION / BASE-RECETTES =====================
_VARIANT_INDEX: dict | None = None
_SK_INDEX:      dict | None = None
_ALIAS_INDEX:   dict | None = None


def _build_ingredient_fr_map() -> None:
    """Reconstruit INGREDIENT_FR_MAP depuis _VARIANT_INDEX (après chargement n2)."""
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
            # Clé précise : base_key/var_key
            full_key = f"{base_key}/{var_key}"
            entry = INGREDIENT_FR_MAP.setdefault(full_key, [])
            if name_fr not in entry:
                entry.append(name_fr)
            # Clé générique : base_key (union de tous les noms)
            if name_fr not in base_names:
                base_names.append(name_fr)
        if base_names:
            INGREDIENT_FR_MAP[base_key] = base_names


def init_variant_index(nutrition_path: str | None, recipes_ref_path: str | None) -> None:
    global _VARIANT_INDEX, _SK_INDEX, _ALIAS_INDEX
    _VARIANT_INDEX = {}
    _SK_INDEX      = {}
    _ALIAS_INDEX   = {}

    if nutrition_path:
        try:
            with open(nutrition_path, encoding="utf-8") as f:
                nutr = json.load(f)
            ingredients = nutr.get("ingredients", {})
            for base_key, entry in ingredients.items():
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
                  f"{sum(len(v) for v in _VARIANT_INDEX.values())} variants, "
                  f"{len(INGREDIENT_FR_MAP)} clés FR mappées")
        except Exception as e:
            print(f"⚠️  Impossible de charger nutrition : {e}")

    _BASE_DISH_TYPES = {"sauce", "condiment", "broth", "paste", "roux", "ingredient"}
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


# ===================== DÉTECTEURS D'ÉLIGIBILITÉ =====================

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
_COOKING_WORDS  = re.compile(
    r'\bcuire\b|\bfaire revenir\b|\bfeu (vif|moyen|doux)\b|\bcuisson thermique\b|\bblanchir\b|\bsauter\b',
    re.IGNORECASE
)


def detect_issues(r: dict) -> list[str]:
    """
    Retourne la liste des types de problèmes détectés pour une recette.
    Valeurs possibles :
      'description_auto', 'description_courte', 'etapes_vagues',
      'four_sans_temp', 'generique', 'flags_bloquants',
      'ingredients_generiques', 'ingredients_non_couverts'
    """
    issues = []
    desc   = r.get('description', '') or ''
    instrs = r.get('instructions', []) or []
    instr_text = ' '.join(instrs)

    if any(re.search(p, desc, re.IGNORECASE) for p in _AUTO_DESC_PATTERNS):
        issues.append('description_auto')

    if len(desc) < DESC_MIN_LEN:
        if 'description_auto' not in issues:
            issues.append('description_courte')

    vague = [s for s in instrs if isinstance(s, str) and len(s.strip()) < STEP_MIN_LEN]
    if len(vague) >= MIN_VAGUE_STEPS:
        issues.append('etapes_vagues')

    if _OVEN_PATTERN.search(instr_text) and not _TEMP_PATTERN.search(instr_text):
        issues.append('four_sans_temp')

    for s in instrs:
        sl = s.lower().strip()
        if any(kw in sl for kw in _GENERIC_KWORDS):
            has_criterion = re.search(
                r'(doit être|qui doit|légèrement|texture\s+\w+|couleur|soyeuse|ferme|crémeux|en appréci)',
                sl
            )
            if not has_criterion or len(s) < STEP_GENERIC_MAX:
                issues.append('generique')
                break

    flags = r.get('_flags', []) or []
    if any('BLOQUANT' in f or 'vegan_alert' in f or 'vegan_flag_but_animal' in f for f in flags):
        issues.append('flags_bloquants')

    # Fix v6.1 — détection levée sans prep_passive_min déclaré
    # (ex: focaccia, bao, pain) — le timing passif restait à 0 même quand
    # les instructions décrivaient explicitement une levée ou un repos.
    _LEVAISON_RE = re.compile(
        r'\b(lever?|levée|laisser lever|laisser repo|repos(?:er)?|ferment|pousser)\b',
        re.IGNORECASE
    )
    _YEAST_INGS = {'yeast', 'levure', 'sourdough', 'starter', 'poolish', 'levain'}
    timing_check = r.get('timing') or {}
    if (timing_check.get('prep_passive_min', 0) or 0) == 0:
        has_yeast_ing = any(
            any(y in c.get('ingredient', '').lower() for y in _YEAST_INGS)
            for c in r.get('composition', [])
        )
        if has_yeast_ing and _LEVAISON_RE.search(instr_text):
            issues.append('passive_time_manquant')

    if _VARIANT_INDEX is not None:
        upgradeable, _ = analyze_generic_ingredients(r)
        if upgradeable:
            issues.append('ingredients_generiques')

    if INGREDIENT_FR_MAP and instr_text:
        instr_lower = instr_text.lower()
        for c in r.get('composition', []):
            ing_key = c.get('ingredient', '')
            fr_terms = INGREDIENT_FR_MAP.get(ing_key)
            if not fr_terms:
                continue
            if not any(term.lower() in instr_lower for term in fr_terms):
                issues.append('ingredients_non_couverts')
                break

    return issues


# ===================== SCORING (v6.0 — NOUVEAU) =====================

# Grille de pénalités par type d'issue
_SCORE_PENALTIES: dict[str, float] = {
    'description_auto':         2.5,
    'description_courte':       1.5,
    'etapes_vagues':            1.5,
    'four_sans_temp':           1.0,
    'generique':                0.5,
    'flags_bloquants':          2.0,
    'ingredients_non_couverts': 0.5,
    'ingredients_generiques':   0.25,
    'passive_time_manquant':    1.0,   # v6.1 — levée sans prep_passive_min
}

# Pénalité additionnelle : description trop longue (> 250 chars)
_DESC_TOO_LONG_PENALTY = 0.5


def score_recipe(r: dict, issues: list[str] | None = None) -> float:
    """
    Retourne un score de qualité de 0.0 à 10.0 pour une recette.

    Calcul :
      10.0 — somme des pénalités par issue détectée
      Pénalité additionnelle si description > 250 chars (style trop verbeux).
      Score plancher : 0.0

    Si `issues` est fourni (déjà calculé), le score est calculé depuis
    cette liste pour éviter un double appel à detect_issues().
    """
    if issues is None:
        issues = detect_issues(r)

    penalty = sum(_SCORE_PENALTIES.get(i, 0.0) for i in issues)

    # Pénalité description trop longue (non couverte par detect_issues)
    desc = r.get('description', '') or ''
    if len(desc) > 250:
        penalty += _DESC_TOO_LONG_PENALTY

    return round(max(0.0, 10.0 - penalty), 2)


def score_label(score: float) -> str:
    """Étiquette courte pour l'affichage."""
    if score >= 9.5:  return "🟢 excellent"
    if score >= 8.5:  return "🟡 bon"
    if score >= 7.0:  return "🟠 moyen"
    if score >= 5.5:  return "🔴 faible"
    return "⛔ critique"


# ===================== PROMPT SYSTÈME =====================

CHEF_SYSTEM = """\
Tu es un chef cuisinier français professionnel, passionné, rigoureux et pédagogue, avec plus de 15 ans d'expérience dans la cuisine végétalienne créative et savoureuse.

Ton style est élégant, précis, chaleureux et naturel. Tu rédiges comme si tu expliquais à un élève motivé et exigeant.

═══ RÈGLES ABSOLUES ═══

① RÉGIME — LIS `is_vegan_recipe` DANS LE PAYLOAD AVANT TOUT
   Le projet est 100 % végétarien. Certaines recettes sont aussi vegan, d'autres non.

   SI `is_vegan_recipe` est `true` (recette vegan) :
   • Remplace tout produit animal dans description ET instructions :
       lait → lait de coco ou lait d'avoine
       crème / crème fraîche → crème de coco
       fromage / parmesan → fromage végétal râpé ou levure nutritionnelle
       beurre → huile de coco ou huile d'olive
       yaourt → yaourt de coco
       œuf (liant) → œuf de lin (1 c. à soupe graines + 3 c. à soupe eau)
   • Conserve exactement "Vegan" ou "végan" si présent dans le titre.
   • Si un flag "BLOQUANT" ou "vegan_alert" est signalé, corrige impérativement.

   SI `is_vegan_recipe` est `false` (recette végétarienne, pas vegan) :
   • NE REMPLACE PAS les produits laitiers, les œufs, le fromage, le beurre, etc.
     Ces ingrédients sont légitimes dans une recette végétarienne.
   • N'invente pas de substituts vegan non demandés.
   • Corrige uniquement si un flag "BLOQUANT" ou "vegan_flag_but_animal" est
     explicitement signalé dans `_flags` (recette étiquetée vegan à tort).

② DESCRIPTION — OBLIGATOIRE
   • Longueur : STRICTEMENT entre 150 et 250 caractères.
   • Structure : technique principale → texture attendue → origine/contexte culinaire.
   • Aucun terme anglais (pas de "crispy", "bowl", "mix", "dash"…).
   • INTERDIT — ces formules sont des templates vides à bannir absolument :
       ✗ « à base de [ingrédient EN] »  (ex : "à base de split peas", "à base de tofu")
       ✗ « aux saveurs umami et profond »  ou  « aux saveurs profond »
       ✗ « saveurs équilibrées »  seul, sans détail concret
       ✗ « aux saveurs umami et équilibre »
       ✗ « Soupe [pays] à base de [ingr], aux saveurs X »
       ✗ « Plat [nationalité] à base de »
       ✗ « aux saveurs equilibre »  /  « saveurs doux »
       ✗ « Délicieux [plat] aux saveurs équilibrées »
   • OBLIGATOIRE : au moins un repère sensoriel CONCRET (texture, couleur, odeur,
     température) + au moins un élément d'origine ou de technique.
   • EXEMPLE à éviter → « Soupe japonaise à base de tofu, aux saveurs umami et profond. »
   • EXEMPLE correct → « Bouillon dashi relevé d'une pâte miso blanche, où le tofu
     soyeux fond en bouche — recette fondatrice de la cuisine zen japonaise. »

③ INSTRUCTIONS — QUALITÉ CHEF
   • Vise 7–11 étapes pour un plat principal, 4–7 pour une entrée/base.
   • Chaque étape ≥ 120 caractères avec : action précise + repère (temps, texture,
     couleur, son) + quantité si pertinente.
   • Si cuisson four ou gril est mentionnée : OBLIGATOIRE d'inclure la température
     en °C (ex : "préchauffer à 200°C", "enfourner à 220°C").
   • INTERDIT en étape standalone (sans critère concret) :
       - "Servir immédiatement." → remplace par : "Servir sans attendre : [pourquoi
         la chaleur/le croustillant est essentiel ici]."
       - "Vérifier la texture." → remplace par : "Vérifier que [critère précis :
         la lame ressort sèche / les grains se détachent / la sauce nappe la cuillère]."

④ COUVERTURE INGRÉDIENTS
   • Chaque ingrédient de "composition" doit être nommé en français dans les
     instructions (pas la clé normalisée EN, le nom FR usuel).
   • Si "ingredients_non_couverts" est signalé dans audit_issues, le payload
     contient un champ "ingredients_non_couverts" listant pour chaque ingrédient
     manquant sa clé normalisée ET ses "noms_fr" officiels (issus de nutrition_v2).
     Utilise EXACTEMENT l'un de ces noms FR dans les instructions — ne les invente pas.
   • Exemple de payload : {"ing_key": "lemon", "noms_fr": ["citron", "citron jaune"]}
     → écris "citron" ou "jus de citron" dans les instructions.
   • Assure-toi que CHAQUE ingrédient listé dans "ingredients_non_couverts"
     apparaît explicitement dans les instructions réécrites.

⑤ TIMING (si fourni)
   • Si "cook_min_issue" est signalé et que les instructions décrivent une cuisson
     thermique réelle (feu, four, friture…), fournis un champ "cook_min_corrige"
     avec la valeur correcte estimée en minutes (entier).
   • Si "passive_time_manquant" est signalé dans audit_issues, lis les instructions
     et détermine le temps passif réel (levée, repos, marinade, réfrigération…).
     Fournis un champ "prep_passive_min_corrige" avec la valeur en minutes (entier).
     Exemples : focaccia 1h30 levée + 30min détente → 120 ; bao 1h levée → 60.

⑥ AFFINEMENT DES INGRÉDIENTS (si "upgradeable_ingredients" est fourni)
   • Le payload peut contenir un champ "upgradeable_ingredients" listant les
     ingrédients génériques pour lesquels des variants précis sont disponibles.
   • Pour chaque entrée, choisis le variant le PLUS COHÉRENT avec la recette
     traditionnelle (origine, technique, usage culinaire réel).
   • CONTRÔLE ABSOLU : tu ne peux choisir QUE parmi les variants listés dans
     "available_variants" — aucune invention, aucun variant hors liste.
   • Si aucun variant de la liste ne convient vraiment (ingrédient trop
     polyvalent, recette ambiguë), tu peux conserver le générique en
     n'incluant PAS cette clé dans "ingredient_variants".
   • Ne modifie PAS les ingrédients déjà précis (variant non-default).

═══ FORMAT DE RÉPONSE ═══
JSON valide UNIQUEMENT, aucun texte avant/après :
{
  "recipes": [
    {
      "id": "...",
      "description": "...",
      "instructions": ["Étape 1 : ...", "Étape 2 : ..."],
      "cook_min_corrige": 25,
      "ingredient_variants": {
        "ing_key": "variant_key"
      },
      "note": "Résumé des corrections effectuées"
    }
  ]
}
(cook_min_corrige et ingredient_variants sont optionnels)
"""


# ===================== APPEL API GROQ =====================

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
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        )
    }
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=90) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]


# ===================== APPEL API ANTHROPIC =====================

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
        "anthropic-version": "2023-06-01"
    }
    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as resp:
        result = json.loads(resp.read().decode("utf-8"))
        text_blocks = [b["text"] for b in result.get("content", []) if b.get("type") == "text"]
        return "\n".join(text_blocks)


# ===================== PARSING RÉPONSE =====================

def parse_response(text: str) -> dict | None:
    m = re.search(r'```json\s*([\s\S]*?)```', text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r'(\{"recipes"\s*:[\s\S]*\})', text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    m = re.search(r'(\{[\s\S]+\})', text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass
    return None


# ===================== CHARGEMENT DES DONNÉES =====================

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


# ===================== FUSION & SAUVEGARDE =====================

def merge_and_save(
    recipes: list,
    processed: dict,
    output_path: Path,
    data: dict | list,
    data_is_list: bool
) -> int:
    today     = str(datetime.now().date())
    log_entry = f"chef_rewrite_v6_{today}"
    updated   = 0

    for r in recipes:
        patch = processed.get(r["id"])
        if not patch:
            continue

        r["description"]  = patch.get("description",  r.get("description"))
        r["instructions"] = patch.get("instructions", r.get("instructions"))

        if "cook_min_corrige" in patch:
            try:
                new_cook = int(patch["cook_min_corrige"])
                timing = r.setdefault("timing", {})
                old_cook  = timing.get("cook_min", 0)
                timing["cook_min"] = new_cook
                prep_active  = timing.get("prep_active_min", 0) or 0
                prep_passive = timing.get("prep_passive_min", 0) or 0
                timing["total_min"] = prep_active + prep_passive + new_cook
                flags = r.get("_flags", [])
                r["_flags"] = [f for f in flags if "cook_zero" not in f and "timing_cook_zero" not in f]
                if "cook_min_correction" not in r:
                    r["cook_min_correction"] = {"from": old_cook, "to": new_cook, "by": log_entry}
            except (ValueError, TypeError):
                pass

        # v6.1 — application de prep_passive_min_corrige (levée, repos…)
        if "prep_passive_min_corrige" in patch:
            try:
                new_passive = int(patch["prep_passive_min_corrige"])
                timing = r.setdefault("timing", {})
                old_passive = timing.get("prep_passive_min", 0) or 0
                timing["prep_passive_min"] = new_passive
                # Recalcul du total
                prep_active = timing.get("prep_active_min", 0) or 0
                cook        = timing.get("cook_min", 0) or 0
                timing["total_min"] = prep_active + new_passive + cook
                # Purger le flag passive_time_manquant
                r["_flags"] = [f for f in r.get("_flags", []) if "passive_time" not in f]
                if "prep_passive_correction" not in r:
                    r["prep_passive_correction"] = {
                        "from": old_passive, "to": new_passive, "by": log_entry
                    }
            except (ValueError, TypeError):
                pass

        ing_variants = patch.get("ingredient_variants", {})
        if ing_variants and _VARIANT_INDEX is not None:
            applied   = []
            rejected  = []
            for c in r.get("composition", []):
                ing_key = c.get("ingredient", "")
                if ing_key not in ing_variants:
                    continue
                chosen_var = ing_variants[ing_key]
                resolved = resolve_ingredient_to_base(ing_key)
                if resolved is None:
                    rejected.append(f"{ing_key}→{chosen_var} (base inconnue)")
                    continue
                base_key, _ = resolved
                available   = get_available_variants(base_key)
                if chosen_var not in available:
                    rejected.append(f"{ing_key}→{chosen_var} (variant hors index)")
                    continue
                old_ing = c["ingredient"]
                c["ingredient"] = f"{base_key}/{chosen_var}"
                c["variant"]    = chosen_var
                c["variant_name_fr"] = available[chosen_var]
                applied.append(f"{old_ing} → {c['ingredient']} ({available[chosen_var]})")

            if applied:
                if "_ingredient_variants_log" not in r:
                    r["_ingredient_variants_log"] = []
                r["_ingredient_variants_log"].append({"by": log_entry, "applied": applied})
            if rejected:
                if "_ingredient_variants_rejected" not in r:
                    r["_ingredient_variants_rejected"] = []
                r["_ingredient_variants_rejected"].extend(rejected)

        missing_vars = patch.get("_missing_variants_payload", [])
        if missing_vars:
            r.setdefault("_missing_variants", [])
            for m in missing_vars:
                if m not in r["_missing_variants"]:
                    r["_missing_variants"].append(m)

        if "_corrections_log" not in r:
            r["_corrections_log"] = []
        if log_entry not in r["_corrections_log"]:
            r["_corrections_log"].append(log_entry)

        updated += 1

    output_data = recipes if data_is_list else data
    tmp_path = output_path.with_suffix(".tmp.json")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    tmp_path.replace(output_path)

    return updated


# ===================== CONSTRUCTION DU PAYLOAD =====================

def _recipe_is_vegan(r: dict) -> bool:
    """True si la recette est vegan (diet_flags, titre ou flag), False si juste végétarienne.

    Ordre de priorité :
      1. diet_flags.vegan = True  → vegan certain
      2. "vegan" / "végan" dans le titre  → vegan annoncé
      3. flag vegan_alert / vegan_flag_but_animal  → vegan à corriger
    Bug corrigé v6.1 : l'ancienne version ignorait diet_flags.vegan, ce qui faisait
    traiter comme végétariennes des recettes vegan sans "vegan" dans le titre.
    """
    if r.get("diet_flags", {}).get("vegan", False):
        return True
    titles = r.get("titles") or {}
    title_fr = titles.get("fr", "").lower()
    title_en = titles.get("en", "").lower()
    flags = r.get("_flags", []) or []
    return (
        "vegan" in title_fr or "végan" in title_fr or "vegan" in title_en
        or any("vegan_alert" in f or "vegan_flag_but_animal" in f for f in flags)
    )


def build_batch_item(r: dict, issues: list[str]) -> dict:
    comp = [
        {
            "ingredient": c.get("ingredient"),
            "quantity":   c.get("quantity"),
            "unit":       c.get("unit")
        }
        for c in r.get("composition", [])
    ]

    item = {
        "id":             r["id"],
        "titles":         r.get("titles"),
        "description":    r.get("description"),
        "composition":    comp,
        "instructions":   r.get("instructions"),
        "audit_issues":   issues,
        "is_vegan_recipe": _recipe_is_vegan(r),
    }

    timing = r.get("timing", {})
    title_fr = (r.get("titles") or {}).get("fr", "").lower()
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
            "cook_min":          cook_min_val,
            "prep_passive_min":  passive_min_val,
            "total_min":         timing.get("total_min"),
        }
        if cook_min_val == 0 and not is_legitimate_zero:
            item["cook_min_issue"] = True
        if "passive_time_manquant" in issues:
            item["passive_time_issue"] = True  # signal explicite au LLM

    flags = r.get("_flags", [])
    if flags:
        item["_flags"] = flags

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

    if "ingredients_non_couverts" in issues:
        instr_lower = ' '.join(r.get("instructions", [])).lower()
        non_couverts = []
        for c in r.get("composition", []):
            ing_key = c.get("ingredient", "")
            fr_terms = INGREDIENT_FR_MAP.get(ing_key)
            if not fr_terms:
                continue
            if not any(term.lower() in instr_lower for term in fr_terms):
                non_couverts.append({"ing_key": ing_key, "noms_fr": fr_terms})
        if non_couverts:
            item["ingredients_non_couverts"] = non_couverts

    return item


# ===================== RAPPORT FINAL D'AUDIT =====================

def print_audit_report(
    recipes: list,
    eligible_ids: set,
    processed: set,
    score_threshold: float = DEFAULT_SCORE_THRESHOLD
) -> None:
    """Affiche un rapport enrichi avec distribution des scores."""
    print("\n" + "─" * 65)
    print("📊 RAPPORT FINAL")
    print("─" * 65)

    # ── Comptages par issue ──────────────────────────────────────────
    counts = {k: 0 for k in _SCORE_PENALTIES}
    all_scores = []
    below_threshold = []

    for r in recipes:
        issues = detect_issues(r)
        sc = score_recipe(r, issues)
        all_scores.append(sc)
        for issue in issues:
            counts[issue] = counts.get(issue, 0) + 1
        if sc < score_threshold:
            below_threshold.append((sc, r))

    labels = {
        'description_auto':         'Descriptions auto-générées (cluster umami…)',
        'description_courte':       f'Descriptions < {DESC_MIN_LEN} chars',
        'etapes_vagues':            f'Recettes avec ≥{MIN_VAGUE_STEPS} étapes vagues (<{STEP_MIN_LEN}c)',
        'four_sans_temp':           'Four/gril sans température °C',
        'generique':                'Formules génériques standalone',
        'flags_bloquants':          'Flags bloquants / vegan alerts',
        'ingredients_generiques':   'Ingrédients génériques améliorables',
        'ingredients_non_couverts': 'Ingrédients normalisés absents des instructions',
    }
    for k, label in labels.items():
        print(f"  {label:<52} : {counts.get(k, 0)}")

    # ── Distribution des scores ──────────────────────────────────────
    print()
    print("  Distribution des scores :")
    thresholds = [10.0, 9.5, 9.0, 8.5, 8.0, 7.5, 7.0, 5.5, 0.0]
    labels_score = ["10.0", "9.5–9.9", "9.0–9.4", "8.5–8.9", "8.0–8.4",
                    "7.5–7.9", "7.0–7.4", "5.5–6.9", "< 5.5"]
    bands = [0] * (len(thresholds))
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

    # ── 10 pires recettes restantes ─────────────────────────────────
    if below_threshold:
        below_threshold.sort(key=lambda x: x[0])
        print(f"\n  Top 10 pires recettes restantes (< {score_threshold}) :")
        for sc, r in below_threshold[:10]:
            title = r.get("titles", {}).get("fr", r["id"])
            issues = detect_issues(r)
            print(f"    {sc:.1f}  {score_label(sc)}  {title[:40]:<40}  [{', '.join(issues)}]")

    # ── Variants ────────────────────────────────────────────────────
    total_applied  = sum(len(r.get("_ingredient_variants_log", [])) for r in recipes)
    total_rejected = sum(len(r.get("_ingredient_variants_rejected", [])) for r in recipes)
    total_missing  = sum(len(r.get("_missing_variants", [])) for r in recipes)
    if total_applied or total_rejected or total_missing:
        print()
        print(f"  {'Variants ingrédients appliqués':<44} : {total_applied}")
        if total_rejected:
            print(f"  {'Variants rejetés (hors index)':<44} : {total_rejected}")
        if total_missing:
            print(f"  {'Ingrédients hors index (no variant dispo)':<44} : {total_missing}")

    print(f"\n  Éligibles traités dans ce run : {len(processed & eligible_ids)} / {len(eligible_ids)}")
    print("─" * 65)


# ===================== MAIN =====================

def main():
    parser = argparse.ArgumentParser(
        description="Réécriture chef v6.0 — score-based filtering + rapport enrichi"
    )
    parser.add_argument("--key",             required=False, default=None,
                        help="Clé API Groq (gsk_...)")
    parser.add_argument("--key-anthropic",   required=False, default=None,
                        help="Clé API Anthropic (sk-ant-...)")
    parser.add_argument("--mode",            choices=["groq", "anthropic"], default="groq",
                        help="Provider API à utiliser (défaut: groq)")
    parser.add_argument("--input",           default="recipes.json",
                        help="Fichier source JSON")
    parser.add_argument("--nutrition",       default=None,
                        help="Fichier nutrition_v2.json")
    parser.add_argument("--recipes-ref",     default=None,
                        help="Fichier recipes.json de référence pour les base_recipes")

    # ── Filtres de sélection ─────────────────────────────────────────
    parser.add_argument("--score-threshold", type=float, default=DEFAULT_SCORE_THRESHOLD,
                        help=f"Score seuil : seules les recettes STRICTEMENT en dessous "
                             f"sont traitées (défaut: {DEFAULT_SCORE_THRESHOLD}). "
                             f"Exemple : --score-threshold 8.5 cible toutes les < 8.5/10")
    parser.add_argument("--target",
                        choices=["all", "description_auto", "description_courte",
                                 "etapes_vagues", "four_sans_temp", "generique",
                                 "flags_bloquants", "ingredients_generiques",
                                 "ingredients_non_couverts", "passive_time_manquant"],
                        default="all",
                        help="Cibler un type de problème spécifique (défaut: all). "
                             "Combinable avec --score-threshold.")
    parser.add_argument("--limit",           type=int, default=0,
                        help="Limiter le nombre de recettes à traiter (0 = illimité)")

    # ── Modes utilitaires ────────────────────────────────────────────
    parser.add_argument("--dry-run",         action="store_true",
                        help="Affiche les recettes éligibles sans appeler l'API")
    parser.add_argument("--show-scores",     action="store_true",
                        help="Affiche le score de chaque recette en mode dry-run")
    parser.add_argument("--clean-progress",  action="store_true",
                        help="Supprime le fichier de progression puis quitte")
    parser.add_argument("--repair-progress", action="store_true",
                        help="Reconstruit le fichier de progression depuis l'output existant")
    parser.add_argument("--report",          action="store_true",
                        help="Affiche uniquement le rapport d'audit puis quitte")
    args = parser.parse_args()

    # ── Chargement index variants ────────────────────────────────────
    if args.nutrition or args.recipes_ref:
        init_variant_index(args.nutrition, args.recipes_ref)
    else:
        print("ℹ️  --nutrition non fourni : détecteur 'ingredients_generiques' désactivé")

    # Validation clé API
    if not args.dry_run and not args.report and not args.clean_progress and not args.repair_progress:
        if args.mode == "groq" and not args.key:
            print("❌ --key requis pour le mode groq")
            sys.exit(1)
        if args.mode == "anthropic" and not args.key_anthropic:
            print("❌ --key-anthropic requis pour le mode anthropic")
            sys.exit(1)

    input_path    = Path(args.input)
    output_path   = input_path.with_name(input_path.stem + OUTPUT_SUFFIX)
    progress_path = input_path.with_name(input_path.stem + PROGRESS_SUFFIX)

    # ── Nettoyage progression ────────────────────────────────────────
    if args.clean_progress:
        if progress_path.exists():
            progress_path.unlink()
            print(f"🗑  Progression supprimée : {progress_path.name}")
        else:
            print("ℹ  Aucun fichier de progression à supprimer.")
        sys.exit(0)

    # ── Reconstruction progression ───────────────────────────────────
    if args.repair_progress:
        if not output_path.exists():
            print(f"❌ Aucun fichier de sortie trouvé : {output_path.name}")
            sys.exit(1)
        result = load_recipes_safe(output_path)
        if result is None:
            print("❌ Fichier de sortie illisible — impossible de reconstruire.")
            sys.exit(1)
        out_recipes, _, _ = result
        progress = {}
        for r in out_recipes:
            if not r.get("_corrections_log"):
                continue
            entry = {
                "id":           r["id"],
                "description":  r.get("description", ""),
                "instructions": r.get("instructions", []),
            }
            if "cook_min_correction" in r:
                entry["cook_min_corrige"] = r["cook_min_correction"]["to"]
            progress[r["id"]] = entry
        with open(progress_path, "w", encoding="utf-8") as f:
            json.dump(progress, f, ensure_ascii=False, indent=2)
        print(f"✅ Progression reconstruite : {len(progress)} recettes → {progress_path.name}")
        sys.exit(0)

    # ── Chargement ───────────────────────────────────────────────────
    if not input_path.exists():
        print(f"❌ Fichier non trouvé : {input_path}")
        sys.exit(1)

    source_recipes, _, _ = load_recipes(input_path)
    print(f"📊 {len(source_recipes)} recettes dans la source")

    if output_path.exists():
        print(f"♻️  Fichier de sortie existant — utilisé comme base : {output_path.name}")
        _loaded = load_recipes_safe(output_path)
        if _loaded is not None:
            recipes, data, data_is_list = _loaded
        else:
            print("🔄 Bascule sur la source après corruption détectée.")
            _, data, data_is_list = load_recipes(input_path)
            recipes = source_recipes
    else:
        print("🆕 Démarrage depuis la source.")
        _, data, data_is_list = load_recipes(input_path)
        recipes = source_recipes

    recipe_index       = {r["id"]: r for r in recipes}
    recipe_index_lower = {k.lower(): k for k in recipe_index}
    source_index       = {r["id"]: r for r in source_recipes}

    # ── Rapport seul ─────────────────────────────────────────────────
    if args.report:
        print_audit_report(recipes, set(), set(), args.score_threshold)
        sys.exit(0)

    # ── Détection des éligibles ──────────────────────────────────────
    #
    #  v6 : double filtre — issues ET score < threshold
    #  On évalue les problèmes sur le fichier de TRAVAIL (output si existant).
    #
    eligible: dict[str, tuple[list[str], float]] = {}   # rid → (issues, score)
    for r in recipes:
        issues = detect_issues(r)
        if not issues:
            continue
        # Filtre --target
        if args.target != "all" and args.target not in issues:
            continue
        sc = score_recipe(r, issues)
        # ── FILTRE SCORE (v6) ────────────────────────────────────────
        if sc >= args.score_threshold:
            continue
        eligible[r["id"]] = (issues, sc)

    eligible_ids = set(eligible.keys())
    print(f"🎯 Score seuil : < {args.score_threshold}/10")
    print(f"🔍 {len(eligible_ids)} recettes éligibles (score < {args.score_threshold} ET problèmes détectés)")

    # Répartition par type
    type_counts: dict[str, int] = {}
    for issues, _ in eligible.values():
        for i in issues:
            type_counts[i] = type_counts.get(i, 0) + 1
    for k, v in sorted(type_counts.items(), key=lambda x: -x[1]):
        print(f"   • {k:<35} : {v}")

    if not eligible_ids:
        print(f"✅ Aucune recette sous {args.score_threshold}/10. Fin du script.")
        sys.exit(0)

    # ── Dry run ──────────────────────────────────────────────────────
    if args.dry_run:
        sorted_eligible = sorted(eligible.items(), key=lambda x: x[1][1])
        print(f"\n── DRY RUN — {len(eligible_ids)} recettes à traiter (score < {args.score_threshold}) ──")
        for rid, (issues, sc) in sorted_eligible:
            r = recipe_index.get(rid, {})
            title = r.get("titles", {}).get("fr", rid)
            score_info = f"  [{sc:.1f}]" if args.show_scores else ""
            print(f"  {score_info} [{', '.join(issues)}] {title}")
        sys.exit(0)

    # ── Chargement de la progression ─────────────────────────────────
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
        (rid, eligible[rid][0], eligible[rid][1])  # (rid, issues, score)
        for rid in eligible_ids
        if rid not in processed
    ]
    # Tri : score le plus bas en premier (pires recettes traitées en priorité)
    PRIORITY = {
        'description_auto': 0, 'flags_bloquants': 1, 'four_sans_temp': 2,
        'passive_time_manquant': 2, 'description_courte': 3, 'etapes_vagues': 4,
        'generique': 5, 'ingredients_non_couverts': 6, 'ingredients_generiques': 7,
    }
    to_process.sort(key=lambda x: (x[2], min(PRIORITY.get(i, 9) for i in x[1])))

    if args.limit > 0:
        to_process = to_process[:args.limit]
        print(f"⚠️  Limité à {args.limit} recettes (--limit)")

    print(f"⏭  {len(to_process)} recettes restantes à traiter")

    if not to_process:
        print("✅ Toutes les recettes éligibles ont été traitées. Fusion finale.")

    # ── Sélection du provider ────────────────────────────────────────
    def call_api(batch_data: list) -> str:
        if args.mode == "anthropic":
            return call_anthropic(batch_data, args.key_anthropic)
        return call_groq(batch_data, args.key)

    # ── Boucle principale ────────────────────────────────────────────
    total_lots = (len(to_process) + BATCH_SIZE - 1) // BATCH_SIZE if to_process else 0
    newly_processed = set()

    for lot_i, (rid, issues, sc) in enumerate(to_process, start=1):
        r = recipe_index.get(rid) or source_index.get(rid)
        if not r:
            print(f"   ⚠ ID {rid} introuvable dans le recipe_index — ignoré")
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
                    raise ValueError("Impossible d'extraire un JSON valide de la réponse")

                for item in result.get("recipes", []):
                    item_id = item.get("id", "")

                    if item_id not in recipe_index:
                        canonical = recipe_index_lower.get(item_id.lower())
                        if canonical:
                            print(f"   ℹ️  ID normalisé : '{item_id}' → '{canonical}'")
                            item["id"] = canonical
                            item_id = canonical
                        else:
                            print(f"   ⚠️  ID inconnu ignoré : '{item_id}'")
                            continue

                    new_desc = item.get("description", "")
                    if len(new_desc) < 100:
                        print(f"   ⚠️  Description trop courte ({len(new_desc)} chars) — recette conservée mais à retraiter")

                    batch_item = batch_data[0] if batch_data else {}
                    missing_in_payload = batch_item.get("_missing_variants", [])
                    if missing_in_payload:
                        item["_missing_variants_payload"] = missing_in_payload

                    processed[item_id] = item
                    newly_processed.add(item_id)

                success = True
                first_item = result.get("recipes", [{}])[0]
                note     = first_item.get("note", "")
                cook_fix = first_item.get("cook_min_corrige")
                ing_vars = first_item.get("ingredient_variants", {})
                status = f"✅ Lot {lot_i} OK (tentative {attempt})"
                if cook_fix is not None:
                    status += f" | cook_min → {cook_fix} min"
                if ing_vars:
                    status += f" | {len(ing_vars)} variant(s) ing."
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
                    wait = 2 * attempt
                    print(f"   ⚠ Tentative {attempt}/{MAX_RETRIES} — HTTP {e.code}: {e}")
                    if attempt < MAX_RETRIES:
                        time.sleep(wait)

            except Exception as e:
                wait = 2 * attempt
                print(f"   ⚠ Tentative {attempt}/{MAX_RETRIES} échouée : {e}")
                if attempt < MAX_RETRIES:
                    time.sleep(wait)

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
    print(f"✅ {updated_count} recettes mises à jour au total")
    print(f"   dont {len(newly_processed)} dans ce run")
    print(f"📁 Fichier de sortie : {output_path}")

    # ── Rapport final ────────────────────────────────────────────────
    recipes_final, _, _ = load_recipes(output_path)
    print_audit_report(
        recipes_final, eligible_ids,
        newly_processed | set(processed.keys()),
        args.score_threshold
    )

    print("\nℹ️  Progression conservée pour reprise éventuelle.")
    print(f"   Pour la supprimer : python rewrite_smart_v6.py --input {input_path} --clean-progress")


if __name__ == "__main__":
    main()
