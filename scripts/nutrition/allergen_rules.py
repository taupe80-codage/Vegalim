"""
allergen_rules.py — Règles allergènes UE (Règl. 1169/2011, annexe II) et
flags d'exclusion dérivés, partagées par build_dict_v2.py et
fix_dict_allergens.py.

Pourquoi un module séparé : build_dict_v2.py ne recalculait allergens_eu que
si le champ était absent (`is None`) ; les listes vides héritées de l'ancien
dico survivaient donc à chaque rebuild (œuf cru, beurre, tofu, sésame… sans
allergène). Et la règle gluten ne connaissait que les noms de céréales
(wheat/barley/rye…) : pain, pâtes, couscous, pâtes à tarte ressortaient
gluten_free=True. Ces règles s'appliquent sur la clé d'entrée (tokens séparés
par '_') en plus de la taxonomie.

Principe : ces fonctions ne font qu'AJOUTER des allergènes et passer des flags
d'exclusion à False — jamais l'inverse. Une sur-déclaration exclut une recette
à tort ; une sous-déclaration expose un allergique.
"""
from __future__ import annotations

# ── Gluten ─────────────────────────────────────────────────────────────────────
GLUTEN_TOKENS = frozenset({
    'wheat', 'barley', 'rye', 'spelt', 'einkorn', 'kamut', 'khorasan', 'farro',
    'triticale', 'bulgur', 'couscous', 'semolina', 'seitan', 'oat', 'oats',
    'bread', 'breadcrumbs', 'croutons', 'crispbread', 'toast', 'pita', 'bagel',
    'naan', 'paratha', 'brioche', 'baguette', 'panini', 'focaccia', 'bun',
    'matzo', 'bannock', 'pasta', 'udon', 'ramen', 'gnocchi', 'pastry', 'phyllo',
    'filo', 'crackers', 'ladyfinger', 'shoyu',
    # 'brick' / 'pizza' volontairement absents (fromage brick, sauce pizza) :
    # feuilles de brick et pâtes à pizza sont couvertes par GLUTEN_SUBS.
})
GLUTEN_SUBS = frozenset({
    'wheat', 'barley', 'rye', 'oats', 'bulgur', 'couscous', 'breads', 'pasta',
    'wheat_semolinas', 'heritage_varieties', 'pastry_doughs_and_pie_crusts',
})
# Tokens qui annulent la règle gluten (produit explicitement sans gluten, ou
# « pain » qui n'en est pas : papadum = farine de lentille)
GLUTEN_EXCEPT_TOKENS = frozenset({'papad', 'papadum'})
# Sous-catégories de céréales sans gluten (pâtes de maïs, nouilles de riz…)
GLUTEN_FREE_SUBS = frozenset({'rice', 'corn', 'millet', 'sorghum', 'buckwheat',
                              'quinoa', 'amaranth', 'teff', 'fonio', 'tapioca'})

# ── Règles taxonomiques (cat1, cat2) — historiques de build_dict_v2.py ──────────
ALLERGEN_RULES = [
    (None,'wheat',['cereals_gluten']),(None,'barley',['cereals_gluten']),
    (None,'rye',['cereals_gluten']),(None,'oat',['cereals_gluten']),
    (None,'spelt',['cereals_gluten']),(None,'kamut',['cereals_gluten']),
    ('cereals','pasta',['cereals_gluten']),('cereals','semolina',['cereals_gluten']),
    ('dairy',None,['milk']),('eggs',None,['eggs']),(None,'prepared_eggs',['eggs']),
    (None,'peanut',['peanuts']),
    ('nuts_and_seeds','almond',['tree_nuts']),('nuts_and_seeds','walnut',['tree_nuts']),
    ('nuts_and_seeds','hazelnut',['tree_nuts']),('nuts_and_seeds','cashew',['tree_nuts']),
    ('nuts_and_seeds','pistachio',['tree_nuts']),('nuts_and_seeds','brazil',['tree_nuts']),
    ('nuts_and_seeds','macadamia',['tree_nuts']),('nuts_and_seeds','pecan',['tree_nuts']),
    ('nuts_and_seeds','pine',['tree_nuts']),
    (None,'soy',['soybeans']),(None,'sesame',['sesame']),(None,'mustard',['mustard']),
    (None,'celery',['celery']),('fish',None,['fish']),
    (None,'crustacean',['crustaceans']),(None,'shrimp',['crustaceans']),
    (None,'mussel',['molluscs']),(None,'oyster',['molluscs']),(None,'squid',['molluscs']),
    (None,'lupin',['lupin']),(None,'wine',['sulphites']),(None,'vinegar',['sulphites']),
]

def get_allergens(cat: str, sub: str) -> list:
    cat_l, sub_l = cat.lower(), sub.lower()
    if any(sub_l.startswith(g) for g in GLUTEN_FREE_SUBS): return []
    als: set = set()
    for rc, rs, a in ALLERGEN_RULES:
        if (rc is None or cat_l.startswith(rc)) and (rs is None or sub_l.startswith(rs)):
            als.update(a)
    return sorted(als)


# ── Autres allergènes par token ────────────────────────────────────────────────
SOY_TOKENS       = frozenset({'soy', 'soya', 'soybean', 'tofu', 'tempeh', 'tempe',
                              'miso', 'natto', 'edamame', 'okara', 'tvp', 'yuba',
                              'shoyu', 'tamari'})
SESAME_TOKENS    = frozenset({'sesame', 'tahini', 'tahina', 'gomasio'})
PEANUT_TOKENS    = frozenset({'peanut', 'peanuts'})
TREE_NUT_TOKENS  = frozenset({'almond', 'almonds', 'hazelnut', 'hazelnuts', 'walnut',
                              'walnuts', 'cashew', 'cashews', 'pecan', 'pecans',
                              'pistachio', 'pistachios', 'macadamia', 'brazil',
                              'marzipan', 'praline', 'gianduja'})
MILK_TOKENS      = frozenset({'milk', 'buttermilk', 'butter', 'cheese', 'cream', 'yogurt',
                              'yoghurt', 'ghee', 'paneer', 'whey', 'kefir', 'ricotta',
                              'mozzarella', 'parmesan', 'feta', 'mascarpone', 'tzatziki',
                              'custard', 'bechamel', 'brioche'})
# Marqueurs d'une version végétale ou d'un faux ami (beurre de cacahuète,
# lait de coco, crème de tartre, kéfir d'eau…)
MILK_EXCEPT_TOKENS = frozenset({'plant', 'vegan', 'soy', 'soybean', 'coconut', 'almond',
                                'cashew', 'peanut', 'sesame', 'tahini', 'sunflower',
                                'cocoa', 'oat', 'rice', 'shea', 'water', 'tartar',
                                'thistle', 'vegetable', 'bean', 'fruit'})
EGG_TOKENS       = frozenset({'egg', 'eggs', 'omelette', 'zabaglione', 'ladyfinger',
                              'brioche', 'mayonnaise', 'meringue'})
EGG_EXCEPT_TOKENS = frozenset({'plant', 'vegan'})
CELERY_TOKENS    = frozenset({'celery', 'celeriac'})
MUSTARD_TOKENS   = frozenset({'mustard'})
LUPIN_TOKENS     = frozenset({'lupin', 'lupine'})


def _tokens(key: str) -> set[str]:
    return set((key or '').lower().split('_'))


def is_explicitly_gluten_free(entry_key: str) -> bool:
    """Produit étiqueté sans gluten (ex. pasta_raw_gluten_free_dried)."""
    return 'gluten_free' in (entry_key or '').lower()


def key_allergens(entry_key: str, sub_label: str = '') -> set[str]:
    """Allergènes UE déductibles de la clé d'entrée et de la sous-catégorie."""
    t = _tokens(entry_key)
    sub = (sub_label or '').lower()
    out: set[str] = set()

    if (not is_explicitly_gluten_free(entry_key)
            and not (t & GLUTEN_EXCEPT_TOKENS)
            and sub not in GLUTEN_FREE_SUBS):
        if (t & GLUTEN_TOKENS) or sub in GLUTEN_SUBS:
            out.add('cereals_gluten')
    # Huile de soja raffinée : exemptée d'étiquetage (annexe II, 6.a)
    if (t & SOY_TOKENS) and 'oil' not in t:
        out.add('soybeans')
    if t & SESAME_TOKENS:
        out.add('sesame')
    if t & PEANUT_TOKENS:
        out.add('peanuts')
    if t & TREE_NUT_TOKENS:
        out.add('tree_nuts')
    if (t & MILK_TOKENS) and not (t & MILK_EXCEPT_TOKENS):
        out.add('milk')
    if (t & EGG_TOKENS) and not (t & EGG_EXCEPT_TOKENS):
        out.add('eggs')
    if t & CELERY_TOKENS:
        out.add('celery')
    if t & MUSTARD_TOKENS:
        out.add('mustard')
    if t & LUPIN_TOKENS:
        out.add('lupin')
    return out


def restrict_diet_profile(dp: dict, allergens, entry_key: str = '',
                          sub_label: str = '') -> dict:
    """Passe à False les flags d'exclusion contredits par les allergènes.
    Ne passe jamais un flag de False à True. Modifie et retourne dp."""
    al = set(allergens or [])
    if 'cereals_gluten' in al and not is_explicitly_gluten_free(entry_key):
        dp['gluten_free'] = False
    if 'soybeans' in al:
        dp['soy_free'] = False
    if 'eggs' in al:
        dp['egg_free'] = False
        dp['vegan'] = False
    if 'milk' in al:
        dp['dairy_free'] = False
        dp['lactose_free'] = False
        dp['vegan'] = False
    if al & {'tree_nuts', 'peanuts'}:
        dp['nut_free'] = False
    # Miel : produit animal (non couvert par les allergènes)
    if (sub_label or '').lower() == 'honeys' or 'honey' in _tokens(entry_key):
        dp['vegan'] = False
    return dp
