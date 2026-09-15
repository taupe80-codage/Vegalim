"""Lot 1 : préparations de base (lait d'amande → mole)."""

PATCHES = {
    "base_almond_milk_226291": [
        ("txt", "Faire tremper 100g d'amandes dans 800ml d'eau froide", "Faire tremper 100g d'amandes dans de l'eau froide"),
        ("txt", "Égoutter, rincer, puis peler", "Égoutter et jeter l'eau de trempage, rincer, puis peler"),
    ],
    "base_cheddar_vegane_529b97": [
        ("txt", "40g de fécule de tapioca et 25ml d'huile de noix de coco", "40g de fécule de maïs et 25ml de lait de coco"),
    ],
    "base_cream_cheese_c6e3b6": [
        ("ing", "lemon", "lemon_juice"),
    ],
    "base_creme_fraiche_b536c1": [
        ("time", 5, 1680, 0),  # 12-24 h de fermentation + 4 h de froid
    ],
    "base_curry_paste_49c97f": [
        ("time", 20, 0, 0),
        ("step-", "Servir chaud, garni de feuilles de coriandre"),
    ],
    "base_empanada_dough_65661a": [
        ("txt", "Ajoutez progressivement 60ml d'eau froide", "Ajoutez l'œuf battu, puis progressivement 60ml d'eau froide,"),
        ("step-", "Servir aussitôt, garni d'une salade verte"),
    ],
    "base_gnocchi_vegan_dd3b0e": [
        ("txt", "Les pommes de terre doivent être tendres et légèrement croustillantes à l'extérieur.",
         "Les pommes de terre doivent être tendres à cœur."),
        ("txt", "pendant 25 minutes dans de l'eau bouillante salée avec 5g de sel", "pendant 25 minutes dans de l'eau bouillante salée"),
    ],
    "base_gochujang_41da6e": [
        ("ing", "chilli_pepper_raw", "gochugaru"),
        ("ing", "white_rice_raw_seed_unenriched", "white_glutinous_rice_seed_dried"),
        ("ing", "soybean_raw_dried", "soybean_flour_raw_whole"),
        ("txt", "100g de poudre de poivron rouge", "100g de piment coréen en poudre (gochugaru)"),
        ("time", 20, 4320, 20),
    ],
    "base_green_curry_paste_250117": [
        ("ing", "red_hot_chili_pepper_raw", "serrano_pepper_raw"),
        ("txt", "60g de piment rouge émincé", "60g de piment vert émincé"),
    ],
    "base_gundruk_94c079": [
        ("yield", 0.12),  # fermenté puis séché complètement au soleil
        # gundruk traditionnel : fermentation sans sel
        ("del", "table_salt_unenriched"),
        ("txt", "Masser légèrement les feuilles avec 10g de sel pour briser", "Écraser légèrement les feuilles pour briser"),
    ],
    "base_harissa_ef842f": [
        ("ing", "chilli_pepper_raw", "red_hot_chili_pepper_spice_dried"),
    ],
    "base_hoisin_033e33": [
        ("ing", "soybean_raw_dried", "soybean_boiled_dried"),
        ("time", 10, 1440, 5),  # refroidissement puis 24 h de repos
    ],
    "base_japanese_curry_roux_385e52": [
        ("txt", "Faites chauffer 50g de beurre dans une poêle à feu moyen, à environ 180°C.",
         "Faites fondre 50g de beurre dans une poêle à feu moyen."),
        ("step-", "Servir chaud, en vous régaland"),
        ("step-", "Accompagnez de riz ou de nouilles pour un repas complet."),
    ],
    "base_kimchi_61791a": [
        ("txt", "Servez votre kimchi végétal créé avec amour, accompagné", "Servez le kimchi accompagné"),
    ],
    "base_mala_broth_1ab129": [
        ("ing", "chilli_pepper_raw", "red_hot_chili_pepper_spice_dried"),
        ("txt", "créer une texture riche et crémeuse", "concentrer le bouillon"),
    ],
    "base_mayonnaise_0d3e4e": [
        ("ing", "egg_raw", "egg_yolk_raw", 20, "g"),
        ("ing", "lemon", "lemon_juice"),
        ("txt", " Servir fraîche, dans des bols ou des assiettes, accompagnée de crackers ou de légumes crus.", ""),
    ],
    "base_mole_d0034f": [
        ("ing", "chilli_pepper_raw", "red_hot_chili_pepper_spice_dried"),
        ("add", "coconut_oil_plant", 10, "ml", "fat"),
    ],
}
