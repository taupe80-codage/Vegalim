"""
engine/clusterer.py
Regroupe les recettes similaires (variantes d'un même plat) par clustering
TF-IDF + similarité cosinus sur titre + ingrédients.

Sortie :
  - Chaque RecipeCDC reçoit un _cluster_id
  - Un dict cluster_id → [RecipeCDC] permet de travailler par groupe
    dans le synthesizer (une synthèse par cluster)
"""

from __future__ import annotations
import sys as _sys
import os as _os
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
import re
import logging
import hashlib
from collections import defaultdict
from typing import Optional

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import AgglomerativeClustering

from config.schema import RecipeCDC

log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
# REPRÉSENTATION TEXTUELLE D'UNE RECETTE (pour TF-IDF)
# ═══════════════════════════════════════════════════════════════════════════════

# Stopwords culinaires à ignorer (n'apportent pas de signal discriminant)
CULINARY_STOPWORDS = {
    "add","mix","stir","heat","cook","place","put","remove","serve",
    "cut","chop","slice","dice","pour","bring","let","use","make",
    "prepare","combine","transfer","set","aside","minutes","minute",
    "teaspoon","tablespoon","cup","ounce","pound","gram","ml","large",
    "small","medium","fresh","dry","dried","ground","whole","sliced",
    "chopped","diced","minced","optional","taste","salt","pepper",
    "water","oil","and","the","with","for","into","until",
    "ajoutez","mélangez","faites","cuire","coupez","servez","ajoutez",
    "versez","incorporez","chauffez","préparez",
}

def _recipe_text(recipe: RecipeCDC) -> str:
    """
    Représentation textuelle normalisée d'une recette pour TF-IDF.
    On pondère le titre (×3) et les ingrédients (×2) vs instructions.
    """
    title = re.sub(r"[^\w\s]", " ", (recipe.titles.get("en") or recipe.titles.get("fr") or "")).lower()

    ingredient_tokens = " ".join(
        c.ingredient.replace("_", " ")
        for c in recipe.composition
    )

    instruction_tokens = " ".join(recipe.instructions).lower()
    instruction_tokens = re.sub(r"[^\w\s]", " ", instruction_tokens)

    # Pondération par répétition
    return f"{title} {title} {title} {ingredient_tokens} {ingredient_tokens} {instruction_tokens}"


# ═══════════════════════════════════════════════════════════════════════════════
# CLUSTERER PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class RecipeClusterer:
    """
    Regroupe des recettes similaires par clustering hiérarchique agglomératif
    sur matrice TF-IDF cosinus.

    Paramètres :
        similarity_threshold  : distance max pour être dans le même cluster
                                (0.0 = identiques, 1.0 = totalement différents)
                                Recommandé : 0.55–0.75
        min_df / max_df       : filtre TF-IDF (ignorer termes trop rares/fréquents)
        ngram_range           : unigrammes + bigrammes par défaut
    """

    def __init__(
        self,
        similarity_threshold: float = 0.65,
        min_df: int = 1,
        max_df: float = 0.95,
        ngram_range: tuple = (1, 2),
    ):
        self.threshold = similarity_threshold
        self.vectorizer = TfidfVectorizer(
            stop_words=list(CULINARY_STOPWORDS),
            min_df=min_df,
            max_df=max_df,
            ngram_range=ngram_range,
            sublinear_tf=True,   # log(tf+1) → réduit l'effet des mots très fréquents
        )
        self.labels_: Optional[np.ndarray] = None
        self.matrix_: Optional[np.ndarray] = None

    def fit(self, recipes: list[RecipeCDC]) -> "RecipeClusterer":
        """Calcule les clusters sur la liste de recettes."""
        if len(recipes) < 2:
            # Cas dégénéré : un seul cluster par recette
            for i, r in enumerate(recipes):
                r._cluster_id = self._cluster_label(i)
            self.labels_ = np.array(list(range(len(recipes))))
            return self

        texts = [_recipe_text(r) for r in recipes]

        # Matrice TF-IDF
        tfidf_matrix = self.vectorizer.fit_transform(texts)
        self.matrix_ = tfidf_matrix

        # Distance cosinus = 1 − similarité
        sim_matrix = cosine_similarity(tfidf_matrix)
        dist_matrix = 1.0 - sim_matrix
        dist_matrix = np.clip(dist_matrix, 0.0, 1.0)

        # Clustering agglomératif (average linkage → équilibre taille/cohérence)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=self.threshold,
            metric="precomputed",
            linkage="average",
        )
        self.labels_ = clustering.fit_predict(dist_matrix)

        # Assigner les cluster_ids
        for recipe, label in zip(recipes, self.labels_):
            recipe._cluster_id = self._cluster_label(int(label))

        n_clusters = len(set(self.labels_))
        log.info(
            f"Clustering → {n_clusters} clusters pour {len(recipes)} recettes "
            f"(threshold={self.threshold})"
        )
        return self

    def _cluster_label(self, idx: int) -> str:
        return f"cluster_{idx:04d}"

    def get_clusters(self, recipes: list[RecipeCDC]) -> dict[str, list[RecipeCDC]]:
        """
        Retourne un dict {cluster_id: [recettes]}.
        Trie chaque cluster du plus complet au moins complet (nb ingrédients desc).
        """
        clusters: dict[str, list[RecipeCDC]] = defaultdict(list)
        for r in recipes:
            clusters[r._cluster_id].append(r)

        # Tri interne : recettes avec le plus d'ingrédients en premier
        for cid in clusters:
            clusters[cid].sort(key=lambda r: -len(r.composition))

        return dict(clusters)

    def top_variants(
        self,
        clusters: dict[str, list[RecipeCDC]],
        max_per_cluster: int = 5,
    ) -> dict[str, list[RecipeCDC]]:
        """
        Retourne les N meilleures variantes par cluster (pour limiter les tokens Groq).
        Score = nb ingrédients + nb étapes instructions.
        """
        result = {}
        for cid, members in clusters.items():
            scored = sorted(
                members,
                key=lambda r: len(r.composition) * 2 + len(r.instructions),
                reverse=True,
            )
            result[cid] = scored[:max_per_cluster]
        return result

    def cluster_summary(self, clusters: dict[str, list[RecipeCDC]]) -> dict:
        """Statistiques sur le résultat du clustering."""
        sizes = [len(v) for v in clusters.values()]
        singleton_rate = sum(1 for s in sizes if s == 1) / len(sizes) if sizes else 0
        return {
            "n_clusters":      len(clusters),
            "n_recipes":       sum(sizes),
            "max_cluster_size": max(sizes) if sizes else 0,
            "avg_cluster_size": round(sum(sizes) / len(sizes), 2) if sizes else 0,
            "singleton_rate":  round(singleton_rate, 2),
            "multi_variant_clusters": sum(1 for s in sizes if s > 1),
        }


# ═══════════════════════════════════════════════════════════════════════════════
# INTERFACE SIMPLIFIÉE
# ═══════════════════════════════════════════════════════════════════════════════

def cluster_recipes(
    recipes: list[RecipeCDC],
    similarity_threshold: float = 0.65,
    max_variants_per_cluster: int = 5,
    verbose: bool = True,
) -> tuple[dict[str, list[RecipeCDC]], dict]:
    """
    Point d'entrée unique.
    Retourne (clusters_dict, stats).

    Exemple :
        clusters, stats = cluster_recipes(parsed_recipes)
        for cluster_id, variants in clusters.items():
            synthesized = synthesizer.synthesize(variants)
    """
    clusterer = RecipeClusterer(similarity_threshold=similarity_threshold)
    clusterer.fit(recipes)

    all_clusters = clusterer.get_clusters(recipes)
    top_clusters = clusterer.top_variants(all_clusters, max_per_cluster=max_variants_per_cluster)
    stats = clusterer.cluster_summary(all_clusters)

    if verbose:
        log.info(f"Clustering summary: {stats}")
        large = [(cid, len(members)) for cid, members in all_clusters.items() if len(members) > 3]
        large.sort(key=lambda x: -x[1])
        if large:
            log.info("Top clusters multi-variantes :")
            for cid, n in large[:10]:
                sample = all_clusters[cid][0].titles.get("en", "?")
                log.info(f"  {cid}: {n} variantes — ex: {sample}")

    return top_clusters, stats


# ═══════════════════════════════════════════════════════════════════════════════
# RECHERCHE DE SIMILARITÉ (sans clustering)
# ═══════════════════════════════════════════════════════════════════════════════

def find_similar(
    query_recipe: RecipeCDC,
    corpus: list[RecipeCDC],
    top_k: int = 5,
    min_similarity: float = 0.3,
) -> list[tuple[RecipeCDC, float]]:
    """
    Trouve les recettes les plus similaires à une recette de requête.
    Utile pour la déduplication ou la recommandation.
    Retourne [(recette, score)] trié par score décroissant.
    """
    all_recipes = [query_recipe] + corpus
    texts = [_recipe_text(r) for r in all_recipes]

    vectorizer = TfidfVectorizer(
        stop_words=list(CULINARY_STOPWORDS),
        ngram_range=(1, 2),
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(texts)
    sim = cosine_similarity(matrix[0:1], matrix[1:])[0]

    results = [
        (corpus[i], float(sim[i]))
        for i in np.argsort(sim)[::-1]
        if float(sim[i]) >= min_similarity
    ]
    return results[:top_k]


def deduplicate(
    recipes: list[RecipeCDC],
    similarity_threshold: float = 0.90,
) -> list[RecipeCDC]:
    """
    Supprime les quasi-doublons exacts (similarity > 0.90 par défaut).
    Garde la recette la plus complète (nb ingrédients + nb étapes max).
    """
    if len(recipes) < 2:
        return recipes

    texts  = [_recipe_text(r) for r in recipes]
    vect   = TfidfVectorizer(stop_words=list(CULINARY_STOPWORDS), sublinear_tf=True)
    matrix = vect.fit_transform(texts)
    sim    = cosine_similarity(matrix)

    to_remove: set[int] = set()
    for i in range(len(recipes)):
        if i in to_remove:
            continue
        for j in range(i + 1, len(recipes)):
            if sim[i][j] >= similarity_threshold:
                # Garder le plus complet
                score_i = len(recipes[i].composition) + len(recipes[i].instructions)
                score_j = len(recipes[j].composition) + len(recipes[j].instructions)
                to_remove.add(j if score_i >= score_j else i)

    deduped = [r for i, r in enumerate(recipes) if i not in to_remove]
    log.info(f"Déduplication → {len(deduped)}/{len(recipes)} recettes conservées")
    return deduped