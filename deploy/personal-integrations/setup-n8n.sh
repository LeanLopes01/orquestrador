#!/bin/bash
# Prepares the Jarvis n8n instance. Run as lean (docker group), no sudo:
#   bash setup-n8n.sh
# Applies compose.yaml (callback URL), creates the gateway secret once, imports the
# credential skeletons that do not exist yet (never overwrites one that was already
# authorised), imports and publishes the read-only proxy workflows, then checks the
# webhook refuses calls without the secret. Safe to repeat.
set -euo pipefail
cd "$(dirname "$0")"
C=jarvis-integrations-n8n-1
umask 077

wait_ready() {
    local i
    for i in $(seq 1 90); do
        curl -fs http://127.0.0.1:5679/healthz/readiness >/dev/null && return 0
        sleep 2
    done
    echo 'n8n did not become ready.' >&2
    exit 1
}

mkdir -p secrets
[ -s secrets/gateway.secret ] || openssl rand -hex 32 > secrets/gateway.secret
docker compose -f compose.yaml up -d
wait_ready

# Snap Docker cannot read /tmp: stage under this directory and remove afterwards.
stage=$(mktemp -d "$PWD/.import.XXXXXX")
trap 'rm -rf "$stage"; docker exec "$C" rm -rf /home/node/.n8n/.jarvis-import' EXIT
docker exec "$C" sh -c 'rm -rf /home/node/.n8n/.jarvis-import && mkdir -m 700 /home/node/.n8n/.jarvis-import'

# IDs only: the export holds encrypted data and is deleted at once.
existing=$(docker exec "$C" sh -c '
    f=/home/node/.n8n/.jarvis-import/ids.json
    n8n export:credentials --all --output="$f" >/dev/null 2>&1 || echo "[]" > "$f"
    node -e "for (const c of require(process.argv[1])) console.log(c.id)" "$f"
    rm -f "$f"')
python3 - "$stage/credentials.json" "$existing" <<'PY'
import json, sys
out, existing = sys.argv[1], set(sys.argv[2].split())
secret = open('secrets/gateway.secret').read().strip()
items = []
for item in json.load(open('n8n/credentials.template.json')):
    if item['id'] in existing:
        continue
    if item['type'] == 'httpHeaderAuth':
        item['data']['value'] = secret
    items.append(item)
json.dump(items, open(out, 'w'))
print('credentials to create:', ', '.join(i['name'] for i in items) or 'none')
PY
cp n8n/workflows/*.json "$stage/"
docker cp "$stage/." "$C:/home/node/.n8n/.jarvis-import/"
if [ "$(python3 -c "import json;print(len(json.load(open('$stage/credentials.json'))))")" != 0 ]; then
    docker exec "$C" n8n import:credentials --input=/home/node/.n8n/.jarvis-import/credentials.json | tail -1
fi
for account in google_a google_b outlook notion; do
    docker exec "$C" n8n import:workflow --input="/home/node/.n8n/.jarvis-import/$account.json" | tail -1
done
for id in $(python3 -c "import json,glob;print(' '.join(json.load(open(f))['id'] for f in sorted(glob.glob('n8n/workflows/*.json'))))"); do
    docker exec "$C" n8n publish:workflow --id="$id" >/dev/null
done
docker restart "$C" >/dev/null
wait_ready
for i in $(seq 1 30); do
    docker logs --since 5m "$C" 2>&1 | grep -q 'Finished building workflow dependency' && break
    sleep 2
done

printf 'X-Jarvis-Gateway: %s\n' "$(cat secrets/gateway.secret)" > "$stage/header"
code() { curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' "$@"; }
for path in jarvis-google-a jarvis-google-b jarvis-outlook jarvis-notion; do
    without=$(code -d '{}' "http://127.0.0.1:5679/webhook/$path")
    refused=$(code -H @"$stage/header" -d '{"method":"DELETE","path":"/x"}' "http://127.0.0.1:5679/webhook/$path")
    echo "$path: without secret $without (expect 403), outside the policy $refused (expect 500)"
    [ "$without" = 403 ] && [ "$refused" = 500 ] || { echo 'Unexpected answer.' >&2; exit 1; }
done
echo 'n8n ready. Next: owner, OAuth clients and sign-in (see README.md).'
