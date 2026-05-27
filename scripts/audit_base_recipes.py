"""
scripts/audit_base_recipes.py
Verifie l'architecture et la coherence des recettes base_* dans recipes.json.

Controles :
  1. Champs obligatoires (id, titles, composition, servings, dish_type)
  2. Coherence composition (quantites, unites, ingredients resolus)
  3. Utilisation des bases par les recettes normales (references croisees)
  4. Incoherences dietetiques (base non-vegan utilisee dans recette vegan)
"""
import json
import pathlib
import collections

DATA         = pathlib.Path("backend/data")
RECIPES_PATH = DATA / "recipes" / "recipes.json"
NG_PATH      = DATA / "graphs" / "recipe_nutrition_graph_v1.json"

raw     = json.loads(RECIPES_PATH.read_text(encoding="utf-8"))
recipes = raw.get("recipes", raw) if isinstance(raw, dict) else raw
NG      = json.loads(NG_PATH.read_text(encoding="utf-8"))

recipe_map = {str(r["id"]): r for r in recipes}
base_ids   = [str(r["id"]) for r in recipes if str(r["id"]).startswith("base_")]
normal_ids = [str(r["id"]) for r in recipes if not str(r["id"]).startswith("base_")]

print(f"=== Audit Base Recettes ===")
print(f"Total recettes   : {len(recipes)}")
print(f"Base recettes    : {len(base_ids)}")
print(f"Recettes normales: {len(normal_ids)}")
print(f"Dans NG          : {len(NG)}")

# ── 1. Champs obligatoires ────────────────────────────────────────────────────
REQUIRED_FIELDS = ["id", "composition", "servings", "dish_type"]
print(f"\n{'='*60}")
print("1. CHAMPS OBLIGATOIRES")
print(f"{'='*60}")

issues_fields = []
for rid in base_ids:
    r = recipe_map[rid]
    missing = [f for f in REQUIRED_FIELDS if not r.get(f)]
    title = (r.get("titles") or {}).get("fr") or r.get("title_fr", rid)
    if missing:
        issues_fields.append((rid, title, missing))

if issues_fields:
    for rid, title, missing in issues_fields:
        print(f"  MANQUE {missing} | {rid} | {title[:45]}")
else:
    print(f"  OK — tous les {len(base_ids)} base_* ont les champs requis")

# ── 2. Coherence composition ──────────────────────────────────────────────────
print(f"\n{'='*60}")
print("2. COHERENCE COMPOSITION")
print(f"{'='*60}")

VALID_UNITS = {
    "g", "kg", "ml", "l", "cl", "dl", "mg",
    "piece", "pieces", "tbsp", "tsp", "cup",
    "cuillere_soupe", "cuillere_cafe",
    "gousse", "tranche", "botte", "branche",
    "pinch", "pincee",
}

stats = collections.defaultdict(int)
issues_comp = []
empty_comp  = []

for rid in base_ids:
    r    = recipe_map[rid]
    comp = r.get("composition") or []
    title = (r.get("titles") or {}).get("fr") or r.get("title_fr", rid)

    if not comp:
        empty_comp.append((rid, title))
        stats["vide"] += 1
        continue

    stats["avec_composition"] += 1
    has_qty_issue = False
    for item in comp:
        if not isinstance(item, dict):
            issues_comp.append((rid, title, f"item non-dict: {item}"))
            has_qty_issue = True
            continue
        ing   = item.get("ingredient", "")
        qty   = item.get("quantity", 0)
        unit  = item.get("unit", "g")
        if not ing:
            issues_comp.append((rid, title, "ingredient vide"))
            has_qty_issue = True
        if qty is None or (isinstance(qty, (int, float)) and qty < 0):
            issues_comp.append((rid, title, f"qty invalide: {qty} pour {ing}"))
            has_qty_issue = True
        if unit and str(unit).lower() not in VALID_UNITS:
            issues_comp.append((rid, title, f"unite inconnue: '{unit}' pour {ing}"))

    if not has_qty_issue:
        stats["composition_ok"] += 1

print(f"  Base avec composition      : {stats['avec_composition']}")
print(f"  Base composition OK        : {stats['composition_ok']}")
print(f"  Base composition VIDE      : {len(empty_comp)}")

if empty_comp:
    print("\n  Bases SANS composition :")
    for rid, title in empty_comp:
        in_ng = "NG:OK" if rid in NG else "NG:MANQUE"
        print(f"    {rid} | {title[:45]} | {in_ng}")

if issues_comp:
    print(f"\n  Problemes composition ({len(issues_comp)}) :")
    for rid, title, msg in issues_comp[:15]:
        print(f"    {rid[:30]} | {msg}")

# ── 3. References croisees ────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("3. REFERENCES CROISEES (base utilisee par recettes normales)")
print(f"{'='*60}")

base_usage = collections.defaultdict(list)  # base_id -> [recipe_ids qui l'utilisent]

for rid in normal_ids:
    r    = recipe_map[rid]
    comp = r.get("composition") or []
    for item in comp:
        if isinstance(item, dict):
            ing = item.get("ingredient", "")
        else:
            ing = str(item)
        if ing.startswith("base_") and ing in recipe_map:
            base_usage[ing].append(rid)

used_bases   = set(base_usage.keys())
unused_bases = set(base_ids) - used_bases

print(f"  Bases referencees par recettes normales : {len(used_bases)}")
print(f"  Bases NON referencees (standalone)      : {len(unused_bases)}")

print("\n  Top 10 bases les plus utilisees :")
for bid, users in sorted(base_usage.items(), key=lambda x: -len(x[1]))[:10]:
    btitle = (recipe_map[bid].get("titles") or {}).get("fr", bid)[:35]
    print(f"    {bid:35s} x{len(users):3d}  {btitle}")

# ── 4. Coherence dietetique ───────────────────────────────────────────────────
print(f"\n{'='*60}")
print("4. COHERENCE DIETETIQUE (base non-vegan dans recette vegan)")
print(f"{'='*60}")

NON_VEGAN_BASES = set()
for bid in base_ids:
    r     = recipe_map[bid]
    flags = r.get("diet_flags") or {}
    tags  = r.get("tags") or {}
    is_vegan = flags.get("vegan") or "vegan" in (tags.get("diet") or [])
    if not is_vegan:
        NON_VEGAN_BASES.add(bid)

diet_issues = []
for rid in normal_ids:
    r     = recipe_map[rid]
    flags = r.get("diet_flags") or {}
    tags  = r.get("tags") or {}
    is_vegan = flags.get("vegan") or "vegan" in (tags.get("diet") or [])
    if not is_vegan:
        continue
    comp = r.get("composition") or []
    for item in comp:
        ing = item.get("ingredient", "") if isinstance(item, dict) else str(item)
        if ing in NON_VEGAN_BASES:
            rtitle = (r.get("titles") or {}).get("fr", rid)[:35]
            btitle = (recipe_map[ing].get("titles") or {}).get("fr", ing)[:25]
            diet_issues.append((rid, rtitle, ing, btitle))

if diet_issues:
    print(f"  INCOHERENCES ({len(diet_issues)}) :")
    for rid, rt, bid, bt in diet_issues:
        print(f"    {rid[:30]} ({rt}) utilise base non-vegan : {bt}")
else:
    print(f"  OK — aucune incoherence dietetique detectee")

# ── 5. Etat graphe nutrition ──────────────────────────────────────────────────
print(f"\n{'='*60}")
print("5. COUVERTURE GRAPHE NUTRITION (base_*)")
print(f"{'='*60}")

in_ng     = [bid for bid in base_ids if bid in NG]
not_in_ng = [bid for bid in base_ids if bid not in NG]
print(f"  Bases dans NG     : {len(in_ng)}/{len(base_ids)}")
print(f"  Bases manquantes  : {len(not_in_ng)}")

if not_in_ng:
    print("\n  Bases manquantes dans NG :")
    for bid in sorted(not_in_ng):
        comp = recipe_map[bid].get("composition") or []
        btitle = (recipe_map[bid].get("titles") or {}).get("fr", bid)[:40]
        print(f"    {bid:40s} | comp:{len(comp)} items | {btitle}")

# ── Resume ────────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("RESUME")
print(f"{'='*60}")
print(f"  Base recettes total         : {len(base_ids)}")
print(f"  Avec composition            : {stats['avec_composition']}")
print(f"  Composition vide            : {len(empty_comp)}")
print(f"  Problemes composition       : {len(issues_comp)}")
print(f"  Champs manquants            : {len(issues_fields)}")
print(f"  Incoherences dietetiques    : {len(diet_issues)}")
print(f"  Dans graphe nutrition       : {len(in_ng)}/{len(base_ids)}")
print(f"  Bases non referencees       : {len(unused_bases)}")
