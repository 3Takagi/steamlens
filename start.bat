@echo off
setlocal
cd /d "%~dp0"
set "PYTHON=E:\codex\tools\Python310\python.exe"
if not exist "%PYTHON%" set "PYTHON=python"
start "SteamLens Server" /b "%PYTHON%" -m http.server 8096 --bind 127.0.0.1 >nul 2>&1
timeout /t 1 /nobreak >nul
start "" http://127.0.0.1:8096/
