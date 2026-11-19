"""Lot 16 : plats d'hiver et plats riches en protéines (21 recettes).

Comble deux manques relevés par l'analyse d'équilibre du 2026-11-19 : une quarantaine de plats
seulement étaient de saison en décembre-février (chou, poireau, courge, racines, endive), et
75 plats atteignaient 20 g de protéines par portion, dont 39 vegan.
"""
from ._schema import recipe

RECIPES = [
    # ── B. Plats d'hiver ────────────────────────────────────────────────────────────────────
    recipe(
        rid="pasta_pizzoccheri_valtellina_6e2d81",
        fr="Pizzoccheri, pâtes de sarrasin au chou et aux pommes de terre",
        en="Pizzoccheri, Buckwheat Pasta with Cabbage and Potatoes",
        original="Pizzoccheri della Valtellina",
        cuisine="italian", country="italy", region="lombardie", city="teglio",
        dish="main", servings=4, prep=35, rest=15, cook=30,
        texture=("fondant", "filant"), taste=("lacté", "aillé"),
        technique=("kneading", "boiling", "baking"), difficulty="medium",
        desc="Plat d'hiver de la Valteline : des tagliatelles épaisses de sarrasin cuites avec le chou "
             "et les pommes de terre, puis montées en couches avec du fromage fondant et arrosées de "
             "beurre noisette à l'ail et à la sauge.",
        compo=[
            ("buckwheat_flour", 300, "g", "base"),
            ("wheat_flour_t55", 100, "g", "base"),
            ("water", 3250, "ml", "liquid"),
            ("savoy_cabbage_raw", 400, "g", "main_vegetable"),
            ("potato_raw_flesh", 400, "g", "vegetable"),
            ("gruyere_whole_cow", 160, "g", "dairy"),
            ("parmesan_grated_dried_cow", 50, "g", "dairy"),
            ("butter_sup80pct", 60, "g", "fat"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("sage_fresh_herb", 4, "g", "herb"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Pétrir 300 g de farine de sarrasin, 100 g de farine de blé, 2 g de sel et 250 ml d'eau "
            "tiède en pâte ferme, puis laisser reposer 15 minutes sous un linge.",
            "Abaisser la pâte sur 3 mm et la couper en rubans de 1 cm sur 7 cm.",
            "Porter 3 litres d'eau à ébullition avec 3 g de sel, y cuire 400 g de pommes de terre en "
            "cubes et 400 g de chou de Milan en lanières, 5 minutes.",
            "Ajouter les pizzoccheri et cuire encore 8 minutes.",
            "Pendant ce temps, fondre 60 g de beurre avec 8 g d'ail écrasé et 4 g de sauge jusqu'à "
            "ce qu'il blondisse.",
            "Égoutter, alterner dans un plat les pâtes et légumes avec 160 g de fromage en lamelles et "
            "50 g de parmesan, poivrer avec 1 g de poivre et arroser de beurre noisette.",
            "Passer 5 minutes au four à 200 °C pour faire fondre le fromage, et servir brûlant.",
        ],
    ),
    recipe(
        rid="pasta_croziflette_poireaux_1b47c9",
        fr="Croziflette végétarienne aux poireaux et reblochon",
        en="Vegetarian Croziflette with Leeks and Reblochon",
        original="Croziflette",
        cuisine="french", country="france", region="savoie",
        dish="main", servings=5, prep=15, cook=40,
        texture=("fondant", "gratiné"), taste=("lacté", "doux"),
        technique=("boiling", "sauteing", "gratinating"), difficulty="easy",
        desc="La cousine savoyarde de la tartiflette, faite de crozets : les petites pâtes carrées "
             "cuisent puis gratinent avec des poireaux fondus au vin blanc, de la crème et un "
             "reblochon coupé en deux, croûte vers le haut.",
        compo=[
            ("pasta_raw_dried", 400, "g", "carbohydrate"),
            ("leeks_raw", 500, "g", "main_vegetable"),
            ("onion_raw", 100, "g", "aromatic"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("white_wine_liquid", 100, "ml", "liquid"),
            ("cream_heavy_refrigerated_30pct", 200, "ml", "dairy"),
            ("reblochon_cow", 450, "g", "dairy"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "seasoning"),
            ("water", 3000, "ml", "liquid"),
        ],
        steps=[
            "Cuire 400 g de crozets (petites pâtes carrées de Savoie) 15 minutes dans 3 litres d'eau bouillante salée avec 3 g de sel, "
            "puis égoutter.",
            "Faire fondre 500 g de poireaux en rondelles et 100 g d'oignon émincé dans 30 g de beurre, "
            "10 minutes à feu doux, sans coloration.",
            "Mouiller avec 100 ml de vin blanc, réduire 3 minutes, puis ajouter 200 ml de crème, "
            "2 g de sel et 2 g de poivre.",
            "Mélanger les crozets à la fondue de poireaux et verser dans un plat à gratin.",
            "Couper 450 g de reblochon en deux dans l'épaisseur et le poser croûte vers le haut.",
            "Gratiner 15 minutes à 210 °C, jusqu'à ce que le fromage coule et dore.",
        ],
    ),
    recipe(
        rid="stew_waterzooi_legumes_9c3a52",
        fr="Waterzooi de légumes d'hiver à la crème",
        en="Winter Vegetable Waterzooi",
        original="Waterzooi",
        cuisine="belgian", country="belgium", region="flandre", city="gand",
        dish="main", servings=4, prep=20, cook=35,
        texture=("fondant", "crémeux"), taste=("doux", "herbacé"),
        technique=("simmering",), difficulty="easy",
        desc="Le ragoût-soupe de Gand en version végétarienne : poireaux, carottes, céleri-rave et "
             "pommes de terre en julienne cuits dans un bouillon aux herbes, lié en fin de cuisson à "
             "la crème et au jaune d'œuf.",
        compo=[
            ("leeks_raw", 300, "g", "main_vegetable"),
            ("carrot_raw", 250, "g", "vegetable"),
            ("celeriac_raw", 250, "g", "vegetable"),
            ("potato_raw_flesh", 400, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("vegetable_stock_dried", 15, "g", "seasoning"),
            ("water", 1000, "ml", "liquid"),
            ("thyme_fresh_herb", 2, "g", "herb"),
            ("bay_leaf_spice", 1, "g", "spice"),
            ("cream_heavy_refrigerated_30pct", 150, "ml", "dairy"),
            ("egg_yolk_raw", 40, "g", "binder"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Tailler en julienne 300 g de poireaux, 250 g de carottes et 250 g de céleri-rave, couper "
            "400 g de pommes de terre en cubes et émincer 100 g d'oignon.",
            "Faire suer poireaux, oignon, carottes et céleri dans 30 g de beurre, 8 minutes à feu "
            "doux.",
            "Ajouter les pommes de terre, 1 litre d'eau, 15 g de bouillon, 2 g de thym et 1 g de "
            "laurier, et cuire 25 minutes à petit frémissement.",
            "Fouetter 150 ml de crème avec 40 g de jaunes d'œufs, verser une louche de bouillon "
            "chaud dessus, puis reverser le tout dans la cocotte hors du feu en remuant.",
            "Rectifier avec 3 g de sel et 1 g de poivre, et servir en assiette creuse, parsemé de "
            "15 g de persil.",
        ],
    ),
    recipe(
        rid="stew_pot_au_feu_legumes_4f80d7",
        fr="Pot-au-feu de légumes au bouillon d'herbes",
        en="Vegetable Pot-au-Feu in Herb Broth",
        cuisine="french", country="france", region="",
        dish="main", servings=4, prep=20, cook=50,
        texture=("fondant", "bouillon_riche"), taste=("doux", "herbacé"),
        technique=("simmering",), difficulty="easy",
        desc="Le pot-au-feu sans viande : carottes, navets, poireaux ficelés, céleri-rave et pommes "
             "de terre pochés dans un bouillon parfumé à l'oignon piqué de clous de girofle, servis "
             "avec moutarde, gros sel et le bouillon en tasse.",
        compo=[
            ("carrot_raw", 400, "g", "main_vegetable"),
            ("turnip_raw", 300, "g", "vegetable"),
            ("leeks_raw", 300, "g", "vegetable"),
            ("celeriac_raw", 300, "g", "vegetable"),
            ("potato_raw_flesh", 500, "g", "vegetable"),
            ("onion_raw", 120, "g", "aromatic"),
            ("cloves_spice", 1, "g", "spice"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("bay_leaf_spice", 1, "g", "spice"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("vegetable_stock_dried", 15, "g", "seasoning"),
            ("water", 2000, "ml", "liquid"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "seasoning"),
            ("mustard", 40, "g", "condiment"),
        ],
        steps=[
            "Porter 2 litres d'eau à frémissement avec 15 g de bouillon, 120 g d'oignon piqué de 1 g "
            "de clous de girofle, 10 g d'ail, 3 g de thym, 1 g de laurier, 2 g de sel et 2 g de "
            "poivre en grains, et laisser infuser 15 minutes.",
            "Éplucher 400 g de carottes, 300 g de navets et 300 g de céleri-rave en gros morceaux, "
            "ficeler 300 g de poireaux en botte.",
            "Plonger carottes et céleri dans le bouillon, cuire 10 minutes, puis ajouter navets et "
            "poireaux.",
            "Ajouter 500 g de pommes de terre en morceaux 20 minutes avant la fin, et poursuivre "
            "jusqu'à ce que tout soit tendre, 25 minutes au total après les navets.",
            "Servir les légumes égouttés parsemés de 15 g de persil, avec 40 g de moutarde, et le "
            "bouillon en tasse à côté.",
        ],
    ),
    recipe(
        rid="tarte_tatin_legumes_racines_0d6b44",
        allow_similar=("racines",),
        fr="Tatin de légumes racines, panais, carotte et échalote",
        en="Root Vegetable Tatin with Parsnip, Carrot and Shallot",
        cuisine="french", country="france", region="",
        dish="main", servings=4, prep=20, cook=45,
        texture=("caramélisé", "feuilleté"), taste=("sucré", "salé"),
        technique=("caramelizing", "baking"), difficulty="medium",
        desc="Une tarte renversée salée : panais, carottes et échalotes rôties dans un caramel au miel "
             "et au vinaigre balsamique, recouvertes de pâte feuilletée et retournées à la sortie du "
             "four.",
        compo=[
            ("parsnip_raw", 350, "g", "main_vegetable"),
            ("carrot_raw", 300, "g", "vegetable"),
            ("shallot_raw", 150, "g", "aromatic"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("honey", 30, "g", "sweetener"),
            ("balsamic_vinegar_liquid", 20, "ml", "acidity"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("puff_pastry_all_butter_raw_paste_pre_packaged", 230, "g", "base"),
            ("olive_oil_extra_virgin_plant", 15, "ml", "fat"),
            ("goat_cheese_fresh", 150, "g", "dairy"),
            ("arugula_raw", 60, "g", "vegetable"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Couper 350 g de panais et 300 g de carottes en bâtonnets épais, peler 150 g d'échalotes "
            "et les couper en deux.",
            "Les rôtir 20 minutes à 200 °C avec 15 ml d'huile d'olive, 3 g de sel et 1 g de poivre.",
            "Dans un moule à manqué allant au feu, fondre 30 g de beurre avec 30 g de miel jusqu'à "
            "caramel blond, déglacer avec 20 ml de vinaigre balsamique et ajouter 3 g de thym.",
            "Ranger les légumes serrés dans le caramel, couvrir de 230 g de pâte feuilletée en "
            "rentrant les bords et piquer.",
            "Cuire 25 minutes au four à 200 °C, laisser reposer 5 minutes et retourner sur un plat ; émietter 150 g de chèvre frais sur les légumes et servir avec 60 g de roquette.",
        ],
    ),
    recipe(
        rid="side_gratin_celeri_rave_noix_7a19e6",
        fr="Gratin de céleri-rave aux noix",
        en="Celeriac and Walnut Gratin",
        cuisine="french", country="france", region="",
        dish="side", servings=4, prep=15, cook=45,
        texture=("fondant", "gratiné"), taste=("doux", "torréfié"),
        technique=("baking", "gratinating"), difficulty="easy",
        desc="Un gratin d'hiver au goût de noisette : céleri-rave et pommes de terre en fines "
             "lamelles cuits dans une crème à l'ail et à la muscade, sous une croûte de comté et de "
             "noix concassées.",
        compo=[
            ("celeriac_raw", 600, "g", "main_vegetable"),
            ("potato_raw_flesh", 300, "g", "vegetable"),
            ("cream_heavy_refrigerated_30pct", 200, "ml", "dairy"),
            ("milk_liquid_pasteurized_3_5pct", 150, "ml", "dairy"),
            ("garlic_raw", 5, "g", "aromatic"),
            ("nutmeg_spice", 1, "g", "spice"),
            ("comte_cow", 60, "g", "dairy"),
            ("walnut_shelled_dried", 50, "g", "nut"),
            ("butter_sup80pct", 10, "g", "fat"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Peler 600 g de céleri-rave et 300 g de pommes de terre, les couper en lamelles de 3 mm.",
            "Chauffer 200 ml de crème et 150 ml de lait avec 5 g d'ail écrasé, 1 g de muscade, 5 g de "
            "sel et 1 g de poivre.",
            "Beurrer un plat avec 10 g de beurre, y ranger les lamelles en couches et verser la crème "
            "chaude.",
            "Cuire 35 minutes au four à 180 °C, couvert d'une feuille de papier cuisson.",
            "Parsemer de 60 g de comté râpé et de 50 g de noix concassées, et gratiner 10 minutes à "
            "découvert.",
        ],
    ),
    recipe(
        rid="side_endives_braisees_orange_3c5b17",
        allow_similar=("braisees", "endives", "orange"),
        fr="Endives braisées à l'orange",
        en="Orange-Braised Endives",
        cuisine="belgian", country="belgium", region="",
        dish="side", servings=4, prep=10, cook=30,
        texture=("fondant", "caramélisé"), taste=("amer", "sucré"),
        technique=("caramelizing", "simmering"), difficulty="easy",
        desc="Les endives, dorées à la poêle puis braisées à couvert dans le jus d'orange, perdent "
             "leur amertume crue et prennent un glaçage sucré-acidulé ; vegan, à l'huile d'olive.",
        compo=[
            ("endive_raw", 600, "g", "main_vegetable"),
            ("olive_oil_extra_virgin_plant", 25, "ml", "fat"),
            ("brown_sugar", 10, "g", "sweetener"),
            ("orange_raw_juice_fresh", 150, "ml", "acidity"),
            ("orange_peel_raw", 3, "g", "aroma"),
            ("thyme_fresh_herb", 2, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Couper 600 g d'endives en deux dans la longueur et retirer le cône amer de la base.",
            "Les dorer face coupée dans 25 ml d'huile d'olive à feu moyen, 5 minutes, saupoudrées de "
            "10 g de cassonade.",
            "Retourner, verser 150 ml de jus d'orange, ajouter 3 g de zeste, 2 g de thym, 3 g de sel "
            "et 1 g de poivre.",
            "Couvrir et braiser 20 minutes à feu doux, puis découvrir et laisser réduire le jus en "
            "sirop 5 minutes.",
        ],
    ),
    recipe(
        rid="side_choux_bruxelles_miso_sesame_8b26f0",
        fr="Choux de Bruxelles rôtis au miso et au sésame",
        en="Miso and Sesame Roasted Brussels Sprouts",
        cuisine="international", country="international",
        dish="side", servings=4, prep=10, cook=25,
        texture=("croustillant", "fondant"), taste=("umami", "torréfié"),
        technique=("baking",), difficulty="easy",
        desc="Les choux de Bruxelles coupés en deux et rôtis à four chaud jusqu'à brunir sur les "
             "bords, puis laqués d'une sauce au miso, au sirop d'érable et à l'huile de sésame.",
        compo=[
            ("brussels_sprouts_raw", 600, "g", "main_vegetable"),
            ("sunflower_oil_plant", 20, "ml", "fat_cooking"),
            ("miso_fermented", 30, "g", "umami"),
            ("maple_syrup", 15, "ml", "sweetener"),
            ("sesame_oil_plant", 10, "ml", "fat"),
            ("cider_vinegar_liquid", 10, "ml", "acidity"),
            ("garlic_raw", 4, "g", "aromatic"),
            ("sesame_raw_seed", 10, "g", "garnish"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ],
        steps=[
            "Parer 600 g de choux de Bruxelles et les couper en deux.",
            "Les mélanger à 20 ml d'huile et 2 g de sel, et les rôtir face coupée contre la plaque "
            "20 minutes à 220 °C.",
            "Fouetter 30 g de miso, 15 ml de sirop d'érable, 10 ml d'huile de sésame, 10 ml de "
            "vinaigre de cidre et 4 g d'ail râpé.",
            "Enrober les choux de la sauce, remettre 5 minutes au four et servir parsemé de 10 g de "
            "sésame torréfié.",
        ],
    ),
    recipe(
        rid="side_panais_carottes_miel_thym_2e9d61",
        fr="Panais et carottes rôtis au miel et au thym",
        en="Honey and Thyme Roasted Parsnips and Carrots",
        cuisine="british", country="united_kingdom",
        dish="side", servings=4, prep=10, cook=35,
        texture=("caramélisé", "fondant"), taste=("sucré", "herbacé"),
        technique=("baking", "caramelizing"), difficulty="easy",
        desc="L'accompagnement du rôti dominical britannique : panais et carottes en quartiers rôtis "
             "jusqu'à dorer, puis glacés de miel et de thym frais en fin de cuisson.",
        compo=[
            ("parsnip_raw", 500, "g", "main_vegetable"),
            ("carrot_raw", 400, "g", "vegetable"),
            ("olive_oil_extra_virgin_plant", 30, "ml", "fat"),
            ("honey", 30, "g", "sweetener"),
            ("thyme_fresh_herb", 4, "g", "herb"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Peler 500 g de panais et 400 g de carottes et les couper en quartiers dans la longueur.",
            "Les mélanger à 30 ml d'huile d'olive, 8 g d'ail en chemise, 4 g de sel et 1 g de poivre, "
            "puis les rôtir 25 minutes à 210 °C.",
            "Arroser de 30 g de miel, parsemer de 4 g de thym, mélanger et rôtir encore 10 minutes, "
            "jusqu'à ce que les bords caramélisent.",
        ],
    ),
    recipe(
        rid="soup_veloute_panais_poire_5d0c8a",
        fr="Velouté de panais à la poire",
        en="Parsnip and Pear Velouté",
        cuisine="french", country="france", region="",
        dish="soup", servings=4, prep=15, cook=30,
        texture=("velouté", "lisse"), taste=("doux", "sucré"),
        technique=("simmering", "blending"), difficulty="easy",
        desc="Le panais, sucré et légèrement anisé, mixé avec une poire et un trait de lait de coco "
             "en un velouté d'hiver vegan, relevé de muscade et de noisettes torréfiées.",
        compo=[
            ("parsnip_raw", 600, "g", "main_vegetable"),
            ("pear_raw_with_skin", 200, "g", "fruit"),
            ("onion_raw", 100, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 20, "ml", "fat"),
            ("vegetable_stock_dried", 12, "g", "seasoning"),
            ("water", 900, "ml", "liquid"),
            ("coconut_milk_plant", 100, "ml", "fat"),
            ("nutmeg_spice", 1, "g", "spice"),
            ("hazelnut_raw_unsalted", 30, "g", "garnish"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Faire suer 100 g d'oignon émincé dans 20 ml d'huile d'olive 5 minutes.",
            "Ajouter 600 g de panais et 200 g de poire en morceaux, 900 ml d'eau et 12 g de bouillon, "
            "et cuire 25 minutes.",
            "Mixer très finement avec 100 ml de lait de coco, 1 g de muscade, 3 g de sel et 1 g de "
            "poivre.",
            "Torréfier 30 g de noisettes à sec, les concasser et en parsemer les bols.",
        ],
    ),
    recipe(
        rid="side_hutspot_carottes_oignons_a4e7f3",
        fr="Hutspot, purée néerlandaise aux carottes et oignons",
        en="Hutspot, Dutch Carrot and Onion Mash",
        original="Hutspot",
        cuisine="dutch", country="netherlands", region="hollande_meridionale", city="leyde",
        dish="side", servings=4, prep=15, cook=25,
        texture=("rustique", "fondant"), taste=("doux", "beurré"),
        technique=("boiling",), difficulty="easy",
        desc="La purée d'hiver de Leyde, écrasée grossièrement : pommes de terre, carottes et "
             "oignons cuits ensemble, puis montés au beurre et au lait chaud avec de la muscade.",
        compo=[
            ("potato_raw_flesh", 700, "g", "carbohydrate"),
            ("carrot_raw", 500, "g", "main_vegetable"),
            ("onion_raw", 250, "g", "aromatic"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("milk_liquid_pasteurized_3_5pct", 100, "ml", "dairy"),
            ("nutmeg_spice", 1, "g", "spice"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("water", 1500, "ml", "liquid"),
        ],
        steps=[
            "Couper 700 g de pommes de terre en gros cubes, 500 g de carottes en rondelles et 250 g "
            "d'oignons en quartiers.",
            "Les couvrir de 1,5 litre d'eau froide avec 2 g de sel et cuire 22 minutes après "
            "ébullition.",
            "Égoutter et écraser au presse-purée en gardant des morceaux.",
            "Incorporer 40 g de beurre et 100 ml de lait chaud, assaisonner de 1 g de muscade, 2 g de "
            "sel et 1 g de poivre.",
        ],
    ),
    recipe(
        rid="side_topinambours_marrons_6f31b2",
        allow_similar=("topinambours",),
        fr="Poêlée de topinambours aux marrons",
        en="Pan-Fried Jerusalem Artichokes with Chestnuts",
        cuisine="french", country="france", region="",
        dish="side", servings=4, prep=15, cook=25,
        texture=("fondant", "doré"), taste=("doux", "noisette"),
        technique=("boiling", "sauteing"), difficulty="easy",
        desc="Topinambours précuits puis dorés à la poêle avec des marrons, des échalotes et du thym, "
             "finis au persil et au citron : un accompagnement d'hiver au goût d'artichaut et de "
             "noisette.",
        compo=[
            ("jerusalem_artichoke_raw", 600, "g", "main_vegetable"),
            ("european_chestnuts_sweet_cooked", 200, "g", "vegetable"),
            ("shallot_raw", 60, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 30, "ml", "fat"),
            ("thyme_fresh_herb", 2, "g", "herb"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("lemon_juice", 10, "ml", "acidity"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("water", 1500, "ml", "liquid"),
        ],
        steps=[
            "Brosser 600 g de topinambours, les couper en morceaux et les cuire 8 minutes dans "
            "1,5 litre d'eau bouillante salée avec 2 g de sel et 10 ml de jus de citron ; égoutter.",
            "Les faire dorer dans 30 ml d'huile d'olive à feu moyen, 10 minutes en remuant.",
            "Ajouter 60 g d'échalotes émincées, 200 g de marrons (châtaignes) cuits et 2 g de thym, et poursuivre "
            "5 minutes.",
            "Assaisonner de 2 g de sel et 1 g de poivre, et parsemer de 10 g de persil ciselé.",
        ],
    ),

    # ── C. Plats riches en protéines ────────────────────────────────────────────────────────
    recipe(
        rid="protein_polpette_lenticchie_8d52c0",
        fr="Polpette di lenticchie, boulettes de lentilles au sugo",
        en="Polpette di Lenticchie, Lentil Meatballs in Tomato Sauce",
        original="Polpette di lenticchie al sugo",
        cuisine="italian", country="italy", region="ombrie",
        dish="main", servings=4, prep=25, cook=45,
        texture=("moelleux", "nappant"), taste=("umami", "tomaté"),
        technique=("boiling", "baking", "simmering"), difficulty="medium",
        desc="Boulettes vegan de lentilles vertes, chapelure, graines de lin et levure maltée, cuites "
             "au four puis mijotées dans un sugo de tomate au basilic : un plat complet riche en "
             "protéines.",
        compo=[
            ("green_lentil_dried", 300, "g", "plant_protein"),
            ("breadcrumbs_dried", 70, "g", "binder"),
            ("flaxseed_linseed_ground", 20, "g", "binder"),
            ("nutritional_yeast_flakes", 30, "g", "umami"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("parsley_fresh_herb", 20, "g", "herb"),
            ("oregano_spice_dried", 2, "g", "herb"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("onion_raw", 100, "g", "aromatic"),
            ("tomato_crushed_canned", 800, "g", "sauce"),
            ("basil_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("water", 1100, "ml", "liquid"),
        ],
        steps=[
            "Cuire 300 g de lentilles vertes dans 1 litre d'eau 20 minutes, égoutter et laisser "
            "tiédir.",
            "Mélanger 20 g de graines de lin moulues à 60 ml d'eau et laisser gonfler 5 minutes.",
            "Écraser grossièrement les lentilles avec le lin, 70 g de chapelure, 30 g de levure "
            "maltée, 5 g d'ail râpé, 20 g de persil haché, 2 g d'origan, 4 g de sel et 1 g de poivre.",
            "Former vingt boulettes, les huiler avec 15 ml d'huile et les cuire 20 minutes au four à 200 °C.",
            "Faire revenir 100 g d'oignon et 5 g d'ail dans 25 ml d'huile, ajouter 800 g de tomates "
            "concassées, 40 ml d'eau et 2 g de sel, et mijoter 15 minutes.",
            "Plonger les boulettes dans la sauce 5 minutes et servir parsemé de 10 g de basilic.",
        ],
    ),
    recipe(
        rid="protein_tofu_tikka_masala_3e8f45",
        allow_similar=("tikka",),
        fr="Tofu tikka masala",
        en="Tofu Tikka Masala",
        original="Tofu tikka masala",
        cuisine="indian", country="india", region="pendjab",
        dish="main", servings=4, prep=20, rest=30, cook=30,
        texture=("nappant", "grillé"), taste=("épicé", "crémeux"),
        technique=("marinating", "grilling", "simmering"), difficulty="medium", spice=2,
        desc="Cubes de tofu marinés au yaourt de soja et aux épices, grillés au four jusqu'à marquer, "
             "puis plongés dans une sauce tomate onctueuse au lait de coco, aux noix de cajou et au "
             "garam masala.",
        compo=[
            ("tofu_plain_pre_packaged", 600, "g", "plant_protein"),
            ("soybean_yogurt_plain_plant", 150, "g", "dairy"),
            ("garam_masala", 8, "g", "spice"),
            ("paprika_powder", 5, "g", "spice"),
            ("turmeric_powder", 2, "g", "spice"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("onion_raw", 150, "g", "aromatic"),
            ("tomato_crushed_canned", 400, "g", "sauce"),
            ("cashew_nuts_raw", 40, "g", "nut"),
            ("coconut_milk_plant", 200, "ml", "fat"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("lemon_juice", 15, "ml", "acidity"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
        ],
        steps=[
            "Presser 600 g de tofu 10 minutes, le couper en gros cubes et le mélanger à 150 g de "
            "yaourt de soja, 4 g de garam masala, 3 g de paprika, 15 ml de jus de citron et 3 g de "
            "sel ; laisser mariner 30 minutes.",
            "Étaler les cubes sur une plaque huilée avec 10 ml d'huile et les griller 15 minutes à "
            "230 °C, jusqu'à ce qu'ils marquent.",
            "Faire revenir 150 g d'oignon émincé dans 20 ml d'huile 8 minutes, ajouter 10 g d'ail, "
            "15 g de gingembre, 3 g de cumin, 2 g de curcuma et 2 g de paprika.",
            "Verser 400 g de tomates concassées et 40 g de noix de cajou, mijoter 10 minutes, puis "
            "mixer avec 200 ml de lait de coco, 4 g de garam masala et 3 g de sel.",
            "Ajouter le tofu grillé, mijoter 5 minutes et servir parsemé de 10 g de coriandre.",
        ],
    ),
    recipe(
        rid="salad_lentilles_beluga_tofu_fume_9a1c63",
        allow_similar=("beluga",),
        fr="Salade de lentilles beluga, tofu fumé et noisettes",
        en="Beluga Lentil Salad with Smoked Tofu and Hazelnuts",
        cuisine="french", country="france", region="",
        dish="main", servings=4, prep=15, cook=25,
        texture=("croquant", "ferme"), taste=("fumé", "acidulé"),
        technique=("boiling", "sauteing"), difficulty="easy",
        desc="Lentilles noires cuites fermes, tofu fumé doré à la poêle, noisettes torréfiées et "
             "roquette, liés d'une vinaigrette à la moutarde et à l'huile de noisette : une salade "
             "complète d'hiver.",
        compo=[
            ("green_lentil_dried", 250, "g", "plant_protein"),
            ("tofu_smoked_pre_packaged", 300, "g", "plant_protein"),
            ("hazelnut_raw_unsalted", 50, "g", "nut"),
            ("arugula_raw", 80, "g", "vegetable"),
            ("shallot_raw", 40, "g", "aromatic"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("mustard", 15, "g", "condiment"),
            ("cider_vinegar_liquid", 20, "ml", "acidity"),
            ("hazelnut_oil_plant", 20, "ml", "fat"),
            ("olive_oil_extra_virgin_plant", 30, "ml", "fat"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("water", 1000, "ml", "liquid"),
        ],
        steps=[
            "Cuire 250 g de lentilles beluga rincées dans 1 litre d'eau 22 minutes, en les gardant "
            "fermes, puis égoutter.",
            "Fouetter 15 g de moutarde, 20 ml de vinaigre de cidre, 20 ml d'huile de noisette, 15 ml "
            "d'huile d'olive, 3 g de sel et 1 g de poivre, et y mélanger les lentilles tièdes avec "
            "40 g d'échalote ciselée.",
            "Couper 300 g de tofu fumé en dés et le faire dorer dans 15 ml d'huile d'olive, 6 minutes.",
            "Torréfier 50 g de noisettes, les concasser ; râper 150 g de carotte.",
            "Mélanger lentilles, tofu, carotte, 80 g de roquette et 15 g de persil, saler de 1 g et "
            "parsemer de noisettes.",
        ],
    ),
    recipe(
        rid="protein_tempeh_patate_douce_cacahuete_4b7e90",
        fr="Tempeh rôti, patate douce et sauce cacahuète",
        en="Roasted Tempeh with Sweet Potato and Peanut Sauce",
        cuisine="indonesian", country="indonesia", region="java",
        dish="main", servings=4, prep=15, cook=30,
        texture=("croustillant", "fondant"), taste=("torréfié", "sucré"),
        technique=("baking", "sauce_making"), difficulty="easy", spice=1,
        desc="Tranches de tempeh marinées au soja et rôties avec des cubes de patate douce et du "
             "brocoli, nappées d'une sauce cacahuète au citron vert et au gingembre inspirée du "
             "bumbu kacang javanais.",
        compo=[
            ("tempeh_tempe_raw_fermented", 400, "g", "plant_protein"),
            ("sweet_potato_raw", 600, "g", "carbohydrate"),
            ("broccoli_raw", 300, "g", "vegetable"),
            ("soy_sauce_shoyu_reduced_sodium", 40, "ml", "seasoning"),
            ("maple_syrup", 15, "ml", "sweetener"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("peanut_butter_natural_plant", 80, "g", "fat"),
            ("lime_juice_fresh", 30, "ml", "acidity"),
            ("ginger_raw_root_fresh", 10, "g", "aromatic"),
            ("garlic_raw", 5, "g", "aromatic"),
            ("red_hot_chili_pepper_spice_dried", 1, "g", "spice"),
            ("water", 80, "ml", "liquid"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ],
        steps=[
            "Couper 400 g de tempeh en tranches et le mariner 10 minutes dans 25 ml de sauce soja et "
            "15 ml de sirop d'érable.",
            "Couper 600 g de patate douce en cubes, les mélanger à 20 ml d'huile et 3 g de sel, et "
            "les rôtir 15 minutes à 210 °C.",
            "Ajouter le tempeh égoutté et 300 g de brocoli en fleurettes arrosés de 10 ml d'huile, et "
            "rôtir encore 15 minutes.",
            "Fouetter 80 g de beurre de cacahuète, 30 ml de jus de citron vert, 15 ml de sauce soja, "
            "10 g de gingembre et 5 g d'ail râpés, 1 g de piment et 80 ml d'eau chaude.",
            "Servir la plaque nappée de sauce et parsemée de 10 g de coriandre.",
        ],
    ),
    recipe(
        rid="protein_roti_seitan_herbes_2f6d18",
        fr="Rôti de seitan aux herbes et légumes d'hiver",
        en="Herb Seitan Roast with Winter Vegetables",
        cuisine="international", country="international",
        dish="main", servings=6, prep=25, cook=75,
        texture=("ferme", "fondant"), taste=("umami", "herbacé"),
        technique=("kneading", "steaming", "baking"), difficulty="medium",
        desc="Un rôti de fête vegan : pâte de gluten et de farine de pois chiche assaisonnée d'ail, de "
             "sauge et de romarin, cuite à la vapeur puis rôtie avec carottes, panais et oignons "
             "rouges, et arrosée d'un jus au soja.",
        compo=[
            ("vital_wheat_gluten_flour", 250, "g", "plant_protein"),
            ("chickpea_flour", 50, "g", "plant_protein"),
            ("nutritional_yeast_flakes", 20, "g", "umami"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("sage_fresh_herb", 3, "g", "herb"),
            ("rosemary_fresh_herb", 3, "g", "herb"),
            ("paprika_powder", 3, "g", "spice"),
            ("soy_sauce_shoyu_reduced_sodium", 50, "ml", "seasoning"),
            ("vegetable_stock_dried", 15, "g", "seasoning"),
            ("water", 600, "ml", "liquid"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("carrot_raw", 400, "g", "vegetable"),
            ("parsnip_raw", 400, "g", "vegetable"),
            ("red_onion_raw", 200, "g", "aromatic"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Mélanger 250 g de gluten, 50 g de farine de pois chiche, 20 g de levure maltée, 3 g de "
            "paprika, 2 g de sauge et 2 g de romarin hachés, et 8 g d'ail râpé.",
            "Ajouter 220 ml d'eau, 30 ml de sauce soja et 10 ml d'huile, pétrir 3 minutes et façonner "
            "un boudin serré.",
            "L'envelopper dans du papier cuisson puis de l'aluminium, et le cuire 40 minutes à la "
            "vapeur.",
            "Couper 400 g de carottes, 400 g de panais et 200 g d'oignons rouges en gros morceaux, les "
            "mélanger à 20 ml d'huile, 4 g de sel et 1 g de poivre.",
            "Déballer le rôti, le poser sur les légumes, le badigeonner de 10 ml d'huile et rôtir "
            "35 minutes à 200 °C en l'arrosant à mi-cuisson.",
            "Pendant ce temps, porter à ébullition 380 ml d'eau, 15 g de bouillon, 20 ml de sauce "
            "soja, 4 g d'ail, 1 g de sauge et 1 g de romarin, et réduire de moitié : servir ce jus "
            "avec le rôti tranché.",
        ],
    ),
    recipe(
        rid="protein_halloumi_pois_chiches_rotis_7c40e2",
        fr="Halloumi, pois chiches rôtis et légumes grillés",
        en="Halloumi with Roasted Chickpeas and Grilled Vegetables",
        cuisine="cypriot", country="cyprus", region="",
        dish="main", servings=4, prep=15, cook=30,
        texture=("croustillant", "ferme"), taste=("salé", "citronné"),
        technique=("baking", "grilling"), difficulty="easy",
        desc="Plaque complète à la chypriote : pois chiches rôtis au cumin avec courgettes, poivrons "
             "et oignon rouge, couronnés de tranches de halloumi grillées à la poêle, de menthe et "
             "de citron.",
        compo=[
            ("base_halloumi_293d5e", 250, "g", "dairy"),
            ("chickpea_boiled", 500, "g", "plant_protein"),
            ("green_zucchini_squash_raw", 300, "g", "vegetable"),
            ("red_bell_pepper_raw", 200, "g", "vegetable"),
            ("red_onion_raw", 150, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("oregano_spice_dried", 2, "g", "herb"),
            ("lemon_juice", 25, "ml", "acidity"),
            ("mint_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Égoutter et sécher 500 g de pois chiches, couper 300 g de courgettes, 200 g de poivron "
            "rouge et 150 g d'oignon rouge en morceaux.",
            "Mélanger le tout à 30 ml d'huile d'olive, 3 g de cumin, 2 g d'origan, 3 g de sel et 1 g "
            "de poivre, et rôtir 25 minutes à 220 °C.",
            "Couper 250 g de halloumi en tranches de 1 cm et les griller 2 minutes par face dans une "
            "poêle avec 10 ml d'huile.",
            "Poser le halloumi sur les légumes, arroser de 25 ml de jus de citron et parsemer de 10 g "
            "de menthe ciselée.",
        ],
    ),
    recipe(
        rid="protein_tofu_chimichurri_haricots_5e93a7",
        allow_similar=("chimichurri",),
        fr="Tofu grillé au chimichurri et haricots blancs",
        en="Grilled Tofu with Chimichurri and White Beans",
        cuisine="argentinian", country="argentina", region="",
        dish="main", servings=4, prep=15, cook=15,
        texture=("grillé", "fondant"), taste=("herbacé", "acidulé"),
        technique=("grilling", "sauteing"), difficulty="easy", spice=1,
        desc="Le chimichurri argentin, persil, origan, ail et vinaigre de vin, sur des tranches de "
             "tofu grillées et des haricots blancs tièdes à l'huile d'olive et au citron.",
        compo=[
            ("tofu_plain_pre_packaged", 500, "g", "plant_protein"),
            ("white_bean_boiled", 500, "g", "plant_protein"),
            ("parsley_fresh_herb", 40, "g", "herb"),
            ("oregano_spice_dried", 3, "g", "herb"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("red_wine_vinegar_liquid", 30, "ml", "acidity"),
            ("olive_oil_extra_virgin_plant", 90, "ml", "fat"),
            ("red_hot_chili_pepper_spice_dried", 1, "g", "spice"),
            ("lemon_juice", 15, "ml", "acidity"),
            ("cherry_tomato_raw", 200, "g", "vegetable"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Hacher finement 40 g de persil et 8 g d'ail, les mélanger à 3 g d'origan, 1 g de "
            "piment, 30 ml de vinaigre de vin, 60 ml d'huile d'olive et 2 g de sel : c'est le "
            "chimichurri, à laisser reposer 10 minutes.",
            "Couper 500 g de tofu pressé en tranches de 1,5 cm, les huiler avec 10 ml d'huile, saler "
            "de 1 g et les griller 4 minutes par face à la poêle-gril.",
            "Réchauffer 500 g de haricots blancs égouttés 3 minutes avec 20 ml d'huile, 2 g d'ail, "
            "15 ml de jus de citron, 2 g de sel et 1 g de poivre.",
            "Servir le tofu sur les haricots avec 200 g de tomates cerises coupées, nappé de "
            "chimichurri.",
        ],
    ),
    recipe(
        rid="soup_haricots_kale_tofu_fume_1d84c6",
        fr="Soupe de haricots blancs, chou kale et tofu fumé",
        en="White Bean, Kale and Smoked Tofu Soup",
        cuisine="international", country="international",
        dish="soup", servings=4, prep=15, cook=30,
        texture=("épais", "fondant"), taste=("fumé", "herbacé"),
        technique=("simmering",), difficulty="easy",
        desc="Une soupe-repas d'hiver épaisse : haricots blancs en partie écrasés pour lier le "
             "bouillon, chou kale, carotte et céleri, avec des dés de tofu fumé qui remplacent le "
             "lard.",
        compo=[
            ("white_bean_boiled", 500, "g", "plant_protein"),
            ("tofu_smoked_pre_packaged", 250, "g", "plant_protein"),
            ("kale_raw", 200, "g", "main_vegetable"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("celery_stalk_raw", 100, "g", "vegetable"),
            ("onion_raw", 120, "g", "aromatic"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("tomato_crushed_canned", 200, "g", "sauce"),
            ("rosemary_fresh_herb", 2, "g", "herb"),
            ("vegetable_stock_dried", 10, "g", "seasoning"),
            ("water", 1200, "ml", "liquid"),
            ("olive_oil_extra_virgin_plant", 30, "ml", "fat"),
            ("red_hot_chili_pepper_spice_dried", 1, "g", "spice"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ],
        steps=[
            "Faire dorer 250 g de tofu fumé en dés dans 15 ml d'huile d'olive 5 minutes, puis le "
            "réserver.",
            "Dans la même cocotte, faire suer 120 g d'oignon, 150 g de carotte et 100 g de céleri en "
            "dés avec 15 ml d'huile, 8 g d'ail, 2 g de romarin et 1 g de piment, 6 minutes.",
            "Ajouter 200 g de tomates concassées, 1,2 litre d'eau, 10 g de bouillon et 500 g de "
            "haricots blancs, et cuire 15 minutes.",
            "Écraser une louche de haricots contre la paroi pour épaissir, ajouter 200 g de kale "
            "effeuillé en lanières et cuire 5 minutes.",
            "Remettre le tofu, assaisonner de 1 g de sel et 1 g de poivre, et servir.",
        ],
    ),
    recipe(
        rid="curry_pois_chiches_tofu_coco_6a2f95",
        fr="Curry de pois chiches et tofu au lait de coco",
        en="Chickpea and Tofu Coconut Curry",
        original="Kadala curry",
        cuisine="sri_lankan", country="sri_lanka", region="",
        dish="main", servings=4, prep=15, cook=30,
        texture=("nappant", "fondant"), taste=("épicé", "crémeux"),
        technique=("sauteing", "simmering"), difficulty="easy", spice=2,
        desc="Curry sri-lankais au lait de coco : graines de moutarde et feuilles de curry grésillées, "
             "oignon, tomate et poudre de curry torréfiée, pois chiches et tofu mijotés jusqu'à ce "
             "que la sauce nappe la cuillère.",
        compo=[
            ("chickpea_boiled", 400, "g", "plant_protein"),
            ("tofu_plain_pre_packaged", 400, "g", "plant_protein"),
            ("coconut_milk_plant", 400, "ml", "fat"),
            ("onion_raw", 150, "g", "aromatic"),
            ("tomato_raw_ripe", 200, "g", "vegetable"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("ginger_raw_root_fresh", 10, "g", "aromatic"),
            ("curry_leaf", 2, "g", "herb"),
            ("yellow_mustard_spice_seed", 3, "g", "spice"),
            ("curry_powder", 10, "g", "spice"),
            ("turmeric_powder", 2, "g", "spice"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("lime_juice_fresh", 15, "ml", "acidity"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("water", 100, "ml", "liquid"),
        ],
        steps=[
            "Couper 400 g de tofu en cubes et les faire dorer dans 15 ml d'huile 6 minutes ; réserver.",
            "Chauffer 15 ml d'huile, faire grésiller 3 g de graines de moutarde et 2 g de feuilles de "
            "curry, puis ajouter 150 g d'oignon émincé et cuire 6 minutes.",
            "Ajouter 10 g d'ail, 10 g de gingembre, 10 g de curry et 2 g de curcuma, puis 200 g de "
            "tomate en dés, et cuire 4 minutes.",
            "Verser 400 ml de lait de coco, 100 ml d'eau, 400 g de pois chiches et 5 g de sel, et "
            "mijoter 12 minutes.",
            "Remettre le tofu, chauffer 3 minutes, arroser de 15 ml de jus de citron vert et parsemer "
            "de 10 g de coriandre.",
        ],
    ),
]
