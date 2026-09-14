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
import logging
logger = logging.getLogger(__name__)
import unicodedata
import re
from backend.core.data_cache import data_cached


def _normalize(text: str) -> str:
    text = text.lower().strip()
    nfkd = unicodedata.normalize("NFKD", text)
    ascii_s = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"[\s\-_]+", " ", ascii_s).strip()


@data_cached
def _fr_to_en_map() -> dict[str, str]:
    """Mapping FR→EN normalisé depuis fr_to_en_mapping.json (879 paires)."""
    from backend.core.data_io import load_fr_to_en
    raw = load_fr_to_en()
    return {_normalize(k): v for k, v in raw.items()}


@data_cached
def _synonym_map() -> dict[str, str]:
    """Construit le mapping {synonyme_normalisé → id_canonique}."""
    mapping: dict[str, str] = {}
    try:
        # FIX #13 : utilise l'API publique data_io au lieu de la méthode privée
        # get_data.ingredients._ingredients_raw(). Évite les cassures lors des
        # refactors de data_access et garantit un fallback propre si absent.
        from backend.core.data_io import load_ingredients_dict, load_ingredients_alias_index
        ingredients_raw = load_ingredients_dict()
        alias_index = load_ingredients_alias_index()
    except Exception:
        logger.warning("_synonym_map : erreur ignorée (repli)", exc_info=True)
        return mapping

    for canonical, entry in ingredients_raw.items():
        if not isinstance(entry, dict) or not canonical:
            continue
        for key in ("canonical_name_fr", "canonical_name_en"):
            val = entry.get(key, "")
            if val:
                mapping[_normalize(val)] = canonical
        mapping[_normalize(canonical)] = canonical
        for syn in (entry.get("aliases") or []):
            mapping[_normalize(str(syn))] = canonical

    # Anciennes clés (avant fusion/rename par build_dict_v2.py) -> clé actuelle.
    for old_key, current_key in alias_index.items():
        if current_key in ingredients_raw:
            mapping[_normalize(old_key)] = current_key

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
