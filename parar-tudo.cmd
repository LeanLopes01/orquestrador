@echo off
setlocal
rem Desliga RAG + ingestao + relatorios (encerramento limpo), o helper Jarvis Desktop e a interface.
rem Um relatorio em andamento fica salvo como interrupted; nada e reexecutado sozinho.
cd /d "%~dp0"
title Orquestrador DiceVTT - desligando

echo [1/2] Desligando RAG, ingestao, relatorios e helper Jarvis Desktop...
pushd "C:\J.A.R.V.I.S\jarvis\src"
"C:\J.A.R.V.I.S\jarvis\.venv\Scripts\python.exe" -m jarvis_desktop stop
if errorlevel 3 if not errorlevel 4 (
  echo.
  echo Um agente do orquestrador ainda esta trabalhando ^(lista acima^).
  echo Desligar agora descarta o trabalho que ele estiver terminando.
  choice /c SN /n /m "Desligar mesmo assim? [S/N] "
  if errorlevel 2 (
    popd
    echo Nada foi desligado.
    timeout /t 6 >nul
    exit /b 1
  )
  "C:\J.A.R.V.I.S\jarvis\.venv\Scripts\python.exe" -m jarvis_desktop stop --force
)
popd

echo [2/2] Desligando a interface (porta 1420), somente se for o Vite do Orquestrador...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$l=Get-NetTCPConnection -LocalPort 1420 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if($l){ $p=Get-CimInstance Win32_Process -Filter \"ProcessId=$($l.OwningProcess)\"; if($p.Name -eq 'node.exe' -and $p.CommandLine -match 'vite'){ Stop-Process -Id $p.ProcessId; Write-Host '      Interface desligada.' } else { Write-Host '      A porta 1420 pertence a outro programa; nada foi encerrado.' } } else { Write-Host '      A interface ja estava desligada.' }"

echo.
echo Tudo desligado. Para ligar de novo: iniciar-tudo.cmd
timeout /t 6 >nul
