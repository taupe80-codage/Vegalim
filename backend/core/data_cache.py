"""
data_cache.py — Cache de fonctions de chargement invalidé quand les données changent.

Problème : une trentaine de loaders (repositories, scoring, carbone, résolveur…)
étaient décorés @lru_cache(maxsize=1) et ne se rechargeaient jamais. Après un
rebuild (scripts, /admin/*, correction de prix), l'API servait un mélange de
données anciennes et nouvelles jusqu'au redémarrage — différemment dans chaque
worker uvicorn.

@data_cached remplace @lru_cache(maxsize=1) pour les fonctions SANS argument :
le cache est vidé dès qu'un fichier JSON sous backend/data/ (hors dossiers
d'archives/sauvegardes) change de date de modification ou de taille. La
vérification (os.scandir de quelques dossiers) est faite au plus une fois par
CHECK_INTERVAL_S secondes, tous caches confondus.

Chaque worker vérifie de son côté : plus besoin de redémarrer après un rebuild.
"""
from __future__ import annotations

import functools
import os
import threading
import time
from pathlib import Path

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"

WATCHED_DIRS = (
    "recipes", "ingredients", "nutrition/processed", "nutrition/reference",
    "graphs", "indexes", "config", "modules",
)
CHECK_INTERVAL_S = 1.0

_lock = threading.Lock()
_state = {"checked_at": 0.0, "signature": None, "generation": 0}


def _signature() -> tuple:
    entries = []
    for rel in WATCHED_DIRS:
        try:
            with os.scandir(DATA_ROOT / rel) as it:
                for e in it:
                    if e.is_file() and e.name.endswith(".json"):
                        st = e.stat()
                        entries.append((rel, e.name, st.st_mtime_ns, st.st_size))
        except OSError:
            continue
    return tuple(sorted(entries))


def data_generation() -> int:
    """Numéro incrémenté à chaque changement détecté des fichiers de données."""
    now = time.monotonic()
    if now - _state["checked_at"] < CHECK_INTERVAL_S:
        return _state["generation"]
    with _lock:
        if now - _state["checked_at"] >= CHECK_INTERVAL_S:
            sig = _signature()
            if _state["signature"] is not None and sig != _state["signature"]:
                _state["generation"] += 1
            _state["signature"] = sig
            _state["checked_at"] = now
    return _state["generation"]


def data_cached(fn):
    """@lru_cache(maxsize=1) invalidé quand les fichiers de données changent."""
    cached = functools.lru_cache(maxsize=1)(fn)
    seen = {"generation": None}

    @functools.wraps(fn)
    def wrapper():
        gen = data_generation()
        if gen != seen["generation"]:
            cached.cache_clear()
            seen["generation"] = gen
        return cached()

    wrapper.cache_clear = cached.cache_clear
    wrapper.cache_info = cached.cache_info
    return wrapper
