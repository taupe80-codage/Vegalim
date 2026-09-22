"""Lot 24 : gado-gado, mapo tofu, moqueca, pad thaï, palak/paneer véganes, tikka."""

PATCHES = {
    "protein_gadogado_indonesien_200c65": [
        ("del", "butter_sup80pct"),
        ("ing", "lime_raw", "lime_juice_fresh", 30, "ml"),
        ("add", "water", 100, "ml", "liquid"),
        ("txt", "la sauce soja de 45ml et le jus de citron vert de 140g", "la sauce soja de 45ml et 30 ml de jus de citron vert"),
        ("step-", "Ajouter 30 g de beurre fondu pour lier la sauce cacahuète"),
        ("step-", "Ajouter des légumes supplémentaires tels que des carottes"),
    ],
    "protein_mapo_tofu_4b4458": [
        ("add", "cornstarch", 8, "g", "thickener"),
        ("add", "water", 200, "ml", "liquid"),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Ajouter les 20 g de sauce aux haricots noirs fermentés", "Ajouter les 20 g de pâte de piment fermentée"),
        ("txt", "Servir sans attendre dans des bols préchauffés, garni", "Servir sans attendre, garni"),
    ],
    "protein_moqueca_a65174": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 10),
        ("ing", "lime_raw", "lime_juice_fresh", 30, "ml"),
        ("add", "vegetable_stock_dried", 1.3, "g", "ingredient"),
        ("add", "water", 100, "ml", "liquid"),
        ("txt", "Presser le jus d'un citron vert frais hors du feu et incorporer 3 g de coriandre ciselée",
         "Ajouter 30 ml de jus de citron vert hors du feu et incorporer 10 g de coriandre ciselée"),
    ],
    "protein_pad_thai_vegan_33c0f3": [
        ("txt", "200g de vermicelles de riz larges", "200g de vermicelles de riz"),
        ("txt", "20g de sucre de coco et 15ml de jus de citron vert.", "20g de sucre de coco, 15ml de jus de citron vert et 15 ml de sauce poisson végétale."),
    ],
    "protein_palak_paneer_vegan_bdac46": [
        ("txt", "Blanchir les épinards crus pendant 2 minutes à 90°C", "Blanchir les épinards crus 2 minutes dans l'eau bouillante"),
        ("txt", "servir chaud, dans des bols préchauffés, garni de coriandre ciselée et d'un filet d'huile végétale. Accompagner d'un pain pita tiède ou de riz basmati pour un repas complet et équilibré.",
         "servir chaud, accompagné de riz basmati ou de naan."),
    ],
    "protein_paneer_butter_masala_vega_6c63de": [
        ("txt", "Incorporer la crème de coco", "Incorporer le lait de coco"),
        ("txt", ", avec un léger croquant des oignons caramélisés", ""),
        ("step-", "Ajouter l'huile d'olive pour donner une texture onctueuse"),
        ("time", 23, 0, 20),
        ('txt', 'les épices cardamom, cinnamon, cumin et garam masala', '2 g de cardamome, 2,3 g de cannelle, 2,5 g de cumin et 2,5 g de garam masala'),
        ('txt', 'Assaisonner avec du sel et servir sans attendre, en vérifiant que les saveurs sont équilibrées et que la texture est onctueuse et crémeuse.', 'Assaisonner avec 5 g de sel.'),
        ('txt', 'Servir chaud, en garnissant de coriandre fraîche et en vérifiant que les saveurs sont équilibrées et que la sauce a une couleur riche et intense.', 'Servir chaud, garni de 10 g de coriandre fraîche.'),
    ],
    "protein_paneer_tikka_94f80a": [
        ("ing", "lemon_raw", "lemon_juice", 30, "ml"),
        ("add", "table_salt_unenriched", 3, "g", "seasoning"),
        ("txt", "Couper le fromage en cubes", "Couper le paneer en cubes"),
        ("step-", "Ajouter un mélange d'épices composé de cumin, de garam masala et de paprika"),
    ],
    "protein_paneer_tikka_vegan_8bf0a0": [
        ("ing", "lemon_raw", "lemon_juice", 30, "ml"),
        ("add", "table_salt_unenriched", 3, "g", "seasoning"),
        ("txt", "Faire cuire les brochettes pendant 3 minutes à feu vif, en les retournant régulièrement, jusqu'à ce qu'elles soient bien dorées et croustillantes.",
         "Passer les brochettes 3 minutes sous le gril, en les retournant, jusqu'à ce qu'elles soient bien dorées."),
        ("time", 21, 45, 15),
        ('qty', 'olive_oil_extra_virgin_plant', 45),
        ('txt', "Badigeonner les brochettes avec 45,7ml d'huile d'olive et servir sans attendre : la chaleur et le croustillant sont essentiels pour apprécier pleinement les saveurs.", "Badigeonner les brochettes de 45 ml d'huile d'olive et servir sans attendre."),
        ('step-', 'Garnir avec des herbes fraîches et vérifier'),
    ],
}
