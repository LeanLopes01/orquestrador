@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0evolution.ps1" -Action rollback
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
