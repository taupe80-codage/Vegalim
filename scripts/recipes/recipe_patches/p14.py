"""Lot 14 : plats de légumes (callaloo → gözleme)."""

PATCHES = {
    "main_callaloo_f7ae5c": [
        ("txt", "3g de thym frais haché", "3g de thym séché"),
        ("txt", "Retirer le piment scotch bonnet entier (si utilisé) et écraser légèrement", "Écraser légèrement"),
        ("txt", "de ce ragoût indien", "de ce ragoût caribéen"),
    ],
    "main_caponata_d15a4f": [
        ("add", "table_salt_unenriched", 3, "g", "seasoning"),
        ("txt", "Ciselez les aubergines en cubes de 2 cm", "Coupez les aubergines en cubes de 2 cm"),
        ("txt", "Nacrez les oignons blancs émincés à feu moyen", "Faites revenir l'oignon émincé à feu moyen"),
        ("txt", "Juliennez les tomates concassées et ajoutez-les à la poêle", "Ajoutez les tomates concassées à la poêle"),
        ("txt", "Brounoisez les olives noires et les câpres", "Hachez grossièrement les olives noires et les câpres"),
        ("txt", "Émulsionnez la sauce avec le vinaigre rouge et le sucre, en la fouettant jusqu'à obtention d'une texture lisse et d'un équilibre sucré-acidulé bien marqué.",
         "Ajoutez le vinaigre de vin rouge et le sucre, puis laissez réduire 2 minutes jusqu'à obtenir un équilibre sucré-acidulé bien marqué."),
        ("txt", "Ajoutez l'huile d'olive et le sel pour rehausser les saveurs, puis servez", "Ajoutez 3 g de sel pour rehausser les saveurs, puis servez"),
    ],
    "main_carottes_glacees_a_lerabl_87d5f0": [
        ("qty", "carrot_raw", 600),
        ("add", "water", 50, "ml", "liquid"),
        ("txt", "Peler 200 g de carottes crues", "Peler 600 g de carottes"),
    ],
    "main_caviar_d_aubergine_0e824d": [
        ("ing", "lemon_raw", "lemon_juice", 30, "ml"),
        ("add", "paprika_powder", 2, "g", "spice"),
        ("step-", "Servir sans attendre, car la chaleur et le croustillant du pain pita"),
    ],
    "main_chili_sin_carne_125ff2": [
        ("txt", "Assaisonner avec de la coriandre fraîche ciselée et servir chaud", "Saler avec 5 g de sel, parsemer de coriandre fraîche ciselée et servir chaud"),
    ],
    "main_chou_farci_vegetarien_7a01f5": [
        ("add", "olive_oil_plant", 30, "ml", "fat"),
        ("txt", "pendant 5 minutes à feu moyen dans de l'huile d'olive, en remuant régulièrement", "pendant 5 minutes à feu moyen dans 20 ml d'huile d'olive, en remuant régulièrement"),
        ("txt", "Faire dorer les choux farcis pendant 5 minutes à feu moyen dans de l'huile d'olive", "Faire dorer les choux farcis pendant 5 minutes à feu moyen dans 10 ml d'huile d'olive"),
    ],
    "main_choucroute_vegetarienne_25c7a3": [
        ("qty", "olive_oil_plant", 20),
        ("add", "table_salt_unenriched", 3, "g", "seasoning"),
        ("flag", "kid_friendly", False),  # 200 ml de vin blanc
        ("txt", "les baies de genièvre et le vin blanc sec", "les baies de genièvre, le carvi et le vin blanc sec"),
    ],
    "main_crepe_complete_1d0fb7": [
        ("add", "water", 500, "ml", "liquid"),
        ("add", "table_salt_unenriched", 5, "g", "seasoning"),
        ("dish", "main"),
        ("txt", "Retourner la galette et déposer le fromage râpé en laissant 2 cm de bord.",
         "Retourner la galette, casser l'œuf au centre et déposer le fromage râpé autour en laissant 2 cm de bord."),
    ],
    "main_crumble_aux_myrtilles_5f7d47": [
        ("qty", "blueberry", 500),
        ("qty", "wheat_all_purpose_flour_unenriched_unbleached", 100),
        ("qty", "white_sugar", 60),
        ("qty", "butter_salted", 100),
        ("txt", "Disposer 200g de myrtilles", "Disposer 500g de myrtilles"),
        ("txt", "mélanger 200g de farine de blé, 80g de flocons d'avoine roulés et 10g de sucre blanc",
         "mélanger 100g de farine de blé, 80g de flocons d'avoine et 60g de sucre"),
        ("txt", "Faire fondre 40g de beurre", "Faire fondre 100g de beurre"),
        ("txt", "Servir tiède, dans des bols préchauffés, accompagné", "Servir tiède, accompagné"),
    ],
    "main_daube_de_legumes_4a045f": [
        ("qty", "olive_oil_plant", 30),
        ("txt", "dans 4 ml d'huile d'olive", "dans 30 ml d'huile d'olive"),
        ("txt", "Ajouter l'oignon blanc émincé", "Ajouter l'oignon émincé"),
        ("txt", "Assaisonner et servir avec des pommes de terre vapeur", "Assaisonner avec 5 g de sel et servir avec des pommes de terre vapeur"),
        ("time", 20, 0, 60),
    ],
    "main_endives_au_gratin_6b58ee": [
        ("add", "table_salt_unenriched", 4, "g", "seasoning"),
        ("txt", "jusqu'à ce que la roux soit lisse et parfumée", "jusqu'à ce que le roux soit lisse et parfumé"),
        ("txt", "disposer dans un plat huilé de beurre", "disposer dans un plat beurré"),
    ],
    "main_epinards_assaisonnes_core_b596b9": [
        ("txt", "Ajouter 20g de graines de sésame noir", "Ajouter 20g de graines de sésame"),
        ("txt", "Émulsionner les saveurs en remuant constamment pendant 1 min", "Mélanger de nouveau pendant 1 minute"),
        ("txt", "en saupoudrant de graines de sésame noir et en arrosant d'huile de sésame chaude pour un parfum intense et une texture croustillante",
         "en saupoudrant d'un peu de graines de sésame"),
        ("time", 11, 0, 5),
    ],
    "main_escalivada_1ee1c4": [
        ("time", 17, 30, 50),
    ],
    "main_farofa_bresilienne_29e38e": [
        ("step-", "Accompagner de plats traditionnels brésiliens"),
    ],
    "main_fasolakia_grecques_67b6d9": [
        ("qty", "french_bean_raw", 600),
        ("txt", "Équêter les haricots verts de 300g et les couper en deux", "Équeuter 600g de haricots verts et les couper en deux"),
        ("txt", "jusqu'à ce que les échalotes soient tendres", "jusqu'à ce que les oignons soient tendres"),
    ],
    "main_feijoada_2f6754": [
        ("ing", "orange_raw", "orange_raw_juice_fresh", 120, "ml"),
        ("add", "vegetable_stock_dried", 5, "g", "ingredient"),
        ("add", "water", 300, "ml", "liquid"),
        ("txt", "Ajouter les carottes en brunoise et blanchir 3 minutes", "Ajouter les carottes en brunoise et les faire revenir 3 minutes"),
        ("txt", "Incorporer les haricots noirs égouttés et nacrer 2 minutes", "Incorporer les haricots noirs égouttés et les enrober 2 minutes"),
        ("txt", "Verser le jus d'orange fraîchement pressé et un peu de bouillon végétal", "Verser 120 ml de jus d'orange fraîchement pressé et 300 ml de bouillon végétal"),
        ("txt", "Servir dans des bols préchauffés, accompagné", "Servir bien chaud, accompagné"),
    ],
    "main_flamiche_aux_poireaux_fa3d0b": [
        ("qty", "leeks_raw", 800),
        ("add", "table_salt_unenriched", 4, "g", "seasoning"),
        ("txt", "la farine et l'beurre froid en dés", "la farine et le beurre froid en dés"),
        ("txt", "Émincer finement les 1200 g de poireaux", "Émincer finement les 800 g de poireaux"),
        ("txt", "Faire fondre l'beurre dans une casserole", "Faire fondre le beurre dans une casserole"),
        ("step-", "Vérifier que la lame d'un couteau insérée au centre de la tarte ressorte nette"),
    ],
    "main_fricassee_printaniere_619cae": [
        ("ing", "fava_bean_dried", "broadbeans_fava_beans_raw_fresh"),
        ("ing", "lemon", "lemon_juice", 20, "ml"),
        ("txt", "la ciboulette et l'estragon ciselés", "la ciboulette ciselée"),
    ],
    "main_fried_rice_a6e811": [
        ("txt", "Servir aussitôt dans des bols préchauffés, en veillant", "Servir aussitôt, en veillant"),
    ],
    "main_ful_medames_389da8": [
        ("ing", "lemon_raw", "lemon_juice", 30, "ml"),
        ("add", "parsley_fresh_herb", 15, "g", "herb"),
        ("txt", "les cuire 1 heure à 100°C dans l'eau non salée", "les cuire 1 heure dans l'eau non salée"),
        ("txt", ", en vérifiant la coloration dorée des tomates et en entendant le craquement du pain pita", ""),
        ("time", 13, 720, 80),
    ],
    "main_galettes_sarrasin_ce9f40": [
        ("add", "water", 500, "ml", "liquid"),
        ("add", "table_salt_unenriched", 5, "g", "seasoning"),
        ("txt", "un peu de beurre fondue", "un peu de beurre fondu"),
        ("txt", "casser 1 œuf (220g) au centre", "casser un œuf au centre (220 g pour les 4 galettes)"),
    ],
    "main_garbure_gasconne_545667": [
        ("add", "water", 1500, "ml", "liquid"),
        ("add", "olive_oil_plant", 20, "ml", "fat"),
        ("txt", "Faire revenir l'oignon et l'ail dans une grande cocotte", "Faire revenir l'oignon et l'ail dans 20 ml d'huile d'olive, dans une grande cocotte"),
        ("txt", "Couvrir d'eau et ajouter le thym", "Couvrir de 1,5 litre d'eau et ajouter le thym"),
        ("txt", "dans un pot-au-feu traditionnel", "dans des assiettes creuses"),
    ],
    "main_girolles_a_la_creme_7d432d": [
        ("flag", "kid_friendly", False),  # 80 ml de vin blanc
    ],
    "main_gnocchi_f17041": [
        ("time", 30, 0, 50),
    ],
    "main_gozleme_aux_epinards_66eccf": [
        ("add", "water", 180, "ml", "liquid"),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Mélanger avec 150 g de feta râpée, l'oignon et le poivre.", "Mélanger avec 150 g de feta émiettée, l'oignon émincé et le poivre."),
        ("txt", "Servir chaud, garni de coriandre fraîche ciselée et d'un filet d'huile d'olive.", "Servir chaud."),
    ],
}
