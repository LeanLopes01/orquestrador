@echo off
chcp 65001 >nul
echo Aplicando o pacote de autoconhecimento ja preparado no servidor.
echo Encerre a chamada de voz. Digite a senha de sudo somente neste terminal.
ssh -t user@your-server-ip "sudo bash /home/user/jarvis-self-knowledge-20261028/install-server.sh"
if errorlevel 1 (
  echo Instalacao nao confirmada. Confira a mensagem acima.
) else (
  echo Instalacao concluida. Abra uma nova chamada de voz para usar a correcao.
)
pause
