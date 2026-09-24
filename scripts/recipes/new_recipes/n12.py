"""Lot 12 : Caraïbes, océan Indien et suite de l'Afrique (22 recettes).

Deux zones presque absentes du dataset : les Caraïbes (5 plats avant ce lot) et l'océan Indien
hors Sri Lanka (aucun). Complété par le Maghreb hors couscous et l'Afrique australe.
"""
from ._schema import recipe

RECIPES = [
    recipe(
        rid="side_coucou_barbadien_6f31a8",
        fr="Cou-cou barbadien, semoule de maïs aux gombos",
        en="Barbadian Cou-Cou, Cornmeal with Okra",
        original="Cou-cou",
        cuisine="barbadian", country="barbados", region="bridgetown",
        dish="side", prep=15, cook=35,
        texture=("épais", "lisse"), taste=("doux", "beurré"),
        technique=("simmer",), difficulty="medium",
        desc="Plat national de la Barbade : de la semoule de maïs travaillée à la spatule dans une "
             "eau de cuisson de gombos, ce qui la rend soyeuse, puis moulée en dôme et arrosée de "
             "beurre fondu.",
        compo=[
            ("cornmeal_whole_dried", 200, "g", "base"),
            ("okra", 250, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 900, "ml", "liquid"),
        ],
        steps=[
            "Couper 250 g de gombos en rondelles et les cuire 12 minutes dans 900 ml d'eau salée "
            "(4 g de sel) avec 100 g d'oignon émincé et 3 g de thym.",
            "Prélever 300 ml de cette eau de cuisson et la réserver au chaud.",
            "Verser 200 g de semoule de maïs en pluie dans la casserole en remuant énergiquement "
            "pour éviter les grumeaux.",
            "Travailler la semoule 15 minutes à la spatule en ajoutant l'eau réservée par petites "
            "quantités : elle devient lisse et se détache des parois.",
            "Assaisonner de 2 g de poivre, puis tasser la préparation dans un bol humidifié.",
            "Démouler en dôme sur le plat, arroser de 40 g de beurre fondu et servir aussitôt.",
        ],
    ),
    recipe(
        rid="main_jerk_tofu_a91e26",
        fr="Jerk tofu, tofu grillé à la marinade jamaïcaine",
        en="Jerk Tofu, Grilled Tofu with Jamaican Jerk Marinade",
        original="Jerk tofu",
        cuisine="jamaican", country="jamaica", region="portland",
        dish="main", prep=20, rest=120, cook=25,
        texture=("ferme", "caramélisé"), taste=("piquant", "fumé"),
        technique=("marinate", "grill"), spice=4, kid_friendly=False,
        desc="Tofu pressé mariné deux heures dans une pâte jerk — piment, oignon vert, thym, "
             "piment de la Jamaïque et gingembre — puis grillé jusqu'à ce que les arêtes "
             "caramélisent, servi avec du riz.",
        compo=[
            ("tofu_plain_pre_packaged", 600, "g", "plant_protein"),
            ("green_onion_raw", 100, "g", "aromatic"),
            ("red_hot_chili_pepper_raw", 20, "g", "spice"),
            ("ginger_raw_root_fresh", 20, "g", "aromatic"),
            ("garlic_raw", 15, "g", "aromatic"),
            ("thyme_fresh_herb", 6, "g", "herb"),
            ("allspice_powder", 5, "g", "spice"),
            ("soy_sauce_tamari", 40, "ml", "condiment"),
            ("brown_sugar", 20, "g", "balance"),
            ("lime_raw_juice_fresh", 40, "ml", "acidity"),
            ("sunflower_oil_plant", 40, "ml", "fat_cooking"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("white_rice_long_grain_seed_dried", 200, "g", "base", "dried"),
        ],
        steps=[
            "Presser 600 g de tofu 20 minutes sous un poids, puis le couper en tranches épaisses "
            "de 2 cm.",
            "Mixer 100 g d'oignon vert, 20 g de piment, 20 g de gingembre, 15 g d'ail, 6 g de "
            "thym, 5 g de piment de la Jamaïque, 40 ml de tamari, 20 g de sucre roux, 40 ml de jus "
            "de citron vert et 2 g de poivre.",
            "Enrober le tofu de marinade et laisser 2 heures au frais, en retournant à mi-temps.",
            "Cuire 200 g de riz long à l'eau salée pendant ce temps.",
            "Chauffer 40 ml d'huile dans une poêle-gril et saisir le tofu 6 minutes par face, en "
            "badigeonnant du reste de marinade.",
            "Laisser réduire la marinade 4 minutes dans la poêle et en napper le tofu, servir avec "
            "le riz.",
        ],
    ),
    recipe(
        rid="snack_festival_jamaicain_c3f705",
        fr="Festival, beignets de maïs jamaïcains",
        en="Festival, Jamaican Cornmeal Dumplings",
        original="Festival",
        cuisine="jamaican", country="jamaica", region="kingston",
        dish="snack", servings=6, prep=15, rest=20, cook=15,
        texture=("croustillant", "moelleux"), taste=("sucré", "salé"),
        technique=("fry",),
        desc="Petits pains frits de la côte jamaïcaine : pâte de semoule de maïs légèrement sucrée, "
             "roulée en boudins et frite jusqu'à l'or, croustillante dehors et dense dedans.",
        compo=[
            ("cornmeal_whole_dried", 150, "g", "base"),
            ("wheat_flour_t55", 150, "g", "base"),
            ("sugars_granulated", 30, "g", "sweetener"),
            ("baking_powder", 8, "g", "ingredient"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("water", 150, "ml", "liquid"),
            ("sunflower_oil_plant", 60, "ml", "fat_cooking"),
        ],
        steps=[
            "Mélanger 150 g de semoule de maïs, 150 g de farine, 30 g de sucre, 8 g de poudre à "
            "lever et 3 g de sel.",
            "Ajouter 150 ml d'eau peu à peu et pétrir jusqu'à obtenir une pâte ferme et non "
            "collante.",
            "Laisser reposer 20 minutes sous un linge.",
            "Diviser en douze et rouler chaque part en boudin de 8 cm.",
            "Chauffer 60 ml d'huile dans une sauteuse et frire les festivals 7 minutes en les "
            "retournant, jusqu'à une couleur dorée uniforme.",
            "Égoutter sur papier absorbant et servir chaud avec un plat relevé.",
        ],
    ),
    recipe(
        rid="snack_accras_legumes_7e2b58",
        fr="Accras de légumes antillais",
        en="Antillean Vegetable Fritters",
        original="Accras",
        cuisine="caribbean", country="guadeloupe", region="basse_terre",
        dish="snack", prep=20, rest=30, cook=15,
        texture=("croustillant", "aérien"), taste=("salé", "herbacé"),
        technique=("fry",), spice=2,
        desc="Beignets antillais sans morue : une pâte à la farine et aux pois chiches, très "
             "parfumée d'oignon vert, persil et piment, frite en petites boules qui gonflent et "
             "restent creuses.",
        compo=[
            ("wheat_flour_t55", 150, "g", "base"),
            ("chickpea_flour", 50, "g", "plant_protein"),
            ("green_onion_raw", 80, "g", "aromatic"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("red_hot_chili_pepper_raw", 8, "g", "spice"),
            ("baking_powder", 5, "g", "ingredient"),
            ("lime_raw_juice_fresh", 20, "ml", "acidity"),
            ("sunflower_oil_plant", 80, "ml", "fat_cooking"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("water", 180, "ml", "liquid"),
        ],
        steps=[
            "Mélanger 150 g de farine, 50 g de farine de pois chiches, 5 g de poudre à lever et 4 g "
            "de sel.",
            "Ajouter 180 ml d'eau en fouettant pour obtenir une pâte épaisse et lisse.",
            "Incorporer 80 g d'oignon vert, 15 g de persil, 10 g d'ail et 8 g de piment hachés très "
            "fin, ainsi que 20 ml de jus de citron vert.",
            "Laisser reposer 30 minutes : la pâte se détend et commence à bulier.",
            "Chauffer 80 ml d'huile et y déposer des cuillerées à café de pâte, six à la fois.",
            "Frire 3 minutes en retournant : les accras doivent gonfler et dorer ; égoutter et "
            "servir aussitôt.",
        ],
    ),
    recipe(
        rid="main_colombo_legumes_58a0e1",
        fr="Colombo de légumes, curry guadeloupéen",
        en="Vegetable Colombo, Guadeloupean Curry",
        original="Colombo",
        cuisine="caribbean", country="guadeloupe", region="grande_terre",
        dish="main", prep=25, cook=40,
        texture=("fondant",), taste=("épicé", "acide"),
        technique=("simmer",), spice=2,
        desc="Curry créole des Antilles : christophine, courge et pomme de terre mijotées dans un "
             "lait de coco au colombo — mélange d'épices proche du massalé — acidulé au tamarin, "
             "servi avec du riz.",
        compo=[
            ("chayote_raw", 300, "g", "vegetable"),
            ("butternut_squash_raw_skinless", 300, "g", "vegetable"),
            ("potato_raw_flesh", 300, "g", "vegetable"),
            ("eggplant_raw", 200, "g", "vegetable"),
            ("coconut_milk_plant", 200, "ml", "dairy_alt"),
            ("curry_powder", 15, "g", "spice"),
            ("turmeric_powder", 3, "g", "spice"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("tamarind_paste", 20, "g", "acidity"),
            ("sunflower_oil_plant", 40, "ml", "fat_cooking"),
            ("white_rice_long_grain_seed_dried", 200, "g", "base", "dried"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 500, "ml", "liquid"),
        ],
        steps=[
            "Faire revenir 150 g d'oignon et 12 g d'ail dans 40 ml d'huile, 6 minutes, puis ajouter "
            "15 g de colombo (curry) et 3 g de curcuma et remuer 1 minute.",
            "Ajouter 300 g de christophine, 300 g de courge, 300 g de pomme de terre et 200 g "
            "d'aubergine en cubes de 2 cm, enrober d'épices.",
            "Verser 500 ml d'eau et 4 g de sel, couvrir et mijoter 25 minutes.",
            "Délayer 20 g de pâte de tamarin dans un peu de bouillon et l'ajouter au plat.",
            "Verser 200 ml de lait de coco et poursuivre 10 minutes à découvert, jusqu'à ce que la "
            "sauce nappe les légumes.",
            "Cuire 200 g de riz à l'eau salée (1 g de sel) et servir le colombo dessus.",
        ],
    ),
    recipe(
        rid="condiment_pikliz_2f47c9",
        fr="Pikliz, condiment haïtien de chou au piment",
        en="Pikliz, Haitian Spicy Pickled Cabbage",
        original="Pikliz",
        cuisine="haitian", country="haiti", region="port_au_prince",
        dish="condiment", servings=8, prep=20, rest=2880,
        texture=("croquant",), taste=("piquant", "acide"),
        spice=5, kid_friendly=False,
        desc="Condiment haïtien indispensable : chou, carotte et oignon crus tranchés très fin, "
             "noyés de vinaigre avec beaucoup de piment, qui macèrent deux jours et accompagnent "
             "tous les plats frits.",
        compo=[
            ("cabbage_raw", 400, "g", "vegetable"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic"),
            ("red_hot_chili_pepper_raw", 40, "g", "spice"),
            ("cider_vinegar_liquid", 400, "ml", "acidity"),
            ("lime_raw_juice_fresh", 30, "ml", "acidity"),
            ("cloves", 1, "g", "spice"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
        ],
        steps=[
            "Trancher 400 g de chou en lanières très fines, râper 150 g de carotte et émincer 100 g "
            "d'oignon.",
            "Couper 40 g de piments en rondelles, avec les graines pour la force.",
            "Mélanger tous les légumes avec 6 g de sel, 2 g de poivre et 1 g de clou de girofle "
            "écrasé.",
            "Tasser dans un bocal propre et couvrir de 400 ml de vinaigre de cidre et 30 ml de jus "
            "de citron vert.",
            "Fermer et laisser macérer 48 heures à température ambiante, en secouant une fois.",
            "Conserver ensuite au frais : le pikliz se garde plusieurs semaines et gagne en force.",
        ],
        raw=True,
    ),
    recipe(
        rid="main_doubles_trinidad_e60b34",
        fr="Doubles trinidadiens, bara et pois chiches au curry",
        en="Trinidadian Doubles, Fried Flatbread with Curried Chickpeas",
        original="Doubles",
        cuisine="trinidadian", country="trinidad_and_tobago", region="chaguanas",
        dish="main", prep=30, rest=750, cook=80,
        texture=("moelleux", "fondant"), taste=("épicé", "umami"),
        technique=("fry", "simmer"), difficulty="medium", spice=3, kid_friendly=False,
        desc="Le sandwich de rue de Trinité : deux petites galettes frites au curcuma, souples "
             "comme des crêpes, refermées sur des pois chiches mijotés au curry et relevés de "
             "piment.",
        compo=[
            ("chickpea_raw_dried", 200, "g", "plant_protein", "dried"),
            ("wheat_flour_t55", 250, "g", "base"),
            ("bakers_yeast_dehydrated", 5, "g", "ferment"),
            ("turmeric_powder", 5, "g", "spice"),
            ("curry_powder", 12, "g", "spice"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("red_hot_chili_pepper_raw", 10, "g", "spice"),
            ("sunflower_oil_plant", 70, "ml", "fat_cooking"),
            ("coriander", 15, "g", "herb"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
            ("water", 1200, "ml", "liquid"),
        ],
        steps=[
            "Faire tremper 200 g de pois chiches 12 heures, puis les cuire 60 minutes dans 1 L "
            "d'eau jusqu'à ce qu'ils s'écrasent facilement.",
            "Pétrir 250 g de farine, 5 g de levure, 3 g de curcuma, 3 g de sel et 150 ml d'eau "
            "tiède, puis laisser lever 90 minutes.",
            "Faire revenir 100 g d'oignon, 12 g d'ail et 15 g de gingembre dans 20 ml d'huile, "
            "puis ajouter 12 g de curry et 10 g de piment haché.",
            "Verser les pois chiches avec un peu de leur eau, 3 g de sel, et écraser un quart "
            "d'entre eux pour épaissir ; mijoter 15 minutes.",
            "Diviser la pâte en huit, étaler en disques de 12 cm et les frire 40 secondes par face "
            "dans le reste d'huile : les bara doivent rester souples.",
            "Garnir chaque bara de pois chiches, parsemer de 15 g de coriandre et refermer avec un "
            "second bara.",
        ],
    ),
    recipe(
        rid="dessert_blanc_manger_coco_b17e62",
        fr="Blanc-manger coco antillais",
        en="Antillean Coconut Blancmange",
        original="Blanc-manger coco",
        cuisine="caribbean", country="martinique", region="fort_de_france",
        dish="dessert", prep=15, rest=240, cook=10,
        texture=("tremblotant", "crémeux"), taste=("sucré", "lacté"),
        technique=("simmer",),
        desc="Entremets martiniquais très parfumé : lait de coco sucré pris à la fécule avec un "
             "zeste de citron vert et de la cannelle, démoulé en dôme brillant et servi glacé.",
        compo=[
            ("coconut_milk_plant", 500, "ml", "dairy_alt"),
            ("milk_liquid_pasteurized_3_5pct", 250, "ml", "dairy"),
            ("sugars_granulated", 80, "g", "sweetener"),
            ("cornstarch_flour", 50, "g", "thickener"),
            ("cinnamon", 2, "g", "spice"),
            ("lemon_peel_raw", 5, "g", "aroma"),
            ("coconut_flesh_dried", 20, "g", "garnish"),
        ],
        steps=[
            "Délayer 50 g de fécule de maïs dans 100 ml de lait froid.",
            "Chauffer 500 ml de lait de coco avec le reste du lait, 80 g de sucre, 2 g de cannelle "
            "et 5 g de zeste de citron vert, jusqu'aux premiers frémissements.",
            "Verser la fécule en fouettant et cuire 4 minutes : la crème doit être épaisse et "
            "brillante.",
            "Retirer le zeste et verser dans un moule humidifié.",
            "Réfrigérer 4 heures jusqu'à prise complète.",
            "Démouler sur un plat froid et parsemer de 20 g de coco râpée grillée.",
        ],
    ),
    recipe(
        rid="beverage_sorrel_hibiscus_39d5a7",
        fr="Sorrel, boisson jamaïcaine à l'hibiscus et au gingembre",
        en="Sorrel, Jamaican Hibiscus and Ginger Drink",
        original="Sorrel drink",
        cuisine="jamaican", country="jamaica", region="saint_andrew",
        dish="beverage", prep=10, rest=720, cook=10, meal="beverage",
        texture=("liquide",), taste=("acide", "épicé"),
        technique=("infuse",),
        desc="Boisson de Noël jamaïcaine d'un rouge profond : calices d'hibiscus infusés avec "
             "gingembre, clou de girofle et badiane, sucrés et laissés macérer une nuit avant "
             "d'être servis sur glace.",
        compo=[
            ("roselle_raw", 60, "g", "aroma"),
            ("ginger_raw_root_fresh", 20, "g", "aromatic"),
            ("cloves", 1, "g", "spice"),
            ("star_anise", 1, "g", "spice"),
            ("sugars_granulated", 80, "g", "sweetener"),
            ("lime_raw_juice_fresh", 30, "ml", "acidity"),
            ("water", 1200, "ml", "liquid"),
        ],
        steps=[
            "Porter 1,2 L d'eau à ébullition avec 20 g de gingembre en lamelles, 1 g de clou de "
            "girofle et 1 g de badiane.",
            "Hors du feu, ajouter 60 g de calices d'hibiscus séchés et couvrir.",
            "Laisser infuser 12 heures à température ambiante : la couleur devient rouge sombre.",
            "Filtrer en pressant les calices, puis dissoudre 80 g de sucre dans l'infusion.",
            "Ajouter 30 ml de jus de citron vert et goûter : la boisson doit rester franchement "
            "acide.",
            "Servir très frais sur glace.",
        ],
    ),
    recipe(
        rid="condiment_rougail_aubergine_84c103",
        fr="Rougail aubergine réunionnais",
        en="Réunion Eggplant Rougail",
        original="Rougail aubergine",
        cuisine="reunionese", country="france", region="la_reunion",
        dish="condiment", servings=6, prep=15, cook=25,
        texture=("fondant", "écrasé"), taste=("piquant", "acide"),
        technique=("fry",), spice=4, kid_friendly=False,
        desc="Écrasé d'aubergines réunionnais servi en petite quantité à côté du riz : aubergines "
             "revenues puis écrasées avec gingembre, piment et citron vert, très relevé.",
        compo=[
            ("eggplant_raw", 400, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("tomato_raw_ripe", 150, "g", "vegetable"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("red_hot_chili_pepper_raw", 15, "g", "spice"),
            ("turmeric_powder", 3, "g", "spice"),
            ("sunflower_oil_plant", 40, "ml", "fat_cooking"),
            ("lime_raw_juice_fresh", 20, "ml", "acidity"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Couper 400 g d'aubergines en dés de 2 cm et les faire revenir 10 minutes dans 40 ml "
            "d'huile jusqu'à ce qu'ils soient dorés et fondants.",
            "Ajouter 100 g d'oignon émincé, 15 g de gingembre râpé et 3 g de curcuma, cuire "
            "5 minutes.",
            "Incorporer 150 g de tomates concassées et 4 g de sel, puis laisser réduire "
            "10 minutes.",
            "Écraser 15 g de piment au mortier et l'ajouter hors du feu.",
            "Écraser grossièrement l'ensemble à la fourchette : le rougail doit rester rustique.",
            "Ajouter 20 ml de jus de citron vert et servir tiède à côté du riz.",
        ],
    ),
    recipe(
        rid="side_gratin_chouchou_7a4f91",
        fr="Gratin de chouchou réunionnais",
        en="Réunion Chayote Gratin",
        original="Gratin de chouchou",
        cuisine="reunionese", country="france", region="la_reunion",
        dish="side", prep=20, cook=40,
        texture=("fondant", "gratiné"), taste=("doux", "lacté"),
        technique=("boil", "gratinate"),
        desc="Gratin des Hauts de La Réunion : la christophine, blanchie puis liée à une béchamel "
             "muscadée et gratinée avec du fromage et de la chapelure, garde une texture très "
             "douce et légèrement croquante.",
        compo=[
            ("chayote_raw", 800, "g", "vegetable"),
            ("milk_liquid_pasteurized_3_5pct", 300, "ml", "dairy"),
            ("wheat_flour_t55", 30, "g", "thickener"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("emmental_de_savoie_cow", 80, "g", "dairy"),
            ("breadcrumbs_dried", 30, "g", "garnish"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("nutmeg", 1, "g", "spice"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 1000, "ml", "liquid"),
        ],
        steps=[
            "Peler 800 g de chouchous sous l'eau (ils collent aux doigts), les couper en deux et "
            "retirer le noyau.",
            "Les cuire 12 minutes dans 1 L d'eau salée (2 g de sel), puis les égoutter et les "
            "presser pour retirer l'eau.",
            "Faire un roux avec 40 g de beurre et 30 g de farine, verser 300 ml de lait chaud en "
            "fouettant et cuire 5 minutes.",
            "Assaisonner la béchamel de 8 g d'ail écrasé, 1 g de muscade, 2 g de sel et 2 g de "
            "poivre.",
            "Écraser les chouchous à la fourchette, les mélanger à la béchamel et verser dans un "
            "plat beurré.",
            "Couvrir de 80 g d'emmental râpé et 30 g de chapelure, puis enfourner 25 minutes à "
            "200 °C jusqu'à ce que le gratin soit doré.",
        ],
    ),
    recipe(
        rid="condiment_achards_legumes_1c5d84",
        fr="Achards de légumes mauriciens",
        en="Mauritian Vegetable Achards",
        original="Achard de légumes",
        cuisine="mauritian", country="mauritius", region="port_louis",
        dish="condiment", servings=8, prep=25, rest=120, cook=15,
        texture=("croquant",), taste=("acide", "épicé"),
        technique=("fry",), spice=3, kid_friendly=False,
        desc="Légumes mauriciens blanchis puis enrobés d'une huile parfumée au curcuma, à la "
             "moutarde et au gingembre, vinaigrés : ils restent croquants et se conservent au "
             "frais plusieurs jours.",
        compo=[
            ("carrot_raw", 200, "g", "vegetable"),
            ("french_bean_raw", 200, "g", "vegetable"),
            ("cabbage_raw", 200, "g", "vegetable"),
            ("cauliflower_raw_flower", 150, "g", "vegetable"),
            ("mustard", 15, "g", "condiment"),
            ("turmeric_powder", 5, "g", "spice"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("red_hot_chili_pepper_raw", 10, "g", "spice"),
            ("sunflower_oil_plant", 60, "ml", "fat_cooking"),
            ("cider_vinegar_liquid", 60, "ml", "acidity"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
            ("water", 1000, "ml", "liquid"),
        ],
        steps=[
            "Couper 200 g de carotte en bâtonnets, 200 g de haricots verts en tronçons, 200 g de "
            "chou en lanières et 150 g de chou-fleur en petits bouquets.",
            "Blanchir les légumes 2 minutes dans 1 L d'eau bouillante salée (3 g de sel), puis les "
            "refroidir à l'eau glacée et les égoutter à fond.",
            "Chauffer 60 ml d'huile et y faire revenir 15 g de gingembre, 12 g d'ail, 10 g de "
            "piment et 5 g de curcuma, 3 minutes.",
            "Ajouter 15 g de moutarde et 60 ml de vinaigre de cidre, laisser tiédir.",
            "Mélanger les légumes à cette huile parfumée avec 3 g de sel.",
            "Laisser mariner 2 heures avant de servir, en remuant une fois.",
        ],
    ),
    recipe(
        rid="snack_dholl_puri_0e6b47",
        fr="Dholl puri, galettes mauriciennes fourrées aux pois cassés",
        en="Dholl Puri, Mauritian Split Pea Flatbread",
        original="Dholl puri",
        cuisine="mauritian", country="mauritius", region="port_louis",
        dish="snack", servings=6, prep=35, rest=60, cook=25,
        texture=("souple", "moelleux"), taste=("épicé", "céréalier"),
        technique=("steam", "griddle"), difficulty="hard",
        desc="Spécialité de rue mauricienne : des galettes très souples fourrées d'une poudre de "
             "pois cassés cuits au curcuma et au cumin, cuites à sec sur une plaque et servies "
             "roulées avec un curry.",
        compo=[
            ("wheat_flour_t55", 300, "g", "base"),
            ("split_peas_dried", 150, "g", "plant_protein", "dried"),
            ("turmeric_powder", 4, "g", "spice"),
            ("cumin_spice_seed", 4, "g", "spice"),
            ("sunflower_oil_plant", 50, "ml", "fat_cooking"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 700, "ml", "liquid"),
        ],
        steps=[
            "Rincer 150 g de pois cassés et les cuire 30 minutes dans 500 ml d'eau avec 4 g de "
            "curcuma, jusqu'à ce qu'ils soient tendres mais entiers.",
            "Les égoutter, les sécher 5 minutes à la poêle et les réduire en poudre grossière avec "
            "4 g de cumin grillé et 2 g de sel.",
            "Pétrir 300 g de farine, 200 ml d'eau, 20 ml d'huile et 3 g de sel, puis laisser "
            "reposer 60 minutes.",
            "Diviser en douze boules, les creuser et les farcir d'une cuillerée de poudre de pois "
            "cassés, puis refermer.",
            "Abaisser délicatement chaque boule en galette de 18 cm sans faire sortir la farce.",
            "Cuire 1 minute par face sur une plaque chaude légèrement huilée : les galettes "
            "gonflent et se tachent de brun ; les empiler sous un linge.",
        ],
    ),
    recipe(
        rid="noodle_mine_frite_5d9c02",
        fr="Mine frite, nouilles sautées mauriciennes",
        en="Mine Frite, Mauritian Stir-Fried Noodles",
        original="Mine frite",
        cuisine="mauritian", country="mauritius", region="curepipe",
        dish="main", prep=20, cook=15,
        texture=("souple", "croquant"), taste=("umami", "salé"),
        technique=("stir_fry",), allow_similar=("frite",),
        desc="Nouilles sautées à la mauricienne, héritage sino-mauricien : nouilles saisies au wok "
             "avec chou, carotte et tofu fumé, sauce soja et beaucoup d'oignon vert ajouté hors du "
             "feu.",
        compo=[
            ("egg_pasta_raw_dried", 300, "g", "base", "dried"),
            ("cabbage_raw", 200, "g", "vegetable"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("green_onion_raw", 100, "g", "aromatic"),
            ("tofu_smoked_pre_packaged", 200, "g", "plant_protein"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("soy_sauce_tamari", 40, "ml", "condiment"),
            ("sunflower_oil_plant", 40, "ml", "fat_cooking"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 2000, "ml", "liquid"),
        ],
        steps=[
            "Cuire 300 g de nouilles 6 minutes dans 2 L d'eau, les rincer à l'eau froide et les "
            "égoutter à fond pour qu'elles ne collent pas.",
            "Couper 200 g de tofu fumé en bâtonnets et le saisir 4 minutes dans 20 ml d'huile, "
            "puis le réserver.",
            "Faire sauter 12 g d'ail et 15 g de gingembre dans le reste d'huile, 30 secondes à feu "
            "vif.",
            "Ajouter 200 g de chou en lanières et 150 g de carotte en julienne, sauter 3 minutes en "
            "gardant du croquant.",
            "Ajouter les nouilles, le tofu, 40 ml de tamari et 2 g de poivre, sauter 3 minutes en "
            "décollant du fond.",
            "Hors du feu, mélanger 100 g d'oignon vert ciselé et servir aussitôt.",
        ],
    ),
    recipe(
        rid="main_romazava_bredes_d40a75",
        fr="Romazava de brèdes et tofu, ragoût malgache aux feuilles",
        en="Romazava with Greens and Tofu, Malagasy Leaf Stew",
        original="Romazava",
        cuisine="malagasy", country="madagascar", region="antananarivo",
        dish="main", prep=20, cook=35,
        texture=("fondant", "bouillon"), taste=("herbacé", "umami"),
        technique=("simmer",),
        desc="Plat national malgache en version végétarienne : un bouillon de brèdes — épinards et "
             "feuilles de moutarde — au gingembre et à la tomate, dans lequel mijotent des cubes de "
             "tofu, servi avec du riz blanc.",
        compo=[
            ("spinach", 400, "g", "vegetable"),
            ("mustard_raw_leaf", 200, "g", "vegetable"),
            ("tofu_plain_pre_packaged", 400, "g", "plant_protein"),
            ("tomato_raw_ripe", 200, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("ginger_raw_root_fresh", 20, "g", "aromatic"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("sunflower_oil_plant", 40, "ml", "fat_cooking"),
            ("lime_raw_juice_fresh", 20, "ml", "acidity"),
            ("white_rice_long_grain_seed_dried", 200, "g", "base", "dried"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 700, "ml", "liquid"),
        ],
        steps=[
            "Couper 400 g de tofu en cubes et les faire dorer 6 minutes dans 40 ml d'huile, puis "
            "les réserver.",
            "Faire revenir 150 g d'oignon, 20 g de gingembre râpé et 12 g d'ail dans la même "
            "sauteuse, 5 minutes.",
            "Ajouter 200 g de tomates concassées et cuire 5 minutes jusqu'à ce qu'elles se "
            "défassent.",
            "Verser 700 ml d'eau, 4 g de sel et 2 g de poivre, porter à frémissement, puis ajouter "
            "400 g d'épinards et 200 g de feuilles de moutarde ciselées.",
            "Remettre le tofu et mijoter 20 minutes à couvert : le bouillon doit être vert et "
            "parfumé.",
            "Cuire 200 g de riz à l'eau salée (1 g de sel), ajouter 20 ml de jus de citron vert au "
            "romazava et servir sur le riz.",
        ],
    ),
    recipe(
        rid="dessert_ladob_banane_9b6318",
        fr="Ladob, bananes plantain au lait de coco des Seychelles",
        en="Ladob, Seychellois Plantain in Coconut Milk",
        original="Ladob",
        cuisine="seychellois", country="seychelles", region="mahe",
        dish="dessert", prep=10, cook=25,
        texture=("fondant", "sirupeux"), taste=("sucré", "lacté"),
        technique=("simmer",),
        desc="Dessert seychellois d'une grande simplicité : des bananes plantain bien mûres pochées "
             "dans du lait de coco sucré à la vanille et à la muscade, jusqu'à ce que le sirop "
             "épaississe et nappe les fruits.",
        compo=[
            ("plantain_banana_raw_ripe", 600, "g", "fruit"),
            ("coconut_milk_plant", 400, "ml", "dairy_alt"),
            ("sugars_granulated", 40, "g", "sweetener"),
            ("vanilla_extract", 5, "ml", "aroma"),
            ("nutmeg", 1, "g", "spice"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ],
        steps=[
            "Peler 600 g de bananes plantain bien mûres et les couper en tronçons de 4 cm.",
            "Porter 400 ml de lait de coco à frémissement avec 40 g de sucre et 1 g de sel.",
            "Ajouter les plantains en une seule couche et pocher 20 minutes à feu doux, sans "
            "remuer.",
            "Ajouter 5 ml de vanille et 1 g de muscade râpée.",
            "Poursuivre 5 minutes à découvert : le lait de coco doit réduire en sirop nappant.",
            "Servir tiède ou froid, arrosé du sirop de cuisson.",
        ],
    ),
    recipe(
        rid="main_tajine_citron_confit_c082f4",
        fr="Tajine de légumes au citron confit et aux amandes",
        en="Vegetable Tagine with Preserved Lemon and Almonds",
        original="Tajine",
        cuisine="moroccan", country="morocco", region="fes",
        dish="main", prep=25, cook=55,
        texture=("fondant",), taste=("acide", "épicé"),
        technique=("simmer",),
        desc="Tajine marocain sans viande : carotte, courge et pomme de terre confites au ras "
             "el-hanout et au safran, relevées de citron confit émincé et parsemées d'amandes "
             "grillées.",
        compo=[
            ("carrot_raw", 250, "g", "vegetable"),
            ("butternut_squash_raw_skinless", 300, "g", "vegetable"),
            ("potato_raw_flesh", 250, "g", "vegetable"),
            ("chickpea_rinsed_canned", 200, "g", "plant_protein", "cooked"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("preserved_lemon", 40, "g", "condiment"),
            ("almond_raw_skinless_unsalted", 40, "g", "nut"),
            ("base_ras_el_hanout_7cd544", 10, "g", "spice"),
            ("saffron", 0.2, "g", "spice"),
            ("olive_oil_plant", 50, "ml", "fat_cooking"),
            ("coriander", 15, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("water", 400, "ml", "liquid"),
        ],
        allow_similar=("tajine", "confit"),
        steps=[
            "Faire revenir 150 g d'oignon émincé dans 40 ml d'huile d'olive au fond d'un tajine ou "
            "d'une cocotte, 8 minutes à feu doux.",
            "Ajouter 10 g de ras el-hanout et 0,2 g de safran infusé dans un peu d'eau chaude, "
            "remuer 1 minute.",
            "Ranger 250 g de carotte, 300 g de courge et 250 g de pomme de terre en quartiers en "
            "dôme sur l'oignon.",
            "Verser 400 ml d'eau et 4 g de sel, couvrir et laisser confire 40 minutes à feu doux "
            "sans remuer.",
            "Ajouter 200 g de pois chiches et 40 g de citron confit en lamelles, poursuivre "
            "10 minutes.",
            "Faire dorer 40 g d'amandes dans le reste d'huile, en parsemer le tajine avec 15 g de "
            "coriandre et servir dans le plat de cuisson.",
        ],
    ),
    recipe(
        rid="soup_chorba_frik_3b5d90",
        fr="Chorba frik algérienne au blé vert concassé",
        en="Algerian Chorba Frik with Green Wheat",
        original="Chorba frik",
        cuisine="algerian", country="algeria", region="alger",
        dish="soup", prep=20, cook=45,
        texture=("épais", "grenu"), taste=("umami", "herbacé"),
        technique=("simmer",),
        desc="Soupe du ramadan algérien : du frik — blé vert concassé au goût fumé — cuit dans un "
             "bouillon de tomate avec des pois chiches, parfumé à la cannelle et à la menthe "
             "séchée, épaissi par le grain.",
        compo=[
            ("freekeh_immature_wheat_raw_cracked_seed", 120, "g", "base", "dried"),
            ("chickpea_rinsed_canned", 150, "g", "plant_protein", "cooked"),
            ("tomato_raw_ripe", 300, "g", "vegetable"),
            ("tomato_paste_unsalted_canned", 30, "g", "condiment"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("leeks", 100, "g", "aromatic"),
            ("coriander", 15, "g", "herb"),
            ("spearmint_dried_herb", 3, "g", "herb"),
            ("cinnamon", 2, "g", "spice"),
            ("olive_oil_plant", 30, "ml", "fat_cooking"),
            ("vegetable_stock_dried", 6, "g", "seasoning"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 1500, "ml", "liquid"),
        ],
        steps=[
            "Faire revenir 150 g d'oignon râpé et 100 g de poireau émincé dans 30 ml d'huile "
            "d'olive, 6 minutes.",
            "Ajouter 30 g de concentré de tomate, 300 g de tomates râpées, 2 g de cannelle, 4 g de "
            "sel et 2 g de poivre, cuire 5 minutes.",
            "Verser 1,5 L d'eau et 6 g de bouillon de légumes, porter à ébullition.",
            "Rincer 120 g de frik et le verser en pluie, puis cuire 30 minutes à feu doux en "
            "remuant régulièrement pour éviter qu'il n'attache.",
            "Ajouter 150 g de pois chiches et 3 g de menthe séchée, poursuivre 8 minutes.",
            "Parsemer de 15 g de coriandre hachée et servir avec un quartier de citron.",
        ],
    ),
    recipe(
        rid="brkf_msemen_6e1a38",
        fr="Msemen, crêpes feuilletées marocaines",
        en="Msemen, Moroccan Layered Flatbread",
        original="Msemen",
        cuisine="moroccan", country="morocco", region="casablanca",
        dish="breakfast", servings=6, prep=30, rest=30, cook=25,
        texture=("feuilleté", "moelleux"), taste=("céréalier", "beurré"),
        technique=("griddle",), difficulty="medium",
        desc="Crêpes carrées du petit-déjeuner marocain : la pâte est étirée jusqu'à la "
             "transparence, huilée et saupoudrée de semoule avant d'être pliée en carré, ce qui "
             "donne des couches bien distinctes à la cuisson.",
        compo=[
            ("wheat_flour_t55", 300, "g", "base"),
            ("durum_wheat_semolina", 100, "g", "base"),
            ("sunflower_oil_plant", 60, "ml", "fat_cooking"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 250, "ml", "liquid"),
        ],
        steps=[
            "Pétrir 300 g de farine, 50 g de semoule fine, 5 g de sel et 250 ml d'eau tiède "
            "pendant 10 minutes : la pâte doit être très souple.",
            "Huiler la pâte, la diviser en six boules et laisser reposer 30 minutes sous un film.",
            "Étaler chaque boule à la main sur un plan huilé jusqu'à obtenir une feuille presque "
            "transparente.",
            "Badigeonner de beurre fondu et saupoudrer du reste de semoule, puis replier les quatre "
            "côtés pour former un carré.",
            "Cuire chaque msemen 4 minutes sur une plaque chaude légèrement huilée, en appuyant et "
            "en retournant deux fois.",
            "Servir chaud, avec du thé à la menthe et du miel ou de la confiture.",
        ],
    ),
    recipe(
        rid="snack_brik_oeuf_2a7e64",
        fr="Brik à l'œuf tunisienne aux pommes de terre",
        en="Tunisian Egg Brik with Potato",
        original="Brik à l'œuf",
        cuisine="tunisian", country="tunisia", region="tunis",
        dish="snack", prep=25, cook=20,
        texture=("croustillant", "coulant"), taste=("salé", "piquant"),
        technique=("fry",), spice=2, difficulty="medium",
        desc="Feuille de brick garnie de pommes de terre écrasées, câpres et persil, avec un œuf "
             "cassé au centre, frite une minute par face : le jaune doit rester coulant à "
             "l'ouverture.",
        compo=[
            ("phyllo_filo_pastry_raw_paste", 120, "g", "base"),
            ("potato_raw_flesh", 250, "g", "vegetable"),
            ("egg_raw", 200, "g", "animal_protein"),
            ("capers_canned_in_vinegar", 20, "g", "condiment"),
            ("parsley_fresh_herb", 20, "g", "herb"),
            ("base_harissa_ef842f", 15, "g", "condiment"),
            ("sunflower_oil_plant", 80, "ml", "fat_cooking"),
            ("lemon_juice", 20, "ml", "acidity"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Cuire 250 g de pommes de terre 20 minutes à l'eau salée, les égoutter et les écraser "
            "grossièrement.",
            "Mélanger la purée avec 20 g de câpres hachées, 20 g de persil, 15 g de harissa, 4 g de "
            "sel et 2 g de poivre.",
            "Poser une feuille de brick, déposer un quart de la garniture en couronne et casser un "
            "œuf (50 g) au centre.",
            "Replier la feuille en demi-lune en soudant bien les bords avec un peu d'eau.",
            "Chauffer 80 ml d'huile et frire chaque brik 1 minute par face, en arrosant le dessus à "
            "la cuillère.",
            "Égoutter et servir aussitôt avec 20 ml de jus de citron, avant que le jaune ne "
            "prenne.",
        ],
    ),
    recipe(
        rid="main_yassa_legumes_b74c2e",
        fr="Yassa de légumes, oignons confits au citron du Sénégal",
        en="Vegetable Yassa, Senegalese Lemon Onion Stew",
        original="Yassa",
        cuisine="senegalese", country="senegal", region="casamance",
        dish="main", prep=25, rest=60, cook=45,
        texture=("fondant",), taste=("acide", "umami"),
        technique=("marinate", "simmer"), spice=2,
        desc="Plat casamançais dont la sauce est faite d'une montagne d'oignons confits, marinés au "
             "citron et à la moutarde : ils fondent en une compotée acide servie sur du riz, avec "
             "des pois chiches et des olives.",
        compo=[
            ("onion_raw", 800, "g", "aromatic_base"),
            ("lime_raw_juice_fresh", 80, "ml", "acidity"),
            ("mustard", 20, "g", "condiment"),
            ("carrot_raw", 200, "g", "vegetable"),
            ("chickpea_rinsed_canned", 250, "g", "plant_protein", "cooked"),
            ("black_olive_canned_in_brine", 40, "g", "condiment"),
            ("red_hot_chili_pepper_raw", 8, "g", "spice"),
            ("bay_leaf", 1, "g", "spice"),
            ("sunflower_oil_plant", 50, "ml", "fat_cooking"),
            ("white_rice_long_grain_seed_dried", 250, "g", "base", "dried"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 700, "ml", "liquid"),
        ],
        steps=[
            "Émincer 800 g d'oignons en fines lamelles et les mélanger avec 80 ml de jus de citron "
            "vert, 20 g de moutarde, 4 g de sel et 2 g de poivre.",
            "Laisser mariner 60 minutes à température ambiante, le temps que les oignons rendent "
            "leur eau.",
            "Égoutter les oignons en gardant la marinade, puis les faire suer 20 minutes dans 50 ml "
            "d'huile à feu moyen, sans les laisser brunir.",
            "Ajouter 200 g de carotte en rondelles, la marinade réservée, 400 ml d'eau, 1 g de "
            "laurier et le piment entier (8 g).",
            "Mijoter 20 minutes : la sauce doit être compotée et franchement acide.",
            "Ajouter 250 g de pois chiches et 40 g d'olives noires, réchauffer 5 minutes et retirer "
            "le piment.",
            "Cuire 250 g de riz dans 300 ml d'eau complétée à hauteur avec 1 g de sel, et servir le "
            "yassa dessus.",
        ],
    ),
    recipe(
        rid="main_bobotie_vegetarien_e5b742",
        fr="Bobotie végétarien, gratin sud-africain aux lentilles",
        en="Vegetarian Bobotie, South African Lentil Bake",
        original="Bobotie",
        cuisine="south_african", country="south_africa", region="le_cap",
        dish="main", prep=25, cook=50,
        texture=("fondant", "gratiné"), taste=("épicé", "sucré"),
        technique=("bake",),
        desc="Gratin du Cap en version végétarienne : des lentilles au curry avec pomme râpée et "
             "cranberries, couvertes d'un appareil au lait et à l'œuf qui prend au four en une "
             "couche jaune pâle, parfumé au laurier.",
        compo=[
            ("green_lentil_dried", 250, "g", "plant_protein", "dried"),
            ("onion_raw", 200, "g", "aromatic_base"),
            ("curry_powder", 12, "g", "spice"),
            ("turmeric_powder", 3, "g", "spice"),
            ("apple_raw", 150, "g", "fruit"),
            ("cranberry_dried_sweetened", 40, "g", "fruit"),
            ("bread_white_commercial", 80, "g", "base"),
            ("milk_liquid_pasteurized_3_5pct", 250, "ml", "dairy"),
            ("egg_raw", 100, "g", "binder"),
            ("bay_leaf", 2, "g", "spice"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("cider_vinegar_liquid", 20, "ml", "acidity"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 700, "ml", "liquid"),
        ],
        steps=[
            "Cuire 250 g de lentilles vertes 25 minutes dans 700 ml d'eau, puis les égoutter en "
            "gardant un peu de jus.",
            "Faire revenir 200 g d'oignon dans 30 ml d'huile, 8 minutes, puis ajouter 12 g de curry "
            "et 3 g de curcuma.",
            "Faire tremper 80 g de pain dans 100 ml de lait, l'essorer et l'émietter dans la poêle.",
            "Mélanger les lentilles, 150 g de pomme râpée, 40 g de cranberries, 20 ml de vinaigre "
            "de cidre, 4 g de sel et 2 g de poivre, puis verser dans un plat beurré.",
            "Battre 100 g d'œufs avec le reste du lait et 1 g de sel, verser sur la préparation et "
            "planter 2 g de feuilles de laurier dans la surface.",
            "Enfourner 35 minutes à 180 °C, jusqu'à ce que la couche d'œuf soit prise et "
            "légèrement dorée ; laisser reposer 5 minutes avant de servir.",
        ],
    ),
]
