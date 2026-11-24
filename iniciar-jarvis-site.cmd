@echo off
setlocal
cd /d "%~dp0"
if not exist dist\index.html (
  call npm.cmd run build
  if errorlevel 1 exit /b 1
)
start "" "http://127.0.0.1:1420/#home"
node services/server.mjs --with-helper
pause
