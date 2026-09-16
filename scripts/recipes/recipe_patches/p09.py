"""Lot 9 : desserts (crumble → tarte au citron meringuée)."""

PATCHES = {
    "dessert_crumble_aux_myrtilles_veg_15390f": [
        ("qty", "wheat_all_purpose_flour_unenriched_unbleached", 100),
        ("qty", "vegan_butter", 100),
        ("qty", "white_sugar", 60),
        ("txt", "mélangez 200g de farine de blé, 80g de flocons d'avoine et 14.1g de sucre de canne",
         "mélangez 100g de farine de blé, 80g de flocons d'avoine et 60g de sucre"),
        ("txt", "Incorporez 40g d'huile fondue en morceaux du bout des doigts", "Incorporez 100g de beurre végétal froid en morceaux du bout des doigts"),
    ],
    "dessert_far_breton_aux_pruneaux_069b81": [
        ("ing", "plum_raw_pitted", "prune_raw_pitted_dried"),
        ("txt", "en huilant un plat de 30×20 cm avec du beurre", "en beurrant un plat de 30×20 cm"),
        ("txt", "Fouetter 220 g de yaourt", "Fouetter 220 g d'œufs"),
        ("txt", " et 30 ml de rhum pour parfumer la pâte", " pour parfumer la pâte"),
    ],
    "dessert_financiers_aux_amandes_a02063": [
        ("add", "almond_raw_with_skin_unsalted", 20, "g", "garnish"),
        ("qty", "white_sugar", 180),
        ("txt", "Ajoutez l'beurre noisette refroidie", "Ajoutez le beurre noisette refroidi"),
    ],
    "dessert_flan_patissier_aa63b2": [
        ("txt", " et en vérifiant que la lame ressort sèche après 3 minutes de cuisson", ""),
        ("time", 25, 120, 45),
    ],
    "dessert_fondant_au_chocolat_a4c8aa": [
        ("steps", [
            "Préchauffer le four à 200°C. Beurrer et sucrer des ramequins individuels en veillant à une couche régulière.",
            "Faire fondre 200 g de chocolat noir et 120 g de beurre au bain-marie, en remuant jusqu'à obtenir un mélange lisse.",
            "Incorporer 165 g d'œufs entiers, 54 g de jaunes et 100 g de sucre au mélange chocolat-beurre tiédi, en fouettant jusqu'à obtenir une texture lisse et brillante.",
            "Ajouter 50 g de farine et mélanger jusqu'à obtenir une pâte homogène.",
            "Verser la pâte dans les ramequins en les remplissant aux deux tiers, puis réfrigérer 30 minutes.",
            "Enfourner 12 minutes à 200°C : les bords doivent être pris et le centre rester coulant.",
            "Démouler aussitôt et servir sans attendre.",
        ]),
    ],
    "dessert_galette_des_rois_briochee_6f0909": [
        ("txt", "y compris la farine à pain, le sucre blanc", "y compris la farine, le sucre"),
        ("txt", "puis décorer de sucre en grains", "puis saupoudrer d'un peu de sucre"),
        ("txt", "Servir chaud, garnie de sucre en grains et accompagnée d'une couronne dorée, si désiré.", "Servir tiède."),
    ],
    "dessert_gateau_au_yaourt_citron_f27832": [
        ("txt", "Mélanger 125 g de yaourt avec 125 g de sucre", "Mélanger 125 g de yaourt avec 165 g d'œufs, 125 g de sucre"),
        ("txt", "un moule beurré avec de l'huile d'olive et fariné", "un moule huilé et fariné"),
    ],
    "dessert_gateau_basque_f22cc0": [
        ("serv", 8),
        ("txt", "Incorporer 2 œufs et 1 jaune, puis ajouter 300 g de farine", "Incorporer 165 g d'œufs et 2 ml de rhum, puis ajouter 300 g de farine"),
        ("txt", "dans un moule huilé de beurre de 22 cm", "dans un moule beurré de 22 cm"),
        ("txt", "Garnir de confiture de cerise noire ou de crème pâtissière préparée avec du lait et des œufs.", "Garnir de 200 g de confiture de cerise noire."),
        ("txt", "Dorer avec un mélange à base de jus de citron et de sucre, puis strier", "Badigeonner d'un peu d'eau sucrée, puis strier"),
    ],
    "dessert_gateau_carottes_vegan_9d8a84": [
        ("ing", "grenoble_walnut_igp_candied", "walnut_shelled_dried"),
        ("qty", "white_sugar", 150),
        ("serv", 8),
        ("txt", "Laisser refroidir avant de servir. Ce gâteau carottes végétalien est délicieux chaud ou froid, accompagné de votre choix de garniture, comme une crème de noix de cajou ou un glaçage au citron. Servir dans un plat de service, napper de sauce et découper en parts. Se déguste chaud ou tiède, accompagné d'une salade verte.",
         "Laisser refroidir complètement. Préparer le glaçage en mélangeant 150 g de purée de cajou avec 29 ml de jus de citron, le napper sur le gâteau, puis découper en parts."),
    ],
    "dessert_ile_flottante_4623ef": [
        ("txt", "Ajouter 150 g de sucre et blanchir les jaunes d'œuf avec le sucre, jusqu'à obtenir une consistance lisse et crémeuse.",
         "Blanchir les jaunes d'œufs avec 100 g de sucre, jusqu'à obtenir une consistance lisse et crémeuse."),
        ("txt", "avec une pincée de sel, incorporer le sucre, jusqu'à crépitation légère et obtenir une consistance aérienne",
         "avec une pincée de sel, puis incorporer 50 g de sucre, jusqu'à obtenir une consistance ferme et aérienne"),
        ("txt", "avec filets de caramel, crépitant légèrement pour ajouter une texture croustillante", "avec un filet de caramel"),
    ],
    "dessert_kheer_au_riz_ee0837": [
        ("txt", "jusqu'à ce qu'il soit tendre et commence à germer, en vérifiant régulièrement pour éviter un trempage excessif",
         "jusqu'à ce que les grains soient légèrement gonflés"),
    ],
    "dessert_kouign_amann_a71af6": [
        ("txt", "200 g de beurre fondu en plaquette", "200 g de beurre froid aplati en plaquette"),
        ("txt", "Saupoudrer de sucre pour créer une couche croustillante", "Saupoudrer des 50 g de sucre restants pour créer une couche croustillante"),
    ],
    "dessert_lait_coco_vegan_3b8a99": [
        ("ing", "coconut_flour", "coconut_sugar"),
        ("txt", " et un filet de sirop d'agave pour ajouter une touche de douceur", ""),
        ("step-", "levure nutritionnelle râpée"),
    ],
    "dessert_lait_vanille_cddf17": [
        ("txt", "Incorporer le riz blanchi", "Incorporer le riz rincé"),
    ],
    "dessert_madeleines_4572e8": [
        ("txt", "jusqu'à ce qu'elle atteigne une consistance lisse et fluide", "jusqu'à ce qu'il tiédisse"),
        ("txt", "Battez 165g de mélange d'œufs", "Battez 165g d'œufs"),
        ("txt", "ajoutez l'beurre refroidie", "ajoutez le beurre refroidi"),
        ("txt", "des moules beurrés à l'beurre", "des moules beurrés"),
        ("txt", "la relaxation des gluten", "la détente du gluten"),
    ],
    "dessert_mousse_au_chocolat_vegan_b5d48f": [
        ("txt", "Décorer d'éclats de cacao frais", "Saupoudrer de cacao en poudre"),
    ],
    "dessert_pain_d_epices_754c93": [
        ("txt", "Huiler un moule à cake avec de l'huile et fariner", "Beurrer ou huiler un moule à cake et le fariner"),
        ("txt", "Chauffer 200g de sirop d'agave (remplaçant le miel)", "Chauffer 200g de miel"),
        ("txt", "2g d'anis en poudre. Ces épices", "2g d'anis en poudre et 1g de muscade. Ces épices"),
        ("txt", "Incorporer le sirop d'agave chaud", "Incorporer le miel chaud"),
    ],
    "dessert_panna_cotta_coco_vegan_16d6b5": [
        ("ing", "coconut_flour", "coconut_sugar"),
        ("qty", "coconut_milk_plant", 450),
        ("txt", "napper de coulis de fruits rouges ou de passion", "napper de pulpe de fruit de la passion"),
    ],
    "dessert_profiteroles_0d0e42": [
        ("steps", [
            "Préparer la pâte à choux : porter 200 ml d'eau à ébullition avec 80 g de beurre et une pincée de sel. Hors du feu, ajouter d'un coup 150 g de farine et mélanger énergiquement sur feu doux jusqu'à ce que la pâte se détache de la casserole.",
            "Hors du feu, incorporer 220 g d'œufs battus petit à petit, jusqu'à obtenir une pâte souple qui retombe lentement en ruban.",
            "Dresser des boules de 3 cm à la poche à douille sur une plaque, en les espaçant de 4 cm. Lisser le dessus avec le dos d'une cuillère mouillée, puis enfourner à 200°C pendant 25 minutes sans ouvrir le four : les choux doivent doubler de volume et être brun doré.",
            "Laisser refroidir complètement sur une grille. Fouetter 200 ml de crème très froide avec 60 g de sucre et 5 g de vanille, jusqu'à obtenir une crème ferme.",
            "Couper chaque chou aux deux tiers, le garnir de crème à la poche, puis dresser en pyramide.",
            "Préparer la sauce en faisant fondre 150 g de chocolat noir avec les 100 ml de crème restants.",
            "Napper les profiteroles de sauce chocolat chaude au moment de servir.",
        ]),
    ],
    "dessert_sorbet_mangue_passion_583687": [
        ("add", "water", 150, "ml", "liquid"),
    ],
    "dessert_tarte_aux_fraises_a05bbd": [
        ("txt", "Étalez 200g de pâte sablée", "Étalez 200g de pâte brisée"),
    ],
    # « œufs végétaux » et « beurre à la place du beurre » dans une recette aux œufs et au beurre
    "dessert_tarte_citron_meringuee_7f6440": [
        ("qty", "white_sugar", 250),
        ("steps", [
            "Préchauffer le four à 180°C. Foncer un moule à tarte avec 200 g de pâte brisée et la cuire à blanc 15 minutes.",
            "Préparer le curd au bain-marie : fouetter 110 g d'œufs et 72 g de jaunes avec 150 g de sucre, 150 ml de jus de citron et 10 g de zeste pendant environ 10 minutes, jusqu'à épaississement.",
            "Hors du feu, incorporer 100 g de beurre en dés.",
            "Verser le curd sur le fond de tarte cuit et laisser refroidir 1 heure.",
            "Monter 140 g de blancs en neige, puis incorporer 100 g de sucre pour obtenir une meringue brillante et ferme.",
            "Napper la tarte de meringue, puis la dorer au chalumeau ou sous le gril 2 à 3 minutes.",
            "Réfrigérer 1 heure avant de servir.",
        ]),
    ],
}
