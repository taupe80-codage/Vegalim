"""Lot 19 : plats rapides, riches en protéines et d'hiver ; desserts et petits-déjeuners vegan
minute (18 recettes, 2026-11-23).

Mesure du 2026-11-23 (951 plats) : 53 plats principaux sur 451 en 30 minutes ou moins (14 en
20 minutes), 95 plats à 20 g de protéines par portion (49 vegan), aucun dessert en 15 minutes,
20 desserts vegan sur 75. Chaque plat ci-dessous croise plusieurs de ces manques : prêt en
25 minutes au plus, au moins 20 g de protéines par portion pour les plats salés, légumes de
fin d'automne et d'hiver (poireau, chou, kale, choux de Bruxelles, épinard, poire, agrumes).

Le seitan, les nouilles soba et les tortillas sont les préparations de base du catalogue
(maison ou du commerce) : leur temps de fabrication n'entre pas dans celui des plats.
"""
from ._schema import recipe

RECIPES = [
    # ── A. Plats principaux rapides et riches en protéines ────────────────────────────────
    recipe(
        rid="main_soba_tofu_pak_choi_cacahuetes_4e81c2",
        fr="Soba sautées au tofu, pak-choï et cacahuètes",
        en="Stir-Fried Soba with Tofu, Bok Choy and Peanuts",
        cuisine="japanese", country="japan",
        dish="main", servings=4, prep=10, cook=15,
        texture=("al_dente", "croquant"), taste=("umami", "equilibre"),
        technique=("boiling", "sauteing"), difficulty="easy",
        desc="Des nouilles de sarrasin sautées au wok avec du tofu doré, du pak-choï tout juste "
             "saisi et une sauce soja, gingembre et sirop d'érable, finies aux cacahuètes "
             "concassées : un dîner complet en vingt-cinq minutes.",
        compo=[
            ("base_soba_noodles_33e97c", 400, "g", "carbohydrate"),
            ("tofu_plain_pre_packaged", 400, "g", "plant_protein"),
            ("bok_choy_raw", 400, "g", "main_vegetable"),
            ("peanut_roasted_salted_dry", 50, "g", "garnish"),
            ("soy_sauce_shoyu_reduced_sodium", 45, "ml", "umami"),
            ("maple_syrup", 15, "ml", "sweetener"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("sesame_oil_plant", 20, "ml", "fat"),
            ("green_onion_raw", 30, "g", "garnish"),
        ],
        steps=[
            "Couper 400 g de tofu en dés de 2 cm et les faire dorer 6 minutes dans 10 ml d'huile "
            "de sésame au wok, à feu vif, en les retournant souvent ; réserver.",
            "Cuire 400 g de nouilles soba 3 minutes dans l'eau bouillante, les égoutter et les "
            "rincer à l'eau froide pour qu'elles ne collent pas.",
            "Dans le wok, faire revenir 1 minute 15 g de gingembre et 10 g d'ail hachés dans "
            "10 ml d'huile de sésame, ajouter 400 g de pak-choï coupé en quatre et le sauter "
            "3 minutes : les tiges doivent rester croquantes.",
            "Ajouter les nouilles, le tofu, 45 ml de sauce soja et 15 ml de sirop d'érable, et "
            "sauter 2 minutes en mélangant.",
            "Servir parsemé de 50 g de cacahuètes concassées et de 30 g d'oignon vert ciselé.",
        ],
    ),
    recipe(
        rid="main_dahl_express_poireau_epinards_9c3a7e",
        fr="Dahl express de lentilles corail au poireau et aux épinards",
        en="Quick Red Lentil Dal with Leek and Spinach",
        cuisine="indian", country="india",
        dish="main", servings=4, prep=5, cook=20,
        texture=("cremeux", "fondant"), taste=("epice", "doux"),
        technique=("sauteing", "simmering"), difficulty="easy", spice=1,
        desc="Les lentilles corail cuisent en vingt minutes et fondent d'elles-mêmes : un dahl "
             "doux au lait de coco, relevé de garam masala et de gingembre, avec du poireau "
             "fondu et des épinards ajoutés au dernier moment.",
        compo=[
            ("red_lentil_dried", 320, "g", "plant_protein"),
            ("leeks_raw", 300, "g", "main_vegetable"),
            ("spinach_raw_baby", 150, "g", "vegetable"),
            ("coconut_milk_plant", 200, "ml", "liquid"),
            ("tomato_crushed_canned", 200, "g", "vegetable"),
            ("water", 800, "ml", "liquid"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("garam_masala", 8, "g", "spice"),
            ("turmeric_powder", 3, "g", "spice"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("lemon_juice", 30, "ml", "acidity"),
        ],
        steps=[
            "Faire fondre 300 g de poireau émincé 4 minutes dans 20 ml d'huile d'olive, avec "
            "10 g d'ail et 15 g de gingembre râpés.",
            "Ajouter 8 g de garam masala et 3 g de curcuma, remuer 30 secondes, puis verser "
            "320 g de lentilles corail rincées, 200 g de tomates concassées et 800 ml d'eau.",
            "Cuire 15 minutes à petit bouillon en remuant de temps en temps, jusqu'à ce que les "
            "lentilles se défassent.",
            "Incorporer 200 ml de lait de coco, 4 g de sel et 150 g de jeunes pousses "
            "d'épinard, et cuire encore 2 minutes.",
            "Servir arrosé de 30 ml de jus de citron.",
        ],
    ),
    recipe(
        rid="main_pois_chiches_kale_tahini_boulgour_7b2f41",
        fr="Pois chiches dorés au kale et sauce tahini, boulgour",
        en="Crispy Chickpeas with Kale, Tahini Sauce and Bulgur",
        cuisine="levantine", country="lebanon",
        dish="main", servings=4, prep=10, cook=15,
        texture=("croustillant", "fondant"), taste=("terreux", "acidule"),
        technique=("boiling", "sauteing"), difficulty="easy",
        desc="Des pois chiches dorés à la poêle au cumin et au paprika, du chou kale juste "
             "tombé à l'ail, sur un lit de boulgour, nappés d'une sauce tahini au citron.",
        compo=[
            ("bulgur_raw_dried", 200, "g", "carbohydrate"),
            ("water", 400, "ml", "liquid"),
            ("chickpea_rinsed_canned", 560, "g", "plant_protein"),
            ("kale_raw", 250, "g", "main_vegetable"),
            ("sesame_tahini_raw_butter_seed_plant", 70, "g", "sauce"),
            ("lemon_juice", 40, "ml", "acidity"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("cumin_spice_seed", 4, "g", "spice"),
            ("paprika_powder", 3, "g", "spice"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Verser 200 g de boulgour dans 400 ml d'eau bouillante salée avec 2 g de sel, "
            "couvrir et laisser gonfler 12 minutes hors du feu.",
            "Égoutter et sécher 560 g de pois chiches, les faire dorer 8 minutes dans 20 ml "
            "d'huile d'olive à feu vif avec 4 g de cumin et 3 g de paprika.",
            "Retirer les pois chiches, faire revenir 8 g d'ail émincé 30 secondes dans 10 ml "
            "d'huile, ajouter 250 g de kale effeuillé et le cuire 3 minutes en remuant.",
            "Délayer 70 g de tahini avec 40 ml de jus de citron, 2 g de sel et 4 cuillères à "
            "soupe d'eau froide, jusqu'à une sauce nappante.",
            "Dresser le boulgour, le kale et les pois chiches, et napper de sauce tahini.",
        ],
    ),
    recipe(
        rid="main_tempeh_erable_choux_bruxelles_2d9e60",
        fr="Tempeh laqué à l'érable, choux de Bruxelles poêlés et riz",
        en="Maple-Glazed Tempeh with Pan-Roasted Brussels Sprouts and Rice",
        cuisine="american", country="usa",
        dish="main", servings=4, prep=10, cook=15,
        texture=("croustillant", "fondant"), taste=("caramelise", "umami"),
        technique=("boiling", "sauteing", "caramelizing"), difficulty="easy",
        desc="Des tranches de tempeh dorées puis laquées d'une sauce érable, soja et vinaigre "
             "de cidre, avec des choux de Bruxelles coupés en deux et poêlés jusqu'à colorer, "
             "des noix et du riz basmati.",
        compo=[
            ("basmati_rice_raw_seed", 240, "g", "carbohydrate"),
            ("water", 480, "ml", "liquid"),
            ("tempeh_tempe_raw_fermented", 400, "g", "plant_protein"),
            ("brussels_sprouts_raw", 500, "g", "main_vegetable"),
            ("maple_syrup", 40, "ml", "sweetener"),
            ("soy_sauce_shoyu_reduced_sodium", 30, "ml", "umami"),
            ("cider_vinegar_liquid", 15, "ml", "acidity"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("walnut_shelled_dried", 40, "g", "garnish"),
        ],
        steps=[
            "Cuire 240 g de riz basmati rincé dans 480 ml d'eau, à couvert et à feu doux, "
            "15 minutes.",
            "Couper 500 g de choux de Bruxelles en deux et les poêler 10 minutes dans 15 ml "
            "d'huile d'olive, face coupée vers le bas, jusqu'à ce qu'ils soient bien dorés.",
            "En même temps, couper 400 g de tempeh en tranches de 1 cm et les dorer 3 minutes "
            "par face dans 15 ml d'huile.",
            "Mélanger 40 ml de sirop d'érable, 30 ml de sauce soja, 15 ml de vinaigre de cidre "
            "et 8 g d'ail râpé, verser sur le tempeh et laisser réduire 2 minutes en retournant "
            "les tranches pour les laquer.",
            "Servir le tempeh sur le riz avec les choux de Bruxelles et 40 g de noix concassées.",
        ],
    ),
    recipe(
        rid="main_seitan_poireaux_moutarde_5f0c38",
        fr="Émincé de seitan aux poireaux et à la moutarde, pommes de terre vapeur",
        en="Seitan Strips with Leeks in Mustard Sauce and Steamed Potatoes",
        cuisine="french", country="france",
        dish="main", servings=4, prep=10, cook=15,
        texture=("fondant", "nappant"), taste=("savoureux", "acidule"),
        technique=("steaming", "sauteing", "sauce_making"), difficulty="easy",
        desc="Un émincé de bistrot sans viande : seitan saisi, poireaux fondus, sauce crémeuse "
             "à la moutarde liée au yaourt de soja, avec des pommes de terre vapeur.",
        compo=[
            ("potato_raw_flesh", 600, "g", "carbohydrate"),
            ("base_seitan_249032", 320, "g", "plant_protein"),
            ("leeks_raw", 500, "g", "main_vegetable"),
            ("mustard", 30, "g", "condiment"),
            ("soybean_yogurt_plain_plant", 150, "g", "sauce"),
            ("olive_oil_plant", 25, "ml", "fat"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ],
        steps=[
            "Cuire 600 g de pommes de terre coupées en morceaux 15 minutes à la vapeur.",
            "Couper 320 g de seitan en lanières et les saisir 4 minutes dans 15 ml d'huile "
            "d'olive à feu vif ; réserver.",
            "Faire fondre 500 g de poireau émincé 8 minutes à feu moyen dans 10 ml d'huile, "
            "avec 3 g de sel et 1 g de poivre.",
            "Hors du feu, incorporer 30 g de moutarde et 150 g de yaourt de soja, remettre le "
            "seitan et réchauffer 1 minute sans faire bouillir.",
            "Servir avec les pommes de terre et 10 g de persil haché.",
        ],
        # « Seitan mijoté aux champignons et à la moutarde » : autre plat (mijoté, champignons)
        allow_similar=("moutarde",),
    ),
    recipe(
        rid="main_frittata_epinards_feta_8a4d17",
        fr="Frittata aux épinards, oignon et feta",
        en="Spinach, Onion and Feta Frittata",
        cuisine="italian", country="italy",
        dish="main", servings=4, prep=5, cook=15,
        texture=("moelleux", "fondant"), taste=("savoureux", "salé"),
        technique=("sauteing", "baking"), difficulty="easy",
        desc="Une omelette épaisse à l'italienne, pleine d'épinards et d'oignon fondu, piquée de "
             "feta, prise à la poêle puis finie au four : à servir chaude ou tiède avec une "
             "salade.",
        compo=[
            ("egg_raw", 480, "g", "protein"),
            ("spinach_raw_mature", 300, "g", "main_vegetable"),
            ("feta_cow", 150, "g", "dairy"),
            ("onion_raw", 100, "g", "aromatic"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ],
        steps=[
            "Préchauffer le gril du four. Faire fondre 100 g d'oignon émincé 4 minutes dans "
            "20 ml d'huile d'olive, dans une poêle allant au four.",
            "Ajouter 300 g d'épinards et les faire tomber 2 minutes.",
            "Battre 8 œufs (480 g) avec 2 g de sel, 1 g de poivre et 15 g de persil haché, "
            "les verser sur les épinards et émietter 150 g de feta par-dessus.",
            "Cuire 6 minutes à feu doux sans remuer, jusqu'à ce que les bords soient pris.",
            "Cuire 3 minutes au four sous le gril, jusqu'à ce que le dessus soit pris et doré.",
        ],
    ),
    recipe(
        rid="pasta_haricots_blancs_kale_parmesan_3e6b92",
        fr="Pâtes aux haricots blancs, chou kale et parmesan",
        en="Pasta with White Beans, Kale and Parmesan",
        cuisine="italian", country="italy",
        dish="main", servings=4, prep=5, cook=15,
        texture=("al_dente", "cremeux"), taste=("savoureux", "aillé"),
        technique=("boiling", "sauteing"), difficulty="easy",
        desc="Pasta e fagioli version poêlée : des haricots blancs écrasés en partie pour lier "
             "la sauce, du kale à l'ail et au piment, et beaucoup de parmesan.",
        compo=[
            ("pasta_raw_dried", 320, "g", "carbohydrate"),
            ("water", 3000, "ml", "liquid"),
            ("white_bean_canned", 400, "g", "plant_protein"),
            ("kale_raw", 250, "g", "main_vegetable"),
            ("parmesan_grated_dried_cow", 60, "g", "dairy"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("red_hot_chili_pepper_spice_dried", 2, "g", "spice"),
            ("lemon_juice", 20, "ml", "acidity"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Cuire 320 g de pâtes dans 3 l d'eau bouillante salée avec 4 g de sel, selon le "
            "temps du paquet (10 minutes environ) ; garder un verre d'eau de cuisson.",
            "Faire revenir 12 g d'ail émincé et 2 g de piment séché 1 minute dans 40 ml "
            "d'huile d'olive.",
            "Ajouter 250 g de kale effeuillé et le cuire 4 minutes, puis 400 g de haricots "
            "blancs égouttés, dont on écrase un tiers à la fourchette.",
            "Ajouter les pâtes, un demi-verre d'eau de cuisson et 40 g de parmesan, et mélanger "
            "1 minute jusqu'à ce que la sauce enrobe les pâtes.",
            "Servir avec 20 ml de jus de citron et 20 g de parmesan.",
        ],
        allow_similar=("kale", "parmesan"),
    ),
    recipe(
        rid="main_chili_sin_carne_lentilles_express_6c1e05",
        fr="Chili sin carne express aux lentilles corail",
        en="Quick Red Lentil Chili Sin Carne",
        cuisine="mexican", country="mexico",
        dish="main", servings=4, prep=5, cook=20,
        texture=("sauce_dense", "fondant"), taste=("epice", "tomate"),
        technique=("simmering", "boiling"), difficulty="easy", spice=2,
        desc="Le chili du soir de semaine : des lentilles corail qui cuisent dans la sauce et "
             "l'épaississent, des haricots rouges, du poivron, du cumin, du paprika et une "
             "pointe de cacao, avec du riz.",
        compo=[
            ("basmati_rice_raw_seed", 240, "g", "carbohydrate"),
            ("red_lentil_dried", 150, "g", "plant_protein"),
            ("kidney_bean_boiled", 500, "g", "plant_protein"),
            ("tomato_crushed_canned", 400, "g", "sauce"),
            ("onion_raw", 150, "g", "aromatic"),
            ("red_bell_pepper_raw", 150, "g", "vegetable"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("cumin_spice_seed", 4, "g", "spice"),
            ("paprika_powder", 4, "g", "spice"),
            ("red_hot_chili_pepper_spice_dried", 2, "g", "spice"),
            ("cocoa_powder_unsweetened", 5, "g", "spice"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("water", 1080, "ml", "liquid"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Cuire 240 g de riz basmati rincé dans 480 ml d'eau, à couvert et à feu doux, "
            "15 minutes.",
            "Faire revenir 150 g d'oignon et 150 g de poivron rouge en dés 4 minutes dans 20 ml "
            "d'huile d'olive, avec 10 g d'ail.",
            "Ajouter 4 g de cumin, 4 g de paprika, 2 g de piment et 5 g de cacao, remuer 30 "
            "secondes, puis 150 g de lentilles corail rincées, 400 g de tomates "
            "concassées et 600 ml d'eau.",
            "Laisser mijoter 12 minutes à couvert en remuant de temps en temps, puis ajouter "
            "500 g de haricots rouges égouttés et 4 g de sel, et cuire encore 3 minutes : les "
            "lentilles se défont et lient la sauce.",
            "Servir avec le riz.",
        ],
        allow_similar=("chili", "carne"),
    ),
    recipe(
        rid="main_tofu_croustillant_sesame_brocoli_0a7d53",
        fr="Tofu croustillant au sésame, brocoli et riz",
        en="Crispy Sesame Tofu with Broccoli and Rice",
        cuisine="chinese", country="china",
        dish="main", servings=4, prep=10, cook=15,
        texture=("croustillant", "croquant"), taste=("umami", "légèrement_sucré"),
        technique=("boiling", "sauteing", "steaming"), difficulty="easy",
        desc="Des dés de tofu roulés dans la fécule et dorés jusqu'à être croustillants, laqués "
             "d'une sauce soja, gingembre et érable, avec du brocoli croquant et du sésame.",
        compo=[
            ("basmati_rice_raw_seed", 240, "g", "carbohydrate"),
            ("water", 480, "ml", "liquid"),
            ("tofu_plain_pre_packaged", 450, "g", "plant_protein"),
            ("cornstarch_flour", 30, "g", "binder"),
            ("broccoli_raw", 400, "g", "main_vegetable"),
            ("soy_sauce_shoyu_reduced_sodium", 40, "ml", "umami"),
            ("maple_syrup", 20, "ml", "sweetener"),
            ("ginger_raw_root_fresh", 10, "g", "aromatic"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("sunflower_oil_plant", 30, "ml", "fat"),
            ("sesame_oil_plant", 10, "ml", "fat"),
            ("sesame_seed_hulled_dried", 20, "g", "garnish"),
        ],
        steps=[
            "Cuire 240 g de riz basmati rincé dans 480 ml d'eau, à couvert et à feu doux, "
            "15 minutes.",
            "Couper 450 g de tofu en dés, bien les sécher et les rouler dans 30 g de fécule de "
            "maïs.",
            "Dorer le tofu 8 minutes dans 30 ml d'huile de tournesol à feu vif, en le "
            "retournant pour que chaque face soit croustillante.",
            "Pendant ce temps, cuire 400 g de bouquets de brocoli 4 minutes à la vapeur.",
            "Mélanger 40 ml de sauce soja, 20 ml de sirop d'érable, 10 g de gingembre et 8 g "
            "d'ail râpés et 10 ml d'huile de sésame, verser sur le tofu et laisser réduire "
            "1 minute ; servir avec le brocoli et le riz, parsemé de 20 g de sésame.",
        ],
        # « Tofu croustillant sauce ail » : autre plat (sauce à l'ail, sans brocoli ni sésame)
        allow_similar=("croustillant", "brocoli"),
    ),
    recipe(
        rid="main_quesadillas_haricots_noirs_cheddar_b5e294",
        fr="Quesadillas aux haricots noirs, maïs et cheddar",
        en="Black Bean, Corn and Cheddar Quesadillas",
        cuisine="mexican", country="mexico",
        dish="main", servings=4, prep=10, cook=10,
        texture=("croustillant", "fondant"), taste=("savoureux", "epice"),
        technique=("sauteing", "assembly"), difficulty="easy", spice=1,
        desc="Des tortillas de maïs garnies de haricots noirs écrasés au cumin, de maïs, de "
             "poivron et de cheddar fondant, dorées à la poêle, avec de la coriandre et du "
             "citron vert.",
        compo=[
            ("base_tortilla_92c2a6", 320, "g", "carbohydrate"),
            ("black_bean_boiled", 400, "g", "plant_protein"),
            ("sweet_corn_canned", 150, "g", "vegetable"),
            ("cheddar_cow", 140, "g", "dairy"),
            ("red_bell_pepper_raw", 150, "g", "vegetable"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("paprika_powder", 3, "g", "spice"),
            ("olive_oil_plant", 15, "ml", "fat"),
            ("coriander_raw_fresh_herb", 15, "g", "herb"),
            ("lime_juice_fresh", 20, "ml", "acidity"),
        ],
        steps=[
            "Écraser 400 g de haricots noirs égouttés avec 3 g de cumin et 3 g de paprika.",
            "Faire revenir 150 g de poivron rouge en petits dés 3 minutes dans 5 ml d'huile, "
            "puis mélanger avec 150 g de maïs égoutté.",
            "Étaler la purée de haricots sur 4 tortillas (160 g), répartir le poivron, le maïs "
            "et 140 g de cheddar râpé, et couvrir des 4 autres tortillas (160 g).",
            "Dorer les quesadillas 2 minutes par face dans une poêle légèrement huilée (10 ml), "
            "jusqu'à ce que le fromage file.",
            "Couper en quartiers et servir avec 15 g de coriandre et 20 ml de jus de citron vert.",
        ],
        kid_friendly=True,
    ),
    recipe(
        rid="salad_lentilles_chou_rouge_noix_feta_d40c8b",
        fr="Salade tiède de lentilles, chou rouge, noix et feta",
        en="Warm Lentil Salad with Red Cabbage, Walnuts and Feta",
        cuisine="french", country="france",
        dish="main", servings=4, prep=15, cook=5,
        texture=("croquant", "fondant"), taste=("acidule", "terreux"),
        technique=("sauteing", "assembly"), difficulty="easy",
        desc="Lentilles vertes cuites réchauffées dans une vinaigrette à la moutarde, chou rouge "
             "émincé fin, pomme, noix et feta : une salade d'hiver qui tient au corps.",
        compo=[
            ("green_lentil_boiled", 600, "g", "plant_protein"),
            ("red_cabbage_raw", 300, "g", "main_vegetable"),
            ("apple_raw_with_skin", 150, "g", "fruit"),
            ("walnut_shelled_dried", 50, "g", "garnish"),
            ("feta_cow", 120, "g", "dairy"),
            ("red_onion_raw", 60, "g", "aromatic"),
            ("mustard", 15, "g", "condiment"),
            ("cider_vinegar_liquid", 20, "ml", "acidity"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("parsley_fresh_herb", 20, "g", "herb"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ],
        steps=[
            "Émincer très finement 300 g de chou rouge et 60 g d'oignon rouge, couper 150 g "
            "de pomme en dés.",
            "Fouetter 15 g de moutarde, 20 ml de vinaigre de cidre, 40 ml d'huile d'olive et "
            "2 g de sel.",
            "Réchauffer 600 g de lentilles vertes cuites 3 minutes à la poêle avec la moitié de "
            "la vinaigrette.",
            "Mélanger les lentilles tièdes avec le chou, l'oignon, la pomme et le reste de la "
            "vinaigrette.",
            "Servir parsemé de 120 g de feta émiettée, 50 g de noix concassées et 20 g de "
            "persil.",
        ],
        allow_similar=("salade", "lentilles"),
    ),

    # ── B. Soupe et petits-déjeuners protéinés ────────────────────────────────────────────
    recipe(
        rid="soup_miso_soba_tofu_epinards_71f6aa",
        fr="Soupe miso aux nouilles soba, tofu et épinards",
        en="Miso Soup with Soba Noodles, Tofu and Spinach",
        cuisine="japanese", country="japan",
        dish="soup", servings=4, prep=5, cook=15,
        texture=("bouillon_riche", "fondant"), taste=("umami", "equilibre"),
        technique=("simmering", "boiling"), difficulty="easy",
        desc="Un bol complet pour les soirs froids : bouillon de shiitake et gingembre, miso "
             "délayé hors du feu, nouilles de sarrasin, tofu et jeunes pousses d'épinard.",
        compo=[
            ("water", 1500, "ml", "liquid"),
            ("shiitake_mushroom_raw", 150, "g", "umami"),
            ("ginger_raw_root_fresh", 10, "g", "aromatic"),
            ("miso_fermented", 60, "g", "umami"),
            ("soy_sauce_shoyu_reduced_sodium", 15, "ml", "seasoning"),
            ("base_soba_noodles_33e97c", 300, "g", "carbohydrate"),
            ("tofu_plain_pre_packaged", 350, "g", "plant_protein"),
            ("spinach_raw_baby", 150, "g", "vegetable"),
            ("green_onion_raw", 30, "g", "garnish"),
        ],
        steps=[
            "Porter 1,5 l d'eau à frémissement avec 150 g de shiitake émincés et 10 g de "
            "gingembre en lamelles, et laisser infuser 8 minutes.",
            "Ajouter 300 g de nouilles soba et 350 g de tofu en dés, et cuire 3 minutes.",
            "Hors du feu, délayer 60 g de miso dans une louche de bouillon et le reverser dans "
            "la casserole avec 15 ml de sauce soja : le miso ne doit pas bouillir.",
            "Répartir 150 g de jeunes pousses d'épinard dans les bols, verser la soupe "
            "brûlante et parsemer de 30 g d'oignon vert.",
        ],
        allow_similar=("miso", "soba"),
    ),
    recipe(
        rid="brkf_tofu_brouille_champignons_epinards_e2c946",
        fr="Tofu brouillé aux champignons et épinards sur pain complet",
        en="Tofu Scramble with Mushrooms and Spinach on Wholemeal Toast",
        cuisine="international", country="",
        dish="breakfast", servings=4, prep=5, cook=10,
        texture=("moelleux", "croustillant"), taste=("savoureux", "umami"),
        technique=("sauteing", "toasting"), difficulty="easy",
        desc="Un petit-déjeuner salé et rassasiant : tofu émietté et poêlé avec des champignons "
             "dorés, des épinards, du curcuma et de la levure nutritionnelle, sur des tartines "
             "de pain complet grillé.",
        compo=[
            ("tofu_plain_pre_packaged", 500, "g", "plant_protein"),
            ("button_mushroom_raw", 250, "g", "vegetable"),
            ("spinach_raw_baby", 100, "g", "vegetable"),
            ("nutritional_yeast_flakes", 20, "g", "umami"),
            ("turmeric_powder", 2, "g", "spice"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("wholemeal_bread_whole", 160, "g", "carbohydrate"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ],
        steps=[
            "Dorer 250 g de champignons émincés 4 minutes dans 20 ml d'huile d'olive à feu vif.",
            "Émietter 500 g de tofu dans la poêle avec 2 g de curcuma, 3 g de sel et 1 g de "
            "poivre, et cuire 3 minutes en remuant.",
            "Ajouter 100 g de jeunes pousses d'épinard et 20 g de levure nutritionnelle, et "
            "mélanger 1 minute jusqu'à ce que les épinards tombent.",
            "Griller 160 g de pain complet et servir le tofu brouillé dessus.",
        ],
        allow_similar=("brouille",),
    ),
    recipe(
        rid="brkf_porridge_soja_cacahuete_chanvre_58bd03",
        fr="Porridge au lait de soja, beurre de cacahuète, banane et chanvre",
        en="Soy Milk Porridge with Peanut Butter, Banana and Hemp Seeds",
        cuisine="international", country="",
        dish="breakfast", servings=4, prep=2, cook=8,
        texture=("cremeux", "onctueux"), taste=("doux", "légèrement_sucré"),
        technique=("simmering",), difficulty="easy",
        desc="Des flocons d'avoine cuits dans le lait de soja, avec beurre de cacahuète, banane, "
             "cannelle et graines de chanvre : environ 20 g de protéines par bol pour tenir "
             "jusqu'à midi.",
        compo=[
            ("oat_flakes_whole_seed", 180, "g", "carbohydrate"),
            ("soybean_milk_unsweetened_plant", 800, "ml", "liquid"),
            ("peanut_butter_natural_plant", 60, "g", "plant_protein"),
            ("hemp_seed_hulled", 40, "g", "garnish"),
            ("banana_raw", 240, "g", "fruit"),
            ("maple_syrup", 20, "ml", "sweetener"),
            ("cinnamon_powder", 2, "g", "spice"),
        ],
        steps=[
            "Porter 800 ml de lait de soja à frémissement avec 2 g de cannelle, ajouter 180 g "
            "de flocons d'avoine et cuire 5 minutes à feu doux en remuant.",
            "Répartir dans les bols, ajouter 60 g de beurre de cacahuète en spirale et 240 g "
            "de banane en rondelles.",
            "Parsemer de 40 g de graines de chanvre et arroser de 20 ml de sirop d'érable.",
        ],
        allow_similar=("porridge",),
    ),

    # ── C. Desserts vegan minute ──────────────────────────────────────────────────────────
    recipe(
        rid="dess_poires_poelees_erable_noix_6f3b21",
        fr="Poires poêlées à l'érable et aux noix, yaourt de soja",
        en="Maple Pan-Fried Pears with Walnuts and Soy Yogurt",
        cuisine="french", country="france",
        dish="dessert", servings=4, prep=5, cook=10,
        texture=("fondant", "croquant"), taste=("caramelise", "doux"),
        technique=("sauteing", "caramelizing"), difficulty="easy",
        desc="Des quartiers de poire dorés au beurre végétal et caramélisés au sirop d'érable "
             "et à la cannelle, servis tièdes sur un yaourt de soja, avec des noix grillées.",
        compo=[
            ("pear_raw_with_skin", 600, "g", "fruit"),
            ("vegan_butter", 20, "g", "fat"),
            ("maple_syrup", 40, "ml", "sweetener"),
            ("cinnamon_powder", 2, "g", "spice"),
            ("lemon_juice", 15, "ml", "acidity"),
            ("walnut_shelled_dried", 40, "g", "garnish"),
            ("soybean_yogurt_plain_plant", 300, "g", "dairy"),
        ],
        steps=[
            "Couper 600 g de poires en quartiers sans les peler, retirer le cœur et les arroser "
            "de 15 ml de jus de citron.",
            "Dorer les quartiers 5 minutes dans 20 g de beurre végétal à feu moyen.",
            "Ajouter 40 ml de sirop d'érable et 2 g de cannelle, et cuire encore 3 minutes en "
            "arrosant les poires jusqu'à ce qu'elles soient laquées.",
            "Griller 40 g de noix 2 minutes à sec, puis servir les poires tièdes sur 300 g de "
            "yaourt de soja, avec le sirop et les noix.",
        ],
        allow_similar=("poires",),
    ),
    recipe(
        rid="dess_glace_minute_banane_cacao_9a52e7",
        fr="Glace minute à la banane, cacao et beurre de cacahuète",
        en="Instant Banana, Cocoa and Peanut Butter Ice Cream",
        cuisine="international", country="",
        dish="dessert", servings=4, prep=5, rest=240, cook=0,
        texture=("cremeux", "onctueux"), taste=("doux", "chocolaté"),
        technique=("blending",), difficulty="easy",
        desc="Des bananes coupées en rondelles et congelées d'avance (le repos de quatre heures), "
             "mixées avec du cacao, du beurre de cacahuète et un trait de lait de soja : une "
             "glace onctueuse en cinq minutes de travail, sucrée d'une seule cuillère de sirop "
             "d'érable.",
        compo=[
            ("banana_raw", 480, "g", "fruit"),
            ("cocoa_powder_unsweetened", 15, "g", "flavor"),
            ("peanut_butter_natural_plant", 30, "g", "fat"),
            ("soybean_milk_unsweetened_plant", 60, "ml", "liquid"),
            ("maple_syrup", 10, "ml", "sweetener"),
        ],
        steps=[
            "Couper 480 g de bananes bien mûres en rondelles et les congeler à plat, d'avance "
            "(au moins 4 heures, elles se gardent un mois au congélateur).",
            "Mixer les rondelles encore congelées avec 15 g de cacao, 30 g de beurre de "
            "cacahuète, 60 ml de lait de soja et 10 ml de sirop d'érable, en raclant les "
            "parois, jusqu'à une texture de glace à l'italienne.",
            "Servir aussitôt.",
        ],
        # « Glace vegan à la vanille et au lait de coco » : autre dessert (turbinée, coco)
        allow_similar=("glace", "minute"),
    ),
    recipe(
        rid="dess_pommes_poelees_crumble_avoine_c7e408",
        fr="Pommes poêlées et crumble express aux flocons d'avoine",
        en="Pan-Fried Apples with Quick Oat Crumble",
        cuisine="french", country="france",
        dish="dessert", servings=4, prep=5, cook=10,
        texture=("fondant", "croustillant"), taste=("caramelise", "doux"),
        technique=("sauteing", "toasting"), difficulty="easy",
        desc="Le goût du crumble sans le four : des pommes poêlées à la cannelle, couvertes "
             "d'un mélange de flocons d'avoine, de noisettes et de sucre de coco dorés à la "
             "poêle dans le beurre végétal.",
        compo=[
            ("apple_raw_with_skin", 600, "g", "fruit"),
            ("vegan_butter", 40, "g", "fat"),
            ("coconut_sugar", 40, "g", "sweetener"),
            ("cinnamon_powder", 3, "g", "spice"),
            ("lemon_juice", 10, "ml", "acidity"),
            ("oat_flakes_whole_seed", 80, "g", "carbohydrate"),
            ("hazelnut_raw_unsalted", 30, "g", "garnish"),
        ],
        steps=[
            "Couper 600 g de pommes en dés, les cuire 6 minutes dans 20 g de beurre végétal "
            "avec 3 g de cannelle, 20 g de sucre de coco et 10 ml de jus de citron.",
            "Dans une autre poêle, faire dorer 4 minutes à feu moyen 80 g de flocons d'avoine "
            "et 30 g de noisettes concassées avec 20 g de beurre végétal et 20 g de sucre de "
            "coco, en remuant, jusqu'à ce que le mélange sente le biscuit.",
            "Répartir les pommes dans des coupes et les couvrir de crumble.",
        ],
        allow_similar=("crumble",),
    ),
    recipe(
        rid="dess_agrumes_hiver_pistaches_fleur_oranger_14d9b3",
        fr="Salade d'agrumes d'hiver à la fleur d'oranger et aux pistaches",
        en="Winter Citrus Salad with Orange Blossom and Pistachios",
        cuisine="moroccan", country="morocco",
        dish="dessert", servings=4, prep=10, cook=0,
        texture=("frais", "croquant"), taste=("acidule", "frais"),
        technique=("assembly",), difficulty="easy",
        desc="Oranges et pamplemousse pelés à vif et tranchés, arrosés d'un sirop d'agave à la "
             "fleur d'oranger et à la cannelle, avec des pistaches et de la menthe : le dessert "
             "frais des repas d'hiver.",
        compo=[
            ("orange_raw", 600, "g", "fruit"),
            ("grapefruit_raw", 300, "g", "fruit"),
            ("agave_syrup", 20, "ml", "sweetener"),
            ("orange_blossom_water", 10, "ml", "flavor"),
            ("cinnamon_powder", 1, "g", "spice"),
            ("pistachio_nuts_raw", 40, "g", "garnish"),
            ("mint_fresh_herb", 5, "g", "herb"),
        ],
        steps=[
            "Peler à vif 600 g d'oranges et 300 g de pamplemousse et les couper en rondelles, "
            "en recueillant le jus.",
            "Mélanger le jus avec 20 ml de sirop d'agave et 10 ml d'eau de fleur d'oranger.",
            "Disposer les rondelles sur un plat, arroser du sirop et saupoudrer de 1 g de "
            "cannelle.",
            "Parsemer de 40 g de pistaches concassées et de 5 g de menthe ciselée.",
        ],
        # « Carpaccio betterave agrumes » : une entrée salée, pas ce dessert
        allow_similar=("agrumes", "pistaches"),
    ),
]
