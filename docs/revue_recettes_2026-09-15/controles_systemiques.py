import json, re, sys, logging, collections
from pathlib import Path
ROOT = Path(r"C:\Users\Samijo\Downloads\project_final_v6_migrated\project_final_v6_migrated")
sys.path.insert(0, str(ROOT)); logging.disable(logging.CRITICAL)
from backend.core.data_io import load_recipes, load_nutrition_graph
from backend.engine import nutrition_engine as ne
from backend.engine.nutrition_engine import get_data
R = load_recipes(); NG = load_nutrition_graph()
def txt(r): return " ".join(r.get("instructions") or []).lower()
def comp(r): return [c for c in r.get("composition") or [] if (c.get("meta") or {}).get("role") != "serving_suggestion"]
out = collections.defaultdict(list)
for r in R:
    t = txt(r); ids = [c["ingredient"] for c in comp(r)]; rid = r["id"]
    flags = r.get("diet_flags") or {}
    # 1 legumes cuites mais texte cuit du sec
    for i in ids:
        if re.search(r"(lentil|bean|chickpea|pea|cowpea)s?_boiled|black_eyed_peas_cowpeas_boiled", i):
            if re.search(r"tremp|secs?\b|sèches|(\d{2,3}) ?min(utes)?[^.]*(tendre|fondant)|1 ?h", t) and re.search(r"tremp|sec|sèche|cuire|cuisez|mijot", t):
                if re.search(r"tremp|\bsecs?\b|sèches|lentilles[^.]{0,40}(\d{2}) ?min|rincer? \d+ ?g de lentilles", t):
                    out["legumineuse_cuite_pour_texte_sec"].append(rid); break
    # 2 riz cru + riz cuit dans le texte
    if any(re.match(r"white_rice_(raw|short)", i) for i in ids) and re.search(r"riz[^.]{0,40}(cuit|froid|de la veille)", t) and not re.search(r"cuire (le|les|\d+ ?g de) riz|faire cuire[^.]{0,20}riz|cuisez[^.]{0,20}riz", t):
        out["riz_cru_pour_riz_cuit"].append(rid)
    # 3 gabarit
    q = {c["ingredient"]: c.get("quantity") for c in comp(r)}
    tpl = sum([q.get("onion_raw") == 300 or q.get("yellow_onion_raw") == 300 or q.get("white_onion_raw") == 300,
               q.get("garlic_raw") == 9, q.get("tomato_raw_ripe") == 480,
               q.get("olive_oil_plant") == 45 or q.get("olive_oil_extra_virgin_plant") == 45,
               q.get("coriander_spice_seed") == 3, q.get("egg_raw") == 220, q.get("parmesan_grated_dried_cow") == 150])
    if tpl >= 3: out["gabarit_quantites_>=3"].append(rid)
    # 4 sel absent et sodium bas
    na = (NG.get(rid) or {}).get("sodium") or 0
    if r.get("dish_type") in ("main", "soup", "starter", "side") and "table_salt_unenriched" not in ids and na < 150:
        out["sel_absent_Na<150"].append(rid)
    # 5 kid_friendly + piment
    pim = sum((c.get("quantity") or 0) for c in comp(r) if re.search(r"chil|pepper_raw$|ancho|chili|piment|gochujang|pate_piment|kimchi", c["ingredient"]) and "bell" not in c["ingredient"] and "black_pepper" not in c["ingredient"])
    if flags.get("kid_friendly") and pim >= 10: out["kid_friendly_piment>=10g"].append(rid)
    # 6 raw + cuisson
    if flags.get("raw") and ((r.get("timing") or {}).get("cook_min") or 0) > 0 or (flags.get("raw") and re.search(r"cuit|frire|saisir|four|bouill", t)):
        out["regime_raw_avec_cuisson"].append(rid)
    # 7 temperature sur feu
    if re.search(r"(feu|mijot|frémiss|bouillon|poêle|wok|casserole)[^.]{0,40}(à|\() ?(environ )?1[0-9]0 ?°c", t): out["temperature_sur_feu"].append(rid)
    # 8 lame ressort seche hors patisserie
    if "ressort" in t and "sèche" in t and r.get("dish_type") not in ("dessert", "breakfast", "snack"): out["lame_ressort_seche_hors_gateau"].append(rid)
    # 9 bases sans libelle
    for i in ids:
        if i.startswith("base_"):
            try: n = get_data.ingredients.resolve_nutrition(i, use_cooked=False) or {}
            except Exception: n = {}
            if not n.get("name_fr"): out["base_sans_libelle"].append(rid); break
    # 10 huile < 5 ml
    for c in comp(r):
        if "oil" in c["ingredient"] and c.get("unit") in ("ml", "g") and (c.get("quantity") or 99) < 5 and r.get("dish_type") in ("main", "soup", "starter", "side"):
            out["huile_<5ml"].append(rid); break
    # 11 cook_min>0 sans cuisson
    if ((r.get("timing") or {}).get("cook_min") or 0) > 0 and not re.search(r"cui|four|poêle|saisir|bouill|frire|griller|revenir|chauff|mijot|blanch|toast|rôt|dorer|frém|réduire|vapeur", t):
        out["cook_min_sans_cuisson"].append(rid)
# doublons de titre normalisé
tit = collections.defaultdict(list)
for r in R:
    k = re.sub(r"\(vegan\)|vegan|végétarien(ne)?|classique|traditionnel(le)?|simple|optimisé|maîtrisé|structuré(e)?s?|[^a-zàâçéèêëîïôûù ]", "", ((r.get("titles") or {}).get("fr") or "").lower()).strip()
    k = " ".join(sorted(k.split()))
    tit[k].append(r["id"])
dups = {k: v for k, v in tit.items() if len(v) > 1}
res = {k: sorted(set(v)) for k, v in out.items()}
res["doublons_titre"] = dups
Path("systemic.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
for k, v in res.items(): print(k, len(v))
print("recettes dans groupes de doublons:", sum(len(v) for v in dups.values()))
