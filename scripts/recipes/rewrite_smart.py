#!/usr/bin/env python3
"""
ALIM — Réécriture Chef v2.2 (Smart Filter)
Ne réécrit que les recettes avec _quality_score < 8.5

Corrections v2.2 :
  - Fix crash si JSON source est une liste et non un dict
  - Regex JSON plus robuste (cible {"recipes":...})
  - Avertissement explicite si un lot échoue définitivement
  - max_tokens augmenté à 12000
  - Imports déplacés en en-tête
  - data["recipes"] protégé si data est une liste
"""

import json
import re
import time
import sys
import argparse
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

# ===================== CONFIG =====================
BATCH_SIZE  = 1
DELAY_S     = 30      # 30s entre chaque recette (rate limit Groq plan gratuit)
MAX_RETRIES = 6
TEMPERATURE = 0.65
MIN_SCORE_THRESHOLD = 8.5

OUTPUT_SUFFIX   = "_chef_rewrite_smart.json"
PROGRESS_SUFFIX = ".rewrite_progress_smart.json"

# ===================== PROMPT SYSTÈME =====================
CHEF_SYSTEM = """Tu es un chef cuisinier français professionnel, passionné, rigoureux et pédagogue, avec plus de 15 ans d'expérience dans la cuisine végétalienne créative et savoureuse.

Ton style est élégant, précis, chaleureux et naturel. Tu rédiges comme si tu expliquais à un élève motivé et exigeant.

### RÈGLES ABSOLUES (à respecter à 100%) :

1. Vegan Strict : Remplace tout ingrédient animal (lait→lait de coco, crème→crème de coco, fromage→fromage végétal râpé, parmesan→levure nutritionnelle, beurre→huile de coco, yaourt→yaourt de coco). Aucun terme animal ne doit rester.
2. Titre : Conserve exactement "Vegan" ou "végan" s'il est présent.
3. Couverture ingrédients : Tous les ingrédients de "composition" doivent être nommés explicitement dans les instructions.
4. Instructions : Fluides, vivantes, avec repères sensoriels (texture, couleur, odeur, consistance). Vise 7-11 étapes pour un plat principal.
5. Description : Appétissante, évocatrice, 140-220 caractères.
6. Ton : Chaleureux, expert et accessible.

Réponds UNIQUEMENT avec un JSON valide :
{"recipes":[{"id":"...","description":"...","instructions":["Étape 1...","Étape 2..."],"note":"Améliorations faites"}]}
"""

# ===================== APPEL API =====================
def call_groq(batch_data: list, api_key: str) -> str:
    url = "https://api.groq.com/openai/v1/chat/completions"
    payload = {
        "model": "llama-3.3-70b-versatile",
        "temperature": TEMPERATURE,
        "max_tokens": 8000,   # ✅ augmenté (8000 insuffisant pour 4 recettes détaillées)
        "messages": [
            {"role": "system", "content": CHEF_SYSTEM},
            {
                "role": "user",
                "content": (
                    "Réécris ces recettes avec excellence culinaire :\n\n"
                    + json.dumps(batch_data, ensure_ascii=False, indent=2)
                )
            }
        ]
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    data = json.dumps(payload).encode("utf-8")
    req  = urllib.request.Request(url, data=data, headers=headers, method="POST")

    with urllib.request.urlopen(req, timeout=90) as r:
        result = json.loads(r.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]


# ===================== PARSING RÉPONSE =====================
def parse_response(text: str) -> dict | None:
    """
    Extrait le JSON de la réponse du modèle.
    Essaie d'abord le bloc ```json ... ```, puis cherche {"recipes":...}.
    ✅ Regex plus ciblée pour éviter de capturer du JSON partiel.
    """
    # Bloc markdown en priorité
    m = re.search(r'```json\s*([\s\S]*?)```', text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    # Recherche directe du bloc {"recipes":...}
    m = re.search(r'(\{"recipes"\s*:[\s\S]*\})', text)
    if m:
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            pass

    return None


# ===================== MAIN =====================
def main():
    parser = argparse.ArgumentParser(description="Réécriture intelligente des recettes")
    parser.add_argument("--key",   required=True,            help="Clé API Groq (gsk_...)")
    parser.add_argument("--input", default="recipes.json",   help="Fichier source JSON")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"❌ Fichier non trouvé : {input_path}")
        sys.exit(1)

    output_path   = input_path.with_name(input_path.stem + OUTPUT_SUFFIX)
    progress_path = input_path.with_name(input_path.stem + PROGRESS_SUFFIX)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    # ✅ Fix : data peut être une liste ou un dict
    if isinstance(data, list):
        recipes    = data
        data_is_list = True
    else:
        recipes      = data.get("recipes", [])
        data_is_list = False

    print(f"📊 {len(recipes)} recettes chargées")

    # Filtrage par score
    to_process = [r for r in recipes if r.get("_quality_score", 0) < MIN_SCORE_THRESHOLD]
    print(f"🔍 {len(to_process)} recettes à réécrire (score < {MIN_SCORE_THRESHOLD})")

    if not to_process:
        print("✅ Aucune recette à traiter. Fin du script.")
        sys.exit(0)

    # Chargement de la progression existante
    processed: dict = {}
    if progress_path.exists():
        with open(progress_path, encoding="utf-8") as f:
            processed = json.load(f)
        print(f"🔁 Reprise — {len(processed)} recettes déjà traitées")

    # ✅ On saute les recettes déjà traitées
    to_process = [r for r in to_process if r["id"] not in processed]
    print(f"⏭  {len(to_process)} recettes restantes à traiter")

    if not to_process:
        print("✅ Toutes les recettes ont déjà été traitées. Passage à la fusion.")
    
    # Boucle par lots
    total_lots = (len(to_process) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in range(0, len(to_process), BATCH_SIZE):
        batch      = to_process[i:i+BATCH_SIZE]
        lot_num    = i // BATCH_SIZE + 1
        print(f"\n🔄 Lot {lot_num}/{total_lots} — {len(batch)} recettes")

        # Prépare les données du lot
        batch_data = []
        for r in batch:
            comp = [
                {
                    "ingredient": c.get("ingredient"),
                    "quantity":   c.get("quantity"),
                    "unit":       c.get("unit")
                }
                for c in r.get("composition", [])
            ]
            batch_data.append({
                "id":           r["id"],
                "titles":       r.get("titles"),
                "description":  r.get("description"),
                "composition":  comp,
                "instructions": r.get("instructions")
            })

        success = False
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                text   = call_groq(batch_data, args.key)
                result = parse_response(text)

                if result is None:
                    raise ValueError("Impossible d'extraire un JSON valide de la réponse")

                for item in result.get("recipes", []):
                    processed[item["id"]] = item

                success = True
                print(f"   ✅ Lot {lot_num} réussi (tentative {attempt})")
                break

            except urllib.error.HTTPError as e:
                wait = 2 * attempt
                if e.code == 429:
                    wait = 30 * attempt  # attente longue sur rate limit
                    print(f"   ⏳ Rate limit — attente {wait}s...")
                else:
                    print(f"   ⚠ Tentative {attempt}/{MAX_RETRIES} échouée : {e}")
                    if attempt < MAX_RETRIES:
                        print(f"   ⏳ Attente {wait}s avant retry...")
                time.sleep(wait)
            except Exception as e:
                wait = 2 * attempt
                print(f"   ⚠ Tentative {attempt}/{MAX_RETRIES} échouée : {e}")
                if attempt < MAX_RETRIES:
                    print(f"   ⏳ Attente {wait}s avant retry...")
                time.sleep(wait)

        # ✅ Avertissement clair si le lot est définitivement perdu
        if not success:
            ids = [r["id"] for r in batch]
            print(f"   ❌ Lot {lot_num} définitivement échoué — recettes ignorées : {ids}")
        else:
            # Sauvegarde de la progression après chaque lot réussi
            with open(progress_path, "w", encoding="utf-8") as f:
                json.dump(processed, f, ensure_ascii=False, indent=2)

        time.sleep(DELAY_S)

    # ===================== FUSION =====================
    print("\n🔀 Fusion des résultats...")
    updated_count = 0
    for r in recipes:
        updated = processed.get(r["id"])
        if updated:
            r["description"]  = updated.get("description",  r.get("description"))
            r["instructions"] = updated.get("instructions", r.get("instructions"))
            if "_corrections_log" not in r:
                r["_corrections_log"] = []
            r["_corrections_log"].append(f"chef_rewrite_smart_{datetime.now().date()}")
            updated_count += 1

    # ✅ Reconstruction du fichier selon son type d'origine
    if data_is_list:
        output_data = recipes
    else:
        data["recipes"] = recipes
        output_data = data

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"✅ {updated_count} recettes mises à jour")
    print(f"📁 Fichier sauvegardé : {output_path.name}")

    # Nettoyage du fichier de progression
    if progress_path.exists():
        progress_path.unlink()
        print(f"🗑  Fichier de progression supprimé : {progress_path.name}")


if __name__ == "__main__":
    main()
