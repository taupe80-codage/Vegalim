"""Lot 17 : lobio, manakish, zaalouk, moussaka, plats népalais, parmigiana, pav bhaji."""

PATCHES = {
    "main_lobio_5cdec6": [
        ("qty", "pomegranate_raw", 80),
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
        ("txt", "mijoter 10 minutes à 80°C", "mijoter 10 minutes à feu doux"),
        ("txt", "garnir de 280g de graines de grenade", "garnir de 80g de graines de grenade"),
    ],
    "main_manakish_zaatar_580150": [
        ("add", "water", 100, "ml", "liquid"),
        ("serv", 4),
        ("time", 13, 60, 10),
    ],
    "main_mexican_enfrijoladas_vega_d6a9a8": [
        ("txt", "Ajouter une touche de 20 ml de crème de coco", "Ajouter 20 ml de lait de coco"),
    ],
    "main_moroccan_zaalouk_d90202": [
        ("del", "onion_raw"),
        ("ing", "lemon_raw", "lemon_juice", 30, "ml"),
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
        ("txt", "Faire revenir l'ail et l'oignon dans l'huile d'olive", "Faire revenir l'ail dans l'huile d'olive"),
        ('dish', 'side'),
    ],
    # moussaka végétalienne sans aucune protéine : lentilles ajoutées à la sauce
    "main_moussaka_fcf86b": [
        ("add", "green_lentil_dried", 100, "g", "plant_protein"),
        ("add", "water", 300, "ml", "liquid"),
        ("txt", "puis en ajoutant 300 g de tomates concassées. Cuire pendant 10 minutes à feu doux",
         "puis en ajoutant 100 g de lentilles vertes rincées, 300 g de tomates concassées et 300 ml d'eau. Cuire pendant 25 minutes à feu doux"),
        ("txt", "Servir chaud, dans des assiettes préchauffées, en garnissant", "Servir chaud, en garnissant"),
        ("time", 13, 0, 55),
    ],
    "main_nepali_aloo_tama_4664a3": [
        ("ing", "olive_oil_extra_virgin_plant", "sunflower_oil_plant"),
        ("add", "water", 400, "ml", "liquid"),
        ("txt", "Chauffer 45ml d'huile d'olive extra vierge à feu moyen", "Chauffer 45ml d'huile de tournesol à feu moyen"),
        ("txt", "Couvrir d'eau à hauteur des ingrédients", "Couvrir de 400 ml d'eau"),
    ],
    "main_nepali_saag_92a5f7": [
        ("del", "mustard"),
        ("txt", "Incorporer 3g de curcuma et 3g de cumin.", "Incorporer 3g de curcuma."),
    ],
    "main_nepali_tarkari_9199c8": [
        ("qty", "sunflower_oil_plant", 30),
    ],
    "main_nepali_tomato_achar_9575d1": [
        ("qty", "eggplant_raw", 200),
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
    ],
    "main_papaya_salad_918f58": [
        ("ing", "lime_raw", "lime_juice_fresh", 40, "ml"),
        ("del", "white_sugar"),
        ("qty", "french_bean_raw", 150),
        ("txt", "Ajouter 300g de haricots verts coupés en deux", "Ajouter 150g de haricots verts coupés en deux"),
        ("txt", "10g de sucre de coco et 140g de jus de citron vert", "10g de sucre de coco et 40 ml de jus de citron vert"),
        ('del', 'tomato_raw_ripe'),
        ('txt', '200g de tomates cerises et 240g de tomates coupées en dés', '200g de tomates cerises coupées en deux'),
    ],
    "main_parmigiana_di_melanzane_6bd49f": [
        ("qty", "table_salt_unenriched", 2),
        ("txt", "puis en ajoutant 240g de tomates concassées et 150g d'oignon émincé. Cuire pendant 12 minutes à 180°C",
         "puis en ajoutant 240g de tomates concassées, 400g de sauce tomate et l'oignon émincé. Cuire pendant 12 minutes à feu moyen"),
        ("step-", "Ajouter un peu de poivre pour relever le goût"),
        ("step-", "Pour une présentation élégante, garnir de feuilles de basilic frais et de tranches de citron"),
        ('txt', "d'aubergines, de mozzarella et de parmesan", "d'aubergines, de mozzarella, de feuilles de basilic et de parmesan"),
    ],
    "main_parmigiana_di_melanzane_v_8f8b8b": [
        ("qty", "nutritional_yeast_flakes", 20),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "puis en ajoutant les tomates concassées, le sel et le poivre", "puis en ajoutant l'oignon émincé, les tomates concassées, le sel et le poivre"),
        ("txt", "et que les aubergines soient tendres et al dente, signe d'une cuisson parfaite", "et que les aubergines soient tendres"),
        ('qty', 'olive_oil_plant', 45),
        ('txt', "puis d'une couche de fromage végétal râpé, en alternant", "puis de feuilles de basilic et d'une couche de fromage végétal râpé, en alternant"),
    ],
    "main_patatas_bravas_98ec00": [
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Nacrez les pommes de terre avec la sauce brava chaude", "Nappez les pommes de terre de sauce brava chaude"),
    ],
    "main_pav_bhaji_e99df8": [
        ("ing", "snow_peas_raw", "green_peas_boiled_frozen_salted"),
        ("add", "water", 150, "ml", "liquid"),
        ("txt", "600g de pommes de terre et 200g de pois à la vapeur", "600g de pommes de terre et 200g de petits pois à la vapeur"),
        ("txt", "Ajoutez un peu d'eau et laissez mijoter", "Ajoutez 150 ml d'eau et laissez mijoter"),
    ],
    "main_pav_bhaji_vegan_c1437e": [
        ("ing", "snow_peas_raw", "green_peas_boiled_frozen_salted"),
        ("txt", "les pois mangetout de 200g", "les petits pois de 200g"),
    ],
}
