"""Lot 45 : préparations de base (crêpe de sarrasin → sauce cacahuète)."""

PATCHES = {
    "base_buckwheat_crepe_03db22": [
        ("qty", "egg_raw", 110, "g"),
        ("txt", "Servir aussitôt dans des assiettes, accompagné d'un peu de beurre doux et de sirop d'érable ou de votre garniture préférée.",
         "Empiler les crêpes sous un torchon jusqu'à utilisation."),
    ],
    "base_cashew_ricotta_5c62e9": [
        ("add", "water", 45, "ml", "liquid"),
    ],
    # noix de cajou grillées à l'huile pour des noix crues trempées ; eau du mixage absente
    "base_vegan_cheddar_024998": [
        ("ing", "cashew_nuts_roasted_in_oil", "cashew_nuts_raw"),
        ("add", "water", 60, "ml", "liquid"),
        ("txt", "Servir frais, découpé en tranches fines, accompagné de crackers ou de pain grillé.", "Conserver 5 jours au réfrigérateur ; s'utilise en tartinade ou fondu."),
    ],
    # 60 ml d'huile dont une partie est égouttée
    "base_fried_onion_217e6a": [
        ("qty", "sunflower_oil_plant", 40),
        ("txt", "et lesisser refroidir", "et laisser refroidir"),
        ("txt", "Servir chaud, éventuellement comme topping ou condiment pour divers plats.", "Utiliser en garniture ; se conserve 3 jours au réfrigérateur."),
    ],
    "base_tortilla_92c2a6": [
        ("time", 20, 10, 15),
    ],
    "base_gnocchi_8f01d0": [
        ("qty", "egg_raw", 55, "g"),
    ],
    "base_noodles_2d0ed7": [
        ("qty", "egg_raw", 55, "g"),
    ],
    "base_wonton_wrapper_7bfeb5": [
        ("qty", "egg_raw", 55, "g"),
    ],
    "base_nouilles_ramen_3907e3": [
        ("time", 20, 60, 33),
    ],
    "base_doubanjiang_paste_340399": [
        ("ing", "chilli_pepper_raw", "red_hot_chili_pepper_spice_dried", 50),
        ("txt", "Équeuter 100 g de piments rouges secs", "Équeuter 50 g de piments rouges secs"),
    ],
    "base_sauce_peanut_d92c5c": [
        ("add", "white_sugar", 5, "g", "sweetener"),
        ("txt", "Goûter et ajuster l'équilibre acidité-sel-sucre.", "Ajouter 5 g de sucre et goûter."),
    ],
}
