"""Lot 38 : soupes (courge coco → ash reshteh vegan)."""

PATCHES = {
    "soup_courge_au_lait_de_coco_224d09": [
        ("qty", "garlic_raw", 10),
        ("qty", "soy_sauce_shoyu_reduced_sodium", 10),
        ("txt", "Faites revenir 2g d'ail", "Faites revenir 10g d'ail"),
        ("txt", "20ml de sauce de soja", "10ml de sauce de soja"),
        ("txt", " et de feuilles de citron vert pour la décoration", ""),
    ],
    # nimono (courge mijotée) : pas une soupe, pas de four
    "soup_courge_mijotee_japonaise_3852ae": [
        ("qty", "base_dashi_broth_a3a517", 400),
        ("qty", "soy_sauce_tamari", 30),
        ("txt", "Saisir la courge kabocha (600g) en morceaux de 4-5 cm, côté peau, pour favoriser une cuisson uniforme et révéler sa texture tendre.",
         "Couper la courge kabocha (600g) en morceaux de 4-5 cm, en gardant la peau."),
        ("txt", "dashi végétal (700ml), sauce soja (45ml)", "dashi végétal (400ml), sauce soja (30ml)"),
        ("txt", "et enfourner pendant 20 minutes à 180°C", "et cuire à feu doux pendant 20 minutes"),
        ("txt", "Réduire la sauce jusqu'à ce qu'elle atteigne une couleur dorée blonde et crépite légèrement, indiquant qu'elle est sirupeuse et prête à napper la courge.",
         "Retirer le couvercle et laisser réduire la sauce 5 minutes, jusqu'à ce qu'elle soit légèrement sirupeuse."),
        ("txt", "Assaisonner avec soin, puis servir chaud, en ajoutant éventuellement un peu de sauce soja pour donner un peu de saveur supplémentaire au plat, si désiré, dans des bols préchauffés.",
         "Servir chaud ou tiède, nappé de sauce."),
        ("time", 9, 0, 30),
    ],
    "soup_de_gundruk_a62723": [
        ("add", "water", 700, "ml", "liquid"),
        ("txt", "mijoter pendant 20 minutes à 180°C", "mijoter pendant 20 minutes à feu doux"),
    ],
    "soup_de_pois_casses_58fc34": [
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Assaisonner de 5g de sel", "Assaisonner de 2g de sel"),
        ("txt", "Servir chaud, dans des bols préchauffés, en accompagnant d'un filet", "Servir chaud, avec un filet"),
    ],
    # noix de muscade entière (5 g) retirée mais comptée ; piment absent
    "soup_de_potiron_caribeenne_a0fabd": [
        ("qty", "nutmeg_spice", 1),
        ("qty", "table_salt_unenriched", 2),
        ("add", "chilli_pepper_raw", 5, "g", "spice"),
        ("add", "coriander_raw_fresh_herb", 5, "g", "herb"),
        ("txt", "3g de thym frais et 5g de noix de muscade entière", "3g de thym frais, 1g de noix de muscade râpée et 5 g de piment antillais épépiné"),
        ("txt", "Retirer la noix de muscade et mixer la soupe", "Mixer la soupe"),
        ("txt", "assaisonner avec 5g de sel", "assaisonner avec 2g de sel"),
        ("txt", " La soupe doit être servie dans un bol chaud et invitante.", ""),
    ],
    # quinoa « blanchi » puis oublié ; 600 g de pommes de terre + 250 g de quinoa
    "soup_de_quinoa_2df148": [
        ("qty", "quinoa_raw_dried", 100),
        ("qty", "potato_raw_flesh", 300),
        ("qty", "water", 1200),
        ("qty", "vegetable_stock_dried", 12),
        ("qty", "table_salt_unenriched", 2),
        ("add", "black_pepper_spice", 1, "g", "spice"),
        ("txt", "Rincer 250g de quinoa et le blanchir pendant 5 minutes à feu moyen, jusqu'à ce que les grains soient légèrement gonflés.",
         "Rincer 100g de quinoa à l'eau froide et l'égoutter."),
        ("txt", "et 600g de pomme de terre en dés", "et 300g de pomme de terre en dés"),
        ("txt", "Incorporer 750ml de bouillon de légumes chaud", "Incorporer le quinoa et 1,2 L de bouillon de légumes chaud"),
        ("txt", "Assaisonner avec 5g de sel et servir chaud.", "Assaisonner avec 2g de sel et du poivre."),
        ("step-", "Déguster et ajuster l'assaisonnement si nécessaire"),
    ],
    "soup_gaspacho_provencal_f69228": [
        ("qty", "olive_oil_plant", 30),
        ("add", "red_wine_vinegar_liquid", 15, "ml", "condiment"),
        ("txt", "puis assaisonner généreusement de sel et de poivre", "puis assaisonner avec 5 g de sel, 15 ml de vinaigre de vin et du poivre"),
        ("txt", "en ajoutant un filet d'huile d'olive", "en ajoutant 30 ml d'huile d'olive"),
        ("step-", "Rectifier l'assaisonnement si nécessaire"),
    ],
    "soup_gazpacho_classic_v2_x9k3m1": [
        ("ing", "white_vinegar_liquid_distilled", "red_wine_vinegar_liquid"),
        ("add", "white_bread_baguette", 50, "g", "ingredient"),
        ("txt", "le vinaigre de fruit (ou de légume)", "le vinaigre de vin"),
        ("txt", " Émulsionnez avec l'huile d'olive en filet.", ""),
        ("txt", "Ajoutez les tomates, le concombre, le poivron et mixez", "Ajoutez les tomates, le concombre, le poivron et 50 g de pain rassis trempé, puis mixez"),
        ("flag", "gluten_free", False),  # pain rassis
    ],
    # les haricots n'étaient jamais ajoutés
    "soup_haricots_au_lait_de_coco_207254": [
        ("qty", "garlic_raw", 10),
        ("qty", "coconut_milk_plant", 250),
        ("txt", "Faites revenir 2 g d'ail", "Faites revenir 10 g d'ail"),
        ("txt", "Incorporez 200 g de tofu ferme égoutté et coupé en dés", "Incorporez 300 g de haricots blancs cuits, 200 g de tofu ferme égoutté et coupé en dés"),
        ("txt", "Versez 400 ml de lait de coco", "Versez 250 ml de lait de coco"),
        ("txt", " Vérifiez que la lame ressort sèche après avoir trempé un morceau de pain dans la sauce.", ""),
    ],
    "soup_harira_classic_v3_p9x4k2": [
        ("qty", "vegetable_stock_dried", 12),
        ("add", "tomato_paste_unsalted_canned", 20, "g", "ingredient"),
        ("add", "lemon_juice", 15, "ml", "condiment"),
        ("txt", "et le concentré de tomate végan", "et 20 g de concentré de tomate"),
        ("txt", "dans un peu d'eau froide végane", "dans un peu d'eau froide"),
        ("txt", "en ajoutant un filet de citron", "en ajoutant 15 ml de jus de citron"),
        ('txt', "Faire suer les 120g d'oignon", "Faire suer les 120g d'oignon et 80 g de céleri émincé"),
    ],
    # 2 kg de légumes, eau en plus du bouillon, shiitakés enfournés, bouillon « réduit sirupeux »
    "soup_hot_pot_e7fc15": [
        ("qty", "bok_choy_raw", 300),
        ("qty", "napa_cabbage_raw", 300),
        ("qty", "red_bell_pepper_raw", 150),
        ("qty", "soy_sauce_shoyu_reduced_sodium", 30),
        ("steps", [
            "Porter 1 L de bouillon mala à frémissement dans un caquelon.",
            "Couper le pak-choï, la carotte, le poivron rouge et le chou napa en morceaux, et le tofu ferme en cubes.",
            "Émincer les shiitakés et 9 g d'ail, puis les ajouter au bouillon.",
            "Réhydrater les vermicelles de riz 5 minutes à l'eau chaude, puis les égoutter.",
            "À table, plonger les ingrédients dans le bouillon frémissant et les cuire 2 à 5 minutes selon leur taille, puis les repêcher avec les vermicelles.",
            "Servir avec une sauce trempette : 30 ml de sauce soja, 45 ml de tahini, 15 g de piment haché et 15 g de graines de sésame.",
        ]),
    ],
    "soup_minestrone_9116a2": [
        ("txt", "Ajouter 3 gousses d'ail émincé", "Ajouter 9 g d'ail émincé"),
        ("txt", "100g de petites pâtes végétales", "100g de petites pâtes"),
        ("txt", "Rectifier le sel et le poivre, ajouter des herbes fraîches comme le basilic ou le thym, et servir sans attendre : la chaleur est essentielle pour apprécier les saveurs et les textures de cette soupe minestrone végétarien.",
         "Poivrer et servir aussitôt."),
        ("step-", "Pour une variante, ajouter des légumes supplémentaires"),
    ],
    # 320 g de pâtes dans une soupe
    "soup_minestrone_italienne_f98e05": [
        ("qty", "pasta_raw_dried", 100),
        ("qty", "garlic_raw", 10),
        ("qty", "vegetable_stock_dried", 12),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Ajouter 20g d'ail émincé", "Ajouter 10g d'ail émincé"),
        ("txt", "Incorporer 320g de pâtes de blé et 300g de haricots rouges égouttés. Verser 1,2L de bouillon végétal chaud et porter à ébullition",
         "Incorporer 300g de haricots rouges égouttés et verser 1,2L de bouillon végétal chaud. Porter à ébullition"),
        ("txt", "Ajouter 5g de sel de mer et poivrer selon le goût. Laisser cuire encore 5 minutes", "Ajouter 100 g de petites pâtes, 2 g de sel et du poivre. Laisser cuire encore 10 minutes"),
        ("step-", "Rectifier l'assaisonnement si nécessaire."),
        ("step-", "Ajouter un filet d'huile d'olive extra vierge"),
        ("step-", "Pour une touche finale, ajouter des herbes fraîches"),
        ("txt", "Servir chaud, dans des bols préchauffés, avec un peu de crème fraîche si désiré, pour une texture crémeuse et onctueuse.", "Servir chaud."),
    ],
    # « odeur de noix de coco », huile de coco chaude, wakamé utilisé deux fois
    "soup_miso_k2d1p1": [
        ("steps", [
            "Porter 800 ml d'eau à frémissement (ou utiliser un dashi végétal).",
            "Réhydrater 5 g de wakamé 5 minutes dans l'eau froide, puis l'égoutter. Couper 150 g de tofu ferme en cubes de 2 cm et ciseler 10 g d'oignon vert.",
            "Ajouter le tofu et le wakamé dans l'eau frémissante et chauffer 2 minutes.",
            "Hors du feu, délayer 40 g de miso dans une louche de bouillon, puis le verser dans la casserole sans refaire bouillir.",
            "Servir aussitôt, parsemé d'oignon vert.",
        ]),
    ],
    "soup_persian_ash_reshteh_vegan_968f7d": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 30),
        ("qty", "olive_oil_plant", 45),
        ("add", "water", 1500, "ml", "liquid"),
        ("txt", "couvrir d'eau et laisser mijoter 20 min", "couvrir de 1,5 L d'eau et laisser mijoter 20 min"),
        ("step-", "Vérifier que les légumineuses et les nouilles sont tendres"),
        ('txt', "Ajouter l'ail, le curcuma et les épices", "Ajouter l'ail, le curcuma et 5 g de piment séché"),
        ('txt', 'puis servir chaud, accompagné de pain ou de crackers', 'puis servir chaud, parsemé de 20 g de menthe ciselée'),
    ],
}
