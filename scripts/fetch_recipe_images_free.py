"""
Vegalim — Photos de recettes depuis des sources libres de droits
================================================================

Sources, sans clé API :
  * Wikimedia Commons (CC BY, CC BY-SA, CC0, domaine public)
  * Openverse, filtré sur les licences autorisant l'usage commercial
    et les œuvres dérivées (donc ni NC ni ND)

Le script ne devine jamais : une photo n'est retenue que si son titre
contient un mot distinctif du nom du plat, et il écarte tout ce qui sent
la viande ou le poisson. Les recettes sans correspondance sûre sont
listées dans _unmatched.json pour une reprise à la main.

Chaque image téléchargée est créditée (auteur, licence, page source)
dans _credits.json et CREDITS.md : c'est obligatoire pour les licences CC.

Usage :
    python scripts/fetch_recipe_images_free.py --limit 25            # essai
    python scripts/fetch_recipe_images_free.py --slug pav-bhaji ...  # ciblé
    python scripts/fetch_recipe_images_free.py                       # tout
    python scripts/fetch_recipe_images_free.py --dry-run             # sans écrire
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Module 'requests' manquant : pip install requests")

# la console Windows est en cp1252 : on force l'UTF-8 pour les titres etrangers
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

ROOT = Path(__file__).resolve().parent.parent
RECIPES = ROOT / "backend" / "data" / "recipes" / "recipes.json"
OUT = ROOT / "frontend" / "public" / "images" / "recipes"
CREDITS_JSON = OUT / "_credits.json"
CREDITS_MD = OUT / "CREDITS.md"
UNMATCHED = OUT / "_unmatched.json"
# Photos deja ecartees a la relecture visuelle (viande visible, sujet hors
# propos). Elles reviennent sinon sur une autre recette : la photo de marche
# aux legumes avait ete retenue une douzaine de fois.
BLOCKLIST = OUT / "_blocklist.json"

UA = "VegalimImageBot/1.0 (https://github.com/taupe80-codage/Vegalim; taupe80@gmail.com)"
# Flickr (ou Openverse heberge la plupart de ses images) renvoie 403 des que
# le User-Agent contient « Bot ». Wikimedia, lui, exige un agent descriptif :
# on garde donc un agent par usage.
UA_DOWNLOAD = "Vegalim/1.0 (+https://github.com/taupe80-codage/Vegalim; taupe80@gmail.com)"
TARGET_WIDTH = 1080
MIN_WIDTH = 500
DELAY = 0.7  # politesse envers Commons et Openverse

# ── Filtres ───────────────────────────────────────────────────────────────────

# Le site est végétarien : toute photo qui annonce viande ou poisson est écartée.
# Les titres de Commons sont dans toutes les langues (« Spätzle med svinekotelet »),
# donc on cherche des RACINES en début de mot, plusieurs langues à la fois.
# Racines assez distinctives pour être cherchées n'importe où dans un mot :
# c'est ce qui permet d'attraper les mots composés (« svinekotelet », « Hähnchenbrust »).
MEAT_ANYWHERE = (
    "meat", "beef", "pork", "bacon", "sausag", "chorizo", "salami", "pancetta",
    "chicken", "poultry", "turkey", "mutton", "steak", "brisket", "jerky",
    "prosciut", "pepperoni", "bologna", "seafood", "salmon", "mackerel", "herring",
    "trout", "anchov", "sardine", "shrimp", "prawn", "lobster", "squid", "octopus",
    "mussel", "oyster", "scallop", "caviar", "bonito", "katsuobushi", "worcester",
    "escargot", "tripe", "viande", "boeuf", "poulet", "jambon", "saucis", "agneau",
    "canard", "lardon", "poisson", "crevette", "saumon", "anchois", "charcut",
    "merguez", "rillette", "magret", "fleisch", "schwein", "schinken", "wurst",
    "hahnchen", "kotelet", "kylling", "gehakt", "lachs", "forelle", "hering",
    "carne", "cerdo", "jamon", "chuleta", "ternera", "cordero", "chicharr",
    "frango", "porco", "presunto", "linguic", "maiale", "manzo", "salsiccia",
    "vitello", "agnello", "pesce", "pescado", "peixe", "bacalao", "marisco",
    "camaron", "gosht", "murgh", "keema", "kheema", "kebab", "shawarma", "gyros",
    "nikuman", "tonkatsu", "tonkotsu", "chashu", "yakitori", "bulgogi",
    "samgyeopsal", "sucuk", "pastirma", "biltong", "kottbull", "kottfars",
    "skinka", "korv", "frikadell", "boulette de viande", "tasajo", "guanciale",
    "cecina", "carnitas", "barbacoa", "birria", "lengua", "chicharron", "pernil",
    "cochinita", "milanesa", "albondiga", "morcilla", "longaniza", "pastrami",
)

# Mots trop courts ou trop ambigus pour une recherche en sous-chaîne
# (« rib » est dans « ribollita », « ham » dans « hamantaschen ») : mot entier.
MEAT_WORDS = {
    "veal", "ham", "cod", "rib", "ribs", "duck", "goose", "lamb", "liver", "fish",
    "eel", "snail", "frog", "offal", "clam", "clams", "crab", "crabs", "tuna",
    "dashi", "porc", "thon", "foie", "bavette", "huhn", "rind", "kalb", "speck",
    "svin", "okse", "kod", "flask", "kjott", "kip", "vis", "vlees", "varken",
    "rund", "pollo", "lomo", "atun", "gamba", "gambas", "buta", "galbi", "unagi",
    "pesci", "carnitas", "barbacoa", "birria", "lengua", "chicharron",
    "kott", "biff", "kjott", "lever",
}

# Faux amis : mots qui contiennent une racine ci-dessus sans parler de viande.
MEAT_SAFE = {
    "porcini", "porcelain", "porcelaine", "carnival", "carnaval", "carnation",
    "carnitasless", "ribollita", "ribbon", "ribes", "duckweed", "hamantaschen",
    "lambic", "lamington", "kipferl", "carneros", "carnegie",
}

# Images qui ne montrent pas une assiette : plans, logos, cartes, panneaux…
NOT_FOOD = {
    "map", "logo", "coat", "arms", "flag", "poster", "sign", "signboard", "banner",
    "diagram", "chart", "graph", "portrait", "statue", "monument", "building",
    "facade", "storefront", "restaurant exterior", "menu", "receipt", "packaging",
    "package", "label", "bottle cap", "stamp", "coin", "book", "cover", "screenshot",
    "carte", "affiche", "panneau", "enseigne", "logotype", "blason", "drapeau",
    # vivants et lieux : le puceron du haricot noir, le temple, le jardin
    "aphid", "insect", "beetle", "larva", "caterpillar", "pest", "weed", "bird",
    "cow", "cattle", "pig", "sheep", "hen", "rooster", "temple", "shrine",
    "church", "mosque", "museum", "palace", "castle", "park", "garden", "farm",
    "field", "plantation", "greenhouse", "harvest", "tree", "blossom", "flower",
    "landscape", "street", "village", "town", "city", "station", "airport",
    "figurine", "doll", "toy", "sculpture", "model", "mannequin", "poupee",
    "puceron", "insecte", "jardin", "ferme", "champ", "arbre", "fleur", "eglise",
    "musee", "chateau", "village", "ville", "paysage", "recolte",
}

# Mots trop génériques pour prouver qu'une photo montre le bon plat.
GENERIC = {
    "vegan", "vegetarian", "vegetarien", "vegetarienne", "vegetariennes", "vege",
    "homemade", "maison", "fait", "recipe", "recette", "style", "facon", "la", "le",
    "les", "de", "du", "des", "au", "aux", "a", "et", "en", "the", "of", "with",
    "and", "for", "in", "on", "sans", "avec", "plat", "dish", "food", "cuisine",
    "express", "rapide", "quick", "easy", "simple", "classique", "classic", "base",
    "traditionnel", "traditionnelle", "traditional", "nature", "preparation",
    "fresh", "frais", "fraiche", "chaud", "froid", "cold", "hot", "new", "veggie",
    "grand", "petit", "petits", "grande", "mere", "jour", "bowl", "assiette",
    # nationalites : « japonais » dans une requete ramene des jardins japonais
    "italienne", "italien", "italian", "italiano", "francaise", "francais",
    "french", "japonais", "japonaise", "japanese", "chinois", "chinoise",
    "chinese", "indien", "indienne", "indian", "mexicaine", "mexicain",
    "mexican", "mexicana", "espagnole", "espagnol", "spanish", "espanola",
    "grecque", "grec", "greek", "turque", "turc", "turkish", "libanais",
    "libanaise", "lebanese", "marocain", "marocaine", "moroccan", "thailandais",
    "thai", "vietnamien", "vietnamienne", "vietnamese", "coreen", "coreenne",
    "korean", "allemand", "allemande", "german", "polonais", "polonaise",
    "polish", "russe", "russian", "portugais", "portugaise", "portuguese",
    "bresilien", "bresilienne", "brazilian", "peruvien", "peruvienne",
    "peruvian", "argentin", "argentine", "ethiopien", "ethiopienne",
    "ethiopian", "nepalais", "nepalaise", "nepali", "iranien", "iranienne",
    "persian", "persan", "persane", "quebecois", "quebecoise", "americain",
    "americaine", "american", "anglais", "anglaise", "english", "bretonnes",
    "bretonne", "breton", "alsaciennes", "alsacienne", "alsacien", "provencal",
    "provencale", "napolitaine", "napolitain", "neapolitan", "sicilienne",
    "sicilien", "sicilian", "traditionnelles",
}


def strip_accents(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


def slugify(text: str) -> str:
    """Identique à slugify() du frontend (RecipeCard.jsx)."""
    text = strip_accents(text).lower().strip().replace(chr(92), "-")
    text = re.sub(r"[\s_/]+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    return re.sub(r"-+", "-", text).strip("-")


def words(text: str) -> list[str]:
    return [w for w in re.split(r"[^a-z0-9]+", strip_accents(text).lower()) if w]


def key_words(title: str) -> list[str]:
    """Mots distinctifs du nom du plat, les plus parlants d'abord."""
    out = []
    for w in words(title):
        if len(w) > 2 and w not in GENERIC and w not in out:
            out.append(w)
    return out


# ── Recettes ──────────────────────────────────────────────────────────────────

def load_recipes() -> list[dict]:
    data = json.loads(RECIPES.read_text(encoding="utf-8"))
    recipes = data["recipes"] if isinstance(data, dict) else data
    items = []
    for r in recipes:
        t = r.get("titles", {})
        fr = t.get("fr") or t.get("en") or t.get("original") or ""
        if not fr:
            continue
        items.append({
            "slug": slugify(fr),
            "fr": fr,
            "en": t.get("en", ""),
            "original": t.get("original", ""),
            "dish_type": r.get("dish_type", ""),
            "cuisine": r.get("origin", {}).get("cuisine", ""),
        })
    return items


def build_queries(item: dict) -> list[str]:
    """Du plus précis au plus large, sans jamais perdre le nom du plat."""
    out, seen = [], set()

    def add(q):
        q = re.sub(r"\s+", " ", q).strip(" ,-")
        if q and len(q) > 2 and q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)

    for title in (item["en"], item["original"], item["fr"]):
        if not title:
            continue
        # « Paneer Makhani de Delhi (paneer butter masala) » → on garde aussi la parenthèse
        inner = re.findall(r"\(([^)]+)\)", title)
        clean = re.sub(r"\([^)]*\)", "", title)
        # la partie avant la première virgule ou tiret porte le nom du plat
        head = re.split(r"[,—–]|\s-\s", clean)[0]
        add(head)
        for i in inner:
            add(i)
        add(clean)

    # Dernier repli : le mot long et singulier du nom du plat (« bannock »,
    # « panzanella », « tostadas »). On ne tronque jamais sur les premiers mots :
    # « oven baked bannock » réduit à « oven baked » ramenait des portes de four.
    # On ne cherche le mot long que parmi les trois premiers mots distinctifs,
    # la ou se trouve le nom du plat, et on garde le dernier : en anglais comme
    # en francais, c'est le nom et non l'adjectif (« Breton Buckwheat Galettes »
    # donne « galettes », pas « buckwheat »).
    # Le nom du plat est le mot le plus long du groupe de tete : « salmorejo »
    # avant « cordobes », « panzanella » avant « italienne ». On essaie les
    # candidats du plus long au plus court.
    for title, english in ((item["en"], True), (item["original"], True),
                           (item["fr"], False)):
        head = key_words(re.split(r"[,—–]|\s-\s", title or "")[0])[:3]
        longs = [w for w in head if len(w) >= 7 and w not in PLAIN_INGREDIENTS]
        if not longs:
            continue
        for w in sorted(longs, key=len, reverse=True):
            add(w)
        break
    return out[:6]


# ── Pertinence ────────────────────────────────────────────────────────────────

def rejected_for(text: str) -> str:
    """Motif de rejet, ou chaîne vide. En cas de doute on rejette : mieux vaut
    une recette sans photo qu'une assiette de viande sur un site végétarien."""
    ws = words(text)
    for w in ws:
        if w in MEAT_SAFE:
            continue
        if w in MEAT_WORDS:
            return f"viande/poisson ({w})"
        for root in MEAT_ANYWHERE:
            if root in w:
                return f"viande/poisson ({w})"
    bag = set(ws)
    for bad in NOT_FOOD:
        if bad in bag:
            return f"hors sujet ({bad})"
    return ""


def covers(candidate_title: str, query: str) -> int:
    """Le titre de la photo contient-il TOUS les mots distinctifs de la requête ?

    Renvoie le nombre de mots couverts, ou 0 s'il en manque un. C'est la règle
    qui évite « Oven baked banana bread » pour « oven baked bannock » : il suffit
    qu'un seul mot du plat manque pour écarter la photo.
    """
    needed = key_words(query)
    if not needed:
        return 0
    have = set(words(candidate_title))
    for w in needed:
        hit = w in have or (len(w) >= 6 and any(
            h.startswith(w[:-1]) or w.startswith(h[:-1]) for h in have if len(h) >= 5))
        if not hit:
            return 0
    return len(needed)


# ── Sources ───────────────────────────────────────────────────────────────────

def clean_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def search_commons(session: requests.Session, query: str) -> list[dict]:
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}", "gsrnamespace": "6", "gsrlimit": "10",
        "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": str(TARGET_WIDTH),
    }
    try:
        r = session.get("https://commons.wikimedia.org/w/api.php", params=params, timeout=25)
        if r.status_code != 200:
            return []
        pages = (r.json().get("query") or {}).get("pages") or {}
    except (requests.RequestException, ValueError):
        return []

    out = []
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        if not info or info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if (info.get("width") or 0) < MIN_WIDTH:
            continue
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName", {}).get("value") or "").strip()
        low = lic.lower()
        free = (
            "cc0" in low or "public domain" in low
            or low.startswith("cc by") or "cc-by" in low
        )
        # CC BY-ND interdit les œuvres dérivées (recadrage, redimensionnement)
        if not free or {"nd", "by-nd"} & set(re.split(r"[^a-z0-9-]+", low)):
            continue
        out.append({
            "source": "Wikimedia Commons",
            "title": page.get("title", "").removeprefix("File:"),
            "download": info.get("thumburl") or info.get("url"),
            "page": info.get("descriptionurl", ""),
            "author": clean_html(meta.get("Artist", {}).get("value", "")) or "inconnu",
            "license": lic,
            "width": info.get("thumbwidth") or info.get("width"),
            "height": info.get("thumbheight") or info.get("height"),
            "categories": clean_html(meta.get("Categories", {}).get("value", "")),
        })
    return out


def api_get(session: requests.Session, url: str, params: dict) -> dict | None:
    """Appel d'API MediaWiki avec reprise : interroges en parallele, les wikis
    repondent 429 ou 503, et un echec silencieux se lisait a tort comme
    « ce plat n'a pas d'article »."""
    for essai in range(4):
        try:
            r = session.get(url, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            if r.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (essai + 1))
                continue
            return None
        except (requests.RequestException, ValueError):
            time.sleep(1.0 * (essai + 1))
    return None


def commons_file(session: requests.Session, filename: str) -> dict | None:
    """Métadonnées Commons d'un fichier précis : licence, auteur, miniature.

    Une image hébergée localement sur un wiki (et non sur Commons) revient
    absente : c'est souvent une image sous usage loyal, qu'on ne veut pas.
    """
    params = {
        "action": "query", "format": "json", "titles": f"File:{filename}",
        "prop": "imageinfo", "iiprop": "url|mime|size|extmetadata",
        "iiurlwidth": str(TARGET_WIDTH),
    }
    data = api_get(session, "https://commons.wikimedia.org/w/api.php", params)
    if not data:
        return None
    pages = (data.get("query") or {}).get("pages") or {}

    for page in pages.values():
        if "missing" in page:
            continue
        info = (page.get("imageinfo") or [{}])[0]
        if not info or info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        # l'image d'un article encyclopedique est la bonne photo du plat,
        # meme en resolution modeste : on accepte plus petit qu'ailleurs
        if (info.get("width") or 0) < 320:
            continue
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName", {}).get("value") or "").strip()
        low = lic.lower()
        free = ("cc0" in low or "public domain" in low
                or low.startswith("cc by") or "cc-by" in low)
        if not free or {"nd", "by-nd"} & set(re.split(r"[^a-z0-9-]+", low)):
            continue
        return {
            "source": "Wikimedia Commons",
            "title": page.get("title", "").removeprefix("File:"),
            "download": info.get("thumburl") or info.get("url"),
            "page": info.get("descriptionurl", ""),
            "author": clean_html(meta.get("Artist", {}).get("value", "")) or "inconnu",
            "license": lic,
            "width": info.get("thumbwidth") or info.get("width"),
            "height": info.get("thumbheight") or info.get("height"),
            "categories": clean_html(meta.get("Categories", {}).get("value", "")),
        }
    return None


def search_wikipedia(session: requests.Session, query: str) -> list[dict]:
    """Image principale de l'article encyclopédique du plat.

    C'est la piste la plus sûre : l'article « Chilaquiles » est illustré par
    une assiette de chilaquiles, pas par un fichier dont le nom contient le
    mot. On vérifie ensuite que le titre de l'article correspond bien au plat
    cherché — sinon on écarte, parce que la recherche d'un wiki répond
    toujours quelque chose.
    """
    out = []
    for lang in ("fr", "en"):
        params = {
            "action": "query", "format": "json",
            "generator": "search", "gsrsearch": query, "gsrlimit": "3",
            "gsrnamespace": "0",
            "prop": "pageimages", "piprop": "original|name", "pilicense": "any",
        }
        data = api_get(session, f"https://{lang}.wikipedia.org/w/api.php", params)
        if not data:
            continue
        pages = (data.get("query") or {}).get("pages") or {}

        for page in sorted(pages.values(), key=lambda p: p.get("index", 99)):
            fichier = page.get("pageimage")
            titre_article = page.get("title", "")
            if not fichier or not titre_article:
                continue
            # L'article doit parler du plat cherché, et son titre ne doit pas
            # annoncer de viande : « Kung Pao chicken » mène à « Poulet
            # impérial », dont l'image est un plat de poulet.
            if not covers(titre_article, query):
                continue
            if rejected_for(titre_article):
                continue
            cand = commons_file(session, fichier)
            if not cand:
                continue
            # Un mot peut nommer un plat et tout autre chose : « Festival »,
            # « Cou », « Fenouil » ont un article, qui n'illustre pas une
            # assiette. Les categories Commons de l'image doivent dire que
            # c'est de la nourriture, sauf si l'article reprend au moins deux
            # mots du plat et ne laisse donc plus de doute.
            nourriture = bool(set(words(cand["categories"])) & FOOD_MARKERS)
            if not nourriture and covers(titre_article, query) < 2:
                continue
            cand["source"] = f"Wikipédia ({lang}) · Wikimedia Commons"
            cand["article"] = titre_article
            # c'est le titre de l'article qui prouve la pertinence, pas le
            # nom du fichier, souvent cryptique (« Alicha_1.jpg »)
            cand["match_title"] = titre_article
            out.append(cand)
            break
        if out:
            break
    return out


def search_openverse(session: requests.Session, query: str) -> list[dict]:
    params = {
        "q": query, "page_size": "10",
        # usage commercial + œuvres dérivées autorisés : exclut NC et ND
        "license_type": "commercial,modification",
        "mature": "false", "extension": "jpg,png",
    }
    try:
        r = session.get("https://api.openverse.org/v1/images/", params=params, timeout=25)
        if r.status_code != 200:
            return []
        results = r.json().get("results") or []
    except (requests.RequestException, ValueError):
        return []

    out = []
    for res in results:
        if (res.get("width") or 0) < MIN_WIDTH:
            continue
        lic = f"CC {(res.get('license') or '').upper()} {res.get('license_version') or ''}".strip()
        out.append({
            "source": res.get("source") or "Openverse",
            "title": res.get("title") or "",
            "download": res.get("url"),
            "page": res.get("foreign_landing_url") or "",
            "author": res.get("creator") or "inconnu",
            "license": lic,
            "width": res.get("width"),
            "height": res.get("height"),
            "categories": " ".join(res.get("tags_list") or []),
        })
    return out


# Un ingredient courant ne suffit pas a identifier un plat : chercher
# « coconut » pour un fromage vegetal au lait de coco ramene une tarte a la
# noix de coco. Dans ce cas on prefere ne rien retenir.
PLAIN_INGREDIENTS = {
    "coconut", "chocolate", "chocolat", "scrambled", "brouille", "gingembre",
    "ginger", "chickpea", "chickpeas", "lentils", "lentilles", "potato",
    "potatoes", "tomato", "tomatoes", "tomate", "tomates", "cheese", "fromage",
    "pumpkin", "potiron", "butternut", "courgette", "zucchini", "aubergine",
    "eggplant", "mushroom", "mushrooms", "champignon", "champignons", "spinach",
    "epinards", "cabbage", "chou", "carrot", "carrots", "carotte", "carottes",
    "avocado", "avocat", "banana", "banane", "apple", "pomme", "pommes",
    "strawberry", "fraise", "fraises", "cinnamon", "cannelle", "vanilla",
    "vanille", "almond", "amande", "amandes", "peanut", "cacahuete", "sesame",
    "noisette", "noisettes", "myrtille", "myrtilles", "blueberry", "blueberries",
    "asperges", "asparagus", "artichoke", "artichaut", "betterave", "beetroot",
    "concombre", "cucumber", "haricots", "haricot", "poivron", "poivrons",
    "pepper", "peppers", "oignon", "oignons", "onion", "onions", "garlic",
    "patate", "sarrasin", "boulgour", "semoule", "quinoa", "legumes",
    "vegetal", "vegetale", "fondant", "fondante", "creme", "cremeuse",
}

# Preuve qu'on regarde bien un plat, et pas un jardin japonais ou un puceron
# du haricot noir : un de ces mots doit apparaître dans le titre, les catégories
# Commons ou les tags Openverse.
FOOD_MARKERS = {
    "food", "foods", "dish", "dishes", "cuisine", "cooking", "cooked", "cookery",
    "recipe", "recipes", "meal", "meals", "plate", "plated", "bowl", "serving",
    "soup", "soups", "stew", "stews", "salad", "salads", "bread", "breads",
    "cake", "cakes", "pie", "pies", "pastry", "pastries", "dessert", "desserts",
    "snack", "snacks", "breakfast", "lunch", "dinner", "supper", "street",
    "tofu", "tempeh", "seitan", "paneer", "cheese", "yogurt", "yoghurt", "egg",
    "eggs", "rice", "pasta", "noodle", "noodles", "dumpling", "dumplings",
    "curry", "curries", "sauce", "sauces", "paste", "pizza", "sandwich", "taco",
    "tacos", "burrito", "wrap", "pancake", "pancakes", "waffle", "porridge",
    "drink", "drinks", "beverage", "beverages", "tea", "coffee", "juice",
    "smoothie", "cocktail", "pickle", "pickles", "pickled", "fermented",
    "vegetable", "vegetables", "vegetarian", "vegan", "legume", "legumes",
    "bean", "beans", "lentil", "lentils", "potato", "potatoes", "cereal",
    "flatbread", "pastries", "confectionery", "gastronomy", "restaurant",
    "nourriture", "plat", "plats", "assiette", "soupe", "soupes", "salade",
    "salades", "pain", "gateau", "patisserie", "dessert", "boisson", "cuisine",
    "legume", "legumes", "fromage", "riz", "pates", "nouilles", "sauce",
    "comida", "platos", "cibo", "piatto", "essen", "gericht", "speise",
}

# Une photo d'ingrédients crus ou de gros plan n'illustre pas le plat.
WEAK = {"ingredienti", "ingredients", "ingredient", "raw", "crudo", "cru", "crue",
        "seeds", "graines", "plant", "plante", "leaves", "feuilles", "tree", "field",
        "market", "marche", "shop", "closeup", "macro", "detail", "texture"}


def load_blocklist() -> set:
    if not BLOCKLIST.exists():
        return set()
    try:
        return {" ".join(words(t)) for t in json.loads(BLOCKLIST.read_text(encoding="utf-8"))}
    except ValueError:
        return set()


def pick(session: requests.Session, item: dict, min_hits: int = 1,
         blocked: set | None = None, sources: tuple = ()):
    """Meilleure photo pertinente, Commons d'abord (licences plus simples).

    Une photo n'est retenue que si son titre couvre TOUS les mots distinctifs
    de la requête : « Pesto Genovese » exige pesto ET genovese. Les requêtes
    sont essayées de la plus précise à la plus large, et on s'arrête à la
    première qui donne un résultat — donc au nom de plat le plus complet.
    """
    tried = []
    # Commons répond en une seconde, Openverse en une quinzaine : on épuise
    # d'abord toutes les requêtes sur Commons, et on ne sollicite Openverse
    # que pour les plats qu'il n'a pas.
    finders = sources or (search_wikipedia, search_commons, search_openverse)
    for rank, finder in enumerate(finders):
        for query in build_queries(item):
            batch = []
            for pos, cand in enumerate(finder(session, query)):
                if blocked and " ".join(words(cand["title"])) in blocked:
                    tried.append(f"{cand['title'][:40]} → deja ecartee a la relecture")
                    continue
                haystack = f"{cand['title']} {cand['categories']}"
                why = rejected_for(haystack)
                if why:
                    tried.append(f"{cand['title'][:40]} → {why}")
                    continue
                # Une image d'article prouve sa pertinence par le titre de
                # l'article, déjà vérifié : le nom du fichier est souvent
                # cryptique et les heuristiques ci-dessous n'ont pas de sens.
                if cand.get("match_title"):
                    cand.update(query=query, hits=covers(cand["match_title"], query))
                    batch.append(((-99, 0, rank, pos), cand))
                    continue

                hits = covers(cand["title"], query)
                if hits < max(1, min_hits):
                    tried.append(f"{cand['title'][:40]} → nom du plat incomplet")
                    continue

                title_words = [w for w in words(cand["title"])
                               if not w.isdigit() and len(w) > 2]
                evidence = set(title_words) | set(words(cand["categories"]))
                rare_head = (hits == 1 and title_words
                             and title_words[0] in key_words(query)
                             and len(title_words[0]) >= 7 and len(title_words) <= 2)
                if not (evidence & FOOD_MARKERS) and hits < 2 and not rare_head:
                    tried.append(f"{cand['title'][:40]} → rien ne dit que c'est un plat")
                    continue
                # Un seul mot-clé commun : on n'accepte qu'un titre court où le
                # nom du plat est en tête (« Enchiladas-rojas.jpg »), sinon le
                # mot peut n'être qu'un détail de la légende.
                if hits == 1 and (len(title_words) > 5
                                  or not (set(title_words[:3]) & set(key_words(query)))):
                    tried.append(f"{cand['title'][:40]} → mot-clé noyé dans la légende")
                    continue
                weak = len(WEAK & set(words(cand["title"])))
                cand.update(query=query, hits=hits)
                # tri : mots couverts, puis photo de plat, puis source, puis rang
                batch.append(((-hits, weak, rank, pos), cand))
            if batch:
                batch.sort(key=lambda b: b[0])
                return batch[0][1], tried
            time.sleep(DELAY)
    return None, tried


def download(session: requests.Session, url: str, dest: Path) -> bool:
    try:
        r = session.get(url, timeout=60, stream=True,
                        headers={"User-Agent": UA_DOWNLOAD})
        r.raise_for_status()
        tmp = dest.with_suffix(".part")
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        if tmp.stat().st_size < 8000:  # fichier manifestement vide ou cassé
            tmp.unlink(missing_ok=True)
            return False
        tmp.replace(dest)
        return True
    except Exception:
        return False


# ── Crédits ───────────────────────────────────────────────────────────────────

def load_credits() -> dict:
    if CREDITS_JSON.exists():
        try:
            return json.loads(CREDITS_JSON.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return {}


def save_credits(credits: dict) -> None:
    CREDITS_JSON.write_text(json.dumps(credits, ensure_ascii=False, indent=1, sort_keys=True),
                            encoding="utf-8")
    lines = [
        "# Crédits photos des recettes",
        "",
        "Chaque photo ci-dessous vient de Wikimedia Commons ou d'Openverse, sous une",
        "licence autorisant l'usage commercial et les œuvres dérivées. L'attribution",
        "est obligatoire : ne retirez pas ce fichier et gardez-le à jour.",
        "",
        "| Recette | Auteur | Licence | Source |",
        "| --- | --- | --- | --- |",
    ]
    for slug in sorted(credits):
        c = credits[slug]
        page = c.get("page") or ""
        src = f"[{c.get('source', '')}]({page})" if page else c.get("source", "")
        lines.append(f"| `{slug}` | {c.get('author', '')} | {c.get('license', '')} | {src} |")
    CREDITS_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="n'traiter que les N premières")
    ap.add_argument("--slug", nargs="*", help="slugs précis à traiter")
    ap.add_argument("--dry-run", action="store_true", help="chercher sans télécharger")
    ap.add_argument("--min-hits", type=int, default=1, help="mots-clés exigés dans le titre")
    ap.add_argument("--source", choices=("all", "wikipedia"), default="all",
                    help="wikipedia : uniquement l'image de l'article du plat")
    ap.add_argument("--workers", type=int, default=6,
                    help="recherches menées en parallèle (6 par défaut)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers["User-Agent"] = UA

    items = load_recipes()
    if args.slug:
        wanted = set(args.slug)
        todo = [i for i in items if i["slug"] in wanted]
    else:
        todo = [i for i in items if not (OUT / f"{i['slug']}.jpg").exists()]
    if args.limit:
        todo = todo[:args.limit]

    print(f"{len(items)} recettes, {len(todo)} à traiter"
          f"{' (simulation)' if args.dry_run else ''}\n")

    finders = (search_wikipedia,) if args.source == "wikipedia" else ()
    credits = load_credits()
    blocked = load_blocklist()
    if args.slug:
        # on refait ces recettes : la photo actuelle est justement celle a eviter
        blocked |= {" ".join(words(credits[s]["title"]))
                    for s in args.slug if s in credits and credits[s].get("title")}
    # une photo deja utilisee par une autre recette ne doit pas resservir :
    # sans cela, les quatre variantes de gnocchi recevaient la meme assiette
    refaits = set(args.slug or ())
    blocked |= {" ".join(words(c["title"])) for sl, c in credits.items()
                if sl not in refaits and c.get("title")}
    unmatched = []
    ok = fail = 0

    # Une recette sans correspondance coute 12 requetes : en series, les 535
    # recettes demandaient une nuit entiere. Quelques fils suffisent a tenir
    # la charge sans brusquer Commons, chacun avec sa propre session HTTP.
    lock = threading.Lock()
    done = [0]
    local = threading.local()

    def session_for_thread() -> requests.Session:
        if not hasattr(local, "session"):
            local.session = requests.Session()
            local.session.headers["User-Agent"] = UA
        return local.session

    def handle(item: dict) -> None:
        nonlocal ok, fail
        cand, tried = pick(session_for_thread(), item, args.min_hits, blocked, finders)
        line_no = None
        with lock:
            done[0] += 1
            line_no = done[0]

        if not cand:
            with lock:
                print(f"[{line_no}/{len(todo)}] {item['fr'][:55]:<55} aucune photo sûre")
                unmatched.append({**item, "essais": tried[:6]})
                fail += 1
            return

        label = f"{cand['source']} · {cand['license']} · {cand['author'][:24]}"
        if args.dry_run:
            with lock:
                print(f"[{line_no}/{len(todo)}] {item['fr'][:55]:<55} "
                      f"OK {cand['hits']} mot(s) — {cand['title'][:45]}")
                if args.verbose:
                    print(f"      {label}\n      {cand['download']}")
                ok += 1
            return

        got = download(session_for_thread(), cand["download"], OUT / f"{item['slug']}.jpg")
        with lock:
            if got:
                blocked.add(" ".join(words(cand["title"])))
                credits[item["slug"]] = {
                    "recipe": item["fr"], "source": cand["source"], "title": cand["title"],
                    "author": cand["author"], "license": cand["license"],
                    "page": cand["page"], "query": cand["query"],
                }
                save_credits(credits)
                print(f"[{line_no}/{len(todo)}] {item['fr'][:55]:<55} OK — {label}")
                ok += 1
            else:
                print(f"[{line_no}/{len(todo)}] {item['fr'][:55]:<55} échec du téléchargement")
                unmatched.append({**item, "essais": [f"download KO: {cand['download']}"]})
                fail += 1

    if args.workers > 1:
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            list(pool.map(handle, todo))
    else:
        for item in todo:
            handle(item)

    if unmatched and not args.dry_run:
        UNMATCHED.write_text(json.dumps(unmatched, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\ntrouvées {ok} · sans correspondance {fail}")
    if unmatched and not args.dry_run:
        print(f"à reprendre à la main : {UNMATCHED}")


if __name__ == "__main__":
    main()
