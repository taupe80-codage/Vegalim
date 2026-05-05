"""
gen_variants_data.py
Extrait les données de variantes (avec état, cuisson, etc.) depuis les 3 sources brutes.
Produit variants_data.json : {canonical_bk -> [variant_entries]}
"""
import json, sys
sys.stdout.reconfigure(encoding="utf-8")

# ── Load sources ──────────────────────────────────────────────────────────────
print("Loading sources...")
with open("backend/data/nutrition/raw/ciqual_flat_v3.json", encoding="utf-8") as f: ciqual = json.load(f)
with open("backend/data/nutrition/raw/usda_flat_v2.json",   encoding="utf-8") as f: usda   = json.load(f)
with open("backend/data/nutrition/raw/cnf_full_v10.json",   encoding="utf-8") as f: cnf    = json.load(f)

def _s(v): return v if v and v not in ("null","None") else None

def walk(tree, src_name, depth=0):
    """Recursive walk of variant tree → flat list of entries."""
    entries = []
    for key, node in (tree or {}).items():
        if not isinstance(node, dict): continue
        state = node.get("state") or {}
        proc  = state.get("process") or {}
        ext   = {}
        # Extensions fields (v3.0+ schema)
        for ef in ("variety","preservation","physical_form","part",
                   "fat_level","fat_pct","maturity","dairy_process","species","cocoa_pct"):
            v = state.get(ef)
            if v is None:
                # Also check extensions sub-dict
                v = (state.get("extensions") or {}).get(ef)
            if v is not None:
                ext[ef] = v

        entry = {
            "k":     key,
            "depth": depth,
            "type":  node.get("type","?"),
            "dim":   node.get("dimension",""),
            "src":   src_name,
            "sid":   _s(node.get("source_id","")),
            "label": _s(node.get("source_label","")),
            "l1":    _s(proc.get("level1","")),
            "l2":    _s(proc.get("level2","")),
            "conf":  proc.get("confidence"),
            "raw_frag": _s(proc.get("raw_label_fragment","")),
        }
        entry.update(ext)

        children = node.get("children") or {}
        if children:
            entry["ch"] = walk(children, src_name, depth+1)

        entries.append(entry)
    return entries

# ── Build canonical → variant list ────────────────────────────────────────────
# Load enhanced taxonomy to get canonical mapping
with open("enhanced_taxonomy.json", encoding="utf-8") as f:
    taxonomy = json.load(f)

# Build bk → canonical map from taxonomy
BK_TO_CANON = {}
for g in taxonomy:
    for e in g["entries"]:
        BK_TO_CANON[e["bk"]] = e.get("canon", e["bk"])

VARIANTS = {}  # canonical → [entries]

def add_variants(src_name, groups):
    for bk, grp in groups.items():
        vtree = grp.get("variants") or {}
        if not vtree: continue
        entries = walk(vtree, src_name, depth=0)
        # Resolve canonical
        canon = BK_TO_CANON.get(bk, bk)
        if canon not in VARIANTS:
            VARIANTS[canon] = {"bk_sources": {}, "tree": {}}
        # Store per-source tree
        VARIANTS[canon]["bk_sources"][bk] = src_name
        if src_name not in VARIANTS[canon]["tree"]:
            VARIANTS[canon]["tree"][src_name] = {}
        VARIANTS[canon]["tree"][src_name][bk] = entries

add_variants("CIQUAL", ciqual.get("groups", {}))
add_variants("USDA",   usda.get("groups", {}))
add_variants("CNF",    cnf.get("groups", {}))

print(f"Canonicals with variants: {len(VARIANTS)}")
leaf_total = 0
for c, data in VARIANTS.items():
    for src, bks in data["tree"].items():
        for bk, entries in bks.items():
            def count_leaves(el):
                n = 0
                for e in el:
                    if e.get("type") == "leaf": n += 1
                    n += count_leaves(e.get("ch", []))
                return n
            leaf_total += count_leaves(entries)
print(f"Total leaf variants: {leaf_total}")

with open("variants_data.json", "w", encoding="utf-8") as f:
    json.dump(VARIANTS, f, ensure_ascii=False, separators=(",",":"))

size = open("variants_data.json").seek(0,2) if False else None
import os
size = os.path.getsize("variants_data.json")
print(f"variants_data.json: {size//1024}KB")
