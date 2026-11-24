"""Back up source files before the Jarvis evolution; never copy credentials."""
from pathlib import Path
import hashlib
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]
JARVIS = Path(r'C:\J.A.R.V.I.S\jarvis')
BACKUP = ROOT / '.local/evolution/baseline'

def main():
    if (BACKUP / 'manifest.json').exists():
        print('Baseline already recorded; preserved.')
        return
    manifest = {}
    for prefix, base, folders in [
        ('orchestrator', ROOT, ['src', 'services', 'scripts', 'src-tauri/src']),
        ('jarvis', JARVIS, ['src', 'tests', 'deploy', 'livekit_flutter_starter-main/lib', 'livekit_flutter_starter-main/android/app/src']),
    ]:
        files = [p for folder in folders for p in (base / folder).rglob('*') if p.is_file()
                 and '__pycache__' not in p.parts and p.suffix in {'.py', '.mjs', '.ts', '.tsx', '.css', '.rs', '.dart', '.kt', '.xml', '.json', '.sh', '.cmd', '.ps1'}]
        names = ['package.json', 'package-lock.json', 'vite.config.mjs', 'src-tauri/tauri.conf.json', 'src-tauri/Cargo.toml', 'src-tauri/Cargo.lock', 'iniciar-tudo.cmd', 'parar-tudo.cmd'] if prefix == 'orchestrator' else ['scenarios.yaml', 'pyproject.toml', 'uv.lock', 'livekit_flutter_starter-main/pubspec.yaml', 'livekit_flutter_starter-main/android/app/build.gradle']
        files += [base / name for name in names if (base / name).exists()]
        for path in files:
            rel = f'{prefix}/{path.relative_to(base).as_posix()}'
            target = BACKUP / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            manifest[rel] = hashlib.sha256(path.read_bytes()).hexdigest()
    (BACKUP / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f'Backed up {len(manifest)} source files. No credentials copied.')

if __name__ == '__main__':
    main()
