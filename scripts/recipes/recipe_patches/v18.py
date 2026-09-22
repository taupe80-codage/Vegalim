"""Variantes 18 : suite des plats trop légers — reclassements demandés."""

VARIANTS = {
    # préparation de base (sert d'ingrédient), pas un plat
    "base_seitan_249032": [
        ("dish", "base"),
        ("title", "Seitan maison à la vapeur"),
        ("desc", "Préparation de base vegan très riche en protéines : gluten de blé pétri avec sauce soja, ail et "
                 "gingembre, roulé puis cuit à la vapeur, à trancher pour les sautés et les mijotés."),
    ],
    # galette de teff : base de pain éthiopien, support des plats
    "crepe_galette_de_teff_a1a8d3": [
        ("dish", "base"),
        ("desc", "Galette éthiopienne à la farine de teff : une pâte très liquide laissée fermenter deux jours, "
                 "versée en spirale sur une plaque brûlante et cuite d'un seul côté, souple et alvéolée ; "
                 "elle sert d'assiette et de couvert pour les plats en sauce."),
    ],
    # tapa, pas un plat
    "bread_pan_con_tomate_06a94e": [("dish", "snack"), ("origin", {"cuisine": "spanish"})],
    # préparations de légumes servies en accompagnement
    "main_caponata_d15a4f": [("dish", "side")],
    "main_pisto_espagnol_7a98be": [("dish", "side")],
    "main_bohemienne_provencale_781b61": [("dish", "side")],
    "main_aubergines_sichuan_ff9921": [("dish", "side")],
}
