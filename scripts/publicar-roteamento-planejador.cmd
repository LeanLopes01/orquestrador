@echo off
rem Publica no servidor o roteamento do planejador (Codex ou Antigravity planeja, Claude executa).
rem So faz o deploy: nao muda papeis, pareamento nem permissoes de nenhum aparelho.
rem O pacote ja esta em /tmp do servidor; a senha sudo e pedida pelo SSH, aqui no terminal.
rem jarvis-deploy roda a suite de testes e o smoke test, e volta a versao anterior se falhar.
rem O helper do PC ja foi atualizado e reiniciado antes deste deploy.
ssh -t user@your-server-ip "sudo jarvis-deploy /tmp/jarvis-backend-20261022T223448Z-planner-routing.tar.gz f9689359afee52a639cdcba4029df966e36bb2bdee134682ea5bf6a0f3a5bdac"
if errorlevel 1 (
  echo.
  echo Publicacao nao concluida. Confira a mensagem do servidor acima.
  pause
  exit /b 1
)
echo.
echo Servidor atualizado. Nenhum papel de aparelho foi alterado.
pause
