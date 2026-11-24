#!/bin/bash
# Encrypted backup of the n8n volume (database and encryption key), and a restore
# test. Run as lean (docker group), in a terminal: gpg asks for the passphrase.
#   bash backup-n8n.sh                  stop n8n briefly, archive, encrypt, start
#   bash backup-n8n.sh --verify FILE    restore FILE into a throwaway n8n and check it
# Keep the passphrase outside this server. Without it the backup is useless; with
# the backup and the passphrase, anyone can use the stored authorisations.
# GPG_PASSPHRASE_FILE=path skips the prompt (used only for the procedure test).
set -euo pipefail
cd "$(dirname "$0")"
C=jarvis-integrations-n8n-1
VOLUME=jarvis-integrations_n8n_data
IMAGE=$(docker inspect --format '{{.Config.Image}}' "$C")
TEST=jarvis-n8n-restore-test
umask 077
mkdir -p backups
gpg_args=()
if [ -n "${GPG_PASSPHRASE_FILE:-}" ]; then
    gpg_args=(--batch --pinentry-mode loopback --passphrase-file "$GPG_PASSPHRASE_FILE")
fi

if [ "${1:-}" = --verify ]; then
    file=${2:?backup file}
    scratch=jarvis-n8n-restore-$$
    docker volume create "$scratch" >/dev/null
    trap 'docker rm -f "$TEST" >/dev/null 2>&1 || true; docker volume rm "$scratch" >/dev/null 2>&1 || true' EXIT
    gpg "${gpg_args[@]}" --quiet --decrypt "$file" |
        docker run --rm -i --user 0 -v "$scratch:/data" --entrypoint tar "$IMAGE" -xzf - -C /data
    docker run -d --name "$TEST" -v "$scratch:/home/node/.n8n" \
        -e N8N_DIAGNOSTICS_ENABLED=false -e N8N_ENFORCE_SETTINGS_FILE_PERMISSIONS=true \
        "$IMAGE" >/dev/null
    for i in $(seq 1 90); do
        docker exec "$TEST" node -e "fetch('http://127.0.0.1:5678/healthz/readiness').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))" 2>/dev/null && break
        [ "$i" = 90 ] && { docker logs "$TEST" 2>&1 | tail -20; echo 'restore did not start' >&2; exit 1; }
        sleep 2
    done
    workflows=$(docker exec "$TEST" n8n list:workflow 2>/dev/null | grep -c '|' || true)
    # Decrypting proves the restored key matches the restored credentials.
    credentials=$(docker exec "$TEST" sh -c '
        f=/home/node/.n8n/.restore-check.json
        n8n export:credentials --all --decrypted --output="$f" >/dev/null 2>&1 || exit 1
        node -e "const c=require(process.argv[1]); console.log(c.filter(x=>x.data&&typeof x.data===\"object\").length)" "$f"
        rm -f "$f"')
    echo "restore OK: $workflows workflows, $credentials credentials decrypted with the restored key"
    exit 0
fi

out="backups/n8n-$(date -u +%Y%m%dT%H%M%SZ).tar.gz.gpg"
docker stop "$C" >/dev/null
trap 'docker start "$C" >/dev/null' EXIT
docker run --rm -v "$VOLUME:/data:ro" --entrypoint tar "$IMAGE" -czf - -C /data . |
    gpg "${gpg_args[@]}" --symmetric --cipher-algo AES256 -o "$out"
echo "backup: $PWD/$out"
echo "Test it now: bash backup-n8n.sh --verify $out"
