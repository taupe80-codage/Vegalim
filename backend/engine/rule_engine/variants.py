"""
variants.py — Variantes vegan d'une recette.
Fusionne : vegan_variant_engine

API :
    vegan_variant(recipe) → dict  {recipe, substitutions, unresolved, source}
"""
from __future__ import annotations
import re
import logging

logger = logging.getLogger(__name__)

VEGAN_SUBS: dict[str, str | None] = {
    "oeuf": "tofu", "oeufs": "tofu", "lait": "lait_coco",
    "beurre": "olive_oil", "butter": "olive_oil", "ghee": "coconut_oil",
    "creme": "lait_coco", "creme_fraiche": "tofu_soyeux",
    "fromage_blanc": "tofu_soyeux", "yogurt": "tofu_soyeux", "yaourt": "tofu_soyeux",
    "feta": "tofu_feta", "mozzarella": "mozzarella_vegane",
    "cheese": "tofu_soyeux", "fromage": "tofu_soyeux",
    "parmesan": "levure_maltee", "ricotta": "noix_de_cajou",
    "cheddar": "cheddar_vegane", "gruyere": "levure_maltee",
    "paneer": "tofu", "kashk": "tofu_soyeux",
    "miel": "sirop_agave", "honey": "sirop_agave",
    "mayonnaise": "mayonnaise_vegan",
}

# Identifiants CIQUAL des recettes → substitut vegan présent dans les données.
# Les clés courtes ci-dessus ('butter') ne correspondaient à aucun id réel
# ('butter_sup80pct') : la variante ne remplaçait rien mais se déclarait vegan.
# Chaque substitut est vegan selon le dictionnaire ou les diet_flags de sa
# sous-recette (vérifié par test). Quantités reprises telles quelles.
# Les préparations sans équivalent vegan du commerce ont leur version vegan maison
# (lot n18 : roux japonais, spätzle, galette de sarrasin, glace, biscuits à la
# cuillère), à la même échelle que l'originale.
VEGAN_SUBS_CIQUAL: dict[str, str] = {
    # Beurre, ghee
    "butter_sup80pct": "vegan_butter", "butter_salted": "vegan_butter", "butter": "vegan_butter",
    "base_ghee_ec9064": "coconut_oil_plant",
    # Œufs
    "egg_raw": "silken_tofu_pre_packaged", "egg_yolk_raw": "silken_tofu_pre_packaged",
    "egg_hard_boiled": "tofu_plain_pre_packaged", "egg_white_raw": "aquafaba",
    # Lait, crème, yaourt
    "milk_liquid_uht_3_5pct": "soybean_milk_unsweetened_plant",
    "milk_liquid_pasteurized_3_5pct": "soybean_milk_unsweetened_plant",
    "buttermilk_1pct": "soybean_milk_unsweetened_plant",
    "condensed_milk_concentrated_sweetened_canned_whole": "coconut_milk_plant",
    "condensed_milk_concentrated_unsweetened_whole": "coconut_milk_plant",
    "cream": "base_soy_cream_4dc027", "cream_heavy": "base_soy_cream_4dc027",
    "cream_heavy_refrigerated_18pct": "base_soy_cream_4dc027",
    "cream_heavy_refrigerated_30pct": "base_soy_cream_4dc027",
    "cream_liquid_uht": "base_soy_cream_4dc027",
    "base_creme_fraiche_b536c1": "base_soy_cream_4dc027",
    "sour_cream_fermented_18pct": "soybean_yogurt_plain_plant",
    "cream_sour_18pct": "soybean_yogurt_plain_plant",
    "cream_sour_fermented": "soybean_yogurt_plain_plant",
    "yogurt_plain_3pct": "soybean_yogurt_plain_plant",
    "yogurt_fermented_plain": "soybean_yogurt_plain_plant",
    "yogurt_greek_plain_4pct": "soybean_yogurt_plain_plant",
    "yogurt_greek_style_plain_8pct": "soybean_yogurt_plain_plant",
    "kefir_fermented": "soybean_yogurt_plain_plant",
    "base_kashk_fd3ac6": "soybean_yogurt_plain_plant",
    "fromage_blanc_plain_2_5pct_cow": "silken_tofu_pre_packaged",
    "cottage_cheese_4pct_cow": "silken_tofu_pre_packaged",
    # Fromages
    "parmesan_grated_dried_cow": "nutritional_yeast_flakes",
    "pecorino_sheep": "nutritional_yeast_flakes",
    "cotija_block_cow": "nutritional_yeast_flakes",
    "feta": "tofu_plain_pre_packaged", "feta_cow": "tofu_plain_pre_packaged",
    "queso_fresco_block_cow": "tofu_plain_pre_packaged",
    "base_paneer_04e1db": "tofu_plain_pre_packaged",
    "base_halloumi_293d5e": "tofu_plain_pre_packaged",
    "base_fromage_en_grain_a00941": "tofu_plain_pre_packaged",
    "cows_milk_mozzarella_cow": "base_mozzarella_vegane_fca8c8",
    "cheddar": "base_vegan_cheddar_024998", "cheddar_cow": "base_vegan_cheddar_024998",
    "gruyere": "base_vegan_cheddar_024998", "comte_cow": "base_vegan_cheddar_024998",
    "emmental_de_savoie_cow": "base_vegan_cheddar_024998",
    "tomme_de_savoie_cow": "base_vegan_cheddar_024998",
    "gouda_cow": "base_vegan_cheddar_024998", "provolone_paste_cow": "base_vegan_cheddar_024998",
    "queso_chihuahua_whole_cow": "base_vegan_cheddar_024998",
    "camembert_pasteurized_cow": "base_vegan_cheddar_024998",
    "roquefort": "base_vegan_cheddar_024998",
    # ids réels des recettes (les clés courtes ci-dessus n'y correspondaient pas)
    "gruyere_whole_cow": "base_vegan_cheddar_024998", "reblochon_cow": "base_vegan_cheddar_024998",
    "roquefort_sheep": "base_vegan_cheddar_024998",
    "mascarpone_cow": "base_cashew_ricotta_5c62e9",
    "ricotta": "base_cashew_ricotta_5c62e9", "ricotta_whole_cow": "base_cashew_ricotta_5c62e9",
    "base_salted_ricotta_1ecd1c": "base_cashew_ricotta_5c62e9",
    "mascarpone": "base_cashew_ricotta_5c62e9",
    "cream_cheese_block_whole_cow": "base_cashew_ricotta_5c62e9",
    "goat_cheese_fresh": "base_cashew_ricotta_5c62e9",
    "goat_cheese_log": "base_cashew_ricotta_5c62e9",
    # Divers
    "honey": "agave_syrup",
    "base_mayonnaise_0d3e4e": "base_vegan_mayonnaise_b68322",
    "base_bechamel_7db18f": "base_bechamel_vegane_7a210c",
    "base_pesto_905db7": "base_pistou_43e29a",
    "base_wonton_wrapper_7bfeb5": "base_gyoza_wrapper_0dba00",
    "puff_pastry_all_butter_raw_paste_pre_packaged": "puff_pastry_vegetable_fat_raw_paste_plant",
    "egg_pasta_raw_dried": "pasta_raw_dried",
    # Pâtes : la brisée et la pâte à empanada (farine, beurre, œuf) ont leur
    # équivalent du commerce à la matière grasse végétale ; les nouilles de blé
    # maison sont les nouilles ramen maison sans l'œuf (même farine, même eau).
    "shortcrust_pastry_all_butter_raw_paste_pre_packaged":
        "shortcrust_pastry_vegetable_fat_raw_paste_pre_packaged_plant",
    "shortcrust_pastry_all_butter_cooked_paste_pre_packaged":
        "shortcrust_pastry_vegetable_fat_cooked_paste_pre_packaged_plant",
    "base_shortcrust_e6e9f0": "shortcrust_pastry_vegetable_fat_raw_paste_pre_packaged_plant",
    "base_empanada_dough_65661a": "shortcrust_pastry_vegetable_fat_raw_paste_pre_packaged_plant",
    "base_noodles_2d0ed7": "base_nouilles_ramen_3907e3",
    "base_japanese_curry_roux_385e52": "base_roux_curry_japonais_vegetal_f245c7",
    "base_spaetzle_a22916": "base_spaetzle_vegan_265b64",
    "base_buckwheat_crepe_03db22": "base_galette_sarrasin_eau_533afe",
    "vanilla_ice_cream": "base_glace_vanille_vegan_4e694a",
    "ladyfinger": "base_biscuits_cuillere_vegan_40fae8",
    # gulab jamun : la farine d'amande remplace le lait en poudre (même rôle de pâte)
    "milk_powder_whole": "almond_flour",
}


def _is_vegan_id(iid: str) -> bool | None:
    """True / False selon le dictionnaire d'ingrédients ou les diet_flags de la
    sous-recette ; None si l'id est inconnu (anciens ids courts)."""
    from backend.db.culinary_repositories import IngredientRepository, _recipes_index
    item = IngredientRepository().get_by_name(iid)
    dp = (item or {}).get("diet_profile")
    if dp and dp.get("vegan") is not None:
        return bool(dp["vegan"])
    sub = _recipes_index().get(iid)
    if sub is not None:
        flag = (sub.get("diet_flags") or {}).get("vegan")
        return None if flag is None else bool(flag)
    return None


def _display_name(iid: str) -> str:
    """Nom français d'un ingrédient ou d'une sous-recette, pour l'affichage."""
    from backend.core.data_io import load_ingredients_dict
    from backend.db.culinary_repositories import _recipes_index
    from backend.services.ingredient_catalog import full_name_fr
    entry = load_ingredients_dict().get(iid)
    name = full_name_fr(entry, iid) if entry and entry.get("canonical_name_fr") else None
    if not name:
        name = ((_recipes_index().get(iid) or {}).get("titles") or {}).get("fr")
    # « Pâte brisée matière grasse végétale » → « Pâte brisée végétale », comme les étapes
    return (name or iid.replace("/", " ").replace("_", " ")).replace("matière grasse végétale", "végétale")


def _item_id(item) -> str:
    if isinstance(item, dict):
        return str(item.get("ingredient") or item.get("ingredient_id") or "")
    return str(item)




def _short(name: str) -> str:
    """« beurre végétal (vegan) » → « beurre végétal », en minuscules ;
    « pâte brisée matière grasse végétale » → « pâte brisée végétale »."""
    s = re.sub(r"\s*\([^)]*\)", "", name or "").strip().lower()
    return s.replace("matière grasse végétale", "végétale")


_LINK_WORDS = {"à", "au", "aux", "de", "du", "des", "d'", "en", "et", "la", "le", "les", "pur"}


def _forms(name: str, heads: bool = True) -> list[str]:
    """Formes de l'ingrédient d'origine dans le texte d'une étape : nom complet,
    pluriels, et (heads) débuts du nom (« crème épaisse » → « crème »)."""
    base = _short(name)
    if not base:
        return []
    forms = {base}
    m = re.match(r"(\S+)( d'| de )(.+)", base)
    if m:                                       # jaune d'œuf → jaunes d'œufs, jaune d'œufs…
        head, link, tail = m.groups()
        forms |= {f"{head}s{link}{tail}", f"{head}s{link}{tail}s", f"{head}{link}{tail}s"}
    elif heads and len(base.split()) > 1 and len(base.split()[0]) > 3:
        # crème épaisse → crème ; pâte brisée pur beurre → pâte brisée, pâte (le plus
        # long d'abord : sinon « pâte brisée » devenait « pâte brisée végétale brisée »)
        words = base.split()
        forms |= {" ".join(words[:n]) for n in range(1, len(words))
                  if words[n - 1] not in _LINK_WORDS}     # pas « pâtes aux »
    for f in list(forms):
        if not f.endswith(("s", "x")):
            forms.add(f + ("x" if f.endswith("eau") else "s"))
    return sorted(forms, key=len, reverse=True)


# Ingrédients comptés à la pièce : remplacés seulement dans une quantité en grammes,
# et jamais quand la pièce elle-même est cuite, cassée ou séparée (« séparer 3 tofu
# soyeux », « pocher des tofu soyeux » n'ont pas de sens).
_COUNTED = re.compile(r"(?:^|\s)(œufs?|jaunes? d'œufs?|blancs? d'œufs?)$")
_PIECE_USE = re.compile(r"pocher|poch[ée]|frire|au plat|écaler|casser|séparer|mollet|\bdurs?\b|coque", re.I)
_VOWELS = set("aeiouàâéèêëîïôûœ")      # pas « y » (de yaourt) ni « h » (de haricots)
_H_MUET = ("huile",)                     # h muet : « d'huile », « à l'huile »
# genre du premier mot des substituts, pour accorder l'article qui les précède
_GENDER = {"tofu": "m", "yaourt": "m", "beurre": "m", "lait": "m", "sirop": "m", "jus": "m",
           "cheddar": "m", "fromage": "m",
           "crème": "f", "ricotta": "f", "mozzarella": "f", "mayonnaise": "f", "huile": "f",
           "levure": "f", "sauce": "f", "béchamel": "f"}


# Œuf servi « entier » (dur, au plat, poché, brouillé, cassé dans le plat) : le tofu soyeux
# ne tient pas, les versions vegan de ces plats prennent du tofu ferme. Le tofu soyeux reste
# pour les pâtes et appareils (pâte à choux, gnocchis, génoise, flan).
_EGG_SOLID = re.compile(r"écaler|au plat|poch|brouill|œufs? durs?|creux|remuer sans (?:cesse|arrêt)|"
                        r"ajouter les œufs \(\d+ ?g au total\)|œufs?,? (?:[^.]{0,60} )?en (?:petits )?dés|"
                        r"œufs en quartiers|casser l'œuf au centre|"
                        r"casser (?:un|les|\d+)[^.]{0,25}?œufs?(?![^.]{0,15}dans un bol)", re.I)
# Œuf utilisé seulement pour dorer ou souder (brioches, böreks) : lait de soja, l'usage vegan
_EGG_WASH = re.compile(r"(?:dorer|souder|soudant|badigeonner)[^.]*œuf battu|casser l'œuf battu \(\d+ ?g\) au centre", re.I)
_Q = r"(?:(?:\d+) œufs? \((?P<g1>\d+) ?g\)|(?:les )?(?P<g2>\d+) ?g d'œufs?(?: durs)?)"
_EGG_SOLID_RULES = [
    # œufs durs
    (re.compile(rf"[Cc]uire {_Q}(?: \([^)]*\))? \d+ minutes(?: dans [^.]*?eau bouillante| à l'eau bouillante)?"
                rf"(?:, les refroidir)?(?:,| et) les écaler(?: et les couper en (?P<cut>[a-zé]+))?"),
     lambda m: f"Couper {m['g1'] or m['g2']} g de tofu ferme en {m['cut'] or 'morceaux'}"),
    (re.compile(r"[Ff]aire cuire les (?P<g>\d+) ?g d'œufs durs pendant \d+ minutes à l'eau bouillante"),
     lambda m: f"Couper {m['g']} g de tofu ferme en tranches"),
    (re.compile(r"Entailler chaque œuf de quatre fentes, les rouler"), lambda m: "Rouler le tofu"),
    # œufs pochés ou cassés dans le plat
    (re.compile(r"[Pp]ochez des œufs dans de l'eau frémissante vinaigrée pendant (?P<n>\d+) minutes"),
     lambda m: f"Faites dorer le tofu ferme en tranches épaisses à la poêle, {m['n']} minutes par face"),
    (re.compile(r"y casser les (?P<g>\d+) ?g d'œufs pour les pocher directement dans le bouillon"),
     lambda m: f"y déposer {m['g']} g de tofu ferme en dés et le laisser chauffer dans le bouillon"),
    (re.compile(r"pocher délicatement les (?P<g>\d+) ?g d'œufs dans une eau frémissante additionnée "
                r"d'un trait de vinaigre pendant (?P<n>\d+) minutes"),
     lambda m: f"faire dorer {m['g']} g de tofu ferme en tranches à la poêle, {m['n']} minutes par face"),
    (re.compile(r"y casser les œufs \((?P<g>\d+) ?g\) et couvrir (?P<n>\d+) minutes, jusqu'à ce qu'ils soient pris"),
     lambda m: f"y déposer {m['g']} g de tofu ferme en tranches et couvrir {m['n']} minutes"),
    (re.compile(r"y casser les œufs"), lambda m: "y déposer le tofu ferme en tranches"),
    (re.compile(r"[Cc]asser les œufs directement dans la poêle"), lambda m: "Émietter le tofu directement dans la poêle"),
    (re.compile(r"casser un œuf \((?P<g>\d+) ?g\) au centre"),
     lambda m: f"déposer {m['g']} g de tofu ferme émietté au centre"),
    (re.compile(r"[Cc]asser un œuf dessus \((?P<g>\d+) ?g pour quatre crêpes\), l'étaler"),
     lambda m: f"Émietter du tofu ferme dessus ({m['g']} g pour quatre crêpes)"),
    (re.compile(r" pour obtenir des jaunes coulants qui servira de liant\. Cuire l'œuf pendant environ \d+ "
                r"minutes à feu doux, jusqu'à ce que le blanc soit ferme"), lambda m: ""),
    # œufs au plat
    (re.compile(rf"(?:[Cc]uire|[Ff]aire frire) {_Q} au plat"),
     lambda m: f"Poêler {m['g1'] or m['g2']} g de tofu ferme en tranches, 3 minutes par face,"),
    (re.compile(r"(?:[Cc]uire|[Ff]aire frire) \d+ œufs au plat \((?P<g>\d+) ?g\)"),
     lambda m: f"Poêler {m['g']} g de tofu ferme en tranches, 3 minutes par face,"),
    (re.compile(r"cuire les œufs au plat"), lambda m: "poêler le tofu ferme en tranches"),
    # œufs brouillés
    (re.compile(rf"[Bb]rouiller (?:les )?{_Q}"), lambda m: f"émietter {m['g1'] or m['g2']} g de tofu ferme et le faire revenir"),
    (re.compile(r"(?P<v>[Vv])erser les œufs sur les asperges et remuer sans cesse (?P<n>\d+) minutes, jusqu'à ce "
                r"qu'ils soient pris mais encore crémeux"),
     lambda m: f"{'A' if m['v'] == 'V' else 'a'}jouter le tofu ferme émietté sur les asperges et remuer sans "
               f"cesse {m['n']} minutes, jusqu'à ce qu'il soit bien chaud"),
    (re.compile(r"[Vv]erser les œufs et remuer sans arrêt à la spatule, (?P<n>\d+) minutes : ils doivent prendre en "
                r"petits grains serrés, jamais secs"),
     lambda m: f"Ajouter le tofu ferme émietté et remuer sans arrêt à la spatule, {m['n']} minutes : il doit "
               f"rester moelleux, jamais sec"),
    (re.compile(r"ils doivent rester crémeux et légèrement coulants"), lambda m: "il doit rester moelleux"),
    # œufs durs cités ailleurs, œufs ajoutés dans des creux de sauce, sur une galette
    (re.compile(r"\d+ œufs durs \((?P<g>\d+) ?g\) hachés"), lambda m: f"{m['g']} g de tofu ferme haché"),
    (re.compile(r"des (?P<g>\d+) ?g d'œufs durs hachés \(cuits \d+ minutes\)"),
     lambda m: f"{m['g']} g de tofu ferme émietté"),
    (re.compile(r"\d+ œufs durs \((?P<g>\d+) ?g\)"), lambda m: f"{m['g']} g de tofu ferme"),
    (re.compile(rf"[Bb]attre (?:légèrement )?{_Q}"), lambda m: f"Émietter {m['g1'] or m['g2']} g de tofu ferme"),
    (re.compile(r" sans les faire mousser"), lambda m: ""),
    (re.compile(r"le tofu et les œufs en quartiers"), lambda m: "le tofu"),
    (re.compile(r"(?P<g>\d+) ?g d'œufs durs"), lambda m: f"{m['g']} g de tofu ferme"),
    (re.compile(r"beurre (?:végétal )?d'œuf"), lambda m: "beurre au tofu"),
    (re.compile(r",? en prenant soin de répartir les ingrédients de manière égale et de laisser le blanc d'œuf cuire "
                r"jusqu'à ce qu'il soit pris"), lambda m: ", en répartissant les ingrédients de manière égale"),
    (re.compile(r"jusqu'à ce qu'ils soient pris mais encore crémeux, comme des œufs brouillés"),
     lambda m: "jusqu'à ce qu'il soit bien chaud"),
    (re.compile(r", puis les refroidir, les écaler et les couper en tranches"), lambda m: ""),
    (re.compile(r"ajouter les œufs \((?P<g>\d+) ?g au total\)"), lambda m: f"ajouter {m['g']} g de tofu ferme en tranches"),
    (re.compile(r"casser un œuf au centre \((?P<g>\d+) ?g pour les 4 galettes\)"),
     lambda m: f"émietter du tofu ferme au centre ({m['g']} g pour les 4 galettes)"),
    (re.compile(r"casser l'œuf au centre"), lambda m: "émietter le tofu ferme au centre"),
    (re.compile(r"sauce aux œufs"), lambda m: "sauce au tofu"),
    (re.compile(r"nappe bien l'œuf"), lambda m: "nappe bien le tofu"),
    (re.compile(r"[Aa]jouter \d+ œufs battus \((?P<g>\d+) ?g\) et les brouiller"),
     lambda m: f"Ajouter {m['g']} g de tofu ferme émietté et le faire revenir"),
    (re.compile(r"[Vv]erser (?P<g>\d+) ?g d'œufs? battus? et brouiller"),
     lambda m: f"Ajouter {m['g']} g de tofu ferme émietté et le faire revenir"),
    (re.compile(r"casser les (?P<g>\d+) ?g d'œufs et les brouiller"),
     lambda m: f"ajouter {m['g']} g de tofu ferme émietté et le faire revenir"),
    (re.compile(r"[Bb]attre \d+ œufs \((?P<g>\d+) ?g\) (?P<x>avec [^,]*? )?et les brouiller"),
     lambda m: f"Émietter {m['g']} g de tofu ferme {m['x'] or ''}et le faire revenir"),
    (re.compile(r"[Cc]asser \d+ œufs \((?P<g>\d+) ?g\) dans la poêle et les brouiller"),
     lambda m: f"Émietter {m['g']} g de tofu ferme dans la poêle et le faire revenir"),
    # œufs cassés dans le plat
    (re.compile(r"[Cc]asser \d+ œufs \((?P<g>\d+) ?g\) (?P<loc>à la surface|dans la soupe frémissante) et "
                r"(?:cuire|pocher) (?P<n>\d+) minutes"),
     lambda m: f"Ajouter {m['g']} g de tofu ferme en dés {m['loc']} et cuire {m['n']} minutes"),
    # suites du geste : « jusqu'à ce que le blanc soit pris et le jaune coulant »
    (re.compile(r",? jusqu'à ce que (?:le|les) blancs? soi(?:t|ent) pris(?: et (?:le|les) jaunes? encore coulants?)?"),
     lambda m: ""),
    (re.compile(r",? jusqu'à ce que l'œuf soit pris"), lambda m: ""),
    (re.compile(r",? avant que le jaune ne prenne"), lambda m: ""),
    (re.compile(r",? sans les battre au préalable"), lambda m: ""),
    (re.compile(r",? (?:pour (?:garder|obtenir) (?:le|des) jaunes? coulants?|jaune coulant)(?=[,.])"), lambda m: ""),
    # le reste de la recette parle encore des œufs
    (re.compile(r"les œufs réservés"), lambda m: "le tofu réservé"),
    (re.compile(r"les œufs coupés en deux"), lambda m: "le tofu en tranches"),
    (re.compile(r"tranches d'œuf dur"), lambda m: "tranches de tofu"),
    (re.compile(r"un demi-œuf(?: dur)?"), lambda m: "un morceau de tofu"),
    (re.compile(r"d'un œuf\b"), lambda m: "de tofu poêlé"),
    (re.compile(r"\bun œuf(?: au plat| poché)?(?= (?:par|sur|dessus))"), lambda m: "du tofu"),
    (re.compile(r"\b([Ll])es œufs\b"), lambda m: f"{m[1]}e tofu"),
    (re.compile(r"(?<=, )œufs?(?=, )"), lambda m: "tofu"),
    (re.compile(r"\b(le tofu), le tofu\b"), lambda m: m[1]),
]
# œuf battu dans une pâte ou un appareil (tofu soyeux)
_EGG_SILKEN_RULES = [
    (re.compile(r"\b([Ll])es œufs entiers crus"), lambda m: f"{m[1]}e tofu soyeux"),
    (re.compile(r"incorporer les œufs un à un"), lambda m: "incorporer le tofu soyeux petit à petit"),
    (re.compile(r"\b([Bb]attez|[Bb]attre) les œufs"), lambda m: f"{m[1]} le tofu soyeux"),
    (re.compile(r"sur les œufs en fouettant, pour les tempérer"), lambda m: "sur le tofu soyeux en fouettant, pour le tempérer"),
    (re.compile(r"au mélange de sucre et d'œuf"), lambda m: "au mélange de sucre et de tofu soyeux"),
    (re.compile(r"au mélange d'œufs?"), lambda m: "au mélange de tofu soyeux"),
    (re.compile(r"et d'œuf sur les pâtes"), lambda m: "et de tofu soyeux sur les pâtes"),
    (re.compile(r"mélange œufs-"), lambda m: "mélange tofu soyeux-"),
    (re.compile(r"la couche d'œuf"), lambda m: "la couche de tofu soyeux"),
    (re.compile(r"Battre l'œuf, l'incorporer"), lambda m: "Mixer le tofu soyeux, l'incorporer"),
    (re.compile(r"jusqu'à ce que les œufs soient cuits et le mélange"), lambda m: "jusqu'à ce que le mélange soit"),
]
# œuf de dorure ou de soudure (lait de soja)
_EGG_WASH_RULES = [
    (re.compile(r"à l'œuf battu \((?P<g>\d+) ?g\)"), lambda m: f"au lait de soja ({m['g']} g)"),
    (re.compile(r"avec de l'œuf battu \((?P<g>\d+) ?g\)"), lambda m: f"avec du lait de soja ({m['g']} g)"),
    (re.compile(r"casser l'œuf battu \((?P<g>\d+) ?g\) au centre de chaque pide"),
     lambda m: f"badigeonner le centre de chaque pide de lait de soja ({m['g']} g)"),
]


def _apply_rules(steps: list, rules) -> list:
    out = []
    for s in steps:
        if isinstance(s, str) and "œuf" in s:
            for pat, repl in rules:
                s = pat.sub(repl, s)
        out.append(s)
    return out
# pronoms qui désignaient les œufs, dans une étape où le tofu les remplace
_EGG_PRONOUNS = [
    (re.compile(r"en les gardant"), "en le gardant"), (re.compile(r"tout en les incorporant"), "tout en l'incorporant"),
    (re.compile(r"ils doivent rester"), "il doit rester"), (re.compile(r"et les servir"), "et le servir"),
    (re.compile(r"pour les déposer"), "pour le déposer"), (re.compile(r"puis les mélanger"), "puis le mélanger"),
    (re.compile(r"en les arrosant"), "en l'arrosant"), (re.compile(r"à la fourchette, les mélanger"),
                                                        "à la fourchette, le mélanger"),
    (re.compile(r"et les dorer"), "et le dorer"),
]
# accords après « œufs » → « tofu » (descriptions et étapes)
_TOFU_AGREEMENT = [
    (re.compile(r"\b([Dd])es (tofu(?: soyeux| ferme)?)\b"), lambda m: f"{m[1]}u {m[2]}"),
    (re.compile(r"\b(tofu(?: soyeux| ferme)?) (brouill|cass|frit|poch)és\b"), lambda m: f"{m[1]} {m[2]}é"),
    (re.compile(r"\btofu et tofu\b"), lambda m: "tofu"),
    (re.compile(r"\b([Tt]ofu(?: soyeux| ferme)?) brouillés cuits"), lambda m: f"{m[1]} brouillé cuit"),
    (re.compile(r"\b(tofu brouillé) à peine cuits"), lambda m: f"{m[1]} à peine cuit"),
    (re.compile(r"(?<=cuit très doucement, presque comme une crème de soja maison), montés (.*?) et servis"),
     lambda m: f", monté {m[1]} et servi"),
    (re.compile(r" et un lait de soja cassé au centre à la sortie du four"),
     lambda m: " et le centre badigeonné de lait de soja"),
    (re.compile(r" : le jaune doit rester coulant à l'ouverture"), lambda m: ""),
]


def _rewrite_egg_solid(steps: list) -> list:
    """Gestes de l'œuf entier réécrits pour le tofu ferme (voir _EGG_SOLID)."""
    out = []
    for s in steps:
        if isinstance(s, str) and re.search(r"œuf|jaune|blanc", s):
            for pat, repl in _EGG_SOLID_RULES:
                s = pat.sub(repl, s)
            if "tofu" in s:
                for pat, repl in _EGG_PRONOUNS:
                    s = pat.sub(repl, s)
        out.append(s)
    return out


def _tofu_agreement(text):
    if not isinstance(text, str):
        return text
    for pat, repl in _TOFU_AGREEMENT:
        text = pat.sub(repl, text)
    return text


def _drop_echo(m) -> str:
    """Retire les mots qui suivent un substitut et répètent un morceau de son nom
    (« pâte brisée végétale brisée », « roux … végétal de curry »). Il faut au moins
    un mot plein : « en » ou « de » seuls ne sont jamais retirés."""
    sub_words = m.group(1).lower().split()
    tail = m.group(2).split()
    for k in range(len(tail), 0, -1):
        seq = [w.lower() for w in tail[:k]]
        if any(w not in _LINK_WORDS for w in seq) and any(
                sub_words[i:i + k] == seq for i in range(1, len(sub_words) - k + 1)):
            return m.group(1) + "".join(" " + w for w in tail[k:])
    return m.group(0)


# Autres noms d'un ingrédient dans les textes des recettes (« 300 g de ladyfinger »)
_TEXT_ALIASES = {"ladyfinger": ("ladyfinger",)}


def _pluralize(name: str) -> str:
    """« courgette » → « courgettes », « beurre de cacahuète » → « beurres de cacahuète »."""
    words = name.split()
    out = []
    for i, w in enumerate(words):
        if w in _LINK_WORDS or w.startswith(("d'", "d’")):
            return " ".join(out + words[i:])
        if w.endswith(("s", "x", "z")):
            out.append(w)
        elif w.endswith(("eau", "eu")):
            out.append(w + "x")
        elif w.endswith("al"):
            out.append(w[:-2] + "aux")
        else:
            out.append(w + "s")
    return " ".join(out)


def _rewrite_steps(steps: list, applied: list[dict], prose: bool = False,
                   edit: bool = False) -> tuple[list, int]:
    """Étapes avec les ingrédients de substitution. Prudent : mots entiers, un seul
    passage (un substitut n'est jamais remplacé à son tour), « 3 œufs (150 g) » →
    « 150 g de tofu soyeux », élision « de / d' » rétablie autour des seuls
    substituts ; dans les étapes, les œufs ne sont remplacés que dans une quantité en
    grammes. prose (description) : « un appareil d'œufs » → « de tofu soyeux » aussi.
    edit (recette modifiée par un membre) : pluriel accordé (« les aubergines » →
    « les courgettes ») et « d'aubergines » remplacé aussi (« de courgettes »).
    Renvoie (étapes, nb modifiées)."""
    mapping: dict[str, str] = {}
    # noms complets d'abord : « lait » (liquide → lait de soja) ne doit pas être pris
    # par le début de « lait en poudre » (→ farine d'amande)
    for heads in (False, True):
        for a in applied:
            sub = _short(a.get("substitute_name") or "")
            if not sub:
                continue
            names = [a.get("original_name") or ""] + list(_TEXT_ALIASES.get(a.get("original"), ()))
            for name in names:
                for f in _forms(name, heads):
                    mapping.setdefault(f, sub)
    if not mapping:
        return steps, 0
    counted_forms = [f for f in mapping if _COUNTED.search(f)]
    mass_forms = [f for f in mapping if f not in counted_forms]
    # forme au pluriel : la même sans son « s » / « x » final est aussi une forme
    plural_forms = {f for f in mapping if edit and f[-1:] in "sx" and f[:-1] in mapping}

    def alt(fs):
        return "|".join(re.escape(f) for f in sorted(fs, key=len, reverse=True))

    rules = []
    if counted_forms:
        c = alt(counted_forms)
        # « 3 œufs (150 g) », « 2 œufs battus (110 g) » ; « 220 g d'œufs battus »
        rules.append((re.compile(rf"\b\d+ ({c})(?: [a-zéèêû]+)? \((\d+(?:[,.]\d+)?) ?(g|ml)\)", re.I),
                      lambda m: f"{m.group(2)} {m.group(3)} de {mapping[m.group(1).lower()]}", True))
        rules.append((re.compile(rf"\b(\d+(?:[,.]\d+)?) ?(g|ml) (?:de |d')({c})(?: (?:battus?|entiers?|crus?))?(?!\w)", re.I),
                      lambda m: f"{m.group(1)} {m.group(2)} de {mapping[m.group(3).lower()]}", True))
        if prose:
            # description : l'œuf comme ingrédient, hors « jaune / blanc d'œuf » non remplacés
            rules.append((re.compile(rf"(?<!jaune d')(?<!jaunes d')(?<!blanc d')(?<!blancs d')"
                                     rf"(?<![\w])({c})(?![\w-])", re.I),     # pas « œufs-crème »
                          lambda m: (lambda s: s[:1].upper() + s[1:] if m.group(1)[:1].isupper() else s)(
                              mapping[m.group(1).lower()]), True))
    if mass_forms:
        def mass(m):
            key = m.group(1).lower()
            sub = _pluralize(mapping[key]) if key in plural_forms else mapping[key]
            # « Paneer maison en cubes… » en début de phrase → « Tofu maison… »
            return sub[:1].upper() + sub[1:] if m.group(1)[:1].isupper() else sub
        # edit : aussi après « d' » (l'élision est rétablie plus bas), jamais après « l' »
        # (le genre du remplaçant est inconnu)
        before = r"(?<![\w])(?<![^dD]')(?<![^dD]’)" if edit else r"(?<![\w'’])"
        rules.append((re.compile(rf"{before}({alt(mass_forms)})(?!\w)", re.I), mass, False))
    out, changed = [], 0
    for step in steps:
        if not isinstance(step, str):
            out.append(step)
            continue
        new = step
        for pattern, repl, counted in rules:
            if counted and _PIECE_USE.search(step):
                continue
            new = pattern.sub(repl, new)
        if new != step:
            # élision autour des seuls substituts insérés : le reste de l'étape n'est
            # pas touché (« de haricots »)
            subs = set(mapping.values())
            if edit:
                subs |= {_pluralize(v) for v in subs}
            for sub in subs:
                esc = re.escape(sub)
                elide = sub[:1] in _VOWELS or sub.startswith(_H_MUET)
                if elide:
                    new = re.sub(rf"\b([Dd])e {esc}", lambda mm, s=sub: f"{mm.group(1)}'{s}", new)
                else:
                    new = re.sub(rf"\b([Dd])'{esc}", lambda mm, s=sub: f"{mm.group(1)}e {s}", new)
                # « parmesan râpé » → « levure nutritionnelle en paillettes » (sans « râpé »)
                new = re.sub(rf"({esc}) râpée?s?\b", lambda mm: mm.group(1), new)
                # qualificatifs du seul produit d'origine : « crème fraîche », « lait entier »,
                # « lait de vache », « fromage frais », « œuf cru »
                new = re.sub(rf"({esc}) (?:fraîches?|frais|entiers?|entières?|de vache|demi-écrémée?|"
                             rf"écrémée?|fermiers?|fermières?|crus?|crues?)(?![\w-])",
                             lambda mm: mm.group(1), new, flags=re.I)
                # écho : seul le début du nom d'origine a été remplacé et la suite est
                # restée (« roux de curry » → « roux de curry japonais végétal de curry »)
                new = re.sub(rf"({esc})((?: [\w'’-]+){{1,4}})", _drop_echo, new, flags=re.I)
                # article accordé au substitut : « de la crème » → « du yaourt de soja »
                gender = _GENDER.get(sub.split()[0])
                if not elide:                           # « l'œuf » → « le tofu soyeux »
                    new = re.sub(rf"\b([Ll])['’]({esc})", lambda mm: mm.group(1)
                                 + ("a " if gender == "f" else "e ") + mm.group(2), new, flags=re.I)
                    if gender != "f":                   # « à le », « de le » → « au », « du »
                        new = re.sub(rf"\b([Àà]) le ({esc})", lambda mm: "au " + mm.group(2), new, flags=re.I)
                        new = re.sub(rf"\b([Dd])e le ({esc})", lambda mm: mm.group(1) + "u " + mm.group(2),
                                     new, flags=re.I)
                if gender == "m":
                    new = re.sub(rf"\b([Dd])e la {esc}", lambda mm, s=sub: f"{mm.group(1)}u {s}", new)
                    new = re.sub(rf"\b([Àà]) la {esc}", lambda mm, s=sub: f"au {s}", new)
                    new = re.sub(rf"\b([Ll])a {esc}", lambda mm, s=sub: f"{mm.group(1)}e {s}", new)
                elif gender == "f":
                    la = "l'" if elide else "la "       # « à l'huile de coco », pas « à la huile »
                    new = re.sub(rf"\b([Dd])u {esc}", lambda mm, s=sub: f"{mm.group(1)}e {la}{s}", new)
                    new = re.sub(rf"\b([Aa])u {esc}", lambda mm, s=sub: f"{'À' if mm.group(1) == 'A' else 'à'} {la}{s}", new)
                    new = re.sub(rf"\b([Ll])e {esc}", lambda mm, s=sub: f"{mm.group(1)}{la[1:]}{s}", new)
            changed += 1
        out.append(new)
    return out, changed


def vegan_variant(recipe: dict) -> dict:
    """
    Retourne la version vegan d'une recette, générée par substitution.

    L'index pré-calculé (vegan_variants_index.json) n'est plus consulté : ses
    variantes pointent vers des recettes inexistantes et ses substitutions vers
    d'anciens ids courts — la recette originale était renvoyée inchangée.

    Returns:
        {recipe, substitutions: [{original, substitute, original_name,
         substitute_name}], unresolved: [{id, name}], source}
        source : "generated" (tout est remplacé), "partial" (des ingrédients
        non vegan restent : la variante n'est pas étiquetée vegan) ou
        "already_vegan".
    """
    import copy
    r = copy.deepcopy(recipe)
    applied = []
    unresolved = []

    has_composition = "composition" in r
    target_list = r.get("composition", r.get("ingredients", []))
    new_ings = []

    steps0 = [s for s in r.get("instructions") or [] if isinstance(s, str)]
    # le geste doit porter sur l'œuf (« pocher les gnocchis » ne compte pas)
    egg_solid = any("œuf" in s.lower() and _EGG_SOLID.search(s) for s in steps0)
    egg_steps = [s for s in steps0 if "œuf" in s.lower()]
    egg_qty = sum(float(c.get("quantity") or 0) for c in target_list
                  if isinstance(c, dict) and _item_id(c) == "egg_raw")
    egg_wash = (not egg_solid and bool(egg_steps) and egg_qty <= 60
                and all(_EGG_WASH.search(s) for s in egg_steps))
    for item in target_list:
        iid = _item_id(item)
        key = iid.lower()
        sub = VEGAN_SUBS_CIQUAL.get(key) or VEGAN_SUBS.get(key)
        if key == "egg_raw" and egg_solid:
            sub = "tofu_plain_pre_packaged"      # œuf dur, au plat, brouillé : tofu ferme
        elif key == "egg_raw" and egg_wash:
            sub = "soybean_milk_unsweetened_plant"   # dorure, soudure : lait de soja
        if sub:
            applied.append({"original": iid, "substitute": sub,
                            "original_name": _display_name(iid),
                            "substitute_name": _display_name(sub)})
            if not isinstance(item, dict):
                item = sub
            elif "ingredient" in item:
                item = {**item, "ingredient": sub}
            else:
                item = {**item, "ingredient_id": sub}
        elif iid and _is_vegan_id(key) is False:
            unresolved.append({"id": iid, "name": _display_name(iid)})
        new_ings.append(item)

    if has_composition:
        r["composition"] = new_ings
    else:
        r["ingredients"] = new_ings

    # Noms affichés par la fiche recette (comme enrich_one) : sans eux les
    # substituts s'affichaient sous leur id brut.
    from backend.db.culinary_repositories import _recipes_index
    r["ingredients_meta"] = {
        _item_id(i): {"name_fr": _display_name(_item_id(i)),
                      **({"recipe_id": _item_id(i)} if _item_id(i) in _recipes_index() else {})}
        for i in new_ings if isinstance(i, dict) and _item_id(i)
    }

    # Étapes réécrites avec les substituts (« 250 g de paneer » → « 250 g de tofu »)
    if applied and isinstance(r.get("instructions"), list):
        steps = r["instructions"]
        egg_subs = {a["original"]: a["substitute"] for a in applied if a["original"].startswith("egg_")}
        if (egg_solid and "egg_raw" in egg_subs) or "egg_hard_boiled" in egg_subs:
            steps = _rewrite_egg_solid(steps)
        elif egg_wash and "egg_raw" in egg_subs:
            steps = _apply_rules(steps, _EGG_WASH_RULES)
        elif egg_subs.get("egg_raw") == "silken_tofu_pre_packaged":
            steps = _apply_rules(steps, _EGG_SILKEN_RULES)
        if egg_subs.get("egg_white_raw") == "aquafaba":      # meringue : « 140 g de blancs en neige »
            steps = [re.sub(r"(\d+) ?g de blancs en neige", r"\1 g d'aquafaba en neige", s)
                     if isinstance(s, str) else s for s in steps]
        r["instructions"], r["_steps_rewritten"] = _rewrite_steps(steps, applied)
        if any(a["original"] == "egg_raw" for a in applied):
            r["instructions"] = [_tofu_agreement(s) for s in r["instructions"]]
    # Description aussi (« garnies de queso fresco » → « garnies de tofu ») ; le titre
    # reste le nom du plat (« Palak paneer »), le badge « Version vegan » l'accompagne.
    if applied and isinstance(r.get("description"), str):
        r["description"] = _rewrite_steps([r["description"]], applied, prose=True)[0][0]
        if any(a["original"] == "egg_raw" for a in applied):
            r["description"] = _tofu_agreement(r["description"])

    # Régimes et allergènes recalculés sur la nouvelle composition : la variante
    # gardait ceux de l'original (« œufs », « lait » affichés après substitution)
    # et ignorait ceux des substituts — tofu soyeux, lait et crème de soja (soja),
    # ricotta de cajou (fruits à coque) — un risque pour les personnes allergiques.
    from backend.engine.rule_engine.diet import allergen_tags, compute_diet_flags
    core = [c for c in r.get("composition") or []
            if isinstance(c, dict) and (c.get("meta") or {}).get("role") != "serving_suggestion"]
    computed = compute_diet_flags({**r, "composition": core})
    allergens = allergen_tags(r)
    flags = dict(r.get("diet_flags") or {})
    for f in ("vegetarian", "gluten_free", "lactose_free", "nut_free"):
        if f in computed:
            flags[f] = bool(computed[f])
    excludes = {"gluten_free": {"gluten"}, "lactose_free": {"milk", "lactose"},
                "nut_free": {"tree_nuts", "peanuts"}}
    for f, tags_ in excludes.items():
        if tags_ & set(allergens):
            flags[f] = False
    flags["vegan"] = False
    r["diet_flags"] = flags
    r.setdefault("tags", {})
    if isinstance(r["tags"], dict):
        r["tags"]["allergens"] = allergens
        r["tags"]["diet"] = [d for d in (r["tags"].get("diet") or []) if d != "vegan"
                             and not (d in excludes and flags.get(d) is False)]
    r["diet_flags_enriched"] = {"egg_free": "eggs" not in allergens,
                                "dairy_free": "milk" not in allergens,
                                "soy_free": "soy" not in allergens}

    if unresolved:
        source = "partial"
    else:
        source = "generated" if applied else "already_vegan"
        r["_vegan_variant"] = True
        if "tags" in r and isinstance(r["tags"], dict):
            if "diet" not in r["tags"]: r["tags"]["diet"] = []
            if "vegan" not in r["tags"]["diet"]: r["tags"]["diet"].append("vegan")
            if "vegetarien" not in r["tags"]["diet"]: r["tags"]["diet"].append("vegetarien")
        if r.get("diet_flags"):
            r["diet_flags"] = {**r["diet_flags"], "vegan": True, "vegetarian": True}

    # Pas de version vegan quand elle ne serait pas fiable : on ne la propose pas plutôt que
    # d'en fabriquer une bancale (décision du 2026-11-21).
    reason = unreliable_reason(recipe, r, applied, unresolved)
    if reason:
        return {"recipe": recipe, "substitutions": [], "unresolved": unresolved,
                "source": "unavailable", "reason": reason}

    return {
        "recipe":        r,
        "substitutions": applied,
        "unresolved":    unresolved,
        "source":        source,
    }


_EGG_IDS = {"egg_raw", "egg_yolk_raw", "egg_white_raw", "egg_hard_boiled"}
# plat qui porte l'œuf dans son nom : le remplacer contredit le plat
_EGG_DISH = re.compile(r"\b(?:œufs?|huevos|omelette|anda)\b", re.I)
# technique à base d'œuf restée sans équivalent (blancs en neige, jaunes séparés…)
_EGG_LEFT = re.compile(r"œuf|(?<!oignon )(?<!oignons )\bjaunes?\b(?! d'oignon)|blancs? en neige", re.I)


def unreliable_reason(original: dict, variant: dict, applied: list, unresolved: list) -> str | None:
    """Pourquoi la version vegan d'une recette ne serait pas fiable (None : elle l'est)."""
    if unresolved:
        names = ", ".join(u.get("name") or u.get("id") for u in unresolved)
        return f"pas de remplacement vegan pour : {names}"
    if not any(a["original"] in _EGG_IDS for a in applied):
        return None
    title = (original.get("titles") or {}).get("fr") or ""
    if _EGG_DISH.search(title):
        return "l'œuf est l'ingrédient principal de ce plat"
    steps = [s for s in variant.get("instructions") or [] if isinstance(s, str)]
    if any(_EGG_LEFT.search(s) for s in steps):
        return "la recette repose sur une technique à base d'œufs (blancs en neige, jaunes) sans équivalent fiable"
    return None
