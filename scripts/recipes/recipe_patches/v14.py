"""Variantes 14 : tamales, tostadas, mercimek, varenyky."""

VARIANTS = {
    # ── Tamales : rajas con queso / de frijol vegan ──
    "soup_tamales_7dd98a": [
        ("title", "Tamales rajas con queso"),
        ("desc", "Tamales de Mexico : pâte de maïs battue à l'huile, garnie de lanières de poivron et de piment "
                 "vert revenues à l'oignon et de fromage frais, cuite à la vapeur dans des feuilles de maïs."),
        ("origin", {"cuisine": "mexican", "country": "mexico", "region": "ciudad_de_mexico", "city": "mexico"}),
        ("compo", [
            ("masa_harina", 300, "g", "ingredient"),
            ("baking_powder", 5, "g", "leavening"),
            ("vegetable_stock_dried", 4, "g", "ingredient"),
            ("water", 350, "ml", "ingredient"),
            ("sunflower_oil_plant", 60, "ml", "fat"),
            ("green_bell_pepper_raw", 200, "g", "vegetable"),
            ("jalapeno_pepper_raw", 20, "g", "spice"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("queso_fresco_block_cow", 150, "g", "ingredient"),
            ("corn_husk", 40, "g", "ingredient"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire tremper 40 g de feuilles de maïs 30 minutes dans l'eau chaude.",
            "Battre 300 g de masa harina avec 5 g de poudre à lever, 3 g de sel, 50 ml d'huile et 350 ml de bouillon tiède (4 g de bouillon déshydraté), 5 minutes, jusqu'à ce que la pâte soit légère.",
            "Faire revenir 200 g de poivron vert et 20 g de jalapeño en lanières avec 100 g d'oignon dans 10 ml d'huile, 6 minutes.",
            "Étaler 2 cuillerées de pâte sur chaque feuille, garnir de rajas et de fromage frais (150 g en tout), puis replier.",
            "Cuire debout à la vapeur 60 minutes, jusqu'à ce que la pâte se détache de la feuille.",
        ]),
        ("time", 35, 30, 60),
        ("flag", "kid_friendly", False),
    ],
    "snack_tamales_vegan_d7cbdc": [
        ("title", "Tamales de frijol à la sauce rouge (vegan)"),
        ("desc", "Tamales végétaux fourrés de haricots noirs écrasés et d'une sauce rouge aux piments ancho, "
                 "à l'ail et au cumin, cuits à la vapeur en feuilles de maïs."),
        ("compo", [
            ("masa_harina", 300, "g", "ingredient"),
            ("baking_powder", 5, "g", "leavening"),
            ("vegetable_stock_dried", 4, "g", "ingredient"),
            ("water", 450, "ml", "ingredient"),
            ("sunflower_oil_plant", 60, "ml", "fat"),
            ("black_bean_boiled", 300, "g", "plant_protein", "cooked"),
            ("ancho_pepper_spice_dried", 15, "g", "spice", "dry"),
            ("tomato_raw_ripe", 150, "g", "fruit"),
            ("white_onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("cumin_spice_seed", 2, "g", "spice"),
            ("corn_husk", 40, "g", "ingredient"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire tremper 40 g de feuilles de maïs 30 minutes, et 15 g de piments ancho épépinés 15 minutes dans 100 ml d'eau chaude.",
            "Mixer les piments et leur eau avec 150 g de tomate, 50 g d'oignon, 9 g d'ail, 2 g de cumin et 1 g de sel, puis cuire la sauce 8 minutes dans 10 ml d'huile.",
            "Écraser 300 g de haricots noirs avec 50 g d'oignon haché et la moitié de la sauce.",
            "Battre 300 g de masa harina avec 5 g de poudre à lever, 3 g de sel, 50 ml d'huile et 350 ml de bouillon tiède (4 g de bouillon déshydraté).",
            "Garnir les feuilles de pâte, de haricots et d'un peu de sauce, replier et cuire 60 minutes à la vapeur. Servir avec le reste de sauce.",
        ]),
        ("time", 35, 30, 60),
    ],

    # ── Tostadas : de frijoles et crème / de tinga de champignons vegan ──
    "bread_tostadas_06442e": [
        ("title", "Tostadas aux haricots noirs, avocat et crème"),
        ("desc", "Tortillas croustillantes cuites au four, tartinées de haricots noirs refrits, garnies de laitue, "
                 "tomate, avocat, crème et queso fresco, arrosées de citron vert."),
        ("origin", {"cuisine": "mexican", "country": "mexico", "region": "ciudad_de_mexico", "city": "mexico"}),
        ("compo", [
            ("base_tortilla_92c2a6", 320, "g", "ingredient"),
            ("black_bean_boiled", 300, "g", "protein", "cooked"),
            ("avocado_raw", 200, "g", "fruit"),
            ("tomato_raw_ripe", 200, "g", "fruit"),
            ("lettuce", 150, "g", "vegetable"),
            ("sour_cream_fermented_18pct", 80, "g", "ingredient"),
            ("queso_fresco_block_cow", 60, "g", "ingredient"),
            ("onion_raw", 60, "g", "aromatic_base"),
            ("lime_juice_fresh", 30, "ml", "fruit"),
            ("vegetable_oil_plant", 25, "ml", "fat"),
            ("cumin_spice_seed", 2, "g", "spice"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Préchauffer le four à 200°C. Badigeonner les tortillas de 15 ml d'huile et les cuire 8 minutes, jusqu'à ce qu'elles soient croustillantes.",
            "Faire revenir 60 g d'oignon haché dans 10 ml d'huile, ajouter 300 g de haricots noirs, 2 g de cumin et 2 g de sel, puis les écraser avec un peu d'eau en purée épaisse.",
            "Écraser 200 g d'avocat avec 20 ml de jus de citron vert et 1 g de sel.",
            "Tartiner chaque tostada de haricots, puis garnir de 150 g de laitue émincée, 200 g de tomate en dés et d'avocat.",
            "Terminer avec 80 g de crème, 60 g de queso fresco émietté et 10 ml de jus de citron vert.",
        ]),
        ("time", 20, 0, 15),
    ],
    "snack_tostadas_vegan_f7257b": [
        ("title", "Tostadas de tinga de champignons (vegan)"),
        ("desc", "Tostadas garnies de tinga de champignons effilochés, mijotés avec oignon, tomate et paprika "
                 "fumé, avec avocat, chou croquant et crème de cajou au citron vert."),
        ("dish", "main"),
        ("serv", 4),
        ("compo", [
            ("base_tortilla_92c2a6", 320, "g", "ingredient"),
            ("oyster_mushroom_raw", 400, "g", "protein"),
            ("black_bean_boiled", 200, "g", "protein", "cooked"),
            ("onion_raw", 120, "g", "aromatic_base"),
            ("tomato_raw_ripe", 250, "g", "fruit"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("paprika", 3, "g", "spice"),
            ("oregano_spice_dried", 1, "g", "herb"),
            ("avocado_raw", 150, "g", "fruit"),
            ("green_cabbage_raw", 100, "g", "vegetable"),
            ("cashew_butter_plain_plant", 40, "g", "ingredient"),
            ("lime_juice_fresh", 30, "ml", "fruit"),
            ("vegetable_oil_plant", 30, "ml", "fat"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Préchauffer le four à 200°C. Badigeonner les tortillas de 15 ml d'huile et les cuire 8 minutes.",
            "Tinga : effilocher 400 g de pleurotes et les dorer dans 15 ml d'huile, 6 minutes, puis ajouter 120 g d'oignon émincé et 6 g d'ail, et cuire 4 minutes.",
            "Ajouter 250 g de tomates mixées, 3 g de paprika fumé, 1 g d'origan et 2 g de sel, puis mijoter 10 minutes. Ajouter 200 g de haricots noirs.",
            "Crème : délayer 40 g de beurre de cajou avec 20 ml de jus de citron vert, 1 g de sel et 30 ml d'eau.",
            "Garnir les tostadas de tinga, de 100 g de chou émincé et de 150 g d'avocat, puis napper de crème de cajou et arroser de 10 ml de citron vert.",
        ]),
        ("time", 20, 0, 25),
    ],

    # ── Mercimek : köftesi / çorbası au beurre pimenté / ezogelin vegan ──
    "dal_mercimek_koftesi_34f72d": [
        ("title", "Mercimek köftesi, boulettes de lentilles au boulgour"),
        ("desc", "Spécialité turque sans cuisson de viande : lentilles corail et boulgour fin gonflés ensemble, "
                 "pétris avec oignon, concentré de tomate, épices et persil, façonnés en quenelles servies dans la laitue."),
        ("origin", {"cuisine": "turkish", "country": "turkey", "region": "anatolie", "city": ""}),
    ],
    "dal_turkish_mercimek_soup_a7afcf": [
        ("title", "Mercimek çorbası d'Istanbul au beurre pimenté"),
        ("desc", "La soupe de lentilles corail des lokantas : lentilles, oignon et carotte mixés en velouté, "
                 "servie avec un filet de beurre fondu à la menthe séchée, et du citron."),
        ("origin", {"cuisine": "turkish", "country": "turkey", "region": "istanbul", "city": "istanbul"}),
        ("dish", "soup"),
    ],
    "soup_turkish_mercimek_soup_veg_f30ebc": [
        ("title", "Ezogelin çorbası, lentilles, boulgour et menthe (vegan)"),
        ("desc", "Soupe de Gaziantep plus rustique que la mercimek : lentilles corail, boulgour et riz mijotés "
                 "au concentré de tomate et au piment pul biber, parfumés à la menthe séchée."),
        ("origin", {"cuisine": "turkish", "country": "turkey", "region": "gaziantep", "city": "gaziantep"}),
        ("compo", [
            ("red_lentil_dried", 200, "g", "plant_protein", "dried"),
            ("bulgur_raw_dried", 50, "g", "carbohydrate"),
            ("white_rice_raw_seed_unenriched", 30, "g", "carbohydrate"),
            ("yellow_onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("tomato_paste_unsalted_canned", 30, "g", "ingredient"),
            ("red_hot_chili_pepper_spice_dried", 2, "g", "spice"),
            ("paprika_powder", 2, "g", "spice"),
            ("dried_mint_herb", 3, "g", "herb"),
            ("olive_oil_plant", 35, "ml", "fat"),
            ("vegetable_stock_dried", 9, "g", "ingredient"),
            ("water", 1300, "ml", "ingredient"),
            ("lemon_juice", 30, "ml", "fruit"),
        ]),
        ("steps", [
            "Faire revenir 150 g d'oignon et 6 g d'ail hachés dans 20 ml d'huile d'olive, 5 minutes, puis ajouter 30 g de concentré de tomate et 2 g de paprika, et cuire 1 minute.",
            "Ajouter 200 g de lentilles corail, 50 g de boulgour et 30 g de riz rincés, 1,3 L d'eau et 9 g de bouillon.",
            "Mijoter 30 minutes à feu doux en remuant de temps en temps, sans mixer : la soupe doit rester épaisse et granuleuse.",
            "Chauffer 15 ml d'huile avec 3 g de menthe séchée et 2 g de pul biber, 30 secondes, puis verser sur la soupe.",
            "Servir avec 30 ml de jus de citron.",
        ]),
        ("time", 10, 0, 40),
    ],

    # ── Varenyky : pomme de terre-aneth et oignons frits / aux griottes vegan ──
    "main_varenyky_pomme_de_terre_0bb7cf": [
        ("title", "Varenyky ukrainiens à la pomme de terre et à l'aneth, oignons frits"),
        ("desc", "Raviolis ukrainiens à la pâte à l'eau, farcis de purée, de fromage blanc et d'aneth, pochés puis "
                 "servis avec des oignons frits au beurre et de la crème aigre."),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 300, "g", "carbohydrate"),
            ("water", 160, "ml", "liquid"),
            ("sunflower_oil_plant", 15, "ml", "fat_cooking"),
            ("potato_raw_flesh", 500, "g", "ingredient"),
            ("fromage_blanc_plain_2_5pct_cow", 100, "g", "ingredient"),
            ("dill_weed_fresh_herb_leaf", 10, "g", "herb"),
            ("onion_raw", 200, "g", "aromatic_base"),
            ("butter_sup80pct", 40, "g", "fat_cooking"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("sour_cream_fermented_18pct", None, "2 cuillères à soupe", "serving_suggestion"),
        ]),
        ("steps", [
            "Pétrir 300 g de farine avec 160 ml d'eau tiède, 15 ml d'huile et 2 g de sel, puis laisser reposer 30 minutes.",
            "Cuire 500 g de pommes de terre à l'eau 20 minutes, les écraser avec 100 g de fromage blanc, 10 g d'aneth ciselé, 2 g de sel et 1 g de poivre.",
            "Étaler la pâte finement, découper des disques de 7 cm, garnir, replier en demi-lune et pincer les bords.",
            "Pocher les varenyky 4 minutes dans l'eau bouillante salée après qu'ils remontent.",
            "Faire frire 200 g d'oignon émincé dans 40 g de beurre jusqu'à ce qu'il soit doré, et en napper les varenyky. Servir avec de la crème aigre.",
        ]),
        ("time", 40, 30, 35),
    ],
    "snack_varenyky_pomme_de_terre_v_8b6240": [
        ("title", "Varenyky aux griottes (vegan)"),
        ("origin", {"country": "ukraine"}),
        ("desc", "Le dessert d'été ukrainien : raviolis à la pâte à l'eau farcis de griottes sucrées, pochés et "
                 "servis nappés de leur jus réduit."),
        ("dish", "dessert"),
        ("serv", 6),
        ("compo", [
            ("wheat_flour", 300, "g", "carbohydrate"),
            ("water", 160, "ml", "liquid"),
            ("vegetable_oil_plant", 15, "ml", "fat_cooking"),
            ("sour_cherry_raw", 500, "g", "ingredient"),
            ("white_sugar", 60, "g", "sweetener"),
            ("cornstarch_flour", 10, "g", "thickener"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Dénoyauter 500 g de griottes, les mélanger avec 40 g de sucre et laisser dégorger 30 minutes, puis les égoutter en gardant le jus.",
            "Pétrir 300 g de farine avec 160 ml d'eau tiède, 15 ml d'huile et 1 g de sel, puis laisser reposer 30 minutes.",
            "Étaler la pâte finement, découper des disques de 7 cm, garnir de 3 ou 4 griottes roulées dans 10 g de fécule, puis replier et bien souder.",
            "Pocher les varenyky 4 minutes dans l'eau frémissante après qu'ils remontent.",
            "Réduire le jus des griottes avec 20 g de sucre 5 minutes et en napper les varenyky. Servir tiède.",
        ]),
        ("time", 40, 30, 25),
    ],
}
