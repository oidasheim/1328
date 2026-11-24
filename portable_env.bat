@echo off
rem Portable project-local paths only; no hard-coded drive letters.
set "SYNAPSE_ROOT=%~dp0"
set "WEEDIT_DB_PATH=%SYNAPSE_ROOT%database\genome.sqlite3"
set "WEEDIT_OUTPUT_DIR=%SYNAPSE_ROOT%output"
set "WEEDIT_REPORT_DIR=%SYNAPSE_ROOT%reports"
set "WEEDIT_TEMP_DIR=%SYNAPSE_ROOT%temp"
set "TMP=%WEEDIT_TEMP_DIR%"
set "TEMP=%WEEDIT_TEMP_DIR%"
set "UV_LINK_MODE=copy"
