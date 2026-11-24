@echo off
rem Publica no servidor Jarvis os avisos falados do Orquestrador: "trabalhando",
rem "ainda trabalhando" a cada 3 minutos e a resposta do pedido no celular mestre.
rem O pacote ja foi copiado para /tmp do servidor. A senha sudo e pedida pelo SSH,
rem nesta janela, sem passar pelo chat. O jarvis-deploy roda os testes, o smoke test
rem e volta para a versao anterior sozinho se algo falhar.
setlocal
set "PKG=jarvis-backend-20261022T094226Z-working-voice.tar.gz"
set "SHA=bd965ad7f87897f32843d8ed19aa1b85ea3a60f0e1364a89d31211def3810135"
echo Publicando %PKG% no servidor your-server-ip...
ssh -t user@your-server-ip "sudo jarvis-deploy /tmp/%PKG% %SHA% && sudo jarvis-control devices"
if errorlevel 1 (
  echo.
  echo Publicacao nao concluida. Confira a mensagem do servidor acima.
  pause
  exit /b 1
)
echo.
echo Servidor atualizado: o Motorola passa a falar quando o Orquestrador trabalha e a resposta final.
pause
