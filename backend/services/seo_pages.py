"""
seo_pages.py — Pages HTML servies par le backend, pour le référencement.

L'application est une SPA à routes « en dièse » (/ui#/recette/…) : les moteurs
de recherche n'indexent pas ce qui suit le #, aucune recette n'était donc
référençable. Ce module produit de vraies pages HTML (2026-11-24) :

  /idees                 index des thèmes
  /idees/<thème>         sélection de recettes (riches en fer, vegan rapides,
                         de saison en novembre, au potimarron, cuisine indienne…)
  /recette/<id>          fiche recette avec données structurées schema.org/Recipe
  /sitemap.xml, /robots.txt

Les thèmes sont calculés depuis les données de l'application (scores santé
du filtre, régimes, temps, saisons, composition) : une page n'existe que si
elle réunit au moins MIN_RECIPES recettes.
"""
from __future__ import annotations

import html
import json
import os
import re
import threading
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

SITE_NAME = "ALIM"
MIN_RECIPES = 6
MAX_LISTED = 40

_ROOT = Path(__file__).resolve().parents[2]
_IMG_DIRS = (_ROOT / "frontend" / "dist" / "images" / "recipes",
             _ROOT / "frontend" / "public" / "images" / "recipes")

MONTHS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
             "août", "septembre", "octobre", "novembre", "décembre"]

CUISINES_FR = {
    "french": "française", "indian": "indienne", "italian": "italienne",
    "american": "américaine", "japanese": "japonaise", "mexican": "mexicaine",
    "chinese": "chinoise", "levantine": "levantine", "korean": "coréenne",
    "greek": "grecque", "thai": "thaïe", "turkish": "turque", "moroccan": "marocaine",
    "spanish": "espagnole", "british": "britannique", "persian": "persane",
    "vietnamese": "vietnamienne", "brazilian": "brésilienne", "indonesian": "indonésienne",
    "lebanese": "libanaise", "polish": "polonaise", "ethiopian": "éthiopienne",
    "german": "allemande", "sri_lankan": "sri-lankaise", "peruvian": "péruvienne",
}

DISH_FR = {
    "main": "plat", "side": "accompagnement", "dessert": "dessert", "soup": "soupe",
    "starter": "entrée", "breakfast": "petit-déjeuner", "snack": "en-cas",
    "beverage": "boisson", "bread": "pain",
}

# (slug, libellé « aux/au/à la … », préfixes ou segments d'ids de composition,
# mot du titre). Une recette en fait partie si l'ingrédient pèse au moins
# INGREDIENT_MIN_SHARE du plat ou si le mot figure dans son titre : une
# carotte dans un bouillon ne fait pas une « recette à la carotte ».
INGREDIENT_MIN_SHARE = 0.10
INGREDIENT_EXCLUDE = {
    "courge": ("zucchini", "summer_squash", "courgette", "_seed"),
    "pommes-de-terre": ("sweet_potato",),
    "chou": ("cauliflower", "brussels"),
    "pomme": ("pineapple",),
}
INGREDIENT_THEMES: list[tuple[str, str, tuple[str, ...]]] = [
    ("potimarron", "au potimarron", ("red_kuri_squash",)),
    ("courge", "à la courge", ("pumpkin", "butternut", "squash", "kabocha", "red_kuri_squash")),
    ("courgette", "à la courgette", ("zucchini", "courgette")),
    ("aubergine", "à l'aubergine", ("eggplant",)),
    ("poireau", "au poireau", ("leek",)),
    ("chou", "au chou", ("cabbage", "kale", "curly_kale")),
    ("chou-fleur", "au chou-fleur", ("cauliflower",)),
    ("brocoli", "au brocoli", ("broccoli",)),
    ("epinards", "aux épinards", ("spinach",)),
    ("champignons", "aux champignons", ("mushroom", "shiitake", "chanterelle", "porcini", "morel", "enoki")),
    ("carotte", "à la carotte", ("carrot",)),
    ("patate-douce", "à la patate douce", ("sweet_potato",)),
    ("pommes-de-terre", "aux pommes de terre", ("potato_",)),   # pas sweet_potato : préfixe seul
    ("tomate", "à la tomate", ("tomato_raw", "cherry_tomato")),
    ("poivron", "au poivron", ("bell_pepper",)),
    ("asperges", "aux asperges", ("asparagus",)),
    ("petits-pois", "aux petits pois", ("green_peas",)),
    ("betterave", "à la betterave", ("beetroot", "beet_")),
    ("avocat", "à l'avocat", ("avocado",)),
    ("lentilles", "aux lentilles", ("lentil",)),
    ("pois-chiches", "aux pois chiches", ("chickpea",)),
    ("haricots-rouges", "aux haricots rouges", ("kidney_bean", "red_bean", "medium_red_bean")),
    ("haricots-noirs", "aux haricots noirs", ("black_bean",)),
    ("haricots-blancs", "aux haricots blancs", ("white_bean", "great_northern", "navy_bean", "cannellini")),
    ("tofu", "au tofu", ("tofu",)),
    ("tempeh", "au tempeh", ("tempeh",)),
    ("seitan", "au seitan", ("seitan",)),
    ("quinoa", "au quinoa", ("quinoa",)),
    ("feta", "à la feta", ("feta",)),
    ("chevre", "au chèvre", ("goat_cheese", "chevre", "_goat")),
    ("oeufs", "aux œufs", ("egg_raw", "egg_whole", "egg_yolk", "egg_white")),
    ("lait-de-coco", "au lait de coco", ("coconut_milk",)),
    ("pomme", "à la pomme", ("apple_raw",)),
    ("banane", "à la banane", ("banana",)),
    ("chocolat", "au chocolat", ("chocolate", "cocoa")),
]


# ── Données d'une recette pour les pages ─────────────────────────────────────

@dataclass
class Info:
    id: str
    title: str
    description: str
    recipe: dict
    hs: dict
    nutr: dict
    flags: dict
    total_min: int
    dish: str
    cuisine: str
    tokens: set[str]
    shares: dict[str, float]          # part de chaque ingrédient dans le poids du plat
    score: float
    image: str | None
    seasons: dict[int, float] = field(default_factory=dict)


def _norm(text: str) -> str:
    t = unicodedata.normalize("NFD", (text or "").replace("œ", "oe"))
    return "".join(c for c in t if unicodedata.category(c) != "Mn").lower()


def slugify(text: str) -> str:
    t = unicodedata.normalize("NFD", text or "")
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").lower().strip()
    t = re.sub(r"[\s_/\\]+", "-", t)
    t = re.sub(r"[^a-z0-9-]", "", t)
    return re.sub(r"-+", "-", t).strip("-")


def recipe_image(recipe: dict) -> str | None:
    """Chemin public de la photo (même règle que RecipeCard.getRecipeImageUrl)."""
    if recipe.get("image_url"):
        return recipe["image_url"]
    title = (recipe.get("titles") or {}).get("fr") or (recipe.get("titles") or {}).get("en") or ""
    name = f"{slugify(title)}.jpg"
    # photo d'un membre acceptée par la modération : prioritaire (routes/photo_proposals)
    from backend.api.routes.photo_proposals import member_photo
    if title and member_photo(slugify(title)):
        return f"/images/recipes/{name}"
    # /images est servi depuis le build (frontend/dist) s'il existe : une photo
    # ajoutée dans public/ après le dernier build y serait une image cassée.
    served = next((d for d in _IMG_DIRS if d.is_dir()), None)
    if title and served and (served / name).exists():
        return f"/images/recipes/{name}"
    return None


def _total_min(r: dict) -> int:
    t = r.get("timing") or {}
    if isinstance(t.get("total_min"), (int, float)):
        return int(t["total_min"])
    return int((t.get("prep_active_min") or 0) + (t.get("prep_passive_min") or 0) + (t.get("cook_min") or 0))


def _shares(r: dict) -> dict[str, float]:
    from backend.engine.nutrition_engine import _qty_to_g
    grams: dict[str, float] = {}
    for c in r.get("composition") or []:
        t = str(c.get("ingredient") or "")
        if not t or t == "water" or t.startswith("vegetable_stock"):
            continue
        try:
            g = _qty_to_g(t, c) if c.get("quantity") is not None else 0.0
        except Exception:
            g = 0.0
        grams[t] = grams.get(t, 0.0) + g
    total = sum(grams.values()) or 1.0
    return {t: g / total for t, g in grams.items()}


def _build_infos() -> list[Info]:
    from backend.core.data_io import (
        load_recipes, load_nutrition_graph, load_score_graph, recipe_cuisine, is_component_recipe,
    )
    from backend.engine.rule_engine.seasonality import season_ratio
    from backend.services.filter_service import _hs

    ng, sg = load_nutrition_graph(), load_score_graph()
    out = []
    for r in load_recipes():
        if is_component_recipe(r):
            continue
        rid = str(r.get("id"))
        titles = r.get("titles") or {}
        cuisine = recipe_cuisine(r)
        if cuisine.startswith("french"):
            cuisine = "french"
        info = Info(
            id=rid, title=titles.get("fr") or titles.get("en") or rid,
            description=(r.get("description") or "").strip(), recipe=r,
            hs=_hs(r), nutr=ng.get(rid) or {}, flags=r.get("diet_flags") or {},
            total_min=_total_min(r), dish=str(r.get("dish_type") or ""),
            cuisine=cuisine,
            tokens={str(c.get("ingredient") or "") for c in r.get("composition") or []},
            shares=_shares(r),
            score=float((sg.get(rid) or {}).get("overall_score") or 0),
            image=recipe_image(r),
        )
        for m in range(1, 13):
            ratio = season_ratio(r, m)
            if ratio is not None:
                info.seasons[m] = ratio
        out.append(info)
    return out


# ── Thèmes ───────────────────────────────────────────────────────────────────

@dataclass
class Theme:
    slug: str
    group: str
    h1: str
    description: str          # balise meta (≤ 160 caractères)
    intro: str
    select: Callable[[Info], bool]
    metric: Callable[[Info], float] = lambda i: i.score
    badge: Callable[[Info], str] = lambda i: ""
    recipes: list[Info] = field(default_factory=list)


def _fr(x: float, d: int = 1) -> str:
    s = f"{x:.{d}f}".rstrip("0").rstrip(".") if d else f"{x:.0f}"
    return s.replace(".", ",")


def _nutrient_themes() -> list[Theme]:
    N = []

    def add(slug, h1, desc, intro, key, flag=None, test=None, unit="", d=1, label=""):
        N.append(Theme(
            slug=slug, group="Nutrition", h1=h1, description=desc, intro=intro,
            select=test or (lambda i, f=flag: bool(i.hs.get(f))),
            metric=lambda i, k=key: float(i.nutr.get(k) or 0),
            badge=lambda i, k=key, u=unit, dd=d, lb=label: f"{_fr(float(i.nutr.get(k) or 0), dd)} {u} {lb}".strip(),
        ))

    add("recettes-vegetariennes-riches-en-fer", "Recettes végétariennes riches en fer",
        "Recettes végétariennes apportant au moins 4,2 mg de fer par portion (30 % des apports), avec la vitamine C qui aide à l'absorber.",
        "Chaque recette apporte au moins 4,2 mg de fer par portion, soit 30 % de l'apport de référence (14 mg). "
        "Le fer des végétaux est mieux absorbé avec de la vitamine C : un filet de citron, du poivron ou du persil font la différence.",
        "iron", "high_iron", unit="mg", label="de fer")
    add("recettes-vegetariennes-riches-en-proteines", "Recettes végétariennes riches en protéines",
        "Plats végétariens d'au moins 20 g de protéines par portion : légumineuses, tofu, tempeh, seitan, œufs et fromages.",
        "Chaque recette apporte au moins 20 g de protéines par portion. Les légumineuses associées aux céréales, le tofu, "
        "le tempeh et le seitan sont les piliers d'une assiette végétarienne rassasiante.",
        "protein", "high_protein", unit="g", label="de protéines")
    add("recettes-riches-en-fibres", "Recettes végétariennes riches en fibres",
        "Recettes d'au moins 8 g de fibres par portion, pour la satiété et le transit.",
        "Chaque recette apporte au moins 8 g de fibres par portion, près d'un tiers des 25 à 30 g conseillés par jour.",
        "fiber", "high_fiber", unit="g", label="de fibres")
    add("recettes-vegetariennes-riches-en-calcium", "Recettes végétariennes riches en calcium",
        "Recettes apportant au moins 150 mg de calcium par portion : fromages, tofu, amandes, choux, sésame.",
        "Chaque recette apporte au moins 150 mg de calcium par portion (15 % de l'apport de référence de 1 000 mg).",
        "calcium", "high_calcium", d=0, unit="mg", label="de calcium")
    add("recettes-riches-en-vitamine-c", "Recettes riches en vitamine C",
        "Recettes apportant au moins 27 mg de vitamine C par portion, un tiers des besoins du jour.",
        "Chaque recette apporte au moins 27 mg de vitamine C par portion, soit 30 % de l'apport de référence. "
        "Poivrons, choux, agrumes et herbes fraîches en sont les meilleures sources.",
        "vitamin_c", "high_vitamin_c", d=0, unit="mg", label="de vitamine C")
    add("recettes-riches-en-magnesium", "Recettes végétariennes riches en magnésium",
        "Recettes apportant au moins 100 mg de magnésium par portion : légumineuses, céréales complètes, oléagineux.",
        "Chaque recette apporte au moins 100 mg de magnésium par portion, un quart de l'apport de référence (375 mg).",
        "magnesium", "high_magnesium", d=0, unit="mg", label="de magnésium")
    add("recettes-vegetariennes-riches-en-omega-3", "Recettes végétariennes sources d'oméga-3",
        "Recettes apportant au moins 0,3 g d'oméga-3 (ALA) par portion : noix, lin, chia, colza.",
        "Chaque recette apporte au moins 0,3 g d'acide alpha-linolénique (oméga-3) par portion, le seuil de l'allégation « source d'oméga-3 ».",
        "omega3", "source_omega3", unit="g", label="d'oméga-3")
    add("recettes-legeres-moins-de-400-kcal", "Plats végétariens légers, moins de 400 kcal",
        "Plats complets végétariens de moins de 400 kcal par portion, sans sacrifier la gourmandise.",
        "Des plats et soupes complets de moins de 400 kcal par portion, pour un repas léger mais rassasiant.",
        "calories", test=lambda i: i.dish in ("main", "soup") and 150 <= float(i.nutr.get("calories") or 0) < 400,
        d=0, unit="kcal")
    N[-1].metric = lambda i: -float(i.nutr.get("calories") or 0)
    add("recettes-peu-de-glucides-rapides", "Recettes adaptées au diabète : peu de glucides rapides",
        "Plats végétariens apportant au plus 10 g de glucides rapides par portion, adaptés à une alimentation pour le diabète.",
        "Chaque plat apporte au plus 10 g de glucides rapides par portion (féculents raffinés, sucres, fruits très sucrés), "
        "les fibres et les protéines y font le gros de l'assiette. Un repère, pas un avis médical.",
        "fast_carbs", test=lambda i: i.dish in ("main", "soup") and i.hs.get("glycemic_category") == "low",
        d=0, unit="g", label="de glucides rapides")
    N[-1].metric = lambda i: -float(i.nutr.get("fast_carbs") or 0)
    add("recettes-pauvres-en-fodmap", "Recettes végétariennes pauvres en FODMAP",
        "Recettes végétariennes pauvres en FODMAP aux portions indiquées, pour les intestins sensibles (régime Monash).",
        "Les quantités de chaque ingrédient restent sous les seuils FODMAP de l'université Monash à la portion indiquée : "
        "sans ail ni oignon en excès, sans légumineuses en grande quantité.",
        "fiber", test=lambda i: i.hs.get("fodmap_level") == "low" and i.dish in ("main", "soup", "breakfast", "dessert", "side"))
    N[-1].metric, N[-1].badge = (lambda i: i.score), (lambda i: "")
    add("recettes-pauvres-en-sel", "Recettes végétariennes pauvres en sel",
        "Recettes pauvres en sodium (au plus 120 mg pour 100 g), pour limiter le sel sans perdre le goût.",
        "Chaque recette contient au plus 120 mg de sodium pour 100 g, le seuil de l'allégation « pauvre en sodium ». "
        "Herbes, épices et agrumes prennent le relais du sel.",
        "sodium", test=lambda i: bool(i.hs.get("low_sodium")) and i.dish in ("main", "soup", "side"),
        d=0, unit="mg", label="de sodium")
    N[-1].metric = lambda i: -float(i.nutr.get("sodium") or 0)
    return N


def _diet_time_dish_themes() -> list[Theme]:
    T: list[Theme] = []
    is_vegan = lambda i: bool(i.flags.get("vegan"))                 # noqa: E731
    is_salad = lambda i: i.id.startswith("salad") or i.title.lower().startswith("salade")  # noqa: E731
    time_badge = lambda i: f"{i.total_min} min"                     # noqa: E731
    by_time = lambda i: -i.total_min                                # noqa: E731

    def add(slug, group, h1, desc, intro, test, metric=None, badge=None):
        T.append(Theme(slug=slug, group=group, h1=h1, description=desc, intro=intro, select=test,
                       metric=metric or (lambda i: i.score), badge=badge or (lambda i: "")))

    add("recettes-vegan", "Régimes", "Recettes vegan",
        "Recettes 100 % végétales : sans viande, poisson, œufs, lait ni miel, des plats du monde entier.",
        "Toutes ces recettes sont 100 % végétales : sans viande ni poisson, sans œufs, produits laitiers ni miel.",
        is_vegan)
    add("recettes-vegetariennes-sans-gluten", "Régimes", "Recettes végétariennes sans gluten",
        "Recettes végétariennes sans gluten : sans blé, seigle, orge ni épeautre, vérifiées ingrédient par ingrédient.",
        "Aucun ingrédient de ces recettes ne contient de gluten (blé, seigle, orge, épeautre). "
        "Vérifiez toujours l'étiquette des produits transformés : sauces, bouillons, levure.",
        lambda i: bool(i.flags.get("gluten_free")))
    add("recettes-vegetariennes-sans-lactose", "Régimes", "Recettes végétariennes sans lactose",
        "Recettes végétariennes sans lactose : sans lait, crème, beurre ni fromage frais.",
        "Aucun ingrédient de ces recettes n'apporte de lactose : ni lait, ni crème, ni beurre, ni fromage frais.",
        lambda i: bool(i.flags.get("lactose_free")))
    add("recettes-sans-fruits-a-coque", "Régimes", "Recettes végétariennes sans fruits à coque",
        "Recettes végétariennes sans amandes, noix, noisettes, cajou ni pistaches, pour les allergies.",
        "Aucune de ces recettes ne contient de fruits à coque (amande, noix, noisette, cajou, pistache, pécan…).",
        lambda i: bool(i.flags.get("nut_free")) and i.dish in ("main", "dessert"))
    add("recettes-vegetariennes-rapides-moins-de-20-minutes", "Rapide", "Recettes végétariennes prêtes en 20 minutes",
        "Recettes végétariennes prêtes en 20 minutes au plus, préparation et cuisson comprises.",
        "Préparation et cuisson comprises, ces recettes sont sur la table en 20 minutes au plus.",
        lambda i: 0 < i.total_min <= 20 and i.dish not in ("beverage",), by_time, time_badge)
    add("diners-vegetariens-rapides-moins-de-30-minutes", "Rapide", "Dîners végétariens en moins de 30 minutes",
        "Plats végétariens complets prêts en 30 minutes au plus pour les soirs de semaine.",
        "Des plats complets prêts en 30 minutes au plus, préparation et cuisson comprises.",
        lambda i: i.dish == "main" and 0 < i.total_min <= 30, by_time, time_badge)
    add("plats-vegan-rapides", "Rapide", "Plats vegan rapides, en 30 minutes",
        "Plats 100 % végétaux prêts en 30 minutes au plus.",
        "Des plats complets 100 % végétaux, sur la table en 30 minutes au plus.",
        lambda i: i.dish == "main" and is_vegan(i) and 0 < i.total_min <= 30, by_time, time_badge)
    add("soupes-vegetariennes", "Type de plat", "Soupes végétariennes",
        "Soupes, veloutés et potages végétariens du monde entier, avec leur valeur nutritionnelle.",
        "Veloutés, soupes-repas et bouillons : des soupes végétariennes du monde entier.",
        lambda i: i.dish == "soup")
    add("salades-vegetariennes", "Type de plat", "Salades végétariennes",
        "Salades composées végétariennes, en entrée ou en plat complet.",
        "Des salades composées végétariennes, en entrée ou en plat complet.",
        is_salad)
    add("desserts-vegan", "Type de plat", "Desserts vegan",
        "Desserts 100 % végétaux : gâteaux, crèmes et fruits, sans œufs ni produits laitiers.",
        "Des desserts sans œufs ni produits laitiers.",
        lambda i: i.dish == "dessert" and is_vegan(i))
    add("desserts-vegetariens", "Type de plat", "Desserts végétariens",
        "Desserts végétariens : gâteaux, tartes, crèmes et desserts aux fruits du monde entier.",
        "Gâteaux, tartes, crèmes et desserts aux fruits.",
        lambda i: i.dish == "dessert")
    add("petits-dejeuners-vegetariens", "Type de plat", "Petits-déjeuners végétariens",
        "Idées de petits-déjeuners végétariens, sucrés et salés, du porridge au tofu brouillé.",
        "Sucrés ou salés, des petits-déjeuners végétariens pour bien commencer la journée.",
        lambda i: i.dish == "breakfast")
    add("entrees-vegetariennes", "Type de plat", "Entrées végétariennes",
        "Entrées et apéritifs végétariens : tartinades, bouchées, salades et verrines.",
        "Tartinades, bouchées et petites assiettes végétariennes.",
        lambda i: i.dish == "starter")
    add("accompagnements-vegetariens", "Type de plat", "Accompagnements végétariens",
        "Accompagnements de légumes, céréales et légumineuses pour compléter un repas.",
        "Légumes, céréales et légumineuses pour compléter l'assiette.",
        lambda i: i.dish == "side")
    return T


def _cuisine_themes(infos: list[Info]) -> list[Theme]:
    T = []
    for code, fr in CUISINES_FR.items():
        T.append(Theme(
            slug=f"cuisine-{slugify(fr)}-vegetarienne", group="Cuisines du monde",
            h1=f"Cuisine {fr} végétarienne",
            description=f"Recettes végétariennes de la cuisine {fr} : plats traditionnels et variantes sans viande.",
            intro=f"Les grands classiques et les plats du quotidien de la cuisine {fr}, en version végétarienne.",
            select=lambda i, c=code: i.cuisine == c,
        ))
    return T


def _season_themes() -> list[Theme]:
    T = []
    for m in range(1, 13):
        mois = MONTHS_FR[m - 1]
        de = "d'" if mois[0] in "aeiouo" else "de "
        T.append(Theme(
            slug=f"recettes-de-saison-{slugify(mois)}", group="De saison",
            h1=f"Recettes végétariennes de saison en {mois}",
            description=f"Recettes végétariennes avec les fruits et légumes de saison en {mois}, pour cuisiner local et moins cher.",
            intro=f"Les fruits et légumes frais de ces recettes sont tous ou presque de saison en {mois} en France : "
                  f"meilleurs, moins chers et moins transportés. Une sélection {de}idées pour le mois.",
            select=lambda i, mm=m: i.seasons.get(mm, 0) >= 0.75 and i.dish in ("main", "soup", "side", "starter", "dessert"),
            metric=lambda i, mm=m: i.seasons.get(mm, 0) * 10 + i.score,
        ))
    return T


def _ingredient_themes() -> list[Theme]:
    T = []
    for slug, label, keys in INGREDIENT_THEMES:
        word = label.split(" ", 1)[1].replace("l'", "").replace("la ", "").replace("le ", "").strip()
        excl = INGREDIENT_EXCLUDE.get(slug, ())

        def match(t, ks=keys, ex=excl):
            if any(x in t for x in ex):
                return False
            return any(t.startswith(k) or (not k.endswith("_") and f"_{k}" in f"_{t}") for k in ks)

        def share(i, ks=keys, m=match):
            return sum(v for t, v in i.shares.items() if m(t, ks))

        def in_title(i, ks=keys, w=word, m=match):
            return (any(m(t, ks) for t in i.tokens)
                    and re.search(rf"(?<![a-z]){re.escape(_norm(w))}s?(?![a-z])", _norm(i.title)) is not None)

        T.append(Theme(
            slug=f"recettes-vegetariennes-{slug}", group="Par ingrédient",
            h1=f"Recettes végétariennes {label}",
            description=f"Idées de recettes végétariennes {label} : plats, soupes, salades et desserts, avec leur valeur nutritionnelle.",
            intro=f"Toutes nos recettes végétariennes {label}, des plus simples aux plus élaborées : "
                  f"l'ingrédient y tient une vraie place, en premier celles où il est la vedette.",
            select=lambda i, s=share, it=in_title: s(i) >= INGREDIENT_MIN_SHARE or it(i),
            # la vedette d'abord : nommée dans le titre, puis par part du plat
            metric=lambda i, s=share, it=in_title: (1.0 if it(i) else 0.0) + s(i),
        ))
    return T


_cache_lock = threading.Lock()
_cache: dict = {"key": None, "themes": None, "infos": None}


def _cache_key() -> tuple:
    from backend.core.data_cache import data_generation
    from backend.core.data_io import load_recipes
    return (data_generation(), id(load_recipes()))


def build() -> tuple[dict[str, Theme], dict[str, Info]]:
    """Thèmes non vides (≥ MIN_RECIPES recettes) et recettes, mis en cache."""
    key = _cache_key()
    with _cache_lock:
        if _cache["key"] == key:
            return _cache["themes"], _cache["infos"]
        infos = _build_infos()
        themes: dict[str, Theme] = {}
        for th in (_nutrient_themes() + _diet_time_dish_themes() + _season_themes()
                   + _ingredient_themes() + _cuisine_themes(infos)):
            sel = [i for i in infos if _safe(th.select, i)]
            if len(sel) < MIN_RECIPES:
                continue
            sel.sort(key=lambda i: (th.metric(i), i.score), reverse=True)
            th.recipes = sel
            themes[th.slug] = th
        _cache.update(key=key, themes=themes, infos={i.id: i for i in infos})
        return themes, _cache["infos"]


def _safe(fn, i) -> bool:
    try:
        return bool(fn(i))
    except Exception:
        return False


def themes_of(rid: str, limit: int = 6) -> list[Theme]:
    themes, _ = build()
    return [t for t in themes.values() if any(i.id == rid for i in t.recipes)][:limit]


# ── Rendu HTML ───────────────────────────────────────────────────────────────

def base_url(request_base: str) -> str:
    """Adresse publique du site : APP_BASE_URL (sans /ui) sinon celle de la requête."""
    env = (os.getenv("APP_BASE_URL") or "").strip().rstrip("/")
    if env:
        return re.sub(r"/ui$", "", env)
    return request_base.rstrip("/")


E = html.escape

CSS = """
:root{--bg:#fbfaf7;--txt:#1f2421;--mut:#5d655f;--grn:#2f6b45;--brd:#e3e0d8;--card:#fff}
@media (prefers-color-scheme:dark){:root{--bg:#141714;--txt:#e9ece8;--mut:#a3aba4;--grn:#7cc596;--brd:#2c322d;--card:#1b1f1b}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--txt);font:16px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:var(--grn)}header,main,footer{max-width:1080px;margin:0 auto;padding:0 16px}
header{display:flex;justify-content:space-between;align-items:center;padding-top:16px;padding-bottom:8px}
.logo{font-weight:700;font-size:20px;text-decoration:none;color:var(--txt)}.cta{background:var(--grn);color:var(--bg);padding:8px 14px;border-radius:8px;text-decoration:none;font-size:14px}
nav.crumbs{font-size:13px;color:var(--mut);margin:8px 0}nav.crumbs a{color:var(--mut)}
h1{font-size:clamp(24px,4vw,34px);line-height:1.2;margin:8px 0 12px}.intro{color:var(--mut);max-width:760px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:16px;margin:24px 0;padding:0;list-style:none}
.card{background:var(--card);border:1px solid var(--brd);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.card a{text-decoration:none;color:inherit;display:block}.card img,.ph{width:100%;aspect-ratio:3/2;object-fit:cover;display:block;background:linear-gradient(135deg,#d9e8d2,#f3e6c8)}
.card .b{padding:10px 12px}.card h2,.card h3{font-size:16px;margin:0 0 4px}.meta{font-size:13px;color:var(--mut)}
.badge{display:inline-block;font-size:12px;border:1px solid var(--brd);border-radius:999px;padding:1px 8px;margin:2px 4px 2px 0}
section.group{margin:28px 0}section.group h2{font-size:20px}.tags{display:flex;flex-wrap:wrap;gap:8px;padding:0;list-style:none}
.tags a{display:inline-block;border:1px solid var(--brd);border-radius:999px;padding:4px 12px;text-decoration:none;font-size:14px;background:var(--card)}
.hero{width:100%;max-height:420px;object-fit:cover;border-radius:12px}
.cols{display:grid;grid-template-columns:1fr 2fr;gap:28px}@media(max-width:760px){.cols{grid-template-columns:1fr}}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{border-bottom:1px solid var(--brd);padding:6px 4px;text-align:left}
ol li{margin-bottom:8px}footer{color:var(--mut);font-size:13px;padding-top:24px;padding-bottom:32px}
"""


def _page(title: str, description: str, canonical: str, body: str, jsonld: list[dict],
          crumbs: list[tuple[str, str]] | None = None, image: str | None = None) -> str:
    def _ld(d: dict) -> str:
        # « </ » dans un texte fermerait la balise script
        return json.dumps(d, ensure_ascii=False).replace("</", "<" + chr(92) + "/")
    ld = "".join(f'<script type="application/ld+json">{_ld(d)}</script>' for d in jsonld)
    crumb_html = ""
    if crumbs:
        crumb_html = '<nav class="crumbs" aria-label="Fil d\'Ariane">' + " › ".join(
            f'<a href="{E(u)}">{E(t)}</a>' if u else E(t) for t, u in crumbs) + "</nav>"
    og_img = f'<meta property="og:image" content="{E(image)}">' if image else ""
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)}</title>
<meta name="description" content="{E(description)}">
<link rel="canonical" href="{E(canonical)}">
<meta property="og:type" content="website"><meta property="og:title" content="{E(title)}">
<meta property="og:description" content="{E(description)}"><meta property="og:url" content="{E(canonical)}">
{og_img}<meta property="og:site_name" content="{SITE_NAME}">
<link rel="icon" href="/favicon.svg"><link rel="stylesheet" href="/idees/style.css">
{ld}</head><body>
<header><a class="logo" href="/idees">{SITE_NAME}</a><a class="cta" href="/ui">Ouvrir l'application</a></header>
<main>{crumb_html}{body}</main>
<footer>{SITE_NAME} — recettes végétariennes, valeurs nutritionnelles calculées depuis les tables CIQUAL (Anses), CNF et USDA.
<a href="/idees">Toutes les idées de recettes</a></footer>
</body></html>"""


def _card(i: Info, badge: str, tag: str = "h2") -> str:
    img = (f'<img src="{E(i.image)}" alt="{E(i.title)}" loading="lazy" width="300" height="200">'
           if i.image else '<div class="ph" role="img" aria-label=""></div>')
    meta = []
    if i.total_min:
        meta.append(f"{i.total_min} min" if i.total_min < 240 else "à préparer la veille")
    if i.nutr.get("calories"):
        meta.append(f"{int(i.nutr['calories'])} kcal")
    if i.flags.get("vegan"):
        meta.append("vegan")
    b = f'<span class="badge">{E(badge)}</span>' if badge else ""
    return (f'<li class="card"><a href="/recette/{E(i.id)}">{img}<div class="b">'
            f'<{tag}>{E(i.title)}</{tag}>{b}<div class="meta">{E(" · ".join(meta))}</div></div></a></li>')


def render_index(base: str) -> str:
    themes, _ = build()
    groups: dict[str, list[Theme]] = {}
    for t in themes.values():
        groups.setdefault(t.group, []).append(t)
    body = ["<h1>Idées de recettes végétariennes</h1>",
            '<p class="intro">Des recettes végétariennes et vegan du monde entier, classées par besoin : '
            "nutrition, régime, temps disponible, saison ou ingrédient. Chaque recette affiche sa valeur "
            "nutritionnelle par portion.</p>"]
    for g in ("Nutrition", "Régimes", "Rapide", "Type de plat", "De saison", "Par ingrédient", "Cuisines du monde"):
        if g not in groups:
            continue
        links = "".join(f'<li><a href="/idees/{E(t.slug)}">{E(t.h1)} ({len(t.recipes)})</a></li>' for t in groups[g])
        body.append(f'<section class="group"><h2>{E(g)}</h2><ul class="tags">{links}</ul></section>')
    body.append('<p><a href="/ingredient">Fiches ingrédients : valeurs nutritionnelles, saison, prix</a></p>')
    jsonld = [{"@context": "https://schema.org", "@type": "CollectionPage",
               "name": "Idées de recettes végétariennes", "url": f"{base}/idees"}]
    return _page(f"Idées de recettes végétariennes — {SITE_NAME}",
                 "Recettes végétariennes et vegan classées par nutrition, régime, temps, saison, ingrédient et cuisine du monde.",
                 f"{base}/idees", "".join(body), jsonld, [("Accueil", "/ui"), ("Idées de recettes", "")])


def render_theme(slug: str, base: str) -> str | None:
    themes, _ = build()
    th = themes.get(slug)
    if not th:
        return None
    shown = th.recipes[:MAX_LISTED]
    n = len(th.recipes)
    cards = "".join(_card(i, th.badge(i)) for i in shown)
    more = (f'<p class="meta">{n} recettes au total ; les {len(shown)} mieux adaptées sont affichées. '
            f'<a href="/ui#/">Toutes les recettes dans l\'application</a>, avec les filtres.</p>') if n > len(shown) else ""
    related = [t for t in themes.values() if t.group == th.group and t.slug != slug][:12]
    rel = ("<section class=\"group\"><h2>Voir aussi</h2><ul class=\"tags\">"
           + "".join(f'<li><a href="/idees/{E(t.slug)}">{E(t.h1)}</a></li>' for t in related)
           + "</ul></section>") if related else ""
    body = (f"<h1>{E(th.h1)}</h1><p class=\"intro\">{E(th.intro)}</p>"
            f'<ul class="grid">{cards}</ul>{more}{rel}')
    url = f"{base}/idees/{slug}"
    jsonld = [
        {"@context": "https://schema.org", "@type": "ItemList", "name": th.h1, "url": url,
         "numberOfItems": len(shown),
         "itemListElement": [{"@type": "ListItem", "position": k + 1, "url": f"{base}/recette/{i.id}", "name": i.title}
                             for k, i in enumerate(shown)]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Idées de recettes", "item": f"{base}/idees"},
            {"@type": "ListItem", "position": 2, "name": th.h1, "item": url}]},
    ]
    first_img = next((f"{base}{i.image}" for i in shown if i.image and i.image.startswith("/")), None)
    return _page(f"{th.h1} : {n} idées — {SITE_NAME}", th.description, url, body, jsonld,
                 [("Idées de recettes", "/idees"), (th.h1, "")], first_img)


_STEP_PREFIX = re.compile(r"^\s*(?:[ÉE]tape|Step)\s*\d+\s*[:.\-–]\s*", re.I)


def _ingredient_lines(r: dict) -> list[str]:
    return [text for text, _ in _ingredient_items(r)]


def _ingredient_items(r: dict) -> list[tuple[str, str]]:
    """(ligne affichée, id de l'ingrédient). Mêmes libellés que l'application
    (« huile d'olive », pas « olive » ; titre des préparations maison)."""
    from backend.services.ingredient_catalog import names_of
    comp = r.get("composition") or []
    names = names_of([str(c.get("ingredient") or "") for c in comp])
    out = []
    for c in comp:
        t = str(c.get("ingredient") or "")
        if not t or t == "water":
            continue
        name = names.get(t) or t
        name = t.replace("_", " ") if name == t else name
        name = re.sub(r"\s*\(.*?\)\s*", " ", name).strip()
        q, unit = c.get("quantity"), (c.get("unit") or "")
        role = (c.get("meta") or {}).get("role")
        if isinstance(q, (int, float)) and q > 0 and unit in ("g", "ml", "kg", "l"):
            out.append((f"{_fr(float(q), 1)} {unit} {name}", t))
        elif unit == "to_taste":
            out.append((f"{name}, selon le goût", t))
        elif role == "serving_suggestion":
            out.append((f"{name} ({unit + ', ' if unit else ''}au service)", t))
        elif isinstance(q, (int, float)) and q > 0:
            out.append((f"{_fr(float(q), 1)} {unit} {name}".strip(), t))
        else:
            out.append((name, t))
    return out


def _iso(minutes) -> str | None:
    m = int(minutes or 0)
    if m <= 0:
        return None
    h, mm = divmod(m, 60)
    return f"PT{h}H{mm}M" if h else f"PT{mm}M"


def render_recipe(rid: str, base: str) -> str | None:
    _, infos = build()
    i = infos.get(rid)
    if not i:
        return None
    r = i.recipe
    steps = [_STEP_PREFIX.sub("", s if isinstance(s, str) else str(s.get("text", ""))).strip()
             for s in (r.get("instructions") or [])]
    steps = [s for s in steps if s]
    items = _ingredient_items(r)
    ings = [text for text, _ in items]
    from backend.services.ingredient_sheet import public_ingredients, public_slug
    public_ids = set(public_ingredients().values())

    def _ing_li(text: str, iid: str) -> str:
        if iid in public_ids:     # fiche ingrédient : valeurs pour 100 g, saison, autres recettes
            return f'<li><a href="/ingredient/{E(public_slug(iid))}">{E(text)}</a></li>'
        return f"<li>{E(text)}</li>"
    t = r.get("timing") or {}
    srv = r.get("servings_default") or r.get("servings") or 4
    n = i.nutr

    rows = [("Énergie", n.get("calories"), "kcal", 0), ("Protéines", n.get("protein"), "g", 1),
            ("Glucides", n.get("carbs"), "g", 1), ("dont sucres", n.get("sugar"), "g", 1),
            ("Lipides", n.get("fat"), "g", 1), ("Fibres", n.get("fiber"), "g", 1),
            ("Sel", n.get("salt"), "g", 2), ("Fer", n.get("iron"), "mg", 1),
            ("Calcium", n.get("calcium"), "mg", 0), ("Vitamine C", n.get("vitamin_c"), "mg", 0)]
    table = "".join(f"<tr><th>{lb}</th><td>{_fr(float(v), d)} {u}</td></tr>"
                    for lb, v, u, d in rows if isinstance(v, (int, float)))
    diets = [lb for k, lb in (("vegan", "vegan"), ("gluten_free", "sans gluten"),
                              ("lactose_free", "sans lactose"), ("nut_free", "sans fruits à coque"))
             if i.flags.get(k)]
    meta = []
    if t.get("prep_active_min"):
        meta.append(f"Préparation {t['prep_active_min']} min")
    if t.get("cook_min"):
        meta.append(f"cuisson {t['cook_min']} min")
    if (t.get("prep_passive_min") or 0) >= 240:
        meta.append("à lancer la veille")
    meta.append(f"{srv} portions")
    cuisine_fr = CUISINES_FR.get(i.cuisine)
    if cuisine_fr:
        meta.append(f"cuisine {cuisine_fr}")

    hero = f'<img class="hero" src="{E(i.image)}" alt="{E(i.title)}" width="1080" height="420">' if i.image else ""
    th = themes_of(rid)
    see = ("<section class=\"group\"><h2>Dans les mêmes idées</h2><ul class=\"tags\">"
           + "".join(f'<li><a href="/idees/{E(x.slug)}">{E(x.h1)}</a></li>' for x in th)
           + "</ul></section>") if th else ""
    author = ((r.get("community") or {}).get("author_name") or None) if isinstance(r.get("community"), dict) else None
    body = (f"<h1>{E(i.title)}</h1>{hero}"
            f'<p class="intro">{E(i.description)}</p>'
            f'<p class="meta">{E(" · ".join(meta))}'
            + (" " + "".join(f'<span class="badge">{E(d)}</span>' for d in diets) if diets else "")
            + (f" · proposée par {E(author)}" if author else "")
            + "</p>"
            f'<p><a class="cta" href="/ui#/recette/{E(rid)}">Ouvrir dans l\'application</a> '
            "pour ajuster les portions, l'ajouter au planning ou à la liste de courses.</p>"
            '<div class="cols"><section><h2>Ingrédients</h2><ul>'
            + "".join(_ing_li(x, iid) for x, iid in items)
            + f'</ul><h2>Par portion</h2><table>{table}</table></section>'
            '<section><h2>Préparation</h2><ol>'
            + "".join(f"<li>{E(s)}</li>" for s in steps)
            + f"</ol></section></div>{see}")

    url = f"{base}/recette/{rid}"
    diet_uri = {"vegan": "VeganDiet", "gluten_free": "GlutenFreeDiet", "lactose_free": "LowLactoseDiet"}
    suitable = ["https://schema.org/VegetarianDiet"] + [f"https://schema.org/{v}" for k, v in diet_uri.items() if i.flags.get(k)]
    nutrition = {"@type": "NutritionInformation", "servingSize": "1 portion"}
    for key, field_, unit in (("calories", "calories", "kcal"), ("protein", "proteinContent", "g"),
                              ("carbs", "carbohydrateContent", "g"), ("sugar", "sugarContent", "g"),
                              ("fat", "fatContent", "g"), ("saturated_fat", "saturatedFatContent", "g"),
                              ("fiber", "fiberContent", "g"), ("sodium", "sodiumContent", "mg")):
        v = n.get(key)
        if isinstance(v, (int, float)):
            nutrition[field_] = f"{_fr(float(v), 1)} {unit}".replace(",", ".")
    ld = {
        "@context": "https://schema.org", "@type": "Recipe", "name": i.title, "url": url,
        "description": i.description or i.title,
        "author": ({"@type": "Person", "name": author} if author else {"@type": "Organization", "name": SITE_NAME}),
        "recipeYield": f"{srv} portions",
        "recipeCategory": DISH_FR.get(i.dish, "plat"),
        "recipeIngredient": ings,
        "recipeInstructions": [{"@type": "HowToStep", "position": k + 1, "text": s} for k, s in enumerate(steps)],
        "nutrition": nutrition,
        "suitableForDiet": suitable,
        "keywords": ", ".join(["végétarien"] + diets + ([f"cuisine {cuisine_fr}"] if cuisine_fr else [])),
    }
    if cuisine_fr:
        ld["recipeCuisine"] = cuisine_fr
    for k, v in (("prepTime", _iso((t.get("prep_active_min") or 0) + (t.get("prep_passive_min") or 0))),
                 ("cookTime", _iso(t.get("cook_min"))), ("totalTime", _iso(i.total_min))):
        if v:
            ld[k] = v
    img_abs = f"{base}{i.image}" if i.image and i.image.startswith("/") else i.image
    if img_abs:
        ld["image"] = [img_abs]
    crumbs_ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "Idées de recettes", "item": f"{base}/idees"}]
        + ([{"@type": "ListItem", "position": 2, "name": th[0].h1, "item": f"{base}/idees/{th[0].slug}"}] if th else [])
        + [{"@type": "ListItem", "position": 3 if th else 2, "name": i.title, "item": url}]}
    crumbs = [("Idées de recettes", "/idees")] + ([(th[0].h1, f"/idees/{th[0].slug}")] if th else []) + [(i.title, "")]
    desc = (i.description or f"Recette végétarienne : {i.title}.")
    if len(desc) > 158:
        desc = desc[:155].rsplit(" ", 1)[0] + "…"
    return _page(f"{i.title} — recette végétarienne | {SITE_NAME}", desc, url, body, [ld, crumbs_ld], crumbs, img_abs)


def render_sitemap(base: str) -> str:
    themes, infos = build()
    from backend.services.ingredient_sheet import public_ingredients
    urls = ([f"{base}/idees"] + [f"{base}/idees/{s}" for s in themes] + [f"{base}/recette/{rid}" for rid in infos]
            + [f"{base}/ingredient"] + [f"{base}/ingredient/{s}" for s in sorted(public_ingredients())])
    items = "".join(f"<url><loc>{E(u)}</loc></url>" for u in urls)
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{items}</urlset>')


# Routes d'API JSON : inutiles aux moteurs (et coûteuses à explorer)
_API_PREFIXES = ("/auth/", "/profil/", "/recettes/", "/nutrition/", "/planning/", "/admin/",
                 "/ingredients/", "/frigo/", "/contributions/", "/avis/", "/notifications/",
                 "/ingredient-corrections", "/mes-versions", "/docs", "/redoc")


def render_robots(base: str) -> str:
    lines = ["User-agent: *", "Allow: /"] + [f"Disallow: {p}" for p in _API_PREFIXES]
    return "\n".join(lines + [f"Sitemap: {base}/sitemap.xml", ""])


# ── Fiches ingrédients (/ingredient, /ingredient/<slug>) ──────────────────────

def _fmt_val(v, unit: str) -> str:
    if v is None:
        return "—"
    v = float(v)
    d = 0 if v >= 100 else 1 if v >= 10 else 2 if v >= 1 else 3
    txt = f"{v:.{d}f}".rstrip("0").rstrip(".") if d else f"{v:.0f}"
    return f"{txt.replace('.', ',')} {unit}"


def _ingredient_intro(sh: dict) -> str:
    """Phrase d'introduction propre à chaque ingrédient (pas un gabarit vide) ;
    tournures sans genre (« aubergine », « chou » : le genre n'est pas connu)."""
    n = sh.get("nutrition_per_100g") or {}
    parts = []
    if sh.get("kcal_100g") is not None:
        parts.append(f"Pour 100 g : {sh['kcal_100g']} kcal")
        extra = []
        if isinstance(n.get("protein_g"), (int, float)):
            extra.append(f"{_fmt_val(n['protein_g'], 'g')} de protéines")
        if isinstance(n.get("fiber_g"), (int, float)) and n["fiber_g"] >= 1:
            extra.append(f"{_fmt_val(n['fiber_g'], 'g')} de fibres")
        if extra:
            parts[-1] += ", " + " et ".join(extra)
    rich = [r["label"].lower() for g in sh["nutrition"] for r in g["rows"]
            if (r.get("pct") or 0) >= 30 and not r["label"].startswith("dont ")
            and r["key"] not in ("calories_kcal", "fat_g", "carbs_g", "sugar_g", "salt_g", "fa_saturated_g")]
    if rich:
        parts.append(f"riche en {', '.join(rich[:4])} (30 % des valeurs de référence ou plus pour 100 g)")
    txt = " ; ".join(parts) + "." if parts else ""
    if sh.get("season"):
        txt += f" De saison en {sh['season']['label']}."
    if sh.get("recipes_count"):
        nb = sh["recipes_count"]
        txt += f" {nb} recette{'s' if nb > 1 else ''} végétarienne{'s' if nb > 1 else ''} du site l'utilise{'nt' if nb > 1 else ''}."
    return txt.strip()


def render_ingredient(slug: str, base: str) -> str | None:
    from backend.services.ingredient_sheet import public_ingredients, public_slug, sheet
    pub = public_ingredients()
    iid = pub.get(slug)
    if not iid:
        return None
    sh = sheet(iid, with_recipes=400)
    if not sh:
        return None
    name = sh["name_fr"]
    url = f"{base}/ingredient/{slug}"
    src = sh["source"]
    tables = []
    for g in sh["nutrition"]:
        rows = "".join(
            f'<tr><th scope="row">{E(r["label"])}</th><td>{E(_fmt_val(r["value"], r["unit"]))}</td>'
            f'<td>{E(str(r["pct"]) + " %") if r.get("pct") is not None else ""}</td></tr>'
            for r in g["rows"] if r["value"] is not None)
        if rows:
            tables.append(f'<h3>{E(g["title"])}</h3><table><thead><tr><th>Pour 100 g</th><th>Quantité</th>'
                          f'<th>% VNR</th></tr></thead><tbody>{rows}</tbody></table>')
    facts = []
    if sh.get("price"):
        facts.append(("Prix moyen", f"{_fmt_val(sh['price']['per_kg_eur'], '€')} le kilo"
                      + (f" ({sh['price']['package']})" if sh['price'].get('package') else "")))
    if sh.get("carbon"):
        facts.append(("Empreinte carbone", f"{_fmt_val(sh['carbon']['kg_co2_per_kg'], 'kg')} CO₂e par kilo"))
    facts.append(("Saison", sh["season"]["label"] if sh.get("season") else "toute l'année"))
    facts.append(("Allergènes (UE)", ", ".join(sh["allergens"]) or "aucun"))
    facts.append(("Convient à", ", ".join(sh["diets"]) or "—"))
    facts.append(("Rayon", sh["aisle"]))
    facts_html = "".join(f'<tr><th scope="row">{E(k)}</th><td>{E(v)}</td></tr>' for k, v in facts)
    repl_links = []
    for r in sh.get("replacements") or []:
        s2 = public_slug(r["id"])
        href = f"/ingredient/{s2}" if pub.get(s2) == r["id"] else f"/ui#/ingredient/{r['id']}"
        repl_links.append(f'<li><a href="{E(href)}">{E(r["name_fr"])}</a></li>')
    recipes = "".join(f'<li><a href="/recette/{E(x["id"])}">{E(x["title"])}</a></li>' for x in sh["recipes"])
    corr = "".join(
        f'<li>{E(c["label"])} : {E(_fmt_val(c.get("previous"), c["unit"]))} → {E(_fmt_val(c["value"], c["unit"]))}'
        f' (source : {E(c.get("source") or "")})</li>' for c in sh.get("corrections") or [])
    source = (f'<a href="{E(src["url"])}" rel="nofollow noopener">{E(src["name"])}'
              f'{", code " + E(src["id"]) if src.get("id") else ""}</a>' if src.get("url") else E(src["name"]))
    body = (f"<h1>{E(name)} : valeurs nutritionnelles, saison et recettes végétariennes</h1>"
            f'<p class="intro">{E(_ingredient_intro(sh))}</p>'
            f'<p><a class="cta" href="/ui#/ingredient/{E(iid)}">Ouvrir dans l\'application</a></p>'
            '<div class="cols"><section><h2>En bref</h2>'
            f"<table><tbody>{facts_html}</tbody></table>"
            + (f'<h2>Peut se remplacer par</h2><ul class="tags">{"".join(repl_links)}</ul>' if repl_links else "")
            + '</section><section><h2>Valeurs nutritionnelles pour 100 g</h2>'
            "<p class=\"meta\">Produit cru ou tel qu'acheté. % VNR : part des valeurs nutritionnelles de référence "
            "d'un adulte (règlement UE 1169/2011 ; fibres : repère ANSES de 30 g).</p>"
            + "".join(tables)
            + f'<p class="meta">Source : {source}'
            + (f' — « {E(src["label"])} »' if src.get("label") else "") + "</p>"
            + (f"<h3>Corrections apportées</h3><ul>{corr}</ul>" if corr else "")
            + "</section></div>"
            f'<section class="group"><h2>Recettes végétariennes avec {E(name.lower())} '
            f'({sh["recipes_count"]})</h2><ul>{recipes}</ul></section>')
    n = sh.get("nutrition_per_100g") or {}
    desc = (f"{name} : {sh.get('kcal_100g', '—')} kcal, {_fmt_val(n.get('protein_g'), 'g')} de protéines pour 100 g, "
            f"vitamines et minéraux, saison, prix et {sh['recipes_count']} recettes végétariennes.")
    ld = [
        {"@context": "https://schema.org", "@type": "WebPage", "name": f"{name} : valeurs nutritionnelles",
         "url": url, "description": desc, "inLanguage": "fr",
         "about": {"@type": "Thing", "name": name, **({"alternateName": sh["name_en"]} if sh.get("name_en") else {})},
         "isBasedOn": src.get("url") or src["name"]},
        {"@context": "https://schema.org", "@type": "ItemList", "name": f"Recettes végétariennes avec {name.lower()}",
         "itemListElement": [{"@type": "ListItem", "position": k + 1, "url": f"{base}/recette/{x['id']}"}
                             for k, x in enumerate(sh["recipes"][:50])]},
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Ingrédients", "item": f"{base}/ingredient"},
            {"@type": "ListItem", "position": 2, "name": name, "item": url}]},
    ]
    return _page(f"{name} : valeurs nutritionnelles, saison, recettes | {SITE_NAME}", desc, url, body, ld,
                 [("Idées de recettes", "/idees"), ("Ingrédients", "/ingredient"), (name, "")])


def render_ingredient_index(base: str) -> str:
    from backend.engine.planning_engine.shopping import AISLES, aisle_of
    from backend.services.ingredient_sheet import display_name, public_ingredients
    groups: dict[str, list[tuple[str, str]]] = {}
    for slug, iid in public_ingredients().items():
        groups.setdefault(aisle_of(iid), []).append((display_name(iid), slug))
    body = ["<h1>Fiches ingrédients</h1>",
            '<p class="intro">Valeurs nutritionnelles pour 100 g (tables Ciqual, canadienne et USDA), saison, '
            "prix, empreinte carbone et recettes végétariennes de chaque ingrédient.</p>"]
    for aisle in list(AISLES) + sorted(set(groups) - set(AISLES)):
        items = sorted(groups.get(aisle) or [])
        if not items:
            continue
        links = "".join(f'<li><a href="/ingredient/{E(s)}">{E(n)}</a></li>' for n, s in items)
        body.append(f'<section class="group"><h2>{E(aisle)}</h2><ul class="tags">{links}</ul></section>')
    ld = [{"@context": "https://schema.org", "@type": "CollectionPage", "name": "Fiches ingrédients",
           "url": f"{base}/ingredient"}]
    return _page(f"Fiches ingrédients : valeurs nutritionnelles et saisons | {SITE_NAME}",
                 "Valeurs nutritionnelles pour 100 g, saison, prix et recettes végétariennes de chaque ingrédient.",
                 f"{base}/ingredient", "".join(body), ld, [("Idées de recettes", "/idees"), ("Ingrédients", "")])
