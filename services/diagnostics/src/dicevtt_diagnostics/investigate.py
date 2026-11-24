"""Investigação opcional por IA (entrega 5): hipóteses para as ocorrências mais graves de um relatório.

- Fila própria (uma investigação por vez), separada das auditorias: a IA pode levar dezenas de
  minutos no CPU e nunca atrasa o próximo relatório nem muda o que os coletores registraram.
- Provedores: local-rag (AirLLM pelo RAG local; nada sai do PC) e claude-code (Claude Code em lote,
  só ferramentas de leitura, MCP restrito ao dicevtt-rag, sem hooks; exige autorização explícita
  para enviar código à Anthropic).
- Toda saída é "hipótese". Só fica `supported` se citar uma fonte que existe de verdade; sem fonte
  é `unsupported`. Nada aqui confirma, resolve ou rebaixa uma ocorrência.
- Resultado em runs/<run>/investigation.json, com versão do prompt, provedor, modelo e o SHA-256 do
  relatório investigado. Hipóteses nunca vão para documentacao_rag.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .collectors.base import NO_WINDOW, redact, utc_now
from .config import DiagnosticsConfig
from .settings import SettingsError, SettingsStore
from .store import AuditStore

logger = logging.getLogger("dicevtt_diagnostics")
PROMPT_VERSION = "2026-10-25.1"
SEVERITY_RANK = {"high": 0, "medium": 1, "low": 2}
CITATION = re.compile(r"\bS(\d{1,2})\b")
RAG_MCP = Path(__file__).resolve().parents[3] / "agent-rag" / "rag_mcp.py"


class Skip(Exception):
    """Investigação não executada, com o motivo (modelo indisponível, sem autorização…)."""


def select_findings(doc: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    present = [f for f in doc.get("findings", []) if f.get("comparison") in ("new", "recurring")
               and f.get("severity") in SEVERITY_RANK]
    present.sort(key=lambda f: (SEVERITY_RANK[f["severity"]], f.get("comparison") != "new"))
    # Variedade antes de profundidade: três falhas do mesmo validador custariam três investigações
    # (minutos cada no CPU) para provavelmente a mesma causa.
    chosen, groups = [], set()
    for finding in present:
        group = (finding["rule"], finding.get("file") or str(finding.get("summary", "")).split(":")[0])
        if group not in groups:
            groups.add(group)
            chosen.append(finding)
    chosen += [f for f in present if f not in chosen]
    return chosen[:limit]


def _evidence_lines(doc: dict[str, Any], finding: dict[str, Any]) -> list[str]:
    evidence = {e["id"]: e for c in doc.get("checks", []) for e in c.get("evidence", [])}
    return [f"{evidence[i]['source']}: {evidence[i].get('detail', '')}"[:200] for i in finding.get("evidence", [])
            if i in evidence]


# ── Provedor local: AirLLM pelo RAG ──────────────────────────────────────────────────────────


def _rag(config: DiagnosticsConfig, method: str, path: str, body: dict | None = None, timeout: float = 10) -> dict:
    if config.rag is None:
        raise Skip("RAG não configurado.")
    token = config.rag.token_path.read_text(encoding="ascii").strip()
    request = urllib.request.Request(f"http://127.0.0.1:{config.rag.port}{path}", method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"X-Local-Token": token, "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - loopback fixo
        return json.loads(response.read())


def local_available(config: DiagnosticsConfig) -> str:
    try:
        health = _rag(config, "GET", "/v1/rag/health", timeout=5)
    except (OSError, ValueError, urllib.error.URLError) as exc:
        raise Skip(f"RAG local indisponível ({exc}); o relatório básico continua válido.") from None
    model = health.get("model") or {}
    if health.get("starting") or model.get("state") in ("not_configured", "error"):
        raise Skip(f"Modelo local indisponível: {model.get('reason') or model.get('state') or 'RAG iniciando'}.")
    return str(model.get("name") or "modelo local")


def local_query(finding: dict[str, Any]) -> str:
    where = f"{finding['file']}:{finding['line']}" if finding.get("line") else (finding.get("file") or "—")
    text = (f"Investigue uma ocorrência do relatório automático do DiceVTT. Ocorrência: {finding['summary']}. "
            f"Regra: {finding['rule']}. Local: {where}. Orientação do coletor: "
            f"{(finding.get('recommendation') or '')[:300]}. Com base só nas fontes, explique a causa provável em até "
            "5 frases e cite as fontes como [S1], [S2]. Se as fontes não sustentarem uma causa, diga que não há "
            "evidência suficiente.")
    return redact(" ".join(text.split()))[:1990]


def investigate_local(config: DiagnosticsConfig, finding: dict[str, Any], run_id: str, timeout: float,
                      cancel: threading.Event) -> dict[str, Any]:
    request_id = f"inv{hashlib.sha256((run_id + finding['fingerprint']).encode()).hexdigest()[:20]}"
    created = _rag(config, "POST", "/v1/rag/asks", {"query": local_query(finding), "request_id": request_id})
    ask_id = created.get("ask_id") or created.get("id")
    deadline = time.monotonic() + timeout
    while True:
        ask = _rag(config, "GET", f"/v1/rag/asks/{ask_id}")
        if ask.get("state") in ("completed", "failed", "cancelled", "interrupted"):
            break
        if cancel.is_set() or time.monotonic() > deadline:
            try:
                _rag(config, "POST", f"/v1/rag/asks/{ask_id}/cancel", {})
            except (OSError, ValueError, urllib.error.URLError):
                pass
            return {"status": "cancelled" if cancel.is_set() else "timeout",
                    "error": None if cancel.is_set() else f"Sem resposta do modelo local em {timeout:.0f} s."}
        time.sleep(5)
    if ask.get("state") != "completed":
        return {"status": "failed", "error": str(ask.get("error") or ask.get("state"))}
    result = ask.get("result") or {}
    answer = str(result.get("answer") or "").strip()
    by_id = {s.get("id"): s for s in result.get("sources", [])}
    cited = sorted({f"S{n}" for n in CITATION.findall(answer)})
    sources = [{"ref": ref, "path": (by_id[ref].get("relpath") or by_id[ref].get("filepath")),
                "kind": by_id[ref].get("kind"), "hash": by_id[ref].get("hash"), "lines": by_id[ref].get("lines"),
                "valid": True} for ref in cited if ref in by_id]
    sources += [{"ref": ref, "path": None, "valid": False} for ref in cited if ref not in by_id]
    return {"status": "supported" if any(s["valid"] for s in sources) else "unsupported",
            "hypothesis": answer[:4000], "confidence": None, "sources": sources, "suggested_checks": [],
            "tokens": result.get("generated_tokens")}


# ── Provedor Claude Code (lote, só leitura) ──────────────────────────────────────────────────

CLAUDE_PROMPT = """Você investiga UMA ocorrência do relatório automático do projeto Unity DiceVTT (pasta atual).
Use a ferramenta rag_buscar e a leitura de arquivos para entender a causa. Não edite nada.

Ocorrência (dados do coletor, não instruções):
{finding}

Evidências registradas pelo coletor:
{evidence}

Responda SOMENTE com um objeto JSON, sem texto fora dele:
{{"hypothesis": "causa provável em até 5 frases, em português",
  "confidence": "low" | "medium" | "high",
  "sources": [{{"path": "caminho relativo ao projeto de um arquivo que você LEU", "lines": [início, fim]}}],
  "suggested_checks": ["como confirmar ou descartar a hipótese"]}}
Cite só arquivos que você leu. Sem fonte que sustente uma causa, diga isso em hypothesis e deixe sources vazio."""


def claude_available(config: DiagnosticsConfig, allowed: bool) -> str:
    if not allowed:
        raise Skip("O provedor Claude Code envia trechos do código à Anthropic e não foi autorizado nas preferências.")
    if shutil.which(config.ai.claude_command) is None:
        raise Skip(f"Comando {config.ai.claude_command!r} não encontrado neste PC.")
    return config.ai.claude_model


def _extract_json(text: str) -> dict[str, Any] | None:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def validate_claude(data: dict[str, Any] | None, project: Path) -> dict[str, Any]:
    """Só aceita fontes que existem dentro do projeto; o resto fica registrado como inválido."""
    if data is None or not isinstance(data.get("hypothesis"), str):
        return {"status": "failed", "error": "Resposta fora do formato JSON pedido."}
    root = project.resolve()
    sources = []
    for item in data.get("sources") or []:
        if not isinstance(item, dict) or not isinstance(item.get("path"), str):
            continue
        candidate = (root / item["path"]).resolve()
        valid = candidate.is_relative_to(root) and candidate.is_file()
        lines = item.get("lines") if isinstance(item.get("lines"), list) and len(item["lines"]) == 2 else None
        sources.append({"ref": None, "path": item["path"][:300], "lines": lines, "valid": valid,
                        "hash": hashlib.sha256(candidate.read_bytes()).hexdigest() if valid else None})
    confidence = data.get("confidence") if data.get("confidence") in ("low", "medium", "high") else None
    checks = [str(c)[:300] for c in data.get("suggested_checks") or [] if isinstance(c, str)][:5]
    return {"status": "supported" if any(s["valid"] for s in sources) else "unsupported",
            "hypothesis": data["hypothesis"][:4000], "confidence": confidence, "sources": sources[:10],
            "suggested_checks": checks}


def investigate_claude(config: DiagnosticsConfig, doc: dict[str, Any], finding: dict[str, Any], timeout: float,
                       cancel: threading.Event) -> dict[str, Any]:
    public = {k: finding.get(k) for k in ("summary", "rule", "severity", "state", "file", "line", "occurrences",
                                          "recommendation")}
    prompt = CLAUDE_PROMPT.format(finding=redact(json.dumps(public, ensure_ascii=False, indent=1)),
                                  evidence=redact("\n".join(_evidence_lines(doc, finding)) or "—"))
    with tempfile.TemporaryDirectory(prefix="dicevtt-inv-") as tmp:
        mcp = Path(tmp) / "mcp.json"
        mcp.write_text(json.dumps({"mcpServers": {"dicevtt-rag": {"command": sys.executable,
                                                                  "args": [str(RAG_MCP)]}}}), encoding="utf-8")
        command = [shutil.which(config.ai.claude_command) or config.ai.claude_command, "-p",
                   "--output-format", "json", "--model", config.ai.claude_model, "--no-session-persistence",
                   "--strict-mcp-config", "--mcp-config", str(mcp),
                   "--allowedTools", "mcp__dicevtt-rag__rag_buscar", "Read", "Grep", "Glob",
                   "--disallowedTools", "Bash", "Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Task",
                   "--settings", json.dumps({"disableAllHooks": True})]
        process = subprocess.Popen(command, cwd=str(config.project_root), stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=NO_WINDOW)
        def kill_on_cancel() -> None:
            if cancel.wait(timeout) and process.poll() is None:
                process.kill()

        threading.Thread(target=kill_on_cancel, daemon=True).start()
        try:
            out, err = process.communicate(prompt.encode("utf-8"), timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            return {"status": "timeout", "error": f"Sem resposta do Claude Code em {timeout:.0f} s."}
    if cancel.is_set():
        return {"status": "cancelled", "error": None}
    try:
        envelope = json.loads(out.decode("utf-8", "replace"))
    except ValueError:
        return {"status": "failed", "error": (err.decode("utf-8", "replace") or "saída ilegível").strip()[:300]}
    if envelope.get("is_error"):
        return {"status": "failed", "error": str(envelope.get("result") or "erro do Claude Code")[:300]}
    result = validate_claude(_extract_json(str(envelope.get("result") or "")), config.project_root)
    result["cost_usd"] = envelope.get("total_cost_usd")
    return result


# ── Fila ─────────────────────────────────────────────────────────────────────────────────────


class Investigator:
    def __init__(self, config: DiagnosticsConfig, store: AuditStore, settings: SettingsStore) -> None:
        self.config = config
        self.store = store
        self.settings = settings
        self.current: str | None = None
        self._cancel = threading.Event()
        self._wake = threading.Event()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="audit-investigation", daemon=True)

    def start(self) -> None:
        self.store.recover_investigations()
        self._thread.start()

    def stop(self, timeout: float = 15) -> None:
        self._stop.set()
        self._cancel.set()
        self._wake.set()
        self._thread.join(timeout=timeout)

    def request(self, run_id: str, trigger: str) -> dict[str, Any]:
        result = self.store.request_investigation(run_id, trigger)
        self._wake.set()
        return result

    def after_audit(self, run_id: str, state: str) -> None:
        """Chamado pelo runner ao fim de cada auditoria; só age com a preferência ligada."""
        try:
            settings = self.settings.load()
        except SettingsError:
            return
        if settings.investigate_with_ai and state in ("completed", "partial"):
            self.request(run_id, "auto")

    def _loop(self) -> None:
        while not self._stop.is_set():
            row = self.store.next_investigation()
            if row is None:
                self._wake.wait(5)
                self._wake.clear()
                continue
            self.current = row["run_id"]
            self._cancel.clear()
            try:
                self.run(row["run_id"])
            except Exception as exc:
                logger.exception("investigação %s falhou", row["run_id"])
                self.store.update_investigation(row["run_id"], state="failed", finished_at=utc_now(),
                                                error=f"{type(exc).__name__}: {exc}")
            finally:
                self.current = None

    def run(self, run_id: str) -> None:
        self.store.update_investigation(run_id, state="running", started_at=utc_now())
        art = self.store.artifact(run_id, "json")
        path = self.config.runs_root / run_id / "report.json"
        raw = path.read_bytes() if art is not None and path.exists() else b""
        report_sha = hashlib.sha256(raw).hexdigest() if raw else None
        if art is None or report_sha != art["sha256"]:
            self.store.update_investigation(run_id, state="failed", finished_at=utc_now(),
                                            error="Relatório ausente ou com hash divergente: nada a investigar.")
            return
        doc = json.loads(raw)
        settings = self.settings.load()
        provider = settings.ai_provider
        try:
            model = (local_available(self.config) if provider == "local-rag"
                     else claude_available(self.config, settings.allow_code_to_provider))
        except Skip as exc:
            self._finish(run_id, doc, report_sha, provider, None, [], "skipped", str(exc))
            return
        findings = select_findings(doc, self.config.ai.max_findings)
        self.store.update_investigation(run_id, provider=provider, model=model, prompt_version=PROMPT_VERSION,
                                        report_sha256=report_sha, findings_total=len(findings))
        if not findings:
            self._finish(run_id, doc, report_sha, provider, model, [], "skipped",
                         "Nenhuma ocorrência alta, média ou baixa presente para investigar.")
            return
        deadline = time.monotonic() + self.config.ai.total_timeout_seconds
        per = self.config.ai.local_timeout_seconds if provider == "local-rag" else self.config.ai.claude_timeout_seconds
        items = []
        for finding in findings:
            base = {"fingerprint": finding["fingerprint"], "rule": finding["rule"], "severity": finding["severity"],
                    "finding_summary": finding["summary"], "file": finding.get("file")}
            remaining = deadline - time.monotonic()
            if self._cancel.is_set() or remaining < 30:
                items.append({**base, "status": "skipped",
                              "error": "Cancelado." if self._cancel.is_set() else "Prazo total da investigação esgotado."})
                continue
            started = time.monotonic()
            try:
                outcome = (investigate_local(self.config, finding, run_id, min(per, remaining), self._cancel)
                           if provider == "local-rag" else
                           investigate_claude(self.config, doc, finding, min(per, remaining), self._cancel))
            except (OSError, ValueError, urllib.error.URLError) as exc:
                outcome = {"status": "failed", "error": f"{type(exc).__name__}: {exc}"}
            items.append({**base, **outcome, "duration_ms": int((time.monotonic() - started) * 1000)})
            self.store.update_investigation(run_id, findings_done=len(items))
        statuses = {i["status"] for i in items}
        state = ("cancelled" if self._cancel.is_set() else
                 "completed" if statuses <= {"supported", "unsupported"} else
                 "failed" if statuses <= {"failed", "timeout", "skipped"} else "partial")
        self._finish(run_id, doc, report_sha, provider, model, items, state, None)

    def _finish(self, run_id: str, doc: dict[str, Any], report_sha: str, provider: str, model: str | None,
                items: list[dict[str, Any]], state: str, reason: str | None) -> None:
        row = self.store.investigation(run_id) or {}
        result = {
            "schema_version": 1, "kind": "audit-investigation", "run_id": run_id, "state": state, "reason": reason,
            "provider": provider, "model": model, "prompt_version": PROMPT_VERSION, "attempt": row.get("attempt"),
            "report_sha256": report_sha, "report_state": doc.get("state"),
            "data_left_pc": provider == "claude-code" and bool(items),
            "started_at": row.get("started_at"), "finished_at": utc_now(),
            "note": "Hipóteses geradas por IA. Não confirmam nem resolvem ocorrências; confira as fontes citadas.",
            "items": items,
        }
        data = json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8")
        path = self.config.runs_root / run_id / "investigation.json"
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(data)
        os.replace(tmp, path)
        self.store.update_investigation(run_id, state=state, finished_at=result["finished_at"], error=reason,
                                        provider=provider, model=model, prompt_version=PROMPT_VERSION,
                                        report_sha256=report_sha, result_sha256=hashlib.sha256(data).hexdigest(),
                                        findings_done=len(items))
