@echo off
rem A senha sudo fica no terminal SSH, nunca no chat.
ssh -t user@your-server-ip "sudo bash /home/user/jarvis-json-fix-20261024/install.sh"
if errorlevel 1 (
  echo Correcao nao concluida. Confira a mensagem acima.
  pause
  exit /b 1
)
echo Correcao publicada. Clique em Atualizar no Orquestrador.
pause
