"""Variantes 6 : polenta aux champignons, risottos (champignons, citron, asperges)."""


def _risotto(fat, aromatics, rice=280, broth=900, stock=9):
    """Premières étapes communes d'un risotto."""
    return [
        f"Porter à frémissement {broth} ml d'eau avec {stock} g de bouillon déshydraté et le garder chaud.",
        f"Faire suer {aromatics} dans {fat}, 5 minutes, sans coloration.",
        f"Ajouter {rice} g de riz et le nacrer 2 minutes, jusqu'à ce que les grains soient translucides.",
        "Mouiller louche par louche de bouillon chaud, en remuant souvent, pendant 18 minutes : le riz doit rester légèrement ferme au cœur.",
    ]


VARIANTS = {
    # ── Polenta : crémeuse aux cèpes / grillée trifolati / vegan au ragoût / frites vegan ──
    "main_polenta_ai_funghi_b96235": [
        ("title", "Polenta crémeuse aux cèpes et au parmesan"),
        ("desc", "Polenta morbida de Vénétie, montée au beurre et au parmesan, nappée de cèpes et champignons "
                 "sautés à l'ail et au thym."),
        ("origin", {"cuisine": "italian", "country": "italy", "region": "veneto", "city": ""}),
        ("compo", [
            ("polenta", 250, "g", "grain"),
            ("porcini_mushroom_raw", 150, "g", "ingredient"),
            ("button_mushroom_raw", 200, "g", "ingredient"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 20, "ml", "fat"),
            ("butter_sup80pct", 20, "g", "fat_cooking"),
            ("parmesan_grated_dried_cow", 40, "g", "ingredient"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("water", 1200, "ml", "liquid"),
        ]),
        ("steps", [
            "Porter à ébullition 1,2 L d'eau avec 3 g de sel, puis verser 250 g de polenta en pluie en fouettant.",
            "Cuire 35 minutes à feu doux en remuant régulièrement, jusqu'à ce que la polenta soit crémeuse et se détache des parois.",
            "Pendant ce temps, faire revenir 100 g d'oignon émincé dans 20 ml d'huile d'olive, 4 minutes, puis ajouter 150 g de cèpes et 200 g de champignons émincés et les saisir 8 minutes à feu vif.",
            "Ajouter 9 g d'ail haché, 3 g de thym et 1 g de poivre, puis cuire 1 minute.",
            "Hors du feu, incorporer à la polenta 20 g de beurre et 40 g de parmesan.",
            "Servir la polenta dans des assiettes creuses, couverte des champignons.",
        ]),
        ("time", 15, 0, 40),
    ],
    "main_polenta_aux_champignons_5af074": [
        ("title", "Polenta grillée aux champignons trifolati"),
        ("desc", "Polenta du Frioul refroidie en plaque, découpée et grillée, servie avec des champignons trifolati "
                 "à l'ail et au persil, et des copeaux de parmesan."),
        ("origin", {"cuisine": "italian", "country": "italy", "region": "frioul", "city": ""}),
        ("compo", [
            ("polenta", 250, "g", "grain"),
            ("button_mushroom_raw", 400, "g", "ingredient"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("parsley_fresh_herb", 20, "g", "herb"),
            ("vegetable_oil_plant", 10, "ml", "fat"),
            ("olive_oil_extra_virgin_plant", 20, "ml", "fat"),
            ("butter_sup80pct", 20, "g", "fat_cooking"),
            ("parmesan_grated_dried_cow", 40, "g", "ingredient"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("water", 1100, "ml", "liquid"),
        ]),
        ("steps", [
            "Porter à ébullition 1,1 L d'eau avec 3 g de sel, verser 250 g de polenta en pluie et cuire 30 minutes en remuant. Incorporer 20 g de beurre.",
            "Étaler la polenta sur 2 cm d'épaisseur dans un plat huilé et laisser prendre au frais au moins 1 heure.",
            "Découper en rectangles, les badigeonner de 10 ml d'huile et les griller 4 minutes de chaque côté dans une poêle-gril.",
            "Faire sauter 400 g de champignons en lamelles dans 20 ml d'huile d'olive à feu vif, 8 minutes, puis ajouter 12 g d'ail et 20 g de persil hachés et 1 g de poivre.",
            "Servir la polenta grillée couverte de champignons et de 40 g de copeaux de parmesan.",
        ]),
        ("time", 20, 60, 45),
    ],
    "main_polenta_ai_funghi_vegan_ab13cd": [
        ("title", "Polenta crémeuse, ragoût de champignons à la tomate (vegan)"),
        ("desc", "Polenta montée à l'huile d'olive et à la levure nutritionnelle, servie avec un ragoût de "
                 "champignons mijotés à la tomate et au romarin."),
        ("compo", [
            ("polenta", 200, "g", "grain"),
            ("button_mushroom_raw", 400, "g", "ingredient"),
            ("tomato_crushed_canned", 300, "g", "vegetable"),
            ("yellow_onion_raw", 150, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("rosemary_fresh_herb", 3, "g", "herb"),
            ("olive_oil_extra_virgin_plant", 45, "ml", "fat"),
            ("nutritional_yeast_flakes", 20, "g", "ingredient"),
            ("vegan_butter", 20, "g", "fat"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("water", 1000, "ml", "liquid"),
        ]),
        ("steps", [
            "Faire revenir 150 g d'oignon émincé dans 30 ml d'huile d'olive, 5 minutes, puis ajouter 400 g de champignons en quartiers et cuire 8 minutes à feu vif.",
            "Ajouter 12 g d'ail haché, 3 g de romarin, 300 g de tomates concassées et 1 g de sel, puis mijoter 20 minutes.",
            "Porter à ébullition 1 L d'eau avec 3 g de sel, verser 200 g de polenta en pluie et cuire 30 minutes en remuant.",
            "Hors du feu, incorporer 20 g de beurre végétal, 15 ml d'huile d'olive et 20 g de levure nutritionnelle.",
            "Servir la polenta nappée du ragoût de champignons et poivrée.",
        ]),
        ("time", 15, 0, 35),
    ],
    "main_polenta_aux_champignons_v_b0e1ad": [
        ("title", "Frites de polenta au four, poêlée de champignons au persil (vegan)"),
        ("desc", "Bâtonnets de polenta ferme parfumée au thym, rôtis au four jusqu'à être croustillants, "
                 "servis avec une poêlée de champignons à l'ail et au persil."),
        ("compo", [
            ("polenta", 280, "g", "grain"),
            ("button_mushroom_raw", 400, "g", "ingredient"),
            ("onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 12, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 45, "ml", "fat"),
            ("nutritional_yeast_flakes", 20, "g", "ingredient"),
            ("parsley_fresh_herb", 20, "g", "herb"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
            ("water", 1200, "ml", "liquid"),
        ]),
        ("steps", [
            "Porter à ébullition 1,2 L d'eau avec 3 g de sel et 3 g de thym, verser 280 g de polenta en pluie et cuire 30 minutes en remuant, puis incorporer 20 g de levure nutritionnelle.",
            "Étaler sur 2 cm dans un plat huilé et laisser prendre 1 heure au frais.",
            "Préchauffer le four à 220°C. Couper la polenta en bâtonnets, les mélanger avec 25 ml d'huile d'olive et les rôtir 25 minutes en les retournant, jusqu'à ce qu'ils soient dorés.",
            "Faire sauter 100 g d'oignon et 400 g de champignons émincés dans 20 ml d'huile d'olive, 10 minutes, puis ajouter 12 g d'ail et 20 g de persil hachés et 1 g de poivre.",
            "Servir les frites de polenta avec la poêlée de champignons.",
        ]),
        ("time", 20, 60, 55),
    ],

    # ── Risotto champignons : cèpes mantecato / forestier au thym / vegan noisettes / vegan épinards ──
    "rice_risotto_ai_funghi_395f00": [
        ("title", "Risotto ai porcini, mantecato au beurre et parmesan"),
        ("desc", "Risotto piémontais aux cèpes : une partie des champignons cuite avec le riz pour parfumer le "
                 "bouillon, l'autre saisie à part, puis mantecatura au beurre froid et au parmesan."),
        ("origin", {"region": "piemont", "city": ""}),
        ("compo", [
            ("white_rice_raw_seed_unenriched", 280, "g", "base", "sauteed"),
            ("porcini_mushroom_raw", 250, "g", "vegetable"),
            ("button_mushroom_raw", 100, "g", "vegetable"),
            ("onion_raw", 100, "g", "aromatic"),
            ("vegetable_stock_dried", 9, "g", "vegetable"),
            ("water", 900, "ml", "vegetable"),
            ("olive_oil_extra_virgin_plant", 20, "ml", "fat"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("parmesan_grated_dried_cow", 40, "g", "finishing"),
            ("parsley_fresh_herb", None, "1 poignée", "serving_suggestion"),
        ]),
        ("steps", _risotto("10 ml d'huile d'olive", "100 g d'oignon ciselé et 100 g de champignons de Paris hachés") + [
            "Pendant ce temps, saisir 250 g de cèpes en lamelles dans 10 ml d'huile d'olive à feu vif, 5 minutes. En ajouter la moitié au riz à mi-cuisson.",
            "Hors du feu, incorporer 30 g de beurre froid en dés et 40 g de parmesan, couvrir et laisser reposer 2 minutes.",
            "Servir couvert du reste des cèpes saisis.",
        ]),
        ("time", 15, 0, 30),
    ],
    "rice_risotto_aux_champignon_25ed38": [
        ("title", "Risotto forestier aux pleurotes et au thym"),
        ("desc", "Risotto aux champignons des bois (pleurotes, cèpes et champignons de Paris) rôtis au thym, "
                 "lié au beurre et au parmesan."),
        ("compo", [
            ("white_rice_raw_seed_unenriched", 280, "g", "starch"),
            ("oyster_mushroom_raw", 150, "g", "vegetable"),
            ("porcini_mushroom_raw", 100, "g", "vegetable"),
            ("button_mushroom_raw", 150, "g", "vegetable"),
            ("onion_raw", 80, "g", "aromatic"),
            ("thyme_fresh_herb", 3, "g", "herb"),
            ("vegetable_stock_dried", 9, "g", "liquid"),
            ("water", 900, "ml", "liquid"),
            ("butter_sup80pct", 40, "g", "fat"),
            ("parmesan_grated_dried_cow", 30, "g", "dairy"),
            ("black_pepper_spice", 1, "g", "seasoning"),
        ]),
        ("steps", [
            "Faire dorer 150 g de pleurotes, 100 g de cèpes et 150 g de champignons de Paris en morceaux dans 15 g de beurre à feu vif, 8 minutes, avec 3 g de thym. Réserver.",
        ] + _risotto("15 g de beurre", "80 g d'oignon ciselé") + [
            "Ajouter les champignons les 3 dernières minutes.",
            "Hors du feu, incorporer 10 g de beurre froid, 30 g de parmesan et 1 g de poivre, puis servir.",
        ]),
        ("time", 15, 0, 35),
    ],
    "rice_risotto_ai_funghi_vegan_41360e": [
        ("title", "Risotto aux champignons rôtis et noisettes (vegan)"),
        ("desc", "Risotto crémeux sans beurre ni fromage : champignons rôtis au four, levure nutritionnelle "
                 "pour le côté fromagé et noisettes torréfiées pour le croquant."),
        ("compo", [
            ("white_rice_raw_seed_unenriched", 280, "g", "ingredient"),
            ("button_mushroom_raw", 300, "g", "ingredient"),
            ("porcini_mushroom_raw", 150, "g", "vegetable"),
            ("onion_raw", 120, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("vegetable_stock_dried", 9, "g", "ingredient"),
            ("water", 900, "ml", "ingredient"),
            ("nutritional_yeast_flakes", 25, "g", "ingredient"),
            ("hazelnut_dry_roasted_dried_unsalted", 30, "g", "garnish"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Préchauffer le four à 220°C. Mélanger 300 g de champignons et 150 g de cèpes en morceaux avec 20 ml d'huile d'olive et rôtir 20 minutes.",
        ] + _risotto("20 ml d'huile d'olive", "120 g d'oignon ciselé et 9 g d'ail haché") + [
            "Hors du feu, incorporer 25 g de levure nutritionnelle et les deux tiers des champignons rôtis.",
            "Servir couvert du reste des champignons, de 30 g de noisettes concassées et de 1 g de poivre.",
        ]),
        ("time", 15, 0, 35),
    ],
    "rice_risotto_aux_champignons_v_13d611": [
        ("title", "Risotto aux champignons et aux épinards (vegan)"),
        ("desc", "Risotto vert et doux : champignons de Paris sautés, jeunes pousses d'épinards fondues au dernier "
                 "moment, levure nutritionnelle et zeste de citron."),
        ("compo", [
            ("white_rice_raw_seed_unenriched", 280, "g", "ingredient"),
            ("button_mushroom_raw", 300, "g", "ingredient"),
            ("spinach_raw_baby", 150, "g", "vegetable"),
            ("yellow_onion_raw", 120, "g", "aromatic_base"),
            ("garlic_raw", 9, "g", "aromatic"),
            ("vegetable_stock_dried", 9, "g", "ingredient"),
            ("water", 900, "ml", "ingredient"),
            ("nutritional_yeast_flakes", 25, "g", "ingredient"),
            ("olive_oil_extra_virgin_plant", 30, "ml", "fat"),
            ("vegan_butter", 20, "g", "fat"),
            ("lemon_peel_raw", 3, "g", "aromatic"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", [
            "Faire sauter 300 g de champignons émincés dans 15 ml d'huile d'olive à feu vif, 6 minutes. Réserver.",
        ] + _risotto("15 ml d'huile d'olive", "120 g d'oignon ciselé et 9 g d'ail haché") + [
            "Ajouter les champignons et 150 g de jeunes pousses d'épinards, puis remuer 1 minute jusqu'à ce qu'elles tombent.",
            "Hors du feu, incorporer 20 g de beurre végétal, 25 g de levure nutritionnelle, 3 g de zeste de citron et 1 g de poivre, puis servir.",
        ]),
        ("time", 15, 0, 30),
    ],

    # ── Risotto citron : d'Amalfi / vegan citron-fenouil ──
    "rice_risotto_al_limone_4088e5": [
        ("title", "Risotto al limone d'Amalfi"),
        ("desc", "Risotto de la côte amalfitaine : zeste et jus de citron, beurre et parmesan, relevé "
                 "de feuilles de basilic, à la fois crémeux et très frais."),
        ("origin", {"region": "campania", "city": "amalfi"}),
        ("compo", [
            ("white_rice_raw_seed_unenriched", 280, "g", "base", "sauteed"),
            ("yellow_onion_raw", 100, "g", "aromatic"),
            ("vegetable_stock_dried", 9, "g", "vegetable"),
            ("water", 900, "ml", "vegetable"),
            ("olive_oil_plant", 15, "ml", "fat"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("parmesan_grated_dried_cow", 40, "g", "finishing"),
            ("lemon_juice", 30, "ml", "seasoning"),
            ("lemon_peel_raw", 6, "g", "aromatic"),
            ("basil_fresh_herb", 8, "g", "herb"),
        ]),
        ("steps", _risotto("15 ml d'huile d'olive", "100 g d'oignon ciselé") + [
            "Hors du feu, incorporer 30 g de beurre froid, 40 g de parmesan, 6 g de zeste de citron et 30 ml de jus de citron.",
            "Couvrir 2 minutes, puis servir parsemé de 8 g de basilic ciselé.",
        ]),
        ("time", 10, 0, 30),
    ],
    "rice_risotto_al_limone_vegan_a234ae": [
        ("title", "Risotto au citron et au fenouil (vegan)"),
        ("desc", "Risotto sans produit laitier au fenouil fondant, zeste et jus de citron, fini à l'huile d'olive "
                 "et à la levure nutritionnelle, avec les pluches de fenouil."),
        ("origin", {"region": "", "city": ""}),
        ("compo", [
            ("white_rice_raw_seed_unenriched", 280, "g", "ingredient"),
            ("fennel_raw", 250, "g", "vegetable"),
            ("yellow_onion_raw", 100, "g", "aromatic_base"),
            ("garlic_raw", 6, "g", "aromatic"),
            ("olive_oil_extra_virgin_plant", 40, "ml", "fat"),
            ("vegetable_stock_dried", 9, "g", "ingredient"),
            ("water", 900, "ml", "ingredient"),
            ("nutritional_yeast_flakes", 25, "g", "ingredient"),
            ("lemon_juice", 30, "ml", "fruit"),
            ("lemon_peel_raw", 5, "g", "aromatic"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", _risotto("25 ml d'huile d'olive", "100 g d'oignon ciselé, 6 g d'ail et 250 g de fenouil émincé finement") + [
            "Hors du feu, incorporer 15 ml d'huile d'olive, 25 g de levure nutritionnelle, 5 g de zeste et 30 ml de jus de citron, et 1 g de poivre.",
            "Servir parsemé des pluches de fenouil.",
        ]),
        ("time", 15, 0, 30),
    ],

    # ── Risotto asperges : blanches de Bassano / vegan vertes et petits pois ──
    "rice_risotto_citron_asperges_f2f765": [
        ("title", "Risotto aux asperges blanches de Bassano"),
        ("desc", "Risotto vénitien de printemps : asperges blanches dont les parures parfument le bouillon, "
                 "pointes ajoutées en fin de cuisson, beurre, parmesan et zeste de citron."),
        ("origin", {"region": "veneto", "city": "bassano"}),
        ("compo", [
            ("white_rice_raw_seed_unenriched", 280, "g", "base", "sauteed"),
            ("white_asparagus_raw_peeled", 400, "g", "vegetable"),
            ("yellow_onion_raw", 100, "g", "aromatic"),
            ("vegetable_stock_dried", 9, "g", "vegetable"),
            ("water", 1000, "ml", "vegetable"),
            ("olive_oil_plant", 15, "ml", "fat"),
            ("butter_sup80pct", 30, "g", "fat"),
            ("parmesan_grated_dried_cow", 40, "g", "finishing"),
            ("lemon_peel_raw", 3, "g", "aromatic"),
        ]),
        ("steps", [
            "Éplucher 400 g d'asperges blanches, couper les pointes et réserver, tailler les tiges en rondelles. Faire frémir les épluchures 15 minutes dans 1 L d'eau avec 9 g de bouillon déshydraté, puis filtrer.",
            "Faire suer 100 g d'oignon ciselé et les rondelles d'asperges dans 15 ml d'huile d'olive, 5 minutes.",
            "Ajouter 280 g de riz et le nacrer 2 minutes.",
            "Mouiller louche par louche avec le bouillon chaud en remuant, 18 minutes, en ajoutant les pointes à mi-cuisson.",
            "Hors du feu, incorporer 30 g de beurre, 40 g de parmesan et 3 g de zeste de citron, puis servir.",
        ]),
        ("time", 20, 0, 40),
    ],
    "rice_risotto_citron_asperges_v_e20e67": [
        ("title", "Risotto aux asperges vertes, petits pois et menthe (vegan)"),
        ("desc", "Risotto printanier sans lactose : asperges vertes, petits pois et menthe fraîche, lié à "
                 "l'huile d'olive, à la levure nutritionnelle et au citron."),
        ("compo", [
            ("white_rice_raw_seed_unenriched", 280, "g", "ingredient"),
            ("green_asparagus_raw", 250, "g", "vegetable"),
            ("green_peas_raw", 150, "g", "vegetable"),
            ("yellow_onion_raw", 100, "g", "aromatic_base"),
            ("vegetable_stock_dried", 9, "g", "ingredient"),
            ("water", 900, "ml", "ingredient"),
            ("nutritional_yeast_flakes", 25, "g", "ingredient"),
            ("olive_oil_extra_virgin_plant", 30, "ml", "fat"),
            ("vegan_butter", 15, "g", "fat"),
            ("lemon_juice", 20, "ml", "fruit"),
            ("mint_fresh_herb", 8, "g", "herb"),
            ("black_pepper_spice", 1, "g", "spice"),
        ]),
        ("steps", _risotto("20 ml d'huile d'olive", "100 g d'oignon ciselé") + [
            "À mi-cuisson, ajouter 250 g d'asperges vertes en tronçons (pointes réservées) ; 5 minutes avant la fin, ajouter les pointes et 150 g de petits pois.",
            "Hors du feu, incorporer 15 g de beurre végétal, 10 ml d'huile d'olive, 25 g de levure nutritionnelle, 20 ml de jus de citron et 1 g de poivre.",
            "Servir parsemé de 8 g de menthe ciselée.",
        ]),
        ("time", 15, 0, 30),
    ],
}
