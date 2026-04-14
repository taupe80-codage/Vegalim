"""
engine/synthesizer.py
Synthèse d'une recette optimale depuis un cluster de variantes.

Backends LLM (par ordre de priorité) :
  1. Groq API  (llama-3.3-70b-versatile — free tier ~500 req/jour, ~30k tokens/min)
  2. Ollama    (local, mistral ou llama3 — zéro coût si la machine tourne)
  3. Mode stub (renvoie la meilleure variante brute — aucun LLM)

Chaque synthèse = 1 appel API pour N variantes → économique.
"""

from __future__ import annotations
import sys as _sys
import os as _os
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
import re
import json
import time
import logging
import os
from typing import Optional

from config.schema import RecipeCDC, IngredientEntry, TimingEntry, NutritionEntry

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CLIENTS LLM
# ═══════════════════════════════════════════════════════════════════════════════

class GroqClient:
    """Wrapper minimal pour l'API Groq (openai-compatible)."""

    BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
    DEFAULT_MODEL = "llama-3.3-70b-versatile"   # free tier Groq

    def __init__(self, api_key: str, model: str | None = None):
        self.api_key = api_key
        self.model   = model or self.DEFAULT_MODEL
        self._last_call = 0.0
        self._min_interval = 2.0   # 30 req/min free tier → ~2s entre appels

    def chat(self, system: str, user: str, max_tokens: int = 3000, temperature: float = 0.3) -> str:
        import requests

        # Rate limiting doux
        elapsed = time.time() - self._last_call
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)

        payload = {
            "model":       self.model,
            "max_tokens":  max_tokens,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type":  "application/json",
        }

        for attempt in range(4):
            try:
                r = requests.post(self.BASE_URL, json=payload, headers=headers, timeout=60)
                self._last_call = time.time()

                if r.status_code == 429:
                    wait = 30 * (attempt + 1)
                    log.warning(f"Groq rate limit — pause {wait}s")
                    time.sleep(wait)
                    continue

                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]

            except Exception as e:
                if attempt < 3:
                    time.sleep(2 ** attempt * 3)
                else:
                    raise RuntimeError(f"Groq API échec: {e}")
        return ""


class OllamaClient:
    """Wrapper pour Ollama local (http://localhost:11434)."""

    def __init__(self, model: str = "mistral", base_url: str = "http://localhost:11434"):
        self.model    = model
        self.base_url = base_url.rstrip("/")

    def chat(self, system: str, user: str, max_tokens: int = 3000, temperature: float = 0.3) -> str:
        import requests

        payload = {
            "model":  self.model,
            "stream": False,
            "options": {"num_predict": max_tokens, "temperature": temperature},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
        }
        try:
            r = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=120)
            r.raise_for_status()
            return r.json()["message"]["content"]
        except Exception as e:
            raise RuntimeError(f"Ollama échec: {e}")

    def is_available(self) -> bool:
        import requests
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False


def build_llm_client(
    groq_api_key: str | None = None,
    ollama_model: str = "mistral",
    force_backend: str | None = None,   # "groq" | "ollama" | "stub"
) -> tuple[object | None, str]:
    """
    Sélectionne le meilleur backend disponible.
    Retourne (client, backend_name).
    """
    groq_key = groq_api_key or os.environ.get("GROQ_API_KEY", "")

    if force_backend == "stub" or (not force_backend and not groq_key):
        log.info("Backend LLM : stub (pas de clé Groq, pas d'Ollama requis)")
        return None, "stub"

    if force_backend == "groq" or (groq_key and force_backend != "ollama"):
        log.info(f"Backend LLM : Groq ({GroqClient.DEFAULT_MODEL})")
        return GroqClient(api_key=groq_key), "groq"

    # Fallback Ollama
    ollama = OllamaClient(model=ollama_model)
    if ollama.is_available():
        log.info(f"Backend LLM : Ollama ({ollama_model})")
        return ollama, "ollama"

    log.warning("Aucun backend LLM disponible — mode stub")
    return None, "stub"


# ═══════════════════════════════════════════════════════════════════════════════
# CONSTRUCTION DU PROMPT
# ═══════════════════════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """Tu es chef cuisinier professionnel spécialisé en cuisine végétarienne internationale,
nutritionniste et expert en rédaction de recettes techniques.
Tu réponds UNIQUEMENT en JSON valide, sans markdown, sans commentaire, sans texte avant ou après le JSON."""

def _build_synthesis_prompt(variants: list[RecipeCDC]) -> str:
    """
    Construit le prompt de synthèse pour un cluster de variantes.
    On sérialise chaque variante de façon compacte pour économiser les tokens.
    """
    compact_variants = []
    for i, r in enumerate(variants):
        compact_variants.append({
            "source":      r._source,
            "title":       r.titles.get("en") or r.titles.get("fr"),
            "cuisine":     r.origin.get("cuisine", ""),
            "servings":    r.servings,
            "cook_min":    r.timing.cook_min,
            "ingredients": [
                {"name": c.ingredient.replace("_"," "), "qty": c.quantity, "unit": c.unit}
                for c in r.composition[:14]
            ],
            "instructions": r.instructions[:6],
            "dish_type":   r.dish_type,
        })

    return f"""Voici {len(variants)} variantes de la même recette issues de sources différentes.
Synthétise-les en une recette OPTIMALE en français, en choisissant les meilleures instructions,
quantités et techniques de chaque variante.

Variantes :
{json.dumps(compact_variants, ensure_ascii=False, indent=2)}

Réponds UNIQUEMENT avec ce JSON (aucun texte avant/après) :
{{
  "title_fr":    "Nom de la recette en français",
  "title_en":    "Recipe name in English",
  "description": "Description courte (2 phrases max)",
  "servings":    4,
  "cook_min":    0,
  "prep_min":    0,
  "difficulty":  "easy|medium|hard|expert",
  "dish_type":   "main|soup|salad|curry|...",
  "cuisine":     "indian|italian|...",
  "ingredients": [
    {{"name": "ingredient_canonique", "quantity": 200, "unit": "g", "role": "base|aromatic|fat|..."}}
  ],
  "instructions": [
    "Étape 1 avec durée précise et indicateur sensoriel (80-200 caractères)",
    "Étape 2...",
    "..."
  ],
  "equipment": ["poêle","spatule"],
  "notes": "Astuces ou variations éventuelles"
}}

RÈGLES INSTRUCTIONS :
- 5 à 7 étapes, chaque étape entre 80 et 200 caractères
- Durées précises : 'cuire 8 min à feu moyen-vif'
- Températures systématiques pour four/casserole
- Indicateurs sensoriels : coloration, texture, consistance, son
- Verbes techniques : saisir, blanchir, nacrer, émulsionner, réduire, ciseler..."""


def _build_rewrite_prompt(recipe: RecipeCDC) -> str:
    """Prompt de réécriture des instructions seules (mode Phase 2)."""
    return f"""Réécris uniquement les instructions de cette recette en français.
Ne modifie PAS les ingrédients.

Recette : {recipe.titles.get('fr', recipe.titles.get('en', ''))}
Ingrédients : {', '.join(c.ingredient.replace('_',' ') for c in recipe.composition[:12])}
Instructions actuelles :
{json.dumps(recipe.instructions, ensure_ascii=False)}

Réponds UNIQUEMENT avec :
{{"instructions": ["étape 1", "étape 2", ...]}}

RÈGLES : 5-7 étapes, durées précises, températures, indicateurs sensoriels, verbes techniques."""


# ═══════════════════════════════════════════════════════════════════════════════
# PARSING DE LA RÉPONSE LLM
# ═══════════════════════════════════════════════════════════════════════════════

def _extract_json(text: str) -> dict:
    """Extrait le premier objet JSON valide d'une chaîne de texte."""
    text = text.strip()
    # Retire les balises markdown éventuelles
    text = re.sub(r"```json|```", "", text).strip()

    # Chercher le premier { ... } ou [ ... ]
    for pat in [r"\{.*\}", r"\[.*\]"]:
        m = re.search(pat, text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    raise ValueError(f"Aucun JSON valide trouvé dans la réponse LLM:\n{text[:300]}")


def _llm_to_recipe(llm_data: dict, cluster_id: str, variants: list[RecipeCDC]) -> RecipeCDC:
    """Convertit la réponse JSON du LLM en RecipeCDC."""
    from engine.parser import _make_id, _canonicalize_ingredient
    from engine.validator import validate_recipe   # import tardif pour éviter circulaire

    title_fr = llm_data.get("title_fr", variants[0].titles.get("fr", ""))
    title_en = llm_data.get("title_en", variants[0].titles.get("en", ""))
    title    = title_fr or title_en

    recipe_id = _make_id(title, "synthesized", cluster_id)

    # Composition
    composition = []
    for item in llm_data.get("ingredients", []):
        name  = _canonicalize_ingredient(str(item.get("name", "")))
        qty   = item.get("quantity")
        unit  = str(item.get("unit", ""))
        role  = str(item.get("role", ""))
        if not name:
            continue
        composition.append(IngredientEntry(
            ingredient=name,
            quantity=float(qty) if qty is not None else None,
            unit=unit,
            meta={"role": role, "form": "", "state": "raw", "preparation": ""},
        ))

    cook_min = int(llm_data.get("cook_min", 0))
    prep_min = int(llm_data.get("prep_min", 0))

    recipe = RecipeCDC(
        id=recipe_id,
        titles={"original": title, "fr": title_fr, "en": title_en},
        description=str(llm_data.get("description", "")),
        origin={
            "cuisine": str(llm_data.get("cuisine", variants[0].origin.get("cuisine", ""))),
            "country": variants[0].origin.get("country", ""),
            "region":  "",
            "city":    "",
        },
        servings=int(llm_data.get("servings", 4)),
        timing=TimingEntry(
            prep_active_min=prep_min,
            prep_passive_min=0,
            cook_min=cook_min,
            total_min=prep_min + cook_min,
        ),
        composition=composition,
        instructions=llm_data.get("instructions", []),
        tags={"diet": [], "allergens": [], "technique": [], "process": []},
        diet_flags={"vegan": False, "vegetarian": False, "gluten_free": False,
                    "lactose_free": False, "nut_free": False},
        equipment=llm_data.get("equipment", []),
        difficulty_level=str(llm_data.get("difficulty", "medium")),
        dish_type=str(llm_data.get("dish_type", variants[0].dish_type)),
        nutrition=NutritionEntry(),
        _source="synthesized",
        _cluster_id=cluster_id,
        _quality_score=0.0,
        _flags=[],
    )

    if llm_data.get("notes"):
        recipe._corrections_log.append(f"[LLM note] {llm_data['notes']}")

    return recipe


# ═══════════════════════════════════════════════════════════════════════════════
# SYNTHESIZER
# ═══════════════════════════════════════════════════════════════════════════════

class RecipeSynthesizer:
    """
    Synthétise la meilleure recette depuis un cluster de variantes.

    Usage :
        synth = RecipeSynthesizer(groq_api_key="gsk_...")
        best  = synth.synthesize(variants, cluster_id="cluster_0001")
    """

    def __init__(
        self,
        groq_api_key: str | None = None,
        ollama_model: str = "mistral",
        force_backend: str | None = None,
    ):
        self.client, self.backend = build_llm_client(
            groq_api_key=groq_api_key,
            ollama_model=ollama_model,
            force_backend=force_backend,
        )

    def synthesize(
        self,
        variants: list[RecipeCDC],
        cluster_id: str = "",
    ) -> RecipeCDC:
        """
        Synthétise N variantes en 1 recette optimale.
        En mode stub : retourne simplement la variante la plus complète.
        """
        if not variants:
            raise ValueError("synthesize() appelé avec une liste vide")

        # Trier par complétude
        best_variant = max(
            variants,
            key=lambda r: len(r.composition) * 2 + len(r.instructions)
        )

        if self.backend == "stub" or len(variants) == 1:
            best_variant._cluster_id = cluster_id
            best_variant._source     = best_variant._source or "stub"
            log.debug(f"Stub synthesis pour {cluster_id} — {best_variant.titles.get('fr','?')}")
            return best_variant

        prompt = _build_synthesis_prompt(variants)

        try:
            raw_response = self.client.chat(
                system=SYSTEM_PROMPT,
                user=prompt,
                max_tokens=2500,
                temperature=0.25,
            )
            llm_data = _extract_json(raw_response)
            recipe   = _llm_to_recipe(llm_data, cluster_id, variants)
            recipe._quality_score = 0.5   # sera affiné par le validator
            log.info(f"[{self.backend}] Synthèse OK — {recipe.titles.get('fr','?')} ({len(variants)} variantes)")
            return recipe

        except Exception as e:
            log.warning(f"Synthèse LLM échouée pour {cluster_id}: {e} — fallback sur meilleure variante")
            best_variant._cluster_id = cluster_id
            best_variant._flags.append(f"synthesis_failed:{type(e).__name__}")
            return best_variant

    def rewrite_instructions(self, recipe: RecipeCDC) -> RecipeCDC:
        """
        Phase 2 seule : réécrit uniquement les instructions d'une recette existante.
        Ne modifie pas la composition.
        """
        if self.backend == "stub":
            return recipe

        try:
            prompt = _build_rewrite_prompt(recipe)
            raw    = self.client.chat(SYSTEM_PROMPT, prompt, max_tokens=1000, temperature=0.2)
            data   = _extract_json(raw)
            if instrs := data.get("instructions"):
                if len(instrs) >= 3:
                    recipe.instructions = instrs
                    recipe._corrections_log.append("[P2] instructions réécrites par LLM")
        except Exception as e:
            log.warning(f"rewrite_instructions échoué pour {recipe.id}: {e}")

        return recipe

    def synthesize_batch(
        self,
        clusters: dict[str, list[RecipeCDC]],
        max_clusters: int = 0,
        delay_between_calls: float = 2.0,
    ) -> list[RecipeCDC]:
        """
        Synthétise tous les clusters.
        max_clusters=0 → tous les clusters.
        """
        items = list(clusters.items())
        if max_clusters:
            items = items[:max_clusters]

        results: list[RecipeCDC] = []
        for i, (cluster_id, variants) in enumerate(items):
            log.info(f"Synthèse [{i+1}/{len(items)}] {cluster_id} ({len(variants)} variantes)")
            recipe = self.synthesize(variants, cluster_id=cluster_id)
            results.append(recipe)

            if self.backend != "stub" and i < len(items) - 1:
                time.sleep(delay_between_calls)

        log.info(f"synthesize_batch → {len(results)} recettes synthétisées")
        return results