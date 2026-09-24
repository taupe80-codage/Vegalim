"""Variantes 21 : deux plats mal rattachés, repérés en préparant le lot Caraïbes/océan Indien.

« Callaloo » était classé cuisine indienne (Punjab) alors que c'est le ragoût de feuilles des
Antilles ; « Tajine Pois Chiches Citron » était en cuisine « international » avec 160 g de citron
confit pour quatre.
"""

VARIANTS = {
    "main_callaloo_f7ae5c": [
        ("title", "Callaloo, ragoût caribéen d'épinards au lait de coco"),
        ("desc", "Ragoût des Antilles anglophones : des feuilles vertes fondues dans du lait de "
                 "coco avec des gombos qui l'épaississent naturellement, parfumé au thym et à "
                 "l'oignon vert, écrasé à la fourchette et servi sur du riz."),
        ("origin", {"cuisine": "trinidadian", "country": "trinidad_and_tobago",
                    "region": "port_of_spain", "city": ""}),
        ("add", "okra", 200, "g", "vegetable"),
        ("add", "green_onion_raw", 60, "g", "aromatic"),
        ("steps", [
            "Laver 300 g d'épinards et les émincer en lanières de 2 à 3 cm ; couper 200 g de "
            "gombos en rondelles.",
            "Faire revenir 150 g d'oignon jaune, 60 g d'oignon vert et 9 g d'ail dans 25 ml "
            "d'huile d'olive, 5 minutes à feu moyen.",
            "Ajouter 300 g de tomates concassées et 3 g de thym séché, cuire 3 minutes.",
            "Incorporer les gombos, verser 400 ml de lait de coco et mijoter 10 minutes à "
            "couvert : les gombos libèrent leur mucilage et lient la sauce.",
            "Ajouter les épinards et poursuivre 10 minutes, jusqu'à ce qu'ils soient fondants et "
            "la sauce d'un vert profond.",
            "Écraser grossièrement à la fourchette, saler avec 5 g de sel et servir sur un lit de "
            "riz chaud.",
        ]),
    ],
    "dal_tajine_pois_chiches_citron_047521": [
        ("title", "Tajine de pois chiches au citron confit et aux olives"),
        ("desc", "Tajine marocain de pois chiches mijotés avec gingembre, cumin et curcuma, "
                 "relevé de quartiers de citron confit et d'olives noires : une sauce courte et "
                 "très salée-acide, à servir avec du pain ou du couscous."),
        ("origin", {"cuisine": "moroccan", "country": "morocco", "region": "fes", "city": "fes"}),
        ("qty", "preserved_lemon", 80),
        ("txt", "Ajouter 160 g de citron confit", "Ajouter 80 g de citron confit"),
    ],
}
