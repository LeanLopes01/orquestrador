@echo off
rem O pacote e o script ja estao no servidor. A senha sudo e digitada no terminal.
rem Testes e smoke test sao executados pelo jarvis-deploy, com rollback em falha.
ssh -t user@your-server-ip "sudo bash /home/user/jarvis-integrations/publish-personal.sh"
if errorlevel 1 (
  echo Publicacao nao concluida. Confira a mensagem acima.
  pause
  exit /b 1
)
echo Atualizacao de Conexoes concluida.
pause
