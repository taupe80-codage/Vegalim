"""Lot 23 : pâtes italiennes, ash reshteh, nouilles asiatiques, banh mi, bulgogi."""

PATCHES = {
    "pasta_pasta_al_pomodoro_3ffaef": [
        ("txt", "Ajuster sel et huile d'olive pour équilibrer les saveurs.", "Ajuster le sel (5 g) et parsemer de 30 g de parmesan râpé."),
    ],
    "pasta_pasta_alla_norma_5cc26e": [
        ("ing", "ricotta", "base_salted_ricotta_1ecd1c", 100),
        ("txt", "Chauffer 50 ml d'huile d'olive vierge extra", "Chauffer 45 ml d'huile d'olive vierge extra"),
        ("txt", "Ajouter la ricotta. Mélanger délicatement pour incorporer.", "Parsemer de 100 g de ricotta salée râpée et mélanger délicatement."),
        ("txt", "Servir aussitôt dans des bols préchauffés, parsemé", "Servir aussitôt, parsemé"),
    ],
    "pasta_pasta_alla_norma_a_la_ric_d282a6": [
        ("txt", "dans 50 ml d'huile d'olive à feu vif", "dans 45 ml d'huile d'olive à feu vif"),
        ("txt", "Ajoutez du fromage végétal râpé pour lier", "Ajoutez 60 g de ricotta de cajou pour lier"),
        ("txt", " Présentez dans des assiettes préchauffées pour conserver la fraîcheur et la texture al dente des pâtes.", ""),
    ],
    "pasta_pasta_e_fagioli_68905b": [
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Faire blanchir l'oignon dans l'huile d'olive", "Faire revenir l'oignon dans l'huile d'olive"),
    ],
    "pasta_persian_ash_reshteh_8cb79c": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 30),
        ("qty", "parsley_fresh_herb", 100),
        ("qty", "spinach_raw_mature", 300),
        ("qty", "table_salt_unenriched", 3),
        ("add", "water", 1200, "ml", "liquid"),
        ("txt", "puis couvrez-les d'eau et laissez mijoter pendant 20 minutes à 160°C", "puis couvrez-les de 1,2 L d'eau et laissez mijoter 20 minutes à feu doux"),
        ('txt', "Ajoutez l'ail et le curcuma", "Ajoutez l'ail, le curcuma et 5 g de piment séché"),
    ],
    "pasta_pesto_k3d2p1": [
        ("txt", "aux 400 g de pâtes fraîches", "aux 400 g de pâtes"),
        ("step-", "Pour un accompagnement idéal, proposer un vin blanc sec"),
    ],
    "pasta_pierogi_aux_pommes_de_6b3efe": [
        ("txt", "dans 2 cuillères à soupe de beurre à feu moyen", "dans 40 g de beurre à feu moyen"),
        ("time", 40, 20, 35),
    ],
    # les 4 L d'eau de cuisson étaient comptés comme ingrédient (1 kg par portion)
    "pasta_plain_k2d1p1": [
        ("del", "water"),
        ("ing", "coconut_oil_plant", "olive_oil_plant"),
        ("txt", "Porter 4 L d'eau à ébullition à feu vif, saler à 10 g/L pour obtenir une eau de cuisson parfumée, en surveillant la température pour atteindre les 100°C.",
         "Porter une grande casserole d'eau salée à ébullition."),
        ("txt", "Ajouter 10 ml d'huile de coco aux pâtes", "Ajouter 10 ml d'huile d'olive aux pâtes"),
        ("txt", "en les servant dans un bol préchauffé, garnies d'un filet d'huile de coco", "garnies d'un filet d'huile d'olive"),
    ],
    "pasta_puttanesca_v1x9q2": [
        ("qty", "chilli_pepper_raw", 10),
        ("qty", "black_olive_canned_in_oil", 60),
        ("qty", "capers_canned_in_vinegar", 20),
        ("qty", "garlic_raw", 12),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "25g d'ail haché finement et 30g de piment rouge concassé", "12g d'ail haché finement et 10g de piment rouge concassé"),
        ("txt", "90g d'olives noires dénoyautées et 35g de câpres rincées", "60g d'olives noires dénoyautées et 20g de câpres rincées"),
        ("txt", "en ajoutant 5g de sel pour rehausser", "en ajoutant 2g de sel pour rehausser"),
    ],
    "pasta_soupe_de_nouilles_thukpa_9c3ce8": [
        ("qty", "table_salt_unenriched", 2),
        ("qty", "soy_sauce_shoyu_reduced_sodium", 30),
        ("add", "coriander_raw_fresh_herb", 10, "g", "herb"),
        ("add", "green_onion_raw", 40, "g", "garnish"),
        ("txt", "Cuire 300 g de nouilles de riz séparément", "Cuire 300 g de nouilles séparément"),
        ("txt", "Ajouter un filet de sauce de soja (45 ml) et un peu de sel (5 g) pour amplifier les saveurs.",
         "Ajouter 30 ml de sauce soja et 2 g de sel en fin de cuisson."),
    ],
    "pasta_yakisoba_c6cc19": [
        ("add", "nutritional_yeast_flakes", 15, "g", "seasoning"),
        ("step-", "Servir chaud, garni de feuilles de chou vert ciselé"),
    ],
    "protein_banh_mi_tofu_9b1ea2": [
        ("ing", "coriander_spice_seed", "coriander_raw_fresh_herb", 10),
        ("qty", "cucumber_raw_with_skin", 150),
        ("txt", "de 350 g de concombre en tranches", "de 150 g de concombre en tranches"),
        ("step-", "Enfournez le sandwich pendant 2 minutes à 180°C"),
        ('txt', ', 11,2 g de gingembre frais et 3 g de coriandre moulue dans un bol', ' et 11 g de gingembre frais dans un bol'),
    ],
    "protein_buddhas_delight_f736c7": [
        ("ing", "shiitake_mushroom_raw", "shiitake_mushroom_dried", 30),
        ("ing", "coconut_milk_plant", "coconut_oil_plant", 30, "ml"),
        ("txt", "Ajouter les vermicelles de riz, les légumes", "Ajouter les vermicelles de soja, les légumes"),
    ],
    "protein_bulgogi_tofu_fc5de9": [
        ("qty", "sesame_oil_plant", 45),
        ("del", "table_salt_unenriched"),
        ("time", 15, 30, 15),
    ],
    "protein_bun_f5c7db": [
        ("txt", "Ajouter le chou vert, le tofu et le gingembre dans le wok. Faire sauter pendant 1 minute, en remuant constamment, jusqu'à ce que les ingrédients soient bien mélangés.",
         "Ajouter le chou vert, les champignons émincés, le tofu en dés et le gingembre dans le wok. Faire sauter 4 minutes, en remuant, jusqu'à ce que les champignons soient dorés."),
    ],
}
