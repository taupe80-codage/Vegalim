"""
ALIM — Réécriture des instructions via Groq (llama-3.3-70b, gratuit)
Fichier unique, aucune dépendance interne.

Améliorations v2 :
  - Validation métier AVANT réécriture (cohérence ingrédients)
  - Prompt enrichi (quantités, diet_flags, techniques meta)
  - Post-validation LLM (contrôle des instructions générées)
  - Blocage des instructions hallucinées
  - Score qualité mis à jour après réécriture
  - VISUAL_MARKERS enrichis

Usage :
    $env:GROQ_API_KEY = "gsk_..."        (PowerShell)
    python alim_rewriter.py --input recipes.json --output recipes_v2.json
    python alim_rewriter.py --input recipes.json --output recipes_v2.json --max 50
    python alim_rewriter.py --input recipes.json --output recipes_v2.json --resume
    python alim_rewriter.py --input recipes.json --output recipes_v2.json --validate-only
"""

import json, re, os, sys, time, argparse, threading
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

try:
    import requests
except ImportError:
    print("pip install requests")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
# VISUAL MARKERS — enrichis
# ═══════════════════════════════════════════════════════════════════════════════

VISUAL_MARKERS = [
    # FR — texture / couleur
    "doré","fondant","croustillant","texture","couleur","caramélisé",
    "translucide","ébullition","frémiss","brunir","homogène","brillant",
    "réduit","al dente","coloration","réduction","nacré","saisi",
    "doré","blond","évapor","attache","lame ressort","crépite",
    # EN — fallback si instructions partiellement en anglais
    "golden","browned","crispy","tender","simmering","absorbed",
    "caramelized","translucent","reduced","glossy",
]

# ═══════════════════════════════════════════════════════════════════════════════
# DÉTECTION DES RECETTES À RÉÉCRIRE
# ═══════════════════════════════════════════════════════════════════════════════

def needs_rewrite(r: dict) -> bool:
    """Retourne True si les instructions de cette recette doivent être réécrites."""
    if r.get("_rewritten"):
        return False
    if r.get("_needs_rewrite"):
        return True

    instrs = r.get("instructions") or []
    if not instrs:
        return True

    text = " ".join(instrs).lower()
    issues = []

    avg = sum(len(i) for i in instrs) / len(instrs)
    if avg < 55:                                                          issues.append("trop_court")
    if len(instrs) < 4:                                                   issues.append("trop_peu_etapes")
    if not re.search(r"(°C|\bfeu\s+(vif|doux|moyen))", text, re.I):     issues.append("pas_temperature")
    if not re.search(r"\b(min|minutes)\b", text, re.I):                  issues.append("pas_duree")
    if not any(m in text for m in VISUAL_MARKERS):                       issues.append("pas_visuel")

    return len(issues) >= 2

# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATION MÉTIER — AVANT RÉÉCRITURE (nouveau)
# ═══════════════════════════════════════════════════════════════════════════════

# Mots à ignorer dans la comparaison ingrédients (trop génériques)
_INGREDIENT_STOPWORDS = {
    "water","sel","salt","oil","huile","poivre","pepper","sugar","sucre",
    "butter","beurre","flour","farine","milk","lait","cream","crème",
    "garlic","ail","onion","oignon","herb","herbe","spice","épice",
}

def _extract_ingredient_tokens(name: str) -> set:
    """Retourne les tokens significatifs d'un nom d'ingrédient."""
    tokens = set(re.split(r"[\s_\-]+", name.lower()))
    return tokens - _INGREDIENT_STOPWORDS

def validate_recipe_pre(r: dict) -> list[str]:
    """
    Validation métier AVANT réécriture.
    Retourne une liste d'anomalies (vide = OK).
    """
    issues = []
    instrs = r.get("instructions") or []
    composition = r.get("composition") or []

    # Construire un corpus des tokens d'ingrédients connus
    known_tokens: set[str] = set()
    for comp in composition:
        ing = comp.get("ingredient", "")
        known_tokens |= _extract_ingredient_tokens(ing)

    instr_text = " ".join(instrs).lower()

    # 1. Ingrédients nommés dans les instructions mais absents de la composition
    #    (heuristique sur les mots ≥ 5 lettres non-stopwords)
    words_in_instr = set(re.findall(r"\b[a-zàâéèêëîïôùûüç]{5,}\b", instr_text))
    suspicious = words_in_instr - known_tokens - _INGREDIENT_STOPWORDS
    # Filtrer : seulement mots qui ressemblent à un ingrédient (pas de verbes courants)
    _VERB_STOP = {"cuire","faire","ajouter","mettre","verser","mixer","laisser",
                  "couvrir","porter","chauffer","incorporer","servir","garnir",
                  "assaisonner","saupoudrer","réserver","égoutter","rincer",
                  "couper","hacher","émincer","ciseler","peler","éplucher",
                  "mélanger","remuer","fouetter","battre","étaler","rouler"}
    suspicious -= _VERB_STOP
    if len(suspicious) > 6:
        issues.append(f"ingredient_mismatch_potential:{','.join(list(suspicious)[:5])}")

    # 2. Timing incohérent
    cook_min = (r.get("timing") or {}).get("cook_min", 0)
    if cook_min == 0 and re.search(r"\b(four|cuire|bouillir|frire|rôtir)\b", instr_text):
        issues.append("timing_cook_zero_but_cooking_mentioned")

    # 3. Recette marquée vegan mais instructions mentionnent fromage/crème/œuf
    diet_flags = r.get("diet_flags") or {}
    if diet_flags.get("vegan"):
        non_vegan_pattern = r"\b(fromage|cheese|parmesan|crème fraîche|beurre|oeuf|egg|lait|milk|miel|honey)\b"
        if re.search(non_vegan_pattern, instr_text, re.I):
            issues.append("vegan_flag_but_animal_product_in_instructions")

    # 4. Composition vide
    if not composition:
        issues.append("composition_empty")

    return issues


def compute_quality_score(r: dict) -> float:
    """
    Score qualité simple 0-1 sur 7 dimensions.
    Compatible avec le champ _quality_score CDC v4.
    """
    score = 0.0
    weights = {
        "instructions": 0.30,
        "composition":  0.20,
        "timing":       0.15,
        "description":  0.10,
        "origin":       0.10,
        "tags":         0.10,
        "diet_flags":   0.05,
    }

    # Instructions
    instrs = r.get("instructions") or []
    if instrs:
        text = " ".join(instrs).lower()
        instr_score = 0.0
        avg = sum(len(i) for i in instrs) / len(instrs)
        if avg >= 80:         instr_score += 0.25
        elif avg >= 55:       instr_score += 0.15
        if len(instrs) >= 5:  instr_score += 0.25
        elif len(instrs) >= 4: instr_score += 0.15
        if re.search(r"(°C|\bfeu\s+(vif|doux|moyen))", text, re.I): instr_score += 0.25
        if re.search(r"\b(min|minutes)\b", text, re.I):              instr_score += 0.15
        if any(m in text for m in VISUAL_MARKERS):                   instr_score += 0.10
        score += min(instr_score, 1.0) * weights["instructions"]

    # Composition
    comp = r.get("composition") or []
    if len(comp) >= 5:   score += weights["composition"]
    elif len(comp) >= 2: score += weights["composition"] * 0.5

    # Timing
    timing = r.get("timing") or {}
    if timing.get("total_min") and timing["total_min"] > 0:
        score += weights["timing"]

    # Description
    desc = r.get("description") or ""
    if len(desc) >= 50: score += weights["description"]
    elif len(desc) > 0: score += weights["description"] * 0.5

    # Origin
    origin = r.get("origin") or {}
    if origin.get("cuisine") and origin.get("country"):
        score += weights["origin"]

    # Tags
    tags = r.get("tags") or {}
    if tags.get("diet") or tags.get("technique"):
        score += weights["tags"]

    # Diet flags
    df = r.get("diet_flags") or {}
    if df:
        score += weights["diet_flags"]

    return round(min(score, 1.0), 3)

# ═══════════════════════════════════════════════════════════════════════════════
# CLIENT GROQ
# ═══════════════════════════════════════════════════════════════════════════════

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"

_last_call  = 0.0
_call_lock  = threading.Lock()
MIN_INTERVAL = 4.5   # ~13 req/min — safe pour le free tier Groq (limite : ~30/min)

def groq_chat(api_key: str, system_msg: str, user_msg: str,
              max_tokens: int = 2000, retries: int = 4) -> str:
    global _last_call
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type":  "application/json",
    }
    payload = {
        "model":       GROQ_MODEL,
        "max_tokens":  max_tokens,
        "temperature": 0.20,   # légèrement réduit pour moins d'hallucinations
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": user_msg},
        ],
    }
    for attempt in range(retries):
        with _call_lock:
            elapsed = time.time() - _last_call
            if elapsed < MIN_INTERVAL:
                time.sleep(MIN_INTERVAL - elapsed)
            _last_call = time.time()

        try:
            r = requests.post(GROQ_URL, json=payload, headers=headers, timeout=60)
            if r.status_code == 429:
                wait = 45 * (attempt + 1)
                print(f"    ⏳ Rate limit Groq — pause {wait}s...")
                time.sleep(wait)
                continue
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(3 * (attempt + 1))
            else:
                raise RuntimeError(f"Groq échec après {retries} tentatives: {e}")
    return ""


def extract_json(text: str):
    """Extrait le premier tableau JSON valide d'une réponse LLM."""
    text = re.sub(r"```json|```", "", text).strip()
    m = re.search(r"\[.*\]", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError(f"Aucun JSON trouvé:\n{text[:200]}")

# ═══════════════════════════════════════════════════════════════════════════════
# POST-VALIDATION LLM — APRÈS RÉÉCRITURE (nouveau)
# ═══════════════════════════════════════════════════════════════════════════════

def validate_generated_instructions(instrs: list, recipe: dict) -> tuple[bool, list[str]]:
    """
    Valide les instructions produites par le LLM.
    Retourne (ok: bool, raisons: list[str]).
    """
    reasons = []

    if not instrs or len(instrs) < 3:
        reasons.append("trop_peu_etapes")
        return False, reasons

    text = " ".join(instrs).lower()

    # Durée obligatoire seulement pour les plats avec cuisson effective
    cook_min_check = (recipe.get("timing") or {}).get("cook_min", 0)
    if cook_min_check and cook_min_check > 0:
        if not re.search(r"\b(min|minutes|heure|h\b)", text, re.I):
            reasons.append("pas_de_duree_malgre_cuisson")

    # Température pour les plats chauds
    cook_min = (recipe.get("timing") or {}).get("cook_min", 0)
    if cook_min and cook_min > 10:
        if not re.search(r"(°C|\bfeu\s+(vif|doux|moyen|fort)|four|\bchaud\b)", text, re.I):
            reasons.append("pas_temperature_malgre_cuisson")

    # Détection d'hallucinations — approche positive (patterns réellement suspects)
    # On ne cherche PAS à lister tous les mots culinaires légitimes (impossible).
    # On détecte uniquement des signaux forts et rares d'invention :
    #   - noms de viandes/poissons dans une recette végétarienne
    #   - mentions de marques commerciales
    #   - mesures aberrantes (ex: "500 litres")
    diet_flags = recipe.get("diet_flags") or {}
    is_vegetarian = diet_flags.get("vegetarian", True)  # on suppose végé par défaut

    if is_vegetarian:
        # Ingrédients carnés qui ne devraient jamais apparaître
        MEAT_PATTERN = r"\b(poulet|boeuf|porc|agneau|veau|canard|lapin|saumon|thon|crevette|lardons|jambon|bacon|anchois|merlan|cabillaud)\b"
        if re.search(MEAT_PATTERN, text, re.I):
            reasons.append("hallucination_viande_dans_recette_vegetarienne")
    # Longueur moyenne des étapes
    avg = sum(len(i) for i in instrs) / len(instrs)
    if avg < 40:
        reasons.append("etapes_trop_courtes")

    ok = len(reasons) == 0
    return ok, reasons

# ═══════════════════════════════════════════════════════════════════════════════
# PROMPT DE RÉÉCRITURE — enrichi
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM = (
    "Tu es chef cuisinier professionnel spécialisé en cuisine végétarienne internationale. "
    "Tu réponds UNIQUEMENT en JSON valide, sans markdown, sans texte avant ou après. "
    "Tu ne mentionnes JAMAIS un ingrédient absent de la liste fournie. "
    "Si une information manque (température exacte, durée précise), tu estimes de façon réaliste "
    "en cohérence avec le type de plat — tu n'inventes pas d'ingrédients."
)

def build_prompt(batch: list) -> str:
    items = []
    for r in batch:
        # Composition enrichie avec quantités (nouveau)
        composition_detail = []
        for c in (r.get("composition") or [])[:14]:
            ing = c.get("ingredient", "").replace("_", " ")
            qty = c.get("quantity")
            unit = c.get("unit", "")
            meta_role = (c.get("meta") or {}).get("role", "")
            part = f"{ing}"
            if qty:
                part += f" ({qty}{' ' + unit if unit else ''})"
            if meta_role:
                part += f" [rôle:{meta_role}]"
            composition_detail.append(part)

        # Techniques issues du meta (nouveau)
        techniques = []
        for c in (r.get("composition") or []):
            t = (c.get("meta") or {}).get("technique", "")
            if t and t not in techniques:
                techniques.append(t)

        items.append({
            "id":          r["id"],
            "titre":       r["titles"].get("fr") or r["titles"].get("en", ""),
            "cuisine":     (r.get("origin") or {}).get("cuisine", ""),
            "dish_type":   r.get("dish_type", ""),
            "portions":    r.get("servings", 4),
            "cuisson_min": (r.get("timing") or {}).get("cook_min", 0),
            "prep_min":    (r.get("timing") or {}).get("prep_active_min", 0),
            "diet_flags":  [k for k, v in (r.get("diet_flags") or {}).items() if v],
            "composition": composition_detail,   # enrichi avec quantités
            "techniques":  techniques,           # nouveau
            "equipement":  (r.get("equipment") or [])[:4],
            "instructions_actuelles": (r.get("instructions") or [])[:6],
        })

    return f"""Réécris les instructions de ces {len(batch)} recettes en français.

CONTRAINTES STRICTES :
- 5 à 7 étapes par recette, chaque étape entre 80 et 200 caractères
- Durées précises : "cuire 8 min à feu moyen-vif", "enfourner 25 min à 180°C"
- Températures systématiques pour four ou cuisson longue (≥ 5 min)
- Indicateurs sensoriels : coloration ("jusqu'à dorure blonde"), texture ("la lame ressort sèche"), son ("crépite légèrement"), odeur
- Verbes techniques : saisir, blanchir, nacrer, émulsionner, réduire, ciseler, brunoise, julienne
- Respecter le dish_type dans le registre (dip = onctueux, stir-fry = vif et rapide, etc.)
- INTERDICTION ABSOLUE : ne pas mentionner un ingrédient absent de la liste "composition"
- Si diet_flags contient "vegan" : pas de fromage, beurre, crème, œuf, miel
- Respecter les quantités fournies (ne pas inventer de proportions)

Réponds UNIQUEMENT avec ce JSON (sans markdown) :
[{{"id":"recipe_id","instructions":["étape 1","étape 2",...]}}]

Recettes :
{json.dumps(items, ensure_ascii=False, indent=2)}"""

# ═══════════════════════════════════════════════════════════════════════════════
# TRAITEMENT D'UN BATCH
# ═══════════════════════════════════════════════════════════════════════════════

def _retry_with_duration(api_key: str, recipe: dict, instrs: list) -> list:
    """
    Retry ciblé : demande au LLM d'ajouter des durées précises aux étapes existantes.
    Appelé uniquement quand le seul problème est l'absence de durée.
    """
    titre = recipe["titles"].get("fr") or recipe["titles"].get("en", "")
    cook_min = (recipe.get("timing") or {}).get("cook_min", 0)
    system = (
        "Tu es chef cuisinier. Tu réponds UNIQUEMENT en JSON valide, sans markdown."
    )
    prompt = (
        f"Ces instructions pour {titre!r} (cuisson: {cook_min} min) manquent de durees precises.\n"
        "Reecris-les en ajoutant une duree precise (ex: 3 min, 2 min a feu vif) "
        "a chaque etape qui implique une cuisson ou une attente.\n"
        "Reponds UNIQUEMENT avec un tableau JSON: [\"etape 1\", \"etape 2\", ...]\n\n"
        + "Instructions actuelles:\n" + json.dumps(instrs, ensure_ascii=False)
    )
    try:
        response = groq_chat(api_key, system, prompt, max_tokens=800, retries=2)
        result = extract_json(response)
        if isinstance(result, list) and len(result) >= 3:
            return result
    except Exception:
        pass
    return instrs  # fallback : retourner les instructions originales


write_lock = threading.Lock()


def process_batch(api_key: str, batch: list, recipes_map: dict,
                  batch_idx: int, total_batches: int) -> tuple[int, int]:
    titles = ", ".join(r["titles"].get("fr", "?") for r in batch)[:60]
    try:
        prompt   = build_prompt(batch)
        response = groq_chat(api_key, SYSTEM, prompt)
        results  = extract_json(response)

        ok = 0
        rejected = 0
        for item in results:
            rid    = item.get("id")
            instrs = item.get("instructions", [])
            if not rid or rid not in recipes_map:
                continue

            recipe = recipes_map[rid]

            # ── Post-validation LLM — avec retry ciblé ──────────────────
            valid, reasons = validate_generated_instructions(instrs, recipe)
            if not valid:
                # Retry unique avec prompt correctif si seul problème = durée manquante
                soft_reasons = {"pas_de_duree_malgre_cuisson"}
                if set(reasons) <= soft_reasons and api_key:
                    instrs = _retry_with_duration(api_key, recipe, instrs)
                    valid, reasons = validate_generated_instructions(instrs, recipe)

                if not valid:
                    with write_lock:
                        recipe.setdefault("_corrections_log", []).append(
                            f"[P2] réécriture rejetée: {'; '.join(reasons)}"
                        )
                        recipe["_rewrite_rejected"] = True
                    rejected += 1
                    print(f"    ⚠  [{batch_idx+1}/{total_batches}] rejet {rid[:20]} — {', '.join(reasons)}")
                    continue

            if len(instrs) >= 3:
                with write_lock:
                    recipe["instructions"] = instrs
                    recipe.pop("_needs_rewrite", None)
                    recipe.pop("_rewrite_rejected", None)
                    recipe["_rewritten"] = True
                    recipe.setdefault("_corrections_log", []).append(
                        "[P2] instructions réécrites par Groq/llama3"
                    )
                    # Mettre à jour le score qualité (nouveau)
                    recipe["_quality_score"] = compute_quality_score(recipe)
                    ok += 1

        fail = len(batch) - ok - rejected
        status = "✓" if ok == len(batch) else ("~" if ok > 0 else "✗")
        detail = f"ok={ok} rejet={rejected} fail={fail}"
        print(f"  {status} [{batch_idx+1}/{total_batches}] {detail} — {titles}...")
        return ok, len(batch) - ok

    except Exception as e:
        print(f"  ✗ [{batch_idx+1}/{total_batches}] ERREUR: {e} — {titles}")
        return 0, len(batch)

# ═══════════════════════════════════════════════════════════════════════════════
# MODE VALIDATE-ONLY — nouveau
# ═══════════════════════════════════════════════════════════════════════════════

def run_validate_only(recipes: list) -> None:
    """
    Parcourt toutes les recettes, applique la validation pré-réécriture
    et met à jour les champs _quality_score et _needs_rewrite sans LLM.
    """
    print("\n🔍  Mode validation seule (sans LLM)...\n")
    flagged = 0
    for r in recipes:
        issues = validate_recipe_pre(r)
        score  = compute_quality_score(r)
        r["_quality_score"] = score
        if issues:
            r.setdefault("_flags", [])
            for issue in issues:
                if issue not in r["_flags"]:
                    r["_flags"].append(issue)
            flagged += 1
        # Marquer pour réécriture si besoin
        if needs_rewrite(r) and not r.get("_rewritten"):
            r["_needs_rewrite"] = True

    print(f"  ✅  {len(recipes)} recettes validées")
    print(f"  ⚠   {flagged} recettes avec anomalies métier")
    print(f"  📝  {sum(1 for r in recipes if r.get('_needs_rewrite'))} recettes marquées pour réécriture")

# ═══════════════════════════════════════════════════════════════════════════════
# RAPPORT FINAL — nouveau
# ═══════════════════════════════════════════════════════════════════════════════

def print_quality_report(recipes: list) -> None:
    scores = [r.get("_quality_score", 0) for r in recipes if "_quality_score" in r]
    if not scores:
        return
    avg = sum(scores) / len(scores)
    below_05 = sum(1 for s in scores if s < 0.5)
    above_08 = sum(1 for s in scores if s >= 0.8)
    print(f"\n  📊  Score qualité moyen : {avg:.3f}")
    print(f"       > 0.80 : {above_08} recettes ({above_08*100//len(scores)}%)")
    print(f"       < 0.50 : {below_05} recettes ({below_05*100//len(scores)}%)")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ALIM — Réécriture instructions via Groq")
    parser.add_argument("--input",         required=True,        help="Fichier JSON source")
    parser.add_argument("--output",        required=True,        help="Fichier JSON résultat")
    parser.add_argument("--batch-size",    type=int, default=3,  help="Recettes par appel API (défaut: 3)")
    parser.add_argument("--workers",       type=int, default=1,  help="Appels parallèles (défaut: 1 — safe free tier Groq)")
    parser.add_argument("--max",           type=int, default=0,  help="Nb max de recettes à traiter (debug)")
    parser.add_argument("--resume",        action="store_true",  help="Reprendre depuis le fichier de sortie existant")
    parser.add_argument("--validate-only", action="store_true",  help="Validation métier seule, sans réécriture LLM")
    args = parser.parse_args()

    # ── Chargement ────────────────────────────────────────────────────────────
    source = args.output if args.resume and Path(args.output).exists() else args.input
    print(f"\n📂  Chargement de {source}...")
    with open(source, encoding="utf-8") as f:
        data = json.load(f)
    recipes = data.get("recipes", data) if isinstance(data, dict) else data
    recipes_map = {r["id"]: r for r in recipes}
    print(f"    {len(recipes)} recettes chargées")

    # ── Validation pré-réécriture (toujours effectuée) ────────────────────────
    print("\n🔎  Validation métier pré-réécriture...")
    pre_issues_count = 0
    for r in recipes:
        issues = validate_recipe_pre(r)
        if issues:
            r.setdefault("_flags", [])
            for issue in issues:
                if issue not in r["_flags"]:
                    r["_flags"].append(issue)
            pre_issues_count += 1
    print(f"    {pre_issues_count} recettes avec anomalies métier détectées")

    # ── Mode validate-only ────────────────────────────────────────────────────
    if args.validate_only:
        run_validate_only(recipes)
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n  💾  {args.output}")
        print_quality_report(recipes)
        return

    # ── Clé API ───────────────────────────────────────────────────────────────
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        print("❌  GROQ_API_KEY non définie.")
        print("    Dans PowerShell : $env:GROQ_API_KEY = 'gsk_...'")
        sys.exit(1)

    # ── Sélection des recettes à réécrire ─────────────────────────────────────
    to_fix = [r for r in recipes if needs_rewrite(r)]
    if args.max:
        to_fix = to_fix[:args.max]

    print(f"\n✦   {len(to_fix)} recettes à réécrire (instructions insuffisantes)")
    if not to_fix:
        print("    Rien à faire — toutes les instructions sont déjà de bonne qualité.")
        print_quality_report(recipes)
        return

    batches   = [to_fix[i:i+args.batch_size] for i in range(0, len(to_fix), args.batch_size)]
    n_batches = len(batches)
    print(f"    {n_batches} appels Groq prévus · batch={args.batch_size} · workers={args.workers}")
    print(f"    Durée estimée : ~{n_batches * 3 // args.workers} secondes\n")

    # ── Traitement parallèle ──────────────────────────────────────────────────
    total_ok = total_fail = 0
    start = time.time()
    done_count = 0

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = {
            ex.submit(process_batch, api_key, batch, recipes_map, idx, n_batches): idx
            for idx, batch in enumerate(batches)
        }
        for fut in as_completed(futures):
            try:
                ok, fail = fut.result()
                total_ok   += ok
                total_fail += fail
            except Exception as e:
                idx = futures[fut]
                print(f"  ✗ Batch {idx+1} exception: {e}")
                total_fail += args.batch_size

            done_count += 1
            if done_count % 10 == 0:
                with open(args.output, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                print(f"  💾  Checkpoint ({done_count * args.batch_size} recettes traitées)")

    # ── Sauvegarde finale ─────────────────────────────────────────────────────
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    elapsed = time.time() - start
    print(f"\n{'═'*55}")
    print(f"  ✅  {total_ok} recettes réécrites  |  ✗ {total_fail} échecs")
    print(f"  ⏱   {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  💾  {args.output}")
    print_quality_report(recipes)


if __name__ == "__main__":
    main()