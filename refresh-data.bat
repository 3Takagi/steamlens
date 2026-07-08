@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=E:\codex\tools\Python310\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
echo Refreshing four Steam review datasets...
"%PYTHON%" scripts\collect.py
if errorlevel 1 (
  echo.
  echo Collection failed. Check the network connection and try again.
) else (
  if exist ".venv\Scripts\python.exe" (
    echo Running model analysis...
    ".venv\Scripts\python.exe" scripts\analyze.py
  )
  echo.
  echo Data refresh completed.
)
pause
