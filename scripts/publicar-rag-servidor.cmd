@echo off
rem Publica no servidor Jarvis as rotas /v1/rag/* e a ferramenta de voz do RAG.
rem O pacote ja foi copiado para /tmp do servidor. A senha sudo e pedida pelo SSH,
rem nesta janela, sem passar pelo chat. O jarvis-deploy roda os testes, o smoke test
rem e volta para a versao anterior sozinho se algo falhar.
setlocal
set "PKG=jarvis-backend-20261022T010605Z-rag.tar.gz"
set "SHA=2cb24d6f0f7b44a98bb2ef5f6cb57d94112f9b6496fb06fb8869cec8be597d2f"
echo Publicando %PKG% no servidor your-server-ip...
ssh -t user@your-server-ip "sudo jarvis-deploy /tmp/%PKG% %SHA% && sudo jarvis-control devices"
if errorlevel 1 (
  echo.
  echo Publicacao nao concluida. Confira a mensagem do servidor acima.
  pause
  exit /b 1
)
echo.
echo Servidor atualizado: os celulares ja podem usar Knowledge (RAG) e o Jarvis por voz consulta o RAG.
pause
