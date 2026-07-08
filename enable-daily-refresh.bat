@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0schedule-refresh.ps1" -Frequency Daily -Time 09:00
echo.
pause
