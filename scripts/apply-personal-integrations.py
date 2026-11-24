"""Apply only this task's changes after checking original source fingerprints."""
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parents[1]
stage = root / '.local/personal-integrations-work'
target = Path('C:/J.A.R.V.I.S/jarvis')
baseline = json.loads((root / '.local/personal-integrations-baseline.json').read_text())
for previous in sorted((root / '.local/backups').glob('*-personal-connections/manifest.json')):
    for item in json.loads(previous.read_text()):
        baseline[item['path']] = item['after']
paths = [
    'src/jarvis_control/integrations.py', 'src/jarvis_control/store.py',
    'src/jarvis_control/web.py', 'src/jarvis_control/__main__.py',
    'tests/test_personal_integrations.py',
    'livekit_flutter_starter-main/lib/services/jarvis_api.dart',
    'livekit_flutter_starter-main/lib/screens/connections_screen.dart',
    'livekit_flutter_starter-main/lib/screens/master_screen.dart',
    'livekit_flutter_starter-main/lib/screens/master_landscape.dart',
    'livekit_flutter_starter-main/lib/screens/welcome_screen.dart',
    'livekit_flutter_starter-main/test/connections_test.dart',
    'livekit_flutter_starter-main/pubspec.yaml',
]
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

changed = [p for p in paths if digest(stage / p) != digest(target / p)]
for p in changed:
    if digest(target / p) != baseline.get(p):
        raise SystemExit(f'Concurrent modification: {p}; original left intact.')
backup = root / '.local/backups' / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-personal-connections')
backup.mkdir(parents=True)
manifest = []
for p in changed:
    dest = target / p
    before = digest(dest)
    if dest.exists():
        previous = backup / p
        previous.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(dest, previous)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(stage / p, dest)
    manifest.append({'path': p, 'before': before, 'after': digest(dest)})
(backup / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps({'backup': str(backup), 'changed': changed}))
