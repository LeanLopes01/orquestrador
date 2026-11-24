$ErrorActionPreference = 'Stop'
$target = 'C:\J.A.R.V.I.S\jarvis'
$manifest = Get-Content -LiteralPath (Join-Path $PSScriptRoot 'manifest.json') -Raw | ConvertFrom-Json
foreach ($entry in $manifest.files) {
    $source = Join-Path $PSScriptRoot $entry.path
    if ((Get-FileHash -LiteralPath $source).Hash.ToLower() -ne $entry.after) { throw "Pacote alterado: $($entry.path)" }
    $dest = Join-Path $target $entry.path
    if (Test-Path -LiteralPath $dest) {
        $actual = (Get-FileHash -LiteralPath $dest).Hash.ToLower()
        if ($actual -ne $entry.before -and $actual -ne $entry.after) { throw "Arquivo mudou: $dest" }
    } elseif ($entry.before) { throw "Arquivo original ausente: $dest" }
}
$backup = Join-Path $target ('backups\self-knowledge-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup | Out-Null
foreach ($entry in $manifest.files) {
    $dest = Join-Path $target $entry.path
    if (Test-Path -LiteralPath $dest) {
        $saved = Join-Path $backup $entry.path
        New-Item -ItemType Directory -Force -Path (Split-Path $saved) | Out-Null
        Copy-Item -LiteralPath $dest -Destination $saved
    }
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $entry.path) -Destination $dest
}
Write-Output "Instalado. Backup: $backup. O helper precisa reiniciar para anunciar system.inspect."
