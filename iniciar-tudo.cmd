@echo off
setlocal
rem Inicia tudo no PC principal com dois cliques:
rem   1) helper Jarvis Desktop (conecta o PC ao servidor Jarvis e aos celulares)
rem   2) RAG local + ingestao (sobem e descem junto com o helper)
rem   3) relatorio automatico do DiceVTT (runner local, sobe junto com o helper)
rem   4) interface do Orquestrador em http://127.0.0.1:1420/#reports
rem Para desligar tudo: parar-tudo.cmd (ou Ctrl+C aqui fecha so a interface).
cd /d "%~dp0"
title Orquestrador DiceVTT - helper + RAG + interface

set "HELPER_PY=C:\J.A.R.V.I.S\jarvis\.venv\Scripts\pythonw.exe"
set "HELPER_SRC=C:\J.A.R.V.I.S\jarvis\src"
set "RAG_PY=%~dp0.venv-rag\Scripts\python.exe"
set "AUDIT_PYW=%~dp0.venv-rag\Scripts\pythonw.exe"

if not exist "%HELPER_PY%" (
  echo [erro] Helper Jarvis Desktop nao encontrado em %HELPER_PY%
  pause
  exit /b 1
)
if not exist "%RAG_PY%" (
  echo [aviso] Ambiente do RAG ^(.venv-rag^) nao encontrado: o helper sobe sem o RAG.
  echo         Veja services\rag\README.md para instalar.
)

echo [1/4] Iniciando o helper Jarvis Desktop (o RAG e a ingestao sobem junto)...
rem Uma segunda copia do helper encerra sozinha se ele ja estiver rodando.
start "" /D "%HELPER_SRC%" "%HELPER_PY%" -m jarvis_desktop run

echo [2/4] Pedindo o relatorio automatico do DiceVTT em segundo plano...
rem Antes de qualquer espera e da bifurcacao "interface ja aberta": o pedido nunca bloqueia a UI.
rem request-startup cria um startup_id, espera o runner ate 30 s e registra tudo em
rem .local\audits\logs\startup.log. Desligado nas preferencias = registrado como desativado.
set "AUDIT_OK="
if exist "%AUDIT_PYW%" if exist "%~dp0.local\diagnostics.toml" set "AUDIT_OK=1"
if defined AUDIT_OK (
  start "" "%AUDIT_PYW%" -m dicevtt_diagnostics --config ".local\diagnostics.toml" request-startup
  echo       Pedido enviado. O resultado aparece em Relatorios em ate 2 minutos.
) else (
  echo       [aviso] Runner de relatorios nao configurado: nenhum relatorio pedido.
  echo       Veja services\diagnostics\README.md.
)

echo [3/4] Aguardando o RAG local responder em 127.0.0.1:8767 (ate 90 s)...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$ok=$false; for($i=0;$i -lt 90;$i++){ try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8767); $c.Close(); $ok=$true; break } catch { Start-Sleep -Seconds 1 } }; if($ok){ Write-Host '      RAG online. A indexacao inicial e o watcher continuam em segundo plano.' } else { Write-Host '      RAG ainda nao respondeu. Log: .local\rag\logs\service.log' }"

echo [4/4] Abrindo a interface do Orquestrador...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "try { $c=New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',1420); $c.Close(); exit 0 } catch { exit 1 }"
if not errorlevel 1 (
  echo       A interface ja esta rodando em http://127.0.0.1:1420
  start "" "http://127.0.0.1:1420/#reports"
  echo.
  echo Tudo ligado. Pode fechar esta janela; para desligar use parar-tudo.cmd.
  timeout /t 8 >nul
  exit /b 0
)

if not exist node_modules (
  echo       Instalando dependencias da interface...
  call npm.cmd ci --cache .local/npm-cache
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
start "" /min powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; Start-Process 'http://127.0.0.1:1420/#reports'"
echo.
echo Interface em http://127.0.0.1:1420  (Relatorios: #reports  ^|  RAG: #rag  ^|  Projects: #projects)
echo Mantenha esta janela aberta. Ctrl+C fecha so a interface;
echo para desligar helper + RAG + interface use parar-tudo.cmd.
echo.
call npm.cmd run dev
