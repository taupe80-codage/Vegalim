"""
ALIM — Correcteur de recettes autonome (fichier unique)
Aucun dossier config/ engine/ sources/ requis.

Usage :
    python alim_corriger.py --input recipes.json --output recipes_v3.json
"""
import json, re, sys, time, argparse, threading
from pathlib import Path
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════════════════════

ALLERGEN_MAP = {
    "flour":"gluten","wheat":"gluten","rye":"gluten","barley":"gluten",
    "oat":"gluten","spelt":"gluten","semolina":"gluten","bread":"gluten",
    "pasta":"gluten","couscous":"gluten","bulgur":"gluten","seitan":"gluten",
    "soy_sauce":"gluten","breadcrumbs":"gluten","pita":"gluten","naan":"gluten",
    "milk":"lactose","cream":"lactose","butter":"lactose","cheese":"lactose",
    "yogurt":"lactose","parmesan":"lactose","mozzarella":"lactose",
    "ricotta":"lactose","mascarpone":"lactose","feta":"lactose",
    "halloumi":"lactose","ghee":"lactose","cheddar":"lactose",
    "goat_cheese":"lactose","cream_cheese":"lactose","sour_cream":"lactose",
    "egg":"eggs","eggs":"eggs","mayonnaise":"eggs",
    "soy":"soy","tofu":"soy","tempeh":"soy","edamame":"soy","miso":"soy",
    "tamari":"soy","soy_milk":"soy",
    "walnut":"tree_nuts","hazelnut":"tree_nuts","almond":"tree_nuts",
    "cashew":"tree_nuts","pistachio":"tree_nuts","pecan":"tree_nuts",
    "macadamia":"tree_nuts","pine_nut":"tree_nuts","chestnut":"tree_nuts",
    "peanut":"peanuts","peanut_butter":"peanuts",
    "sesame":"sesame","tahini":"sesame","sesame_oil":"sesame",
    "salmon":"fish","tuna":"fish","cod":"fish","sardine":"fish",
    "anchovy":"fish","trout":"fish","fish_sauce":"fish",
    "shrimp":"crustaceans","prawn":"crustaceans","lobster":"crustaceans",
    "crab":"crustaceans","langoustine":"crustaceans",
    "mussel":"molluscs","oyster":"molluscs","squid":"molluscs",
    "celery":"celery","celeriac":"celery",
    "mustard":"mustard","mustard_seed":"mustard",
    "wine":"sulphites","vinegar":"sulphites","dried_fruit":"sulphites",
    "lupin":"lupin",
}

NON_VEGAN = {
    "milk","cream","butter","cheese","yogurt","parmesan","mozzarella","ricotta",
    "mascarpone","feta","halloumi","ghee","cheddar","goat_cheese","cream_cheese",
    "sour_cream","condensed_milk","egg","eggs","honey","fish","salmon","tuna",
    "cod","sardine","anchovy","shrimp","prawn","lobster","crab","gelatin","lard",
    "fish_sauce","worcestershire_sauce",
}
NON_VEGETARIAN = NON_VEGAN | {
    "beef","pork","lamb","veal","chicken","turkey","duck","rabbit","venison",
    "bacon","ham","prosciutto","chorizo","salami","pepperoni","meat","sausage",
}
GLUTEN_ING = {
    "flour","wheat","rye","barley","oat","spelt","semolina","bread","pasta",
    "couscous","bulgur","seitan","breadcrumbs","pita","soy_sauce",
}
LACTOSE_ING = {
    "milk","cream","butter","cheese","yogurt","parmesan","mozzarella","ricotta",
    "mascarpone","feta","halloumi","ghee","cheddar","goat_cheese","cream_cheese",
    "sour_cream","condensed_milk",
}
NUT_ING = {
    "walnut","hazelnut","almond","cashew","pistachio","pecan","macadamia",
    "pine_nut","peanut","peanut_butter",
}
SPICE_CLAMP = {
    "cumin":8,"turmeric":5,"garlic":30,"chili":5,"cinnamon":6,
    "clove":3,"nutmeg":3,"cardamom":4,"saffron":1,"cayenne":4,
    "smoked_paprika":8,"curry_powder":10,"ginger":15,"paprika":10,
}
VISUAL_MARKERS = [
    "dore","fondant","croustillant","texture","couleur","caramelise",
    "translucide","ebullition","fremiss","brunir","homogene","brillant",
    "reduit","al dente","coloration","reduction","nacre","saisie","cremeux",
    "golden","browned","crispy","tender","simmering","absorbed","caramelized",
]
BOILERPLATE = [
    re.compile(r"le bouillon doit etre riche", re.I),
    re.compile(r"gouter.*rectifier.*servir chaud et bien presente", re.I),
]

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def get_ingredients(r):
    """Retourne la liste des noms d'ingrédients d'une recette."""
    comp = r.get("composition") or []
    return [c.get("ingredient","").lower() for c in comp if c.get("ingredient")]

def get_tags_diet(r):
    tags = r.get("tags") or {}
    if isinstance(tags, dict):
        return set(tags.get("diet", []))
    return set()

def get_tags_allergens(r):
    tags = r.get("tags") or {}
    if isinstance(tags, dict):
        return set(tags.get("allergens", []))
    return set()

def parse_grams(qty, unit):
    try:
        qty_f = float(qty)
        unit = str(unit).lower()
        if unit == "kg": return qty_f * 1000
        if unit == "g":  return qty_f
    except: pass
    return None

# ═══════════════════════════════════════════════════════════════════════════════
# DÉTECTION DES PROBLÈMES
# ═══════════════════════════════════════════════════════════════════════════════

def detect_issues(r):
    issues = []
    instrs = r.get("instructions") or []
    text   = " ".join(instrs).lower()
    ings   = get_ingredients(r)
    ing_set = set(ings)
    tags_diet = get_tags_diet(r)

    # Instructions
    if instrs:
        avg = sum(len(i) for i in instrs) / len(instrs)
        if avg < 55:                                    issues.append("trop_courtes")
        if len(instrs) < 4:                             issues.append("trop_peu_etapes")
        if not re.search(r"(°C|\bfeu\s+(vif|doux|moyen))", text, re.I): issues.append("no_temperature")
        if not re.search(r"\b(min|minutes)\b", text, re.I):             issues.append("no_duration")
        if not any(m in text for m in VISUAL_MARKERS): issues.append("visuel_absent")
        if len(re.findall(r"\b(faire|mettre|preparer)\b", text, re.I)) >= 3: issues.append("techniques_vagues")
        if any(p.search(text) for p in BOILERPLATE):   issues.append("boilerplate")

    # Ingrédients
    if "vegan" in tags_diet and ing_set & NON_VEGAN:        issues.append("tag_vegan_incorrect")
    if "vegetarian" in tags_diet and ing_set & NON_VEGETARIAN: issues.append("tag_vegetarian_incorrect")
    if "gluten_free" in " ".join(tags_diet) and ing_set & GLUTEN_ING: issues.append("tag_gluten_incorrect")

    # Quantités suspectes
    for c in r.get("composition") or []:
        ing  = c.get("ingredient","").lower()
        grams = parse_grams(c.get("quantity"), c.get("unit",""))
        if grams and ing in SPICE_CLAMP and grams > SPICE_CLAMP[ing]:
            issues.append(f"qty_suspecte:{ing}")

    # Allergènes manquants
    detected = {ALLERGEN_MAP[i] for i in ing_set if i in ALLERGEN_MAP}
    declared = get_tags_allergens(r)
    if detected - declared:
        issues.append("allergenes_manquants")

    return issues

# ═══════════════════════════════════════════════════════════════════════════════
# CORRECTIONS AUTOMATIQUES (sans LLM)
# ═══════════════════════════════════════════════════════════════════════════════

def auto_correct(r):
    changes = []
    ing_set = set(get_ingredients(r))
    tags    = r.get("tags") or {}
    if not isinstance(tags, dict):
        tags = {}
    diet_tags = set(tags.get("diet", []))
    diet_flags = r.get("diet_flags") or {}

    # 1. Tags régimes
    if "vegan" in diet_tags and ing_set & NON_VEGAN:
        diet_tags.discard("vegan")
        offenders = sorted(ing_set & NON_VEGAN)[:3]
        changes.append(f"tag_vegan_retire ({','.join(offenders)})")

    if "vegetarian" in diet_tags and ing_set & NON_VEGETARIAN:
        diet_tags.discard("vegetarian")
        offenders = sorted(ing_set & NON_VEGETARIAN)[:3]
        changes.append(f"tag_vegetarian_retire ({','.join(offenders)})")

    if "gluten_free" in diet_tags and ing_set & GLUTEN_ING:
        diet_tags.discard("gluten_free")
        offenders = sorted(ing_set & GLUTEN_ING)[:2]
        changes.append(f"tag_gluten_free_retire ({','.join(offenders)})")

    # Ajouter les tags corrects manquants
    is_veg  = not bool(ing_set & NON_VEGETARIAN)
    is_vegan = is_veg and not bool(ing_set & NON_VEGAN)
    is_gf   = not bool(ing_set & GLUTEN_ING)
    is_lf   = not bool(ing_set & LACTOSE_ING)
    is_nf   = not bool(ing_set & NUT_ING)

    if is_vegan and "vegan" not in diet_tags:
        diet_tags.add("vegan"); changes.append("tag_vegan_ajoute")
    if is_veg and "vegetarian" not in diet_tags:
        diet_tags.add("vegetarian"); changes.append("tag_vegetarian_ajoute")
    if is_gf and "gluten_free" not in diet_tags:
        diet_tags.add("gluten_free"); changes.append("tag_gluten_free_ajoute")

    tags["diet"] = sorted(diet_tags)
    r["tags"] = tags

    # 2. Sync diet_flags
    new_flags = {"vegan":is_vegan,"vegetarian":is_veg,"gluten_free":is_gf,
                 "lactose_free":is_lf,"nut_free":is_nf}
    for k, v in new_flags.items():
        if diet_flags.get(k) != v:
            changes.append(f"flag_{k}→{v}")
    r["diet_flags"] = new_flags

    # 3. Allergènes EU
    detected = {ALLERGEN_MAP[i] for i in ing_set if i in ALLERGEN_MAP}
    declared = set(tags.get("allergens", []))
    missing  = detected - declared
    if missing:
        tags["allergens"] = sorted(declared | detected)
        changes.append(f"allergenes_ajoutes:{','.join(sorted(missing))}")
    r["tags"] = tags

    # 4. Clamp quantités suspectes
    for c in r.get("composition") or []:
        ing   = c.get("ingredient","").lower()
        grams = parse_grams(c.get("quantity"), c.get("unit",""))
        if grams and ing in SPICE_CLAMP and grams > SPICE_CLAMP[ing]:
            new_g = round(SPICE_CLAMP[ing] * 0.75, 1)
            old   = f"{c['quantity']}{c.get('unit','')}"
            c["quantity"] = new_g
            c["unit"]     = "g"
            changes.append(f"qty_clamp:{ing} {old}→{new_g}g")

    # 5. Flag instructions à réécrire
    style_issues = [i for i in detect_issues(r) if i in {
        "trop_courtes","trop_peu_etapes","no_temperature",
        "no_duration","visuel_absent","techniques_vagues","boilerplate"
    }]
    if style_issues:
        r["_needs_rewrite"] = style_issues

    if changes:
        r.setdefault("_corrections_log", []).extend(changes)

    return changes

# ═══════════════════════════════════════════════════════════════════════════════
# QUALITY SCORE
# ═══════════════════════════════════════════════════════════════════════════════

def quality_score(r):
    issues = detect_issues(r)
    score  = 1.0 - len(issues) * 0.08
    instrs = r.get("instructions") or []
    text   = " ".join(instrs)
    if len(r.get("composition",[])) >= 6: score += 0.05
    if len(instrs) >= 5:                  score += 0.05
    if re.search(r"(°C|\bfeu\s+(vif|doux|moyen))", text, re.I): score += 0.05
    if re.search(r"\b\d+\s*min", text, re.I):                    score += 0.05
    return round(max(0.0, min(1.0, score)), 3)

# ═══════════════════════════════════════════════════════════════════════════════
# RAPPORT QUALITÉ
# ═══════════════════════════════════════════════════════════════════════════════

def print_report(recipes, label=""):
    print(f"\n{'═'*55}")
    if label: print(f"  {label}")
    all_issues = [detect_issues(r) for r in recipes]
    issue_count = Counter(i for issues in all_issues for i in issues)
    scores = [quality_score(r) for r in recipes]
    avg = sum(scores)/len(scores) if scores else 0
    needs_rewrite = sum(1 for r in recipes if r.get("_needs_rewrite"))

    print(f"  Recettes totales     : {len(recipes)}")
    print(f"  Score moyen          : {avg:.3f}")
    print(f"  Score ≥ 0.8          : {sum(1 for s in scores if s >= 0.8)}")
    print(f"  Score < 0.6          : {sum(1 for s in scores if s < 0.6)}")
    print(f"  Nécessitent réécriture (LLM) : {needs_rewrite}")
    if issue_count:
        print(f"\n  Top problèmes :")
        for issue, count in issue_count.most_common(10):
            bar = "█" * (count // max(1, len(recipes)//40))
            print(f"    {issue:<40} {count:>4}  {bar}")

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ALIM — Correcteur de recettes autonome")
    parser.add_argument("--input",  required=True,  help="Fichier JSON source (recipes.json)")
    parser.add_argument("--output", required=True,  help="Fichier JSON corrigé")
    parser.add_argument("--report-only", action="store_true", help="Afficher le rapport sans corriger")
    parser.add_argument("--min-score",   type=float, default=0.0, help="Score minimum à afficher")
    args = parser.parse_args()

    # Chargement
    print(f"\n📂  Chargement de {args.input}...")
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    recipes = data.get("recipes", data) if isinstance(data, dict) else data
    print(f"    {len(recipes)} recettes chargées")

    # Rapport initial
    print_report(recipes, "Analyse initiale")

    if args.report_only:
        return

    # Corrections
    print(f"\n🔧  Correction en cours...")
    total_changes = 0
    total_corrected = 0
    start = time.time()

    for r in recipes:
        changes = auto_correct(r)
        r["_quality_score"] = quality_score(r)
        if changes:
            total_corrected += 1
            total_changes   += len(changes)

    elapsed = time.time() - start

    # Rapport final
    print_report(recipes, "Analyse post-correction")

    # Sauvegarde
    if isinstance(data, dict) and "recipes" in data:
        data["recipes"] = recipes
        out = data
    else:
        out = {"recipes": recipes}

    out.setdefault("metadata", {}).update({
        "corrected_by": "alim_corriger.py",
        "corrections_count": total_changes,
        "recipes_corrected": total_corrected,
    })

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"\n{'═'*55}")
    print(f"  ✅  {total_corrected} recettes corrigées ({total_changes} corrections)")
    print(f"  ⏱   {elapsed:.1f}s")
    print(f"  💾  {args.output}")

if __name__ == "__main__":
    main()
