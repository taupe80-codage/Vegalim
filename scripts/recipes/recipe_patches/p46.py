"""Lot 46 : contrôle automatique après relecture (ingrédients absents du texte, sel, étapes de remplissage)."""

PATCHES = {
    "bread_gong_bao_tofu_3f7cc1": [
        ('txt', "avec 80g d'arachides et la marinade restante", "avec 80g d'arachides et la marinade restante mélangée à 20 g de fécule de maïs"),
        ('step-', 'Pour une présentation plus élégante, saupoudrer'),
    ],
    "brkf_tofu_brouille_aux_herbes_eb117c": [
        ('del', 'tomato_raw_ripe'),
        ('txt', 'accompagné de 120g de tomates cerises et de 240g de tomates fraîches, si désiré.', 'accompagné de 120g de tomates cerises.'),
    ],
    "curry_daubergine_indien_779e72": [
        ('step-', "Goûter le curry et ajuster l'assaisonnement si nécessaire. Vous pouvez ajouter un peu de levure"),
        ('txt', 'garni de coriandre fraîche ou de noix de coco râpée, selon vos préférences. Vous pouvez également servir avec du riz basmati ou des naans pour un repas complet.', 'avec du riz basmati ou des naans.'),
    ],
    "egg_mirza_ghasemi_454e24": [
        ('txt', "Saisissez les aubergines pendant 7 minutes à feu vif, jusqu'à ce qu'elles soient légèrement carbonisées et que leur peau commence à se fendiller, libérant un parfum intense.", "Grillez les aubergines entières sur la flamme ou sous le gril pendant 20 minutes, jusqu'à ce que la peau soit carbonisée et la chair fondante."),
        ('txt', "Faites revenir l'ail pendant 2 minutes à feu moyen", "Faites revenir l'ail dans 45 ml d'huile d'olive pendant 2 minutes à feu moyen"),
    ],
    "egg_sabich_b270c4": [
        ('txt', ", puis les faire nacrer légèrement dans l'huile d'olive, jusqu'à crépitation légère et parfum.", ", puis les faire revenir 5 minutes dans un peu d'huile d'olive."),
        ('txt', 'oignon jaune, avec une présentation visuelle appétissante et une saveur intense.', 'oignon jaune, puis napper de tahini et parsemer de 30 g de persil ciselé.'),
    ],
    "entry_terrine_de_legumes_e52466": [
        ('txt', 'Alternez des couches de légumes en jouant sur les couleurs', 'Alternez des couches de légumes et de feuilles de basilic (20 g) en jouant sur les couleurs'),
    ],
    "main_aligot_c03237": [
        ('step-', "Présenter l'aligot brillant"),
    ],
    "main_arepas_vegan_01b62b": [
        ('txt', 'garnir de tomates fraîches, de fromage végétal râpé', "garnir de tomates fraîches revenues 5 minutes avec 15 g d'ail, 2,5 g de cumin et 2,3 g de paprika, de fromage végétal râpé"),
    ],
    "main_loubia_marocaine_e3b91b": [
        ('txt', '3g de paprika et 3g de cumin en poudre', '3g de paprika, 3g de cumin et 3 g de coriandre en poudre'),
    ],
    "main_soup_k3d2p1": [
        ('dish', 'soup'),
    ],
    "salad_de_poivrons_et_tomates_d5f4ec": [
        ('dish', 'side'),
    ],
}
