"""Lot 14 : desserts du monde, petits-déjeuners, plats sans gluten et recettes crues (20 recettes).

Dernier lot de la montée à 1 000 recettes : huit desserts non européens ou peu représentés,
quatre petits-déjeuners, quatre préparations crues et quatre plats (dont trois sans gluten).
"""
from ._schema import recipe

RECIPES = [
    recipe(
        rid="dessert_pasteis_de_nata_7c14b9",
        fr="Pastéis de nata, flans portugais à la cannelle",
        en="Pastéis de Nata, Portuguese Custard Tarts",
        original="Pastéis de nata",
        cuisine="portuguese", country="portugal", region="lisbonne",
        dish="dessert", servings=6, prep=30, cook=20,
        texture=("croustillant", "crémeux"), taste=("sucré", "lacté"),
        technique=("bake",), difficulty="hard",
        desc="Petits flans lisboètes en coque de pâte feuilletée roulée : la crème pâtissière au "
             "zeste de citron est cuite à four très chaud jusqu'à ce que le dessus se tache de noir, "
             "et se mange tiède saupoudrée de cannelle.",
        compo=[
            ("puff_pastry_all_butter_raw_paste_pre_packaged", 250, "g", "base"),
            ("milk_liquid_pasteurized_3_5pct", 300, "ml", "dairy"),
            ("egg_raw", 100, "g", "binder"),
            ("sugars_granulated", 120, "g", "sweetener"),
            ("wheat_flour_t55", 25, "g", "thickener"),
            ("lemon_peel_raw", 5, "g", "aroma"),
            ("cinnamon", 2, "g", "spice"),
        ],
        steps=[
            "Rouler 250 g de pâte feuilletée en boudin serré, le couper en douze tronçons et écraser "
            "chaque rondelle au pouce dans une empreinte de moule à muffins.",
            "Délayer 25 g de farine dans 100 ml de lait froid, puis chauffer le reste du lait avec "
            "5 g de zeste de citron.",
            "Verser la farine délayée dans le lait chaud et cuire 3 minutes en fouettant jusqu'à "
            "épaississement.",
            "Faire un sirop avec 120 g de sucre et 60 ml d'eau porté à 100 °C, puis l'incorporer à "
            "la crème tiède.",
            "Ajouter 100 g de jaunes d'œufs battus hors du feu, passer la crème au tamis et remplir "
            "les fonds aux trois quarts.",
            "Enfourner 20 minutes à 250 °C, jusqu'à ce que la crème boursoufle et se tache de brun "
            "presque noir.",
            "Démouler tiède et saupoudrer de 2 g de cannelle.",
        ],
    ),
    recipe(
        rid="dessert_knafeh_fromage_2e58d0",
        fr="Knafeh au fromage et au sirop de rose",
        en="Cheese Knafeh with Rose Syrup",
        original="Knafeh",
        cuisine="levantine", country="lebanon", region="tripoli",
        dish="dessert", servings=8, prep=25, cook=35,
        texture=("croustillant", "filant"), taste=("sucré", "floral"),
        technique=("bake",), difficulty="medium",
        desc="Dessert levantin servi brûlant : une couche de cheveux de pâte beurrés, une couche de "
             "fromage doux qui file, et du sirop parfumé à l'eau de rose versé à la sortie du four.",
        compo=[
            ("phyllo_filo_pastry_raw_paste", 200, "g", "base"),
            ("cows_milk_mozzarella_cow", 250, "g", "dairy"),
            ("ricotta_whole_cow", 150, "g", "dairy"),
            ("butter_sup80pct", 80, "g", "fat"),
            ("sugars_granulated", 150, "g", "sweetener"),
            ("rose_water", 10, "ml", "aroma"),
            ("pistachio_nuts_raw", 30, "g", "garnish"),
            ("lemon_juice", 10, "ml", "acidity"),
            ("water", 150, "ml", "liquid"),
        ],
        steps=[
            "Préparer le sirop : cuire 150 g de sucre, 150 ml d'eau et 10 ml de jus de citron "
            "8 minutes, puis ajouter 10 ml d'eau de rose et laisser refroidir.",
            "Hacher grossièrement 200 g de pâte filo au couteau pour imiter les cheveux de knafeh, "
            "et les mélanger à 60 g de beurre fondu jusqu'à ce que tout soit enrobé.",
            "Tasser la moitié de la pâte au fond d'un moule beurré avec le reste du beurre.",
            "Mélanger 250 g de mozzarella râpée et 150 g de ricotta, répartir sur la pâte en "
            "laissant 1 cm de bord.",
            "Couvrir du reste de pâte et tasser fermement à la paume.",
            "Enfourner 35 minutes à 200 °C, jusqu'à ce que le dessous soit doré (vérifier en "
            "soulevant un bord).",
            "Démouler à l'envers, arroser aussitôt de sirop froid et parsemer de 30 g de pistaches ; "
            "servir immédiatement pour que le fromage file.",
        ],
    ),
    recipe(
        rid="dessert_gulab_jamun_a6b371",
        fr="Gulab jamun, beignets indiens au sirop de rose",
        en="Gulab Jamun, Indian Milk Dumplings in Rose Syrup",
        original="Gulab jamun",
        cuisine="indian", country="india", region="bengale_occidental",
        dish="dessert", servings=8, prep=25, rest=30, cook=30,
        texture=("fondant", "spongieux"), taste=("sucré", "floral"),
        technique=("fry",), difficulty="hard",
        desc="Boulettes de lait en poudre frites à basse température jusqu'à un brun profond, puis "
             "gorgées d'un sirop à la cardamome et à l'eau de rose : elles doivent être trempées à "
             "cœur et servies tièdes.",
        compo=[
            ("milk_powder_whole", 200, "g", "dairy"),
            ("wheat_flour_t55", 40, "g", "base"),
            ("butter_sup80pct", 20, "g", "fat"),
            ("milk_liquid_pasteurized_3_5pct", 60, "ml", "dairy"),
            ("baking_powder", 2, "g", "ingredient"),
            ("sugars_granulated", 250, "g", "sweetener"),
            ("cardamom_powder", 3, "g", "spice"),
            ("rose_water", 10, "ml", "aroma"),
            ("sunflower_oil_plant", 80, "ml", "fat_cooking"),
            ("water", 500, "ml", "liquid"),
        ],
        steps=[
            "Cuire 250 g de sucre dans 500 ml d'eau avec 3 g de cardamome 10 minutes, ajouter 10 ml "
            "d'eau de rose et garder le sirop tiède.",
            "Mélanger 200 g de lait en poudre, 40 g de farine, 2 g de poudre à lever et 20 g de "
            "beurre fondu.",
            "Ajouter 60 ml de lait peu à peu pour former une pâte souple, sans la travailler : elle "
            "doit rester tendre.",
            "Laisser reposer 30 minutes, puis rouler seize boules bien lisses, sans fissure.",
            "Chauffer 80 ml d'huile à 130 °C seulement et frire les boules 8 minutes en les "
            "remuant sans arrêt : elles doivent brunir lentement et gonfler.",
            "Les plonger aussitôt dans le sirop tiède et laisser tremper 20 minutes : elles doublent "
            "de volume.",
            "Servir deux gulab jamun par personne avec un peu de sirop.",
        ],
    ),
    recipe(
        rid="dessert_tres_leches_5b09e4",
        fr="Pastel de tres leches, gâteau mexicain aux trois laits",
        en="Pastel de Tres Leches, Mexican Three-Milk Cake",
        original="Pastel de tres leches",
        cuisine="mexican", country="mexico", region="mexico_city",
        dish="dessert", servings=10, prep=25, rest=240, cook=30,
        texture=("moelleux", "imbibé"), taste=("sucré", "lacté"),
        technique=("bake",), difficulty="medium", allow_similar=("pastel",),
        desc="Génoise sèche percée à la fourchette puis noyée d'un mélange de lait concentré sucré, "
             "de lait concentré non sucré et de crème : elle absorbe tout et devient spongieuse, "
             "servie très froide sous une chantilly.",
        compo=[
            ("wheat_flour_t55", 150, "g", "base"),
            ("egg_raw", 200, "g", "binder"),
            ("sugars_granulated", 150, "g", "sweetener"),
            ("condensed_milk_concentrated_sweetened_canned_whole", 200, "g", "dairy"),
            ("condensed_milk_concentrated_unsweetened_whole", 200, "ml", "dairy"),
            ("cream_heavy_refrigerated_30pct", 200, "ml", "dairy"),
            ("vanilla_extract", 5, "ml", "aroma"),
            ("baking_powder", 5, "g", "ingredient"),
            ("cinnamon", 2, "g", "spice"),
        ],
        steps=[
            "Séparer 200 g d'œufs, monter les blancs en neige avec 50 g de sucre.",
            "Battre les jaunes avec 100 g de sucre jusqu'à ce qu'ils blanchissent, puis incorporer "
            "150 g de farine tamisée avec 5 g de poudre à lever.",
            "Ajouter les blancs en deux fois et verser dans un moule rectangulaire beurré.",
            "Enfourner 30 minutes à 175 °C, jusqu'à ce que la pointe d'un couteau ressorte sèche.",
            "Percer le gâteau tiède de coups de fourchette sur toute la surface.",
            "Mélanger 200 g de lait concentré sucré, 200 ml de lait concentré non sucré et 100 ml de "
            "crème avec 5 ml de vanille, puis verser lentement sur le gâteau.",
            "Réfrigérer 4 heures, monter le reste de crème en chantilly, en couvrir le gâteau et "
            "saupoudrer de 2 g de cannelle.",
        ],
    ),
    recipe(
        rid="dessert_tarta_de_santiago_d82f16",
        fr="Tarta de Santiago, gâteau galicien aux amandes",
        en="Tarta de Santiago, Galician Almond Cake",
        original="Tarta de Santiago",
        cuisine="spanish", country="spain", region="galice",
        dish="dessert", servings=8, prep=15, cook=35,
        texture=("dense", "moelleux"), taste=("sucré", "amande"),
        technique=("bake",),
        desc="Gâteau de Saint-Jacques-de-Compostelle sans farine : uniquement des amandes, du sucre "
             "et des œufs avec du zeste de citron, dense et humide, décoré au sucre glace de la "
             "croix de l'ordre.",
        compo=[
            ("almond_flour", 250, "g", "base"),
            ("sugars_granulated", 200, "g", "sweetener"),
            ("egg_raw", 200, "g", "binder"),
            ("lemon_peel_raw", 8, "g", "aroma"),
            ("cinnamon", 2, "g", "spice"),
        ],
        steps=[
            "Battre 200 g d'œufs avec 180 g de sucre 5 minutes, jusqu'à ce que le mélange double de "
            "volume.",
            "Ajouter 8 g de zeste de citron et 2 g de cannelle.",
            "Incorporer 250 g de poudre d'amandes à la maryse, sans travailler la masse.",
            "Verser dans un moule de 22 cm chemisé de papier cuisson.",
            "Enfourner 35 minutes à 175 °C : le dessus doit être doré et le centre encore souple.",
            "Laisser refroidir complètement, puis saupoudrer du reste de sucre glacé à travers un "
            "pochoir en forme de croix.",
        ],
    ),
    recipe(
        rid="dessert_sticky_toffee_pudding_39c7a2",
        fr="Sticky toffee pudding, gâteau anglais aux dattes",
        en="Sticky Toffee Pudding",
        original="Sticky toffee pudding",
        cuisine="british", country="united_kingdom", region="angleterre",
        dish="dessert", servings=8, prep=20, cook=40,
        texture=("moelleux", "sirupeux"), taste=("sucré", "caramel"),
        technique=("bake",), allow_similar=("sticky",),
        desc="Gâteau anglais très moelleux aux dattes fondues, noyé d'une sauce caramel au beurre et "
             "à la crème versée brûlante, puis repassé quelques minutes sous le gril.",
        compo=[
            ("date_with_skin_dried", 200, "g", "fruit"),
            ("wheat_flour_t55", 180, "g", "base"),
            ("brown_sugar", 150, "g", "sweetener"),
            ("butter_sup80pct", 100, "g", "fat"),
            ("egg_raw", 100, "g", "binder"),
            ("cream_heavy_refrigerated_30pct", 150, "ml", "dairy"),
            ("baking_powder", 6, "g", "ingredient"),
            ("water", 250, "ml", "liquid"),
        ],
        steps=[
            "Couvrir 200 g de dattes dénoyautées de 250 ml d'eau bouillante et laisser gonfler "
            "10 minutes, puis les écraser à la fourchette.",
            "Battre 60 g de beurre avec 80 g de sucre roux, ajouter 100 g d'œufs puis 180 g de "
            "farine et 6 g de poudre à lever.",
            "Incorporer la purée de dattes avec son eau : la pâte est très liquide, c'est normal.",
            "Verser dans un moule beurré et enfourner 35 minutes à 180 °C.",
            "Pendant ce temps, cuire le reste du beurre, 70 g de sucre roux et 150 ml de crème "
            "5 minutes jusqu'à obtenir une sauce caramel nappante.",
            "Percer le gâteau chaud et verser la moitié de la sauce, puis passer 3 minutes sous le "
            "gril.",
            "Servir chaud avec le reste de sauce caramel.",
        ],
    ),
    recipe(
        rid="dessert_cendol_8f2a45",
        fr="Cendol, dessert glacé malaisien au lait de coco",
        en="Cendol, Malaysian Coconut Ice Dessert",
        original="Cendol",
        cuisine="malaysian", country="malaysia", region="penang",
        dish="dessert", prep=25, rest=60, cook=15,
        texture=("gélatineux", "glacé"), taste=("sucré", "lacté"),
        technique=("simmer",), difficulty="medium",
        desc="Dessert de rue malaisien : des vermicelles verts de farine de riz poussés au tamis "
             "dans l'eau glacée, servis sur de la glace pilée avec du lait de coco salé et du sirop "
             "de sucre de palme.",
        compo=[
            ("rice_flour", 80, "g", "base"),
            ("cornstarch_flour", 20, "g", "thickener"),
            ("coconut_milk_plant", 500, "ml", "dairy_alt"),
            ("brown_sugar", 100, "g", "sweetener"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
            ("water", 700, "ml", "liquid"),
        ],
        steps=[
            "Délayer 80 g de farine de riz et 20 g de fécule dans 500 ml d'eau et cuire à feu moyen "
            "en fouettant, 6 minutes, jusqu'à obtenir une pâte épaisse et translucide.",
            "Passer la pâte chaude à travers une passoire à gros trous au-dessus d'un saladier d'eau "
            "glacée : les vermicelles se forment et se raffermissent.",
            "Les laisser 60 minutes dans l'eau froide, puis les égoutter.",
            "Cuire 100 g de sucre de palme (ou sucre roux) avec 200 ml d'eau 8 minutes pour obtenir "
            "un sirop épais, et le laisser refroidir.",
            "Saler 500 ml de lait de coco avec 1 g de sel.",
            "Dresser dans des verres : glace pilée, vermicelles, lait de coco salé et sirop versé en "
            "dernier.",
        ],
    ),
    recipe(
        rid="dessert_tangyuan_sesame_c50b87",
        fr="Tangyuan au sésame noir, boulettes chinoises en bouillon sucré",
        en="Black Sesame Tangyuan in Sweet Ginger Broth",
        original="Tangyuan",
        cuisine="chinese", country="china", region="jiangnan",
        dish="dessert", servings=6, prep=30, cook=15,
        texture=("élastique", "coulant"), taste=("sucré", "grillé"),
        technique=("boil",), difficulty="medium",
        desc="Boulettes de farine de riz gluant à la garniture coulante de sésame noir, pochées puis "
             "servies dans un bouillon léger au gingembre : la fête des lanternes en six bouchées.",
        compo=[
            ("white_glutinous_rice_flour", 200, "g", "base"),
            ("black_sesame", 80, "g", "nut"),
            ("sugars_granulated", 80, "g", "sweetener"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("ginger_raw_root_fresh", 20, "g", "aromatic"),
            ("water", 900, "ml", "liquid"),
        ],
        steps=[
            "Griller 80 g de graines de sésame noir 3 minutes à sec, puis les broyer avec 50 g de "
            "sucre et 40 g de beurre mou jusqu'à obtenir une pâte.",
            "Former douze petites billes de garniture et les raffermir 15 minutes au froid.",
            "Mélanger 200 g de farine de riz gluant avec 170 ml d'eau chaude pour obtenir une pâte "
            "souple et non collante.",
            "Diviser en douze, aplatir chaque part, y enfermer une bille de sésame et rouler en "
            "boule bien lisse.",
            "Faire frémir 700 ml d'eau avec 20 g de gingembre en lamelles et le reste du sucre.",
            "Pocher les boulettes 5 minutes : elles sont cuites lorsqu'elles remontent à la "
            "surface ; servir deux par bol avec le bouillon.",
        ],
    ),
    recipe(
        rid="brkf_baghrir_1d63c8",
        fr="Baghrir, crêpes marocaines aux mille trous",
        en="Baghrir, Moroccan Thousand-Hole Pancakes",
        original="Baghrir",
        cuisine="moroccan", country="morocco", region="marrakech",
        dish="breakfast", servings=6, prep=15, rest=40, cook=20,
        texture=("spongieux", "alvéolé"), taste=("doux", "beurré"),
        technique=("griddle",),
        desc="Crêpes de semoule fine cuites d'un seul côté : la levure forme des milliers de trous "
             "en surface, qui boivent le beurre fondu et le sirop au moment de servir.",
        compo=[
            ("durum_wheat_semolina", 250, "g", "base"),
            ("wheat_flour_t55", 50, "g", "base"),
            ("bakers_yeast_dehydrated", 6, "g", "ferment"),
            ("sugars_granulated", 40, "g", "sweetener"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("water", 650, "ml", "liquid"),
        ],
        steps=[
            "Mixer 250 g de semoule fine, 50 g de farine, 6 g de levure, 10 g de sucre, 3 g de sel "
            "et 600 ml d'eau tiède 2 minutes : la pâte doit être très liquide.",
            "Laisser reposer 40 minutes à couvert, jusqu'à ce que la surface mousse.",
            "Chauffer une poêle antiadhésive à feu moyen, sans matière grasse.",
            "Verser une louche de pâte sans l'étaler et cuire 2 minutes : les trous apparaissent et "
            "la surface sèche ; ne pas retourner.",
            "Empiler les baghrir sur une assiette en les séparant, pour qu'ils ne collent pas.",
            "Faire fondre 40 g de beurre avec 30 g de sucre et en arroser les crêpes avant de "
            "servir.",
        ],
    ),
    recipe(
        rid="brkf_full_breakfast_vegetarien_6e05b3",
        fr="Full breakfast végétarien, assiette anglaise du matin",
        en="Vegetarian Full Breakfast",
        original="Full English breakfast",
        cuisine="british", country="united_kingdom", region="angleterre",
        dish="breakfast", prep=15, cook=25,
        texture=("fondant", "croustillant"), taste=("umami", "salé"),
        technique=("fry",), allow_similar=("breakfast",),
        desc="L'assiette anglaise complète sans viande : haricots blancs à la tomate, champignons et "
             "tomates poêlés, œufs au plat et pain grillé beurré, tout servi en même temps et très "
             "chaud.",
        compo=[
            ("egg_raw", 200, "g", "animal_protein"),
            ("white_bean_canned", 400, "g", "plant_protein", "cooked"),
            ("button_mushroom_raw", 200, "g", "vegetable"),
            ("tomato_raw_ripe", 200, "g", "vegetable"),
            ("bread_white_commercial", 160, "g", "base"),
            ("tomato_paste_unsalted_canned", 30, "g", "condiment"),
            ("brown_sugar", 10, "g", "balance"),
            ("base_worcestershire_vegan_5f26ec", 10, "ml", "condiment"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("sunflower_oil_plant", 20, "ml", "fat_cooking"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 3, "g", "spice"),
        ],
        steps=[
            "Chauffer 400 g de haricots blancs égouttés avec 30 g de concentré de tomate, 10 g de "
            "sucre roux, 10 ml de sauce worcestershire végane et 100 ml d'eau, 10 minutes à feu "
            "doux.",
            "Couper 200 g de champignons en deux et 200 g de tomates en moitiés, les poêler dans "
            "20 ml d'huile 8 minutes, face coupée en dessous d'abord.",
            "Assaisonner les légumes de 2 g de sel et 2 g de poivre et les réserver au chaud.",
            "Cuire 200 g d'œufs au plat dans 10 g de beurre, à feu doux, pour garder le jaune "
            "coulant.",
            "Griller 160 g de pain et le beurrer avec le reste du beurre.",
            "Dresser les quatre assiettes avec tous les éléments en même temps et servir sans "
            "attendre.",
        ],
    ),
    recipe(
        rid="brkf_kaya_toast_b0f739",
        fr="Kaya toast, pain grillé singapourien à la confiture de coco",
        en="Kaya Toast, Singaporean Coconut Jam Toast",
        original="Kaya toast",
        cuisine="singaporean", country="singapore", region="singapour",
        dish="breakfast", prep=15, cook=30,
        texture=("croustillant", "crémeux"), taste=("sucré", "lacté"),
        technique=("toast",), difficulty="medium",
        desc="Le petit-déjeuner des kopitiam : une confiture d'œufs et de lait de coco cuite au bain-"
             "marie, étalée avec une lame de beurre froid entre deux tranches de pain grillé très "
             "fin.",
        compo=[
            ("egg_raw", 150, "g", "binder"),
            ("coconut_milk_plant", 250, "ml", "dairy_alt"),
            ("sugars_granulated", 100, "g", "sweetener"),
            ("vanilla_extract", 3, "ml", "aroma"),
            ("bread_white_commercial", 200, "g", "base"),
            ("butter_sup80pct", 60, "g", "fat"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ],
        steps=[
            "Fouetter 150 g d'œufs avec 100 g de sucre et 1 g de sel, sans faire mousser.",
            "Ajouter 250 ml de lait de coco et 3 ml de vanille, puis passer le mélange au tamis.",
            "Cuire au bain-marie 25 minutes en remuant sans arrêt, jusqu'à ce que la kaya nappe la "
            "cuillère ; ne jamais laisser bouillir.",
            "Laisser refroidir : la confiture épaissit encore en refroidissant.",
            "Griller 200 g de pain en tranches fines jusqu'à ce qu'il soit cassant.",
            "Tartiner généreusement de kaya, ajouter deux fines lames de beurre froid (60 g au "
            "total) et refermer en sandwich avant de couper en doigts.",
        ],
    ),
    recipe(
        rid="brkf_pancakes_riz_banane_4a91f0",
        fr="Pancakes de farine de riz à la banane (sans gluten)",
        en="Gluten-Free Rice Flour Banana Pancakes",
        cuisine="international", country="international", region="world",
        dish="breakfast", prep=10, cook=15,
        texture=("moelleux",), taste=("sucré", "fruité"),
        technique=("griddle",), allow_similar=("farine", "gluten"),
        desc="Pancakes sans gluten à la farine de riz, sucrés par la banane écrasée : la pâte est "
             "plus fluide qu'avec du blé mais les pancakes restent moelleux et dorent bien.",
        compo=[
            ("rice_flour", 200, "g", "base"),
            ("banana_raw", 300, "g", "fruit"),
            ("egg_raw", 100, "g", "binder"),
            ("milk_liquid_pasteurized_3_5pct", 200, "ml", "dairy"),
            ("baking_powder", 6, "g", "ingredient"),
            ("sugars_granulated", 30, "g", "sweetener"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("cinnamon", 2, "g", "spice"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ],
        steps=[
            "Écraser 300 g de bananes à la fourchette en gardant quelques morceaux.",
            "Mélanger 200 g de farine de riz, 6 g de poudre à lever, 30 g de sucre, 2 g de cannelle "
            "et 2 g de sel.",
            "Ajouter 100 g d'œufs battus et 200 ml de lait, puis la purée de bananes.",
            "Laisser reposer 5 minutes : la farine de riz absorbe le liquide et la pâte épaissit.",
            "Cuire des pancakes de 10 cm dans un peu d'huile, 2 minutes par face à feu moyen.",
            "Servir chaud, empilés, avec du sirop d'érable ou du yaourt.",
        ],
    ),
    recipe(
        rid="entry_ceviche_champignons_93e2c7",
        fr="Ceviche de champignons au citron vert",
        en="Mushroom Ceviche with Lime",
        cuisine="peruvian", country="peru", region="lima",
        dish="starter", prep=20, rest=30,
        texture=("croquant", "frais"), taste=("acide", "piquant"),
        spice=3, kid_friendly=False,
        desc="Ceviche sans poisson : des champignons crus marinés dans un jus de citron vert très "
             "salé au piment, servis avec oignon rouge, maïs, avocat et beaucoup de coriandre.",
        compo=[
            ("button_mushroom_raw", 500, "g", "vegetable"),
            ("lime_raw_juice_fresh", 100, "ml", "acidity"),
            ("onion_raw", 100, "g", "aromatic"),
            ("coriander", 15, "g", "herb"),
            ("red_hot_chili_pepper_raw", 10, "g", "spice"),
            ("avocado_raw", 150, "g", "fruit"),
            ("sweet_corn_canned", 100, "g", "vegetable"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Émincer 500 g de champignons de Paris en fines lamelles et les mettre dans un saladier "
            "froid.",
            "Verser 100 ml de jus de citron vert et 4 g de sel, mélanger : les champignons rendent "
            "de l'eau et s'attendrissent.",
            "Ajouter 100 g d'oignon émincé très fin et 10 g de piment haché sans les graines.",
            "Laisser mariner 30 minutes au réfrigérateur, en mélangeant une fois.",
            "Au moment de servir, ajouter 150 g d'avocat en dés, 100 g de maïs égoutté, 15 g de "
            "coriandre et 30 ml d'huile d'olive.",
            "Servir très frais, avec le jus de marinade au fond de l'assiette.",
        ],
        raw=True,
    ),
    recipe(
        rid="side_salade_fenouil_cru_0b48e5",
        fr="Salade de fenouil cru aux olives noires et au citron",
        en="Raw Fennel Salad with Black Olives and Lemon",
        cuisine="italian", country="italy", region="sicile",
        dish="side", prep=15,
        texture=("croquant",), taste=("anisé", "acide"),
        allow_similar=("noires", "olives"),
        desc="Salade sicilienne d'hiver : le fenouil tranché à la mandoline reste très croquant, "
             "juste assaisonné de citron, d'huile d'olive et d'olives noires, avec beaucoup de "
             "persil.",
        compo=[
            ("fennel_raw", 500, "g", "vegetable"),
            ("black_olive_canned_in_brine", 60, "g", "condiment"),
            ("lemon_juice", 40, "ml", "acidity"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Parer 500 g de bulbes de fenouil et garder les pluches vertes.",
            "Trancher les bulbes à la mandoline à 2 mm et les plonger 5 minutes dans de l'eau "
            "glacée pour qu'ils raidissent.",
            "Les égoutter et les sécher soigneusement dans un linge.",
            "Fouetter 40 ml de jus de citron avec 40 ml d'huile d'olive, 3 g de sel et 2 g de "
            "poivre.",
            "Mélanger le fenouil, 60 g d'olives noires dénoyautées et la sauce.",
            "Parsemer de 15 g de persil et des pluches de fenouil, servir aussitôt.",
        ],
        raw=True,
    ),
    recipe(
        rid="side_chou_rouge_pomme_noix_5d7c19",
        fr="Chou rouge cru, pomme et noix à la crème de yaourt",
        en="Raw Red Cabbage Slaw with Apple and Walnuts",
        cuisine="german", country="germany", region="bade_wurtemberg",
        dish="side", prep=15,
        texture=("croquant",), taste=("acide", "doux"),
        desc="Salade d'hiver croquante : chou rouge finement émincé et massé au sel, pomme acidulée "
             "en julienne, cerneaux de noix et une sauce au yaourt moutardée.",
        compo=[
            ("red_cabbage_raw", 500, "g", "vegetable"),
            ("apple_raw", 200, "g", "fruit"),
            ("walnut_shelled_dried", 50, "g", "nut"),
            ("yogurt_fermented_plain", 100, "g", "dairy"),
            ("mustard", 15, "g", "condiment"),
            ("cider_vinegar_liquid", 30, "ml", "acidity"),
            ("sunflower_oil_plant", 20, "ml", "fat"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
        ],
        steps=[
            "Émincer 500 g de chou rouge très finement, le saler avec 3 g de sel et le masser "
            "2 minutes à la main : il assouplit et fonce.",
            "Ajouter 30 ml de vinaigre de cidre et laisser reposer 10 minutes.",
            "Couper 200 g de pomme en julienne, sans la peler.",
            "Fouetter 100 g de yaourt avec 15 g de moutarde, 20 ml d'huile et 2 g de poivre.",
            "Mélanger le chou essoré, la pomme et la sauce.",
            "Parsemer de 50 g de cerneaux de noix concassés au moment de servir pour garder le "
            "croquant.",
        ],
        raw=True,
    ),
    recipe(
        rid="side_oi_muchim_c71e34",
        fr="Oi muchim, salade coréenne de concombre au piment",
        en="Oi Muchim, Korean Spicy Cucumber Salad",
        original="Oi muchim",
        cuisine="korean", country="south_korea", region="seoul",
        dish="side", prep=15, rest=20,
        texture=("croquant",), taste=("piquant", "acide"),
        spice=3, kid_friendly=False,
        desc="Banchan express : concombres tranchés et dégorgés, assaisonnés de piment, d'ail, "
             "d'huile de sésame et de vinaigre, à manger dans l'heure tant qu'ils croquent.",
        compo=[
            ("cucumber_raw", 600, "g", "vegetable"),
            ("green_onion_raw", 60, "g", "aromatic"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("red_hot_chili_pepper_raw", 12, "g", "spice"),
            ("sesame_oil_plant", 15, "ml", "fat"),
            ("soy_sauce_tamari", 20, "ml", "condiment"),
            ("sugars_granulated", 8, "g", "balance"),
            ("sesame_seed_hulled_dried", 10, "g", "garnish"),
            ("cider_vinegar_liquid", 20, "ml", "acidity"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Trancher 600 g de concombres en rondelles de 5 mm, les saler avec 4 g de sel et laisser "
            "dégorger 20 minutes.",
            "Les rincer rapidement et les presser entre les mains pour retirer l'eau.",
            "Mélanger 12 g de piment haché, 10 g d'ail écrasé, 20 ml de tamari, 20 ml de vinaigre, "
            "8 g de sucre et 15 ml d'huile de sésame.",
            "Enrober les concombres de cette sauce en mélangeant à la main.",
            "Ajouter 60 g d'oignon vert ciselé et 10 g de graines de sésame grillées.",
            "Servir frais, en petites portions à côté du riz.",
        ],
        raw=True,
    ),
    recipe(
        rid="main_ghormeh_sabzi_e0a9d3",
        fr="Ghormeh sabzi aux haricots rouges, ragoût d'herbes iranien",
        en="Ghormeh Sabzi with Kidney Beans, Persian Herb Stew",
        original="Ghormeh sabzi",
        cuisine="persian", country="iran", region="teheran",
        dish="main", prep=30, rest=720, cook=95,
        texture=("fondant",), taste=("acide", "herbacé"),
        technique=("simmer",), difficulty="medium",
        desc="Le ragoût national iranien en version végétarienne : une masse d'herbes longuement "
             "revenues jusqu'à noircir, du fenugrec, des haricots rouges et beaucoup de jus de "
             "citron, servi sur du riz.",
        compo=[
            ("kidney_bean_dried", 150, "g", "plant_protein", "dried"),
            ("spinach", 400, "g", "vegetable"),
            ("parsley_fresh_herb", 100, "g", "herb"),
            ("coriander", 60, "g", "herb"),
            ("leeks", 100, "g", "aromatic"),
            ("fenugreek_spice_seed", 5, "g", "spice"),
            ("turmeric_powder", 4, "g", "spice"),
            ("onion_raw", 200, "g", "aromatic_base"),
            ("lime_raw_juice_fresh", 40, "ml", "acidity"),
            ("sunflower_oil_plant", 50, "ml", "fat_cooking"),
            ("white_rice_long_grain_seed_dried", 250, "g", "base", "dried"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 1200, "ml", "liquid"),
        ],
        steps=[
            "Faire tremper 150 g de haricots rouges 12 heures, puis les égoutter.",
            "Hacher finement 400 g d'épinards, 100 g de persil, 60 g de coriandre et 100 g de "
            "poireau.",
            "Faire revenir 200 g d'oignon dans 30 ml d'huile 8 minutes, ajouter 4 g de curcuma puis "
            "réserver.",
            "Faire revenir les herbes dans le reste d'huile 20 minutes à feu moyen, en remuant : "
            "elles doivent foncer presque jusqu'au noir et sentir le grillé.",
            "Réunir oignon, herbes, haricots, 5 g de fenugrec, 800 ml d'eau, 4 g de sel et 2 g de "
            "poivre, puis mijoter 75 minutes à couvert.",
            "Ajouter 40 ml de jus de citron vert et laisser réduire 10 minutes à découvert : la "
            "sauce doit être sombre et huileuse en surface.",
            "Cuire 250 g de riz dans 400 ml d'eau salée (1 g de sel) et servir le ghormeh sabzi "
            "dessus.",
        ],
    ),
    recipe(
        rid="main_sarson_ka_saag_2b76ae",
        fr="Sarson ka saag, purée de feuilles de moutarde du Pendjab",
        en="Sarson ka Saag, Punjabi Mustard Greens",
        original="Sarson ka saag",
        cuisine="indian", country="india", region="pendjab",
        dish="main", prep=20, cook=50,
        texture=("épais", "granuleux"), taste=("amer", "beurré"),
        technique=("simmer",), spice=2, kid_friendly=False,
        desc="Purée punjabie de feuilles de moutarde et d'épinards, liée à la semoule de maïs et "
             "finie au beurre : amère, épaisse, traditionnellement mangée avec une galette de maïs.",
        compo=[
            ("mustard_raw_leaf", 600, "g", "vegetable"),
            ("spinach", 300, "g", "vegetable"),
            ("cornmeal_whole_dried", 60, "g", "thickener"),
            ("ginger_raw_root_fresh", 20, "g", "aromatic"),
            ("garlic_raw", 15, "g", "aromatic"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("green_chili_pepper_spice_canned", 10, "g", "spice"),
            ("butter_sup80pct", 50, "g", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("water", 700, "ml", "liquid"),
        ],
        steps=[
            "Laver 600 g de feuilles de moutarde et 300 g d'épinards, retirer les tiges dures et les "
            "ciseler.",
            "Les cuire 30 minutes dans 700 ml d'eau avec 10 g de piment vert et 4 g de sel, à "
            "couvert.",
            "Écraser au presse-purée ou mixer par impulsions : la texture doit rester granuleuse.",
            "Verser 60 g de semoule de maïs en pluie et cuire 10 minutes en remuant, jusqu'à ce que "
            "la purée épaississe et se détache de la casserole.",
            "Faire fondre 50 g de beurre et y blondir 150 g d'oignon, 20 g de gingembre et 15 g "
            "d'ail, 8 minutes.",
            "Verser ce beurre aromatique sur le saag et mélanger à moitié, servir avec une galette "
            "de maïs.",
        ],
    ),
    recipe(
        rid="side_salade_wakame_sesame_6d2c81",
        fr="Salade de wakamé au sésame et au concombre",
        en="Wakame Salad with Sesame and Cucumber",
        original="Wakame sunomono",
        cuisine="japanese", country="japan", region="kansai",
        dish="side", prep=15, rest=15,
        texture=("glissant", "croquant"), taste=("umami", "acide"),
        desc="Petite salade japonaise sans cuisson : du wakamé simplement réhydraté, du concombre en "
             "fines rondelles et une sauce vinaigrée au sésame, servie très froide en début de "
             "repas.",
        compo=[
            ("wakame_dried", 25, "g", "vegetable", "dried"),
            ("cucumber_raw", 300, "g", "vegetable"),
            ("cider_vinegar_liquid", 30, "ml", "acidity"),
            ("soy_sauce_tamari", 20, "ml", "condiment"),
            ("sesame_oil_plant", 10, "ml", "fat"),
            ("sugars_granulated", 8, "g", "balance"),
            ("sesame_seed_hulled_dried", 10, "g", "garnish"),
            ("green_onion_raw", 40, "g", "aromatic"),
            ("water", 500, "ml", "liquid"),
        ],
        steps=[
            "Faire tremper 25 g de wakamé séché 10 minutes dans 500 ml d'eau froide : il gonfle "
            "jusqu'à quatre fois son volume.",
            "Égoutter le wakamé, presser l'excès d'eau et couper les tronçons trop longs.",
            "Trancher 300 g de concombre en rondelles très fines et les saler légèrement.",
            "Mélanger 30 ml de vinaigre de cidre, 20 ml de tamari, 8 g de sucre et 10 ml d'huile de "
            "sésame.",
            "Réunir wakamé, concombre et sauce, puis laisser reposer 15 minutes au frais.",
            "Parsemer de 10 g de graines de sésame grillées et de 40 g d'oignon vert, servir froid.",
        ],
        raw=True,
    ),
    recipe(
        rid="main_matoke_ougandais_b5e740",
        fr="Matoke, plantains verts mijotés à l'ougandaise",
        en="Matoke, Ugandan Stewed Green Plantains",
        original="Matoke",
        cuisine="ugandan", country="uganda", region="buganda",
        dish="main", prep=25, cook=45,
        texture=("fondant", "épais"), taste=("doux", "umami"),
        technique=("steam", "simmer"),
        desc="Plat quotidien du Buganda : des plantains verts pelés puis étuvés jusqu'à se défaire, "
             "servis dans une sauce d'arachide à la tomate et aux doliques, sans épices fortes.",
        compo=[
            ("plantain_banana_raw", 900, "g", "vegetable"),
            ("black_eyed_peas_cowpeas_boiled", 250, "g", "plant_protein", "cooked"),
            ("peanut_butter_natural_plant", 80, "g", "plant_protein"),
            ("tomato_raw_ripe", 300, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("curry_powder", 6, "g", "spice"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 2, "g", "spice"),
            ("water", 600, "ml", "liquid"),
        ],
        steps=[
            "Peler 900 g de plantains verts au couteau (ils collent : huiler les mains) et les couper "
            "en gros tronçons.",
            "Les ranger dans une casserole avec 300 ml d'eau et 2 g de sel, couvrir et étuver "
            "25 minutes jusqu'à ce qu'ils soient très tendres.",
            "Faire revenir 150 g d'oignon et 12 g d'ail dans 30 ml d'huile, 8 minutes, puis ajouter "
            "6 g de curry.",
            "Ajouter 300 g de tomates concassées et cuire 5 minutes.",
            "Délayer 80 g de pâte d'arachide dans 300 ml d'eau chaude et la verser dans la sauce avec "
            "250 g de doliques, 3 g de sel et 2 g de poivre ; mijoter 15 minutes.",
            "Écraser grossièrement les plantains à la cuillère et les napper de sauce, servir "
            "aussitôt.",
        ],
    ),
]
