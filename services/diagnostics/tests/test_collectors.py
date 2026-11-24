from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import replace

from dicevtt_diagnostics.collectors import logs, services, unity, vcs
from dicevtt_diagnostics.collectors.base import CheckResult, Context


def ctx_for(config, tmp_path):
    return Context(config, threading.Event(), time.monotonic() + 30, tmp_path)


def test_only_last_compilation_counts_and_secrets_are_redacted(config, tmp_path):
    ctx = ctx_for(config, tmp_path)
    check = CheckResult("logs", "Logs")
    logs.collect(ctx, check)
    rules = {f.rule: f for f in check.findings}
    errors = [f for f in check.findings if f.rule == "unity.compile-error"]
    assert [f.file for f in errors] == ["Assets/Scripts/A.cs"]  # Velho.cs ficou na compilação anterior
    assert errors[0].state == "confirmed" and errors[0].severity == "high"
    warning = rules["unity.compile-warning"]
    assert warning.occurrences == 2 and warning.key == "CS0618"
    exception = rules["unity.editor-exception"]
    assert exception.occurrences == 2 and exception.file == "Assets/Scripts/Lobby.cs"
    assert check.data["editor_log"]["last_compile"] == {"result": "failed", "errors": 1, "warnings": 2}
    assert "abc123secret" not in repr([f.to_dict() for f in check.findings])


def test_log_identity_ignores_line_numbers():
    first = logs._exceptions("NullReferenceException: x\nA.B () (at Assets/A.cs:10)\n")
    second = logs._exceptions("NullReferenceException: x\nA.B () (at Assets/A.cs:99)\n")
    assert first.keys() == second.keys()


def test_log_from_other_project_is_partial_without_findings(config, tmp_path):
    other = config.editor_log.read_text(encoding="utf-8").replace(str(config.project_root), r"C:\Outro\Projeto")
    config.editor_log.write_text(other, encoding="utf-8")
    future = time.time() + 60
    os.utime(config.editor_log, (future, future))
    check = CheckResult("logs", "Logs")
    logs.collect(ctx_for(config, tmp_path), check)
    assert check.status == "partial"
    assert check.findings == []


def test_stale_log_findings_are_only_suspected(config, tmp_path):
    past = time.time() - 3600
    os.utime(config.editor_log, (past, past))
    ctx = ctx_for(config, tmp_path)
    unity.scan_assets(ctx, CheckResult("unity", "Unity"))  # define o script mais recente
    check = CheckResult("logs", "Logs")
    logs.collect(ctx, check)
    assert check.status == "partial"
    assert {f.state for f in check.findings} == {"suspected"}


def test_unity_inventory_and_rag_coverage(config, tmp_path):
    check = CheckResult("unity", "Unity")
    unity.collect(ctx_for(config, tmp_path), check)
    rules = {f.rule: f for f in check.findings}
    assert check.data["editor_version"] == "6000.3.10f1" and check.data["editor_path"]
    assert check.data["scripts"] == 2  # Ignorado~ não conta: a Unity ignora pastas com ~
    assert rules["rag.scripts-outside-index"].occurrences == 1
    assert "tests.no-test-assembly" in rules
    assert "packages.git-unpinned" not in rules  # o lock tem hash


def test_missing_editor_is_high(config, tmp_path):
    cfg = replace(config, unity_editors=tmp_path / "vazio")
    (tmp_path / "vazio").mkdir()
    check = CheckResult("unity", "Unity")
    unity.collect(ctx_for(cfg, tmp_path), check)
    assert any(f.rule == "unity.editor-missing" and f.severity == "high" for f in check.findings)


def test_git_unavailable_is_a_collection_error_not_a_finding(config, tmp_path):
    check = CheckResult("vcs", "VCS")
    vcs.collect(ctx_for(config, tmp_path), check)  # o executável configurado não existe
    assert check.status == "error"
    assert not any(f.rule == "vcs.unversioned" for f in check.findings)


def test_project_outside_any_repository_is_reported(config, tmp_path):
    check = CheckResult("vcs", "VCS")
    vcs.collect(ctx_for(replace(config, git="git"), tmp_path), check)
    assert check.status == "collected" and check.data["vcs"] is None
    assert any(f.rule == "vcs.unversioned" for f in check.findings)


def test_plastic_without_cm_is_partial(config, tmp_path):
    meta = config.project_root / ".plastic"
    meta.mkdir()
    (meta / "plastic.selector").write_text('rep "Repo@cloud"\n  path "/"\n    smartbranch "/main/X" changeset "7"\n',
                                          encoding="utf-8")
    check = CheckResult("vcs", "VCS")
    vcs.collect(ctx_for(replace(config, git="git"), tmp_path), check)
    assert check.status == "partial"
    assert check.data["plastic"]["branch"] == "/main/X"
    assert not any(f.rule == "vcs.unversioned" for f in check.findings)


def test_mcp_collector_checks_claude_codex_and_antigravity(tmp_path):
    (tmp_path / ".claude.json").write_text(json.dumps({"mcpServers": {"dicevtt-rag": {}}}), encoding="utf-8")
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".codex" / "config.toml").write_text('[mcp_servers.dicevtt-rag]\ncommand = "python"\n', encoding="utf-8")
    agy_cfg = tmp_path / ".gemini" / "config" / "mcp_config.json"
    agy_cfg.parent.mkdir(parents=True)
    agy_cfg.write_text(json.dumps({"mcpServers": {"dicevtt-rag": {"command": "python"}}}), encoding="utf-8")

    ok_check = CheckResult("services", "Services")
    services.collect_mcp(ok_check, home=tmp_path)
    assert ok_check.data["mcp"] == {"claude_code": True, "codex": True, "antigravity": True}
    assert ok_check.findings == []

    agy_cfg.write_text(json.dumps({"mcpServers": {"dicevtt-rag": {"command": "python", "disabled": True}}}), encoding="utf-8")
    disabled_check = CheckResult("services", "Services")
    services.collect_mcp(disabled_check, home=tmp_path)
    assert disabled_check.data["mcp"]["antigravity"] is False
    assert [f.key for f in disabled_check.findings] == ["antigravity"]
