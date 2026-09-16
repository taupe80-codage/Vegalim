"""Lot 12 : entrées (fromage de cajou → œufs en meurette) et falafels."""

PATCHES = {
    "entry_fromage_de_cajou_aux_herb_4f0f9b": [
        ("ing", "cashew_nuts_roasted_in_oil", "cashew_nuts_raw"),
        ("txt", ", avec une texture molle et une légère fermentation", ", avec une texture molle"),
        ("txt", "5g d'herbes de Provence séchées", "5g de thym séché"),
        ("txt", "Rouler le cylindre dans les herbes de Provence séchées", "Rouler le cylindre dans un peu de thym séché"),
        ("txt", "Servir aussitôt, garni de ciboulette ciselée et d'un filet d'huile d'olive. Accompagner d'un pain pita tiède ou de riz basmati.",
         "Servir frais, avec du pain grillé ou des crudités."),
    ],
    "entry_gaspacho_de_melon_menthe_ee9907": [
        ("txt", "15ml de vinaigre de xérès", "15ml de vinaigre de vin rouge"),
    ],
    "entry_haricots_verts_amandine_391638": [
        ("ing", "lemon", "lemon_juice", 20, "ml"),
        ("txt", "jus de citron (en utilisant 50g de citron)", "20 ml de jus de citron"),
        ("txt", "Servir aussitôt, garni de quelques feuilles de persil frais pour une touche de couleur et de fraîcheur.", "Servir aussitôt."),
    ],
    # salade tiède transformée en soupe par l'ajout de bouillon à la fin
    "entry_lentilles_beluga_au_xeres_de4a76": [
        ("txt", "Rincez 200g de lentilles beluga, puis cuisez-les pendant 25 minutes à feu moyen dans 600ml d'eau salée",
         "Rincez 200g de lentilles vertes (ou beluga), puis cuisez-les pendant 25 minutes à feu moyen dans 500 ml de bouillon de légumes"),
        ("txt", "15ml de vinaigre de xérès", "15ml de vinaigre"),
        ("step-", "Ajoutez 500ml de bouillon de légumes et mélangez bien"),
        ("txt", "Servez la soupe tiède", "Servez la salade tiède"),
    ],
    "entry_matbucha_fbcb0e": [
        ("qty", "tomato_raw_ripe", 300),
        ("add", "parsley_fresh_herb", 10, "g", "herb"),
        ("txt", "Ajouter 480 g de tomates pelées concassées", "Ajouter 300 g de tomates pelées concassées"),
    ],
    "entry_mousse_avocat_wasabi_773105": [
        ("txt", "Coupez 3 avocats en deux", "Coupez 400 g d'avocats en deux"),
        ("txt", "50ml de crème de coco", "50ml de lait de coco"),
    ],
    "entry_muhammara_cd05ca": [
        ("txt", "la mélasse de grenade", "le jus de grenade"),
    ],
    "entry_rillettes_lentilles_corai_40d7dc": [
        ("qty", "shallot_raw", 60),
    ],
    "entry_skordalia_18cd77": [
        ("ing", "white_bread_roasted", "white_bread_unsalted"),
        ("qty", "olive_oil_plant", 60),
        ("txt", "Ajouter progressivement 100 millilitres d'huile d'olive", "Ajouter progressivement 60 millilitres d'huile d'olive"),
    ],
    "entry_souffle_au_fromage_64984b": [
        ("txt", "pour faire une roux", "pour faire un roux"),
        ("txt", "Monte les blancs d'œufs", "Montez les blancs d'œufs"),
        ("txt", "Démoulez le soufflé chaud et servez-le dans des assiettes préchauffées, accompagné", "Servez aussitôt à la sortie du four, accompagné"),
    ],
    "entry_tapenade_d_olives_noires_ed6d5d": [
        ("qty", "black_olive_canned_in_oil", 120),
        ("qty", "capers_canned_in_vinegar", 20),
        ("qty", "olive_oil_extra_virgin_plant", 30),
        ("txt", "Égoutter 200g d'olives noires et 30g de câpres", "Égoutter 120g d'olives noires et 20g de câpres"),
        ("txt", "en ajoutant en filet 61.5ml d'huile d'olive extra-vierge", "en ajoutant en filet 30ml d'huile d'olive extra-vierge"),
    ],
    "entry_terrine_legumes_du_soleil_e5e24a": [
        ("txt", "les courgettes jaunes et les aubergines noires", "les courgettes et les aubergines"),
        ("txt", "d'herbes de Provence, d'huile d'olive, de sel de Guérande", "de thym séché, d'huile d'olive, de sel"),
        ("txt", " Servez sans attendre, en vous assurant que les tranches soient servies à température ambiante pour profiter des saveurs et des textures.", ""),
    ],
    "entry_tzatziki_grec_2b21fb": [
        ("qty", "table_salt_unenriched", 3),
        ("txt", "assaisonnez-le de 3g de sel de table", "assaisonnez-le d'un peu de sel"),
        ("txt", "Servez le tzatziki à température ambiante", "Servez le tzatziki bien frais"),
    ],
    "entry_veloute_potimarron_en_ver_e5a2ca": [
        ("title", "Velouté de butternut en verrine"),
        ("txt", "Éplucher le potimarron", "Éplucher la courge butternut"),
        ("txt", "Ajouter les cubes de potimarron", "Ajouter les cubes de courge"),
        ("txt", "puis enfourner pendant 25 minutes à 180°C, jusqu'à ce que le potimarron soit tendre",
         "puis laisser mijoter 25 minutes à couvert, jusqu'à ce que la courge soit tendre"),
        ("txt", "Mixer le mélange de potimarron et de bouillon", "Mixer la courge et le bouillon"),
        ("txt", "Incorporer la crème de coco", "Incorporer le lait de coco"),
    ],
    "entry_white_bean_dip_ail_roti_e61590": [
        ("qty", "garlic_raw", 40),
        ("txt", "Servir sans attendre, en garnissant de persil frais si désiré, pour profiter de la chaleur et de la fraîcheur de la dip.",
         "Servir frais ou à température ambiante, garni de persil."),
    ],
    "entry_Œufs_en_meurette_b8fce3": [
        ("add", "table_salt_unenriched", 3, "g", "seasoning"),
        ("add", "bay_leaf_spice", 1, "g", "herb"),
        ("txt", "40g de beurre froide", "40g de beurre froid"),
        ("txt", "pendant 3 minutes, jusqu'à coagulation complète", "pendant 3 minutes, jusqu'à ce que le blanc soit pris et le jaune encore coulant"),
    ],
    "falafel_bowl_de_falafel_vegan_f4fd40": [
        ("add", "garlic_raw", 12, "g", "aromatic"),
        ("add", "parsley_fresh_herb", 15, "g", "herb"),
        ("add", "cumin_spice_seed", 2.5, "g", "spice"),
        ("add", "water", 300, "ml", "liquid"),
        ("ing", "lemon_raw", "lemon_juice", 30, "ml"),
        ("qty", "white_rice_raw_seed_unenriched", 200),
        ("txt", "Cuire 300 g de riz à la méthode absorption (450 ml d'eau", "Cuire 200 g de riz à la méthode absorption (300 ml d'eau"),
        ("txt", "les 200 g de tofu soyeux coupé en cubes", "les 200 g de tofu soyeux en cuillerées"),
        ("time", 17, 0, 25),
    ],
    "falafel_optimise_2f1451": [
        ("qty", "coriander_raw_fresh_herb", 40),
        ("qty", "sunflower_oil_plant", 60),
        ("txt", "20 g de persil frais, 15 g de coriandre fraîche", "20 g de persil frais, 40 g de coriandre fraîche"),
        ("txt", "Incorporer 125 g de coriandre fraîche et réfrigérer pendant 30 minutes", "Réfrigérer pendant 30 minutes"),
        ("txt", "Chauffer 500 ml d'huile de tournesol à 175°C", "Chauffer un bain d'huile de tournesol à 175°C"),
        ("step-", "Pour une présentation plus appétissante, vous pouvez ajouter des feuilles de persil"),
        ("step-", "Pour une variante plus épicée"),
        ("step-", "Pour conserver les falafels"),
        ("step-", "Pour réchauffer les falafels"),
    ],
}
