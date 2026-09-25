#!/usr/bin/env python3
"""audit_text_coherence.py — cohérence entre les étapes et la composition des recettes.

  - jamais_cite     : ingrédient de la composition absent des étapes (alias FR connus)
  - quantite_texte  : quantité citée dans une étape sans ligne de composition correspondante

Le bouillon déshydraté, l'eau et le sel sont exclus du second contrôle : le texte cite le
bouillon reconstitué (750 ml) là où la composition porte la poudre (9,4 g).

Usage :
    python scripts/recipes/audit_text_coherence.py [--out chemin.txt]
"""
import json, re, sys, logging, unicodedata
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT)); logging.disable(logging.CRITICAL)
sys.stdout.reconfigure(encoding="utf-8")
from backend.core.data_io import load_recipes
from backend.engine import nutrition_engine as ne
from backend.engine.nutrition_engine import get_data


def norm(s):
    s = (s or "").replace("œ", "oe").replace("Œ", "oe")
    return unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()


_c = {}
def fr(i):
    if i not in _c:
        try:
            _c[i] = (get_data.ingredients.resolve_nutrition(i, use_cooked=False) or {}).get("name_fr") or ""
        except Exception:
            _c[i] = ""
    return _c[i]


# ingrédients dont la mention dans le texte n'est pas attendue
SKIP = ("water", "table_salt", "salt", "black_pepper", "white_pepper", "vegetable_stock")

# id (préfixe) -> mots acceptables dans le texte
BY_ID = {
    "blueberry": ["myrtille", "bleuet"], "bilberry": ["myrtille"], "wild_blueberry": ["myrtille"],
    "couscous": ["couscous", "semoule"], "sesame_tahini": ["tahin", "sesame"],
    "white_bread": ["pain", "baguette", "croutons", "mouillettes", "tartine"],
    "bread_": ["pain", "tartine", "croutons"], "brioche": ["brioche", "pain"],
    "masa_harina": ["masa", "farine de mais"], "allspice": ["jamaique", "quatre-epices", "allspice"],
    "lemon_grass": ["citronnelle", "citronelle"], "gochugaru": ["piment", "gochugaru"],
    "breadcrumbs": ["chapelure", "panko"], "phyllo": ["filo", "phyllo", "brick", "feuille"],
    "puff_pastry": ["feuilletee", "pate"], "shortcrust": ["brisee", "pate"],
    "urad_lentil": ["urad", "lentille"], "drumstick": ["moringa", "drumstick", "cassier"],
    "pasta_raw_dried": ["pates", "vermicelles", "spaghetti", "macaroni", "lasagne", "nouilles", "tagliatelle", "penne", "fusilli"],
    "whole_wheat_pasta": ["pates", "lasagne", "nouilles"],
    "rice_vermicelli": ["vermicelle", "nouilles", "riz"],
    "potato_gnocchi": ["gnocchi"], "hominy": ["mais", "hominy", "nixtamalise"],
    "pickles_cucumber": ["cornichon"], "potato_starch": ["fecule"],
    "hot_dog_bun": ["pain", "bun"], "red_kuri_squash": ["potimarron", "courge"],
    "jerusalem_artichoke": ["topinambour"], "green_chicory": ["chicoree", "frisee", "salade"],
    "prune_umeboshi": ["umeboshi"], "canola": ["colza", "huile"], "vegetable_oil": ["huile"],
    "lettuce": ["laitue", "salade", "feuille"], "vital_wheat_gluten": ["gluten"],
    "coconut_sugar": ["sucre"],
    "egg_pasta": ["pates", "spatzle", "nouilles"], "udon": ["udon", "nouilles"],
    "tomato_ketchup": ["ketchup"], "mixed_seaweed": ["algue", "nori", "dulse"],
    "nori": ["nori", "algue"], "wakame": ["wakame", "algue"],
    "agave_syrup": ["agave", "sirop"], "maple_syrup": ["erable", "sirop"],
    "vanilla": ["vanille"], "cornstarch": ["fecule", "maizena"], "corn_flour": ["farine de mais", "mais"],
    "cornmeal": ["semoule de mais", "mais", "polenta"], "rice_flour": ["farine de riz", "riz"],
    "glutinous_rice_flour": ["farine de riz", "riz gluant"], "white_glutinous_rice_flour": ["farine de riz", "riz gluant"],
    "wheat_flour": ["farine"], "rye_flour": ["seigle", "farine"], "almond_flour": ["amande"],
    "chickpea_flour": ["pois chiche", "farine"], "buckwheat_flour": ["sarrasin", "farine"],
    "durum_wheat_semolina": ["semoule"], "wheat_semolina": ["semoule"],
    "egg_": ["oeuf", "jaune", "blanc"], "duck_egg": ["oeuf"],
    "butter_sup80pct": ["beurre"], "ghee": ["ghee", "beurre"],
    "milk_liquid": ["lait"], "milk_powder": ["lait"], "condensed_milk": ["lait concentre", "lait"],
    "cream_": ["creme"], "creme_fraiche": ["creme"], "yogurt": ["yaourt"], "soybean_yogurt": ["yaourt"],
    "coconut_milk": ["lait de coco", "coco"], "coconut_flesh": ["coco"], "coconut_oil": ["huile", "coco"],
    "oat_milk": ["lait", "avoine"], "soy_milk": ["lait", "soja"], "almond_milk": ["lait", "amande"],
    "soy_sauce": ["soja", "tamari", "shoyu"], "tamarind": ["tamarin"],
    "peanut": ["cacahuete", "arachide"], "walnut": ["noix"], "cashew": ["cajou"],
    "pistachio": ["pistache"], "almond_raw": ["amande"], "pine_nut": ["pignon"],
    "hazelnut": ["noisette"], "sunflower_oil": ["huile"], "olive_oil": ["huile"],
    "sesame_oil": ["huile de sesame", "sesame"], "palm_oil": ["huile"], "rapeseed": ["huile"],
    "grapeseed": ["huile"], "corn_oil": ["huile"], "peanut_oil": ["huile"], "avocado_oil": ["huile"],
    "sugars": ["sucre"], "brown_sugar": ["sucre", "cassonade", "palme"], "honey": ["miel"],
    "molasses": ["melasse"], "vanilla_sugar": ["sucre"], "baking_powder": ["levure", "poudre", "bicarbonate"],
    "bakers_yeast": ["levure"], "nutritional_yeast": ["levure"],
    "red_hot_chili": ["piment"], "chilli": ["piment"], "chili_powder": ["piment", "chili"],
    "green_chili": ["piment"], "banana_pepper": ["piment"], "cayenne": ["piment", "cayenne"],
    "lime_juice": ["citron vert", "lime"], "lime_raw_juice": ["citron vert", "lime"],
    "lemon_juice": ["citron"], "lemon_peel": ["zeste", "citron"], "preserved_lemon": ["citron confit"],
    "orange_juice": ["orange"], "mint": ["menthe"], "spearmint": ["menthe"], "peppermint": ["menthe"],
    "coriander": ["coriandre"], "parsley": ["persil"], "dill": ["aneth"], "chives": ["ciboulette"],
    "basil": ["basilic"], "thyme": ["thym"], "rosemary": ["romarin"], "bay_leaf": ["laurier"],
    "sage": ["sauge"], "oregano": ["origan"], "tarragon": ["estragon"], "fenugreek": ["fenugrec"],
    "onion": ["oignon", "ciboule"], "green_onion": ["oignon vert", "ciboule", "cebette"],
    "shallot": ["echalote"], "leek": ["poireau"], "garlic": ["ail"], "ginger": ["gingembre"],
    "turmeric": ["curcuma"], "cumin": ["cumin"], "cardamom": ["cardamome"], "cinnamon": ["cannelle"],
    "clove": ["girofle"], "nutmeg": ["muscade"], "paprika": ["paprika"], "saffron": ["safran"],
    "star_anise": ["badiane", "anis"], "caraway": ["carvi"], "juniper": ["genievre"],
    "poppy": ["pavot"], "sumac": ["sumac"], "curry_powder": ["curry", "colombo", "massale"],
    "curry_leaf": ["curry", "kaloupile"], "mustard": ["moutarde"], "rose_water": ["eau de rose", "rose"],
    "roselle": ["hibiscus", "bissap", "oseille"], "coffee": ["cafe"], "tea_leaf": ["the"],
    "tofu": ["tofu"], "tempeh": ["tempeh"], "seitan": ["seitan"], "paneer": ["paneer"],
    "halloumi": ["halloumi"], "feta": ["feta", "fromage"], "mozzarella": ["mozzarella", "fromage"],
    "ricotta": ["ricotta", "fromage"], "parmesan": ["parmesan", "fromage"], "cheddar": ["cheddar", "fromage"],
    "gouda": ["gouda", "fromage"], "emmental": ["emmental", "fromage"], "comte": ["comte", "fromage"],
    "camembert": ["camembert", "fromage"], "queso": ["queso", "fromage"], "tomme": ["tome", "tomme", "fromage"],
    "goat_cheese": ["chevre", "fromage"], "cream_cheese": ["fromage"], "blue_cheese": ["bleu", "fromage"],
    "mascarpone": ["mascarpone"], "kefir": ["kefir"], "skyr": ["skyr"],
    "black_bean": ["haricot", "haricots"], "kidney_bean": ["haricot", "haricots"],
    "white_bean": ["haricot", "haricots"], "small_white_bean": ["haricot", "haricots"],
    "cranberry_bean": ["haricot"], "french_bean": ["haricot"], "broadbeans": ["feve", "gourgane"],
    "black_eyed_peas": ["dolique", "niebe", "cornille"], "split_peas": ["pois casse"],
    "chickpea": ["pois chiche"], "green_lentil": ["lentille"], "red_lentil": ["lentille", "corail"],
    "lentil": ["lentille"], "mung_bean": ["mungo", "soja", "germe", "pousse"],
    "soybean": ["soja"], "edamame": ["edamame", "soja"],
    "potato": ["pomme de terre", "patate"], "sweet_potato": ["patate douce"],
    "cassava": ["manioc"], "plantain": ["plantain", "banane"], "banana": ["banane"],
    "taro": ["taro"], "yam": ["igname"], "beetroot": ["betterave"], "carrot": ["carotte"],
    "cabbage": ["chou"], "red_cabbage": ["chou"], "savoy_cabbage": ["chou"], "kale": ["chou", "kale"],
    "curly_kale": ["chou", "kale"], "collard": ["chou"], "brussels": ["chou"],
    "cauliflower": ["chou-fleur", "chou fleur"], "broccoli": ["brocoli"], "spinach": ["epinard"],
    "mustard_raw_leaf": ["moutarde", "brede"], "swiss_chard": ["blette", "bette"],
    "zucchini": ["courgette"], "eggplant": ["aubergine"], "tomato_raw": ["tomate"],
    "tomato_paste": ["concentre", "tomate"], "tomato_concentrated": ["concentre", "tomate"],
    "tomato_dried": ["tomate sechee", "tomate confite", "tomate"], "bell_pepper": ["poivron"],
    "cucumber": ["concombre"], "chayote": ["chouchou", "christophine", "chayote"],
    "okra": ["gombo"], "mushroom": ["champignon"], "shiitake": ["shiitake", "champignon"],
    "oyster_mushroom": ["pleurote", "champignon"], "fennel": ["fenouil"], "celeriac": ["celeri"],
    "celery": ["celeri"], "rutabaga": ["rutabaga"], "turnip": ["navet"], "radish": ["radis"],
    "pumpkin": ["citrouille", "courge", "potiron"], "butternut": ["courge", "butternut"],
    "squash": ["courge"], "corn": ["mais"], "sweet_corn": ["mais"], "peas": ["pois"],
    "green_peas": ["pois"], "artichoke": ["artichaut"], "asparagus": ["asperge"],
    "avocado": ["avocat"], "apple": ["pomme"], "pear": ["poire"], "mango": ["mangue"],
    "papaya": ["papaye"], "pineapple": ["ananas"], "orange": ["orange"], "lime_raw": ["citron vert"],
    "grape": ["raisin"], "raisin": ["raisin"], "date_with_skin": ["datte"], "fig": ["figue"],
    "apricot": ["abricot"], "peach": ["peche"], "plum": ["prune", "pruneau"], "prune": ["pruneau"],
    "cherry": ["cerise", "griotte"], "sour_cherry": ["cerise", "griotte"],
    "strawberry": ["fraise"], "raspberry": ["framboise"], "blackberry": ["mure"],
    "cranberry": ["canneberge", "cranberr", "airelle"], "pomegranate": ["grenade"],
    "watermelon": ["pasteque"], "melon": ["melon"], "coconut": ["coco"], "olive": ["olive"],
    "caper": ["capre"], "pickle": ["cornichon", "pickle"], "vinegar": ["vinaigre"],
    "wine": ["vin"], "beer": ["biere"], "rum": ["rhum"], "cognac": ["cognac"],
    "chocolate": ["chocolat"], "cocoa": ["cacao"], "coffee_ground": ["cafe"],
    "rice": ["riz"], "quinoa": ["quinoa"], "bulgur": ["boulgour"], "freekeh": ["frik", "freekeh"],
    "barley": ["orge"], "oat": ["avoine", "flocons"], "millet": ["millet"], "teff": ["teff"],
    "buckwheat": ["sarrasin", "kasha"], "amaranth": ["amarante"], "tapioca": ["tapioca", "manioc"],
    "chia": ["chia"], "flax": ["lin"], "sesame_seed": ["sesame"], "black_sesame": ["sesame"],
    "sunflower_seed": ["tournesol"], "pumpkin_squash_raw_seed": ["courge"],
    "vine_leaf": ["vigne"], "grape_leave": ["vigne"], "kombu": ["kombu", "algue"],
    "miso": ["miso"], "natto": ["natto"], "gochujang": ["gochujang", "piment"],
    "doenjang": ["doenjang", "pate"], "fermented_bean_paste": ["pate", "doenjang"],
    "kimchi": ["kimchi"], "sauerkraut": ["choucroute"], "harissa": ["harissa"],
    "za_atar": ["za'atar", "zaatar"], "ras_el_hanout": ["ras el hanout", "ras-el-hanout"],
    "berbere": ["berbere"], "salted_crackers": ["cracker", "biscuit"],
    "flour": ["farine"], "all_purpose_flour": ["farine"], "bread_flour": ["farine", "pain"],
    "polenta": ["polenta", "semoule"], "capers": ["capre"], "aquafaba": ["aquafaba", "pois chiche"],
    "orange_blossom_water": ["oranger", "fleur"], "gruyere": ["gruyere", "fromage"],
    "sweet_and_sour_gherkin_flavored_pre_packaged": ["cornichon"],
    "chanterelle": ["girolle", "chanterelle", "champignon"], "morel": ["morille", "champignon"],
    "porcini": ["cepe", "champignon"], "enoki": ["enoki", "champignon"],
    "gelatin": ["gelatine"], "agar": ["agar"], "salt": ["sel"],
}
STOP = {"de", "du", "la", "le", "les", "d", "l", "en", "a", "au", "aux", "et", "cru", "crue", "sec", "seche"}


def keys_for(cid):
    # 1) alias explicite, uniquement sur un préfixe ou un segment complet de l'id
    segs = set(cid.split("_"))
    for k in sorted(BY_ID, key=len, reverse=True):      # 1a) préfixe de l'id
        if cid == k or cid.startswith(k + "_"):
            return BY_ID[k]
    for k in sorted(BY_ID, key=len, reverse=True):      # 1b) segment complet
        if ("_" + k + "_") in ("_" + cid + "_"):
            return BY_ID[k]
    for k in sorted(BY_ID, key=len, reverse=True):
        if "_" not in k and k in segs:
            return BY_ID[k]
    # 2) sinon, les mots du libellé français
    n = re.split(r"[(,]", norm(fr(cid)))[0].strip()
    words = [w for w in re.split(r"[^a-z]+", n) if w and w not in STOP]
    return words[-2:] if len(words) > 1 else words


def stem(w):
    w = w.strip()
    return w[:max(4, len(w) - 2)] if len(w) > 5 else w


def cited(keys, text):
    """un ingrédient est cité si le dernier mot significatif d'un de ses libellés apparaît."""
    for k in keys:
        parts = [w for w in re.split(r"[^a-z']+", k) if w and w not in STOP]
        if not parts:
            continue
        if all(stem(p) in text for p in parts[-1:]):
            return True
    return False


out = defaultdict(list)
UNIT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*(g|kg|ml|cl|l)\b")
for r in load_recipes():
    rid = r["id"]
    comp = [c for c in (r.get("composition") or [])
            if (c.get("meta") or {}).get("role") != "serving_suggestion" and c.get("quantity") is not None]
    text = norm(" ".join(r.get("instructions") or []))
    if not text:
        continue
    # ---- ingrédient jamais cité
    for c in comp:
        cid = c["ingredient"]
        if cid.startswith(SKIP):
            continue
        ks = keys_for(cid)
        if ks and not cited(ks, text):
            out["jamais_cite"].append(f"{rid} {cid} ({fr(cid)}) — mots cherchés {ks}")
    # ---- quantité du texte qui ne correspond à rien
    by_key = defaultdict(list)
    for c in comp:
        if c["ingredient"].startswith(("vegetable_stock", "water", "table_salt", "salt")):
            continue
        for k in keys_for(c["ingredient"]):
            q = float(c["quantity"])
            if (c.get("unit") or "") in ("kg", "l"):
                q *= 1000
            by_key[k].append(q)
    for m in UNIT_RE.finditer(text):
        v = float(m.group(1).replace(",", "."))
        if m.group(2) in ("kg", "l"):
            v *= 1000
        elif m.group(2) == "cl":
            v *= 10
        tail = text[m.end():m.end() + 45]
        for k, qs in by_key.items():
            if re.match(rf"\s+(?:de |d'|d’)?(?:[a-z']+\s+){{0,2}}{re.escape(k)}", tail):
                if not any(abs(v - q) <= max(q * 0.15, 2) or v <= q for q in qs):
                    out["quantite_texte"].append(
                        f"{rid} « {v:g} {m.group(2)} …{tail[:28]} » ; composition : {k} = {sorted(qs)}")
                break

rep = (Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv
       else Path(__file__).with_name("audit_text_coherence.txt"))
with rep.open("w", encoding="utf-8", newline="\n") as f:
    for k in sorted(out, key=lambda k: -len(out[k])):
        f.write(f"\n## {k} ({len(out[k])})\n")
        for l in out[k]:
            f.write(f"  {l}\n")
for k in sorted(out, key=lambda k: -len(out[k])):
    print(f"{len(out[k]):5d}  {k}")
print("→", rep)
