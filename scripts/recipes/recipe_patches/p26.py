"""Lot 26 : riz sautés au kimchi, mexican rice, mujadara, nasi goreng, onigiri."""

PATCHES = {
    "rice_kimchi_bokkeumbap_2cbfe6": [
        ("qty", "canola", 15),
        ("txt", "Faire chauffer 10 ml d'huile de sésame à feu moyen dans une poêle.", "Faire chauffer 15 ml d'huile de colza à feu moyen dans une poêle."),
        ("txt", "Casser 2 œufs dans un bol", "Casser les œufs (220 g) dans un bol"),
        ("txt", "Ajouter 45 ml d'huile de colza et mélanger pour bien enrober le plat. Servir sans attendre",
         "Rectifier l'assaisonnement et servir sans attendre"),
    ],
    "rice_kimchi_fried_rice_1f3e90": [
        ("qty", "sweet_onion_raw", 150),
        ("qty", "vegetable_oil_plant", 30),
        ("txt", "Dans une poêle, ajouter 15ml d'huile de sésame", "Dans une poêle, ajouter 30 ml d'huile végétale et 15ml d'huile de sésame"),
        ("txt", "Incorporer 300g de riz blanc cru non enrichi froid", "Incorporer 300g de riz cuit froid"),
        ("txt", ", et 5ml de gochujang", ""),
        ("txt", "Incorporer les oignons doux crus ciselés de 300g", "Incorporer 150 g d'oignon doux ciselé"),
        ("step-", "Ajouter les épices et herbes de votre choix"),
        ("step-", "Servir dans des bols préchauffés"),
    ],
    "rice_mexican_rice_94bd67": [
        ("qty", "shallot_raw", 100),
        ("qty", "table_salt_unenriched", 2),
    ],
    "rice_mujadara_classic_ee2456": [
        ("add", "water", 960, "ml", "liquid"),
    ],
    "rice_nasi_goreng_edfce4": [
        ("qty", "coconut_oil_plant", 40),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Servir aussitôt dans des bols préchauffés, garni de coriandre ciselée et d'un filet d'huile de coco. Accompagner de pain pita tiède.",
         "Servir aussitôt, garni de coriandre ciselée."),
    ],
    "rice_nasi_goreng_vegan_bcc9cb": [
        ("qty", "soy_sauce_shoyu_reduced_sodium", 20),
        ("qty", "base_fried_onion_217e6a", 20),
        ("qty", "table_salt_unenriched", 2),
        ("txt", "Assaisonner avec 5 g de sel et du poivre noir", "Assaisonner avec 2 g de sel et du poivre noir"),
    ],
    "rice_onigiri_nature_cd56ab": [
        ("serv", 4),
        ("del", "vinegar_liquid"),
        ("del", "white_sugar"),
        ("qty", "table_salt_unenriched", 3),
        ("txt", "Assaisonner avec 30ml de vinaigre de riz, 5g de sel et 15g de sucre blanc, puis laisser refroidir complètement.",
         "Saler légèrement (3 g) et laisser refroidir complètement."),
        ("step-", "Enfourner les triangles de riz à 180°C pendant 5 minutes"),
    ],
    "rice_onigiri_umeboshi_7a5ef3": [
        ("qty", "table_salt_unenriched", 3),
        ("txt", "puis laisser reposer 10 minutes à 60°C", "puis laisser reposer 10 minutes à couvert"),
        ("txt", "creuser un sillon au centre en utilisant la lame d'un couteau", "creuser un sillon au centre avec le pouce"),
        ("txt", ", en vérifiant que le nori crépite légèrement lors de la cuisson, puis servir aussitôt sur une assiette, en vérifiant la texture croustillante du nori.",
         ", puis servir aussitôt."),
    ],
}
