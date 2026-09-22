#!/usr/bin/env python3
"""
apply_recipe_patches.py — applique les corrections manuelles recette par recette
(relecture 2026-09-15, docs/revue_recettes_2026-09-15) décrites dans
scripts/recipes/recipe_patches/p*.py (dictionnaire PATCHES = {id: [opérations]}).

Opérations :
  ("ing", ancien_id, nouvel_id[, quantité[, unité]])  remplace un ingrédient
  ("qty", id, quantité[, unité])                      change une quantité
  ("add", id, quantité, unité, rôle)                  ajoute un ingrédient
  ("del", id)                                         retire un ingrédient
  ("sugg-", id)                                       retire une suggestion de service
  ("delq", id, quantité)                              retire la ligne ayant cette quantité (doublon)
  ("txt", ancien, nouveau)                            remplace un passage des instructions
  ("step-", passage)                                  supprime l'étape qui contient le passage
  ("steps", [texte, …])                               réécrit toutes les étapes (« Étape N : » ajouté)
  ("serv", n)                                         portions
  ("flag", régime, bool)                              diet_flags + tags.diet
  ("time", actif, passif, cuisson)                    temps (total recalculé)
  ("title", fr)                                       titre français
  ("dish", type)                                      dish_type
  ("desc", texte)                                     description
  ("origin", {clé: valeur, …})                        champs de origin (cuisine, country, region, city)
  ("compo", [(id, qté, unité, rôle[, état]), …])     réécrit toute la composition (suggestions conservées)
  ("title_en", texte)            titles.en et titles.original (recipe_patches/titles_en.py, variantes)

Variantes (recipe_patches/v*.py, dictionnaire VARIANTS) : définition complète d'une recette
qui la différencie de ses quasi-doublons. Elle remplace les opérations p*.py de la recette
(la variante est l'état final : les anciens correctifs ciblaient un texte qui n'existe plus).

Idempotent : une opération déjà appliquée est ignorée ; une opération qui ne
trouve pas sa cible (ingrédient ou passage absent) arrête le script.
Tout nouvel ingrédient doit avoir une fiche nutritionnelle.

Relancer ensuite fix_recipe_diet_allergens.py, build_derived_base_registry.py,
rebuild_graphs.py, build_index.py.

Usage :
    python scripts/recipes/apply_recipe_patches.py --dry-run
    python scripts/recipes/apply_recipe_patches.py
"""
import argparse, importlib, json, logging, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
logging.disable(logging.WARNING)

from backend.engine.config import RECIPES_PATH

PATCH_DIR = Path(__file__).parent / "recipe_patches"


class PatchError(Exception):
    pass


def load_patches() -> dict:
    sys.path.insert(0, str(PATCH_DIR.parent))
    patches = {}
    for f in sorted(PATCH_DIR.glob("p*.py")):
        mod = importlib.import_module(f"recipe_patches.{f.stem}")
        for rid, ops in mod.PATCHES.items():
            if rid in patches:
                raise PatchError(f"{rid} corrigée dans deux fichiers")
            patches[rid] = ops
    seen = set()
    for f in sorted(PATCH_DIR.glob("v*.py")):
        mod = importlib.import_module(f"recipe_patches.{f.stem}")
        for rid, ops in mod.VARIANTS.items():
            if rid in seen:
                raise PatchError(f"{rid} : variante définie dans deux fichiers")
            seen.add(rid)
            patches[rid] = ops  # remplace les correctifs p*.py de cette recette
    from recipe_patches.titles_en import TITLES_EN
    for rid, en in TITLES_EN.items():
        if rid not in seen:
            raise PatchError(f"{rid} : titre anglais sans variante")
        patches[rid] = [*patches[rid], ("title_en", en)]
    return patches


def _lines(r):
    return [c for c in r.get("composition") or [] if (c.get("meta") or {}).get("role") != "serving_suggestion"]


def _find(r, iid):
    return next((c for c in _lines(r) if c.get("ingredient") == iid), None)


def _renumber(steps: list[str]) -> list[str]:
    import re
    out, n = [], 0
    for s in steps:
        m = re.match(r"^(\s*[ÉE]tape\s*)\d+(\s*:\s*)", s)
        if m:
            n += 1
            s = f"{m.group(1)}{n}{m.group(2)}{s[m.end():]}"
        out.append(s)
    return out


def _has_nutrition(iid: str) -> bool:
    from backend.engine.nutrition_engine import get_data
    try:
        n = get_data.ingredients.resolve_nutrition(iid, use_cooked=False) or {}
    except Exception:
        return False
    return n.get("calories_kcal") is not None or iid.startswith("base_")


DIET_FLAGS = ("vegan", "vegetarian", "gluten_free", "lactose_free", "nut_free")


def reset_diet(r: dict) -> None:
    """Composition réécrite : régimes remis à vrai et allergènes vidés.

    fix_recipe_diet_allergens.py (lancé ensuite) ne fait que rétrograder les flags et
    ajouter les allergènes : il recalcule donc l'état exact à partir de la nouvelle
    composition, sans garder les restrictions de l'ancienne."""
    flags = r.setdefault("diet_flags", {})
    for f in DIET_FLAGS:
        flags[f] = True
    tags = r.setdefault("tags", {})
    tags["diet"] = [d for d in tags.get("diet") or [] if d not in DIET_FLAGS] + list(DIET_FLAGS)
    tags["allergens"] = []


def apply_op(r: dict, op: tuple) -> str | None:
    kind, args = op[0], op[1:]
    if kind == "ing":
        old, new, *rest = args
        line = _find(r, old)
        if line is None:
            if _find(r, new) is not None:
                return None
            raise PatchError(f"ingrédient absent : {old}")
        if not _has_nutrition(new):
            raise PatchError(f"pas de fiche nutritionnelle : {new}")
        line["ingredient"] = new
        if rest:
            line["quantity"] = rest[0]
        if len(rest) > 1:
            line["unit"] = rest[1]
        return f"{old} → {new} {line.get('quantity')} {line.get('unit')}"
    if kind == "qty":
        iid, q, *u = args
        line = _find(r, iid)
        if line is None:
            raise PatchError(f"ingrédient absent : {iid}")
        if line.get("quantity") == q and (not u or line.get("unit") == u[0]):
            return None
        old = line.get("quantity")
        line["quantity"] = q
        if u:
            line["unit"] = u[0]
        return f"{iid} {old} → {q} {line.get('unit')}"
    if kind == "add":
        iid, q, unit, role = args
        if _find(r, iid) is not None:
            return None
        if not _has_nutrition(iid):
            raise PatchError(f"pas de fiche nutritionnelle : {iid}")
        r["composition"].append({"ingredient": iid, "quantity": q, "unit": unit,
                                 "meta": {"role": role, "form": "", "state": "raw", "preparation": ""}})
        return f"+ {iid} {q} {unit}"
    if kind == "delq":  # retire la ligne de cet ingrédient ayant cette quantité (ingrédient en double)
        iid, q = args
        line = next((c for c in _lines(r) if c.get("ingredient") == iid and c.get("quantity") == q), None)
        if line is None:
            return None
        r["composition"].remove(line)
        return f"- {iid} {q}"
    if kind == "sugg-":  # retire une suggestion de service
        (iid,) = args
        lines = [c for c in r.get("composition") or []
                 if c.get("ingredient") == iid and (c.get("meta") or {}).get("role") == "serving_suggestion"]
        for c in lines:
            r["composition"].remove(c)
        return f"- suggestion {iid}" if lines else None
    if kind == "del":
        (iid,) = args
        line = _find(r, iid)
        if line is None:
            return None
        r["composition"].remove(line)
        return f"- {iid}"
    if kind == "txt":
        old, new = args
        steps = r.get("instructions") or []
        if new and old in new and any(new in s for s in steps):
            return None  # remplacement qui prolonge le passage : déjà appliqué
        hits = [i for i, s in enumerate(steps) if old in s]
        if not hits:
            if not new or any(new in s for s in steps):
                return None  # déjà appliquée (un passage supprimé ne se retrouve plus)
            raise PatchError(f"passage absent : {old[:60]!r}")
        for i in hits:
            steps[i] = steps[i].replace(old, new)
        return f"texte : {old[:40]!r} → {new[:40]!r}"
    if kind == "step-":
        (old,) = args
        steps = r.get("instructions") or []
        hits = [s for s in steps if old in s]
        if not hits:
            return None
        if len(steps) - len(hits) < 2:
            raise PatchError(f"suppression d'étape laisserait moins de 2 étapes : {old[:40]!r}")
        kept = [s for s in steps if old not in s]
        r["instructions"] = _renumber(kept)
        return f"étape supprimée : {old[:50]!r}"
    if kind == "steps":
        (new_steps,) = args
        new_steps = [f"Étape {i} : {t}" for i, t in enumerate(new_steps, 1)]
        if r.get("instructions") == new_steps:
            return None
        r["instructions"] = new_steps
        return f"instructions réécrites ({len(new_steps)} étapes)"
    if kind == "serv":
        (n,) = args
        if r.get("servings") == n:
            return None
        old = r.get("servings")
        r["servings"] = n
        if "servings_default" in r:
            r["servings_default"] = n
        return f"portions {old} → {n}"
    if kind == "flag":
        name, value = args
        flags = r.setdefault("diet_flags", {})
        diet = r.setdefault("tags", {}).setdefault("diet", [])
        changed = flags.get(name) is not value or ((name in diet) != value)
        flags[name] = value
        if value and name not in diet:
            diet.append(name)
        if not value and name in diet:
            diet.remove(name)
        return f"{name} = {value}" if changed else None
    if kind == "time":
        a, p, c = args
        t = r.setdefault("timing", {})
        new = {"prep_active_min": a, "prep_passive_min": p, "cook_min": c, "total_min": a + p + c}
        if all(t.get(k) == v for k, v in new.items()):
            return None
        t.update(new)
        return f"temps {a}/{p}/{c}"
    if kind == "title":
        (fr,) = args
        if r["titles"].get("fr") == fr:
            return None
        old = r["titles"].get("fr")
        r["titles"]["fr"] = fr
        return f"titre {old!r} → {fr!r}"
    if kind == "title_en":
        (en,) = args
        t = r["titles"]
        if t.get("en") == en and t.get("original") == en:
            return None
        old = t.get("en")
        t["en"] = t["original"] = en
        return f"titre anglais {old!r} → {en!r}"
    if kind == "yield":
        (y,) = args
        if r.get("yield_factor") == y:
            return None
        old = r.get("yield_factor")
        r["yield_factor"] = y
        return f"rendement {old} → {y}"
    if kind == "dish":
        (dt,) = args
        if r.get("dish_type") == dt:
            return None
        old = r.get("dish_type")
        r["dish_type"] = dt
        return f"type {old} → {dt}"
    if kind == "desc":
        (txt,) = args
        if r.get("description") == txt:
            return None
        r["description"] = txt
        return f"description : {txt[:50]!r}"
    if kind == "origin":
        (vals,) = args
        o = r.setdefault("origin", {})
        if all(o.get(k) == v for k, v in vals.items()):
            return None
        o.update(vals)
        return f"origine {vals}"
    if kind == "compo":
        (items,) = args
        new = []
        for it in items:
            iid, q, unit, role, *st = it
            new.append({"ingredient": iid, "quantity": q, "unit": unit,
                        "meta": {"role": role, "form": "", "state": st[0] if st else "raw", "preparation": ""}})
        # les suggestions de service listées remplacent les anciennes ; sinon celles en place sont gardées
        is_sugg = lambda c: (c.get("meta") or {}).get("role") == "serving_suggestion"
        key = lambda c: (c["ingredient"], c.get("quantity"), c.get("unit"), (c.get("meta") or {}).get("role"),
                         (c.get("meta") or {}).get("state"))
        old = r.get("composition") or []
        sugg = [c for c in new if is_sugg(c)] or [c for c in old if is_sugg(c)]
        new = [c for c in new if not is_sugg(c)] + sugg
        if [key(c) for c in old] == [key(c) for c in new]:
            return None
        for c in new:
            if not is_sugg(c) and not _has_nutrition(c["ingredient"]):
                raise PatchError(f"pas de fiche nutritionnelle : {c['ingredient']}")
        r["composition"] = new
        reset_diet(r)
        return f"composition réécrite ({len(new)} ingrédients)"
    raise PatchError(f"opération inconnue : {kind}")


def apply_all(recipes: list[dict], patches: dict) -> list[str]:
    by_id = {r["id"]: r for r in recipes}
    log, errors = [], []
    for rid, ops in patches.items():
        r = by_id.get(rid)
        if r is None:
            errors.append(f"{rid} : recette introuvable")
            continue
        for op in ops:
            try:
                msg = apply_op(r, op)
            except PatchError as e:
                errors.append(f"{rid} : {e}")
                continue
            if msg:
                log.append(f"{rid} : {msg}")
    if errors:
        raise SystemExit("ERREURS :\n  " + "\n  ".join(errors))
    return log


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    raw = json.loads(Path(RECIPES_PATH).read_text(encoding="utf-8"))
    patches = load_patches()
    log = apply_all(raw["recipes"], patches)
    for line in log:
        print(line)
    print(f"\n{len(patches)} recettes corrigées, {len(log)} modifications")
    if args.dry_run or not log:
        return
    tmp = Path(RECIPES_PATH).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(RECIPES_PATH)
    print(f"écrit : {RECIPES_PATH}")


if __name__ == "__main__":
    main()
