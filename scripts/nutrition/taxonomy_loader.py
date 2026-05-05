"""
taxonomy_loader.py
==================
Utilitaire partagé : charge taxonomy_session_*.json et construit
BK_TO_TAXONOMY, le dictionnaire de lookup principal utilisé par les 4
scripts de build (CIQUAL, CNF, Ontologie, Aliases).

Format de sortie (par bk) :
    {
        "group_id":       "G02",
        "group_label":    "Boissons alcoolisées",
        "subgroup_id":    "sg_bieres",
        "subgroup_label": "Bières"
    }

Usage :
    from taxonomy_loader import load_bk_taxonomy
    BK_TO_TAXONOMY = load_bk_taxonomy("path/to/taxonomy_session_*.json")
    tax = BK_TO_TAXONOMY.get("agar")          # → dict ou None
    tax = BK_TO_TAXONOMY.get("biere_brune")   # → dict avec sg_bieres
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sentinel d'entrée non classifiée
# ---------------------------------------------------------------------------
UNCLASSIFIED_TAXONOMY: dict = {
    "group_id":       None,
    "group_label":    None,
    "subgroup_id":    None,
    "subgroup_label": None,
}


def load_bk_taxonomy(path: str | Path) -> dict[str, dict]:
    """
    Charge le fichier taxonomy_session JSON et retourne BK_TO_TAXONOMY.

    Structure attendue du JSON source :
        {
          "taxonomy": [
            {
              "id": "G02",
              "label": "Boissons alcoolisées",
              "subgroups": [{"id": "sg_bieres", "label": "Bières"}, ...],
              "entries": [{"bk": "biere_5", "sg": "sg_bieres"}, ...]
            },
            ...
          ]
        }

    Paramètres
    ----------
    path : chemin vers taxonomy_session_*.json

    Retourne
    --------
    dict[bk_str, taxonomy_dict]
        Chaque valeur contient group_id, group_label, subgroup_id,
        subgroup_label. Retourne {} en cas d'erreur (non bloquant).

    Garanties
    ---------
    - Aucune concatenation bk+label (pas de "sg_bieres_bieres").
    - Les bk non résolus dans un groupe produisent un log warning et
      sont ignorés (fallback dans le script appelant).
    - Thread-safe en lecture seule après construction.
    """
    path = Path(path)
    if not path.exists():
        logger.error("taxonomy_loader: fichier introuvable : %s", path)
        return {}

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("taxonomy_loader: lecture impossible (%s) : %s", path, exc)
        return {}

    taxonomy_array = raw.get("taxonomy")
    if not isinstance(taxonomy_array, list):
        logger.error(
            "taxonomy_loader: clé 'taxonomy' manquante ou malformée dans %s", path
        )
        return {}

    bk_to_taxonomy: dict[str, dict] = {}
    total_groups   = 0
    total_entries  = 0
    skipped        = 0

    for group in taxonomy_array:
        group_id    = group.get("id")
        group_label = group.get("label", "")
        subgroups   = {sg["id"]: sg["label"] for sg in group.get("subgroups", [])}
        entries     = group.get("entries", [])

        if not group_id:
            logger.warning("taxonomy_loader: groupe sans 'id', ignoré : %s", group)
            continue

        total_groups += 1

        for entry in entries:
            bk  = entry.get("bk")
            sg  = entry.get("sg")      # subgroup id (ex : "sg_bieres")

            if not bk:
                skipped += 1
                continue

            if sg and sg not in subgroups:
                logger.warning(
                    "taxonomy_loader: bk=%r — sg=%r introuvable dans "
                    "les subgroups du groupe %s",
                    bk, sg, group_id,
                )

            subgroup_label = subgroups.get(sg) if sg else None

            # Protection anti-doublon : le premier groupe qui revendique
            # un bk est prioritaire (les entrées sont ordonnées).
            if bk in bk_to_taxonomy:
                logger.debug(
                    "taxonomy_loader: bk=%r déjà indexé (groupe %s), "
                    "entrée groupe %s ignorée",
                    bk, bk_to_taxonomy[bk]["group_id"], group_id,
                )
                continue

            bk_to_taxonomy[bk] = {
                "group_id":       group_id,
                "group_label":    group_label,
                "subgroup_id":    sg,
                "subgroup_label": subgroup_label,
            }
            total_entries += 1

    logger.info(
        "taxonomy_loader: %d groupes, %d entrées indexées, %d ignorées — source: %s",
        total_groups, total_entries, skipped, path.name,
    )
    return bk_to_taxonomy


def resolve_taxonomy(bk: str | None, bk_taxonomy: dict[str, dict]) -> dict | None:
    """
    Résout un bk en objet taxonomy structuré.

    Retourne None si le bk est None ou absent de la taxonomie
    (le script appelant doit décider de son fallback : conserver
    l'ancien champ category, injecter UNCLASSIFIED_TAXONOMY, etc.).
    """
    if not bk:
        return None
    return bk_taxonomy.get(bk)


def build_taxonomy_object(
    bk: str | None,
    bk_taxonomy: dict[str, dict],
    *,
    fallback_unclassified: bool = True,
) -> dict | None:
    """
    Retourne le dict taxonomy prêt à être injecté dans l'objet food.

    Paramètres
    ----------
    bk                    : base key (ingredient_key / group_key)
    bk_taxonomy           : résultat de load_bk_taxonomy()
    fallback_unclassified : si True, retourne UNCLASSIFIED_TAXONOMY quand
                            le bk est absent ; si False, retourne None.

    Exemple de retour :
        {
            "group_id":       "G02",
            "group_label":    "Boissons alcoolisées",
            "subgroup_id":    "sg_bieres",
            "subgroup_label": "Bières"
        }
    """
    result = resolve_taxonomy(bk, bk_taxonomy)
    if result is not None:
        return result
    if fallback_unclassified:
        return dict(UNCLASSIFIED_TAXONOMY)   # copie défensive
    return None
