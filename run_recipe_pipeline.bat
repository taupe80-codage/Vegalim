@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

echo.
echo ================================================================
echo   PIPELINE RECETTES ALIM v4
echo   Reconstitution culinaire (collect / parse / cluster / synth)
echo ================================================================
echo.

set PYTHONIOENCODING=utf-8
set PIPELINE_DIR=scripts\recipe_pipeline
set OUTPUT_DIR=backend\data\recipes
set OUTPUT_RAW=%OUTPUT_DIR%\recipes_raw_collected.json
set OUTPUT_CDC=%OUTPUT_DIR%\recipes_cdc.json

:: -- Verification Python ------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable. Verifiez votre PATH.
    pause & exit /b 1
)

:: -- Installation dependances -------------------------------------
echo [INFO] Verification dependances...
python -m pip install -q -r %PIPELINE_DIR%\requirements.txt
if errorlevel 1 (
    echo [ERREUR] Installation dependances echouee.
    pause & exit /b 1
)
echo   OK

:: -- Verification dossier de sortie ------------------------------
if not exist "%OUTPUT_DIR%" (
    mkdir "%OUTPUT_DIR%"
    echo   Dossier cree : %OUTPUT_DIR%
)

:: -- Menu principal ----------------------------------------------
echo.
echo  Que voulez-vous faire ?
echo.
echo   [1] Pipeline complet   : collecte MealDB + parsing + cluster + synthese (stub si pas de cle Groq)
echo   [2] Pipeline + Groq    : meme chose mais avec réécriture LLM (necessite GROQ_API_KEY)
echo   [3] Valider un CDC     : valider + corriger automatiquement un fichier CDC existant
echo   [4] Post-corriger      : alim_corrector — cohere vegan flags + recalcul scores
echo   [5] Reecrire Groq      : alim_rewriter — reecrire les instructions insuffisantes via Groq
echo   [6] Validate-only      : marquer les recettes a reecrire sans appel LLM
echo.
set /p CHOIX="Votre choix (1-6) : "

if "!CHOIX!"=="1" goto :PIPELINE_STUB
if "!CHOIX!"=="2" goto :PIPELINE_GROQ
if "!CHOIX!"=="3" goto :VALIDATE_CDC
if "!CHOIX!"=="4" goto :POST_CORRECT
if "!CHOIX!"=="5" goto :REWRITE_GROQ
if "!CHOIX!"=="6" goto :VALIDATE_ONLY
echo [ERREUR] Choix invalide.
pause & exit /b 1


:: ================================================================
:PIPELINE_STUB
echo.
echo [1/7] Pipeline complet — mode stub (pas de LLM)
echo ----------------------------------------------------------------
python %PIPELINE_DIR%\pipeline.py ^
    --sources mealdb ^
    --output %OUTPUT_CDC% ^
    --save-raw %OUTPUT_RAW% ^
    --llm-backend stub
if errorlevel 1 (
    echo [ERREUR] Pipeline echoue.
    pause & exit /b 1
)
goto :END


:: ================================================================
:PIPELINE_GROQ
echo.
echo [2/7] Pipeline complet — Groq llama-3.3-70b
echo ----------------------------------------------------------------
if "!GROQ_API_KEY!"=="" (
    set /p GROQ_API_KEY="Entrez votre cle GROQ_API_KEY (gsk_...) : "
)
if "!GROQ_API_KEY!"=="" (
    echo [ERREUR] Cle Groq manquante.
    pause & exit /b 1
)
python %PIPELINE_DIR%\pipeline.py ^
    --sources mealdb ^
    --output %OUTPUT_CDC% ^
    --save-raw %OUTPUT_RAW% ^
    --llm-backend groq ^
    --groq-api-key !GROQ_API_KEY!
if errorlevel 1 (
    echo [ERREUR] Pipeline echoue.
    pause & exit /b 1
)
goto :END


:: ================================================================
:VALIDATE_CDC
echo.
echo [3] Validation + corrections automatiques d'un CDC existant
echo ----------------------------------------------------------------
set /p CDC_INPUT="Chemin du fichier CDC a valider (defaut: %OUTPUT_CDC%) : "
if "!CDC_INPUT!"=="" set CDC_INPUT=%OUTPUT_CDC%
if not exist "!CDC_INPUT!" (
    echo [ERREUR] Fichier introuvable : !CDC_INPUT!
    pause & exit /b 1
)
python %PIPELINE_DIR%\pipeline.py ^
    --from-cdc "!CDC_INPUT!" ^
    --validate-only ^
    --output "!CDC_INPUT!"
if errorlevel 1 (
    echo [ERREUR] Validation echouee.
    pause & exit /b 1
)
goto :END


:: ================================================================
:POST_CORRECT
echo.
echo [4] Post-correction flags vegan + recalcul scores
echo ----------------------------------------------------------------
set /p PC_INPUT="Fichier source (defaut: %OUTPUT_CDC%) : "
if "!PC_INPUT!"=="" set PC_INPUT=%OUTPUT_CDC%
if not exist "!PC_INPUT!" (
    echo [ERREUR] Fichier introuvable : !PC_INPUT!
    pause & exit /b 1
)
set PC_OUTPUT=!PC_INPUT:.json=_corrected.json!
python %PIPELINE_DIR%\alim_corrector.py ^
    --input "!PC_INPUT!" ^
    --output "!PC_OUTPUT!" ^
    --report
if errorlevel 1 (
    echo [ERREUR] Correction echouee.
    pause & exit /b 1
)
echo   Sortie : !PC_OUTPUT!
goto :END


:: ================================================================
:REWRITE_GROQ
echo.
echo [5] Reecriture instructions via Groq
echo ----------------------------------------------------------------
if "!GROQ_API_KEY!"=="" (
    set /p GROQ_API_KEY="Entrez votre cle GROQ_API_KEY (gsk_...) : "
)
if "!GROQ_API_KEY!"=="" (
    echo [ERREUR] Cle Groq manquante.
    pause & exit /b 1
)
set /p RW_INPUT="Fichier source (defaut: %OUTPUT_CDC%) : "
if "!RW_INPUT!"=="" set RW_INPUT=%OUTPUT_CDC%
if not exist "!RW_INPUT!" (
    echo [ERREUR] Fichier introuvable : !RW_INPUT!
    pause & exit /b 1
)
set RW_OUTPUT=!RW_INPUT:.json=_rewritten.json!
python %PIPELINE_DIR%\alim_rewriter.py ^
    --input "!RW_INPUT!" ^
    --output "!RW_OUTPUT!" ^
    --batch-size 3 ^
    --workers 1
if errorlevel 1 (
    echo [ERREUR] Réécriture echouee.
    pause & exit /b 1
)
echo   Sortie : !RW_OUTPUT!
goto :END


:: ================================================================
:VALIDATE_ONLY
echo.
echo [6] Validation seule — marquer les recettes a reecrire
echo ----------------------------------------------------------------
set /p VO_INPUT="Fichier source (defaut: %OUTPUT_CDC%) : "
if "!VO_INPUT!"=="" set VO_INPUT=%OUTPUT_CDC%
if not exist "!VO_INPUT!" (
    echo [ERREUR] Fichier introuvable : !VO_INPUT!
    pause & exit /b 1
)
python %PIPELINE_DIR%\alim_rewriter.py ^
    --input "!VO_INPUT!" ^
    --output "!VO_INPUT!" ^
    --validate-only
if errorlevel 1 (
    echo [ERREUR] Validation echouee.
    pause & exit /b 1
)
goto :END


:: ================================================================
:END
echo.
echo ================================================================
echo   TERMINE
echo ================================================================
echo.
python -c "
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
p = Path('backend/data/recipes/recipes_cdc.json')
if not p.exists():
    print('  (aucun fichier CDC produit)')
    sys.exit(0)
data = json.loads(p.read_text(encoding='utf-8'))
recipes = data.get('recipes', data) if isinstance(data, dict) else data
meta    = data.get('metadata', {}) if isinstance(data, dict) else {}
scores  = [r.get('_quality_score', 0) for r in recipes if '_quality_score' in r]
avg     = sum(scores)/len(scores) if scores else 0
above8  = sum(1 for s in scores if s >= 0.8)
print(f'  Recettes exportees  : {len(recipes)}')
print(f'  Score moyen         : {avg:.3f}')
print(f'  Score >= 0.80       : {above8}')
print(f'  Version CDC         : {meta.get(\"version\", \"?\")}')
print(f'  Genere le          : {meta.get(\"generated_at\", \"?\")}')
" 2>nul

echo.
pause
