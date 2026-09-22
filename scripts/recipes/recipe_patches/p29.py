"""Lot 29 : sunomono, mastava, spring rolls, tacu tacu, tteokbokki, plov ouzbek."""

PATCHES = {
    # sunomono : concombre CRU, pas blanchi puis saisi
    "rice_salade_de_concombre_japonaise_d66133": [
        ("steps", [
            "Tailler 350 g de concombre en fines rondelles de 2 mm, les laisser dégorger 10 minutes dans une passoire, puis les presser doucement pour éliminer l'eau.",
            "Préparer la vinaigrette en fouettant 30 ml de vinaigre de riz, 45 ml de sauce soja et 30 ml d'huile de sésame, jusqu'à obtenir une émulsion lisse.",
            "Incorporer 11 g de gingembre frais râpé finement à la vinaigrette.",
            "Mélanger les rondelles de concombre à la vinaigrette, puis laisser mariner 15 minutes au frais.",
            "Garnir de 20 g de graines de sésame torréfiées et servir frais.",
        ]),
        ("time", 10, 15, 0),
    ],
    # 300 g de riz + 600 g de pommes de terre dans 750 ml : ce n'était pas une soupe
    "rice_soupe_de_riz_mastava_6db971": [
        ("qty", "white_rice_short_grain_seed_dried", 150),
        ("qty", "potato_raw_flesh", 400),
        ("qty", "water", 1400),
        ("qty", "table_salt_unenriched", 3),
        ("add", "tomato_raw_ripe", 300, "g", "vegetable"),
        ("txt", "600g de pomme de terre crue en dés", "400g de pomme de terre crue en dés"),
        ("txt", "Incorporer 300g de riz rond rincé", "Incorporer 150g de riz rond rincé"),
        ("txt", "Verser 750 ml de bouillon de légumes chaud et porter à ébullition. Ensuite, enfourner pendant 25 minutes à 180°C, jusqu'à ce que le riz soit cuit et les légumes soient tendres, en vérifiant régulièrement la texture.",
         "Ajouter 300 g de tomates concassées, verser 1,4 L de bouillon de légumes chaud et porter à ébullition, puis laisser mijoter 25 minutes à couvert, jusqu'à ce que le riz soit cuit et les légumes tendres."),
        ("step-", "Présenter dans des bols préchauffés"),
    ],
    "rice_spring_rolls_45fdfa": [
        ("qty", "green_cabbage_raw", 200),
        ("qty", "button_mushroom_raw", 200),
        ("qty", "sesame_oil_plant", 20),
        ("qty", "soy_sauce_shoyu_reduced_sodium", 30),
        ("qty", "table_salt_unenriched", 3),
        ("steps", [
            "Réhydrater 150 g de vermicelles de riz 5 minutes dans l'eau chaude, les égoutter et les couper en tronçons.",
            "Tailler la carotte en julienne, puis émincer le chou vert, les champignons et l'oignon jaune.",
            "Faire sauter les légumes 4 minutes à feu vif dans 20 ml d'huile de sésame avec 9 g d'ail haché, jusqu'à ce qu'ils soient tendres, saler avec 3 g de sel, puis laisser refroidir.",
            "Mélanger les légumes refroidis avec les vermicelles et 30 ml de sauce soja.",
            "Réhydrater les galettes de riz une par une 15 à 20 secondes dans l'eau tiède, jusqu'à ce qu'elles soient souples.",
            "Déposer la garniture au bas de chaque galette, replier les côtés et rouler serré.",
            "Servir dans les 30 minutes, avec une sauce nuoc-cham.",
        ]),
    ],
    # tacu tacu = galette de riz et haricots écrasés poêlée, pas un pilaf
    "rice_tacu_tacu_9e0073": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 10),
        ("qty", "table_salt_unenriched", 3),
        ("steps", [
            "Cuire 300 g de riz long grain dans 750 ml de bouillon végétal, à couvert et à feu doux, pendant 15 minutes, puis le laisser refroidir : il doit rester légèrement collant.",
            "Chauffer 25 ml d'huile d'olive dans une poêle et faire revenir l'oignon émincé 5 minutes jusqu'à ce qu'il soit translucide, puis ajouter 9 g d'ail haché et cuire 1 minute.",
            "Ajouter 300 g de haricots rouges cuits et les écraser grossièrement à la fourchette avec l'oignon, 3 minutes à feu moyen.",
            "Mélanger la purée de haricots au riz refroidi, saler avec 3 g de sel et ajouter 10 g de coriandre fraîche ciselée.",
            "Former quatre galettes ovales bien tassées.",
            "Chauffer les 20 ml d'huile restants dans une poêle antiadhésive et dorer les galettes 4 minutes de chaque côté, jusqu'à ce qu'une croûte dorée se forme.",
            "Servir chaud, avec une salsa criolla.",
        ]),
    ],
    # `puffed_rice_cakes` (galettes soufflées, 385 kcal) pour des tteok : fiche `tteok` ajoutée le 2026-09-22
    "rice_tteokbokki_0861f2": [
        ("ing", "puffed_rice_cakes", "tteok", 400, "g"),
        ("add", "water", 400, "ml", "liquid"),
        ("add", "vegetable_stock_dried", 5, "g", "ingredient"),
        ("txt", "Plonger les gâteaux de riz (tteok) dans l'eau froide pendant 10 minutes pour les ramollir s'ils sont congelés, vérifiant qu'ils soient bien égouttés avant la suite de la préparation.",
         "Faire tremper 400 g de tteok (bâtonnets de gâteau de riz) 10 minutes dans l'eau froide s'ils sont durs, puis les égoutter."),
        ("txt", "15 g de sucre blanc", "10 g de sucre blanc"),
        ("step-", "Assaisonner avec du sel et du poivre pour équilibrer les saveurs"),
        ("txt", "Servir sans attendre, en accompagnant d'une garniture de feuilles de coriandre fraîche pour une touche de couleur et de fraîcheur, et en présentant dans des bols préchauffés pour conserver la chaleur.",
         "Servir sans attendre, parsemé d'oignons verts émincés."),
    ],
    # 300 g d'épinards dans un plov : ce sont des carottes
    "rice_uzbek_vegetable_plov_2ff045": [
        ("ing", "spinach_raw_baby", "carrot_raw", 300),
        ("ing", "coriander_spice_leaf_dried", "coriander_raw_fresh_herb", 10),
        ("qty", "table_salt_unenriched", 3),
        ("txt", "Ajoutez les gousses d'ail écrasées et les épices (cumin et coriandre), puis faites sauter",
         "Ajoutez 300 g de carotte en bâtonnets, les gousses d'ail écrasées et 3 g de cumin, puis faites sauter"),
        ("txt", "pour que les grains soient bien enrobés des saveurs, avec une texture crémeuse et une odeur de riz cuit",
         "pour que les grains soient bien enrobés des saveurs"),
        ("txt", "Ajoutez les épinards crus et mélangez délicatement pour les incorporer au plov, en prenant soin de ne pas écraser les feuilles, avec une texture fraîche et une odeur d'épinards crus.",
         "Ajoutez 10 g de coriandre fraîche ciselée et mélangez délicatement."),
        ("txt", "garni de gousses d'ail rôties et de feuilles d'épinards fraîches", "garni de coriandre fraîche ciselée"),
    ],
}
