@echo off
setlocal
set "PYTHONUTF8=1"
set "SCRIPT=%~dp0src\fullstack_v9_workflow.py"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%SCRIPT%" %*
) else (
  python "%SCRIPT%" %*
)
exit /b %errorlevel%
