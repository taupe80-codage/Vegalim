"""
ALIM — Correcteur post-pipeline (alim_corrector.py)
Corrige les problèmes critiques réels identifies dans recipes_v4.json.

Problemes traites :
  1. Vegan flag = True MAIS produit animal dans composition -> correction flag
  2. Vegan flag = True MAIS produit animal dans instructions -> flag d'alerte
  3. Viande/poisson dans instructions recette vegetarienne -> flag bloquant + revue manuelle
  4. _flags bruites (ingredient_mismatch_potential) -> suppression complete
  5. _quality_score non discriminant (82% a 1.0) -> recalcul reel penalisant

Usage :
    python alim_corrector.py --input recipes_v4.json --output recipes_v5.json
    python alim_corrector.py --input recipes_v4.json --output recipes_v5.json --dry-run
    python alim_corrector.py --input recipes_v4.json --output recipes_v5.json --report
"""

import json, re, argparse
from collections import defaultdict

# ═══════════════════════════════════════════════════════════════════════════════
# PATTERNS
# ═══════════════════════════════════════════════════════════════════════════════

ANIMAL_IN_INSTRS = re.compile(
    r"\b(creme fraiche|creme fraiche|sour cream|heavy cream|"
    r"fromage blanc|fromage frais|fromage|cheese|parmesan|gruyere|emmental|"
    r"mozzarella|feta|ricotta|chevre|goat cheese|"
    r"beurre|butter|lait|milk|creme|cream|"
    r"yaourt|yogurt|yoghurt|"
    r"miel|honey|"
    r"oeuf|oeufs|egg|eggs)\b",
    re.I,
)

# Version avec accents pour recherche dans texte reel
ANIMAL_IN_INSTRS_FR = re.compile(
    r"cr[eè]me\s+fra[iî]che|cr[eè]me\s+fleurette|cr[eè]me\s+liquide|"
    r"cr[eè]me\s+fouett[eé]e|fromage\s+blanc|fromage\s+frais|"
    r"\bfromage\b|\bcr[eè]me\b|\bbeurre\b|\blait\b|\byaourt\b|"
    r"\bparmesan\b|\bgruy[eè]re\b|\bfeta\b|\bricotta\b|\bch[eè]vre\b|"
    r"\bmozzarella\b|\bemmental\b|\bgouda\b|\bcheddar\b|"
    r"\bmiel\b|\bhoney\b|\boeuf\b|\boeufs\b|\begg\b|\beggs\b|"
    r"\bbutter\b|\bmilk\b|\byogurt\b|\byoghurt\b",
    re.I,
)

MEAT_IN_INSTRS = re.compile(
    r"\b(poulet|boeuf|porc|agneau|veau|canard|lapin|pintade|"
    r"saumon|thon|cabillaud|merlan|dorade|crevette|langoustine|homard|"
    r"lardons|jambon|bacon|pancetta|chorizo|saucisse|anchois|sardine|"
    r"chicken|beef|pork|lamb|turkey|dinde|veal|rabbit|duck|"
    r"tuna|salmon|shrimp|prawn|lobster|mussel)\b",
    re.I,
)

ANIMAL_IN_COMP = {
    "cream","heavy_cream","sour_cream","whipping_cream","creme_fraiche",
    "fromage","cheese","parmesan","gruyere","emmental","mozzarella","feta",
    "ricotta","goat_cheese","chevre","brie","camembert","cheddar","gorgonzola",
    "butter","beurre",
    "milk","lait","whole_milk","skim_milk","condensed_milk",
    "cream_cheese","fromage_blanc","fromage_frais",
    "yogurt","yoghurt","yaourt","greek_yogurt",
    "honey","miel",
    "egg","eggs","oeuf","oeufs","egg_yolk","egg_white","jaune_oeuf","blanc_oeuf",
    "ghee","lard",
    "gelatin","gelatine",
}

MEAT_IN_COMP = {
    "chicken","beef","pork","lamb","veal","turkey","duck","rabbit",
    "poulet","boeuf","porc","agneau","veau","dinde","canard","lapin",
    "bacon","lardons","jambon","ham","pancetta","prosciutto","chorizo",
    "saucisse","sausage","salami","pepperoni",
    "anchovy","anchois","tuna","thon","salmon","saumon","cod","cabillaud",
    "shrimp","crevette","prawn","lobster","homard","crab","mussel","moule",
    "fish_sauce","oyster_sauce","worcestershire",
}

# ═══════════════════════════════════════════════════════════════════════════════
# SCORE QUALITE REEL — discriminant
# ═══════════════════════════════════════════════════════════════════════════════

VISUAL_MARKERS = {
    "dore","blonde","doree","fondant","croustillant","translucide","caramelise",
    "fremiss","brunir","homogene","brillant","al dente","coloration","reduction",
    "nacre","saisi","evapor","crepite","lisse","ferme","onctueux","veloute",
    "golden","browned","crispy","tender","simmering","caramelized","glossy",
}

TECH_VERBS = re.compile(
    r"\b(saisir|blanchir|nacrer|emulsionner|reduire|ciseler|julienne|brunoise|"
    r"deglacer|pocher|rissoler|flamber|gratiner|infuser|monter|incorporer|"
    r"concasser|zester|emincer|chiffonade|lier|napper)\b", re.I,
)


def _strip_accents(text):
    """Normalise pour comparaison sans accents."""
    import unicodedata
    return ''.join(
        c for c in unicodedata.normalize('NFD', text)
        if unicodedata.category(c) != 'Mn'
    ).lower()


def compute_quality_score(r: dict) -> float:
    """Score qualite discriminant. Penalise les vrais problemes."""
    score = 0.0

    instrs = r.get("instructions") or []
    composition = r.get("composition") or []
    diet_flags = r.get("diet_flags") or {}
    timing = r.get("timing") or {}
    description = r.get("description") or ""
    origin = r.get("origin") or {}

    # Dimension 1 — Instructions (35 pts max)
    if instrs:
        text = " ".join(instrs)
        text_low = _strip_accents(text)
        avg_len = sum(len(i) for i in instrs) / len(instrs)
        n = len(instrs)

        if avg_len >= 100:   score += 12
        elif avg_len >= 70:  score += 8
        elif avg_len >= 50:  score += 5

        if n >= 5:    score += 10
        elif n >= 4:  score += 7
        elif n >= 3:  score += 4

        if re.search(r"(°C|\bfeu\s+(vif|doux|moyen)|\bfour\b)", text, re.I):
            score += 8

        if re.search(r"\b(min|minutes|heure)\b", text, re.I):
            score += 3

        if any(m in text_low for m in VISUAL_MARKERS):
            score += 1

        if TECH_VERBS.search(text):
            score += 1
    # max possible = 35

    # Dimension 2 — Composition (20 pts max)
    n_comp = len(composition)
    if n_comp >= 8:    score += 20
    elif n_comp >= 5:  score += 15
    elif n_comp >= 3:  score += 10
    elif n_comp >= 1:  score += 5

    # Dimension 3 — Timing (10 pts max)
    total_min = timing.get("total_min", 0)
    prep = timing.get("prep_active_min", 0)
    if total_min and total_min > 0:  score += 10
    elif prep and prep > 0:          score += 5

    # Dimension 4 — Description (10 pts max)
    if len(description) >= 100:  score += 10
    elif len(description) >= 50: score += 7
    elif len(description) >= 20: score += 4

    # Dimension 5 — Origin (10 pts max)
    if origin.get("cuisine") and origin.get("country"):  score += 10
    elif origin.get("cuisine"):                           score += 5

    # Dimension 6 — Tags (10 pts max)
    tags = r.get("tags") or {}
    if tags.get("technique") and tags.get("diet"):  score += 10
    elif tags.get("diet"):                           score += 6
    elif tags.get("technique"):                      score += 4

    # Dimension 7 — Diet flags coherents (5 pts max, penalites si incoherents)
    score += 5  # bonus de base
    instr_text = _strip_accents(" ".join(instrs))
    comp_names = {c.get("ingredient","").lower() for c in composition}

    if diet_flags.get("vegan"):
        if ANIMAL_IN_INSTRS_FR.search(" ".join(instrs)):
            score -= 15  # penalite forte : incoherence flagrante
        animal_comp = comp_names & ANIMAL_IN_COMP
        if animal_comp:
            score -= 20  # penalite tres forte : composition incompatible

    if diet_flags.get("vegetarien") or diet_flags.get("vegetarian"):
        if MEAT_IN_INSTRS.search(" ".join(instrs)):
            score -= 25  # bloquant
        meat_comp = comp_names & MEAT_IN_COMP
        if meat_comp:
            score -= 25

    # Normaliser sur 100 pts max theorique
    return round(max(0.0, min(1.0, score / 100.0)), 3)


# ═══════════════════════════════════════════════════════════════════════════════
# CORRECTEURS
# ═══════════════════════════════════════════════════════════════════════════════

def fix_flags_noise(r: dict) -> list:
    """Supprime les _flags ingredient_mismatch_potential (100% faux positifs)."""
    old = r.get("_flags") or []
    clean = [f for f in old if "ingredient_mismatch_potential" not in f]
    if len(clean) != len(old):
        r["_flags"] = clean
        return [f"flags_noise_removed:{len(old)-len(clean)}"]
    return []


def fix_vegan_coherence(r: dict, dry_run: bool) -> list:
    """Corrige les incohérences vegan."""
    corrections = []
    diet_flags = r.get("diet_flags") or {}
    if not diet_flags.get("vegan"):
        return corrections

    composition = r.get("composition") or []
    instrs = r.get("instructions") or []
    comp_names = {c.get("ingredient","").lower() for c in composition}

    # 1. Composition incompatible avec vegan -> corriger le flag
    animal_comp = comp_names & ANIMAL_IN_COMP
    meat_comp = comp_names & MEAT_IN_COMP
    incompatible = animal_comp | meat_comp

    if incompatible:
        if not dry_run:
            r["diet_flags"]["vegan"] = False
            # Retirer aussi lactose_free si produit laitier present
            dairy = {"butter","beurre","milk","lait","cream","fromage","cheese",
                     "yogurt","yaourt","ghee"}
            if animal_comp & dairy:
                r["diet_flags"]["lactose_free"] = False
            flag = f"vegan_corrected:composition:{','.join(sorted(incompatible)[:3])}"
            r.setdefault("_flags", []).append(flag)
            r.setdefault("_corrections_log", []).append(
                f"[corrector] vegan=False — composition contient: {','.join(sorted(incompatible)[:3])}"
            )
        corrections.append(f"vegan_flag_corrected:{','.join(sorted(incompatible)[:3])}")

    # 2. Instructions mentionnent produit animal (composition OK) -> flag alerte
    else:
        match = ANIMAL_IN_INSTRS_FR.search(" ".join(instrs))
        if match:
            if not dry_run:
                flag = f"vegan_alert:instructions_mention:{match.group().strip()}"
                flags = r.get("_flags") or []
                if not any("vegan_alert" in f for f in flags):
                    r.setdefault("_flags", []).append(flag)
                    r.setdefault("_corrections_log", []).append(
                        f"[corrector] ALERTE: instructions mentionnent '{match.group().strip()}' "
                        f"malgre vegan=True — verification manuelle requise"
                    )
            corrections.append(f"vegan_instruction_alert:{match.group().strip()}")

    return corrections


def fix_meat_in_vegetarian(r: dict, dry_run: bool) -> list:
    """Detecte viande dans recette vegetarienne -> flag bloquant."""
    corrections = []
    diet_flags = r.get("diet_flags") or {}
    if not (diet_flags.get("vegetarien") or diet_flags.get("vegetarian")):
        return corrections

    instrs = r.get("instructions") or []
    match = MEAT_IN_INSTRS.search(" ".join(instrs))
    if match:
        if not dry_run:
            flag = f"BLOQUANT:viande_instructions:{match.group()}"
            flags = r.get("_flags") or []
            if not any("BLOQUANT" in f for f in flags):
                r.setdefault("_flags", []).append(flag)
                r.setdefault("_corrections_log", []).append(
                    f"[corrector] BLOQUANT: '{match.group()}' dans recette vegetarienne"
                )
            r["_needs_manual_review"] = True
        corrections.append(f"meat_in_vegetarian:{match.group()}")

    return corrections


# ═══════════════════════════════════════════════════════════════════════════════
# RAPPORT
# ═══════════════════════════════════════════════════════════════════════════════

def print_report(all_corrections: dict, recipes: list, full: bool) -> None:
    print(f"\n{'=':=<60}")
    print("  RAPPORT DE CORRECTION")
    print(f"{'=':=<60}")

    total = sum(len(v) for v in all_corrections.values())
    print(f"\n  {total} corrections sur {len(recipes)} recettes ({len(all_corrections)} recettes modifiees)")

    cats = defaultdict(int)
    for corrs in all_corrections.values():
        for c in corrs:
            cats[c.split(":")[0]] += 1

    print("\n  Par type :")
    for cat, n in sorted(cats.items(), key=lambda x: -x[1]):
        print(f"    {n:4d}  {cat}")

    scores = [r.get("_quality_score", 0) for r in recipes]
    avg = sum(scores) / len(scores) if scores else 0
    print(f"\n  Score qualite moyen apres correction : {avg:.3f}")
    buckets = [
        ("superieur 0.90", sum(1 for s in scores if s >= 0.90)),
        ("0.70 a 0.89",    sum(1 for s in scores if 0.70 <= s < 0.90)),
        ("0.50 a 0.69",    sum(1 for s in scores if 0.50 <= s < 0.70)),
        ("inferieur 0.50", sum(1 for s in scores if s < 0.50)),
    ]
    for label, n in buckets:
        bar = "#" * (n * 40 // max(len(recipes), 1))
        print(f"    {label:16s} {n:4d}  {bar}")

    manual = [r["id"] for r in recipes if r.get("_needs_manual_review")]
    if manual:
        print(f"\n  REVUE MANUELLE REQUISE : {len(manual)} recettes")
        for rid in manual:
            print(f"    - {rid}")

    vegan_alerts = [
        r["id"] for r in recipes
        if any("vegan_alert" in f for f in (r.get("_flags") or []))
    ]
    if vegan_alerts:
        print(f"\n  ALERTE VEGAN (instructions) : {len(vegan_alerts)} recettes")
        if full:
            for rid in vegan_alerts:
                r = next(x for x in recipes if x["id"] == rid)
                flag = next(f for f in r.get("_flags",[]) if "vegan_alert" in f)
                print(f"    - {rid[:45]} | {flag}")

    if full and all_corrections:
        print(f"\n{'─':─<60}")
        print("  DETAIL COMPLET")
        print(f"{'─':─<60}")
        for rid, corrs in sorted(all_corrections.items()):
            print(f"\n  {rid}")
            for c in corrs:
                print(f"    -> {c}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="ALIM — Correcteur post-pipeline")
    parser.add_argument("--input",   required=True)
    parser.add_argument("--output",  required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--report",  action="store_true", help="Rapport detaille complet")
    args = parser.parse_args()

    print(f"\nChargement de {args.input}...")
    with open(args.input, encoding="utf-8") as f:
        data = json.load(f)
    recipes = data.get("recipes", data) if isinstance(data, dict) else data
    print(f"  {len(recipes)} recettes chargees")
    if args.dry_run:
        print("  Mode dry-run — aucune ecriture\n")

    all_corrections = {}

    # Etape 1 — Nettoyage _flags bruites
    print("\nEtape 1 : Nettoyage _flags bruites...")
    n = 0
    for r in recipes:
        corrs = fix_flags_noise(r)
        if corrs:
            all_corrections.setdefault(r["id"], []).extend(corrs)
            n += 1
    print(f"  {n} recettes nettoyees")

    # Etape 2 — Coherence vegan
    print("\nEtape 2 : Coherence vegan...")
    n_fixed = n_alert = 0
    for r in recipes:
        corrs = fix_vegan_coherence(r, args.dry_run)
        if corrs:
            all_corrections.setdefault(r["id"], []).extend(corrs)
            for c in corrs:
                if "corrected" in c: n_fixed += 1
                if "alert" in c:     n_alert += 1
    print(f"  {n_fixed} flags vegan corriges (composition incompatible)")
    print(f"  {n_alert} alertes (instructions — verification manuelle)")

    # Etape 3 — Viande dans vegetarien
    print("\nEtape 3 : Viande dans recettes vegetariennes...")
    n = 0
    for r in recipes:
        corrs = fix_meat_in_vegetarian(r, args.dry_run)
        if corrs:
            all_corrections.setdefault(r["id"], []).extend(corrs)
            n += 1
    print(f"  {n} recettes flaggees BLOQUANT")

    # Etape 4 — Recalcul scores
    print("\nEtape 4 : Recalcul scores qualite...")
    old_perfect = sum(1 for r in recipes if r.get("_quality_score", 0) >= 0.99)
    for r in recipes:
        if not args.dry_run:
            r["_quality_score"] = compute_quality_score(r)
    new_below = sum(1 for r in recipes if r.get("_quality_score", 0) < 0.80)
    print(f"  {old_perfect} recettes etaient a 1.0")
    print(f"  {new_below} recettes maintenant sous 0.80 (problemes reels detectes)")

    # Rapport
    print_report(all_corrections, recipes, full=args.report)

    # Sauvegarde
    if not args.dry_run:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n  Sauvegarde : {args.output}")
    else:
        print(f"\n  (dry-run — {args.output} non ecrit)")


if __name__ == "__main__":
    main()
