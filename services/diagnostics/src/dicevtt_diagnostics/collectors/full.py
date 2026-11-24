"""Perfil completo (entrega 4): cópia isolada + Unity em lote. A origem só é lida.

- Snapshot: Assets/Packages/ProjectSettings copiados com SHA-256 (links e junctions não são
  seguidos) para audit_root/snapshots/<run>/<projeto>. Identidade = hash da árvore + revisão do VCS.
- Dados isolados: na cópia, productName ganha um sufixo, então o persistentDataPath do editor de
  auditoria é outra pasta. Os sistemas do jogo são provisionados lá como cópia; os do usuário não
  são tocados. Sem esse isolamento, os validadores não rodam.
- Library: um cache próprio (audit_root/cache/Library) que entra e sai da cópia a cada run. Sem
  cache, só é semeado a partir da origem se nenhum editor estiver com ela aberta.
- Unity: um processo por etapa, num job object próprio (unity_process), com timeout.
- Ao final, a árvore da origem é recalculada: o hash precisa ser o mesmo do início.
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .. import unity_process
from .assets import collect_refs
from .base import CheckResult, Context, Finding, redact, sha256_bytes
from .logs import compile_findings

# Só mensagens fatais. "[Licensing::Module] LicensingClient has failed validation; ignoring" aparece em
# execuções que licenciam e terminam com sucesso: não é falta de licença.
LICENSE = re.compile(r"(?i)(no valid unity (editor )?license|license (is )?not (active|valid)|"
                     r"failed to (activate|acquire)[^\n]*license|unable to (acquire|find)[^\n]*license)")
METHOD_MISSING = re.compile(r"(?i)executeMethod[^\n]*(could not be found|does not exist|not found)")
FAILURE_LINE = re.compile(r"^\s*(?:FALHA|FALHOU|FAIL)\b[:\s-]*(.+)$", re.M)
RESULT_LINE = re.compile(r"^\s*RESULTADO\b[:\s]*(.+)$", re.M)
LOG_TAIL = 8 * 1024 * 1024
MIN_STEP_SECONDS = 120


@dataclass
class Session:
    root: Path  # audit_root/snapshots/<run>
    project: Path
    out: Path  # logs e relatórios (caminho ASCII para a Unity)
    cache: Path
    persistent: Path | None = None
    library_source: str = "cold"
    isolated_data: bool = False
    compiled: bool = False
    manifest: dict[str, str] = field(default_factory=dict)


def unity_command(ctx: Context) -> list[str] | None:
    """Prefixo do comando da Unity. Isolado numa função para os testes trocarem por um falso."""
    editor = ctx.shared.get("editor_path")
    return [editor] if editor else None


def _session(ctx: Context) -> Session | None:
    return ctx.shared.get("full_session")


def source_editor_open(project: Path) -> bool:
    """A Unity segura Temp/UnityLockfile enquanto o projeto está aberto; abrir para leitura falha."""
    lock = project / "Temp" / "UnityLockfile"
    if not lock.exists():
        return False
    try:
        fd = os.open(lock, os.O_RDONLY)
    except PermissionError:
        return True
    except OSError:
        return False
    os.close(fd)
    return False


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def hash_tree(root: Path, dirs: tuple[str, ...], ctx: Context,
              copy_to: Path | None = None) -> tuple[dict[str, str], list[str]]:
    """{caminho relativo: sha256} das pastas; com copy_to, copia enquanto lê (uma leitura só)."""
    manifest: dict[str, str] = {}
    skipped: list[str] = []
    for top in dirs:
        base = root / top
        if not base.is_dir():
            continue
        for current, subdirs, files in os.walk(base):
            ctx.check_cancel()
            here = Path(current)
            for name in list(subdirs):
                if _is_link(here / name):
                    skipped.append((here / name).relative_to(root).as_posix())
                    subdirs.remove(name)
            for name in files:
                source = here / name
                rel = source.relative_to(root).as_posix()
                if _is_link(source):
                    skipped.append(rel)
                    continue
                digest = hashlib.sha256()
                target = None
                if copy_to is not None:
                    destination = copy_to / rel
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    target = destination.open("wb")
                try:
                    with source.open("rb") as handle:
                        while chunk := handle.read(1024 * 1024):
                            digest.update(chunk)
                            if target is not None:
                                target.write(chunk)
                finally:
                    if target is not None:
                        target.close()
                manifest[rel] = digest.hexdigest()
    return manifest, skipped


def tree_digest(manifest: dict[str, str]) -> str:
    return hashlib.sha256("".join(f"{k}\0{v}\n" for k, v in sorted(manifest.items())).encode()).hexdigest()


def _settings_value(text: str, key: str) -> str | None:
    match = re.search(rf"^\s*{key}:\s*(.+?)\s*$", text, re.M)
    return match.group(1) if match else None


def _local_low() -> Path:
    return Path(os.environ.get("USERPROFILE", str(Path.home()))) / "AppData" / "LocalLow"


def _rmtree(path: Path, inside: Path) -> None:
    """Apaga só dentro de `inside` (a raiz da auditoria ou a pasta de dados isolada)."""
    if path.exists() and path.resolve().is_relative_to(inside.resolve()) and path.resolve() != inside.resolve():
        shutil.rmtree(path, ignore_errors=False)


def _copy_dir(source: Path, target: Path, ctx: Context) -> int:
    count = 0
    for current, subdirs, files in os.walk(source):
        ctx.check_cancel()
        here = Path(current)
        subdirs[:] = [d for d in subdirs if not _is_link(here / d)]
        for name in files:
            if _is_link(here / name):
                continue
            destination = target / (here / name).relative_to(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(here / name, destination)
            count += 1
    return count


def _read_log(path: Path) -> tuple[str, str | None]:
    try:
        data = path.read_bytes()[-LOG_TAIL:]
    except OSError:
        return "", None
    return data.decode("utf-8", "replace"), sha256_bytes(data)


def _run(ctx: Context, check: CheckResult, args: list[str], log: Path, timeout: float) -> unity_process.UnityRun | None:
    prefix = unity_command(ctx)
    if prefix is None:
        check.degrade("error", "Editor da Unity não localizado (veja o check Unity, pacotes e scripts).")
        return None
    session = _session(ctx)
    return unity_process.run_unity(prefix + args, log, timeout, ctx.cancel, session.root if session else ctx.run_dir)


def _environment_problem(check: CheckResult, text: str, run: unity_process.UnityRun) -> bool:
    """Licença indisponível ou timeout são problemas do ambiente: erro de coleta, não achado."""
    license_line = LICENSE.search(text) if run.code != 0 else None  # saiu com 0: licenciou
    if license_line:
        check.degrade("error", f"Licença da Unity indisponível em lote: {redact(license_line.group(0))[:160]}")
        return True
    if run.timed_out:
        check.degrade("error", f"A Unity excedeu o tempo ({run.duration_ms // 1000} s) e foi encerrada (só ela).")
        return True
    return False


# ── Checks ──────────────────────────────────────────────────────────────────────────────────


def prepare_snapshot(ctx: Context, check: CheckResult) -> None:
    full = ctx.config.full
    origin = ctx.config.project_root
    run_id = ctx.run_dir.name
    snapshots = full.audit_root / "snapshots"
    session = Session(root=snapshots / run_id, project=snapshots / run_id / ctx.config.project_name,
                      out=snapshots / run_id / "out", cache=full.audit_root / "cache" / "Library")
    if session.project.resolve().is_relative_to(origin.resolve()) or origin.resolve().is_relative_to(full.audit_root.resolve()):
        check.degrade("error", "A pasta da auditoria e a origem se sobrepõem; nada foi copiado.")
        return
    session.cache.parent.mkdir(parents=True, exist_ok=True)
    # Restos de um run interrompido: a Library volta para o cache, o resto é apagado.
    if snapshots.is_dir():
        for old in snapshots.iterdir():
            if old.name == run_id:
                continue
            leftover = old / ctx.config.project_name / "Library"
            if leftover.is_dir() and not session.cache.exists():
                os.replace(leftover, session.cache)
            _rmtree(old, full.audit_root)
    session.out.mkdir(parents=True, exist_ok=True)
    ctx.shared["full_session"] = session
    ctx.cleanups.append(lambda: _teardown(ctx, session))

    editor_open = source_editor_open(origin)
    session.manifest, skipped = hash_tree(origin, full.copy_dirs, ctx, copy_to=session.project)
    digest = tree_digest(session.manifest)
    ctx.shared["origin_manifest"] = session.manifest
    vcs = ctx.shared.get("vcs") or {}
    plastic = vcs.get("plastic") or {}
    check.data.update(snapshot=session.project.as_posix(), files=len(session.manifest), tree_sha256=digest,
                      skipped_links=skipped[:50], editor_open_on_source=editor_open,
                      source={"vcs": vcs.get("vcs"), "changeset": plastic.get("changeset"),
                              "pending": plastic.get("pending"), "state": "working_tree"})
    check.add_evidence("file", origin.as_posix(), f"{len(session.manifest)} arquivos copiados de "
                                  f"{', '.join(full.copy_dirs)}", sha256=digest)
    if skipped:
        check.problems.append(f"{len(skipped)} link(s)/junction(s) não seguidos na cópia.")
    if editor_open:
        check.problems.append("A Unity estava com a origem aberta: arquivos em gravação podem ter sido copiados "
                              "no meio; a Library da origem não foi usada.")

    # Dados isolados: productName com sufixo → persistentDataPath próprio da auditoria.
    settings_path = session.project / "ProjectSettings" / "ProjectSettings.asset"
    text = settings_path.read_text(encoding="utf-8", errors="replace") if settings_path.exists() else ""
    company, product = _settings_value(text, "companyName"), _settings_value(text, "productName")
    if company and product:
        audit_product = product + full.product_suffix
        settings_path.write_text(re.sub(r"^(\s*productName:\s*).+$", lambda m: m.group(1) + audit_product, text,
                                        count=1, flags=re.M), encoding="utf-8")
        local_low = _local_low()
        real = local_low / company / product
        session.persistent = local_low / company / audit_product
        if session.persistent == real:
            check.degrade("error", "O sufixo do productName está vazio: os dados do usuário não ficariam isolados.")
        else:
            _rmtree(session.persistent, local_low / company)
            session.persistent.mkdir(parents=True, exist_ok=True)
            provisioned = {}
            for name in full.provision:
                if (real / name).is_dir():
                    provisioned[name] = _copy_dir(real / name, session.persistent / name, ctx)
            session.isolated_data = True
            check.data.update(persistent_data=session.persistent.as_posix(), provisioned=provisioned,
                              product_patch=f"{product} -> {audit_product}")
    else:
        check.degrade("partial", "companyName/productName não encontrados: dados do jogo não isolados, "
                                 "os validadores não vão rodar.")

    # Library: cache próprio; semeado da origem só com o editor fechado.
    library = session.project / "Library"
    if session.cache.is_dir():
        os.replace(session.cache, library)
        session.library_source = "cache"
    elif not editor_open and (origin / "Library").is_dir():
        _copy_dir(origin / "Library", library, ctx)
        session.library_source = "seeded_from_origin"
    else:
        session.library_source = "cold"
        check.problems.append("Sem cache de Library: a primeira importação será completa e demorada.")
    check.data["library_source"] = session.library_source
    check.note = (f"Snapshot {digest[:12]} · {len(session.manifest)} arquivos · Library: "
                  f"{ {'cache': 'cache da auditoria', 'seeded_from_origin': 'copiada da origem', 'cold': 'importação completa'}[session.library_source]}"
                  + (" · dados isolados" if session.isolated_data else ""))


def _teardown(ctx: Context, session: Session) -> None:
    """Salva logs/relatórios no run, devolve a Library ao cache e apaga cópia e dados isolados."""
    errors: list[str] = []
    target = ctx.run_dir / "full"
    try:
        if session.out.is_dir():
            shutil.copytree(session.out, target, dirs_exist_ok=True)
    except OSError as exc:
        errors.append(f"cópia dos logs: {exc}")
    library = session.project / "Library"
    try:
        if library.is_dir():
            if session.cache.exists():
                _rmtree(session.cache, ctx.config.full.audit_root)
            os.replace(library, session.cache)
    except OSError as exc:
        errors.append(f"cache da Library: {exc}")
    try:
        _rmtree(session.root, ctx.config.full.audit_root)
    except OSError as exc:
        errors.append(f"remoção do snapshot: {exc}")
    if session.persistent is not None and session.isolated_data:
        try:
            _rmtree(session.persistent, session.persistent.parent)
        except OSError as exc:
            errors.append(f"dados isolados: {exc}")
    ctx.shared["cleanup_errors"] = errors


def import_and_compile(ctx: Context, check: CheckResult) -> None:
    session = _session(ctx)
    if session is None or not session.manifest:
        check.status, check.note = "skipped", "Sem snapshot: nada a importar."
        return
    full = ctx.config.full
    limit = full.import_timeout_seconds if session.library_source == "cold" else full.unity_timeout_seconds
    timeout = min(limit, ctx.remaining())
    if timeout < MIN_STEP_SECONDS:
        check.status, check.note = "skipped", "Prazo do perfil completo esgotado antes da importação."
        return
    log = session.out / "import.log"
    run = _run(ctx, check, ["-batchmode", "-nographics", "-quit", "-projectPath", str(session.project),
                            "-logFile", str(log)], log, timeout)
    if run is None:
        return
    text, digest = _read_log(log)
    check.data.update(exit_code=run.code, duration_ms=run.duration_ms, library_source=session.library_source,
                      contained=run.contained)
    evidence = check.add_evidence("log_excerpt", "full/import.log", f"exit {run.code} · {run.duration_ms // 1000} s",
                                  sha256=digest)
    if _environment_problem(check, text, run):
        return
    last = compile_findings(check, text, "isolated", "confirmed", evidence, ctx.config.max_findings_per_check)
    check.data["last_compile"] = last
    session.compiled = run.code == 0 and (last is None or last["result"] == "success")
    if run.code != 0 and not check.findings:
        check.degrade("error", f"A Unity saiu com código {run.code} sem erro de compilação identificável; "
                               "veja full/import.log.")
    check.note = (f"Importação {'concluída' if session.compiled else 'com falha'} em {run.duration_ms // 1000} s"
                  + (f" · compilação: {last['result']}, {last['errors']} erro(s), {last['warnings']} aviso(s)"
                     if last else " · nenhuma recompilação registrada (cache em dia)"))


def asset_references(ctx: Context, check: CheckResult) -> None:
    session = _session(ctx)
    if session is None or not session.manifest:
        check.status, check.note = "skipped", "Sem snapshot."
        return
    roots = [session.project / "Library" / "PackageCache"]
    editor = ctx.shared.get("editor_path")
    if editor:
        roots.append(Path(editor).parent / "Data" / "Resources" / "PackageManager" / "BuiltInPackages")
    collect_refs(ctx, check, session.project, roots)


def parse_test_results(path: Path) -> dict | None:
    """NUnit 3 do Test Runner. None = XML ausente ou ilegível (não é aprovação)."""
    try:
        root = ET.parse(path).getroot()
    except (OSError, ET.ParseError):
        return None
    attrs = {k: int(root.get(k, "0") or 0) for k in ("total", "passed", "failed", "skipped", "inconclusive")}
    failures = [(case.get("fullname") or case.get("name") or "?",
                 (case.findtext("failure/message") or "").strip()[:300])
                for case in root.iter("test-case") if case.get("result") == "Failed"]
    return {**attrs, "result": root.get("result"), "failures": failures}


def editmode_tests(ctx: Context, check: CheckResult) -> None:
    session = _session(ctx)
    assemblies = ctx.shared.get("test_assemblies") or []
    if not assemblies:
        check.status = "skipped"
        check.note = ("Nenhuma assembly de teste no projeto: o Test Runner rodaria zero testes, o que não é "
                      "aprovação. Crie uma assembly EditMode para ativar esta etapa.")
        return
    if session is None or not session.compiled:
        check.status, check.note = "skipped", "A cópia não compilou: testes não executados."
        return
    timeout = min(ctx.config.full.unity_timeout_seconds, ctx.remaining())
    if timeout < MIN_STEP_SECONDS:
        check.status, check.note = "skipped", "Prazo do perfil completo esgotado antes dos testes."
        return
    xml, log = session.out / "editmode.xml", session.out / "editmode.log"
    run = _run(ctx, check, ["-batchmode", "-projectPath", str(session.project), "-runTests", "-testPlatform",
                            "EditMode", "-testResults", str(xml), "-logFile", str(log)], log, timeout)
    if run is None:
        return
    text, digest = _read_log(log)
    if _environment_problem(check, text, run):
        return
    results = parse_test_results(xml)
    if results is None:
        check.degrade("error", f"Sem XML de resultados (exit {run.code}): os testes não podem ser dados como "
                               "aprovados. Veja full/editmode.log.")
        return
    evidence = check.add_evidence("file", "full/editmode.xml", f"{results['total']} teste(s), "
                                  f"{results['failed']} falha(s)", sha256=sha256_bytes(xml.read_bytes()))
    check.data.update(tests=results, exit_code=run.code)
    if results["total"] == 0:
        check.findings.append(Finding(
            rule="tests.zero", severity="medium", state="confirmed", key="editmode", evidence=[evidence],
            summary="O Test Runner encontrou zero testes EditMode",
            recommendation="Zero testes não é aprovação: confira se as assemblies de teste compilam e se têm [Test].",
        ))
    for name, message in results["failures"][:ctx.config.max_findings_per_check]:
        check.findings.append(Finding(
            rule="tests.failed", severity="high", state="confirmed", key=name, evidence=[evidence],
            summary=f"Teste EditMode falhou: {name}", recommendation=redact(message) or "Veja o XML de resultados.",
        ))
    check.note = (f"{results['total']} teste(s): {results['passed']} passaram, {results['failed']} falharam, "
                  f"{results['skipped']} ignorados")


def _normalize(line: str) -> str:
    return re.sub(r"\d+", "#", line.strip())[:160]


def run_validators(ctx: Context, check: CheckResult) -> None:
    session = _session(ctx)
    validators = ctx.config.full.validators
    if not validators:
        check.status, check.note = "skipped", "Nenhum validador configurado em [[full.validators]]."
        return
    if session is None or not session.compiled:
        check.status, check.note = "skipped", "A cópia não compilou: validadores não executados."
        return
    if not session.isolated_data:
        check.status, check.note = "skipped", "Dados do jogo não isolados: validadores não rodam sobre os dados reais."
        return
    outcomes = []
    for validator in validators:
        outcome = {"id": validator.id, "name": validator.name}
        outcomes.append(outcome)
        timeout = min(validator.timeout_seconds, ctx.remaining())
        if timeout < MIN_STEP_SECONDS:
            outcome.update(status="skipped", note="prazo do perfil completo esgotado")
            continue
        report, log = session.out / f"{validator.id}.txt", session.out / f"{validator.id}.log"
        args = ["-batchmode", *([] if validator.graphics else ["-nographics"]), "-projectPath", str(session.project),
                "-executeMethod", validator.method, validator.report_arg, str(report), *validator.extra_args,
                "-logFile", str(log)]
        run = _run(ctx, check, args, log, timeout)
        if run is None:
            outcome.update(status="error", note="editor não localizado")
            break
        text, log_digest = _read_log(log)
        outcome.update(exit_code=run.code, duration_ms=run.duration_ms)
        license_line = LICENSE.search(text) if run.code != 0 else None
        if license_line or run.timed_out or METHOD_MISSING.search(text):
            reason = ("licença indisponível" if license_line else "tempo esgotado; só este processo foi encerrado"
                      if run.timed_out else "método não encontrado no projeto")
            outcome.update(status="timeout" if run.timed_out else "error", note=reason)
            continue
        try:
            raw = report.read_bytes()
        except OSError:
            outcome.update(status="error", note=f"sem relatório (exit {run.code}); veja full/{validator.id}.log")
            continue
        content = raw.decode("utf-8-sig", "replace")
        failures = [m.group(1).strip() for m in FAILURE_LINE.finditer(content)]
        summary = RESULT_LINE.search(content)
        evidence = check.add_evidence("file", f"full/{validator.id}.txt", f"{validator.name}: exit {run.code}, "
                                      f"{len(failures)} falha(s)", sha256=sha256_bytes(raw),
                                      extra={"log_sha256": log_digest})
        outcome.update(status="passed" if run.code == 0 and not failures else "failed", failures=len(failures),
                       result=summary.group(1).strip()[:200] if summary else None, report_sha256=sha256_bytes(raw))
        for line in failures[:15]:
            check.findings.append(Finding(
                rule="validator.failure", severity="high", state="confirmed", key=f"{validator.id}|{_normalize(line)}",
                evidence=[evidence], summary=f"{validator.name}: {redact(line)[:220]}",
                recommendation=f"Reproduza com Unity -executeMethod {validator.method} numa cópia; relatório completo "
                               f"em full/{validator.id}.txt.",
            ))
        if len(failures) > 15:
            check.problems.append(f"{validator.name}: mais {len(failures) - 15} falha(s) no relatório.")
        if run.code not in (0, None) and not failures:
            check.findings.append(Finding(
                rule="validator.failed", severity="high", state="confirmed", key=validator.id, evidence=[evidence],
                summary=f"{validator.name} saiu com código {run.code} sem detalhar a falha",
                recommendation=f"Veja full/{validator.id}.txt e full/{validator.id}.log.",
            ))
    check.data["validators"] = outcomes
    bad = [o for o in outcomes if o.get("status") in ("error", "timeout", "skipped")]
    if bad:
        check.degrade("error" if len(bad) == len(outcomes) else "partial",
                      "Não executados por completo: " + ", ".join(f"{o['name']} ({o.get('note')})" for o in bad))
    passed = sum(1 for o in outcomes if o.get("status") == "passed")
    failed = sum(1 for o in outcomes if o.get("status") == "failed")
    check.note = f"{len(outcomes)} validador(es): {passed} sem falhas, {failed} com falhas, {len(bad)} não concluídos"


def origin_integrity(ctx: Context, check: CheckResult) -> None:
    before = ctx.shared.get("origin_manifest")
    if not before:
        check.status, check.note = "skipped", "Sem snapshot, a origem nem foi lida."
        return
    after, _ = hash_tree(ctx.config.project_root, ctx.config.full.copy_dirs, ctx)
    changed = sorted(k for k in before.keys() & after.keys() if before[k] != after[k])
    added = sorted(after.keys() - before.keys())
    removed = sorted(before.keys() - after.keys())
    same = not (changed or added or removed)
    check.data.update(identical=same, tree_before=tree_digest(before), tree_after=tree_digest(after),
                      changed=len(changed), added=len(added), removed=len(removed))
    evidence = check.add_evidence("file", ctx.config.project_root.as_posix(),
                                  f"árvore antes {tree_digest(before)[:12]} · depois {tree_digest(after)[:12]}")
    if same:
        check.note = f"Origem idêntica ao início do job ({len(after)} arquivos, hash {tree_digest(after)[:12]})."
        return
    examples = ", ".join((changed + added + removed)[:6])
    check.findings.append(Finding(
        rule="audit.origin-changed", severity="info", state="confirmed", key="origin", evidence=[evidence],
        occurrences=len(changed) + len(added) + len(removed),
        summary=f"A origem mudou durante a auditoria: {len(changed)} alterado(s), {len(added)} novo(s), "
                f"{len(removed)} removido(s)",
        recommendation="A auditoria só lê a origem e roda a Unity na cópia; mudanças assim vêm de edição em "
                       f"paralelo (editor aberto, agentes). O relatório vale para o snapshot. Ex.: {examples}",
    ))
    check.note = "A origem mudou durante o job (edição em paralelo); a auditoria vale para o snapshot."


CHECKS: list[tuple[str, str, Callable[[Context, CheckResult], None]]] = [
    ("snapshot", "Cópia isolada (snapshot)", prepare_snapshot),
    ("isolated_compile", "Importação e compilação na cópia", import_and_compile),
    ("asset_refs", "Referências de assets", asset_references),
    ("editmode", "Testes EditMode", editmode_tests),
    ("validators", "Validadores do projeto na cópia", run_validators),
    ("origin_integrity", "Integridade da origem", origin_integrity),
]
