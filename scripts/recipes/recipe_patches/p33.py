"""Lot 33 : çoban, caramel, pâte à samosa, huancaína, tofu sauce ail, vinaigrette, accompagnements."""

PATCHES = {
    "salad_turque_coban_cdd8c4": [
        ("ing", "lemon_raw", "lemon_juice", 40, "ml"),
        ("txt", "en épépinant le poivron vert et rouge", "en épépinant le poivron rouge"),
        ("txt", "émulsionnez le jus de citron, l'huile d'olive, le sel et le poivre pendant 2 minutes à température ambiante",
         "émulsionnez 40 ml de jus de citron, 45 ml d'huile d'olive, 5 g de sel et du poivre"),
        ("txt", ", en servant sans attendre pour conserver la fraîcheur : la chaleur et le croustillant des légumes sont essentiels ici.", ", puis servez sans attendre."),
        ("step-", "Vérifiez que les dés de légumes sont nets et fermes"),
    ],
    "salted_butter_caramel_096c73": [
        ("txt", "incorporer l'beurre en dés", "incorporer le beurre en dés"),
        ("txt", "Servir sans attendre pour apprécier la texture lisse et le goût riche du caramel, idéal pour accompagner des crêpes ou des gâteaux.",
         "Se conserve 2 semaines au réfrigérateur ; le tiédir avant de servir avec des crêpes ou des gâteaux."),
    ],
    "samosa_dough_c03717": [
        ("step-", "Servir la pâte à samosa dans des bols"),
    ],
    # cream cheese à la place du queso fresco ; servie froide
    "sauce_pommes_de_terre_sauce_hua_3304de": [
        ("ing", "cream_cheese_block_whole_cow", "queso_fresco_block_cow"),
        ("add", "black_olive_canned_in_brine", 40, "g", "garnish"),
        ("add", "parsley_fresh_herb", 10, "g", "herb"),
        ("txt", "en mixant 150 g de fromage râpé, 15 g de piment amarillo", "en mixant 150 g de queso fresco, 15 g de piment séché (ancho, à défaut d'ají amarillo)"),
        ("step-", "Goûter et ajuster le sel et le piquant de la sauce"),
        ("txt", "puis garnir d'olives noires et de persil frais", "puis garnir de 40 g d'olives noires et de 10 g de persil frais"),
        ("txt", "Servir chaud, sans attendre, pour préserver la texture crémeuse de la sauce et la tendreté des pommes de terre, et déguster jusqu'à épuisement de la sauce.",
         "Servir froid ou à température ambiante."),
    ],
    "sauce_tofu_croustillant_sauce_a_b8be56": [
        ("ing", "coconut_oil_plant", "sunflower_oil_plant"),
        ("txt", "Chauffer 40 ml d'huile de coco", "Chauffer 45 ml d'huile de tournesol"),
        ("step-", "Goûter et rectifier l'assaisonnement si nécessaire"),
        ("step-", "Ajouter un peu de levure nutritionnelle"),
        ("txt", "Servir dans un plat chaud et décorer avec des feuilles de coriandre fraîche pour ajouter une touche de couleur et de fraîcheur.",
         "Servir aussitôt, avec du riz."),
        ("time", 17, 20, 12),
    ],
    "sauce_vinaigrette_174a79": [
        ("txt", "en filet fin à 20°C", "en filet fin"),
        ("step-", "Utiliser cette délicieuse vinaigrette végane"),
    ],
    "side_brocoli_roti_sauce_gribic_694128": [
        ("ing", "sweet_and_sour_gherkin_flavored_pre_packaged", "pickles_cucumber_canned_in_vinegar"),
        ("qty", "olive_oil_plant", 45),
        ("qty", "table_salt_unenriched", 3),
        ("txt", "30ml de vinaigre de vin blanc", "30ml de vinaigre blanc"),
        ("step-", "Vérifiez que le brocoli est tendre"),
        ("step-", "Garnissez de feuilles de persil frais"),
        ("step-", "Présentez avec une salade verte"),
    ],
    "side_carottes_glacees_a_lerabl_1d1c44": [
        ("qty", "carrot_raw", 600),
        ("qty", "table_salt_unenriched", 3),
        ("txt", "Peler 200g de carottes", "Peler 600g de carottes"),
        ("txt", "ajouter une pincée de sel", "ajouter 3 g de sel"),
        ("step-", "Assaisonner de sel selon les goûts"),
        ("time", 7, 0, 15),
    ],
    # version classique : beurre végétal + beurre + « 20 g d'huile » en finition
    "side_champignons_sautes_ail_pe_b477e2": [
        ("del", "vegan_butter"),
        ("qty", "olive_oil_plant", 25),
        ("qty", "lemon_juice", 15),
        ("txt", "14,6 ml de jus de citron fraîchement pressé, 20 g d'huile d'olive, 20g de beurre végétal et 30g de beurre",
         "15 ml de jus de citron fraîchement pressé et 30g de beurre"),
    ],
}
