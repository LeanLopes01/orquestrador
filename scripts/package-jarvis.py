"""Explicit backend allowlist, matching Jarvis's existing deployment workflow."""
import hashlib
import json
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

workspace = Path(__file__).resolve().parents[1]
stage = workspace / ".local/jarvis-work"
suffix = sys.argv[1] if len(sys.argv) > 1 else "companion"
version = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{suffix}"
output = workspace / ".local/releases"
output.mkdir(parents=True, exist_ok=True)
patterns = [
    "src/*.py", "src/jarvis_control/*.py", "src/jarvis_desktop/*.py",
    "tests/*.py", "deploy/jarvis-deploy", "deploy/jarvis-control",
    "deploy/smoke_session.py", "deploy/systemd/*.service", "deploy/polkit/*.rules",
    "pyproject.toml", "uv.lock", "scenarios.yaml", "README.md", "LICENSE", ".env.example",
]
paths = sorted({p for pattern in patterns for p in stage.glob(pattern)})
package = output / f"jarvis-backend-{version}.tar.gz"
with tarfile.open(package, "w:gz") as archive:
    for path in paths:
        archive.add(path, arcname=path.relative_to(stage).as_posix(), recursive=False)
checksum = hashlib.sha256(package.read_bytes()).hexdigest()
metadata = {"version": version, "package": str(package), "sha256": checksum, "files": len(paths)}
(output / "latest.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
print(json.dumps(metadata))
