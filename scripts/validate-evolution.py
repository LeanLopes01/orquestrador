"""Validate the exact packaged backend and ensure the companion is never shipped."""
import hashlib
import json
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
release = json.loads((ROOT/'artifacts/server/release.json').read_text(encoding='utf-8'))
package = ROOT/'artifacts/server'/release['package']
assert hashlib.sha256(package.read_bytes()).hexdigest() == release['sha256']
bundle = ROOT/'artifacts/server'/release['bundle']
assert hashlib.sha256(bundle.read_bytes()).hexdigest() == release['bundle_sha256']
with tarfile.open(bundle) as archive:
    names = set(archive.getnames())
    assert {'install.sh', 'rollback.sh', 'registry.json', release['package']} <= names
    assert hashlib.file_digest(archive.extractfile(release['package']), 'sha256').hexdigest() == release['sha256']
    for member in archive:
        assert not member.name.startswith('/') and '..' not in Path(member.name).parts
        assert not (member.name.endswith('.apk') or Path(member.name).name in {'.env', 'personal.env', 'gateway.secret'})
        if member.isfile() and member.name.startswith(('n8n-nodes/', 'workflows/')):
            assert archive.extractfile(member).read() == (ROOT/'deploy/evolution'/member.name).read_bytes(), member.name
    assert len([name for name in names if name.startswith('workflows/') and name.endswith('.json')]) == 75
stage = ROOT/'.local/evolution'/('check-'+release['version'])
stage.mkdir(parents=True, exist_ok=True)
with tarfile.open(package) as archive:
    members = archive.getmembers()
    assert 'deploy/mobile/jarvis-primary.apk' in {m.name for m in members}
    assert not any('companion' in m.name.lower() and m.name.endswith('.apk') for m in members)
    assert not any(Path(m.name).name in {'.env','personal.env','gateway.secret'} for m in members)
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        if member.name.endswith('.apk'):
            continue
        destination=stage/member.name
        destination.parent.mkdir(parents=True,exist_ok=True)
        destination.write_bytes(archive.extractfile(member).read())
with (ROOT/'.local/evolution/packaged-backend-tests.log').open('w',encoding='utf-8') as log:
    result = subprocess.run(['uv','run','--project','C:/J.A.R.V.I.S/jarvis','python','-m','pytest','-q'],cwd=stage,stdout=log,stderr=subprocess.STDOUT)
lines=(ROOT/'.local/evolution/packaged-backend-tests.log').read_text(encoding='utf-8').splitlines()
print('\n'.join(lines[-12:]))
(ROOT/'artifacts/server/validation.json').write_text(json.dumps({
    'version': release['version'], 'bundle_sha256': release['bundle_sha256'],
    'validated_at': datetime.now(timezone.utc).isoformat(), 'backend_test_exit_code': result.returncode,
    'backend_result': next((line for line in reversed(lines) if 'passed' in line), ''),
    'catalog_workflows': 75, 'companion_in_upload': False,
}, indent=2), encoding='utf-8')
raise SystemExit(result.returncode)
