"""Editor.log e Player.log: só os últimos MB, com origem, trecho lido, hash e correspondência ao projeto.

Logs podem ser antigos ou de outro projeto. Sem correspondência confiável o achado fica `suspected`
e o check `partial`; nunca "erro atual confirmado".
"""

from __future__ import annotations

import os
import re
from collections import Counter, defaultdict

from .base import CheckResult, Context, Finding, local_time, read_head, read_tail, redact

_COMPILE_START = re.compile(r"^\[ScriptCompilation\] Requested script compilation", re.M)
_COMPILE_END = re.compile(r"^\*\*\* Tundra build (success|failed)", re.M)
_DIAGNOSTIC = re.compile(r"^(?P<file>[^\s(][^(\n]*?)\((?P<line>\d+),\d+\): (?P<level>error|warning) (?P<code>CS\d+): "
                         r"(?P<msg>.*)$", re.M)
_EXCEPTION = re.compile(r"^(?P<type>[A-Za-z_][\w.]*Exception)(?::\s*(?P<msg>.*))?$", re.M)
_FRAME = re.compile(r"\(at (?P<file>[^:)]+):(?P<line>\d+)\)")
_VERSION = re.compile(r"Version is '([^']+)'")


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path.strip()))


def _project_of(head: str) -> str | None:
    lines = head.splitlines()
    for index, line in enumerate(lines):
        if line.strip().lower() == "-projectpath" and index + 1 < len(lines):
            return lines[index + 1].strip()
    return None


def _freshness(ctx: Context, log_mtime: float) -> tuple[bool, str]:
    latest = ctx.shared.get("latest_script_mtime") or 0.0
    if latest > log_mtime:
        return False, f"scripts alterados depois do log ({ctx.shared.get('latest_script')} em {local_time(latest)})"
    return True, ""


def _exceptions(text: str) -> dict[tuple[str, str], dict]:
    """Agrupa por tipo + primeiro frame do projeto (sem linha: a identidade não muda a cada edição)."""
    groups: dict[tuple[str, str], dict] = {}
    lines = text.splitlines()
    for number, line in enumerate(lines):
        match = _EXCEPTION.match(line)
        if match is None:
            continue
        frame_file, frame_line = "", None
        for follow in lines[number + 1:number + 12]:
            frame = _FRAME.search(follow)
            if frame and frame.group("file").replace("\\", "/").startswith("Assets/"):
                frame_file, frame_line = frame.group("file").replace("\\", "/"), int(frame.group("line"))
                break
        key = (match.group("type"), frame_file)
        group = groups.setdefault(key, {"count": 0, "message": redact((match.group("msg") or "")[:240]),
                                        "line": frame_line, "excerpt": redact("\n".join(lines[number:number + 6]))[:700]})
        group["count"] += 1
    return groups


def _exception_findings(check: CheckResult, groups: dict, rule: str, state: str, evidence: str, where: str,
                        limit: int) -> None:
    ranked = sorted(groups.items(), key=lambda item: -item[1]["count"])
    for (kind, file), info in ranked[:limit]:
        check.findings.append(Finding(
            rule=rule, severity="medium", state=state, key=f"{kind}|{file}", file=file or None, line=info["line"],
            occurrences=info["count"], evidence=[evidence],
            summary=f"{kind} {info['count']}x no {where}" + (f" em {file}" if file else "")
                    + (f": {info['message']}" if info["message"] else ""),
            recommendation="Reproduza a ação que gerou a exceção e confira o trecho do log:\n" + info["excerpt"],
        ))


def compile_findings(check: CheckResult, text: str, prefix: str, state: str, evidence: str, limit: int) -> dict | None:
    """Erros e avisos só da ÚLTIMA compilação do log; os anteriores são histórico já superado."""
    ends = list(_COMPILE_END.finditer(text))
    if not ends:
        return None
    end = ends[-1]
    starts = [m for m in _COMPILE_START.finditer(text, 0, end.start())]
    segment = text[starts[-1].start() if starts else 0:end.end()]
    result = end.group(1)
    diags = list(_DIAGNOSTIC.finditer(segment))
    errors = [d for d in diags if d.group("level") == "error"]
    warnings = Counter(d.group("code") for d in diags if d.group("level") == "warning")
    by_file: dict[tuple[str, str], list[re.Match[str]]] = defaultdict(list)
    for diag in errors:
        by_file[(diag.group("code"), diag.group("file").replace("\\", "/"))].append(diag)
    for (code, file), items in list(by_file.items())[:limit]:
        first = items[0]
        check.findings.append(Finding(
            rule=f"{prefix}.compile-error", severity="high", state=state, key=f"{code}|{file}", file=file,
            line=int(first.group("line")), occurrences=len(items), evidence=[evidence],
            summary=f"Erro de compilação {code} em {file}: {redact(first.group('msg'))[:200]}",
            recommendation="Corrija o erro e recompile; o relatório seguinte confirma pela próxima compilação.",
        ))
    if result == "failed" and not errors:
        check.findings.append(Finding(
            rule=f"{prefix}.compile-failed", severity="high", state=state, key="tundra", evidence=[evidence],
            summary="A última compilação falhou sem erro C# identificável no trecho lido",
            recommendation="Abra o Console da Unity; o detalhe pode estar antes do trecho lido.",
        ))
    for code, count in warnings.most_common(5):
        sample = next(d for d in diags if d.group("code") == code)
        files = Counter(d.group("file").replace("\\", "/") for d in diags if d.group("code") == code)
        check.findings.append(Finding(
            rule=f"{prefix}.compile-warning", severity="low", state=state, key=code, occurrences=count,
            file=sample.group("file").replace("\\", "/"), evidence=[evidence],
            summary=f"{count} aviso(s) {code} na última compilação: {redact(sample.group('msg'))[:160]}",
            recommendation="Arquivos: " + ", ".join(f"{f} ({n})" for f, n in files.most_common(5))
                           + ". A Unity só reimprime avisos dos assemblies recompilados.",
        ))
    return {"result": result, "errors": len(errors), "warnings": sum(warnings.values())}


def collect_editor(ctx: Context, check: CheckResult) -> None:
    path = ctx.config.editor_log
    if path is None or not path.exists():
        check.degrade("partial", f"Editor.log não encontrado ({path}).")
        return
    head = read_head(path)
    tail = read_tail(path, ctx.config.log_read_bytes)
    project = _project_of(head)
    matches = project is not None and _norm(project) == _norm(str(ctx.config.project_root))
    fresh, stale_reason = _freshness(ctx, path.stat().st_mtime)
    version = _VERSION.search(head)
    closed = "Checking for leaked weakptr" in tail.text[-4000:] or "Exiting batchmode" in tail.text[-4000:]
    evidence = check.add_evidence(
        "log_excerpt", path.as_posix(), f"bytes {tail.offset}-{tail.size} de {tail.size}", sha256=tail.sha256,
        observed_at=tail.mtime, extra={"project": project, "matches_project": matches, "editor_closed": closed},
    )
    check.data["editor_log"] = {"path": path.as_posix(), "modified_at": tail.mtime, "size": tail.size,
                                "read_offset": tail.offset, "sha256": tail.sha256, "project": project,
                                "matches_project": matches, "fresh": fresh, "editor_version": version.group(1) if version else None,
                                "session_closed": closed}
    if not matches:
        check.degrade("partial", f"Editor.log é de outro projeto ({project or 'desconhecido'}); achados ignorados.")
        return
    if not fresh:
        check.degrade("partial", f"Editor.log possivelmente desatualizado: {stale_reason}.")
    state = "confirmed" if fresh else "suspected"
    last = compile_findings(check, tail.text, "unity", state, evidence, ctx.config.max_findings_per_check)
    check.data["editor_log"]["last_compile"] = last
    if last is None:
        check.problems.append("Nenhuma compilação registrada no trecho lido do Editor.log.")
    _exception_findings(check, _exceptions(tail.text), "unity.editor-exception", state, evidence,
                        "Editor.log", ctx.config.max_findings_per_check)


def collect_player(ctx: Context, check: CheckResult) -> None:
    folder = ctx.config.player_log_dir
    path = folder / "Player.log" if folder else None
    if path is None or not path.exists():
        check.data["player_log"] = None
        check.problems.append("Player.log não encontrado: nenhuma execução do build registrada.")
        return
    tail = read_tail(path, ctx.config.log_read_bytes)
    head = read_head(path, 4096)
    build = re.search(r"Discovering subsystems at path (.+?)/UnitySubsystems", head)
    fresh, stale_reason = _freshness(ctx, path.stat().st_mtime)
    evidence = check.add_evidence("log_excerpt", path.as_posix(), f"bytes {tail.offset}-{tail.size}",
                                  sha256=tail.sha256, observed_at=tail.mtime,
                                  extra={"build": build.group(1) if build else None})
    check.data["player_log"] = {"path": path.as_posix(), "modified_at": tail.mtime, "size": tail.size,
                                "sha256": tail.sha256, "build": build.group(1) if build else None, "fresh": fresh}
    if not fresh:
        check.problems.append(f"Player.log de um build anterior: {stale_reason}.")
    _exception_findings(check, _exceptions(tail.text), "unity.player-exception", "suspected", evidence,
                        "Player.log (último build executado)", ctx.config.max_findings_per_check)


def collect(ctx: Context, check: CheckResult) -> None:
    collect_editor(ctx, check)
    ctx.check_cancel()
    collect_player(ctx, check)
    editor = check.data.get("editor_log") or {}
    compile_info = editor.get("last_compile")
    parts = []
    if editor:
        parts.append(f"Editor.log de {local_time(editor.get('modified_at'))}"
                     + ("" if editor.get("matches_project") else " (outro projeto)"))
    if compile_info:
        parts.append(f"última compilação: {compile_info['result']}, {compile_info['errors']} erro(s), "
                     f"{compile_info['warnings']} aviso(s)")
    if check.data.get("player_log"):
        parts.append(f"Player.log de {local_time(check.data['player_log']['modified_at'])}")
    check.note = " · ".join(parts) or "Nenhum log disponível."
