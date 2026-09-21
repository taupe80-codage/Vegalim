"""Lot 35 : potimarron, céleri, pilaf vegan, rösti, sabzi polo vegan, taboulé de sarrasin, tian."""

PATCHES = {
    "side_potimarron_roti_aux_epice_b9c552": [
        ("qty", "olive_oil_plant", 30),
        ("qty", "sesame_tahini_raw_butter_seed_plant", 15),
        ("txt", "Mélangez 46,2ml d'huile d'olive", "Mélangez 30ml d'huile d'olive"),
        ("txt", "faites griller des graines de grenade dans une poêle sans huile, en les agitant régulièrement pour éviter qu'elles ne brûlent et pour obtenir une texture croustillante.",
         "égrenez 50 g de grenade et diluez 15 ml de tahini avec un peu d'eau."),
        ("txt", "de graines de grenade grillées", "des graines de grenade"),
    ],
    "side_puree_de_celerirave_vegan_a55054": [
        ("txt", "Vérifier que la purée est lisse et crémeuse, avec une saveur riche et parfumée. Servir sans attendre.", "Servir sans attendre."),
    ],
    # 750 ml de bouillon pour 300 g de riz pilaf
    "side_riz_pilaf_turc_vegan_3bb995": [
        ("qty", "water", 500),
        ("qty", "vegetable_stock_dried", 6.3),
        ("txt", "Verser 750ml de bouillon végétal chaud, saler au goût", "Verser 500ml de bouillon végétal chaud"),
        ("step-", "Vérifier que le riz est cuit, en plantant une lame"),
    ],
    # rösti = pommes de terre seules
    "side_rosti_4ec9f8": [
        ("del", "yellow_onion_raw"),
        ("txt", "Incorporer l'oignon jaune émincé (150g), le thym frais (3g)", "Incorporer le thym frais (3g)"),
        ("step-", "Présenter le rösti dans un plat coloré"),
        ("time", 11, 10, 20),
    ],
    "side_sabzi_polo_vegan_7bf9df": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 30),
        ("qty", "parsley_fresh_herb", 100),
        ("qty", "dill_weed_fresh_herb_leaf", 60),
        ("qty", "chives_raw_fresh", 40),
        ("qty", "olive_oil_plant", 30),
        ("txt", "persil (30g), aneth (20g), ciboulette (25g) et fenugrec (3.5g)", "persil (100g), aneth (60g), ciboulette (40g), coriandre (30g) et fenugrec séché (3.5g)"),
        ("txt", "Ajoutez le safran (0.5g) et le coriandre en poudre (2g) au riz", "Ajoutez le safran (0.5g) infusé dans 2 cuillerées d'eau chaude au riz"),
        ("txt", "et un peu d'huile d'olive (46.2ml)", "et 30 ml d'huile d'olive"),
        ("txt", "Faites cuire la croûte à feu moyen pendant environ 5 minutes", "Couvrez et faites cuire à feu doux pendant environ 25 minutes"),
        ("step-", "Présentez le plat chaud"),
        ("time", 19, 0, 40),
    ],
    "side_tabbouleh_de_sarrasin_7e68ad": [
        ("qty", "olive_oil_plant", 45),
        ("qty", "lemon_juice", 60),
        ("txt", "dans 400ml d'eau bouillante salée à 100°C", "dans 400ml d'eau bouillante salée"),
        ("txt", "Égouttez le sarrasin cuit", "Égrenez le sarrasin cuit"),
        ("txt", "46.2ml d'huile d'olive, 58.3ml de jus de citron", "45 ml d'huile d'olive, 60 ml de jus de citron"),
    ],
    "side_tian_provencal_vegan_886a6d": [
        ("qty", "olive_oil_plant", 60),
    ],
}
