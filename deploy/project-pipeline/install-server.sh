#!/bin/bash
set -euo pipefail
[ "$(id -u)" = 0 ] || { echo 'Execute com sudo.'; exit 1; }
bundle=$(cd -- "$(dirname -- "$0")" && pwd)
current=$(readlink -f /opt/jarvis/current)
case "$current" in /opt/jarvis/releases/*) ;; *) echo 'Release inesperada'; exit 1;; esac
systemctl is-active --quiet jarvis-agent && { echo 'Encerre a chamada de voz primeiro.'; exit 1; }
# Validate all baselines and payloads before stopping any service.
python3 - "$bundle" "$current" <<'PY'
import hashlib,json,pathlib,sys
bundle,root=map(pathlib.Path,sys.argv[1:])
allowed={'src/project_pipeline.py','src/jarvis_control/orchestrator.py','src/jarvis_control/web.py'}
items=json.loads((bundle/'manifest.json').read_text())
if {i['path'] for i in items} != allowed: raise SystemExit('Manifesto inesperado')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
for item in items:
    if digest(bundle/item['path'])!=item['after']: raise SystemExit('Pacote alterado: '+item['path'])
    if digest(root/item['path']) not in (item['before'],item['after']): raise SystemExit('Base mudou: '+item['path'])
    compile((bundle/item['path']).read_text(),item['path'],'exec')
PY
backup=/var/backups/jarvis-project-pipeline/$(date -u +%Y%m%dT%H%M%SZ)
install -d -m 700 "$backup"
python3 - <<'PY'
import sqlite3
from pathlib import Path
path=Path('/var/lib/jarvis-control/orchestrator.db')
if not path.is_file(): raise SystemExit('Banco esperado ausente.')
with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
    if db.execute("SELECT COUNT(*) FROM runs WHERE state IN ('running','reviewing')").fetchone()[0] or db.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('dispatching','waiting_for_pc','running')").fetchone()[0]:
        raise SystemExit('Há trabalhos ativos; nenhum serviço foi interrompido.')
PY
systemctl stop jarvis-control
trap 'systemctl start jarvis-control' EXIT
# After stop, no new request can race this check. Never interrupt an active run.
python3 - <<'PY'
import sqlite3
from pathlib import Path
path=Path('/var/lib/jarvis-control/orchestrator.db')
if not path.is_file(): raise SystemExit('Banco esperado ausente; confira o diretório de estado antes de instalar.')
with sqlite3.connect(f'file:{path}?mode=ro',uri=True) as db:
    active=db.execute("SELECT COUNT(*) FROM runs WHERE state IN ('running','reviewing')").fetchone()[0]
    jobs=db.execute("SELECT COUNT(*) FROM jobs WHERE state IN ('dispatching','waiting_for_pc','running')").fetchone()[0]
    if active or jobs: raise SystemExit('Há trabalhos ativos. Aguarde antes de instalar.')
PY
python3 - "$bundle" "$current" "$backup" <<'PY'
import json,pathlib,shutil,sys
bundle,root,backup=map(pathlib.Path,sys.argv[1:])
items=json.loads((bundle/'manifest.json').read_text())
for item in items:
    src=root/item['path'];saved=backup/item['path']
    if src.exists():
        saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,saved)
(backup/'manifest.json').write_text(json.dumps(items))
(backup/'target.txt').write_text(str(root))
try:
    for item in items:
        dest=root/item['path'];tmp=dest.with_suffix('.pipeline-new')
        shutil.copyfile(bundle/item['path'],tmp);tmp.chmod(0o644);tmp.replace(dest)
except BaseException:
    for item in items:
        dest=root/item['path'];saved=backup/item['path']
        if saved.exists(): shutil.copy2(saved,dest)
        elif item['before'] is None: dest.unlink(missing_ok=True)
    raise
PY
systemctl start jarvis-control
ok=false
for i in $(seq 1 15); do
  if curl -fsS http://127.0.0.1:8090/v1/health >/dev/null; then ok=true; break; fi
  sleep 1
done
if [ "$ok" != true ]; then
  systemctl stop jarvis-control
  python3 - "$current" "$backup" <<'PY'
import json,pathlib,shutil,sys
root,backup=map(pathlib.Path,sys.argv[1:])
for item in json.loads((backup/'manifest.json').read_text()):
    dest=root/item['path'];saved=backup/item['path']
    if saved.exists(): shutil.copy2(saved,dest)
    elif item['before'] is None: dest.unlink(missing_ok=True)
PY
  echo 'Health falhou; arquivos anteriores restaurados.'; exit 1
fi
echo "Três etapas instaladas. Backup: $backup"
