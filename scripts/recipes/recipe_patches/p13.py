"""Lot 13 : gratin, bolani, ajvar, arepas, parmigiana, ziti, plats de légumes (A-C)."""

PATCHES = {
    "gratin_dauphinois_classic_v3_p9x4t2": [
        ("add", "nutmeg_spice", 0.5, "g", "spice"),
        ("txt", "puis huiler généreusement avec du beurre", "puis le beurrer généreusement"),
    ],
    "main_afghan_bolani_e66cba": [
        ("del", "tomato_raw_ripe"),
        ("add", "water", 120, "ml", "liquid"),
        ("txt", "mélanger 200g de farine avec 5g de sel et ajouter progressivement de l'eau", "mélanger 200g de farine avec 5g de sel et ajouter progressivement 120 ml d'eau"),
        ("txt", "Ajouter 300g de tomates concassées, 9g d'ail écrasé", "Ajouter 9g d'ail écrasé"),
        ("time", 17, 0, 25),
    ],
    # l'ajvar est majoritairement du poivron
    "main_ajvar_puree_de_poivrons_5d2e79": [
        ("qty", "red_bell_pepper_raw", 800),
        ("qty", "eggplant_raw", 300),
        ("txt", "Placez 320g de poivrons rouges entiers et 600g d'aubergines", "Placez 800g de poivrons rouges entiers et 300g d'aubergines"),
    ],
    "main_aloo_gobi_b21c85": [
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
    ],
    "main_aloo_palak_7e9377": [
        ("add", "ginger_raw_root_fresh", 10, "g", "aromatic"),
        ("add", "water", 100, "ml", "liquid"),
        ("txt", "Ajoutez 100 ml d'eau ou de lait de coco", "Ajoutez 100 ml d'eau"),
    ],
    "main_arepas_fromage_e3a54c": [
        ("ing", "parmesan_grated_dried_cow", "queso_fresco_block_cow", 80),
        ("add", "water", 250, "ml", "liquid"),
        ("txt", "incorporer 50 g de fromage râpé", "incorporer 80 g de fromage frais râpé"),
        ("txt", "puis enfourner les arepas pendant 5 minutes de chaque côté à 180°C", "puis cuire les arepas 5 minutes de chaque côté"),
    ],
    "main_arepas_fromage_vegan_3a4125": [
        ("add", "water", 250, "ml", "liquid"),
        ("serv", 4),
        ("txt", "avec de l'eau tiède salée (environ 30°C) additionnée", "avec 250 ml d'eau tiède salée additionnée"),
        ("step-", "Pour varier les saveurs"),
    ],
    "main_aubergines_parmigiana_sim_ad314c": [
        ("qty", "nutritional_yeast_flakes", 20),
        ("add", "basil_fresh_herb", 10, "g", "herb"),
        ("txt", "en utilisant environ 90 grammes de levure nutritionnelle", "en utilisant 20 grammes de levure nutritionnelle"),
        ("txt", "et que les aubergines soient tendres et al dente", "et que les aubergines soient tendres"),
    ],
    "main_aubergines_parmigiana_sim_e5028f": [
        ("qty", "table_salt_unenriched", 2),
        ("txt", "en les mélangeant avec amour et en ajustant l'assaisonnement selon vos goûts", "en ajustant l'assaisonnement selon vos goûts"),
        ("step-", "Conserver les restes au réfrigérateur"),
    ],
    "main_aubergines_sichuan_ff9921": [
        ("qty", "cornstarch", 10),
        ("txt", "Julienne 600g d'aubergines et blanchir dans 45 ml d'huile de sésame à feu moyen-vif pendant 2 minutes, jusqu'à légère coloration dorée.",
         "Couper 600g d'aubergines en bâtonnets et les faire sauter dans 45 ml d'huile de sésame à feu moyen-vif pendant 5 minutes, jusqu'à coloration dorée. Réserver."),
        ("txt", "Ajouter 20g de fécule de maïs pour épaissir la sauce", "Délayer 10g de fécule de maïs dans un peu d'eau froide et l'ajouter pour épaissir la sauce"),
        ("txt", "Servir chaud, parsemé de sauce soja et décoré", "Servir chaud, décoré"),
    ],
    "main_baingan_bharta_b5f900": [
        ("txt", "à feu moyen, jusqu'à brun doré. L'oignon devrait être translucide et parfumé.", "à feu moyen, jusqu'à ce qu'il soit doré et parfumé."),
        ("txt", "Vérifier que la sauce nappe la cuillère et rectifier", "Saler avec 5 g de sel, vérifier que la sauce nappe la cuillère et rectifier"),
        ("txt", "Servir aussitôt dans des bols préchauffés, garni de coriandre ciselée et d'un filet d'huile d'olive extra vierge.",
         "Servir aussitôt, garni de coriandre ciselée."),
    ],
    "main_baked_ziti_b9e13e": [
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Ajouter 400g de sauce tomate et assaisonner avec 5g de sel.",
         "Ajouter 400g de sauce tomate et 240g de tomates fraîches concassées, puis assaisonner avec 2g de sel."),
    ],
    "main_baked_ziti_vegan_ad57f8": [
        ("qty", "nutritional_yeast_flakes", 20),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "les 400g de sauce tomate et les 5g de sel", "les 400g de sauce tomate, les 240g de tomates fraîches concassées et 2g de sel"),
        ("txt", "saupoudrer des 90g de levure nutritionnelle", "saupoudrer de 20g de levure nutritionnelle"),
    ],
    "main_banane_caramelisee_philip_df163c": [
        ("qty", "table_salt_unenriched", 1),
        ("qty", "white_sugar", 40),
        ("qty", "sunflower_oil_plant", 30),
        ("txt", "Saupoudrez légèrement de sucre blanc sur les faces coupées", "Saupoudrez 40 g de sucre sur les faces coupées"),
        ("txt", "Chauffez 45 ml d'huile de tournesol", "Chauffez 30 ml d'huile de tournesol"),
        ("txt", ", accompagné de riz gluant ou de crudités fraîches", ", accompagné de riz gluant"),
        ("step-", "Pour conserver les bananes caramélisées"),
    ],
    "main_batata_harra_c2de57": [
        ("ing", "lemon_raw", "lemon_juice", 30, "ml"),
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
        ("txt", "et le jus de 100g de citron frais", "et 30 ml de jus de citron"),
        ("txt", "garni d'un filet d'huile d'olive et de quelques feuilles de persil frais pour une présentation appetissante",
         "garni d'un filet d'huile d'olive et de coriandre fraîche ciselée"),
    ],
    "main_beignets_de_legumes_indon_e74ee9": [
        ("add", "water", 200, "ml", "liquid"),
        ("qty", "sunflower_oil_plant", 60),
        ("dish", "snack"),
        ("txt", "3g de coriandre moulue avec de l'eau", "3g de coriandre moulue avec 200 ml d'eau"),
        ("txt", "Chauffer 500ml d'huile de friture végétale à 170°C", "Chauffer un bain d'huile de friture à 170°C"),
    ],
    "main_bhindi_masala_ade89d": [
        ("ing", "coriander_spice_leaf_dried", "coriander_spice_seed"),
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
    ],
    "main_bissara_23c21a": [
        ("add", "water", 900, "ml", "liquid"),
        ("ing", "lemon_raw", "lemon_juice", 30, "ml"),
        ("txt", "Faire blanchir les fèves sèches pendant 5 minutes à feu moyen, en les remuant régulièrement, jusqu'à ce qu'elles soient tendres et légèrement ramollies.",
         "Faire tremper les fèves sèches une nuit dans de l'eau froide, puis les égoutter."),
        ("txt", "Assaisonner de sel et de cumin. Servir sans attendre, garni de citron et de levure nutritionnelle râpée pour un parfum umami.",
         "Assaisonner de sel et de cumin. Servir sans attendre, arrosé de 30 ml de jus de citron et saupoudré de cumin."),
        ("time", 13, 480, 55),
    ],
    "main_bohemienne_provencale_781b61": [
        ("txt", "Ajouter les tomates fraîches concassées, le thym frais et le basilic frais.", "Ajouter le poivron rouge en lanières, les tomates fraîches concassées et le thym frais."),
        ("txt", "Assaisonner et terminer avec des feuilles de basilic frais déchirées.", "Assaisonner avec 5 g de sel et terminer avec des feuilles de basilic frais déchirées."),
    ],
    "main_briam_f33bb8": [
        ("txt", "Servir tiède avec du pain et du fromage végétal râpé, en remplacement du fromage feta traditionnel.", "Servir tiède avec du pain."),
        ("time", 17, 0, 60),
    ],
    "main_bulgarian_shopska_salad_d473eb": [
        ("dish", "starter"),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "une pointe de vinaigre de vin blanc (30 ml), du sel (5g)", "une pointe de vinaigre blanc (30 ml), du sel (2g)"),
    ],
    "main_caldo_verde_72b654": [
        ("qty", "table_salt_unenriched", 2),
    ],
}
