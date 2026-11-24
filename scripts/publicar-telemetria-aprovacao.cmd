@echo off
rem Publica no servidor a validacao da telemetria dos jobs (eventos, uso, atividade).
rem So faz o deploy: nao muda papeis, pareamento nem permissoes de nenhum aparelho.
rem O pacote ja esta em /tmp do servidor; a senha sudo e pedida pelo SSH, aqui no terminal.
rem jarvis-deploy roda a suite de testes e o smoke test, e volta a versao anterior se falhar.
ssh -t user@your-server-ip "sudo jarvis-deploy /tmp/jarvis-backend-20261022T122150Z-telemetry-approval.tar.gz fccf5eac6c7b9d62f22186c49585d379e1c8d27cb649437fa150bec04c741a87"
if errorlevel 1 (
  echo.
  echo Publicacao nao concluida. Confira a mensagem do servidor acima.
  pause
  exit /b 1
)
echo.
echo Servidor atualizado. Nenhum papel de aparelho foi alterado.
pause
