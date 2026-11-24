#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Execute com sudo.'; exit 1; }
bundle=$(cd -- "$(dirname -- "$0")" && pwd)
current=$(readlink -f /opt/jarvis/current)
case "$current" in /opt/jarvis/releases/*) ;; *) echo 'Release inesperada'; exit 1;; esac
if systemctl is-active --quiet jarvis-agent; then
  echo 'Encerre a chamada de voz antes de instalar. Nada alterado.'; exit 1
fi
# Validate every input and original before touching the release.
python3 - "$bundle" "$current" <<'PY'
import hashlib,json,pathlib,sys
bundle,root=map(pathlib.Path,sys.argv[1:])
for item in json.loads((bundle/'manifest.json').read_text())['files']:
    path=item['path']
    if path not in {'src/agent.py','src/project_knowledge.py','src/system_knowledge.py','src/jarvis_desktop/actions.py','src/jarvis_desktop/system_inspection.py','tests/test_system_knowledge.py'}:
        raise SystemExit('Caminho inesperado')
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
    if digest(bundle/path)!=item['after']: raise SystemExit('Pacote alterado: '+path)
    if digest(root/path) not in (item['before'],item['after']): raise SystemExit('Base mudou: '+path)
PY
stage=$(mktemp -d /tmp/jarvis-self-check.XXXXXX)
chmod 755 "$stage"
cp -a "$current/src" "$stage/src"
mkdir "$stage/tests"
cp "$bundle/src/agent.py" "$bundle/src/project_knowledge.py" "$bundle/src/system_knowledge.py" "$stage/src/"
cp "$bundle/src/jarvis_desktop/"*.py "$stage/src/jarvis_desktop/"
cp "$bundle/tests/test_system_knowledge.py" "$stage/tests/"
cd "$stage"
runuser -u jarvis -- env PYTHONDONTWRITEBYTECODE=1 "$current/.venv/bin/python" -m pytest -q -p no:cacheprovider -o asyncio_mode=auto tests/test_system_knowledge.py
backup=/var/backups/jarvis-self-knowledge/$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 700 "$backup"
python3 - "$bundle" "$current" "$backup" <<'PY'
import json,pathlib,shutil,sys
bundle,root,backup=map(pathlib.Path,sys.argv[1:])
items=json.loads((bundle/'manifest.json').read_text())['files']
for item in items:
    dest=root/item['path']; saved=backup/item['path']
    if dest.exists():
        saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,saved)
(backup/'manifest.json').write_text(json.dumps(items))
(backup/'target.txt').write_text(str(root))
try:
    for item in items:
        dest=root/item['path'];tmp=dest.with_suffix(dest.suffix+'.self-new')
        shutil.copyfile(bundle/item['path'],tmp);tmp.chmod(0o644);tmp.replace(dest)
except BaseException:
    for item in items:
        dest=root/item['path'];saved=backup/item['path']
        if saved.exists(): shutil.copy2(saved,dest)
        elif item['before'] is None: dest.unlink(missing_ok=True)
    raise
PY
echo "Instalado para a próxima chamada de voz. Backup: $backup"
# Voice is on-demand. No restart of the gateway or n8n is necessary.
