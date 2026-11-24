from pathlib import Path

root = Path(__file__).resolve().parents[1] / ".local/jarvis-work"


def edit(name, old, new):
    p = root / name
    s = p.read_text(encoding="utf-8")
    assert old in s, (name, old[:100])
    p.write_text(s.replace(old, new), encoding="utf-8")


# Scenario is written before changing voice behavior.
with (root / "scenarios.yaml").open("a", encoding="utf-8") as f:
    f.write("""
  - label: Reports the actual mobile project request status
    instructions: |
      PERSONA: Brazilian user on their S23 FE.
      OPENING LINE: "Jarvis, como está o progresso do request que fiz no Projects?"
      DO, IN ORDER:
      1. Ask whether there is anything waiting for your answer.
      2. Ask if the request is complete and whether tests really ran.
      3. End the conversation.
    agent_expectations: >
      Calls check_coding_agents and uses the returned orchestrator request state,
      last update, messages, job progress and results. Does not invent a percentage,
      test pass or completion. If the server or PC is unavailable, explains the
      limitation and distinguishes saved progress from live execution. Never starts
      another job when asked only for status.
    tags:
      feature: project-request-progress
""")
o = "src/jarvis_control/orchestrator.py"
edit(o, 'self._db.executescript(SCHEMA)', '''self._db.executescript(SCHEMA)
        self._db.execute("""CREATE TABLE IF NOT EXISTS job_progress (
            job_id TEXT PRIMARY KEY, updated_at REAL NOT NULL, body TEXT NOT NULL
        )""")''')
edit(o, '        return conv\n\n    @staticmethod', '''        conv["jobs"] = self._rows(
            """SELECT j.id, j.agent, j.state, j.purpose, j.started_at, j.finished_at,
                      p.updated_at, p.body AS progress
               FROM jobs j LEFT JOIN job_progress p ON p.job_id = j.id
               WHERE j.conversation_id = ? ORDER BY j.created_at DESC LIMIT 30""",
            conversation_id,
        )
        for job in conv["jobs"]:
            job["progress"] = json.loads(job["progress"]) if job["progress"] else None
        return conv

    def progress(self) -> dict[str, Any]:
        """Saved server evidence remains readable when the PC is offline."""
        requests = []
        for item in self.conversations()[:5]:
            conv = self.conversation(item["id"])
            requests.append({
                "id": conv["id"], "title": conv["title"], "state": conv["state"],
                "updated_at": conv["updated_at"],
                "messages": conv["messages"][-4:], "jobs": conv["jobs"][:5],
                "runs": conv["runs"][-1:],
            })
        return {"requests": requests, "observed_at": self._clock(),
                "source": "jarvis_orchestrator_saved_state"}

    @staticmethod''')
edit(o, '''        if state not in self.FINAL:
            return
        self._db.execute(''', '''        if state not in (*self.FINAL, "queued", "preparing", "running"):
            return
        progress = update.get("progress")
        if isinstance(progress, dict):
            # Only allow bounded display fields; never store the entire CLI stream here.
            body = {k: str(progress[k])[:6000] for k in ("stage", "stdout_tail", "stderr_tail") if k in progress}
            self._db.execute(
                "INSERT OR REPLACE INTO job_progress VALUES (?, ?, ?)",
                (job["id"], self._clock(), json.dumps(body, ensure_ascii=False)),
            )
        if state not in self.FINAL:
            self._db.execute("UPDATE jobs SET state = ? WHERE id = ?", (state, job["id"]))
            return
        self._db.execute(''')
# Stream bounded, redacted tails while retaining the existing final result protocol.
j = "src/jarvis_desktop/agent_jobs.py"
edit(j, "from .credentials import local_dir", "from .credentials import local_dir\nfrom .coding import redact")
edit(j, '''    @staticmethod
    def _message(job:''', '''    async def _communicate_progress(self, proc, job):
        tails = {"stdout": bytearray(), "stderr": bytearray()}

        async def consume(stream, key):
            while chunk := await stream.read(4096):
                tails[key].extend(chunk)
                if len(tails[key]) > OUTPUT_LIMIT:
                    del tails[key][:-OUTPUT_LIMIT]

        async def report():
            while True:
                job["progress"] = {
                    "stage": job["state"],
                    **{f"{key}_tail": redact(bytes(value).decode("utf-8", errors="replace")[-6000:])
                       for key, value in tails.items()},
                }
                self._save(job)
                if self.notify is not None:
                    self.notify(self._message(job))
                await asyncio.sleep(3)

        reporter = asyncio.create_task(report())
        try:
            await asyncio.gather(consume(proc.stdout, "stdout"), consume(proc.stderr, "stderr"), proc.wait())
            return bytes(tails["stdout"]), bytes(tails["stderr"])
        finally:
            reporter.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await reporter
            job["progress"] = {
                "stage": job["state"],
                **{f"{key}_tail": redact(bytes(value).decode("utf-8", errors="replace")[-6000:])
                   for key, value in tails.items()},
            }

    @staticmethod
    def _message(job:''')
edit(j, 'proc.communicate(), job["timeout"] + 30', 'self._communicate_progress(proc, job), job["timeout"] + 30')
edit(j, '                    "result",\n', '                    "result",\n                    "progress",\n')
edit(j, '''        if job is not None:
            job["acked"] = True''', '''        if job is not None and job["state"] not in {"queued", "preparing", "running"}:
            job["acked"] = True''')
w = "src/jarvis_control/web.py"
edit(w, '''    store: Store | None = None,
) -> web.Application:''', '''    store: Store | None = None,
    orchestrator: Orchestrator | None = None,
) -> web.Application:''')
edit(w, '''        try:
            params = apply_music_policy(action, params, music_target())''', '''        if action == "orchestrator.progress" and orchestrator is not None:
            return web.json_response({"ok": True, "result": orchestrator.progress()})
        try:
            params = apply_music_policy(action, params, music_target())''')
c = "src/coding_agents.py"
edit(c, '''        try:
            return await self._link.call(
                "coding.activity", {"agent": agent, "hours": hours, "limit": 5}
            )
        except DesktopLinkError as exc:
            raise CodingReportError(str(exc)) from exc''', '''        saved = None
        try:
            saved = await self._link.call("orchestrator.progress", {})
        except DesktopLinkError:
            pass  # Compatible with older control servers.
        try:
            result = await self._link.call(
                "coding.activity", {"agent": agent, "hours": hours, "limit": 5}
            )
        except DesktopLinkError as exc:
            if saved is None:
                raise CodingReportError(str(exc)) from exc
            result = {"available": False, "problem": str(exc)}
        if saved is not None:
            result["orchestrator"] = saved
        return result''')
edit(c, '''        of programming work. Each session lists''', '''        of programming work, mobile Projects requests, or the orchestrator.
        The orchestrator field is authoritative saved request state, messages, jobs,
        logs and results. Check its timestamps; saved state does not prove the PC is
        still executing. Never invent progress percentages or passed tests.
        Each session lists''')
print("Progress and voice backend changes prepared.")
