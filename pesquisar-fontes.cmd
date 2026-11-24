@echo off
setlocal
rem Descoberta e importacao em massa de fontes para o RAG (services\discovery):
rem   1) APIs da Unity/pacotes/Facepunch usadas nos scripts do DiceVTT e ausentes do RAG
rem   2) topicos estruturados + AirLLM local + perguntas recentes -> paginas do manual
rem   3) corpus local (SRD 5e em XML + notas Markdown da Janela de Contexto)
rem   4) coleta pela ingestao e indexacao no RAG
rem Uso: pesquisar-fontes.cmd                  (importa corpus local + coleta web rapida + indexa)
rem      pesquisar-fontes.cmd import-local     (so importa SRD 5e XML + notas locais)
rem      pesquisar-fontes.cmd plan --no-llm    (so mostra o que seria coletado na web)
rem      pesquisar-fontes.cmd run --no-llm     (coleta web sem AirLLM: muito mais rapido)
rem      pesquisar-fontes.cmd run              (coleta web com AirLLM)
cd /d "%~dp0"
chcp 65001 >nul
set "PYTHONIOENCODING=utf-8"
title Orquestrador DiceVTT - pesquisando fontes para o RAG

set "RAG_PY=%~dp0.venv-rag\Scripts\python.exe"
set "HELPER_PY=C:\J.A.R.V.I.S\jarvis\.venv\Scripts\pythonw.exe"
set "HELPER_SRC=C:\J.A.R.V.I.S\jarvis\src"
set "CMD=%~1"
if "%CMD%"=="" set "CMD=bulk"

if not exist "%RAG_PY%" (
  echo [erro] Ambiente do RAG ^(.venv-rag^) nao encontrado.
  pause
  exit /b 2
)

if /i "%CMD%"=="run" goto :ensure_services
if /i "%CMD%"=="bulk" goto :ensure_services
if /i "%CMD%"=="import-local" goto :ensure_services
goto :dispatch

:ensure_services
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8766); $c.Close(); exit 0 } catch { exit 1 }"
if errorlevel 1 (
  echo Ingestao/RAG desligados: iniciando o helper Jarvis Desktop...
  start "" /D "%HELPER_SRC%" "%HELPER_PY%" -m jarvis_desktop run
  powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ok=$false; for($i=0;$i -lt 90;$i++){ try { foreach($p in 8766,8767){ $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',$p); $c.Close() }; $ok=$true; break } catch { Start-Sleep -Seconds 1 } }; if(-not $ok){ exit 1 }"
  if errorlevel 1 (
    echo [erro] Ingestao/RAG nao responderam em 90 s. Veja .local\rag\logs\service.log
    pause
    exit /b 1
  )
)

:dispatch
if /i "%CMD%"=="bulk" (
  echo [1/2] Importando corpus local ^(SRD 5e XML + Notas da Janela de Contexto^)...
  "%RAG_PY%" -m rag_discovery --config .local\discovery.toml import-local --no-index
  echo.
  echo [2/2] Coletando documentacao oficial da web e indexando tudo no RAG...
  "%RAG_PY%" -m rag_discovery --config .local\discovery.toml run --no-llm
) else (
  "%RAG_PY%" -m rag_discovery --config .local\discovery.toml %*
)
set "CODE=%ERRORLEVEL%"
echo.
echo Fim (codigo %CODE%). Historico: "%RAG_PY%" -m rag_discovery list
timeout /t 15 >nul
exit /b %CODE%
