@echo off
setlocal
cd /d "%~dp0"
if not exist node_modules (
  echo Instalando dependencias da interface...
  call npm.cmd ci --cache .local/npm-cache
  if errorlevel 1 exit /b 1
)
echo Abra http://127.0.0.1:1420 no navegador.
echo Para encerrar, pressione Ctrl+C nesta janela.
call npm.cmd run dev
