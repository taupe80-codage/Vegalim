"""Variantes 17 : plats principaux trop légers — préparations de légumes reclassées en accompagnement
ou en entrée, deux recettes complétées pour rester des plats."""

VARIANTS = {
    # ── Reclassées en accompagnement : préparations de légumes de 125 à 190 kcal/portion,
    #    sans source de protéines, qui se mangent avec du riz, du pain ou des galettes ──
    "stew_eggplant_classic_5d46a1": [("dish", "side")],
    "curry_baingan_bharta_d54d1c": [("dish", "side")],
    "main_baingan_bharta_b5f900": [("dish", "side")],
    "curry_daubergine_indien_779e72": [("dish", "side")],
    "main_bhindi_masala_ade89d": [("dish", "side")],
    "main_nepali_saag_92a5f7": [("dish", "side")],
    "wok_chou_ethiopien_saute_93ab43": [("dish", "side")],
    "main_legumes_braises_7030b7": [("dish", "side")],
    "stew_ajapsandali_m8d4q1": [("dish", "side")],
    "main_fricassee_printaniere_619cae": [("dish", "side")],
    "main_aubergines_imam_bayildi_e1443e": [
        ("dish", "side"),
        ("origin", {"cuisine": "turkish"}),
    ],
    "main_papaya_salad_918f58": [("dish", "side")],

    # ── Reclassée en entrée : mezze persan servi avec du pain ──
    "main_kashke_bademjan_10dd33": [("dish", "starter")],

    # ── Complétées pour rester des plats ──
    "main_fasolakia_grecques_67b6d9": [
        ("title", "Fasolakia grecques aux pommes de terre et à la feta"),
        ("desc", "Ladera grec : haricots verts et pommes de terre mijotés longuement dans l'huile d'olive et la "
                 "tomate, servis tièdes avec de la feta émiettée."),
        ("compo", [
            ("french_bean_raw", 600, "g", "vegetable"),
            ("potato_raw_flesh", 400, "g", "carbohydrate"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("tomato_raw_ripe", 400, "g", "fruit"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("feta", 120, "g", "protein"),
            ("olive_oil_plant", 50, "ml", "fat"),
            ("oregano", 2, "g", "ingredient"),
            ("parsley_fresh_herb", 10, "g", "herb"),
            ("water", 250, "ml", "liquid"),
            ("table_salt_unenriched", 2, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Équeuter 600 g de haricots verts et les couper en deux. Couper 400 g de pommes de terre en gros quartiers.",
            "Faire revenir 150 g d'oignon émincé dans 40 ml d'huile d'olive, 6 minutes, puis ajouter 6 g d'ail haché.",
            "Ajouter 400 g de tomates concassées et cuire 5 minutes.",
            "Ajouter les haricots verts, les pommes de terre, 250 ml d'eau, 2 g d'origan, 2 g de sel et 1 g de poivre.",
            "Couvrir à moitié et laisser mijoter 45 minutes à feu très doux, jusqu'à ce que les légumes soient fondants et la sauce réduite.",
            "Servir tiède, arrosé de 10 ml d'huile d'olive, parsemé de 120 g de feta émiettée et de 10 g de persil.",
        ]),
        ("time", 15, 0, 50),
    ],
    "main_hungarian_lecs_47d502": [
        ("title", "Lecsó hongrois aux œufs"),
        ("desc", "Poivrons et tomates fondus au paprika doux, dans lesquels on brouille des œufs en fin de "
                 "cuisson, servis avec du pain de campagne."),
        ("compo", [
            ("red_bell_pepper_raw", 500, "g", "vegetable"),
            ("tomato_raw_ripe", 400, "g", "fruit"),
            ("onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("egg_raw", 220, "g", "protein"),
            ("paprika_powder", 4, "g", "spice"),
            ("sunflower_oil_plant", 35, "ml", "fat"),
            ("white_bread_unsalted", 160, "g", "carbohydrate"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Faire revenir 150 g d'oignon émincé dans 35 ml d'huile de tournesol, 6 minutes.",
            "Ajouter 500 g de poivrons en lanières et 9 g d'ail haché, puis cuire 5 minutes à feu moyen-vif.",
            "Hors du feu, ajouter 4 g de paprika doux, puis 400 g de tomates concassées, 3 g de sel et 1 g de poivre.",
            "Mijoter 20 minutes à feu doux, jusqu'à ce que les poivrons soient fondants et la sauce nappante.",
            "Battre 4 œufs (220 g), les verser dans le lecsó et remuer 2 minutes, jusqu'à ce qu'ils soient juste pris.",
            "Servir chaud avec 160 g de pain de campagne.",
        ]),
        ("time", 15, 0, 35),
    ],
}
