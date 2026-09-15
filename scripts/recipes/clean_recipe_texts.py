#!/usr/bin/env python3
"""
clean_recipe_texts.py — nettoie les instructions générées (relecture 2026-09-15,
docs/revue_recettes_2026-09-15) :

  1. Phrases de remplissage : « Déguster et apprécier… », « Expérimentez avec… »,
     « Bon appétit ! », « … pour une expérience culinaire complète », « car la
     chaleur et le croustillant sont essentiels… ». Étape vide → supprimée,
     « Étape N » renumérotées.
  2. « La lame ressort sèche » hors pâtisserie/four : test absurde pour une
     soupe, une purée ou un sauté.
  3. Températures en °C sur le feu (« mijoter à 180 °C », « service à 70 °C »).
  4. « Bols / assiettes préchauffés » pour les plats servis froids.

Les phrases contenant une quantité (chiffre suivi d'une unité) ne sont jamais
supprimées entières : seules les incises sont retirées.

Idempotent. Relancer ensuite scripts/build_index.py.

Usage :
    python scripts/recipes/clean_recipe_texts.py --dry-run [--show N]
    python scripts/recipes/clean_recipe_texts.py
"""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.engine.config import RECIPES_PATH

ETAPE = re.compile(r"^\s*([ÉE]tape\s*)(\d+)(\s*:\s*)", re.I)
QUANTITE = re.compile(r"\d+(?:[.,]\d+)?\s*(?:g|kg|ml|cl|l|cm|mm|°C|minutes?|min|heures?|h)\b", re.I)

# ── 1. Remplissage ────────────────────────────────────────────────────────────
PHRASE_REMPLISSAGE = re.compile(
    r"^(?:d[ée]guste[rz]?|appr[ée]cie[rz]?|profite[rz]?|exp[ée]rimente[rz]?|savoure[rz]?|partage[rz]?|"
    r"bon app[ée]tit|n'oubliez pas|enfin, prenez un moment|pour une exp[ée]rience culinaire|"
    r"servir et partager|servez et partagez)\b"
    r"|doit [êe]tre d[ée]gust[ée]e? avec plaisir|pr[ée]sent[ée]e? de mani[èe]re app[ée]tissante\.?$",
    re.I)
# « Déguster et ajuster l'assaisonnement » est une vraie consigne
AJUSTER = re.compile(r"ajust|rectifi|assaisonn|goût", re.I)
INCISES_REMPLISSAGE = [
    r"(?:,|\s+et)?\s*(?:tout )?en (?:appr[ée]ciant|savourant|profitant de l'exp[ée]rience|sentant la satisfaction|"
    r"partageant (?:avec|ce plat)|se r[ée]jouissant|vous r[ée]jouissant)[^.!?]*",
    r",?\s*car la chaleur(?: et le croustillant)? (?:est|sont) essentiel(?:le)?s?[^.!?]*",
    r",?\s*pour (?:une|profiter de cette) exp[ée]rience (?:culinaire|gastronomique)(?: [a-zéèêàûôî]+)*",
    r",?\s*et d[ée]guste[rz]?(?:-le|-la|-les)? avec plaisir",
    r",?\s*et profite[rz]? de cette exp[ée]rience[^.!?]*",
]

# ── 2. Lame sèche ─────────────────────────────────────────────────────────────
CONTEXTE_FOUR = re.compile(r"enfourn|au four|\bfour\b|g[âa]teau|cake|\bpain\b|tourte|quiche|tarte|"
                           r"cookies?|muffins?|brownie|cheesecake|clafoutis|flan|far\b|madeleine|"
                           r"financier|moelleux|fondant|biscuit|gratin|bannock|galette|crumble|"
                           r"pain d'[ée]pices|g[ée]noise|b[ée]chamel au four", re.I)
LAME = re.compile(r"lame[^.;!?]{0,80}?s[èe]che|s[èe]che[^.;!?]{0,20}la lame", re.I)
SUBST_LAME = [
    # « Vérifier que la lame ressort sèche et que X » → « Vérifier que X »
    (r"(v[ée]rifi\w+\s+que\s+)la lame(?: d'une? \w+)? ressort(?:e|ir)? s[èe]che(?: [^,.;]{0,60}?)?\s+et\s+(?:que\s+)?", r"\1"),
    # incises
    (r",?\s*(?:en\s+)?v[ée]rifiant que la lame(?: d'une? \w+)?(?: \w+){0,3} ressort(?:e|ir)? s[èe]che[^,.;!?]*", ""),
    (r",?\s*(?:et\s+)?jusqu'à ce que\s+la lame(?: d'une? \w+)?(?: \w+){0,3} (?:ressorte|ressort) s[èe]che[^,.;!?]*", ""),
    (r",?\s*(?:et\s+)?(?:que\s+)?la lame(?: d'une? \w+)?(?: \w+){0,3} (?:doit )?ressort(?:e|ir)? s[èe]che[^,.;!?]*", ""),
]

# ── 3. Températures sur le feu ────────────────────────────────────────────────
FEU = re.compile(r"mijot|feu (?:tr[èe]s )?(?:doux|moyen|vif)|po[êe]le|casserole|wok|cocotte|sauteuse|"
                 r"frémiss|servir|service", re.I)
# « cuire / réduire à 180 °C » : sur le feu seulement si la recette n'a pas de four
FEU_SANS_FOUR = re.compile(r"r[ée]dui|cuire|cuisez", re.I)
FOUR_RECETTE = re.compile(r"four|enfourn", re.I)
PAS_FEU = re.compile(r"four|enfourn|gril|friteuse|friture|frire|frit|huile (?:de friture|à)|thermom|"
                     r"gaufrier|crêpière|vapeur|bain-marie|ferment|lever|tiédir|eau|lait|crème|sirop|"
                     r"chocolat|caramel|beurre|ambiante|inférieure|refroid|profond|remonte|grésille", re.I)
TEMP = re.compile(r",?\s*(?:\(|à |a )?(?:environ |une température de |température d'environ )?"
                  r"\d{2,3}(?:\s*(?:-|à)\s*\d{2,3})?\s*°\s*C\)?", re.I)

# ── 4. Bols préchauffés pour un plat froid ───────────────────────────────────
PRECHAUFFE = re.compile(r",?\s*(?:dans|sur) (?:des|un|une) (?:petits? |grands? )?(?:bols?|assiettes?|plats?)"
                        r"(?: de service)? (?:préchauff|chaud)\w*", re.I)
SERVI_FROID = re.compile(r"servir (?:bien |très )?(?:froid|frais)|température ambiante|réfrigér", re.I)


def _propre(s: str) -> str:
    s = re.sub(r"\s+,", ",", s)
    s = re.sub(r",\s*,", ",", s)
    s = re.sub(r",\s*([.!?])", r"\1", s)
    s = re.sub(r"\s+(?:et|ou|jusqu'à ce)\s*([.!?])$", r"\1", s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    s = re.sub(r"^[,;:\s]+", "", s)
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    if s and s[-1] not in ".!?":
        s += "."
    return s


def _phrases(corps: str) -> list[str]:
    return [p for p in re.split(r"(?<=[.!?])\s+", corps.strip()) if p]


def nettoyer_etape(corps: str, recette_froide: bool, contexte_four: bool, four_recette: bool = False) -> str:
    sorties = []
    for p in _phrases(corps):
        orig = p
        if PHRASE_REMPLISSAGE.search(p) and not QUANTITE.search(p) and not AJUSTER.search(p):
            continue
        for pat in INCISES_REMPLISSAGE:
            p = re.sub(pat, "", p, flags=re.I)
        if LAME.search(p) and not contexte_four:
            for pat, rep in SUBST_LAME:
                p = re.sub(pat, rep, p, flags=re.I)
            # « Vérifier, que les graines… » → « Vérifier que les graines… »
            p = re.sub(r"^(v[ée]rifi\w+)\s*,\s*(que\b)", r"\1 \2", p, flags=re.I)
            # « Vérifier, et la diluer… » / « Vérifier, indiquant que… »
            if re.match(r"^v[ée]rifi\w+\s*(?:,|et\b|$|[.!?])", p, re.I):
                p = re.sub(r"^v[ée]rifi\w+\s*,?\s*(?:et\s+)?", "", p, flags=re.I)
            if not p.strip(" .!?") or re.match(r"^(?:indiquant|ce qui indique|signe)", p, re.I) \
                    or (LAME.search(p) and not QUANTITE.search(p)):
                continue  # phrase entièrement consacrée au test
        for m in list(TEMP.finditer(p))[::-1]:
            avant = p[max(0, m.start() - 70):m.start()]
            apres = p[m.end():m.end() + 80]
            deg = int(re.search(r"\d{2,3}", m.group(0)).group(0))
            feu = FEU.search(avant) or (not four_recette and FEU_SANS_FOUR.search(avant))
            if feu and not PAS_FEU.search(avant + apres) and (deg >= 100 or re.search(r"servi", avant, re.I)):
                p = p[:m.start()] + p[m.end():]
        if recette_froide:
            p = PRECHAUFFE.sub("", p)
        p = _propre(p) if p != orig else p
        if re.fullmatch(r"[\W_]*", p):
            continue
        sorties.append(p)
    return " ".join(sorties)


def nettoyer(recette: dict) -> list[str]:
    t = recette.get("timing") or {}
    texte = " ".join(recette.get("instructions") or [])
    froide = (not t.get("cook_min")) or bool(SERVI_FROID.search(texte)) or \
        str(recette.get("id", "")).startswith("salad_")
    etapes = []
    for s in recette.get("instructions") or []:
        m = ETAPE.match(s)
        corps = s[m.end():] if m else s
        contexte_four = bool(CONTEXTE_FOUR.search(corps)) or \
            (recette.get("dish_type") in ("dessert", "bread", "pastry") and bool(CONTEXTE_FOUR.search(texte)))
        four = bool(FOUR_RECETTE.search(texte)) or recette.get("dish_type") in ("dessert", "bread", "pastry")
        neuf = nettoyer_etape(corps, froide, contexte_four, four)
        if neuf:
            etapes.append((m, neuf))
    if len(etapes) < 2:  # garde-fou : ne jamais vider une recette
        return recette.get("instructions") or []
    out, n = [], 0
    for m, corps in etapes:
        n += 1
        out.append(f"{m.group(1)}{n}{m.group(3)}{corps}" if m else corps)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--show", type=int, default=0, help="afficher N recettes modifiées (avant/après)")
    args = ap.parse_args()
    raw = json.loads(Path(RECIPES_PATH).read_text(encoding="utf-8"))
    changed, etapes_suppr, montrees = 0, 0, 0
    for r in raw["recipes"]:
        avant = r.get("instructions") or []
        apres = nettoyer(r)
        if apres != avant:
            changed += 1
            etapes_suppr += len(avant) - len(apres)
            if montrees < args.show:
                montrees += 1
                print(f"\n=== {r['id']}")
                for a in avant:
                    if a not in apres:
                        print("  - ", a)
                for b in apres:
                    if b not in avant:
                        print("  + ", b)
            r["instructions"] = apres
    print(f"\n{changed} recettes modifiées, {etapes_suppr} étapes supprimées")
    if args.dry_run or not changed:
        return
    tmp = Path(RECIPES_PATH).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(RECIPES_PATH)
    print(f"écrit : {RECIPES_PATH}")


if __name__ == "__main__":
    main()
