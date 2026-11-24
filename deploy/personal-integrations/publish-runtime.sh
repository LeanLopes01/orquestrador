#!/bin/bash
# Run with sudo. Installs the personal-data runtime: the gateway environment for
# jarvis-control, then release 20261024T011920Z-personal-runtime through jarvis-deploy (tests, voice smoke test,
# rollback). The runtime stays OFF until the accounts are verified.
set -euo pipefail
test "$(id -u)" = 0 || { echo 'Execute com sudo.'; exit 1; }
here=/home/user/jarvis-integrations
expected=/opt/jarvis/releases/20261023T205950Z-personal-connections
target=/opt/jarvis/releases/20261024T011920Z-personal-runtime
package=/tmp/jarvis-backend-20261024T011920Z-personal-runtime.tar.gz
secret=$here/secrets/gateway.secret
[ -s "$secret" ] || { echo 'Rode antes: bash setup-n8n.sh (como lean).'; exit 1; }

# Environment first: the new jarvis-control unit reads it when the release starts.
umask 077
tmp=$(mktemp /etc/jarvis/.personal.env.XXXXXX)
printf 'JARVIS_PERSONAL_N8N_URL=http://127.0.0.1:5679
JARVIS_PERSONAL_N8N_SECRET=%s
'     "$(tr -d '[:space:]' < "$secret")" > "$tmp"
chown root:jarvis-control "$tmp"
chmod 640 "$tmp"
mv -f "$tmp" /etc/jarvis/personal.env

active=$(readlink -f /opt/jarvis/current)
if [ "$active" != "$target" ]; then
    [ "$active" = "$expected" ] || { echo 'A release mudou. Rever o pacote antes de publicar.'; exit 1; }
    jarvis-deploy "$package" 6f6996e4e9ba2ad07b68aa2cf3b19531e98820a12242fa0e7ebb15baeb2f3b07
else
    systemctl restart jarvis-control.service
fi
sleep 2
curl -fsS http://127.0.0.1:8090/v1/health
echo
jarvis-control personal-status
echo
echo 'Runtime pessoal instalado e DESLIGADO. Depois de autorizar as contas no n8n:'
echo '  sudo jarvis-control personal-verify'
echo '  sudo jarvis-control personal-runtime on'
