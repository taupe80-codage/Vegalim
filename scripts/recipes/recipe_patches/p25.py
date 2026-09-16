"""Lot 25 : tofu braisé, teriyaki, pâte de curry, bibimbap, bigos, biryani, riz."""

PATCHES = {
    "protein_tofu_braise_aux_champigno_c515dd": [
        ("qty", "water", 150),
        ("qty", "vegetable_stock_dried", 2),
        ("qty", "cornstarch", 10),
        ("add", "sesame_raw_seed", 10, "g", "garnish"),
        ("txt", "Ajouter 20 g de fécule de maïs délayée", "Ajouter 10 g de fécule de maïs délayée"),
    ],
    "protein_tofu_teriyaki_ffcb47": [
        ("qty", "coconut_oil_plant", 20),
        ("add", "coconut_sugar", 10, "g", "sweetener"),
        ("txt", "Préparer la sauce teriyaki végane en mélangeant 40 ml de sauce teriyaki, 30 ml d'huile de coco et 10 g de sucre de coco dans un bol",
         "Préparer la sauce en mélangeant 60 ml de sauce teriyaki et 10 g de sucre de coco dans un bol"),
        ("txt", "servir le tofu doré sur un lit de riz japonais, avec des rondelles de concombre frais et des feuilles de menthe pour un contraste de textures et de saveurs",
         "servir le tofu doré sur un lit de riz japonais"),
        ("time", 9, 20, 25),
    ],
    "red_curry_paste_3ee8f5": [
        ("ing", "red_hot_chili_pepper_raw", "red_hot_chili_pepper_spice_dried", 15),
        ("txt", "Faites tremper 40g de piments rouges séchés", "Faites tremper 15g de piments rouges séchés"),
        ("step-", "Servir la pâte de curry rouge thaï dans un bol"),
    ],
    "rice_bibimbap_classic_k91x2a": [
        ("add", "sesame_oil_plant", 20, "ml", "fat"),
        ("add", "soy_sauce_shoyu_reduced_sodium", 20, "ml", "condiment"),
        ("qty", "garlic_raw", 10),
        ("flag", "gluten_free", False),  # gochujang
        ("txt", "sauter les carottes crues en julienne fine pendant 2 minutes à feu vif", "sauter les carottes et la courgette en julienne fine 2 minutes à feu vif"),
        ("txt", "Faire frire un œuf au plat pour obtenir un jaune coulant", "Faire frire 4 œufs au plat (220 g) pour obtenir des jaunes coulants"),
        ("txt", "Ajouter des gousses d'ail émincées pour une saveur plus intense.", "Ajouter l'ail émincé aux légumes sautés et un filet de sauce soja."),
    ],
    "rice_bibimbap_tofu_a265dc": [
        ("txt", "Ajouter une cuillerée à soupe de gochujang, un filet d'huile de sésame et parsemer de graines de sésame.",
         "Déposer un œuf au plat par bol (220 g au total), ajouter une cuillerée de gochujang, un filet d'huile de sésame et parsemer de graines de sésame."),
    ],
    # le bigos ne contient pas de riz (300 g de riz cru comptés)
    "rice_bigos_497b21": [
        ("del", "white_rice_raw_seed_unenriched"),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Ajouter le riz cuit et mélanger bien pour que les saveurs se mélangent. Servir chaud, garni de levure nutritionnelle râpée pour un parfum umami.",
         "Rectifier l'assaisonnement et servir chaud, avec du pain de seigle."),
        ("time", 21, 0, 60),
    ],
    "rice_biryani_classic_k82x7b": [
        ("qty", "table_salt_unenriched", 5),
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
        ("txt", "Cuire dans 1,5 L d'eau bouillante fortement salée", "Cuire dans 1,5 L d'eau bouillante salée"),
        ("txt", "Cuire à feu très doux pendant 25 minutes à 180°C", "Cuire à feu très doux pendant 25 minutes"),
    ],
    "rice_bun_cha_e5c855": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 10),
        ("add", "table_salt_unenriched", 3, "g", "seasoning"),
        ("txt", "Faites cuire les vermicelles de riz pendant 12 minutes à feu doux, en remuant régulièrement pour éviter leur collage, jusqu'à absorption complète de l'eau et texture tendre.",
         "Faites cuire les vermicelles de riz 4 minutes dans l'eau bouillante, puis rincez-les à l'eau froide et égouttez-les."),
        ("txt", "Blanchissez les légumes (laitue, menthe, concombre, carotte) pendant 2 minutes à l'eau bouillante, puis rincez-les à l'eau froide pour conserver leur texture croquante et leur fraîcheur, puis égouttez-les sur un papier absorbant.",
         "Lavez la laitue et la menthe, taillez le concombre en rondelles et la carotte en julienne, puis réservez le tout au frais."),
        ("txt", "Ajoutez le coriandre moulue, l'ail émincé", "Ajoutez la coriandre ciselée, l'ail émincé"),
    ],
    "rice_crepe_vietnamienne_71beca": [
        ("add", "water", 150, "ml", "liquid"),
        ("add", "coconut_oil_plant", 20, "ml", "fat"),
        ("txt", "200 g de tofu ferme en dés", "400 g de tofu ferme en dés"),
    ],
    "rice_dolma_au_persil_6aeb1e": [
        ("qty", "white_rice_short_grain_seed_dried", 150),
    ],
    "rice_donburi_tofu_teriyaki_a71cfc": [
        ("ing", "coconut_oil_plant", "sunflower_oil_plant"),
        ("txt", "Chauffer les 45 ml d'huile de coco", "Chauffer les 45 ml d'huile de tournesol"),
        ("txt", "pour préserver la texture croustillante du tofu et la crémeuse du riz", "pour préserver la texture croustillante du tofu"),
    ],
    "rice_fried_rice_chinois_vegan_c2b92d": [
        ("qty", "sesame_oil_plant", 15),
        ("add", "sunflower_oil_plant", 30, "ml", "fat"),
        ("txt", "Chauffer 45,7 ml d'huile de sésame dans le wok", "Chauffer 30 ml d'huile de tournesol dans le wok"),
    ],
    "rice_goi_cuon_efb313": [
        ("del", "garlic_raw"),
        ("add", "soy_sauce_shoyu_reduced_sodium", 20, "ml", "condiment"),
        ("txt", "et blanchissez-les pendant 3 minutes à l'eau bouillante salée, jusqu'à ce qu'elles soient tendres mais encore croquantes, puis plongez-les dans un bain d'eau glacée pour arrêter la cuisson",
         "et réservez-les crues pour garder leur croquant"),
    ],
    "rice_jeera_rice_a4633c": [
        ("add", "water", 450, "ml", "liquid"),
        ("txt", "avec l'huile de coco parfumée au cumin", "avec le beurre parfumé au cumin"),
        ("txt", "Verser 450 ml d'eau bouillante salée (1,5 fois le volume du riz)", "Verser 450 ml d'eau bouillante (1,5 fois le volume du riz)"),
    ],
    "rice_karelian_pies_106cca": [
        ("qty", "water", 200),
        ("qty", "white_rice_short_grain_seed_dried", 150),
        ("qty", "milk_liquid_uht_3_5pct", 500),
        ("txt", "avec 500ml d'eau et 5g de sel", "avec 200ml d'eau et 5g de sel"),
        ("txt", "en cuisant 300g de riz dans 250ml de lait 15 min à feu doux", "en cuisant 150g de riz dans 500 ml de lait 25 min à feu doux"),
        ("txt", "Servir chaud, en accompagnant de salade ou de légumes pour un repas complet.",
         "Servir chaud avec le « beurre d'œuf » : écraser 220 g d'œufs durs avec une pincée de sel."),
    ],
    "rice_kimbap_4cb3da": [
        ("qty", "spinach_raw_mature", 200),
        ("qty", "garlic_raw", 10),
        ("txt", "Faire sauter 300g d'épinards, 200g de carottes et 20g d'ail haché", "Faire sauter 200g d'épinards, 200g de carottes et 10g d'ail haché"),
        ("txt", "nacrer le riz pour obtenir une texture lisse et homogène", "presser légèrement le riz pour obtenir une couche régulière"),
        ("txt", "Disposer les garnitures en ligne au bas du riz, ciseler les légumes en julienne fine pour une texture variée.",
         "Préparer une omelette fine avec les 220 g d'œufs, la couper en lanières, puis disposer les garnitures (légumes en julienne, concombre et omelette) en ligne au bas du riz."),
        ("txt", "avec une sauce au soja et du wasabi", "avec une sauce au soja"),
    ],
}
