"""Lot 18 : pico de gallo, piperade, pisto, pkhali, plantains, poêlée."""

PATCHES = {
    "main_pico_de_gallo_31e006": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 15),
        ("ing", "lime_raw", "lime_juice_fresh", 40, "ml"),
        ("qty", "table_salt_unenriched", 2),
        ("dish", "starter"),
        ("txt", ", puis blanchissez-le pendant 2 minutes pour le rendre plus tendre et éliminer l'amertume", ""),
    ],
    "main_piperade_basque_3e1c65": [
        ("qty", "olive_oil_plant", 30),
        ("add", "table_salt_unenriched", 4, "g", "seasoning"),
        ("txt", "dans 3ml d'huile d'olive", "dans 30ml d'huile d'olive"),
        ("txt", "640g de poivrons rouges et verts en lanières", "640g de poivrons rouges en lanières"),
    ],
    "main_pisto_espagnol_7a98be": [
        ("add", "thyme_fresh_herb", 3, "g", "herb"),
        ("txt", "d'herbes fraîches, telles que du thym ou du romarin", "de 3 g de thym frais"),
        ("txt", "accompagné de pain grillé ou de riz basmati", "accompagné de pain grillé"),
    ],
    "main_pisto_manchego_09ba97": [
        ("txt", "Faire revenir 1 oignon rouge haché finement", "Faire revenir 150 g d'oignon haché finement"),
        ("txt", "Ajouter 1 poivron rouge coupé en dés", "Ajouter 320 g de poivron rouge coupé en dés"),
        ("txt", "Rectifier l'assaisonnement avec 2 g de poivre et 1 g de sel, pour équilibrer les saveurs et ajouter une touche de piquant.",
         "Creuser deux puits dans le pisto, y casser les œufs (55 g) et couvrir 3 minutes, jusqu'à ce qu'ils soient pris. Rectifier l'assaisonnement avec 2 g de poivre et 1 g de sel."),
    ],
    "main_pkhali_46d354": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 15),
        ("qty", "pomegranate_raw", 80),
        ("dish", "starter"),
        ("txt", "Ajoutez 280g de graines de grenade fraîche", "Ajoutez 80g de graines de grenade fraîche"),
        ("step-", "Enfournez les boulettes pendant 10 minutes à 180°C"),
    ],
    "main_plantain_frit_au_citron_60d4e3": [
        ("ing", "lemon_raw", "lemon_juice", 30, "ml"),
        ("txt", "Servir aussitôt dans des assiettes préchauffées.", "Servir aussitôt."),
        ("time", 7, 0, 18),
    ],
    "main_plantain_frit_nature_323054": [
        ("txt", "Servir les plantains frits chauds, dans des bols préchauffés, accompagnés", "Servir les plantains frits chauds, accompagnés"),
        ("step-", "Démouler sur un plat de service"),
    ],
    "main_poelee_de_legumes_f74508": [
        ("txt", "les oignons blancs et l'ail en morceaux", "l'oignon et l'ail en morceaux"),
        ("txt", "Incorporer les oignons blancs et l'ail.", "Incorporer l'oignon et l'ail."),
        ("txt", ", avec un peu de levure nutritionnelle râpée pour ajouter une touche de saveur umami, laissant", ", en laissant"),
    ],
}
