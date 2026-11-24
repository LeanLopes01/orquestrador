"""Versão da Unity, pacotes declarados, assemblies de teste e inventário de scripts. Somente leitura."""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from .base import CheckResult, Context, Finding, read_head, sha256_bytes

_VERSION = re.compile(r"m_EditorVersion:\s*(\S+)")


def collect_version(ctx: Context, check: CheckResult) -> None:
    path = ctx.config.project_root / "ProjectSettings" / "ProjectVersion.txt"
    try:
        raw = path.read_bytes()
    except OSError as exc:
        check.degrade("error", f"ProjectVersion.txt ilegível: {exc}")
        return
    match = _VERSION.search(raw.decode("utf-8", "replace"))
    version = match.group(1) if match else None
    evidence = check.add_evidence("file", path.as_posix(), f"m_EditorVersion: {version}", sha256=sha256_bytes(raw))
    editors = ctx.config.unity_editors
    installed = sorted(p.name for p in editors.iterdir() if p.is_dir()) if editors and editors.is_dir() else []
    executable = editors / version / "Editor" / "Unity.exe" if editors and version else None
    check.data.update(editor_version=version, installed_editors=installed,
                      editor_path=executable.as_posix() if executable and executable.exists() else None)
    ctx.shared["editor_path"] = check.data["editor_path"]  # a auditoria completa usa este editor
    if version and executable is not None and not executable.exists():
        check.findings.append(Finding(
            rule="unity.editor-missing", severity="high", state="confirmed", key=version, evidence=[evidence],
            summary=f"A versão {version} pedida pelo projeto não está instalada no Unity Hub",
            recommendation=f"Instale {version} pelo Unity Hub. Instaladas: {', '.join(installed) or 'nenhuma'}.",
        ))
    check.note = f"Unity {version}" + (" instalada" if check.data["editor_path"] else " — editor não localizado")


def collect_packages(ctx: Context, check: CheckResult) -> None:
    packages = ctx.config.project_root / "Packages"
    try:
        manifest_raw = (packages / "manifest.json").read_bytes()
        manifest = json.loads(manifest_raw)
    except (OSError, ValueError) as exc:
        check.degrade("error", f"Packages/manifest.json ilegível: {exc}")
        return
    deps: dict[str, str] = manifest.get("dependencies", {})
    manifest_ev = check.add_evidence("file", (packages / "manifest.json").as_posix(), f"{len(deps)} dependência(s)",
                                     sha256=sha256_bytes(manifest_raw))
    try:
        lock = json.loads((packages / "packages-lock.json").read_bytes()).get("dependencies", {})
    except (OSError, ValueError):
        lock = None
    git_deps = {name: url for name, url in deps.items() if url.startswith(("http", "git", "ssh")) or url.endswith(".git")}
    check.data.update(dependencies=len(deps), git_dependencies=sorted(git_deps),
                      test_framework=deps.get("com.unity.test-framework"))
    if lock is None:
        check.findings.append(Finding(
            rule="packages.no-lock", severity="medium", state="confirmed", key="packages-lock", evidence=[manifest_ev],
            summary="Packages/packages-lock.json ausente: as versões resolvidas não são reproduzíveis",
            recommendation="Abra o projeto na Unity para gerar o lock e versione-o.",
        ))
    else:
        for name, url in git_deps.items():
            pinned = "#" in url or bool((lock.get(name) or {}).get("hash"))
            if not pinned:
                check.findings.append(Finding(
                    rule="packages.git-unpinned", severity="low", state="confirmed", key=name, evidence=[manifest_ev],
                    summary=f"Pacote {name} vem de Git sem revisão fixada",
                    recommendation="Fixe um commit ou tag na URL (#<rev>) para builds reproduzíveis.",
                ))


def _is_test_assembly(data: dict) -> bool:
    refs = [str(r) for r in data.get("references", [])]
    return ("UNITY_INCLUDE_TESTS" in data.get("defineConstraints", [])
            or "TestAssemblies" in data.get("optionalUnityReferences", [])
            or any("TestRunner" in r or "nunit" in r.lower() for r in refs + data.get("precompiledReferences", [])))


def scan_assets(ctx: Context, check: CheckResult) -> None:
    """Uma passada em Assets: scripts, asmdefs e o script mais recente (frescor dos logs)."""
    assets = ctx.config.project_root / "Assets"
    rag_root = ctx.config.rag.scripts_root if ctx.config.rag else None
    scripts = 0
    latest = 0.0
    latest_path = None
    outside_rag: Counter[str] = Counter()
    asmdefs, test_asmdefs = [], []
    visited = 0
    truncated = False
    for root, dirs, files in os.walk(assets):
        # Pastas com "~" ou ocultas são ignoradas pela Unity.
        dirs[:] = [d for d in dirs if not d.endswith("~") and not d.startswith(".")]
        ctx.check_cancel()
        for name in files:
            visited += 1
            if visited > ctx.config.scan_file_limit:
                truncated = True
                break
            path = Path(root, name)
            if name.endswith(".cs"):
                scripts += 1
                try:
                    mtime = path.stat().st_mtime
                except OSError:
                    continue
                if mtime > latest:
                    latest, latest_path = mtime, path
                if rag_root is not None and not path.is_relative_to(rag_root):
                    top = path.relative_to(assets).parts[0]
                    outside_rag[top] += 1
            elif name.endswith(".asmdef"):
                rel = path.relative_to(ctx.config.project_root).as_posix()
                asmdefs.append(rel)
                try:
                    if _is_test_assembly(json.loads(read_head(path, 65_536))):
                        test_asmdefs.append(rel)
                except ValueError:
                    pass
        if truncated:
            break
    latest_iso = datetime.fromtimestamp(latest, UTC).isoformat(timespec="seconds") if latest else None
    ctx.shared["latest_script_mtime"] = latest
    ctx.shared["latest_script"] = latest_path.relative_to(ctx.config.project_root).as_posix() if latest_path else None
    ctx.shared["test_assemblies"] = test_asmdefs
    check.data.update(scripts=scripts, latest_script=ctx.shared["latest_script"], latest_script_at=latest_iso,
                      asmdefs=asmdefs, test_assemblies=test_asmdefs, files_visited=visited, scan_truncated=truncated,
                      scripts_outside_rag=dict(outside_rag))
    scan_ev = check.add_evidence("file", assets.as_posix(),
                                 f"{scripts} scripts .cs, {len(asmdefs)} asmdef, {visited} arquivos lidos"
                                 + (" (limite atingido)" if truncated else ""), observed_at=latest_iso)
    if truncated:
        check.degrade("partial", "Varredura interrompida no limite de arquivos.")
    if check.data.get("test_framework") and not test_asmdefs:
        check.findings.append(Finding(
            rule="tests.no-test-assembly", severity="medium", state="confirmed", key="editmode-playmode",
            evidence=[scan_ev],
            summary="Test Framework declarado, mas nenhuma assembly de teste encontrada em Assets",
            recommendation="Crie uma assembly de testes (EditMode) antes de ativar o perfil completo; hoje ele "
                           "rodaria zero testes, o que não significa aprovação.",
        ))
    if outside_rag:
        total = sum(outside_rag.values())
        folders = ", ".join(f"{name} ({n})" for name, n in outside_rag.most_common(6))
        check.findings.append(Finding(
            rule="rag.scripts-outside-index", severity="low", state="confirmed", key="scripts-root",
            evidence=[scan_ev], occurrences=total,
            summary=f"{total} script(s) fora de {rag_root.relative_to(ctx.config.project_root).as_posix()} "
                    "não entram no RAG",
            recommendation=f"Pastas: {folders}. Amplie o scripts_root do RAG se forem código do projeto.",
        ))


def collect(ctx: Context, check: CheckResult) -> None:
    collect_version(ctx, check)
    ctx.check_cancel()
    collect_packages(ctx, check)
    ctx.check_cancel()
    scan_assets(ctx, check)
    tests = len(check.data.get("test_assemblies", []))
    check.note = (f"{check.note} · {check.data.get('dependencies', '?')} pacote(s) · "
                  f"{check.data.get('scripts', '?')} script(s) · {tests} assembly(ies) de teste").strip(" ·")
