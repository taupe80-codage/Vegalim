"""Variantes 13 : rösti, sabzi polo, salade andine, salmorejo, shakshuka."""

VARIANTS = {
    # ── Rösti bernois / aux légumes racines vegan ──
    "side_rosti_4ec9f8": [
        ("title", "Rösti bernois au beurre"),
        ("desc", "La galette de pommes de terre de Berne : pommes de terre cuites la veille, râpées grossièrement "
                 "et dorées lentement au beurre en une seule grande galette croustillante."),
        ("origin", {"region": "berne", "city": "berne"}),
        ("compo", [
            ("potato_raw_with_skin", 700, "g", "ingredient"),
            ("butter_sup80pct", 40, "g", "fat_cooking"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "La veille, cuire 700 g de pommes de terre avec la peau à l'eau, 15 minutes : elles doivent rester fermes. Les laisser refroidir une nuit au frais.",
            "Les éplucher et les râper grossièrement, puis saler avec 3 g de sel et poivrer avec 1 g de poivre.",
            "Faire fondre 30 g de beurre dans une poêle de 24 cm, y tasser les pommes de terre en galette et cuire 12 minutes à feu moyen-doux, jusqu'à ce que le dessous soit doré.",
            "Retourner la galette à l'aide d'une assiette, ajouter 10 g de beurre et cuire encore 10 minutes.",
            "Servir aussitôt, coupé en parts.",
        ]),
        ("time", 10, 600, 40),
    ],
    "snack_rosti_vegan_be15a2": [
        ("title", "Rösti aux légumes racines et à la ciboulette (vegan)"),
        ("desc", "Galettes croustillantes de pommes de terre, carotte, céleri-rave et oignon râpés, dorées à "
                 "l'huile et parsemées de ciboulette."),
        ("dish", "side"),
        ("compo", [
            ("potato_raw_with_skin", 400, "g", "ingredient"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("celeriac_raw", 150, "g", "vegetable"),
            ("onion_raw", 80, "g", "aromatic_base"),
            ("potato_starch_flour", 15, "g", "binder"),
            ("chives_raw_fresh", 10, "g", "herb"),
            ("sunflower_oil_plant", 35, "ml", "fat_cooking"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("green_salad_raw_plain", None, "une portion", "serving_suggestion"),
        ]),
        ("steps", [
            "Râper 400 g de pommes de terre, 150 g de carotte, 150 g de céleri-rave et 80 g d'oignon, puis presser dans un torchon pour retirer l'eau.",
            "Mélanger avec 15 g de fécule, 3 g de sel, 1 g de poivre et 10 g de ciboulette ciselée.",
            "Former 8 galettes fines et les cuire dans 35 ml d'huile, 5 minutes de chaque côté à feu moyen, jusqu'à ce qu'elles soient dorées.",
            "Égoutter sur du papier absorbant et servir chaud.",
        ]),
        ("time", 20, 0, 20),
    ],

    # ── Sabzi polo de Norouz / baghali polo vegan ──
    "rice_sabzi_polo_e099d2": [
        ("title", "Sabzi polo de Norouz au tahdig"),
        ("desc", "Le riz aux herbes du Nouvel An persan : basmati cuit à l'étouffée avec persil, coriandre, "
                 "aneth, ciboulette et fenugrec, fond croustillant (tahdig) au beurre et safran."),
    ],
    "side_sabzi_polo_vegan_7bf9df": [
        ("title", "Baghali polo aux fèves et à l'aneth (vegan)"),
        ("desc", "Riz persan aux fèves fraîches et à l'aneth, cuit à l'étouffée à l'huile d'olive avec un fond "
                 "croustillant, parfumé au safran."),
        ("origin", {"cuisine": "persian", "country": "iran", "region": "tehran", "city": "tehran"}),
        ("compo", [
            ("basmati_rice_raw_seed", 300, "g", "ingredient"),
            ("broadbeans_fava_beans_boiled_fresh", 250, "g", "plant_protein", "cooked"),
            ("dill_weed_fresh_herb_leaf", 50, "g", "herb"),
            ("saffron", 0.3, "g", "spice"),
            ("turmeric_powder", 1, "g", "spice"),
            ("olive_oil_plant", 45, "ml", "fat_cooking"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("water", 1500, "ml", "liquid"),
        ]),
        ("steps", [
            "Rincer 300 g de riz basmati et le laisser tremper 1 heure dans l'eau salée.",
            "Le précuire 6 minutes dans 1,5 L d'eau bouillante avec 4 g de sel, puis l'égoutter : les grains doivent rester fermes. Mélanger avec 250 g de fèves pelées et 50 g d'aneth ciselé.",
            "Chauffer 30 ml d'huile d'olive avec 1 g de curcuma au fond d'une cocotte, puis y étaler le riz en dôme.",
            "Faire infuser 0,3 g de safran dans 30 ml d'eau chaude et l'arroser sur le riz avec 15 ml d'huile.",
            "Couvrir d'un couvercle enveloppé d'un torchon et cuire 40 minutes à feu très doux, jusqu'à ce que le fond soit doré.",
            "Démouler et servir le riz avec des morceaux de tahdig.",
        ]),
        ("time", 15, 60, 50),
    ],

    # ── Salade andine : solterito d'Arequipa / quinoa-avocat vegan ──
    "salad_andine_au_fromage_c537bd": [
        ("title", "Solterito d'Arequipa au fromage frais"),
        ("desc", "Salade du sud du Pérou : fèves, maïs, tomate, oignon rouge, olives noires et fromage frais, "
                 "relevés de piment et de citron vert."),
        ("origin", {"cuisine": "peruvian", "country": "peru", "region": "arequipa", "city": "arequipa"}),
        ("compo", [
            ("broadbeans_fava_beans_boiled_fresh", 250, "g", "plant_protein", "cooked"),
            ("sweet_corn_on_the_cob_cooked", 250, "g", "vegetable"),
            ("tomato_raw_ripe", 300, "g", "fruit"),
            ("red_onion_raw", 100, "g", "vegetable"),
            ("black_olive_canned_in_brine", 40, "g", "fruit"),
            ("queso_fresco_block_cow", 150, "g", "ingredient"),
            ("chilli_pepper_raw", 6, "g", "spice"),
            ("lime_juice_fresh", 30, "ml", "condiment"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ]),
        ("steps", [
            "Émincer finement 100 g d'oignon rouge et le laisser tremper 10 minutes dans l'eau froide, puis l'égoutter.",
            "Couper 300 g de tomates et 150 g de fromage frais en dés, égrener 250 g de maïs cuit et peler 250 g de fèves.",
            "Mélanger avec 40 g d'olives noires, 6 g de piment haché et 15 g de persil.",
            "Assaisonner avec 30 ml de jus de citron vert, 30 ml d'huile d'olive et 2 g de sel, puis servir frais.",
        ]),
        ("time", 20, 10, 0),
    ],
    "salad_andine_au_fromage_vegan_566f05": [
        ("title", "Salade andine au quinoa, avocat et haricots noirs (vegan)"),
        ("desc", "Salade complète des Andes : quinoa, haricots noirs, maïs, tomate, avocat et oignon rouge, "
                 "en vinaigrette citron vert-coriandre."),
        ("compo", [
            ("quinoa_raw_dried", 150, "g", "carbohydrate"),
            ("black_bean_boiled", 200, "g", "plant_protein", "cooked"),
            ("sweet_corn_on_the_cob_cooked", 200, "g", "vegetable"),
            ("tomato_raw_ripe", 250, "g", "fruit"),
            ("avocado_raw", 200, "g", "fruit"),
            ("red_onion_raw", 80, "g", "vegetable"),
            ("coriander_raw_fresh_herb", 15, "g", "herb"),
            ("lime_juice_fresh", 30, "ml", "condiment"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("cumin_spice_seed", 1, "g", "spice"),
            ("water", 300, "ml", "liquid"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Rincer 150 g de quinoa et le cuire dans 300 ml d'eau salée avec 1 g de sel, 12 minutes à couvert, puis le laisser refroidir.",
            "Couper 250 g de tomates et 200 g d'avocat en dés, émincer 80 g d'oignon rouge et égrener 200 g de maïs.",
            "Vinaigrette : mélanger 30 ml de jus de citron vert, 30 ml d'huile d'olive, 1 g de cumin et 2 g de sel.",
            "Mélanger le quinoa, 200 g de haricots noirs, les légumes et 15 g de coriandre avec la vinaigrette, puis servir frais.",
        ]),
        ("time", 20, 0, 12),
    ],

    # ── Salmorejo cordobés / ajo blanco vegan ──
    "bread_salmorejo_a156e9": [
        ("title", "Salmorejo cordobés à l'œuf dur"),
        ("desc", "La crème froide de Cordoue : tomates mûres mixées avec pain, ail et beaucoup d'huile d'olive "
                 "jusqu'à être veloutée, servie bien fraîche avec des œufs durs hachés."),
        ("origin", {"cuisine": "spanish", "country": "spain", "region": "andalousie", "city": "cordoue"}),
        ("dish", "starter"),
        ("compo", [
            ("tomato_raw_ripe", 800, "g", "fruit"),
            ("white_bread_baguette", 150, "g", "ingredient"),
            ("garlic_raw", 5, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 70, "ml", "fat"),
            ("white_vinegar_liquid_distilled", 10, "ml", "ingredient"),
            ("egg_hard_boiled", 110, "g", "ingredient"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Mixer 800 g de tomates mûres, puis les passer au chinois.",
            "Ajouter 150 g de pain rassis en morceaux et laisser tremper 10 minutes.",
            "Mixer avec 5 g d'ail, 10 ml de vinaigre et 3 g de sel, puis verser 70 ml d'huile d'olive en filet en mixant, jusqu'à obtenir une crème épaisse.",
            "Réfrigérer au moins 2 heures.",
            "Servir bien froid, parsemé de 2 œufs durs (110 g) hachés et d'un filet d'huile.",
        ]),
        ("time", 15, 120, 0),
    ],
    "entry_salmorejo_vegan_d0b7f7": [
        ("title", "Ajo blanco de Málaga aux amandes et au raisin (vegan)"),
        ("desc", "La soupe froide blanche d'Andalousie, antérieure au gaspacho : amandes, pain, ail, huile d'olive "
                 "et vinaigre mixés avec de l'eau glacée, servie avec des grains de raisin."),
        ("origin", {"region": "andalousie", "city": "malaga"}),
        ("compo", [
            ("almond_raw_skinless_unsalted", 100, "g", "ingredient"),
            ("white_bread_unsalted", 100, "g", "ingredient"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("white_vinegar_liquid_distilled", 15, "ml", "ingredient"),
            ("water", 600, "ml", "liquid"),
            ("chasselas_grape_raw", 120, "g", "garnish"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire tremper 100 g de pain rassis sans croûte dans un peu d'eau 5 minutes, puis l'essorer.",
            "Mixer 100 g d'amandes mondées avec 6 g d'ail, le pain et 200 ml d'eau glacée jusqu'à obtenir une pâte fine.",
            "Ajouter 40 ml d'huile d'olive en filet, puis 15 ml de vinaigre, 3 g de sel et 400 ml d'eau glacée.",
            "Réfrigérer au moins 2 heures.",
            "Servir très froid, garni de 120 g de grains de raisin coupés en deux.",
        ]),
        ("time", 15, 120, 0),
    ],

    # ── Shakshuka tunisienne à la feta / d'aubergine au tofu soyeux vegan ──
    "egg_shakshuka_eb137b": [
        ("title", "Shakshuka tunisienne aux poivrons et à la feta"),
        ("desc", "Poivrons et tomates mijotés au cumin et au paprika, œufs pochés dans la sauce et feta émiettée, "
                 "à servir dans la poêle avec du pain."),
    ],
    "brkf_shakshuka_vegan_81fa9a": [
        ("title", "Shakshuka d'aubergine au tofu soyeux et au sumac (vegan)"),
        ("desc", "Sauce tomate aux aubergines et poivrons fondus, épicée au cumin et au paprika fumé, avec des "
                 "cuillerées de tofu soyeux au curcuma qui rappellent les œufs, relevée de sumac."),
        ("compo", [
            ("eggplant_raw", 250, "g", "vegetable"),
            ("tomato_raw_ripe", 400, "g", "fruit"),
            ("red_bell_pepper_raw", 200, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("silken_tofu_pre_packaged", 250, "g", "ingredient"),
            ("turmeric_powder", 1, "g", "spice"),
            ("cumin_spice_seed", 2, "g", "spice"),
            ("paprika_powder", 2, "g", "spice"),
            ("sumac", 2, "g", "spice"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire revenir 250 g d'aubergine en dés dans 20 ml d'huile d'olive, 8 minutes, puis ajouter 100 g d'oignon et 200 g de poivron émincés et cuire 5 minutes.",
            "Ajouter 9 g d'ail, 2 g de cumin et 2 g de paprika, puis 400 g de tomates concassées et 2 g de sel, et mijoter 15 minutes.",
            "Égoutter 250 g de tofu soyeux et le mélanger avec 1 g de curcuma, 10 ml d'huile et 1 g de sel.",
            "Creuser des puits dans la sauce, y déposer le tofu en cuillerées, couvrir et chauffer 5 minutes.",
            "Parsemer de 2 g de sumac et de 10 g de coriandre, puis servir dans la poêle.",
        ]),
        ("time", 15, 0, 35),
    ],
}
