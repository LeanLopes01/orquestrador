"""Perfil do projeto Unity a partir dos scripts C# e do manifest de pacotes.

Contagem por arquivo (quantos scripts usam o símbolo), não por ocorrência: um tipo
usado em 40 scripts pesa mais que um repetido 40 vezes num só.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

_COMMENTS = re.compile(r"//[^\n]*|/\*.*?\*/", re.DOTALL)
_STRINGS = re.compile(r'@"(?:[^"]|"")*"|\$?"(?:\\.|[^"\\\n])*"|\'(?:\\.|[^\'\\\n])\'')
_USING = re.compile(r"(?<![\w.])using\s+(?:static\s+)?([A-Za-z_][\w.]*)\s*;")
_DECLARED = re.compile(r"\b(?:class|struct|enum|interface|record|delegate\s+\w+)\s+([A-Z]\w*)")
_TYPE = re.compile(r"(?<![\w.])([A-Z][A-Za-z0-9_]*)\b")
_MEMBER = re.compile(r"(?<![\w.])([A-Z][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)\b")
MAX_SCRIPT_BYTES = 2 * 1024 * 1024


@dataclass
class CodeProfile:
    files: int = 0
    usings: Counter = field(default_factory=Counter)
    types: Counter = field(default_factory=Counter)
    members: Counter = field(default_factory=Counter)
    # (símbolo, namespace) → scripts que usam o símbolo E importam o namespace: Button com
    # `using UnityEngine.UI` num arquivo não conta para UIElements.Button importado em outro.
    by_namespace: Counter = field(default_factory=Counter)
    declared: set[str] = field(default_factory=set)
    packages: list[str] = field(default_factory=list)
    unity_version: str = ""

    def project_types(self, limit: int = 30) -> list[str]:
        """Tipos do próprio projeto mais referenciados: revelam o domínio (Dice, Lobby, Token...)."""
        return [name for name, _ in self.types.most_common() if name in self.declared][:limit]


def _clean(source: str) -> str:
    return _STRINGS.sub('""', _COMMENTS.sub(" ", source))


def scan_source(source: str, profile: CodeProfile) -> None:
    profile.files += 1
    code = _clean(source)
    usings = set(_USING.findall(code))
    types = set(_TYPE.findall(code))
    members = {f"{a}.{b}" for a, b in _MEMBER.findall(code)}
    profile.usings.update(usings)
    profile.declared.update(_DECLARED.findall(code))
    profile.types.update(types)
    profile.members.update(members)
    profile.by_namespace.update((symbol, ns) for symbol in types | members for ns in usings)


def files_using(profile: CodeProfile, symbol: str, namespaces: frozenset[str] | None) -> tuple[int, str]:
    """(scripts, namespace mais frequente). Sem namespace exigido, conta todos os scripts."""
    if namespaces is None:
        counter = profile.members if "." in symbol else profile.types
        return counter.get(symbol, 0), ""
    best = max(((profile.by_namespace.get((symbol, ns), 0), ns) for ns in sorted(namespaces)),
               key=lambda pair: pair[0])
    return best


def read_packages(unity_root: Path) -> tuple[list[str], str]:
    packages: list[str] = []
    try:
        manifest = json.loads((unity_root / "Packages" / "manifest.json").read_text(encoding="utf-8-sig"))
        packages = [f"{name} {version}" for name, version in manifest.get("dependencies", {}).items()
                    if not name.startswith("com.unity.modules.")]
    except (OSError, ValueError):
        pass
    version = ""
    try:
        text = (unity_root / "ProjectSettings" / "ProjectVersion.txt").read_text(encoding="utf-8")
        match = re.search(r"m_EditorVersion:\s*(\S+)", text)
        version = match.group(1) if match else ""
    except OSError:
        pass
    return packages, version


def scan_project(scripts_root: Path, unity_root: Path | None = None) -> CodeProfile:
    profile = CodeProfile()
    for path in sorted(scripts_root.rglob("*.cs")):
        try:
            if path.stat().st_size > MAX_SCRIPT_BYTES:
                continue
            raw = path.read_bytes()
        except OSError:
            continue
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1252", errors="replace")
        scan_source(text, profile)
    if unity_root is not None:
        profile.packages, profile.unity_version = read_packages(unity_root)
    return profile
