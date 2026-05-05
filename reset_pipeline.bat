@echo off
REM ============================================================
REM reset_pipeline.bat  [v2.2]
REM Pipeline complet ALIM v6 — nutrition + recettes
REM
REM Etapes :
REM   1.  Build ontologie (fusion CIQUAL/USDA/CNF)
REM   2.  Auto-correction + enrichissement
REM   3.  Validation croisee CIQUAL/USDA/CNF
REM   3b. Application corrections (--apply)
REM   4.  Patch criticals + tagging carbs_schema (v8)
REM   4b. Validation post-patch (0 criticals attendus)
REM   5.  Diagnostic final couverture
REM   6.  Promotion vers nutrition_v2.json
REM   7.  Generation aliases nutrition
REM   7b. Corrections critiques nutrition_v2
REM   7c. Coherence macro (fiber/starch)
REM   8.  Audit + corrections coherence recettes
REM   9.  Synchro dictionnaire ingredients
REM
REM Usage :
REM   reset_pipeline.bat             # pipeline complet
REM   reset_pipeline.bat --skip-src  # saute les etapes 0 (sources deja a jour)
REM
REM PREREQUIS : lancer depuis la RACINE du projet
REM   cd C:\...\project_final_v6_migrated
REM   scripts\nutrition\reset_pipeline.bat
REM ============================================================

setlocal EnableDelayedExpansion

REM Encodage UTF-8
chcp 65001 > nul
set PYTHONIOENCODING=utf-8

REM Verification repertoire courant
if not exist "backend\data\recipes\recipes.json" (
    echo ERREUR : Lancer depuis la RACINE du projet.
    echo   cd C:\...\project_final_v6_migrated
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  ALIM v6 — Pipeline complet
echo ============================================================

REM ── ETAPE 1 — Ontologie ──────────────────────────────────────
echo.
echo [1/9] Build ontologie (fusion CIQUAL v3 + USDA v2 + CNF v10)...
python scripts\nutrition\build_ontology_v6.py
if errorlevel 1 goto error

REM ── ETAPE 2 — Auto-correction ────────────────────────────────
echo.
echo [2/9] Auto-correction + enrichissement nutrition_v2...
python scripts\nutrition\auto_correct_v6.py
if errorlevel 1 goto error

REM ── ETAPE 3 — Validation ─────────────────────────────────────
echo.
echo [3/9] Validation croisee CIQUAL/USDA/CNF...
python scripts\nutrition\validator_v12.py
if errorlevel 1 goto error

echo.
echo [3b/9] Application corrections (score>=0.90, severity>=warning)...
python scripts\nutrition\validator_v12.py --apply --severity=warning --score=0.90
if errorlevel 1 goto error

REM ── ETAPE 4 — Patch ──────────────────────────────────────────
echo.
echo [4/9] Patch criticals + tagging carbs_schema (v8)...
python scripts\nutrition\patch_nutrition_v8.py
if errorlevel 1 goto error

REM -- ETAPE 4b -- Validation post-patch (0 criticals attendus)
echo.
echo [4b/9] Validation post-patch...
python scripts\nutrition\validator_v12.py --audit --input backend\data\nutrition\reference\nutrition_patched_v8.json
if errorlevel 1 (
    echo.
    echo  ATTENTION : criticals detectes - corriger patch_nutrition_v8.py avant de promouvoir.
    goto error
)

REM ── ETAPE 5 — Diagnostic ─────────────────────────────────────
echo.
echo [5/9] Diagnostic final couverture...
python scripts\nutrition\_diagnose_v2.py --section coverage
python scripts\nutrition\_diagnose_v2.py --section log

REM ── ETAPE 6 — Promotion ──────────────────────────────────────
echo.
echo [6/9] Promotion vers nutrition_v2.json...
python scripts\nutrition\promote_nutrition.py --confirm
if errorlevel 1 goto error

REM ── ETAPE 7 — Aliases ────────────────────────────────────────
echo.
echo [7/9] Generation aliases nutrition...
python scripts\nutrition\build_nutrition_aliases.py
if errorlevel 1 goto error

REM ── ETAPE 7b — Patches critiques nutrition ─────────────────────
echo.
echo [7b/9] Corrections critiques nutrition_v2 (water/oil/quinoa/pepper/almond)...
python scripts\nutrition\patch_nutrition_critical.py
if errorlevel 1 goto error

REM ── ETAPE 7c — Coherence macro (fiber/starch) ──────────────────
echo.
echo [7c/9] Coherence macro (carbs_basis flags + starch overflow)...
python scripts\nutrition\patch_macro_coherence.py
if errorlevel 1 goto error

REM ── ETAPE 8 — Coherence recettes ───────────────────────────────
echo.
echo [8/9] Audit + correction coherence recettes (fix_recipes_coherence)...
echo       Controles : lactose_free, vegan flags, timing, descriptions, servings...
python scripts\nutrition\fix_recipes_coherence.py --apply
if errorlevel 1 goto error

REM ── ETAPE 9 — Synchro dictionnaire ───────────────────────────
echo.
echo [9/9] Synchro dictionnaire ingredients...
python scripts\nutrition\sync_nutrition_to_dict.py
if errorlevel 1 goto error

REM ── FIN ───────────────────────────────────────────────────────
echo.
echo ============================================================
echo  Pipeline termine avec succes.
echo.
echo  Fichiers produits :
echo    backend\data\nutrition\processed\nutrition_v2.json
echo    backend\data\nutrition\reference\nutrition_aliases_v6.json
echo    backend\data\ingredients\ingredients_dictionary.json
echo    backend\data\recipes\recipes.json
echo    backend\data\logs\coherence_corrections_log.json
echo ============================================================
pause
exit /b 0

:error
echo.
echo ============================================================
echo  ERREUR dans le pipeline — etape precedente.
echo  Consultez le message ci-dessus.
echo ============================================================
pause
exit /b 1
