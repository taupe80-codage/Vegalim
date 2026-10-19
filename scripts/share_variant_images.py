"""
Vegalim — Photo partagée entre variantes d'un même plat
=======================================================

« Curry d'aubergine sri lankais — version express » et « … — épices fraîches »
sont le même plat dans l'assiette : la variante change la méthode, pas la tête
du plat. Une recette sans photo peut donc reprendre celle d'une recette
voisine déjà illustrée.

L'appariement se fait sur le NOM DE BASE : le titre avant la virgule ou le
tiret, débarrassé des qualificatifs de variante (express, maison, rapide,
traditionnel, vegan…). Deux recettes se correspondent quand leurs noms de base
partagent les mêmes mots distinctifs, ou que l'un contient l'autre en
commençant par le même mot.

Usage :
    python scripts/share_variant_images.py            # propose, n'écrit rien
    python scripts/share_variant_images.py --apply    # copie les photos
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
RECIPES = ROOT / "backend" / "data" / "recipes" / "recipes.json"
IMG = ROOT / "frontend" / "public" / "images" / "recipes"
CREDITS = IMG / "_credits.json"

# Mots qui décrivent une variante ou une manière de faire, pas le plat.
VARIANTE = {
    "express", "rapide", "quick", "maison", "homemade", "version", "facon",
    "traditionnel", "traditionnelle", "traditional", "classique", "classic",
    "simple", "simplifie", "simplifiee", "facile", "easy", "ultra", "optimise",
    "optimisee", "maitrise", "maitrisee", "structure", "structuree", "base",
    "preparation", "nature", "minute", "complet", "complete", "legere", "leger",
    "revisite", "revisitee", "ameliore", "amelioree", "fete", "jour", "soir",
    "express", "nouvelle", "nouveau", "grand", "petit", "mere", "chef",
}

# Mots vides, ignorés pour comparer deux noms de plats.
STOP = {
    "de", "du", "des", "la", "le", "les", "au", "aux", "a", "et", "en", "un",
    "une", "sans", "avec", "pour", "sur", "dans", "par", "ses", "leur", "the",
    "of", "with", "and", "for", "in", "on", "to",
}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip().replace(chr(92), "-")
    text = re.sub(r"[\s_/]+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    return re.sub(r"-+", "-", text).strip("-")


def base_words(title: str) -> list[str]:
    """Mots distinctifs du nom du plat, qualificatifs de variante retirés."""
    tete = re.split(r"[,—–(]|\s-\s", title or "")[0]
    tete = unicodedata.normalize("NFD", tete)
    tete = "".join(c for c in tete if unicodedata.category(c) != "Mn").lower()
    mots = [w for w in re.split(r"[^a-z0-9]+", tete) if w]
    return [w for w in mots if w not in STOP and w not in VARIANTE and len(w) > 2]


def apparie(sans: list[str], avec: list[str]) -> bool:
    """Deux noms de base désignent-ils le même plat ?"""
    if not sans or not avec:
        return False
    a, b = set(sans), set(avec)
    if a == b:
        return True
    court, long_ = (sans, avec) if len(sans) <= len(avec) else (avec, sans)
    # l'un contient l'autre, et les deux commencent par le même mot :
    # « gnocchi pesto » et « gnocchi pesto roquette noix » sont le même plat
    return len(court) >= 2 and set(court) <= set(long_) and sans[0] == avec[0]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="copier réellement les photos")
    args = ap.parse_args()

    data = json.loads(RECIPES.read_text(encoding="utf-8"))
    recipes = data["recipes"] if isinstance(data, dict) else data

    avec, sans = [], []
    for r in recipes:
        t = r.get("titles", {})
        nom = t.get("fr") or t.get("en") or ""
        if not nom:
            continue
        fiche = {"slug": slugify(nom), "nom": nom, "base": base_words(nom)}
        (avec if (IMG / f"{fiche['slug']}.jpg").exists() else sans).append(fiche)

    print(f"{len(avec)} recettes illustrées, {len(sans)} sans photo\n")

    credits = json.loads(CREDITS.read_text(encoding="utf-8")) if CREDITS.exists() else {}
    paires, ambigus = [], []
    for s in sans:
        candidats = [a for a in avec if apparie(s["base"], a["base"])]
        if not candidats:
            continue
        # le plus proche : celui dont le nom de base compte le moins de mots
        # en trop, donc le plus générique du plat
        candidats.sort(key=lambda a: (len(set(a["base"]) ^ set(s["base"])), a["slug"]))
        if len(candidats) > 1 and len(set(c["base"][0] for c in candidats)) > 1:
            ambigus.append((s, candidats))
            continue
        paires.append((s, candidats[0]))

    print(f"{len(paires)} variantes rattachables, {len(ambigus)} ambiguës\n")
    for s, a in paires:
        src = credits.get(a["slug"], {})
        print(f"  {s['nom'][:52]:<52} ← {a['nom'][:46]}")
        if args.apply:
            shutil.copyfile(IMG / f"{a['slug']}.jpg", IMG / f"{s['slug']}.jpg")
            if src:
                credits[s["slug"]] = {**src, "recipe": s["nom"],
                                      "partagee_avec": a["slug"]}

    if ambigus:
        print("\nAmbiguës, laissées de côté :")
        for s, cs in ambigus:
            print(f"  {s['nom'][:52]:<52} ? {', '.join(c['slug'][:28] for c in cs[:3])}")

    if args.apply:
        CREDITS.write_text(json.dumps(credits, ensure_ascii=False, indent=1, sort_keys=True),
                           encoding="utf-8")
        print(f"\n{len(paires)} photos copiées, crédits mis à jour.")
    else:
        print("\nSimulation — relancer avec --apply pour copier.")


if __name__ == "__main__":
    main()
