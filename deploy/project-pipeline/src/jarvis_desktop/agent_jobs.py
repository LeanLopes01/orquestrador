"""Long jobs of the coding agents on this PC, started by the JARVIS orchestrator.

A job is one run of a CLI: the planner chosen for the request ("coordinate":
Codex in a read-only sandbox, or Antigravity in plan mode, both on a read-only
copy) or an agent working on a task (Codex, Claude Code or Antigravity) inside the
run's work copy of the project. A coordinate job without an agent comes from a
server older than planner routing, which only knew Antigravity. Starting a job returns at once; the result goes back to the
server as a "job_update" message and is repeated until the server acknowledges it.

Each job's state is a file in %LOCALAPPDATA%/JarvisDesktop/jobs, so a helper
restart cannot lose a result. A job found "running" after a restart is finished from
its saved output when the CLI had already exited (exit.json); otherwise it is
reported as "unknown": it is never started again automatically, since it may
already have changed files.

Arguments are lists (no shell, no .cmd shims); Claude and Codex read the prompt
from stdin, Antigravity (no stdin prompt) gets it as one argument of a native exe.
An exhausted quota is reported with its release time when the CLI gives one; the
job is never repeated for it, nor handed to another agent.
The CLIs run without a console window: the helper runs under pythonw, and Windows
would otherwise open an empty console for each one. Their JSON streams feed the
live telemetry (job_stream). Cancelling kills only this job's process tree.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from .coding import redact
from .credentials import local_dir
from .job_stream import StreamTelemetry, final_line
from .workspaces import (
    WorkspaceError,
    apply_to_project,
    changes,
    clean_copies,
    copy_from_reference,
    copy_project,
    keep_reference,
    load_manifest,
    manifest,
    projects,
    seed_reference,
    work_root,
)

logger = logging.getLogger("jarvis_desktop")

KINDS = ("coordinate", "execute")
AGENTS = ("codex", "claude", "antigravity")
# Planners this helper runs for "coordinate" jobs (announced to the server).
PLANNERS = ("codex", "antigravity")
# Executors this helper runs for "execute" jobs (announced to the server).
EXECUTORS = ("claude", "antigravity", "codex")
ROUTING_VERSION = 1
OUTPUT_LIMIT = 200_000
CONTEXT_TIMEOUT = 30.0
PROMPT_ARGUMENT_LIMIT = 30_000
# Headless Claude cannot ask for approval: anything not listed is refused. Bash
# only gets reading commands (grep, cat, ls... are already read-only for Claude).
CLAUDE_TOOLS = (
    "Read",
    "Edit",
    "MultiEdit",
    "Write",
    "Glob",
    "Grep",
    "Bash(ls:*)",
    "Bash(git status:*)",
    "Bash(git diff:*)",
    "Bash(git log:*)",
    "Bash(git show:*)",
)
# Told to Claude so it looks there instead of searching the disk: the Unity
# editors hold the built-in packages and shaders the projects depend on.
UNITY_EDITORS = (
    Path(os.environ.get("PROGRAMFILES", "C:/Program Files")) / "Unity/Hub/Editor"
)
CLAUDE_POLICY = (
    "You run unattended: a tool call outside the allowed list is refused and nobody "
    "can approve it. Read, Glob and Grep work on any folder; use them to look at "
    "files outside the project too. Bash only runs reading commands (grep, cat, "
    "head, ls, find without -exec, git status/diff/log/show) on known paths, never "
    "a search of the whole disk; PowerShell and anything that writes or runs "
    "programs are refused.{unity} If you still cannot find what you need, say what "
    "is missing instead of trying other ways around the refusal."
)
# Headless Antigravity ends the turn without output when a tool is refused. The
# coordinator then gets one more turn in the same conversation, told why.
RETRY_PROMPT = (
    "Your last command was refused by the read-only policy; do not run it again. "
    "Allowed: one pipeline of reading commands (Get-ChildItem, Get-Content, "
    "Select-String, rg, findstr), optionally piped to Select-Object, Sort-Object, "
    "Measure-Object or Select-String. Outside quotes there must be no ;, &, $, "
    "backticks, parentheses, braces, redirection or line breaks. Put any text with "
    "| ( ) { } in single quotes, for example: Get-ChildItem -Recurse -Filter *.cs | "
    "Select-String -Pattern 'Skin|Texture' | Select-Object -ExpandProperty Path "
    "-Unique. If you still cannot read what you need, do not try other ways around "
    "the refusal: answer with what you checked and list what is missing, in the "
    "required JSON format."
)
EXECUTE_RETRY_PROMPT = (
    "Your last terminal command was refused by the unattended policy; do not run it "
    "again. In accept-edits mode, read, edit and create files directly with your file "
    "tools instead of terminal commands. Terminal commands only allow one read-only "
    "search pipeline (Get-ChildItem, Get-Content, Select-String, rg, findstr), "
    "optionally piped to Select-Object, Sort-Object, Measure-Object or Select-String, "
    "with no ;, &, $, backticks, parentheses, braces, redirection or line breaks "
    "outside quotes. Continue the task with your file tools and finish with your "
    "short report."
)


ACTIVE = {"queued", "preparing", "running"}
FINAL_ACTIVITY = {
    "completed": "Concluído",
    "failed": "Falhou",
    "cancelled": "Cancelado",
    "unknown": "Interrompido",
}
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
AGENT_NAMES = {"codex": "Codex", "claude": "Claude Code", "antigravity": "Antigravity"}
QUOTA_SIGNS = re.compile(
    r"usage limit|rate.?limit|quota|resource.?exhausted|too many requests"
    r"|\b429\b|limit (?:reached|exceeded)|exceeded your",
    re.IGNORECASE,
)
RETRY_AT = re.compile(
    r"(?:try again|retry|resets?|available again)\s+(?:at|in|after|on)\s+"
    r"([^.\n\"]{3,60})",
    re.IGNORECASE,
)
# npm installs Codex as codex.CMD; the native binary sits in the platform package.
CODEX_NATIVE = (
    "@openai/codex-win32-x64/vendor/x86_64-pc-windows-msvc/bin/codex.exe",
    "@openai/codex-win32-arm64/vendor/aarch64-pc-windows-msvc/bin/codex.exe",
)


def jobs_dir() -> Path:
    return local_dir() / "jobs"


def _exe(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise WorkspaceError(f"{name} is not installed on this computer")
    if found.lower().endswith((".cmd", ".bat")):
        if name == "codex":
            return _codex_native(Path(found))
        # cmd.exe would open a console and cut multi-line arguments.
        raise WorkspaceError(f"{name} is only installed as a script ({found})")
    return found


def _codex_native(shim: Path) -> str:
    modules = shim.parent / "node_modules"
    for base in (modules / "@openai/codex/node_modules", modules):
        for relative in CODEX_NATIVE:
            if (base / relative).exists():
                return str(base / relative)
    raise WorkspaceError(
        f"codex.exe not found next to {shim}; reinstall Codex (npm i -g @openai/codex)"
    )


def active_jobs(directory: Path | None = None) -> list[str]:
    """One line per job still running, read from the job files (no helper needed)."""
    lines = []
    for path in sorted((directory or jobs_dir()).glob("*.json")):
        with contextlib.suppress(OSError, ValueError):
            job = json.loads(path.read_text(encoding="utf-8"))
            if job.get("state") in ACTIVE:
                stage = (job.get("progress") or {}).get("activity") or job["state"]
                name = AGENT_NAMES.get(job.get("agent") or "antigravity", "agent")
                lines.append(f"{job['id'][:8]} {job['kind']} {name}: {stage}")
    return lines


def _agent(job: dict[str, Any]) -> str | None:
    # Coordinate jobs saved before planner routing had no agent: Antigravity.
    if job["kind"] == "coordinate":
        return job.get("agent") or "antigravity"
    return job.get("agent")


def stdin_for(job: dict[str, Any]) -> bytes | None:
    """Claude and Codex read the prompt from stdin (no command-line length limit)."""
    if _agent(job) in {"claude", "codex"}:
        return job["prompt"].encode("utf-8")
    return None


def quota_info(texts: list[Any]) -> dict[str, Any] | None:
    """An exhausted quota or rate limit in a failed job's errors, with the release
    time when the CLI states one."""
    for text in texts:
        if isinstance(text, str) and QUOTA_SIGNS.search(text):
            found = RETRY_AT.search(text)
            return {
                "quota_exhausted": True,
                "retry_at": found.group(1).strip() if found else None,
                "quota_message": redact(text.strip())[:300],
            }
    return None


def command_for(job, cwd, files):
    try:
        from ..project_pipeline import model_flags
    except ImportError:
        from project_pipeline import model_flags
    flags = model_flags(_agent(job), job.get("model", ""), job.get("effort", ""))
    args = _base_command_for(job, cwd, files)
    insert = 2 if _agent(job) == "codex" else 1
    return args[:insert] + flags + args[insert:]


def _base_command_for(job: dict[str, Any], cwd: Path, files: Path) -> list[str]:
    """The CLI call for a job. Never a shell string."""
    prompt = job["prompt"]
    if job["kind"] == "coordinate":
        schema = files / "schema.json"
        schema.write_text(json.dumps(job["schema"]), encoding="utf-8")
        if _agent(job) == "codex":
            # Read-only sandbox on the reference copy; the final message must
            # follow the schema (checked again in read_result).
            return [
                _exe("codex"),
                "exec",
                "-C",
                str(cwd),
                "-s",
                "read-only",
                "--skip-git-repo-check",
                "--json",
                "--output-schema",
                str(schema),
                "-o",
                str(files / "last_message.txt"),
                "-",  # prompt on stdin
            ]
        args = [
            _exe("agy"),
            "-p",
            prompt,
            "--mode",
            "plan",
            "--output-format",
            "stream-json",
            "--json-schema",
            str(schema),
            "--print-timeout",
            f"{int(job['timeout'])}s",
            "--add-dir",
            str(cwd),
        ]
        if job.get("agy_conversation_id"):
            args += ["--conversation", job["agy_conversation_id"]]
        return args
    agent = job["agent"]
    if agent == "codex":
        return [
            _exe("codex"),
            "exec",
            "-C",
            str(cwd),
            "-s",
            "workspace-write",
            "--skip-git-repo-check",
            "--json",
            "-o",
            str(files / "last_message.txt"),
            "-",  # prompt on stdin
        ]
    if agent == "claude":
        unity = (
            f" Unity editors (built-in packages, shaders): {UNITY_EDITORS}."
            if UNITY_EDITORS.is_dir()
            else ""
        )
        return [
            _exe("claude"),
            "-p",  # prompt on stdin
            "--output-format",
            "stream-json",
            "--verbose",  # required by stream-json in print mode
            "--permission-mode",
            "acceptEdits",
            "--append-system-prompt",
            CLAUDE_POLICY.format(unity=unity),
            "--allowedTools",
            *CLAUDE_TOOLS,
        ]
    if agent == "antigravity":
        args = [
            _exe("agy"),
            "-p",
            prompt,
            "--mode",
            "accept-edits",
            "--output-format",
            "stream-json",
            "--print-timeout",
            f"{int(job['timeout'])}s",
            "--add-dir",
            str(cwd),
        ]
        if job.get("agy_conversation_id"):
            args += ["--conversation", job["agy_conversation_id"]]
        return args
    raise WorkspaceError(f"unknown agent {agent}")


def read_result(job: dict[str, Any], stdout: str, files: Path) -> dict[str, Any]:
    """What the CLI reported, with honest failure signals (denied tools, no output)."""
    result: dict[str, Any] = {"exit_code": job.get("exit_code")}
    data: dict[str, Any] = {}
    agent = _agent(job)
    if agent in {"claude", "antigravity"}:
        data = final_line(stdout)
    if agent == "antigravity":
        result.update(
            agy_conversation_id=data.get("conversation_id"),
            status=data.get("status"),
            text=data.get("response"),
            structured=data.get("structured_output"),
            denied=data.get("denied_actions") or [],
            usage=data.get("usage"),
        )
    elif agent == "claude":
        result.update(
            text=data.get("result"),
            session_id=data.get("session_id"),
            is_error=data.get("is_error"),
            denied=data.get("permission_denials") or [],
            model=data.get("model") or (next(iter(data.get("modelUsage") or {}), None)),
        )
    elif agent == "codex":
        last = files / "last_message.txt"
        result["text"] = (
            last.read_text(encoding="utf-8", errors="replace")
            if last.exists()
            else None
        )
        for line in stdout.splitlines():
            with contextlib.suppress(ValueError):
                event = json.loads(line)
                if event.get("type") == "thread.started":
                    result["thread_id"] = event.get("thread_id")
                if event.get("type") in {"turn.failed", "error"}:
                    result.setdefault("errors", []).append(str(event)[:500])
                if event.get("type") == "turn.completed" and isinstance(
                    event.get("usage"), dict
                ):
                    result["usage"] = event["usage"]
        if job["kind"] == "coordinate":
            with contextlib.suppress(ValueError, TypeError):
                structured = json.loads(result["text"] or "")
                if isinstance(structured, dict):
                    result["structured"] = structured
            if not result.get("structured"):
                result["problem"] = (
                    "o Codex terminou sem o resultado estruturado exigido"
                )
    ok = (
        job.get("exit_code") == 0
        and not result.get("is_error")
        and not result.get("errors")
    )
    if job["kind"] == "coordinate":
        ok = ok and isinstance(result.get("structured"), dict)
    if result.get("denied"):
        # A tool the agent needed was refused: the turn may look successful but is not.
        result["problem"] = f"tools refused: {result['denied']}"
        ok = ok and job["kind"] != "coordinate" and bool(result.get("text"))
    result["ok"] = bool(ok)
    return result


class JobManager:
    def __init__(
        self,
        directory: Path | None = None,
        *,
        notify: Callable[[dict[str, Any]], None] | None = None,
        context: Callable[[str], Awaitable[str]] | None = None,
    ) -> None:
        self.dir = directory or jobs_dir()
        self.dir.mkdir(parents=True, exist_ok=True)
        self.notify = notify
        # Extra context for a planner's prompt (the DiceVTT RAG, planning_context.py).
        self.context = context
        # The shared reference copy is synchronised only while no planner reads it.
        self._reference_lock = threading.Lock()
        self._readers: dict[str, set[str]] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._procs: dict[str, asyncio.subprocess.Process] = {}
        self._sent_at: dict[str, float] = {}
        self.command_for = command_for  # replaced in tests
        self.stdin_for = stdin_for
        for job in self._all():
            if job["state"] in ACTIVE:
                if (self.dir / job["id"] / "exit.json").exists():
                    # The CLI had finished; only the bookkeeping was interrupted.
                    self._tasks[job["id"]] = asyncio.ensure_future(self._recover(job))
                    continue
                job.update(
                    state="unknown",
                    finished_at=time.time(),
                    result={
                        "ok": False,
                        "problem": "the helper restarted while this job ran",
                    },
                )
                self._save(job)

    # Persistence

    def _path(self, job_id: str) -> Path:
        if not job_id.replace("-", "").isalnum() or len(job_id) > 80:
            raise WorkspaceError("bad job id")
        return self.dir / f"{job_id}.json"

    def _save(self, job: dict[str, Any]) -> None:
        with tempfile.NamedTemporaryFile(
            "w", dir=self.dir, delete=False, suffix=".tmp", encoding="utf-8"
        ) as tmp:
            json.dump(job, tmp, ensure_ascii=False)
        # On Windows the rename fails while another thread is reading the file.
        for attempt in range(50):
            try:
                os.replace(tmp.name, self._path(job["id"]))
                return
            except PermissionError:
                if attempt == 49:
                    raise
                time.sleep(0.02)

    def get(self, job_id: str) -> dict[str, Any] | None:
        path = self._path(job_id)
        try:
            return (
                json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
            )
        except ValueError:
            return None

    def _all(self) -> list[dict[str, Any]]:
        jobs = []
        for path in self.dir.glob("*.json"):
            with contextlib.suppress(OSError, ValueError):
                jobs.append(json.loads(path.read_text(encoding="utf-8")))
        return jobs

    # Starting and stopping

    def start(self, params: dict[str, Any]) -> dict[str, Any]:
        job_id = str(params.get("job_id") or "")
        existing = self.get(job_id)
        if existing is not None:
            return {"job_id": job_id, "state": existing["state"]}  # sent twice
        kind = params.get("kind")
        if kind not in KINDS:
            raise WorkspaceError("unknown job kind")
        if kind == "execute" and params.get("agent") not in AGENTS:
            raise WorkspaceError("unknown agent")
        agent = params.get("agent")
        if kind == "coordinate":
            agent = agent or "antigravity"  # a server from before planner routing
            if agent not in PLANNERS:
                raise WorkspaceError(f"planner not supported here: {agent}")
        project = projects().get(str(params.get("project")))
        if project is None:
            raise WorkspaceError("unknown project")
        job = {
            "id": job_id,
            "kind": kind,
            "project": project.key,
            "agent": agent,
            "planning_agent": params.get("planning_agent"),
            "execution_agent": params.get("execution_agent"),
            "model": params.get("model", ""),
            "effort": params.get("effort", ""),
            "stage": params.get("stage"),
            "conversation_id": params.get("conversation_id"),
            "run_id": params.get("run_id"),
            "task_id": params.get("task_id"),
            "agy_conversation_id": params.get("agy_conversation_id"),
            "prompt": str(params.get("prompt") or "")[:60_000],
            "schema": params.get("schema"),
            "timeout": min(max(float(params.get("timeout") or 600), 30), 4 * 3600),
            "state": "queued",
            "created_at": time.time(),
            "finished_at": None,
            "result": None,
        }
        self._save(job)
        self._tasks[job_id] = asyncio.ensure_future(self._run(job))
        return {"job_id": job_id, "state": "queued"}

    async def cancel(self, job_id: str) -> dict[str, Any]:
        job = self.get(job_id)
        if job is None:
            return {"job_id": job_id, "state": "unknown_job"}
        task = self._tasks.get(job_id)
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await asyncio.wait_for(asyncio.shield(task), 15)
        job = self.get(job_id) or job
        return {"job_id": job_id, "state": job["state"]}

    async def _kill(self, proc: asyncio.subprocess.Process) -> None:
        """This job's process and its children only."""
        if proc.returncode is not None:
            return
        try:
            import psutil

            parent = psutil.Process(proc.pid)
            for child in parent.children(recursive=True):
                with contextlib.suppress(psutil.Error):
                    child.kill()
            parent.kill()
        except Exception:
            with contextlib.suppress(ProcessLookupError):
                proc.kill()
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(proc.wait(), 10)

    # Running

    def _workspace(self, job: dict[str, Any]) -> Path:
        project = projects()[job["project"]]
        root = work_root() / project.key
        last_progress = 0.0

        def progress(done: int, total: int) -> None:
            nonlocal last_progress
            if job["state"] != "preparing":
                raise WorkspaceError("Workspace preparation cancelled")
            now = time.monotonic()
            if done not in (0, total) and now - last_progress < 2:
                return
            last_progress = now
            job["progress"] = {
                "stage": f"Atualizando cópia isolada: {done} de {total} arquivos alterados",
                "stdout_tail": "Só os arquivos alterados desde a última cópia são copiados. O projeto original permanece sem alterações.",
            }
            self._save(job)

        work = root / "runs" / str(job.get("run_id")) / "work"
        if job["kind"] == "execute" and (work.parent / "work.manifest.json").exists():
            return work  # a later task of the same run
        reference = root / "reference"
        with self._reference_lock:
            readers = self._readers.setdefault(project.key, set())
            if not reference.exists():
                self._seed(project, root, reference)
            if readers and (root / "reference.manifest.json").exists():
                # Another planner is reading it: use it as it is, unsynchronised.
                job["copy"] = {
                    **json.loads(
                        (root / "reference.info.json").read_text(encoding="utf-8")
                    ),
                    "synced": False,
                }
            else:
                job["copy"] = copy_project(project, reference, on_progress=progress)
            if job["kind"] == "coordinate":
                readers.add(job["id"])
                return reference
            self._clean(project.key)
            job["copy"] = {
                **copy_from_reference(reference, work, on_progress=progress),
                "synced": job["copy"].get("synced", True),
            }
            keep_reference(work)
        return work

    def _seed(self, project: Any, root: Path, reference: Path) -> None:
        """First run after the shared reference: start from the newest old copy."""
        busy = self._in_use()
        olds = sorted(
            (root / "conversations").glob("*/reference"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old in olds:
            if old not in busy and seed_reference(reference, old, project):
                logger.info("reference copy seeded from %s", old.parent.name)
                return

    def _in_use(self) -> set[Path]:
        return {
            Path(job["cwd"])
            for job in self._all()
            if job.get("state") in ACTIVE and job.get("cwd")
        }

    def _clean(self, key: str) -> None:
        root = work_root() / key
        removed = clean_copies(root, self._in_use())
        if removed:
            logger.info("removed %d old copies of %s", len(removed), key)

    def clean(self) -> None:
        """At start-up: seed the shared reference and delete copies nobody needs."""
        for project in projects().values():
            root = work_root() / project.key
            if not root.is_dir():
                continue
            try:
                with self._reference_lock:
                    if not (root / "reference").exists():
                        self._seed(project, root, root / "reference")
                    self._clean(project.key)
            except OSError:
                logger.exception("could not clean the copies of %s", project.key)

    async def _run(self, job: dict[str, Any]) -> None:
        files = self.dir / job["id"]
        files.mkdir(exist_ok=True)
        proc: asyncio.subprocess.Process | None = None
        try:
            job["state"] = "preparing"
            job["progress"] = {"stage": "Preparando cópia isolada do projeto"}
            self._save(job)
            cwd = await asyncio.to_thread(self._workspace, job)
            if job["kind"] == "coordinate" and self.context is not None:
                await self._add_context(job)
            args = self.command_for(job, cwd, files)
            agent = job.get("agent") or "antigravity"  # the coordinator is Antigravity
            job.update(
                state="running",
                started_at=time.time(),
                cwd=str(cwd),
                command=[*args[:1], "…"],
                progress={
                    "stage": "running",
                    "activity": f"Iniciando {AGENT_NAMES.get(agent, agent)}",
                },
            )
            self._save(job)
            self._notify(job)
            current = job
            refused: list[str] = []  # exact commands refused, for the diagnosis
            for attempt in range(2):
                (files / "exit.json").unlink(missing_ok=True)
                stdin = self.stdin_for(current)
                proc = await asyncio.create_subprocess_exec(
                    *args,
                    cwd=cwd,
                    stdin=asyncio.subprocess.PIPE
                    if stdin is not None
                    else asyncio.subprocess.DEVNULL,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    creationflags=NO_WINDOW,
                )
                self._procs[job["id"]] = proc
                job["pid"] = proc.pid
                self._save(job)
                telemetry = StreamTelemetry(job["id"], agent)
                try:
                    stdout, stderr = await asyncio.wait_for(
                        self._communicate_progress(proc, job, telemetry, stdin),
                        job["timeout"] + 30,
                    )
                except asyncio.TimeoutError:
                    await self._kill(proc)
                    raise TimeoutError(
                        f"no result within {int(job['timeout'])} s"
                    ) from None
                job["exit_code"] = proc.returncode
                out = stdout.decode("utf-8", errors="replace")
                err = stderr.decode("utf-8", errors="replace")
                (files / f"stdout{attempt or ''}.txt").write_text(
                    out[-OUTPUT_LIMIT:], encoding="utf-8"
                )
                (files / f"stderr{attempt or ''}.txt").write_text(
                    err[-OUTPUT_LIMIT:], encoding="utf-8"
                )
                # Written last: a restart after this point finishes from these files.
                (files / "exit.json").write_text(
                    json.dumps({"exit_code": proc.returncode, "attempt": attempt}),
                    encoding="utf-8",
                )
                result = read_result(job, out, files)
                refused += telemetry.denied
                retry = (
                    attempt == 0
                    and agent == "antigravity"
                    and not result["ok"]
                    and result.get("denied")
                    and result.get("agy_conversation_id")
                )
                if not retry:
                    break
                logger.info(
                    "job %s: a tool was refused; asking %s again",
                    job["id"][:8],
                    agent,
                )
                job["agy_conversation_id"] = result["agy_conversation_id"]
                retry_prompt = (
                    RETRY_PROMPT
                    if job["kind"] == "coordinate"
                    else EXECUTE_RETRY_PROMPT
                )
                current = {**job, "prompt": retry_prompt}
                args = self.command_for(current, cwd, files)
                job["first_attempt_denied"] = result.get("denied")
            if refused:
                result["denied_commands"] = refused[:5]
                if not result["ok"] and agent == "antigravity":
                    result["problem"] = (
                        "comando recusado pela política somente leitura do "
                        f"Antigravity (modo headless não pede permissão): {refused[-1]}"
                    )
            result = await self._finish(job, result, err)
            job.update(state="completed" if result["ok"] else "failed", result=result)
        except asyncio.CancelledError:
            if proc is not None:
                await self._kill(proc)
            job.update(
                state="cancelled", result={"ok": False, "problem": "stopped on request"}
            )
        except Exception as exc:
            logger.exception("job %s failed", job["id"])
            job.update(
                state="failed",
                result={"ok": False, "problem": f"{type(exc).__name__}: {exc}"[:600]},
            )
        finally:
            self._close(job)

    async def _add_context(self, job: dict[str, Any]) -> None:
        """Relevant files and documentation for the planner, appended to its prompt.
        Optional: without the RAG the planner simply searches the copy itself."""
        assert self.context is not None
        job["progress"] = {"stage": "Consultando o RAG do projeto"}
        self._save(job)
        try:
            extra = await asyncio.wait_for(self.context(job["prompt"]), CONTEXT_TIMEOUT)
        except Exception as exc:
            logger.warning("job %s: no RAG context (%s)", job["id"][:8], exc)
            job["rag_context"] = {"used": False, "reason": str(exc)[:200]}
            return
        # Antigravity gets the prompt as one argument (Windows limit: 32,767 chars).
        room = PROMPT_ARGUMENT_LIMIT - len(job["prompt"])
        if not extra or (_agent(job) == "antigravity" and len(extra) > room):
            job["rag_context"] = {"used": False, "reason": "no room or no match"}
            return
        job["prompt"] += "\n\n" + extra
        job["rag_context"] = {"used": True, "chars": len(extra)}
        self._save(job)

    async def _finish(
        self, job: dict[str, Any], result: dict[str, Any], stderr: str
    ) -> dict[str, Any]:
        """After the CLI exits: check the copy. Shown as its own stage (can take a while)."""
        job["progress"] = {
            **(job.get("progress") or {}),
            "stage": "finishing",
            "activity": "Verificando as alterações na cópia isolada",
        }
        self._save(job)
        self._notify(job)
        if job["kind"] == "coordinate":
            # Plan mode must not change the reference copy. If it did, the next sync
            # puts the touched files back (their times no longer match the index).
            reference = Path(job["cwd"])
            expected = load_manifest(reference)
            now = await asyncio.to_thread(manifest, reference)
            if now != expected:
                result["reference_changed"] = sorted(
                    p for p in set(now) | set(expected) if now.get(p) != expected.get(p)
                )[:50]
        if job["kind"] == "execute":
            work = Path(job["cwd"])
            result["changes"] = await asyncio.to_thread(
                changes, work, load_manifest(work)
            )
        if job.get("first_attempt_denied"):
            result["first_attempt_denied"] = job["first_attempt_denied"]
        if not result.get("ok"):
            quota = quota_info(
                [*result.get("errors", []), stderr[-4000:], result.get("text")]
            )
            if quota:
                result.update(quota)
                name = AGENT_NAMES.get(_agent(job) or "", "agente")
                result["problem"] = (
                    f"cota ou limite de uso do {name} esgotado"
                    + (
                        f"; liberação informada: {quota['retry_at']}"
                        if quota["retry_at"]
                        else "; o CLI não informou quando libera"
                    )
                    + ". Nenhuma nova tentativa automática nem troca de agente."
                )
        result["stderr_tail"] = stderr[-1500:]
        return result

    async def _recover(self, job: dict[str, Any]) -> None:
        """A restart hit between the CLI's exit and the end of the bookkeeping."""
        files = self.dir / job["id"]
        try:
            info = json.loads((files / "exit.json").read_text(encoding="utf-8"))
            suffix = info.get("attempt") or ""
            out = (files / f"stdout{suffix}.txt").read_text(encoding="utf-8")
            err = (files / f"stderr{suffix}.txt").read_text(encoding="utf-8")
            job["exit_code"] = info.get("exit_code")
            result = await self._finish(job, read_result(job, out, files), err)
            result["recovered"] = (
                "o helper reiniciou depois que o CLI terminou; resultado lido dos "
                "arquivos salvos"
            )
            job.update(state="completed" if result["ok"] else "failed", result=result)
            logger.info("job %s: finished from saved output", job["id"][:8])
        except Exception as exc:
            logger.exception("job %s could not be recovered", job["id"])
            job.update(
                state="unknown",
                result={
                    "ok": False,
                    "problem": f"the helper restarted while this job ran ({exc})"[:600],
                },
            )
        finally:
            self._close(job)

    def _close(self, job: dict[str, Any]) -> None:
        with self._reference_lock:
            self._readers.get(job.get("project", ""), set()).discard(job["id"])
        job["finished_at"] = time.time()
        problem = (job.get("result") or {}).get("problem")
        job["progress"] = {
            **(job.get("progress") or {}),
            "stage": job["state"],
            "activity": FINAL_ACTIVITY.get(job["state"], job["state"])
            + (f": {redact(str(problem))[:300]}" if problem else ""),
        }
        if "copy" in job and isinstance(job.get("result"), dict):
            job["result"]["copy"] = job["copy"]  # where the copy came from
        self._save(job)
        self._procs.pop(job["id"], None)
        logger.info(
            "job %s (%s %s) -> %s",
            job["id"][:8],
            job["kind"],
            job.get("agent") or "",
            job["state"],
        )
        self._notify(job)

    def _notify(self, job: dict[str, Any]) -> None:
        if self.notify is not None:
            self.notify(self._message(job))

    # Reporting to the server

    async def _communicate_progress(
        self,
        proc,
        job,
        telemetry: StreamTelemetry | None = None,
        stdin: bytes | None = None,
    ):
        tails = {"stdout": bytearray(), "stderr": bytearray()}

        async def feed():
            try:
                proc.stdin.write(stdin)
                await proc.stdin.drain()
            except (BrokenPipeError, ConnectionResetError):
                pass  # the CLI exited before reading everything; its output says why
            finally:
                with contextlib.suppress(Exception):
                    proc.stdin.close()

        async def consume(stream, key):
            while chunk := await stream.read(4096):
                tails[key].extend(chunk)
                if len(tails[key]) > OUTPUT_LIMIT:
                    del tails[key][:-OUTPUT_LIMIT]
                if key == "stdout" and telemetry is not None:
                    telemetry.feed(chunk)

        def snapshot() -> dict[str, Any]:
            return {
                "stage": job["state"],
                **{
                    f"{key}_tail": redact(
                        bytes(value).decode("utf-8", errors="replace")[-6000:]
                    )
                    for key, value in tails.items()
                },
                **(telemetry.snapshot() if telemetry is not None else {}),
            }

        async def report():
            # A heartbeat every 3 s even when the CLI prints nothing.
            while True:
                job["progress"] = snapshot()
                self._save(job)
                self._notify(job)
                await asyncio.sleep(3)

        reporter = asyncio.create_task(report())
        work = [
            consume(proc.stdout, "stdout"),
            consume(proc.stderr, "stderr"),
            proc.wait(),
        ]
        if stdin is not None and proc.stdin is not None:
            work.append(feed())
        try:
            await asyncio.gather(*work)
            return bytes(tails["stdout"]), bytes(tails["stderr"])
        finally:
            reporter.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reporter
            job["progress"] = snapshot()

    @staticmethod
    def _message(job: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "job_progress"
            if job["state"] in {"queued", "preparing", "running"}
            else "job_update",
            "job": {
                k: job.get(k)
                for k in (
                    "id",
                    "kind",
                    "agent",
                    "state",
                    "conversation_id",
                    "run_id",
                    "task_id",
                    "created_at",
                    "started_at",
                    "finished_at",
                    "result",
                    "progress",
                )
            },
        }

    def due(self, now: float | None = None) -> list[dict[str, Any]]:
        """Live snapshots every three seconds, final results until acknowledged."""
        now = time.time() if now is None else now
        messages = []
        for job in self._all():
            active = job["state"] in {"queued", "preparing", "running"}
            if job.get("acked") and not active:
                continue
            key = f"{job['id']}:{job['state']}"
            if now - self._sent_at.get(key, 0) < (3 if active else 30):
                continue
            self._sent_at[key] = now
            messages.append(self._message(job))
        return messages

    def acknowledge(self, job_id: str) -> None:
        job = self.get(job_id)
        if job is not None and job["state"] not in {"queued", "preparing", "running"}:
            job["acked"] = True
            self._save(job)

    def status(self, job_ids: list[str]) -> dict[str, Any]:
        return {
            job_id: (self.get(job_id) or {}).get("state", "unknown_job")
            for job_id in job_ids[:100]
        }

    def apply(self, params: dict[str, Any]) -> dict[str, Any]:
        project = projects().get(str(params.get("project")))
        if project is None:
            raise WorkspaceError("unknown project")
        work = work_root() / project.key / "runs" / str(params.get("run_id")) / "work"
        if not work.exists():
            raise WorkspaceError("this run has no work copy on this computer")
        return apply_to_project(project, work, load_manifest(work))
