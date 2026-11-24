@echo off
setlocal
cd /d "%~dp0"
if not defined PYTHON_EXE set "PYTHON_EXE=python"
"%PYTHON_EXE%" scripts\portable_install.py %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo Portable setup completed with errors. See reports\portable-install-latest.json
exit /b %RC%
