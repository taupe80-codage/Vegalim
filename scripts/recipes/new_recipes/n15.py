"""Lot 15 : plats principaux en 30 minutes ou moins, petits-déjeuners vegan et sans gluten
(18 recettes).

Comble deux manques relevés par l'analyse d'équilibre du 2026-11-19 : 40 plats principaux
seulement se faisaient en 30 minutes ou moins, et 8 petits-déjeuners étaient à la fois vegan
et sans gluten.
"""
from ._schema import recipe

RECIPES = [
    # ── A. Plats principaux en 30 minutes ou moins ──────────────────────────────────────────
    recipe(
        rid="pasta_orecchiette_brocoli_3a71c4",
        fr="Orecchiette aux brocolis, ail et piment",
        en="Orecchiette with Broccoli, Garlic and Chili",
        original="Orecchiette con broccoli",
        cuisine="italian", country="italy", region="pouilles",
        dish="main", servings=4, prep=10, cook=15,
        texture=("fondant", "al_dente"), taste=("aillé", "pimenté"),
        technique=("boiling", "sauteing"), difficulty="easy", spice=1,
        desc="Plat des Pouilles : les fleurettes de brocoli cuisent dans l'eau des pâtes, puis "
             "s'écrasent à la poêle dans l'huile d'olive à l'ail et au piment jusqu'à napper les "
             "orecchiette d'une sauce verte et rustique.",
        compo=[
            ("pasta_raw_dried", 350, "g", "carbohydrate"),
            ("broccoli_raw", 500, "g", "main_vegetable"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("red_hot_chili_pepper_spice_dried", 2, "g", "spice"),
            ("olive_oil_extra_virgin_plant", 50, "ml", "fat"),
            ("lemon_peel_raw", 3, "g", "aroma"),
            ("breadcrumbs_dried", 30, "g", "garnish"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("water", 3000, "ml", "liquid"),
        ],
        steps=[
            "Porter 3 litres d'eau à ébullition avec 3 g de sel et détailler 500 g de brocoli en "
            "petites fleurettes, la tige pelée et coupée en dés.",
            "Faire dorer 30 g de chapelure à sec dans une grande poêle, 2 minutes, et la réserver.",
            "Cuire 350 g d'orecchiette et le brocoli ensemble dans l'eau bouillante, 11 minutes.",
            "Pendant ce temps, chauffer doucement 50 ml d'huile d'olive avec 12 g d'ail émincé et "
            "2 g de piment séché, sans laisser brunir l'ail.",
            "Égoutter pâtes et brocoli en gardant une louche d'eau de cuisson, verser dans la poêle "
            "et écraser le brocoli à la cuillère en remuant 2 minutes avec l'eau réservée.",
            "Râper 3 g de zeste de citron, poivrer avec 1 g de poivre et servir parsemé de chapelure "
            "dorée.",
        ],
    ),
    recipe(
        rid="wok_tofu_aigre_doux_ananas_8c2e15",
        fr="Tofu aigre-doux à l'ananas et aux poivrons",
        en="Sweet and Sour Tofu with Pineapple and Peppers",
        cuisine="chinese", country="china", region="guangdong",
        dish="main", servings=4, prep=15, cook=15,
        texture=("croustillant", "nappé"), taste=("sucré", "acidulé"),
        technique=("sauteing",), difficulty="easy",
        desc="Version végétale du classique cantonais : des cubes de tofu poêlés jusqu'à croustiller, "
             "sautés au wok avec ananas et poivrons dans une sauce brillante au vinaigre, au sucre "
             "et au concentré de tomate.",
        compo=[
            ("tofu_plain_pre_packaged", 400, "g", "plant_protein"),
            ("cornstarch_flour", 35, "g", "binder"),
            ("pineapple_raw", 250, "g", "fruit"),
            ("red_bell_pepper_raw", 150, "g", "vegetable"),
            ("green_bell_pepper_raw", 150, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("ginger_raw_root_fresh", 10, "g", "aromatic"),
            ("cider_vinegar_liquid", 45, "ml", "acidity"),
            ("brown_sugar", 40, "g", "sweetener"),
            ("tomato_paste_unsalted_canned", 30, "g", "condiment"),
            ("soy_sauce_shoyu_reduced_sodium", 30, "ml", "seasoning"),
            ("water", 100, "ml", "liquid"),
            ("sunflower_oil_plant", 40, "ml", "fat_cooking"),
            ("jasmine_rice_raw_seed", None, "g", "serving_suggestion"),
        ],
        steps=[
            "Égoutter 400 g de tofu, le couper en cubes de 2 cm et l'enrober de 25 g de fécule.",
            "Mélanger la sauce : 45 ml de vinaigre de cidre, 40 g de cassonade, 30 g de concentré "
            "de tomate, 30 ml de sauce soja, 100 ml d'eau et 10 g de fécule.",
            "Faire dorer le tofu dans 30 ml d'huile à feu vif, 6 minutes en le retournant, puis le "
            "réserver.",
            "Dans le wok, verser 10 ml d'huile et sauter 100 g d'oignon en pétales, 150 g de poivron "
            "rouge et 150 g de poivron vert en carrés, 3 minutes.",
            "Ajouter 6 g d'ail et 10 g de gingembre hachés, puis 250 g d'ananas en morceaux, et "
            "sauter 1 minute.",
            "Verser la sauce, laisser épaissir 1 minute, remettre le tofu et enrober ; servir aussitôt "
            "avec du riz jasmin.",
        ],
    ),
    recipe(
        rid="wrap_fajitas_champignons_5b9d02",
        fr="Fajitas de champignons et poivrons, guacamole",
        en="Mushroom and Pepper Fajitas with Guacamole",
        original="Fajitas de hongos",
        cuisine="mexican", country="mexico", region="",
        dish="main", servings=4, prep=15, cook=12,
        texture=("fondant", "croquant"), taste=("fumé", "acidulé"),
        technique=("sauteing",), difficulty="easy", spice=1,
        desc="Lanières de champignons, de poivrons et d'oignon saisies à feu vif avec cumin et "
             "paprika fumé, roulées dans des tortillas chaudes avec un guacamole au citron vert.",
        compo=[
            ("base_tortilla_92c2a6", 320, "g", "carbohydrate"),
            ("button_mushroom_raw", 500, "g", "main_vegetable"),
            ("red_bell_pepper_raw", 150, "g", "vegetable"),
            ("green_bell_pepper_raw", 150, "g", "vegetable"),
            ("red_onion_raw", 150, "g", "aromatic"),
            ("cumin_spice_seed", 4, "g", "spice"),
            ("paprika_powder", 4, "g", "spice"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("avocado_raw", 300, "g", "fat"),
            ("lime_juice_fresh", 30, "ml", "acidity"),
            ("coriander_raw_fresh_herb", 15, "g", "herb"),
            ("tomato_raw_ripe", 100, "g", "vegetable"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
        ],
        steps=[
            "Écraser la chair de 300 g d'avocat avec 30 ml de jus de citron vert, 100 g de tomate en "
            "petits dés, 10 g de coriandre hachée et 2 g de sel : c'est le guacamole.",
            "Émincer 500 g de champignons, 150 g de poivron rouge, 150 g de poivron vert et 150 g "
            "d'oignon rouge en lanières.",
            "Saisir les champignons dans 15 ml d'huile à feu très vif, 5 minutes, sans remuer au "
            "début pour qu'ils dorent, puis les réserver.",
            "Sauter poivrons et oignon dans 15 ml d'huile 4 minutes, remettre les champignons, ajouter "
            "4 g de cumin, 4 g de paprika et 3 g de sel, puis cuire 1 minute.",
            "Chauffer 320 g de tortillas 20 secondes de chaque côté dans une poêle sèche.",
            "Garnir chaque tortilla de légumes et de guacamole, parsemer de 5 g de coriandre et rouler.",
        ],
    ),
    recipe(
        rid="pasta_epinards_ricotta_citron_d40a6e",
        fr="Pâtes aux épinards, ricotta et citron",
        en="Pasta with Spinach, Ricotta and Lemon",
        original="Pasta ricotta e spinaci",
        cuisine="italian", country="italy", region="",
        dish="main", servings=4, prep=5, cook=12,
        texture=("crémeux",), taste=("frais", "lacté"),
        technique=("boiling",), difficulty="easy",
        desc="Plat de semaine en quinze minutes : la ricotta détendue à l'eau de cuisson forme une "
             "sauce sans crème, relevée de zeste de citron, de parmesan et de jeunes pousses "
             "d'épinard qui tombent au contact des pâtes chaudes.",
        compo=[
            ("pasta_raw_dried", 350, "g", "carbohydrate"),
            ("ricotta_whole_cow", 250, "g", "dairy"),
            ("spinach_raw_baby", 200, "g", "vegetable"),
            ("parmesan_grated_dried_cow", 40, "g", "dairy"),
            ("lemon_peel_raw", 4, "g", "aroma"),
            ("lemon_juice", 15, "ml", "acidity"),
            ("garlic_raw", 4, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 20, "ml", "fat"),
            ("nutmeg_spice", 1, "g", "spice"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("water", 3000, "ml", "liquid"),
        ],
        steps=[
            "Cuire 350 g de pâtes dans 3 litres d'eau bouillante salée avec 3 g de sel.",
            "Dans un grand saladier, mélanger 250 g de ricotta, 30 g de parmesan, 4 g de zeste et "
            "15 ml de jus de citron, 4 g d'ail râpé, 1 g de muscade et 1 g de poivre.",
            "Détendre la ricotta avec une louche d'eau de cuisson pour obtenir une crème souple.",
            "Égoutter les pâtes, les verser bouillantes sur 200 g de jeunes pousses d'épinard dans le "
            "saladier et mélanger : les épinards tombent en 1 minute.",
            "Napper de la crème de ricotta, arroser de 20 ml d'huile d'olive et servir avec 10 g de "
            "parmesan.",
        ],
    ),
    recipe(
        rid="egg_anda_curry_7f13b8",
        fr="Anda curry, œufs durs dans une sauce tomate aux épices",
        en="Anda Curry, Indian Egg Curry",
        original="Anda curry",
        cuisine="indian", country="india", region="pendjab",
        dish="main", servings=4, prep=10, cook=20,
        texture=("nappant", "fondant"), taste=("épicé", "tomaté"),
        technique=("boiling", "sauteing", "simmering"), kid_friendly=False, difficulty="easy", spice=2,
        desc="Le curry du soir des foyers indiens : des œufs durs entaillés et dorés au curcuma, "
             "plongés dans une sauce d'oignon, de tomate, de gingembre et de garam masala qui "
             "s'infiltre dans le blanc.",
        compo=[
            ("egg_raw", 480, "g", "protein"),
            ("onion_raw", 200, "g", "aromatic"),
            ("tomato_crushed_canned", 400, "g", "sauce"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("chilli_pepper_raw", 10, "g", "spice"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("turmeric_powder", 3, "g", "spice"),
            ("paprika_powder", 4, "g", "spice"),
            ("garam_masala", 6, "g", "spice"),
            ("sunflower_oil_plant", 40, "ml", "fat_cooking"),
            ("water", 1650, "ml", "liquid"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("basmati_rice_raw_seed", None, "g", "serving_suggestion"),
        ],
        steps=[
            "Cuire 480 g d'œufs (huit œufs) 9 minutes dans 1,5 litre d'eau bouillante, les refroidir "
            "et les écaler.",
            "Entailler chaque œuf de quatre fentes, les rouler dans 1 g de curcuma et les dorer "
            "2 minutes dans 15 ml d'huile ; réserver.",
            "Dans la même poêle, chauffer 25 ml d'huile, faire grésiller 3 g de cumin, puis cuire "
            "200 g d'oignon haché 7 minutes jusqu'à ce qu'il blondisse.",
            "Ajouter 10 g d'ail, 15 g de gingembre, 10 g de piment vert, 2 g de curcuma et 4 g de "
            "paprika, puis 400 g de tomates concassées, 150 ml d'eau et 5 g de sel ; mijoter "
            "8 minutes.",
            "Ajouter 6 g de garam masala et les œufs, mijoter 3 minutes en les arrosant de sauce, "
            "et servir parsemé de 10 g de coriandre, avec du riz basmati.",
        ],
    ),
    recipe(
        rid="bread_piadina_legumes_grilles_2c86f9",
        fr="Piadina aux légumes grillés et mozzarella",
        en="Piadina with Grilled Vegetables and Mozzarella",
        original="Piadina romagnola",
        cuisine="italian", country="italy", region="emilie_romagne",
        dish="main", servings=4, prep=15, cook=15,
        texture=("souple", "filant"), taste=("grillé", "lacté"),
        technique=("grilling",), difficulty="easy",
        desc="Galette de Romagne sans levure, pétrie en cinq minutes et cuite à la poêle, pliée sur "
             "des tranches d'aubergine et de courgette grillées, de la mozzarella et de la roquette.",
        compo=[
            ("wheat_flour_t55", 300, "g", "base"),
            ("olive_oil_extra_virgin_plant", 50, "ml", "fat"),
            ("baking_soda_powder", 2, "g", "leavening"),
            ("water", 150, "ml", "liquid"),
            ("eggplant_raw", 250, "g", "vegetable"),
            ("green_zucchini_squash_raw", 250, "g", "vegetable"),
            ("cows_milk_mozzarella_cow", 250, "g", "dairy"),
            ("arugula_raw", 60, "g", "vegetable"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Pétrir 300 g de farine, 2 g de bicarbonate, 4 g de sel, 30 ml d'huile d'olive et 150 ml "
            "d'eau tiède 5 minutes, puis diviser en quatre boules.",
            "Couper 250 g d'aubergine et 250 g de courgette en tranches de 5 mm, les badigeonner de "
            "20 ml d'huile et les griller 3 minutes par face à la poêle-gril ; saler de 2 g de sel.",
            "Étaler chaque boule en disque de 22 cm et le cuire 2 minutes par face dans une poêle "
            "sèche très chaude, jusqu'à ce qu'il se tache de brun.",
            "Garnir une moitié de chaque piadina chaude de légumes et de 250 g de mozzarella en "
            "tranches, poivrer avec 1 g de poivre, ajouter 60 g de roquette et replier.",
        ],
    ),
    recipe(
        rid="pasta_spaghetti_nerano_courgettes_e5c3a0",
        fr="Spaghetti alla Nerano, courgettes frites et provolone",
        en="Spaghetti alla Nerano with Fried Zucchini and Provolone",
        original="Spaghetti alla Nerano",
        cuisine="italian", country="italy", region="campanie", city="nerano",
        dish="main", servings=4, prep=10, cook=20,
        texture=("crémeux", "al_dente"), taste=("lacté", "doux"),
        technique=("sauteing", "boiling"), difficulty="medium",
        desc="Plat de la côte amalfitaine : des rondelles de courgettes frites jusqu'à fondre, "
             "écrasées avec l'eau des pâtes, du provolone et du parmesan en une sauce crémeuse sans "
             "crème, parfumée au basilic.",
        compo=[
            ("pasta_raw_dried", 350, "g", "carbohydrate"),
            ("green_zucchini_squash_raw", 600, "g", "main_vegetable"),
            ("sunflower_oil_plant", 60, "ml", "fat_cooking"),
            ("provolone_paste_cow", 80, "g", "dairy"),
            ("parmesan_grated_dried_cow", 40, "g", "dairy"),
            ("basil_fresh_herb", 15, "g", "herb"),
            ("garlic_raw", 4, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 15, "ml", "fat"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("water", 3000, "ml", "liquid"),
        ],
        steps=[
            "Couper 600 g de courgettes en rondelles fines et les frire en deux fois dans 60 ml "
            "d'huile chaude, 6 minutes, jusqu'à ce qu'elles dorent et s'affaissent ; saler de 2 g.",
            "Cuire 350 g de spaghetti dans 3 litres d'eau bouillante salée avec 3 g de sel, 2 minutes de "
            "moins que le temps indiqué.",
            "Dans une sauteuse, chauffer 15 ml d'huile d'olive avec 4 g d'ail écrasé, ajouter les "
            "courgettes et 10 g de basilic, et les écraser grossièrement.",
            "Ajouter les pâtes égouttées et deux louches d'eau de cuisson, finir la cuisson 2 minutes "
            "en remuant.",
            "Hors du feu, incorporer 80 g de provolone râpé et 40 g de parmesan en remuant vivement "
            "jusqu'à obtenir une sauce crémeuse ; poivrer avec 1 g de poivre et servir avec 5 g de "
            "basilic.",
        ],
    ),
    recipe(
        rid="rice_khao_pad_sapparot_9a40d3",
        fr="Khao pad sapparot, riz sauté thaï à l'ananas",
        en="Khao Pad Sapparot, Thai Pineapple Fried Rice",
        original="Khao pad sapparot",
        cuisine="thai", country="thailand", region="bangkok",
        dish="main", servings=4, prep=10, cook=20,
        texture=("grains_separes", "croquant"), taste=("sucré", "salé"),
        technique=("sauteing",), difficulty="easy",
        desc="Riz de la veille sauté au wok avec ananas, tofu, petits pois, raisins secs et noix de "
             "cajou, coloré au curry : un riz sauté sucré-salé servi dans les restaurants thaïs, "
             "parfois dans la demi-écorce de l'ananas.",
        compo=[
            ("jasmine_rice_raw_seed", 300, "g", "carbohydrate"),
            ("pineapple_raw", 250, "g", "fruit"),
            ("tofu_plain_pre_packaged", 200, "g", "plant_protein"),
            ("green_peas_raw", 100, "g", "vegetable"),
            ("cashew_nuts_raw", 50, "g", "nut"),
            ("grape_dried", 30, "g", "fruit"),
            ("onion_raw", 80, "g", "aromatic"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("curry_powder", 6, "g", "spice"),
            ("soy_sauce_shoyu_reduced_sodium", 40, "ml", "seasoning"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("green_onion_raw", 20, "g", "garnish"),
            ("water", 450, "ml", "liquid"),
        ],
        steps=[
            "Cuire 300 g de riz jasmin dans 450 ml d'eau 12 minutes à couvert, puis l'étaler pour le "
            "refroidir (ou utiliser du riz de la veille).",
            "Couper 200 g de tofu en dés et le faire dorer dans 15 ml d'huile à feu vif, 4 minutes.",
            "Ajouter 15 ml d'huile, 80 g d'oignon émincé, 6 g d'ail et 50 g de noix de cajou ; "
            "sauter 2 minutes.",
            "Verser le riz, 6 g de curry et 40 ml de sauce soja, et sauter 2 minutes en décollant "
            "les grains.",
            "Ajouter 250 g d'ananas en dés, 100 g de petits pois et 30 g de raisins secs, sauter "
            "2 minutes et servir parsemé de 20 g d'oignon vert ciselé.",
        ],
    ),
    recipe(
        rid="bread_croque_champignons_comte_1e7b58",
        allow_similar=("comte",),
        fr="Croque végétarien aux champignons et comté",
        en="Vegetarian Croque with Mushrooms and Comté",
        cuisine="french", country="france", region="franche_comte",
        dish="main", servings=4, prep=10, cook=18,
        texture=("croustillant", "filant"), taste=("lacté", "boisé"),
        technique=("sauteing", "baking"), difficulty="easy",
        desc="Le croque-monsieur sans jambon : une fondue de champignons au thym entre deux tranches "
             "de pain de mie, nappée de béchamel légère et de comté râpé, gratinée au four.",
        compo=[
            ("bread_white_commercial", 320, "g", "carbohydrate"),
            ("button_mushroom_raw", 400, "g", "main_vegetable"),
            ("shallot_raw", 40, "g", "aromatic"),
            ("thyme_fresh_herb", 2, "g", "herb"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("wheat_flour_t55", 20, "g", "thickener"),
            ("milk_liquid_pasteurized_3_5pct", 250, "ml", "dairy"),
            ("comte_cow", 120, "g", "dairy"),
            ("nutmeg_spice", 1, "g", "spice"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("arugula_raw", None, "g", "serving_suggestion"),
        ],
        steps=[
            "Faire sauter 400 g de champignons émincés et 40 g d'échalote dans 20 g de beurre à feu "
            "vif, 6 minutes, avec 2 g de thym, 2 g de sel et 1 g de poivre.",
            "Fondre 20 g de beurre, ajouter 20 g de farine, puis 250 ml de lait en fouettant ; cuire "
            "2 minutes, assaisonner de 1 g de muscade et 2 g de sel.",
            "Tartiner huit tranches de pain de mie (320 g) de béchamel, garnir quatre d'entre elles "
            "de champignons et de 60 g de comté râpé, puis refermer.",
            "Napper le dessus du reste de béchamel et de 60 g de comté, et gratiner 8 minutes à "
            "220 °C ; servir avec une salade de roquette.",
        ],
    ),
    recipe(
        rid="salad_lentilles_feta_croquante_4d95a1",
        fr="Salade-repas de lentilles, feta et légumes croquants",
        en="Hearty Lentil Salad with Feta and Crunchy Vegetables",
        cuisine="greek", country="greece", region="",
        dish="main", servings=4, prep=10, cook=20,
        texture=("croquant", "fondant"), taste=("acidulé", "salé"),
        technique=("boiling",), difficulty="easy",
        desc="Lentilles vertes cuites al dente, mélangées tièdes à une vinaigrette à la moutarde pour "
             "qu'elles s'en imprègnent, puis à du concombre, des tomates cerises, de l'oignon rouge "
             "et de la feta émiettée.",
        compo=[
            ("green_lentil_dried", 250, "g", "plant_protein"),
            ("feta_cow", 150, "g", "dairy"),
            ("cucumber_raw_with_skin", 200, "g", "vegetable"),
            ("cherry_tomato_raw", 200, "g", "vegetable"),
            ("red_onion_raw", 60, "g", "aromatic"),
            ("parsley_fresh_herb", 20, "g", "herb"),
            ("olive_oil_extra_virgin_plant", 45, "ml", "fat"),
            ("red_wine_vinegar_liquid", 20, "ml", "acidity"),
            ("mustard", 10, "g", "condiment"),
            ("oregano_spice_dried", 1, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("water", 1000, "ml", "liquid"),
        ],
        steps=[
            "Cuire 250 g de lentilles vertes rincées dans 1 litre d'eau non salée, 20 minutes : "
            "elles doivent rester entières ; préparer le reste pendant ce temps.",
            "Fouetter 10 g de moutarde, 20 ml de vinaigre de vin, 45 ml d'huile d'olive, 3 g de sel "
            "et 1 g de poivre.",
            "Égoutter les lentilles, ajouter 1 g de sel et les mélanger tièdes à la vinaigrette.",
            "Couper 200 g de concombre en dés, 200 g de tomates cerises en deux et 60 g d'oignon "
            "rouge en lamelles fines, ciseler 20 g de persil.",
            "Mélanger le tout aux lentilles, émietter 150 g de feta par-dessus et saupoudrer de 1 g "
            "d'origan.",
        ],
    ),
    recipe(
        rid="bread_pita_pois_chiches_tzatziki_6b0e27",
        allow_similar=("tzatziki",),
        fr="Pita aux pois chiches rôtis et tzatziki",
        en="Pita with Roasted Chickpeas and Tzatziki",
        cuisine="greek", country="greece", region="",
        dish="main", servings=4, prep=10, cook=20,
        texture=("croustillant", "frais"), taste=("épicé", "frais"),
        technique=("baking",), difficulty="easy", spice=1,
        desc="Pois chiches rôtis au paprika et au cumin jusqu'à croustiller, glissés dans une pita "
             "chaude avec tomate, oignon rouge, laitue et un tzatziki au concombre et à l'aneth.",
        compo=[
            ("white_pita_bread", 320, "g", "carbohydrate"),
            ("chickpea_boiled", 400, "g", "plant_protein"),
            ("paprika_powder", 4, "g", "spice"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("olive_oil_extra_virgin_plant", 30, "ml", "fat"),
            ("yogurt_greek_plain_4pct", 250, "g", "dairy"),
            ("cucumber_raw_with_skin", 150, "g", "vegetable"),
            ("garlic_raw", 4, "g", "aromatic"),
            ("dill_weed_fresh_herb_leaf", 8, "g", "herb"),
            ("tomato_raw_ripe", 150, "g", "vegetable"),
            ("red_onion_raw", 50, "g", "aromatic"),
            ("lettuce_raw", 80, "g", "vegetable"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Sécher 400 g de pois chiches égouttés dans un torchon, les mélanger à 20 ml d'huile "
            "d'olive, 4 g de paprika, 3 g de cumin et 2 g de sel.",
            "Les rôtir 20 minutes à 220 °C en secouant la plaque à mi-cuisson.",
            "Râper 150 g de concombre, le presser pour en extraire l'eau, et le mélanger à 250 g de "
            "yaourt grec, 4 g d'ail râpé, 8 g d'aneth ciselé, 10 ml d'huile d'olive et 2 g de sel.",
            "Réchauffer 320 g de pitas 1 minute au four, les ouvrir en poche.",
            "Garnir de 80 g de laitue, de 150 g de tomate et de 50 g d'oignon rouge émincés, des "
            "pois chiches et d'une bonne cuillerée de tzatziki.",
        ],
    ),

    # ── D. Petits-déjeuners vegan et sans gluten ────────────────────────────────────────────
    recipe(
        rid="brkf_sabudana_khichdi_c8f461",
        allow_similar=("khichdi",),
        fr="Sabudana khichdi, perles de tapioca aux cacahuètes",
        en="Sabudana Khichdi, Tapioca Pearls with Peanuts",
        original="Sabudana khichdi",
        cuisine="indian", country="india", region="maharashtra", city="pune",
        dish="breakfast", servings=4, prep=10, rest=360, cook=12,
        texture=("moelleux", "croquant"), taste=("épicé", "citronné"),
        technique=("sauteing",), kid_friendly=False, difficulty="medium", spice=1,
        desc="Petit-déjeuner du Maharashtra : des perles de tapioca trempées la nuit, sautées avec "
             "pommes de terre, cumin, piment vert et cacahuètes concassées, jusqu'à devenir "
             "translucides et détachées, avec un filet de citron.",
        compo=[
            ("tapioca_raw_dried", 250, "g", "carbohydrate"),
            ("peanut_raw", 80, "g", "nut"),
            ("potato_raw_flesh", 200, "g", "vegetable"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("chilli_pepper_raw", 10, "g", "spice"),
            ("curry_leaf", 2, "g", "herb"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("lemon_juice", 20, "ml", "acidity"),
            ("white_sugar", 5, "g", "sweetener"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 300, "ml", "liquid"),
        ],
        steps=[
            "Rincer 250 g de perles de tapioca jusqu'à ce que l'eau soit claire, les couvrir de "
            "300 ml d'eau à hauteur et laisser tremper 6 heures (ou la nuit) : elles s'écrasent "
            "entre les doigts.",
            "Torréfier 80 g de cacahuètes à sec, les concasser grossièrement et les mélanger aux "
            "perles égouttées avec 5 g de sel et 5 g de sucre.",
            "Chauffer 30 ml d'huile, faire grésiller 3 g de cumin, 2 g de feuilles de curry et 10 g "
            "de piment vert émincé, puis ajouter 200 g de pomme de terre en petits dés.",
            "Cuire les pommes de terre 6 minutes à couvert, ajouter les perles et sauter 5 minutes à "
            "feu moyen, jusqu'à ce qu'elles deviennent translucides.",
            "Arroser de 20 ml de jus de citron et parsemer de 10 g de coriandre.",
        ],
    ),
    recipe(
        rid="brkf_pesarattu_mungo_7d2c39",
        fr="Pesarattu, crêpes de haricots mungo au gingembre",
        en="Pesarattu, Mung Bean Crêpes with Ginger",
        original="Pesarattu",
        cuisine="indian", country="india", region="andhra_pradesh",
        dish="breakfast", servings=4, prep=15, rest=360, cook=30,
        texture=("croustillant", "souple"), taste=("épicé", "herbacé"),
        technique=("blending", "sauteing"), kid_friendly=False, difficulty="medium", spice=1,
        desc="Crêpe d'Andhra Pradesh sans fermentation : des haricots mungo entiers trempés, mixés "
             "avec un peu de riz, de gingembre et de piment vert, cuits en voile fin et "
             "croustillant parsemé d'oignon et de coriandre.",
        compo=[
            ("mung_bean_raw", 200, "g", "plant_protein"),
            ("white_rice_raw_seed_unenriched", 40, "g", "carbohydrate"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("chilli_pepper_raw", 10, "g", "spice"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("onion_raw", 80, "g", "aromatic"),
            ("coriander_raw_fresh_herb", 15, "g", "herb"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 650, "ml", "liquid"),
        ],
        steps=[
            "Faire tremper 200 g de haricots mungo entiers et 40 g de riz dans 500 ml d'eau "
            "6 heures, puis égoutter.",
            "Mixer avec 15 g de gingembre, 10 g de piment vert, 3 g de cumin, 5 g de sel et environ "
            "150 ml d'eau en une pâte fluide comme une pâte à crêpes.",
            "Hacher finement 80 g d'oignon et 15 g de coriandre.",
            "Chauffer une poêle huilée, étaler une louche de pâte en spirale du centre vers le bord "
            "et parsemer d'oignon et de coriandre.",
            "Arroser le bord d'un filet d'huile (30 ml au total) et cuire 3 minutes jusqu'à ce que "
            "le dessous croustille, retourner 1 minute et servir aussitôt.",
        ],
    ),
    recipe(
        rid="brkf_porridge_sarrasin_pomme_b37e90",
        fr="Porridge de sarrasin aux pommes et à la cannelle",
        en="Buckwheat Porridge with Apple and Cinnamon",
        original="Grechnevaya kasha",
        cuisine="russian", country="russia", region="",
        dish="breakfast", servings=4, prep=5, cook=20,
        texture=("crémeux", "fondant"), taste=("sucré", "épicé"),
        technique=("simmering",), difficulty="easy",
        desc="Le sarrasin, naturellement sans gluten, cuit doucement dans une boisson d'amande "
             "jusqu'à devenir crémeux, avec des dés de pomme, de la cannelle et du sirop d'érable, "
             "servi avec des noix torréfiées.",
        compo=[
            ("buckwheat_raw_whole_seed", 200, "g", "carbohydrate"),
            ("almond_milk_refrigerated_unsweetened_plant", 700, "ml", "liquid"),
            ("apple_raw_with_skin", 300, "g", "fruit"),
            ("cinnamon_powder", 3, "g", "spice"),
            ("maple_syrup", 40, "ml", "sweetener"),
            ("walnut_shelled_dried", 40, "g", "garnish"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ],
        steps=[
            "Rincer 200 g de sarrasin décortiqué non grillé et le porter à frémissement dans 600 ml "
            "de boisson d'amande avec 1 g de sel.",
            "Ajouter 300 g de pomme en dés et 3 g de cannelle, et cuire 18 minutes à feu doux en "
            "remuant souvent.",
            "Détendre avec 100 ml de boisson d'amande pour obtenir une texture crémeuse.",
            "Torréfier 40 g de noix 3 minutes à sec et les concasser.",
            "Servir arrosé de 40 ml de sirop d'érable et parsemé de noix.",
        ],
    ),
    recipe(
        rid="brkf_granola_sarrasin_noisettes_0f5a72",
        allow_similar=("noisettes",),
        fr="Granola sans gluten au sarrasin et aux noisettes",
        en="Gluten-Free Buckwheat and Hazelnut Granola",
        cuisine="international", country="international",
        dish="breakfast", servings=8, prep=10, cook=25,
        texture=("croustillant",), taste=("sucré", "torréfié"),
        technique=("baking",), difficulty="easy",
        desc="Un granola sans avoine, donc sans risque de gluten : sarrasin, noisettes, graines de "
             "tournesol et noix de coco enrobés de sirop d'érable et d'huile de coco, cuits en "
             "plaque jusqu'à former des grappes croustillantes.",
        compo=[
            ("buckwheat_raw_whole_seed", 200, "g", "carbohydrate"),
            ("hazelnut_raw_unsalted", 100, "g", "nut"),
            ("sunflower_raw_seed", 60, "g", "nut"),
            ("coconut_flesh_dried", 40, "g", "texture"),
            ("maple_syrup", 80, "ml", "sweetener"),
            ("coconut_oil_plant", 40, "g", "fat"),
            ("cinnamon_powder", 3, "g", "spice"),
            ("grape_dried", 60, "g", "fruit"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
            ("almond_milk_refrigerated_unsweetened_plant", None, "ml", "serving_suggestion"),
        ],
        steps=[
            "Mélanger 200 g de sarrasin cru, 100 g de noisettes concassées, 60 g de graines de "
            "tournesol, 40 g de noix de coco râpée, 3 g de cannelle et 1 g de sel.",
            "Fondre 40 g d'huile de coco avec 80 ml de sirop d'érable et verser sur les graines en "
            "mélangeant bien.",
            "Étaler sur une plaque recouverte de papier cuisson en tassant, et cuire 25 minutes au "
            "four à 160 °C en retournant une fois.",
            "Laisser refroidir sans toucher pour que les grappes durcissent, puis ajouter 60 g de "
            "raisins secs ; servir avec une boisson d'amande.",
        ],
    ),
    recipe(
        rid="brkf_bubur_ketan_hitam_4a8d16",
        fr="Bubur ketan hitam, riz noir au lait de coco",
        en="Bubur Ketan Hitam, Black Rice Pudding with Coconut Milk",
        original="Bubur ketan hitam",
        cuisine="indonesian", country="indonesia", region="java",
        dish="breakfast", servings=4, prep=5, rest=120, cook=45,
        texture=("crémeux", "moelleux"), taste=("sucré", "lacté"),
        technique=("simmering",), difficulty="easy",
        desc="Bouillie indonésienne de riz noir cuit longuement avec du sucre de coco et une pointe "
             "de gingembre, servie tiède sous un trait de lait de coco salé : un petit-déjeuner "
             "aussi courant qu'un dessert.",
        compo=[
            ("black_rice_raw_seed_unenriched", 200, "g", "carbohydrate"),
            ("water", 1200, "ml", "liquid"),
            ("coconut_sugar", 70, "g", "sweetener"),
            ("ginger_raw_root_fresh", 10, "g", "aroma"),
            ("coconut_milk_plant", 200, "ml", "fat"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ],
        steps=[
            "Rincer 200 g de riz noir et le faire tremper 2 heures dans de l'eau froide, puis "
            "égoutter.",
            "Le cuire dans 1,2 litre d'eau avec 10 g de gingembre en lamelles, 40 minutes à petit feu "
            "en remuant de temps en temps, jusqu'à ce que les grains éclatent et que la bouillie "
            "épaississe.",
            "Ajouter 70 g de sucre de coco et 1 g de sel, et cuire encore 5 minutes ; retirer le "
            "gingembre.",
            "Chauffer 200 ml de lait de coco avec 1 g de sel sans faire bouillir.",
            "Servir la bouillie tiède, nappée de lait de coco salé.",
        ],
    ),
    recipe(
        rid="brkf_muffins_polenta_myrtilles_e2b947",
        fr="Muffins de polenta aux myrtilles",
        en="Polenta Blueberry Muffins",
        cuisine="american", country="united_states",
        dish="breakfast", servings=10, prep=15, cook=22,
        texture=("moelleux", "granuleux"), taste=("sucré", "fruité"),
        technique=("baking",), difficulty="easy",
        desc="Muffins sans œufs ni gluten : la semoule de maïs et la farine de riz donnent une mie "
             "dorée et légèrement croquante, soulevée par le bicarbonate et le vinaigre, et "
             "constellée de myrtilles.",
        compo=[
            ("cornmeal_whole_dried", 150, "g", "base"),
            ("rice_flour", 120, "g", "base"),
            ("white_sugar", 90, "g", "sweetener"),
            ("baking_soda_powder", 6, "g", "leavening"),
            ("almond_milk_refrigerated_unsweetened_plant", 240, "ml", "liquid"),
            ("sunflower_oil_plant", 70, "ml", "fat"),
            ("cider_vinegar_liquid", 15, "ml", "acidity"),
            ("lemon_peel_raw", 3, "g", "aroma"),
            ("blueberry_raw", 150, "g", "fruit"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ],
        steps=[
            "Mélanger 150 g de semoule de maïs fine, 120 g de farine de riz, 90 g de sucre, 6 g de "
            "bicarbonate et 2 g de sel.",
            "Fouetter 240 ml de boisson d'amande, 70 ml d'huile, 15 ml de vinaigre de cidre et 3 g "
            "de zeste de citron.",
            "Verser le liquide sur les poudres et mélanger juste assez pour qu'il ne reste plus de "
            "poudre, puis incorporer 150 g de myrtilles.",
            "Répartir dans dix caissettes et cuire 22 minutes au four à 190 °C, jusqu'à ce qu'une lame en "
            "ressorte sèche.",
        ],
    ),
    recipe(
        rid="brkf_toasts_patate_douce_cacahuete_5c71e3",
        allow_similar=("toasts",),
        fr="Toasts de patate douce, beurre de cacahuète et banane",
        en="Sweet Potato Toasts with Peanut Butter and Banana",
        cuisine="american", country="united_states",
        dish="breakfast", servings=2, prep=5, cook=15,
        texture=("fondant", "croustillant"), taste=("sucré", "torréfié"),
        technique=("baking",), difficulty="easy",
        desc="Des tranches épaisses de patate douce grillées remplacent le pain : tartinées de beurre "
             "de cacahuète, garnies de banane et de graines de chia, un petit-déjeuner sans gluten "
             "qui tient au corps.",
        compo=[
            ("sweet_potato_raw", 300, "g", "carbohydrate"),
            ("peanut_butter_natural_plant", 40, "g", "fat"),
            ("banana_raw", 120, "g", "fruit"),
            ("chia_raw_seed_dried", 8, "g", "garnish"),
            ("cinnamon_powder", 1, "g", "spice"),
            ("maple_syrup", 10, "ml", "sweetener"),
            ("sunflower_oil_plant", 5, "ml", "fat_cooking"),
        ],
        steps=[
            "Couper 300 g de patate douce lavée en tranches de 8 mm dans la longueur et les "
            "badigeonner de 5 ml d'huile.",
            "Les griller 15 minutes au four à 210 °C en les retournant à mi-cuisson, jusqu'à ce "
            "qu'elles soient tendres et dorées (ou deux passages au grille-pain).",
            "Tartiner chaque tranche de beurre de cacahuète (40 g au total).",
            "Garnir de 120 g de banane en rondelles, saupoudrer de 1 g de cannelle et de 8 g de "
            "graines de chia, et arroser de 10 ml de sirop d'érable.",
        ],
    ),
]
