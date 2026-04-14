"""
engine/validator.py
Validation métier complète d'une RecipeCDC.

Responsabilités :
  - Cohérence ingrédients ↔ instructions
  - Logique culinaire (séquences interdites, températures, timing)
  - Quantités réalistes (clamp culinaire)
  - Tags / diet_flags cohérents avec la composition
  - Allergènes EU déclarés
  - Calcul d'un quality_score [0.0–1.0]
  - Application des corrections automatiques (sans LLM)

Peut être utilisé seul (python -m engine.validator) ou importé dans le pipeline.
"""

from __future__ import annotations
import sys as _sys
import os as _os
from pathlib import Path as _Path
_sys.path.insert(0, str(_Path(__file__).resolve().parent.parent))
import re
import logging
from dataclasses import dataclass, field
from typing import Optional

from config.schema import (
    RecipeCDC, IngredientEntry,
    ALLERGEN_MAP, SPICE_CLAMP_G,
)

log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES MÉTIER
# ═══════════════════════════════════════════════════════════════════════════════

NON_VEGAN = {
    "milk","cream","butter","cheese","yogurt","parmesan","mozzarella","ricotta",
    "mascarpone","feta","halloumi","ghee","cheddar","goat_cheese","cream_cheese",
    "sour_cream","condensed_milk","egg","honey","fish","salmon","tuna","cod",
    "sardine","anchovy","shrimp","prawn","lobster","crab","gelatin","lard",
    "fish_sauce","worcestershire_sauce",
}
NON_VEGETARIAN = NON_VEGAN | {
    "beef","pork","lamb","veal","chicken","turkey","duck","rabbit","venison",
    "bacon","ham","prosciutto","chorizo","salami","pepperoni","meat","sausage",
}
GLUTEN_ING = {
    "flour","wheat","rye","barley","oat","spelt","semolina","bread","pasta",
    "couscous","bulgur","seitan","breadcrumbs","pita","soy_sauce",
}
LACTOSE_ING = {
    "milk","cream","butter","cheese","yogurt","parmesan","mozzarella","ricotta",
    "mascarpone","feta","halloumi","ghee","cheddar","goat_cheese","cream_cheese",
    "sour_cream","condensed_milk",
}
NUT_ING = {
    "walnut","hazelnut","almond","cashew","pistachio","pecan","macadamia",
    "pine_nut","peanut","peanut_butter","brazil_nut","chestnut",
}

# Indicateurs sensoriels dans les instructions
VISUAL_MARKERS = [
    "doré","fondant","croustillant","jusqu'à","texture","couleur","consistance",
    "napper","caramélisé","translucide","ébullition","frémiss","absorption",
    "brunir","homogène","brillant","sirupeux","réduit","concentré","al dente",
    "coloration","réduction","évaporation","nacré","saisie","attache","crépite",
    "légèrement","onctueux","lié","soufflé","séparés","se détache","fond",
    "golden","browned","crispy","tender","translucent","simmering","absorbed",
]

# Patterns boilerplate à détecter
BOILERPLATE_PATS = [
    re.compile(r"le bouillon doit être riche et corsé", re.I),
    re.compile(r"assembler les ingrédients dans un saladier.*vinaigrette", re.I | re.S),
    re.compile(r"goûter.{0,20}rectifier.{0,30}servir chaud et bien présenté", re.I),
    re.compile(r"maintenir le feu très vif tout au long", re.I),
]

# Séquences logiquement impossibles (index_1 > index_2 dans la liste)
IMPOSSIBLE_SEQUENCES = [
    ("décongel",   "cuir"),        # décongeler APRÈS cuire
    ("décongel",   "servir"),
    ("surgel",     "servir"),
    ("surgel",     "cuir"),
]

# Températures anormalement basses pour cuisson longue
LOW_TEMP_PAT    = re.compile(r"\b([4-7]\d)\s*°C\b")
# Temps très courts pour techniques longues
BRAISE_SHORT_PAT = re.compile(r"(brais|mijoter|confit|pocher)[^.]{0,30}(\d+)\s*min", re.I)

# Ingrédients fréquents dans les instructions mais souvent oubliés en composition
COMMON_INGREDIENTS_TO_CHECK = [
    "garlic","onion","oil","olive_oil","salt","pepper","water","broth",
    "lemon","lemon_juice","butter","cream","cheese","egg","flour","sugar",
    "cumin","turmeric","paprika","ginger","cilantro","parsley","basil","thyme",
    "tomato","carrot","spinach","mushroom","bell_pepper","zucchini",
    "soy_sauce","tamari","miso","tahini","coconut_milk","yogurt",
    "tofu","chickpeas","lentils","rice","pasta","quinoa",
]

# ═══════════════════════════════════════════════════════════════════════════════
# RAPPORT DE VALIDATION
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class ValidationReport:
    recipe_id:   str
    recipe_title: str
    errors:   list[str] = field(default_factory=list)    # bloquants
    warnings: list[str] = field(default_factory=list)    # non-bloquants
    fixes:    list[str] = field(default_factory=list)    # corrections auto appliquées
    quality_score: float = 0.0

    def is_valid(self) -> bool:
        return len(self.errors) == 0

    def summary(self) -> str:
        e = len(self.errors)
        w = len(self.warnings)
        f = len(self.fixes)
        return (
            f"[{self.recipe_id[:30]}] "
            f"score={self.quality_score:.2f} "
            f"errors={e} warnings={w} fixes={f}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# VALIDATEUR PRINCIPAL
# ═══════════════════════════════════════════════════════════════════════════════

class RecipeValidator:
    """
    Valide et corrige automatiquement une RecipeCDC.
    Les corrections "sûres" (clamp, tags, allergènes) sont appliquées en place.
    Les problèmes nécessitant un LLM sont reportés comme warnings/errors.
    """

    def validate(self, recipe: RecipeCDC, auto_fix: bool = True) -> ValidationReport:
        report = ValidationReport(
            recipe_id=recipe.id,
            recipe_title=recipe.titles.get("fr") or recipe.titles.get("en") or "",
        )

        self._check_structure(recipe, report)
        self._check_instructions(recipe, report)
        self._check_ingredients_coherence(recipe, report)
        if auto_fix:
            self._fix_quantities(recipe, report)
            self._fix_diet_tags(recipe, report)
            self._fix_allergens(recipe, report)
        self._check_culinary_logic(recipe, report)
        report.quality_score = self._compute_quality_score(recipe, report)
        recipe._quality_score = report.quality_score

        # Consolider dans _flags
        recipe._flags = report.errors + report.warnings
        recipe._corrections_log.extend(report.fixes)

        return report

    # ── Structure de base ─────────────────────────────────────────────────────

    def _check_structure(self, r: RecipeCDC, rep: ValidationReport):
        if not r.titles.get("fr") and not r.titles.get("en"):
            rep.errors.append("missing_title")
        if not r.composition:
            rep.errors.append("no_ingredients")
        if not r.instructions:
            rep.errors.append("no_instructions")
        if r.servings <= 0:
            rep.warnings.append("invalid_servings")
            if hasattr(r, 'servings'):
                r.servings = 4

    # ── Instructions ─────────────────────────────────────────────────────────

    def _check_instructions(self, r: RecipeCDC, rep: ValidationReport):
        instrs = r.instructions or []
        if not instrs:
            return

        text = " ".join(instrs)
        avg  = sum(len(i) for i in instrs) / len(instrs)

        if len(instrs) < 4:
            rep.warnings.append(f"too_few_steps:{len(instrs)}<4")
        if len(instrs) > 10:
            rep.warnings.append(f"too_many_steps:{len(instrs)}>10")
        if avg < 55:
            rep.warnings.append(f"steps_too_short:avg={avg:.0f}chars")
        if not re.search(r"(°C|feu\s+(vif|doux|moyen|fort))", text, re.I):
            rep.warnings.append("no_temperature_indicator")
        if not re.search(r"\b(min|minute|minutes)\b", text, re.I):
            rep.warnings.append("no_duration_indicator")
        if not any(m in text.lower() for m in VISUAL_MARKERS):
            rep.warnings.append("no_sensory_markers")
        if len(re.findall(r"\b(Faire\b|Mettre\b|Préparer\b)", text)) >= 3:
            rep.warnings.append("vague_verbs")
        if any(p.search(text) for p in BOILERPLATE_PATS):
            rep.warnings.append("boilerplate_detected")

        # Séquences impossibles
        lower = text.lower()
        for word_after, word_before in IMPOSSIBLE_SEQUENCES:
            idx_a = lower.find(word_after)
            idx_b = lower.find(word_before)
            if idx_a != -1 and idx_b != -1 and idx_a > idx_b:
                rep.errors.append(f"impossible_sequence:{word_after}_after_{word_before}")

        # Températures anormalement basses
        if LOW_TEMP_PAT.search(text):
            rep.warnings.append("suspiciously_low_temperature")

        # Temps trop court pour braiser/mijoter
        m = BRAISE_SHORT_PAT.search(text)
        if m:
            minutes = int(m.group(2))
            if minutes < 20:
                rep.warnings.append(f"unrealistic_braise_time:{minutes}min")

    # ── Cohérence ingrédients ↔ instructions ─────────────────────────────────

    def _check_ingredients_coherence(self, r: RecipeCDC, rep: ValidationReport):
        if not r.instructions or not r.composition:
            return

        instr_text = " ".join(r.instructions).lower()
        comp_names = {c.ingredient.lower().replace("_", " ") for c in r.composition}
        comp_names_raw = {c.ingredient.lower() for c in r.composition}

        # Ingrédients listés mais jamais mentionnés dans les instructions
        unused = []
        for name in comp_names_raw:
            readable = name.replace("_", " ")
            if len(readable) > 3 and readable not in instr_text and name not in instr_text:
                unused.append(name)
        if unused:
            rep.warnings.append(f"ingredients_unused_in_instructions:{','.join(unused[:4])}")

        # Ingrédients fréquents présents dans instructions mais absents de la liste
        missing = []
        for ing in COMMON_INGREDIENTS_TO_CHECK:
            readable = ing.replace("_", " ")
            if (readable in instr_text or ing in instr_text) and ing not in comp_names_raw:
                missing.append(ing)
        if missing:
            rep.warnings.append(f"ingredients_missing_from_list:{','.join(missing[:5])}")

        # Quantités manquantes
        missing_qty = [
            c.ingredient for c in r.composition
            if c.quantity is None and c.ingredient not in {"salt","pepper","water","oil"}
        ]
        if len(missing_qty) > 3:
            rep.warnings.append(f"many_missing_quantities:{len(missing_qty)}")
        elif missing_qty:
            rep.warnings.append(f"missing_quantities:{','.join(missing_qty[:4])}")

    # ── Correction automatique — Clamp quantités ──────────────────────────────

    def _fix_quantities(self, r: RecipeCDC, rep: ValidationReport):
        for c in r.composition:
            if c.quantity is None or c.unit not in ("g", "ml", ""):
                continue
            if c.unit == "ml":
                continue   # clamp en g uniquement

            max_g = SPICE_CLAMP_G.get(c.ingredient)
            if max_g and c.unit == "g" and c.quantity > max_g:
                old_qty = c.quantity
                c.quantity = round(max_g * 0.75, 1)
                fix_msg = f"qty_clamped:{c.ingredient} {old_qty}g→{c.quantity}g"
                rep.fixes.append(fix_msg)
                log.debug(fix_msg)

    # ── Correction automatique — Tags & diet_flags ────────────────────────────

    def _fix_diet_tags(self, r: RecipeCDC, rep: ValidationReport):
        ing_set = {c.ingredient for c in r.composition}
        tags_diet = set(r.tags.get("diet", []))
        flags = r.diet_flags or {}

        # Recalculer la réalité
        is_vegetarian = not bool(ing_set & NON_VEGETARIAN)
        is_vegan      = is_vegetarian and not bool(ing_set & NON_VEGAN)
        is_gf         = not bool(ing_set & GLUTEN_ING)
        is_lf         = not bool(ing_set & LACTOSE_ING)
        is_nf         = not bool(ing_set & NUT_ING)

        corrections = []
        if "vegan" in tags_diet and not is_vegan:
            offenders = ing_set & NON_VEGAN
            tags_diet.discard("vegan")
            corrections.append(f"tag_vegan_removed(offenders:{','.join(list(offenders)[:3])})")
        if "vegetarian" in tags_diet and not is_vegetarian:
            offenders = ing_set & NON_VEGETARIAN
            tags_diet.discard("vegetarian")
            corrections.append(f"tag_vegetarian_removed(offenders:{','.join(list(offenders)[:3])})")
        if "gluten_free" in tags_diet and not is_gf:
            offenders = ing_set & GLUTEN_ING
            tags_diet.discard("gluten_free")
            corrections.append(f"tag_gluten_free_removed(offenders:{','.join(list(offenders)[:2])})")

        # Ajouter les tags manquants
        if is_vegan and "vegan" not in tags_diet:
            tags_diet.add("vegan")
            corrections.append("tag_vegan_added")
        if is_vegetarian and "vegetarian" not in tags_diet:
            tags_diet.add("vegetarian")
            corrections.append("tag_vegetarian_added")
        if is_gf and "gluten_free" not in tags_diet:
            tags_diet.add("gluten_free")
            corrections.append("tag_gluten_free_added")

        r.tags["diet"] = sorted(tags_diet)

        # Sync diet_flags
        new_flags = {
            "vegan":        is_vegan,
            "vegetarian":   is_vegetarian,
            "gluten_free":  is_gf,
            "lactose_free": is_lf,
            "nut_free":     is_nf,
        }
        for k, v in new_flags.items():
            if flags.get(k) != v:
                corrections.append(f"flag_{k}_synced→{v}")
        r.diet_flags = new_flags

        rep.fixes.extend(corrections)

    # ── Correction automatique — Allergènes ──────────────────────────────────

    def _fix_allergens(self, r: RecipeCDC, rep: ValidationReport):
        detected = set()
        for c in r.composition:
            if c.ingredient in ALLERGEN_MAP:
                detected.add(ALLERGEN_MAP[c.ingredient])

        declared = set(r.tags.get("allergens", []))
        missing  = detected - declared

        if missing:
            r.tags["allergens"] = sorted(declared | detected)
            rep.fixes.append(f"allergens_added:{','.join(sorted(missing))}")

    # ── Logique culinaire ─────────────────────────────────────────────────────

    def _check_culinary_logic(self, r: RecipeCDC, rep: ValidationReport):
        if not r.timing:
            return

        # Timing total incohérent
        declared_total = r.timing.total_min
        computed_total = r.timing.prep_active_min + r.timing.cook_min
        if declared_total and abs(declared_total - computed_total) > 30:
            rep.warnings.append(
                f"timing_mismatch:declared={declared_total}min computed={computed_total}min"
            )

        # Recette sans aucun temps de cuisson mais avec techniques de cuisson
        if r.timing.cook_min == 0 and r.instructions:
            text = " ".join(r.instructions).lower()
            if re.search(r"\b(cuire|sauté|frire|rôtir|bouillir|griller|poêler|braiser)\b", text):
                rep.warnings.append("cook_time_zero_but_cooking_mentioned")

        # Recettes trop simples
        if len(r.composition) < 3:
            rep.warnings.append(f"very_few_ingredients:{len(r.composition)}")

    # ── Score qualité ─────────────────────────────────────────────────────────

    def _compute_quality_score(self, r: RecipeCDC, rep: ValidationReport) -> float:
        """
        Score [0.0–1.0] pondéré sur plusieurs critères.
        Décompte : erreurs −0.20 chacune, warnings −0.05 chacun.
        """
        score = 1.0

        # Pénalités structurelles
        score -= len(rep.errors)   * 0.20
        score -= len(rep.warnings) * 0.05

        # Bonus complétude
        if len(r.composition) >= 6:   score += 0.05
        if len(r.instructions) >= 5:  score += 0.05
        if r.timing.cook_min > 0:     score += 0.03
        if r.description:             score += 0.02
        if r.nutrition.kcal:          score += 0.02
        if r.origin.get("cuisine"):   score += 0.02

        # Bonus qualité instructions
        text = " ".join(r.instructions)
        if re.search(r"(°C|feu\s+(vif|doux|moyen))", text, re.I):  score += 0.05
        if re.search(r"\b\d+\s*min", text, re.I):                   score += 0.05
        if any(m in text.lower() for m in VISUAL_MARKERS):           score += 0.05

        return max(0.0, min(1.0, round(score, 3)))


# ═══════════════════════════════════════════════════════════════════════════════
# INTERFACE PUBLIQUE
# ═══════════════════════════════════════════════════════════════════════════════

_validator = RecipeValidator()

def validate_recipe(recipe: RecipeCDC, auto_fix: bool = True) -> ValidationReport:
    """Point d'entrée unique — valide et corrige une recette."""
    return _validator.validate(recipe, auto_fix=auto_fix)


def validate_batch(
    recipes: list[RecipeCDC],
    auto_fix: bool = True,
    min_score: float = 0.0,
) -> tuple[list[RecipeCDC], list[ValidationReport]]:
    """
    Valide une liste de recettes.
    Retourne (recettes_valides, tous_les_rapports).
    min_score filtre les recettes sous le seuil.
    """
    reports = []
    valid   = []

    for r in recipes:
        rep = validate_recipe(r, auto_fix=auto_fix)
        reports.append(rep)
        if rep.quality_score >= min_score:
            valid.append(r)
        else:
            log.info(f"Recette rejetée (score={rep.quality_score:.2f}): {rep.recipe_title}")

    passed = len(valid)
    total  = len(recipes)
    log.info(f"validate_batch → {passed}/{total} recettes valides (min_score={min_score})")
    return valid, reports


def quality_report(reports: list[ValidationReport]) -> dict:
    """Rapport agrégé sur un ensemble de ValidationReport."""
    from collections import Counter

    scores   = [r.quality_score for r in reports]
    all_errs = Counter(e for r in reports for e in r.errors)
    all_warn = Counter(w for r in reports for w in r.warnings)
    all_fix  = Counter(f.split(":")[0] for r in reports for f in r.fixes)

    return {
        "total":          len(reports),
        "avg_score":      round(sum(scores) / len(scores), 3) if scores else 0,
        "score_ge_08":    sum(1 for s in scores if s >= 0.8),
        "score_06_08":    sum(1 for s in scores if 0.6 <= s < 0.8),
        "score_lt_06":    sum(1 for s in scores if s < 0.6),
        "top_errors":     dict(all_errs.most_common(8)),
        "top_warnings":   dict(all_warn.most_common(10)),
        "top_auto_fixes": dict(all_fix.most_common(10)),
    }