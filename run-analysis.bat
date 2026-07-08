@echo off
setlocal
cd /d "%~dp0"
set "BASE_PYTHON=E:\codex\tools\Python310\python.exe"
if not exist "%BASE_PYTHON%" set "BASE_PYTHON=python"
if not exist ".venv\Scripts\python.exe" (
  echo Creating local analysis environment...
  "%BASE_PYTHON%" -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-analysis.txt
  if errorlevel 1 goto :error
)
echo Running SteamLens data quality and model analysis...
".venv\Scripts\python.exe" scripts\analyze.py
if errorlevel 1 goto :error
echo Analysis completed.
pause
exit /b 0
:error
echo Analysis failed. Review the message above.
pause
exit /b 1
