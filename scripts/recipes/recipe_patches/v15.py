"""Variantes 15 : derniers quasi-doublons (kimchi bokkeumbap, rajma, moussaka, norma, salade grecque,
soupe à l'oignon, tatin, dauphinois, soupes de courge et de lentilles, terrines)."""

VARIANTS = {
    # ── Troisième kimchi bokkeumbap : au fromage fondu ──
    "rice_kimchi_bokkeumbap_2cbfe6": [
        ("title", "Kimchi bokkeumbap gratiné au fromage"),
        ("desc", "La version « cheese » des snack-bars coréens : riz sauté au kimchi, carotte et oignons verts, "
                 "couvert de mozzarella fondue à la poêle, avec un œuf brouillé."),
        ("compo", [
            ("white_rice_cooked_short_grain_seed", 600, "g", "carbohydrate", "cooked"),
            ("base_kimchi_61791a", 250, "g", "ingredient"),
            ("carrot_raw", 120, "g", "vegetable"),
            ("egg_raw", 110, "g", "ingredient"),
            ("cows_milk_mozzarella_cow", 120, "g", "ingredient"),
            ("green_onion_raw", 40, "g", "ingredient"),
            ("soy_sauce_shoyu_reduced_sodium", 15, "ml", "condiment"),
            ("sesame_oil_plant", 10, "ml", "fat"),
            ("canola", 20, "ml", "fat"),
        ]),
        ("steps", [
            "Faire revenir 120 g de carotte en petits dés dans 20 ml d'huile, 3 minutes, puis ajouter 250 g de kimchi haché et sauter 4 minutes.",
            "Ajouter 600 g de riz cuit froid et 15 ml de sauce soja, puis sauter 4 minutes à feu vif.",
            "Pousser le riz sur le côté, brouiller 2 œufs (110 g) dans la poêle, puis les mélanger au riz.",
            "Tasser le riz, couvrir de 120 g de mozzarella râpée, couvrir la poêle et laisser fondre 3 minutes à feu doux.",
            "Arroser de 10 ml d'huile de sésame, parsemer de 40 g d'oignons verts et servir dans la poêle.",
        ]),
        ("time", 10, 0, 15),
    ],

    # ── Rajma chawal de Jammu (le rajma masala vegan devient celui du Pendjab, v09) ──
    "main_rajma_masala_bce2a4": [
        ("title", "Rajma chawal de Jammu, haricots rouges et riz"),
        ("desc", "Le repas du dimanche au Jammu : petits haricots rouges mijotés dans une sauce oignon-tomate au "
                 "gingembre et aux épices, servis sur un riz basmati fumant."),
        ("origin", {"region": "jammu", "city": "jammu"}),
        ("compo", [
            ("kidney_bean_boiled", 360, "g", "plant_protein", "cooked"),
            ("basmati_rice_raw_seed", 240, "g", "carbohydrate"),
            ("yellow_onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("ginger_raw_root_fresh", 10, "g", "aromatic"),
            ("tomato_raw_ripe", 300, "g", "fruit"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("turmeric_powder", 2, "g", "spice"),
            ("garam_masala", 3, "g", "spice"),
            ("sunflower_oil_plant", 30, "ml", "fat"),
            ("coriander_raw_fresh_herb", 10, "g", "herb"),
            ("water", 700, "ml", "liquid"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ]),
        ("steps", [
            "Rincer 240 g de riz basmati et le cuire dans 400 ml d'eau salée avec 1 g de sel, 12 minutes à couvert, puis le laisser reposer.",
            "Faire grésiller 3 g de cumin dans 30 ml d'huile, ajouter 150 g d'oignon haché et le dorer 10 minutes.",
            "Ajouter 9 g d'ail et 10 g de gingembre hachés, 2 g de curcuma, puis 300 g de tomates mixées et 3 g de sel, et cuire 8 minutes.",
            "Ajouter 360 g de haricots rouges et 300 ml d'eau, puis mijoter 20 minutes en écrasant quelques haricots. Ajouter 3 g de garam masala.",
            "Servir le rajma sur le riz, parsemé de 10 g de coriandre.",
        ]),
        ("time", 15, 0, 40),
    ],

    # ── Moussaka : végétarienne béchamel au lait / vegan aux lentilles ──
    "tarte_moussaka_veg_d55fa8": [
        ("title", "Moussaka végétarienne grecque, béchamel au lait"),
        ("desc", "Moussaka sans viande à la grecque : aubergines rôties, sauce tomate à l'ail et à la cannelle, "
                 "sous une épaisse béchamel au beurre et à la muscade, gratinée."),
    ],
    "main_moussaka_fcf86b": [
        ("title", "Moussaka aux lentilles et pommes de terre (vegan)"),
        ("desc", "Moussaka végétale : couches de pommes de terre et d'aubergines, ragoût de lentilles vertes à la "
                 "tomate, béchamel vegan au lait d'avoine gratinée."),
    ],

    # ── Pasta alla Norma : de Catane / vegan aubergines rôties et ricotta de cajou ──
    "pasta_pasta_alla_norma_5cc26e": [
        ("title", "Pasta alla Norma de Catane, ricotta salata"),
        ("desc", "Le plat emblématique de Catane : aubergines frites, sauce tomate au basilic et ricotta salata "
                 "râpée généreusement sur les pâtes."),
        ("origin", {"region": "sicile", "city": "catane"}),
        ("compo", [
            ("pasta_raw_dried", 320, "g", "ingredient"),
            ("eggplant_raw", 600, "g", "vegetable"),
            ("tomato_raw_ripe", 400, "g", "fruit"),
            ("base_salted_ricotta_1ecd1c", 80, "g", "ingredient"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("olive_oil_plant", 45, "ml", "fat"),
            ("basil_fresh_herb", 20, "g", "herb"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
        ]),
        ("steps", [
            "Couper 600 g d'aubergines en dés, les dorer en deux fois dans 35 ml d'huile d'olive à feu vif, 8 minutes, puis les égoutter.",
            "Faire revenir 9 g d'ail dans 10 ml d'huile, ajouter 400 g de tomates concassées et 1 g de sel, puis cuire 12 minutes. Ajouter 20 g de basilic.",
            "Cuire 320 g de pâtes dans l'eau bouillante salée avec 1 g de sel, 1 minute de moins que le temps indiqué.",
            "Mélanger les pâtes, la sauce et les aubergines avec un peu d'eau de cuisson.",
            "Servir couvert de 80 g de ricotta salata râpée.",
        ]),
        ("time", 15, 0, 35),
    ],
    "pasta_pasta_alla_norma_a_la_ric_d282a6": [
        ("title", "Pâtes aux aubergines rôties, tomates cerises et ricotta de cajou (vegan)"),
        ("desc", "Variante de la Norma plus légère : aubergines rôties au four, tomates cerises éclatées, menthe "
                 "et basilic, et quenelles de ricotta de cajou."),
        ("compo", [
            ("pasta_raw_dried", 320, "g", "ingredient"),
            ("eggplant_raw", 600, "g", "vegetable"),
            ("cherry_tomato_raw", 350, "g", "fruit"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("base_cashew_ricotta_5c62e9", 80, "g", "ingredient"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("basil_fresh_herb", 15, "g", "herb"),
            ("mint_fresh_herb", 5, "g", "herb"),
            ("chilli_pepper_raw", 3, "g", "spice"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ]),
        ("steps", [
            "Préchauffer le four à 220°C. Mélanger 600 g d'aubergines en dés avec 25 ml d'huile d'olive et 1 g de sel, puis rôtir 25 minutes.",
            "Ajouter 350 g de tomates cerises coupées en deux, 9 g d'ail émincé et 3 g de piment, arroser de 15 ml d'huile et rôtir encore 10 minutes.",
            "Cuire 320 g de pâtes dans l'eau salée avec 2 g de sel et les égoutter en gardant une louche d'eau.",
            "Mélanger les pâtes aux légumes rôtis avec un peu d'eau de cuisson, 15 g de basilic et 5 g de menthe.",
            "Servir avec des quenelles de ricotta de cajou (80 g au total).",
        ]),
        ("time", 15, 0, 35),
    ],

    # ── Salade grecque : horiatiki / vegan pois chiches et tofu mariné ──
    "salad_greek_classic_v2_t4m8q1": [
        ("title", "Horiatiki, salade grecque de village à la feta"),
        ("desc", "La salade des tavernes grecques : tomates, concombre, poivron vert, oignon rouge et olives, "
                 "un bloc de feta posé dessus, huile d'olive et origan."),
        ("compo", [
            ("tomato_raw_ripe", 400, "g", "base"),
            ("cucumber_raw_with_skin", 300, "g", "freshness"),
            ("green_bell_pepper_raw", 120, "g", "vegetable"),
            ("red_onion_raw", 80, "g", "aromatic"),
            ("black_olive_canned_in_oil", 50, "g", "garnish"),
            ("feta", 120, "g", "protein"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("red_wine_vinegar_liquid", 10, "ml", "acidity"),
            ("oregano_spice_dried", 1, "g", "herb"),
            ("black_pepper_spice", 1, "g", "finishing"),
        ]),
        ("steps", [
            "Couper 400 g de tomates en quartiers, 300 g de concombre en demi-rondelles épaisses et 120 g de poivron vert en anneaux, émincer 80 g d'oignon rouge.",
            "Mélanger avec 50 g d'olives noires, 10 ml de vinaigre et 1 g de poivre.",
            "Poser 120 g de feta en un seul bloc sur la salade.",
            "Arroser de 40 ml d'huile d'olive, saupoudrer de 1 g d'origan et servir sans saler davantage.",
        ]),
        ("time", 15, 0, 0),
    ],
    "salad_grecque_classique_vegan_a9f9a4": [
        ("title", "Salade grecque aux pois chiches et au tofu mariné à l'origan (vegan)"),
        ("desc", "Salade grecque plat complet et végétale : crudités, olives et pois chiches, avec des dés de tofu "
                 "marinés au citron et à l'origan en guise de feta."),
        ("compo", [
            ("tomato_raw_ripe", 300, "g", "fruit"),
            ("cucumber_raw_with_skin", 300, "g", "vegetable"),
            ("chickpea_boiled", 200, "g", "plant_protein", "cooked"),
            ("black_olive_canned_in_brine", 60, "g", "fruit"),
            ("tofu_plain_pre_packaged", 200, "g", "ingredient"),
            ("red_onion_raw", 80, "g", "vegetable"),
            ("olive_oil_plant", 45, "ml", "fat"),
            ("lemon_juice", 30, "ml", "fruit"),
            ("oregano", 2, "g", "ingredient"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Couper 200 g de tofu ferme en dés et les mariner 20 minutes avec 20 ml de jus de citron, 15 ml d'huile d'olive, 1 g d'origan et 1 g de sel.",
            "Couper 300 g de tomates et 300 g de concombre en morceaux, émincer 80 g d'oignon rouge.",
            "Mélanger avec 200 g de pois chiches, 60 g d'olives, 30 ml d'huile d'olive, 10 ml de jus de citron, 1 g de sel et 1 g de poivre.",
            "Répartir le tofu mariné sur la salade et saupoudrer de 1 g d'origan.",
        ]),
        ("time", 15, 20, 0),
    ],

    # ── Soupe à l'oignon : lyonnaise au comté / au cidre et croûtons à l'ail vegan ──
    "soup_soup_k3d2p1": [
        ("title", "Soupe à l'oignon gratinée lyonnaise au comté"),
        ("desc", "La soupe des bouchons lyonnais : oignons longuement caramélisés au beurre, déglacés au vin "
                 "blanc, bouillon, croûtons et comté gratinés au four."),
        ("origin", {"cuisine": "french_lyonnaise", "region": "auvergne_rhone_alpes", "city": "lyon"}),
    ],
    "soup_a_l_oignon_gratinee_vegan_826f59": [
        ("title", "Soupe à l'oignon au cidre et croûtons à l'ail (vegan)"),
        ("desc", "Soupe à l'oignon normande végétale : oignons caramélisés à l'huile, déglacés au cidre brut, "
                 "bouillon au thym, servie avec des croûtons frottés à l'ail et à la levure nutritionnelle."),
        ("origin", {"cuisine": "french_normand", "region": "normandie", "city": ""}),
        ("compo", [
            ("yellow_onion_raw", 800, "g", "aromatic_base"),
            ("olive_oil_plant", 35, "ml", "fat_cooking"),
            ("dry_cider_liquid_unsweetened", 150, "ml", "liquid"),
            ("wheat_all_purpose_flour_unenriched_unbleached", 15, "g", "carbohydrate"),
            ("vegetable_stock_dried", 9, "g", "ingredient"),
            ("water", 850, "ml", "ingredient"),
            ("thyme_fresh_herb", 4, "g", "herb"),
            ("bay_leaf_spice", 1, "g", "herb"),
            ("white_bread_baguette", 120, "g", "ingredient"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("nutritional_yeast_flakes", 15, "g", "ingredient"),
            ("table_salt_unenriched", 1, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Émincer 800 g d'oignons et les faire suer à couvert dans 25 ml d'huile d'olive, 20 minutes à feu doux, puis les caraméliser 20 minutes à découvert jusqu'à ce qu'ils soient brun acajou.",
            "Saupoudrer de 15 g de farine, remuer 1 minute, puis déglacer avec 150 ml de cidre brut et réduire 2 minutes.",
            "Ajouter 850 ml d'eau, 9 g de bouillon, 4 g de thym, 1 g de laurier, 1 g de sel et 1 g de poivre, puis mijoter 15 minutes.",
            "Griller 120 g de baguette en tranches, les frotter avec 6 g d'ail, les arroser de 10 ml d'huile et les saupoudrer de 15 g de levure nutritionnelle.",
            "Servir la soupe bien chaude avec les croûtons.",
        ]),
        ("time", 15, 0, 60),
    ],

    # ── Tatin : de Lamotte-Beuvron / de poires à la cardamome vegan ──
    "dessert_tarte_tatin_9c0f67": [
        ("title", "Tarte Tatin de Lamotte-Beuvron au caramel beurre"),
        ("desc", "La tarte renversée des sœurs Tatin, en Sologne : pommes en quartiers épais confites dans un "
                 "caramel au beurre, couvertes de pâte brisée, cuites puis retournées tièdes."),
        ("origin", {"region": "centre_val_de_loire", "city": "lamotte_beuvron"}),
    ],
    "dessert_tarte_tatin_vegan_1ae13b": [
        ("title", "Tatin de poires à la cardamome, pâte feuilletée (vegan)"),
        ("desc", "Tarte renversée aux poires caramélisées au beurre végétal et à la cardamome, sous une pâte "
                 "feuilletée végétale croustillante."),
        ("compo", [
            ("pear_raw_with_skin", 1200, "g", "main_fruit"),
            ("vegan_butter", 70, "g", "fat"),
            ("white_sugar", 120, "g", "sweetener"),
            ("cardamom", 1, "g", "spice"),
            ("puff_pastry_vegetable_fat_raw_paste_plant", 200, "g", "dough_base"),
            ("base_soy_cream_4dc027", None, "2 cuillères à soupe", "serving_suggestion"),
        ]),
        ("steps", [
            "Éplucher 1,2 kg de poires fermes, les couper en deux et retirer le cœur.",
            "Faire fondre 70 g de beurre végétal avec 120 g de sucre dans une poêle allant au four, 6 minutes, jusqu'à obtenir un caramel blond, puis ajouter 1 g de cardamome moulue.",
            "Ranger les poires serrées, face bombée vers le bas, et les cuire 12 minutes à feu moyen en les arrosant de caramel.",
            "Préchauffer le four à 200°C. Couvrir de 200 g de pâte feuilletée en rentrant les bords.",
            "Cuire 25 minutes, laisser reposer 5 minutes, puis retourner sur un plat. Servir tiède.",
        ]),
        ("time", 20, 5, 45),
    ],

    # ── Gratin : dauphinois traditionnel / pommes de terre-poireaux vegan ──
    "gratin_dauphinois_classic_v3_p9x4t2": [
        ("dish", "side"),
        ("desc", "Le gratin du Dauphiné, sans fromage : fines lamelles de pommes de terre cuites lentement dans "
                 "la crème et le lait infusés à l'ail et à la muscade, jusqu'à une croûte dorée."),
        ("origin", {"region": "auvergne_rhone_alpes", "city": "grenoble"}),
    ],
    "side_dauphinois_vegan_c584cb": [
        ("title", "Gratin de pommes de terre et poireaux à la crème d'avoine (vegan)"),
        ("desc", "Gratin végétal fondant : pommes de terre et poireaux fondus en couches, crème et lait d'avoine "
                 "à l'ail et à la muscade, cuit jusqu'à ce que le dessus soit doré."),
        ("compo", [
            ("potato_raw_with_skin", 700, "g", "base"),
            ("leeks_raw", 300, "g", "vegetable"),
            ("base_oat_cream_954865", 250, "ml", "sauce"),
            ("oat_milk_refrigerated_plain_plant", 150, "ml", "sauce"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("nutmeg_spice", 1, "g", "spice"),
            ("thyme_dried_herb", 1, "g", "herb"),
            ("vegetable_oil_plant", 20, "ml", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Préchauffer le four à 180°C. Faire fondre 300 g de poireaux émincés dans 15 ml d'huile, 8 minutes.",
            "Couper 700 g de pommes de terre en lamelles de 3 mm.",
            "Chauffer 250 ml de crème d'avoine et 150 ml de lait d'avoine avec 9 g d'ail écrasé, 1 g de muscade, 1 g de thym, 4 g de sel et 1 g de poivre.",
            "Alterner pommes de terre et poireaux dans un plat huilé (5 ml), puis verser le mélange crémeux.",
            "Cuire 60 minutes, jusqu'à ce que les pommes de terre soient fondantes et le dessus doré.",
        ]),
        ("time", 20, 0, 70),
    ],

    # ── Soupes de courge : butternut rôtie / thaïe au lait de coco ──
    "soup_pumpkin_k2d1p1": [
        ("title", "Velouté de butternut rôtie aux graines de courge"),
        ("desc", "Butternut et oignon rôtis au four avant d'être mixés, pour un velouté au goût caramélisé, "
                 "servi avec des graines de courge grillées."),
        ("origin", {"cuisine": "french", "country": "france", "region": "", "city": ""}),
        ("steps", [
            "Préchauffer le four à 200°C. Couper 800 g de butternut en cubes de 4 cm et 120 g d'oignon en quartiers.",
            "Les mélanger avec 8 g d'ail, 20 ml d'huile et 3 g de sel, puis rôtir 35 minutes, jusqu'à ce que les bords soient caramélisés.",
            "Mixer les légumes rôtis avec 600 ml d'eau chaude, 2 g de sel et 2 g de poivre jusqu'à obtenir un velouté lisse, puis réchauffer 5 minutes.",
            "Griller 20 g de graines de courge à sec, 3 minutes à la poêle.",
            "Servir le velouté chaud, parsemé de graines de courge.",
        ]),
        ("time", 15, 0, 40),
    ],
    "soup_soupe_courge_butternut_2f5cf3": [
        ("title", "Soupe de butternut thaïe au lait de coco et au gingembre"),
        ("desc", "Soupe de courge butternut relevée de gingembre frais et de curry, adoucie au lait de coco, "
                 "parsemée de graines de courge."),
    ],

    # ── Soupes de lentilles : paysanne aux lentilles vertes / shorbat adas libanaise ──
    "dal_soupe_de_lentilles_621239": [
        ("title", "Soupe paysanne aux lentilles vertes et légumes"),
        ("desc", "Soupe rustique à la française : lentilles vertes, carotte, céleri et tomate mijotés avec thym "
                 "et laurier, non mixée."),
        ("origin", {"cuisine": "french", "country": "france", "region": "auvergne", "city": "le_puy_en_velay"}),
        ("dish", "soup"),
        ("compo", [
            ("green_lentil_dried", 150, "g", "base", "dried"),
            ("onion_raw", 120, "g", "aromatic"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("celery_stalk_raw", 80, "g", "vegetable"),
            ("tomato_raw_ripe", 200, "g", "vegetable"),
            ("thyme_dried_herb", 1, "g", "herb"),
            ("bay_leaf", 1, "g", "aromatic"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("vegetable_stock_dried", 10, "g", "seasoning"),
            ("water", 1100, "ml", "seasoning"),
            ("parsley_fresh_herb", 10, "g", "herb"),
        ]),
        ("steps", [
            "Faire revenir 120 g d'oignon, 150 g de carotte et 80 g de céleri en dés dans 20 ml d'huile d'olive, 6 minutes, puis ajouter 6 g d'ail.",
            "Ajouter 150 g de lentilles vertes rincées, 200 g de tomates concassées, 1 g de thym, 1 g de laurier, 1,1 L d'eau et 10 g de bouillon.",
            "Mijoter 35 minutes, jusqu'à ce que les lentilles soient tendres.",
            "Servir sans mixer, parsemé de 10 g de persil.",
        ]),
        ("time", 15, 0, 40),
    ],
    "dal_soupe_lentilles_turque_e797cb": [
        ("title", "Shorbat adas, soupe libanaise de lentilles corail au citron"),
        ("desc", "Soupe de lentilles corail du Levant, mixée et veloutée, parfumée au cumin, servie avec beaucoup "
                 "de citron et des oignons dorés."),
        ("origin", {"cuisine": "lebanese", "country": "lebanon", "region": "beyrouth", "city": "beyrouth"}),
        ("dish", "soup"),
        ("compo", [
            ("red_lentil_dried", 200, "g", "base", "dried"),
            ("yellow_onion_raw", 200, "g", "aromatic"),
            ("garlic_raw", 10, "g", "aromatic"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("cumin_spice_seed", 4, "g", "spice"),
            ("turmeric_powder", 1, "g", "spice"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("lemon_juice", 40, "ml", "condiment"),
            ("vegetable_stock_dried", 10, "g", "seasoning"),
            ("water", 1100, "ml", "seasoning"),
            ("parsley_fresh_herb", 10, "g", "herb"),
        ]),
        ("steps", [
            "Faire revenir 120 g d'oignon haché et 10 g d'ail dans 15 ml d'huile, 5 minutes, avec 4 g de cumin et 1 g de curcuma.",
            "Ajouter 200 g de lentilles corail, 150 g de carotte en dés, 1,1 L d'eau et 10 g de bouillon, puis mijoter 25 minutes.",
            "Mixer en velouté.",
            "Dorer 80 g d'oignon émincé dans 15 ml d'huile.",
            "Servir avec les oignons dorés, 10 g de persil et 40 ml de jus de citron.",
        ]),
        ("time", 10, 0, 30),
    ],

    # ── Terrines : printanière en gelée / provençale au chèvre ──
    "entry_terrine_de_legumes_e52466": [
        ("title", "Terrine de légumes printaniers en gelée au basilic"),
        ("desc", "Entrée légère : carottes, courgettes, haricots verts et poivron blanchis, pris dans une gelée "
                 "de bouillon à l'agar-agar parfumée au basilic, servie en tranches bien fraîches."),
    ],
    "entry_terrine_legumes_du_soleil_e5e24a": [
        ("title", "Terrine provençale de légumes grillés au chèvre"),
        ("desc", "Couches de poivrons, courgettes et aubergines grillés à l'huile d'olive et au thym, alternées "
                 "avec du chèvre frais, pressées une nuit et arrosées de balsamique."),
    ],
}
