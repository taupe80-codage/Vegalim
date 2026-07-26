#!/usr/bin/env python3
"""
map_editor.py — Outil interactif pour corriger ingredient_map_v2.json
======================================================================
Permet de :
  1. Rechercher des group_ids dans nutrition_v2 par terme (avec catégorie)
  2. Voir l'état actuel d'un recipe_id dans le map
  3. Assigner un group_id à un recipe_id (avec cooking_variants optionnel)
  4. Lister les entrées AUTO_LOW / MANUAL_NEEDED / absentes

Usage :
  python scripts/map_editor.py

Commandes interactives :
  s <terme>          — Recherche dans nutrition_v2 (group_id + canonical_name)
  sc <categorie>     — Lister tous les group_ids d'une catégorie
  cat                — Lister toutes les catégories disponibles
  show <recipe_id>   — Voir l'entrée actuelle dans le map
  set <rid> <gid>    — Assigner gid à rid (raw only)
  setc <rid> <gid_raw> <gid_cooked>  — Assigner raw + default_cooked
  low                — Lister toutes les entrées AUTO_LOW
  missing            — Lister les recipe_ids fréquents absents du map
  save               — Sauvegarder le map (fait aussi à chaque set/setc)
  q                  — Quitter
"""
import sys, json, re
from pathlib import Path
from collections import Counter, defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

MAP_PATH  = Path("backend/data/recipes/ingredient_map_v2.json")
NUTR_PATH = Path("backend/data/nutrition/processed/nutrition_v2.json")
REC_PATH  = Path("backend/data/recipes/recipes.json")

# ── Chargement ────────────────────────────────────────────────────────────────
print("Chargement des données...")
m        = json.load(open(MAP_PATH,  encoding="utf-8"))
nutr     = json.load(open(NUTR_PATH, encoding="utf-8"))
ings_n2  = nutr.get("ingredients", {})
recipes  = json.load(open(REC_PATH,  encoding="utf-8"))["recipes"]

# Index des fréquences d'usage dans les recettes
ing_freq: Counter = Counter()
for rec in recipes:
    for comp in rec.get("composition", []):
        raw = comp.get("ingredient", "")
        if raw:
            ing_freq[raw] += 1
            base = raw.split("/")[0]
            if base != raw:
                ing_freq[base] += 1

# Index nutrition_v2 par catégorie (cat1)
cat_index: dict[str, list] = defaultdict(list)
for gid, entry in ings_n2.items():
    tax  = entry.get("taxonomy", {})
    cat1 = tax.get("cat1", "unknown")
    variants = entry.get("variants", {})
    vdata = next(iter(variants.values()), {}) if variants else {}
    cal   = vdata.get("calories_kcal", "?")
    prot  = vdata.get("protein_g", "?")
    cs    = vdata.get("axes", {}).get("cooking_state", "")
    name_en = tax.get("name_en", "")
    name_fr = tax.get("name_fr", "")
    source  = vdata.get("_source", "")
    cat_index[cat1].append({
        "gid": gid, "cat1": cat1,
        "cat2": tax.get("cat2", ""),
        "name_en": name_en, "name_fr": name_fr,
        "cal": cal, "prot": prot,
        "cooking_state": cs, "source": source,
    })

all_cats = sorted(cat_index.keys())

# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm(s: str) -> str:
    return s.lower().replace("_", " ").replace("/", " ").replace("-", " ")

def _sim(a: str, b: str) -> float:
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio()

def _fmt_entry(e: dict, rank: int = 0) -> str:
    cs  = f" [{e['cooking_state']}]" if e['cooking_state'] else ""
    fr  = f" / {e['name_fr']}"      if e['name_fr'] else ""
    src = f" {e['source']}"
    return (f"  [{rank:>3d}] {e['gid']:<55s}"
            f"  cal={str(e['cal']):>5}{cs}"
            f"  {e['cat2']}")

def search(term: str, limit: int = 25) -> list[dict]:
    """Fuzzy search dans group_ids ET canonical_name_en/fr."""
    results = []
    term_lower = term.lower().replace("_", " ")
    for gid, info_list in [(e["gid"], e) for cat in cat_index.values() for e in cat]:
        g_score = _sim(term_lower, gid)
        n_score = _sim(term_lower, info_list["name_en"])
        f_score = _sim(term_lower, info_list["name_fr"])
        # Bonus si le terme est contenu dans le gid ou name
        if term_lower in gid.lower() or term_lower in info_list["name_en"].lower():
            g_score = max(g_score, 0.95)
        best = max(g_score, n_score, f_score)
        results.append((best, info_list))
    results.sort(key=lambda x: -x[0])
    return [r for _, r in results[:limit]]

def show_map_entry(rid: str):
    e = m.get(rid)
    if not e:
        print(f"  '{rid}' absent du map")
        freq = ing_freq.get(rid, 0)
        print(f"  Fréquence recettes: {freq}")
        return
    print(f"  recipe_id   : {rid}")
    print(f"  group_id_v2 : {e.get('group_id_v2')}")
    print(f"  status      : {e.get('status')}  conf={e.get('confidence','?')}")
    print(f"  method      : {e.get('method')}")
    print(f"  cooking_variants:")
    cv = e.get("cooking_variants", {})
    for k, v in cv.items():
        print(f"    {k:<15s}: {v}")

def assign(rid: str, gid: str, cv: dict | None = None):
    if gid not in ings_n2:
        print(f"  ERREUR: '{gid}' absent de nutrition_v2")
        return
    e_n2 = ings_n2[gid]
    tax  = e_n2.get("taxonomy", {})
    vdata = next(iter(e_n2.get("variants", {}).values()), {})
    cal  = vdata.get("calories_kcal", "?")
    if rid not in m:
        m[rid] = {}
    m[rid].update({
        "group_id_v2":      gid,
        "confidence":       1.0,
        "method":           "manual_editor",
        "status":           "AUTO_HIGH",
        "canonical_name_en": tax.get("name_en", ""),
        "cat_id":           tax.get("cat1", ""),
    })
    m[rid]["cooking_variants"] = cv if cv else {"raw": gid, "default": gid}
    # Sauvegarde immédiate
    MAP_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  OK: '{rid}' -> '{gid}'  (cal={cal} kcal/100g)  [sauvegardé]")

def list_low():
    low = [(rid, e) for rid, e in m.items()
           if e.get("status") in ("AUTO_LOW", "MANUAL_NEEDED")]
    print(f"\n  {len(low)} entrées AUTO_LOW / MANUAL_NEEDED :")
    for rid, e in sorted(low):
        freq = ing_freq.get(rid, 0)
        print(f"    {rid:<40s}  -> {e.get('group_id_v2','?')}  [{e.get('status')}]  {freq}x recettes")

def list_missing(limit: int = 50):
    missing = [(iid, cnt) for iid, cnt in ing_freq.most_common()
               if iid not in m and cnt >= 3]
    print(f"\n  {len(missing)} IDs recettes absents du map (min 3 occurrences):")
    for iid, cnt in missing[:limit]:
        print(f"    {iid:<40s}  {cnt:>4d}x")

def list_cats():
    print(f"\n  {len(all_cats)} catégories dans nutrition_v2 :")
    for i, cat in enumerate(all_cats):
        n = len(cat_index[cat])
        print(f"    [{i:>3d}] {cat:<45s} ({n:>4d} groupes)")

def search_cat(cat_term: str, limit: int = 40):
    matches = [(c, cat_index[c]) for c in all_cats if cat_term.lower() in c.lower()]
    if not matches:
        print(f"  Catégorie '{cat_term}' introuvable")
        list_cats()
        return
    for cat, entries in matches[:3]:
        print(f"\n  [{cat}]  ({len(entries)} groupes)")
        # Trier par sous-catégorie puis gid
        for e in sorted(entries, key=lambda x: (x["cat2"], x["gid"]))[:limit]:
            cs   = f"[{e['cooking_state']}]" if e['cooking_state'] else "       "
            fr   = e['name_fr'][:25] if e['name_fr'] else ""
            print(f"    {e['gid']:<55s}  {cs}  {e['cat2'][:25]}")

# ── REPL ─────────────────────────────────────────────────────────────────────

HELP = """
Commandes :
  s <terme>                    Recherche fuzzy dans nutrition_v2
  sc <cat>                     Lister group_ids d'une catégorie
  cat                          Lister toutes les catégories
  show <recipe_id>             Voir entrée map actuelle
  set <rid> <gid>              Assigner gid à rid (raw uniquement)
  setc <rid> <gid_raw> <gid_cooked>  Assigner raw + default_cooked
  low                          Lister AUTO_LOW / MANUAL_NEEDED
  missing [N]                  Lister IDs recettes absents (défaut top 50)
  save                         Sauvegarder
  h                            Aide
  q                            Quitter
"""

print(f"\nMap chargé : {len(m)} entrées")
print(f"Nutrition_v2 : {len(ings_n2)} group_ids")
print(f"Recettes : {len(recipes)} | IDs uniques : {len(ing_freq)}")
print(HELP)

while True:
    try:
        line = input("map> ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAu revoir.")
        break

    if not line:
        continue
    parts = line.split()
    cmd   = parts[0].lower()

    # ── Recherche
    if cmd == "s" and len(parts) >= 2:
        term    = " ".join(parts[1:])
        results = search(term)
        print(f"\n  Résultats pour '{term}' ({len(results)} trouvés):")
        for i, e in enumerate(results):
            print(_fmt_entry(e, i + 1))

    # ── Recherche par catégorie
    elif cmd == "sc" and len(parts) >= 2:
        search_cat(" ".join(parts[1:]))

    # ── Catégories
    elif cmd == "cat":
        list_cats()

    # ── Afficher entrée map
    elif cmd == "show" and len(parts) >= 2:
        show_map_entry(parts[1])

    # ── Assigner simple
    elif cmd == "set" and len(parts) == 3:
        rid, gid = parts[1], parts[2]
        assign(rid, gid)

    # ── Assigner avec cuisson
    elif cmd == "setc" and len(parts) == 4:
        rid, gid_raw, gid_cooked = parts[1], parts[2], parts[3]
        if gid_cooked not in ings_n2:
            print(f"  ERREUR: '{gid_cooked}' absent de nutrition_v2")
        else:
            cv = {
                "raw": gid_raw, "default": gid_raw,
                "boiled": gid_cooked, "cooked": gid_cooked,
                "default_cooked": gid_cooked,
            }
            assign(rid, gid_raw, cv=cv)

    # ── Lister LOW
    elif cmd == "low":
        list_low()

    # ── Lister absents
    elif cmd == "missing":
        limit = int(parts[1]) if len(parts) > 1 else 50
        list_missing(limit)

    # ── Sauvegarder
    elif cmd == "save":
        MAP_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Sauvegardé : {MAP_PATH}  ({len(m)} entrées)")

    # ── Aide
    elif cmd in ("h", "help"):
        print(HELP)

    # ── Quitter
    elif cmd == "q":
        MAP_PATH.write_text(json.dumps(m, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  Sauvegardé et fermeture. ({len(m)} entrées)")
        break

    else:
        print(f"  Commande inconnue : '{cmd}'. Tape 'h' pour l'aide.")
