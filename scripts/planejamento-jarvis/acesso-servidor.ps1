[CmdletBinding()]
param(
    [ValidateSet('Diagnostico', 'Painel')]
    [string]$Acao = 'Diagnostico',
    [ValidatePattern('^[A-Za-z0-9_.-]+@[A-Za-z0-9][A-Za-z0-9.-]*$')]
    [string]$Servidor = 'user@your-server-ip',
    [switch]$ValidarSomente
)

$ErrorActionPreference = 'Stop'

if ($ValidarSomente) {
    Write-Host "Parametros validos. Acao: $Acao. Servidor: $Servidor. Nenhuma conexao realizada."
    return
}

$sshJarvis = Get-Command ssh.exe -ErrorAction SilentlyContinue
if (-not $sshJarvis) {
    throw 'OpenSSH Client nao encontrado. Habilite o cliente OpenSSH do Windows antes de executar.'
}

$opcoesJarvis = @('-o', 'ConnectTimeout=10', '-o', 'StrictHostKeyChecking=ask')
if ($Acao -eq 'Painel') {
    Write-Host 'Tunel para o n8n existente. Depois de autenticar, abra http://localhost:5679 no navegador deste PC.'
    Write-Host 'Mantenha esta janela aberta. Ctrl+C encerra o tunel. Nenhuma configuracao sera alterada.'
    & $sshJarvis.Source @opcoesJarvis -o ExitOnForwardFailure=yes -N -L '127.0.0.1:5679:127.0.0.1:5679' $Servidor
    if ($LASTEXITCODE -ne 0) { throw "Tunel encerrado com codigo $LASTEXITCODE. Confira rede, login e porta local 5679." }
    return
}

Write-Host 'Diagnostico de leitura. Nao publica, nao reinicia e nao ativa integracoes.'
Write-Host 'O SSH/sudo pode pedir senha no terminal. O status pode conter identificadores pessoais.'
# Fixed remote command: no user-provided shell fragments, no environment/secret dumps.
$comandoJarvis = @'
failed=0
printf '\n== Release ativa ==\n'
readlink -f /opt/jarvis/current || failed=1
printf '\n== Jarvis Control ==\n'
systemctl is-active jarvis-control.service || failed=1
printf '\n== Saude n8n ==\n'
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:5679/healthz/readiness || failed=1
printf '\n== Contas e runtime (somente status) ==\n'
sudo jarvis-control personal-status || failed=1
printf '\n== Fim: nenhuma configuracao alterada ==\n'
exit "$failed"
'@
$comandoJarvis = $comandoJarvis.Replace("`r", '')
& $sshJarvis.Source @opcoesJarvis -t $Servidor $comandoJarvis
if ($LASTEXITCODE -ne 0) {
    throw "Um ou mais checks falharam (codigo $LASTEXITCODE). A saida acima identifica a camada; nenhuma correcao foi aplicada."
}
