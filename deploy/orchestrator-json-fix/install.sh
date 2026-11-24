#!/bin/bash
# Targeted, reversible API hotfix. Does not edit the database or restart voice.
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Execute com sudo.' >&2; exit 1; }
bundle=$(cd -- "$(dirname -- "$0")" && pwd)
current=$(readlink -f /opt/jarvis/current)
target=$current/src/jarvis_control/orchestrator.py
before=5ba53730ffafd87e10a04f781eae42d79eb029c8e2d4ea5250e36ff1772c4b71
after=b7db7375616ead60ce6e1ae7fdc3269e6580a058a6afabd102d11dd79261a5b1
actual=$(sha256sum "$target" | cut -d ' ' -f 1)
echo "$after  $bundle/orchestrator.py" | sha256sum -c -
if [ "$actual" = "$after" ]; then
    echo 'Correcao ja instalada.'
    runuser -u jarvis-control -- env PYTHONDONTWRITEBYTECODE=1 \
        "$current/.venv/bin/python" - "$current/src" < "$bundle/verify_saved.py"
    exit 0
fi
[ "$actual" = "$before" ] || { echo 'Versao mudou: nada foi alterado.' >&2; exit 1; }
stage=$(mktemp -d /tmp/jarvis-json-check.XXXXXX)
chmod 755 "$stage"
cp -a "$current/src" "$stage/src"
install -m 644 "$bundle/orchestrator.py" "$stage/src/jarvis_control/orchestrator.py"
mkdir "$stage/tests"
install -m 644 "$bundle/test_orchestrator_result_json.py" "$stage/tests/"
cd "$stage"
echo 'Validando regressao e leitura do banco real (somente leitura)...'
runuser -u jarvis-control -- env PYTHONDONTWRITEBYTECODE=1 \
    "$current/.venv/bin/python" -m pytest -q -p no:cacheprovider \
    -o asyncio_mode=auto tests/test_orchestrator_result_json.py
runuser -u jarvis-control -- env PYTHONDONTWRITEBYTECODE=1 \
    "$current/.venv/bin/python" - "$stage/src" < "$bundle/verify_saved.py"
backup=/var/backups/jarvis-json-fix/$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 700 "$backup"
cp -p "$target" "$backup/orchestrator.py"
printf '%s\n' "$target" > "$backup/target.txt"
rollback() {
    echo "Falha na ativacao; restaurando $backup/orchestrator.py" >&2
    install -m 644 "$backup/orchestrator.py" "$target.new"
    mv -f "$target.new" "$target"
    systemctl restart jarvis-control
}
trap rollback ERR
install -m 644 "$bundle/orchestrator.py" "$target.new"
mv -f "$target.new" "$target"
# Persist the regression test alongside the active release for future checks.
install -m 644 "$bundle/test_orchestrator_result_json.py" "$current/tests/"
systemctl restart jarvis-control
curl --fail --silent --show-error --retry 15 --retry-connrefused --retry-delay 1 \
    --max-time 3 http://127.0.0.1:8090/v1/health
runuser -u jarvis-control -- env PYTHONDONTWRITEBYTECODE=1 \
    "$current/.venv/bin/python" - "$current/src" < "$bundle/verify_saved.py"
trap - ERR
echo
echo "Correcao ativa. Backup: $backup. Atualize Projects no Orquestrador."
