"""Lot 17 : plats de printemps (18 recettes, végétariennes au minimum).

Comble le manque relevé après la relecture du calendrier de saisonnalité (2026-11-19) : le
printemps était la saison la plus pauvre (106 à 166 plats de saison par mois de mars à mai,
contre 345 à 411 de juin à septembre). Asperges (4 plats), fèves (1), rhubarbe (1), radis (3)
et artichaut (aucun) étaient presque absents.
"""
from ._schema import recipe

RECIPES = [
    # ── A. Plats principaux ─────────────────────────────────────────────────────────────────
    recipe(
        rid="stew_vignarola_romaine_5e1a07",
        fr="Vignarola, ragoût romain d'artichauts, fèves et petits pois",
        en="Vignarola, Roman Stew of Artichokes, Fava Beans and Peas",
        original="Vignarola",
        cuisine="italian", country="italy", region="latium", city="rome",
        dish="main", servings=4, prep=35, cook=30,
        texture=("fondant", "legumes_tendres"), taste=("herbacé", "doux"),
        technique=("sauteing", "simmering"), difficulty="medium",
        desc="Le ragoût de printemps des Romains, quand arrivent ensemble les premiers artichauts, "
             "les fèves et les petits pois : les légumes étuvent à l'huile d'olive avec la cébette "
             "et un trait de vin blanc, puis la laitue et la menthe fondent dedans au dernier "
             "moment. Servi tiède avec du pain.",
        compo=[
            ("artichoke_raw", 800, "g", "main_vegetable"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("broadbeans_fava_beans_raw_fresh", 300, "g", "vegetable"),
            ("green_peas_raw", 300, "g", "vegetable"),
            ("green_onion_raw", 150, "g", "aromatic"),
            ("lettuce_raw", 200, "g", "vegetable"),
            ("olive_oil_extra_virgin_plant", 60, "ml", "fat"),
            ("white_wine_liquid", 100, "ml", "liquid"),
            ("water", 200, "ml", "liquid"),
            ("mint_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("sourdough_bread", 240, "g", "carbohydrate"),
        ],
        steps=[
            "Retirer les feuilles dures de 800 g d'artichauts violets, parer les fonds, les couper "
            "en quartiers, ôter le foin et les plonger dans de l'eau citronnée avec 30 ml de jus "
            "de citron.",
            "Faire fondre 150 g de cébettes émincées dans 60 ml d'huile d'olive, 5 minutes à feu "
            "doux.",
            "Ajouter les artichauts égouttés, mouiller avec 100 ml de vin blanc, laisser réduire "
            "2 minutes, puis ajouter 200 ml d'eau et cuire 10 minutes à couvert.",
            "Ajouter 300 g de fèves écossées et pelées et 300 g de petits pois, et cuire encore "
            "8 minutes.",
            "Incorporer 200 g de laitue romaine en lanières et 10 g de menthe ciselée, saler avec "
            "5 g de sel, poivrer avec 1 g de poivre et laisser fondre 5 minutes à découvert.",
            "Laisser tiédir 10 minutes et servir avec 240 g de pain de campagne.",
        ],
    ),
    recipe(
        rid="stew_anginares_a_la_polita_8b2c46",
        fr="Anginares a la polita, artichauts à la grecque aux pommes de terre et à l'aneth",
        en="Anginares a la Polita, Greek Artichokes with Potatoes and Dill",
        original="Αγκινάρες α λα πολίτα",
        cuisine="greek", country="greece", region="attique",
        dish="main", servings=4, prep=35, cook=40,
        texture=("fondant", "legumes_tendres"), taste=("acidulé", "herbacé"),
        technique=("simmering",), difficulty="medium",
        desc="Plat de Carême venu de Constantinople : des fonds d'artichauts mijotés à l'huile "
             "d'olive avec carottes, pommes de terre et petits pois, dans un bouillon citronné "
             "parfumé à l'aneth et à la cébette.",
        compo=[
            ("artichoke_raw", 1000, "g", "main_vegetable"),
            ("lemon_juice", 80, "ml", "acidity"),
            ("potato_raw_flesh", 500, "g", "carbohydrate"),
            ("carrot_raw", 250, "g", "vegetable"),
            ("green_peas_raw", 200, "g", "vegetable"),
            ("onion_raw", 120, "g", "aromatic"),
            ("green_onion_raw", 80, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 80, "ml", "fat"),
            ("water", 400, "ml", "liquid"),
            ("dill_weed_fresh_herb_leaf", 20, "g", "herb"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Parer 1 kg d'artichauts jusqu'au cœur, ôter le foin, couper les fonds en deux et les "
            "garder dans de l'eau avec 40 ml de jus de citron.",
            "Faire revenir 120 g d'oignon et 80 g de cébettes émincées dans 80 ml d'huile "
            "d'olive, 5 minutes.",
            "Ajouter 250 g de carottes en rondelles épaisses et 500 g de pommes de terre en gros "
            "morceaux, et remuer 2 minutes.",
            "Poser les artichauts égouttés par-dessus, verser 400 ml d'eau et 40 ml de jus de "
            "citron, puis saler avec 5 g de sel, et poivrer avec 1 g de poivre.",
            "Couvrir et cuire 30 minutes à petit feu, en secouant la cocotte de temps en temps.",
            "Ajouter 200 g de petits pois et 20 g d'aneth ciselé, et cuire encore 10 minutes, "
            "jusqu'à ce que la sauce soit courte.",
        ],
    ),
    recipe(
        rid="main_spargel_sauce_hollandaise_3d9f15",
        allow_similar=("blanches",),
        fr="Asperges blanches à l'allemande, sauce hollandaise et pommes de terre nouvelles",
        en="German White Asparagus with Hollandaise and New Potatoes",
        original="Spargel mit Sauce hollandaise und Kartoffeln",
        cuisine="german", country="germany", region="bade", city="schwetzingen",
        dish="main", servings=4, prep=25, cook=25,
        texture=("fondant", "onctueux"), taste=("beurré", "acidulé"),
        technique=("boiling", "sauce_making"), difficulty="medium",
        desc="Le repas de la « Spargelzeit », d'avril à la Saint-Jean : asperges blanches cuites "
             "dans une eau légèrement sucrée et beurrée, pommes de terre nouvelles et sauce "
             "hollandaise montée au beurre fondu.",
        compo=[
            ("white_asparagus_raw_peeled", 1200, "g", "main_vegetable"),
            ("new_potato_raw", 800, "g", "carbohydrate"),
            ("water", 4000, "ml", "liquid"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
            ("white_sugar", 5, "g", "seasoning"),
            ("butter_sup80pct", 200, "g", "fat"),
            ("egg_yolk_raw", 60, "g", "binder"),
            ("lemon_juice", 20, "ml", "acidity"),
            ("chives_raw_fresh", 8, "g", "herb"),
        ],
        steps=[
            "Peler 1,2 kg d'asperges blanches de la pointe vers le talon et couper 1 cm de la base.",
            "Cuire 800 g de pommes de terre nouvelles avec leur peau 20 minutes dans 1,5 litre "
            "d'eau bouillante salée avec 2 g de sel.",
            "Porter 2,5 litres d'eau à ébullition avec 3 g de sel, 5 g de sucre et 20 g de beurre, "
            "y cuire les asperges 12 à 15 minutes : la pointe d'un couteau doit entrer sans "
            "résistance.",
            "Pour la hollandaise, fondre 180 g de beurre ; au bain-marie, fouetter 60 g de jaunes "
            "d'œufs avec 30 ml d'eau jusqu'à ce qu'ils épaississent et forment un ruban.",
            "Hors du feu, verser le beurre fondu en filet en fouettant, puis ajouter 20 ml de jus "
            "de citron et 1 g de sel.",
            "Servir les asperges égouttées avec les pommes de terre parsemées de 8 g de "
            "ciboulette et la sauce à part.",
        ],
    ),
    recipe(
        rid="stew_navarin_printanier_legumes_c47e90",
        fr="Navarin printanier de légumes nouveaux",
        en="Spring Navarin of New Vegetables",
        cuisine="french", country="france", region="",
        dish="main", servings=4, prep=30, cook=35,
        texture=("fondant", "sauce_liee"), taste=("doux", "herbacé"),
        technique=("sauteing", "simmering"), difficulty="easy",
        desc="Le navarin sans agneau : pommes de terre, carottes et navets nouveaux, petits pois "
             "et fèves mijotés dans un jus lié à la tomate et au thym, garni de cébettes. Les "
             "légumes entrent l'un après l'autre pour rester entiers.",
        compo=[
            ("new_potato_raw", 500, "g", "carbohydrate"),
            ("carrot_raw", 300, "g", "main_vegetable"),
            ("turnip_raw", 300, "g", "vegetable"),
            ("green_peas_raw", 200, "g", "vegetable"),
            ("broadbeans_fava_beans_raw_fresh", 200, "g", "vegetable"),
            ("green_onion_raw", 150, "g", "aromatic"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("olive_oil_extra_virgin_plant", 15, "ml", "fat"),
            ("wheat_flour_t55", 15, "g", "binder"),
            ("tomato_paste_unsalted_canned", 20, "g", "condiment"),
            ("vegetable_stock_dried", 10, "g", "seasoning"),
            ("water", 600, "ml", "liquid"),
            ("thyme_fresh_herb", 2, "g", "herb"),
            ("bay_leaf_spice", 1, "g", "spice"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Gratter 500 g de pommes de terre nouvelles, 300 g de carottes nouvelles et 300 g de "
            "navets nouveaux ; couper les plus gros en deux.",
            "Faire revenir les cébettes (150 g, coupées en tronçons) et 6 g d'ail dans 30 g de "
            "beurre et 15 ml d'huile, 3 minutes.",
            "Saupoudrer de 15 g de farine, ajouter 20 g de concentré de tomate et remuer 1 minute.",
            "Mouiller avec 600 ml d'eau et 10 g de bouillon, ajouter 2 g de thym et 1 g de "
            "laurier, puis les carottes et les pommes de terre, et cuire 15 minutes à couvert.",
            "Ajouter les navets et cuire 10 minutes, puis 200 g de petits pois et 200 g de fèves "
            "pelées, et cuire encore 8 minutes à découvert, jusqu'à ce que la sauce nappe.",
            "Saler avec 3 g de sel, poivrer avec 1 g de poivre et parsemer de 10 g de persil.",
        ],
    ),
    recipe(
        rid="egg_revuelto_esparragos_trigueros_6a2b38",
        fr="Revuelto de espárragos trigueros, œufs brouillés aux asperges vertes",
        en="Revuelto de Espárragos Trigueros, Scrambled Eggs with Wild Asparagus",
        original="Revuelto de espárragos trigueros",
        cuisine="spanish", country="spain", region="andalousie",
        dish="main", servings=4, prep=10, cook=15,
        texture=("cremeux", "croquant"), taste=("doux", "herbacé"),
        technique=("sauteing",), difficulty="easy",
        desc="Les « asperges de blé » qu'on cueille au printemps au bord des champs andalous, "
             "sautées à l'huile d'olive et à l'ail puis prises dans des œufs brouillés à peine "
             "cuits. Ici avec des asperges vertes fines, servies sur du pain grillé.",
        compo=[
            ("green_asparagus_raw", 500, "g", "main_vegetable"),
            ("egg_raw", 480, "g", "protein"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("sourdough_bread", 240, "g", "carbohydrate"),
        ],
        steps=[
            "Casser la base dure de 500 g d'asperges vertes fines et les couper en tronçons de 3 cm.",
            "Faire revenir 8 g d'ail émincé dans 40 ml d'huile d'olive 1 minute, ajouter les "
            "asperges et les sauter 6 minutes à feu moyen.",
            "Battre légèrement 8 œufs (480 g) avec 3 g de sel et 1 g de poivre.",
            "Baisser le feu, verser les œufs sur les asperges et remuer sans cesse 3 minutes, "
            "jusqu'à ce qu'ils soient pris mais encore crémeux.",
            "Servir aussitôt sur 240 g de pain grillé.",
        ],
    ),
    recipe(
        rid="tofu_saute_asperges_mange_tout_9f4d21",
        fr="Tofu sauté aux asperges et pois mange-tout",
        en="Stir-Fried Tofu with Asparagus and Snow Peas",
        cuisine="chinese", country="china", region="",
        dish="main", servings=4, prep=15, cook=20,
        texture=("croquant", "enrobe"), taste=("umami", "aromatique"),
        technique=("sauteing", "boiling"), difficulty="easy",
        desc="Un sauté vif au wok : tofu doré, asperges vertes et pois mange-tout encore croquants, "
             "liés d'une sauce soja au gingembre et à l'ail, servis sur du riz.",
        compo=[
            ("tofu_plain_pre_packaged", 400, "g", "protein"),
            ("green_asparagus_raw", 300, "g", "main_vegetable"),
            ("snow_peas_raw", 200, "g", "vegetable"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("ginger_raw_root_fresh", 10, "g", "aromatic"),
            ("green_onion_raw", 40, "g", "aromatic"),
            ("soy_sauce_shoyu_reduced_sodium", 30, "ml", "condiment"),
            ("white_sugar", 5, "g", "seasoning"),
            ("cornstarch_flour", 10, "g", "binder"),
            ("water", 530, "ml", "liquid"),
            ("sunflower_oil_plant", 30, "ml", "fat"),
            ("sesame_oil_plant", 5, "ml", "fat"),
            ("white_rice_raw_seed_unenriched", 300, "g", "carbohydrate"),
        ],
        steps=[
            "Cuire 300 g de riz dans 450 ml d'eau, 12 minutes à couvert, puis laisser gonfler "
            "hors du feu.",
            "Couper 400 g de tofu en cubes, 300 g d'asperges en biseaux de 4 cm, effiler 200 g de "
            "pois mange-tout.",
            "Mélanger 30 ml de sauce soja, 5 g de sucre, 10 g de fécule et 80 ml d'eau.",
            "Dorer le tofu dans 20 ml d'huile au wok 6 minutes, puis le réserver.",
            "Dans 10 ml d'huile, sauter 10 g d'ail et 10 g de gingembre hachés 30 secondes, puis "
            "les asperges et les pois 3 minutes à feu vif.",
            "Remettre le tofu, verser la sauce et remuer 1 minute jusqu'à ce qu'elle enrobe, puis "
            "finir avec 5 ml d'huile de sésame et 40 g de cébette ciselée, et servir sur le riz.",
        ],
    ),
    recipe(
        rid="tart_asperges_vertes_ricotta_2c85b3",
        fr="Tarte aux asperges vertes et à la ricotta citronnée",
        en="Green Asparagus and Lemon Ricotta Tart",
        cuisine="french", country="france", region="",
        dish="main", servings=6, prep=20, cook=35,
        texture=("fondant", "croustillant"), taste=("lacté", "herbacé"),
        technique=("boiling", "baking"), difficulty="easy",
        desc="Une tarte de printemps : un appareil de ricotta, d'œufs et de parmesan parfumé au "
             "zeste de citron, sur lequel les asperges vertes blanchies sont rangées tête-bêche "
             "avant de cuire.",
        compo=[
            ("shortcrust_pastry_all_butter_raw_paste_pre_packaged", 230, "g", "base"),
            ("green_asparagus_raw", 400, "g", "main_vegetable"),
            ("ricotta_whole_cow", 250, "g", "dairy"),
            ("egg_raw", 150, "g", "binder"),
            ("cream_heavy_refrigerated_30pct", 100, "ml", "dairy"),
            ("parmesan_grated_dried_cow", 40, "g", "dairy"),
            ("lemon_peel_raw", 3, "g", "aromatic"),
            ("chives_raw_fresh", 5, "g", "herb"),
            ("water", 1500, "ml", "liquid"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Foncer un moule de 26 cm avec 230 g de pâte brisée, la piquer et la cuire à blanc "
            "10 minutes au four à 190 °C.",
            "Blanchir 400 g d'asperges vertes 3 minutes dans 1,5 litre d'eau bouillante salée avec "
            "1 g de sel, puis les rafraîchir.",
            "Mélanger 250 g de ricotta, 3 œufs (150 g), 100 ml de crème, 40 g de parmesan, 3 g de "
            "zeste de citron, 5 g de ciboulette, 2 g de sel et 1 g de poivre.",
            "Verser l'appareil sur le fond de tarte et y ranger les asperges tête-bêche.",
            "Cuire 25 minutes au four à 180 °C, jusqu'à ce que l'appareil soit pris et doré.",
            "Laisser reposer 10 minutes avant de découper.",
        ],
    ),
    recipe(
        rid="pasta_fave_piselli_pecorino_7d3e52",
        fr="Pâtes aux fèves, petits pois, menthe et pecorino",
        en="Pasta with Fava Beans, Peas, Mint and Pecorino",
        original="Pasta con fave, piselli e pecorino",
        cuisine="italian", country="italy", region="latium",
        dish="main", servings=4, prep=20, cook=15,
        texture=("al_dente", "enrobe"), taste=("herbacé", "fromage"),
        technique=("boiling", "sauteing"), difficulty="easy",
        desc="Le premier de mai des Romains, quand on croque les fèves crues avec le pecorino : "
             "ici, fèves et petits pois sautés à la cébette enrobent des pâtes courtes avec "
             "l'eau de cuisson, le pecorino râpé et la menthe.",
        compo=[
            ("pasta_raw_dried", 320, "g", "carbohydrate"),
            ("broadbeans_fava_beans_raw_fresh", 300, "g", "main_vegetable"),
            ("green_peas_raw", 200, "g", "vegetable"),
            ("green_onion_raw", 100, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("pecorino_sheep", 60, "g", "dairy"),
            ("mint_fresh_herb", 8, "g", "herb"),
            ("lemon_peel_raw", 3, "g", "aromatic"),
            ("water", 3000, "ml", "liquid"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Écosser les fèves (300 g), les blanchir 1 minute à l'eau bouillante et retirer leur "
            "peau.",
            "Cuire 320 g de pâtes courtes dans 3 litres d'eau bouillante salée avec 3 g de sel, "
            "en suivant le temps du paquet (10 minutes environ).",
            "Pendant ce temps, faire fondre 100 g de cébettes émincées dans 40 ml d'huile d'olive, "
            "ajouter 200 g de petits pois, les fèves et 100 ml d'eau de cuisson, et cuire 5 minutes.",
            "Égoutter les pâtes en gardant un peu d'eau, les mélanger aux légumes hors du feu avec "
            "60 g de pecorino râpé et un filet d'eau de cuisson jusqu'à ce que la sauce enrobe.",
            "Finir avec 8 g de menthe ciselée, 3 g de zeste de citron, 1 g de sel et 1 g de poivre.",
        ],
    ),
    recipe(
        rid="curry_matar_paneer_4a7c19",
        fr="Matar paneer, curry de petits pois et paneer",
        en="Matar Paneer, Pea and Paneer Curry",
        original="मटर पनीर",
        cuisine="indian", country="india", region="pendjab",
        dish="main", servings=4, prep=15, cook=30,
        texture=("fondant", "sauce_dense"), taste=("epice", "tomate"),
        technique=("sauteing", "simmering", "boiling"), difficulty="easy", spice=1,
        desc="Classique des tables du nord de l'Inde : des cubes de paneer et des petits pois "
             "mijotés dans une sauce d'oignon, de tomate, d'ail et de gingembre aux épices, "
             "adoucie d'un peu de crème. Servi avec du riz basmati.",
        compo=[
            ("base_paneer_04e1db", 250, "g", "protein"),
            ("green_peas_raw", 300, "g", "main_vegetable"),
            ("tomato_raw_ripe", 300, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("ginger_raw_root_fresh", 10, "g", "aromatic"),
            ("sunflower_oil_plant", 30, "ml", "fat"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("turmeric_powder", 2, "g", "spice"),
            ("coriander_spice_seed", 3, "g", "spice"),
            ("red_hot_chili_pepper_spice_dried", 2, "g", "spice"),
            ("garam_masala", 4, "g", "spice"),
            ("water", 650, "ml", "liquid"),
            ("cream_heavy_refrigerated_30pct", 50, "ml", "dairy"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("basmati_rice_raw_seed", 280, "g", "carbohydrate"),
        ],
        steps=[
            "Rincer 280 g de riz basmati et le cuire dans 450 ml d'eau, 12 minutes à couvert.",
            "Dans 30 ml d'huile, faire grésiller 3 g de cumin, puis dorer 150 g d'oignon haché "
            "8 minutes.",
            "Ajouter 10 g d'ail et 10 g de gingembre râpés, 2 g de curcuma, 3 g de coriandre "
            "moulue et 2 g de piment, et remuer 1 minute.",
            "Ajouter 300 g de tomates mixées et cuire 8 minutes, jusqu'à ce que l'huile se sépare.",
            "Verser 200 ml d'eau, ajouter 300 g de petits pois et 4 g de sel, et cuire 6 minutes.",
            "Ajouter 250 g de paneer en cubes, 4 g de garam masala et 50 ml de crème, mijoter "
            "4 minutes et parsemer de 10 g de coriandre fraîche.",
        ],
    ),
    recipe(
        rid="starter_asperges_a_la_flamande_1e6b84",
        fr="Asperges à la flamande, œuf dur et beurre fondu",
        en="Flemish-Style Asparagus with Egg and Melted Butter",
        original="Asperges op Vlaamse wijze",
        cuisine="belgian", country="belgium", region="flandre", city="malines",
        dish="starter", servings=4, prep=20, cook=20,
        texture=("fondant", "onctueux"), taste=("beurré", "doux"),
        technique=("boiling",), difficulty="easy",
        desc="La façon belge de servir les asperges blanches de Malines : arrosées d'une sauce de "
             "beurre fondu, d'œufs durs écrasés à la fourchette, de persil et d'une pointe de "
             "muscade.",
        compo=[
            ("white_asparagus_raw_peeled", 1000, "g", "main_vegetable"),
            ("egg_raw", 200, "g", "protein"),
            ("butter_sup80pct", 100, "g", "fat"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("nutmeg_spice", 0.5, "g", "spice"),
            ("water", 3000, "ml", "liquid"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Cuire 4 œufs (200 g) 10 minutes à l'eau bouillante, les refroidir et les écaler.",
            "Peler 1 kg d'asperges blanches et les cuire 12 à 15 minutes dans 3 litres d'eau "
            "bouillante salée avec 3 g de sel.",
            "Fondre 100 g de beurre à feu doux sans le colorer.",
            "Écraser les œufs à la fourchette, les mélanger au beurre avec 15 g de persil haché, "
            "0,5 g de muscade, 1 g de sel et 1 g de poivre.",
            "Dresser les asperges égouttées et napper les pointes de sauce aux œufs.",
        ],
    ),

    # ── B. Entrées, accompagnements et soupe ────────────────────────────────────────────────
    recipe(
        rid="side_foul_akhdar_bi_zeit_5b9a63",
        fr="Foul akhdar bi zeit, fèves fraîches à l'huile d'olive et à la coriandre",
        en="Foul Akhdar bi Zeit, Fresh Fava Beans with Olive Oil and Coriander",
        original="فول أخضر بالزيت",
        cuisine="lebanese", country="lebanon", region="mont_liban",
        dish="side", servings=4, prep=20, cook=20,
        texture=("fondant",), taste=("herbacé", "acidulé"),
        technique=("sauteing", "simmering"), difficulty="easy",
        desc="Un plat « à l'huile » de la montagne libanaise, servi tiède ou froid parmi les "
             "mezzés : fèves fraîches étuvées avec l'oignon, l'ail et beaucoup de coriandre, "
             "relevées de citron.",
        compo=[
            ("broadbeans_fava_beans_raw_fresh", 500, "g", "main_vegetable"),
            ("onion_raw", 100, "g", "aromatic"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 50, "ml", "fat"),
            ("coriander_raw_fresh_herb", 30, "g", "herb"),
            ("water", 100, "ml", "liquid"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Faire fondre 100 g d'oignon émincé dans 50 ml d'huile d'olive, 5 minutes.",
            "Ajouter 10 g d'ail haché et la moitié de 30 g de coriandre ciselée, et remuer "
            "1 minute.",
            "Ajouter 500 g de fèves écossées, 100 ml d'eau, 3 g de sel et 1 g de poivre, couvrir "
            "et cuire 15 minutes à feu doux, jusqu'à ce qu'elles soient tendres.",
            "Hors du feu, arroser de 30 ml de jus de citron, ajouter le reste de la coriandre et "
            "servir tiède ou froid.",
        ],
    ),
    recipe(
        rid="side_asperges_goma_ae_8c1f47",
        fr="Asperges goma-ae, asperges vertes à la sauce sésame",
        en="Asparagus Goma-ae, Green Asparagus with Sesame Dressing",
        original="アスパラガスの胡麻和え",
        cuisine="japanese", country="japan", region="",
        dish="side", servings=4, prep=10, cook=10,
        texture=("croquant", "enrobe"), taste=("noisette", "umami"),
        technique=("toasting", "boiling"), difficulty="easy",
        desc="Un petit accompagnement japonais : asperges vertes blanchies, enrobées de graines de "
             "sésame grillées et pilées avec la sauce soja, le sucre et le mirin.",
        compo=[
            ("green_asparagus_raw", 400, "g", "main_vegetable"),
            ("sesame_seed_hulled_dried", 30, "g", "condiment"),
            ("soy_sauce_shoyu_reduced_sodium", 15, "ml", "condiment"),
            ("white_sugar", 8, "g", "seasoning"),
            ("mirin", 10, "ml", "condiment"),
            ("water", 1500, "ml", "liquid"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ],
        steps=[
            "Griller 30 g de graines de sésame à sec 3 minutes, jusqu'à ce qu'elles sentent bon, "
            "puis les piler grossièrement au mortier.",
            "Mélanger le sésame avec 15 ml de sauce soja, 8 g de sucre et 10 ml de mirin.",
            "Couper 400 g d'asperges vertes en tronçons de 4 cm et les blanchir 2 minutes dans "
            "1,5 litre d'eau bouillante salée avec 1 g de sel.",
            "Les rafraîchir, bien les égoutter, puis les enrober de sauce au sésame juste avant "
            "de servir.",
        ],
    ),
    recipe(
        rid="soup_potage_oseille_0f7d29",
        fr="Potage à l'oseille",
        en="Sorrel Soup",
        cuisine="french", country="france", region="",
        dish="soup", servings=4, prep=15, cook=30,
        texture=("cremeux", "lisse"), taste=("acidulé", "lacté"),
        technique=("sauteing", "simmering", "blending"), difficulty="easy",
        desc="Le potage de printemps des jardins français : l'oseille fond dans le beurre, cuit "
             "avec des pommes de terre, puis la soupe mixée est liée à la crème et au jaune d'œuf. "
             "Sa pointe acide se marie au cerfeuil.",
        compo=[
            ("dock_sorrel_raw", 150, "g", "main_vegetable"),
            ("potato_raw_flesh", 400, "g", "carbohydrate"),
            ("onion_raw", 100, "g", "aromatic"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("vegetable_stock_dried", 10, "g", "seasoning"),
            ("water", 1000, "ml", "liquid"),
            ("cream_heavy_refrigerated_30pct", 100, "ml", "dairy"),
            ("egg_yolk_raw", 20, "g", "binder"),
            ("chervil_fresh_herb", 5, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Faire fondre 100 g d'oignon émincé dans 30 g de beurre, 5 minutes.",
            "Ajouter 150 g d'oseille équeutée et la laisser fondre 2 minutes : elle devient vert "
            "olive.",
            "Ajouter 400 g de pommes de terre en cubes, 1 litre d'eau et 10 g de bouillon, et "
            "cuire 20 minutes.",
            "Mixer finement, puis fouetter 100 ml de crème avec 20 g de jaune d'œuf et les verser "
            "dans la soupe hors du feu en remuant.",
            "Rectifier avec 3 g de sel et 1 g de poivre, et servir parsemé de 5 g de cerfeuil.",
        ],
    ),
    recipe(
        rid="side_radis_glaces_miel_3a8e51",
        fr="Radis glacés au beurre et au miel",
        en="Butter and Honey Glazed Radishes",
        cuisine="french", country="france", region="",
        dish="side", servings=4, prep=10, cook=15,
        texture=("fondant", "enrobe"), taste=("légèrement_sucré", "beurré"),
        technique=("caramelizing",), difficulty="easy",
        desc="Les radis roses perdent leur piquant à la cuisson : glacés au beurre et au miel "
             "jusqu'à ce que le jus devienne sirupeux, ils accompagnent une omelette ou une "
             "céréale.",
        compo=[
            ("red_radish_raw", 500, "g", "main_vegetable"),
            ("butter_sup80pct", 25, "g", "fat"),
            ("honey", 15, "g", "sweetener"),
            ("water", 150, "ml", "liquid"),
            ("lemon_juice", 10, "ml", "acidity"),
            ("chives_raw_fresh", 5, "g", "herb"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Laver 500 g de radis roses (deux bottes), garder 1 cm de fane et couper les plus "
            "gros en deux.",
            "Les mettre dans une sauteuse avec 25 g de beurre, 15 g de miel, 150 ml d'eau et 2 g "
            "de sel.",
            "Couvrir d'un papier sulfurisé et cuire 10 minutes à feu moyen.",
            "Retirer le papier et faire réduire 4 minutes en remuant, jusqu'à ce que les radis "
            "soient brillants.",
            "Finir avec 10 ml de jus de citron, 1 g de poivre et 5 g de ciboulette.",
        ],
    ),

    # ── C. Desserts et petit-déjeuner ───────────────────────────────────────────────────────
    recipe(
        rid="dessert_rhubarb_crumble_6d2f80",
        allow_similar=("rhubarb",),
        fr="Rhubarb crumble, crumble anglais à la rhubarbe",
        en="Rhubarb Crumble",
        cuisine="british", country="united_kingdom", region="angleterre",
        dish="dessert", servings=6, prep=20, cook=40,
        texture=("croustillant", "fondant"), taste=("acidulé", "sucré"),
        technique=("baking",), difficulty="easy",
        desc="Le dessert anglais du printemps : des tronçons de rhubarbe sucrés et vanillés sous "
             "un sablage de farine, de beurre, de cassonade et de flocons d'avoine, cuit jusqu'à "
             "ce que le jus bouillonne sur les bords.",
        compo=[
            ("rhubarb_raw_stem", 700, "g", "main_fruit"),
            ("white_sugar", 90, "g", "sweetener"),
            ("vanilla_extract", 5, "ml", "aromatic"),
            ("ginger_powder", 1, "g", "spice"),
            ("wheat_flour_t55", 150, "g", "base"),
            ("butter_sup80pct", 100, "g", "fat"),
            ("brown_sugar", 80, "g", "sweetener"),
            ("oat_flakes_whole_seed", 50, "g", "base"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ],
        steps=[
            "Couper 700 g de rhubarbe en tronçons de 2 cm et les mélanger dans un plat avec 90 g "
            "de sucre, 5 ml de vanille et 1 g de gingembre.",
            "Sabler du bout des doigts 150 g de farine, 100 g de beurre froid en dés et 1 g de sel, "
            "puis ajouter 80 g de cassonade et 50 g de flocons d'avoine.",
            "Répartir la pâte en grumeaux sur la rhubarbe sans tasser.",
            "Cuire 40 minutes au four à 180 °C, jusqu'à ce que le dessus soit doré et que le jus "
            "bouillonne.",
            "Laisser tiédir 10 minutes avant de servir.",
        ],
    ),
    recipe(
        rid="dessert_eton_mess_fraises_2b7a94",
        fr="Eton mess, fraises, meringue et crème fouettée",
        en="Eton Mess with Strawberries",
        original="Eton mess",
        cuisine="british", country="united_kingdom", region="angleterre", city="eton",
        dish="dessert", servings=4, prep=20, rest=60, cook=90,
        texture=("croquant", "cremeux"), taste=("sucré", "frais"),
        technique=("baking", "assembly"), difficulty="easy",
        desc="Le dessert du collège d'Eton, servi au match de cricket contre Harrow : des "
             "fraises, de la crème fouettée et des morceaux de meringue mélangés sans façon "
             "au dernier moment.",
        compo=[
            ("egg_white_raw", 90, "g", "binder"),
            ("white_sugar", 170, "g", "sweetener"),
            ("strawberry_raw", 500, "g", "main_fruit"),
            ("lemon_juice", 10, "ml", "acidity"),
            ("cream_heavy_refrigerated_30pct", 300, "ml", "dairy"),
            ("vanilla_extract", 5, "ml", "aromatic"),
            ("mint_fresh_herb", 4, "g", "herb"),
        ],
        steps=[
            "Monter 90 g de blancs d'œufs en neige ferme en ajoutant peu à peu 150 g de sucre, "
            "jusqu'à ce que la meringue soit brillante.",
            "La déposer en petits tas sur une plaque et cuire 1 h 30 au four à 100 °C, puis "
            "laisser refroidir 1 heure dans le four éteint.",
            "Couper 500 g de fraises en quartiers et les mélanger avec 20 g de sucre et 10 ml de "
            "jus de citron.",
            "Fouetter 300 ml de crème froide avec 5 ml de vanille en chantilly souple.",
            "Juste avant de servir, mélanger grossièrement la crème, les fraises et la meringue "
            "concassée, et décorer de 4 g de menthe.",
        ],
    ),
    recipe(
        rid="dessert_kirschenmichel_cerises_7e3c06",
        fr="Kirschenmichel, pudding de pain aux cerises",
        en="Kirschenmichel, Cherry Bread Pudding",
        original="Kirschenmichel",
        cuisine="german", country="germany", region="palatinat",
        dish="dessert", servings=6, prep=20, rest=15, cook=45,
        texture=("moelleux", "fondant"), taste=("sucré", "acidulé"),
        technique=("baking",), difficulty="easy",
        desc="Le dessert anti-gaspillage du Palatinat : du pain rassis trempé dans le lait sucré "
             "et les œufs, mêlé de cerises et d'amandes, cuit au four jusqu'à ce qu'il gonfle et "
             "dore.",
        compo=[
            ("white_bread_unsalted", 300, "g", "base"),
            ("milk_liquid_uht_3_5pct", 500, "ml", "liquid"),
            ("egg_raw", 200, "g", "binder"),
            ("white_sugar", 100, "g", "sweetener"),
            ("butter_sup80pct", 50, "g", "fat"),
            ("cherry_raw_with_skin", 600, "g", "main_fruit"),
            ("almond_flour", 50, "g", "base"),
            ("cinnamon_powder", 2, "g", "spice"),
            ("vanilla_extract", 5, "ml", "aromatic"),
            ("lemon_peel_raw", 3, "g", "aromatic"),
        ],
        steps=[
            "Couper 300 g de pain rassis en dés, verser dessus 500 ml de lait tiède et laisser "
            "tremper 15 minutes.",
            "Fouetter 40 g de beurre fondu avec 100 g de sucre, puis 4 œufs (200 g), 5 ml de "
            "vanille, 3 g de zeste de citron et 2 g de cannelle.",
            "Mélanger ce mélange au pain avec 50 g d'amandes en poudre, puis incorporer 600 g de "
            "cerises dénoyautées.",
            "Verser dans un plat beurré avec 10 g de beurre et cuire 45 minutes au four à 180 °C, "
            "jusqu'à ce que le dessus soit doré et gonflé.",
            "Servir tiède.",
        ],
    ),
    recipe(
        rid="breakfast_tartine_petits_pois_feta_9a4b72",
        allow_similar=("ecrases",),
        fr="Tartine de petits pois écrasés, feta, radis et menthe",
        en="Smashed Peas on Toast with Feta, Radish and Mint",
        cuisine="british", country="united_kingdom", region="angleterre",
        dish="breakfast", servings=4, prep=15, cook=10,
        texture=("croustillant", "cremeux"), taste=("frais", "herbacé"),
        technique=("boiling", "toasting"), difficulty="easy",
        desc="Un brunch de café londonien : petits pois frais écrasés à l'huile d'olive, au "
             "citron et à la menthe sur du pain au levain grillé, avec de la feta émiettée et "
             "des rondelles de radis.",
        compo=[
            ("sourdough_bread", 300, "g", "carbohydrate"),
            ("green_peas_raw", 400, "g", "main_vegetable"),
            ("feta_cow", 120, "g", "dairy"),
            ("red_radish_raw", 80, "g", "vegetable"),
            ("mint_fresh_herb", 10, "g", "herb"),
            ("lemon_juice", 15, "ml", "acidity"),
            ("olive_oil_extra_virgin_plant", 30, "ml", "fat"),
            ("water", 1000, "ml", "liquid"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("red_hot_chili_pepper_spice_dried", 1, "g", "spice"),
        ],
        steps=[
            "Cuire 400 g de petits pois 4 minutes dans 1 litre d'eau bouillante salée avec 1 g de "
            "sel, puis les égoutter.",
            "Les écraser à la fourchette avec 30 ml d'huile d'olive, 15 ml de jus de citron, 8 g "
            "de menthe ciselée, 1 g de sel et 1 g de poivre.",
            "Griller 4 tranches de pain au levain (300 g).",
            "Étaler les petits pois sur le pain, émietter 120 g de feta dessus et ajouter 80 g de "
            "radis en fines rondelles, 1 g de piment en flocons et le reste de la menthe.",
        ],
    ),
]
