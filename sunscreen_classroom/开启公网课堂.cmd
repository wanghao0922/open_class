@echo off
chcp 65001 >nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-online.ps1"
start "" "https://sunscreen-classroom.onrender.com/teacher"
pause
