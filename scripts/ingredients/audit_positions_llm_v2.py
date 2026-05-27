#!/usr/bin/env python3
"""
audit_positions_llm_v2.py — LLM audit v2 of ingredient axes and tree positions.

Améliorations vs v1:
  • Modèle : llama-3.3-70b-versatile (bien meilleur raisonnement)
  • Digest sources : construit une seule fois depuis les fichiers bruts → lookup
    JSON compact réutilisé à chaque run (rapide + économe en tokens)
  • Axes multi-valeurs : axes_set accepte string OU liste pour les axes
    qui peuvent légitimement avoir plusieurs valeurs simultanées
  • Nouveaux axes : axes_propose pour des caractéristiques présentes dans les
    sources mais absentes du schéma actuel
  • Suppression précise : axes_remove liste les clés exactes à supprimer
    (jamais en conflit avec axes_set — remplacer = axes_set seulement)
  • Sourçage strict : aucun axe ne peut être posé sans citation explicite
    de la source brute ; reason doit citer le texte exact
  • Enrichissement USDA API (optionnel, --usda-api-key)

Usage:
  # Étape 1 — Construire le digest des sources (une seule fois)
  python audit_positions_llm_v2.py --build-digest

  # Étape 2 — Lancer l'audit
  python audit_positions_llm_v2.py
  python audit_positions_llm_v2.py --dry-run           # aperçu sans appel API
  python audit_positions_llm_v2.py --limit 20          # N premiers IGs seulement
  python audit_positions_llm_v2.py --batch-size 5      # IGs par appel (défaut 5)
  python audit_positions_llm_v2.py --usda-api-key KEY  # enrichissement USDA API
  python audit_positions_llm_v2.py --rebuild-digest    # re-construire le digest
"""

import argparse
import csv
import datetime
import itertools
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional

import openpyxl
from openai import OpenAI

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT        = Path(__file__).parent.parent.parent
RAW         = ROOT / "backend" / "data" / "nutrition" / "raw"
TREE_PATH   = ROOT / "backend" / "data" / "ingredients" / "ingredients_tree.json"
AXES_PATH   = ROOT / "backend" / "data" / "ingredients" / "axes_schema.json"
OUT_PATH    = Path(__file__).parent / "llm_audit_results_v2.json"
DIGEST_PATH = Path(__file__).parent / "source_digest.json"

DEFAULT_MODEL = "llama-3.3-70b-versatile"
DEFAULT_BATCH = 5
DEFAULT_SLEEP = 2.0   # secondes entre batches

# ---------------------------------------------------------------------------
# Source loaders (fichiers bruts)
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
            continue
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
    """CNF FOOD_NAME.csv + FOOD_GROUP.csv → {food_id_str: {desc_en, desc_fr, sci_name, group_en}}"""
    groups: dict[str, str] = {}
    with open(RAW / "cnf" / "FOOD_GROUP.csv", encoding="latin-1") as f:
        for row in csv.DictReader(f):
            groups[row["FoodGroupID"]] = row["FoodGroupName"].strip()

    result: dict[str, dict] = {}
    with open(RAW / "cnf" / "FOOD_NAME.csv", encoding="latin-1") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            fn = reader.fieldnames[0]
            if fn.startswith("\xef\xbb\xbf"):
                reader.fieldnames[0] = fn[3:]
            elif fn.startswith("\ufeff"):
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
    """USDA Foundation Foods json → {fdcId_str: {description, category, input_foods}}
    Extrait aussi inputFoods pour un contexte plus riche sur l'état/traitement.
    """
    path = RAW / "FoodData_Central_foundation_food_json_2025-12-18.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    foods = data.get("FoundationFoods", [])
    result = {}
    for item in foods:
        if "fdcId" not in item:
            continue
        # InputFoods : descriptions des matières premières utilisées
        input_foods = []
        for inp in item.get("inputFoods", [])[:6]:
            desc = (inp.get("foodDescription") or
                    inp.get("inputFood", {}).get("description", ""))
            if desc:
                input_foods.append(desc.strip()[:100])
        # FoodPortions : indique parfois la forme (flour, ground, sliced…)
        portions = []
        for p in item.get("foodPortions", [])[:3]:
            modifier = p.get("modifier", "").strip()
            port_desc = p.get("portionDescription", "").strip()
            if modifier and modifier.lower() not in ("", "g", "gram"):
                portions.append(modifier[:60])
            elif port_desc:
                portions.append(port_desc[:60])
        result[str(item["fdcId"])] = {
            "description":  item.get("description", "").strip(),
            "category":     item.get("foodCategory", {}).get("description", "").strip(),
            "input_foods":  input_foods,
            "portions":     portions,
        }
    return result


def fetch_usda_api(fdc_id: str, api_key: str) -> Optional[dict]:
    """Appelle l'API FoodData Central pour enrichir un item USDA.
    Retourne un dict enrichi ou None en cas d'erreur.
    """
    try:
        import urllib.request
        url = f"https://api.nal.usda.gov/fdc/v1/food/{fdc_id}?api_key={api_key}&format=full"
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read().decode())
        input_foods = []
        for inp in data.get("inputFoods", [])[:8]:
            desc = inp.get("foodDescription") or inp.get("inputFood", {}).get("description", "")
            if desc:
                input_foods.append(desc.strip()[:100])
        portions = []
        for p in data.get("foodPortions", [])[:3]:
            m = p.get("modifier", "").strip()
            if m and m.lower() not in ("", "g", "gram"):
                portions.append(m[:60])
        return {
            "description": data.get("description", "").strip(),
            "category":    data.get("foodCategory", {}).get("description", "").strip(),
            "input_foods": input_foods,
            "portions":    portions,
        }
    except Exception as exc:
        print(f"  [USDA API] {fdc_id} → {exc}", file=sys.stderr)
        return None


# ---------------------------------------------------------------------------
# Digest builder
# ---------------------------------------------------------------------------

def build_digest(tree: dict, ciqual: dict, cnf: dict, usda: dict,
                 usda_api_key: Optional[str] = None) -> dict:
    """Construit le digest compact {ig_id: [source_entry, ...]} depuis les fichiers bruts.

    Chaque entry encode TOUTE l'information descriptive disponible dans la source
    pour cet aliment : noms, noms scientifiques, groupes, descriptions d'inputs,
    etc. Ce digest est sauvegardé une fois et réutilisé à chaque run d'audit.
    """
    digest: dict[str, list] = {}
    warned = 0
    total  = 0

    for cat in tree["categories"]:
        for sub in cat["subcategories"]:
            for ig in sub["ingredient_groups"]:
                total += 1
                ig_id = ig["id"]
                entries = []
                seen_descs: set[str] = set()

                for var in ig.get("variants", []):
                    src  = var.get("source", "")
                    sid  = str(var.get("source_id", ""))
                    entry: Optional[dict] = None

                    if src == "CIQUAL" and sid in ciqual:
                        d = ciqual[sid]
                        # Concaténer tous les groupes significatifs
                        grps = [g for g in (d["grp1"], d["grp2"], d["grp3"]) if g]
                        entry = {
                            "s":    "CIQUAL",
                            "id":   sid,
                            "desc": d["nom_fr"],
                            "grp":  " > ".join(grps),
                        }
                        if d["nom_sci"]:
                            entry["sci"] = d["nom_sci"]

                    elif src == "CNF" and sid in cnf:
                        d = cnf[sid]
                        # Les deux langues sont utiles : EN pour les termes de
                        # traitement (raw, cooked, dried…) ; FR pour le contexte
                        entry = {
                            "s":      "CNF",
                            "id":     sid,
                            "desc":   d["desc_en"],
                            "desc_fr": d["desc_fr"],
                            "grp":    d["group_en"],
                        }
                        if d["sci_name"]:
                            entry["sci"] = d["sci_name"]

                    elif src == "USDA" and sid in usda:
                        d = usda[sid]
                        entry = {
                            "s":    "USDA",
                            "id":   sid,
                            "desc": d["description"],
                            "cat":  d["category"],
                        }
                        if d["input_foods"]:
                            entry["inputs"] = d["input_foods"]
                        if d["portions"]:
                            entry["portions"] = d["portions"]
                        # Enrichissement API optionnel
                        if usda_api_key:
                            enriched = fetch_usda_api(sid, usda_api_key)
                            if enriched and enriched.get("input_foods"):
                                entry["inputs"] = enriched["input_foods"]
                            time.sleep(0.1)  # rate limit

                    if entry is not None:
                        key = entry["desc"].lower()
                        if key not in seen_descs:
                            seen_descs.add(key)
                            entries.append(entry)

                if entries:
                    digest[ig_id] = entries
                else:
                    warned += 1
                    print(f"  [WARN-DIGEST] {ig_id} ({ig.get('canonical_name_en', '?')}) "
                          f"aucune entrée source trouvée", file=sys.stderr)

    print(f"Digest : {len(digest)} IGs avec sources / {total} total "
          f"({warned} sans source)")
    return digest


def save_digest(digest: dict, path: Path) -> None:
    payload = {
        "version":    "2.0",
        "built_at":   datetime.datetime.utcnow().isoformat() + "Z",
        "count":      len(digest),
        "digest":     digest,
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Digest sauvegardé → {path} ({path.stat().st_size // 1024} Ko)")


def load_digest(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    built_at = payload.get("built_at", "?")
    count    = payload.get("count", "?")
    print(f"Digest chargé : {count} IGs (construit le {built_at})")
    return payload["digest"]


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
    """Yield (cat_label, sub_label, ig_dict) pour tous les IGs non ANIMAL_BASED."""
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


# ---------------------------------------------------------------------------
# Context builder (utilise le digest, pas les fichiers bruts)
# ---------------------------------------------------------------------------

def build_context(cat_lbl: str, sub_lbl: str, ig: dict,
                  digest: dict, locations: list[str]) -> dict:
    """Construit le bloc de contexte envoyé au LLM pour un IG.

    Les sources viennent du digest pré-construit (lecture instantanée).
    On envoie au maximum 10 entrées sources, limitées à 120 chars de desc.
    """
    ig_id   = ig["id"]
    sources = digest.get(ig_id, [])

    # Troncature légère des descriptions (garde l'info clé)
    trimmed = []
    for e in sources[:10]:
        entry = {k: v for k, v in e.items()}
        if "desc" in entry:
            entry["desc"] = entry["desc"][:120]
        if "desc_fr" in entry:
            entry["desc_fr"] = entry["desc_fr"][:80]
        if "inputs" in entry:
            entry["inputs"] = [s[:80] for s in entry["inputs"][:5]]
        trimmed.append(entry)

    # Candidats de repositionnement : même catégorie en priorité
    same_cat_cands = [l for l in locations if l.startswith(f"{cat_lbl}/")]

    return {
        "id":    ig_id,
        "name":  ig.get("canonical_name_en", ""),
        "loc":   f"{cat_lbl}/{sub_lbl}",
        "cands": same_cat_cands,
        "axes":  ig.get("axes_en", {}),
        "src":   trimmed,
    }


# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

MULTI_VALUE_AXES = {
    "treatment",   # ex. ["blanched", "salted"]
    "cooking_state",
    "packaging",
    "seasoning",
}

def build_system_prompt(axes_schema: dict) -> str:
    """Prompt système embarquant les axes valides et les règles strictes."""
    valid_axes = {k: list(v["values"].keys()) for k, v in axes_schema["axes"].items()}
    multi_axes_str = ", ".join(sorted(MULTI_VALUE_AXES))

    return f"""You are a rigorous food taxonomy auditor. Respond ONLY with a JSON object.

=== OUTPUT FORMAT ===
{{
  "results": [
    {{
      "id": "ing_X",
      "axes_set": {{}},
      "axes_remove": [],
      "axes_propose": [],
      "position_ok": true,
      "suggested_location": null,
      "sci_name": null,
      "confidence": "high",
      "reason": ""
    }}
  ]
}}

=== FIELD RULES ===

axes_set   : Dict of axes to ADD or CHANGE. Values: string OR list of strings.
             Multi-valued axes (can be a list): {multi_axes_str}.
             ALL other axes: single string only.
             Use ONLY values from VALID_AXES below.
             ⚠ If an axis is in axes_set, it MUST NOT appear in axes_remove.
             To replace a value: put it in axes_set only (no need to also remove).
             ⚠ NEVER put "sci_name" in axes_set — use the dedicated sci_name field.

axes_remove: List of axis KEYS to delete entirely.
             Use ONLY when the source text explicitly shows the current value is wrong
             and no replacement value exists.
             ⚠ Never list a key here if it is already in axes_set.

axes_propose: List of proposed NEW axes not in VALID_AXES below.
             Format: [{{"key":"new_axis","value":"val","source_quote":"exact phrase from source"}}]
             Only propose if: (1) the characteristic is clearly and explicitly in the source
             text AND (2) no existing axis covers it.

position_ok       : false ONLY if the current location is clearly wrong.
suggested_location: one of cands[] or null.
sci_name          : binomial Latin name if unambiguous from source, else null.
confidence        : "high" (act on it) | "medium" (flag for review) | "low" (skip).
reason            : ONE sentence. MUST quote the exact source phrase(s) that justify
                    each change. Format: SOURCE 'exact phrase' → axis:value.

=== ⚠ STRICT SOURCING RULE ===
You MUST set an axis value ONLY when the source description text EXPLICITLY mentions
the characteristic. Never infer from general food science knowledge.

✓ CIQUAL 'Agar-agar, poudre' → form:"powder"  (word "poudre" is explicit)
✓ CNF 'Oat bran, raw' → cooking_state:"raw"  ("raw" is explicit)
✓ USDA 'Wheat flour, whole-grain' → treatment:"unrefined"  ("whole-grain" implies unrefined, explicit)
✗ Spirulina → thermal_state:"dried"  (not stated in source — DO NOT SET)
✗ Wine → cooking_state:"distilled"  (wine is not distilled — factual error)

If the source does not mention a characteristic: leave the axis unchanged (do not set, do not remove).
If you are unsure: set confidence:"low" and explain in reason.

=== VALID_AXES ===
{json.dumps(valid_axes, ensure_ascii=False)}

Each IG context has:
  loc   = current location in tree
  cands = candidate locations for repositioning (same category)
  axes  = current axes already set
  src   = source entries from raw databases (CIQUAL/CNF/USDA)
"""


# ---------------------------------------------------------------------------
# Groq API call (avec backoff exponentiel sur 429)
# ---------------------------------------------------------------------------

# Paramètres du backoff : attentes en secondes pour chaque tentative
# [15s, 30s, 60s, 120s] → 4 essais max avant de lever l'exception
_BACKOFF_DELAYS = [15, 30, 60, 120]


def _is_rate_limit(exc: Exception) -> bool:
    return "429" in str(exc) or "rate_limit" in str(exc).lower()


def _parse_retry_after(exc: Exception) -> Optional[float]:
    """Extrait le délai retry-after depuis le message d'erreur Groq si disponible."""
    import re
    m = re.search(r"try again in ([\d.]+)s", str(exc), re.IGNORECASE)
    if m:
        return float(m.group(1)) + 1.0   # +1s de marge
    return None


def call_groq(client_factory, batch: list[dict], system_prompt: str,
              model: str) -> list[dict]:
    """Appelle l'API Groq avec backoff exponentiel sur rate limit (429).

    Accepte client_factory (callable → OpenAI) pour renouveler le client
    (et donc tourner les clés) à chaque retry.
    """
    user_msg = json.dumps(batch, ensure_ascii=False)
    last_exc: Exception = RuntimeError("no attempts made")

    for attempt, delay in enumerate([0] + _BACKOFF_DELAYS):
        if delay:
            print(f"  [429] tentative {attempt+1}/{len(_BACKOFF_DELAYS)+1} "
                  f"— attente {delay}s...", flush=True)
            time.sleep(delay)

        try:
            client = client_factory()
            resp   = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_msg},
                ],
                temperature=0.05,
                max_tokens=8192,
                response_format={"type": "json_object"},
            )
            raw = resp.choices[0].message.content
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as e:
                raise ValueError(
                    f"LLM → JSON invalide: {e}\nRaw (300 chars): {raw[:300]}"
                ) from e

            if isinstance(parsed, dict):
                for key in ("results", "items", "data", "corrections"):
                    if key in parsed and isinstance(parsed[key], list):
                        return parsed[key]
                for v in parsed.values():
                    if isinstance(v, list):
                        return v
                return []
            if isinstance(parsed, list):
                return parsed
            return []

        except Exception as exc:
            last_exc = exc
            if _is_rate_limit(exc):
                # Extraire un éventuel retry-after explicite dans le message
                suggested = _parse_retry_after(exc)
                if suggested and attempt < len(_BACKOFF_DELAYS):
                    _BACKOFF_DELAYS[attempt] = max(_BACKOFF_DELAYS[attempt], suggested)
                continue   # passer à l'itération suivante avec le backoff
            raise          # erreur non-429 → propager immédiatement

    raise last_exc         # tous les essais épuisés


# ---------------------------------------------------------------------------
# Post-processing / validation d'un résultat brut LLM
# ---------------------------------------------------------------------------

def normalize_result(raw: dict, axes_schema: dict) -> dict:
    """Nettoie et valide un résultat brut retourné par le LLM.

    - Élimine les conflits axes_set / axes_remove
    - Valide les valeurs axes_set contre le schéma (marque les inconnues)
    - Normalise axes_propose en liste
    - Normalise les valeurs multi-valuées selon MULTI_VALUE_AXES
    """
    valid_axes = {k: set(v["values"].keys()) for k, v in axes_schema["axes"].items()}

    axes_set    = raw.get("axes_set", {}) or {}
    axes_remove = list(raw.get("axes_remove", []) or [])
    axes_propose = raw.get("axes_propose", []) or []

    # Normaliser axes_propose en liste si le LLM a retourné un dict
    if isinstance(axes_propose, dict):
        axes_propose = [{"key": k, "value": v} for k, v in axes_propose.items()]

    # Récupérer sci_name s'il a été mis par erreur dans axes_set
    sci_name_rescued: Optional[str] = None
    if "sci_name" in axes_set:
        val = axes_set.pop("sci_name")
        if isinstance(val, str) and val.strip():
            sci_name_rescued = val.strip()

    # sci_name définitif : champ dédié en priorité, sinon valeur rescapée de axes_set
    sci_name_final: Optional[str] = raw.get("sci_name") or sci_name_rescued

    # Supprimer de axes_remove toute clé déjà dans axes_set (conflit)
    conflict_keys = set(axes_set.keys()) & set(axes_remove)
    if conflict_keys:
        axes_remove = [k for k in axes_remove if k not in conflict_keys]

    # Valider les valeurs axes_set
    unknown_values: list[str] = []
    clean_axes_set: dict = {}
    for axis_key, val in axes_set.items():
        if axis_key not in valid_axes:
            # Axe inconnu → déplacer dans axes_propose
            axes_propose.append({
                "key":          axis_key,
                "value":        val,
                "source_quote": "(moved from axes_set: axis not in schema)",
            })
            continue
        allowed = valid_axes[axis_key]
        if isinstance(val, list):
            if axis_key not in MULTI_VALUE_AXES:
                # Multi-valeur sur un axe mono → prendre le premier
                val = val[0] if val else None
                if val is None:
                    continue
            valid_vals   = [v for v in val if v in allowed]
            invalid_vals = [v for v in val if v not in allowed]
            if invalid_vals:
                unknown_values.append(f"{axis_key}={invalid_vals} (not in schema)")
            if valid_vals:
                clean_axes_set[axis_key] = valid_vals if len(valid_vals) > 1 else valid_vals[0]
        else:
            if val not in allowed:
                unknown_values.append(f"{axis_key}={val!r} (not in schema)")
                # On garde quand même en axes_propose pour review
                axes_propose.append({
                    "key":          axis_key,
                    "value":        val,
                    "source_quote": "(moved from axes_set: value not in schema)",
                })
            else:
                clean_axes_set[axis_key] = val

    result = {
        "id":               raw.get("id", ""),
        "axes_set":         clean_axes_set,
        "axes_remove":      axes_remove,
        "axes_propose":     axes_propose,
        "position_ok":      raw.get("position_ok", True),
        "suggested_location": raw.get("suggested_location"),
        "sci_name":         sci_name_final,
        "confidence":       raw.get("confidence", "high"),
        "reason":           raw.get("reason", ""),
    }

    if unknown_values:
        note = " | SCHEMA_VIOLATIONS: " + "; ".join(unknown_values)
        result["reason"] = (result["reason"] or "") + note

    return result


# ---------------------------------------------------------------------------
# Sauvegarde incrémentale
# ---------------------------------------------------------------------------

def _save(results: list[dict], model: str) -> None:
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(
            {
                "version": "2.0",
                "model":   model,
                "total":   len(results),
                "results": results,
            },
            f, ensure_ascii=False, indent=2,
        )


# ---------------------------------------------------------------------------
# Retry récursif sur 413 (payload trop grand)
# ---------------------------------------------------------------------------

def retry_split(sub: list[dict], client_factory, system_prompt: str,
                model: str, axes_schema: dict, sleep: float,
                depth: int = 0) -> list[dict]:
    if not sub:
        return []
    if len(sub) == 1:
        trimmed = dict(sub[0])
        trimmed["src"] = trimmed.get("src", [])[:3]
        print(f"  [trim] {trimmed['id']} sources réduites à 3", flush=True)
        try:
            time.sleep(sleep)
            raws = call_groq(client_factory, [trimmed], system_prompt, model)
            return [normalize_result(r, axes_schema) for r in raws]
        except Exception as e2:
            print(f"  [skip] {trimmed['id']} toujours trop grand: {e2}")
            return [{"id": trimmed["id"], "error": str(e2)}]
    half = len(sub) // 2
    indent = "  " * depth
    print(f"  {indent}split {len(sub)}→{half}+{len(sub)-half}", flush=True)
    time.sleep(sleep)
    left  = retry_split(sub[:half],  client_factory, system_prompt, model, axes_schema, sleep, depth + 1)
    time.sleep(sleep)
    right = retry_split(sub[half:], client_factory, system_prompt, model, axes_schema, sleep, depth + 1)
    return left + right


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="LLM audit v2 — axes et positions")
    parser.add_argument("--build-digest",   action="store_true",
                        help="Construire le digest sources (à lancer une fois)")
    parser.add_argument("--rebuild-digest", action="store_true",
                        help="Reconstruire le digest même s'il existe déjà")
    parser.add_argument("--usda-api-key",   default=None,
                        help="Clé API USDA FoodData Central (enrichissement optionnel)")
    parser.add_argument("--dry-run",        action="store_true",
                        help="Affiche le contexte, pas d'appel API")
    parser.add_argument("--limit",          type=int, default=0,
                        help="Traiter seulement N IGs (0 = tous)")
    parser.add_argument("--batch-size",     type=int, default=DEFAULT_BATCH,
                        dest="batch_size")
    parser.add_argument("--model",          default=DEFAULT_MODEL)
    parser.add_argument("--sleep",          type=float, default=DEFAULT_SLEEP)
    args = parser.parse_args()

    # ------------------------------------------------------------------ Tree
    print("Chargement du tree et du schéma d'axes...")
    tree        = load_tree()
    axes_schema = load_axes_schema()
    locations   = build_location_list(tree)

    # -------------------------------------------------------- Build-digest mode
    if args.build_digest or args.rebuild_digest:
        if DIGEST_PATH.exists() and not args.rebuild_digest:
            print(f"Le digest existe déjà : {DIGEST_PATH}")
            print("Utilisez --rebuild-digest pour le reconstruire.")
            return

        print("Chargement des sources brutes...")
        print("  CIQUAL...", end=" ", flush=True)
        ciqual = load_ciqual()
        print(f"{len(ciqual)} entrées")

        print("  CNF...", end=" ", flush=True)
        cnf = load_cnf()
        print(f"{len(cnf)} entrées")

        print("  USDA...", end=" ", flush=True)
        usda = load_usda()
        print(f"{len(usda)} entrées")

        print("Construction du digest...")
        digest = build_digest(tree, ciqual, cnf, usda,
                              usda_api_key=args.usda_api_key)
        save_digest(digest, DIGEST_PATH)
        print("Digest construit. Vous pouvez maintenant lancer l'audit.")
        return

    # ------------------------------------------------------- Chargement digest
    if not DIGEST_PATH.exists():
        print("ERREUR : le digest source n'existe pas.", file=sys.stderr)
        print("Lancez d'abord : python audit_positions_llm_v2.py --build-digest",
              file=sys.stderr)
        sys.exit(1)

    digest = load_digest(DIGEST_PATH)

    # -------------------------------------------------------- System prompt
    system_prompt = build_system_prompt(axes_schema)

    # -------------------------------------------------------- Clés Groq
    groq_keys: list[str] = []

    def _extract_keys(pairs):
        keys = []
        for k, v in pairs:
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if v and (k == "GROQ_API_KEY" or
                      (k.startswith("GROQ_API_KEY_") and k[13:].isdigit())):
                keys.append(v)
        return keys

    env_file = ROOT / ".env"
    if env_file.exists():
        pairs = []
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                pairs.append(line.split("=", 1))
        groq_keys = _extract_keys(pairs)

    if not groq_keys:
        groq_keys = _extract_keys(os.environ.items())

    if not groq_keys and not args.dry_run:
        print("ERREUR : aucune GROQ_API_KEY trouvée.", file=sys.stderr)
        sys.exit(1)

    groq_keys = groq_keys or ["dummy"]
    key_cycle = itertools.cycle(groq_keys)
    print(f"Groq keys : {len(groq_keys)} "
          f"({'rotation' if len(groq_keys) > 1 else 'clé unique'})")

    def make_client() -> OpenAI:
        return OpenAI(api_key=next(key_cycle),
                      base_url="https://api.groq.com/openai/v1")

    # -------------------------------------------------- Collecte des IGs
    all_veg = list(iter_vegetarian_igs(tree))
    print(f"IGs végétariens : {len(all_veg)}")

    # Resume
    existing: dict[str, dict] = {}
    if OUT_PATH.exists():
        with open(OUT_PATH, encoding="utf-8") as f:
            saved = json.load(f)
        existing = {r["id"]: r for r in saved.get("results", [])}
        print(f"Reprise : {len(existing)} IGs déjà traités")

    pending_raw = [(c, s, ig) for c, s, ig in all_veg if ig["id"] not in existing]
    if args.limit:
        pending_raw = pending_raw[:args.limit]

    pending = [
        build_context(c, s, ig, digest, locations)
        for c, s, ig in pending_raw
    ]
    # Signaler les IGs sans sources dans le digest
    no_src = [p for p in pending if not p["src"]]
    if no_src:
        print(f"⚠ {len(no_src)} IGs sans sources dans le digest "
              f"(seront envoyés avec src=[])")

    print(f"En attente : {len(pending)} IGs à traiter")

    if args.dry_run:
        for ctx in pending[:3]:
            print(json.dumps(ctx, ensure_ascii=False, indent=2))
        n_batches = -(-len(pending) // args.batch_size)
        print(f"[dry-run] {len(pending)} IGs en {n_batches} batches "
              f"(batch_size={args.batch_size}, model={args.model})")
        return

    # -------------------------------------------------- Boucle de traitement
    results: list[dict] = list(existing.values())
    n_batches = -(-len(pending) // args.batch_size)

    for batch_idx in range(0, len(pending), args.batch_size):
        batch     = pending[batch_idx:batch_idx + args.batch_size]
        batch_num = batch_idx // args.batch_size + 1
        ids_str   = ", ".join(b["id"] for b in batch)
        print(f"[{batch_num}/{n_batches}] {ids_str}", end=" ... ", flush=True)

        try:
            raw_corrections = call_groq(make_client, batch, system_prompt, args.model)
            corr_by_id = {c["id"]: normalize_result(c, axes_schema)
                          for c in raw_corrections if "id" in c}
            for ctx in batch:
                results.append(
                    corr_by_id.get(ctx["id"],
                                   {"id": ctx["id"], "error": "missing_from_response"})
                )
            n_changes = sum(
                1 for c in corr_by_id.values()
                if (c.get("axes_set") or c.get("axes_remove") or c.get("axes_propose")
                    or not c.get("position_ok", True) or c.get("sci_name"))
            )
            print(f"ok ({n_changes} avec modifications)")

        except Exception as exc:
            err_str = str(exc)
            if "413" in err_str:
                print(f"413 (trop grand) — split récursif...", flush=True)
                sub_results = retry_split(batch, make_client, system_prompt,
                                          args.model, axes_schema, args.sleep)
                corr_by_id = {r["id"]: r for r in sub_results if "id" in r}
                for ctx in batch:
                    results.append(
                        corr_by_id.get(ctx["id"],
                                       {"id": ctx["id"], "error": "missing_from_response"})
                    )
                n_changes = sum(
                    1 for r in sub_results
                    if (r.get("axes_set") or r.get("axes_remove") or r.get("axes_propose")
                        or not r.get("position_ok", True) or r.get("sci_name"))
                )
                print(f"ok après split ({n_changes} avec modifications)")
            else:
                print(f"ERREUR: {exc}")
                for ctx in batch:
                    results.append({"id": ctx["id"], "error": err_str})

        _save(results, args.model)

        if batch_idx + args.batch_size < len(pending):
            time.sleep(args.sleep)

    # -------------------------------------------------- Résumé final
    changed  = [r for r in results if (r.get("axes_set") or r.get("axes_remove")
                                       or r.get("axes_propose")
                                       or not r.get("position_ok", True)
                                       or r.get("sci_name"))]
    errors   = [r for r in results if r.get("error")]
    proposed = [r for r in results if r.get("axes_propose")]
    violations = [r for r in results if "SCHEMA_VIOLATIONS" in (r.get("reason") or "")]

    print(f"\n{'='*60}")
    print(f"Total traités    : {len(results)}")
    print(f"Avec modifications : {len(changed)}")
    print(f"Axes proposés    : {len(proposed)} IGs avec axes_propose")
    print(f"Violations schema: {len(violations)} (valeurs inconnues déplacées en axes_propose)")
    print(f"Erreurs          : {len(errors)}")
    print(f"Sortie           : {OUT_PATH}")
    axes_changes   = [r for r in results if r.get("axes_set") or r.get("axes_remove")]
    wrong_position = [r for r in results if not r.get("position_ok", True)]
    with_sci_name  = [r for r in results if r.get("sci_name")]
    print(f"  axes modifiés  : {len(axes_changes)}")
    print(f"  positions KO   : {len(wrong_position)}")
    print(f"  sci_name ajouté: {len(with_sci_name)}")


if __name__ == "__main__":
    main()
