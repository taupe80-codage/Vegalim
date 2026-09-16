"""Lot 20 : spätzle, tartes salées, tempura, tian."""

PATCHES = {
    # la pâte à spätzle était refaite alors que la base est déjà comptée
    "main_spatzle_au_fromage_586859": [
        ("ing", "parmesan_grated_dried_cow", "gruyere", 120),
        ("del", "egg_raw"),
        ("step-", "Préparer la pâte en fouettant 55 grammes d'œuf"),
        ("step-", "Porter 3 litres d'eau salée à forte ébullition"),
        ("step-", "Cuire pendant 2 à 3 minutes, ou jusqu'à ce que les spätzle remontent en surface"),
        ("step-", "Mélanger délicatement pour éviter la formation de grumeaux."),
        ("step-", "Servir dans des bols préchauffés"),
        ("txt", "Incorporer 150 grammes de fromage parmesan hors du feu", "Incorporer 120 grammes de gruyère râpé hors du feu"),
    ],
    "main_tarte_a_la_tomate_a1d175": [
        ("qty", "olive_oil_plant", 20),
        ("add", "table_salt_unenriched", 3, "g", "seasoning"),
        ("txt", "et 2 ml d'huile d'olive sur les tomates", "et 20 ml d'huile d'olive sur les tomates"),
        ("txt", "Enfournez la tarte à 190°C pendant 25 minutes", "Enfournez la tarte à 180°C pendant 25 minutes"),
    ],
    "main_tarte_oignon_alsacienne_c49dd2": [
        ("add", "table_salt_unenriched", 4, "g", "seasoning"),
    ],
    "main_tarte_roquefort_et_noix_b24bec": [
        ("serv", 6),
        ("txt", "Vérifiez la cuisson en insérant une lame de couteau dans la tarte.", "Vérifiez que l'appareil est pris."),
        ("step-", "Si la lame ressort sèche, la tarte est prête."),
    ],
    "main_tempura_de_legumes_20cc9f": [
        ("qty", "water", 200),
        ("qty", "sunflower_oil_plant", 80),
        ("txt", "avec 500 ml d'eau très froide", "avec 200 ml d'eau très froide"),
        ("txt", "Servir chaud, garni d'un peu de daikon râpé et accompagné d'une sauce légère, dans des bols préchauffés.",
         "Servir chaud, garni d'un peu de daikon râpé et accompagné d'une sauce légère."),
        ("step-", "Présenter les tempuras de manière attrayante"),
    ],
    "main_tian_provencal_4c7999": [
        ("time", 13, 0, 50),
    ],
}
