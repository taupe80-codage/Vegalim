"""Lot 5 : tartines, couscous (semoule sèche), galettes, currys."""

PATCHES = {
    "brkf_tartines_beurre_amande_ba_9f16cc": [
        ("del", "butter_sup80pct"),
        ("txt", "Remplacez le miel par un filet de sirop de dattes ou de coco et servez sans attendre: la chaleur du pain toasté et la fraîcheur de la banane sont essentielles pour apprécier pleinement ce petit-déjeuner.",
         "Arrosez d'un filet de miel et servez sans attendre."),
        ("time", 5, 0, 3),
    ],
    "brkf_tartines_ricotta_figue_mi_6f7590": [
        ("ing", "fig_dried", "fig_raw", 200),
        ("qty", "honey", 15.0),
        ("txt", "le fromage râpé", "la ricotta"),
        ("txt", "Couper les figues séchées en quartiers et les réhydrater si nécessaire dans de l'eau tiède pendant 5 minutes, jusqu'à ce qu'elles soient tendres et parfumées.",
         "Couper les figues fraîches en quartiers."),
        ("txt", "arrosez de sirop de fleurs d'oranger, et parsemez de thym frais concassé", "arrosez de miel et parsemez de thym séché"),
        ("step-", "Garnissez avec des feuilles de thym frais et servez sans attendre"),
    ],
    "brkf_toast_avocat_graines_dfc001": [
        ("qty", "sourdough_bread", 120),
        ("txt", "les tranches de pain complet", "les tranches de pain au levain"),
    ],
    # semoule sèche (fiche « couscous à cuire » 366 kcal) au lieu du couscous cuit
    "couscous_couscous_mediterraneenne_bdf9d9": [
        ("ing", "couscous_cooked_seed_unsalted", "couscous_to_cook_seed_dried"),
        ("del", "vegetable_stock_dried"),
        ("delq", "water", 800.0),
        ("add", "lemon_juice", 30, "ml", "acid"),
        ("add", "table_salt_unenriched", 4, "g", "seasoning"),
        ("add", "parsley_fresh_herb", 15, "g", "herb"),
        ("steps", [
            "Verser 200 ml d'eau bouillante salée sur 200 g de semoule dans un grand saladier, couvrir et laisser gonfler 5 minutes.",
            "Égrainer à la fourchette en incorporant 20 ml d'huile d'olive, puis laisser refroidir.",
            "Couper les carottes et les courgettes en petits dés de 1 cm, les tomates en dés, et émincer finement l'oignon.",
            "Mélanger la semoule froide avec les légumes et les pois chiches égouttés.",
            "Assaisonner avec le jus de citron et le sel, ajouter le persil ciselé et mélanger délicatement.",
            "Réfrigérer 30 minutes et servir frais.",
        ]),
        ("time", 15, 30, 0),
    ],
    "couscous_tfaya_classic_k1d1p6": [
        ("ing", "couscous_cooked_seed_unsalted", "couscous_to_cook_seed_dried"),
        ("add", "water", 380, "ml", "liquid"),
        ("txt", "arroser de 200 ml d'eau bouillante salée", "arroser de 300 ml d'eau bouillante salée"),
        ("txt", "4,5 g de curcuma", "3,8 g de curcuma"),
    ],
    "couscous_tfaya_quick_ee5f20": [
        ("ing", "couscous_cooked_seed_unsalted", "couscous_to_cook_seed_dried"),
        ("title", "Couscous aux légumes express"),
        ("step-", "levure nutritionnelle râpée"),
        ("step-", "Accompagnez ce plat de pain complet ou de crackers"),
    ],
    "couscous_tfaya_vegan_65aba6": [
        ("ing", "couscous_cooked_seed_unsalted", "couscous_to_cook_seed_dried"),
        ("add", "water", 400, "ml", "liquid"),
        ("del", "vegan_butter"),
        ("qty", "maple_syrup", 40),
        ("txt", "80ml de sirop d'érable", "40ml de sirop d'érable"),
        ("txt", " et d'un filet d'huile d'olive. Servir sans attendre, pour apprécier les saveurs et les textures de ce plat créatif et délicieux, avec la chaleur et la fraîcheur des ingrédients.",
         ". Servir chaud."),
        ("step-", "Servir chaud et apprécier les saveurs"),
    ],
    "couscous_traditionnel_132078": [
        ("ing", "couscous_cooked_seed_unsalted", "couscous_to_cook_seed_dried"),
    ],
    "crepe_galette_de_teff_a1a8d3": [
        ("qty", "sunflower_oil_plant", 15),
        ("txt", "Ajouter 45 ml d'huile végétale pour graisser légèrement la surface.", "Graisser légèrement la surface avec un peu d'huile (15 ml pour toute la pâte)."),
    ],
    "crepe_galettes_de_courgette_ult_669679": [
        ("title", "Galettes de courgette"),
        ("txt", "80 g d'oignon pice haché, 65 g de farine de blé végétal", "80 g d'oignon haché, 65 g de farine de blé"),
        ("txt", "Servir chaud avec un yaourt à la menthe fraîche.", "Servir chaud avec un yaourt végétal à la menthe."),
    ],
    "crepe_pancakes_sales_ultra_stru_1e8bd8": [
        ("title", "Pancakes salés à l'oignon rouge"),
        ("txt", "de yaourt ou d'une sauce végétarien de votre choix", "de yaourt végétal ou d'une sauce de votre choix"),
        ("step-", "Contrôler la texture en insérant une lame"),
    ],
    "curry_aubergine_sri_lanka_bf8bcd": [
        ("del", "mustard"),
        ("step-", "Ajouter 15 g de moutarde de Dijon"),
        ("txt", "sur du riz basmati, dans un bol préchauffé.", "sur du riz basmati."),
    ],
    "curry_baingan_bharta_d54d1c": [
        ("ing", "coriander_spice_leaf_dried", "coriander_spice_seed", 5),
        ("txt", "12g de coriandre moulue", "5g de coriandre moulue"),
        ("txt", "Servir aussitôt dans des bols préchauffés, garni de coriandre fraîche ciselée et d'un filet d'huile de tournesol. Accompagner d'un pain pita tiède ou de riz basmati.",
         "Servir aussitôt, accompagné de naan ou de riz basmati."),
    ],
    "curry_chickpea_k5x2p9": [
        ("add", "water", 200, "ml", "liquid"),
        ("add", "lemon_juice", 15, "ml", "acid"),
    ],
    "curry_chickpea_spinach_k6518f8": [
        ("txt", "30 grammes de piment, 6 grammes de cumin en graines et 10 grammes de garam masala", "30 grammes de piment et 10 grammes de garam masala"),
        ("step-", "Parsemer de levure nutritionnelle pour un effet fromage"),
    ],
    "curry_d_aubergine_sri_lankais_72254d": [
        ("step-", "Présentez le plat avec élégance et simplicité"),
    ],
    "curry_de_pommes_de_terre_et_bam_e5161e": [
        ("add", "cumin_spice_seed", 3, "g", "spice"),
        ("add", "yellow_mustard_spice_seed", 3, "g", "spice"),
        ("add", "water", 200, "ml", "liquid"),
        ("qty", "onion_raw", 150),
        ("qty", "coconut_oil_plant", 30),
        ("txt", "Chauffer 45ml d'huile de coco", "Chauffer 30ml d'huile de coco"),
        ("txt", "Ajouter 300g d'oignon émincé", "Ajouter 150g d'oignon émincé"),
        ("txt", "Verser 200ml d'eau et ajouter 5g de sel.", "Ajouter 480g de tomates concassées, 200ml d'eau et 5g de sel."),
        ("txt", "Ajouter 480g de tomates concassées et rectifier l'assaisonnement avec du sel si nécessaire. Garnir de coriandre fraîche.",
         "Rectifier l'assaisonnement et garnir de coriandre fraîche."),
        ("step-", "Observer la sauce onctueuse et parfumée"),
        ("step-", "Présenter le plat avec les couleurs vives des légumes"),
    ],
    "curry_de_pommes_de_terre_et_pet_9271d8": [
        ("ing", "snow_peas_raw", "green_peas_boiled_frozen_salted"),
        ("add", "turmeric_powder", 3, "g", "spice"),
        ("add", "coriander_spice_seed", 3, "g", "spice"),
        ("add", "water", 200, "ml", "liquid"),
        ("qty", "onion_raw", 150),
        ("qty", "coconut_oil_plant", 25),
        ("txt", "200 ml d'eau de coco", "200 ml d'eau"),
        ("txt", "les pois mange-tout surgelés", "les petits pois surgelés"),
        ("txt", "les pois mange-tout chauds", "les petits pois chauds"),
    ],
    "curry_green_curry_tofu_2a30dd": [
        ("qty", "onion_raw", 150),
        ("txt", "dans 30 ml d'huile de coco à 180°C", "dans 30 ml d'huile de coco à feu moyen-vif"),
        ("txt", "300 g d'oignon finement émincé", "150 g d'oignon finement émincé"),
        ("txt", " et de graines de sésame pour une touche de croquant", ""),
    ],
    "curry_japanese_4533d1": [
        ("title", "Curry japonais rapide"),
        ("qty", "onion_raw", 150),
        ("del", "table_salt_unenriched"),  # roux et bouillon déjà salés (Na 1240 mg)
        ("txt", "300g d'oignon jaune en cubes petits", "150g d'oignon jaune en petits cubes"),
        ("txt", "Assaisonner le curry de sel et de poivre au goût", "Goûter et poivrer le curry"),
        ("txt", "de riz basmati cuit ou de nouilles de riz", "de riz japonais"),
    ],
    # texte sans curry ni bouillon, beurre annoncé « huile »
    "curry_japanese_classic_v3_m8q2z4": [
        ("steps", [
            "Éplucher et couper les carottes et les pommes de terre en gros cubes, émincer l'oignon, hacher l'ail et le gingembre.",
            "Dans une cocotte, faire fondre 25 g de beurre et faire revenir l'oignon 6 minutes à feu moyen jusqu'à ce qu'il soit translucide. Ajouter l'ail et le gingembre, cuire 1 minute.",
            "Ajouter les carottes et les pommes de terre, faire revenir 3 minutes, puis verser 850 ml d'eau chaude et le bouillon en poudre. Porter à ébullition en écumant, couvrir et cuire à feu moyen 18 à 20 minutes, jusqu'à ce que les légumes soient tendres.",
            "Pendant ce temps, préparer le roux : faire fondre 35 g de beurre dans une poêle, ajouter 35 g de farine et cuire en remuant 5 à 8 minutes, jusqu'à ce qu'il soit brun clair et sente la noisette. Hors du feu, incorporer 7,5 g de curry en poudre et 5 g de garam masala.",
            "Délayer le roux dans une louche de bouillon, puis l'incorporer aux légumes en remuant jusqu'à dissolution complète. Ajouter 15 g de sucre.",
            "Laisser mijoter 5 minutes à feu doux en remuant, jusqu'à ce que la sauce épaississe et devienne brillante. Rectifier l'assaisonnement.",
            "Servir bien chaud sur du riz japonais.",
        ]),
        ("time", 20, 5, 35),
    ],
}
