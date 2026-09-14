"""
tests/test_data_cache.py — @data_cached : cache vidé quand les données changent.

Régression 2026-09-14 : les loaders @lru_cache ne se rechargeaient jamais —
après un rebuild, l'API mélangeait anciennes et nouvelles données jusqu'au
redémarrage.
"""
from __future__ import annotations

import os

import pytest

from backend.core import data_cache


@pytest.fixture()
def watched_tmp(tmp_path, monkeypatch):
    (tmp_path / "config").mkdir()
    monkeypatch.setattr(data_cache, "DATA_ROOT", tmp_path)
    monkeypatch.setattr(data_cache, "WATCHED_DIRS", ("config",))
    monkeypatch.setattr(data_cache, "CHECK_INTERVAL_S", 0.0)
    monkeypatch.setitem(data_cache._state, "signature", None)
    monkeypatch.setitem(data_cache._state, "checked_at", 0.0)
    return tmp_path / "config"


def test_cache_reutilise_tant_que_rien_ne_change(watched_tmp):
    (watched_tmp / "a.json").write_text("{}", encoding="utf-8")
    calls = []

    @data_cached_fresh
    def loader():
        calls.append(1)
        return len(calls)

    assert loader() == 1
    assert loader() == 1
    assert len(calls) == 1


def test_cache_recharge_apres_modification(watched_tmp):
    f = watched_tmp / "a.json"
    f.write_text("{}", encoding="utf-8")
    calls = []

    @data_cached_fresh
    def loader():
        calls.append(1)
        return len(calls)

    assert loader() == 1
    f.write_text('{"modifié": true}', encoding="utf-8")
    st = f.stat()
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 10_000_000))
    assert loader() == 2


def test_cache_recharge_apres_ajout_de_fichier(watched_tmp):
    (watched_tmp / "a.json").write_text("{}", encoding="utf-8")
    calls = []

    @data_cached_fresh
    def loader():
        calls.append(1)
        return len(calls)

    loader()
    (watched_tmp / "b.json").write_text("{}", encoding="utf-8")
    assert loader() == 2


def test_cache_clear_expose():
    assert callable(getattr(data_cache.data_cached(lambda: 1), "cache_clear", None))


def data_cached_fresh(fn):
    """data_cached avec une génération de référence initialisée (état de test)."""
    data_cache.data_generation()
    return data_cache.data_cached(fn)
