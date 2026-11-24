"""Snapshot the current Jarvis sources without overwriting earlier work."""
import hashlib
import json
import shutil
from pathlib import Path

workspace = Path(__file__).resolve().parents[1]
source = Path('C:/J.A.R.V.I.S/jarvis')
stage = workspace / '.local/personal-integrations-work'
if stage.exists():
    raise SystemExit('Stage already exists; preserve it and inspect before proceeding.')
stage.mkdir(parents=True)
ignore = shutil.ignore_patterns('.git', '.venv', '__pycache__', '.dart_tool', 'build', '.gradle', '.pytest_cache', '.ruff_cache')
for name in ('src', 'tests', 'deploy', 'livekit_flutter_starter-main'):
    shutil.copytree(source / name, stage / name, ignore=ignore)
for name in ('pyproject.toml', 'uv.lock', 'scenarios.yaml', 'README.md', 'LICENSE', '.env.example', 'AGENTS.md'):
    shutil.copy2(source / name, stage / name)
manifest = {}
for p in stage.rglob('*'):
    if p.is_file():
        manifest[p.relative_to(stage).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
(workspace / '.local/personal-integrations-baseline.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(f'Staged {len(manifest)} files at {stage}')
