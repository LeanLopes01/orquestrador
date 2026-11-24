$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$installer=Join-Path $root 'artifacts\windows\Jarvis_0.3.0_x64-setup.exe'
if(-not (Test-Path -LiteralPath $installer)){throw 'Instalador nao encontrado em artifacts/windows'}
$manifest=Get-Content -LiteralPath (Join-Path $root 'artifacts\windows\release.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if($manifest.package -ne (Split-Path $installer -Leaf) -or (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant() -ne $manifest.sha256){throw 'Hash do instalador nao confere. Nenhuma alteracao foi feita.'}
$backup=Join-Path $root '.local\evolution\desktop-startup-backup'
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$startup=Join-Path ([Environment]::GetFolderPath('Startup')) 'JarvisDesktop.vbs'
if(Test-Path -LiteralPath $startup){Copy-Item -LiteralPath $startup -Destination (Join-Path $backup 'JarvisDesktop.vbs')}
Push-Location 'C:\J.A.R.V.I.S\jarvis\src'
try {
    & 'C:\J.A.R.V.I.S\jarvis\.venv\Scripts\python.exe' -m jarvis_desktop stop
    if($LASTEXITCODE -ne 0){throw 'Ha tarefa ativa ou o helper nao encerrou. Aguarde/cancele no Jarvis antes de instalar.'}
    & 'C:\J.A.R.V.I.S\jarvis\.venv\Scripts\python.exe' -m jarvis_desktop uninstall-startup
    if($LASTEXITCODE -ne 0){throw 'Nao foi possivel ajustar a inicializacao'}
} finally {Pop-Location}
# The installer is the interactive application the user explicitly opened.
$process=Start-Process -FilePath $installer -Wait -PassThru
if($process.ExitCode -ne 0){throw 'Instalador nao concluiu. Backup do inicio automatico em .local/evolution/desktop-startup-backup'}
Write-Host 'Abra Jarvis pelo menu Iniciar. O helper e o RAG passam a acompanhar a sessao do aplicativo.'
