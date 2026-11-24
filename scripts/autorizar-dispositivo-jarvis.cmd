@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0evolution.ps1" -Action grant
pause
