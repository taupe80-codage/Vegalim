"""Variantes 10 : farofa, feijão tropeiro, gado-gado, briam, gözleme, humita, jeera rice."""

VARIANTS = {
    # ── Farofa : aux œufs / à la banane plantain vegan ──
    "main_farofa_bresilienne_29e38e": [
        ("title", "Farofa de ovo, farine de manioc grillée aux œufs"),
        ("desc", "L'accompagnement brésilien des haricots et des grillades : farine de manioc dorée au beurre "
                 "avec oignon, carotte râpée, œufs brouillés et persil."),
        ("dish", "side"),
        ("compo", [
            ("cassava_flour", 150, "g", "carbohydrate"),
            ("egg_raw", 110, "g", "protein"),
            ("yellow_onion_raw", 120, "g", "aromatic_base"),
            ("carrot_raw", 100, "g", "vegetable"),
            ("butter_sup80pct", 40, "g", "fat_cooking"),
            ("parsley_fresh_herb", 20, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire fondre 40 g de beurre et y faire revenir 120 g d'oignon émincé et 100 g de carotte râpée, 5 minutes.",
            "Ajouter 2 œufs battus (110 g) et les brouiller 1 minute.",
            "Verser 150 g de farine de manioc en pluie et la faire griller 6 à 8 minutes à feu moyen en remuant sans cesse, jusqu'à ce qu'elle soit blonde et sente la noisette.",
            "Saler avec 3 g de sel, ajouter 20 g de persil ciselé et servir.",
        ]),
        ("time", 10, 0, 15),
    ],
    "side_farofa_bresilienne_vegan_45d889": [
        ("title", "Farofa à la banane plantain et aux noix de cajou (vegan)"),
        ("desc", "Farofa de banana du Nordeste : farine de manioc grillée à l'huile avec oignon, banane plantain "
                 "mûre caramélisée et noix de cajou, parfumée à la coriandre."),
        ("compo", [
            ("cassava_flour", 150, "g", "carbohydrate"),
            ("plantain_banana_raw_ripe", 250, "g", "ingredient"),
            ("yellow_onion_raw", 100, "g", "aromatic_base"),
            ("cashew_nuts_grilled_unsalted", 30, "g", "garnish"),
            ("olive_oil_extra_virgin_plant", 35, "ml", "fat_cooking"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Couper 250 g de banane plantain mûre en dés et la dorer dans 15 ml d'huile d'olive, 5 minutes. Réserver.",
            "Faire revenir 100 g d'oignon émincé dans 20 ml d'huile, 4 minutes.",
            "Ajouter 150 g de farine de manioc et la griller 6 à 8 minutes en remuant, jusqu'à ce qu'elle soit blonde.",
            "Ajouter la banane, 30 g de noix de cajou concassées, 3 g de sel et 10 g de coriandre, puis servir.",
        ]),
        ("time", 10, 0, 18),
    ],

    # ── Feijão : tropeiro mineiro / tutu de feijão vegan ──
    "egg_feijo_tropeiro_bb31e4": [
        ("title", "Feijão tropeiro mineiro, œufs et chou kale"),
        ("desc", "Plat des muletiers du Minas Gerais : haricots pinto sautés avec farine de manioc, oignon, ail, "
                 "œufs brouillés et chou kale émincé très fin."),
        ("origin", {"region": "minas_gerais", "city": "belo_horizonte"}),
        ("compo", [
            ("pinto_bean_boiled", 350, "g", "plant_protein", "cooked"),
            ("cassava_flour", 120, "g", "carbohydrate"),
            ("egg_raw", 165, "g", "ingredient"),
            ("kale_raw", 150, "g", "vegetable"),
            ("yellow_onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire revenir 150 g d'oignon et 9 g d'ail hachés dans 30 ml d'huile d'olive, 5 minutes.",
            "Ajouter 3 œufs battus (165 g) et les brouiller 1 minute.",
            "Ajouter 350 g de haricots pinto égouttés et 3 g de sel, puis les faire sauter 3 minutes.",
            "Incorporer 120 g de farine de manioc petit à petit en remuant, jusqu'à ce que le mélange soit sableux.",
            "À part, sauter 150 g de chou kale émincé en fines lanières dans 10 ml d'huile, 2 minutes.",
            "Servir le tropeiro parsemé de 15 g de persil, avec le chou.",
        ]),
        ("time", 15, 0, 20),
    ],
    "side_feijo_tropeiro_vegan_ccc81d": [
        ("title", "Tutu de feijão, purée de haricots noirs à la farine de manioc (vegan)"),
        ("desc", "Spécialité du Minas Gerais : haricots noirs mixés avec leur bouillon, épaissis à la farine de "
                 "manioc, relevés d'ail et d'oignon, servis avec du chou kale sauté."),
        ("origin", {"region": "minas_gerais", "city": "belo_horizonte"}),
        ("compo", [
            ("black_bean_boiled", 400, "g", "plant_protein", "cooked"),
            ("cassava_flour", 60, "g", "carbohydrate"),
            ("onion_raw", 120, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("kale_raw", 150, "g", "vegetable"),
            ("bay_leaf", 1, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 35, "ml", "fat"),
            ("water", 300, "ml", "liquid"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Mixer 400 g de haricots noirs cuits avec 300 ml d'eau.",
            "Faire revenir 120 g d'oignon et 9 g d'ail hachés dans 25 ml d'huile d'olive, 5 minutes, ajouter la purée, 1 g de laurier et 3 g de sel, puis porter à frémissement.",
            "Verser 60 g de farine de manioc en pluie en remuant et cuire 5 minutes, jusqu'à obtenir une purée épaisse.",
            "Sauter 150 g de chou kale émincé avec 3 g d'ail dans 10 ml d'huile, 2 minutes.",
            "Servir le tutu parsemé de 15 g de persil, avec le chou.",
        ]),
        ("time", 15, 0, 20),
    ],

    # ── Gado-gado de Jakarta / pecel javanais vegan ──
    "protein_gadogado_indonesien_200c65": [
        ("title", "Gado-gado de Jakarta aux œufs et sauce cacahuète"),
        ("desc", "Salade tiède de Jakarta : pommes de terre, haricots verts et pousses de soja blanchis, "
                 "concombre, tofu doré et œufs durs, nappés d'une sauce cacahuète au citron vert."),
        ("compo", [
            ("potato_raw_flesh", 400, "g", "ingredient"),
            ("french_bean_raw", 250, "g", "vegetable"),
            ("mung_bean_sprouts_raw_seed_sprouted", 150, "g", "vegetable"),
            ("cucumber_raw_with_skin", 250, "g", "vegetable"),
            ("tofu_plain_pre_packaged", 300, "g", "protein"),
            ("egg_raw", 220, "g", "ingredient"),
            ("peanut_butter_plant_regular", 70, "g", "sauce"),
            ("soy_sauce_shoyu_reduced_sodium", 25, "ml", "condiment"),
            ("coconut_sugar", 10, "g", "sweetener"),
            ("garlic_raw", 3, "g", "aromatic"),
            ("chilli_pepper_raw", 4, "g", "spice"),
            ("lime_juice_fresh", 30, "ml", "fruit"),
            ("coconut_oil_plant", 25, "ml", "fat"),
            ("water", 120, "ml", "liquid"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Cuire 400 g de pommes de terre en cubes 15 minutes à l'eau salée avec 1 g de sel, puis 4 œufs (220 g) 9 minutes. Blanchir 250 g de haricots verts 5 minutes et 150 g de pousses de soja 30 secondes.",
            "Dorer 300 g de tofu en cubes dans 25 ml d'huile de coco, 6 minutes.",
            "Sauce : mélanger 70 g de beurre de cacahuète, 25 ml de sauce soja, 10 g de sucre de coco, 3 g d'ail râpé, 4 g de piment, 30 ml de jus de citron vert et 120 ml d'eau chaude jusqu'à ce qu'elle soit lisse.",
            "Disposer les légumes, 250 g de concombre en rondelles, le tofu et les œufs en quartiers.",
            "Napper de sauce cacahuète et servir tiède.",
        ]),
        ("time", 25, 0, 30),
    ],
    "salad_gadogado_indonesien_vegan_e4cd75": [
        ("title", "Pecel javanais, légumes blanchis et sauce cacahuète épicée (vegan)"),
        ("desc", "Le pecel de Java-Est : épinards, chou, haricots verts et pousses de soja blanchis, tempeh "
                 "grillé, sous une sauce cacahuète relevée de piment, combava et sucre de coco."),
        ("origin", {"region": "jawa_timur", "city": "madiun"}),
        ("compo", [
            ("spinach_raw_mature", 250, "g", "vegetable"),
            ("green_cabbage_raw", 200, "g", "vegetable"),
            ("french_bean_raw", 200, "g", "vegetable"),
            ("mung_bean_sprouts_raw_seed_sprouted", 150, "g", "vegetable"),
            ("tempeh_tempe_raw_fermented", 250, "g", "protein"),
            ("peanut_roasted_salted_dry", 100, "g", "sauce"),
            ("chilli_pepper_raw", 8, "g", "spice"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("kaffir_lime_leaf", 1, "g", "aromatic"),
            ("coconut_sugar", 15, "g", "sweetener"),
            ("tamarind", 15, "ml", "ingredient"),
            ("coconut_oil_plant", 25, "ml", "fat"),
            ("water", 150, "ml", "liquid"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
            ("base_fried_onion_217e6a", 20, "g", "garnish"),
        ]),
        ("steps", [
            "Sauce : mixer 100 g de cacahuètes grillées avec 8 g de piment, 6 g d'ail, 1 g de feuille de combava, 15 g de sucre de coco, 15 ml de tamarin, 1 g de sel et 150 ml d'eau chaude.",
            "Couper 250 g de tempeh en tranches et le dorer dans 25 ml d'huile de coco, 3 minutes par face.",
            "Blanchir séparément 200 g de haricots verts (4 minutes), 200 g de chou émincé (2 minutes), 250 g d'épinards (30 secondes) et 150 g de pousses de soja (30 secondes), puis les égoutter.",
            "Disposer les légumes et le tempeh, napper de sauce et parsemer de 20 g d'oignons frits.",
        ]),
        ("time", 25, 0, 20),
    ],

    # ── Briam : à la feta / vegan aux pois chiches ──
    "main_greek_briam_4091c5": [
        ("title", "Briam grec aux légumes rôtis et à la feta"),
        ("desc", "Le tian grec : pommes de terre, aubergines, courgettes et tomates rôtis longuement à l'huile "
                 "d'olive, à l'ail et à l'origan, servis avec de la feta émiettée."),
        ("compo", [
            ("eggplant_raw", 500, "g", "vegetable"),
            ("green_zucchini_squash_raw", 400, "g", "vegetable"),
            ("potato_raw_flesh", 500, "g", "ingredient"),
            ("tomato_raw_ripe", 400, "g", "fruit"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("olive_oil_plant", 50, "ml", "fat"),
            ("feta", 150, "g", "ingredient"),
            ("oregano_spice_dried", 2, "g", "herb"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Préchauffer le four à 190°C.",
            "Couper 500 g de pommes de terre, 500 g d'aubergines et 400 g de courgettes en morceaux, émincer 150 g d'oignon et hacher 9 g d'ail.",
            "Mélanger les légumes dans un plat avec 400 g de tomates concassées, 50 ml d'huile d'olive, 2 g d'origan, 2 g de sel et 1 g de poivre.",
            "Couvrir et cuire 40 minutes, puis découvrir et cuire encore 30 minutes, jusqu'à ce que les légumes soient fondants et dorés.",
            "Servir tiède, parsemé de 150 g de feta émiettée.",
        ]),
        ("time", 20, 0, 70),
    ],
    "main_greek_briam_vegan_3fb054": [
        ("title", "Briam aux pois chiches, citron et aneth (vegan)"),
        ("desc", "Briam végétal plus riche en protéines : légumes rôtis à la tomate et aux pois chiches, "
                 "terminés au citron, à l'aneth et à l'huile d'olive."),
        ("compo", [
            ("eggplant_raw", 500, "g", "vegetable"),
            ("green_zucchini_squash_raw", 400, "g", "vegetable"),
            ("potato_raw_flesh", 400, "g", "ingredient"),
            ("tomato_raw_ripe", 400, "g", "fruit"),
            ("chickpea_boiled", 240, "g", "plant_protein", "cooked"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("olive_oil_plant", 50, "ml", "fat"),
            ("lemon_juice", 20, "ml", "condiment"),
            ("dill_weed_fresh_herb_leaf", 10, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Préchauffer le four à 190°C.",
            "Couper 400 g de pommes de terre, 500 g d'aubergines et 400 g de courgettes en morceaux, émincer 150 g d'oignon et hacher 12 g d'ail.",
            "Mélanger les légumes dans un plat avec 400 g de tomates concassées, 240 g de pois chiches, 50 ml d'huile d'olive et 3 g de sel.",
            "Couvrir et cuire 40 minutes, puis découvrir et cuire encore 30 minutes.",
            "Arroser de 20 ml de jus de citron et parsemer de 10 g d'aneth ciselé avant de servir.",
        ]),
        ("time", 20, 0, 70),
    ],

    # ── Gözleme : épinards-feta / pommes de terre épicées vegan ──
    "main_gozleme_aux_epinards_66eccf": [
        ("title", "Gözleme anatolien aux épinards et à la feta"),
        ("desc", "Galette turque à la pâte fine étirée au rouleau, farcie d'épinards, d'oignon et de fromage "
                 "blanc saumuré, cuite sur une plaque (sac) et badigeonnée d'huile."),
        ("origin", {"cuisine": "turkish", "country": "turkey", "region": "anatolie", "city": ""}),
    ],
    "snack_gozleme_aux_epinards_vega_6ff07b": [
        ("title", "Gözleme aux pommes de terre épicées et au persil (vegan)"),
        ("desc", "Patatesli gözleme : pâte fine sans produit laitier, farcie de pommes de terre écrasées avec "
                 "oignon, piment pul biber, persil et menthe, dorée à la poêle."),
        ("origin", {"cuisine": "turkish", "country": "turkey", "region": "anatolie", "city": ""}),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 250, "g", "carbohydrate"),
            ("water", 150, "ml", "liquid"),
            ("potato_raw_flesh", 400, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("red_hot_chili_pepper_spice_dried", 2, "g", "spice"),
            ("paprika", 2, "g", "spice"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("mint", 3, "g", "herb"),
            ("olive_oil_extra_virgin_plant", 35, "ml", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ]),
        ("steps", [
            "Pétrir 250 g de farine avec 150 ml d'eau tiède, 10 ml d'huile d'olive et 2 g de sel, puis laisser reposer 30 minutes.",
            "Cuire 400 g de pommes de terre à l'eau 20 minutes et les écraser. Faire revenir 100 g d'oignon haché dans 10 ml d'huile, puis mélanger aux pommes de terre avec 2 g de pul biber, 2 g de paprika, 15 g de persil, 3 g de menthe et 2 g de sel.",
            "Diviser la pâte en 5, étaler chaque pâton très finement en rectangle.",
            "Étaler la farce sur une moitié, replier et souder les bords.",
            "Cuire à sec dans une grande poêle, 3 minutes de chaque côté, en badigeonnant de 15 ml d'huile au total. Couper en parts.",
        ]),
        ("time", 25, 30, 25),
    ],

    # ── Humita : péruvienne en feuilles de maïs / en olla argentine vegan ──
    "main_humita_andine_fe7789": [
        ("title", "Humitas péruviennes au fromage frais, en feuilles de maïs"),
        ("desc", "Humitas salées des Andes péruviennes : maïs frais râpé mêlé d'oignon revenu, piment doux et "
                 "fromage frais, enveloppé dans des feuilles de maïs et cuit à la vapeur."),
        ("compo", [
            ("sweet_corn_raw_fresh", 500, "g", "vegetable"),
            ("yellow_onion_raw", 100, "g", "aromatic_base"),
            ("red_bell_pepper_raw", 80, "g", "vegetable"),
            ("queso_fresco_block_cow", 120, "g", "ingredient"),
            ("butter_sup80pct", 25, "g", "fat"),
            ("milk_liquid_uht_3_5pct", 50, "ml", "ingredient"),
            ("corn_husk", 40, "g", "ingredient"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire tremper 40 g de feuilles de maïs séchées 30 minutes dans l'eau chaude.",
            "Mixer grossièrement 500 g de grains de maïs avec 50 ml de lait.",
            "Faire revenir 100 g d'oignon et 80 g de poivron en petits dés dans 25 g de beurre, 5 minutes, puis mélanger au maïs avec 3 g de sel.",
            "Déposer 2 cuillerées de pâte sur chaque feuille, ajouter un morceau de fromage frais (120 g en tout), puis replier en paquet.",
            "Cuire à la vapeur 40 minutes. Servir chaud.",
        ]),
        ("time", 30, 30, 40),
    ],
    "snack_humita_andine_vegan_1f09bf": [
        ("title", "Humita en olla argentine, maïs et courge (vegan)"),
        ("desc", "La humita en olla du nord-ouest argentin : maïs frais et courge butternut cuits en crème "
                 "épaisse avec oignon, poivron et paprika, adoucie au lait d'avoine, servie à la cuillère."),
        ("origin", {"cuisine": "argentinian", "country": "argentina", "region": "tucuman", "city": ""}),
        ("dish", "main"),
        ("compo", [
            ("sweet_corn_raw_fresh", 500, "g", "vegetable"),
            ("butternut_squash_raw_skinless", 300, "g", "vegetable"),
            ("onion_raw", 120, "g", "aromatic_base"),
            ("red_bell_pepper_raw", 100, "g", "vegetable"),
            ("oat_milk_refrigerated_plain_plant", 200, "ml", "ingredient"),
            ("nutritional_yeast_flakes", 15, "g", "ingredient"),
            ("paprika", 2, "g", "spice"),
            ("cumin_spice_seed", 1, "g", "spice"),
            ("olive_oil_extra_virgin_plant", 25, "ml", "fat"),
            ("basil_fresh_herb", 5, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire revenir 120 g d'oignon et 100 g de poivron en dés dans 25 ml d'huile d'olive, 6 minutes, avec 2 g de paprika et 1 g de cumin.",
            "Ajouter 300 g de courge en petits dés et 100 ml de lait d'avoine, couvrir et cuire 12 minutes.",
            "Mixer grossièrement 500 g de grains de maïs avec 100 ml de lait d'avoine, puis les ajouter à la casserole.",
            "Cuire 15 minutes à feu doux en remuant, jusqu'à ce que la humita épaississe. Saler avec 3 g de sel et ajouter 15 g de levure nutritionnelle.",
            "Servir parsemé de 5 g de basilic ciselé.",
        ]),
        ("time", 20, 0, 35),
    ],

    # ── Jeera rice : au beurre / jeera matar pulao vegan ──
    "rice_jeera_rice_a4633c": [
        ("title", "Jeera rice au beurre et aux graines de cumin"),
        ("desc", "Le riz basmati parfumé du nord de l'Inde : graines de cumin crépitées dans le beurre, riz "
                 "nacré puis cuit par absorption, grains bien séparés."),
    ],
    "side_jeera_rice_vegan_694fd1": [
        ("title", "Pulao aux petits pois et au cumin (vegan)"),
        ("desc", "Jeera matar pulao : riz basmati cuit avec cumin, laurier, cannelle et petits pois dans l'huile, "
                 "parsemé de coriandre fraîche."),
        ("compo", [
            ("white_rice_raw_seed_unenriched", 300, "g", "carbohydrate"),
            ("green_peas_raw", 150, "g", "vegetable"),
            ("onion_raw", 80, "g", "aromatic_base"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("bay_leaf", 1, "g", "aromatic"),
            ("cinnamon", 1, "g", "spice"),
            ("sunflower_oil_plant", 30, "ml", "fat_cooking"),
            ("water", 480, "ml", "liquid"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ]),
        ("steps", [
            "Rincer 300 g de riz basmati jusqu'à ce que l'eau soit claire, puis le laisser tremper 20 minutes et l'égoutter.",
            "Chauffer 30 ml d'huile, y faire crépiter 3 g de cumin avec 1 g de laurier et 1 g de cannelle, puis ajouter 80 g d'oignon émincé et le dorer 5 minutes.",
            "Ajouter le riz et 150 g de petits pois, puis remuer 1 minute.",
            "Verser 480 ml d'eau bouillante avec 4 g de sel, couvrir et cuire 12 minutes à feu très doux.",
            "Laisser reposer 5 minutes, égrener et parsemer de 10 g de coriandre.",
        ]),
        ("time", 10, 20, 20),
    ],
}
