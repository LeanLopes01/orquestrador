"""Revisão do projeto: Git (a raiz real é o repositório pai) e Unity Version Control (.plastic).

O perfil leve sempre analisa a cópia de trabalho: source_state = working_tree.
"""

from __future__ import annotations

import os
import re
from collections import Counter
from pathlib import Path

from .base import CheckResult, Context, Finding, read_head, run_command

PENDING = {"CH", "AD", "CO", "DE", "MV", "LD", "LM", "RP", "AD+LD", "CO+LD", "CH+LD"}
_SELECTOR_BRANCH = re.compile(r'(?:smartbranch|br(?:anch)?)\s+"([^"]+)"(?:\s+changeset\s+"(\d+)")?')
_SELECTOR_REPO = re.compile(r'rep\s+"([^"]+)"')


def _rel(project: Path, raw: str) -> str:
    try:
        return Path(os.path.relpath(raw, project)).as_posix()
    except ValueError:
        return raw.replace("\\", "/")


def collect_git(ctx: Context, check: CheckResult) -> None:
    project = ctx.config.project_root
    timeout = ctx.config.command_timeout_seconds
    git = ctx.config.git
    top = run_command([git, "-C", str(project), "rev-parse", "--show-toplevel"], project, timeout, ctx)
    check.add_evidence("command", "git rev-parse --show-toplevel", (top.stdout or top.stderr).strip()[:300])
    if top.code is None:  # git não executou: não dá para afirmar que o projeto está fora de um repositório
        check.degrade("error", f"Git indisponível: {top.stderr.strip()[:200] or 'timeout'}")
        check.data.update(git_root=None, tracked_files=None)
        return
    if top.code != 0:
        check.status, check.note = "collected", "O projeto não está dentro de um repositório Git."
        check.data.update(git_root=None, tracked_files=0)
        return
    root = Path(top.stdout.strip())
    relative = _rel(root, str(project))
    head = run_command([git, "-C", str(root), "rev-parse", "--verify", "-q", "HEAD"], root, timeout, ctx)
    branch = run_command([git, "-C", str(root), "branch", "--show-current"], root, timeout, ctx)
    tracked = run_command([git, "-C", str(root), "ls-files", "--", relative], root, timeout, ctx)
    status = run_command([git, "-C", str(root), "status", "--porcelain=v1", "--untracked-files=normal", "--", relative],
                         root, timeout, ctx)
    if any(r.timed_out for r in (head, branch, tracked, status)):
        check.degrade("partial", f"Um comando git excedeu {timeout:.0f} s.")
    tracked_files = len([line for line in tracked.stdout.splitlines() if line.strip()])
    entries = [line for line in status.stdout.splitlines() if line.strip()]
    check.data.update(
        git_root=root.as_posix(), project_relative_path=relative,
        commit=head.stdout.strip() or None, branch=branch.stdout.strip() or None,
        tracked_files=tracked_files, status_entries=len(entries),
        project_untracked=any(line[3:].rstrip("/") == relative for line in entries if line.startswith("??")),
    )
    check.add_evidence("command", "git status --porcelain -- " + relative,
                       f"{len(entries)} entrada(s); {tracked_files} arquivo(s) rastreado(s) em {relative}")
    if not check.note:
        check.note = (f"Raiz Git {root.as_posix()} · commit {(check.data['commit'] or '—')[:10]} · "
                      f"{tracked_files} arquivo(s) do projeto rastreado(s).")


def collect_plastic(ctx: Context, check: CheckResult) -> None:
    project = ctx.config.project_root
    meta = project / ".plastic"
    if not meta.is_dir():
        check.data["plastic"] = None
        return
    selector = (meta / "plastic.selector")
    text = read_head(selector) if selector.exists() else ""
    branch = _SELECTOR_BRANCH.search(text)
    repo = _SELECTOR_REPO.search(text)
    info = {"workspace": True, "repository": repo.group(1) if repo else None,
            "branch": branch.group(1) if branch else None,
            "selector_changeset": int(branch.group(2)) if branch and branch.group(2) else None}
    check.add_evidence("file", selector.as_posix(), f"branch {info['branch']} · repositório {info['repository']}")
    cm = ctx.config.plastic_cm
    if cm is None or not cm.exists():
        info["status"] = "cm_unavailable"
        check.data["plastic"] = info
        check.degrade("partial", "Workspace do Unity Version Control detectado, mas o cm.exe não foi encontrado.")
        return
    result = run_command([str(cm), "status", "--machinereadable", "--fieldseparator=;"], project,
                         ctx.config.command_timeout_seconds, ctx)
    if result.code != 0 or result.timed_out:
        info["status"] = "timeout" if result.timed_out else "error"
        check.data["plastic"] = info
        check.degrade("partial", f"cm status falhou: {(result.stderr or result.stdout).strip()[:200] or 'timeout'}")
        return
    lines = [line.split(";") for line in result.stdout.splitlines() if line.strip()]
    header = next((parts for parts in lines if parts[0] == "STATUS"), None)
    items = [(parts[0], _rel(project, parts[1])) for parts in lines if parts[0] != "STATUS" and len(parts) > 1]
    counts = Counter(kind for kind, _ in items)
    pending = sum(n for kind, n in counts.items() if kind in PENDING)
    info.update(status="ok", changeset=int(header[1]) if header and header[1].isdigit() else None,
                pending=pending, private=counts.get("PR", 0), by_type=dict(counts))
    check.data["plastic"] = info
    check.data["dirty"] = pending > 0
    evidence = check.add_evidence("command", "cm status --machinereadable",
                                  f"changeset {info['changeset']} · {pending} pendente(s) · {info['private']} privado(s)")
    deleted = [path for kind, path in items if kind.endswith("LD")]
    if deleted:
        check.findings.append(Finding(
            rule="vcs.locally-deleted", severity="medium", state="confirmed", key="plastic",
            summary=f"{len(deleted)} item(ns) controlado(s) foram apagados do disco sem registrar a exclusão",
            evidence=[evidence], occurrences=len(deleted), file=deleted[0],
            recommendation="Confirme no Unity Version Control se a exclusão é intencional (Delete) ou restaure "
                           "os arquivos. Exemplos: " + ", ".join(deleted[:6]),
        ))
    private_scripts = [path for kind, path in items if kind == "PR" and path.endswith(".cs")
                       and path.startswith("Assets/") and "~/" not in path]
    if private_scripts:
        check.findings.append(Finding(
            rule="vcs.private-scripts", severity="medium", state="confirmed", key="plastic",
            summary=f"{len(private_scripts)} script(s) C# em Assets fora do controle de versão",
            evidence=[evidence], occurrences=len(private_scripts), file=private_scripts[0],
            recommendation="Adicione ao Unity Version Control ou ignore explicitamente. Exemplos: "
                           + ", ".join(private_scripts[:6]),
        ))


def collect(ctx: Context, check: CheckResult) -> None:
    collect_git(ctx, check)
    ctx.check_cancel()
    collect_plastic(ctx, check)
    plastic = check.data.get("plastic") or {}
    git_has_project = (check.data.get("tracked_files") or 0) > 0
    check.data["vcs"] = "plastic" if plastic else ("git" if git_has_project else None)
    check.data["source_state"] = "working_tree"
    ctx.shared["vcs"] = check.data  # identidade do snapshot da auditoria completa
    if check.data.get("git_root") and not git_has_project and plastic:
        check.findings.append(Finding(
            rule="vcs.git-parent-without-project", severity="info", state="confirmed", key="git-parent",
            summary="O Git da pasta pai não contém o DiceVTT; o versionamento real é o Unity Version Control",
            evidence=[check.evidence[0].id] if check.evidence else [],
            recommendation="Uma auditoria completa não pode usar git worktree: o snapshot isolado precisa sair "
                           "do Unity Version Control ou de uma cópia da pasta.",
        ))
    elif not git_has_project and not plastic and check.data.get("tracked_files") is not None:
        check.findings.append(Finding(
            rule="vcs.unversioned", severity="high", state="confirmed", key="project",
            summary="Nenhum controle de versão encontrado para o projeto",
            recommendation="Configure Git ou Unity Version Control antes de qualquer correção automática.",
        ))
    if plastic.get("status") == "ok":
        check.note = (f"Unity Version Control · {plastic.get('branch') or '?'} · changeset {plastic.get('changeset')} · "
                      f"{plastic.get('pending')} alteração(ões) pendente(s), {plastic.get('private')} item(ns) privado(s).")
