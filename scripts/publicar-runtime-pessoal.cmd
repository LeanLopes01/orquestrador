@echo off
rem Publica o runtime de dados pessoais. O pacote e o script ja estao no servidor.
rem A senha sudo e digitada no terminal. jarvis-deploy roda testes e smoke de voz,
rem com rollback em falha. As ferramentas continuam desligadas ate a verificacao.
ssh -t user@your-server-ip "sudo bash /home/user/jarvis-integrations/publish-runtime.sh"
if errorlevel 1 (
  echo Publicacao nao concluida. Confira a mensagem acima.
  pause
  exit /b 1
)
echo Runtime pessoal publicado (desligado).
pause
