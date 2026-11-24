"""Overlay the personal-data runtime on the package of the active release.

The base is the archive that was deployed as 20261023T205950Z-personal-connections,
so the server's helper files stay as they are there. Refuses to overlay a file
whose base content differs from the snapshot this work started from.
"""
import hashlib
import importlib.util
import io
import json
import tarfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

root = Path(__file__).resolve().parents[1]
stage = root / '.local/personal-runtime-work'
base_release = '20261023T205950Z-personal-connections'
base = root / f'.local/releases/jarvis-backend-{base_release}.tar.gz'
spec = importlib.util.spec_from_file_location('apply', root / 'scripts/apply-personal-runtime.py')
apply = importlib.util.module_from_spec(spec)
spec.loader.exec_module(apply)
overlay = apply.PATHS

version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ') + '-personal-runtime'
out = root / '.local/releases'
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
    mode = 0o644
    if name in contents:
        old = hashlib.sha256(contents[name][0]).hexdigest()
        if old != apply.baseline.get(name):
            raise SystemExit(f'Base source changed; review before overlay: {name}')
        mode = contents[name][1]
    contents[name] = ((stage / name).read_bytes(), mode)
with tarfile.open(package, 'w:gz') as archive:
    for name, (data, mode) in sorted(contents.items()):
        info = tarfile.TarInfo(name)
        info.mode, info.size = mode, len(data)
        archive.addfile(info, io.BytesIO(data))
metadata = {
    'version': version, 'package': str(package),
    'sha256': hashlib.sha256(package.read_bytes()).hexdigest(),
    'base_release': base_release, 'overlay': overlay,
}
(out / 'personal-runtime.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')
print(json.dumps(metadata))
