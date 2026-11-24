#!/bin/bash
set -euo pipefail
umask 077
[ "$(id -u)" = 0 ] || exit 1
version=${1:-}
[[ "$version" =~ ^[0-9]{8}T[0-9]{6}Z-evolution$ ]] || exit 1
backup="/var/backups/jarvis-evolution/$version"
key="/var/lib/jarvis-backup-keys/$version.key"
test -s "$key" && test -s "$backup/previous"
(cd "$backup" && sha256sum -c SHA256SUMS)
echo 'A restauração retorna contas, workflows e dados ao momento do backup.'
read -r -p 'Digite RESTAURAR para continuar: ' answer
[ "$answer" = RESTAURAR ] || exit 1
previous=$(cat "$backup/previous")
[[ "$previous" == /opt/jarvis/releases/* ]] && test -d "$previous"
C=jarvis-integrations-n8n-1
image=$(docker inspect "$C" --format '{{.Config.Image}}')
systemctl stop jarvis-control.service jarvis-agent.service
docker stop "$C" >/dev/null
# n8n is offline; replace the volume contents, including its original encryption key.
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$key" -in "$backup/n8n.tar.gz.enc" |
 docker run --rm -i --network none --volumes-from "$C" --user 0 --entrypoint sh "$image" -c 'find /home/node/.n8n -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +; tar -xzf - -C /home/node'
test ! -e "/var/lib/jarvis-control.before-restore-$version"
mv /var/lib/jarvis-control "/var/lib/jarvis-control.before-restore-$version"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$key" -in "$backup/control.tar.gz.enc" | tar -xzf - -C /
ln -sfn "$previous" /opt/jarvis/current.restore
mv -Tf /opt/jarvis/current.restore /opt/jarvis/current
docker start "$C" >/dev/null
systemctl start jarvis-control.service
curl --retry 10 --retry-connrefused --retry-delay 2 -fsS http://127.0.0.1:8090/v1/health
echo 'Backup restaurado. Dados posteriores ao backup não foram mesclados.'
