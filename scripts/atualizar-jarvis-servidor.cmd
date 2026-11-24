@echo off
setlocal
title Atualizar Jarvis no servidor
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0evolution.ps1" -Action deploy
set "RESULT=%ERRORLEVEL%"
echo.
pause
exit /b %RESULT%
