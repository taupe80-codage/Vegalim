#!/usr/bin/env python3
"""audit_coherence.py — audit de cohérence de toutes les recettes (nutrition, structure, métadonnées).

Écrit un rapport détaillé (audit_coherence.txt à côté du script par défaut) et un résumé par
catégorie sur la sortie standard. Les catégories et leur interprétation sont documentées dans
docs/audit_coherence_2026-09-25.md : certaines sont des signaux de qualité, pas des erreurs.

Usage :
    python scripts/recipes/audit_coherence.py [--out chemin.txt]
"""
import json, re, sys, logging, unicodedata, difflib
from pathlib import Path
from collections import defaultdict, Counter

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); logging.disable(logging.CRITICAL)
sys.stdout.reconfigure(encoding="utf-8")

from backend.core.data_io import load_recipes, load_nutrition_graph, is_component_recipe
from backend.engine import nutrition_engine as ne
from backend.engine.nutrition_engine import get_data
from backend.engine.rule_engine.diet import compute_diet_flags

NG = load_nutrition_graph()
RECIPES = load_recipes()
IDS = {r["id"] for r in RECIPES}
out = defaultdict(list)


def norm(s):
    s = (s or "").replace("œ", "oe").replace("Œ", "oe")
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


_cache = {}
def ing(i):
    """fiche nutritionnelle brute de l'ingrédient (dict vide si inconnu)."""
    if i not in _cache:
        try:
            _cache[i] = get_data.ingredients.resolve_nutrition(i, use_cooked=False) or {}
        except Exception:
            _cache[i] = {}
    return _cache[i]


def fr(i):
    return ing(i).get("name_fr") or ""


# ---------------------------------------------------------------- bornes
KCAL = {  # (min, max) kcal/portion plausibles
    "main": (200, 850), "pasta": (250, 900), "soup": (60, 600), "side": (40, 600),
    "starter": (40, 600), "dessert": (90, 650), "breakfast": (120, 750), "snack": (60, 650),
    "bread": (80, 700), "pastry": (80, 700), "beverage": (0, 450),
}
PORTION_MIN_G = {  # poids hors eau minimal (g/portion), cf. propose_servings
    "main": 150, "pasta": 150, "soup": 120, "side": 80, "starter": 60, "dessert": 60,
    "breakfast": 90, "snack": 60, "bread": 50, "pastry": 40, "beverage": 100,
}
SAUCY = ("sauce", "condiment", "paste", "base", "broth", "dairy", "ingredient", "roux")

COOK_RE = re.compile(r"\b(cuire|cuisez|cuisson|mijoter|bouillir|ebullition|frire|rotir|"
                     r"enfourner|enfournez|griller|grillez|saisir|revenir|sauter|poeler|"
                     r"blanchir|pocher|gratiner|braiser|etuver|caraceliser|caraeliser)\b")
NUTS = ("almond", "walnut", "cashew", "pistachio", "hazelnut", "pecan", "macadamia",
        "brazil_nut", "pine_nut", "peanut", "nut_")
GLUTEN = ("wheat", "barley", "rye_", "couscous", "semolina", "bulgur", "freekeh", "seitan",
          "pasta_raw_dried", "egg_pasta", "udon", "phyllo", "puff_pastry", "bread",
          "spelt", "farro", "soy_sauce_shoyu", "bakers_yeast", "panko", "breadcrumbs")
DAIRY = ("milk", "butter_sup", "cream", "cheese", "yogurt", "feta", "mozzarella", "ricotta",
         "parmesan", "gouda", "cheddar", "camembert", "comte", "emmental", "queso", "halloumi",
         "kefir", "ghee", "mascarpone", "gruyere", "brousse", "brocciu")
ANIMAL = ("egg_", "honey", "gelatin", "fish", "anchov", "chicken", "beef", "pork", "lard",
          "duck_egg", "quail")
CHILI = ("chili", "chilli", "piment", "harissa", "gochujang", "cayenne", "jalapeno",
         "sambal", "berbere", "sriracha")


def portion_weight_g(r, servings):
    """poids hors eau d'une portion (g)."""
    tot = 0.0
    for c in r.get("composition") or []:
        m = c.get("meta") or {}
        if m.get("role") == "serving_suggestion" or c.get("quantity") is None:
            continue
        cid = c["ingredient"]
        if cid.startswith("water"):
            continue
        try:
            g = ne._qty_to_g(cid, c)
        except Exception:
            continue
        w = ing(cid).get("water_g")
        tot += g * (1 - (w or 0) / 100) if w is not None else g
    return tot / max(servings, 1)


BY_ID = {r["id"]: r for r in RECIPES}


def chili_g(rid, depth=0):
    """grammes d'ingrédient piquant, sous-recettes comprises."""
    r = BY_ID.get(rid)
    if r is None or depth > 3:
        return 0.0
    tot = 0.0
    for c in r.get("composition") or []:
        cid = c["ingredient"]
        if (c.get("meta") or {}).get("role") == "serving_suggestion" or c.get("quantity") is None:
            continue
        try:
            g = ne._qty_to_g(cid, c)
        except Exception:
            g = 0.0
        if any(k in cid for k in CHILI) or any(k in norm(fr(cid)) for k in ("piment", "harissa", "gochujang")):
            tot += g
        elif cid in BY_ID:
            sub = chili_g(cid, depth + 1)
            if sub:
                tot += sub * (g / max(sum((ne._qty_to_g(x["ingredient"], x) if x.get("quantity") else 0)
                                          for x in BY_ID[cid].get("composition") or []), 1))
    return tot


# --------------------------------------------------------- boucle principale
sig_by_dish = defaultdict(list)          # (dish_type) -> (rid, set(ingrédients))
titles = []
for r in RECIPES:
    rid, dt = r["id"], (r.get("dish_type") or "")
    t = r.get("titles") or {}
    fr_title = t.get("fr") or ""
    n = NG.get(rid) or {}
    kcal = n.get("calories") or 0
    na = n.get("sodium") or 0
    fat = n.get("fat") or 0
    prot = n.get("protein") or 0
    srv = ne.resolve_servings(r)
    comp = r.get("composition") or []
    core = [c for c in comp if (c.get("meta") or {}).get("role") != "serving_suggestion"]
    steps = r.get("instructions") or []
    text = norm(" ".join(steps))
    timing = r.get("timing") or {}
    flags = r.get("diet_flags") or {}
    component = is_component_recipe(r)

    # ---- 1. nutrition
    if dt in KCAL and kcal and not component:
        lo, hi = KCAL[dt]
        if kcal < lo:
            out["kcal_bas"].append(f"{rid} ({dt}) {kcal:.0f} kcal/portion < {lo} — {fr_title}")
        elif kcal > hi:
            out["kcal_haut"].append(f"{rid} ({dt}) {kcal:.0f} kcal/portion > {hi} — {fr_title}")
    if na > 1300 and dt not in SAUCY:
        out["sodium"].append(f"{rid} ({dt}) Na {na:.0f} mg/portion — {fr_title}")
    if kcal and fat * 9 / kcal > 0.65 and dt not in SAUCY and dt not in ("dessert", "beverage") and not component:
        out["gras"].append(f"{rid} ({dt}) {fat*9/kcal:.0%} des kcal en lipides — {fr_title}")
    if dt in ("main", "pasta") and prot and prot < 10 and not component:
        out["proteines_main"].append(f"{rid} P{prot:.1f} g/portion — {fr_title}")
    if dt in PORTION_MIN_G and not component:
        pw = portion_weight_g(r, srv)
        if pw < PORTION_MIN_G[dt] * 0.45 and kcal and kcal < 350:
            out["portion_legere"].append(f"{rid} ({dt}) {pw:.0f} g hors eau/portion (min {PORTION_MIN_G[dt]}) — {fr_title}")

    # ---- 2. composition
    seen = Counter(c["ingredient"] for c in core)
    for cid, k in seen.items():
        if k > 1:
            out["ingredient_double"].append(f"{rid} {cid} ×{k} — {fr_title}")
    for c in comp:
        cid = c["ingredient"]
        m = c.get("meta") or {}
        q, u = c.get("quantity"), c.get("unit")
        if cid not in IDS and not ing(cid):
            out["ingredient_inconnu"].append(f"{rid} {cid}")
        if m.get("role") != "serving_suggestion":
            if q is None:
                out["quantite_absente"].append(f"{rid} {cid} (role {m.get('role')!r})")
            elif isinstance(q, (int, float)) and q <= 0:
                out["quantite_nulle"].append(f"{rid} {cid} = {q}")
        if q is not None and u not in ("g", "ml", "cl", "l", "kg", "piece", "pieces", "unite", "cuillere", None):
            out["unite_inhabituelle"].append(f"{rid} {cid} {q} {u!r}")
        try:
            gp = ne._qty_to_g(cid, c) / srv if q is not None else 0
        except Exception:
            gp = 0
        if gp > 350 and not cid.startswith(("water", "base_", "milk", "vegetable_stock", "coconut_milk")) \
                and dt not in ("base", "dairy", "broth", "beverage", "soup"):
            out["ingredient_lourd"].append(f"{rid} {cid} {gp:.0f} g/portion — {fr_title}")
        if cid.startswith("table_salt") and q and gp > 2.5:
            out["sel"].append(f"{rid} {gp:.1f} g de sel/portion — {fr_title}")

    # ---- 3. régimes / allergènes (recalcul indépendant)
    try:
        calc = compute_diet_flags(core, get_data.ingredients) or {}
    except Exception:
        calc = {}
    for f in ("vegan", "vegetarian", "gluten_free", "lactose_free", "nut_free"):
        if f in calc and flags.get(f) and not calc[f]:
            out["regime_contredit"].append(f"{rid} {f}=True mais le calcul dit False — {fr_title}")
    ids_core = [c["ingredient"] for c in core]
    if flags.get("vegan") and not flags.get("vegetarian"):
        out["vegan_sans_vegetarien"].append(f"{rid} — {fr_title}")
    tag_diet = set((r.get("tags") or {}).get("diet") or [])
    for f, v in flags.items():
        if f in ("vegan", "vegetarian", "gluten_free", "lactose_free", "nut_free", "raw", "kid_friendly"):
            if not v and f in tag_diet:
                out["tags_diet_desync"].append(f"{rid} flag {f}=False présent dans tags.diet — {fr_title}")

    # ---- 4. temps et texte
    a, p, ck = (timing.get(k) or 0 for k in ("prep_active_min", "prep_passive_min", "cook_min"))
    if timing.get("total_min") != a + p + ck:
        out["temps_total"].append(f"{rid} total {timing.get('total_min')} ≠ {a}+{p}+{ck}")
    if a + p + ck == 0:
        out["temps_zero"].append(f"{rid} — {fr_title}")
    m_cook = COOK_RE.search(text)
    if ck == 0 and m_cook and not flags.get("raw"):
        out["cuisson_sans_temps"].append(f"{rid} cook_min=0 mais « {m_cook.group(1)} » dans le texte — {fr_title}")
    if flags.get("raw") and ck > 0:
        out["raw_avec_cuisson"].append(f"{rid} raw + cook_min={ck} — {fr_title}")
    if flags.get("raw") and m_cook:
        out["raw_texte_cuisson"].append(f"{rid} raw mais « {m_cook.group(1)} » dans le texte — {fr_title}")
    if len(steps) < 3:
        out["etapes_courtes"].append(f"{rid} {len(steps)} étape(s) — {fr_title}")
    for i, s in enumerate(steps, 1):
        if not s.startswith(f"Étape {i}"):
            out["numerotation"].append(f"{rid} étape {i} : {s[:40]!r}")
            break
        if len(s) > 400:
            out["etape_longue"].append(f"{rid} étape {i} : {len(s)} caractères")
    d = r.get("description") or ""
    if len(d) < 60:
        out["description_courte"].append(f"{rid} {len(d)} caractères : {d[:60]!r}")
    if d and d[0].islower():
        out["description_minuscule"].append(f"{rid} {d[:50]!r}")

    # ---- 5. métadonnées
    if not t.get("en"):
        out["titre_en_absent"].append(f"{rid} — {fr_title}")
    elif norm(t["en"]) == norm(fr_title) and re.search(
            r"\b(de|du|des|au|aux|a|la|le|les|et|en|sans|maison|sauce|salade|soupe|gateau|"
            r"galette|tarte|puree|creme|riz|pain|legumes)\b", norm(fr_title)):
        out["titre_en_identique"].append(f"{rid} « {fr_title} »")
    o = r.get("origin") or {}
    if not o.get("cuisine"):
        out["origine_absente"].append(f"{rid} — {fr_title}")
    elif o.get("cuisine") == "international" and not component:
        out["cuisine_international"].append(f"{rid} ({dt}) — {fr_title}")
    if not o.get("country"):
        out["pays_absent"].append(f"{rid} ({o.get('cuisine')}) — {fr_title}")
    if r.get("servings") != r.get("servings_default"):
        out["portions_desync"].append(f"{rid} servings {r.get('servings')} ≠ default {r.get('servings_default')}")
    if not (r.get("result") or {}).get("texture"):
        out["texture_absente"].append(f"{rid} — {fr_title}")
    if not (r.get("tags") or {}).get("technique"):
        out["technique_absente"].append(f"{rid} ({dt}) — {fr_title}")
    sp = (r.get("scoring") or {}).get("spice_level")
    cg = chili_g(rid)
    if (sp or 0) == 0 and cg >= 8:
        out["piment_sans_niveau"].append(f"{rid} {cg:.0f} g de piment, spice_level=0 — {fr_title}")
    if (sp or 0) >= 3 and cg < 1:
        out["niveau_sans_piment"].append(f"{rid} spice_level={sp} sans ingrédient piquant — {fr_title}")
    if flags.get("kid_friendly") and cg >= 10:
        out["kid_friendly_piment"].append(f"{rid} {cg:.0f} g de piment — {fr_title}")

    titles.append((rid, fr_title, dt))
    sig_by_dish[dt].append((rid, fr_title, frozenset(ids_core)))

# ---- 6. doublons : composition presque identique dans le même dish_type
for dt, items in sig_by_dish.items():
    for i in range(len(items)):
        rid_a, ta, sa = items[i]
        if len(sa) < 4:
            continue
        for j in range(i + 1, len(items)):
            rid_b, tb, sb = items[j]
            if len(sb) < 4:
                continue
            inter = len(sa & sb)
            jac = inter / len(sa | sb)
            if jac >= 0.8:
                out["compo_quasi_identique"].append(
                    f"{jac:.0%} {rid_a} « {ta} » ≈ {rid_b} « {tb} » ({dt})")

# ---- 7. titres très proches
seen_t = defaultdict(list)
for rid, ti, dt in titles:
    key = norm(ti).split(",")[0].strip()
    seen_t[key].append((rid, ti, dt))
for key, v in seen_t.items():
    if len(v) > 1:
        out["titre_identique"].append(" / ".join(f"{rid} « {ti} » ({dt})" for rid, ti, dt in v))
norm_titles = [(rid, norm(ti).split(",")[0].strip(), ti, dt) for rid, ti, dt in titles]
for i in range(len(norm_titles)):
    for j in range(i + 1, len(norm_titles)):
        a, b = norm_titles[i], norm_titles[j]
        if abs(len(a[1]) - len(b[1])) > 6 or a[1] == b[1]:
            continue
        if difflib.SequenceMatcher(None, a[1], b[1]).ratio() >= 0.9:
            out["titre_proche"].append(f"{a[0]} « {a[2]} » ≈ {b[0]} « {b[2]} »")

rep = (Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv
       else Path(__file__).with_name("audit_coherence.txt"))
with rep.open("w", encoding="utf-8", newline="\n") as f:
    for k in sorted(out, key=lambda k: -len(out[k])):
        f.write(f"\n## {k} ({len(out[k])})\n")
        for line in out[k]:
            f.write(f"  {line}\n")
print(f"{len(RECIPES)} recettes auditées → {rep}\n")
for k in sorted(out, key=lambda k: -len(out[k])):
    print(f"{len(out[k]):5d}  {k}")
print(f"\ntotal signalements : {sum(len(v) for v in out.values())}")
