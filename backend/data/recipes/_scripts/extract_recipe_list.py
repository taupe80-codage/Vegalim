#!/usr/bin/env python3
"""Extrait un resume plat des recettes (id, titre, cuisine, type, vegan) depuis
recipes.json, pour revue reguliere et pour alimenter l'artifact HTML de
selection/suppression (recipe_list_artifact).

Usage:
    python extract_recipe_list.py

Genere (a cote de recipes.json):
    - recipe_list.json  : liste plate triee par titre, utilisee comme source
                           pour regenerer l'artifact interactif
    - recipe_list.md    : liste lisible groupee par lettre, pour revue directe
                           dans le repo (git diff facile a lire)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "recipes.json"
OUT_JSON = ROOT / "recipe_list.json"
OUT_MD = ROOT / "recipe_list.md"


def load_recipes():
    data = json.loads(SRC.read_text(encoding="utf-8"))
    return data["recipes"], data.get("metadata", {})


def extract(recipes):
    out = []
    for r in recipes:
        title = (r.get("titles") or {}).get("fr") or r.get("id", "")
        out.append({
            "id": r.get("id", ""),
            "title": title,
            "cuisine": (r.get("origin") or {}).get("cuisine", ""),
            "dish_type": r.get("dish_type", ""),
            "vegan": "vegan" in (r.get("tags") or {}).get("diet", []),
        })
    out.sort(key=lambda x: x["title"].casefold())
    return out


def write_json(rows):
    OUT_JSON.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def letter_of(title):
    c = (title or "").strip()[:1].upper()
    return c if c.isalpha() else "#"


def write_md(rows, total):
    lines = [
        "# Liste des recettes ALIM",
        "",
        f"{total} recettes. Genere automatiquement par "
        "`_scripts/extract_recipe_list.py` a partir de `recipes.json` "
        "— ne pas editer a la main.",
        "",
    ]
    current_letter = None
    for r in rows:
        L = letter_of(r["title"])
        if L != current_letter:
            current_letter = L
            lines.append(f"\n## {L}\n")
        tags = []
        if r["vegan"]:
            tags.append("vegan")
        if r["dish_type"]:
            tags.append(r["dish_type"])
        if r["cuisine"]:
            tags.append(r["cuisine"])
        tag_str = f" _({', '.join(tags)})_" if tags else ""
        lines.append(f"- **{r['title']}**{tag_str} — `{r['id']}`")
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    recipes, metadata = load_recipes()
    rows = extract(recipes)
    write_json(rows)
    write_md(rows, len(rows))
    print(f"{len(rows)} recettes -> {OUT_JSON.name}, {OUT_MD.name}")


if __name__ == "__main__":
    main()
