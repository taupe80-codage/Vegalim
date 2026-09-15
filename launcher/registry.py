"""Catalogue des actions pilotables depuis le panneau de controle ALIM.

Chaque Action decrit un script "sur (relisible sans risque de corrompre les
donnees) et la maniere de le lancer. Les scripts historiques ponctuels de
correction (fusions, splits, renommages one-shot deja appliques) ne sont
volontairement PAS ici : ils restent accessibles seulement en ligne de
commande pour eviter un double-declenchement accidentel.
"""
from __future__ import annotations

import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Action:
    key: str
    category: str
    title: str
    description: str
    kind: str  # "capture" (sortie affichee dans le journal) | "console" (fenetre dediee)
    steps: tuple = ()       # pour kind == "capture" : liste d'etapes, chaque etape = tuple de tokens
    bat: str = ""           # pour kind == "console" : chemin du .bat relatif a la racine du projet
    dry_run: bool = False   # ajoute une case a cocher "--dry-run" (ajoutee a la 1ere etape)


ACTIONS: tuple[Action, ...] = (
    # ── Recettes ────────────────────────────────────────────────────────────
    Action(
        key="recipe_list_refresh",
        category="Recettes",
        title="Rafraichir la liste des recettes",
        description=(
            "Relit backend/data/recipes/recipes.json et regenere recipe_list.json "
            "et recipe_list.md (liste triee alphabetiquement : titre, cuisine, type "
            "de plat, vegan/non-vegan), puis reconstruit recipe_list_artifact.html, "
            "la version interactive avec recherche, filtre vegan et selection pour "
            "suppression ou regroupement. A relancer apres tout ajout, suppression "
            "ou renommage de recette."
        ),
        kind="capture",
        steps=(
            ("{python}", "backend/data/recipes/_scripts/extract_recipe_list.py"),
            ("{python}", "backend/data/recipes/_scripts/build_recipe_list_artifact.py"),
        ),
    ),
    Action(
        key="audit_base_recipes",
        category="Recettes",
        title="Audit des recettes de base (base_*)",
        description=(
            "Verifie l'integrite de toutes les recettes dont l'id commence par "
            "base_ : champs obligatoires (titres, composition, portions, type de "
            "plat), coherence des quantites/unites/ingredients resolus, usage "
            "effectif de chaque base par les recettes qui la referencent, et "
            "incoherences dietetiques (base non-vegan utilisee dans une recette "
            "taguee vegan). Lecture seule, n'ecrit rien."
        ),
        kind="capture",
        steps=(("{python}", "scripts/audit_base_recipes.py"),),
    ),

    # ── Ingredients ─────────────────────────────────────────────────────────
    Action(
        key="ing_audit_axes_usage",
        category="Ingredients",
        title="Audit usage des axes",
        description=(
            "Parcourt tous les ingredient_groups de ingredients_tree.json et "
            "compte, pour chaque axe de classification (etat de cuisson, forme, "
            "traitement...) et chaque valeur du vocabulaire, combien d'ingredients "
            "l'utilisent reellement. Signale les axes ou valeurs jamais utilises. "
            "Lecture seule."
        ),
        kind="capture",
        steps=(("{python}", "backend/data/ingredients/_scripts/audit_axes_usage.py"),),
    ),
    Action(
        key="ing_audit_encoding",
        category="Ingredients",
        title="Audit encodage complet",
        description=(
            "Scanne toutes les chaines de texte du referentiel d'ingredients a la "
            "recherche de caracteres non-ASCII et classe chaque occurrence par "
            "type de probleme potentiel (accent correct, mojibake probable, "
            "caractere suspect). Utile pour detecter une regression d'encodage "
            "apres un import. Lecture seule."
        ),
        kind="capture",
        steps=(("{python}", "backend/data/ingredients/_scripts/audit_encoding_full.py"),),
    ),
    Action(
        key="ing_list_categories",
        category="Ingredients",
        title="Lister les categories",
        description=(
            "Affiche le catalogue complet des categories et sous-categories "
            "d'ingredients (cat1/cat2) avec leurs libelles francais et le nombre "
            "d'ingredients dans chacune. Pratique pour retrouver l'identifiant "
            "exact d'une categorie avant une operation manuelle. Lecture seule."
        ),
        kind="capture",
        steps=(("{python}", "backend/data/ingredients/_scripts/list_categories.py"),),
    ),
    Action(
        key="ing_verify_split",
        category="Ingredients",
        title="Verifier les splits historiques",
        description=(
            "Compare l'etat actuel des ingredients touches par les scissions "
            "historiques (figues sechees, jus d'orange, pommes, pommes de terre, "
            "haricots, lait, oeufs...) a une liste de valeurs attendues (axes, "
            "nombre de variantes) pour confirmer qu'aucune regression n'a ete "
            "introduite depuis ces corrections. Lecture seule, n'ecrit rien."
        ),
        kind="capture",
        steps=(("{python}", "backend/data/ingredients/_scripts/verify_split.py"),),
    ),

    # ── Index & Prix ────────────────────────────────────────────────────────
    Action(
        key="build_index",
        category="Index & Prix",
        title="Construire l'index de recherche",
        description=(
            "Reconstruit entierement backend/data/indexes/search_index.json a "
            "partir de recipes.json : indexe titres, composition, tags (regime, "
            "allergenes, technique) et origine culinaire en tokens de recherche "
            "normalises (sans accents, minuscules, mots vides filtres). "
            "Regeneration complete et deterministe, sans danger a relancer."
        ),
        kind="capture",
        steps=(("{python}", "scripts/build_index.py"),),
        dry_run=True,
    ),
    Action(
        key="update_prices",
        category="Index & Prix",
        title="Mettre a jour les prix (Open Food Facts)",
        description=(
            "Interroge l'API publique Open Food Facts Open Prices pour chaque "
            "ingredient du catalogue de prix, calcule la mediane des prix "
            "trouves, et met a jour le prix catalogue si l'ecart depasse 10 %. "
            "Necessite une connexion internet ; ~0,4 s de delai entre requetes "
            "pour respecter la limite de l'API (peut prendre plusieurs minutes "
            "sur tout le catalogue)."
        ),
        kind="capture",
        steps=(("{python}", "scripts/update_prices.py"),),
        dry_run=True,
    ),
    Action(
        key="generate_alias_proposals",
        category="Index & Prix",
        title="Generer les propositions d'alias",
        description=(
            "Compare les termes non resolus listes dans AUDIT_KG_UNMATCHED.md aux "
            "group_id et noms canoniques du dictionnaire d'ingredients v2 par "
            "correspondance floue, et propose pour chacun un alias avec un score "
            "de confiance (AUTO_HIGH / AUTO_MED / AUTO_LOW / SKIP / NO_ALIAS). "
            "Ecrit uniquement scripts/alias_proposals.yaml, un brouillon a relire "
            "et valider manuellement -- ne touche pas au dictionnaire."
        ),
        kind="capture",
        steps=(("{python}", "scripts/generate_alias_proposals.py"),),
    ),

    # ── Pipeline complet ────────────────────────────────────────────────────
    Action(
        key="run_pipeline_bat",
        category="Pipeline complet",
        title="Rebuild complet des donnees (CIQUAL / USDA / CNF -> recettes)",
        description=(
            "Ouvre dans une console dediee le rebuild valide (meme sequence que "
            "le README) : nutrition_v2 depuis CIQUAL/USDA Foundation + SR Legacy/"
            "CNF, dictionnaire, index nutrition, regimes/allergenes et registre "
            "des sous-recettes (jusqu'a stabilisation), graphes nutrition et "
            "scoring, index de recherche, puis controles en lecture seule "
            "(portions, coherence, tests d'integrite). S'arrete a la premiere "
            "erreur. Plusieurs minutes ; verifier git diff avant de commiter."
        ),
        kind="console",
        bat="run_pipeline.bat",
    ),
    Action(
        key="run_recipe_pipeline_bat",
        category="Pipeline complet",
        title="Pipeline recettes (collecte / parsing / synthese)",
        description=(
            "Ouvre le pipeline de reconstitution des recettes dans une fenetre de "
            "console dediee avec un menu a 6 choix : pipeline complet, pipeline + "
            "reecriture LLM (Groq), validation d'un CDC existant, post-correction "
            "des flags vegan, reecriture Groq, ou validation seule. Certaines "
            "options necessitent une cle GROQ_API_KEY saisie au clavier."
        ),
        kind="console",
        bat="run_recipe_pipeline.bat",
    ),
    Action(
        key="download_recipe_images",
        category="Pipeline complet",
        title="Telecharger les images de recettes",
        description=(
            "Telecharge automatiquement une photo par recette depuis l'API "
            "Unsplash, en filtrant les resultats tagges viande/poisson pour les "
            "recettes vegan/vegetariennes, et sauvegarde la progression dans "
            "frontend/public/images/recipes/_progress.json pour pouvoir reprendre "
            "apres une interruption. Respecte la limite gratuite Unsplash "
            "(~50 req/heure, 1,5 s entre requetes) -- peut etre long sur tout le "
            "catalogue."
        ),
        kind="capture",
        steps=(("{python}", "download_recipe_images.py"),),
    ),

    # ── Tests ───────────────────────────────────────────────────────────────
    Action(
        key="run_pytest",
        category="Tests",
        title="Lancer la suite de tests",
        description=(
            "Lance l'integralite de la suite de tests automatises (tests/) avec "
            "pytest en mode compact. Certains tests marques 'pipeline' ou "
            "'integration' necessitent que le pipeline nutrition ait tourne et/ou "
            "qu'un serveur uvicorn + base de donnees soient disponibles ; ils "
            "echoueront sinon sans que ce soit un vrai bug."
        ),
        kind="capture",
        steps=(("{python}", "-m", "pytest"),),
    ),
)


def find_root() -> Path:
    """Localise la racine du projet (dossier contenant backend/ et scripts/).

    En exe fige (PyInstaller), part du dossier de l'exe. En script, part du
    dossier parent de launcher/. Remonte ensuite l'arborescence au besoin.
    """
    if getattr(sys, "frozen", False):
        start = Path(sys.executable).resolve().parent
    else:
        start = Path(__file__).resolve().parent.parent

    for candidate in (start, *start.parents):
        if (candidate / "backend").is_dir() and (candidate / "scripts").is_dir():
            return candidate
    return start


def find_python(root: Path) -> str:
    """Trouve un interpreteur Python reel (jamais sys.executable en exe fige)."""
    for rel in ("venv/Scripts/python.exe", "env/Scripts/python.exe"):
        candidate = root / rel
        if candidate.exists():
            return str(candidate)
    for name in ("python", "py"):
        found = shutil.which(name)
        if found:
            return found
    return "python"


def categories() -> list[str]:
    seen: list[str] = []
    for action in ACTIONS:
        if action.category not in seen:
            seen.append(action.category)
    return seen
