from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pytest

from dicevtt_diagnostics.config import load_config

EDITOR_LOG = """\
Built from '6000.3/staging' branch; Version is '6000.3.10f1 (e35f0c77bd8e) revision 14901004'
COMMAND LINE ARGUMENTS:
C:\\Program Files\\Unity\\Hub\\Editor\\6000.3.10f1\\Editor\\Unity.exe
-projectpath
{project}
[ScriptCompilation] Requested script compilation because: first
Assets\\Scripts\\Velho.cs(3,5): error CS0103: The name 'x' does not exist token=abc123secret
*** Tundra build failed (1.00 seconds), 1 items updated, 10 evaluated
[ScriptCompilation] Requested script compilation because: second
Assets\\Scripts\\A.cs(10,13): warning CS0618: 'Foo' is obsolete
Assets\\Scripts\\B.cs(11,13): warning CS0618: 'Foo' is obsolete
Assets\\Scripts\\A.cs(20,1): error CS1002: ; expected
*** Tundra build failed (2.00 seconds), 1 items updated, 10 evaluated
NullReferenceException: Object reference not set to an instance of an object
Lobby.Entrar () (at Assets/Scripts/Lobby.cs:42)
UnityEngine.Debug:Log (object)
NullReferenceException: Object reference not set to an instance of an object
Lobby.Entrar () (at Assets/Scripts/Lobby.cs:44)
"""


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    root = tmp_path / "Proj"
    (root / "ProjectSettings").mkdir(parents=True)
    (root / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.3.10f1\n", encoding="utf-8")
    (root / "Packages").mkdir()
    (root / "Packages" / "manifest.json").write_text(json.dumps({"dependencies": {
        "com.unity.test-framework": "1.6.0", "com.exemplo.git": "https://example.com/repo.git"}}), encoding="utf-8")
    (root / "Packages" / "packages-lock.json").write_text(json.dumps({"dependencies": {
        "com.exemplo.git": {"version": "https://example.com/repo.git", "hash": "abc"}}}), encoding="utf-8")
    scripts = root / "Assets" / "Scripts"
    scripts.mkdir(parents=True)
    (scripts / "A.cs").write_text("class A {}", encoding="utf-8")
    (root / "Assets" / "Outros").mkdir()
    (root / "Assets" / "Outros" / "C.cs").write_text("class C {}", encoding="utf-8")
    (root / "Assets" / "Ignorado~").mkdir()
    (root / "Assets" / "Ignorado~" / "D.cs").write_text("class D {}", encoding="utf-8")
    editors = tmp_path / "Editors" / "6000.3.10f1" / "Editor"
    editors.mkdir(parents=True)
    (editors / "Unity.exe").write_bytes(b"")
    return root


@pytest.fixture()
def config(tmp_path: Path, project: Path):
    local = tmp_path / "local"
    local.mkdir()
    log = tmp_path / "Editor.log"
    log.write_text(EDITOR_LOG.format(project=project), encoding="utf-8")
    future = time.time() + 60  # log mais novo que os scripts: achados confirmados
    os.utime(log, (future, future))
    (local / "rag.toml").write_text(
        f'scripts_root = "{(project / "Assets" / "Scripts").as_posix()}"\ntoken_path = "rag/api-token"\n'
        '[service]\nport = 9\n', encoding="utf-8")
    (local / "diagnostics.toml").write_text(f"""
project_id = "dicevtt"
project_name = "DiceVTT"
project_root = "{project.as_posix()}"
[service]
port = 8768
[limits]
light_deadline_seconds = 20
command_timeout_seconds = 5
rag_wait_seconds = 0
[tools]
git = "git-inexistente-para-teste"
plastic_cm = "{(tmp_path / 'sem-cm.exe').as_posix()}"
unity_editors = "{(tmp_path / 'Editors').as_posix()}"
[logs]
editor_log = "{log.as_posix()}"
player_log_dir = "{(tmp_path / 'sem-player').as_posix()}"
[rag]
config = "rag.toml"
""", encoding="utf-8")
    return load_config(local / "diagnostics.toml")
