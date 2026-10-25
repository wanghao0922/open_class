@echo off
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ".\start-local.ps1"
start "" "http://127.0.0.1:8010/teacher"
pause
