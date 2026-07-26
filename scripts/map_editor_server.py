#!/usr/bin/env python3
"""
map_editor_server.py — Serveur HTTP local pour l'éditeur de map
================================================================
Lance un serveur sur http://localhost:7432
Ouvre automatiquement le navigateur.

Usage :
    python scripts/map_editor_server.py
"""
import json
import os
import re
import sys
import threading
import webbrowser
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

PORT = 7432
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MAP_PATH     = PROJECT_ROOT / "backend" / "data" / "recipes" / "ingredient_map_v2.json"
NUTR_PATH    = PROJECT_ROOT / "backend" / "data" / "nutrition" / "processed" / "nutrition_v2.json"
REC_PATH     = PROJECT_ROOT / "backend" / "data" / "recipes" / "recipes.json"
HTML_PATH    = Path(__file__).parent / "map_editor.html"

# ── Data loading ──────────────────────────────────────────────────────────────

def load_map():
    return json.load(open(MAP_PATH, encoding="utf-8"))

@lru_cache(maxsize=1)
def load_nutr():
    print("Chargement nutrition_v2...")
    raw = json.load(open(NUTR_PATH, encoding="utf-8"))
    return raw.get("ingredients", {})

@lru_cache(maxsize=1)
def load_ing_freq():
    print("Chargement recettes...")
    recipes = json.load(open(REC_PATH, encoding="utf-8"))["recipes"]
    freq = Counter()
    for rec in recipes:
        for comp in rec.get("composition", []):
            raw = comp.get("ingredient", "")
            if raw:
                freq[raw] += 1
                base = raw.split("/")[0]
                if base != raw:
                    freq[base] += 1
    return freq

@lru_cache(maxsize=1)
def build_n2_index():
    """Construit l'index plat de nutrition_v2 pour la recherche."""
    ings = load_nutr()
    index = []
    for gid, entry in ings.items():
        tax     = entry.get("taxonomy", {})
        variants = entry.get("variants", {})
        vdata   = next(iter(variants.values()), {}) if variants else {}
        cs      = vdata.get("axes", {}).get("cooking_state", "")
        index.append({
            "gid":     gid,
            "cat1":    tax.get("cat1", ""),
            "cat2":    tax.get("cat2", ""),
            "name_en": tax.get("name_en", ""),
            "name_fr": tax.get("name_fr", ""),
            "cal":     vdata.get("calories_kcal"),
            "prot":    vdata.get("protein_g"),
            "fat":     vdata.get("fat_g"),
            "cooking_state": cs,
            "source":  vdata.get("_source", ""),
        })
    return index

def _norm(s):
    return s.lower().replace("_", " ").replace("/", " ").replace("-", " ")

def search_n2(term, limit=30):
    if not term:
        return []
    t = _norm(term)
    results = []
    for e in build_n2_index():
        exact = t in _norm(e["gid"]) or t in _norm(e["name_en"]) or t in _norm(e["name_fr"])
        score = max(
            SequenceMatcher(None, t, _norm(e["gid"])).ratio(),
            SequenceMatcher(None, t, _norm(e["name_en"])).ratio(),
            SequenceMatcher(None, t, _norm(e["name_fr"])).ratio(),
        )
        if exact:
            score = max(score, 0.85)
        results.append((score, e))
    results.sort(key=lambda x: -x[0])
    return [e for _, e in results[:limit] if _ > 0.35]

def get_categories():
    cats = defaultdict(set)
    for e in build_n2_index():
        cats[e["cat1"]].add(e["cat2"])
    return {k: sorted(v) for k, v in sorted(cats.items())}

def get_missing(limit=200):
    freq = load_ing_freq()
    m    = load_map()
    return [{"id": iid, "count": cnt}
            for iid, cnt in freq.most_common()
            if iid not in m and cnt >= 2][:limit]

def get_map_stats(m):
    counts = Counter(e.get("status", "?") for e in m.values())
    freq   = load_ing_freq()
    missing_count = sum(1 for iid, cnt in freq.items() if iid not in m and cnt >= 2)
    manual_count  = sum(1 for e in m.values() if str(e.get("method", "")).startswith("manual"))
    return {**dict(counts), "missing": missing_count, "total": len(m), "manual_edited": manual_count}

def save_map(m):
    MAP_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")

# ── HTTP Handler ──────────────────────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # silence les logs HTTP

    def _send(self, data, content_type="application/json", status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8") \
               if content_type == "application/json" else data
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", len(body))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html):
        self._send(html.encode("utf-8"), content_type="text/html; charset=utf-8")

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path   = parsed.path
        qs     = parse_qs(parsed.query)

        if path == "/" or path == "/index.html":
            self._send_html(HTML_PATH.read_text(encoding="utf-8"))

        elif path == "/api/map":
            m = load_map()
            freq = load_ing_freq()
            result = {}
            for rid, e in m.items():
                result[rid] = {**e, "_freq": freq.get(rid, 0)}
            self._send(result)

        elif path == "/api/stats":
            m = load_map()
            self._send(get_map_stats(m))

        elif path == "/api/search":
            term = qs.get("q", [""])[0]
            self._send(search_n2(term))

        elif path == "/api/categories":
            self._send(get_categories())

        elif path == "/api/category":
            cat  = qs.get("name", [""])[0]
            sub  = qs.get("sub", [""])[0]
            res  = [e for e in build_n2_index()
                    if e["cat1"] == cat and (not sub or e["cat2"] == sub)]
            res.sort(key=lambda x: (x["cat2"], x["gid"]))
            self._send(res)

        elif path == "/api/missing":
            self._send(get_missing())

        else:
            self._send({"error": "not found"}, status=404)

    def do_POST(self):
        length  = int(self.headers.get("Content-Length", 0))
        body    = json.loads(self.rfile.read(length))
        path    = urlparse(self.path).path

        if path == "/api/assign":
            rid      = body.get("recipe_id", "").strip()
            gid_raw  = body.get("group_id_raw", "").strip()
            gid_cook = body.get("group_id_cooked", "").strip()

            if not rid or not gid_raw:
                self._send({"ok": False, "error": "recipe_id et group_id_raw requis"})
                return

            ings = load_nutr()
            if gid_raw not in ings:
                self._send({"ok": False, "error": f"'{gid_raw}' absent de nutrition_v2"})
                return
            if gid_cook and gid_cook not in ings:
                self._send({"ok": False, "error": f"'{gid_cook}' absent de nutrition_v2"})
                return

            m = load_map()
            if rid not in m:
                m[rid] = {}

            tax   = ings[gid_raw].get("taxonomy", {})
            vdata = next(iter(ings[gid_raw].get("variants", {}).values()), {})

            cv = {"raw": gid_raw, "default": gid_raw}
            if gid_cook:
                cv["boiled"]        = gid_cook
                cv["cooked"]        = gid_cook
                cv["default_cooked"]= gid_cook

            m[rid].update({
                "group_id_v2":      gid_raw,
                "confidence":       1.0,
                "method":           "manual_editor_html",
                "status":           "AUTO_HIGH",
                "canonical_name_en": tax.get("name_en", ""),
                "cat_id":           tax.get("cat1", ""),
                "cooking_variants": cv,
            })
            save_map(m)
            freq = load_ing_freq()
            result = {**m[rid], "_freq": freq.get(rid, 0)}
            self._send({"ok": True, "entry": result, "stats": get_map_stats(m)})

        elif path == "/api/reject":
            rid = body.get("recipe_id", "").strip()
            if not rid:
                self._send({"ok": False, "error": "recipe_id requis"})
                return

            m = load_map()
            if rid not in m:
                m[rid] = {}

            m[rid].update({
                "group_id_v2":      None,
                "confidence":       0.0,
                "method":           "manual_reject_html",
                "status":           "REJECTED",
                "canonical_name_en": "",
                "cat_id":           "",
                "cooking_variants": {},
            })
            save_map(m)
            freq = load_ing_freq()
            result = {**m[rid], "_freq": freq.get(rid, 0)}
            self._send({"ok": True, "entry": result, "stats": get_map_stats(m)})

        elif path == "/api/delete":
            rid = body.get("recipe_id", "").strip()
            m   = load_map()
            if rid in m:
                del m[rid]
                save_map(m)
            self._send({"ok": True, "stats": get_map_stats(m)})

        else:
            self._send({"error": "not found"}, status=404)


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("Préchauffage des index...")
    build_n2_index()
    load_ing_freq()
    print(f"Serveur démarré : http://localhost:{PORT}")
    threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    HTTPServer(("localhost", PORT), Handler).serve_forever()
