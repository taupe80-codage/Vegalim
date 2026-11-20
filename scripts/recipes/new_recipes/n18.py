"""Lot 18 : préparations de base vegan (5 sous-recettes, 2026-11-20).

Dix variantes vegan restaient « incomplètes » faute d'équivalent vegan de leur
préparation de base ou d'un produit (variants.py, VEGAN_SUBS_CIQUAL) : roux de curry
japonais au beurre, spätzle et galette de sarrasin aux œufs et au lait, glace à la
vanille, biscuits à la cuillère. Chacune reçoit ici sa version vegan, à la même
échelle que l'originale pour que les quantités des plats restent justes.
"""
from ._schema import recipe

RECIPES = [
    recipe(
        rid="base_roux_curry_japonais_vegetal_f245c7",
        fr="Roux de curry japonais au beurre végétal",
        en="Plant-Based Japanese Curry Roux",
        cuisine="japanese", country="japan",
        dish="base", meal="base", servings=8, prep=5, rest=10, cook=15,
        texture=("pâteux",), taste=("épicé", "doux"),
        technique=("sauteing", "sauce_making"), difficulty="easy", spice=1,
        desc="Le roux qui épaissit et parfume le curry japonais, fait au beurre végétal : farine "
             "blondie, curry en poudre, pomme râpée et concentré de tomate, pour la douceur et la "
             "rondeur des tablettes du commerce, sans produit laitier.",
        compo=[
            ("vegan_butter", 50, "g", "fat"),
            ("wheat_all_purpose_flour_unenriched_unbleached", 50, "g", "thickener"),
            ("curry_powder", 15, "g", "spice"),
            ("apple_raw_with_skin", 20, "g", "sweetener"),
            ("white_sugar", 5, "g", "sweetener"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("tomato_paste_unsalted_canned", 10, "g", "umami"),
            ("garlic_raw", 5, "g", "aromatic"),
        ],
        steps=[
            "Faire fondre 50 g de beurre végétal dans une poêle à feu moyen, ajouter 5 g d'ail "
            "émincé et le faire revenir 2 minutes sans le colorer.",
            "Ajouter 50 g de farine et cuire 5 minutes en remuant sans cesse, jusqu'à ce que le "
            "roux prenne une couleur noisette.",
            "Hors du feu, incorporer 15 g de curry en poudre, 5 g de sucre, 5 g de sel, 10 g de "
            "concentré de tomate et 20 g de pomme finement râpée.",
            "Remettre 2 minutes sur feu doux en remuant, verser dans un petit plat et laisser "
            "prendre 10 minutes au frais avant de couper en carrés.",
        ],
    ),
    recipe(
        rid="base_spaetzle_vegan_265b64",
        fr="Spätzle vegan au lait de soja",
        en="Vegan Spätzle",
        cuisine="alsatian", country="france", region="alsace",
        dish="base", meal="base", servings=4, prep=15, rest=10, cook=20,
        texture=("moelleux",), taste=("neutre",),
        technique=("boiling", "sauteing"), difficulty="medium",
        desc="Les pâtes fraîches alsaciennes sans œuf : une pâte de farine, de lait de soja et "
             "d'eau, battue jusqu'à faire des bulles, qu'on fait tomber en filaments irréguliers "
             "dans l'eau bouillante, puis qu'on fait dorer à la poêle.",
        compo=[
            ("wheat_all_purpose_flour_unenriched_unbleached", 300, "g", "base"),
            ("soybean_milk_unsweetened_plant", 200, "ml", "liquid"),
            ("water", 100, "ml", "liquid"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("nutmeg_spice", 1, "g", "spice"),
            ("olive_oil_plant", 30, "ml", "fat"),
        ],
        steps=[
            "Mélanger 300 g de farine, 5 g de sel et 1 g de muscade râpée, verser 200 ml de lait "
            "de soja et 100 ml d'eau, et battre 3 minutes à la cuillère en bois jusqu'à ce que la "
            "pâte, épaisse et élastique, fasse des bulles.",
            "Laisser reposer la pâte 10 minutes.",
            "Porter une grande casserole d'eau salée à ébullition, y faire tomber la pâte à "
            "travers une râpe à spätzle par petites quantités et retirer les spätzle à "
            "l'écumoire dès qu'ils remontent, après 2 minutes environ.",
            "Les faire dorer 5 minutes dans 30 ml d'huile d'olive à la poêle, à feu moyen.",
        ],
    ),
    recipe(
        rid="base_galette_sarrasin_eau_533afe",
        fr="Galette de sarrasin à l'eau",
        en="Buckwheat Galette (Water Batter)",
        cuisine="french", country="france", region="bretagne",
        dish="base", meal="base", servings=4, prep=10, rest=60, cook=20,
        texture=("souple", "croustillant"), taste=("noisette",),
        technique=("pan_frying",), difficulty="medium",
        desc="La galette de blé noir comme on la fait en Haute-Bretagne : de la farine de "
             "sarrasin, de l'eau et du sel, sans œuf ni lait. La pâte repose une heure, puis "
             "cuit très chaud pour une galette fine, souple au centre et dentelée au bord.",
        compo=[
            ("buckwheat_flour", 250, "g", "base"),
            ("water", 550, "ml", "liquid"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("sunflower_oil_plant", 10, "ml", "fat"),
        ],
        steps=[
            "Mélanger 250 g de farine de sarrasin et 5 g de sel, verser 550 ml d'eau froide peu "
            "à peu en fouettant jusqu'à obtenir une pâte lisse, un peu plus épaisse qu'une pâte "
            "à crêpes.",
            "Couvrir et laisser reposer 1 heure au frais.",
            "Graisser une crêpière bien chaude avec 10 ml d'huile de tournesol au fil des "
            "cuissons, étaler une louche de pâte et cuire chaque galette 2 minutes d'un côté "
            "et 1 minute de l'autre.",
            "Empiler les galettes sous un torchon jusqu'à utilisation.",
        ],
    ),
    recipe(
        rid="base_glace_vanille_vegan_4e694a",
        fr="Glace vegan à la vanille et au lait de coco",
        en="Vegan Coconut Vanilla Ice Cream",
        cuisine="french", country="france",
        dish="base", meal="base", servings=6, prep=15, rest=360, cook=5,
        texture=("crémeux",), taste=("sucré", "vanillé"),
        technique=("freezing",), difficulty="easy",
        desc="Une glace sans sorbetière, crémeuse grâce au lait de coco et à un peu de fécule : "
             "la crème vanillée cuit deux minutes pour épaissir, puis prend au congélateur en "
             "étant remuée deux fois pour rester lisse.",
        compo=[
            ("coconut_milk_plant", 400, "ml", "base"),
            ("soybean_milk_unsweetened_plant", 200, "ml", "liquid"),
            ("white_sugar", 90, "g", "sweetener"),
            ("cornstarch_flour", 15, "g", "thickener"),
            ("vanilla_extract", 10, "ml", "flavor"),
        ],
        steps=[
            "Délayer 15 g de fécule de maïs dans 200 ml de lait de soja, ajouter 400 ml de lait "
            "de coco et 90 g de sucre, et porter à frémissement en fouettant.",
            "Cuire 2 minutes jusqu'à ce que la crème nappe la cuillère, retirer du feu et "
            "ajouter 10 ml d'extrait de vanille.",
            "Laisser refroidir, verser dans une boîte et mettre 6 heures au congélateur, en "
            "fouettant la glace au bout de 2 heures puis de 4 heures.",
        ],
    ),
    recipe(
        rid="base_biscuits_cuillere_vegan_40fae8",
        fr="Biscuits à la cuillère vegan à l'aquafaba",
        en="Vegan Aquafaba Ladyfingers",
        cuisine="french", country="france",
        dish="base", meal="base", servings=6, prep=20, cook=15,
        texture=("léger", "croquant"), taste=("sucré",),
        technique=("baking", "whipping"), difficulty="medium",
        allow_similar=("biscuits",),       # « Biscuits et sauce blanche » : biscuits salés américains
        desc="Les biscuits du tiramisu et de la charlotte, sans œuf : le jus de pois chiches "
             "monté en neige ferme remplace les blancs, la farine et la fécule sont incorporées "
             "délicatement, et les biscuits cuisent doucement pour rester légers.",
        compo=[
            ("aquafaba", 120, "ml", "binder"),
            ("white_sugar", 90, "g", "sweetener"),
            ("wheat_all_purpose_flour_unenriched_unbleached", 90, "g", "base"),
            ("cornstarch_flour", 30, "g", "thickener"),
            ("baking_powder", 4, "g", "leavening"),
            ("vanilla_extract", 5, "ml", "flavor"),
        ],
        steps=[
            "Monter 120 ml d'aquafaba en neige ferme au batteur électrique pendant 5 minutes, "
            "puis ajouter 90 g de sucre en pluie et fouetter encore 5 minutes jusqu'à obtenir "
            "une meringue brillante ; ajouter 5 ml d'extrait de vanille.",
            "Tamiser 90 g de farine, 30 g de fécule de maïs et 4 g de levure chimique, et les "
            "incorporer à la spatule en soulevant la meringue.",
            "Dresser des bâtonnets de 10 cm à la poche sur une plaque couverte de papier "
            "cuisson et cuire 15 minutes au four à 160 °C, jusqu'à ce qu'ils soient à peine "
            "dorés.",
            "Laisser sécher et refroidir sur une grille.",
        ],
    ),
]
