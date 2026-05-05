#!/usr/bin/env python3
"""
fix_recipes_coherence.py — Étape 8 du pipeline ALIM v6
=======================================================
Audit et correction de cohérence du fichier recipes.json.

Contrôles appliqués :
  C1  lactose_free faux positifs  — ingrédients laitiers détectés
  C2  vegan faux positifs         — produits animaux détectés dans tags.diet
  C3  vegan tag vs diet_flags     — désynchronisation tags / flags
  C4  timing aberrant             — total_min incohérent avec prep+cook
  C5  description template        — "Soupe à base de [key_en], bouillon..." auto-générée
  C6  servings calibration        — valeur unique par défaut dish_type
  C7  titre dupliqué              — même titre FR sur 2 recettes distinctes
  C8  ingredient nom dans Vegan   — creme_fraiche dans recette étiquetée Vegan

Usage :
  python scripts/nutrition/fix_recipes_coherence.py                  # dry-run
  python scripts/nutrition/fix_recipes_coherence.py --apply          # application
  python scripts/nutrition/fix_recipes_coherence.py --apply --quiet  # silencieux
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────────────────

BASE_DIR     = Path(__file__).resolve().parents[2]
RECIPES_FILE = BASE_DIR / "backend" / "data" / "recipes" / "recipes.json"
LOG_FILE     = BASE_DIR / "backend" / "data" / "logs" / "coherence_corrections_log.json"

NOW = datetime.now(timezone.utc).isoformat()

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("fix_recipes_coherence")

# ── Vocabulaires ───────────────────────────────────────────────────────────────

# Produits laitiers ANIMAUX uniquement.
# cream_plant / milk_plant / yogurt_plant sont végétaux → exclus.
# Utilisé par C1 (lactose_free) et C8 (vegan name conflict).
DAIRY_INGREDIENTS = {
    "milk", "milk_animal", "cream", "cream_animal",
    "creme_fraiche", "heavy_cream", "butter", "dairy_butter",
    "cheese", "cheddar", "gruyere", "mozzarella", "parmesan",
    "feta", "ricotta", "mascarpone", "cream_cheese", "roquefort",
    "pecorino_romano", "fromage_blanc", "comté", "comte",
    "yogurt", "yogurt_animal", "greek_yogurt", "kefir",
    # NOTE : cream_plant / milk_plant / yogurt_plant volontairement absents
    # (produits végétaux, compatibles vegan et lactose_free)
}

PLANT_DAIRY = {
    "milk_plant", "cream_plant", "lait_coco", "lait_amande", "lait_avoine", 
    "lait_soja", "oat_milk", "almond_milk", "soy_milk", "coconut_milk",
    "cashew_cream", "coconut_cream", "plant_yogurt", "coconut_yogurt",
    "soy_cream", "creme_avoine", "creme_soja", "lait_vegetal"
}

ANIMAL_INGREDIENTS = {
    "chicken", "beef", "pork", "fish", "salmon", "tuna", "shrimp",
    "lamb", "turkey", "duck", "bacon", "ham", "sausage", "anchovy",
    "meat", "egg", "poulet", "boeuf", "porc", "saumon", "thon",
    "crevette", "agneau", "veau", "gelatin",
}

DAIRY_SUBSTITUTES = {
    # Substitutions véganes — utilisées par C8 auto-fix
    "creme_fraiche":   "cashew_cream",
    "heavy_cream":     "oat_cream",
    "butter":          "vegan_butter",
    "cream":           "cashew_cream",
    "milk_animal":     "milk_plant",
    "milk":            "milk_plant",
    "yogurt_animal":   "yogurt_plant",
    "yogurt":          "yogurt_plant",
    "cheese":          "vegan_cheese",
    "parmesan":        "vegan_parmesan",
    "feta":            "vegan_feta",
    "cheddar":         "vegan_cheddar",
    "gruyere":         "vegan_cheese",
    "ricotta":         "cashew_ricotta",
    "fromage_blanc":   "cashew_cream",
    "cream_cheese":    "cashew_cream",
    "mozzarella":      "vegan_mozzarella",
}

DEFAULT_SERVINGS: dict[str, int] = {
    "main":      4,
    "soup":      4,
    "side":      4,
    "starter":   4,
    "dessert":   6,
    "snack":     2,
    "breakfast": 2,
    "sauce":     8,
}

TEMPLATE_DESC_RGX = re.compile(
    # V14 FIX : whitelist des termes ING_FR acceptables dans les descriptions générées.
    # La regex ne doit pas matcher des termes qui sont des traductions légitimes
    # dans ING_FR (ex: "bok choy" est dans ING_FR → description correcte).
    # On cible uniquement : clés snake_case EN non traduites + termes anglais bruts.
    r"(bouillon riche en ar[oô]mes)"                    # template factory historique
    r"|\b[a-z][a-z0-9]*_[a-z][a-z0-9_]+\b"            # snake_case (ingredient_key EN)
    r"|\b(broth|white\s+bean|black\s+bean|split\s+pea"
    r"|miso\s+broth)\b",                               # mots anglais non traduits (dashi/noodle/bok choy exclus : dans ING_FR)
    re.I,
)

# Termes générés par _generate_description qui sont acceptables malgré leur forme.
# Ces descriptions ont déjà été corrigées — ne pas re-trigger C5.
DESCRIPTION_WHITELIST_PATTERNS = re.compile(
    r"\b(bok choy|dashi|noodle|soba|kabocha|tempeh|miso|kimchi|gundruk|attiéké"
    r"|edamame|quinoa|tahini|couscous|boulgour|gnocchi|udon|tofu)\b",
    re.I,
)

# Traductions basiques pour descriptions
ING_FR: dict[str, str] = {
    "eggplant": "aubergine", "tomato": "tomate", "onion": "oignon",
    "garlic": "ail", "ginger": "gingembre", "carrot": "carotte",
    "potato": "pomme de terre", "spinach": "épinards", "lentil": "lentilles",
    "chickpea": "pois chiches", "bean": "haricots", "rice": "riz",
    "pasta": "pâtes", "bread": "pain", "egg": "œufs", "cheese": "fromage",
    "tofu": "tofu", "mushroom": "champignons", "zucchini": "courgettes",
    "pepper": "poivrons", "cucumber": "concombre", "corn": "maïs",
    "pumpkin": "courge", "squash": "courge", "leek": "poireaux",
    "broccoli": "brocoli", "cauliflower": "chou-fleur", "cabbage": "chou",
    "celery": "céleri", "turnip": "navet", "beet": "betterave",
    "avocado": "avocat", "mango": "mangue", "coconut": "noix de coco",
    "lemon": "citron", "lime": "citron vert", "apple": "pomme",
    "walnut": "noix", "almond": "amandes", "cashew": "cajou",
    "peanut": "cacahuètes", "sesame": "sésame", "olive": "olives",
    "butter": "beurre", "cream": "crème", "milk": "lait",
    "yogurt": "yaourt", "tahini": "tahini", "miso": "miso",
    "vinegar": "vinaigre", "honey": "miel", "sugar": "sucre",
    "flour": "farine", "oats": "flocons d'avoine",
    "split_pea": "pois cassés", "udon": "udon", "noodle": "nouilles",
    "gnocchi": "gnocchi", "couscous": "couscous", "quinoa": "quinoa",
    "bulgur": "boulgour", "chestnut": "châtaignes", "edamame": "edamame",
    # ── V13 : traductions manquantes (identifiées via C5 run 2026-05) ────────
    "broth":             "bouillon",
    "white_bean":        "haricots blancs",   "white bean":        "haricots blancs",
    "black_bean":        "haricots noirs",    "black bean":        "haricots noirs",
    "bok_choy":          "bok choy",          "bok choy":          "bok choy",
    "kabocha":           "courge kabocha",
    "stale":             "pain rassis",
    "dried_bean":        "haricots secs",     "dried bean":        "haricots secs",
    "rice_paper":        "galette de riz",    "rice paper":        "galette de riz",
    "all_purpose_flour": "farine",            "all purpose flour": "farine",
    "green_papaya":      "papaye verte",      "green papaya":      "papaye verte",
    "napa_cabbage":      "chou chinois",      "napa cabbage":      "chou chinois",
    "red_bell_pepper":   "poivron rouge",     "red bell pepper":   "poivron rouge",
    "miso":              "miso",
    "tempeh":            "tempeh",
    "jackfruit":         "jacquier",
    "taro":              "taro",
    "soba":              "nouilles soba",
    "tofu":              "tofu",
    "kimchi":            "kimchi",
    "gundruk":           "gundruk",
    "attieke":           "attiéké",
}

CUISINE_ADJ: dict[str, str] = {
    "french": "française", "italian": "italienne", "greek": "grecque",
    "indian": "indienne", "japanese": "japonaise", "chinese": "chinoise",
    "korean": "coréenne", "thai": "thaïlandaise", "mexican": "mexicaine",
    "moroccan": "marocaine", "turkish": "turque", "lebanese": "libanaise",
    "levantine": "levantine", "persian": "persane", "armenian": "arménienne",
    "sri_lankan": "sri-lankaise", "ethiopian": "éthiopienne",
    "nepalese": "népalaise", "mediterranean": "méditerranéenne",
    "middle_eastern": "du Moyen-Orient", "chilean": "chilienne",
    "portuguese": "portugaise", "spanish": "espagnole",
    "international": "internationale",
}

DISH_TYPE_FR: dict[str, str] = {
    "main": "Plat", "soup": "Soupe", "side": "Accompagnement",
    "starter": "Entrée", "dessert": "Dessert", "snack": "En-cas",
    "breakfast": "Petit-déjeuner", "sauce": "Sauce",
}

# ── Helpers ────────────────────────────────────────────────────────────────────

def _ing_names(recipe: dict) -> set[str]:
    return {
        (i.get("ingredient") or "").lower()
        for i in (recipe.get("composition") or [])
        if isinstance(i, dict)
    }


def _title(recipe: dict) -> str:
    return (
        recipe.get("titles", {}).get("fr")
        or recipe.get("titles", {}).get("original")
        or f"#{recipe.get('id', '?')}"
    )


def _generate_description(recipe: dict) -> str:
    """Génère une description FR propre depuis le contexte de la recette."""
    origin    = recipe.get("origin") or {}
    cuisine   = origin.get("cuisine", "")
    dish_type = recipe.get("dish_type", "main")
    if not isinstance(dish_type, str): dish_type = "main"
    comp   = recipe.get("composition") or []
    result = recipe.get("result") or {}

    base_ings = [i for i in comp if isinstance(i, dict)
                 and (i.get("meta") or {}).get("role") in ("base", "protein")]
    if not base_ings:
        base_ings = [i for i in comp if isinstance(i, dict)]

    def fr(key: str) -> str:
        k = key.lower()
        return ING_FR.get(k, k.replace("_", " "))

    main_ings = [fr(i.get("ingredient", "")) for i in base_ings[:3]]
    ing_str   = ", ".join(main_ings) if main_ings else ""

    texture_map = {
        "cremeux": "crémeux", "croquant": "croquant", "moelleux": "moelleux",
        "fondant": "fondant", "croustillant": "croustillant", "tendre": "tendre",
    }
    taste_map = {
        "fumee": "fumé", "acidule": "acidulé", "sucre": "sucré",
        "sale": "salé", "epice": "épicé", "umami": "umami", "doux": "doux",
    }
    txt_words   = [texture_map.get(t, t.replace("_", " ")) for t in (result.get("texture") or [])[:2]]
    taste_words = [taste_map.get(t, t.replace("_", " ")) for t in (result.get("taste") or [])[:2]]
    cuis_adj = CUISINE_ADJ.get(cuisine, "")
    dt_fr    = DISH_TYPE_FR.get(dish_type, "Plat")
    cuis_str = f" {cuis_adj}" if cuis_adj else ""

    if dish_type == "soup":
        desc = f"Soupe{cuis_str} à base de {ing_str}" if ing_str else f"Soupe{cuis_str}"
        if taste_words: desc += f", aux saveurs {' et '.join(taste_words)}"
    elif dish_type == "dessert":
        desc = f"Dessert{cuis_str} à base de {ing_str}" if ing_str else f"Dessert{cuis_str}"
        if txt_words: desc += f", {' et '.join(txt_words)}"
    elif dish_type in ("snack", "breakfast", "sauce", "starter"):
        desc = f"{dt_fr}{cuis_str} à base de {ing_str}" if ing_str else f"{dt_fr}{cuis_str}"
        qual = (txt_words + taste_words)[:2]
        if qual: desc += f", {' et '.join(qual)}"
    else:
        desc = f"{dt_fr}{cuis_str} à base de {ing_str}" if ing_str else f"{dt_fr}{cuis_str}"
        qual = (txt_words + taste_words)[:2]
        if qual: desc += f", {' et '.join(qual)}"

    desc = desc.strip() + "."
    return desc[0].upper() + desc[1:]


# ── Contrôles ──────────────────────────────────────────────────────────────────

def run_checks(recipes: list[dict]) -> list[dict]:
    """Retourne la liste de tous les problèmes détectés."""
    issues: list[dict] = []

    def issue(sev: str, rid, title: str, check: str, detail: str, fix: dict | None = None):
        issues.append({
            "severity": sev, "id": rid, "title": title,
            "check": check, "detail": detail, "fix": fix,
        })

    title_counter = Counter(
        r.get("titles", {}).get("fr", "") for r in recipes
        if r.get("titles", {}).get("fr")
    )

    for r in recipes:
        rid   = r.get("id", "?")
        tf    = _title(r)
        df    = r.get("diet_flags") or {}
        tags  = (r.get("tags") or {}).get("diet") or []
        comp  = r.get("composition") or []
        ings  = _ing_names(r)
        timing = r.get("timing") or {}
        dt    = r.get("dish_type", "main") if isinstance(r.get("dish_type"), str) else "main"
        desc  = r.get("description", "") or ""

        # C1 — lactose_free faux positif
        if df.get("lactose_free"):
            dairy = ings & DAIRY_INGREDIENTS
            if dairy:
                issue("critical", rid, tf, "C1_lactose_false_positive",
                      f"lactose_free=True mais ingrédients laitiers: {dairy}",
                      fix={"diet_flags.lactose_free": False})

        # C2 — vegan faux positif dans diet_flags
        if df.get("vegan"):
            animal = ings & ANIMAL_INGREDIENTS
            if animal:
                issue("critical", rid, tf, "C2_vegan_false_positive",
                      f"diet_flags.vegan=True mais ingrédients animaux: {animal}",
                      fix={"diet_flags.vegan": False})

        # C3 — tag vegan désynchronisé
        if "vegan" in tags and not df.get("vegan"):
            issue("warning", rid, tf, "C3_vegan_tag_mismatch",
                  "tag 'vegan' présent mais diet_flags.vegan=False",
                  fix={"tags.diet.remove": "vegan"})

        # C4 — timing aberrant
        prep  = timing.get("prep_active_min") or 0
        passv = timing.get("prep_passive_min") or 0
        cook  = timing.get("cook_min") or 0
        total = timing.get("total_min") or 0
        if total > 0:
            calc = prep + passv + cook
            if abs(total - calc) > 15 and calc > 0 and passv < 60:
                # passv >= 60 = repos/levée : timing long intentionnel
                issue("warning", rid, tf, "C4_timing_incoherent",
                      f"total_min={total} ≠ prep({prep})+passive({passv})+cook({cook})={calc}")

        # C5 — description template auto-générée
        # Skip si la description contient des termes whitelistés (déjà correcte)
        if TEMPLATE_DESC_RGX.search(desc) and not DESCRIPTION_WHITELIST_PATTERNS.search(desc):
            new_desc = _generate_description(r)
            # Vérifier que la nouvelle description ne re-triggera pas C5
            if not TEMPLATE_DESC_RGX.search(new_desc) or DESCRIPTION_WHITELIST_PATTERNS.search(new_desc):
                issue("info", rid, tf, "C5_description_template",
                      f"Description template détectée: '{desc[:80]}'",
                      fix={"description": new_desc})

        # C6 — servings calibration
        srv = r.get("servings")
        expected = DEFAULT_SERVINGS.get(dt, 4)
        if srv != expected:
            issue("info", rid, tf, "C6_servings_uncalibrated",
                  f"servings={srv} mais dish_type={dt} → attendu {expected}",
                  fix={
                      "servings": expected,
                      "servings_default": expected,
                      "servings_user_override": None,
                  })

        # C7 — titre dupliqué
        title_fr = r.get("titles", {}).get("fr", "")
        if title_fr and title_counter.get(title_fr, 0) > 1:
            # Auto-fix : si c'est une recette de base (id préfixé "base_"),
            # suffixer le titre FR avec " (base)" pour le distinguer.
            is_base = str(rid).startswith("base_")
            if is_base and not title_fr.endswith(" (base)"):
                issue("warning", rid, tf, "C7_duplicate_title",
                      f"Titre '{title_fr}' apparaît {title_counter[title_fr]}x — renommage base",
                      fix={"titles.fr": title_fr + " (base)"})
            else:
                issue("warning", rid, tf, "C7_duplicate_title",
                      f"Titre '{title_fr}' apparaît {title_counter[title_fr]}x")

        # C8 — ingrédient laitier animal dans recette nommée "Vegan"
        # Auto-substitution via DAIRY_SUBSTITUTES pour les cas couverts.
        vegan_in_name = "vegan" in tf.lower()
        if vegan_in_name:
            dairy = ings & DAIRY_INGREDIENTS
            plant_dairy = ings & PLANT_DAIRY
            if dairy and not plant_dairy:
                # Construire les fixes de substitution pour chaque laitier trouvé
                fixes: dict = {}
                unresolved = []
                for d in dairy:
                    sub = DAIRY_SUBSTITUTES.get(d)
                    if sub:
                        fixes[f"composition.replace.{d}"] = sub
                    else:
                        unresolved.append(d)
                if fixes:
                    issue("warning", rid, tf, "C8_vegan_name_ingredient_conflict",
                          f"Recette nommée 'Vegan' contient des laitiers animaux: {dairy} → substitution auto",
                          fix=fixes)
                if unresolved:
                    issue("warning", rid, tf, "C8_vegan_name_ingredient_conflict",
                          f"Recette nommée 'Vegan' — laitiers sans substitut connu: {unresolved}",
                          fix=None)

    return issues


# ── Application des corrections ────────────────────────────────────────────────

def apply_fixes(recipes: list[dict], issues: list[dict]) -> tuple[int, list[dict]]:
    """
    Applique les corrections issues des contrôles.
    Retourne (nb_corrections, log_entries).
    """
    index = {r.get("id"): r for r in recipes}
    applied: list[dict] = []

    for iss in issues:
        if not iss.get("fix"):
            continue
        rid   = iss["id"]
        r     = index.get(rid)
        if not r:
            continue
        fix   = iss["fix"]
        title = iss["title"]

        for field, value in fix.items():

            # diet_flags.*
            if field.startswith("diet_flags."):
                key = field.split(".", 1)[1]
                old = (r.get("diet_flags") or {}).get(key)
                r.setdefault("diet_flags", {})[key] = value
                applied.append({"id": rid, "title": title, "field": field, "old": old, "new": value, "check": iss["check"]})

            # tags.diet.remove
            elif field == "tags.diet.remove":
                tags = (r.get("tags") or {}).get("diet") or []
                if isinstance(tags, list) and value in tags:
                    old = list(tags)
                    new = [t for t in tags if t != value]
                    r.setdefault("tags", {})["diet"] = new
                    applied.append({"id": rid, "title": title, "field": "tags.diet", "old": old, "new": new, "check": iss["check"]})

            # titles.fr (C7 renommage doublon)
            elif field == "titles.fr":
                old = (r.get("titles") or {}).get("fr")
                r.setdefault("titles", {})["fr"] = value
                applied.append({"id": rid, "title": title, "field": field, "old": str(old)[:80], "new": str(value)[:80], "check": iss["check"]})

            # description, servings, servings_default, servings_user_override
            elif field in ("description", "servings", "servings_default", "servings_user_override"):
                old = r.get(field)
                r[field] = value
                applied.append({"id": rid, "title": title, "field": field, "old": str(old)[:80], "new": str(value)[:80], "check": iss["check"]})

            # composition.replace.<ing> → substitute
            elif field.startswith("composition.replace."):
                old_ing = field.split(".", 2)[2]
                for item in (r.get("composition") or []):
                    if isinstance(item, dict) and item.get("ingredient") == old_ing:
                        item["ingredient"] = value
                        item.setdefault("meta", {})["substitution_note"] = (
                            f"{old_ing} → {value} (fix_recipes_coherence C8)"
                        )
                        applied.append({"id": rid, "title": title, "field": f"composition[{old_ing}]", "old": old_ing, "new": value, "check": iss["check"]})
                        break

        # Journaliser dans la recette
        r.setdefault("_corrections_log", []).append({
            "date": NOW,
            "script": "fix_recipes_coherence.py",
            "check": iss["check"],
            "detail": iss["detail"][:200],
        })

    return len(applied), applied


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Audit et correction de cohérence recipes.json")
    parser.add_argument("--apply",  action="store_true", help="Applique les corrections (défaut: dry-run)")
    parser.add_argument("--quiet",  action="store_true", help="Affichage réduit")
    parser.add_argument("--input",  type=Path, default=RECIPES_FILE, help="Chemin recipes.json")
    parser.add_argument("--output", type=Path, default=None, help="Chemin de sortie (défaut: même fichier)")
    args = parser.parse_args()

    src  = args.input
    dest = args.output or src

    if not src.exists():
        log.error("Fichier introuvable : %s", src)
        raise SystemExit(1)

    raw     = json.loads(src.read_text(encoding="utf-8"))
    recipes = raw.get("recipes", [])
    log.info("Recettes chargées : %d", len(recipes))

    # ── Audit ──
    issues = run_checks(recipes)

    sev_count = Counter(i["severity"] for i in issues)
    check_count = Counter(i["check"] for i in issues)

    if not args.quiet:
        print(f"\n{'='*60}")
        print(f"  AUDIT COHÉRENCE — {len(recipes)} recettes")
        print(f"{'='*60}")
        print(f"  critical : {sev_count.get('critical', 0)}")
        print(f"  warning  : {sev_count.get('warning', 0)}")
        print(f"  info     : {sev_count.get('info', 0)}")
        print(f"  total    : {len(issues)}\n")
        print("  Répartition par contrôle :")
        for check, n in sorted(check_count.items()):
            print(f"    {check:40s} {n:4d}")

    if not args.apply:
        print("\n  ▸ Mode DRY-RUN — aucune modification écrite.")
        print("    Relancer avec --apply pour appliquer les corrections.\n")
        # Afficher les critiques
        crits = [i for i in issues if i["severity"] == "critical"]
        if crits and not args.quiet:
            print("  Problèmes critiques :")
            for i in crits[:20]:
                print(f"    [{i['id']}] {i['detail'][:80]}")
        return

    # ── Application ──
    nb_applied, correction_log = apply_fixes(recipes, issues)

    # Mise à jour métadonnées
    meta = raw.get("metadata", {})
    meta["last_coherence_audit"]        = NOW
    meta["last_coherence_corrections"]  = nb_applied
    raw["metadata"] = meta

    # Écriture atomique
    fd, tmp = tempfile.mkstemp(dir=dest.parent, suffix=".tmp", prefix="recipes_fix_")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        os.replace(tmp, dest)
    except Exception:
        os.unlink(tmp)
        raise

    # Log de corrections
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    existing: list = []
    if LOG_FILE.exists():
        try:
            existing = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.extend(correction_log)
    LOG_FILE.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"  {nb_applied} corrections appliquées")
    print(f"  Fichier : {dest}")
    print(f"  Log     : {LOG_FILE}")
    print(f"{'='*60}")
    if not args.quiet:
        for c in correction_log[:25]:
            print(f"  [{c['id'][:30]:30s}] {c['field']:35s} {str(c.get('old',''))[:30]} → {str(c.get('new',''))[:30]}")
        if len(correction_log) > 25:
            print(f"  ... et {len(correction_log) - 25} autres")


if __name__ == "__main__":
    main()
