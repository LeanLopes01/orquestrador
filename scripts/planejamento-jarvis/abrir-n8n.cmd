@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0acesso-servidor.ps1" -Acao Painel
set "jarvis_exit=%errorlevel%"
echo.
pause
exit /b %jarvis_exit%
