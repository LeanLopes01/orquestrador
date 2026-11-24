"""Overlay only the integration change on an archive of the active release."""
import hashlib
import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

root = Path(__file__).resolve().parents[1]
stage = root / '.local/personal-integrations-work'
base = root / '.local/personal-integrations-base.tar.gz'
overlay = [
    'src/jarvis_control/integrations.py', 'src/jarvis_control/store.py',
    'src/jarvis_control/web.py', 'src/jarvis_control/__main__.py',
    'tests/test_personal_integrations.py',
]
baseline = json.loads((root / '.local/personal-integrations-baseline.json').read_text())
version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-personal-connections'
out = root / '.local/releases'
out.mkdir(exist_ok=True)
package = out / f'jarvis-backend-{version}.tar.gz'
contents = {}
with tarfile.open(base, 'r:gz') as archive:
    for member in archive.getmembers():
        if member.isdir():
            continue
        path = PurePosixPath(member.name)
        if not member.isfile() or path.is_absolute() or '..' in path.parts:
            raise SystemExit(f'Unsafe archive member: {member.name}')
        if '__pycache__' in path.parts:
            continue
        contents[member.name] = (archive.extractfile(member).read(), member.mode)
for name in overlay:
    if name in contents and hashlib.sha256(contents[name][0]).hexdigest() != baseline.get(name):
        raise SystemExit(f'Base source changed; review before overlay: {name}')
    contents[name] = ((stage / name).read_bytes(), 0o644)
with tarfile.open(package, 'w:gz') as archive:
    for name, (data, mode) in sorted(contents.items()):
        info = tarfile.TarInfo(name)
        info.mode, info.size = mode, len(data)
        archive.addfile(info, io.BytesIO(data))
metadata = {
    'version': version, 'package': str(package),
    'sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
    'base_release': '20261022T223448Z-planner-routing', 'overlay': overlay,
}
(out / 'personal-integrations.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
print(json.dumps(metadata))
