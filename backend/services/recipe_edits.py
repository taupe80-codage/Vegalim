"""
recipe_edits.py — Recette modifiée par un membre (2026-11-26).

Le membre remplace, retire ou ajoute des ingrédients et change les quantités
sur la fiche. La version modifiée est décrite par des « lignes » :

    {"base": "original" | "vegan",
     "rows": [{"src": 0, "orig": "eggplant_raw", "ingredient": "zucchini_raw",
               "quantity": 400, "unit": "g"},           # ligne 0 remplacée
              {"src": 2, "orig": "garlic_raw", "ingredient": "garlic_raw",
               "quantity": 25, "unit": "g"},            # ligne 2 inchangée
              {"src": null, "ingredient": "tofu_plain_pre_packaged",
               "quantity": 200, "unit": "g"}]}          # ajoutée

Une ligne de la recette absente de `rows` est retirée. `src` désigne la ligne
de la composition de base (recette ou sa version vegan) ; `orig` (son
ingrédient) permet de la retrouver si la recette a été retouchée depuis.
Les quantités sont celles de la recette (pour ses portions d'origine).

La même description sert partout : fiche, version enregistrée, planning,
liste de courses, coût et bilan de la semaine.

Nutrition : écart calculé (CIQUAL) entre la version modifiée et l'originale,
ajouté aux valeurs de la fiche d'origine. Sans modification, la version
affiche exactement les valeurs de l'originale.
"""
from __future__ import annotations

import copy
import logging
import re
from functools import lru_cache

from backend.core.data_cache import data_cached

logger = logging.getLogger(__name__)

MAX_ROWS = 60
MAX_QTY = 10_000            # g ou ml, pour la recette entière
NUMERIC_UNITS = ("g", "ml")
# Indications propres à l'ingrédient d'origine : fausses pour son remplaçant
_DROP_META_ON_REPLACE = ("ingredient_fr", "note", "preparation")
_NON_NUMERIC_NUTR = {"servings_used", "source", "_per_serving", "_source", "glycemic_index"}


class EditError(ValueError):
    """Description de modifications invalide (message affichable)."""


# ── Noms et validation ────────────────────────────────────────────────────────

def display_name(iid: str) -> str:
    from backend.engine.rule_engine.variants import _display_name
    return _display_name(iid)


def is_known_ingredient(iid: str) -> bool:
    """Ingrédient du dictionnaire (tous végétariens) ou préparation de base."""
    from backend.core.data_io import load_ingredients_dict
    from backend.db.culinary_repositories import _recipes_index
    return bool(iid) and (iid in load_ingredients_dict() or iid in _recipes_index())


def _qty_str(q, unit) -> str:
    if q in (None, ""):
        return str(unit or "")
    q = float(q)
    txt = str(int(round(q))) if abs(q - round(q)) < 1e-9 or q >= 10 else f"{q:.1f}".replace(".", ",")
    return f"{txt} {unit or ''}".strip()


def normalize_rows(raw_rows) -> list[dict]:
    """Lignes validées (types, bornes) ; EditError sinon."""
    if not isinstance(raw_rows, list) or not raw_rows:
        raise EditError("Gardez au moins un ingrédient.")
    if len(raw_rows) > MAX_ROWS:
        raise EditError(f"{MAX_ROWS} ingrédients au plus.")
    rows = []
    for x in raw_rows:
        if not isinstance(x, dict):
            raise EditError("Ligne d'ingrédient illisible.")
        src = x.get("src")
        if src is not None:
            if isinstance(src, bool) or not isinstance(src, int) or src < 0 or src > 500:
                raise EditError("Ligne d'ingrédient inconnue.")
        ing = str(x.get("ingredient") or "").strip()
        if not ing or len(ing) > 120:
            raise EditError("Ingrédient manquant.")
        q = x.get("quantity")
        if q is not None:
            try:
                q = float(q)
            except (TypeError, ValueError):
                raise EditError("Quantité illisible.")
            if not 0 < q <= MAX_QTY:
                raise EditError("Quantité hors limites (de 0,1 g à 10 kg).")
        unit = x.get("unit")
        if unit is not None and unit not in NUMERIC_UNITS:
            raise EditError("Unité acceptée : g ou ml.")
        orig = x.get("orig")
        orig = str(orig)[:120] if orig else None
        rows.append({"src": src, "orig": orig, "ingredient": ing, "quantity": q, "unit": unit})
    return rows


def base_recipe(recipe: dict, base: str) -> dict:
    """Composition de départ : la recette, ou sa version vegan (fiable seulement)."""
    if base == "original":
        return recipe
    if base != "vegan":
        raise EditError("Version de départ inconnue.")
    if (recipe.get("diet_flags") or {}).get("vegan"):
        return recipe
    from backend.engine.rule_engine.variants import vegan_variant
    v = vegan_variant(recipe)
    if v.get("source") != "generated":
        raise EditError("Pas de version vegan fiable pour ce plat.")
    return v["recipe"]


# ── Étapes ────────────────────────────────────────────────────────────────────

_UNIT_WORDS = {"g": r"g|grammes?", "ml": r"ml|millilitres?"}


def _num_pattern(q: float) -> str:
    if abs(q - round(q)) < 1e-9:
        return str(int(round(q)))
    return f"{q:.1f}".replace(".", "[,.]").rstrip("0")


def _name_forms(iid: str, item: dict) -> list[str]:
    from backend.engine.rule_engine.variants import _forms
    names = [display_name(iid)]
    fr = (item.get("meta") or {}).get("ingredient_fr")
    if fr:
        names.append(fr)
    forms: set[str] = set()
    for n in names:
        forms.update(_forms(n))
    return sorted(forms, key=len, reverse=True)


def _rewrite_quantities(steps: list, qty_changes: list[tuple]) -> tuple[list, int]:
    """« 500 g d'aubergines » → « 300 g d'aubergines » : seulement la quantité suivie
    (à deux mots près) du nom de l'ingrédient, pour ne pas toucher aux autres."""
    rules = []
    for item, q0, u0, q1, u1 in qty_changes:
        forms = _name_forms(item["ingredient"], item)
        if not forms:
            continue
        alt = "|".join(re.escape(f) for f in forms)
        pat = re.compile(
            rf"(?<![\d,.])({_num_pattern(q0)})\s?({_UNIT_WORDS[u0]})(?![\w])"
            rf"(?=\s+(?:de |d'|d’|du |des )?(?:[\wàâçéèêëîïôûùœ’'-]+\s+){{0,2}}?(?:{alt})(?![\w]))",
            re.I)
        rules.append((pat, _qty_str(q1, "").strip(), None if u1 == u0 else u1))
    if not rules:
        return steps, 0
    out, changed = [], 0
    for step in steps:
        if not isinstance(step, str):
            out.append(step)
            continue
        new = step
        for pat, num, unit in rules:
            new = pat.sub(lambda m, n=num, u=unit: f"{n} {u or m.group(2)}", new)
        changed += new != step
        out.append(new)
    return out, changed


def _mentions(steps: list, iid: str, item: dict) -> bool:
    forms = _name_forms(iid, item)
    if not forms:
        return False
    pat = re.compile(rf"(?<![\w'’])(?:{'|'.join(re.escape(f) for f in forms)})(?!\w)", re.I)
    return any(isinstance(s, str) and pat.search(s) for s in steps)


# ── Régimes et allergènes ─────────────────────────────────────────────────────

def _recompute_diet(r: dict) -> None:
    """Régimes et allergènes recalculés sur la composition modifiée (comme la
    variante vegan) : remplacer le beurre par du beurre de cacahuète ajoute
    l'arachide, retirer la feta rend le plat sans lactose."""
    from backend.engine.rule_engine.diet import allergen_tags, compute_diet_flags
    core = [c for c in r.get("composition") or []
            if isinstance(c, dict) and (c.get("meta") or {}).get("role") != "serving_suggestion"]
    computed = compute_diet_flags({**r, "composition": core})
    allergens = allergen_tags(r)
    flags = dict(r.get("diet_flags") or {})
    for f in ("vegan", "vegetarian", "gluten_free", "lactose_free", "nut_free"):
        if f in computed:
            flags[f] = bool(computed[f])
    excludes = {"gluten_free": {"gluten"}, "lactose_free": {"milk", "lactose"},
                "nut_free": {"tree_nuts", "peanuts"}, "vegan": {"milk", "eggs"}}
    for f, tags_ in excludes.items():
        if tags_ & set(allergens):
            flags[f] = False
    r["diet_flags"] = flags
    tags = r.setdefault("tags", {})
    if isinstance(tags, dict):
        tags["allergens"] = allergens
        diet = [d for d in (tags.get("diet") or []) if not (d in flags and flags[d] is False)]
        if flags.get("vegan") and "vegan" not in diet:
            diet.append("vegan")
        tags["diet"] = diet


# ── Application ───────────────────────────────────────────────────────────────

def apply_edits(recipe: dict, edits: dict) -> dict:
    """Version modifiée d'une recette.

    Returns: {"recipe": recette modifiée, "base": ..., "changes": [...],
              "step_notes": [...], "rows": lignes normalisées}
    Raises: EditError.
    """
    if not isinstance(edits, dict):
        raise EditError("Modifications illisibles.")
    base = edits.get("base") or "original"
    rows = normalize_rows(edits.get("rows"))
    start = base_recipe(recipe, base)
    comp = [c for c in start.get("composition") or [] if isinstance(c, dict)]

    used: set[int] = set()
    resolved: list[tuple[int | None, dict]] = []
    for row in rows:
        s = row["src"]
        if s is not None:
            ok = s < len(comp) and s not in used and (
                not row["orig"] or comp[s].get("ingredient") == row["orig"])
            if not ok:
                # recette retouchée depuis l'enregistrement : on retrouve la ligne
                # par son ingrédient, sinon elle devient un ajout
                s = next((i for i, c in enumerate(comp)
                          if i not in used and row["orig"] and c.get("ingredient") == row["orig"]), None)
                if s is None and not row["orig"]:
                    raise EditError("Ligne d'ingrédient inconnue.")
        if s is not None:
            used.add(s)
        resolved.append((s, row))

    new_comp: list[dict] = []
    changes: list[dict] = []
    applied: list[dict] = []
    qty_changes: list[tuple] = []
    added_items: list[dict] = []
    for s, row in resolved:
        iid = row["ingredient"]
        if not is_known_ingredient(iid):
            raise EditError(f"Ingrédient inconnu : {iid}.")
        if s is None:
            if row["quantity"] is None:
                raise EditError(f"Indiquez la quantité de : {display_name(iid)}.")
            unit = row["unit"] or "g"
            item = {"ingredient": iid, "quantity": round(row["quantity"], 1), "unit": unit,
                    "meta": {"role": "added"}}
            changes.append({"kind": "added", "ingredient": iid, "name": display_name(iid),
                            "after": _qty_str(item["quantity"], unit)})
            added_items.append(item)
            new_comp.append(item)
            continue
        orig_item = comp[s]
        item = copy.deepcopy(orig_item)
        meta = dict(item.get("meta") or {})
        oid = orig_item.get("ingredient")
        change: dict = {"ingredient": iid, "name": display_name(oid)}
        if iid != oid:
            item["ingredient"] = iid
            for k in _DROP_META_ON_REPLACE:
                meta.pop(k, None)
            applied.append({"original": oid, "substitute": iid,
                            "original_name": display_name(oid), "substitute_name": display_name(iid)})
            change.update(kind="replaced", original=oid, new_name=display_name(iid))
        q0, u0 = orig_item.get("quantity"), orig_item.get("unit")
        if row["quantity"] is not None:
            unit = row["unit"] or (u0 if u0 in NUMERIC_UNITS else "g")
            q1 = round(row["quantity"], 1)
            if not (q0 is not None and abs(float(q0) - q1) < 0.05 and u0 == unit):
                item["quantity"], item["unit"] = q1, unit
                change.setdefault("kind", "quantity")
                change["before"] = _qty_str(q0, u0)
                change["after"] = _qty_str(q1, unit)
                if q0 and u0 in NUMERIC_UNITS:
                    qty_changes.append((orig_item, float(q0), u0, q1, unit))
        item["meta"] = meta
        if "kind" in change:
            changes.append(change)
        new_comp.append(item)

    removed = [comp[i] for i in range(len(comp)) if i not in used]
    for c in removed:
        changes.append({"kind": "removed", "ingredient": c.get("ingredient"),
                        "name": display_name(c.get("ingredient") or ""),
                        "before": _qty_str(c.get("quantity"), c.get("unit"))})
    if not any((c.get("meta") or {}).get("role") != "serving_suggestion" for c in new_comp):
        raise EditError("Gardez au moins un ingrédient.")

    r = copy.deepcopy(start)
    r["composition"] = new_comp
    steps = list(r.get("instructions") or [])
    n_changed = 0
    if qty_changes:
        steps, n = _rewrite_quantities(steps, qty_changes)
        n_changed += n
    if applied:
        from backend.engine.rule_engine.variants import _rewrite_steps
        steps, n = _rewrite_steps(steps, applied, edit=True)
        n_changed += n
        if isinstance(r.get("description"), str):
            r["description"] = _rewrite_steps([r["description"]], applied, prose=True, edit=True)[0][0]
    if isinstance(r.get("instructions"), list):
        r["instructions"] = steps

    notes: list[str] = []
    for c in removed:
        if _mentions(steps, c.get("ingredient") or "", c):
            notes.append(f"Les étapes parlent encore de « {display_name(c.get('ingredient') or '').lower()} » "
                         "(retiré) : sautez ce passage.")
    for a in applied:
        item = next((c for c in comp if c.get("ingredient") == a["original"]), {})
        if _mentions(steps, a["original"], item):
            notes.append(f"Là où les étapes disent encore « {a['original_name'].lower()} », "
                         f"utilisez {a['substitute_name'].lower()}.")
    for it in added_items:
        name = display_name(it["ingredient"])
        notes.append(f"{name[:1].upper()}{name[1:]} ({_qty_str(it['quantity'], it['unit'])}) "
                     "n'est pas dans les étapes : ajoutez-le au moment qui convient.")

    r.pop("_vegan_variant", None)
    _recompute_diet(r)
    r["_steps_rewritten"] = n_changed
    return {"recipe": r, "base": base, "changes": changes, "step_notes": notes,
            "rows": rows, "base_composition": comp}


def custom_recipe(recipe: dict, edits: dict) -> dict:
    """Recette modifiée seule (liste de courses, coût)."""
    return apply_edits(recipe, edits)["recipe"]


# ── Nutrition ────────────────────────────────────────────────────────────────

def _numeric(d: dict) -> dict[str, float]:
    return {k: float(v) for k, v in (d or {}).items()
            if k not in _NON_NUMERIC_NUTR and isinstance(v, (int, float)) and not isinstance(v, bool)}


def custom_nutrition(original: dict, custom: dict) -> tuple[dict, dict]:
    """(nutrition de la fiche, nutrition « graphe ») par portion de la version.

    Valeurs de l'originale + écart CIQUAL (version − originale) : la fiche, le
    score et le bilan de la semaine restent cohérents avec ceux de l'originale.
    """
    from backend.core.data_io import load_nutrition_graph
    from backend.engine.nutrition_engine import compute_nutrition
    rid = str(original.get("id", ""))
    fresh0 = compute_nutrition(original)
    fresh1 = compute_nutrition(custom)
    graph0 = _numeric(load_nutrition_graph().get(rid) or {})
    f0, f1 = _numeric(fresh0), _numeric(fresh1)
    # fiche d'origine : valeurs CIQUAL, graphe pour les clés absentes (enrich_one)
    merged0 = dict(f0)
    for k, v in graph0.items():
        if k not in merged0 or (not merged0[k] and v):
            merged0[k] = v
    keys = set(merged0) | set(f1)
    delta = {k: f1.get(k, 0.0) - f0.get(k, 0.0) for k in keys}

    def _shift(ref: dict) -> dict:
        out = {k: round(max(0.0, ref.get(k, merged0.get(k, 0.0)) + delta.get(k, 0.0)), 2)
               for k in keys | set(ref)}
        if out.get("sodium", 0) > 0:
            out["salt"] = round(out["sodium"] * 0.00254, 2)
        if "calories" in out:
            out["calories"] = round(out["calories"])
        gi = fresh1.get("glycemic_index")
        if gi:
            out["glycemic_index"] = gi
        return out

    panel = _shift(merged0)
    for k in ("servings_used", "source"):
        if k in fresh1:
            panel[k] = fresh1[k]
    graph = _shift(graph0) if graph0 else dict(panel)
    return panel, graph


def portion_nutrition(recipe: dict, edits: dict | None) -> dict:
    """Nutrition par portion (format du graphe) : version modifiée si `edits`."""
    from backend.core.data_io import load_nutrition_graph
    if edits:
        try:
            return custom_nutrition(recipe, custom_recipe(recipe, edits))[1]
        except EditError:
            logger.info("portion_nutrition : modifications ignorées pour %s", recipe.get("id"))
    return load_nutrition_graph().get(str(recipe.get("id", ""))) or {}


# ── Fiche complète ────────────────────────────────────────────────────────────

def custom_view(recipe: dict, edits: dict) -> dict:
    """Fiche de la version modifiée : mêmes champs que GET /recettes/{id}
    (nutrition, prix, carbone, badges, scores), plus `_custom`."""
    from backend.services.enrichment_service import _AJR, enrich_one
    from backend.services.filter_service import health_scores_for
    res = apply_edits(recipe, edits)
    custom = res["recipe"]
    out = dict(custom)
    out.update(enrich_one(custom))
    panel, graph = custom_nutrition(recipe, custom)
    servings = out.get("nutrition", {}).get("_per_serving") or custom.get("servings") or 4
    out["nutrition"] = {**panel, "_per_serving": servings}
    summary: dict = {}
    for key, ajr in _AJR.items():
        val = graph.get(key, 0) or 0
        summary[key] = {"value": round(val, 1), "pct_ajr": round(val / ajr * 100) if val > 0 and ajr else 0}
    summary["calories"] = {"value": round(graph.get("calories") or 0), "pct_ajr": 0}
    summary["_servings"] = servings
    out["_nutrition"] = summary
    out["health_scores"] = health_scores_for(custom, graph)
    try:
        from backend.engine.diabetes import diabetes_watch
        out["diabetes_watch"] = diabetes_watch(custom)
    except Exception as e:  # la fiche reste servie sans l'information
        logger.warning("diabetes_watch (version) échoué : %s", e)
    from backend.engine.equipment import recipe_equipment
    out["equipment_needed"] = recipe_equipment(custom)
    out.pop("vegan_variant", None)
    out["_custom"] = {"base": res["base"], "changes": res["changes"],
                      "step_notes": res["step_notes"], "rows": res["rows"],
                      # composition de départ : l'éditeur de la fiche en part
                      "base_composition": res["base_composition"],
                      "base_ingredients_meta": _names_meta(res["base_composition"])}
    return out


def _names_meta(composition: list[dict]) -> dict:
    return {c["ingredient"]: {"name_fr": display_name(c["ingredient"])}
            for c in composition if isinstance(c, dict) and c.get("ingredient")}


def has_changes(recipe: dict, edits: dict) -> bool:
    return bool(apply_edits(recipe, edits)["changes"])


# ── Suggestions de remplacement ───────────────────────────────────────────────

@lru_cache(maxsize=4096)
def _per100(iid: str) -> tuple[float, ...] | None:
    """kcal, protéines, glucides, lipides, fibres pour 100 g (CIQUAL)."""
    from backend.engine.nutrition_engine import compute_nutrition
    try:
        n = compute_nutrition({"composition": [{"ingredient": iid, "quantity": 100, "unit": "g",
                                                "meta": {}}], "servings": 1})
    except Exception:
        return None
    v = tuple(float(n.get(k) or 0) for k in ("calories", "protein", "carbs", "fat", "fiber"))
    return v if any(v) else None


@lru_cache(maxsize=1)
def _usual_roles() -> dict[str, str]:
    """Rôle le plus fréquent de chaque ingrédient dans les recettes (base,
    aromatic, spice, fat…) : l'aubergine ne se remplace pas par du gingembre."""
    from collections import Counter, defaultdict
    from backend.core.data_io import load_catalogue_recipes
    roles: dict[str, Counter] = defaultdict(Counter)
    for r in load_catalogue_recipes():
        for c in r.get("composition") or []:
            role = (c.get("meta") or {}).get("role")
            if isinstance(c, dict) and c.get("ingredient") and role and role != "serving_suggestion":
                roles[c["ingredient"]][role] += 1
    return {iid: cnt.most_common(1)[0][0] for iid, cnt in roles.items()}


def _distance(a, b) -> float:
    w = (1 / 40, 1 / 4, 1 / 8, 1 / 4, 1 / 3)       # 40 kcal ≈ 4 g de protéines ≈ 8 g de glucides
    return sum(((x - y) * k) ** 2 for x, y, k in zip(a, b, w)) ** 0.5


MAX_SUGGEST_DISTANCE = 2.5


def culinary_equivalents(iid: str) -> list[tuple[str, str]]:
    """[(id, libellé du groupe)] des ingrédients qui jouent le même rôle en
    cuisine (backend/data/config/culinary_equivalences.json, écrit à la main)."""
    out: list[tuple[str, str]] = []
    for g in _equivalence_groups():
        if iid in g["ingredients"]:
            label = g["label"] + (f" ({g['note']})" if g.get("note") else "")
            out += [(x, label) for x in g["ingredients"] if x != iid and x not in {o for o, _ in out}]
    return out


@data_cached
def _equivalence_groups() -> list[dict]:
    from backend.core.data_io import load_json
    from backend.engine.config import DATA_ROOT
    data = load_json(DATA_ROOT / "config" / "culinary_equivalences.json", default={}) or {}
    return [g for g in data.get("groups") or [] if isinstance(g, dict) and g.get("ingredients")]
MAX_OTHER_USE_DISTANCE = 1.2      # autre usage : seulement s'il est très proche

_KIND_OVERRIDES = (
    (re.compile(r"coconut_(milk|cream)|(?:^|_)cream(?:_|$)|creme"), "crème"),
)


def _kind(iid: str) -> str:
    """Famille d'un ingrédient pour les remplacements : le rayon, sans tenir
    compte de la boîte (pois chiches en conserve = légumineuse) ; lait et
    crème de coco avec les crèmes."""
    from backend.engine.planning_engine.shopping import aisle_of
    for pat, kind in _KIND_OVERRIDES:
        if pat.search(iid):
            return kind
    return aisle_of(re.sub(r"_?canned_?|_?in_brine", "_", iid).strip("_"))


def replacement_suggestions(iid: str, limit: int = 8) -> list[dict]:
    """Remplaçants proposés : substitut vegan connu, équivalents en cuisine
    (table écrite à la main), puis ingrédients du même rayon et du même usage aux
    valeurs nutritionnelles proches, déjà utilisés dans les recettes."""
    from backend.core.data_io import load_ingredients_dict
    from backend.engine.planning_engine.shopping import aisle_of
    from backend.engine.rule_engine.variants import VEGAN_SUBS_CIQUAL
    from backend.services.ingredient_catalog import get_catalog
    out: list[dict] = []
    seen = {iid}
    sub = VEGAN_SUBS_CIQUAL.get(iid)
    if sub and is_known_ingredient(sub):
        out.append({"id": sub, "name_fr": display_name(sub), "reason": "version vegan"})
        seen.add(sub)
    from backend.engine.rule_engine.variants import _is_vegan_id
    equivalents = culinary_equivalents(iid)
    if _is_vegan_id(iid):              # un plat vegan le reste : équivalents vegan d'abord
        equivalents.sort(key=lambda e: _is_vegan_id(e[0]) is False)
    for cid, label in equivalents:
        if cid not in seen and is_known_ingredient(cid):
            out.append({"id": cid, "name_fr": display_name(cid), "reason": f"équivalent en cuisine : {label.lower()}"})
            seen.add(cid)
    d = load_ingredients_dict()
    group = (d.get(iid) or {}).get("v32_ing_id")
    aisle = _kind(iid)
    ref = _per100(iid)
    name0 = display_name(iid).lower()
    role = _usual_roles().get(iid)
    pool = []
    for e in get_catalog():
        cid = e["id"]
        if cid in seen or (e.get("recipe_count") or 0) < 2 or cid not in d:
            continue
        if group and (d.get(cid) or {}).get("v32_ing_id") == group:
            continue                       # même produit, autre état (cru / cuit)
        if _kind(cid) != aisle:
            continue
        name = display_name(cid)
        if name.lower() == name0:
            continue
        v = _per100(cid)
        dist = _distance(ref, v) if ref and v else 2.0
        if dist > MAX_SUGGEST_DISTANCE:
            continue                       # trop différent (glace pour du tofu)
        # même usage d'abord (base, aromate, épice…) ; les autres seulement s'il en manque
        other_use = bool(role) and _usual_roles().get(cid, role) != role
        if other_use and dist > MAX_OTHER_USE_DISTANCE:
            continue
        pool.append((other_use, dist - min(e["recipe_count"], 80) / 160, cid, name))
    pool.sort()
    if sum(1 for x in pool if not x[0]) >= 2:
        pool = [x for x in pool if not x[0]]
    pool = [x[1:] for x in pool]
    names = {o["name_fr"].lower() for o in out}
    for _, cid, name in pool:
        if len(out) >= limit:
            break
        if name.lower() in names:
            continue
        names.add(name.lower())
        out.append({"id": cid, "name_fr": name, "reason": "même rayon, valeurs proches"})
    return out


# ── Planning ─────────────────────────────────────────────────────────────────

def plan_entry_recipe(recipe: dict, entry: dict | None) -> dict:
    """Recette à cuisiner pour une entrée du planning : version modifiée par le
    membre (variant « perso » + edits), version vegan (variant « vegan ») ou
    recette d'origine. Liste de courses, coût, bilan et batch cooking."""
    entry = entry if isinstance(entry, dict) else {}
    variant = entry.get("variant")
    if variant == "perso" and isinstance(entry.get("edits"), dict):
        try:
            return custom_recipe(recipe, entry["edits"])
        except EditError as e:
            logger.info("planning : version modifiée ignorée pour %s (%s)", recipe.get("id"), e)
    elif variant == "vegan" and not (recipe.get("diet_flags") or {}).get("vegan"):
        from backend.engine.rule_engine.variants import vegan_variant
        v = vegan_variant(recipe)
        if v.get("source") in ("generated", "partial"):
            return v["recipe"]
    return recipe


def plan_entry_nutrition(recipe: dict | None, entry: dict | None, graph: dict) -> dict | None:
    """Nutrition par portion d'une entrée du planning (format du graphe)."""
    rid = str((entry or {}).get("id") or "")
    if recipe is None:
        return graph.get(rid)
    cooked = plan_entry_recipe(recipe, entry)
    if cooked is recipe:
        return graph.get(rid)
    return custom_nutrition(recipe, cooked)[1]
