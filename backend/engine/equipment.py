"""
equipment.py — Matériel nécessaire à une recette.

Le champ `equipment` n'est renseigné que pour 460 plats sur 1 001 (et avec un
vocabulaire libre : « casserole_fond_epais », « bocal_verre_3l »). Le matériel
est donc déduit du texte des étapes, complété par le champ quand il existe —
calculé à la lecture plutôt que recopié dans recipes.json, pour rester juste
quand une étape change (et couvrir les recettes proposées).

Sert au filtre « Sans four / Sans mixeur » (recherche, planning, frigo, « Sur
place ») et à la ligne « Matériel » de la fiche recette.
"""
from __future__ import annotations

import re

# (libellé, motif dans les étapes, valeurs du champ equipment)
_RULES: list[tuple[str, re.Pattern, set[str]]] = [
    ("four", re.compile(r"\b(four|enfourn\w*|pr[ée]chauff\w*|gratiner|gratinez)\b", re.I),
     {"four", "plat_gratin", "moule_tarte", "plaque_four", "plaques_four"}),
    ("mixeur", re.compile(r"\b(mix(er|ez|é|ée|és|ées)|mixeur|blender|robot|mouliner|moulinez)\b", re.I),
     {"mixeur", "mixeur_plongeant", "robot_pâtissier", "blender"}),
    ("poêle", re.compile(r"\bpo[êe]le\b", re.I),
     {"poele", "poele_antiadhesive", "poele_profonde", "grande_poele", "poele_large"}),
    ("casserole", re.compile(r"\b(casserole|faitout|marmite)\b", re.I),
     {"casserole", "casserole_fond_epais"}),
    ("cocotte", re.compile(r"\b(cocotte|tajine|daubi[èe]re)\b", re.I), {"cocotte"}),
    ("wok", re.compile(r"\bwok\b", re.I), {"wok"}),
    ("cuit-vapeur", re.compile(r"\b(vapeur|cuit-vapeur|panier vapeur)\b", re.I), {"vapeur", "couscoussier"}),
    ("friteuse ou bain de friture", re.compile(r"\b(friteuse|bain d'huile|bain de friture|frire dans)\b", re.I),
     {"friteuse"}),
]

_cache: dict[str, tuple[int, list[str]]] = {}


def recipe_equipment(recipe: dict) -> list[str]:
    """Matériel nécessaire, dans l'ordre de _RULES (« four », « mixeur », « poêle »…)."""
    text = " ".join(str(s) for s in (recipe.get("instructions") or []))
    eq = {str(e).lower() for e in (recipe.get("equipment") or [])}
    key = str(recipe.get("id") or "")
    sig = hash((text, tuple(sorted(eq))))
    hit = _cache.get(key)
    if key and hit and hit[0] == sig:
        return hit[1]
    out = [label for label, pat, names in _RULES if pat.search(text) or eq & names]
    if key:
        _cache[key] = (sig, out)
    return out


def needs_oven(recipe: dict) -> bool:
    return "four" in recipe_equipment(recipe)


def needs_blender(recipe: dict) -> bool:
    return "mixeur" in recipe_equipment(recipe)
