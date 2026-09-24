"""Lot 10 : Moyen-Orient et Turquie (22 recettes).

Manques comblés : Turquie hors soupes de lentilles, Levant hors mezze déjà présents, Iran
(riz et ragoûts), desserts et boissons du Moyen-Orient.
"""
from ._schema import recipe

RECIPES = [
    recipe(
        rid="main_karniyarik_7b31c2",
        fr="Karnıyarık, aubergines farcies aux lentilles et à la tomate",
        en="Karnıyarık, Eggplant Stuffed with Lentils and Tomato",
        original="Karnıyarık",
        cuisine="turkish", country="turkey", region="anatolie_centrale",
        dish="main", prep=30, cook=50,
        texture=("fondant", "moelleux"), taste=("umami", "doux"),
        technique=("fry", "bake"),
        desc="Version végétarienne du karnıyarık : des demi-aubergines frites puis fendues, "
             "garnies d'une farce de lentilles vertes à l'oignon et à la tomate, coiffées d'une "
             "rondelle de tomate et de poivron, et terminées au four dans un fond de jus.",
        compo=[
            ("eggplant_raw", 800, "g", "vegetable"),
            ("green_lentil_dried", 120, "g", "plant_protein", "dried"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("tomato_raw_ripe", 250, "g", "vegetable"),
            ("tomato_paste_unsalted_canned", 30, "g", "condiment"),
            ("green_bell_pepper_raw", 100, "g", "vegetable"),
            ("white_rice_long_grain_seed_dried", 100, "g", "base", "dried"),
            ("olive_oil_plant", 60, "ml", "fat_cooking"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("paprika_powder", 3, "g", "spice"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 300, "ml", "liquid"),
        ],
        steps=[
            "Rincer 120 g de lentilles vertes et les cuire 20 minutes dans de l'eau non salée, "
            "puis les égoutter : elles doivent rester fermes.",
            "Couper 800 g d'aubergines en deux dans la longueur, les saler légèrement et les faire "
            "dorer 8 minutes dans 40 ml d'huile d'olive sur les deux faces.",
            "Dans la même poêle, faire revenir 150 g d'oignon émincé et 10 g d'ail dans le reste "
            "d'huile, 6 minutes, puis ajouter 200 g de tomates concassées, 30 g de concentré, 3 g "
            "de cumin, 3 g de paprika, 4 g de sel et 2 g de poivre.",
            "Incorporer les lentilles et 15 g de persil haché, cuire 5 minutes à feu doux : la "
            "farce doit être sèche.",
            "Fendre les aubergines sur le dessus, les garnir de farce, poser sur chacune une "
            "rondelle de tomate (50 g au total) et une lanière de poivron vert (100 g).",
            "Verser 300 ml d'eau dans le plat et enfourner 30 minutes à 190 °C, jusqu'à ce que le "
            "poivron soit grillé et le jus réduit.",
            "Pendant ce temps, cuire 100 g de riz long à l'eau salée et le servir à côté.",
        ],
    ),
    recipe(
        rid="bread_peynirli_pide_44a0d9",
        fr="Peynirli pide, pain plat turc au fromage",
        en="Peynirli Pide, Turkish Flatbread with Cheese",
        original="Peynirli pide",
        cuisine="turkish", country="turkey", region="mer_noire",
        dish="main", prep=30, rest=90, cook=15,
        texture=("moelleux", "filant"), taste=("salé", "lacté"),
        technique=("knead", "bake"), difficulty="medium",
        desc="Barque de pâte levée turque garnie de mozzarella et de feta, les bords repliés en "
             "navette et un œuf cassé au centre à la sortie du four : la pâte reste moelleuse et "
             "le fromage file.",
        compo=[
            ("wheat_flour_t55", 400, "g", "base"),
            ("bakers_yeast_dehydrated", 5, "g", "ferment"),
            ("water", 250, "ml", "liquid"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("cows_milk_mozzarella_cow", 200, "g", "dairy"),
            ("feta_cow", 100, "g", "dairy"),
            ("egg_raw", 50, "g", "binder"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("black_pepper_spice", 1, "g", "spice"),
        ],
        steps=[
            "Délayer 5 g de levure sèche dans 250 ml d'eau tiède, ajouter 400 g de farine, 5 g de "
            "sel et 15 ml d'huile d'olive, puis pétrir 8 minutes.",
            "Couvrir et laisser lever 90 minutes à température ambiante, jusqu'au doublement.",
            "Diviser la pâte en quatre, étaler chaque part en ovale de 25 cm sur une plaque "
            "farinée.",
            "Mélanger 200 g de mozzarella râpée, 100 g de feta écrasée, 10 g de persil haché et "
            "1 g de poivre, répartir sur les ovales en laissant 2 cm de bord.",
            "Replier les bords sur la garniture et pincer les deux extrémités pour former une "
            "barque, badigeonner avec le reste d'huile.",
            "Enfourner 15 minutes à 240 °C, puis casser l'œuf battu (50 g) au centre de chaque "
            "pide et remettre 2 minutes au four.",
            "Servir brûlant, coupé en tronçons.",
        ],
    ),
    recipe(
        rid="entry_cacik_9d1f4e",
        fr="Cacık, yaourt turc au concombre et à l'aneth",
        en="Cacık, Turkish Yogurt with Cucumber and Dill",
        original="Cacık",
        cuisine="turkish", country="turkey", region="egee",
        dish="starter", prep=15, rest=30,
        texture=("liquide", "frais"), taste=("acide", "herbacé"),
        desc="Yaourt battu allongé d'un peu d'eau glacée, concombre râpé, ail, aneth et menthe : "
             "un mezze très frais que l'on sert aussi comme soupe froide en été.",
        compo=[
            ("yogurt_fermented_plain", 500, "g", "dairy"),
            ("cucumber_raw", 300, "g", "vegetable"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("dill_weed_fresh_herb_leaf", 10, "g", "herb"),
            ("mint_fresh_herb", 8, "g", "herb"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("water", 100, "ml", "liquid"),
        ],
        steps=[
            "Râper 300 g de concombre avec la peau, le saler avec 1 g de sel et le laisser dégorger "
            "10 minutes, puis le presser à la main.",
            "Battre 500 g de yaourt avec 100 ml d'eau glacée jusqu'à obtenir une crème lisse.",
            "Écraser 6 g d'ail avec le reste du sel et l'incorporer au yaourt.",
            "Ajouter le concombre, 10 g d'aneth et 8 g de menthe ciselés, mélanger.",
            "Réserver 30 minutes au frais, puis arroser de 20 ml d'huile d'olive au moment de "
            "servir.",
        ],
        raw=True,
    ),
    recipe(
        rid="soup_yayla_corbasi_2c8a71",
        fr="Yayla çorbası, soupe turque au yaourt et à la menthe",
        en="Yayla Çorbası, Turkish Yogurt and Mint Soup",
        original="Yayla çorbası",
        cuisine="turkish", country="turkey", region="anatolie_orientale",
        dish="soup", prep=15, cook=25,
        texture=("velouté", "onctueux"), taste=("acide", "herbacé"),
        technique=("simmer",), difficulty="medium",
        desc="Soupe de montagne anatolienne : du riz cuit dans un bouillon léger puis lié au "
             "yaourt battu avec un œuf et un peu de farine, finie par un beurre de menthe séchée "
             "versé brûlant.",
        compo=[
            ("yogurt_fermented_plain", 500, "g", "dairy"),
            ("white_rice_short_grain_seed_dried", 80, "g", "base", "dried"),
            ("egg_raw", 50, "g", "binder"),
            ("wheat_flour_t55", 20, "g", "thickener"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("spearmint_dried_herb", 3, "g", "herb"),
            ("vegetable_stock_dried", 6, "g", "seasoning"),
            ("water", 900, "ml", "liquid"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ],
        steps=[
            "Porter 900 ml d'eau à ébullition avec 6 g de bouillon de légumes, verser 80 g de riz "
            "rond et cuire 18 minutes.",
            "Fouetter 500 g de yaourt avec 50 g d'œuf battu et 20 g de farine jusqu'à obtenir un "
            "mélange parfaitement lisse.",
            "Délayer deux louches de bouillon chaud dans le yaourt pour le tempérer.",
            "Verser le yaourt tempéré dans la casserole en fouettant, puis cuire 5 minutes à feu "
            "très doux sans laisser bouillir : la soupe épaissit sans trancher.",
            "Assaisonner de 3 g de sel et 1 g de poivre.",
            "Faire fondre 30 g de beurre avec 3 g de menthe séchée et verser ce beurre parfumé sur "
            "chaque assiette.",
        ],
    ),
    recipe(
        rid="side_pilaki_3e60b8",
        fr="Fasulye pilaki, haricots blancs turcs à l'huile d'olive",
        en="Fasulye Pilaki, Turkish White Beans in Olive Oil",
        original="Fasulye pilaki",
        cuisine="turkish", country="turkey", region="marmara",
        dish="side", prep=20, rest=720, cook=70,
        texture=("fondant",), taste=("doux", "acide"),
        technique=("simmer",),
        desc="Mezze turc servi froid : haricots blancs trempés puis mijotés longuement avec "
             "carotte, oignon et une bonne dose d'huile d'olive, acidulés au citron et parsemés "
             "de persil au moment de servir.",
        compo=[
            ("white_bean_dried_canned", 250, "g", "plant_protein", "dried"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("tomato_paste_unsalted_canned", 30, "g", "condiment"),
            ("olive_oil_extra_virgin_plant", 80, "ml", "fat"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("sugars_granulated", 5, "g", "balance"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("water", 700, "ml", "liquid"),
        ],
        steps=[
            "Faire tremper 250 g de haricots blancs 12 heures dans de l'eau froide, puis les "
            "égoutter.",
            "Faire revenir 150 g d'oignon émincé, 150 g de carotte en rondelles et 12 g d'ail dans "
            "50 ml d'huile d'olive, 8 minutes à feu moyen.",
            "Ajouter 30 g de concentré de tomate, remuer 1 minute, puis verser les haricots et "
            "700 ml d'eau.",
            "Cuire 60 minutes à couvert et à feu doux, jusqu'à ce que les haricots soient fondants "
            "mais entiers ; saler avec 4 g de sel en fin de cuisson.",
            "Ajouter 5 g de sucre et 30 ml de jus de citron, laisser réduire 5 minutes à découvert.",
            "Laisser refroidir complètement, arroser du reste d'huile d'olive et parsemer de 15 g "
            "de persil avant de servir à température ambiante.",
        ],
    ),
    recipe(
        rid="snack_mucver_51d9c4",
        fr="Mücver, galettes turques de courgette à la feta",
        en="Mücver, Turkish Zucchini and Feta Fritters",
        original="Mücver",
        cuisine="turkish", country="turkey", region="egee",
        dish="snack", prep=20, cook=20,
        texture=("croustillant", "moelleux"), taste=("salé", "herbacé"),
        technique=("fry",),
        desc="Galettes de courgette râpée bien essorée, liées à l'œuf et à la farine avec feta, "
             "aneth et oignon vert, frites à la poêle : croustillantes dehors, fondantes dedans, "
             "servies avec du yaourt.",
        compo=[
            ("green_zucchini_squash_raw", 600, "g", "vegetable"),
            ("egg_raw", 100, "g", "binder"),
            ("wheat_flour_t55", 80, "g", "base"),
            ("feta_cow", 100, "g", "dairy"),
            ("dill_weed_fresh_herb_leaf", 10, "g", "herb"),
            ("green_onion_raw", 60, "g", "aromatic"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("sunflower_oil_plant", 60, "ml", "fat_cooking"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("yogurt_fermented_plain", None, "à volonté", "serving_suggestion"),
        ],
        steps=[
            "Râper 600 g de courgettes, les mélanger avec 3 g de sel et laisser dégorger "
            "10 minutes, puis presser fortement dans un linge.",
            "Mélanger les courgettes avec 100 g d'œufs battus, 80 g de farine, 100 g de feta "
            "écrasée, 60 g d'oignon vert émincé, 10 g d'aneth, 10 g de persil et 2 g de poivre.",
            "Chauffer 20 ml d'huile de tournesol dans une poêle et déposer des cuillerées de pâte "
            "aplaties à 1 cm.",
            "Cuire 3 minutes par face à feu moyen, jusqu'à ce que les galettes soient dorées, puis "
            "les égoutter sur papier absorbant.",
            "Répéter avec le reste de la pâte et de l'huile, en essuyant la poêle entre deux "
            "fournées.",
            "Servir chaud avec du yaourt nature.",
        ],
    ),
    recipe(
        rid="dal_fatteh_pois_chiches_a7c503",
        fr="Fatteh de pois chiches au yaourt et au pain grillé",
        en="Chickpea Fatteh with Yogurt and Toasted Bread",
        original="Fatteh hummus",
        cuisine="levantine", country="lebanon", region="beyrouth",
        dish="main", prep=20, rest=720, cook=75,
        texture=("croustillant", "crémeux"), taste=("acide", "umami"),
        technique=("boil", "toast"),
        desc="Plat de partage levantin monté en couches : pain pita grillé au fond, pois chiches "
             "chauds par-dessus, sauce au yaourt et tahini, beurre noisette et pignons grillés "
             "pour finir.",
        compo=[
            ("chickpea_raw_dried", 200, "g", "plant_protein", "dried"),
            ("yogurt_fermented_plain", 400, "g", "dairy"),
            ("sesame_tahini_raw_butter_seed_plant", 60, "ml", "condiment"),
            ("white_pita_bread", 150, "g", "base"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("pine_nuts_raw", 30, "g", "garnish"),
            ("butter_sup80pct", 20, "g", "fat"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("water", 1000, "ml", "liquid"),
        ],
        steps=[
            "Faire tremper 200 g de pois chiches 12 heures, puis les cuire 70 minutes dans 1 L "
            "d'eau non salée jusqu'à ce qu'ils s'écrasent entre les doigts.",
            "Couper 150 g de pain pita en carrés et les griller 8 minutes à 200 °C jusqu'à ce "
            "qu'ils soient secs et dorés.",
            "Fouetter 400 g de yaourt avec 60 ml de tahini, 30 ml de jus de citron, 10 g d'ail "
            "écrasé, 3 g de cumin et 4 g de sel.",
            "Faire dorer 30 g de pignons dans 20 g de beurre, 2 minutes, jusqu'à ce qu'ils soient "
            "blonds.",
            "Répartir le pain grillé dans un plat creux, l'humecter de quelques cuillerées d'eau de "
            "cuisson, puis couvrir des pois chiches égouttés et encore chauds.",
            "Napper de sauce au yaourt, verser le beurre aux pignons et parsemer de 10 g de "
            "persil ; servir aussitôt pour garder le contraste croustillant.",
        ],
    ),
    recipe(
        rid="side_loubieh_bi_zeit_6f2b19",
        fr="Loubieh bi zeit, haricots verts libanais à l'huile d'olive",
        en="Loubieh bi Zeit, Lebanese Green Beans in Olive Oil",
        original="Loubieh bi zeit",
        cuisine="lebanese", country="lebanon", region="mont_liban",
        dish="side", prep=15, cook=35,
        texture=("fondant",), taste=("doux", "herbacé"),
        technique=("simmer",),
        desc="Haricots verts longuement mijotés dans l'huile d'olive avec tomate, oignon et ail, "
             "jusqu'à ce qu'ils perdent tout croquant : un mezze du Levant servi tiède ou froid.",
        compo=[
            ("french_bean_raw", 600, "g", "vegetable"),
            ("tomato_raw_ripe", 300, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("olive_oil_plant", 60, "ml", "fat"),
            ("coriander", 10, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("water", 100, "ml", "liquid"),
        ],
        steps=[
            "Équeuter 600 g de haricots verts et les couper en tronçons de 4 cm.",
            "Faire fondre 150 g d'oignon émincé dans 60 ml d'huile d'olive, 8 minutes à feu doux, "
            "sans coloration.",
            "Ajouter 12 g d'ail et 10 g de coriandre hachée, remuer 1 minute.",
            "Incorporer 300 g de tomates concassées, 3 g de sel et 1 g de poivre, cuire 5 minutes.",
            "Ajouter les haricots et 100 ml d'eau, couvrir et mijoter 25 minutes : les haricots "
            "doivent être complètement tendres et la sauce réduite.",
            "Laisser tiédir avant de servir, avec du pain plat.",
        ],
    ),
    recipe(
        rid="main_bamia_8d40f6",
        fr="Bamia, gombos mijotés à la tomate et à la coriandre",
        en="Bamia, Okra Stewed with Tomato and Coriander",
        original="Bamia",
        cuisine="levantine", country="jordan", region="amman",
        dish="main", prep=20, cook=40,
        texture=("fondant", "sirupeux"), taste=("acide", "umami"),
        technique=("simmer",),
        desc="Ragoût de gombos du Levant : les gombos entiers restent fermes dans une sauce "
             "tomate à l'ail et à la coriandre, acidulée au citron pour couper le mucilage, servi "
             "avec du riz.",
        compo=[
            ("okra", 700, "g", "vegetable"),
            ("tomato_raw_ripe", 400, "g", "vegetable"),
            ("tomato_paste_unsalted_canned", 40, "g", "condiment"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("olive_oil_plant", 45, "ml", "fat_cooking"),
            ("coriander", 15, "g", "herb"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("white_rice_long_grain_seed_dried", 200, "g", "base", "dried"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("water", 500, "ml", "liquid"),
        ],
        steps=[
            "Laver 700 g de gombos, couper la base sans ouvrir la gousse pour limiter le "
            "mucilage.",
            "Faire revenir 150 g d'oignon dans 45 ml d'huile d'olive, 6 minutes, puis ajouter 12 g "
            "d'ail et 3 g de cumin.",
            "Ajouter 400 g de tomates concassées et 40 g de concentré, cuire 5 minutes jusqu'à ce "
            "que la sauce fonce.",
            "Déposer les gombos en une seule couche, verser 300 ml d'eau et 4 g de sel, couvrir et "
            "mijoter 25 minutes sans remuer.",
            "Ajouter 30 ml de jus de citron et 15 g de coriandre hachée, cuire 3 minutes à "
            "découvert.",
            "Cuire 200 g de riz long dans 200 ml d'eau et le reste d'eau bouillante, puis servir "
            "les gombos dessus.",
        ],
    ),
    recipe(
        rid="rice_maqluba_legumes_c15e82",
        fr="Maqluba de légumes, riz renversé aux aubergines et chou-fleur",
        en="Vegetable Maqluba, Upside-Down Rice with Eggplant and Cauliflower",
        original="Maqluba",
        cuisine="palestinian", country="palestine", region="naplouse",
        dish="main", prep=35, cook=45,
        texture=("fondant", "grenu"), taste=("épicé", "umami"),
        technique=("fry", "steam"), difficulty="medium",
        desc="Riz palestinien cuit dans une marmite tapissée d'aubergines et de chou-fleur frits, "
             "parfumé cannelle et cumin, que l'on renverse d'un geste sur le plat de service ; les "
             "légumes forment le dessus doré.",
        compo=[
            ("white_rice_long_grain_seed_dried", 300, "g", "base", "dried"),
            ("eggplant_raw", 400, "g", "vegetable"),
            ("cauliflower_raw_flower", 400, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("sunflower_oil_plant", 80, "ml", "fat_cooking"),
            ("cinnamon", 3, "g", "spice"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("turmeric_powder", 2, "g", "spice"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("pine_nuts_raw", 30, "g", "garnish"),
            ("vegetable_stock_dried", 6, "g", "seasoning"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 600, "ml", "liquid"),
            ("yogurt_fermented_plain", None, "en accompagnement", "serving_suggestion"),
        ],
        steps=[
            "Rincer 300 g de riz et le laisser tremper 20 minutes dans de l'eau froide.",
            "Couper 400 g d'aubergines en rondelles et détailler 400 g de chou-fleur en bouquets, "
            "les faire dorer par fournées dans 70 ml d'huile de tournesol, 10 minutes en tout.",
            "Faire revenir 150 g d'oignon émincé dans le reste d'huile, puis ajouter 3 g de "
            "cannelle, 3 g de cumin, 2 g de curcuma, 2 g de poivre et 5 g de sel.",
            "Tapisser le fond d'une marmite des rondelles d'aubergine, ajouter le chou-fleur puis "
            "l'oignon épicé, et couvrir du riz égoutté sans mélanger.",
            "Verser 600 ml d'eau chaude additionnée de 6 g de bouillon, porter à frémissement, "
            "couvrir et cuire 30 minutes à feu très doux.",
            "Laisser reposer 10 minutes hors du feu, puis retourner la marmite d'un coup sur un "
            "grand plat.",
            "Parsemer de 30 g de pignons grillés et servir avec du yaourt.",
        ],
    ),
    recipe(
        rid="main_freekeh_legumes_rotis_9a2d47",
        fr="Freekeh aux légumes rôtis et pois chiches",
        en="Freekeh with Roasted Vegetables and Chickpeas",
        cuisine="levantine", country="syria", region="alep",
        dish="main", prep=20, cook=40,
        texture=("grenu", "fondant"), taste=("fumé", "umami"),
        technique=("roast", "simmer"),
        desc="Le freekeh, blé vert grillé au goût fumé, mijoté en pilaf puis mélangé à des "
             "courgettes, poivrons et tomates rôtis et à des pois chiches, relevé de cumin et de "
             "cannelle et rafraîchi au citron.",
        compo=[
            ("freekeh_immature_wheat_raw_cracked_seed", 250, "g", "base", "dried"),
            ("green_zucchini_squash_raw", 250, "g", "vegetable"),
            ("green_bell_pepper_raw", 200, "g", "vegetable"),
            ("tomato_raw_ripe", 200, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("chickpea_rinsed_canned", 200, "g", "plant_protein", "cooked"),
            ("olive_oil_plant", 60, "ml", "fat"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("cinnamon", 2, "g", "spice"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 600, "ml", "liquid"),
        ],
        steps=[
            "Couper 250 g de courgette, 200 g de poivron vert et 200 g de tomates en gros dés, les "
            "mélanger à 30 ml d'huile d'olive, 2 g de sel et 2 g de poivre.",
            "Rôtir les légumes 30 minutes à 210 °C, en remuant à mi-cuisson, jusqu'aux bords "
            "colorés.",
            "Rincer 250 g de freekeh, le faire revenir 2 minutes avec 150 g d'oignon émincé dans "
            "le reste d'huile, avec 3 g de cumin et 2 g de cannelle.",
            "Verser 600 ml d'eau chaude et 2 g de sel, couvrir et cuire 25 minutes à feu doux "
            "jusqu'à absorption.",
            "Ajouter 200 g de pois chiches égouttés dans le freekeh, laisser 5 minutes à couvert "
            "pour les réchauffer.",
            "Mélanger les légumes rôtis, 30 ml de jus de citron et 15 g de persil haché, puis "
            "servir tiède.",
        ],
    ),
    recipe(
        rid="main_kousa_mahshi_2f9e6b",
        fr="Kousa mahshi, courgettes farcies au riz et à la menthe",
        en="Kousa Mahshi, Zucchini Stuffed with Rice and Mint",
        original="Kousa mahshi",
        cuisine="lebanese", country="lebanon", region="bekaa",
        dish="main", prep=40, cook=45,
        texture=("fondant",), taste=("doux", "herbacé"),
        technique=("simmer",), difficulty="medium",
        desc="Courgettes évidées à la cuillère puis farcies d'un riz cru assaisonné de tomate, "
             "cannelle et menthe, cuites debout dans un bouillon tomaté qui finit de cuire le riz "
             "à l'intérieur.",
        compo=[
            ("green_zucchini_squash_raw", 900, "g", "vegetable"),
            ("white_rice_short_grain_seed_dried", 150, "g", "base", "dried"),
            ("tomato_raw_ripe", 300, "g", "vegetable"),
            ("tomato_paste_unsalted_canned", 30, "g", "condiment"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("olive_oil_plant", 45, "ml", "fat"),
            ("mint_fresh_herb", 8, "g", "herb"),
            ("cinnamon", 2, "g", "spice"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 500, "ml", "liquid"),
        ],
        steps=[
            "Couper le pédoncule de 900 g de courgettes courtes et les évider à la cuillère à "
            "melon en laissant 5 mm de paroi.",
            "Mélanger 150 g de riz rond rincé, 100 g de tomates en dés, 100 g d'oignon râpé, 8 g "
            "de menthe ciselée, 2 g de cannelle, 2 g de sel et 2 g de poivre avec 15 ml d'huile.",
            "Remplir les courgettes aux trois quarts avec la farce, sans tasser : le riz va "
            "gonfler.",
            "Faire revenir 10 g d'ail dans le reste d'huile, ajouter 200 g de tomates concassées, "
            "30 g de concentré, 500 ml d'eau et 2 g de sel, porter à frémissement.",
            "Ranger les courgettes debout dans la sauce, couvrir et cuire 40 minutes à feu doux.",
            "Laisser reposer 5 minutes hors du feu, puis servir les courgettes nappées de leur "
            "sauce.",
        ],
    ),
    recipe(
        rid="dairy_labneh_herbes_5c71a0",
        fr="Labneh maison aux herbes et au za'atar",
        en="Homemade Labneh with Herbs and Za'atar",
        original="Labneh",
        cuisine="levantine", country="lebanon", region="mont_liban",
        dish="starter", prep=10, rest=720,
        texture=("crémeux", "épais"), taste=("acide", "herbacé"),
        desc="Yaourt salé égoutté une nuit dans une étamine jusqu'à devenir un fromage frais "
             "tartinable, servi en assiette creuse avec beaucoup d'huile d'olive, du za'atar et "
             "du sumac.",
        compo=[
            ("yogurt_fermented_plain", 800, "g", "dairy"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("base_za_atar_2badf3", 15, "g", "condiment"),
            ("sumac", 2, "g", "spice"),
            ("mint_fresh_herb", 5, "g", "herb"),
        ],
        steps=[
            "Mélanger 800 g de yaourt avec 4 g de sel.",
            "Verser le yaourt dans une étamine posée sur une passoire, refermer et laisser égoutter "
            "12 heures au réfrigérateur.",
            "Récupérer le labneh : il doit être assez ferme pour former une boule à la cuillère.",
            "L'étaler dans une assiette creuse en creusant un sillon à la cuillère.",
            "Arroser de 40 ml d'huile d'olive, saupoudrer de 15 g de za'atar et 2 g de sumac.",
            "Parsemer de 5 g de menthe ciselée et servir avec du pain plat.",
        ],
    ),
    recipe(
        rid="main_khoresh_bademjan_b62c85",
        fr="Khoresh bademjan, ragoût persan d'aubergines aux pois chiches",
        en="Khoresh Bademjan, Persian Eggplant Stew with Chickpeas",
        original="Khoresh bademjan",
        cuisine="persian", country="iran", region="teheran",
        dish="main", prep=25, cook=55,
        texture=("fondant",), taste=("acide", "umami"),
        technique=("fry", "simmer"),
        desc="Ragoût iranien d'aubergines dorées à l'huile puis mijotées dans une sauce tomate au "
             "curcuma, acidulée au jus de citron ; les pois chiches remplacent l'agneau et le plat "
             "se mange avec du riz blanc.",
        compo=[
            ("eggplant_raw", 700, "g", "vegetable"),
            ("tomato_raw_ripe", 400, "g", "vegetable"),
            ("onion_raw", 200, "g", "aromatic_base"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("tomato_paste_unsalted_canned", 40, "g", "condiment"),
            ("chickpea_rinsed_canned", 250, "g", "plant_protein", "cooked"),
            ("sunflower_oil_plant", 80, "ml", "fat_cooking"),
            ("turmeric_powder", 4, "g", "spice"),
            ("cinnamon", 2, "g", "spice"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 400, "ml", "liquid"),
            ("white_rice_long_grain_seed_dried", None, "en accompagnement", "serving_suggestion"),
        ],
        steps=[
            "Couper 700 g d'aubergines en quartiers dans la longueur, les saler avec 1 g de sel et "
            "laisser dégorger 15 minutes.",
            "Les faire dorer par fournées dans 60 ml d'huile de tournesol, 10 minutes, puis les "
            "réserver sur papier absorbant.",
            "Faire blondir 200 g d'oignon émincé dans le reste d'huile, 8 minutes, ajouter 10 g "
            "d'ail, 4 g de curcuma et 2 g de cannelle.",
            "Ajouter 40 g de concentré de tomate et 400 g de tomates concassées, cuire 5 minutes.",
            "Verser 400 ml d'eau, 3 g de sel et 2 g de poivre, remettre les aubergines et mijoter "
            "30 minutes à couvert sans remuer.",
            "Ajouter 250 g de pois chiches égouttés et 30 ml de jus de citron, poursuivre "
            "10 minutes à découvert pour réduire la sauce.",
            "Servir avec du riz blanc.",
        ],
        allow_similar=("bademjan",),
    ),
    recipe(
        rid="egg_kuku_sabzi_d3b408",
        fr="Kuku sabzi, omelette persane aux herbes et aux noix",
        en="Kuku Sabzi, Persian Herb Frittata with Walnuts",
        original="Kuku sabzi",
        cuisine="persian", country="iran", region="chiraz",
        dish="main", prep=25, cook=25,
        texture=("moelleux",), taste=("herbacé", "umami"),
        technique=("fry",), difficulty="medium",
        desc="Omelette iranienne où les herbes dominent l'œuf : persil, coriandre, aneth et oignon "
             "vert hachés très fin, épinards, éclats de noix, cuite doucement à la poêle jusqu'à "
             "une tranche vert sombre.",
        compo=[
            ("egg_raw", 300, "g", "animal_protein"),
            ("parsley_fresh_herb", 100, "g", "herb"),
            ("coriander", 60, "g", "herb"),
            ("dill_weed_fresh_herb_leaf", 60, "g", "herb"),
            ("green_onion_raw", 100, "g", "aromatic"),
            ("spinach", 100, "g", "vegetable"),
            ("walnut_shelled_dried", 40, "g", "nut"),
            ("wheat_flour_t55", 20, "g", "binder"),
            ("turmeric_powder", 2, "g", "spice"),
            ("sunflower_oil_plant", 60, "ml", "fat_cooking"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Hacher finement 100 g de persil, 60 g de coriandre, 60 g d'aneth, 100 g d'oignon vert "
            "et 100 g d'épinards.",
            "Battre 300 g d'œufs avec 20 g de farine, 2 g de curcuma, 4 g de sel et 2 g de poivre.",
            "Incorporer les herbes et 40 g de noix concassées : le mélange doit être très vert et "
            "à peine liquide.",
            "Chauffer 40 ml d'huile dans une poêle de 24 cm, verser l'appareil et égaliser.",
            "Couvrir et cuire 15 minutes à feu doux, jusqu'à ce que le dessus soit pris.",
            "Retourner la kuku à l'aide d'une assiette, ajouter le reste d'huile et cuire "
            "10 minutes de l'autre côté.",
            "Laisser tiédir et couper en parts, servir avec du yaourt et du pain plat.",
        ],
    ),
    recipe(
        rid="rice_tahchin_e48a16",
        fr="Tahchin, gâteau de riz persan au safran et au yaourt",
        en="Tahchin, Persian Saffron Rice Cake with Yogurt",
        original="Tahchin",
        cuisine="persian", country="iran", region="isfahan",
        dish="main", prep=25, rest=30, cook=60,
        texture=("croustillant", "grenu"), taste=("doux", "lacté"),
        technique=("bake",), difficulty="hard",
        desc="Riz basmati précuit mélangé à du yaourt, de l'œuf et du safran, tassé dans un moule "
             "beurré et cuit jusqu'à former une croûte dorée que l'on démoule d'un bloc : le "
             "tahdig devient le dessus du gâteau.",
        compo=[
            ("white_rice_long_grain_seed_dried", 300, "g", "base", "dried"),
            ("yogurt_fermented_plain", 300, "g", "dairy"),
            ("egg_raw", 100, "g", "binder"),
            ("saffron", 0.3, "g", "spice"),
            ("butter_sup80pct", 60, "g", "fat"),
            ("pistachio_nuts_raw", 30, "g", "garnish"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 1500, "ml", "liquid"),
        ],
        steps=[
            "Rincer 300 g de riz basmati et le laisser tremper 30 minutes dans de l'eau salée.",
            "Le cuire 6 minutes dans 1,5 L d'eau bouillante avec 3 g de sel, puis l'égoutter : les "
            "grains doivent rester fermes au cœur.",
            "Infuser 0,3 g de safran pilé dans 20 ml d'eau chaude, puis le mélanger à 300 g de "
            "yaourt, 100 g d'œufs battus, 2 g de sel et 30 g de beurre fondu.",
            "Mélanger un tiers du riz à l'appareil au yaourt et l'étaler au fond d'un moule beurré "
            "avec le reste du beurre.",
            "Couvrir du riz restant, tasser légèrement et fermer le moule avec un papier cuisson.",
            "Enfourner 60 minutes à 180 °C, jusqu'à ce que le fond soit doré et se détache.",
            "Laisser reposer 5 minutes, démouler à l'envers sur un plat et parsemer de 30 g de "
            "pistaches concassées.",
        ],
    ),
    recipe(
        rid="rice_adas_polo_74c1d9",
        fr="Adas polo, riz persan aux lentilles et aux dattes",
        en="Adas Polo, Persian Rice with Lentils and Dates",
        original="Adas polo",
        cuisine="persian", country="iran", region="yazd",
        dish="main", prep=25, cook=45,
        texture=("grenu", "fondant"), taste=("sucré", "épicé"),
        technique=("steam",), difficulty="medium",
        desc="Riz basmati dressé en couches avec des lentilles cuites, des oignons frits et des "
             "dattes caramélisées à la cannelle : un plat iranien à la fois sucré et épicé, cuit à "
             "l'étouffée pour obtenir une croûte au fond.",
        compo=[
            ("white_rice_long_grain_seed_dried", 250, "g", "base", "dried"),
            ("green_lentil_dried", 150, "g", "plant_protein", "dried"),
            ("date_with_skin_dried", 100, "g", "fruit"),
            ("onion_raw", 200, "g", "aromatic_base"),
            ("sunflower_oil_plant", 50, "ml", "fat_cooking"),
            ("cinnamon", 3, "g", "spice"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("turmeric_powder", 2, "g", "spice"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 1200, "ml", "liquid"),
        ],
        steps=[
            "Cuire 150 g de lentilles vertes 20 minutes dans de l'eau non salée, puis les "
            "égoutter.",
            "Rincer 250 g de riz basmati et le cuire 6 minutes dans 1,2 L d'eau bouillante salée "
            "(3 g), puis l'égoutter.",
            "Faire frire 200 g d'oignon émincé dans 35 ml d'huile, 12 minutes, jusqu'au brun "
            "doré ; en réserver la moitié.",
            "Ajouter 100 g de dattes dénoyautées coupées en deux, 3 g de cannelle, 3 g de cumin et "
            "2 g de curcuma, cuire 3 minutes.",
            "Dans une marmite huilée avec le reste d'huile, alterner riz, lentilles et mélange aux "
            "dattes, en terminant par du riz en dôme.",
            "Couvrir d'un linge et du couvercle, cuire 25 minutes à feu très doux pour former la "
            "croûte.",
            "Renverser sur un plat, saler avec 2 g de sel et parsemer des oignons frits réservés.",
        ],
    ),
    recipe(
        rid="dessert_malabi_1e7f53",
        fr="Malabi, crème de lait à l'eau de rose et à la grenade",
        en="Malabi, Rose Water Milk Pudding with Pomegranate",
        original="Malabi",
        cuisine="levantine", country="israel", region="tel_aviv",
        dish="dessert", prep=15, rest=180, cook=10,
        texture=("crémeux", "tremblotant"), taste=("sucré", "floral"),
        technique=("simmer",),
        desc="Crème de lait prise à la fécule, parfumée à l'eau de rose et servie très froide sous "
             "un sirop rose, avec des pistaches concassées et des graines de grenade pour le "
             "croquant.",
        compo=[
            ("milk_liquid_pasteurized_3_5pct", 800, "ml", "dairy"),
            ("cornstarch_flour", 70, "g", "thickener"),
            ("sugars_granulated", 80, "g", "sweetener"),
            ("rose_water", 15, "ml", "aroma"),
            ("pistachio_nuts_raw", 30, "g", "garnish"),
            ("pomegranate_raw", 100, "g", "fruit"),
        ],
        steps=[
            "Délayer 70 g de fécule de maïs dans 150 ml de lait froid prélevé sur les 800 ml.",
            "Chauffer le reste du lait avec 60 g de sucre jusqu'aux premiers frémissements.",
            "Verser la fécule délayée en fouettant et cuire 3 minutes : la crème doit napper la "
            "cuillère.",
            "Hors du feu, ajouter 10 ml d'eau de rose, puis répartir dans quatre coupes.",
            "Filmer au contact et réfrigérer 3 heures jusqu'à prise complète.",
            "Faire un sirop avec 20 g de sucre, 30 ml d'eau et 5 ml d'eau de rose, laisser "
            "refroidir.",
            "Napper les crèmes de sirop, parsemer de 30 g de pistaches concassées et de 100 g de "
            "graines de grenade.",
        ],
    ),
    recipe(
        rid="dessert_om_ali_36b9e4",
        fr="Om Ali, gratin égyptien de pâte filo au lait",
        en="Om Ali, Egyptian Filo and Milk Pudding",
        original="Om Ali",
        cuisine="egyptian", country="egypt", region="le_caire",
        dish="dessert", prep=15, cook=35,
        texture=("fondant", "croustillant"), taste=("sucré", "lacté"),
        technique=("bake",),
        desc="Dessert égyptien de fête : de la pâte filo cuite à sec puis émiettée, noyée de lait "
             "sucré à la cannelle avec noix et pistaches, gratinée jusqu'à ce que le dessus "
             "croustille et que le dessous reste crémeux.",
        compo=[
            ("phyllo_filo_pastry_raw_paste", 200, "g", "base"),
            ("milk_liquid_pasteurized_3_5pct", 600, "ml", "dairy"),
            ("sugars_granulated", 70, "g", "sweetener"),
            ("pistachio_nuts_raw", 30, "g", "nut"),
            ("walnut_shelled_dried", 40, "g", "nut"),
            ("cinnamon", 2, "g", "spice"),
            ("rose_water", 10, "ml", "aroma"),
        ],
        steps=[
            "Étaler 200 g de pâte filo froissée sur une plaque et la cuire 12 minutes à 190 °C "
            "jusqu'à ce qu'elle soit dorée et cassante.",
            "Émietter la pâte refroidie dans un plat à gratin.",
            "Parsemer de 30 g de pistaches et 40 g de noix concassées et de 2 g de cannelle.",
            "Chauffer 600 ml de lait avec 70 g de sucre sans le faire bouillir, puis ajouter 10 ml "
            "d'eau de rose.",
            "Verser le lait chaud sur la pâte et appuyer à la cuillère pour l'imbiber.",
            "Enfourner 20 minutes à 200 °C, jusqu'à ce que le dessus soit doré et le lait "
            "absorbé ; servir tiède.",
        ],
    ),
    recipe(
        rid="sauce_zhug_yemenite_0a5d76",
        fr="Zhug, sauce yéménite à la coriandre et au piment vert",
        en="Zhug, Yemeni Green Chili and Coriander Sauce",
        original="Zhug",
        cuisine="yemeni", country="yemen", region="sanaa",
        dish="condiment", servings=8, prep=15,
        texture=("épais", "granuleux"), taste=("piquant", "herbacé"),
        spice=4, kid_friendly=False,
        desc="Sauce verte yéménite très piquante : coriandre et persil pilés avec du piment vert, "
             "de l'ail, du cumin et de la cardamome, montés à l'huile d'olive ; une cuillerée "
             "relève soupes, falafels et pains plats.",
        compo=[
            ("coriander", 100, "g", "herb"),
            ("parsley_fresh_herb", 50, "g", "herb"),
            ("red_hot_chili_pepper_raw", 60, "g", "spice"),
            ("garlic_raw", 20, "g", "aromatic"),
            ("cumin_spice_seed", 5, "g", "spice"),
            ("cardamom_powder", 2, "g", "spice"),
            ("olive_oil_plant", 100, "ml", "fat"),
            ("lemon_juice", 20, "ml", "acidity"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Laver et essorer 100 g de coriandre et 50 g de persil, tiges tendres comprises.",
            "Épépiner partiellement 60 g de piments verts frais selon la force souhaitée.",
            "Piler 20 g d'ail avec 4 g de sel, 5 g de cumin et 2 g de cardamome au mortier.",
            "Ajouter les herbes et les piments et piler jusqu'à obtenir une pâte grossière (ou "
            "mixer par impulsions).",
            "Monter la sauce en versant 100 ml d'huile d'olive en filet, puis ajouter 20 ml de jus "
            "de citron.",
            "Conserver au frais dans un bocal couvert d'un film d'huile, jusqu'à une semaine.",
        ],
        raw=True,
    ),
    recipe(
        rid="beverage_sahlab_8c04f2",
        fr="Sahlab, boisson chaude au lait et à l'eau de rose",
        en="Sahlab, Hot Milk Drink with Rose Water",
        original="Sahlab",
        cuisine="levantine", country="lebanon", region="beyrouth",
        dish="beverage", prep=5, cook=10, meal="beverage",
        texture=("onctueux",), taste=("sucré", "floral"),
        technique=("simmer",),
        desc="Boisson d'hiver du Levant, à mi-chemin entre le lait chaud et la crème : lait lié à "
             "la fécule, sucré et parfumé à l'eau de rose, servi en tasse avec cannelle et "
             "pistaches.",
        compo=[
            ("milk_liquid_pasteurized_3_5pct", 800, "ml", "dairy"),
            ("cornstarch_flour", 40, "g", "thickener"),
            ("sugars_granulated", 50, "g", "sweetener"),
            ("rose_water", 10, "ml", "aroma"),
            ("cinnamon", 2, "g", "spice"),
            ("pistachio_nuts_raw", 20, "g", "garnish"),
        ],
        steps=[
            "Délayer 40 g de fécule de maïs dans 100 ml de lait froid prélevé sur les 800 ml.",
            "Chauffer le reste du lait avec 50 g de sucre à feu moyen, sans bouillir.",
            "Verser la fécule en fouettant et cuire 4 minutes : la boisson doit épaissir sans "
            "devenir une crème ferme.",
            "Hors du feu, parfumer avec 10 ml d'eau de rose.",
            "Verser en tasses, saupoudrer de 2 g de cannelle et de 20 g de pistaches concassées, "
            "servir très chaud.",
        ],
    ),
    recipe(
        rid="beverage_limonana_5b2e08",
        fr="Limonana, limonade glacée à la menthe",
        en="Limonana, Frozen Mint Lemonade",
        original="Limonana",
        cuisine="levantine", country="israel", region="tel_aviv",
        dish="beverage", prep=10, rest=60, meal="beverage",
        texture=("granité", "mousseux"), taste=("acide", "herbacé"),
        desc="Limonade du Levant mixée avec de la glace et une grosse poignée de menthe jusqu'à "
             "obtenir un granité vert pâle et mousseux, ni sirupeux ni trop acide.",
        compo=[
            ("lemon_juice", 150, "ml", "acidity"),
            ("mint_fresh_herb", 20, "g", "herb"),
            ("sugars_granulated", 70, "g", "sweetener"),
            ("water", 800, "ml", "liquid"),
        ],
        steps=[
            "Dissoudre 70 g de sucre dans 100 ml d'eau chaude, puis laisser refroidir ce sirop.",
            "Congeler 400 ml d'eau en glaçons, au moins une heure.",
            "Mixer les glaçons avec 150 ml de jus de citron, le sirop, 20 g de menthe et 300 ml "
            "d'eau froide, 30 secondes à pleine puissance.",
            "Goûter et rectifier l'équilibre sucre-citron selon la maturité des citrons.",
            "Servir aussitôt dans des verres glacés, avec quelques feuilles de menthe entières.",
        ],
        raw=True,
    ),
]
