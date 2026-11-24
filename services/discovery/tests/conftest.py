from __future__ import annotations

import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from rag_discovery.config import load_config

UNITY_INDEX = """//
// Search index for Unity script documentation
//
var pages =
[["Grid", "Grid"],["GridLayout.WorldToCell", "GridLayout.WorldToCell"],["Tilemaps.Tilemap", "Tilemap"],
["Tilemaps.Tilemap.SetTile", "Tilemap.SetTile"],["Physics2D.Raycast", "Physics2D.Raycast"],
["Transform-position", "Transform.position"],["UIElements.Button", "Button"],["MonoBehaviour", "MonoBehaviour"],
["Rigidbody", "Rigidbody"]];
var info = [[0, 1]];
"""
UNITY_TOC = """{"link":"null","title":"root","children":[
 {"link":"UnityManual","title":"Unity Manual","children":[
   {"link":"tilemaps-intro","title":"Introduction to tilemaps","children":null},
   {"link":"multiplayer-netcode","title":"Netcode for GameObjects overview","children":null}]},
 {"link":"audio-overview","title":"Audio overview","children":null}]}"""
XREFMAP = """### YamlMime:XRefMap
sorted: true
references:
- uid: UnityEngine.UI.Button
  name: Button
  href: api/UnityEngine.UI.Button.html
  commentId: T:UnityEngine.UI.Button
  fullName: UnityEngine.UI.Button
  nameWithType: Button
- uid: UnityEngine.UI.Button.onClick
  name: onClick
  href: api/UnityEngine.UI.Button.html#UnityEngine_UI_Button_onClick
  commentId: P:UnityEngine.UI.Button.onClick
  fullName: UnityEngine.UI.Button.onClick
  nameWithType: Button.onClick
- uid: TMPro.TMP_Text
  name: TMP_Text
  href: api/TMPro.TMP_Text.html
  commentId: T:TMPro.TMP_Text
  fullName: TMPro.TMP_Text
  nameWithType: TMP_Text
"""
FACEPUNCH = """<html><body>
<a href="/steamworks/~edit">edit</a>
<a href="/steamworks/SteamMatchmaking">SteamMatchmaking</a>
<a href="/steamworks/Data.Lobby">Lobby</a>
<a href="/steamworks/SteamServerInit.SteamPort">SteamPort</a>
<a href="/steamworks/SteamMatchmaking#x">SteamMatchmaking</a>
<a href="/steamworks/Sending_P2P_Messages">
   P2P Networking
</a>
<a href="https://other.example.com/steamworks/Out">Out</a>
</body></html>"""
INDEXES = {
    "https://docs.example/ScriptReference/docdata/index.js": UNITY_INDEX,
    "https://docs.example/Manual/docdata/toc.json": UNITY_TOC,
    "https://docs.example/Packages/ugui/xrefmap.yml": XREFMAP,
    "https://wiki.example/steamworks/": FACEPUNCH,
}

SCRIPTS = {
    "Board.cs": """using UnityEngine;
using UnityEngine.Tilemaps;
// Rigidbody só em comentário não conta
public class Board : MonoBehaviour {
    public Tilemap map; Grid grid;
    void Place(Vector3Int c) { map.SetTile(c, null); var hit = Physics2D.Raycast(Vector2.zero, Vector2.up); }
    string s = "Rigidbody";
}""",
    "Hud.cs": """using UnityEngine;
using UnityEngine.UI;
using Steamworks;
public class Hud : MonoBehaviour { public Button roll; Grid g; void A() { SteamMatchmaking.CreateLobbyAsync(); } }""",
}


@pytest.fixture(autouse=True)
def no_external_network(monkeypatch):
    real = socket.socket.connect

    def guarded(self, address):
        host = address[0] if isinstance(address, tuple) else address
        if host not in {"127.0.0.1", "::1", "localhost"}:
            raise AssertionError(f"conexão externa bloqueada no teste: {address}")
        return real(self, address)

    monkeypatch.setattr(socket.socket, "connect", guarded)


def fake_fetch(url: str, _ua: str) -> str:
    return INDEXES[url]


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    unity = tmp_path / "unity"
    scripts = unity / "Assets" / "Scripts"
    scripts.mkdir(parents=True)
    for name, body in SCRIPTS.items():
        (scripts / name).write_text(body, encoding="utf-8")
    (unity / "Packages").mkdir()
    (unity / "Packages" / "manifest.json").write_text(
        '{"dependencies": {"com.unity.ugui": "2.0.0", "com.unity.modules.audio": "1.0.0"}}', encoding="utf-8")
    (unity / "ProjectSettings").mkdir()
    (unity / "ProjectSettings" / "ProjectVersion.txt").write_text("m_EditorVersion: 6000.3.10f1\n", encoding="utf-8")
    local = tmp_path / "local"
    local.mkdir()
    (local / "ingestion.toml").write_text('project_id = "dicevtt"\noutput_root = "../docs"\n', encoding="utf-8")
    (local / "rag.toml").write_text(
        f'project_id = "dicevtt"\nunity_project_root = "{unity.as_posix()}"\n'
        f'scripts_root = "{scripts.as_posix()}"\ndocs_root = "../docs"\nchroma_path = "rag/chroma"\n',
        encoding="utf-8")
    (local / "discovery.toml").write_text("""
[limits]
max_api_per_run = 50
max_topic_per_run = 10
min_files_per_symbol = 1

[topics]
min_score = 0.2
results_per_topic = 2
extra = ["tilemaps introduction"]

[llm]
enabled = true
topics = 3

[run]
poll_seconds = 0.5

[[catalogs]]
id = "unity-scripting"
kind = "unity_pages"
index = "https://docs.example/ScriptReference/docdata/index.js"
base = "https://docs.example/ScriptReference/"
api = true

[[catalogs]]
id = "unity-manual"
kind = "unity_toc"
index = "https://docs.example/Manual/docdata/toc.json"
base = "https://docs.example/Manual/"
topics = true

[[catalogs]]
id = "ugui-api"
kind = "docfx_xrefmap"
index = "https://docs.example/Packages/ugui/xrefmap.yml"
base = "https://docs.example/Packages/ugui/"
api = true

[[catalogs]]
id = "facepunch"
kind = "html_links"
index = "https://wiki.example/steamworks/"
base = "https://wiki.example/steamworks/"
namespace = "Steamworks"
api = true
topics = true
""", encoding="utf-8")
    return local


@pytest.fixture
def config(workspace: Path):
    return load_config(workspace / "discovery.toml")
