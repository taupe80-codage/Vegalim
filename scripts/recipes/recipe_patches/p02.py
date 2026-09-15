"""Lot 2 : préparations de base (mozzarella végane → teriyaki)."""

PATCHES = {
    "base_mozzarella_vegane_fca8c8": [
        ("txt", "50 g de fécule de tapioca", "50 g de fécule de maïs"),
        ("txt", "Placez la casserole sur feu moyen, environ 180°C,", "Placez la casserole sur feu moyen"),
    ],
    "base_natto_7060f1": [
        ("step-", "Servir le natto à température ambiante, après avoir laissé décongeler"),
        ("dish", "condiment"),
    ],
    "base_oat_cream_954865": [
        ("step-", "Servir aussitôt, garni de coriandre ciselée"),
    ],
    "base_oat_milk_3519f4": [
        ("time", 5, 30, 0),
    ],
    "base_okonomiyaki_1e5fba": [
        ("time", 5, 10, 0),
        ("txt", " La sauce doit être chaude et crémeuse, avec une texture qui complète parfaitement les galettes.", ""),
    ],
    "base_peanut_butter_81c37b": [
        ("txt", "Servez sans attendre sur du pain complet toasté", "Tartinez sur du pain complet toasté"),
        ("txt", ", en profitant de la chaleur et de la fraîcheur du beurre de cacahuète", ""),
    ],
    "base_pesto_905db7": [
        ("time", 10, 0, 0),
    ],
    "base_pistou_43e29a": [
        ("time", 10, 0, 0),
    ],
    "base_puff_pastry_fca43b": [
        ("txt", "50g de beurre fondue", "50g de beurre fondu"),
        ("txt", "sur l'beurre", "sur le beurre"),
        ("txt", "à la épaisseur", "à l'épaisseur"),
        ("txt", "Répétez les étapes de pliage, d'étalage et de réfrigération cinq fois au total, en laissant reposer la pâte entre chaque double tour",
         "Répétez l'étalage, le pliage en trois et la réfrigération jusqu'à 6 tours simples au total, en laissant reposer la pâte entre chaque tour"),
        ("step-", "vérifiez que la lame ressort sèche"),
        ("time", 30, 180, 25),
    ],
    "base_ras_el_hanout_7cd544": [
        ("ing", "ginger_raw_root_fresh", "ginger_powder"),
        ("txt", "le cumin, la coriandre et le cardamome entiers", "le cumin, la coriandre et la cardamome entiers"),
        ("txt", "le cumin moulu, la coriandre moulue, le cardamome moulu, le cumin cru, la coriandre crue, la cannelle, le gingembre,",
         "le cumin, la coriandre et la cardamome moulus, la cannelle, le gingembre moulu,"),
        ("step-", "Ajouter les épices crues restantes si nécessaire"),
    ],
    "base_rice_milk_128001": [
        ("qty", "water", 1100),  # 300 ml de cuisson du riz + 800 ml de mixage
    ],
    "base_salted_ricotta_1ecd1c": [
        ("txt", "Préparez le fromage râpé en le laissant égoutter", "Laissez égoutter la ricotta"),
        ("txt", "mélangez délicatement le fromage râpé avec", "mélangez délicatement la ricotta égouttée avec"),
    ],
    # 300 g de farine lavée ne laissent qu'environ 35 g de gluten : recette refaite au gluten de blé
    "base_seitan_249032": [
        ("ing", "wheat_all_purpose_flour_unenriched_unbleached", "vital_wheat_gluten_flour", 150),
        ("txt", "mélangez 300g de farine de blé avec 150ml d'eau tiède, jusqu'à obtenir une pâte lisse et homogène. Pétrissez pendant 5 minutes, jusqu'à ce que la pâte devienne élastique et se décolle facilement des parois du bol.",
         "mélangez 150g de gluten de blé avec 150ml d'eau tiède. Pétrissez pendant 5 minutes, jusqu'à ce que la pâte devienne élastique."),
        ("step-", "Laissez reposer la pâte dans un bain d'eau froide"),
        ("step-", "Rincez la pâte sous l'eau froide en la malaxant"),
    ],
    "base_shortcrust_e6e9f0": [
        ("txt", "125g de beurre froide", "125g de beurre froid"),
        ("txt", "Ajouter 30ml d'eau froide et 4g de sel.", "Ajouter l'œuf battu, 30ml d'eau froide et 4g de sel."),
        ("txt", " Servir dans un plat décoratif, accompagné d'une salade verte ou d'un légume grillé.", ""),
    ],
    "base_soy_cream_4dc027": [
        ("step-", "Servir la crème de soja maison froide, garnie"),
    ],
    "base_spring_roll_wrappers_eba962": [
        ("txt", ", en vérifiant que la pâte a doublé de volume", ""),
    ],
    "base_strawberry_coulis_49d4ea": [
        ("ing", "lemon", "lemon_juice"),
    ],
    "base_teriyaki_03b2ff": [
        ("step-", "feuilles de thé vert"),
        ("txt", ", garnie de feuilles de coriandre ou de tranches de citron, pour une présentation élégante", ""),
    ],
}
