"""Variantes 5 : sundubu, puttanesca, quiche, empanadas, minestrone."""

VARIANTS = {
    # ── Sundubu : baek sundubu doux / kimchi sundubu épicé ──
    "egg_sundubu_jjigae_bc21e0": [
        ("title", "Baek sundubu, ragoût de tofu soyeux doux"),
        ("desc", "La version blanche et non pimentée du sundubu : tofu soyeux, champignons et courgette dans un "
                 "bouillon dashi clair à la sauce soja, œufs pochés dans le ragoût et oignons verts."),
        ("compo", [
            ("silken_tofu_pre_packaged", 600, "g", "protein"),
            ("shiitake_mushroom_raw", 100, "g", "ingredient"),
            ("button_mushroom_raw", 150, "g", "ingredient"),
            ("green_zucchini_squash_raw", 150, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("base_dashi_broth_a3a517", 700, "ml", "ingredient"),
            ("soy_sauce_shoyu_reduced_sodium", 15, "ml", "seasoning"),
            ("egg_raw", 220, "g", "ingredient"),
            ("green_onion_raw", 40, "g", "ingredient"),
            ("sesame_oil_plant", 10, "ml", "fat"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
            ("white_rice_short_grain_seed_dried", None, "1 portion", "serving_suggestion"),
        ]),
        ("steps", [
            "Dans un poêlon en terre ou une casserole, faire revenir 100 g d'oignon émincé et 9 g d'ail haché dans 10 ml d'huile de sésame, 3 minutes.",
            "Ajouter 100 g de shiitakés et 150 g de champignons émincés, puis 150 g de courgette en demi-rondelles, et cuire 3 minutes.",
            "Verser 700 ml de dashi, 15 ml de sauce soja et 1 g de sel, puis porter à frémissement.",
            "Ajouter 600 g de tofu soyeux en grosses cuillerées et laisser frémir 5 minutes sans remuer.",
            "Casser 4 œufs (220 g) à la surface et cuire 2 minutes, jusqu'à ce que les blancs soient pris.",
            "Parsemer de 40 g d'oignons verts émincés et servir bouillant, avec du riz.",
        ]),
        ("time", 15, 0, 20),
    ],
    "stew_sundubu_tofu_stew_ebe50e": [
        ("title", "Kimchi sundubu jjigae épicé"),
        ("desc", "Le sundubu rouge des restaurants de Séoul : kimchi bien fermenté revenu avec une huile au piment "
                 "gochugaru, gochujang, tofu soyeux et œufs, servi bouillonnant."),
        ("compo", [
            ("silken_tofu_pre_packaged", 500, "g", "protein"),
            ("base_kimchi_61791a", 250, "g", "ingredient"),
            ("button_mushroom_raw", 200, "g", "ingredient"),
            ("green_zucchini_squash_raw", 150, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("gochugaru", 8, "g", "spice"),
            ("base_gochujang_41da6e", 30, "ml", "condiment"),
            ("base_dashi_broth_a3a517", 700, "ml", "ingredient"),
            ("egg_raw", 220, "g", "ingredient"),
            ("green_onion_raw", 40, "g", "ingredient"),
            ("sesame_oil_plant", 20, "ml", "fat"),
            ("white_rice_short_grain_seed_dried", None, "1 portion", "serving_suggestion"),
        ]),
        ("steps", [
            "Huile pimentée : chauffer doucement 20 ml d'huile de sésame avec 100 g d'oignon émincé, 12 g d'ail haché et 8 g de gochugaru, 2 minutes, sans brûler le piment.",
            "Ajouter 250 g de kimchi haché et le faire revenir 4 minutes, jusqu'à ce qu'il soit translucide.",
            "Ajouter 30 ml de gochujang, 200 g de champignons et 150 g de courgette, puis verser 700 ml de dashi et mijoter 8 minutes.",
            "Ajouter 500 g de tofu soyeux en grosses cuillerées et laisser frémir 5 minutes.",
            "Casser 4 œufs (220 g) à la surface et cuire 2 minutes.",
            "Parsemer de 40 g d'oignons verts émincés et servir bouillant, avec du riz.",
        ]),
        ("time", 15, 0, 25),
    ],

    # ── Puttanesca : napolitaine / tomates cerises rôties et chapelure ──
    "pasta_pasta_puttanesca_e14266": [
        ("title", "Spaghetti alla puttanesca napolitaine"),
        ("desc", "La puttanesca de Naples, sans anchois : sauce tomate vive à l'ail et au piment, olives de Gaète, "
                 "câpres et origan, liée à l'huile d'olive."),
        ("origin", {"region": "campania", "city": "naples"}),
        ("compo", [
            ("pasta_raw_dried", 320, "g", "ingredient"),
            ("tomato_raw_ripe", 400, "g", "fruit"),
            ("capers_canned_in_vinegar", 20, "g", "ingredient"),
            ("black_olive_canned_in_brine", 80, "g", "fruit"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("chilli_pepper_raw", 8, "g", "spice"),
            ("oregano_spice_dried", 1, "g", "herb"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("parsley_fresh_herb", None, "1 poignée", "serving_suggestion"),
        ]),
        ("steps", [
            "Faire chauffer 40 ml d'huile d'olive avec 9 g d'ail émincé et 8 g de piment frais haché, 1 minute, sans colorer.",
            "Ajouter 400 g de tomates concassées et cuire 10 minutes à feu vif.",
            "Ajouter 80 g d'olives noires dénoyautées, 20 g de câpres rincées et 1 g d'origan, puis cuire 3 minutes.",
            "Cuire 320 g de spaghetti dans l'eau bouillante salée avec 3 g de sel, 1 minute de moins que le temps indiqué.",
            "Égoutter les pâtes, les terminer 1 minute dans la sauce avec une louche d'eau de cuisson, puis servir.",
        ]),
        ("time", 10, 0, 20),
    ],
    "pasta_puttanesca_v1x9q2": [
        ("title", "Pâtes puttanesca aux tomates cerises rôties et chapelure à l'ail"),
        ("desc", "Puttanesca au four : tomates cerises rôties jusqu'à éclater avec olives et câpres, pâtes enrobées "
                 "de leur jus et couvertes d'une chapelure croustillante à l'ail et au citron."),
        ("origin", {"region": "", "city": ""}),
        ("compo", [
            ("pasta_raw_dried", 360, "g", "starch"),
            ("cherry_tomato_raw", 500, "g", "vegetable"),
            ("black_olive_canned_in_oil", 60, "g", "vegetable"),
            ("capers_canned_in_vinegar", 20, "g", "salty_acidity"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("chilli_pepper_raw", 6, "g", "spice"),
            ("breadcrumbs_dried", 40, "g", "topping"),
            ("lemon_juice", 10, "ml", "condiment"),
            ("basil_fresh_herb", 15, "g", "herb"),
            ("olive_oil_plant", 45, "ml", "fat"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Préchauffer le four à 200°C. Mélanger dans un plat 500 g de tomates cerises, 60 g d'olives, 20 g de câpres, 8 g d'ail émincé, 6 g de piment et 30 ml d'huile d'olive, puis rôtir 20 minutes.",
            "Chapelure : dorer 40 g de chapelure dans 15 ml d'huile d'olive avec 4 g d'ail râpé, 3 minutes, puis ajouter 10 ml de jus de citron.",
            "Cuire 360 g de pâtes dans l'eau bouillante légèrement salée (1 g de sel), puis les égoutter en gardant une louche d'eau.",
            "Mélanger les pâtes aux tomates rôties en les écrasant légèrement avec un peu d'eau de cuisson.",
            "Servir parsemé de 15 g de basilic et de chapelure à l'ail.",
        ]),
        ("time", 10, 0, 25),
    ],

    # ── Quiche : oignons confits et chèvre / légumes du soleil et parmesan ──
    "egg_quiche_lorraine_vegetarienne_77343c": [
        ("title", "Quiche aux oignons confits et au chèvre frais"),
        ("desc", "Quiche végétarienne à la lorraine : pâte brisée précuite, lit d'oignons fondus, appareil "
                 "œufs-crème et chèvre frais émietté, cuite jusqu'à ce que le centre soit juste pris."),
    ],
    "tarte_quiche_vegetarienne_b849b0": [
        ("title", "Quiche aux légumes du soleil et au parmesan"),
        ("desc", "Quiche d'été garnie de poivron, courgette et champignons revenus à l'huile d'olive, "
                 "dans un appareil œufs, crème et lait relevé de parmesan et d'origan."),
        ("compo", [
            ("shortcrust_pastry_all_butter_raw_paste_pre_packaged", 230, "g", "starch"),
            ("egg_raw", 220, "g", "protein"),
            ("cream_heavy", 150, "ml", "fat"),
            ("milk_liquid_uht_3_5pct", 150, "ml", "batter_softening"),
            ("parmesan_grated_dried_cow", 50, "g", "dairy"),
            ("red_bell_pepper_raw", 150, "g", "vegetable"),
            ("green_zucchini_squash_raw", 150, "g", "vegetable"),
            ("button_mushroom_raw", 120, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic"),
            ("oregano_spice_dried", 1, "g", "herb"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
            ("green_salad_raw_plain", None, "1 portion", "serving_suggestion"),
        ]),
        ("steps", [
            "Préchauffer le four à 180°C. Foncer un moule de 26 cm avec 230 g de pâte brisée, piquer le fond et précuire 12 minutes.",
            "Faire revenir 100 g d'oignon émincé, 150 g de poivron en lanières, 150 g de courgette en dés et 120 g de champignons émincés dans 20 ml d'huile d'olive, 8 minutes, jusqu'à évaporation de l'eau.",
            "Fouetter 4 œufs (220 g) avec 150 ml de crème, 150 ml de lait, 1 g de sel, 1 g de poivre et 1 g d'origan.",
            "Répartir les légumes sur le fond de tarte, verser l'appareil et parsemer de 50 g de parmesan.",
            "Enfourner 30 à 35 minutes, jusqu'à ce que le centre soit juste pris.",
            "Laisser tiédir 5 minutes avant de servir, avec une salade verte.",
        ]),
        ("time", 25, 0, 50),
    ],

    # ── Empanadas : humita de Salta / fromage-oignon / vegan cheddar végétal ──
    "snack_empanadas_974cf2": [
        ("title", "Empanadas salteñas humita, maïs et fromage frais"),
        ("desc", "Empanadas du nord-ouest argentin, garnies de humita : maïs, poivron et oignon revenus, "
                 "queso fresco et œuf dur, cuites au four jusqu'à ce qu'elles soient bien dorées."),
        ("origin", {"region": "salta", "city": "salta"}),
    ],
    "snack_empanadas_au_fromage_466bc4": [
        ("title", "Empanadas fromage-oignon de Buenos Aires"),
        ("desc", "Les empanadas de queso y cebolla des pizzerias de Buenos Aires : fromage frais fondant "
                 "et oignons compotés dans une pâte au beurre dorée au four."),
    ],
    "snack_empanadas_au_fromage_vega_79575a": [
        ("title", "Empanadas vegan à l'oignon caramélisé et au cheddar végétal"),
        ("desc", "Empanadas à la pâte à l'huile, sans beurre ni œuf, garnies d'oignons caramélisés et de "
                 "cheddar végétal maison, dorées au four."),
        ("origin", {"cuisine": "argentinian", "country": "argentina", "region": "buenos_aires"}),
    ],

    # ── Minestrone : d'été au pistou (Ligurie) / d'hiver milanais au riz ──
    "soup_minestrone_9116a2": [
        ("title", "Minestrone d'été alla genovese, au basilic"),
        ("desc", "Minestrone ligure de saison : courgettes, haricots blancs, tomates et petites pâtes, "
                 "servi avec une cuillerée de pistou au basilic et à l'ail."),
        ("origin", {"region": "liguria", "city": "genes"}),
        ("compo", [
            ("carrot_raw", 150, "g", "vegetable"),
            ("celery_stalk_raw", 80, "g", "vegetable"),
            ("onion_raw", 120, "g", "aromatic"),
            ("green_zucchini_squash_raw", 300, "g", "vegetable"),
            ("french_bean_raw", 150, "g", "vegetable"),
            ("tomato_raw_ripe", 300, "g", "vegetable"),
            ("white_bean_boiled", 240, "g", "ingredient", "cooked"),
            ("pasta_raw_dried", 80, "g", "ingredient"),
            ("vegetable_stock_dried", 10, "g", "seasoning"),
            ("water", 1200, "ml", "seasoning"),
            ("basil_fresh_herb", 25, "g", "herb"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("olive_oil_plant", 40, "ml", "fat"),
        ]),
        ("steps", [
            "Faire revenir 120 g d'oignon, 150 g de carotte et 80 g de céleri en dés dans 15 ml d'huile d'olive, 6 minutes.",
            "Ajouter 300 g de tomates concassées, 1,2 L d'eau et 10 g de bouillon déshydraté, puis porter à ébullition.",
            "Ajouter 150 g de haricots verts en tronçons et 300 g de courgettes en dés, puis mijoter 10 minutes.",
            "Ajouter 240 g de haricots blancs et 80 g de petites pâtes, puis cuire 9 minutes.",
            "Pistou : piler ou mixer 25 g de basilic avec 9 g d'ail et 25 ml d'huile d'olive.",
            "Servir le minestrone avec une cuillerée de pistou dans chaque bol.",
        ]),
        ("time", 20, 0, 30),
    ],
    "soup_minestrone_italienne_f98e05": [
        ("title", "Minestrone d'hiver milanais au riz et chou de Milan"),
        ("desc", "Minestrone alla milanese : chou de Milan, pommes de terre et haricots rouges mijotés longuement, "
                 "épaissis au riz plutôt qu'aux pâtes et servis avec du parmesan."),
        ("origin", {"region": "lombardie", "city": "milan"}),
        ("compo", [
            ("carrot_raw", 150, "g", "vegetable"),
            ("celery_stalk_raw", 80, "g", "vegetable"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("savoy_cabbage_raw", 250, "g", "vegetable"),
            ("potato_raw_flesh", 200, "g", "vegetable"),
            ("kidney_bean_boiled", 240, "g", "protein", "cooked"),
            ("white_rice_short_grain_seed_dried", 80, "g", "ingredient"),
            ("tomato_paste_unsalted_canned", 20, "g", "fruit"),
            ("sage_fresh_herb", 3, "g", "herb"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("parmesan_grated_dried_cow", 30, "g", "cheese"),
            ("vegetable_stock_dried", 10, "g", "ingredient"),
            ("water", 1300, "ml", "ingredient"),
        ]),
        ("steps", [
            "Faire revenir 150 g d'oignon, 150 g de carotte et 80 g de céleri en dés avec 6 g d'ail et 3 g de sauge hachés dans 30 ml d'huile d'olive, 8 minutes.",
            "Ajouter 20 g de concentré de tomate, 200 g de pommes de terre en dés, 250 g de chou de Milan émincé, 1,3 L d'eau et 10 g de bouillon déshydraté. Mijoter 30 minutes à couvert.",
            "Ajouter 240 g de haricots rouges et 80 g de riz rond, puis cuire 15 minutes, jusqu'à ce que le riz soit tendre et la soupe épaisse.",
            "Laisser reposer 5 minutes hors du feu.",
            "Servir parsemé de 30 g de parmesan râpé.",
        ]),
        ("time", 20, 5, 55),
    ],
}
