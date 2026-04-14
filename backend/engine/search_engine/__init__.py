"""
search_engine/ — Moteur de recherche recettes.

Fusionne 6 engines :
    search_engine_v3 + search_orchestrator + embedding_engine
    similarity_engine + ingredient_synonym_resolver + dictionary_engine

API PUBLIQUE :
    from backend.engine.search_engine import search, find_similar, resolve, resolve_list
"""
from backend.engine.search_engine.core     import search
from backend.engine.search_engine.similar  import find_similar
from backend.engine.search_engine.resolver import resolve, resolve_list

__all__ = ["search", "find_similar", "resolve", "resolve_list"]
