@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: ================================================================
::  PIPELINE DONNEES ALIM - rebuild complet et valide
::
::  Meme sequence que la section « Rebuild des donnees » du README
::  (verifiee le 2026-09-15). Chaque etape s'arrete a la premiere erreur.
::
::  NE PAS AJOUTER build_physical_v2.py ni build_base_recipe_aliases.py :
::  ils regenerent ingredient_physical.json (1007 cles renommees) et des
::  alias de preparations differents des fichiers actuels.
::  Garde-fou : tests/test_data_integrity.py::test_run_pipeline_bat_sequence_validee
:: ================================================================

:: -- Activation venv si present ------------------------------------
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
)

echo.
echo ================================================================
echo   PIPELINE DONNEES ALIM - rebuild complet
echo ================================================================
echo.

set PYTHONIOENCODING=utf-8

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable. Verifiez votre PATH.
    pause
    exit /b 1
)

:: -- ETAPE 0 : sources brutes --------------------------------------
echo [ETAPE 0] Verification des sources brutes...
echo ----------------------------------------------------------------
if not exist "backend\data\nutrition\raw\Table_Ciqual_2025_FR_2025_11_03.xlsx" (
    echo [ERREUR] CIQUAL xlsx introuvable.
    pause & exit /b 1
)
if not exist "backend\data\nutrition\raw\FoodData_Central_foundation_food_json_2025-12-18.json" (
    echo [ERREUR] USDA Foundation json introuvable.
    pause & exit /b 1
)
if not exist "backend\data\nutrition\raw\sr_legacy\food.csv" (
    echo [ERREUR] USDA SR Legacy absent : extraire FoodData_Central_sr_legacy_food_csv_2018-04.zip
    echo          dans backend\data\nutrition\raw\sr_legacy\ - requis pour haricots secs et plats cuisines
    pause & exit /b 1
)
if not exist "backend\data\nutrition\raw\cnf\FOOD_NAME.csv" (
    echo [ERREUR] CNF csv introuvable.
    pause & exit /b 1
)
echo   OK - CIQUAL 2025, USDA Foundation + SR Legacy, CNF

:: -- ETAPE 1 : nutrition_v2 ----------------------------------------
echo.
echo [ETAPE 1/7] build_n2_direct --promote  (CIQUAL xlsx ~30 s)
echo ----------------------------------------------------------------
python scripts\nutrition\build_n2_direct.py --promote
if errorlevel 1 ( echo [ERREUR] build_n2_direct.py & pause & exit /b 1 )

:: -- ETAPE 2 : dictionnaire ----------------------------------------
echo.
echo [ETAPE 2/7] build_dict_v2
echo ----------------------------------------------------------------
python scripts\nutrition\build_dict_v2.py
if errorlevel 1 ( echo [ERREUR] build_dict_v2.py & pause & exit /b 1 )

:: -- ETAPE 3 : index nutrition -------------------------------------
echo.
echo [ETAPE 3/7] build_indexes
echo ----------------------------------------------------------------
python scripts\nutrition\build_indexes.py
if errorlevel 1 ( echo [ERREUR] build_indexes.py & pause & exit /b 1 )

:: -- ETAPE 4 : regimes / allergenes + registre des sous-recettes ---
::    alternes jusqu'a stabilisation (un flag de sous-recette peut changer
::    le registre, qui change les flags des recettes qui l'utilisent)
echo.
echo [ETAPE 4/7] Regimes/allergenes et registre des sous-recettes
echo ----------------------------------------------------------------
for /l %%i in (1,1,4) do (
    python scripts\recipes\fix_recipe_diet_allergens.py
    if errorlevel 1 ( echo [ERREUR] fix_recipe_diet_allergens.py & pause & exit /b 1 )
    python scripts\recipes\build_derived_base_registry.py
    if errorlevel 1 ( echo [ERREUR] build_derived_base_registry.py & pause & exit /b 1 )
    python scripts\recipes\build_derived_base_registry.py --check >nul 2>&1
    if not errorlevel 1 goto registry_ok
)
echo [ERREUR] registre des sous-recettes non stabilise apres 4 passes.
pause & exit /b 1
:registry_ok
echo   OK - registre stable

:: -- ETAPE 5 : graphes nutrition + scoring -------------------------
echo.
echo [ETAPE 5/7] rebuild_graphs
echo ----------------------------------------------------------------
python scripts\recipes\rebuild_graphs.py
if errorlevel 1 ( echo [ERREUR] rebuild_graphs.py & pause & exit /b 1 )

:: -- ETAPE 6 : index de recherche ----------------------------------
echo.
echo [ETAPE 6/7] build_index (search_index.json)
echo ----------------------------------------------------------------
python scripts\build_index.py
if errorlevel 1 ( echo [ERREUR] build_index.py & pause & exit /b 1 )

:: -- ETAPE 7 : controles (lecture seule) ---------------------------
echo.
echo [ETAPE 7/7] Controles de coherence (aucune ecriture)
echo ----------------------------------------------------------------
python scripts\recipes\propose_servings.py --out "%TEMP%\alim_servings_check.csv"
python scripts\recipes\propose_servings.py --components --out "%TEMP%\alim_servings_components_check.csv"
python scripts\nutrition\fix_recipes_coherence.py --quiet
python -m pytest tests\test_data_integrity.py -q
if errorlevel 1 (
    echo.
    echo [AVERTISSEMENT] tests d'integrite des donnees en echec : voir ci-dessus
    echo                 avant de commiter les fichiers regeneres.
) else (
    echo   OK - tests d'integrite des donnees
)

echo.
echo ================================================================
echo   PIPELINE TERMINE - verifier « git diff --stat » avant commit
echo ================================================================
echo.
pause
