"""Lot 11 : Europe germanique, Benelux, pays nordiques et îles britanniques (22 recettes).

La France (108 plats) et l'Italie (63) sont déjà surreprésentées : ce lot ne comble que les
trous réels — Allemagne, Autriche, Suisse, Pays-Bas, Belgique, Suède, Danemark, Norvège,
Finlande, Irlande, Pays de Galles.
"""
from ._schema import recipe

RECIPES = [
    recipe(
        rid="side_rotkohl_9c4e21",
        fr="Rotkohl, chou rouge braisé aux pommes et au genièvre",
        en="Rotkohl, Braised Red Cabbage with Apple and Juniper",
        original="Rotkohl",
        cuisine="german", country="germany", region="rhenanie",
        dish="side", prep=20, cook=60,
        texture=("fondant",), taste=("acide", "sucré"),
        technique=("braise",),
        desc="Chou rouge émincé braisé une heure avec des pommes râpées, du vinaigre et des baies "
             "de genièvre : il devient fondant et violet profond, à la fois acide et sucré, "
             "l'accompagnement classique des plats d'hiver allemands.",
        compo=[
            ("red_cabbage_raw", 800, "g", "vegetable"),
            ("apple_raw", 200, "g", "fruit"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("red_wine_vinegar_liquid", 40, "ml", "acidity"),
            ("brown_sugar", 20, "g", "balance"),
            ("juniper_berry", 2, "g", "spice"),
            ("cinnamon", 1, "g", "spice"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("water", 150, "ml", "liquid"),
        ],
        steps=[
            "Émincer finement 800 g de chou rouge et le mélanger avec 40 ml de vinaigre de vin "
            "rouge et 3 g de sel, laisser dégorger 15 minutes.",
            "Faire fondre 30 g de beurre dans une cocotte et y blondir 100 g d'oignon émincé, "
            "5 minutes.",
            "Ajouter le chou, 200 g de pommes râpées, 20 g de sucre roux, 2 g de baies de genièvre "
            "écrasées et 1 g de cannelle.",
            "Verser 150 ml d'eau, couvrir et braiser 55 minutes à feu doux, en remuant toutes les "
            "quinze minutes.",
            "Découvrir en fin de cuisson pour faire évaporer le liquide restant : le chou doit "
            "être brillant et fondant.",
            "Goûter et rectifier l'équilibre vinaigre-sucre avant de servir.",
        ],
    ),
    recipe(
        rid="dessert_kaiserschmarrn_5a71d8",
        fr="Kaiserschmarrn, crêpe autrichienne déchirée au sucre glace",
        en="Kaiserschmarrn, Shredded Austrian Pancake",
        original="Kaiserschmarrn",
        cuisine="austrian", country="austria", region="tyrol",
        dish="dessert", prep=15, cook=20,
        texture=("moelleux", "aérien"), taste=("sucré", "lacté"),
        technique=("fry",), difficulty="medium",
        desc="Épaisse crêpe autrichienne aux blancs montés, cuite à la poêle puis déchirée à la "
             "spatule en gros lambeaux caramélisés au sucre, servie avec une compote de pommes.",
        compo=[
            ("wheat_flour_t55", 150, "g", "base"),
            ("milk_liquid_pasteurized_3_5pct", 250, "ml", "dairy"),
            ("egg_raw", 150, "g", "binder"),
            ("sugars_granulated", 50, "g", "sweetener"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("vanilla_extract", 5, "ml", "aroma"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
            ("apple_puree_pre_packaged", None, "en accompagnement", "serving_suggestion"),
        ],
        steps=[
            "Séparer 150 g d'œufs : mélanger les jaunes avec 150 g de farine, 250 ml de lait, 5 ml "
            "d'extrait de vanille et 1 g de sel jusqu'à obtenir une pâte lisse.",
            "Monter les blancs en neige souple avec 20 g de sucre.",
            "Incorporer les blancs à la pâte en deux fois, à la maryse, sans les casser.",
            "Faire fondre 25 g de beurre dans une grande poêle, verser la pâte sur 2 cm et cuire "
            "6 minutes à feu moyen-doux, jusqu'à ce que le dessous soit doré.",
            "Retourner en quatre quartiers, ajouter le reste du beurre et cuire 4 minutes.",
            "Déchirer la crêpe en morceaux irréguliers à la spatule, saupoudrer du reste de sucre "
            "et laisser caraméliser 3 minutes en remuant.",
            "Servir aussitôt avec une compote de pommes.",
        ],
    ),
    recipe(
        rid="pasta_krautfleckerl_d2b906",
        fr="Krautfleckerl, pâtes autrichiennes au chou caramélisé",
        en="Krautfleckerl, Austrian Pasta with Caramelized Cabbage",
        original="Krautfleckerl",
        cuisine="austrian", country="austria", region="vienne",
        dish="main", prep=20, cook=45,
        texture=("fondant", "tendre"), taste=("sucré", "poivré"),
        technique=("caramelize",),
        desc="Plat viennois de ménage : du chou blanc longuement caramélisé au sucre et au beurre, "
             "généreusement poivré, mélangé à des carrés de pâtes ; simple, doux et réconfortant.",
        compo=[
            ("white_cabbage_raw", 800, "g", "vegetable"),
            ("pasta_raw_dried", 250, "g", "base", "dried"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("butter_sup80pct", 50, "g", "fat"),
            ("sugars_granulated", 20, "g", "balance"),
            ("caraway_spice_seed", 3, "g", "spice"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 4, "g", "spice"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("water", 2000, "ml", "liquid"),
        ],
        steps=[
            "Émincer 800 g de chou blanc en lanières fines et le saler avec 3 g de sel.",
            "Faire fondre 50 g de beurre dans une sauteuse, ajouter 20 g de sucre et le laisser "
            "blondir 2 minutes.",
            "Ajouter 150 g d'oignon émincé puis le chou, et cuire 35 minutes à feu moyen en "
            "remuant : le chou doit dorer et réduire de moitié.",
            "Assaisonner de 3 g de carvi et 4 g de poivre, généreusement.",
            "Cuire 250 g de pâtes courtes dans 2 L d'eau salée (2 g de sel), les égoutter en "
            "gardant une louche d'eau de cuisson.",
            "Mélanger les pâtes au chou avec un peu d'eau de cuisson, réchauffer 3 minutes et "
            "parsemer de 10 g de persil.",
        ],
    ),
    recipe(
        rid="dal_linsen_spatzle_71ea34",
        fr="Linsen und Spätzle, lentilles souabes aux pâtes fraîches",
        en="Linsen und Spätzle, Swabian Lentils with Egg Noodles",
        original="Linsen mit Spätzle",
        cuisine="german", country="germany", region="souabe",
        dish="main", prep=25, cook=45,
        texture=("fondant",), taste=("acide", "umami"),
        technique=("simmer",),
        desc="Plat souabe du dimanche : des lentilles mijotées avec carotte et céleri-rave, "
             "relevées d'un trait de vinaigre, servies sur des spätzle aux œufs — les saucisses "
             "sont remplacées par une bonne dose d'oignons frits.",
        compo=[
            ("green_lentil_dried", 250, "g", "plant_protein", "dried"),
            ("egg_pasta_raw_dried", 250, "g", "base", "dried"),
            ("onion_raw", 200, "g", "aromatic_base"),
            ("carrot_raw", 100, "g", "vegetable"),
            ("celeriac", 100, "g", "vegetable"),
            ("leeks", 100, "g", "aromatic"),
            ("red_wine_vinegar_liquid", 30, "ml", "acidity"),
            ("sunflower_oil_plant", 40, "ml", "fat_cooking"),
            ("vegetable_stock_dried", 8, "g", "seasoning"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 1200, "ml", "liquid"),
        ],
        steps=[
            "Rincer 250 g de lentilles vertes et les couvrir de 900 ml d'eau avec 8 g de bouillon "
            "de légumes.",
            "Ajouter 100 g de carotte, 100 g de céleri-rave et 100 g de poireau en petits dés, "
            "puis cuire 35 minutes à feu doux.",
            "Faire frire 200 g d'oignon émincé dans 40 ml d'huile, 12 minutes, jusqu'à ce qu'il "
            "soit brun et croustillant ; en réserver la moitié.",
            "Incorporer la moitié des oignons frits aux lentilles avec 30 ml de vinaigre de vin "
            "rouge, 2 g de sel et 2 g de poivre, puis mijoter 5 minutes.",
            "Cuire 250 g de spätzle (pâtes aux œufs) dans 300 ml d'eau bouillante complétée à "
            "hauteur et salée avec 2 g de sel, 8 minutes.",
            "Dresser les spätzle, napper de lentilles et couronner des oignons frits réservés.",
        ],
        allow_similar=("spatzle",),
    ),
    recipe(
        rid="dessert_apfelstrudel_b0c517",
        fr="Apfelstrudel, strudel viennois aux pommes et aux noix",
        en="Apfelstrudel, Viennese Apple Strudel",
        original="Apfelstrudel",
        cuisine="austrian", country="austria", region="vienne",
        dish="dessert", prep=30, cook=40,
        texture=("croustillant", "fondant"), taste=("sucré", "acide"),
        technique=("bake",), difficulty="medium",
        desc="Rouleau de pâte très fine garni de pommes acidulées, de noix et de cannelle, avec "
             "de la chapelure beurrée pour absorber le jus : la pâte reste feuilletée et croquante "
             "malgré la garniture fondante.",
        compo=[
            ("phyllo_filo_pastry_raw_paste", 150, "g", "base"),
            ("apple_raw", 700, "g", "fruit"),
            ("sugars_granulated", 60, "g", "sweetener"),
            ("walnut_shelled_dried", 40, "g", "nut"),
            ("breadcrumbs_dried", 30, "g", "thickener"),
            ("butter_sup80pct", 50, "g", "fat"),
            ("cinnamon", 3, "g", "spice"),
            ("lemon_juice", 20, "ml", "acidity"),
        ],
        steps=[
            "Peler et couper 700 g de pommes en fines lamelles, les mélanger avec 20 ml de jus de "
            "citron, 50 g de sucre, 3 g de cannelle et 40 g de noix concassées.",
            "Faire dorer 30 g de chapelure dans 20 g de beurre, 3 minutes, puis laisser tiédir.",
            "Étaler les feuilles de pâte (150 g) en les badigeonnant de beurre fondu une à une.",
            "Répartir la chapelure sur un tiers de la surface, poser les pommes dessus en laissant "
            "3 cm de marge.",
            "Rouler serré en rabattant les côtés, poser la soudure en dessous sur une plaque et "
            "badigeonner du reste de beurre.",
            "Enfourner 40 minutes à 190 °C, jusqu'à ce que le strudel soit doré et ferme.",
            "Saupoudrer du reste de sucre et servir tiède, coupé en tronçons épais.",
        ],
    ),
    recipe(
        rid="entry_obatzda_46f2c9",
        fr="Obatzda, fromage bavarois battu au paprika",
        en="Obatzda, Bavarian Whipped Cheese Spread",
        original="Obatzda",
        cuisine="german", country="germany", region="baviere",
        dish="starter", prep=15, rest=60,
        texture=("crémeux", "granuleux"), taste=("salé", "umami"),
        desc="Tartinade des jardins à bière bavarois : du camembert bien mûr écrasé à la fourchette "
             "avec du beurre, de la crème et du paprika, parsemé d'oignon cru et de ciboulette, "
             "servi avec du bretzel.",
        compo=[
            ("camembert_pasteurized_cow", 250, "g", "dairy"),
            ("butter_sup80pct", 60, "g", "fat"),
            ("cream_sour_18pct", 40, "g", "dairy"),
            ("onion_raw", 60, "g", "aromatic"),
            ("paprika_powder", 5, "g", "spice"),
            ("caraway_spice_seed", 2, "g", "spice"),
            ("chives_raw_fresh", 10, "g", "herb"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Sortir 250 g de camembert une heure à l'avance : il doit être très mûr et souple.",
            "Écraser le fromage à la fourchette avec 60 g de beurre pommade, en gardant des "
            "morceaux.",
            "Ajouter 40 g de crème sure, 5 g de paprika, 2 g de carvi moulu et 2 g de poivre, "
            "mélanger sans lisser.",
            "Incorporer 30 g d'oignon haché très fin.",
            "Réserver une heure au frais pour que les arômes se lient.",
            "Parsemer du reste d'oignon en rondelles et de 10 g de ciboulette ciselée, servir avec "
            "du bretzel ou du pain de seigle.",
        ],
    ),
    recipe(
        rid="snack_laugenbrezel_03d8b7",
        fr="Laugenbrezel, bretzels allemands au gros sel",
        en="Laugenbrezel, German Salted Pretzels",
        original="Laugenbrezel",
        cuisine="german", country="germany", region="souabe",
        dish="snack", servings=6, prep=35, rest=80, cook=18,
        texture=("croustillant", "moelleux"), taste=("salé",),
        technique=("knead", "bake"), difficulty="hard",
        desc="Bretzels tressés plongés dans un bain alcalin bouillant avant cuisson : la croûte "
             "prend sa couleur brun acajou et son goût caractéristique, la mie reste blanche et "
             "élastique.",
        compo=[
            ("wheat_flour_t55", 400, "g", "base"),
            ("bakers_yeast_dehydrated", 6, "g", "ferment"),
            ("water", 230, "ml", "liquid"),
            ("butter_sup80pct", 20, "g", "fat"),
            ("baking_powder", 10, "g", "ingredient"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
        ],
        steps=[
            "Pétrir 400 g de farine, 6 g de levure sèche, 230 ml d'eau tiède, 20 g de beurre et 3 g "
            "de sel pendant 10 minutes : la pâte doit être ferme.",
            "Laisser lever 60 minutes à couvert, puis diviser en six pâtons.",
            "Rouler chaque pâton en boudin de 50 cm, fin aux extrémités, et le nouer en bretzel.",
            "Laisser reposer 20 minutes au frais, le temps que la surface sèche légèrement.",
            "Porter 1 L d'eau à ébullition avec 10 g de bicarbonate, y plonger les bretzels "
            "30 secondes par face, puis les égoutter.",
            "Entailler le ventre de chaque bretzel, saupoudrer du reste de sel et enfourner "
            "18 minutes à 220 °C jusqu'à une couleur acajou.",
        ],
    ),
    recipe(
        rid="pasta_alplermagronen_e31c40",
        fr="Älplermagronen, macaronis suisses aux pommes de terre et au fromage",
        en="Älplermagronen, Swiss Alpine Macaroni",
        original="Älplermagronen",
        cuisine="swiss", country="switzerland", region="grisons",
        dish="main", prep=20, cook=30,
        texture=("crémeux", "fondant"), taste=("umami", "lacté"),
        technique=("boil", "gratinate"),
        desc="Plat des bergers suisses : macaronis et dés de pomme de terre cuits ensemble, liés à "
             "la crème et à l'emmental, couverts d'oignons frits et servis avec de la compote de "
             "pommes qui tranche sur le gras.",
        compo=[
            ("pasta_raw_dried", 250, "g", "base", "dried"),
            ("potato_raw_flesh", 300, "g", "vegetable"),
            ("emmental_de_savoie_cow", 150, "g", "dairy"),
            ("cream_heavy_refrigerated_30pct", 100, "ml", "dairy"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("nutmeg", 1, "g", "spice"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 1500, "ml", "liquid"),
            ("apple_puree_pre_packaged", None, "en accompagnement", "serving_suggestion"),
        ],
        steps=[
            "Couper 300 g de pommes de terre en dés de 1,5 cm et les cuire 8 minutes dans 1,5 L "
            "d'eau salée (4 g de sel).",
            "Ajouter 250 g de macaronis dans la même eau et poursuivre la cuisson 9 minutes.",
            "Pendant ce temps, faire frire 150 g d'oignon émincé dans 30 g de beurre, 12 minutes, "
            "jusqu'au brun doré.",
            "Égoutter pâtes et pommes de terre, les remettre dans la casserole avec 100 ml de "
            "crème et 120 g d'emmental râpé.",
            "Mélanger hors du feu jusqu'à ce que le fromage fonde, assaisonner de 1 g de muscade, "
            "1 g de sel et 2 g de poivre.",
            "Verser dans un plat, couvrir du reste d'emmental et passer 5 minutes sous le gril.",
            "Servir couronné des oignons frits, avec de la compote de pommes.",
        ],
    ),
    recipe(
        rid="main_stamppot_boerenkool_8f50a2",
        fr="Stamppot boerenkool, purée néerlandaise au chou kale",
        en="Stamppot Boerenkool, Dutch Kale Mash",
        original="Stamppot boerenkool",
        cuisine="dutch", country="netherlands", region="hollande_du_nord",
        dish="main", prep=20, cook=30,
        texture=("épais", "fondant"), taste=("doux", "poivré"),
        technique=("boil", "mash"),
        desc="Purée néerlandaise d'hiver : des pommes de terre écrasées grossièrement avec beaucoup "
             "de chou kale émincé, du lait et du beurre, relevée de moutarde et servie avec un "
             "puits de beurre fondu au centre.",
        compo=[
            ("potato_raw_flesh", 800, "g", "vegetable"),
            ("kale_raw", 300, "g", "vegetable"),
            ("milk_liquid_pasteurized_3_5pct", 150, "ml", "dairy"),
            ("butter_sup80pct", 50, "g", "fat"),
            ("mustard", 20, "g", "condiment"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("nutmeg", 1, "g", "spice"),
            ("water", 1200, "ml", "liquid"),
        ],
        steps=[
            "Peler 800 g de pommes de terre, les couper en morceaux et les cuire 20 minutes dans "
            "1,2 L d'eau salée (4 g de sel).",
            "Retirer les côtes de 300 g de chou kale, ciseler les feuilles finement.",
            "Ajouter le kale et 100 g d'oignon émincé sur les pommes de terre pour les 8 dernières "
            "minutes de cuisson.",
            "Égoutter, puis écraser grossièrement au presse-purée en versant 150 ml de lait chaud.",
            "Incorporer 30 g de beurre, 20 g de moutarde, 1 g de sel, 2 g de poivre et 1 g de "
            "muscade : la purée doit rester rustique.",
            "Servir en creusant un puits au centre et y déposer le reste du beurre.",
        ],
    ),
    recipe(
        rid="soup_erwtensoep_2d19b6",
        fr="Erwtensoep, soupe néerlandaise aux pois cassés",
        en="Erwtensoep, Dutch Split Pea Soup",
        original="Erwtensoep",
        cuisine="dutch", country="netherlands", region="utrecht",
        dish="soup", prep=20, cook=90,
        texture=("épais", "velouté"), taste=("umami", "doux"),
        technique=("simmer",),
        desc="Soupe si épaisse que la cuillère y tient debout : pois cassés fondus avec poireau, "
             "céleri-rave et carotte, cuits une heure et demie, servis avec du pain de seigle "
             "beurré.",
        compo=[
            ("split_peas_dried", 300, "g", "plant_protein", "dried"),
            ("carrot_raw", 200, "g", "vegetable"),
            ("leeks", 150, "g", "aromatic"),
            ("celeriac", 150, "g", "vegetable"),
            ("potato_raw_flesh", 200, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("vegetable_stock_dried", 8, "g", "seasoning"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("chives_raw_fresh", 10, "g", "herb"),
            ("water", 1800, "ml", "liquid"),
            ("rye_bread", None, "en accompagnement", "serving_suggestion"),
        ],
        steps=[
            "Rincer 300 g de pois cassés et les mettre dans une grande casserole avec 1,8 L d'eau "
            "et 8 g de bouillon de légumes.",
            "Porter à ébullition, écumer, puis cuire 45 minutes à couvert et à feu doux.",
            "Ajouter 200 g de carotte, 150 g de céleri-rave, 200 g de pomme de terre en dés, 150 g "
            "de poireau et 100 g d'oignon.",
            "Poursuivre 45 minutes : les pois doivent se défaire complètement et la soupe napper "
            "la cuillère.",
            "Écraser au fouet pour lier, assaisonner de 3 g de sel et 2 g de poivre.",
            "Parsemer de 10 g de ciboulette et servir avec du pain de seigle.",
        ],
    ),
    recipe(
        rid="main_chicons_gratin_c47b83",
        fr="Chicons au gratin végétariens, endives au fromage",
        en="Vegetarian Chicons au Gratin, Belgian Endive Cheese Bake",
        original="Chicons au gratin",
        cuisine="belgian", country="belgium", region="flandre",
        dish="main", prep=20, cook=45,
        texture=("fondant", "gratiné"), taste=("amer", "lacté"),
        technique=("braise", "gratinate"),
        desc="Classique belge sans jambon : des endives braisées au beurre jusqu'à perdre leur "
             "amertume, roulées dans une béchamel au gouda et gratinées jusqu'à ce que le dessus "
             "soit tacheté de brun.",
        compo=[
            ("belgium_endive_raw", 900, "g", "vegetable"),
            ("butter_sup80pct", 50, "g", "fat"),
            ("wheat_flour_t55", 40, "g", "thickener"),
            ("milk_liquid_pasteurized_3_5pct", 500, "ml", "dairy"),
            ("gouda_cow", 150, "g", "dairy"),
            ("nutmeg", 1, "g", "spice"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Retirer le cône amer à la base de 900 g d'endives et les faire braiser 20 minutes dans "
            "20 g de beurre à couvert, en les retournant à mi-cuisson.",
            "Les égoutter et les presser délicatement pour retirer l'eau de végétation.",
            "Faire un roux avec 30 g de beurre et 40 g de farine, cuire 2 minutes sans colorer.",
            "Verser 500 ml de lait chaud en fouettant et cuire 5 minutes jusqu'à épaississement, "
            "puis assaisonner de 1 g de muscade, 4 g de sel et 2 g de poivre.",
            "Ajouter 100 g de gouda râpé hors du feu, mélanger jusqu'à fonte complète.",
            "Ranger les endives dans un plat, napper de sauce, couvrir du reste de gouda et "
            "enfourner 25 minutes à 200 °C jusqu'à ce que le gratin soit doré.",
        ],
    ),
    recipe(
        rid="snack_speculoos_1f6a05",
        fr="Speculoos, biscuits belges à la cannelle",
        en="Speculoos, Belgian Spiced Biscuits",
        original="Speculoos",
        cuisine="belgian", country="belgium", region="anvers",
        dish="snack", servings=8, prep=20, rest=720, cook=15,
        texture=("croustillant", "sec"), taste=("sucré", "épicé"),
        technique=("bake",),
        desc="Biscuits fins et cassants au sucre roux et aux épices — cannelle dominante, un peu "
             "de cardamome et de muscade — dont la pâte repose une nuit avant d'être abaissée très "
             "mince.",
        compo=[
            ("wheat_flour_t55", 250, "g", "base"),
            ("brown_sugar", 150, "g", "sweetener"),
            ("butter_sup80pct", 125, "g", "fat"),
            ("egg_raw", 25, "g", "binder"),
            ("cinnamon", 8, "g", "spice"),
            ("cardamom_powder", 2, "g", "spice"),
            ("nutmeg", 1, "g", "spice"),
            ("baking_powder", 5, "g", "ingredient"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ],
        steps=[
            "Battre 125 g de beurre pommade avec 150 g de sucre roux jusqu'à ce que le mélange "
            "blanchisse.",
            "Ajouter 25 g d'œuf battu, puis 250 g de farine tamisée avec 8 g de cannelle, 2 g de "
            "cardamome, 1 g de muscade, 5 g de poudre à lever et 2 g de sel.",
            "Former une boule, l'aplatir en disque, filmer et réserver 12 heures au frais.",
            "Abaisser la pâte à 3 mm sur un plan fariné et découper des rectangles.",
            "Enfourner 15 minutes à 170 °C : les biscuits doivent être colorés et encore souples "
            "au centre.",
            "Les laisser refroidir sur une grille, où ils durcissent et deviennent cassants.",
        ],
    ),
    recipe(
        rid="side_hasselbackspotatis_6b2e74",
        fr="Hasselbackspotatis, pommes de terre suédoises en éventail",
        en="Hasselbackspotatis, Swedish Hasselback Potatoes",
        original="Hasselbackspotatis",
        cuisine="swedish", country="sweden", region="stockholm",
        dish="side", prep=20, cook=55,
        texture=("croustillant", "fondant"), taste=("salé", "beurré"),
        technique=("bake",),
        desc="Pommes de terre entaillées en fines tranches sans les détacher, arrosées de beurre "
             "pendant la cuisson : les bords s'écartent et croustillent tandis que le cœur reste "
             "moelleux.",
        compo=[
            ("potato_raw_flesh", 900, "g", "vegetable"),
            ("butter_sup80pct", 50, "g", "fat"),
            ("olive_oil_plant", 20, "ml", "fat_cooking"),
            ("breadcrumbs_dried", 30, "g", "garnish"),
            ("thyme_fresh_herb", 5, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("chives_raw_fresh", 10, "g", "herb"),
        ],
        steps=[
            "Brosser 900 g de pommes de terre de calibre moyen, les poser dans une cuillère à "
            "soupe pour les entailler tous les 3 mm sans aller jusqu'au fond.",
            "Les badigeonner de 20 ml d'huile d'olive, saler avec 4 g de sel et poivrer avec 2 g "
            "de poivre.",
            "Enfourner 30 minutes à 200 °C, les tranches commencent à s'écarter.",
            "Arroser de 40 g de beurre fondu en insistant entre les tranches, ajouter 5 g de thym.",
            "Parsemer de 30 g de chapelure mélangée au reste de beurre et poursuivre 25 minutes "
            "jusqu'à ce que les bords soient dorés et croustillants.",
            "Parsemer de 10 g de ciboulette et servir aussitôt.",
        ],
    ),
    recipe(
        rid="bread_knackebrod_a58d19",
        fr="Knäckebröd, pain croustillant suédois au seigle",
        en="Knäckebröd, Swedish Rye Crispbread",
        original="Knäckebröd",
        cuisine="swedish", country="sweden", region="dalecarlie",
        dish="bread", servings=8, prep=25, rest=45, cook=20,
        texture=("croustillant", "sec"), taste=("céréalier",),
        technique=("bake",),
        desc="Grandes plaques de pâte de seigle abaissées très fines, piquées au rouleau et cuites "
             "jusqu'à devenir cassantes : elles se conservent des semaines et se cassent à la main "
             "pour accompagner fromages et soupes.",
        compo=[
            ("rye_flour", 300, "g", "base"),
            ("wheat_flour_t55", 100, "g", "base"),
            ("bakers_yeast_dehydrated", 5, "g", "ferment"),
            ("water", 250, "ml", "liquid"),
            ("caraway_spice_seed", 5, "g", "spice"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
        ],
        steps=[
            "Délayer 5 g de levure dans 250 ml d'eau tiède, ajouter 300 g de farine de seigle, "
            "100 g de farine de blé, 5 g de carvi et 6 g de sel.",
            "Pétrir 5 minutes : la pâte est dense et peu élastique.",
            "Laisser reposer 45 minutes à couvert.",
            "Diviser en huit, abaisser chaque part à 2 mm sur un papier cuisson fariné.",
            "Piquer toute la surface à la fourchette ou au rouleau à picots et percer un trou au "
            "centre.",
            "Enfourner 20 minutes à 210 °C, jusqu'à ce que les plaques soient sèches et dorées ; "
            "laisser refroidir sur grille avant de les empiler.",
        ],
    ),
    recipe(
        rid="dessert_kanelbullar_4e0c93",
        fr="Kanelbullar, brioches suédoises à la cannelle",
        en="Kanelbullar, Swedish Cinnamon Buns",
        original="Kanelbullar",
        cuisine="swedish", country="sweden", region="scanie",
        dish="dessert", servings=10, prep=35, rest=110, cook=15,
        texture=("moelleux", "filant"), taste=("sucré", "épicé"),
        technique=("knead", "bake"), difficulty="medium",
        desc="Brioches roulées parfumées à la cardamome, garnies d'un beurre à la cannelle et "
             "nouées en torsade : la mie reste filante et le sucre perle caramélise sur le dessus.",
        compo=[
            ("wheat_flour_t55", 400, "g", "base"),
            ("milk_liquid_pasteurized_3_5pct", 220, "ml", "dairy"),
            ("butter_sup80pct", 100, "g", "fat"),
            ("sugars_granulated", 120, "g", "sweetener"),
            ("bakers_yeast_dehydrated", 7, "g", "ferment"),
            ("cardamom_powder", 4, "g", "spice"),
            ("cinnamon", 10, "g", "spice"),
            ("egg_raw", 50, "g", "binder"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ],
        steps=[
            "Tiédir 220 ml de lait, y délayer 7 g de levure et 40 g de sucre.",
            "Ajouter 400 g de farine, 4 g de cardamome, 3 g de sel et 50 g de beurre mou, puis "
            "pétrir 10 minutes jusqu'à une pâte souple.",
            "Laisser lever 60 minutes à couvert.",
            "Mélanger 50 g de beurre pommade, 60 g de sucre et 10 g de cannelle pour la garniture.",
            "Abaisser la pâte en rectangle de 40 × 30 cm, étaler la garniture, plier en trois et "
            "découper dix bandes que l'on tord et noue.",
            "Laisser pousser 50 minutes sur la plaque, dorer à l'œuf battu (50 g) et saupoudrer du "
            "reste de sucre.",
            "Enfourner 15 minutes à 210 °C et laisser tiédir sous un linge pour garder le "
            "moelleux.",
        ],
    ),
    recipe(
        rid="beverage_blabarssoppa_7d3a26",
        fr="Blåbärssoppa, soupe suédoise de myrtilles à boire",
        en="Blåbärssoppa, Swedish Blueberry Drink",
        original="Blåbärssoppa",
        cuisine="swedish", country="sweden", region="norrland",
        dish="beverage", prep=10, cook=15, meal="beverage",
        texture=("sirupeux",), taste=("acide", "sucré"),
        technique=("simmer",),
        desc="Boisson chaude des courses de ski de fond : myrtilles cuites avec un peu de sucre et "
             "liées à la fécule, à boire en tasse ou à verser froide sur du porridge.",
        compo=[
            ("bilberry_raw", 400, "g", "fruit"),
            ("sugars_granulated", 60, "g", "sweetener"),
            ("cornstarch_flour", 15, "g", "thickener"),
            ("lemon_juice", 20, "ml", "acidity"),
            ("water", 800, "ml", "liquid"),
        ],
        steps=[
            "Porter 400 g de myrtilles, 700 ml d'eau et 60 g de sucre à frémissement, puis cuire "
            "10 minutes.",
            "Écraser les baies au presse-purée pour libérer le jus, sans mixer.",
            "Délayer 15 g de fécule de maïs dans 100 ml d'eau froide.",
            "Verser la fécule dans la casserole en fouettant et cuire 3 minutes : la boisson doit "
            "napper légèrement la cuillère.",
            "Ajouter 20 ml de jus de citron, puis servir chaud en tasse ou refroidir pour le "
            "lendemain.",
        ],
    ),
    recipe(
        rid="dessert_risalamande_92f1c8",
        fr="Risalamande, riz au lait danois aux amandes et aux cerises",
        en="Risalamande, Danish Rice Pudding with Almonds and Cherries",
        original="Risalamande",
        cuisine="danish", country="denmark", region="copenhague",
        dish="dessert", servings=6, prep=20, rest=180, cook=45,
        texture=("crémeux", "aérien"), taste=("sucré", "acide"),
        technique=("simmer",),
        desc="Dessert de Noël danois : un riz au lait refroidi allégé de crème fouettée, parsemé "
             "d'amandes hachées et servi sous une sauce de cerises acides — celui qui trouve "
             "l'amande entière gagne un cadeau.",
        compo=[
            ("white_rice_short_grain_seed_dried", 100, "g", "base", "dried"),
            ("milk_liquid_pasteurized_3_5pct", 700, "ml", "dairy"),
            ("cream_heavy_refrigerated_30pct", 200, "ml", "dairy"),
            ("sugars_granulated", 60, "g", "sweetener"),
            ("almond_raw_skinless_unsalted", 50, "g", "nut"),
            ("vanilla_extract", 5, "ml", "aroma"),
            ("sour_cherry_canned_in_water", 200, "g", "fruit"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ],
        steps=[
            "Cuire 100 g de riz rond 5 minutes dans 200 ml d'eau bouillante, puis ajouter 700 ml "
            "de lait et 1 g de sel.",
            "Laisser mijoter 40 minutes à feu très doux en remuant souvent, jusqu'à ce que le riz "
            "soit très tendre et le mélange épais.",
            "Ajouter 40 g de sucre et 5 ml de vanille, puis laisser refroidir 3 heures au "
            "réfrigérateur.",
            "Hacher 45 g d'amandes en gardant une amande entière et les incorporer au riz froid.",
            "Monter 200 ml de crème en chantilly souple et l'incorporer délicatement.",
            "Chauffer 200 g de cerises acides avec 20 g de sucre 5 minutes pour obtenir une sauce, "
            "puis la laisser refroidir.",
            "Dresser le riz en coupes et napper de sauce aux cerises au moment de servir.",
        ],
    ),
    recipe(
        rid="brkf_rommegrot_58c40e",
        fr="Rømmegrøt, porridge norvégien à la crème",
        en="Rømmegrøt, Norwegian Sour Cream Porridge",
        original="Rømmegrøt",
        cuisine="norwegian", country="norway", region="telemark",
        dish="breakfast", prep=10, cook=30,
        texture=("épais", "onctueux"), taste=("lacté", "sucré"),
        technique=("simmer",), difficulty="medium",
        desc="Bouillie de fête norvégienne : de la crème épaisse cuite avec de la farine jusqu'à ce "
             "que le beurre se sépare et remonte, allongée de lait et servie avec ce beurre, du "
             "sucre et de la cannelle.",
        compo=[
            ("cream_sour_fermented", 400, "g", "dairy"),
            ("wheat_flour_t55", 80, "g", "thickener"),
            ("milk_liquid_pasteurized_3_5pct", 400, "ml", "dairy"),
            ("sugars_granulated", 30, "g", "sweetener"),
            ("cinnamon", 3, "g", "spice"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ],
        steps=[
            "Porter 400 g de crème épaisse à frémissement dans une casserole à fond épais, "
            "10 minutes à feu doux.",
            "Incorporer 50 g de farine en pluie en fouettant : le beurre commence à se séparer.",
            "Récupérer le beurre qui remonte à la surface à la cuillère et le réserver.",
            "Ajouter le reste de la farine puis 400 ml de lait chaud en trois fois, en fouettant "
            "sans arrêt.",
            "Cuire 12 minutes à feu doux jusqu'à obtenir une bouillie épaisse et brillante, saler "
            "avec 2 g de sel.",
            "Servir en assiettes creuses, arroser du beurre réservé et saupoudrer de 30 g de sucre "
            "et 3 g de cannelle.",
        ],
    ),
    recipe(
        rid="snack_karjalanpiirakka_c9b641",
        fr="Karjalanpiirakka, tartelettes caréliennes au riz",
        en="Karjalanpiirakka, Karelian Rice Pasties",
        original="Karjalanpiirakka",
        cuisine="finnish", country="finland", region="carelie",
        dish="snack", servings=8, prep=40, cook=25,
        texture=("croustillant", "crémeux"), taste=("lacté", "salé"),
        technique=("bake",), difficulty="medium",
        desc="Barquettes finlandaises à la coque de seigle très fine garnie de riz au lait, cuites "
             "à four très chaud et badigeonnées de beurre à la sortie ; on les mange couvertes de "
             "beurre d'œuf.",
        compo=[
            ("rye_flour", 200, "g", "base"),
            ("water", 120, "ml", "liquid"),
            ("white_rice_short_grain_seed_dried", 100, "g", "base", "dried"),
            ("milk_liquid_pasteurized_3_5pct", 500, "ml", "dairy"),
            ("butter_sup80pct", 60, "g", "fat"),
            ("egg_hard_boiled", 100, "g", "animal_protein", "cooked"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Cuire 100 g de riz rond 5 minutes à l'eau, l'égoutter, puis le cuire 30 minutes dans "
            "500 ml de lait avec 2 g de sel : la bouillie doit être épaisse.",
            "Pétrir 200 g de farine de seigle, 120 ml d'eau et 2 g de sel en une pâte ferme.",
            "Diviser en seize boules et les abaisser en disques très fins de 12 cm.",
            "Garnir chaque disque de bouillie de riz et pincer les bords en les rabattant pour "
            "former une barquette ouverte.",
            "Enfourner 25 minutes à 250 °C, jusqu'à ce que les bords soient tachés de brun.",
            "Badigeonner aussitôt de 40 g de beurre fondu et couvrir d'un linge 5 minutes.",
            "Écraser 100 g d'œufs durs avec le reste du beurre et servir ce beurre d'œuf sur les "
            "tartelettes.",
        ],
    ),
    recipe(
        rid="dessert_mustikkapiirakka_3a07f5",
        fr="Mustikkapiirakka, tarte finlandaise aux myrtilles",
        en="Mustikkapiirakka, Finnish Blueberry Tart",
        original="Mustikkapiirakka",
        cuisine="finnish", country="finland", region="savonie",
        dish="dessert", servings=8, prep=25, cook=35,
        texture=("fondant", "sableux"), taste=("acide", "sucré"),
        technique=("bake",),
        desc="Tarte de chalet finlandaise : une pâte sablée pressée à la main dans le moule, des "
             "myrtilles crues par-dessus et un appareil à la crème sure qui prend au four en une "
             "couche acidulée.",
        compo=[
            ("wheat_flour_t55", 200, "g", "base"),
            ("butter_sup80pct", 100, "g", "fat"),
            ("sugars_granulated", 120, "g", "sweetener"),
            ("bilberry_raw", 400, "g", "fruit"),
            ("cream_sour_18pct", 200, "g", "dairy"),
            ("egg_raw", 50, "g", "binder"),
            ("baking_powder", 5, "g", "ingredient"),
            ("vanilla_extract", 3, "ml", "aroma"),
        ],
        steps=[
            "Travailler 100 g de beurre mou avec 60 g de sucre, puis ajouter 200 g de farine et 5 g "
            "de poudre à lever.",
            "Presser cette pâte sableuse au fond et sur les bords d'un moule de 24 cm.",
            "Répartir 400 g de myrtilles sur le fond de pâte.",
            "Fouetter 200 g de crème sure avec 50 g d'œuf, 60 g de sucre et 3 ml de vanille.",
            "Verser l'appareil sur les fruits et enfourner 35 minutes à 200 °C, jusqu'à ce que la "
            "surface soit prise et légèrement colorée.",
            "Laisser refroidir complètement avant de découper : la garniture se raffermit en "
            "tiédissant.",
        ],
    ),
    recipe(
        rid="side_colcannon_64e2b0",
        fr="Colcannon, purée irlandaise au chou frisé",
        en="Colcannon, Irish Kale Mash",
        original="Colcannon",
        cuisine="irish", country="ireland", region="leinster",
        dish="side", prep=15, cook=30,
        texture=("onctueux",), taste=("doux", "beurré"),
        technique=("boil", "mash"),
        desc="Purée irlandaise de pommes de terre au chou frisé fondu et à l'oignon nouveau, "
             "montée au lait chaud et servie avec un puits de beurre fondu au centre.",
        compo=[
            ("potato_raw_flesh", 800, "g", "vegetable"),
            ("curly_kale_raw", 250, "g", "vegetable"),
            ("milk_liquid_pasteurized_3_5pct", 150, "ml", "dairy"),
            ("butter_sup80pct", 60, "g", "fat"),
            ("green_onion_raw", 80, "g", "aromatic"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 1200, "ml", "liquid"),
        ],
        steps=[
            "Cuire 800 g de pommes de terre pelées 20 minutes dans 1,2 L d'eau salée (3 g de sel).",
            "Faire tomber 250 g de chou frisé ciselé 6 minutes dans 20 g de beurre avec 80 g "
            "d'oignon nouveau émincé.",
            "Chauffer 150 ml de lait sans le faire bouillir.",
            "Égoutter les pommes de terre, les écraser au presse-purée et les détendre avec le lait "
            "chaud.",
            "Incorporer le chou et l'oignon, 20 g de beurre, 1 g de sel et 2 g de poivre.",
            "Dresser en dôme, creuser un puits et y verser le reste du beurre fondu.",
        ],
    ),
    recipe(
        rid="snack_welsh_rarebit_0b7d52",
        fr="Welsh rarebit, toast gallois au cheddar fondu",
        en="Welsh Rarebit, Welsh Melted Cheddar Toast",
        original="Welsh rarebit",
        cuisine="british", country="united_kingdom", region="pays_de_galles",
        dish="snack", prep=10, cook=15,
        texture=("croustillant", "coulant"), taste=("umami", "piquant"),
        technique=("gratinate",),
        desc="Tranches de pain grillé nappées d'une sauce épaisse au cheddar, moutarde et sauce "
             "worcestershire végane, passées sous le gril jusqu'à cloquer : plus proche d'un gratin "
             "que d'un simple toast au fromage.",
        compo=[
            ("white_bread_unsalted", 200, "g", "base"),
            ("cheddar_cow", 200, "g", "dairy"),
            ("milk_liquid_pasteurized_3_5pct", 80, "ml", "dairy"),
            ("butter_sup80pct", 20, "g", "fat"),
            ("wheat_flour_t55", 15, "g", "thickener"),
            ("mustard", 15, "g", "condiment"),
            ("base_worcestershire_vegan_5f26ec", 10, "ml", "condiment"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("chives_raw_fresh", 10, "g", "herb"),
        ],
        steps=[
            "Faire un roux avec 20 g de beurre et 15 g de farine, cuire 2 minutes sans colorer.",
            "Verser 80 ml de lait en fouettant et cuire 3 minutes jusqu'à obtenir une sauce très "
            "épaisse.",
            "Hors du feu, ajouter 200 g de cheddar râpé, 15 g de moutarde, 10 ml de sauce "
            "worcestershire végane et 2 g de poivre, mélanger jusqu'à fonte.",
            "Griller 200 g de pain en tranches épaisses d'un seul côté.",
            "Étaler la préparation au fromage sur la face non grillée, jusqu'aux bords pour éviter "
            "qu'ils ne brûlent.",
            "Passer 5 minutes sous le gril, jusqu'à ce que le dessus cloque et se tache de brun ; "
            "parsemer de 10 g de ciboulette et servir aussitôt.",
        ],
    ),
]
