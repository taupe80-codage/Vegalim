"""
Vegalim — Une photo par plat, partagée entre ses variantes
==========================================================

« Curry d'aubergine sri lankais — version express » et « … — épices fraîches »
sont le même plat dans l'assiette. Chercher leur titre complet ne donne rien,
parce qu'aucune photo au monde n'illustre une version express. Chercher le
NOM DU PLAT, lui, marche.

Ce script regroupe donc les recettes sans photo par nom de plat, cherche une
photo pour ce nom, et la donne à toutes les recettes du groupe.

Il réutilise les filtres de fetch_recipe_images_free.py : viande et poisson,
sujets hors propos, liste noire des photos déjà écartées à la relecture.

Usage :
    python scripts/fetch_images_by_dish.py              # simulation
    python scripts/fetch_images_by_dish.py --apply
    python scripts/fetch_images_by_dish.py --apply --workers 3
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "frontend" / "public" / "images" / "recipes"

_spec = importlib.util.spec_from_file_location(
    "fetch_free", Path(__file__).parent / "fetch_recipe_images_free.py")
F = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(F)

_spec2 = importlib.util.spec_from_file_location(
    "share_variants", Path(__file__).parent / "share_variant_images.py")
V = importlib.util.module_from_spec(_spec2)
_spec2.loader.exec_module(V)

import requests  # noqa: E402  (après le chargement des modules frères)


def nom_de_plat(item: dict) -> str:
    """Nom du plat seul : ni qualificatif de variante, ni garniture, ni
    adjectif de pays. « Auvergne aligot » ne trouvait rien, « aligot » oui."""
    for cle in ("en", "original", "fr"):
        mots = [w for w in V.base_words(item.get(cle) or "")
                if w not in F.GENERIC and w not in F.PLAIN_INGREDIENTS]
        if mots:
            return " ".join(mots[:3])
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--max-groupe", type=int, default=0,
                    help="ne traiter que les N premiers groupes (essai)")
    args = ap.parse_args()

    items = F.load_recipes()
    sans = [i for i in items if not (IMG / f"{i['slug']}.jpg").exists()]

    groupes: dict[str, list[dict]] = {}
    trop_vague = 0
    for i in sans:
        plat = nom_de_plat(i)
        if not plat:
            continue
        # « salad » tout court rattacherait trois salades differentes a la
        # meme cesar : il faut au moins un mot propre au plat
        if all(w in F.FOOD_MARKERS for w in plat.split()):
            trop_vague += 1
            continue
        groupes.setdefault(plat, []).append(i)

    ordre = sorted(groupes.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    if args.max_groupe:
        ordre = ordre[:args.max_groupe]

    print(f"{len(sans)} recettes sans photo, {len(groupes)} plats distincts")
    print(f"dont {sum(1 for _, v in groupes.items() if len(v) > 1)} plats à plusieurs variantes\n")

    credits = F.load_credits()
    blocked = F.load_blocklist()
    # une photo déjà portée par une autre recette ne doit pas resservir, sauf
    # entre variantes d'un même plat — ce que fait ce script, après coup
    blocked |= {" ".join(F.words(c["title"])) for c in credits.values() if c.get("title")}

    lock = threading.Lock()
    local = threading.local()
    trouves, rates = [], []

    def session() -> requests.Session:
        if not hasattr(local, "s"):
            local.s = requests.Session()
            local.s.headers["User-Agent"] = F.UA
        return local.s

    def requetes(plat: str) -> list[str]:
        """Le nom entier, puis le meme sans son premier mot.

        En anglais comme en francais, l'adjectif de lieu ouvre le nom :
        « Auvergne aligot », « Bernese butter rosti ». Le retirer trouve
        l'article. On s'arrete la : chercher mot a mot ramenait une cesar
        pour « achichuk salad » et des frites pour « baked polenta fries ».
        """
        mots = plat.split()
        out = [plat]
        reste = mots[1:]
        if reste and not all(w in F.FOOD_MARKERS for w in reste):
            out.append(" ".join(reste))
        return out

    def accepte(c: dict, q: str) -> bool:
        """Un repli d'un seul mot doit tomber sur l'article qui porte
        exactement ce nom : « aligot » oui, « sichuan » non, qui menerait au
        poivre de Sichuan et pas au plat."""
        if len(q.split()) > 1:
            return True
        return V.slugify(c.get("article", "")) == V.slugify(q)

    def traite(entree) -> None:
        plat, membres = entree
        cand = None
        for q in requetes(plat):
            # appel direct : pick() ajoute ses propres requetes de repli, et
            # « braised vegetables » devenait « vegetables », qui ramenait une
            # photo de chou.
            for c in F.search_wikipedia(session(), q):
                if " ".join(F.words(c["title"])) in blocked:
                    continue
                if F.rejected_for(f"{c['title']} {c['categories']}"):
                    continue
                if not accepte(c, q):
                    continue
                c["query"] = q
                cand = c
                break
            if cand:
                break
        with lock:
            if not cand:
                rates.append((plat, membres))
                print(f"  — {plat[:46]:<46} aucune photo sûre")
                return
            blocked.add(" ".join(F.words(cand["title"])))
            trouves.append((plat, membres, cand))
            noms = ", ".join(m["slug"][:26] for m in membres)
            print(f"  ✓ {plat[:46]:<46} {cand['title'][:36]}  → {len(membres)} recette(s)")
            print(f"      {noms}")

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        list(pool.map(traite, ordre))

    print(f"\n{len(trouves)} plats trouvés, {len(rates)} sans photo sûre")
    print(f"soit {sum(len(m) for _, m, _ in trouves)} recettes illustrables")

    if not args.apply:
        print("\nSimulation — relancer avec --apply pour télécharger.")
        return

    ok = 0
    s = requests.Session()
    s.headers["User-Agent"] = F.UA
    for plat, membres, cand in trouves:
        premier = IMG / f"{membres[0]['slug']}.jpg"
        if not F.download(s, cand["download"], premier):
            print(f"  échec du téléchargement : {plat}")
            continue
        for m in membres:
            cible = IMG / f"{m['slug']}.jpg"
            if cible != premier:
                shutil.copyfile(premier, cible)
            credits[m["slug"]] = {
                "recipe": m["fr"], "source": cand["source"], "title": cand["title"],
                "author": cand["author"], "license": cand["license"],
                "page": cand["page"], "query": cand["query"], "plat": plat,
            }
            ok += 1
        F.save_credits(credits)
    print(f"\n{ok} recettes illustrées.")


if __name__ == "__main__":
    main()
