"""
config/schema.py
Schéma pivot CDC v4, constantes partagées, dictionnaires de canonicalisation.
Importé par tous les modules — ne dépend d'aucun autre module interne.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Optional
import json

# ═══════════════════════════════════════════════════════════════════════════════
# SCHÉMA PIVOT — CDC v4
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class IngredientEntry:
    ingredient: str          # clé canonique (snake_case anglais)
    quantity: Optional[float] = None
    unit: str = ""
    meta: dict = field(default_factory=lambda: {
        "role": "",          # base | aromatic | fat | binding | seasoning | garnish
        "form": "",          # whole | chopped | sliced | ground | julienne | ...
        "state": "raw",      # raw | cooked | frozen | dried
        "preparation": "",   # grilled | blanched | roasted | ...
    })


@dataclass
class TimingEntry:
    prep_active_min: int = 0
    prep_passive_min: int = 0
    cook_min: int = 0
    total_min: int = 0


@dataclass
class NutritionEntry:
    kcal: Optional[float] = None
    proteines_g: Optional[float] = None
    glucides_g: Optional[float] = None
    lipides_g: Optional[float] = None
    fibres_g: Optional[float] = None


@dataclass
class RecipeCDC:
    """Schéma complet CDC v4 — sortie normalisée du pipeline."""
    id: str = ""
    titles: dict = field(default_factory=lambda: {"original": "", "fr": "", "en": ""})
    description: str = ""
    origin: dict = field(default_factory=lambda: {
        "cuisine": "", "country": "", "region": "", "city": ""
    })
    servings: int = 4
    timing: TimingEntry = field(default_factory=TimingEntry)
    composition: list[IngredientEntry] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    tags: dict = field(default_factory=lambda: {
        "diet": [],        # vegan | vegetarian | gluten_free | ...
        "allergens": [],   # 14 allergènes EU
        "technique": [],
        "process": [],
    })
    diet_flags: dict = field(default_factory=lambda: {
        "vegan": False, "vegetarian": False, "gluten_free": False,
        "lactose_free": False, "nut_free": False,
    })
    equipment: list[str] = field(default_factory=list)
    difficulty_level: str = "medium"   # easy | medium | hard | expert
    dish_type: str = ""
    nutrition: NutritionEntry = field(default_factory=NutritionEntry)
    # Pipeline metadata
    _source: str = ""          # mealdb | recipenlg | wikibooks | synthesized
    _cluster_id: str = ""
    _quality_score: float = 0.0
    _flags: list[str] = field(default_factory=list)   # alertes validator
    _corrections_log: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d['timing'] = asdict(self.timing)
        d['nutrition'] = asdict(self.nutrition)
        d['composition'] = [asdict(c) for c in self.composition]
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=indent)


# ═══════════════════════════════════════════════════════════════════════════════
# DICTIONNAIRE DE CANONICALISATION DES INGRÉDIENTS
# ═══════════════════════════════════════════════════════════════════════════════

INGREDIENT_CANON: dict[str, str] = {
    # Céréales & féculents
    "riz": "rice", "rice": "rice", "basmati": "basmati_rice",
    "pâtes": "pasta", "pasta": "pasta", "spaghetti": "spaghetti",
    "farine": "flour", "flour": "flour", "farine de blé": "flour",
    "pain": "bread", "bread": "bread",
    "couscous": "couscous", "boulgour": "bulgur", "bulgur": "bulgur",
    "quinoa": "quinoa", "orge": "barley", "barley": "barley",
    "avoine": "oat", "oat": "oat", "polenta": "polenta",
    # Légumineuses
    "lentilles": "lentils", "lentils": "lentils", "red lentils": "red_lentils",
    "pois chiches": "chickpeas", "chickpeas": "chickpeas", "chickpea": "chickpeas",
    "haricots": "beans", "beans": "beans", "black beans": "black_beans",
    "flageolets": "flageolet_beans", "pois cassés": "split_peas",
    "tofu": "tofu", "tempeh": "tempeh", "edamame": "edamame",
    "seitan": "seitan",
    # Légumes courants
    "tomate": "tomato", "tomato": "tomato", "tomatoes": "tomato",
    "oignon": "onion", "onion": "onion", "red onion": "red_onion",
    "ail": "garlic", "garlic": "garlic",
    "gingembre": "ginger", "ginger": "ginger",
    "carotte": "carrot", "carrot": "carrot", "carrots": "carrot",
    "courgette": "zucchini", "zucchini": "zucchini", "courgettes": "zucchini",
    "aubergine": "eggplant", "eggplant": "eggplant", "aubergines": "eggplant",
    "poivron": "bell_pepper", "bell pepper": "bell_pepper",
    "épinard": "spinach", "spinach": "spinach",
    "champignon": "mushroom", "mushroom": "mushroom", "mushrooms": "mushroom",
    "brocoli": "broccoli", "broccoli": "broccoli",
    "chou-fleur": "cauliflower", "cauliflower": "cauliflower",
    "patate douce": "sweet_potato", "sweet potato": "sweet_potato",
    "pomme de terre": "potato", "potato": "potato", "potatoes": "potato",
    "céleri": "celery", "celery": "celery",
    "poireau": "leek", "leek": "leek",
    "maïs": "corn", "corn": "corn",
    "petit pois": "peas", "peas": "peas", "green peas": "peas",
    "avocat": "avocado", "avocado": "avocado",
    # Herbes & épices
    "persil": "parsley", "parsley": "parsley",
    "coriandre": "cilantro", "cilantro": "cilantro", "coriander": "cilantro",
    "basilic": "basil", "basil": "basil",
    "thym": "thyme", "thyme": "thyme",
    "romarin": "rosemary", "rosemary": "rosemary",
    "laurier": "bay_leaf", "bay leaf": "bay_leaf",
    "cumin": "cumin", "curcuma": "turmeric", "turmeric": "turmeric",
    "paprika": "paprika", "curry": "curry_powder", "curry powder": "curry_powder",
    "cannelle": "cinnamon", "cinnamon": "cinnamon",
    "garam masala": "garam_masala", "cardamome": "cardamom",
    "safran": "saffron", "saffron": "saffron",
    "piment": "chili", "chili": "chili", "chilli": "chili",
    "poivre": "pepper", "pepper": "pepper", "black pepper": "pepper",
    "sel": "salt", "salt": "salt",
    # Matières grasses & sauces
    "huile d'olive": "olive_oil", "olive oil": "olive_oil",
    "huile": "oil", "oil": "oil", "vegetable oil": "oil",
    "beurre": "butter", "butter": "butter",
    "tahini": "tahini",
    "sauce soja": "soy_sauce", "soy sauce": "soy_sauce", "tamari": "tamari",
    "miso": "miso",
    # Produits laitiers & œufs
    "lait": "milk", "milk": "milk",
    "crème": "cream", "cream": "cream", "heavy cream": "cream",
    "fromage": "cheese", "cheese": "cheese",
    "parmesan": "parmesan", "mozzarella": "mozzarella", "feta": "feta",
    "yaourt": "yogurt", "yogurt": "yogurt", "yoghurt": "yogurt",
    "œuf": "egg", "egg": "egg", "eggs": "egg",
    # Liquides & bouillons
    "eau": "water", "water": "water",
    "bouillon": "broth", "broth": "broth", "stock": "broth",
    "lait de coco": "coconut_milk", "coconut milk": "coconut_milk",
    "vin": "wine", "wine": "wine", "white wine": "white_wine",
    "vinaigre": "vinegar", "vinegar": "vinegar",
    "jus de citron": "lemon_juice", "lemon juice": "lemon_juice",
    "citron": "lemon", "lemon": "lemon", "lime": "lime",
    # Sucrants
    "sucre": "sugar", "sugar": "sugar", "brown sugar": "brown_sugar",
    "miel": "honey", "honey": "honey",
    "sirop d'agave": "agave_syrup", "agave": "agave_syrup",
    # Noix & graines
    "noix": "walnut", "walnut": "walnut",
    "amande": "almond", "almond": "almond", "almonds": "almond",
    "cajou": "cashew", "cashew": "cashew",
    "noisette": "hazelnut", "hazelnut": "hazelnut",
    "sésame": "sesame", "sesame": "sesame", "sesame seeds": "sesame",
    "graines de tournesol": "sunflower_seeds",
    "graines de courge": "pumpkin_seeds",
    "pignons": "pine_nut", "pine nuts": "pine_nut",
}

# ═══════════════════════════════════════════════════════════════════════════════
# CONVERSION D'UNITÉS → grammes / ml
# ═══════════════════════════════════════════════════════════════════════════════

UNIT_CONVERSIONS: dict[str, tuple[float, str]] = {
    # → grammes
    "kg": (1000.0, "g"),
    "lb": (453.6, "g"),
    "lbs": (453.6, "g"),
    "oz": (28.35, "g"),
    "g": (1.0, "g"),
    # → ml
    "l": (1000.0, "ml"),
    "litre": (1000.0, "ml"),
    "liter": (1000.0, "ml"),
    "dl": (100.0, "ml"),
    "cl": (10.0, "ml"),
    "ml": (1.0, "ml"),
    "fl oz": (29.57, "ml"),
    "cup": (240.0, "ml"),
    "cups": (240.0, "ml"),
    "tbsp": (15.0, "ml"),
    "tablespoon": (15.0, "ml"),
    "tablespoons": (15.0, "ml"),
    "tsp": (5.0, "ml"),
    "teaspoon": (5.0, "ml"),
    "teaspoons": (5.0, "ml"),
}

# ═══════════════════════════════════════════════════════════════════════════════
# CLAMP CULINAIRE — quantités max réalistes par portion (grammes)
# ═══════════════════════════════════════════════════════════════════════════════

SPICE_CLAMP_G: dict[str, float] = {
    "cumin": 8.0,     "turmeric": 5.0,    "garlic": 30.0,
    "chili": 5.0,     "cinnamon": 6.0,    "clove": 3.0,
    "nutmeg": 3.0,    "cardamom": 4.0,    "saffron": 1.0,
    "cayenne": 4.0,   "smoked_paprika": 8.0, "curry_powder": 10.0,
    "ginger": 15.0,   "paprika": 10.0,    "allspice": 4.0,
    "star_anise": 4.0, "fenugreek": 5.0,  "garam_masala": 8.0,
}

# ═══════════════════════════════════════════════════════════════════════════════
# ALLERGÈNES EU (14 majeurs)
# ═══════════════════════════════════════════════════════════════════════════════

ALLERGEN_MAP: dict[str, str] = {
    # gluten
    "flour":"gluten","wheat":"gluten","rye":"gluten","barley":"gluten",
    "oat":"gluten","spelt":"gluten","semolina":"gluten","bread":"gluten",
    "pasta":"gluten","couscous":"gluten","bulgur":"gluten","seitan":"gluten",
    "soy_sauce":"gluten","breadcrumbs":"gluten","pita":"gluten",
    # lactose
    "milk":"lactose","cream":"lactose","butter":"lactose","cheese":"lactose",
    "yogurt":"lactose","parmesan":"lactose","mozzarella":"lactose",
    "ricotta":"lactose","mascarpone":"lactose","feta":"lactose",
    "halloumi":"lactose","ghee":"lactose","cheddar":"lactose",
    "goat_cheese":"lactose","cream_cheese":"lactose","sour_cream":"lactose",
    # eggs
    "egg":"eggs","mayonnaise":"eggs",
    # soy
    "soy":"soy","tofu":"soy","tempeh":"soy","edamame":"soy","miso":"soy",
    "tamari":"soy","soy_milk":"soy",
    # tree nuts
    "walnut":"tree_nuts","hazelnut":"tree_nuts","almond":"tree_nuts",
    "cashew":"tree_nuts","pistachio":"tree_nuts","pecan":"tree_nuts",
    "macadamia":"tree_nuts","pine_nut":"tree_nuts","chestnut":"tree_nuts",
    # peanuts
    "peanut":"peanuts","peanut_butter":"peanuts",
    # sesame
    "sesame":"sesame","tahini":"sesame","sesame_oil":"sesame",
    # fish
    "salmon":"fish","tuna":"fish","cod":"fish","sardine":"fish",
    "anchovy":"fish","trout":"fish","fish_sauce":"fish",
    # crustaceans
    "shrimp":"crustaceans","prawn":"crustaceans","lobster":"crustaceans",
    "crab":"crustaceans","langoustine":"crustaceans",
    # molluscs
    "mussel":"molluscs","oyster":"molluscs","squid":"molluscs",
    "octopus":"molluscs","clam":"molluscs",
    # celery
    "celery":"celery","celeriac":"celery",
    # mustard
    "mustard":"mustard","mustard_seed":"mustard",
    # sulphites
    "wine":"sulphites","vinegar":"sulphites","dried_fruit":"sulphites",
    # lupin
    "lupin":"lupin","lupin_flour":"lupin",
}

# ═══════════════════════════════════════════════════════════════════════════════
# CATÉGORIES DE PLATS
# ═══════════════════════════════════════════════════════════════════════════════

DISH_TYPE_KEYWORDS: dict[str, list[str]] = {
    "soup":       ["soup","soupe","potage","velouté","bouillon","bisque","chowder"],
    "salad":      ["salad","salade","taboulé","coleslaw"],
    "curry":      ["curry","korma","tikka","masala","dahl","dal","dhal"],
    "stew":       ["stew","ragoût","cassoulet","tajine","tagine","daube"],
    "pasta":      ["pasta","spaghetti","penne","tagliatelle","gnocchi","lasagne","risotto"],
    "rice":       ["rice","riz","pilaf","biryani","paella","bibimbap","fried rice"],
    "sandwich":   ["sandwich","burger","wrap","taco","burrito","falafel"],
    "dip":        ["hummus","dip","guacamole","baba","tzatziki","raita"],
    "dessert":    ["cake","tart","mousse","crème","pudding","brownie","cookie","glace"],
    "breakfast":  ["pancake","waffle","granola","porridge","muesli","omelette"],
    "stir_fry":   ["stir fry","stir-fry","wok","sauté"],
    "pizza":      ["pizza","flatbread","focaccia","pissaladière"],
    "pie":        ["pie","quiche","galette","tarte","empanada"],
    "bowl":       ["bowl","poke","açaí","buddha"],
    "roast":      ["roast","gratin","bake","baked","gratin"],
}

# Cuisines reconnues
CUISINE_KEYWORDS: dict[str, list[str]] = {
    "indian":     ["indian","inde","masala","tikka","biryani","dhal","samosa"],
    "italian":    ["italian","italie","pasta","risotto","pizza","pesto","carbonara"],
    "mexican":    ["mexican","mexique","taco","burrito","guacamole","enchilada"],
    "chinese":    ["chinese","chine","wok","dim sum","mapo","kung pao","fried rice"],
    "japanese":   ["japanese","japon","sushi","ramen","miso","udon","tempura"],
    "thai":       ["thai","thaï","pad thai","green curry","som tam","tom yum"],
    "french":     ["french","français","ratatouille","bouillabaisse","gratin","crêpe"],
    "levantine":  ["levantine","levant","hummus","falafel","baba","taboulé","shawarma"],
    "moroccan":   ["moroccan","maroc","tagine","couscous","harira","chermoula"],
    "korean":     ["korean","coréen","bibimbap","kimchi","bulgogi","gochujang"],
    "mediterranean":["mediterranean","méditerranée","mezze","dolma","spanakopita"],
    "american":   ["american","américain","burger","bbq","chili","mac and cheese"],
}
