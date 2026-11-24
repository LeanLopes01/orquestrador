@echo off
rem Depois de autorizar as contas no n8n: verifica identidade e servicos de cada
rem conta e mostra o estado. So liga as ferramentas se voce confirmar.
ssh -t user@your-server-ip "sudo jarvis-control personal-verify; sudo jarvis-control personal-status"
set /p LIGAR=Ligar as ferramentas pessoais no Jarvis agora? (s/N) 
if /i "%LIGAR%"=="s" ssh -t user@your-server-ip "sudo jarvis-control personal-runtime on && sudo jarvis-control personal-status"
pause
