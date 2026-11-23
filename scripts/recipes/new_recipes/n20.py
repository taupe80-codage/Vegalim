"""Lot 20 : plats d'hiver (16 recettes, 2026-11-23).

Mesure du 2026-11-23 : 108 plats principaux sur 462 de saison de décembre à février
(season_ratio ≥ 0,5). Ce lot met au centre les légumes que le calendrier tient pour
de saison tout l'hiver — céleri-rave, panais, topinambour, poireau, chou, kale,
choux de Bruxelles, navet, endive, chou-fleur, courge, épinard — et les fruits
d'hiver (poire, pomme, orange, kiwi), avec plusieurs plats complets riches en
protéines (lentilles, pois cassés, seitan, tofu fumé, sarrasin).
"""
from ._schema import recipe

RECIPES = [
    # ── A. Plats complets ─────────────────────────────────────────────────────────────────
    recipe(
        rid="main_potee_lentilles_chou_tofu_fume_8d1f52",
        fr="Potée de lentilles vertes au chou et au tofu fumé",
        en="Green Lentil and Cabbage Stew with Smoked Tofu",
        cuisine="french", country="france",
        dish="main", servings=4, prep=15, cook=40,
        texture=("fondant", "bouillon_riche"), taste=("fumé", "terreux"),
        technique=("sauteing", "simmering"), difficulty="easy",
        desc="La potée des soirs froids sans lard : lentilles vertes, chou vert, carottes et "
             "tofu fumé qui donne au bouillon son goût de feu de bois, relevée de moutarde au "
             "moment de servir.",
        compo=[
            ("green_lentil_dried", 250, "g", "plant_protein"),
            ("tofu_smoked_pre_packaged", 200, "g", "plant_protein"),
            ("green_cabbage_raw", 500, "g", "main_vegetable"),
            ("carrot_raw", 300, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("bay_leaf_spice", 1, "g", "herb"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("vegetable_stock_dried", 12, "g", "seasoning"),
            ("water", 1200, "ml", "liquid"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("mustard", 20, "g", "condiment"),
        ],
        steps=[
            "Faire revenir 150 g d'oignon émincé et 10 g d'ail 5 minutes dans 20 ml d'huile "
            "d'olive, dans une cocotte.",
            "Ajouter 300 g de carottes en rondelles, 250 g de lentilles vertes rincées, 1 feuille "
            "de laurier, 3 g de thym, 12 g de bouillon de légumes et 1,2 l d'eau ; porter à "
            "ébullition.",
            "Ajouter 500 g de chou vert émincé grossièrement et laisser mijoter 30 minutes à "
            "couvert, jusqu'à ce que les lentilles soient tendres.",
            "Ajouter 200 g de tofu fumé en dés pour les 5 dernières minutes, puis servir avec "
            "20 g de moutarde à part.",
        ],
        allow_similar=("potee",),
    ),
    recipe(
        rid="main_pot_au_feu_seitan_legumes_hiver_3a6c94",
        fr="Pot-au-feu végétal au seitan et légumes d'hiver",
        en="Plant-Based Pot-au-Feu with Seitan and Winter Vegetables",
        cuisine="french", country="france",
        dish="main", servings=4, prep=20, cook=60,
        texture=("fondant", "bouillon_riche"), taste=("savoureux", "aromatique"),
        technique=("simmering",), difficulty="easy",
        desc="Le pot-au-feu de l'hiver, avec du seitan à la place du bœuf : carottes, navets, "
             "poireaux, céleri-rave et pommes de terre cuits doucement dans un bouillon "
             "parfumé au clou de girofle et au laurier, servis avec moutarde et gros sel.",
        compo=[
            ("base_seitan_249032", 300, "g", "plant_protein"),
            ("carrot_raw", 400, "g", "vegetable"),
            ("turnip_raw", 400, "g", "main_vegetable"),
            ("leeks_raw", 300, "g", "vegetable"),
            ("celeriac_raw", 300, "g", "vegetable"),
            ("potato_raw_flesh", 400, "g", "carbohydrate"),
            ("onion_raw", 150, "g", "aromatic"),
            ("cloves_spice", 1, "g", "spice"),
            ("bay_leaf_spice", 1, "g", "herb"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("vegetable_stock_dried", 20, "g", "seasoning"),
            ("water", 2000, "ml", "liquid"),
            ("mustard", 30, "g", "condiment"),
        ],
        steps=[
            "Piquer l'oignon entier (150 g) de 3 clous de girofle et le mettre dans une grande "
            "marmite avec 2 l d'eau, 20 g de bouillon de légumes, le laurier et 3 g de thym ; "
            "porter à frémissement.",
            "Ajouter 400 g de carottes, 400 g de navets et 300 g de céleri-rave en gros "
            "morceaux, et cuire 20 minutes à petit frémissement.",
            "Ajouter 300 g de poireaux en tronçons ficelés et 400 g de pommes de terre en "
            "morceaux, et cuire encore 25 minutes.",
            "Ajouter 300 g de seitan en tranches épaisses et le réchauffer 10 minutes dans le "
            "bouillon.",
            "Servir les légumes et le seitan avec un peu de bouillon et 30 g de moutarde à part.",
        ],
        allow_similar=("pot", "feu"),
    ),
    recipe(
        rid="main_curry_potimarron_pois_chiches_epinards_5c27e1",
        fr="Curry de potimarron, pois chiches et épinards",
        en="Red Kuri Squash, Chickpea and Spinach Curry",
        cuisine="indian", country="india",
        dish="main", servings=4, prep=15, cook=30,
        texture=("fondant", "cremeux"), taste=("epice", "doux"),
        technique=("sauteing", "simmering", "boiling"), difficulty="easy", spice=1,
        desc="Le potimarron fond dans une sauce au lait de coco et à la tomate, avec des pois "
             "chiches et des épinards : un curry doux et réconfortant, servi avec du riz "
             "basmati.",
        compo=[
            ("basmati_rice_raw_seed", 280, "g", "carbohydrate"),
            ("red_kuri_squash_raw_skinless", 600, "g", "main_vegetable"),
            ("chickpea_rinsed_canned", 480, "g", "plant_protein"),
            ("spinach_raw_mature", 200, "g", "vegetable"),
            ("coconut_milk_plant", 400, "ml", "liquid"),
            ("tomato_crushed_canned", 200, "g", "sauce"),
            ("onion_raw", 150, "g", "aromatic"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("garam_masala", 8, "g", "spice"),
            ("turmeric_powder", 3, "g", "spice"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 560, "ml", "liquid"),
        ],
        steps=[
            "Cuire 280 g de riz basmati rincé dans 560 ml d'eau, à couvert et à feu doux, "
            "15 minutes.",
            "Faire revenir 150 g d'oignon, 10 g d'ail et 15 g de gingembre hachés 5 minutes "
            "dans 20 ml d'huile, ajouter 8 g de garam masala et 3 g de curcuma et remuer "
            "30 secondes.",
            "Ajouter 600 g de potimarron en cubes (la peau se mange), 200 g de tomates "
            "concassées, 400 ml de lait de coco et 5 g de sel, et cuire 15 minutes à couvert.",
            "Ajouter 480 g de pois chiches égouttés et 200 g d'épinards, et cuire encore "
            "5 minutes. Servir avec le riz.",
        ],
        allow_similar=("potimarron", "epinards"),
    ),
    recipe(
        rid="main_galettes_sarrasin_poireaux_emmental_e04b77",
        fr="Galettes de sarrasin aux poireaux fondus, œuf et emmental",
        en="Buckwheat Galettes with Melted Leeks, Egg and Emmental",
        cuisine="french", country="france", region="bretagne",
        dish="main", servings=4, prep=10, rest=30, cook=30,
        texture=("croustillant", "fondant"), taste=("noisette", "lacté"),
        technique=("sauteing", "pan_frying"), difficulty="medium",
        desc="La galette complète d'hiver : pâte de sarrasin à l'eau, garnie de poireaux "
             "fondus au beurre, d'un œuf et d'emmental, pliée en carré et dorée à la poêle.",
        compo=[
            ("buckwheat_flour", 250, "g", "base"),
            ("water", 600, "ml", "liquid"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("leeks_raw", 500, "g", "main_vegetable"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("egg_raw", 240, "g", "protein"),
            ("emmental_de_savoie_cow", 120, "g", "dairy"),
            ("black_pepper_spice", 1, "g", "spice"),
        ],
        steps=[
            "Fouetter 250 g de farine de sarrasin, 5 g de sel et 600 ml d'eau en une pâte lisse "
            "et la laisser reposer 30 minutes.",
            "Faire fondre 500 g de poireaux émincés 12 minutes à feu doux dans 20 g de beurre, "
            "avec 1 g de poivre.",
            "Cuire chaque galette dans une poêle très chaude légèrement beurrée (20 g de beurre "
            "pour l'ensemble), 2 minutes, puis la retourner.",
            "Garnir de poireaux, d'un œuf (60 g) cassé au centre et de 30 g d'emmental râpé, "
            "replier les bords en carré et cuire 3 minutes jusqu'à ce que le blanc soit pris.",
        ],
        allow_similar=("galettes", "sarrasin", "poireaux"),
    ),
    recipe(
        rid="main_gnocchis_choux_bruxelles_sauge_noisettes_2b8a6d",
        fr="Gnocchis poêlés aux choux de Bruxelles, sauge et noisettes",
        en="Pan-Fried Gnocchi with Brussels Sprouts, Sage and Hazelnuts",
        cuisine="italian", country="italy",
        dish="main", servings=4, prep=10, cook=15,
        texture=("croustillant", "moelleux"), taste=("noisette", "savoureux"),
        technique=("sauteing", "toasting"), difficulty="easy",
        desc="Des gnocchis dorés à la poêle sans être cuits à l'eau, avec des choux de Bruxelles "
             "émincés, du beurre végétal à la sauge, des noisettes grillées et du parmesan.",
        compo=[
            ("potato_gnocchi_to_cook", 800, "g", "carbohydrate"),
            ("brussels_sprouts_raw", 400, "g", "main_vegetable"),
            ("vegan_butter", 40, "g", "fat"),
            ("sage_fresh_herb", 8, "g", "herb"),
            ("hazelnut_raw_unsalted", 40, "g", "garnish"),
            ("parmesan_grated_dried_cow", 40, "g", "dairy"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ],
        steps=[
            "Griller 40 g de noisettes 3 minutes à sec, puis les concasser.",
            "Dorer 800 g de gnocchis 6 minutes dans 20 g de beurre végétal, en les retournant.",
            "Ajouter 400 g de choux de Bruxelles émincés finement, 6 g d'ail et 2 g de sel, et "
            "sauter 4 minutes.",
            "Faire grésiller 8 g de feuilles de sauge 1 minute dans 20 g de beurre végétal, "
            "verser sur les gnocchis et servir avec les noisettes et 40 g de parmesan.",
        ],
        # « Gnocchis poêlés aux tomates cerises », « Choux de Bruxelles rôtis au miso » : autres plats
        allow_similar=("gnocchis", "poeles", "sauge", "choux", "bruxelles", "noisettes"),
    ),
    recipe(
        rid="main_chou_fleur_roti_epices_tahini_6e93c0",
        fr="Chou-fleur rôti aux épices, pois chiches et sauce tahini",
        en="Spiced Roast Cauliflower with Chickpeas and Tahini Sauce",
        cuisine="levantine", country="lebanon",
        dish="main", servings=4, prep=15, cook=35,
        texture=("croustillant", "fondant"), taste=("epice", "acidule"),
        technique=("baking", "roasting"), difficulty="easy",
        desc="Des fleurettes de chou-fleur et des pois chiches rôtis au cumin et au paprika "
             "jusqu'à caraméliser, nappés de sauce tahini au citron et parsemés de persil.",
        compo=[
            ("cauliflower_raw_flower", 1000, "g", "main_vegetable"),
            ("chickpea_rinsed_canned", 240, "g", "plant_protein"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("cumin_spice_seed", 4, "g", "spice"),
            ("paprika_powder", 4, "g", "spice"),
            ("sesame_tahini_raw_butter_seed_plant", 60, "g", "sauce"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("garlic_raw", 5, "g", "aromatic"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Préchauffer le four à 220 °C. Couper 1 kg de chou-fleur en fleurettes et les "
            "mélanger avec 240 g de pois chiches égouttés, 30 ml d'huile d'olive, 4 g de cumin, "
            "4 g de paprika et 3 g de sel.",
            "Étaler sur une plaque et cuire 35 minutes au four à 220 °C, en remuant à mi-cuisson, "
            "jusqu'à ce que le chou-fleur soit bien doré.",
            "Délayer 60 g de tahini avec 30 ml de jus de citron, 5 g d'ail râpé, 1 g de sel et "
            "4 cuillères à soupe d'eau.",
            "Napper le chou-fleur de sauce et parsemer de 15 g de persil haché.",
        ],
        allow_similar=("chou", "fleur", "tahini"),
    ),

    # ── B. Soupes ─────────────────────────────────────────────────────────────────────────

    # ── C. Accompagnements et entrées ─────────────────────────────────────────────────────
    recipe(
        rid="side_topinambours_rotis_noisette_persil_8a2e10",
        fr="Topinambours rôtis, noisettes et persil",
        en="Roast Jerusalem Artichokes with Hazelnuts and Parsley",
        cuisine="french", country="france",
        dish="side", servings=4, prep=10, cook=35,
        texture=("croustillant", "fondant"), taste=("noisette", "terreux"),
        technique=("roasting", "baking"), difficulty="easy",
        desc="Le topinambour rôti prend un goût d'artichaut et de noisette : coupé en deux, "
             "doré au four, puis mélangé à des noisettes grillées, du persil et un trait de "
             "citron.",
        compo=[
            ("jerusalem_artichoke_raw", 800, "g", "main_vegetable"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("hazelnut_raw_unsalted", 40, "g", "garnish"),
            ("lemon_juice", 15, "ml", "acidity"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("garlic_raw", 5, "g", "aromatic"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ],
        steps=[
            "Préchauffer le four à 210 °C. Brosser 800 g de topinambours, les couper en deux et "
            "les mélanger avec 30 ml d'huile d'olive et 3 g de sel.",
            "Cuire 35 minutes au four à 210 °C, face coupée vers le bas, jusqu'à ce qu'ils "
            "soient dorés et tendres.",
            "Griller 40 g de noisettes 3 minutes à sec et les concasser.",
            "Mélanger les topinambours avec les noisettes, 15 g de persil, 5 g d'ail haché et "
            "15 ml de jus de citron.",
        ],
    ),
    recipe(
        rid="side_navets_carottes_glaces_erable_0f5b92",
        fr="Navets et carottes glacés au sirop d'érable et au thym",
        en="Maple and Thyme Glazed Turnips and Carrots",
        cuisine="french", country="france",
        dish="side", servings=4, prep=10, cook=25,
        texture=("fondant", "laque"), taste=("légèrement_sucré", "aromatique"),
        technique=("simmering", "caramelizing"), difficulty="easy",
        desc="Des navets et des carottes cuits à court mouillement jusqu'à ce que l'eau "
             "s'évapore, puis glacés au beurre végétal et au sirop d'érable avec du thym.",
        compo=[
            ("turnip_raw", 600, "g", "main_vegetable"),
            ("carrot_raw", 300, "g", "vegetable"),
            ("vegan_butter", 25, "g", "fat"),
            ("maple_syrup", 20, "ml", "sweetener"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("water", 250, "ml", "liquid"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ],
        steps=[
            "Couper 600 g de navets et 300 g de carottes en morceaux de même taille.",
            "Les mettre dans une sauteuse avec 250 ml d'eau, 25 g de beurre végétal, 20 ml de "
            "sirop d'érable, 3 g de thym et 3 g de sel.",
            "Cuire 20 minutes à couvert, puis découvrir et laisser l'eau s'évaporer 5 minutes en "
            "remuant, jusqu'à ce que les légumes soient brillants et laqués.",
        ],
        allow_similar=("navets", "carottes", "glaces"),
    ),

    # ── E. Plats ajoutés à la place de quasi-doublons du catalogue ─────────────────────────
    recipe(
        rid="main_bourguignon_champignons_panais_4f2a81",
        fr="Bourguignon de champignons, panais et carottes",
        en="Mushroom, Parsnip and Carrot Bourguignon",
        cuisine="french", country="france", region="bourgogne",
        dish="main", servings=4, prep=20, cook=50,
        texture=("fondant", "nappant"), taste=("umami", "profond"),
        technique=("sauteing", "simmering", "boiling"), difficulty="easy",
        desc="Le bourguignon sans viande : champignons saisis, panais et carottes mijotés dans "
             "le vin rouge avec thym et laurier, sauce liée à la farine et au concentré de "
             "tomate, servi avec des pommes de terre vapeur.",
        compo=[
            ("button_mushroom_raw", 600, "g", "umami"),
            ("parsnip_raw", 400, "g", "main_vegetable"),
            ("carrot_raw", 300, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("red_wine_liquid", 400, "ml", "liquid"),
            ("tomato_paste_unsalted_canned", 30, "g", "umami"),
            ("wheat_all_purpose_flour_unenriched_unbleached", 20, "g", "thickener"),
            ("vegetable_stock_dried", 8, "g", "seasoning"),
            ("water", 400, "ml", "liquid"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("bay_leaf_spice", 1, "g", "herb"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("potato_raw_flesh", 700, "g", "carbohydrate"),
        ],
        steps=[
            "Saisir 600 g de champignons coupés en quatre 6 minutes dans 15 ml d'huile d'olive à "
            "feu vif ; réserver.",
            "Faire revenir 150 g d'oignon et 10 g d'ail 4 minutes dans 15 ml d'huile, ajouter "
            "20 g de farine et 30 g de concentré de tomate et remuer 1 minute.",
            "Verser 400 ml de vin rouge et 400 ml d'eau avec 8 g de bouillon, ajouter 400 g de "
            "panais et 300 g de carottes en tronçons, le thym et le laurier, et mijoter "
            "35 minutes à couvert.",
            "Remettre les champignons pour les 10 dernières minutes. Pendant ce temps, cuire "
            "700 g de pommes de terre 20 minutes à la vapeur et servir ensemble.",
        ],
    ),
    recipe(
        rid="main_choux_bruxelles_tofu_fume_puree_panais_8c5d13",
        fr="Choux de Bruxelles et tofu fumé à l'érable, purée de panais",
        en="Maple Brussels Sprouts and Smoked Tofu with Parsnip Mash",
        cuisine="french", country="france",
        dish="main", servings=4, prep=15, cook=25,
        texture=("cremeux", "croustillant"), taste=("fumé", "légèrement_sucré"),
        technique=("boiling", "sauteing", "caramelizing"), difficulty="easy",
        desc="Une purée de panais et de pommes de terre au lait d'avoine, des choux de Bruxelles "
             "et des dés de tofu fumé poêlés puis laqués au sirop d'érable et à la moutarde.",
        compo=[
            ("parsnip_raw", 600, "g", "main_vegetable"),
            ("potato_raw_flesh", 300, "g", "carbohydrate"),
            ("oat_milk_refrigerated_plain_plant", 150, "ml", "liquid"),
            ("vegan_butter", 20, "g", "fat"),
            ("brussels_sprouts_raw", 500, "g", "vegetable"),
            ("tofu_smoked_pre_packaged", 300, "g", "plant_protein"),
            ("maple_syrup", 30, "ml", "sweetener"),
            ("mustard", 15, "g", "condiment"),
            ("olive_oil_plant", 25, "ml", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("nutmeg_spice", 1, "g", "spice"),
        ],
        steps=[
            "Cuire 600 g de panais et 300 g de pommes de terre en morceaux 20 minutes dans l'eau "
            "bouillante salée avec 3 g de sel, puis les écraser avec 150 ml de lait d'avoine "
            "chaud, 20 g de beurre végétal et 1 g de muscade.",
            "Couper 500 g de choux de Bruxelles en deux et les poêler 10 minutes dans 15 ml "
            "d'huile d'olive, face coupée vers le bas, avec 1 g de sel.",
            "Dorer 300 g de tofu fumé en dés 5 minutes dans 10 ml d'huile, ajouter les choux, "
            "30 ml de sirop d'érable et 15 g de moutarde, et laquer 2 minutes en remuant.",
            "Servir sur la purée de panais.",
        ],
        allow_similar=("choux", "bruxelles", "erable", "tofu"),
    ),
    recipe(
        rid="main_tajine_legumes_hiver_pois_chiches_2e9b70",
        fr="Tajine de légumes d'hiver aux pois chiches, panais et navets",
        en="Winter Vegetable Tagine with Chickpeas, Parsnips and Turnips",
        cuisine="moroccan", country="morocco",
        dish="main", servings=4, prep=15, cook=45,
        texture=("fondant", "sauce_dense"), taste=("epice", "légèrement_sucré"),
        technique=("sauteing", "simmering", "boiling"), difficulty="easy", spice=1,
        desc="Panais, navets, carottes et courge mijotés avec des pois chiches, parfumés de "
             "cannelle, de gingembre et de cumin et adoucis d'abricots secs, servis sur une "
             "semoule.",
        compo=[
            ("parsnip_raw", 300, "g", "main_vegetable"),
            ("turnip_raw", 300, "g", "vegetable"),
            ("carrot_raw", 300, "g", "vegetable"),
            ("butternut_squash_raw_skinless", 300, "g", "vegetable"),
            ("chickpea_rinsed_canned", 480, "g", "plant_protein"),
            ("apricot_pitted_dried", 80, "g", "fruit"),
            ("onion_raw", 150, "g", "aromatic"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("cumin_spice_seed", 4, "g", "spice"),
            ("cinnamon_powder", 2, "g", "spice"),
            ("ginger_powder", 3, "g", "spice"),
            ("turmeric_powder", 2, "g", "spice"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("water", 900, "ml", "liquid"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("couscous_to_cook_seed_dried", 240, "g", "carbohydrate"),
            ("coriander_raw_fresh_herb", 15, "g", "herb"),
        ],
        steps=[
            "Faire revenir 150 g d'oignon et 8 g d'ail 4 minutes dans 20 ml d'huile d'olive, "
            "ajouter 4 g de cumin, 2 g de cannelle, 3 g de gingembre et 2 g de curcuma, et "
            "remuer 30 secondes.",
            "Ajouter 300 g de panais, 300 g de navets, 300 g de carottes et 300 g de courge en "
            "gros morceaux, 80 g d'abricots secs, 5 g de sel et 600 ml d'eau, et mijoter "
            "30 minutes à couvert.",
            "Ajouter 480 g de pois chiches égouttés et cuire encore 10 minutes.",
            "Verser 300 ml d'eau bouillante sur 240 g de semoule avec 10 ml d'huile, couvrir "
            "5 minutes et égrener. Servir le tajine sur la semoule avec 15 g de coriandre.",
        ],
        allow_similar=("tajine", "legumes", "pois", "chiches"),
    ),
    recipe(
        rid="main_chili_butternut_haricots_noirs_6b0e42",
        fr="Chili de courge butternut aux haricots noirs",
        en="Butternut Squash and Black Bean Chili",
        cuisine="mexican", country="mexico",
        dish="main", servings=4, prep=15, cook=35,
        texture=("fondant", "sauce_dense"), taste=("epice", "doux"),
        technique=("sauteing", "simmering"), difficulty="easy", spice=2,
        desc="La courge butternut fond dans un chili de haricots noirs à la tomate, au cumin, "
             "au paprika et au piment, servi avec du yaourt de soja, de la coriandre et du "
             "citron vert.",
        compo=[
            ("butternut_squash_raw_skinless", 600, "g", "main_vegetable"),
            ("black_bean_boiled", 500, "g", "plant_protein"),
            ("tomato_crushed_canned", 400, "g", "sauce"),
            ("onion_raw", 150, "g", "aromatic"),
            ("red_bell_pepper_raw", 150, "g", "vegetable"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("cumin_spice_seed", 5, "g", "spice"),
            ("paprika_powder", 5, "g", "spice"),
            ("red_hot_chili_pepper_spice_dried", 2, "g", "spice"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("water", 300, "ml", "liquid"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("soybean_yogurt_plain_plant", 200, "g", "sauce"),
            ("coriander_raw_fresh_herb", 15, "g", "herb"),
            ("lime_juice_fresh", 20, "ml", "acidity"),
        ],
        steps=[
            "Faire revenir 150 g d'oignon, 150 g de poivron rouge et 10 g d'ail 5 minutes dans "
            "20 ml d'huile d'olive, puis ajouter 5 g de cumin, 5 g de paprika et 2 g de piment.",
            "Ajouter 600 g de butternut en cubes, 400 g de tomates concassées, 300 ml d'eau et "
            "5 g de sel, et mijoter 20 minutes à couvert.",
            "Ajouter 500 g de haricots noirs égouttés et cuire encore 10 minutes à découvert, "
            "jusqu'à ce que la sauce épaississe.",
            "Servir avec 200 g de yaourt de soja, 15 g de coriandre et 20 ml de jus de citron "
            "vert.",
        ],
        allow_similar=("chili", "butternut", "courge"),
    ),
    recipe(
        rid="soup_chou_fleur_celeri_rave_curry_3d7f50",
        fr="Soupe de chou-fleur et céleri-rave au curry et au lait de coco",
        en="Cauliflower and Celeriac Curry Soup with Coconut Milk",
        cuisine="international", country="",
        dish="soup", servings=4, prep=10, cook=30,
        texture=("velouté", "lisse"), taste=("epice", "doux"),
        technique=("sauteing", "simmering", "blending"), difficulty="easy", spice=1,
        desc="Chou-fleur et céleri-rave mijotés avec du curry en poudre, mixés avec du lait de "
             "coco en un velouté doux, servi avec des graines de courge grillées.",
        compo=[
            ("cauliflower_raw_flower", 500, "g", "main_vegetable"),
            ("celeriac_raw", 300, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic"),
            ("curry_powder", 6, "g", "spice"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("water", 800, "ml", "liquid"),
            ("vegetable_stock_dried", 8, "g", "seasoning"),
            ("coconut_milk_plant", 200, "ml", "liquid"),
            ("pumpkin_squash_raw_seed", 30, "g", "garnish"),
        ],
        steps=[
            "Faire revenir 100 g d'oignon 3 minutes dans 20 ml d'huile d'olive, ajouter 6 g de "
            "curry et remuer 30 secondes.",
            "Ajouter 500 g de chou-fleur en fleurettes, 300 g de céleri-rave en cubes, 800 ml "
            "d'eau et 8 g de bouillon, et cuire 25 minutes à couvert.",
            "Mixer finement avec 200 ml de lait de coco.",
            "Griller 30 g de graines de courge 3 minutes à sec et en parsemer la soupe.",
        ],
        allow_similar=("chou", "fleur", "celeri", "rave", "curry"),
    ),
    recipe(
        rid="side_chou_rouge_saute_balsamique_graines_7a91c4",
        fr="Chou rouge sauté au vinaigre balsamique et aux graines de courge",
        en="Sautéed Red Cabbage with Balsamic Vinegar and Pumpkin Seeds",
        cuisine="international", country="",
        dish="side", servings=4, prep=10, cook=12,
        texture=("croquant", "fondant"), taste=("acidule", "légèrement_sucré"),
        technique=("sauteing",), difficulty="easy",
        desc="Le chou rouge émincé fin et sauté juste assez pour rester croquant, déglacé au "
             "vinaigre balsamique avec une pointe de sirop d'érable, et parsemé de graines de "
             "courge grillées.",
        compo=[
            ("red_cabbage_raw", 600, "g", "main_vegetable"),
            ("red_onion_raw", 100, "g", "aromatic"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("balsamic_vinegar_liquid", 30, "ml", "acidity"),
            ("maple_syrup", 10, "ml", "sweetener"),
            ("pumpkin_squash_raw_seed", 30, "g", "garnish"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ],
        steps=[
            "Émincer finement 600 g de chou rouge et 100 g d'oignon rouge.",
            "Les sauter 8 minutes à feu vif dans 20 ml d'huile d'olive avec 3 g de sel, en "
            "remuant souvent.",
            "Déglacer avec 30 ml de vinaigre balsamique et 10 ml de sirop d'érable, et cuire "
            "encore 2 minutes.",
            "Griller 30 g de graines de courge 3 minutes à sec et en parsemer le chou.",
        ],
        allow_similar=("chou", "rouge"),
    ),

    # ── D. Desserts ───────────────────────────────────────────────────────────────────────
    recipe(
        rid="dess_poires_pochees_vin_rouge_epices_5a1c8e",
        fr="Poires pochées au vin rouge et aux épices",
        en="Pears Poached in Spiced Red Wine",
        cuisine="french", country="france",
        dish="dessert", servings=4, prep=10, cook=35,
        texture=("fondant", "sirupeux"), taste=("epice", "fruité"),
        technique=("simmering",), difficulty="easy", kid_friendly=False,
        desc="Des poires entières pochées dans un vin rouge parfumé à la cannelle, à l'anis "
             "étoilé et à l'orange, puis nappées du sirop réduit : le dessert vegan des fêtes.",
        compo=[
            ("pear_raw_with_skin", 720, "g", "fruit"),
            ("red_wine_liquid", 750, "ml", "liquid"),
            ("white_sugar", 100, "g", "sweetener"),
            ("cinnamon_powder", 2, "g", "spice"),
            ("star_anise", 2, "g", "spice"),
            ("orange_raw", 100, "g", "fruit"),
        ],
        steps=[
            "Porter à ébullition 750 ml de vin rouge avec 100 g de sucre, 2 g de cannelle, "
            "2 étoiles de badiane et 100 g d'orange en rondelles.",
            "Peler 4 poires (720 g) en gardant la queue, les plonger dans le vin et les pocher "
            "25 minutes à frémissement, en les retournant pour qu'elles se colorent également.",
            "Retirer les poires et faire réduire le vin 10 minutes à feu vif, jusqu'à ce qu'il "
            "devienne sirupeux.",
            "Servir les poires tièdes ou froides nappées de sirop.",
        ],
        allow_similar=("poires", "pochees"),
    ),
    recipe(
        rid="dess_salade_oranges_kiwis_menthe_9d3f27",
        fr="Oranges et kiwis à la menthe et au sirop d'érable",
        en="Oranges and Kiwis with Mint and Maple Syrup",
        cuisine="international", country="",
        dish="dessert", servings=4, prep=10, cook=0,
        texture=("frais", "juteux"), taste=("acidule", "frais"),
        technique=("assembly",), difficulty="easy",
        desc="Les fruits frais de l'hiver, riches en vitamine C : oranges pelées à vif et "
             "kiwis en rondelles, avec de la menthe ciselée et un filet de sirop d'érable.",
        compo=[
            ("orange_raw", 500, "g", "fruit"),
            ("kiwi_raw", 300, "g", "fruit"),
            ("maple_syrup", 15, "ml", "sweetener"),
            ("mint_fresh_herb", 5, "g", "herb"),
        ],
        steps=[
            "Peler à vif 500 g d'oranges et les couper en rondelles, en recueillant le jus.",
            "Peler 300 g de kiwis et les couper en rondelles.",
            "Disposer les fruits, arroser du jus et de 15 ml de sirop d'érable, et parsemer de "
            "5 g de menthe ciselée.",
        ],
        allow_similar=("oranges", "kiwis"),
    ),
]
