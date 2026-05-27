#!/usr/bin/env python3
"""
audit_positions_llm.py — LLM audit of ingredient axes and tree positions.

Uses Groq API (llama-3.3-70b-versatile via openai package) to verify for each IG:
  1. axes_en correctness based on raw source descriptions (CIQUAL/CNF/USDA)
  2. category/subcategory placement correctness
  3. Scientific name (sci_name) if identifiable from sources

Scope: vegetarian IGs only (excludes _dietary_flag=ANIMAL_BASED).
Sources: raw files only — CIQUAL xlsx, CNF csv, USDA json.

Output: scripts/ingredients/llm_audit_results.json (incremental, resumable)

Usage:
  python audit_positions_llm.py                  # run all
  python audit_positions_llm.py --dry-run        # show context, no API call
  python audit_positions_llm.py --limit 20       # process first N IGs only
  python audit_positions_llm.py --batch-size 5   # IGs per API call (default 8)
  python audit_positions_llm.py --model llama-3.1-8b-instant  # faster/cheaper
"""

import argparse
import csv
import itertools
import json
import os
import sys
import time
from pathlib import Path

import openpyxl
from openai import OpenAI

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent.parent
RAW = ROOT / "backend" / "data" / "nutrition" / "raw"
TREE_PATH = ROOT / "backend" / "data" / "ingredients" / "ingredients_tree.json"
AXES_PATH = ROOT / "backend" / "data" / "ingredients" / "axes_schema.json"
OUT_PATH = Path(__file__).parent / "llm_audit_results.json"

DEFAULT_MODEL = "llama-3.1-8b-instant"
DEFAULT_BATCH = 4
DEFAULT_SLEEP = 1.5  # seconds between batches (respecter TPM limit)


# ---------------------------------------------------------------------------
# Source loaders (raw files only)
# ---------------------------------------------------------------------------

def load_ciqual() -> dict:
    """CIQUAL xlsx → {alim_code_str: {nom_fr, nom_sci, grp1, grp2, grp3}}"""
    path = RAW / "Table_Ciqual_2025_FR_2025_11_03.xlsx"
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    result = {}
    first = True
    for row in ws.iter_rows(values_only=True):
        if first:
            first = False
            continue  # skip header
        # col indices (0-based):
        # 0:alim_grp_code  1:alim_ssgrp_code  2:alim_ssssgrp_code
        # 3:alim_grp_nom_fr  4:alim_ssgrp_nom_fr  5:alim_ssssgrp_nom_fr
        # 6:alim_code  7:alim_nom_fr  8:alim_nom_sci  ...
        alim_code = row[6]
        if alim_code is None:
            continue
        result[str(int(alim_code))] = {
            "nom_fr":  str(row[7] or "").strip(),
            "nom_sci": str(row[8] or "").strip() or None,
            "grp1":    str(row[3] or "").strip(),
            "grp2":    str(row[4] or "").strip(),
            "grp3":    str(row[5] or "").strip(),
        }
    wb.close()
    return result


def load_cnf() -> dict:
    """CNF FOOD_NAME.csv + FOOD_GROUP.csv → {food_id_str: {desc_en, desc_fr, sci_name, group_en}}
    File is latin-1 with a UTF-8 BOM on the first byte — strip BOM from first field name.
    """
    groups: dict[str, str] = {}
    with open(RAW / "cnf" / "FOOD_GROUP.csv", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            groups[row["FoodGroupID"]] = row["FoodGroupName"].strip()

    result: dict[str, dict] = {}
    with open(RAW / "cnf" / "FOOD_NAME.csv", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        # Strip UTF-8 BOM from first field name.
        # latin-1 decodes the 3 BOM bytes (0xEF 0xBB 0xBF) as 3 distinct
        # latin-1 characters ('\xef\xbb\xbf'), NOT as the single U+FEFF char.
        # Handle both cases in case the encoding changes upstream.
        if reader.fieldnames:
            fn = reader.fieldnames[0]
            if fn.startswith("\xef\xbb\xbf"):    # latin-1 read: 3 separate chars
                reader.fieldnames[0] = fn[3:]
            elif fn.startswith("\ufeff"):         # utf-8/utf-8-sig read: 1 char
                reader.fieldnames[0] = fn[1:]
        for row in reader:
            sci = row.get("ScientificName", "").strip()
            result[row["FoodID"]] = {
                "desc_en":  row["FoodDescription"].strip(),
                "desc_fr":  row["FoodDescriptionF"].strip(),
                "sci_name": sci or None,
                "group_en": groups.get(row["FoodGroupID"], ""),
            }
    return result


def load_usda() -> dict:
    """USDA json → {fdcId_str: {description, category}}"""
    with open(RAW / "FoodData_Central_foundation_food_json_2025-12-18.json", encoding="utf-8") as f:
        data = json.load(f)
    foods = data.get("FoundationFoods", [])
    return {
        str(item["fdcId"]): {
            "description": item.get("description", "").strip(),
            "category":    item.get("foodCategory", {}).get("description", "").strip(),
        }
        for item in foods
        if "fdcId" in item
    }


# ---------------------------------------------------------------------------
# Tree helpers
# ---------------------------------------------------------------------------

def load_tree() -> dict:
    with open(TREE_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_axes_schema() -> dict:
    with open(AXES_PATH, encoding="utf-8") as f:
        return json.load(f)


def iter_vegetarian_igs(tree: dict):
    """Yield (cat_label, sub_label, ig_dict) for all non-ANIMAL_BASED IGs."""
    for cat in tree["categories"]:
        for sub in cat["subcategories"]:
            for ig in sub["ingredient_groups"]:
                if ig.get("_dietary_flag") != "ANIMAL_BASED":
                    yield cat["label"], sub["label"], ig


def build_location_list(tree: dict) -> list[str]:
    locs = []
    for cat in tree["categories"]:
        for sub in cat["subcategories"]:
            locs.append(f"{cat['label']}/{sub['label']}")
    return locs


def build_axes_summary(schema: dict) -> str:
    lines = []
    for key, val in schema["axes"].items():
        values = list(val["values"].keys())
        lines.append(f"  {key}: [{', '.join(values)}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Context builder
# ---------------------------------------------------------------------------

def build_context(cat_lbl: str, sub_lbl: str, ig: dict,
                  ciqual: dict, cnf: dict, usda: dict,
                  locations: list[str]) -> dict:
    """Minimal per-IG context block — NO valid_axes / NO candidates (hoisted to system prompt)."""
    MAX_NAME = 80   # chars — keeps token cost predictable per source entry
    seen_names: set[str] = set()
    sources = []
    for var in ig.get("variants", []):
        src = var.get("source", "")
        sid = str(var.get("source_id", ""))
        entry: dict | None = None
        if src == "CIQUAL" and sid in ciqual:
            d = ciqual[sid]
            name = d["nom_fr"][:MAX_NAME]
            entry = {"s": "CQ", "n": name}
            if d["nom_sci"]:
                entry["sci"] = d["nom_sci"][:60]
        elif src == "CNF" and sid in cnf:
            d = cnf[sid]
            name = d["desc_en"][:MAX_NAME]
            entry = {"s": "CN", "n": name}
            if d["sci_name"]:
                entry["sci"] = d["sci_name"][:60]
        elif src == "USDA" and sid in usda:
            d = usda[sid]
            name = d["description"][:MAX_NAME]
            entry = {"s": "US", "n": name}
        if entry is not None:
            key = entry["n"].lower()
            if key not in seen_names:   # deduplicate near-identical entries
                seen_names.add(key)
                sources.append(entry)
    sources = sources[:12]  # hard cap: max 12 source entries per IG
    if not sources:
        print(f"  [WARN] {ig['id']} ({ig.get('canonical_name_en', '?')}) has no matching source entries",
              file=sys.stderr)
    # Candidate locations: subcategories of same category (compact, ~5-8 items)
    same_cat_cands = [l for l in locations if l.startswith(f"{cat_lbl}/")]
    return {
        "id":    ig["id"],
        "name":  ig.get("canonical_name_en", ""),
        "loc":   f"{cat_lbl}/{sub_lbl}",
        "cands": same_cat_cands,
        "axes":  ig.get("axes_en", {}),
        "src":   sources,
    }


def build_system_prompt(axes_schema: dict) -> str:
    """Build the system prompt once — valid_axes embedded, locations omitted (~1500 tokens saved/call).
    Candidate locations are sent per-IG in the user message instead."""
    valid_axes = {k: list(v["values"].keys()) for k, v in axes_schema["axes"].items()}
    return (
        "Food science auditor. JSON in → JSON out only.\n"
        'Output: {"results":[{"id":"ing_X","axes_set":{},"axes_remove":[],...' +
        '"position_ok":true,"suggested_location":null,"sci_name":null,' +
        '"confidence":"high","reason":""}]}\n\n' +
        "VALID_AXES (use ONLY these values):\n" +
        json.dumps(valid_axes, ensure_ascii=False) + "\n\n" +
        "Each IG has: loc=current location, cands=candidate locations, "
        "axes=current axes, src=source descriptions.\n"
        "Rules: axes_set=only axes to ADD/CHANGE (values from VALID_AXES only). "
        "axes_remove=axes keys to DELETE. "
        "position_ok=false only if clearly wrong. "
        "suggested_location=one of cands[] or null. "
        "sci_name=binomial or null. "
        "confidence=high/medium/low (apply changes only if high/medium). "
        'reason=1 sentence or "".'
    )

# SYSTEM_PROMPT is now built dynamically via build_system_prompt()
# so that valid_axes and all_locations are embedded once, not repeated per IG.


# ---------------------------------------------------------------------------
# Groq call
# ---------------------------------------------------------------------------

def call_groq(client: OpenAI, batch: list[dict], system_prompt: str,
              model: str) -> list[dict]:
    """Send a batch to Groq, return list of correction dicts keyed by IG id."""
    user_msg = json.dumps(batch, ensure_ascii=False)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.1,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LLM returned invalid JSON: {e}\nRaw (first 300 chars): {raw[:300]}") from e
    # Unwrap {"results": [...]} or handle bare list
    if isinstance(parsed, dict):
        for key in ("results", "items", "data", "ingredient_groups", "corrections"):
            if key in parsed and isinstance(parsed[key], list):
                return parsed[key]
        # Fallback: first list value
        for v in parsed.values():
            if isinstance(v, list):
                return v
        return []
    if isinstance(parsed, list):
        return parsed
    return []


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LLM audit of ingredient axes and positions")
    parser.add_argument("--dry-run",    action="store_true", help="Print context, skip API calls")
    parser.add_argument("--limit",      type=int, default=0,  help="Process only N IGs (0 = all)")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH, dest="batch_size")
    parser.add_argument("--model",      default=DEFAULT_MODEL)
    parser.add_argument("--sleep",      type=float, default=DEFAULT_SLEEP,
                        help="Seconds to sleep between batches")
    args = parser.parse_args()

    # ---- API keys (rotation: GROQ_API_KEY_1, _2, _3 … ou plain GROQ_API_KEY) ----
    # Le .env est toujours lu en priorité (plus complet que les vars système).
    # Les vars système servent de fallback si le .env n'existe pas ou est vide.
    groq_keys: list[str] = []

    def _extract_keys(pairs):
        keys = []
        for k, v in pairs:
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if v and (k == "GROQ_API_KEY" or (k.startswith("GROQ_API_KEY_") and k[13:].isdigit())):
                keys.append(v)
        return keys

    # 1. Fichier .env (prioritaire)
    env_file = ROOT / ".env"
    if env_file.exists():
        pairs = []
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                pairs.append(line.split("=", 1))
        groq_keys = _extract_keys(pairs)

    # 2. Variables d'environnement système (fallback)
    if not groq_keys:
        groq_keys = _extract_keys(os.environ.items())

    if not groq_keys and not args.dry_run:
        print("ERROR: aucune GROQ_API_KEY trouvée dans le .env ou l'environnement", file=sys.stderr)
        sys.exit(1)

    groq_keys = groq_keys or ["dummy"]
    key_cycle = itertools.cycle(groq_keys)
    print(f"Groq keys chargées : {len(groq_keys)} ({'rotation active' if len(groq_keys) > 1 else 'clé unique'})")

    def make_client() -> OpenAI:
        return OpenAI(api_key=next(key_cycle), base_url="https://api.groq.com/openai/v1")

    # ---- Load sources ----
    print("Loading CIQUAL...", end=" ", flush=True)
    ciqual = load_ciqual()
    print(f"{len(ciqual)} entries")

    print("Loading CNF...", end=" ", flush=True)
    cnf = load_cnf()
    print(f"{len(cnf)} entries")

    print("Loading USDA...", end=" ", flush=True)
    usda = load_usda()
    print(f"{len(usda)} entries")

    print("Loading tree and axes schema...")
    tree        = load_tree()
    axes_schema = load_axes_schema()

    locations     = build_location_list(tree)
    system_prompt = build_system_prompt(axes_schema)  # valid_axes only; cands sent per-IG

    # ---- Collect IGs ----
    all_veg = list(iter_vegetarian_igs(tree))
    print(f"Vegetarian IGs: {len(all_veg)} / {sum(len(s['ingredient_groups']) for c in tree['categories'] for s in c['subcategories'])}")

    # ---- Resume support ----
    existing: dict[str, dict] = {}
    if OUT_PATH.exists():
        with open(OUT_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        existing = {r["id"]: r for r in saved.get("results", [])}
        print(f"Resuming: {len(existing)} IGs already processed")

    # ---- Build pending list ----
    pending_raw = [(c, s, ig) for c, s, ig in all_veg if ig["id"] not in existing]
    if args.limit:
        pending_raw = pending_raw[:args.limit]

    pending = [
        build_context(c, s, ig, ciqual, cnf, usda, locations)
        for c, s, ig in pending_raw
    ]
    print(f"Pending: {len(pending)} IGs to process")

    if args.dry_run:
        for ctx in pending[:3]:
            print(json.dumps(ctx, ensure_ascii=False, indent=2))
        print(f"[dry-run] Would send {len(pending)} IGs in {-(-len(pending)//args.batch_size)} batches")
        return

    # ---- Process batches ----
    results: list[dict] = list(existing.values())
    n_batches = -(-len(pending) // args.batch_size)

    for batch_idx in range(0, len(pending), args.batch_size):
        batch = pending[batch_idx:batch_idx + args.batch_size]
        batch_num = batch_idx // args.batch_size + 1
        ids_str = ", ".join(b["id"] for b in batch)
        print(f"[{batch_num}/{n_batches}] {ids_str}", end=" ... ", flush=True)

        try:
            corrections = call_groq(make_client(), batch, system_prompt, args.model)
            # Index by id for safety
            corr_by_id = {c["id"]: c for c in corrections if "id" in c}
            for ctx in batch:
                results.append(corr_by_id.get(ctx["id"], {"id": ctx["id"], "error": "missing_from_response"}))
            n_changes = sum(
                1 for c in corrections
                if c.get("axes_set") or c.get("axes_remove") or not c.get("position_ok", True) or c.get("sci_name")
            )
            print(f"ok ({n_changes} with changes)")
        except Exception as exc:
            err_str = str(exc)
            if "413" in err_str:
                # Recursive split-and-retry: halve until single IG, then truncate sources
                def retry_split(sub: list[dict], depth: int = 0) -> list[dict]:
                    if not sub:
                        return []
                    if len(sub) == 1:
                        # Single IG still too large — hard-truncate its sources to 3
                        trimmed = dict(sub[0])
                        trimmed["src"] = trimmed.get("src", [])[:3]
                        print(f"  [trim] {trimmed['id']} sources capped to 3", flush=True)
                        try:
                            time.sleep(args.sleep)
                            return call_groq(make_client(), [trimmed], system_prompt, args.model)
                        except Exception as e2:
                            print(f"  [skip] {trimmed['id']} still too large: {e2}")
                            return [{"id": trimmed["id"], "error": str(e2)}]
                    half = len(sub) // 2
                    print(f"  {'  '*depth}splitting {len(sub)}→{half}+{len(sub)-half}", flush=True)
                    time.sleep(args.sleep)
                    left  = retry_split(sub[:half],  depth + 1)
                    time.sleep(args.sleep)
                    right = retry_split(sub[half:], depth + 1)
                    return left + right

                print(f"413 (too large) — recursive split...", flush=True)
                sub_corrections = retry_split(batch)
                corr_by_id = {c["id"]: c for c in sub_corrections if "id" in c}
                for ctx in batch:
                    results.append(corr_by_id.get(ctx["id"], {"id": ctx["id"], "error": "missing_from_response"}))
                n_changes = sum(
                    1 for c in sub_corrections
                    if c.get("axes_set") or c.get("axes_remove") or not c.get("position_ok", True) or c.get("sci_name")
                )
                print(f"ok after split ({n_changes} with changes)")
            else:
                print(f"ERROR: {exc}")
                for ctx in batch:
                    results.append({"id": ctx["id"], "error": err_str})

        # Incremental save
        _save(results, args.model)

        if batch_idx + args.batch_size < len(pending):
            time.sleep(args.sleep)

    # ---- Summary ----
    changed = [r for r in results
               if r.get("axes_set") or r.get("axes_remove")
               or not r.get("position_ok", True) or r.get("sci_name")]
    errors  = [r for r in results if r.get("error")]
    print(f"\n{'='*60}")
    print(f"Total processed : {len(results)}")
    print(f"With changes    : {len(changed)}")
    print(f"Errors          : {len(errors)}")
    print(f"Output          : {OUT_PATH}")

    # Breakdown
    axes_changes    = [r for r in results if r.get("axes_set") or r.get("axes_remove")]
    wrong_position  = [r for r in results if not r.get("position_ok", True)]
    with_sci_name   = [r for r in results if r.get("sci_name")]
    print(f"  axes corrections : {len(axes_changes)}")
    print(f"  position issues  : {len(wrong_position)}")
    print(f"  sci_name added   : {len(with_sci_name)}")


def _save(results: list[dict], model: str) -> None:
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {"version": "1.0", "model": model, "total": len(results), "results": results},
            f, ensure_ascii=False, indent=2,
        )


if __name__ == "__main__":
    main()
