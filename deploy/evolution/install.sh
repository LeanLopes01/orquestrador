#!/bin/bash
# Invoked only by atualizar-jarvis-servidor.cmd. No credentials in the payload.
set -euo pipefail
umask 077
[ "$(id -u)" = 0 ] || { echo 'Execute com sudo.'; exit 1; }
here=$(cd -- "$(dirname -- "$0")" && pwd)
cd "$here"
version=$(python3 -c 'import json;print(json.load(open("release.json"))["version"])')
expected=$(python3 -c 'import json;print(json.load(open("release.json"))["base_release"])')
hash=$(python3 -c 'import json;print(json.load(open("release.json"))["sha256"])')
[[ "$version" =~ ^[0-9]{8}T[0-9]{6}Z-evolution$ ]] || exit 1
active=$(readlink -f /opt/jarvis/current)
if [ "$active" = "/opt/jarvis/releases/$version" ]; then
  echo 'Esta release já está ativa. Nenhuma credencial foi reimportada.'; exit 0
fi
[ "$active" = "/opt/jarvis/releases/$expected" ] || { echo 'A release ativa mudou. Gere um pacote contra a base atual antes de publicar.'; exit 1; }
printf '%s  %s\n' "$hash" "jarvis-backend-$version.tar.gz" | sha256sum -c -
C=jarvis-integrations-n8n-1
integration=/home/user/jarvis-integrations
test -s "$integration/secrets/gateway.secret"
docker inspect "$C" >/dev/null
image=$(docker inspect "$C" --format '{{.Config.Image}}')
backup="/var/backups/jarvis-evolution/$version"
key="/var/lib/jarvis-backup-keys/$version.key"
[ ! -e "$backup" ] || { echo "Backup já existe: $backup. Use restaurar-jarvis-servidor.cmd ou revise a tentativa anterior."; exit 1; }
echo '[1/6] Verificando se o servidor está livre...'
if systemctl is-active --quiet jarvis-agent.service; then
  echo 'Encerre a chamada de voz e execute novamente. Nada foi atualizado.'
  exit 1
fi
python3 - <<'PY'
import sqlite3, pathlib
p=pathlib.Path('/var/lib/jarvis-control/orchestrator.db')
if p.exists():
    db=sqlite3.connect(f'file:{p}?mode=ro',uri=True)
    tables={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    for table in ('jobs','runs'):
        if table in tables and db.execute(f"SELECT count(*) FROM {table} WHERE state IN ('queued','preparing','running','planning','reviewing','waiting_input')").fetchone()[0]:
            raise SystemExit('Há um projeto em execução. Aguarde ou cancele antes de atualizar.')
PY
mkdir -p "$backup" /var/lib/jarvis-backup-keys
chmod 700 "$backup" /var/lib/jarvis-backup-keys
openssl rand -hex 32 > "$key"
chmod 600 "$key"
printf '%s\n' "$active" > "$backup/previous"
cp "$here/rollback.sh" "$backup/rollback.sh"
work_tmp=$(mktemp -d "$here/stage.XXXXXX")
rm -rf /home/user/.jarvis-import.* /home/user/.jarvis-restore-check.* /home/user/.jarvis-header.* 2>/dev/null || true
cleanup_tmp() {
  [[ -n "${work_tmp:-}" && "$work_tmp" == "$here"/stage.* ]] && rm -rf -- "$work_tmp" || true
}
restart_on_error() {
  cleanup_tmp
  systemctl start jarvis-control.service || true
  docker start "$C" >/dev/null || true
  echo "Atualização interrompida. Backup: $backup. Consulte o erro antes de repetir."
}
trap 'result=$?; if [ "$result" -ne 0 ]; then restart_on_error; else cleanup_tmp; fi' EXIT
systemctl stop jarvis-control.service
docker stop "$C" >/dev/null
echo '[2/6] Backup cifrado de dados, configuração e n8n...'
tar -czf - -C / etc/jarvis var/lib/jarvis-control home/lean/jarvis-integrations/compose.yaml |
  openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass "file:$key" -out "$backup/control.tar.gz.enc"
docker run --rm --network none --volumes-from "$C:ro" --user 0 --entrypoint tar "$image" -czf - -C /home/node .n8n |
  openssl enc -aes-256-cbc -salt -pbkdf2 -iter 200000 -pass "file:$key" -out "$backup/n8n.tar.gz.enc"
(cd "$backup" && sha256sum *.enc > SHA256SUMS)
# Verify a restore into an isolated directory before touching the original volume.
verify="$work_tmp/restore-check"
mkdir -p "$verify"
openssl enc -d -aes-256-cbc -pbkdf2 -iter 200000 -pass "file:$key" -in "$backup/n8n.tar.gz.enc" | tar -xzf - -C "$verify"
python3 - "$verify" <<'PY'
import pathlib,sqlite3,sys
p=pathlib.Path(sys.argv[1])/'.n8n'
assert (p/'config').is_file(), 'Chave n8n ausente no backup'
db=sqlite3.connect(f'file:{p / "database.sqlite"}?mode=ro',uri=True)
assert db.execute('PRAGMA quick_check').fetchone()[0]=='ok', 'Backup SQLite inválido'
db.close()
PY
rm -rf -- "$verify"
docker start "$C" >/dev/null
wait_ready() { for i in $(seq 1 90); do curl -fs http://127.0.0.1:5679/healthz/readiness >/dev/null && return; sleep 2; done; return 1; }
wait_ready
echo '[3/6] Instalando conectores privados e preservando credenciais...'
# Snap Docker blocks host paths under $HOME/.* for `docker cp`; stream via stdin instead.
docker exec -u 0 "$C" rm -rf /home/node/.n8n/.jarvis-evolution
docker exec -u 0 "$C" mkdir -p /home/node/.n8n/custom/jarvis /home/node/.n8n/.jarvis-evolution
tar -cf - -C n8n-nodes . | docker exec -i -u 0 "$C" tar -xf - -C /home/node/.n8n/custom/jarvis
docker exec -u 0 "$C" chown -R node:node /home/node/.n8n/custom/jarvis /home/node/.n8n/.jarvis-evolution
docker restart "$C" >/dev/null
wait_ready
docker exec "$C" n8n export:credentials --all --output=/home/node/.n8n/.jarvis-evolution/existing.json >/dev/null
ids=$(docker exec "$C" node -e 'for(const c of require("/home/node/.n8n/.jarvis-evolution/existing.json"))console.log(c.id)')
docker exec "$C" rm -f /home/node/.n8n/.jarvis-evolution/existing.json
stage="$work_tmp/import-creds"
mkdir -p "$stage"
python3 - "$stage" "$ids" <<'PY'
import json,secrets,sys,pathlib
out=pathlib.Path(sys.argv[1]);existing=set(sys.argv[2].split());items=[]
for entry in json.load(open('registry.json'))['entries']:
    if entry['credential_id'] not in existing:
        items.append({'id':entry['credential_id'],'name':'Jarvis · '+entry['name'],'type':'jarvisConnection','data':{'configuration':'{}','stateSecret':secrets.token_hex(32),'origins':'','privateNetwork':False}})
(out/'credentials.json').write_text(json.dumps(items))
print('Novas credenciais protegidas:',len(items),'(existentes preservadas)')
PY
if [ "$(python3 -c "import json;print(len(json.load(open('$stage/credentials.json'))))")" != 0 ]; then
  docker exec -i -u node "$C" sh -c 'cat > /home/node/.n8n/.jarvis-evolution/credentials.json' < "$stage/credentials.json"
  docker exec "$C" n8n import:credentials --input=/home/node/.n8n/.jarvis-evolution/credentials.json >/dev/null
  docker exec "$C" rm -f /home/node/.n8n/.jarvis-evolution/credentials.json
fi
rm -rf -- "$stage"
# Existing catalog workflows may contain user-selected OAuth mappings: preserve them.
docker exec "$C" n8n export:workflow --all --output=/home/node/.n8n/.jarvis-evolution/workflows.json >/dev/null
existing=$(docker exec "$C" node -e 'for(const w of require("/home/node/.n8n/.jarvis-evolution/workflows.json"))console.log(w.id)')
docker exec "$C" rm -f /home/node/.n8n/.jarvis-evolution/workflows.json
stage="$work_tmp/import-workflows"
mkdir -p "$stage"
python3 - "$stage" "$existing" <<'PY'
import json,pathlib,sys
out=pathlib.Path(sys.argv[1]);existing=set(sys.argv[2].split())
items=[json.loads(p.read_text()) for p in sorted(pathlib.Path('workflows').glob('*.json'))]
items=[item for item in items if item['id'] not in existing]
(out/'workflows.json').write_text(json.dumps(items))
(out/'ids').write_text('\n'.join(item['id'] for item in items))
print('Novos workflows:',len(items),'(existentes preservados)')
PY
if [ -s "$stage/ids" ]; then
  docker exec -i -u node "$C" sh -c 'cat > /home/node/.n8n/.jarvis-evolution/workflows.json' < "$stage/workflows.json"
  docker exec "$C" n8n import:workflow --input=/home/node/.n8n/.jarvis-evolution/workflows.json >/dev/null
  while IFS= read -r id || [ -n "$id" ]; do
    echo "Publicando conector $id..."
    docker exec "$C" n8n publish:workflow --id="$id" >/dev/null
  done < "$stage/ids"
  docker exec "$C" rm -f /home/node/.n8n/.jarvis-evolution/workflows.json
fi
rm -rf -- "$stage"
# Apply the reviewed Notion API fix to the existing personal gateway.
docker exec -i -u node "$C" sh -c 'cat > /home/node/.n8n/.jarvis-evolution/notion.json' < notion.json
docker exec "$C" n8n import:workflow --input=/home/node/.n8n/.jarvis-evolution/notion.json >/dev/null
docker exec "$C" rm -f /home/node/.n8n/.jarvis-evolution/notion.json
notion_id=$(python3 -c 'import json;print(json.load(open("notion.json"))["id"])')
docker exec "$C" n8n publish:workflow --id="$notion_id" >/dev/null
docker restart "$C" >/dev/null
wait_ready
echo '[4/6] Testando proteção dos webhooks...'
for slug in $(python3 -c 'import json;print(" ".join(e["id"] for e in json.load(open("registry.json"))["entries"]))'); do
  for attempt in $(seq 1 30); do
    status=$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' -d '{}' "http://127.0.0.1:5679/webhook/jarvis-catalog/$slug")
    [ "$status" = 403 ] && break
    sleep 2
  done
  [ "$status" = 403 ] || { echo "Webhook $slug recusou com código inesperado: $status"; exit 1; }
done
header="$work_tmp/header.txt"
printf 'X-Jarvis-Gateway: %s\n' "$(cat "$integration/secrets/gateway.secret")" > "$header"
if ! curl -fsS -X POST -H @"$header" -H 'Content-Type: application/json' -d '{"tool":"get_time","arguments":{"timezone":"America/Sao_Paulo"}}' http://127.0.0.1:5679/webhook/jarvis-catalog/timezone-world-clock |
 python3 -c 'import json,sys;v=json.load(sys.stdin);s=json.dumps(v);assert "Paulo" in s and "\"error\"" not in s, "Conector de teste falhou"'; then
  rm -f -- "$header"
  echo 'O nó personalizado não passou no teste real. O backend não será trocado.'
  exit 1
fi
rm -f -- "$header"
echo '[5/6] Instalando backend, site e APK principal com testes e rollback...'
# jarvis-deploy removes its input on success; keep the original bundle reviewable.
cp "jarvis-backend-$version.tar.gz" "/tmp/jarvis-backend-$version.tar.gz"
jarvis-deploy "/tmp/jarvis-backend-$version.tar.gz" "$hash"
echo '[6/6] Verificando serviços e contas...'
health_ok=0
for _ in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8090/v1/health && echo; then
    health_ok=1
    break
  fi
  sleep 1
done
[ "$health_ok" = 1 ] || { echo 'jarvis-control não respondeu em 127.0.0.1:8090/v1/health a tempo.'; exit 1; }
curl -fsS http://127.0.0.1:8090/ >/dev/null
jarvis-control personal-verify || echo 'Há contas que precisam de autorização. Veja o guia CONTAS.md.'
jarvis-control personal-status
echo "Instalado: $version. Site: https://your-jarvis-api.example.com/"
echo "Backup cifrado: $backup. Chave separada: $key"
echo 'O S23 não foi enviado. Conectores novos continuam pausados no Jarvis até sua configuração.'
