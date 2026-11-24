"""Documento do relatório (schema_version 1), comparação entre runs e HTML estático.

O HTML é gerado só a partir do JSON validado, com tudo escapado e sem scripts. Logs e textos
de evidência são dados não confiáveis.
"""

from __future__ import annotations

import html
from datetime import datetime
from typing import Any

from . import __version__
from .collectors.base import CheckResult, Finding, local_time

SCHEMA_VERSION = 1
SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2, "info": 3}
COMPARISON_LABEL = {"new": "Nova", "recurring": "Recorrente", "resolved": "Resolvida",
                    "not_rechecked": "Não reverificada"}
STATUS_LABEL = {"collected": "Coletado", "partial": "Parcial", "error": "Erro na coleta", "skipped": "Não executado"}
SEVERITY_LABEL = {"high": "Alta", "medium": "Média", "low": "Baixa", "info": "Informativa"}
STATE_LABEL = {"completed": "Concluído", "partial": "Parcial", "failed": "Falhou", "cancelled": "Cancelado",
               "interrupted": "Interrompido"}


def compare(current: list[tuple[str, Finding]], statuses: dict[str, str], previous: list[Any]) -> list[dict[str, Any]]:
    """Novos/recorrentes vêm do run atual; do anterior, o que sumiu vira resolvido só se o check
    correspondente foi coletado por inteiro agora. Caso contrário, não reverificado."""
    previous_by_fp = {row["fingerprint"]: row for row in previous}
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for check_id, finding in current:
        if finding.fingerprint in seen:
            continue
        seen.add(finding.fingerprint)
        out.append({**finding.to_dict(), "check_id": check_id,
                    "comparison": "recurring" if finding.fingerprint in previous_by_fp else "new"})
    for fingerprint, row in previous_by_fp.items():
        if fingerprint in seen:
            continue
        resolved = statuses.get(row["check_id"]) == "collected"
        out.append({"fingerprint": fingerprint, "check_id": row["check_id"], "rule": row["rule"],
                    "severity": row["severity"], "state": row["state"], "summary": row["summary"],
                    "file": row["file"], "line": row["line"], "evidence": [], "recommendation": "",
                    "origin": "collector", "occurrences": 0,
                    "comparison": "resolved" if resolved else "not_rechecked"})
    out.sort(key=lambda f: (f["comparison"] in ("resolved", "not_rechecked"), SEVERITY_ORDER.get(f["severity"], 9)))
    return out


def summarize(findings: list[dict[str, Any]], checks: list[CheckResult]) -> dict[str, Any]:
    present = [f for f in findings if f["comparison"] in ("new", "recurring")]
    by_severity = {s: sum(1 for f in present if f["severity"] == s) for s in SEVERITY_ORDER}
    statuses = [c.status for c in checks]
    return {
        "findings": len(present), "by_severity": by_severity,
        "new": sum(1 for f in findings if f["comparison"] == "new"),
        "recurring": sum(1 for f in findings if f["comparison"] == "recurring"),
        "resolved": sum(1 for f in findings if f["comparison"] == "resolved"),
        "not_rechecked": sum(1 for f in findings if f["comparison"] == "not_rechecked"),
        "coverage": {s: statuses.count(s) for s in ("collected", "partial", "error", "skipped")},
    }


def run_state(checks: list[CheckResult]) -> str:
    if checks and all(c.status in ("error", "skipped") for c in checks):
        return "failed"
    return "completed" if all(c.status == "collected" for c in checks) else "partial"


def build(run: dict[str, Any], checks: list[CheckResult], findings: list[dict[str, Any]], revision: dict[str, Any],
          previous_run: str | None, state: str, settings_revision: int) -> dict[str, Any]:
    started = run.get("started_at")
    finished = run.get("finished_at")
    duration = None
    if started and finished:
        duration = int((datetime.fromisoformat(finished) - datetime.fromisoformat(started)).total_seconds() * 1000)
    return {
        "schema_version": SCHEMA_VERSION, "kind": "audit", "executed": True,
        "generator": {"name": "dicevtt-diagnostics", "version": __version__},
        "run_id": run["id"], "startup_ids": run.get("startup_ids", []), "project": run["project"],
        "trigger": run["trigger"], "profile": run["profile"], "state": state,
        "created_at": run["created_at"], "started_at": started, "finished_at": finished, "duration_ms": duration,
        "timezone": "America/Sao_Paulo", "settings_revision": settings_revision,
        "revision": revision, "previous_run_id": previous_run,
        "summary": summarize(findings, checks),
        "checks": [c.to_dict() for c in checks],
        "findings": findings,
        "sync": {"state": "local_only", "note": "Sincronização com o servidor/n8n ainda não implementada (entrega 3)."},
        "auto_fix": False,
    }


def render_html(doc: dict[str, Any]) -> str:
    e = html.escape
    summary = doc["summary"]
    rev = doc.get("revision") or {}
    plastic = rev.get("plastic") or {}
    rows_checks = "".join(
        f"<tr><td>{e(c['name'])}</td><td><span class='b {e(c['status'])}'>{e(STATUS_LABEL.get(c['status'], c['status']))}"
        f"</span></td><td>{e(c['note'] or '')}"
        + "".join(f"<div class='muted'>{e(p)}</div>" for p in c.get("problems", []))
        + f"</td><td class='num'>{c.get('duration_ms') or 0} ms</td></tr>" for c in doc["checks"])
    evidence = {ev["id"]: ev for c in doc["checks"] for ev in c.get("evidence", [])}
    blocks = []
    for f in doc["findings"]:
        refs = "".join(
            f"<li><code>{e(evidence[i]['source'])}</code> {e(evidence[i].get('detail') or '')}"
            + (f" · sha256 {e(evidence[i]['sha256'][:16])}" if evidence[i].get("sha256") else "") + "</li>"
            for i in f.get("evidence", []) if i in evidence)
        where = f"{f['file']}" + (f":{f['line']}" if f.get("line") else "") if f.get("file") else ""
        advice = f"<pre>{e(f['recommendation'])}</pre>" if f.get("recommendation") else ""
        blocks.append(
            f"<details class='f'><summary><span class='b sev-{e(f['severity'])}'>{e(SEVERITY_LABEL.get(f['severity'], f['severity']))}"
            f"</span> <span class='b'>{e(COMPARISON_LABEL.get(f['comparison'], f['comparison']))}</span> "
            f"{e(f['summary'])}</summary><div>"
            f"<p><b>Regra:</b> <code>{e(f['rule'])}</code> · <b>Estado:</b> {e(f['state'])}"
            + (f" · <b>Ocorrências:</b> {f['occurrences']}" if f.get("occurrences") else "")
            + (f" · <b>Local:</b> <code>{e(where)}</code>" if where else "")
            + f"</p>{advice}"
            + (f"<ul>{refs}</ul>" if refs else "") + f"<p class='muted'>fingerprint {e(f['fingerprint'])}</p></div></details>")
    sev = summary["by_severity"]
    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Relatório {e(doc['run_id'])} · {e(doc['project'])}</title>
<style>
body{{font:14px/1.55 system-ui,Segoe UI,sans-serif;margin:0;background:#f6f7f5;color:#1d2420}}
main{{max-width:1000px;margin:0 auto;padding:28px 18px}}h1{{font-size:22px;margin:0 0 4px}}h2{{font-size:16px;margin:28px 0 10px}}
.muted{{color:#5f6b63;font-size:12px}}table{{width:100%;border-collapse:collapse;background:#fff}}td,th{{text-align:left;padding:8px;border-bottom:1px solid #e1e5e1;vertical-align:top}}
.num{{text-align:right;white-space:nowrap}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}}
.card{{background:#fff;border:1px solid #e1e5e1;border-radius:8px;padding:12px}}.card b{{display:block;font-size:20px}}
.b{{display:inline-block;font-size:11px;padding:1px 7px;border-radius:9px;background:#e8ece8}}.collected{{background:#dcefe2}}.partial{{background:#f6ecd0}}.error{{background:#f6d9d5}}.skipped{{background:#e6e6e6}}
.sev-high{{background:#f3cfca}}.sev-medium{{background:#f6e3bf}}.sev-low{{background:#dde8f4}}.sev-info{{background:#e6e6e6}}
details.f{{background:#fff;border:1px solid #e1e5e1;border-radius:8px;margin:8px 0;padding:8px 12px}}summary{{cursor:pointer}}
pre{{white-space:pre-wrap;word-break:break-word;background:#f0f2f0;padding:8px;border-radius:6px;font-size:12px}}code{{font-size:12px;word-break:break-all}}
</style></head><body><main>
<p class="muted">DiceVTT · relatório automático · {e(doc['profile'])} · disparo {e(doc['trigger'])}</p>
<h1>{e(doc['project'])} — {e(STATE_LABEL.get(doc['state'], doc['state']))}</h1>
<p class="muted">Run {e(doc['run_id'])} · início {e(local_time(doc['started_at']))} · fim {e(local_time(doc['finished_at']))} (America/Sao_Paulo) · {doc.get('duration_ms') or 0} ms</p>
<div class="grid">
<div class="card"><span class="muted">Ocorrências atuais</span><b>{summary['findings']}</b><span class="muted">alta {sev['high']} · média {sev['medium']} · baixa {sev['low']} · info {sev['info']}</span></div>
<div class="card"><span class="muted">Comparação</span><b>{summary['new']} novas</b><span class="muted">{summary['recurring']} recorrentes · {summary['resolved']} resolvidas · {summary['not_rechecked']} não reverificadas</span></div>
<div class="card"><span class="muted">Cobertura</span><b>{summary['coverage']['collected']}/{len(doc['checks'])}</b><span class="muted">parciais {summary['coverage']['partial']} · erros {summary['coverage']['error']} · não executados {summary['coverage']['skipped']}</span></div>
<div class="card"><span class="muted">Revisão analisada</span><b>{e(rev.get('source_state') or '—')}</b><span class="muted">{e(str(rev.get('vcs') or 'sem VCS'))} · {e(str(plastic.get('branch') or rev.get('branch') or '—'))} · cs {e(str(plastic.get('changeset') or '—'))}</span></div>
</div>
<h2>Verificações</h2><table><tr><th>Check</th><th>Coleta</th><th>Resultado</th><th class="num">Tempo</th></tr>{rows_checks}</table>
<h2>Ocorrências</h2>{''.join(blocks) or '<p>Nenhuma ocorrência nos checks coletados.</p>'}
<p class="muted">Checks parciais ou não executados não contam como aprovação. Sincronização: {e(doc['sync']['note'])}</p>
</main></body></html>"""
