"""Lot 16 : kibbeh, kimchi, korma, koshari, laing, légumes braisés."""

PATCHES = {
    "main_kibbeh_3d2be1": [
        ("add", "sunflower_oil_plant", 60, "ml", "fat_frying"),
        ("qty", "nutmeg_spice", 1),
        ("txt", "Frire dans l'huile d'olive à 175°C", "Frire dans un bain d'huile à 175°C"),
        ('qty', 'onion_raw', 300),
        ('txt', '(cannelle, cumin, piments de la Jamaïque)', '(cannelle, cumin, piment de la Jamaïque, muscade)'),
    ],
    "main_kimchi_1dc648": [
        ("flag", "kid_friendly", False),  # 20 g de piment coréen
        ("txt", "Servir sans attendre : la chaleur et le croustillant sont essentiels pour apprécier pleinement les saveurs et textures de ce kimchi.",
         "Conserver au réfrigérateur et servir frais, en accompagnement."),
        ("time", 15, 1560, 0),
    ],
    "main_korma_de_legumes_ddde08": [
        ("add", "water", 100, "ml", "liquid"),
        ("step-", "Présenter dans des bols préchauffés"),
    ],
    "main_koshari_classic_v4_q7n5z2": [
        ("ing", "coconut_oil_plant", "sunflower_oil_plant"),
        ("qty", "white_rice_raw_seed_unenriched", 250),
        ("qty", "pasta_raw_dried", 150),
        ("add", "cumin_spice_seed", 3, "g", "spice"),
        ("txt", "les 250g de lentilles corail 20 minutes, le 300g de riz long grain 12 minutes, les 200g de petites pâtes 8 minutes, en utilisant de l'huile de coco pour la cuisson.",
         "les 250g de lentilles vertes 25 minutes, les 250g de riz long grain 12 minutes, les 150g de petites pâtes 8 minutes."),
        ("txt", "faire frire dans 80ml d'huile de coco", "faire frire dans 80ml d'huile de tournesol"),
        ("txt", "faire revenir 20g d'ail 30 secondes dans de l'huile de coco", "faire revenir 20g d'ail 30 secondes dans un peu d'huile"),
        ("txt", "couche de lentilles corail", "couche de lentilles"),
        ("txt", " et parsemer de pois chiches si disponibles", ""),
    ],
    "main_laing_ee9d64": [
        ("txt", "Ajouter 9g d'ail haché et 15g de piment haché. Faire revenir pendant 2 minutes, jusqu'à ce que l'odeur soit parfumée.",
         "Ajouter 150 g d'oignon émincé, 9g d'ail haché et 15g de piment haché. Faire revenir pendant 5 minutes, jusqu'à ce que l'oignon soit doré et parfumé."),
        ("step-", "préalablement cuit à feu doux dans 30 ml d'huile de noix de coco"),
        ('qty', 'coconut_oil_plant', 15),
        ('qty', 'soy_sauce_shoyu_reduced_sodium', 20),
        ('qty', 'table_salt_unenriched', 2),
        ('txt', 'saler légèrement avec 5g de sel', 'saler légèrement avec 2g de sel'),
        ('txt', 'Ajouter 200 ml de lait de coco supplémentaire en fin de cuisson.', 'Ajouter 200 ml de lait de coco supplémentaire et 20 ml de sauce soja en fin de cuisson.'),
    ],
    "main_legumes_braises_7030b7": [
        ("txt", "et les oignons blancs en lamelles", "et l'oignon en lamelles"),
        ("txt", "puis ajouter l'ail et les herbes de Provence", "puis ajouter l'ail et la moitié du basilic ciselé"),
    ],
}
