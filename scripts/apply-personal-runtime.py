"""Apply the personal-data runtime to C:\\J.A.R.V.I.S\\jarvis, with a backup.

Copies only this delivery's files from .local/personal-runtime-work after checking
that the originals still match the snapshot taken when the work started.
"""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
stage = root / '.local/personal-runtime-work'
target = Path('C:/J.A.R.V.I.S/jarvis')
baseline = {}
for line in (root / '.local/personal-runtime-baseline.txt').read_text(encoding='utf-8').splitlines():
    digest, path = line.split(' ', 1)
    baseline[path] = digest
PATHS = [
    'src/agent.py', 'src/conversation_log.py', 'src/personal_data.py',
    'src/jarvis_control/config.py', 'src/jarvis_control/integrations.py',
    'src/jarvis_control/personal.py', 'src/jarvis_control/web.py',
    'src/jarvis_control/__main__.py',
    'tests/test_personal_gateway.py', 'tests/test_personal_agent.py',
    'deploy/jarvis-control', 'deploy/systemd/jarvis-control.service',
    'deploy/n8n/build.py', 'deploy/n8n/credentials.template.json',
    'deploy/n8n/workflows/google_a.json', 'deploy/n8n/workflows/google_b.json',
    'deploy/n8n/workflows/outlook.json', 'deploy/n8n/workflows/notion.json',
    'scenarios.yaml',
]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


if __name__ == '__main__':
    changed = [p for p in PATHS if digest(stage / p) != digest(target / p)]
    for p in changed:
        if digest(target / p) != baseline.get(p):
            raise SystemExit(f'Concurrent modification: {p}; original left intact.')
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = root / '.local/backups' / f'{stamp}-personal-runtime'
    backup.mkdir(parents=True)
    manifest = []
    for p in changed:
        dest = target / p
        before = digest(dest)
        if dest.exists():
            saved = backup / p
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, saved)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(stage / p, dest)
        manifest.append({'path': p, 'before': before, 'after': digest(dest)})
    (backup / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'backup': str(backup), 'changed': changed}))
