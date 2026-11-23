"""
composites.py — Nutrition des ingrédients composites (mélanges d'épices, fruits
rouges mélangés, chutney…) calculée depuis leurs composants.

Appelé par build_n2_direct.py après l'injection des suppléments MANUAL : la
variante `default` de chaque composite est remplacée par la somme pondérée de
ses composants (déjà construits depuis CIQUAL / CNF / USDA), ramenée à 100 g
du lot fini.

Règles :
  - poids du lot = yield_g s'il est donné (l'eau évaporée est retirée de
    water_g), sinon la somme des composants ;
  - un nutriment n'est calculé que si les composants qui le renseignent pèsent
    au moins la moitié du lot ; il est alors extrapolé à tout le lot et listé
    dans `_estimated_fields` quand la couverture n'est pas complète. En deçà,
    il reste absent (inconnu) plutôt que faussement nul.

Format du fichier : backend/data/nutrition/reference/composite_ingredients.json
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
COMPOSITES_FILE = ROOT / "backend" / "data" / "nutrition" / "reference" / "composite_ingredients.json"

MIN_COVERAGE = 0.5
_META_FIELDS = {"axes", "axes_fr", "name_fr", "name_en", "indus_conditionne", "conditioning_types"}


def _numeric_fields(variant: dict) -> dict:
    return {k: v for k, v in variant.items()
            if not k.startswith("_") and k not in _META_FIELDS
            and isinstance(v, (int, float)) and not isinstance(v, bool)}


def load_composites(path: Path | None = None) -> dict:
    path = path or COMPOSITES_FILE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8")).get("composites", {})


def compute(spec: dict, ingredients: dict) -> tuple[dict, dict]:
    """Nutriments pour 100 g du lot fini + informations de traçabilité.

    Raises:
        KeyError si un composant (clé n2 / variante) est introuvable.
    """
    comps = []
    for c in spec["components"]:
        base = ingredients.get(c["ingredient"])
        if base is None or c["variant"] not in base.get("variants", {}):
            raise KeyError(f"{c['ingredient']}/{c['variant']}")
        comps.append((float(c["g"]), _numeric_fields(base["variants"][c["variant"]]),
                      base["variants"][c["variant"]].get("_source")))
    total = sum(g for g, _, _ in comps)
    batch = float(spec.get("yield_g") or total)
    fields = sorted({f for _, vals, _ in comps for f in vals})

    out, estimated = {}, []
    for f in fields:
        known = [(g, vals[f]) for g, vals, _ in comps if f in vals]
        known_g = sum(g for g, _ in known)
        if not known or known_g / total < MIN_COVERAGE:
            continue
        amount = sum(g * v / 100.0 for g, v in known) * (total / known_g)   # pour tout le lot
        if f == "water_g":
            amount -= (total - batch)                                        # eau évaporée
            amount = max(amount, 0.0)
        out[f] = round(amount * 100.0 / batch, 4)
        if known_g < total:
            estimated.append(f)
    if "sodium_mg" in out:
        out["salt_g"] = round(out["sodium_mg"] * 0.00254, 4)

    official_g = sum(g for g, _, src in comps if src not in ("MANUAL", "COMPOSITE", None))
    trace = {
        "_components": [{"ingredient": c["ingredient"], "variant": c["variant"], "g": c["g"]}
                        for c in spec["components"]],
        "_batch_g": batch,
        "_official_share": round(official_g / total, 3),
        "_estimated_fields": estimated,
    }
    return out, trace


def apply(ingredients: dict, composites: dict | None = None) -> dict:
    """Remplace la variante `default` de chaque composite présent. Rapport : {clé: kcal | erreur}."""
    composites = load_composites() if composites is None else composites
    report = {}
    for key, spec in composites.items():
        base = ingredients.get(key)
        if base is None:
            report[key] = "absent de nutrition_v2"
            continue
        try:
            nutrients, trace = compute(spec, ingredients)
        except KeyError as e:
            report[key] = f"composant introuvable : {e}"
            continue
        old = base.get("variants", {}).get("default", {})
        keep = {k: v for k, v in old.items() if k.startswith("_v32") or k in _META_FIELDS}
        base.setdefault("variants", {})["default"] = {
            **keep,
            "_source": "COMPOSITE",
            "_source_id": None,
            **trace,
            **nutrients,
        }
        report[key] = nutrients.get("calories_kcal")
    return report


__all__ = ["load_composites", "compute", "apply", "COMPOSITES_FILE", "MIN_COVERAGE"]
