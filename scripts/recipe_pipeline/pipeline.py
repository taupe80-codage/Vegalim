"""
pipeline.py
═══════════════════════════════════════════════════════════════════════
ALIM — Moteur de Reconstitution Culinaire
Pipeline complet en 7 étapes :

  1. COLLECT   — TheMealDB, Wikibooks, RecipeNLG
  2. PARSE     — normalisation brute → schéma pivot CDC v4
  3. DEDUPE    — suppression quasi-doublons (TF-IDF cosine)
  4. CLUSTER   — regroupement variantes (clustering agglomératif)
  5. SYNTHESIZE— synthèse LLM (Groq/Ollama/stub) par cluster
  6. VALIDATE  — règles métier + corrections automatiques
  7. EXPORT    — CDC v4 JSON + rapport qualité

Usage :
    # Collecte + pipeline complet
    python pipeline.py --sources mealdb wikibooks --output output/recipes.json

    # Depuis un fichier JSON brut existant
    python pipeline.py --from-raw raw_collected.json --output output/recipes.json

    # Juste valider + corriger un fichier CDC existant
    python pipeline.py --from-cdc recipes_v2.json --validate-only --output output/recipes_fixed.json

    # Avec Groq (llama3 gratuit)
    GROQ_API_KEY=gsk_... python pipeline.py --sources mealdb --output output/recipes.json

    # Forcer Ollama local
    python pipeline.py --sources mealdb --llm-backend ollama --llm-model mistral
═══════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations
import json
import sys
import os
import time
import logging
import argparse
from pathlib import Path
from collections import Counter

# ── Encodage stdout (évite UnicodeEncodeError sur terminal cp1252) ───────────
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Logging ─────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Fix chemin Windows (doit etre AVANT tout import interne) ────────────────
_here = Path(__file__).resolve().parent
if str(_here) not in sys.path:
    sys.path.insert(0, str(_here))
os.chdir(str(_here))

# Verification que config est accessible
_config_path = _here / "config" / "schema.py"
if not _config_path.exists():
    print(f"ERREUR : config/schema.py introuvable dans {_here}")
    print(f"Verifiez que les dossiers config/, engine/, sources/ sont bien dans {_here}")
    sys.exit(1)

from config.schema import RecipeCDC
from sources.collector import collect_all
from engine.parser import parse_batch
from engine.clusterer import cluster_recipes, deduplicate
from engine.synthesizer import RecipeSynthesizer
from engine.validator import validate_batch, quality_report


# ═══════════════════════════════════════════════════════════════════════════════
# SÉRIALISATION / DÉSÉRIALISATION CDC v4
# ═══════════════════════════════════════════════════════════════════════════════

def recipe_to_dict(r: RecipeCDC) -> dict:
    from dataclasses import asdict
    d = asdict(r)
    d['timing']    = asdict(r.timing)
    d['nutrition'] = asdict(r.nutrition)
    d['composition'] = [asdict(c) for c in r.composition]
    return d


def dict_to_recipe(d: dict) -> RecipeCDC:
    """Recharge un dict CDC en RecipeCDC (pour --from-cdc)."""
    from config.schema import IngredientEntry, TimingEntry, NutritionEntry
    from dataclasses import fields

    timing    = TimingEntry(**{k: d['timing'][k] for k in ('prep_active_min','prep_passive_min','cook_min','total_min') if k in d.get('timing', {})})
    nutrition = NutritionEntry(**{k: d['nutrition'].get(k) for k in ('kcal','proteines_g','glucides_g','lipides_g','fibres_g')} if d.get('nutrition') else {})

    composition = [
        IngredientEntry(
            ingredient=c.get('ingredient',''),
            quantity=c.get('quantity'),
            unit=c.get('unit',''),
            meta=c.get('meta', {}),
        )
        for c in d.get('composition', [])
    ]

    r = RecipeCDC(
        id            = d.get('id',''),
        titles        = d.get('titles', {}),
        description   = d.get('description',''),
        origin        = d.get('origin', {}),
        servings      = d.get('servings', 4),
        timing        = timing,
        composition   = composition,
        instructions  = d.get('instructions', []),
        tags          = d.get('tags', {}),
        diet_flags    = d.get('diet_flags', {}),
        equipment     = d.get('equipment', []),
        difficulty_level = d.get('difficulty_level','medium'),
        dish_type     = d.get('dish_type',''),
        nutrition     = nutrition,
        _source       = d.get('_source',''),
        _cluster_id   = d.get('_cluster_id',''),
        _quality_score= d.get('_quality_score', 0.0),
        _flags        = d.get('_flags', []),
        _corrections_log = d.get('_corrections_log', []),
    )
    return r


def load_cdc_json(path: str) -> list[RecipeCDC]:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    recipes_raw = data.get('recipes', data) if isinstance(data, dict) else data
    return [dict_to_recipe(d) for d in recipes_raw]


def save_cdc_json(recipes: list[RecipeCDC], path: str, metadata: dict | None = None):
    output = {
        "metadata": metadata or {
            "version": "CDC-v4",
            "generator": "ALIM-RecipeEngine",
            "count": len(recipes),
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        },
        "recipes": [recipe_to_dict(r) for r in recipes],
    }
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    log.info(f"💾  {len(recipes)} recettes sauvegardées → {path}")


# ═══════════════════════════════════════════════════════════════════════════════
# ÉTAPES DU PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════

def step_collect(args) -> list[dict]:
    """Étape 1 — Collecte depuis les sources activées."""
    log.info("═══ ÉTAPE 1 — COLLECTE ═══")

    if args.from_raw:
        log.info(f"Chargement depuis fichier brut : {args.from_raw}")
        with open(args.from_raw, encoding='utf-8') as f:
            raw = json.load(f)
        return raw if isinstance(raw, list) else raw.get('raw', [])

    sources = args.sources or ['mealdb']
    raw = collect_all(
        sources=sources,
        wikibooks_max=args.wikibooks_max,
        recipenlg_path=args.recipenlg_path,
    )

    if args.save_raw:
        with open(args.save_raw, 'w', encoding='utf-8') as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)
        log.info(f"Brut sauvegardé → {args.save_raw}")

    return raw


def step_parse(raw: list[dict]) -> list[RecipeCDC]:
    """Étape 2 — Parsing & normalisation CDC v4."""
    log.info("═══ ÉTAPE 2 — PARSING ═══")
    recipes = parse_batch(raw)
    log.info(f"  → {len(recipes)} recettes normalisées")
    return recipes


def step_dedupe(recipes: list[RecipeCDC], threshold: float = 0.92) -> list[RecipeCDC]:
    """Étape 3 — Déduplication quasi-doublons."""
    log.info("═══ ÉTAPE 3 — DÉDUPLICATION ═══")
    before = len(recipes)
    recipes = deduplicate(recipes, similarity_threshold=threshold)
    log.info(f"  → {len(recipes)} recettes (−{before - len(recipes)} doublons)")
    return recipes


def step_cluster(
    recipes: list[RecipeCDC],
    threshold: float = 0.65,
    max_variants: int = 5,
) -> tuple[dict, dict]:
    """Étape 4 — Clustering des variantes."""
    log.info("═══ ÉTAPE 4 — CLUSTERING ═══")
    clusters, stats = cluster_recipes(
        recipes,
        similarity_threshold=threshold,
        max_variants_per_cluster=max_variants,
    )
    log.info(f"  → {stats['n_clusters']} clusters ({stats['multi_variant_clusters']} multi-variantes)")
    return clusters, stats


def step_synthesize(
    clusters: dict,
    groq_api_key: str | None = None,
    llm_backend: str | None = None,
    llm_model: str = "mistral",
    max_clusters: int = 0,
) -> list[RecipeCDC]:
    """Étape 5 — Synthèse LLM par cluster."""
    log.info(f"═══ ÉTAPE 5 — SYNTHÈSE (backend={llm_backend or 'auto'}) ═══")

    synthesizer = RecipeSynthesizer(
        groq_api_key=groq_api_key,
        ollama_model=llm_model,
        force_backend=llm_backend,
    )

    recipes = synthesizer.synthesize_batch(
        clusters,
        max_clusters=max_clusters,
        delay_between_calls=2.5,
    )
    log.info(f"  → {len(recipes)} recettes synthétisées")
    return recipes


def step_validate(
    recipes: list[RecipeCDC],
    min_score: float = 0.40,
) -> tuple[list[RecipeCDC], list, dict]:
    """Étape 6 — Validation métier + corrections auto."""
    log.info("═══ ÉTAPE 6 — VALIDATION ═══")

    valid, reports = validate_batch(recipes, auto_fix=True, min_score=min_score)
    report_agg = quality_report(reports)

    log.info(f"  → {len(valid)}/{len(recipes)} recettes retenues (score ≥ {min_score})")
    log.info(f"  Score moyen : {report_agg['avg_score']:.3f}")
    log.info(f"  Score ≥0.8  : {report_agg['score_ge_08']}")
    log.info(f"  Score 0.6–0.8: {report_agg['score_06_08']}")
    log.info(f"  Score <0.6  : {report_agg['score_lt_06']}")

    if report_agg['top_warnings']:
        log.info("  Top warnings :")
        for warn, cnt in list(report_agg['top_warnings'].items())[:5]:
            log.info(f"    {warn:<45} {cnt}")

    return valid, reports, report_agg


def step_export(
    recipes: list[RecipeCDC],
    output_path: str,
    report_agg: dict,
    pipeline_meta: dict,
) -> None:
    """Étape 7 — Export JSON CDC v4 + rapport."""
    log.info("═══ ÉTAPE 7 — EXPORT ═══")

    metadata = {
        "version":       "CDC-v4",
        "generator":     "ALIM-RecipeEngine",
        "count":         len(recipes),
        "generated_at":  time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pipeline":      pipeline_meta,
        "quality":       report_agg,
    }
    save_cdc_json(recipes, output_path, metadata)

    # Rapport JSON séparé
    report_path = output_path.replace('.json', '_report.json')
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump({"metadata": metadata, "quality_report": report_agg}, f, ensure_ascii=False, indent=2)
    log.info(f"  Rapport → {report_path}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="ALIM — Moteur de Reconstitution Culinaire",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Sources
    src = p.add_argument_group("Sources")
    src.add_argument("--sources",         nargs="+", choices=["mealdb","wikibooks","recipenlg"],
                     default=["mealdb"],  help="Sources à collecter (défaut: mealdb)")
    src.add_argument("--wikibooks-max",   type=int, default=100, help="Nb max recettes Wikibooks")
    src.add_argument("--recipenlg-path",  type=str, default=None, help="Chemin fichier parquet RecipeNLG")
    src.add_argument("--from-raw",        type=str, default=None, help="Charger depuis un JSON brut existant")
    src.add_argument("--from-cdc",        type=str, default=None, help="Charger depuis un fichier CDC v4 existant")
    src.add_argument("--save-raw",        type=str, default=None, help="Sauvegarder les données brutes collectées")

    # Pipeline
    pipe = p.add_argument_group("Pipeline")
    pipe.add_argument("--output",          required=True, help="Fichier de sortie CDC v4 JSON")
    pipe.add_argument("--validate-only",   action="store_true", help="Sauter collecte/synthèse, juste valider")
    pipe.add_argument("--skip-cluster",    action="store_true", help="Passer directement à la synthèse sans cluster")
    pipe.add_argument("--max-recipes",     type=int, default=0,  help="Limiter le nb de recettes (debug)")
    pipe.add_argument("--dedup-threshold", type=float, default=0.92, help="Seuil de déduplication (défaut: 0.92)")
    pipe.add_argument("--cluster-threshold", type=float, default=0.65, help="Seuil de clustering (défaut: 0.65)")
    pipe.add_argument("--max-variants",    type=int, default=5, help="Variantes max par cluster (défaut: 5)")
    pipe.add_argument("--min-score",       type=float, default=0.40, help="Score qualité minimum (défaut: 0.40)")
    pipe.add_argument("--max-clusters",    type=int, default=0, help="Nb max de clusters à synthétiser (debug)")

    # LLM
    llm = p.add_argument_group("LLM")
    llm.add_argument("--llm-backend",  choices=["groq","ollama","stub"], default=None,
                     help="Forcer un backend LLM (défaut: auto-détection)")
    llm.add_argument("--llm-model",    type=str, default="mistral", help="Modèle Ollama (défaut: mistral)")
    llm.add_argument("--groq-api-key", type=str, default=None, help="Clé Groq API (ou GROQ_API_KEY env)")

    return p


def main():
    parser = build_parser()
    args   = parser.parse_args()

    start = time.time()
    groq_key = args.groq_api_key or os.environ.get("GROQ_API_KEY", "")

    log.info("╔══════════════════════════════════════════════╗")
    log.info("║  ALIM — Moteur de Reconstitution Culinaire  ║")
    log.info("╚══════════════════════════════════════════════╝")

    # ── Chargement depuis CDC existant (validate-only) ────────────────────────
    if args.from_cdc or args.validate_only:
        source_path = args.from_cdc or args.output
        log.info(f"Chargement CDC depuis : {source_path}")
        recipes = load_cdc_json(source_path)
        if args.max_recipes:
            recipes = recipes[:args.max_recipes]
        valid, reports, report_agg = step_validate(recipes, min_score=args.min_score)
        step_export(valid, args.output, report_agg, pipeline_meta={
            "mode": "validate_only", "input": source_path
        })
        _print_final_summary(valid, report_agg, start)
        return

    # ── Pipeline complet ──────────────────────────────────────────────────────

    # 1. Collecte
    raw = step_collect(args)
    if not raw:
        log.error("Aucune donnée collectée. Vérifier les sources et la connectivité.")
        sys.exit(1)
    if args.max_recipes:
        raw = raw[:args.max_recipes]

    # 2. Parsing
    recipes = step_parse(raw)
    if not recipes:
        log.error("Aucune recette parsée valide.")
        sys.exit(1)

    # 3. Déduplication
    recipes = step_dedupe(recipes, threshold=args.dedup_threshold)

    # 4. Clustering
    if args.skip_cluster:
        clusters = {f"single_{i:04d}": [r] for i, r in enumerate(recipes)}
        cluster_stats = {"n_clusters": len(clusters), "multi_variant_clusters": 0}
    else:
        clusters, cluster_stats = step_cluster(
            recipes,
            threshold=args.cluster_threshold,
            max_variants=args.max_variants,
        )

    # 5. Synthèse
    synthesized = step_synthesize(
        clusters,
        groq_api_key=groq_key or None,
        llm_backend=args.llm_backend,
        llm_model=args.llm_model,
        max_clusters=args.max_clusters,
    )

    # 6. Validation
    valid, reports, report_agg = step_validate(synthesized, min_score=args.min_score)

    # 7. Export
    pipeline_meta = {
        "sources":          args.sources,
        "raw_collected":    len(raw),
        "parsed":           len(recipes),
        "clusters":         cluster_stats.get("n_clusters", 0),
        "synthesized":      len(synthesized),
        "validated":        len(valid),
        "llm_backend":      args.llm_backend or "auto",
        "cluster_threshold": args.cluster_threshold,
        "min_score":        args.min_score,
    }
    step_export(valid, args.output, report_agg, pipeline_meta)

    _print_final_summary(valid, report_agg, start)


def _print_final_summary(recipes: list[RecipeCDC], report: dict, start: float):
    elapsed = time.time() - start
    by_source = Counter(r._source for r in recipes)

    print(f"\n{'═'*55}")
    print(f"  ✅  {len(recipes)} recettes exportées")
    print(f"  ⏱   {elapsed:.0f}s ({elapsed/60:.1f} min)")
    print(f"  📊  Score moyen : {report['avg_score']:.3f}")
    print(f"  🏅  ≥0.8 : {report['score_ge_08']}   0.6–0.8 : {report['score_06_08']}   <0.6 : {report['score_lt_06']}")
    if by_source:
        print(f"  🔎  Sources : " + " · ".join(f"{s}:{n}" for s,n in by_source.most_common()))
    if report.get('top_auto_fixes'):
        print(f"  🔧  Top corrections auto :")
        for fix, cnt in list(report['top_auto_fixes'].items())[:5]:
            print(f"       {fix:<40} {cnt}")
    print(f"{'═'*55}\n")


if __name__ == "__main__":
    main()