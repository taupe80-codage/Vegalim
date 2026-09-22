"""Variantes 7 : shopska, quesadillas, galettes de sarrasin, pad thaï / see ew / krapow."""


def _quesadilla(filling, cheese, oil):
    return [
        f"Préparer la garniture : {filling}",
        f"Chauffer une poêle à feu moyen et la badigeonner d'un peu des {oil} restants.",
        f"Poser une tortilla, garnir une moitié d'un quart de la garniture et de {cheese}, puis replier en demi-lune.",
        "Cuire 2 à 3 minutes de chaque côté, jusqu'à ce que la tortilla soit dorée et la garniture chaude. Répéter avec les autres tortillas.",
        "Couper en triangles et servir aussitôt.",
    ]


VARIANTS = {
    # ── Shopska : de Sofia au sirene / ovcharska du berger / vegan tofu à l'aneth / vegan haricots et poivrons grillés ──
    "main_bulgarian_shopska_salad_d473eb": [
        ("title", "Salade shopska de Sofia au sirene"),
        ("desc", "La salade nationale bulgare : tomates, concombre, poivrons grillés et oignon rouge, "
                 "assaisonnés simplement, entièrement recouverts de sirene (fromage de brebis saumuré) râpé."),
        ("compo", [
            ("tomato_raw_ripe", 350, "g", "fruit"),
            ("cucumber_raw_with_skin", 300, "g", "vegetable"),
            ("red_bell_pepper_raw", 300, "g", "vegetable"),
            ("red_onion_raw", 80, "g", "vegetable"),
            ("feta", 150, "g", "ingredient"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("sunflower_oil_plant", 30, "ml", "fat"),
            ("red_wine_vinegar_liquid", 15, "ml", "ingredient"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Griller 300 g de poivrons sous le gril du four, 15 minutes, en les retournant, puis les enfermer 10 minutes dans un saladier couvert, les peler et les couper en lanières.",
            "Couper 350 g de tomates et 300 g de concombre en dés, émincer finement 80 g d'oignon rouge et ciseler 10 g de persil.",
            "Mélanger les légumes avec 30 ml d'huile de tournesol, 15 ml de vinaigre de vin et 1 g de sel.",
            "Répartir dans les assiettes et couvrir entièrement de 150 g de sirene (ou feta) râpé finement.",
        ]),
        ("time", 20, 10, 15),
    ],
    "salad_shopska_04dd73": [
        ("title", "Salade ovcharska du berger, œufs et champignons"),
        ("desc", "Cousine plus copieuse de la shopska : tomates, concombre et poivron, champignons sautés, "
                 "œufs durs et fromage de brebis, un vrai plat complet des tavernes bulgares."),
        ("compo", [
            ("tomato_raw_ripe", 300, "g", "fruit"),
            ("cucumber_raw_with_skin", 250, "g", "vegetable"),
            ("red_bell_pepper_raw", 200, "g", "vegetable"),
            ("onion_raw", 80, "g", "aromatic_base"),
            ("button_mushroom_raw", 250, "g", "vegetable"),
            ("egg_raw", 220, "g", "protein"),
            ("feta", 120, "g", "ingredient"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("red_wine_vinegar_liquid", 20, "ml", "fruit"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Cuire 4 œufs (220 g) 9 minutes à l'eau bouillante, les refroidir, les écaler et les couper en quartiers.",
            "Faire sauter 250 g de champignons émincés dans 10 ml d'huile d'olive, 6 minutes à feu vif, puis laisser tiédir.",
            "Couper 300 g de tomates, 250 g de concombre et 200 g de poivron en dés, émincer 80 g d'oignon.",
            "Mélanger les légumes et les champignons avec 30 ml d'huile d'olive, 20 ml de vinaigre de vin rouge et 1 g de sel.",
            "Dresser, disposer les œufs, puis couvrir de 120 g de fromage de brebis émietté et de 10 g de persil ciselé.",
        ]),
        ("time", 20, 0, 15),
    ],
    "salad_bulgarian_shopska_salad_v_adc716": [
        ("title", "Salade shopska au tofu mariné à l'aneth (vegan)"),
        ("desc", "Shopska végétale : les crudités classiques couvertes d'un tofu émietté mariné au citron, "
                 "à l'aneth et au sel, qui imite la fraîcheur acidulée du sirene."),
        ("compo", [
            ("tomato_raw_ripe", 300, "g", "fruit"),
            ("cucumber_raw_with_skin", 300, "g", "vegetable"),
            ("red_bell_pepper_raw", 250, "g", "vegetable"),
            ("red_onion_raw", 80, "g", "vegetable"),
            ("tofu_plain_pre_packaged", 250, "g", "ingredient"),
            ("lemon_juice", 20, "ml", "ingredient"),
            ("dill_weed_fresh_herb_leaf", 8, "g", "herb"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("white_vinegar_liquid_distilled", 15, "ml", "ingredient"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Émietter 250 g de tofu ferme et le mélanger avec 20 ml de jus de citron, 8 g d'aneth ciselé, 10 ml d'huile d'olive et 2 g de sel. Laisser mariner 20 minutes.",
            "Couper 300 g de tomates, 300 g de concombre et 250 g de poivron en dés, émincer 80 g d'oignon rouge.",
            "Assaisonner les légumes avec 30 ml d'huile d'olive, 15 ml de vinaigre, 1 g de sel et 1 g de poivre.",
            "Dresser et couvrir du tofu mariné.",
        ]),
        ("time", 20, 20, 0),
    ],
    "salad_shopska_vegan_001f9e": [
        ("title", "Salade shopska aux haricots blancs et poivrons grillés (vegan)"),
        ("flag", "raw", False),
        ("desc", "Version plat complet et végétale : poivrons grillés, haricots blancs, tomates, concombre "
                 "et oignon, en vinaigrette au vin rouge et au persil."),
        ("compo", [
            ("tomato_raw_ripe", 300, "g", "fruit"),
            ("cucumber_raw_with_skin", 250, "g", "vegetable"),
            ("red_bell_pepper_raw", 300, "g", "vegetable"),
            ("onion_raw", 80, "g", "aromatic_base"),
            ("white_bean_boiled", 300, "g", "ingredient", "cooked"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("olive_oil_plant", 45, "ml", "fat"),
            ("red_wine_vinegar_liquid", 20, "ml", "fruit"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Griller 300 g de poivrons sous le gril du four, 15 minutes, les peler et les couper en lanières.",
            "Couper 300 g de tomates et 250 g de concombre en dés, émincer 80 g d'oignon et ciseler 15 g de persil.",
            "Rincer et égoutter 300 g de haricots blancs cuits.",
            "Mélanger le tout avec 45 ml d'huile d'olive, 20 ml de vinaigre de vin rouge et 3 g de sel, puis servir frais.",
        ]),
        ("time", 20, 0, 15),
    ],

    # ── Quesadillas : rajas au Chihuahua / champignons-chèvre / vegan haricots noirs / vegan patate douce-maïs ──
    "wrap_quesadillas_au_fromage_511e1a": [
        ("title", "Quesadillas de rajas au queso Chihuahua"),
        ("desc", "Quesadillas du nord du Mexique : lanières de poivrons grillés et de piment vert (rajas) revenues "
                 "avec l'oignon, et queso Chihuahua fondant."),
        ("origin", {"region": "chihuahua", "city": ""}),
        ("flag", "kid_friendly", False),
        ("compo", [
            ("base_tortilla_92c2a6", 320, "g", "ingredient"),
            ("queso_chihuahua_whole_cow", 150, "g", "ingredient"),
            ("red_bell_pepper_raw", 200, "g", "vegetable"),
            ("green_bell_pepper_raw", 150, "g", "vegetable"),
            ("chilli_pepper_raw", 10, "g", "spice"),
            ("yellow_onion_raw", 120, "g", "aromatic_base"),
            ("olive_oil_extra_virgin_plant", 35, "ml", "fat"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
            ("lime", None, "1/2", "serving_suggestion"),
        ]),
        ("steps", _quesadilla(
            "griller 200 g de poivron rouge et 150 g de poivron vert, les peler et les couper en lanières, puis les faire revenir 5 minutes avec 120 g d'oignon émincé et 10 g de piment vert dans 20 ml d'huile d'olive et 1 g de sel.",
            "150 g de queso Chihuahua râpé", "15 ml d'huile")),
        ("time", 20, 0, 25),
    ],
    "wrap_quesadillas_c8edf2": [
        ("title", "Quesadillas aux champignons et au chèvre frais, pico de gallo"),
        ("desc", "Quesadillas de Mexico garnies de champignons sautés à l'ail et au piment, de chèvre frais, "
                 "servies avec une pico de gallo à la tomate et à la coriandre."),
        ("compo", [
            ("base_tortilla_92c2a6", 320, "g", "ingredient"),
            ("button_mushroom_raw", 250, "g", "vegetable"),
            ("goat_cheese_fresh", 120, "g", "ingredient"),
            ("yellow_onion_raw", 120, "g", "aromatic_base"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("chilli_pepper_raw", 6, "g", "spice"),
            ("tomato_raw_ripe", 200, "g", "fruit"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("lime_juice_fresh", 10, "ml", "condiment"),
            ("olive_oil_extra_virgin_plant", 35, "ml", "fat"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ]),
        ("steps", [
            "Pico de gallo : mélanger 200 g de tomates en petits dés, 40 g d'oignon ciselé, 10 g de coriandre, 3 g de piment haché, 10 ml de jus de citron vert et 1 g de sel.",
        ] + _quesadilla(
            "faire sauter 250 g de champignons émincés avec 80 g d'oignon, 6 g d'ail et 3 g de piment dans 20 ml d'huile d'olive, 7 minutes, puis saler avec 1 g de sel.",
            "120 g de chèvre frais émietté", "15 ml d'huile")[:-1] + [
            "Couper en triangles et servir avec la pico de gallo.",
        ]),
        ("time", 20, 0, 25),
    ],
    "wrap_quesadillas_au_fromage_ve_9794c7": [
        ("title", "Quesadillas aux haricots noirs et cheddar végétal (vegan)"),
        ("desc", "Quesadillas vegan garnies de haricots noirs écrasés au cumin, poivrons et oignon revenus, "
                 "et de cheddar végétal maison qui fond à la cuisson."),
        ("compo", [
            ("base_tortilla_92c2a6", 320, "g", "ingredient"),
            ("black_bean_boiled", 240, "g", "protein", "cooked"),
            ("base_vegan_cheddar_024998", 120, "g", "ingredient"),
            ("red_bell_pepper_raw", 200, "g", "vegetable"),
            ("yellow_onion_raw", 120, "g", "aromatic_base"),
            ("cumin_spice_seed", 2, "g", "spice"),
            ("vegetable_oil_plant", 35, "ml", "fat"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ]),
        ("steps", _quesadilla(
            "faire revenir 120 g d'oignon et 200 g de poivron émincés dans 20 ml d'huile, 7 minutes, puis ajouter 240 g de haricots noirs, 2 g de cumin et 2 g de sel et les écraser grossièrement.",
            "120 g de cheddar végétal râpé", "15 ml d'huile")),
        ("time", 15, 0, 25),
    ],
    "wrap_quesadillas_vegan_f68baa": [
        ("title", "Quesadillas patate douce, maïs et cheddar végétal (vegan)"),
        ("desc", "Quesadillas végétales à la purée de patate douce rôtie au paprika, maïs doux, tomate et "
                 "cheddar végétal, dorées à la poêle."),
        ("compo", [
            ("base_tortilla_92c2a6", 320, "g", "ingredient"),
            ("sweet_potato_raw", 300, "g", "vegetable"),
            ("sweet_corn_canned", 150, "g", "vegetable"),
            ("base_vegan_cheddar_024998", 120, "g", "ingredient"),
            ("yellow_onion_raw", 100, "g", "aromatic_base"),
            ("tomato_raw_ripe", 150, "g", "fruit"),
            ("paprika", 2, "g", "spice"),
            ("olive_oil_extra_virgin_plant", 30, "ml", "fat"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("coriander", None, "1 poignée", "serving_suggestion"),
        ]),
        ("steps", _quesadilla(
            "cuire 300 g de patate douce en cubes à la vapeur 12 minutes et l'écraser avec 2 g de paprika et 2 g de sel ; faire revenir 100 g d'oignon dans 15 ml d'huile d'olive, puis ajouter 150 g de tomates en dés égouttées et 150 g de maïs.",
            "120 g de cheddar végétal râpé", "15 ml d'huile")),
        ("time", 15, 0, 30),
    ],

    # ── Sarrasin : galettes bretonnes à l'eau / galette complète forestière / galette vegan aux champignons ──
    "bread_buckwheat_crepe_03db22": [
        ("title", "Galettes de blé noir bretonnes, pâte à l'eau"),
        ("desc", "La pâte traditionnelle de Haute-Bretagne : farine de blé noir, eau et sel, longuement battue "
                 "puis reposée, cuite sur une crêpière beurrée pour des galettes fines et croustillantes."),
        ("origin", {"cuisine": "french_breton", "region": "bretagne", "city": "rennes"}),
        ("compo", [
            ("buckwheat_flour", 250, "g", "base"),
            ("water", 550, "ml", "hydration"),
            ("egg_raw", 55, "g", "binding"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("butter_sup80pct", 20, "g", "fat"),
        ]),
        ("steps", [
            "Mélanger 250 g de farine de blé noir avec 5 g de sel, puis verser 400 ml d'eau froide petit à petit en battant énergiquement 5 minutes, jusqu'à ce que la pâte fasse des bulles.",
            "Ajouter 1 œuf (55 g) et 150 ml d'eau, puis battre encore 2 minutes.",
            "Laisser reposer au moins 2 heures au frais.",
            "Chauffer une crêpière ou une grande poêle et la graisser au beurre (20 g en tout).",
            "Verser une louche de pâte, l'étaler finement et cuire 2 minutes, jusqu'à ce que les bords soient dentelés et croustillants, puis retourner 30 secondes.",
        ]),
        ("time", 10, 120, 25),
    ],
    "main_galettes_sarrasin_ce9f40": [
        ("title", "Galette complète forestière, œuf, gruyère et champignons"),
        ("desc", "Galette de blé noir garnie comme une complète : œuf miroir, gruyère fondu, champignons "
                 "sautés et épinards, repliée en carré."),
    ],
    "brkf_galette_sarrasin_champign_f6a798": [
        ("title", "Galette de sarrasin aux champignons à l'ail et au thym (vegan)"),
        ("desc", "Galette de sarrasin sans œuf ni beurre, à la pâte eau et lait d'avoine, garnie de champignons "
                 "poêlés à l'ail et au thym."),
    ],

    # ── Pad thaï : de Bangkok à l'œuf / vegan aux légumes croquants ──
    "wok_thai_veg_eb92db": [
        ("title", "Pad thaï de Bangkok au tofu et à l'œuf"),
        ("desc", "Pad thaï de rue : nouilles de riz sautées au tamarin et au sucre de coco, tofu doré, œuf brouillé "
                 "dans le wok, pousses de soja, cacahuètes et citron vert."),
    ],
    "protein_pad_thai_vegan_33c0f3": [
        ("title", "Pad thaï aux légumes croquants (vegan)"),
        ("desc", "Pad thaï sans œuf, riche en légumes : carotte et chou rouge en julienne, pousses de soja et "
                 "tofu, nappés d'une sauce tamarin-soja, cacahuètes et citron vert."),
        ("compo", [
            ("rice_vermicelli_raw_dried", 200, "g", "base"),
            ("tofu_plain_pre_packaged", 200, "g", "protein"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("red_cabbage_raw", 150, "g", "vegetable"),
            ("mung_bean_sprouts_raw_seed_sprouted", 100, "g", "vegetable"),
            ("green_onion_raw", 30, "g", "vegetable"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("tamarind_raw", 30, "g", "seasoning"),
            ("soy_sauce_shoyu_reduced_sodium", 30, "ml", "condiment"),
            ("base_vegetarian_fish_sauce_536a33", 15, "ml", "condiment"),
            ("coconut_sugar", 20, "g", "sweetener"),
            ("sesame_oil_plant", 10, "ml", "fat_cooking"),
            ("peanut_oil_plant", 15, "ml", "fat_cooking"),
            ("peanut_roasted_salted_dry", 30, "g", "garnish"),
            ("lime_juice_fresh", 15, "ml", "seasoning"),
        ]),
        ("steps", [
            "Faire tremper 200 g de nouilles de riz 30 minutes dans l'eau tiède, puis les égoutter.",
            "Sauce : délayer 30 g de pulpe de tamarin dans 30 ml d'eau chaude, filtrer, puis ajouter 30 ml de sauce soja, 15 ml de sauce « poisson » végétale et 20 g de sucre de coco.",
            "Dorer 200 g de tofu en dés dans 15 ml d'huile d'arachide, 5 minutes, puis réserver.",
            "Dans 10 ml d'huile de sésame, sauter 6 g d'ail, 150 g de carotte et 150 g de chou rouge en julienne 2 minutes à feu vif.",
            "Ajouter les nouilles et la sauce, puis sauter 3 minutes. Ajouter le tofu, 100 g de pousses de soja et 30 g d'oignons verts.",
            "Servir avec 30 g de cacahuètes concassées et 15 ml de jus de citron vert.",
        ]),
        ("time", 25, 30, 10),
    ],

    # ── See ew : classique au brocoli chinois / pad kee mao vegan (nouilles ivres) ──
    "noodle_pad_see_ew_classic_v3_n8x4p2": [
        ("title", "Pad see ew au brocoli chinois, tofu et œuf"),
        ("desc", "Larges nouilles de riz caramélisées au wok avec sauce soja sucrée, brocoli chinois (kai lan), "
                 "tofu et œuf, pour un goût fumé typique."),
    ],
    "noodle_pad_see_ew_vegan_162330": [
        ("title", "Pad kee mao, nouilles ivres au basilic (vegan)"),
        ("desc", "Les « nouilles ivres » de Bangkok : larges nouilles de riz sautées très vivement avec piment, "
                 "ail, basilic thaï, brocoli, poivron et tofu, dans une sauce soja et « huître » végétale."),
        ("compo", [
            ("base_rice_noodle_831080", 300, "g", "ingredient"),
            ("tofu_plain_pre_packaged", 200, "g", "ingredient"),
            ("broccoli_raw", 150, "g", "secondary_vegetable"),
            ("red_bell_pepper_raw", 150, "g", "vegetable"),
            ("basil_fresh_herb", 20, "g", "herb"),
            ("chilli_pepper_raw", 10, "g", "spice"),
            ("garlic_raw", 15, "g", "aromatic"),
            ("soy_sauce_shoyu_reduced_sodium", 30, "ml", "condiment"),
            ("base_vegetarian_oyster_sauce_b74b21", 20, "ml", "condiment"),
            ("white_sugar", 8, "g", "seasoning"),
            ("peanut_oil_plant", 30, "ml", "fat"),
        ]),
        ("steps", [
            "Piler 15 g d'ail avec 10 g de piment.",
            "Dorer 200 g de tofu en dés dans 15 ml d'huile d'arachide, 5 minutes, puis réserver.",
            "Dans 15 ml d'huile, faire grésiller la pâte ail-piment 30 secondes, ajouter 150 g de brocoli en petits bouquets et 150 g de poivron en lanières et sauter 3 minutes à feu vif.",
            "Ajouter 300 g de nouilles de riz, 30 ml de sauce soja, 20 ml de sauce « huître » végétale et 8 g de sucre, puis sauter 3 minutes.",
            "Ajouter le tofu et 20 g de basilic, mélanger 30 secondes et servir aussitôt.",
        ]),
        ("time", 15, 10, 12),
    ],

    # ── Krapow : au riz et œuf frit / vegan haricots verts-champignons ──
    "rice_pad_krapow_63acfb": [
        ("title", "Pad krapow au tofu, riz jasmin et œuf frit"),
        ("desc", "Le plat de rue le plus commandé de Bangkok : tofu émietté sauté au basilic sacré, ail et piment, "
                 "servi sur du riz avec un œuf frit croustillant (khai dao)."),
    ],
    "wok_pad_krapow_vegetarien_565aa9": [
        ("title", "Pad krapow aux haricots verts et champignons (vegan)"),
        ("desc", "Krapow végétal : tofu, haricots verts croquants et champignons sautés au wok avec ail, piment "
                 "et basilic, servis sur un riz jasmin."),
        ("compo", [
            ("tofu_plain_pre_packaged", 300, "g", "protein"),
            ("french_bean_raw", 200, "g", "vegetable"),
            ("button_mushroom_raw", 200, "g", "vegetable"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("chilli_pepper_raw", 6, "g", "spice", "pounded"),
            ("basil_fresh_herb", 25, "g", "signature_flavor"),
            ("soy_sauce_shoyu_reduced_sodium", 30, "ml", "umami_salty"),
            ("white_sugar", 8, "g", "balance"),
            ("peanut_oil_plant", 25, "ml", "wok_searing"),
            ("water", 400, "ml", "light_binding"),
            ("white_rice_raw_seed_unenriched", 250, "g", "carbohydrate"),
        ]),
        ("steps", [
            "Rincer 250 g de riz et le cuire à couvert dans 370 ml d'eau, 12 minutes, puis le laisser reposer.",
            "Piler 12 g d'ail avec 6 g de piment.",
            "Émietter 300 g de tofu et le faire dorer dans 25 ml d'huile d'arachide à feu vif, 6 minutes.",
            "Ajouter la pâte ail-piment, 200 g de haricots verts en tronçons et 200 g de champignons émincés, puis sauter 4 minutes.",
            "Ajouter 30 ml de sauce soja, 8 g de sucre et 30 ml d'eau, sauter 1 minute, puis 25 g de basilic hors du feu.",
            "Servir sur le riz.",
        ]),
        ("time", 20, 5, 20),
    ],
}
