"""Apply only source changes, keeping a reversible backup of every replaced file."""
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path

workspace = Path(__file__).resolve().parents[1]
stage = workspace / ".local/jarvis-work"
destination = Path(r"C:\J.A.R.V.I.S\jarvis")
backup = workspace / ".local/backups" / datetime.now().strftime("%Y%m%d-%H%M%S")
patterns = [
    "src/*.py", "src/jarvis_control/*.py", "src/jarvis_desktop/*.py",
    "tests/*.py", "scenarios.yaml",
    "livekit_flutter_starter-main/lib/**/*.dart",
    "livekit_flutter_starter-main/test/*.dart",
    "livekit_flutter_starter-main/android/app/src/main/kotlin/**/*.kt",
    "livekit_flutter_starter-main/pubspec.yaml",
]
changed = []
for path in sorted({p for pattern in patterns for p in stage.glob(pattern)}):
    relative = path.relative_to(stage)
    target = destination / relative
    data = path.read_bytes()
    if target.exists() and target.read_bytes() == data:
        continue
    previous = None
    if target.exists():
        previous = hashlib.sha256(target.read_bytes()).hexdigest()
        copy = backup / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, copy)
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    changed.append({"path": relative.as_posix(), "before": previous, "after": hashlib.sha256(data).hexdigest()})
backup.mkdir(parents=True, exist_ok=True)
(backup / "manifest.json").write_text(json.dumps(changed, indent=2), encoding="utf-8")
print(json.dumps({"backup": str(backup), "changed": [item["path"] for item in changed]}, indent=2))
