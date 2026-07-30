"""
ALIM — Téléchargement automatique des images de recettes via Unsplash API
=========================================================================

Prérequis :
    pip install requests
    export UNSPLASH_ACCESS_KEY="votre_cle_unsplash"   (clé gratuite sur unsplash.com/developers)

Utilisation :
    python download_recipe_images.py
"""

import json
import os
import time
import unicodedata
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Module 'requests' manquant. Lance : pip install requests")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════════════

UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY")
if not UNSPLASH_ACCESS_KEY:
    print("❌ Variable d'environnement UNSPLASH_ACCESS_KEY manquante.")
    print("   Lance : export UNSPLASH_ACCESS_KEY=\"votre_cle\"  (clé gratuite sur unsplash.com/developers)")
    sys.exit(1)

RECIPES_JSON_PATH = Path(__file__).parent / "backend" / "data" / "recipes" / "recipes.json"
OUTPUT_DIR        = Path(__file__).parent / "frontend" / "public" / "images" / "recipes"
PROGRESS_FILE     = OUTPUT_DIR / "_progress.json"

# small=400px | regular=1080px | full=original
IMAGE_SIZE = "regular"

# Délai entre requêtes (limite gratuite Unsplash : 50 req/heure)
DELAY_SECONDS = 1.5

# ══════════════════════════════════════════════════════════════
#  FILTRE ANTI-VIANDE
#  On filtre UNIQUEMENT sur les tags Unsplash (pas la description)
#  car la description peut dire "sans viande" et déclencher un faux positif
# ══════════════════════════════════════════════════════════════
MEAT_TAGS = {
    "meat", "beef", "pork", "chicken", "turkey", "lamb",
    "bacon", "ham", "sausage", "steak", "seafood", "fish",
    "salmon", "tuna", "shrimp", "prawn", "lobster",
}


# ══════════════════════════════════════════════════════════════
#  FONCTIONS
# ══════════════════════════════════════════════════════════════

def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower().strip()
    text = re.sub(r"[\s_/\\]+", "-", text)
    text = re.sub(r"[^a-z0-9-]", "", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text


def load_recipes() -> list:
    if not RECIPES_JSON_PATH.exists():
        print(f"❌ Fichier recettes introuvable : {RECIPES_JSON_PATH}")
        sys.exit(1)
    with open(RECIPES_JSON_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("recipes", [])


def build_query(recipe: dict) -> str:
    """
    Requête courte et efficace :
    - Nom de la recette en anglais (meilleur résultat Unsplash)
    - + "vegetarian" pour orienter sans bloquer
    On évite les requêtes trop longues qui donnent zéro résultat.
    """
    titles  = recipe.get("titles", {})
    # Unsplash est en anglais → on préfère le titre anglais
    name    = titles.get("en") or titles.get("fr") or titles.get("original", "")
    is_vegan = recipe.get("diet_flags", {}).get("vegan", False)

    label = "vegan" if is_vegan else "vegetarian"
    return f"{name} {label}", name


def is_meat_free(result: dict) -> tuple:
    """
    Vérifie uniquement les TAGS Unsplash (pas la description).
    Les tags sont les mots-clés choisis explicitement pour décrire l'image.
    """
    tags = {tag.get("title", "").lower() for tag in result.get("tags", [])}
    for keyword in MEAT_TAGS:
        if keyword in tags:
            return False, keyword
    return True, ""


def search_unsplash_safe(recipe: dict):
    """
    Cherche une image végétarienne.
    - Récupère 5 résultats
    - Filtre sur les tags uniquement
    - Si tous rejetés → retente sans le label végé (fallback)
    """
    url     = "https://api.unsplash.com/search/photos"
    headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
    query, name = build_query(recipe)

    queries_to_try = [
        query,           # "Vegetable Korma vegetarian"
        name,            # "Vegetable Korma"  (sans label végé — fallback)
    ]

    for q in queries_to_try:
        params = {
            "query":          q,
            "per_page":       10,
            "orientation":    "landscape",
            "content_filter": "high",
        }
        try:
            r = requests.get(url, params=params, headers=headers, timeout=10)

            if r.status_code == 401:
                print("\n❌ Clé API Unsplash invalide.")
                sys.exit(1)
            if r.status_code == 429:
                print("\n⏳ Limite API atteinte. Attente 60s...")
                time.sleep(60)
                return search_unsplash_safe(recipe)
            if r.status_code != 200:
                continue

            results = r.json().get("results", [])
            for photo in results:
                ok, _ = is_meat_free(photo)
                if ok:
                    return photo

        except requests.RequestException:
            continue

    return None


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=30, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception:
        return False


def generate_slug_mapping(recipes: list) -> list:
    result = []
    seen   = {}
    for r in recipes:
        titles = r.get("titles", {})
        name   = titles.get("fr") or titles.get("en") or titles.get("original", "")
        if not name:
            continue
        slug = slugify(name)
        if slug in seen:
            seen[slug] += 1
            slug = f"{slug}-{seen[slug]}"
        else:
            seen[slug] = 1
        result.append((r, name, slug))
    return result


def load_progress() -> int:
    try:
        if PROGRESS_FILE.exists():
            with open(PROGRESS_FILE, encoding="utf-8") as f:
                return json.load(f).get("last_index", 0)
    except Exception:
        pass
    return 0


def save_progress(index: int, total: int) -> None:
    with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_index": index, "total": total}, f)


# ══════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════

def main():
    print("═══════════════════════════════════════════════════")
    print("  ALIM — Téléchargement images recettes (Unsplash)")
    print("  🥦 Filtre anti-viande (tags uniquement)")
    print("═══════════════════════════════════════════════════\n")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    recipes = load_recipes()
    items   = generate_slug_mapping(recipes)
    total   = len(items)

    mapping_path = OUTPUT_DIR / "_slug_mapping.json"
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump({slug: name for _, name, slug in items}, f, ensure_ascii=False, indent=2)

    print(f"📋 {total} recettes chargées")
    print(f"📁 Destination : {OUTPUT_DIR}\n")

    start_index = load_progress()
    if 0 < start_index < total:
        print(f"🔁 Reprise depuis la recette {start_index + 1}/{total} : "
              f"{items[start_index][1][:50]}\n")
    else:
        start_index = 0
        print("▶️  Démarrage depuis le début\n")

    success = 0
    skipped = 0
    failed  = 0

    for i, (recipe, name, slug) in enumerate(items):

        if i < start_index:
            skipped += 1
            continue

        dest = OUTPUT_DIR / f"{slug}.jpg"
        pct  = int(((i + 1) / total) * 40)
        bar  = "█" * pct + "░" * (40 - pct)
        print(f"[{bar}] {i+1}/{total} — {name[:45]:<45}", end=" ")

        if dest.exists():
            print("⏭️  déjà présente")
            save_progress(i + 1, total)
            skipped += 1
            continue

        result = search_unsplash_safe(recipe)

        if not result:
            print("❌ aucun résultat")
            failed += 1
            save_progress(i + 1, total)
            time.sleep(DELAY_SECONDS)
            continue

        img_url      = result["urls"].get(IMAGE_SIZE) or result["urls"]["regular"]
        photographer = result.get("user", {}).get("name", "inconnu")

        if download_image(img_url, dest):
            print(f"✅ {photographer}")
            success += 1
        else:
            print("❌ échec download")
            failed += 1

        save_progress(i + 1, total)
        time.sleep(DELAY_SECONDS)

    print(f"\n{'═'*51}")
    print(f"  ✅ Téléchargées  : {success}")
    print(f"  ⏭️  Ignorées      : {skipped}")
    print(f"  ❌ Échouées      : {failed}")
    print(f"  📁 Dossier       : {OUTPUT_DIR}")
    print(f"{'═'*51}\n")

    if success + failed + skipped >= total:
        PROGRESS_FILE.unlink(missing_ok=True)
        print("🎉 Terminé ! Toutes les recettes ont été traitées.\n")
    else:
        remaining = total - (success + failed + start_index)
        print(f"💡 {remaining} recettes restantes. Relance le script pour continuer.\n")


if __name__ == "__main__":
    main()
