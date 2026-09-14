@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: -- Activation venv si present ------------------------------------
if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) else if exist "env\Scripts\activate.bat" (
    call env\Scripts\activate.bat
)

echo.
echo ================================================================
echo   PIPELINE NUTRITION v8 - Source-ID driven (5 etapes)
echo ================================================================
echo.

set PYTHONIOENCODING=utf-8

:: -- Verification Python ------------------------------------------
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERREUR] Python introuvable. Verifiez votre PATH.
    pause
    exit /b 1
)

:: -- Verification openpyxl ----------------------------------------
python -c "import openpyxl" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installation openpyxl...
    pip install openpyxl -q
)

:: -- Verification sources brutes ----------------------------------
echo [ETAPE 0] Verification sources brutes...
echo ----------------------------------------------------------------

if not exist "backend\data\nutrition\raw\Table_Ciqual_2025_FR_2025_11_03.xlsx" (
    echo [ERREUR] CIQUAL xlsx introuvable.
    pause & exit /b 1
)
if not exist "backend\data\nutrition\raw\FoodData_Central_foundation_food_json_2025-12-18.json" (
    echo [ERREUR] USDA Foundation json introuvable.
    pause & exit /b 1
)
if not exist "backend\data\nutrition\raw\FoodData_Central_sr_legacy_food_csv_2018-04\food.csv" (
    echo [AVERTISSEMENT] USDA SR Legacy absent - portions USDA reduites.
)
if not exist "backend\data\nutrition\raw\cnf\FOOD_NAME.csv" (
    echo [ERREUR] CNF csv introuvable.
    pause & exit /b 1
)
if not exist "backend\data\ingredients\ingredients_tree.json" (
    echo [ERREUR] ingredients_tree.json introuvable.
    pause & exit /b 1
)

echo   OK - CIQUAL 2025
echo   OK - USDA FDC (Foundation Foods)
echo   OK - CNF
echo   OK - ingredients_tree.json

:: -- ETAPE 1 : Build nutrition_v2 ---------------------------------
echo.
echo [ETAPE 1/4] Build nutrition_v2.json...
echo   (chargement CIQUAL xlsx ~30s, patience...)
echo ----------------------------------------------------------------

python scripts\nutrition\build_n2_direct.py --promote
if errorlevel 1 (
    echo [ERREUR] build_n2_direct.py a echoue.
    echo          Verifiez que misses = 0 dans le rapport ci-dessus.
    pause & exit /b 1
)

:: -- ETAPE 2 : Build dictionnaire v2 ------------------------------
echo.
echo [ETAPE 2/4] Build dictionnaire ingredients v2...
echo   (Phase 1: structure, Phase 2: aliases, Phase 3: enrichissement)
echo ----------------------------------------------------------------

python scripts\nutrition\build_dict_v2.py
if errorlevel 1 (
    echo [ERREUR] build_dict_v2.py a echoue.
    pause & exit /b 1
)

:: -- ETAPE 2.5 : Build ingredient_physical ------------------------
echo.
echo [ETAPE 2.5/4] Build ingredient_physical.json...
echo   (water_content, edible_pct, portions depuis CIQUAL+USDA+CNF)
echo ----------------------------------------------------------------

python scripts\nutrition\build_physical_v2.py
if errorlevel 1 (
    echo [ERREUR] build_physical_v2.py a echoue.
    pause & exit /b 1
)

:: -- ETAPE 3 : Build indexes et graphs ----------------------------
echo.
echo [ETAPE 3/4] Build indexes et graphs (SOURCE:id driven)...
echo   (nutrition_index, token_index, availability, relation)
echo ----------------------------------------------------------------

python scripts\nutrition\build_indexes.py
if errorlevel 1 (
    echo [ERREUR] build_indexes.py a echoue.
    pause & exit /b 1
)

python scripts\nutrition\build_base_recipe_aliases.py
if errorlevel 1 (
    echo [ERREUR] build_base_recipe_aliases.py a echoue.
    pause & exit /b 1
)

:: -- ETAPE 4 : Coherence recettes [optionnel] ---------------------
echo.
set /p RUN_REC="[OPTIONNEL] Lancer fix_recipes_coherence --apply ? (o/N) : "
if /i "!RUN_REC!"=="o" (
    echo.
    echo [ETAPE 4/4] Coherence recettes...
    echo ----------------------------------------------------------------
    python scripts\nutrition\fix_recipes_coherence.py --apply
    if errorlevel 1 (
        echo [AVERTISSEMENT] fix_recipes_coherence a signale des anomalies.
    )
)

:: -- ETAPE 5 : Index recherche recettes [optionnel] ---------------
echo.
set /p RUN_IDX="[OPTIONNEL] Reconstruire search_index.json (recipes.json modifie) ? (o/N) : "
if /i "!RUN_IDX!"=="o" (
    echo.
    echo [ETAPE 5] Reconstruction search_index...
    echo ----------------------------------------------------------------
    python scripts\build_index.py
    if errorlevel 1 (
        echo [ERREUR] build_index.py a echoue.
        pause & exit /b 1
    )
)

:: -- ETAPE 6 : Rebuild graphs nutrition + scoring [optionnel] ------
echo.
set /p RUN_GRP="[OPTIONNEL] Reconstruire nutrition+scoring graphs (~45s) ? (o/N) : "
if /i "!RUN_GRP!"=="o" (
    echo.
    echo [ETAPE 6] Rebuild graphs nutrition + scoring...
    echo ----------------------------------------------------------------
    python scripts\recipes\rebuild_graphs.py
    if errorlevel 1 (
        echo [AVERTISSEMENT] rebuild_graphs a signale des anomalies.
    )
)

:: -- Resume -------------------------------------------------------
echo.
echo ================================================================
echo   PIPELINE TERMINE
echo ================================================================
echo.

python -c "
import json, sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
n2  = json.loads(Path('backend/data/nutrition/processed/nutrition_v2.json').read_text(encoding='utf-8'))
dv2 = json.loads(Path('backend/data/ingredients/ingredients_dictionary.json').read_text(encoding='utf-8'))
ni  = json.loads(Path('backend/data/indexes/nutrition_index.json').read_text(encoding='utf-8'))
ph  = json.loads(Path('backend/data/ingredients/ingredient_physical.json').read_text(encoding='utf-8'))
sch = dv2.get('_schema', {})
total = sum(len(sub['ingredient_groups'])
            for cat in dv2.get('categories', {}).values()
            for sub in cat['subcategories'].values())
m = ni.get('_meta', {})
pm = ph.get('_meta', {})
print('  nutrition_v2         :', n2.get('total_bases','?'), 'bases |', n2.get('total_variants','?'), 'variants')
print('  dict v2              :', total, 'entrees | built_at:', sch.get('built_at','?'))
print('  alias_index          :', len(dv2.get('alias_index', {})), 'entrees')
print('  nutrition_index      :', m.get('total_entries','?'), 'entrees |', m.get('by_source','?'))
print('  ingredient_physical  :', pm.get('total_entries','?'), 'entrees | ok:', pm.get('entries_ok','?'), '| stubs:', pm.get('entries_stub','?'))
print('  schema version       :', sch.get('version','?'))
si_path = Path('backend/data/indexes/search_index.json')
if si_path.exists():
    si = json.loads(si_path.read_text(encoding='utf-8'))
    print('  search_index         :', len(si), 'entrees')
"

echo.
pause
