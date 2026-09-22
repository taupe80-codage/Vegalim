#!/usr/bin/env python3
"""Extrait un resume enrichi des recettes depuis recipes.json, pour revue
reguliere et pour alimenter l'artifact HTML de selection/comparaison
(recipe_list_artifact).

Usage:
    python extract_recipe_list.py

Genere (a cote de recipes.json):
    - recipe_list.json  : liste plate triee par titre (titre, cuisine, type,
                           regimes, allergenes, portions, temps, confiance,
                           description, composition, alertes qualite,
                           doublons potentiels par similarite de titre),
                           utilisee comme source pour regenerer l'artifact
                           interactif
    - recipe_list.md    : liste lisible groupee par lettre, pour revue
                           directe dans le repo (git diff facile a lire)
"""
from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "recipes.json"
OUT_JSON = ROOT / "recipe_list.json"
OUT_MD = ROOT / "recipe_list.md"

LOW_CONFIDENCE_THRESHOLD = 0.6

# Mots qui marquent une variante plutot qu'un plat different : on les retire
# avant de comparer les titres, sinon "X" et "X (Vegan)" ne matchent jamais
# assez fort.
VARIANT_WORDS = {
    "vegan", "vegane", "vegetal", "vegetale", "vegetalienne", "vegetarien",
    "vegetarienne", "veggie", "classic", "classique", "rapide", "express",
    "traditionnel", "traditionnelle", "maison", "simple", "facile",
    "original", "originale", "version", "recette",
}

JACCARD_THRESHOLD = 0.6
MIN_SHARED_WORDS = 2  # sauf si les titres normalises sont strictement identiques
MAX_SIMILAR_PER_RECIPE = 6


def load_recipes():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    return data["recipes"], data.get("metadata", {})


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


def normalize_title(title: str) -> str:
    """Normalise un titre pour comparaison : minuscules, sans accents, sans
    parentheses, sans ponctuation, sans mots de variante (vegan, rapide...)."""
    t = _strip_accents(title or "").lower()
    t = re.sub(r"\([^)]*\)", " ", t)  # retire le contenu entre parentheses
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    words = [w for w in t.split() if w and w not in VARIANT_WORDS]
    return " ".join(words)


def significant_words(normalized: str) -> set[str]:
    return {w for w in normalized.split() if len(w) >= 4}


def extract(recipes):
    out = []
    for r in recipes:
        title = (r.get("titles") or {}).get("fr") or r.get("id", "")
        tags = r.get("tags") or {}
        diet = tags.get("diet", []) or []
        composition = [
            {
                "ingredient": c.get("ingredient", ""),
                "quantity": c.get("quantity"),
                "unit": c.get("unit", ""),
            }
            for c in (r.get("composition") or [])
        ]
        instructions = r.get("instructions") or []
        description = (r.get("description") or "").strip()
        confidence = (r.get("scoring") or {}).get("confidence")

        flags = []
        if not instructions:
            flags.append("no_instructions")
        if not description:
            flags.append("no_description")
        if not composition:
            flags.append("no_composition")
        if isinstance(confidence, (int, float)) and confidence < LOW_CONFIDENCE_THRESHOLD:
            flags.append("low_confidence")

        out.append({
            "id": r.get("id", ""),
            "title": title,
            "cuisine": (r.get("origin") or {}).get("cuisine", ""),
            "dish_type": r.get("dish_type", ""),
            "vegan": "vegan" in diet,
            "diet": diet,
            "allergens": tags.get("allergens", []) or [],
            "servings": r.get("servings"),
            "time_total": (r.get("timing") or {}).get("total_min"),
            "confidence": confidence,
            "description": description,
            "composition": composition,
            "n_instructions": len(instructions),
            "flags": flags,
            "similar": [],  # rempli par find_duplicates()
        })
    out.sort(key=lambda x: x["title"].casefold())
    return out


def find_duplicates(rows: list[dict]) -> None:
    """Detecte les titres probablement doublons/variantes du meme plat et
    remplit le champ 'similar' de chaque recette (in-place).

    Le score est un indice de Jaccard sur les mots significatifs (>=4
    lettres) du titre normalise : bien plus fiable qu'un ratio de
    caracteres brut, qui matche a tort des titres courts ne partageant
    qu'un seul mot (ex. "Aubergines Parmigiana Simple" / "Aubergines
    Sichuan" partagent juste "aubergines" mais ne sont pas le meme plat).

    Un seul mot partage ne suffit pas (trop de faux positifs, ex. "Bagel
    Fromage Frais Concombre" / "Fromage Frais"), sauf si les deux titres
    normalises sont strictement identiques (cas le plus sur : meme plat,
    seul le mot de variante — vegan, rapide... — differe)."""
    norm = [normalize_title(r["title"]) for r in rows]
    sig = [significant_words(n) for n in norm]
    matches: list[list[tuple[float, int]]] = [[] for _ in rows]

    n = len(rows)
    for i in range(n):
        if not sig[i]:
            continue
        for j in range(i + 1, n):
            if not sig[j]:
                continue
            inter = sig[i] & sig[j]
            if not inter:
                continue
            exact = bool(norm[i]) and norm[i] == norm[j]
            if not exact and len(inter) < MIN_SHARED_WORDS:
                continue
            union = sig[i] | sig[j]
            jaccard = len(inter) / len(union)
            if exact or jaccard >= JACCARD_THRESHOLD:
                score = 1.0 if exact else jaccard
                matches[i].append((score, j))
                matches[j].append((score, i))

    for i, row in enumerate(rows):
        best = sorted(matches[i], key=lambda t: -t[0])[:MAX_SIMILAR_PER_RECIPE]
        row["similar"] = [
            {"id": rows[j]["id"], "title": rows[j]["title"], "score": round(score, 2)}
            for score, j in best
        ]


def write_json(rows):
    OUT_JSON.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def letter_of(title):
    c = (title or "").strip()[:1].upper()
    return c if c.isalpha() else "#"


def write_md(rows, total):
    n_flagged = sum(1 for r in rows if r["flags"])
    n_dup_clusters = sum(1 for r in rows if r["similar"])
    lines = [
        "# Liste des recettes ALIM",
        "",
        f"{total} recettes ({n_flagged} avec une alerte qualite, "
        f"{n_dup_clusters} avec un doublon potentiel detecte). Genere "
        "automatiquement par `_scripts/extract_recipe_list.py` a partir de "
        "`recipes.json` — ne pas editer a la main.",
        "",
    ]
    current_letter = None
    for r in rows:
        L = letter_of(r["title"])
        if L != current_letter:
            current_letter = L
            lines.append(f"\n## {L}\n")
        tags = list(r["diet"])
        if r["dish_type"]:
            tags.append(r["dish_type"])
        if r["cuisine"]:
            tags.append(r["cuisine"])
        tag_str = f" _({', '.join(tags)})_" if tags else ""
        warn = ""
        if r["flags"]:
            warn += " ⚠ " + ", ".join(r["flags"])
        if r["similar"]:
            warn += f" 🔁 doublon possible : " + ", ".join(s["title"] for s in r["similar"][:3])
        lines.append(f"- **{r['title']}**{tag_str} — `{r['id']}`{warn}")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main():
    recipes, metadata = load_recipes()
    rows = extract(recipes)
    find_duplicates(rows)
    write_json(rows)
    write_md(rows, len(rows))
    n_flagged = sum(1 for r in rows if r["flags"])
    n_dup = sum(1 for r in rows if r["similar"])
    print(
        f"{len(rows)} recettes -> {OUT_JSON.name}, {OUT_MD.name} "
        f"({n_flagged} alertes, {n_dup} avec doublon potentiel)"
    )


if __name__ == "__main__":
    main()
