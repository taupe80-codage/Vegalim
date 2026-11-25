"""
scripts/remove_wrong_photos_2026_11_26.py — Retire les photos de recette fausses
repérées à la relecture des 929 photos (planches de build_image_contact_sheets.py).

Motifs : viande ou poisson visibles sur une recette végétarienne, autre plat que
la recette, personne au premier plan, sujet hors cuisine. Le fichier .jpg est
supprimé, le crédit retiré (_credits.json et CREDITS.md) et le titre Commons
ajouté à _blocklist.json pour qu'une recherche future ne le reprenne pas.
La fiche affiche alors l'illustration par défaut (RecipeCard, onError).

Usage : python scripts/remove_wrong_photos_2026_11_26.py [--dry-run]
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "frontend" / "public" / "images" / "recipes"
BLOCKLIST = IMG / "_blocklist.json"

VIANDE = "viande ou poisson visible"
AUTRE = "autre plat que la recette"
PERSONNE = "personne au premier plan"
HORS = "hors sujet"

WRONG: dict[str, str] = {
    "adas-polo-riz-persan-aux-lentilles-et-aux-dattes": VIANDE,
    "arepas-colombiennes-au-fromage-frais-et-au-beurre": HORS,
    "arepas-reina-pepiada-avocat-et-pois-chiches-vegan": VIANDE,
    "arepas-vegan": AUTRE,
    "ash-reshteh-de-teheran-au-kashk-et-a-la-menthe-frite": AUTRE,
    "baghali-polo-aux-feves-et-a-laneth-vegan": AUTRE,
    "baked-beans-a-la-melasse": PERSONNE,
    "beignets-de-legumes-indonesiens": AUTRE,
    "beurre-de-cacahuete": AUTRE,
    "bibimbap-tofu": VIANDE,
    "bibimbap-vegetarien": VIANDE,
    "cachapa-au-fromage-frais": VIANDE,
    "celeri-remoulade": VIANDE,
    "crepe-de-sarrasin": AUTRE,
    "curry-japonais-au-potiron-et-aux-shiitakes": AUTRE,
    "donburi-tofu-teriyaki": VIANDE,
    "epinards-a-la-creme-vegan": AUTRE,
    "fasolakia-grecques-aux-pommes-de-terre-et-a-la-feta": AUTRE,
    "feijoada": VIANDE,
    "flageolets-a-la-bretonne": AUTRE,
    "galette-de-sarrasin-aux-champignons-a-lail-et-au-thym-vegan": AUTRE,
    "galettes-de-pommes-de-terre-suedoises": AUTRE,
    "gaspacho-de-melon-a-la-menthe": AUTRE,
    "gateau-au-yaourt-citron": AUTRE,
    "gnocchi-au-pesto-de-roquette-et-noix-vegan": VIANDE,
    "gratin-de-navets": AUTRE,
    "halloumi-grille-au-citron-et-a-la-menthe": AUTRE,
    "harira-marocaine-traditionnelle-a-la-tadouira": VIANDE,
    "hiyashi-chuka-nouilles-froides-japonaises": VIANDE,
    "hoppin-john-riz-et-doliques-du-sud": VIANDE,
    "ile-flottante": AUTRE,
    "involtini-daubergines-a-la-sicilienne-vegan": VIANDE,
    "japchae-nouilles-de-patate-douce-sautees": VIANDE,
    "kheer-au-riz": AUTRE,
    "kibbeh": VIANDE,
    "kimchi-bokkeumbap-gratine-au-fromage": AUTRE,
    "manakish-zaatar": PERSONNE,
    "maqluba-de-legumes-riz-renverse-aux-aubergines-et-chou-fleur": VIANDE,
    "masoor-dal-bengali-au-panch-phoron": VIANDE,
    "mayonnaise": VIANDE,
    "menemen": VIANDE,
    "mercimek-koftesi-boulettes-de-lentilles-au-boulgour": AUTRE,
    "mirza-ghasemi": AUTRE,
    "moqueca": VIANDE,
    "moussaka-vegetarienne-grecque-bechamel-au-lait": VIANDE,
    "mujadara-libanaise-traditionnelle": VIANDE,
    "nasi-lemak-vegetarien": VIANDE,
    "pain-au-fromage-bresilien": AUTRE,
    "pain-depices": AUTRE,
    "papaya-salad": AUTRE,
    "parmigiana-legere-daubergines-et-courgettes-grillees": AUTRE,
    "pasta-al-forno-aux-legumes-rotis-et-mozzarella-vegetale-vegan": HORS,
    "pate-de-laksa": VIANDE,
    "pates-nature": AUTRE,
    "pho": VIANDE,
    "pierogi-aux-pommes-de-terre-et-a-laneth-vegan": VIANDE,
    "pierogi-de-lublin-au-sarrasin-et-pommes-de-terre": VIANDE,
    "pierogi-du-reveillon-choucroute-et-champignons-vegan": VIANDE,
    "plantain-frit-nature": AUTRE,
    "provoleta-grillee-a-lorigan": AUTRE,
    "riz-blanc": HORS,
    "roti-canai-pain-feuillete-malaisien": PERSONNE,
    "salade-de-pousses-de-soja-coreenne": VIANDE,
    "salade-mache-aux-noix": VIANDE,
    "sancocho": VIANDE,
    "sarmale-de-post-choux-farcis-au-riz": AUTRE,
    "shakshuka-tunisienne-aux-poivrons-et-a-la-feta": PERSONNE,
    "smoothie-vert-epinards-banane": HORS,
    "sopa-paraguaya": AUTRE,
    "sri-lankan-pumpkin-curry": VIANDE,
    "taamiya-egyptienne-aux-feves": HORS,
    "tacos": VIANDE,
    "tajine-de-legumes-au-citron-confit-et-aux-amandes": VIANDE,
    "tamagoyaki-omelette-roulee-japonaise": AUTRE,
    "tatin-de-poires-a-la-cardamome-pate-feuilletee-vegan": AUTRE,
    "tempura-de-legumes": VIANDE,
    "terrine-de-legumes-printaniers-en-gelee-au-basilic": HORS,
    "tian-provencal-gratine-au-chevre": AUTRE,
    "tostadas-aux-haricots-noirs-avocat-et-creme": VIANDE,
    "uzbek-vegetable-plov": VIANDE,
    "welsh-rarebit-toast-gallois-au-cheddar-fondu": VIANDE,
    "yaki-udon-aux-legumes-et-au-tofu-fume": VIANDE,
}


def _fetch_module():
    spec = importlib.util.spec_from_file_location(
        "fetch_recipe_images_free", ROOT / "scripts" / "fetch_recipe_images_free.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    F = _fetch_module()
    credits = F.load_credits()
    blocklist = json.loads(BLOCKLIST.read_text(encoding="utf-8")) if BLOCKLIST.exists() else []
    known = set(blocklist)

    missing = [s for s in WRONG if not (IMG / f"{s}.jpg").exists()]
    if missing:
        raise SystemExit("Photos introuvables : " + ", ".join(missing))

    removed = blocked = 0
    for slug, reason in sorted(WRONG.items()):
        title = (credits.get(slug) or {}).get("title")
        print(f"{slug} — {reason}" + (f" — bloque « {title} »" if title else ""))
        if args.dry_run:
            continue
        (IMG / f"{slug}.jpg").unlink()
        removed += 1
        credits.pop(slug, None)
        if title and title not in known:
            blocklist.append(title)
            known.add(title)
            blocked += 1

    if args.dry_run:
        print(f"\n{len(WRONG)} photos à retirer (rien n'est modifié).")
        return
    F.save_credits(credits)
    BLOCKLIST.write_text(json.dumps(sorted(blocklist), ensure_ascii=False, indent=1),
                         encoding="utf-8")
    # write_text met des CRLF sous Windows : on garde les fins de ligne LF du dépôt.
    for f in (IMG / "_credits.json", IMG / "CREDITS.md", BLOCKLIST):
        f.write_bytes(f.read_bytes().replace(b"\r\n", b"\n"))
    print(f"\n{removed} photos retirées, {blocked} titres ajoutés à la liste noire.")


if __name__ == "__main__":
    main()
