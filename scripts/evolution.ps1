param([ValidateSet('deploy','rollback','grant','verify')][string]$Action='deploy')
$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
$releasePath=Join-Path $root 'artifacts\server\release.json'
$hostName='user@your-server-ip'
function Check-Exit([string]$operation) { if($LASTEXITCODE -ne 0){throw "$operation nao foi concluida (codigo $LASTEXITCODE). O motivo aparece nas linhas acima. Nenhuma tentativa automatica sera feita."} }
function Test-PendingWork {
    $python='C:\J.A.R.V.I.S\jarvis\.venv\Scripts\python.exe'
    $bridge=Join-Path $root 'services\jarvis-request.py'
    if(-not (Test-Path -LiteralPath $python) -or -not (Test-Path -LiteralPath $bridge)){return $false}
    try {
        $request='{"method":"GET","path":"/v1/orchestration/active"}'
        $raw=$request | & $python -X utf8 $bridge
        if($LASTEXITCODE -ne 0){throw 'Consulta local indisponivel'}
        $response=$raw | ConvertFrom-Json
        if($response.status -ne 200){throw 'Consulta de atividades indisponivel'}
        if(@($response.body.active).Count -eq 0){return $false}
        Write-Host ''
        Write-Host 'ATUALIZACAO ADIADA: o Jarvis tem trabalho pendente.' -ForegroundColor Yellow
        foreach($item in $response.body.active){
            Write-Host ("Tipo: {0} | Estado: {1} | Execucao: {2} | Conversa: {3}" -f $item.kind,$item.state,$item.run_id,$item.conversation_id)
        }
        Write-Host 'Abra Projetos no Jarvis e aguarde a conclusao ou cancele a execucao correspondente.'
        Write-Host 'Depois execute este atualizador novamente. Nenhum upload ou alteracao foi feito nesta tentativa.'
        return $true
    } catch {
        Write-Host 'Nao foi possivel consultar atividades pelo PC. A verificacao obrigatoria sera feita no servidor antes de instalar.'
        return $false
    }
}
if($Action -eq 'grant') {
    & ssh -t $hostName 'sudo jarvis-control devices'
    Check-Exit 'Consulta de dispositivos'
    $device=Read-Host 'Cole o ID completo do navegador ou PC que deseja autorizar'
    if($device -notmatch '^[a-f0-9]{32}$'){throw 'ID invalido'}
    & ssh -t $hostName "sudo jarvis-control work $device && sudo jarvis-control personal-access $device"
    Check-Exit 'Autorizacao'
    exit 0
}
if($Action -eq 'verify') {
    $account=Read-Host 'Conta: google_a, google_b, notion ou outlook'
    if($account -notmatch '^(google_a|google_b|notion|outlook)$'){throw 'Conta invalida'}
    & ssh -t $hostName "sudo jarvis-control personal-verify $account && sudo jarvis-control personal-status"
    Check-Exit 'Verificacao'
    $enable=Read-Host 'Habilitar consultas pessoais dos servicos verificados? Digite SIM'
    if($enable -eq 'SIM'){& ssh -t $hostName 'sudo jarvis-control personal-runtime on'; Check-Exit 'Ativacao'}
    exit 0
}
$release=Get-Content -LiteralPath $releasePath -Raw -Encoding UTF8 | ConvertFrom-Json
$version=$release.version
if($version -notmatch '^\d{8}T\d{6}Z-evolution$'){throw 'Versao invalida'}
if($Action -eq 'rollback') {
    & ssh -t $hostName "sudo bash /var/backups/jarvis-evolution/$version/rollback.sh $version"
    Check-Exit 'Restauracao'
    exit 0
}
if(Test-PendingWork){exit 0}
$bundle=Join-Path (Split-Path $releasePath) $release.bundle
if((Get-FileHash -LiteralPath $bundle -Algorithm SHA256).Hash.ToLowerInvariant() -ne $release.bundle_sha256){throw 'Hash do pacote local nao confere'}
Write-Host "Pacote: $version. Inclui backend, site, conectores e APK principal. O S23 fica local."
& ssh -o BatchMode=yes $hostName "umask 077 && mkdir -p jarvis-updates/$version"
Check-Exit 'Preparacao do upload'
Push-Location (Split-Path $bundle)
try { & scp -- $release.bundle "${hostName}:jarvis-updates/$version/"; Check-Exit 'Upload' } finally { Pop-Location }
$name=$release.bundle
$hash=$release.bundle_sha256
if($name -notmatch '^jarvis-update-\d{8}T\d{6}Z-evolution\.tar\.gz$' -or $hash -notmatch '^[a-f0-9]{64}$'){throw 'Manifesto invalido'}
& ssh -t $hostName "cd jarvis-updates/$version && printf '%s  %s\n' '$hash' '$name' | sha256sum -c - && tar -xzf '$name' && sudo bash install.sh"
Check-Exit 'Implantacao'
Write-Host 'Atualizacao concluida. Abra o site e configure as contas seguindo docs/planejamento-jarvis/ENTREGA.md.'
