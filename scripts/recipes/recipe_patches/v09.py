"""Variantes 9 : bannock, boulettes suédoises, carottes à l'érable, crumble, crêpes coréennes, dal makhani, enchiladas."""

VARIANTS = {
    # ── Bannock : au four / frit aux bleuets vegan ──
    "bread_bannock_e03ffe": [
        ("title", "Bannock au four, pain des Premières Nations"),
        ("desc", "Pain rapide sans levure des Premières Nations du Canada : farine, poudre à lever, beurre et eau, "
                 "façonné en galette épaisse et cuit au four jusqu'à ce qu'il soit doré."),
        ("origin", {"cuisine": "canadian"}),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 250, "g", "carbohydrate"),
            ("baking_powder", 10, "g", "leavening"),
            ("butter_sup80pct", 40, "g", "fat_cooking"),
            ("water", 170, "ml", "ingredient"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("strawberry_jam", None, "2 cuillères à soupe", "serving_suggestion"),
        ]),
        ("steps", [
            "Préchauffer le four à 200°C.",
            "Mélanger 250 g de farine, 10 g de poudre à lever et 3 g de sel, puis sabler avec 40 g de beurre froid du bout des doigts.",
            "Ajouter 170 ml d'eau et mélanger juste assez pour former une pâte souple, sans pétrir.",
            "Façonner une galette de 2 cm d'épaisseur sur une plaque farinée et la piquer à la fourchette.",
            "Cuire 25 minutes, jusqu'à ce que le dessous sonne creux. Servir tiède, coupé en parts.",
        ]),
        ("time", 10, 0, 25),
    ],
    "snack_bannock_vegan_46a1a8": [
        ("title", "Bannock frit aux bleuets (vegan)"),
        ("desc", "Version poêlée du bannock, comme dans les pow-wow : petits pains à la pâte aux bleuets sauvages, "
                 "dorés à l'huile, moelleux à cœur."),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 200, "g", "carbohydrate"),
            ("baking_powder", 10, "g", "leavening"),
            ("blueberry_raw", 100, "g", "ingredient"),
            ("white_sugar", 15, "g", "sweetener"),
            ("vegan_butter", 20, "g", "fat_cooking"),
            ("water", 140, "ml", "ingredient"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("sunflower_oil_plant", 30, "ml", "fat"),
        ]),
        ("steps", [
            "Mélanger 200 g de farine, 10 g de poudre à lever, 15 g de sucre et 2 g de sel, puis sabler avec 20 g de beurre végétal.",
            "Ajouter 140 ml d'eau, puis incorporer délicatement 100 g de bleuets.",
            "Former 8 petites galettes de 1,5 cm d'épaisseur.",
            "Les cuire dans une poêle avec 30 ml d'huile de tournesol, 4 minutes de chaque côté à feu moyen, jusqu'à ce qu'elles soient dorées.",
            "Égoutter sur du papier absorbant et servir tiède.",
        ]),
        ("time", 10, 0, 15),
    ],

    # ── Boulettes suédoises : köttbullar aux pois chiches sauce crème / vegan lentilles-champignons sauce brune ──
    "dal_boulettes_suedoises_2ac55d": [
        ("title", "Köttbullar végétariennes aux pois chiches, sauce crème et airelles"),
        ("desc", "Boulettes à la suédoise de pois chiches, oignon et muscade, nappées d'une sauce à la crème "
                 "et à la sauce soja, servies avec des airelles et une purée."),
        ("compo", [
            ("chickpea_boiled", 400, "g", "plant_protein", "cooked"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("egg_raw", 55, "g", "ingredient"),
            ("breadcrumbs", 50, "g", "ingredient"),
            ("nutmeg_spice", 1, "g", "seasoning"),
            ("allspice_powder", 1, "g", "seasoning"),
            ("sunflower_oil_plant", 30, "ml", "fat"),
            ("butter_sup80pct", 15, "g", "fat"),
            ("wheat_all_purpose_flour_unenriched_unbleached", 10, "g", "binder"),
            ("cream_heavy_refrigerated_18pct", 150, "ml", "sauce"),
            ("water", 150, "ml", "liquid"),
            ("soy_sauce_shoyu_reduced_sodium", 10, "ml", "seasoning"),
            ("lingonberry", 60, "g", "condiment"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("potato_raw_flesh", None, "1 portion de purée", "serving_suggestion"),
        ]),
        ("steps", [
            "Mixer grossièrement 400 g de pois chiches avec 100 g d'oignon, 1 œuf (55 g), 50 g de chapelure, 1 g de muscade, 1 g de piment de la Jamaïque, 3 g de sel et 1 g de poivre.",
            "Former 24 boulettes de la taille d'une noix et les réfrigérer 15 minutes.",
            "Les dorer dans 30 ml d'huile, 8 minutes, en les roulant. Réserver.",
            "Sauce : faire fondre 15 g de beurre, ajouter 10 g de farine, puis 150 ml d'eau, 150 ml de crème et 10 ml de sauce soja, et cuire 3 minutes.",
            "Remettre les boulettes 2 minutes dans la sauce et servir avec 60 g d'airelles et une purée.",
        ]),
        ("time", 20, 15, 20),
    ],
    "dal_boulettes_suedoises_vegan_fea9f6": [
        ("title", "Boulettes suédoises aux lentilles et champignons, sauce brune (vegan)"),
        ("origin", {"country": "sweden", "region": "svealand"}),
        ("desc", "Boulettes végétales de lentilles et de champignons au thym, liées au lin, servies dans une "
                 "sauce brune au lait d'avoine et à la sauce soja."),
        ("compo", [
            ("green_lentil_dried", 150, "g", "plant_protein", "dried"),
            ("button_mushroom_raw", 250, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("breadcrumbs", 60, "g", "ingredient"),
            ("flaxseed_linseed_ground", 10, "g", "binder"),
            ("thyme_dried_herb", 1, "g", "herb"),
            ("nutmeg_spice", 1, "g", "seasoning"),
            ("sunflower_oil_plant", 40, "ml", "fat"),
            ("wheat_all_purpose_flour_unenriched_unbleached", 15, "g", "binder"),
            ("oat_milk_refrigerated_plain_plant", 200, "ml", "sauce"),
            ("soy_sauce_shoyu_reduced_sodium", 20, "ml", "seasoning"),
            ("water", 450, "ml", "liquid"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Cuire 150 g de lentilles vertes dans 400 ml d'eau, 25 minutes, puis les égoutter. Mélanger 10 g de lin moulu avec 30 ml d'eau.",
            "Faire revenir 100 g d'oignon et 250 g de champignons hachés dans 10 ml d'huile, 8 minutes, jusqu'à évaporation.",
            "Mixer grossièrement lentilles, champignons, lin, 60 g de chapelure, 1 g de thym, 1 g de muscade, 2 g de sel et 1 g de poivre, puis former 24 boulettes.",
            "Les dorer dans 25 ml d'huile, 8 minutes. Réserver.",
            "Sauce brune : faire roussir 15 g de farine dans 5 ml d'huile, puis ajouter 200 ml de lait d'avoine, 20 ml d'eau et 20 ml de sauce soja, et cuire 3 minutes. Y réchauffer les boulettes.",
        ]),
        ("time", 25, 0, 45),
    ],

    # ── Carottes : glacées au beurre et à l'érable / rôties érable-cumin-sésame vegan ──
    "main_carottes_glacees_a_lerabl_87d5f0": [
        ("title", "Carottes glacées au beurre et à l'érable du Québec"),
        ("desc", "Carottes cuites à couvert puis glacées au beurre et au sirop d'érable jusqu'à ce qu'elles "
                 "brillent, parfumées au thym frais."),
        ("origin", {"cuisine": "canadian", "country": "canada", "region": "quebec", "city": ""}),
    ],
    "side_carottes_glacees_a_lerabl_1d1c44": [
        ("title", "Carottes rôties à l'érable, cumin et sésame (vegan)"),
        ("desc", "Carottes entières rôties au four avec sirop d'érable, cumin et huile d'olive, "
                 "parsemées de graines de sésame grillées."),
        ("compo", [
            ("carrot_raw", 600, "g", "ingredient"),
            ("maple_syrup", 40, "g", "sweetener"),
            ("olive_oil_plant", 25, "ml", "fat"),
            ("cumin_spice_seed", 2, "g", "spice"),
            ("sesame_seed_hulled_dried", 10, "g", "garnish"),
            ("thyme_fresh_herb", 2, "g", "ingredient"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ]),
        ("steps", [
            "Préchauffer le four à 210°C.",
            "Mélanger 600 g de carottes épluchées et coupées en deux dans la longueur avec 25 ml d'huile d'olive, 2 g de cumin, 2 g de thym et 2 g de sel.",
            "Rôtir 25 minutes, puis arroser de 40 g de sirop d'érable et rôtir encore 8 minutes.",
            "Parsemer de 10 g de graines de sésame grillées et servir.",
        ]),
        ("time", 10, 0, 33),
    ],

    # ── Crumble : pommes-myrtilles au beurre salé / myrtilles-citron-amandes vegan ──
    "main_crumble_aux_myrtilles_5f7d47": [
        ("title", "Crumble pommes-myrtilles au beurre salé"),
        ("desc", "Crumble à l'anglaise : pommes fondantes et myrtilles sous une pâte sablée croustillante "
                 "au beurre salé et aux flocons d'avoine."),
        ("compo", [
            ("blueberry", 300, "g", "ingredient"),
            ("apple_raw", 300, "g", "ingredient"),
            ("wheat_all_purpose_flour_unenriched_unbleached", 100, "g", "base"),
            ("oat_flakes_whole_seed", 60, "g", "base"),
            ("brown_sugar", 60, "g", "sweetener"),
            ("butter_salted", 90, "g", "fat"),
            ("cinnamon", 1, "g", "spice"),
            ("vanilla_ice_cream", None, "1 boule", "serving_suggestion"),
        ]),
        ("steps", [
            "Préchauffer le four à 180°C.",
            "Couper 300 g de pommes en dés, les mélanger avec 300 g de myrtilles et 1 g de cannelle, puis les étaler dans un plat.",
            "Sabler 100 g de farine, 60 g de flocons d'avoine et 60 g de sucre roux avec 90 g de beurre salé froid.",
            "Répartir la pâte en miettes sur les fruits.",
            "Cuire 35 minutes, jusqu'à ce que le dessus soit doré et le jus bouillonne. Servir tiède.",
        ]),
        ("time", 15, 0, 35),
    ],
    "dessert_crumble_aux_myrtilles_veg_15390f": [
        ("title", "Crumble myrtilles-citron aux amandes et à l'avoine (vegan)"),
        ("desc", "Myrtilles relevées de zeste de citron sous un crumble d'avoine, d'amandes concassées et de sucre "
                 "de coco, lié à l'huile de coco."),
        ("compo", [
            ("blueberry", 500, "g", "ingredient"),
            ("lemon_peel_raw", 4, "g", "aromatic"),
            ("cornstarch_flour", 10, "g", "thickener"),
            ("oat_flakes_whole_seed", 80, "g", "base"),
            ("wheat_all_purpose_flour_unenriched_unbleached", 60, "g", "base"),
            ("almond_raw_with_skin_unsalted", 40, "g", "base"),
            ("coconut_sugar", 60, "g", "sweetener"),
            ("coconut_oil_plant", 70, "ml", "fat"),
        ]),
        ("steps", [
            "Préchauffer le four à 180°C.",
            "Mélanger 500 g de myrtilles avec 4 g de zeste de citron et 10 g de fécule de maïs, puis les étaler dans un plat.",
            "Mélanger 80 g de flocons d'avoine, 60 g de farine, 40 g d'amandes concassées et 60 g de sucre de coco, puis ajouter 70 ml d'huile de coco fondue jusqu'à former des miettes.",
            "Répartir sur les fruits et cuire 30 minutes, jusqu'à ce que le dessus soit doré.",
        ]),
        ("time", 10, 0, 30),
    ],

    # ── Crêpes coréennes : pajeon à l'œuf / kimchijeon vegan ──
    "egg_crepe_coreenne_aux_oignons_ver_356ac2": [
        ("title", "Pajeon aux oignons verts, sauce soja vinaigrée"),
        ("desc", "La crêpe coréenne des jours de pluie : pâte fine à l'œuf couvrant une nappe d'oignons verts "
                 "entiers, poêlée jusqu'à être croustillante, trempée dans une sauce soja au vinaigre."),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 150, "g", "carbohydrate"),
            ("rice_flour", 50, "g", "carbohydrate"),
            ("egg_raw", 110, "g", "ingredient"),
            ("water", 250, "ml", "ingredient"),
            ("green_onion_raw", 200, "g", "ingredient"),
            ("vegetable_oil_plant", 45, "ml", "fat"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("soy_sauce_shoyu_reduced_sodium", 30, "ml", "condiment"),
            ("white_vinegar_liquid_distilled", 15, "ml", "condiment"),
            ("gochugaru", 1, "g", "spice"),
        ]),
        ("steps", [
            "Fouetter 150 g de farine, 50 g de farine de riz, 2 œufs (110 g), 250 ml d'eau glacée et 2 g de sel en une pâte fluide.",
            "Couper 200 g d'oignons verts en tronçons de 10 cm.",
            "Chauffer 15 ml d'huile dans une grande poêle, y ranger un tiers des oignons verts, puis couvrir d'un tiers de la pâte.",
            "Cuire 4 minutes à feu moyen-vif, retourner, ajouter un filet d'huile et cuire encore 3 minutes en appuyant. Répéter deux fois.",
            "Sauce : mélanger 30 ml de sauce soja, 15 ml de vinaigre et 1 g de gochugaru. Servir la crêpe coupée en carrés.",
        ]),
        ("time", 10, 0, 25),
    ],
    "snack_crepe_coreenne_aux_oignon_a45536": [
        ("title", "Kimchijeon, crêpe croustillante au kimchi (vegan)"),
        ("flag", "kid_friendly", False),
        ("desc", "Crêpe coréenne sans œuf au kimchi haché et à son jus, avec oignons verts et fécule pour le "
                 "croustillant, poêlée à l'huile de sésame."),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 150, "g", "carbohydrate"),
            ("potato_starch_flour", 30, "g", "thickener"),
            ("base_kimchi_61791a", 250, "g", "ingredient"),
            ("green_onion_raw", 40, "g", "ingredient"),
            ("water", 180, "ml", "ingredient"),
            ("gochugaru", 2, "g", "spice"),
            ("sesame_oil_plant", 15, "ml", "fat"),
            ("sunflower_oil_plant", 25, "ml", "fat"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Hacher 250 g de kimchi en gardant son jus, émincer 40 g d'oignons verts.",
            "Mélanger 150 g de farine, 30 g de fécule, 180 ml d'eau glacée, 2 g de gochugaru et 1 g de sel, puis ajouter le kimchi, son jus et les oignons verts.",
            "Chauffer 15 ml d'huile de tournesol et 5 ml d'huile de sésame dans une poêle, y étaler la moitié de la pâte en couche fine.",
            "Cuire 4 minutes à feu moyen-vif jusqu'à ce que le dessous soit croustillant, retourner et cuire 3 minutes. Répéter.",
            "Couper en parts et servir chaud.",
        ]),
        ("time", 10, 0, 15),
    ],

    # ── Dal makhani de Delhi / rajma masala vegan ──
    "dal_dal_makhani_c9ce94": [
        ("title", "Dal makhani de Delhi au beurre et à la crème"),
        ("desc", "Le dal des grandes tables de Delhi : lentilles urad noires et haricots rouges trempés une nuit, "
                 "mijotés longuement avec tomate, gingembre et épices, puis enrichis de beurre et de crème."),
        ("origin", {"region": "delhi", "city": "delhi"}),
    ],
    "dal_makhani_vegan_259219": [
        ("title", "Rajma masala du Pendjab (vegan)"),
        ("desc", "Le curry de haricots rouges du Pendjab : haricots trempés une nuit puis mijotés dans une sauce "
                 "épaisse d'oignon, tomate, gingembre, ail et garam masala, servi sur du riz."),
        ("origin", {"region": "punjab", "city": "amritsar"}),
        ("compo", [
            ("kidney_bean_dried", 250, "g", "protein", "dried"),
            ("tomato_raw_ripe", 400, "g", "sauce_base"),
            ("onion_raw", 200, "g", "aromatic_base"),
            ("garlic_raw", 15, "g", "aromatic"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("chilli_pepper_raw", 5, "g", "spice"),
            ("sunflower_oil_plant", 35, "ml", "fat"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("coriander_spice_seed", 3, "g", "spice"),
            ("turmeric_powder", 2, "g", "spice"),
            ("garam_masala", 3, "g", "spice"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("water", 1200, "ml", "liquid"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("basmati_rice_raw_seed", None, "1 portion", "serving_suggestion"),
        ]),
        ("steps", [
            "Faire tremper 250 g de haricots rouges 12 heures, les égoutter, puis les cuire 1 heure dans 1 L d'eau fraîche (après 10 minutes d'ébullition vive), jusqu'à ce qu'ils soient tendres.",
            "Faire grésiller 3 g de cumin dans 35 ml d'huile, ajouter 200 g d'oignon haché et le dorer 12 minutes.",
            "Ajouter 15 g d'ail, 15 g de gingembre et 5 g de piment hachés, puis 3 g de coriandre moulue et 2 g de curcuma, et cuire 1 minute.",
            "Ajouter 400 g de tomates mixées et 4 g de sel, puis cuire 10 minutes jusqu'à ce que l'huile se sépare.",
            "Ajouter les haricots avec 200 ml de leur eau et mijoter 20 minutes, en écrasant quelques haricots pour épaissir. Ajouter 3 g de garam masala.",
            "Servir parsemé de 10 g de coriandre, avec du riz.",
        ]),
        ("time", 20, 720, 100),
    ],

    # ── Enchiladas : rojas au queso fresco / verdes vegan patate douce-épinards ──
    "bread_enchiladas_fe7221": [
        ("title", "Enchiladas rojas aux haricots noirs et queso fresco"),
        ("desc", "Tortillas roulées autour de haricots noirs, nappées d'une sauce rouge aux piments ancho séchés "
                 "et à la tomate, parsemées de queso fresco et gratinées."),
        ("compo", [
            ("base_tortilla_92c2a6", 320, "g", "ingredient"),
            ("black_bean_boiled", 300, "g", "plant_protein", "cooked"),
            ("queso_fresco_block_cow", 120, "g", "ingredient"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("tomato_raw_ripe", 300, "g", "fruit"),
            ("ancho_pepper_spice_dried", 30, "g", "spice", "dry"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("oregano_spice_dried", 1, "g", "herb"),
            ("olive_oil_extra_virgin_plant", 35, "ml", "fat"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
        ]),
        ("steps", [
            "Épépiner 30 g de piments ancho, les griller 30 secondes à sec, puis les faire tremper 15 minutes dans 250 ml d'eau chaude.",
            "Mixer les piments et leur eau avec 300 g de tomates, 50 g d'oignon, 6 g d'ail, 3 g de cumin, 1 g d'origan et 2 g de sel, puis cuire la sauce 10 minutes dans 15 ml d'huile.",
            "Faire revenir 100 g d'oignon et 3 g d'ail dans 20 ml d'huile, ajouter 300 g de haricots noirs et 1 g de sel, puis les écraser grossièrement.",
            "Préchauffer le four à 190°C. Tremper les tortillas une à une dans la sauce, les garnir de haricots, les rouler et les ranger dans un plat.",
            "Napper du reste de sauce, parsemer de 120 g de queso fresco et cuire 15 minutes. Servir avec 10 g de coriandre.",
        ]),
        ("time", 25, 15, 30),
    ],
    "wrap_enchiladas_vegan_f70bca": [
        ("title", "Enchiladas verdes à la patate douce et aux épinards (vegan)"),
        ("desc", "Enchiladas à la sauce verte de tomatilles, piment serrano et coriandre, garnies de patate douce "
                 "rôtie, d'épinards et de haricots noirs, gratinées au cheddar végétal."),
        ("compo", [
            ("base_tortilla_92c2a6", 320, "g", "ingredient"),
            ("sweet_potato_raw", 400, "g", "vegetable"),
            ("spinach_raw_baby", 150, "g", "vegetable"),
            ("black_bean_boiled", 150, "g", "plant_protein", "cooked"),
            ("base_vegan_cheddar_024998", 100, "g", "ingredient"),
            ("tomatillo_raw", 400, "g", "fruit"),
            ("serrano_pepper_raw", 10, "g", "spice"),
            ("yellow_onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("coriander_raw_fresh_herb", 20, "g", "herb"),
            ("cumin_spice_seed", 2, "g", "spice"),
            ("olive_oil_extra_virgin_plant", 35, "ml", "fat"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Préchauffer le four à 210°C. Rôtir 400 g de patate douce en dés avec 20 ml d'huile d'olive, 2 g de cumin et 1 g de sel, 25 minutes.",
            "Sauce verte : cuire 400 g de tomatilles, 10 g de serrano, 50 g d'oignon et 9 g d'ail dans l'eau bouillante 8 minutes, puis les mixer avec 20 g de coriandre, 15 ml d'huile et 2 g de sel.",
            "Faire tomber 150 g d'épinards avec 50 g d'oignon, puis les mélanger à la patate douce et à 150 g de haricots noirs.",
            "Baisser le four à 190°C. Garnir et rouler les tortillas, les ranger dans un plat et les napper de sauce verte.",
            "Parsemer de 100 g de cheddar végétal et cuire 15 minutes.",
        ]),
        ("time", 25, 0, 50),
    ],
}
