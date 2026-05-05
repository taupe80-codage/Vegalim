"""
build_taxonomy_html.py — Build complet : données + HTML v3 auto-contenu
Génère TOUTES les entrées depuis les 3 sources brutes.
Lance avec : python -X utf8 build_taxonomy_html.py
"""
import json, sys, os
sys.stdout.reconfigure(encoding="utf-8")

# ════════════════════════════════════════════════════════════════════
# 1. LOAD SOURCES
# ════════════════════════════════════════════════════════════════════
print("Loading source JSONs...")
BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE,"backend/data/nutrition/raw/ciqual_flat_v3.json"), encoding="utf-8") as f: ciqual = json.load(f)
with open(os.path.join(BASE,"backend/data/nutrition/raw/usda_flat_v2.json"),   encoding="utf-8") as f: usda   = json.load(f)
with open(os.path.join(BASE,"backend/data/nutrition/raw/cnf_full_v10.json"),   encoding="utf-8") as f: cnf    = json.load(f)
CG = ciqual.get("groups",{}); UG = usda.get("groups",{}); NG = cnf.get("groups",{})

# ════════════════════════════════════════════════════════════════════
# 2. GROUP + SUBGROUP DEFINITIONS
# ════════════════════════════════════════════════════════════════════
RULES = [
  {"id":"G01","label":"Algues & Champignons","l2codes":["1007"],"subgroups":[
     {"id":"sg_algues","label":"Algues & Algues marines","m":lambda bk,g: True}]},
  {"id":"G01c","label":"Champignons","l2codes":[],"subgroups":[
     {"id":"sg_champignons","label":"Champignons","m":lambda bk,g: True}]},
  {"id":"G02","label":"Boissons alcoolisées","l2codes":["603"],"subgroups":[
     {"id":"sg_alcool","label":"Alcools & Spiritueux","m":lambda bk,g: True}]},
  {"id":"G03","label":"Boissons non alcoolisées","l2codes":["601","602"],"subgroups":[
     {"id":"sg_eau","label":"Eaux","m":lambda bk,g: "601." in str(g.get("category",{}).get("level2_code",""))},
     {"id":"sg_boisson_na","label":"Boissons sans alcool","m":lambda bk,g: True}]},
  {"id":"G04","label":"Céréales & Grains","l2codes":["301","304"],"subgroups":[
     {"id":"sg_pates","label":"Pâtes, Riz & Céréales","m":lambda bk,g: any(x in bk for x in ["pate","riz","rice","pasta","noodle","quinoa","orge","millet","sorgho","avoine","oat","couscous","boulgour","grain","cereal"])},
     {"id":"sg_farines","label":"Farines & Amidons","m":lambda bk,g: True}]},
  {"id":"G04b","label":"Pain, Pâtisseries & Viennoiseries","l2codes":["302","305"],"subgroups":[
     {"id":"sg_pain","label":"Pains","m":lambda bk,g: any(x in bk for x in ["pain","bread","baguette","brioche","bagel","focaccia","naan","tortilla","pitta"])},
     {"id":"sg_viennoiserie","label":"Viennoiseries & Pâtisseries","m":lambda bk,g: True}]},
  {"id":"G05","label":"Chocolat & Confiseries","l2codes":["702","703"],"subgroups":[
     {"id":"sg_chocolat","label":"Chocolat & Cacao","m":lambda bk,g: any(x in bk for x in ["chocolat","chocolate","cacao","cocoa"])},
     {"id":"sg_confiserie","label":"Confiseries","m":lambda bk,g: True}]},
  {"id":"G06","label":"Condiments, Herbes & Épices","l2codes":["1001","1002","1004","1005","1006"],"subgroups":[
     {"id":"sg_herbes","label":"Herbes aromatiques","m":lambda bk,g: "1006." in str(g.get("category",{}).get("level2_code",""))},
     {"id":"sg_epices","label":"Épices","m":lambda bk,g: "1005." in str(g.get("category",{}).get("level2_code",""))},
     {"id":"sg_condiments","label":"Condiments & Sauces","m":lambda bk,g: True}]},
  {"id":"G07","label":"Corps gras — Beurres & Margarines","l2codes":["901","903"],"subgroups":[
     {"id":"sg_beurre","label":"Beurres & Margarines","m":lambda bk,g: True}]},
  {"id":"G08","label":"Corps gras — Huiles","l2codes":["902"],"subgroups":[
     {"id":"sg_huile","label":"Huiles végétales","m":lambda bk,g: True}]},
  {"id":"G09","label":"Fromages","l2codes":["503"],"subgroups":[
     {"id":"sg_ppcu","label":"Pâte pressée cuite (dure)","m":lambda bk,g: any(x in bk for x in ["comte","cantal","beaufort","emmental","gruyere","parmesan","appenzell","abondance","beaumont","swiss"])},
     {"id":"sg_ppncu","label":"Pâte pressée non cuite","m":lambda bk,g: any(x in bk for x in ["gouda","edam","cheddar","provolone","colby","mimolette","raclette","tomme","saint_nectaire"])},
     {"id":"sg_pmfl","label":"Pâte molle — Croûte fleurie","m":lambda bk,g: any(x in bk for x in ["camembert","brie","coulommiers","chaource","neufchatel","chevre","fromage_de_chevre"])},
     {"id":"sg_pmlav","label":"Pâte molle — Croûte lavée","m":lambda bk,g: any(x in bk for x in ["munster","livarot","maroilles","epoisses","pont","reblochon","vacherin"])},
     {"id":"sg_pers","label":"Pâte persillée (bleu)","m":lambda bk,g: any(x in bk for x in ["roquefort","bleu","blue","gorgonzola","fourme","stilton"])},
     {"id":"sg_frais_ff","label":"Fromages frais & Cottage","m":lambda bk,g: any(x in bk for x in ["fromage_blanc","fromage_frais","ricotta","mascarpone","cottage","petit_suisse","quark","skyr","cream_cheese"])},
     {"id":"sg_fr_etr","label":"Fromages étrangers & Spéciaux","m":lambda bk,g: True}]},
  {"id":"G10","label":"Fruits tempérés","l2codes":[],"subgroups":[
     {"id":"sg_pommes","label":"Pommes & Poires","m":lambda bk,g: any(x in bk for x in ["pomme","poire","apple","pear","coing","quince"])},
     {"id":"sg_baies","label":"Baies & Petits fruits","m":lambda bk,g: any(x in bk for x in ["fraise","framboise","myrtille","groseille","cassis","mure","airelle","strawberry","raspberry","blueberry","blackberry","cherry","cerise","cranberry"])},
     {"id":"sg_prunes","label":"Prunes & Drupes","m":lambda bk,g: any(x in bk for x in ["prune","peche","abricot","nectarine","plum","peach","apricot","brugnon","mirabelle"])},
     {"id":"sg_raisin_melon","label":"Raisin & Melon","m":lambda bk,g: any(x in bk for x in ["raisin","melon","pasteque","grape","watermelon"])},
     {"id":"sg_fruits_temp_autres","label":"Autres fruits tempérés","m":lambda bk,g: True}]},
  {"id":"G11","label":"Agrumes","l2codes":[],"subgroups":[
     {"id":"sg_agrumes","label":"Agrumes","m":lambda bk,g: True}]},
  {"id":"G12","label":"Fruits tropicaux & Exotiques","l2codes":[],"subgroups":[
     {"id":"sg_trop","label":"Fruits tropicaux","m":lambda bk,g: True}]},
  {"id":"G13","label":"Oléagineux & Fruits à coque","l2codes":["205"],"subgroups":[
     {"id":"sg_noix","label":"Noix & Noisettes","m":lambda bk,g: any(x in bk for x in ["noix","noisette","walnut","hazelnut","pecan","chestnut","chataigne","noix_de_coco"])},
     {"id":"sg_amandes","label":"Amandes, Pistaches & Cajou","m":lambda bk,g: any(x in bk for x in ["amande","pistache","almond","pistachio","cashew","cajou","cacahouete","peanut"])},
     {"id":"sg_graines_ol","label":"Graines oléagineuses","m":lambda bk,g: True}]},
  {"id":"G14","label":"Légumes-feuilles & Salades","l2codes":[],"subgroups":[
     {"id":"sg_laitue","label":"Laitues, Salades & Épinards","m":lambda bk,g: any(x in bk for x in ["laitue","salade","roquette","epinard","endive","cresson","mache","radicchio","chicory","lettuce","spinach","watercress","arugula"])},
     {"id":"sg_feuilles_veg","label":"Feuilles de légumes","m":lambda bk,g: any(x in bk for x in ["blette","bette","beet_green","kale","oseille","sorrel"])},
     {"id":"sg_herbes_fraich","label":"Herbes fraîches","m":lambda bk,g: any(x in bk for x in ["persil","ciboulette","coriandre","basilic","parsley","chive","cilantro","basil","mint","menthe","estragon","tarragon","aneth","dill"])},
     {"id":"sg_legfeuilles_autres","label":"Autres","m":lambda bk,g: True}]},
  {"id":"G15","label":"Légumes-fruits","l2codes":[],"subgroups":[
     {"id":"sg_tomate","label":"Tomates","m":lambda bk,g: "tomate" in bk or "tomato" in bk},
     {"id":"sg_poivron","label":"Poivrons & Piments","m":lambda bk,g: any(x in bk for x in ["poivron","piment","pepper","capsicum","jalapeno","chili","chile"])},
     {"id":"sg_avocats","label":"Avocats & Olives","m":lambda bk,g: any(x in bk for x in ["avocat","olive","avocado"])},
     {"id":"sg_aubergine","label":"Aubergines & Okras","m":lambda bk,g: any(x in bk for x in ["aubergine","eggplant","okra","gombo"])},
     {"id":"sg_legfruits_autres","label":"Autres légumes-fruits","m":lambda bk,g: True}]},
  {"id":"G16","label":"Légumes-racines & Tubercules","l2codes":["202"],"subgroups":[
     {"id":"sg_pdterre","label":"Pomme de terre","m":lambda bk,g: "pomme_de_terre" in bk or "potato" in bk or "fecule" in bk or "flocon" in bk},
     {"id":"sg_racines","label":"Racines & Tubercules divers","m":lambda bk,g: any(x in bk for x in ["carotte","panais","betterave","radis","navet","carrot","parsnip","beet","turnip","radish","celeriac","celeri_rave","manioc","cassava","igname","yam","patate","sweet_potato","taro","choux_rave","kohlrabi","salsifis","parsley_root"])},
     {"id":"sg_allium","label":"Alliacés","m":lambda bk,g: any(x in bk for x in ["oignon","ail","echalote","poireau","onion","garlic","shallot","leek","scallion","chive","ciboulette"])},
     {"id":"sg_racines_autres","label":"Autres racines","m":lambda bk,g: True}]},
  {"id":"G17","label":"Légumes-tiges, Choux & Cucurbitacées","l2codes":[],"subgroups":[
     {"id":"sg_brassicas","label":"Brassicacées & Choux","m":lambda bk,g: any(x in bk for x in ["brocoli","broccoli","chou","cauliflower","chou_fleur","brussel","choux_bruxelles","cabbage","kale","kohlrabi","bok_choy","bok","romanesco"])},
     {"id":"sg_cucurbit","label":"Cucurbitacées","m":lambda bk,g: any(x in bk for x in ["courgette","concombre","squash","pumpkin","courge","zucchini","cucumber","gourd","melon_amer"])},
     {"id":"sg_asperge","label":"Asperges","m":lambda bk,g: "asperge" in bk or "asparagus" in bk},
     {"id":"sg_artichaut","label":"Artichauts & Fenouil","m":lambda bk,g: any(x in bk for x in ["artichaut","artichoke","fenouil","fennel","rhubarb"])},
     {"id":"sg_tiges_autres","label":"Autres légumes-tiges","m":lambda bk,g: True}]},
  {"id":"G18","label":"Légumineuses","l2codes":["203"],"subgroups":[
     {"id":"sg_haricots","label":"Haricots","m":lambda bk,g: any(x in bk for x in ["haricot","bean","kidney","flageolet","mungo","adzuki","navy","pinto"])},
     {"id":"sg_lentilles","label":"Lentilles, Pois & Fèves","m":lambda bk,g: any(x in bk for x in ["lentille","pois","feve","chickpea","pois_chiche","lentil","split_pea","black_eyed","dal"])},
     {"id":"sg_soja_leg","label":"Soja, Tofu & Édamame","m":lambda bk,g: any(x in bk for x in ["soja","soy","edamame","tofu","tempeh","miso"])},
     {"id":"sg_leg_autres","label":"Autres légumineuses","m":lambda bk,g: True}]},
  {"id":"G19","label":"Lait, Yaourts & Boissons laitières","l2codes":["501","502","504"],"subgroups":[
     {"id":"sg_lait","label":"Laits","m":lambda bk,g: any(x in bk for x in ["lait","milk"]) and not any(x in bk for x in ["chocolat","fraise","cacao","coco","amande","soja","avoine","riz","oat"])},
     {"id":"sg_yaourt","label":"Yaourts & Kéfir","m":lambda bk,g: any(x in bk for x in ["yaourt","yogurt","yoghurt","kefir","lassi","skyr"])},
     {"id":"sg_creme","label":"Crèmes","m":lambda bk,g: any(x in bk for x in ["creme","cream","chantilly","fraiche"])},
     {"id":"sg_boisson_veg","label":"Boissons végétales & Laits alternatifs","m":lambda bk,g: True}]},
  {"id":"G20","label":"Œufs","l2codes":["410"],"subgroups":[
     {"id":"sg_oeufs","label":"Œufs","m":lambda bk,g: True}]},
  {"id":"G21","label":"Protéines végétales & Substituts","l2codes":["1009"],"subgroups":[
     {"id":"sg_prot_veg","label":"Protéines végétales","m":lambda bk,g: True}]},
  {"id":"G22","label":"Sucres, Confitures & Miels","l2codes":["701","704"],"subgroups":[
     {"id":"sg_sucres","label":"Sucres & Édulcorants","m":lambda bk,g: any(x in bk for x in ["sucre","sugar","miel","honey","sirop","syrup","fructose","glucose","agave","stevia","maltose","lactose","dextrose"])},
     {"id":"sg_confitures","label":"Confitures, Gelées & Compotes","m":lambda bk,g: True}]},
  {"id":"G23","label":"Viandes & Charcuteries","l2codes":[],"subgroups":[
     {"id":"sg_viande_rouge","label":"Viandes rouges","m":lambda bk,g: any(x in bk for x in ["boeuf","veau","agneau","porc","beef","veal","lamb","pork","mutton","venison","gibier","lapin","rabbit","cheval","horse"])},
     {"id":"sg_volaille","label":"Volailles","m":lambda bk,g: any(x in bk for x in ["poulet","dinde","canard","chicken","turkey","duck","goose","oie","pintade","caille","quail"])},
     {"id":"sg_charcuterie","label":"Charcuteries & Préparations","m":lambda bk,g: any(x in bk for x in ["saucisse","jambon","boudin","bacon","saucisson","mortadelle","salami","chorizo","lardons","ham","sausage","pepperoni","pancetta","prosciutto"])},
     {"id":"sg_viande_autres","label":"Autres viandes & Abats","m":lambda bk,g: True}]},
  {"id":"G24","label":"Poissons & Fruits de mer","l2codes":[],"subgroups":[
     {"id":"sg_poisson_gras","label":"Poissons gras","m":lambda bk,g: any(x in bk for x in ["saumon","thon","maquereau","sardine","anchois","hareng","salmon","tuna","mackerel","herring","anchovy","anguille","eel"])},
     {"id":"sg_poisson_maigre","label":"Poissons maigres","m":lambda bk,g: any(x in bk for x in ["cabillaud","sole","merlu","lieu","dorade","bar","brochet","carpe","cod","haddock","halibut","tilapia","trout","truite","perch","bass","flounder","catfish"])},
     {"id":"sg_crustaces","label":"Crustacés & Coquillages","m":lambda bk,g: any(x in bk for x in ["crevette","homard","crabe","langoustine","moule","huitre","coquille","shrimp","lobster","crab","mussel","oyster","clam","scallop","calamar","squid","octopus","poulpe"])},
     {"id":"sg_poisson_autres","label":"Autres poissons & produits","m":lambda bk,g: True}]},
  {"id":"G25","label":"Divers & Aides culinaires","l2codes":["1003"],"subgroups":[
     {"id":"sg_divers","label":"Aides culinaires & Divers","m":lambda bk,g: True}]},
]

# ── Build lookup maps ──────────────────────────────────────────────────────────
L2_TO_GID = {}
for r in RULES:
    for code in r["l2codes"]:
        L2_TO_GID[code] = r["id"]

GRP = {r["id"]: {"id":r["id"],"label":r["label"],
       "subgroups":[{"id":sg["id"],"label":sg["label"]} for sg in r["subgroups"]],
       "entries":[]} for r in RULES}

# ── Auto-routing helpers ───────────────────────────────────────────────────────
def _veg_route(bk):
    if any(x in bk for x in ["mushroom","champignon"]): return "G01c"
    if any(x in bk for x in ["spinach","epinard","lettuce","laitue","cress","cresson","arugula","roquette","chard","blette","kale","bette","mache","endive","chicory","radicchio","watercress"]): return "G14"
    if any(x in bk for x in ["tomato","tomate","pepper","poivron","piment","capsicum","eggplant","aubergine","okra","gombo","olive","avocado","avocat"]): return "G15"
    if any(x in bk for x in ["potato","pomme_de_terre","carrot","garlic","onion","leek","beet","radish","turnip","parsnip","celeriac","igname","yam","manioc","taro","sweet_potato","patate","shallot","echalote"]): return "G16"
    if any(x in bk for x in ["broccoli","brocoli","cauliflower","chou","cabbage","kale","brussels","asparagus","asperge","artichoke","artichaut","fennel","fenouil","courgette","cucumber","squash","pumpkin","zucchini","concombre","courge"]): return "G17"
    if any(x in bk for x in ["bean","lentil","pea","chickpea","soy","edamame","tofu"]): return "G18"
    return "G17"

def _fruit_route(bk):
    if any(x in bk for x in ["orange","lemon","lime","grapefruit","mandarin","citrus","clementine","tangerine","pomelo","bergamot","yuzu"]): return "G11"
    if any(x in bk for x in ["mango","mangue","banana","banane","pineapple","ananas","papaya","papaye","guava","goyave","coconut","noix_de_coco","kiwi","fig","figue","date","datte","lychee","passion","jackfruit","durian","carambola"]): return "G12"
    return "G10"

def _alcool_bk(bk):
    return any(x in bk for x in ["beer","wine","spirit","whisky","vodka","rum","gin","ale","lager","cider","champagne","brandy","cognac","armagnac","porto","sake","mead","liqueur","absinthe","schnapps"])

# ── Group resolver ─────────────────────────────────────────────────────────────
def resolve_gid_ciqual(bk, cg):
    l3f = (cg.get("category",{}).get("level3_fr","") or "").lower()
    if "champignon" in l3f: return "G01c"
    l2c = str(cg.get("category",{}).get("level2_code","")).split(".")[0]
    return L2_TO_GID.get(l2c, "G25")

def resolve_gid_usda(bk, ug):
    cat = ((ug.get("category",{}).get("level1_fr","") or ug.get("category",{}).get("level1_en","")) or "").lower()
    if "légume" in cat or "vegetable" in cat or "plant" in cat: return _veg_route(bk)
    if "légumineuse" in cat or "legume" in cat or "bean" in cat: return "G18"
    if "matière grasse" in cat or "fat" in cat or "oil" in cat: return "G08" if ("oil" in bk or "huile" in bk) else "G07"
    if "noix" in cat or "nut" in cat or "seed" in cat or "grain" in cat and "oilseed" in cat: return "G13"
    if "laitier" in cat or "dairy" in cat:
        if "egg" in bk or "oeuf" in bk: return "G20"
        if "cheese" in bk or "fromage" in bk: return "G09"
        return "G19"
    if "oeuf" in cat or "egg" in cat: return "G20"
    if "céréale" in cat or "grain" in cat or "cereal" in cat or "bread" in cat or "pasta" in cat:
        return "G04b" if any(x in bk for x in ["bread","pain","cake","cookie","cracker","muffin","pastry","biscuit","pretzel","roll","bun"]) else "G04"
    if "fruit" in cat: return _fruit_route(bk)
    if "sucre" in cat or "sweet" in cat or "confis" in cat or "sugar" in cat:
        return "G05" if ("chocolat" in bk or "chocolate" in bk) else "G22"
    if "boisson" in cat or "beverage" in cat or "drink" in cat:
        return "G02" if _alcool_bk(bk) else "G03"
    if "épice" in cat or "spice" in cat or "herb" in cat or "condiment" in cat: return "G06"
    if "fish" in cat or "seafood" in cat or "shellfish" in cat or "poisson" in cat: return "G24"
    if "meat" in cat or "poultry" in cat or "viande" in cat or "volaille" in cat or "charcuterie" in cat: return "G23"
    if "mushroom" in cat or "champignon" in cat: return "G01c"
    if "seaweed" in cat or "algue" in cat: return "G01"
    return "G25"

def resolve_gid_cnf(bk, ng):
    cat = ((ng.get("category",{}).get("level1_en","") or ng.get("category",{}).get("level1_fr","")) or "").lower()
    if "vegetable" in cat or "légume" in cat: return _veg_route(bk)
    if "legume" in cat or "légumineuse" in cat: return "G18"
    if "fat" in cat or "oil" in cat: return "G08" if ("oil" in bk) else "G07"
    if "nut" in cat or "seed" in cat: return "G13"
    if "dairy" in cat or "laitier" in cat:
        if "egg" in bk: return "G20"
        if "cheese" in bk: return "G09"
        return "G19"
    if "egg" in cat or "oeuf" in cat: return "G20"
    if "grain" in cat or "cereal" in cat or "bread" in cat or "baked" in cat:
        return "G04b" if any(x in bk for x in ["bread","cake","cookie","cracker","muffin","pastry","biscuit","crouton","matzo"]) else "G04"
    if "fruit" in cat: return _fruit_route(bk)
    if "sweet" in cat or "sugar" in cat or "candy" in cat or "confec" in cat:
        return "G05" if "chocolate" in bk else "G22"
    if "beverage" in cat or "drink" in cat:
        return "G02" if _alcool_bk(bk) else "G03"
    if "spice" in cat or "herb" in cat or "condiment" in cat: return "G06"
    if "fish" in cat or "shellfish" in cat or "seafood" in cat or "crustac" in cat: return "G24"
    if "meat" in cat or "poultry" in cat or "game" in cat: return "G23"
    if "mushroom" in cat or "fungi" in cat: return "G01c"
    if "seaweed" in cat or "algae" in cat: return "G01"
    if "meal" in cat or "dish" in cat or "prepared" in cat or "soup" in cat: return "G25"
    return "G25"

# ── Subgroup assigner ─────────────────────────────────────────────────────────
def assign_sg(gid, bk, cgroup):
    rule = next((r for r in RULES if r["id"]==gid), None)
    if not rule: return ""
    for sg in rule["subgroups"]:
        try:
            if sg["m"](bk, cgroup): return sg["id"]
        except: pass
    return ""

# ════════════════════════════════════════════════════════════════════
# 3. BUILD TAXONOMY (all entries from all 3 sources)
# ════════════════════════════════════════════════════════════════════
print("Building taxonomy from sources...")

# bk_place : bk -> (gid, entry_ref)  — first source wins, others just add badge
bk_place = {}  # bk -> gid

# CIQUAL special: separate mushrooms from algues
CIQUAL_MUSH = {bk for bk,cg in CG.items()
               if "champignon" in (cg.get("category",{}).get("level3_fr","") or "").lower()}

for bk, cg in sorted(CG.items()):
    gid = "G01c" if bk in CIQUAL_MUSH else resolve_gid_ciqual(bk, cg)
    sgid = assign_sg(gid, bk, cg)
    info = {"name_fr":cg.get("name_fr","")or"","name_en":cg.get("name_en","")or"","leaves":cg.get("_meta",{}).get("leaf_count",0)}
    if bk not in bk_place:
        GRP[gid]["entries"].append({"bk":bk,"sources":["CIQUAL"],"canon":bk,"sg":sgid,**info})
        bk_place[bk] = gid
    else:
        placed_gid = bk_place[bk]
        for e in GRP[placed_gid]["entries"]:
            if e["bk"]==bk and "CIQUAL" not in e["sources"]: e["sources"].append("CIQUAL"); break

for bk, ug in sorted(UG.items()):
    gid = resolve_gid_usda(bk, ug)
    sgid = assign_sg(gid, bk, ug)
    info = {"name_fr":ug.get("name_fr","")or"","name_en":ug.get("name_en","")or"","leaves":ug.get("_meta",{}).get("leaf_count",0)}
    if bk not in bk_place:
        GRP[gid]["entries"].append({"bk":bk,"sources":["USDA"],"canon":bk,"sg":sgid,**info})
        bk_place[bk] = gid
    else:
        placed_gid = bk_place[bk]
        for e in GRP[placed_gid]["entries"]:
            if e["bk"]==bk and "USDA" not in e["sources"]: e["sources"].append("USDA"); break

for bk, ng in sorted(NG.items()):
    gid = resolve_gid_cnf(bk, ng)
    sgid = assign_sg(gid, bk, ng)
    info = {"name_fr":ng.get("name_fr","")or"","name_en":ng.get("name_en","")or"","leaves":ng.get("_meta",{}).get("leaf_count",0)}
    if bk not in bk_place:
        GRP[gid]["entries"].append({"bk":bk,"sources":["CNF"],"canon":bk,"sg":sgid,**info})
        bk_place[bk] = gid
    else:
        placed_gid = bk_place[bk]
        for e in GRP[placed_gid]["entries"]:
            if e["bk"]==bk and "CNF" not in e["sources"]: e["sources"].append("CNF"); break

TAXONOMY = [g for g in sorted(GRP.values(), key=lambda x: x["id"]) if g["entries"]]
total_entries = sum(len(g["entries"]) for g in TAXONOMY)
print(f"Taxonomy: {len(TAXONOMY)} groups, {total_entries} entries")

# ════════════════════════════════════════════════════════════════════
# PART 2: VARIANT EXTRACTION — append from saved part2
# ════════════════════════════════════════════════════════════════════

# ════════════════════════════════════════════════════════════════════════════════
# 2. VARIANT DATA EXTRACTION
# ════════════════════════════════════════════════════════════════════════════════

def _s(v):
    return v if (v is not None and str(v) not in ("null","None","")) else None

def walk_tree(tree, src_name, depth=0):
    entries = []
    for key, node in (tree or {}).items():
        if not isinstance(node, dict): continue
        state = node.get("state") or {}
        proc  = state.get("process") or {}
        # gather extension fields
        ext_fields = ["variety","preservation","physical_form","part",
                      "fat_level","fat_pct","maturity","dairy_process","species"]
        exts = {}
        for ef in ext_fields:
            v = state.get(ef)
            if v is None: v = (state.get("extensions") or {}).get(ef)
            if v is not None: exts[ef] = str(v)

        entry = {
            "k":    key,
            "d":    depth,
            "t":    node.get("type","?"),        # leaf / node
            "dim":  node.get("dimension",""),
            "src":  src_name,
            "sid":  _s(node.get("source_id")),
            "lbl":  _s(node.get("source_label")),
            "l1":   _s(proc.get("level1")),
            "l2":   _s(proc.get("level2")),
            "conf": proc.get("confidence"),
            "frag": _s(proc.get("raw_label_fragment")),
        }
        entry.update(exts)
        ch = node.get("children") or {}
        if ch: entry["ch"] = walk_tree(ch, src_name, depth+1)
        entries.append(entry)
    return entries

# Build canonical → {src → {bk → [variants]}}
print("Extracting variants...")
VARIANTS = {}

# Build canonical map from taxonomy
BK2CANON = {e["bk"]: e["canon"] for g in TAXONOMY for e in g["entries"]}

def process_source(src_name, groups):
    for bk, grp in groups.items():
        vtree = grp.get("variants") or {}
        if not vtree: continue
        canon = BK2CANON.get(bk, bk)
        if canon not in VARIANTS: VARIANTS[canon] = {}
        if src_name not in VARIANTS[canon]: VARIANTS[canon][src_name] = {}
        VARIANTS[canon][src_name][bk] = walk_tree(vtree, src_name)

process_source("CIQUAL", CG)
process_source("USDA",   UG)
process_source("CNF",    NG)

def count_leaves(entries):
    n = 0
    for e in entries:
        if e.get("t") == "leaf": n += 1
        n += count_leaves(e.get("ch", []))
    return n

total_leaves = sum(count_leaves(v) for src_dict in VARIANTS.values() for bk_dict in src_dict.values() for v in bk_dict.values())
print(f"Variants: {len(VARIANTS)} canonicals, ~{total_leaves} leaves")

# ════════════════════════════════════════════════════════════════════════════════
# 3. GENERATE HTML
# ════════════════════════════════════════════════════════════════════════════════

print("Generating HTML...")
taxonomy_json  = json.dumps(TAXONOMY,  ensure_ascii=False, separators=(",",":"))
variants_json  = json.dumps(VARIANTS,  ensure_ascii=False, separators=(",",":"))

HTML = r"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8"/>
<title>Taxonomie Unifiée v3</title>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet"/>
<style>
:root{
  --bg:#0a0c18;--bg2:#111323;--bg3:#181b2e;--bg4:#1f2340;--bg5:#252a48;
  --border:#2a2f52;--border2:#353b65;
  --accent:#6366f1;--accent2:#818cf8;--accent3:#4f46e5;
  --green:#22c55e;--green2:#16a34a;--red:#ef4444;--amber:#f59e0b;
  --cyan:#22d3ee;--violet:#a855f7;--rose:#fb7185;
  --text:#e2e8f0;--muted:#94a3b8;--dim:#475569;--dimmer:#334155;
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Inter',sans-serif;background:var(--bg);color:var(--text);min-height:100vh;font-size:13px;overflow:hidden}

/* HEADER */
header{height:52px;background:var(--bg2);border-bottom:1px solid var(--border);display:flex;align-items:center;padding:0 18px;gap:16px;flex-shrink:0;z-index:50}
.logo{font-size:16px;font-weight:700;background:linear-gradient(135deg,#6366f1,#a78bfa);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.logo-sub{font-size:10px;color:var(--dim)}
.tabs{display:flex;gap:3px;background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:3px}
.tab{padding:5px 13px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:500;color:var(--muted);transition:all .15s;border:none;background:none}
.tab.active{background:var(--accent);color:#fff}
.tab:hover:not(.active){color:var(--text);background:var(--bg4)}
.stats-bar{margin-left:auto;display:flex;gap:7px;align-items:center}
.sb{background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:3px 9px;font-size:11px;color:var(--muted)}
.sb strong{color:var(--text)}
.btn-p{background:var(--accent);border:none;color:#fff;padding:6px 13px;border-radius:7px;font-size:12px;font-weight:600;cursor:pointer}
.btn-p:hover{background:var(--accent2)}
.btn-s{background:var(--bg3);border:1px solid var(--border);color:var(--muted);padding:5px 11px;border-radius:6px;font-size:11px;cursor:pointer}
.btn-s:hover{color:var(--text);border-color:var(--border2)}

/* PAGES */
.page{display:none;height:calc(100vh - 52px);overflow:hidden}
.page.active{display:flex}

/* ═══ SHARED SIDEBAR TREE ═══ */
.tree-panel{width:220px;min-width:220px;background:var(--bg2);border-right:1px solid var(--border);overflow-y:auto;display:flex;flex-direction:column;flex-shrink:0}
.tree-search{padding:9px 11px;border-bottom:1px solid var(--border)}
.tree-search input{width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 9px;border-radius:6px;font-size:12px}
.tree-search input:focus{outline:none;border-color:var(--accent)}
.tree-item{cursor:pointer;border-left:3px solid transparent}
.tree-item.active{border-left-color:var(--accent)}
.tree-group{padding:7px 11px;display:flex;align-items:center;gap:7px;border-bottom:1px solid var(--border)}
.tree-group:hover,.tree-item.active .tree-group{background:var(--bg3)}
.tree-gid{font-family:'JetBrains Mono',monospace;font-size:9px;color:var(--dim);min-width:28px}
.tree-glabel{flex:1;font-size:12px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tree-cnt{font-size:10px;color:var(--dim);background:var(--bg4);padding:1px 5px;border-radius:3px}
.tree-subs{padding:0 0 3px 18px;display:none}
.tree-item.open .tree-subs{display:block}
.tree-sub{padding:4px 9px;font-size:11px;color:var(--muted);cursor:pointer;border-radius:4px;display:flex;align-items:center;gap:5px}
.tree-sub:hover,.tree-sub.active{background:var(--bg4);color:var(--text)}
.tree-sub.active{background:var(--accent3);color:#fff}
.tree-sub-cnt{font-size:9px;background:rgba(255,255,255,.1);padding:1px 4px;border-radius:3px;margin-left:auto}

/* ═══ PAGE 1 — GROUPES ═══ */
#pg-groups{flex-direction:row}
.detail-panel{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.detail-header{background:var(--bg2);border-bottom:1px solid var(--border);padding:11px 18px;display:flex;align-items:center;gap:10px;flex-shrink:0}
.detail-gid-input{font-family:'JetBrains Mono',monospace;font-size:10px;background:var(--bg3);border:1px solid var(--border);color:var(--dim);padding:2px 6px;border-radius:4px;width:75px}
.detail-gid-input:focus{outline:none;border-color:var(--accent);color:var(--text)}
.editable-title{font-size:16px;font-weight:700;background:transparent;border:none;color:var(--text);padding:0;line-height:1.3;flex:1}
.editable-title:focus{outline:none;border-bottom:1px solid var(--accent)}
.sgs-area{flex:1;overflow-y:auto;padding:14px}
.sgs-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:11px;align-items:start}
.add-sg-btn{border:2px dashed var(--border);border-radius:10px;padding:18px;text-align:center;cursor:pointer;color:var(--dim);font-size:12px}
.add-sg-btn:hover{border-color:var(--accent);color:var(--accent2)}
.sg-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;overflow:hidden}
.sg-card:hover{border-color:var(--border2)}
.sg-card-header{background:var(--bg3);padding:9px 13px;display:flex;align-items:center;gap:7px}
.sg-name-input{flex:1;background:transparent;border:none;color:var(--text);font-size:12px;font-weight:600;padding:0}
.sg-name-input:focus{outline:none;border-bottom:1px solid var(--accent2)}
.sg-id-input{font-family:'JetBrains Mono',monospace;font-size:9px;background:var(--bg4);border:1px solid var(--border);color:var(--dim);padding:2px 5px;border-radius:3px;width:110px}
.sg-id-input:focus{outline:none;border-color:var(--accent);color:var(--text)}
.sg-del{background:none;border:none;color:var(--dimmer);cursor:pointer;font-size:13px;padding:1px 3px;border-radius:3px}
.sg-del:hover{color:var(--red)}
.sg-entries{padding:7px 13px;max-height:190px;overflow-y:auto}
.sg-entry{padding:3px 0;display:flex;align-items:center;gap:5px;border-bottom:1px solid rgba(255,255,255,.04)}
.sg-entry:last-child{border:none}
.sg-entry-bk{font-family:'JetBrains Mono',monospace;font-size:10px;color:#c4b5fd;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;cursor:pointer}
.sg-entry-bk:hover{color:var(--accent2);text-decoration:underline}
.sg-entry-src{display:flex;gap:2px}
.sg-entry-rem{background:none;border:none;color:var(--dimmer);cursor:pointer;font-size:10px;padding:0 2px}
.sg-entry-rem:hover{color:var(--red)}
.sg-add-entry{padding:7px 13px;border-top:1px solid var(--border)}
.sg-add-entry input{width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 7px;border-radius:5px;font-size:11px;font-family:'JetBrains Mono',monospace}
.sg-add-entry input:focus{outline:none;border-color:var(--accent)}
.sg-cnt{font-size:10px;color:var(--muted);background:var(--bg4);padding:1px 5px;border-radius:3px}
.unassigned-section{margin-top:14px}
.unassigned-header{font-size:11px;font-weight:600;color:var(--amber);margin-bottom:7px}
.unassigned-chips{display:flex;flex-wrap:wrap;gap:5px}
.unassigned-chip{background:var(--bg3);border:1px solid var(--amber);border-radius:5px;padding:2px 7px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--amber);cursor:pointer}
.unassigned-chip:hover{background:rgba(245,158,11,.15)}

/* ═══ PAGE 2 — INGRÉDIENTS ═══ */
#pg-ingr{flex-direction:column}
.ctrl-bar{background:var(--bg2);border-bottom:1px solid var(--border);padding:7px 15px;display:flex;gap:7px;align-items:center;flex-wrap:wrap;flex-shrink:0}
.sbox{background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:5px 10px;border-radius:7px;font-size:12px;width:230px}
.sbox:focus{outline:none;border-color:var(--accent)}
.fb{background:var(--bg3);border:1px solid var(--border);color:var(--muted);padding:4px 9px;border-radius:6px;font-size:11px;cursor:pointer;white-space:nowrap}
.fb.active,.fb:hover{background:var(--accent);border-color:var(--accent);color:#fff}
.tw{flex:1;overflow:auto;min-height:0}
table{width:100%;border-collapse:collapse;min-width:1000px}
thead th{background:var(--bg3);border-bottom:2px solid var(--border);padding:7px 9px;text-align:left;font-size:10px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.4px;position:sticky;top:0;z-index:5;white-space:nowrap}
tbody tr{border-bottom:1px solid rgba(42,47,82,.5);transition:background .08s}
tbody tr:hover{background:rgba(99,102,241,.05)}
tbody tr.checked{background:rgba(34,197,94,.05)}
tbody tr.modified{background:rgba(245,158,11,.04)}
tbody tr.rejected td{opacity:.3}
td{padding:5px 9px;vertical-align:middle}
.ed{background:transparent;border:none;border-bottom:1px solid transparent;color:var(--text);font-size:12px;width:100%;padding:2px 0;transition:border .12s;min-width:50px}
.ed:focus{outline:none;border-bottom-color:var(--accent);background:rgba(99,102,241,.06);padding:2px 4px;border-radius:3px 3px 0 0}
.ed.mod{border-bottom-color:var(--amber);color:var(--amber)}
.ed-mono{font-family:'JetBrains Mono',monospace;font-size:11px}
.canon-wrap{display:flex;align-items:center;gap:3px}
.rsb{background:none;border:none;color:var(--amber);font-size:12px;cursor:pointer;padding:0;display:none}
.ed.mod~.rsb{display:block}
.gsel,.sgsel{background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:3px 5px;border-radius:4px;font-size:10px;cursor:pointer;width:100%;min-width:80px}
.gsel:focus,.sgsel:focus{outline:none;border-color:var(--accent)}
.cw{display:inline-flex;align-items:center;justify-content:center;width:19px;height:19px;border:2px solid var(--border);border-radius:5px;cursor:pointer;flex-shrink:0}
.cw:hover{border-color:var(--green)}
.cw.checked{background:var(--green);border-color:var(--green2)}
.cw svg{display:none;width:10px;height:10px;stroke:#fff;stroke-width:3;fill:none;stroke-linecap:round;stroke-linejoin:round}
.cw.checked svg{display:block}
.rjbtn{background:transparent;border:1px solid var(--border);color:var(--dimmer);width:20px;height:20px;border-radius:4px;cursor:pointer;font-size:10px;display:inline-flex;align-items:center;justify-content:center}
.rjbtn:hover{border-color:var(--red);color:var(--red)}
.rjbtn.active{background:rgba(239,68,68,.12);border-color:var(--red);color:var(--red)}
.bkcell{font-family:'JetBrains Mono',monospace;font-size:11px;color:#c4b5fd}
.src-badge{display:inline-block;padding:1px 4px;border-radius:3px;font-size:9px;font-weight:700}
.s-CIQUAL{background:rgba(99,102,241,.2);color:#818cf8;border:1px solid rgba(99,102,241,.3)}
.s-USDA{background:rgba(34,211,238,.15);color:#22d3ee;border:1px solid rgba(34,211,238,.3)}
.s-CNF{background:rgba(245,158,11,.15);color:#fbbf24;border:1px solid rgba(245,158,11,.3)}
.gsep td{padding:4px 9px;font-size:10px;font-weight:700;color:var(--accent2);background:var(--bg3);letter-spacing:.4px;text-transform:uppercase;border-top:2px solid var(--border)}
.view-var-btn{background:var(--bg4);border:1px solid var(--border);color:var(--muted);padding:2px 6px;border-radius:4px;font-size:10px;cursor:pointer;white-space:nowrap}
.view-var-btn:hover{border-color:var(--accent);color:var(--accent2)}

/* ═══ PAGE 3 — VARIANTS ═══ */
#pg-var{flex-direction:row}
.var-left{width:260px;min-width:260px;background:var(--bg2);border-right:1px solid var(--border);display:flex;flex-direction:column;overflow:hidden;flex-shrink:0}
.var-left-hdr{padding:10px 12px;border-bottom:1px solid var(--border);flex-shrink:0}
.var-left-hdr input{width:100%;background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:6px;font-size:12px;margin-bottom:7px}
.var-left-hdr input:focus{outline:none;border-color:var(--accent)}
.var-src-filters{display:flex;gap:5px;flex-wrap:wrap}
.vsf{background:var(--bg3);border:1px solid var(--border);color:var(--muted);padding:3px 8px;border-radius:5px;font-size:10px;cursor:pointer}
.vsf.active{background:var(--accent);border-color:var(--accent);color:#fff}
.canon-list{flex:1;overflow-y:auto}
.canon-item{padding:7px 12px;cursor:pointer;border-bottom:1px solid var(--border);display:flex;align-items:center;gap:8px;transition:background .1s}
.canon-item:hover{background:var(--bg3)}
.canon-item.active{background:var(--accent3);border-left:3px solid var(--accent)}
.canon-bk{font-family:'JetBrains Mono',monospace;font-size:11px;color:#c4b5fd}
.canon-lbl{font-size:11px;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.canon-lvc{font-size:10px;color:var(--dim);background:var(--bg4);padding:1px 5px;border-radius:3px;flex-shrink:0}

.var-right{flex:1;display:flex;flex-direction:column;overflow:hidden;min-width:0}
.var-right-hdr{background:var(--bg2);border-bottom:1px solid var(--border);padding:10px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0}
.var-right-hdr h2{font-size:14px;font-weight:700}
.var-right-hdr .canon-badge{font-family:'JetBrains Mono',monospace;font-size:12px;color:#c4b5fd;background:var(--bg3);border:1px solid var(--border);padding:3px 8px;border-radius:5px}
.variant-area{flex:1;overflow-y:auto;padding:14px}
.var-src-section{margin-bottom:18px}
.var-src-title{font-size:11px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:9px;display:flex;align-items:center;gap:8px}
.var-bk-section{margin-bottom:12px}
.var-bk-title{font-size:10px;color:var(--dim);font-family:'JetBrains Mono',monospace;background:var(--bg3);border:1px solid var(--border);padding:3px 8px;border-radius:5px;display:inline-block;margin-bottom:7px}

/* Variant card (leaf/node) */
.vcard{background:var(--bg2);border:1px solid var(--border);border-radius:8px;margin-bottom:7px;overflow:hidden;transition:border .15s}
.vcard:hover{border-color:var(--border2)}
.vcard.is-leaf{border-left:3px solid var(--green)}
.vcard.is-node{border-left:3px solid var(--amber)}
.vcard.modified{border-left-color:var(--accent);border-color:var(--accent2)}
.vcard-header{padding:8px 12px;background:var(--bg3);display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.vtype{font-size:9px;font-weight:700;padding:2px 6px;border-radius:3px;text-transform:uppercase;flex-shrink:0}
.vtype-leaf{background:rgba(34,197,94,.2);color:var(--green);border:1px solid rgba(34,197,94,.3)}
.vtype-node{background:rgba(245,158,11,.2);color:var(--amber);border:1px solid rgba(245,158,11,.3)}
.vkey{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--accent2)}
.vsid{font-size:10px;color:var(--dim);margin-left:auto}
.vlabel{font-size:12px;color:var(--text);flex:1;min-width:200px;font-style:italic}
.vcard-body{padding:10px 12px}
.vfields{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:8px}
.vfield{display:flex;flex-direction:column;gap:3px}
.vf-label{font-size:9px;font-weight:700;color:var(--muted);text-transform:uppercase;letter-spacing:.3px}
.vf-input{background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 7px;border-radius:5px;font-size:12px;font-family:'JetBrains Mono',monospace;width:100%}
.vf-input:focus{outline:none;border-color:var(--accent);background:var(--bg4)}
.vf-input.mod{border-color:var(--amber);color:var(--amber)}
.vf-select{background:var(--bg3);border:1px solid var(--border);color:var(--text);padding:4px 7px;border-radius:5px;font-size:12px;width:100%;cursor:pointer}
.vf-select:focus{outline:none;border-color:var(--accent)}
.vf-select.mod{border-color:var(--amber);color:var(--amber)}
.vf-readonly{font-family:'JetBrains Mono',monospace;font-size:11px;color:var(--muted);padding:4px 0}
.vcue{font-size:10px;color:var(--dim);margin-top:6px;font-style:italic}
.vcard-children{padding:0 12px 10px 24px}
.no-variants{text-align:center;padding:50px;color:var(--dim);font-size:13px}

/* depth indentation */
.v-depth-0{}
.v-depth-1{margin-left:16px}
.v-depth-2{margin-left:32px}

/* MODAL */
.modal-ov{display:none;position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:200;align-items:center;justify-content:center}
.modal-ov.open{display:flex}
.modal{background:var(--bg2);border:1px solid var(--border);border-radius:14px;padding:20px;width:min(740px,92vw);max-height:82vh;display:flex;flex-direction:column;gap:11px}
.modal-hdr{display:flex;align-items:center;gap:10px}
.modal-hdr h2{font-size:14px;flex:1}
.modal pre{background:var(--bg3);border:1px solid var(--border);border-radius:8px;padding:13px;font-family:'JetBrains Mono',monospace;font-size:10px;overflow:auto;color:#a5b4fc;white-space:pre;line-height:1.7;flex:1;max-height:50vh}

/* Scrollbars */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:var(--border);border-radius:3px}

/* Session modal extras */
.session-modal{width:min(520px,92vw)}
.session-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.session-btn{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;background:var(--bg3);border:1px solid var(--border);border-radius:10px;padding:18px 12px;cursor:pointer;font-size:12px;color:var(--muted);transition:all .15s;text-align:center}
.session-btn:hover{border-color:var(--accent);color:var(--text);background:var(--bg4)}
.session-btn .s-icon{font-size:24px}
.session-btn.danger:hover{border-color:var(--red);color:var(--red)}
.session-info{font-size:11px;color:var(--dim);background:var(--bg3);border:1px solid var(--border);border-radius:7px;padding:10px 13px;line-height:1.7}
.autosave-dot{width:7px;height:7px;border-radius:50%;background:var(--green);display:inline-block;margin-right:4px;animation:pulse 2s ease infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.ts-label{font-size:10px;color:var(--dim);cursor:pointer}
.ts-label:hover{color:var(--muted)}
/* ── Drag & Drop ─────────────────────────────── */
.sg-entry[draggable]{cursor:grab}
.sg-entry[draggable]:active{cursor:grabbing}
.sg-entry.bk-dragging{opacity:.3;background:rgba(99,102,241,.06)}
.sg-entries.dz-on{background:rgba(99,102,241,.1);outline:2px dashed var(--accent);outline-offset:-2px;border-radius:6px;min-height:32px}
.drag-handle{color:var(--dimmer);font-size:11px;cursor:grab;padding:0 3px 0 0;user-select:none;flex-shrink:0}
.drag-handle:hover{color:var(--accent2)}
.unassigned-chip[draggable]{cursor:grab}
.unassigned-chip.bk-dragging{opacity:.3}

</style>
</head>
<body>
<header>
  <div><div class="logo">🧬 Taxonomie v3</div><div class="logo-sub">CIQUAL · USDA · CNF</div></div>
  <div class="tabs">
    <button class="tab active" onclick="showPage('groups',this)">🗂 Groupes</button>
    <button class="tab" onclick="showPage('ingr',this)">🥦 Ingrédients</button>
    <button class="tab" onclick="showPage('var',this)">🔬 Variants &amp; Sources</button>
  </div>
  <div class="stats-bar">
    <div class="sb">Entrées&thinsp;: <strong id="s-total">—</strong></div>
    <div class="sb">✓ <strong id="s-ok">0</strong></div>
    <div class="sb">✏ <strong id="s-mod">0</strong></div>
    <div class="sb">✗ <strong id="s-rej">0</strong></div>
    <span class="ts-label" onclick="openSession()" title="Ouvrir le gestionnaire de session"><span class="autosave-dot" id="as-dot" style="background:var(--dim)"></span><span id="as-ts">non sauvegardé</span></span>
    <button class="btn-s" onclick="openSession()">💾 Session</button>
    <button class="btn-p" onclick="openExport()">📥 Exporter</button>
  </div>
</header>

<!-- PAGE 1 — GROUPES -->
<div id="pg-groups" class="page active">
  <div class="tree-panel">
    <div class="tree-search"><input type="search" placeholder="🔍 Groupe…" oninput="filterTree(this.value)"/></div>
    <div id="tree-list"></div>
  </div>
  <div class="detail-panel">
    <div class="detail-header" id="detail-header"><div style="color:var(--dim)">← Sélectionner un groupe</div></div>
    <div class="sgs-area" id="sgs-area"></div>
  </div>
</div>

<!-- PAGE 2 — INGRÉDIENTS -->
<div id="pg-ingr" class="page">
  <div class="ctrl-bar">
    <input class="sbox" type="search" placeholder="🔍 base_key, nom, canonical…" oninput="onIS(this.value)"/>
    <button class="fb active" data-f="all" onclick="setF('all',this)">Tous</button>
    <button class="fb" data-f="unchecked" onclick="setF('unchecked',this)">À valider</button>
    <button class="fb" data-f="checked" onclick="setF('checked',this)">✓</button>
    <button class="fb" data-f="modified" onclick="setF('modified',this)">✏</button>
    <button class="fb" data-f="rejected" onclick="setF('rejected',this)">✗</button>
    <button class="fb" style="background:rgba(99,102,241,.2);color:#818cf8;border-color:rgba(99,102,241,.4)" data-f="CIQUAL" onclick="setF('CIQUAL',this)">CIQUAL</button>
    <button class="fb" style="background:rgba(34,211,238,.15);color:#22d3ee;border-color:rgba(34,211,238,.35)" data-f="USDA" onclick="setF('USDA',this)">USDA</button>
    <button class="fb" style="background:rgba(245,158,11,.15);color:#fbbf24;border-color:rgba(245,158,11,.35)" data-f="CNF" onclick="setF('CNF',this)">CNF</button>
    <span id="visible-count" style="color:var(--dim);font-size:11px;margin-left:4px"></span>
    <button class="btn-s" style="margin-left:auto" onclick="checkAllVisible()">✓ Tout valider</button>
  </div>
  <div class="tw">
    <table><thead><tr>
      <th>✓</th><th>BASE_KEY</th><th>Sources</th><th>Nom FR</th><th>Nom EN</th>
      <th>Lv</th><th>Groupe</th><th>Sous-groupe</th><th>Canonical</th><th>Note</th><th>Var</th><th>✗</th>
    </tr></thead><tbody id="ingr-tbody"></tbody></table>
    <div id="ingr-empty" style="display:none;text-align:center;padding:50px;color:var(--dim)">Aucun résultat.</div>
  </div>
</div>

<!-- PAGE 3 — VARIANTS -->
<div id="pg-var" class="page">
  <div class="var-left">
    <div class="var-left-hdr">
      <input type="search" id="var-canon-search" placeholder="🔍 Rechercher canonical…" oninput="filterCanons(this.value)"/>
      <div class="var-src-filters">
        <button class="vsf active" data-vs="all" onclick="setVSF('all',this)">Tous</button>
        <button class="vsf" data-vs="CIQUAL" onclick="setVSF('CIQUAL',this)" style="color:#818cf8">CIQUAL</button>
        <button class="vsf" data-vs="USDA"   onclick="setVSF('USDA',this)"   style="color:#22d3ee">USDA</button>
        <button class="vsf" data-vs="CNF"    onclick="setVSF('CNF',this)"    style="color:#fbbf24">CNF</button>
        <button class="vsf" data-vs="multi"  onclick="setVSF('multi',this)"  style="color:#a855f7">Multi</button>
        <button class="vsf" data-vs="issue"  onclick="setVSF('issue',this)"  style="color:#fb7185">⚠ Issues</button>
      </div>
    </div>
    <div class="canon-list" id="canon-list"></div>
  </div>
  <div class="var-right">
    <div class="var-right-hdr" id="var-right-hdr">
      <div style="color:var(--dim);font-size:12px">← Sélectionner un canonical pour voir ses variants</div>
    </div>
    <div class="variant-area" id="variant-area">
      <div class="no-variants">Sélectionner un ingrédient dans la liste de gauche.</div>
    </div>
  </div>
</div>

<!-- MODAL EXPORT -->
<div class="modal-ov" id="modal" onclick="if(event.target===this)closeExport()">
  <div class="modal">
    <div class="modal-hdr">
      <h2>📥 Export — BASE_INGREDIENT_MAP + STATE_OVERRIDES</h2>
      <button class="btn-s" onclick="copyExport()">📋 Copier</button>
      <button class="btn-s" onclick="closeExport()">Fermer</button>
    </div>
    <pre id="ex-content"></pre>
  </div>
</div>

<script>
// ═══════════════════════════════════════════════════════════
//  DATA
// ═══════════════════════════════════════════════════════════
const TAXONOMY = %%TAXONOMY%%;
const VD       = %%VARIANTS%%;   // {canon -> {src -> {bk -> [entries]}}}

const GROUP_MAP = {};
const SG_MAP    = {};
TAXONOMY.forEach(g=>{
  GROUP_MAP[g.id]=g;
  (g.subgroups||[]).forEach(sg=>{ SG_MAP[sg.id]={group:g,sg}; });
});

// ── Entry state ──────────────────────────────────────────────
const S = {};   // gid|bk -> state obj
const VS = {};  // canon|src|bk|VID -> state obj  (variant state overrides)

TAXONOMY.forEach(g=>g.entries.forEach(e=>{
  const id=g.id+'|'+e.bk;
  S[id]={checked:false,rejected:false,
    canon:e.canon,origCanon:e.canon,
    name_fr:e.name_fr||'',name_en:e.name_en||'',
    note:'',sgid:e.sg||'',origSgid:e.sg||'',
    gid:g.id,bk:e.bk,sources:e.sources||[],leaves:e.leaves||0};
}));

// ── Tabs ─────────────────────────────────────────────────────
function showPage(p,btn){
  document.querySelectorAll('.page').forEach(el=>el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  document.getElementById('pg-'+p).classList.add('active');
  btn.classList.add('active');
  if(p==='ingr') renderIngrTable();
  if(p==='groups') renderTree();
  if(p==='var') renderCanonList();
}

// ── Stats ─────────────────────────────────────────────────────
function upStats(){
  let tot=0,ok=0,mod=0,rej=0;
  Object.values(S).forEach(s=>{tot++;if(s.checked)ok++;if(s.canon!==s.origCanon||s.sgid!==s.origSgid)mod++;if(s.rejected)rej++;});
  const vm=Object.keys(VS).length; mod+=vm;
  document.getElementById('s-total').textContent=tot;
  document.getElementById('s-ok').textContent=ok;
  document.getElementById('s-mod').textContent=mod;
  document.getElementById('s-rej').textContent=rej;
}

// ════════════════════════════════════════════════════════════
//  PAGE 1 — GROUPS
// ════════════════════════════════════════════════════════════
let activeGid=null,activeSgid=null;

function renderTree(filter=''){
  const tl=document.getElementById('tree-list'); tl.innerHTML='';
  TAXONOMY.forEach(g=>{
    if(filter&&!g.label.toLowerCase().includes(filter)&&!g.id.toLowerCase().includes(filter))return;
    const isOpen=g.id===activeGid||(activeSgid&&SG_MAP[activeSgid]?.group.id===g.id);
    const div=document.createElement('div');
    div.className='tree-item'+(g.id===activeGid?' active':'')+(isOpen?' open':'');
    div.innerHTML=`<div class="tree-group" onclick="selectGroup('${g.id}')">
      <span class="tree-gid">${g.id}</span>
      <span class="tree-glabel">${g.label}</span>
      <span class="tree-cnt">${g.entries.length}</span>
    </div>
    <div class="tree-subs">
      ${(g.subgroups||[]).map(sg=>{
        const cnt=g.entries.filter(e=>e.sg===sg.id).length;
        return `<div class="tree-sub${activeSgid===sg.id?' active':''}" onclick="selectSG('${g.id}','${sg.id}',event)">
          ↳ <span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${sg.label}</span>
          <span class="tree-sub-cnt">${cnt}</span>
        </div>`;
      }).join('')}
    </div>`;
    tl.appendChild(div);
  });
}
function filterTree(v){renderTree(v.toLowerCase());}
function selectGroup(gid){activeGid=gid;activeSgid=null;renderTree();renderDetail(gid,null);}
function selectSG(gid,sgid,ev){ev.stopPropagation();activeGid=gid;activeSgid=sgid;renderTree();renderDetail(gid,sgid);}

function renderDetail(gid,sgid){
  const g=GROUP_MAP[gid]; if(!g)return;
  document.getElementById('detail-header').innerHTML=`
    <input class="detail-gid-input" value="${g.id}" onchange="updateGid('${g.id}',this.value)"/>
    <input class="editable-title" value="${g.label}" style="flex:1" onchange="GROUP_MAP['${g.id}'].label=this.value;renderTree()"/>
    <button class="btn-s" onclick="addSG('${gid}')">+ Sous-groupe</button>`;
  const area=document.getElementById('sgs-area');
  const sgs=sgid?(g.subgroups||[]).filter(s=>s.id===sgid):(g.subgroups||[]);
  const unassigned=g.entries.filter(e=>!e.sg);
  let html='<div class="sgs-grid">';
  sgs.forEach(sg=>{
    const entries=g.entries.filter(e=>e.sg===sg.id);
    html+=`<div class="sg-card"><div class="sg-card-header">
      <input class="sg-id-input" value="${sg.id}" onchange="updateSgId('${gid}','${sg.id}',this.value)"/>
      <input class="sg-name-input" value="${sg.label}" onchange="updateSgLabel('${gid}','${sg.id}',this.value)"/>
      <span class="sg-cnt">${entries.length}</span>
      <button class="sg-del" onclick="deleteSG('${gid}','${sg.id}')">🗑</button>
    </div>
    <div class="sg-entries" ondragover="event.preventDefault()" ondragenter="onDrEnt(event,'${gid}','${sg.id}')" ondragleave="onDrLv(event)" ondrop="onDropBK(event,'${gid}','${sg.id}')">
      ${entries.map(e=>`<div class="sg-entry" draggable="true" ondragstart="onDragBK(event,'${gid}','${e.bk}')" ondragend="onDrEnd(event)">
        <span class="drag-handle" title="Glisser pour déplacer">&#8943;</span>
        <span class="sg-entry-bk" onclick="goToVariant('${e.canon||e.bk}')" title="Voir les variants de ${e.canon||e.bk}">${e.bk}</span>
        <span class="sg-entry-src">${e.sources.map(s=>`<span class="src-badge s-${s}" style="font-size:8px">${s[0]}</span>`).join('')}</span>
        <button class="sg-entry-rem" onclick="unassign('${gid}','${e.bk}','${sg.id}')">✕</button>
      </div>`).join('')}
      ${!entries.length?'<div style="color:var(--dim);font-size:11px;padding:7px 0">Vide</div>':''}
    </div>
    <div class="sg-add-entry">
      <input placeholder="+ base_key…" onkeydown="if(event.key==='Enter')assignEntry('${gid}','${sg.id}',this)" list="bkdl"/>
    </div></div>`;
  });
  if(!sgid) html+=`<div class="add-sg-btn" onclick="addSG('${gid}')"><div style="font-size:18px;margin-bottom:5px">+</div>Ajouter sous-groupe</div>`;
  html+='</div>';
  if(unassigned.length&&!sgid) html+=`<div class="unassigned-section">
    <div class="unassigned-header">⚠ ${unassigned.length} sans sous-groupe</div>
    <div class="unassigned-chips">${unassigned.map(e=>`<div class="unassigned-chip" draggable="true" ondragstart="onDragBK(event,'${gid}','${e.bk}')" ondragend="onDrEnd(event)" onclick="promptAssign('${gid}','${e.bk}')">${e.bk}</div>`).join('')}</div>
  </div>`;
  html+=`<datalist id="bkdl">${g.entries.map(e=>`<option value="${e.bk}">`).join('')}</datalist>`;
  area.innerHTML=html;
}

function addSG(gid){const g=GROUP_MAP[gid];if(!g)return;const id='sg_new_'+Date.now();const sg={id,label:'Nouveau'};(g.subgroups||(g.subgroups=[])).push(sg);SG_MAP[id]={group:g,sg};activeSgid=null;renderTree();renderDetail(gid,null);}
function deleteSG(gid,sgid){const g=GROUP_MAP[gid];if(!g)return;g.entries.forEach(e=>{if(e.sg===sgid){e.sg='';const s=S[gid+'|'+e.bk];if(s)s.sgid='';}});g.subgroups=(g.subgroups||[]).filter(s=>s.id!==sgid);delete SG_MAP[sgid];if(activeSgid===sgid)activeSgid=null;renderTree();renderDetail(gid,null);}
function updateGid(old,nw){if(!nw||nw===old)return;const g=GROUP_MAP[old];if(!g)return;delete GROUP_MAP[old];g.id=nw;GROUP_MAP[nw]=g;g.entries.forEach(e=>{const oid=old+'|'+e.bk;const s=S[oid];if(s){delete S[oid];s.gid=nw;S[nw+'|'+e.bk]=s;}});activeGid=nw;renderTree();renderDetail(nw,activeSgid);}
function updateSgId(gid,old,nw){if(!nw||nw===old)return;const g=GROUP_MAP[gid];if(!g)return;const sg=(g.subgroups||[]).find(s=>s.id===old);if(!sg)return;sg.id=nw;delete SG_MAP[old];SG_MAP[nw]={group:g,sg};g.entries.forEach(e=>{if(e.sg===old){e.sg=nw;const s=S[gid+'|'+e.bk];if(s)s.sgid=nw;}});if(activeSgid===old)activeSgid=nw;renderTree();renderDetail(gid,activeSgid);}
function updateSgLabel(gid,sgid,lbl){const g=GROUP_MAP[gid];if(!g)return;const sg=(g.subgroups||[]).find(s=>s.id===sgid);if(sg)sg.label=lbl;renderTree();}
function unassign(gid,bk,sgid){const g=GROUP_MAP[gid];if(!g)return;const e=g.entries.find(x=>x.bk===bk);if(e)e.sg='';const s=S[gid+'|'+bk];if(s)s.sgid='';renderDetail(gid,activeSgid);}
function assignEntry(gid,sgid,inp){const bk=inp.value.trim();if(!bk)return;const g=GROUP_MAP[gid];if(!g)return;let e=g.entries.find(x=>x.bk===bk);if(!e){e={bk,sources:[],canon:bk,name_fr:'',name_en:'',leaves:0,sg:sgid};g.entries.push(e);S[gid+'|'+bk]={checked:false,rejected:false,canon:bk,origCanon:bk,name_fr:'',name_en:'',note:'',sgid,origSgid:'',gid,bk,sources:[],leaves:0};}else{e.sg=sgid;const s=S[gid+'|'+bk];if(s)s.sgid=sgid;}inp.value='';renderTree();renderDetail(gid,activeSgid);upStats();}
function promptAssign(gid,bk){const g=GROUP_MAP[gid];if(!g)return;const opts=(g.subgroups||[]).map(sg=>sg.id+': '+sg.label).join('\n');const c=prompt('Assigner "'+bk+'" à:\n\n'+opts+'\n\nID du sous-groupe:')?.trim();if(c&&(g.subgroups||[]).find(s=>s.id===c)){const e=g.entries.find(x=>x.bk===bk);if(e)e.sg=c;const s=S[gid+'|'+bk];if(s)s.sgid=c;renderDetail(gid,activeSgid);}}


// ════════════════════════════════════════════════════════════
//  DRAG & DROP — glisser les base_keys entre sous-groupes / groupes
// ════════════════════════════════════════════════════════════
let _drag = null;  // {fromGid, bk}

function onDragBK(ev, fromGid, bk){
  _drag = {fromGid, bk};
  ev.dataTransfer.effectAllowed = 'move';
  ev.dataTransfer.setData('text/plain', bk);
  setTimeout(()=>{ if(ev.target) ev.target.classList.add('bk-dragging'); }, 0);
}

function onDrEnd(ev){
  if(ev.target) ev.target.classList.remove('bk-dragging');
  document.querySelectorAll('.dz-on').forEach(el=>el.classList.remove('dz-on'));
}

function onDrEnt(ev, targetGid, targetSgid){
  if(!_drag) return;
  ev.preventDefault();
  ev.currentTarget.classList.add('dz-on');
}

function onDrLv(ev){
  if(!ev.currentTarget.contains(ev.relatedTarget)){
    ev.currentTarget.classList.remove('dz-on');
  }
}

function onDropBK(ev, targetGid, targetSgid){
  ev.preventDefault();
  document.querySelectorAll('.dz-on').forEach(el=>el.classList.remove('dz-on'));
  if(!_drag) return;
  const {fromGid, bk} = _drag;
  _drag = null;

  if(fromGid === targetGid){
    // Même groupe : changement de sous-groupe seulement
    const g = GROUP_MAP[fromGid]; if(!g) return;
    const e = g.entries.find(x=>x.bk===bk); if(!e) return;
    if(e.sg === targetSgid) return;
    e.sg = targetSgid;
    const s = S[fromGid+'|'+bk]; if(s) s.sgid = targetSgid;
  } else {
    // Déplacement inter-groupes
    const fromG = GROUP_MAP[fromGid];
    const toG   = GROUP_MAP[targetGid];
    if(!fromG || !toG) return;
    const idx = fromG.entries.findIndex(x=>x.bk===bk);
    if(idx < 0) return;
    const [entry] = fromG.entries.splice(idx, 1);
    entry.sg = targetSgid;
    toG.entries.push(entry);
    // Re-clé dans S
    const oldK = fromGid+'|'+bk;
    const newK = targetGid+'|'+bk;
    const s = S[oldK];
    if(s){ delete S[oldK]; s.gid=targetGid; s.sgid=targetSgid; S[newK]=s; }
  }

  // Afficher le groupe cible
  activeGid = targetGid;
  activeSgid = null;
  renderTree();
  renderDetail(targetGid, null);
  upStats();
}

// Navigate from group to variant page
function goToVariant(canon){
  // Switch to variant page
  document.querySelectorAll('.page').forEach(el=>el.classList.remove('active'));
  document.querySelectorAll('.tab').forEach(b=>b.classList.remove('active'));
  document.getElementById('pg-var').classList.add('active');
  document.querySelectorAll('.tab')[2].classList.add('active');
  renderCanonList();
  selectCanon(canon);
}

// ════════════════════════════════════════════════════════════
//  PAGE 2 — INGRÉDIENTS
// ════════════════════════════════════════════════════════════
let curF='all',curSearch='';
let isTimer;
function onIS(v){clearTimeout(isTimer);isTimer=setTimeout(()=>{curSearch=v.trim().toLowerCase();renderIngrTable();},180);}
function setF(f,btn){curF=f;document.querySelectorAll('.fb').forEach(b=>b.classList.toggle('active',b.dataset.f===f));renderIngrTable();}

function isVis(gid,e){
  const s=S[gid+'|'+e.bk]; if(!s)return false;
  if(curF==='checked'&&!s.checked)return false;
  if(curF==='unchecked'&&(s.checked||s.rejected))return false;
  if(curF==='modified'&&s.canon===s.origCanon&&s.sgid===s.origSgid)return false;
  if(curF==='rejected'&&!s.rejected)return false;
  if(['CIQUAL','USDA','CNF'].includes(curF)&&!e.sources.includes(curF))return false;
  if(curSearch){const q=curSearch;if(!e.bk.includes(q)&&!s.canon.includes(q)&&!s.name_fr.toLowerCase().includes(q)&&!s.name_en.toLowerCase().includes(q))return false;}
  return true;
}

function renderIngrTable(){
  const tbody=document.getElementById('ingr-tbody');
  let html='',cnt=0;
  TAXONOMY.forEach(g=>{
    const vis=g.entries.filter(e=>isVis(g.id,e));
    if(!vis.length)return;
    html+=`<tr class="gsep"><td colspan="12">${g.id} — ${g.label} <span style="opacity:.5;font-weight:400">(${vis.length})</span></td></tr>`;
    vis.forEach(e=>{html+=ingrRow(g,e);cnt++;});
  });
  tbody.innerHTML=html;
  document.getElementById('ingr-empty').style.display=cnt?'none':'block';
  document.getElementById('visible-count').textContent=cnt?cnt+' entrées':'';
}

function ingrRow(g,e){
  const sid=g.id+'|'+e.bk, s=S[sid];
  const mod=s.canon!==s.origCanon||s.sgid!==s.origSgid;
  const cls=s.rejected?'rejected':s.checked?'checked':mod?'modified':'';
  const rid='r-'+sid.replace(/[^a-z0-9]/gi,'_');
  const srcs=e.sources.map(src=>`<span class="src-badge s-${src}">${src[0]}</span>`).join(' ');
  const gOpts=TAXONOMY.map(gg=>`<option value="${gg.id}"${gg.id===s.gid?'selected':''}>${gg.id}</option>`).join('');
  const cg=GROUP_MAP[s.gid]||g;
  const sgOpts=`<option value="">—</option>`+(cg.subgroups||[]).map(sg=>`<option value="${sg.id}"${sg.id===s.sgid?'selected':''}>${sg.label}</option>`).join('');
  const hasVar=!!(VD[s.canon]);
  return `<tr class="${cls}" id="${rid}">
    <td><div class="cw${s.checked?' checked':''}" onclick="tchk('${g.id}','${e.bk}','${rid}')"><svg viewBox="0 0 16 16"><polyline points="2,8 6,13 14,3"/></svg></div></td>
    <td class="bkcell">${e.bk}</td>
    <td>${srcs}</td>
    <td><input class="ed" value="${s.name_fr}" oninput="S['${sid}'].name_fr=this.value;upStats()" style="min-width:90px"/></td>
    <td><input class="ed" value="${s.name_en}" oninput="S['${sid}'].name_en=this.value;upStats()" style="min-width:90px"/></td>
    <td style="text-align:center;color:var(--dim);font-size:11px">${e.leaves||''}</td>
    <td><select class="gsel" onchange="onGChange(this,'${g.id}','${e.bk}','${rid}')">${gOpts}</select></td>
    <td><select class="sgsel" id="sgsel-${rid}" onchange="onSGChange(this,'${g.id}','${e.bk}','${rid}')">${sgOpts}</select></td>
    <td style="min-width:150px"><div class="canon-wrap">
      <input class="ed ed-mono${s.canon!==s.origCanon?' mod':''}" value="${s.canon}"
        oninput="onCanon(this,'${g.id}','${e.bk}','${rid}')" style="min-width:140px"/>
      <button class="rsb" onclick="resetCanon('${g.id}','${e.bk}','${rid}')">↺</button>
    </div></td>
    <td><input class="ed" value="${s.note}" placeholder="note…" oninput="S['${sid}'].note=this.value" style="min-width:90px"/></td>
    <td><button class="view-var-btn" onclick="goToVariant('${s.canon}')" title="Voir les variants de ${s.canon}">${hasVar?'🔬 '+countLeaves(VD[s.canon]):'—'}</button></td>
    <td><button class="rjbtn${s.rejected?' active':''}" onclick="trj('${g.id}','${e.bk}','${rid}')">✕</button></td>
  </tr>`;
}

function countLeaves(srcDict){
  let n=0;
  if(!srcDict)return 0;
  Object.values(srcDict).forEach(bkDict=>{
    Object.values(bkDict).forEach(entries=>{
      n+=countLeavesArr(entries);
    });
  });
  return n;
}
function countLeavesArr(arr){
  let n=0;
  (arr||[]).forEach(e=>{if(e.t==='leaf')n++;n+=countLeavesArr(e.ch);});
  return n;
}

function tchk(gid,bk,rid){const s=S[gid+'|'+bk];if(s.rejected)return;s.checked=!s.checked;const tr=document.getElementById(rid);if(tr){tr.className=s.checked?'checked':(s.canon!==s.origCanon?'modified':'');tr.querySelector('.cw').classList.toggle('checked',s.checked);}upStats();}
function onCanon(el,gid,bk,rid){const s=S[gid+'|'+bk];s.canon=el.value;const mod=el.value!==s.origCanon;el.classList.toggle('mod',mod);const rb=el.nextElementSibling;if(rb)rb.style.display=mod?'block':'none';const tr=document.getElementById(rid);if(tr&&!s.checked&&!s.rejected)tr.className=mod?'modified':'';upStats();}
function resetCanon(gid,bk,rid){const s=S[gid+'|'+bk];s.canon=s.origCanon;const tr=document.getElementById(rid);if(!tr)return;const inp=tr.querySelector('.ed-mono');if(inp){inp.value=s.origCanon;inp.classList.remove('mod');}const rb=tr.querySelector('.rsb');if(rb)rb.style.display='none';if(!s.checked&&!s.rejected)tr.className='';upStats();}
function onGChange(sel,gid,bk,rid){const newGid=sel.value;const s=S[gid+'|'+bk];if(!s)return;const og=GROUP_MAP[gid],ng=GROUP_MAP[newGid];if(og&&ng){const idx=og.entries.findIndex(x=>x.bk===bk);if(idx>=0){const[e]=og.entries.splice(idx,1);e.sg='';ng.entries.push(e);}}delete S[gid+'|'+bk];s.gid=newGid;s.sgid='';S[newGid+'|'+bk]=s;const sgsel=document.getElementById('sgsel-'+rid);if(sgsel){sgsel.innerHTML=`<option>—</option>`+(ng?.subgroups||[]).map(sg=>`<option value="${sg.id}">${sg.label}</option>`).join('');}const tr=document.getElementById(rid);if(tr&&!s.checked&&!s.rejected)tr.className='modified';upStats();}
function onSGChange(sel,gid,bk,rid){const s=S[gid+'|'+bk];if(!s)return;s.sgid=sel.value;const g=GROUP_MAP[s.gid];if(g){const e=g.entries.find(x=>x.bk===bk);if(e)e.sg=sel.value;}upStats();}
function trj(gid,bk,rid){const s=S[gid+'|'+bk];s.rejected=!s.rejected;if(s.rejected)s.checked=false;const tr=document.getElementById(rid);if(tr){tr.className=s.rejected?'rejected':(s.checked?'checked':'');tr.querySelector('.cw').classList.remove('checked');tr.querySelector('.rjbtn').classList.toggle('active',s.rejected);}upStats();}
function checkAllVisible(){TAXONOMY.forEach(g=>g.entries.filter(e=>isVis(g.id,e)).forEach(e=>{const s=S[g.id+'|'+e.bk];if(s&&!s.rejected)s.checked=true;}));renderIngrTable();upStats();}

// ════════════════════════════════════════════════════════════
//  PAGE 3 — VARIANTS & SOURCES
// ════════════════════════════════════════════════════════════
let curVSF='all', varCanonSearch='', activeCanon=null;

const L1_OPTIONS=['raw','cooked','dried','manufactured','fermented','unknown'];
const L2_OPTIONS=['boiled','steamed','roasted','fried','baked','stir_fried','grilled','poached','pressure_cooked','microwaved','pan_fried','deep_fried','cooked_generic','dried','dehydrated','fermented','smoked','cured','null'];
const PRES_OPTIONS=['canned','frozen','fresh','dried','pickled','preserved','null'];
const FORM_OPTIONS=['whole','pureed','sliced','chopped','ground','powder','liquid','paste','juice','null'];
const PART_OPTIONS=['whole','flesh','skin','core','seed','leaf','root','stem','flower','null'];

function hasIssue(srcDict){
  let found=false;
  if(!srcDict)return false;
  Object.values(srcDict).forEach(bkDict=>{
    Object.values(bkDict).forEach(entries=>{
      if(checkIssue(entries))found=true;
    });
  });
  return found;
}
function checkIssue(arr){
  return (arr||[]).some(e=>e.l1==='unknown'||e.t==='unknown'||checkIssue(e.ch));
}

function getSrcList(srcDict){
  return Object.keys(srcDict||{});
}

function renderCanonList(filter){
  const q=(filter||varCanonSearch||'').toLowerCase();
  const cl=document.getElementById('canon-list'); cl.innerHTML='';
  const allCanons=Object.keys(VD).sort();
  let shown=0;
  allCanons.forEach(canon=>{
    const srcDict=VD[canon];
    const srcs=getSrcList(srcDict);
    if(curVSF==='CIQUAL'&&!srcs.includes('CIQUAL'))return;
    if(curVSF==='USDA'&&!srcs.includes('USDA'))return;
    if(curVSF==='CNF'&&!srcs.includes('CNF'))return;
    if(curVSF==='multi'&&srcs.length<2)return;
    if(curVSF==='issue'&&!hasIssue(srcDict))return;
    if(q&&!canon.includes(q))return;
    const lv=countLeaves(srcDict);
    const srcBadges=srcs.map(s=>`<span class="src-badge s-${s}" style="font-size:8px">${s[0]}</span>`).join('');
    const issue=hasIssue(srcDict);
    const div=document.createElement('div');
    div.className='canon-item'+(canon===activeCanon?' active':'');
    div.innerHTML=`<div style="flex:1;min-width:0">
      <div class="canon-bk">${canon}${issue?' <span style="color:var(--rose);font-size:9px">⚠</span>':''}</div>
      <div style="display:flex;align-items:center;gap:4px;margin-top:2px">${srcBadges}</div>
    </div>
    <span class="canon-lvc">${lv}v</span>`;
    div.onclick=()=>selectCanon(canon);
    cl.appendChild(div);
    shown++;
  });
  if(!shown) cl.innerHTML='<div style="text-align:center;padding:30px;color:var(--dim);font-size:12px">Aucun résultat</div>';
}

function filterCanons(v){varCanonSearch=v;renderCanonList();}
function setVSF(f,btn){curVSF=f;document.querySelectorAll('.vsf').forEach(b=>b.classList.toggle('active',b.dataset.vs===f));renderCanonList();}

function selectCanon(canon){
  activeCanon=canon;
  renderCanonList();
  renderVariantDetail(canon);
}

function renderVariantDetail(canon){
  const srcDict=VD[canon];
  const hdr=document.getElementById('var-right-hdr');
  const area=document.getElementById('variant-area');
  if(!srcDict){
    hdr.innerHTML=`<span class="canon-badge">${canon}</span><span style="color:var(--dim);font-size:12px;margin-left:8px">Aucun variant trouvé dans les sources</span>`;
    area.innerHTML='<div class="no-variants">Aucune donnée de variant pour ce canonical.<br/><small>Vérifier que ce canonical correspond à un base_key dans les sources.</small></div>';
    return;
  }
  const issue=hasIssue(srcDict);
  hdr.innerHTML=`<span class="canon-badge">${canon}</span>
    ${issue?'<span style="background:rgba(251,113,133,.15);border:1px solid var(--rose);color:var(--rose);padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700">⚠ Issues détectés</span>':''}
    <span style="color:var(--dim);font-size:11px;margin-left:auto">${countLeaves(srcDict)} feuilles · ${Object.keys(srcDict).join(', ')}</span>`;

  let html='';
  Object.entries(srcDict).forEach(([src,bkDict])=>{
    const badge=`<span class="src-badge s-${src}">${src}</span>`;
    html+=`<div class="var-src-section">
      <div class="var-src-title">${badge} Source&thinsp;: <strong>${src}</strong></div>`;
    Object.entries(bkDict).forEach(([bk,entries])=>{
      html+=`<div class="var-bk-section">
        <div class="var-bk-title">base_key source&thinsp;: ${bk}</div>
        ${renderVEntries(canon,src,bk,entries,0)}
      </div>`;
    });
    html+='</div>';
  });
  area.innerHTML=html;
}

function renderVEntries(canon,src,bk,entries,depth){
  let html='';
  (entries||[]).forEach(e=>{
    const vid=canon+'|'+src+'|'+bk+'|'+e.k;
    const ovr=VS[vid]||{};
    const l1=ovr.l1!==undefined?ovr.l1:e.l1;
    const l2=ovr.l2!==undefined?ovr.l2:e.l2;
    const variety=ovr.variety!==undefined?ovr.variety:(e.variety||'');
    const pres=ovr.preservation!==undefined?ovr.preservation:(e.preservation||'');
    const form=ovr.physical_form!==undefined?ovr.physical_form:(e.physical_form||'');
    const part_=ovr.part!==undefined?ovr.part:(e.part||'');
    const isModified=Object.keys(ovr).length>0;
    const isIssue=e.l1==='unknown'||e.t==='unknown';
    const cls='vcard is-'+e.t+(isModified?' modified':'')+(depth?' v-depth-'+Math.min(depth,2):'');
    const ek=vid.replace(/[^a-z0-9]/gi,'_');

    html+=`<div class="${cls}" id="vc-${ek}">
      <div class="vcard-header">
        <span class="vtype vtype-${e.t}">${e.t}</span>
        <span class="vkey">${e.k}</span>
        ${e.lbl?`<span class="vlabel">"${e.lbl}"</span>`:''}
        ${e.sid?`<span class="vsid">${e.sid}</span>`:''}
        ${isIssue?'<span style="color:var(--rose);font-size:10px;background:rgba(251,113,133,.1);border:1px solid var(--rose);padding:1px 6px;border-radius:3px">⚠ unknown</span>':''}
        ${isModified?'<span style="color:var(--accent2);font-size:10px">✏ modifié</span>':''}
        ${e.frag?`<span style="font-size:9px;color:var(--dim);background:var(--bg4);padding:1px 5px;border-radius:3px;font-family:monospace" title="Fragment brut extrait du nom">"${e.frag}"</span>`:''}
      </div>
      <div class="vcard-body">
        <div class="vfields">
          <div class="vfield">
            <div class="vf-label">process.level1</div>
            <select class="vf-select${ovr.l1!==undefined?' mod':''}" onchange="setVOvr('${vid}','l1',this.value)">
              ${L1_OPTIONS.map(v=>`<option value="${v}"${(l1||'')==v?'selected':''}>${v}</option>`).join('')}
            </select>
          </div>
          <div class="vfield">
            <div class="vf-label">process.level2</div>
            <select class="vf-select${ovr.l2!==undefined?' mod':''}" onchange="setVOvr('${vid}','l2',this.value)">
              ${L2_OPTIONS.map(v=>`<option value="${v||'null'}"${(l2||'null')===(v||'null')?'selected':''}>${v||'— aucun'}</option>`).join('')}
            </select>
          </div>
          <div class="vfield">
            <div class="vf-label">variety</div>
            <input class="vf-input${ovr.variety!==undefined?' mod':''}" value="${variety}"
              oninput="setVOvr('${vid}','variety',this.value)" placeholder="—"/>
          </div>
          <div class="vfield">
            <div class="vf-label">preservation</div>
            <select class="vf-select${ovr.preservation!==undefined?' mod':''}" onchange="setVOvr('${vid}','preservation',this.value)">
              ${PRES_OPTIONS.map(v=>`<option value="${v}"${(pres||'null')===v?'selected':''}>${v==='null'?'— aucun':v}</option>`).join('')}
            </select>
          </div>
          <div class="vfield">
            <div class="vf-label">physical_form</div>
            <select class="vf-select${ovr.physical_form!==undefined?' mod':''}" onchange="setVOvr('${vid}','physical_form',this.value)">
              ${FORM_OPTIONS.map(v=>`<option value="${v}"${(form||'null')===v?'selected':''}>${v==='null'?'— aucun':v}</option>`).join('')}
            </select>
          </div>
          <div class="vfield">
            <div class="vf-label">part</div>
            <select class="vf-select${ovr.part!==undefined?' mod':''}" onchange="setVOvr('${vid}','part',this.value)">
              ${PART_OPTIONS.map(v=>`<option value="${v}"${(part_||'null')===v?'selected':''}>${v==='null'?'— aucun':v}</option>`).join('')}
            </select>
          </div>
          ${e.conf!==null&&e.conf!==undefined?`<div class="vfield">
            <div class="vf-label">Confiance</div>
            <div class="vf-readonly">${Math.round((e.conf||0)*100)}%</div>
          </div>`:''}
        </div>
        ${e.lbl&&!e.frag?`<div class="vcue">🏷 Nom brut complet : "${e.lbl}"</div>`:''}
      </div>
      ${e.ch&&e.ch.length?`<div class="vcard-children">${renderVEntries(canon,src,bk,e.ch,depth+1)}</div>`:''}
    </div>`;
  });
  return html;
}

function setVOvr(vid,field,val){
  if(!VS[vid])VS[vid]={};
  if(val==='null'||val==='')delete VS[vid][field];
  else VS[vid][field]=val;
  if(!Object.keys(VS[vid]).length)delete VS[vid];
  upStats();
  // Update vcard style
  const ek=vid.replace(/[^a-z0-9]/gi,'_');
  const card=document.getElementById('vc-'+ek);
  if(card){
    const isM=!!VS[vid];
    card.classList.toggle('modified',isM);
  }
}

// ════════════════════════════════════════════════════════════
//  EXPORT
// ════════════════════════════════════════════════════════════
function openExport(){
  const lines=['# ═══ BASE_INGREDIENT_MAP ═══','# Source bk → canonical bk','','BASE_INGREDIENT_MAP = {'];
  const byGroup={};
  TAXONOMY.forEach(g=>g.entries.forEach(e=>{
    const s=S[g.id+'|'+e.bk]; if(!s||s.rejected||e.bk===s.canon)return;
    if(!byGroup[g.label])byGroup[g.label]=[];
    byGroup[g.label].push({bk:e.bk,canon:s.canon,gl:g.label,note:s.note});
  }));
  Object.entries(byGroup).forEach(([gl,entries])=>{
    lines.push('  # ── '+gl+' ──');
    entries.forEach(x=>lines.push('  "'+x.bk+'": {"base_key": "'+x.canon+'", "group_label": "'+x.gl+'"},  '+( x.note?'# '+x.note:'')));
    lines.push('');
  });
  lines.push('}','','');

  if(Object.keys(VS).length){
    lines.push('# ═══ STATE_OVERRIDES ═══','# Corrections manuelles des états de variants','# Format: "source_id|canonical|bk|variant_key" -> corrections','','STATE_OVERRIDES = {');
    Object.entries(VS).forEach(([vid,ovr])=>{
      const[canon,src,bk,vk]=vid.split('|');
      const ovrStr=Object.entries(ovr).map(([k,v])=>'"'+k+'": "'+v+'"').join(', ');
      lines.push('  # '+src+' / '+bk+' / '+vk);
      lines.push('  "'+vid+'": {'+ovrStr+'},');
    });
    lines.push('}');
  }

  document.getElementById('ex-content').textContent=lines.join('\n');
  document.getElementById('modal').classList.add('open');
}
function closeExport(){document.getElementById('modal').classList.remove('open');}
function copyExport(){navigator.clipboard.writeText(document.getElementById('ex-content').textContent).then(()=>{const b=document.querySelector('.modal .btn-s');b.textContent='✅ Copié!';setTimeout(()=>b.textContent='📋 Copier',2000);});}
document.addEventListener('keydown',e=>{if(e.key==='Escape')closeExport();});

// ── Init ─────────────────────────────────────────────────────
renderTree();
upStats();
if(TAXONOMY.length) selectGroup(TAXONOMY[0].id);
renderCanonList();
</script>
</body>
</html>""".replace("%%TAXONOMY%%", taxonomy_json).replace("%%VARIANTS%%", variants_json)

with open("taxonomy_review.html","w",encoding="utf-8") as f:
    f.write(HTML)

sz = len(HTML)
print(f"taxonomy_review.html: {sz//1024}KB")

# Cleanup
import os
for tmp in ["enhanced_taxonomy.json","variants_data.json"]:
    try: os.remove(tmp)
    except: pass
print("Done.")
