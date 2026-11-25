#!/usr/bin/env python3
"""fix_main_dish_types_2026_11_25.py — « plats principaux » qui n'en sont pas.

21 recettes classées `main` apportent moins de 6 g de protéines et 300 kcal par
portion : ce sont des accompagnements, des soupes ou des entrées dans leur
cuisine d'origine. Classées en plat, le planning (hors budget) pouvait les
servir comme repas complet, et les pages « plats » les mêlaient aux vrais plats.
Arbitrage validé le 2026-11-25 (l'arbitrage de 2026-09-26 gardait les 120 plats
sous 10 g de protéines : seuls les plus maigres, qui ne font pas un repas, sont
reclassés ici).

Restent des plats : le curry japonais au potiron (servi avec du riz, plat unique)
et le pancit (nouilles sautées, plat unique aux Philippines).

Idempotent. Relancer ensuite rebuild_graphs.py et build_index.py.

Usage :
    python scripts/recipes/fix_main_dish_types_2026_11_25.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from backend.engine.config import RECIPES_PATH  # noqa: E402

# id : (nouveau dish_type, raison)
RECLASS: dict[str, tuple[str, str]] = {
    # Accompagnements : se servent avec un dal, du riz, une protéine
    "curry_aubergine_sri_lanka_bf8bcd": ("side", "wambatu curry, un des currys du « rice and curry »"),
    "curry_dry_aloo_gobi_9a6763": ("side", "sabzi sec, servi avec dal et roti"),
    "main_aloo_gobi_b21c85": ("side", "sabzi, servi avec dal et roti"),
    "main_aloo_palak_7e9377": ("side", "sabzi, servi avec dal et roti"),
    "main_nepali_aloo_tama_4664a3": ("side", "accompagne le dal bhat"),
    "main_mexican_calabacitas_f3511d": ("side", "guarnición de courgettes"),
    "main_poelee_scandinave_de_legu_31947f": ("side", "poêlée de légumes"),
    "main_choucroute_vegetarienne_25c7a3": ("side", "choucroute sans garniture"),
    "main_daube_de_legumes_4a045f": ("side", "légumes mijotés"),
    "rice_bigos_497b21": ("side", "chou mijoté, sans la viande qui en fait un plat"),
    "stew_ragout_de_plantain_2140eb": ("side", "plantain mijoté"),
    "stew_ratatouille_k8d2p4": ("side", "accompagnement provençal classique"),
    "rice_white_k1d1p1": ("side", "riz nature"),
    "pasta_plain_k2d1p1": ("side", "pâtes nature"),
    "wok_pommes_de_terre_sautees_8bafe1": ("side", "garniture"),
    "salad_de_pommes_de_terre_allema_3cdeab": ("side", "Kartoffelsalat, servi en accompagnement"),
    # Soupes
    "bread_de_pain_a_la_tomate_14891a": ("soup", "soupe de pain et de tomate"),
    "main_pozole_82d096": ("soup", "soupe-ragoût de maïs hominy"),
    # Entrées
    "bread_panzanella_italienne_307da1": ("starter", "salade de pain"),
    "main_patatas_bravas_98ec00": ("starter", "tapa"),
    # En-cas
    "rice_beignet_de_riz_nepalais_7ac83e": ("snack", "sel roti, beignet de riz sucré"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    path = Path(RECIPES_PATH)
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    idx = {r["id"]: r for r in data["recipes"]}
    log: list[str] = []
    for rid, (dish, why) in RECLASS.items():
        r = idx[rid]
        if r.get("dish_type") != dish:
            log.append(f"{rid} : {r.get('dish_type')} → {dish} ({why})")
            r["dish_type"] = dish
    print(*log, f"{len(log)} changement(s)", sep="\n")
    if args.dry_run or not log:
        return
    end = "\n" if raw.endswith("\n") else ""
    write_with_retry(path, json.dumps(data, ensure_ascii=False, indent=2) + end)


def write_with_retry(path: Path, text: str) -> None:
    """Windows : juste après une autre écriture, l'ouverture échoue parfois (OSError 22) : on réessaie."""
    for attempt in range(5):
        try:
            with path.open("w", encoding="utf-8", newline="\n") as f:
                f.write(text)
            return
        except OSError:
            if attempt == 4:
                raise
            time.sleep(1)


if __name__ == "__main__":
    main()
