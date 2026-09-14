#!/usr/bin/env python3
"""
update_prices.py — Met à jour les prix du catalogue via Open Food Facts Open Prices.

Usage :
    python scripts/update_prices.py            # met à jour tout
    python scripts/update_prices.py --dry-run  # affiche les changements sans écrire
    python scripts/update_prices.py --key tofu olive_oil  # ciblé

Stratégie (en 2 étapes — voir "Piège corrigé" plus bas) :
  Pour chaque ingrédient du catalogue :
  1. Cherche des produits correspondants sur la base produits Open Food Facts
     (recherche plein texte par nom FR), puis ne garde QUE les produits dont
     le nom contient réellement les mots significatifs de la recherche
     (l'API de recherche OFF est un plein-texte assez large : une recherche
     "huile d'olive" remonte aussi "Ratatouille" ou "Gazpacho" — on filtre
     nous-mêmes côté client plutôt que de faire confiance au classement).
  2. Pour les codes-barres retenus (jusqu'à 5), récupère les prix reels
     depuis Open Prices (prices.openfoodfacts.org) par product_code.
  3. Calcule la médiane de tous les prix recueillis et compare à l'ancien prix.
  4. Met à jour si l'écart > 10 % OU si demandé en force.
  5. Marque la date de mise à jour.

Les ingrédients sans résultat restent inchangés (pas de prix moyen inventé).

Piège corrigé (2026-07-29) : l'ancienne version interrogeait directement
prices.openfoodfacts.org avec un paramètre `product__product_name__icontains`
qui n'existe pas sur cette API — silencieusement ignoré, il renvoyait donc le
même jeu de résultats non filtré pour CHAQUE recherche (vérifié : une
recherche sur une chaîne absurde retournait le même résultat qu'une vraie
recherche). Résultat : ~93 % du catalogue s'est retrouvé avec le même prix
médian bidon (3,69 €), y compris pour de l'eau du robinet. Le champ
`product_name` sur les objets Price d'Open Prices est lui-même presque
toujours vide (les prix sont rattachés par code-barres, pas par nom) : le
texte doit donc être cherché sur la base produits OFF, puis les prix
récupérés par code-barres — d'où la recherche en 2 étapes ci-dessus.
"""
from __future__ import annotations
import argparse
import json
import re
import statistics
import time
import unicodedata
from datetime import date
from pathlib import Path

import requests

CATALOG_PATH = Path(__file__).parent.parent / "backend/data/config/prices_catalog.json"
SEARCH_URL = "https://world.openfoodfacts.org/cgi/search.pl"
PRICES_API_BASE = "https://prices.openfoodfacts.org/api/v1"
THRESHOLD = 0.10   # 10 % d'écart minimum pour déclencher mise à jour
DELAY = 0.4        # secondes entre requêtes
MAX_BARCODES = 5   # nb max de produits distincts interrogés par ingrédient
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
# OFF bloque en 403 les requetes sans User-Agent explicite (politique anti-abus)
HEADERS = {"User-Agent": "ALIM-PriceSync/1.0 (script interne, usage non-commercial)"}


def _strip_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _normalize(s: str) -> str:
    s = _strip_accents((s or "").lower())
    return re.sub(r"[^a-z0-9\s]", " ", s)


def _significant_words(s: str) -> set[str]:
    return {w for w in _normalize(s).split() if len(w) >= 3}


def _get_with_retries(url: str, params: dict) -> dict | None:
    """Requete avec backoff exponentiel. Les 503 (surcharge serveur, frequent
    sur l'endpoint de recherche classique OFF) recoivent un delai plus long
    qu'un simple timeout reseau, sinon on relance trop vite dans le mur."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            resp = requests.get(url, params=params, headers=HEADERS, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if attempt == MAX_RETRIES:
                print(f"    ⚠ API erreur ({url.split('/')[2]}, HTTP {status}): {e}")
                return None
            backoff = (3.0 if status == 503 else 1.0) * (attempt + 1)
            time.sleep(backoff)
        except Exception as e:
            if attempt == MAX_RETRIES:
                print(f"    ⚠ API erreur ({url.split('/')[2]}): {e}")
                return None
            time.sleep(1.0 * (attempt + 1))
    return None


def _find_matching_barcodes(name_fr: str) -> list[str]:
    """Cherche des produits sur OFF dont le nom contient reellement les mots
    significatifs de name_fr (filtre client-side, l'API de recherche OFF est
    trop permissive pour etre fiable seule)."""
    data = _get_with_retries(SEARCH_URL, {
        "search_terms": name_fr,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 15,
        "fields": "code,product_name,product_name_fr",
    })
    time.sleep(DELAY)
    if not data:
        return []

    query_words = _significant_words(name_fr)
    if not query_words:
        return []

    barcodes = []
    for p in data.get("products", []):
        code = p.get("code")
        if not code:
            continue
        label = p.get("product_name_fr") or p.get("product_name") or ""
        label_words = _significant_words(label)
        # Exige que TOUS les mots significatifs de la recherche soient
        # presents dans le nom du produit (pas juste un mot en commun,
        # sinon "riz" matche "salade de riz aux legumes").
        if query_words <= label_words:
            barcodes.append(code)
        if len(barcodes) >= MAX_BARCODES:
            break
    return barcodes


def _prices_for_barcode(code: str, currency: str = "EUR") -> list[float]:
    data = _get_with_retries(PRICES_API_BASE + "/prices", {
        "product_code": code,
        "currency": currency,
        "price__gt": 0,
        "size": 30,
    })
    time.sleep(DELAY)
    if not data:
        return []
    items = data.get("items", [])
    return [float(i["price"]) for i in items if i.get("price") and float(i["price"]) > 0]


def _search_prices(name_fr: str) -> list[float]:
    """Retourne une liste de prix reels (en EUR) pour ce nom d'ingredient,
    en passant par une recherche produit (nom) puis un lookup de prix
    (code-barres) — voir docstring du module."""
    barcodes = _find_matching_barcodes(name_fr)
    if not barcodes:
        return []
    prices: list[float] = []
    for code in barcodes:
        prices.extend(_prices_for_barcode(code))
    return prices


def _median(values: list[float]) -> float:
    return statistics.median(values)


def _update_catalog(catalog: dict, keys: list[str] | None, dry_run: bool) -> int:
    today = str(date.today())
    updated = 0

    target_keys = keys if keys else list(catalog.keys())
    # Déduplique les entrées ayant la même name_fr (évite double requête)
    seen_names: dict[str, float | None] = {}

    for key in target_keys:
        entry = catalog.get(key)
        if not entry:
            print(f"  ✗ Clé inconnue : {key}")
            continue

        name_fr  = entry.get("name_fr", key)
        packages = entry.get("packages", [])
        if not packages:
            continue

        # Si même name_fr déjà traitée, réutilise le résultat
        if name_fr in seen_names:
            new_price = seen_names[name_fr]
        else:
            print(f"  🔍 {name_fr}...", end=" ", flush=True)
            raw_prices = _search_prices(name_fr)
            time.sleep(DELAY)

            if not raw_prices:
                print("— aucun résultat")
                seen_names[name_fr] = None
                continue

            new_price = round(_median(raw_prices), 2)
            seen_names[name_fr] = new_price

        if new_price is None:
            continue

        # Compare au prix du plus petit paquet
        ref_pkg  = min(packages, key=lambda p: p["price"])
        old_price = ref_pkg["price"]

        if old_price == 0:
            ecart_pct = 1.0
        else:
            ecart_pct = abs(new_price - old_price) / old_price

        if ecart_pct >= THRESHOLD or (keys and key in keys):
            if dry_run:
                print(f"→ {old_price:.2f}€  →  {new_price:.2f}€  (Δ {ecart_pct*100:.0f}%) [DRY RUN]")
            else:
                ref_pkg["price"] = new_price
                entry["last_updated"] = today
                updated += 1
                print(f"✓ {old_price:.2f}€ → {new_price:.2f}€  (Δ {ecart_pct*100:.0f}%)")
        else:
            print(f"≈ stable {old_price:.2f}€  (Δ {ecart_pct*100:.0f}% < seuil)")

    return updated


def main() -> None:
    parser = argparse.ArgumentParser(description="Mise à jour des prix du catalogue ALIM")
    parser.add_argument("--dry-run", action="store_true", help="Affiche les changements sans écrire")
    parser.add_argument("--key", nargs="+", metavar="KEY", help="Clés spécifiques à mettre à jour")
    args = parser.parse_args()

    catalog: dict = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    print(f"📦 Catalogue : {len(catalog)} ingrédients")
    print(f"🌐 Source : Open Food Facts Open Prices")
    if args.dry_run:
        print("⚠  Mode DRY RUN — aucune écriture\n")

    n = _update_catalog(catalog, keys=args.key, dry_run=args.dry_run)

    if not args.dry_run and n > 0:
        CATALOG_PATH.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"\n✅ {n} prix mis à jour → {CATALOG_PATH}")
    elif args.dry_run:
        print(f"\nℹ  {n} mises à jour détectées (non appliquées)")
    else:
        print("\nℹ  Aucun prix modifié (tous stables ou sans données)")


if __name__ == "__main__":
    main()
