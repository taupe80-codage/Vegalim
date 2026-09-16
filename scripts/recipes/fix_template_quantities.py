#!/usr/bin/env python3
"""
fix_template_quantities.py — corrige les quantités « gabarit » repérées par la
relecture 2026-09-15 : presque toutes les recettes générées portent 300 g
d'oignon et 480 g de tomates fraîches pour 4 portions, quel que soit le plat
(1 kg de légumes par recette, soit 250 g d'oignon-tomate par personne).

Règles (uniquement sur ces valeurs exactes, donc idempotent) :
  - oignon (onion_raw, yellow_onion_raw, white_onion_raw) en rôle aromatic_base
    à 300 g  → 150 g ;
  - tomato_raw_ripe à 480 g → 300 g ;
  - le texte des étapes est resynchronisé (300 g / 300g / 300 grammes dans une
    phrase qui parle d'oignon, 480 g / 480g / 480 grammes pour la tomate).

EXCLUSIONS : plats où l'oignon est l'ingrédient principal (pakora, kadhi,
koshari, mujadara, misir wot, soupes à l'oignon…).

Usage :
    python scripts/recipes/fix_template_quantities.py --dry-run
    python scripts/recipes/fix_template_quantities.py
"""
import argparse, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.engine.config import RECIPES_PATH

OIGNONS = ("onion_raw", "yellow_onion_raw", "white_onion_raw")

# l'oignon y est le légume principal (beignets, riz aux oignons frits, soupes)
SANS_OIGNON = {
    "dal_pakora_b418ab", "dal_kadhi_pakora_078de2", "dal_kadhi_pakora_vegan_5cb5d4",
    "dal_koshari_15670d", "dal_koshari_egyptien_73828c", "dal_mujadara_2f5904",
    "dal_ethiopian_misir_wot_4203c8", "egg_sopa_paraguaya_43987c",
}


def _sync(steps: list[str], mot: str, avant: int, apres: int) -> None:
    """Remplace la quantité seulement si le mot (oignon / tomate) est à proximité."""
    motif = re.compile(rf"\b{avant}\s?g(?:rammes)?\b")
    for i, s in enumerate(steps):
        if mot not in s.lower():
            continue
        out, pos = [], 0
        for m in motif.finditer(s):
            apres_txt = re.split(r',| et |\.|;', s[m.end():m.end() + 40])[0].lower()
            avant_txt = re.split(r',| et |\.|;', s[max(0, m.start() - 30):m.start()])[-1].lower()
            out.append(s[pos:m.start()])
            trouve = mot in apres_txt or mot in avant_txt
            out.append(m.group(0).replace(str(avant), str(apres)) if trouve else m.group(0))
            pos = m.end()
        steps[i] = "".join(out) + s[pos:]


def corriger(r: dict) -> list[str]:
    log = []
    steps = r.get("instructions") or []
    if r.get("servings") != 4:
        return log
    for c in r.get("composition") or []:
        meta = c.get("meta") or {}
        iid, q = c.get("ingredient"), c.get("quantity")
        if (iid in OIGNONS and q == 300 and meta.get("role") == "aromatic_base"
                and r["id"] not in SANS_OIGNON and "oignon" not in r["titles"].get("fr", "").lower()):
            c["quantity"] = 150
            _sync(steps, "oignon", 300, 150)
            log.append(f"{r['id']} : {iid} 300 → 150 g")
        if iid == "tomato_raw_ripe" and q == 480:
            c["quantity"] = 300
            _sync(steps, "tomate", 480, 300)
            log.append(f"{r['id']} : tomate 480 → 300 g")
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    raw = json.loads(Path(RECIPES_PATH).read_text(encoding="utf-8"))
    log = [ligne for r in raw["recipes"] for ligne in corriger(r)]
    for ligne in log:
        print(ligne)
    print(f"\n{len(log)} quantités corrigées")
    if args.dry_run or not log:
        return
    tmp = Path(RECIPES_PATH).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(RECIPES_PATH)
    print(f"écrit : {RECIPES_PATH}")


if __name__ == "__main__":
    main()
