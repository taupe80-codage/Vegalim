"""Lot 34 : accompagnements (couscous de chou-fleur → purée)."""

PATCHES = {
    "side_couscous_de_choufleur_ac056b": [
        ("ing", "green_grape_raw", "grape_dried"),
        ("qty", "olive_oil_plant", 30),
        ("qty", "lemon_juice", 30),
        ("txt", "Faites chauffer 46,2 ml d'huile d'olive", "Faites chauffer 30 ml d'huile d'olive"),
        ("txt", "Incorporez 40 g de raisins frais", "Incorporez 40 g de raisins secs"),
        ("txt", "Arrosez de 29,1 ml de jus de citron", "Arrosez de 30 ml de jus de citron"),
    ],
    "side_dauphinois_vegan_c584cb": [
        ("qty", "vegetable_oil_plant", 10),
        ("txt", "huiler légèrement avec 30ml d'huile végétale", "huiler légèrement avec 10ml d'huile végétale"),
        ("txt", "puis servir chaud dans des bols préchauffés, accompagné d'un filet d'huile végétale et d'une poignée de persil frais ciselé si désiré.", "puis servir chaud."),
    ],
    "side_de_courge_butternut_d512a4": [
        ("txt", "Huiler un plat à gratin avec du beurre", "Beurrer légèrement un plat à gratin"),
        ("txt", "Enfourner à 180°C pendant environ 30 minutes", "Enfourner à 180°C pendant environ 45 minutes"),
        ("step-", "Servir chaud, garnir de persil frais si désiré"),
        ("time", 15, 10, 45),
    ],
    # pickle sri lankais : 100 ml d'huile comptés (30 dans le texte), moutarde de Dijon, pickle enfourné
    "side_eggplant_k1d1p1": [
        ("qty", "coconut_oil_plant", 60),
        ("qty", "chilli_pepper_raw", 20),
        ("del", "mustard"),
        ("txt", "dans 30 ml d'huile de coco", "dans 60 ml d'huile de coco"),
        ("txt", "15 g de sucre de canne, 3,8 g de curcuma, 15 g de sucre et 60 g de piment", "3,8 g de curcuma, 30 g de sucre et 20 g de piment"),
        ("step-", "Enfourner pendant 10 minutes à 180°C"),
        ("step-", "Vérifier la coloration, qui doit être dorée"),
        ("step-", "Ajouter 15 g de moutarde de Dijon"),
        ("time", 30, 50, 15),
    ],
    "side_epinards_a_la_creme_vegan_10afc3": [
        ("qty", "lemon_juice", 15),
        ("txt", "0,5 g de noix de muscade et 14,6 ml de jus de citron frais", "0,5 g de noix de muscade et 15 ml de jus de citron frais"),
        ("step-", "Contrôlez la texture et la température pour un service"),
        ("step-", "Rectifiez l'assaisonnement si nécessaire avant de servir"),
    ],
    "side_feijo_tropeiro_vegan_ccc81d": [
        ("qty", "olive_oil_extra_virgin_plant", 45),
        ("txt", "dans 45.7ml d'huile d'olive", "dans 45 ml d'huile d'olive"),
    ],
    "side_fenouil_braise_a_l_orange_a75916": [
        ("qty", "olive_oil_plant", 45),
        ("flag", "kid_friendly", False),
        ("txt", "le jus d'une orange, 100 ml de vin blanc sec", "150 ml de jus d'orange, 100 ml de vin blanc sec"),
    ],
    "side_flageolets_a_la_bretonne_a2af15": [
        ("qty", "thyme_dried_herb", 2),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "dans 30 g de beurre à 170°C pendant 6 minutes", "dans 30 g de beurre à feu moyen pendant 6 minutes"),
        ("txt", "Ajoutez 10 g d'ail haché et 10 g de bouquet garni", "Ajoutez 10 g d'ail haché et un bouquet garni (2 g de thym, une feuille de laurier)"),
        ("txt", "rectifiez l'assaisonnement avec 5 g de sel", "rectifiez l'assaisonnement avec 2 g de sel"),
        ("step-", "Vérifiez que les flageolets sont tendres"),
        ("txt", "Servez chaud, en contrôlant la température pour un service, pour préserver la tendresse des flageolets et la saveur de la sauce.", "Servez chaud."),
        ('txt', "Faites revenir 150 g d'oignon jaune en brunoise", "Faites revenir 150 g d'oignon jaune, 100 g de carotte et 40 g de céleri en brunoise"),
    ],
    "side_haricots_verts_a_la_greno_f1bdca": [
        ("qty", "lemon_juice", 30),
        ("txt", "Terminer avec 29.1ml de jus de citron", "Terminer avec 30 ml de jus de citron"),
        ("txt", "Servir sans attendre: la chaleur et le croustillant sont essentiels pour apprécier les saveurs et les textures de ce plat.", "Servir sans attendre."),
        ("step-", "Vérifier que les haricots sont tendres, les croûtons croustillants"),
    ],
    "side_jeera_rice_vegan_694fd1": [
        ("add", "water", 450, "ml", "liquid"),
        ("steps", [
            "Rincer 300 g de riz basmati sous l'eau froide jusqu'à ce que l'eau soit claire, puis l'égoutter.",
            "Faire fondre 40 g de beurre végétal dans une casserole à fond épais à feu moyen.",
            "Ajouter 2,5 g de graines de cumin et les laisser crépiter 30 à 45 secondes.",
            "Ajouter le riz égoutté et mélanger délicatement pendant 1 minute pour bien l'enrober.",
            "Verser 450 ml d'eau bouillante avec 5 g de sel, couvrir et cuire 12 minutes à feu très doux.",
            "Retirer du feu, laisser reposer 5 minutes à couvert, puis égrainer délicatement et servir.",
        ]),
    ],
    "side_lentilles_du_puy_echalote_37c76e": [
        ("qty", "olive_oil_plant", 30),
        ("txt", "et 2 g de laurier à 180°C pendant 20-25 minutes", "et 2 g de laurier, à petit frémissement, pendant 20-25 minutes"),
        ("txt", "dans 30 g d'huile d'olive", "dans 30 ml d'huile d'olive"),
        ("txt", ", 15 g de persil frais haché et un filet d'huile d'olive,", " et 15 g de persil frais haché,"),
    ],
    "side_orge_perle_aux_champignon_2824cb": [
        ("qty", "olive_oil_plant", 25),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "avec 5 g de sel et 3 g de poivre", "avec 2 g de sel et 3 g de poivre"),
        ("txt", "Servir sans attendre, pour profiter de la chaleur et du croustillant des champignons.", "Servir sans attendre."),
    ],
    # `sourdough_bread` (pain cuit) comptait pour le levain ; 1 pain de 950 g = 10 tranches
    "side_pain_de_campagne_31cbd7": [
        ("del", "sourdough_bread"),
        ("qty", "bread_flour_blanched", 575),
        ("qty", "water", 425),
        ("serv", 10),
        ("dish", "bread"),
        ("flag", "vegan", True),
        ("flag", "lactose_free", True),
        ("steps", [
            "Mélanger 500 g de farine à pain avec 150 g de levain actif (75 g de farine et 75 ml d'eau rafraîchis la veille) et 350 ml d'eau tiède.",
            "Incorporer 10 g de sel et pétrir 10 minutes, jusqu'à obtenir une pâte ferme et élastique.",
            "Laisser pousser 4 à 6 heures à température ambiante, jusqu'à ce que la pâte ait nettement gonflé.",
            "Façonner en boule et placer dans un banneton fariné.",
            "Préchauffer le four à 240°C avec une cocotte en fonte à l'intérieur.",
            "Cuire 25 minutes à couvert, puis 15 à 20 minutes à découvert, jusqu'à ce que la croûte soit brun acajou.",
            "Laisser refroidir 1 heure sur une grille avant de trancher.",
        ]),
    ],
    "side_petits_pois_a_la_francais_1aa736": [
        ("qty", "butter_sup80pct", 40),
        ("txt", "Ajouter les oignons grelots et les faire dorer", "Ajouter 100 g d'oignons grelots et les faire dorer"),
        ("txt", "Ajouter 100 g d'oignons grelots préalablement cuits et 40 g de beurre pour donner une saveur riche et crémeuse.",
         "Ajouter 10 g de beurre froid pour lier la sauce."),
    ],
    # 500 ml d'huile de friture comptés comme mangés
    "side_pommes_dauphine_73a2c7": [
        ("qty", "vegetable_oil_plant", 40),
        ("txt", "porter l'eau, l'beurre et le sel", "porter l'eau, le beurre et le sel"),
    ],
    "side_potatoes_k3d2p1": [
        ("txt", "Incorporer 60 g de beurre doux fondue.", "Incorporer 60 g de beurre doux."),
        ("step-", "Vérification de la cuisson."),
        ("txt", "Servir chaud dans des bols préchauffés, accompagné d'un peu de beurre doux fondu et de poivre noir fraîchement moulu.", "Servir chaud."),
    ],
}
