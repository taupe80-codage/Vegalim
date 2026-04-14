"""
resolver.py — Résolution des synonymes d'ingrédients.
Fusionne : ingredient_synonym_resolver + dictionary_engine (normalize_list)

API :
    resolve(text)         → str   (id canonique ou texte original)
    resolve_list(texts)   → list[str]
    is_known(text)        → bool

Depuis v6 : résolution FR→EN via fr_to_en_mapping avant lookup dict.
"""
from __future__ import annotations
import unicodedata
import re
from functools import lru_cache


def _normalize(text: str) -> str:
    text = text.lower().strip()
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_s = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[\s\-_]+", " ", ascii_s).strip()


@lru_cache(maxsize=1)
def _fr_to_en_map() -> dict[str, str]:
    """Mapping FR→EN normalisé depuis fr_to_en_mapping.json (879 paires)."""
    from backend.core.data_io import load_fr_to_en
    raw = load_fr_to_en()
    return {_normalize(k): v for k, v in raw.items()}


@lru_cache(maxsize=1)
def _synonym_map() -> dict[str, str]:
    """Construit le mapping {synonyme_normalisé → id_canonique}."""
    from backend.db.data_access import get_data
    mapping: dict[str, str] = {}

    for item in get_data.ingredients._ingredients_raw() if hasattr(get_data.ingredients, '_ingredients_raw') else []:
        canonical = item.get("id", "")
        if not canonical:
            continue
        for key in ("name_fr", "name_en", "id"):
            val = item.get(key, "")
            if val:
                mapping[_normalize(val)] = canonical
        for syn in (item.get("synonyms") or []):
            mapping[_normalize(str(syn))] = canonical

    return mapping


def resolve(text: str) -> str:
    """
    Retourne l'id canonique d'un ingrédient.
    Pipeline : normalise → dict canonique → FR→EN → EN lookup → original.
    """
    norm = _normalize(text)
    # 1. Lookup direct (couvre name_fr, name_en, id, synonymes)
    hit = _synonym_map().get(norm)
    if hit:
        return hit
    # 2. Traduction FR→EN puis re-lookup
    en_key = _fr_to_en_map().get(norm)
    if en_key:
        return _synonym_map().get(_normalize(en_key), en_key)
    return text


def resolve_list(texts: list[str]) -> list[str]:
    """Résout une liste de tokens ingrédients vers leurs ids canoniques."""
    return [resolve(t) for t in texts]


def is_known(text: str) -> bool:
    """Retourne True si le texte correspond à un ingrédient connu."""
    norm = _normalize(text)
    return norm in _synonym_map() or norm in _fr_to_en_map()


def normalize_list(tokens: list[str]) -> list[str]:
    """Alias de resolve_list — compat dictionary_engine.normalize_list."""
    return resolve_list(tokens)
