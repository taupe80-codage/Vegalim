"""Lot 13 : boissons, snacks et plats express (22 recettes).

Trois manques du recomptage : les boissons (16 avant ce lot, dont 7 laits végétaux), les snacks
et les recettes de moins de 20 minutes.
"""
from ._schema import recipe

RECIPES = [
    recipe(
        rid="beverage_cafe_de_olla_1a7c05",
        fr="Café de olla, café mexicain à la cannelle",
        en="Café de Olla, Mexican Cinnamon Coffee",
        original="Café de olla",
        cuisine="mexican", country="mexico", region="oaxaca",
        dish="beverage", prep=5, cook=12, meal="beverage",
        texture=("liquide",), taste=("amer", "sucré"),
        technique=("infuse",),
        desc="Café préparé à la mexicaine dans une jarre de terre : l'eau est d'abord sucrée au "
             "sucre roux avec cannelle et clou de girofle, puis le café moulu infuse hors du feu.",
        compo=[
            ("coffee_ground", 40, "g", "base"),
            ("brown_sugar", 60, "g", "sweetener"),
            ("cinnamon", 3, "g", "spice"),
            ("cloves", 1, "g", "spice"),
            ("water", 1000, "ml", "liquid"),
        ],
        steps=[
            "Porter 1 L d'eau à ébullition avec 60 g de sucre roux, 3 g de cannelle et 1 g de clou "
            "de girofle.",
            "Laisser bouillir 5 minutes pour que le sirop se parfume.",
            "Retirer du feu, verser 40 g de café moulu grossier et couvrir.",
            "Laisser infuser 5 minutes sans remuer : le marc descend au fond.",
            "Filtrer et servir très chaud dans des tasses en terre ou épaisses.",
        ],
    ),
    recipe(
        rid="beverage_atole_vanille_5c93b1",
        fr="Atole de vanille, boisson mexicaine au maïs",
        en="Vanilla Atole, Mexican Corn Drink",
        original="Atole",
        cuisine="mexican", country="mexico", region="puebla",
        dish="beverage", prep=5, cook=15, meal="beverage",
        texture=("onctueux", "épais"), taste=("sucré", "céréalier"),
        technique=("simmer",),
        desc="Boisson chaude épaissie à la farine de maïs, sucrée et parfumée à la vanille et à la "
             "cannelle : on la boit au petit-déjeuner ou le soir, à la cuillère presque.",
        compo=[
            ("corn_flour_seed", 60, "g", "thickener"),
            ("milk_liquid_pasteurized_3_5pct", 600, "ml", "dairy"),
            ("sugars_granulated", 60, "g", "sweetener"),
            ("vanilla_extract", 5, "ml", "aroma"),
            ("cinnamon", 2, "g", "spice"),
            ("water", 400, "ml", "liquid"),
        ],
        steps=[
            "Délayer 60 g de farine de maïs dans 400 ml d'eau froide jusqu'à disparition des "
            "grumeaux.",
            "Chauffer 600 ml de lait avec 60 g de sucre et 2 g de cannelle, sans faire bouillir.",
            "Verser la farine délayée en filet dans le lait chaud, en fouettant sans arrêt.",
            "Cuire 10 minutes à feu doux : l'atole épaissit et perd le goût de cru.",
            "Ajouter 5 ml de vanille hors du feu et servir brûlant en tasses.",
        ],
    ),
    recipe(
        rid="beverage_ayran_8d20f6",
        fr="Ayran, boisson turque au yaourt salé",
        en="Ayran, Turkish Salted Yogurt Drink",
        original="Ayran",
        cuisine="turkish", country="turkey", region="anatolie_centrale",
        dish="beverage", prep=5, meal="beverage",
        texture=("liquide", "mousseux"), taste=("acide", "salé"),
        desc="Yaourt battu avec de l'eau glacée et une pointe de sel, fouetté jusqu'à mousser : la "
             "boisson qui accompagne les grillades et les plats relevés en Turquie.",
        compo=[
            ("yogurt_fermented_plain", 600, "g", "dairy"),
            ("water", 400, "ml", "liquid"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("mint_fresh_herb", 5, "g", "herb"),
        ],
        steps=[
            "Fouetter 600 g de yaourt avec 3 g de sel jusqu'à obtenir une crème lisse.",
            "Ajouter 400 ml d'eau très froide en filet, en fouettant énergiquement.",
            "Battre encore 1 minute pour faire mousser la surface.",
            "Goûter : l'ayran doit être franchement salé et acide, jamais sucré.",
            "Servir aussitôt dans des verres glacés, avec 5 g de menthe ciselée.",
        ],
        raw=True,
    ),
    recipe(
        rid="beverage_thandai_4f6e29",
        fr="Thandai, lait indien aux amandes et aux épices",
        en="Thandai, Indian Spiced Almond Milk",
        original="Thandai",
        cuisine="indian", country="india", region="uttar_pradesh",
        dish="beverage", prep=15, rest=120, cook=10, meal="beverage",
        texture=("onctueux",), taste=("sucré", "épicé"),
        technique=("infuse",),
        desc="Boisson de la fête de Holi : amandes, pavot et cardamome trempés puis broyés en pâte, "
             "délayés dans du lait safrané et servis glacés avec des pistaches.",
        compo=[
            ("milk_liquid_pasteurized_3_5pct", 700, "ml", "dairy"),
            ("almond_raw_skinless_unsalted", 60, "g", "nut"),
            ("poppy_spice_seed", 10, "g", "spice"),
            ("cardamom_powder", 3, "g", "spice"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("saffron", 0.2, "g", "spice"),
            ("sugars_granulated", 70, "g", "sweetener"),
            ("pistachio_nuts_raw", 20, "g", "garnish"),
            ("water", 200, "ml", "liquid"),
        ],
        steps=[
            "Faire tremper 60 g d'amandes et 10 g de graines de pavot 2 heures dans 200 ml d'eau "
            "tiède.",
            "Chauffer 700 ml de lait avec 70 g de sucre et 0,2 g de safran, 10 minutes à feu doux, "
            "puis laisser tiédir.",
            "Mixer amandes et pavot égouttés avec un peu de lait jusqu'à obtenir une pâte lisse.",
            "Incorporer cette pâte au lait avec 3 g de cardamome et 1 g de poivre.",
            "Filtrer à travers une étamine en pressant, puis réfrigérer.",
            "Servir très frais, parsemé de 20 g de pistaches concassées.",
        ],
    ),
    recipe(
        rid="beverage_aam_panna_63b7d4",
        fr="Aam panna, boisson indienne à la mangue verte",
        en="Aam Panna, Indian Green Mango Cooler",
        original="Aam panna",
        cuisine="indian", country="india", region="maharashtra",
        dish="beverage", prep=10, cook=15, meal="beverage",
        texture=("liquide",), taste=("acide", "épicé"),
        technique=("boil",), spice=1,
        desc="Boisson d'été indienne contre la chaleur : de la mangue verte cuite puis écrasée, "
             "sucrée et relevée de cumin grillé et de menthe, allongée d'eau glacée.",
        compo=[
            ("mango_raw", 500, "g", "fruit"),
            ("sugars_granulated", 60, "g", "sweetener"),
            ("cumin_spice_seed", 4, "g", "spice"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("mint_fresh_herb", 10, "g", "herb"),
            ("water", 900, "ml", "liquid"),
        ],
        steps=[
            "Cuire 500 g de mangues vertes entières 15 minutes dans 300 ml d'eau, jusqu'à ce que la "
            "peau se fende.",
            "Laisser tiédir, puis récupérer la pulpe à la cuillère et la passer au tamis.",
            "Griller 4 g de cumin à sec 1 minute et le moudre.",
            "Mélanger la pulpe avec 60 g de sucre, le cumin, 3 g de sel et 10 g de menthe pilée.",
            "Allonger de 600 ml d'eau glacée et goûter : la boisson doit être acide, salée et "
            "sucrée à la fois.",
            "Servir sur glace avec une feuille de menthe.",
        ],
        allow_similar=("panna",),
    ),
    recipe(
        rid="beverage_ca_phe_sua_da_92e714",
        fr="Cà phê sữa đá, café glacé vietnamien au lait concentré",
        en="Cà Phê Sữa Đá, Vietnamese Iced Coffee",
        original="Cà phê sữa đá",
        cuisine="vietnamese", country="vietnam", region="ho_chi_minh",
        dish="beverage", prep=10, cook=5, meal="beverage",
        texture=("liquide", "sirupeux"), taste=("amer", "sucré"),
        technique=("infuse",),
        desc="Café vietnamien filtré goutte à goutte sur un fond de lait concentré sucré, remué puis "
             "versé sur de la glace : très serré, très sucré, très froid.",
        compo=[
            ("coffee_ground", 40, "g", "base"),
            ("condensed_milk_concentrated_sweetened_canned_whole", 120, "g", "dairy"),
            ("water", 500, "ml", "liquid"),
        ],
        steps=[
            "Répartir 120 g de lait concentré sucré au fond de quatre verres.",
            "Tasser 10 g de café moulu fin dans chaque filtre vietnamien (ou utiliser une cafetière "
            "à piston).",
            "Verser 50 ml d'eau à 95 °C par filtre et laisser gonfler 1 minute.",
            "Compléter avec le reste de l'eau et laisser filtrer 5 minutes : le café doit couler "
            "goutte à goutte.",
            "Remuer pour dissoudre le lait concentré, puis verser sur des verres remplis de glace.",
        ],
    ),
    recipe(
        rid="beverage_barley_water_citron_07f5c2",
        fr="Barley water au citron, orgeat britannique",
        en="Lemon Barley Water",
        original="Lemon barley water",
        cuisine="british", country="united_kingdom", region="angleterre",
        dish="beverage", prep=10, rest=60, cook=30, meal="beverage",
        texture=("liquide",), taste=("acide", "céréalier"),
        technique=("boil",), allow_similar=("barley",),
        desc="Boisson anglaise des courts de tennis : de l'orge perlé bouilli longuement, son eau "
             "filtrée puis parfumée de zeste et de jus de citron, sucrée et servie glacée.",
        compo=[
            ("barley_raw_whole_seed", 80, "g", "base", "dried"),
            ("lemon_juice", 80, "ml", "acidity"),
            ("lemon_peel_raw", 5, "g", "aroma"),
            ("sugars_granulated", 60, "g", "sweetener"),
            ("water", 1200, "ml", "liquid"),
        ],
        steps=[
            "Rincer 80 g d'orge perlé à l'eau froide jusqu'à ce que l'eau soit claire.",
            "Le couvrir de 1,2 L d'eau et cuire 30 minutes à couvert.",
            "Hors du feu, ajouter 60 g de sucre et 5 g de zeste de citron, puis couvrir.",
            "Laisser infuser 60 minutes : le liquide devient légèrement opalescent.",
            "Filtrer, ajouter 80 ml de jus de citron et réfrigérer.",
            "Servir très frais ; l'orge cuit peut être gardé pour une soupe.",
        ],
    ),
    recipe(
        rid="beverage_agua_tamarindo_3e8b90",
        fr="Agua de tamarindo, eau fraîche mexicaine au tamarin",
        en="Agua de Tamarindo, Mexican Tamarind Cooler",
        original="Agua de tamarindo",
        cuisine="mexican", country="mexico", region="jalisco",
        dish="beverage", prep=10, cook=10, meal="beverage",
        texture=("liquide",), taste=("acide", "sucré"),
        technique=("infuse",),
        desc="Une des aguas frescas les plus vendues au Mexique : pâte de tamarin délayée dans l'eau "
             "chaude, filtrée, sucrée et servie sur glace avec un trait de citron vert.",
        compo=[
            ("tamarind_paste", 80, "g", "fruit"),
            ("sugars_granulated", 70, "g", "sweetener"),
            ("lime_raw_juice_fresh", 20, "ml", "acidity"),
            ("water", 1200, "ml", "liquid"),
        ],
        steps=[
            "Délayer 80 g de pâte de tamarin dans 400 ml d'eau chaude, en écrasant à la fourchette.",
            "Laisser infuser 10 minutes puis passer au tamis en pressant la pulpe.",
            "Dissoudre 70 g de sucre dans le liquide encore tiède.",
            "Allonger de 800 ml d'eau froide et ajouter 20 ml de jus de citron vert.",
            "Goûter et ajuster le sucre selon l'acidité du tamarin, puis servir sur glace.",
        ],
    ),
    recipe(
        rid="snack_mandazi_b4f108",
        fr="Mandazi, beignets kényans au lait de coco",
        en="Mandazi, Kenyan Coconut Doughnuts",
        original="Mandazi",
        cuisine="kenyan", country="kenya", region="mombasa",
        dish="snack", servings=6, prep=20, rest=30, cook=15,
        texture=("moelleux", "croustillant"), taste=("sucré", "épicé"),
        technique=("fry",),
        desc="Beignets triangulaires de la côte swahilie, parfumés à la cardamome et au lait de "
             "coco : ils gonflent en friture et se mangent tièdes au petit-déjeuner ou avec le thé.",
        compo=[
            ("wheat_flour_t55", 300, "g", "base"),
            ("coconut_milk_plant", 150, "ml", "dairy_alt"),
            ("sugars_granulated", 60, "g", "sweetener"),
            ("egg_raw", 50, "g", "binder"),
            ("baking_powder", 8, "g", "ingredient"),
            ("cardamom_powder", 3, "g", "spice"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("sunflower_oil_plant", 70, "ml", "fat_cooking"),
        ],
        steps=[
            "Mélanger 300 g de farine, 60 g de sucre, 8 g de poudre à lever, 3 g de cardamome et "
            "2 g de sel.",
            "Ajouter 50 g d'œuf battu et 150 ml de lait de coco, puis pétrir 5 minutes en une pâte "
            "souple.",
            "Laisser reposer 30 minutes sous un linge.",
            "Abaisser la pâte à 1 cm et découper des triangles de 6 cm.",
            "Chauffer 70 ml d'huile et frire les mandazi 4 minutes en les retournant, jusqu'à ce "
            "qu'ils soient gonflés et dorés.",
            "Égoutter sur papier absorbant et servir tièdes.",
        ],
    ),
    recipe(
        rid="entry_halloumi_grille_2d6c85",
        fr="Halloumi grillé au citron et à la menthe",
        en="Grilled Halloumi with Lemon and Mint",
        cuisine="cypriot", country="cyprus", region="nicosie",
        dish="starter", prep=5, cook=8,
        texture=("croustillant", "élastique"), taste=("salé", "acide"),
        technique=("grill",), allow_similar=("halloumi",),
        desc="Tranches de halloumi saisies à sec sur une poêle brûlante jusqu'à ce qu'elles dorent "
             "et grincent sous la dent, arrosées de jus de citron et parsemées de menthe.",
        compo=[
            ("base_halloumi_293d5e", 300, "g", "dairy"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("mint_fresh_herb", 8, "g", "herb"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Couper 300 g de halloumi en tranches de 1 cm et les éponger soigneusement.",
            "Chauffer une poêle à sec jusqu'à ce qu'elle fume légèrement.",
            "Saisir les tranches 2 minutes par face, sans y toucher, jusqu'à une croûte dorée.",
            "Les disposer sur un plat et arroser de 20 ml d'huile d'olive et 30 ml de jus de "
            "citron.",
            "Parsemer de 8 g de menthe ciselée et 2 g de poivre, servir immédiatement : le halloumi "
            "durcit en refroidissant.",
        ],
    ),
    recipe(
        rid="entry_houmous_betterave_51b3e7",
        fr="Houmous de betterave au cumin",
        en="Beetroot Hummus with Cumin",
        cuisine="levantine", country="lebanon", region="beyrouth",
        dish="starter", prep=15,
        texture=("crémeux",), taste=("doux", "terreux"),
        desc="Houmous rose vif : betterave cuite mixée avec les pois chiches et le tahini, relevée "
             "de cumin grillé et de citron, plus douce et plus sucrée que le houmous classique.",
        compo=[
            ("beetroot_cooked_root", 250, "g", "vegetable", "cooked"),
            ("chickpea_rinsed_canned", 250, "g", "plant_protein", "cooked"),
            ("sesame_tahini_raw_butter_seed_plant", 50, "ml", "condiment"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("garlic_raw", 8, "g", "aromatic"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Griller 3 g de cumin à sec 1 minute, puis le moudre au mortier.",
            "Mixer 250 g de betterave cuite avec 250 g de pois chiches rincés, 50 ml de tahini, "
            "30 ml de jus de citron et 8 g d'ail.",
            "Ajouter le cumin et 4 g de sel, mixer 2 minutes jusqu'à obtenir une crème lisse.",
            "Détendre avec une cuillerée d'eau froide si la texture est trop dense.",
            "Étaler dans une assiette creuse, arroser de 30 ml d'huile d'olive et servir avec du "
            "pain plat.",
        ],
    ),
    recipe(
        rid="entry_roules_courgette_ricotta_c8a460",
        fr="Roulés de courgette grillée à la ricotta",
        en="Grilled Zucchini Rolls with Ricotta",
        cuisine="italian", country="italy", region="ligurie",
        dish="starter", prep=15, cook=10,
        texture=("fondant", "crémeux"), taste=("doux", "herbacé"),
        technique=("grill",),
        desc="Lamelles de courgette grillées puis roulées autour d'une ricotta citronnée au "
             "parmesan, parsemées de pignons : un antipasto qui se mange tiède ou froid.",
        compo=[
            ("green_zucchini_squash_raw", 500, "g", "vegetable"),
            ("ricotta_whole_cow", 250, "g", "dairy"),
            ("parmesan_grated_dried_cow", 30, "g", "dairy"),
            ("pine_nuts_raw", 20, "g", "garnish"),
            ("mint_fresh_herb", 8, "g", "herb"),
            ("lemon_peel_raw", 5, "g", "aroma"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Trancher 500 g de courgettes dans la longueur à 3 mm, à la mandoline si possible.",
            "Les badigeonner de 15 ml d'huile d'olive et les griller 2 minutes par face sur une "
            "poêle-gril brûlante.",
            "Mélanger 250 g de ricotta avec 30 g de parmesan, 5 g de zeste de citron, 8 g de menthe "
            "ciselée, 3 g de sel et 2 g de poivre.",
            "Déposer une cuillerée de ricotta à l'extrémité de chaque lamelle tiède et rouler.",
            "Ranger les roulés sur un plat, arroser du reste d'huile et parsemer de 20 g de pignons "
            "grillés.",
        ],
    ),
    recipe(
        rid="snack_pisang_goreng_9f4d21",
        fr="Pisang goreng, beignets de banane indonésiens",
        en="Pisang Goreng, Indonesian Banana Fritters",
        original="Pisang goreng",
        cuisine="indonesian", country="indonesia", region="java",
        dish="snack", prep=15, cook=15,
        texture=("croustillant", "fondant"), taste=("sucré",),
        technique=("fry",),
        desc="Bananes enrobées d'une pâte à la farine de riz qui devient très croustillante à la "
             "friture, vendues à tous les coins de rue en Indonésie et mangées brûlantes.",
        compo=[
            ("banana_raw", 500, "g", "fruit"),
            ("wheat_flour_t55", 100, "g", "base"),
            ("rice_flour", 50, "g", "base"),
            ("sugars_granulated", 20, "g", "sweetener"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("water", 120, "ml", "liquid"),
            ("sunflower_oil_plant", 80, "ml", "fat_cooking"),
        ],
        steps=[
            "Mélanger 100 g de farine de blé, 50 g de farine de riz, 20 g de sucre et 2 g de sel.",
            "Ajouter 120 ml d'eau glacée en fouettant : la pâte doit napper le dos d'une cuillère.",
            "Peler 500 g de bananes et les couper en deux dans la longueur.",
            "Chauffer 80 ml d'huile à 170 °C dans une sauteuse.",
            "Tremper les bananes dans la pâte et les frire 3 minutes par face, jusqu'à ce que "
            "l'enrobage soit doré et bulleux.",
            "Égoutter sur une grille et servir aussitôt, éventuellement avec un filet de miel.",
        ],
    ),
    recipe(
        rid="snack_pao_de_queijo_0c73f5",
        fr="Pão de queijo, petits pains brésiliens au fromage",
        en="Pão de Queijo, Brazilian Cheese Bread",
        original="Pão de queijo",
        cuisine="brazilian", country="brazil", region="minas_gerais",
        dish="snack", servings=6, prep=20, cook=25,
        texture=("élastique", "croustillant"), taste=("salé", "lacté"),
        technique=("bake",), difficulty="medium",
        desc="Petits pains sans gluten à l'amidon de manioc, élastiques à l'intérieur et croustillants "
             "dehors, chargés de fromage râpé : le goûter emblématique du Minas Gerais.",
        compo=[
            ("tapioca_raw_dried", 250, "g", "base"),
            ("milk_liquid_pasteurized_3_5pct", 120, "ml", "dairy"),
            ("sunflower_oil_plant", 60, "ml", "fat"),
            ("egg_raw", 100, "g", "binder"),
            ("parmesan_grated_dried_cow", 100, "g", "dairy"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Porter 120 ml de lait, 60 ml d'huile et 4 g de sel à ébullition.",
            "Verser ce liquide bouillant sur 250 g d'amidon de manioc et mélanger vivement : la "
            "pâte devient grumeleuse et translucide.",
            "Laisser tiédir 10 minutes, puis incorporer 100 g d'œufs battus en travaillant à la "
            "main.",
            "Ajouter 100 g de parmesan râpé et pétrir jusqu'à obtenir une pâte souple et "
            "collante.",
            "Former dix-huit boules de la taille d'une noix et les ranger espacées sur une plaque.",
            "Enfourner 25 minutes à 190 °C, jusqu'à ce que les pains soient gonflés et dorés ; "
            "servir chauds.",
        ],
    ),
    recipe(
        rid="snack_chin_chin_7b52e0",
        fr="Chin chin, biscuits frits nigérians à la muscade",
        en="Chin Chin, Nigerian Fried Nutmeg Biscuits",
        original="Chin chin",
        cuisine="nigerian", country="nigeria", region="lagos",
        dish="snack", servings=8, prep=20, rest=30, cook=20,
        texture=("croustillant", "sec"), taste=("sucré", "épicé"),
        technique=("fry",),
        desc="Petits dés de pâte sucrée à la muscade, frits jusqu'à devenir durs et croquants : ils "
             "se grignotent par poignées et se conservent des semaines en boîte.",
        compo=[
            ("wheat_flour_t55", 300, "g", "base"),
            ("sugars_granulated", 80, "g", "sweetener"),
            ("butter_sup80pct", 60, "g", "fat"),
            ("egg_raw", 50, "g", "binder"),
            ("milk_liquid_pasteurized_3_5pct", 60, "ml", "dairy"),
            ("nutmeg", 2, "g", "spice"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("sunflower_oil_plant", 80, "ml", "fat_cooking"),
        ],
        steps=[
            "Mélanger 300 g de farine, 80 g de sucre, 2 g de muscade râpée et 2 g de sel.",
            "Sabler avec 60 g de beurre froid, puis lier avec 50 g d'œuf et 60 ml de lait.",
            "Pétrir brièvement et laisser reposer 30 minutes.",
            "Abaisser la pâte à 4 mm et la découper en dés de 1 cm au couteau.",
            "Chauffer 80 ml d'huile à 165 °C et frire les dés par petites quantités, 4 minutes, en "
            "remuant.",
            "Égoutter et laisser refroidir complètement : les chin chin durcissent en "
            "refroidissant.",
        ],
    ),
    recipe(
        rid="main_tofu_gingembre_express_4e91c6",
        fr="Tofu sauté au gingembre et à la sauce soja",
        en="Ginger Soy Stir-Fried Tofu",
        cuisine="chinese", country="china", region="canton",
        dish="main", prep=8, cook=10,
        texture=("croustillant", "fondant"), taste=("umami", "piquant"),
        technique=("stir_fry",),
        desc="Plat de semaine en dix minutes : cubes de tofu enrobés de fécule et saisis jusqu'à "
             "croustiller, glacés d'une sauce soja au gingembre et à l'oignon vert, servis sur du "
             "riz.",
        compo=[
            ("tofu_plain_pre_packaged", 500, "g", "plant_protein"),
            ("cornstarch_flour", 15, "g", "thickener"),
            ("ginger_raw_root_fresh", 25, "g", "aromatic"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("green_onion_raw", 80, "g", "aromatic"),
            ("soy_sauce_tamari", 40, "ml", "condiment"),
            ("sesame_oil_plant", 15, "ml", "fat"),
            ("sunflower_oil_plant", 25, "ml", "fat_cooking"),
            ("sugars_granulated", 5, "g", "balance"),
            ("white_rice_long_grain_seed_dried", 200, "g", "base", "dried"),
        ],
        steps=[
            "Égoutter 500 g de tofu, le couper en cubes de 2 cm et les rouler dans 15 g de fécule.",
            "Lancer la cuisson de 200 g de riz à l'eau salée.",
            "Saisir le tofu dans 25 ml d'huile à feu vif, 6 minutes, sans le remuer trop souvent "
            "pour qu'il croustille.",
            "Ajouter 25 g de gingembre râpé et 12 g d'ail, remuer 30 secondes.",
            "Verser 40 ml de tamari mélangé à 5 g de sucre et 30 ml d'eau, laisser glacer "
            "2 minutes.",
            "Hors du feu, ajouter 15 ml d'huile de sésame et 80 g d'oignon vert, servir sur le riz.",
        ],
    ),
    recipe(
        rid="wrap_falafel_tahini_6a2d73",
        fr="Wrap de falafels à la sauce tahini",
        en="Falafel Wrap with Tahini Sauce",
        cuisine="levantine", country="lebanon", region="beyrouth",
        dish="main", prep=15,
        texture=("croustillant", "frais"), taste=("umami", "acide"),
        allow_similar=("falafels",),
        desc="Assemblage express à partir de falafels déjà prêts : pain pita chaud, crudités "
             "croquantes, sauce au tahini citronnée et yaourt, roulés serré dans du papier.",
        compo=[
            ("falafel", 300, "g", "plant_protein", "cooked"),
            ("white_pita_bread", 240, "g", "base"),
            ("sesame_tahini_raw_butter_seed_plant", 40, "ml", "condiment"),
            ("yogurt_fermented_plain", 100, "g", "dairy"),
            ("lemon_juice", 20, "ml", "acidity"),
            ("tomato_raw_ripe", 150, "g", "vegetable"),
            ("cucumber_raw", 150, "g", "vegetable"),
            ("red_cabbage_raw", 100, "g", "vegetable"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ],
        steps=[
            "Fouetter 40 ml de tahini avec 100 g de yaourt, 20 ml de jus de citron, 2 g de sel et "
            "un peu d'eau froide jusqu'à obtenir une sauce nappante.",
            "Émincer 100 g de chou rouge, couper 150 g de tomate et 150 g de concombre en dés.",
            "Réchauffer 240 g de pain pita 1 minute à la poêle sèche pour le rendre souple.",
            "Étaler la sauce sur chaque pain, répartir 300 g de falafels écrasés à la fourchette.",
            "Ajouter les crudités et 15 g de persil, puis rouler serré dans du papier cuisson pour "
            "maintenir le wrap.",
        ],
    ),
    recipe(
        rid="salad_pois_chiches_express_b39e57",
        fr="Salade de pois chiches express au citron et à la feta",
        en="Quick Chickpea Salad with Lemon and Feta",
        cuisine="greek", country="greece", region="attique",
        dish="starter", prep=12,
        texture=("croquant", "fondant"), taste=("acide", "salé"),
        desc="Salade assemblée en douze minutes sans cuisson : pois chiches en conserve, concombre "
             "et tomate en dés, feta émiettée et beaucoup de citron, d'huile d'olive et d'herbes.",
        compo=[
            ("chickpea_rinsed_canned", 400, "g", "plant_protein", "cooked"),
            ("cucumber_raw", 200, "g", "vegetable"),
            ("tomato_raw_ripe", 200, "g", "vegetable"),
            ("feta_cow", 100, "g", "dairy"),
            ("onion_raw", 80, "g", "aromatic"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("mint_fresh_herb", 8, "g", "herb"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Rincer et égoutter 400 g de pois chiches en conserve.",
            "Couper 200 g de concombre et 200 g de tomate en dés de 1 cm, émincer 80 g d'oignon très "
            "fin.",
            "Fouetter 40 ml d'huile d'olive avec 30 ml de jus de citron, 3 g de sel et 2 g de "
            "poivre.",
            "Mélanger les légumes, les pois chiches et la vinaigrette.",
            "Ajouter 100 g de feta émiettée, 15 g de persil et 8 g de menthe, mélanger "
            "délicatement et servir.",
        ],
        raw=True,
    ),
    recipe(
        rid="brkf_oeufs_brouilles_ciboulette_d05a18",
        fr="Œufs brouillés crémeux à la ciboulette",
        en="Creamy Scrambled Eggs with Chives",
        cuisine="french", country="france", region="ile_de_france",
        dish="breakfast", prep=5, cook=8,
        texture=("crémeux", "fondant"), taste=("lacté", "herbacé"),
        technique=("simmer",), allow_similar=("brouilles", "ciboulette"),
        desc="Œufs brouillés cuits très doucement, presque comme une crème, montés au beurre et à "
             "la crème hors du feu et servis sur du pain grillé chaud.",
        compo=[
            ("egg_raw", 300, "g", "animal_protein"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("cream_heavy_refrigerated_30pct", 40, "ml", "dairy"),
            ("chives_raw_fresh", 12, "g", "herb"),
            ("white_bread_roasted", 120, "g", "base"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Battre 300 g d'œufs à la fourchette sans les faire mousser.",
            "Faire fondre 20 g de beurre dans une casserole à feu très doux.",
            "Verser les œufs et remuer sans arrêt à la spatule, 6 minutes : ils doivent prendre en "
            "petits grains serrés, jamais secs.",
            "Retirer du feu dès qu'ils nappent la spatule, puis incorporer 40 ml de crème et le "
            "reste du beurre.",
            "Assaisonner de 3 g de sel et 2 g de poivre, ajouter 12 g de ciboulette et servir sur "
            "120 g de pain grillé.",
        ],
    ),
    recipe(
        rid="noodle_yaki_udon_legumes_38c0b4",
        fr="Yaki udon aux légumes et au tofu fumé",
        en="Yaki Udon with Vegetables and Smoked Tofu",
        original="Yaki udon",
        cuisine="japanese", country="japan", region="kanto",
        dish="main", prep=10, cook=10,
        texture=("souple", "croquant"), taste=("umami", "salé"),
        technique=("stir_fry",), allow_similar=("udon",),
        desc="Nouilles udon épaisses saisies au wok avec chou, carotte et champignons, laquées de "
             "sauce soja et d'huile de sésame : dix minutes de cuisson, servi avec beaucoup "
             "d'oignon vert.",
        compo=[
            ("udon", 600, "g", "base", "cooked"),
            ("tofu_smoked_pre_packaged", 200, "g", "plant_protein"),
            ("cabbage_raw", 200, "g", "vegetable"),
            ("carrot_raw", 120, "g", "vegetable"),
            ("button_mushroom_raw", 150, "g", "vegetable"),
            ("green_onion_raw", 80, "g", "aromatic"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("soy_sauce_tamari", 45, "ml", "condiment"),
            ("sesame_oil_plant", 15, "ml", "fat"),
            ("sunflower_oil_plant", 25, "ml", "fat_cooking"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Détacher 600 g d'udon cuits sous un filet d'eau tiède pour qu'ils ne collent pas.",
            "Saisir 200 g de tofu fumé en bâtonnets dans 25 ml d'huile, 3 minutes à feu vif, puis "
            "réserver.",
            "Faire sauter 12 g d'ail, 15 g de gingembre, 200 g de chou émincé, 120 g de carotte en "
            "julienne et 150 g de champignons en lamelles, 4 minutes.",
            "Ajouter les udon et le tofu, puis 45 ml de tamari et 2 g de poivre, sauter 3 minutes "
            "en décollant le fond.",
            "Hors du feu, ajouter 15 ml d'huile de sésame et 80 g d'oignon vert, servir aussitôt.",
        ],
    ),
    recipe(
        rid="snack_aloo_chaat_94e6c1",
        fr="Aloo chaat, pommes de terre épicées au tamarin",
        en="Aloo Chaat, Spiced Potatoes with Tamarind",
        original="Aloo chaat",
        cuisine="indian", country="india", region="delhi",
        dish="snack", prep=10, cook=20,
        texture=("croustillant", "fondant"), taste=("acide", "piquant"),
        technique=("fry",), spice=3, kid_friendly=False, allow_similar=("chaat",),
        desc="Snack de rue de Delhi : des dés de pomme de terre frits jusqu'à croustiller, "
             "assaisonnés de cumin grillé, de piment et de tamarin, avec beaucoup de coriandre et "
             "de citron vert.",
        compo=[
            ("potato_raw_flesh", 700, "g", "vegetable"),
            ("tamarind_paste", 30, "g", "acidity"),
            ("coriander", 15, "g", "herb"),
            ("red_hot_chili_pepper_raw", 10, "g", "spice"),
            ("cumin_spice_seed", 4, "g", "spice"),
            ("onion_raw", 80, "g", "aromatic"),
            ("lime_raw_juice_fresh", 25, "ml", "acidity"),
            ("sunflower_oil_plant", 40, "ml", "fat_cooking"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("water", 800, "ml", "liquid"),
        ],
        steps=[
            "Couper 700 g de pommes de terre en dés de 2 cm et les cuire 8 minutes dans 800 ml "
            "d'eau salée (2 g de sel), puis les égoutter et les sécher.",
            "Les faire dorer 10 minutes dans 40 ml d'huile bien chaude, en les retournant peu.",
            "Griller 4 g de cumin à sec et le moudre grossièrement.",
            "Délayer 30 g de pâte de tamarin dans 40 ml d'eau chaude.",
            "Mélanger les pommes de terre chaudes avec le tamarin, le cumin, 10 g de piment haché, "
            "80 g d'oignon cru et 2 g de sel.",
            "Ajouter 25 ml de jus de citron vert et 15 g de coriandre, servir aussitôt.",
        ],
    ),
    recipe(
        rid="snack_toast_haricots_romarin_5f80d2",
        fr="Toasts de haricots blancs écrasés au romarin",
        en="Crushed White Bean Toasts with Rosemary",
        cuisine="italian", country="italy", region="toscane",
        dish="snack", prep=7, cook=5,
        texture=("croustillant", "crémeux"), taste=("herbacé", "doux"),
        technique=("toast",), allow_similar=("romarin",),
        desc="Version toscane du toast express : haricots blancs écrasés à la fourchette avec de "
             "l'ail et du romarin frit dans l'huile d'olive, étalés sur du pain grillé.",
        compo=[
            ("white_bean_canned", 400, "g", "plant_protein", "cooked"),
            ("white_bread_roasted", 160, "g", "base"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("rosemary_fresh_herb", 4, "g", "herb"),
            ("lemon_juice", 20, "ml", "acidity"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Faire chauffer 30 ml d'huile d'olive avec 10 g d'ail écrasé et 4 g de romarin, "
            "3 minutes à feu doux, jusqu'à ce que l'huile soit parfumée.",
            "Ajouter 400 g de haricots blancs égouttés et les réchauffer 2 minutes.",
            "Les écraser grossièrement à la fourchette en gardant des morceaux entiers.",
            "Assaisonner de 20 ml de jus de citron, 3 g de sel et 2 g de poivre.",
            "Griller 160 g de pain, l'arroser du reste d'huile et le tartiner généreusement de "
            "purée de haricots tiède.",
        ],
    ),
]
