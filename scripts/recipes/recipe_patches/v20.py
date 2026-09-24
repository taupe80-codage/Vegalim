"""Variantes 20 : famille des soupes de lentilles du Levant et paire houmous.

Cinq soupes de lentilles quasi identiques (arménienne, libanaise, persane, irakienne, et celle
renommée en v15 qui portait le même nom que l'irakienne) : chacune reçoit son nom régional et
l'ingrédient qui la caractérise. Les deux houmous se distinguent par le mode de cuisson des
pois chiches (secs trempés / conserve).
"""

VARIANTS = {
    # Liban : adas bi hamod, la version aux blettes et très citronnée
    "dal_lebanese_lentil_soup_eae561": [
        ("title", "Adas bi hamod, soupe libanaise de lentilles aux blettes et au citron"),
        ("desc", "Soupe libanaise de lentilles vertes aux côtes de blettes, très citronnée : les lentilles "
                 "restent entières dans un bouillon clair parfumé à la coriandre et à l'ail, et le jus de "
                 "citron ajouté hors du feu domine en bouche."),
        ("add", "swiss_chard_raw", 300, "g", "vegetable"),
        ("qty", "lemon_juice", 60),
        ("del", "tomato_raw_ripe"),
        ("add", "coriander", 15, "g", "herb"),
        ("qty", "olive_oil_plant", 45),
        ("steps", [
            "Rincer 300 g de lentilles vertes, les couvrir de 750 ml de bouillon de légumes et cuire "
            "20 minutes à petits bouillons : elles doivent rester entières.",
            "Émincer 150 g d'oignon et couper 200 g de carotte en rondelles, les faire revenir 6 minutes "
            "dans 45 ml d'huile d'olive avec 3 g de cumin, jusqu'à ce que l'oignon soit blond.",
            "Laver 300 g de blettes, séparer les côtes des feuilles : couper les côtes en tronçons de 2 cm "
            "et ciseler les feuilles.",
            "Verser l'oignon, la carotte et les côtes de blettes dans les lentilles, poursuivre la cuisson "
            "15 minutes à feu doux.",
            "Écraser l'ail avec 2 g de sel et 15 g de coriandre hachée, ajouter cette pâte et les feuilles "
            "de blettes, cuire 3 minutes de plus.",
            "Hors du feu, verser 60 ml de jus de citron, goûter : la soupe doit être franchement acide. "
            "Servir chaud avec un quartier de citron.",
        ]),
    ],
    # Arménie : vospov apur, adoucie aux abricots secs
    "dal_armenian_lentil_soup_0f1067": [
        ("title", "Vospov apur, soupe arménienne de lentilles aux abricots secs"),
        ("desc", "Soupe arménienne de lentilles vertes mixée, adoucie par des abricots secs fondus à la "
                 "cuisson : une texture épaisse et velourée, un équilibre sucré-acidulé relevé de paprika "
                 "et d'un filet de citron."),
        ("add", "apricot_pitted_dried", 80, "g", "fruit"),
        ("qty", "tomato_raw_ripe", 200),
        ("steps", [
            "Faire revenir 150 g d'oignon émincé et 9 g d'ail haché dans 45 ml d'huile de tournesol, "
            "3 minutes à feu moyen, jusqu'à ce qu'ils soient translucides.",
            "Ajouter 200 g de carotte en dés et 200 g de tomates concassées, cuire 5 minutes en remuant.",
            "Incorporer 200 g de lentilles vertes rincées, 80 g d'abricots secs coupés en quatre, 3 g de "
            "cumin et 3 g de paprika, puis couvrir de 750 ml de bouillon de légumes chaud.",
            "Porter à ébullition, baisser le feu et laisser mijoter 30 minutes : les abricots doivent se "
            "défaire complètement et épaissir la soupe.",
            "Mixer aux trois quarts pour garder quelques lentilles entières, puis ajouter 40 ml de jus de "
            "citron, 2 g de sel et 2 g de poivre.",
            "Servir chaud avec un peu de paprika saupoudré et du persil frais.",
        ]),
    ],
    # Iran : adasi, au curcuma et aux dattes, servie aussi au petit-déjeuner
    "dal_persian_lentil_soup_71e221": [
        ("title", "Adasi, soupe persane de lentilles au curcuma et aux dattes"),
        ("desc", "Adasi iranienne : lentilles fondues au curcuma et à la cannelle, enrichies de dattes "
                 "dénoyautées qui se défont dans le bouillon et d'une noix de beurre, une soupe épaisse "
                 "que l'on mange aussi au petit-déjeuner avec du pain."),
        ("add", "date_with_skin_dried", 80, "g", "fruit"),
        ("del", "tomato_raw_ripe"),
        ("steps", [
            "Faire revenir 150 g d'oignon émincé dans 45 ml d'huile d'olive vierge extra, 5 minutes à feu "
            "moyen, jusqu'à ce qu'il soit doré.",
            "Ajouter 9 g d'ail haché, 3 g de curcuma, 3 g de cumin et 3 g de cannelle, remuer 1 minute "
            "pour réveiller les épices.",
            "Verser 300 g de lentilles vertes rincées et 200 g de carotte en petits dés, enrober 2 minutes.",
            "Couvrir de 750 ml de bouillon de légumes, porter à ébullition puis laisser mijoter 25 minutes "
            "à couvert.",
            "Ajouter 80 g de dattes dénoyautées coupées en morceaux et poursuivre 10 minutes : elles "
            "fondent et sucrent légèrement le bouillon.",
            "Écraser grossièrement à la cuillère pour épaissir, assaisonner de 2 g de sel et 2 g de poivre, "
            "puis incorporer 30 g de beurre hors du feu.",
            "Ajouter 30 ml de jus de citron, servir très chaud avec du pain plat et de la coriandre.",
        ]),
    ],
    # Irak : titre explicite, c'est la version aux lentilles corail et au tadka de paprika
    "dal_shorbat_adas_d4f98a": [
        ("title", "Shorbat adas irakienne, soupe de lentilles corail au curcuma"),
        ("desc", "Soupe irakienne de lentilles corail mixée jusqu'à être velourée, colorée au curcuma et "
                 "finie par un tadka d'huile au paprika versé brûlant sur l'assiette."),
    ],
    # deux houmous : celui-ci part de pois chiches en conserve
    "dal_hummus_traditionnel_7f6ccc": [
        ("title", "Houmous express aux pois chiches en conserve"),
        ("desc", "Houmous prêt en dix minutes : des pois chiches en conserve rincés, mixés avec tahin, "
                 "citron et ail, allongés d'eau glacée ; moins aérien qu'avec des pois chiches secs, mais "
                 "parfumé au cumin et servi aussitôt."),
        ("time", 10, 0, 0),
        ("steps", [
            "Égoutter et rincer 400 g de pois chiches en conserve, retirer les peaux qui se détachent "
            "pour un résultat plus lisse.",
            "Mixer les pois chiches 3 minutes avec 45 ml de tahin, 40 ml de jus de citron et 9 g d'ail.",
            "Ajouter 60 ml d'eau glacée en filet, moteur en marche, jusqu'à obtenir une crème souple.",
            "Saler avec 5 g de sel, ajouter 3 g de cumin et mixer encore 1 minute.",
            "Étaler dans une assiette creuse, creuser un sillon à la cuillère et arroser de 45 ml "
            "d'huile d'olive.",
            "Garnir de 5 g de persil haché et de quelques pois chiches entiers, servir tout de suite.",
        ]),
    ],
}
