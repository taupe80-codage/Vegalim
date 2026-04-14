"""
engine/parser.py
Normalise les dicts bruts produits par collector.py -> RecipeCDC v4.
"""

from __future__ import annotations
import re
import sys
import os
import unicodedata
import hashlib
import logging
from pathlib import Path
from typing import Optional

# Fix chemin Windows
_here = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_here))

from config.schema import (
    RecipeCDC, IngredientEntry, TimingEntry, NutritionEntry,
    INGREDIENT_CANON, UNIT_CONVERSIONS, ALLERGEN_MAP,
    DISH_TYPE_KEYWORDS, CUISINE_KEYWORDS,
)

NON_VEGAN_ING = {
    "milk","cream","butter","cheese","yogurt","parmesan","mozzarella",
    "ricotta","mascarpone","feta","halloumi","ghee","cheddar","goat_cheese",
    "cream_cheese","sour_cream","egg","honey","fish","salmon","tuna",
    "cod","sardine","anchovy","shrimp","prawn","lobster","crab","gelatin",
    "lard","fish_sauce","worcestershire_sauce",
}
NON_VEGETARIAN_ING = NON_VEGAN_ING | {
    "beef","pork","lamb","veal","chicken","turkey","duck","rabbit","venison",
    "bacon","ham","prosciutto","chorizo","salami","pepperoni","meat","sausage",
}
GLUTEN_ING = {
    "flour","wheat","rye","barley","oat","spelt","semolina","bread",
    "pasta","couscous","bulgur","seitan","breadcrumbs","pita","soy_sauce",
}

log = logging.getLogger(__name__)


def _slugify(text: str, max_len: int = 48) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s-]+", "_", text)
    return text[:max_len]


def _make_id(title: str, source: str, raw_id: str) -> str:
    slug = _slugify(title)
    suffix = hashlib.md5(f"{source}:{raw_id}".encode()).hexdigest()[:6]
    return f"{slug}_{suffix}"


def _parse_quantity(measure_str: str) -> tuple:
    s = measure_str.strip().lower()
    if not s:
        return None, ""

    frac_pat = re.compile(r"^(\d+)\s+(\d+)/(\d+)")
    m = frac_pat.match(s)
    if m:
        qty = int(m.group(1)) + int(m.group(2)) / int(m.group(3))
        s = s[m.end():].strip()
    else:
        m = re.match(r"^(\d+)/(\d+)", s)
        if m:
            qty = int(m.group(1)) / int(m.group(2))
            s = s[m.end():].strip()
        else:
            m = re.match(r"^([\d.,]+)", s)
            if m:
                qty = float(m.group(1).replace(",", "."))
                s = s[m.end():].strip()
            else:
                qty = None

    unit_raw = s.split()[0] if s else ""
    for known_unit, (factor, normalized_unit) in UNIT_CONVERSIONS.items():
        if unit_raw == known_unit or s.startswith(known_unit):
            if qty is not None:
                qty = round(qty * factor, 2)
            return qty, normalized_unit

    return qty, unit_raw


def _canonicalize_ingredient(raw: str) -> str:
    raw = raw.lower().strip()
    if raw in INGREDIENT_CANON:
        return INGREDIENT_CANON[raw]
    for alias, canon in INGREDIENT_CANON.items():
        if raw.startswith(alias) or alias in raw:
            return canon
    return re.sub(r"\s+", "_", re.sub(r"[^\w\s]", "", raw))


def _split_instructions(raw: str) -> list:
    if not raw:
        return []
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")
    raw = re.sub(r"\n{3,}", "\n\n", raw)

    numbered = re.split(r"\n?\s*(?:step\s*)?(\d+)[.)]\s+", raw, flags=re.I)
    if len(numbered) > 3:
        steps = [s.strip() for s in numbered if s.strip() and not s.strip().isdigit()]
        steps = [s for s in steps if len(s) > 15]
        if steps:
            return steps

    paras = [p.strip() for p in raw.split("\n\n") if p.strip()]
    if len(paras) >= 3:
        return paras

    lines = [l.strip() for l in raw.split("\n") if l.strip() and len(l.strip()) > 10]
    if len(lines) >= 2:
        return lines

    sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z])", raw.strip())
    return [s.strip() for s in sentences if len(s.strip()) > 10]


def _infer_dish_type(title: str, instructions: str) -> str:
    combined = (title + " " + instructions).lower()
    for dish_type, keywords in DISH_TYPE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return dish_type
    return "main"


def _infer_cuisine(title: str, area: str, instructions: str) -> str:
    if area:
        area_lower = area.lower()
        for cuisine, keywords in CUISINE_KEYWORDS.items():
            if any(kw in area_lower for kw in keywords):
                return cuisine
    combined = (title + " " + instructions).lower()
    for cuisine, keywords in CUISINE_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            return cuisine
    return ""


def _infer_timing(instructions: list) -> TimingEntry:
    text = " ".join(instructions).lower()
    cook_min = 0
    for pat in [
        r"(\d+)\s*[-]\s*(\d+)\s*(?:min|minute)",
        r"(\d+)\s*(?:min|minute)",
        r"(\d+)\s*(?:hour|heure)",
    ]:
        matches = re.findall(pat, text)
        for m in matches:
            if isinstance(m, tuple):
                vals = [int(v) for v in m if v]
                cook_min += sum(vals) // len(vals) if vals else 0
            else:
                val = int(m)
                if "hour" in pat or "heure" in pat:
                    val *= 60
                cook_min += val
        if cook_min:
            break
    cook_min = min(cook_min, 480)
    prep_min = max(5, len(instructions) * 3)
    return TimingEntry(
        prep_active_min=prep_min,
        prep_passive_min=0,
        cook_min=cook_min,
        total_min=prep_min + cook_min,
    )


def _compute_diet_flags(canon_ingredients: list) -> tuple:
    ing_set = set(canon_ingredients)
    is_vegetarian = not bool(ing_set & NON_VEGETARIAN_ING)
    is_vegan      = is_vegetarian and not bool(ing_set & NON_VEGAN_ING)
    is_gluten_free = not bool(ing_set & GLUTEN_ING)
    is_lactose_free = not bool(ing_set & {
        "milk","cream","butter","cheese","yogurt","parmesan","mozzarella",
        "ricotta","mascarpone","feta","halloumi","ghee","cheddar",
        "goat_cheese","cream_cheese","sour_cream","condensed_milk",
    })
    is_nut_free = not bool(ing_set & {
        "walnut","hazelnut","almond","cashew","pistachio","pecan",
        "macadamia","pine_nut","peanut","peanut_butter",
    })
    diet_flags = {
        "vegan": is_vegan, "vegetarian": is_vegetarian,
        "gluten_free": is_gluten_free, "lactose_free": is_lactose_free,
        "nut_free": is_nut_free,
    }
    diet_tags = []
    if is_vegan:       diet_tags.append("vegan")
    if is_vegetarian:  diet_tags.append("vegetarian")
    if is_gluten_free: diet_tags.append("gluten_free")
    detected_allergens = set()
    for ing in ing_set:
        if ing in ALLERGEN_MAP:
            detected_allergens.add(ALLERGEN_MAP[ing])
    return diet_flags, {"diet": diet_tags, "allergens": sorted(detected_allergens)}


def parse_raw(raw: dict) -> Optional[RecipeCDC]:
    source   = raw.get("_source", "unknown")
    title_en = raw.get("title_en", "").strip()
    title_fr = raw.get("title_fr", "").strip()
    if not title_en and not title_fr:
        return None
    title = title_en or title_fr
    recipe_id = _make_id(title, source, raw.get("raw_id", ""))

    ingredients_raw = raw.get("ingredients_raw", [])
    composition = []
    canon_names = []
    for item in ingredients_raw:
        raw_name    = item.get("raw_name", "").strip()
        raw_measure = item.get("raw_measure", "").strip()
        if not raw_name or len(raw_name) < 2:
            continue
        canon = _canonicalize_ingredient(raw_name)
        qty, unit = _parse_quantity(raw_measure)
        canon_names.append(canon)
        composition.append(IngredientEntry(
            ingredient=canon, quantity=qty, unit=unit,
            meta={"role": "", "form": "", "state": "raw", "preparation": ""},
        ))

    if not composition:
        return None

    instructions_raw = raw.get("instructions_raw", "")
    instructions = _split_instructions(instructions_raw)
    if not instructions:
        instructions = ["Preparer les ingredients. Assembler et cuire selon la technique adaptee."]

    area      = raw.get("area", "")
    instr_str = " ".join(instructions)
    dish_type = _infer_dish_type(title, instr_str)
    cuisine   = _infer_cuisine(title, area, instr_str)
    timing    = _infer_timing(instructions)
    diet_flags, tags_computed = _compute_diet_flags(canon_names)

    raw_tags   = raw.get("tags_raw", "") or ""
    extra_tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
    tags = {
        "diet": tags_computed["diet"], "allergens": tags_computed["allergens"],
        "technique": [], "process": [],
    }
    if extra_tags:
        tags["extra"] = extra_tags

    return RecipeCDC(
        id=recipe_id,
        titles={"original": title, "fr": title_fr or title, "en": title_en or title},
        description="",
        origin={"cuisine": cuisine, "country": area.lower(), "region": "", "city": ""},
        servings=4, timing=timing, composition=composition,
        instructions=instructions, tags=tags, diet_flags=diet_flags,
        equipment=[], difficulty_level="medium", dish_type=dish_type,
        nutrition=NutritionEntry(), _source=source, _cluster_id="",
        _quality_score=0.0, _flags=[],
    )


def parse_batch(raw_list: list) -> list:
    results = []
    for raw in raw_list:
        try:
            r = parse_raw(raw)
            if r:
                results.append(r)
        except Exception as e:
            log.warning(f"parse_raw error: {e}")
    log.info(f"parse_batch -> {len(results)}/{len(raw_list)} recettes valides")
    return results