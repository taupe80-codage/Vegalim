"""
variants.py — Variantes vegan d'une recette.
Fusionne : vegan_variant_engine

API :
    vegan_variant(recipe) → dict  {recipe, substitutions, unresolved, source}
"""
from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)

VEGAN_SUBS: dict[str, str | None] = {
    "oeuf": "tofu", "oeufs": "tofu", "lait": "lait_coco",
    "beurre": "olive_oil", "butter": "olive_oil", "ghee": "coconut_oil",
    "creme": "lait_coco", "creme_fraiche": "tofu_soyeux",
    "fromage_blanc": "tofu_soyeux", "yogurt": "tofu_soyeux", "yaourt": "tofu_soyeux",
    "feta": "tofu_feta", "mozzarella": "mozzarella_vegane",
    "cheese": "tofu_soyeux", "fromage": "tofu_soyeux",
    "parmesan": "levure_maltee", "ricotta": "noix_de_cajou",
    "cheddar": "cheddar_vegane", "gruyere": "levure_maltee",
    "paneer": "tofu", "kashk": "tofu_soyeux",
    "miel": "sirop_agave", "honey": "sirop_agave",
    "mayonnaise": "mayonnaise_vegan",
}

# Identifiants CIQUAL des recettes → substitut vegan présent dans les données.
# Les clés courtes ci-dessus ('butter') ne correspondaient à aucun id réel
# ('butter_sup80pct') : la variante ne remplaçait rien mais se déclarait vegan.
# Chaque substitut est vegan selon le dictionnaire ou les diet_flags de sa
# sous-recette (vérifié par test). Quantités reprises telles quelles.
# Sans substitut fiable (signalés dans « unresolved ») : pâtes brisée et à
# empanada au beurre, nouilles et spätzle aux œufs, roux de curry japonais,
# crêpe de sarrasin, biscuits à la cuillère, glace vanille, lait en poudre.
VEGAN_SUBS_CIQUAL: dict[str, str] = {
    # Beurre, ghee
    "butter_sup80pct": "vegan_butter", "butter_salted": "vegan_butter", "butter": "vegan_butter",
    "base_ghee_ec9064": "coconut_oil_plant",
    # Œufs
    "egg_raw": "silken_tofu_pre_packaged", "egg_yolk_raw": "silken_tofu_pre_packaged",
    "egg_hard_boiled": "tofu_plain_pre_packaged", "egg_white_raw": "aquafaba",
    # Lait, crème, yaourt
    "milk_liquid_uht_3_5pct": "soybean_milk_unsweetened_plant",
    "milk_liquid_pasteurized_3_5pct": "soybean_milk_unsweetened_plant",
    "buttermilk_1pct": "soybean_milk_unsweetened_plant",
    "condensed_milk_concentrated_sweetened_canned_whole": "coconut_milk_plant",
    "condensed_milk_concentrated_unsweetened_whole": "coconut_milk_plant",
    "cream": "base_soy_cream_4dc027", "cream_heavy": "base_soy_cream_4dc027",
    "cream_heavy_refrigerated_18pct": "base_soy_cream_4dc027",
    "cream_heavy_refrigerated_30pct": "base_soy_cream_4dc027",
    "cream_liquid_uht": "base_soy_cream_4dc027",
    "base_creme_fraiche_b536c1": "base_soy_cream_4dc027",
    "sour_cream_fermented_18pct": "soybean_yogurt_plain_plant",
    "cream_sour_18pct": "soybean_yogurt_plain_plant",
    "cream_sour_fermented": "soybean_yogurt_plain_plant",
    "yogurt_plain_3pct": "soybean_yogurt_plain_plant",
    "yogurt_fermented_plain": "soybean_yogurt_plain_plant",
    "yogurt_greek_plain_4pct": "soybean_yogurt_plain_plant",
    "yogurt_greek_style_plain_8pct": "soybean_yogurt_plain_plant",
    "kefir_fermented": "soybean_yogurt_plain_plant",
    "base_kashk_fd3ac6": "soybean_yogurt_plain_plant",
    "fromage_blanc_plain_2_5pct_cow": "silken_tofu_pre_packaged",
    "cottage_cheese_4pct_cow": "silken_tofu_pre_packaged",
    # Fromages
    "parmesan_grated_dried_cow": "nutritional_yeast_flakes",
    "pecorino_sheep": "nutritional_yeast_flakes",
    "cotija_block_cow": "nutritional_yeast_flakes",
    "feta": "tofu_plain_pre_packaged", "feta_cow": "tofu_plain_pre_packaged",
    "queso_fresco_block_cow": "tofu_plain_pre_packaged",
    "base_paneer_04e1db": "tofu_plain_pre_packaged",
    "base_halloumi_293d5e": "tofu_plain_pre_packaged",
    "base_fromage_en_grain_a00941": "tofu_plain_pre_packaged",
    "cows_milk_mozzarella_cow": "base_mozzarella_vegane_fca8c8",
    "cheddar": "base_vegan_cheddar_024998", "cheddar_cow": "base_vegan_cheddar_024998",
    "gruyere": "base_vegan_cheddar_024998", "comte_cow": "base_vegan_cheddar_024998",
    "emmental_de_savoie_cow": "base_vegan_cheddar_024998",
    "tomme_de_savoie_cow": "base_vegan_cheddar_024998",
    "gouda_cow": "base_vegan_cheddar_024998", "provolone_paste_cow": "base_vegan_cheddar_024998",
    "queso_chihuahua_whole_cow": "base_vegan_cheddar_024998",
    "camembert_pasteurized_cow": "base_vegan_cheddar_024998",
    "roquefort": "base_vegan_cheddar_024998",
    "ricotta": "base_cashew_ricotta_5c62e9", "ricotta_whole_cow": "base_cashew_ricotta_5c62e9",
    "base_salted_ricotta_1ecd1c": "base_cashew_ricotta_5c62e9",
    "mascarpone": "base_cashew_ricotta_5c62e9",
    "cream_cheese_block_whole_cow": "base_cashew_ricotta_5c62e9",
    "goat_cheese_fresh": "base_cashew_ricotta_5c62e9",
    "goat_cheese_log": "base_cashew_ricotta_5c62e9",
    # Divers
    "honey": "agave_syrup",
    "base_mayonnaise_0d3e4e": "base_vegan_mayonnaise_b68322",
    "base_bechamel_7db18f": "base_bechamel_vegane_7a210c",
    "base_pesto_905db7": "base_pistou_43e29a",
    "base_wonton_wrapper_7bfeb5": "base_gyoza_wrapper_0dba00",
    "puff_pastry_all_butter_raw_paste_pre_packaged": "puff_pastry_vegetable_fat_raw_paste_plant",
    "egg_pasta_raw_dried": "pasta_raw_dried",
}


def _is_vegan_id(iid: str) -> bool | None:
    """True / False selon le dictionnaire d'ingrédients ou les diet_flags de la
    sous-recette ; None si l'id est inconnu (anciens ids courts)."""
    from backend.db.culinary_repositories import IngredientRepository, _recipes_index
    item = IngredientRepository().get_by_name(iid)
    dp = (item or {}).get("diet_profile")
    if dp and dp.get("vegan") is not None:
        return bool(dp["vegan"])
    sub = _recipes_index().get(iid)
    if sub is not None:
        flag = (sub.get("diet_flags") or {}).get("vegan")
        return None if flag is None else bool(flag)
    return None


def _display_name(iid: str) -> str:
    """Nom français d'un ingrédient ou d'une sous-recette, pour l'affichage."""
    from backend.core.data_io import load_ingredients_dict
    from backend.db.culinary_repositories import _recipes_index
    from backend.services.ingredient_catalog import full_name_fr
    entry = load_ingredients_dict().get(iid)
    name = full_name_fr(entry, iid) if entry and entry.get("canonical_name_fr") else None
    if not name:
        name = ((_recipes_index().get(iid) or {}).get("titles") or {}).get("fr")
    return name or iid.replace("/", " ").replace("_", " ")


def _item_id(item) -> str:
    if isinstance(item, dict):
        return str(item.get("ingredient") or item.get("ingredient_id") or "")
    return str(item)




def _short(name: str) -> str:
    """« beurre végétal (vegan) » → « beurre végétal », en minuscules."""
    return re.sub(r"\s*\([^)]*\)", "", name or "").strip().lower()


def _forms(name: str) -> list[str]:
    """Formes de l'ingrédient d'origine dans le texte d'une étape : nom complet,
    pluriels, nom de tête (« crème épaisse » → « crème »)."""
    base = _short(name)
    if not base:
        return []
    forms = {base}
    m = re.match(r"(\S+)( d'| de )(.+)", base)
    if m:                                       # jaune d'œuf → jaunes d'œufs, jaune d'œufs…
        head, link, tail = m.groups()
        forms |= {f"{head}s{link}{tail}", f"{head}s{link}{tail}s", f"{head}{link}{tail}s"}
    elif len(base.split()) > 1 and len(base.split()[0]) > 3:
        forms.add(base.split()[0])              # crème épaisse → crème
    for f in list(forms):
        if not f.endswith(("s", "x")):
            forms.add(f + ("x" if f.endswith("eau") else "s"))
    return sorted(forms, key=len, reverse=True)


# Ingrédients comptés à la pièce : remplacés seulement dans une quantité en grammes,
# et jamais quand la pièce elle-même est cuite, cassée ou séparée (« séparer 3 tofu
# soyeux », « pocher des tofu soyeux » n'ont pas de sens).
_COUNTED = re.compile(r"(?:^|\s)(œufs?|jaunes? d'œufs?|blancs? d'œufs?)$")
_PIECE_USE = re.compile(r"pocher|poch[ée]|frire|au plat|écaler|casser|séparer|mollet|\bdurs?\b|coque", re.I)
_VOWELS = set("aeiouàâéèêëîïôûœ")      # pas « y » (de yaourt) ni « h » (de haricots)
# genre du premier mot des substituts, pour accorder l'article qui les précède
_GENDER = {"tofu": "m", "yaourt": "m", "beurre": "m", "lait": "m", "sirop": "m", "jus": "m",
           "cheddar": "m", "fromage": "m",
           "crème": "f", "ricotta": "f", "mozzarella": "f", "mayonnaise": "f", "huile": "f",
           "levure": "f", "sauce": "f", "béchamel": "f"}


def _rewrite_steps(steps: list, applied: list[dict]) -> tuple[list, int]:
    """Étapes avec les ingrédients de substitution. Prudent : mots entiers, un seul
    passage (un substitut n'est jamais remplacé à son tour), « 3 œufs (150 g) » →
    « 150 g de tofu soyeux », élision « de / d' » rétablie autour des seuls
    substituts ; les œufs ne sont remplacés que dans une quantité en grammes.
    Renvoie (étapes, nb modifiées)."""
    mapping: dict[str, str] = {}
    for a in applied:
        sub = _short(a.get("substitute_name") or "")
        if not sub:
            continue
        for f in _forms(a.get("original_name") or ""):
            mapping.setdefault(f, sub)
    if not mapping:
        return steps, 0
    counted_forms = [f for f in mapping if _COUNTED.search(f)]
    mass_forms = [f for f in mapping if f not in counted_forms]

    def alt(fs):
        return "|".join(re.escape(f) for f in sorted(fs, key=len, reverse=True))

    rules = []
    if counted_forms:
        c = alt(counted_forms)
        # « 3 œufs (150 g) », « 2 œufs battus (110 g) » ; « 220 g d'œufs battus »
        rules.append((re.compile(rf"\b\d+ ({c})(?: [a-zéèêû]+)? \((\d+(?:[,.]\d+)?) ?(g|ml)\)", re.I),
                      lambda m: f"{m.group(2)} {m.group(3)} de {mapping[m.group(1).lower()]}", True))
        rules.append((re.compile(rf"\b(\d+(?:[,.]\d+)?) ?(g|ml) (?:de |d')({c})(?: (?:battus?|entiers?|crus?))?(?!\w)", re.I),
                      lambda m: f"{m.group(1)} {m.group(2)} de {mapping[m.group(3).lower()]}", True))
    if mass_forms:
        rules.append((re.compile(rf"(?<![\w'’])({alt(mass_forms)})(?!\w)", re.I),
                      lambda m: mapping[m.group(1).lower()], False))
    out, changed = [], 0
    for step in steps:
        if not isinstance(step, str):
            out.append(step)
            continue
        new = step
        for pattern, repl, counted in rules:
            if counted and _PIECE_USE.search(step):
                continue
            new = pattern.sub(repl, new)
        if new != step:
            # élision autour des seuls substituts insérés : le reste de l'étape n'est
            # pas touché (« de haricots »)
            for sub in set(mapping.values()):
                esc = re.escape(sub)
                if sub[:1] in _VOWELS:
                    new = re.sub(rf"\b([Dd])e {esc}", lambda mm, s=sub: f"{mm.group(1)}'{s}", new)
                else:
                    new = re.sub(rf"\b([Dd])'{esc}", lambda mm, s=sub: f"{mm.group(1)}e {s}", new)
                # « parmesan râpé » → « levure nutritionnelle en paillettes » (sans « râpé »)
                new = re.sub(rf"({esc}) râpée?s?\b", lambda mm: mm.group(1), new)
                # article accordé au substitut : « de la crème » → « du yaourt de soja »
                gender = _GENDER.get(sub.split()[0])
                if gender == "m":
                    new = re.sub(rf"\b([Dd])e la {esc}", lambda mm, s=sub: f"{mm.group(1)}u {s}", new)
                    new = re.sub(rf"\b([Àà]) la {esc}", lambda mm, s=sub: f"au {s}", new)
                    new = re.sub(rf"\b([Ll])a {esc}", lambda mm, s=sub: f"{mm.group(1)}e {s}", new)
                elif gender == "f":
                    new = re.sub(rf"\b([Dd])u {esc}", lambda mm, s=sub: f"{mm.group(1)}e la {s}", new)
                    new = re.sub(rf"\b([Aa])u {esc}", lambda mm, s=sub: f"{'À' if mm.group(1) == 'A' else 'à'} la {s}", new)
                    new = re.sub(rf"\b([Ll])e {esc}", lambda mm, s=sub: f"{mm.group(1)}a {s}", new)
            changed += 1
        out.append(new)
    return out, changed


def vegan_variant(recipe: dict) -> dict:
    """
    Retourne la version vegan d'une recette, générée par substitution.

    L'index pré-calculé (vegan_variants_index.json) n'est plus consulté : ses
    variantes pointent vers des recettes inexistantes et ses substitutions vers
    d'anciens ids courts — la recette originale était renvoyée inchangée.

    Returns:
        {recipe, substitutions: [{original, substitute, original_name,
         substitute_name}], unresolved: [{id, name}], source}
        source : "generated" (tout est remplacé), "partial" (des ingrédients
        non vegan restent : la variante n'est pas étiquetée vegan) ou
        "already_vegan".
    """
    import copy
    r = copy.deepcopy(recipe)
    applied = []
    unresolved = []

    has_composition = "composition" in r
    target_list = r.get("composition", r.get("ingredients", []))
    new_ings = []

    for item in target_list:
        iid = _item_id(item)
        key = iid.lower()
        sub = VEGAN_SUBS_CIQUAL.get(key) or VEGAN_SUBS.get(key)
        if sub:
            applied.append({"original": iid, "substitute": sub,
                            "original_name": _display_name(iid),
                            "substitute_name": _display_name(sub)})
            if not isinstance(item, dict):
                item = sub
            elif "ingredient" in item:
                item = {**item, "ingredient": sub}
            else:
                item = {**item, "ingredient_id": sub}
        elif iid and _is_vegan_id(key) is False:
            unresolved.append({"id": iid, "name": _display_name(iid)})
        new_ings.append(item)

    if has_composition:
        r["composition"] = new_ings
    else:
        r["ingredients"] = new_ings

    # Noms affichés par la fiche recette (comme enrich_one) : sans eux les
    # substituts s'affichaient sous leur id brut.
    from backend.db.culinary_repositories import _recipes_index
    r["ingredients_meta"] = {
        _item_id(i): {"name_fr": _display_name(_item_id(i)),
                      **({"recipe_id": _item_id(i)} if _item_id(i) in _recipes_index() else {})}
        for i in new_ings if isinstance(i, dict) and _item_id(i)
    }

    # Étapes réécrites avec les substituts (« 250 g de paneer » → « 250 g de tofu »)
    if applied and isinstance(r.get("instructions"), list):
        r["instructions"], r["_steps_rewritten"] = _rewrite_steps(r["instructions"], applied)

    # Régimes et allergènes recalculés sur la nouvelle composition : la variante
    # gardait ceux de l'original (« œufs », « lait » affichés après substitution)
    # et ignorait ceux des substituts — tofu soyeux, lait et crème de soja (soja),
    # ricotta de cajou (fruits à coque) — un risque pour les personnes allergiques.
    from backend.engine.rule_engine.diet import allergen_tags, compute_diet_flags
    core = [c for c in r.get("composition") or []
            if isinstance(c, dict) and (c.get("meta") or {}).get("role") != "serving_suggestion"]
    computed = compute_diet_flags({**r, "composition": core})
    allergens = allergen_tags(r)
    flags = dict(r.get("diet_flags") or {})
    for f in ("vegetarian", "gluten_free", "lactose_free", "nut_free"):
        if f in computed:
            flags[f] = bool(computed[f])
    excludes = {"gluten_free": {"gluten"}, "lactose_free": {"milk", "lactose"},
                "nut_free": {"tree_nuts", "peanuts"}}
    for f, tags_ in excludes.items():
        if tags_ & set(allergens):
            flags[f] = False
    flags["vegan"] = False
    r["diet_flags"] = flags
    r.setdefault("tags", {})
    if isinstance(r["tags"], dict):
        r["tags"]["allergens"] = allergens
        r["tags"]["diet"] = [d for d in (r["tags"].get("diet") or []) if d != "vegan"
                             and not (d in excludes and flags.get(d) is False)]
    r["diet_flags_enriched"] = {"egg_free": "eggs" not in allergens,
                                "dairy_free": "milk" not in allergens,
                                "soy_free": "soy" not in allergens}

    if unresolved:
        source = "partial"
    else:
        source = "generated" if applied else "already_vegan"
        r["_vegan_variant"] = True
        if "tags" in r and isinstance(r["tags"], dict):
            if "diet" not in r["tags"]: r["tags"]["diet"] = []
            if "vegan" not in r["tags"]["diet"]: r["tags"]["diet"].append("vegan")
            if "vegetarien" not in r["tags"]["diet"]: r["tags"]["diet"].append("vegetarien")
        if r.get("diet_flags"):
            r["diet_flags"] = {**r["diet_flags"], "vegan": True, "vegetarian": True}

    return {
        "recipe":        r,
        "substitutions": applied,
        "unresolved":    unresolved,
        "source":        source,
    }
