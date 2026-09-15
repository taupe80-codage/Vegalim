"""Lot 3 : fin des préparations de base, kombucha, pains et plats à base de pain/tortilla."""

PATCHES = {
    "base_tomato_paste_26412f": [
        ("yield", 0.22),  # texte : réduit de 75-80 %
    ],
    "base_vegetable_broth_303b7d": [
        ("txt", "3g de thym frais", "3g de thym séché"),
    ],
    "base_vegetarian_fish_sauce_536a33": [
        ("add", "water", 100, "ml", "liquid"),
        ("txt", "Servir aussitôt dans des bols préchauffés, garni d'un filet de citron vert et d'une feuille de coriandre fraîche ciselée.",
         "Laisser refroidir, verser dans une bouteille propre et conserver au réfrigérateur jusqu'à 2 semaines."),
    ],
    "base_vegetarian_oyster_sauce_b74b21": [
        ("add", "water", 220, "ml", "liquid"),
        ("txt", "Réhydrater 150g de champignons shiitake frais dans 200ml d'eau chaude pendant environ 20 minutes, jusqu'à ce qu'ils soient tendres et leur eau de réhydratation soit trouble et parfumée",
         "Faire infuser 150g de champignons shiitake frais émincés dans 200ml d'eau chaude pendant environ 20 minutes, jusqu'à ce qu'ils soient tendres et que l'eau soit trouble et parfumée"),
        ("txt", "les champignons shiitake réhydratés avec leur eau de réhydratation", "les champignons shiitake avec leur eau d'infusion"),
        ("txt", "Servir la sauce chaude, garnie de quelques feuilles de coriandre fraîche ciselée si désiré.",
         "Laisser refroidir et conserver en bocal au réfrigérateur jusqu'à 2 semaines."),
    ],
    "base_za_atar_2badf3": [
        ("ing", "thyme_fresh_herb", "thyme_dried_herb"),
        ("txt", "Servir sans attendre, mélangé à l'huile d'olive", "Servir mélangé à l'huile d'olive"),
        ("step-", "Servir dans des bols préchauffés"),
    ],
    "beverage_kombucha_3df24c": [
        ("ing", "matcha_green_tea_powder", "tea_leaf"),
        ("txt", "8 g de thé vert", "8 g de thé vert en feuilles"),
        ("time", 20, 14400, 10),  # 7 à 14 jours de fermentation
    ],
    "bread_acorda_a_lail_et_coriandr_048494": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 20),
        ("txt", ", de coriandre ou de lait si besoin", " ou de coriandre si besoin"),
        ("step-", "Laisser reposer pendant 2 minutes avant de servir"),
    ],
    "bread_bannock_e03ffe": [
        ("qty", "water", 120),
        ("txt", "Versez 500ml d'eau tiède", "Versez 120ml d'eau tiède"),
        ("txt", "40g de beurre fondue", "40g de beurre fondu"),
        ("txt", "votre confiture végétarien préférée", "votre confiture préférée"),
        ("txt", ", et servez-le dans un plat préchauffé pour conserver la chaleur", ""),
        ("dish", "bread"),
    ],
    "bread_bao_ff9db9": [
        ("add", "water", 100, "ml", "liquid"),
        ("txt", "7g de levure sèche", "7g de levure fraîche"),
        ("txt", "Pétrir 5 minutes à feu doux", "Pétrir 5 minutes"),
        ("txt", "jusqu'à ce que les bao soient dorés et gonflés", "jusqu'à ce que les bao soient gonflés"),
        ("txt", " Servir sans attendre, accompagné d'une salade verte ou d'un bol de riz végétal, en profitant de la chaleur et de la fraîcheur des ingrédients.", ""),
    ],
    "bread_buckwheat_crepe_03db22": [
        ("txt", "Ajouter progressivement 500ml d'eau", "Ajouter l'œuf battu, puis progressivement 500ml d'eau"),
        ("txt", "20g de beurre fondue", "20g de beurre fondu"),
    ],
    # recette refaite : chilaquiles rojos (tortillas frites, sauce tomate, œuf au plat, queso fresco)
    "bread_chilaquiles_13372e": [
        ("ing", "parmesan_grated_dried_cow", "queso_fresco_block_cow", 100),
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 10),
        ("del", "tomato_raw_ripe"),
        ("del", "milk_liquid_uht_3_5pct"),
        ("qty", "onion_raw", 150),
        ("qty", "table_salt_unenriched", 3),
        ("steps", [
            "Couper les tortillas en 6 triangles. Chauffer 30 ml d'huile d'olive dans une grande poêle à feu moyen-vif et faire dorer les triangles 3 à 4 minutes en les retournant, jusqu'à ce qu'ils soient croustillants. Égoutter sur du papier absorbant.",
            "Dans la même poêle, faire revenir l'oignon émincé 4 minutes à feu moyen jusqu'à ce qu'il soit translucide.",
            "Ajouter la sauce tomate et le sel, puis laisser mijoter 5 minutes jusqu'à léger épaississement.",
            "Pendant ce temps, cuire les œufs au plat dans les 15 ml d'huile restants, 3 minutes, jusqu'à ce que le blanc soit pris et le jaune encore coulant.",
            "Hors du feu, ajouter les tortillas croustillantes dans la sauce et mélanger 1 minute pour les enrober sans les ramollir complètement.",
            "Répartir dans les assiettes, déposer un œuf sur chaque portion, émietter le queso fresco et parsemer de coriandre ciselée. Servir aussitôt.",
        ]),
        ("time", 15, 0, 15),
    ],
    "bread_enchiladas_fe7221": [
        ("ing", "parmesan_grated_dried_cow", "queso_fresco_block_cow", 120),
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
        ("qty", "onion_raw", 150),
        ("txt", "150g de parmesan râpé et 300g d'oignon émincé", "80g de queso fresco émietté et 150g d'oignon émincé"),
        ("txt", "Parsemez de parmesan râpé", "Parsemez du reste de queso fresco"),
        ("txt", "jusqu'à ce que le fromage soit fondu et gratiné, avec une couleur dorée et une texture croustillante",
         "jusqu'à ce que la sauce bouillonne et que le fromage soit doré"),
        ("txt", "Garnissez d'une coriandre fraîche et d'un peu de crème fraîche, puis servez chaud.",
         "Garnissez de coriandre fraîche ciselée, puis servez chaud."),
        ("step-", "Servez dans des bols préchauffés"),
    ],
    "bread_focaccia_bf8608": [
        ("qty", "water", 150),
        ("txt", "7g de levure sèche", "7g de levure fraîche"),
        ("txt", "350ml d'eau tiède", "150ml d'eau tiède"),
    ],
    # panure en surquantité, fromage fantôme, huile comptée deux fois : recette refaite
    "bread_katsu_bf3f1e": [
        ("qty", "rice_flour", 60),
        ("qty", "egg_raw", 110),
        ("qty", "onion_raw", 150),
        ("steps", [
            "Rincer 300 g de riz japonais jusqu'à ce que l'eau soit claire, puis le cuire à couvert avec 350 ml d'eau pendant 12 minutes à feu doux. Laisser reposer 10 minutes hors du feu.",
            "Émincer l'oignon et l'ail, puis les faire revenir 5 minutes à feu moyen dans 15 ml d'huile de tournesol jusqu'à ce que l'oignon soit doré.",
            "Ajouter le curry en poudre et 20 g de farine de riz, remuer 1 minute, puis verser progressivement 400 ml d'eau chaude et le bouillon en poudre en fouettant. Laisser mijoter 10 minutes jusqu'à ce que la sauce nappe la cuillère.",
            "Égoutter le tofu, le couper en 4 tranches épaisses et les éponger. Les passer dans 40 g de farine de riz, puis dans les œufs battus, puis dans la chapelure panko.",
            "Chauffer 30 ml d'huile de tournesol dans une grande poêle à feu moyen-vif et dorer les tranches 3 à 4 minutes de chaque côté, jusqu'à ce que la panure soit croustillante. Égoutter sur du papier absorbant.",
            "Trancher le katsu, le dresser sur le riz et napper de sauce curry. Servir chaud.",
        ]),
        ("time", 20, 10, 30),
    ],
    "bread_mexican_enfrijoladas_578ae7": [
        ("ing", "parmesan_grated_dried_cow", "queso_fresco_block_cow", 80),
        ("add", "cumin_spice_seed", 3, "g", "spice"),
        ("add", "table_salt_unenriched", 4, "g", "seasoning"),
        ("qty", "onion_raw", 150),
        ("txt", "Préchauffer le four à 200°C. Passer les enfrijoladas sous le gril chaud", "Préchauffer le gril du four. Passer les enfrijoladas sous le gril"),
        ("txt", "garnies d'oignon rouge, de coriandre fraîche et de piment jalapeño, si désiré",
         "garnies de queso fresco émietté, de coriandre fraîche et, si désiré, de piment jalapeño"),
    ],
    "bread_migas_portugaises_76818b": [
        ("add", "water", 100, "ml", "liquid"),
        ("txt", "150g de pain complet rassis", "150g de pain blanc rassis"),
    ],
    "bread_panzanella_italienne_307da1": [
        ("txt", "le pain complet de 150g", "le pain rassis de 150g"),
    ],
    "bread_quenelles_de_pain_813118": [
        ("qty", "wheat_all_purpose_flour_unenriched_unbleached", 60),
        ("txt", "200 g de farine", "60 g de farine"),
        ("add", "nutmeg_spice", 1, "g", "spice"),
    ],
    "bread_salmorejo_a156e9": [
        ("steps", [
            "Couper les tomates en quartiers. Faire tremper le pain rassis 5 minutes dans un peu d'eau froide, puis l'essorer.",
            "Mixer les tomates, le pain essoré et l'ail à pleine puissance pendant 2 minutes, puis ajouter l'huile d'olive en filet sans cesser de mixer, jusqu'à obtenir une crème lisse et épaisse.",
            "Ajouter le vinaigre et le sel, mixer à nouveau, goûter et ajuster.",
            "Passer au chinois fin en pressant bien pour retirer les peaux et les graines.",
            "Réfrigérer au moins 2 heures.",
            "Servir très froid en petits bols, garni des œufs durs écalés et hachés.",
        ]),
    ],
    "bread_spanakopita_a_la_muscade_6a9e84": [
        ("ing", "spinach_cooked", "spinach_raw_mature", 500),
        ("qty", "nutmeg_spice", 1),
        ("qty", "yellow_onion_raw", 150),
        ("txt", "300g d'épinards crus", "500g d'épinards crus"),
        ("txt", "300g d'oignon jaune", "150g d'oignon jaune"),
        ("txt", "150g de fromage végétal râpé, 1 cuillère à soupe de graines de lin mélangées à 3 cuillères à soupe d'eau (liant), 5g de muscade",
         "150g de tofu ferme émietté, 1g de muscade"),
    ],
    "bread_tacos_6fd5c2": [
        ("ing", "lime_raw", "lime_juice_fresh", 40, "ml"),
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
        ("txt", "faire revenir 150g d'oignon rouge et 9g d'ail", "faire revenir la moitié de l'oignon rouge (75g) et 9g d'ail"),
        ("txt", "émincer 150g d'oignon rouge en fines lamelles", "émincer le reste de l'oignon rouge en fines lamelles"),
        ("txt", "un trait de jus de 140g de citron vert, en pressant légèrement le citron pour libérer les huiles essentielles et les saveurs",
         "un trait de jus de citron vert"),
        ("step-", "n'oubliez pas de partager vos créations culinaires"),
    ],
}
