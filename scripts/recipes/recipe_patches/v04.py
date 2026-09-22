"""Variantes 4 : pierogi, tian, gnocchis, taboulé."""

_PIEROGI_DOUGH_STEP = ("Pétrir 300 g de farine avec {liant} et 3 g de sel jusqu'à obtenir une pâte lisse, "
                       "puis la laisser reposer 30 minutes sous un linge.")

VARIANTS = {
    # ── Pierogi : ruskie / sarrasin de Lublin / vegan pommes de terre-aneth / champignons / champignons-choucroute vegan ──
    "dumpling_pierogi_pommes_de_terre_ca9985": [
        ("title", "Pierogi ruskie, pommes de terre et fromage blanc"),
        ("desc", "Les pierogi les plus populaires de Pologne : farce de pommes de terre, twaróg (fromage blanc) et "
                 "oignons dorés au beurre, pochés puis servis nappés d'oignons fondants."),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 300, "g", "carbohydrate"),
            ("egg_raw", 55, "g", "ingredient"),
            ("water", 110, "ml", "liquid"),
            ("potato_raw_flesh", 500, "g", "ingredient"),
            ("fromage_blanc_plain_2_5pct_cow", 200, "g", "ingredient"),
            ("yellow_onion_raw", 200, "g", "aromatic_base"),
            ("butter_sup80pct", 40, "g", "fat_cooking"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            _PIEROGI_DOUGH_STEP.format(liant="1 œuf (55 g), 110 ml d'eau tiède"),
            "Cuire 500 g de pommes de terre à l'eau 20 minutes, puis les écraser.",
            "Faire dorer 200 g d'oignon émincé dans 40 g de beurre, 10 minutes. Mélanger la moitié des oignons aux pommes de terre avec 200 g de fromage blanc bien égoutté, 2 g de sel et 1 g de poivre.",
            "Étaler la pâte sur 2 mm, découper des disques de 8 cm, garnir d'une cuillerée de farce, puis replier et souder les bords en pinçant.",
            "Pocher les pierogi par petites quantités dans l'eau bouillante salée, 3 minutes après qu'ils remontent à la surface.",
            "Servir nappés du reste des oignons au beurre.",
        ]),
        ("time", 45, 30, 35),
    ],
    "pasta_pierogi_aux_pommes_de_6b3efe": [
        ("title", "Pierogi de Lublin au sarrasin et pommes de terre"),
        ("desc", "Spécialité de la région de Lublin : pierogi farcis de kasza (gruau de sarrasin grillé), de pommes de "
                 "terre et d'oignons, à la saveur de noisette, puis dorés à la poêle."),
        ("origin", {"region": "lubelskie", "city": "lublin"}),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 300, "g", "dough"),
            ("water", 150, "ml", "hydration"),
            ("sunflower_oil_plant", 15, "ml", "dough"),
            ("buckwheat_groats_roasted_dried_dry", 100, "g", "ingredient"),
            ("potato_raw_flesh", 300, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic"),
            ("butter_sup80pct", 40, "g", "onion_cooking"),
            ("marjoram_spice_dried", 1, "g", "herb"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ]),
        ("steps", [
            _PIEROGI_DOUGH_STEP.format(liant="150 ml d'eau tiède, 15 ml d'huile"),
            "Cuire 100 g de gruau de sarrasin grillé dans 200 ml d'eau salée, 12 minutes à couvert. Cuire 300 g de pommes de terre à l'eau 20 minutes, puis les écraser.",
            "Faire dorer 150 g d'oignon émincé dans 20 g de beurre, 10 minutes. Mélanger avec le sarrasin, la purée, 1 g de marjolaine, 2 g de sel et 1 g de poivre.",
            "Étaler la pâte sur 2 mm, découper des disques de 8 cm, garnir, puis replier et souder les bords.",
            "Pocher les pierogi 3 minutes après qu'ils remontent à la surface, puis les égoutter.",
            "Les faire dorer 3 minutes de chaque côté dans 20 g de beurre et servir.",
        ]),
        ("time", 40, 30, 40),
    ],
    "dumpling_pierogi_aux_pommes_de_ter_24a890": [
        ("title", "Pierogi aux pommes de terre et à l'aneth (vegan)"),
        ("desc", "Pâte à l'huile sans œuf, farce de pommes de terre écrasées aux oignons caramélisés, à l'aneth "
                 "et à la muscade, pierogi dorés à la poêle."),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 300, "g", "carbohydrate"),
            ("water", 150, "ml", "liquid"),
            ("olive_oil_plant", 45, "ml", "fat_cooking"),
            ("potato_raw_flesh", 600, "g", "ingredient"),
            ("onion_raw", 200, "g", "aromatic_base"),
            ("dill_weed_fresh_herb_leaf", 10, "g", "herb"),
            ("nutmeg_spice", 1, "g", "spice"),
            ("vegan_butter", 20, "g", "fat"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
        ]),
        ("steps", [
            _PIEROGI_DOUGH_STEP.format(liant="150 ml d'eau tiède, 15 ml d'huile d'olive"),
            "Cuire 600 g de pommes de terre à l'eau 20 minutes, puis les écraser.",
            "Caraméliser 200 g d'oignon émincé dans 30 ml d'huile d'olive, 20 minutes à feu doux. En mélanger les deux tiers à la purée avec 10 g d'aneth ciselé, 1 g de muscade et 2 g de sel.",
            "Étaler la pâte sur 2 mm, découper des disques de 8 cm, garnir, puis replier et souder les bords.",
            "Pocher les pierogi 3 minutes après qu'ils remontent, les égoutter, puis les dorer dans 20 g de beurre végétal.",
            "Servir avec le reste des oignons caramélisés.",
        ]),
        ("time", 40, 30, 40),
    ],
    "dumpling_pierogi_aux_champignons_d86017": [
        ("title", "Pierogi aux champignons et à la crème aigre"),
        ("desc", "Pierogi à la pâte aux œufs, farcis de champignons et d'oignons revenus à la marjolaine, "
                 "servis dorés au beurre avec de la crème aigre."),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 300, "g", "carbohydrate"),
            ("egg_raw", 55, "g", "ingredient"),
            ("water", 110, "ml", "liquid"),
            ("button_mushroom_raw", 400, "g", "ingredient"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("breadcrumbs_dried", 20, "g", "binder"),
            ("marjoram_spice_dried", 1, "g", "herb"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("canola", 15, "ml", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("sour_cream_fermented_18pct", None, "2 cuillères à soupe", "serving_suggestion"),
        ]),
        ("steps", [
            _PIEROGI_DOUGH_STEP.format(liant="1 œuf (55 g), 110 ml d'eau tiède"),
            "Hacher finement 400 g de champignons et 150 g d'oignon, puis les faire revenir dans 15 ml d'huile de colza à feu vif, 12 minutes, jusqu'à évaporation complète de l'eau.",
            "Ajouter 6 g d'ail haché, 1 g de marjolaine, 2 g de sel, 1 g de poivre et 20 g de chapelure, puis laisser refroidir.",
            "Étaler la pâte sur 2 mm, découper des disques de 8 cm, garnir, puis replier et souder les bords.",
            "Pocher les pierogi 3 minutes après qu'ils remontent, puis les dorer dans 30 g de beurre.",
            "Servir avec de la crème aigre.",
        ]),
        ("time", 40, 30, 35),
    ],
    "dumpling_pierogi_aux_champignons_v_beca85": [
        ("title", "Pierogi du réveillon, choucroute et champignons (vegan)"),
        ("desc", "Pierogi de Wigilia, le repas maigre de Noël polonais : farce de choucroute et de champignons "
                 "revenus à l'oignon, pâte à l'huile sans œuf."),
        ("compo", [
            ("wheat_all_purpose_flour_unenriched_unbleached", 300, "g", "carbohydrate"),
            ("water", 150, "ml", "liquid"),
            ("olive_oil_extra_virgin_plant", 45, "ml", "fat"),
            ("sauerkraut_canned_low_sodium", 300, "g", "ingredient"),
            ("button_mushroom_raw", 200, "g", "ingredient"),
            ("porcini_mushroom_raw", 50, "g", "ingredient"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("bay_leaf", 1, "g", "aromatic"),
            ("allspice_powder", 1, "g", "spice"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            _PIEROGI_DOUGH_STEP.format(liant="150 ml d'eau tiède, 15 ml d'huile d'olive"),
            "Rincer 300 g de choucroute, l'égoutter et la cuire 25 minutes à couvert avec 100 ml d'eau, 1 g de laurier et 1 g de piment de la Jamaïque, puis la presser et la hacher.",
            "Faire revenir 150 g d'oignon, 200 g de champignons et 50 g de cèpes hachés dans 30 ml d'huile d'olive, 10 minutes. Mélanger à la choucroute avec 1 g de poivre.",
            "Étaler la pâte sur 2 mm, découper des disques de 8 cm, garnir, puis replier et souder les bords.",
            "Pocher les pierogi 3 minutes après qu'ils remontent à la surface.",
            "Servir chauds, arrosés d'un filet d'huile de cuisson des oignons.",
        ]),
        ("time", 40, 30, 45),
    ],

    # ── Tian : gratiné au chèvre (plat) / niçois aux pommes de terre (accompagnement vegan) ──
    "main_tian_provencal_4c7999": [
        ("title", "Tian provençal gratiné au chèvre"),
        ("desc", "Tian en plat complet : rosaces de courgettes, aubergines et tomates sur un lit d'oignons fondus, "
                 "gratinées au chèvre et à la chapelure parfumée au thym."),
        ("origin", {"cuisine": "french_provencal"}),
        ("compo", [
            ("green_zucchini_squash_raw", 450, "g", "vegetable"),
            ("eggplant_raw", 400, "g", "vegetable"),
            ("tomato_raw_ripe", 400, "g", "fruit"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("goat_cheese_log", 150, "g", "protein"),
            ("breadcrumbs_dried", 25, "g", "topping"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Préchauffer le four à 180°C. Faire fondre 150 g d'oignon émincé et 9 g d'ail haché dans 15 ml d'huile d'olive, 8 minutes, puis les étaler au fond d'un plat.",
            "Couper en rondelles de 5 mm 450 g de courgettes, 400 g d'aubergines et 400 g de tomates, puis les disposer en rosace serrée en les alternant.",
            "Arroser de 25 ml d'huile d'olive, saler avec 3 g de sel, poivrer et parsemer de 3 g de thym.",
            "Couvrir de papier aluminium et cuire 40 minutes.",
            "Découvrir, répartir 150 g de chèvre en rondelles et 25 g de chapelure, puis gratiner 15 minutes.",
            "Servir chaud ou tiède.",
        ]),
        ("time", 20, 0, 55),
    ],
    "side_tian_provencal_vegan_886a6d": [
        ("title", "Tian niçois aux pommes de terre et au romarin (vegan)"),
        ("desc", "Accompagnement vegan cuit lentement : pommes de terre, courgettes, aubergines et tomates en lamelles, "
                 "arrosés d'huile d'olive, parfumés au romarin et au thym."),
        ("origin", {"cuisine": "french_provencal", "region": "provence_alpes_cote_dazur", "city": "nice"}),
    ],

    # ── Gnocchis : pesto et haricots verts / pesto pilé / pesto vegan roquette-noix / sorrentina / poêlés vegan / beurre-sauge ──
    "pasta_gnocchi_al_pesto_5bb01c": [
        ("title", "Gnocchi au pesto, haricots verts et pommes de terre"),
        ("desc", "Comme les trofie de Gênes, des gnocchis cuits avec des haricots verts, enrobés de pesto maison "
                 "et servis avec du parmesan."),
        ("origin", {"region": "liguria", "city": "genes"}),
        ("compo", [
            ("potato_gnocchi_to_cook", 500, "g", "base"),
            ("french_bean_raw", 250, "g", "vegetable"),
            ("base_pesto_905db7", 120, "g", "seasoning"),
            ("parmesan_grated_dried_cow", None, "1 cuillère à soupe", "serving_suggestion"),
        ]),
        ("steps", [
            "Porter à ébullition une grande casserole d'eau légèrement salée.",
            "Cuire 250 g de haricots verts équeutés et coupés en tronçons 6 minutes.",
            "Ajouter 500 g de gnocchis dans la même eau et les retirer dès qu'ils remontent à la surface, avec les haricots.",
            "Mélanger hors du feu avec 120 g de pesto détendu d'une cuillerée d'eau de cuisson.",
            "Servir aussitôt avec du parmesan.",
        ]),
        ("time", 10, 0, 10),
    ],
    "pasta_gnocchi_pesto_classic_v2_m7k2q4": [
        ("title", "Gnocchi au pesto génois pilé au mortier"),
        ("desc", "Pesto alla genovese préparé au mortier : basilic frais, pignons, ail, parmesan et huile d'olive "
                 "pilés jusqu'à obtenir une crème verte, qui enrobe des gnocchis de pomme de terre."),
        ("origin", {"region": "liguria", "city": "genes"}),
    ],
    "pasta_gnocchi_al_pesto_vegan_954303": [
        ("title", "Gnocchi au pesto de roquette et noix (vegan)"),
        ("desc", "Gnocchis maison sans œuf enrobés d'un pesto vegan de roquette, basilic et cerneaux de noix, "
                 "relevé à la levure nutritionnelle."),
        ("origin", {"region": "", "city": ""}),
        ("compo", [
            ("base_gnocchi_vegan_dd3b0e", 500, "g", "ingredient"),
            ("arugula_raw", 40, "g", "herb"),
            ("basil_fresh_herb", 20, "g", "herb"),
            ("walnut_shelled_dried", 30, "g", "ingredient"),
            ("nutritional_yeast_flakes", 15, "g", "ingredient"),
            ("garlic_raw", 5, "g", "aromatic"),
            ("olive_oil_plant", 50, "ml", "fat"),
            ("lemon_juice", 10, "ml", "condiment"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Mixer 40 g de roquette, 20 g de basilic, 30 g de cerneaux de noix, 15 g de levure nutritionnelle, 5 g d'ail, 50 ml d'huile d'olive, 10 ml de jus de citron, 1 g de sel et 1 g de poivre en pesto grossier.",
            "Cuire 500 g de gnocchis vegan dans l'eau bouillante salée avec 2 g de sel, et les retirer dès qu'ils remontent à la surface.",
            "Mélanger hors du feu avec le pesto détendu de 2 cuillerées d'eau de cuisson.",
            "Servir aussitôt.",
        ]),
        ("time", 10, 0, 10),
    ],
    "pasta_gnocchis_a_la_tomate_8e1632": [
        ("title", "Gnocchi alla sorrentina"),
        ("desc", "Spécialité de Sorrente : gnocchis enrobés de sauce tomate au basilic, couverts de mozzarella "
                 "puis gratinés au four jusqu'à ce que le fromage file."),
        ("origin", {"region": "campania", "city": "sorrente"}),
        ("compo", [
            ("potato_gnocchi_to_cook", 500, "g", "base"),
            ("tomato_raw_ripe", 500, "g", "vegetable"),
            ("garlic_raw", 5, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 20, "ml", "fat"),
            ("cows_milk_mozzarella_cow", 125, "g", "topping"),
            ("parmesan_grated_dried_cow", 20, "g", "topping"),
            ("basil_fresh_herb", 10, "g", "herb"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire revenir 5 g d'ail haché dans 20 ml d'huile d'olive 1 minute, ajouter 500 g de tomates concassées et 1 g de sel, puis mijoter 15 minutes. Ajouter 10 g de basilic ciselé.",
            "Préchauffer le four à 220°C. Cuire 500 g de gnocchis à l'eau bouillante salée et les retirer dès qu'ils remontent.",
            "Mélanger les gnocchis à la sauce et les verser dans un plat à gratin.",
            "Couvrir de 125 g de mozzarella en dés et de 20 g de parmesan, puis gratiner 10 minutes.",
            "Servir brûlant.",
        ]),
        ("time", 10, 0, 30),
    ],
    "pasta_gnocchis_a_la_tomate_vega_ca281e": [
        ("title", "Gnocchis poêlés aux tomates cerises et basilic (vegan)"),
        ("desc", "Gnocchis maison vegan dorés à la poêle, puis sautés avec des tomates cerises éclatées, de l'ail "
                 "et du basilic, saupoudrés de levure nutritionnelle."),
        ("origin", {"region": "", "city": ""}),
        ("compo", [
            ("base_gnocchi_vegan_dd3b0e", 500, "g", "ingredient"),
            ("cherry_tomato_raw", 400, "g", "fruit"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("basil_fresh_herb", 20, "g", "herb"),
            ("olive_oil_extra_virgin_plant", 35, "ml", "fat"),
            ("nutritional_yeast_flakes", 15, "g", "ingredient"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Cuire 500 g de gnocchis vegan à l'eau bouillante salée et les retirer dès qu'ils remontent, puis les égoutter.",
            "Les faire dorer dans 25 ml d'huile d'olive à feu vif, 5 minutes, en les retournant.",
            "Ajouter 10 ml d'huile, 10 g d'ail émincé et 400 g de tomates cerises coupées en deux, puis sauter 5 minutes, jusqu'à ce que les tomates éclatent. Saler avec 3 g de sel.",
            "Hors du feu, ajouter 20 g de basilic ciselé et parsemer de 15 g de levure nutritionnelle.",
        ]),
        ("time", 10, 0, 15),
    ],
    "main_gnocchi_f17041": [
        ("title", "Gnocchi maison au beurre et à la sauge"),
        ("desc", "Gnocchis de pomme de terre roulés à la main, pochés puis enrobés de beurre noisette à la sauge "
                 "et de parmesan, à la vénitienne."),
        ("compo", [
            ("potato_raw_flesh", 800, "g", "base"),
            ("wheat_all_purpose_flour_unenriched_unbleached", 200, "g", "binding"),
            ("egg_raw", 50, "g", "binding"),
            ("butter_sup80pct", 50, "g", "fat"),
            ("sage_fresh_herb", 6, "g", "herb"),
            ("parmesan_grated_dried_cow", 30, "g", "topping"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Cuire 800 g de pommes de terre entières avec la peau à l'eau salée, 30 minutes, puis les éplucher chaudes et les passer au presse-purée.",
            "Ajouter 200 g de farine, 1 œuf (50 g) et 3 g de sel, puis pétrir juste le temps d'obtenir une pâte souple.",
            "Rouler en boudins de 2 cm, couper des tronçons de 2 cm et les rainurer à la fourchette.",
            "Pocher les gnocchis dans l'eau bouillante salée et les retirer dès qu'ils remontent.",
            "Faire mousser 50 g de beurre avec 6 g de feuilles de sauge jusqu'à ce qu'il soit noisette, puis y enrober les gnocchis.",
            "Servir parsemé de 30 g de parmesan et de 1 g de poivre.",
        ]),
        ("time", 40, 0, 40),
    ],

    # ── Taboulé : traditionnel / à la grenade / de sarrasin au concombre ──
    "entry_taboule_libanais_a_la_gre_cae147": [
        ("title", "Taboulé libanais à la grenade et au sumac"),
        ("desc", "Taboulé d'herbes à la libanaise, persil et menthe dominants, relevé de sumac et parsemé "
                 "de grains de grenade pour une note acidulée et croquante."),
        ("origin", {"country": "lebanon"}),
        ("compo", [
            ("parsley_fresh_herb", 150, "g", "main_herb"),
            ("mint_fresh_herb", 30, "g", "herb"),
            ("bulgur_raw_dried", 50, "g", "base", "soaked"),
            ("tomato_raw_ripe", 240, "g", "vegetable"),
            ("lemon_juice", 60, "ml", "acidifier"),
            ("olive_oil_plant", 45, "ml", "fat"),
            ("pomegranate_raw", 80, "g", "garnish"),
            ("sumac", 2, "g", "spice"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire tremper 50 g de boulgour fin dans 60 ml de jus de citron et 30 ml d'eau, 10 minutes.",
            "Ciseler très finement 150 g de persil et 30 g de menthe, puis couper 240 g de tomates en petits dés.",
            "Mélanger les herbes, les tomates et le boulgour avec 45 ml d'huile d'olive, 3 g de sel, 1 g de poivre et 2 g de sumac.",
            "Parsemer de 80 g de grains de grenade et servir frais.",
        ]),
        ("time", 20, 10, 0),
    ],
    "salad_tabbouleh_f7x2p9": [
        ("desc", "Le taboulé des montagnes libanaises : une salade de persil ciselé au couteau, à peine de boulgour, "
                 "tomates, oignon et menthe, assaisonnée de citron et d'huile d'olive."),
    ],
    "side_tabbouleh_de_sarrasin_7e68ad": [
        ("title", "Taboulé de sarrasin au concombre"),
        ("desc", "Variante sans gluten : grains de sarrasin cuits, concombre, tomates cerises, persil et menthe, "
                 "dans une vinaigrette citronnée."),
        ("origin", {"cuisine": "levantine"}),
        ("compo", [
            ("buckwheat_raw_whole_seed", 200, "g", "base", "cooked"),
            ("parsley_fresh_herb", 60, "g", "herb"),
            ("mint_fresh_herb", 20, "g", "herb"),
            ("cherry_tomato_raw", 250, "g", "vegetable"),
            ("cucumber_raw_with_skin", 200, "g", "vegetable"),
            ("olive_oil_plant", 45, "ml", "fat"),
            ("lemon_juice", 50, "ml", "acidifier"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Rincer 200 g de sarrasin et le cuire 12 minutes à l'eau bouillante salée : il doit rester ferme. Égoutter et laisser refroidir.",
            "Couper 250 g de tomates cerises en quartiers et 200 g de concombre en petits dés. Ciseler 60 g de persil et 20 g de menthe.",
            "Mélanger 45 ml d'huile d'olive, 50 ml de jus de citron, 2 g de sel et 1 g de poivre.",
            "Mélanger le sarrasin, les légumes, les herbes et la vinaigrette, puis servir frais.",
        ]),
        ("time", 15, 0, 12),
    ],
}
