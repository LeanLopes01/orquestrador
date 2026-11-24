@echo off
setlocal
echo Crie o codigo abaixo, abra https://your-jarvis-api.example.com/ e informe-o.
ssh -t user@your-server-ip "sudo jarvis-control pair --kind app"
if errorlevel 1 goto end
echo Depois de parear, volte a esta janela para liberar o navegador correto.
pause
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0evolution.ps1" -Action grant
:end
pause
