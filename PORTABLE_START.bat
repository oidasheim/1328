@echo off
setlocal
cd /d "%~dp0"
if not defined PYTHON_EXE set "PYTHON_EXE=python"
:menu
cls
echo WE.ED.IT OIDA portable launcher
echo 1. Doctor and toolchain
echo 2. Verify local install
echo 3. Run all setup and verification stages
echo 4. Compile and render (provide paths)
echo 5. Exit
set /p choice=Select: 
if "%choice%"=="1" "%PYTHON_EXE%" -m weedit_native.cli doctor --deep & pause & goto menu
if "%choice%"=="2" "%PYTHON_EXE%" -m weedit_native.cli verify & pause & goto menu
if "%choice%"=="3" call PORTABLE_INSTALL.bat & pause & goto menu
if "%choice%"=="4" echo Usage: weed make SONG CLIPS --out OUTPUT.mp4 & pause & goto menu
if "%choice%"=="5" exit /b 0
goto menu
