@echo off
REM ========================================
REM  Inventory Manager Pro - Build Script
REM  Automated EXE Creation
REM ========================================

echo.
echo ========================================
echo  INVENTORY MANAGER PRO - BUILD SCRIPT
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed!
    echo Please install Python from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [OK] Python is installed
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] PyInstaller not found. Installing...
    pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] Failed to install PyInstaller
        pause
        exit /b 1
    )
    echo [OK] PyInstaller installed
) else (
    echo [OK] PyInstaller is installed
)

echo.
echo ========================================
echo  BUILD OPTIONS
echo ========================================
echo.
echo Choose build type:
echo  1. Quick Build (onefile, windowed)
echo  2. Full Build (onefile, windowed, icon, optimized)
echo  3. Debug Build (onedir, with console)
echo.
set /p choice="Enter choice (1-3): "

if "%choice%"=="1" goto quick_build
if "%choice%"=="2" goto full_build
if "%choice%"=="3" goto debug_build

echo [ERROR] Invalid choice!
pause
exit /b 1

:quick_build
echo.
echo [INFO] Starting Quick Build...
echo.

echo [1/3] Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo [2/3] Building EXE...
pyinstaller --onefile --windowed --name "InventoryManager" inventory_manager.py

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [3/3] Copying files...
copy README.md dist\ >nul 2>nul
copy Import_Demo_Excel.xlsx dist\ >nul 2>nul

goto build_complete

:full_build
echo.
echo [INFO] Starting Full Build (Optimized)...
echo.

REM Check for icon
if not exist app_icon.ico (
    echo [WARNING] app_icon.ico not found. Build will proceed without icon.
    set icon_param=
) else (
    echo [OK] Icon file found
    set icon_param=--icon=app_icon.ico
)

echo [1/4] Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo [2/4] Building optimized EXE...
pyinstaller --onefile ^
    --windowed ^
    --name "InventoryManager" ^
    %icon_param% ^
    --hidden-import=openpyxl ^
    --hidden-import=openpyxl.cell._writer ^
    --hidden-import=sqlite3 ^
    --add-data "README.md;." ^
    --optimize=2 ^
    inventory_manager.py

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [3/4] Copying additional files...
copy README.md dist\ >nul 2>nul
copy Import_Demo_Excel.xlsx dist\ >nul 2>nul
copy BUILD_TO_EXE.md dist\ >nul 2>nul
copy FEATURE_IDEAS.md dist\ >nul 2>nul

echo [4/4] Creating distribution package...
cd dist
if not exist InventoryManager_Package mkdir InventoryManager_Package
copy InventoryManager.exe InventoryManager_Package\ >nul
copy README.md InventoryManager_Package\ >nul 2>nul
copy Import_Demo_Excel.xlsx InventoryManager_Package\ >nul 2>nul
copy BUILD_TO_EXE.md InventoryManager_Package\ >nul 2>nul

cd ..

goto build_complete

:debug_build
echo.
echo [INFO] Starting Debug Build (with console)...
echo.

echo [1/3] Cleaning old builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec

echo [2/3] Building debug EXE...
pyinstaller --onedir ^
    --console ^
    --name "InventoryManager_Debug" ^
    --hidden-import=openpyxl ^
    --hidden-import=sqlite3 ^
    inventory_manager.py

if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [3/3] Copying files...
copy README.md dist\InventoryManager_Debug\ >nul 2>nul
copy Import_Demo_Excel.xlsx dist\InventoryManager_Debug\ >nul 2>nul

goto build_complete

:build_complete
echo.
echo ========================================
echo  BUILD COMPLETE!
echo ========================================
echo.

if "%choice%"=="1" (
    echo EXE Location: dist\InventoryManager.exe
    echo Size: 
    dir dist\InventoryManager.exe | find "InventoryManager.exe"
)

if "%choice%"=="2" (
    echo EXE Location: dist\InventoryManager.exe
    echo Package Location: dist\InventoryManager_Package\
    echo.
    echo Size:
    dir dist\InventoryManager.exe | find "InventoryManager.exe"
)

if "%choice%"=="3" (
    echo Debug Build Location: dist\InventoryManager_Debug\
    echo Run: dist\InventoryManager_Debug\InventoryManager_Debug.exe
)

echo.
echo ========================================
echo  NEXT STEPS
echo ========================================
echo.
echo 1. Test the EXE: Double-click to run
echo 2. Check for errors
echo 3. Distribute to users
echo.
echo TIP: For distribution, create a ZIP of the dist folder
echo.

REM Ask if user wants to run the EXE
set /p run="Do you want to run the EXE now? (Y/N): "
if /i "%run%"=="Y" (
    if "%choice%"=="1" start dist\InventoryManager.exe
    if "%choice%"=="2" start dist\InventoryManager.exe
    if "%choice%"=="3" start dist\InventoryManager_Debug\InventoryManager_Debug.exe
)

echo.
echo Build script completed successfully!
pause
