@echo off
chcp 65001 >nul
echo Atualizacao do fluxo Planejamento - UI - Codigo.
echo Aguarde os trabalhos ativos terminarem. Digite a senha de sudo no terminal.
ssh -t user@your-server-ip "sudo bash /home/user/jarvis-project-pipeline-20261028/install-server.sh"
if errorlevel 1 (
  echo Instalacao nao confirmada. Confira a mensagem acima.
) else (
  echo Atualizacao concluida. Atualize a pagina Projects no Orquestrador.
)
pause
