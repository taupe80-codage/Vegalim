"""Lot 22 : lasagnes, mac and cheese, nouilles coréennes et satay."""

PATCHES = {
    "pasta_lasagnes_8adf61": [
        ("txt", "Préparer la béchamel en faisant fondre 60 g de beurre dans une poêle, puis ajouter 400 ml de lait et cuire à feu moyen jusqu'à obtention d'une sauce épaisse et lisse.",
         "Réchauffer doucement les 400 ml de béchamel jusqu'à ce qu'elle soit lisse et nappante."),
        ("txt", "Enfourner 25 min à 180°C, puis retirer le papier aluminium et cuire encore 10 min",
         "Couvrir de papier aluminium et enfourner 25 min à 180°C, puis retirer le papier et cuire encore 10 min"),
    ],
    "pasta_lasagnes_de_legumes_ultra_9b6a4e": [
        ("qty", "coconut_milk_plant", 400),
        ("qty", "pasta_raw_dried", 250),
        ("delq", "olive_oil_plant", 50),
        ("qty", "olive_oil_plant", 60),
        ("add", "nutritional_yeast_flakes", 20, "g", "seasoning"),
        ("txt", "en faisant fondre 50 g d'huile d'olive, puis incorporez 50 g de farine de blé", "en chauffant 30 ml d'huile d'olive, puis incorporez 50 g de farine de blé"),
        ("txt", "Versez progressivement 600 ml de lait de coco chaud", "Versez progressivement 400 ml de lait de coco chaud"),
        ("txt", "de sauce tomate et de levure nutritionnelle râpée", "de sauce tomate et de levure maltée"),
        ("step-", "Cette recette est idéale pour un repas en famille"),
    ],
    "pasta_lasagnes_vegan_412e90": [
        ("qty", "nutritional_yeast_flakes", 30),
        ("txt", "Préparer la béchamel végétalienne en utilisant 400 ml de lait d'avoine et 60 g de levure nutritionnelle, cuire 5 minutes à feu moyen, en remuant constamment, jusqu'à obtenir une sauce épaisse et lisse.",
         "Réchauffer les 400 ml de béchamel végétale avec 30 g de levure maltée, 5 minutes à feu moyen, en remuant, jusqu'à obtenir une sauce épaisse et lisse."),
        ("txt", "Enfourner 25 minutes à 180°C, retirer le papier aluminium", "Couvrir de papier aluminium, enfourner 25 minutes à 180°C, puis retirer le papier"),
        ("txt", "puis servir chaud, dans des assiettes préchauffées, accompagné d'un filet d'huile d'olive vierge extra et d'une garniture de noix de coco et d'herbes fraîches.",
         "puis servir chaud, accompagné d'un filet d'huile d'olive vierge extra et d'herbes fraîches."),
    ],
    "pasta_mac_and_cheese_b3073b": [
        ("txt", "dans 1 litre d'eau bouillante non salée", "dans une grande casserole d'eau bouillante salée"),
        ("txt", "faire fondre 40g de beurre à 50°C dans une poêle, puis ajouter 1 cuillère à soupe de farine de blé",
         "faire fondre 40g de beurre dans une poêle, puis ajouter 20 g de farine de blé"),
        ("txt", "puis cuire 2 minutes à 80°C", "puis cuire 2 minutes à feu doux"),
    ],
    "pasta_mac_and_cheese_vegan_4acb30": [
        ("qty", "wheat_all_purpose_flour_unenriched_unbleached", 20),
        ("ing", "coconut_milk_plant", "oat_milk_refrigerated_plain_plant"),
        ("txt", "puis ajouter 200g de farine", "puis ajouter 20g de farine"),
        ("txt", "Verser progressivement 250ml de lait de coco", "Verser progressivement 250ml de lait d'avoine"),
    ],
    "pasta_nouilles_coreennes_aux_legumes_82115e": [
        ("add", "green_onion_raw", 40, "g", "garnish"),
        ("txt", "Servir tiède ou à température ambiante : la chaleur est essentielle pour garder les saveurs et les textures des légumes et des nouilles.",
         "Servir tiède ou à température ambiante."),
    ],
    # satay à la crème épaisse (400 ml) + beurre + 90 ml d'huile : 992 kcal
    "pasta_nouilles_satay_864b31": [
        ("ing", "cream_heavy", "coconut_milk_plant", 300, "ml"),
        ("ing", "lime_raw", "lime_juice_fresh", 30, "ml"),
        ("del", "butter_sup80pct"),
        ("add", "peanut_raw", 20, "g", "garnish"),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "60 ml de beurre de cacahuète et 400 ml de crème fraîche", "60 ml de beurre de cacahuète et 300 ml de lait de coco"),
        ("txt", "Dans un wok très chaud, ajouter 45 ml d'huile d'olive et sauter 200 g de carottes", "Dans un wok très chaud, sauter 200 g de carottes"),
        ("txt", "Assaisonner de 5 g de sel et goûter", "Assaisonner de 2 g de sel et goûter"),
    ],
}
