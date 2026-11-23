"""Lot 21 : recettes pauvres en FODMAP (16 recettes, 2026-11-23).

Mesure du 2026-11-23 : 74 plats « low FODMAP » sur 985 (compute_fodmap), dont 8 plats
principaux et 2 soupes. Ces recettes suivent les repères Monash appliqués par
rule_engine.diet.compute_fodmap :
  - ni ail, ni oignon, ni échalote, ni poireau, ni champignon, ni blé, ni bouillon en
    poudre (compté comme de l'oignon en poudre) : la ciboulette, le gingembre, les
    herbes et les épices font le goût ;
  - sauce soja ≤ 14 g, miso ≤ 12 g, tahini ≤ 20 g, flocons d'avoine ≤ 52 g, lait de
    coco ~ 100 ml par portion ;
  - lait d'amande, fromages affinés et feta plutôt que lait et yaourt (lactose),
    tofu ferme plutôt que tofu soyeux.
"""
from ._schema import recipe

RECIPES = [
    # ── A. Plats principaux ───────────────────────────────────────────────────────────────
    recipe(
        rid="main_riz_saute_tofu_pak_choi_lowfodmap_1a4c7e",
        fr="Riz sauté au tofu, pak-choï, carottes et cacahuètes",
        en="Fried Rice with Tofu, Bok Choy, Carrots and Peanuts",
        cuisine="chinese", country="china",
        dish="main", servings=4, prep=10, cook=20,
        texture=("grain_separe", "croquant"), taste=("umami", "equilibre"),
        technique=("boiling", "sauteing"), difficulty="easy",
        desc="Un riz sauté sans ail ni oignon, pauvre en FODMAP : tofu ferme doré, carottes, "
             "pak-choï, gingembre et ciboulette, une sauce soja mesurée et des cacahuètes "
             "grillées.",
        compo=[
            ("white_rice_raw_seed_unenriched", 280, "g", "carbohydrate"),
            ("water", 560, "ml", "liquid"),
            ("tofu_plain_pre_packaged", 400, "g", "plant_protein"),
            ("carrot_raw", 200, "g", "vegetable"),
            ("bok_choy_raw", 300, "g", "main_vegetable"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("soy_sauce_shoyu_reduced_sodium", 40, "ml", "umami"),
            ("sesame_oil_plant", 20, "ml", "fat"),
            ("peanut_roasted_salted_dry", 40, "g", "garnish"),
            ("chives_raw_fresh", 15, "g", "herb"),
        ],
        steps=[
            "Cuire 280 g de riz rincé dans 560 ml d'eau, à couvert et à feu doux, 15 minutes, "
            "puis l'étaler pour le laisser refroidir.",
            "Dorer 400 g de tofu en dés 6 minutes dans 10 ml d'huile de sésame à feu vif ; "
            "réserver.",
            "Sauter 200 g de carottes en bâtonnets et 15 g de gingembre râpé 3 minutes dans "
            "10 ml d'huile, puis 300 g de pak-choï émincé 2 minutes.",
            "Ajouter le riz, le tofu et 40 ml de sauce soja, et sauter 3 minutes à feu vif.",
            "Servir parsemé de 40 g de cacahuètes concassées et de 15 g de ciboulette.",
        ],
        allow_similar=("saute", "tofu", "pak", "choi"),
    ),
    recipe(
        rid="main_curry_tofu_coco_courgette_lowfodmap_5e2b90",
        fr="Curry doux de tofu au lait de coco, courgettes et épinards",
        en="Mild Coconut Tofu Curry with Zucchini and Spinach",
        cuisine="indian", country="india",
        dish="main", servings=4, prep=10, cook=25,
        texture=("cremeux", "fondant"), taste=("epice", "doux"),
        technique=("sauteing", "simmering", "boiling"), difficulty="easy", spice=1,
        desc="Un curry sans oignon ni ail, pauvre en FODMAP : le gingembre, le curcuma et le "
             "cumin parfument un lait de coco où mijotent tofu, courgettes et épinards, "
             "servi avec du riz basmati.",
        compo=[
            ("basmati_rice_raw_seed", 280, "g", "carbohydrate"),
            ("water", 560, "ml", "liquid"),
            ("tofu_plain_pre_packaged", 400, "g", "plant_protein"),
            ("green_zucchini_squash_raw", 400, "g", "main_vegetable"),
            ("spinach_raw_baby", 150, "g", "vegetable"),
            ("coconut_milk_plant", 400, "ml", "liquid"),
            ("tomato_crushed_canned", 200, "g", "sauce"),
            ("ginger_raw_root_fresh", 20, "g", "aromatic"),
            ("curry_powder", 6, "g", "spice"),
            ("turmeric_powder", 2, "g", "spice"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("lime_juice_fresh", 15, "ml", "acidity"),
        ],
        steps=[
            "Cuire 280 g de riz basmati rincé dans 560 ml d'eau, à couvert et à feu doux, "
            "15 minutes.",
            "Faire revenir 20 g de gingembre râpé, 6 g de curry, 2 g de curcuma et 3 g de cumin "
            "1 minute dans 20 ml d'huile d'olive.",
            "Ajouter 400 g de courgettes en dés et 400 g de tofu en cubes, puis 400 ml de lait "
            "de coco, 200 g de tomates concassées et 5 g de sel, et mijoter 15 minutes.",
            "Ajouter 150 g de jeunes pousses d'épinard pour 2 minutes et 15 ml de jus de citron "
            "vert, puis servir avec le riz.",
        ],
        allow_similar=("curry", "tofu", "courgettes", "epinards"),
    ),
    recipe(
        rid="main_bowl_quinoa_legumes_rotis_feta_lowfodmap_8c3f14",
        fr="Bowl de quinoa, légumes rôtis, feta et graines de courge",
        en="Quinoa Bowl with Roast Vegetables, Feta and Pumpkin Seeds",
        cuisine="international", country="",
        dish="main", servings=4, prep=15, cook=30,
        texture=("croquant", "fondant"), taste=("acidule", "savoureux"),
        technique=("roasting", "boiling", "assembly"), difficulty="easy",
        desc="Quinoa, carottes, courgettes et poivron rôtis au paprika, feta émiettée, graines "
             "de courge et vinaigrette citronnée : un bol complet et pauvre en FODMAP.",
        compo=[
            ("quinoa_raw_dried", 240, "g", "carbohydrate"),
            ("water", 480, "ml", "liquid"),
            ("carrot_raw", 300, "g", "vegetable"),
            ("green_zucchini_squash_raw", 300, "g", "main_vegetable"),
            ("red_bell_pepper_raw", 200, "g", "vegetable"),
            ("olive_oil_plant", 45, "ml", "fat"),
            ("paprika_powder", 3, "g", "spice"),
            ("feta_cow", 120, "g", "dairy"),
            ("pumpkin_squash_raw_seed", 40, "g", "garnish"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("parsley_fresh_herb", 15, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
        ],
        steps=[
            "Préchauffer le four à 210 °C. Couper 300 g de carottes, 300 g de courgettes et "
            "200 g de poivron en morceaux, les mélanger avec 25 ml d'huile d'olive, 3 g de "
            "paprika et 3 g de sel.",
            "Rôtir les légumes 30 minutes au four à 210 °C.",
            "Cuire 240 g de quinoa rincé dans 480 ml d'eau 15 minutes à couvert, puis le laisser "
            "gonfler 5 minutes hors du feu.",
            "Fouetter 20 ml d'huile, 30 ml de jus de citron et 1 g de sel.",
            "Dresser le quinoa, les légumes, 120 g de feta émiettée, 40 g de graines de courge "
            "et 15 g de persil, et arroser de vinaigrette.",
        ],
        allow_similar=("bowl", "quinoa", "feta"),
    ),
    recipe(
        rid="main_tortilla_pommes_de_terre_ciboulette_lowfodmap_2f8d61",
        fr="Tortilla de pommes de terre à la ciboulette, sans oignon",
        en="Potato Tortilla with Chives (Onion-Free)",
        cuisine="spanish", country="spain",
        dish="main", servings=4, prep=10, cook=30,
        texture=("moelleux", "fondant"), taste=("savoureux", "doux"),
        technique=("sauteing", "pan_frying"), difficulty="medium",
        desc="L'omelette épaisse espagnole, ici sans oignon pour rester pauvre en FODMAP : "
             "pommes de terre confites à l'huile d'olive, œufs et ciboulette, servie avec une "
             "salade verte.",
        compo=[
            ("potato_raw_flesh", 700, "g", "carbohydrate"),
            ("egg_raw", 360, "g", "protein"),
            ("olive_oil_plant", 60, "ml", "fat"),
            ("chives_raw_fresh", 15, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("lettuce_raw", 150, "g", "vegetable"),
        ],
        steps=[
            "Couper 700 g de pommes de terre en fines lamelles et les confire 15 minutes à feu "
            "doux dans 50 ml d'huile d'olive, avec 3 g de sel, sans les colorer.",
            "Battre 6 œufs (360 g) avec 15 g de ciboulette et 1 g de sel, y ajouter les pommes "
            "de terre égouttées.",
            "Verser dans une poêle de 24 cm avec 10 ml d'huile et cuire 8 minutes à feu doux.",
            "Retourner la tortilla à l'aide d'une assiette et cuire encore 4 minutes. Servir "
            "tiède avec 150 g de salade verte.",
        ],
        allow_similar=("tortilla", "pommes", "terre"),
    ),
    recipe(
        rid="main_polenta_legumes_soleil_parmesan_lowfodmap_7b1e35",
        fr="Polenta crémeuse et légumes du soleil au parmesan",
        en="Creamy Polenta with Mediterranean Vegetables and Parmesan",
        cuisine="italian", country="italy",
        dish="main", servings=4, prep=15, cook=35,
        texture=("cremeux", "fondant"), taste=("tomate", "savoureux"),
        technique=("simmering", "sauteing"), difficulty="easy",
        desc="Une polenta onctueuse au parmesan, avec aubergine, poivron et courgette mijotés "
             "à la tomate et au basilic, sans ail ni oignon.",
        compo=[
            ("cornmeal_whole_dried", 200, "g", "carbohydrate"),
            ("water", 900, "ml", "liquid"),
            ("parmesan_grated_dried_cow", 60, "g", "dairy"),
            ("eggplant_raw", 300, "g", "main_vegetable"),
            ("red_bell_pepper_raw", 200, "g", "vegetable"),
            ("green_zucchini_squash_raw", 200, "g", "vegetable"),
            ("tomato_crushed_canned", 400, "g", "sauce"),
            ("basil_fresh_herb", 10, "g", "herb"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("table_salt_unenriched", 6, "g", "seasoning"),
        ],
        steps=[
            "Faire revenir 300 g d'aubergine, 200 g de poivron et 200 g de courgette en dés "
            "8 minutes dans 30 ml d'huile d'olive.",
            "Ajouter 400 g de tomates concassées et 3 g de sel, et mijoter 20 minutes ; finir "
            "avec 10 g de basilic.",
            "Porter 900 ml d'eau à ébullition avec 3 g de sel, verser 200 g de semoule de maïs "
            "en pluie et cuire 10 minutes en remuant.",
            "Incorporer à la polenta 40 g de parmesan et 10 ml d'huile, et servir avec les "
            "légumes et 20 g de parmesan.",
        ],
        allow_similar=("polenta", "parmesan"),
    ),
    recipe(
        rid="main_vermicelles_riz_tofu_oeuf_cacahuetes_lowfodmap_4d6a28",
        fr="Vermicelles de riz sautés au tofu, œuf et cacahuètes",
        en="Stir-Fried Rice Vermicelli with Tofu, Egg and Peanuts",
        cuisine="thai", country="thailand",
        dish="main", servings=4, prep=15, cook=10,
        texture=("al_dente", "croquant"), taste=("acidule", "umami"),
        technique=("boiling", "sauteing"), difficulty="easy",
        desc="Dans l'esprit du pad thaï, sans ail ni échalote : vermicelles de riz, tofu ferme, "
             "œufs brouillés, carottes et concombre, sauce soja, citron vert et sirop d'érable, "
             "cacahuètes et ciboulette.",
        compo=[
            ("rice_vermicelli_raw_dried", 250, "g", "carbohydrate"),
            ("tofu_plain_pre_packaged", 300, "g", "plant_protein"),
            ("egg_raw", 180, "g", "protein"),
            ("carrot_raw", 150, "g", "vegetable"),
            ("cucumber_raw", 150, "g", "vegetable"),
            ("soy_sauce_shoyu_reduced_sodium", 40, "ml", "umami"),
            ("lime_juice_fresh", 30, "ml", "acidity"),
            ("maple_syrup", 15, "ml", "sweetener"),
            ("sesame_oil_plant", 20, "ml", "fat"),
            ("peanut_roasted_salted_dry", 50, "g", "garnish"),
            ("chives_raw_fresh", 15, "g", "herb"),
        ],
        steps=[
            "Plonger 250 g de vermicelles de riz 4 minutes dans l'eau bouillante, les égoutter "
            "et les rincer à l'eau froide.",
            "Dorer 300 g de tofu en dés 5 minutes dans 10 ml d'huile de sésame ; ajouter 3 œufs "
            "(180 g) battus et les brouiller 1 minute.",
            "Ajouter les vermicelles, 150 g de carottes râpées et une sauce de 40 ml de sauce "
            "soja, 30 ml de jus de citron vert et 15 ml de sirop d'érable, et sauter 2 minutes "
            "avec 10 ml d'huile.",
            "Servir avec 150 g de concombre en bâtonnets, 50 g de cacahuètes concassées et 15 g "
            "de ciboulette.",
        ],
        allow_similar=("vermicelles", "riz", "tofu", "cacahuetes"),
    ),
    recipe(
        rid="main_tempeh_grille_pommes_persillees_haricots_lowfodmap_9e0c47",
        fr="Tempeh grillé, pommes de terre persillées et haricots verts",
        en="Grilled Tempeh with Parsley Potatoes and Green Beans",
        cuisine="international", country="",
        dish="main", servings=4, prep=10, cook=25,
        texture=("croustillant", "fondant"), taste=("savoureux", "herbacé"),
        technique=("steaming", "sauteing", "grilling"), difficulty="easy",
        desc="Une assiette simple et pauvre en FODMAP : tempeh mariné au soja et au paprika puis "
             "grillé, pommes de terre vapeur à l'huile d'olive et au persil, haricots verts.",
        compo=[
            ("tempeh_tempe_raw_fermented", 400, "g", "plant_protein"),
            ("soy_sauce_shoyu_reduced_sodium", 30, "ml", "umami"),
            ("paprika_powder", 3, "g", "spice"),
            ("maple_syrup", 10, "ml", "sweetener"),
            ("potato_raw_flesh", 700, "g", "carbohydrate"),
            ("french_bean_raw", 400, "g", "vegetable"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("parsley_fresh_herb", 20, "g", "herb"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ],
        steps=[
            "Couper 400 g de tempeh en tranches et les mariner 10 minutes dans 30 ml de sauce "
            "soja, 3 g de paprika et 10 ml de sirop d'érable.",
            "Cuire 700 g de pommes de terre en morceaux 20 minutes et 400 g de haricots verts "
            "8 minutes à la vapeur.",
            "Griller le tempeh 3 minutes par face dans 20 ml d'huile d'olive.",
            "Mélanger les pommes de terre avec 20 ml d'huile, 20 g de persil haché et 3 g de "
            "sel, et servir avec les haricots verts et le tempeh.",
        ],
        allow_similar=("tempeh", "haricots", "verts"),
    ),
    recipe(
        rid="main_galettes_quinoa_carottes_tahini_lowfodmap_3c5b82",
        fr="Galettes de quinoa aux carottes et à la ciboulette, sauce tahini",
        en="Quinoa and Carrot Patties with Chives and Tahini Sauce",
        cuisine="international", country="",
        dish="main", servings=4, prep=20, cook=25,
        texture=("croustillant", "moelleux"), taste=("terreux", "acidule"),
        technique=("boiling", "pan_frying"), difficulty="medium",
        desc="Des galettes dorées de quinoa, carotte râpée et ciboulette, liées à la farine de "
             "sarrasin, servies avec une sauce tahini au citron et une salade verte.",
        compo=[
            ("quinoa_raw_dried", 200, "g", "carbohydrate"),
            ("water", 400, "ml", "liquid"),
            ("carrot_raw", 250, "g", "vegetable"),
            ("buckwheat_flour", 60, "g", "binder"),
            ("egg_raw", 120, "g", "binder"),
            ("chives_raw_fresh", 15, "g", "herb"),
            ("cumin_spice_seed", 3, "g", "spice"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("sesame_tahini_raw_butter_seed_plant", 60, "g", "sauce"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("lettuce_raw", 150, "g", "vegetable"),
        ],
        steps=[
            "Cuire 200 g de quinoa rincé dans 400 ml d'eau 15 minutes à couvert, puis le "
            "laisser tiédir.",
            "Mélanger le quinoa avec 250 g de carottes râpées, 60 g de farine de sarrasin, "
            "2 œufs (120 g), 15 g de ciboulette, 3 g de cumin et 3 g de sel.",
            "Former 12 galettes et les dorer 4 minutes par face dans 40 ml d'huile d'olive.",
            "Délayer 60 g de tahini avec 30 ml de jus de citron, 1 g de sel et 4 cuillères à "
            "soupe d'eau, et servir avec les galettes et 150 g de salade.",
        ],
        allow_similar=("galettes", "quinoa", "carottes", "tahini"),
    ),
    recipe(
        rid="main_oeufs_brouilles_epinards_cheddar_pdt_lowfodmap_6f2d19",
        fr="Œufs brouillés aux épinards et cheddar, pommes de terre sautées",
        en="Scrambled Eggs with Spinach and Cheddar, Sautéed Potatoes",
        cuisine="international", country="",
        dish="main", servings=4, prep=10, cook=20,
        texture=("cremeux", "croustillant"), taste=("savoureux", "lacté"),
        technique=("sauteing",), difficulty="easy",
        desc="Des œufs brouillés crémeux aux épinards et au cheddar (un fromage affiné, presque "
             "sans lactose), avec des pommes de terre sautées à la ciboulette.",
        compo=[
            ("potato_raw_flesh", 600, "g", "carbohydrate"),
            ("olive_oil_plant", 30, "ml", "fat"),
            ("egg_raw", 480, "g", "protein"),
            ("spinach_raw_baby", 150, "g", "vegetable"),
            ("cheddar_cow", 80, "g", "dairy"),
            ("chives_raw_fresh", 10, "g", "herb"),
            ("table_salt_unenriched", 4, "g", "seasoning"),
            ("black_pepper_spice", 1, "g", "spice"),
        ],
        steps=[
            "Faire sauter 600 g de pommes de terre en dés 15 minutes dans 25 ml d'huile d'olive, "
            "avec 3 g de sel, jusqu'à ce qu'elles soient dorées.",
            "Faire tomber 150 g de jeunes pousses d'épinard 1 minute dans 5 ml d'huile.",
            "Ajouter 8 œufs (480 g) battus avec 1 g de sel et 1 g de poivre, et les cuire à feu "
            "doux en remuant sans cesse 4 minutes.",
            "Hors du feu, incorporer 80 g de cheddar râpé, et servir avec les pommes de terre et "
            "10 g de ciboulette.",
        ],
        allow_similar=("oeufs", "brouilles", "epinards"),
    ),
    recipe(
        rid="salad_riz_concombre_tomate_feta_lowfodmap_0b7e53",
        fr="Salade de riz, concombre, tomate, feta et basilic",
        en="Rice Salad with Cucumber, Tomato, Feta and Basil",
        cuisine="greek", country="greece",
        dish="main", servings=4, prep=15, cook=15,
        texture=("frais", "croquant"), taste=("frais", "acidule"),
        technique=("boiling", "assembly"), difficulty="easy",
        desc="Une salade complète pauvre en FODMAP : riz, concombre, tomates, poivron, feta, "
             "olives et basilic, vinaigrette au citron et à l'huile d'olive.",
        compo=[
            ("white_rice_raw_seed_unenriched", 240, "g", "carbohydrate"),
            ("water", 480, "ml", "liquid"),
            ("cucumber_raw", 250, "g", "vegetable"),
            ("tomato_raw_ripe", 300, "g", "vegetable"),
            ("red_bell_pepper_raw", 150, "g", "vegetable"),
            ("feta_cow", 150, "g", "dairy"),
            ("black_olive_canned_in_brine", 60, "g", "garnish"),
            ("basil_fresh_herb", 15, "g", "herb"),
            ("olive_oil_plant", 40, "ml", "fat"),
            ("lemon_juice", 30, "ml", "acidity"),
            ("table_salt_unenriched", 3, "g", "seasoning"),
        ],
        steps=[
            "Cuire 240 g de riz rincé dans 480 ml d'eau 15 minutes à couvert, puis l'étaler pour "
            "le refroidir.",
            "Couper 250 g de concombre, 300 g de tomates et 150 g de poivron en dés.",
            "Fouetter 40 ml d'huile d'olive, 30 ml de jus de citron et 3 g de sel.",
            "Mélanger le riz, les légumes, 60 g d'olives et la vinaigrette, puis ajouter 150 g "
            "de feta en dés et 15 g de basilic ciselé.",
        ],
        allow_similar=("salade", "riz", "feta"),
    ),

    # ── B. Soupes ─────────────────────────────────────────────────────────────────────────
    recipe(
        rid="soup_miso_vermicelles_tofu_pak_choi_lowfodmap_8d4a90",
        fr="Soupe miso aux vermicelles de riz, tofu et pak-choï",
        en="Miso Soup with Rice Vermicelli, Tofu and Bok Choy",
        cuisine="japanese", country="japan",
        dish="soup", servings=4, prep=10, cook=10,
        texture=("bouillon_riche", "fondant"), taste=("umami", "equilibre"),
        technique=("simmering", "boiling"), difficulty="easy",
        desc="Un bouillon au gingembre et au miso dosé pour rester pauvre en FODMAP, avec "
             "vermicelles de riz, tofu ferme, pak-choï et ciboulette.",
        compo=[
            ("water", 1500, "ml", "liquid"),
            ("ginger_raw_root_fresh", 15, "g", "aromatic"),
            ("miso_fermented", 40, "g", "umami"),
            ("soy_sauce_shoyu_reduced_sodium", 15, "ml", "seasoning"),
            ("rice_vermicelli_raw_dried", 150, "g", "carbohydrate"),
            ("tofu_plain_pre_packaged", 300, "g", "plant_protein"),
            ("bok_choy_raw", 300, "g", "vegetable"),
            ("chives_raw_fresh", 10, "g", "garnish"),
        ],
        steps=[
            "Porter 1,5 l d'eau à frémissement avec 15 g de gingembre en lamelles et laisser "
            "infuser 5 minutes.",
            "Ajouter 300 g de pak-choï émincé, 300 g de tofu en dés et 150 g de vermicelles de "
            "riz, et cuire 4 minutes.",
            "Hors du feu, délayer 40 g de miso dans une louche de bouillon et le reverser avec "
            "15 ml de sauce soja.",
            "Servir parsemé de 10 g de ciboulette.",
        ],
        allow_similar=("miso", "vermicelles", "pak", "choi"),
    ),
    recipe(
        rid="soup_veloute_carottes_gingembre_coco_lowfodmap_2e6f71",
        fr="Velouté de carottes au gingembre et au lait de coco",
        en="Carrot, Ginger and Coconut Milk Soup",
        cuisine="international", country="",
        dish="soup", servings=4, prep=10, cook=25,
        texture=("velouté", "lisse"), taste=("doux", "epice"),
        technique=("sauteing", "simmering", "blending"), difficulty="easy",
        desc="Un velouté sans bouillon cube ni oignon, pauvre en FODMAP : carottes et pomme de "
             "terre cuites au gingembre et au cumin, mixées avec du lait de coco.",
        compo=[
            ("carrot_raw", 700, "g", "main_vegetable"),
            ("potato_raw_flesh", 200, "g", "vegetable"),
            ("ginger_raw_root_fresh", 20, "g", "aromatic"),
            ("cumin_spice_seed", 2, "g", "spice"),
            ("olive_oil_plant", 15, "ml", "fat"),
            ("water", 900, "ml", "liquid"),
            ("coconut_milk_plant", 200, "ml", "liquid"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("chives_raw_fresh", 10, "g", "garnish"),
        ],
        steps=[
            "Faire revenir 20 g de gingembre râpé et 2 g de cumin 1 minute dans 15 ml d'huile "
            "d'olive.",
            "Ajouter 700 g de carottes et 200 g de pomme de terre en rondelles, 900 ml d'eau et "
            "5 g de sel, et cuire 20 minutes à couvert.",
            "Mixer finement avec 200 ml de lait de coco.",
            "Servir parsemé de 10 g de ciboulette.",
        ],
        allow_similar=("veloute", "carottes", "gingembre", "coco"),
    ),
    recipe(
        rid="soup_courgettes_pommes_de_terre_basilic_lowfodmap_5a9c03",
        fr="Soupe de courgettes, pommes de terre et basilic",
        en="Zucchini, Potato and Basil Soup",
        cuisine="italian", country="italy",
        dish="soup", servings=4, prep=10, cook=20,
        texture=("velouté", "lisse"), taste=("herbacé", "doux"),
        technique=("simmering", "blending"), difficulty="easy",
        desc="Une soupe verte et douce, sans ail ni oignon : courgettes et pommes de terre "
             "mixées avec du basilic et un filet d'huile d'olive, servie avec du parmesan.",
        compo=[
            ("green_zucchini_squash_raw", 700, "g", "main_vegetable"),
            ("potato_raw_flesh", 250, "g", "vegetable"),
            ("water", 800, "ml", "liquid"),
            ("basil_fresh_herb", 15, "g", "herb"),
            ("olive_oil_plant", 20, "ml", "fat"),
            ("table_salt_unenriched", 5, "g", "seasoning"),
            ("parmesan_grated_dried_cow", 30, "g", "dairy"),
        ],
        steps=[
            "Cuire 700 g de courgettes et 250 g de pommes de terre en morceaux 18 minutes dans "
            "800 ml d'eau avec 5 g de sel.",
            "Mixer avec 15 g de basilic et 20 ml d'huile d'olive.",
            "Servir avec 30 g de parmesan râpé.",
        ],
        allow_similar=("soupe", "courgettes", "basilic"),
    ),

    # ── C. Petit-déjeuner ─────────────────────────────────────────────────────────────────
    recipe(
        rid="brkf_porridge_amande_fraises_graines_lowfodmap_7c1d58",
        fr="Porridge au lait d'amande, fraises et graines de courge",
        en="Almond Milk Porridge with Strawberries and Pumpkin Seeds",
        cuisine="international", country="",
        dish="breakfast", servings=4, prep=5, cook=8,
        texture=("cremeux", "croquant"), taste=("doux", "fruité"),
        technique=("simmering",), difficulty="easy",
        desc="Un porridge pauvre en FODMAP : 50 g de flocons d'avoine par bol, cuits dans le "
             "lait d'amande, avec des fraises, des graines de courge et un filet de sirop "
             "d'érable.",
        compo=[
            ("oat_flakes_whole_seed", 200, "g", "carbohydrate"),
            ("almond_milk_refrigerated_unsweetened_plant", 800, "ml", "liquid"),
            ("strawberry_raw", 300, "g", "fruit"),
            ("pumpkin_squash_raw_seed", 40, "g", "garnish"),
            ("maple_syrup", 30, "ml", "sweetener"),
            ("cinnamon_powder", 2, "g", "spice"),
        ],
        steps=[
            "Porter 800 ml de lait d'amande à frémissement avec 2 g de cannelle, ajouter 200 g "
            "de flocons d'avoine et cuire 5 minutes à feu doux en remuant.",
            "Répartir dans les bols et garnir de 300 g de fraises en morceaux et de 40 g de "
            "graines de courge.",
            "Arroser de 30 ml de sirop d'érable.",
        ],
        allow_similar=("porridge", "fraises"),
    ),

    # ── D. Desserts ───────────────────────────────────────────────────────────────────────
    recipe(
        rid="dess_riz_coco_ananas_roti_lowfodmap_4b8e26",
        fr="Riz au lait de coco et ananas rôti",
        en="Coconut Rice Pudding with Roast Pineapple",
        cuisine="thai", country="thailand",
        dish="dessert", servings=4, prep=10, cook=35,
        texture=("cremeux", "fondant"), taste=("doux", "fruité"),
        technique=("simmering", "caramelizing"), difficulty="easy",
        desc="Un riz au lait vegan et pauvre en FODMAP : riz rond cuit dans le lait de coco à la "
             "vanille et au sirop d'érable, avec de l'ananas doré à la poêle.",
        compo=[
            ("white_rice_short_grain_seed_dried", 150, "g", "carbohydrate"),
            ("coconut_milk_plant", 400, "ml", "liquid"),
            ("water", 400, "ml", "liquid"),
            ("maple_syrup", 50, "ml", "sweetener"),
            ("vanilla_extract", 5, "ml", "flavor"),
            ("pineapple_raw", 400, "g", "fruit"),
            ("lime_juice_fresh", 10, "ml", "acidity"),
        ],
        steps=[
            "Cuire 150 g de riz rond dans 400 ml de lait de coco et 400 ml d'eau à feu doux "
            "30 minutes, en remuant souvent, jusqu'à ce qu'il soit crémeux.",
            "Hors du feu, ajouter 40 ml de sirop d'érable et 5 ml d'extrait de vanille.",
            "Dorer 400 g d'ananas en morceaux 5 minutes à la poêle avec 10 ml de sirop d'érable "
            "et 10 ml de jus de citron vert.",
            "Servir le riz tiède ou froid avec l'ananas.",
        ],
        allow_similar=("riz", "coco", "ananas"),
    ),
    recipe(
        rid="dess_salade_ananas_kiwi_fraises_menthe_lowfodmap_9f3a12",
        fr="Salade d'ananas, kiwi et fraises à la menthe",
        en="Pineapple, Kiwi and Strawberry Salad with Mint",
        cuisine="international", country="",
        dish="dessert", servings=4, prep=15, cook=0,
        texture=("frais", "juteux"), taste=("acidule", "frais"),
        technique=("assembly",), difficulty="easy",
        desc="Trois fruits pauvres en FODMAP, ananas, kiwi et fraises, avec de la menthe et un "
             "trait de citron vert : le dessert frais et léger.",
        compo=[
            ("pineapple_raw", 400, "g", "fruit"),
            ("kiwi_raw", 240, "g", "fruit"),
            ("strawberry_raw", 300, "g", "fruit"),
            ("lime_juice_fresh", 15, "ml", "acidity"),
            ("mint_fresh_herb", 5, "g", "herb"),
            ("maple_syrup", 10, "ml", "sweetener"),
        ],
        steps=[
            "Couper 400 g d'ananas, 240 g de kiwis pelés et 300 g de fraises en morceaux.",
            "Mélanger avec 15 ml de jus de citron vert et 10 ml de sirop d'érable.",
            "Parsemer de 5 g de menthe ciselée et servir frais.",
        ],
        allow_similar=("salade", "ananas", "kiwi", "fraises"),
    ),
]
