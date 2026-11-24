# Execute no seu PowerShell. A senha sudo sera solicitada pelo SSH, sem passar pelo chat.
$ErrorActionPreference = 'Stop'
ssh -t user@your-server-ip 'sudo jarvis-deploy /tmp/jarvis-backend-20261021T005253Z-companion.tar.gz a57034194077b81188ae39ea1f3ebdf0685e254515afb98ded6a09b479c9caef && sudo jarvis-control master 931e18105a3641f98948555713e79641 --off && sudo jarvis-control work 931e18105a3641f98948555713e79641 && sudo jarvis-control work 79652afcd37f48148e028142965d4caf && sudo jarvis-control devices'
if ($LASTEXITCODE -ne 0) { throw 'Publicacao nao concluida. Confira a mensagem do servidor.' }
Write-Host 'Servidor atualizado. S23 FE liberado como companion; Motorola preservado.'